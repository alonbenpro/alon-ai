"""Explicit local recorded transport through the governed L06 IdeaRuntime.

This is available only with provider_mode=fake outside production. It never
opens a network connection or produces real market evidence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting.models import (
    CapabilityConfig,
    ControlPolicy,
    EvidenceRecord,
    FxVersion,
    PriceBound,
    PriceVersion,
)
from alon_ai.accounting.repository import GovernanceProvisioner, GovernanceRepository
from alon_ai.openai_runtime.contract import RoutingPolicy
from alon_ai.openai_runtime.idea import IdeaRuntime, IdeaStage, idea_profile
from alon_ai.openai_runtime.runtime import OpenAIRuntime
from alon_ai.openai_runtime.store import OpenAIRunStore
from alon_ai.providers.contracts import (
    AgentActor,
    CallAttribution,
    Capability,
    ContentField,
    OperationRunKind,
    Provider,
    Purpose,
    UsageComponent,
)
from alon_ai.providers.rights import IntendedUse, ProviderUsageGrant
from alon_ai.records import ProductRecordsRepository


def _id(key: UUID, label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"alon-ai-l07-fake/{key}/{label}")


class _RecordedSecrets:
    def get(self, handle: str) -> SecretStr:
        if handle != "l07-recorded-only":
            raise ValueError("unknown recorded transport handle")
        return SecretStr("recorded-only")


class _RecordedResponses:
    async def create(self, **kwargs: object) -> dict[str, Any]:
        raw = kwargs.get("input_json")
        if not isinstance(raw, str):
            raise TypeError("recorded input missing")
        bound = json.loads(raw)
        artifacts = bound.get("artifacts", [])
        if len(artifacts) != 1 or artifacts[0].get("kind") != "IDEA_SEED":
            raise ValueError("recorded transport requires exact seed")
        statement = artifacts[0]["payload"]["statement"].strip()
        advice = {
            "title": statement[:120],
            "customer": "Customer stated in original seed; verify before research",
            "problem": "Problem stated in original seed; verify before research",
            "core_intent": statement,
            "material_pivot": False,
            "grounding_refs": ["SEED"],
            "uncertainties": [
                "Synthetic recorded advice; customer, problem and demand are unverified"
            ],
        }
        return {
            "id": "resp_l07_recorded",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(advice)}],
                }
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
                "input_tokens_details": {"cached_tokens": 0},
            },
        }


async def provision_recorded_seeded_runtime(
    engine: AsyncEngine,
    *,
    experiment_id: UUID,
    workflow_id: UUID,
    agent_id: UUID,
    operator_id: UUID,
    run_id: UUID,
    budget_usd: Decimal,
) -> tuple[IdeaRuntime, CallAttribution]:
    """Provision synthetic authority/accounting for one local recorded run."""

    now = datetime.now(UTC)
    effective = now - timedelta(minutes=1)
    expiry = now + timedelta(hours=1)
    config_version = _id(run_id, "version")
    attribution = CallAttribution(
        experiment_id=experiment_id,
        workflow_run_id=workflow_id,
        operation_run_id=_id(run_id, "operation"),
        operation_run_kind=OperationRunKind.SYSTEM,
        actor=AgentActor(agent_run_id=agent_id),
        correlation_id=_id(run_id, "correlation"),
        logical_operation_id=_id(run_id, "logical"),
        config_version=config_version,
        deadline=now + timedelta(seconds=60),
    )
    provisioner = GovernanceProvisioner(engine)
    await provisioner.scope(attribution)
    use = IntendedUse(
        provider=Provider.OPENAI,
        account_handle=f"l07-recorded-{run_id.hex[:16]}",
        capability=Capability.OPENAI_GENERATE,
        plan_identifier="recorded.only",
        order_form_ref="recorded.only",
        terms_version="recorded.v1",
        purpose=Purpose.GENERATION,
        required_fields=frozenset({ContentField.TEXT}),
    )

    async def proof(
        label: str, kind: Literal["CONTROL", "GRANT", "PRICE", "FX"]
    ) -> UUID:
        evidence_id = _id(run_id, label)
        await provisioner.evidence(
            EvidenceRecord(
                id=evidence_id,
                kind=kind,
                mode="SYNTHETIC",
                registered_by=operator_id,
                registered_at=now,
            )
        )
        return evidence_id

    policy = ControlPolicy(
        id=_id(run_id, "policy"),
        effective_at=effective,
        expires_at=expiry,
        evidence_id=await proof("CONTROL", "CONTROL"),
        capability=Capability.OPENAI_GENERATE,
        account_handle=use.account_handle,
        timeout_seconds=30,
        quota_limit=10,
        window_seconds=3600,
        concurrency_limit=1,
        failure_threshold=2,
        failure_window_seconds=3600,
        cooldown_seconds=60,
    )
    await provisioner.policy(policy)
    grant = ProviderUsageGrant(
        grant_id=_id(run_id, "grant"),
        version=1,
        **use.model_dump(exclude={"schema_version", "required_fields"}),
        outbound_use_permitted=True,
        storage_fields=frozenset({ContentField.TEXT}),
        retention_rule_id=_id(run_id, "retention"),
        retention_seconds=60,
        approved_by=operator_id,
        approved_at=effective,
        effective_at=effective,
        expires_at=expiry,
        supporting_evidence_ref=await proof("GRANT", "GRANT"),
    )
    await provisioner.grant(grant)
    prices = []
    for component in (
        UsageComponent.REQUEST,
        UsageComponent.INPUT_TOKEN,
        UsageComponent.OUTPUT_TOKEN,
        UsageComponent.CACHED_TOKEN,
    ):
        price = PriceVersion(
            id=_id(run_id, f"price-{component.value}"),
            effective_at=effective,
            expires_at=expiry,
            evidence_id=await proof(f"PRICE_{component.value}", "PRICE"),
            model_identifier="gpt-5-mini",
            capability=Capability.OPENAI_GENERATE,
            component=component,
            currency="USD",
            unit_price=Decimal("0.000001"),
            unit_quantity=Decimal(1),
            currency_quantum=Decimal("0.01"),
        )
        await provisioner.price(price)
        prices.append(price)
    fx = FxVersion(
        id=_id(run_id, "fx"),
        effective_at=effective,
        expires_at=expiry,
        evidence_id=await proof("FX", "FX"),
        currency="USD",
        rate=Decimal("3.5"),
    )
    await provisioner.fx(fx)
    config = CapabilityConfig(
        id=_id(run_id, "config"),
        version=config_version,
        workflow_id=workflow_id,
        intended_use=use,
        prices=tuple(
            PriceBound(
                price_id=price.id,
                max_quantity=Decimal(1)
                if price.component is UsageComponent.REQUEST
                else Decimal(300)
                if price.component is UsageComponent.OUTPUT_TOKEN
                else Decimal(10000),
            )
            for price in prices
        ),
        fx_id=fx.id,
        requested_count=1,
        secret_handle="l07-recorded-only",
        adapter_version=_id(run_id, "adapter"),
        model_identifier="gpt-5-mini",
    )
    await provisioner.config(config)
    await provisioner.budgets(
        attribution,
        provider=Provider.OPENAI,
        currencies=("USD", "ILS"),
        limit=budget_usd,
        effective_at=effective,
        expires_at=expiry,
    )
    repository = GovernanceRepository(engine)
    transport = _RecordedResponses()
    runtimes = {}
    for stage in IdeaStage:
        profile = idea_profile(
            stage,
            config_id=config.id,
            config_version=config.version,
            adapter_version=config.adapter_version,
            model_identifier="gpt-5-mini",
            reasoning_effort="low",
            max_output_tokens=300,
        )
        runtimes[stage] = OpenAIRuntime(
            repository,
            OpenAIRunStore(engine),
            routes=RoutingPolicy(
                cheap=config.id,
                stronger=_id(run_id, "stronger"),
                premium=_id(run_id, "premium"),
            ),
            profiles={config.id: profile},
            transport=transport,
            secrets=_RecordedSecrets(),
        )
    return IdeaRuntime(ProductRecordsRepository(engine), runtimes), attribution
