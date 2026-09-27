"""Focused DBOS control-plane contract for the first L04 transition."""

import asyncio
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from test_product_record_guards import cycle_fixture

from alon_ai.db.repositories.workflow_market_research import (
    MarketResearchWorkflowRepository,
)
from alon_ai.db.tables import records
from alon_ai.services.schemas.records import ArtifactInput, ProductRecordsDenied
from alon_ai.workflows.schemas.market_research import MarketResearchWorkflowRequest
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION

pytestmark = pytest.mark.integration

HARNESS = Path(__file__).with_name("dbos_market_research_harness.py")


def _urls(governance_engine) -> tuple[str, str]:
    application = governance_engine.url.render_as_string(hide_password=False)
    system = governance_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    return application, system


def _environment(governance_engine) -> dict[str, str]:
    application, system = _urls(governance_engine)
    return {
        **os.environ,
        "ALON_AI_DATABASE_URL": application,
        "ALON_AI_DBOS_SYSTEM_DATABASE_URL": system,
        "ALON_AI_ENVIRONMENT": "test",
    }


def _command(
    mode: str,
    request_path: Path | None,
    *,
    application_version: str = DBOS_APPLICATION_VERSION,
    executor_id: str = "l04-test-executor",
) -> list[str]:
    command = [
        sys.executable,
        str(HARNESS),
        mode,
        "--application-version",
        application_version,
        "--executor-id",
        executor_id,
    ]
    if request_path is not None:
        command.extend(("--request", str(request_path)))
    return command


def _migrate_dbos(governance_engine) -> None:
    _, system = _urls(governance_engine)
    completed = subprocess.run(
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
    assert completed.returncode == 0, completed.stderr


async def _request_file(governance_engine, tmp_path: Path):
    _, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    request = MarketResearchWorkflowRequest(
        experiment_id=experiment_id,
        cycle_id=cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    path = tmp_path / "request.json"
    path.write_text(request.model_dump_json(exclude_computed_fields=True))
    return request, path


async def _spawn(
    command: list[str], environment: dict[str, str]
) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *command,
        cwd=Path(__file__).parents[2],
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def _wait_for(path: Path, process: asyncio.subprocess.Process) -> None:
    for _ in range(500):
        if path.exists():
            return
        if process.returncode is not None:
            stdout, stderr = await process.communicate()
            pytest.fail(
                "subprocess exited before barrier: "
                f"{stdout.decode()}\n{stderr.decode()}"
            )
        await asyncio.sleep(0.02)
    process.kill()
    stdout, stderr = await process.communicate()
    pytest.fail(
        f"subprocess never reached barrier: {stdout.decode()}\n{stderr.decode()}"
    )


async def _assert_single_transition(governance_engine, cycle_id) -> None:
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.research_attempts)
                .where(records.research_attempts.c.cycle_id == cycle_id)
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycle_transitions)
                .where(records.cycle_transitions.c.cycle_id == cycle_id)
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.commands)
                .where(records.commands.c.kind == "START_MARKET_RESEARCH")
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.audit)
                .where(records.audit.c.kind == "START_MARKET_RESEARCH")
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.outbox)
                .where(records.outbox.c.topic == "product-record.start-market-research")
            )
            == 1
        )
        assert (
            await connection.scalar(
                select(
                    records.market_research_workflow_bindings.c.delivery_state
                ).where(
                    records.market_research_workflow_bindings.c.cycle_id == cycle_id
                )
            )
            == "RUNTIME_COMPLETED"
        )


async def _persisted_receipt(governance_engine, cycle_id) -> dict[str, object] | None:
    async with governance_engine.connect() as connection:
        transition = (
            (
                await connection.execute(
                    select(records.cycle_transitions).where(
                        records.cycle_transitions.c.cycle_id == cycle_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if transition is None:
            return None
        attempt = (
            (
                await connection.execute(
                    select(records.research_attempts).where(
                        records.research_attempts.c.id
                        == transition["research_attempt_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        return {
            "command_id": str(transition["command_id"]),
            "result_id": str(attempt["id"]),
            "id": str(attempt["id"]),
            "cycle_id": str(cycle_id),
            "ordinal": attempt["ordinal"],
            "transition_id": str(transition["id"]),
            "state": "MARKET_RESEARCH",
        }


def _result(stdout: str) -> dict[str, object]:
    line = next(line for line in stdout.splitlines() if line.startswith("RESULT:"))
    result = json.loads(line.removeprefix("RESULT:"))
    result.pop("schema_version")
    return result


async def test_workflow_binding_replays_identically_and_rejects_identity_changes(
    governance_engine,
):
    _, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    command_key = uuid4()
    request = MarketResearchWorkflowRequest(
        experiment_id=experiment_id,
        cycle_id=cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=command_key,
    )
    repository = MarketResearchWorkflowRepository(governance_engine)

    original = await repository.bind(
        request, application_version=DBOS_APPLICATION_VERSION
    )

    assert (
        await repository.bind(request, application_version=DBOS_APPLICATION_VERSION)
        == original
    )
    with pytest.raises(ProductRecordsDenied, match="WORKFLOW_BINDING_CONFLICT"):
        await repository.bind(
            request.model_copy(update={"command_key": uuid4()}),
            application_version=DBOS_APPLICATION_VERSION,
        )
    with pytest.raises(ProductRecordsDenied, match="WORKFLOW_BINDING_CONFLICT"):
        await repository.bind(
            request.model_copy(
                update={
                    "plan": request.plan.model_copy(update={"content_hash": "f" * 64})
                }
            ),
            application_version=DBOS_APPLICATION_VERSION,
        )

    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count()).select_from(
                    records.market_research_workflow_bindings
                )
            )
        ) == 1


@pytest.mark.parametrize(
    "barrier",
    [
        "before-business",
        "after-business",
        "after-binding-commit",
        "after-receipt-delivery",
    ],
)
async def test_process_kill_recovers_once_across_the_business_commit_boundary(
    governance_engine, tmp_path, barrier
):
    request, request_path = await _request_file(governance_engine, tmp_path)
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    environment = {
        **_environment(governance_engine),
        "ALON_AI_DBOS_TEST_BARRIER": barrier,
        "ALON_AI_DBOS_TEST_READY": str(ready),
        "ALON_AI_DBOS_TEST_RELEASE": str(release),
    }
    process = await _spawn(_command("start", request_path), environment)
    await _wait_for(ready, process)
    original_receipt = await _persisted_receipt(governance_engine, request.cycle_id)
    process.send_signal(signal.SIGKILL)
    await asyncio.wait_for(process.wait(), timeout=10)

    recovered = await asyncio.to_thread(
        subprocess.run,
        _command("recover", request_path),
        cwd=Path(__file__).parents[2],
        env=_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert recovered.returncode == 0, recovered.stderr
    recovered_receipt = _result(recovered.stdout)
    if original_receipt is not None:
        assert recovered_receipt == original_receipt
    await _assert_single_transition(governance_engine, request.cycle_id)


async def test_two_recovery_workers_still_commit_one_transition(
    governance_engine, tmp_path
):
    request, request_path = await _request_file(governance_engine, tmp_path)
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await _spawn(
        _command("start", request_path),
        {
            **_environment(governance_engine),
            "ALON_AI_DBOS_TEST_BARRIER": "after-receipt-delivery",
            "ALON_AI_DBOS_TEST_READY": str(ready),
            "ALON_AI_DBOS_TEST_RELEASE": str(release),
        },
    )
    await _wait_for(ready, process)
    process.kill()
    await asyncio.wait_for(process.wait(), timeout=10)
    workers = [
        await _spawn(
            _command("recover", request_path),
            _environment(governance_engine),
        )
        for _ in range(2)
    ]
    outputs = await asyncio.wait_for(
        asyncio.gather(*(worker.communicate() for worker in workers)), timeout=30
    )
    assert all(worker.returncode == 0 for worker in workers), outputs
    await _assert_single_transition(governance_engine, request.cycle_id)


async def test_version_mismatch_is_reported_instead_of_counting_as_recovery(
    governance_engine, tmp_path
):
    request, request_path = await _request_file(governance_engine, tmp_path)
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await _spawn(
        _command("start", request_path),
        {
            **_environment(governance_engine),
            "ALON_AI_DBOS_TEST_BARRIER": "after-receipt-delivery",
            "ALON_AI_DBOS_TEST_READY": str(ready),
            "ALON_AI_DBOS_TEST_RELEASE": str(release),
        },
    )
    await _wait_for(ready, process)
    process.kill()
    await asyncio.wait_for(process.wait(), timeout=10)

    mismatch = await asyncio.to_thread(
        subprocess.run,
        _command("recover", request_path, application_version="l04-wrong-version"),
        cwd=Path(__file__).parents[2],
        env=_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert mismatch.returncode != 0
    assert "DBOS_APPLICATION_VERSION_MISMATCH" in mismatch.stderr
    assert await _persisted_receipt(governance_engine, request.cycle_id) is not None


async def test_cancellation_before_business_step_leaves_no_partial_state(
    governance_engine, tmp_path
):
    request, request_path = await _request_file(governance_engine, tmp_path)
    _migrate_dbos(governance_engine)
    ready, release = tmp_path / "ready", tmp_path / "release"
    process = await _spawn(
        _command("start", request_path),
        {
            **_environment(governance_engine),
            "ALON_AI_DBOS_TEST_BARRIER": "before-business",
            "ALON_AI_DBOS_TEST_READY": str(ready),
            "ALON_AI_DBOS_TEST_RELEASE": str(release),
        },
    )
    await _wait_for(ready, process)
    cancelled = await asyncio.to_thread(
        subprocess.run,
        _command("cancel", request_path),
        cwd=Path(__file__).parents[2],
        env=_environment(governance_engine),
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert cancelled.returncode == 0, cancelled.stderr
    release.touch()
    await asyncio.wait_for(process.communicate(), timeout=15)
    async with governance_engine.connect() as connection:
        assert not await connection.scalar(
            select(records.cycle_transitions.c.id).where(
                records.cycle_transitions.c.cycle_id == request.cycle_id
            )
        )
        assert not await connection.scalar(
            select(records.research_attempts.c.id).where(
                records.research_attempts.c.cycle_id == request.cycle_id
            )
        )
        assert (
            await connection.scalar(
                select(
                    records.market_research_workflow_bindings.c.delivery_state
                ).where(
                    records.market_research_workflow_bindings.c.cycle_id
                    == request.cycle_id
                )
            )
            == "CANCELLED"
        )


async def test_production_startup_rejects_missing_and_outdated_dbos_schema(
    governance_engine,
):
    environment = _environment(governance_engine)
    missing = await asyncio.to_thread(
        subprocess.run,
        _command("launch", None),
        cwd=Path(__file__).parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert missing.returncode != 0
    assert "run_migrations disabled" in missing.stderr

    _migrate_dbos(governance_engine)
    async with governance_engine.begin() as connection:
        await connection.execute(text("UPDATE dbos.dbos_migrations SET version=1"))
    outdated = await asyncio.to_thread(
        subprocess.run,
        _command("launch", None),
        cwd=Path(__file__).parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert outdated.returncode != 0
    assert "run_migrations disabled" in outdated.stderr
