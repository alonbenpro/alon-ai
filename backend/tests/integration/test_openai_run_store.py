"""A run intent survives dispatch uncertainty without retaining model content."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from test_governance import reserve, seed

from alon_ai.openai_runtime.store import (
    OpenAIRunConflict,
    OpenAIRunIntent,
    OpenAIRunOutcome,
    OpenAIRunStore,
)

pytestmark = pytest.mark.integration


def intent_for(attr, config):
    return OpenAIRunIntent(
        idempotency_key=uuid4(),
        config_id=config.id,
        config_version=config.version,
        experiment_id=attr.experiment_id,
        workflow_id=attr.workflow_run_id,
        operation_id=attr.operation_run_id,
        agent_run_id=None,
        prompt_version="research-v1",
        prompt_hash="b" * 64,
        schema_version="lead-v1",
        output_schema_hash="d" * 64,
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        accepted_input_refs=(uuid4(),),
        input_hash="a" * 64,
        client_request_id=uuid4(),
        created_at=datetime.now(UTC),
    )


async def test_begin_is_durable_before_call_and_rejects_changed_identity(
    governance_engine,
):
    _, _, attr, config, _, _ = await seed(governance_engine)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)

    first = await store.begin(intent)
    assert first.outcome == OpenAIRunOutcome.READY
    assert first.prompt_hash == "b" * 64
    assert first.output_schema_hash == "d" * 64
    assert first.call_id is None
    assert await store.begin(intent) == first
    assert await OpenAIRunStore(governance_engine).get(intent.idempotency_key) == first

    with pytest.raises(OpenAIRunConflict):
        await store.begin(intent.model_copy(update={"prompt_hash": "e" * 64}))
    with pytest.raises(OpenAIRunConflict):
        await store.begin(intent.model_copy(update={"output_schema_hash": "f" * 64}))
    assert await store.get(intent.idempotency_key) == first


async def test_concurrent_begin_has_one_immutable_identity(governance_engine):
    _, _, attr, config, _, _ = await seed(governance_engine)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)

    first, repeated = await asyncio.gather(store.begin(intent), store.begin(intent))
    assert repeated == first
    async with governance_engine.connect() as connection:
        count = (
            await connection.execute(
                text(
                    "SELECT count(*) FROM openai_run_intents WHERE idempotency_key=:key"
                ),
                {"key": intent.idempotency_key},
            )
        ).scalar_one()
    assert count == 1


async def test_finish_binds_ledger_call_once_and_rejects_changed_result(
    governance_engine,
):
    repo, _, attr, config, _, _ = await seed(governance_engine)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)
    await store.begin(intent)
    receipt = await reserve(repo, attr, config, key=intent.idempotency_key)

    with pytest.raises(OpenAIRunConflict):
        await store.finish(
            intent.idempotency_key,
            receipt.call_id,
            OpenAIRunOutcome.SUCCEEDED,
            "c" * 64,
        )
    await repo.cancel_before_dispatch(receipt.call_id, command_key=uuid4())
    done = await store.finish(
        intent.idempotency_key,
        receipt.call_id,
        OpenAIRunOutcome.FAILED,
        None,
    )
    assert done.call_id == receipt.call_id
    assert done.outcome == OpenAIRunOutcome.FAILED
    assert done.output_hash is None
    assert (
        await store.finish(
            intent.idempotency_key,
            receipt.call_id,
            OpenAIRunOutcome.FAILED,
            None,
        )
        == done
    )
    with pytest.raises(OpenAIRunConflict):
        await store.finish(
            intent.idempotency_key,
            receipt.call_id,
            OpenAIRunOutcome.REFUSED,
            None,
        )
    assert await store.get(intent.idempotency_key) == done


async def test_finish_rejects_same_key_ledger_call_from_other_config(governance_engine):
    repo, admin, attr, config, _, _ = await seed(governance_engine)
    other_config = config.model_copy(update={"id": uuid4()})
    await admin.config(other_config)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)
    await store.begin(intent)
    receipt = await reserve(repo, attr, other_config, key=intent.idempotency_key)

    with pytest.raises(OpenAIRunConflict):
        await store.finish(
            intent.idempotency_key,
            receipt.call_id,
            OpenAIRunOutcome.SUCCEEDED,
            "c" * 64,
        )
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                text("""UPDATE openai_run_intents
                    SET call_id=:call_id, outcome='SUCCEEDED', output_hash=:hash,
                        finished_at=:now WHERE idempotency_key=:key"""),
                {
                    "call_id": receipt.call_id,
                    "hash": "c" * 64,
                    "now": datetime.now(UTC),
                    "key": intent.idempotency_key,
                },
            )
    remaining = await store.get(intent.idempotency_key)
    assert remaining is not None
    assert remaining.outcome == OpenAIRunOutcome.READY


async def test_interrupted_attempt_can_finish_without_call_receipt(governance_engine):
    _, _, attr, config, _, _ = await seed(governance_engine)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)
    await store.begin(intent)

    uncertain = await store.finish(
        intent.idempotency_key, None, OpenAIRunOutcome.UNCERTAIN, None
    )
    assert uncertain.call_id is None
    assert uncertain.outcome == OpenAIRunOutcome.UNCERTAIN
    assert (
        await store.finish(
            intent.idempotency_key, None, OpenAIRunOutcome.UNCERTAIN, None
        )
        == uncertain
    )


async def test_timeout_is_distinct_and_keeps_ledger_call_for_reconciliation(
    governance_engine,
):
    repo, _, attr, config, _, _ = await seed(governance_engine)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)
    await store.begin(intent)
    receipt = await reserve(repo, attr, config, key=intent.idempotency_key)

    timed_out = await store.finish(
        intent.idempotency_key, receipt.call_id, OpenAIRunOutcome.TIMEOUT, None
    )
    assert timed_out.outcome == OpenAIRunOutcome.TIMEOUT
    assert timed_out.call_id == receipt.call_id
    assert timed_out.output_hash is None
    assert await store.get(intent.idempotency_key) == timed_out


async def test_database_guards_identity_and_stores_only_safe_fields(governance_engine):
    _, _, attr, config, _, _ = await seed(governance_engine)
    store = OpenAIRunStore(governance_engine)
    intent = intent_for(attr, config)
    await store.begin(intent)
    async with governance_engine.connect() as connection:
        columns = await connection.run_sync(
            lambda sync: {
                column["name"]
                for column in inspect(sync).get_columns("openai_run_intents")
            }
        )
    assert not columns.intersection(
        {"prompt", "input", "output", "request", "response", "secret"}
    )
    with pytest.raises(DBAPIError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                text("""UPDATE openai_run_intents SET input_hash=:hash
                    WHERE idempotency_key=:key"""),
                {"hash": "b" * 64, "key": intent.idempotency_key},
            )
