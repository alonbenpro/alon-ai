"""PostgreSQL authority. Trusted provisioning is separate from runtime execution.

Lock order everywhere: experiment fence -> authority(account,capability) -> call
-> sorted budget account IDs. Grant/control writers take only authority; they
never acquire experiments. No hook or transaction may perform network I/O.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal, localcontext
from functools import wraps
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import and_, delete, insert, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting import schema as s
from alon_ai.accounting.models import (
    AccountingDenied,
    CallReceipt,
    CallState,
    CapabilityConfig,
    ControlPolicy,
    EvidenceRecord,
    FxVersion,
    PriceVersion,
    Reason,
    current,
    exact_product,
    reserve_amount,
)
from alon_ai.providers.contracts import (
    CAPABILITIES,
    AgentActor,
    CallAttribution,
    CostKnowledge,
    Nature,
    Provider,
    ProviderResultMetadata,
    SafeRequestMetadata,
    UsageObservation,
)
from alon_ai.providers.rights import (
    GrantEvent,
    ProviderUsageGrant,
    RightsMode,
    RuntimeContent,
    evaluate_rights,
)


def safe_errors[**P, R](
    function: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    @wraps(function)
    async def guarded(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            with localcontext() as decimal_context:
                decimal_context.prec = 64
                return await function(*args, **kwargs)
        except (SQLAlchemyError, ValidationError, ArithmeticError, PermissionError):
            pass
        # Raise outside the exception handler: raw source/DB parameters cannot
        # survive in __context__, even when callers inspect the public error.
        raise AccountingDenied(Reason.STATE)

    return guarded


def _dto(cls, data):
    return cls.model_validate_json(json.dumps(data, default=str))


async def lock_experiment(
    conn: AsyncConnection, experiment_id: UUID
) -> Mapping[str, Any]:
    """Task4 acceptance and every paid admission share this exact transaction fence."""
    row = (
        (
            await conn.execute(
                select(s.experiments)
                .where(s.experiments.c.id == experiment_id)
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccountingDenied(Reason.SCOPE)
    return dict(row)


class AdmissionHook(Protocol):
    async def admit(
        self,
        connection: AsyncConnection,
        attribution: CallAttribution,
        call_id: UUID,
        phase: str,
    ) -> None:
        """SQL-only; raise AccountingDenied to roll back. Experiment already locked."""
        ...


async def _authority(conn, account, capability):
    row = (
        (
            await conn.execute(
                select(s.authorities)
                .where(
                    s.authorities.c.account == account,
                    s.authorities.c.capability == capability,
                )
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise AccountingDenied(Reason.CONFIG)
    return row


async def _audit(conn, now, kind, *, call_id=None, attr=None, reason=None):
    await conn.execute(
        insert(s.audit).values(
            id=uuid4(),
            call_id=call_id,
            experiment_id=attr.experiment_id if attr else None,
            correlation_id=attr.correlation_id if attr else None,
            kind=kind,
            reason=reason,
            created_at=now,
        )
    )


class GovernanceProvisioner:
    """Trusted operator/L03 composition only; never expose through a generic endpoint."""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    @safe_errors
    async def evidence(self, proof: EvidenceRecord) -> None:
        async with self.engine.begin() as c:
            await c.execute(
                insert(s.evidence).values(
                    **proof.model_dump(exclude={"schema_version"})
                )
            )

    @safe_errors
    async def scope(self, attr: CallAttribution, *, gate_kind: str = "NONE") -> None:
        async with self.engine.begin() as conn:
            await conn.execute(
                pg_insert(s.experiments)
                .values(id=attr.experiment_id)
                .on_conflict_do_nothing()
            )
            await lock_experiment(conn, attr.experiment_id)
            for tab, values in (
                (
                    s.workflows,
                    {"id": attr.workflow_run_id, "experiment_id": attr.experiment_id},
                ),
                *(
                    (
                        [
                            (
                                s.agents,
                                {
                                    "id": attr.actor.agent_run_id,
                                    "workflow_id": attr.workflow_run_id,
                                },
                            )
                        ]
                    )
                    if isinstance(attr.actor, AgentActor)
                    else []
                ),
                (
                    s.operations,
                    {
                        "id": attr.operation_run_id,
                        "experiment_id": attr.experiment_id,
                        "workflow_id": attr.workflow_run_id,
                        "kind": attr.operation_run_kind,
                        "agent_id": attr.actor.agent_run_id
                        if isinstance(attr.actor, AgentActor)
                        else None,
                        "service": None
                        if isinstance(attr.actor, AgentActor)
                        else attr.actor.service,
                        "config_version": attr.config_version,
                        "gate_kind": gate_kind,
                    },
                ),
            ):
                await conn.execute(
                    pg_insert(tab).values(**values).on_conflict_do_nothing()
                )
                actual = (
                    (await conn.execute(select(tab).where(tab.c.id == values["id"])))
                    .mappings()
                    .one()
                )
                if dict(actual) != values:
                    raise AccountingDenied(Reason.SCOPE)

    @safe_errors
    async def policy(self, policy: ControlPolicy) -> None:
        async with self.engine.begin() as c:
            await c.execute(
                pg_insert(s.authorities)
                .values(account=policy.account_handle, capability=policy.capability)
                .on_conflict_do_nothing()
            )
            await _authority(c, policy.account_handle, policy.capability)
            await c.execute(
                insert(s.policies).values(
                    id=policy.id,
                    account=policy.account_handle,
                    capability=policy.capability,
                    data=policy.model_dump(mode="json"),
                    evidence_id=policy.evidence_id,
                )
            )
            await c.execute(
                update(s.authorities)
                .where(
                    s.authorities.c.account == policy.account_handle,
                    s.authorities.c.capability == policy.capability,
                )
                .values(policy_id=policy.id)
            )

    @safe_errors
    async def grant(self, grant: ProviderUsageGrant) -> None:
        async with self.engine.begin() as c:
            await _authority(c, grant.account_handle, grant.capability)
            await c.execute(
                insert(s.grants).values(
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

    @safe_errors
    async def grant_event(self, event: GrantEvent) -> None:
        async with self.engine.begin() as c:
            g = (
                (
                    await c.execute(
                        select(s.grants).where(
                            s.grants.c.id == event.grant_id,
                            s.grants.c.version == event.grant_version,
                        )
                    )
                )
                .mappings()
                .one()
            )
            await _authority(c, g["account"], g["capability"])
            await c.execute(
                insert(s.grant_events).values(
                    id=event.event_id,
                    grant_id=event.grant_id,
                    grant_version=event.grant_version,
                    data=event.model_dump(mode="json"),
                    evidence_id=event.evidence_ref,
                )
            )

    @safe_errors
    async def price(self, price: PriceVersion) -> None:
        async with self.engine.begin() as c:
            await c.execute(
                insert(s.prices).values(**price.model_dump(exclude={"schema_version"}))
            )

    @safe_errors
    async def fx(self, fx: FxVersion) -> None:
        async with self.engine.begin() as c:
            await c.execute(
                insert(s.fx).values(**fx.model_dump(exclude={"schema_version"}))
            )

    @safe_errors
    async def config(self, config: CapabilityConfig) -> None:
        async with self.engine.begin() as c:
            await c.execute(
                insert(s.configs).values(
                    id=config.id,
                    workflow_id=config.workflow_id,
                    version=config.version,
                    account=config.intended_use.account_handle,
                    capability=config.intended_use.capability,
                    fx_id=config.fx_id,
                    data=config.model_dump(mode="json"),
                )
            )
            for bound in config.prices:
                await c.execute(
                    insert(s.config_prices).values(
                        config_id=config.id,
                        price_id=bound.price_id,
                        max_quantity=bound.max_quantity,
                    )
                )

    @safe_errors
    async def budgets(
        self,
        attr: CallAttribution,
        *,
        provider: Provider,
        currencies: tuple[str, ...],
        limit: Decimal,
        effective_at: datetime,
        expires_at: datetime,
    ) -> None:
        """Create explicit caps. Existing parent caps are immutable in this command.

        A new child scope cannot reset an existing global/experiment/provider cap.
        Operator limit changes are a separate audited control concern.
        """
        if type(limit) is not Decimal or not limit.is_finite() or limit < 0:
            raise AccountingDenied(Reason.BUDGET)
        async with self.engine.begin() as c:
            await lock_experiment(c, attr.experiment_id)
            for scope in _scopes(attr, provider):
                for currency in set(currencies):
                    await c.execute(
                        pg_insert(s.budget_accounts)
                        .values(
                            id=uuid4(),
                            **scope,
                            currency=currency,
                            limit=limit,
                            effective_at=effective_at,
                            expires_at=expires_at,
                        )
                        .on_conflict_do_nothing()
                    )


def _scopes(a, provider):
    return [
        {
            "scope": kind,
            "experiment_id": a.experiment_id
            if kind not in {"GLOBAL", "PROVIDER"}
            else None,
            "workflow_id": a.workflow_run_id
            if kind in {"WORKFLOW", "OPERATION"}
            else None,
            "operation_id": a.operation_run_id if kind == "OPERATION" else None,
            "provider": provider
            if kind in {"PROVIDER", "EXPERIMENT_PROVIDER"}
            else None,
        }
        for kind in (
            "GLOBAL",
            "EXPERIMENT",
            "WORKFLOW",
            "OPERATION",
            "PROVIDER",
            "EXPERIMENT_PROVIDER",
        )
    ]


class GovernanceRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        admission_hooks: Mapping[str, AdmissionHook] | None = None,
    ):
        self.engine = engine
        self.clock = clock
        self._hooks = dict(admission_hooks or {})

    async def _config(self, c, config_id):
        row = (
            await c.execute(select(s.configs.c.data).where(s.configs.c.id == config_id))
        ).scalar_one_or_none()
        if row is None:
            raise AccountingDenied(Reason.CONFIG)
        return _dto(CapabilityConfig, row)

    @safe_errors
    async def config_for_call(self, call_id: UUID) -> CapabilityConfig:
        async with self.engine.connect() as c:
            row = await self._call(c, call_id)
            return await self._config(c, row["config_id"])

    @safe_errors
    async def generation_config_and_prices(
        self, config_id: UUID
    ) -> tuple[CapabilityConfig, tuple[PriceVersion, ...]]:
        """Read the same immutable price versions used by reservation and settlement."""
        async with self.engine.connect() as c:
            config = await self._config(c, config_id)
            prices, _, _, _ = await self._prices(c, config, self.clock())
            return config, tuple(prices)

    @safe_errors
    async def receipt_for_idempotency_key(self, key: UUID) -> CallReceipt | None:
        """Find a fenced attempt after cancellation or an interrupted response path."""
        async with self.engine.connect() as c:
            row = (
                (
                    await c.execute(
                        select(s.calls).where(s.calls.c.idempotency_key == key)
                    )
                )
                .mappings()
                .one_or_none()
            )
            return self._receipt(row) if row is not None else None

    async def _call(self, c, call_id, *, lock=False):
        q = select(s.calls).where(s.calls.c.id == call_id)
        row = (
            (await c.execute(q.with_for_update() if lock else q))
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AccountingDenied(Reason.STATE)
        return row

    def _receipt(self, row, *, token=None, timeout=None):
        return CallReceipt(
            call_id=row["id"],
            state=CallState(row["state"]),
            currency=row["currency"],
            reserved=row["reserved"],
            reserved_ils=row["reserved_ils"],
            accrued=row["accrued"],
            accrued_ils=row["accrued_ils"],
            token=token,
            timeout_seconds=timeout,
        )

    @safe_errors
    async def get(self, call_id: UUID) -> CallReceipt:
        async with self.engine.connect() as c:
            return self._receipt(await self._call(c, call_id))

    async def _scope(self, c, a):
        op = (
            (
                await c.execute(
                    select(s.operations).where(s.operations.c.id == a.operation_run_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if op is None or any(
            op[k] != v
            for k, v in {
                "experiment_id": a.experiment_id,
                "workflow_id": a.workflow_run_id,
                "config_version": a.config_version,
                "kind": a.operation_run_kind,
                "agent_id": a.actor.agent_run_id
                if isinstance(a.actor, AgentActor)
                else None,
                "service": None if isinstance(a.actor, AgentActor) else a.actor.service,
            }.items()
        ):
            raise AccountingDenied(Reason.SCOPE)
        return op

    async def _gate(self, c, a, op, call_id, phase):
        if op["gate_kind"] != "NONE":
            hook = self._hooks.get(op["gate_kind"])
            if hook is None:
                raise AccountingDenied(Reason.GATE)
            await hook.admit(c, a, call_id, phase)

    async def _rights(self, c, config, now, expected=None):
        use = config.intended_use
        rows = (
            (
                await c.execute(
                    select(s.grants).where(
                        s.grants.c.account == use.account_handle,
                        s.grants.c.capability == use.capability,
                        s.grants.c.effective_at <= now,
                        s.grants.c.expires_at > now,
                    )
                )
            )
            .mappings()
            .all()
        )
        candidates = [_dto(ProviderUsageGrant, r["data"]) for r in rows]
        superseded = {g.supersedes_id for g in candidates if g.supersedes_id}
        candidates = [g for g in candidates if g.grant_id not in superseded]
        if len(candidates) != 1:
            raise AccountingDenied(Reason.RIGHTS)
        grant = candidates[0]
        events = tuple(
            _dto(GrantEvent, r)
            for r in (
                await c.execute(
                    select(s.grant_events.c.data).where(
                        s.grant_events.c.grant_id == grant.grant_id,
                        s.grant_events.c.grant_version == grant.version,
                    )
                )
            ).scalars()
        )
        if expected and (grant.grant_id, grant.version) != expected:
            raise AccountingDenied(Reason.RIGHTS)
        if evaluate_rights(grant, events, use, now=now).mode == RightsMode.DENIED:
            raise AccountingDenied(Reason.RIGHTS)
        return grant, events

    async def _prices(self, c, config, now, *, check_current=True):
        prices = [
            _dto(PriceVersion, dict(r))
            for r in (
                await c.execute(
                    select(s.prices).where(
                        s.prices.c.id.in_([b.price_id for b in config.prices])
                    )
                )
            ).mappings()
        ]
        fxrow = (
            (await c.execute(select(s.fx).where(s.fx.c.id == config.fx_id)))
            .mappings()
            .one_or_none()
        )
        if fxrow is None or len(prices) != len(config.prices):
            raise AccountingDenied(Reason.PRICE)
        fx = _dto(FxVersion, dict(fxrow))
        if (
            len({p.component for p in prices}) != len(prices)
            or len({p.currency_quantum for p in prices}) != 1
        ):
            raise AccountingDenied(Reason.PRICE)
        if any(
            p.capability != config.intended_use.capability
            or p.currency != fx.currency
            or p.model_identifier != config.model_identifier
            for p in prices
        ):
            raise AccountingDenied(Reason.PRICE)
        if check_current and (
            not current(fx, now) or any(not current(p, now) for p in prices)
        ):
            raise AccountingDenied(Reason.PRICE)
        with localcontext() as ctx:
            ctx.prec = 64
            total = Decimal(0)
            for bound in config.prices:
                p = next(p for p in prices if p.id == bound.price_id)
                total += (bound.max_quantity * p.unit_price / p.unit_quantity).quantize(
                    Decimal("1e-24"), rounding=ROUND_CEILING
                )
        return (
            prices,
            fx,
            reserve_amount(total, prices[0].currency_quantum),
            reserve_amount(exact_product(total, fx.rate), Decimal(".01")),
        )

    async def _accounts(self, c, a, provider, currencies, now):
        scopes = _scopes(a, provider)
        conditions = [
            and_(*(s.budget_accounts.c[k] == v for k, v in scope.items()))
            for scope in scopes
        ]
        rows = (
            (
                await c.execute(
                    select(s.budget_accounts)
                    .where(
                        or_(*conditions),
                        s.budget_accounts.c.currency.in_(currencies),
                        s.budget_accounts.c.effective_at <= now,
                        s.budget_accounts.c.expires_at > now,
                    )
                    .order_by(s.budget_accounts.c.id)
                    .with_for_update()
                )
            )
            .mappings()
            .all()
        )
        if len(rows) != len(scopes) * len(set(currencies)) or len(
            {(r["scope"], r["currency"]) for r in rows}
        ) != len(rows):
            raise AccountingDenied(Reason.BUDGET)
        return rows

    @safe_errors
    async def reserve(
        self,
        attribution: CallAttribution,
        request: SafeRequestMetadata,
        *,
        idempotency_key: UUID,
    ) -> CallReceipt:
        now = self.clock()
        try:
            async with self.engine.begin() as c:
                root = await lock_experiment(c, attribution.experiment_id)
                op = await self._scope(c, attribution)
                # UUID advisory lock prevents same-key races across different experiments.
                await c.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": idempotency_key.int % (2**63 - 1)},
                )
                prior = (
                    (
                        await c.execute(
                            select(s.calls).where(
                                or_(
                                    s.calls.c.idempotency_key == idempotency_key,
                                    s.calls.c.logical_operation_id
                                    == attribution.logical_operation_id,
                                )
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if prior:
                    if (
                        prior["idempotency_key"] != idempotency_key
                        or prior["attribution"] != attribution.model_dump(mode="json")
                        or prior["request"] != request.model_dump(mode="json")
                    ):
                        raise AccountingDenied(Reason.CONFLICT)
                    return self._receipt(prior)
                if not root["enabled"]:
                    raise AccountingDenied(Reason.GATE)
                now = self.clock()
                if now >= attribution.deadline:
                    raise AccountingDenied(Reason.DEADLINE)
                config = await self._config(c, request.config_ref)
                if (
                    config.workflow_id != attribution.workflow_run_id
                    or config.version != attribution.config_version
                ):
                    raise AccountingDenied(Reason.SCOPE)
                if request.requested_count != config.requested_count:
                    raise AccountingDenied(Reason.CONFIG)
                if CAPABILITIES[config.intended_use.capability].nature == Nature.WRITE:
                    raise AccountingDenied(Reason.WRITE)
                auth = await _authority(
                    c,
                    config.intended_use.account_handle,
                    config.intended_use.capability,
                )
                if not auth["enabled"]:
                    raise AccountingDenied(Reason.CONFIG)
                now = self.clock()
                policy = await self._policy(c, auth, now)
                grant, events = await self._rights(c, config, now)
                prices, fx, reserved, reserved_ils = await self._prices(c, config, now)
                call_id = uuid4()
                await self._gate(c, attribution, op, call_id, "RESERVE")
                accounts = await self._accounts(
                    c,
                    attribution,
                    config.intended_use.provider,
                    {fx.currency, "ILS"},
                    now,
                )
                now = self._admission_now(
                    attribution, config, grant, events, prices, fx, policy, accounts
                )
                for a in accounts:
                    amount = reserved_ils if a["currency"] == "ILS" else reserved
                    if (
                        a["frozen"]
                        or a["reserved"] + a["accrued"] + amount > a["limit"]
                    ):
                        raise AccountingDenied(Reason.BUDGET)
                await c.execute(
                    insert(s.calls).values(
                        id=call_id,
                        idempotency_key=idempotency_key,
                        logical_operation_id=attribution.logical_operation_id,
                        experiment_id=attribution.experiment_id,
                        workflow_id=attribution.workflow_run_id,
                        operation_id=attribution.operation_run_id,
                        config_version=attribution.config_version,
                        config_id=config.id,
                        attribution=attribution.model_dump(mode="json"),
                        request=request.model_dump(mode="json"),
                        grant_id=grant.grant_id,
                        grant_version=grant.version,
                        currency=fx.currency,
                        reserved=reserved,
                        reserved_ils=reserved_ils,
                        state="RESERVED",
                        created_at=now,
                    )
                )
                for a in accounts:
                    amount = reserved_ils if a["currency"] == "ILS" else reserved
                    await c.execute(
                        insert(s.allocations).values(
                            call_id=call_id, account_id=a["id"], amount=amount
                        )
                    )
                    await c.execute(
                        update(s.budget_accounts)
                        .where(s.budget_accounts.c.id == a["id"])
                        .values(reserved=a["reserved"] + amount)
                    )
                await _audit(c, now, "RESERVED", call_id=call_id, attr=attribution)
                return self._receipt(await self._call(c, call_id))
        except AccountingDenied as error:
            async with self.engine.begin() as c:
                await _audit(c, now, "DENIED", attr=attribution, reason=error.reason)
            raise

    async def _policy(self, c, auth, now):
        data = (
            await c.execute(
                select(s.policies.c.data).where(s.policies.c.id == auth["policy_id"])
            )
        ).scalar_one_or_none()
        if data is None:
            raise AccountingDenied(Reason.CONFIG)
        policy = _dto(ControlPolicy, data)
        if (
            not current(policy, now)
            or policy.capability != auth["capability"]
            or policy.account_handle != auth["account"]
        ):
            raise AccountingDenied(Reason.CONFIG)
        return policy

    async def _locked_call(self, c, call_id):
        initial = await self._call(c, call_id)
        root = await lock_experiment(c, initial["experiment_id"])
        config = await self._config(c, initial["config_id"])
        auth = await _authority(
            c, config.intended_use.account_handle, config.intended_use.capability
        )
        row = await self._call(c, call_id, lock=True)
        return row, config, auth, root

    @safe_errors
    async def dispatch(self, call_id: UUID) -> CallReceipt:
        now = self.clock()
        try:
            async with self.engine.begin() as c:
                row, config, auth, root = await self._locked_call(c, call_id)
                if row["state"] in {"DISPATCHED", "RECONCILING"}:
                    raise AccountingDenied(Reason.UNCERTAIN)
                if row["state"] != "RESERVED":
                    raise AccountingDenied(Reason.STATE)
                attr = _dto(CallAttribution, row["attribution"])
                now = self.clock()
                if now >= attr.deadline:
                    raise AccountingDenied(Reason.DEADLINE)
                if not root["enabled"] or not auth["enabled"]:
                    raise AccountingDenied(Reason.GATE)
                if CAPABILITIES[config.intended_use.capability].nature == Nature.WRITE:
                    raise AccountingDenied(Reason.WRITE)
                op = await self._scope(c, attr)
                await self._gate(c, attr, op, call_id, "DISPATCH")
                accounts = await self._allocation_accounts(c, call_id)
                now = self.clock()
                grant, events = await self._rights(
                    c, config, now, (row["grant_id"], row["grant_version"])
                )
                prices, fx, _, _ = await self._prices(c, config, now)
                policy = await self._policy(c, auth, now)
                now = self._admission_now(
                    attr, config, grant, events, prices, fx, policy, accounts
                )
                if any(
                    a["frozen"]
                    or a["reserved"] + a["accrued"] > a["limit"]
                    or not a["effective_at"] <= now < a["expires_at"]
                    for a in accounts
                ):
                    raise AccountingDenied(Reason.BUDGET)
                if auth["open_until"] and (
                    now < auth["open_until"] or auth["probe_id"] is not None
                ):
                    raise AccountingDenied(Reason.CIRCUIT)
                # Anchored UTC policy windows never reset just because a worker restarts.
                elapsed = (now - policy.effective_at) // timedelta(
                    seconds=policy.window_seconds
                )
                window = policy.effective_at + timedelta(
                    seconds=elapsed * policy.window_seconds
                )
                used = auth["quota_used"] if auth["window_start"] == window else 0
                if used >= policy.quota_limit:
                    raise AccountingDenied(Reason.QUOTA)
                if auth["active"] >= policy.concurrency_limit:
                    raise AccountingDenied(Reason.CONCURRENCY)
                timeout = min(
                    policy.timeout_seconds,
                    (attr.deadline - now).total_seconds(),
                )
                token = uuid4()
                await c.execute(
                    update(s.authorities)
                    .where(
                        s.authorities.c.account == auth["account"],
                        s.authorities.c.capability == auth["capability"],
                    )
                    .values(
                        quota_used=used + 1,
                        window_start=window,
                        active=auth["active"] + 1,
                        probe_id=call_id if auth["open_until"] else None,
                    )
                )
                await c.execute(
                    update(s.calls)
                    .where(s.calls.c.id == call_id)
                    .values(
                        state="DISPATCHED",
                        token=token,
                        dispatch_at=now,
                        lease_until=now + timedelta(seconds=timeout),
                        policy_id=policy.id,
                    )
                )
                await _audit(c, now, "DISPATCHED", call_id=call_id, attr=attr)
                return self._receipt(
                    await self._call(c, call_id), token=token, timeout=timeout
                )
        except AccountingDenied as e:
            async with self.engine.begin() as c:
                await _audit(
                    c, now, "DISPATCH_DENIED", call_id=call_id, reason=e.reason
                )
            raise

    def _admission_now(
        self, attribution, config, grant, events, prices, fx, policy, accounts
    ):
        """Final pure checks AFTER every row lock and SQL-only admission hook.

        Rows/grant events are stable under the acquired locks; wall-clock validity
        is not. No subsequent admission write needs another safety-row lock.
        """
        now = self.clock()
        if now >= attribution.deadline:
            raise AccountingDenied(Reason.DEADLINE)
        if (
            evaluate_rights(grant, events, config.intended_use, now=now).mode
            == RightsMode.DENIED
        ):
            raise AccountingDenied(Reason.RIGHTS)
        if not current(fx, now) or any(not current(price, now) for price in prices):
            raise AccountingDenied(Reason.PRICE)
        if not current(policy, now):
            raise AccountingDenied(Reason.CONFIG)
        if any(
            not account["effective_at"] <= now < account["expires_at"]
            for account in accounts
        ):
            raise AccountingDenied(Reason.BUDGET)
        return now

    async def _allocation_accounts(self, c, call_id):
        return (
            (
                await c.execute(
                    select(s.budget_accounts, s.allocations.c.amount)
                    .join(
                        s.allocations,
                        s.allocations.c.account_id == s.budget_accounts.c.id,
                    )
                    .where(s.allocations.c.call_id == call_id)
                    .order_by(s.budget_accounts.c.id)
                    .with_for_update(of=s.budget_accounts)
                )
            )
            .mappings()
            .all()
        )

    @safe_errors
    async def cancel_before_dispatch(
        self, call_id: UUID, *, command_key: UUID
    ) -> CallReceipt:
        now = self.clock()
        async with self.engine.begin() as c:
            row, _, _, _ = await self._locked_call(c, call_id)
            if row["state"] == "RELEASED":
                return self._receipt(row)
            if row["state"] != "RESERVED":
                raise AccountingDenied(Reason.STATE)
            for a in await self._allocation_accounts(c, call_id):
                await c.execute(
                    update(s.budget_accounts)
                    .where(s.budget_accounts.c.id == a["id"])
                    .values(reserved=a["reserved"] - a["amount"])
                )
            proof_id = uuid4()
            await c.execute(
                insert(s.evidence).values(
                    id=proof_id,
                    kind="RECONCILIATION",
                    mode="TRUSTED_REFERENCE",
                    registered_by=call_id,
                    registered_at=now,
                    call_id=call_id,
                )
            )
            await c.execute(
                insert(s.settlements).values(
                    id=uuid4(),
                    call_id=call_id,
                    command_key=command_key,
                    kind="PROVEN_UNUSED",
                    cost=0,
                    cost_ils=0,
                    previous_cost=0,
                    previous_ils=0,
                    evidence_id=proof_id,
                    created_at=now,
                )
            )
            await c.execute(
                update(s.calls)
                .where(s.calls.c.id == call_id)
                .values(state="RELEASED", finished_at=now)
            )
            await _audit(c, now, "RELEASED", call_id=call_id)
            return self._receipt(await self._call(c, call_id))

    def _token(self, row, token):
        if (
            token is None
            or row["token"] != token
            or row["state"] not in {"DISPATCHED", "RECONCILING", "FINAL"}
        ):
            raise AccountingDenied(Reason.STATE)

    @safe_errors
    async def mark_unknown(self, call_id: UUID, *, token: UUID) -> CallReceipt:
        async with self.engine.begin() as c:
            row, _, auth, _ = await self._locked_call(c, call_id)
            self._token(row, token)
            if row["state"] != "FINAL":
                if row["error"] != "UNCERTAIN":
                    data = (
                        await c.execute(
                            select(s.policies.c.data).where(
                                s.policies.c.id == row["policy_id"]
                            )
                        )
                    ).scalar_one()
                    policy = _dto(ControlPolicy, data)
                    updates = self._failure_values(auth, policy, self.clock())
                    await c.execute(
                        update(s.authorities)
                        .where(
                            s.authorities.c.account == auth["account"],
                            s.authorities.c.capability == auth["capability"],
                        )
                        .values(**updates)
                    )
                await c.execute(
                    update(s.calls)
                    .where(s.calls.c.id == call_id)
                    .values(state="RECONCILING", error="UNCERTAIN")
                )
                await _audit(c, self.clock(), "UNKNOWN", call_id=call_id)
            return self._receipt(await self._call(c, call_id))

    @safe_errors
    async def finish_attempt(
        self,
        call_id: UUID,
        *,
        token: UUID,
        success: bool,
        metadata: ProviderResultMetadata | None = None,
    ) -> UUID | None:
        """Positive completed-response evidence; exceptions/timeouts use mark_unknown."""
        now = self.clock()
        async with self.engine.begin() as c:
            row, config, auth, _ = await self._locked_call(c, call_id)
            self._token(row, token)
            if row["finished_at"]:
                return
            if metadata and (
                metadata.capability != config.intended_use.capability
                or metadata.status == "UNKNOWN"
            ):
                raise AccountingDenied(Reason.USAGE)
            await self._finish(c, row, auth, now, success)
            if metadata:
                await c.execute(
                    update(s.calls)
                    .where(s.calls.c.id == call_id)
                    .values(result_metadata=metadata.model_dump(mode="json"))
                )
                proof_id = uuid4()
                await c.execute(
                    insert(s.evidence).values(
                        id=proof_id,
                        kind="PROVIDER_RESULT",
                        mode="TRUSTED_REFERENCE",
                        registered_by=call_id,
                        registered_at=now,
                        call_id=call_id,
                    )
                )
                return proof_id
            return None

    async def _finish(self, c, row, auth, now, success):
        # Completion uses the policy pinned at dispatch in its immutable event.
        # Current settings may get stricter while in flight, never erase failures.
        data = (
            await c.execute(
                select(s.policies.c.data).where(s.policies.c.id == row["policy_id"])
            )
        ).scalar_one()
        policy = _dto(ControlPolicy, data)
        updates = {
            "active": auth["active"] - 1,
            "probe_id": None if auth["probe_id"] == row["id"] else auth["probe_id"],
        }
        if success:
            if auth["probe_id"] == row["id"]:
                updates.update(failures=0, failure_start=None, open_until=None)
        elif success is False and row["error"] != "UNCERTAIN":
            updates.update(self._failure_values(auth, policy, now))
        await c.execute(
            update(s.authorities)
            .where(
                s.authorities.c.account == auth["account"],
                s.authorities.c.capability == auth["capability"],
            )
            .values(**updates)
        )
        await c.execute(
            update(s.calls).where(s.calls.c.id == row["id"]).values(finished_at=now)
        )

    def _failure_values(self, auth, policy, now):
        start = auth["failure_start"]
        failures = (
            auth["failures"]
            if start and now < start + timedelta(seconds=policy.failure_window_seconds)
            else 0
        )
        values = {"failures": failures + 1, "failure_start": start if failures else now}
        if failures + 1 >= policy.failure_threshold or auth["probe_id"] is not None:
            values["open_until"] = now + timedelta(seconds=policy.cooldown_seconds)
        return values

    @safe_errors
    async def record_usage(
        self,
        call_id: UUID,
        observations: tuple[UsageObservation, ...],
        *,
        token: UUID,
        supersedes: Mapping[UUID, UUID] | None = None,
    ) -> None:
        """Append observations; correction keys bind the exact prior call/component."""
        now = self.clock()
        async with self.engine.begin() as c:
            row, config, _, _ = await self._locked_call(c, call_id)
            self._token(row, token)
            prices, _, _, _ = await self._prices(c, config, now, check_current=False)
            by_component = {p.component: p for p in prices}
            for obs in observations:
                if (
                    (
                        obs.cost is not None
                        and (
                            int(obs.cost.as_tuple().exponent) < -12
                            or obs.cost >= Decimal("1e12")
                        )
                    )
                    or obs.currency != row["currency"]
                    or obs.component not in by_component
                ):
                    raise AccountingDenied(Reason.USAGE)
                if row["state"] == "FINAL" and obs.knowledge != CostKnowledge.FINAL:
                    raise AccountingDenied(Reason.USAGE)
                parent_key = (supersedes or {}).get(obs.observation_key)
                parent = None
                if parent_key:
                    parent = (
                        (
                            await c.execute(
                                select(s.usage).where(
                                    s.usage.c.call_id == call_id,
                                    s.usage.c.observation_key == parent_key,
                                )
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if parent is None or parent["component"] != obs.component:
                        raise AccountingDenied(Reason.USAGE)
                values = {
                    "call_id": call_id,
                    "observation_key": obs.observation_key,
                    "component": obs.component,
                    "price_id": by_component[obs.component].id,
                    "currency": obs.currency,
                    "quantity": obs.quantity,
                    "cost": obs.cost,
                    "knowledge": obs.knowledge,
                    "supersedes_id": parent["id"] if parent else None,
                }
                old = (
                    (
                        await c.execute(
                            select(s.usage).where(
                                s.usage.c.call_id == call_id,
                                s.usage.c.observation_key == obs.observation_key,
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if old:
                    if any(old[k] != v for k, v in values.items()):
                        raise AccountingDenied(Reason.CONFLICT)
                    continue
                if (
                    parent
                    and (
                        await c.execute(
                            select(s.usage.c.id).where(
                                s.usage.c.supersedes_id == parent["id"]
                            )
                        )
                    ).first()
                ):
                    raise AccountingDenied(Reason.CONFLICT)
                await c.execute(
                    insert(s.usage).values(id=uuid4(), **values, observed_at=now)
                )
            if row["state"] != "FINAL":
                await c.execute(
                    update(s.calls)
                    .where(s.calls.c.id == call_id)
                    .values(state="RECONCILING")
                )

    @safe_errors
    async def reconcile(
        self, call_id: UUID, *, command_key: UUID, evidence_id: UUID
    ) -> CallReceipt:
        now = self.clock()
        async with self.engine.begin() as c:
            row, config, auth, _ = await self._locked_call(c, call_id)
            await self._proof(
                c, evidence_id, call_id, {"PROVIDER_RESULT", "RECONCILIATION"}
            )
            if (
                await c.execute(
                    select(s.settlements.c.id).where(
                        s.settlements.c.call_id == call_id,
                        s.settlements.c.command_key == command_key,
                    )
                )
            ).first():
                return self._receipt(row)
            if row["state"] not in {"DISPATCHED", "RECONCILING", "FINAL"}:
                raise AccountingDenied(Reason.STATE)
            prices, fx, _, _ = await self._prices(c, config, now, check_current=False)
            all_usage = (
                (await c.execute(select(s.usage).where(s.usage.c.call_id == call_id)))
                .mappings()
                .all()
            )
            superseded = {u["supersedes_id"] for u in all_usage if u["supersedes_id"]}
            live = [u for u in all_usage if u["id"] not in superseded]
            if {u["component"] for u in live} != {p.component for p in prices} or any(
                u["knowledge"] != "FINAL" for u in live
            ):
                raise AccountingDenied(Reason.UNCERTAIN)
            with localcontext() as ctx:
                ctx.prec = 64
                cost = sum((u["cost"] for u in live), Decimal(0))
                cost_ils = cost * fx.rate
                # Input costs <=12 places × FX<=12 preserve exact conversion <=24.
                if (
                    max(cost, cost_ils) >= Decimal("1e24")
                    or int(cost_ils.as_tuple().exponent) < -24
                ):
                    raise AccountingDenied(Reason.USAGE)
                accounts = await self._allocation_accounts(c, call_id)
                for a in accounts:
                    actual = cost_ils if a["currency"] == "ILS" else cost
                    prior = (
                        row["accrued_ils"] if a["currency"] == "ILS" else row["accrued"]
                    )
                    reserved = a["reserved"] - (
                        a["amount"] if row["state"] != "FINAL" else 0
                    )
                    accrued = a["accrued"] + actual - prior
                    await c.execute(
                        update(s.budget_accounts)
                        .where(s.budget_accounts.c.id == a["id"])
                        .values(
                            reserved=reserved,
                            accrued=accrued,
                            frozen=a["frozen"]
                            or reserved + accrued > a["limit"]
                            or actual > a["amount"],
                        )
                    )
            await c.execute(
                insert(s.settlements).values(
                    id=uuid4(),
                    call_id=call_id,
                    command_key=command_key,
                    kind="ADJUSTMENT" if row["state"] == "FINAL" else "FINAL",
                    cost=cost,
                    cost_ils=cost_ils,
                    previous_cost=row["accrued"],
                    previous_ils=row["accrued_ils"],
                    evidence_id=evidence_id,
                    created_at=now,
                )
            )
            if row["finished_at"] is None:
                await self._finish(c, row, auth, now, None)
            await c.execute(
                update(s.calls)
                .where(s.calls.c.id == call_id)
                .values(state="FINAL", accrued=cost, accrued_ils=cost_ils)
            )
            await _audit(c, now, "RECONCILED", call_id=call_id)
            return self._receipt(await self._call(c, call_id))

    @safe_errors
    async def settle_cash(
        self,
        call_id: UUID,
        *,
        command_key: UUID,
        amount: Decimal,
        evidence_id: UUID,
        corrects_id: UUID | None = None,
    ) -> UUID:
        """Cash is an invoice/payment view; it NEVER charges accrual budgets again."""
        if type(amount) is not Decimal or not amount.is_finite() or amount < 0:
            raise AccountingDenied(Reason.USAGE)
        async with self.engine.begin() as c:
            row, config, _, _ = await self._locked_call(c, call_id)
            await self._proof(c, evidence_id, call_id, {"INVOICE"})
            prices, fx, _, _ = await self._prices(
                c, config, self.clock(), check_current=False
            )
            if reserve_amount(amount, prices[0].currency_quantum) != amount:
                raise AccountingDenied(Reason.USAGE)
            old = (
                (
                    await c.execute(
                        select(s.cash_entries).where(
                            s.cash_entries.c.command_key == command_key
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if old:
                if (
                    old["call_id"] != call_id
                    or old["amount"] != amount
                    or old["corrects_id"] != corrects_id
                ):
                    raise AccountingDenied(Reason.CONFLICT)
                return old["id"]
            if row["state"] != "FINAL":
                raise AccountingDenied(Reason.STATE)
            if corrects_id:
                parent = (
                    await c.execute(
                        select(s.cash_entries.c.call_id).where(
                            s.cash_entries.c.id == corrects_id
                        )
                    )
                ).scalar_one_or_none()
                if parent != call_id:
                    raise AccountingDenied(Reason.SCOPE)
            entry_id = uuid4()
            await c.execute(
                insert(s.cash_entries).values(
                    id=entry_id,
                    call_id=call_id,
                    command_key=command_key,
                    amount=amount,
                    amount_ils=exact_product(amount, fx.rate),
                    evidence_id=evidence_id,
                    corrects_id=corrects_id,
                    created_at=self.clock(),
                )
            )
            return entry_id

    @safe_errors
    async def retain_content(
        self, call_id: UUID, content: RuntimeContent
    ) -> tuple[UUID, ...]:
        """Trusted adapter content for this call only; never a public payload writer."""
        now = self.clock()
        async with self.engine.begin() as c:
            row, config, auth, root = await self._locked_call(c, call_id)
            if (
                row["state"] not in {"DISPATCHED", "RECONCILING", "FINAL"}
                or not root["enabled"]
                or not auth["enabled"]
            ):
                raise AccountingDenied(Reason.RETENTION)
            old_rows = (
                (
                    await c.execute(
                        select(s.retained)
                        .where(s.retained.c.call_id == call_id)
                        .order_by(s.retained.c.id)
                        .with_for_update()
                    )
                )
                .mappings()
                .all()
            )
            old_by_field = {item["field"]: item for item in old_rows}
            now = self.clock()
            grant, events = await self._rights(
                c, config, now, (row["grant_id"], row["grant_version"])
            )
            try:
                now = self.clock()
                permitted = content.retain(current_grant=grant, events=events, now=now)
            except PermissionError:
                raise AccountingDenied(Reason.RETENTION) from None
            if (permitted.grant_id, permitted.grant_version) != (
                row["grant_id"],
                row["grant_version"],
            ) or not set(permitted.fields) <= config.intended_use.required_fields:
                raise AccountingDenied(Reason.RETENTION)
            ids = []
            for field, values in permitted.fields.items():
                old = old_by_field.get(field)
                if old:
                    if (
                        old["values"] != list(values)
                        or old["expires_at"] != permitted.expires_at
                    ):
                        raise AccountingDenied(Reason.CONFLICT)
                    ids.append(old["id"])
                    continue
                id_ = uuid4()
                await c.execute(
                    insert(s.retained).values(
                        id=id_,
                        call_id=call_id,
                        grant_id=grant.grant_id,
                        grant_version=grant.version,
                        field=field,
                        values=list(values),
                        expires_at=permitted.expires_at,
                        retention_rule_id=permitted.retention_rule_id,
                    )
                )
                ids.append(id_)
            await _audit(c, now, "RETAINED", call_id=call_id)
            return tuple(ids)

    @safe_errors
    async def read_content(self, call_id: UUID) -> dict[str, tuple[str, ...]]:
        """Explicit licensed content read; this value must never enter audit/checkpoints."""
        async with self.engine.begin() as c:
            row, config, auth, root = await self._locked_call(c, call_id)
            if not auth["enabled"] or not root["enabled"]:
                raise AccountingDenied(Reason.RETENTION)
            rows = (
                (
                    await c.execute(
                        select(s.retained).where(
                            s.retained.c.call_id == call_id,
                            s.retained.c.expires_at > self.clock(),
                        )
                    )
                )
                .mappings()
                .all()
            )
            grant, events = await self._rights(
                c, config, self.clock(), (row["grant_id"], row["grant_version"])
            )
            now = self.clock()
            if (
                evaluate_rights(grant, events, config.intended_use, now=now).mode
                == RightsMode.DENIED
            ):
                raise AccountingDenied(Reason.RIGHTS)
            return {
                r["field"]: tuple(r["values"]) for r in rows if r["expires_at"] > now
            }

    @safe_errors
    async def purge_expired(self) -> int:
        async with self.engine.begin() as c:
            removed = (
                await c.execute(
                    delete(s.retained)
                    .where(s.retained.c.expires_at <= self.clock())
                    .returning(s.retained.c.id)
                )
            ).all()
            return len(removed)

    async def _proof(self, c, evidence_id, call_id, kinds):
        proof = (
            (await c.execute(select(s.evidence).where(s.evidence.c.id == evidence_id)))
            .mappings()
            .one_or_none()
        )
        if proof is None or proof["call_id"] != call_id or proof["kind"] not in kinds:
            raise AccountingDenied(Reason.SCOPE)

    @safe_errors
    async def query(self, call_id: UUID):
        """Separate cash/accrual/estimates/capacity; callers must not sum bases."""
        from alon_ai.accounting.models import CostSnapshot

        async with self.engine.begin() as c:
            row, _, _, _ = await self._locked_call(c, call_id)
            usage_rows = (
                (await c.execute(select(s.usage).where(s.usage.c.call_id == call_id)))
                .mappings()
                .all()
            )
            replaced = {u["supersedes_id"] for u in usage_rows}
            live = [u for u in usage_rows if u["id"] not in replaced]
            cash_rows = (
                (
                    await c.execute(
                        select(s.cash_entries).where(
                            s.cash_entries.c.call_id == call_id
                        )
                    )
                )
                .mappings()
                .all()
            )
            corrected = {u["corrects_id"] for u in cash_rows}
            cash = [u for u in cash_rows if u["id"] not in corrected]
            pending = row["state"] not in {"FINAL", "RELEASED"}
            return CostSnapshot(
                call_id=call_id,
                state=CallState(row["state"]),
                currency=row["currency"],
                live_reserved=row["reserved"] if pending else Decimal(0),
                live_reserved_ils=row["reserved_ils"] if pending else Decimal(0),
                accrued=row["accrued"],
                accrued_ils=row["accrued_ils"],
                estimated=sum(
                    (u["cost"] for u in live if u["knowledge"] == "ESTIMATE"),
                    Decimal(0),
                ),
                unknown_components=sum(u["knowledge"] == "UNAVAILABLE" for u in live),
                cash=sum((u["amount"] for u in cash), Decimal(0)),
                cash_ils=sum((u["amount_ils"] for u in cash), Decimal(0)),
            )

    @safe_errors
    async def record_reconciled_usage(
        self,
        call_id: UUID,
        observations: tuple[UsageObservation, ...],
        *,
        evidence_id: UUID,
        supersedes: Mapping[UUID, UUID] | None = None,
    ) -> None:
        """Trusted recovery path after restart; proof grants accounting, never retry.

        Proof/intent are immutable. The subsequent usage transaction rechecks the
        current call state and correction lineage under the same ordered locks.
        """
        async with self.engine.begin() as connection:
            row, _, _, _ = await self._locked_call(connection, call_id)
            await self._proof(
                connection, evidence_id, call_id, {"RECONCILIATION", "PROVIDER_RESULT"}
            )
            token = row["token"]
            if token is None:
                raise AccountingDenied(Reason.STATE)
        await self.record_usage(
            call_id, observations, token=token, supersedes=supersedes
        )
