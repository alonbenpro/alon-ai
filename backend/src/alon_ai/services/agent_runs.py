"""Coordinate governed OpenAI runs, authority, persistence, and replay."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from alon_ai.agents.runtime import (
    AcceptedArtifact,
    AcceptedOperatorProfile,
    AcceptedRetainedEvidence,
    AcceptedSource,
    OpenAIExecution,
)
from alon_ai.agents.schemas.openai import (
    OpenAIProfile,
    Route,
    RoutingFacts,
    RoutingPolicy,
    canonical_json,
    sha256,
)
from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.db.repositories.openai_authority import OpenAIAuthorityStore
from alon_ai.db.repositories.openai_inputs import accepted_input as _accepted_input
from alon_ai.db.repositories.openai_run import (
    OpenAIRunConflict,
    OpenAIRunIntent,
    OpenAIRunOutcome,
    OpenAIRunRecord,
    OpenAIRunStore,
)
from alon_ai.integrations.openai import ResponsesTransport
from alon_ai.integrations.schemas.provider import (
    AgentActor,
    CallAttribution,
    Capability,
    ProviderErrorCode,
    Purpose,
    SafeRequestMetadata,
)
from alon_ai.policies.openai_inputs import _require_market_inputs
from alon_ai.policies.openai_pricing import _verify_pricing_bounds
from alon_ai.provider_usage.openai import ConfiguredResponsesAdapter
from alon_ai.provider_usage.schemas.accounting import CallState
from alon_ai.provider_usage.service import GovernedExecutor
from alon_ai.security.secrets import SecretStore


class OpenAIRuntime:
    def __init__(
        self,
        repository: GovernanceRepository,
        store: OpenAIRunStore,
        *,
        routes: RoutingPolicy,
        profiles: Mapping[UUID, OpenAIProfile],
        transport: ResponsesTransport,
        secrets: SecretStore,
    ):
        self.repository = repository
        self.store = store
        self.routes = routes
        self.profiles = MappingProxyType(dict(profiles))
        self.transport = transport
        self.secrets = secrets
        self.authority = OpenAIAuthorityStore(repository.engine)

    async def _replay(self, record: OpenAIRunRecord, route: Route) -> OpenAIExecution:
        receipt = await self.repository.get(record.call_id) if record.call_id else None
        # Successful original delivery does not imply we retained a replayable artifact.
        outcome = (
            OpenAIRunOutcome.RESULT_UNAVAILABLE
            if record.outcome is OpenAIRunOutcome.SUCCEEDED
            else record.outcome
        )
        return OpenAIExecution(route, outcome, receipt, None)

    async def run(
        self,
        attribution: CallAttribution,
        *,
        facts: RoutingFacts,
        sources: tuple[AcceptedSource, ...] = (),
        artifacts: tuple[AcceptedArtifact, ...] = (),
        operator_profiles: tuple[AcceptedOperatorProfile, ...] = (),
        retained_evidence: tuple[AcceptedRetainedEvidence, ...] = (),
        idempotency_key: UUID,
    ) -> OpenAIExecution:
        now = self.repository.clock()
        selection = self.routes.resolve(facts, scope=attribution.experiment_id)
        facts_hash = sha256(
            canonical_json(
                {
                    "needs_ai": facts.needs_ai,
                    "validated_escalation": facts.validated_escalation,
                    "premium_requested": facts.premium_requested,
                    "approval_id": str(facts.premium_authorization.authorization_id)
                    if facts.premium_authorization
                    else None,
                    "source_refs": [str(source.evidence_ref) for source in sources],
                    "artifacts": [
                        {
                            "ref": str(item.artifact.artifact_id),
                            "kind": item.artifact.kind.value,
                            "version": item.artifact.version,
                            "hash": item.artifact.content_hash,
                            "role": item.artifact.role,
                            "schema_version": item.schema_version,
                            "experiment": str(item.experiment_id),
                            "selection": str(item.selection_id)
                            if item.selection_id
                            else None,
                            "cycle": str(item.cycle_id) if item.cycle_id else None,
                            "attempt": str(item.attempt_id)
                            if item.attempt_id
                            else None,
                        }
                        for item in artifacts
                    ],
                    "operator_profiles": [
                        {
                            "ref": str(item.profile_id),
                            "version": item.version,
                            "hash": item.content_hash,
                            "experiment": str(item.experiment_id),
                            "schema_version": item.profile_schema_version,
                        }
                        for item in operator_profiles
                    ],
                    "retained_evidence": [
                        item.reference.model_dump(mode="json")
                        for item in retained_evidence
                    ],
                }
            )
        )
        await self.authority.bind_decision(
            idempotency_key,
            attribution,
            facts_hash,
            selection.route,
            selection.config_id,
            facts.premium_authorization.authorization_id
            if facts.premium_requested and facts.premium_authorization
            else None,
        )
        if selection.route is Route.NO_AI:
            return OpenAIExecution(Route.NO_AI, OpenAIRunOutcome.NO_AI, None, None)
        assert selection.config_id is not None
        profile = self.profiles[selection.config_id]
        _require_market_inputs(profile, sources, artifacts, operator_profiles)
        previous = await self.store.get(idempotency_key)
        if previous is not None:
            if (
                previous.config_id != profile.config_id
                or previous.config_version != profile.config_version
                or previous.experiment_id != attribution.experiment_id
                or previous.workflow_id != attribution.workflow_run_id
                or previous.operation_id != attribution.operation_run_id
                or previous.accepted_input_refs
                != tuple(source.evidence_ref for source in sources)
                + tuple(item.artifact.artifact_id for item in artifacts)
                + tuple(item.profile_id for item in operator_profiles)
                + tuple(
                    item.reference.retained_id
                    for item in retained_evidence
                    if item.reference.retained_id is not None
                )
                or previous.prompt_version != profile.prompt_version
                or previous.schema_version != profile.schema_version
                or previous.prompt_hash != sha256(profile.instructions)
                or previous.output_schema_hash != sha256(profile.schema_json)
                or previous.model_identifier != profile.model_identifier
                or previous.reasoning_effort != profile.reasoning_effort
            ):
                raise OpenAIRunConflict()
            recovered = await self.store.recover(idempotency_key)
            if recovered.outcome is not OpenAIRunOutcome.READY:
                return await self._replay(recovered, selection.route)
        self.routes.select(
            facts, scope=attribution.experiment_id, now=self.repository.clock()
        )
        config, prices = await self.repository.generation_config_and_prices(
            profile.config_id
        )
        if (
            config.version != profile.config_version
            or config.adapter_version != profile.adapter_version
            or config.model_identifier != profile.model_identifier
            or config.intended_use.capability is not Capability.OPENAI_GENERATE
            or config.intended_use.purpose is not Purpose.GENERATION
            or config.requested_count != 1
            or config.secret_handle is None
            or attribution.config_version != config.version
        ):
            raise PermissionError(
                "OpenAI run profile does not match immutable capability"
            )
        preflight = (
            await self.authority.snapshot(
                tuple(
                    (source.current_grant.grant_id, source.current_grant.version)
                    for source in sources
                )
                + tuple(
                    (item.reference.grant_id, item.reference.grant_version)
                    for item in retained_evidence
                    if item.reference.grant_id is not None
                    and item.reference.grant_version is not None
                ),
                None,
            )
            if retained_evidence
            else None
        )
        input_json = await _accepted_input(
            self.repository.engine,
            sources,
            artifacts,
            operator_profiles,
            retained_evidence,
            attribution.experiment_id,
            self.repository.clock(),
            grants=preflight.grants if preflight else None,
            events=preflight.events if preflight else (),
        )
        _verify_pricing_bounds(config, prices, profile, input_json)
        previous = await self.store.get(idempotency_key)
        intent = OpenAIRunIntent(
            idempotency_key=idempotency_key,
            config_id=config.id,
            config_version=config.version,
            experiment_id=attribution.experiment_id,
            workflow_id=attribution.workflow_run_id,
            operation_id=attribution.operation_run_id,
            agent_run_id=attribution.actor.agent_run_id
            if isinstance(attribution.actor, AgentActor)
            else None,
            prompt_version=profile.prompt_version,
            prompt_hash=sha256(profile.instructions),
            schema_version=profile.schema_version,
            output_schema_hash=sha256(profile.schema_json),
            model_identifier=profile.model_identifier,
            reasoning_effort=profile.reasoning_effort,
            accepted_input_refs=tuple(source.evidence_ref for source in sources)
            + tuple(item.artifact.artifact_id for item in artifacts)
            + tuple(item.profile_id for item in operator_profiles)
            + tuple(
                item.reference.retained_id
                for item in retained_evidence
                if item.reference.retained_id is not None
            ),
            input_hash=sha256(input_json),
            client_request_id=uuid5(NAMESPACE_URL, str(idempotency_key)),
            created_at=previous.created_at if previous else now,
        )
        try:
            record = await self.store.begin(intent)
        except OpenAIRunConflict:
            # Concurrent first use may race only on created_at. The store still
            # compares every identity field and will reject altered inputs.
            latest = await self.store.get(idempotency_key)
            if latest is None:
                raise
            record = await self.store.begin(
                intent.model_copy(update={"created_at": latest.created_at})
            )
        record = await self.store.recover(idempotency_key)
        if record.outcome is not OpenAIRunOutcome.READY:
            return await self._replay(record, selection.route)
        adapter = ConfiguredResponsesAdapter(
            profile=profile,
            input_json=input_json,
            client_request_id=intent.client_request_id,
            key=idempotency_key,
            prices=prices,
            transport=self.transport,
            clock=self.repository.clock,
            authority=self.authority,
            routes=self.routes,
            facts=facts,
            scope=attribution.experiment_id,
            sources=sources,
            artifacts=artifacts,
            operator_profiles=operator_profiles,
            retained_evidence=retained_evidence,
            engine=self.repository.engine,
        )
        executor = GovernedExecutor(
            self.repository,
            adapters={profile.adapter_version: adapter},
            secrets=self.secrets,
        )
        try:
            result = await executor.execute(
                attribution,
                SafeRequestMetadata(config_ref=config.id),
                idempotency_key=idempotency_key,
            )
        except asyncio.CancelledError:
            interrupted = await self.repository.receipt_for_idempotency_key(
                idempotency_key
            )
            await asyncio.shield(
                self.store.finish(
                    idempotency_key,
                    interrupted.call_id if interrupted else None,
                    OpenAIRunOutcome.CANCELLED,
                    None,
                )
            )
            raise
        except Exception:
            interrupted = await self.repository.receipt_for_idempotency_key(
                idempotency_key
            )
            outcome = (
                OpenAIRunOutcome.UNCERTAIN
                if interrupted is not None
                and interrupted.state not in {CallState.RESERVED, CallState.RELEASED}
                else OpenAIRunOutcome.FAILED
            )
            await self.store.finish(
                idempotency_key,
                interrupted.call_id if interrupted else None,
                outcome,
                None,
            )
            raise
        if adapter.parsed is None:
            if result.error is None and result.receipt.state is not CallState.RELEASED:
                # Another caller owns this idempotency key's dispatch. It may
                # still be processing; only its adapter can close this run.
                return await self._replay(
                    await self.store.recover(idempotency_key), selection.route
                )
            outcome = (
                OpenAIRunOutcome.TIMEOUT
                if result.error is ProviderErrorCode.TIMEOUT
                else OpenAIRunOutcome.FAILED
                if result.receipt.state is CallState.RELEASED
                or result.error is ProviderErrorCode.DENIED
                else OpenAIRunOutcome.UNCERTAIN
            )
            output = None
            output_hash = None
        else:
            outcome = OpenAIRunOutcome(adapter.parsed.outcome)
            if (
                outcome is OpenAIRunOutcome.SUCCEEDED
                and result.receipt.state is not CallState.FINAL
            ):
                outcome = OpenAIRunOutcome.RESULT_UNAVAILABLE
            output = (
                adapter.parsed.output
                if result.receipt.state is CallState.FINAL
                else None
            )
            output_hash = adapter.parsed.output_hash
        try:
            await self.store.finish(
                idempotency_key, result.receipt.call_id, outcome, output_hash
            )
        except OpenAIRunConflict:
            # A concurrent replay may have closed the finalized ledger's lost-output
            # window. Its conservative terminal result takes precedence.
            recovered = await self.store.get(idempotency_key)
            if (
                recovered is None
                or recovered.call_id != result.receipt.call_id
                or recovered.outcome is not OpenAIRunOutcome.RESULT_UNAVAILABLE
            ):
                raise
            return await self._replay(recovered, selection.route)
        return OpenAIExecution(selection.route, outcome, result.receipt, output)
