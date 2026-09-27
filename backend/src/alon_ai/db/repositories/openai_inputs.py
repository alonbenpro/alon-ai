"""Exact persisted OpenAI input and current source authority reads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.agents.market_research import MARKET_EVIDENCE_POLICY_VERSION
from alon_ai.agents.schemas.openai import canonical_json
from alon_ai.db.tables import accounting as gov_schema
from alon_ai.db.tables import records as record_schema
from alon_ai.policies.openai_inputs import _current_retained_rights, _source_input
from alon_ai.policies.provider_rights import GrantEvent, ProviderUsageGrant
from alon_ai.services.schemas.records import ArtifactKind, SourceReference

if TYPE_CHECKING:
    from alon_ai.agents.runtime import (
        AcceptedArtifact,
        AcceptedOperatorProfile,
        AcceptedRetainedEvidence,
        AcceptedSource,
    )


async def accepted_input(
    engine: AsyncEngine,
    sources: tuple[AcceptedSource, ...],
    artifacts: tuple[AcceptedArtifact, ...],
    operator_profiles: tuple[AcceptedOperatorProfile, ...],
    retained_evidence: tuple[AcceptedRetainedEvidence, ...],
    experiment_id: UUID,
    now: datetime,
    *,
    grants: Mapping[tuple[UUID, int], ProviderUsageGrant] | None = None,
    events: tuple[GrantEvent, ...] = (),
) -> str:
    if (
        not sources
        and not artifacts
        and not operator_profiles
        and not retained_evidence
    ):
        raise PermissionError("accepted input required")
    source_entries = (
        json.loads(_source_input(sources, now, grants, events))["sources"]
        if sources
        else []
    )
    if not artifacts and not operator_profiles and not retained_evidence:
        return canonical_json({"sources": source_entries})
    entries = []
    profiles = []
    retained_entries = []
    async with engine.connect() as connection:
        if len(operator_profiles) > 1:
            raise PermissionError("only one experiment profile is accepted")
        for accepted_profile in operator_profiles:
            if accepted_profile.experiment_id != experiment_id:
                raise PermissionError("operator profile scope mismatch")
            profile = (
                (
                    await connection.execute(
                        select(record_schema.operator_profiles)
                        .select_from(
                            record_schema.experiments.join(
                                record_schema.operator_profiles,
                                record_schema.experiments.c.operator_profile_id
                                == record_schema.operator_profiles.c.id,
                            )
                        )
                        .where(
                            record_schema.experiments.c.id == experiment_id,
                            record_schema.experiments.c.operator_profile_version
                            == record_schema.operator_profiles.c.version,
                            record_schema.operator_profiles.c.id
                            == accepted_profile.profile_id,
                            record_schema.operator_profiles.c.version
                            == accepted_profile.version,
                            record_schema.operator_profiles.c.content_hash
                            == accepted_profile.content_hash,
                            record_schema.operator_profiles.c.profile_schema_version
                            == accepted_profile.profile_schema_version,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if profile is None:
                raise PermissionError("accepted operator profile changed")
            profiles.append(
                {
                    "ref": str(accepted_profile.profile_id),
                    "version": accepted_profile.version,
                    "schema_version": accepted_profile.profile_schema_version,
                    "hash": accepted_profile.content_hash,
                    "capabilities": profile["capabilities"],
                    "constraints": profile["constraints"],
                    "delivery": profile["delivery"],
                    "commercial": profile["commercial"],
                }
            )
        for accepted in artifacts:
            ref = accepted.artifact
            if accepted.experiment_id != experiment_id or ref.kind not in {
                ArtifactKind.IDEA_SEED,
                ArtifactKind.IDEA_CANDIDATE,
                ArtifactKind.EXPERIMENT_BRIEF,
                ArtifactKind.IDEA_BRIEF,
                ArtifactKind.RESEARCH_PLAN,
                ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
            }:
                raise PermissionError("artifact is outside accepted first-party inputs")
            row = (
                (
                    await connection.execute(
                        select(record_schema.artifacts).where(
                            record_schema.artifacts.c.id == ref.artifact_id,
                            record_schema.artifacts.c.experiment_id == experiment_id,
                            record_schema.artifacts.c.kind == ref.kind,
                            record_schema.artifacts.c.version == ref.version,
                            record_schema.artifacts.c.content_hash == ref.content_hash,
                            record_schema.artifacts.c.schema_version
                            == accepted.schema_version,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise PermissionError("accepted artifact identity changed")
            if await connection.scalar(
                select(record_schema.artifacts.c.id).where(
                    record_schema.artifacts.c.logical_id == row["logical_id"],
                    record_schema.artifacts.c.version > row["version"],
                )
            ):
                raise PermissionError("accepted artifact has a newer version")
            if await connection.scalar(
                select(record_schema.artifact_dispositions.c.id).where(
                    record_schema.artifact_dispositions.c.artifact_id
                    == ref.artifact_id,
                    record_schema.artifact_dispositions.c.disposition == "SUPERSEDED",
                )
            ):
                raise PermissionError("accepted artifact was superseded")
            if ref.kind not in {
                ArtifactKind.IDEA_BRIEF,
                ArtifactKind.RESEARCH_PLAN,
                ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
            } and (
                await connection.scalar(
                    select(record_schema.source_refs.c.id).where(
                        record_schema.source_refs.c.artifact_id == ref.artifact_id
                    )
                )
                or await connection.scalar(
                    select(record_schema.artifact_links.c.consumer_id).where(
                        record_schema.artifact_links.c.consumer_id == ref.artifact_id
                    )
                )
            ):
                raise PermissionError("artifact has external or linked inputs")
            if ref.kind is ArtifactKind.IDEA_BRIEF and accepted.return_id is not None:
                if accepted.cycle_id is None:
                    raise PermissionError("returned brief lacks a cycle")
                returned = await connection.scalar(
                    select(record_schema.returns.c.id).where(
                        record_schema.returns.c.id == accepted.return_id,
                        record_schema.returns.c.to_cycle_id == accepted.cycle_id,
                        record_schema.returns.c.idea_artifact_id == ref.artifact_id,
                    )
                )
                if returned is None:
                    raise PermissionError("returned brief lineage changed")
            elif ref.kind is ArtifactKind.IDEA_BRIEF:
                if (
                    accepted.cycle_id is None
                    or accepted.selection_id is not None
                    or accepted.attempt_id is not None
                ):
                    raise PermissionError("research requires an accepted idea cycle")
                accepted_cycle = await connection.scalar(
                    select(record_schema.cycles.c.id)
                    .select_from(
                        record_schema.cycles.join(
                            record_schema.idea_acceptances,
                            record_schema.cycles.c.id
                            == record_schema.idea_acceptances.c.cycle_id,
                        )
                    )
                    .where(
                        record_schema.cycles.c.id == accepted.cycle_id,
                        record_schema.cycles.c.experiment_id == experiment_id,
                        record_schema.idea_acceptances.c.artifact_id == ref.artifact_id,
                        record_schema.idea_acceptances.c.artifact_kind == ref.kind,
                        record_schema.idea_acceptances.c.artifact_version
                        == ref.version,
                        record_schema.idea_acceptances.c.artifact_hash
                        == ref.content_hash,
                        record_schema.cycles.c.id
                        == select(record_schema.cycles.c.id)
                        .where(record_schema.cycles.c.experiment_id == experiment_id)
                        .order_by(record_schema.cycles.c.ordinal.desc())
                        .limit(1)
                        .scalar_subquery(),
                    )
                )
                if accepted_cycle is None:
                    raise PermissionError(
                        "research idea is not the current accepted brief"
                    )
                state = await connection.scalar(
                    select(record_schema.cycle_states.c.state).where(
                        record_schema.cycle_states.c.cycle_id == accepted.cycle_id,
                        record_schema.cycle_states.c.experiment_id == experiment_id,
                    )
                )
                if state != "MARKET_RESEARCH":
                    raise PermissionError("research cycle is not active")
            elif ref.kind is ArtifactKind.RESEARCH_FEEDBACK_BRIEF:
                if accepted.return_id is None or accepted.cycle_id is None:
                    raise PermissionError("feedback lacks return lineage")
                returned = await connection.scalar(
                    select(record_schema.returns.c.id).where(
                        record_schema.returns.c.id == accepted.return_id,
                        record_schema.returns.c.to_cycle_id == accepted.cycle_id,
                        record_schema.returns.c.feedback_artifact_id == ref.artifact_id,
                        record_schema.returns.c.feedback_kind == ref.kind,
                        record_schema.returns.c.feedback_version == ref.version,
                        record_schema.returns.c.feedback_hash == ref.content_hash,
                    )
                )
                if returned is None:
                    raise PermissionError("feedback return lineage changed")
                if not await connection.scalar(
                    select(record_schema.artifact_dispositions.c.id).where(
                        record_schema.artifact_dispositions.c.artifact_id
                        == ref.artifact_id,
                        record_schema.artifact_dispositions.c.disposition == "ACCEPTED",
                    )
                ):
                    raise PermissionError("feedback is not committed")
            elif ref.kind is ArtifactKind.RESEARCH_PLAN:
                if (
                    accepted.cycle_id is None
                    or accepted.attempt_id is None
                    or accepted.selection_id is not None
                ):
                    raise PermissionError("research plan lacks an exact attempt")
                if await connection.scalar(
                    select(record_schema.source_refs.c.id).where(
                        record_schema.source_refs.c.artifact_id == ref.artifact_id
                    )
                ):
                    raise PermissionError("research plan has external sources")
                attempt = await connection.scalar(
                    select(record_schema.research_attempts.c.id)
                    .select_from(
                        record_schema.research_attempts.join(
                            record_schema.cycles,
                            record_schema.research_attempts.c.cycle_id
                            == record_schema.cycles.c.id,
                        )
                    )
                    .where(
                        record_schema.research_attempts.c.id == accepted.attempt_id,
                        record_schema.research_attempts.c.experiment_id
                        == experiment_id,
                        record_schema.research_attempts.c.cycle_id == accepted.cycle_id,
                        record_schema.research_attempts.c.plan_artifact_id
                        == ref.artifact_id,
                        record_schema.research_attempts.c.plan_kind == ref.kind,
                        record_schema.research_attempts.c.plan_version == ref.version,
                        record_schema.research_attempts.c.plan_hash == ref.content_hash,
                        record_schema.research_attempts.c.ordinal
                        == select(record_schema.research_attempts.c.ordinal)
                        .where(
                            record_schema.research_attempts.c.cycle_id
                            == accepted.cycle_id
                        )
                        .order_by(record_schema.research_attempts.c.ordinal.desc())
                        .limit(1)
                        .scalar_subquery(),
                        record_schema.cycles.c.id
                        == select(record_schema.cycles.c.id)
                        .where(record_schema.cycles.c.experiment_id == experiment_id)
                        .order_by(record_schema.cycles.c.ordinal.desc())
                        .limit(1)
                        .scalar_subquery(),
                    )
                )
                linked_brief = artifacts[0].artifact if artifacts else None
                plan_links = (
                    (
                        await connection.execute(
                            select(record_schema.artifact_links.c.role).where(
                                record_schema.artifact_links.c.consumer_id
                                == ref.artifact_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                plan_link = (
                    await connection.scalar(
                        select(record_schema.artifact_links.c.producer_id).where(
                            record_schema.artifact_links.c.consumer_id
                            == ref.artifact_id,
                            record_schema.artifact_links.c.role == "ACCEPTED_IDEA",
                            record_schema.artifact_links.c.producer_id
                            == linked_brief.artifact_id,
                            record_schema.artifact_links.c.producer_kind
                            == linked_brief.kind,
                            record_schema.artifact_links.c.producer_version
                            == linked_brief.version,
                            record_schema.artifact_links.c.producer_hash
                            == linked_brief.content_hash,
                        )
                    )
                    if linked_brief is not None
                    else None
                )
                state = await connection.scalar(
                    select(record_schema.cycle_states.c.state).where(
                        record_schema.cycle_states.c.cycle_id == accepted.cycle_id,
                        record_schema.cycle_states.c.experiment_id == experiment_id,
                    )
                )
                if (
                    attempt is None
                    or plan_link is None
                    or plan_links != ["ACCEPTED_IDEA"]
                    or state != "MARKET_RESEARCH"
                ):
                    raise PermissionError("research plan is not the active attempt")
            elif ref.kind is ArtifactKind.EXPERIMENT_BRIEF:
                if (
                    accepted.selection_id is not None
                    or accepted.cycle_id is not None
                    or accepted.attempt_id is not None
                ):
                    raise PermissionError(
                        "discovery brief cannot be selected or cycled"
                    )
                if row["created_by"] != await connection.scalar(
                    select(record_schema.operator_profiles.c.operator_id)
                    .select_from(
                        record_schema.experiments.join(
                            record_schema.operator_profiles,
                            (
                                record_schema.experiments.c.operator_profile_id
                                == record_schema.operator_profiles.c.id
                            )
                            & (
                                record_schema.experiments.c.operator_profile_version
                                == record_schema.operator_profiles.c.version
                            ),
                        )
                    )
                    .where(record_schema.experiments.c.id == experiment_id)
                ):
                    raise PermissionError("discovery brief is not operator supplied")
            elif ref.kind is ArtifactKind.IDEA_SEED:
                operator_id = await connection.scalar(
                    select(record_schema.operator_profiles.c.operator_id)
                    .select_from(
                        record_schema.experiments.join(
                            record_schema.operator_profiles,
                            record_schema.experiments.c.operator_profile_id
                            == record_schema.operator_profiles.c.id,
                        )
                    )
                    .where(
                        record_schema.experiments.c.id == experiment_id,
                        record_schema.experiments.c.operator_profile_version
                        == record_schema.operator_profiles.c.version,
                    )
                )
                if (
                    row["created_by"] != operator_id
                    or row["payload"].get("origin") != "USER_SUPPLIED"
                    or accepted.selection_id is not None
                    or accepted.cycle_id is None
                ):
                    raise PermissionError("idea seed is not operator supplied")
                seeded_cycle = await connection.scalar(
                    select(record_schema.cycles.c.id).where(
                        record_schema.cycles.c.id == accepted.cycle_id,
                        record_schema.cycles.c.experiment_id == experiment_id,
                        record_schema.cycles.c.idea_mode == "USER_SEEDED_REFINEMENT",
                        record_schema.cycles.c.purpose == "INITIAL",
                        record_schema.cycles.c.seed_artifact_id == ref.artifact_id,
                        record_schema.cycles.c.seed_version == ref.version,
                        record_schema.cycles.c.seed_hash == ref.content_hash,
                    )
                )
                if seeded_cycle is None:
                    raise PermissionError("idea seed is outside its cycle")
            else:
                if accepted.selection_id is None or accepted.cycle_id is None:
                    raise PermissionError("candidate requires selected cycle")
                selected = await connection.scalar(
                    select(record_schema.cycles.c.id)
                    .select_from(
                        record_schema.cycles.join(
                            record_schema.candidate_selections,
                            record_schema.cycles.c.selection_id
                            == record_schema.candidate_selections.c.id,
                        )
                    )
                    .where(
                        record_schema.cycles.c.id == accepted.cycle_id,
                        record_schema.cycles.c.experiment_id == experiment_id,
                        record_schema.cycles.c.idea_mode == "SYSTEM_DISCOVERY",
                        record_schema.cycles.c.purpose == "INITIAL",
                        record_schema.cycles.c.selection_id == accepted.selection_id,
                        record_schema.cycles.c.seed_artifact_id == ref.artifact_id,
                        record_schema.cycles.c.seed_version == ref.version,
                        record_schema.cycles.c.seed_hash == ref.content_hash,
                        record_schema.candidate_selections.c.artifact_id
                        == ref.artifact_id,
                        record_schema.candidate_selections.c.artifact_version
                        == ref.version,
                        record_schema.candidate_selections.c.artifact_hash
                        == ref.content_hash,
                    )
                )
                if selected is None:
                    raise PermissionError("candidate selection is not current")
            entries.append(
                {
                    "ref": str(ref.artifact_id),
                    "kind": ref.kind.value,
                    "version": ref.version,
                    "schema_version": accepted.schema_version,
                    "hash": ref.content_hash,
                    "role": ref.role,
                    "selection_id": str(accepted.selection_id)
                    if accepted.selection_id
                    else None,
                    "cycle_id": str(accepted.cycle_id) if accepted.cycle_id else None,
                    "attempt_id": str(accepted.attempt_id)
                    if accepted.attempt_id
                    else None,
                    "payload": row["payload"],
                }
            )
        if retained_evidence and (
            len(artifacts) != 2
            or artifacts[0].artifact.kind is not ArtifactKind.IDEA_BRIEF
            or artifacts[1].artifact.kind is not ArtifactKind.RESEARCH_PLAN
        ):
            raise PermissionError("retained research evidence requires accepted plan")
        seen_retained: set[UUID] = set()
        for item in retained_evidence:
            ref = item.reference
            if (
                ref.kind != "RETAINED_CONTENT"
                or ref.retained_id is None
                or ref.call_id is None
                or ref.grant_id is None
                or ref.grant_version is None
                or ref.field is None
                or ref.expires_at is None
                or ref.retained_id in seen_retained
            ):
                raise PermissionError("invalid retained evidence reference")
            seen_retained.add(ref.retained_id)
            row = (
                (
                    await connection.execute(
                        select(
                            gov_schema.retained,
                            gov_schema.calls.c.experiment_id,
                            gov_schema.calls.c.state,
                        )
                        .select_from(
                            gov_schema.retained.join(
                                gov_schema.calls,
                                gov_schema.retained.c.call_id == gov_schema.calls.c.id,
                            )
                        )
                        .where(
                            gov_schema.retained.c.id == ref.retained_id,
                            gov_schema.retained.c.call_id == ref.call_id,
                            gov_schema.retained.c.grant_id == ref.grant_id,
                            gov_schema.retained.c.grant_version == ref.grant_version,
                            gov_schema.retained.c.field == ref.field,
                            gov_schema.retained.c.expires_at == ref.expires_at,
                            gov_schema.retained.c.expires_at > now,
                            gov_schema.calls.c.experiment_id == experiment_id,
                            gov_schema.calls.c.state == "FINAL",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            grant = grants.get((ref.grant_id, ref.grant_version)) if grants else None
            if row is None or grant is None:
                raise PermissionError("retained evidence is missing or stale")
            plan = artifacts[1].artifact
            candidates = (
                (
                    await connection.execute(
                        select(
                            record_schema.artifacts.c.id,
                            record_schema.artifacts.c.logical_id,
                            record_schema.artifacts.c.version,
                        )
                        .select_from(
                            record_schema.source_refs.join(
                                record_schema.artifacts,
                                record_schema.source_refs.c.artifact_id
                                == record_schema.artifacts.c.id,
                            ).join(
                                record_schema.artifact_links,
                                record_schema.artifact_links.c.consumer_id
                                == record_schema.artifacts.c.id,
                            )
                        )
                        .where(
                            record_schema.source_refs.c.experiment_id == experiment_id,
                            record_schema.source_refs.c.kind == "RETAINED_CONTENT",
                            record_schema.source_refs.c.retained_id == ref.retained_id,
                            record_schema.source_refs.c.call_id == ref.call_id,
                            record_schema.source_refs.c.grant_id == ref.grant_id,
                            record_schema.source_refs.c.grant_version
                            == ref.grant_version,
                            record_schema.source_refs.c.field == ref.field,
                            record_schema.source_refs.c.expires_at == ref.expires_at,
                            record_schema.artifacts.c.experiment_id == experiment_id,
                            record_schema.artifacts.c.kind
                            == ArtifactKind.RESEARCH_EVIDENCE,
                            record_schema.artifact_links.c.role == "PLAN",
                            record_schema.artifact_links.c.producer_id
                            == plan.artifact_id,
                            record_schema.artifact_links.c.producer_kind == plan.kind,
                            record_schema.artifact_links.c.producer_version
                            == plan.version,
                            record_schema.artifact_links.c.producer_hash
                            == plan.content_hash,
                        )
                    )
                )
                .mappings()
                .all()
            )
            current_selection = False
            for candidate in candidates:
                newer = await connection.scalar(
                    select(record_schema.artifacts.c.id).where(
                        record_schema.artifacts.c.logical_id == candidate["logical_id"],
                        record_schema.artifacts.c.version > candidate["version"],
                    )
                )
                withdrawn = await connection.scalar(
                    select(record_schema.artifact_dispositions.c.id).where(
                        record_schema.artifact_dispositions.c.artifact_id
                        == candidate["id"],
                        record_schema.artifact_dispositions.c.disposition.in_(
                            ("SUPERSEDED", "REJECTED")
                        ),
                    )
                )
                if newer is None and withdrawn is None:
                    current_selection = True
                    break
            if not current_selection:
                raise PermissionError("retained source is outside the accepted plan")
            candidate_grants = tuple(
                ProviderUsageGrant.model_validate_json(json.dumps(data, default=str))
                for data in (
                    await connection.execute(
                        select(gov_schema.grants.c.data).where(
                            gov_schema.grants.c.account == grant.account_handle,
                            gov_schema.grants.c.capability == grant.capability,
                        )
                    )
                ).scalars()
            )
            authority_enabled = await connection.scalar(
                select(gov_schema.authorities.c.enabled).where(
                    gov_schema.authorities.c.account == grant.account_handle,
                    gov_schema.authorities.c.capability == grant.capability,
                )
            )
            if authority_enabled is not True:
                raise PermissionError("retained source authority is disabled")
            if (
                not _current_retained_rights(
                    grant, candidate_grants, events, ref.field, now
                )
                or not isinstance(row["values"], list)
                or not row["values"]
                or any(not isinstance(value, str) for value in row["values"])
            ):
                raise PermissionError("retained evidence rights are not current")
            retained_entries.append(
                {
                    "ref": str(ref.retained_id),
                    "field": ref.field,
                    "values": row["values"],
                    "expires_at": ref.expires_at.isoformat(),
                }
            )
    return canonical_json(
        {
            "sources": source_entries,
            "artifacts": entries,
            "operator_profiles": profiles,
            "retained_evidence": retained_entries,
            "evidence_policy_version": MARKET_EVIDENCE_POLICY_VERSION
            if retained_evidence
            else None,
        }
    )


@asynccontextmanager
async def experiment_dispatch_guard(engine: AsyncEngine, experiment_id: UUID):
    """Hold the experiment's shared lock through a bounded provider dispatch."""
    async with engine.begin() as connection:
        enabled = await connection.scalar(
            select(gov_schema.experiments.c.enabled)
            .where(gov_schema.experiments.c.id == experiment_id)
            .with_for_update(read=True)
        )
        yield enabled


async def retained_rights_status(
    engine: AsyncEngine,
    retained_evidence: tuple[AcceptedRetainedEvidence, ...],
    grants: Mapping[tuple[UUID, int], ProviderUsageGrant],
) -> list[
    tuple[
        SourceReference, ProviderUsageGrant, tuple[ProviderUsageGrant, ...], bool | None
    ]
]:
    rights = []
    async with engine.connect() as connection:
        for item in retained_evidence:
            ref = item.reference
            if ref.grant_id is None or ref.grant_version is None:
                raise PermissionError("retained evidence grant is missing")
            grant = grants.get((ref.grant_id, ref.grant_version))
            if grant is None:
                raise PermissionError("retained evidence grant is missing")
            candidates = tuple(
                ProviderUsageGrant.model_validate_json(json.dumps(data, default=str))
                for data in (
                    await connection.execute(
                        select(gov_schema.grants.c.data).where(
                            gov_schema.grants.c.account == grant.account_handle,
                            gov_schema.grants.c.capability == grant.capability,
                        )
                    )
                ).scalars()
            )
            enabled = await connection.scalar(
                select(gov_schema.authorities.c.enabled).where(
                    gov_schema.authorities.c.account == grant.account_handle,
                    gov_schema.authorities.c.capability == grant.capability,
                )
            )
            rights.append((ref, grant, candidates, enabled))
    return rights
