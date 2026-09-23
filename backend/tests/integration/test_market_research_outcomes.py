"""Focused L04 market-research verdict and bounded-return state machine."""

import asyncio
import signal
import subprocess
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from test_dbos_market_research_workflow import (
    _command,
    _environment,
    _migrate_dbos,
    _spawn,
    _wait_for,
)
from test_governance import seed as governance_seed
from test_product_record_guards import cycle_fixture, put
from test_product_records import NOW, artifact, register_test_operator

from alon_ai.accounting import schema as governance
from alon_ai.providers.contracts import CallAttribution
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
    ResearchCycleBudgetInput,
)
from alon_ai.records import schema as records
from alon_ai.workflows.market_research import (
    DBOS_APPLICATION_VERSION,
    MarketResearchDecisionWorkflowRepository,
    MarketResearchOutcomeWorkflowRequest,
    market_research_outcome_workflow_id,
)

pytestmark = pytest.mark.integration


async def prepared_research(engine, verdict: str):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(engine)
    attempt = await repo.start_market_research(
        experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    report = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "Observed evidence", "limitations": ["Bounded sample"]},
        inputs=(ArtifactInput.from_receipt(plan, role="PLAN"),),
    )
    recommendation = await put(
        repo,
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {"recommendation": verdict, "rationale": "Exact evidence disposition"},
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
    )
    return repo, experiment_id, cycle, idea, attempt, report, recommendation


async def governed_research(engine, verdict: str, *, max_count: int = 10):
    _, admin, attr, config, _, now = await governance_seed(engine)
    agent_id = uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            governance.agents.insert().values(
                id=agent_id, workflow_id=attr.workflow_run_id
            )
        )
    await register_test_operator(engine)
    profile = OperatorCapabilityProfile(
        id=UUID(int=2),
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
            minimum_margin_rate=Decimal("0.4"),
            maximum_discount_rate=Decimal("0.1"),
            minimum_deposit_rate=Decimal("0.5"),
        ),
        approved_by=UUID(int=1),
        created_at=NOW,
    )
    repo = ProductRecordsRepository(engine, clock=lambda: NOW)
    await repo.register_profile(profile, command_key=uuid4())
    await repo.bind_roots(
        ProductExperiment(
            id=attr.experiment_id,
            operator_profile_id=profile.id,
            operator_profile_version=1,
            name="governed-research",
            created_at=NOW,
        ),
        ProductWorkflow(
            id=attr.workflow_run_id,
            experiment_id=attr.experiment_id,
            role="IDEA_TO_RESEARCH",
            created_at=NOW,
        ),
        ProductAgent(
            id=agent_id,
            workflow_id=attr.workflow_run_id,
            role="MARKET_RESEARCH",
            created_at=NOW,
        ),
        command_key=uuid4(),
    )
    seed = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Original intent."},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        command_key=uuid4(),
    )
    cycle = await repo.create_cycle(
        attr.experiment_id,
        seed=ArtifactInput.from_receipt(seed, role="SEED"),
        command_key=uuid4(),
    )
    idea_draft = artifact(
        attr.experiment_id,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Service",
            "customer": "Operators",
            "problem": "Manual work",
            "core_intent": "reduce-manual-work",
            "material_pivot": False,
        },
        workflow_id=attr.workflow_run_id,
        agent_id=agent_id,
    )
    idea = await repo.append_artifact(idea_draft, command_key=uuid4())
    await repo.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    plan = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {"questions": ["Is there demand?"], "method": "Fixture review"},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),),
        command_key=uuid4(),
    )
    attempt = await repo.start_market_research(
        attr.experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    parent_account = await _workflow_account(engine, attr.workflow_run_id)
    await repo.bind_research_cycle_budget(
        cycle.id,
        ResearchCycleBudgetInput(
            workflow_id=attr.workflow_run_id,
            config_id=config.id,
            config_version=config.version,
            budget_account_id=parent_account,
            max_search_results=max_count,
            max_capture_pages=max_count,
            max_openai_calls=max_count,
        ),
        command_key=uuid4(),
    )
    report = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.MARKET_RESEARCH_REPORT,
            {"finding": "Observed evidence", "limitations": ["Bounded sample"]},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(ArtifactInput.from_receipt(plan, role="PLAN"),),
        command_key=uuid4(),
    )
    recommendation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
            {"recommendation": verdict, "rationale": "Exact evidence"},
            workflow_id=attr.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
        command_key=uuid4(),
    )
    return repo, admin, attr, config, agent_id, cycle, idea_draft, idea, attempt, report, recommendation, now


async def _workflow_account(engine, workflow_id):
    async with engine.connect() as connection:
        return await connection.scalar(
            select(governance.budget_accounts.c.id).where(
                governance.budget_accounts.c.scope == "WORKFLOW",
                governance.budget_accounts.c.workflow_id == workflow_id,
                governance.budget_accounts.c.currency == "USD",
            )
        )


async def child_governance(engine, admin, attr: CallAttribution, config, now):
    child_workflow, child_operation, child_agent = uuid4(), uuid4(), uuid4()
    child_attr = attr.model_copy(
        update={
            "workflow_run_id": child_workflow,
            "operation_run_id": child_operation,
            "logical_operation_id": uuid4(),
            "correlation_id": uuid4(),
            "config_version": uuid4(),
            "deadline": now + timedelta(hours=1),
        }
    )
    await admin.scope(child_attr, gate_kind="NONE")
    child_config = config.model_copy(
        update={
            "id": uuid4(),
            "version": child_attr.config_version,
            "workflow_id": child_workflow,
            "adapter_version": uuid4(),
        }
    )
    await admin.config(child_config)
    await admin.budgets(
        child_attr,
        provider=child_config.intended_use.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(1),
        effective_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )
    async with engine.begin() as connection:
        await connection.execute(
            governance.agents.insert().values(
                id=child_agent, workflow_id=child_workflow
            )
        )
        await connection.execute(
            records.workflows.insert().values(
                id=child_workflow,
                experiment_id=attr.experiment_id,
                role="TARGETED_RESEARCH",
                created_at=NOW,
            )
        )
        await connection.execute(
            records.agents.insert().values(
                id=child_agent,
                workflow_id=child_workflow,
                role="MARKET_RESEARCH",
                created_at=NOW,
            )
        )
    account = await _workflow_account(engine, child_workflow)
    return child_workflow, child_agent, child_config, account


async def pivot_inputs(
    engine,
    repo,
    admin,
    attr,
    config,
    now,
    idea_draft,
    idea,
    report,
    recommendation,
    *,
    material_pivot: bool = True,
    next_version: int = 2,
):
    workflow, agent, child_config, account = await child_governance(
        engine, admin, attr, config, now
    )
    feedback = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
            {"preserve": ["Evidence"], "change": ["Approved buyer pivot"]},
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
        command_key=uuid4(),
    )
    feedback_validation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {"validator": "pivot-v1", "disposition": "PASS", "reason": "Exact"},
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(ArtifactInput.from_receipt(feedback, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(feedback, role="TARGET"),
        experiment_id=attr.experiment_id,
        disposition="VALIDATED",
        validation=ArtifactInput.from_receipt(
            feedback_validation, role="VALIDATION"
        ),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    next_idea = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                "title": "Pivoted service" if material_pivot else "Refined service",
                "customer": "Finance leaders" if material_pivot else "Operators",
                "problem": "Forecast errors" if material_pivot else "Manual work",
                "core_intent": (
                    "reduce-forecast-error" if material_pivot else "reduce-manual-work"
                ),
                "material_pivot": material_pivot,
            },
            logical_id=idea_draft.logical_id,
            version=next_version,
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(idea, role="SUPERSEDES"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
            ArtifactInput.from_receipt(feedback, role="RETURN_FEEDBACK"),
        ),
        command_key=uuid4(),
    )
    validation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {
                "validator": "pivot-classifier-v1",
                "disposition": "PASS",
                "reason": "Deterministic changed core intent",
            },
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(ArtifactInput.from_receipt(next_idea, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(next_idea, role="TARGET"),
        experiment_id=attr.experiment_id,
        disposition="VALIDATED",
        validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    plan = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {"questions": ["Does pivot demand exist?"], "method": "Targeted"},
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(next_idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(feedback, role="RETURN_FEEDBACK"),
        ),
        command_key=uuid4(),
    )
    budget = ResearchCycleBudgetInput(
        workflow_id=workflow,
        config_id=child_config.id,
        config_version=child_config.version,
        budget_account_id=account,
        max_search_results=10,
        max_capture_pages=10,
        max_openai_calls=10,
    )
    return feedback, feedback_validation, next_idea, plan, budget


async def _child_research_outputs(engine, repo, experiment_id, cycle_id):
    async with engine.connect() as connection:
        attempt = (
            (
                await connection.execute(
                    select(records.research_attempts).where(
                        records.research_attempts.c.cycle_id == cycle_id
                    )
                )
            )
            .mappings()
            .one()
        )
        plan = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == attempt["plan_artifact_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
    plan_ref = ArtifactInput(
        artifact_id=plan["id"],
        kind=ArtifactKind.RESEARCH_PLAN,
        version=plan["version"],
        content_hash=plan["content_hash"],
        role="PLAN",
    )
    report = await repo.append_artifact(
        artifact(
            experiment_id,
            ArtifactKind.MARKET_RESEARCH_REPORT,
            {
                "finding": "Bounded follow-up evidence",
                "limitations": ["Synthetic sample"],
            },
            workflow_id=plan["workflow_id"],
            agent_id=plan["agent_id"],
        ),
        inputs=(plan_ref,),
        command_key=uuid4(),
    )
    recommendation = await repo.append_artifact(
        artifact(
            experiment_id,
            ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
            {
                "recommendation": "REFINE_SAME_IDEA",
                "rationale": "Evidence remains narrow",
            },
            workflow_id=plan["workflow_id"],
            agent_id=plan["agent_id"],
        ),
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
        command_key=uuid4(),
    )
    return attempt["id"], report, recommendation


async def test_third_same_intent_return_blocks_without_child_graph(governance_engine):
    (
        repo,
        admin,
        attr,
        config,
        _agent,
        _cycle,
        idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(governance_engine, "REFINE_SAME_IDEA")
    attempt_id = attempt.id
    for next_version in (2, 3):
        feedback, validation, proposed, plan, budget = await pivot_inputs(
            governance_engine,
            repo,
            admin,
            attr,
            config,
            now,
            idea_draft,
            idea,
            report,
            recommendation,
            material_pivot=False,
            next_version=next_version,
        )
        prior = await repo.commit_market_research_outcome(
            attempt_id,
            report=ArtifactInput.from_receipt(report, role="REPORT"),
            recommendation=ArtifactInput.from_receipt(
                recommendation, role="RECOMMENDATION"
            ),
            verdict="REFINE_SAME_IDEA",
            committed_by=UUID(int=1),
            feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
            feedback_validation=ArtifactInput.from_receipt(
                validation, role="VALIDATION"
            ),
            proposed_idea=ArtifactInput.from_receipt(proposed, role="PROPOSED_IDEA"),
            plan=ArtifactInput.from_receipt(plan, role="PLAN"),
            budget=budget,
            accepted_by=UUID(int=1),
            command_key=uuid4(),
        )
        assert prior.child_cycle_id is not None and prior.block_id is None
        idea = proposed
        attempt_id, report, recommendation = await _child_research_outputs(
            governance_engine, repo, attr.experiment_id, prior.child_cycle_id
        )

    watched = (
        records.cycles,
        records.idea_acceptances,
        records.research_attempts,
        records.research_cycle_budgets,
        records.returns,
    )
    async with governance_engine.connect() as connection:
        before = {
            table.name: await connection.scalar(
                select(func.count())
                .select_from(table)
                .where(table.c.experiment_id == attr.experiment_id)
            )
            for table in watched
        }
        plan_count = await connection.scalar(
            select(func.count())
            .select_from(records.artifacts)
            .where(
                records.artifacts.c.experiment_id == attr.experiment_id,
                records.artifacts.c.kind == ArtifactKind.RESEARCH_PLAN,
            )
        )
    key = uuid4()
    report_input = ArtifactInput.from_receipt(report, role="REPORT")
    recommendation_input = ArtifactInput.from_receipt(
        recommendation, role="RECOMMENDATION"
    )
    blocked = await repo.commit_market_research_outcome(
        attempt_id,
        report=report_input,
        recommendation=recommendation_input,
        verdict="REFINE_SAME_IDEA",
        committed_by=UUID(int=1),
        command_key=key,
    )
    assert blocked.verdict == "REFINE_SAME_IDEA"
    assert blocked.state == "RETURN_FOR_REFINEMENT"
    assert blocked.child_cycle_id is None and blocked.block_id is not None
    assert (
        await repo.commit_market_research_outcome(
            attempt_id,
            report=report_input,
            recommendation=recommendation_input,
            verdict="REFINE_SAME_IDEA",
            committed_by=UUID(int=1),
            command_key=key,
        )
        == blocked
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.research_return_blocks.c.reason_code).where(
                    records.research_return_blocks.c.id == blocked.block_id
                )
            )
            == "SAME_INTENT_LIMIT_REACHED"
        )
        for table in watched:
            assert (
                await connection.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.experiment_id == attr.experiment_id)
                )
                == before[table.name]
            )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.artifacts)
                .where(
                    records.artifacts.c.experiment_id == attr.experiment_id,
                    records.artifacts.c.kind == ArtifactKind.RESEARCH_PLAN,
                )
            )
            == plan_count
        )
        command = (
            (
                await connection.execute(
                    select(records.commands).where(
                        records.commands.c.command_key == key
                    )
                )
            )
            .mappings()
            .one()
        )
        assert command["id"] == blocked.command_id
        assert command["result_id"] == blocked.result_id
        for table in (records.audit, records.outbox):
            assert (
                await connection.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.command_id == blocked.command_id)
                )
                == 1
            )


async def test_proceed_outcome_commits_exact_verdict_and_state_once(
    governance_engine,
):
    (
        repo,
        experiment_id,
        cycle,
        _idea,
        attempt,
        report,
        recommendation,
    ) = await prepared_research(governance_engine, "PROCEED_TO_OFFER")
    key = uuid4()
    kwargs = {
        "attempt_id": attempt.id,
        "report": ArtifactInput.from_receipt(report, role="REPORT"),
        "recommendation": ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        "verdict": "PROCEED_TO_OFFER",
        "committed_by": UUID(int=1),
        "command_key": key,
    }

    receipt = await repo.commit_market_research_outcome(**kwargs)
    assert await repo.commit_market_research_outcome(**kwargs) == receipt

    async with governance_engine.connect() as connection:
        state = (
            (
                await connection.execute(
                    select(records.cycle_states).where(
                        records.cycle_states.c.cycle_id == cycle.id
                    )
                )
            )
            .mappings()
            .one()
        )
        transition = (
            (
                await connection.execute(
                    select(records.cycle_transitions).where(
                        records.cycle_transitions.c.id == receipt.transition_id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert state["state"] == "PROCEED_TO_OFFER"
        assert transition["verdict_id"] == receipt.id
        assert transition["from_state"] == "MARKET_RESEARCH"
        assert transition["to_state"] == "PROCEED_TO_OFFER"
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycle_transitions)
                .where(records.cycle_transitions.c.cycle_id == cycle.id)
            )
        ) == 2
        assert not await connection.scalar(
            select(records.artifacts.c.id).where(
                records.artifacts.c.experiment_id == experiment_id,
                records.artifacts.c.kind == "OFFER_DESIGN_INPUT_BUNDLE",
            )
        )

    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.commit_market_research_outcome(
            **{**kwargs, "committed_by": UUID(int=2)}
        )


async def test_outcome_rejects_superseded_report_without_partial_graph(
    governance_engine,
):
    repo, experiment_id, cycle, _idea, attempt, report, recommendation = (
        await prepared_research(governance_engine, "PROCEED_TO_OFFER")
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(report, role="REPORT"),
        experiment_id=experiment_id,
        disposition="SUPERSEDED",
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )

    with pytest.raises(ProductRecordsDenied, match="STALE_INPUT"):
        await repo.commit_market_research_outcome(
            attempt.id,
            report=ArtifactInput.from_receipt(report, role="REPORT"),
            recommendation=ArtifactInput.from_receipt(
                recommendation, role="RECOMMENDATION"
            ),
            verdict="PROCEED_TO_OFFER",
            committed_by=UUID(int=1),
            command_key=uuid4(),
        )

    async with governance_engine.connect() as connection:
        assert not await connection.scalar(
            select(records.verdicts.c.id).where(
                records.verdicts.c.cycle_id == cycle.id
            )
        )


async def test_kill_outcome_is_terminal_for_offer_and_research(governance_engine):
    (
        repo,
        experiment_id,
        cycle,
        idea,
        attempt,
        report,
        recommendation,
    ) = await prepared_research(governance_engine, "KILL_IDEA")
    receipt = await repo.commit_market_research_outcome(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="KILL_IDEA",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    assert receipt.state == "KILLED"

    with pytest.raises(ProductRecordsDenied, match="INVALID_STATE"):
        await repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            plan=ArtifactInput.from_receipt(report, role="PLAN"),
            command_key=uuid4(),
        )


async def test_material_pivot_denials_have_distinct_identity_and_replay(
    governance_engine,
):
    (
        repo,
        _experiment_id,
        cycle,
        _idea,
        attempt,
        report,
        recommendation,
    ) = await prepared_research(governance_engine, "MATERIAL_PIVOT_RECOMMENDED")
    outcome_key = uuid4()
    outcome_kwargs = {
        "attempt_id": attempt.id,
        "report": ArtifactInput.from_receipt(report, role="REPORT"),
        "recommendation": ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        "verdict": "MATERIAL_PIVOT_RECOMMENDED",
        "committed_by": UUID(int=1),
        "command_key": outcome_key,
    }
    verdict = await repo.commit_market_research_outcome(**outcome_kwargs)
    first_id, second_id = uuid4(), uuid4()
    first_key, second_key = uuid4(), uuid4()

    first = await repo.decide_material_pivot(
        verdict.id,
        decision_id=first_id,
        decision="DENIED",
        decided_by=UUID(int=1),
        reason_code="INSUFFICIENT_JUSTIFICATION",
        command_key=first_key,
    )
    assert (
        await repo.decide_material_pivot(
            verdict.id,
            decision_id=first_id,
            decision="DENIED",
            decided_by=UUID(int=1),
            reason_code="INSUFFICIENT_JUSTIFICATION",
            command_key=first_key,
        )
        == first
    )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.decide_material_pivot(
            verdict.id,
            decision_id=first_id,
            decision="DENIED",
            decided_by=UUID(int=1),
            reason_code="DIFFERENT_REASON",
            command_key=first_key,
        )
    second = await repo.decide_material_pivot(
        verdict.id,
        decision_id=second_id,
        decision="DENIED",
        decided_by=UUID(int=1),
        reason_code="INSUFFICIENT_JUSTIFICATION",
        command_key=second_key,
    )
    assert first.id != second.id
    assert await repo.commit_market_research_outcome(**outcome_kwargs) == verdict

    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.pivot_decisions)
                .where(records.pivot_decisions.c.cycle_id == cycle.id)
            )
        ) == 2
        assert (
            await connection.scalar(
                select(records.cycle_states.c.state).where(
                    records.cycle_states.c.cycle_id == cycle.id
                )
            )
        ) == "WAITING_FOR_PIVOT_APPROVAL"


async def test_outcome_runtime_binding_pins_payload_hash_and_cancels_cleanly(
    governance_engine,
):
    (
        _repo,
        experiment_id,
        cycle,
        _idea,
        attempt,
        report,
        recommendation,
    ) = await prepared_research(governance_engine, "KILL_IDEA")
    key = uuid4()
    request = MarketResearchOutcomeWorkflowRequest(
        experiment_id=experiment_id,
        cycle_id=cycle.id,
        attempt_id=attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="KILL_IDEA",
        committed_by=UUID(int=1),
        command_key=key,
    )
    runtime = MarketResearchDecisionWorkflowRepository(governance_engine)
    binding = await runtime.bind_outcome(
        request, application_version=DBOS_APPLICATION_VERSION
    )
    assert binding.dbos_workflow_id == market_research_outcome_workflow_id(
        attempt.id, key
    )
    assert binding.request_hash == request.request_hash
    assert binding.request_payload["verdict"] == "KILL_IDEA"

    changed = request.model_copy(update={"committed_by": UUID(int=2)})
    with pytest.raises(ProductRecordsDenied, match="WORKFLOW_BINDING_CONFLICT"):
        await runtime.bind_outcome(
            changed, application_version=DBOS_APPLICATION_VERSION
        )
    await runtime.cancel(binding.dbos_workflow_id)

    rejected_request = request.model_copy(update={"command_key": uuid4()})
    rejected = await runtime.start_outcome(
        rejected_request, application_version=DBOS_APPLICATION_VERSION
    )
    await runtime.record_rejection(rejected.dbos_workflow_id, "STALE_INPUT")

    async with governance_engine.connect() as connection:
        assert not await connection.scalar(
            select(records.verdicts.c.id).where(
                records.verdicts.c.cycle_id == cycle.id
            )
        )
        assert (
            await connection.scalar(
                select(
                    records.market_research_decision_workflow_bindings.c.delivery_state
                ).where(
                    records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                    == binding.dbos_workflow_id
                )
            )
        ) == "CANCELLED"
        rejected_row = (
            (
                await connection.execute(
                    select(
                        records.market_research_decision_workflow_bindings.c.delivery_state,
                        records.market_research_decision_workflow_bindings.c.failure_code,
                    ).where(
                        records.market_research_decision_workflow_bindings.c.dbos_workflow_id
                        == rejected.dbos_workflow_id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert rejected_row == {
            "delivery_state": "REJECTED",
            "failure_code": "STALE_INPUT",
        }


async def test_same_intent_outcome_atomically_starts_targeted_child(
    governance_engine,
):
    (
        repo,
        admin,
        attr,
        config,
        _agent_id,
        _cycle,
        idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(governance_engine, "REFINE_SAME_IDEA")
    child_workflow, child_agent, child_config, child_account = (
        await child_governance(governance_engine, admin, attr, config, now)
    )
    feedback = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
            {
                "preserve": ["Original pain and buyer"],
                "change": ["Obtain willingness-to-pay evidence"],
            },
            workflow_id=child_workflow,
            agent_id=child_agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
        command_key=uuid4(),
    )
    feedback_validation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {
                "validator": "bounded-return-validator-v1",
                "disposition": "PASS",
                "reason": "Exact verdict evidence",
            },
            workflow_id=child_workflow,
            agent_id=child_agent,
        ),
        inputs=(ArtifactInput.from_receipt(feedback, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(feedback, role="TARGET"),
        experiment_id=attr.experiment_id,
        disposition="VALIDATED",
        validation=ArtifactInput.from_receipt(
            feedback_validation, role="VALIDATION"
        ),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    next_idea = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                "title": "Service clarified",
                "customer": "Operators",
                "problem": "Manual work",
                "core_intent": "reduce-manual-work",
                "material_pivot": False,
            },
            logical_id=idea_draft.logical_id,
            version=2,
            workflow_id=child_workflow,
            agent_id=child_agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(idea, role="SUPERSEDES"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
            ArtifactInput.from_receipt(feedback, role="RETURN_FEEDBACK"),
        ),
        command_key=uuid4(),
    )
    idea_validation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {
                "validator": "idea-lineage-validator-v1",
                "disposition": "PASS",
                "reason": "Same core intent and next version",
            },
            workflow_id=child_workflow,
            agent_id=child_agent,
        ),
        inputs=(ArtifactInput.from_receipt(next_idea, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(next_idea, role="TARGET"),
        experiment_id=attr.experiment_id,
        disposition="VALIDATED",
        validation=ArtifactInput.from_receipt(idea_validation, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    child_plan = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {
                "questions": ["What evidence closes the price gap?"],
                "method": "Targeted follow-up",
            },
            workflow_id=child_workflow,
            agent_id=child_agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(next_idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(feedback, role="RETURN_FEEDBACK"),
        ),
        command_key=uuid4(),
    )
    budget = ResearchCycleBudgetInput(
        workflow_id=child_workflow,
        config_id=child_config.id,
        config_version=child_config.version,
        budget_account_id=child_account,
        max_search_results=10,
        max_capture_pages=10,
        max_openai_calls=10,
    )
    key = uuid4()
    kwargs = {
        "attempt_id": attempt.id,
        "report": ArtifactInput.from_receipt(report, role="REPORT"),
        "recommendation": ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        "verdict": "REFINE_SAME_IDEA",
        "committed_by": UUID(int=1),
        "feedback": ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        "feedback_validation": ArtifactInput.from_receipt(
            feedback_validation, role="VALIDATION"
        ),
        "proposed_idea": ArtifactInput.from_receipt(
            next_idea, role="PROPOSED_IDEA"
        ),
        "plan": ArtifactInput.from_receipt(child_plan, role="PLAN"),
        "budget": budget,
        "accepted_by": UUID(int=1),
        "command_key": key,
    }
    receipt = await repo.commit_market_research_outcome(**kwargs)
    assert receipt.child_cycle_id is not None
    assert receipt.block_id is None
    assert await repo.commit_market_research_outcome(**kwargs) == receipt

    async with governance_engine.connect() as connection:
        child_state = await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == receipt.child_cycle_id
            )
        )
        assert child_state == "MARKET_RESEARCH"
        assert await connection.scalar(
            select(records.idea_acceptances.c.artifact_id).where(
                records.idea_acceptances.c.cycle_id == receipt.child_cycle_id
            )
        ) == next_idea.artifact_id
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.returns)
                .where(records.returns.c.verdict_id == receipt.id)
            )
        ) == 1


async def test_approved_material_pivot_commits_supplied_idea_and_child(
    governance_engine,
):
    (
        repo,
        admin,
        attr,
        config,
        _agent,
        cycle,
        idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(governance_engine, "MATERIAL_PIVOT_RECOMMENDED")
    verdict = await repo.commit_market_research_outcome(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="MATERIAL_PIVOT_RECOMMENDED",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    feedback, feedback_validation, next_idea, plan, budget = await pivot_inputs(
        governance_engine,
        repo,
        admin,
        attr,
        config,
        now,
        idea_draft,
        idea,
        report,
        recommendation,
    )
    key, decision_id = uuid4(), uuid4()
    kwargs = {
        "verdict_id": verdict.id,
        "decision_id": decision_id,
        "decision": "APPROVED",
        "decided_by": UUID(int=1),
        "reason_code": "OPERATOR_APPROVED",
        "proposed_idea": ArtifactInput.from_receipt(
            next_idea, role="PROPOSED_IDEA"
        ),
        "feedback": ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        "feedback_validation": ArtifactInput.from_receipt(
            feedback_validation, role="VALIDATION"
        ),
        "plan": ArtifactInput.from_receipt(plan, role="PLAN"),
        "budget": budget,
        "accepted_by": UUID(int=1),
        "command_key": key,
    }
    receipt = await repo.decide_material_pivot(**kwargs)
    assert receipt.child_cycle_id is not None
    assert await repo.decide_material_pivot(**kwargs) == receipt

    async with governance_engine.connect() as connection:
        assert await connection.scalar(
            select(records.idea_acceptances.c.artifact_id).where(
                records.idea_acceptances.c.cycle_id == receipt.child_cycle_id
            )
        ) == next_idea.artifact_id
        assert await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == receipt.child_cycle_id
            )
        ) == "MARKET_RESEARCH"
        assert await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == cycle.id
            )
        ) == "RETURN_FOR_REFINEMENT"


async def test_inconclusive_allows_one_atomic_supplement(governance_engine):
    (
        repo,
        admin,
        attr,
        config,
        _agent,
        _cycle,
        _idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(governance_engine, "INCONCLUSIVE")
    verdict = await repo.commit_market_research_outcome(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="INCONCLUSIVE",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    workflow, agent, child_config, account = await child_governance(
        governance_engine, admin, attr, config, now
    )
    feedback = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
            {"preserve": ["Current idea"], "change": ["Missing evidence only"]},
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
        command_key=uuid4(),
    )
    validation = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {
                "validator": "supplement-v1",
                "disposition": "PASS",
                "reason": "Explicit missing evidence",
            },
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(ArtifactInput.from_receipt(feedback, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(feedback, role="TARGET"),
        experiment_id=attr.experiment_id,
        disposition="VALIDATED",
        validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    plan = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.RESEARCH_PLAN,
            {"questions": ["Resolve missing evidence"], "method": "Supplement"},
            workflow_id=workflow,
            agent_id=agent,
        ),
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(feedback, role="RETURN_FEEDBACK"),
        ),
        command_key=uuid4(),
    )
    budget = ResearchCycleBudgetInput(
        workflow_id=workflow,
        config_id=child_config.id,
        config_version=child_config.version,
        budget_account_id=account,
        max_search_results=5,
        max_capture_pages=5,
        max_openai_calls=5,
    )
    key = uuid4()
    kwargs = {
        "verdict_id": verdict.id,
        "feedback": ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        "feedback_validation": ArtifactInput.from_receipt(
            validation, role="VALIDATION"
        ),
        "plan": ArtifactInput.from_receipt(plan, role="PLAN"),
        "budget": budget,
        "accepted_by": UUID(int=1),
        "command_key": key,
    }
    receipt = await repo.start_inconclusive_supplement(**kwargs)
    assert receipt.outcome == "STARTED"
    assert receipt.child_cycle_id is not None
    assert await repo.start_inconclusive_supplement(**kwargs) == receipt

    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.returns)
                .where(
                    records.returns.c.kind == "INCONCLUSIVE_SUPPLEMENT",
                    records.returns.c.applicable_scope_id
                    == select(records.cycles.c.episode_id)
                    .where(records.cycles.c.id == receipt.child_cycle_id)
                    .scalar_subquery(),
                )
            )
        ) == 1


async def test_exhausted_budget_commits_block_without_child_cycle(governance_engine):
    (
        repo,
        admin,
        attr,
        config,
        _agent,
        cycle,
        idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(
        governance_engine, "REFINE_SAME_IDEA", max_count=0
    )
    feedback, feedback_validation, proposed, plan, budget = await pivot_inputs(
        governance_engine,
        repo,
        admin,
        attr,
        config,
        now,
        idea_draft,
        idea,
        report,
        recommendation,
    )
    key = uuid4()
    receipt = await repo.commit_market_research_outcome(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="REFINE_SAME_IDEA",
        committed_by=UUID(int=1),
        feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        feedback_validation=ArtifactInput.from_receipt(
            feedback_validation, role="VALIDATION"
        ),
        proposed_idea=ArtifactInput.from_receipt(proposed, role="PROPOSED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        budget=budget,
        accepted_by=UUID(int=1),
        command_key=key,
    )
    assert receipt.block_id is not None
    assert receipt.child_cycle_id is None
    async with governance_engine.connect() as connection:
        block = (
            (
                await connection.execute(
                    select(records.research_return_blocks).where(
                        records.research_return_blocks.c.id == receipt.block_id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert block["reason_code"] == "BUDGET_EXHAUSTED"
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycles)
                .where(records.cycles.c.experiment_id == attr.experiment_id)
            )
        ) == 1
        assert await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == cycle.id
            )
        ) == "RETURN_FOR_REFINEMENT"

    with pytest.raises(ProductRecordsDenied, match="MANAGED_RETURN_COMMAND_REQUIRED"):
        await repo.return_to_research(
            receipt.id,
            kind="SAME_INTENT",
            feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
            command_key=uuid4(),
        )


async def test_exhausted_supplied_child_budget_blocks_without_child_cycle(
    governance_engine,
):
    (
        repo,
        admin,
        attr,
        config,
        _agent,
        _cycle,
        idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(governance_engine, "REFINE_SAME_IDEA")
    feedback, feedback_validation, proposed, plan, budget = await pivot_inputs(
        governance_engine,
        repo,
        admin,
        attr,
        config,
        now,
        idea_draft,
        idea,
        report,
        recommendation,
        material_pivot=False,
    )
    budget = budget.model_copy(update={"max_search_results": 0})

    receipt = await repo.commit_market_research_outcome(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="REFINE_SAME_IDEA",
        committed_by=UUID(int=1),
        feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        feedback_validation=ArtifactInput.from_receipt(
            feedback_validation, role="VALIDATION"
        ),
        proposed_idea=ArtifactInput.from_receipt(proposed, role="PROPOSED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        budget=budget,
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )

    assert receipt.block_id is not None
    assert receipt.child_cycle_id is None
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.research_return_blocks.c.reason_code).where(
                    records.research_return_blocks.c.id == receipt.block_id
                )
            )
        ) == "BUDGET_EXHAUSTED"
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycles)
                .where(records.cycles.c.experiment_id == attr.experiment_id)
            )
        ) == 1


async def test_same_intent_child_failure_rolls_back_entire_graph(governance_engine):
    (
        repo,
        admin,
        attr,
        config,
        _agent,
        cycle,
        idea_draft,
        idea,
        attempt,
        report,
        recommendation,
        now,
    ) = await governed_research(governance_engine, "REFINE_SAME_IDEA")
    feedback, feedback_validation, proposed, plan, budget = await pivot_inputs(
        governance_engine,
        repo,
        admin,
        attr,
        config,
        now,
        idea_draft,
        idea,
        report,
        recommendation,
        material_pivot=False,
    )
    async with governance_engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE FUNCTION fail_bounded_return_attempt() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                  RAISE EXCEPTION 'synthetic bounded return failure';
                END $$;
                CREATE TRIGGER fail_bounded_return_attempt
                BEFORE INSERT ON record_research_attempts FOR EACH ROW
                EXECUTE FUNCTION fail_bounded_return_attempt();
                """
            )
        )
    key = uuid4()
    try:
        with pytest.raises(ProductRecordsDenied):
            await repo.commit_market_research_outcome(
                attempt.id,
                report=ArtifactInput.from_receipt(report, role="REPORT"),
                recommendation=ArtifactInput.from_receipt(
                    recommendation, role="RECOMMENDATION"
                ),
                verdict="REFINE_SAME_IDEA",
                committed_by=UUID(int=1),
                feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
                feedback_validation=ArtifactInput.from_receipt(
                    feedback_validation, role="VALIDATION"
                ),
                proposed_idea=ArtifactInput.from_receipt(
                    proposed, role="PROPOSED_IDEA"
                ),
                plan=ArtifactInput.from_receipt(plan, role="PLAN"),
                budget=budget,
                accepted_by=UUID(int=1),
                command_key=key,
            )
    finally:
        async with governance_engine.begin() as connection:
            await connection.execute(
                text(
                    "DROP TRIGGER fail_bounded_return_attempt "
                    "ON record_research_attempts; "
                    "DROP FUNCTION fail_bounded_return_attempt()"
                )
            )
    async with governance_engine.connect() as connection:
        assert not await connection.scalar(
            select(records.verdicts.c.id).where(
                records.verdicts.c.cycle_id == cycle.id
            )
        )
        assert not await connection.scalar(
            select(records.commands.c.id).where(
                records.commands.c.command_key == key
            )
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycles)
                .where(records.cycles.c.experiment_id == attr.experiment_id)
            )
        ) == 1
        assert await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == cycle.id
            )
        ) == "MARKET_RESEARCH"


@pytest.mark.parametrize(
    "barrier", ["before-outcome-business", "after-outcome-business"]
)
async def test_dbos_outcome_process_kill_recovers_one_business_graph(
    governance_engine, tmp_path: Path, barrier: str
):
    (
        _repo,
        experiment_id,
        cycle,
        _idea,
        attempt,
        report,
        recommendation,
    ) = await prepared_research(governance_engine, "PROCEED_TO_OFFER")
    request = MarketResearchOutcomeWorkflowRequest(
        experiment_id=experiment_id,
        cycle_id=cycle.id,
        attempt_id=attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="PROCEED_TO_OFFER",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    request_path = tmp_path / "outcome-request.json"
    request_path.write_text(request.model_dump_json(exclude_computed_fields=True))
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    environment = {
        **_environment(governance_engine),
        "ALON_AI_DBOS_TEST_BARRIER": barrier,
        "ALON_AI_DBOS_TEST_READY": str(ready),
        "ALON_AI_DBOS_TEST_RELEASE": str(release),
    }
    process = await _spawn(_command("start-outcome", request_path), environment)
    await _wait_for(ready, process)
    process.send_signal(signal.SIGKILL)
    await asyncio.wait_for(process.wait(), timeout=10)

    recovered = await asyncio.to_thread(
        subprocess.run,
        _command("recover-outcome", request_path),
        cwd=Path(__file__).parents[2],
        env=_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert recovered.returncode == 0, recovered.stderr
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.verdicts)
                .where(records.verdicts.c.cycle_id == cycle.id)
            )
        ) == 1
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycle_transitions)
                .where(records.cycle_transitions.c.cycle_id == cycle.id)
            )
        ) == 2
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.outbox)
                .where(
                    records.outbox.c.command_id
                    == select(records.commands.c.id)
                    .where(records.commands.c.command_key == request.command_key)
                    .scalar_subquery()
                )
            )
        ) == 1
