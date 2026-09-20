"""Offer-specific qualification matrices and atomic fixed-50 cohorts."""

from datetime import timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import SQLAlchemyError
from test_campaign_supply import candidate, setup
from test_offer_records import (
    OFFER_FIELD_EVIDENCE_ROLES,
    OPERATOR_FIELD_CONSTRAINTS,
    PROTECTED_OFFER_FIELDS,
    REQUIRED_QUALIFICATION_CATEGORIES,
    OperatorConstraint,
    package_payload,
    put,
    ready_proposal,
)
from test_organization_records import complete_content, provision_call, snapshot
from test_product_records import NOW

from alon_ai.contact import ContactPolicyRepository
from alon_ai.providers.contracts import Capability, ContentField
from alon_ai.providers.execution import ExecutionResult
from alon_ai.records import ArtifactInput, ArtifactKind, ProductRecordsDenied
from alon_ai.records import offer_schema as offers
from alon_ai.records import organization_schema as organizations
from alon_ai.records import qualification_schema as qualification
from alon_ai.records.offer_models import (
    INITIAL_OUTREACH_POLICY,
    OfferAcceptanceRequest,
    OfferFieldSource,
    QualificationCriterion,
)
from alon_ai.records.organization_models import RetainedOrganizationSource
from alon_ai.records.organizations import OrganizationRepository
from alon_ai.records.qualification_models import (
    CriterionResultInput,
    FreezeCohortRequest,
    LeadDossierRequest,
    LeadEvidenceInput,
    QualificationDecisionRequest,
    QualificationOutcome,
)
from alon_ai.records.qualifications import QualificationCohortRepository
from alon_ai.supply import schema as supply_schema

pytestmark = pytest.mark.integration

OWNER = UUID(int=1)
KEY = SecretStr("0123456789abcdef" * 2)


async def accepted_offer(engine):
    (
        context,
        offer_repo,
        _,
        _,
        proposal,
        proposal_artifact,
        inputs,
    ) = await ready_proposal(engine)
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
        {"summary": "Exact lead qualification profile"},
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
    criteria = tuple(
        QualificationCriterion(
            code=f"C{index}",
            category=category,
            requirement="Evidence must support the exact offer fit",
            question="What retained evidence answers this criterion?",
            rule_kind=(
                "FATAL_DISQUALIFIER"
                if category == "FATAL_DISQUALIFIER"
                else "SOFT_SIGNAL"
                if category in {"POSITIVE_SIGNAL", "PILOT_FIT"}
                else "HARD_GATE"
            ),
            comparison="PRESENT",
            threshold=None,
            required_evidence_kind="RESEARCH_EVIDENCE",
            unknown_behavior=(
                "NOT_APPLICABLE"
                if category in {"POSITIVE_SIGNAL", "PILOT_FIT"}
                else "BLOCK"
            ),
        )
        for index, category in enumerate(REQUIRED_QUALIFICATION_CATEGORIES, 1)
    )
    acceptance = await offer_repo.accept_offer(
        OfferAcceptanceRequest(
            package=ArtifactInput.from_receipt(package, role="OFFER"),
            proposal_id=proposal.id,
            qualification_profile=ArtifactInput.from_receipt(profile, role="PROFILE"),
            criteria=criteria,
            outreach_policy=ArtifactInput.from_receipt(policy, role="POLICY"),
            field_sources=tuple(
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
            ),
            accepted_by=OWNER,
        ),
        command_key=uuid4(),
    )
    async with engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(offers.offer_acceptances).where(
                        offers.offer_acceptances.c.id == acceptance.id
                    )
                )
            )
            .mappings()
            .one()
        )
    return context[1], row, criteria


async def qualified_pool(engine, size=52):
    experiment_id, acceptance, criteria = await accepted_offer(engine)
    supply, writer, _, plan, _ = await setup(engine, existing_exp=experiment_id)
    batch_id = await supply.begin_batch(experiment_id, 1, plan, uuid4())
    candidates = [
        await candidate(
            supply,
            writer,
            experiment_id,
            batch_id,
            index,
            supported=None,
        )
        for index in range(size)
    ]

    company_context = await provision_call(
        engine,
        experiment_id,
        Capability.FIRECRAWL_PAGE_CAPTURE,
        {ContentField.COMPANY, ContentField.URL},
    )
    company_values = tuple(
        snapshot(registered=str(100000 + index)).model_dump_json()
        for index in range(size)
    )
    _, _, _, _, retained_companies = await complete_content(
        engine, company_context, {ContentField.COMPANY: company_values}
    )

    org_repo = OrganizationRepository(engine, lookup_key=KEY, clock=lambda: NOW)
    contact = ContactPolicyRepository(engine, supply, clock=lambda: NOW)
    leads = []
    for index, (candidate_id, fact) in enumerate(candidates):
        async with engine.connect() as connection:
            identity_id = await connection.scalar(
                select(supply_schema.candidates.c.identity_id).where(
                    supply_schema.candidates.c.id == candidate_id
                )
            )
        identity = await org_repo.register_identity(
            experiment_id,
            identity_id,
            RetainedOrganizationSource(
                retained_id=retained_companies[0], value_index=index, observed_at=NOW
            ),
            registered_by=OWNER,
            command_key=uuid4(),
        )
        admission = await org_repo.admit(
            identity.binding_id, acted_by=OWNER, command_key=uuid4()
        )
        email_context = await provision_call(
            engine,
            experiment_id,
            Capability.BRAVE_LOCAL_DISCOVERY,
            {ContentField.EMAIL},
            service="contact-resolution",
            contact_data=(supply, contact, batch_id, candidate_id),
        )
        content, _, _, final, retained_email = await complete_content(
            engine,
            email_context,
            {ContentField.EMAIL: (f"lead-{index}@fixture.example",)},
        )
        source_id = uuid4()
        await fact("SOURCE_EMAIL", contact_ref=source_id)
        await contact.record_source(
            candidate_id,
            source_id,
            ExecutionResult(receipt=final, content=content),
            uuid4(),
        )
        policy_id = await supply.verification_policy(experiment_id)
        verification_id = await fact(
            "VERIFIED", contact_ref=source_id, policy_ref=policy_id
        )
        await supply.resolve_contact(candidate_id, source_id, verification_id)
        recipient = await org_repo.register_recipient(
            identity.binding_id,
            candidate_id,
            source_id,
            RetainedOrganizationSource(
                retained_id=retained_email[0], value_index=0, observed_at=NOW
            ),
            acted_by=OWNER,
            command_key=uuid4(),
        )
        leads.append((candidate_id, fact, identity, admission, recipient))
    assert await supply.close_contactability(batch_id, uuid4()) is None
    async with engine.begin() as connection:
        await connection.execute(
            update(supply_schema.candidates)
            .where(supply_schema.candidates.c.experiment_id == experiment_id)
            .values(deep_started=True)
        )
    return experiment_id, acceptance, criteria, plan, supply, org_repo, leads


def dossier_request(acceptance, lead, index=0):
    candidate_id, _, identity, admission, recipient = lead
    evidence_id = uuid4()
    return LeadDossierRequest(
        candidate_id=candidate_id,
        binding_id=identity.binding_id,
        admission_id=admission.result_id,
        recipient_source_id=recipient.result_id,
        offer_acceptance_id=acceptance["id"],
        recorded_by=OWNER,
        evidence=(
            LeadEvidenceInput(
                id=evidence_id,
                code=f"OBS-{index}",
                kind="OBSERVED_FACT",
                source_ref=f"fixture://lead/{index}",
                excerpt="The retained public evidence supports this assessment.",
                observed_at=NOW,
                valid_until=NOW + timedelta(hours=2),
                confidence=Decimal("0.95"),
            ),
        ),
    )


def criterion_results(
    criteria,
    evidence_id,
    *,
    hard_failure=None,
    fatal=False,
    fatal_status=None,
    pilot_status=None,
):
    values = []
    for criterion in criteria:
        if criterion.rule_kind == "FATAL_DISQUALIFIER":
            status = fatal_status or ("SATISFIED" if fatal else "NOT_SATISFIED")
        elif criterion.category == "PILOT_FIT" and pilot_status is not None:
            status = pilot_status
        elif criterion.code == hard_failure:
            status = "NOT_SATISFIED"
        else:
            status = "SATISFIED"
        values.append(
            CriterionResultInput(
                criterion_code=criterion.code,
                status=status,
                evidence_ids=(evidence_id,),
                rationale="Evaluated against retained public evidence.",
            )
        )
    return tuple(values)


async def decision_request(
    lead,
    dossier,
    criteria,
    *,
    outcome: QualificationOutcome = "QUALIFIED_CONTACTABLE",
    **kw,
):
    _, fact, _, _, _ = lead
    supply_outcome = (
        "QUALIFIED"
        if outcome in {"QUALIFIED_CONTACTABLE", "PILOT_FIT_CONTACTABLE"}
        else "REJECTED_FIT"
    )
    proposal_fact_id = await fact(
        supply_outcome,
        policy_ref=kw.pop("policy_ref"),
    )
    return QualificationDecisionRequest(
        dossier_id=dossier.id,
        proposal_fact_id=proposal_fact_id,
        proposed_outcome=outcome,
        results=criterion_results(criteria, dossier.evidence_ids[0], **kw),
        finding_codes=("OFFER_FIT_REVIEWED",),
        decided_by=OWNER,
        valid_until=NOW + timedelta(hours=1),
    )


async def test_matrix_rejects_incomplete_failed_stale_and_protected_inputs(
    governance_engine,
):
    (
        experiment_id,
        acceptance,
        criteria,
        plan,
        _,
        org_repo,
        leads,
    ) = await qualified_pool(governance_engine)
    repo = QualificationCohortRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[0]), command_key=uuid4()
    )
    request = await decision_request(
        leads[0], dossier, criteria, policy_ref=plan.qualification_rule_id
    )
    with pytest.raises(ProductRecordsDenied, match="MISSING_CRITERION_RESULT"):
        await repo.decide(
            request.model_copy(update={"results": request.results[:-1]}),
            command_key=uuid4(),
        )
    without_evidence = request.results[0].model_copy(update={"evidence_ids": ()})
    with pytest.raises(ProductRecordsDenied, match="MISSING_EVIDENCE"):
        await repo.decide(
            request.model_copy(
                update={"results": (without_evidence, *request.results[1:])}
            ),
            command_key=uuid4(),
        )

    failed_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[1], 1), command_key=uuid4()
    )
    hard_code = next(c.code for c in criteria if c.rule_kind == "HARD_GATE")
    failed = await repo.decide(
        await decision_request(
            leads[1],
            failed_dossier,
            criteria,
            outcome="REJECTED_NOT_A_FIT",
            policy_ref=plan.qualification_rule_id,
            hard_failure=hard_code,
        ),
        command_key=uuid4(),
    )
    assert (failed.outcome, failed.reason_code) == (
        "REJECTED_NOT_A_FIT",
        "FAILED_HARD_GATE",
    )

    fatal_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[2], 2), command_key=uuid4()
    )
    fatal = await repo.decide(
        await decision_request(
            leads[2],
            fatal_dossier,
            criteria,
            outcome="REJECTED_NOT_A_FIT",
            policy_ref=plan.qualification_rule_id,
            fatal=True,
        ),
        command_key=uuid4(),
    )
    assert fatal.reason_code == "FATAL_DISQUALIFIER"

    unknown_fatal_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[3], 3), command_key=uuid4()
    )
    unknown_fatal = await repo.decide(
        await decision_request(
            leads[3],
            unknown_fatal_dossier,
            criteria,
            outcome="REJECTED_NOT_A_FIT",
            policy_ref=plan.qualification_rule_id,
            fatal_status="UNKNOWN",
        ),
        command_key=uuid4(),
    )
    assert unknown_fatal.reason_code == "FATAL_DISQUALIFIER"

    pilot_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[5], 5), command_key=uuid4()
    )
    with pytest.raises(ProductRecordsDenied, match="PILOT_FIT_NOT_PERMITTED"):
        await repo.decide(
            await decision_request(
                leads[5],
                pilot_dossier,
                criteria,
                outcome="PILOT_FIT_CONTACTABLE",
                policy_ref=plan.qualification_rule_id,
                pilot_status="NOT_SATISFIED",
            ),
            command_key=uuid4(),
        )

    guarded_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[4], 4), command_key=uuid4()
    )
    guarded_row = None
    async with governance_engine.connect() as connection:
        guarded_row = (
            (
                await connection.execute(
                    select(qualification.dossiers).where(
                        qualification.dossiers.c.id == guarded_dossier.id
                    )
                )
            )
            .mappings()
            .one()
        )
    guarded_fact = await leads[4][1]("QUALIFIED", policy_ref=plan.qualification_rule_id)
    matrix_id = uuid4()
    with pytest.raises(SQLAlchemyError, match="complete authoritative qualification"):
        async with governance_engine.begin() as connection:
            lineage = {
                name: guarded_row[name]
                for name in (
                    "experiment_id",
                    "candidate_id",
                    "organization_id",
                    "recipient_id",
                    "recipient_source_id",
                    "offer_acceptance_id",
                    "offer_id",
                    "profile_id",
                    "policy_id",
                )
            }
            await connection.execute(
                insert(qualification.matrices).values(
                    id=matrix_id,
                    dossier_id=guarded_dossier.id,
                    created_at=NOW,
                    **lineage,
                )
            )
            raw_results = criterion_results(
                criteria, guarded_dossier.evidence_ids[0], fatal_status="UNKNOWN"
            )
            await connection.execute(
                insert(qualification.criterion_results),
                [
                    {
                        "matrix_id": matrix_id,
                        "profile_id": acceptance["profile_id"],
                        "criterion_code": item.criterion_code,
                        "status": item.status,
                        "rationale": item.rationale,
                    }
                    for item in raw_results
                ],
            )
            await connection.execute(
                insert(qualification.result_evidence),
                [
                    {
                        "matrix_id": matrix_id,
                        "criterion_code": item.criterion_code,
                        "dossier_id": guarded_dossier.id,
                        "evidence_id": guarded_dossier.evidence_ids[0],
                    }
                    for item in raw_results
                ],
            )
            await connection.execute(
                insert(supply_schema.qualifications).values(
                    candidate_id=guarded_row["candidate_id"],
                    experiment_id=experiment_id,
                    fact_id=guarded_fact,
                    accepted_at=NOW,
                    outcome="QUALIFIED",
                )
            )
            await connection.execute(
                insert(qualification.decisions).values(
                    id=uuid4(),
                    matrix_id=matrix_id,
                    dossier_id=guarded_dossier.id,
                    proposal_fact_id=guarded_fact,
                    outcome="QUALIFIED_CONTACTABLE",
                    reason_code="QUALIFIED",
                    finding_codes=["BYPASS_ATTEMPT"],
                    valid_until=NOW + timedelta(hours=1),
                    decided_by=OWNER,
                    decided_at=NOW,
                    **lineage,
                )
            )

    stale_repo = QualificationCohortRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW + timedelta(hours=3)
    )
    stale_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[50], 50), command_key=uuid4()
    )
    with pytest.raises(ProductRecordsDenied, match="STALE_CONTACT"):
        await stale_repo.decide(
            await decision_request(
                leads[50],
                stale_dossier,
                criteria,
                policy_ref=plan.qualification_rule_id,
            ),
            command_key=uuid4(),
        )

    await org_repo.suppress(
        acted_by=OWNER,
        reason_code="OPERATOR_BLOCK",
        organization_id=leads[51][2].organization_id,
        command_key=uuid4(),
    )
    protected_dossier = await repo.record_dossier(
        dossier_request(acceptance, leads[51], 51), command_key=uuid4()
    )
    with pytest.raises(ProductRecordsDenied, match="PROTECTION_CONFLICT"):
        await repo.decide(
            await decision_request(
                leads[51],
                protected_dossier,
                criteria,
                policy_ref=plan.qualification_rule_id,
            ),
            command_key=uuid4(),
        )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count()).select_from(qualification.decisions)
            )
            == 3
        )
        assert (
            await connection.scalar(
                select(func.count()).select_from(supply_schema.qualifications)
            )
            == 3
        )
        assert (
            await connection.scalar(
                select(supply_schema.plans.c.state).where(
                    supply_schema.plans.c.experiment_id == experiment_id
                )
            )
            == "ACTIVE"
        )


async def test_exact_fifty_freeze_is_atomic_protected_and_replayable(governance_engine):
    (
        experiment_id,
        acceptance,
        criteria,
        plan,
        _,
        org_repo,
        leads,
    ) = await qualified_pool(governance_engine, size=50)
    repo = QualificationCohortRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    decisions = []
    for index, lead in enumerate(leads):
        request = dossier_request(acceptance, lead, index)
        dossier = await repo.record_dossier(request, command_key=uuid4())
        decisions.append(
            await repo.decide(
                await decision_request(
                    lead,
                    dossier,
                    criteria,
                    policy_ref=plan.qualification_rule_id,
                ),
                command_key=uuid4(),
            )
        )

    preexisting = await org_repo.reserve(
        leads[-1][4].result_id, acted_by=OWNER, command_key=uuid4()
    )
    freeze = FreezeCohortRequest(
        offer_acceptance_id=acceptance["id"],
        decision_ids=tuple(item.id for item in decisions),
        frozen_by=OWNER,
    )
    with pytest.raises(ProductRecordsDenied, match="PROTECTION_CONFLICT"):
        await repo.freeze_cohort(freeze, command_key=uuid4())
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count()).select_from(qualification.cohorts)
            )
            == 0
        )
        assert (
            await connection.scalar(
                select(func.count()).select_from(qualification.cohort_members)
            )
            == 0
        )
        assert (
            await connection.scalar(
                select(func.count()).select_from(organizations.reservations)
            )
            == 1
        )

    await org_repo.release(
        preexisting.result_id,
        acted_by=OWNER,
        evidence_id=None,
        command_key=uuid4(),
    )
    with pytest.raises(ProductRecordsDenied, match="STALE_OFFER_VERSION"):
        await repo.freeze_cohort(
            freeze.model_copy(update={"offer_acceptance_id": uuid4()}),
            command_key=uuid4(),
        )

    command_key = uuid4()
    cohort = await repo.freeze_cohort(freeze, command_key=command_key)
    assert await repo.freeze_cohort(freeze, command_key=command_key) == cohort
    assert cohort.member_count == 50
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count()).select_from(qualification.cohort_members)
            )
            == 50
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(organizations.reservations)
                .where(
                    organizations.reservations.c.experiment_id == experiment_id,
                    ~organizations.reservations.c.id.in_([preexisting.result_id]),
                )
            )
            == 50
        )
        assert (
            await connection.scalar(
                select(supply_schema.plans.c.state).where(
                    supply_schema.plans.c.experiment_id == experiment_id
                )
            )
            == "TARGET_50_REACHED"
        )
