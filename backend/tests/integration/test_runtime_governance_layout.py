"""Canonical runtime and governance ownership without duplicate metadata."""

from importlib import import_module


def test_runtime_and_provider_modules_have_canonical_owners():
    owners = {
        "alon_ai.services.agent_runs": "OpenAIRuntime",
        "alon_ai.services.ideas": "IdeaRuntime",
        "alon_ai.agents.market_research": "MarketResearchAdvice",
        "alon_ai.integrations.openai": "SDKResponsesTransport",
        "alon_ai.integrations.live_idea": "LiveIdeaRuntimeConfig",
        "alon_ai.provider_usage.live_idea": "build_live_idea_runtime_provider",
        "alon_ai.integrations.recorded_idea": "_RecordedResponses",
        "alon_ai.provider_usage.recorded_idea": "provision_recorded_seeded_runtime",
        "alon_ai.provider_usage.service": "GovernedExecutor",
        "alon_ai.provider_usage.sending": "SendGateway",
        "alon_ai.policies.provider_rights": "evaluate_rights",
        "alon_ai.db.repositories.accounting": "GovernanceRepository",
        "alon_ai.db.repositories.openai_run": "OpenAIRunStore",
        "alon_ai.db.repositories.openai_authority": "OpenAIAuthorityStore",
    }
    for module_name, symbol in owners.items():
        assert getattr(import_module(module_name), symbol).__module__ == module_name


def test_governance_and_openai_tables_use_one_metadata_registry():
    accounting = import_module("alon_ai.db.tables.accounting")
    openai = import_module("alon_ai.db.tables.openai")
    assert openai.run_intents.metadata is accounting.metadata
    assert accounting.metadata.tables["openai_run_intents"] is openai.run_intents
    assert accounting.metadata.tables["gov_calls"] is accounting.calls


def test_accepted_input_sql_lives_in_repository():
    repository = import_module("alon_ai.db.repositories.openai_inputs")
    assert repository.accepted_input.__module__ == repository.__name__
    assert (
        import_module("alon_ai.services.agent_runs")._accepted_input
        is repository.accepted_input
    )
    assert (
        import_module("alon_ai.provider_usage.openai")._accepted_input
        is repository.accepted_input
    )


def test_guarded_openai_dispatch_is_owned_by_provider_usage():
    dispatch = import_module("alon_ai.provider_usage.openai")
    assert dispatch.ConfiguredResponsesAdapter.__module__ == dispatch.__name__


def test_dispatch_adapter_uses_repository_for_sql_and_locks():
    from pathlib import Path

    module = import_module("alon_ai.provider_usage.openai")
    assert module.__file__ is not None
    source = Path(module.__file__).read_text()
    assert "from sqlalchemy import select" not in source
    assert ".engine.connect()" not in source
    assert ".engine.begin()" not in source


def test_idea_service_delegates_persistence_to_repository():
    from pathlib import Path

    service = import_module("alon_ai.services.ideas")
    assert service.__file__ is not None
    source = Path(service.__file__).read_text()
    assert "from sqlalchemy import select" not in source
    assert ".engine.connect()" not in source


def test_integrations_do_not_provision_authority_or_budgets():
    from pathlib import Path

    for module_name in (
        "alon_ai.integrations.live_idea",
        "alon_ai.integrations.recorded_idea",
    ):
        module = import_module(module_name)
        assert module.__file__ is not None
        source = Path(module.__file__).read_text()
        assert "GovernanceProvisioner" not in source
        assert ".budgets(" not in source


async def test_bounded_agent_dispatches_once_and_rejects_role_invalid_output():
    from uuid import uuid4

    from pydantic import SecretStr

    from alon_ai.agents.runtime import BoundedOpenAICall
    from alon_ai.agents.schemas.openai import AdvisoryAnswer, OpenAIProfile
    from alon_ai.integrations.schemas.provider import StrictDTO

    class RecordedTransport:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            self.calls += 1
            return {
                "id": "resp_recorded",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"answer":"invalid role advice"}',
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }

    def reject_role_output(output: StrictDTO, input_json: str) -> None:
        raise ValueError("role output is invalid")

    profile = OpenAIProfile(
        config_id=uuid4(),
        config_version=uuid4(),
        adapter_version=uuid4(),
        prompt_version="test-v1",
        instructions="Produce advice",
        schema_version="test-v1",
        json_schema={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
        output_model=AdvisoryAnswer,
        model_identifier="recorded-model",
        reasoning_effort="low",
        max_output_tokens=16,
        output_validator=reject_role_output,
    )
    transport = RecordedTransport()
    bounded = BoundedOpenAICall(profile, transport)
    response = await bounded.dispatch("{}", SecretStr("recorded-only"), uuid4())
    parsed = bounded.classify(response, "{}")
    assert transport.calls == 1
    assert parsed.outcome == "SCHEMA_MISMATCH"
    assert parsed.output is None


def test_provider_usage_guard_delegates_single_call_classification():
    from pathlib import Path

    module = import_module("alon_ai.provider_usage.openai")
    assert module.__file__ is not None
    source = Path(module.__file__).read_text()
    assert "self.transport.create(" not in source
    assert "classify_response(" not in source
    assert "self.profile.output_validator(" not in source


def test_bounded_agent_has_no_accounting_or_provider_result_construction():
    from pathlib import Path

    module = import_module("alon_ai.agents.runtime")
    assert module.__file__ is not None
    source = Path(module.__file__).read_text()
    assert "PriceVersion" not in source
    assert "_priced_usage" not in source
    assert "ProviderCallResult" not in source
