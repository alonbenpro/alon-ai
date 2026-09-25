"""Recorded shape and reference boundaries for Market Research advice."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from alon_ai.openai_runtime.contract import classify_response
from alon_ai.openai_runtime.market import (
    MarketFinding,
    MarketResearchAdvice,
    market_profile,
    validate_market_references,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "openai_market" / "synthesis.json"


def _case():
    return json.loads(FIXTURE.read_text())


def _profile():
    return market_profile(
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=900,
    )


def _parsed(advice):
    return classify_response(
        {
            "id": "resp_market_recorded",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(advice)}],
                }
            ],
            "usage": {"input_tokens": 30, "output_tokens": 12, "total_tokens": 42},
        },
        _profile(),
    )


def test_recorded_market_advice_is_typed_and_cites_claim_level_retained_evidence():
    case = _case()
    parsed = _parsed(case["advice"])
    assert parsed.outcome == "SUCCEEDED"
    assert isinstance(parsed.output, MarketResearchAdvice)
    assert parsed.output.proposed_recommendation.value == "INCONCLUSIVE"
    assert parsed.output.findings[0].source_refs == (
        "evidence-price-a",
        "evidence-price-b",
    )
    assert parsed.output.findings[1].source_refs == ()
    validate_market_references(parsed.output, frozenset(case["retained_evidence"]))


@pytest.mark.parametrize(
    ("change", "expected_outcome"),
    [
        ({"proposed_recommendation": "ACCEPT_IDEA"}, "SCHEMA_MISMATCH"),
        ({"execute_verdict": "PROCEED_TO_OFFER"}, "SCHEMA_MISMATCH"),
        ({"send_email": True}, "SCHEMA_MISMATCH"),
    ],
)
def test_market_output_cannot_add_commands_or_unknown_recommendations(
    change, expected_outcome
):
    advice = {**_case()["advice"], **change}
    assert _parsed(advice).outcome == expected_outcome


@pytest.mark.parametrize(
    ("finding_change", "expected_outcome"),
    [
        ({"basis": "RETAINED_EVIDENCE", "source_refs": []}, "SCHEMA_MISMATCH"),
        ({"basis": "UNKNOWN", "source_refs": ["evidence-price-a"]}, "SCHEMA_MISMATCH"),
        ({"source_refs": ["evidence-price-a", "evidence-price-a"]}, "SCHEMA_MISMATCH"),
        ({"source_refs": [" evidence-price-a "]}, "SCHEMA_MISMATCH"),
        ({"source_refs": ["evidence-price-a"], "extra": "execute"}, "SCHEMA_MISMATCH"),
    ],
)
def test_market_finding_requires_honest_basis_and_unique_references(
    finding_change, expected_outcome
):
    advice = _case()["advice"]
    advice["findings"][0].update(finding_change)
    assert _parsed(advice).outcome == expected_outcome


def test_unknown_retained_reference_is_rejected_after_typed_parse():
    parsed = _parsed(_case()["advice"])
    assert isinstance(parsed.output, MarketResearchAdvice)
    with pytest.raises(PermissionError, match="retained evidence reference"):
        validate_market_references(parsed.output, frozenset())


def test_retained_reference_ids_are_exact_without_whitespace_normalization():
    finding = _case()["advice"]["findings"][0]
    finding["source_refs"] = [" evidence-price-a "]
    with pytest.raises(ValueError):
        MarketFinding.model_validate_json(json.dumps(finding))


@pytest.mark.parametrize(
    "input_json",
    [
        "{}",
        '{"retained_evidence":[{"ref":"evidence-price-a"}]}',
        '{"retained_evidence":[{"ref":"evidence-price-a"},{"ref":"evidence-price-a"}]}',
        '{"retained_evidence":[{"ref":null}]}',
    ],
)
def test_profile_validator_rejects_missing_or_incomplete_retained_ids(input_json):
    advice = MarketResearchAdvice.model_validate_json(json.dumps(_case()["advice"]))
    validator = _profile().output_validator
    assert validator is not None
    with pytest.raises(PermissionError, match="retained evidence"):
        validator(advice, input_json)


def test_profile_validator_accepts_exact_retained_input_ids():
    advice = MarketResearchAdvice.model_validate_json(json.dumps(_case()["advice"]))
    validator = _profile().output_validator
    assert validator is not None
    validator(
        advice,
        json.dumps(
            {
                "retained_evidence": [
                    {"ref": "evidence-price-a"},
                    {"ref": "evidence-price-b"},
                ]
            }
        ),
    )


def test_profile_validator_allows_explicit_unknowns_without_retained_evidence():
    case = _case()
    case["advice"]["findings"] = [case["advice"]["findings"][1]]
    advice = MarketResearchAdvice.model_validate_json(json.dumps(case["advice"]))
    validator = _profile().output_validator
    assert validator is not None
    validator(advice, '{"retained_evidence":[]}')
