"""R01A operator run contracts and Idea output safety."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from alon_ai.services.idea_safety import IdeaSafetyError, validate_idea_advice
from alon_ai.services.schemas.agent_runs import AgentRunRequest


def test_agent_run_request_accepts_only_idea_tasks():
    key = uuid4()
    request = AgentRunRequest.model_validate(
        {"task_kind": "IDEA_REFINEMENT", "command_key": str(key)}
    )
    assert request.command_key == key
    with pytest.raises(ValidationError):
        AgentRunRequest.model_validate(
            {"task_kind": "MARKET_RESEARCH", "command_key": str(key)}
        )


def _advice(**changes):
    baseline = {
        "title": "Request intake",
        "customer": "Customer to validate",
        "problem": "Request follow-up problem to validate",
        "core_intent": "Help teams track inbound requests",
        "intent_relationship": "PRESERVES_CORE_INTENT",
        "material_pivot": False,
        "buyer": {"segment": "Unverified small teams", "role": "Unverified operator"},
        "service_hypothesis": "A Python request tracking service to validate",
        "value_hypothesis": "May reduce missed requests; verify before research",
        "assumptions": ["Demand is unknown"],
        "exclusions": ["No guaranteed result"],
        "research_questions": ["Who owns follow-up?"],
        "grounding_refs": ["SEED", "OPERATOR_PROFILE"],
        "uncertainties": ["Buyer unknown"],
    }
    return {**baseline, **changes}


def test_acceptance_safety_rejects_unsupported_facts_and_capabilities():
    seed = "Help teams track inbound requests"
    capabilities = ["Python development", "Business process automation"]
    validate_idea_advice(_advice(), seed=seed, capabilities=capabilities)
    with pytest.raises(IdeaSafetyError, match="UNSUPPORTED_FACT"):
        validate_idea_advice(
            _advice(value_hypothesis="Guaranteed $100,000 yearly savings"),
            seed=seed,
            capabilities=capabilities,
        )
    with pytest.raises(IdeaSafetyError, match="CAPABILITY_UNSUPPORTED"):
        validate_idea_advice(
            _advice(service_hypothesis="We provide legal advice to clients"),
            seed=seed,
            capabilities=capabilities,
        )


def test_acceptance_safety_blocks_unrelated_and_material_pivot():
    seed = "Help teams track inbound requests"
    capabilities = ["Python development"]
    with pytest.raises(IdeaSafetyError, match="IDEA_UNRELATED"):
        validate_idea_advice(
            _advice(intent_relationship="UNRELATED"),
            seed=seed,
            capabilities=capabilities,
        )
    with pytest.raises(IdeaSafetyError, match="MATERIAL_PIVOT_REQUIRES_APPROVAL"):
        validate_idea_advice(
            _advice(intent_relationship="MATERIAL_PIVOT", material_pivot=True),
            seed=seed,
            capabilities=capabilities,
        )
