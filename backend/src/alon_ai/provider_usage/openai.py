"""Governed, bounded OpenAI dispatch with post-lock authority rechecks."""

from __future__ import annotations

from contextlib import AsyncExitStack
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.runtime import BoundedOpenAICall
from alon_ai.agents.schemas.openai import (
    OpenAIProfile,
    ParsedResponse,
    RoutingFacts,
    RoutingPolicy,
    sha256,
)
from alon_ai.db.repositories.openai_inputs import (
    accepted_input as _accepted_input,
)
from alon_ai.db.repositories.openai_inputs import (
    experiment_dispatch_guard,
    retained_rights_status,
)
from alon_ai.integrations.openai import ResponsesTransport
from alon_ai.integrations.schemas.provider import (
    Capability,
    CostKnowledge,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderResultMetadata,
    Purpose,
    ResultStatus,
    UsageObservation,
)
from alon_ai.policies.openai_inputs import (
    _current_retained_rights,
    _require_market_inputs,
    _source_input,
)
from alon_ai.policies.openai_pricing import _priced_usage
from alon_ai.policies.provider_rights import RuntimeContent
from alon_ai.provider_usage.schemas.accounting import CapabilityConfig, PriceVersion

if TYPE_CHECKING:
    from alon_ai.agents.runtime import (
        AcceptedArtifact,
        AcceptedOperatorProfile,
        AcceptedRetainedEvidence,
        AcceptedSource,
    )
    from alon_ai.db.repositories.openai_authority import OpenAIAuthorityStore


class ConfiguredResponsesAdapter:
    def __init__(
        self,
        *,
        profile: OpenAIProfile,
        input_json: str,
        client_request_id: UUID,
        key: UUID,
        prices: tuple[PriceVersion, ...],
        transport: ResponsesTransport,
        clock,
        authority: OpenAIAuthorityStore,
        routes: RoutingPolicy,
        facts: RoutingFacts,
        scope: UUID,
        sources: tuple[AcceptedSource, ...],
        artifacts: tuple[AcceptedArtifact, ...],
        operator_profiles: tuple[AcceptedOperatorProfile, ...],
        retained_evidence: tuple[AcceptedRetainedEvidence, ...],
        engine: AsyncEngine,
    ):
        self.profile = profile
        self.input_json = input_json
        self.client_request_id = client_request_id
        self.key = key
        self.prices = prices
        self.bounded = BoundedOpenAICall(profile, transport)
        self.clock = clock
        self.authority = authority
        self.routes = routes
        self.facts = facts
        self.scope = scope
        self.sources = sources
        self.artifacts = artifacts
        self.operator_profiles = operator_profiles
        self.retained_evidence = retained_evidence
        self.engine = engine
        self.parsed: ParsedResponse | None = None

    async def invoke(
        self, config: CapabilityConfig, secret: SecretStr | None, /
    ) -> ProviderCallResult[RuntimeContent]:
        if (
            config.id != self.profile.config_id
            or config.version != self.profile.config_version
            or config.adapter_version != self.profile.adapter_version
            or config.model_identifier != self.profile.model_identifier
            or config.intended_use.capability is not Capability.OPENAI_GENERATE
            or config.intended_use.purpose is not Purpose.GENERATION
            or secret is None
        ):
            raise ValueError("configured OpenAI capability mismatch")
        approval = (
            self.facts.premium_authorization if self.facts.premium_requested else None
        )
        async with AsyncExitStack() as stack:
            root_enabled = True
            if self.artifacts or self.operator_profiles:
                # Product commands take this experiment lock before changing
                # versions, acceptances or cycle state. Keep the same order as
                # governance: experiment first, then provider authority.
                root_enabled = await stack.enter_async_context(
                    experiment_dispatch_guard(self.engine, self.scope)
                )
            snapshot = await stack.enter_async_context(
                self.authority.dispatch_guard(
                    tuple(
                        (source.current_grant.grant_id, source.current_grant.version)
                        for source in self.sources
                    )
                    + tuple(
                        (item.reference.grant_id, item.reference.grant_version)
                        for item in self.retained_evidence
                        if item.reference.grant_id is not None
                        and item.reference.grant_version is not None
                    ),
                    approval.authorization_id if approval else None,
                )
            )
            # Locks serialize revocation with this bounded transport operation.
            # Time validity is checked after every lock/snapshot wait.
            started = self.clock()
            try:
                if root_enabled is not True:
                    raise PermissionError("experiment was disabled before dispatch")
                _require_market_inputs(
                    self.profile,
                    self.sources,
                    self.artifacts,
                    self.operator_profiles,
                )
                self.routes.select(self.facts, scope=self.scope, now=started)
                if self.facts.premium_requested and (
                    approval is None
                    or snapshot.approval != approval
                    or snapshot.approval_config_id != config.id
                    or snapshot.revoked_at is not None
                    and snapshot.revoked_at <= started
                ):
                    raise PermissionError("premium approval is not current")
                input_json = await _accepted_input(
                    self.engine,
                    self.sources,
                    self.artifacts,
                    self.operator_profiles,
                    self.retained_evidence,
                    self.scope,
                    started,
                    grants=snapshot.grants,
                    events=snapshot.events,
                )
                retained_rights = (
                    await retained_rights_status(
                        self.engine, self.retained_evidence, snapshot.grants
                    )
                    if self.retained_evidence
                    else []
                )
                # Artifact/profile reads can wait on the DB after the first
                # authority check. Re-evaluate rights at the final dispatch
                # time; no further DB await occurs before transport.
                started = self.clock()
                self.routes.select(self.facts, scope=self.scope, now=started)
                if self.facts.premium_requested and (
                    approval is None
                    or snapshot.approval != approval
                    or snapshot.approval_config_id != config.id
                    or snapshot.revoked_at is not None
                    and snapshot.revoked_at <= started
                ):
                    raise PermissionError("premium approval is not current")
                if self.sources:
                    _source_input(
                        self.sources, started, snapshot.grants, snapshot.events
                    )
                for ref, grant, candidates, enabled in retained_rights:
                    if (
                        ref.expires_at is None
                        or ref.field is None
                        or started >= ref.expires_at
                        or enabled is not True
                        or not _current_retained_rights(
                            grant, candidates, snapshot.events, ref.field, started
                        )
                    ):
                        raise PermissionError(
                            "retained evidence rights changed before dispatch"
                        )
                if sha256(input_json) != sha256(self.input_json):
                    raise PermissionError("accepted source content changed")
            except PermissionError:
                # Positive evidence of no transport means zero billable usage.
                return ProviderCallResult(
                    ProviderResultMetadata(
                        capability=Capability.OPENAI_GENERATE,
                        started_at=started,
                        finished_at=started,
                        status=ResultStatus.FAILED,
                        error_code=ProviderErrorCode.DENIED,
                        usage=tuple(
                            UsageObservation(
                                component=price.component,
                                quantity=Decimal(0),
                                cost=Decimal(0),
                                currency=price.currency,
                                knowledge=CostKnowledge.FINAL,
                                observation_key=uuid5(self.key, price.component.value),
                            )
                            for price in self.prices
                        ),
                    ),
                    None,
                )
            response = await self.bounded.dispatch(
                input_json, secret, self.client_request_id
            )
        finished = self.clock()
        parsed = self.bounded.classify(response, input_json)
        self.parsed = parsed
        status, error = {
            "SUCCEEDED": (ResultStatus.SUCCEEDED, None),
            "REFUSED": (ResultStatus.REFUSED, ProviderErrorCode.REFUSED),
            "SCHEMA_MISMATCH": (
                ResultStatus.FAILED,
                ProviderErrorCode.MALFORMED_RESPONSE,
            ),
            "INCOMPLETE": (ResultStatus.FAILED, ProviderErrorCode.INCOMPLETE_RESULT),
            "FAILED": (ResultStatus.FAILED, ProviderErrorCode.UNAVAILABLE),
            "CANCELLED": (ResultStatus.FAILED, ProviderErrorCode.CANCELLED_RESULT),
            "UNCERTAIN": (ResultStatus.UNKNOWN, ProviderErrorCode.UNAVAILABLE),
        }[parsed.outcome]
        return ProviderCallResult(
            ProviderResultMetadata(
                capability=Capability.OPENAI_GENERATE,
                external_request_id=parsed.external_request_id,
                started_at=started,
                finished_at=finished,
                status=status,
                error_code=error,
                usage=_priced_usage(parsed, self.prices, self.key),
            ),
            None,
        )
