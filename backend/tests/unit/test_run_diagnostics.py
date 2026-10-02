"""Sanitized, durable operator diagnostics for failed agent runs."""

from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from alon_ai.agents.tools.research import ResearchToolError, ResearchTools
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.integrations.schemas.provider import ProviderErrorCode, ProviderFailure
from alon_ai.provider_usage.schemas.accounting import AccountingDenied, Reason
from alon_ai.services.run_diagnostics import diagnostic_for_error


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
