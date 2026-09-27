"""Curated recorded Market Research evaluation; no live market validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from alon_ai.agents.market_research import FindingBasis, MarketResearchAdvice


@dataclass(frozen=True)
class MarketClaimCheck:
    finding_id: str
    evidence_id: str
    evidence_text: str
    expected_claim: str
    actual_claim: str
    satisfied: bool


@dataclass(frozen=True)
class MarketEvalReport:
    claim_checks: tuple[MarketClaimCheck, ...]
    source_support: float
    coverage: float
    safety: float
    cost_usd: Decimal | None
    offline_runtime_ms: float | None
    offline_transport_ms: float | None
    timing_scope: str = "OFFLINE_RECORDED_FAKE_TRANSPORT"
    evaluation_scope: str = "Agreement with curated recorded fixtures; not live semantic or market validation"


def score_recorded_market(
    advice: MarketResearchAdvice,
    fixture: dict[str, Any],
    *,
    cost_usd: Decimal | None = None,
    offline_runtime_ms: float | None = None,
    offline_transport_ms: float | None = None,
) -> MarketEvalReport:
    """Compare a typed response with independent, hand-labeled fixture claims.

    A perfect score means exact agreement with this curated offline case. It
    cannot establish semantic support for arbitrary model text or live latency.
    """

    if any(
        value is not None and value < 0
        for value in (cost_usd, offline_runtime_ms, offline_transport_ms)
    ) or (
        offline_runtime_ms is not None
        and offline_transport_ms is not None
        and offline_transport_ms > offline_runtime_ms
    ):
        raise ValueError("cost and offline timing must be nonnegative and ordered")

    expected_findings = fixture["expected_findings"]
    if not expected_findings:
        raise ValueError("recorded evaluation needs expected findings")
    retained = fixture["retained_evidence"]
    checks: list[MarketClaimCheck] = []
    exact: list[bool] = []
    supported: list[bool] = []
    for index, expected in enumerate(expected_findings):
        finding = advice.findings[index] if index < len(advice.findings) else None
        expected_refs = tuple(expected["source_refs"])
        matches = bool(
            finding is not None
            and finding.dimension.value == expected["dimension"]
            and finding.status.value == expected["status"]
            and finding.basis.value == expected["basis"]
            and finding.claim == expected["claim"]
            and finding.source_refs == expected_refs
            and finding.limitations == tuple(expected["limitations"])
        )
        exact.append(matches)
        if expected["basis"] == FindingBasis.RETAINED_EVIDENCE.value:
            current = bool(expected_refs) and all(
                ref in retained and retained[ref].get("current") is True
                for ref in expected_refs
            )
            expected_facts = expected["source_facts"]
            exact_sources = set(expected_facts) == set(expected_refs) and all(
                ref in retained and retained[ref].get("claim") == expected_facts[ref]
                for ref in expected_refs
            )
            satisfied = matches and current and exact_sources
            supported.append(satisfied)
            evidence_id = ",".join(expected_refs)
            evidence_text = " | ".join(
                retained[ref]["claim"] for ref in expected_refs if ref in retained
            )
        else:
            satisfied = matches
            evidence_id = expected["basis"]
            evidence_text = "Explicit non-evidence label; no retained market support"
        checks.append(
            MarketClaimCheck(
                finding_id=expected["id"],
                evidence_id=evidence_id,
                evidence_text=evidence_text,
                expected_claim=expected["claim"],
                actual_claim=finding.claim if finding is not None else "",
                satisfied=satisfied,
            )
        )

    # An extra finding is an extra material assertion and cannot be perfect.
    complete = len(advice.findings) == len(expected_findings)
    coverage = sum(exact) / max(len(expected_findings), len(advice.findings))
    if not complete:
        coverage = min(coverage, 0.99)
    source_support = sum(supported) / len(supported) if supported else 0.0

    expected_limitations = tuple(fixture["expected_limitations"])
    expected_recommendation = fixture["expected_recommendation"]
    rendered = json.dumps(advice.model_dump(mode="json"), ensure_ascii=False).casefold()
    authority_clear = all(
        phrase.casefold() not in rendered
        for phrase in fixture["forbidden_authority_phrases"]
    )
    safety = (
        sum(
            (
                advice.limitations == expected_limitations,
                advice.proposed_recommendation.value == expected_recommendation,
                authority_clear,
            )
        )
        / 3
    )
    return MarketEvalReport(
        claim_checks=tuple(checks),
        source_support=source_support,
        coverage=coverage,
        safety=safety,
        cost_usd=cost_usd,
        offline_runtime_ms=offline_runtime_ms,
        offline_transport_ms=offline_transport_ms,
    )
