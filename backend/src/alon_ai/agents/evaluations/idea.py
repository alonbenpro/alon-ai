"""Deterministic, labeled offline evaluation of recorded Idea advice.

Fixture labels describe first-party input support, not market validation. A
proposal can satisfy coverage without becoming an externally verified fact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from alon_ai.agents.idea_discovery import (
    IdeaBriefAdvice,
    IdeaCandidateAdvice,
    IdeaStage,
    SeededIdeaBriefAdvice,
    SelectedCandidateIdeaBriefAdvice,
)


@dataclass(frozen=True)
class EvidenceFinding:
    field: str
    evidence_id: str
    evidence_text: str
    expected: object
    actual: object
    satisfied: bool


@dataclass(frozen=True)
class IdeaEvalReport:
    mode: IdeaStage
    claims: tuple[EvidenceFinding, ...]
    constraints: tuple[EvidenceFinding, ...]
    grounding: float
    coverage: float
    safety: float
    cost_usd: Decimal | None
    offline_runtime_ms: float | None
    offline_transport_ms: float | None


def _text(value: object) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _claim(
    advice: IdeaBriefAdvice | IdeaCandidateAdvice,
    fixture: dict[str, Any],
    claim: dict[str, Any],
) -> EvidenceFinding:
    source_fact = claim.get("source_fact")
    if source_fact is None:
        if claim.get("kind") != "UNVALIDATED_PROPOSAL":
            raise ValueError("expected claim lacks a source fact or proposal label")
        evidence_id = "DISCOVERY.UNVALIDATED_PROPOSAL"
        evidence_text = (
            "Unvalidated proposal; no observed customer, problem, or demand evidence"
        )
    else:
        evidence_id = str(source_fact)
        source_facts = fixture["source_facts"]
        if evidence_id not in source_facts:
            raise ValueError(f"expected claim cites unknown source fact: {evidence_id}")
        evidence_text = source_facts[evidence_id]
    field = claim["field"]
    actual = getattr(advice, field)
    if "expected_contains" in claim:
        expected = claim["expected_contains"]
        satisfied = _text(expected) in _text(actual)
    else:
        expected = claim["expected"]
        satisfied = _text(actual) == _text(expected)
    return EvidenceFinding(
        field, evidence_id, evidence_text, expected, actual, satisfied
    )


def _constraint(
    advice: IdeaBriefAdvice | IdeaCandidateAdvice,
    constraint: dict[str, Any],
) -> EvidenceFinding:
    kind = constraint["kind"]
    expected = constraint["expected"]
    if kind == "field_equals":
        actual = getattr(advice, constraint["field"])
        satisfied = actual == expected
    elif kind == "uncertainties_equal":
        actual = advice.uncertainties
        satisfied = tuple(actual) == tuple(expected)
    elif kind == "forbid_text":
        actual = json.dumps(
            advice.model_dump(mode="json", exclude={"schema_version"}),
            ensure_ascii=False,
        )
        satisfied = _text(expected) not in _text(actual)
    elif kind == "grounding_refs_equal":
        actual = advice.grounding_refs
        satisfied = tuple(actual) == tuple(expected)
    else:
        raise ValueError(f"unknown constraint kind: {kind}")
    return EvidenceFinding(
        constraint.get("field", kind),
        constraint["id"],
        constraint["basis"],
        expected,
        actual,
        satisfied,
    )


def score_recorded_idea(
    advice: IdeaBriefAdvice | IdeaCandidateAdvice,
    fixture: dict[str, Any],
    *,
    cost_usd: Decimal | None = None,
    offline_runtime_ms: float | None = None,
    offline_transport_ms: float | None = None,
) -> IdeaEvalReport:
    """Score exact fixture expectations and measured local fake-transport metrics.

    This intentionally bounded evaluator tests recorded answers. Perfect scores
    mean agreement with curated fixture text, not general semantic support or
    live OpenAI API latency.
    """

    mode = IdeaStage(fixture["mode"])
    expected_type = {
        IdeaStage.USER_SEEDED_REFINEMENT: SeededIdeaBriefAdvice,
        IdeaStage.SYSTEM_DISCOVERY: IdeaCandidateAdvice,
        IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: SelectedCandidateIdeaBriefAdvice,
    }[mode]
    if not isinstance(advice, expected_type):
        raise TypeError("mode and advice type disagree")
    if any(
        value is not None and value < 0
        for value in (cost_usd, offline_runtime_ms, offline_transport_ms)
    ):
        raise ValueError("cost and offline timing must be nonnegative")
    claims = tuple(
        _claim(advice, fixture, claim) for claim in fixture["expected_claims"]
    )
    constraints = tuple(
        _constraint(advice, constraint) for constraint in fixture["constraints"]
    )
    if not claims or not constraints:
        raise ValueError("evaluation requires claims and constraints")
    grounded = tuple(
        finding
        for claim, finding in zip(fixture["expected_claims"], claims, strict=True)
        if "source_fact" in claim
    )
    asserted = tuple(finding for finding in grounded if _text(finding.actual))
    grounding = (
        sum(finding.satisfied for finding in asserted) / len(asserted)
        if asserted
        else 0.0
    )
    coverage = sum(finding.satisfied for finding in claims) / len(claims)
    safety = sum(finding.satisfied for finding in constraints) / len(constraints)
    return IdeaEvalReport(
        mode=mode,
        claims=claims,
        constraints=constraints,
        grounding=grounding,
        coverage=coverage,
        safety=safety,
        cost_usd=cost_usd,
        offline_runtime_ms=offline_runtime_ms,
        offline_transport_ms=offline_transport_ms,
    )
