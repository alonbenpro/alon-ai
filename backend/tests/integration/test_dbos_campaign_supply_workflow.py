"""Durable L04 campaign-supply command delivery against isolated PostgreSQL."""

import asyncio
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import DBAPIError
from test_campaign_supply import NOW, candidate, setup

from alon_ai.accounting import schema as gov
from alon_ai.policies.campaign_supply import (
    DiscoveryCompletionEvidence,
    DiscoveryPlan,
    SupplyDenied,
)
from alon_ai.records import schema as records
from alon_ai.supply import schema as supply
from alon_ai.workflows.campaign_supply import (
    CampaignSupplyWorkflowRepository,
    CampaignSupplyWorkflowRequest,
    campaign_supply_workflow_id,
)

pytestmark = pytest.mark.integration
HARNESS = Path(__file__).with_name("dbos_campaign_supply_harness.py")


def _environment(engine) -> dict[str, str]:
    url = engine.url.render_as_string(hide_password=False)
    system = engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    return {
        **os.environ,
        "ALON_AI_DATABASE_URL": url,
        "ALON_AI_DBOS_SYSTEM_DATABASE_URL": system,
        "ALON_AI_ENVIRONMENT": "test",
    }


def _migrate_dbos(engine) -> None:
    system = engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("dbos")),
            "migrate",
            "--sys-db-url",
            system,
            "--schema",
            "dbos",
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


async def _wait_for(path: Path, process: asyncio.subprocess.Process) -> None:
    for _ in range(500):
        if path.exists():
            return
        if process.returncode is not None:
            stdout, stderr = await process.communicate()
            pytest.fail(
                f"supply workflow exited before barrier: {stdout.decode()}\n{stderr.decode()}"
            )
        await asyncio.sleep(0.02)
    process.kill()
    await process.wait()
    pytest.fail("supply workflow never reached its barrier")


async def test_supply_workflow_binding_replay_conflict_and_next_action(
    governance_engine,
):
    repo, _, experiment_id, plan, filters = await setup(governance_engine)
    runtime = CampaignSupplyWorkflowRepository(governance_engine, clock=lambda: NOW)
    assert (await runtime.next_action(experiment_id)).kind == "BEGIN_BATCH_1"
    request = CampaignSupplyWorkflowRequest(
        operation_kind="BEGIN_BATCH",
        experiment_id=experiment_id,
        slot=1,
        plan=plan,
        command_key=uuid4(),
    )
    binding = await runtime.bind(request, application_version="l04-market-research-v1")
    assert (
        await runtime.bind(request, application_version="l04-market-research-v1")
        == binding
    )
    changed = request.model_copy(
        update={
            "plan": DiscoveryPlan(
                qualification_rule_id=plan.qualification_rule_id,
                filters=(filters[1],),
            )
        }
    )
    with pytest.raises(SupplyDenied, match="WORKFLOW_BINDING_CONFLICT"):
        await runtime.bind(changed, application_version="l04-market-research-v1")
    assert binding.dbos_workflow_id.startswith(f"campaign-supply:{experiment_id}:")
    with pytest.raises(DBAPIError, match="immutable supply workflow identity"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE supply_workflow_bindings SET request_hash=:hash WHERE dbos_workflow_id=:id"
                ),
                {"hash": "0" * 64, "id": binding.dbos_workflow_id},
            )
    assert repo is not None


async def test_coordinator_waits_for_persisted_discovery_and_contact_evidence(
    governance_engine,
):
    repo, writer, experiment_id, plan, filters = await setup(governance_engine)
    runtime = CampaignSupplyWorkflowRepository(governance_engine, clock=lambda: NOW)
    batch_id = await repo.begin_batch(experiment_id, 1, plan, uuid4())
    assert (await runtime.next_action(experiment_id)).kind == "WAIT_DISCOVERY"
    await writer.discovery_completion(
        DiscoveryCompletionEvidence(
            id=uuid4(),
            batch_id=batch_id,
            filter=filters[0],
            kind="QUERY_COMPLETE",
            mode="SYNTHETIC",
            registered_by=uuid4(),
            observed_at=NOW,
        )
    )
    assert (await runtime.next_action(experiment_id)).kind == "CLOSE_CONTACTABILITY"
    await candidate(repo, writer, experiment_id, batch_id, 0, supported=None)
    assert (await runtime.next_action(experiment_id)).kind == "WAIT_CONTACTABILITY"


async def test_competing_supply_bindings_and_commands_have_one_batch(governance_engine):
    repo, _, experiment_id, plan, _ = await setup(governance_engine)
    runtime = CampaignSupplyWorkflowRepository(governance_engine, clock=lambda: NOW)
    request = CampaignSupplyWorkflowRequest(
        operation_kind="BEGIN_BATCH",
        experiment_id=experiment_id,
        slot=1,
        plan=plan,
        command_key=uuid4(),
    )
    first, second = await asyncio.gather(
        runtime.bind(request, application_version="l04-market-research-v1"),
        runtime.bind(request, application_version="l04-market-research-v1"),
    )
    assert first == second
    await runtime.start(request, application_version="l04-market-research-v1")
    results = await asyncio.gather(
        repo.begin_batch(
            experiment_id,
            1,
            plan,
            request.command_key,
            workflow_id=first.dbos_workflow_id,
        ),
        repo.begin_batch(
            experiment_id,
            1,
            plan,
            request.command_key,
            workflow_id=first.dbos_workflow_id,
        ),
    )
    assert results[0] == results[1]
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(supply.batches)
                .where(supply.batches.c.experiment_id == experiment_id)
            )
            == 1
        )


async def test_coordinator_reports_deadline_and_governed_budget_stops(
    governance_engine,
):
    _, _, experiment_id, _, _ = await setup(governance_engine)
    late = CampaignSupplyWorkflowRepository(
        governance_engine, clock=lambda: NOW + timedelta(hours=2)
    )
    assert (await late.next_action(experiment_id)).kind == "DEADLINE_EXHAUSTED"
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(gov.budget_accounts).values(
                id=uuid4(),
                scope="EXPERIMENT",
                experiment_id=experiment_id,
                currency="ILS",
                effective_at=NOW - timedelta(days=1),
                expires_at=NOW + timedelta(days=1),
                limit=Decimal(1),
                reserved=Decimal(1),
                accrued=Decimal(0),
                frozen=False,
            )
        )
    current = CampaignSupplyWorkflowRepository(governance_engine, clock=lambda: NOW)
    assert (await current.next_action(experiment_id)).kind == "BUDGET_EXHAUSTED"


@pytest.mark.parametrize("barrier", ("before-business", "after-business"))
async def test_dbos_supply_batch_crash_replays_one_business_graph(
    governance_engine, tmp_path, barrier
):
    _, _, experiment_id, plan, _ = await setup(
        governance_engine,
        supply_deadline=datetime.now(UTC) + timedelta(days=2),
    )
    request = CampaignSupplyWorkflowRequest(
        operation_kind="BEGIN_BATCH",
        experiment_id=experiment_id,
        slot=1,
        plan=plan,
        command_key=uuid4(),
    )
    request_path = tmp_path / "supply-request.json"
    request_path.write_text(request.model_dump_json(exclude_computed_fields=True))
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(HARNESS),
        "start",
        "--request",
        str(request_path),
        cwd=Path(__file__).parents[2],
        env={
            **_environment(governance_engine),
            "ALON_AI_SUPPLY_DBOS_TEST_BARRIER": barrier,
            "ALON_AI_SUPPLY_DBOS_TEST_READY": str(ready),
            "ALON_AI_SUPPLY_DBOS_TEST_RELEASE": str(release),
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for(ready, process)
    process.send_signal(signal.SIGKILL)
    await asyncio.wait_for(process.wait(), timeout=10)
    recovered = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, str(HARNESS), "recover", "--request", str(request_path)],
        cwd=Path(__file__).parents[2],
        env=_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert recovered.returncode == 0, recovered.stderr
    workflow_id = campaign_supply_workflow_id(request)
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(supply.batches)
                .where(supply.batches.c.experiment_id == experiment_id)
            )
            == 1
        )
        command = (
            (
                await connection.execute(
                    select(records.commands).where(
                        records.commands.c.command_key == request.command_key
                    )
                )
            )
            .mappings()
            .one()
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.audit)
                .where(records.audit.c.command_id == command["id"])
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.outbox)
                .where(records.outbox.c.command_id == command["id"])
            )
            == 1
        )
        binding = (
            (
                await connection.execute(
                    select(supply.workflow_bindings).where(
                        supply.workflow_bindings.c.dbos_workflow_id == workflow_id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert binding["delivery_state"] == "RUNTIME_COMPLETED"
        assert binding["command_id"] == command["id"]
    assert (
        await CampaignSupplyWorkflowRepository(governance_engine).cancel(workflow_id)
        == "INEFFECTIVE_ALREADY_COMMITTED"
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(supply.workflow_bindings.c.delivery_state).where(
                    supply.workflow_bindings.c.dbos_workflow_id == workflow_id
                )
            )
            == "RUNTIME_COMPLETED"
        )


@pytest.mark.parametrize(
    ("barrier", "expected_cancel", "expected_batches"),
    (
        ("before-business", "EFFECTIVE", 0),
        ("after-business", "INEFFECTIVE_ALREADY_COMMITTED", 1),
    ),
)
async def test_supply_cancellation_serializes_with_business_commit(
    governance_engine, tmp_path, barrier, expected_cancel, expected_batches
):
    _, _, experiment_id, plan, _ = await setup(
        governance_engine,
        supply_deadline=datetime.now(UTC) + timedelta(days=2),
    )
    request = CampaignSupplyWorkflowRequest(
        operation_kind="BEGIN_BATCH",
        experiment_id=experiment_id,
        slot=1,
        plan=plan,
        command_key=uuid4(),
    )
    request_path = tmp_path / "supply-request.json"
    request_path.write_text(request.model_dump_json(exclude_computed_fields=True))
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(HARNESS),
        "start",
        "--request",
        str(request_path),
        cwd=Path(__file__).parents[2],
        env={
            **_environment(governance_engine),
            "ALON_AI_SUPPLY_DBOS_TEST_BARRIER": barrier,
            "ALON_AI_SUPPLY_DBOS_TEST_READY": str(ready),
            "ALON_AI_SUPPLY_DBOS_TEST_RELEASE": str(release),
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for(ready, process)
    runtime = CampaignSupplyWorkflowRepository(governance_engine)
    workflow_id = campaign_supply_workflow_id(request)
    assert await runtime.cancel(workflow_id) == expected_cancel
    process.send_signal(signal.SIGKILL)
    await asyncio.wait_for(process.wait(), timeout=10)
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(supply.batches)
                .where(supply.batches.c.experiment_id == experiment_id)
            )
            == expected_batches
        )
    if expected_batches:
        recovered = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, str(HARNESS), "recover", "--request", str(request_path)],
            cwd=Path(__file__).parents[2],
            env=_environment(governance_engine),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert recovered.returncode == 0, recovered.stderr
        async with governance_engine.connect() as connection:
            state = await connection.scalar(
                select(supply.workflow_bindings.c.delivery_state).where(
                    supply.workflow_bindings.c.dbos_workflow_id == workflow_id
                )
            )
            assert state == "RUNTIME_COMPLETED"
