"""Native price observations retain precise facts and never invent an offer."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from alon_ai.agents.schemas.idea import PriceKind, PriceObservation
from alon_ai.services.combined_idea import price_finding_requests
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    SourceReference,
)


def subject():
    return ArtifactInput(
        artifact_id=uuid4(),
        kind=ArtifactKind.IDEA_SEED,
        version=2,
        content_hash="a" * 64,
        role="RESEARCH_SUBJECT",
    )


def source():
    return SourceReference.retained_content(
        retained_id=uuid4(),
        call_id=uuid4(),
        grant_id=uuid4(),
        grant_version=1,
        field="TEXT",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


@pytest.mark.parametrize(
    "kind,low,high",
    [
        ("EXACT", "29.99", None),
        ("RANGE", "20", "50"),
        ("STARTING_AT", "10", None),
        ("QUOTE_ONLY", None, None),
    ],
)
def test_observed_price_fields_and_exact_evidence_survive(kind, low, high):
    run, version, ref = uuid4(), subject(), source()
    price = PriceObservation.model_validate(
        {
            "subject": "Published competitor plan",
            "kind": kind,
            "currency": "USD",
            "amount_low": low,
            "amount_high": high,
            "unit": "month",
            "package": "Starter",
            "observed_date": "2026-09-28",
            "source_refs": [str(ref.retained_id)],
        }
    )
    (result,) = price_finding_requests(run, version, 0, price, (ref,))
    assert result == price_finding_requests(run, version, 0, price, (ref,))[0]
    assert result.dimension == "PRICING" and result.subject == version
    assert result.sources == (ref,) and result.evidence_status == "SUPPORTED"
    assert result.claim == price.subject
    assert json.loads(result.finding) == price.model_dump(
        mode="json", exclude={"source_refs", "subject"}
    )
    assert "not our offer price" in result.limitations[1]


def test_not_found_is_inconclusive_with_no_source_or_numeric_invention():
    price = PriceObservation(subject="Unlisted plan", kind=PriceKind.NOT_FOUND)
    (result,) = price_finding_requests(uuid4(), subject(), 0, price, (source(),))
    assert result.evidence_status == "INCONCLUSIVE" and result.sources == ()
    assert json.loads(result.finding)["amount_low"] is None
    assert "does not establish" in result.limitations[1]


def test_long_metadata_splits_without_truncating_fields_or_colliding_step_ids():
    ref, version, run = source(), subject(), uuid4()
    price = PriceObservation.model_validate(
        {
            "subject": "Plan",
            "kind": "EXACT",
            "currency": "USD",
            "amount_low": "9",
            "unit": "u" * 4000,
            "package": "p" * 4000,
            "source_refs": [str(ref.retained_id)],
        }
    )
    results = price_finding_requests(run, version, 0, price, (ref,))
    assert len(results) == 3
    assert len({item.step_key for item in results}) == 3
    assert results[1].finding == price.unit and results[2].finding == price.package
    assert all(item.sources == (ref,) for item in results)
