"""Lead-readiness persistence without provider transport or response copying.

An evidence link names its provenance exactly as ``provider-result:<uuid>`` or
``independent-source:<uuid>``.  This prevents a dossier excerpt from claiming a
provider result that was never retained under a current source grant.
"""

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.db.repositories.accounting import GovernanceRepository, lock_experiment
from alon_ai.db.repositories.records import (
    _complete,
    _existing,
    _request_hash,
    safe_records,
)
from alon_ai.db.repositories.records_organizations import OrganizationRepository
from alon_ai.db.tables import accounting as governance
from alon_ai.db.tables import records, supply
from alon_ai.db.tables import records_offer as offer
from alon_ai.db.tables import records_organization as organization
from alon_ai.db.tables import records_qualification as qualification
from alon_ai.db.tables import records_readiness as readiness
from alon_ai.db.tables.contact import attempts as contact_attempts
from alon_ai.db.tables.contact import cases as contact_cases
from alon_ai.db.tables.contact import operations as contact_operations
from alon_ai.integrations.schemas.provider import Provider
from alon_ai.policies.provider_rights import RightsMode, evaluate_rights
from alon_ai.provider_usage.schemas.accounting import AccountingDenied, CapabilityConfig
from alon_ai.services.schemas.records import ArtifactKind, ProductRecordsDenied
from alon_ai.services.schemas.records_qualification import LeadEvidenceInput
from alon_ai.services.schemas.records_readiness import (
    ContactabilityDecisionRequest,
    ContactabilityReceipt,
    DiscoveryPlanRequest,
    ProviderResultRequest,
    ReadinessReceipt,
    ResearchEvidenceLinkRequest,
    ResearchPlanRequest,
    ResearchRunRequest,
)


async def _one(connection: AsyncConnection, table, key: str, value: object):
    row = (
        (await connection.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("MISSING_REFERENCE")
    return row


async def _current_offer(connection: AsyncConnection, experiment_id: UUID):
    return (
        (
            await connection.execute(
                select(offer.offer_acceptances)
                .where(offer.offer_acceptances.c.experiment_id == experiment_id)
                .order_by(
                    offer.offer_acceptances.c.accepted_at.desc(),
                    offer.offer_acceptances.c.id.desc(),
                )
                .limit(1)
            )
        )
        .mappings()
        .one_or_none()
    )


async def latest_contactability(connection: AsyncConnection, candidate_id: UUID):
    return (
        (
            await connection.execute(
                select(readiness.contactability_decisions)
                .where(
                    readiness.contactability_decisions.c.candidate_id == candidate_id
                )
                .order_by(readiness.contactability_decisions.c.version.desc())
                .limit(1)
            )
        )
        .mappings()
        .one_or_none()
    )


async def assert_current_contact(connection: AsyncConnection, dossier, now: datetime):
    """Gate consumers on the append-only readiness decision when one exists."""
    contact = await _one(
        connection, supply.contacts, "candidate_id", dossier["candidate_id"]
    )
    source = await _one(
        connection, organization.recipient_sources, "id", dossier["recipient_source_id"]
    )
    if (
        contact["outcome"] != "SUPPORTED"
        or contact["source_id"] != source["source_fact_id"]
        or not contact["resolved_at"] <= now < contact["valid_until"]
    ):
        raise ProductRecordsDenied("STALE_CONTACT")
    decision = await latest_contactability(connection, dossier["candidate_id"])
    if decision is not None and (
        decision["outcome"] != "SUPPORTED_CONTACT_ADDRESS"
        or decision["recipient_source_id"] != source["id"]
        or decision["source_fact_id"] != contact["source_id"]
        or decision["verification_fact_id"] != contact["verification_id"]
        or not decision["decided_at"] <= now < decision["valid_until"]
    ):
        raise ProductRecordsDenied("STALE_CONTACT")
    block = await connection.scalar(
        text("SELECT record_org_block_reason(:org,:recipient,:exp)"),
        {
            "org": dossier["organization_id"],
            "recipient": dossier["recipient_id"],
            "exp": dossier["experiment_id"],
        },
    )
    if block is not None:
        raise ProductRecordsDenied("PROTECTION_CONFLICT")
    permitted = await connection.scalar(
        text("SELECT record_org_source_current(:source,'EMAIL')"),
        {"source": source["retained_id"]},
    )
    if permitted is not True:
        raise ProductRecordsDenied("SOURCE_RIGHTS")
    return contact, decision


async def assert_dossier_research_lineage(
    connection: AsyncConnection, dossier, now: datetime
) -> None:
    """Require linked, still-permitted research only after readiness adopts a lead."""
    plans = tuple(
        (
            await connection.execute(
                select(readiness.research_plans.c.id).where(
                    readiness.research_plans.c.candidate_id == dossier["candidate_id"],
                    readiness.research_plans.c.offer_acceptance_id
                    == dossier["offer_acceptance_id"],
                )
            )
        ).scalars()
    )
    if not plans:
        adopted = await connection.scalar(
            select(readiness.research_plans.c.id).where(
                readiness.research_plans.c.candidate_id == dossier["candidate_id"]
            )
        )
        if (
            adopted is not None
            or await connection.scalar(
                select(readiness.contactability_decisions.c.id)
                .where(
                    readiness.contactability_decisions.c.candidate_id
                    == dossier["candidate_id"]
                )
                .limit(1)
            )
            is not None
        ):
            raise ProductRecordsDenied("MISSING_RESEARCH_PLAN")
        return
    evidence_ids = tuple(
        (
            await connection.execute(
                select(qualification.evidence.c.id).where(
                    qualification.evidence.c.dossier_id == dossier["id"]
                )
            )
        ).scalars()
    )
    linked = tuple(
        (
            await connection.execute(
                select(readiness.evidence_links.c.dossier_evidence_id)
                .join(
                    readiness.research_runs,
                    readiness.research_runs.c.id == readiness.evidence_links.c.run_id,
                )
                .where(
                    readiness.evidence_links.c.dossier_id == dossier["id"],
                    readiness.research_runs.c.plan_id.in_(plans),
                )
            )
        ).scalars()
    )
    if set(linked) != set(evidence_ids):
        raise ProductRecordsDenied("MISSING_RESEARCH_LINEAGE")
    provider_roots = tuple(
        (
            await connection.execute(
                select(
                    readiness.provider_results.c.retained_id,
                    governance.retained.c.field,
                )
                .join(
                    readiness.research_runs,
                    readiness.research_runs.c.provider_result_id
                    == readiness.provider_results.c.id,
                )
                .join(
                    readiness.evidence_links,
                    readiness.evidence_links.c.run_id == readiness.research_runs.c.id,
                )
                .join(
                    governance.retained,
                    governance.retained.c.id
                    == readiness.provider_results.c.retained_id,
                )
                .where(readiness.evidence_links.c.dossier_id == dossier["id"])
            )
        ).all()
    )
    for retained_id, field in provider_roots:
        current = await connection.scalar(
            text("SELECT record_org_source_current(:id,:field)"),
            {"id": retained_id, "field": field},
        )
        if current is not True:
            raise ProductRecordsDenied("SOURCE_RIGHTS")


async def assert_dossier_evidence_input(
    connection: AsyncConnection,
    *,
    candidate_id: UUID,
    offer_acceptance_id: UUID,
    evidence: Sequence[LeadEvidenceInput],
    now: datetime,
) -> None:
    """Reject provider text outside its retained owner before dossier insertion."""
    plans = tuple(
        (
            await connection.execute(
                select(readiness.research_plans.c.id).where(
                    readiness.research_plans.c.candidate_id == candidate_id,
                    readiness.research_plans.c.offer_acceptance_id
                    == offer_acceptance_id,
                )
            )
        ).scalars()
    )
    if not plans:
        adopted = await connection.scalar(
            select(readiness.research_plans.c.id).where(
                readiness.research_plans.c.candidate_id == candidate_id
            )
        )
        if (
            adopted is not None
            or await connection.scalar(
                select(readiness.contactability_decisions.c.id)
                .where(
                    readiness.contactability_decisions.c.candidate_id == candidate_id
                )
                .limit(1)
            )
            is not None
        ):
            raise ProductRecordsDenied("MISSING_RESEARCH_PLAN")
        return
    for item in evidence:
        source_ref, excerpt, valid_until = (
            item.source_ref,
            item.excerpt,
            item.valid_until,
        )
        if source_ref.startswith("provider-result:"):
            try:
                result_id = UUID(source_ref.removeprefix("provider-result:"))
            except ValueError as error:
                raise ProductRecordsDenied("RESEARCH_PROVENANCE") from error
            result = await _one(connection, readiness.provider_results, "id", result_id)
            run = await connection.scalar(
                select(readiness.research_runs.c.id).where(
                    readiness.research_runs.c.plan_id.in_(plans),
                    readiness.research_runs.c.provider_result_id == result_id,
                )
            )
            if (
                run is None
                or result["retained_id"] is None
                or excerpt != f"Retained source: {source_ref}"
                or valid_until > result["valid_until"]
            ):
                raise ProductRecordsDenied("RESEARCH_PROVENANCE")
            field = await connection.scalar(
                select(governance.retained.c.field).where(
                    governance.retained.c.id == result["retained_id"]
                )
            )
            allowed = await connection.scalar(
                text("SELECT record_org_source_current(:id,:field)"),
                {"id": result["retained_id"], "field": field},
            )
            if allowed is not True or valid_until <= now:
                raise ProductRecordsDenied("SOURCE_RIGHTS")
        elif source_ref.startswith("independent-source:"):
            try:
                source_id = UUID(source_ref.removeprefix("independent-source:"))
            except ValueError as error:
                raise ProductRecordsDenied("RESEARCH_PROVENANCE") from error
            source = await _one(connection, supply.references, "id", source_id)
            run = await connection.scalar(
                select(readiness.research_runs.c.id).where(
                    readiness.research_runs.c.plan_id.in_(plans),
                    readiness.research_runs.c.independent_source_id == source_id,
                )
            )
            if source["kind"] != "INDEPENDENT_SOURCE" or run is None:
                raise ProductRecordsDenied("RESEARCH_PROVENANCE")
        else:
            raise ProductRecordsDenied("RESEARCH_PROVENANCE")


class ReadinessRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        lookup_key: SecretStr,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine, self.clock = engine, clock
        self.organizations = OrganizationRepository(
            engine, lookup_key=lookup_key, clock=clock
        )
        self.governance = GovernanceRepository(engine, clock=clock)

    async def _finish(
        self, connection, experiment_id, kind, request_hash, result_id, command_key
    ):
        return await _complete(
            connection,
            command_key=command_key,
            experiment_id=experiment_id,
            kind=kind,
            request_hash=request_hash,
            result_type=kind,
            result_id=result_id,
            now=self.clock(),
        )

    @safe_records
    async def record_provider_result(
        self, request: ProviderResultRequest, *, command_key: UUID
    ) -> ReadinessReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            call = await _one(connection, governance.calls, "id", request.call_id)
            await lock_experiment(connection, call["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection,
                command_key,
                "RECORD_READINESS_PROVIDER_RESULT",
                request_hash,
            )
            if old:
                return ReadinessReceipt(
                    command_id=old["id"], result_id=old["result_id"]
                )
            operation = await _one(
                connection, supply.operations, "operation_id", call["operation_id"]
            )
            evidence = await _one(
                connection, governance.evidence, "id", request.result_evidence_id
            )
            candidate = None
            if request.candidate_id is not None:
                candidate = await _one(
                    connection, supply.candidates, "id", request.candidate_id
                )
            if (
                (
                    candidate is not None
                    and candidate["experiment_id"] != call["experiment_id"]
                )
                or operation["candidate_id"] != (candidate["id"] if candidate else None)
                or operation["batch_id"] != request.batch_id
                or operation["experiment_id"] != call["experiment_id"]
                or call["state"] != "FINAL"
                or evidence["kind"] != "PROVIDER_RESULT"
                or evidence["call_id"] != call["id"]
            ):
                raise ProductRecordsDenied("PROVIDER_RESULT_SCOPE")
            if candidate is None:
                await _one(
                    connection, readiness.discovery_plans, "batch_id", request.batch_id
                )
            config_row = await _one(
                connection, governance.configs, "id", call["config_id"]
            )
            config = CapabilityConfig.model_validate_json(
                json.dumps(config_row["data"], default=str)
            )
            now = self.clock()
            try:
                grant, events = await self.governance._rights(
                    connection, config, now, (call["grant_id"], call["grant_version"])
                )
            except AccountingDenied as error:
                raise ProductRecordsDenied("SOURCE_RIGHTS") from error
            decision = evaluate_rights(grant, events, config.intended_use, now=now)
            if (
                config.version != call["config_version"]
                or decision.mode is not RightsMode.RETAIN_SCOPED_CONTENT
                or (
                    grant.provider is Provider.BRAVE
                    and not grant.outbound_use_permitted
                )
            ):
                raise ProductRecordsDenied("SOURCE_RIGHTS")
            if request.retained_id is not None:
                retained = await _one(
                    connection, governance.retained, "id", request.retained_id
                )
                if (
                    retained["call_id"] != call["id"]
                    or retained["grant_id"] != call["grant_id"]
                    or retained["grant_version"] != call["grant_version"]
                    or retained["expires_at"] <= now
                ):
                    raise ProductRecordsDenied("SOURCE_RIGHTS")
            if decision.retain_until is None:
                raise ProductRecordsDenied("SOURCE_RIGHTS")
            if (
                request.observed_at > now
                or request.valid_until > decision.retain_until
                or request.valid_until <= now
            ):
                raise ProductRecordsDenied("STALE_EVIDENCE")
            await self.organizations._owner(
                connection, call["experiment_id"], request.recorded_by
            )
            result_id = uuid4()
            await connection.execute(
                insert(readiness.provider_results).values(
                    id=result_id,
                    experiment_id=call["experiment_id"],
                    candidate_id=candidate["id"] if candidate else None,
                    batch_id=request.batch_id,
                    call_id=call["id"],
                    operation_id=call["operation_id"],
                    config_id=call["config_id"],
                    config_version=call["config_version"],
                    grant_id=call["grant_id"],
                    grant_version=call["grant_version"],
                    result_evidence_id=evidence["id"],
                    retained_id=request.retained_id,
                    rights_mode="RETAIN_SCOPED_CONTENT",
                    rights_reason="ALLOWED",
                    result_hash=_request_hash(
                        call_id=call["id"],
                        evidence_id=evidence["id"],
                        retained_id=request.retained_id,
                        metadata=call["result_metadata"],
                    ),
                    observed_at=request.observed_at,
                    valid_until=request.valid_until,
                )
            )
            command_id = await self._finish(
                connection,
                call["experiment_id"],
                "RECORD_READINESS_PROVIDER_RESULT",
                request_hash,
                result_id,
                command_key,
            )
            return ReadinessReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def decide_contactability(
        self, request: ContactabilityDecisionRequest, *, command_key: UUID
    ) -> ContactabilityReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            candidate = await _one(
                connection, supply.candidates, "id", request.candidate_id
            )
            await lock_experiment(connection, candidate["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "DECIDE_CONTACTABILITY", request_hash
            )
            if old:
                row = await _one(
                    connection,
                    readiness.contactability_decisions,
                    "id",
                    old["result_id"],
                )
                return ContactabilityReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    outcome=row["outcome"],
                    version=row["version"],
                )
            contact = await _one(
                connection, supply.contacts, "candidate_id", request.candidate_id
            )
            source = None
            if request.recipient_source_id is not None:
                source = await _one(
                    connection,
                    organization.recipient_sources,
                    "id",
                    request.recipient_source_id,
                )
            valid_contact = (
                request.valid_until > self.clock()
                and request.valid_until <= contact["valid_until"]
            )
            supported = (
                source is not None
                and source["experiment_id"] == candidate["experiment_id"]
                and source["candidate_id"] == candidate["id"]
                and contact["source_id"] == source["source_fact_id"]
                and contact["outcome"] == "SUPPORTED"
                and valid_contact
            )
            no_email = (
                source is None
                and contact["outcome"] in {"EMAIL_NOT_FOUND", "VERIFICATION_REJECTED"}
                and valid_contact
            )
            if (request.outcome == "SUPPORTED_CONTACT_ADDRESS" and not supported) or (
                request.outcome == "EMAIL_NOT_FOUND" and not no_email
            ):
                raise ProductRecordsDenied("CONTACTABILITY_LINEAGE")
            no_email_org = None
            if request.outcome == "EMAIL_NOT_FOUND":
                no_email_org = await connection.scalar(
                    select(organization.bindings.c.organization_id)
                    .join(
                        supply.candidates,
                        supply.candidates.c.identity_id
                        == organization.bindings.c.identity_id,
                    )
                    .where(
                        supply.candidates.c.id == candidate["id"],
                        organization.bindings.c.experiment_id
                        == candidate["experiment_id"],
                    )
                )
                if no_email_org is None:
                    raise ProductRecordsDenied("CONTACTABILITY_LINEAGE")
            provider = None
            if request.provider_result_id is not None:
                provider = await _one(
                    connection,
                    readiness.provider_results,
                    "id",
                    request.provider_result_id,
                )
                if (
                    provider["candidate_id"] != candidate["id"]
                    or provider["experiment_id"] != candidate["experiment_id"]
                ):
                    raise ProductRecordsDenied("PROVIDER_RESULT_SCOPE")
            if provider is None:
                raise ProductRecordsDenied("MISSING_CONTACT_VERIFICATION")
            case = await _one(
                connection, contact_cases, "candidate_id", candidate["id"]
            )
            related_calls = {case["brave_call_id"]}
            if contact["verification_id"] is not None:
                expected = (
                    ("VALID",)
                    if request.outcome == "SUPPORTED_CONTACT_ADDRESS"
                    else ("INVALID", "ACCEPT_ALL", "UNKNOWN")
                )
                verification = (
                    await connection.execute(
                        select(contact_attempts.c.call_id)
                        .join(
                            contact_operations,
                            contact_operations.c.operation_id
                            == contact_attempts.c.operation_id,
                        )
                        .where(
                            contact_attempts.c.candidate_id == candidate["id"],
                            contact_attempts.c.output_fact_id
                            == contact["verification_id"],
                            contact_attempts.c.outcome.in_(expected),
                            contact_operations.c.capability
                            == "HUNTER_EMAIL_VERIFICATION",
                            contact_operations.c.source_fact_id == contact["source_id"],
                        )
                    )
                ).scalar_one_or_none()
                if verification is None:
                    raise ProductRecordsDenied("MISSING_CONTACT_VERIFICATION")
                related_calls.add(verification)
            else:
                source_attempt = (
                    await connection.execute(
                        select(contact_attempts.c.call_id).where(
                            contact_attempts.c.candidate_id == candidate["id"],
                            contact_attempts.c.output_fact_id == contact["source_id"],
                            contact_attempts.c.outcome.in_(["FOUND", "NOT_FOUND"]),
                        )
                    )
                ).scalar_one_or_none()
                if request.outcome == "SUPPORTED_CONTACT_ADDRESS" or (
                    case["source_fact_id"] != contact["source_id"]
                    and source_attempt is None
                ):
                    raise ProductRecordsDenied("MISSING_CONTACT_VERIFICATION")
                if source_attempt is not None:
                    related_calls.add(source_attempt)
            if provider["call_id"] not in related_calls:
                raise ProductRecordsDenied("MISSING_CONTACT_VERIFICATION")
            await self.organizations._owner(
                connection, candidate["experiment_id"], request.decided_by
            )
            version = (
                await connection.scalar(
                    select(
                        func.coalesce(
                            func.max(readiness.contactability_decisions.c.version), 0
                        )
                    ).where(
                        readiness.contactability_decisions.c.candidate_id
                        == candidate["id"]
                    )
                )
                or 0
            ) + 1
            result_id, now = uuid4(), self.clock()
            await connection.execute(
                insert(readiness.contactability_decisions).values(
                    id=result_id,
                    experiment_id=candidate["experiment_id"],
                    candidate_id=candidate["id"],
                    organization_id=source["organization_id"]
                    if source
                    else no_email_org,
                    recipient_id=source["recipient_id"] if source else None,
                    recipient_source_id=source["id"] if source else None,
                    source_fact_id=contact["source_id"] if source else None,
                    verification_fact_id=contact["verification_id"] if source else None,
                    provider_result_id=provider["id"] if provider else None,
                    version=version,
                    outcome=request.outcome,
                    reason_code=request.reason_code,
                    payload_hash=request_hash,
                    decided_by=request.decided_by,
                    decided_at=now,
                    valid_until=request.valid_until,
                )
            )
            command_id = await self._finish(
                connection,
                candidate["experiment_id"],
                "DECIDE_CONTACTABILITY",
                request_hash,
                result_id,
                command_key,
            )
            return ContactabilityReceipt(
                command_id=command_id,
                result_id=result_id,
                outcome=request.outcome,
                version=version,
            )

    @safe_records
    async def record_research_plan(
        self, request: ResearchPlanRequest, *, command_key: UUID
    ) -> ReadinessReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            acceptance = await _one(
                connection, offer.offer_acceptances, "id", request.offer_acceptance_id
            )
            await lock_experiment(connection, acceptance["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_LEAD_RESEARCH_PLAN", request_hash
            )
            if old:
                return ReadinessReceipt(
                    command_id=old["id"], result_id=old["result_id"]
                )
            candidate = await _one(
                connection, supply.candidates, "id", request.candidate_id
            )
            source = await _one(
                connection,
                organization.recipient_sources,
                "id",
                request.recipient_source_id,
            )
            artifact = await _one(
                connection, records.artifacts, "id", request.artifact.artifact_id
            )
            current = await _current_offer(connection, acceptance["experiment_id"])
            dossier = {
                "candidate_id": candidate["id"],
                "recipient_source_id": source["id"],
                "organization_id": source["organization_id"],
                "recipient_id": source["recipient_id"],
                "experiment_id": acceptance["experiment_id"],
            }
            _, contactability = await assert_current_contact(
                connection, dossier, self.clock()
            )
            if contactability is None:
                raise ProductRecordsDenied("MISSING_CONTACT_VERIFICATION")
            if (
                current is None
                or current["id"] != acceptance["id"]
                or candidate["experiment_id"] != acceptance["experiment_id"]
                or source["candidate_id"] != candidate["id"]
                or artifact["experiment_id"] != acceptance["experiment_id"]
                or artifact["kind"] != ArtifactKind.RESEARCH_PLAN
                or artifact["version"] != request.artifact.version
                or artifact["content_hash"] != request.artifact.content_hash
            ):
                raise ProductRecordsDenied("RESEARCH_PLAN_LINEAGE")
            await self.organizations._owner(
                connection, acceptance["experiment_id"], request.created_by
            )
            criteria = tuple(
                dict(row)
                for row in (
                    await connection.execute(
                        select(offer.qualification_criteria)
                        .where(
                            offer.qualification_criteria.c.profile_id
                            == acceptance["profile_id"]
                        )
                        .order_by(offer.qualification_criteria.c.code)
                    )
                ).mappings()
            )
            if not criteria:
                raise ProductRecordsDenied("MISSING_QUALIFICATION_PROFILE")
            result_id = uuid4()
            await connection.execute(
                insert(readiness.research_plans).values(
                    id=result_id,
                    experiment_id=acceptance["experiment_id"],
                    candidate_id=candidate["id"],
                    organization_id=source["organization_id"],
                    recipient_id=source["recipient_id"],
                    recipient_source_id=source["id"],
                    contactability_id=contactability["id"] if contactability else None,
                    offer_acceptance_id=acceptance["id"],
                    offer_id=acceptance["offer_id"],
                    profile_id=acceptance["profile_id"],
                    policy_id=acceptance["policy_id"],
                    profile_criteria_hash=_request_hash(criteria=criteria),
                    artifact_id=artifact["id"],
                    artifact_kind=artifact["kind"],
                    artifact_version=artifact["version"],
                    artifact_hash=artifact["content_hash"],
                    created_by=request.created_by,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                connection,
                acceptance["experiment_id"],
                "RECORD_LEAD_RESEARCH_PLAN",
                request_hash,
                result_id,
                command_key,
            )
            return ReadinessReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def record_discovery_plan(
        self, request: DiscoveryPlanRequest, *, command_key: UUID
    ) -> ReadinessReceipt:
        """Pin a bounded supply batch to its accepted idea, research and offer."""
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            batch = await _one(connection, supply.batches, "id", request.batch_id)
            await lock_experiment(connection, batch["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_LEAD_DISCOVERY_PLAN", request_hash
            )
            if old:
                return ReadinessReceipt(
                    command_id=old["id"], result_id=old["result_id"]
                )
            acceptance = await _one(
                connection, offer.offer_acceptances, "id", request.offer_acceptance_id
            )
            current = await _current_offer(connection, batch["experiment_id"])
            idea = await _one(
                connection, records.artifacts, "id", request.accepted_idea.artifact_id
            )
            research = await _one(
                connection, records.artifacts, "id", request.market_research.artifact_id
            )
            if (
                current is None
                or current["id"] != acceptance["id"]
                or acceptance["experiment_id"] != batch["experiment_id"]
                or idea["experiment_id"] != batch["experiment_id"]
                or research["experiment_id"] != batch["experiment_id"]
                or idea["kind"] != ArtifactKind.IDEA_BRIEF
                or research["kind"] != ArtifactKind.MARKET_RESEARCH_REPORT
                or any(
                    row[key] != value
                    for row, item in (
                        (idea, request.accepted_idea),
                        (research, request.market_research),
                    )
                    for key, value in (
                        ("version", item.version),
                        ("content_hash", item.content_hash),
                    )
                )
            ):
                raise ProductRecordsDenied("DISCOVERY_PLAN_LINEAGE")
            geographies = tuple(
                UUID(item["value"])
                for item in batch["plan"]["filters"]
                if item["dimension"] == "GEOGRAPHY"
            )
            if set(geographies) != set(request.geography_filter_ids):
                raise ProductRecordsDenied("DISCOVERY_GEOGRAPHY_LINEAGE")
            await self.organizations._owner(
                connection, batch["experiment_id"], request.created_by
            )
            result_id = uuid4()
            await connection.execute(
                insert(readiness.discovery_plans).values(
                    id=result_id,
                    experiment_id=batch["experiment_id"],
                    batch_id=batch["id"],
                    offer_acceptance_id=acceptance["id"],
                    offer_id=acceptance["offer_id"],
                    profile_id=acceptance["profile_id"],
                    policy_id=acceptance["policy_id"],
                    mode=request.mode,
                    geography_filter_ids=list(request.geography_filter_ids),
                    idea_artifact_id=idea["id"],
                    idea_kind=idea["kind"],
                    idea_version=idea["version"],
                    idea_hash=idea["content_hash"],
                    research_artifact_id=research["id"],
                    research_kind=research["kind"],
                    research_version=research["version"],
                    research_hash=research["content_hash"],
                    batch_plan_hash=_request_hash(plan=batch["plan"]),
                    created_by=request.created_by,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                connection,
                batch["experiment_id"],
                "RECORD_LEAD_DISCOVERY_PLAN",
                request_hash,
                result_id,
                command_key,
            )
            return ReadinessReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def complete_research_run(
        self, request: ResearchRunRequest, *, command_key: UUID
    ) -> ReadinessReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            plan = await _one(
                connection, readiness.research_plans, "id", request.plan_id
            )
            await lock_experiment(connection, plan["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "COMPLETE_LEAD_RESEARCH_RUN", request_hash
            )
            if old:
                return ReadinessReceipt(
                    command_id=old["id"], result_id=old["result_id"]
                )
            current = await _current_offer(connection, plan["experiment_id"])
            plan_dossier = {
                "candidate_id": plan["candidate_id"],
                "recipient_source_id": plan["recipient_source_id"],
                "organization_id": plan["organization_id"],
                "recipient_id": plan["recipient_id"],
                "experiment_id": plan["experiment_id"],
            }
            if current is None or current["id"] != plan["offer_acceptance_id"]:
                raise ProductRecordsDenied("STALE_OFFER_VERSION")
            await assert_current_contact(connection, plan_dossier, self.clock())
            if request.provider_result_id is not None:
                root = await _one(
                    connection,
                    readiness.provider_results,
                    "id",
                    request.provider_result_id,
                )
                if (
                    root["candidate_id"] != plan["candidate_id"]
                    or root["experiment_id"] != plan["experiment_id"]
                ):
                    raise ProductRecordsDenied("RESEARCH_PROVENANCE")
            else:
                root = await _one(
                    connection, supply.references, "id", request.independent_source_id
                )
                if (
                    root["experiment_id"] != plan["experiment_id"]
                    or root["kind"] != "INDEPENDENT_SOURCE"
                ):
                    raise ProductRecordsDenied("RESEARCH_PROVENANCE")
            await self.organizations._owner(
                connection, plan["experiment_id"], request.completed_by
            )
            result_id = uuid4()
            await connection.execute(
                insert(readiness.research_runs).values(
                    id=result_id,
                    plan_id=plan["id"],
                    experiment_id=plan["experiment_id"],
                    candidate_id=plan["candidate_id"],
                    provider_result_id=request.provider_result_id,
                    independent_source_id=request.independent_source_id,
                    payload_hash=request_hash,
                    completed_by=request.completed_by,
                    completed_at=self.clock(),
                )
            )
            command_id = await self._finish(
                connection,
                plan["experiment_id"],
                "COMPLETE_LEAD_RESEARCH_RUN",
                request_hash,
                result_id,
                command_key,
            )
            return ReadinessReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def link_research_evidence(
        self, request: ResearchEvidenceLinkRequest, *, command_key: UUID
    ) -> ReadinessReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            run = await _one(connection, readiness.research_runs, "id", request.run_id)
            await lock_experiment(connection, run["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "LINK_LEAD_RESEARCH_EVIDENCE", request_hash
            )
            if old:
                return ReadinessReceipt(
                    command_id=old["id"], result_id=old["result_id"]
                )
            plan = await _one(
                connection, readiness.research_plans, "id", run["plan_id"]
            )
            dossier = await _one(
                connection, qualification.dossiers, "id", request.dossier_id
            )
            evidence = await _one(
                connection, qualification.evidence, "id", request.dossier_evidence_id
            )
            current = await _current_offer(connection, run["experiment_id"])
            if (
                current is None
                or dossier["offer_acceptance_id"] != current["id"]
                or dossier["candidate_id"] != run["candidate_id"]
                or dossier["experiment_id"] != run["experiment_id"]
                or evidence["dossier_id"] != dossier["id"]
                or plan["offer_acceptance_id"] != dossier["offer_acceptance_id"]
            ):
                raise ProductRecordsDenied("RESEARCH_EVIDENCE_LINEAGE")
            await assert_current_contact(connection, dossier, self.clock())
            now = self.clock()
            if evidence["valid_until"] <= now:
                raise ProductRecordsDenied("STALE_EVIDENCE")
            if run["provider_result_id"] is not None:
                root = await _one(
                    connection,
                    readiness.provider_results,
                    "id",
                    run["provider_result_id"],
                )
                if (
                    root["retained_id"] is None
                    or evidence["source_ref"] != f"provider-result:{root['id']}"
                    or evidence["valid_until"] > root["valid_until"]
                ):
                    raise ProductRecordsDenied("RESEARCH_PROVENANCE")
            else:
                if (
                    evidence["source_ref"]
                    != f"independent-source:{run['independent_source_id']}"
                ):
                    raise ProductRecordsDenied("RESEARCH_PROVENANCE")
            await self.organizations._owner(
                connection, run["experiment_id"], request.linked_by
            )
            result_id = uuid4()
            await connection.execute(
                insert(readiness.evidence_links).values(
                    id=result_id,
                    run_id=run["id"],
                    dossier_id=dossier["id"],
                    dossier_evidence_id=evidence["id"],
                    experiment_id=run["experiment_id"],
                    payload_hash=request_hash,
                    linked_by=request.linked_by,
                    linked_at=self.clock(),
                )
            )
            command_id = await self._finish(
                connection,
                run["experiment_id"],
                "LINK_LEAD_RESEARCH_EVIDENCE",
                request_hash,
                result_id,
                command_key,
            )
            return ReadinessReceipt(command_id=command_id, result_id=result_id)
