"""Controlled waits and crashes exercise the actual PostgreSQL dispatch boundary."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_governance import add_event, register
from test_openai_runtime import recorded, setup

from alon_ai.accounting.models import ControlPolicy
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.openai_runtime.contract import PremiumAuthorization, RoutingFacts
from alon_ai.openai_runtime.runtime import AcceptedSource
from alon_ai.openai_runtime.schema import premium_approvals, route_decisions
from alon_ai.openai_runtime.store import OpenAIRunConflict
from alon_ai.providers.rights import GrantEvent, GrantEventKind, RuntimeContent

pytestmark = pytest.mark.integration


async def while_reserved(runtime, attr, source, facts, change):
    entered, release = asyncio.Event(), asyncio.Event()
    reserve = runtime.repository.reserve

    async def paused(*args, **kwargs):
        receipt = await reserve(*args, **kwargs)
        entered.set()
        await release.wait()
        return receipt

    runtime.repository.reserve = paused
    task = asyncio.create_task(
        runtime.run(attr, facts=facts, sources=(source,), idempotency_key=uuid4())
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        await change()
    finally:
        release.set()
    return await task


async def test_premium_expiry_during_reservation_prevents_transport(governance_engine):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    clock = [now]
    runtime.repository.clock = lambda: clock[0]
    authorization = PremiumAuthorization(
        uuid4(), attr.experiment_id, now + timedelta(seconds=1), uuid4(), now
    )
    runtime.routes = replace(
        runtime.routes, premium=runtime.routes.cheap, approved_premium=(authorization,)
    )
    await runtime.authority.approve(authorization, runtime.routes.premium)

    async def expire():
        clock[0] = now + timedelta(seconds=2)

    result = await while_reserved(
        runtime,
        attr,
        source,
        RoutingFacts(
            needs_ai=True, premium_requested=True, premium_authorization=authorization
        ),
        expire,
    )
    assert transport.calls == []
    assert result.output is None


async def test_premium_revocation_during_reservation_prevents_transport(
    governance_engine,
):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    authorization = PremiumAuthorization(
        uuid4(), attr.experiment_id, now + timedelta(minutes=5), uuid4(), now
    )
    runtime.routes = replace(
        runtime.routes, premium=runtime.routes.cheap, approved_premium=(authorization,)
    )
    await runtime.authority.approve(authorization, runtime.routes.premium)

    async def revoke():
        await runtime.authority.revoke(authorization.authorization_id, now)

    result = await while_reserved(
        runtime,
        attr,
        source,
        RoutingFacts(
            needs_ai=True, premium_requested=True, premium_authorization=authorization
        ),
        revoke,
    )
    assert len(transport.calls) == 0
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0


async def test_retention_expiry_during_reservation_prevents_transport(
    governance_engine,
):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    clock = [now]
    runtime.repository.clock = lambda: clock[0]
    profile = runtime.profiles[runtime.routes.cheap]
    config, _ = await runtime.repository.generation_config_and_prices(profile.config_id)
    source = replace(
        source,
        content=RuntimeContent(
            {
                field: ("licensed evidence",)
                for field in config.intended_use.required_fields
            },
            grant=source.current_grant,
            intended_use=config.intended_use,
            observed_at=now - timedelta(seconds=59),
        ),
    )

    async def expire():
        clock[0] = now + timedelta(seconds=2)

    result = await while_reserved(
        runtime, attr, source, RoutingFacts(needs_ai=True), expire
    )
    assert transport.calls == []
    assert result.output is None


async def test_source_revocation_during_reservation_prevents_transport(
    governance_engine,
):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    admin = GovernanceProvisioner(governance_engine)
    grant = source.current_grant.model_copy(
        update={
            "grant_id": uuid4(),
            "account_handle": "source-only",
            "supporting_evidence_ref": uuid4(),
        }
    )
    policy = ControlPolicy(
        id=uuid4(),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        evidence_id=uuid4(),
        capability=grant.capability,
        account_handle=grant.account_handle,
        timeout_seconds=1,
        quota_limit=10,
        window_seconds=60,
        concurrency_limit=2,
        failure_threshold=2,
        failure_window_seconds=60,
        cooldown_seconds=10,
    )
    await register(admin, policy.evidence_id, "CONTROL", now)
    await admin.policy(policy)
    await register(admin, grant.supporting_evidence_ref, "GRANT", now)
    await admin.grant(grant)
    config, _ = await runtime.repository.generation_config_and_prices(
        runtime.routes.cheap
    )
    use = config.intended_use.model_copy(update={"account_handle": "source-only"})
    source = AcceptedSource(
        uuid4(),
        RuntimeContent(
            {field: ("licensed evidence",) for field in use.required_fields},
            grant=grant,
            intended_use=use,
            observed_at=now,
        ),
        grant,
    )

    async def revoke():
        await add_event(
            admin,
            GrantEvent(
                event_id=uuid4(),
                grant_id=grant.grant_id,
                grant_version=grant.version,
                kind=GrantEventKind.REVOKED,
                effective_at=now,
                actor_id=uuid4(),
                evidence_ref=uuid4(),
            ),
        )

    result = await while_reserved(
        runtime, attr, source, RoutingFacts(needs_ai=True), revoke
    )
    assert transport.calls == []
    assert result.output is None


@pytest.mark.parametrize("first_paid", [False, True])
async def test_no_ai_and_paid_decisions_cannot_reuse_each_others_key(
    governance_engine, first_paid
):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    key = uuid4()
    await runtime.run(
        attr,
        facts=RoutingFacts(needs_ai=first_paid),
        sources=(source,),
        idempotency_key=key,
    )
    with pytest.raises(OpenAIRunConflict):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=not first_paid),
            sources=(source,),
            idempotency_key=key,
        )
    assert len(transport.calls) == int(first_paid)


class SimulatedCrash(BaseException):
    pass


async def test_replay_after_ledger_finalization_closes_run_without_transport(
    governance_engine,
):
    runtime, store, attr, source, transport = await setup(governance_engine, recorded())
    key = uuid4()
    finish = store.finish

    async def crash(*args, **kwargs):
        raise SimulatedCrash()

    store.finish = crash
    with pytest.raises(SimulatedCrash):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    store.finish = finish
    replay = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert replay.outcome == "RESULT_UNAVAILABLE"
    assert replay.output is None
    run = await store.get(key)
    assert run is not None and run.outcome == "RESULT_UNAVAILABLE"
    assert len(transport.calls) == 1


@pytest.mark.parametrize("response", [recorded(usage=False), recorded(cached=False)])
async def test_unresolved_usage_never_records_usable_success(
    governance_engine, response
):
    runtime, store, attr, source, transport = await setup(governance_engine, response)
    key = uuid4()
    result = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert result.outcome == "RESULT_UNAVAILABLE"
    assert result.output is None
    run = await store.get(key)
    assert run is not None and run.outcome == "RESULT_UNAVAILABLE"
    replay = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert replay.outcome == "RESULT_UNAVAILABLE"
    assert len(transport.calls) == 1


async def test_premium_call_retains_immutable_approval_identity(governance_engine):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    authorization = PremiumAuthorization(
        uuid4(), attr.experiment_id, now + timedelta(minutes=5), uuid4(), now
    )
    runtime.routes = replace(
        runtime.routes, premium=runtime.routes.cheap, approved_premium=(authorization,)
    )
    await runtime.authority.approve(authorization, runtime.routes.premium)
    key = uuid4()
    result = await runtime.run(
        attr,
        sources=(source,),
        idempotency_key=key,
        facts=RoutingFacts(
            needs_ai=True,
            premium_requested=True,
            premium_authorization=authorization,
        ),
    )
    assert result.outcome == "SUCCEEDED" and len(transport.calls) == 1
    async with governance_engine.connect() as conn:
        audit = (
            (
                await conn.execute(
                    select(
                        route_decisions.c.approval_id,
                        premium_approvals.c.approved_by,
                        premium_approvals.c.scope,
                        premium_approvals.c.config_id,
                    )
                    .join(
                        premium_approvals,
                        route_decisions.c.approval_id
                        == premium_approvals.c.authorization_id,
                    )
                    .where(route_decisions.c.idempotency_key == key)
                )
            )
            .mappings()
            .one()
        )
    assert audit["approval_id"] == authorization.authorization_id
    assert audit["approved_by"] == authorization.approved_by
    assert audit["scope"] == attr.experiment_id
    assert audit["config_id"] == runtime.routes.premium


async def test_dispatch_crash_is_durably_recovering_without_retry(governance_engine):
    runtime, store, attr, source, transport = await setup(
        governance_engine, SimulatedCrash()
    )
    key = uuid4()
    with pytest.raises(SimulatedCrash):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    for _ in range(2):
        replay = await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
        assert replay.outcome == "RECOVERING" and replay.output is None
    run = await store.get(key)
    assert run is not None and run.outcome == "RECOVERING" and run.call_id is not None
    assert len(transport.calls) == 1


async def test_completed_response_crash_before_reconciliation_loses_output_safely(
    governance_engine,
):
    runtime, store, attr, source, transport = await setup(governance_engine, recorded())
    key = uuid4()

    async def crash(*args, **kwargs):
        raise SimulatedCrash()

    runtime.repository.reconcile = crash
    with pytest.raises(SimulatedCrash):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    replay = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert replay.outcome == "RESULT_UNAVAILABLE" and replay.output is None
    run = await store.get(key)
    assert run is not None and run.outcome == "RESULT_UNAVAILABLE"
    assert len(transport.calls) == 1


async def test_concurrent_recovery_after_ledger_finalization_does_not_break_owner(
    governance_engine,
):
    runtime, store, attr, source, transport = await setup(governance_engine, recorded())
    key = uuid4()
    entered, release = asyncio.Event(), asyncio.Event()
    finish = store.finish

    async def paused(*args, **kwargs):
        entered.set()
        await release.wait()
        return await finish(*args, **kwargs)

    store.finish = paused
    owner = asyncio.create_task(
        runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    )
    await asyncio.wait_for(entered.wait(), 5)
    try:
        replay = await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
        assert replay.outcome == "RESULT_UNAVAILABLE"
    finally:
        release.set()
    result = await owner
    assert result.outcome == "RESULT_UNAVAILABLE" and result.output is None
    assert len(transport.calls) == 1


async def test_expired_premium_approval_cannot_block_read_only_crash_recovery(
    governance_engine,
):
    runtime, store, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    clock = [now]
    runtime.repository.clock = lambda: clock[0]
    authorization = PremiumAuthorization(
        uuid4(), attr.experiment_id, now + timedelta(seconds=1), uuid4(), now
    )
    runtime.routes = replace(
        runtime.routes, premium=runtime.routes.cheap, approved_premium=(authorization,)
    )
    await runtime.authority.approve(authorization, runtime.routes.premium)
    facts = RoutingFacts(
        needs_ai=True, premium_requested=True, premium_authorization=authorization
    )
    key = uuid4()
    finish = store.finish

    async def crash(*args, **kwargs):
        raise SimulatedCrash()

    store.finish = crash
    with pytest.raises(SimulatedCrash):
        await runtime.run(attr, facts=facts, sources=(source,), idempotency_key=key)
    store.finish = finish
    clock[0] = now + timedelta(minutes=2)
    replay = await runtime.run(
        attr, facts=facts, sources=(source,), idempotency_key=key
    )
    assert replay.outcome == "RESULT_UNAVAILABLE" and len(transport.calls) == 1


@pytest.mark.parametrize("expired", ["premium", "retention"])
async def test_expiry_after_authority_lock_wait_is_checked_before_transport(
    governance_engine, expired
):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    now = runtime.repository.clock()
    clock = [now]
    runtime.repository.clock = lambda: clock[0]
    facts = RoutingFacts(needs_ai=True)
    if expired == "premium":
        authorization = PremiumAuthorization(
            uuid4(), attr.experiment_id, now + timedelta(seconds=1), uuid4(), now
        )
        runtime.routes = replace(
            runtime.routes,
            premium=runtime.routes.cheap,
            approved_premium=(authorization,),
        )
        await runtime.authority.approve(authorization, runtime.routes.premium)
        facts = RoutingFacts(
            needs_ai=True, premium_requested=True, premium_authorization=authorization
        )
    else:
        config, _ = await runtime.repository.generation_config_and_prices(
            runtime.routes.cheap
        )
        source = replace(
            source,
            content=RuntimeContent(
                {
                    field: ("licensed evidence",)
                    for field in config.intended_use.required_fields
                },
                grant=source.current_grant,
                intended_use=config.intended_use,
                observed_at=now - timedelta(seconds=59),
            ),
        )
    entered, release = asyncio.Event(), asyncio.Event()
    guard = runtime.authority.dispatch_guard

    @asynccontextmanager
    async def paused_guard(*args, **kwargs):
        async with guard(*args, **kwargs) as snapshot:
            entered.set()
            await release.wait()
            yield snapshot

    runtime.authority.dispatch_guard = paused_guard
    task = asyncio.create_task(
        runtime.run(attr, facts=facts, sources=(source,), idempotency_key=uuid4())
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        clock[0] = now + timedelta(seconds=2)
    finally:
        release.set()
    result = await task
    assert result.output is None and transport.calls == []
