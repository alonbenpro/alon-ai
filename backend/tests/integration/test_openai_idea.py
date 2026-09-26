"""Recorded, bounded Idea Discovery and Refinement profiles."""

import asyncio
import json
from dataclasses import replace
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select
from test_governance import another, seed
from test_openai_runtime import FakeSecrets, RecordedResponses, recorded
from test_product_records import NOW, artifact, roots

from alon_ai.accounting import schema as gov
from alon_ai.openai_runtime.contract import (
    RoutingFacts,
    RoutingPolicy,
    classify_response,
)
from alon_ai.openai_runtime.idea import (
    IdeaBriefAdvice,
    IdeaCandidateSetAdvice,
    IdeaRuntime,
    IdeaStage,
    idea_profile,
)
from alon_ai.openai_runtime.runtime import AcceptedArtifact, OpenAIRuntime
from alon_ai.openai_runtime.store import OpenAIRunOutcome, OpenAIRunStore
from alon_ai.providers.contracts import Capability, UsageComponent
from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    ProductAgent,
    ProductExperiment,
    ProductRecordsRepository,
    ProductWorkflow,
)
from alon_ai.records import schema as records


@pytest.mark.parametrize(
    ("stage", "text", "expected_type"),
    [
        (
            IdeaStage.USER_SEEDED_REFINEMENT,
            '{"title":"Appointment triage","customer":"Clinics","problem":"Manual triage","core_intent":"Reduce admin time","intent_relationship":"PRESERVES_CORE_INTENT","material_pivot":false,"grounding_refs":["SEED"],"uncertainties":["Demand unverified"]}',
            IdeaBriefAdvice,
        ),
        (
            IdeaStage.SYSTEM_DISCOVERY,
            '{"candidates":[{"title":"Appointment triage 1","hypothesis":"Clinics may pay for triage","demand_status":"UNVERIFIED","grounding_refs":["OPERATOR_PROFILE"],"uncertainties":["Demand unverified"]},{"title":"Appointment triage 2","hypothesis":"Clinics may pay for triage","demand_status":"UNVERIFIED","grounding_refs":["OPERATOR_PROFILE"],"uncertainties":["Demand unverified"]},{"title":"Appointment triage 3","hypothesis":"Clinics may pay for triage","demand_status":"UNVERIFIED","grounding_refs":["OPERATOR_PROFILE"],"uncertainties":["Demand unverified"]}]}',
            IdeaCandidateSetAdvice,
        ),
        (
            IdeaStage.SYSTEM_CANDIDATE_REFINEMENT,
            '{"title":"Appointment triage","customer":"Clinics","problem":"Manual triage","core_intent":"Reduce admin time","intent_relationship":"PRESERVES_CORE_INTENT","material_pivot":false,"grounding_refs":["SELECTED_CANDIDATE"],"uncertainties":["Demand unverified"]}',
            IdeaBriefAdvice,
        ),
    ],
)
def test_recorded_idea_profiles_parse_only_stage_specific_typed_advice(
    stage, text, expected_type
):
    profile = idea_profile(
        stage,
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
    )
    parsed = classify_response(
        {
            "id": "resp_idea_fixture",
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": text}]}
            ],
            "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
        },
        profile,
    )
    assert parsed.outcome == "SUCCEEDED"
    assert isinstance(parsed.output, expected_type)


@pytest.mark.parametrize(
    ("stage", "advice"),
    [
        (
            IdeaStage.USER_SEEDED_REFINEMENT,
            {
                "title": "x",
                "customer": "y",
                "problem": "z",
                "core_intent": "q",
                "material_pivot": False,
                "grounding_refs": ["INVENTED_MARKET_REPORT"],
                "uncertainties": ["unknown"],
            },
        ),
        (
            IdeaStage.SYSTEM_DISCOVERY,
            {
                "title": "x",
                "hypothesis": "y",
                "grounding_refs": ["FABRICATED_SOURCE"],
                "uncertainties": ["unknown"],
            },
        ),
        (
            IdeaStage.SYSTEM_CANDIDATE_REFINEMENT,
            {
                "title": "x",
                "customer": "y",
                "problem": "z",
                "core_intent": "q",
                "material_pivot": False,
                "grounding_refs": ["UNSELECTED_CANDIDATE"],
                "uncertainties": ["unknown"],
            },
        ),
    ],
)
def test_fabricated_grounding_reference_is_rejected(stage, advice):
    profile = idea_profile(
        stage,
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
    )
    parsed = classify_response(recorded(text=json.dumps(advice)), profile)
    assert parsed.outcome == "SCHEMA_MISMATCH"


def test_discovery_profile_requires_three_to_five_typed_distinct_candidates():
    profile = idea_profile(
        IdeaStage.SYSTEM_DISCOVERY,
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=1200,
    )
    candidate = {
        "title": "Clinic workflow",
        "hypothesis": "Clinics might need workflow software",
        "demand_status": "UNVERIFIED",
        "grounding_refs": ["OPERATOR_PROFILE"],
        "uncertainties": ["Demand unverified"],
    }
    for size, expected in [
        (2, "SCHEMA_MISMATCH"),
        (3, "SUCCEEDED"),
        (6, "SCHEMA_MISMATCH"),
    ]:
        items = [{**candidate, "title": f"Idea {number}"} for number in range(size)]
        parsed = classify_response(
            recorded(text=json.dumps({"candidates": items})), profile
        )
        assert parsed.outcome == expected
        if expected == "SUCCEEDED":
            assert isinstance(parsed.output, IdeaCandidateSetAdvice)
            assert len(parsed.output.candidates) == 3
    invalid = [{**candidate, "title": f"Idea {number}"} for number in range(3)]
    invalid[1]["demand_status"] = "VALIDATED"
    assert (
        classify_response(
            recorded(text=json.dumps({"candidates": invalid})), profile
        ).outcome
        == "SCHEMA_MISMATCH"
    )


def test_seeded_brief_requires_typed_advisory_intent_relationship():
    profile = idea_profile(
        IdeaStage.USER_SEEDED_REFINEMENT,
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
    )
    advice = {
        "title": "Clinic intake",
        "customer": "Clinics",
        "problem": "Manual intake",
        "core_intent": "Simplify clinic intake",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["Demand unverified"],
    }
    assert (
        classify_response(recorded(text=json.dumps(advice)), profile).outcome
        == "SCHEMA_MISMATCH"
    )
    advice["intent_relationship"] = "CLARIFIES_CORE_INTENT"
    assert (
        classify_response(recorded(text=json.dumps(advice)), profile).outcome
        == "SUCCEEDED"
    )
    advice["material_pivot"] = True
    assert (
        classify_response(recorded(text=json.dumps(advice)), profile).outcome
        == "SCHEMA_MISMATCH"
    )


@pytest.mark.parametrize(
    ("stage", "field"),
    [
        (IdeaStage.SYSTEM_DISCOVERY, "title"),
        (IdeaStage.SYSTEM_DISCOVERY, "hypothesis"),
        (IdeaStage.SYSTEM_DISCOVERY, "uncertainties"),
        (IdeaStage.USER_SEEDED_REFINEMENT, "title"),
        (IdeaStage.USER_SEEDED_REFINEMENT, "customer"),
        (IdeaStage.USER_SEEDED_REFINEMENT, "problem"),
        (IdeaStage.USER_SEEDED_REFINEMENT, "core_intent"),
        (IdeaStage.USER_SEEDED_REFINEMENT, "uncertainties"),
        (IdeaStage.SYSTEM_CANDIDATE_REFINEMENT, "title"),
        (IdeaStage.SYSTEM_CANDIDATE_REFINEMENT, "customer"),
        (IdeaStage.SYSTEM_CANDIDATE_REFINEMENT, "problem"),
        (IdeaStage.SYSTEM_CANDIDATE_REFINEMENT, "core_intent"),
        (IdeaStage.SYSTEM_CANDIDATE_REFINEMENT, "uncertainties"),
    ],
)
@pytest.mark.parametrize("blank", ["", " \t "])
def test_blank_idea_advice_field_is_schema_mismatch(stage, field, blank):
    advice = (
        {
            "title": "Clinic triage",
            "hypothesis": "Clinics may need scheduling help",
            "grounding_refs": ["OPERATOR_PROFILE"],
            "uncertainties": ["Demand unverified"],
        }
        if stage is IdeaStage.SYSTEM_DISCOVERY
        else {
            "title": "Clinic triage",
            "customer": "Clinics",
            "problem": "Manual scheduling",
            "core_intent": "Reduce admin time",
            "material_pivot": False,
            "grounding_refs": [
                "SEED"
                if stage is IdeaStage.USER_SEEDED_REFINEMENT
                else "SELECTED_CANDIDATE"
            ],
            "uncertainties": ["Demand unverified"],
        }
    )
    advice[field] = [blank] if field == "uncertainties" else blank
    profile = idea_profile(
        stage,
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
    )
    parsed = classify_response(recorded(text=json.dumps(advice)), profile)
    assert parsed.outcome == "SCHEMA_MISMATCH"
    assert parsed.output is None


def test_idea_service_rejects_missing_mode_profile():
    with pytest.raises(ValueError, match="three stages"):
        IdeaRuntime(cast(ProductRecordsRepository, object()), {})


async def setup_idea(governance_engine, responses):
    default_brief = {
        "title": "default",
        "customer": "unknown",
        "problem": "unknown",
        "core_intent": "unknown",
        "intent_relationship": "PRESERVES_CORE_INTENT",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["unverified"],
    }
    all_responses = {
        IdeaStage.USER_SEEDED_REFINEMENT: default_brief,
        IdeaStage.SYSTEM_DISCOVERY: {
            "candidates": [
                {
                    "title": f"default {number}",
                    "hypothesis": "unverified",
                    "demand_status": "UNVERIFIED",
                    "grounding_refs": ["OPERATOR_PROFILE"],
                    "uncertainties": ["unverified"],
                }
                for number in range(3)
            ]
        },
        IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: {
            **default_brief,
            "grounding_refs": ["SELECTED_CANDIDATE"],
        },
        **responses,
    }
    _, operator_profile, _, _, _ = await roots(governance_engine)
    repository, admin, attribution, config, _, now = await seed(
        governance_engine,
        limit=Decimal(100),
        capability=Capability.OPENAI_GENERATE,
        price_components=(
            UsageComponent.REQUEST,
            UsageComponent.INPUT_TOKEN,
            UsageComponent.OUTPUT_TOKEN,
            UsageComponent.CACHED_TOKEN,
        ),
    )
    product = ProductRecordsRepository(governance_engine, clock=lambda: NOW)
    agent_id = uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(gov.agents).values(
                id=agent_id, workflow_id=attribution.workflow_run_id
            )
        )
    await product.bind_roots(
        ProductExperiment(
            id=attribution.experiment_id,
            operator_profile_id=operator_profile.id,
            operator_profile_version=operator_profile.version,
            name="idea-runtime-recorded",
            created_at=now,
        ),
        ProductWorkflow(
            id=attribution.workflow_run_id,
            experiment_id=attribution.experiment_id,
            role="IDEA_TO_RESEARCH",
            created_at=now,
        ),
        ProductAgent(
            id=agent_id,
            workflow_id=attribution.workflow_run_id,
            role="IDEA_DISCOVERY",
            created_at=now,
        ),
        command_key=uuid4(),
    )
    await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.EXPERIMENT_BRIEF,
            {
                "objective": "Explore capability fit",
                "target_customer": "Clinics",
                "problem": "Manual coordination",
                "geographies": ["Israel"],
                "commercial_boundaries": "No price before evidence",
                "budget_usd": "100.00",
                "evidence_definitions": ["Observe workflow"],
                "launch_stage": "SHADOW",
            },
            workflow_id=attribution.workflow_run_id,
            agent_id=agent_id,
        ),
        command_key=uuid4(),
    )
    runtimes = {}
    transports = {}
    for stage, advice in all_responses.items():
        stage_config = config.model_copy(
            update={"id": uuid4(), "secret_handle": "test-openai"}
        )
        await admin.config(stage_config)
        assert stage_config.model_identifier is not None
        profile = idea_profile(
            stage,
            config_id=stage_config.id,
            config_version=stage_config.version,
            adapter_version=stage_config.adapter_version,
            model_identifier=stage_config.model_identifier,
            reasoning_effort="low",
            max_output_tokens=300,
        )
        transport = RecordedResponses(recorded(text=json.dumps(advice)))
        runtimes[stage] = OpenAIRuntime(
            repository,
            OpenAIRunStore(governance_engine),
            routes=RoutingPolicy(
                cheap=stage_config.id, stronger=uuid4(), premium=uuid4()
            ),
            profiles={stage_config.id: profile},
            transport=transport,
            secrets=FakeSecrets(),
        )
        transports[stage] = transport
    return IdeaRuntime(product, runtimes), attribution, product, transports


@pytest.mark.integration
async def test_seeded_cycle_uses_exact_operator_seed_without_record_authority(
    governance_engine,
):
    advice = {
        "title": "Appointment triage",
        "customer": "Clinics",
        "problem": "Manual triage",
        "core_intent": "Reduce admin time",
        "intent_relationship": "PRESERVES_CORE_INTENT",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["Demand unverified"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine, {IdeaStage.USER_SEEDED_REFINEMENT: advice}
    )
    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Reduce clinic admin time"},
        ),
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    result = await service.refine_cycle(
        attribution,
        cycle_id=cycle.id,
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    assert result.outcome is OpenAIRunOutcome.SUCCEEDED
    assert isinstance(result.output, IdeaBriefAdvice)
    assert result.output.model_dump(exclude={"schema_version"}) == {
        **advice,
        "grounding_refs": ("SEED",),
        "uncertainties": ("Demand unverified",),
    }
    assert result.receipt is not None and result.receipt.accrued > 0
    sent = transports[IdeaStage.USER_SEEDED_REFINEMENT].calls
    assert len(sent) == 1
    assert "Reduce clinic admin time" in sent[0]["input_json"]
    assert str(seed_receipt.artifact_id) in sent[0]["input_json"]
    assert "Python backend development" in sent[0]["input_json"]
    assert '"grant"' not in sent[0]["input_json"]
    async with governance_engine.connect() as conn:
        assert (
            await conn.scalar(
                select(func.count()).select_from(records.idea_acceptances)
            )
            == 0
        )
        assert (
            await conn.scalar(
                select(func.count()).select_from(records.candidate_selections)
            )
            == 0
        )
        assert (
            await conn.scalar(
                select(func.count())
                .select_from(records.artifacts)
                .where(records.artifacts.c.kind == ArtifactKind.IDEA_BRIEF)
            )
            == 0
        )
    # A separate operator command turns reviewed advice into an accepted record.
    brief = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                key: advice[key]
                for key in (
                    "title",
                    "customer",
                    "problem",
                    "core_intent",
                    "material_pivot",
                )
            },
        ),
        inputs=(ArtifactInput.from_receipt(seed_receipt, role="SEED"),),
        command_key=uuid4(),
    )
    accepted = await product.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    assert accepted.artifact_id == brief.artifact_id


@pytest.mark.integration
async def test_system_discovery_then_selected_candidate_refinement_stays_advisory(
    governance_engine,
):
    candidate_advice = {
        "title": "Appointment triage",
        "hypothesis": "Clinics may pay for triage",
        "demand_status": "UNVERIFIED",
        "grounding_refs": ["OPERATOR_PROFILE"],
        "uncertainties": ["Demand unverified"],
    }
    brief_advice = {
        "title": "Appointment triage",
        "customer": "Clinics",
        "problem": "Manual triage",
        "core_intent": "Reduce admin time",
        "intent_relationship": "PRESERVES_CORE_INTENT",
        "material_pivot": False,
        "grounding_refs": ["SELECTED_CANDIDATE"],
        "uncertainties": ["Demand unverified"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine,
        {
            IdeaStage.SYSTEM_DISCOVERY: {
                "candidates": [
                    {**candidate_advice, "title": f"Appointment triage {number}"}
                    for number in range(3)
                ]
            },
            IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: brief_advice,
        },
    )
    discovered = await service.discover_system(
        attribution,
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    assert discovered.outcome is OpenAIRunOutcome.SUCCEEDED
    assert isinstance(discovered.output, IdeaCandidateSetAdvice)
    assert len(discovered.output.candidates) == 3
    discovery_input = transports[IdeaStage.SYSTEM_DISCOVERY].calls[0]["input_json"]
    assert "Python backend development" in discovery_input
    assert "Synthetic work only" in discovery_input
    async with governance_engine.connect() as conn:
        assert await conn.scalar(select(func.count()).select_from(records.cycles)) == 0
        assert (
            await conn.scalar(
                select(func.count()).select_from(records.candidate_selections)
            )
            == 0
        )
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
                "title": candidate_advice["title"],
                "hypothesis": candidate_advice["hypothesis"],
            },
            workflow_id=attribution.workflow_run_id,
            agent_id=agent_id,
        ),
        command_key=uuid4(),
    )
    selected = ArtifactInput.from_receipt(candidate, role="CANDIDATE")
    selection = await product.select_idea_candidate(
        attribution.experiment_id,
        selected,
        selected_by=UUID(int=1),
        reason="Explicit operator selection for recorded test",
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        candidate=selected,
        selection_id=selection.result_id,
        command_key=uuid4(),
    )
    refined = await service.refine_cycle(
        another(attribution),
        cycle_id=cycle.id,
        facts=RoutingFacts(needs_ai=True),
        idempotency_key=uuid4(),
    )
    assert refined.outcome is OpenAIRunOutcome.SUCCEEDED
    assert isinstance(refined.output, IdeaBriefAdvice)
    assert refined.output.model_dump(exclude={"schema_version"}) == {
        **brief_advice,
        "grounding_refs": ("SELECTED_CANDIDATE",),
        "uncertainties": ("Demand unverified",),
    }
    sent = transports[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].calls
    assert len(sent) == 1
    assert str(candidate.artifact_id) in sent[0]["input_json"]
    assert "Clinics may pay for triage" in sent[0]["input_json"]
    async with governance_engine.connect() as conn:
        assert (
            await conn.scalar(
                select(func.count()).select_from(records.idea_acceptances)
            )
            == 0
        )
        assert (
            await conn.scalar(
                select(func.count())
                .select_from(records.artifacts)
                .where(records.artifacts.c.kind == ArtifactKind.IDEA_BRIEF)
            )
            == 0
        )
    brief = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                key: brief_advice[key]
                for key in (
                    "title",
                    "customer",
                    "problem",
                    "core_intent",
                    "material_pivot",
                )
            },
        ),
        inputs=(ArtifactInput.from_receipt(candidate, role="SELECTED_CANDIDATE"),),
        command_key=uuid4(),
    )
    accepted = await product.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(brief, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    assert accepted.artifact_id == brief.artifact_id


@pytest.mark.integration
async def test_no_ai_in_both_modes_stays_zero_call(governance_engine):
    candidate = {
        "title": "x",
        "hypothesis": "y",
        "demand_status": "UNVERIFIED",
        "grounding_refs": ["OPERATOR_PROFILE"],
        "uncertainties": ["z"],
    }
    brief = {
        "title": "x",
        "customer": "y",
        "problem": "z",
        "core_intent": "q",
        "intent_relationship": "PRESERVES_CORE_INTENT",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["w"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine,
        {
            IdeaStage.SYSTEM_DISCOVERY: {
                "candidates": [
                    {**candidate, "title": f"Idea {number}"} for number in range(3)
                ]
            },
            IdeaStage.USER_SEEDED_REFINEMENT: brief,
        },
    )
    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Own seed"},
        ),
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    discovery = await service.discover_system(
        attribution, facts=RoutingFacts(needs_ai=False), idempotency_key=uuid4()
    )
    refinement = await service.refine_cycle(
        attribution,
        cycle_id=cycle.id,
        facts=RoutingFacts(needs_ai=False),
        idempotency_key=uuid4(),
    )
    assert discovery.outcome is refinement.outcome is OpenAIRunOutcome.NO_AI
    assert discovery.receipt is refinement.receipt is None
    assert all(not transport.calls for transport in transports.values())


@pytest.mark.integration
async def test_forged_seed_hash_and_operator_profile_never_dispatch(governance_engine):
    brief = {
        "title": "x",
        "customer": "y",
        "problem": "z",
        "core_intent": "q",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["w"],
    }
    candidate = {
        "title": "x",
        "hypothesis": "y",
        "grounding_refs": ["OPERATOR_PROFILE"],
        "uncertainties": ["z"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine,
        {
            IdeaStage.USER_SEEDED_REFINEMENT: brief,
            IdeaStage.SYSTEM_DISCOVERY: candidate,
        },
    )
    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Own seed"},
        ),
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    profile = await service._operator_profile(attribution.experiment_id)
    forged = ArtifactInput.from_receipt(seed_receipt, role="SEED").model_copy(
        update={"content_hash": "0" * 64}
    )
    with pytest.raises(PermissionError):
        await service.runtimes[IdeaStage.USER_SEEDED_REFINEMENT].run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            sources=(),
            artifacts=(
                AcceptedArtifact(
                    artifact=forged,
                    experiment_id=attribution.experiment_id,
                    schema_version=1,
                    cycle_id=cycle.id,
                ),
            ),
            operator_profiles=(profile,),
            idempotency_key=uuid4(),
        )
    with pytest.raises(PermissionError):
        await service.runtimes[IdeaStage.SYSTEM_DISCOVERY].run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            sources=(),
            artifacts=(),
            operator_profiles=(replace(profile, content_hash="0" * 64),),
            idempotency_key=uuid4(),
        )
    assert all(not transport.calls for transport in transports.values())


@pytest.mark.integration
async def test_candidate_refinement_requires_durable_selection_and_cycle(
    governance_engine,
):
    brief = {
        "title": "x",
        "customer": "y",
        "problem": "z",
        "core_intent": "q",
        "material_pivot": False,
        "grounding_refs": ["SELECTED_CANDIDATE"],
        "uncertainties": ["w"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine, {IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: brief}
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
            {"title": "Recorded", "hypothesis": "Unselected"},
            workflow_id=attribution.workflow_run_id,
            agent_id=agent_id,
        ),
        command_key=uuid4(),
    )
    with pytest.raises(PermissionError):
        await service.runtimes[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].run(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            sources=(),
            artifacts=(
                AcceptedArtifact(
                    artifact=ArtifactInput.from_receipt(
                        candidate, role="SELECTED_CANDIDATE"
                    ),
                    experiment_id=attribution.experiment_id,
                    schema_version=1,
                    selection_id=uuid4(),
                    cycle_id=uuid4(),
                ),
            ),
            operator_profiles=(
                await service._operator_profile(attribution.experiment_id),
            ),
            idempotency_key=uuid4(),
        )
    assert not transports[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].calls


@pytest.mark.integration
async def test_candidate_with_unchecked_record_provenance_is_not_dispatched(
    governance_engine,
):
    brief = {
        "title": "x",
        "customer": "y",
        "problem": "z",
        "core_intent": "q",
        "material_pivot": False,
        "grounding_refs": ["SELECTED_CANDIDATE"],
        "uncertainties": ["w"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine, {IdeaStage.SYSTEM_CANDIDATE_REFINEMENT: brief}
    )
    async with governance_engine.connect() as conn:
        agent_id = await conn.scalar(
            select(records.agents.c.id).where(
                records.agents.c.workflow_id == attribution.workflow_run_id
            )
        )
    assert agent_id is not None
    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Operator seed"},
        ),
        command_key=uuid4(),
    )
    candidate = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_CANDIDATE,
            {"title": "Candidate", "hypothesis": "Linked material"},
            workflow_id=attribution.workflow_run_id,
            agent_id=agent_id,
        ),
        inputs=(ArtifactInput.from_receipt(seed_receipt, role="SEED"),),
        command_key=uuid4(),
    )
    selected = ArtifactInput.from_receipt(candidate, role="CANDIDATE")
    selection = await product.select_idea_candidate(
        attribution.experiment_id,
        selected,
        selected_by=UUID(int=1),
        reason="Explicit operator selection",
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        candidate=selected,
        selection_id=selection.result_id,
        command_key=uuid4(),
    )
    with pytest.raises(PermissionError):
        await service.refine_cycle(
            attribution,
            cycle_id=cycle.id,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=uuid4(),
        )
    assert not transports[IdeaStage.SYSTEM_CANDIDATE_REFINEMENT].calls


@pytest.mark.integration
async def test_seed_with_unchecked_record_provenance_is_not_dispatched(
    governance_engine,
):
    brief = {
        "title": "x",
        "customer": "y",
        "problem": "z",
        "core_intent": "q",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["w"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine, {IdeaStage.USER_SEEDED_REFINEMENT: brief}
    )
    context = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.EXPERIMENT_BRIEF,
            {"objective": "Linked context"},
        ),
        command_key=uuid4(),
    )
    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Own seed with provenance"},
        ),
        inputs=(ArtifactInput.from_receipt(context, role="CONTEXT"),),
        command_key=uuid4(),
    )
    cycle = await product.create_cycle(
        attribution.experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    with pytest.raises(PermissionError):
        await service.refine_cycle(
            attribution,
            cycle_id=cycle.id,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=uuid4(),
        )
    assert not transports[IdeaStage.USER_SEEDED_REFINEMENT].calls


@pytest.mark.integration
async def test_superseded_seed_during_reservation_denies_dispatch(governance_engine):
    advice = {
        "title": "Clinic triage",
        "customer": "Clinics",
        "problem": "Manual scheduling",
        "core_intent": "Reduce admin time",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["Demand unverified"],
    }
    service, attribution, product, transports = await setup_idea(
        governance_engine, {IdeaStage.USER_SEEDED_REFINEMENT: advice}
    )
    seed_receipt = await product.append_artifact(
        artifact(
            attribution.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Reduce clinic admin time"},
        ),
        command_key=uuid4(),
    )
    seed_ref = ArtifactInput.from_receipt(seed_receipt, role="SEED")
    cycle = await product.create_cycle(
        attribution.experiment_id, seed=seed_ref, command_key=uuid4()
    )
    runtime = service.runtimes[IdeaStage.USER_SEEDED_REFINEMENT]
    reserve = runtime.repository.reserve
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_reserve(*args, **kwargs):
        receipt = await reserve(*args, **kwargs)
        entered.set()
        await release.wait()
        return receipt

    runtime.repository.reserve = paused_reserve
    task = asyncio.create_task(
        service.refine_cycle(
            attribution,
            cycle_id=cycle.id,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        await product.record_disposition(
            seed_ref,
            experiment_id=attribution.experiment_id,
            disposition="SUPERSEDED",
            decided_by=UUID(int=1),
            command_key=uuid4(),
        )
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transports[IdeaStage.USER_SEEDED_REFINEMENT].calls == []


@pytest.mark.integration
async def test_newer_seed_version_during_reservation_denies_dispatch(
    governance_engine,
):
    service, attribution, product, transports = await setup_idea(governance_engine, {})
    draft = artifact(
        attribution.experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Reduce clinic admin time"},
    )
    seed_receipt = await product.append_artifact(draft, command_key=uuid4())
    seed_ref = ArtifactInput.from_receipt(seed_receipt, role="SEED")
    cycle = await product.create_cycle(
        attribution.experiment_id, seed=seed_ref, command_key=uuid4()
    )
    runtime = service.runtimes[IdeaStage.USER_SEEDED_REFINEMENT]
    reserve = runtime.repository.reserve
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused_reserve(*args, **kwargs):
        receipt = await reserve(*args, **kwargs)
        entered.set()
        await release.wait()
        return receipt

    runtime.repository.reserve = paused_reserve
    task = asyncio.create_task(
        service.refine_cycle(
            attribution,
            cycle_id=cycle.id,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=uuid4(),
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 5)
        await product.append_artifact(
            artifact(
                attribution.experiment_id,
                ArtifactKind.IDEA_SEED,
                {"origin": "USER_SUPPLIED", "statement": "Newer clinic brief"},
                logical_id=draft.logical_id,
                version=2,
            ),
            inputs=(seed_ref.model_copy(update={"role": "SUPERSEDES"}),),
            command_key=uuid4(),
        )
    finally:
        release.set()
    result = await task
    assert result.output is None
    assert result.receipt is not None and result.receipt.accrued == 0
    assert transports[IdeaStage.USER_SEEDED_REFINEMENT].calls == []
