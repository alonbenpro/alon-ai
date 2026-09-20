"""Transactional commands for exact offer design and acceptance records."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records import offer_schema as s
from alon_ai.records import schema as records
from alon_ai.records.models import (
    ArtifactInput,
    ArtifactKind,
    CycleReceipt,
    ProductRecordsDenied,
)
from alon_ai.records.offer_models import (
    INITIAL_OUTREACH_POLICY,
    OFFER_FIELD_EVIDENCE_ROLES,
    OPERATOR_FIELD_CONSTRAINTS,
    PROTECTED_OFFER_FIELDS,
    REQUIRED_QUALIFICATION_CATEGORIES,
    REQUIRED_RESEARCH_ROLES,
    CommercialEnvelopeReceipt,
    CommercialEnvelopeRequest,
    InputBundleReceipt,
    OfferAcceptanceReceipt,
    OfferAcceptanceRequest,
    OfferGapRequest,
    OfferProposalReceipt,
)
from alon_ai.records.repository import (
    _complete,
    _existing,
    _request_hash,
    safe_records,
)


async def _exact_artifact(connection: AsyncConnection, value: ArtifactInput):
    row = (
        (
            await connection.execute(
                select(records.artifacts).where(
                    records.artifacts.c.id == value.artifact_id,
                    records.artifacts.c.kind == value.kind,
                    records.artifacts.c.version == value.version,
                    records.artifacts.c.content_hash == value.content_hash,
                )
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("EXACT_ARTIFACT")
    return row


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


class OfferRecordsRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.clock = clock

    @safe_records
    async def freeze_input_bundle(
        self,
        artifact: ArtifactInput,
        *,
        verdict_id: UUID,
        command_key: UUID,
    ) -> InputBundleReceipt:
        async with self.engine.begin() as connection:
            bundle_artifact = await _exact_artifact(connection, artifact)
            experiment_id = bundle_artifact["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(artifact=artifact, verdict_id=verdict_id)
            old = await _existing(
                connection, command_key, "FREEZE_OFFER_INPUT", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(s.offer_bundles).where(
                                s.offer_bundles.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return InputBundleReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    artifact_id=row["artifact_id"],
                    version=row["artifact_version"],
                    content_hash=row["artifact_hash"],
                )
            if artifact.kind is not ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE:
                raise ProductRecordsDenied("BUNDLE_KIND")
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == verdict_id,
                            records.verdicts.c.experiment_id == experiment_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if verdict is None or verdict["verdict"] != "PROCEED_TO_OFFER":
                raise ProductRecordsDenied("PROCEED_REQUIRED")
            idea = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == verdict["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            links = (
                (
                    await connection.execute(
                        select(records.artifact_links).where(
                            records.artifact_links.c.consumer_id == artifact.artifact_id
                        )
                    )
                )
                .mappings()
                .all()
            )
            by_role = {row["role"]: row for row in links}
            role_counts = {
                role: sum(row["role"] == role for row in links)
                for role in REQUIRED_RESEARCH_ROLES
            }
            if any(count != 1 for count in role_counts.values()):
                raise ProductRecordsDenied("INCOMPLETE_RESEARCH")
            fixed = {
                "ACCEPTED_IDEA": idea["artifact_id"],
                "REPORT": verdict["report_artifact_id"],
                "RECOMMENDATION": verdict["recommendation_artifact_id"],
            }
            for role, expected in fixed.items():
                if by_role.get(role, {}).get("producer_id") != expected:
                    raise ProductRecordsDenied(f"INCOMPLETE_RESEARCH_{role}")
            report_links = (
                (
                    await connection.execute(
                        select(records.artifact_links).where(
                            records.artifact_links.c.consumer_id
                            == verdict["report_artifact_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
            report_exact = {
                (
                    row["role"],
                    row["producer_id"],
                    row["producer_kind"],
                    row["producer_version"],
                    row["producer_hash"],
                )
                for row in report_links
            }
            for role in REQUIRED_RESEARCH_ROLES:
                row = by_role[role]
                if (
                    role,
                    row["producer_id"],
                    row["producer_kind"],
                    row["producer_version"],
                    row["producer_hash"],
                ) not in report_exact:
                    raise ProductRecordsDenied("INCOMPLETE_RESEARCH")
                if not await connection.scalar(
                    select(records.source_refs.c.id).where(
                        records.source_refs.c.artifact_id == row["producer_id"]
                    )
                ):
                    raise ProductRecordsDenied("MISSING_SOURCE_PROVENANCE")
            prices = (
                (
                    await connection.execute(
                        select(records.artifacts.c.payload).where(
                            records.artifacts.c.id.in_(
                                [by_role["PRICE_OBSERVATION"]["producer_id"]]
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )
            if any(price["status"] != "QUOTED" for price in prices):
                raise ProductRecordsDenied("INCOMPLETE_RESEARCH")
            result_id = uuid4()
            await connection.execute(
                insert(s.offer_bundles).values(
                    id=result_id,
                    experiment_id=experiment_id,
                    artifact_id=artifact.artifact_id,
                    artifact_kind=artifact.kind,
                    artifact_version=artifact.version,
                    artifact_hash=artifact.content_hash,
                    idea_acceptance_id=idea["id"],
                    idea_artifact_id=idea["artifact_id"],
                    verdict_id=verdict_id,
                    report_artifact_id=verdict["report_artifact_id"],
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(s.offer_bundle_inputs),
                [
                    {
                        "bundle_id": result_id,
                        "experiment_id": experiment_id,
                        "role": row["role"],
                        "artifact_id": row["producer_id"],
                        "artifact_kind": row["producer_kind"],
                        "artifact_version": row["producer_version"],
                        "artifact_hash": row["producer_hash"],
                    }
                    for row in links
                ],
            )
            previous = (
                (
                    await connection.execute(
                        select(s.offer_proposals.c.id)
                        .join(
                            s.offer_bundles,
                            s.offer_bundles.c.id == s.offer_proposals.c.bundle_id,
                        )
                        .where(
                            s.offer_bundles.c.idea_artifact_id == idea["artifact_id"],
                            s.offer_proposals.c.id.not_in(
                                select(s.offer_packages.c.proposal_id)
                            ),
                            s.offer_proposals.c.id.not_in(
                                select(s.offer_proposal_invalidations.c.proposal_id)
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if previous:
                await connection.execute(
                    insert(s.offer_proposal_invalidations),
                    [
                        {
                            "proposal_id": proposal_id,
                            "experiment_id": experiment_id,
                            "superseding_bundle_id": result_id,
                            "reason": "SUPERSEDED_RESEARCH",
                            "created_at": self.clock(),
                        }
                        for proposal_id in previous
                    ],
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="FREEZE_OFFER_INPUT",
                request_hash=request_hash,
                result_type="OFFER_INPUT_BUNDLE",
                result_id=result_id,
                now=self.clock(),
            )
            return InputBundleReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                artifact_id=artifact.artifact_id,
                version=artifact.version,
                content_hash=artifact.content_hash,
            )

    @safe_records
    async def derive_commercial_envelope(
        self, request: CommercialEnvelopeRequest, *, command_key: UUID
    ) -> CommercialEnvelopeReceipt:
        async with self.engine.begin() as connection:
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(
                            s.offer_bundles.c.id == request.bundle_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, bundle["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "DERIVE_COMMERCIAL_ENVELOPE", request_hash
            )
            if old:
                return await self._envelope_receipt(
                    connection, old["result_id"], old["id"]
                )
            artifact = await _exact_artifact(connection, request.artifact)
            scope = await _exact_artifact(connection, request.scope_estimate)
            if (
                artifact["experiment_id"] != bundle["experiment_id"]
                or request.artifact.kind is not ArtifactKind.COMMERCIAL_DESIGN_ENVELOPE
            ):
                raise ProductRecordsDenied("ENVELOPE_SCOPE")
            scope_input = await connection.scalar(
                select(s.offer_bundle_inputs.c.artifact_id).where(
                    s.offer_bundle_inputs.c.bundle_id == request.bundle_id,
                    s.offer_bundle_inputs.c.role == "SCOPE_ESTIMATE",
                    s.offer_bundle_inputs.c.artifact_id
                    == request.scope_estimate.artifact_id,
                    s.offer_bundle_inputs.c.artifact_hash
                    == request.scope_estimate.content_hash,
                )
            )
            if (
                scope_input is None
                or request.scope_estimate.kind
                is not ArtifactKind.DELIVERY_SCOPE_ESTIMATE
            ):
                raise ProductRecordsDenied("SCOPE_EVIDENCE")
            experiment = (
                (
                    await connection.execute(
                        select(records.experiments).where(
                            records.experiments.c.id == bundle["experiment_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            profile = (
                (
                    await connection.execute(
                        select(s.operator_profiles).where(
                            s.operator_profiles.c.id
                            == experiment["operator_profile_id"],
                            s.operator_profiles.c.version
                            == experiment["operator_profile_version"],
                        )
                    )
                )
                .mappings()
                .one()
            )
            commercial = profile["commercial"]
            delivery = profile["delivery"]
            hours = Decimal(scope["payload"]["hours"])
            currency = commercial["currency"]
            quoted_currencies = set(
                (
                    await connection.execute(
                        select(records.artifacts.c.payload["currency"].as_string())
                        .join(
                            s.offer_bundle_inputs,
                            s.offer_bundle_inputs.c.artifact_id
                            == records.artifacts.c.id,
                        )
                        .where(
                            s.offer_bundle_inputs.c.bundle_id == request.bundle_id,
                            s.offer_bundle_inputs.c.role == "PRICE_OBSERVATION",
                        )
                    )
                ).scalars()
            )
            margin = Decimal(str(commercial["minimum_margin_rate"]))
            status = "READY"
            delivery_cost = minimum_price = None
            if hours > Decimal(str(delivery["max_project_hours"])):
                status = "DELIVERY_CAPACITY_EXCEEDED"
            elif margin >= 1:
                status = "IMPOSSIBLE_ECONOMICS"
            elif quoted_currencies != {currency}:
                status = "CURRENCY_MISMATCH"
            else:
                delivery_cost = _money(hours * Decimal(str(commercial["hourly_cost"])))
                margin_floor = _money(delivery_cost / (Decimal(1) - margin))
                minimum_price = max(
                    margin_floor,
                    _money(Decimal(str(commercial["minimum_project_price"]))),
                )
            if artifact["payload"]["status"] != status:
                raise ProductRecordsDenied("ENVELOPE_CLASSIFICATION")
            result_id = uuid4()
            await connection.execute(
                insert(s.commercial_envelopes).values(
                    id=result_id,
                    experiment_id=bundle["experiment_id"],
                    artifact_id=request.artifact.artifact_id,
                    artifact_kind=request.artifact.kind,
                    artifact_version=request.artifact.version,
                    artifact_hash=request.artifact.content_hash,
                    bundle_id=request.bundle_id,
                    operator_profile_id=profile["id"],
                    operator_profile_version=profile["version"],
                    scope_artifact_id=request.scope_estimate.artifact_id,
                    status=status,
                    currency=currency,
                    service_hours=hours,
                    delivery_cost=delivery_cost,
                    minimum_price=minimum_price,
                    minimum_margin_rate=margin,
                    maximum_discount_rate=Decimal(
                        str(commercial["maximum_discount_rate"])
                    ),
                    minimum_deposit_rate=Decimal(
                        str(commercial["minimum_deposit_rate"])
                    ),
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=bundle["experiment_id"],
                kind="DERIVE_COMMERCIAL_ENVELOPE",
                request_hash=request_hash,
                result_type="COMMERCIAL_ENVELOPE",
                result_id=result_id,
                now=self.clock(),
            )
            return CommercialEnvelopeReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                bundle_id=request.bundle_id,
                status=status,
                currency=currency,
                delivery_cost=delivery_cost,
                minimum_price=minimum_price,
            )

    async def _envelope_receipt(self, connection, result_id, command_id):
        row = (
            (
                await connection.execute(
                    select(s.commercial_envelopes).where(
                        s.commercial_envelopes.c.id == result_id
                    )
                )
            )
            .mappings()
            .one()
        )
        return CommercialEnvelopeReceipt(
            command_id=command_id,
            result_id=row["id"],
            id=row["id"],
            bundle_id=row["bundle_id"],
            status=row["status"],
            currency=row["currency"],
            delivery_cost=row["delivery_cost"],
            minimum_price=row["minimum_price"],
        )

    @safe_records
    async def register_proposal(
        self,
        artifact: ArtifactInput,
        *,
        bundle_id: UUID,
        envelope_id: UUID,
        command_key: UUID,
    ) -> OfferProposalReceipt:
        async with self.engine.begin() as connection:
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(s.offer_bundles.c.id == bundle_id)
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, bundle["experiment_id"])
            request_hash = _request_hash(
                artifact=artifact, bundle_id=bundle_id, envelope_id=envelope_id
            )
            old = await _existing(
                connection, command_key, "REGISTER_OFFER_PROPOSAL", request_hash
            )
            if old:
                return OfferProposalReceipt(
                    command_id=old["id"],
                    result_id=old["result_id"],
                    id=old["result_id"],
                    bundle_id=bundle_id,
                )
            value = await _exact_artifact(connection, artifact)
            envelope = (
                (
                    await connection.execute(
                        select(s.commercial_envelopes).where(
                            s.commercial_envelopes.c.id == envelope_id,
                            s.commercial_envelopes.c.bundle_id == bundle_id,
                        )
                    )
                )
                .mappings()
                .one()
            )
            if (
                artifact.kind is not ArtifactKind.OFFER_DESIGN_PROPOSAL
                or envelope["status"] != "READY"
            ):
                raise ProductRecordsDenied("ENVELOPE_NOT_READY")
            if (
                value["payload"]["currency"] != envelope["currency"]
                or Decimal(value["payload"]["base_price"]) < envelope["minimum_price"]
            ):
                raise ProductRecordsDenied("COMMERCIAL_FLOOR")
            result_id = uuid4()
            await connection.execute(
                insert(s.offer_proposals).values(
                    id=result_id,
                    experiment_id=bundle["experiment_id"],
                    artifact_id=artifact.artifact_id,
                    artifact_kind=artifact.kind,
                    artifact_version=artifact.version,
                    artifact_hash=artifact.content_hash,
                    bundle_id=bundle_id,
                    envelope_id=envelope_id,
                    created_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=bundle["experiment_id"],
                kind="REGISTER_OFFER_PROPOSAL",
                request_hash=request_hash,
                result_type="OFFER_PROPOSAL",
                result_id=result_id,
                now=self.clock(),
            )
            return OfferProposalReceipt(
                command_id=command_id,
                result_id=result_id,
                id=result_id,
                bundle_id=bundle_id,
            )

    @safe_records
    async def accept_offer(
        self, request: OfferAcceptanceRequest, *, command_key: UUID
    ) -> OfferAcceptanceReceipt:
        if {item.field_path for item in request.field_sources} != set(
            PROTECTED_OFFER_FIELDS
        ) or len(request.field_sources) != len(PROTECTED_OFFER_FIELDS):
            raise ProductRecordsDenied("FIELD_LINEAGE")
        if {item.category for item in request.criteria} != set(
            REQUIRED_QUALIFICATION_CATEGORIES
        ):
            raise ProductRecordsDenied("QUALIFICATION_COVERAGE")
        for item in request.field_sources:
            if item.source is not None:
                if item.source.role not in OFFER_FIELD_EVIDENCE_ROLES.get(
                    item.field_path, ()
                ):
                    raise ProductRecordsDenied("FIELD_LINEAGE")
            elif (
                OPERATOR_FIELD_CONSTRAINTS.get(item.field_path)
                != item.operator_constraint
            ):
                raise ProductRecordsDenied("FIELD_LINEAGE")
        async with self.engine.begin() as connection:
            proposal = (
                (
                    await connection.execute(
                        select(s.offer_proposals).where(
                            s.offer_proposals.c.id == request.proposal_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, proposal["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(connection, command_key, "ACCEPT_OFFER", request_hash)
            if old:
                row = (
                    (
                        await connection.execute(
                            select(
                                s.offer_acceptances,
                                s.offer_packages.c.bundle_id,
                                s.commercial_envelopes.c.minimum_price,
                            )
                            .join(
                                s.offer_packages,
                                s.offer_packages.c.id == s.offer_acceptances.c.offer_id,
                            )
                            .join(
                                s.commercial_envelopes,
                                s.commercial_envelopes.c.id
                                == s.offer_packages.c.envelope_id,
                            )
                            .where(s.offer_acceptances.c.id == old["result_id"])
                        )
                    )
                    .mappings()
                    .one()
                )
                return OfferAcceptanceReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    bundle_id=row["bundle_id"],
                    offer_artifact_id=row["offer_artifact_id"],
                    minimum_price=row["minimum_price"],
                )
            if await connection.scalar(
                select(s.offer_proposal_invalidations.c.proposal_id).where(
                    s.offer_proposal_invalidations.c.proposal_id == request.proposal_id
                )
            ):
                raise ProductRecordsDenied("PROPOSAL_INVALIDATED")
            package = await _exact_artifact(connection, request.package)
            await _exact_artifact(connection, request.qualification_profile)
            policy_artifact = await _exact_artifact(connection, request.outreach_policy)
            proposal_artifact = (
                (
                    await connection.execute(
                        select(records.artifacts).where(
                            records.artifacts.c.id == proposal["artifact_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            envelope = (
                (
                    await connection.execute(
                        select(s.commercial_envelopes).where(
                            s.commercial_envelopes.c.id == proposal["envelope_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            if (
                request.package.kind is not ArtifactKind.OFFER_PACKAGE
                or package["payload"] != proposal_artifact["payload"]
            ):
                raise ProductRecordsDenied("PACKAGE_DRIFT")
            if (
                request.qualification_profile.kind
                is not ArtifactKind.OFFER_QUALIFICATION_PROFILE
                or request.outreach_policy.kind
                is not ArtifactKind.INITIAL_OUTREACH_POLICY
                or policy_artifact["payload"] != INITIAL_OUTREACH_POLICY
            ):
                raise ProductRecordsDenied("MATCHING_RECORDS")
            evidence_ids = set(
                (
                    await connection.execute(
                        select(s.offer_bundle_inputs.c.artifact_id).where(
                            s.offer_bundle_inputs.c.bundle_id == proposal["bundle_id"]
                        )
                    )
                ).scalars()
            )
            if any(
                item.source is not None and item.source.artifact_id not in evidence_ids
                for item in request.field_sources
            ):
                raise ProductRecordsDenied("FIELD_LINEAGE")
            offer_id, profile_id, policy_id, acceptance_id = (
                uuid4(),
                uuid4(),
                uuid4(),
                uuid4(),
            )
            await connection.execute(
                insert(s.offer_packages).values(
                    id=offer_id,
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.package.artifact_id,
                    artifact_kind=request.package.kind,
                    artifact_version=request.package.version,
                    artifact_hash=request.package.content_hash,
                    proposal_id=request.proposal_id,
                    bundle_id=proposal["bundle_id"],
                    envelope_id=proposal["envelope_id"],
                    currency=package["payload"]["currency"],
                    base_price=Decimal(package["payload"]["base_price"]),
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(s.offer_field_sources),
                [
                    {
                        "offer_id": offer_id,
                        "experiment_id": proposal["experiment_id"],
                        "field_path": item.field_path,
                        "source_artifact_id": item.source.artifact_id
                        if item.source
                        else None,
                        "source_kind": item.source.kind if item.source else None,
                        "source_role": item.source.role if item.source else None,
                        "source_version": item.source.version if item.source else None,
                        "source_hash": item.source.content_hash
                        if item.source
                        else None,
                        "operator_constraint": item.operator_constraint,
                        "bundle_id": proposal["bundle_id"],
                    }
                    for item in request.field_sources
                ],
            )
            await connection.execute(
                insert(s.offer_qualification_profiles).values(
                    id=profile_id,
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.qualification_profile.artifact_id,
                    artifact_kind=request.qualification_profile.kind,
                    artifact_version=request.qualification_profile.version,
                    artifact_hash=request.qualification_profile.content_hash,
                    offer_id=offer_id,
                )
            )
            await connection.execute(
                insert(s.qualification_criteria),
                [
                    dict(
                        profile_id=profile_id,
                        **item.model_dump(exclude={"schema_version"}),
                    )
                    for item in request.criteria
                ],
            )
            await connection.execute(
                insert(s.initial_outreach_policies).values(
                    id=policy_id,
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.outreach_policy.artifact_id,
                    artifact_kind=request.outreach_policy.kind,
                    artifact_version=request.outreach_policy.version,
                    artifact_hash=request.outreach_policy.content_hash,
                    offer_id=offer_id,
                    **INITIAL_OUTREACH_POLICY,
                )
            )
            await connection.execute(
                insert(s.offer_acceptances).values(
                    id=acceptance_id,
                    experiment_id=proposal["experiment_id"],
                    offer_id=offer_id,
                    offer_artifact_id=request.package.artifact_id,
                    profile_id=profile_id,
                    profile_artifact_id=request.qualification_profile.artifact_id,
                    policy_id=policy_id,
                    policy_artifact_id=request.outreach_policy.artifact_id,
                    accepted_by=request.accepted_by,
                    accepted_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=proposal["experiment_id"],
                kind="ACCEPT_OFFER",
                request_hash=request_hash,
                result_type="OFFER_ACCEPTANCE",
                result_id=acceptance_id,
                now=self.clock(),
            )
            return OfferAcceptanceReceipt(
                command_id=command_id,
                result_id=acceptance_id,
                id=acceptance_id,
                bundle_id=proposal["bundle_id"],
                offer_artifact_id=request.package.artifact_id,
                minimum_price=envelope["minimum_price"],
            )

    @safe_records
    async def activate_offer_gap(self, request: OfferGapRequest, *, command_key: UUID):
        async with self.engine.begin() as connection:
            proposal = (
                (
                    await connection.execute(
                        select(s.offer_proposals).where(
                            s.offer_proposals.c.id == request.proposal_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            await lock_experiment(connection, proposal["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "ACTIVATE_OFFER_GAP", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            select(records.cycles).where(
                                records.cycles.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return CycleReceipt(
                    command_id=old["id"],
                    result_id=row["id"],
                    id=row["id"],
                    experiment_id=row["experiment_id"],
                    ordinal=row["ordinal"],
                )
            artifact = await _exact_artifact(connection, request.artifact)
            if (
                request.artifact.kind is not ArtifactKind.OFFER_RESEARCH_GAP_BRIEF
                or artifact["experiment_id"] != proposal["experiment_id"]
            ):
                raise ProductRecordsDenied("GAP_SCOPE")
            await connection.execute(
                insert(s.offer_gap_briefs).values(
                    id=uuid4(),
                    experiment_id=proposal["experiment_id"],
                    artifact_id=request.artifact.artifact_id,
                    artifact_kind=request.artifact.kind,
                    artifact_version=request.artifact.version,
                    artifact_hash=request.artifact.content_hash,
                    proposal_id=request.proposal_id,
                    bundle_id=proposal["bundle_id"],
                    missing_fields=list(request.missing_fields),
                    contradictory_fields=list(request.contradictory_fields),
                    required_source_types=list(request.required_source_types),
                    targeted_questions=list(request.targeted_questions),
                    created_at=self.clock(),
                )
            )
            bundle = (
                (
                    await connection.execute(
                        select(s.offer_bundles).where(
                            s.offer_bundles.c.id == proposal["bundle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            verdict = (
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.id == bundle["verdict_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            parent = (
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.id == verdict["cycle_id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            idea = (
                (
                    await connection.execute(
                        select(records.idea_acceptances).where(
                            records.idea_acceptances.c.cycle_id == parent["id"]
                        )
                    )
                )
                .mappings()
                .one()
            )
            ordinal = (
                await connection.scalar(
                    select(func.count())
                    .select_from(records.cycles)
                    .where(records.cycles.c.experiment_id == proposal["experiment_id"])
                )
                or 0
            ) + 1
            cycle_id = uuid4()
            await connection.execute(
                insert(records.cycles).values(
                    id=cycle_id,
                    experiment_id=proposal["experiment_id"],
                    ordinal=ordinal,
                    parent_cycle_id=parent["id"],
                    idea_mode=parent["idea_mode"],
                    selection_id=parent["selection_id"],
                    purpose="OFFER_GAP_RETURN",
                    episode_id=parent["episode_id"],
                    seed_artifact_id=parent["seed_artifact_id"],
                    seed_kind=parent["seed_kind"],
                    seed_version=parent["seed_version"],
                    seed_hash=parent["seed_hash"],
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(records.returns).values(
                    id=uuid4(),
                    experiment_id=proposal["experiment_id"],
                    from_cycle_id=parent["id"],
                    verdict_id=verdict["id"],
                    to_cycle_id=cycle_id,
                    ordinal=1,
                    kind="OFFER_GAP",
                    applicable_scope_id=idea["artifact_id"],
                    idea_artifact_id=idea["artifact_id"],
                    offer_input_bundle_id=bundle["artifact_id"],
                    feedback_artifact_id=request.artifact.artifact_id,
                    feedback_kind=request.artifact.kind,
                    feedback_version=request.artifact.version,
                    feedback_hash=request.artifact.content_hash,
                    created_at=self.clock(),
                )
            )
            await connection.execute(
                insert(records.idea_acceptances).values(
                    id=uuid4(),
                    experiment_id=proposal["experiment_id"],
                    cycle_id=cycle_id,
                    artifact_id=idea["artifact_id"],
                    artifact_kind=idea["artifact_kind"],
                    artifact_version=idea["artifact_version"],
                    artifact_hash=idea["artifact_hash"],
                    accepted_by=idea["accepted_by"],
                    accepted_at=self.clock(),
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=proposal["experiment_id"],
                kind="ACTIVATE_OFFER_GAP",
                request_hash=request_hash,
                result_type="CYCLE",
                result_id=cycle_id,
                now=self.clock(),
            )
            return CycleReceipt(
                command_id=command_id,
                result_id=cycle_id,
                id=cycle_id,
                experiment_id=proposal["experiment_id"],
                ordinal=ordinal,
            )
