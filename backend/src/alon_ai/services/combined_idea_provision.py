"""Reviewed R01A authority and private, consumer-scoped credential provisioning.

This command never calls providers. It accepts complete reviewed authority rows;
API keys, possession of a price card, and public terms cannot create a grant.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
import termios
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.config import Settings
from alon_ai.db.engine import create_engine
from alon_ai.db.repositories.live_idea_provision import (
    current_operator_status,
    register_authority_rows,
)
from alon_ai.integrations.schemas.provider import (
    Capability,
    ContentField,
    Provider,
    Purpose,
    StrictDTO,
    UsageComponent,
)
from alon_ai.policies.provider_rights import ProviderUsageGrant
from alon_ai.provider_usage.schemas.accounting import (
    AccountingDenied,
    ControlPolicy,
    EvidenceRecord,
    FxVersion,
    PriceVersion,
    Reason,
)
from alon_ai.security.secrets import (
    EncryptedFileSecretStore,
    SecretStore,
    SecretStoreError,
)
from alon_ai.services.combined_idea import CombinedIdeaConfig
from alon_ai.services.live_idea_provision import (
    _fsync_directory,
    _private_data_dir,
    _provision_lock,
    _write_private_new,
)

_CONSUMERS = {
    Provider.OPENAI: "openai-idea",
    Provider.BRAVE: "brave-research",
    Provider.FIRECRAWL: "firecrawl-research",
}


class ReviewedAuthority(StrictDTO):
    policy: ControlPolicy
    grant: ProviderUsageGrant
    prices: tuple[PriceVersion, ...] = Field(min_length=1, max_length=4)
    fx: FxVersion
    evidence: tuple[EvidenceRecord, ...] = Field(min_length=4, max_length=7)


class ReviewedProof(StrictDTO):
    """A locally retained reviewed document, pinned to its actual bytes."""

    evidence_id: UUID
    document: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FirecrawlCommercialApproval(StrictDTO):
    """Operator attestation to express permission in the retained grant document."""

    grant_id: UUID
    evidence_id: UUID
    express_commercial_use_authorized: Literal[True]
    permitted_use: Literal["R01A_COMMERCIAL_MARKET_RESEARCH"]
    reviewed_by: UUID


class ResearchModelUseApproval(StrictDTO):
    """Reviewed permission to send this grant's scoped data to the selected model."""

    grant_id: UUID
    evidence_id: UUID
    outbound_to_openai_authorized: Literal[True]
    permitted_use: Literal["R01A_MODEL_CONSUMPTION"]
    destination_account_handle: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    destination_model_identifier: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    reviewed_by: UUID


class IncludedResearchCreditsApproval(StrictDTO):
    """An evidenced included-credit allowance with all paid overage paths disabled."""

    provider: Literal[Provider.BRAVE, Provider.FIRECRAWL]
    account_handle: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    price_ids: tuple[UUID, ...] = Field(min_length=1, max_length=5)
    pricing_evidence_refs: tuple[UUID, ...] = Field(min_length=1, max_length=5)
    control_evidence_refs: tuple[UUID, ...] = Field(min_length=1, max_length=5)
    included_credit_limit: int = Field(ge=1, le=1_000_000)
    credit_unit: Literal["PROVIDER_CREDIT"]
    included_credits_confirmed: Literal[True]
    pay_as_you_go_enabled: Literal[False]
    automatic_topups_enabled: Literal[False]
    reviewed_by: UUID


class CombinedIdeaSetupManifest(StrictDTO):
    version: Literal[1]
    config: CombinedIdeaConfig
    authorities: tuple[ReviewedAuthority, ...] = Field(min_length=3, max_length=6)
    proofs: tuple[ReviewedProof, ...] = Field(min_length=12, max_length=42)
    firecrawl_commercial_approvals: tuple[FirecrawlCommercialApproval, ...] = Field(
        min_length=1, max_length=4
    )

    research_model_use_approvals: tuple[ResearchModelUseApproval, ...] = Field(
        min_length=2, max_length=5
    )

    included_research_credits: tuple[IncludedResearchCreditsApproval, ...] = Field(
        default=(), max_length=2
    )

    @model_validator(mode="after")
    def exact_authority(self) -> Self:
        config = self.config
        operator = config.model.approved_by
        bindings = config.research_bindings
        capabilities = [a.grant.capability for a in self.authorities]
        expected = {Capability.OPENAI_GENERATE} | {
            b.config.intended_use.capability for b in bindings
        }
        if (
            len(capabilities) != len(set(capabilities))
            or set(capabilities) != expected
            or len(bindings) != len(expected) - 1
            or Capability.FIRECRAWL_MAP in expected
            or Capability.BRAVE_WEB_COVERAGE not in expected
            or not any(
                b.config.intended_use.provider is Provider.FIRECRAWL for b in bindings
            )
            or config.research_policy.approved_by != operator
        ):
            raise ValueError("exact combined provider authority required")
        handles = _handles(config)
        if len(set(handles.values())) != 3:
            raise ValueError("separate provider secret handles required")
        approvals = {a.grant_id: a for a in self.firecrawl_commercial_approvals}
        firecrawl_grants = {
            a.grant.grant_id
            for a in self.authorities
            if a.grant.provider is Provider.FIRECRAWL
        }
        if set(approvals) != firecrawl_grants or len(approvals) != len(
            self.firecrawl_commercial_approvals
        ):
            raise ValueError("exact Firecrawl commercial proof required")
        model_approvals = {a.grant_id: a for a in self.research_model_use_approvals}
        research_grants = {b.grant.grant_id for b in bindings}
        if set(model_approvals) != research_grants or len(model_approvals) != len(
            self.research_model_use_approvals
        ):
            raise ValueError("exact research model-consumption proof required")
        proof_ids = [p.evidence_id for p in self.proofs]
        evidence_ids = [e.id for a in self.authorities for e in a.evidence]
        if (
            len(set(proof_ids)) != len(proof_ids)
            or len(set(evidence_ids)) != len(evidence_ids)
            or set(proof_ids) != set(evidence_ids)
        ):
            raise ValueError("unique complete evidence documents required")
        for authority in self.authorities:
            grant, policy = authority.grant, authority.policy
            binding = next(
                (b for b in bindings if b.grant.capability == grant.capability), None
            )
            use = binding.config.intended_use if binding else config.model.intended_use
            bounds = binding.config.prices if binding else config.model.prices
            fx_id = binding.config.fx_id if binding else config.model.fx_id
            start, end = config.model.effective_at, config.model.expires_at
            if (
                grant.approved_by != operator
                or grant.outbound_use_permitted != (binding is not None)
                or not use.required_fields <= grant.storage_fields
                or policy.capability != grant.capability
                or policy.account_handle != grant.account_handle
                or any(
                    getattr(use, key) != getattr(grant, key)
                    for key in (
                        "provider",
                        "capability",
                        "account_handle",
                        "plan_identifier",
                        "order_form_ref",
                        "terms_version",
                        "purpose",
                    )
                )
                or (binding is not None and binding.grant != grant)
                or any(
                    v.effective_at > start or v.expires_at < end
                    for v in (grant, policy, authority.fx, *authority.prices)
                )
                or authority.fx.id != fx_id
                or authority.fx.currency != "USD"
                or authority.fx.rate != config.model.fx_rate
                or len({p.id for p in authority.prices}) != len(authority.prices)
                or {p.id for p in authority.prices} != {b.price_id for b in bounds}
                or len({p.component for p in authority.prices}) != len(authority.prices)
                or any(
                    p.capability != grant.capability
                    or p.currency != "USD"
                    or (p.unit_price == 0 and binding is None)
                    for p in authority.prices
                )
            ):
                raise ValueError("reviewed authority does not match runtime")
            records = {e.id: e for e in authority.evidence}
            expected_proofs = [
                (policy.evidence_id, "CONTROL"),
                (grant.supporting_evidence_ref, "GRANT"),
                (authority.fx.evidence_id, "FX"),
                *((p.evidence_id, "PRICE") for p in authority.prices),
            ]
            if set(records) != {key for key, _ in expected_proofs} or any(
                key not in records
                or records[key].kind != kind
                or records[key].mode != "TRUSTED_REFERENCE"
                or records[key].registered_by != operator
                or records[key].registered_at > start
                for key, kind in expected_proofs
            ):
                raise ValueError("reviewed authority evidence mismatch")
            if grant.provider is Provider.BRAVE and (
                use.purpose is not Purpose.OFFICIAL_SOURCE_IDENTIFICATION
                or use.required_fields
                or grant.storage_fields
                or grant.retention_seconds is not None
                or grant.retention_rule_id is not None
            ):
                raise ValueError(
                    "Brave permits ephemeral official source identification only"
                )
            if grant.capability is Capability.FIRECRAWL_PAGE_CAPTURE:
                source_fields = {ContentField.URL, ContentField.TEXT}
                if (
                    not source_fields <= use.required_fields
                    or not source_fields <= grant.storage_fields
                    or grant.retention_rule_id is None
                    or grant.retention_seconds is None
                ):
                    raise ValueError("reviewed page URL and text retention required")
            if grant.provider is Provider.FIRECRAWL:
                approval = approvals[grant.grant_id]
                if (
                    approval.evidence_id != grant.supporting_evidence_ref
                    or approval.reviewed_by != operator
                ):
                    raise ValueError("Firecrawl express commercial permission required")
            if binding:
                model_approval = model_approvals[grant.grant_id]
                if (
                    model_approval.evidence_id != grant.supporting_evidence_ref
                    or model_approval.reviewed_by != operator
                    or model_approval.destination_account_handle
                    != config.model.intended_use.account_handle
                    or model_approval.destination_model_identifier
                    != config.model.model_identifier
                ):
                    raise ValueError("reviewed permission for selected model required")
                component = (
                    UsageComponent.CAPTURE_PAGE
                    if grant.capability
                    in {
                        Capability.FIRECRAWL_PAGE_CAPTURE,
                        Capability.FIRECRAWL_JS_RETRIEVAL,
                    }
                    else UsageComponent.REQUEST
                )
                if (
                    len(authority.prices) != 1
                    or authority.prices[0].component is not component
                    or bounds[0].max_quantity != 1
                ):
                    raise ValueError("exact bounded research price required")
            elif any(
                p.model_identifier != config.model.model_identifier
                for p in authority.prices
            ) or not {UsageComponent.INPUT_TOKEN, UsageComponent.OUTPUT_TOKEN} <= {
                p.component for p in authority.prices
            }:
                raise ValueError("exact model token prices required")
        self._validate_included_credits()
        if (
            config.research_policy.effective_at > config.model.effective_at
            or config.research_policy.expires_at < config.model.expires_at
        ):
            raise ValueError("research policy must cover runtime validity")
        return self

    def _validate_included_credits(self) -> None:
        zero_authorities = [
            a for a in self.authorities if any(p.unit_price == 0 for p in a.prices)
        ]
        scopes = {(a.grant.provider, a.grant.account_handle) for a in zero_authorities}
        approvals = {
            (a.provider, a.account_handle): a for a in self.included_research_credits
        }
        if set(approvals) != scopes or len(approvals) != len(
            self.included_research_credits
        ):
            raise ValueError(
                "exact included-credit review required for zero research prices"
            )
        for scope, approval in approvals.items():
            authorities = [
                a
                for a in zero_authorities
                if (a.grant.provider, a.grant.account_handle) == scope
            ]
            prices = [p for a in authorities for p in a.prices]
            expected = (
                (approval.price_ids, {p.id for p in prices}),
                (approval.pricing_evidence_refs, {p.evidence_id for p in prices}),
                (
                    approval.control_evidence_refs,
                    {a.policy.evidence_id for a in authorities},
                ),
            )
            if (
                approval.reviewed_by != self.config.model.approved_by
                or any(
                    len(refs) != len(set(refs)) or set(refs) != required
                    for refs, required in expected
                )
                or any(p.unit_price != 0 or p.unit_quantity != 1 for p in prices)
            ):
                raise ValueError(
                    "included-credit evidence must match exact prices and controls"
                )
            credit_bound = 0
            for authority in authorities:
                binding = next(
                    b
                    for b in self.config.research_bindings
                    if b.grant.grant_id == authority.grant.grant_id
                )
                policy = authority.policy
                # The ledger counts dispatches in windows anchored at effective_at.
                # Never permit that quota to reset during this free-credit approval.
                if (
                    policy.effective_at + timedelta(seconds=policy.window_seconds)
                    < self.config.model.expires_at
                ):
                    raise ValueError(
                        "included-credit quota window must cover full approval"
                    )
                credit_bound += policy.quota_limit * int(
                    binding.config.prices[0].max_quantity
                )
            if credit_bound > approval.included_credit_limit:
                raise ValueError("dispatch quotas exceed reviewed included credits")


def _handles(config: CombinedIdeaConfig) -> dict[str, str]:
    handles = {"openai-idea": config.model.secret_handle}
    for binding in config.research_bindings:
        consumer = _CONSUMERS[binding.config.intended_use.provider]
        handle = binding.config.secret_handle
        if handle is None or (consumer in handles and handles[consumer] != handle):
            raise ValueError("one scoped handle per provider required")
        handles[consumer] = handle
    if set(handles) != set(_CONSUMERS.values()):
        raise ValueError("three providers required")
    return handles


def _read_private(path: Path, limit: int = 1_048_576) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
            or info.st_size > limit
        ):
            raise ValueError("owner-private regular file required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("private file limit exceeded")
        return data
    finally:
        os.close(fd)


class CombinedSecretStore:
    """Composition-only router; hand individual consumers their scoped store."""

    def __init__(self, stores: dict[str, SecretStore], handles: dict[str, str]):
        self._stores, self._handles = stores, handles

    def for_consumer(self, consumer: str) -> SecretStore:
        try:
            return self._stores[consumer]
        except KeyError:
            raise SecretStoreError("Secret access failed") from None

    def research_store(self) -> CombinedSecretStore:
        names = {"brave-research", "firecrawl-research"}
        return CombinedSecretStore(
            {k: v for k, v in self._stores.items() if k in names},
            {k: v for k, v in self._handles.items() if k in names},
        )

    def get(self, handle: str) -> SecretStr:
        for consumer, permitted in self._handles.items():
            if handle == permitted:
                return self._stores[consumer].get(handle)
        raise SecretStoreError("Secret access failed")


def load_combined_secret_store(
    directory: Path, config: CombinedIdeaConfig
) -> CombinedSecretStore:
    try:
        handles = _handles(config)
        stores: dict[str, SecretStore] = {}
        for consumer, handle in handles.items():
            key = _read_private(directory / consumer / "live-secret.key", 32)
            if len(key) != 32:
                raise ValueError("invalid key")
            stores[consumer] = EncryptedFileSecretStore(
                directory / consumer / "secrets",
                consumer=consumer,
                allowed_handles={handle},
                keys={"v1": key},
                active_key_version="v1",
            )
        return CombinedSecretStore(stores, handles)
    except Exception:  # noqa: BLE001 - redact credentials and private filesystem details
        raise AccountingDenied(Reason.SECRET) from None


def read_api_key(consumer: str) -> SecretStr:
    try:
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        with os.fdopen(fd, "w") as terminal:
            termios.tcgetattr(terminal.fileno())
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                value = getpass.getpass(f"API key for {consumer}: ", stream=terminal)
        if not value:
            raise ValueError("empty credential")
        return SecretStr(value)
    except (OSError, ValueError, termios.error, getpass.GetPassWarning):
        raise RuntimeError("Private terminal required for provider key") from None


async def provision_from_manifest(
    manifest_path: Path, data_dir: Path, engine: AsyncEngine
) -> Path:
    manifest = CombinedIdeaSetupManifest.model_validate_json(
        _read_private(manifest_path)
    )
    for proof in manifest.proofs:
        if (
            hashlib.sha256(
                _read_private(manifest_path.parent / proof.document, 10_000_000)
            ).hexdigest()
            != proof.sha256
        ):
            raise ValueError("reviewed evidence document changed")
    config = manifest.config

    async def require_operator() -> None:
        if (
            not config.model.effective_at <= datetime.now(UTC) < config.model.expires_at
            or await current_operator_status(engine, config.model.approved_by)
            != "ACTIVE"
        ):
            raise RuntimeError("Current active operator approval required")

    _private_data_dir(data_dir)
    with _provision_lock(data_dir):
        await require_operator()
        final_dir = data_dir / "combined-live"
        config_path = final_dir / "combined-idea.json"
        if final_dir.exists() or final_dir.is_symlink():
            _private_data_dir(final_dir)
            if (
                _read_private(final_dir / "reviewed-manifest.json")
                != manifest.model_dump_json().encode()
                or CombinedIdeaConfig.model_validate_json(_read_private(config_path))
                != config
            ):
                raise RuntimeError(
                    "Published authority differs; reviewed rotation required"
                )
            store = load_combined_secret_store(final_dir, config)
            for handle in _handles(config).values():
                store.get(handle)
            for authority in manifest.authorities:
                await register_authority_rows(engine, authority)
            return config_path
        stage = Path(tempfile.mkdtemp(prefix=".combined-stage-", dir=data_dir))
        try:
            for consumer, handle in _handles(config).items():
                private = stage / consumer
                _private_data_dir(private)
                value = read_api_key(consumer)
                key = secrets.token_bytes(32)
                _write_private_new(private / "live-secret.key", key)
                store = EncryptedFileSecretStore(
                    private / "secrets",
                    consumer=consumer,
                    allowed_handles={handle},
                    keys={"v1": key},
                    active_key_version="v1",
                )
                store.put(handle, value)
                del value
                _fsync_directory(private)
            # Each bundle is immutable and exact-replayable. A later failure leaves
            # registered rows but no published executable combined configuration.
            for authority in manifest.authorities:
                await register_authority_rows(engine, authority)
            await require_operator()
            _write_private_new(
                stage / "reviewed-manifest.json", manifest.model_dump_json().encode()
            )
            _write_private_new(
                stage / "combined-idea.json", config.model_dump_json().encode()
            )
            _fsync_directory(stage)
            os.rename(stage, final_dir)
            _fsync_directory(data_dir)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return config_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision reviewed combined Idea authority"
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--print-schema", action="store_true")
    args = parser.parse_args()
    if args.print_schema:
        print(json.dumps(CombinedIdeaSetupManifest.model_json_schema(), indent=2))
        return
    if args.manifest is None or args.data_dir is None:
        parser.error("--manifest and --data-dir are required for provisioning")

    async def run() -> None:
        engine = create_engine(Settings())
        try:
            await provision_from_manifest(args.manifest, args.data_dir, engine)
        finally:
            await engine.dispose()

    try:
        asyncio.run(run())
    except Exception:  # noqa: BLE001 - never print private paths, input, or credentials
        print(
            "Combined provisioning failed; review private authority and evidence",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print(
        "Combined authority and three encrypted credentials provisioned; no provider calls made"
    )


if __name__ == "__main__":
    main()
