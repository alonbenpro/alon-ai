"""One-time, explicit operator setup for a live Idea Responses capability.

Run inside the API container as its normal UID. The manifest contains reviewed
authority and prices; the API key is entered separately without terminal echo.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import getpass
import json
import os
import secrets as random_secrets
import shutil
import stat
import sys
import tempfile
import termios
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, Self
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import AwareDatetime, Field, SecretStr, model_validator
from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

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
from alon_ai.accounting.repository import safe_errors
from alon_ai.api.live_idea_runtime import (
    LiveIdeaRuntimeConfig,
    load_live_idea_runtime_config,
    load_live_secret_store,
)
from alon_ai.config import Settings
from alon_ai.db.engine import create_engine
from alon_ai.openai_runtime.contract import canonical_json
from alon_ai.providers.contracts import (
    Capability,
    ContentField,
    Provider,
    Purpose,
    StrictDTO,
    UsageComponent,
)
from alon_ai.providers.rights import IntendedUse, ProviderUsageGrant
from alon_ai.records.operators import operators
from alon_ai.security.secrets import EncryptedFileSecretStore


class LivePriceSpec(StrictDTO):
    component: UsageComponent
    unit_price: Decimal = Field(ge=0, allow_inf_nan=False)
    max_quantity: Decimal = Field(gt=0, allow_inf_nan=False)


class LiveIdeaSetupManifest(StrictDTO):
    """Exact reviewed inputs. No API key field is accepted."""

    operator_id: UUID
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    account_handle: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    plan_identifier: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    order_form_ref: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    terms_version: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    rights_reference: str = Field(min_length=1, max_length=500)
    pricing_reference: str = Field(min_length=1, max_length=500)
    fx_reference: str = Field(min_length=1, max_length=500)
    control_reference: str = Field(min_length=1, max_length=500)
    model_identifier: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"]
    max_output_tokens: int = Field(ge=1, le=32768)
    timeout_seconds: int = Field(ge=1, le=3600)
    budget_cap_usd: Decimal = Field(gt=0, allow_inf_nan=False)
    secret_handle: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    fx_rate: Decimal = Field(gt=0, allow_inf_nan=False)
    retention_seconds: int = Field(ge=1, le=315360000)
    quota_limit: int = Field(ge=1)
    window_seconds: int = Field(ge=1, le=31536000)
    concurrency_limit: int = Field(ge=1, le=1000)
    failure_threshold: int = Field(ge=1, le=1000)
    failure_window_seconds: int = Field(ge=1, le=86400)
    cooldown_seconds: int = Field(ge=1, le=86400)
    prices: tuple[LivePriceSpec, ...] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def exact_bounds(self) -> Self:
        components = [price.component for price in self.prices]
        if (
            self.effective_at >= self.expires_at
            or not {UsageComponent.INPUT_TOKEN, UsageComponent.OUTPUT_TOKEN}
            <= set(components)
            or len(components) != len(set(components))
            or any(
                component
                not in {
                    UsageComponent.REQUEST,
                    UsageComponent.INPUT_TOKEN,
                    UsageComponent.OUTPUT_TOKEN,
                    UsageComponent.CACHED_TOKEN,
                }
                for component in components
            )
            or any(
                price.component is UsageComponent.OUTPUT_TOKEN
                and price.max_quantity < self.max_output_tokens
                for price in self.prices
            )
            or any(
                price.component is not UsageComponent.REQUEST and price.unit_price <= 0
                for price in self.prices
            )
        ):
            raise ValueError("invalid reviewed live Idea limits")
        return self


@dataclass(frozen=True)
class LiveAuthorityBundle:
    config: LiveIdeaRuntimeConfig
    policy: ControlPolicy
    grant: ProviderUsageGrant
    prices: tuple[PriceVersion, ...]
    fx: FxVersion
    evidence: tuple[EvidenceRecord, ...]


def make_authority_bundle(manifest: LiveIdeaSetupManifest) -> LiveAuthorityBundle:
    """Build immutable, uniquely identified versions from reviewed manifest facts."""

    fingerprint = canonical_json(manifest.model_dump(mode="json"))

    def identity(label: str) -> UUID:
        return uuid5(NAMESPACE_URL, f"alon-ai-l07-live-authority/{fingerprint}/{label}")

    evidence: list[EvidenceRecord] = []

    def proof(label: str, kind: Literal["CONTROL", "GRANT", "PRICE", "FX"]) -> UUID:
        reference = {
            "CONTROL": manifest.control_reference,
            "GRANT": manifest.rights_reference,
            "PRICE": manifest.pricing_reference,
            "FX": manifest.fx_reference,
        }[kind]
        evidence_id = identity(f"proof/{label}/{reference}")
        evidence.append(
            EvidenceRecord(
                id=evidence_id,
                kind=kind,
                mode="TRUSTED_REFERENCE",
                registered_by=manifest.operator_id,
                registered_at=manifest.effective_at,
            )
        )
        return evidence_id

    use = IntendedUse(
        provider=Provider.OPENAI,
        account_handle=manifest.account_handle,
        capability=Capability.OPENAI_GENERATE,
        plan_identifier=manifest.plan_identifier,
        order_form_ref=manifest.order_form_ref,
        terms_version=manifest.terms_version,
        purpose=Purpose.GENERATION,
        required_fields=frozenset({ContentField.TEXT}),
    )
    policy = ControlPolicy(
        id=identity("policy"),
        effective_at=manifest.effective_at,
        expires_at=manifest.expires_at,
        evidence_id=proof("policy", "CONTROL"),
        capability=Capability.OPENAI_GENERATE,
        account_handle=manifest.account_handle,
        timeout_seconds=manifest.timeout_seconds,
        quota_limit=manifest.quota_limit,
        window_seconds=manifest.window_seconds,
        concurrency_limit=manifest.concurrency_limit,
        failure_threshold=manifest.failure_threshold,
        failure_window_seconds=manifest.failure_window_seconds,
        cooldown_seconds=manifest.cooldown_seconds,
    )
    grant = ProviderUsageGrant(
        grant_id=identity("grant"),
        version=1,
        **use.model_dump(exclude={"schema_version", "required_fields"}),
        outbound_use_permitted=False,
        storage_fields=frozenset({ContentField.TEXT}),
        retention_rule_id=identity("retention"),
        retention_seconds=manifest.retention_seconds,
        approved_by=manifest.operator_id,
        approved_at=manifest.effective_at,
        effective_at=manifest.effective_at,
        expires_at=manifest.expires_at,
        supporting_evidence_ref=proof("grant", "GRANT"),
    )
    prices = tuple(
        PriceVersion(
            id=identity(f"price/{spec.component.value}"),
            effective_at=manifest.effective_at,
            expires_at=manifest.expires_at,
            evidence_id=proof(f"price/{spec.component.value}", "PRICE"),
            model_identifier=manifest.model_identifier,
            capability=Capability.OPENAI_GENERATE,
            component=spec.component,
            currency="USD",
            unit_price=spec.unit_price,
            unit_quantity=Decimal(1),
            currency_quantum=Decimal("0.01"),
        )
        for spec in manifest.prices
    )
    fx = FxVersion(
        id=identity("fx"),
        effective_at=manifest.effective_at,
        expires_at=manifest.expires_at,
        evidence_id=proof("fx", "FX"),
        currency="USD",
        rate=manifest.fx_rate,
    )
    config = LiveIdeaRuntimeConfig(
        approved_by=manifest.operator_id,
        effective_at=manifest.effective_at,
        expires_at=manifest.expires_at,
        intended_use=use,
        prices=tuple(
            PriceBound(price_id=price.id, max_quantity=spec.max_quantity)
            for price, spec in zip(prices, manifest.prices, strict=True)
        ),
        fx_id=fx.id,
        fx_rate=manifest.fx_rate,
        secret_handle=manifest.secret_handle,
        model_identifier=manifest.model_identifier,
        reasoning_effort=manifest.reasoning_effort,
        max_output_tokens=manifest.max_output_tokens,
        timeout_seconds=manifest.timeout_seconds,
        budget_cap_usd=manifest.budget_cap_usd,
    )
    return LiveAuthorityBundle(config, policy, grant, prices, fx, tuple(evidence))


@safe_errors
async def register_authority(engine: AsyncEngine, bundle: LiveAuthorityBundle) -> None:
    """Register the same L03 authority rows in one all-or-nothing transaction."""

    policy = bundle.policy
    grant = bundle.grant
    async with engine.begin() as connection:
        existing_authority = (
            (
                await connection.execute(
                    select(gov.authorities)
                    .where(
                        gov.authorities.c.account == policy.account_handle,
                        gov.authorities.c.capability == policy.capability,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if existing_authority is not None:

            async def exact(table, key, expected) -> bool:
                row = (
                    (await connection.execute(select(table).where(table.c.id == key)))
                    .mappings()
                    .one_or_none()
                )
                return row is not None and all(
                    row[field] == value for field, value in expected.items()
                )

            matches = (
                existing_authority["enabled"] is True
                and existing_authority["policy_id"] == policy.id
                and await exact(
                    gov.policies,
                    policy.id,
                    {
                        "account": policy.account_handle,
                        "capability": policy.capability,
                        "data": policy.model_dump(mode="json"),
                        "evidence_id": policy.evidence_id,
                    },
                )
                and await exact(
                    gov.grants,
                    grant.grant_id,
                    {
                        "version": grant.version,
                        "account": grant.account_handle,
                        "capability": grant.capability,
                        "effective_at": grant.effective_at,
                        "expires_at": grant.expires_at,
                        "data": grant.model_dump(mode="json"),
                        "evidence_id": grant.supporting_evidence_ref,
                    },
                )
                and all(
                    [
                        await exact(
                            gov.evidence,
                            proof.id,
                            proof.model_dump(exclude={"schema_version"}),
                        )
                        for proof in bundle.evidence
                    ]
                )
                and all(
                    [
                        await exact(
                            gov.prices,
                            price.id,
                            price.model_dump(exclude={"schema_version"}),
                        )
                        for price in bundle.prices
                    ]
                )
                and await exact(
                    gov.fx,
                    bundle.fx.id,
                    bundle.fx.model_dump(exclude={"schema_version"}),
                )
                and (
                    await connection.scalar(
                        select(gov.grant_events.c.id).where(
                            gov.grant_events.c.grant_id == grant.grant_id,
                            gov.grant_events.c.grant_version == grant.version,
                        )
                    )
                )
                is None
            )
            if not matches:
                raise AccountingDenied(Reason.CONFIG)
            return
        for proof in bundle.evidence:
            await connection.execute(
                insert(gov.evidence).values(
                    **proof.model_dump(exclude={"schema_version"})
                )
            )
        inserted = await connection.execute(
            pg_insert(gov.authorities)
            .values(account=policy.account_handle, capability=policy.capability)
            .on_conflict_do_nothing()
            .returning(gov.authorities.c.account)
        )
        if inserted.scalar_one_or_none() is None:
            raise AccountingDenied(Reason.CONFIG)
        await connection.execute(
            insert(gov.policies).values(
                id=policy.id,
                account=policy.account_handle,
                capability=policy.capability,
                data=policy.model_dump(mode="json"),
                evidence_id=policy.evidence_id,
            )
        )
        await connection.execute(
            update(gov.authorities)
            .where(
                gov.authorities.c.account == policy.account_handle,
                gov.authorities.c.capability == policy.capability,
            )
            .values(policy_id=policy.id)
        )
        await connection.execute(
            insert(gov.grants).values(
                id=grant.grant_id,
                version=grant.version,
                account=grant.account_handle,
                capability=grant.capability,
                effective_at=grant.effective_at,
                expires_at=grant.expires_at,
                data=grant.model_dump(mode="json"),
                evidence_id=grant.supporting_evidence_ref,
            )
        )
        for price in bundle.prices:
            await connection.execute(
                insert(gov.prices).values(
                    **price.model_dump(exclude={"schema_version"})
                )
            )
        await connection.execute(
            insert(gov.fx).values(**bundle.fx.model_dump(exclude={"schema_version"}))
        )


async def _require_current_operator(
    engine: AsyncEngine, manifest: LiveIdeaSetupManifest
) -> None:
    now = datetime.now(UTC)
    if not manifest.effective_at <= now < manifest.expires_at:
        raise RuntimeError("Live authority period is not current")
    async with engine.connect() as connection:
        status = await connection.scalar(
            select(operators.c.status).where(operators.c.id == manifest.operator_id)
        )
    if status != "ACTIVE":
        raise RuntimeError("Approved operator is not active")


def read_live_api_key() -> SecretStr:
    """Require an actual terminal; getpass must never fall back to echoed input."""

    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        with os.fdopen(fd, "w") as terminal:
            termios.tcgetattr(terminal.fileno())
            value = getpass.getpass(
                "OpenAI API key for the approved handle: ", stream=terminal
            )
        if not value:
            raise ValueError("empty key")
        return SecretStr(value)
    except (OSError, ValueError, termios.error):
        raise RuntimeError("Private terminal required for OpenAI key") from None


def _write_private_new(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def _private_data_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise RuntimeError("Live provision data directory unavailable")


@contextmanager
def _provision_lock(data_dir: Path) -> Iterator[None]:
    lock_path = data_dir / ".live-provision.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise RuntimeError("Live provision lock unavailable")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_stale_stages(data_dir: Path) -> None:
    for stage in data_dir.glob(".live-stage-*"):
        info = stage.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise RuntimeError("Live provision staging directory unavailable")
        shutil.rmtree(stage)


def _verify_published(final_dir: Path, bundle: LiveAuthorityBundle) -> None:
    info = final_dir.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise RuntimeError("Published live configuration unavailable")
    try:
        loaded = load_live_idea_runtime_config(final_dir / "live-idea.json")
        if loaded != bundle.config:
            raise RuntimeError("Published live configuration differs from manifest")
        load_live_secret_store(final_dir, allowed_handle=loaded.secret_handle).get(
            loaded.secret_handle
        )
    except Exception:  # noqa: BLE001 - never print private file or key details
        raise RuntimeError(
            "Published live configuration is incomplete or altered"
        ) from None


async def provision_from_manifest(
    manifest_path: Path, data_dir: Path, engine: AsyncEngine
) -> None:
    """Create encrypted credentials and authority; publish config last."""

    raw = manifest_path.read_text(encoding="utf-8")
    manifest = LiveIdeaSetupManifest.model_validate_json(raw)
    bundle = make_authority_bundle(manifest)
    _private_data_dir(data_dir)
    with _provision_lock(data_dir):
        _remove_stale_stages(data_dir)
        final_dir = data_dir / "live"
        if final_dir.exists() or final_dir.is_symlink():
            _verify_published(final_dir, bundle)
            await _require_current_operator(engine, manifest)
            await register_authority(engine, bundle)
            return
        if any(
            (data_dir / name).exists()
            for name in ("live-idea.json", "live-secret.key", "secrets")
        ):
            raise RuntimeError("Legacy live configuration requires manual review")
        await _require_current_operator(engine, manifest)
        key_value = read_live_api_key()
        # DB registration is atomic. A crash before publication leaves at most
        # a private staging directory; exact DB replay is safe on the next run.
        await register_authority(engine, bundle)
        stage = Path(tempfile.mkdtemp(prefix=".live-stage-", dir=data_dir))
        try:
            key = random_secrets.token_bytes(32)
            _write_private_new(stage / "live-secret.key", key)
            store = EncryptedFileSecretStore(
                stage / "secrets",
                consumer="openai-idea",
                allowed_handles={manifest.secret_handle},
                keys={"v1": key},
                active_key_version="v1",
            )
            store.put(manifest.secret_handle, key_value)
            del key_value
            await _require_current_operator(engine, manifest)
            _write_private_new(
                stage / "live-idea.json",
                json.dumps(
                    bundle.config.model_dump(mode="json"), separators=(",", ":")
                ).encode(),
            )
            _fsync_directory(stage)
            os.rename(stage, final_dir)
            _fsync_directory(data_dir)
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision reviewed live Idea authority"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()

    async def run() -> None:
        engine = create_engine(Settings())
        try:
            await provision_from_manifest(args.manifest, args.data_dir, engine)
        finally:
            await engine.dispose()

    try:
        asyncio.run(run())
    except Exception:  # noqa: BLE001 - do not print key, paths, or provider errors
        print(
            "Live Idea provisioning failed; configuration remains unavailable",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print("Live Idea authority and encrypted credential provisioned")


if __name__ == "__main__":
    main()
