"""Reviewed provisioning denies absent proof and never dispatches a provider."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.integrations.live_research import (
    ResearchCapabilityBinding,
    ResearchRunPolicy,
)
from alon_ai.integrations.schemas.provider import (
    Capability,
    ContentField,
    Provider,
    Purpose,
    UsageComponent,
)
from alon_ai.policies.provider_rights import IntendedUse, ProviderUsageGrant
from alon_ai.provider_usage.live_idea import CombinedModelLimits
from alon_ai.provider_usage.schemas.accounting import (
    CapabilityConfig,
    ControlPolicy,
    EvidenceRecord,
    FxVersion,
    PriceBound,
    PriceVersion,
)
from alon_ai.security.secrets import SecretStoreError
from alon_ai.services import combined_idea_provision as setup
from alon_ai.services.combined_idea import CombinedIdeaConfig
from alon_ai.services.live_idea_provision import (
    LiveIdeaSetupManifest,
    LivePriceSpec,
    make_authority_bundle,
)


def reviewed(tmp_path):
    now, operator = datetime.now(UTC), uuid4()
    start, end = now - timedelta(minutes=1), now + timedelta(days=1)
    model = make_authority_bundle(
        LiveIdeaSetupManifest(
            operator_id=operator,
            effective_at=start,
            expires_at=end,
            account_handle="openai-account",
            plan_identifier="plan",
            order_form_ref="order",
            terms_version="terms",
            rights_reference="rights",
            pricing_reference="price",
            fx_reference="fx",
            control_reference="controls",
            model_identifier="reviewed-model",
            reasoning_effort="low",
            max_output_tokens=300,
            timeout_seconds=30,
            budget_cap_usd=Decimal(1),
            secret_handle="openai-key",
            fx_rate=Decimal("3.5"),
            retention_seconds=60,
            quota_limit=10,
            window_seconds=3600,
            concurrency_limit=1,
            failure_threshold=2,
            failure_window_seconds=60,
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
    )
    authorities = [
        setup.ReviewedAuthority(
            policy=model.policy,
            grant=model.grant,
            prices=model.prices,
            fx=model.fx,
            evidence=model.evidence,
        )
    ]
    bindings, approvals = [], []
    for provider, capability, purpose, fields in (
        (
            Provider.BRAVE,
            Capability.BRAVE_WEB_COVERAGE,
            Purpose.OFFICIAL_SOURCE_IDENTIFICATION,
            frozenset(),
        ),
        (
            Provider.FIRECRAWL,
            Capability.FIRECRAWL_PAGE_CAPTURE,
            Purpose.RESEARCH,
            frozenset({ContentField.URL, ContentField.TEXT}),
        ),
    ):
        use = IntendedUse(
            provider=provider,
            capability=capability,
            purpose=purpose,
            required_fields=fields,
            account_handle=provider.value.lower(),
            plan_identifier="reviewed",
            order_form_ref="reviewed",
            terms_version="reviewed",
        )
        evidence = tuple(
            EvidenceRecord(
                id=uuid4(),
                kind=kind,
                mode="TRUSTED_REFERENCE",
                registered_by=operator,
                registered_at=start,
            )
            for kind in ("CONTROL", "GRANT", "PRICE", "FX")
        )
        grant = ProviderUsageGrant(
            grant_id=uuid4(),
            version=1,
            **use.model_dump(exclude={"schema_version", "required_fields"}),
            outbound_use_permitted=True,
            storage_fields=fields,
            retention_rule_id=uuid4() if fields else None,
            retention_seconds=60 if fields else None,
            approved_by=operator,
            approved_at=start,
            effective_at=start,
            expires_at=end,
            supporting_evidence_ref=evidence[1].id,
        )
        policy = ControlPolicy(
            **{
                **model.policy.model_dump(),
                "id": uuid4(),
                "capability": capability,
                "account_handle": use.account_handle,
                "evidence_id": evidence[0].id,
            }
        )
        price = PriceVersion(
            id=uuid4(),
            effective_at=start,
            expires_at=end,
            evidence_id=evidence[2].id,
            capability=capability,
            component=UsageComponent.CAPTURE_PAGE if fields else UsageComponent.REQUEST,
            currency="USD",
            unit_price=Decimal("0.01"),
            unit_quantity=Decimal(1),
            currency_quantum=Decimal("0.01"),
        )
        fx = FxVersion(
            id=uuid4(),
            effective_at=start,
            expires_at=end,
            evidence_id=evidence[3].id,
            currency="USD",
            rate=Decimal("3.5"),
        )
        binding = ResearchCapabilityBinding(
            grant=grant,
            config=CapabilityConfig(
                id=uuid4(),
                version=uuid4(),
                workflow_id=uuid4(),
                intended_use=use,
                prices=(PriceBound(price_id=price.id, max_quantity=Decimal(1)),),
                fx_id=fx.id,
                requested_count=1,
                secret_handle=provider.value.lower() + "-key",
                adapter_version=uuid4(),
            ),
        )
        authorities.append(
            setup.ReviewedAuthority(
                policy=policy, grant=grant, prices=(price,), fx=fx, evidence=evidence
            )
        )
        bindings.append(binding)
        if fields:
            approvals.append(
                setup.FirecrawlCommercialApproval(
                    grant_id=grant.grant_id,
                    evidence_id=evidence[1].id,
                    express_commercial_use_authorized=True,
                    permitted_use="R01A_COMMERCIAL_MARKET_RESEARCH",
                    reviewed_by=operator,
                )
            )
    proofs = []
    for authority in authorities:
        for proof in authority.evidence:
            name = f"{proof.id}.txt"
            data = b"Synthetic unit-test evidence, never production authorization."
            path = tmp_path / name
            path.write_bytes(data)
            path.chmod(0o600)
            proofs.append(
                setup.ReviewedProof(
                    evidence_id=proof.id,
                    document=name,
                    sha256=hashlib.sha256(data).hexdigest(),
                )
            )
    config = CombinedIdeaConfig(
        version=1,
        model=model.config,
        limits=CombinedModelLimits(
            model_request_limit=2,
            input_tokens_limit=20000,
            output_tokens_limit=600,
            total_tokens_limit=20600,
            run_timeout_seconds=120,
        ),
        research_policy=ResearchRunPolicy(
            approved_by=operator,
            effective_at=start,
            expires_at=end,
            max_calls=2,
            max_pages=2,
            timeout_seconds=60,
            max_spend_usd=Decimal("0.1"),
            max_results=2,
            max_pdf_bytes=10000,
            max_pdf_pages=2,
            max_text_chars=1000,
            pdf_cpu_seconds=1,
            pdf_memory_bytes=67108864,
            pdf_wall_seconds=2,
        ),
        research_bindings=tuple(bindings),
    )
    manifest = setup.CombinedIdeaSetupManifest(
        version=1,
        config=config,
        authorities=tuple(authorities),
        proofs=tuple(proofs),
        firecrawl_commercial_approvals=tuple(approvals),
        research_model_use_approvals=tuple(
            setup.ResearchModelUseApproval(
                grant_id=b.grant.grant_id,
                evidence_id=b.grant.supporting_evidence_ref,
                outbound_to_openai_authorized=True,
                permitted_use="R01A_MODEL_CONSUMPTION",
                destination_account_handle=model.config.intended_use.account_handle,
                destination_model_identifier=model.config.model_identifier,
                reviewed_by=operator,
            )
            for b in bindings
        ),
    )
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json())
    path.chmod(0o600)
    return manifest, path


def test_requires_explicit_commercial_permission_and_complete_proof(tmp_path):
    manifest, _ = reviewed(tmp_path)
    for patch in ({"firecrawl_commercial_approvals": []}, {"proofs": []}):
        with pytest.raises(ValidationError):
            setup.CombinedIdeaSetupManifest.model_validate(
                {**manifest.model_dump(), **patch}
            )
    raw = manifest.model_dump(mode="json")
    raw["firecrawl_commercial_approvals"][0]["express_commercial_use_authorized"] = (
        False
    )
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(
            __import__("json").dumps(raw)
        )


def test_brave_retention_and_scope_mismatches_denied(tmp_path):
    manifest, _ = reviewed(tmp_path)
    raw = manifest.model_dump(mode="json")
    raw["config"]["research_bindings"][0]["config"]["intended_use"]["purpose"] = (
        "RESEARCH"
    )
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(
            __import__("json").dumps(raw)
        )
    raw = manifest.model_dump(mode="json")
    raw["authorities"][1]["policy"]["account_handle"] = "wrong"
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(
            __import__("json").dumps(raw)
        )


@pytest.mark.asyncio
async def test_publish_three_scoped_envelopes_and_exact_replay(tmp_path, monkeypatch):
    manifest, path = reviewed(tmp_path)
    registered, prompts = [], []

    async def active(*_):
        return "ACTIVE"

    async def register(_, authority):
        registered.append(authority)

    def prompt(consumer):
        prompts.append(consumer)
        return SecretStr("secret-" + consumer)

    monkeypatch.setattr(setup, "current_operator_status", active)
    monkeypatch.setattr(setup, "register_authority_rows", register)
    monkeypatch.setattr(setup, "read_api_key", prompt)
    engine = cast(AsyncEngine, object())
    directory = tmp_path / "private"
    output = await setup.provision_from_manifest(path, directory, engine)
    assert output.is_file() and len(registered) == 3 and len(prompts) == 3
    store = setup.load_combined_secret_store(output.parent, manifest.config)
    assert (
        store.for_consumer("openai-idea").get("openai-key").get_secret_value()
        == "secret-openai-idea"
    )
    with pytest.raises(SecretStoreError):
        store.for_consumer("openai-idea").get("brave-key")
    with pytest.raises(SecretStoreError):
        store.research_store().get("openai-key")
    for file in directory.rglob("*"):
        if file.is_file():
            assert b"secret-openai-idea" not in file.read_bytes()
    assert await setup.provision_from_manifest(path, directory, engine) == output
    assert len(prompts) == 3 and len(registered) == 6


@pytest.mark.asyncio
async def test_registration_failure_never_publishes_config(tmp_path, monkeypatch):
    _, path = reviewed(tmp_path)

    async def active(*_):
        return "ACTIVE"

    async def fail(*_):
        raise RuntimeError("registration failed")

    monkeypatch.setattr(setup, "current_operator_status", active)
    monkeypatch.setattr(setup, "register_authority_rows", fail)
    monkeypatch.setattr(setup, "read_api_key", lambda _: SecretStr("synthetic"))
    with pytest.raises(RuntimeError):
        await setup.provision_from_manifest(
            path, tmp_path / "private", cast(AsyncEngine, object())
        )
    assert not (tmp_path / "private" / "combined-live").exists()
    assert not tuple((tmp_path / "private").glob(".combined-stage-*"))


@pytest.mark.asyncio
async def test_evidence_tampering_and_public_manifest_fail_before_prompt(
    tmp_path, monkeypatch
):
    manifest, path = reviewed(tmp_path)

    def forbidden(_):
        pytest.fail("must reject before requesting a credential")

    monkeypatch.setattr(setup, "read_api_key", forbidden)
    path.chmod(0o644)
    with pytest.raises(ValueError):
        await setup.provision_from_manifest(
            path, tmp_path / "private", cast(AsyncEngine, object())
        )
    path.chmod(0o600)
    (tmp_path / manifest.proofs[0].document).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="changed"):
        await setup.provision_from_manifest(
            path, tmp_path / "private", cast(AsyncEngine, object())
        )


def test_private_reader_rejects_symlinks_and_hardlinks(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"test")
    source.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(OSError):
        setup._read_private(link)
    link.unlink()
    os.link(source, link)
    with pytest.raises(ValueError):
        setup._read_private(link)


def test_key_prompt_cannot_fallback_to_echo(monkeypatch):
    monkeypatch.setattr(setup.os, "open", lambda *_: (_ for _ in ()).throw(OSError()))
    with pytest.raises(RuntimeError, match="Private terminal"):
        setup.read_api_key("openai-idea")


def test_map_unavailable_even_with_reviewed_result_limit_price_bound(tmp_path):
    import json

    manifest, _ = reviewed(tmp_path)
    raw = manifest.model_dump(mode="json")
    authority, binding = raw["authorities"][2], raw["config"]["research_bindings"][1]
    authority["grant"]["capability"] = "FIRECRAWL_MAP"
    authority["policy"]["capability"] = "FIRECRAWL_MAP"
    authority["prices"][0]["capability"] = "FIRECRAWL_MAP"
    authority["prices"][0]["component"] = "REQUEST"
    binding["grant"]["capability"] = "FIRECRAWL_MAP"
    binding["config"]["intended_use"]["capability"] = "FIRECRAWL_MAP"
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
    binding["config"]["prices"][0]["max_quantity"] = str(
        raw["config"]["research_policy"]["max_results"]
    )
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def test_model_use_requires_explicit_reviewed_exact_destination(tmp_path):
    import json

    manifest, _ = reviewed(tmp_path)
    assert not manifest.authorities[0].grant.outbound_use_permitted
    assert all(
        b.grant.outbound_use_permitted for b in manifest.config.research_bindings
    )
    assert not manifest.config.research_bindings[0].grant.storage_fields
    for index in range(2):
        raw = manifest.model_dump(mode="json")
        raw["authorities"][index + 1]["grant"]["outbound_use_permitted"] = False
        raw["config"]["research_bindings"][index]["grant"]["outbound_use_permitted"] = (
            False
        )
        with pytest.raises(ValidationError):
            setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
        for key, value in (
            ("outbound_to_openai_authorized", False),
            ("destination_account_handle", "another-account"),
            ("destination_model_identifier", "another-model"),
            ("evidence_id", str(uuid4())),
            ("reviewed_by", str(uuid4())),
        ):
            raw = manifest.model_dump(mode="json")
            raw["research_model_use_approvals"][index][key] = value
            with pytest.raises(ValidationError):
                setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
    raw = manifest.model_dump(mode="json")
    del raw["research_model_use_approvals"]
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def test_model_disclosure_approval_does_not_grant_brave_retention(tmp_path):
    import json

    manifest, _ = reviewed(tmp_path)
    raw = manifest.model_dump(mode="json")
    for grant in (
        raw["authorities"][1]["grant"],
        raw["config"]["research_bindings"][0]["grant"],
    ):
        grant["storage_fields"] = ["URL"]
        grant["retention_seconds"] = 60
        grant["retention_rule_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
    raw = manifest.model_dump(mode="json")
    raw["authorities"][0]["grant"]["outbound_use_permitted"] = True
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def included_credit_manifest(tmp_path):
    import json

    manifest, _ = reviewed(tmp_path)
    raw = manifest.model_dump(mode="json")
    authority = raw["authorities"][2]
    authority["prices"][0]["unit_price"] = "0"
    authority["policy"]["window_seconds"] = 90000
    raw["included_research_credits"] = [
        {
            "provider": "FIRECRAWL",
            "account_handle": authority["grant"]["account_handle"],
            "price_ids": [authority["prices"][0]["id"]],
            "pricing_evidence_refs": [authority["prices"][0]["evidence_id"]],
            "control_evidence_refs": [authority["policy"]["evidence_id"]],
            "included_credit_limit": authority["policy"]["quota_limit"],
            "credit_unit": "PROVIDER_CREDIT",
            "included_credits_confirmed": True,
            "pay_as_you_go_enabled": False,
            "automatic_topups_enabled": False,
            "reviewed_by": raw["config"]["model"]["approved_by"],
        }
    ]
    return setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def test_reviewed_included_credits_allow_zero_cash_price_with_quantity_bounds(tmp_path):
    manifest = included_credit_manifest(tmp_path)
    assert manifest.authorities[2].prices[0].unit_price == 0
    assert manifest.config.research_bindings[1].config.prices[0].max_quantity == 1
    assert manifest.config.research_policy.max_calls == 2
    assert manifest.config.research_policy.max_pages == 2
    assert manifest.included_research_credits[0].included_credit_limit == 10


@pytest.mark.parametrize(
    "field,value",
    [
        ("pay_as_you_go_enabled", True),
        ("automatic_topups_enabled", True),
        ("included_credits_confirmed", False),
        ("included_credit_limit", 9),
        ("pricing_evidence_refs", []),
        ("control_evidence_refs", []),
        ("reviewed_by", str(uuid4())),
        ("price_ids", [str(uuid4())]),
    ],
)
def test_zero_cash_price_requires_proof_and_disabled_paid_overage(
    tmp_path, field, value
):
    import json

    raw = included_credit_manifest(tmp_path).model_dump(mode="json")
    raw["included_research_credits"][0][field] = value
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def test_free_credit_quota_cannot_reset_or_drop_proof(tmp_path):
    import json

    manifest = included_credit_manifest(tmp_path)
    raw = manifest.model_dump(mode="json")
    raw["authorities"][2]["policy"]["window_seconds"] = 3600
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
    raw = manifest.model_dump(mode="json")
    raw["included_research_credits"] = []
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def test_map_unavailable_even_with_sufficient_reviewed_included_credits(tmp_path):
    import json

    raw = included_credit_manifest(tmp_path).model_dump(mode="json")
    authority, binding = raw["authorities"][2], raw["config"]["research_bindings"][1]
    authority["grant"]["capability"] = "FIRECRAWL_MAP"
    authority["policy"]["capability"] = "FIRECRAWL_MAP"
    authority["prices"][0]["capability"] = "FIRECRAWL_MAP"
    authority["prices"][0]["component"] = "REQUEST"
    binding["grant"]["capability"] = "FIRECRAWL_MAP"
    binding["config"]["intended_use"]["capability"] = "FIRECRAWL_MAP"
    binding["config"]["prices"][0]["max_quantity"] = "2"
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
    raw["included_research_credits"][0]["included_credit_limit"] = 20
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize("missing", ["URL", "TEXT"])
def test_page_capture_requires_reviewed_original_source_fields(tmp_path, missing):
    import json

    manifest, _ = reviewed(tmp_path)
    raw = manifest.model_dump(mode="json")
    binding = raw["config"]["research_bindings"][1]
    binding["config"]["intended_use"]["required_fields"].remove(missing)
    # Even if storage is licensed, omitting the requested field cannot produce
    # the original-source projection needed by the combined research case.
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
    for grant in (binding["grant"], raw["authorities"][2]["grant"]):
        grant["storage_fields"].remove(missing)
    with pytest.raises(ValidationError):
        setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))


def test_page_capture_title_is_optional_and_reviewed_when_requested(tmp_path):
    import json

    manifest, _ = reviewed(tmp_path)
    binding = manifest.config.research_bindings[1]
    assert binding.config.intended_use.required_fields == {
        ContentField.URL,
        ContentField.TEXT,
    }
    raw = manifest.model_dump(mode="json")
    binding = raw["config"]["research_bindings"][1]
    binding["config"]["intended_use"]["required_fields"].append("TITLE")
    for grant in (binding["grant"], raw["authorities"][2]["grant"]):
        grant["storage_fields"].append("TITLE")
    setup.CombinedIdeaSetupManifest.model_validate_json(json.dumps(raw))
