"""Exact persisted Idea inputs used by the governed agent run service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.runtime import AcceptedOperatorProfile
from alon_ai.db.tables import records
from alon_ai.services.schemas.records import ArtifactKind


class OpenAIIdeaInputRepository:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def operator_profile(self, experiment_id: UUID) -> AcceptedOperatorProfile:
        async with self.engine.connect() as connection:
            profile = (
                (
                    await connection.execute(
                        select(
                            records.operator_profiles.c.id,
                            records.operator_profiles.c.version,
                            records.operator_profiles.c.content_hash,
                        )
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
                        .where(records.experiments.c.id == experiment_id)
                    )
                )
                .mappings()
                .one_or_none()
            )
        if profile is None:
            raise PermissionError("Idea run requires an exact operator profile")
        return AcceptedOperatorProfile(
            profile_id=profile["id"],
            version=profile["version"],
            content_hash=profile["content_hash"],
            experiment_id=experiment_id,
            profile_schema_version=2,
        )

    async def experiment_brief(self, experiment_id: UUID):
        async with self.engine.connect() as connection:
            brief = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind == ArtifactKind.EXPERIMENT_BRIEF,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return brief

    async def cycle_origin(self, experiment_id: UUID, cycle_id: UUID):
        async with self.engine.connect() as connection:
            cycle = (
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.id == cycle_id,
                            records.cycles.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if cycle is None:
                raise PermissionError("Idea cycle is not in the attributed experiment")
            if cycle["purpose"] not in {"INITIAL", "SAME_INTENT_RETURN"}:
                raise PermissionError(
                    "Idea profile is limited to initial and same-intent cycles"
                )
            schema_version = await connection.scalar(
                select(records.artifacts.c.schema_version).where(
                    records.artifacts.c.id == cycle["seed_artifact_id"],
                    records.artifacts.c.experiment_id == experiment_id,
                    records.artifacts.c.kind == cycle["seed_kind"],
                    records.artifacts.c.version == cycle["seed_version"],
                    records.artifacts.c.content_hash == cycle["seed_hash"],
                )
            )
        return cycle, schema_version

    async def return_inputs(self, experiment_id: UUID, cycle_id: UUID):
        async with self.engine.connect() as connection:
            returned = (
                (
                    await connection.execute(
                        select(records.returns).where(
                            records.returns.c.to_cycle_id == cycle_id,
                            records.returns.c.experiment_id == experiment_id,
                            records.returns.c.kind == "SAME_INTENT",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if returned is None:
                raise PermissionError("same-intent cycle lacks return evidence")
            prior = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == returned["idea_artifact_id"],
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind == ArtifactKind.IDEA_BRIEF,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            feedback = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == returned["feedback_artifact_id"],
                            records.artifacts.c.experiment_id == experiment_id,
                            records.artifacts.c.kind
                            == ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
        return returned, prior, feedback
