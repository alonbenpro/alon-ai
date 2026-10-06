"""Durable, owner-scoped admission and lifecycle for operator Idea runs."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid5

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records
from alon_ai.db.tables.agent_run_steps import steps
from alon_ai.db.tables.agent_runs import runs
from alon_ai.db.tables.intake import commands, intakes
from alon_ai.db.tables.openai import run_intents

if TYPE_CHECKING:
    from alon_ai.services.run_exchanges import RunExchange


def _event(
    row,
    event_type: str,
    now: datetime,
    detail: str | None = None,
    diagnostic: dict | None = None,
    exchange: dict | None = None,
):
    event = {
        "sequence": len(row["events"]) + 1,
        "at": now.isoformat(),
        "type": event_type,
        "detail": detail,
    }
    if diagnostic is not None:
        event["diagnostic"] = diagnostic
    if exchange is not None:
        event["exchange"] = exchange
    return [*row["events"], event]


class AgentRunRepository:
    def __init__(self, engine):
        self.engine = engine

    async def admit(self, values: dict):
        now = datetime.now(UTC)
        payload = dict(
            values,
            status="QUEUED",
            outcome=None,
            blocked_reason=None,
            events=[
                {"sequence": 1, "at": now.isoformat(), "type": "QUEUED", "detail": None}
            ],
            cancel_key=None,
            cancel_requested_at=None,
            cancel_confirmed=False,
            review_key=None,
            review_status="PENDING",
            review_reason=None,
            created_at=now,
            started_at=None,
            finished_at=None,
        )
        async with self.engine.begin() as connection:
            await connection.execute(
                insert(runs)
                .values(**payload)
                .on_conflict_do_nothing(index_elements=["command_key"])
            )
            row = (
                (
                    await connection.execute(
                        select(runs).where(runs.c.command_key == values["command_key"])
                    )
                )
                .mappings()
                .one()
            )
            if any(row[key] != value for key, value in values.items()):
                raise ExperimentError(409, "COMMAND_CONFLICT")
            return row

    async def owned(self, run_id: UUID, operator_id: UUID):
        async with self.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs).where(
                            runs.c.run_id == run_id, runs.c.operator_id == operator_id
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
        return row

    async def get(self, run_id: UUID):
        async with self.engine.connect() as connection:
            return (
                (await connection.execute(select(runs).where(runs.c.run_id == run_id)))
                .mappings()
                .one_or_none()
            )

    async def scoped_evidence_reference(
        self, run_id: UUID, experiment_id: UUID, reference
    ):
        """Scope exact evidence to this run or its pinned immutable prior report."""
        current = await self.get(run_id)
        if current is None or current["experiment_id"] != experiment_id:
            return None
        allowed_runs = [run_id]
        revision_ref = next(
            (
                ref
                for ref in current["input_refs"]
                if ref["role"] == "OPERATOR_REVISION"
            ),
            None,
        )
        report_ref = next(
            (ref for ref in current["input_refs"] if ref["role"] == "PRIOR_RESEARCH"),
            None,
        )
        if revision_ref is not None and report_ref is not None:
            revision = await self.artifact(experiment_id, revision_ref)
            report = await self.artifact(experiment_id, report_ref)
            if (
                revision is not None
                and report is not None
                and report["kind"] == "MARKET_RESEARCH_REPORT"
            ):
                async with self.engine.connect() as connection:
                    prior_run = await connection.scalar(
                        select(records.idea_refinements.c.run_id).where(
                            records.idea_refinements.c.experiment_id == experiment_id,
                            records.idea_refinements.c.operation_id
                            == report["operation_id"],
                        )
                    )
                if prior_run is not None and report["id"] == uuid5(
                    prior_run, "combined-case"
                ):
                    allowed_runs.append(prior_run)
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(gov.retained.c.id, gov.retained.c.expires_at)
                        .join(gov.calls, gov.calls.c.id == gov.retained.c.call_id)
                        .join(steps, steps.c.provider_call_id == gov.calls.c.id)
                        .where(
                            steps.c.run_id.in_(allowed_runs),
                            steps.c.experiment_id == experiment_id,
                            gov.calls.c.experiment_id == experiment_id,
                            gov.retained.c.id == reference.retained_id,
                            gov.retained.c.call_id == reference.call_id,
                            gov.retained.c.grant_id == reference.grant_id,
                            gov.retained.c.grant_version == reference.grant_version,
                            gov.retained.c.field == reference.field,
                            gov.retained.c.expires_at == reference.expires_at,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def by_command(self, command_key: UUID):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(runs).where(runs.c.command_key == command_key)
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def pending(self):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(runs)
                        .where(runs.c.status == "QUEUED")
                        .order_by(runs.c.created_at)
                        .limit(50)
                    )
                )
                .mappings()
                .all()
            )

    async def latest(self, experiment_id: UUID, operator_id: UUID):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.experiment_id == experiment_id,
                            runs.c.operator_id == operator_id,
                        )
                        .order_by(runs.c.created_at.desc())
                        .limit(1)
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def incomplete(self):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(runs).where(
                            runs.c.status.in_(["RUNNING", "OUTCOME_UNKNOWN"])
                        )
                    )
                )
                .mappings()
                .all()
            )

    async def artifact(self, experiment_id: UUID, ref: dict):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == UUID(str(ref["artifact_id"])),
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind == ref["kind"],
                            records.artifacts.c.version == ref["version"],
                            records.artifacts.c.content_hash == ref["content_hash"],
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def profile_projection(self, row):
        async with self.engine.connect() as connection:
            profile = (
                (
                    await connection.execute(
                        select(records.operator_profiles).where(
                            records.operator_profiles.c.id == row["profile_id"],
                            records.operator_profiles.c.version
                            == row["profile_version"],
                            records.operator_profiles.c.content_hash
                            == row["profile_hash"],
                            records.operator_profiles.c.operator_id
                            == row["operator_id"],
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return profile

    async def details(self, run_id: UUID, task_kind: str):
        async with self.engine.connect() as connection:
            table = (
                records.idea_discoveries
                if task_kind == "IDEA_DISCOVERY"
                else records.idea_refinements
            )
            product = (
                (
                    await connection.execute(
                        select(table).where(table.c.run_id == run_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
            intent = (
                (
                    await connection.execute(
                        select(run_intents).where(
                            run_intents.c.idempotency_key == run_id
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            call = (
                (
                    await connection.execute(
                        select(gov.calls).where(gov.calls.c.idempotency_key == run_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
            usage = (
                (
                    await connection.execute(
                        select(gov.usage).where(gov.usage.c.call_id == call["id"])
                    )
                )
                .mappings()
                .all()
                if call
                else []
            )
            accepted = None
            if product and task_kind == "IDEA_REFINEMENT":
                accepted = await connection.scalar(
                    select(records.idea_acceptances.c.id)
                    .select_from(
                        records.idea_acceptances.join(
                            records.artifacts,
                            records.idea_acceptances.c.artifact_id
                            == records.artifacts.c.id,
                        )
                    )
                    .where(records.artifacts.c.operation_id == product["operation_id"])
                )
        return product, intent, call, usage, accepted

    async def start(self, run_id: UUID) -> bool:
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs).where(runs.c.run_id == run_id).with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if row["status"] != "QUEUED":
                return False
            now = datetime.now(UTC)
            await connection.execute(
                update(runs)
                .where(runs.c.run_id == run_id)
                .values(
                    status="RUNNING", started_at=now, events=_event(row, "RUNNING", now)
                )
            )
            return True

    async def append_diagnostic(self, run_id: UUID, diagnostic: dict):
        """Append a classified diagnostic without changing lifecycle state.

        The event log remains backwards compatible: historical events do not
        contain a ``diagnostic`` member, while new events add one safely.
        """
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs).where(runs.c.run_id == run_id).with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            if any(event.get("diagnostic") == diagnostic for event in row["events"]):
                return row
            now = datetime.now(UTC)
            return (
                (
                    await connection.execute(
                        update(runs)
                        .where(runs.c.run_id == run_id)
                        .values(
                            events=_event(
                                row,
                                "DIAGNOSTIC",
                                now,
                                detail=diagnostic["code"],
                                diagnostic=diagnostic,
                            )
                        )
                        .returning(runs)
                    )
                )
                .mappings()
                .one()
            )

    async def record_activity(
        self,
        run_id: UUID,
        event_type: str,
        detail: str | None = None,
        *,
        exchange: "RunExchange | None" = None,
    ):
        """Append a safe operator-visible activity event without lifecycle changes."""
        try:
            async with self.engine.begin() as connection:
                row = (
                    (
                        await connection.execute(
                            select(runs)
                            .where(runs.c.run_id == run_id)
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    return None
                now = datetime.now(UTC)
                return (
                    (
                        await connection.execute(
                            update(runs)
                            .where(runs.c.run_id == run_id)
                            .values(
                                events=_event(
                                    row,
                                    event_type,
                                    now,
                                    detail,
                                    exchange=exchange.model_dump(mode="json")
                                    if exchange
                                    else None,
                                )
                            )
                            .returning(runs)
                        )
                    )
                    .mappings()
                    .one()
                )
        except Exception as error:  # noqa: BLE001 - observability cannot change provider outcome
            structlog.get_logger(__name__).error(
                "agent_run_activity_persistence_failed",
                run_id=str(run_id),
                event_type=event_type,
                error_type=type(error).__name__,
            )
            return None

    async def finish(
        self,
        run_id: UUID,
        status: str,
        *,
        outcome: str | None = None,
        blocked_reason: str | None = None,
    ):
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs).where(runs.c.run_id == run_id).with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if row["status"] in {"SUCCEEDED", "BLOCKED", "FAILED", "CANCELLED"}:
                return row
            now = datetime.now(UTC)
            updated = (
                (
                    await connection.execute(
                        update(runs)
                        .where(runs.c.run_id == run_id)
                        .values(
                            status=status,
                            outcome=outcome,
                            blocked_reason=blocked_reason,
                            finished_at=now,
                            events=_event(row, status, now, blocked_reason),
                        )
                        .returning(runs)
                    )
                )
                .mappings()
                .one()
            )
            return updated

    async def cancel(self, run_id: UUID, operator_id: UUID, key: UUID):
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.run_id == run_id, runs.c.operator_id == operator_id
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
            if row["cancel_key"] is not None:
                if row["cancel_key"] != key:
                    raise ExperimentError(409, "COMMAND_CONFLICT")
                return row
            if row["status"] in {"SUCCEEDED", "BLOCKED", "FAILED", "CANCELLED"}:
                return row
            now = datetime.now(UTC)
            confirmed = row["status"] == "QUEUED"
            values = {
                "cancel_key": key,
                "cancel_requested_at": now,
                "cancel_confirmed": confirmed,
                "events": _event(
                    row, "CANCEL_CONFIRMED" if confirmed else "CANCEL_REQUESTED", now
                ),
            }
            if confirmed:
                values.update(status="CANCELLED", finished_at=now, outcome="CANCELLED")
                intake_finished = await connection.execute(
                    update(commands)
                    .where(
                        commands.c.command_key == row["command_key"],
                        commands.c.experiment_id == row["experiment_id"],
                        commands.c.state == "RUNNING",
                    )
                    .values(state="BLOCKED")
                )
                if intake_finished.rowcount == 1:
                    await connection.execute(
                        update(intakes)
                        .where(intakes.c.experiment_id == row["experiment_id"])
                        .values(blocked_reason="CANCELLED")
                    )
            elif row["status"] == "RUNNING":
                values.update(
                    status="OUTCOME_UNKNOWN",
                    blocked_reason="CANCEL_REQUESTED_AFTER_DISPATCH",
                )
            updated = (
                (
                    await connection.execute(
                        update(runs)
                        .where(runs.c.run_id == run_id)
                        .values(**values)
                        .returning(runs)
                    )
                )
                .mappings()
                .one()
            )
            return updated

    @asynccontextmanager
    async def revision_scope(self, run_id: UUID, operator_id: UUID):
        """Serialize revision admission with acceptance, rejection and other revisions."""
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.run_id == run_id, runs.c.operator_id == operator_id
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
            yield row

    @asynccontextmanager
    async def review_scope(self, run_id: UUID | None, operator_id: UUID):
        """Keep consuming a discovery result ordered before concurrent rejection."""
        if run_id is None:
            yield
            return
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.run_id == run_id,
                            runs.c.operator_id == operator_id,
                        )
                        .with_for_update(read=True)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is not None and row["review_status"] == "REJECTED":
                raise ExperimentError(409, "DISCOVERY_RUN_REJECTED")
            yield

    async def reject(self, run_id: UUID, operator_id: UUID, key: UUID, reason: str):
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.run_id == run_id, runs.c.operator_id == operator_id
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
            if row["review_status"] == "ACCEPTED":
                raise ExperimentError(409, "RUN_ALREADY_ACCEPTED")
            if row["review_key"] is not None:
                if row["review_key"] != key or row["review_reason"] != reason:
                    raise ExperimentError(409, "RUN_REVIEW_CONFLICT")
                return row
            if row["status"] != "SUCCEEDED" or row["review_status"] != "PENDING":
                raise ExperimentError(409, "RUN_NOT_REVIEWABLE")
            operation_id = await connection.scalar(
                select(records.idea_refinements.c.operation_id).where(
                    records.idea_refinements.c.run_id == run_id,
                    records.idea_refinements.c.experiment_id == row["experiment_id"],
                )
            )
            if operation_id is not None:
                accepted = await connection.scalar(
                    select(records.idea_acceptances.c.id)
                    .select_from(
                        records.idea_acceptances.join(
                            records.artifacts,
                            records.idea_acceptances.c.artifact_id
                            == records.artifacts.c.id,
                        )
                    )
                    .where(
                        records.idea_acceptances.c.experiment_id
                        == row["experiment_id"],
                        records.artifacts.c.operation_id == operation_id,
                    )
                )
                if accepted is not None:
                    raise ExperimentError(409, "RUN_ALREADY_ACCEPTED")
            now = datetime.now(UTC)
            return (
                (
                    await connection.execute(
                        update(runs)
                        .where(runs.c.run_id == run_id)
                        .values(
                            review_key=key,
                            review_status="REJECTED",
                            review_reason=reason,
                            events=_event(row, "REJECTED", now, reason),
                        )
                        .returning(runs)
                    )
                )
                .mappings()
                .one()
            )

    async def claim_acceptance(
        self, run_id: UUID, experiment_id: UUID, operator_id: UUID, key: UUID
    ):
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs)
                        .where(
                            runs.c.run_id == run_id,
                            runs.c.experiment_id == experiment_id,
                            runs.c.operator_id == operator_id,
                        )
                        .with_for_update()
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ExperimentError(404, "AGENT_RUN_NOT_FOUND")
            if row["review_status"] == "REJECTED":
                raise ExperimentError(409, "IDEA_RUN_REJECTED")
            if row["status"] != "SUCCEEDED":
                raise ExperimentError(409, "RUN_NOT_REVIEWABLE")
            if row["review_key"] is not None:
                if row["review_key"] != key or row["review_reason"] is not None:
                    raise ExperimentError(409, "RUN_REVIEW_CONFLICT")
                return row
            latest = await connection.scalar(
                select(runs.c.run_id)
                .where(runs.c.experiment_id == experiment_id)
                .order_by(runs.c.created_at.desc(), runs.c.run_id.desc())
                .limit(1)
            )
            if latest != run_id:
                raise ExperimentError(409, "IDEA_REVIEW_STALE")
            now = datetime.now(UTC)
            return (
                (
                    await connection.execute(
                        update(runs)
                        .where(runs.c.run_id == run_id)
                        .values(
                            review_key=key,
                            events=_event(row, "ACCEPT_REQUESTED", now),
                        )
                        .returning(runs)
                    )
                )
                .mappings()
                .one()
            )

    async def complete_acceptance(self, run_id: UUID, key: UUID):
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        select(runs).where(runs.c.run_id == run_id).with_for_update()
                    )
                )
                .mappings()
                .one()
            )
            if row["review_key"] != key or row["review_reason"] is not None:
                raise ExperimentError(409, "RUN_REVIEW_CONFLICT")
            if row["review_status"] == "ACCEPTED":
                return row
            now = datetime.now(UTC)
            return (
                (
                    await connection.execute(
                        update(runs)
                        .where(runs.c.run_id == run_id)
                        .values(
                            review_status="ACCEPTED",
                            events=_event(row, "ACCEPTED", now),
                        )
                        .returning(runs)
                    )
                )
                .mappings()
                .one()
            )
