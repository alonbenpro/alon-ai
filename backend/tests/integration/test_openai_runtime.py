"""Recorded Responses exercise the real PostgreSQL governance and usage ledger."""

import asyncio
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from test_governance import seed

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import AccountingDenied, CallState, Reason
from alon_ai.openai_runtime.contract import (
    AdvisoryAnswer,
    OpenAIProfile,
    RoutingFacts,
    RoutingPolicy,
)
from alon_ai.openai_runtime.runtime import AcceptedSource, OpenAIRuntime
from alon_ai.openai_runtime.store import OpenAIRunOutcome, OpenAIRunStore
from alon_ai.providers.contracts import Capability, ContentField, UsageComponent
from alon_ai.providers.rights import RuntimeContent

pytestmark = pytest.mark.integration

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


class FakeSecrets:
    def get(self, handle):
        assert handle == "test-openai"
        return SecretStr("recorded-only")


class RecordedResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def recorded(
    *, status="completed", usage=True, cached=True, text='{"answer":"advisory"}'
):
    return {
        "id": "resp_recorded_1",
        "status": status,
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": text}]}
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 4,
            "total_tokens": 14,
            **({"input_tokens_details": {"cached_tokens": 3}} if cached else {}),
        }
        if usage
        else None,
    }


async def setup(
    governance_engine,
    response,
    *,
    limit=Decimal(100),
    price_components=(
        UsageComponent.REQUEST,
        UsageComponent.INPUT_TOKEN,
        UsageComponent.OUTPUT_TOKEN,
        UsageComponent.CACHED_TOKEN,
    ),
    max_output_tokens=300,
):
    repo, admin, attr, config, grant, now = await seed(
        governance_engine,
        limit=limit,
        capability=Capability.OPENAI_GENERATE,
        price_components=price_components,
    )
    config = config.model_copy(update={"secret_handle": "test-openai"})
    # Provision a fresh immutable config with the required secret handle.
    config = config.model_copy(update={"id": uuid4()})
    await admin.config(config)
    profile = OpenAIProfile(
        config_id=config.id,
        config_version=config.version,
        adapter_version=config.adapter_version,
        prompt_version="checkpoint-v1",
        instructions="Use only the supplied source; return advisory JSON.",
        schema_version="advisory-v1",
        json_schema=SCHEMA,
        output_model=AdvisoryAnswer,
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=max_output_tokens,
    )
    source = AcceptedSource(
        evidence_ref=uuid4(),
        content=RuntimeContent(
            {ContentField.TEXT: ("licensed evidence",)},
            grant=grant,
            intended_use=config.intended_use,
            observed_at=now,
        ),
        current_grant=grant,
    )
    transport = RecordedResponses(response)
    store = OpenAIRunStore(governance_engine)
    runtime = OpenAIRuntime(
        repo,
        store,
        routes=RoutingPolicy(cheap=config.id, stronger=uuid4(), premium=uuid4()),
        profiles={config.id: profile},
        transport=transport,
        secrets=FakeSecrets(),
    )
    return runtime, store, attr, source, transport


async def test_recorded_success_is_attributed_and_reconciled_once(governance_engine):
    runtime, store, attr, source, transport = await setup(governance_engine, recorded())
    key = uuid4()
    result = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert result.outcome is OpenAIRunOutcome.SUCCEEDED
    assert result.receipt is not None
    assert result.receipt.state is CallState.FINAL
    assert result.receipt.accrued == Decimal("0.015000000000")
    assert result.output == AdvisoryAnswer(answer="advisory")
    run = await store.get(key)
    assert run is not None
    assert run.call_id == result.receipt.call_id
    assert (
        run.output_hash
        and run.input_hash
        and run.accepted_input_refs == (source.evidence_ref,)
    )
    async with governance_engine.connect() as conn:
        usage = (
            (
                await conn.execute(
                    select(gov.usage).where(gov.usage.c.call_id == run.call_id)
                )
            )
            .mappings()
            .all()
        )
    assert {row["component"]: row["quantity"] for row in usage} == {
        "REQUEST": Decimal(1),
        "INPUT_TOKEN": Decimal(7),
        "OUTPUT_TOKEN": Decimal(4),
        "CACHED_TOKEN": Decimal(3),
    }
    replay = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert replay.outcome is OpenAIRunOutcome.SUCCEEDED
    assert replay.output is None
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    ("response", "outcome", "state"),
    [
        (
            recorded(text='{"other":"bad"}'),
            OpenAIRunOutcome.SCHEMA_MISMATCH,
            CallState.FINAL,
        ),
        (
            {
                **recorded(),
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "no"}],
                    }
                ],
            },
            OpenAIRunOutcome.REFUSED,
            CallState.FINAL,
        ),
        (recorded(status="incomplete"), OpenAIRunOutcome.INCOMPLETE, CallState.FINAL),
        (recorded(status="cancelled"), OpenAIRunOutcome.CANCELLED, CallState.FINAL),
        (recorded(usage=False), OpenAIRunOutcome.SUCCEEDED, CallState.RECONCILING),
        (recorded(cached=False), OpenAIRunOutcome.SUCCEEDED, CallState.RECONCILING),
    ],
)
async def test_classified_response_retains_usage_or_uncertainty(
    governance_engine, response, outcome, state
):
    runtime, store, attr, source, transport = await setup(governance_engine, response)
    key = uuid4()
    result = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert result.outcome is outcome
    assert result.receipt is not None
    assert result.receipt.state is state
    if state is CallState.RECONCILING:
        assert result.output is None
    run = await store.get(key)
    assert run is not None
    assert run.call_id == result.receipt.call_id
    assert len(transport.calls) == 1


async def test_revoked_source_never_dispatches(governance_engine):
    runtime, _, attr, source, transport = await setup(governance_engine, recorded())
    revoked = source.current_grant.model_copy(
        update={"expires_at": runtime.repository.clock() - timedelta(seconds=1)}
    )
    with pytest.raises(PermissionError):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source.__class__(source.evidence_ref, source.content, revoked),),
            idempotency_key=uuid4(),
        )
    assert transport.calls == []


@pytest.mark.parametrize(
    ("failure", "outcome"),
    [
        (TimeoutError("timeout"), OpenAIRunOutcome.TIMEOUT),
        (ConnectionError("uncertain dispatch"), OpenAIRunOutcome.UNCERTAIN),
    ],
)
async def test_transport_failure_remains_attributed_and_uncertain(
    governance_engine, failure, outcome
):
    runtime, store, attr, source, transport = await setup(governance_engine, failure)
    key = uuid4()
    result = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert result.outcome is outcome
    assert result.receipt is not None
    assert result.receipt.state is CallState.RECONCILING
    assert result.output is None
    run = await store.get(key)
    assert run is not None
    assert run.call_id == result.receipt.call_id
    assert len(transport.calls) == 1


async def test_cancellation_is_classified_and_retains_ledger_dispatch(
    governance_engine,
):
    runtime, store, attr, source, transport = await setup(
        governance_engine, asyncio.CancelledError()
    )
    key = uuid4()
    with pytest.raises(asyncio.CancelledError):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    run = await store.get(key)
    assert run is not None
    assert run.outcome is OpenAIRunOutcome.CANCELLED
    async with governance_engine.connect() as conn:
        call = (
            (
                await conn.execute(
                    select(gov.calls).where(gov.calls.c.idempotency_key == key)
                )
            )
            .mappings()
            .one()
        )
    assert call["state"] == "RECONCILING"
    assert len(transport.calls) == 1


async def test_no_ai_never_creates_a_paid_attempt(governance_engine):
    runtime, store, attr, _, transport = await setup(governance_engine, recorded())
    key = uuid4()
    result = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=False), sources=(), idempotency_key=key
    )
    assert result.outcome is OpenAIRunOutcome.NO_AI
    assert result.receipt is None
    assert await store.get(key) is None
    assert transport.calls == []


async def test_budget_denial_closes_intent_without_dispatch(governance_engine):
    runtime, store, attr, source, transport = await setup(
        governance_engine, recorded(), limit=Decimal("0.01")
    )
    key = uuid4()
    with pytest.raises(AccountingDenied) as denied:
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    assert denied.value.reason is Reason.BUDGET
    run = await store.get(key)
    assert run is not None
    assert run.outcome is OpenAIRunOutcome.FAILED
    assert run.call_id is None
    assert transport.calls == []


@pytest.mark.parametrize(
    "options",
    [
        {"price_components": (UsageComponent.REQUEST,)},
        {"max_output_tokens": 5000},
    ],
)
async def test_unpriced_or_under_reserved_tokens_never_dispatch(
    governance_engine, options
):
    runtime, store, attr, source, transport = await setup(
        governance_engine, recorded(), **options
    )
    key = uuid4()
    with pytest.raises(PermissionError):
        await runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    assert await store.get(key) is None
    assert transport.calls == []


async def test_same_key_concurrent_reader_cannot_finalize_owners_run(
    governance_engine,
):
    runtime, store, attr, source, transport = await setup(governance_engine, recorded())
    entered = asyncio.Event()
    release = asyncio.Event()

    async def blocked_create(**kwargs):
        transport.calls.append(kwargs)
        entered.set()
        await release.wait()
        return recorded()

    transport.create = blocked_create
    key = uuid4()
    owner = asyncio.create_task(
        runtime.run(
            attr,
            facts=RoutingFacts(needs_ai=True),
            sources=(source,),
            idempotency_key=key,
        )
    )
    await asyncio.wait_for(entered.wait(), 5)
    concurrent = await runtime.run(
        attr, facts=RoutingFacts(needs_ai=True), sources=(source,), idempotency_key=key
    )
    assert concurrent.outcome is OpenAIRunOutcome.UNCERTAIN
    pending = await store.get(key)
    assert pending is not None
    assert pending.outcome is OpenAIRunOutcome.READY
    release.set()
    completed = await owner
    assert completed.outcome is OpenAIRunOutcome.SUCCEEDED
    assert completed.output == AdvisoryAnswer(answer="advisory")
    assert len(transport.calls) == 1
