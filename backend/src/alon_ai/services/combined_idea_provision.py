"""Reviewed R01A authority and private, consumer-scoped credential provisioning.

This command never calls providers. It accepts complete reviewed authority rows;
API keys, possession of a price card, and public terms cannot create a grant.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, SecretStr, model_validator
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.config import Settings
from alon_ai.db.engine import create_engine
from alon_ai.db.repositories.live_idea_provision import (
    active_operator_for_subject,
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
_API_KEY_CONSUMERS = {
    "OPENAI_API_KEY": "openai-idea",
    "BRAVE_API_KEY": "brave-research",
    "FIRECRAWL_API_KEY": "firecrawl-research",
}
BOOTSTRAP_OPERATOR_ID = UUID("00000000-0000-4000-8000-00000000f00d")
_OPERATOR_REFERENCE_KEYS = frozenset(
    {"approved_by", "registered_by", "reviewed_by", "attested_by"}
)


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
    """Operator attestation to express Firecrawl authorization for commercial use."""

    grant_id: UUID
    evidence_id: UUID
    express_commercial_use_authorized: Literal[True]
    permitted_use: Literal["R01A_COMMERCIAL_MARKET_RESEARCH"]
    reviewed_by: UUID


class FirecrawlPersonalUseApproval(StrictDTO):
    """Operator attestation that this Firecrawl use is personal and noncommercial."""

    grant_id: UUID
    evidence_id: UUID
    operator_attested_personal_noncommercial_test: Literal[True]
    permitted_use: Literal["R01A_PERSONAL_NONCOMMERCIAL_TEST"]
    attested_by: UUID
    attested_at: AwareDatetime


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
        default=(), max_length=4
    )
    firecrawl_personal_use_approvals: tuple[FirecrawlPersonalUseApproval, ...] = Field(
        default=(), max_length=4
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
        commercial_approvals = {
            a.grant_id: a for a in self.firecrawl_commercial_approvals
        }
        personal_approvals = {
            a.grant_id: a for a in self.firecrawl_personal_use_approvals
        }
        firecrawl_grants = {
            a.grant.grant_id: a.grant
            for a in self.authorities
            if a.grant.provider is Provider.FIRECRAWL
        }
        commercial_grants = {
            grant_id
            for grant_id, grant in firecrawl_grants.items()
            if grant.purpose is Purpose.RESEARCH
        }
        personal_grants = {
            grant_id
            for grant_id, grant in firecrawl_grants.items()
            if grant.purpose is Purpose.R01A_PERSONAL_NONCOMMERCIAL_TEST
        }
        if (
            set(commercial_approvals) != commercial_grants
            or set(personal_approvals) != personal_grants
            or set(commercial_approvals) & set(personal_approvals)
            or len(commercial_approvals) != len(self.firecrawl_commercial_approvals)
            or len(personal_approvals) != len(self.firecrawl_personal_use_approvals)
        ):
            raise ValueError("exact Firecrawl use approval required")
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
                if grant.purpose is Purpose.RESEARCH:
                    approval = commercial_approvals[grant.grant_id]
                    if (
                        approval.evidence_id != grant.supporting_evidence_ref
                        or approval.reviewed_by != operator
                    ):
                        raise ValueError(
                            "Firecrawl express commercial permission required"
                        )
                elif grant.purpose is Purpose.R01A_PERSONAL_NONCOMMERCIAL_TEST:
                    approval = personal_approvals[grant.grant_id]
                    if (
                        approval.evidence_id != grant.supporting_evidence_ref
                        or approval.attested_by != operator
                        or approval.attested_at > start
                    ):
                        raise ValueError("Firecrawl personal-use approval mismatch")
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


def load_combined_idea_runtime_config(config_path: Path) -> CombinedIdeaConfig:
    """Bind personal Firecrawl rights only from this bundle's reviewed attestation."""
    try:
        config = CombinedIdeaConfig.model_validate_json(_read_private(config_path))
        manifest = CombinedIdeaSetupManifest.model_validate_json(
            _read_private(config_path.parent / "reviewed-manifest.json")
        )
        if manifest.config != config:
            raise ValueError("reviewed config mismatch")
        approvals = {
            approval.grant_id: approval
            for approval in manifest.firecrawl_personal_use_approvals
        }
        bindings = []
        personal_grants = set()
        for binding in config.research_bindings:
            use = binding.config.intended_use
            if use.purpose is not Purpose.R01A_PERSONAL_NONCOMMERCIAL_TEST:
                if binding.grant.grant_id in approvals:
                    raise ValueError("unexpected personal Firecrawl approval")
                bindings.append(binding)
                continue
            grant = binding.grant
            personal_grants.add(grant.grant_id)
            approval = approvals.get(grant.grant_id)
            if (
                use.provider is not Provider.FIRECRAWL
                or use.capability is not Capability.FIRECRAWL_PAGE_CAPTURE
                or approval is None
                or approval.evidence_id != grant.supporting_evidence_ref
                or approval.attested_by != config.model.approved_by
            ):
                raise ValueError("personal Firecrawl approval mismatch")
            scoped_use = use.model_copy(
                update={"personal_noncommercial_approval_ref": approval.evidence_id}
            )
            scoped_config = binding.config.model_copy(
                update={"intended_use": scoped_use}
            )
            bindings.append(binding.model_copy(update={"config": scoped_config}))
        if personal_grants != set(approvals):
            raise ValueError("personal Firecrawl approval set mismatch")
        return config.model_copy(update={"research_bindings": tuple(bindings)})
    except Exception:  # noqa: BLE001 - redact private paths and evidence details
        raise ValueError("reviewed local combined runtime scope required") from None


def read_api_keys_file(path: Path) -> dict[str, SecretStr]:
    """Read exactly three credentials from a private dotenv-style file, never source it."""
    try:
        contents = _read_private(path, 16_384).decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        raise ValueError("owner-private provider key file required") from None

    values: dict[str, SecretStr] = {}
    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if (
            not separator
            or name not in _API_KEY_CONSUMERS
            or name in values
            or not value
            or value != value.strip()
            or not value.isprintable()
            or any(character.isspace() for character in value)
            or value[0] in "'\""
        ):
            raise ValueError("invalid provider key file")
        values[name] = SecretStr(value)
    if set(values) != set(_API_KEY_CONSUMERS):
        raise ValueError("provider key file must contain all three provider keys")
    return {_API_KEY_CONSUMERS[name]: value for name, value in values.items()}


async def configured_active_operator_id(
    engine: AsyncEngine, auth_subject: str | None
) -> UUID | None:
    if not auth_subject:
        return None
    return await active_operator_for_subject(engine, auth_subject)


def _contains_bootstrap_operator(value: object) -> bool:
    marker = str(BOOTSTRAP_OPERATOR_ID)
    if isinstance(value, dict):
        return any(_contains_bootstrap_operator(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_bootstrap_operator(child) for child in value)
    return value == marker


def _validate_bootstrap_operator_markers(raw: dict) -> None:
    marker = str(BOOTSTRAP_OPERATOR_ID)

    def visit(value: object, key: str | None = None) -> None:
        if isinstance(value, dict):
            for name, child in value.items():
                visit(child, name)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif value == marker and key not in _OPERATOR_REFERENCE_KEYS:
            raise ValueError("invalid local operator marker placement")
        elif key in _OPERATOR_REFERENCE_KEYS and value != marker:
            raise ValueError(
                "local operator marker must cover every approval reference"
            )

    visit(raw)


def _resolve_bootstrap_operator(raw: dict, operator_id: UUID) -> dict:
    marker = str(BOOTSTRAP_OPERATOR_ID)
    _validate_bootstrap_operator_markers(raw)

    def replace(value: object, key: str | None = None) -> object:
        if isinstance(value, dict):
            return {name: replace(child, name) for name, child in value.items()}
        if isinstance(value, list):
            return [replace(child, key) for child in value]
        if value == marker:
            if key not in _OPERATOR_REFERENCE_KEYS:
                raise ValueError("invalid local operator marker placement")
            return str(operator_id)
        if key in _OPERATOR_REFERENCE_KEYS:
            raise ValueError(
                "local operator marker must cover every approval reference"
            )
        return value

    resolved = replace(raw)
    if not isinstance(resolved, dict):
        raise TypeError("invalid local operator manifest")
    return resolved


async def provision_from_manifest(
    manifest_path: Path, data_dir: Path, engine: AsyncEngine, keys_file: Path
) -> Path:
    raw_manifest = json.loads(_read_private(manifest_path))
    if _contains_bootstrap_operator(raw_manifest):
        _validate_bootstrap_operator_markers(raw_manifest)
        operator_id = await configured_active_operator_id(
            engine, Settings().operator_auth_subject
        )
        if operator_id is None:
            raise RuntimeError("Current active operator approval required")
        raw_manifest = _resolve_bootstrap_operator(raw_manifest, operator_id)
    manifest = CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw_manifest))
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

    await require_operator()
    credentials = read_api_keys_file(keys_file)
    _private_data_dir(data_dir)
    with _provision_lock(data_dir):
        await require_operator()
        final_dir = data_dir / "combined-live"
        config_path = final_dir / "combined-idea.json"
        if final_dir.exists() or final_dir.is_symlink():
            _private_data_dir(final_dir)
            if (
                CombinedIdeaSetupManifest.model_validate_json(
                    _read_private(final_dir / "reviewed-manifest.json")
                )
                != manifest
                or CombinedIdeaConfig.model_validate_json(_read_private(config_path))
                != config
            ):
                raise RuntimeError(
                    "Published authority differs; reviewed rotation required"
                )
            store = load_combined_secret_store(final_dir, config)
            for consumer, handle in _handles(config).items():
                if (
                    store.for_consumer(consumer).get(handle).get_secret_value()
                    != credentials[consumer].get_secret_value()
                ):
                    raise RuntimeError(
                        "Published credentials differ; reviewed rotation required"
                    )
            for authority in manifest.authorities:
                await register_authority_rows(engine, authority)
            return config_path
        stage = Path(tempfile.mkdtemp(prefix=".combined-stage-", dir=data_dir))
        try:
            for consumer, handle in _handles(config).items():
                private = stage / consumer
                _private_data_dir(private)
                value = credentials[consumer]
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
    parser.add_argument("--keys-file", type=Path)
    parser.add_argument("--print-schema", action="store_true")
    args = parser.parse_args()
    if args.print_schema:
        print(json.dumps(CombinedIdeaSetupManifest.model_json_schema(), indent=2))
        return
    if args.manifest is None or args.data_dir is None or args.keys_file is None:
        parser.error(
            "--manifest, --data-dir, and --keys-file are required for provisioning"
        )

    async def run() -> None:
        engine = create_engine(Settings())
        try:
            await provision_from_manifest(
                args.manifest, args.data_dir, engine, args.keys_file
            )
        finally:
            await engine.dispose()

    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 - never print private paths or values
        category = (
            "reviewed authority or configuration"
            if isinstance(exc, (ValueError, TypeError))
            else "private file access"
            if isinstance(exc, (OSError, UnicodeDecodeError))
            else "operator or published authority state"
            if isinstance(exc, RuntimeError)
            else "provider accounting authority"
            if isinstance(exc, AccountingDenied)
            else "unexpected internal failure"
        )
        print(
            f"Combined provisioning failed ({category}); review private authority and evidence",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print(
        "Combined authority and three encrypted credentials provisioned; no provider calls made"
    )


if __name__ == "__main__":
    main()
