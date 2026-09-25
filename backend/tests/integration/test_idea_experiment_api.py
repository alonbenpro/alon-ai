"""Authenticated L07 seeded experiment commands against real PostgreSQL."""

import asyncio
import importlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from test_operator_access import ORIGIN, _app
from test_product_records import artifact, roots

from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.api.auth import COOKIE_NAME
from alon_ai.api.recorded_idea_runtime import (
    _RecordedResponses,
    provision_recorded_seeded_runtime,
)
from alon_ai.openai_runtime.contract import RoutingFacts
from alon_ai.providers.contracts import AgentActor, CallAttribution, OperationRunKind
from alon_ai.records import (
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
    ProductRecordsRepository,
)
from alon_ai.records import schema as records

pytestmark = pytest.mark.integration


def creation_body():
    return {
        "name": "Clinic intake",
        "idea_seed": "  Build a clinic intake assistant.\n",
        "brief": {
            "objective": "Test clinic intake demand",
            "target_customer": "Small clinics",
            "problem": "Manual intake",
            "geographies": ["Israel"],
            "commercial_boundaries": "No offer or price before research",
            "budget_usd": "1.00",
            "evidence_definitions": ["Document observed intake workflow"],
            "launch_stage": "SHADOW",
        },
        "operator_profile": {
            "capabilities": ["Python backend development"],
            "constraints": ["No medical advice"],
            "delivery": {
                "max_project_hours": "80",
                "hours_per_week": "20",
                "concurrent_projects": 1,
            },
            "commercial": {
                "currency": "ILS",
                "hourly_cost": "100",
                "minimum_project_price": "5000",
                "minimum_margin_rate": "0.4",
                "maximum_discount_rate": "0.1",
                "minimum_deposit_rate": "0.5",
            },
        },
        "command_key": str(uuid4()),
    }


async def test_runtime_readiness_is_private_and_never_exposes_credentials(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    with TestClient(app) as client:
        assert client.get("/operator/experiments/runtime").status_code == 401
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        response = client.get("/operator/experiments/runtime")
        assert response.status_code == 200
        assert response.json() == {"provider_mode": "disabled", "ready": False}
        assert "test-password" not in response.text
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        assert client.get("/operator/experiments/runtime").json() == {
            "provider_mode": "fake",
            "ready": True,
        }
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "live"})
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        assert client.get("/operator/experiments/runtime").json() == {
            "provider_mode": "live",
            "ready": False,
        }
        experiment_id = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        denied = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert denied.status_code == 409
        assert denied.json() == {"detail": "LIVE_CONFIG_REQUIRED"}


async def test_live_mode_uses_only_explicit_startup_provider_with_recorded_test_transport(
    governance_engine, monkeypatch, tmp_path
):
    app, _ = await _app(governance_engine)
    data_dir = tmp_path / "private"
    app.state.settings = app.state.settings.model_copy(
        update={
            "provider_mode": "live",
            "l07_live_config_path": data_dir / "live-idea.json",
            "l07_secret_root": data_dir / "secrets",
            "l07_secret_key_file": data_dir / "live-secret.key",
            "l07_secret_key_version": "v1",
        }
    )
    app_module = importlib.import_module("alon_ai.api.app")
    observed = []

    def load_config(path):
        observed.append(("config", path))
        return SimpleNamespace(secret_handle="recorded-only")

    def load_secrets(path, *, allowed_handle):
        observed.append(("secrets", path, allowed_handle))
        return SimpleNamespace(get=lambda handle: "recorded-secret")

    async def recorded_live_provider(engine, **kwargs):
        service, attribution = await provision_recorded_seeded_runtime(engine, **kwargs)
        return service, attribution, "OPENAI"

    monkeypatch.setattr(app_module, "load_live_idea_runtime_config", load_config)
    monkeypatch.setattr(app_module, "load_live_secret_store", load_secrets)
    monkeypatch.setattr(
        app_module,
        "build_live_idea_runtime_provider",
        lambda config, secrets: recorded_live_provider,
    )
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        assert client.get("/operator/experiments/runtime").json() == {
            "provider_mode": "live",
            "ready": True,
        }
        experiment_id = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        assert refined.json()["state"] == "AWAITING_REVIEW"
        assert refined.json()["advice_source"] == "OPENAI"
    assert observed == [
        ("config", data_dir / "live-idea.json"),
        ("secrets", data_dir, "recorded-only"),
    ]


async def test_create_seeded_experiment_requires_session_and_retains_exact_seed(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    body = creation_body()
    body["brief"]["budget_usd"] = "150.00"
    with TestClient(app) as client:
        assert (
            client.post("/operator/experiments", json=body, headers=ORIGIN).status_code
            == 401
        )
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = client.post("/operator/experiments", json=body, headers=ORIGIN)
        assert created.status_code == 201, created.text
        ids = created.json()
        assert ids["state"] == "AWAITING_REFINEMENT"
        detail = client.get(f"/operator/experiments/{ids['experiment_id']}")
        assert detail.status_code == 200
        assert detail.json()["idea_seed"] == body["idea_seed"]
        assert detail.json()["brief"] == body["brief"]
        assert detail.json()["accepted_brief"] is None
        assert detail.json()["advice"] is None
        replay = client.post("/operator/experiments", json=body, headers=ORIGIN)
        assert replay.status_code == 201
        assert replay.json() == ids
    async with governance_engine.connect() as connection:
        seeds = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.kind == "IDEA_SEED"
                    )
                )
            )
            .mappings()
            .all()
        )
    assert len(seeds) == 1
    assert seeds[0]["payload"]["statement"] == body["idea_seed"]


async def test_authenticated_operator_cannot_read_another_owners_experiment(
    governance_engine,
):
    repository, _, other_experiment, _, _ = await roots(governance_engine)
    await repository.append_artifact(
        artifact(
            other_experiment,
            ArtifactKind.EXPERIMENT_BRIEF,
            {"objective": "Other owner's private experiment"},
        ),
        command_key=uuid4(),
    )
    seed = await repository.append_artifact(
        artifact(
            other_experiment,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Other private seed"},
        ),
        command_key=uuid4(),
    )
    await repository.create_cycle(
        other_experiment,
        seed=ArtifactInput.from_receipt(seed, role="SEED"),
        command_key=uuid4(),
    )
    app, _ = await _app(governance_engine)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        assert (
            client.get(f"/operator/experiments/{other_experiment}").status_code == 404
        )


async def test_recorded_refinement_is_reviewed_and_accepted_only_by_operator_command(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    body = creation_body()
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = client.post("/operator/experiments", json=body, headers=ORIGIN).json()
        experiment_id = UUID(created["experiment_id"])
        run_id = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        assert refined.json()["outcome"] == "SUCCEEDED"
        assert refined.json()["advice_source"] == "RECORDED_FAKE"
        assert refined.json()["state"] == "AWAITING_REVIEW"
        assert refined.json()["advice"]["core_intent"] == body["idea_seed"].strip()
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["latest_run_id"] == run_id
        assert snapshot["advice"] == refined.json()["advice"]
        assert snapshot["accepted_brief"] is None
        assert client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        ).json() == {"detail": "REVIEW_PENDING"}
        assert (
            client.post(
                f"/operator/experiments/{experiment_id}/refine",
                json={"idempotency_key": run_id},
                headers=ORIGIN,
            ).json()["advice"]
            == refined.json()["advice"]
        )
        accepted = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={"run_id": run_id, "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["state"] == "IDEA_ACCEPTED"
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["accepted_brief"]["core_intent"] == body["idea_seed"].strip()
        assert snapshot["state"] == "IDEA_ACCEPTED"
        assert (
            client.post(
                f"/operator/experiments/{experiment_id}/accept",
                json={"run_id": run_id, "command_key": str(uuid4())},
                headers=ORIGIN,
            ).status_code
            == 409
        )
    async with governance_engine.connect() as connection:
        acceptances = (
            (await connection.execute(select(records.idea_acceptances)))
            .mappings()
            .all()
        )
    assert len(acceptances) == 1


async def test_disabled_runtime_cannot_create_advice_or_acceptance(governance_engine):
    app, _ = await _app(governance_engine)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        run_id = str(uuid4())
        response = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert response.status_code == 409
        assert response.json() == {"detail": "REFINEMENT_UNAVAILABLE"}
        assert (
            client.post(
                f"/operator/experiments/{experiment_id}/accept",
                json={"run_id": run_id, "command_key": str(uuid4())},
                headers=ORIGIN,
            ).status_code
            == 409
        )


async def test_refresh_reports_pending_run_without_suggesting_fresh_refinement(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()
        experiment_id = UUID(created["experiment_id"])
        async with governance_engine.connect() as connection:
            roots = (
                (
                    await connection.execute(
                        select(
                            records.workflows.c.id,
                            records.agents.c.id.label("agent_id"),
                        )
                        .select_from(
                            records.workflows.join(
                                records.agents,
                                records.agents.c.workflow_id == records.workflows.c.id,
                            )
                        )
                        .where(records.workflows.c.experiment_id == experiment_id)
                    )
                )
                .mappings()
                .one()
            )
        run_id, operation_id = uuid4(), uuid4()
        now = datetime.now(UTC)
        attribution = CallAttribution(
            experiment_id=experiment_id,
            workflow_run_id=roots["id"],
            operation_run_id=operation_id,
            operation_run_kind=OperationRunKind.SYSTEM,
            actor=AgentActor(agent_run_id=roots["agent_id"]),
            correlation_id=uuid4(),
            logical_operation_id=uuid4(),
            config_version=uuid4(),
            deadline=now + timedelta(minutes=1),
        )
        await GovernanceProvisioner(governance_engine).scope(attribution)
        async with governance_engine.begin() as connection:
            await connection.execute(
                records.idea_refinements.insert().values(
                    run_id=run_id,
                    experiment_id=experiment_id,
                    cycle_id=created["cycle_id"],
                    seed_artifact_id=created["seed_artifact_id"],
                    operation_id=operation_id,
                    state="RUNNING",
                    advice_source="RECORDED_FAKE",
                    created_at=now,
                )
            )
        detail = client.get(f"/operator/experiments/{experiment_id}")
        assert detail.status_code == 200
        assert detail.json()["state"] == "REFINEMENT_IN_PROGRESS"
        assert detail.json()["latest_run_id"] == str(run_id)
        assert detail.json()["advice"] is None
        blocked = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert blocked.status_code == 409
        assert blocked.json() == {"detail": "REFINEMENT_IN_PROGRESS"}
    async with governance_engine.connect() as connection:
        assert (
            await connection.execute(select(records.idea_acceptances))
        ).mappings().all() == []


async def test_concurrent_refinement_claim_dispatches_only_one_run(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    route = importlib.import_module("alon_ai.api.routes.experiments")
    original = route.provision_recorded_seeded_runtime
    both_provisioned = asyncio.Event()
    dispatch_count = 0
    provision_count = 0
    provision_lock = asyncio.Lock()

    async def delayed_provision(*args, **kwargs):
        nonlocal provision_count
        provision_count += 1
        if provision_count == 2:
            both_provisioned.set()
        await asyncio.wait_for(both_provisioned.wait(), timeout=10)
        async with provision_lock:
            runtime, attribution = await original(*args, **kwargs)
        original_refine = runtime.refine_cycle

        async def delayed_refine(*run_args, **run_kwargs):
            nonlocal dispatch_count
            dispatch_count += 1
            return await original_refine(*run_args, **run_kwargs)

        runtime.refine_cycle = delayed_refine
        return runtime, attribution

    monkeypatch.setattr(route, "provision_recorded_seeded_runtime", delayed_provision)
    with TestClient(app) as setup:
        assert (
            setup.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = setup.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        token = setup.cookies.get(COOKIE_NAME)
        assert token
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies={COOKIE_NAME: token},
        ) as client:
            first = asyncio.create_task(
                client.post(
                    f"/operator/experiments/{experiment_id}/refine",
                    json={"idempotency_key": str(uuid4())},
                    headers=ORIGIN,
                )
            )
            second = asyncio.create_task(
                client.post(
                    f"/operator/experiments/{experiment_id}/refine",
                    json={"idempotency_key": str(uuid4())},
                    headers=ORIGIN,
                )
            )
            responses = await asyncio.wait_for(
                asyncio.gather(first, second), timeout=15
            )
            assert sorted(response.status_code for response in responses) == [
                200,
                409,
            ], [response.text for response in responses]
            assert any(
                response.json() == {"detail": "REFINEMENT_IN_PROGRESS"}
                for response in responses
            ), [response.text for response in responses]
            assert dispatch_count == 1


async def test_same_key_claim_loser_does_not_block_winning_run(
    governance_engine, monkeypatch
):
    app, operator_id = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    route = importlib.import_module("alon_ai.api.routes.experiments")
    run_id = uuid4()
    with TestClient(app) as setup:
        assert (
            setup.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = setup.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()
        async with governance_engine.connect() as connection:
            roots = (
                (
                    await connection.execute(
                        select(
                            records.workflows.c.id,
                            records.agents.c.id.label("agent_id"),
                        )
                        .select_from(
                            records.workflows.join(
                                records.agents,
                                records.agents.c.workflow_id == records.workflows.c.id,
                            )
                        )
                        .where(
                            records.workflows.c.experiment_id
                            == UUID(created["experiment_id"])
                        )
                    )
                )
                .mappings()
                .one()
            )
        runtime, attribution = await provision_recorded_seeded_runtime(
            governance_engine,
            experiment_id=UUID(created["experiment_id"]),
            workflow_id=roots["id"],
            agent_id=roots["agent_id"],
            operator_id=operator_id,
            run_id=run_id,
            budget_usd=Decimal("1.00"),
        )
        two_ready = asyncio.Event()
        arrivals = 0

        async def same_provision(*args, **kwargs):
            nonlocal arrivals
            arrivals += 1
            if arrivals == 2:
                two_ready.set()
            await asyncio.wait_for(two_ready.wait(), timeout=10)
            return runtime, attribution

        monkeypatch.setattr(route, "provision_recorded_seeded_runtime", same_provision)
        token = setup.cookies.get(COOKIE_NAME)
        assert token
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            cookies={COOKIE_NAME: token},
        ) as client:
            path = f"/operator/experiments/{created['experiment_id']}/refine"
            body = {"idempotency_key": str(run_id)}
            responses = await asyncio.wait_for(
                asyncio.gather(
                    client.post(path, json=body, headers=ORIGIN),
                    client.post(path, json=body, headers=ORIGIN),
                ),
                timeout=15,
            )
            assert sorted(response.status_code for response in responses) == [200, 409]
            snapshot = (
                await client.get(f"/operator/experiments/{created['experiment_id']}")
            ).json()
            assert snapshot["state"] == "AWAITING_REVIEW"
            assert snapshot["latest_run_id"] == str(run_id)
            assert snapshot["advice"] is not None


async def test_stale_refinement_uses_ledger_to_decide_safe_retry(governance_engine):
    app, operator_id = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    old = datetime.now(UTC) - timedelta(hours=2)

    async def roots_for(experiment_id):
        async with governance_engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        select(
                            records.workflows.c.id,
                            records.agents.c.id.label("agent_id"),
                        )
                        .select_from(
                            records.workflows.join(
                                records.agents,
                                records.agents.c.workflow_id == records.workflows.c.id,
                            )
                        )
                        .where(records.workflows.c.experiment_id == UUID(experiment_id))
                    )
                )
                .mappings()
                .one()
            )

    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        first = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()
        first_roots = await roots_for(first["experiment_id"])
        uncalled = uuid4()
        attribution = CallAttribution(
            experiment_id=UUID(first["experiment_id"]),
            workflow_run_id=first_roots["id"],
            operation_run_id=uuid4(),
            operation_run_kind=OperationRunKind.SYSTEM,
            actor=AgentActor(agent_run_id=first_roots["agent_id"]),
            correlation_id=uuid4(),
            logical_operation_id=uuid4(),
            config_version=uuid4(),
            deadline=datetime.now(UTC) + timedelta(minutes=1),
        )
        await GovernanceProvisioner(governance_engine).scope(attribution)
        async with governance_engine.begin() as connection:
            await connection.execute(
                records.idea_refinements.insert().values(
                    run_id=uncalled,
                    experiment_id=first["experiment_id"],
                    cycle_id=first["cycle_id"],
                    seed_artifact_id=first["seed_artifact_id"],
                    operation_id=attribution.operation_run_id,
                    state="RUNNING",
                    advice_source="RECORDED_FAKE",
                    created_at=old,
                )
            )
        safe = client.get(f"/operator/experiments/{first['experiment_id']}")
        assert safe.json()["state"] == "REFINEMENT_FAILED"

        second = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()
        second_roots = await roots_for(second["experiment_id"])
        called = uuid4()
        runtime, second_attr = await provision_recorded_seeded_runtime(
            governance_engine,
            experiment_id=UUID(second["experiment_id"]),
            workflow_id=second_roots["id"],
            agent_id=second_roots["agent_id"],
            operator_id=operator_id,
            run_id=called,
            budget_usd=Decimal("1.00"),
        )
        async with governance_engine.begin() as connection:
            await connection.execute(
                records.idea_refinements.insert().values(
                    run_id=called,
                    experiment_id=second["experiment_id"],
                    cycle_id=second["cycle_id"],
                    seed_artifact_id=second["seed_artifact_id"],
                    operation_id=second_attr.operation_run_id,
                    state="RUNNING",
                    advice_source="RECORDED_FAKE",
                    created_at=old,
                )
            )
        execution = await runtime.refine_cycle(
            second_attr,
            cycle_id=UUID(second["cycle_id"]),
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=called,
        )
        assert execution.outcome == "SUCCEEDED"
        blocked = client.get(f"/operator/experiments/{second['experiment_id']}")
        assert blocked.json()["state"] == "REFINEMENT_BLOCKED"
        assert blocked.json()["advice"] is None
        fresh = client.post(
            f"/operator/experiments/{second['experiment_id']}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert fresh.json() == {"detail": "REFINEMENT_RECONCILIATION_REQUIRED"}


async def test_create_key_rejects_changed_operator_profile(governance_engine):
    app, _ = await _app(governance_engine)
    body = creation_body()
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        assert (
            client.post("/operator/experiments", json=body, headers=ORIGIN).status_code
            == 201
        )
        changed = creation_body()
        changed["command_key"] = body["command_key"]
        changed["operator_profile"]["capabilities"] = [
            "Unapproved different capability"
        ]
        response = client.post("/operator/experiments", json=changed, headers=ORIGIN)
        assert response.status_code == 409
        assert response.json() == {"detail": "COMMAND_CONFLICT"}


async def test_create_retry_resumes_after_roots_are_recorded(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    body = creation_body()
    original = ProductRecordsRepository.append_artifact
    failed = False

    async def fail_once(self, draft, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise ProductRecordsDenied("INVALID_STATE")
        return await original(self, draft, **kwargs)

    monkeypatch.setattr(ProductRecordsRepository, "append_artifact", fail_once)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        first = client.post("/operator/experiments", json=body, headers=ORIGIN)
        assert first.status_code == 409
        second = client.post("/operator/experiments", json=body, headers=ORIGIN)
        assert second.status_code == 201, second.text
        assert (
            client.get(
                f"/operator/experiments/{second.json()['experiment_id']}"
            ).json()["idea_seed"]
            == body["idea_seed"]
        )


async def test_accept_retry_reuses_committed_idea_brief(governance_engine, monkeypatch):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = ProductRecordsRepository.accept_idea
    failed = False

    async def fail_once(self, *args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise ProductRecordsDenied("INVALID_STATE")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(ProductRecordsRepository, "accept_idea", fail_once)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        run_id = str(uuid4())
        assert (
            client.post(
                f"/operator/experiments/{experiment_id}/refine",
                json={"idempotency_key": run_id},
                headers=ORIGIN,
            ).status_code
            == 200
        )
        body = {"run_id": run_id, "command_key": str(uuid4())}
        first = client.post(
            f"/operator/experiments/{experiment_id}/accept", json=body, headers=ORIGIN
        )
        assert first.status_code == 409
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()[
                "accepted_brief"
            ]
            is None
        )
        second = client.post(
            f"/operator/experiments/{experiment_id}/accept", json=body, headers=ORIGIN
        )
        assert second.status_code == 200, second.text
        replay = client.post(
            f"/operator/experiments/{experiment_id}/accept", json=body, headers=ORIGIN
        )
        assert replay.status_code == 200
        assert replay.json() == second.json()


async def test_recorded_transport_failure_never_leaks_or_accepts_advice(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})

    async def fail_with_sensitive_detail(self, **kwargs):
        raise RuntimeError("secret-provider-marker")

    monkeypatch.setattr(_RecordedResponses, "create", fail_with_sensitive_detail)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        run_id = str(uuid4())
        response = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert "secret-provider-marker" not in response.text
        assert response.status_code == 200
        assert response.json()["outcome"] == "UNCERTAIN"
        assert response.json()["state"] == "REFINEMENT_BLOCKED"
        assert response.json()["advice"] is None
        replay = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert replay.status_code == 200
        assert replay.json()["outcome"] == response.json()["outcome"]
        new_run = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert new_run.status_code == 409
        assert new_run.json() == {"detail": "REFINEMENT_RECONCILIATION_REQUIRED"}
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["state"] == "REFINEMENT_BLOCKED"
        assert snapshot["advice"] is None
        assert snapshot["accepted_brief"] is None
        assert (
            client.post(
                f"/operator/experiments/{experiment_id}/accept",
                json={"run_id": run_id, "command_key": str(uuid4())},
                headers=ORIGIN,
            ).status_code
            == 409
        )


async def test_material_pivot_advice_cannot_be_accepted(governance_engine, monkeypatch):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = _RecordedResponses.create

    async def material_pivot(self, **kwargs):
        response = await original(self, **kwargs)
        advice = json.loads(response["output"][0]["content"][0]["text"])
        advice["material_pivot"] = True
        response["output"][0]["content"][0]["text"] = json.dumps(advice)
        return response

    monkeypatch.setattr(_RecordedResponses, "create", material_pivot)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        run_id = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        assert refined.json()["advice"]["material_pivot"] is True
        denied = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={"run_id": run_id, "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert denied.status_code == 409
        assert denied.json() == {"detail": "MATERIAL_PIVOT_REQUIRES_APPROVAL"}
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()[
                "accepted_brief"
            ]
            is None
        )


async def test_seed_preserving_narrowing_can_be_accepted(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = _RecordedResponses.create

    async def narrow_without_replacing_seed(self, **kwargs):
        response = await original(self, **kwargs)
        advice = json.loads(response["output"][0]["content"][0]["text"])
        advice["core_intent"] += " Focus on small Israeli clinics."
        response["output"][0]["content"][0]["text"] = json.dumps(advice)
        return response

    monkeypatch.setattr(_RecordedResponses, "create", narrow_without_replacing_seed)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = client.post(
            "/operator/experiments", json=creation_body(), headers=ORIGIN
        ).json()
        run_id = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{created['experiment_id']}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert refined.status_code == 200
        accepted = client.post(
            f"/operator/experiments/{created['experiment_id']}/accept",
            json={"run_id": run_id, "command_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
