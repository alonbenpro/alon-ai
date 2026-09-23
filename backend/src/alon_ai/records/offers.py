"""Transactional commands for exact offer design and acceptance records."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.accounting.repository import lock_experiment
from alon_ai.records import offer_schema as s
from alon_ai.records import schema as records
from alon_ai.records.models import (
    ArtifactInput,
    ArtifactKind,
    CycleReceipt,
    ProductRecordsDenied,
)
from alon_ai.records.offer_models import (
    INITIAL_OUTREACH_POLICY,
    OFFER_FIELD_EVIDENCE_ROLES,
    OPERATOR_FIELD_CONSTRAINTS,
    PROTECTED_OFFER_FIELDS,
    REQUIRED_QUALIFICATION_CATEGORIES,
    REQUIRED_RESEARCH_ROLES,
    CommercialEnvelopeReceipt,
    CommercialEnvelopeRequest,
    InputBundleReceipt,
    OfferAcceptanceReceipt,
    OfferAcceptanceRequest,
    OfferDesignDecisionReceipt,
    OfferDesignDecisionRequest,
    OfferDesignStartReceipt,
    OfferDesignStartRequest,
    OfferGapRequest,
    OfferIdeaRefinementReturnReceipt,
    OfferIdeaRefinementReturnRequest,
    OfferProposalReceipt,
    OfferTargetedResearchReturnReceipt,
    OfferTargetedResearchReturnRequest,
)
from alon_ai.records.repository import (
    _complete,
    _existing,
    _request_hash,
    _supplied_budget_block_reason,
    safe_records,
)


async def _require_active_offer_design_workflow(
    connection: AsyncConnection,
    *,
    workflow_id: str | None,
    command_key: UUID,
    request_hash: str,
) -> None:
    """Make DBOS cancellation and a business command share one lock boundary."""
    if workflow_id is None:
        return
    binding = (
        (
            await connection.execute(
                select(s.offer_design_workflow_bindings)
                .where(
                    s.offer_design_workflow_bindings.c.dbos_workflow_id == workflow_id,
                    s.offer_design_workflow_bindings.c.business_command_key
                    == command_key,
                    s.offer_design_workflow_bindings.c.request_hash == request_hash,
                )
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    if binding is None or binding["delivery_state"] not in {
        "STARTED",
        "BUSINESS_COMMITTED",
        "RECEIPT_DELIVERED",
        "RUNTIME_COMPLETED",
    }:
        raise ProductRecordsDenied("WORKFLOW_NOT_EXECUTABLE")


async def _exact_offer_validation_lineage(
    connection: AsyncConnection,
    *,
    validation_id: UUID,
    proposal_artifact_id: UUID,
    package_artifact_id: UUID,
    profile_artifact_id: UUID,
    policy_artifact_id: UUID,
) -> bool:
    expected = {
        "OFFER_DESIGN_PROPOSAL": proposal_artifact_id,
        "OFFER_PACKAGE": package_artifact_id,
        "OFFER_QUALIFICATION_PROFILE": profile_artifact_id,
        "INITIAL_OUTREACH_POLICY": policy_artifact_id,
    }
    links = set(
        (
            await connection.execute(
                select(
                    records.artifact_links.c.role, records.artifact_links.c.producer_id
                ).where(
                    records.artifact_links.c.consumer_id == validation_id,
                    records.artifact_links.c.role.in_(expected),
                )
            )
        ).all()
    )
    if links != set(expected.items()):
        return False
    for role in expected:
        count = await connection.scalar(
            select(func.count())
            .select_from(records.artifact_links)
            .where(
                records.artifact_links.c.consumer_id == validation_id,
                records.artifact_links.c.role == role,
            )
        )
        if count != 1:
            return False
    return True


async def _exact_artifact(connection: AsyncConnection, value: ArtifactInput):
    row = (
        (
            await connection.execute(
                select(records.artifacts).where(
                    records.artifacts.c.id == value.artifact_id,
                    records.artifacts.c.kind == value.kind,
                    records.artifacts.c.version == value.version,
                    records.artifacts.c.content_hash == value.content_hash,
                )
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("EXACT_ARTIFACT")
    if await connection.scalar(
        select(records.artifacts.c.id).where(
            records.artifacts.c.logical_id == row["logical_id"],
            records.artifacts.c.version > row["version"],
        )
    ) or await connection.scalar(
        select(records.artifact_dispositions.c.id).where(
            records.artifact_dispositions.c.artifact_id == row["id"],
            records.artifact_dispositions.c.disposition == "SUPERSEDED",
        )
    ):
        raise ProductRecordsDenied("STALE_INPUT")
    return row


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


class OfferRecordsRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.clock = clock

    async def start_offer_design(
        self,
        request: OfferDesignStartRequest,
        *,
        command_key: UUID,
        workflow_id: str | None = None,
    ) -> OfferDesignStartReceipt:
        """Begin one pinned Offer Design run after a committed proceed verdict."""
        async with self.engine.begin() as connection:
            bundle_artifact = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == request.input_bundle.artifact_id,
                            records.artifacts.c.kind == request.input_bundle.kind,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if bundle_artifact is None:
                raise ProductRecordsDenied("EXACT_ARTIFACT")
            await lock_experiment(connection, bundle_artifact["experiment_id"])
            request_hash = _request_hash(request=request)
            await _require_active_offer_design_workflow(
                connection,
                workflow_id=workflow_id,
                command_key=command_key,
                request_hash=request_hash,
            )
            old = await _existing(
                connection, command_key, "START_OFFER_DESIGN", request_hash
            )
            if old:
                run = (
                    (
                        await connection.execute(
                            select(s.offer_design_runs).where(
                                s.offer_design_runs.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                transition = await connection.scalar(
                    select(records.cycle_transitions.c.id).where(
                        records.cycle_transitions.c.offer_design_run_id == run["id"],
                        records.cycle_transitions.c.command_id == old["id"],
                    )
                )
                if transition is None:
                    raise ProductRecordsDenied("OFFER_RUN_LINEAGE")
                return OfferDesignStartReceipt(
                    command_id=old["id"],
                    result_id=run["id"],
                    id=run["id"],
                    cycle_id=run["cycle_id"],
                    bundle_id=run["bundle_id"],
                    envelope_id=run["envelope_id"],
                    transition_id=transition,
                )
            bundle_artifact = await _exact_artifact(connection, request.input_bundle)
            envelope_artifact = await _exact_artifact(connection, request.envelope)
            scope_artifact = await _exact_artifact(connection, request.scope_estimate)
            if request.input_bundle.kind is not ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE:
                raise ProductRecordsDenied("BUNDLE_KIND")
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == request.verdict_id,
                            records.verdicts.c.experiment_id
                            == bundle_artifact["experiment_id"],
                            records.verdicts.c.verdict == "PROCEED_TO_OFFER",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if verdict is None:
                raise ProductRecordsDenied("PROCEED_REQUIRED")
            state = (
                (
                    await connection.execute(
                        select(records.cycle_states)
                        .where(records.cycle_states.c.cycle_id == verdict["cycle_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if state["state"] != "PROCEED_TO_OFFER":
                raise ProductRecordsDenied("STALE_PROCEED")
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(
                            s.offer_bundles.c.artifact_id
                            == request.input_bundle.artifact_id,
                            s.offer_bundles.c.verdict_id == request.verdict_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            envelope = (
                (
                    await connection.execute(
                        select(s.commercial_envelopes).where(
                            s.commercial_envelopes.c.artifact_id
                            == envelope_artifact["id"],
                            s.commercial_envelopes.c.artifact_kind
                            == request.envelope.kind,
                            s.commercial_envelopes.c.artifact_version
                            == request.envelope.version,
                            s.commercial_envelopes.c.artifact_hash
                            == request.envelope.content_hash,
                            s.commercial_envelopes.c.bundle_id
                            == (bundle["id"] if bundle else None),
                            s.commercial_envelopes.c.status == "READY",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            prompt = await _exact_artifact(connection, request.prompt_configuration)
            report = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == verdict["report_artifact_id"]
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                bundle is None
                or envelope is None
                or report is None
                or request.envelope.kind is not ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE
                or envelope_artifact["experiment_id"] != bundle["experiment_id"]
                or request.scope_estimate.artifact_id != envelope["scope_artifact_id"]
                or scope_artifact["experiment_id"] != bundle["experiment_id"]
                or prompt["experiment_id"] != bundle["experiment_id"]
                or request.prompt_configuration.kind
                is not ArtifactKind.OUTREACH_PROMPT_CONFIGURATION
                or not await connection.scalar(
                    select(records.artifacts.c.id).where(
                        records.artifacts.c.id == request.scope_estimate.artifact_id,
                        records.artifacts.c.kind
                        == ArtifactKind.DELIVERY_SCOPE_ESTIMATE,
                        records.artifacts.c.experiment_id == bundle["experiment_id"],
                        records.artifacts.c.content_hash
                        == request.scope_estimate.content_hash,
                    )
                )
                or await connection.scalar(
                    select(records.artifacts.c.id).where(
                        records.artifacts.c.logical_id == report["logical_id"],
                        records.artifacts.c.version > report["version"],
                    )
                )
                or await connection.scalar(
                    select(records.artifact_dispositions.c.id).where(
                        records.artifact_dispositions.c.artifact_id == report["id"],
                        records.artifact_dispositions.c.disposition == "SUPERSEDED",
                    )
                )
                or not await connection.scalar(
                    select(records.experiments.c.id).where(
                        records.experiments.c.id == bundle["experiment_id"]
                    )
                )
                or not await connection.scalar(
                    select(records.operator_profiles.c.id).where(
                        records.operator_profiles.c.operator_id == request.started_by
                    )
                )
                or not await connection.scalar(
                    select(records.artifacts.c.id).where(
                        records.artifacts.c.id == request.input_bundle.artifact_id,
                        records.artifacts.c.experiment_id == bundle["experiment_id"],
                    )
                )
                or not await connection.scalar(
                    select(records.artifacts.c.id).where(
                        records.artifacts.c.id == request.envelope.artifact_id,
                        records.artifacts.c.experiment_id == bundle["experiment_id"],
                    )
                )
                or not await connection.scalar(
                    select(records.artifacts.c.id).where(
                        records.artifacts.c.id
                        == request.prompt_configuration.artifact_id,
                        records.artifacts.c.version
                        == request.prompt_configuration.version,
                        records.artifacts.c.content_hash
                        == request.prompt_configuration.content_hash,
                    )
                )
            ):
                raise ProductRecordsDenied("STALE_OFFER_INPUT")
            config = await connection.scalar(
                select(gov.configs.c.id).where(
                    gov.configs.c.id == request.model_config_id,
                    gov.configs.c.workflow_id == request.model_config_workflow_id,
                    gov.configs.c.version == request.model_config_version,
                )
            )
            if config is None:
                raise ProductRecordsDenied("STALE_MODEL_CONFIG")
            acceptance = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == verdict["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            run_id, transition_id = uuid4(), uuid4()
            now = self.clock()
            await connection.execute(
                insert(s.offer_design_runs).values(
                    id=run_id,
                    experiment_id=bundle["experiment_id"],
                    cycle_id=verdict["cycle_id"],
                    verdict_id=verdict["id"],
                    bundle_id=bundle["id"],
                    envelope_id=envelope["id"],
                    prompt_artifact_id=request.prompt_configuration.artifact_id,
                    prompt_version=request.prompt_configuration.version,
                    prompt_hash=request.prompt_configuration.content_hash,
                    model_config_id=request.model_config_id,
                    model_config_workflow_id=request.model_config_workflow_id,
                    model_config_version=request.model_config_version,
                    started_by=request.started_by,
                    created_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=bundle["experiment_id"],
                kind="START_OFFER_DESIGN",
                request_hash=request_hash,
                result_type="OFFER_DESIGN_RUN",
                result_id=run_id,
                now=now,
            )
            await connection.execute(
                insert(records.cycle_transitions).values(
                    id=transition_id,
                    experiment_id=bundle["experiment_id"],
                    cycle_id=verdict["cycle_id"],
                    ordinal=state["transition_ordinal"] + 1,
                    from_state="PROCEED_TO_OFFER",
                    to_state="OFFER_DESIGN",
                    idea_acceptance_id=acceptance["id"],
                    idea_artifact_id=acceptance["artifact_id"],
                    idea_kind=acceptance["artifact_kind"],
                    idea_version=acceptance["artifact_version"],
                    idea_hash=acceptance["artifact_hash"],
                    research_attempt_id=verdict["attempt_id"],
                    verdict_id=verdict["id"],
                    offer_design_run_id=run_id,
                    offer_design_decision_id=None,
                    command_id=command_id,
                    created_at=now,
                )
            )
            advanced = await connection.execute(
                update(records.cycle_states)
                .where(
                    records.cycle_states.c.cycle_id == verdict["cycle_id"],
                    records.cycle_states.c.state == "PROCEED_TO_OFFER",
                    records.cycle_states.c.transition_ordinal
                    == state["transition_ordinal"],
                )
                .values(
                    state="OFFER_DESIGN",
                    transition_ordinal=state["transition_ordinal"] + 1,
                    last_transition_id=transition_id,
                    updated_at=now,
                )
            )
            if advanced.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            return OfferDesignStartReceipt(
                command_id=command_id,
                result_id=run_id,
                id=run_id,
                cycle_id=verdict["cycle_id"],
                bundle_id=bundle["id"],
                envelope_id=envelope["id"],
                transition_id=transition_id,
            )

    @safe_records
    async def decide_offer_design(
        self,
        request: OfferDesignDecisionRequest,
        *,
        command_key: UUID,
        workflow_id: str | None = None,
    ) -> OfferDesignDecisionReceipt:
        """Persist one non-accepting terminal Offer Design decision."""
        if request.outcome == "ACCEPT":
            raise ProductRecordsDenied("ACCEPT_REQUIRES_PACKAGE")
        if request.outcome == "TARGETED_RESEARCH_REQUIRED":
            raise ProductRecordsDenied("TARGETED_RETURN_REQUIRES_PLAN")
        async with self.engine.begin() as connection:
            run = (
                (
                    await connection.execute(
                        select(s.offer_design_runs).where(
                            s.offer_design_runs.c.id == request.run_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, run["experiment_id"])
            request_hash = _request_hash(request=request)
            await _require_active_offer_design_workflow(
                connection,
                workflow_id=workflow_id,
                command_key=command_key,
                request_hash=request_hash,
            )
            old = await _existing(
                connection, command_key, "DECIDE_OFFER_DESIGN", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.offer_design_decisions).where(
                                s.offer_design_decisions.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                transition_id = await connection.scalar(
                    select(records.cycle_transitions.c.id).where(
                        records.cycle_transitions.c.offer_design_decision_id
                        == row["id"],
                        records.cycle_transitions.c.command_id == old["id"],
                    )
                )
                if transition_id is None:
                    raise ProductRecordsDenied("OFFER_DECISION_LINEAGE")
                return OfferDesignDecisionReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    run_id=row["run_id"],
                    outcome=row["outcome"],
                    transition_id=transition_id,
                )
            state = (
                (
                    await connection.execute(
                        select(records.cycle_states)
                        .where(records.cycle_states.c.cycle_id == run["cycle_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if state["state"] != "OFFER_DESIGN":
                raise ProductRecordsDenied("INVALID_STATE")
            artifact = await _exact_artifact(connection, request.decision_artifact)
            if artifact["experiment_id"] != run["experiment_id"]:
                raise ProductRecordsDenied("DECISION_LINEAGE")
            target = {
                "IDEA_REFINEMENT_RECOMMENDED": "WAITING_FOR_OPERATOR_INPUT",
                "WAITING_FOR_OPERATOR_INPUT": "WAITING_FOR_OPERATOR_INPUT",
            }[request.outcome]
            decision_id, transition_id = uuid4(), uuid4()
            now = self.clock()
            await connection.execute(
                insert(s.offer_design_decisions).values(
                    id=decision_id,
                    experiment_id=run["experiment_id"],
                    run_id=run["id"],
                    artifact_id=request.decision_artifact.artifact_id,
                    artifact_kind=request.decision_artifact.kind,
                    artifact_version=request.decision_artifact.version,
                    artifact_hash=request.decision_artifact.content_hash,
                    outcome=request.outcome,
                    operator_id=request.operator_id,
                    created_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=run["experiment_id"],
                kind="DECIDE_OFFER_DESIGN",
                request_hash=request_hash,
                result_type="OFFER_DESIGN_DECISION",
                result_id=decision_id,
                now=now,
            )
            acceptance = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == run["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == run["verdict_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            await connection.execute(
                insert(records.cycle_transitions).values(
                    id=transition_id,
                    experiment_id=run["experiment_id"],
                    cycle_id=run["cycle_id"],
                    ordinal=state["transition_ordinal"] + 1,
                    from_state="OFFER_DESIGN",
                    to_state=target,
                    idea_acceptance_id=acceptance["id"],
                    idea_artifact_id=acceptance["artifact_id"],
                    idea_kind=acceptance["artifact_kind"],
                    idea_version=acceptance["artifact_version"],
                    idea_hash=acceptance["artifact_hash"],
                    research_attempt_id=verdict["attempt_id"],
                    verdict_id=verdict["id"],
                    offer_design_run_id=run["id"],
                    offer_design_decision_id=decision_id,
                    command_id=command_id,
                    created_at=now,
                )
            )
            advanced = await connection.execute(
                update(records.cycle_states)
                .where(
                    records.cycle_states.c.cycle_id == run["cycle_id"],
                    records.cycle_states.c.state == "OFFER_DESIGN",
                    records.cycle_states.c.transition_ordinal
                    == state["transition_ordinal"],
                )
                .values(
                    state=target,
                    transition_ordinal=state["transition_ordinal"] + 1,
                    last_transition_id=transition_id,
                    updated_at=now,
                )
            )
            if advanced.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            return OfferDesignDecisionReceipt(
                command_id=command_id,
                result_id=decision_id,
                id=decision_id,
                run_id=run["id"],
                outcome=request.outcome,
                transition_id=transition_id,
            )

    @safe_records
    async def return_for_targeted_research(
        self,
        request: OfferTargetedResearchReturnRequest,
        *,
        command_key: UUID,
        workflow_id: str | None = None,
    ) -> OfferTargetedResearchReturnReceipt:
        """Atomically return one unaccepted Offer Design run to scoped research."""
        async with self.engine.begin() as connection:
            run = (
                (
                    await connection.execute(
                        select(s.offer_design_runs).where(
                            s.offer_design_runs.c.id == request.run_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, run["experiment_id"])
            request_hash = _request_hash(request=request)
            await _require_active_offer_design_workflow(
                connection,
                workflow_id=workflow_id,
                command_key=command_key,
                request_hash=request_hash,
            )
            old = await _existing(
                connection, command_key, "RETURN_FOR_TARGETED_RESEARCH", request_hash
            )
            if old:
                decision = (
                    (
                        await connection.execute(
                            select(s.offer_design_decisions).where(
                                s.offer_design_decisions.c.id == old["result_id"],
                                s.offer_design_decisions.c.run_id == run["id"],
                                s.offer_design_decisions.c.outcome
                                == "TARGETED_RESEARCH_REQUIRED",
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                gap_id = await connection.scalar(
                    select(s.offer_gap_briefs.c.id).where(
                        s.offer_gap_briefs.c.proposal_id == request.proposal_id,
                        s.offer_gap_briefs.c.bundle_id == run["bundle_id"],
                        s.offer_gap_briefs.c.artifact_id
                        == request.gap.artifact.artifact_id,
                        s.offer_gap_briefs.c.artifact_version
                        == request.gap.artifact.version,
                        s.offer_gap_briefs.c.artifact_hash
                        == request.gap.artifact.content_hash,
                    )
                )
                returned = (
                    (
                        await connection.execute(
                            select(records.returns).where(
                                records.returns.c.experiment_id == run["experiment_id"],
                                records.returns.c.from_cycle_id == run["cycle_id"],
                                records.returns.c.verdict_id == run["verdict_id"],
                                records.returns.c.kind == "OFFER_GAP",
                                records.returns.c.feedback_artifact_id
                                == request.gap.artifact.artifact_id,
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if decision is None or gap_id is None or returned is None:
                    raise ProductRecordsDenied("TARGETED_RETURN_LINEAGE")
                child = returned["to_cycle_id"]
                parent_transition = await connection.scalar(
                    select(records.cycle_transitions.c.id).where(
                        records.cycle_transitions.c.command_id == old["id"],
                        records.cycle_transitions.c.cycle_id == run["cycle_id"],
                        records.cycle_transitions.c.from_state == "OFFER_DESIGN",
                        records.cycle_transitions.c.to_state
                        == "RETURN_FOR_TARGETED_RESEARCH",
                        records.cycle_transitions.c.offer_design_run_id == run["id"],
                        records.cycle_transitions.c.offer_design_decision_id
                        == decision["id"],
                        records.cycle_transitions.c.verdict_id == run["verdict_id"],
                    )
                )
                child_transition = (
                    (
                        await connection.execute(
                            select(records.cycle_transitions).where(
                                records.cycle_transitions.c.command_id == old["id"],
                                records.cycle_transitions.c.cycle_id == child,
                                records.cycle_transitions.c.from_state
                                == "IDEA_REFINEMENT",
                                records.cycle_transitions.c.to_state
                                == "MARKET_RESEARCH",
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if parent_transition is None or child_transition is None:
                    raise ProductRecordsDenied("TARGETED_RETURN_LINEAGE")
                attempt = child_transition["research_attempt_id"]
                if not await connection.scalar(
                    select(records.research_attempts.c.id).where(
                        records.research_attempts.c.id == attempt,
                        records.research_attempts.c.cycle_id == child,
                        records.research_attempts.c.ordinal == 1,
                    )
                ):
                    raise ProductRecordsDenied("TARGETED_RETURN_LINEAGE")
                return OfferTargetedResearchReturnReceipt(
                    command_id=old["id"],
                    result_id=decision["id"],
                    id=decision["id"],
                    run_id=run["id"],
                    decision_id=decision["id"],
                    child_cycle_id=child,
                    research_attempt_id=attempt,
                    parent_transition_id=parent_transition,
                    child_transition_id=child_transition["id"],
                )
            existing_acceptance = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == run["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            if await connection.scalar(
                select(records.returns.c.id).where(
                    records.returns.c.experiment_id == run["experiment_id"],
                    records.returns.c.kind == "OFFER_GAP",
                    records.returns.c.applicable_scope_id
                    == existing_acceptance["artifact_id"],
                )
            ):
                raise ProductRecordsDenied("OFFER_TARGETED_RETURN_LIMIT")
            state = (
                (
                    await connection.execute(
                        select(records.cycle_states)
                        .where(records.cycle_states.c.cycle_id == run["cycle_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if state["state"] != "OFFER_DESIGN":
                raise ProductRecordsDenied("INVALID_STATE")
            if request.gap.proposal_id != request.proposal_id:
                raise ProductRecordsDenied("GAP_PROPOSAL_MISMATCH")
            named_fields = set(request.gap.missing_fields) | set(
                request.gap.contradictory_fields
            )
            if not named_fields.issubset(PROTECTED_OFFER_FIELDS):
                raise ProductRecordsDenied("UNNAMED_OFFER_GAP")
            proposal = (
                (
                    await connection.execute(
                        select(s.offer_proposals).where(
                            s.offer_proposals.c.id == request.proposal_id,
                            s.offer_proposals.c.offer_design_run_id == run["id"],
                            s.offer_proposals.c.experiment_id == run["experiment_id"],
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if proposal is None or await connection.scalar(
                select(s.offer_packages.c.id).where(
                    s.offer_packages.c.proposal_id == request.proposal_id
                )
            ):
                raise ProductRecordsDenied("UNACCEPTED_PROPOSAL_REQUIRED")
            if await connection.scalar(
                select(s.offer_proposal_invalidations.c.proposal_id).where(
                    s.offer_proposal_invalidations.c.proposal_id == request.proposal_id
                )
            ):
                raise ProductRecordsDenied("PROPOSAL_INVALIDATED")
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(
                            s.offer_bundles.c.id == proposal["bundle_id"],
                            s.offer_bundles.c.experiment_id == run["experiment_id"],
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if bundle is None:
                raise ProductRecordsDenied("TARGETED_RETURN_LINEAGE")
            gap = await _exact_artifact(connection, request.gap.artifact)
            plan = await _exact_artifact(connection, request.plan)
            decision_artifact = await _exact_artifact(
                connection, request.decision_artifact
            )
            if (
                request.gap.artifact.kind is not ArtifactKind.OFFER_RESEARCH_GAP_BRIEF
                or request.plan.kind is not ArtifactKind.RESEARCH_PLAN
                or gap["experiment_id"] != run["experiment_id"]
                or plan["experiment_id"] != run["experiment_id"]
                or decision_artifact["experiment_id"] != run["experiment_id"]
                or plan["workflow_id"] != request.budget.workflow_id
            ):
                raise ProductRecordsDenied("TARGETED_RETURN_LINEAGE")
            if not await connection.scalar(
                select(records.artifact_dispositions.c.id).where(
                    records.artifact_dispositions.c.artifact_id == gap["id"],
                    records.artifact_dispositions.c.disposition == "ACCEPTED",
                )
            ):
                raise ProductRecordsDenied("UNACCEPTED_OFFER_GAP")
            acceptance = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == run["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            plan_links = set(
                (
                    await connection.execute(
                        select(
                            records.artifact_links.c.role,
                            records.artifact_links.c.producer_id,
                        ).where(
                            records.artifact_links.c.consumer_id
                            == request.plan.artifact_id
                        )
                    )
                ).all()
            )
            if ("ACCEPTED_IDEA", acceptance["artifact_id"]) not in plan_links or (
                "RETURN_FEEDBACK",
                gap["id"],
            ) not in plan_links:
                raise ProductRecordsDenied("TARGETED_PLAN_LINEAGE")
            now = self.clock()
            block_reason = await _supplied_budget_block_reason(
                connection, run["experiment_id"], request.budget, now
            )
            if block_reason is not None:
                raise ProductRecordsDenied(block_reason)
            parent = (
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.id == run["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == run["verdict_id"],
                            records.verdicts.c.verdict == "PROCEED_TO_OFFER",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if verdict is None:
                raise ProductRecordsDenied("STALE_PROCEED")
            decision_id, gap_id = uuid4(), uuid4()
            child_cycle_id, return_id, child_acceptance_id = uuid4(), uuid4(), uuid4()
            attempt_id, parent_transition_id, child_transition_id = (
                uuid4(),
                uuid4(),
                uuid4(),
            )
            await connection.execute(
                insert(s.offer_design_decisions).values(
                    id=decision_id,
                    experiment_id=run["experiment_id"],
                    run_id=run["id"],
                    artifact_id=request.decision_artifact.artifact_id,
                    artifact_kind=request.decision_artifact.kind,
                    artifact_version=request.decision_artifact.version,
                    artifact_hash=request.decision_artifact.content_hash,
                    outcome="TARGETED_RESEARCH_REQUIRED",
                    operator_id=request.operator_id,
                    created_at=now,
                )
            )
            await connection.execute(
                insert(s.offer_gap_briefs).values(
                    id=gap_id,
                    experiment_id=run["experiment_id"],
                    artifact_id=request.gap.artifact.artifact_id,
                    artifact_kind=request.gap.artifact.kind,
                    artifact_version=request.gap.artifact.version,
                    artifact_hash=request.gap.artifact.content_hash,
                    proposal_id=proposal["id"],
                    bundle_id=proposal["bundle_id"],
                    missing_fields=list(request.gap.missing_fields),
                    contradictory_fields=list(request.gap.contradictory_fields),
                    required_source_types=list(request.gap.required_source_types),
                    targeted_questions=list(request.gap.targeted_questions),
                    created_at=now,
                )
            )
            await connection.execute(
                insert(s.offer_proposal_invalidations).values(
                    proposal_id=proposal["id"],
                    experiment_id=run["experiment_id"],
                    superseding_bundle_id=None,
                    offer_gap_brief_id=gap_id,
                    reason="OFFER_GAP_RETURN",
                    created_at=now,
                )
            )
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(records.cycles)
                    .where(records.cycles.c.experiment_id == run["experiment_id"])
                )
                or 0
            ) + 1
            await connection.execute(
                insert(records.cycles).values(
                    id=child_cycle_id,
                    experiment_id=run["experiment_id"],
                    ordinal=ordinal,
                    parent_cycle_id=parent["id"],
                    idea_mode=parent["idea_mode"],
                    selection_id=parent["selection_id"],
                    purpose="OFFER_GAP_RETURN",
                    episode_id=parent["episode_id"],
                    seed_artifact_id=parent["seed_artifact_id"],
                    seed_kind=parent["seed_kind"],
                    seed_version=parent["seed_version"],
                    seed_hash=parent["seed_hash"],
                    created_at=now,
                )
            )
            await connection.execute(
                insert(records.returns).values(
                    id=return_id,
                    experiment_id=run["experiment_id"],
                    from_cycle_id=parent["id"],
                    verdict_id=verdict["id"],
                    to_cycle_id=child_cycle_id,
                    ordinal=1,
                    kind="OFFER_GAP",
                    applicable_scope_id=acceptance["artifact_id"],
                    idea_artifact_id=acceptance["artifact_id"],
                    offer_input_bundle_id=bundle["artifact_id"],
                    feedback_artifact_id=request.gap.artifact.artifact_id,
                    feedback_kind=request.gap.artifact.kind,
                    feedback_version=request.gap.artifact.version,
                    feedback_hash=request.gap.artifact.content_hash,
                    created_at=now,
                )
            )
            await connection.execute(
                insert(records.idea_acceptances).values(
                    id=child_acceptance_id,
                    experiment_id=run["experiment_id"],
                    cycle_id=child_cycle_id,
                    artifact_id=acceptance["artifact_id"],
                    artifact_kind=acceptance["artifact_kind"],
                    artifact_version=acceptance["artifact_version"],
                    artifact_hash=acceptance["artifact_hash"],
                    pivot_approval_id=None,
                    accepted_by=request.accepted_by,
                    accepted_at=now,
                )
            )
            await connection.execute(
                insert(records.research_cycle_budgets).values(
                    cycle_id=child_cycle_id,
                    experiment_id=run["experiment_id"],
                    **request.budget.model_dump(exclude={"schema_version"}),
                    created_at=now,
                )
            )
            await connection.execute(
                insert(records.research_attempts).values(
                    id=attempt_id,
                    experiment_id=run["experiment_id"],
                    cycle_id=child_cycle_id,
                    ordinal=1,
                    plan_artifact_id=request.plan.artifact_id,
                    plan_kind=request.plan.kind,
                    plan_version=request.plan.version,
                    plan_hash=request.plan.content_hash,
                    created_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=run["experiment_id"],
                kind="RETURN_FOR_TARGETED_RESEARCH",
                request_hash=request_hash,
                result_type="OFFER_DESIGN_DECISION",
                result_id=decision_id,
                now=now,
            )
            for (
                transition_id,
                cycle_id,
                ordinal_value,
                from_state,
                to_state,
                idea_id,
                attempt,
            ) in (
                (
                    parent_transition_id,
                    parent["id"],
                    state["transition_ordinal"] + 1,
                    "OFFER_DESIGN",
                    "RETURN_FOR_TARGETED_RESEARCH",
                    acceptance["id"],
                    verdict["attempt_id"],
                ),
                (
                    child_transition_id,
                    child_cycle_id,
                    1,
                    "IDEA_REFINEMENT",
                    "MARKET_RESEARCH",
                    child_acceptance_id,
                    attempt_id,
                ),
            ):
                await connection.execute(
                    insert(records.cycle_transitions).values(
                        id=transition_id,
                        experiment_id=run["experiment_id"],
                        cycle_id=cycle_id,
                        ordinal=ordinal_value,
                        from_state=from_state,
                        to_state=to_state,
                        idea_acceptance_id=idea_id,
                        idea_artifact_id=acceptance["artifact_id"],
                        idea_kind=acceptance["artifact_kind"],
                        idea_version=acceptance["artifact_version"],
                        idea_hash=acceptance["artifact_hash"],
                        research_attempt_id=attempt,
                        verdict_id=verdict["id"] if cycle_id == parent["id"] else None,
                        offer_design_run_id=run["id"]
                        if cycle_id == parent["id"]
                        else None,
                        offer_design_decision_id=decision_id
                        if cycle_id == parent["id"]
                        else None,
                        command_id=command_id,
                        created_at=now,
                    )
                )
            parent_updated = await connection.execute(
                update(records.cycle_states)
                .where(
                    records.cycle_states.c.cycle_id == parent["id"],
                    records.cycle_states.c.state == "OFFER_DESIGN",
                    records.cycle_states.c.transition_ordinal
                    == state["transition_ordinal"],
                )
                .values(
                    state="RETURN_FOR_TARGETED_RESEARCH",
                    transition_ordinal=state["transition_ordinal"] + 1,
                    last_transition_id=parent_transition_id,
                    updated_at=now,
                )
            )
            if parent_updated.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            child_updated = await connection.execute(
                update(records.cycle_states)
                .where(
                    records.cycle_states.c.cycle_id == child_cycle_id,
                    records.cycle_states.c.state == "IDEA_REFINEMENT",
                )
                .values(
                    state="MARKET_RESEARCH",
                    transition_ordinal=1,
                    last_transition_id=child_transition_id,
                    updated_at=now,
                )
            )
            if child_updated.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            return OfferTargetedResearchReturnReceipt(
                command_id=command_id,
                result_id=decision_id,
                id=decision_id,
                run_id=run["id"],
                decision_id=decision_id,
                child_cycle_id=child_cycle_id,
                research_attempt_id=attempt_id,
                parent_transition_id=parent_transition_id,
                child_transition_id=child_transition_id,
            )

    @safe_records
    async def confirm_offer_idea_refinement(
        self,
        request: OfferIdeaRefinementReturnRequest,
        *,
        command_key: UUID,
        workflow_id: str | None = None,
    ) -> OfferIdeaRefinementReturnReceipt:
        """Create an operator-confirmed next IdeaBrief; never infer one."""
        async with self.engine.begin() as connection:
            run = (
                (
                    await connection.execute(
                        select(s.offer_design_runs).where(
                            s.offer_design_runs.c.id == request.run_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, run["experiment_id"])
            request_hash = _request_hash(request=request)
            await _require_active_offer_design_workflow(
                connection,
                workflow_id=workflow_id,
                command_key=command_key,
                request_hash=request_hash,
            )
            old = await _existing(
                connection, command_key, "CONFIRM_OFFER_IDEA_REFINEMENT", request_hash
            )
            if old:
                transition_id = await connection.scalar(
                    select(records.cycle_transitions.c.id).where(
                        records.cycle_transitions.c.command_id == old["id"],
                        records.cycle_transitions.c.cycle_id == run["cycle_id"],
                        records.cycle_transitions.c.from_state
                        == "WAITING_FOR_OPERATOR_INPUT",
                        records.cycle_transitions.c.to_state
                        == "RETURN_FOR_IDEA_REFINEMENT",
                        records.cycle_transitions.c.offer_design_run_id == run["id"],
                        records.cycle_transitions.c.offer_design_decision_id
                        == request.decision_id,
                    )
                )
                child_cycle_id = await connection.scalar(
                    select(records.cycles.c.id)
                    .join(
                        records.idea_acceptances,
                        records.idea_acceptances.c.cycle_id == records.cycles.c.id,
                    )
                    .where(
                        records.cycles.c.experiment_id == run["experiment_id"],
                        records.cycles.c.parent_cycle_id == run["cycle_id"],
                        records.cycles.c.purpose == "SAME_INTENT_RETURN",
                        records.idea_acceptances.c.artifact_id
                        == request.proposed_idea.artifact_id,
                        records.idea_acceptances.c.artifact_version
                        == request.proposed_idea.version,
                        records.idea_acceptances.c.artifact_hash
                        == request.proposed_idea.content_hash,
                    )
                )
                if child_cycle_id is None or transition_id is None:
                    raise ProductRecordsDenied("IDEA_REFINEMENT_LINEAGE")
                return OfferIdeaRefinementReturnReceipt(
                    command_id=old["id"],
                    result_id=request.decision_id,
                    id=request.decision_id,
                    run_id=run["id"],
                    decision_id=request.decision_id,
                    child_cycle_id=child_cycle_id,
                    transition_id=transition_id,
                )
            state = (
                (
                    await connection.execute(
                        select(records.cycle_states)
                        .where(records.cycle_states.c.cycle_id == run["cycle_id"])
                        .with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            decision = (
                (
                    await connection.execute(
                        select(s.offer_design_decisions).where(
                            s.offer_design_decisions.c.id == request.decision_id,
                            s.offer_design_decisions.c.run_id == run["id"],
                            s.offer_design_decisions.c.outcome
                            == "IDEA_REFINEMENT_RECOMMENDED",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if decision is None or state["state"] != "WAITING_FOR_OPERATOR_INPUT":
                raise ProductRecordsDenied("OPERATOR_CONFIRMATION_REQUIRED")
            evidence = await _exact_artifact(
                connection, request.commercial_failure_evidence
            )
            proposed = await _exact_artifact(connection, request.proposed_idea)
            acceptance = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == run["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            current_idea = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == acceptance["artifact_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            if (
                evidence["id"] != decision["artifact_id"]
                or proposed["experiment_id"] != run["experiment_id"]
                or request.proposed_idea.kind is not ArtifactKind.IDEA_BRIEF
                or proposed["logical_id"] != current_idea["logical_id"]
                or proposed["version"] != current_idea["version"] + 1
                or proposed["payload"].get("core_intent")
                != current_idea["payload"].get("core_intent")
                or proposed["payload"].get("material_pivot") is not False
            ):
                raise ProductRecordsDenied("INVALID_PROPOSED_IDEA_LINEAGE")
            if not await connection.scalar(
                select(records.artifact_dispositions.c.id).where(
                    records.artifact_dispositions.c.artifact_id == proposed["id"],
                    records.artifact_dispositions.c.disposition.in_(
                        ("VALIDATED", "ACCEPTED")
                    ),
                )
            ):
                raise ProductRecordsDenied("UNVALIDATED_PROPOSED_IDEA")
            parent = (
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.id == run["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == run["verdict_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            now = self.clock()
            child_cycle_id, child_acceptance_id, transition_id = (
                uuid4(),
                uuid4(),
                uuid4(),
            )
            cycle_ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(records.cycles)
                    .where(records.cycles.c.experiment_id == run["experiment_id"])
                )
                or 0
            ) + 1
            await connection.execute(
                insert(records.cycles).values(
                    id=child_cycle_id,
                    experiment_id=run["experiment_id"],
                    ordinal=cycle_ordinal,
                    parent_cycle_id=parent["id"],
                    idea_mode=parent["idea_mode"],
                    selection_id=parent["selection_id"],
                    purpose="SAME_INTENT_RETURN",
                    episode_id=parent["episode_id"],
                    seed_artifact_id=parent["seed_artifact_id"],
                    seed_kind=parent["seed_kind"],
                    seed_version=parent["seed_version"],
                    seed_hash=parent["seed_hash"],
                    created_at=now,
                )
            )
            await connection.execute(
                insert(records.idea_acceptances).values(
                    id=child_acceptance_id,
                    experiment_id=run["experiment_id"],
                    cycle_id=child_cycle_id,
                    artifact_id=request.proposed_idea.artifact_id,
                    artifact_kind=request.proposed_idea.kind,
                    artifact_version=request.proposed_idea.version,
                    artifact_hash=request.proposed_idea.content_hash,
                    pivot_approval_id=None,
                    accepted_by=request.accepted_by,
                    accepted_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=run["experiment_id"],
                kind="CONFIRM_OFFER_IDEA_REFINEMENT",
                request_hash=request_hash,
                result_type="OFFER_DESIGN_DECISION",
                result_id=decision["id"],
                now=now,
            )
            await connection.execute(
                insert(records.cycle_transitions).values(
                    id=transition_id,
                    experiment_id=run["experiment_id"],
                    cycle_id=run["cycle_id"],
                    ordinal=state["transition_ordinal"] + 1,
                    from_state="WAITING_FOR_OPERATOR_INPUT",
                    to_state="RETURN_FOR_IDEA_REFINEMENT",
                    idea_acceptance_id=acceptance["id"],
                    idea_artifact_id=acceptance["artifact_id"],
                    idea_kind=acceptance["artifact_kind"],
                    idea_version=acceptance["artifact_version"],
                    idea_hash=acceptance["artifact_hash"],
                    research_attempt_id=verdict["attempt_id"],
                    verdict_id=verdict["id"],
                    offer_design_run_id=run["id"],
                    offer_design_decision_id=decision["id"],
                    command_id=command_id,
                    created_at=now,
                )
            )
            advanced = await connection.execute(
                update(records.cycle_states)
                .where(
                    records.cycle_states.c.cycle_id == run["cycle_id"],
                    records.cycle_states.c.state == "WAITING_FOR_OPERATOR_INPUT",
                    records.cycle_states.c.transition_ordinal
                    == state["transition_ordinal"],
                )
                .values(
                    state="RETURN_FOR_IDEA_REFINEMENT",
                    transition_ordinal=state["transition_ordinal"] + 1,
                    last_transition_id=transition_id,
                    updated_at=now,
                )
            )
            if advanced.rowcount != 1:
                raise ProductRecordsDenied("INVALID_STATE")
            return OfferIdeaRefinementReturnReceipt(
                command_id=command_id,
                result_id=decision["id"],
                id=decision["id"],
                run_id=run["id"],
                decision_id=decision["id"],
                child_cycle_id=child_cycle_id,
                transition_id=transition_id,
            )

    @safe_records
    async def freeze_input_bundle(
        self,
        artifact: ArtifactInput,
        *,
        verdict_id: UUID,
        command_key: UUID,
    ) -> InputBundleReceipt:
        async with self.engine.begin() as connection:
            bundle_artifact = await _exact_artifact(connection, artifact)
            experiment_id = bundle_artifact["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(artifact=artifact, verdict_id=verdict_id)
            old = await _existing(
                connection, command_key, "FREEZE_OFFER_INPUT", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.offer_bundles).where(
                                s.offer_bundles.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return InputBundleReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    artifact_id=row["artifact_id"],
                    version=row["artifact_version"],
                    content_hash=row["artifact_hash"],
                )
            if artifact.kind is not ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE:
                raise ProductRecordsDenied("BUNDLE_KIND")
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == verdict_id,
                            records.verdicts.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if verdict is None or verdict["verdict"] != "PROCEED_TO_OFFER":
                raise ProductRecordsDenied("PROCEED_REQUIRED")
            idea = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == verdict["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            links = (
                (
                    await connection.execute(
                        select(records.artifact_links).where(
                            records.artifact_links.c.consumer_id == artifact.artifact_id
                        )
                    )
                )
                .mappings()
                .all()
            )
            by_role = {row["role"]: row for row in links}
            role_counts = {
                role: sum(row["role"] == role for row in links)
                for role in REQUIRED_RESEARCH_ROLES
            }
            if any(count != 1 for count in role_counts.values()):
                raise ProductRecordsDenied("INCOMPLETE_RESEARCH")
            fixed = {
                "ACCEPTED_IDEA": idea["artifact_id"],
                "REPORT": verdict["report_artifact_id"],
                "RECOMMENDATION": verdict["recommendation_artifact_id"],
            }
            for role, expected in fixed.items():
                if by_role.get(role, {}).get("producer_id") != expected:
                    raise ProductRecordsDenied(f"INCOMPLETE_RESEARCH_{role}")
            report_links = (
                (
                    await connection.execute(
                        select(records.artifact_links).where(
                            records.artifact_links.c.consumer_id
                            == verdict["report_artifact_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
            report_exact = {
                (
                    row["role"],
                    row["producer_id"],
                    row["producer_kind"],
                    row["producer_version"],
                    row["producer_hash"],
                )
                for row in report_links
            }
            for role in REQUIRED_RESEARCH_ROLES:
                row = by_role[role]
                if (
                    role,
                    row["producer_id"],
                    row["producer_kind"],
                    row["producer_version"],
                    row["producer_hash"],
                ) not in report_exact:
                    raise ProductRecordsDenied("INCOMPLETE_RESEARCH")
                if not await connection.scalar(
                    select(records.source_refs.c.id).where(
                        records.source_refs.c.artifact_id == row["producer_id"]
                    )
                ):
                    raise ProductRecordsDenied("MISSING_SOURCE_PROVENANCE")
            prices = (
                (
                    await connection.execute(
                        select(records.artifacts.c.payload).where(
                            records.artifacts.c.id.in_(
                                [by_role["PRICE_OBSERVATION"]["producer_id"]]
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )
            if any(price["status"] != "QUOTED" for price in prices):
                raise ProductRecordsDenied("INCOMPLETE_RESEARCH")
            result_id = uuid4()
            await connection.execute(
                insert(s.offer_bundles).values(
                    id=result_id,
                    experiment_id=experiment_id,
                    artifact_id=artifact.artifact_id,
                    artifact_kind=artifact.kind,
                    artifact_version=artifact.version,
                    artifact_hash=artifact.content_hash,
                    idea_acceptance_id=idea["id"],
                    idea_artifact_id=idea["artifact_id"],
                    verdict_id=verdict_id,
                    report_artifact_id=verdict["report_artifact_id"],
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(s.offer_bundle_inputs),
                [
                    {
                        "bundle_id": result_id,
                        "experiment_id": experiment_id,
                        "role": row["role"],
                        "artifact_id": row["producer_id"],
                        "artifact_kind": row["producer_kind"],
                        "artifact_version": row["producer_version"],
                        "artifact_hash": row["producer_hash"],
                    }
                    for row in links
                ],
            )
            previous = (
                (
                    await connection.execute(
                        select(s.offer_proposals.c.id)
                        .join(
                            s.offer_bundles,
                            s.offer_bundles.c.id == s.offer_proposals.c.bundle_id,
                        )
                        .where(
                            s.offer_bundles.c.idea_artifact_id == idea["artifact_id"],
                            s.offer_proposals.c.id.not_in(
                                select(s.offer_packages.c.proposal_id)
                            ),
                            s.offer_proposals.c.id.not_in(
                                select(s.offer_proposal_invalidations.c.proposal_id)
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if previous:
                await connection.execute(
                    insert(s.offer_proposal_invalidations),
                    [
                        {
                            "proposal_id": proposal_id,
                            "experiment_id": experiment_id,
                            "superseding_bundle_id": result_id,
                            "reason": "SUPERSEDED_RESEARCH",
                            "created_at": self.clock(),
                        }
                        for proposal_id in previous
                    ],
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="FREEZE_OFFER_INPUT",
                request_hash=request_hash,
                result_type="OFFER_INPUT_BUNDLE",
                result_id=result_id,
                now=self.clock(),
            )
            return InputBundleReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                artifact_id=artifact.artifact_id,
                version=artifact.version,
                content_hash=artifact.content_hash,
            )

    @safe_records
    async def derive_commercial_envelope(
        self, request: CommercialEnvelopeRequest, *, command_key: UUID
    ) -> CommercialEnvelopeReceipt:
        async with self.engine.begin() as connection:
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(
                            s.offer_bundles.c.id == request.bundle_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, bundle["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "DERIVE_COMMERCIAL_ENVELOPE", request_hash
            )
            if old:
                return await self._envelope_receipt(
                    connection, old["result_id"], old["id"]
                )
            artifact = await _exact_artifact(connection, request.artifact)
            scope = await _exact_artifact(connection, request.scope_estimate)
            if (
                artifact["experiment_id"] != bundle["experiment_id"]
                or request.artifact.kind is not ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE
            ):
                raise ProductRecordsDenied("ENVELOPE_SCOPE")
            scope_input = await connection.scalar(
                select(s.offer_bundle_inputs.c.artifact_id).where(
                    s.offer_bundle_inputs.c.bundle_id == request.bundle_id,
                    s.offer_bundle_inputs.c.role == "SCOPE_ESTIMATE",
                    s.offer_bundle_inputs.c.artifact_id
                    == request.scope_estimate.artifact_id,
                    s.offer_bundle_inputs.c.artifact_hash
                    == request.scope_estimate.content_hash,
                )
            )
            if (
                scope_input is None
                or request.scope_estimate.kind
                is not ArtifactKind.DELIVERY_SCOPE_ESTIMATE
            ):
                raise ProductRecordsDenied("SCOPE_EVIDENCE")
            experiment = (
                (
                    await connection.execute(
                        select(records.experiments).where(
                            records.experiments.c.id == bundle["experiment_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            profile = (
                (
                    await connection.execute(
                        select(s.operator_profiles).where(
                            s.operator_profiles.c.id
                            == experiment["operator_profile_id"],
                            s.operator_profiles.c.version
                            == experiment["operator_profile_version"],
                        )
                    )
                )
                .mappings()
                .one()
            )
            commercial = profile["commercial"]
            delivery = profile["delivery"]
            hours = Decimal(scope["payload"]["hours"])
            currency = commercial["currency"]
            quoted_currencies = set(
                (
                    await connection.execute(
                        select(records.artifacts.c.payload["currency"].as_string())
                        .join(
                            s.offer_bundle_inputs,
                            s.offer_bundle_inputs.c.artifact_id
                            == records.artifacts.c.id,
                        )
                        .where(
                            s.offer_bundle_inputs.c.bundle_id == request.bundle_id,
                            s.offer_bundle_inputs.c.role == "PRICE_OBSERVATION",
                        )
                    )
                ).scalars()
            )
            margin = Decimal(str(commercial["minimum_margin_rate"]))
            status = "READY"
            delivery_cost = minimum_price = None
            if hours > Decimal(str(delivery["max_project_hours"])):
                status = "DELIVERY_CAPACITY_EXCEEDED"
            elif margin >= 1:
                status = "IMPOSSIBLE_ECONOMICS"
            elif quoted_currencies != {currency}:
                status = "CURRENCY_MISMATCH"
            else:
                delivery_cost = _money(hours * Decimal(str(commercial["hourly_cost"])))
                margin_floor = _money(delivery_cost / (Decimal(1) - margin))
                minimum_price = max(
                    margin_floor,
                    _money(Decimal(str(commercial["minimum_project_price"]))),
                )
            if artifact["payload"]["status"] != status:
                raise ProductRecordsDenied("ENVELOPE_CLASSIFICATION")
            result_id = uuid4()
            await connection.execute(
                insert(s.commercial_envelopes).values(
                    id=result_id,
                    experiment_id=bundle["experiment_id"],
                    artifact_id=request.artifact.artifact_id,
                    artifact_kind=request.artifact.kind,
                    artifact_version=request.artifact.version,
                    artifact_hash=request.artifact.content_hash,
                    bundle_id=request.bundle_id,
                    operator_profile_id=profile["id"],
                    operator_profile_version=profile["version"],
                    scope_artifact_id=request.scope_estimate.artifact_id,
                    status=status,
                    currency=currency,
                    service_hours=hours,
                    delivery_cost=delivery_cost,
                    minimum_price=minimum_price,
                    minimum_margin_rate=margin,
                    maximum_discount_rate=Decimal(
                        str(commercial["maximum_discount_rate"])
                    ),
                    minimum_deposit_rate=Decimal(
                        str(commercial["minimum_deposit_rate"])
                    ),
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=bundle["experiment_id"],
                kind="DERIVE_COMMERCIAL_ENVELOPE",
                request_hash=request_hash,
                result_type="COMMERCIAL_ENVELOPE",
                result_id=result_id,
                now=self.clock(),
            )
            return CommercialEnvelopeReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                bundle_id=request.bundle_id,
                status=status,
                currency=currency,
                delivery_cost=delivery_cost,
                minimum_price=minimum_price,
            )

    async def _envelope_receipt(self, connection, result_id, command_id):
        row = (
            (
                await connection.execute(
                    select(s.commercial_envelopes).where(
                        s.commercial_envelopes.c.id == result_id
                    )
                )
            )
            .mappings()
            .one()
        )
        return CommercialEnvelopeReceipt(
            command_id=command_id,
            result_id=row["id"],
            id=row["id"],
            bundle_id=row["bundle_id"],
            status=row["status"],
            currency=row["currency"],
            delivery_cost=row["delivery_cost"],
            minimum_price=row["minimum_price"],
        )

    @safe_records
    async def register_proposal(
        self,
        artifact: ArtifactInput,
        *,
        bundle_id: UUID,
        envelope_id: UUID,
        offer_design_run_id: UUID | None = None,
        command_key: UUID,
    ) -> OfferProposalReceipt:
        async with self.engine.begin() as connection:
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(s.offer_bundles.c.id == bundle_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, bundle["experiment_id"])
            request_hash = _request_hash(
                artifact=artifact,
                bundle_id=bundle_id,
                envelope_id=envelope_id,
                offer_design_run_id=offer_design_run_id,
            )
            old = await _existing(
                connection, command_key, "REGISTER_OFFER_PROPOSAL", request_hash
            )
            if old:
                return OfferProposalReceipt(
                    command_id=old["id"],
                    result_id=old["result_id"],
                    id=old["result_id"],
                    bundle_id=bundle_id,
                )
            value = await _exact_artifact(connection, artifact)
            envelope = (
                (
                    await connection.execute(
                        select(s.commercial_envelopes).where(
                            s.commercial_envelopes.c.id == envelope_id,
                            s.commercial_envelopes.c.bundle_id == bundle_id,
                        )
                    )
                )
                .mappings()
                .one()
            )
            if (
                artifact.kind is not ArtifactKind.OFFER_DESIGN_PROPOSAL
                or envelope["status"] != "READY"
            ):
                raise ProductRecordsDenied("ENVELOPE_NOT_READY")
            if offer_design_run_id is not None and not await connection.scalar(
                select(s.offer_design_runs.c.id).where(
                    s.offer_design_runs.c.id == offer_design_run_id,
                    s.offer_design_runs.c.bundle_id == bundle_id,
                    s.offer_design_runs.c.envelope_id == envelope_id,
                    s.offer_design_runs.c.experiment_id == bundle["experiment_id"],
                )
            ):
                raise ProductRecordsDenied("OFFER_RUN_LINEAGE")
            if (
                value["payload"]["currency"] != envelope["currency"]
                or Decimal(value["payload"]["base_price"]) < envelope["minimum_price"]
            ):
                raise ProductRecordsDenied("COMMERCIAL_FLOOR")
            result_id = uuid4()
            await connection.execute(
                insert(s.offer_proposals).values(
                    id=result_id,
                    experiment_id=bundle["experiment_id"],
                    artifact_id=artifact.artifact_id,
                    artifact_kind=artifact.kind,
                    artifact_version=artifact.version,
                    artifact_hash=artifact.content_hash,
                    bundle_id=bundle_id,
                    envelope_id=envelope_id,
                    offer_design_run_id=offer_design_run_id,
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=bundle["experiment_id"],
                kind="REGISTER_OFFER_PROPOSAL",
                request_hash=request_hash,
                result_type="OFFER_PROPOSAL",
                result_id=result_id,
                now=self.clock(),
            )
            return OfferProposalReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                bundle_id=bundle_id,
            )

    @safe_records
    async def accept_offer(
        self,
        request: OfferAcceptanceRequest,
        *,
        command_key: UUID,
        offer_design_run_id: UUID | None = None,
        decision_artifact: ArtifactInput | None = None,
    ) -> OfferAcceptanceReceipt:
        if {item.field_path for item in request.field_sources} != set(
            PROTECTED_OFFER_FIELDS
        ) or len(request.field_sources) != len(PROTECTED_OFFER_FIELDS):
            raise ProductRecordsDenied("FIELD_LINEAGE")
        if {item.category for item in request.criteria} != set(
            REQUIRED_QUALIFICATION_CATEGORIES
        ):
            raise ProductRecordsDenied("QUALIFICATION_COVERAGE")
        for item in request.field_sources:
            if item.source is not None:
                if item.source.role not in OFFER_FIELD_EVIDENCE_ROLES.get(
                    item.field_path, ()
                ):
                    raise ProductRecordsDenied("FIELD_LINEAGE")
            elif (
                OPERATOR_FIELD_CONSTRAINTS.get(item.field_path)
                != item.operator_constraint
            ):
                raise ProductRecordsDenied("FIELD_LINEAGE")
        async with self.engine.begin() as connection:
            proposal = (
                (
                    await connection.execute(
                        select(s.offer_proposals).where(
                            s.offer_proposals.c.id == request.proposal_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, proposal["experiment_id"])
            request_hash = (
                _request_hash(request=request)
                if offer_design_run_id is None
                else _request_hash(
                    request=request,
                    offer_design_run_id=offer_design_run_id,
                    decision_artifact=decision_artifact,
                )
            )
            old = await _existing(connection, command_key, "ACCEPT_OFFER", request_hash)
            if old:
                row = (
                    (
                        await connection.execute(
                            select(
                                s.offer_acceptances,
                                s.offer_packages.c.bundle_id,
                                s.commercial_envelopes.c.minimum_price,
                            )
                            .join(
                                s.offer_packages,
                                s.offer_packages.c.id == s.offer_acceptances.c.offer_id,
                            )
                            .join(
                                s.commercial_envelopes,
                                s.commercial_envelopes.c.id
                                == s.offer_packages.c.envelope_id,
                            )
                            .where(s.offer_acceptances.c.id == old["result_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                return OfferAcceptanceReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    bundle_id=row["bundle_id"],
                    offer_artifact_id=row["offer_artifact_id"],
                    minimum_price=row["minimum_price"],
                )
            if await connection.scalar(
                select(s.offer_proposal_invalidations.c.proposal_id).where(
                    s.offer_proposal_invalidations.c.proposal_id == request.proposal_id
                )
            ):
                raise ProductRecordsDenied("PROPOSAL_INVALIDATED")
            run = None
            state = None
            if (offer_design_run_id is None) != (decision_artifact is None):
                raise ProductRecordsDenied("OFFER_RUN_DECISION_REQUIRED")
            if offer_design_run_id is not None:
                run = (
                    (
                        await connection.execute(
                            select(s.offer_design_runs)
                            .where(
                                s.offer_design_runs.c.id == offer_design_run_id,
                                s.offer_design_runs.c.experiment_id
                                == proposal["experiment_id"],
                                s.offer_design_runs.c.bundle_id
                                == proposal["bundle_id"],
                                s.offer_design_runs.c.envelope_id
                                == proposal["envelope_id"],
                            )
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if (
                    run is None
                    or proposal["offer_design_run_id"] != offer_design_run_id
                ):
                    raise ProductRecordsDenied("OFFER_RUN_LINEAGE")
                state = (
                    (
                        await connection.execute(
                            select(records.cycle_states)
                            .where(records.cycle_states.c.cycle_id == run["cycle_id"])
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one()
                )
                if state["state"] != "OFFER_DESIGN":
                    raise ProductRecordsDenied("INVALID_STATE")
                assert decision_artifact is not None
                decision_value = await _exact_artifact(connection, decision_artifact)
                if (
                    decision_artifact.kind is not ArtifactKind.VALIDATION_RESULT
                    or decision_value["payload"].get("disposition") != "PASS"
                    or decision_value["experiment_id"] != proposal["experiment_id"]
                ):
                    raise ProductRecordsDenied("DECISION_LINEAGE")
            if request.calibration_decision_id is not None:
                from alon_ai.records import calibration_schema as calibration
                from alon_ai.records import qualification_schema as qualification

                decision = (
                    (
                        await connection.execute(
                            select(calibration.decisions).where(
                                calibration.decisions.c.id
                                == request.calibration_decision_id
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                current_id = await connection.scalar(
                    select(s.offer_acceptances.c.id)
                    .where(
                        s.offer_acceptances.c.experiment_id == proposal["experiment_id"]
                    )
                    .order_by(
                        s.offer_acceptances.c.accepted_at.desc(),
                        s.offer_acceptances.c.id.desc(),
                    )
                    .limit(1)
                )
                if (
                    decision is None
                    or decision["experiment_id"] != proposal["experiment_id"]
                    or decision["outcome"] != "ACCEPT"
                    or decision["base_offer_acceptance_id"] != current_id
                    or await connection.scalar(
                        select(calibration.fulfillments.c.id).where(
                            calibration.fulfillments.c.calibration_decision_id
                            == request.calibration_decision_id
                        )
                    )
                    is not None
                    or await connection.scalar(
                        select(qualification.cohorts.c.id).where(
                            qualification.cohorts.c.experiment_id
                            == proposal["experiment_id"]
                        )
                    )
                    is not None
                ):
                    raise ProductRecordsDenied("CALIBRATION_NOT_AUTHORIZED")
                base_bundle = await connection.scalar(
                    select(s.offer_packages.c.bundle_id).where(
                        s.offer_packages.c.id == decision["base_offer_id"]
                    )
                )
                if base_bundle != proposal["bundle_id"]:
                    raise ProductRecordsDenied("CALIBRATION_INPUT_DRIFT")
            package = await _exact_artifact(connection, request.package)
            await _exact_artifact(connection, request.qualification_profile)
            policy_artifact = await _exact_artifact(connection, request.outreach_policy)
            proposal_artifact = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == proposal["artifact_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            if run is not None:
                assert decision_artifact is not None
                if not await _exact_offer_validation_lineage(
                    connection,
                    validation_id=decision_artifact.artifact_id,
                    proposal_artifact_id=proposal_artifact["id"],
                    package_artifact_id=package["id"],
                    profile_artifact_id=request.qualification_profile.artifact_id,
                    policy_artifact_id=request.outreach_policy.artifact_id,
                ):
                    raise ProductRecordsDenied("DECISION_LINEAGE")
            envelope = (
                (
                    await connection.execute(
                        select(s.commercial_envelopes).where(
                            s.commercial_envelopes.c.id == proposal["envelope_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            if (
                request.package.kind is not ArtifactKind.OFFER_PACKAGE
                or package["payload"] != proposal_artifact["payload"]
            ):
                raise ProductRecordsDenied("PACKAGE_DRIFT")
            if (
                request.qualification_profile.kind
                is not ArtifactKind.OFFER_QUALIFICATION_PROFILE
                or request.outreach_policy.kind
                is not ArtifactKind.INITIAL_OUTREACH_POLICY
                or {
                    key: value
                    for key, value in policy_artifact["payload"].items()
                    if key != "max_sequence_steps"
                }
                != {
                    key: value
                    for key, value in INITIAL_OUTREACH_POLICY.items()
                    if key != "max_sequence_steps"
                }
                or policy_artifact["payload"]["max_sequence_steps"] <= 0
            ):
                raise ProductRecordsDenied("MATCHING_RECORDS")
            evidence_ids = set(
                (
                    await connection.execute(
                        select(s.offer_bundle_inputs.c.artifact_id).where(
                            s.offer_bundle_inputs.c.bundle_id == proposal["bundle_id"]
                        )
                    )
                ).scalars()
            )
            if any(
                item.source is not None and item.source.artifact_id not in evidence_ids
                for item in request.field_sources
            ):
                raise ProductRecordsDenied("FIELD_LINEAGE")
            offer_id, profile_id, policy_id, acceptance_id = (
                uuid4(),
                uuid4(),
                uuid4(),
                uuid4(),
            )
            await connection.execute(
                insert(s.offer_packages).values(
                    id=offer_id,
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.package.artifact_id,
                    artifact_kind=request.package.kind,
                    artifact_version=request.package.version,
                    artifact_hash=request.package.content_hash,
                    proposal_id=request.proposal_id,
                    calibration_decision_id=request.calibration_decision_id,
                    offer_design_run_id=offer_design_run_id,
                    bundle_id=proposal["bundle_id"],
                    envelope_id=proposal["envelope_id"],
                    currency=package["payload"]["currency"],
                    base_price=Decimal(package["payload"]["base_price"]),
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(s.offer_field_sources),
                [
                    {
                        "offer_id": offer_id,
                        "experiment_id": proposal["experiment_id"],
                        "field_path": item.field_path,
                        "source_artifact_id": item.source.artifact_id
                        if item.source
                        else None,
                        "source_kind": item.source.kind if item.source else None,
                        "source_role": item.source.role if item.source else None,
                        "source_version": item.source.version if item.source else None,
                        "source_hash": item.source.content_hash
                        if item.source
                        else None,
                        "operator_constraint": item.operator_constraint,
                        "bundle_id": proposal["bundle_id"],
                    }
                    for item in request.field_sources
                ],
            )
            await connection.execute(
                insert(s.offer_qualification_profiles).values(
                    id=profile_id,
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.qualification_profile.artifact_id,
                    artifact_kind=request.qualification_profile.kind,
                    artifact_version=request.qualification_profile.version,
                    artifact_hash=request.qualification_profile.content_hash,
                    offer_id=offer_id,
                )
            )
            await connection.execute(
                insert(s.qualification_criteria),
                [
                    dict(
                        profile_id=profile_id,
                        **item.model_dump(exclude={"schema_version"}),
                    )
                    for item in request.criteria
                ],
            )
            await connection.execute(
                insert(s.initial_outreach_policies).values(
                    id=policy_id,
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.outreach_policy.artifact_id,
                    artifact_kind=request.outreach_policy.kind,
                    artifact_version=request.outreach_policy.version,
                    artifact_hash=request.outreach_policy.content_hash,
                    offer_id=offer_id,
                    **policy_artifact["payload"],
                )
            )
            await connection.execute(
                insert(s.offer_acceptances).values(
                    id=acceptance_id,
                    experiment_id=proposal["experiment_id"],
                    offer_id=offer_id,
                    offer_artifact_id=request.package.artifact_id,
                    profile_id=profile_id,
                    profile_artifact_id=request.qualification_profile.artifact_id,
                    policy_id=policy_id,
                    policy_artifact_id=request.outreach_policy.artifact_id,
                    accepted_by=request.accepted_by,
                    accepted_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=proposal["experiment_id"],
                kind="ACCEPT_OFFER",
                request_hash=request_hash,
                result_type="OFFER_ACCEPTANCE",
                result_id=acceptance_id,
                now=self.clock(),
            )
            if run is not None:
                assert state is not None
                decision_id, transition_id = uuid4(), uuid4()
                assert decision_artifact is not None
                await connection.execute(
                    insert(s.offer_design_decisions).values(
                        id=decision_id,
                        experiment_id=proposal["experiment_id"],
                        run_id=run["id"],
                        artifact_id=decision_artifact.artifact_id,
                        artifact_kind=decision_artifact.kind,
                        artifact_version=decision_artifact.version,
                        artifact_hash=decision_artifact.content_hash,
                        outcome="ACCEPT",
                        operator_id=request.accepted_by,
                        created_at=self.clock(),
                    )
                )
                acceptance = (
                    (
                        await connection.execute(
                            select(records.idea_acceptances).where(
                                records.idea_acceptances.c.cycle_id == run["cycle_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                source_verdict = (
                    (
                        await connection.execute(
                            select(records.verdicts).where(
                                records.verdicts.c.id == run["verdict_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                await connection.execute(
                    insert(records.cycle_transitions).values(
                        id=transition_id,
                        experiment_id=proposal["experiment_id"],
                        cycle_id=run["cycle_id"],
                        ordinal=state["transition_ordinal"] + 1,
                        from_state="OFFER_DESIGN",
                        to_state="OFFER_ACCEPTED",
                        idea_acceptance_id=acceptance["id"],
                        idea_artifact_id=acceptance["artifact_id"],
                        idea_kind=acceptance["artifact_kind"],
                        idea_version=acceptance["artifact_version"],
                        idea_hash=acceptance["artifact_hash"],
                        research_attempt_id=source_verdict["attempt_id"],
                        verdict_id=run["verdict_id"],
                        offer_design_run_id=run["id"],
                        offer_design_decision_id=decision_id,
                        command_id=command_id,
                        created_at=self.clock(),
                    )
                )
                advanced = await connection.execute(
                    update(records.cycle_states)
                    .where(
                        records.cycle_states.c.cycle_id == run["cycle_id"],
                        records.cycle_states.c.state == "OFFER_DESIGN",
                        records.cycle_states.c.transition_ordinal
                        == state["transition_ordinal"],
                    )
                    .values(
                        state="OFFER_ACCEPTED",
                        transition_ordinal=state["transition_ordinal"] + 1,
                        last_transition_id=transition_id,
                        updated_at=self.clock(),
                    )
                )
                if advanced.rowcount != 1:
                    raise ProductRecordsDenied("INVALID_STATE")
            return OfferAcceptanceReceipt(
                command_id=command_id,
                result_id=acceptance_id,
                id=acceptance_id,
                bundle_id=proposal["bundle_id"],
                offer_artifact_id=request.package.artifact_id,
                minimum_price=envelope["minimum_price"],
            )

    @safe_records
    async def activate_offer_gap(self, request: OfferGapRequest, *, command_key: UUID):
        async with self.engine.begin() as connection:
            proposal = (
                (
                    await connection.execute(
                        select(s.offer_proposals).where(
                            s.offer_proposals.c.id == request.proposal_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, proposal["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "ACTIVATE_OFFER_GAP", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(records.cycles).where(
                                records.cycles.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return CycleReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    experiment_id=row["experiment_id"],
                    ordinal=row["ordinal"],
                )
            artifact = await _exact_artifact(connection, request.artifact)
            if (
                request.artifact.kind is not ArtifactKind.OFFER_RESEARCH_GAP_BRIEF
                or artifact["experiment_id"] != proposal["experiment_id"]
            ):
                raise ProductRecordsDenied("GAP_SCOPE")
            await connection.execute(
                insert(s.offer_gap_briefs).values(
                    id=uuid4(),
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.artifact.artifact_id,
                    artifact_kind=request.artifact.kind,
                    artifact_version=request.artifact.version,
                    artifact_hash=request.artifact.content_hash,
                    proposal_id=request.proposal_id,
                    bundle_id=proposal["bundle_id"],
                    missing_fields=list(request.missing_fields),
                    contradictory_fields=list(request.contradictory_fields),
                    required_source_types=list(request.required_source_types),
                    targeted_questions=list(request.targeted_questions),
                    created_at=self.clock(),
                )
            )
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(
                            s.offer_bundles.c.id == proposal["bundle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == bundle["verdict_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            parent = (
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.id == verdict["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            idea = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == parent["id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(records.cycles)
                    .where(records.cycles.c.experiment_id == proposal["experiment_id"])
                )
                or 0
            ) + 1
            cycle_id = uuid4()
            await connection.execute(
                insert(records.cycles).values(
                    id=cycle_id,
                    experiment_id=proposal["experiment_id"],
                    ordinal=ordinal,
                    parent_cycle_id=parent["id"],
                    idea_mode=parent["idea_mode"],
                    selection_id=parent["selection_id"],
                    purpose="OFFER_GAP_RETURN",
                    episode_id=parent["episode_id"],
                    seed_artifact_id=parent["seed_artifact_id"],
                    seed_kind=parent["seed_kind"],
                    seed_version=parent["seed_version"],
                    seed_hash=parent["seed_hash"],
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(records.returns).values(
                    id=uuid4(),
                    experiment_id=proposal["experiment_id"],
                    from_cycle_id=parent["id"],
                    verdict_id=verdict["id"],
                    to_cycle_id=cycle_id,
                    ordinal=1,
                    kind="OFFER_GAP",
                    applicable_scope_id=idea["artifact_id"],
                    idea_artifact_id=idea["artifact_id"],
                    offer_input_bundle_id=bundle["artifact_id"],
                    feedback_artifact_id=request.artifact.artifact_id,
                    feedback_kind=request.artifact.kind,
                    feedback_version=request.artifact.version,
                    feedback_hash=request.artifact.content_hash,
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(records.idea_acceptances).values(
                    id=uuid4(),
                    experiment_id=proposal["experiment_id"],
                    cycle_id=cycle_id,
                    artifact_id=idea["artifact_id"],
                    artifact_kind=idea["artifact_kind"],
                    artifact_version=idea["artifact_version"],
                    artifact_hash=idea["artifact_hash"],
                    accepted_by=idea["accepted_by"],
                    accepted_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=proposal["experiment_id"],
                kind="ACTIVATE_OFFER_GAP",
                request_hash=request_hash,
                result_type="CYCLE",
                result_id=cycle_id,
                now=self.clock(),
            )
            return CycleReceipt(
                command_id=command_id,
                result_id=cycle_id,
                id=cycle_id,
                experiment_id=proposal["experiment_id"],
                ordinal=ordinal,
            )
