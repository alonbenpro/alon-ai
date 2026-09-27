"""Durable immutable run intent, committed before any provider dispatch."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.schemas.run import (
    Hash,
    OpenAIRunConflict,
    OpenAIRunIntent,
    OpenAIRunNotFound,
    OpenAIRunOutcome,
    OpenAIRunRecord,
    OpenAIRunStoreError,
)
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.openai import run_intents


def _record(row) -> OpenAIRunRecord:
    return OpenAIRunRecord.model_validate(
        {
            **row,
            "accepted_input_refs": tuple(row["accepted_input_refs"]),
            "outcome": OpenAIRunOutcome(row["outcome"]),
        }
    )


def _same_intent(record: OpenAIRunRecord, intent: OpenAIRunIntent) -> bool:
    return all(
        getattr(record, field) == getattr(intent, field)
        for field in OpenAIRunIntent.model_fields
    )


class OpenAIRunStore:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def begin(self, intent: OpenAIRunIntent) -> OpenAIRunRecord:
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    pg_insert(run_intents)
                    .values(
                        **intent.model_dump(mode="python"),
                        outcome=OpenAIRunOutcome.READY,
                    )
                    .on_conflict_do_nothing(index_elements=["idempotency_key"])
                )
                row = (
                    (
                        await connection.execute(
                            select(run_intents).where(
                                run_intents.c.idempotency_key == intent.idempotency_key
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                record = _record(row)
                if not _same_intent(record, intent):
                    raise OpenAIRunConflict()
                return record
        except SQLAlchemyError:
            raise OpenAIRunStoreError() from None

    async def finish(
        self,
        key: UUID,
        call_id: UUID | None,
        outcome: OpenAIRunOutcome,
        output_hash: Hash | None,
    ) -> OpenAIRunRecord:
        if outcome == OpenAIRunOutcome.READY:
            raise OpenAIRunConflict()
        if outcome == OpenAIRunOutcome.NO_AI and call_id is not None:
            raise OpenAIRunConflict()
        if outcome == OpenAIRunOutcome.SUCCEEDED and (
            call_id is None or output_hash is None
        ):
            raise OpenAIRunConflict()
        if output_hash is not None and (
            len(output_hash) != 64
            or any(c not in "0123456789abcdef" for c in output_hash)
        ):
            raise OpenAIRunConflict()
        try:
            async with self.engine.begin() as connection:
                if call_id is not None:
                    ledger = (
                        await connection.execute(
                            select(gov.calls.c.id)
                            .select_from(
                                gov.calls.join(
                                    run_intents,
                                    gov.calls.c.idempotency_key
                                    == run_intents.c.idempotency_key,
                                )
                            )
                            .where(
                                gov.calls.c.id == call_id,
                                run_intents.c.idempotency_key == key,
                                gov.calls.c.config_id == run_intents.c.config_id,
                                gov.calls.c.config_version
                                == run_intents.c.config_version,
                                gov.calls.c.experiment_id
                                == run_intents.c.experiment_id,
                                gov.calls.c.workflow_id == run_intents.c.workflow_id,
                                gov.calls.c.operation_id == run_intents.c.operation_id,
                                *(
                                    [
                                        gov.calls.c.state == "FINAL",
                                        gov.calls.c.result_metadata["status"].astext
                                        == "SUCCEEDED",
                                    ]
                                    if outcome == OpenAIRunOutcome.SUCCEEDED
                                    else []
                                ),
                            )
                        )
                    ).scalar_one_or_none()
                    if ledger is None:
                        raise OpenAIRunConflict()
                await connection.execute(
                    update(run_intents)
                    .where(
                        run_intents.c.idempotency_key == key,
                        run_intents.c.outcome.in_(
                            [OpenAIRunOutcome.READY, OpenAIRunOutcome.RECOVERING]
                        ),
                    )
                    .values(
                        call_id=call_id,
                        outcome=outcome,
                        output_hash=output_hash,
                        finished_at=None
                        if outcome == OpenAIRunOutcome.RECOVERING
                        else datetime.now(UTC),
                    )
                )
                row = (
                    (
                        await connection.execute(
                            select(run_intents).where(
                                run_intents.c.idempotency_key == key
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    raise OpenAIRunNotFound()
                record = _record(row)
                if (
                    record.call_id != call_id
                    or record.outcome != outcome
                    or record.output_hash != output_hash
                ):
                    raise OpenAIRunConflict()
                return record
        except SQLAlchemyError:
            raise OpenAIRunStoreError() from None

    async def recover(self, key: UUID) -> OpenAIRunRecord:
        """Recover only safe ledger facts. Lost licensed output is never regenerated."""
        try:
            async with self.engine.begin() as connection:
                row = (
                    (
                        await connection.execute(
                            select(run_intents)
                            .where(run_intents.c.idempotency_key == key)
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    raise OpenAIRunNotFound()
                record = _record(row)
                if record.outcome not in {
                    OpenAIRunOutcome.READY,
                    OpenAIRunOutcome.RECOVERING,
                }:
                    return record
                ledger = (
                    (
                        await connection.execute(
                            select(gov.calls).where(
                                gov.calls.c.idempotency_key == key,
                                gov.calls.c.config_id == record.config_id,
                                gov.calls.c.config_version == record.config_version,
                                gov.calls.c.experiment_id == record.experiment_id,
                                gov.calls.c.workflow_id == record.workflow_id,
                                gov.calls.c.operation_id == record.operation_id,
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if ledger is None:
                    return record
                metadata = ledger["result_metadata"] or {}
                status = metadata.get("status")
                if status == "SUCCEEDED" or ledger["state"] == "FINAL" and not metadata:
                    outcome = OpenAIRunOutcome.RESULT_UNAVAILABLE
                elif status == "REFUSED":
                    outcome = OpenAIRunOutcome.REFUSED
                elif status == "FAILED":
                    error_code = metadata.get("error_code")
                    outcome = (
                        {
                            "MALFORMED_RESPONSE": OpenAIRunOutcome.SCHEMA_MISMATCH,
                            "INCOMPLETE_RESULT": OpenAIRunOutcome.INCOMPLETE,
                            "CANCELLED_RESULT": OpenAIRunOutcome.CANCELLED,
                        }.get(error_code, OpenAIRunOutcome.FAILED)
                        if isinstance(error_code, str)
                        else OpenAIRunOutcome.FAILED
                    )
                elif ledger["state"] == "RELEASED":
                    outcome = OpenAIRunOutcome.FAILED
                else:
                    outcome = OpenAIRunOutcome.RECOVERING
                if record.outcome == outcome and record.call_id == ledger["id"]:
                    return record
                updated = (
                    (
                        await connection.execute(
                            update(run_intents)
                            .where(run_intents.c.idempotency_key == key)
                            .values(
                                call_id=ledger["id"],
                                outcome=outcome,
                                finished_at=None
                                if outcome == OpenAIRunOutcome.RECOVERING
                                else datetime.now(UTC),
                            )
                            .returning(run_intents)
                        )
                    )
                    .mappings()
                    .one()
                )
                return _record(updated)
        except SQLAlchemyError:
            raise OpenAIRunStoreError() from None

    async def get(self, key: UUID) -> OpenAIRunRecord | None:
        try:
            async with self.engine.connect() as connection:
                row = (
                    (
                        await connection.execute(
                            select(run_intents).where(
                                run_intents.c.idempotency_key == key
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                return _record(row) if row is not None else None
        except SQLAlchemyError:
            raise OpenAIRunStoreError() from None
