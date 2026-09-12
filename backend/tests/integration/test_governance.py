"""Real PostgreSQL safety tests; all account/grant/price evidence is synthetic."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.exc import DBAPIError

from alon_ai.accounting.models import (
    AccountingDenied,
    CallState,
    CapabilityConfig,
    ControlPolicy,
    FxVersion,
    PriceBound,
    PriceVersion,
    Reason,
)
from alon_ai.providers.contracts import (
    CallAttribution,
    Capability,
    ContentField,
    CostKnowledge,
    OperationRunKind,
    Provider,
    Purpose,
    SafeRequestMetadata,
    SystemActor,
    UsageComponent,
    UsageObservation,
)
from alon_ai.providers.rights import (
    GrantEvent,
    GrantEventKind,
    IntendedUse,
    ProviderUsageGrant,
)

pytestmark = pytest.mark.integration


async def test_migration_installs_durable_governance(governance_engine):
    async with governance_engine.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert "gov_calls" in names
    assert "gov_usage" in names
    assert "gov_budget_accounts" in names


async def register(admin, id_, kind, now, call_id=None):
    from alon_ai.accounting.models import EvidenceRecord

    await admin.evidence(
        EvidenceRecord(
            id=id_,
            kind=kind,
            mode="SYNTHETIC",
            registered_by=UUID(int=1),
            registered_at=now,
            call_id=call_id,
        )
    )


async def proof(repo, call_id, kind="RECONCILIATION"):
    from alon_ai.accounting.repository import GovernanceProvisioner

    id_ = uuid4()
    await register(GovernanceProvisioner(repo.engine), id_, kind, repo.clock(), call_id)
    return id_


async def add_event(admin, event):
    await register(admin, event.evidence_ref, "GRANT_EVENT", event.effective_at)
    await admin.grant_event(event)


async def seed(
    engine,
    *,
    limit=Decimal(1),
    quantum=Decimal(".01"),
    price=Decimal(".001"),
    quota=10,
    concurrency=2,
    gate="NONE",
    capability=Capability.BRAVE_WEB_COVERAGE,
    transient=False,
):
    from alon_ai.accounting.repository import (
        GovernanceProvisioner,
        GovernanceRepository,
    )

    now = datetime(2026, 9, 12, 12, tzinfo=UTC)
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
    admin = GovernanceProvisioner(engine)
    await admin.scope(attr, gate_kind=gate)
    from alon_ai.providers.contracts import CAPABILITIES, Nature

    use = IntendedUse(
        provider=CAPABILITIES[capability].provider,
        account_handle="synthetic-account",
        capability=capability,
        plan_identifier="synthetic-plan",
        order_form_ref="synthetic-order",
        terms_version="synthetic-v1",
        purpose=Purpose.OFFICIAL_SOURCE_IDENTIFICATION
        if transient
        else Purpose.GATEWAY_EFFECT
        if CAPABILITIES[capability].nature == Nature.WRITE
        else Purpose.RESEARCH,
        required_fields=frozenset() if transient else frozenset({ContentField.TEXT}),
    )
    policy = ControlPolicy(
        id=uuid4(),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        evidence_id=uuid4(),
        capability=use.capability,
        account_handle=use.account_handle,
        timeout_seconds=1,
        quota_limit=quota,
        window_seconds=60,
        concurrency_limit=concurrency,
        failure_threshold=2,
        failure_window_seconds=60,
        cooldown_seconds=10,
    )
    await register(admin, policy.evidence_id, "CONTROL", now)
    await admin.policy(policy)
    grant = ProviderUsageGrant(
        grant_id=uuid4(),
        version=1,
        **use.model_dump(exclude={"schema_version", "required_fields"}),
        outbound_use_permitted=True,
        storage_fields=use.required_fields,
        retention_rule_id=None if transient else uuid4(),
        retention_seconds=None if transient else 60,
        approved_by=uuid4(),
        approved_at=now - timedelta(days=2),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        supporting_evidence_ref=uuid4(),
    )
    await register(admin, grant.supporting_evidence_ref, "GRANT", now)
    await admin.grant(grant)
    p = PriceVersion(
        id=uuid4(),
        capability=use.capability,
        component=UsageComponent.REQUEST,
        currency="USD",
        unit_price=price,
        unit_quantity=Decimal(1),
        currency_quantum=quantum,
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        evidence_id=uuid4(),
    )
    f = FxVersion(
        id=uuid4(),
        currency="USD",
        rate=Decimal("3.5"),
        effective_at=p.effective_at,
        expires_at=p.expires_at,
        evidence_id=uuid4(),
    )
    await register(admin, p.evidence_id, "PRICE", now)
    await admin.price(p)
    await register(admin, f.evidence_id, "FX", now)
    await admin.fx(f)
    config = CapabilityConfig(
        id=uuid4(),
        version=attr.config_version,
        workflow_id=attr.workflow_run_id,
        intended_use=use,
        prices=(PriceBound(price_id=p.id, max_quantity=Decimal(1)),),
        fx_id=f.id,
        requested_count=1,
        adapter_version=uuid4(),
    )
    await admin.config(config)
    await admin.budgets(
        attr,
        provider=use.provider,
        currencies=("USD", "ILS"),
        limit=limit,
        effective_at=p.effective_at,
        expires_at=p.expires_at,
    )
    repo = GovernanceRepository(engine, clock=lambda: now)
    return repo, admin, attr, config, grant, now


def another(attr):
    return attr.model_copy(
        update={"logical_operation_id": uuid4(), "correlation_id": uuid4()}
    )


async def reserve(repo, attr, config, key=None):
    return await repo.reserve(
        attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=key or uuid4()
    )


async def test_reservation_race_and_restart_preserve_all_twelve_caps(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.accounting.repository import GovernanceRepository

    repo, _, attr, config, _, now = await seed(governance_engine, limit=Decimal(".01"))
    results = await asyncio.gather(
        reserve(repo, attr, config),
        reserve(repo, another(attr), config),
        return_exceptions=True,
    )
    winners = [r for r in results if not isinstance(r, BaseException)]
    assert len(winners) == 1
    assert any(
        isinstance(r, AccountingDenied) and r.reason == Reason.BUDGET for r in results
    )
    async with governance_engine.connect() as conn:
        rows = (await conn.execute(select(s.budget_accounts))).mappings().all()
        assert len(rows) == 12
        assert {r["reserved"] for r in rows} == {Decimal(".01")}
    restarted = GovernanceRepository(governance_engine, clock=lambda: now)
    assert (await restarted.get(winners[0].call_id)).state == CallState.RESERVED


async def test_idempotency_conflict_scope_and_omitted_account_fail_closed(
    governance_engine,
):
    from alon_ai.accounting import schema as s

    repo, _, attr, config, _, _ = await seed(governance_engine)
    key = uuid4()
    a, b = await asyncio.gather(
        reserve(repo, attr, config, key), reserve(repo, attr, config, key)
    )
    assert a.call_id == b.call_id
    with pytest.raises(AccountingDenied, match="CONFLICT"):
        await reserve(repo, another(attr), config, key)
    with pytest.raises(AccountingDenied, match="SCOPE"):
        await reserve(
            repo, attr.model_copy(update={"workflow_run_id": uuid4()}), config
        )
    async with governance_engine.begin() as c:
        await c.execute(
            update(s.budget_accounts)
            .where(
                s.budget_accounts.c.scope == "GLOBAL",
                s.budget_accounts.c.currency == "USD",
            )
            .values(expires_at=datetime(2026, 9, 12, 11, tzinfo=UTC))
        )
    with pytest.raises(AccountingDenied, match="BUDGET"):
        await reserve(repo, another(attr), config)


@pytest.mark.parametrize(
    "kind",
    [
        "GLOBAL",
        "EXPERIMENT",
        "WORKFLOW",
        "OPERATION",
        "PROVIDER",
        "EXPERIMENT_PROVIDER",
    ],
)
@pytest.mark.parametrize("currency", ["USD", "ILS"])
async def test_any_single_exhausted_scope_rolls_back_every_reservation(
    governance_engine, kind, currency
):
    from alon_ai.accounting import schema as s

    repo, _, attr, config, _, _ = await seed(governance_engine)
    async with governance_engine.begin() as c:
        await c.execute(
            update(s.budget_accounts)
            .where(
                s.budget_accounts.c.scope == kind,
                s.budget_accounts.c.currency == currency,
            )
            .values(limit=0)
        )
    with pytest.raises(AccountingDenied, match="BUDGET"):
        await reserve(repo, attr, config)
    async with governance_engine.connect() as c:
        assert not (await c.execute(select(s.calls))).all()
        assert set(
            (await c.execute(select(s.budget_accounts.c.reserved))).scalars()
        ) == {Decimal(0)}


async def test_database_rejects_nonfinite_wrong_scope_and_immutable_changes(
    governance_engine,
):
    from alon_ai.accounting import schema as s

    _, _, _attr, _, _grant, _ = await seed(governance_engine)
    for value in ["NaN", "Infinity", "-Infinity", "-1", "0.0000000000000000000000001"]:
        with pytest.raises(DBAPIError):
            async with governance_engine.begin() as c:
                await c.execute(update(s.budget_accounts).values(limit=Decimal(value)))
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(
                update(s.budget_accounts)
                .where(s.budget_accounts.c.scope == "WORKFLOW")
                .values(experiment_id=None)
            )
    for tab in (s.grants, s.prices, s.fx, s.operations, s.configs):
        with pytest.raises(DBAPIError):
            async with governance_engine.begin() as c:
                await c.execute(delete(tab))


def observation(
    cost: str | None = ".001",
    *,
    component=UsageComponent.REQUEST,
    key=None,
    knowledge=CostKnowledge.FINAL,
):
    return UsageObservation(
        component=component,
        quantity=Decimal(1),
        currency="USD",
        cost=Decimal(cost) if cost is not None else None,
        knowledge=knowledge,
        observation_key=key or uuid4(),
    )


async def test_dispatch_quota_race_and_expired_lease_never_frees_unknown_slot(
    governance_engine,
):
    from alon_ai.accounting.repository import GovernanceRepository

    repo, _, attr, config, _, now = await seed(
        governance_engine, quota=1, concurrency=1
    )
    a, b = await asyncio.gather(
        reserve(repo, attr, config), reserve(repo, another(attr), config)
    )
    results = await asyncio.gather(
        repo.dispatch(a.call_id), repo.dispatch(b.call_id), return_exceptions=True
    )
    assert len([r for r in results if not isinstance(r, BaseException)]) == 1
    dispatched = next(r for r in results if not isinstance(r, BaseException))
    assert dispatched.token is not None
    assert (await repo.get(dispatched.call_id)).token is None
    restarted = GovernanceRepository(
        governance_engine, clock=lambda: now + timedelta(seconds=61)
    )
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await restarted.dispatch(dispatched.call_id)
    waiting = b if b.call_id != dispatched.call_id else a
    with pytest.raises(AccountingDenied, match="CONCURRENCY"):
        await restarted.dispatch(waiting.call_id)
    with pytest.raises(AccountingDenied, match="STATE"):
        await restarted.cancel_before_dispatch(dispatched.call_id, command_key=uuid4())
    assert (await restarted.get(dispatched.call_id)).reserved == Decimal(".01")


async def test_grant_revocation_before_dispatch_and_unused_release(governance_engine):
    repo, admin, attr, config, grant, now = await seed(governance_engine)
    call = await reserve(repo, attr, config)
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
    with pytest.raises(AccountingDenied, match="RIGHTS"):
        await repo.dispatch(call.call_id)
    key = uuid4()
    assert (
        await repo.cancel_before_dispatch(call.call_id, command_key=key)
    ).state == CallState.RELEASED
    assert (
        await repo.cancel_before_dispatch(call.call_id, command_key=key)
    ).state == CallState.RELEASED


async def test_final_unknown_correction_overrun_and_cash_are_not_double_spend(
    governance_engine,
):
    from alon_ai.accounting import schema as s

    repo, _, attr, config, _, _ = await seed(governance_engine, limit=Decimal(".01"))
    call = await reserve(repo, attr, config)
    dispatch = await repo.dispatch(call.call_id)
    assert dispatch.token is not None
    unknown = observation(None, knowledge=CostKnowledge.UNAVAILABLE)
    await repo.record_usage(call.call_id, (unknown,), token=dispatch.token)
    assert (await repo.get(call.call_id)).state == CallState.RECONCILING
    final = observation(".002")
    await repo.record_usage(
        call.call_id,
        (final,),
        token=dispatch.token,
        supersedes={final.observation_key: unknown.observation_key},
    )
    key = uuid4()
    receipt = await repo.reconcile(
        call.call_id, command_key=key, evidence_id=await proof(repo, call.call_id)
    )
    assert receipt.accrued == Decimal(".002") and receipt.accrued_ils == Decimal(".007")
    assert (
        await repo.reconcile(
            call.call_id, command_key=key, evidence_id=await proof(repo, call.call_id)
        )
    ).accrued == Decimal(".002")
    correction = observation(".02")
    await repo.record_usage(
        call.call_id,
        (correction,),
        token=dispatch.token,
        supersedes={correction.observation_key: final.observation_key},
    )
    await repo.reconcile(
        call.call_id, command_key=uuid4(), evidence_id=await proof(repo, call.call_id)
    )
    with pytest.raises(AccountingDenied, match="BUDGET"):
        await reserve(repo, another(attr), config)
    cashkey = uuid4()
    await repo.settle_cash(
        call.call_id,
        command_key=cashkey,
        amount=Decimal(".02"),
        evidence_id=await proof(repo, call.call_id, "INVOICE"),
    )
    await repo.settle_cash(
        call.call_id,
        command_key=cashkey,
        amount=Decimal(".02"),
        evidence_id=await proof(repo, call.call_id, "INVOICE"),
    )
    async with governance_engine.connect() as c:
        rows = (await c.execute(select(s.budget_accounts))).mappings().all()
        assert all(r["reserved"] == 0 and r["frozen"] for r in rows)
        assert {r["accrued"] for r in rows} == {Decimal(".02"), Decimal(".07")}
        assert len((await c.execute(select(s.usage))).all()) == 3
        assert len((await c.execute(select(s.cash_entries))).all()) == 1


async def test_subcent_accrual_and_duplicate_usage_do_not_round_to_zero(
    governance_engine,
):
    from alon_ai.accounting import schema as s

    repo, _, attr, config, _, _ = await seed(
        governance_engine, price=Decimal(".000001")
    )
    for _ in range(3):
        call = await reserve(repo, another(attr), config)
        d = await repo.dispatch(call.call_id)
        assert d.token is not None
        obs = observation(".000001")
        await repo.record_usage(call.call_id, (obs,), token=d.token)
        await repo.record_usage(call.call_id, (obs,), token=d.token)
        await repo.reconcile(
            call.call_id,
            command_key=uuid4(),
            evidence_id=await proof(repo, call.call_id),
        )
    async with governance_engine.connect() as c:
        rows = (
            (
                await c.execute(
                    select(s.budget_accounts).where(
                        s.budget_accounts.c.scope == "GLOBAL"
                    )
                )
            )
            .mappings()
            .all()
        )
        assert {r["accrued"] for r in rows} == {Decimal(".000003"), Decimal(".0000105")}
        assert all(r["reserved"] == 0 for r in rows)


async def test_circuit_has_one_half_open_probe_and_restart_preserves_failures(
    governance_engine,
):
    from alon_ai.accounting.repository import GovernanceRepository

    repo, _, attr, config, _, now = await seed(governance_engine)
    for _ in range(2):
        call = await reserve(repo, another(attr), config)
        d = await repo.dispatch(call.call_id)
        assert d.token is not None
        await repo.finish_attempt(call.call_id, token=d.token, success=False)
        await repo.record_usage(call.call_id, (observation(),), token=d.token)
        await repo.reconcile(
            call.call_id,
            command_key=uuid4(),
            evidence_id=await proof(repo, call.call_id),
        )
    a = await reserve(repo, another(attr), config)
    b = await reserve(repo, another(attr), config)
    with pytest.raises(AccountingDenied, match="CIRCUIT"):
        await repo.dispatch(a.call_id)
    restarted = GovernanceRepository(
        governance_engine, clock=lambda: now + timedelta(seconds=11)
    )
    results = await asyncio.gather(
        restarted.dispatch(a.call_id),
        restarted.dispatch(b.call_id),
        return_exceptions=True,
    )
    assert len([r for r in results if not isinstance(r, BaseException)]) == 1
    assert any(
        isinstance(r, AccountingDenied) and r.reason == Reason.CIRCUIT for r in results
    )


async def test_persisted_required_gate_cannot_be_bypassed(governance_engine):
    repo, _, attr, config, _, _ = await seed(governance_engine, gate="SUPPLY")
    with pytest.raises(AccountingDenied, match="GATE"):
        await reserve(repo, attr, config)


async def test_retention_current_scope_fields_expiry_and_revocation(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.providers.rights import RuntimeContent

    repo, admin, attr, config, grant, now = await seed(governance_engine)
    call = await reserve(repo, attr, config)
    await repo.dispatch(call.call_id)
    content = RuntimeContent(
        {
            ContentField.TEXT: ("synthetic-private-text",),
            ContentField.EMAIL: ("not-retainable@invalid.test",),
        },
        grant=grant,
        intended_use=config.intended_use,
        observed_at=now,
    )
    ids = await repo.retain_content(call.call_id, content)
    assert len(ids) == 1
    async with governance_engine.connect() as c:
        row = (await c.execute(select(s.retained))).mappings().one()
        assert row["field"] == "TEXT" and row["values"] == ["synthetic-private-text"]
        audit_rows = (await c.execute(select(s.audit))).mappings().all()
        assert "synthetic-private-text" not in str(audit_rows)
    expired = GovernanceRepository(
        governance_engine, clock=lambda: now + timedelta(seconds=61)
    )
    assert await expired.read_content(call.call_id) == {}
    assert await expired.purge_expired() == 1
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
    with pytest.raises(AccountingDenied, match="RIGHTS"):
        await repo.retain_content(call.call_id, content)


async def test_executor_durable_dispatch_no_transaction_and_timeout_replay(
    governance_engine,
):
    from alon_ai.accounting import schema as s
    from alon_ai.providers.contracts import (
        ProviderCallResult,
        ProviderResultMetadata,
        ResultStatus,
    )
    from alon_ai.providers.execution import GovernedExecutor

    repo, _, attr, config, _, now = await seed(governance_engine)

    class Adapter:
        async def invoke(self, configured, secret):
            async with governance_engine.connect() as c:
                row = (await c.execute(select(s.calls))).mappings().one()
                assert row["state"] == "DISPATCHED"
                # A competing transaction can lock the root while provider awaits.
            async with governance_engine.begin() as c:
                await c.execute(text("SET LOCAL lock_timeout='100ms'"))
                await c.execute(select(s.experiments).with_for_update())
            await asyncio.sleep(10)
            return ProviderCallResult(
                ProviderResultMetadata(
                    capability=config.intended_use.capability,
                    started_at=now,
                    finished_at=now,
                    status=ResultStatus.SUCCEEDED,
                ),
                None,
            )

    executor = GovernedExecutor(repo, adapters={config.adapter_version: Adapter()})
    key = uuid4()
    outcome = await executor.execute(
        attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=key
    )
    assert outcome.receipt.state == CallState.RECONCILING and outcome.content is None
    replay = await executor.execute(
        attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=key
    )
    assert replay.receipt.call_id == outcome.receipt.call_id
    assert replay.content is None
    async with governance_engine.connect() as c:
        assert len((await c.execute(select(s.calls))).all()) == 1
        assert (await c.execute(select(s.authorities.c.active))).scalar_one() == 1


async def test_executor_typed_exception_omits_raw_provider_content(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.providers.execution import GovernedExecutor

    repo, _, attr, config, _, _ = await seed(governance_engine)

    class Adapter:
        async def invoke(self, configured, secret):
            raise RuntimeError("upstream-secret-and-content-sentinel")

    outcome = await GovernedExecutor(
        repo, adapters={config.adapter_version: Adapter()}
    ).execute(attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4())
    assert outcome.receipt.state == CallState.RECONCILING
    async with governance_engine.connect() as c:
        for tab in (s.calls, s.audit, s.usage):
            assert "upstream-secret-and-content-sentinel" not in str(
                (await c.execute(select(tab))).mappings().all()
            )


async def test_timeouts_count_toward_circuit_without_freeing_slots(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.providers.contracts import ProviderErrorCode
    from alon_ai.providers.execution import GovernedExecutor

    repo, _, attr, config, _, _ = await seed(governance_engine, concurrency=10)

    class Adapter:
        async def invoke(self, configured, secret):
            raise TimeoutError("raw timeout body")

    executor = GovernedExecutor(repo, adapters={config.adapter_version: Adapter()})
    for _ in range(2):
        result = await executor.execute(
            another(attr),
            SafeRequestMetadata(config_ref=config.id),
            idempotency_key=uuid4(),
        )
        assert result.error == ProviderErrorCode.TIMEOUT
    call = await reserve(repo, another(attr), config)
    with pytest.raises(AccountingDenied, match="CIRCUIT"):
        await repo.dispatch(call.call_id)
    async with governance_engine.connect() as c:
        assert (await c.execute(select(s.authorities.c.active))).scalar_one() == 2


async def test_database_error_does_not_leak_source_content(governance_engine):
    _repo, admin, _attr, _config, grant, _now = await seed(governance_engine)
    # Duplicate immutable version causes a real database exception. The repository
    # may return only its classified error, never statement parameters/DB detail.
    with pytest.raises(AccountingDenied, match="STATE") as exc:
        await admin.grant(grant)
    assert exc.value.__context__ is None


async def test_foreign_grant_event_identity_is_rejected_in_database(governance_engine):
    from alon_ai.accounting import schema as s

    _, admin, _, _, grant, now = await seed(governance_engine)
    event = GrantEvent(
        event_id=uuid4(),
        grant_id=uuid4(),
        grant_version=1,
        kind=GrantEventKind.REVOKED,
        effective_at=now,
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    await register(admin, event.evidence_ref, "GRANT_EVENT", now)
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(
                s.grant_events.insert().values(
                    id=event.event_id,
                    grant_id=grant.grant_id,
                    grant_version=1,
                    data=event.model_dump(mode="json"),
                    evidence_id=event.evidence_ref,
                )
            )


async def test_multi_component_final_requires_complete_usage_and_exact_fx(
    governance_engine,
):
    repo, admin, attr, config, _, now = await seed(governance_engine)
    p = PriceVersion(
        id=uuid4(),
        capability=config.intended_use.capability,
        component=UsageComponent.SEARCH_RESULT,
        currency="USD",
        unit_price=Decimal(".002"),
        unit_quantity=Decimal(1),
        currency_quantum=Decimal(".01"),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        evidence_id=uuid4(),
    )
    await register(admin, p.evidence_id, "PRICE", now)
    await admin.price(p)
    config = config.model_copy(
        update={
            "id": uuid4(),
            "prices": config.prices
            + (PriceBound(price_id=p.id, max_quantity=Decimal(3)),),
        }
    )
    await admin.config(config)
    call = await reserve(repo, attr, config)
    assert call.reserved == Decimal(".01") and call.reserved_ils == Decimal(".03")
    d = await repo.dispatch(call.call_id)
    assert d.token is not None
    await repo.record_usage(call.call_id, (observation(),), token=d.token)
    with pytest.raises(AccountingDenied, match="UNCERTAIN"):
        await repo.reconcile(
            call.call_id,
            command_key=uuid4(),
            evidence_id=await proof(repo, call.call_id),
        )
    await repo.record_usage(
        call.call_id,
        (observation(".006", component=UsageComponent.SEARCH_RESULT),),
        token=d.token,
    )
    final = await repo.reconcile(
        call.call_id, command_key=uuid4(), evidence_id=await proof(repo, call.call_id)
    )
    assert final.accrued == Decimal(".007") and final.accrued_ils == Decimal(".0245")


async def test_cash_minor_units_and_repeat_command_conflict(governance_engine):
    repo, _, attr, config, _, _ = await seed(governance_engine)
    call = await reserve(repo, attr, config)
    d = await repo.dispatch(call.call_id)
    assert d.token is not None
    await repo.record_usage(call.call_id, (observation(),), token=d.token)
    await repo.reconcile(
        call.call_id, command_key=uuid4(), evidence_id=await proof(repo, call.call_id)
    )
    with pytest.raises(AccountingDenied, match="USAGE"):
        await repo.settle_cash(
            call.call_id,
            command_key=uuid4(),
            amount=Decimal(".0001"),
            evidence_id=await proof(repo, call.call_id, "INVOICE"),
        )


async def test_query_separates_reserved_estimated_accrual_and_cash(governance_engine):
    repo, _, attr, config, _, _ = await seed(governance_engine)
    call = await reserve(repo, attr, config)
    snapshot = await repo.query(call.call_id)
    assert (
        snapshot.live_reserved == Decimal(".01")
        and snapshot.accrued == 0
        and snapshot.cash == 0
    )
    d = await repo.dispatch(call.call_id)
    assert d.token is not None
    obs = observation(".002", knowledge=CostKnowledge.ESTIMATE)
    await repo.record_usage(call.call_id, (obs,), token=d.token)
    snapshot = await repo.query(call.call_id)
    assert snapshot.estimated == Decimal(".002") and snapshot.live_reserved == Decimal(
        ".01"
    )


async def test_postgres_rejects_cross_capability_price_and_missing_proof(
    governance_engine,
):
    from alon_ai.accounting import schema as s

    repo, admin, attr, config, _grant, now = await seed(governance_engine)
    p = PriceVersion(
        id=uuid4(),
        capability=Capability.FIRECRAWL_MAP,
        component=UsageComponent.CAPTURE_PAGE,
        currency="USD",
        unit_price=Decimal(".1"),
        unit_quantity=Decimal(1),
        currency_quantum=Decimal(".01"),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        evidence_id=uuid4(),
    )
    with pytest.raises(AccountingDenied):
        await admin.price(p)  # dangling evidence root
    await register(admin, p.evidence_id, "PRICE", now)
    await admin.price(p)
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(
                s.config_prices.insert().values(
                    config_id=config.id, price_id=p.id, max_quantity=1
                )
            )
    call = await reserve(repo, attr, config)
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(
                update(s.calls)
                .where(s.calls.c.id == call.call_id)
                .values(attribution={})
            )


async def test_scope_actor_mismatch_and_new_child_do_not_reset_parent_budget(
    governance_engine,
):
    from alon_ai.providers.contracts import AgentActor

    repo, admin, attr, config, _, now = await seed(
        governance_engine, limit=Decimal(".01")
    )
    with pytest.raises(AccountingDenied, match="SCOPE"):
        await reserve(
            repo,
            attr.model_copy(update={"actor": AgentActor(agent_run_id=uuid4())}),
            config,
        )
    await reserve(repo, attr, config)
    child = attr.model_copy(
        update={
            "workflow_run_id": uuid4(),
            "operation_run_id": uuid4(),
            "logical_operation_id": uuid4(),
        }
    )
    await admin.scope(child)
    childconfig = config.model_copy(
        update={"id": uuid4(), "workflow_id": child.workflow_run_id}
    )
    await admin.config(childconfig)
    await admin.budgets(
        child,
        provider=Provider.BRAVE,
        currencies=("USD", "ILS"),
        limit=Decimal(100),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    with pytest.raises(AccountingDenied, match="BUDGET"):
        await reserve(repo, child, childconfig)


@pytest.mark.parametrize(
    "capability", [Capability.GMAIL_SEND, Capability.GOOGLE_CALENDAR_WRITE]
)
async def test_generic_writes_denied_even_with_full_configuration(
    governance_engine, capability
):
    from alon_ai.providers.execution import GovernedExecutor

    repo, _, attr, config, _, _ = await seed(governance_engine, capability=capability)

    class Adapter:
        async def invoke(self, config, secret):
            pytest.fail("write adapter must never run")

    with pytest.raises(AccountingDenied, match="WRITE"):
        await GovernedExecutor(
            repo, adapters={config.adapter_version: Adapter()}
        ).execute(
            attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4()
        )


async def test_transient_success_is_not_durable_content_or_replay_cache(
    governance_engine,
):
    import hashlib
    import pickle

    from alon_ai.accounting import schema as s
    from alon_ai.providers.contracts import (
        ProviderCallResult,
        ProviderResultMetadata,
        ResultStatus,
    )
    from alon_ai.providers.execution import GovernedExecutor
    from alon_ai.providers.rights import RuntimeContent

    repo, _, attr, config, grant, now = await seed(governance_engine, transient=True)
    sentinel = "https://synthetic-transient-content.invalid/private"

    class Adapter:
        async def invoke(self, config, secret):
            content = RuntimeContent(
                {ContentField.URL: (sentinel,)},
                grant=grant,
                intended_use=config.intended_use,
                observed_at=now,
            )
            metadata = ProviderResultMetadata(
                capability=config.intended_use.capability,
                started_at=now,
                finished_at=now,
                status=ResultStatus.SUCCEEDED,
                usage=(observation(),),
            )
            return ProviderCallResult(metadata, content)

    executor = GovernedExecutor(repo, adapters={config.adapter_version: Adapter()})
    key = uuid4()
    result = await executor.execute(
        attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=key
    )
    assert result.receipt.state == CallState.FINAL and result.content is not None
    with pytest.raises(TypeError):
        pickle.dumps(result)
    with pytest.raises(AccountingDenied, match="RETENTION"):
        await repo.retain_content(result.receipt.call_id, result.content)
    replay = await executor.execute(
        attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=key
    )
    assert replay.content is None
    async with governance_engine.connect() as c:
        for tab in s.metadata.sorted_tables:
            dump = str((await c.execute(select(tab))).mappings().all())
            assert (
                sentinel not in dump
                and hashlib.sha256(sentinel.encode()).hexdigest() not in dump
            )


async def test_admission_hook_mutations_rollback_with_denied_budget(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.accounting.repository import GovernanceRepository

    repo, _, attr, config, _, now = await seed(
        governance_engine, gate="SUPPLY", limit=Decimal(0)
    )

    class Hook:
        async def admit(self, connection, attribution, call_id, phase):
            await connection.execute(
                s.audit.insert().values(
                    id=uuid4(), kind="SYNTHETIC_ADMISSION", created_at=now
                )
            )

    repo = GovernanceRepository(
        governance_engine, clock=lambda: now, admission_hooks={"SUPPLY": Hook()}
    )
    with pytest.raises(AccountingDenied, match="BUDGET"):
        await reserve(repo, attr, config)
    async with governance_engine.connect() as c:
        assert not (
            await c.execute(
                select(s.audit).where(s.audit.c.kind == "SYNTHETIC_ADMISSION")
            )
        ).all()


async def test_dispatch_preserves_positive_fractional_deadline(governance_engine):
    from alon_ai.accounting import schema as s

    repo, _, attr, config, _, now = await seed(governance_engine)
    attr = attr.model_copy(update={"deadline": now + timedelta(milliseconds=100)})
    call = await reserve(repo, attr, config)
    dispatched = await repo.dispatch(call.call_id)
    assert dispatched.timeout_seconds == pytest.approx(0.1)
    async with governance_engine.connect() as c:
        assert (
            await c.execute(select(s.calls.c.lease_until))
        ).scalar_one() == attr.deadline


async def test_restart_reconciles_with_registered_proof_without_dispatch_token(
    governance_engine,
):
    from alon_ai.accounting.repository import GovernanceRepository

    repo, _, attr, config, _, now = await seed(governance_engine)
    call = await reserve(repo, attr, config)
    await repo.dispatch(call.call_id)  # process dies before receiving response
    restarted = GovernanceRepository(
        governance_engine, clock=lambda: now + timedelta(seconds=30)
    )
    evidence = await proof(restarted, call.call_id)
    await restarted.record_reconciled_usage(
        call.call_id, (observation(".001"),), evidence_id=evidence
    )
    final = await restarted.reconcile(
        call.call_id, command_key=uuid4(), evidence_id=evidence
    )
    assert final.state == CallState.FINAL and final.accrued == Decimal(".001")
    with pytest.raises(AccountingDenied, match="STATE"):
        await restarted.dispatch(call.call_id)
    with pytest.raises(AccountingDenied, match="SCOPE"):
        await restarted.record_reconciled_usage(
            call.call_id, (observation(".001"),), evidence_id=uuid4()
        )


async def test_executor_cancellation_quarantines_occupied_slot(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.providers.execution import GovernedExecutor

    repo, _, attr, config, _, _ = await seed(governance_engine)
    started = asyncio.Event()

    class Adapter:
        async def invoke(self, config, secret):
            started.set()
            await asyncio.Future()
            raise AssertionError("unreachable")

    executor = GovernedExecutor(repo, adapters={config.adapter_version: Adapter()})
    task = asyncio.create_task(
        executor.execute(
            attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4()
        )
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with governance_engine.connect() as c:
        row = (await c.execute(select(s.calls))).mappings().one()
        assert row["state"] == "RECONCILING" and row["reserved"] == Decimal(".01")
        assert (await c.execute(select(s.authorities.c.active))).scalar_one() == 1


async def wait_for_pg_lock(engine, task):
    """Observe an actual blocked SQL statement before advancing the test clock."""
    async with asyncio.timeout(5):
        while not task.done():
            async with engine.connect() as c:
                waiting = await c.scalar(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock')"
                    )
                )
            if waiting:
                return
            await asyncio.sleep(0.01)
    pytest.fail("operation did not wait for the held PostgreSQL lock")


@pytest.mark.parametrize(
    "phase,lock_kind",
    [
        ("reserve", "experiment"),
        ("reserve", "authority"),
        ("reserve", "account"),
        ("dispatch", "experiment"),
        ("dispatch", "authority"),
        ("dispatch", "account"),
        ("retain", "experiment"),
        ("retain", "authority"),
    ],
)
async def test_expiry_during_required_lock_wait_denies(
    governance_engine, phase, lock_kind
):
    from alon_ai.accounting import schema as s
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.providers.rights import RuntimeContent

    _, _, attr, config, grant, now = await seed(governance_engine)
    moment = [now]
    repo = GovernanceRepository(governance_engine, clock=lambda: moment[0])
    attr = attr.model_copy(update={"deadline": now + timedelta(days=3)})
    call = await reserve(repo, attr, config) if phase != "reserve" else None
    if phase == "retain":
        assert call is not None
        await repo.dispatch(call.call_id)
    table = {
        "experiment": s.experiments,
        "authority": s.authorities,
        "account": s.budget_accounts,
    }[lock_kind]
    async with governance_engine.begin() as holding:
        await holding.execute(select(table).with_for_update())
        if phase == "reserve":
            task = asyncio.create_task(reserve(repo, attr, config))
        elif phase == "dispatch":
            assert call is not None
            task = asyncio.ensure_future(repo.dispatch(call.call_id))
        else:
            assert call is not None
            content = RuntimeContent(
                {ContentField.TEXT: ("synthetic-expiring-text",)},
                grant=grant,
                intended_use=config.intended_use,
                observed_at=now,
            )
            task = asyncio.ensure_future(repo.retain_content(call.call_id, content))
        await wait_for_pg_lock(governance_engine, task)
        moment[0] = now + timedelta(days=2)
    with pytest.raises(AccountingDenied):
        await task
    async with governance_engine.connect() as c:
        assert (
            not (
                await c.execute(select(s.calls).where(s.calls.c.state == "DISPATCHED"))
            ).all()
            if phase != "retain"
            else not (await c.execute(select(s.retained))).all()
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign_experiment",
        "foreign_workflow",
        "foreign_operation",
        "foreign_kind",
        "foreign_config_version",
        "foreign_actor",
        "actor_extra",
        "attribution_extra",
        "attribution_version",
        "bad_deadline",
        "bad_correlation",
        "request_extra",
        "request_config",
        "request_count",
        "request_version",
    ],
)
async def test_postgres_rejects_malformed_call_intent_json(governance_engine, mutation):
    import copy

    from alon_ai.accounting import schema as s

    repo, _, attr, config, _, _ = await seed(governance_engine)
    await reserve(repo, attr, config)
    async with governance_engine.connect() as c:
        values = copy.deepcopy(
            dict((await c.execute(select(s.calls))).mappings().one())
        )
    values.update(id=uuid4(), idempotency_key=uuid4(), logical_operation_id=uuid4())
    values["attribution"]["logical_operation_id"] = str(values["logical_operation_id"])
    a = values["attribution"]
    request = values["request"]
    if mutation.startswith("foreign_"):
        field = {
            "foreign_experiment": "experiment_id",
            "foreign_workflow": "workflow_run_id",
            "foreign_operation": "operation_run_id",
            "foreign_kind": "operation_run_kind",
            "foreign_config_version": "config_version",
        }.get(mutation)
        if field:
            a[field] = "DISCOVERY" if field == "operation_run_kind" else str(uuid4())
        else:
            a["actor"] = {
                "schema_version": 1,
                "kind": "agent",
                "agent_run_id": str(uuid4()),
            }
    elif mutation == "actor_extra":
        a["actor"]["raw_provider_body"] = "source-sentinel"
    elif mutation == "attribution_extra":
        a["raw_provider_body"] = "source-sentinel"
    elif mutation == "attribution_version":
        a["schema_version"] = 2
    elif mutation == "bad_deadline":
        a["deadline"] = "not-a-time"
    elif mutation == "bad_correlation":
        a["correlation_id"] = "source-sentinel"
    elif mutation == "request_extra":
        request["raw_provider_body"] = "source-sentinel"
    elif mutation == "request_config":
        request["config_ref"] = str(uuid4())
    elif mutation == "request_count":
        request["requested_count"] = 2
    else:
        request["schema_version"] = 2
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(s.calls.insert().values(**values))


@pytest.mark.parametrize(
    "mutation",
    [
        "raw_body",
        "wrong_capability",
        "wrong_status",
        "wrong_error",
        "wrong_version",
        "bad_external_id",
        "bad_timing",
        "usage_extra",
        "usage_unknown",
        "usage_cost",
        "usage_currency",
        "usage_foreign_identity",
    ],
)
async def test_postgres_rejects_malformed_result_json(governance_engine, mutation):
    from alon_ai.accounting import schema as s
    from alon_ai.providers.contracts import ProviderResultMetadata, ResultStatus

    repo, _, attr, config, _, now = await seed(governance_engine)
    call = await reserve(repo, attr, config)
    dispatch = await repo.dispatch(call.call_id)
    assert dispatch.token is not None
    obs = observation()
    await repo.record_usage(call.call_id, (obs,), token=dispatch.token)
    value = ProviderResultMetadata(
        capability=config.intended_use.capability,
        started_at=now,
        finished_at=now,
        status=ResultStatus.SUCCEEDED,
        usage=(obs,),
    ).model_dump(mode="json")
    if mutation == "raw_body":
        value["raw_provider_body"] = "source-sentinel"
    elif mutation == "wrong_capability":
        value["capability"] = "FIRECRAWL_MAP"
    elif mutation == "wrong_status":
        value["status"] = "UNTRUSTED"
    elif mutation == "wrong_error":
        value["error_code"] = "TIMEOUT"
    elif mutation == "wrong_version":
        value["schema_version"] = 2
    elif mutation == "bad_external_id":
        value["external_request_id"] = "raw source sentence with spaces"
    elif mutation == "bad_timing":
        value["finished_at"] = "not-a-time"
    elif mutation == "usage_extra":
        value["usage"][0]["raw_provider_body"] = "source-sentinel"
    elif mutation == "usage_unknown":
        value["usage"][0]["component"] = "UNREGISTERED"
    elif mutation == "usage_cost":
        value["usage"][0]["cost"] = "NaN"
    elif mutation == "usage_currency":
        value["usage"][0]["currency"] = "EUR"
    else:
        value["usage"][0]["observation_key"] = str(uuid4())
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as c:
            await c.execute(
                update(s.calls)
                .where(s.calls.c.id == call.call_id)
                .values(result_metadata=value, finished_at=now)
            )


@pytest.mark.parametrize("target_phase", ["RESERVE", "DISPATCH"])
async def test_expiry_during_sql_admission_hook_wait_denies(
    governance_engine, target_phase
):
    from alon_ai.accounting import schema as s
    from alon_ai.accounting.repository import GovernanceRepository

    _, _, attr, config, grant, now = await seed(governance_engine, gate="SUPPLY")
    moment = [now]

    class Hook:
        async def admit(self, connection, attribution, call_id, phase):
            if phase == target_phase:
                await connection.execute(
                    select(s.evidence)
                    .where(s.evidence.c.id == grant.supporting_evidence_ref)
                    .with_for_update()
                )

    repo = GovernanceRepository(
        governance_engine, clock=lambda: moment[0], admission_hooks={"SUPPLY": Hook()}
    )
    attr = attr.model_copy(update={"deadline": now + timedelta(days=3)})
    call = await reserve(repo, attr, config) if target_phase == "DISPATCH" else None
    async with governance_engine.begin() as holding:
        await holding.execute(
            select(s.evidence)
            .where(s.evidence.c.id == grant.supporting_evidence_ref)
            .with_for_update()
        )
        task = (
            asyncio.ensure_future(repo.dispatch(call.call_id))
            if call
            else asyncio.create_task(reserve(repo, attr, config))
        )
        await wait_for_pg_lock(governance_engine, task)
        moment[0] = now + timedelta(days=2)
    with pytest.raises(AccountingDenied):
        await task


async def test_retention_expiry_during_content_row_lock_wait_denies(governance_engine):
    from alon_ai.accounting import schema as s
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.providers.rights import RuntimeContent

    _, _, attr, config, grant, now = await seed(governance_engine)
    moment = [now]
    repo = GovernanceRepository(governance_engine, clock=lambda: moment[0])
    call = await reserve(repo, attr, config)
    await repo.dispatch(call.call_id)
    content = RuntimeContent(
        {ContentField.TEXT: ("synthetic-expiring-text",)},
        grant=grant,
        intended_use=config.intended_use,
        observed_at=now,
    )
    await repo.retain_content(call.call_id, content)
    async with governance_engine.begin() as holding:
        await holding.execute(select(s.retained).with_for_update())
        task = asyncio.ensure_future(repo.retain_content(call.call_id, content))
        await wait_for_pg_lock(governance_engine, task)
        moment[0] = now + timedelta(seconds=61)
    with pytest.raises(AccountingDenied, match="RETENTION"):
        await task
    assert await repo.read_content(call.call_id) == {}
