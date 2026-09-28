"""Authenticated L07 seeded experiment commands against real PostgreSQL."""

import asyncio
import importlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Response
from pydantic import ValidationError
from sqlalchemy import func, select
from test_operator_access import ORIGIN, _app
from test_product_records import artifact, roots

from alon_ai.agents.idea_discovery import SeededIdeaBriefAdvice
from alon_ai.agents.schemas.openai import RoutingFacts
from alon_ai.db.repositories.accounting import GovernanceProvisioner
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.tables import records
from alon_ai.integrations.schemas.provider import (
    AgentActor,
    CallAttribution,
    OperationRunKind,
)
from alon_ai.provider_usage.recorded_idea import (
    _RecordedResponses,
    provision_recorded_seeded_runtime,
)
from alon_ai.services.auth import COOKIE_NAME
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)

pytestmark = pytest.mark.integration


def test_historical_advice_reads_without_weakening_new_profile_contract():
    route = importlib.import_module("alon_ai.services.experiments")
    historical = {
        "title": "Legacy brief",
        "customer": "Legacy customer",
        "problem": "Legacy problem",
        "core_intent": "legacy intent",
        "intent_relationship": "PRESERVES_CORE_INTENT",
        "material_pivot": False,
        "grounding_refs": ["SEED"],
        "uncertainties": ["Legacy uncertainty"],
    }
    with pytest.raises(ValidationError):
        SeededIdeaBriefAdvice.model_validate(historical)
    assert (
        route._read_persisted_advice(SeededIdeaBriefAdvice, historical)["core_intent"]
        == "legacy intent"
    )


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


def create_historical(client, *, json, headers):
    """Seed pre-intake records without retaining an obsolete production endpoint."""
    from alon_ai.db.repositories.experiments import ExperimentError
    from alon_ai.services.experiments import (
        HistoricalExperimentInput,
        create_experiment,
    )

    async def seed():
        operator = await client.app.state.auth.resolve(client.cookies.get(COOKIE_NAME))
        if operator is None:
            return Response(401, json={"detail": "Operator session required"})
        context = client.app.state.experiment_service_factory._context(operator.id)
        try:
            result = await create_experiment(
                context, HistoricalExperimentInput.model_validate(json)
            )
            return Response(201, json=jsonable_encoder(result))
        except ExperimentError as error:
            return Response(error.status_code, json={"detail": error.detail})

    return client.portal.call(seed)


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
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
    data_dir.mkdir(mode=0o700)
    config_path = data_dir / "combined-idea.json"
    config_path.write_text("{}", encoding="utf-8")
    config_path.chmod(0o600)
    app.state.settings = app.state.settings.model_copy(
        update={
            "provider_mode": "live",
            "r01a_live_config_path": config_path,
        }
    )
    combined_idea = importlib.import_module("alon_ai.services.combined_idea")
    provision = importlib.import_module("alon_ai.services.combined_idea_provision")
    observed = []
    config = SimpleNamespace(secret_handle="recorded-only")
    secrets = SimpleNamespace(get=lambda handle: "recorded-secret")

    def load_config(cls, raw):
        observed.append(("config", raw))
        return config

    def load_secrets(path, loaded_config):
        observed.append(("secrets", path, loaded_config))
        return secrets

    async def recorded_live_provider(engine, **kwargs):
        service, attribution = await provision_recorded_seeded_runtime(engine, **kwargs)
        return service, attribution, "OPENAI"

    monkeypatch.setattr(
        combined_idea.CombinedIdeaConfig,
        "model_validate_json",
        classmethod(load_config),
    )
    monkeypatch.setattr(provision, "load_combined_secret_store", load_secrets)
    monkeypatch.setattr(
        combined_idea,
        "build_combined_idea_provider",
        lambda loaded_config, loaded_secrets, settings: recorded_live_provider,
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
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
        ("config", "{}"),
        ("secrets", data_dir, config),
    ]


async def test_create_seeded_experiment_requires_session_and_retains_exact_seed(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    body = creation_body()
    body["brief"]["budget_usd"] = "150.00"
    with TestClient(app) as client:
        assert create_historical(client, json=body, headers=ORIGIN).status_code == 401
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = create_historical(client, json=body, headers=ORIGIN)
        assert created.status_code == 201, created.text
        ids = created.json()
        assert ids["state"] == "AWAITING_REFINEMENT"
        detail = client.get(f"/operator/experiments/{ids['experiment_id']}")
        assert detail.status_code == 200
        assert detail.json()["idea_seed"] == body["idea_seed"]
        assert detail.json()["brief"] == body["brief"]
        assert detail.json()["accepted_brief"] is None
        assert detail.json()["advice"] is None
        replay = create_historical(client, json=body, headers=ORIGIN)
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
        created = create_historical(client, json=body, headers=ORIGIN).json()
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
            json={
                "run_id": run_id,
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Same clinic intake service",
            },
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
                json={
                    "run_id": run_id,
                    "command_key": str(uuid4()),
                    "intent_relationship": "PRESERVES_CORE_INTENT",
                    "intent_confirmed": True,
                    "intent_rationale": "Same clinic intake service",
                },
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
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
                json={
                    "run_id": run_id,
                    "command_key": str(uuid4()),
                    "intent_relationship": "PRESERVES_CORE_INTENT",
                    "intent_confirmed": True,
                    "intent_rationale": "No successful advice exists",
                },
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
        created = create_historical(client, json=creation_body(), headers=ORIGIN).json()
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
    route = importlib.import_module("alon_ai.bootstrap")
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
        experiment_id = create_historical(
            setup, json=creation_body(), headers=ORIGIN
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
    route = importlib.import_module("alon_ai.bootstrap")
    run_id = uuid4()
    with TestClient(app) as setup:
        assert (
            setup.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = create_historical(setup, json=creation_body(), headers=ORIGIN).json()
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
        first = create_historical(client, json=creation_body(), headers=ORIGIN).json()
        first_roots = await roots_for(first["experiment_id"])
        uncalled = uuid4()
        first_runtime, attribution = await provision_recorded_seeded_runtime(
            governance_engine,
            experiment_id=UUID(first["experiment_id"]),
            workflow_id=first_roots["id"],
            agent_id=first_roots["agent_id"],
            operator_id=operator_id,
            run_id=uncalled,
            budget_usd=Decimal("1.00"),
        )
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
        unresolved = client.get(f"/operator/experiments/{first['experiment_id']}")
        assert unresolved.json()["state"] == "REFINEMENT_BLOCKED"
        assert unresolved.json()["retry_safe"] is False
        fresh = client.post(
            f"/operator/experiments/{first['experiment_id']}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert fresh.json() == {"detail": "REFINEMENT_RECONCILIATION_REQUIRED"}
        # The owner still has a valid attribution and can dispatch after the stale read.
        late_execution = await first_runtime.refine_cycle(
            attribution,
            cycle_id=UUID(first["cycle_id"]),
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=uncalled,
        )
        assert late_execution.outcome == "SUCCEEDED"
        assert (
            client.get(f"/operator/experiments/{first['experiment_id']}").json()[
                "state"
            ]
            == "REFINEMENT_BLOCKED"
        )

        second = create_historical(client, json=creation_body(), headers=ORIGIN).json()
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


async def test_stale_discovery_with_live_owner_remains_blocked(governance_engine):
    app, operator_id = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    body = creation_body()
    body.pop("idea_seed")
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = create_historical(client, json=body, headers=ORIGIN).json()
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
        run_id = uuid4()
        runtime, attribution = await provision_recorded_seeded_runtime(
            governance_engine,
            experiment_id=experiment_id,
            workflow_id=roots["id"],
            agent_id=roots["agent_id"],
            operator_id=operator_id,
            run_id=run_id,
            budget_usd=Decimal("1.00"),
        )
        async with governance_engine.begin() as connection:
            await connection.execute(
                records.idea_discoveries.insert().values(
                    run_id=run_id,
                    experiment_id=experiment_id,
                    operation_id=attribution.operation_run_id,
                    state="RUNNING",
                    advice_source="RECORDED_FAKE",
                    created_at=datetime.now(UTC) - timedelta(hours=2),
                )
            )
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["state"] == "DISCOVERY_BLOCKED"
        assert snapshot["retry_safe"] is False
        fresh = client.post(
            f"/operator/experiments/{experiment_id}/discover",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert fresh.json() == {"detail": "DISCOVERY_RECONCILIATION_REQUIRED"}
        late_execution = await runtime.discover_system(
            attribution,
            facts=RoutingFacts(needs_ai=True),
            idempotency_key=run_id,
        )
        assert late_execution.outcome == "SUCCEEDED"
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()["state"]
            == "DISCOVERY_BLOCKED"
        )


async def test_other_experiment_same_discovery_key_cannot_block_existing_owner(
    governance_engine, monkeypatch
):
    app, operator_id = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    body_a = creation_body()
    body_a.pop("idea_seed")
    body_b = creation_body()
    body_b.pop("idea_seed")
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        first = create_historical(client, json=body_a, headers=ORIGIN).json()
        second = create_historical(client, json=body_b, headers=ORIGIN).json()
        first_id, second_id = (
            UUID(first["experiment_id"]),
            UUID(second["experiment_id"]),
        )
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
                        .where(records.workflows.c.experiment_id == first_id)
                    )
                )
                .mappings()
                .one()
            )
        shared_key = uuid4()
        _, attribution = await provision_recorded_seeded_runtime(
            governance_engine,
            experiment_id=first_id,
            workflow_id=roots["id"],
            agent_id=roots["agent_id"],
            operator_id=operator_id,
            run_id=shared_key,
            budget_usd=Decimal("1.00"),
        )
        async with governance_engine.begin() as connection:
            await connection.execute(
                records.idea_discoveries.insert().values(
                    run_id=shared_key,
                    experiment_id=first_id,
                    operation_id=attribution.operation_run_id,
                    state="RUNNING",
                    advice_source="RECORDED_FAKE",
                    created_at=datetime.now(UTC),
                )
            )
        route = importlib.import_module("alon_ai.bootstrap")

        async def collision(*args, **kwargs):
            assert kwargs["experiment_id"] == second_id
            assert kwargs["run_id"] == shared_key
            raise RuntimeError("same-key provisioning conflict")

        monkeypatch.setattr(route, "provision_recorded_seeded_runtime", collision)
        denied = client.post(
            f"/operator/experiments/{second_id}/discover",
            json={"idempotency_key": str(shared_key)},
            headers=ORIGIN,
        )
        assert denied.status_code == 409
        owner = client.get(f"/operator/experiments/{first_id}").json()
        assert owner["state"] == "DISCOVERY_IN_PROGRESS"
        assert owner["retry_safe"] is False


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
        assert create_historical(client, json=body, headers=ORIGIN).status_code == 201
        changed = creation_body()
        changed["command_key"] = body["command_key"]
        changed["operator_profile"]["capabilities"] = [
            "Unapproved different capability"
        ]
        response = create_historical(client, json=changed, headers=ORIGIN)
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
        first = create_historical(client, json=body, headers=ORIGIN)
        assert first.status_code == 409
        second = create_historical(client, json=body, headers=ORIGIN)
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
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
        body = {
            "run_id": run_id,
            "command_key": str(uuid4()),
            "intent_relationship": "PRESERVES_CORE_INTENT",
            "intent_confirmed": True,
            "intent_rationale": "Same clinic intake service",
        }
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
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
                json={
                    "run_id": run_id,
                    "command_key": str(uuid4()),
                    "intent_relationship": "PRESERVES_CORE_INTENT",
                    "intent_confirmed": True,
                    "intent_rationale": "No successful advice exists",
                },
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
        advice["intent_relationship"] = "MATERIAL_PIVOT"
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
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
            json={
                "run_id": run_id,
                "command_key": str(uuid4()),
                "intent_relationship": "MATERIAL_PIVOT",
                "intent_confirmed": True,
                "intent_rationale": "Model proposes a different service",
            },
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
        created = create_historical(client, json=creation_body(), headers=ORIGIN).json()
        run_id = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{created['experiment_id']}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert refined.status_code == 200
        accepted = client.post(
            f"/operator/experiments/{created['experiment_id']}/accept",
            json={
                "run_id": run_id,
                "command_key": str(uuid4()),
                "intent_relationship": "NARROWS_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Focuses on smaller clinics",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text


async def test_operator_review_rejects_unrelated_and_requires_confirmation(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
        path = f"/operator/experiments/{experiment_id}/accept"
        base = {"run_id": run_id, "command_key": str(uuid4())}
        assert client.post(
            path,
            json={
                **base,
                "intent_relationship": "UNRELATED",
                "intent_confirmed": True,
                "intent_rationale": "Different service",
            },
            headers=ORIGIN,
        ).json() == {"detail": "IDEA_UNRELATED"}
        assert client.post(
            path,
            json={
                **base,
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": False,
                "intent_rationale": "Needs review",
            },
            headers=ORIGIN,
        ).json() == {"detail": "INTENT_CONFIRMATION_REQUIRED"}
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()[
                "accepted_brief"
            ]
            is None
        )


async def test_semantic_operator_review_accepts_paraphrase_without_prefix(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = _RecordedResponses.create

    async def paraphrase(self, **kwargs):
        response = await original(self, **kwargs)
        advice = json.loads(response["output"][0]["content"][0]["text"])
        advice["core_intent"] = (
            "Provide software that improves the way clinics collect patient intake details."
        )
        response["output"][0]["content"][0]["text"] = json.dumps(advice)
        return response

    monkeypatch.setattr(_RecordedResponses, "create", paraphrase)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
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
        accepted = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": run_id,
                "command_key": str(uuid4()),
                "intent_relationship": "CLARIFIES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Same workflow goal in clearer words",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["state"] == "IDEA_ACCEPTED"

    async with governance_engine.connect() as connection:
        review = (
            (await connection.execute(select(records.idea_intent_reviews)))
            .mappings()
            .one()
        )
    assert review["relationship"] == "CLARIFIES_CORE_INTENT"
    assert review["rationale"] == "Same workflow goal in clearer words"
    assert review["source_artifact_id"] is not None


async def test_model_unrelated_continuation_cannot_be_confirmed_as_preserved(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = _RecordedResponses.create

    async def contradictory(self, **kwargs):
        response = await original(self, **kwargs)
        advice = json.loads(response["output"][0]["content"][0]["text"])
        advice["core_intent"] += (
            " Stop building clinic intake software and sell insurance leads."
        )
        advice["intent_relationship"] = "UNRELATED"
        response["output"][0]["content"][0]["text"] = json.dumps(advice)
        return response

    monkeypatch.setattr(_RecordedResponses, "create", contradictory)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        run_id = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        assert refined.json()["advice"]["intent_relationship"] == "UNRELATED"
        denied = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": run_id,
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "I think this is the same idea",
            },
            headers=ORIGIN,
        )
        assert denied.status_code == 409
        assert denied.json() == {"detail": "IDEA_UNRELATED"}
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()[
                "accepted_brief"
            ]
            is None
        )


async def test_system_discovery_persists_reviewable_batch_before_selection(
    governance_engine,
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    body = creation_body()
    body.pop("idea_seed")
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        created = create_historical(client, json=body, headers=ORIGIN)
        assert created.status_code == 201, created.text
        experiment_id = created.json()["experiment_id"]
        assert created.json()["state"] == "AWAITING_DISCOVERY"
        assert created.json()["cycle_id"] is None
        before = client.get(f"/operator/experiments/{experiment_id}").json()
        assert before["mode"] == "SYSTEM_DISCOVERY"
        assert before["candidates"] == []
        assert client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        ).json() == {"detail": "CANDIDATE_SELECTION_REQUIRED"}
        run_id = str(uuid4())
        discovered = client.post(
            f"/operator/experiments/{experiment_id}/discover",
            json={"idempotency_key": run_id},
            headers=ORIGIN,
        )
        assert discovered.status_code == 200, discovered.text
        assert discovered.json()["state"] == "AWAITING_SELECTION"
        assert len(discovered.json()["candidates"]) == 3
        refreshed = client.get(f"/operator/experiments/{experiment_id}").json()
        assert refreshed["candidates"] == discovered.json()["candidates"]
        assert refreshed["latest_run_id"] == run_id
        assert refreshed["selected_candidate_artifact_id"] is None
        choice = refreshed["candidates"][1]["artifact_id"]
        selection_body = {
            "candidate_artifact_id": choice,
            "reason": "Fits delivery constraints",
            "command_key": str(uuid4()),
        }
        selected = client.post(
            f"/operator/experiments/{experiment_id}/select",
            json=selection_body,
            headers=ORIGIN,
        )
        assert selected.status_code == 200, selected.text
        assert selected.json()["state"] == "AWAITING_REFINEMENT"
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()[
                "selected_candidate_artifact_id"
            ]
            == choice
        )
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        assert refined.json()["state"] == "AWAITING_REVIEW"
        assert refined.json()["advice"]["grounding_refs"] == ["SELECTED_CANDIDATE"]
        accepted = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": refined.json()["run_id"],
                "command_key": str(uuid4()),
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Keeps the selected workflow hypothesis",
            },
            headers=ORIGIN,
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["state"] == "IDEA_ACCEPTED"
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()[
                "accepted_brief"
            ]["core_intent"]
            == refined.json()["advice"]["core_intent"]
        )
        replay = client.post(
            f"/operator/experiments/{experiment_id}/select",
            json=selection_body,
            headers=ORIGIN,
        )
        assert replay.status_code == 200, replay.text
        assert replay.json() == selected.json()


async def test_settled_schema_failure_confirms_safe_retry_and_new_run(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = _RecordedResponses.create
    calls = 0

    async def malformed_once(self, **kwargs):
        nonlocal calls
        calls += 1
        response = await original(self, **kwargs)
        if calls == 1:
            response["output"][0]["content"][0]["text"] = "{}"
        return response

    monkeypatch.setattr(_RecordedResponses, "create", malformed_once)
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = create_historical(
            client, json=creation_body(), headers=ORIGIN
        ).json()["experiment_id"]
        first_id = str(uuid4())
        first = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": first_id},
            headers=ORIGIN,
        )
        assert first.status_code == 200, first.text
        assert first.json()["outcome"] == "SCHEMA_MISMATCH"
        assert first.json()["state"] == "REFINEMENT_FAILED"
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["retry_safe"] is True
        assert snapshot["latest_run_id"] == first_id
        replay = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": first_id},
            headers=ORIGIN,
        )
        assert replay.json()["state"] == "REFINEMENT_FAILED"
        second = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert second.status_code == 200, second.text
        assert second.json()["state"] == "AWAITING_REVIEW"


async def test_settled_discovery_failure_allows_new_key(governance_engine, monkeypatch):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = _RecordedResponses.create
    attempts = 0

    async def malformed_once(self, **kwargs):
        nonlocal attempts
        attempts += 1
        response = await original(self, **kwargs)
        if attempts == 1:
            response["output"][0]["content"][0]["text"] = "{}"
        return response

    monkeypatch.setattr(_RecordedResponses, "create", malformed_once)
    body = creation_body()
    body.pop("idea_seed")
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = create_historical(client, json=body, headers=ORIGIN).json()[
            "experiment_id"
        ]
        path = f"/operator/experiments/{experiment_id}/discover"
        first_id = str(uuid4())
        first = client.post(path, json={"idempotency_key": first_id}, headers=ORIGIN)
        assert first.status_code == 200, first.text
        assert first.json()["state"] == "DISCOVERY_FAILED"
        assert (
            client.get(f"/operator/experiments/{experiment_id}").json()["retry_safe"]
            is True
        )
        second = client.post(
            path, json={"idempotency_key": str(uuid4())}, headers=ORIGIN
        )
        assert second.status_code == 200, second.text
        assert second.json()["state"] == "AWAITING_SELECTION"
        assert (
            len(
                client.get(f"/operator/experiments/{experiment_id}").json()[
                    "candidates"
                ]
            )
            == 3
        )


async def test_interrupted_candidate_batch_cannot_be_selected(
    governance_engine, monkeypatch
):
    app, _ = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original = ProductRecordsRepository.append_artifact
    candidate_writes = 0

    async def fail_second_candidate(self, draft, **kwargs):
        nonlocal candidate_writes
        if draft.kind == ArtifactKind.IDEA_CANDIDATE:
            candidate_writes += 1
            if candidate_writes == 2:
                raise ProductRecordsDenied("INVALID_STATE")
        return await original(self, draft, **kwargs)

    monkeypatch.setattr(
        ProductRecordsRepository, "append_artifact", fail_second_candidate
    )
    body = creation_body()
    body.pop("idea_seed")
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id = create_historical(client, json=body, headers=ORIGIN).json()[
            "experiment_id"
        ]
        first = client.post(
            f"/operator/experiments/{experiment_id}/discover",
            json={"idempotency_key": str(uuid4())},
            headers=ORIGIN,
        )
        assert first.status_code == 409
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["state"] == "DISCOVERY_BLOCKED"
        assert snapshot["candidates"] == []
        assert snapshot["retry_safe"] is False
        async with governance_engine.connect() as connection:
            partial_id = await connection.scalar(
                select(records.artifacts.c.id).where(
                    records.artifacts.c.experiment_id == UUID(experiment_id),
                    records.artifacts.c.kind == ArtifactKind.IDEA_CANDIDATE,
                )
            )
        assert partial_id is not None
        assert client.post(
            f"/operator/experiments/{experiment_id}/select",
            json={
                "candidate_artifact_id": str(partial_id),
                "reason": "Looks useful",
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        ).json() == {"detail": "CANDIDATE_NOT_IN_DISCOVERY"}


async def _seeded_return_fixture(client, engine, operator_id):
    """Create only durable local records needed to exercise the L07 return UI."""
    body = creation_body()
    created = create_historical(client, json=body, headers=ORIGIN).json()
    experiment_id = UUID(created["experiment_id"])
    run_id = str(uuid4())
    refined = client.post(
        f"/operator/experiments/{experiment_id}/refine",
        json={"idempotency_key": run_id},
        headers=ORIGIN,
    )
    assert refined.status_code == 200
    accepted = client.post(
        f"/operator/experiments/{experiment_id}/accept",
        json={
            "run_id": run_id,
            "command_key": str(uuid4()),
            "intent_relationship": "PRESERVES_CORE_INTENT",
            "intent_confirmed": True,
            "intent_rationale": "The recorded proposal preserves the supplied idea.",
        },
        headers=ORIGIN,
    ).json()
    repo = ProductRecordsRepository(engine)
    cycle_id = UUID(created["cycle_id"])
    async with engine.connect() as connection:
        workflow = (
            (
                await connection.execute(
                    select(records.workflows).where(
                        records.workflows.c.experiment_id == experiment_id
                    )
                )
            )
            .mappings()
            .one()
        )
        agent = (
            (
                await connection.execute(
                    select(records.agents).where(
                        records.agents.c.workflow_id == workflow["id"]
                    )
                )
            )
            .mappings()
            .one()
        )
    async with engine.connect() as connection:
        prior = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id
                        == UUID(accepted["idea_brief_artifact_id"])
                    )
                )
            )
            .mappings()
            .one()
        )

    def record_input(row, role):
        return ArtifactInput(
            artifact_id=row["id"],
            kind=ArtifactKind(row["kind"]),
            version=row["version"],
            content_hash=row["content_hash"],
            role=role,
        )

    async def put(kind, payload, inputs=()):
        return await repo.append_artifact(
            ArtifactDraft(
                id=uuid4(),
                logical_id=uuid4(),
                version=1,
                experiment_id=experiment_id,
                workflow_id=workflow["id"],
                agent_id=agent["id"],
                kind=kind,
                payload=payload,
                created_by=operator_id,
                created_at=datetime.now(UTC),
            ),
            inputs=inputs,
            command_key=uuid4(),
        )

    idea_input = record_input(prior, "ACCEPTED_IDEA")
    plan = await put(
        ArtifactKind.RESEARCH_PLAN,
        {
            "questions": ["Which buyer signal is missing?"],
            "method": "Recorded fixture review",
        },
        (idea_input,),
    )
    attempt = await repo.start_market_research(
        experiment_id,
        cycle_id,
        accepted_idea=idea_input,
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    report = await put(
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {
            "finding": "Buyer budget signal not established",
            "limitations": ["Recorded fixture"],
        },
        (ArtifactInput.from_receipt(plan, role="PLAN"),),
    )
    recommendation = await put(
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {"recommendation": "REFINE_SAME_IDEA", "rationale": "Clarify buyer evidence"},
        (ArtifactInput.from_receipt(report, role="REPORT"),),
    )
    verdict = await repo.commit_verdict(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict="REFINE_SAME_IDEA",
        committed_by=operator_id,
        command_key=uuid4(),
    )
    feedback = await put(
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        {
            "preserve": ["Original buyer"],
            "change": ["Clarify budget"],
            "failed_dimensions": ["BUYER_BUDGET"],
            "research_questions": ["Which buyer validates a range?"],
        },
        (
            idea_input,
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
    )
    validation = await put(
        ArtifactKind.VALIDATION_RESULT,
        {
            "validator": "fixture",
            "disposition": "PASS",
            "reason": "Exact outcome feedback",
        },
        (ArtifactInput.from_receipt(feedback, role="TARGET"),),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(feedback, role="TARGET"),
        experiment_id=experiment_id,
        disposition="ACCEPTED",
        decided_by=operator_id,
        validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
        command_key=uuid4(),
    )
    return experiment_id, created, accepted, verdict, feedback


async def test_returned_refinement_requires_operator_acceptance_and_versions_brief(
    governance_engine,
):
    app, operator_id = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        (
            experiment_id,
            created,
            accepted,
            verdict,
            feedback,
        ) = await _seeded_return_fixture(client, governance_engine, operator_id)
        available = client.get(f"/operator/experiments/{experiment_id}")
        assert available.status_code == 200, available.text
        assert available.json()["state"] == "RETURN_REVIEW_REQUIRED"
        assert available.json()["return_available"] is not None
        assert available.json()["return_available"]["verdict_id"] == str(verdict.id)
        assert (
            available.json()["return_available"]["research_cycle_id"]
            == created["cycle_id"]
        )
        assert available.json()["return_available"]["feedback"]["artifact_id"] == str(
            feedback.artifact_id
        )
        assert available.json()["return_available"]["return_lineage"] == []
        started = client.post(
            f"/operator/experiments/{experiment_id}/returns/refine",
            json={
                "verdict_id": str(verdict.id),
                "feedback": ArtifactInput.from_receipt(
                    feedback, role="RESEARCH_FEEDBACK"
                ).model_dump(mode="json", exclude={"schema_version"}),
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        )
        assert started.status_code == 200, started.text
        assert started.json()["state"] == "AWAITING_REFINEMENT"
        proposed_run = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": proposed_run},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text
        snapshot = client.get(f"/operator/experiments/{experiment_id}").json()
        assert snapshot["accepted_brief"] is None
        assert (
            snapshot["return_context"]["prior_brief"]["artifact_id"]
            == accepted["idea_brief_artifact_id"]
        )
        accepted_return = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json={
                "run_id": proposed_run,
                "command_key": str(uuid4()),
                "intent_relationship": "CLARIFIES_CORE_INTENT",
                "intent_confirmed": True,
                "intent_rationale": "Feedback narrows the same buyer and problem.",
            },
            headers=ORIGIN,
        )
        assert accepted_return.status_code == 200, accepted_return.text
    async with governance_engine.connect() as connection:
        old = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id
                        == UUID(accepted["idea_brief_artifact_id"])
                    )
                )
            )
            .mappings()
            .one()
        )
        new = (
            (
                await connection.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id
                        == UUID(accepted_return.json()["idea_brief_artifact_id"])
                    )
                )
            )
            .mappings()
            .one()
        )
        seed = await connection.scalar(
            select(records.artifacts.c.id).where(
                records.artifacts.c.experiment_id == experiment_id,
                records.artifacts.c.kind == ArtifactKind.IDEA_SEED,
            )
        )
        return_links = (
            (
                await connection.execute(
                    select(
                        records.artifact_links.c.producer_id,
                        records.artifact_links.c.role,
                    )
                    .where(records.artifact_links.c.consumer_id == new["id"])
                    .order_by(records.artifact_links.c.role)
                )
            )
            .mappings()
            .all()
        )
    assert new["logical_id"] == old["logical_id"]
    assert new["version"] == old["version"] + 1
    assert seed == UUID(created["seed_artifact_id"])
    assert {(row["producer_id"], row["role"]) for row in return_links} == {
        (old["id"], "SUPERSEDES"),
        (feedback.artifact_id, "RESEARCH_FEEDBACK"),
    }


async def test_returned_brief_acceptance_retries_after_persisted_intent_review(
    governance_engine, monkeypatch
):
    app, operator_id = await _app(governance_engine)
    app.state.settings = app.state.settings.model_copy(update={"provider_mode": "fake"})
    original_append = ProductRecordsRepository.append_artifact
    with TestClient(app) as client:
        assert (
            client.post(
                "/auth/login", json={"password": "test-password"}, headers=ORIGIN
            ).status_code
            == 200
        )
        experiment_id, _, _, verdict, feedback = await _seeded_return_fixture(
            client, governance_engine, operator_id
        )
        started = client.post(
            f"/operator/experiments/{experiment_id}/returns/refine",
            json={
                "verdict_id": str(verdict.id),
                "feedback": ArtifactInput.from_receipt(
                    feedback, role="RESEARCH_FEEDBACK"
                ).model_dump(mode="json", exclude={"schema_version"}),
                "command_key": str(uuid4()),
            },
            headers=ORIGIN,
        )
        assert started.status_code == 200, started.text
        proposed_run = str(uuid4())
        refined = client.post(
            f"/operator/experiments/{experiment_id}/refine",
            json={"idempotency_key": proposed_run},
            headers=ORIGIN,
        )
        assert refined.status_code == 200, refined.text

        failed_once = False

        async def fail_first_returned_brief(self, draft, **kwargs):
            nonlocal failed_once
            if (
                draft.kind is ArtifactKind.IDEA_BRIEF
                and draft.version == 2
                and not failed_once
            ):
                failed_once = True
                raise ProductRecordsDenied("INJECTED_APPEND_FAILURE")
            return await original_append(self, draft, **kwargs)

        monkeypatch.setattr(
            ProductRecordsRepository, "append_artifact", fail_first_returned_brief
        )
        acceptance = {
            "run_id": proposed_run,
            "command_key": str(uuid4()),
            "intent_relationship": "CLARIFIES_CORE_INTENT",
            "intent_confirmed": True,
            "intent_rationale": "The same bounded feedback clarifies the brief.",
        }
        first = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json=acceptance,
            headers=ORIGIN,
        )
        assert first.status_code == 409
        assert first.json() == {"detail": "INJECTED_APPEND_FAILURE"}
        retry = client.post(
            f"/operator/experiments/{experiment_id}/accept",
            json=acceptance,
            headers=ORIGIN,
        )
        assert retry.status_code == 200, retry.text
    async with governance_engine.connect() as connection:
        reviews = await connection.scalar(
            select(func.count())
            .select_from(records.idea_intent_reviews)
            .where(records.idea_intent_reviews.c.run_id == UUID(proposed_run))
        )
    assert reviews == 1
