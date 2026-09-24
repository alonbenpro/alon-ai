"""Money ingress must not silently round, accept floats, or drop tiny charges."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from alon_ai.accounting.models import FxVersion, PriceVersion, reserve_amount
from alon_ai.providers.contracts import Capability, UsageComponent


def price(**changes):
    now = datetime.now(UTC)
    return PriceVersion.model_validate(
        dict(
            {
                "id": uuid4(),
                "capability": Capability.OPENAI_GENERATE,
                "component": UsageComponent.INPUT_TOKEN,
                "model_identifier": "synthetic-model-v1",
                "currency": "USD",
                "unit_price": Decimal("0.000001"),
                "unit_quantity": Decimal(1),
                "currency_quantum": Decimal("0.01"),
                "effective_at": now,
                "expires_at": now + timedelta(days=1),
                "evidence_id": uuid4(),
            },
            **changes,
        )
    )


@pytest.mark.parametrize(
    "bad",
    [
        True,
        0.1,
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal(-1),
        Decimal("0.0000000000001"),
    ],
)
def test_price_rejects_inexact_or_nonfinite_money(bad):
    with pytest.raises(ValidationError):
        price(unit_price=bad)


def test_subcent_reservation_is_conservative_in_each_currency():
    assert reserve_amount(Decimal("0.000001"), Decimal("0.01")) == Decimal("0.01")
    assert reserve_amount(Decimal("1.001"), Decimal("0.01")) == Decimal("1.01")


def test_fx_requires_positive_exact_rate():
    p = price()
    with pytest.raises(ValidationError):
        FxVersion(
            id=uuid4(),
            currency="USD",
            rate=Decimal(0),
            effective_at=p.effective_at,
            expires_at=p.expires_at,
            evidence_id=uuid4(),
        )


def test_unknown_currency_and_wrong_minor_unit_policy_are_denied():
    with pytest.raises(ValidationError):
        price(currency="ZZZ")
    with pytest.raises(ValidationError):
        price(currency_quantum=Decimal(1))


def test_openai_price_must_pin_exact_model():
    with pytest.raises(ValidationError):
        price(model_identifier=None)
