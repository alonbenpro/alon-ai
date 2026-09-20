"""Durable supply commands and SQL-only provider admission.

Composition is trusted: evidence writers accept only independently permitted,
scoped provisional references. No route, live adapter, cohort or send authority
is exposed here. Facts cannot be replaced or revoked; a safety change stops the
whole plan under the same experiment fence until a later authority owner exists.
"""

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Literal
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import AccountingDenied, Reason
from alon_ai.accounting.repository import AdmissionHook, lock_experiment
from alon_ai.policies.campaign_supply import (
    DiscoveryCompletionEvidence,
    DiscoveryPlan,
    Filter,
    IdentityEvidence,
    ReferenceEvidence,
    StopReason,
    SupplyDenied,
    SupplyFact,
    SupplySnapshot,
    validate_change,
)
from alon_ai.providers.contracts import CallAttribution
from alon_ai.supply import schema as s


def safe[**P, R](fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @wraps(fn)
    async def run(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await fn(*args, **kwargs)
        except (SQLAlchemyError, ValidationError, AccountingDenied):
            pass
        raise SupplyDenied("INVALID_STATE")

    return run


def dto(cls, data):
    return cls.model_validate_json(json.dumps(data, default=str))


async def row(c, table, key, value):
    result = (
        (await c.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )
    if result is None:
        raise SupplyDenied("MISSING_REFERENCE")
    return result


async def maybe(c, table, key, value):
    return (
        (await c.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )


async def locked(c, exp):
    await lock_experiment(c, exp)
    return await row(c, s.plans, "experiment_id", exp)


def active(plan, now):
    if plan["state"] != "ACTIVE":
        raise SupplyDenied("TERMINAL")
    if now >= plan["deadline"]:
        raise SupplyDenied("DEADLINE_EXHAUSTED")


def valid(proof, now):
    if not proof["observed_at"] <= now < proof["valid_until"]:
        raise SupplyDenied("STALE_EVIDENCE")


async def count(c, table, exp, *conditions):
    return (
        await c.execute(
            select(func.count())
            .select_from(table)
            .where(table.c.experiment_id == exp, *conditions)
        )
    ).scalar_one()


async def finish(c, exp, reason, key):
    await c.execute(
        insert(s.outcomes).values(
            experiment_id=exp,
            command_key=key,
            reason=reason,
            achieved=await count(
                c,
                s.current_qualifications,
                exp,
                s.current_qualifications.c.outcome == "QUALIFIED",
            ),
            batches_used=await count(c, s.batches, exp),
            businesses_discovered=await count(c, s.candidates, exp),
        )
    )


class SupplyEvidenceWriter:
    """Trusted provisional ingestion only. Later L03 must bind real evidence owners.

    INDEPENDENT_SOURCE is an operator-registered permitted provenance root, never
    a provider result/hash. Synthetic roots remain synthetic through every fact.
    """

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def _store(self, table, data, exp):
        async with self.engine.begin() as c:
            await lock_experiment(c, exp)
            existing = await maybe(c, table, "id", data["id"])
            if existing is not None:
                if dict(existing) != data:
                    raise SupplyDenied("EVIDENCE_CONFLICT")
                return
            await c.execute(insert(table).values(**data))

    @safe
    async def reference(self, evidence: ReferenceEvidence) -> None:
        await self._store(
            s.references,
            evidence.model_dump(exclude={"schema_version"}),
            evidence.experiment_id,
        )

    @safe
    async def identity(self, evidence: IdentityEvidence) -> None:
        await self._store(
            s.identities,
            evidence.model_dump(exclude={"schema_version"}),
            evidence.experiment_id,
        )

    @safe
    async def fact(self, evidence: SupplyFact) -> None:
        async with self.engine.connect() as c:
            identity = await row(c, s.identities, "id", evidence.identity_id)
        await self._store(
            s.facts,
            dict(
                evidence.model_dump(exclude={"schema_version"}),
                experiment_id=identity["experiment_id"],
            ),
            identity["experiment_id"],
        )

    @safe
    async def discovery_completion(self, evidence: DiscoveryCompletionEvidence) -> None:
        async with self.engine.connect() as c:
            batch = await row(c, s.batches, "id", evidence.batch_id)
        data = evidence.model_dump(exclude={"schema_version", "filter"})
        data["filter"] = evidence.filter.model_dump(mode="json")
        data["experiment_id"] = batch["experiment_id"]
        await self._store(s.discovery_completions, data, batch["experiment_id"])


class CampaignSupplyRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.engine, self.clock = engine, clock

    @safe
    async def create(
        self,
        experiment_id: UUID,
        initial_plan: DiscoveryPlan,
        allowed: tuple[Filter, ...],
        verification_policy_id: UUID,
        deadline: datetime,
    ) -> None:
        data = {
            "experiment_id": experiment_id,
            "initial_plan": initial_plan.model_dump(mode="json"),
            "allowed": [v.model_dump(mode="json") for v in allowed],
            "verification_policy_id": verification_policy_id,
            "deadline": deadline,
        }
        async with self.engine.begin() as c:
            await lock_experiment(c, experiment_id)
            prior = await maybe(c, s.plans, "experiment_id", experiment_id)
            if prior is not None:
                if any(prior[k] != v for k, v in data.items()):
                    raise SupplyDenied("PLAN_CONFLICT")
                return
            if deadline <= self.clock():
                raise SupplyDenied("DEADLINE_EXHAUSTED")
            await c.execute(insert(s.plans).values(**data))

    @safe
    async def verification_policy(self, experiment_id: UUID) -> UUID:
        async with self.engine.connect() as c:
            return (await row(c, s.plans, "experiment_id", experiment_id))[
                "verification_policy_id"
            ]

    @safe
    async def batch_plan(self, batch_id: UUID) -> DiscoveryPlan:
        async with self.engine.connect() as c:
            return dto(DiscoveryPlan, (await row(c, s.batches, "id", batch_id))["plan"])

    @safe
    async def begin_batch(
        self,
        experiment_id: UUID,
        slot: int,
        plan: DiscoveryPlan,
        command_key: UUID,
        feedback_id: UUID | None = None,
    ) -> UUID:
        async with self.engine.begin() as c:
            root = await locked(c, experiment_id)
            data = {
                "experiment_id": experiment_id,
                "slot": slot,
                "plan": plan.model_dump(mode="json"),
                "command_key": command_key,
                "feedback_id": feedback_id,
            }
            prior = await maybe(c, s.batches, "command_key", command_key)
            if prior:
                if any(prior[k] != v for k, v in data.items()):
                    raise SupplyDenied("COMMAND_CONFLICT")
                return prior["id"]
            active(root, self.clock())
            if slot not in (1, 2, 3):
                raise SupplyDenied("BATCH_LIMIT")
            if slot != 1:
                fb = await row(c, s.feedback, "id", feedback_id)
                previous = await row(c, s.batches, "id", fb["batch_id"])
                failures = tuple(
                    Filter(dimension=x["dimension"], value=UUID(x["value"]))
                    for x in fb["payload"]["performance"]
                    if x["reason"]
                    not in {"SUPPORTED", "QUALIFIED", "PENDING", "SOURCE_FAILURE"}
                )
                validate_change(
                    dto(DiscoveryPlan, previous["plan"]),
                    plan,
                    tuple(dto(Filter, x) for x in root["allowed"]),
                    failures,
                )
                if slot == 3:
                    await self._supported(c, experiment_id, self.clock())
            id_ = uuid4()
            await c.execute(
                insert(s.batches).values(id=id_, started_at=self.clock(), **data)
            )
            return id_

    @safe
    async def admit_candidate(
        self,
        batch_id: UUID,
        identity_id: UUID,
        clearance_id: UUID,
        command_key: UUID,
        *,
        observations: tuple[Filter, ...] = (),
    ) -> UUID:
        async with self.engine.begin() as c:
            batch = await row(c, s.batches, "id", batch_id)
            root = await locked(c, batch["experiment_id"])
            data = {
                "experiment_id": batch["experiment_id"],
                "batch_id": batch_id,
                "identity_id": identity_id,
                "clearance_id": clearance_id,
                "command_key": command_key,
                "observations": [x.model_dump(mode="json") for x in observations],
            }
            prior = await maybe(c, s.candidates, "command_key", command_key)
            if prior:
                if any(prior[k] != v for k, v in data.items()):
                    raise SupplyDenied("COMMAND_CONFLICT")
                return prior["id"]
            active(root, self.clock())
            identity = await row(c, s.identities, "id", identity_id)
            clearance = await row(c, s.facts, "id", clearance_id)
            valid(identity, self.clock())
            valid(clearance, self.clock())
            ordinal = (
                await c.execute(
                    select(func.count())
                    .select_from(s.candidates)
                    .where(s.candidates.c.batch_id == batch_id)
                )
            ).scalar_one() + 1
            id_ = uuid4()
            await c.execute(
                insert(s.candidates).values(id=id_, ordinal=ordinal, **data)
            )
            if clearance["kind"] == "IDENTITY_EXCLUDED":
                await c.execute(
                    insert(s.contacts).values(
                        candidate_id=id_,
                        experiment_id=batch["experiment_id"],
                        source_id=clearance_id,
                        outcome="IDENTITY_EXCLUDED",
                        resolved_at=self.clock(),
                        valid_until=min(
                            identity["valid_until"], clearance["valid_until"]
                        ),
                    )
                )
            return id_

    @safe
    async def resolve_contact(
        self, candidate_id: UUID, source_id: UUID, verification_id: UUID | None = None
    ) -> str:
        async with self.engine.begin() as c:
            candidate = await row(c, s.candidates, "id", candidate_id)
            await locked(c, candidate["experiment_id"])
            return await self._resolve_contact(
                c,
                candidate_id,
                source_id,
                verification_id,
                now=self.clock(),
            )

    async def _resolve_contact(
        self,
        c: AsyncConnection,
        candidate_id: UUID,
        source_id: UUID,
        verification_id: UUID | None = None,
        *,
        now: datetime,
    ) -> str:
        """Materialize a contact while the caller holds the experiment fence."""
        candidate = await row(c, s.candidates, "id", candidate_id)
        root = await row(c, s.plans, "experiment_id", candidate["experiment_id"])
        prior = await maybe(c, s.contacts, "candidate_id", candidate_id)
        if prior:
            if (
                prior["source_id"] != source_id
                or prior["verification_id"] != verification_id
            ):
                raise SupplyDenied("CONTACT_CONFLICT")
            return prior["outcome"]
        active(root, now)
        source = await row(c, s.facts, "id", source_id)
        clearance = await row(c, s.facts, "id", candidate["clearance_id"])
        identity = await row(c, s.identities, "id", candidate["identity_id"])
        proofs = [identity, clearance, source]
        outcome = {
            "EMAIL_ABSENT": "EMAIL_NOT_FOUND",
            "SOURCE_FAILURE": "SOURCE_FAILURE",
        }.get(source["kind"])
        if verification_id is not None:
            verification = await row(c, s.facts, "id", verification_id)
            proofs.append(verification)
            outcome = {
                "VERIFIED": "SUPPORTED",
                "VERIFICATION_REJECTED": "VERIFICATION_REJECTED",
            }.get(verification["kind"])
        for proof in proofs:
            valid(proof, now)
        if outcome is None:
            raise SupplyDenied("CONTACT_EVIDENCE")
        if outcome == "SOURCE_FAILURE":
            prior_failure = await maybe(c, s.contact_failures, "source_id", source_id)
            if prior_failure and prior_failure["candidate_id"] != candidate_id:
                raise SupplyDenied("FAILURE_CONFLICT")
            if not prior_failure:
                await c.execute(
                    insert(s.contact_failures).values(
                        source_id=source_id,
                        candidate_id=candidate_id,
                        experiment_id=candidate["experiment_id"],
                    )
                )
            return outcome
        await c.execute(
            insert(s.contacts).values(
                candidate_id=candidate_id,
                experiment_id=candidate["experiment_id"],
                source_id=source_id,
                verification_id=verification_id,
                outcome=outcome,
                resolved_at=now,
                valid_until=min(p["valid_until"] for p in proofs),
            )
        )
        return outcome

    async def _supported(self, c, exp, now):
        contacts = (
            (
                await c.execute(
                    select(s.contacts).where(
                        s.contacts.c.experiment_id == exp,
                        s.contacts.c.outcome == "SUPPORTED",
                    )
                )
            )
            .mappings()
            .all()
        )
        current = [r for r in contacts if r["resolved_at"] <= now < r["valid_until"]]
        if len(current) < 50:
            raise SupplyDenied("EMAIL_GATE")
        # Conservative complete gate dependency: every currently counted support.
        accepted_expiries = [
            expiry
            for validity in (
                await c.execute(
                    select(s.facts.c.valid_until, s.contacts.c.valid_until)
                    .select_from(
                        s.current_qualifications.join(
                            s.facts, s.current_qualifications.c.fact_id == s.facts.c.id
                        ).join(
                            s.contacts,
                            s.current_qualifications.c.candidate_id
                            == s.contacts.c.candidate_id,
                        )
                    )
                    .where(
                        s.current_qualifications.c.experiment_id == exp,
                        s.current_qualifications.c.outcome == "QUALIFIED",
                    )
                )
            ).all()
            for expiry in validity
        ]
        # Historical accepted members are mandatory dependencies, even when
        # enough other current contacts could form a new email quorum. Contact
        # validity is the immutable minimum of identity, clearance, source and
        # verification validity; qualification has its own independent expiry.
        if any(expiry <= now for expiry in accepted_expiries):
            raise SupplyDenied("STALE_ACCEPTED_EVIDENCE")
        return min([r["valid_until"] for r in current] + accepted_expiries)

    @safe
    async def close_contactability(
        self, batch_id: UUID, command_key: UUID
    ) -> UUID | None:
        return await self._close(batch_id, command_key, "EMAIL")

    @safe
    async def close_qualification(
        self, batch_id: UUID, command_key: UUID
    ) -> UUID | None:
        return await self._close(batch_id, command_key, "QUALIFICATION")

    async def _close(self, batch_id, key, gate):
        async with self.engine.begin() as c:
            batch = await row(c, s.batches, "id", batch_id)
            root = await locked(c, batch["experiment_id"])
            prior = await maybe(c, s.closures, "command_key", key)
            if prior:
                if prior["batch_id"] != batch_id or prior["gate"] != gate:
                    raise SupplyDenied("COMMAND_CONFLICT")
                return prior["feedback_id"]
            active(root, self.clock())
            batch = await row(c, s.batches, "id", batch_id)
            if batch["stage"] != ("CONTACT" if gate == "EMAIL" else "QUALIFICATION"):
                raise SupplyDenied("GATE_STATE")
            payload = (
                await c.execute(
                    text("SELECT supply_feedback_payload(:b,:g)"),
                    {"b": batch_id, "g": gate},
                )
            ).scalar_one()
            if any(
                x["reason"] in {"PENDING", "SOURCE_FAILURE"}
                or (gate == "QUALIFICATION" and x["reason"] == "SUPPORTED")
                for x in payload["reasons"]
            ):
                raise SupplyDenied("UNRESOLVED_GATE")
            # A stale known support cannot become a fabricated no-email failure.
            stale = await count(
                c,
                s.contacts,
                batch["experiment_id"],
                s.contacts.c.outcome == "SUPPORTED",
                s.contacts.c.valid_until <= self.clock(),
            )
            if stale:
                raise SupplyDenied("STALE_EVIDENCE")
            feedback_id = None
            if gate == "EMAIL" and payload["deficit"] <= 0:
                stage = "QUALIFICATION"
            elif (gate == "EMAIL" and batch["slot"] == 2) or (
                gate == "QUALIFICATION" and batch["slot"] == 3
            ):
                stage = "DONE"
                await finish(
                    c,
                    batch["experiment_id"],
                    "EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2"
                    if gate == "EMAIL"
                    else "QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3",
                    key,
                )
            else:
                feedback_id = uuid4()
                await c.execute(
                    insert(s.feedback).values(
                        id=feedback_id,
                        experiment_id=batch["experiment_id"],
                        batch_id=batch_id,
                        gate=gate,
                        payload=payload,
                    )
                )
                stage = (
                    "EMAIL_RETRY_READY"
                    if gate == "EMAIL"
                    else "QUALIFICATION_RETRY_READY"
                )
            await c.execute(
                update(s.batches)
                .where(s.batches.c.id == batch_id)
                .values(
                    stage=stage,
                    **(
                        {"completed_at": self.clock()}
                        if stage
                        in {"EMAIL_RETRY_READY", "QUALIFICATION_RETRY_READY", "DONE"}
                        else {}
                    ),
                )
            )
            await c.execute(
                insert(s.closures).values(
                    command_key=key,
                    experiment_id=batch["experiment_id"],
                    batch_id=batch_id,
                    gate=gate,
                    feedback_id=feedback_id,
                )
            )
            return feedback_id

    @safe
    async def accept_qualification(self, candidate_id: UUID, fact_id: UUID) -> str:
        async with self.engine.begin() as c:
            candidate = await row(c, s.candidates, "id", candidate_id)
            root = await locked(c, candidate["experiment_id"])
            prior = await maybe(c, s.qualifications, "candidate_id", candidate_id)
            if prior:
                if prior["fact_id"] != fact_id:
                    raise SupplyDenied("QUALIFICATION_CONFLICT")
                return prior["outcome"]
            active(root, self.clock())
            contact = await row(c, s.contacts, "candidate_id", candidate_id)
            proof = await row(c, s.facts, "id", fact_id)
            valid(proof, self.clock())
            if self.clock() >= contact["valid_until"]:
                raise SupplyDenied("STALE_EVIDENCE")
            await self._supported(c, candidate["experiment_id"], self.clock())
            await c.execute(
                insert(s.qualifications).values(
                    candidate_id=candidate_id,
                    experiment_id=candidate["experiment_id"],
                    fact_id=fact_id,
                    accepted_at=self.clock(),
                    outcome=proof["kind"],
                )
            )
            return proof["kind"]

    @safe
    async def bind_operation(
        self,
        attribution: CallAttribution,
        batch_id: UUID,
        kind: Literal["DISCOVERY", "CONTACT", "DEEP"],
        config_id: UUID,
        candidate_id: UUID | None = None,
    ) -> None:
        async with self.engine.begin() as c:
            root = await locked(c, attribution.experiment_id)
            data = {
                "operation_id": attribution.operation_run_id,
                "experiment_id": attribution.experiment_id,
                "workflow_id": attribution.workflow_run_id,
                "config_version": attribution.config_version,
                "config_id": config_id,
                "batch_id": batch_id,
                "kind": kind,
                "candidate_id": candidate_id,
            }
            prior = await maybe(
                c, s.operations, "operation_id", attribution.operation_run_id
            )
            if prior:
                if dict(prior) != data:
                    raise SupplyDenied("OPERATION_CONFLICT")
                return
            active(root, self.clock())
            await self._work_gate(c, attribution.operation_run_id, kind)
            await c.execute(insert(s.operations).values(**data))
            await self._admit(c, attribution, "RESERVE")

    async def _work_gate(self, c, operation_id, kind):
        expected = {"DISCOVERY": "SUPPLY", "DEEP": "SUPPLY", "CONTACT": "CONTACT"}.get(
            kind
        )
        operation = await row(c, gov.operations, "id", operation_id)
        if expected is None or operation["gate_kind"] != expected:
            raise SupplyDenied("WORK_GATE")
        return expected

    async def _admit(self, c, attr, phase, *, expected_gate=None):
        root = await row(c, s.plans, "experiment_id", attr.experiment_id)
        active(root, self.clock())
        binding = await row(c, s.operations, "operation_id", attr.operation_run_id)
        if (
            binding["experiment_id"] != attr.experiment_id
            or binding["workflow_id"] != attr.workflow_run_id
            or binding["config_version"] != attr.config_version
        ):
            raise SupplyDenied("OPERATION_SCOPE")
        gate = await self._work_gate(c, attr.operation_run_id, binding["kind"])
        if expected_gate is not None and gate != expected_gate:
            raise SupplyDenied("WORK_GATE")
        batch = await row(c, s.batches, "id", binding["batch_id"])
        upper = root["deadline"]
        if binding["kind"] == "DISCOVERY":
            if (
                batch["stage"] != "CONTACT"
                or await count(
                    c,
                    s.candidates,
                    attr.experiment_id,
                    s.candidates.c.batch_id == batch["id"],
                )
                >= 100
            ):
                raise SupplyDenied("DISCOVERY_GATE")
        else:
            candidate = await row(c, s.candidates, "id", binding["candidate_id"])
            if candidate["stopped"]:
                raise SupplyDenied("CANDIDATE_STOPPED")
            identity = await row(c, s.identities, "id", candidate["identity_id"])
            clearance = await row(c, s.facts, "id", candidate["clearance_id"])
            for proof in (identity, clearance):
                valid(proof, self.clock())
                upper = min(upper, proof["valid_until"])
            if clearance["kind"] != "IDENTITY_CLEAR":
                raise SupplyDenied("IDENTITY_EXCLUDED")
            if binding["kind"] == "CONTACT":
                if (
                    candidate["batch_id"] != batch["id"]
                    or batch["stage"] != "CONTACT"
                    or await maybe(c, s.contacts, "candidate_id", candidate["id"])
                ):
                    raise SupplyDenied("CONTACT_GATE")
            else:
                if batch["stage"] != "QUALIFICATION" or await maybe(
                    c, s.qualifications, "candidate_id", candidate["id"]
                ):
                    raise SupplyDenied("QUALIFICATION_GATE")
                contact = await row(c, s.contacts, "candidate_id", candidate["id"])
                if contact["outcome"] != "SUPPORTED":
                    raise SupplyDenied("EMAIL_NOT_FOUND")
                upper = min(
                    upper,
                    contact["valid_until"],
                    await self._supported(c, attr.experiment_id, self.clock()),
                )
        if attr.deadline > upper or self.clock() >= attr.deadline:
            raise SupplyDenied("DEADLINE_BOUND")
        if phase == "DISPATCH" and binding["kind"] == "DEEP":
            await c.execute(
                update(s.candidates)
                .where(s.candidates.c.id == binding["candidate_id"])
                .values(deep_started=True)
            )

    @safe
    async def stop(
        self, experiment_id: UUID, reason: StopReason, command_key: UUID
    ) -> SupplySnapshot:
        if reason not in {
            "CANCELLED",
            "BUDGET_EXHAUSTED",
            "DEADLINE_EXHAUSTED",
            "SOURCE_FAILURE",
            "PROVIDER_FAILURE",
            "SEARCH_EXHAUSTED",
            "SAFETY_STOP",
        }:
            raise SupplyDenied("STOP_REASON")
        async with self.engine.begin() as c:
            root = await locked(c, experiment_id)
            prior = await maybe(c, s.outcomes, "experiment_id", experiment_id)
            if prior:
                if prior["command_key"] != command_key or prior["reason"] != reason:
                    raise SupplyDenied("TERMINAL")
            else:
                if root["state"] != "ACTIVE":
                    raise SupplyDenied("TERMINAL")
                await finish(c, experiment_id, reason, command_key)
        return await self.snapshot(experiment_id)

    @safe
    async def snapshot(self, experiment_id: UUID) -> SupplySnapshot:
        async with self.engine.begin() as c:
            root = await locked(c, experiment_id)
            await c.execute(
                text("SELECT set_config('alon.organization_now',:now,true)"),
                {"now": self.clock().isoformat()},
            )
            slots = tuple(
                (
                    await c.execute(
                        select(s.batches.c.slot)
                        .where(s.batches.c.experiment_id == experiment_id)
                        .order_by(s.batches.c.slot)
                    )
                ).scalars()
            )
            return SupplySnapshot(
                experiment_id=experiment_id,
                state=root["state"],
                batches_used=len(slots),
                logical_slots=slots,
                businesses_discovered=await count(c, s.candidates, experiment_id),
                supported_emails=await count(
                    c,
                    s.contacts,
                    experiment_id,
                    s.contacts.c.outcome == "SUPPORTED",
                    s.contacts.c.valid_until > self.clock(),
                ),
                current_qualified_contactable=(
                    await c.execute(
                        select(func.count())
                        .select_from(
                            s.current_qualifications.join(
                                s.contacts,
                                s.contacts.c.candidate_id
                                == s.current_qualifications.c.candidate_id,
                            ).join(
                                s.facts,
                                s.facts.c.id == s.current_qualifications.c.fact_id,
                            )
                        )
                        .where(
                            s.current_qualifications.c.experiment_id == experiment_id,
                            s.current_qualifications.c.outcome == "QUALIFIED",
                            s.contacts.c.valid_until > self.clock(),
                            s.facts.c.valid_until > self.clock(),
                        )
                    )
                ).scalar_one(),
                accepted=await count(
                    c,
                    s.current_qualifications,
                    experiment_id,
                    s.current_qualifications.c.outcome == "QUALIFIED",
                ),
            )


class SupplyAdmissionHook:
    """Standalone SUPPLY owner. CONTACT requires ComposedContactSupplyHook."""

    def __init__(self, repository: CampaignSupplyRepository):
        self.repository = repository

    async def admit(
        self,
        connection: AsyncConnection,
        attribution: CallAttribution,
        call_id: UUID,
        phase: str,
    ) -> None:
        try:
            if phase not in {"RESERVE", "DISPATCH"}:
                raise SupplyDenied("PHASE")
            await self.repository._admit(
                connection, attribution, phase, expected_gate="SUPPLY"
            )
        except SupplyDenied:
            raise AccountingDenied(Reason.GATE) from None


class ComposedContactSupplyHook:
    """Required CONTACT owner plus supply checks in the same fenced transaction.

    Task5 supplies the SQL-only contact owner implementing source precedence,
    identity/contact proof validity and its own complete deadline attenuation.
    The owner must not commit, perform network I/O or acquire experiment roots
    out of order. Neither possessing this wrapper nor provider credentials
    supplies those missing contact rules. Supply claims run exactly once, after
    the owner's SQL decision, and all changes roll back on either denial.
    """

    def __init__(
        self, repository: CampaignSupplyRepository, *, contact_owner: AdmissionHook
    ):
        if contact_owner is None:
            raise ValueError("contact admission owner required")
        self.repository = repository
        self.contact_owner = contact_owner

    async def admit(
        self,
        connection: AsyncConnection,
        attribution: CallAttribution,
        call_id: UUID,
        phase: str,
    ) -> None:
        reason = Reason.GATE
        try:
            if phase not in {"RESERVE", "DISPATCH"}:
                raise SupplyDenied("PHASE")
            binding = await row(
                connection, s.operations, "operation_id", attribution.operation_run_id
            )
            if binding["kind"] != "CONTACT":
                raise SupplyDenied("WORK_GATE")
            await self.repository._work_gate(
                connection, attribution.operation_run_id, "CONTACT"
            )
            await self.contact_owner.admit(connection, attribution, call_id, phase)
            await self.repository._admit(
                connection, attribution, phase, expected_gate="CONTACT"
            )
            return
        except AccountingDenied as error:
            reason = error.reason
        except Exception:  # noqa: BLE001 — sanitize faulty trusted-owner boundaries
            # A faulty trusted owner must not expose an upstream exception body
            # or continue a paid call. Raise outside the handler to drop context.
            reason = Reason.GATE
        raise AccountingDenied(reason)
