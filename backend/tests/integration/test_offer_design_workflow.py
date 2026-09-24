"""Focused L04 Offer Design workflow state-machine coverage."""

import asyncio
import os
import signal
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text, update
from test_governance import seed as governance_seed
from test_market_research_outcomes import child_governance, governed_research
from test_offer_records import (
    RESEARCH_ROLES,
    complete_research,
    freeze_bundle,
    package_payload,
)
from test_product_record_guards import put
from test_product_records import artifact

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import EvidenceRecord
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    OfferDesignDecisionRequest,
    OfferDesignStartRequest,
    OfferGapRequest,
    OfferIdeaRefinementReturnRequest,
    OfferTargetedResearchReturnRequest,
    ProductRecordsDenied,
    ResearchCycleBudgetInput,
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
    QualificationCriterion,
)
from alon_ai.records.offers import OfferRecordsRepository
from alon_ai.workflows.market_research import DBOS_APPLICATION_VERSION
from alon_ai.workflows.offer_design import (
    OfferDesignDecisionWorkflowRequest,
    OfferDesignWorkflowRepository,
    OfferIdeaRefinementWorkflowRequest,
    OfferTargetedResearchWorkflowRequest,
    assert_offer_design_compatible_application_version,
    offer_design_decision_workflow_id,
    offer_idea_refinement_workflow_id,
)

pytestmark = pytest.mark.integration
HARNESS = Path(__file__).with_name("dbos_offer_design_harness.py")


def _dbos_environment(governance_engine) -> dict[str, str]:
    application = governance_engine.url.render_as_string(hide_password=False)
    system = governance_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    return {
        **os.environ,
        "ALON_AI_DATABASE_URL": application,
        "ALON_AI_DBOS_SYSTEM_DATABASE_URL": system,
        "ALON_AI_ENVIRONMENT": "test",
    }


def _migrate_dbos(governance_engine) -> None:
    system = governance_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("dbos")),
            "migrate",
            "--sys-db-url",
            system,
            "--schema",
            "dbos",
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def _wait_for(path: Path, process: asyncio.subprocess.Process) -> None:
    for _ in range(500):
        if path.exists():
            return
        if process.returncode is not None:
            stdout, stderr = await process.communicate()
            pytest.fail(f"workflow stopped early: {stdout.decode()}\n{stderr.decode()}")
        await asyncio.sleep(0.02)
    process.kill()
    await process.wait()
    pytest.fail("workflow did not reach its barrier")


def test_offer_design_workflow_entrypoint_is_available():
    assert callable(getattr(OfferRecordsRepository, "start_offer_design", None))


async def _started_offer_design_run(governance_engine, *, start: bool = True):
    _, _, _, config, _, _ = await governance_seed(governance_engine)
    context = await complete_research(governance_engine)
    offer_repo, bundle, bundle_artifact, inputs = await freeze_bundle(
        governance_engine, context
    )
    scope = next(item for item in inputs if item.role == "SCOPE_ESTIMATE")
    envelope_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
        {"status": "READY", "reason": "Deterministic operator constraints"},
        inputs=(
            ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
            scope,
        ),
    )
    await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    prompt = await put(
        context[0],
        context[1],
        ArtifactKind.OUTREACH_PROMPT_CONFIGURATION,
        {"template": "Use supplied research only."},
    )
    request = OfferDesignStartRequest(
        verdict_id=context[4].id,
        input_bundle=ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
        envelope=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
        scope_estimate=scope,
        prompt_configuration=ArtifactInput.from_receipt(prompt, role="PROMPT"),
        model_config_id=config.id,
        model_config_workflow_id=config.workflow_id,
        model_config_version=config.version,
        started_by=UUID(int=1),
    )
    command_key = uuid4()
    if not start:
        return offer_repo, context, prompt, None, request, command_key
    receipt = await offer_repo.start_offer_design(request, command_key=command_key)
    return offer_repo, context, prompt, receipt, request, command_key


async def _targeted_return_ready_run(governance_engine):
    (
        repo,
        admin,
        attr,
        config,
        agent_id,
        _cycle,
        _,
        idea,
        attempt,
        _,
        _,
        now,
    ) = await governed_research(governance_engine, "PROCEED_TO_OFFER")
    proof_id = uuid4()
    await GovernanceProvisioner(governance_engine).evidence(
        EvidenceRecord(
            id=proof_id,
            kind="CONTROL",
            mode="SYNTHETIC",
            registered_by=UUID(int=1),
            registered_at=now,
        )
    )
    source = SourceReference.governance_evidence(proof_id)
    evidence: list[ArtifactInput] = []
    for role in RESEARCH_ROLES:
        receipt = await repo.append_artifact(
            artifact(
                attr.experiment_id,
                ArtifactKind.RESEARCH_EVIDENCE,
                {"claim": role, "finding": f"Supported {role.lower()}"},
                workflow_id=attr.workflow_run_id,
                agent_id=agent_id,
            ),
            sources=(source,),
            command_key=uuid4(),
        )
        evidence.append(ArtifactInput.from_receipt(receipt, role=role))
    extras = (
        (
            ArtifactKind.COMPETITOR_PROFILE,
            "COMPETITOR_PROFILE",
            {"name": "Competitor", "positioning": "Manual alternative"},
        ),
        (
            ArtifactKind.SERVICE_PROFILE,
            "SERVICE_PROFILE",
            {"name": "Implementation", "scope": "Sixty-hour delivery"},
        ),
        (
            ArtifactKind.PRICE_OBSERVATION,
            "PRICE_OBSERVATION",
            {
                "status": "QUOTED",
                "currency": "ILS",
                "amount": "12000",
                "unit": "project",
                "source_note": "Published project quote",
            },
        ),
        (
            ArtifactKind.DELIVERY_SCOPE_ESTIMATE,
            "SCOPE_ESTIMATE",
            {"hours": "60", "basis": "Observed implementation scope"},
        ),
    )
    for kind, role, payload in extras:
        receipt = await repo.append_artifact(
            artifact(
                attr.experiment_id,
                kind,
                payload,
                workflow_id=attr.workflow_run_id,
                agent_id=agent_id,
            ),
            sources=(source,),
            command_key=uuid4(),
        )
        evidence.append(ArtifactInput.from_receipt(receipt, role=role))
    # The existing initial attempt already pins the accepted idea and plan.
    async with governance_engine.connect() as connection:
        plan_id = await connection.scalar(
            select(records.research_attempts.c.plan_artifact_id).where(
                records.research_attempts.c.id == attempt.id
            )
        )
        plan_row = (
            (
                await connection.execute(
                    select(records.artifacts).where(records.artifacts.c.id == plan_id)
                )
            )
            .mappings()
            .one()
        )
    initial_plan_input = ArtifactInput(
        artifact_id=plan_row["id"],
        kind=ArtifactKind.RESEARCH_PLAN,
        version=plan_row["version"],
        content_hash=plan_row["content_hash"],
        role="PLAN",
    )
    report = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.MARKET_RESEARCH_REPORT,
            {"finding": "Complete offer research", "limitations": ["Synthetic"]},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(initial_plan_input, *evidence),
        command_key=uuid4(),
    )
    recommendation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
            {
                "recommendation": "PROCEED_TO_OFFER",
                "rationale": "All required categories have exact evidence",
            },
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
        command_key=uuid4(),
    )
    verdict = await repo.commit_market_research_outcome(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="PROCEED_TO_OFFER",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    bundle_artifact = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE,
            {"status": "FROZEN"},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
            *evidence,
        ),
        command_key=uuid4(),
    )
    offer_repo = OfferRecordsRepository(governance_engine, clock=lambda: now)
    bundle = await offer_repo.freeze_input_bundle(
        ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
        verdict_id=verdict.id,
        command_key=uuid4(),
    )
    scope = next(item for item in evidence if item.role == "SCOPE_ESTIMATE")
    envelope_artifact = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
            {"status": "READY", "reason": "Deterministic operator constraints"},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(
            ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
            scope,
        ),
        command_key=uuid4(),
    )
    envelope = await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    prompt = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.OUTREACH_PROMPT_CONFIGURATION,
            {"template": "Use supplied research only."},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        command_key=uuid4(),
    )
    run = await offer_repo.start_offer_design(
        OfferDesignStartRequest(
            verdict_id=verdict.id,
            input_bundle=ArtifactInput.from_receipt(
                bundle_artifact, role="INPUT_BUNDLE"
            ),
            envelope=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            scope_estimate=scope,
            prompt_configuration=ArtifactInput.from_receipt(prompt, role="PROMPT"),
            model_config_id=config.id,
            model_config_workflow_id=config.workflow_id,
            model_config_version=config.version,
            started_by=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    proposal_artifact = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.OFFER_DESIGN_PROPOSAL,
            package_payload(),
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(
            ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
            ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
        ),
        command_key=uuid4(),
    )
    proposal = await offer_repo.register_proposal(
        ArtifactInput.from_receipt(proposal_artifact, role="PROPOSAL"),
        bundle_id=bundle.id,
        envelope_id=envelope.id,
        offer_design_run_id=run.id,
        command_key=uuid4(),
    )
    return (
        offer_repo,
        repo,
        admin,
        attr,
        config,
        agent_id,
        idea,
        run,
        proposal,
        prompt,
        now,
    )


async def _targeted_return_request(governance_engine):
    (
        offer_repo,
        repo,
        admin,
        attr,
        config,
        _agent_id,
        idea,
        run,
        proposal,
        prompt,
        now,
    ) = await _targeted_return_ready_run(governance_engine)
    workflow_id, workflow_agent_id, child_config, account = await child_governance(
        governance_engine, admin, attr, config, now
    )
    async with governance_engine.begin() as connection:
        await connection.execute(
            update(gov.budget_accounts)
            .where(gov.budget_accounts.c.id == account)
            .values(limit=Decimal(100))
        )
    async with governance_engine.connect() as connection:
        run_row = (
            (
                await connection.execute(
                    select(offers.offer_design_runs).where(
                        offers.offer_design_runs.c.id == run.id
                    )
                )
            )
            .mappings()
            .one()
        )
        proposal_row = (
            (
                await connection.execute(
                    select(offers.offer_proposals).where(
                        offers.offer_proposals.c.id == proposal.id
                    )
                )
            )
            .mappings()
            .one()
        )
        bundle_row = (
            (
                await connection.execute(
                    select(offers.offer_bundles).where(
                        offers.offer_bundles.c.id == proposal.bundle_id
                    )
                )
            )
            .mappings()
            .one()
        )
        verdict_row = (
            (
                await connection.execute(
                    select(records.verdicts).where(
                        records.verdicts.c.id == run_row["verdict_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        report_row, recommendation_row = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id.in_(
                            (
                                verdict_row["report_artifact_id"],
                                verdict_row["recommendation_artifact_id"],
                            )
                        )
                    )
                )
            )
            .mappings()
            .all()
        )
        if report_row["id"] != verdict_row["report_artifact_id"]:
            report_row, recommendation_row = recommendation_row, report_row
    gap = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.OFFER_RESEARCH_GAP_BRIEF,
            {
                "required_evidence": ["PRICE_OBSERVATION"],
                "justification": "Price evidence is contradictory.",
            },
            workflow_id=workflow_id,
            agent_id=workflow_agent_id,
        ),
        inputs=(
            ArtifactInput(
                artifact_id=proposal_row["artifact_id"],
                kind=ArtifactKind(proposal_row["artifact_kind"]),
                version=proposal_row["artifact_version"],
                content_hash=proposal_row["artifact_hash"],
                role="ORIGINATING_PROPOSAL",
            ),
            ArtifactInput(
                artifact_id=bundle_row["artifact_id"],
                kind=ArtifactKind(bundle_row["artifact_kind"]),
                version=bundle_row["artifact_version"],
                content_hash=bundle_row["artifact_hash"],
                role="OFFER_INPUT_BUNDLE",
            ),
            ArtifactInput(
                artifact_id=report_row["id"],
                kind=ArtifactKind(report_row["kind"]),
                version=report_row["version"],
                content_hash=report_row["content_hash"],
                role="REPORT",
            ),
            ArtifactInput(
                artifact_id=recommendation_row["id"],
                kind=ArtifactKind(recommendation_row["kind"]),
                version=recommendation_row["version"],
                content_hash=recommendation_row["content_hash"],
                role="RECOMMENDATION",
            ),
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        ),
        command_key=uuid4(),
    )
    validation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {
                "validator": "offer-gap-v1",
                "disposition": "PASS",
                "reason": "Exact named gap is reviewable.",
            },
            workflow_id=workflow_id,
            agent_id=workflow_agent_id,
        ),
        inputs=(ArtifactInput.from_receipt(gap, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(gap, role="TARGET"),
        experiment_id=attr.experiment_id,
        disposition="ACCEPTED",
        validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    plan = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {
                "questions": ["What exact price evidence closes the gap?"],
                "method": "Targeted",
            },
            workflow_id=workflow_id,
            agent_id=workflow_agent_id,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(gap, role="RETURN_FEEDBACK"),
        ),
        command_key=uuid4(),
    )
    request = OfferTargetedResearchReturnRequest(
        run_id=run.id,
        proposal_id=proposal.id,
        decision_artifact=ArtifactInput.from_receipt(prompt, role="DECISION"),
        gap=OfferGapRequest(
            artifact=ArtifactInput.from_receipt(gap, role="GAP"),
            proposal_id=proposal.id,
            missing_fields=("base_price",),
            required_source_types=("PRICE_OBSERVATION",),
            targeted_questions=("What exact price evidence closes the gap?",),
        ),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        budget=ResearchCycleBudgetInput(
            workflow_id=workflow_id,
            config_id=child_config.id,
            config_version=child_config.version,
            budget_account_id=account,
            max_search_results=10,
            max_capture_pages=10,
            max_openai_calls=10,
        ),
        operator_id=UUID(int=1),
        accepted_by=UUID(int=1),
    )
    return offer_repo, repo, attr, run, request


async def test_current_proceed_starts_one_pinned_offer_design_run(governance_engine):
    (
        offer_repo,
        _,
        prompt,
        receipt,
        request,
        command_key,
    ) = await _started_offer_design_run(governance_engine)
    assert receipt is not None
    assert receipt.bundle_id
    assert receipt.envelope_id
    assert (
        await offer_repo.start_offer_design(request, command_key=command_key) == receipt
    )
    decision_request = OfferDesignDecisionRequest(
        run_id=receipt.id,
        outcome="IDEA_REFINEMENT_RECOMMENDED",
        decision_artifact=ArtifactInput.from_receipt(prompt, role="DECISION"),
        operator_id=UUID(int=1),
    )
    workflow_request = OfferDesignDecisionWorkflowRequest(
        request=decision_request, command_key=uuid4()
    )
    runtime = OfferDesignWorkflowRepository(governance_engine)
    binding = await runtime.bind(workflow_request, application_version="l04-test")
    assert (
        await runtime.bind(workflow_request, application_version="l04-test") == binding
    )
    with pytest.raises(ProductRecordsDenied, match="WORKFLOW_BINDING_CONFLICT"):
        await runtime.bind(
            workflow_request.model_copy(
                update={
                    "request": decision_request.model_copy(
                        update={"operator_id": uuid4()}
                    )
                }
            ),
            application_version="l04-test",
        )
    decision = await offer_repo.decide_offer_design(
        decision_request, command_key=workflow_request.command_key
    )
    assert decision.outcome == "IDEA_REFINEMENT_RECOMMENDED"
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == receipt.cycle_id
                )
            )
            == "WAITING_FOR_OPERATOR_INPUT"
        )


async def test_offer_design_start_rejects_mismatched_and_superseded_envelopes(
    governance_engine,
):
    offer_repo, context, _, _, request, _ = await _started_offer_design_run(
        governance_engine, start=False
    )
    with pytest.raises(ProductRecordsDenied, match="EXACT_ARTIFACT"):
        await offer_repo.start_offer_design(
            request.model_copy(
                update={
                    "envelope": request.envelope.model_copy(
                        update={"content_hash": "0" * 64}
                    )
                }
            ),
            command_key=uuid4(),
        )
    old = request.envelope
    # A newer envelope version preserves the immutable predecessor lineage.
    async with governance_engine.connect() as connection:
        current = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == old.artifact_id
                    )
                )
            )
            .mappings()
            .one()
        )
    newer = await context[0].append_artifact(
        artifact(
            context[1],
            ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
            {"status": "READY", "reason": "Newer envelope version"},
            logical_id=current["logical_id"],
            version=current["version"] + 1,
        ),
        inputs=(
            ArtifactInput(
                artifact_id=current["id"],
                kind=ArtifactKind(current["kind"]),
                version=current["version"],
                content_hash=current["content_hash"],
                role="SUPERSEDES",
            ),
        ),
        command_key=uuid4(),
    )
    assert newer.version == old.version + 1
    with pytest.raises(ProductRecordsDenied, match="STALE_INPUT"):
        await offer_repo.start_offer_design(request, command_key=uuid4())


async def test_targeted_research_return_is_atomic_and_replays_exact_roles(
    governance_engine,
):
    offer_repo, _, _, run, request = await _targeted_return_request(governance_engine)
    command_key = uuid4()
    receipt = await offer_repo.return_for_targeted_research(
        request, command_key=command_key
    )
    assert (
        await offer_repo.return_for_targeted_research(request, command_key=command_key)
        == receipt
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == run.cycle_id
                )
            )
            == "RETURN_FOR_TARGETED_RESEARCH"
        )
        assert (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == receipt.child_cycle_id
                )
            )
            == "MARKET_RESEARCH"
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.commands)
                .where(records.commands.c.command_key == command_key)
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.audit)
                .join(
                    records.commands,
                    records.audit.c.command_id == records.commands.c.id,
                )
                .where(records.commands.c.command_key == command_key)
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.outbox)
                .join(
                    records.commands,
                    records.outbox.c.command_id == records.commands.c.id,
                )
                .where(records.commands.c.command_key == command_key)
            )
            == 1
        )
    with pytest.raises(ProductRecordsDenied, match="OFFER_TARGETED_RETURN_LIMIT"):
        await offer_repo.return_for_targeted_research(request, command_key=uuid4())
    async with governance_engine.connect() as connection:
        run_row = (
            (
                await connection.execute(
                    select(offers.offer_design_runs).where(
                        offers.offer_design_runs.c.id == run.id
                    )
                )
            )
            .mappings()
            .one()
        )
        envelope_row = (
            (
                await connection.execute(
                    select(offers.commercial_envelopes).where(
                        offers.commercial_envelopes.c.id == run_row["envelope_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        artifact_rows = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id.in_(
                            (
                                run_row["prompt_artifact_id"],
                                envelope_row["scope_artifact_id"],
                                envelope_row["artifact_id"],
                                run_row["bundle_id"],
                            )
                        )
                    )
                )
            )
            .mappings()
            .all()
        )
        bundle_row = (
            (
                await connection.execute(
                    select(offers.offer_bundles).where(
                        offers.offer_bundles.c.id == run_row["bundle_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        artifact_rows += (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == bundle_row["artifact_id"]
                    )
                )
            )
            .mappings()
            .all()
        )
    by_id = {row["id"]: row for row in artifact_rows}

    def pinned(artifact_id, role):
        row = by_id[artifact_id]
        return ArtifactInput(
            artifact_id=row["id"],
            kind=ArtifactKind(row["kind"]),
            version=row["version"],
            content_hash=row["content_hash"],
            role=role,
        )

    with pytest.raises(ProductRecordsDenied, match="STALE_PROCEED"):
        await offer_repo.start_offer_design(
            OfferDesignStartRequest(
                verdict_id=run_row["verdict_id"],
                input_bundle=pinned(bundle_row["artifact_id"], "INPUT_BUNDLE"),
                envelope=pinned(envelope_row["artifact_id"], "ENVELOPE"),
                scope_estimate=pinned(
                    envelope_row["scope_artifact_id"], "SCOPE_ESTIMATE"
                ),
                prompt_configuration=pinned(run_row["prompt_artifact_id"], "PROMPT"),
                model_config_id=run_row["model_config_id"],
                model_config_workflow_id=run_row["model_config_workflow_id"],
                model_config_version=run_row["model_config_version"],
                started_by=run_row["started_by"],
            ),
            command_key=uuid4(),
        )


async def test_targeted_research_return_rolls_back_without_partial_graph(
    governance_engine,
):
    offer_repo, _, _, _, request = await _targeted_return_request(governance_engine)
    tables = (
        records.cycles,
        records.research_cycle_budgets,
        records.research_attempts,
        records.cycle_transitions,
        records.returns,
        records.commands,
        records.audit,
        records.outbox,
    )
    async with governance_engine.connect() as connection:
        before = []
        for table in tables:
            before.append(
                await connection.scalar(select(func.count()).select_from(table))
            )
    with pytest.raises(ProductRecordsDenied, match="BUDGET_EXHAUSTED"):
        await offer_repo.return_for_targeted_research(
            request.model_copy(
                update={
                    "budget": request.budget.model_copy(
                        update={"max_search_results": 0}
                    )
                }
            ),
            command_key=uuid4(),
        )
    async with governance_engine.connect() as connection:
        after = []
        for table in tables:
            after.append(
                await connection.scalar(select(func.count()).select_from(table))
            )
    assert after == before


async def _operator_refinement_request(
    governance_engine,
):
    offer_repo, context, prompt, run, _, _ = await _started_offer_design_run(
        governance_engine
    )
    assert run is not None
    decision = await offer_repo.decide_offer_design(
        OfferDesignDecisionRequest(
            run_id=run.id,
            outcome="IDEA_REFINEMENT_RECOMMENDED",
            decision_artifact=ArtifactInput.from_receipt(prompt, role="DECISION"),
            operator_id=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    async with governance_engine.connect() as connection:
        current = (
            (
                await connection.execute(
                    select(records.artifacts)
                    .join(
                        records.idea_acceptances,
                        records.idea_acceptances.c.artifact_id
                        == records.artifacts.c.id,
                    )
                    .where(records.idea_acceptances.c.cycle_id == run.cycle_id)
                )
            )
            .mappings()
            .one()
        )
    proposed = await context[0].append_artifact(
        artifact(
            context[1],
            ArtifactKind.IDEA_BRIEF,
            {
                **current["payload"],
                "title": "Service refined by operator",
                "material_pivot": False,
            },
            logical_id=current["logical_id"],
            version=current["version"] + 1,
        ),
        inputs=(
            ArtifactInput(
                artifact_id=current["id"],
                kind=ArtifactKind(current["kind"]),
                version=current["version"],
                content_hash=current["content_hash"],
                role="SUPERSEDES",
            ),
        ),
        command_key=uuid4(),
    )
    validation = await context[0].append_artifact(
        artifact(
            context[1],
            ArtifactKind.VALIDATION_RESULT,
            {"validator": "idea-v1", "disposition": "PASS", "reason": "Exact"},
        ),
        inputs=(ArtifactInput.from_receipt(proposed, role="TARGET"),),
        command_key=uuid4(),
    )
    await context[0].record_disposition(
        ArtifactInput.from_receipt(proposed, role="TARGET"),
        experiment_id=context[1],
        disposition="VALIDATED",
        validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    request = OfferIdeaRefinementReturnRequest(
        run_id=run.id,
        decision_id=decision.id,
        commercial_failure_evidence=ArtifactInput.from_receipt(prompt, role="FAILURE"),
        proposed_idea=ArtifactInput.from_receipt(proposed, role="NEXT_IDEA"),
        accepted_by=UUID(int=1),
    )
    return offer_repo, run, request, prompt


async def test_operator_confirmed_refinement_uses_only_the_supplied_validated_idea(
    governance_engine,
):
    offer_repo, _, request, prompt = await _operator_refinement_request(
        governance_engine
    )
    key = uuid4()
    receipt = await offer_repo.confirm_offer_idea_refinement(request, command_key=key)
    assert (
        await offer_repo.confirm_offer_idea_refinement(request, command_key=key)
        == receipt
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await offer_repo.confirm_offer_idea_refinement(
            request.model_copy(update={"accepted_by": uuid4()}), command_key=key
        )
    with pytest.raises(ProductRecordsDenied, match="OPERATOR_CONFIRMATION_REQUIRED"):
        await offer_repo.confirm_offer_idea_refinement(
            request.model_copy(
                update={
                    "proposed_idea": ArtifactInput.from_receipt(
                        prompt, role="NEXT_IDEA"
                    )
                }
            ),
            command_key=uuid4(),
        )


@pytest.mark.parametrize("barrier", ("before-business", "after-business"))
async def test_dbos_offer_decision_crash_replays_one_receipt(
    governance_engine, tmp_path, barrier
):
    _, _, prompt, run, _, _ = await _started_offer_design_run(governance_engine)
    assert run is not None
    request = OfferDesignDecisionWorkflowRequest(
        request=OfferDesignDecisionRequest(
            run_id=run.id,
            outcome="WAITING_FOR_OPERATOR_INPUT",
            decision_artifact=ArtifactInput.from_receipt(prompt, role="DECISION"),
            operator_id=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    request_path = tmp_path / "offer-decision.json"
    request_path.write_text(request.model_dump_json(exclude_computed_fields=True))
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    command = [
        sys.executable,
        str(HARNESS),
        "start",
        "--request",
        str(request_path),
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=Path(__file__).parents[2],
        env={
            **_dbos_environment(governance_engine),
            "ALON_AI_OFFER_DBOS_TEST_BARRIER": barrier,
            "ALON_AI_OFFER_DBOS_TEST_READY": str(ready),
            "ALON_AI_OFFER_DBOS_TEST_RELEASE": str(release),
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for(ready, process)
    process.send_signal(signal.SIGKILL)
    await asyncio.wait_for(process.wait(), timeout=10)
    recovered = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(HARNESS), "recover", "--request", str(request_path)],
        cwd=Path(__file__).parents[2],
        env=_dbos_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert recovered.returncode == 0, recovered.stderr
    workflow_id = offer_design_decision_workflow_id(run.id, request.command_key)
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.commands)
                .where(records.commands.c.kind == "DECIDE_OFFER_DESIGN")
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(offers.offer_design_workflow_bindings.c.delivery_state).where(
                    offers.offer_design_workflow_bindings.c.dbos_workflow_id
                    == workflow_id
                )
            )
            == "RUNTIME_COMPLETED"
        )


@pytest.mark.parametrize("operation", ("TARGETED", "REFINEMENT"))
@pytest.mark.parametrize("barrier", ("before-business", "after-business"))
async def test_dbos_offer_return_crash_recovers_original_command(
    governance_engine, tmp_path, operation, barrier
):
    if operation == "TARGETED":
        _, _, _, run, business_request = await _targeted_return_request(
            governance_engine
        )
        # The shared fixture pins its clock to September 12; the DBOS process
        # uses the real clock and needs a genuinely active governed budget.
        async with governance_engine.begin() as connection:
            await connection.execute(
                update(gov.budget_accounts)
                .where(
                    gov.budget_accounts.c.id
                    == business_request.budget.budget_account_id
                )
                .values(expires_at=func.now() + text("INTERVAL '30 days'"))
            )
        workflow_request = OfferTargetedResearchWorkflowRequest(
            request=business_request, command_key=uuid4()
        )
        workflow_id = offer_design_decision_workflow_id(
            run.id, workflow_request.command_key
        )
    else:
        _, run, business_request, _ = await _operator_refinement_request(
            governance_engine
        )
        workflow_request = OfferIdeaRefinementWorkflowRequest(
            request=business_request, command_key=uuid4()
        )
        workflow_id = offer_idea_refinement_workflow_id(
            business_request.decision_id, workflow_request.command_key
        )
    request_path = tmp_path / "offer-return.json"
    request_path.write_text(
        workflow_request.model_dump_json(exclude_computed_fields=True)
    )
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(HARNESS),
        "start",
        "--request",
        str(request_path),
        cwd=Path(__file__).parents[2],
        env={
            **_dbos_environment(governance_engine),
            "ALON_AI_OFFER_DBOS_TEST_BARRIER": barrier,
            "ALON_AI_OFFER_DBOS_TEST_READY": str(ready),
            "ALON_AI_OFFER_DBOS_TEST_RELEASE": str(release),
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for(ready, process)
    process.send_signal(signal.SIGKILL)
    await asyncio.wait_for(process.wait(), timeout=10)
    recovered = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(HARNESS), "recover", "--request", str(request_path)],
        cwd=Path(__file__).parents[2],
        env=_dbos_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert recovered.returncode == 0, recovered.stderr
    runtime = OfferDesignWorkflowRepository(governance_engine)
    with pytest.raises(ProductRecordsDenied, match="WORKFLOW_BINDING_CONFLICT"):
        await runtime.bind(
            workflow_request.model_copy(
                update={
                    "request": business_request.model_copy(
                        update={"accepted_by": uuid4()}
                    )
                }
            ),
            application_version=DBOS_APPLICATION_VERSION,
        )
    async with governance_engine.connect() as connection:
        binding = (
            (
                await connection.execute(
                    select(offers.offer_design_workflow_bindings).where(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert binding["delivery_state"] == "RUNTIME_COMPLETED"
        assert binding["command_id"] is not None
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.commands)
                .where(records.commands.c.command_key == workflow_request.command_key)
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.audit)
                .where(records.audit.c.command_id == binding["command_id"])
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.outbox)
                .where(records.outbox.c.command_id == binding["command_id"])
            )
            == 1
        )


async def test_dbos_offer_decision_cancellation_and_version_conflict_leave_no_graph(
    governance_engine,
):
    _, _, prompt, run, _, _ = await _started_offer_design_run(governance_engine)
    assert run is not None
    request = OfferDesignDecisionWorkflowRequest(
        request=OfferDesignDecisionRequest(
            run_id=run.id,
            outcome="WAITING_FOR_OPERATOR_INPUT",
            decision_artifact=ArtifactInput.from_receipt(prompt, role="DECISION"),
            operator_id=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    runtime = OfferDesignWorkflowRepository(governance_engine)
    binding = await runtime.bind(request, application_version="l04-offer-v1")
    await runtime.cancel(binding.dbos_workflow_id)
    with pytest.raises(ProductRecordsDenied, match="WORKFLOW_CANCELLED"):
        await runtime.start(request, application_version="l04-offer-v1")
    async with governance_engine.connect() as connection:
        assert not await connection.scalar(
            select(records.commands.c.id).where(
                records.commands.c.kind == "DECIDE_OFFER_DESIGN"
            )
        )
    incompatible = await runtime.bind(
        request.model_copy(update={"command_key": uuid4()}),
        application_version="l04-offer-v2",
    )
    assert incompatible.delivery_state == "PENDING"
    with pytest.raises(RuntimeError, match="DBOS_APPLICATION_VERSION_MISMATCH"):
        await assert_offer_design_compatible_application_version(
            governance_engine, "l04-offer-v1"
        )


async def test_dbos_late_cancellation_is_ineffective_and_remains_recoverable(
    governance_engine, tmp_path
):
    _, _, prompt, run, _, _ = await _started_offer_design_run(governance_engine)
    assert run is not None
    request = OfferDesignDecisionWorkflowRequest(
        request=OfferDesignDecisionRequest(
            run_id=run.id,
            outcome="WAITING_FOR_OPERATOR_INPUT",
            decision_artifact=ArtifactInput.from_receipt(prompt, role="DECISION"),
            operator_id=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    request_path = tmp_path / "late-cancel.json"
    request_path.write_text(request.model_dump_json(exclude_computed_fields=True))
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(HARNESS),
        "start",
        "--request",
        str(request_path),
        cwd=Path(__file__).parents[2],
        env={
            **_dbos_environment(governance_engine),
            "ALON_AI_OFFER_DBOS_TEST_BARRIER": "after-business",
            "ALON_AI_OFFER_DBOS_TEST_READY": str(ready),
            "ALON_AI_OFFER_DBOS_TEST_RELEASE": str(release),
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for(ready, process)
    workflow_id = offer_design_decision_workflow_id(run.id, request.command_key)
    assert (
        await OfferDesignWorkflowRepository(governance_engine).cancel(workflow_id)
        == "INEFFECTIVE_ALREADY_COMMITTED"
    )
    release.touch()
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    assert process.returncode == 0, f"{stdout.decode()}\n{stderr.decode()}"
    async with governance_engine.connect() as connection:
        binding = (
            (
                await connection.execute(
                    select(
                        offers.offer_design_workflow_bindings.c.delivery_state,
                        offers.offer_design_workflow_bindings.c.cancellation_outcome,
                    ).where(
                        offers.offer_design_workflow_bindings.c.dbos_workflow_id
                        == workflow_id
                    )
                )
            )
            .mappings()
            .one()
        )
    assert binding == {
        "delivery_state": "RUNTIME_COMPLETED",
        "cancellation_outcome": "INEFFECTIVE_ALREADY_COMMITTED",
    }


async def test_offer_design_acceptance_commits_one_package_graph_and_transition(
    governance_engine,
):
    _, _, _, config, _, _ = await governance_seed(governance_engine)
    context = await complete_research(governance_engine)
    offer_repo, bundle, bundle_artifact, inputs = await freeze_bundle(
        governance_engine, context
    )
    scope = next(item for item in inputs if item.role == "SCOPE_ESTIMATE")
    envelope_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE,
        {"status": "READY", "reason": "Deterministic operator constraints"},
        inputs=(
            ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
            scope,
        ),
    )
    envelope = await offer_repo.derive_commercial_envelope(
        CommercialEnvelopeRequest(
            artifact=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            bundle_id=bundle.id,
            scope_estimate=scope,
        ),
        command_key=uuid4(),
    )
    prompt = await put(
        context[0],
        context[1],
        ArtifactKind.OUTREACH_PROMPT_CONFIGURATION,
        {"template": "Use supplied research only."},
    )
    run = await offer_repo.start_offer_design(
        OfferDesignStartRequest(
            verdict_id=context[4].id,
            input_bundle=ArtifactInput.from_receipt(
                bundle_artifact, role="INPUT_BUNDLE"
            ),
            envelope=ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
            scope_estimate=scope,
            prompt_configuration=ArtifactInput.from_receipt(prompt, role="PROMPT"),
            model_config_id=config.id,
            model_config_workflow_id=config.workflow_id,
            model_config_version=config.version,
            started_by=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    proposal_artifact = await put(
        context[0],
        context[1],
        ArtifactKind.OFFER_DESIGN_PROPOSAL,
        package_payload(),
        inputs=(
            ArtifactInput.from_receipt(bundle_artifact, role="INPUT_BUNDLE"),
            ArtifactInput.from_receipt(envelope_artifact, role="ENVELOPE"),
        ),
    )
    proposal = await offer_repo.register_proposal(
        ArtifactInput.from_receipt(proposal_artifact, role="PROPOSAL"),
        bundle_id=bundle.id,
        envelope_id=envelope.id,
        offer_design_run_id=run.id,
        command_key=uuid4(),
    )
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
    decision = await put(
        context[0],
        context[1],
        ArtifactKind.VALIDATION_RESULT,
        {
            "validator": "offer-design-acceptance-v1",
            "disposition": "PASS",
            "reason": "Operator accepted supplied package.",
        },
        inputs=(
            ArtifactInput.from_receipt(proposal_artifact, role="OFFER_DESIGN_PROPOSAL"),
            ArtifactInput.from_receipt(package, role="OFFER_PACKAGE"),
            ArtifactInput.from_receipt(profile, role="OFFER_QUALIFICATION_PROFILE"),
            ArtifactInput.from_receipt(policy, role="INITIAL_OUTREACH_POLICY"),
        ),
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
                Literal[
                    "CURRENCY",
                    "DELIVERY_CAPACITY",
                    "HOURLY_COST",
                    "MINIMUM_PRICE",
                    "MINIMUM_MARGIN_RATE",
                    "MAXIMUM_DISCOUNT_RATE",
                    "MINIMUM_DEPOSIT_RATE",
                ]
                | None,
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
            required_evidence_kind="RESEARCH_EVIDENCE",
            unknown_behavior=(
                "NOT_APPLICABLE" if category == "POSITIVE_SIGNAL" else "BLOCK"
            ),
        )
        for index, category in enumerate(REQUIRED_QUALIFICATION_CATEGORIES, 1)
    )
    acceptance_request = OfferAcceptanceRequest(
        package=ArtifactInput.from_receipt(package, role="OFFER"),
        proposal_id=proposal.id,
        qualification_profile=ArtifactInput.from_receipt(profile, role="PROFILE"),
        criteria=criteria,
        outreach_policy=ArtifactInput.from_receipt(policy, role="POLICY"),
        field_sources=field_sources,
        accepted_by=UUID(int=1),
    )
    unrelated_pass = await put(
        context[0],
        context[1],
        ArtifactKind.VALIDATION_RESULT,
        {"validator": "other-run", "disposition": "PASS", "reason": "Unrelated"},
    )
    with pytest.raises(ProductRecordsDenied, match="DECISION_LINEAGE"):
        await offer_repo.accept_offer(
            acceptance_request,
            offer_design_run_id=run.id,
            decision_artifact=ArtifactInput.from_receipt(
                unrelated_pass, role="DECISION"
            ),
            command_key=uuid4(),
        )
    accepted = await offer_repo.accept_offer(
        acceptance_request,
        offer_design_run_id=run.id,
        decision_artifact=ArtifactInput.from_receipt(decision, role="DECISION"),
        command_key=uuid4(),
    )
    assert accepted.bundle_id == bundle.id
