"""Legal first-party context and candidate comparison reasoning remain lossless."""

import json
from uuid import uuid4

import pytest
from test_idea_market_research import _opportunity

from alon_ai.agents.schemas.idea import (
    IdeaAgentInput,
    IdeaOperation,
    ResearchedOpportunity,
)
from alon_ai.services.combined_idea import (
    candidate_analysis_requests,
    exact_idea_text,
    profile_context_text,
    return_context_text,
)
from alon_ai.services.schemas.records import ArtifactInput, ArtifactKind


@pytest.mark.parametrize(
    "kind,key",
    [
        ("IDEA_SEED", "statement"),
        ("IDEA_CANDIDATE", "hypothesis"),
        ("IDEA_BRIEF", "core_intent"),
    ],
)
def test_legal_maximum_idea_text_is_passed_without_json_expansion(kind, key):
    text = '"' * 4000
    result = IdeaAgentInput(
        operation=IdeaOperation.SELECTED_DEEPEN,
        operator_profile_ref=uuid4(),
        profile_context="Approved operator",
        approved_limits_ref=uuid4(),
        idea_version_ref=uuid4(),
        idea_text=exact_idea_text(
            {"kind": kind, "payload": {key: text, "title": "Additional valid metadata"}}
        ),
    )
    assert result.idea_text == text


def test_full_legal_profile_envelope_is_preserved_without_truncation():
    capabilities = ["a" * 996 + f"{i:04d}" for i in range(100)]
    constraints = ["b" * 996 + f"{i:04d}" for i in range(100)]
    text = profile_context_text(
        {"capabilities": capabilities, "constraints": constraints},
        {"profile_version": 1, "profile_hash": "a" * 64},
    )
    result = IdeaAgentInput(
        operation=IdeaOperation.DISCOVER,
        operator_profile_ref=uuid4(),
        profile_context=text,
        approved_limits_ref=uuid4(),
    )
    assert len(result.profile_context) > 200000
    assert all(item in result.profile_context for item in capabilities + constraints)


def test_original_comparison_analysis_is_retained_as_unverified_hypotheses():
    option = ResearchedOpportunity.model_validate(
        {
            **_opportunity("Option", str(uuid4())),
            "customer": "c" * 4000,
            "problem": "p" * 4000,
            "approach": "a" * 4000,
            "commercial_reasoning": "m" * 4000,
            "alternatives": ["x" * 4000],
            "risks": ["r" * 4000],
        }
    )
    subject = ArtifactInput(
        artifact_id=uuid4(),
        kind=ArtifactKind.IDEA_CANDIDATE,
        version=1,
        content_hash="a" * 64,
        role="RESEARCH_SUBJECT",
    )
    run_id = uuid4()
    requests = candidate_analysis_requests(run_id, subject, option)
    assert requests == candidate_analysis_requests(run_id, subject, option)
    assert {item.finding for item in requests} == {
        option.customer,
        option.problem,
        option.approach,
        option.commercial_reasoning,
        *option.alternatives,
        *option.risks,
    }
    assert len({item.step_key for item in requests}) == 6
    assert all(
        item.evidence_status == "INCONCLUSIVE"
        and not item.sources
        and item.subject == subject
        for item in requests
    )


def test_return_context_keeps_full_brief_and_feedback_and_exact_input_whitespace():
    original = "  " + "x" * 3996 + "  "
    brief = {
        "kind": "IDEA_BRIEF",
        "payload": {
            "core_intent": original,
            "buyer": {"role": "Owner"},
            "problem": "p" * 4000,
            "assumptions": ["a" * 4000],
        },
    }
    feedback = {
        "kind": "RESEARCH_FEEDBACK_BRIEF",
        "payload": {"change": ["c" * 4000], "preserve": ["Buyer identity"]},
    }
    result = IdeaAgentInput(
        operation=IdeaOperation.REFINE,
        operator_profile_ref=uuid4(),
        profile_context="Approved operator",
        approved_limits_ref=uuid4(),
        idea_version_ref=uuid4(),
        idea_text=exact_idea_text(brief),
        revision_guidance=original,
        prior_research_summary=return_context_text(brief, [brief, feedback]),
    )
    assert result.idea_text == result.revision_guidance == original
    assert result.prior_research_summary is not None
    assert json.loads(result.prior_research_summary) == {
        "prior_idea_brief": brief["payload"],
        "research_feedback": feedback["payload"],
    }


def test_combined_runtime_configuration_rejects_unreconcilable_map(tmp_path):
    from pydantic import ValidationError
    from test_combined_idea_provision import reviewed

    from alon_ai.services.combined_idea import CombinedIdeaConfig

    manifest, _ = reviewed(tmp_path)
    raw = manifest.config.model_dump(mode="json")
    binding = raw["research_bindings"][1]
    binding["grant"]["capability"] = "FIRECRAWL_MAP"
    binding["config"]["intended_use"]["capability"] = "FIRECRAWL_MAP"
    from alon_ai.integrations.live_research import ResearchCapabilityBinding

    ResearchCapabilityBinding.model_validate_json(json.dumps(binding))
    with pytest.raises(ValidationError):
        CombinedIdeaConfig.model_validate_json(json.dumps(raw))
