"""Shared cap changes preserve accounting and are explicitly audited."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select, text, update

from alon_ai.db.repositories.accounting import GovernanceProvisioner
from alon_ai.db.tables import accounting as s
from alon_ai.db.tables.records_operator import operators
from alon_ai.integrations.schemas.provider import (
    CallAttribution,
    OperationRunKind,
    Provider,
    SystemActor,
)
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    EvidenceRecord,
    FxVersion,
)

pytestmark = pytest.mark.integration


async def setup(engine, scope="GLOBAL"):
    now = datetime.now(UTC)
    admin = GovernanceProvisioner(engine)
    operator_id, evidence_id, fx_id, fx_proof = (uuid4() for _ in range(4))
    async with engine.begin() as conn:
        await conn.execute(
            insert(operators).values(
                id=operator_id,
                auth_subject=str(operator_id),
                display_name="Test operator",
                timezone="Asia/Jerusalem",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
    proofs: tuple[tuple[UUID, Literal["CONTROL", "FX"]], ...] = (
        (evidence_id, "CONTROL"),
        (fx_proof, "FX"),
    )
    for id_, kind in proofs:
        await admin.evidence(
            EvidenceRecord(
                id=id_,
                kind=kind,
                mode="SYNTHETIC",
                registered_by=operator_id,
                registered_at=now,
            )
        )
    await admin.fx(
        FxVersion(
            id=fx_id,
            evidence_id=fx_proof,
            currency="USD",
            rate=Decimal("3.08"),
            effective_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
        )
    )
    attr = CallAttribution(
        experiment_id=uuid4(),
        workflow_run_id=uuid4(),
        operation_run_id=uuid4(),
        actor=SystemActor(service="provider-executor"),
        operation_run_kind=OperationRunKind.RESEARCH,
        correlation_id=uuid4(),
        logical_operation_id=uuid4(),
        config_version=uuid4(),
        deadline=now + timedelta(hours=1),
    )
    await admin.scope(attr)
    for currency, limit in (("USD", ".20"), ("ILS", ".616")):
        await admin.budgets(
            attr,
            provider=Provider.OPENAI,
            currencies=(currency,),
            limit=Decimal(limit),
            effective_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=1),
        )
    async with engine.begin() as conn:
        await conn.execute(
            update(s.budget_accounts).values(
                accrued=Decimal(".05"),
                reserved=Decimal(".02"),
                frozen=True,
            )
        )
    before = await accounts(engine)
    pair = {row["currency"]: row for row in before.values() if row["scope"] == scope}
    command = {
        "command_id": uuid4(),
        "operator_id": operator_id,
        "evidence_id": evidence_id,
        "scope": scope,
        "provider": Provider.OPENAI if scope == "PROVIDER" else None,
        "usd_account_id": pair["USD"]["id"],
        "ils_account_id": pair["ILS"]["id"],
        "expected_usd_limit": Decimal(".20"),
        "expected_ils_limit": Decimal(".616"),
        "new_usd_limit": Decimal(2),
        "fx_id": fx_id,
    }
    return admin, command, before


async def accounts(engine):
    async with engine.connect() as conn:
        rows = (await conn.execute(select(s.budget_accounts))).mappings().all()
        return {row["id"]: dict(row) for row in rows}


async def audits(engine):
    async with engine.connect() as conn:
        return (await conn.execute(select(s.audit))).mappings().all()


@pytest.mark.parametrize("scope", ["GLOBAL", "PROVIDER"])
async def test_shared_adjustment_changes_only_selected_limits(governance_engine, scope):
    admin, command, before = await setup(governance_engine, scope)
    result = await admin.adjust_shared_budget(**command)
    after = await accounts(governance_engine)
    for id_, old in before.items():
        expected = dict(old)
        if id_ == command["usd_account_id"]:
            expected["limit"] = Decimal(2)
        if id_ == command["ils_account_id"]:
            expected["limit"] = Decimal("6.16")
        assert after[id_] == expected
    rows = await audits(governance_engine)
    assert len(rows) == 1
    assert rows[0]["id"] == command["command_id"]
    assert rows[0]["kind"] == "SHARED_BUDGET_ADJUSTED"
    assert json.loads(rows[0]["reason"]) == result
    assert result["before"]["USD"] == "0.20"
    assert result["after"] == {"USD": "2", "ILS": "6.16"}


async def test_replay_never_resets_later_adjustment(governance_engine):
    admin, command, _ = await setup(governance_engine)
    original, duplicate = await asyncio.gather(
        admin.adjust_shared_budget(**command), admin.adjust_shared_budget(**command)
    )
    assert duplicate == original
    assert len(await audits(governance_engine)) == 1
    await admin.adjust_shared_budget(
        **{
            **command,
            "command_id": uuid4(),
            "expected_usd_limit": Decimal(2),
            "expected_ils_limit": Decimal("6.16"),
            "new_usd_limit": Decimal(3),
        }
    )
    assert await admin.adjust_shared_budget(**command) == original
    assert (await accounts(governance_engine))[command["usd_account_id"]]["limit"] == 3
    assert len(await audits(governance_engine)) == 2
    with pytest.raises(AccountingDenied, match="CONFLICT"):
        await admin.adjust_shared_budget(**{**command, "new_usd_limit": Decimal(4)})


@pytest.mark.parametrize(
    "invalid",
    ["stale", "child", "currency", "evidence", "operator", "fx", "below_commitments"],
)
async def test_invalid_adjustment_changes_neither_currency(governance_engine, invalid):
    admin, command, before = await setup(governance_engine)
    if invalid == "stale":
        command["expected_ils_limit"] = Decimal(".60")
    elif invalid == "child":
        command["usd_account_id"] = next(
            id_
            for id_, row in before.items()
            if row["scope"] == "EXPERIMENT" and row["currency"] == "USD"
        )
    elif invalid == "currency":
        command["usd_account_id"], command["ils_account_id"] = (
            command["ils_account_id"],
            command["usd_account_id"],
        )
    elif invalid == "evidence":
        command["evidence_id"] = uuid4()
    elif invalid == "operator":
        async with governance_engine.begin() as conn:
            await conn.execute(
                update(operators)
                .where(operators.c.id == command["operator_id"])
                .values(status="DISABLED")
            )
    elif invalid == "fx":
        command["fx_id"] = uuid4()
    else:
        command["new_usd_limit"] = Decimal(".01")
    with pytest.raises(AccountingDenied):
        await admin.adjust_shared_budget(**command)
    assert await accounts(governance_engine) == before
    assert not await audits(governance_engine)


async def test_concurrent_adjustments_have_one_winner(governance_engine):
    admin, command, _ = await setup(governance_engine)
    first, second = await asyncio.gather(
        admin.adjust_shared_budget(**command),
        admin.adjust_shared_budget(
            **{**command, "command_id": uuid4(), "new_usd_limit": Decimal(3)}
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(result, AccountingDenied) for result in (first, second)) == 1
    assert len(await audits(governance_engine)) == 1


async def test_audit_failure_rolls_back_both_limit_changes(governance_engine):
    admin, command, before = await setup(governance_engine)
    async with governance_engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE FUNCTION test_reject_budget_audit() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test audit failure'; END $$
        """)
        )
        await conn.execute(
            text("""
            CREATE TRIGGER test_reject_budget_audit BEFORE INSERT ON gov_audit
            FOR EACH ROW EXECUTE FUNCTION test_reject_budget_audit()
        """)
        )
    with pytest.raises(AccountingDenied, match="STATE"):
        await admin.adjust_shared_budget(**command)
    assert await accounts(governance_engine) == before
    assert not await audits(governance_engine)
