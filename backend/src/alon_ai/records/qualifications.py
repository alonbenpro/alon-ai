"""Deterministic qualification decisions and atomic protected cohort freezes."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records import offer_schema as offer
from alon_ai.records import organization_schema as org
from alon_ai.records import qualification_schema as q
from alon_ai.records.models import ProductRecordsDenied
from alon_ai.records.organizations import OrganizationRepository
from alon_ai.records.qualification_models import (
    CohortReceipt,
    FreezeCohortRequest,
    LeadDossierReceipt,
    LeadDossierRequest,
    QualificationDecisionReceipt,
    QualificationDecisionRequest,
)
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records
from alon_ai.supply import schema as supply

ACCEPTED = {"QUALIFIED_CONTACTABLE", "PILOT_FIT_CONTACTABLE"}


async def _one(connection, table, key, value):
    row = (
        (await connection.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("MISSING_REFERENCE")
    return row


class QualificationCohortRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        lookup_key: SecretStr,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.clock = clock
        self.organizations = OrganizationRepository(
            engine, lookup_key=lookup_key, clock=clock
        )

    async def _context(self, connection: AsyncConnection) -> None:
        await self.organizations._context(connection)

    async def _current_acceptance(self, connection, experiment_id):
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

    async def _dossier_receipt(self, connection, dossier_id, command_id):
        dossier = await _one(connection, q.dossiers, "id", dossier_id)
        evidence_ids = tuple(
            (
                await connection.execute(
                    select(q.evidence.c.id)
                    .where(q.evidence.c.dossier_id == dossier_id)
                    .order_by(q.evidence.c.code)
                )
            ).scalars()
        )
        return LeadDossierReceipt(
            command_id=command_id,
            result_id=dossier_id,
            id=dossier_id,
            version=dossier["version"],
            evidence_ids=evidence_ids,
        )

    @safe_records
    async def record_dossier(
        self, request: LeadDossierRequest, *, command_key: UUID
    ) -> LeadDossierReceipt:
        async with self.engine.begin() as connection:
            await self._context(connection)
            acceptance = await _one(
                connection, offer.offer_acceptances, "id", request.offer_acceptance_id
            )
            experiment_id = acceptance["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_LEAD_DOSSIER", request_hash
            )
            if old:
                return await self._dossier_receipt(
                    connection, old["result_id"], old["id"]
                )
            candidate = await _one(
                connection, supply.candidates, "id", request.candidate_id
            )
            binding = await _one(connection, org.bindings, "id", request.binding_id)
            admission = await _one(
                connection, org.admissions, "id", request.admission_id
            )
            source = await _one(
                connection, org.recipient_sources, "id", request.recipient_source_id
            )
            if (
                candidate["experiment_id"] != experiment_id
                or binding["experiment_id"] != experiment_id
                or binding["identity_id"] != candidate["identity_id"]
                or admission["binding_id"] != binding["id"]
                or admission["organization_id"] != binding["organization_id"]
                or source["binding_id"] != binding["id"]
                or source["candidate_id"] != candidate["id"]
                or source["organization_id"] != binding["organization_id"]
            ):
                raise ProductRecordsDenied("LINEAGE_MISMATCH")
            await self.organizations._owner(
                connection, experiment_id, request.recorded_by
            )
            version = (
                await connection.scalar(
                    select(func.coalesce(func.max(q.dossiers.c.version), 0)).where(
                        q.dossiers.c.candidate_id == request.candidate_id
                    )
                )
                or 0
            ) + 1
            result_id = uuid4()
            await connection.execute(
                insert(q.dossiers).values(
                    id=result_id,
                    experiment_id=experiment_id,
                    candidate_id=candidate["id"],
                    organization_id=binding["organization_id"],
                    recipient_id=source["recipient_id"],
                    binding_id=binding["id"],
                    admission_id=admission["id"],
                    recipient_source_id=source["id"],
                    offer_acceptance_id=acceptance["id"],
                    offer_id=acceptance["offer_id"],
                    profile_id=acceptance["profile_id"],
                    policy_id=acceptance["policy_id"],
                    version=version,
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(q.evidence),
                [
                    {
                        **item.model_dump(exclude={"schema_version"}),
                        "dossier_id": result_id,
                        "experiment_id": experiment_id,
                    }
                    for item in request.evidence
                ],
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="RECORD_LEAD_DOSSIER",
                request_hash=request_hash,
                result_type="LEAD_DOSSIER",
                result_id=result_id,
                now=self.clock(),
            )
            return await self._dossier_receipt(connection, result_id, command_id)

    async def _decision_receipt(self, connection, decision_id, command_id):
        decision = await _one(connection, q.decisions, "id", decision_id)
        return QualificationDecisionReceipt(
            command_id=command_id,
            result_id=decision_id,
            id=decision_id,
            matrix_id=decision["matrix_id"],
            outcome=decision["outcome"],
            reason_code=decision["reason_code"],
        )

    async def _decision_gate(self, connection, dossier, now):
        current = await self._current_acceptance(connection, dossier["experiment_id"])
        if current is None or current["id"] != dossier["offer_acceptance_id"]:
            raise ProductRecordsDenied("STALE_OFFER_VERSION")
        contact = await _one(
            connection, supply.contacts, "candidate_id", dossier["candidate_id"]
        )
        source = await _one(
            connection,
            org.recipient_sources,
            "id",
            dossier["recipient_source_id"],
        )
        if (
            contact["outcome"] != "SUPPORTED"
            or contact["source_id"] != source["source_fact_id"]
            or not contact["resolved_at"] <= now < contact["valid_until"]
        ):
            raise ProductRecordsDenied("STALE_CONTACT")
        reason = await connection.scalar(
            text("SELECT record_org_block_reason(:org,:recipient,:exp)"),
            {
                "org": dossier["organization_id"],
                "recipient": dossier["recipient_id"],
                "exp": dossier["experiment_id"],
            },
        )
        if reason is not None:
            raise ProductRecordsDenied("PROTECTION_CONFLICT")
        return contact

    @safe_records
    async def decide(
        self, request: QualificationDecisionRequest, *, command_key: UUID
    ) -> QualificationDecisionReceipt:
        async with self.engine.begin() as connection:
            await self._context(connection)
            dossier = await _one(connection, q.dossiers, "id", request.dossier_id)
            experiment_id = dossier["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "DECIDE_LEAD_QUALIFICATION", request_hash
            )
            if old:
                return await self._decision_receipt(
                    connection, old["result_id"], old["id"]
                )
            now = self.clock()
            contact = await self._decision_gate(connection, dossier, now)
            criteria = tuple(
                (
                    await connection.execute(
                        select(offer.qualification_criteria).where(
                            offer.qualification_criteria.c.profile_id
                            == dossier["profile_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
            by_code = {item.criterion_code: item for item in request.results}
            if set(by_code) != {row["code"] for row in criteria}:
                raise ProductRecordsDenied("MISSING_CRITERION_RESULT")
            evidence = {
                row["id"]: row
                for row in (
                    (
                        await connection.execute(
                            select(q.evidence).where(
                                q.evidence.c.dossier_id == dossier["id"]
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            }
            for result in request.results:
                if not result.evidence_ids or any(
                    evidence_id not in evidence for evidence_id in result.evidence_ids
                ):
                    raise ProductRecordsDenied("MISSING_EVIDENCE")
                if any(
                    evidence[evidence_id]["valid_until"] <= now
                    for evidence_id in result.evidence_ids
                ):
                    raise ProductRecordsDenied("STALE_EVIDENCE")
            fatal = any(
                row["rule_kind"] == "FATAL_DISQUALIFIER"
                and by_code[row["code"]].status != "NOT_SATISFIED"
                for row in criteria
            )
            failed_hard = any(
                row["rule_kind"] == "HARD_GATE"
                and by_code[row["code"]].status != "SATISFIED"
                for row in criteria
            )
            reason_code = (
                "FATAL_DISQUALIFIER"
                if fatal
                else "FAILED_HARD_GATE"
                if failed_hard
                else "QUALIFIED"
            )
            expected_fact = "REJECTED_FIT" if fatal or failed_hard else "QUALIFIED"
            pilot_allowed = any(
                row["category"] == "PILOT_FIT"
                and by_code[row["code"]].status == "SATISFIED"
                for row in criteria
            )
            if (
                request.proposed_outcome == "PILOT_FIT_CONTACTABLE"
                and not pilot_allowed
            ):
                raise ProductRecordsDenied("PILOT_FIT_NOT_PERMITTED")
            if (request.proposed_outcome in ACCEPTED) != (expected_fact == "QUALIFIED"):
                raise ProductRecordsDenied("QUALIFICATION_PROPOSAL_MISMATCH")
            proof = await _one(connection, supply.facts, "id", request.proposal_fact_id)
            candidate = await _one(
                connection, supply.candidates, "id", dossier["candidate_id"]
            )
            if (
                proof["identity_id"] != candidate["identity_id"]
                or proof["experiment_id"] != experiment_id
                or proof["kind"] != expected_fact
                or proof["valid_until"] <= now
            ):
                raise ProductRecordsDenied("QUALIFICATION_PROPOSAL_MISMATCH")
            if request.valid_until <= now:
                raise ProductRecordsDenied("STALE_EVIDENCE")
            supported = await connection.scalar(
                select(func.count())
                .select_from(supply.contacts)
                .where(
                    supply.contacts.c.experiment_id == experiment_id,
                    supply.contacts.c.outcome == "SUPPORTED",
                    supply.contacts.c.resolved_at <= now,
                    supply.contacts.c.valid_until > now,
                )
            )
            if (supported or 0) < 50:
                raise ProductRecordsDenied("EMAIL_GATE")
            await self.organizations._owner(
                connection, experiment_id, request.decided_by
            )
            matrix_id, decision_id = uuid4(), uuid4()
            lineage = {
                name: dossier[name]
                for name in (
                    "experiment_id",
                    "candidate_id",
                    "organization_id",
                    "recipient_id",
                    "recipient_source_id",
                    "offer_acceptance_id",
                    "offer_id",
                    "profile_id",
                    "policy_id",
                )
            }
            await connection.execute(
                insert(q.matrices).values(
                    id=matrix_id,
                    dossier_id=dossier["id"],
                    created_at=now,
                    **lineage,
                )
            )
            await connection.execute(
                insert(q.criterion_results),
                [
                    {
                        "matrix_id": matrix_id,
                        "profile_id": dossier["profile_id"],
                        "criterion_code": item.criterion_code,
                        "status": item.status,
                        "rationale": item.rationale,
                    }
                    for item in request.results
                ],
            )
            await connection.execute(
                insert(q.result_evidence),
                [
                    {
                        "matrix_id": matrix_id,
                        "criterion_code": item.criterion_code,
                        "dossier_id": dossier["id"],
                        "evidence_id": evidence_id,
                    }
                    for item in request.results
                    for evidence_id in item.evidence_ids
                ],
            )
            await connection.execute(
                insert(supply.qualifications).values(
                    candidate_id=dossier["candidate_id"],
                    experiment_id=experiment_id,
                    fact_id=proof["id"],
                    accepted_at=now,
                    outcome=proof["kind"],
                )
            )
            await connection.execute(
                insert(q.decisions).values(
                    id=decision_id,
                    matrix_id=matrix_id,
                    dossier_id=dossier["id"],
                    proposal_fact_id=proof["id"],
                    outcome=request.proposed_outcome,
                    reason_code=reason_code,
                    finding_codes=list(request.finding_codes),
                    valid_until=min(
                        request.valid_until,
                        contact["valid_until"],
                        proof["valid_until"],
                        *(item["valid_until"] for item in evidence.values()),
                    ),
                    decided_by=request.decided_by,
                    decided_at=now,
                    **lineage,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="DECIDE_LEAD_QUALIFICATION",
                request_hash=request_hash,
                result_type="LEAD_QUALIFICATION_DECISION",
                result_id=decision_id,
                now=now,
            )
            return await self._decision_receipt(connection, decision_id, command_id)

    async def _cohort_receipt(self, connection, cohort_id, command_id):
        count = await connection.scalar(
            select(func.count())
            .select_from(q.cohort_members)
            .where(q.cohort_members.c.cohort_id == cohort_id)
        )
        return CohortReceipt(
            command_id=command_id,
            result_id=cohort_id,
            id=cohort_id,
            member_count=count,
        )

    @safe_records
    async def freeze_cohort(
        self, request: FreezeCohortRequest, *, command_key: UUID
    ) -> CohortReceipt:
        if len(set(request.decision_ids)) != 50:
            raise ProductRecordsDenied("COHORT_MEMBERS")
        async with self.engine.begin() as connection:
            await self._context(connection)
            rows = tuple(
                (
                    await connection.execute(
                        select(q.decisions).where(
                            q.decisions.c.id.in_(request.decision_ids)
                        )
                    )
                )
                .mappings()
                .all()
            )
            if len(rows) != 50:
                raise ProductRecordsDenied("COHORT_MEMBERS")
            experiment_id = rows[0]["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "FREEZE_LEAD_COHORT", request_hash
            )
            if old:
                return await self._cohort_receipt(
                    connection, old["result_id"], old["id"]
                )
            current = await self._current_acceptance(connection, experiment_id)
            if (
                current is None
                or current["id"] != request.offer_acceptance_id
                or any(
                    row["experiment_id"] != experiment_id
                    or row["offer_acceptance_id"] != request.offer_acceptance_id
                    for row in rows
                )
            ):
                raise ProductRecordsDenied("STALE_OFFER_VERSION")
            await self.organizations._owner(
                connection, experiment_id, request.frozen_by
            )
            state = await connection.scalar(
                select(supply.plans.c.state).where(
                    supply.plans.c.experiment_id == experiment_id
                )
            )
            if state != "TARGET_50_REACHED":
                raise ProductRecordsDenied("COHORT_TARGET")
            now = self.clock()
            by_id = {row["id"]: row for row in rows}
            ordered = [by_id[item] for item in request.decision_ids]
            for row in ordered:
                if row["outcome"] not in ACCEPTED or row["valid_until"] <= now:
                    raise ProductRecordsDenied("STALE_DECISION")
                await self._decision_gate(
                    connection,
                    await _one(connection, q.dossiers, "id", row["dossier_id"]),
                    now,
                )
            cohort_id = uuid4()
            await connection.execute(
                insert(q.cohorts).values(
                    id=cohort_id,
                    experiment_id=experiment_id,
                    offer_acceptance_id=current["id"],
                    offer_id=current["offer_id"],
                    profile_id=current["profile_id"],
                    policy_id=current["policy_id"],
                    target_size=50,
                    frozen_by=request.frozen_by,
                    frozen_at=now,
                )
            )
            try:
                for ordinal, row in enumerate(ordered, 1):
                    reservation_id = uuid4()
                    await connection.execute(
                        insert(org.reservations).values(
                            id=reservation_id,
                            organization_id=row["organization_id"],
                            recipient_id=row["recipient_id"],
                            experiment_id=experiment_id,
                            source_id=row["recipient_source_id"],
                            created_at=now,
                        )
                    )
                    await connection.execute(
                        insert(q.cohort_members).values(
                            cohort_id=cohort_id,
                            experiment_id=experiment_id,
                            ordinal=ordinal,
                            decision_id=row["id"],
                            candidate_id=row["candidate_id"],
                            organization_id=row["organization_id"],
                            recipient_id=row["recipient_id"],
                            recipient_source_id=row["recipient_source_id"],
                            reservation_id=reservation_id,
                        )
                    )
            except SQLAlchemyError as error:
                raise ProductRecordsDenied("PROTECTION_CONFLICT") from error
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="FREEZE_LEAD_COHORT",
                request_hash=request_hash,
                result_type="LEAD_COHORT",
                result_id=cohort_id,
                now=now,
            )
            return await self._cohort_receipt(connection, cohort_id, command_id)
