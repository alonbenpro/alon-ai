"""Durable L02 contact-source precedence and SQL-only provider admission.

This module binds provisional supply facts to governed provider calls. It owns no
organization, address, lead, cohort, send, booking, or qualification schema.
Provider content remains runtime-only; durable rows contain identities and enums.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from functools import wraps
from typing import Literal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    UniqueConstraint,
    insert,
    select,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.accounting.models import (
    AccountingDenied,
    CallState,
    CapabilityConfig,
    Reason,
)
from alon_ai.accounting.repository import GovernanceRepository, lock_experiment
from alon_ai.policies.campaign_supply import SupplyDenied
from alon_ai.providers.contracts import (
    CallAttribution,
    Capability,
    ContentField,
    EmailPresence,
    ProviderResultMetadata,
    StrictDTO,
    VerificationStatus,
)
from alon_ai.providers.execution import ExecutionResult
from alon_ai.providers.rights import (
    GrantEvent,
    GrantEventKind,
    ProviderUsageGrant,
    RuntimeContent,
)
from alon_ai.supply import schema as supply_schema
from alon_ai.supply.repository import CampaignSupplyRepository


def _table(name: str, *columns) -> Table:
    return Table("contact_" + name, gov.metadata, *columns)


cases = _table(
    "cases",
    gov.col("candidate_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("source_fact_id", gov.U),
    gov.col("brave_call_id", gov.U, unique=True),
    gov.col("result_evidence_id", gov.U, unique=True),
    gov.col("config_id", gov.U),
    gov.col("config_version", gov.U),
    gov.col("grant_id", gov.U),
    gov.col("grant_version", Integer),
    gov.col("presence", String),
    gov.col("decision", String),
    gov.col("command_key", gov.U, unique=True),
    gov.col("observed_at", gov.T),
    gov.col("valid_until", gov.T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(["brave_call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
    ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
    ForeignKeyConstraint(
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
    UniqueConstraint("candidate_id", "experiment_id"),
    CheckConstraint("observed_at < valid_until"),
    gov.enumcheck("presence", list(EmailPresence)),
    gov.enumcheck("decision", ["AVOIDED_HUNTER", "FALLBACK_ALLOWED", "PAUSED"]),
    CheckConstraint(
        "(presence='PRESENT' AND decision='AVOIDED_HUNTER') OR "
        "(presence='ABSENT' AND decision='FALLBACK_ALLOWED') OR "
        "(presence='NOT_AVAILABLE' AND decision='PAUSED')"
    ),
)

operations = _table(
    "operations",
    gov.col("operation_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("candidate_id", gov.U),
    gov.col("config_id", gov.U),
    gov.col("config_version", gov.U),
    gov.col("case_id", gov.U, nullable=True),
    gov.col("source_fact_id", gov.U, nullable=True),
    gov.col("verification_policy_id", gov.U, nullable=True),
    gov.col("capability", String),
    ForeignKeyConstraint(["operation_id"], ["supply_operations.operation_id"]),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["case_id", "experiment_id"],
        ["contact_cases.candidate_id", "contact_cases.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["verification_policy_id", "experiment_id"],
        ["supply_references.id", "supply_references.experiment_id"],
    ),
    ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
    UniqueConstraint("operation_id", "candidate_id", "experiment_id"),
    gov.enumcheck(
        "capability",
        [
            Capability.BRAVE_LOCAL_DISCOVERY,
            Capability.BRAVE_COMPANY_DISCOVERY,
            Capability.HUNTER_DOMAIN_SEARCH,
            Capability.HUNTER_EMAIL_FINDER,
            Capability.HUNTER_COMPANY_ENRICHMENT,
            Capability.HUNTER_PERSON_ENRICHMENT,
            Capability.HUNTER_EMAIL_VERIFICATION,
        ],
    ),
    CheckConstraint(
        "(capability IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY') "
        "AND case_id IS NULL AND source_fact_id IS NULL AND verification_policy_id IS NULL) OR "
        "(capability IN ('HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT') "
        "AND case_id IS NOT NULL AND source_fact_id IS NULL AND verification_policy_id IS NULL) OR "
        "(capability='HUNTER_EMAIL_VERIFICATION' AND case_id IS NOT NULL "
        "AND source_fact_id IS NOT NULL AND verification_policy_id IS NOT NULL)"
    ),
)

attempts = _table(
    "attempts",
    gov.col("call_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("operation_id", gov.U),
    gov.col("candidate_id", gov.U),
    gov.col("result_evidence_id", gov.U, unique=True),
    gov.col("output_fact_id", gov.U, nullable=True),
    gov.col("outcome", String),
    gov.col("command_key", gov.U, unique=True),
    gov.col("observed_at", gov.T),
    gov.col("valid_until", gov.T),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(
        ["operation_id", "candidate_id", "experiment_id"],
        [
            "contact_operations.operation_id",
            "contact_operations.candidate_id",
            "contact_operations.experiment_id",
        ],
    ),
    ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
    ForeignKeyConstraint(
        ["output_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    UniqueConstraint("output_fact_id"),
    CheckConstraint("observed_at < valid_until"),
    gov.enumcheck(
        "outcome",
        [
            "FOUND",
            "NOT_FOUND",
            "VALID",
            "INVALID",
            "ACCEPT_ALL",
            "UNKNOWN",
            "TEMPORARY_FAILURE",
            "TRANSIENT",
        ],
    ),
)

CONTACT_TABLES = (cases, operations, attempts)


class ContactDecision(StrEnum):
    AVOIDED_HUNTER = "AVOIDED_HUNTER"
    FALLBACK_ALLOWED = "FALLBACK_ALLOWED"
    PAUSED = "PAUSED"


class ContactDecisionReceipt(StrictDTO):
    candidate_id: UUID
    presence: EmailPresence
    decision: ContactDecision
    counterfactual_savings: Literal["UNAVAILABLE"] = "UNAVAILABLE"


class ContactPolicyDenied(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__("contact policy denied: " + reason)


def _safe[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    async def run(*args: P.args, **kwargs: P.kwargs):
        try:
            return await function(*args, **kwargs)  # type: ignore[misc]
        except ContactPolicyDenied:
            raise
        except (
            SQLAlchemyError,
            AccountingDenied,
            SupplyDenied,
            PermissionError,
            ValueError,
            TypeError,
        ):
            pass
        raise ContactPolicyDenied("INVALID_STATE")

    return run  # type: ignore[return-value]


def _metadata(value: object) -> ProviderResultMetadata:
    return ProviderResultMetadata.model_validate_json(json.dumps(value, default=str))


def _fields(
    content: RuntimeContent,
    grant: ProviderUsageGrant,
    events: tuple[GrantEvent, ...],
    now: datetime,
):
    return content.retain(current_grant=grant, events=events, now=now).fields


def observe_email_presence(
    content: RuntimeContent,
    grant: ProviderUsageGrant,
    events: tuple[GrantEvent, ...],
    *,
    now: datetime,
) -> EmailPresence:
    """Inspect only currently licensed EMAIL content; never return the address."""
    values = _fields(content, grant, events, now).get(ContentField.EMAIL, ())
    return EmailPresence.PRESENT if values else EmailPresence.ABSENT


def observe_verification_status(
    content: RuntimeContent,
    grant: ProviderUsageGrant,
    events: tuple[GrantEvent, ...],
    *,
    now: datetime,
) -> VerificationStatus:
    """Parse an exact licensed verifier status; malformed content stays UNKNOWN."""
    values = _fields(content, grant, events, now).get(ContentField.TEXT, ())
    if len(values) != 1:
        return VerificationStatus.UNKNOWN
    try:
        return VerificationStatus(values[0])
    except ValueError:
        return VerificationStatus.UNKNOWN


async def _one(connection: AsyncConnection, table: Table, key: str, value: object):
    row = (
        (await connection.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ContactPolicyDenied("MISSING_PROOF")
    return row


class ContactPolicyRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        supply: CampaignSupplyRepository,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.supply = supply
        self.clock = clock
        # Reuse Task3's exact current-grant/supersession/event evaluation on the
        # active connection. This instance performs no transaction of its own.
        self.governance = GovernanceRepository(engine, clock=clock)

    @_safe
    async def bind_operation(
        self,
        attribution: CallAttribution,
        candidate_id: UUID,
        config_id: UUID,
        *,
        source_case_id: UUID | None = None,
        source_fact_id: UUID | None = None,
    ) -> None:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, attribution.experiment_id)
            supply_op = await _one(
                connection,
                supply_schema.operations,
                "operation_id",
                attribution.operation_run_id,
            )
            config = await _one(connection, gov.configs, "id", config_id)
            capability = Capability(config["capability"])
            allowed = {
                Capability.BRAVE_LOCAL_DISCOVERY,
                Capability.BRAVE_COMPANY_DISCOVERY,
                Capability.HUNTER_DOMAIN_SEARCH,
                Capability.HUNTER_EMAIL_FINDER,
                Capability.HUNTER_COMPANY_ENRICHMENT,
                Capability.HUNTER_PERSON_ENRICHMENT,
                Capability.HUNTER_EMAIL_VERIFICATION,
            }
            if capability not in allowed or any(
                supply_op[key] != value
                for key, value in {
                    "experiment_id": attribution.experiment_id,
                    "candidate_id": candidate_id,
                    "config_id": config_id,
                    "config_version": attribution.config_version,
                    "kind": "CONTACT",
                }.items()
            ):
                raise ContactPolicyDenied("OPERATION_SCOPE")
            brave = capability in {
                Capability.BRAVE_LOCAL_DISCOVERY,
                Capability.BRAVE_COMPANY_DISCOVERY,
            }
            verifier = capability is Capability.HUNTER_EMAIL_VERIFICATION
            if brave and (source_case_id is not None or source_fact_id is not None):
                raise ContactPolicyDenied("OPERATION_SHAPE")
            if not brave:
                case = await _one(connection, cases, "candidate_id", source_case_id)
                if case["candidate_id"] != candidate_id:
                    raise ContactPolicyDenied("OPERATION_SCOPE")
            policy_id = None
            if verifier:
                source = await _one(
                    connection, supply_schema.facts, "id", source_fact_id
                )
                candidate = await _one(
                    connection, supply_schema.candidates, "id", candidate_id
                )
                if (
                    source["kind"] != "SOURCE_EMAIL"
                    or source["identity_id"] != candidate["identity_id"]
                ):
                    raise ContactPolicyDenied("BUSINESS_MATCH")
                policy_id = (
                    await _one(
                        connection,
                        supply_schema.plans,
                        "experiment_id",
                        attribution.experiment_id,
                    )
                )["verification_policy_id"]
            elif source_fact_id is not None:
                raise ContactPolicyDenied("OPERATION_SHAPE")
            data = {
                "operation_id": attribution.operation_run_id,
                "experiment_id": attribution.experiment_id,
                "candidate_id": candidate_id,
                "config_id": config_id,
                "config_version": attribution.config_version,
                "case_id": source_case_id,
                "source_fact_id": source_fact_id,
                "verification_policy_id": policy_id,
                "capability": capability,
            }
            prior = (
                (
                    await connection.execute(
                        select(operations).where(
                            operations.c.operation_id == attribution.operation_run_id
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                if dict(prior) != data:
                    raise ContactPolicyDenied("OPERATION_CONFLICT")
                return
            await connection.execute(insert(operations).values(**data))

    @_safe
    async def record_source(
        self,
        candidate_id: UUID,
        source_fact_id: UUID,
        result: ExecutionResult,
        command_key: UUID,
    ) -> ContactDecisionReceipt:
        if not isinstance(result, ExecutionResult):
            raise ContactPolicyDenied("EXECUTION_RESULT")
        brave_call_id = result.receipt.call_id
        async with self.engine.begin() as connection:
            call = await _one(connection, gov.calls, "id", brave_call_id)
            await lock_experiment(connection, call["experiment_id"])
            operation = await _one(
                connection, operations, "operation_id", call["operation_id"]
            )
            candidate = await _one(
                connection, supply_schema.candidates, "id", candidate_id
            )
            source = await _one(connection, supply_schema.facts, "id", source_fact_id)
            proof = (
                (
                    await connection.execute(
                        select(gov.evidence).where(
                            gov.evidence.c.call_id == brave_call_id,
                            gov.evidence.c.kind == "PROVIDER_RESULT",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if proof is None or any(
                operation[key] != value
                for key, value in {
                    "candidate_id": candidate_id,
                    "config_id": call["config_id"],
                    "config_version": call["config_version"],
                    "capability": call["result_metadata"]["capability"]
                    if call["result_metadata"]
                    else operation["capability"],
                }.items()
            ):
                raise ContactPolicyDenied("SOURCE_SCOPE")
            capability = Capability(operation["capability"])
            if (
                capability
                not in {
                    Capability.BRAVE_LOCAL_DISCOVERY,
                    Capability.BRAVE_COMPANY_DISCOVERY,
                }
                or source["identity_id"] != candidate["identity_id"]
            ):
                raise ContactPolicyDenied("SOURCE_SCOPE")
            if result.receipt.state is not CallState.FINAL or call["state"] != "FINAL":
                raise ContactPolicyDenied("SOURCE_STATUS")
            context = await _source_context(connection, brave_call_id)
            await _lock_source_authority(connection, context)
            now = self.clock()
            grant, events = await self.governance._rights(
                connection,
                context[1],
                now,
                (call["grant_id"], call["grant_version"]),
            )
            metadata = (
                _metadata(call["result_metadata"]) if call["result_metadata"] else None
            )
            if (
                metadata is not None
                and metadata.status == "SUCCEEDED"
                and result.content is not None
            ):
                presence = observe_email_presence(
                    result.content, grant, events, now=now
                )
            else:
                presence = EmailPresence.NOT_AVAILABLE
            decision = {
                EmailPresence.PRESENT: ContactDecision.AVOIDED_HUNTER,
                EmailPresence.ABSENT: ContactDecision.FALLBACK_ALLOWED,
                EmailPresence.NOT_AVAILABLE: ContactDecision.PAUSED,
            }[presence]
            expected_kind = {
                EmailPresence.PRESENT: "SOURCE_EMAIL",
                EmailPresence.ABSENT: "EMAIL_ABSENT",
                EmailPresence.NOT_AVAILABLE: "SOURCE_FAILURE",
            }[presence]
            if source["kind"] != expected_kind:
                raise ContactPolicyDenied("SOURCE_FACT")
            observed_at = (
                metadata.finished_at
                if metadata
                else call["finished_at"] or call["created_at"]
            )
            valid_until = min(
                source["valid_until"],
                grant.expires_at,
                CallAttribution.model_validate_json(
                    json.dumps(call["attribution"], default=str)
                ).deadline,
            )
            data = {
                "candidate_id": candidate_id,
                "experiment_id": call["experiment_id"],
                "source_fact_id": source_fact_id,
                "brave_call_id": brave_call_id,
                "result_evidence_id": proof["id"],
                "config_id": call["config_id"],
                "config_version": call["config_version"],
                "grant_id": call["grant_id"],
                "grant_version": call["grant_version"],
                "presence": presence,
                "decision": decision,
                "command_key": command_key,
                "observed_at": observed_at,
                "valid_until": valid_until,
            }
            prior = (
                (
                    await connection.execute(
                        select(cases).where(
                            (cases.c.candidate_id == candidate_id)
                            | (cases.c.command_key == command_key)
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                if dict(prior) != data:
                    raise ContactPolicyDenied("SOURCE_CONFLICT")
            else:
                await connection.execute(insert(cases).values(**data))
        return ContactDecisionReceipt(
            candidate_id=candidate_id, presence=presence, decision=decision
        )

    @_safe
    async def record_attempt(
        self,
        result: ExecutionResult,
        command_key: UUID,
        *,
        output_fact_id: UUID | None = None,
    ) -> None:
        if not isinstance(result, ExecutionResult):
            raise ContactPolicyDenied("EXECUTION_RESULT")
        call_id = result.receipt.call_id
        async with self.engine.begin() as connection:
            call = await _one(connection, gov.calls, "id", call_id)
            await lock_experiment(connection, call["experiment_id"])
            operation = await _one(
                connection, operations, "operation_id", call["operation_id"]
            )
            case = await _one(connection, cases, "candidate_id", operation["case_id"])
            proof = (
                (
                    await connection.execute(
                        select(gov.evidence).where(
                            gov.evidence.c.call_id == call_id,
                            gov.evidence.c.kind == "PROVIDER_RESULT",
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                proof is None
                or call["state"] != "FINAL"
                or result.receipt.state is not CallState.FINAL
            ):
                raise ContactPolicyDenied("ATTEMPT_STATUS")
            metadata = _metadata(call["result_metadata"])
            capability = Capability(operation["capability"])
            verifier = capability is Capability.HUNTER_EMAIL_VERIFICATION
            context = await _source_context(connection, call_id)
            await _lock_source_authority(connection, context)
            now = self.clock()
            grant, events = await self.governance._rights(
                connection,
                context[1],
                now,
                (call["grant_id"], call["grant_version"]),
            )
            if metadata.status != "SUCCEEDED" or result.content is None:
                outcome = "TRANSIENT"
            elif verifier:
                outcome = observe_verification_status(
                    result.content, grant, events, now=now
                ).value
            else:
                outcome = (
                    "FOUND"
                    if observe_email_presence(result.content, grant, events, now=now)
                    is EmailPresence.PRESENT
                    else "NOT_FOUND"
                )
            allowed_outcomes = (
                {
                    "VALID",
                    "INVALID",
                    "ACCEPT_ALL",
                    "UNKNOWN",
                    "TEMPORARY_FAILURE",
                    "TRANSIENT",
                }
                if verifier
                else {"FOUND", "NOT_FOUND", "TRANSIENT"}
            )
            if outcome not in allowed_outcomes:
                raise ContactPolicyDenied("ATTEMPT_OUTCOME")
            output = None
            if output_fact_id is not None:
                output = await _one(
                    connection, supply_schema.facts, "id", output_fact_id
                )
            expected = (
                "VERIFIED"
                if outcome == "VALID"
                else "VERIFICATION_REJECTED"
                if verifier and outcome in {"INVALID", "ACCEPT_ALL", "UNKNOWN"}
                else "SOURCE_EMAIL"
                if not verifier and outcome == "FOUND"
                else None
            )
            if (expected is None) != (output is None) or (
                output is not None
                and (
                    output["kind"] != expected
                    or output["identity_id"]
                    != (
                        await _one(
                            connection,
                            supply_schema.candidates,
                            "id",
                            operation["candidate_id"],
                        )
                    )["identity_id"]
                    or (
                        verifier
                        and (
                            output["contact_ref"] != operation["source_fact_id"]
                            or output["policy_ref"]
                            != operation["verification_policy_id"]
                        )
                    )
                )
            ):
                raise ContactPolicyDenied("ATTEMPT_FACT")
            observed_at = metadata.finished_at
            valid_until = min(
                case["valid_until"],
                output["valid_until"] if output is not None else case["valid_until"],
                CallAttribution.model_validate_json(
                    json.dumps(call["attribution"], default=str)
                ).deadline,
            )
            data = {
                "call_id": call_id,
                "experiment_id": call["experiment_id"],
                "operation_id": operation["operation_id"],
                "candidate_id": operation["candidate_id"],
                "result_evidence_id": proof["id"],
                "output_fact_id": output_fact_id,
                "outcome": outcome,
                "command_key": command_key,
                "observed_at": observed_at,
                "valid_until": valid_until,
            }
            prior = (
                (
                    await connection.execute(
                        select(attempts).where(
                            (attempts.c.call_id == call_id)
                            | (attempts.c.command_key == command_key)
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                if dict(prior) != data:
                    raise ContactPolicyDenied("ATTEMPT_CONFLICT")
                return
            await connection.execute(insert(attempts).values(**data))

    @_safe
    async def resolve(self, candidate_id: UUID) -> str:
        async with self.engine.begin() as connection:
            candidate = await _one(
                connection, supply_schema.candidates, "id", candidate_id
            )
            await lock_experiment(connection, candidate["experiment_id"])
            case = await _one(connection, cases, "candidate_id", candidate_id)
            if case["decision"] == ContactDecision.PAUSED:
                raise ContactPolicyDenied("PAUSED")
            source_fact_id = case["source_fact_id"]
            selected_source_attempt = None
            if case["decision"] == ContactDecision.FALLBACK_ALLOWED:
                selected_source_attempt = (
                    (
                        await connection.execute(
                            select(attempts)
                            .join(
                                operations,
                                operations.c.operation_id == attempts.c.operation_id,
                            )
                            .where(
                                attempts.c.candidate_id == candidate_id,
                                operations.c.capability.in_(
                                    [x.value for x in _HUNTER_DISCOVERY]
                                ),
                            )
                            .order_by(attempts.c.observed_at.desc())
                            .limit(1)
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if selected_source_attempt is None or selected_source_attempt[
                    "outcome"
                ] in {
                    "TRANSIENT",
                    "TEMPORARY_FAILURE",
                }:
                    raise ContactPolicyDenied("PAUSED")
                if selected_source_attempt["outcome"] == "FOUND":
                    source_fact_id = selected_source_attempt["output_fact_id"]

            verification = None
            verification_fact_id = None
            if not (
                selected_source_attempt is not None
                and selected_source_attempt["outcome"] == "NOT_FOUND"
            ):
                verification = (
                    (
                        await connection.execute(
                            select(attempts)
                            .join(
                                operations,
                                operations.c.operation_id == attempts.c.operation_id,
                            )
                            .where(
                                attempts.c.candidate_id == candidate_id,
                                operations.c.capability
                                == Capability.HUNTER_EMAIL_VERIFICATION,
                                operations.c.source_fact_id == source_fact_id,
                            )
                            .order_by(attempts.c.observed_at.desc())
                            .limit(1)
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if verification is None or verification["outcome"] in {
                    "TRANSIENT",
                    "TEMPORARY_FAILURE",
                }:
                    raise ContactPolicyDenied("PAUSED")
                verification_fact_id = verification["output_fact_id"]

            # Resolve holds no current provider authority initially. Lock the
            # complete dependency chain in one supported order, then sample time.
            contexts = []
            if verification is not None:
                contexts.append(
                    await _source_context(connection, verification["call_id"])
                )
            if selected_source_attempt is not None:
                contexts.append(
                    await _source_context(
                        connection, selected_source_attempt["call_id"]
                    )
                )
            contexts.append(await _source_context(connection, case["brave_call_id"]))
            seen_authorities = set()
            for context in contexts:
                authority = (
                    context[1].intended_use.account_handle,
                    context[1].intended_use.capability,
                )
                if authority not in seen_authorities:
                    await _lock_source_authority(connection, context)
                    seen_authorities.add(authority)
            now = self.clock()
            for call, config in contexts:
                try:
                    await self.governance._rights(
                        connection,
                        config,
                        now,
                        (call["grant_id"], call["grant_version"]),
                    )
                except AccountingDenied:
                    raise ContactPolicyDenied("SOURCE_RIGHTS") from None
            if (
                not case["observed_at"] <= now < case["valid_until"]
                or (
                    selected_source_attempt is not None
                    and not selected_source_attempt["observed_at"]
                    <= now
                    < selected_source_attempt["valid_until"]
                )
                or (
                    verification is not None
                    and not verification["observed_at"]
                    <= now
                    < verification["valid_until"]
                )
            ):
                raise ContactPolicyDenied("STALE_PROOF")
            result = await self.supply._resolve_contact(
                connection,
                candidate_id,
                source_fact_id,
                verification_fact_id,
                now=now,
            )
            return "SUPPORTED" if result == "SUPPORTED" else "EMAIL_NOT_FOUND"


_HUNTER_DISCOVERY = {
    Capability.HUNTER_DOMAIN_SEARCH,
    Capability.HUNTER_EMAIL_FINDER,
    Capability.HUNTER_COMPANY_ENRICHMENT,
    Capability.HUNTER_PERSON_ENRICHMENT,
}


async def _source_context(connection: AsyncConnection, call_id: UUID):
    call = await _one(connection, gov.calls, "id", call_id)
    config_row = await _one(connection, gov.configs, "id", call["config_id"])
    config = CapabilityConfig.model_validate_json(
        json.dumps(config_row["data"], default=str)
    )
    if (
        config.id != call["config_id"]
        or config.version != call["config_version"]
        or config.workflow_id != call["workflow_id"]
    ):
        raise ContactPolicyDenied("SOURCE_CONFIG")
    return call, config


async def _lock_source_authority(connection: AsyncConnection, context) -> None:
    _, config = context
    source_authority = (
        (
            await connection.execute(
                select(gov.authorities)
                .where(
                    gov.authorities.c.account == config.intended_use.account_handle,
                    gov.authorities.c.capability == config.intended_use.capability,
                )
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    if source_authority is None or not source_authority["enabled"]:
        raise ContactPolicyDenied("SOURCE_RIGHTS")


class ContactAdmissionHook:
    """SQL-only CONTACT owner; the composed supply hook runs immediately after it."""

    def __init__(self, repository: ContactPolicyRepository) -> None:
        self.repository = repository

    async def admit(
        self,
        connection: AsyncConnection,
        attribution: CallAttribution,
        call_id: UUID,
        phase: str,
    ) -> None:
        del call_id
        if phase not in {"RESERVE", "DISPATCH"}:
            raise AccountingDenied(Reason.GATE)
        try:
            operation = await _one(
                connection, operations, "operation_id", attribution.operation_run_id
            )
            if any(
                operation[key] != value
                for key, value in {
                    "experiment_id": attribution.experiment_id,
                    "config_version": attribution.config_version,
                }.items()
            ):
                raise ContactPolicyDenied("OPERATION_SCOPE")
            capability = Capability(operation["capability"])
            if capability in {
                Capability.BRAVE_LOCAL_DISCOVERY,
                Capability.BRAVE_COMPANY_DISCOVERY,
            }:
                return
            case = await _one(connection, cases, "candidate_id", operation["case_id"])
            if case["decision"] == "PAUSED":
                raise ContactPolicyDenied("SOURCE_CURRENT")
            source = None
            selected = None
            contexts = []
            if capability in _HUNTER_DISCOVERY:
                if (
                    case["decision"] != "FALLBACK_ALLOWED"
                    or case["presence"] != "ABSENT"
                ):
                    raise ContactPolicyDenied("SOURCE_PRECEDENCE")
            elif capability is Capability.HUNTER_EMAIL_VERIFICATION:
                source = await _one(
                    connection, supply_schema.facts, "id", operation["source_fact_id"]
                )
                candidate = await _one(
                    connection,
                    supply_schema.candidates,
                    "id",
                    operation["candidate_id"],
                )
                plan = await _one(
                    connection,
                    supply_schema.plans,
                    "experiment_id",
                    attribution.experiment_id,
                )
                if (
                    source["kind"] != "SOURCE_EMAIL"
                    or source["identity_id"] != candidate["identity_id"]
                    or operation["verification_policy_id"]
                    != plan["verification_policy_id"]
                ):
                    raise ContactPolicyDenied("BUSINESS_MATCH")
                # Fixed supported order: verifier authority (already held) -> the
                # selected Hunter source (when present) -> original Brave source.
                # Discovery itself uses Hunter -> Brave, so no reverse pair exists.
                if operation["source_fact_id"] != case["source_fact_id"]:
                    selected = (
                        (
                            await connection.execute(
                                select(attempts).where(
                                    attempts.c.output_fact_id
                                    == operation["source_fact_id"],
                                    attempts.c.outcome == "FOUND",
                                )
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if selected is None:
                        raise ContactPolicyDenied("SOURCE_PROVENANCE")
                    contexts.append(
                        await _source_context(connection, selected["call_id"])
                    )
            else:
                raise ContactPolicyDenied("CAPABILITY")
            contexts.append(await _source_context(connection, case["brave_call_id"]))
            seen_authorities = set()
            for context in contexts:
                authority = (
                    context[1].intended_use.account_handle,
                    context[1].intended_use.capability,
                )
                if authority not in seen_authorities:
                    await _lock_source_authority(connection, context)
                    seen_authorities.add(authority)
            now = self.repository.clock()
            upper = case["valid_until"]
            if selected is not None:
                if not selected["observed_at"] <= now < selected["valid_until"]:
                    raise ContactPolicyDenied("SOURCE_CURRENT")
                upper = min(upper, selected["valid_until"])
            for call, config in contexts:
                grant, events = await self.repository.governance._rights(
                    connection,
                    config,
                    now,
                    (call["grant_id"], call["grant_version"]),
                )
                upper = min(upper, grant.expires_at)
                for event in events:
                    if (
                        event.kind is not GrantEventKind.ACTIVATED
                        and event.effective_at > now
                    ):
                        upper = min(upper, event.effective_at)
                # Source authority locks prevent concurrent provisioning. Bound
                # the later accounting lock wait by already scheduled changes.
                future_grants = (
                    await connection.execute(
                        select(gov.grants.c.effective_at).where(
                            gov.grants.c.account == config.intended_use.account_handle,
                            gov.grants.c.capability == config.intended_use.capability,
                            gov.grants.c.effective_at > now,
                        )
                    )
                ).scalars()
                for effective_at in future_grants:
                    upper = min(upper, effective_at)
            if not case["observed_at"] <= now < case["valid_until"]:
                raise ContactPolicyDenied("SOURCE_CURRENT")
            if source is not None:
                if not source["observed_at"] <= now < source["valid_until"]:
                    raise ContactPolicyDenied("SOURCE_CURRENT")
                upper = min(upper, source["valid_until"])
            if attribution.deadline > upper or now >= attribution.deadline:
                raise ContactPolicyDenied("DEADLINE_BOUND")
        except ContactPolicyDenied:
            raise AccountingDenied(Reason.GATE) from None
