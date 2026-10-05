"""Governed research requests, durable request checkpoints and licensed evidence.

Only runtime request inputs are hashed. Provider response bodies never enter step
checkpoints. All provider requests pass through the existing GovernedExecutor.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta
from decimal import ROUND_CEILING, Decimal, localcontext
from typing import Protocol
from uuid import UUID, uuid5

import httpx
from pydantic import SecretStr
from sqlalchemy import select

from alon_ai.agents.tools.research import (
    SavedEvidenceExcerpt,
    TransientSearchUrls,
    UnavailableResearchResult,
)
from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.agent_run_steps import steps as step_rows
from alon_ai.db.tables.agent_runs import runs
from alon_ai.integrations.brave import BraveSearchAdapter
from alon_ai.integrations.firecrawl import FirecrawlAdapter
from alon_ai.integrations.live_research import (
    ResearchCapabilityBinding,
    ResearchRunPolicy,
)
from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    CallAttribution,
    Capability,
    CostKnowledge,
    FirecrawlCaptureRequest,
    FirecrawlMapRequest,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderFailure,
    Purpose,
    ResultStatus,
    SafeRequestMetadata,
    UsageComponent,
    UsageObservation,
)
from alon_ai.policies.provider_rights import RuntimeContent
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    CallReceipt,
    CallState,
    CapabilityConfig,
    Reason,
    reserve_amount,
)
from alon_ai.provider_usage.service import GovernedExecutor
from alon_ai.security.secrets import SecretStore
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    SourceReference,
)

ResearchRequest = BraveSearchRequest | FirecrawlMapRequest | FirecrawlCaptureRequest
_KINDS = {
    "BRAVE_SEARCH",
    "FIRECRAWL_MAP",
    "FIRECRAWL_PAGE_CAPTURE",
    "FIRECRAWL_PDF_CAPTURE",
    "FIRECRAWL_JS_RETRIEVAL",
}


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _request_hash(request: ResearchRequest) -> str:
    data = request.model_dump(mode="json")
    # SecretStr serialization is deliberately redacted; bind the real runtime query.
    if isinstance(request, BraveSearchRequest):
        data["query"] = request.query.get_secret_value()
    if isinstance(request, (FirecrawlMapRequest, FirecrawlCaptureRequest)):
        data["url"] = request.url
    return _hash(data)


class ResearchStepStore(Protocol):
    async def claim(
        self,
        *,
        key: UUID,
        request_hash: str,
        binding: ResearchCapabilityBinding,
        policy: ResearchRunPolicy,
        candidate: ArtifactInput | None,
    ) -> Mapping: ...
    async def bind_receipt(self, key: UUID, receipt: CallReceipt) -> None: ...
    async def finish(
        self, key: UUID, *, status: str, reason: str | None = None
    ) -> None: ...
    def dispatch_scope(self) -> AbstractAsyncContextManager[None]: ...


class PostgreSQLResearchStepStore:
    """Run-row locking serializes durable limits with cancellation and dispatch."""

    def __init__(
        self,
        repository: GovernanceRepository,
        *,
        run_id: UUID,
        operator_id: UUID,
        attribution: CallAttribution,
        policy: ResearchRunPolicy,
    ):
        self.policy = policy
        self.repository, self.run_id = repository, run_id
        self.operator_id, self.attribution = operator_id, attribution
        self.store = AgentRunStepRepository(repository.engine)

    async def _run(self, connection):
        row = (
            (
                await connection.execute(
                    select(runs)
                    .where(
                        runs.c.run_id == self.run_id,
                        runs.c.experiment_id == self.attribution.experiment_id,
                        runs.c.operator_id == self.operator_id,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if (
            row is None
            or row["status"] != "RUNNING"
            or row["cancel_requested_at"] is not None
        ):
            raise AccountingDenied(Reason.GATE)
        now = self.repository.clock()
        started = row["started_at"] or row["created_at"]
        if (
            not self.policy.effective_at
            <= now
            < min(
                self.policy.expires_at,
                started + timedelta(seconds=self.policy.timeout_seconds),
            )
        ):
            raise AccountingDenied(Reason.DEADLINE)
        return row

    @asynccontextmanager
    async def dispatch_scope(self):
        async with self.repository.engine.begin() as connection:
            await self._run(connection)
            yield

    async def claim(self, *, key, request_hash, binding, policy, candidate):
        config_hash = _hash(
            {
                "binding": binding.model_dump(mode="json"),
                "policy": policy.model_dump(mode="json"),
            }
        )
        identity = {
            "request_hash": request_hash,
            "config_ref": binding.config.id,
            "config_hash": config_hash,
            "candidate_artifact_id": candidate.artifact_id if candidate else None,
            "candidate_kind": candidate.kind.value if candidate else None,
            "candidate_version": candidate.version if candidate else None,
            "candidate_hash": candidate.content_hash if candidate else None,
        }
        kind = (
            "BRAVE_SEARCH"
            if binding.config.intended_use.capability is Capability.BRAVE_WEB_COVERAGE
            else binding.config.intended_use.capability.value
        )
        async with self.repository.engine.begin() as connection:
            run = await self._run(connection)
            rows = (
                (
                    await connection.execute(
                        select(step_rows).where(step_rows.c.run_id == self.run_id)
                    )
                )
                .mappings()
                .all()
            )
            old = next((r for r in rows if r["step_key"] == key), None)
            if old is not None:
                if any(old[k] != v for k, v in identity.items()):
                    raise AccountingDenied(Reason.CONFLICT)
                return old
            now = self.repository.clock()
            started = run["started_at"] or run["created_at"]
            if (
                not policy.effective_at
                <= now
                < min(
                    policy.expires_at,
                    started + timedelta(seconds=policy.timeout_seconds),
                )
            ):
                raise AccountingDenied(Reason.DEADLINE)
            research = [r for r in rows if r["kind"] in _KINDS]
            pages = sum(
                policy.max_pdf_pages
                if r["kind"] == "FIRECRAWL_PDF_CAPTURE"
                else 1
                if r["kind"] in {"FIRECRAWL_PAGE_CAPTURE", "FIRECRAWL_JS_RETRIEVAL"}
                else 0
                for r in research
            )
            added = (
                policy.max_pdf_pages
                if kind == "FIRECRAWL_PDF_CAPTURE"
                else 1
                if kind in {"FIRECRAWL_PAGE_CAPTURE", "FIRECRAWL_JS_RETRIEVAL"}
                else 0
            )
            if len(research) >= policy.max_calls or pages + added > policy.max_pages:
                raise AccountingDenied(Reason.BUDGET)
            values = dict(
                run_id=self.run_id,
                experiment_id=self.attribution.experiment_id,
                step_key=key,
                ordinal=max((r["ordinal"] for r in rows), default=0) + 1,
                kind=kind,
                **identity,
                request_ref=key,
                request_version=1,
                config_version=1,
                operation_id=self.attribution.operation_run_id,
                operation_workflow_id=self.attribution.workflow_run_id,
                provider_call_id=None,
                status="CLAIMED",
                reason_code=None,
                result_artifact_id=None,
                result_kind=None,
                result_version=None,
                result_hash=None,
                created_at=now,
                finished_at=None,
            )
            return (
                (
                    await connection.execute(
                        step_rows.insert().values(**values).returning(step_rows)
                    )
                )
                .mappings()
                .one()
            )

    async def bind_receipt(self, key, receipt):
        await self.store.bind(self.run_id, key, provider_call_id=receipt.call_id)

    async def finish(self, key, *, status, reason=None):
        await self.store.finish(self.run_id, key, status=status, reason_code=reason)


class _RequestAdapter:
    def __init__(self, owner, binding, request, prices, key):
        self.owner, self.binding, self.request, self.prices, self.key = (
            owner,
            binding,
            request,
            prices,
            key,
        )
        self.failure: ProviderFailure | None = None
        self.completed_rejection = False

    async def invoke(
        self, config: CapabilityConfig, secret: SecretStr | None, /
    ) -> ProviderCallResult[RuntimeContent]:
        if config != self.binding.config or secret is None:
            raise AccountingDenied(Reason.CONFIG)
        owner = self.owner
        async with owner._steps.dispatch_scope():
            async with owner._repository.engine.connect() as connection:
                grant, events = await owner._repository._rights(
                    connection,
                    config,
                    owner._repository.clock(),
                    (self.binding.grant.grant_id, self.binding.grant.version),
                )
            kwargs = {
                "grant": grant,
                "intended_use": config.intended_use,
                "events": lambda: events,
                "clock": owner._repository.clock,
            }
            try:
                if isinstance(self.request, BraveSearchRequest):
                    result = await BraveSearchAdapter(
                        secret, **kwargs, transport=owner._brave_transport
                    ).search(self.request)
                else:
                    extra = (
                        {} if owner._resolver is None else {"resolver": owner._resolver}
                    )
                    adapter = FirecrawlAdapter(
                        secret,
                        **kwargs,
                        **extra,
                        transport=owner._firecrawl_transport,
                        max_pdf_bytes=owner._policy.max_pdf_bytes,
                        max_pdf_pages=owner._policy.max_pdf_pages,
                        max_text_chars=owner._policy.max_text_chars,
                        pdf_cpu_seconds=owner._policy.pdf_cpu_seconds,
                        pdf_memory_bytes=owner._policy.pdf_memory_bytes,
                        pdf_wall_seconds=owner._policy.pdf_wall_seconds,
                    )
                    result = await (
                        adapter.map(self.request)
                        if isinstance(self.request, FirecrawlMapRequest)
                        else adapter.capture(self.request)
                    )
            except ProviderFailure as error:
                # Keep only the classified code/status in memory after the executor
                # quarantines this dispatched attempt. Never retain the response.
                self.failure = ProviderFailure(
                    error.code, http_status=error.http_status
                )
                raise
            self.completed_rejection = (
                config.intended_use.capability
                in {
                    Capability.FIRECRAWL_PAGE_CAPTURE,
                    Capability.FIRECRAWL_JS_RETRIEVAL,
                }
                and result.metadata.status is ResultStatus.FAILED
                and result.metadata.error_code is ProviderErrorCode.MALFORMED_RESPONSE
                and result.content is None
            )
            observations = []
            for observed in result.metadata.usage:
                if config.intended_use.capability is Capability.FIRECRAWL_MAP:
                    # Returned link count does not prove provider-billed credit usage.
                    # Keep the full ceiling reserved pending authoritative reconciliation.
                    observations.append(observed)
                    continue
                price = next(
                    p for p in self.prices if p.component == observed.component
                )
                bound = next(b for b in config.prices if b.price_id == price.id)
                if observed.quantity is None and self.completed_rejection:
                    # Exact immutable included-credit prices prove cash zero,
                    # not consumed credits. Keep quantity unknown and quota used.
                    zero_cash = all(p.unit_price == 0 for p in self.prices)
                    observations.append(
                        observed.model_copy(
                            update={
                                "currency": price.currency,
                                "cost": Decimal(0) if zero_cash else None,
                                "knowledge": CostKnowledge.FINAL
                                if zero_cash
                                else CostKnowledge.UNAVAILABLE,
                                "observation_key": uuid5(
                                    self.key, observed.component.value
                                ),
                            }
                        )
                    )
                    continue
                if observed.quantity is None or observed.quantity > bound.max_quantity:
                    raise AccountingDenied(Reason.USAGE)
                with localcontext() as context:
                    context.prec = 64
                    cost = (
                        observed.quantity * price.unit_price / price.unit_quantity
                    ).quantize(Decimal("1e-12"), rounding=ROUND_CEILING)
                observations.append(
                    UsageObservation(
                        component=observed.component,
                        quantity=observed.quantity,
                        currency=price.currency,
                        cost=cost,
                        knowledge=CostKnowledge.FINAL,
                        observation_key=uuid5(self.key, observed.component.value),
                    )
                )
            unresolved = any(
                item.knowledge is CostKnowledge.UNAVAILABLE for item in observations
            )
            return ProviderCallResult(
                result.metadata.model_copy(
                    update={
                        "usage": tuple(observations),
                        **(
                            {"status": ResultStatus.UNKNOWN}
                            if self.completed_rejection and unresolved
                            else {}
                        ),
                    }
                ),
                result.content,
            )


class GovernedLiveResearchPort:
    def __init__(
        self,
        repository: GovernanceRepository,
        secrets: SecretStore,
        *,
        run_id: UUID,
        operator_id: UUID,
        attribution: CallAttribution,
        policy: ResearchRunPolicy,
        bindings: Mapping[Capability, ResearchCapabilityBinding],
        steps: ResearchStepStore | None = None,
        candidate: ArtifactInput | None = None,
        brave_transport: httpx.AsyncBaseTransport | None = None,
        firecrawl_transport: httpx.AsyncBaseTransport | None = None,
        resolver: Callable[[str], tuple[str, ...]] | None = None,
    ):
        if (
            policy.approved_by != operator_id
            or not bindings
            or candidate is not None
            and candidate.kind is not ArtifactKind.IDEA_CANDIDATE
        ):
            raise AccountingDenied(Reason.CONFIG)
        for capability, binding in bindings.items():
            if (
                capability is not binding.config.intended_use.capability
                or binding.config.version != attribution.config_version
                or binding.config.workflow_id != attribution.workflow_run_id
            ):
                raise AccountingDenied(Reason.CONFIG)
        self._transient_calls: set[UUID] = set()
        self._served: dict[UUID, SourceReference] = {}
        self._repository, self._secrets = repository, secrets
        self._run_id, self._attribution, self._policy = run_id, attribution, policy
        self._bindings, self._candidate = dict(bindings), candidate
        self._steps = (
            steps
            if steps is not None
            else PostgreSQLResearchStepStore(
                repository,
                run_id=run_id,
                operator_id=operator_id,
                attribution=attribution,
                policy=policy,
            )
        )
        self._brave_transport, self._firecrawl_transport, self._resolver = (
            brave_transport,
            firecrawl_transport,
            resolver,
        )

    async def search(
        self, experiment_id: UUID, request: BraveSearchRequest
    ) -> tuple[SourceReference, ...] | TransientSearchUrls | UnavailableResearchResult:
        if not isinstance(request, BraveSearchRequest):
            raise AccountingDenied(Reason.CONFIG)
        return await self._execute(experiment_id, request)

    async def map(
        self, experiment_id: UUID, request: FirecrawlMapRequest
    ) -> tuple[SourceReference, ...] | UnavailableResearchResult:
        if not isinstance(request, FirecrawlMapRequest):
            raise AccountingDenied(Reason.CONFIG)
        result = await self._execute(experiment_id, request)
        if isinstance(result, UnavailableResearchResult):
            return result
        if not isinstance(result, tuple):
            raise AccountingDenied(Reason.CONFIG)
        return result

    async def capture(
        self, experiment_id: UUID, request: FirecrawlCaptureRequest
    ) -> tuple[SourceReference, ...] | UnavailableResearchResult:
        if not isinstance(request, FirecrawlCaptureRequest):
            raise AccountingDenied(Reason.CONFIG)
        result = await self._execute(experiment_id, request)
        if isinstance(result, UnavailableResearchResult):
            return result
        if not isinstance(result, tuple):
            raise AccountingDenied(Reason.CONFIG)
        return result

    async def _execute(self, experiment_id, request):
        activity = AgentRunRepository(self._repository.engine)
        capability = request.capability.value
        await activity.record_activity(
            self._run_id,
            "RESEARCH_REQUEST",
            f"{capability} requested · result limit {getattr(request, 'limit', 1)}",
        )
        try:
            result = await self._execute_request(experiment_id, request)
        except AccountingDenied as error:
            failure = error.__cause__
            detail = error.reason.value
            if isinstance(failure, ProviderFailure):
                detail = (
                    f"HTTP_{failure.http_status}"
                    if failure.http_status is not None
                    else failure.code.value
                )
            if error.reason is Reason.UNCERTAIN:
                detail += " · accounting pending reconciliation"
            await asyncio.shield(
                activity.record_activity(
                    self._run_id,
                    "RESEARCH_RESPONSE",
                    f"{capability} blocked · {detail}",
                )
            )
            raise
        if isinstance(result, UnavailableResearchResult):
            await activity.record_activity(
                self._run_id,
                "RESEARCH_RESPONSE",
                f"{capability} blocked · CIRCUIT · not dispatched"
                if result.status == "NOT_DISPATCHED"
                else f"{capability} completed with unusable content · no evidence · cash reconciled",
            )
            return result
        count = (
            len(result.urls) if isinstance(result, TransientSearchUrls) else len(result)
        )
        await activity.record_activity(
            self._run_id,
            "RESEARCH_RESPONSE",
            f"{capability} completed · {count} references returned",
        )
        return result

    async def _execute_request(self, experiment_id, request):
        if experiment_id != self._attribution.experiment_id:
            raise AccountingDenied(Reason.SCOPE)
        now = self._repository.clock()
        if not self._policy.effective_at <= now < self._policy.expires_at:
            raise AccountingDenied(Reason.CONFIG)
        binding = self._bindings.get(request.capability)
        if binding is None or getattr(request, "limit", 1) > self._policy.max_results:
            raise AccountingDenied(Reason.CONFIG)
        config, prices = await self._repository.generation_config_and_prices(
            binding.config.id
        )
        component = (
            UsageComponent.CAPTURE_PAGE
            if request.capability
            in {Capability.FIRECRAWL_PAGE_CAPTURE, Capability.FIRECRAWL_JS_RETRIEVAL}
            else UsageComponent.REQUEST
        )
        if (
            config != binding.config
            or len(prices) != 1
            or prices[0].component is not component
            or prices[0].currency != "USD"
            or len(config.prices) != 1
            or config.prices[0].max_quantity
            != Decimal(
                self._policy.max_results
                if request.capability is Capability.FIRECRAWL_MAP
                else 1
            )
        ):
            raise AccountingDenied(Reason.PRICE)
        # Conservative policy envelope: every permitted call could use this route.
        if (
            reserve_amount(
                config.prices[0].max_quantity
                * prices[0].unit_price
                / prices[0].unit_quantity,
                Decimal(".01"),
            )
            * self._policy.max_calls
            > self._policy.max_spend_usd
        ):
            raise AccountingDenied(Reason.BUDGET)
        digest = _request_hash(request)
        key = uuid5(self._run_id, "research/" + digest)
        step = await self._steps.claim(
            key=key,
            request_hash=digest,
            binding=binding,
            policy=self._policy,
            candidate=self._candidate,
        )
        if step["status"] != "CLAIMED":
            if step["status"] == "BLOCKED" and step["reason_code"] == "CIRCUIT":
                receipt = await self._repository.receipt_for_idempotency_key(key)
                if receipt is not None and receipt.state is CallState.RELEASED:
                    return UnavailableResearchResult.circuit_open()
            if (
                step["status"] == "FAILED"
                and step["reason_code"] == "MALFORMED_RESPONSE"
                and request.capability
                in {
                    Capability.FIRECRAWL_PAGE_CAPTURE,
                    Capability.FIRECRAWL_JS_RETRIEVAL,
                }
            ):
                receipt = await self._repository.receipt_for_idempotency_key(key)
                if receipt is not None and receipt.state is CallState.FINAL:
                    return UnavailableResearchResult()
            if step["status"] != "SUCCEEDED" or step["provider_call_id"] is None:
                raise AccountingDenied(Reason.UNCERTAIN)
            if config.intended_use.purpose is Purpose.OFFICIAL_SOURCE_IDENTIFICATION:
                raise AccountingDenied(Reason.RETENTION)
            return await self._references(step["provider_call_id"])
        adapter = _RequestAdapter(self, binding, request, prices, key)
        result = None
        try:
            result = await GovernedExecutor(
                self._repository,
                adapters={config.adapter_version: adapter},
                secrets=self._secrets,
            ).execute(
                self._attribution.model_copy(
                    update={
                        "logical_operation_id": key,
                        "deadline": min(
                            self._attribution.deadline,
                            self._policy.expires_at,
                            self._attribution.deadline,
                        ),
                    }
                ),
                SafeRequestMetadata(config_ref=config.id),
                idempotency_key=key,
            )
        except (AccountingDenied, asyncio.CancelledError) as error:
            receipt = await asyncio.shield(
                self._repository.receipt_for_idempotency_key(key)
            )
            if receipt is not None:
                await asyncio.shield(self._steps.bind_receipt(key, receipt))
            await asyncio.shield(
                self._steps.finish(
                    key,
                    status="OUTCOME_UNKNOWN"
                    if isinstance(error, asyncio.CancelledError) and receipt is not None
                    else "BLOCKED",
                    reason="PROVIDER_OUTCOME_UNKNOWN"
                    if isinstance(error, asyncio.CancelledError)
                    else error.reason.value,
                )
            )
            if (
                isinstance(error, AccountingDenied)
                and error.reason is Reason.CIRCUIT
                and receipt is not None
                and receipt.state is CallState.RELEASED
            ):
                return UnavailableResearchResult.circuit_open()
            raise
        finally:
            receipt = await asyncio.shield(
                self._repository.receipt_for_idempotency_key(key)
            )
            if receipt is not None:
                await asyncio.shield(self._steps.bind_receipt(key, receipt))
        if result.error is not None:
            if adapter.completed_rejection and result.receipt.state is CallState.FINAL:
                await self._steps.finish(
                    key, status="FAILED", reason="MALFORMED_RESPONSE"
                )
                return UnavailableResearchResult()
            await self._steps.finish(
                key, status="OUTCOME_UNKNOWN", reason="PROVIDER_OUTCOME_UNKNOWN"
            )
            raise AccountingDenied(Reason.UNCERTAIN) from (
                adapter.failure or ProviderFailure(result.error)
            )
        async with self._steps.dispatch_scope():
            if config.intended_use.purpose is Purpose.OFFICIAL_SOURCE_IDENTIFICATION:
                if result.content is None:
                    raise AccountingDenied(Reason.RETENTION)
                async with self._repository.engine.connect() as connection:
                    grant, events = await self._repository._rights(
                        connection,
                        config,
                        self._repository.clock(),
                        (binding.grant.grant_id, binding.grant.version),
                    )
                urls: list[str] = []
                result.content.consume_official_sources(
                    urls.extend,
                    current_grant=grant,
                    events=events,
                    now=self._repository.clock(),
                )
                self._transient_calls.add(result.receipt.call_id)
                await self._steps.finish(key, status="SUCCEEDED")
                return TransientSearchUrls(tuple(urls))
            if result.content is not None:
                await self._repository.retain_content(
                    result.receipt.call_id, result.content
                )
            references = await self._references(result.receipt.call_id)
            if not references:
                raise AccountingDenied(Reason.RETENTION)
            await self._steps.finish(key, status="SUCCEEDED")
            return references

    async def _references(self, call_id: UUID) -> tuple[SourceReference, ...]:
        content = await self._repository.read_content(call_id)
        async with self._repository.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(gov.retained)
                        .join(gov.calls, gov.calls.c.id == gov.retained.c.call_id)
                        .where(
                            gov.retained.c.call_id == call_id,
                            gov.calls.c.experiment_id
                            == self._attribution.experiment_id,
                            gov.calls.c.operation_id
                            == self._attribution.operation_run_id,
                            gov.retained.c.expires_at > self._repository.clock(),
                        )
                        .order_by(gov.retained.c.field, gov.retained.c.id)
                    )
                )
                .mappings()
                .all()
            )
        return tuple(
            SourceReference.retained_content(
                retained_id=r["id"],
                call_id=call_id,
                grant_id=r["grant_id"],
                grant_version=r["grant_version"],
                field=r["field"],
                expires_at=r["expires_at"],
            )
            for r in rows
            if r["field"] in content
        )

    async def read_saved_evidence(
        self, experiment_id: UUID, retained_id: UUID, *, max_chars: int
    ) -> SavedEvidenceExcerpt:
        if (
            experiment_id != self._attribution.experiment_id
            or type(max_chars) is not int
            or not 1 <= max_chars <= 4000
        ):
            raise AccountingDenied(Reason.SCOPE)
        async with self._repository.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(gov.retained)
                        .join(gov.calls, gov.calls.c.id == gov.retained.c.call_id)
                        .where(
                            gov.retained.c.id == retained_id,
                            gov.calls.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise AccountingDenied(Reason.SCOPE)
        fields = await self._repository.read_content(row["call_id"])
        if row["field"] not in fields or row["expires_at"] <= self._repository.clock():
            raise AccountingDenied(Reason.RETENTION)
        reference = SourceReference.retained_content(
            retained_id=row["id"],
            call_id=row["call_id"],
            grant_id=row["grant_id"],
            grant_version=row["grant_version"],
            field=row["field"],
            expires_at=row["expires_at"],
        )
        self._served[retained_id] = reference
        return SavedEvidenceExcerpt(
            reference, "\n\n".join(fields[row["field"]])[:max_chars]
        )

    async def resolve_references(
        self, identifiers: tuple[str, ...]
    ) -> tuple[SourceReference, ...]:
        """Resolve only source IDs produced by this run, with current rights."""
        if len(identifiers) > 20 or len(set(identifiers)) != len(identifiers):
            raise AccountingDenied(Reason.SCOPE)
        references = []
        for identifier in identifiers:
            try:
                retained_id = UUID(identifier)
            except (ValueError, TypeError):
                raise AccountingDenied(Reason.SCOPE) from None
            async with self._repository.engine.connect() as connection:
                allowed = await connection.scalar(
                    select(gov.retained.c.id)
                    .join(
                        step_rows,
                        step_rows.c.provider_call_id == gov.retained.c.call_id,
                    )
                    .where(
                        gov.retained.c.id == retained_id,
                        step_rows.c.run_id == self._run_id,
                        step_rows.c.status == "SUCCEEDED",
                    )
                )
            if allowed is None:
                raise AccountingDenied(Reason.SCOPE)
            excerpt = await self.read_saved_evidence(
                self._attribution.experiment_id, retained_id, max_chars=1
            )
            references.append(excerpt.reference)
        return tuple(references)

    @asynccontextmanager
    async def dispatch_guard(self):
        """Keep cancellation and the consumed evidence rights stable during model use."""
        async with (
            self._steps.dispatch_scope(),
            self._repository.engine.begin() as connection,
        ):
            for call_id in sorted(self._transient_calls, key=str):
                row, config, authority, root = await self._repository._locked_call(
                    connection, call_id
                )
                grant, _ = await self._repository._rights(
                    connection,
                    config,
                    self._repository.clock(),
                    (row["grant_id"], row["grant_version"]),
                )
                if (
                    not authority["enabled"]
                    or not root["enabled"]
                    or not grant.outbound_use_permitted
                ):
                    raise AccountingDenied(Reason.RIGHTS)
            for reference in sorted(
                self._served.values(), key=lambda r: str(r.call_id)
            ):
                _row, config, authority, root = await self._repository._locked_call(
                    connection, reference.call_id
                )
                now = self._repository.clock()
                if (
                    not root["enabled"]
                    or not authority["enabled"]
                    or reference.expires_at is None
                    or reference.expires_at <= now
                ):
                    raise AccountingDenied(Reason.RIGHTS)
                grant, _ = await self._repository._rights(
                    connection,
                    config,
                    now,
                    (reference.grant_id, reference.grant_version),
                )
                if not grant.outbound_use_permitted:
                    raise AccountingDenied(Reason.RIGHTS)
            yield
