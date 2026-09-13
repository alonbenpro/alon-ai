"""Explicit operator ownership and real delivery/commercial profile versions."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError

from alon_ai.accounting import schema as gov
from alon_ai.records import schema as records
from alon_ai.records.models import ProductRecordsDenied
from alon_ai.records.operator_models import (
    CommercialConstraints,
    DeliveryConstraints,
    OperatorIdentity,
    OperatorProfileVersion,
)
from alon_ai.records.operators import OperatorRepository, operators

NOW = datetime(2026, 9, 13, 0, tzinfo=UTC)


def profile(owner, *, id_=None, version=1):
    return OperatorProfileVersion(
        id=id_ or uuid4(),
        version=version,
        operator_id=owner,
        capabilities=("Python development", "Business process automation"),
        constraints=("No revenue guarantees",),
        delivery=DeliveryConstraints(
            max_project_hours=Decimal(100),
            hours_per_week=Decimal(25),
            concurrent_projects=2,
        ),
        commercial=CommercialConstraints(
            currency="ILS",
            hourly_cost=Decimal(150),
            minimum_project_price=Decimal(2500),
            minimum_margin_rate=Decimal("0.30"),
            maximum_discount_rate=Decimal("0.10"),
            minimum_deposit_rate=Decimal("0.25"),
        ),
        approved_by=owner,
        created_at=NOW,
    )


async def owner_and_profile(engine):
    repo = OperatorRepository(engine, clock=lambda: NOW)
    owner = uuid4()
    identity = OperatorIdentity(
        id=owner, auth_subject=f"synthetic:{owner}", display_name="Synthetic operator"
    )
    await repo.register_operator(identity, command_key=uuid4())
    p = profile(owner)
    await repo.register_profile(p, command_key=uuid4())
    return repo, identity, p


async def test_profile_authority_comes_from_active_owner_not_skill_labels(
    governance_engine,
):
    repo, identity, p = await owner_and_profile(governance_engine)
    experiment = uuid4()
    async with governance_engine.begin() as c:
        await c.execute(insert(gov.experiments).values(id=experiment))
        await c.execute(
            insert(records.experiments).values(
                id=experiment,
                operator_profile_id=p.id,
                operator_profile_version=p.version,
                name="Synthetic experiment",
                created_at=NOW,
            )
        )
        assert (
            await c.scalar(
                text("SELECT record_operator_authorized(:e,:a)"),
                {"e": experiment, "a": identity.id},
            )
            is True
        )
        assert (
            await c.scalar(
                text("SELECT record_operator_authorized(:e,:a)"),
                {"e": experiment, "a": uuid4()},
            )
            is False
        )
    await repo.set_operator_status(
        identity.id, active=False, acted_by=identity.id, command_key=uuid4()
    )
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(
                text("SELECT record_operator_authorized(:e,:a)"),
                {"e": experiment, "a": identity.id},
            )
            is False
        )
    with pytest.raises(ProductRecordsDenied):
        await repo.register_profile(
            profile(identity.id, id_=p.id, version=2), command_key=uuid4()
        )


async def test_profile_versions_are_owned_immutable_and_replay_exact(governance_engine):
    repo, identity, p = await owner_and_profile(governance_engine)
    key = uuid4()
    second = profile(identity.id, id_=p.id, version=2)
    first = await repo.register_profile(second, command_key=key)
    assert await repo.register_profile(second, command_key=key) == first
    changed = second.model_copy(update={"capabilities": ("Different skill",)})
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.register_profile(changed, command_key=key)
    with pytest.raises(ProductRecordsDenied):
        await repo.register_profile(
            profile(identity.id, id_=p.id, version=4), command_key=uuid4()
        )
    async with governance_engine.connect() as c:
        row = (
            (
                await c.execute(
                    select(records.operator_profiles).where(
                        records.operator_profiles.c.id == p.id,
                        records.operator_profiles.c.version == 2,
                    )
                )
            )
            .mappings()
            .one()
        )
        assert row["profile_schema_version"] == 2
        assert row["delivery"]["hours_per_week"] == "25"
        assert row["commercial"]["minimum_project_price"] == "2500"
        assert len(row["content_hash"]) == 64
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(
                update(records.operator_profiles)
                .where(records.operator_profiles.c.id == p.id)
                .values(capabilities=["RESEARCH_REVIEW"])
            )
    with pytest.raises(ProductRecordsDenied):
        await repo.set_operator_status(
            identity.id, active=False, acted_by=uuid4(), command_key=uuid4()
        )


async def test_raw_profile_cannot_forge_approval_or_null_commercial_limits(
    governance_engine,
):
    _, identity, p = await owner_and_profile(governance_engine)
    async with governance_engine.connect() as c:
        existing = dict(
            (
                await c.execute(
                    select(records.operator_profiles).where(
                        records.operator_profiles.c.id == p.id
                    )
                )
            )
            .mappings()
            .one()
        )
    for altered in (
        {"approved_by": uuid4()},
        {"commercial": None},
        {"commercial": {**existing["commercial"], "minimum_margin_rate": "NaN"}},
    ):
        with pytest.raises(DBAPIError):
            async with governance_engine.begin() as c:
                await c.execute(
                    insert(records.operator_profiles).values(
                        {**existing, "version": 2, **altered}
                    )
                )
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(
                select(operators.c.status).where(operators.c.id == identity.id)
            )
            == "ACTIVE"
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("hourly_cost", Decimal("NaN")),
        ("minimum_margin_rate", Decimal("1.01")),
        ("maximum_discount_rate", Decimal(-1)),
    ],
)
def test_nonfinite_and_out_of_range_commercial_bounds_are_rejected(field, value):
    p = profile(uuid4())
    with pytest.raises(ValidationError):
        CommercialConstraints.model_validate(
            {**p.commercial.model_dump(), field: value}
        )
