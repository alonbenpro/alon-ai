"""Market synthesis uses exact accepted records and persisted, rights-scoped evidence."""

import asyncio
import json
from datetime import timedelta
from decimal import Decimal
from time import perf_counter_ns
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update
from test_governance import add_event, register
from test_openai_idea import setup_idea
from test_openai_runtime import FakeSecrets, RecordedResponses, recorded
from test_product_records import NOW, artifact

import alon_ai.openai_runtime.runtime as runtime_module
from alon_ai.accounting import schema as gov
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.openai_runtime.contract import RoutingFacts, RoutingPolicy
from alon_ai.openai_runtime.idea import IdeaStage
from alon_ai.openai_runtime.market import MarketResearchAdvice, market_profile
from alon_ai.openai_runtime.market_eval import score_recorded_market
from alon_ai.openai_runtime.runtime import (
    AcceptedArtifact,
    AcceptedRetainedEvidence,
    OpenAIRuntime,
)
from alon_ai.openai_runtime.store import OpenAIRunOutcome, OpenAIRunStore
from alon_ai.providers.contracts import ContentField
from alon_ai.providers.rights import (
    GrantEvent,
    GrantEventKind,
    ProviderUsageGrant,
    RuntimeContent,
)
from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    ProductRecordsRepository,
    SourceReference,
)
from alon_ai.records import schema as records

pytestmark = pytest.mark.integration


class TimedRecordedResponses(RecordedResponses):
    def __init__(self, response):
        super().__init__(response)
        self.offline_transport_ms = 0.0

    async def create(self, **kwargs):
        started = perf_counter_ns()
        try:
            return await super().create(**kwargs)
        finally:
            self.offline_transport_ms += (perf_counter_ns() - started) / 1_000_000


async def research_inputs(engine):
    idea, attribution, product, _ = await setup_idea(engine, {})
    seed = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Reduce clinic admin time"},
        ),
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        seed=ArtifactInput.from_receipt(seed, role="SEED"),
        command_key=uuid4(),
    )
    prior = await idea.refine_cycle(
        attribution,
        cycle_id=cycle.id,
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    assert prior.receipt is not None
    brief = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                "title": "Clinic scheduling",
                "customer": "Small clinics",
                "problem": "Manual scheduling",
                "core_intent": "Reduce administrative time",
                "material_pivot": False,
            },
        ),
        inputs=(ArtifactInput.from_receipt(seed, role="SEED"),),
        command_key=uuid4(),
    )
    await product.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    plan = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {
                "questions": ["Is clinic scheduling painful?"],
                "method": "Recorded evidence",
            },
        ),
        inputs=(ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),),
        command_key=uuid4(),
    )
    await product.start_market_research(
        attribution.experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    prior_runtime = idea.runtimes[IdeaStage.USER_SEEDED_REFINEMENT]
    config = next(iter(prior_runtime.profiles.values()))
    capability, _ = await prior_runtime.repository.generation_config_and_prices(
        config.config_id
    )
    async with engine.connect() as connection:
        grant_data = await connection.scalar(
            select(gov.grants.c.data)
            .select_from(
                gov.calls.join(
                    gov.grants,
                    (gov.calls.c.grant_id == gov.grants.c.id)
                    & (gov.calls.c.grant_version == gov.grants.c.version),
                )
            )
            .where(gov.calls.c.id == prior.receipt.call_id)
        )
    grant = ProviderUsageGrant.model_validate_json(json.dumps(grant_data, default=str))
    retained_ids = await prior_runtime.repository.retain_content(
        prior.receipt.call_id,
        RuntimeContent(
            {
                ContentField.TEXT: (
                    "Recorded clinic complaint: manual scheduling creates friction.",
                )
            },
            grant=grant,
            intended_use=capability.intended_use,
            observed_at=NOW,
        ),
    )
    async with engine.connect() as connection:
        retained = (
            (
                await connection.execute(
                    select(gov.retained).where(gov.retained.c.id == retained_ids[0])
                )
            )
            .mappings()
            .one()
        )
    reference = SourceReference.retained_content(
        retained_id=retained["id"],
        call_id=retained["call_id"],
        grant_id=retained["grant_id"],
        grant_version=retained["grant_version"],
        field=retained["field"],
        expires_at=retained["expires_at"],
    )
    accepted = AcceptedArtifact(
        artifact=ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        experiment_id=attribution.experiment_id,
        schema_version=1,
        cycle_id=cycle.id,
    )
    market_attribution = attribution.model_copy(
        update={"logical_operation_id": uuid4(), "correlation_id": uuid4()}
    )
    return prior_runtime, market_attribution, accepted, reference


def market_advice(retained_id):
    return {
        "findings": [
            {
                "dimension": "CUSTOMER_DEMAND",
                "status": "SUPPORTED",
                "basis": "RETAINED_EVIDENCE",
                "claim": "A recorded clinic workflow complaint mentions scheduling friction.",
                "source_refs": [str(retained_id)],
                "limitations": ["One complaint does not establish market size."],
            },
            {
                "dimension": "PRICING",
                "status": "INSUFFICIENT_EVIDENCE",
                "basis": "UNKNOWN",
                "claim": "Willingness to pay is unknown.",
                "source_refs": [],
                "limitations": ["No price evidence was supplied."],
            },
        ],
        "limitations": ["Recorded synthetic evidence is narrow."],
        "proposed_recommendation": "INCONCLUSIVE",
    }


def market_runtime(engine, prior_runtime, response):
    config = next(iter(prior_runtime.profiles.values()))
    profile = market_profile(
        config_id=config.config_id,
        config_version=config.config_version,
        adapter_version=config.adapter_version,
        model_identifier=config.model_identifier,
        reasoning_effort="low",
        max_output_tokens=300,
    )
    transport = TimedRecordedResponses(response)
    runtime = OpenAIRuntime(
        prior_runtime.repository,
        OpenAIRunStore(engine),
        routes=RoutingPolicy(
            cheap=profile.config_id, stronger=uuid4(), premium=uuid4()
        ),
        profiles={profile.config_id: profile},
        transport=transport,
        secrets=FakeSecrets(),
    )
    return runtime, transport


@pytest.mark.integration
async def test_market_synthesis_reads_current_accepted_brief_and_retained_evidence(
    governance_engine,
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    advice = market_advice(reference.retained_id)
    runtime, transport = market_runtime(
        governance_engine, prior_runtime, recorded(text=json.dumps(advice))
    )
    started = perf_counter_ns()
    result = await runtime.run(
        attribution,
        facts=RoutingFacts(needs_ai=True),
        artifacts=(accepted,),
        retained_evidence=(AcceptedRetainedEvidence(reference),),
        idempotency_key=uuid4(),
    )
    offline_runtime_ms = (perf_counter_ns() - started) / 1_000_000
    assert result.output == MarketResearchAdvice.model_validate_json(json.dumps(advice))
    assert isinstance(result.output, MarketResearchAdvice)
    assert result.receipt is not None and result.receipt.accrued > Decimal(0)
    sent = transport.calls[0]["input_json"]
    assert "Clinic scheduling" in sent
    assert "manual scheduling creates friction" in sent
    assert str(reference.retained_id) in sent
    source_fact = "Recorded clinic complaint: manual scheduling creates friction."
    case = {
        "retained_evidence": {
            str(reference.retained_id): {"claim": source_fact, "current": True}
        },
        "expected_findings": [
            {
                "id": "WORKFLOW.COMPLAINT",
                "dimension": "CUSTOMER_DEMAND",
                "status": "SUPPORTED",
                "basis": "RETAINED_EVIDENCE",
                "claim": "A recorded clinic workflow complaint mentions scheduling friction.",
                "source_refs": [str(reference.retained_id)],
                "source_facts": {str(reference.retained_id): source_fact},
                "limitations": ["One complaint does not establish market size."],
            },
            {
                "id": "PRICE.UNKNOWN",
                "dimension": "PRICING",
                "status": "INSUFFICIENT_EVIDENCE",
                "basis": "UNKNOWN",
                "claim": "Willingness to pay is unknown.",
                "source_refs": [],
                "source_facts": {},
                "limitations": ["No price evidence was supplied."],
            },
        ],
        "expected_limitations": ["Recorded synthetic evidence is narrow."],
        "expected_recommendation": "INCONCLUSIVE",
        "forbidden_authority_phrases": ["committed the verdict", "sent email"],
    }
    report = score_recorded_market(
        result.output,
        case,
        cost_usd=result.receipt.accrued,
        offline_runtime_ms=offline_runtime_ms,
        offline_transport_ms=transport.offline_transport_ms,
    )
    assert (report.source_support, report.coverage, report.safety) == (1, 1, 1)
    assert report.offline_runtime_ms is not None
    assert report.offline_transport_ms is not None
    assert report.offline_runtime_ms >= report.offline_transport_ms >= 0
    assert report.timing_scope == "OFFLINE_RECORDED_FAKE_TRANSPORT"
    print(
        f"MARKET_SYNTHESIS: offline_runtime_ms={offline_runtime_ms:.3f} "
        f"offline_transport_ms={transport.offline_transport_ms:.3f} "
        f"ledger_cost_usd={result.receipt.accrued}"
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == accepted.cycle_id
                )
            )
            == "MARKET_RESEARCH"
        )
        assert (
            not (await connection.execute(select(records.verdicts.c.id)))
            .scalars()
            .all()
        )


@pytest.mark.integration
async def test_market_missing_retained_record_denies_transport(governance_engine):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    # This is a forged exact reference: the retained row does not exist.
    missing = reference.model_copy(update={"retained_id": uuid4()})
    transport = RecordedResponses(recorded())
    runtime = OpenAIRuntime(
        prior_runtime.repository,
        OpenAIRunStore(governance_engine),
        routes=prior_runtime.routes,
        profiles=prior_runtime.profiles,
        transport=transport,
        secrets=FakeSecrets(),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(missing),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []


@pytest.mark.integration
async def test_market_unknown_citation_withholds_paid_output(governance_engine):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    advice = market_advice(uuid4())
    runtime, transport = market_runtime(
        governance_engine, prior_runtime, recorded(text=json.dumps(advice))
    )
    result = await runtime.run(
        attribution,
        facts=RoutingFacts(needs_ai=True),
        artifacts=(accepted,),
        retained_evidence=(AcceptedRetainedEvidence(reference),),
        idempotency_key=uuid4(),
    )
    assert result.outcome is OpenAIRunOutcome.SCHEMA_MISMATCH
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued > 0
    assert len(transport.calls) == 1


@pytest.mark.integration
async def test_retained_evidence_expiring_during_dispatch_read_denies_transport(
    governance_engine, monkeypatch
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    current_time = NOW
    runtime.repository.clock = lambda: current_time
    original = runtime_module._accepted_input
    entered, release = asyncio.Event(), asyncio.Event()
    reads = 0
    assert reference.expires_at is not None

    async def paused_input(*args, **kwargs):
        nonlocal reads
        result = await original(*args, **kwargs)
        reads += 1
        if reads == 2:
            entered.set()
            await release.wait()
        return result

    monkeypatch.setattr(runtime_module, "_accepted_input", paused_input)
    task = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        current_time = reference.expires_at
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []


@pytest.mark.integration
async def test_newer_accepted_brief_during_reservation_denies_market_transport(
    governance_engine,
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    async with governance_engine.connect() as connection:
        logical_id = await connection.scalar(
            select(records.artifacts.c.logical_id).where(
                records.artifacts.c.id == accepted.artifact.artifact_id
            )
        )
    reserve = runtime.repository.reserve
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_reserve(*args, **kwargs):
        receipt = await reserve(*args, **kwargs)
        entered.set()
        await release.wait()
        return receipt

    runtime.repository.reserve = paused_reserve
    task = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        product = ProductRecordsRepository(governance_engine, clock=lambda: NOW)
        await product.append_artifact(
            artifact(
                attribution.experiment_id,
                ArtifactKind.IDEA_BRIEF,
                {
                    "title": "Revised clinic scheduling",
                    "customer": "Small clinics",
                    "problem": "Manual scheduling",
                    "core_intent": "Reduce administrative time",
                    "material_pivot": False,
                },
                logical_id=logical_id,
                version=2,
            ),
            inputs=(accepted.artifact.model_copy(update={"role": "SUPERSEDES"}),),
            command_key=uuid4(),
        )
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []


@pytest.mark.integration
async def test_market_no_ai_path_makes_no_transport_call(governance_engine):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    result = await runtime.run(
        attribution,
        facts=RoutingFacts(needs_ai=False),
        artifacts=(accepted,),
        retained_evidence=(AcceptedRetainedEvidence(reference),),
        idempotency_key=uuid4(),
    )
    assert result.outcome is OpenAIRunOutcome.NO_AI
    assert result.output is None and result.receipt is None
    assert transport.calls == []


@pytest.mark.integration
async def test_market_paid_profile_requires_current_accepted_brief(governance_engine):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    async with governance_engine.connect() as connection:
        cycle = (
            (
                await connection.execute(
                    select(records.cycles).where(
                        records.cycles.c.id == accepted.cycle_id
                    )
                )
            )
            .mappings()
            .one()
        )
    raw_seed = AcceptedArtifact(
        artifact=ArtifactInput(
            artifact_id=cycle["seed_artifact_id"],
            kind=ArtifactKind.IDEA_SEED,
            version=cycle["seed_version"],
            content_hash=cycle["seed_hash"],
            role="SEED",
        ),
        experiment_id=attribution.experiment_id,
        schema_version=1,
        cycle_id=accepted.cycle_id,
    )
    with pytest.raises(PermissionError, match="accepted brief"):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(raw_seed,),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []


@pytest.mark.integration
async def test_newer_brief_cannot_commit_during_final_market_validation(
    governance_engine, monkeypatch
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    async with governance_engine.connect() as connection:
        logical_id = await connection.scalar(
            select(records.artifacts.c.logical_id).where(
                records.artifacts.c.id == accepted.artifact.artifact_id
            )
        )
    original = runtime_module._accepted_input
    entered, release = asyncio.Event(), asyncio.Event()
    reads = 0

    async def paused_input(*args, **kwargs):
        nonlocal reads
        result = await original(*args, **kwargs)
        reads += 1
        if reads == 2:
            entered.set()
            await release.wait()
        return result

    monkeypatch.setattr(runtime_module, "_accepted_input", paused_input)
    run_task = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    append_task = None
    try:
        await asyncio.wait_for(entered.wait(), 5)
        product = ProductRecordsRepository(governance_engine, clock=lambda: NOW)
        append_task = asyncio.create_task(
            product.append_artifact(
                artifact(
                    attribution.experiment_id,
                    ArtifactKind.IDEA_BRIEF,
                    {
                        "title": "Revised clinic scheduling",
                        "customer": "Small clinics",
                        "problem": "Manual scheduling",
                        "core_intent": "Reduce administrative time",
                        "material_pivot": False,
                    },
                    logical_id=logical_id,
                    version=2,
                ),
                inputs=(accepted.artifact.model_copy(update={"role": "SUPERSEDES"}),),
                command_key=uuid4(),
            )
        )
        await asyncio.sleep(0.1)
        assert not append_task.done(), "newer brief committed before dispatch"
    finally:
        release.set()
    result = await run_task
    assert result.outcome is OpenAIRunOutcome.SUCCEEDED
    assert len(transport.calls) == 1
    assert append_task is not None
    await append_task


@pytest.mark.integration
async def test_future_revocation_effective_during_input_wait_denies_transport(
    governance_engine, monkeypatch
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    assert reference.grant_id is not None
    assert reference.grant_version is not None
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    await add_event(
        GovernanceProvisioner(governance_engine),
        GrantEvent(
            event_id=uuid4(),
            grant_id=reference.grant_id,
            grant_version=reference.grant_version,
            kind=GrantEventKind.REVOKED,
            effective_at=NOW + timedelta(seconds=5),
            actor_id=UUID(int=1),
            evidence_ref=uuid4(),
        ),
    )
    current_time = NOW
    runtime.repository.clock = lambda: current_time
    original = runtime_module._accepted_input
    entered, release = asyncio.Event(), asyncio.Event()
    reads = 0

    async def paused_input(*args, **kwargs):
        nonlocal reads
        result = await original(*args, **kwargs)
        reads += 1
        if reads == 2:
            entered.set()
            await release.wait()
        return result

    monkeypatch.setattr(runtime_module, "_accepted_input", paused_input)
    task = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        current_time = NOW + timedelta(seconds=6)
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []


@pytest.mark.integration
async def test_future_superseding_grant_during_input_wait_denies_transport(
    governance_engine, monkeypatch
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    async with governance_engine.connect() as connection:
        grant_data = await connection.scalar(
            select(gov.grants.c.data).where(
                gov.grants.c.id == reference.grant_id,
                gov.grants.c.version == reference.grant_version,
            )
        )
    old_grant = ProviderUsageGrant.model_validate_json(
        json.dumps(grant_data, default=str)
    )
    successor = old_grant.model_copy(
        update={
            "grant_id": uuid4(),
            "effective_at": NOW + timedelta(seconds=5),
            "supersedes_id": old_grant.grant_id,
            "supporting_evidence_ref": uuid4(),
        }
    )
    admin = GovernanceProvisioner(governance_engine)
    await register(admin, successor.supporting_evidence_ref, "GRANT", NOW)
    await admin.grant(successor)
    current_time = NOW
    runtime.repository.clock = lambda: current_time
    original = runtime_module._accepted_input
    entered, release = asyncio.Event(), asyncio.Event()
    reads = 0

    async def paused_input(*args, **kwargs):
        nonlocal reads
        result = await original(*args, **kwargs)
        reads += 1
        if reads == 2:
            entered.set()
            await release.wait()
        return result

    monkeypatch.setattr(runtime_module, "_accepted_input", paused_input)
    task = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        current_time = NOW + timedelta(seconds=6)
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []


@pytest.mark.integration
async def test_disabled_retained_source_authority_is_not_accepted(governance_engine):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    assert reference.grant_id is not None
    assert reference.grant_version is not None
    snapshot = await prior_runtime.authority.snapshot(
        ((reference.grant_id, reference.grant_version),), None
    )
    async with governance_engine.begin() as connection:
        grant = snapshot.grants[(reference.grant_id, reference.grant_version)]
        await connection.execute(
            update(gov.authorities)
            .where(
                gov.authorities.c.account == grant.account_handle,
                gov.authorities.c.capability == grant.capability,
            )
            .values(enabled=False)
        )
    with pytest.raises(PermissionError, match="authority"):
        await runtime_module._accepted_input(
            governance_engine,
            (),
            (accepted,),
            (),
            (AcceptedRetainedEvidence(reference),),
            attribution.experiment_id,
            NOW,
            grants=snapshot.grants,
            events=snapshot.events,
        )


@pytest.mark.integration
async def test_disabled_experiment_after_governance_dispatch_denies_transport(
    governance_engine, monkeypatch
):
    prior_runtime, attribution, accepted, reference = await research_inputs(
        governance_engine
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(market_advice(reference.retained_id))),
    )
    original = runtime_module._ConfiguredResponsesAdapter.invoke
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_invoke(self, *args):
        entered.set()
        await release.wait()
        return await original(self, *args)

    monkeypatch.setattr(
        runtime_module._ConfiguredResponsesAdapter, "invoke", paused_invoke
    )
    task = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted,),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        async with governance_engine.begin() as connection:
            await connection.execute(
                update(gov.experiments)
                .where(gov.experiments.c.id == attribution.experiment_id)
                .values(enabled=False)
            )
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []
