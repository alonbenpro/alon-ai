"""Labeled, offline recorded-response evaluation for the bounded Idea profiles."""

import json
from decimal import Decimal
from pathlib import Path
from time import perf_counter_ns
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_governance import another
from test_openai_idea import setup_idea
from test_product_records import artifact

from alon_ai.agents.evaluations.idea import score_recorded_idea
from alon_ai.agents.idea_discovery import (
    IdeaCandidateAdvice,
    IdeaCandidateSetAdvice,
    IdeaStage,
    SeededIdeaBriefAdvice,
    SelectedCandidateIdeaBriefAdvice,
)
from alon_ai.agents.schemas.openai import RoutingFacts
from alon_ai.db.repositories.openai_run import OpenAIRunOutcome
from alon_ai.db.tables import records
from alon_ai.services.schemas.records import ArtifactInput, ArtifactKind

FIXTURES = Path(__file__).parents[1] / "fixtures" / "openai_idea"
MODES = (
    ("user_seeded_refinement", SeededIdeaBriefAdvice),
    ("system_discovery", IdeaCandidateAdvice),
    ("selected_candidate_refinement", SelectedCandidateIdeaBriefAdvice),
)


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize(("name", "advice_type"), MODES)
def test_recorded_advice_scores_exact_input_evidence_and_constraints(name, advice_type):
    case = fixture(name)
    advice = advice_type.model_validate_json(json.dumps(case["advice"]))
    report = score_recorded_idea(advice, case)
    assert report.mode is IdeaStage(case["mode"])
    assert report.grounding == 1
    assert report.coverage == 1
    assert report.safety == 1
    assert report.offline_runtime_ms is None
    assert report.offline_transport_ms is None
    assert report.cost_usd is None
    assert report.claims
    assert report.constraints
    assert all(finding.satisfied for finding in report.claims + report.constraints)
    assert all(
        finding.expected is not None for finding in report.claims + report.constraints
    )
    for claim in report.claims:
        if claim.evidence_id in case["source_facts"]:
            assert claim.evidence_text == case["source_facts"][claim.evidence_id]
        else:
            assert claim.evidence_id == "DISCOVERY.UNVALIDATED_PROPOSAL"
            assert "unvalidated" in claim.evidence_text.lower()
    assert {
        finding.evidence_id: finding.evidence_text for finding in report.constraints
    } == {constraint["id"]: constraint["basis"] for constraint in case["constraints"]}


@pytest.mark.parametrize(("name", "advice_type"), MODES)
def test_recorded_adversaries_name_each_violated_fact_or_constraint(name, advice_type):
    case = fixture(name)
    for adversary in case["adversarial"]:
        changed = {**case["advice"], **adversary["changes"]}
        advice = advice_type.model_validate_json(json.dumps(changed))
        report = score_recorded_idea(advice, case)
        violations = {
            finding.evidence_id
            for finding in report.claims + report.constraints
            if not finding.satisfied
        }
        assert set(adversary["violates"]) <= violations, adversary["id"]
        assert min(report.grounding, report.coverage, report.safety) < 1


def test_eval_rejects_unlabeled_expected_claim():
    case = fixture("user_seeded_refinement")
    case["expected_claims"][0]["source_fact"] = "MISSING.SOURCE"
    advice = SeededIdeaBriefAdvice.model_validate_json(json.dumps(case["advice"]))
    with pytest.raises(ValueError, match="unknown source fact"):
        score_recorded_idea(advice, case)


def test_eval_rejects_advice_from_another_mode():
    case = fixture("user_seeded_refinement")
    case["mode"] = "SYSTEM_DISCOVERY"
    advice = SeededIdeaBriefAdvice.model_validate_json(json.dumps(case["advice"]))
    with pytest.raises(TypeError, match="mode and advice type disagree"):
        score_recorded_idea(advice, case)


def _measure_transports(monkeypatch, transports, cases):
    transport_ns = {stage: 0 for stage in cases}
    for stage, case in cases.items():
        transport = transports[stage]
        transport.response["usage"] = case["usage"]
        create = transport.create

        async def timed_create(*, _create=create, _stage=stage, **kwargs):
            started = perf_counter_ns()
            try:
                return await _create(**kwargs)
            finally:
                transport_ns[_stage] += perf_counter_ns() - started

        monkeypatch.setattr(transport, "create", timed_create)
    return transport_ns


def _score_run(stage, run, case, elapsed_ns, transport_ns, transport):
    assert run.outcome is OpenAIRunOutcome.SUCCEEDED
    assert run.output is not None and run.receipt is not None
    report = score_recorded_idea(
        run.output.candidates[0]
        if isinstance(run.output, IdeaCandidateSetAdvice)
        else run.output,
        case,
        cost_usd=run.receipt.accrued,
        offline_runtime_ms=elapsed_ns / 1_000_000,
        offline_transport_ms=transport_ns / 1_000_000,
    )
    assert report.mode is stage
    assert (report.grounding, report.coverage, report.safety) == (1, 1, 1)
    assert report.offline_runtime_ms is not None
    assert report.offline_transport_ms is not None
    assert report.cost_usd is not None
    assert report.offline_runtime_ms > 0
    assert report.offline_transport_ms > 0
    assert report.offline_runtime_ms >= report.offline_transport_ms
    assert report.cost_usd > Decimal(0)
    assert len(transport.calls) == 1
    print(
        f"{stage.value}: offline_runtime_ms={report.offline_runtime_ms:.3f} "
        f"offline_transport_ms={report.offline_transport_ms:.3f} "
        f"ledger_cost_usd={report.cost_usd} "
        f"grounding={report.grounding:.2f} coverage={report.coverage:.2f} "
        f"safety={report.safety:.2f}"
    )
    return report


@pytest.mark.integration
async def test_seeded_recorded_eval_cost_and_measured_offline_time(
    governance_engine, monkeypatch
):
    stage = IdeaStage.USER_SEEDED_REFINEMENT
    seeded = fixture("user_seeded_refinement")
    service, attribution, product, transports = await setup_idea(
        governance_engine, {stage: seeded["advice"]}
    )
    transport_ns = _measure_transports(monkeypatch, transports, {stage: seeded})

    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {
                "origin": "USER_SUPPLIED",
                "statement": seeded["source_facts"]["SEED.GOAL"],
            },
        ),
        command_key=uuid4(),
    )
    seed_cycle = await product.create_cycle(
        attribution.experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    no_ai_seeded = await service.refine_cycle(
        attribution,
        cycle_id=seed_cycle.id,
        facts=RoutingFacts(needs_ai=False),
        idempotency_key=uuid4(),
    )
    assert no_ai_seeded.outcome is OpenAIRunOutcome.NO_AI
    assert no_ai_seeded.receipt is None
    assert not transports[stage].calls
    started = perf_counter_ns()
    seeded_run = await service.refine_cycle(
        attribution,
        cycle_id=seed_cycle.id,
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    seeded_ns = perf_counter_ns() - started
    seeded_input = json.loads(transports[stage].calls[0]["input_json"])
    assert (
        seeded_input["artifacts"][0]["payload"]["statement"]
        == seeded["source_facts"]["SEED.GOAL"]
    )
    assert (
        seeded["source_facts"]["PROFILE.CAPABILITY"]
        in seeded_input["operator_profiles"][0]["capabilities"]
    )
    assert (
        seeded["source_facts"]["PROFILE.CONSTRAINT"]
        in seeded_input["operator_profiles"][0]["constraints"]
    )
    report = _score_run(
        stage, seeded_run, seeded, seeded_ns, transport_ns[stage], transports[stage]
    )
    assert report.cost_usd == Decimal("0.037000000000")


@pytest.mark.integration
async def test_system_and_selected_recorded_eval_cost_and_measured_offline_time(
    governance_engine, monkeypatch
):
    discovery = fixture("system_discovery")
    selected = fixture("selected_candidate_refinement")
    cases = {
        IdeaStage.SYSTEM_DISCOVERY: discovery,
        IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: selected,
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine,
        {
            IdeaStage.SYSTEM_DISCOVERY: {
                "candidates": [
                    discovery["advice"],
                    {
                        **discovery["advice"],
                        "title": "Synthetic clinic scheduling backend 2",
                    },
                    {
                        **discovery["advice"],
                        "title": "Synthetic clinic scheduling backend 3",
                    },
                ]
            },
            IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: selected["advice"],
        },
    )
    transport_ns = _measure_transports(monkeypatch, transports, cases)
    no_ai_discovery = await service.discover_system(
        attribution,
        facts=RoutingFacts(needs_ai=False),
        idempotency_key=uuid4(),
    )
    assert no_ai_discovery.outcome is OpenAIRunOutcome.NO_AI
    assert no_ai_discovery.receipt is None
    assert all(not transport.calls for transport in transports.values())
    started = perf_counter_ns()
    discovery_run = await service.discover_system(
        another(attribution),
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    discovery_ns = perf_counter_ns() - started
    assert isinstance(discovery_run.output, IdeaCandidateSetAdvice)
    discovery_input = json.loads(
        transports[IdeaStage.SYSTEM_DISCOVERY].calls[0]["input_json"]
    )
    assert (
        discovery["source_facts"]["PROFILE.CAPABILITY"]
        in discovery_input["operator_profiles"][0]["capabilities"]
    )
    assert (
        discovery["source_facts"]["PROFILE.CONSTRAINT"]
        in discovery_input["operator_profiles"][0]["constraints"]
    )
    assert (
        selected["source_facts"]["CANDIDATE.TITLE"]
        == discovery_run.output.candidates[0].title
    )
    assert (
        selected["source_facts"]["CANDIDATE.HYPOTHESIS"]
        == discovery_run.output.candidates[0].hypothesis
    )
    async with governance_engine.connect() as conn:
        agent_id = await conn.scalar(
            select(records.agents.c.id).where(
                records.agents.c.workflow_id == attribution.workflow_run_id
            )
        )
    assert agent_id is not None
    candidate = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_CANDIDATE,
            {
                "title": discovery_run.output.candidates[0].title,
                "hypothesis": discovery_run.output.candidates[0].hypothesis,
            },
            workflow_id=attribution.workflow_run_id,
            agent_id=agent_id,
        ),
        command_key=uuid4(),
    )
    candidate_input = ArtifactInput.from_receipt(candidate, role="CANDIDATE")
    selection = await product.select_idea_candidate(
        attribution.experiment_id,
        candidate_input,
        selected_by=UUID(int=1),
        reason="Explicit operator selection for offline recorded evaluation",
        command_key=uuid4(),
    )
    selected_cycle = await product.create_cycle(
        attribution.experiment_id,
        candidate=candidate_input,
        selection_id=selection.result_id,
        command_key=uuid4(),
    )
    no_ai_selected = await service.refine_cycle(
        another(attribution),
        cycle_id=selected_cycle.id,
        facts=RoutingFacts(needs_ai=False),
        idempotency_key=uuid4(),
    )
    assert no_ai_selected.outcome is OpenAIRunOutcome.NO_AI
    assert no_ai_selected.receipt is None
    assert not transports[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].calls
    started = perf_counter_ns()
    selected_run = await service.refine_cycle(
        another(attribution),
        cycle_id=selected_cycle.id,
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    selected_ns = perf_counter_ns() - started
    selected_input = json.loads(
        transports[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].calls[0]["input_json"]
    )
    assert selected_input["artifacts"][0]["payload"] == {
        "title": selected["source_facts"]["CANDIDATE.TITLE"],
        "hypothesis": selected["source_facts"]["CANDIDATE.HYPOTHESIS"],
    }

    reports = {}
    for stage, run, elapsed in (
        (IdeaStage.SYSTEM_DISCOVERY, discovery_run, discovery_ns),
        (IdeaStage.SYSTEM_CANDIDATE_REFINEMENT, selected_run, selected_ns),
    ):
        reports[stage] = _score_run(
            stage,
            run,
            cases[stage],
            elapsed,
            transport_ns[stage],
            transports[stage],
        )
    assert reports[IdeaStage.SYSTEM_DISCOVERY].cost_usd == Decimal("0.024000000000")
    assert reports[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].cost_usd == Decimal(
        "0.029000000000"
    )
