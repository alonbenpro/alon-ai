"""Durable, content-free authority facts used at the Responses dispatch fence."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from test_governance import add_event, reserve, seed

from alon_ai.openai_runtime.authority import (
    OpenAIAuthorityStore,
    OpenAIRunConflict,
)
from alon_ai.openai_runtime.contract import PremiumAuthorization, Route
from alon_ai.openai_runtime.schema import run_intents
from alon_ai.openai_runtime.store import (
    OpenAIRunIntent,
    OpenAIRunOutcome,
    OpenAIRunStore,
)
from alon_ai.providers.contracts import Capability, UsageComponent
from alon_ai.providers.rights import GrantEvent, GrantEventKind

pytestmark = pytest.mark.integration


def _authorization(scope, now):
    return PremiumAuthorization(
        authorization_id=uuid4(),
        scope=scope,
        approved_by=uuid4(),
        approved_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(minutes=5),
    )


def _intent(attr, config, now):
    return OpenAIRunIntent(
        idempotency_key=uuid4(),
        config_id=config.id,
        config_version=config.version,
        experiment_id=attr.experiment_id,
        workflow_id=attr.workflow_run_id,
        operation_id=attr.operation_run_id,
        agent_run_id=None,
        prompt_version="authority-v1",
        prompt_hash="b" * 64,
        schema_version="authority-v1",
        output_schema_hash="d" * 64,
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        accepted_input_refs=(uuid4(),),
        input_hash="a" * 64,
        client_request_id=uuid4(),
        created_at=now,
    )


async def test_premium_decision_is_immutable_and_audits_approved_identity(
    governance_engine,
):
    _, _, attr, config, grant, now = await seed(
        governance_engine,
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
        ),
    )
    authority = OpenAIAuthorityStore(governance_engine)
    approval = _authorization(attr.experiment_id, now)
    await authority.approve(approval, config.id)
    key = uuid4()

    await authority.bind_decision(
        key,
        attr,
        "a" * 64,
        Route.PREMIUM,
        config.id,
        approval.authorization_id,
    )
    await authority.bind_decision(
        key,
        attr,
        "a" * 64,
        Route.PREMIUM,
        config.id,
        approval.authorization_id,
    )
    with pytest.raises(OpenAIRunConflict):
        await authority.bind_decision(
            key,
            attr,
            "b" * 64,
            Route.PREMIUM,
            config.id,
            approval.authorization_id,
        )

    snapshot = await authority.snapshot(
        ((grant.grant_id, grant.version),), approval.authorization_id
    )
    assert snapshot.approval == approval
    assert snapshot.approval_config_id == config.id
    assert snapshot.revoked_at is None
    assert snapshot.grants[(grant.grant_id, grant.version)] == grant


async def test_snapshot_observes_grant_events_and_monotone_approval_revocation(
    governance_engine,
):
    _, admin, attr, config, grant, now = await seed(
        governance_engine,
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
        ),
    )
    authority = OpenAIAuthorityStore(governance_engine)
    approval = _authorization(attr.experiment_id, now)
    await authority.approve(approval, config.id)
    revoked_at = now + timedelta(seconds=1)
    await authority.revoke(approval.authorization_id, revoked_at)
    await authority.revoke(approval.authorization_id, revoked_at)
    with pytest.raises(OpenAIRunConflict):
        await authority.revoke(approval.authorization_id, revoked_at + timedelta(1))

    event = GrantEvent(
        event_id=uuid4(),
        grant_id=grant.grant_id,
        grant_version=grant.version,
        kind=GrantEventKind.REVOKED,
        effective_at=now,
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    await add_event(admin, event)
    snapshot = await authority.snapshot(
        ((grant.grant_id, grant.version),), approval.authorization_id
    )
    assert snapshot.events == (event,)
    assert snapshot.revoked_at == revoked_at


async def test_dispatch_guard_holds_approval_revocation_until_transport_exits(
    governance_engine,
):
    _, _, attr, config, grant, now = await seed(
        governance_engine,
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
        ),
    )
    authority = OpenAIAuthorityStore(governance_engine)
    approval = _authorization(attr.experiment_id, now)
    await authority.approve(approval, config.id)
    revoke_task = None
    async with authority.dispatch_guard(
        ((grant.grant_id, grant.version),), approval.authorization_id
    ) as snapshot:
        assert snapshot.revoked_at is None
        revoke_task = asyncio.create_task(
            authority.revoke(approval.authorization_id, now + timedelta(seconds=1))
        )
        await asyncio.sleep(0.1)
        assert not revoke_task.done()
    assert revoke_task is not None
    await asyncio.wait_for(revoke_task, timeout=2)
    observed = await authority.snapshot(
        ((grant.grant_id, grant.version),), approval.authorization_id
    )
    assert observed.revoked_at == now + timedelta(seconds=1)


async def test_no_ai_cannot_overwrite_a_durable_paid_intent(governance_engine):
    repo, _, attr, config, _, now = await seed(
        governance_engine,
        limit=Decimal(100),
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
        ),
    )
    intent = _intent(attr, config, now)
    await OpenAIRunStore(governance_engine).begin(intent)

    with pytest.raises(OpenAIRunConflict):
        await OpenAIAuthorityStore(governance_engine).bind_decision(
            intent.idempotency_key,
            attr,
            "a" * 64,
            Route.NO_AI,
            None,
            None,
        )

    paid_only_key = uuid4()
    await reserve(repo, attr, config, key=paid_only_key)
    with pytest.raises(OpenAIRunConflict):
        await OpenAIAuthorityStore(governance_engine).bind_decision(
            paid_only_key,
            attr,
            "a" * 64,
            Route.NO_AI,
            None,
            None,
        )


async def test_paid_decision_cannot_adopt_a_legacy_intent_with_changed_config(
    governance_engine,
):
    _, admin, attr, config, _, now = await seed(
        governance_engine,
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
        ),
    )
    intent = _intent(attr, config, now)
    await OpenAIRunStore(governance_engine).begin(intent)
    other_config = config.model_copy(update={"id": uuid4()})
    await admin.config(other_config)

    with pytest.raises(OpenAIRunConflict):
        await OpenAIAuthorityStore(governance_engine).bind_decision(
            intent.idempotency_key,
            attr,
            "a" * 64,
            Route.CHEAP,
            other_config.id,
            None,
        )
    async with governance_engine.connect() as connection:
        count = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM openai_route_decisions WHERE idempotency_key=:key"
                ),
                {"key": intent.idempotency_key},
            )
        ).scalar_one()
    assert count == 0


async def test_authority_tables_store_no_content_or_secrets(governance_engine):
    async with governance_engine.connect() as connection:
        columns = await connection.execute(
            text(
                """SELECT table_name, column_name FROM information_schema.columns
                   WHERE table_name IN ('openai_route_decisions', 'openai_premium_approvals')"""
            )
        )
    names = {row.column_name for row in columns}
    assert not names.intersection(
        {"content", "input", "output", "prompt", "secret", "request", "response"}
    )


async def test_run_intent_cannot_be_inserted_as_a_terminal_result(governance_engine):
    _, _, attr, config, _, now = await seed(
        governance_engine,
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
        ),
    )
    intent = _intent(attr, config, now)
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(run_intents).values(
                    **intent.model_dump(mode="python"),
                    outcome="NO_AI",
                    finished_at=now,
                )
            )


async def test_migration_marks_legacy_nonfinal_success_result_unavailable(
    governance_engine,
):
    database_url = governance_engine.url.render_as_string(hide_password=False)
    await governance_engine.dispose()
    environment = {
        **os.environ,
        "ALON_AI_DATABASE_URL": database_url,
        "ALON_AI_ENVIRONMENT": "test",
    }
    backend = Path(__file__).resolve().parents[2]
    down = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "downgrade", "20260924_22"],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert down.returncode == 0, down.stderr
    legacy_engine = create_async_engine(database_url, hide_parameters=True)
    try:
        repo, _, attr, config, _, now = await seed(
            legacy_engine,
            limit=Decimal(100),
            capability=Capability.OPENAI_GENERATE,
            price_components=(
                UsageComponent.REQUEST,
                UsageComponent.INPUT_TOKEN,
                UsageComponent.OUTPUT_TOKEN,
            ),
        )
        intent = _intent(attr, config, now)
        await OpenAIRunStore(legacy_engine).begin(intent)
        receipt = await reserve(repo, attr, config, key=intent.idempotency_key)
        async with legacy_engine.begin() as connection:
            await connection.execute(
                text(
                    """UPDATE openai_run_intents
                    SET call_id=:call_id, outcome='SUCCEEDED', output_hash=:output_hash,
                        finished_at=:finished_at WHERE idempotency_key=:key"""
                ),
                {
                    "call_id": receipt.call_id,
                    "output_hash": "c" * 64,
                    "finished_at": now,
                    "key": intent.idempotency_key,
                },
            )
    finally:
        await legacy_engine.dispose()
    up = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert up.returncode == 0, up.stderr
    migrated_engine = create_async_engine(database_url, hide_parameters=True)
    try:
        migrated = await OpenAIRunStore(migrated_engine).get(intent.idempotency_key)
        assert migrated is not None
        assert migrated.outcome is OpenAIRunOutcome.RESULT_UNAVAILABLE
        assert migrated.output_hash == "c" * 64
    finally:
        await migrated_engine.dispose()
