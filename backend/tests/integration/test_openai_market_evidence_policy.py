"""Recorded governed research evidence for advisory Market synthesis.

Provider responses and model responses are synthetic offline fixtures. These
tests exercise persisted grant, call, retention, plan, and citation identity;
they do not establish live provider timing or real market claim validity.
"""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from test_governance import add_event, register
from test_openai_idea import setup_idea
from test_openai_runtime import FakeSecrets, RecordedResponses, recorded
from test_product_records import NOW, artifact

import alon_ai.openai_runtime.runtime as runtime_module
from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import (
    CapabilityConfig,
    ControlPolicy,
    FxVersion,
    PriceBound,
    PriceVersion,
)
from alon_ai.accounting.repository import GovernanceProvisioner, GovernanceRepository
from alon_ai.openai_runtime.contract import RoutingFacts, RoutingPolicy
from alon_ai.openai_runtime.idea import IdeaStage
from alon_ai.openai_runtime.market import MarketResearchAdvice, market_profile
from alon_ai.openai_runtime.runtime import (
    AcceptedArtifact,
    AcceptedRetainedEvidence,
    OpenAIRuntime,
)
from alon_ai.openai_runtime.store import OpenAIRunOutcome, OpenAIRunStore
from alon_ai.providers.contracts import (
    CAPABILITIES,
    BraveSearchRequest,
    CalendarReadRequest,
    Capability,
    ContentField,
    EmailVerificationRequest,
    FirecrawlCaptureRequest,
    FirecrawlMapRequest,
    MailboxReadRequest,
    OperationRunKind,
    Purpose,
    SafeRequestMetadata,
    UsageComponent,
)
from alon_ai.providers.execution import GovernedExecutor
from alon_ai.providers.fakes import (
    FakeBraveProvider,
    FakeCalendarProvider,
    FakeEmailVerificationProvider,
    FakeFirecrawlProvider,
    FakeGmailProvider,
    FakeSession,
)
from alon_ai.providers.rights import (
    GrantEvent,
    GrantEventKind,
    IntendedUse,
    ProviderUsageGrant,
)
from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    ProductRecordsRepository,
    SourceReference,
)
from alon_ai.records import schema as records

pytestmark = pytest.mark.integration


class RecordedProviderAdapter:
    def __init__(self, capability, session):
        self.capability = capability
        self.session = session

    async def invoke(self, config, secret):
        assert config.intended_use.capability is self.capability
        assert secret is None
        cap = self.capability
        if cap is Capability.BRAVE_WEB_COVERAGE:
            return await FakeBraveProvider(self.session).search(
                BraveSearchRequest(capability=cap, query=SecretStr("clinic scheduling"))
            )
        if cap is Capability.FIRECRAWL_MAP:
            return await FakeFirecrawlProvider(self.session).map(
                FirecrawlMapRequest(url="https://example.test/clinics")
            )
        if cap is Capability.FIRECRAWL_PAGE_CAPTURE:
            return await FakeFirecrawlProvider(self.session).capture(
                FirecrawlCaptureRequest(url="https://example.test/clinics")
            )
        if cap is Capability.GMAIL_READ:
            return await FakeGmailProvider(self.session).read(
                MailboxReadRequest(mailbox_id=uuid4())
            )
        if cap is Capability.GOOGLE_CALENDAR_READ:
            return await FakeCalendarProvider(self.session).read(
                CalendarReadRequest(
                    calendar_id=uuid4(), starts_at=NOW, ends_at=NOW + timedelta(hours=1)
                )
            )
        if cap is Capability.HUNTER_EMAIL_VERIFICATION:
            return await FakeEmailVerificationProvider(self.session).verify(
                EmailVerificationRequest(
                    business_id=uuid4(),
                    email_candidate_id=uuid4(),
                    source_evidence_ref=uuid4(),
                    business_match_ref=uuid4(),
                    address=SecretStr("synthetic@example.test"),
                )
            )
        raise AssertionError(f"unhandled fixture capability: {cap}")


async def accepted_research_inputs(engine, *, plan_source_capability=None):
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
    plan_sources = ()
    if plan_source_capability is not None:
        direct_reference, _ = await governed_retained_source(
            engine,
            attribution,
            None,
            plan_source_capability,
            link_evidence=False,
        )
        plan_sources = (direct_reference,)
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
        sources=plan_sources,
        command_key=uuid4(),
    )
    attempt = await product.start_market_research(
        attribution.experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    accepted_brief = AcceptedArtifact(
        artifact=ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        experiment_id=attribution.experiment_id,
        schema_version=1,
        cycle_id=cycle.id,
    )
    accepted_plan = AcceptedArtifact(
        artifact=ArtifactInput.from_receipt(plan, role="PLAN"),
        experiment_id=attribution.experiment_id,
        schema_version=1,
        cycle_id=cycle.id,
        attempt_id=attempt.id,
    )
    prior_runtime = idea.runtimes[IdeaStage.USER_SEEDED_REFINEMENT]
    market_attribution = attribution.model_copy(
        update={"logical_operation_id": uuid4(), "correlation_id": uuid4()}
    )
    return prior_runtime, market_attribution, accepted_brief, accepted_plan


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
    transport = RecordedResponses(response)
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


async def governed_retained_source(
    engine,
    attribution,
    accepted_plan,
    capability,
    *,
    link_evidence=True,
    retained_field=None,
):
    """Produce real persisted evidence through governance and a fake provider."""
    admin = GovernanceProvisioner(engine)
    source_attr = attribution.model_copy(
        update={
            "operation_run_id": uuid4(),
            "logical_operation_id": uuid4(),
            "correlation_id": uuid4(),
            "config_version": uuid4(),
            "operation_run_kind": OperationRunKind.RESEARCH,
        }
    )
    await admin.scope(source_attr)
    purpose = {
        Capability.GMAIL_READ: Purpose.MAILBOX_READ,
        Capability.GOOGLE_CALENDAR_READ: Purpose.CALENDAR_READ,
        Capability.HUNTER_EMAIL_VERIFICATION: Purpose.EMAIL_VERIFICATION,
    }.get(capability, Purpose.RESEARCH)
    field = retained_field or (
        ContentField.URL
        if capability is Capability.FIRECRAWL_MAP
        else ContentField.TEXT
    )
    use = IntendedUse(
        provider=CAPABILITIES[capability].provider,
        account_handle="synthetic-research",
        capability=capability,
        plan_identifier="synthetic-plan",
        order_form_ref="synthetic-order",
        terms_version="synthetic-v1",
        purpose=purpose,
        required_fields=frozenset({field}),
    )
    policy = ControlPolicy(
        id=uuid4(),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        evidence_id=uuid4(),
        capability=capability,
        account_handle=use.account_handle,
        timeout_seconds=5,
        quota_limit=10,
        window_seconds=60,
        concurrency_limit=2,
        failure_threshold=2,
        failure_window_seconds=60,
        cooldown_seconds=10,
    )
    await register(admin, policy.evidence_id, "CONTROL", NOW)
    await admin.policy(policy)
    grant = ProviderUsageGrant(
        grant_id=uuid4(),
        version=1,
        **use.model_dump(exclude={"schema_version", "required_fields"}),
        outbound_use_permitted=False,
        storage_fields=use.required_fields,
        retention_rule_id=uuid4(),
        retention_seconds=60,
        approved_by=UUID(int=1),
        approved_at=NOW - timedelta(days=2),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        supporting_evidence_ref=uuid4(),
    )
    await register(admin, grant.supporting_evidence_ref, "GRANT", NOW)
    await admin.grant(grant)
    price = PriceVersion(
        id=uuid4(),
        capability=capability,
        component=(
            UsageComponent.VERIFICATION
            if capability is Capability.HUNTER_EMAIL_VERIFICATION
            else UsageComponent.REQUEST
        ),
        currency="USD",
        unit_price=Decimal(0),
        unit_quantity=Decimal(1),
        currency_quantum=Decimal(".01"),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        evidence_id=uuid4(),
    )
    fx = FxVersion(
        id=uuid4(),
        currency="USD",
        rate=Decimal("3.5"),
        effective_at=price.effective_at,
        expires_at=price.expires_at,
        evidence_id=uuid4(),
    )
    await register(admin, price.evidence_id, "PRICE", NOW)
    await admin.price(price)
    await register(admin, fx.evidence_id, "FX", NOW)
    await admin.fx(fx)
    config = CapabilityConfig(
        id=uuid4(),
        version=source_attr.config_version,
        workflow_id=source_attr.workflow_run_id,
        intended_use=use,
        prices=(PriceBound(price_id=price.id, max_quantity=Decimal(1)),),
        fx_id=fx.id,
        requested_count=1,
        adapter_version=uuid4(),
    )
    await admin.config(config)
    await admin.budgets(
        source_attr,
        provider=use.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(100),
        effective_at=price.effective_at,
        expires_at=price.expires_at,
    )
    repo = GovernanceRepository(engine, clock=lambda: NOW)
    session = FakeSession(
        grants={capability: grant},
        intended_uses={capability: use},
        clock=lambda: NOW,
    )
    result = await GovernedExecutor(
        repo,
        adapters={config.adapter_version: RecordedProviderAdapter(capability, session)},
    ).execute(
        source_attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4()
    )
    assert result.content is not None
    assert result.receipt.accrued == 0
    assert tuple(item.capability for item in session.invocations) == (capability,)
    retained_ids = await repo.retain_content(result.receipt.call_id, result.content)
    assert len(retained_ids) == 1
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
    if link_evidence:
        evidence = await ProductRecordsRepository(
            engine, clock=lambda: NOW
        ).append_artifact(
            artifact(
                attribution.experiment_id,
                ArtifactKind.RESEARCH_EVIDENCE,
                {
                    "claim": "Synthetic recorded source only",
                    "finding": "Fixture observation",
                },
            ),
            inputs=(accepted_plan.artifact,),
            sources=(reference,),
            command_key=uuid4(),
        )
        assert evidence.artifact_id is not None
    return reference, grant


async def governed_market_inputs(
    engine, capability=Capability.BRAVE_WEB_COVERAGE, *, retained_field=None
):
    (
        prior_runtime,
        attribution,
        accepted_brief,
        accepted_plan,
    ) = await accepted_research_inputs(engine)
    reference, grant = await governed_retained_source(
        engine, attribution, accepted_plan, capability, retained_field=retained_field
    )
    return prior_runtime, attribution, (accepted_brief, accepted_plan), reference, grant


async def call_snapshot(engine):
    async with engine.connect() as connection:
        return tuple(
            (await connection.execute(select(gov.calls.c.id, gov.calls.c.accrued)))
            .tuples()
            .all()
        )


def advice_for(reference, capability=Capability.BRAVE_WEB_COVERAGE):
    source_fact = {
        Capability.BRAVE_WEB_COVERAGE: "Synthetic search coverage",
        Capability.FIRECRAWL_MAP: "https://example.test/about",
        Capability.FIRECRAWL_PAGE_CAPTURE: "Synthetic deterministic page capture",
    }.get(capability, "Synthetic recorded provider content")
    return {
        "findings": [
            {
                "dimension": "CUSTOMER_DEMAND",
                "status": "SUPPORTED",
                "basis": "RETAINED_EVIDENCE",
                "claim": f"The recorded source says {source_fact}.",
                "source_refs": [str(reference.retained_id)],
                "limitations": [
                    "This offline fixture does not establish market demand."
                ],
            }
        ],
        "limitations": ["Only synthetic recorded evidence was used."],
        "proposed_recommendation": "INCONCLUSIVE",
    }


@pytest.mark.parametrize(
    "capability",
    [
        Capability.BRAVE_WEB_COVERAGE,
        Capability.FIRECRAWL_MAP,
        Capability.FIRECRAWL_PAGE_CAPTURE,
    ],
)
async def test_current_governed_research_evidence_is_advisory_and_exactly_cited(
    governance_engine, capability
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, capability
    )
    advice = advice_for(reference, capability)
    runtime, transport = market_runtime(
        governance_engine, prior_runtime, recorded(text=json.dumps(advice))
    )
    result = await runtime.run(
        attribution,
        facts=RoutingFacts(needs_ai=True),
        artifacts=artifacts,
        retained_evidence=(AcceptedRetainedEvidence(reference),),
        idempotency_key=uuid4(),
    )
    assert result.outcome is OpenAIRunOutcome.SUCCEEDED
    assert result.output == MarketResearchAdvice.model_validate_json(json.dumps(advice))
    assert result.receipt is not None and result.receipt.accrued > 0
    assert len(transport.calls) == 1
    assert str(reference.retained_id) in transport.calls[0]["input_json"]
    expected_source = {
        Capability.BRAVE_WEB_COVERAGE: "Synthetic search coverage",
        Capability.FIRECRAWL_MAP: "https://example.test/about",
        Capability.FIRECRAWL_PAGE_CAPTURE: "Synthetic deterministic page capture",
    }[capability]
    assert expected_source in transport.calls[0]["input_json"]
    assert str(artifacts[1].artifact.artifact_id) in transport.calls[0]["input_json"]
    async with governance_engine.connect() as connection:
        assert (
            not (await connection.execute(select(records.verdicts.c.id)))
            .scalars()
            .all()
        )
        state = await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == artifacts[0].cycle_id
            )
        )
    assert state == "MARKET_RESEARCH"


@pytest.mark.parametrize(
    "capability",
    [
        Capability.GMAIL_READ,
        Capability.GOOGLE_CALENDAR_READ,
        Capability.HUNTER_EMAIL_VERIFICATION,
    ],
)
async def test_valid_same_experiment_nonresearch_evidence_is_denied_before_paid_reservation(
    governance_engine, capability
):
    (
        prior_runtime,
        attribution,
        artifacts,
        reference,
        grant,
    ) = await governed_market_inputs(governance_engine, capability)
    assert grant.purpose is not Purpose.RESEARCH
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_firecrawl_map_text_is_denied_by_research_field_policy(
    governance_engine,
):
    (
        prior_runtime,
        attribution,
        artifacts,
        reference,
        grant,
    ) = await governed_market_inputs(
        governance_engine,
        Capability.FIRECRAWL_MAP,
        retained_field=ContentField.TEXT,
    )
    assert grant.purpose is Purpose.RESEARCH
    assert reference.field == ContentField.TEXT.value
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference, Capability.FIRECRAWL_MAP))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_plan_attempt_binding_rejects_stale_attempt_before_paid_reservation(
    governance_engine,
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, Capability.BRAVE_WEB_COVERAGE
    )
    stale_plan = replace(artifacts[1], attempt_id=uuid4())
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(artifacts[0], stale_plan),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_plan_newer_logical_version_rejects_stale_plan_before_paid_reservation(
    governance_engine,
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, Capability.BRAVE_WEB_COVERAGE
    )
    async with governance_engine.connect() as connection:
        logical_id = await connection.scalar(
            select(records.artifacts.c.logical_id).where(
                records.artifacts.c.id == artifacts[1].artifact.artifact_id
            )
        )
    await ProductRecordsRepository(
        governance_engine, clock=lambda: NOW
    ).append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {
                "questions": ["Revised clinic demand question"],
                "method": "Recorded evidence",
            },
            logical_id=logical_id,
            version=2,
        ),
        inputs=(artifacts[1].artifact.model_copy(update={"role": "SUPERSEDES"}),),
        command_key=uuid4(),
    )
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_research_evidence_must_be_linked_to_the_current_accepted_plan(
    governance_engine,
):
    (
        prior_runtime,
        attribution,
        accepted_brief,
        accepted_plan,
    ) = await accepted_research_inputs(governance_engine)
    other_plan = await ProductRecordsRepository(
        governance_engine, clock=lambda: NOW
    ).append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {"questions": ["Unaccepted question"], "method": "Recorded evidence"},
        ),
        inputs=(accepted_brief.artifact,),
        command_key=uuid4(),
    )
    wrong_link = replace(
        accepted_plan, artifact=ArtifactInput.from_receipt(other_plan, role="PLAN")
    )
    reference, _ = await governed_retained_source(
        governance_engine, attribution, wrong_link, Capability.BRAVE_WEB_COVERAGE
    )
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted_brief, accepted_plan),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_model_citation_cannot_use_a_different_retained_identity(
    governance_engine,
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, Capability.FIRECRAWL_PAGE_CAPTURE
    )
    advice = advice_for(reference, Capability.FIRECRAWL_PAGE_CAPTURE)
    advice["findings"][0]["source_refs"] = [str(uuid4())]
    runtime, transport = market_runtime(
        governance_engine, prior_runtime, recorded(text=json.dumps(advice))
    )
    result = await runtime.run(
        attribution,
        facts=RoutingFacts(needs_ai=True),
        artifacts=artifacts,
        retained_evidence=(AcceptedRetainedEvidence(reference),),
        idempotency_key=uuid4(),
    )
    assert result.outcome is OpenAIRunOutcome.SCHEMA_MISMATCH
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued > 0
    assert len(transport.calls) == 1


@pytest.mark.parametrize("change", ["expiry", "revocation"])
async def test_research_grant_becoming_ineligible_during_dispatch_wait_has_no_model_cost(
    governance_engine, monkeypatch, change
):
    (
        prior_runtime,
        attribution,
        artifacts,
        reference,
        grant,
    ) = await governed_market_inputs(governance_engine, Capability.BRAVE_WEB_COVERAGE)
    if change == "revocation":
        await add_event(
            GovernanceProvisioner(governance_engine),
            GrantEvent(
                event_id=uuid4(),
                grant_id=grant.grant_id,
                grant_version=grant.version,
                kind=GrantEventKind.REVOKED,
                effective_at=NOW + timedelta(seconds=5),
                actor_id=UUID(int=1),
                evidence_ref=uuid4(),
            ),
        )
    assert reference.expires_at is not None
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
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
    run = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        current_time = (
            reference.expires_at if change == "expiry" else NOW + timedelta(seconds=6)
        )
    finally:
        release.set()
    result = await run
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []


async def test_plan_newer_logical_version_during_reservation_blocks_dispatch(
    governance_engine,
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, Capability.BRAVE_WEB_COVERAGE
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    async with governance_engine.connect() as connection:
        logical_id = await connection.scalar(
            select(records.artifacts.c.logical_id).where(
                records.artifacts.c.id == artifacts[1].artifact.artifact_id
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
    run = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        await ProductRecordsRepository(
            governance_engine, clock=lambda: NOW
        ).append_artifact(
            artifact(
                attribution.experiment_id,
                ArtifactKind.RESEARCH_PLAN,
                {
                    "questions": ["Revised clinic demand question"],
                    "method": "Recorded evidence",
                },
                logical_id=logical_id,
                version=2,
            ),
            inputs=(artifacts[1].artifact.model_copy(update={"role": "SUPERSEDES"}),),
            command_key=uuid4(),
        )
    finally:
        release.set()
    result = await run
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []


async def test_real_retained_source_without_research_evidence_link_is_denied(
    governance_engine,
):
    (
        prior_runtime,
        attribution,
        accepted_brief,
        accepted_plan,
    ) = await accepted_research_inputs(governance_engine)
    reference, _ = await governed_retained_source(
        governance_engine,
        attribution,
        accepted_plan,
        Capability.BRAVE_WEB_COVERAGE,
        link_evidence=False,
    )
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted_brief, accepted_plan),
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_forged_retained_field_cannot_match_plan_linked_source_identity(
    governance_engine,
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, Capability.BRAVE_WEB_COVERAGE
    )
    forged = reference.model_copy(update={"field": ContentField.URL.value})
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(forged),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


async def test_accepted_plan_cannot_carry_direct_retained_gmail_source(
    governance_engine,
):
    (
        prior_runtime,
        attribution,
        accepted_brief,
        accepted_plan,
    ) = await accepted_research_inputs(
        governance_engine, plan_source_capability=Capability.GMAIL_READ
    )
    async with governance_engine.connect() as connection:
        direct_source = (
            (
                await connection.execute(
                    select(records.source_refs).where(
                        records.source_refs.c.artifact_id
                        == accepted_plan.artifact.artifact_id
                    )
                )
            )
            .mappings()
            .one()
        )
    assert direct_source["kind"] == "RETAINED_CONTENT"
    assert direct_source["retained_id"] is not None
    before = await call_snapshot(governance_engine)
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(
            text=json.dumps(
                advice_for(
                    SourceReference.retained_content(
                        retained_id=direct_source["retained_id"],
                        call_id=direct_source["call_id"],
                        grant_id=direct_source["grant_id"],
                        grant_version=direct_source["grant_version"],
                        field=direct_source["field"],
                        expires_at=direct_source["expires_at"],
                    )
                )
            )
        ),
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=(accepted_brief, accepted_plan),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []
    assert await call_snapshot(governance_engine) == before


@pytest.mark.parametrize("change", ["superseded", "newer_version"])
async def test_evidence_becoming_noncurrent_during_reservation_blocks_dispatch(
    governance_engine, change
):
    prior_runtime, attribution, artifacts, reference, _ = await governed_market_inputs(
        governance_engine, Capability.BRAVE_WEB_COVERAGE
    )
    async with governance_engine.connect() as connection:
        evidence = (
            (
                await connection.execute(
                    select(records.artifacts)
                    .select_from(
                        records.artifacts.join(
                            records.source_refs,
                            records.source_refs.c.artifact_id == records.artifacts.c.id,
                        )
                    )
                    .where(records.source_refs.c.retained_id == reference.retained_id)
                )
            )
            .mappings()
            .one()
        )
    evidence_ref = ArtifactInput(
        artifact_id=evidence["id"],
        kind=ArtifactKind.RESEARCH_EVIDENCE,
        version=evidence["version"],
        content_hash=evidence["content_hash"],
        role="TARGET",
    )
    runtime, transport = market_runtime(
        governance_engine,
        prior_runtime,
        recorded(text=json.dumps(advice_for(reference))),
    )
    reserve = runtime.repository.reserve
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_reserve(*args, **kwargs):
        receipt = await reserve(*args, **kwargs)
        entered.set()
        await release.wait()
        return receipt

    runtime.repository.reserve = paused_reserve
    run = asyncio.create_task(
        runtime.run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            artifacts=artifacts,
            retained_evidence=(AcceptedRetainedEvidence(reference),),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        product = ProductRecordsRepository(governance_engine, clock=lambda: NOW)
        if change == "superseded":
            await product.record_disposition(
                evidence_ref,
                experiment_id=attribution.experiment_id,
                disposition="SUPERSEDED",
                decided_by=UUID(int=1),
                command_key=uuid4(),
            )
        else:
            await product.append_artifact(
                artifact(
                    attribution.experiment_id,
                    ArtifactKind.RESEARCH_EVIDENCE,
                    {
                        "claim": "Revised synthetic record",
                        "finding": "Prior source is no longer selected",
                    },
                    logical_id=evidence["logical_id"],
                    version=evidence["version"] + 1,
                ),
                inputs=(evidence_ref.model_copy(update={"role": "SUPERSEDES"}),),
                command_key=uuid4(),
            )
    finally:
        release.set()
    result = await run
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transport.calls == []
