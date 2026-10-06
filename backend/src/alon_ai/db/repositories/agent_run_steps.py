"""Atomic child-step checkpoints for admitted Idea runs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.agent_run_steps import steps

_IDENTITY = (
    "run_id",
    "experiment_id",
    "step_key",
    "ordinal",
    "kind",
    "candidate_artifact_id",
    "candidate_kind",
    "candidate_version",
    "candidate_hash",
    "request_ref",
    "request_version",
    "request_hash",
    "config_ref",
    "config_version",
    "config_hash",
)


class AgentRunStepRepository:
    def __init__(self, engine):
        self.engine = engine

    async def claim(
        self,
        *,
        run_id: UUID,
        experiment_id: UUID,
        step_key: UUID,
        ordinal: int,
        kind: str,
        request_ref: UUID,
        request_version: int,
        request_hash: str,
        config_ref: UUID,
        config_version: int,
        config_hash: str,
        candidate_artifact_id: UUID | None = None,
        candidate_version: int | None = None,
        candidate_hash: str | None = None,
    ):
        row, _ = await self.claim_once(
            run_id=run_id,
            experiment_id=experiment_id,
            step_key=step_key,
            ordinal=ordinal,
            kind=kind,
            request_ref=request_ref,
            request_version=request_version,
            request_hash=request_hash,
            config_ref=config_ref,
            config_version=config_version,
            config_hash=config_hash,
            candidate_artifact_id=candidate_artifact_id,
            candidate_version=candidate_version,
            candidate_hash=candidate_hash,
        )
        return row

    async def claim_once(
        self,
        *,
        run_id: UUID,
        experiment_id: UUID,
        step_key: UUID,
        ordinal: int,
        kind: str,
        request_ref: UUID,
        request_version: int,
        request_hash: str,
        config_ref: UUID,
        config_version: int,
        config_hash: str,
        candidate_artifact_id: UUID | None = None,
        candidate_version: int | None = None,
        candidate_hash: str | None = None,
    ):
        identity = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "step_key": step_key,
            "ordinal": ordinal,
            "kind": kind,
            "candidate_artifact_id": candidate_artifact_id,
            "candidate_kind": "IDEA_CANDIDATE" if candidate_artifact_id else None,
            "candidate_version": candidate_version,
            "candidate_hash": candidate_hash,
            "request_ref": request_ref,
            "request_version": request_version,
            "request_hash": request_hash,
            "config_ref": config_ref,
            "config_version": config_version,
            "config_hash": config_hash,
        }
        async with self.engine.begin() as connection:
            inserted = await connection.scalar(
                insert(steps)
                .values(
                    **identity,
                    operation_id=None,
                    operation_workflow_id=None,
                    provider_call_id=None,
                    status="CLAIMED",
                    reason_code=None,
                    result_artifact_id=None,
                    result_kind=None,
                    result_version=None,
                    result_hash=None,
                    output_hash=None,
                    created_at=datetime.now(UTC),
                    finished_at=None,
                )
                .on_conflict_do_nothing(index_elements=["run_id", "step_key"])
                .returning(steps.c.run_id)
            )
            row = (
                (
                    await connection.execute(
                        select(steps).where(
                            steps.c.run_id == run_id, steps.c.step_key == step_key
                        )
                    )
                )
                .mappings()
                .one()
            )
            if any(row[field] != identity[field] for field in _IDENTITY):
                raise ExperimentError(409, "STEP_CONFLICT")
            return row, inserted is not None

    async def get(self, run_id: UUID, step_key: UUID):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(steps).where(
                            steps.c.run_id == run_id, steps.c.step_key == step_key
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def list(self, run_id: UUID):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(steps)
                        .where(steps.c.run_id == run_id)
                        .order_by(steps.c.ordinal, steps.c.step_key)
                    )
                )
                .mappings()
                .all()
            )

    async def receipts(self, run_id: UUID) -> list[dict]:
        """Project safe child status and governed accounting from one scoped query."""
        call_join = steps.outerjoin(
            gov.calls,
            and_(
                gov.calls.c.id == steps.c.provider_call_id,
                gov.calls.c.experiment_id == steps.c.experiment_id,
                or_(
                    steps.c.operation_id.is_(None),
                    gov.calls.c.operation_id == steps.c.operation_id,
                ),
            ),
        )
        config_join = call_join.outerjoin(
            gov.configs,
            and_(
                gov.configs.c.id == gov.calls.c.config_id,
                gov.configs.c.workflow_id == gov.calls.c.workflow_id,
                gov.configs.c.version == gov.calls.c.config_version,
            ),
        )
        joined = config_join.outerjoin(gov.usage, gov.usage.c.call_id == gov.calls.c.id)
        query = (
            select(
                steps,
                gov.calls.c.id.label("call_id"),
                gov.calls.c.idempotency_key.label("call_idempotency_key"),
                gov.calls.c.state.label("call_state"),
                gov.calls.c.currency.label("call_currency"),
                gov.calls.c.reserved.label("call_reserved"),
                gov.calls.c.reserved_ils.label("call_reserved_ils"),
                gov.calls.c.accrued.label("call_accrued"),
                gov.calls.c.accrued_ils.label("call_accrued_ils"),
                gov.configs.c.data["intended_use"]["provider"].astext.label(
                    "call_provider"
                ),
                gov.configs.c.data["model_identifier"].astext.label("call_model"),
                gov.usage.c.id.label("usage_id"),
                gov.usage.c.component.label("usage_component"),
                gov.usage.c.quantity.label("usage_quantity"),
                gov.usage.c.cost.label("usage_cost"),
                gov.usage.c.currency.label("usage_currency"),
                gov.usage.c.knowledge.label("usage_knowledge"),
                gov.usage.c.supersedes_id.label("usage_supersedes_id"),
                gov.usage.c.observed_at.label("usage_observed_at"),
            )
            .select_from(joined)
            .where(steps.c.run_id == run_id)
            .order_by(
                steps.c.ordinal,
                steps.c.step_key,
                gov.usage.c.observed_at,
                gov.usage.c.id,
            )
        )
        async with self.engine.connect() as connection:
            rows = (await connection.execute(query)).mappings().all()
        receipts: list[dict] = []
        for row in rows:
            if not receipts or receipts[-1]["step_key"] != row["step_key"]:
                receipts.append(
                    {
                        "run_id": row["run_id"],
                        "experiment_id": row["experiment_id"],
                        "step_key": row["step_key"],
                        "ordinal": row["ordinal"],
                        "kind": row["kind"],
                        "candidate_artifact_id": row["candidate_artifact_id"],
                        "candidate_version": row["candidate_version"],
                        "candidate_hash": row["candidate_hash"],
                        "operation_id": row["operation_id"],
                        "provider_call_id": row["provider_call_id"],
                        "status": row["status"],
                        "reason_code": row["reason_code"],
                        "result_artifact_id": row["result_artifact_id"],
                        "result_kind": row["result_kind"],
                        "result_version": row["result_version"],
                        "result_hash": row["result_hash"],
                        "output_hash": row["output_hash"],
                        "call": (
                            {
                                "id": row["call_id"],
                                "idempotency_key": row["call_idempotency_key"],
                                "provider": row["call_provider"],
                                "model_identifier": row["call_model"],
                                "state": row["call_state"],
                                "currency": row["call_currency"],
                                "reserved": row["call_reserved"],
                                "reserved_ils": row["call_reserved_ils"],
                                "accrued": row["call_accrued"],
                                "accrued_ils": row["call_accrued_ils"],
                            }
                            if row["call_id"] is not None
                            else None
                        ),
                        "usage": [],
                    }
                )
            if row["usage_id"] is not None:
                receipts[-1]["usage"].append(
                    {
                        "id": row["usage_id"],
                        "component": row["usage_component"],
                        "quantity": row["usage_quantity"],
                        "cost": row["usage_cost"],
                        "currency": row["usage_currency"],
                        "knowledge": row["usage_knowledge"],
                        "supersedes_id": row["usage_supersedes_id"],
                        "observed_at": row["usage_observed_at"],
                    }
                )
        return receipts

    async def bind(
        self,
        run_id: UUID,
        step_key: UUID,
        *,
        operation_id: UUID | None = None,
        operation_workflow_id: UUID | None = None,
        provider_call_id: UUID | None = None,
    ):
        if (operation_id is None) != (operation_workflow_id is None):
            raise ValueError("operation_id and operation_workflow_id must be paired")
        if operation_id is None and provider_call_id is None:
            raise ValueError("at least one external identifier is required")
        async with self.engine.begin() as connection:
            row = await self._locked(connection, run_id, step_key)
            values = {}
            for field, supplied in (
                ("operation_id", operation_id),
                ("operation_workflow_id", operation_workflow_id),
                ("provider_call_id", provider_call_id),
            ):
                if supplied is None:
                    continue
                if row[field] is not None and row[field] != supplied:
                    raise ExperimentError(409, "STEP_CONFLICT")
                values[field] = supplied
            if row["status"] != "CLAIMED":
                if all(row[field] == value for field, value in values.items()):
                    return row
                raise ExperimentError(409, "STEP_CONFLICT")
            return await self._update(connection, run_id, step_key, values)

    async def finish(
        self,
        run_id: UUID,
        step_key: UUID,
        *,
        status: str,
        reason_code: str | None = None,
        result_artifact_id: UUID | None = None,
        result_kind: str | None = None,
        result_version: int | None = None,
        result_hash: str | None = None,
        output_hash: str | None = None,
    ):
        if status not in {"SUCCEEDED", "BLOCKED", "FAILED", "OUTCOME_UNKNOWN"}:
            raise ValueError("finish requires a terminal status")
        result = {
            "status": status,
            "reason_code": reason_code,
            "result_artifact_id": result_artifact_id,
            "result_kind": result_kind,
            "result_version": result_version,
            "result_hash": result_hash,
            "output_hash": output_hash,
        }
        async with self.engine.begin() as connection:
            row = await self._locked(connection, run_id, step_key)
            if row["status"] != "CLAIMED":
                if all(row[field] == value for field, value in result.items()):
                    return row
                raise ExperimentError(409, "STEP_CONFLICT")
            return await self._update(
                connection,
                run_id,
                step_key,
                {**result, "finished_at": datetime.now(UTC)},
            )

    @staticmethod
    async def _locked(connection, run_id: UUID, step_key: UUID):
        row = (
            (
                await connection.execute(
                    select(steps)
                    .where(steps.c.run_id == run_id, steps.c.step_key == step_key)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ExperimentError(404, "STEP_NOT_FOUND")
        return row

    @staticmethod
    async def _update(connection, run_id: UUID, step_key: UUID, values: dict):
        return (
            (
                await connection.execute(
                    update(steps)
                    .where(steps.c.run_id == run_id, steps.c.step_key == step_key)
                    .values(**values)
                    .returning(steps)
                )
            )
            .mappings()
            .one()
        )
