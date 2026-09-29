"""The live setup manifest must be explicit and contains no provider secret."""

import json
import os
import pty
import select
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, cast
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.integrations.schemas.provider import UsageComponent
from alon_ai.provider_usage.live_idea import build_live_idea_runtime_provider
from alon_ai.provider_usage.schemas.accounting import AccountingDenied
from alon_ai.security.secrets import SecretStore
from alon_ai.services import live_idea_provision as provision
from alon_ai.services.live_idea_provision import (
    LiveIdeaSetupManifest,
    LivePriceSpec,
    make_authority_bundle,
)


def sample_manifest(
    *,
    reasoning_effort: Literal[
        "none", "minimal", "low", "medium", "high", "xhigh", "max"
    ] = "low",
    model_identifier="gpt-5-mini",
) -> LiveIdeaSetupManifest:
    now = datetime.now(UTC)
    return LiveIdeaSetupManifest(
        operator_id=uuid4(),
        effective_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(days=1),
        account_handle="approved_openai_account",
        plan_identifier="approved.plan",
        order_form_ref="approved.order",
        terms_version="approved.terms",
        rights_reference="operator-reviewed-openai-terms",
        pricing_reference="operator-reviewed-price-card",
        fx_reference="operator-reviewed-fx-quote",
        control_reference="operator-reviewed-limit-policy",
        model_identifier=model_identifier,
        reasoning_effort=reasoning_effort,
        max_output_tokens=300,
        timeout_seconds=30,
        budget_cap_usd=Decimal("1.00"),
        secret_handle="openai-idea-key",
        fx_rate=Decimal("3.50"),
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


def test_setup_bundle_binds_operator_reviewed_prices_and_rights():
    manifest = sample_manifest()
    bundle = make_authority_bundle(manifest)
    assert bundle.config.approved_by == manifest.operator_id
    assert bundle.config.model_identifier == manifest.model_identifier
    assert bundle.config.secret_handle == manifest.secret_handle
    assert {p.component for p in bundle.prices} == {
        UsageComponent.INPUT_TOKEN,
        UsageComponent.OUTPUT_TOKEN,
    }
    assert all(proof.mode == "TRUSTED_REFERENCE" for proof in bundle.evidence)
    assert bundle.grant.storage_fields


def test_setup_manifest_accepts_gpt_6_luna_at_max_reasoning_effort():
    original = sample_manifest(
        reasoning_effort="low", model_identifier="gpt-6-luna"
    ).model_dump(mode="json")
    assert LiveIdeaSetupManifest.model_validate_json(json.dumps(original))
    raw = dict(original)
    raw["model_identifier"] = "gpt-6-luna"
    raw["reasoning_effort"] = "max"

    manifest = LiveIdeaSetupManifest.model_validate_json(json.dumps(raw))

    assert manifest.model_identifier == "gpt-6-luna"
    assert manifest.reasoning_effort == "max"


def test_legacy_live_provider_rejects_max_effort_before_runtime_creation():
    manifest = sample_manifest(reasoning_effort="max", model_identifier="gpt-6-luna")
    config = make_authority_bundle(manifest).config

    with pytest.raises(AccountingDenied, match="CONFIG"):
        build_live_idea_runtime_provider(config, cast(SecretStore, object()))


def test_key_prompt_refuses_missing_tty_without_echo_fallback(monkeypatch):
    prompted = False

    def forbidden_prompt(*args, **kwargs):
        nonlocal prompted
        prompted = True
        return "unexpected"

    def no_tty(path, flags):
        raise OSError("no tty")

    monkeypatch.setattr(provision.os, "open", no_tty)
    monkeypatch.setattr(provision.getpass, "getpass", forbidden_prompt)
    with pytest.raises(RuntimeError):
        provision.read_live_api_key()
    assert not prompted


def test_key_prompt_reads_real_terminal_without_echo(monkeypatch):
    master, slave = pty.openpty()
    original_open = os.open
    values: list[str] = []
    errors: list[Exception] = []

    def open_test_tty(path, flags, *args, **kwargs):
        if path == "/dev/tty":
            return os.dup(slave)
        return original_open(path, flags, *args, **kwargs)

    def read_key():
        try:
            values.append(provision.read_live_api_key().get_secret_value())
        except Exception as error:  # noqa: BLE001 - capture thread failure for assertion
            errors.append(error)

    monkeypatch.setattr(provision.os, "open", open_test_tty)
    thread = threading.Thread(target=read_key, daemon=True)
    try:
        thread.start()
        ready, _, _ = select.select([master], [], [], 2)
        if ready:
            prompt = os.read(master, 4096)
            assert b"OpenAI API key" in prompt
            os.write(master, b"test-only\n")
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert not errors
        assert values == ["test-only"]
        ready, _, _ = select.select([master], [], [], 0.1)
        output = os.read(master, 4096) if ready else b""
        assert b"test-only" not in output
    finally:
        os.close(master)
        os.close(slave)


async def test_failed_secret_write_removes_new_private_files(tmp_path, monkeypatch):
    manifest = sample_manifest()
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(manifest.model_dump_json())
    data_dir = tmp_path / "data"

    async def active(*args):
        return None

    async def registered(*args):
        return None

    class BrokenStore:
        def __init__(self, *args, **kwargs):
            pass

        def put(self, handle, value):
            raise RuntimeError("simulated secret write failure")

    monkeypatch.setattr(provision, "_require_current_operator", active)
    monkeypatch.setattr(provision, "register_authority", registered)
    monkeypatch.setattr(provision, "read_live_api_key", lambda: SecretStr("test-only"))
    monkeypatch.setattr(provision, "EncryptedFileSecretStore", BrokenStore)
    with pytest.raises(RuntimeError):
        await provision.provision_from_manifest(
            manifest_file, data_dir, cast(AsyncEngine, object())
        )
    assert not (data_dir / "live").exists()
    assert not list(data_dir.glob(".live-stage-*"))


async def test_incomplete_published_directory_refuses_setup_without_key_prompt(
    tmp_path, monkeypatch
):
    manifest = sample_manifest()
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(manifest.model_dump_json())
    data_dir = tmp_path / "data"
    final_dir = data_dir / "live"
    final_dir.mkdir(parents=True, mode=0o700)
    os.chmod(data_dir, 0o700)

    def forbidden_prompt():
        raise AssertionError("key prompt must not run")

    monkeypatch.setattr(provision, "read_live_api_key", forbidden_prompt)
    with pytest.raises(RuntimeError):
        await provision.provision_from_manifest(
            manifest_file, data_dir, cast(AsyncEngine, object())
        )
    assert final_dir.exists()


def test_manifest_rejects_missing_output_price():
    with pytest.raises(ValueError):
        LiveIdeaSetupManifest.model_validate_json(
            '{"operator_id":"00000000-0000-0000-0000-000000000001"}'
        )
