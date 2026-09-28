from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from alon_ai.integrations.live_research import ResearchRunPolicy


def policy() -> ResearchRunPolicy:
    now = datetime.now(UTC)
    return ResearchRunPolicy(
        approved_by=uuid4(),
        effective_at=now,
        expires_at=now + timedelta(hours=1),
        max_calls=4,
        max_pages=4,
        timeout_seconds=30,
        max_spend_usd=Decimal(1),
        max_results=10,
        max_pdf_bytes=1000000,
        max_pdf_pages=2,
        max_text_chars=10000,
        pdf_cpu_seconds=2,
        pdf_memory_bytes=256_000_000,
        pdf_wall_seconds=5,
    )


def test_no_implicit_research_limits():
    with pytest.raises(ValueError):
        ResearchRunPolicy.model_validate({})


def test_policy_rejects_unbounded_spend_and_invalid_time():
    data = policy().model_dump()
    for key, value in [
        ("max_spend_usd", Decimal("Infinity")),
        ("max_calls", 0),
        ("expires_at", data["effective_at"]),
    ]:
        with pytest.raises(ValueError):
            ResearchRunPolicy.model_validate({**data, key: value})
