"""The combined Idea agent's native typed output and bounded result contracts."""

import json
from typing import cast
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import UsageLimits

from alon_ai.agents.idea_agent import run_idea_agent
from alon_ai.agents.idea_discovery import IdeaBriefAdvice, IdeaStage
from alon_ai.agents.schemas.idea import (
    IdeaAgentInput,
    IdeaOperation,
    IncompleteDiscovery,
    MarketResearchAssessment,
    PriceObservation,
    ResearchedCandidateSet,
)
from alon_ai.integrations.pydantic_openai import build_openai_model


def _opportunity(name: str, source: str) -> dict[str, object]:
    return {
        "title": name,
        "customer": "Small dental clinics",
        "problem": f"{name} workflow burden",
        "approach": f"Software for {name}",
        "commercial_reasoning": "A buyer may pay to reduce administration; willingness to pay is unknown.",
        "alternatives": ["Manual spreadsheet"],
        "risks": ["Clinic software integration needs validation"],
        "source_refs": [source],
        "findings": [
            {
                "topic": "CUSTOMER_PROBLEM",
                "basis": "OBSERVED",
                "claim": "A published clinic workflow describes manual follow-up.",
                "source_refs": [source],
                "confidence": "MEDIUM",
                "limitations": ["One public example does not establish market demand"],
            }
        ],
        "unknowns": ["Actual budget"],
    }


def _input() -> IdeaAgentInput:
    return IdeaAgentInput(
        operation=IdeaOperation.DISCOVER,
        operator_profile_ref=uuid4(),
        profile_context="Python developer in Israel; small-business software",
        approved_limits_ref=uuid4(),
    )


def _assessment(version_ref: str) -> dict[str, object]:
    return {
        "status": "ASSESSED",
        "idea_version_ref": version_ref,
        "brief": {
            "title": "Clinic appointment reminders",
            "customer": "Small dental clinics",
            "problem": "Missed appointments",
            "core_intent": "Appointment reminders",
            "intent_relationship": "PRESERVES_CORE_INTENT",
            "material_pivot": False,
            "buyer": {"segment": "Small dental clinics", "role": "Practice manager"},
            "service_hypothesis": "Reminder software may help clinics",
            "value_hypothesis": "Reduced missed appointments is unverified",
            "assumptions": ["Clinic demand requires validation"],
            "exclusions": ["No medical-record integration"],
            "research_questions": ["Who pays for reminders?"],
            "grounding_refs": ["SELECTED_CANDIDATE"],
            "uncertainties": ["Willingness to pay unknown"],
        },
        "findings": [
            {
                "topic": "CUSTOMER_PROBLEM",
                "basis": "OBSERVED",
                "claim": "Public clinic guidance discusses appointment reminders.",
                "source_refs": ["src-a"],
                "confidence": "MEDIUM",
                "limitations": ["No verified spending signal"],
            }
        ],
        "coverage": ["CUSTOMER_PROBLEM"],
        "gaps": ["Willingness to pay remains unknown"],
        "contradictions": [],
        "source_refs": ["src-a"],
        "recommendation": "INCONCLUSIVE",
    }


def _deepening_input() -> IdeaAgentInput:
    return IdeaAgentInput(
        operation=IdeaOperation.SELECTED_DEEPEN,
        operator_profile_ref=uuid4(),
        profile_context="Python developer in Israel",
        approved_limits_ref=uuid4(),
        idea_version_ref=uuid4(),
        idea_text="Clinic appointment reminders",
    )


@pytest.mark.parametrize("stage", list(IdeaStage))
def test_native_input_retains_trusted_origin_stage(stage: IdeaStage):
    input = _input() if stage is IdeaStage.SYSTEM_DISCOVERY else _deepening_input()

    resolved = IdeaAgentInput.model_validate(
        {**input.model_dump(), "origin_stage": stage}
    )

    assert resolved.origin_stage is stage


def _assessment_correction_outputs(
    input: IdeaAgentInput,
) -> tuple[dict[str, object], dict[str, object]]:
    corrected = _assessment(str(input.idea_version_ref))
    observed = cast(list[dict[str, object]], corrected["findings"])[0]
    unknown = {
        "topic": "DEMAND_AND_SPENDING",
        "basis": "UNKNOWN",
        "claim": "Clinic willingness to pay is unknown.",
        "source_refs": [],
        "confidence": "LOW",
        "limitations": ["No buyer spending evidence retained"],
    }
    inferred = {
        "topic": "ALTERNATIVES",
        "basis": "INFERRED",
        "claim": "Manual reminders may be an alternative.",
        "source_refs": [],
        "confidence": "LOW",
        "limitations": ["Prevalence has not been established"],
    }
    corrected["findings"] = [observed, unknown, inferred]
    invalid = {
        **corrected,
        "findings": [
            {**observed, "source_refs": []},
            {**unknown, "source_refs": ["src-a"]},
            inferred,
        ],
    }
    return invalid, corrected


def _scripted_native_model(
    outputs: list[dict[str, object]],
) -> tuple[FunctionModel, list[list[ModelMessage]]]:
    requests: list[list[ModelMessage]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        requests.append(list(messages))
        return ModelResponse(parts=[TextPart(json.dumps(outputs[len(requests) - 1]))])

    return (
        FunctionModel(respond, profile={"supports_json_schema_output": True}),
        requests,
    )


def _grounded_assessment(
    input: IdeaAgentInput, grounding_refs: list[str]
) -> dict[str, object]:
    output = _assessment(str(input.idea_version_ref))
    output["brief"] = {
        **cast(dict[str, object], output["brief"]),
        "grounding_refs": grounding_refs,
    }
    return output


@pytest.mark.parametrize(
    "stage,invalid_refs,corrected_refs",
    [
        (IdeaStage.USER_SEEDED_REFINEMENT, ["src-a"], ["SEED"]),
        (
            IdeaStage.USER_SEEDED_REFINEMENT,
            ["SELECTED_CANDIDATE"],
            ["SEED", "OPERATOR_PROFILE"],
        ),
        (
            IdeaStage.SYSTEM_CANDIDATE_REFINEMENT,
            ["SEED"],
            ["SELECTED_CANDIDATE", "OPERATOR_PROFILE"],
        ),
        (
            IdeaStage.RESEARCH_FEEDBACK_REFINEMENT,
            ["SELECTED_CANDIDATE"],
            ["PRIOR_IDEA_BRIEF", "RESEARCH_FEEDBACK"],
        ),
        (
            IdeaStage.RESEARCH_FEEDBACK_REFINEMENT,
            ["PRIOR_IDEA_BRIEF", "RESEARCH_FEEDBACK", "RESEARCH_FEEDBACK"],
            ["PRIOR_IDEA_BRIEF", "RESEARCH_FEEDBACK"],
        ),
    ],
)
async def test_native_assessment_corrects_origin_grounding_before_completion(
    stage: IdeaStage, invalid_refs: list[str], corrected_refs: list[str]
):
    input = IdeaAgentInput.model_validate(
        {**_deepening_input().model_dump(), "origin_stage": stage}
    )
    model, requests = _scripted_native_model(
        [
            _grounded_assessment(input, invalid_refs),
            _grounded_assessment(input, corrected_refs),
        ]
    )

    result = await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert isinstance(result.output, MarketResearchAssessment)
    assert result.output.brief.grounding_refs == tuple(corrected_refs)
    assert result.output.source_refs == ("src-a",)
    assert result.usage.requests == len(requests) == 2
    instructions = "\n".join(
        message.instructions or ""
        for message in requests[0]
        if isinstance(message, ModelRequest)
    )
    assert "brief.grounding_refs" in instructions
    assert all(ref in instructions for ref in corrected_refs)
    assert str(input.idea_version_ref) in instructions


@pytest.mark.parametrize(
    "stage",
    [
        IdeaStage.USER_SEEDED_REFINEMENT,
        IdeaStage.SYSTEM_CANDIDATE_REFINEMENT,
        IdeaStage.RESEARCH_FEEDBACK_REFINEMENT,
    ],
)
async def test_native_assessment_rejects_persistently_wrong_origin_grounding(
    stage: IdeaStage,
):
    input = IdeaAgentInput.model_validate(
        {**_deepening_input().model_dump(), "origin_stage": stage}
    )
    invalid = _grounded_assessment(input, ["invented-source"])
    model, requests = _scripted_native_model([invalid, invalid])

    with pytest.raises(UnexpectedModelBehavior, match="output retries"):
        await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert len(requests) == 2


async def test_native_assessment_corrects_wrong_idea_version_before_completion():
    input = _deepening_input()
    corrected = _assessment(str(input.idea_version_ref))
    invalid = {**corrected, "idea_version_ref": str(uuid4())}
    model, requests = _scripted_native_model([invalid, corrected])

    result = await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert isinstance(result.output, MarketResearchAssessment)
    assert result.output.idea_version_ref == input.idea_version_ref
    assert result.usage.requests == len(requests) == 2


async def test_native_assessment_rejects_persistently_wrong_idea_version():
    input = _deepening_input()
    invalid = _assessment(str(uuid4()))
    model, requests = _scripted_native_model([invalid, invalid])

    with pytest.raises(UnexpectedModelBehavior, match="output retries"):
        await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert len(requests) == 2


async def test_native_assessment_corrects_source_basis_errors_once():
    input = _deepening_input()
    invalid, corrected = _assessment_correction_outputs(input)
    model, requests = _scripted_native_model([invalid, corrected])

    result = await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert isinstance(result.output, MarketResearchAssessment)
    assert result.output.idea_version_ref == input.idea_version_ref
    assert result.output.findings[0].source_refs == ("src-a",)
    assert result.output.findings[1].source_refs == ()
    assert result.usage.requests == len(requests) == 2
    feedback = [
        part
        for message in requests[1]
        for part in message.parts
        if isinstance(part, RetryPromptPart)
    ]
    assert len(feedback) == 1
    assert isinstance(feedback[0].content, list)
    assert [
        (error["type"], error["loc"], error["msg"]) for error in feedback[0].content
    ] == [
        (
            "value_error",
            ("findings", 0),
            "Value error, observed finding requires a source",
        ),
        (
            "value_error",
            ("findings", 1),
            "Value error, unknown finding cannot claim source support",
        ),
    ]


@pytest.mark.parametrize(
    "changes,kind,location",
    [
        ({"material_pivot": True}, "value_error", ("brief",)),
        ({"title": "   "}, "string_too_short", ("brief", "title")),
        (
            {"title": {"PRIVATE_KEY": "PRIVATE_VALUE"}},
            "string_type",
            ("brief", "title"),
        ),
        ({"material_pivot": "false"}, "bool_type", ("brief", "material_pivot")),
        ({"PRIVATE_KEY": "PRIVATE_VALUE"}, "extra_forbidden", ("brief", 0)),
        (
            {"buyer": {"PRIVATE_KEY": "PRIVATE_VALUE"}},
            "literal_error",
            ("brief", "buyer", 0, 0),
        ),
    ],
)
async def test_native_brief_correction_feedback_preserves_safe_field_reason(
    changes: dict[str, object], kind: str, location: tuple[str | int, ...]
):
    input = _deepening_input()
    corrected = _assessment(str(input.idea_version_ref))
    invalid = {
        **corrected,
        "brief": {**cast(dict[str, object], corrected["brief"]), **changes},
    }
    model, requests = _scripted_native_model([invalid, corrected])

    result = await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert isinstance(result.output, MarketResearchAssessment)
    assert result.output.brief == IdeaBriefAdvice.model_validate_json(
        json.dumps(corrected["brief"])
    )
    assert result.usage.requests == len(requests) == 2
    feedback = [
        part
        for message in requests[1]
        for part in message.parts
        if isinstance(part, RetryPromptPart)
    ]
    assert len(feedback) == 1
    assert isinstance(feedback[0].content, list)
    assert [(error["type"], error["loc"]) for error in feedback[0].content] == [
        (kind, location)
    ]
    assert all(error["input"] is None for error in feedback[0].content)
    assert all("ctx" not in error for error in feedback[0].content)
    serialized = json.dumps(feedback[0].content)
    assert "PRIVATE" not in serialized
    assert "Clinic appointment reminders" not in serialized
    if kind == "value_error":
        assert feedback[0].content[0]["msg"] == (
            "Value error, pivot flag and intent relationship disagree"
        )


async def test_native_brief_shape_error_can_be_corrected():
    input = _deepening_input()
    corrected = _assessment(str(input.idea_version_ref))
    model, requests = _scripted_native_model(
        [{**corrected, "brief": ["PRIVATE_VALUE"]}, corrected]
    )

    result = await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert isinstance(result.output, MarketResearchAssessment)
    assert result.usage.requests == len(requests) == 2


@pytest.mark.parametrize(
    "changes,frame",
    [
        ({"material_pivot": True}, "value_error:brief:PIVOT_CLASSIFICATION_MISMATCH"),
        ({"title": {"PRIVATE_KEY": "PRIVATE_VALUE"}}, "string_type:brief.title"),
        (
            {"buyer": {"PRIVATE_KEY": "PRIVATE_VALUE"}},
            "literal_error:brief.buyer.[].[]",
        ),
    ],
)
def test_native_brief_diagnostic_preserves_reason_without_raw_context(
    changes: dict[str, object], frame: str
):
    from alon_ai.services.run_diagnostics import diagnostic_for_error

    output = _assessment(str(uuid4()))
    output["brief"] = {
        **cast(dict[str, object], output["brief"]),
        "title": "PRIVATE_VALUE",
        **changes,
    }
    with pytest.raises(ValidationError) as raised:
        MarketResearchAssessment.model_validate_json(json.dumps(output))

    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert all(error["input"] is None for error in raised.value.errors())
    assert "PRIVATE" not in str(raised.value)
    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)
    assert frame in diagnostic.frames
    assert "PRIVATE" not in diagnostic.model_dump_json()


async def test_invalid_native_brief_stops_after_one_correction_with_safe_diagnostic():
    from alon_ai.services.run_diagnostics import diagnostic_for_error

    input = _deepening_input()
    invalid = _assessment(str(input.idea_version_ref))
    invalid["brief"] = {
        **cast(dict[str, object], invalid["brief"]),
        "title": {"PRIVATE_KEY": "PRIVATE_VALUE"},
    }
    model, requests = _scripted_native_model([invalid, invalid])

    with pytest.raises(UnexpectedModelBehavior, match="output retries") as raised:
        await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert len(requests) == 2
    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)
    assert "string_type:brief.title" in diagnostic.frames
    assert "PRIVATE" not in diagnostic.model_dump_json()


def test_original_brief_provider_contract_still_hides_field_errors():
    brief = cast(dict[str, object], _assessment(str(uuid4()))["brief"])
    with pytest.raises(ValidationError) as raised:
        IdeaBriefAdvice.model_validate_json(
            json.dumps({**brief, "title": {"PRIVATE_KEY": "PRIVATE_VALUE"}})
        )

    assert raised.value.errors(include_url=False, include_context=False) == [
        {
            "type": "value_error",
            "loc": (),
            "msg": "Value error, invalid provider contract",
            "input": None,
        }
    ]
    assert "PRIVATE" not in str(raised.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "  Clinic workflow  "},
        {"title": "   "},
        {"title": 123},
        {"material_pivot": "false"},
        {"material_pivot": True},
        {"intent_relationship": "UNRECOGNIZED"},
        {"assumptions": []},
        {"assumptions": "not an array"},
        {"PRIVATE_KEY": "PRIVATE_VALUE"},
        {"buyer": {"PRIVATE_KEY": "PRIVATE_VALUE"}},
    ],
)
def test_native_brief_acceptance_matches_existing_strict_contract(
    changes: dict[str, object],
):
    output = _assessment(str(uuid4()))
    raw = {**cast(dict[str, object], output["brief"]), **changes}
    output["brief"] = raw
    try:
        expected = IdeaBriefAdvice.model_validate_json(json.dumps(raw))
    except ValidationError:
        with pytest.raises(ValidationError):
            MarketResearchAssessment.model_validate_json(json.dumps(output))
    else:
        actual = MarketResearchAssessment.model_validate_json(json.dumps(output))
        assert actual.brief == expected
        assert actual.brief.title == "Clinic workflow"


async def test_native_assessment_stops_after_one_failed_correction():
    input = _deepening_input()
    invalid, _ = _assessment_correction_outputs(input)
    model, requests = _scripted_native_model([invalid, invalid])

    with pytest.raises(UnexpectedModelBehavior, match="output retries"):
        await run_idea_agent(input, model=model, toolset=FunctionToolset())

    assert len(requests) == 2


async def test_native_assessment_correction_respects_request_limit():
    input = _deepening_input()
    invalid, corrected = _assessment_correction_outputs(input)
    model, requests = _scripted_native_model([invalid, corrected])

    with pytest.raises(UsageLimitExceeded, match="request_limit of 1"):
        await run_idea_agent(
            input,
            model=model,
            toolset=FunctionToolset(),
            usage_limits=UsageLimits(request_limit=1),
        )

    assert len(requests) == 1


def test_successful_discovery_requires_three_distinct_researched_options():
    options = [
        _opportunity("Reminders", "src-a"),
        _opportunity("Intake", "src-b"),
        _opportunity("Scheduling", "src-c"),
    ]
    success = ResearchedCandidateSet.model_validate(
        {"status": "SUCCEEDED", "options": options}
    )
    assert len(success.options) == 3
    with pytest.raises(ValidationError):
        ResearchedCandidateSet.model_validate(
            {"status": "SUCCEEDED", "options": options[:2]}
        )
    with pytest.raises(ValidationError):
        ResearchedCandidateSet.model_validate(
            {"status": "SUCCEEDED", "options": [options[0]] * 3}
        )


def test_two_supported_options_are_explicitly_incomplete():
    incomplete = IncompleteDiscovery.model_validate(
        {
            "status": "INCOMPLETE",
            "options": [
                _opportunity("Reminders", "src-a"),
                _opportunity("Intake", "src-b"),
            ],
            "gaps": ["Third option lacks credible retained evidence"],
        }
    )
    assert len(incomplete.options) == 2
    assert incomplete.gaps == ("Third option lacks credible retained evidence",)


def test_price_kinds_do_not_invent_or_blur_numeric_observations():
    exact = PriceObservation.model_validate(
        {
            "subject": "Published reminder plan",
            "kind": "EXACT",
            "currency": "USD",
            "amount_low": "29.99",
            "unit": "month",
            "source_refs": ["src-price"],
        }
    )
    assert str(exact.amount_low) == "29.99"
    with pytest.raises(ValidationError):
        PriceObservation.model_validate({**exact.model_dump(), "amount_high": "39.99"})
    with pytest.raises(ValidationError):
        PriceObservation.model_validate({**exact.model_dump(), "amount_low": "NaN"})
    with pytest.raises(ValidationError):
        PriceObservation.model_validate(
            {
                "subject": "Unlisted price",
                "kind": "NOT_FOUND",
                "amount_low": "5",
            }
        )
    quote = PriceObservation.model_validate(
        {
            "subject": "Contact sales offer",
            "kind": "QUOTE_ONLY",
            "source_refs": ["src-quote"],
        }
    )
    assert quote.amount_low is None


async def test_discovery_invokes_real_agent_with_toolset_and_native_typed_output():
    searches: list[str] = []

    def search_web(query: str) -> str:
        """Search approved public web sources."""
        searches.append(query)
        return "src-a: clinic workflow; src-b: intake; src-c: scheduling"

    toolset = FunctionToolset([search_web])
    output = {
        "status": "SUCCEEDED",
        "options": [
            _opportunity("Reminders", "src-a"),
            _opportunity("Intake", "src-b"),
            _opportunity("Scheduling", "src-c"),
        ],
    }
    result = await run_idea_agent(
        _input(),
        model=TestModel(
            custom_output_text=json.dumps(
                {"result": {"kind": "ResearchedCandidateSet", "data": output}}
            ),
            profile={"supports_json_schema_output": True},
        ),
        toolset=toolset,
    )
    assert isinstance(result.output, ResearchedCandidateSet)
    assert [item.title for item in result.output.options] == [
        "Reminders",
        "Intake",
        "Scheduling",
    ]
    assert searches
    assert result.usage.requests >= 1


async def test_agent_can_return_explicit_incomplete_discovery():
    output = {
        "status": "INCOMPLETE",
        "options": [
            _opportunity("Reminders", "src-a"),
            _opportunity("Intake", "src-b"),
        ],
        "gaps": ["No defensible third option within approved limits"],
    }
    result = await run_idea_agent(
        _input(),
        model=TestModel(
            custom_output_text=json.dumps(
                {"result": {"kind": "IncompleteDiscovery", "data": output}}
            ),
            profile={"supports_json_schema_output": True},
        ),
        toolset=FunctionToolset(),
    )
    assert isinstance(result.output, IncompleteDiscovery)
    assert len(result.output.options) == 2


@pytest.mark.parametrize(
    ("operation", "revision_guidance"),
    [
        (IdeaOperation.SELECTED_DEEPEN, None),
        (IdeaOperation.REFINE, "Avoid medical-record integrations"),
    ],
)
async def test_deepening_and_refinement_return_exact_version_assessment(
    operation: IdeaOperation, revision_guidance: str | None
):
    version_ref = uuid4()
    result = await run_idea_agent(
        IdeaAgentInput(
            operation=operation,
            operator_profile_ref=uuid4(),
            profile_context="Python developer in Israel",
            approved_limits_ref=uuid4(),
            idea_version_ref=version_ref,
            idea_text="Clinic appointment reminders",
            revision_guidance=revision_guidance,
        ),
        model=TestModel(
            custom_output_text=json.dumps(_assessment(str(version_ref))),
            profile={"supports_json_schema_output": True},
        ),
        toolset=FunctionToolset(),
    )
    assert isinstance(result.output, MarketResearchAssessment)
    assert result.output.idea_version_ref == version_ref
    assert result.output.gaps == ("Willingness to pay remains unknown",)


def test_openai_model_uses_responses_with_no_sdk_retries_or_storage():
    model = build_openai_model(
        model_identifier="gpt-5",
        secret=SecretStr("test-only-not-a-real-key"),
        timeout_seconds=30,
        max_output_tokens=1200,
        reasoning_effort="low",
    )
    assert isinstance(model, OpenAIResponsesModel)
    assert model.model_name == "gpt-5"
    settings = cast(OpenAIResponsesModelSettings, model.settings)
    assert settings.get("openai_store") is False
    assert settings.get("max_tokens") == 1200
    provider = model.provider
    assert isinstance(provider, OpenAIProvider)
    assert provider.client.max_retries == 0
