"""Commands for immutable offer-fit calibration and requalification lineage."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.db.repositories.accounting import lock_experiment
from alon_ai.db.repositories.records import (
    _complete,
    _existing,
    _request_hash,
    safe_records,
)
from alon_ai.db.repositories.records_organizations import OrganizationRepository
from alon_ai.db.repositories.records_qualifications import (
    ACCEPTED,
    QualificationCohortRepository,
)
from alon_ai.db.tables import records_calibration as s
from alon_ai.db.tables import records_offer as offer
from alon_ai.db.tables import records_qualification as qualification
from alon_ai.services.schemas.records import ProductRecordsDenied
from alon_ai.services.schemas.records_calibration import (
    CalibrationDecisionReceipt,
    CalibrationDecisionRequest,
    CalibrationFulfillmentReceipt,
    CalibrationFulfillmentRequest,
    CalibrationProposalReceipt,
    CalibrationProposalRequest,
)

CALIBRATION_MISMATCH_OUTCOMES = {
    "TECHNICAL_MISMATCH": "REJECTED_TECHNICAL_MISMATCH",
    "ECONOMIC_MISMATCH": "REJECTED_ECONOMIC_MISMATCH",
    "BUYER_MISMATCH": "REJECTED_BUYER_MISMATCH",
}
CALIBRATION_CATEGORY_BY_MISMATCH = {
    "TECHNICAL_MISMATCH": "TECHNICAL_FIT",
    "ECONOMIC_MISMATCH": "ECONOMIC_FIT",
    "BUYER_MISMATCH": "BUYER_FIT",
}


async def _one(connection: AsyncConnection, table, key: str, value: UUID):
    row = (
        (await connection.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("MISSING_REFERENCE")
    return row


async def assert_no_pending_calibration(
    connection: AsyncConnection, experiment_id: UUID
) -> None:
    """Reject only an accepted calibration that has not received a new offer."""
    pending = await connection.scalar(
        select(s.decisions.c.id)
        .outerjoin(
            s.fulfillments,
            s.fulfillments.c.calibration_decision_id == s.decisions.c.id,
        )
        .where(
            s.decisions.c.experiment_id == experiment_id,
            s.decisions.c.outcome == "ACCEPT",
            s.fulfillments.c.id.is_(None),
        )
        .limit(1)
    )
    if pending is not None:
        raise ProductRecordsDenied("CALIBRATION_FULFILLMENT_PENDING")


async def complete_requalification(
    connection: AsyncConnection,
    decision_id: UUID,
    *,
    completed_at: datetime,
) -> bool:
    """Append completion for a successful new-version decision, never mutate history."""
    decision = await _one(connection, qualification.decisions, "id", decision_id)
    if decision["outcome"] not in ACCEPTED:
        return False
    rows = tuple(
        (
            await connection.execute(
                select(s.obligations, s.fulfillments.c.fulfilled_at)
                .join(
                    s.fulfillments,
                    s.fulfillments.c.id == s.obligations.c.fulfillment_id,
                )
                .outerjoin(
                    s.completions,
                    s.completions.c.obligation_id == s.obligations.c.id,
                )
                .where(
                    s.obligations.c.experiment_id == decision["experiment_id"],
                    s.obligations.c.candidate_id == decision["candidate_id"],
                    s.obligations.c.required_offer_acceptance_id
                    == decision["offer_acceptance_id"],
                    s.completions.c.obligation_id.is_(None),
                )
            )
        )
        .mappings()
        .all()
    )
    for row in rows:
        if decision["decided_at"] < row["fulfilled_at"]:
            continue
        await connection.execute(
            insert(s.completions).values(
                obligation_id=row["id"],
                decision_id=decision_id,
                completed_at=completed_at,
            )
        )
        return True
    return False


class CalibrationRepository:
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
        self.qualifications = QualificationCohortRepository(
            engine, lookup_key=lookup_key, clock=clock
        )

    async def _context(self, connection: AsyncConnection) -> None:
        await self.organizations._context(connection)

    async def _current_acceptance(
        self, connection: AsyncConnection, experiment_id: UUID
    ):
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

    async def _proposal_receipt(
        self, connection: AsyncConnection, proposal_id: UUID, command_id: UUID
    ) -> CalibrationProposalReceipt:
        row = await _one(connection, s.proposals, "id", proposal_id)
        return CalibrationProposalReceipt(
            command_id=command_id,
            result_id=proposal_id,
            id=proposal_id,
            evidence_hash=row["evidence_hash"],
        )

    async def _decision_receipt(
        self, connection: AsyncConnection, decision_id: UUID, command_id: UUID
    ) -> CalibrationDecisionReceipt:
        row = await _one(connection, s.decisions, "id", decision_id)
        return CalibrationDecisionReceipt(
            command_id=command_id,
            result_id=decision_id,
            id=decision_id,
            outcome=row["outcome"],
            reason_code=row["reason_code"],
        )

    async def _fulfillment_receipt(
        self, connection: AsyncConnection, fulfillment_id: UUID, command_id: UUID
    ) -> CalibrationFulfillmentReceipt:
        count = await connection.scalar(
            select(func.count())
            .select_from(s.obligations)
            .where(s.obligations.c.fulfillment_id == fulfillment_id)
        )
        return CalibrationFulfillmentReceipt(
            command_id=command_id,
            result_id=fulfillment_id,
            id=fulfillment_id,
            requalification_count=count or 0,
        )

    async def _proposal_rows(self, connection: AsyncConnection, proposal_id: UUID):
        return tuple(
            (
                await connection.execute(
                    select(s.proposal_evidence).where(
                        s.proposal_evidence.c.proposal_id == proposal_id
                    )
                )
            )
            .mappings()
            .all()
        )

    async def _latest_base_decisions(
        self,
        connection: AsyncConnection,
        experiment_id: UUID,
        base_offer_acceptance_id: UUID,
    ):
        return tuple(
            (
                await connection.execute(
                    select(
                        qualification.decisions.c.id.label("previous_decision_id"),
                        qualification.decisions.c.candidate_id,
                        qualification.decisions.c.dossier_id.label(
                            "previous_dossier_id"
                        ),
                        qualification.decisions.c.matrix_id.label("previous_matrix_id"),
                    )
                    .join(
                        qualification.dossiers,
                        qualification.dossiers.c.id
                        == qualification.decisions.c.dossier_id,
                    )
                    .where(
                        qualification.decisions.c.experiment_id == experiment_id,
                        qualification.decisions.c.offer_acceptance_id
                        == base_offer_acceptance_id,
                    )
                    .distinct(qualification.dossiers.c.candidate_id)
                    .order_by(
                        qualification.dossiers.c.candidate_id,
                        qualification.dossiers.c.version.desc(),
                    )
                )
            )
            .mappings()
            .all()
        )

    async def _validate_evidence(
        self, connection: AsyncConnection, proposal, now: datetime
    ) -> tuple:
        rows = await self._proposal_rows(connection, proposal["id"])
        if len(rows) < 2 or len({row["candidate_id"] for row in rows}) < 2:
            raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
        current = await self._current_acceptance(connection, proposal["experiment_id"])
        if current is None or current["id"] != proposal["base_offer_acceptance_id"]:
            raise ProductRecordsDenied("STALE_OFFER_VERSION")
        for row in rows:
            decision = await _one(
                connection, qualification.decisions, "id", row["decision_id"]
            )
            await self._validate_mismatch_decision(
                connection,
                decision,
                proposal["mismatch_code"],
                proposal["base_offer_acceptance_id"],
                now,
            )
        return rows

    async def _validate_mismatch_decision(
        self,
        connection: AsyncConnection,
        decision,
        mismatch_code: str,
        base_offer_acceptance_id: UUID,
        now: datetime,
    ) -> None:
        expected_outcome = CALIBRATION_MISMATCH_OUTCOMES.get(mismatch_code)
        if (
            expected_outcome is None
            or decision["offer_acceptance_id"] != base_offer_acceptance_id
            or decision["outcome"] != expected_outcome
            or decision["valid_until"] <= now
            or mismatch_code not in decision["finding_codes"]
        ):
            raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
        dossier = await _one(
            connection, qualification.dossiers, "id", decision["dossier_id"]
        )
        await self.qualifications._decision_gate(connection, dossier, now)
        latest = await connection.scalar(
            select(qualification.decisions.c.id)
            .join(
                qualification.dossiers,
                qualification.dossiers.c.id == qualification.decisions.c.dossier_id,
            )
            .where(qualification.decisions.c.candidate_id == decision["candidate_id"])
            .order_by(qualification.dossiers.c.version.desc())
            .limit(1)
        )
        if latest != decision["id"]:
            raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
        results = {
            result["criterion_code"]: result
            for result in (
                (
                    await connection.execute(
                        select(qualification.criterion_results).where(
                            qualification.criterion_results.c.matrix_id
                            == decision["matrix_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
        }
        criteria = tuple(
            (
                await connection.execute(
                    select(offer.qualification_criteria).where(
                        offer.qualification_criteria.c.profile_id
                        == decision["profile_id"]
                    )
                )
            )
            .mappings()
            .all()
        )
        target_category = CALIBRATION_CATEGORY_BY_MISMATCH[mismatch_code]
        if set(results) != {criterion["code"] for criterion in criteria}:
            raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
        material_mismatch = False
        for criterion in criteria:
            status = results[criterion["code"]]["status"]
            if (
                criterion["rule_kind"] == "FATAL_DISQUALIFIER"
                and status != "NOT_SATISFIED"
            ):
                raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
            if (
                criterion["rule_kind"] == "HARD_GATE"
                and criterion["category"] != target_category
                and status != "SATISFIED"
            ):
                raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
            if (
                criterion["category"] == target_category
                and criterion["rule_kind"] == "HARD_GATE"
                and status == "NOT_SATISFIED"
            ):
                material_mismatch = True
        if not material_mismatch:
            raise ProductRecordsDenied("CALIBRATION_EVIDENCE")

    @safe_records
    async def propose(
        self, request: CalibrationProposalRequest, *, command_key: UUID
    ) -> CalibrationProposalReceipt:
        async with self.engine.begin() as connection:
            await self._context(connection)
            acceptance = await _one(
                connection,
                offer.offer_acceptances,
                "id",
                request.base_offer_acceptance_id,
            )
            experiment_id = acceptance["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "PROPOSE_OFFER_CALIBRATION", request_hash
            )
            if old:
                return await self._proposal_receipt(
                    connection, old["result_id"], old["id"]
                )
            current = await self._current_acceptance(connection, experiment_id)
            if current is None or current["id"] != acceptance["id"]:
                raise ProductRecordsDenied("STALE_OFFER_VERSION")
            decisions = tuple(
                (
                    await connection.execute(
                        select(qualification.decisions).where(
                            qualification.decisions.c.id.in_(request.decision_ids)
                        )
                    )
                )
                .mappings()
                .all()
            )
            if len(decisions) != len(request.decision_ids):
                raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
            expected_outcome = CALIBRATION_MISMATCH_OUTCOMES.get(request.mismatch_code)
            if (
                expected_outcome is None
                or len({row["candidate_id"] for row in decisions}) != len(decisions)
                or any(
                    row["experiment_id"] != experiment_id
                    or row["offer_acceptance_id"] != acceptance["id"]
                    or row["outcome"] != expected_outcome
                    or request.mismatch_code not in row["finding_codes"]
                    for row in decisions
                )
            ):
                raise ProductRecordsDenied("CALIBRATION_EVIDENCE")
            now = self.clock()
            for row in decisions:
                await self._validate_mismatch_decision(
                    connection,
                    row,
                    request.mismatch_code,
                    acceptance["id"],
                    now,
                )
            await self.organizations._owner(
                connection, experiment_id, request.proposed_by
            )
            proposal_id = uuid4()
            await connection.execute(
                insert(s.proposals).values(
                    id=proposal_id,
                    experiment_id=experiment_id,
                    base_offer_acceptance_id=acceptance["id"],
                    base_offer_id=acceptance["offer_id"],
                    base_profile_id=acceptance["profile_id"],
                    base_policy_id=acceptance["policy_id"],
                    mismatch_code=request.mismatch_code,
                    proposed_change_codes=list(request.proposed_change_codes),
                    evidence_hash=request_hash,
                    proposed_by=request.proposed_by,
                    proposed_at=now,
                )
            )
            await connection.execute(
                insert(s.proposal_evidence),
                [
                    {
                        "proposal_id": proposal_id,
                        "decision_id": row["id"],
                        "candidate_id": row["candidate_id"],
                        "dossier_id": row["dossier_id"],
                        "matrix_id": row["matrix_id"],
                        "finding_code": request.mismatch_code,
                    }
                    for row in decisions
                ],
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="PROPOSE_OFFER_CALIBRATION",
                request_hash=request_hash,
                result_type="OFFER_CALIBRATION_PROPOSAL",
                result_id=proposal_id,
                now=now,
            )
            return await self._proposal_receipt(connection, proposal_id, command_id)

    @safe_records
    async def decide(
        self, request: CalibrationDecisionRequest, *, command_key: UUID
    ) -> CalibrationDecisionReceipt:
        async with self.engine.begin() as connection:
            await self._context(connection)
            proposal = await _one(connection, s.proposals, "id", request.proposal_id)
            experiment_id = proposal["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "DECIDE_OFFER_CALIBRATION", request_hash
            )
            if old:
                return await self._decision_receipt(
                    connection, old["result_id"], old["id"]
                )
            now = self.clock()
            await self._validate_evidence(connection, proposal, now)
            await self.organizations._owner(
                connection, experiment_id, request.decided_by
            )
            if request.outcome == "ACCEPT":
                if await connection.scalar(
                    select(qualification.cohorts.c.id).where(
                        qualification.cohorts.c.experiment_id == experiment_id
                    )
                ):
                    raise ProductRecordsDenied("COHORT_ALREADY_FROZEN")
                if await connection.scalar(
                    select(s.decisions.c.id).where(
                        s.decisions.c.experiment_id == experiment_id,
                        s.decisions.c.outcome == "ACCEPT",
                    )
                ):
                    raise ProductRecordsDenied("CALIBRATION_ALREADY_ACCEPTED")
            decision_id = uuid4()
            await connection.execute(
                insert(s.decisions).values(
                    id=decision_id,
                    experiment_id=experiment_id,
                    proposal_id=proposal["id"],
                    base_offer_acceptance_id=proposal["base_offer_acceptance_id"],
                    base_offer_id=proposal["base_offer_id"],
                    base_profile_id=proposal["base_profile_id"],
                    base_policy_id=proposal["base_policy_id"],
                    evidence_hash=proposal["evidence_hash"],
                    outcome=request.outcome,
                    rule_version=request.rule_version,
                    reason_code=request.reason_code,
                    decided_by=request.decided_by,
                    decided_at=now,
                )
            )
            if request.outcome == "ACCEPT":
                evidence = await self._latest_base_decisions(
                    connection,
                    experiment_id,
                    proposal["base_offer_acceptance_id"],
                )
                await connection.execute(
                    insert(s.accepted_affected),
                    [
                        {
                            "calibration_decision_id": decision_id,
                            "candidate_id": row["candidate_id"],
                            "previous_decision_id": row["previous_decision_id"],
                            "previous_dossier_id": row["previous_dossier_id"],
                            "previous_matrix_id": row["previous_matrix_id"],
                        }
                        for row in evidence
                    ],
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="DECIDE_OFFER_CALIBRATION",
                request_hash=request_hash,
                result_type="OFFER_CALIBRATION_DECISION",
                result_id=decision_id,
                now=now,
            )
            return await self._decision_receipt(connection, decision_id, command_id)

    @safe_records
    async def fulfill(
        self, request: CalibrationFulfillmentRequest, *, command_key: UUID
    ) -> CalibrationFulfillmentReceipt:
        async with self.engine.begin() as connection:
            await self._context(connection)
            decision = await _one(
                connection, s.decisions, "id", request.calibration_decision_id
            )
            experiment_id = decision["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "FULFILL_OFFER_CALIBRATION", request_hash
            )
            if old:
                return await self._fulfillment_receipt(
                    connection, old["result_id"], old["id"]
                )
            if decision["outcome"] != "ACCEPT":
                raise ProductRecordsDenied("CALIBRATION_NOT_ACCEPTED")
            if await connection.scalar(
                select(qualification.cohorts.c.id).where(
                    qualification.cohorts.c.experiment_id == experiment_id
                )
            ):
                raise ProductRecordsDenied("COHORT_ALREADY_FROZEN")
            acceptance = await _one(
                connection,
                offer.offer_acceptances,
                "id",
                request.offer_acceptance_id,
            )
            current = await self._current_acceptance(connection, experiment_id)
            if (
                acceptance["experiment_id"] != experiment_id
                or current is None
                or current["id"] != acceptance["id"]
                or acceptance["id"] == decision["base_offer_acceptance_id"]
            ):
                raise ProductRecordsDenied("STALE_OFFER_VERSION")
            if acceptance["accepted_at"] < decision["decided_at"]:
                raise ProductRecordsDenied("CALIBRATION_FULFILLMENT_ORDER")
            package = await _one(
                connection, offer.offer_packages, "id", acceptance["offer_id"]
            )
            if package["calibration_decision_id"] != decision["id"]:
                raise ProductRecordsDenied("CALIBRATION_NOT_AUTHORIZED")
            if await connection.scalar(
                select(s.fulfillments.c.id).where(
                    s.fulfillments.c.calibration_decision_id == decision["id"]
                )
            ):
                raise ProductRecordsDenied("CALIBRATION_ALREADY_FULFILLED")
            await self.organizations._owner(
                connection, experiment_id, request.fulfilled_by
            )
            evidence = await self._latest_base_decisions(
                connection, experiment_id, decision["base_offer_acceptance_id"]
            )
            fulfillment_id = uuid4()
            now = self.clock()
            await connection.execute(
                insert(s.fulfillments).values(
                    id=fulfillment_id,
                    experiment_id=experiment_id,
                    calibration_decision_id=decision["id"],
                    base_offer_acceptance_id=decision["base_offer_acceptance_id"],
                    offer_acceptance_id=acceptance["id"],
                    offer_id=acceptance["offer_id"],
                    profile_id=acceptance["profile_id"],
                    policy_id=acceptance["policy_id"],
                    fulfilled_by=request.fulfilled_by,
                    fulfilled_at=now,
                )
            )
            await connection.execute(
                insert(s.obligations),
                [
                    {
                        "id": uuid4(),
                        "experiment_id": experiment_id,
                        "fulfillment_id": fulfillment_id,
                        "candidate_id": row["candidate_id"],
                        "previous_decision_id": row["previous_decision_id"],
                        "previous_dossier_id": row["previous_dossier_id"],
                        "previous_matrix_id": row["previous_matrix_id"],
                        "required_offer_acceptance_id": acceptance["id"],
                        "created_at": now,
                    }
                    for row in evidence
                ],
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="FULFILL_OFFER_CALIBRATION",
                request_hash=request_hash,
                result_type="OFFER_CALIBRATION_FULFILLMENT",
                result_id=fulfillment_id,
                now=now,
            )
            return await self._fulfillment_receipt(
                connection, fulfillment_id, command_id
            )
