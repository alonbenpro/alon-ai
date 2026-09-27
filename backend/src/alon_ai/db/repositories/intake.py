"""Database ownership, command deduplication and proposal history for intake."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from alon_ai.agents.schemas.openai import canonical_json, sha256
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.tables import records
from alon_ai.db.tables.intake import commands, intakes


class IntakeRepository:
    def __init__(self, engine):
        self.engine = engine

    async def get(self, experiment_id: UUID, operator_id: UUID):
        async with self.engine.connect() as c:
            return (
                (
                    await c.execute(
                        select(intakes).where(
                            intakes.c.experiment_id == experiment_id,
                            intakes.c.operator_id == operator_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def reserve(
        self, experiment_id, command_key, operator_id, idea_seed, draft, profile, budget
    ):
        """Pin approved context before any separately committed root/artifact writes."""
        async with self.engine.begin() as c:
            await c.execute(
                insert(intakes)
                .values(
                    experiment_id=experiment_id,
                    command_key=command_key,
                    operator_id=operator_id,
                    idea_seed=idea_seed,
                    draft=draft,
                    profile_id=profile["id"],
                    profile_version=profile["version"],
                    budget_usd=str(budget),
                    created_at=datetime.now(UTC),
                )
                .on_conflict_do_nothing()
            )
            row = (
                (
                    await c.execute(
                        select(intakes).where(intakes.c.experiment_id == experiment_id)
                    )
                )
                .mappings()
                .one()
            )
            if (
                row["operator_id"] != operator_id
                or row["idea_seed"] != idea_seed
                or row["command_key"] != command_key
            ):
                raise ExperimentError(409, "COMMAND_CONFLICT")
            return row

    async def has_commands(self, experiment_id) -> bool:
        async with self.engine.connect() as c:
            return (
                await c.scalar(
                    select(commands.c.command_key)
                    .where(commands.c.experiment_id == experiment_id)
                    .limit(1)
                )
            ) is not None

    async def has_refinement(self, experiment_id) -> bool:
        async with self.engine.connect() as c:
            return (
                await c.scalar(
                    select(records.idea_refinements.c.run_id)
                    .where(records.idea_refinements.c.experiment_id == experiment_id)
                    .limit(1)
                )
            ) is not None

    async def owns_command(self, experiment_id, key) -> bool:
        async with self.engine.connect() as c:
            return (
                await c.scalar(
                    select(commands.c.command_key).where(
                        commands.c.experiment_id == experiment_id,
                        commands.c.command_key == key,
                        commands.c.state == "RUNNING",
                    )
                )
            ) is not None

    async def pending(self, experiment_id):
        async with self.engine.connect() as c:
            return (
                (
                    await c.execute(
                        select(commands)
                        .where(
                            commands.c.experiment_id == experiment_id,
                            commands.c.state == "RUNNING",
                        )
                        .order_by(commands.c.created_at.desc())
                        .limit(1)
                    )
                )
                .mappings()
                .one_or_none()
            )

    async def receipt(self, experiment_id, key, result=None, *, expected_run_id=None):
        async with self.engine.begin() as c:
            if result is not None:
                # Serialize receipt capture with new command admission. A snapshot
                # assembled after another command cannot become this command's result.
                await c.execute(
                    select(intakes.c.experiment_id)
                    .where(intakes.c.experiment_id == experiment_id)
                    .with_for_update()
                )
            command = (
                (
                    await c.execute(
                        select(commands).where(
                            commands.c.experiment_id == experiment_id,
                            commands.c.command_key == key,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if command is None:
                return None
            if command["result"] is not None or result is None:
                return command["result"]
            if command["state"] == "RUNNING" or result.get("stage_status") == "RUNNING":
                return None
            newer = await c.scalar(
                select(commands.c.command_key)
                .where(
                    commands.c.experiment_id == experiment_id,
                    commands.c.command_key != key,
                    commands.c.created_at >= command["created_at"],
                )
                .limit(1)
            )
            if newer is not None:
                raise ExperimentError(409, "INTAKE_RECONCILIATION_REQUIRED")
            if expected_run_id is not None:
                refined = await c.scalar(
                    select(records.idea_refinements.c.run_id).where(
                        records.idea_refinements.c.experiment_id == experiment_id,
                        records.idea_refinements.c.run_id == expected_run_id,
                    )
                )
                discovered = await c.scalar(
                    select(records.idea_discoveries.c.run_id).where(
                        records.idea_discoveries.c.experiment_id == experiment_id,
                        records.idea_discoveries.c.run_id == expected_run_id,
                    )
                )
                if (refined is not None or discovered is not None) and result.get(
                    "latest_run_id"
                ) != str(expected_run_id):
                    raise ExperimentError(409, "INTAKE_RECONCILIATION_REQUIRED")
            if command["action"] == "REVISE" and result.get("cycle_id") is not None:
                raise ExperimentError(409, "INTAKE_RECONCILIATION_REQUIRED")
            await c.execute(
                update(commands)
                .where(
                    commands.c.experiment_id == experiment_id,
                    commands.c.command_key == key,
                    commands.c.result.is_(None),
                )
                .values(result=result)
            )
            return result

    async def replayed(self, experiment_id, command_key, action, payload) -> bool:
        request_hash = sha256(
            canonical_json(
                {
                    "experiment_id": str(experiment_id),
                    "action": action,
                    "payload": payload,
                }
            )
        )
        async with self.engine.connect() as c:
            old = (
                (
                    await c.execute(
                        select(commands).where(commands.c.command_key == command_key)
                    )
                )
                .mappings()
                .one_or_none()
            )
        if old is None:
            return False
        if old["request_hash"] != request_hash:
            raise ExperimentError(409, "COMMAND_CONFLICT")
        return True

    async def clear_block(self, experiment_id):
        async with self.engine.begin() as c:
            await c.execute(
                update(intakes)
                .where(intakes.c.experiment_id == experiment_id)
                .values(blocked_reason=None)
            )

    async def claim(self, experiment_id, command_key, action, payload):
        request_hash = sha256(
            canonical_json(
                {
                    "experiment_id": str(experiment_id),
                    "action": action,
                    "payload": payload,
                }
            )
        )
        async with self.engine.begin() as c:
            # Serialize every intake action so revision/start cannot race dispatch.
            await c.execute(
                select(intakes.c.experiment_id)
                .where(intakes.c.experiment_id == experiment_id)
                .with_for_update()
            )
            old = (
                (
                    await c.execute(
                        select(commands).where(commands.c.command_key == command_key)
                    )
                )
                .mappings()
                .one_or_none()
            )
            if old is not None:
                if old["request_hash"] != request_hash:
                    raise ExperimentError(409, "COMMAND_CONFLICT")
                return False
            draft = await c.scalar(
                select(intakes.c.draft).where(intakes.c.experiment_id == experiment_id)
            )
            if action in {"START_PROPOSAL", "REVISE", "REGENERATE"} and not draft:
                raise ExperimentError(409, "EXPERIMENT_ALREADY_STARTED")
            running = await c.scalar(
                select(commands.c.command_key)
                .where(
                    commands.c.experiment_id == experiment_id,
                    commands.c.state == "RUNNING",
                )
                .limit(1)
            )
            if running is not None:
                raise ExperimentError(409, "INTAKE_IN_PROGRESS")
            await c.execute(
                insert(commands).values(
                    command_key=command_key,
                    experiment_id=experiment_id,
                    request_hash=request_hash,
                    action=action,
                    payload=payload,
                    state="RUNNING",
                    created_at=datetime.now(UTC),
                )
            )
            await c.execute(
                update(intakes)
                .where(intakes.c.experiment_id == experiment_id)
                .values(blocked_reason=None)
            )
            return True

    async def finish(
        self, experiment_id, command_key, *, blocked_reason=None, started=False
    ):
        async with self.engine.begin() as c:
            finished = await c.execute(
                update(commands)
                .where(
                    commands.c.command_key == command_key,
                    commands.c.experiment_id == experiment_id,
                    commands.c.state == "RUNNING",
                )
                .values(state="BLOCKED" if blocked_reason else "COMPLETE")
            )
            if finished.rowcount != 1:
                return
            values = {"blocked_reason": blocked_reason}
            if started:
                values["draft"] = False
            await c.execute(
                update(intakes)
                .where(intakes.c.experiment_id == experiment_id)
                .values(**values)
            )

    async def history(self, experiment_id) -> list[dict[str, Any]]:
        async with self.engine.connect() as c:
            artifacts = (
                (
                    await c.execute(
                        select(records.artifacts)
                        .where(
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind == "IDEA_CANDIDATE",
                        )
                        .order_by(
                            records.artifacts.c.created_at, records.artifacts.c.id
                        )
                    )
                )
                .mappings()
                .all()
            )
            links = (
                (
                    await c.execute(
                        select(records.artifact_links).where(
                            records.artifact_links.c.consumer_id.in_(
                                [r["id"] for r in artifacts]
                            )
                        )
                    )
                )
                .mappings()
                .all()
                if artifacts
                else []
            )
            runs = (
                (
                    await c.execute(
                        select(records.idea_discoveries).where(
                            records.idea_discoveries.c.experiment_id == experiment_id,
                            records.idea_discoveries.c.state == "SUCCEEDED",
                        )
                    )
                )
                .mappings()
                .all()
            )
            edits = (
                (
                    await c.execute(
                        select(commands).where(
                            commands.c.experiment_id == experiment_id,
                            commands.c.action.in_(["REVISE", "REGENERATE"]),
                            commands.c.state == "COMPLETE",
                        )
                    )
                )
                .mappings()
                .all()
            )
        complete_ids = {str(item) for run in runs for item in run["candidate_ids"]}
        complete_ids.update(
            edit["payload"]["revision_id"]
            for edit in edits
            if edit["action"] == "REVISE"
        )
        history = []
        for row in artifacts:
            if str(row["id"]) not in complete_ids:
                continue
            run_id = next(
                (
                    run["run_id"]
                    for run in runs
                    if str(row["id"]) in run["candidate_ids"]
                ),
                None,
            )
            parent = next(
                (
                    link["producer_id"]
                    for link in links
                    if link["consumer_id"] == row["id"]
                ),
                None,
            )
            if parent is None and run_id is not None:
                parent = next(
                    (
                        UUID(command["payload"]["candidate_artifact_id"])
                        for command in edits
                        if command["action"] == "REGENERATE"
                        and command["payload"].get("run_id") == str(run_id)
                        and command["payload"].get("candidate_artifact_id")
                    ),
                    None,
                )
            history.append(dict(row, parent_artifact_id=parent, run_id=run_id))
        return history


async def verified_intake_links(connection, row) -> bool:
    """Allow only links whose exact contents were committed by an intake command.

    This does not relax the generic linked-input guard: sources stay forbidden,
    and arbitrary artifact links or edited command payloads cannot grant authority.
    """
    chain = [row]
    seen = set()
    while chain:
        current = chain.pop()
        if current["id"] in seen or len(seen) >= 100:
            return False
        seen.add(current["id"])
        if await connection.scalar(
            select(records.source_refs.c.id).where(
                records.source_refs.c.artifact_id == current["id"]
            )
        ):
            return False
        links = (
            (
                await connection.execute(
                    select(records.artifact_links).where(
                        records.artifact_links.c.consumer_id == current["id"]
                    )
                )
            )
            .mappings()
            .all()
        )
        if not links:
            # A leaf must belong to a fully committed governed discovery batch.
            runs = (
                (
                    await connection.execute(
                        select(records.idea_discoveries.c.candidate_ids).where(
                            records.idea_discoveries.c.experiment_id
                            == row["experiment_id"],
                            records.idea_discoveries.c.state == "SUCCEEDED",
                        )
                    )
                )
                .scalars()
                .all()
            )
            if current["kind"] != "IDEA_CANDIDATE" or not any(
                str(current["id"]) in ids for ids in runs
            ):
                return False
            continue
        if len(links) != 1:
            return False
        link = links[0]
        action = (
            "REVISE"
            if current["kind"] == "IDEA_CANDIDATE"
            else "REGENERATE"
            if current["kind"] == "EXPERIMENT_BRIEF"
            else None
        )
        if action is None or link["role"] != (
            "REFINES" if action == "REVISE" else "GUIDANCE"
        ):
            return False
        key = "revision_id" if action == "REVISE" else "guidance_artifact_id"
        command = (
            (
                await connection.execute(
                    select(commands).where(
                        commands.c.experiment_id == row["experiment_id"],
                        commands.c.action == action,
                        commands.c.payload[key].astext == str(current["id"]),
                        commands.c.state.in_(
                            ["COMPLETE"]
                            if action == "REVISE"
                            else ["RUNNING", "COMPLETE"]
                        ),
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if command is None or command["payload"]["candidate_artifact_id"] != str(
            link["producer_id"]
        ):
            return False
        parent = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == link["producer_id"],
                        records.artifacts.c.experiment_id == row["experiment_id"],
                        records.artifacts.c.kind == "IDEA_CANDIDATE",
                        records.artifacts.c.version == link["producer_version"],
                        records.artifacts.c.content_hash == link["producer_hash"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if parent is None:
            return False
        owner = await connection.scalar(
            select(intakes.c.operator_id).where(
                intakes.c.experiment_id == row["experiment_id"]
            )
        )
        if current["created_by"] != owner:
            return False
        if (
            action == "REVISE"
            and current["payload"]["hypothesis"] != command["payload"]["idea_seed"]
        ):
            return False
        if (
            action == "REGENERATE"
            and current["payload"].get("guidance") != parent["payload"]["hypothesis"]
        ):
            return False
        chain.append(parent)
    return True
