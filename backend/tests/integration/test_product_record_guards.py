"""Raw PostgreSQL regressions for the product record authority boundaries."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError
from test_product_records import NOW, accept_feedback, artifact, roots

from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
    SourceReference,
)
from alon_ai.records import schema as records

pytestmark = pytest.mark.integration


async def put(repo, experiment_id, kind, payload, **kwargs):
    return await repo.append_artifact(
        artifact(experiment_id, kind, payload), command_key=uuid4(), **kwargs
    )


async def cycle_fixture(engine, *, accept=True):
    repo, _, experiment_id, _, _ = await roots(engine)
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
    if accept:
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
    return repo, experiment_id, seed, cycle, idea, plan


@pytest.mark.parametrize("parent", [False, True])
async def test_create_cycle_cannot_bypass_committed_return(governance_engine, parent):
    repo, experiment_id, seed, cycle, _, _ = await cycle_fixture(governance_engine)
    with pytest.raises(ProductRecordsDenied):
        await repo.create_cycle(
            experiment_id,
            seed=ArtifactInput.from_receipt(seed, role="SEED"),
            parent_cycle_id=cycle.id if parent else None,
            command_key=uuid4(),
        )


async def test_cycle_replay_rejects_changed_request_and_other_experiment(
    governance_engine,
):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    seed = await put(
        repo,
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Seed."},
    )
    key = uuid4()
    original = await repo.create_cycle(
        experiment_id,
        seed=ArtifactInput.from_receipt(seed, role="SEED"),
        command_key=key,
    )
    assert (
        await repo.create_cycle(
            experiment_id,
            seed=ArtifactInput.from_receipt(seed, role="SEED"),
            command_key=key,
        )
        == original
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.create_cycle(
            experiment_id,
            seed=ArtifactInput.from_receipt(seed, role="SEED"),
            parent_cycle_id=uuid4(),
            command_key=key,
        )
    _, _, other, _, _ = await roots(governance_engine)
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.create_cycle(
            other, seed=ArtifactInput.from_receipt(seed, role="SEED"), command_key=key
        )


async def test_append_replay_compares_exact_input_set(governance_engine):
    repo, experiment_id, seed, _, _, _ = await cycle_fixture(governance_engine)
    draft = artifact(
        experiment_id,
        ArtifactKind.SERVICE_PROFILE,
        {"name": "Service", "scope": "Scope"},
    )
    key = uuid4()
    await repo.append_artifact(draft, command_key=key)
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.append_artifact(
            draft,
            inputs=(ArtifactInput.from_receipt(seed, role="INPUT"),),
            command_key=key,
        )


@pytest.mark.parametrize(
    "target",
    ["seed", "idea", "plan", "report", "recommendation", "feedback", "ancestor"],
)
@pytest.mark.parametrize("late_source", [False, True])
async def test_authoritative_receipts_close_artifact_lineage(
    governance_engine, target, late_source
):
    repo, experiment_id, seed, cycle, idea, plan = await cycle_fixture(
        governance_engine
    )
    attempt = await repo.start_research_attempt(
        cycle.id, ArtifactInput.from_receipt(plan, role="PLAN"), command_key=uuid4()
    )
    ancestor = await put(
        repo,
        experiment_id,
        ArtifactKind.SERVICE_PROFILE,
        {"name": "Service", "scope": "Scope"},
    )
    report = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "More refinement needed.", "limitations": ["Fixture"]},
        inputs=(
            ArtifactInput.from_receipt(plan, role="PLAN"),
            ArtifactInput.from_receipt(ancestor, role="INPUT"),
        ),
    )
    recommendation = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {"recommendation": "REFINE_SAME_IDEA", "rationale": "Refine buyer"},
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
    )
    verdict = await repo.commit_verdict(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="REFINE_SAME_IDEA",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    feedback = await put(
        repo,
        experiment_id,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        {"preserve": ["Intent"], "change": ["Buyer"]},
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
    )
    await accept_feedback(repo, experiment_id, feedback)
    await repo.return_to_refinement(
        verdict.id,
        feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        command_key=uuid4(),
    )
    target_id = {
        "seed": seed,
        "idea": idea,
        "plan": plan,
        "report": report,
        "recommendation": recommendation,
        "feedback": feedback,
        "ancestor": ancestor,
    }[target].artifact_id
    late = await put(
        repo,
        experiment_id,
        ArtifactKind.SERVICE_PROFILE,
        {"name": "Later", "scope": "Scope"},
    )
    if late_source:
        from test_governance import register

        from alon_ai.accounting.repository import GovernanceProvisioner

        evidence_id = uuid4()
        await register(
            GovernanceProvisioner(governance_engine), evidence_id, "CONTROL", NOW
        )
        with pytest.raises(SQLAlchemyError, match="lineage is closed"):
            async with governance_engine.begin() as connection:
                await connection.execute(
                    insert(records.source_refs).values(
                        id=uuid4(),
                        artifact_id=target_id,
                        experiment_id=experiment_id,
                        kind="GOVERNANCE_EVIDENCE",
                        evidence_id=evidence_id,
                    )
                )
        return
    with pytest.raises(SQLAlchemyError, match="lineage is closed"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.artifact_links).values(
                    consumer_id=target_id,
                    producer_id=late.artifact_id,
                    experiment_id=experiment_id,
                    role="LATE_INPUT",
                    producer_kind=late.kind,
                    producer_version=late.version,
                    producer_hash=late.content_hash,
                )
            )


async def test_raw_attempt_requires_accepted_idea(governance_engine):
    _, experiment_id, _, cycle, _, plan = await cycle_fixture(
        governance_engine, accept=False
    )
    with pytest.raises(SQLAlchemyError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.research_attempts).values(
                    id=uuid4(),
                    experiment_id=experiment_id,
                    cycle_id=cycle.id,
                    ordinal=1,
                    plan_artifact_id=plan.artifact_id,
                    plan_kind=plan.kind,
                    plan_version=plan.version,
                    plan_hash=plan.content_hash,
                    created_at=NOW,
                )
            )


async def test_unrelated_validation_cannot_accept_artifact(governance_engine):
    repo, experiment_id, _, _, idea, plan = await cycle_fixture(governance_engine)
    validation = await put(
        repo,
        experiment_id,
        ArtifactKind.VALIDATION_RESULT,
        {"validator": "fixture", "disposition": "PASS", "reason": "Valid plan"},
        inputs=(ArtifactInput.from_receipt(plan, role="TARGET"),),
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.record_disposition(
            ArtifactInput.from_receipt(idea, role="TARGET"),
            experiment_id=experiment_id,
            disposition="ACCEPTED",
            validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
            decided_by=UUID(int=1),
            command_key=uuid4(),
        )


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        ("IDEA_SEED", {"origin": None, "statement": "Seed"}),
        (
            "MARKET_RESEARCH_RECOMMENDATION",
            {"recommendation": None, "rationale": "Reason"},
        ),
        (
            "VALIDATION_RESULT",
            {"validator": "fixture", "disposition": None, "reason": "Reason"},
        ),
    ],
)
async def test_raw_null_enum_payload_fails_closed(governance_engine, kind, payload):
    _, _, experiment_id, _, _ = await roots(governance_engine)
    with pytest.raises(SQLAlchemyError, match="invalid artifact payload"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.artifacts).values(
                    id=uuid4(),
                    logical_id=uuid4(),
                    version=1,
                    experiment_id=experiment_id,
                    kind=kind,
                    schema_version=1,
                    payload=payload,
                    content_hash="0" * 64,
                    created_by=UUID(int=1),
                    created_at=NOW,
                )
            )


async def test_unknown_verdict_cannot_create_return(governance_engine):
    repo, experiment_id, _, _, _, _ = await cycle_fixture(governance_engine)
    feedback = await put(
        repo,
        experiment_id,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        {"preserve": ["Intent"], "change": ["Buyer"]},
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.return_to_refinement(
            uuid4(),
            feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
            command_key=uuid4(),
        )
    async with governance_engine.connect() as connection:
        assert not (await connection.execute(select(records.returns))).all()


async def test_attempt_and_verdict_reject_unbound_or_stale_lineage(governance_engine):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    unbound = await put(
        repo,
        experiment_id,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["Demand?"], "method": "Unbound"},
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.start_research_attempt(
            cycle.id,
            ArtifactInput.from_receipt(unbound, role="PLAN"),
            command_key=uuid4(),
        )
    first = await repo.start_research_attempt(
        cycle.id, ArtifactInput.from_receipt(plan, role="PLAN"), command_key=uuid4()
    )
    second_plan = await put(
        repo,
        experiment_id,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["More demand?"], "method": "Follow-up"},
        inputs=(ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),),
    )
    second = await repo.start_research_attempt(
        cycle.id,
        ArtifactInput.from_receipt(second_plan, role="PLAN"),
        command_key=uuid4(),
    )
    report = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "First attempt finding", "limitations": ["Fixture"]},
        inputs=(ArtifactInput.from_receipt(plan, role="PLAN"),),
    )
    recommendation = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {"recommendation": "PROCEED_TO_OFFER", "rationale": "Proceed"},
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
    )
    for attempt in (first, second):
        with pytest.raises(ProductRecordsDenied):
            await repo.commit_verdict(
                attempt.id,
                report=ArtifactInput.from_receipt(report, role="REPORT"),
                recommendation=ArtifactInput.from_receipt(
                    recommendation, role="RECOMMENDATION"
                ),
                verdict="PROCEED_TO_OFFER",
                committed_by=UUID(int=1),
                command_key=uuid4(),
            )


async def test_receipt_replays_compare_all_decision_arguments(governance_engine):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(
        governance_engine, accept=False
    )
    idea_ref = ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA")
    key = uuid4()
    first = await repo.accept_idea(
        cycle.id, idea_ref, accepted_by=UUID(int=1), command_key=key
    )
    assert (
        await repo.accept_idea(
            cycle.id, idea_ref, accepted_by=UUID(int=1), command_key=key
        )
        == first
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.accept_idea(cycle.id, idea_ref, accepted_by=uuid4(), command_key=key)
    key = uuid4()
    plan_ref = ArtifactInput.from_receipt(plan, role="PLAN")
    attempt = await repo.start_research_attempt(cycle.id, plan_ref, command_key=key)
    assert (
        await repo.start_research_attempt(cycle.id, plan_ref, command_key=key)
        == attempt
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.start_research_attempt(cycle.id, idea_ref, command_key=key)
    report = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "Refine", "limitations": ["Fixture"]},
        inputs=(plan_ref,),
    )
    report_ref = ArtifactInput.from_receipt(report, role="REPORT")
    recommendation = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {"recommendation": "REFINE_SAME_IDEA", "rationale": "Refine"},
        inputs=(report_ref,),
    )
    arguments = {
        "report": report_ref,
        "recommendation": ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        "verdict": "REFINE_SAME_IDEA",
        "committed_by": UUID(int=1),
        "command_key": uuid4(),
    }
    verdict = await repo.commit_verdict(attempt.id, **arguments)
    assert await repo.commit_verdict(attempt.id, **arguments) == verdict
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.commit_verdict(
            attempt.id,
            report=report_ref,
            recommendation=ArtifactInput.from_receipt(
                recommendation, role="RECOMMENDATION"
            ),
            verdict="PROCEED_TO_OFFER",
            committed_by=UUID(int=1),
            command_key=arguments["command_key"],
        )
    feedback = await put(
        repo,
        experiment_id,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        {"preserve": ["Intent"], "change": ["Buyer"]},
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
    )
    await accept_feedback(repo, experiment_id, feedback)
    feedback_ref = ArtifactInput.from_receipt(feedback, role="FEEDBACK")
    key = uuid4()
    next_cycle = await repo.return_to_refinement(
        verdict.id, feedback=feedback_ref, command_key=key
    )
    assert (
        await repo.return_to_refinement(
            verdict.id, feedback=feedback_ref, command_key=key
        )
        == next_cycle
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.return_to_refinement(
            verdict.id, feedback=report_ref, command_key=key
        )
    pivot = await put(
        repo,
        experiment_id,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Pivot",
            "customer": "Shops",
            "problem": "Inventory",
            "core_intent": "inventory",
            "material_pivot": True,
        },
    )
    pivot_ref = ArtifactInput.from_receipt(pivot, role="PIVOT_TARGET")
    key = uuid4()
    decision = await repo.approve_material_pivot(
        next_cycle.id, pivot_ref, approved_by=UUID(int=1), command_key=key
    )
    assert (
        await repo.approve_material_pivot(
            next_cycle.id, pivot_ref, approved_by=UUID(int=1), command_key=key
        )
        == decision
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.approve_material_pivot(
            next_cycle.id, pivot_ref, approved_by=uuid4(), command_key=key
        )
    validation = await put(
        repo,
        experiment_id,
        ArtifactKind.VALIDATION_RESULT,
        {"validator": "fixture", "disposition": "PASS", "reason": "Valid"},
        inputs=(ArtifactInput.from_receipt(pivot, role="TARGET"),),
    )
    arguments = {
        "experiment_id": experiment_id,
        "disposition": "VALIDATED",
        "decided_by": UUID(int=1),
        "validation": ArtifactInput.from_receipt(validation, role="VALIDATION"),
        "command_key": uuid4(),
    }
    disposition = await repo.record_disposition(pivot_ref, **arguments)
    assert await repo.record_disposition(pivot_ref, **arguments) == disposition
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.record_disposition(
            pivot_ref,
            experiment_id=experiment_id,
            disposition="ACCEPTED",
            decided_by=UUID(int=1),
            validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
            command_key=arguments["command_key"],
        )


async def test_root_and_profile_replay_compare_full_request(governance_engine):
    repo, profile, experiment_id, workflow_id, agent_id = await roots(governance_engine)
    async with governance_engine.connect() as connection:
        profile_key = await connection.scalar(
            select(records.commands.c.command_key).where(
                records.commands.c.kind == "REGISTER_PROFILE",
                records.commands.c.result_id == profile.id,
            )
        )
        binding_key = await connection.scalar(
            select(records.commands.c.command_key).where(
                records.commands.c.kind == "BIND_ROOTS",
                records.commands.c.result_id == experiment_id,
            )
        )
    await repo.register_profile(profile, command_key=profile_key)
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.register_profile(
            profile.model_copy(update={"constraints": ("CHANGED",)}),
            command_key=profile_key,
        )
    experiment = ProductExperiment(
        id=experiment_id,
        operator_profile_id=profile.id,
        operator_profile_version=1,
        name="synthetic-root",
        created_at=NOW,
    )
    workflow = ProductWorkflow(
        id=workflow_id,
        experiment_id=experiment_id,
        role="IDEA_TO_RESEARCH",
        created_at=NOW,
    )
    agent = ProductAgent(
        id=agent_id, workflow_id=workflow_id, role="MARKET_RESEARCH", created_at=NOW
    )
    await repo.bind_roots(experiment, workflow, agent, command_key=binding_key)
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.bind_roots(
            experiment.model_copy(update={"name": "changed"}),
            workflow,
            agent,
            command_key=binding_key,
        )


async def test_append_replay_compares_sources_and_ignores_input_order(
    governance_engine,
):
    from test_governance import register

    from alon_ai.accounting.repository import GovernanceProvisioner

    repo, experiment_id, seed, _, idea, _ = await cycle_fixture(governance_engine)
    draft = artifact(
        experiment_id,
        ArtifactKind.SERVICE_PROFILE,
        {"name": "Service", "scope": "Scope"},
    )
    key = uuid4()
    inputs = (
        ArtifactInput.from_receipt(seed, role="SEED"),
        ArtifactInput.from_receipt(idea, role="IDEA"),
    )
    original = await repo.append_artifact(draft, inputs=inputs, command_key=key)
    assert (
        await repo.append_artifact(
            draft, inputs=tuple(reversed(inputs)), command_key=key
        )
        == original
    )
    evidence_id = uuid4()
    await register(
        GovernanceProvisioner(governance_engine), evidence_id, "CONTROL", NOW
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.append_artifact(
            draft,
            inputs=inputs,
            sources=(
                SourceReference(kind="GOVERNANCE_EVIDENCE", evidence_id=evidence_id),
            ),
            command_key=key,
        )
