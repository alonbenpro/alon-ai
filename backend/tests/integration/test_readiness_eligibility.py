"""Readiness uses the latest decision without changing historical supply facts."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from test_product_records import NOW
from test_qualification_cohorts import (
    KEY,
    decision_request,
    dossier_request,
    qualified_pool,
)

from alon_ai.records import ProductRecordsDenied
from alon_ai.records import qualification_schema as q
from alon_ai.records.qualifications import QualificationCohortRepository
from alon_ai.supply import schema as supply

pytestmark = pytest.mark.integration


async def test_new_decision_supersedes_readiness_without_rewriting_history(
    governance_engine,
):
    exp, acceptance, criteria, plan, supply_repo, _, leads = await qualified_pool(
        governance_engine, size=50
    )
    repo = QualificationCohortRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    first = await repo.record_dossier(
        dossier_request(acceptance, leads[0]), command_key=uuid4()
    )
    accepted = await repo.decide(
        await decision_request(
            leads[0], first, criteria, policy_ref=plan.qualification_rule_id
        ),
        command_key=uuid4(),
    )
    assert (await supply_repo.snapshot(exp)).current_qualified_contactable == 1
    second = await repo.record_dossier(
        dossier_request(acceptance, leads[0], 1), command_key=uuid4()
    )
    hard = next(item.code for item in criteria if item.rule_kind == "HARD_GATE")
    request = await decision_request(
        leads[0],
        second,
        criteria,
        policy_ref=plan.qualification_rule_id,
        outcome="REJECTED_NOT_A_FIT",
        hard_failure=hard,
    )
    key = uuid4()
    rejected = await repo.decide(request, command_key=key)
    assert await repo.decide(request, command_key=key) == rejected
    assert (await supply_repo.snapshot(exp)).current_qualified_contactable == 0
    async with governance_engine.begin() as connection:
        await repo._context(connection)
        assert (
            await connection.scalar(select(func.count()).select_from(q.decisions)) == 2
        )
        assert (
            await connection.scalar(select(supply.qualifications.c.outcome))
            == "QUALIFIED"
        )
        historical = (
            (
                await connection.execute(
                    select(q.decisions).where(q.decisions.c.id == accepted.id)
                )
            )
            .mappings()
            .one()
        )
        with pytest.raises(ProductRecordsDenied, match="STALE_DECISION"):
            await repo._current_decision(connection, historical, NOW)
    third = await repo.record_dossier(
        dossier_request(acceptance, leads[0], 2), command_key=uuid4()
    )
    restored = await repo.decide(
        await decision_request(
            leads[0], third, criteria, policy_ref=plan.qualification_rule_id
        ),
        command_key=uuid4(),
    )
    assert restored.id != accepted.id
    assert (await supply_repo.snapshot(exp)).current_qualified_contactable == 1
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(select(func.count()).select_from(q.decisions)) == 3
        )
        assert (
            await connection.scalar(
                select(func.count()).select_from(supply.qualifications)
            )
            == 1
        )

    # The old schema cannot represent appended decisions. Refuse a destructive
    # rollback before changing anything instead of discarding immutable history.
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "downgrade", "0d1db464e1c2"],
        cwd=Path(__file__).resolve().parents[2],
        env=dict(
            os.environ,
            ALON_AI_DATABASE_URL=governance_engine.url.render_as_string(
                hide_password=False
            ),
            ALON_AI_ENVIRONMENT="test",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert (
        "historical calibration and requalification cannot be represented"
        in result.stderr
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "20260920_10"
        )
        assert (
            await connection.scalar(select(func.count()).select_from(q.decisions)) == 3
        )
