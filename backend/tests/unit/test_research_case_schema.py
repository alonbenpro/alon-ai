"""Research findings must not masquerade as source quotations or complete coverage."""

from uuid import uuid4

import pytest

from alon_ai.services.schemas.records import ArtifactKind, validate_payload


def finding_payload(**updates):
    return {
        "research_schema": "SOURCE_FINDING_V1",
        "run_id": str(uuid4()),
        "step_key": str(uuid4()),
        "dimension": "CUSTOMER_PAIN",
        "claim": "A recurring administrative problem is plausible.",
        "finding": "The search did not establish buying intent.",
        "evidence_status": "INCONCLUSIVE",
        "limitations": ["No direct buyer interview"],
        **updates,
    }


def test_new_source_finding_shape_accepts_unknown_evidence_without_inventing_support():
    payload = finding_payload(evidence_status="UNAVAILABLE", limitations=[])
    assert validate_payload(ArtifactKind.RESEARCH_EVIDENCE, payload) == payload


@pytest.mark.parametrize(
    "updates",
    [
        {"raw_content": "page body"},
        {"excerpt": "copied provider content"},
        {"evidence_status": "PROVEN"},
        {"dimension": "ANYTHING"},
        {"run_id": "not-a-uuid"},
        {"claim": " "},
        {"limitations": [""]},
    ],
)
def test_finding_rejects_raw_content_and_untyped_claims(updates):
    with pytest.raises(ValueError):
        validate_payload(ArtifactKind.RESEARCH_EVIDENCE, finding_payload(**updates))


def test_versioned_report_preserves_explicit_unresolved_questions():
    payload = {
        "research_schema": "MARKET_RESEARCH_CASE_V1",
        "finding": "Demand remains unverified.",
        "limitations": [],
        "unresolved_questions": ["Who has purchased this service?"],
    }
    assert validate_payload(ArtifactKind.MARKET_RESEARCH_REPORT, payload) == payload


def test_legacy_research_shapes_stay_readable():
    assert validate_payload(
        ArtifactKind.RESEARCH_EVIDENCE, {"claim": "A", "finding": "B"}
    )
    assert validate_payload(
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {
            "finding": "A",
            "limitations": ["B"],
        },
    )


def test_supported_claim_requires_a_retained_source_reference():
    from alon_ai.services.schemas.records import ArtifactInput
    from alon_ai.services.schemas.research import AppendSourceFindingRequest

    with pytest.raises(ValueError):
        AppendSourceFindingRequest(
            run_id=uuid4(),
            step_key=uuid4(),
            subject=ArtifactInput(
                artifact_id=uuid4(),
                kind=ArtifactKind.IDEA_SEED,
                version=1,
                content_hash="a" * 64,
                role="SEED",
            ),
            dimension="DEMAND",
            claim="Buyers pay",
            finding="Confirmed",
            evidence_status="SUPPORTED",
            sources=(),
        )
