"""Durable child-step replay and lineage against an isolated PostgreSQL database."""

import asyncio
import json
from decimal import Decimal
from typing import Any
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_minimal_intake import configured_app

from alon_ai.agents.schemas.openai import RoutingFacts
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import (
    ExperimentError,
    claim_discovery,
    claim_refinement,
)
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records
from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.experiments import ExperimentContext
from alon_ai.services.intake import IntakeService
from alon_ai.services.schemas.agent_runs import AgentRunRequest


async def _run(engine):
    app, operator_id = await configured_app(engine)
    context = ExperimentContext(engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(uuid4(), "Seed", draft=False)
    run = await AgentRunService(context).admit(
        experiment_id,
        AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4()),
    )
    return run.run_id, experiment_id, context


async def _live_combined_guard_roots(engine, *, discovery=False):
    app, operator_id = await configured_app(engine)
    settings = app.state.settings.model_copy(update={"provider_mode": "live"})
    context = ExperimentContext(
        engine, settings, operator_id, idea_runtime_provider=object()
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), None if discovery else "Seed", draft=False
    )
    run = await AgentRunService(context).admit(
        experiment_id,
        AgentRunRequest(
            task_kind="IDEA_DISCOVERY" if discovery else "IDEA_REFINEMENT",
            command_key=uuid4(),
        ),
    )
    assert await AgentRunRepository(engine).start(run.run_id)
    async with engine.connect() as connection:
        workflow_id = await connection.scalar(
            select(gov.workflows.c.id).where(
                gov.workflows.c.experiment_id == experiment_id
            )
        )
        agent_id = await connection.scalar(
            select(gov.agents.c.id).where(gov.agents.c.workflow_id == workflow_id)
        )
        cycle_id = await connection.scalar(
            select(records.cycles.c.id).where(
                records.cycles.c.experiment_id == experiment_id
            )
        )
    runtime, attribution = await provision_recorded_seeded_runtime(
        engine,
        experiment_id=experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        operator_id=operator_id,
        run_id=run.run_id,
        budget_usd=Decimal("0.50"),
    )
    if discovery:
        await claim_discovery(
            engine,
            experiment_id,
            None,
            run.run_id,
            attribution.operation_run_id,
            "OPENAI",
        )
    else:
        await claim_refinement(
            engine,
            experiment_id,
            cycle_id,
            run.run_id,
            attribution.operation_run_id,
            "OPENAI",
        )
    return run.run_id, experiment_id, cycle_id, attribution, runtime


async def _final_model_child(
    engine, run_id, experiment_id, cycle_id, attribution, runtime
):
    model_key = uuid5(run_id, "model-request/1")
    execution = (
        await runtime.discover_system(
            attribution, facts=RoutingFacts(needs_ai=True), idempotency_key=model_key
        )
        if cycle_id is None
        else await runtime.refine_cycle(
            attribution,
            cycle_id=cycle_id,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=model_key,
        )
    )
    assert execution.receipt is not None
    assert execution.receipt.state == "FINAL"
    store = AgentRunStepRepository(engine)
    model = {**_claim(run_id, experiment_id), "step_key": model_key}
    await store.claim(**model)
    await store.bind(
        run_id,
        model_key,
        operation_id=attribution.operation_run_id,
        operation_workflow_id=attribution.workflow_run_id,
        provider_call_id=execution.receipt.call_id,
    )
    await store.finish(run_id, model_key, status="SUCCEEDED")
    return model_key


async def _attempt_refinement_success(engine, run_id, output_hash):
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE record_idea_refinements SET state='SUCCEEDED', "
                "advice='{}'::jsonb, output_hash=:hash, finished_at=now() "
                "WHERE run_id=:run"
            ),
            {"hash": output_hash, "run": run_id},
        )


async def _attempt_discovery_success(engine, run_id, output_hash):
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE record_idea_discoveries SET state='SUCCEEDED', "
                'advice=\'{}\'::jsonb, candidate_ids=\'["one","two","three"]\'::jsonb, '
                "output_hash=:hash, finished_at=now() WHERE run_id=:run"
            ),
            {"hash": output_hash, "run": run_id},
        )


def _claim(run_id, experiment_id) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "step_key": uuid5(run_id, "candidate-1-research"),
        "ordinal": 1,
        "kind": "MODEL_REQUEST",
        "request_ref": run_id,
        "request_version": 1,
        "request_hash": "a" * 64,
        "config_ref": uuid4(),
        "config_version": 1,
        "config_hash": "b" * 64,
    }


async def test_claim_concurrent_replay_and_conflicting_identity(governance_engine):
    run_id, experiment_id, _ = await _run(governance_engine)
    store = AgentRunStepRepository(governance_engine)
    values = _claim(run_id, experiment_id)

    (first, first_created), (second, second_created) = await asyncio.gather(
        store.claim_once(**values), store.claim_once(**values)
    )
    assert sorted([first_created, second_created]) == [False, True]
    assert first["step_key"] == second["step_key"]
    assert first["status"] == second["status"] == "CLAIMED"
    assert len(await store.list(run_id)) == 1
    assert (await store.get(run_id, values["step_key"]))["request_hash"] == "a" * 64
    assert (await store.claim(**values))["status"] == "CLAIMED"

    with pytest.raises(ExperimentError, match="STEP_CONFLICT"):
        await store.claim(**{**values, "request_hash": "c" * 64})


async def test_bound_call_survives_restart_and_terminal_replay(governance_engine):
    run_id, experiment_id, _ = await _run(governance_engine)
    store = AgentRunStepRepository(governance_engine)
    await store.claim(**_claim(run_id, experiment_id))
    step_key = _claim(run_id, experiment_id)["step_key"]
    replay_store = AgentRunStepRepository(governance_engine)
    assert (await replay_store.get(run_id, step_key))["request_ref"] == run_id

    first = await replay_store.finish(
        run_id, step_key, status="BLOCKED", reason_code="NO_EVIDENCE"
    )
    second = await store.finish(
        run_id, step_key, status="BLOCKED", reason_code="NO_EVIDENCE"
    )
    assert first["status"] == second["status"] == "BLOCKED"
    assert second["reason_code"] == "NO_EVIDENCE"
    with pytest.raises(ExperimentError, match="STEP_CONFLICT"):
        await store.finish(run_id, step_key, status="SUCCEEDED")


async def test_database_rejects_cross_experiment_step_and_identity_rewrite(
    governance_engine,
):
    run_id, experiment_id, context = await _run(governance_engine)
    other_experiment_id = await IntakeService(context)._roots(
        uuid4(), "Other seed", draft=False
    )
    store = AgentRunStepRepository(governance_engine)
    with pytest.raises(IntegrityError):
        await store.claim(
            **{**_claim(run_id, experiment_id), "experiment_id": other_experiment_id}
        )

    await store.claim(**_claim(run_id, experiment_id))
    with pytest.raises(Exception, match="immutable"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE record_agent_run_steps SET request_hash=:hash "
                    "WHERE run_id=:run_id AND step_key=:step_key"
                ),
                {
                    "hash": "c" * 64,
                    "run_id": run_id,
                    "step_key": _claim(run_id, experiment_id)["step_key"],
                },
            )


async def test_operation_binding_is_scoped_and_idempotent(governance_engine):
    run_id, experiment_id, context = await _run(governance_engine)
    other_experiment_id = await IntakeService(context)._roots(
        uuid4(), "Other seed", draft=False
    )
    store = AgentRunStepRepository(governance_engine)
    values = _claim(run_id, experiment_id)
    await store.claim(**values)
    operations = []
    async with governance_engine.begin() as connection:
        for scoped_experiment_id in (experiment_id, other_experiment_id):
            workflow_id = await connection.scalar(
                select(gov.workflows.c.id).where(
                    gov.workflows.c.experiment_id == scoped_experiment_id
                )
            )
            agent_id = await connection.scalar(
                select(gov.agents.c.id).where(gov.agents.c.workflow_id == workflow_id)
            )
            operation_id = uuid4()
            await connection.execute(
                gov.operations.insert().values(
                    id=operation_id,
                    experiment_id=scoped_experiment_id,
                    workflow_id=workflow_id,
                    kind="RESEARCH",
                    agent_id=agent_id,
                    service=None,
                    config_version=uuid4(),
                    gate_kind="NONE",
                )
            )
            operations.append((operation_id, workflow_id))

    own_id, own_workflow_id = operations[0]
    other_id, other_workflow_id = operations[1]
    step_key = values["step_key"]
    with pytest.raises(IntegrityError):
        await store.bind(
            run_id,
            step_key,
            operation_id=other_id,
            operation_workflow_id=other_workflow_id,
        )
    first = await store.bind(
        run_id,
        step_key,
        operation_id=own_id,
        operation_workflow_id=own_workflow_id,
    )
    replay = await AgentRunStepRepository(governance_engine).bind(
        run_id,
        step_key,
        operation_id=own_id,
        operation_workflow_id=own_workflow_id,
    )
    assert first["operation_id"] == replay["operation_id"] == own_id
    with pytest.raises(ExperimentError, match="STEP_CONFLICT"):
        await store.bind(
            run_id,
            step_key,
            operation_id=other_id,
            operation_workflow_id=other_workflow_id,
        )


async def test_terminal_result_binds_exact_artifact_version_and_hash(
    governance_engine,
):
    run_id, experiment_id, _ = await _run(governance_engine)
    async with governance_engine.connect() as connection:
        artifact = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.experiment_id == experiment_id,
                        records.artifacts.c.kind == "IDEA_SEED",
                    )
                )
            )
            .mappings()
            .one()
        )
    values = {**_claim(run_id, experiment_id), "kind": "ARTIFACT_SAVE"}
    store = AgentRunStepRepository(governance_engine)
    await store.claim(**values)
    finish = {
        "status": "SUCCEEDED",
        "result_artifact_id": artifact["id"],
        "result_kind": artifact["kind"],
        "result_version": artifact["version"],
        "result_hash": artifact["content_hash"],
    }
    with pytest.raises(IntegrityError):
        await store.finish(
            run_id,
            values["step_key"],
            **{**finish, "result_hash": "0" * 64},
        )
    saved = await store.finish(run_id, values["step_key"], **finish)
    assert saved["result_artifact_id"] == artifact["id"]
    assert saved["result_hash"] == artifact["content_hash"]


async def test_candidate_binding_rejects_non_candidate_artifact(governance_engine):
    run_id, experiment_id, _ = await _run(governance_engine)
    async with governance_engine.connect() as connection:
        seed = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.experiment_id == experiment_id,
                        records.artifacts.c.kind == "IDEA_SEED",
                    )
                )
            )
            .mappings()
            .one()
        )
    values = {
        **_claim(run_id, experiment_id),
        "candidate_artifact_id": seed["id"],
        "candidate_version": seed["version"],
        "candidate_hash": seed["content_hash"],
    }
    with pytest.raises(IntegrityError):
        await AgentRunStepRepository(governance_engine).claim(**values)


async def test_only_successful_artifact_save_can_checkpoint_output_hash(
    governance_engine,
):
    run_id, experiment_id, _ = await _run(governance_engine)
    store = AgentRunStepRepository(governance_engine)
    model = _claim(run_id, experiment_id)
    save = {
        **model,
        "step_key": uuid5(run_id, "save-output"),
        "ordinal": 2,
        "kind": "ARTIFACT_SAVE",
    }
    await store.claim(**model)
    await store.claim(**save)
    with pytest.raises(IntegrityError):
        await store.finish(
            run_id, model["step_key"], status="SUCCEEDED", output_hash="d" * 64
        )
    saved = await store.finish(
        run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
    )
    assert saved["output_hash"] == "d" * 64
    assert (
        await store.finish(
            run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
        )
    )["output_hash"] == "d" * 64
    with pytest.raises(ExperimentError, match="STEP_CONFLICT"):
        await store.finish(
            run_id, save["step_key"], status="SUCCEEDED", output_hash="e" * 64
        )


async def test_combined_proof_rejects_missing_model_and_borrowed_old_call(
    governance_engine,
):
    historical_run_id, experiment_id, context = await _run(governance_engine)
    recorded_context = ExperimentContext(
        governance_engine,
        context.settings,
        context.operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    await AgentRunService(recorded_context).execute(historical_run_id)
    async with governance_engine.connect() as connection:
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(
                        gov.calls.c.idempotency_key == historical_run_id
                    )
                )
            )
            .mappings()
            .one()
        )
    runs = AgentRunRepository(governance_engine)
    historical = await runs.get(historical_run_id)
    new_run_id = uuid4()
    await runs.admit(
        {
            **{
                key: historical[key]
                for key in (
                    "experiment_id",
                    "operator_id",
                    "task_kind",
                    "request_hash",
                    "input_refs",
                    "profile_id",
                    "profile_version",
                    "profile_hash",
                    "application_version",
                )
            },
            "run_id": new_run_id,
            "command_key": uuid4(),
            "provider_mode": "live",
            "dbos_workflow_id": f"test-combined-{new_run_id}",
        }
    )
    assert await runs.start(new_run_id)
    store = AgentRunStepRepository(governance_engine)
    save = {
        **_claim(new_run_id, experiment_id),
        "step_key": uuid5(new_run_id, "artifact-save"),
        "kind": "ARTIFACT_SAVE",
    }
    await store.claim(**save)
    await store.bind(
        new_run_id,
        save["step_key"],
        operation_id=call["operation_id"],
        operation_workflow_id=call["workflow_id"],
    )
    await store.finish(
        new_run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
    )

    async def proof():
        async with governance_engine.connect() as connection:
            return await connection.scalar(
                text(
                    "SELECT record_combined_idea_proof(:run,:experiment,:operation,"
                    ":kind,:hash)"
                ),
                {
                    "run": new_run_id,
                    "experiment": experiment_id,
                    "operation": call["operation_id"],
                    "kind": "IDEA_REFINEMENT",
                    "hash": "d" * 64,
                },
            )

    assert await proof() is False  # An artifact checkpoint cannot stand in for a call.
    model = {**_claim(new_run_id, experiment_id), "step_key": historical_run_id}
    await store.claim(**model)
    await store.bind(
        new_run_id,
        model["step_key"],
        operation_id=call["operation_id"],
        operation_workflow_id=call["workflow_id"],
        provider_call_id=call["id"],
    )
    await store.finish(new_run_id, model["step_key"], status="SUCCEEDED")
    assert await proof() is False  # Call predates this parent run's start.


async def test_native_refinement_guard_rejects_success_without_model_child(
    governance_engine,
):
    run_id, experiment_id, _, attribution, _ = await _live_combined_guard_roots(
        governance_engine
    )
    store = AgentRunStepRepository(governance_engine)
    save = {
        **_claim(run_id, experiment_id),
        "step_key": uuid5(run_id, "artifact-save"),
        "kind": "ARTIFACT_SAVE",
    }
    await store.claim(**save)
    await store.bind(
        run_id,
        save["step_key"],
        operation_id=attribution.operation_run_id,
        operation_workflow_id=attribution.workflow_run_id,
    )
    await store.finish(
        run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
    )
    with pytest.raises(DBAPIError, match="not a successful governed run"):
        await _attempt_refinement_success(governance_engine, run_id, "d" * 64)


async def test_native_refinement_guard_requires_exact_saved_hash_and_final_call(
    governance_engine,
):
    (
        run_id,
        experiment_id,
        cycle_id,
        attribution,
        runtime,
    ) = await _live_combined_guard_roots(governance_engine)
    await _final_model_child(
        governance_engine, run_id, experiment_id, cycle_id, attribution, runtime
    )
    store = AgentRunStepRepository(governance_engine)
    save = {
        **_claim(run_id, experiment_id),
        "step_key": uuid5(run_id, "artifact-save"),
        "ordinal": 2,
        "kind": "ARTIFACT_SAVE",
    }
    await store.claim(**save)
    await store.bind(
        run_id,
        save["step_key"],
        operation_id=attribution.operation_run_id,
        operation_workflow_id=attribution.workflow_run_id,
    )
    await store.finish(
        run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
    )
    with pytest.raises(DBAPIError, match="not a successful governed run"):
        await _attempt_refinement_success(governance_engine, run_id, "e" * 64)
    await _attempt_refinement_success(governance_engine, run_id, "d" * 64)
    async with governance_engine.connect() as connection:
        state = await connection.scalar(
            select(records.idea_refinements.c.state).where(
                records.idea_refinements.c.run_id == run_id
            )
        )
    assert state == "SUCCEEDED"


async def test_native_refinement_guard_rejects_unknown_provider_child(
    governance_engine,
):
    (
        run_id,
        experiment_id,
        cycle_id,
        attribution,
        runtime,
    ) = await _live_combined_guard_roots(governance_engine)
    await _final_model_child(
        governance_engine, run_id, experiment_id, cycle_id, attribution, runtime
    )
    store = AgentRunStepRepository(governance_engine)
    save = {
        **_claim(run_id, experiment_id),
        "step_key": uuid5(run_id, "artifact-save"),
        "ordinal": 2,
        "kind": "ARTIFACT_SAVE",
    }
    await store.claim(**save)
    await store.bind(
        run_id,
        save["step_key"],
        operation_id=attribution.operation_run_id,
        operation_workflow_id=attribution.workflow_run_id,
    )
    await store.finish(
        run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
    )
    await store.claim(
        **{
            **_claim(run_id, experiment_id),
            "step_key": uuid5(run_id, "unresolved-brave-call"),
            "ordinal": 3,
            "kind": "BRAVE_SEARCH",
        }
    )
    with pytest.raises(DBAPIError, match="not a successful governed run"):
        await _attempt_refinement_success(governance_engine, run_id, "d" * 64)


async def test_native_discovery_guard_requires_final_model_and_exact_hash(
    governance_engine,
):
    (
        run_id,
        experiment_id,
        cycle_id,
        attribution,
        runtime,
    ) = await _live_combined_guard_roots(governance_engine, discovery=True)
    assert cycle_id is None
    store = AgentRunStepRepository(governance_engine)
    save = {
        **_claim(run_id, experiment_id),
        "step_key": uuid5(run_id, "artifact-save"),
        "kind": "ARTIFACT_SAVE",
    }
    await store.claim(**save)
    await store.bind(
        run_id,
        save["step_key"],
        operation_id=attribution.operation_run_id,
        operation_workflow_id=attribution.workflow_run_id,
    )
    await store.finish(
        run_id, save["step_key"], status="SUCCEEDED", output_hash="d" * 64
    )
    with pytest.raises(DBAPIError, match="not a governed run"):
        await _attempt_discovery_success(governance_engine, run_id, "d" * 64)
    await _final_model_child(
        governance_engine, run_id, experiment_id, cycle_id, attribution, runtime
    )
    with pytest.raises(DBAPIError, match="not a governed run"):
        await _attempt_discovery_success(governance_engine, run_id, "e" * 64)
    await _attempt_discovery_success(governance_engine, run_id, "d" * 64)
    async with governance_engine.connect() as connection:
        state = await connection.scalar(
            select(records.idea_discoveries.c.state).where(
                records.idea_discoveries.c.run_id == run_id
            )
        )
    assert state == "SUCCEEDED"


async def test_receipts_project_scoped_governed_call_and_usage_without_request(
    governance_engine,
):
    run_id, experiment_id, context = await _run(governance_engine)
    recorded_context = ExperimentContext(
        governance_engine,
        context.settings,
        context.operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    await AgentRunService(recorded_context).execute(run_id)
    async with governance_engine.connect() as connection:
        call = (
            (
                await connection.execute(
                    select(gov.calls).where(gov.calls.c.idempotency_key == run_id)
                )
            )
            .mappings()
            .one()
        )
    store = AgentRunStepRepository(governance_engine)
    values = _claim(run_id, experiment_id)
    await store.claim(**values)
    await store.bind(
        run_id,
        values["step_key"],
        operation_id=call["operation_id"],
        operation_workflow_id=call["workflow_id"],
        provider_call_id=call["id"],
    )
    await store.claim(
        **{
            **values,
            "step_key": uuid5(run_id, "artifact-save"),
            "ordinal": 2,
            "kind": "ARTIFACT_SAVE",
        }
    )
    with pytest.raises(IntegrityError):
        await store.bind(
            run_id,
            uuid5(run_id, "artifact-save"),
            provider_call_id=call["id"],
        )

    receipts = await AgentRunStepRepository(governance_engine).receipts(run_id)

    assert [entry["ordinal"] for entry in receipts] == [1, 2]
    assert receipts[0]["step_key"] == values["step_key"]
    assert receipts[0]["call"] == {
        "id": call["id"],
        "idempotency_key": call["idempotency_key"],
        "provider": "OPENAI",
        "model_identifier": "gpt-5-mini",
        "state": call["state"],
        "currency": call["currency"],
        "reserved": call["reserved"],
        "reserved_ils": call["reserved_ils"],
        "accrued": call["accrued"],
        "accrued_ils": call["accrued_ils"],
    }
    assert receipts[0]["usage"]
    assert all(
        {"component", "quantity", "cost", "currency", "knowledge"} <= item.keys()
        for item in receipts[0]["usage"]
    )
    assert receipts[1]["call"] is None
    assert receipts[1]["usage"] == []
    assert "request" not in str(receipts)
    assert "attribution" not in str(receipts)


async def test_rich_research_payloads_preserve_legacy_contract(governance_engine):
    finding = {
        "research_schema": "SOURCE_FINDING_V1",
        "run_id": str(uuid4()),
        "step_key": str(uuid4()),
        "dimension": "CUSTOMER_PAIN",
        "claim": "Buyers lose time.",
        "finding": "Three public pages describe the same delay.",
        "evidence_status": "SUPPORTED",
        "limitations": [],
    }
    report = {
        "research_schema": "MARKET_RESEARCH_CASE_V1",
        "finding": "Potential niche with unresolved demand.",
        "limitations": [],
        "unresolved_questions": ["Will buyers pay?"],
    }
    cases = [
        ("RESEARCH_EVIDENCE", finding, True),
        ("MARKET_RESEARCH_REPORT", report, True),
        ("RESEARCH_EVIDENCE", {"claim": "Legacy", "finding": "Legacy"}, True),
        (
            "MARKET_RESEARCH_REPORT",
            {"finding": "Legacy", "limitations": ["Old limitation"]},
            True,
        ),
        ("RESEARCH_EVIDENCE", {**finding, "query": "raw secret"}, False),
        ("RESEARCH_EVIDENCE", {**finding, "dimension": "UNKNOWN"}, False),
        ("RESEARCH_EVIDENCE", {**finding, "run_id": "not-uuid"}, False),
        ("RESEARCH_EVIDENCE", {**finding, "step_key": "not-uuid"}, False),
        ("MARKET_RESEARCH_REPORT", {**report, "unresolved_questions": [""]}, False),
    ]
    async with governance_engine.connect() as connection:
        for kind, payload, expected in cases:
            actual = await connection.scalar(
                text("SELECT record_payload_valid(:kind, CAST(:payload AS jsonb))"),
                {"kind": kind, "payload": json.dumps(payload)},
            )
            assert actual is expected, (kind, payload)
