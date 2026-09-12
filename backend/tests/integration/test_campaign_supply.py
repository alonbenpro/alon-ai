import asyncio

"""Synthetic provisional facts against real PostgreSQL; never real accepted leads."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, update

from alon_ai.policies.campaign_supply import (
    DiscoveryPlan,
    Filter,
    IdentityEvidence,
    ReferenceEvidence,
    SupplyDenied,
    SupplyFact,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 12, 12, tzinfo=UTC)


async def setup(engine, existing_exp=None, supply_deadline=NOW + timedelta(hours=1)):
    from alon_ai.accounting.schema import experiments
    from alon_ai.supply.repository import CampaignSupplyRepository, SupplyEvidenceWriter

    exp, rule, verifier = existing_exp or uuid4(), uuid4(), uuid4()
    if existing_exp is None:
        async with engine.begin() as c:
            await c.execute(insert(experiments).values(id=exp))
    repo = CampaignSupplyRepository(engine, clock=lambda: NOW)
    writer = SupplyEvidenceWriter(engine)
    filters = tuple(Filter(dimension="QUERY", value=uuid4()) for _ in range(3))
    for ref, kind, definition, dimension in [
        (rule, "QUALIFICATION_RULE", "synthetic fixed rules", None),
        (verifier, "VERIFICATION_POLICY", "synthetic verifier", None),
    ] + [
        (f.value, "FILTER", f"synthetic query {n}", f.dimension)
        for n, f in enumerate(filters)
    ]:
        await writer.reference(
            ReferenceEvidence(
                id=ref,
                experiment_id=exp,
                kind=kind,  # pyright: ignore[reportArgumentType]
                definition=definition,
                dimension=dimension,
                mode="SYNTHETIC",
                registered_by=uuid4(),
            )
        )
    plan = DiscoveryPlan(qualification_rule_id=rule, filters=(filters[0],))
    await repo.create(exp, plan, filters, verifier, supply_deadline)
    return repo, writer, exp, plan, filters


async def candidate(
    repo,
    writer,
    exp,
    batch,
    n,
    *,
    supported: bool | None = True,
    until=NOW + timedelta(hours=2),
    clearance_kind="IDENTITY_CLEAR",
):
    provenance = uuid4()
    await writer.reference(
        ReferenceEvidence(
            id=provenance,
            experiment_id=exp,
            kind="INDEPENDENT_SOURCE",
            definition=f"synthetic permitted source {n}",
            mode="SYNTHETIC",
            registered_by=uuid4(),
        )
    )
    identity = IdentityEvidence(
        id=uuid4(),
        experiment_id=exp,
        provenance_ref=provenance,
        normalized_key=f"synthetic-{n}",
        mode="SYNTHETIC",
        registered_by=uuid4(),
        observed_at=NOW,
        valid_until=until,
    )
    await writer.identity(identity)

    async def fact(kind, **kw):
        value = SupplyFact(
            id=kw.get("contact_ref", uuid4()) if kind == "SOURCE_EMAIL" else uuid4(),
            identity_id=identity.id,
            kind=kind,
            mode="SYNTHETIC",
            registered_by=identity.registered_by,
            observed_at=NOW,
            valid_until=kw.pop("until", until),
            **kw,
        )
        await writer.fact(value)
        return value.id

    clearance = await fact(clearance_kind)
    candidate_id = await repo.admit_candidate(
        batch,
        identity.id,
        clearance,
        uuid4(),
        observations=(await repo.batch_plan(batch)).filters,
    )
    if supported:
        contact = uuid4()
        source = await fact("SOURCE_EMAIL", contact_ref=contact)
        policy = await repo.verification_policy(exp)
        verified = await fact("VERIFIED", contact_ref=contact, policy_ref=policy)
        await repo.resolve_contact(candidate_id, source, verified)
    elif supported is False:
        await repo.resolve_contact(candidate_id, await fact("EMAIL_ABSENT"))
    return candidate_id, fact


async def test_begin_and_admission_are_durable_unique_and_capped(governance_engine):
    from alon_ai.supply.repository import CampaignSupplyRepository

    repo, writer, exp, plan, _filters = await setup(governance_engine)
    command = uuid4()
    batch = await repo.begin_batch(exp, 1, plan, command)
    assert await repo.begin_batch(exp, 1, plan, command) == batch
    for n in range(100):
        await candidate(repo, writer, exp, batch, n, supported=False)
    with pytest.raises(SupplyDenied):
        await candidate(repo, writer, exp, batch, 100)
    reopened = CampaignSupplyRepository(governance_engine, clock=lambda: NOW)
    snapshot = await reopened.snapshot(exp)
    assert (
        snapshot.logical_slots,
        snapshot.batches_used,
        snapshot.businesses_discovered,
    ) == ((1,), 1, 100)
    with pytest.raises(SupplyDenied):
        await repo.begin_batch(exp, 4, plan, uuid4())


async def test_email_shortage_requires_feedback_change_then_hard_stops(
    governance_engine,
):
    repo, writer, exp, plan, filters = await setup(governance_engine)
    first = await repo.begin_batch(exp, 1, plan, uuid4())
    await candidate(repo, writer, exp, first, 0, supported=False)
    feedback = await repo.close_contactability(first, uuid4())
    assert feedback is not None
    with pytest.raises(SupplyDenied):
        await repo.begin_batch(exp, 2, plan, uuid4(), feedback)
    changed = DiscoveryPlan(
        qualification_rule_id=plan.qualification_rule_id, filters=(filters[1],)
    )
    second = await repo.begin_batch(exp, 2, changed, uuid4(), feedback)
    for n in range(1, 50):
        await candidate(repo, writer, exp, second, n)
    assert await repo.close_contactability(second, uuid4()) is None
    result = await repo.snapshot(exp)
    assert result.state == "EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2"
    assert result.supported_emails == 49 and result.accepted == 0
    with pytest.raises(SupplyDenied):
        await repo.begin_batch(exp, 3, changed, uuid4(), feedback)


async def test_source_failure_stays_unresolved_and_independent_candidate_continues(
    governance_engine,
):
    from alon_ai.supply import schema as s

    repo, writer, exp, plan, _ = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    candidate_id, fact = await candidate(repo, writer, exp, batch, 0, supported=None)
    failure = await fact("SOURCE_FAILURE")
    assert await repo.resolve_contact(candidate_id, failure) == "SOURCE_FAILURE"
    assert (await repo.snapshot(exp)).state == "ACTIVE"
    with pytest.raises(SupplyDenied):
        await repo.close_contactability(batch, uuid4())
    await candidate(repo, writer, exp, batch, 1)
    assert (
        await repo.resolve_contact(candidate_id, await fact("EMAIL_ABSENT"))
        == "EMAIL_NOT_FOUND"
    )
    async with governance_engine.connect() as c:
        assert (
            await c.execute(select(s.contact_failures.c.source_id))
        ).scalar_one() == failure
    assert (await repo.snapshot(exp)).businesses_discovered == 2


async def qualify(repo, engine, candidate_id, fact, rule, outcome="QUALIFIED"):
    from alon_ai.supply import schema as s

    # Synthetic fixture supplies the already-dispatched projection. Separate
    # governed-executor tests below prove the only application writer is its hook.
    async with engine.begin() as c:
        await c.execute(
            update(s.candidates)
            .where(s.candidates.c.id == candidate_id)
            .values(deep_started=True)
        )
    proof = await fact(outcome, policy_ref=rule)
    await repo.accept_qualification(candidate_id, proof)
    return proof


@pytest.mark.parametrize("slots", [(1,), (1, 2), (1, 3), (1, 2, 3)])
async def test_logical_paths_reach_exactly_fifty_without_reset(
    governance_engine, slots
):
    from alon_ai.supply.repository import CampaignSupplyRepository

    repo, writer, exp, plan, filters = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    initial = 25 if 2 in slots else 50
    candidates = [await candidate(repo, writer, exp, batch, n) for n in range(initial)]
    if 2 in slots:
        await candidate(repo, writer, exp, batch, 90, supported=False)
        fb = await repo.close_contactability(batch, uuid4())
        plan = DiscoveryPlan(
            qualification_rule_id=plan.qualification_rule_id, filters=(filters[1],)
        )
        batch = await repo.begin_batch(exp, 2, plan, uuid4(), fb)
        candidates += [
            await candidate(repo, writer, exp, batch, n) for n in range(initial, 50)
        ]
    await repo.close_contactability(batch, uuid4())
    for n, (cid, fact) in enumerate(candidates):
        await qualify(
            repo,
            governance_engine,
            cid,
            fact,
            plan.qualification_rule_id,
            "REJECTED_FIT" if n == 49 and 3 in slots else "QUALIFIED",
        )
    if 3 in slots:
        fb = await repo.close_qualification(batch, uuid4())
        changed = DiscoveryPlan(
            qualification_rule_id=plan.qualification_rule_id, filters=(filters[2],)
        )
        batch = await repo.begin_batch(exp, 3, changed, uuid4(), fb)
        cid, fact = await candidate(repo, writer, exp, batch, 99)
        await repo.close_contactability(batch, uuid4())
        proof = await qualify(
            repo, governance_engine, cid, fact, plan.qualification_rule_id
        )
        assert await repo.accept_qualification(cid, proof) == "QUALIFIED"
    reopened = CampaignSupplyRepository(governance_engine, clock=lambda: NOW)
    snapshot = await reopened.snapshot(exp)
    assert (
        snapshot.state,
        snapshot.accepted,
        snapshot.logical_slots,
        snapshot.batches_used,
    ) == ("TARGET_50_REACHED", 50, slots, len(slots))
    with pytest.raises(SupplyDenied):
        await reopened.begin_batch(exp, 1, plan, uuid4())


async def test_competing_fiftieth_acceptances_have_one_winner(governance_engine):
    from alon_ai.supply import schema as s

    repo, writer, exp, plan, _ = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    records = [await candidate(repo, writer, exp, batch, n) for n in range(51)]
    await repo.close_contactability(batch, uuid4())
    for cid, fact in records[:49]:
        await qualify(repo, governance_engine, cid, fact, plan.qualification_rule_id)
    remaining = []
    async with governance_engine.begin() as c:
        for cid, _ in records[49:]:
            await c.execute(
                update(s.candidates)
                .where(s.candidates.c.id == cid)
                .values(deep_started=True)
            )
    for cid, fact in records[49:]:
        remaining.append(
            (cid, await fact("QUALIFIED", policy_ref=plan.qualification_rule_id))
        )
    results = await asyncio.gather(
        *(repo.accept_qualification(cid, proof) for cid, proof in remaining),
        return_exceptions=True,
    )
    assert sum(r == "QUALIFIED" for r in results) == 1
    assert sum(isinstance(r, SupplyDenied) for r in results) == 1
    assert (await repo.snapshot(exp)).accepted == 50


async def test_final_acceptance_fences_governed_dispatch_and_preserves_unrelated_reads(
    governance_engine, monkeypatch
):
    from test_governance import another, reserve, seed

    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import (
        GovernanceProvisioner,
        GovernanceRepository,
        lock_experiment,
    )
    from alon_ai.providers.contracts import SafeRequestMetadata
    from alon_ai.providers.execution import GovernedExecutor
    from alon_ai.supply import schema as s
    from alon_ai.supply.repository import SupplyAdmissionHook

    accounting, _, attr, config, _, _ = await seed(governance_engine, gate="SUPPLY")
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    records = [await candidate(repo, writer, exp, batch, n) for n in range(51)]
    await repo.close_contactability(batch, uuid4())
    for cid, fact in records[:49]:
        await qualify(repo, governance_engine, cid, fact, plan.qualification_rule_id)
    last, fact = records[49]
    async with governance_engine.begin() as c:
        await c.execute(
            update(s.candidates)
            .where(s.candidates.c.id == last)
            .values(deep_started=True)
        )
    proof = await fact("QUALIFIED", policy_ref=plan.qualification_rule_id)
    await repo.bind_operation(attr, batch, "DEEP", config.id, records[50][0])
    governed = GovernanceRepository(
        governance_engine,
        clock=lambda: NOW,
        admission_hooks={"SUPPLY": SupplyAdmissionHook(repo)},
    )
    key = uuid4()
    call = await reserve(governed, attr, config, key)
    entered, release = asyncio.Event(), asyncio.Event()

    async def pause_after_fence(c, experiment_id):
        result = await lock_experiment(c, experiment_id)
        entered.set()
        await release.wait()
        return result

    monkeypatch.setattr("alon_ai.supply.repository.lock_experiment", pause_after_fence)
    acceptance = asyncio.ensure_future(repo.accept_qualification(last, proof))
    await asyncio.wait_for(entered.wait(), 2)

    class NoCall:
        calls = 0

        async def invoke(self, config, secret):
            self.calls += 1
            raise AssertionError("terminal supply reached an adapter")

    adapter = NoCall()
    executor = GovernedExecutor(governed, adapters={config.adapter_version: adapter})
    dispatch = asyncio.create_task(
        executor.execute(
            attr,
            SafeRequestMetadata(
                config_ref=config.id, requested_count=config.requested_count
            ),
            idempotency_key=key,
        )
    )
    await asyncio.sleep(0.03)
    release.set()
    await acceptance
    with pytest.raises(AccountingDenied):
        await dispatch
    assert adapter.calls == 0
    assert (await governed.get(call.call_id)).state == "RELEASED"
    async with governance_engine.connect() as c:
        stopped = (
            (
                await c.execute(
                    select(s.candidates).where(s.candidates.c.id == records[50][0])
                )
            )
            .mappings()
            .one()
        )
        assert stopped["stopped"] and not stopped["deep_started"]
    # A trusted unrelated operation is not supply-owned merely because it uses
    # the same research capability; later inbox/evaluation work stays possible.
    unrelated = another(attr).model_copy(update={"operation_run_id": uuid4()})
    admin = GovernanceProvisioner(governance_engine)
    await admin.scope(unrelated, gate_kind="NONE")
    await admin.budgets(
        unrelated,
        provider=config.intended_use.provider,
        currencies=("USD", "ILS"),
        limit=__import__("decimal").Decimal(1),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
    )
    fresh = await reserve(accounting, unrelated, config)
    assert (await accounting.dispatch(fresh.call_id)).state == "DISPATCHED"


@pytest.mark.parametrize("phase", ["RESERVE", "DISPATCH"])
async def test_late_budget_wait_obeys_attenuated_evidence_deadline(
    governance_engine, phase
):
    from sqlalchemy import text
    from test_governance import reserve, seed

    from alon_ai.accounting import schema as g
    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.supply import schema as s
    from alon_ai.supply.repository import SupplyAdmissionHook

    _, _, attr, config, _, _ = await seed(governance_engine, gate="SUPPLY")
    repo, writer, exp, plan, _ = await setup(
        governance_engine, attr.experiment_id, supply_deadline=NOW + timedelta(hours=3)
    )
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    records = [
        await candidate(
            repo,
            writer,
            exp,
            batch,
            n,
            until=NOW + timedelta(hours=1 if n == 49 else 2),
        )
        for n in range(50)
    ]
    await repo.close_contactability(batch, uuid4())
    # The last member of the email quorum expires before the target candidate.
    with pytest.raises(SupplyDenied, match="DEADLINE_BOUND"):
        await repo.bind_operation(
            attr.model_copy(update={"deadline": NOW + timedelta(hours=2)}),
            batch,
            "DEEP",
            config.id,
            records[0][0],
        )
    await repo.bind_operation(attr, batch, "DEEP", config.id, records[0][0])
    now = [NOW]
    repo.clock = lambda: now[0]
    entered = asyncio.Event()
    hook = SupplyAdmissionHook(repo)

    tested_phase = phase
    contender_pid = None

    class ObservedHook:
        async def admit(self, connection, attribution, call_id, phase):
            nonlocal contender_pid
            await hook.admit(connection, attribution, call_id, phase)
            if phase == tested_phase:
                contender_pid = await connection.scalar(text("SELECT pg_backend_pid()"))
                entered.set()

    governed = GovernanceRepository(
        governance_engine,
        clock=lambda: now[0],
        admission_hooks={"SUPPLY": ObservedHook()},
    )
    call = await reserve(governed, attr, config) if phase == "DISPATCH" else None
    entered.clear()
    async with governance_engine.begin() as holder:
        await holder.execute(
            select(g.budget_accounts)
            .where(g.budget_accounts.c.scope == "GLOBAL")
            .with_for_update()
        )
        task = asyncio.ensure_future(
            governed.dispatch(call.call_id) if call else reserve(governed, attr, config)
        )
        await asyncio.wait_for(entered.wait(), 2)
        assert contender_pid is not None
        # The exact command (not another test transaction) must actually be
        # blocked on the held budget lock. The hook event alone proves no wait.
        async with asyncio.timeout(5):
            while True:
                async with governance_engine.connect() as observing:
                    blocked = await observing.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid=:pid AND datname=current_database() AND wait_event_type='Lock')"
                        ),
                        {"pid": contender_pid},
                    )
                if blocked:
                    break
                assert not task.done(), (
                    "provider command finished before its budget lock wait"
                )
                await asyncio.sleep(0.01)
        now[0] = attr.deadline
    with pytest.raises(AccountingDenied, match="DEADLINE"):
        await task
    async with governance_engine.connect() as c:
        assert not (
            await c.execute(
                select(s.candidates.c.deep_started).where(
                    s.candidates.c.id == records[0][0]
                )
            )
        ).scalar_one()
        assert (await c.execute(select(g.authorities.c.quota_used))).scalar_one() == 0
        states = list((await c.execute(select(g.calls.c.state))).scalars())
        assert states == (["RESERVED"] if phase == "DISPATCH" else [])


@pytest.mark.parametrize(
    "attack",
    [
        "fixed_target",
        "fake_success",
        "fake_shortage",
        "raw_plan",
        "cross_scope",
        "wrong_verifier",
        "mutate_identity",
        "mutate_contact",
        "mutate_feedback",
        "duplicate_semantics",
        "cosmetic_plan",
        "fake_feedback",
    ],
)
async def test_sql_rejects_malformed_cross_scope_and_immutable_supply_facts(
    governance_engine, attack
):
    from sqlalchemy.exc import DBAPIError

    from alon_ai.supply import schema as s

    repo, writer, exp, plan, filters = await setup(governance_engine)
    foreign_exp = None
    if attack == "cross_scope":
        _, _, foreign_exp, _, _ = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    cid, _ = await candidate(repo, writer, exp, batch, 0, supported=False)
    fb = await repo.close_contactability(batch, uuid4())
    async with governance_engine.connect() as conn:
        identity = (await conn.execute(select(s.identities))).mappings().one()
        contact = (await conn.execute(select(s.contacts))).mappings().one()
        brief = (await conn.execute(select(s.feedback))).mappings().one()
        ref = (
            (
                await conn.execute(
                    select(s.references).where(s.references.c.id == filters[0].value)
                )
            )
            .mappings()
            .one()
        )
    async with governance_engine.begin() as c:
        with pytest.raises(DBAPIError):
            async with c.begin_nested():
                if attack == "fixed_target":
                    await c.execute(
                        update(s.plans)
                        .where(s.plans.c.experiment_id == exp)
                        .values(qualified_contactable_target=49)
                    )
                elif attack in {"fake_success", "fake_shortage"}:
                    await c.execute(
                        insert(s.outcomes).values(
                            experiment_id=exp,
                            command_key=uuid4(),
                            reason="TARGET_50_REACHED"
                            if attack == "fake_success"
                            else "EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2",
                            achieved=0,
                            batches_used=1,
                            businesses_discovered=1,
                        )
                    )
                elif attack == "raw_plan":
                    await c.execute(
                        update(s.plans)
                        .where(s.plans.c.experiment_id == exp)
                        .values(initial_plan={"raw_provider_body": "forbidden"})
                    )
                elif attack == "cross_scope":
                    await c.execute(
                        insert(s.facts).values(
                            id=uuid4(),
                            identity_id=identity["id"],
                            experiment_id=foreign_exp,
                            kind="EMAIL_ABSENT",
                            mode="SYNTHETIC",
                            registered_by=uuid4(),
                            observed_at=NOW,
                            valid_until=NOW + timedelta(hours=1),
                        )
                    )
                elif attack == "wrong_verifier":
                    await c.execute(
                        insert(s.facts).values(
                            id=uuid4(),
                            identity_id=identity["id"],
                            experiment_id=exp,
                            kind="VERIFIED",
                            contact_ref=contact["source_id"],
                            policy_ref=filters[0].value,
                            mode="SYNTHETIC",
                            registered_by=uuid4(),
                            observed_at=NOW,
                            valid_until=NOW + timedelta(hours=1),
                        )
                    )
                elif attack == "mutate_identity":
                    await c.execute(
                        update(s.identities)
                        .where(s.identities.c.id == identity["id"])
                        .values(normalized_key="replacement")
                    )
                elif attack == "mutate_contact":
                    await c.execute(
                        update(s.contacts)
                        .where(s.contacts.c.candidate_id == cid)
                        .values(outcome="SUPPORTED")
                    )
                elif attack == "mutate_feedback":
                    await c.execute(
                        update(s.feedback)
                        .where(s.feedback.c.id == fb)
                        .values(payload={})
                    )
                elif attack == "duplicate_semantics":
                    await c.execute(
                        insert(s.references).values(**dict(ref, id=uuid4()))
                    )
                elif attack == "cosmetic_plan":
                    await c.execute(
                        insert(s.batches).values(
                            id=uuid4(),
                            experiment_id=exp,
                            slot=2,
                            command_key=uuid4(),
                            feedback_id=fb,
                            plan=plan.model_dump(mode="json"),
                        )
                    )
                else:
                    await c.execute(
                        insert(s.feedback).values(
                            **dict(brief, id=uuid4(), payload={"deficit": 1})
                        )
                    )


@pytest.mark.parametrize(
    "reason",
    [
        "CANCELLED",
        "BUDGET_EXHAUSTED",
        "DEADLINE_EXHAUSTED",
        "PROVIDER_FAILURE",
        "SOURCE_FAILURE",
        "SEARCH_EXHAUSTED",
        "SAFETY_STOP",
    ],
)
async def test_explicit_early_stop_is_unsuccessful_and_replayable(
    governance_engine, reason
):
    repo, writer, exp, plan, _ = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    await candidate(repo, writer, exp, batch, 0)
    key = uuid4()
    result = await repo.stop(exp, reason, key)
    assert result.state == reason and result.accepted == 0
    assert await repo.stop(exp, reason, key) == result
    with pytest.raises(SupplyDenied):
        await repo.begin_batch(exp, 2, plan, uuid4())


async def test_deep_work_before_fifty_or_without_email_and_missing_owned_binding_denied(
    governance_engine,
):
    from test_governance import reserve, seed

    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.supply.repository import SupplyAdmissionHook

    _, _, attr, config, _, _ = await seed(governance_engine, gate="SUPPLY")
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    cid, _ = await candidate(repo, writer, exp, batch, 0)
    noemail, _ = await candidate(repo, writer, exp, batch, 1, supported=False)
    for candidate_id in (cid, noemail):
        with pytest.raises(SupplyDenied):
            await repo.bind_operation(attr, batch, "DEEP", config.id, candidate_id)
    governed = GovernanceRepository(
        governance_engine,
        clock=lambda: NOW,
        admission_hooks={"SUPPLY": SupplyAdmissionHook(repo)},
    )
    with pytest.raises(AccountingDenied):
        await reserve(governed, attr, config)
    for n in range(2, 51):
        await candidate(repo, writer, exp, batch, n)
    await repo.close_contactability(batch, uuid4())
    with pytest.raises(SupplyDenied, match="EMAIL_NOT_FOUND"):
        await repo.bind_operation(attr, batch, "DEEP", config.id, noemail)


@pytest.mark.parametrize("yield_count", [0, 25])
async def test_evidence_backed_empty_or_low_yield_can_retry_without_fake_email_failures(
    governance_engine, yield_count
):
    from alon_ai.policies.campaign_supply import DiscoveryCompletionEvidence
    from alon_ai.supply import schema as s

    repo, writer, exp, plan, filters = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    for n in range(yield_count):
        await candidate(repo, writer, exp, batch, n)
    await writer.discovery_completion(
        DiscoveryCompletionEvidence(
            id=uuid4(),
            batch_id=batch,
            filter=filters[0],
            kind="QUERY_COMPLETE",
            mode="SYNTHETIC",
            registered_by=uuid4(),
            observed_at=NOW,
        )
    )
    fb = await repo.close_contactability(batch, uuid4())
    # A justified additional query is material; replacement is not mandatory.
    new = DiscoveryPlan(
        qualification_rule_id=plan.qualification_rule_id,
        filters=(filters[0], filters[1]),
    )
    second = await repo.begin_batch(exp, 2, new, uuid4(), fb)
    async with governance_engine.connect() as c:
        change = (
            (
                await c.execute(
                    select(s.plan_changes).where(s.plan_changes.c.batch_id == second)
                )
            )
            .mappings()
            .one()
        )
        assert change["source_batch_id"] == batch and change[
            "prior_plan"
        ] == plan.model_dump(mode="json")
        assert change["new_plan"] == new.model_dump(mode="json")
        assert "EMAIL_NOT_FOUND" not in str(
            (await c.execute(select(s.feedback.c.payload))).scalar_one()
        )


async def test_missing_or_foreign_completion_cannot_invent_yield_failure(
    governance_engine,
):
    from alon_ai.policies.campaign_supply import DiscoveryCompletionEvidence

    repo, writer, exp, plan, filters = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    with pytest.raises(SupplyDenied):
        await writer.discovery_completion(
            DiscoveryCompletionEvidence(
                id=uuid4(),
                batch_id=batch,
                filter=Filter(dimension="QUERY", value=uuid4()),
                kind="QUERY_COMPLETE",
                mode="SYNTHETIC",
                registered_by=uuid4(),
                observed_at=NOW,
            )
        )
    fb = await repo.close_contactability(batch, uuid4())
    new = DiscoveryPlan(
        qualification_rule_id=plan.qualification_rule_id, filters=(filters[1],)
    )
    with pytest.raises(SupplyDenied, match="UNJUSTIFIED_CHANGE"):
        await repo.begin_batch(exp, 2, new, uuid4(), fb)
    assert (await repo.stop(exp, "SEARCH_EXHAUSTED", uuid4())).accepted == 0


async def test_expired_prior_acceptance_cannot_fabricate_current_fiftieth(
    governance_engine,
):
    from alon_ai.supply import schema as s

    repo, writer, exp, plan, _ = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    records = [await candidate(repo, writer, exp, batch, n) for n in range(50)]
    await repo.close_contactability(batch, uuid4())
    async with governance_engine.begin() as c:
        await c.execute(
            update(s.candidates)
            .where(s.candidates.c.experiment_id == exp)
            .values(deep_started=True)
        )
    for n, (cid, fact) in enumerate(records[:49]):
        proof = await fact(
            "QUALIFIED",
            policy_ref=plan.qualification_rule_id,
            until=NOW + timedelta(minutes=30) if n == 0 else NOW + timedelta(hours=2),
        )
        await repo.accept_qualification(cid, proof)
    repo.clock = lambda: NOW + timedelta(minutes=31)
    last, fact = records[49]
    with pytest.raises(SupplyDenied, match="STALE_ACCEPTED_EVIDENCE"):
        await repo.accept_qualification(
            last, await fact("QUALIFIED", policy_ref=plan.qualification_rule_id)
        )
    result = await repo.snapshot(exp)
    assert (
        result.state == "ACTIVE"
        and result.accepted == 49
        and result.current_qualified_contactable == 48
    )


async def test_concurrent_last_candidate_and_batch_replay_preserve_entitlements(
    governance_engine,
):
    repo, writer, exp, plan, _ = await setup(governance_engine)
    key = uuid4()
    first, duplicate = await asyncio.gather(
        repo.begin_batch(exp, 1, plan, key), repo.begin_batch(exp, 1, plan, key)
    )
    assert first == duplicate
    for n in range(99):
        await candidate(repo, writer, exp, first, n, supported=False)
    results = await asyncio.gather(
        candidate(repo, writer, exp, first, 99, supported=False),
        candidate(repo, writer, exp, first, 100, supported=False),
        return_exceptions=True,
    )
    assert sum(isinstance(r, SupplyDenied) for r in results) == 1
    assert (await repo.snapshot(exp)).businesses_discovered == 100


async def test_third_qualification_shortfall_closes_at_three_hundred_unique_candidates(
    governance_engine,
):
    repo, writer, exp, plan, filters = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    records = [
        await candidate(repo, writer, exp, batch, n, supported=n < 49)
        for n in range(100)
    ]
    fb = await repo.close_contactability(batch, uuid4())
    plan = DiscoveryPlan(
        qualification_rule_id=plan.qualification_rule_id, filters=(filters[1],)
    )
    batch = await repo.begin_batch(exp, 2, plan, uuid4(), fb)
    for n in range(100, 200):
        records.append(await candidate(repo, writer, exp, batch, n, supported=n == 100))
    await repo.close_contactability(batch, uuid4())
    for n in list(range(49)) + [100]:
        cid, fact = records[n]
        await qualify(
            repo,
            governance_engine,
            cid,
            fact,
            plan.qualification_rule_id,
            "REJECTED_FIT",
        )
    fb = await repo.close_qualification(batch, uuid4())
    plan = DiscoveryPlan(
        qualification_rule_id=plan.qualification_rule_id, filters=(filters[2],)
    )
    batch = await repo.begin_batch(exp, 3, plan, uuid4(), fb)
    for n in range(200, 300):
        await candidate(repo, writer, exp, batch, n, supported=False)
    await repo.close_contactability(batch, uuid4())
    await repo.close_qualification(batch, uuid4())
    result = await repo.snapshot(exp)
    assert result.state == "QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3"
    assert (
        result.businesses_discovered == 300
        and result.batches_used == 3
        and result.accepted == 0
    )
    with pytest.raises(SupplyDenied):
        await candidate(repo, writer, exp, batch, 300, supported=False)


async def test_previously_dispatched_call_can_reconcile_after_target(governance_engine):
    from test_governance import observation, proof, reserve, seed

    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.supply.repository import SupplyAdmissionHook

    _, _, attr, config, _, _ = await seed(governance_engine, gate="SUPPLY")
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    records = [await candidate(repo, writer, exp, batch, n) for n in range(50)]
    await repo.close_contactability(batch, uuid4())
    await repo.bind_operation(attr, batch, "DEEP", config.id, records[0][0])
    governed = GovernanceRepository(
        governance_engine,
        clock=lambda: NOW,
        admission_hooks={"SUPPLY": SupplyAdmissionHook(repo)},
    )
    call = await reserve(governed, attr, config)
    dispatched = await governed.dispatch(call.call_id)
    assert dispatched.token is not None
    for cid, fact in records:
        await qualify(repo, governance_engine, cid, fact, plan.qualification_rule_id)
    assert (await repo.snapshot(exp)).state == "TARGET_50_REACHED"
    await governed.finish_attempt(call.call_id, token=dispatched.token, success=True)
    await governed.record_usage(call.call_id, (observation(),), token=dispatched.token)
    settled = await governed.reconcile(
        call.call_id,
        command_key=uuid4(),
        evidence_id=await proof(governed, call.call_id),
    )
    assert settled.state == "FINAL" and settled.accrued > 0


async def test_candidate_replay_and_foreign_feedback_cannot_reset_lineage(
    governance_engine,
):
    from alon_ai.supply import schema as s

    repo, writer, exp, plan, filters = await setup(governance_engine)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    cid, _ = await candidate(repo, writer, exp, batch, 0, supported=False)
    fb = await repo.close_contactability(batch, uuid4())
    async with governance_engine.connect() as c:
        original = (
            (await c.execute(select(s.candidates).where(s.candidates.c.id == cid)))
            .mappings()
            .one()
        )
    assert (
        await repo.admit_candidate(
            batch,
            original["identity_id"],
            original["clearance_id"],
            original["command_key"],
            observations=plan.filters,
        )
        == cid
    )
    new = DiscoveryPlan(
        qualification_rule_id=plan.qualification_rule_id, filters=(filters[1],)
    )
    second = await repo.begin_batch(exp, 2, new, uuid4(), fb)
    with pytest.raises(SupplyDenied):
        await repo.admit_candidate(
            second, original["identity_id"], original["clearance_id"], uuid4()
        )
    _, _, other, other_plan, other_filters = await setup(governance_engine)
    with pytest.raises(SupplyDenied):
        await repo.begin_batch(
            other,
            2,
            DiscoveryPlan(
                qualification_rule_id=other_plan.qualification_rule_id,
                filters=(other_filters[1],),
            ),
            uuid4(),
            fb,
        )
    for n in range(1, 51):
        await candidate(repo, writer, exp, second, n)
    await repo.close_contactability(second, uuid4())
    with pytest.raises(SupplyDenied):
        await repo.begin_batch(
            exp,
            3,
            DiscoveryPlan(
                qualification_rule_id=plan.qualification_rule_id, filters=(filters[2],)
            ),
            uuid4(),
            fb,
        )
    assert (await repo.snapshot(exp)).logical_slots == (1, 2)


async def test_expired_accepted_contact_cannot_hide_behind_fifty_fresh_supports(
    governance_engine,
):
    from test_governance import seed

    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import lock_experiment
    from alon_ai.supply.repository import SupplyAdmissionHook

    _, _, attr, config, _, _ = await seed(governance_engine, gate="SUPPLY")
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    short_expiry = NOW + timedelta(minutes=30)
    records = [
        await candidate(
            repo,
            writer,
            exp,
            batch,
            n,
            until=short_expiry if n == 0 else NOW + timedelta(hours=2),
        )
        for n in range(51)
    ]
    await repo.close_contactability(batch, uuid4())
    cid, fact = records[0]

    # Its qualification lasts two hours, but its accepted identity/contact lineage
    # expires after30minutes. The remaining50 support rows cannot replace it.
    async def long_qualification(kind, **kw):
        return await fact(kind, until=NOW + timedelta(hours=2), **kw)

    await qualify(
        repo, governance_engine, cid, long_qualification, plan.qualification_rule_id
    )
    with pytest.raises(SupplyDenied, match="DEADLINE_BOUND"):
        await repo.bind_operation(attr, batch, "DEEP", config.id, records[1][0])
    await repo.bind_operation(
        attr.model_copy(update={"deadline": short_expiry}),
        batch,
        "DEEP",
        config.id,
        records[1][0],
    )
    repo.clock = lambda: NOW + timedelta(minutes=31)
    snapshot = await repo.snapshot(exp)
    assert (
        snapshot.supported_emails == 50
        and snapshot.accepted == 1
        and snapshot.current_qualified_contactable == 0
    )
    # The binding exists, and this call has a later valid provider deadline.
    # Both phases must reject because the accepted lineage has gone stale.
    for phase in ("RESERVE", "DISPATCH"):
        async with governance_engine.begin() as c:
            await lock_experiment(c, exp)
            with pytest.raises(AccountingDenied, match="GATE"):
                await SupplyAdmissionHook(repo).admit(c, attr, uuid4(), phase)


@pytest.mark.parametrize(
    "kind,gate", [("CONTACT", "SUPPLY"), ("DISCOVERY", "CONTACT"), ("DEEP", "CONTACT")]
)
@pytest.mark.parametrize("writer_kind", ["SERVICE", "SQL"])
async def test_supply_work_kind_requires_exact_gate_owner(
    governance_engine, kind, gate, writer_kind
):
    from sqlalchemy.exc import DBAPIError
    from test_governance import seed

    from alon_ai.providers.contracts import Capability
    from alon_ai.supply import schema as s

    _, _, attr, config, _, _ = await seed(
        governance_engine,
        gate=gate,
        capability=Capability.FIRECRAWL_PAGE_CAPTURE
        if kind == "CONTACT"
        else Capability.BRAVE_WEB_COVERAGE,
    )
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    candidate_id = None
    if kind == "CONTACT":
        candidate_id, _ = await candidate(repo, writer, exp, batch, 0, supported=None)
    elif kind == "DEEP":
        records = [await candidate(repo, writer, exp, batch, n) for n in range(50)]
        candidate_id = records[0][0]
        await repo.close_contactability(batch, uuid4())
    if writer_kind == "SERVICE":
        with pytest.raises(SupplyDenied, match="WORK_GATE"):
            await repo.bind_operation(attr, batch, kind, config.id, candidate_id)
    else:
        async with governance_engine.begin() as c:
            with pytest.raises(DBAPIError):
                async with c.begin_nested():
                    await c.execute(
                        insert(s.operations).values(
                            operation_id=attr.operation_run_id,
                            experiment_id=exp,
                            workflow_id=attr.workflow_run_id,
                            config_id=config.id,
                            config_version=attr.config_version,
                            batch_id=batch,
                            candidate_id=candidate_id,
                            kind=kind,
                        )
                    )


async def test_standalone_supply_hook_cannot_admit_contact_owned_work(
    governance_engine,
):
    from test_governance import reserve, seed

    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.providers.contracts import Capability
    from alon_ai.supply.repository import SupplyAdmissionHook

    _, _, attr, config, _, _ = await seed(
        governance_engine, gate="CONTACT", capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    cid, _ = await candidate(repo, writer, exp, batch, 0, supported=None)
    await repo.bind_operation(attr, batch, "CONTACT", config.id, cid)
    governed = GovernanceRepository(
        governance_engine,
        clock=lambda: NOW,
        admission_hooks={"CONTACT": SupplyAdmissionHook(repo)},
    )
    with pytest.raises(AccountingDenied, match="GATE"):
        await reserve(governed, attr, config)


@pytest.mark.parametrize("denial_phase", [None, "RESERVE", "DISPATCH"])
async def test_contact_supply_composition_requires_owner_and_rolls_back_denial(
    governance_engine, denial_phase
):
    from sqlalchemy import text
    from test_governance import reserve, seed

    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.providers.contracts import Capability
    from alon_ai.supply import schema as s
    from alon_ai.supply.repository import ComposedContactSupplyHook

    _, _, attr, config, _, _ = await seed(
        governance_engine, gate="CONTACT", capability=Capability.FIRECRAWL_PAGE_CAPTURE
    )
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    cid, _ = await candidate(repo, writer, exp, batch, 0, supported=None)
    await repo.bind_operation(attr, batch, "CONTACT", config.id, cid)
    calls = []

    class ContactOwner:
        async def admit(self, connection, attribution, call_id, phase):
            assert attribution == attr
            # The required owner receives the actual governed SQL transaction.
            calls.append(
                (phase, await connection.scalar(text("SELECT pg_backend_pid()")))
            )
            if phase == denial_phase:
                await connection.execute(
                    update(s.candidates)
                    .where(s.candidates.c.id == cid)
                    .values(stopped=True)
                )
                raise ValueError("synthetic-private-owner-error")

    hook = ComposedContactSupplyHook(repo, contact_owner=ContactOwner())
    governed = GovernanceRepository(
        governance_engine, clock=lambda: NOW, admission_hooks={"CONTACT": hook}
    )
    if denial_phase == "RESERVE":
        with pytest.raises(AccountingDenied) as denied:
            await reserve(governed, attr, config)
        assert denied.value.__context__ is None
        assert "synthetic-private" not in str(denied.value)
    else:
        call = await reserve(governed, attr, config)
        if denial_phase == "DISPATCH":
            with pytest.raises(AccountingDenied) as denied:
                await governed.dispatch(call.call_id)
            assert denied.value.__context__ is None
            assert (await governed.get(call.call_id)).state == "RESERVED"
        else:
            assert (await governed.dispatch(call.call_id)).state == "DISPATCHED"
    assert [phase for phase, _ in calls] == (
        ["RESERVE"] if denial_phase == "RESERVE" else ["RESERVE", "DISPATCH"]
    )
    async with governance_engine.connect() as c:
        assert not (
            await c.execute(
                select(s.candidates.c.stopped).where(s.candidates.c.id == cid)
            )
        ).scalar_one()


def test_contact_supply_composition_cannot_omit_required_owner():
    from alon_ai.supply.repository import ComposedContactSupplyHook

    with pytest.raises(TypeError):
        ComposedContactSupplyHook(None)  # pyright: ignore[reportCallIssue,reportArgumentType]
    with pytest.raises(ValueError, match="contact admission owner required"):
        ComposedContactSupplyHook(None, contact_owner=None)  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize("kind,gate", [("CONTACT", "CONTACT"), ("DEEP", "SUPPLY")])
async def test_excluded_identity_replays_and_never_reaches_provider(
    governance_engine, kind, gate
):
    from test_governance import seed

    from alon_ai.accounting.models import AccountingDenied
    from alon_ai.accounting.repository import GovernanceRepository
    from alon_ai.providers.contracts import Capability, SafeRequestMetadata
    from alon_ai.providers.execution import GovernedExecutor
    from alon_ai.supply import schema as s
    from alon_ai.supply.repository import ComposedContactSupplyHook, SupplyAdmissionHook

    _, _, attr, config, _, _ = await seed(
        governance_engine,
        gate=gate,
        capability=Capability.FIRECRAWL_PAGE_CAPTURE
        if kind == "CONTACT"
        else Capability.BRAVE_WEB_COVERAGE,
    )
    repo, writer, exp, plan, _ = await setup(governance_engine, attr.experiment_id)
    batch = await repo.begin_batch(exp, 1, plan, uuid4())
    cid, _ = await candidate(
        repo, writer, exp, batch, 0, supported=None, clearance_kind="IDENTITY_EXCLUDED"
    )
    async with governance_engine.connect() as c:
        original = (
            (await c.execute(select(s.candidates).where(s.candidates.c.id == cid)))
            .mappings()
            .one()
        )
        assert (
            await c.execute(
                select(s.contacts.c.outcome).where(s.contacts.c.candidate_id == cid)
            )
        ).scalar_one() == "IDENTITY_EXCLUDED"
    assert (
        await repo.admit_candidate(
            batch,
            original["identity_id"],
            original["clearance_id"],
            original["command_key"],
            observations=plan.filters,
        )
        == cid
    )
    with pytest.raises(SupplyDenied, match="IDENTITY_EXCLUDED"):
        await repo.bind_operation(attr, batch, kind, config.id, cid)
    # Even a directly registered planned operation cannot bypass the runtime
    # exclusion fence; binding metadata itself does not grant paid access.
    async with governance_engine.begin() as c:
        await c.execute(
            insert(s.operations).values(
                operation_id=attr.operation_run_id,
                experiment_id=exp,
                workflow_id=attr.workflow_run_id,
                config_id=config.id,
                config_version=attr.config_version,
                batch_id=batch,
                candidate_id=cid,
                kind=kind,
            )
        )

    class ContactOwner:
        async def admit(self, connection, attribution, call_id, phase):
            return None

    class NoCall:
        calls = 0

        async def invoke(self, config, secret):
            self.calls += 1
            raise AssertionError("excluded identity reached provider")

    hook = (
        ComposedContactSupplyHook(repo, contact_owner=ContactOwner())
        if kind == "CONTACT"
        else SupplyAdmissionHook(repo)
    )
    governed = GovernanceRepository(
        governance_engine, clock=lambda: NOW, admission_hooks={gate: hook}
    )
    adapter = NoCall()
    executor = GovernedExecutor(governed, adapters={config.adapter_version: adapter})
    with pytest.raises(AccountingDenied, match="GATE"):
        await executor.execute(
            attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4()
        )
    assert adapter.calls == 0
    snapshot = await repo.snapshot(exp)
    assert (
        snapshot.businesses_discovered == 1
        and snapshot.supported_emails == 0
        and snapshot.accepted == 0
    )
