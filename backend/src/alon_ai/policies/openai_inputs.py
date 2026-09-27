"""Deterministic OpenAI source scoping and retained-rights checks."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from alon_ai.agents.market_research import (
    MarketResearchAdvice,
    market_evidence_permitted,
)
from alon_ai.agents.schemas.openai import canonical_json
from alon_ai.integrations.schemas.provider import ContentField, Purpose
from alon_ai.policies.provider_rights import (
    GrantEvent,
    IntendedUse,
    ProviderUsageGrant,
    RightsMode,
    evaluate_rights,
)
from alon_ai.services.schemas.records import ArtifactKind

if TYPE_CHECKING:
    from alon_ai.agents.runtime import (
        AcceptedArtifact,
        AcceptedOperatorProfile,
        AcceptedSource,
    )
    from alon_ai.agents.schemas.openai import OpenAIProfile


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
