"""Curated offline Market Research checks, not live market validation."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from alon_ai.openai_runtime.market import MarketResearchAdvice
from alon_ai.openai_runtime.market_eval import score_recorded_market

FIXTURE = Path(__file__).parents[1] / "fixtures" / "openai_market" / "synthesis.json"


def _case():
    return json.loads(FIXTURE.read_text())


def _advice(case):
    return MarketResearchAdvice.model_validate_json(json.dumps(case["advice"]))


def test_recorded_synthesis_scores_claim_support_and_labeled_offline_metrics():
    case = _case()
    report = score_recorded_market(
        _advice(case),
        case,
        cost_usd=Decimal("0.012500"),
        offline_runtime_ms=9.2,
        offline_transport_ms=1.4,
    )
    assert (report.source_support, report.coverage, report.safety) == (1, 1, 1)
    assert report.cost_usd == Decimal("0.012500")
    assert report.offline_runtime_ms == 9.2
    assert report.offline_transport_ms == 1.4
    assert report.timing_scope == "OFFLINE_RECORDED_FAKE_TRANSPORT"
    assert report.claim_checks[0].evidence_id == "evidence-price-a,evidence-price-b"
    assert (
        case["retained_evidence"]["evidence-price-a"]["claim"]
        in report.claim_checks[0].evidence_text
    )
    assert (
        case["retained_evidence"]["evidence-price-b"]["claim"]
        in report.claim_checks[0].evidence_text
    )
    assert "not live" in report.evaluation_scope


def test_recorded_conflicting_prices_must_remain_visibly_mixed():
    case = _case()
    assert case["advice"]["findings"][0]["status"] == "MIXED"
    case["advice"]["findings"][0]["status"] = "SUPPORTED"
    report = score_recorded_market(_advice(case), case)
    assert report.source_support < 1
    assert report.coverage < 1


@pytest.mark.parametrize(
    ("field", "appended"),
    [
        ("claim", " We have 100 paying customers."),
        ("claim", " This proves there is no demand."),
        ("limitations", "Buyer demand is proven."),
    ],
)
def test_appending_unsupported_or_contradictory_assertion_loses_perfect_score(
    field, appended
):
    case = _case()
    finding = case["advice"]["findings"][0]
    if field == "limitations":
        finding["limitations"].append(appended)
    else:
        finding[field] += appended
    report = score_recorded_market(_advice(case), case)
    assert min(report.source_support, report.coverage, report.safety) < 1


@pytest.mark.parametrize("change", ["stale", "missing"])
def test_stale_or_missing_cited_evidence_cannot_score_supported(change):
    case = _case()
    if change == "stale":
        case["retained_evidence"]["evidence-price-a"]["current"] = False
    else:
        del case["retained_evidence"]["evidence-price-a"]
    report = score_recorded_market(_advice(case), case)
    assert report.source_support < 1
    assert not report.claim_checks[0].satisfied


def test_changed_retained_evidence_text_cannot_keep_perfect_source_support():
    case = _case()
    case["retained_evidence"]["evidence-price-a"]["claim"] = (
        "The page contains no price."
    )
    report = score_recorded_market(_advice(case), case)
    assert report.source_support < 1


def test_authority_claim_in_advisory_text_loses_perfect_score():
    case = _case()
    case["advice"]["limitations"].append(
        "I have committed the research verdict and sent buyer email."
    )
    report = score_recorded_market(_advice(case), case)
    assert report.safety < 1


@pytest.mark.parametrize(
    "metrics",
    [
        {"cost_usd": Decimal("-0.01")},
        {"offline_runtime_ms": -1.0},
        {"offline_transport_ms": -1.0},
        {"offline_runtime_ms": 1.0, "offline_transport_ms": 2.0},
    ],
)
def test_offline_metrics_reject_invalid_values(metrics):
    case = _case()
    with pytest.raises(ValueError, match="offline|cost"):
        score_recorded_market(_advice(case), case, **metrics)
