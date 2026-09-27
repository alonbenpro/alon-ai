"""Atomic SQL and locking for operator-owned Idea experiments."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alon_ai.agents.schemas.openai import canonical_json, sha256
from alon_ai.db.repositories.openai_run import OpenAIRunOutcome
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records
from alon_ai.db.tables.openai import run_intents
from alon_ai.services.schemas.records import ArtifactKind


class ExperimentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _terminal_failure_settled(intent, call) -> bool:
    """A missing call or intent cannot prove that the original owner has stopped."""
    if intent is None or call is None:
        return False
    if (
        intent["outcome"]
        not in {
            OpenAIRunOutcome.FAILED,
            OpenAIRunOutcome.REFUSED,
            OpenAIRunOutcome.SCHEMA_MISMATCH,
            OpenAIRunOutcome.INCOMPLETE,
            OpenAIRunOutcome.TIMEOUT,
            OpenAIRunOutcome.CANCELLED,
        }
        or intent["finished_at"] is None
    ):
        return False
    return intent["call_id"] == call["id"] and call["state"] == "FINAL"


async def profile_rows(engine, operator_id):
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(records.operator_profiles)
                    .where(records.operator_profiles.c.operator_id == operator_id)
                    .order_by(records.operator_profiles.c.version.desc())
                )
            )
            .mappings()
            .all()
        )

    return rows


async def artifact_row(engine, artifact_id):
    async with engine.connect() as connection:
        return (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == artifact_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )


async def existing_experiment(engine, operator_id, experiment_id):
    async with engine.connect() as connection:
        existing = (
            (
                await connection.execute(
                    select(records.experiments)
                    .select_from(
                        records.experiments.join(
                            records.operator_profiles,
                            (
                                records.operator_profiles.c.id
                                == records.experiments.c.operator_profile_id
                            )
                            & (
                                records.operator_profiles.c.version
                                == records.experiments.c.operator_profile_version
                            ),
                        )
                    )
                    .where(
                        records.experiments.c.id == experiment_id,
                        records.operator_profiles.c.operator_id == operator_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    return existing


async def bound_profile(engine, existing, operator_id):
    async with engine.connect() as connection:
        bound_profile = (
            (
                await connection.execute(
                    select(records.operator_profiles).where(
                        records.operator_profiles.c.id
                        == existing["operator_profile_id"],
                        records.operator_profiles.c.version
                        == existing["operator_profile_version"],
                        records.operator_profiles.c.operator_id == operator_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    return bound_profile


async def insert_governance_roots(engine, experiment_id, workflow_id, agent_id):
    async with engine.begin() as connection:
        for table, values in (
            (gov.experiments, {"id": experiment_id}),
            (gov.workflows, {"id": workflow_id, "experiment_id": experiment_id}),
            (gov.agents, {"id": agent_id, "workflow_id": workflow_id}),
        ):
            await connection.execute(
                pg_insert(table).values(**values).on_conflict_do_nothing()
            )


async def existing_cycle(engine, experiment_id):
    async with engine.connect() as connection:
        existing_cycle = (
            await connection.execute(
                select(records.cycles.c.id).where(
                    records.cycles.c.experiment_id == experiment_id
                )
            )
        ).scalar_one_or_none()

    return existing_cycle


async def experiment_snapshot_rows(engine, operator_id, experiment_id):
    async with engine.connect() as connection:
        experiment = (
            (
                await connection.execute(
                    select(records.experiments)
                    .select_from(
                        records.experiments.join(
                            records.operator_profiles,
                            (
                                records.operator_profiles.c.id
                                == records.experiments.c.operator_profile_id
                            )
                            & (
                                records.operator_profiles.c.version
                                == records.experiments.c.operator_profile_version
                            ),
                        )
                    )
                    .where(
                        records.experiments.c.id == experiment_id,
                        records.operator_profiles.c.operator_id == operator_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if experiment is None:
            return None
        artifacts = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.experiment_id == experiment_id
                    )
                )
            )
            .mappings()
            .all()
        )
        cycle = (
            (
                await connection.execute(
                    select(records.cycles)
                    .where(records.cycles.c.experiment_id == experiment_id)
                    .order_by(records.cycles.c.ordinal.desc())
                )
            )
            .mappings()
            .first()
        )
        acceptance = (
            (
                await connection.execute(
                    select(records.idea_acceptances).where(
                        records.idea_acceptances.c.cycle_id == cycle["id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if cycle
            else None
        )
        latest = (
            (
                await connection.execute(
                    select(records.idea_refinements)
                    .where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.cycle_id == cycle["id"],
                    )
                    .order_by(
                        records.idea_refinements.c.created_at.desc(),
                        records.idea_refinements.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
            if cycle
            else None
        )
        discovery = (
            (
                await connection.execute(
                    select(records.idea_discoveries)
                    .where(records.idea_discoveries.c.experiment_id == experiment_id)
                    .order_by(
                        records.idea_discoveries.c.created_at.desc(),
                        records.idea_discoveries.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        run_outcome = (
            await connection.scalar(
                select(run_intents.c.outcome).where(
                    run_intents.c.idempotency_key == latest["run_id"]
                )
            )
            if latest
            else None
        )
        discovery_outcome = (
            await connection.scalar(
                select(run_intents.c.outcome).where(
                    run_intents.c.idempotency_key == discovery["run_id"]
                )
            )
            if discovery
            else None
        )
        returned = (
            (
                await connection.execute(
                    select(records.returns).where(
                        records.returns.c.to_cycle_id == cycle["id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if cycle and cycle["purpose"] == "SAME_INTENT_RETURN"
            else None
        )
        return_context_rows = None
        if returned is not None:
            return_context_rows = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id.in_(
                                [
                                    returned["idea_artifact_id"],
                                    returned["feedback_artifact_id"],
                                ]
                            )
                        )
                    )
                )
                .mappings()
                .all()
            )
        return_verdict = (
            (
                await connection.execute(
                    select(records.verdicts).where(
                        records.verdicts.c.id == returned["verdict_id"]
                    )
                )
            )
            .mappings()
            .one()
            if returned is not None
            else None
        )
        available_verdict = (
            (
                await connection.execute(
                    select(records.verdicts)
                    .where(
                        records.verdicts.c.experiment_id == experiment_id,
                        records.verdicts.c.cycle_id == cycle["id"],
                        records.verdicts.c.verdict == "REFINE_SAME_IDEA",
                    )
                    .order_by(records.verdicts.c.committed_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
            if cycle and acceptance and cycle["purpose"] != "SAME_INTENT_RETURN"
            else None
        )
        available_feedback_rows = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.experiment_id == experiment_id,
                        records.artifacts.c.kind
                        == ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                    )
                )
            )
            .mappings()
            .all()
            if available_verdict is not None
            else []
        )
        return_block = (
            (
                await connection.execute(
                    select(records.research_return_blocks)
                    .where(
                        records.research_return_blocks.c.experiment_id == experiment_id,
                        records.research_return_blocks.c.cycle_id == cycle["id"],
                        records.research_return_blocks.c.return_kind == "SAME_INTENT",
                    )
                    .order_by(records.research_return_blocks.c.created_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
            if cycle
            else None
        )
        cycle_state = (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == cycle["id"],
                    records.cycle_states.c.experiment_id == experiment_id,
                )
            )
            if cycle
            else None
        )
        managed_return = (
            await connection.scalar(
                select(records.cycle_transitions.c.id)
                .join(
                    records.commands,
                    records.commands.c.id == records.cycle_transitions.c.command_id,
                )
                .where(
                    records.cycle_transitions.c.verdict_id == available_verdict["id"],
                    records.commands.c.kind == "COMMIT_MARKET_RESEARCH_OUTCOME",
                )
            )
            if available_verdict is not None
            else None
        )

    return (
        experiment,
        artifacts,
        cycle,
        acceptance,
        latest,
        discovery,
        run_outcome,
        discovery_outcome,
        returned,
        return_context_rows,
        return_verdict,
        available_verdict,
        available_feedback_rows,
        return_block,
        cycle_state,
        managed_return,
    )


async def return_lineage_rows(engine, experiment_id):
    async with engine.connect() as connection:
        lineage_rows = (
            (
                await connection.execute(
                    select(records.returns)
                    .where(
                        records.returns.c.experiment_id == experiment_id,
                        records.returns.c.kind == "SAME_INTENT",
                    )
                    .order_by(records.returns.c.ordinal)
                )
            )
            .mappings()
            .all()
        )

    return lineage_rows


async def matching_feedback(
    engine, available_feedback_rows, acceptance, available_verdict
):
    matching = []
    async with engine.connect() as connection:
        for feedback in available_feedback_rows:
            links = {
                (
                    row["producer_id"],
                    row["producer_kind"],
                    row["producer_version"],
                    row["producer_hash"],
                    row["role"],
                )
                for row in (
                    (
                        await connection.execute(
                            select(records.artifact_links).where(
                                records.artifact_links.c.consumer_id == feedback["id"]
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            }
            if {
                (
                    acceptance["artifact_id"],
                    acceptance["artifact_kind"],
                    acceptance["artifact_version"],
                    acceptance["artifact_hash"],
                    "ACCEPTED_IDEA",
                ),
                (
                    available_verdict["report_artifact_id"],
                    available_verdict["report_kind"],
                    available_verdict["report_version"],
                    available_verdict["report_hash"],
                    "REPORT",
                ),
                (
                    available_verdict["recommendation_artifact_id"],
                    available_verdict["recommendation_kind"],
                    available_verdict["recommendation_version"],
                    available_verdict["recommendation_hash"],
                    "RECOMMENDATION",
                ),
            } != links:
                continue
            if set(feedback["payload"]) != {
                "preserve",
                "change",
                "failed_dimensions",
                "research_questions",
            }:
                continue
            if not await connection.scalar(
                select(records.artifact_dispositions.c.id).where(
                    records.artifact_dispositions.c.artifact_id == feedback["id"],
                    records.artifact_dispositions.c.disposition == "ACCEPTED",
                )
            ):
                continue
            if await connection.scalar(
                select(records.artifacts.c.id).where(
                    records.artifacts.c.logical_id == feedback["logical_id"],
                    records.artifacts.c.version > feedback["version"],
                )
            ) or await connection.scalar(
                select(records.artifact_dispositions.c.id).where(
                    records.artifact_dispositions.c.artifact_id == feedback["id"],
                    records.artifact_dispositions.c.disposition == "SUPERSEDED",
                )
            ):
                continue
            if len(feedback["payload"]["failed_dimensions"]) != len(
                set(feedback["payload"]["failed_dimensions"])
            ):
                continue
            if all(
                isinstance(value, str) and value.strip()
                for field in (
                    "preserve",
                    "change",
                    "failed_dimensions",
                    "research_questions",
                )
                for value in feedback["payload"][field]
            ):
                matching.append(feedback)

    return matching


async def safe_retry_evidence(engine, run_id, operation_id, experiment_id):
    async with engine.connect() as connection:
        intent = (
            (
                await connection.execute(
                    select(run_intents).where(
                        run_intents.c.idempotency_key == run_id,
                        run_intents.c.experiment_id == experiment_id,
                        run_intents.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == run_id,
                        gov.calls.c.experiment_id == experiment_id,
                        gov.calls.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    return intent, call


async def reconcile_stale_discovery(engine, operator_id, experiment_id, stale_before):
    async with engine.begin() as connection:
        owned = await connection.scalar(
            select(records.experiments.c.id)
            .select_from(
                records.experiments.join(
                    records.operator_profiles,
                    (
                        records.experiments.c.operator_profile_id
                        == records.operator_profiles.c.id
                    )
                    & (
                        records.experiments.c.operator_profile_version
                        == records.operator_profiles.c.version
                    ),
                )
            )
            .where(
                records.experiments.c.id == experiment_id,
                records.operator_profiles.c.operator_id == operator_id,
            )
            .with_for_update(of=records.experiments)
        )
        if owned is None:
            return
        pending = (
            (
                await connection.execute(
                    select(records.idea_discoveries).where(
                        records.idea_discoveries.c.experiment_id == experiment_id,
                        records.idea_discoveries.c.state == "RUNNING",
                        records.idea_discoveries.c.created_at < stale_before,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if pending is None:
            return
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == pending["run_id"],
                        gov.calls.c.experiment_id == experiment_id,
                        gov.calls.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        intent = (
            (
                await connection.execute(
                    select(run_intents).where(
                        run_intents.c.idempotency_key == pending["run_id"],
                        run_intents.c.experiment_id == experiment_id,
                        run_intents.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        safe = _terminal_failure_settled(intent, call)
        await connection.execute(
            update(records.idea_discoveries)
            .where(
                records.idea_discoveries.c.run_id == pending["run_id"],
                records.idea_discoveries.c.state == "RUNNING",
            )
            .values(
                state="DISCOVERY_FAILED" if safe else "DISCOVERY_BLOCKED",
                finished_at=datetime.now(UTC),
            )
        )

    return


async def reconcile_stale_refinement(engine, operator_id, experiment_id, stale_before):
    async with engine.begin() as connection:
        owned = await connection.scalar(
            select(records.experiments.c.id)
            .select_from(
                records.experiments.join(
                    records.operator_profiles,
                    (
                        records.operator_profiles.c.id
                        == records.experiments.c.operator_profile_id
                    )
                    & (
                        records.operator_profiles.c.version
                        == records.experiments.c.operator_profile_version
                    ),
                )
            )
            .where(
                records.experiments.c.id == experiment_id,
                records.operator_profiles.c.operator_id == operator_id,
            )
            .with_for_update(of=records.experiments)
        )
        if owned is None:
            return
        pending = (
            (
                await connection.execute(
                    select(records.idea_refinements)
                    .where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.state == "RUNNING",
                        records.idea_refinements.c.created_at < stale_before,
                    )
                    .order_by(records.idea_refinements.c.created_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if pending is None:
            return
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == pending["run_id"],
                        gov.calls.c.experiment_id == experiment_id,
                        gov.calls.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        intent = (
            (
                await connection.execute(
                    select(run_intents).where(
                        run_intents.c.idempotency_key == pending["run_id"],
                        run_intents.c.experiment_id == experiment_id,
                        run_intents.c.operation_id == pending["operation_id"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        safe_to_retry = _terminal_failure_settled(intent, call)
        await connection.execute(
            update(records.idea_refinements)
            .where(
                records.idea_refinements.c.run_id == pending["run_id"],
                records.idea_refinements.c.state == "RUNNING",
            )
            .values(
                state="REFINEMENT_FAILED" if safe_to_retry else "REFINEMENT_BLOCKED",
                finished_at=datetime.now(UTC),
            )
        )

    return


async def owned_verdict(engine, verdict_id, experiment_id):
    async with engine.connect() as connection:
        owned_verdict = await connection.scalar(
            select(records.verdicts.c.id).where(
                records.verdicts.c.id == verdict_id,
                records.verdicts.c.experiment_id == experiment_id,
            )
        )

    return owned_verdict


async def discovery_prior_and_roots(engine, experiment_id):
    async with engine.connect() as connection:
        prior = (
            (
                await connection.execute(
                    select(records.idea_discoveries)
                    .where(records.idea_discoveries.c.experiment_id == experiment_id)
                    .order_by(
                        records.idea_discoveries.c.created_at.desc(),
                        records.idea_discoveries.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        roots = (
            (
                await connection.execute(
                    select(
                        records.workflows.c.id, records.agents.c.id.label("agent_id")
                    )
                    .select_from(
                        records.workflows.join(
                            records.agents,
                            records.agents.c.workflow_id == records.workflows.c.id,
                        )
                    )
                    .where(records.workflows.c.experiment_id == experiment_id)
                )
            )
            .mappings()
            .first()
        )

    return prior, roots


async def claim_discovery(
    engine, experiment_id, prior, run_id, operation_id, advice_source
):
    async with engine.begin() as connection:
        await connection.execute(
            select(records.experiments.c.id)
            .where(records.experiments.c.id == experiment_id)
            .with_for_update()
        )
        latest_run = await connection.scalar(
            select(records.idea_discoveries.c.run_id)
            .where(records.idea_discoveries.c.experiment_id == experiment_id)
            .order_by(
                records.idea_discoveries.c.created_at.desc(),
                records.idea_discoveries.c.run_id.desc(),
            )
            .limit(1)
        )
        if latest_run != (prior["run_id"] if prior else None):
            raise ExperimentError(409, "DISCOVERY_IN_PROGRESS")
        await connection.execute(
            records.idea_discoveries.insert().values(
                run_id=run_id,
                experiment_id=experiment_id,
                operation_id=operation_id,
                state="RUNNING",
                advice_source=advice_source,
                created_at=datetime.now(UTC),
            )
        )


async def finish_successful_discovery(engine, run_id, payload, candidate_ids):
    async with engine.begin() as connection:
        await connection.execute(
            update(records.idea_discoveries)
            .where(
                records.idea_discoveries.c.run_id == run_id,
                records.idea_discoveries.c.state == "RUNNING",
            )
            .values(
                state="SUCCEEDED",
                advice=payload,
                output_hash=sha256(canonical_json(payload)),
                candidate_ids=candidate_ids,
                finished_at=datetime.now(UTC),
            )
        )


async def finish_failed_discovery(engine, run_id, retry_safe):
    async with engine.begin() as connection:
        await connection.execute(
            update(records.idea_discoveries)
            .where(
                records.idea_discoveries.c.run_id == run_id,
                records.idea_discoveries.c.state == "RUNNING",
            )
            .values(
                state="DISCOVERY_FAILED" if retry_safe else "DISCOVERY_BLOCKED",
                finished_at=datetime.now(UTC),
            )
        )


async def block_discovery(engine, run_id, experiment_id, claimed_operation_id):
    async with engine.begin() as connection:
        await connection.execute(
            update(records.idea_discoveries)
            .where(
                records.idea_discoveries.c.run_id == run_id,
                records.idea_discoveries.c.experiment_id == experiment_id,
                records.idea_discoveries.c.operation_id == claimed_operation_id,
                records.idea_discoveries.c.state == "RUNNING",
            )
            .values(state="DISCOVERY_BLOCKED", finished_at=datetime.now(UTC))
        )


async def run_outcome(engine, run_id):
    async with engine.connect() as connection:
        return await connection.scalar(
            select(run_intents.c.outcome).where(run_intents.c.idempotency_key == run_id)
        )


async def candidate_selection_rows(
    engine, experiment_id, candidate_artifact_id, selection_command_id
):
    async with engine.connect() as connection:
        candidate = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == candidate_artifact_id,
                        records.artifacts.c.experiment_id == experiment_id,
                        records.artifacts.c.kind == ArtifactKind.IDEA_CANDIDATE,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        selection = (
            (
                await connection.execute(
                    select(records.candidate_selections).where(
                        records.candidate_selections.c.experiment_id == experiment_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        selection_command = (
            (
                await connection.execute(
                    select(records.commands).where(
                        records.commands.c.command_key == selection_command_id,
                        records.commands.c.experiment_id == experiment_id,
                        records.commands.c.kind == "SELECT_IDEA_CANDIDATE",
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    return candidate, selection, selection_command


async def claim_refinement(
    engine, experiment_id, cycle_id, run_id, operation_id, advice_source
):
    async with engine.begin() as connection:
        await connection.execute(
            select(records.experiments.c.id)
            .where(records.experiments.c.id == experiment_id)
            .with_for_update()
        )
        accepted = await connection.scalar(
            select(records.idea_acceptances.c.id).where(
                records.idea_acceptances.c.cycle_id == cycle_id
            )
        )
        if accepted is not None:
            raise ExperimentError(409, "IDEA_ALREADY_ACCEPTED")
        latest = (
            (
                await connection.execute(
                    select(records.idea_refinements)
                    .where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.cycle_id == cycle_id,
                    )
                    .order_by(
                        records.idea_refinements.c.created_at.desc(),
                        records.idea_refinements.c.run_id.desc(),
                    )
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if latest is not None:
            if latest["run_id"] == run_id:
                raise ExperimentError(409, "REFINEMENT_IN_PROGRESS")
            if latest["state"] == "RUNNING":
                raise ExperimentError(409, "REFINEMENT_IN_PROGRESS")
            if latest["state"] == "SUCCEEDED":
                raise ExperimentError(409, "REVIEW_PENDING")
            if latest["state"] == "REFINEMENT_BLOCKED":
                raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")
        seed_id = await connection.scalar(
            select(records.returns.c.idea_artifact_id).where(
                records.returns.c.to_cycle_id == cycle_id,
                records.returns.c.experiment_id == experiment_id,
                records.returns.c.kind == "SAME_INTENT",
            )
        ) or await connection.scalar(
            select(records.cycles.c.seed_artifact_id).where(
                records.cycles.c.id == cycle_id,
                records.cycles.c.experiment_id == experiment_id,
            )
        )
        if seed_id is None:
            raise ExperimentError(409, "EXPERIMENT_NOT_READY")
        await connection.execute(
            records.idea_refinements.insert().values(
                run_id=run_id,
                experiment_id=experiment_id,
                cycle_id=cycle_id,
                seed_artifact_id=seed_id,
                operation_id=operation_id,
                state="RUNNING",
                advice_source=advice_source,
                created_at=datetime.now(UTC),
            )
        )


async def refinement_existing_and_roots(engine, run_id, experiment_id):
    async with engine.connect() as connection:
        existing = (
            (
                await connection.execute(
                    select(records.idea_refinements).where(
                        records.idea_refinements.c.run_id == run_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        roots = (
            (
                await connection.execute(
                    select(
                        records.workflows.c.id, records.agents.c.id.label("agent_id")
                    )
                    .select_from(
                        records.workflows.join(
                            records.agents,
                            records.agents.c.workflow_id == records.workflows.c.id,
                        )
                    )
                    .where(records.workflows.c.experiment_id == experiment_id)
                )
            )
            .mappings()
            .first()
        )

    return existing, roots


async def finish_refinement(
    engine, run_id, experiment_id, claimed_operation_id, success, retry_safe, payload
):
    async with engine.begin() as connection:
        finalized = await connection.execute(
            update(records.idea_refinements)
            .where(
                records.idea_refinements.c.run_id == run_id,
                records.idea_refinements.c.experiment_id == experiment_id,
                records.idea_refinements.c.operation_id == claimed_operation_id,
                records.idea_refinements.c.state == "RUNNING",
            )
            .values(
                state="SUCCEEDED"
                if success
                else "REFINEMENT_FAILED"
                if retry_safe
                else "REFINEMENT_BLOCKED",
                advice=payload if payload else null(),
                output_hash=sha256(canonical_json(payload)) if payload else None,
                finished_at=datetime.now(UTC),
            )
        )
        if finalized.rowcount != 1:
            raise ExperimentError(409, "REFINEMENT_RECONCILIATION_REQUIRED")


async def block_refinement(engine, run_id, experiment_id, claimed_operation_id):
    async with engine.begin() as connection:
        await connection.execute(
            update(records.idea_refinements)
            .where(
                records.idea_refinements.c.run_id == run_id,
                records.idea_refinements.c.experiment_id == experiment_id,
                records.idea_refinements.c.operation_id == claimed_operation_id,
                records.idea_refinements.c.state == "RUNNING",
            )
            .values(state="REFINEMENT_BLOCKED", finished_at=datetime.now(UTC))
        )


async def acceptance_rows(engine, run_id, experiment_id, cycle_id, cycle_purpose):
    async with engine.connect() as connection:
        reviewed = (
            (
                await connection.execute(
                    select(records.idea_refinements).where(
                        records.idea_refinements.c.run_id == run_id,
                        records.idea_refinements.c.experiment_id == experiment_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        seed = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == reviewed["seed_artifact_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if reviewed
            else None
        )
        workflow = (
            (
                await connection.execute(
                    select(
                        records.workflows.c.id, records.agents.c.id.label("agent_id")
                    )
                    .select_from(
                        records.workflows.join(
                            records.agents,
                            records.agents.c.workflow_id == records.workflows.c.id,
                        )
                    )
                    .where(records.workflows.c.experiment_id == experiment_id)
                )
            )
            .mappings()
            .first()
        )
        returned = (
            (
                await connection.execute(
                    select(records.returns).where(
                        records.returns.c.to_cycle_id == cycle_id
                    )
                )
            )
            .mappings()
            .one_or_none()
            if cycle_purpose == "SAME_INTENT_RETURN"
            else None
        )
        prior = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == returned["idea_artifact_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if returned is not None
            else None
        )
        return_feedback = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == returned["feedback_artifact_id"]
                    )
                )
            )
            .mappings()
            .one_or_none()
            if returned is not None
            else None
        )

    return reviewed, seed, workflow, prior, return_feedback


async def save_intent_review(engine, experiment_id, run_id, expected_review):
    async with engine.begin() as connection:
        await connection.execute(
            select(records.experiments.c.id)
            .where(records.experiments.c.id == experiment_id)
            .with_for_update()
        )
        await connection.execute(
            pg_insert(records.idea_intent_reviews)
            .values(**expected_review, created_at=datetime.now(UTC))
            .on_conflict_do_nothing(index_elements=["run_id"])
        )
        intent_review = (
            (
                await connection.execute(
                    select(records.idea_intent_reviews).where(
                        records.idea_intent_reviews.c.run_id == run_id
                    )
                )
            )
            .mappings()
            .one()
        )
        if any(intent_review[key] != value for key, value in expected_review.items()):
            raise ExperimentError(409, "COMMAND_CONFLICT")


async def accepted_row(engine, cycle_id):
    async with engine.connect() as connection:
        accepted = (
            (
                await connection.execute(
                    select(records.idea_acceptances).where(
                        records.idea_acceptances.c.cycle_id == cycle_id
                    )
                )
            )
            .mappings()
            .one()
        )

    return accepted
