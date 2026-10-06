"""Sanitized, durable operator diagnostics for failed agent runs."""

from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from alon_ai.agents.tools.research import ResearchToolError, ResearchTools
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.integrations.schemas.provider import ProviderErrorCode, ProviderFailure
from alon_ai.provider_usage.schemas.accounting import AccountingDenied, Reason
from alon_ai.services.run_diagnostics import diagnostic_for_error


def test_model_request_limit_diagnostic_requires_configuration_change():
    diagnostic = diagnostic_for_error(
        "PROVIDER_PROVISIONING", ExperimentError(409, "MODEL_REQUEST_LIMIT_TOO_LOW")
    )

    assert "per-run" in diagnostic.message
    assert "at least two" in diagnostic.message
    assert "renew" not in diagnostic.message.lower()


@pytest.mark.parametrize(
    "error,provider",
    [
        (AccountingDenied(Reason.QUOTA), None),
        (ResearchToolError("QUOTA"), None),
        (ExperimentError(409, "MODEL_ALLOWANCE_EXHAUSTED"), "OpenAI"),
        (ExperimentError(409, "CAPTURE_ALLOWANCE_EXHAUSTED"), "Firecrawl"),
    ],
)
def test_local_allowance_diagnostic_identifies_local_block_and_recovery(
    error, provider
):
    diagnostic = diagnostic_for_error("PROVISIONING", error)

    assert "local" in diagnostic.message.lower()
    assert "allowance" in diagnostic.message.lower()
    assert "renew" in diagnostic.message.lower()
    assert "before" in diagnostic.message.lower()
    if provider:
        assert provider in diagnostic.message


@pytest.mark.parametrize(
    "code,message",
    [
        (
            "EVIDENCE_READ_INPUT_INVALID",
            "The evidence read requires a valid saved reference and 1–4,000 characters.",
        ),
        (
            "EVIDENCE_READ_RESULT_INVALID",
            "The saved evidence reader returned an invalid excerpt.",
        ),
        (
            "EVIDENCE_READ_FAILED",
            "The service could not read the saved evidence.",
        ),
    ],
)
def test_evidence_read_diagnostic_survives_grouped_context_without_secrets(
    code, message
):
    try:
        raise ResearchToolError(code) from ExceptionGroup(
            "SECRET provider body", [RuntimeError("SECRET credential")]
        )
    except ResearchToolError as error:
        diagnostic = diagnostic_for_error("AGENT_EXECUTION", error)

    assert diagnostic.code == code
    assert diagnostic.message == message
    assert diagnostic.error_type == "ResearchToolError"
    assert "SECRET" not in diagnostic.model_dump_json()


def test_diagnostic_preserves_safe_denial_cause_hidden_by_research_tool():
    try:
        try:
            raise AccountingDenied(Reason.BUDGET)
        except AccountingDenied:
            raise ResearchToolError() from None
    except ResearchToolError as error:
        diagnostic = diagnostic_for_error("AGENT_EXECUTION", error)

    assert diagnostic.stage == "AGENT_EXECUTION"
    assert diagnostic.error_type == "AccountingDenied"
    assert diagnostic.code == "BUDGET"
    assert diagnostic.message == "The approved budget denied this request."
    assert diagnostic.frames == ["ResearchToolError", "AccountingDenied:BUDGET"]


def test_diagnostic_preserves_safe_research_code_without_exception_context():
    diagnostic = diagnostic_for_error(
        "AGENT_EXECUTION", ResearchToolError("CONCURRENCY")
    )

    assert diagnostic.error_type == "ResearchToolError"
    assert diagnostic.code == "CONCURRENCY"
    assert diagnostic.message == "The provider concurrency limit denied this request."


def test_diagnostic_uses_only_validation_locations_and_types():
    class Input(BaseModel):
        count: int

    with pytest.raises(ValidationError) as raised:
        Input.model_validate({"count": "contains a secret prompt"})
    diagnostic = diagnostic_for_error("ADVICE_MAPPING", raised.value)

    assert diagnostic.error_type == "ValidationError"
    assert diagnostic.code == "VALIDATION_ERROR"
    assert diagnostic.message == "The returned data did not match the approved format."
    assert diagnostic.frames == ["ValidationError", "int_parsing"]
    assert "secret" not in diagnostic.model_dump_json().lower()


def test_diagnostic_does_not_retain_untrusted_validation_field_names():
    class Input(BaseModel):
        model_config = {"extra": "forbid"}

        count: int

    secret_field = "provider_response_contains_secret"
    with pytest.raises(ValidationError) as raised:
        Input.model_validate({"count": 1, secret_field: "value"})
    diagnostic = diagnostic_for_error("ADVICE_MAPPING", raised.value)

    assert diagnostic.frames == ["ValidationError", "extra_forbidden"]
    assert secret_field not in diagnostic.model_dump_json()


def test_native_assessment_invariants_are_identified_without_returned_content():
    from test_idea_market_research import _assessment

    from alon_ai.agents.schemas.idea import MarketResearchAssessment

    raw = cast(dict[str, Any], _assessment(str(uuid4())))
    raw["findings"][0]["source_refs"] = []
    raw["findings"][0]["claim"] = "SECRET patient records"
    raw["findings"].append(
        {**raw["findings"][0], "basis": "UNKNOWN", "source_refs": ["SECRET-source"]}
    )
    with pytest.raises(ValidationError) as raised:
        MarketResearchAssessment.model_validate(raw)
    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)

    assert (
        "value_error:findings.[]:OBSERVED_FINDING_SOURCE_REQUIRED" in diagnostic.frames
    )
    assert (
        "value_error:findings.[]:UNKNOWN_FINDING_CANNOT_CITE_SOURCE"
        in diagnostic.frames
    )
    assert "SECRET" not in diagnostic.model_dump_json()


def test_validation_diagnostics_redact_custom_types_locations_and_messages():
    from pydantic_core import PydanticCustomError

    error = ValidationError.from_exception_data(
        "SECRET model name",
        [
            {
                "type": PydanticCustomError("SECRET_type", "SECRET message"),
                "loc": ("findings", 972501234567, "SECRET_mapping_key", "claim"),
                "input": "SECRET input",
            },
            {
                "type": "value_error",
                "loc": ("brief",),
                "ctx": {
                    "error": ValueError("observed finding requires a source SECRET")
                },
                "input": "SECRET payload",
            },
        ],
    )
    diagnostic = diagnostic_for_error("AGENT_EXECUTION", error)

    assert "validation_error:findings.[].?.claim" in diagnostic.frames
    assert "value_error:brief" in diagnostic.frames
    rendered = diagnostic.model_dump_json()
    assert "SECRET" not in rendered
    assert "972501234567" not in rendered


def test_root_assessment_validator_has_actionable_controlled_code():
    from test_idea_market_research import _assessment

    from alon_ai.agents.schemas.idea import MarketResearchAssessment

    raw = cast(dict[str, Any], _assessment(str(uuid4())))
    raw["source_refs"] = []
    with pytest.raises(ValidationError) as raised:
        MarketResearchAssessment.model_validate(raw)

    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)

    assert "value_error:ASSESSMENT_UNDECLARED_SOURCE" in diagnostic.frames


@pytest.mark.parametrize(
    "field,value,expected",
    [
        (
            "brief",
            {"material_pivot": True},
            "value_error:brief:PIVOT_CLASSIFICATION_MISMATCH",
        ),
        (
            "price_observations",
            [{"subject": "SECRET price", "kind": "EXACT", "source_refs": ["src-a"]}],
            "value_error:price_observations.[]:NUMERIC_PRICE_FIELDS_REQUIRED",
        ),
    ],
)
def test_nested_brief_and_price_invariants_have_controlled_codes(
    field, value, expected
):
    from test_idea_market_research import _assessment

    from alon_ai.agents.schemas.idea import MarketResearchAssessment

    raw = cast(dict[str, Any], _assessment(str(uuid4())))
    if field == "brief":
        raw[field].update(value)
    else:
        raw[field] = value
    with pytest.raises(ValidationError) as raised:
        MarketResearchAssessment.model_validate(raw)
    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)

    assert expected in diagnostic.frames
    assert "SECRET" not in diagnostic.model_dump_json()


def test_diagnostic_classifies_known_provider_and_experiment_codes():
    provider = diagnostic_for_error(
        "AGENT_EXECUTION", ProviderFailure(ProviderErrorCode.UNAVAILABLE)
    )
    experiment = diagnostic_for_error(
        "PUBLICATION", ExperimentError(409, "IDEA_INPUT_STALE")
    )

    assert provider.code == "UNAVAILABLE"
    assert provider.frames == ["ProviderFailure:UNAVAILABLE"]
    assert experiment.code == "IDEA_INPUT_STALE"
    assert experiment.frames == ["ExperimentError:IDEA_INPUT_STALE"]


def test_diagnostic_classifies_typed_http_status_without_body():
    try:
        try:
            raise ProviderFailure(ProviderErrorCode.UNAVAILABLE, http_status=502)
        except ProviderFailure as provider:
            raise ResearchToolError(
                provider.code.value, http_status=provider.http_status
            ) from None
    except ResearchToolError as error:
        diagnostic = diagnostic_for_error("AGENT_EXECUTION", error)

    assert diagnostic.code == "HTTP_502"
    assert diagnostic.message == "The provider returned HTTP 502."
    assert "SECRET" not in diagnostic.model_dump_json()


async def test_diagnostic_includes_sanitized_project_traceback_location():
    class DeniedPort:
        async def search(self, experiment_id, request):
            raise AccountingDenied(Reason.BUDGET)

        async def map(self, experiment_id, request):
            raise AccountingDenied(Reason.BUDGET)

        async def capture(self, experiment_id, request):
            raise AccountingDenied(Reason.BUDGET)

        async def read_saved_evidence(self, experiment_id, retained_id, *, max_chars):
            raise AccountingDenied(Reason.BUDGET)

    tools = ResearchTools(uuid4(), DeniedPort())
    with pytest.raises(ResearchToolError) as raised:
        await tools.search_web("small clinics", limit=1)

    diagnostic = diagnostic_for_error("AGENT_EXECUTION", raised.value)

    assert "small clinics" not in diagnostic.model_dump_json()
    assert any(
        frame.startswith("alon_ai/agents/tools/research.py:")
        for frame in diagnostic.frames
    )
