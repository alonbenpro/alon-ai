"""Application-owned OpenAI execution through the existing governed read path."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_CEILING, Decimal, localcontext
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting import schema as gov_schema
from alon_ai.accounting.models import (
    CallReceipt,
    CallState,
    CapabilityConfig,
    PriceVersion,
)
from alon_ai.accounting.repository import GovernanceRepository
from alon_ai.openai_runtime.authority import OpenAIAuthorityStore
from alon_ai.openai_runtime.contract import (
    OpenAIProfile,
    ParsedResponse,
    Route,
    RoutingFacts,
    RoutingPolicy,
    StrictDTO,
    canonical_json,
    classify_response,
    sha256,
)
from alon_ai.openai_runtime.market import (
    MARKET_EVIDENCE_POLICY_VERSION,
    MarketResearchAdvice,
    market_evidence_permitted,
)
from alon_ai.openai_runtime.store import (
    OpenAIRunConflict,
    OpenAIRunIntent,
    OpenAIRunOutcome,
    OpenAIRunRecord,
    OpenAIRunStore,
)
from alon_ai.openai_runtime.transport import ResponsesTransport
from alon_ai.providers.contracts import (
    AgentActor,
    CallAttribution,
    Capability,
    ContentField,
    CostKnowledge,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderResultMetadata,
    Purpose,
    ResultStatus,
    SafeRequestMetadata,
    UsageComponent,
    UsageObservation,
)
from alon_ai.providers.execution import GovernedExecutor
from alon_ai.providers.rights import (
    GrantEvent,
    IntendedUse,
    ProviderUsageGrant,
    RightsMode,
    RuntimeContent,
    evaluate_rights,
)
from alon_ai.records import schema as record_schema
from alon_ai.records.models import ArtifactInput, ArtifactKind, SourceReference
from alon_ai.security.secrets import SecretStore


@dataclass(frozen=True)
class AcceptedSource:
    """Current source grant is supplied by the trusted content repository."""

    evidence_ref: UUID
    content: RuntimeContent
    current_grant: ProviderUsageGrant
    events: tuple[GrantEvent, ...] = ()


@dataclass(frozen=True)
class AcceptedArtifact:
    """An exact persisted product record reference, resolved by the runtime."""

    artifact: ArtifactInput
    experiment_id: UUID
    schema_version: int
    selection_id: UUID | None = None
    cycle_id: UUID | None = None
    attempt_id: UUID | None = None


@dataclass(frozen=True)
class AcceptedOperatorProfile:
    """Exact experiment-bound first-party capability context."""

    profile_id: UUID
    version: int
    content_hash: str
    experiment_id: UUID
    profile_schema_version: int = 2


@dataclass(frozen=True)
class AcceptedRetainedEvidence:
    """An exact persisted source row, not caller-provided evidence text."""

    reference: SourceReference


def _require_market_inputs(
    profile: OpenAIProfile,
    sources: tuple[AcceptedSource, ...],
    artifacts: tuple[AcceptedArtifact, ...],
    operator_profiles: tuple[AcceptedOperatorProfile, ...],
) -> None:
    if profile.output_model is not MarketResearchAdvice:
        return
    if sources or operator_profiles or len(artifacts) != 2:
        raise PermissionError("Market synthesis requires accepted brief and plan")
    brief, plan = artifacts
    if (
        brief.artifact.kind is not ArtifactKind.IDEA_BRIEF
        or brief.artifact.role != "ACCEPTED_IDEA"
        or brief.cycle_id is None
        or brief.attempt_id is not None
        or plan.artifact.kind is not ArtifactKind.RESEARCH_PLAN
        or plan.artifact.role != "PLAN"
        or plan.cycle_id != brief.cycle_id
        or plan.attempt_id is None
        or plan.selection_id is not None
    ):
        raise PermissionError("Market synthesis requires accepted brief and plan")


@dataclass(frozen=True)
class OpenAIExecution:
    route: Route
    outcome: OpenAIRunOutcome
    receipt: CallReceipt | None
    output: StrictDTO | None = field(repr=False)

    def __reduce_ex__(self, protocol: object):
        raise TypeError("advisory runtime output cannot be serialized")


def _source_input(
    sources: tuple[AcceptedSource, ...],
    now: datetime,
    grants: Mapping[tuple[UUID, int], ProviderUsageGrant] | None = None,
    events: tuple[GrantEvent, ...] = (),
) -> str:
    if not sources:
        raise PermissionError("licensed source content required")
    scoped = []
    for source in sources:
        grant = (
            source.current_grant
            if grants is None
            else grants.get(
                (source.current_grant.grant_id, source.current_grant.version)
            )
        )
        if grant is None or grant.purpose is not Purpose.GENERATION:
            raise PermissionError("source grant does not authorize model generation")
        retained = source.content.retain(
            current_grant=grant, events=source.events + events, now=now
        )
        scoped.append(
            {
                "ref": str(source.evidence_ref),
                "grant": str(retained.grant_id),
                "fields": {
                    key.value: list(value)
                    for key, value in sorted(retained.fields.items())
                },
            }
        )
    return canonical_json({"sources": scoped})


def _current_retained_rights(
    grant: ProviderUsageGrant,
    candidates: tuple[ProviderUsageGrant, ...],
    events: tuple[GrantEvent, ...],
    field_name: str,
    now: datetime,
) -> bool:
    try:
        field = ContentField(field_name)
    except ValueError:
        return False
    if not market_evidence_permitted(grant, field):
        return False
    active = tuple(g for g in candidates if g.effective_at <= now < g.expires_at)
    superseded = {g.supersedes_id for g in active if g.supersedes_id}
    current = tuple(g for g in active if g.grant_id not in superseded)
    use = IntendedUse(
        provider=grant.provider,
        account_handle=grant.account_handle,
        capability=grant.capability,
        plan_identifier=grant.plan_identifier,
        order_form_ref=grant.order_form_ref,
        terms_version=grant.terms_version,
        purpose=Purpose.RESEARCH,
        required_fields=frozenset({field}),
    )
    return (
        len(current) == 1
        and current[0] == grant
        and evaluate_rights(grant, events, use, now=now).mode
        is RightsMode.RETAIN_SCOPED_CONTENT
    )


async def _accepted_input(
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
                }
            )
        for accepted in artifacts:
            ref = accepted.artifact
            if accepted.experiment_id != experiment_id or ref.kind not in {
                ArtifactKind.IDEA_SEED,
                ArtifactKind.IDEA_CANDIDATE,
                ArtifactKind.IDEA_BRIEF,
                ArtifactKind.RESEARCH_PLAN,
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
            if ref.kind is ArtifactKind.IDEA_BRIEF:
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


def _priced_usage(
    parsed: ParsedResponse, prices: tuple[PriceVersion, ...], key: UUID
) -> tuple[UsageObservation, ...]:
    observations = []
    for price in prices:
        component = price.component
        counts = parsed.usage
        quantity: Decimal | None
        if component is UsageComponent.REQUEST:
            quantity = Decimal(1)
        elif counts is None:
            quantity = None
        elif component is UsageComponent.INPUT_TOKEN:
            # When a separate cached-token price exists, input is the uncached
            # remainder. Otherwise this one price covers every input token.
            has_cached_price = any(
                p.component is UsageComponent.CACHED_TOKEN for p in prices
            )
            quantity = (
                Decimal(
                    counts["input_tokens"]
                    - (counts["cached_tokens"] if has_cached_price else 0)
                )
                if not has_cached_price or "cached_tokens" in counts
                else None
            )
        elif component is UsageComponent.OUTPUT_TOKEN:
            quantity = Decimal(counts["output_tokens"])
        elif component is UsageComponent.CACHED_TOKEN:
            quantity = (
                Decimal(counts["cached_tokens"]) if "cached_tokens" in counts else None
            )
        else:
            quantity = None
        with localcontext() as ctx:
            ctx.prec = 64
            cost = (
                (quantity * price.unit_price / price.unit_quantity).quantize(
                    Decimal("1e-12"), rounding=ROUND_CEILING
                )
                if quantity is not None
                else None
            )
        observations.append(
            UsageObservation(
                component=component,
                quantity=quantity,
                currency=price.currency,
                cost=cost,
                knowledge=CostKnowledge.FINAL
                if quantity is not None
                else CostKnowledge.UNAVAILABLE,
                observation_key=uuid5(key, component.value),
            )
        )
    return tuple(observations)


def _verify_pricing_bounds(
    config: CapabilityConfig,
    prices: tuple[PriceVersion, ...],
    profile: OpenAIProfile,
    input_json: str,
) -> None:
    priced = {price.component: price for price in prices}
    allowed = {
        UsageComponent.REQUEST,
        UsageComponent.INPUT_TOKEN,
        UsageComponent.OUTPUT_TOKEN,
        UsageComponent.CACHED_TOKEN,
    }
    if (
        not {UsageComponent.INPUT_TOKEN, UsageComponent.OUTPUT_TOKEN} <= priced.keys()
        or not priced.keys() <= allowed
    ):
        raise PermissionError("configured OpenAI token prices are incomplete")
    bounds = {
        price.component: next(
            bound.max_quantity for bound in config.prices if bound.price_id == price.id
        )
        for price in prices
    }
    # Byte count plus protocol headroom is a conservative token ceiling for
    # supplied text, instructions and schema. The output bound is explicit.
    input_ceiling = Decimal(
        len((input_json + profile.instructions + profile.schema_json).encode("utf-8"))
        + 1024
    )
    if (
        bounds[UsageComponent.INPUT_TOKEN] < input_ceiling
        or bounds[UsageComponent.OUTPUT_TOKEN] < profile.max_output_tokens
        or (
            UsageComponent.CACHED_TOKEN in bounds
            and bounds[UsageComponent.CACHED_TOKEN] < input_ceiling
        )
    ):
        raise PermissionError("configured OpenAI token reservation is insufficient")


class _ConfiguredResponsesAdapter:
    def __init__(
        self,
        *,
        profile: OpenAIProfile,
        input_json: str,
        client_request_id: UUID,
        key: UUID,
        prices: tuple[PriceVersion, ...],
        transport: ResponsesTransport,
        clock,
        authority: OpenAIAuthorityStore,
        routes: RoutingPolicy,
        facts: RoutingFacts,
        scope: UUID,
        sources: tuple[AcceptedSource, ...],
        artifacts: tuple[AcceptedArtifact, ...],
        operator_profiles: tuple[AcceptedOperatorProfile, ...],
        retained_evidence: tuple[AcceptedRetainedEvidence, ...],
        engine: AsyncEngine,
    ):
        self.profile = profile
        self.input_json = input_json
        self.client_request_id = client_request_id
        self.key = key
        self.prices = prices
        self.transport = transport
        self.clock = clock
        self.authority = authority
        self.routes = routes
        self.facts = facts
        self.scope = scope
        self.sources = sources
        self.artifacts = artifacts
        self.operator_profiles = operator_profiles
        self.retained_evidence = retained_evidence
        self.engine = engine
        self.parsed: ParsedResponse | None = None

    async def invoke(
        self, config: CapabilityConfig, secret: SecretStr | None, /
    ) -> ProviderCallResult[RuntimeContent]:
        if (
            config.id != self.profile.config_id
            or config.version != self.profile.config_version
            or config.adapter_version != self.profile.adapter_version
            or config.model_identifier != self.profile.model_identifier
            or config.intended_use.capability is not Capability.OPENAI_GENERATE
            or config.intended_use.purpose is not Purpose.GENERATION
            or secret is None
        ):
            raise ValueError("configured OpenAI capability mismatch")
        approval = (
            self.facts.premium_authorization if self.facts.premium_requested else None
        )
        async with AsyncExitStack() as stack:
            root_enabled = True
            if self.artifacts:
                # Product commands take this experiment lock before changing
                # versions, acceptances or cycle state. Keep the same order as
                # governance: experiment first, then provider authority.
                product_lock = await stack.enter_async_context(self.engine.begin())
                root_enabled = await product_lock.scalar(
                    select(gov_schema.experiments.c.enabled)
                    .where(gov_schema.experiments.c.id == self.scope)
                    .with_for_update(read=True)
                )
            snapshot = await stack.enter_async_context(
                self.authority.dispatch_guard(
                    tuple(
                        (source.current_grant.grant_id, source.current_grant.version)
                        for source in self.sources
                    )
                    + tuple(
                        (item.reference.grant_id, item.reference.grant_version)
                        for item in self.retained_evidence
                        if item.reference.grant_id is not None
                        and item.reference.grant_version is not None
                    ),
                    approval.authorization_id if approval else None,
                )
            )
            # Locks serialize revocation with this bounded transport operation.
            # Time validity is checked after every lock/snapshot wait.
            started = self.clock()
            try:
                if root_enabled is not True:
                    raise PermissionError("experiment was disabled before dispatch")
                _require_market_inputs(
                    self.profile,
                    self.sources,
                    self.artifacts,
                    self.operator_profiles,
                )
                self.routes.select(self.facts, scope=self.scope, now=started)
                if self.facts.premium_requested and (
                    approval is None
                    or snapshot.approval != approval
                    or snapshot.approval_config_id != config.id
                    or snapshot.revoked_at is not None
                    and snapshot.revoked_at <= started
                ):
                    raise PermissionError("premium approval is not current")
                input_json = await _accepted_input(
                    self.engine,
                    self.sources,
                    self.artifacts,
                    self.operator_profiles,
                    self.retained_evidence,
                    self.scope,
                    started,
                    grants=snapshot.grants,
                    events=snapshot.events,
                )
                retained_rights = []
                if self.retained_evidence:
                    async with self.engine.connect() as connection:
                        for item in self.retained_evidence:
                            ref = item.reference
                            if ref.grant_id is None or ref.grant_version is None:
                                raise PermissionError(
                                    "retained evidence grant is missing"
                                )
                            grant = snapshot.grants.get(
                                (ref.grant_id, ref.grant_version)
                            )
                            if grant is None:
                                raise PermissionError(
                                    "retained evidence grant is missing"
                                )
                            candidates = tuple(
                                ProviderUsageGrant.model_validate_json(
                                    json.dumps(data, default=str)
                                )
                                for data in (
                                    await connection.execute(
                                        select(gov_schema.grants.c.data).where(
                                            gov_schema.grants.c.account
                                            == grant.account_handle,
                                            gov_schema.grants.c.capability
                                            == grant.capability,
                                        )
                                    )
                                ).scalars()
                            )
                            enabled = await connection.scalar(
                                select(gov_schema.authorities.c.enabled).where(
                                    gov_schema.authorities.c.account
                                    == grant.account_handle,
                                    gov_schema.authorities.c.capability
                                    == grant.capability,
                                )
                            )
                            retained_rights.append((ref, grant, candidates, enabled))
                # Artifact/profile reads can wait on the DB after the first
                # authority check. Re-evaluate rights at the final dispatch
                # time; no further DB await occurs before transport.
                started = self.clock()
                self.routes.select(self.facts, scope=self.scope, now=started)
                if self.facts.premium_requested and (
                    approval is None
                    or snapshot.approval != approval
                    or snapshot.approval_config_id != config.id
                    or snapshot.revoked_at is not None
                    and snapshot.revoked_at <= started
                ):
                    raise PermissionError("premium approval is not current")
                if self.sources:
                    _source_input(
                        self.sources, started, snapshot.grants, snapshot.events
                    )
                for ref, grant, candidates, enabled in retained_rights:
                    if (
                        ref.expires_at is None
                        or ref.field is None
                        or started >= ref.expires_at
                        or enabled is not True
                        or not _current_retained_rights(
                            grant, candidates, snapshot.events, ref.field, started
                        )
                    ):
                        raise PermissionError(
                            "retained evidence rights changed before dispatch"
                        )
                if sha256(input_json) != sha256(self.input_json):
                    raise PermissionError("accepted source content changed")
            except PermissionError:
                # Positive evidence of no transport means zero billable usage.
                return ProviderCallResult(
                    ProviderResultMetadata(
                        capability=Capability.OPENAI_GENERATE,
                        started_at=started,
                        finished_at=started,
                        status=ResultStatus.FAILED,
                        error_code=ProviderErrorCode.DENIED,
                        usage=tuple(
                            UsageObservation(
                                component=price.component,
                                quantity=Decimal(0),
                                cost=Decimal(0),
                                currency=price.currency,
                                knowledge=CostKnowledge.FINAL,
                                observation_key=uuid5(self.key, price.component.value),
                            )
                            for price in self.prices
                        ),
                    ),
                    None,
                )
            response = await self.transport.create(
                profile=self.profile,
                input_json=input_json,
                secret=secret,
                client_request_id=self.client_request_id,
                timeout_seconds=self.profile.timeout_seconds,
            )
        finished = self.clock()
        parsed = classify_response(response, self.profile)
        if (
            parsed.outcome == "SUCCEEDED"
            and parsed.output is not None
            and self.profile.output_validator is not None
        ):
            try:
                self.profile.output_validator(parsed.output, input_json)
            except (PermissionError, ValueError):
                parsed = ParsedResponse(
                    "SCHEMA_MISMATCH",
                    None,
                    None,
                    parsed.usage,
                    parsed.external_request_id,
                )
        self.parsed = parsed
        status, error = {
            "SUCCEEDED": (ResultStatus.SUCCEEDED, None),
            "REFUSED": (ResultStatus.REFUSED, ProviderErrorCode.REFUSED),
            "SCHEMA_MISMATCH": (
                ResultStatus.FAILED,
                ProviderErrorCode.MALFORMED_RESPONSE,
            ),
            "INCOMPLETE": (ResultStatus.FAILED, ProviderErrorCode.INCOMPLETE_RESULT),
            "FAILED": (ResultStatus.FAILED, ProviderErrorCode.UNAVAILABLE),
            "CANCELLED": (ResultStatus.FAILED, ProviderErrorCode.CANCELLED_RESULT),
            "UNCERTAIN": (ResultStatus.UNKNOWN, ProviderErrorCode.UNAVAILABLE),
        }[parsed.outcome]
        return ProviderCallResult(
            ProviderResultMetadata(
                capability=Capability.OPENAI_GENERATE,
                external_request_id=parsed.external_request_id,
                started_at=started,
                finished_at=finished,
                status=status,
                error_code=error,
                usage=_priced_usage(parsed, self.prices, self.key),
            ),
            None,
        )


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
        adapter = _ConfiguredResponsesAdapter(
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
