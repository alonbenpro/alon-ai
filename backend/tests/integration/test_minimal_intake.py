"""R01A-UX authenticated minimal intake through real governed recorded runs."""

import json
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_operator_access import ORIGIN, _app
from test_operator_records import profile

from alon_ai.db.repositories.records_operators import OperatorRepository
from alon_ai.db.tables import records
from alon_ai.integrations.recorded_idea import _RecordedResponses


async def configured_app(engine, *, mode="fake", with_profile=True, with_budget=True):
    app, operator = await _app(engine)
    if with_profile:
        saved = profile(operator)
        await OperatorRepository(engine).register_profile(saved, command_key=uuid4())
    app.state.settings = app.state.settings.model_copy(
        update={
            "provider_mode": mode,
            "idea_intake_budget_usd": Decimal("1.00") if with_budget else None,
        }
    )
    return app, operator


def login(client):
    assert (
        client.post(
            "/auth/login", json={"password": "test-password"}, headers=ORIGIN
        ).status_code
        == 200
    )


async def test_minimal_supplied_idea_pins_context_dispatches_once_and_requires_acceptance(
    governance_engine, monkeypatch
):
    app, _operator = await configured_app(governance_engine)
    calls = []
    original = _RecordedResponses.create

    async def observe(self, **kwargs):
        calls.append(json.loads(kwargs["input_json"]))
        return await original(self, **kwargs)

    monkeypatch.setattr(_RecordedResponses, "create", observe)
    exact = "  An assistant for appointment intake.\n"
    body = {"idea_seed": exact, "command_key": str(uuid4())}
    with TestClient(app) as client:
        assert (
            client.post("/operator/experiments", json=body, headers=ORIGIN).status_code
            == 401
        )
        login(client)
        response = client.post("/operator/experiments", json=body, headers=ORIGIN)
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["state"] == "AWAITING_REVIEW", saved
        assert saved["stage"] == "IDEA_REFINEMENT"
        assert saved["provider_mode"] == "fake"
        assert saved["advice_source"] == "RECORDED_FAKE"
        assert saved["idea_seed"] == exact
        assert saved["accepted_brief"] is None
        assert saved["latest_run_id"]
        assert saved["brief"] == {
            "intake_policy": "R01A_UX_V1",
            "budget_usd": "1.00",
            "launch_stage": "SHADOW",
            "guidance": "",
        }
        assert (
            client.post("/operator/experiments", json=body, headers=ORIGIN).json()
            == saved
        )
        assert (
            client.get(f"/operator/experiments/{saved['experiment_id']}").json()
            == saved
        )
        changed = {**body, "idea_seed": "Different"}
        assert (
            client.post(
                "/operator/experiments", json=changed, headers=ORIGIN
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/operator/experiments", json={**body, "brief": {}}, headers=ORIGIN
            ).status_code
            == 422
        )
        accepted = client.post(
            f"/operator/experiments/{saved['experiment_id']}/accept",
            json={
                "run_id": saved["latest_run_id"],
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "I reviewed the proposal and it preserves my idea.",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
        assert (
            client.get(f"/operator/experiments/{saved['experiment_id']}").json()[
                "stage_status"
            ]
            == "COMPLETE"
        )
    assert len(calls) == 1
    assert calls[0]["artifacts"][0]["payload"]["statement"] == exact
    context = calls[0]["operator_profiles"][0]
    assert context["capabilities"] == [
        "Python development",
        "Business process automation",
    ]
    assert (
        not {"commercial", "delivery", "operator_id", "auth_subject", "hourly_cost"}
        & context.keys()
    )
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(select(func.count()).select_from(records.idea_refinements))
            == 1
        )
        bound = (
            (
                await c.execute(
                    select(records.experiments).where(
                        records.experiments.c.id == UUID(saved["experiment_id"])
                    )
                )
            )
            .mappings()
            .one()
        )
        assert bound["operator_profile_version"] == 1


async def test_missing_saved_context_is_one_targeted_block(governance_engine):
    app, _ = await configured_app(governance_engine, with_profile=False)
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operator/experiments",
            json={"idea_seed": "One idea", "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert response.json() == {"detail": "OPERATOR_PROFILE_REQUIRED"}


async def test_guided_discovery_preserves_exact_text_and_command_identity(
    governance_engine,
):
    app, _ = await configured_app(governance_engine)
    guidance = "  Software services for small dental clinics.\nKeep it practical.  "
    command_key = str(uuid4())
    with TestClient(app) as client:
        login(client)
        body = {"command_key": command_key, "generation_guidance": guidance}
        response = client.post("/operator/ideas/generate", json=body, headers=ORIGIN)
        assert response.status_code == 200, response.text
        saved = response.json()
        assert saved["brief"]["guidance"] == guidance
        assert (
            client.post("/operator/ideas/generate", json=body, headers=ORIGIN).json()
            == saved
        )
        conflict = client.post(
            "/operator/ideas/generate",
            json={**body, "generation_guidance": "A different market"},
            headers=ORIGIN,
        )
        assert conflict.status_code == 409


async def test_missing_budget_is_one_targeted_block(governance_engine):
    app, _ = await configured_app(governance_engine, with_budget=False)
    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/operator/experiments",
            json={"idea_seed": "One idea", "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert response.json() == {"detail": "INTAKE_BUDGET_REQUIRED"}


async def test_generation_revision_regeneration_and_start_retain_lineage(
    governance_engine,
):
    app, _ = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        request = {"command_key": str(uuid4())}
        generated = client.post(
            "/operator/ideas/generate", json=request, headers=ORIGIN
        )
        assert generated.status_code == 200, generated.text
        draft = generated.json()
        assert draft["state"] == "AWAITING_SELECTION", draft
        assert draft["draft"] is True
        assert len(draft["candidates"]) == 3
        assert (
            client.post("/operator/ideas/generate", json=request, headers=ORIGIN).json()
            == draft
        )
        eid = draft["experiment_id"]
        candidate = draft["candidates"][0]
        exact = "  Refined appointment proposal.\n"
        revision_request = {
            "candidate_artifact_id": candidate["artifact_id"],
            "idea_seed": exact,
            "command_key": str(uuid4()),
        }
        revised = client.post(
            f"/operator/ideas/{eid}/revisions", json=revision_request, headers=ORIGIN
        )
        assert revised.status_code == 200, revised.text
        revision = revised.json()["proposal_history"][-1]
        assert revision["idea_seed"] == exact
        assert revision["parent_artifact_id"] == candidate["artifact_id"]
        assert revision["origin"] == "OPERATOR_EDIT"
        regenerated = client.post(
            f"/operator/ideas/{eid}/generate",
            json={
                "candidate_artifact_id": revision["artifact_id"],
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        )
        assert regenerated.status_code == 200, regenerated.text
        assert len(regenerated.json()["proposal_history"]) == 7, regenerated.json()
        descendants = [
            entry
            for entry in regenerated.json()["proposal_history"]
            if entry["run_id"] == regenerated.json()["latest_run_id"]
        ]
        assert len(descendants) == 3
        assert all(
            entry["parent_artifact_id"] == revision["artifact_id"]
            for entry in descendants
        )
        assert (
            client.get(f"/operator/experiments/{eid}").json()["proposal_history"]
            == regenerated.json()["proposal_history"]
        )
        assert exact.strip() in regenerated.json()["candidates"][0]["hypothesis"]
        # Historical command replay must retain its original run and batch.
        assert (
            client.post("/operator/ideas/generate", json=request, headers=ORIGIN).json()
            == draft
        )
        assert (
            client.post(
                f"/operator/ideas/{eid}/revisions",
                json=revision_request,
                headers=ORIGIN,
            ).json()
            == revised.json()
        )
        start_request = {
            "candidate_artifact_id": revision["artifact_id"],
            "command_key": str(uuid4()),
        }
        started = client.post(
            f"/operator/ideas/{eid}/start", json=start_request, headers=ORIGIN
        )
        assert started.status_code == 200, started.text
        saved = started.json()
        assert saved["draft"] is False
        assert saved["state"] == "AWAITING_REVIEW", saved
        assert saved["selected_candidate_artifact_id"] == revision["artifact_id"]
        assert saved["accepted_brief"] is None
        assert (
            client.post(
                f"/operator/ideas/{eid}/start", json=start_request, headers=ORIGIN
            ).json()
            == saved
        )
        assert client.get(f"/operator/experiments/{eid}").json() == saved


async def test_unconfigured_live_mode_is_visible_and_never_falls_back(
    governance_engine, monkeypatch
):
    app, _ = await configured_app(governance_engine, mode="live")

    async def forbidden(*args, **kwargs):
        raise AssertionError("Fake transport must not run for live intake")

    monkeypatch.setattr(_RecordedResponses, "create", forbidden)
    body = {"idea_seed": "An idea", "command_key": str(uuid4())}
    with TestClient(app) as client:
        login(client)
        response = client.post("/operator/experiments", json=body, headers=ORIGIN)
        assert response.status_code == 201, response.text
        snapshot = response.json()
        assert snapshot["stage_status"] == "BLOCKED"
        assert snapshot["blocked_reason"] == "LIVE_CONFIG_REQUIRED"
        assert snapshot["provider_mode"] == "live"
        assert snapshot["latest_run_id"] is not None
        inspected = client.get(f"/operator/agent-runs/{snapshot['latest_run_id']}")
        assert inspected.status_code == 200
        assert inspected.json()["status"] == "BLOCKED"
        assert (
            client.post("/operator/experiments", json=body, headers=ORIGIN).json()
            == snapshot
        )


async def test_interrupted_creation_reuses_pinned_profile_budget_and_exact_seed(
    governance_engine, monkeypatch
):
    from alon_ai.db.repositories.records import ProductRecordsRepository
    from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
    from alon_ai.services.experiments import CreateExperimentRequest, ExperimentContext
    from alon_ai.services.intake import IntakeService

    app, operator = await configured_app(governance_engine)
    context = ExperimentContext(
        governance_engine,
        app.state.settings,
        operator,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    original = ProductRecordsRepository.append_artifact
    failed = False

    async def interrupt_once(self, draft, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("simulated process stop before first artifact")
        return await original(self, draft, **kwargs)

    monkeypatch.setattr(ProductRecordsRepository, "append_artifact", interrupt_once)
    body = CreateExperimentRequest(
        idea_seed="  Keep exact input.\n", command_key=uuid4()
    )
    import pytest

    with pytest.raises(RuntimeError):
        await IntakeService(context).create(body)
    async with governance_engine.connect() as c:
        pinned = (await c.execute(select(records.operator_profiles))).mappings().one()
    await OperatorRepository(governance_engine).register_profile(
        profile(operator, id_=pinned["id"], version=2), command_key=uuid4()
    )
    changed = ExperimentContext(
        governance_engine,
        app.state.settings.model_copy(
            update={"idea_intake_budget_usd": Decimal("9.00")}
        ),
        operator,
        recorded_runtime_provisioner=provision_recorded_seeded_runtime,
    )
    saved = await IntakeService(changed).create(body)
    assert saved["state"] == "AWAITING_REVIEW", saved
    assert saved["idea_seed"] == body.idea_seed
    assert saved["brief"]["budget_usd"] == "1.00"
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(select(records.experiments.c.operator_profile_version)) == 1
        )
        assert (
            await c.scalar(select(func.count()).select_from(records.idea_refinements))
            == 1
        )


async def test_concurrent_start_and_refresh_expose_same_claim_without_second_dispatch(
    governance_engine, monkeypatch
):
    import asyncio

    from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
    from alon_ai.services.experiments import CreateExperimentRequest, ExperimentContext
    from alon_ai.services.intake import IntakeService

    app, operator = await configured_app(governance_engine)
    service = IntakeService(
        ExperimentContext(
            governance_engine,
            app.state.settings,
            operator,
            recorded_runtime_provisioner=provision_recorded_seeded_runtime,
        )
    )
    entered, release = asyncio.Event(), asyncio.Event()
    original = _RecordedResponses.create
    calls = 0

    async def slow(self, **kwargs):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return await original(self, **kwargs)

    monkeypatch.setattr(_RecordedResponses, "create", slow)
    body = CreateExperimentRequest(idea_seed="One concurrent idea", command_key=uuid4())
    first = asyncio.create_task(service.create(body))
    try:
        await asyncio.wait_for(entered.wait(), 10)
        replay = await service.create(body)
        assert replay["stage_status"] == "RUNNING"
        refreshed = await service.snapshot(replay["experiment_id"])
        assert refreshed["latest_run_id"] == replay["latest_run_id"]
    finally:
        release.set()
    finished = await first
    assert finished["latest_run_id"] == replay["latest_run_id"]
    assert finished["state"] == "AWAITING_REVIEW"
    assert calls == 1


async def test_unexpected_dispatch_error_is_durable_block_and_never_replayed(
    governance_engine, monkeypatch
):
    from alon_ai.services.experiments import CreateExperimentRequest, ExperimentContext
    from alon_ai.services.ideas import IdeaService
    from alon_ai.services.intake import IntakeService

    app, operator = await configured_app(governance_engine)
    service = IntakeService(
        ExperimentContext(governance_engine, app.state.settings, operator)
    )
    calls = 0

    async def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("private detail must not be exposed")

    monkeypatch.setattr(IdeaService, "refine", interrupted)
    body = CreateExperimentRequest(idea_seed="One bounded idea", command_key=uuid4())
    first = await service.create(body)
    assert first["stage_status"] == "BLOCKED"
    assert first["blocked_reason"] == "INTAKE_UNAVAILABLE"
    assert await service.create(body) == first
    assert calls == 1


async def test_crash_after_selection_has_explicit_safe_start_recovery(
    governance_engine, monkeypatch
):
    import importlib
    from datetime import UTC, datetime, timedelta

    import pytest

    from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
    from alon_ai.services.experiments import ExperimentContext
    from alon_ai.services.intake import IntakeService
    from alon_ai.services.schemas.intake import (
        GenerateIdeaRequest,
        StartProposalRequest,
    )

    app, operator = await configured_app(governance_engine)
    service = IntakeService(
        ExperimentContext(
            governance_engine,
            app.state.settings,
            operator,
            recorded_runtime_provisioner=provision_recorded_seeded_runtime,
        )
    )
    generated = await service.generate(GenerateIdeaRequest(command_key=uuid4()))
    eid = generated["experiment_id"]
    proposal = generated["candidates"][0]["artifact_id"]
    original = service._dispatch

    async def crash(*args, **kwargs):
        raise RuntimeError("process disappeared after exact selection")

    monkeypatch.setattr(service, "_dispatch", crash)
    with pytest.raises(RuntimeError):
        await service.start(
            eid,
            StartProposalRequest(candidate_artifact_id=proposal, command_key=uuid4()),
        )
    assert not await service.store.has_refinement(eid)

    class AfterDeadline(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz or UTC) + timedelta(hours=2)

    module = importlib.import_module("alon_ai.services.intake")
    monkeypatch.setattr(module, "datetime", AfterDeadline)
    blocked = await service.snapshot(eid)
    assert blocked["draft"] is True
    assert blocked["stage_status"] == "BLOCKED"
    assert blocked["blocked_reason"] == "INTAKE_RECONCILIATION_REQUIRED"
    monkeypatch.setattr(module, "datetime", datetime)
    monkeypatch.setattr(service, "_dispatch", original)
    recovered = await service.start(
        eid, StartProposalRequest(candidate_artifact_id=proposal, command_key=uuid4())
    )
    assert recovered["state"] == "AWAITING_REVIEW", recovered
    assert recovered["draft"] is False
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(select(func.count()).select_from(records.idea_refinements))
            == 1
        )
        assert (
            await c.scalar(
                select(func.count()).select_from(records.candidate_selections)
            )
            == 1
        )


async def test_full_operator_projection_remains_available_to_other_agent_paths(
    governance_engine,
):
    from datetime import UTC, datetime

    from alon_ai.agents.runtime import AcceptedOperatorProfile
    from alon_ai.db.repositories.openai_inputs import accepted_input

    app, _ = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        snapshot = client.post(
            "/operator/experiments",
            json={"idea_seed": "One idea", "command_key": str(uuid4())},
            headers=ORIGIN,
        ).json()
    async with governance_engine.connect() as c:
        saved = (await c.execute(select(records.operator_profiles))).mappings().one()
    ref = AcceptedOperatorProfile(
        profile_id=saved["id"],
        version=saved["version"],
        content_hash=saved["content_hash"],
        experiment_id=UUID(snapshot["experiment_id"]),
    )
    result = json.loads(
        await accepted_input(
            governance_engine, (), (), (ref,), (), ref.experiment_id, datetime.now(UTC)
        )
    )
    assert result["operator_profiles"][0]["commercial"] == saved["commercial"]
    assert result["operator_profiles"][0]["delivery"] == saved["delivery"]


async def test_unguided_regeneration_does_not_inherit_previous_guidance(
    governance_engine,
):
    app, _ = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        draft = client.post(
            "/operator/ideas/generate",
            json={"command_key": str(uuid4())},
            headers=ORIGIN,
        ).json()
        eid = draft["experiment_id"]
        edited = client.post(
            f"/operator/ideas/{eid}/revisions",
            json={
                "candidate_artifact_id": draft["candidates"][0]["artifact_id"],
                "idea_seed": "Specific operator revision B",
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        ).json()
        revision = edited["proposal_history"][-1]
        guided = client.post(
            f"/operator/ideas/{eid}/generate",
            json={
                "candidate_artifact_id": revision["artifact_id"],
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        ).json()
        assert all(
            "Specific operator revision B" in c["hypothesis"]
            for c in guided["candidates"]
            if c["artifact_id"] != revision["artifact_id"]
        )
        unguided = client.post(
            f"/operator/ideas/{eid}/generate",
            json={"command_key": str(uuid4())},
            headers=ORIGIN,
        ).json()
        assert unguided["state"] == "AWAITING_SELECTION", unguided
        latest = [
            r
            for r in unguided["proposal_history"]
            if r["run_id"] == unguided["latest_run_id"]
        ]
        assert len(latest) == 3
        assert all(
            r["parent_artifact_id"] is None
            and "Specific operator revision B" not in r["hypothesis"]
            for r in latest
        )


async def test_stale_or_invalid_start_cannot_poison_completed_run(governance_engine):
    app, _ = await configured_app(governance_engine)
    with TestClient(app) as client:
        login(client)
        draft = client.post(
            "/operator/ideas/generate",
            json={"command_key": str(uuid4())},
            headers=ORIGIN,
        ).json()
        eid = draft["experiment_id"]
        invalid = client.post(
            f"/operator/ideas/{eid}/start",
            json={"candidate_artifact_id": str(uuid4()), "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert invalid.status_code == 409
        assert (
            client.get(f"/operator/experiments/{eid}").json()["blocked_reason"] is None
        )
        body = {
            "candidate_artifact_id": draft["candidates"][0]["artifact_id"],
            "command_key": str(uuid4()),
        }
        started = client.post(
            f"/operator/ideas/{eid}/start", json=body, headers=ORIGIN
        ).json()
        assert started["state"] == "AWAITING_REVIEW", started
        rejected = client.post(
            f"/operator/ideas/{eid}/start",
            json={**body, "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert rejected.status_code == 409
        assert client.get(f"/operator/experiments/{eid}").json() == started


async def test_other_authenticated_operator_cannot_replay_retained_intake_receipts(
    governance_engine,
):
    from alon_ai.api.app import create_app
    from alon_ai.services.schemas.records_operator import OperatorIdentity

    app, _ = await configured_app(governance_engine)
    with TestClient(app) as owner:
        login(owner)
        generated = owner.post(
            "/operator/ideas/generate",
            json={"command_key": str(uuid4())},
            headers=ORIGIN,
        ).json()
        eid = generated["experiment_id"]
        revision_body = {
            "candidate_artifact_id": generated["candidates"][0]["artifact_id"],
            "idea_seed": "Private operator proposal text",
            "command_key": str(uuid4()),
        }
        revised = owner.post(
            f"/operator/ideas/{eid}/revisions", json=revision_body, headers=ORIGIN
        )
        assert revised.status_code == 200, revised.text
        revision_id = revised.json()["proposal_history"][-1]["artifact_id"]
        generation_body = {
            "candidate_artifact_id": revision_id,
            "command_key": str(uuid4()),
        }
        regenerated = owner.post(
            f"/operator/ideas/{eid}/generate", json=generation_body, headers=ORIGIN
        )
        assert regenerated.status_code == 200, regenerated.text
        start_body = {"candidate_artifact_id": revision_id, "command_key": str(uuid4())}
        started = owner.post(
            f"/operator/ideas/{eid}/start", json=start_body, headers=ORIGIN
        )
        assert started.status_code == 200, started.text

    other = OperatorIdentity(
        id=uuid4(), auth_subject="other@example.test", display_name="Other operator"
    )
    await OperatorRepository(governance_engine).register_operator(
        other, command_key=uuid4()
    )
    other_app = create_app(
        app.state.settings.model_copy(
            update={"operator_auth_subject": other.auth_subject}
        )
    )
    with TestClient(other_app) as stranger:
        login(stranger)
        assert stranger.get(f"/operator/experiments/{eid}").status_code == 404
        for action, body in [
            ("revisions", revision_body),
            ("generate", generation_body),
            ("start", start_body),
        ]:
            replay = stranger.post(
                f"/operator/ideas/{eid}/{action}", json=body, headers=ORIGIN
            )
            assert replay.status_code == 404, (action, replay.text)
            assert replay.json() == {"detail": "EXPERIMENT_NOT_FOUND"}
            changed = stranger.post(
                f"/operator/ideas/{eid}/{action}",
                json={**body, "command_key": str(uuid4())},
                headers=ORIGIN,
            )
            assert changed.status_code == 404, (action, changed.text)
    with TestClient(app) as owner:
        login(owner)
        assert (
            owner.post(
                f"/operator/ideas/{eid}/revisions", json=revision_body, headers=ORIGIN
            ).json()
            == revised.json()
        )
        assert (
            owner.post(
                f"/operator/ideas/{eid}/generate", json=generation_body, headers=ORIGIN
            ).json()
            == regenerated.json()
        )
        assert (
            owner.post(
                f"/operator/ideas/{eid}/start", json=start_body, headers=ORIGIN
            ).json()
            == started.json()
        )


async def test_missing_terminal_receipt_never_replays_a_later_run(
    governance_engine, monkeypatch
):
    import pytest

    from alon_ai.db.repositories.experiments import ExperimentError
    from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
    from alon_ai.services.experiments import ExperimentContext, _id
    from alon_ai.services.intake import IntakeService
    from alon_ai.services.schemas.intake import (
        GenerateIdeaRequest,
        RegenerateIdeaRequest,
    )

    app, operator = await configured_app(governance_engine)
    service = IntakeService(
        ExperimentContext(
            governance_engine,
            app.state.settings,
            operator,
            recorded_runtime_provisioner=provision_recorded_seeded_runtime,
        )
    )
    request = GenerateIdeaRequest(command_key=uuid4())
    original = service.store.receipt

    async def crash_before_receipt(experiment_id, key, result=None, **kwargs):
        if result is not None:
            raise RuntimeError("process stopped after terminal state, before receipt")
        return await original(experiment_id, key, **kwargs)

    monkeypatch.setattr(service.store, "receipt", crash_before_receipt)
    with pytest.raises(RuntimeError):
        await service.generate(request)
    monkeypatch.setattr(service.store, "receipt", original)
    eid = _id(operator, f"intake/{request.command_key}")
    first = await service.snapshot(eid)
    later = await service.regenerate(eid, RegenerateIdeaRequest(command_key=uuid4()))
    assert later["latest_run_id"] != first["latest_run_id"]
    with pytest.raises(ExperimentError) as blocked:
        await service.generate(request)
    assert blocked.value.detail == "INTAKE_RECONCILIATION_REQUIRED"
    assert await service.store.receipt(eid, request.command_key) is None
    assert (await service.snapshot(eid))["latest_run_id"] == later["latest_run_id"]
