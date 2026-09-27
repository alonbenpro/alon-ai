"""Live composition tests use an inert transport; no paid API call is made."""

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select, text, update

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import (
    AccountingDenied,
    ControlPolicy,
    EvidenceRecord,
    FxVersion,
    PriceBound,
    PriceVersion,
    Reason,
)
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.api.live_idea_provision import (
    LiveIdeaSetupManifest,
    LivePriceSpec,
    make_authority_bundle,
    provision_from_manifest,
    register_authority,
)
from alon_ai.api.live_idea_runtime import (
    LiveIdeaRuntimeConfig,
    build_live_idea_runtime_provider,
    load_live_idea_runtime_config,
    load_live_secret_store,
)
from alon_ai.openai_runtime.idea import IdeaStage
from alon_ai.providers.contracts import (
    Capability,
    ContentField,
    Provider,
    Purpose,
    SafeRequestMetadata,
    UsageComponent,
)
from alon_ai.providers.rights import IntendedUse
from alon_ai.records.operators import operators
from alon_ai.security.secrets import SecretStoreError


class RecordingTransport:
    calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        raise AssertionError("No live request is permitted in this test")


class DeniedSecrets:
    def get(self, handle: str):
        raise SecretStoreError("Secret access failed")


def config(*, operator_id: UUID) -> LiveIdeaRuntimeConfig:
    now = datetime.now(UTC)
    return LiveIdeaRuntimeConfig(
        approved_by=operator_id,
        effective_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        intended_use=IntendedUse(
            provider=Provider.OPENAI,
            account_handle="approved_openai_account",
            capability=Capability.OPENAI_GENERATE,
            plan_identifier="approved.plan",
            order_form_ref="approved.order",
            terms_version="approved.terms",
            purpose=Purpose.GENERATION,
            required_fields=frozenset({ContentField.TEXT}),
        ),
        prices=(
            PriceBound(price_id=uuid4(), max_quantity=Decimal(10000)),
            PriceBound(price_id=uuid4(), max_quantity=Decimal(300)),
        ),
        fx_id=uuid4(),
        fx_rate=Decimal("3.5"),
        secret_handle="approved-openai-key",
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
        timeout_seconds=30,
        budget_cap_usd=Decimal("1.00"),
    )


@pytest.mark.integration
async def test_missing_secret_denies_before_governance_or_transport(governance_engine):
    operator_id = uuid4()
    transport = RecordingTransport()
    provider = build_live_idea_runtime_provider(
        config(operator_id=operator_id), DeniedSecrets(), transport=transport
    )
    with pytest.raises(AccountingDenied) as denied:
        await provider(
            governance_engine,
            experiment_id=uuid4(),
            workflow_id=uuid4(),
            agent_id=uuid4(),
            operator_id=operator_id,
            run_id=uuid4(),
            budget_usd=Decimal("0.50"),
        )
    assert denied.value.reason is Reason.SECRET
    assert transport.calls == 0


@pytest.mark.integration
async def test_live_composition_selects_injected_transport_but_no_paid_call(
    governance_engine,
):
    from pydantic import SecretStr

    class AvailableSecrets:
        def get(self, handle: str) -> SecretStr:
            assert handle == "approved-openai-key"
            return SecretStr("test-only")

    operator_id = uuid4()
    transport = RecordingTransport()
    reviewed = config(operator_id=operator_id)
    now = datetime.now(UTC)
    provisioner = GovernanceProvisioner(governance_engine)
    for index, component in enumerate(
        (UsageComponent.INPUT_TOKEN, UsageComponent.OUTPUT_TOKEN)
    ):
        proof_id = uuid4()
        await provisioner.evidence(
            EvidenceRecord(
                id=proof_id,
                kind="PRICE",
                mode="SYNTHETIC",
                registered_by=operator_id,
                registered_at=now,
            )
        )
        await provisioner.price(
            PriceVersion(
                id=reviewed.prices[index].price_id,
                effective_at=reviewed.effective_at,
                expires_at=reviewed.expires_at,
                evidence_id=proof_id,
                model_identifier=reviewed.model_identifier,
                capability=Capability.OPENAI_GENERATE,
                component=component,
                currency="USD",
                unit_price=Decimal("0.000001"),
                unit_quantity=Decimal(1),
                currency_quantum=Decimal("0.01"),
            )
        )
    fx_proof = uuid4()
    await provisioner.evidence(
        EvidenceRecord(
            id=fx_proof,
            kind="FX",
            mode="SYNTHETIC",
            registered_by=operator_id,
            registered_at=now,
        )
    )
    await provisioner.fx(
        FxVersion(
            id=reviewed.fx_id,
            effective_at=reviewed.effective_at,
            expires_at=reviewed.expires_at,
            evidence_id=fx_proof,
            currency="USD",
            rate=reviewed.fx_rate,
        )
    )
    control_proof = uuid4()
    await provisioner.evidence(
        EvidenceRecord(
            id=control_proof,
            kind="CONTROL",
            mode="SYNTHETIC",
            registered_by=operator_id,
            registered_at=now,
        )
    )
    await provisioner.policy(
        ControlPolicy(
            id=uuid4(),
            effective_at=reviewed.effective_at,
            expires_at=reviewed.expires_at,
            evidence_id=control_proof,
            capability=Capability.OPENAI_GENERATE,
            account_handle=reviewed.intended_use.account_handle,
            timeout_seconds=30,
            quota_limit=10,
            window_seconds=3600,
            concurrency_limit=1,
            failure_threshold=2,
            failure_window_seconds=3600,
            cooldown_seconds=60,
        )
    )
    provider = build_live_idea_runtime_provider(
        reviewed, AvailableSecrets(), transport=transport
    )
    experiment_id = uuid4()
    workflow_id = uuid4()
    agent_id = uuid4()
    run_id = uuid4()
    runtime, attribution, source = await provider(
        governance_engine,
        experiment_id=experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        operator_id=operator_id,
        run_id=run_id,
        budget_usd=Decimal("0.50"),
    )
    replay_runtime, replay_attribution, replay_source = await provider(
        governance_engine,
        experiment_id=experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        operator_id=operator_id,
        run_id=run_id,
        budget_usd=Decimal("0.50"),
    )
    assert replay_attribution.operation_run_id == attribution.operation_run_id
    assert replay_runtime.runtimes[IdeaStage.USER_SEEDED_REFINEMENT].routes.cheap == (
        runtime.runtimes[IdeaStage.USER_SEEDED_REFINEMENT].routes.cheap
    )
    assert replay_source == "OPENAI"
    with pytest.raises(AccountingDenied) as changed_budget:
        await provider(
            governance_engine,
            experiment_id=experiment_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            operator_id=operator_id,
            run_id=run_id,
            budget_usd=Decimal("0.40"),
        )
    assert changed_budget.value.reason is Reason.BUDGET
    assert source == "OPENAI"
    assert attribution.config_version is not None
    assert all(item.transport is transport for item in runtime.runtimes.values())
    assert set(runtime.runtimes) == set(IdeaStage)
    assert transport.calls == 0
    with pytest.raises(AccountingDenied) as denied:
        await runtime.runtimes[IdeaStage.USER_SEEDED_REFINEMENT].repository.reserve(
            attribution,
            SafeRequestMetadata(
                config_ref=runtime.runtimes[
                    IdeaStage.USER_SEEDED_REFINEMENT
                ].routes.cheap
            ),
            idempotency_key=uuid4(),
        )
    assert denied.value.reason is Reason.RIGHTS
    async with governance_engine.connect() as connection:
        count = await connection.scalar(select(func.count()).select_from(gov.calls))
    assert count == 0
    assert transport.calls == 0


def test_live_config_loader_requires_private_file_and_rejects_raw_key(tmp_path):
    config_file = tmp_path / "live.json"
    payload = config(operator_id=uuid4()).model_dump(mode="json")
    config_file.write_text(json.dumps(payload))
    os.chmod(config_file, 0o600)
    assert load_live_idea_runtime_config(config_file).model_dump(mode="json") == payload

    payload["openai_api_key"] = "must-not-be-stored-here"
    config_file.write_text(json.dumps(payload))
    with pytest.raises(AccountingDenied) as denied:
        load_live_idea_runtime_config(config_file)
    assert denied.value.reason is Reason.CONFIG

    del payload["openai_api_key"]
    config_file.write_text(json.dumps(payload))
    os.chmod(config_file, 0o644)
    with pytest.raises(AccountingDenied) as denied:
        load_live_idea_runtime_config(config_file)
    assert denied.value.reason is Reason.CONFIG


def test_live_secret_store_loader_reads_only_private_key_file(tmp_path):
    from pydantic import SecretStr

    from alon_ai.security.secrets import EncryptedFileSecretStore

    key_file = tmp_path / "live-secret.key"
    key_file.write_bytes(b"k" * 32)
    os.chmod(key_file, 0o600)
    source = EncryptedFileSecretStore(
        tmp_path / "secrets",
        consumer="openai-idea",
        allowed_handles={"approved-openai-key"},
        keys={"v1": b"k" * 32},
        active_key_version="v1",
    )
    source.put("approved-openai-key", SecretStr("test-only"))
    loaded = load_live_secret_store(tmp_path, allowed_handle="approved-openai-key")
    assert loaded.get("approved-openai-key").get_secret_value() == "test-only"

    os.chmod(key_file, 0o644)
    with pytest.raises(AccountingDenied) as denied:
        load_live_secret_store(tmp_path, allowed_handle="approved-openai-key")
    assert denied.value.reason is Reason.SECRET


@pytest.mark.integration
async def test_unapproved_operator_or_budget_denies_before_transport(governance_engine):
    from pydantic import SecretStr

    class AvailableSecrets:
        def get(self, handle: str) -> SecretStr:
            return SecretStr("test-only")

    operator_id = uuid4()
    transport = RecordingTransport()
    provider = build_live_idea_runtime_provider(
        config(operator_id=operator_id), AvailableSecrets(), transport=transport
    )
    for actor, budget, expected in (
        (uuid4(), Decimal("0.50"), Reason.CONFIG),
        (operator_id, Decimal("1.01"), Reason.BUDGET),
    ):
        with pytest.raises(AccountingDenied) as denied:
            await provider(
                governance_engine,
                experiment_id=uuid4(),
                workflow_id=uuid4(),
                agent_id=uuid4(),
                operator_id=actor,
                run_id=uuid4(),
                budget_usd=budget,
            )
        assert denied.value.reason is expected
    assert transport.calls == 0


def reviewed_manifest(operator_id: UUID, now: datetime) -> LiveIdeaSetupManifest:
    return LiveIdeaSetupManifest(
        operator_id=operator_id,
        effective_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        account_handle="test_approved_openai",
        plan_identifier="reviewed.plan",
        order_form_ref="reviewed.order",
        terms_version="reviewed.terms",
        rights_reference="reviewed-test-rights",
        pricing_reference="reviewed-test-prices",
        fx_reference="reviewed-test-fx",
        control_reference="reviewed-test-controls",
        model_identifier="gpt-5-mini",
        reasoning_effort="low",
        max_output_tokens=300,
        timeout_seconds=30,
        budget_cap_usd=Decimal("1.00"),
        secret_handle="test-openai-key",
        fx_rate=Decimal("3.5"),
        retention_seconds=60,
        quota_limit=10,
        window_seconds=3600,
        concurrency_limit=1,
        failure_threshold=2,
        failure_window_seconds=3600,
        cooldown_seconds=60,
        prices=(
            LivePriceSpec(
                component=UsageComponent.INPUT_TOKEN,
                unit_price=Decimal("0.000001"),
                max_quantity=Decimal(10000),
            ),
            LivePriceSpec(
                component=UsageComponent.OUTPUT_TOKEN,
                unit_price=Decimal("0.000002"),
                max_quantity=Decimal(300),
            ),
        ),
    )


@pytest.mark.integration
async def test_reviewed_manifest_provisions_private_store_and_governed_authority(
    governance_engine, tmp_path, monkeypatch
):
    from pydantic import SecretStr

    from alon_ai.api import live_idea_provision as setup

    now = datetime.now(UTC)
    operator_id = uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(operators).values(
                id=operator_id,
                auth_subject="local-operator@alon.ai",
                display_name="Local Operator",
                timezone="Asia/Jerusalem",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
    manifest = reviewed_manifest(operator_id, now)
    manifest_path = tmp_path / "reviewed-manifest.json"
    manifest_path.write_text(manifest.model_dump_json())
    private_dir = tmp_path / "private"
    abandoned_stage = private_dir / ".live-stage-abandoned"
    abandoned_stage.mkdir(parents=True, mode=0o700)
    os.chmod(private_dir, 0o700)
    (abandoned_stage / "partial.key").write_text("orphaned test data")
    os.chmod(abandoned_stage / "partial.key", 0o600)
    monkeypatch.setattr(setup, "read_live_api_key", lambda: SecretStr("test-only"))
    await provision_from_manifest(manifest_path, private_dir, governance_engine)
    assert not abandoned_stage.exists()
    assert not list(private_dir.glob(".live-stage-*"))
    final_dir = private_dir / "live"
    loaded = load_live_idea_runtime_config(final_dir / "live-idea.json")
    assert loaded.approved_by == operator_id
    assert (
        load_live_secret_store(final_dir, allowed_handle=loaded.secret_handle)
        .get(loaded.secret_handle)
        .get_secret_value()
        == "test-only"
    )

    def forbidden_prompt():
        raise AssertionError("no key prompt on exact replay")

    monkeypatch.setattr(setup, "read_live_api_key", forbidden_prompt)
    await provision_from_manifest(manifest_path, private_dir, governance_engine)


@pytest.mark.integration
async def test_authority_registration_rolls_back_if_fx_insert_fails(governance_engine):
    bundle = make_authority_bundle(reviewed_manifest(uuid4(), datetime.now(UTC)))
    async with governance_engine.begin() as connection:
        await connection.execute(
            text(
                "CREATE FUNCTION reject_live_fx() RETURNS trigger AS $$ "
                "BEGIN RAISE EXCEPTION 'test rejection'; END $$ LANGUAGE plpgsql"
            )
        )
        await connection.execute(
            text(
                "CREATE TRIGGER reject_live_fx BEFORE INSERT ON gov_fx "
                "FOR EACH ROW EXECUTE FUNCTION reject_live_fx()"
            )
        )
    with pytest.raises(AccountingDenied) as denied:
        await register_authority(governance_engine, bundle)
    assert denied.value.reason is Reason.STATE
    async with governance_engine.connect() as connection:
        for table in (
            gov.evidence,
            gov.authorities,
            gov.policies,
            gov.grants,
            gov.prices,
            gov.fx,
        ):
            assert await connection.scalar(select(func.count()).select_from(table)) == 0


@pytest.mark.integration
async def test_config_write_failure_can_retry_exact_authority(
    governance_engine, tmp_path, monkeypatch
):
    from pydantic import SecretStr

    from alon_ai.api import live_idea_provision as setup

    now = datetime.now(UTC)
    operator_id = uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(operators).values(
                id=operator_id,
                auth_subject="retry-operator@alon.ai",
                display_name="Retry Operator",
                timezone="Asia/Jerusalem",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
    manifest = reviewed_manifest(operator_id, now)
    manifest_path = tmp_path / "reviewed-manifest.json"
    manifest_path.write_text(manifest.model_dump_json())
    data_dir = tmp_path / "private"
    monkeypatch.setattr(setup, "read_live_api_key", lambda: SecretStr("test-only"))
    original_write = setup._write_private_new
    failed = False

    def fail_config_once(path, data):
        nonlocal failed
        if path.name == "live-idea.json" and not failed:
            failed = True
            raise OSError("simulated file publication failure")
        return original_write(path, data)

    monkeypatch.setattr(setup, "_write_private_new", fail_config_once)
    with pytest.raises(OSError):
        await provision_from_manifest(manifest_path, data_dir, governance_engine)
    assert not (data_dir / "live").exists()
    await provision_from_manifest(manifest_path, data_dir, governance_engine)
    loaded = load_live_idea_runtime_config(data_dir / "live" / "live-idea.json")
    assert loaded.approved_by == operator_id
    config_file = data_dir / "live" / "live-idea.json"
    valid_content = config_file.read_text()
    altered = json.loads(valid_content)
    altered["model_identifier"] = "gpt-5"
    config_file.write_text(json.dumps(altered))
    with pytest.raises(RuntimeError):
        await provision_from_manifest(manifest_path, data_dir, governance_engine)
    assert json.loads(config_file.read_text()) == altered
    config_file.write_text(valid_content)
    async with governance_engine.begin() as connection:
        await connection.execute(
            update(gov.authorities)
            .where(
                gov.authorities.c.account == manifest.account_handle,
                gov.authorities.c.capability == Capability.OPENAI_GENERATE,
            )
            .values(enabled=False)
        )
    with pytest.raises(AccountingDenied) as changed_authority:
        await register_authority(governance_engine, make_authority_bundle(manifest))
    assert changed_authority.value.reason is Reason.CONFIG
