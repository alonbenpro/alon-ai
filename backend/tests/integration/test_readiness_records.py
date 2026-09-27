"""Immutable receipt-backed lead-readiness records."""

from datetime import timedelta
from functools import partial
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from test_contact_policy import provision
from test_product_record_guards import put
from test_product_records import NOW
from test_qualification_cohorts import KEY, OWNER, qualified_pool

from alon_ai.db.repositories.accounting import GovernanceRepository
from alon_ai.db.repositories.contact import ContactAdmissionHook
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.repositories.records_readiness import ReadinessRepository
from alon_ai.db.repositories.supply import ComposedContactSupplyHook
from alon_ai.db.tables import accounting as governance
from alon_ai.db.tables import supply
from alon_ai.db.tables.contact import cases as contact_cases
from alon_ai.integrations.contact import ConfiguredContactAdapter
from alon_ai.integrations.fakes import FakeEmailVerificationProvider, FakeSession
from alon_ai.integrations.schemas.provider import (
    Capability,
    ContentField,
    EmailVerificationRequest,
    ProviderCallResult,
    SafeRequestMetadata,
    UsageComponent,
)
from alon_ai.policies.provider_rights import RuntimeContent
from alon_ai.provider_usage.service import GovernedExecutor
from alon_ai.services.schemas.records import (
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)
from alon_ai.services.schemas.records_readiness import (
    ContactabilityDecisionRequest,
    ProviderResultRequest,
    ResearchPlanRequest,
)

pytestmark = pytest.mark.integration


async def governed_verifier(
    engine,
    supply_repo,
    contact,
    experiment_id,
    batch_id,
    candidate_id,
    source_id,
    verification_id,
    *,
    status="VALID",
):
    """Complete one real governed verifier attempt for readiness integration tests."""
    attr, config, grant, intended_use = await provision(
        engine,
        supply_repo,
        contact,
        experiment_id=experiment_id,
        workflow_id=uuid4(),
        batch_id=batch_id,
        candidate_id=candidate_id,
        capability=Capability.HUNTER_EMAIL_VERIFICATION,
        component=UsageComponent.VERIFICATION,
        source_case_id=candidate_id,
        source_fact_id=source_id,
    )
    session = FakeSession(
        grants={Capability.HUNTER_EMAIL_VERIFICATION: grant},
        intended_uses={Capability.HUNTER_EMAIL_VERIFICATION: intended_use},
        clock=lambda: NOW,
    )

    class Verifier:
        async def verify(self, request):
            base = await FakeEmailVerificationProvider(session).verify(request)
            return ProviderCallResult(
                base.metadata,
                RuntimeContent(
                    {ContentField.TEXT: (status,)},
                    grant=grant,
                    intended_use=intended_use,
                    observed_at=NOW,
                ),
            )

    adapter = ConfiguredContactAdapter(
        Verifier(),
        EmailVerificationRequest(
            business_id=candidate_id,
            email_candidate_id=source_id,
            source_evidence_ref=source_id,
            business_match_ref=source_id,
            address=SecretStr("lead-0@fixture.example"),
        ),
        capability=Capability.HUNTER_EMAIL_VERIFICATION,
    )
    governed = GovernanceRepository(
        engine,
        clock=lambda: NOW,
        admission_hooks={
            "CONTACT": ComposedContactSupplyHook(
                supply_repo, contact_owner=ContactAdmissionHook(contact)
            )
        },
    )
    result = await GovernedExecutor(
        governed, adapters={config.adapter_version: adapter}
    ).execute(attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4())
    await contact.record_attempt(result, uuid4(), output_fact_id=verification_id)
    return result


async def test_contactability_provider_receipt_and_research_plan_are_replay_safe(
    governance_engine,
):
    exp, acceptance, _, _, _, _, leads = await qualified_pool(
        governance_engine, 50, verify_first=governed_verifier
    )
    candidate, _, _, _, recipient = leads[0]
    repo = ReadinessRepository(governance_engine, lookup_key=KEY, clock=lambda: NOW)
    async with governance_engine.connect() as connection:
        case = (
            (
                await connection.execute(
                    select(contact_cases).where(
                        contact_cases.c.candidate_id == candidate
                    )
                )
            )
            .mappings()
            .one()
        )
        result_evidence_id = await connection.scalar(
            select(governance.evidence.c.id).where(
                governance.evidence.c.call_id == case["brave_call_id"],
                governance.evidence.c.kind == "PROVIDER_RESULT",
            )
        )
        retained_id = await connection.scalar(
            select(governance.retained.c.id).where(
                governance.retained.c.call_id == case["brave_call_id"]
            )
        )
        batch_id = await connection.scalar(
            select(supply.candidates.c.batch_id).where(
                supply.candidates.c.id == candidate
            )
        )
    provider = await repo.record_provider_result(
        ProviderResultRequest(
            candidate_id=candidate,
            batch_id=batch_id,
            call_id=case["brave_call_id"],
            result_evidence_id=result_evidence_id,
            retained_id=retained_id,
            observed_at=NOW,
            valid_until=NOW + timedelta(minutes=30),
            recorded_by=OWNER,
        ),
        command_key=uuid4(),
    )
    request = ContactabilityDecisionRequest(
        candidate_id=candidate,
        recipient_source_id=recipient.result_id,
        provider_result_id=provider.result_id,
        outcome="SUPPORTED_CONTACT_ADDRESS",
        reason_code="VERIFIED_ADDRESS",
        decided_by=OWNER,
        valid_until=NOW + timedelta(minutes=30),
    )
    first = await repo.decide_contactability(request, command_key=uuid4())
    assert first.outcome == "SUPPORTED_CONTACT_ADDRESS"

    artifact = await put(
        ProductRecordsRepository(governance_engine),
        exp,
        ArtifactKind.RESEARCH_PLAN,
        {
            "questions": ["What current evidence supports this offer?"],
            "method": "bounded review",
        },
    )
    plan = await repo.record_research_plan(
        ResearchPlanRequest(
            candidate_id=candidate,
            recipient_source_id=recipient.result_id,
            offer_acceptance_id=acceptance["id"],
            artifact=ArtifactInput.from_receipt(artifact, role="PLAN"),
            created_by=OWNER,
        ),
        command_key=uuid4(),
    )
    assert plan.result_id


async def test_no_email_cannot_be_fabricated_from_a_supported_contact(
    governance_engine,
):
    _, _, _, _, _, _, leads = await qualified_pool(governance_engine, 50)
    candidate = leads[0][0]
    repo = ReadinessRepository(governance_engine, lookup_key=KEY, clock=lambda: NOW)
    with pytest.raises(ProductRecordsDenied, match="CONTACTABILITY_LINEAGE"):
        await repo.decide_contactability(
            ContactabilityDecisionRequest(
                candidate_id=candidate,
                outcome="EMAIL_NOT_FOUND",
                reason_code="NO_EMAIL_RETURNED",
                decided_by=OWNER,
                valid_until=NOW + timedelta(minutes=30),
            ),
            command_key=uuid4(),
        )


@pytest.mark.parametrize("rejected_status", ["INVALID", "UNKNOWN", "ACCEPT_ALL"])
async def test_observed_email_with_rejected_verification_persists_no_email(
    governance_engine, rejected_status
):
    _, _, _, _, _, _, leads = await qualified_pool(
        governance_engine,
        51,
        verify_first=partial(governed_verifier, status=rejected_status),
        first_contact_rejected=True,
    )
    candidate_id, _, identity, _, _ = leads[0]
    repo = ReadinessRepository(governance_engine, lookup_key=KEY, clock=lambda: NOW)
    async with governance_engine.connect() as c:
        case = (
            (
                await c.execute(
                    select(contact_cases).where(
                        contact_cases.c.candidate_id == candidate_id
                    )
                )
            )
            .mappings()
            .one()
        )
        proof = await c.scalar(
            select(governance.evidence.c.id).where(
                governance.evidence.c.call_id == case["brave_call_id"],
                governance.evidence.c.kind == "PROVIDER_RESULT",
            )
        )
        retained = await c.scalar(
            select(governance.retained.c.id).where(
                governance.retained.c.call_id == case["brave_call_id"]
            )
        )
        batch_id = await c.scalar(
            select(supply.candidates.c.batch_id).where(
                supply.candidates.c.id == candidate_id
            )
        )
    receipt = await repo.record_provider_result(
        ProviderResultRequest(
            candidate_id=candidate_id,
            batch_id=batch_id,
            call_id=case["brave_call_id"],
            result_evidence_id=proof,
            retained_id=retained,
            observed_at=NOW,
            valid_until=NOW + timedelta(minutes=30),
            recorded_by=OWNER,
        ),
        command_key=uuid4(),
    )
    request = ContactabilityDecisionRequest(
        candidate_id=candidate_id,
        provider_result_id=receipt.result_id,
        outcome="EMAIL_NOT_FOUND",
        reason_code="EXCLUDED_NO_USABLE_EMAIL",
        decided_by=OWNER,
        valid_until=NOW + timedelta(minutes=30),
    )
    key = uuid4()
    decision = await repo.decide_contactability(request, command_key=key)
    assert decision.outcome == "EMAIL_NOT_FOUND"
    assert await repo.decide_contactability(request, command_key=key) == decision
    from alon_ai.db.tables import records_readiness as readiness_schema

    async with governance_engine.connect() as c:
        row = (
            (await c.execute(select(readiness_schema.contactability_decisions)))
            .mappings()
            .one()
        )
        assert row["organization_id"] == identity.organization_id
        assert row["recipient_source_id"] is None
        candidate = (
            (
                await c.execute(
                    select(supply.candidates).where(
                        supply.candidates.c.id == candidate_id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert not candidate["deep_started"]
