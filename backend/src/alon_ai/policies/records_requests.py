"""Stable request fingerprints shared by records and durable commands."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any
from uuid import UUID

from pydantic_core import to_jsonable_python

from alon_ai.services.schemas.records import ArtifactInput, ResearchCycleBudgetInput


def _request_hash(**request: Any) -> str:
    """Fingerprint the complete immutable request; link/source ordering is not semantic."""
    normalized = to_jsonable_python(request)
    for name in ("inputs", "sources"):
        if name in normalized:
            normalized[name].sort(key=lambda item: json.dumps(item, sort_keys=True))
    return sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def market_research_request_hash(
    *,
    experiment_id: UUID,
    cycle_id: UUID,
    accepted_idea: ArtifactInput,
    plan: ArtifactInput,
) -> str:
    """Return the exact hash used by the authoritative transition command."""
    return _request_hash(
        experiment_id=experiment_id,
        cycle_id=cycle_id,
        accepted_idea=accepted_idea,
        plan=plan,
    )


def market_research_outcome_request_hash(
    *,
    attempt_id: UUID,
    report: ArtifactInput,
    recommendation: ArtifactInput,
    verdict: str,
    committed_by: UUID,
    feedback: ArtifactInput | None = None,
    feedback_validation: ArtifactInput | None = None,
    proposed_idea: ArtifactInput | None = None,
    plan: ArtifactInput | None = None,
    budget: ResearchCycleBudgetInput | None = None,
    accepted_by: UUID | None = None,
) -> str:
    return _request_hash(
        attempt_id=attempt_id,
        report=report,
        recommendation=recommendation,
        verdict=verdict,
        committed_by=committed_by,
        feedback=feedback,
        feedback_validation=feedback_validation,
        proposed_idea=proposed_idea,
        plan=plan,
        budget=budget,
        accepted_by=accepted_by,
    )


def material_pivot_decision_request_hash(
    *,
    verdict_id: UUID,
    decision_id: UUID,
    decision: str,
    decided_by: UUID,
    reason_code: str,
    proposed_idea: ArtifactInput | None = None,
    feedback: ArtifactInput | None = None,
    feedback_validation: ArtifactInput | None = None,
    plan: ArtifactInput | None = None,
    budget: ResearchCycleBudgetInput | None = None,
    accepted_by: UUID | None = None,
) -> str:
    return _request_hash(
        verdict_id=verdict_id,
        decision_id=decision_id,
        decision=decision,
        decided_by=decided_by,
        reason_code=reason_code,
        proposed_idea=proposed_idea,
        feedback=feedback,
        feedback_validation=feedback_validation,
        plan=plan,
        budget=budget,
        accepted_by=accepted_by,
    )


def inconclusive_supplement_request_hash(
    *,
    verdict_id: UUID,
    feedback: ArtifactInput,
    feedback_validation: ArtifactInput,
    plan: ArtifactInput,
    budget: ResearchCycleBudgetInput,
    accepted_by: UUID,
) -> str:
    return _request_hash(
        verdict_id=verdict_id,
        feedback=feedback,
        feedback_validation=feedback_validation,
        plan=plan,
        budget=budget,
        accepted_by=accepted_by,
    )
