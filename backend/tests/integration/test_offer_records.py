"""Offer persistence stays bound to accepted research and operator constraints."""

from decimal import Decimal
from typing import Literal, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from test_product_record_guards import cycle_fixture, put
from test_product_records import NOW, register_test_operator

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import EvidenceRecord
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    CommercialConstraints,
    DeliveryConstraints,
    OperatorCapabilityProfile,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductRecordsRepository,
    ProductWorkflow,
    SourceReference,
)
from alon_ai.records import offer_schema as offers
from alon_ai.records import schema as records
from alon_ai.records.offer_models import (
    INITIAL_OUTREACH_POLICY,
    OFFER_FIELD_EVIDENCE_ROLES,
    OPERATOR_FIELD_CONSTRAINTS,
    PROTECTED_OFFER_FIELDS,
    REQUIRED_QUALIFICATION_CATEGORIES,
    CommercialEnvelopeRequest,
    OfferAcceptanceRequest,
    OfferFieldSource,
    OfferGapRequest,
    QualificationCriterion,
)
from alon_ai.records.offers import OfferRecordsRepository

pytestmark = pytest.mark.integration

OperatorConstraint = Literal[
    "CURRENCY",
    "DELIVERY_CAPACITY",
    "HOURLY_COST",
    "MINIMUM_PRICE",
    "MINIMUM_MARGIN_RATE",
    "MAXIMUM_DISCOUNT_RATE",
    "MINIMUM_DEPOSIT_RATE",
]


RESEARCH_ROLES = (
    "CUSTOMER_EVIDENCE",
    "BUYER_EVIDENCE",
    "PROBLEM_EVIDENCE",
    "ALTERNATIVES",
    "OBJECTIONS",
    "DIFFERENTIATION",
    "REACHABILITY",
    "FEASIBILITY",
    "INTEGRATION",
    "TRUST_COMPLIANCE",
    "CONTRADICTIONS_UNCERTAINTIES",
)


async def complete_research(
    engine, *, currency="ILS", margin_override=None, scope_hours="60"
):
    if margin_override is None:
        repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(engine)
    else:
        repo, experiment_id, cycle, idea, plan = await offer_cycle_fixture(
            engine, margin_override
        )
    proof_id = uuid4()
    await GovernanceProvisioner(engine).evidence(
        EvidenceRecord(
            id=proof_id,
            kind="CONTROL",
            mode="SYNTHETIC",
            registered_by=UUID(int=1),
            registered_at=NOW,
        )
    )
    source = SourceReference.governance_evidence(proof_id)
    attempt = await repo.start_research_attempt(
        cycle.id, ArtifactInput.from_receipt(plan, role="PLAN"), command_key=uuid4()
    )
    evidence = []
    for role in RESEARCH_ROLES:
        receipt = await put(
            repo,
            experiment_id,
            ArtifactKind.RESEARCH_EVIDENCE,
            {"claim": role, "finding": f"Supported {role.lower()}"},
            sources=(source,),
        )
        evidence.append(ArtifactInput.from_receipt(receipt, role=role))
    competitor = await put(
        repo,
        experiment_id,
        ArtifactKind.COMPETITOR_PROFILE,
        {"name": "Competitor", "positioning": "Manual alternative"},
        sources=(source,),
    )
    service = await put(
        repo,
        experiment_id,
        ArtifactKind.SERVICE_PROFILE,
        {"name": "Implementation", "scope": "Sixty-hour delivery"},
        sources=(source,),
    )
    price = await put(
        repo,
        experiment_id,
        ArtifactKind.PRICE_OBSERVATION,
        {
            "status": "QUOTED",
            "currency": currency,
            "amount": "12000",
            "unit": "project",
            "source_note": "Published project quote",
        },
        sources=(source,),
    )
    scope = await put(
        repo,
        experiment_id,
        ArtifactKind.DELIVERY_SCOPE_ESTIMATE,
        {"hours": scope_hours, "basis": "Observed implementation scope"},
        sources=(source,),
    )
    inputs = [ArtifactInput.from_receipt(plan, role="PLAN"), *evidence]
    inputs.extend(
        (
            ArtifactInput.from_receipt(competitor, role="COMPETITOR_PROFILE"),
            ArtifactInput.from_receipt(service, role="SERVICE_PROFILE"),
            ArtifactInput.from_receipt(price, role="PRICE_OBSERVATION"),
            ArtifactInput.from_receipt(scope, role="SCOPE_ESTIMATE"),
        )
    )
    report = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "Complete offer research", "limitations": ["Synthetic"]},
        inputs=inputs,
    )
    recommendation = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {
            "recommendation": "PROCEED_TO_OFFER",
            "rationale": "All required categories have exact evidence",
        },
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
    )
    verdict = await repo.commit_verdict(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="PROCEED_TO_OFFER",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    return repo, experiment_id, cycle, idea, verdict, report, recommendation, inputs


async def offer_cycle_fixture(engine, margin):
    experiment_id, workflow_id, agent_id, profile_id = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    await register_test_operator(engine)
    async with engine.begin() as connection:
        await connection.execute(gov.experiments.insert().values(id=experiment_id))
        await connection.execute(
            gov.workflows.insert().values(id=workflow_id, experiment_id=experiment_id)
        )
        await connection.execute(
            gov.agents.insert().values(id=agent_id, workflow_id=workflow_id)
        )
    repo = ProductRecordsRepository(engine, clock=lambda: NOW)
    await repo.register_profile(
        OperatorCapabilityProfile(
            id=profile_id,
            version=1,
            operator_id=UUID(int=1),
            capabilities=("Python backend development",),
            constraints=("Synthetic work only",),
            delivery=DeliveryConstraints(
                max_project_hours=Decimal(80),
                hours_per_week=Decimal(20),
                concurrent_projects=1,
            ),
            commercial=CommercialConstraints(
                currency="ILS",
                hourly_cost=Decimal(100),
                minimum_project_price=Decimal(5000),
                minimum_margin_rate=margin,
                maximum_discount_rate=Decimal("0.1"),
                minimum_deposit_rate=Decimal("0.5"),
            ),
            approved_by=UUID(int=1),
            created_at=NOW,
        ),
        command_key=uuid4(),
    )
    await repo.bind_roots(
        ProductExperiment(
            id=experiment_id,
            operator_profile_id=profile_id,
            operator_profile_version=1,
            name="impossible-economics",
            created_at=NOW,
        ),
        ProductWorkflow(
            id=workflow_id,
            experiment_id=experiment_id,
            role="IDEA_TO_RESEARCH",
            created_at=NOW,
        ),
        ProductAgent(
            id=agent_id,
            workflow_id=workflow_id,
            role="MARKET_RESEARCH",
            created_at=NOW,
        ),
        command_key=uuid4(),
    )
    seed = await put(
        repo,
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Original intent."},
    )
    cycle = await repo.create_cycle(
        experiment_id,
        seed=ArtifactInput.from_receipt(seed, role="SEED"),
        command_key=uuid4(),
    )
    idea = await put(
        repo,
        experiment_id,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Service",
            "customer": "Operators",
            "problem": "Manual work",
            "core_intent": "reduce-manual-work",
            "material_pivot": False,
        },
    )
    await repo.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    plan = await put(
        repo,
        experiment_id,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["Is there demand?"], "method": "Fixture review"},
        inputs=(ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),),
    )
    return repo, experiment_id, cycle, idea, plan


async def freeze_bundle(engine, context, *, omit_role=None):
    repo, experiment_id, _, idea, verdict, report, recommendation, inputs = context
    bundle_inputs = [
        ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        ArtifactInput.from_receipt(report, role="REPORT"),
        ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        *(item for item in inputs if item.role != "PLAN"),
    ]
    if omit_role:
        bundle_inputs = [item for item in bundle_inputs if item.role != omit_role]
    bundle = await put(
        repo,
        experiment_id,
        ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE,
        {"status": "FROZEN"},
        inputs=bundle_inputs,
    )
    offer_repo = OfferRecordsRepository(engine)
    receipt = await offer_repo.freeze_input_bundle(
        ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"),
        verdict_id=verdict.id,
        command_key=uuid4(),
    )
    return offer_repo, receipt, bundle, bundle_inputs


async def test_bundle_requires_each_real_research_category_and_envelope_is_exact(
    governance_engine,
):
    context = await complete_research(governance_engine)
    with pytest.raises(ProductRecordsDenied, match="INCOMPLETE_RESEARCH"):
        await freeze_bundle(governance_engine, context, omit_role="OBJECTIONS")

    offer_repo, bundle, _, inputs = await freeze_bundle(governance_engine, context)
    scope = next(item for item in inputs if item.role == "SCOPE_ESTIMATE")
    envelope_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
        {"status": "READY", "reason": "Deterministic operator constraints"},
        inputs=(ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"), scope),
    )
    envelope = await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    assert envelope.status == "READY"
    assert envelope.delivery_cost == Decimal(6000)
    assert envelope.minimum_price == Decimal(10000)
    assert envelope.currency == "ILS"


@pytest.mark.parametrize(
    ("currency", "margin", "scope_hours", "expected"),
    [
        ("USD", None, "60", "CURRENCY_MISMATCH"),
        ("ILS", Decimal(1), "60", "IMPOSSIBLE_ECONOMICS"),
        ("ILS", None, "100", "DELIVERY_CAPACITY_EXCEEDED"),
    ],
)
async def test_envelope_persists_fail_closed_commercial_classification(
    governance_engine, currency, margin, scope_hours, expected
):
    context = await complete_research(
        governance_engine,
        currency=currency,
        margin_override=margin,
        scope_hours=scope_hours,
    )
    offer_repo, bundle, _, inputs = await freeze_bundle(governance_engine, context)
    scope = next(item for item in inputs if item.role == "SCOPE_ESTIMATE")
    artifact_receipt = await put(
        context[0],
        context[1],
        ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
        {"status": expected, "reason": "Commercial constraints prevent pricing"},
        inputs=(ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"), scope),
    )
    receipt = await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(artifact_receipt, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    assert receipt.status == expected
    assert receipt.minimum_price is None


def package_payload(*, base_price="12000"):
    return {
        "target_customer": "Owner-operated service businesses",
        "buyer": "Owner",
        "problem": "Manual lead follow-up",
        "solution_mechanism": "Auditable follow-up automation",
        "credible_outcome": "Faster qualified response",
        "positioning": "Implementation with retained evidence",
        "scope": "One intake and follow-up workflow",
        "deliverables": ["Configured workflow", "Handover"],
        "exclusions": ["Paid media"],
        "prerequisites": ["CRM access"],
        "timeline": "Three weeks",
        "customer_responsibilities": ["Provide CRM access"],
        "currency": "ILS",
        "base_price": base_price,
        "pilot_terms": "No discounted pilot",
        "third_party_costs": "Billed directly to customer",
        "payment_terms": "50 percent deposit",
        "validity": "14 days",
        "claims": ["Scope is based on recorded evidence"],
        "ideal_fit": ["Owner handles lead follow-up"],
        "disqualifiers": ["No CRM access"],
        "negotiation_variables": ["Timeline"],
    }


async def ready_proposal(engine):
    context = await complete_research(engine)
    offer_repo, bundle, _, inputs = await freeze_bundle(engine, context)
    scope = next(item for item in inputs if item.role == "SCOPE_ESTIMATE")
    envelope_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
        {"status": "READY", "reason": "Deterministic operator constraints"},
        inputs=(ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"), scope),
    )
    envelope = await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    proposal_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_DESIGN_PROPOSAL,
        package_payload(),
        inputs=(
            ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"),
            ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
        ),
    )
    proposal = await offer_repo.register_proposal(
        ArtifactInput.from_receipt(proposal_artifact, role="PROPOSAL"),
        bundle_id=bundle.id,
        envelope_id=envelope.id,
        command_key=uuid4(),
    )
    return context, offer_repo, bundle, envelope, proposal, proposal_artifact, inputs


async def test_offer_profile_policy_accept_atomically_with_exhaustive_field_lineage(
    governance_engine,
):
    (
        context,
        offer_repo,
        bundle,
        envelope,
        proposal,
        proposal_artifact,
        inputs,
    ) = await ready_proposal(governance_engine)
    package = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_PACKAGE,
        package_payload(),
        inputs=(ArtifactInput.from_receipt(proposal_artifact, role="PROPOSAL"),),
    )
    profile = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_QUALIFICATION_PROFILE,
        {"summary": "Exact matching qualification profile"},
        inputs=(ArtifactInput.from_receipt(package, role="OFFER"),),
    )
    policy = await put(
        context[0],
        context[1],
        ArtifactKind.INITIAL_OUTREACH_POLICY,
        dict(INITIAL_OUTREACH_POLICY),
        inputs=(ArtifactInput.from_receipt(package, role="OFFER"),),
    )
    input_by_role = {item.role: item for item in inputs}
    field_sources = tuple(
        OfferFieldSource(
            field_path=field,
            source=(
                input_by_role[OFFER_FIELD_EVIDENCE_ROLES[field][0]]
                if field in OFFER_FIELD_EVIDENCE_ROLES
                else None
            ),
            operator_constraint=cast(
                OperatorConstraint | None,
                OPERATOR_FIELD_CONSTRAINTS.get(field),
            ),
        )
        for field in PROTECTED_OFFER_FIELDS
    )
    criteria = tuple(
        QualificationCriterion(
            code=f"C{index}",
            category=category,
            requirement="Evidence must be recorded",
            question="What exact evidence supports this fit?",
            rule_kind=(
                "FATAL_DISQUALIFIER"
                if category == "FATAL_DISQUALIFIER"
                else "SOFT_SIGNAL"
                if category == "POSITIVE_SIGNAL"
                else "HARD_GATE"
            ),
            comparison="PRESENT",
            threshold=None,
            required_evidence_kind="RESEARCH_EVIDENCE",
            unknown_behavior=(
                "NOT_APPLICABLE" if category == "POSITIVE_SIGNAL" else "BLOCK"
            ),
        )
        for index, category in enumerate(REQUIRED_QUALIFICATION_CATEGORIES, 1)
    )
    request = OfferAcceptanceRequest(
        package=ArtifactInput.from_receipt(package, role="OFFER"),
        proposal_id=proposal.id,
        qualification_profile=ArtifactInput.from_receipt(profile, role="PROFILE"),
        criteria=criteria,
        outreach_policy=ArtifactInput.from_receipt(policy, role="POLICY"),
        field_sources=field_sources,
        accepted_by=UUID(int=1),
    )
    with pytest.raises(ProductRecordsDenied, match="FIELD_LINEAGE"):
        await offer_repo.accept_offer(
            request.model_copy(update={"field_sources": field_sources[:-1]}),
            command_key=uuid4(),
        )
    command_key = uuid4()
    accepted = await offer_repo.accept_offer(request, command_key=command_key)
    assert await offer_repo.accept_offer(request, command_key=command_key) == accepted
    assert accepted.bundle_id == bundle.id
    assert accepted.minimum_price == envelope.minimum_price
    async with governance_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(offers.offer_acceptances).where(
                        offers.offer_acceptances.c.id == accepted.id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert row["offer_artifact_id"] == package.artifact_id
        assert row["profile_artifact_id"] == profile.artifact_id
        assert row["policy_artifact_id"] == policy.artifact_id


async def test_new_bundle_invalidates_unaccepted_proposal_and_gap_activates_once(
    governance_engine,
):
    (
        context,
        offer_repo,
        bundle,
        _,
        proposal,
        proposal_artifact,
        research_inputs,
    ) = await ready_proposal(governance_engine)
    gap = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_RESEARCH_GAP_BRIEF,
        {
            "required_evidence": ["Current implementation-cost quote"],
            "justification": "The scope-price relationship is contradictory",
        },
        inputs=(
            ArtifactInput.from_receipt(proposal_artifact, role="ORIGINATING_PROPOSAL"),
            ArtifactInput(
                artifact_id=bundle.artifact_id,
                kind=ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE,
                version=bundle.version,
                content_hash=bundle.content_hash,
                role="OFFER_INPUT_BUNDLE",
            ),
            ArtifactInput.from_receipt(context[3], role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(context[5], role="REPORT"),
            ArtifactInput.from_receipt(context[6], role="RECOMMENDATION"),
        ),
    )
    request = OfferGapRequest(
        artifact=ArtifactInput.from_receipt(gap, role="FEEDBACK"),
        proposal_id=proposal.id,
        missing_fields=("third_party_costs",),
        contradictory_fields=("base_price",),
        required_source_types=("CURRENT_PROVIDER_QUOTE",),
        targeted_questions=("What is the current implementation cost?",),
    )
    command_key = uuid4()
    cycle = await offer_repo.activate_offer_gap(request, command_key=command_key)
    assert cycle.ordinal == 2
    assert (
        await offer_repo.activate_offer_gap(request, command_key=command_key) == cycle
    )
    with pytest.raises(ProductRecordsDenied):
        await offer_repo.activate_offer_gap(request, command_key=uuid4())

    next_plan = await put(
        context[0],
        context[1],
        ArtifactKind.RESEARCH_PLAN,
        {
            "questions": ["Has the offer gap been resolved?"],
            "method": "Targeted offer-gap review",
        },
        inputs=(
            ArtifactInput.from_receipt(gap, role="RETURN_FEEDBACK"),
            ArtifactInput.from_receipt(context[3], role="ACCEPTED_IDEA"),
        ),
    )
    attempt = await context[0].start_research_attempt(
        cycle.id,
        ArtifactInput.from_receipt(next_plan, role="PLAN"),
        command_key=uuid4(),
    )
    next_report = await put(
        context[0],
        context[1],
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "Offer gap resolved", "limitations": ["Synthetic"]},
        inputs=(
            ArtifactInput.from_receipt(next_plan, role="PLAN"),
            *(
                item
                for item in research_inputs
                if item.role not in {"ACCEPTED_IDEA", "REPORT", "RECOMMENDATION"}
            ),
        ),
    )
    next_recommendation = await put(
        context[0],
        context[1],
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {
            "recommendation": "PROCEED_TO_OFFER",
            "rationale": "Fresh targeted evidence resolves the gap",
        },
        inputs=(ArtifactInput.from_receipt(next_report, role="REPORT"),),
    )
    next_verdict = await context[0].commit_verdict(
        attempt.id,
        report=ArtifactInput.from_receipt(next_report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            next_recommendation, role="RECOMMENDATION"
        ),
        verdict="PROCEED_TO_OFFER",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    next_bundle_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE,
        {"status": "FROZEN"},
        inputs=(
            ArtifactInput.from_receipt(context[3], role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(next_report, role="REPORT"),
            ArtifactInput.from_receipt(next_recommendation, role="RECOMMENDATION"),
            *(
                item
                for item in research_inputs
                if item.role not in {"ACCEPTED_IDEA", "REPORT", "RECOMMENDATION"}
            ),
        ),
    )
    await offer_repo.freeze_input_bundle(
        ArtifactInput.from_receipt(next_bundle_artifact, role="INPUT_BUNDLE"),
        verdict_id=next_verdict.id,
        command_key=uuid4(),
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(offers.offer_proposal_invalidations.c.proposal_id).where(
                    offers.offer_proposal_invalidations.c.proposal_id == proposal.id
                )
            )
            == proposal.id
        )


async def test_raw_sql_cannot_bypass_floor_or_reopen_bundle_lineage(
    governance_engine,
):
    context = await complete_research(governance_engine)
    _, bundle, bundle_artifact, inputs = await freeze_bundle(governance_engine, context)
    scope = next(item for item in inputs if item.role == "SCOPE_ESTIMATE")
    envelope_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
        {"status": "READY", "reason": "Deterministic operator constraints"},
        inputs=(ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"), scope),
    )
    offer_repo = OfferRecordsRepository(governance_engine)
    envelope = await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    below_floor = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_DESIGN_PROPOSAL,
        package_payload(base_price="9999.99"),
        inputs=(
            ArtifactInput.from_receipt(bundle, role="INPUT_BUNDLE"),
            ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
        ),
    )
    with pytest.raises(SQLAlchemyError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(offers.offer_proposals).values(
                    id=uuid4(),
                    experiment_id=context[1],
                    artifact_id=below_floor.artifact_id,
                    artifact_kind=below_floor.kind,
                    artifact_version=below_floor.version,
                    artifact_hash=below_floor.content_hash,
                    bundle_id=bundle.id,
                    envelope_id=envelope.id,
                    created_at=NOW,
                )
            )
    extra = await put(
        context[0],
        context[1],
        ArtifactKind.RESEARCH_EVIDENCE,
        {"claim": "Late claim", "finding": "Must not rewrite accepted inputs"},
    )
    with pytest.raises(SQLAlchemyError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.artifact_links).values(
                    consumer_id=bundle_artifact.artifact_id,
                    producer_id=extra.artifact_id,
                    experiment_id=context[1],
                    role="LATE_INPUT",
                    producer_kind=extra.kind,
                    producer_version=extra.version,
                    producer_hash=extra.content_hash,
                )
            )
