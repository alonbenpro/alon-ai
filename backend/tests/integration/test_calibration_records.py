"""Aggregate calibration is evidence-backed, replay-safe, and blocks only on accept."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from test_offer_records import PROTECTED_OFFER_FIELDS, package_payload, put
from test_product_records import NOW
from test_qualification_cohorts import (
    KEY,
    OWNER,
    decision_request,
    dossier_request,
    qualified_pool,
)

from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.repositories.records_calibration import (
    CalibrationRepository,
    assert_no_pending_calibration,
)
from alon_ai.db.repositories.records_offers import OfferRecordsRepository
from alon_ai.db.repositories.records_qualifications import QualificationCohortRepository
from alon_ai.db.tables import records_calibration as calibration_schema
from alon_ai.db.tables import records_offer as offers
from alon_ai.db.tables import records_qualification as qualification
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)
from alon_ai.services.schemas.records_calibration import (
    CalibrationDecisionRequest,
    CalibrationFulfillmentRequest,
    CalibrationProposalRequest,
)
from alon_ai.services.schemas.records_offer import (
    INITIAL_OUTREACH_POLICY,
    OfferAcceptanceRequest,
    OfferFieldSource,
)
from alon_ai.services.schemas.records_qualification import FreezeCohortRequest

pytestmark = pytest.mark.integration


async def _technical_mismatch_decisions(engine):
    (
        experiment_id,
        acceptance,
        criteria,
        plan,
        _,
        _,
        leads,
    ) = await qualified_pool(engine, size=50)
    qualifications = QualificationCohortRepository(
        engine, lookup_key=KEY, clock=lambda: NOW
    )
    technical = next(item.code for item in criteria if item.category == "TECHNICAL_FIT")
    decisions = []
    for index, lead in enumerate(leads[:2]):
        dossier = await qualifications.record_dossier(
            dossier_request(acceptance, lead, index), command_key=uuid4()
        )
        request = await decision_request(
            lead,
            dossier,
            criteria,
            outcome="REJECTED_TECHNICAL_MISMATCH",
            policy_ref=plan.qualification_rule_id,
            hard_failure=technical,
        )
        decisions.append(
            await qualifications.decide(
                request.model_copy(update={"finding_codes": ("TECHNICAL_MISMATCH",)}),
                command_key=uuid4(),
            )
        )
    return experiment_id, acceptance, decisions


async def test_calibration_requires_repeated_exact_mismatch_and_replays(
    governance_engine,
):
    experiment_id, acceptance, decisions = await _technical_mismatch_decisions(
        governance_engine
    )
    repository = CalibrationRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    request = CalibrationProposalRequest(
        base_offer_acceptance_id=acceptance["id"],
        decision_ids=tuple(item.id for item in decisions),
        mismatch_code="TECHNICAL_MISMATCH",
        proposed_change_codes=("NARROW_TECHNICAL_PREREQUISITES",),
        proposed_by=OWNER,
    )
    key = uuid4()
    proposal = await repository.propose(request, command_key=key)
    assert await repository.propose(request, command_key=key) == proposal

    rejected = await repository.decide(
        CalibrationDecisionRequest(
            proposal_id=proposal.id,
            outcome="REJECT",
            rule_version="qualification-calibration-v1",
            reason_code="INSUFFICIENT_RECURRING_SIGNAL",
            decided_by=OWNER,
        ),
        command_key=uuid4(),
    )
    assert rejected.outcome == "REJECT"
    async with governance_engine.begin() as connection:
        await assert_no_pending_calibration(connection, experiment_id)


async def test_only_accepted_pending_calibration_blocks_cohort_work(governance_engine):
    experiment_id, acceptance, decisions = await _technical_mismatch_decisions(
        governance_engine
    )
    repository = CalibrationRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    proposal = await repository.propose(
        CalibrationProposalRequest(
            base_offer_acceptance_id=acceptance["id"],
            decision_ids=tuple(item.id for item in decisions),
            mismatch_code="TECHNICAL_MISMATCH",
            proposed_change_codes=("NARROW_TECHNICAL_PREREQUISITES",),
            proposed_by=OWNER,
        ),
        command_key=uuid4(),
    )
    accepted = await repository.decide(
        CalibrationDecisionRequest(
            proposal_id=proposal.id,
            outcome="ACCEPT",
            rule_version="qualification-calibration-v1",
            reason_code="REPEATED_TECHNICAL_MISMATCH",
            decided_by=OWNER,
        ),
        command_key=uuid4(),
    )
    assert accepted.outcome == "ACCEPT"
    async with governance_engine.begin() as connection:
        with pytest.raises(
            ProductRecordsDenied, match="CALIBRATION_FULFILLMENT_PENDING"
        ):
            await assert_no_pending_calibration(connection, experiment_id)


async def _accept_calibrated_offer(
    engine, experiment_id, acceptance, criteria, calibration_decision_id
):
    offer_repository = OfferRecordsRepository(engine)
    records_repository = ProductRecordsRepository(engine, clock=lambda: NOW)
    async with engine.connect() as connection:
        package = (
            (
                await connection.execute(
                    select(offers.offer_packages).where(
                        offers.offer_packages.c.id == acceptance["offer_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        sources = tuple(
            (
                await connection.execute(
                    select(offers.offer_field_sources).where(
                        offers.offer_field_sources.c.offer_id == package["id"]
                    )
                )
            )
            .mappings()
            .all()
        )
        bundle = (
            (
                await connection.execute(
                    select(offers.offer_bundles).where(
                        offers.offer_bundles.c.id == package["bundle_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        envelope = (
            (
                await connection.execute(
                    select(offers.commercial_envelopes).where(
                        offers.commercial_envelopes.c.id == package["envelope_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
    bundle_input = ArtifactInput(
        artifact_id=bundle["artifact_id"],
        kind=ArtifactKind(bundle["artifact_kind"]),
        version=bundle["artifact_version"],
        content_hash=bundle["artifact_hash"],
        role="INPUT_BUNDLE",
    )
    envelope_input = ArtifactInput(
        artifact_id=envelope["artifact_id"],
        kind=ArtifactKind(envelope["artifact_kind"]),
        version=envelope["artifact_version"],
        content_hash=envelope["artifact_hash"],
        role="ENVELOPE",
    )
    proposal_artifact = await put(
        records_repository,
        experiment_id,
        ArtifactKind.OFFER_DESIGN_PROPOSAL,
        package_payload(),
        inputs=(bundle_input, envelope_input),
    )
    proposal = await offer_repository.register_proposal(
        ArtifactInput.from_receipt(proposal_artifact, role="PROPOSAL"),
        bundle_id=package["bundle_id"],
        envelope_id=package["envelope_id"],
        command_key=uuid4(),
    )
    package_artifact = await put(
        records_repository,
        experiment_id,
        ArtifactKind.OFFER_PACKAGE,
        package_payload(),
        inputs=(ArtifactInput.from_receipt(proposal_artifact, role="PROPOSAL"),),
    )
    profile = await put(
        records_repository,
        experiment_id,
        ArtifactKind.OFFER_QUALIFICATION_PROFILE,
        {"summary": "Revalidated exact lead qualification profile"},
        inputs=(ArtifactInput.from_receipt(package_artifact, role="OFFER"),),
    )
    policy = await put(
        records_repository,
        experiment_id,
        ArtifactKind.INITIAL_OUTREACH_POLICY,
        dict(INITIAL_OUTREACH_POLICY),
        inputs=(ArtifactInput.from_receipt(package_artifact, role="OFFER"),),
    )
    source_by_field = {row["field_path"]: row for row in sources}
    field_sources = []
    for field in PROTECTED_OFFER_FIELDS:
        source = source_by_field[field]
        field_sources.append(
            OfferFieldSource(
                field_path=field,
                source=(
                    ArtifactInput(
                        artifact_id=source["source_artifact_id"],
                        kind=ArtifactKind(source["source_kind"]),
                        version=source["source_version"],
                        content_hash=source["source_hash"],
                        role=source["source_role"],
                    )
                    if source["source_artifact_id"] is not None
                    else None
                ),
                operator_constraint=source["operator_constraint"],
            )
        )
    receipt = await offer_repository.accept_offer(
        OfferAcceptanceRequest(
            calibration_decision_id=calibration_decision_id,
            package=ArtifactInput.from_receipt(package_artifact, role="OFFER"),
            proposal_id=proposal.id,
            qualification_profile=ArtifactInput.from_receipt(profile, role="PROFILE"),
            criteria=criteria,
            outreach_policy=ArtifactInput.from_receipt(policy, role="POLICY"),
            field_sources=tuple(field_sources),
            accepted_by=OWNER,
        ),
        command_key=uuid4(),
    )
    async with engine.connect() as connection:
        return (
            (
                await connection.execute(
                    select(offers.offer_acceptances).where(
                        offers.offer_acceptances.c.id == receipt.id
                    )
                )
            )
            .mappings()
            .one()
        )


async def test_fulfillment_appends_obligations_and_requalification_history(
    governance_engine,
):
    (
        experiment_id,
        acceptance,
        criteria,
        plan,
        _,
        _,
        leads,
    ) = await qualified_pool(governance_engine, size=50)
    qualifications = QualificationCohortRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    technical = next(item.code for item in criteria if item.category == "TECHNICAL_FIT")
    rejected = []
    initial = []
    for index, lead in enumerate(leads[:2]):
        dossier = await qualifications.record_dossier(
            dossier_request(acceptance, lead, index), command_key=uuid4()
        )
        request = await decision_request(
            lead,
            dossier,
            criteria,
            outcome="REJECTED_TECHNICAL_MISMATCH",
            policy_ref=plan.qualification_rule_id,
            hard_failure=technical,
        )
        rejected.append(
            await qualifications.decide(
                request.model_copy(update={"finding_codes": ("TECHNICAL_MISMATCH",)}),
                command_key=uuid4(),
            )
        )
    for index, lead in enumerate(leads[2:], 2):
        dossier = await qualifications.record_dossier(
            dossier_request(acceptance, lead, index), command_key=uuid4()
        )
        initial.append(
            await qualifications.decide(
                await decision_request(
                    lead,
                    dossier,
                    criteria,
                    policy_ref=plan.qualification_rule_id,
                ),
                command_key=uuid4(),
            )
        )
    calibration = CalibrationRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    proposal = await calibration.propose(
        CalibrationProposalRequest(
            base_offer_acceptance_id=acceptance["id"],
            decision_ids=tuple(item.id for item in rejected),
            mismatch_code="TECHNICAL_MISMATCH",
            proposed_change_codes=("NARROW_TECHNICAL_PREREQUISITES",),
            proposed_by=OWNER,
        ),
        command_key=uuid4(),
    )
    decision = await calibration.decide(
        CalibrationDecisionRequest(
            proposal_id=proposal.id,
            outcome="ACCEPT",
            rule_version="qualification-calibration-v1",
            reason_code="REPEATED_TECHNICAL_MISMATCH",
            decided_by=OWNER,
        ),
        command_key=uuid4(),
    )
    replacement = await _accept_calibrated_offer(
        governance_engine, experiment_id, acceptance, criteria, decision.id
    )
    fulfillment_request = CalibrationFulfillmentRequest(
        calibration_decision_id=decision.id,
        offer_acceptance_id=replacement["id"],
        fulfilled_by=OWNER,
    )
    fulfillment_key = uuid4()
    fulfillment = await calibration.fulfill(
        fulfillment_request, command_key=fulfillment_key
    )
    assert (
        await calibration.fulfill(fulfillment_request, command_key=fulfillment_key)
        == fulfillment
    )
    assert fulfillment.requalification_count == 50

    current = []
    for index, lead in enumerate(leads):
        dossier = await qualifications.record_dossier(
            dossier_request(replacement, lead, index + 100), command_key=uuid4()
        )
        current.append(
            await qualifications.decide(
                await decision_request(
                    lead,
                    dossier,
                    criteria,
                    policy_ref=plan.qualification_rule_id,
                ),
                command_key=uuid4(),
            )
        )
    cohort = await qualifications.freeze_cohort(
        FreezeCohortRequest(
            offer_acceptance_id=replacement["id"],
            decision_ids=tuple(item.id for item in current),
            frozen_by=OWNER,
        ),
        command_key=uuid4(),
    )
    assert cohort.member_count == 50
    async with governance_engine.begin() as connection:
        await qualifications._context(connection)
        assert (
            await connection.scalar(
                select(func.count()).select_from(qualification.decisions)
            )
            == 100
        )
        assert (
            await connection.scalar(
                select(func.count()).select_from(calibration_schema.completions)
            )
            == 50
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_current_supply_qualifications "
                    "WHERE experiment_id=:experiment AND outcome='QUALIFIED'"
                ),
                {"experiment": experiment_id},
            )
            == 50
        )
