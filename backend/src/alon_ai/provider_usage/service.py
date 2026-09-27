"""The only generic read/generation executor. No generic write binding exists.

Composition supplies trusted, versioned adapters which resolve immutable customer
configuration and its bounded request parameters. Callers supply only safe config
references. Adapters disable automatic HTTP retries and cannot checkpoint content.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import SecretStr

from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.integrations.schemas.provider import (
    CallAttribution,
    ProviderCallResult,
    ProviderErrorCode,
    ResultStatus,
    SafeRequestMetadata,
)
from alon_ai.policies.provider_rights import RuntimeContent
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CallReceipt,
    CallState,
    CapabilityConfig,
    Reason,
)
from alon_ai.security.secrets import SecretStore, SecretStoreError


class ConfiguredAdapter(Protocol):
    async def invoke(
        self, config: CapabilityConfig, secret: SecretStr | None, /
    ) -> ProviderCallResult[RuntimeContent]:
        """Resolve this exact immutable config; obey each configured quantity bound.

        Later concrete adapters must verify endpoint/model/token/page parameters
        against this config. Never accept a caller's independent raw request here.
        """
        ...


class ExecutionResult:
    __slots__ = ("content", "error", "receipt")

    def __init__(
        self,
        receipt: CallReceipt,
        content: RuntimeContent | None = None,
        error: ProviderErrorCode | None = None,
    ):
        self.receipt = receipt
        self.content = content
        self.error = error

    def __repr__(self):
        return f"ExecutionResult(receipt={self.receipt!r}, content=<runtime-only>, error={self.error})"

    def __reduce_ex__(self, protocol):
        raise TypeError("runtime execution result cannot be serialized")


class GovernedExecutor:
    def __init__(
        self,
        repository: GovernanceRepository,
        *,
        adapters: Mapping[UUID, ConfiguredAdapter],
        secrets: SecretStore | None = None,
    ):
        self.repository = repository
        self._adapters = dict(adapters)
        self._secrets = secrets

    async def execute(
        self,
        attribution: CallAttribution,
        request: SafeRequestMetadata,
        *,
        idempotency_key: UUID,
    ) -> ExecutionResult:
        receipt = await self.repository.reserve(
            attribution, request, idempotency_key=idempotency_key
        )
        if receipt.state != CallState.RESERVED:
            return ExecutionResult(receipt)
        config = await self.repository.config_for_call(receipt.call_id)
        adapter = self._adapters.get(config.adapter_version)
        if adapter is None:
            await self.repository.cancel_before_dispatch(
                receipt.call_id, command_key=uuid4()
            )
            raise AccountingDenied(Reason.CONFIG)
        secret = None
        try:
            if config.secret_handle:
                if self._secrets is None:
                    raise SecretStoreError("Secret access failed")
                secret = self._secrets.get(config.secret_handle)
        except SecretStoreError:
            await self.repository.cancel_before_dispatch(
                receipt.call_id, command_key=uuid4()
            )
            raise AccountingDenied(Reason.SECRET) from None
        try:
            dispatched = await self.repository.dispatch(receipt.call_id)
        except AccountingDenied as e:
            if e.reason in {Reason.UNCERTAIN, Reason.STATE}:
                return ExecutionResult(await self.repository.get(receipt.call_id))
            # A denied dispatch has not called the adapter. Cancellation is still
            # fenced: a concurrent successful dispatch cannot be released here.
            try:
                await self.repository.cancel_before_dispatch(
                    receipt.call_id, command_key=uuid4()
                )
            except AccountingDenied:
                pass
            raise
        assert dispatched.token is not None and dispatched.timeout_seconds is not None
        try:
            remaining = (attribution.deadline - self.repository.clock()).total_seconds()
            if remaining <= 0:
                raise TimeoutError("dispatch deadline expired")
            async with asyncio.timeout(min(dispatched.timeout_seconds, remaining)):
                result = await adapter.invoke(config, secret)
            if (
                not isinstance(result, ProviderCallResult)
                or result.metadata.capability != config.intended_use.capability
            ):
                raise ValueError("invalid classified response")
            if result.content is not None and not isinstance(
                result.content, RuntimeContent
            ):
                raise ValueError("invalid runtime content")
        except asyncio.CancelledError:
            await asyncio.shield(
                self.repository.mark_unknown(receipt.call_id, token=dispatched.token)
            )
            raise
        except TimeoutError:
            unknown = await self.repository.mark_unknown(
                receipt.call_id, token=dispatched.token
            )
            return ExecutionResult(unknown, error=ProviderErrorCode.TIMEOUT)
        except Exception:  # noqa: BLE001 - untrusted adapter errors must be classified
            # Do not retain, chain, serialize or log upstream exception data.
            unknown = await self.repository.mark_unknown(
                receipt.call_id, token=dispatched.token
            )
            return ExecutionResult(unknown, error=ProviderErrorCode.UNAVAILABLE)
        await self.repository.record_usage(
            receipt.call_id, result.metadata.usage, token=dispatched.token
        )
        if result.metadata.status == ResultStatus.UNKNOWN:
            return ExecutionResult(
                await self.repository.mark_unknown(
                    receipt.call_id, token=dispatched.token
                ),
                error=result.metadata.error_code,
            )
        proof_id = await self.repository.finish_attempt(
            receipt.call_id,
            token=dispatched.token,
            success=result.metadata.status == ResultStatus.SUCCEEDED,
            metadata=result.metadata,
        )
        assert proof_id is not None
        try:
            receipt = await self.repository.reconcile(
                receipt.call_id, command_key=uuid4(), evidence_id=proof_id
            )
        except AccountingDenied as e:
            if e.reason != Reason.UNCERTAIN:
                raise
            receipt = await self.repository.get(receipt.call_id)
        return ExecutionResult(receipt, result.content, result.metadata.error_code)
