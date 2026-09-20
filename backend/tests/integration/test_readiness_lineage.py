"""Accepted plans and retained-source boundaries survive adoption and replay."""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from test_campaign_supply import setup
from test_contact_policy import register
from test_organization_records import complete_content, provision_call, snapshot
from test_product_record_guards import put
from test_product_records import NOW
from test_qualification_cohorts import (
    KEY,
    OWNER,
    accepted_offer,
    dossier_request,
    qualified_pool,
)

from alon_ai.accounting import schema as g
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.contact import cases
from alon_ai.providers.contracts import Capability, ContentField
from alon_ai.providers.rights import GrantEvent, GrantEventKind
from alon_ai.records import ArtifactInput, ArtifactKind, ProductRecordsDenied
from alon_ai.records import offer_schema as offers
from alon_ai.records import qualification_schema as q
from alon_ai.records import readiness_schema as r
from alon_ai.records import schema as artifacts
from alon_ai.records.qualifications import QualificationCohortRepository
from alon_ai.records.readiness import ReadinessRepository
from alon_ai.records.readiness_models import (
    ContactabilityDecisionRequest,
    DiscoveryPlanRequest,
    ProviderResultRequest,
    ResearchEvidenceLinkRequest,
    ResearchPlanRequest,
    ResearchRunRequest,
)
from alon_ai.records.repository import ProductRecordsRepository
from alon_ai.supply import schema as supply

pytestmark = pytest.mark.integration


async def test_discovery_plan_pins_accepted_inputs_and_explicit_geography(
    governance_engine,
):
    exp, acceptance, _ = await accepted_offer(governance_engine)
    supply_repo, _, _, plan, _ = await setup(governance_engine, existing_exp=exp)
    batch = await supply_repo.begin_batch(exp, 1, plan, uuid4())
    async with governance_engine.connect() as c:
        bundle = (
            (
                await c.execute(
                    select(offers.offer_bundles)
                    .join(
                        offers.offer_packages,
                        offers.offer_packages.c.bundle_id == offers.offer_bundles.c.id,
                    )
                    .where(offers.offer_packages.c.id == acceptance["offer_id"])
                )
            )
            .mappings()
            .one()
        )
        rows = (
            (
                await c.execute(
                    select(artifacts.artifacts).where(
                        artifacts.artifacts.c.id.in_(
                            [bundle["idea_artifact_id"], bundle["report_artifact_id"]]
                        )
                    )
                )
            )
            .mappings()
            .all()
        )
    by_id = {row["id"]: row for row in rows}

    def ref(id_, role):
        row = by_id[id_]
        return ArtifactInput(
            artifact_id=id_,
            kind=ArtifactKind(row["kind"]),
            version=row["version"],
            content_hash=row["content_hash"],
            role=role,
        )

    request = DiscoveryPlanRequest(
        batch_id=batch,
        offer_acceptance_id=acceptance["id"],
        accepted_idea=ref(bundle["idea_artifact_id"], "IDEA"),
        market_research=ref(bundle["report_artifact_id"], "RESEARCH"),
        mode="ONLINE_COMPANY",
        geography_filter_ids=tuple(
            item.value for item in plan.filters if item.dimension == "GEOGRAPHY"
        ),
        created_by=OWNER,
    )
    with pytest.raises(ValidationError):
        DiscoveryPlanRequest.model_validate(
            {
                **request.model_dump(),
                "mode": "LOCAL_BUSINESS",
                "geography_filter_ids": (),
            }
        )
    repo = ReadinessRepository(governance_engine, lookup_key=KEY, clock=lambda: NOW)
    key = uuid4()
    receipt = await repo.record_discovery_plan(request, command_key=key)
    assert await repo.record_discovery_plan(request, command_key=key) == receipt
    with pytest.raises(ProductRecordsDenied):
        await repo.record_discovery_plan(
            request.model_copy(update={"geography_filter_ids": (uuid4(),)}),
            command_key=uuid4(),
        )
    with pytest.raises(ProductRecordsDenied):
        await repo.record_discovery_plan(
            request.model_copy(update={"market_research": request.accepted_idea}),
            command_key=uuid4(),
        )
    async with governance_engine.connect() as c:
        assert await c.scalar(select(func.count()).select_from(r.discovery_plans)) == 1
    context = await provision_call(
        governance_engine,
        exp,
        Capability.BRAVE_LOCAL_DISCOVERY,
        {ContentField.COMPANY},
        service="campaign-supply",
        supply_data=(supply_repo, batch),
    )
    _, _, proof, final, retained = await complete_content(
        governance_engine,
        context,
        {ContentField.COMPANY: (snapshot().model_dump_json(),)},
    )
    result_request = ProviderResultRequest(
        candidate_id=None,
        batch_id=batch,
        call_id=final.call_id,
        result_evidence_id=proof,
        retained_id=retained[0],
        observed_at=NOW,
        valid_until=NOW + timedelta(minutes=30),
        recorded_by=OWNER,
    )
    result_key = uuid4()
    result = await repo.record_provider_result(result_request, command_key=result_key)
    assert (
        await repo.record_provider_result(result_request, command_key=result_key)
        == result
    )


async def test_research_retains_references_not_provider_text_and_rechecks_rights(
    governance_engine,
):
    from test_readiness_records import governed_verifier

    exp, acceptance, _, _, _, _, leads = await qualified_pool(
        governance_engine, 50, verify_first=governed_verifier
    )
    lead = leads[0]
    repo = ReadinessRepository(governance_engine, lookup_key=KEY, clock=lambda: NOW)
    async with governance_engine.connect() as c:
        case = (
            (await c.execute(select(cases).where(cases.c.candidate_id == lead[0])))
            .mappings()
            .one()
        )
        call = (
            (
                await c.execute(
                    select(g.calls).where(g.calls.c.id == case["brave_call_id"])
                )
            )
            .mappings()
            .one()
        )
        proof = await c.scalar(
            select(g.evidence.c.id).where(
                g.evidence.c.call_id == call["id"],
                g.evidence.c.kind == "PROVIDER_RESULT",
            )
        )
        retained = await c.scalar(
            select(g.retained.c.id).where(g.retained.c.call_id == call["id"])
        )
        batch = await c.scalar(
            select(supply.candidates.c.batch_id).where(
                supply.candidates.c.id == lead[0]
            )
        )
    source_request = ProviderResultRequest(
        candidate_id=lead[0],
        batch_id=batch,
        call_id=call["id"],
        result_evidence_id=proof,
        retained_id=retained,
        observed_at=NOW,
        valid_until=NOW + timedelta(minutes=30),
        recorded_by=OWNER,
    )
    source = await repo.record_provider_result(source_request, command_key=uuid4())
    await repo.decide_contactability(
        ContactabilityDecisionRequest(
            candidate_id=lead[0],
            recipient_source_id=lead[4].result_id,
            provider_result_id=source.result_id,
            outcome="SUPPORTED_CONTACT_ADDRESS",
            reason_code="VERIFIED_ADDRESS",
            decided_by=OWNER,
            valid_until=NOW + timedelta(minutes=30),
        ),
        command_key=uuid4(),
    )
    artifact = await put(
        ProductRecordsRepository(governance_engine),
        exp,
        ArtifactKind.RESEARCH_PLAN,
        {
            "questions": ["Check every exact offer criterion"],
            "method": "bounded review",
        },
    )
    plan = await repo.record_research_plan(
        ResearchPlanRequest(
            candidate_id=lead[0],
            recipient_source_id=lead[4].result_id,
            offer_acceptance_id=acceptance["id"],
            artifact=ArtifactInput.from_receipt(artifact, role="PLAN"),
            created_by=OWNER,
        ),
        command_key=uuid4(),
    )
    run_request = ResearchRunRequest(
        plan_id=plan.result_id, provider_result_id=source.result_id, completed_by=OWNER
    )
    run_key = uuid4()
    run = await repo.complete_research_run(run_request, command_key=run_key)
    assert await repo.complete_research_run(run_request, command_key=run_key) == run
    qualifications = QualificationCohortRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW
    )
    original = dossier_request(acceptance, lead)
    reference = f"provider-result:{source.result_id}"
    evidence = original.evidence[0].model_copy(
        update={"source_ref": reference, "valid_until": NOW + timedelta(minutes=20)}
    )
    with pytest.raises(ProductRecordsDenied):
        await qualifications.record_dossier(
            original.model_copy(update={"evidence": (evidence,)}), command_key=uuid4()
        )
    async with governance_engine.connect() as c:
        assert await c.scalar(select(func.count()).select_from(q.evidence)) == 0
    evidence = evidence.model_copy(update={"excerpt": f"Retained source: {reference}"})
    dossier = await qualifications.record_dossier(
        original.model_copy(update={"evidence": (evidence,)}), command_key=uuid4()
    )
    link = ResearchEvidenceLinkRequest(
        run_id=run.result_id,
        dossier_id=dossier.id,
        dossier_evidence_id=dossier.evidence_ids[0],
        linked_by=OWNER,
    )
    link_key = uuid4()
    linked = await repo.link_research_evidence(link, command_key=link_key)
    assert await repo.link_research_evidence(link, command_key=link_key) == linked
    expired = ReadinessRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW + timedelta(minutes=31)
    )
    with pytest.raises(ProductRecordsDenied, match="STALE_CONTACT"):
        await expired.complete_research_run(run_request, command_key=uuid4())
    admin = GovernanceProvisioner(governance_engine)
    event = GrantEvent(
        event_id=uuid4(),
        grant_id=call["grant_id"],
        grant_version=call["grant_version"],
        kind=GrantEventKind.REVOKED,
        effective_at=NOW,
        actor_id=OWNER,
        evidence_ref=uuid4(),
    )
    await register(admin, event.evidence_ref, "GRANT_EVENT", NOW)
    await admin.grant_event(event)
    with pytest.raises(ProductRecordsDenied, match="SOURCE_RIGHTS"):
        await repo.record_provider_result(source_request, command_key=uuid4())
