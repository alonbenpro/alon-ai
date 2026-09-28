"""R01A durable operator run admission against isolated PostgreSQL."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_minimal_intake import configured_app, login
from test_operator_access import ORIGIN
from test_operator_records import profile

from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.integrations.recorded_idea import _RecordedResponses
from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
from alon_ai.services import agent_run_service as agent_run_service_module
from alon_ai.services import ideas as ideas_module
from alon_ai.services.agent_run_service import (
    AgentRunService,
    reconcile_incomplete_idea_runs,
    run_admitted_idea_job,
)
from alon_ai.services.experiments import AcceptRequest, ExperimentContext
from alon_ai.services.ideas import IdeaService
from alon_ai.services.intake import IntakeService
from alon_ai.services.schemas.agent_runs import (
    AgentRunRequest,
    CancelRunRequest,
    RejectRunRequest,
)
from alon_ai.services.schemas.intake import GenerateIdeaRequest


async def test_run_admission_is_idempotent_and_durable(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Exact seed\n", draft=False
    )
    service = AgentRunService(context)
    request = AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())

    first = await service.admit(experiment_id, request)
    second = await service.admit(experiment_id, request)
    saved = await service.get(UUID(str(first.run_id)))

    assert first == second
    assert first.status == "QUEUED"
    assert saved.run_id == first.run_id
    assert [item.kind for item in saved.resolved_inputs] == [
        "EXPERIMENT_BRIEF",
        "IDEA_SEED",
    ]
    seed_payload = saved.resolved_inputs[1].payload
    assert seed_payload is not None
    assert seed_payload["statement"] == "Exact seed\n"
    refreshed = await IntakeService(context).snapshot(experiment_id)
    assert refreshed["latest_run_id"] == first.run_id
    assert refreshed["stage_status"] == "RUNNING"


async def test_worker_execution_retains_result_without_second_provider_call(
    governance_engine,
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Buyer calls\nNeed follow-up", draft=False
    )
    service = AgentRunService(context)
    admitted = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )

    await service.execute(admitted.run_id)
    first = await service.get(admitted.run_id)
    await service.execute(admitted.run_id)
    replay = await service.result(admitted.run_id)

    assert first.status == "SUCCEEDED"
    assert first.output is not None
    assert first.output["buyer"]["role"]
    assert first.output["grounding_refs"]
    assert replay.output == first.output
    assert replay.run_id == admitted.run_id


async def test_same_command_on_other_experiment_conflicts(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    intake = IntakeService(context)
    first_experiment = await intake._roots(uuid4(), "First", draft=False)
    second_experiment = await intake._roots(uuid4(), "Second", draft=False)
    service = AgentRunService(context)
    body = AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    await service.admit(first_experiment, body)

    with pytest.raises(ExperimentError, match="COMMAND_CONFLICT"):
        await service.admit(second_experiment, body)


async def test_queued_cancel_is_confirmed_and_prevents_execution(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(uuid4(), "Exact", draft=False)
    service = AgentRunService(context)
    admitted = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    key = uuid4()

    cancelled = await service.cancel(admitted.run_id, CancelRunRequest(command_key=key))
    await service.execute(admitted.run_id)
    events = await service.events(admitted.run_id)

    assert cancelled.confirmed is True
    assert cancelled.status == "CANCELLED"
    assert [event.type for event in events.events] == ["QUEUED", "CANCEL_CONFIRMED"]
    assert (await service.get(admitted.run_id)).output is None


@pytest.mark.parametrize("origin", ["supplied", "generated"])
async def test_cancelled_queued_intake_is_terminal_across_refresh_and_replay(
    governance_engine, origin
):
    from alon_ai.services.experiments import CreateExperimentRequest

    app, operator_id = await configured_app(governance_engine)
    settings = app.state.settings.model_copy(update={"provider_mode": "live"})
    context = ExperimentContext(
        governance_engine, settings, operator_id, idea_runtime_provider=object()
    )
    intake = IntakeService(context)
    command_key = uuid4()
    snapshot = (
        await intake.create(
            CreateExperimentRequest(
                idea_seed="Exact supplied\nidea", command_key=command_key
            )
        )
        if origin == "supplied"
        else await intake.generate(GenerateIdeaRequest(command_key=command_key))
    )
    assert snapshot["stage_status"] == "RUNNING"
    run_id = snapshot["latest_run_id"]
    service = AgentRunService(context)
    cancel_body = CancelRunRequest(command_key=uuid4())

    first = await service.cancel(run_id, cancel_body)
    replay = await service.cancel(run_id, cancel_body)
    await service.execute(run_id)
    refreshed = await intake.snapshot(snapshot["experiment_id"])
    command = await intake.store.command(snapshot["experiment_id"], command_key)

    assert first == replay
    assert first.confirmed is True
    assert first.status == "CANCELLED"
    assert command["state"] == "BLOCKED"
    assert refreshed["stage_status"] == "BLOCKED"
    assert refreshed["blocked_reason"] == "CANCELLED"
    assert refreshed["latest_run_id"] == run_id
    assert [event.type for event in (await service.events(run_id)).events] == [
        "QUEUED",
        "CANCEL_CONFIRMED",
    ]


async def test_other_operator_cannot_read_run(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Private idea", draft=False
    )
    admitted = await AgentRunService(context).admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )

    stranger = AgentRunService(
        ExperimentContext(governance_engine, app.state.settings, uuid4())
    )
    with pytest.raises(ExperimentError) as denied:
        await stranger.get(admitted.run_id)
    assert denied.value.status_code == 404


async def test_supplied_intake_run_has_inspectable_retained_result(governance_engine):
    app, _operator_id = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operator/experiments",
            json={"idea_seed": "Exact multiline\nidea", "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert response.status_code == 201, response.text
        snapshot = response.json()
        inspected = client.get(f"/operator/agent-runs/{snapshot['latest_run_id']}")
        assert inspected.status_code == 200, inspected.text
        run = inspected.json()
        assert (
            run["resolved_inputs"][1]["payload"]["statement"] == "Exact multiline\nidea"
        )
        assert run["output"]["buyer"]["role"]
        assert run["status"] == "SUCCEEDED"


async def test_generated_intake_run_is_inspectable(governance_engine):
    app, _operator_id = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operator/ideas/generate",
            json={"command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert response.status_code == 200, response.text
        snapshot = response.json()
        inspected = client.get(f"/operator/agent-runs/{snapshot['latest_run_id']}")
        assert inspected.status_code == 200, inspected.text
        run = inspected.json()
        assert run["task_kind"] == "IDEA_DISCOVERY"
        assert len(run["output"]["candidates"]) >= 3


async def test_authenticated_profile_setup_enables_intake_without_sql(
    governance_engine,
):
    app, operator_id = await configured_app(governance_engine, with_profile=False)
    approved = profile(operator_id)
    with TestClient(app) as client:
        login(client)
        setup = client.post(
            "/operator/idea-profile",
            json={
                "profile": {
                    "capabilities": list(approved.capabilities),
                    "constraints": list(approved.constraints),
                    "delivery": approved.delivery.model_dump(
                        mode="json", exclude={"schema_version"}
                    ),
                    "commercial": approved.commercial.model_dump(
                        mode="json", exclude={"schema_version"}
                    ),
                }
            },
            headers=ORIGIN,
        )
        assert setup.status_code == 200, setup.text
        assert setup.json()["profile_version"] == 1
        assert setup.json()["budget_usd"] == "1.00"
        response = client.post(
            "/operator/experiments",
            json={"idea_seed": "A supported idea", "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert response.status_code == 201, response.text


async def test_successful_run_stays_pending_review_until_explicit_accept(
    governance_engine,
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Review this idea", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    await service.execute(ref.run_id)
    assert (await service.get(ref.run_id)).review_status == "PENDING"
    assert (await service.get(ref.run_id)).phase == "WAITING_FOR_OPERATOR"
    with TestClient(app) as client:
        login(client)
        accepted = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": str(ref.run_id),
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "I reviewed this exact output and approve it.",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
    assert (await service.get(ref.run_id)).review_status == "ACCEPTED"
    assert (await service.get(ref.run_id)).phase == "ACCEPTED"


async def test_reject_is_retained_and_prevents_later_acceptance(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Reject this idea", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    await service.execute(ref.run_id)
    rejected = await service.reject(
        ref.run_id, RejectRunRequest(command_key=uuid4(), reason="Wrong buyer")
    )
    assert rejected.review_status == "REJECTED"
    with TestClient(app) as client:
        login(client)
        acceptance = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": str(ref.run_id),
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Try to accept rejected output.",
            },
            headers=ORIGIN,
        )
        assert acceptance.status_code == 409
        assert acceptance.json() == {"detail": "IDEA_RUN_REJECTED"}


async def test_accepted_run_cannot_be_rejected_afterward(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Accept first", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    await service.execute(ref.run_id)
    with TestClient(app) as client:
        login(client)
        accepted = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": str(ref.run_id),
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "This exact run preserves the idea.",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text

    with pytest.raises(ExperimentError) as denied:
        await service.reject(
            ref.run_id, RejectRunRequest(command_key=uuid4(), reason="Too late")
        )
    assert denied.value.detail == "RUN_ALREADY_ACCEPTED"
    assert (await service.get(ref.run_id)).review_status == "ACCEPTED"


async def test_acceptance_claim_serializes_concurrent_rejection(
    governance_engine, monkeypatch
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Concurrent decision", draft=False
    )
    runs = AgentRunService(context)
    ref = await runs.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    await runs.execute(ref.run_id)
    body = AcceptRequest(
        run_id=ref.run_id,
        command_key=uuid4(),
        intent_relationship="PRESERVES_CORE_INTENT",
        intent_confirmed=True,
        intent_rationale="I reviewed this exact run and approve it.",
    )
    claimed, release = asyncio.Event(), asyncio.Event()
    original = AgentRunRepository.claim_acceptance

    async def pause_after_claim(self, run_id, experiment_id, operator_id, command_key):
        result = await original(self, run_id, experiment_id, operator_id, command_key)
        claimed.set()
        await release.wait()
        return result

    monkeypatch.setattr(AgentRunRepository, "claim_acceptance", pause_after_claim)
    accepting = asyncio.create_task(IdeaService(context).accept(experiment_id, body))
    try:
        await asyncio.wait_for(claimed.wait(), 10)
        with pytest.raises(ExperimentError) as denied:
            await runs.reject(
                ref.run_id,
                RejectRunRequest(command_key=uuid4(), reason="Race loser"),
            )
        assert denied.value.detail == "RUN_REVIEW_CONFLICT"
    finally:
        release.set()
    accepted = await accepting
    replay = await IdeaService(context).accept(experiment_id, body)
    assert replay == accepted
    assert (await runs.get(ref.run_id)).review_status == "ACCEPTED"


async def test_acceptance_claim_survives_persistence_failure_for_same_key_retry(
    governance_engine, monkeypatch
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Recover acceptance", draft=False
    )
    runs = AgentRunService(context)
    ref = await runs.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    await runs.execute(ref.run_id)
    body = AcceptRequest(
        run_id=ref.run_id,
        command_key=uuid4(),
        intent_relationship="PRESERVES_CORE_INTENT",
        intent_confirmed=True,
        intent_rationale="Approved after reviewing exact output.",
    )
    original = ideas_module.experiment_repository.save_intent_review
    failed = False

    async def fail_once(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected persistence failure")
        return await original(*args, **kwargs)

    monkeypatch.setattr(
        ideas_module.experiment_repository, "save_intent_review", fail_once
    )
    with pytest.raises(RuntimeError, match="injected persistence failure"):
        await IdeaService(context).accept(experiment_id, body)
    with pytest.raises(ExperimentError) as denied:
        await runs.reject(
            ref.run_id,
            RejectRunRequest(command_key=uuid4(), reason="Conflicting decision"),
        )
    assert denied.value.detail == "RUN_REVIEW_CONFLICT"
    accepted = await IdeaService(context).accept(experiment_id, body)
    assert accepted["state"] == "IDEA_ACCEPTED"
    assert (await runs.get(ref.run_id)).review_status == "ACCEPTED"


async def test_rejected_discovery_cannot_be_selected_or_started(governance_engine):
    app, _operator_id = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        generated = client.post(
            "/operator/ideas/generate",
            json={"command_key": str(uuid4())},
            headers=ORIGIN,
        ).json()
        experiment_id = generated["experiment_id"]
        run_id = generated["latest_run_id"]
        candidate_id = generated["candidates"][0]["artifact_id"]
        rejected = client.post(
            f"/operator/agent-runs/{run_id}/reject",
            json={"command_key": str(uuid4()), "reason": "No suitable buyer"},
            headers=ORIGIN,
        )
        assert rejected.status_code == 200, rejected.text
        selected = client.post(
            f"/operator/experiments/{experiment_id}/select",
            json={
                "candidate_artifact_id": candidate_id,
                "reason": "Attempt to bypass rejected discovery",
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        )
        started = client.post(
            f"/operator/ideas/{experiment_id}/start",
            json={"candidate_artifact_id": candidate_id, "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert selected.status_code == 409
        assert selected.json() == {"detail": "DISCOVERY_RUN_REJECTED"}
        assert started.status_code == 409
        assert started.json() == {"detail": "DISCOVERY_RUN_REJECTED"}


async def test_worker_denies_provider_mode_change_before_dispatch(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    fake_context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(fake_context)._roots(
        uuid4(), "Mode pinned", draft=False
    )
    ref = await AgentRunService(fake_context).admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    live_context = ExperimentContext(
        governance_engine,
        app.state.settings.model_copy(update={"provider_mode": "live"}),
        operator_id,
        idea_runtime_provider=object(),
    )

    await AgentRunService(live_context).execute(ref.run_id)

    saved = await AgentRunService(fake_context).get(ref.run_id)
    assert saved.status == "BLOCKED"
    assert saved.blocked_reason == "RUN_PROVIDER_MODE_CHANGED"
    assert saved.receipt_id is None


async def test_worker_denies_application_version_change_before_dispatch(
    governance_engine, monkeypatch
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Version pinned", draft=False
    )
    ref = await AgentRunService(context).admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    monkeypatch.setattr(
        agent_run_service_module, "DBOS_APPLICATION_VERSION", "new-worker-version"
    )

    await run_admitted_idea_job(governance_engine, app.state.settings, ref.run_id)

    saved = await AgentRunService(context).get(ref.run_id)
    assert saved.status == "BLOCKED"
    assert saved.blocked_reason == "RUN_APPLICATION_VERSION_CHANGED"
    assert saved.receipt_id is None


async def test_missing_live_credential_is_retained_block_without_dispatch(
    governance_engine,
):
    app, operator_id = await configured_app(governance_engine)
    original = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(original)._roots(
        uuid4(), "No credential", draft=False
    )
    live = ExperimentContext(
        governance_engine,
        app.state.settings.model_copy(update={"provider_mode": "live"}),
        operator_id,
    )
    service = AgentRunService(live)

    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )

    assert ref.status == "BLOCKED"
    assert (await service.get(ref.run_id)).blocked_reason == "LIVE_CONFIG_REQUIRED"
    assert await service.store.pending() == []


async def test_missing_budget_denies_new_run_admission(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    original = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(original)._roots(
        uuid4(), "Budgeted seed", draft=False
    )
    missing = ExperimentContext(
        governance_engine,
        app.state.settings.model_copy(update={"idea_intake_budget_usd": None}),
        operator_id,
    )
    with pytest.raises(ExperimentError) as denied:
        await AgentRunService(missing).admit(
            experiment_id,
            AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4()),
        )
    assert denied.value.detail == "INTAKE_BUDGET_REQUIRED"


async def test_intake_retry_repairs_failed_run_admission_without_second_call(
    governance_engine, monkeypatch
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    intake = IntakeService(context)
    from alon_ai.services.experiments import CreateExperimentRequest

    body = CreateExperimentRequest(idea_seed="Retry admission", command_key=uuid4())
    original = AgentRunRepository.admit
    attempts = 0

    async def fail_once(self, values):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("run insert failed before provider dispatch")
        return await original(self, values)

    monkeypatch.setattr(AgentRunRepository, "admit", fail_once)
    with pytest.raises(RuntimeError):
        await intake.create(body)
    saved = await intake.create(body)

    assert attempts == 2
    assert saved["state"] == "AWAITING_REVIEW"
    assert (
        await AgentRunService(context).get(saved["latest_run_id"])
    ).status == "SUCCEEDED"


async def test_cancel_after_dispatch_reports_unknown_until_provider_settles(
    governance_engine, monkeypatch
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Uncertain cancel", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    entered, release = asyncio.Event(), asyncio.Event()
    original = _RecordedResponses.create
    calls = 0

    async def delayed(self, **kwargs):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return await original(self, **kwargs)

    monkeypatch.setattr(_RecordedResponses, "create", delayed)
    running = asyncio.create_task(service.execute(ref.run_id))
    try:
        await asyncio.wait_for(entered.wait(), 10)
        cancellation = await service.cancel(
            ref.run_id, CancelRunRequest(command_key=uuid4())
        )
        assert cancellation.requested is True
        assert cancellation.confirmed is False
        assert cancellation.status == "OUTCOME_UNKNOWN"
    finally:
        release.set()
    await running
    saved = await service.get(ref.run_id)
    assert saved.status == "SUCCEEDED"
    assert saved.cancel_requested is True
    assert saved.cancel_confirmed is False
    assert calls == 1


async def test_cancel_after_success_is_terminal_noop(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Already done", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    await service.execute(ref.run_id)
    before = await service.events(ref.run_id)

    cancelled = await service.cancel(ref.run_id, CancelRunRequest(command_key=uuid4()))

    assert cancelled.requested is False
    assert cancelled.confirmed is False
    assert cancelled.status == "SUCCEEDED"
    assert await service.events(ref.run_id) == before
    assert (await service.get(ref.run_id)).cancel_requested is False


async def test_separate_dbos_worker_dispatches_persisted_idea_run(governance_engine):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Worker supplied idea", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    system_url = governance_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    await asyncio.to_thread(
        subprocess.run,
        [
            str(Path(sys.executable).with_name("dbos")),
            "migrate",
            "--sys-db-url",
            system_url,
            "--schema",
            "dbos",
        ],
        cwd=Path(__file__).parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    env = {
        **os.environ,
        "ALON_AI_DATABASE_URL": governance_engine.url.render_as_string(
            hide_password=False
        ),
        "ALON_AI_DBOS_SYSTEM_DATABASE_URL": system_url,
        "ALON_AI_ENVIRONMENT": "test",
        "ALON_AI_PROVIDER_MODE": "fake",
        "ALON_AI_IDEA_INTAKE_BUDGET_USD": "1.00",
    }
    worker = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alon_ai.worker.main",
        cwd=Path(__file__).parents[2],
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        for _ in range(100):
            if (await service.get(ref.run_id)).status == "SUCCEEDED":
                break
            if worker.returncode is not None:
                output, errors = await worker.communicate()
                pytest.fail(f"worker exited: {output.decode()} {errors.decode()}")
            await asyncio.sleep(0.1)
        else:
            pytest.fail("worker did not dispatch admitted Idea run")
    finally:
        if worker.returncode is None:
            worker.terminate()
            await asyncio.wait_for(worker.communicate(), 10)
    assert (await service.get(ref.run_id)).output is not None


async def test_worker_restart_marks_unsettled_run_unknown_without_resend(
    governance_engine,
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(governance_engine, app.state.settings, operator_id)
    experiment_id = await IntakeService(context)._roots(
        uuid4(), "Interrupted", draft=False
    )
    service = AgentRunService(context)
    ref = await service.admit(
        experiment_id, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    assert await service.store.start(ref.run_id)

    await reconcile_incomplete_idea_runs(governance_engine)
    await service.execute(ref.run_id)

    saved = await service.get(ref.run_id)
    assert saved.status == "OUTCOME_UNKNOWN"
    assert saved.output is None
    assert await service.store.pending() == []


async def test_dispatch_denies_wrong_experiment_artifact_before_provider(
    governance_engine, monkeypatch
):
    app, operator_id = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator_id,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    intake = IntakeService(context)
    first = await intake._roots(uuid4(), "First seed", draft=False)
    second = await intake._roots(uuid4(), "Other seed", draft=False)
    service = AgentRunService(context)
    first_ref = await service.admit(
        first, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    other_ref = await service.admit(
        second, AgentRunRequest(task_kind="IDEA_REFINEMENT", command_key=uuid4())
    )
    original = await service.store.get(first_ref.run_id)
    foreign = await service.store.get(other_ref.run_id)
    assert original and foreign
    bad_id, bad_key = uuid4(), uuid4()
    await service.store.admit(
        {
            "run_id": bad_id,
            "command_key": bad_key,
            "experiment_id": first,
            "operator_id": operator_id,
            "task_kind": "IDEA_REFINEMENT",
            "request_hash": "a" * 64,
            "input_refs": [original["input_refs"][0], foreign["input_refs"][1]],
            "profile_id": original["profile_id"],
            "profile_version": original["profile_version"],
            "profile_hash": original["profile_hash"],
            "provider_mode": "fake",
            "dbos_workflow_id": f"idea-{bad_id}",
            "application_version": original["application_version"],
        }
    )

    async def forbidden(self, **kwargs):
        raise AssertionError("provider transport reached for foreign artifact")

    monkeypatch.setattr(_RecordedResponses, "create", forbidden)
    await service.execute(bad_id)
    saved = await service.store.get(bad_id)
    assert saved["status"] == "BLOCKED"
    assert saved["blocked_reason"] == "IDEA_INPUT_STALE"
    inspected = await service.get(bad_id)
    assert inspected.blocked_reason == "IDEA_INPUT_STALE"
    assert inspected.resolved_inputs[1].payload is None
