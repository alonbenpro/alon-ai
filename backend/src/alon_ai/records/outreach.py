"""Transactional immutable outreach-context and drafting persistence."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from alon_ai.accounting import schema as governance
from alon_ai.accounting.repository import lock_experiment
from alon_ai.records import offer_schema as offer
from alon_ai.records import organization_schema as organization
from alon_ai.records import outreach_schema as outreach
from alon_ai.records import qualification_schema as qualification
from alon_ai.records import schema as records
from alon_ai.records.models import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    ProductRecordsDenied,
)
from alon_ai.records.organizations import OrganizationRepository
from alon_ai.records.outreach_models import (
    DraftGraphRequest,
    DraftValidationReceipt,
    FreezeOutreachContextRequest,
    OutreachContextReceipt,
)
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records
from alon_ai.supply import schema as supply


async def _one(connection, table, key, value):
    row = (
        (await connection.execute(select(table).where(table.c[key] == value)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ProductRecordsDenied("MISSING_REFERENCE")
    return row


async def _exact_artifact(connection, item: ArtifactInput):
    row = await _one(connection, records.artifacts, "id", item.artifact_id)
    if (
        row["kind"] != item.kind
        or row["version"] != item.version
        or row["content_hash"] != item.content_hash
    ):
        raise ProductRecordsDenied("ARTIFACT_DRIFT")
    return row


async def _append_artifact(
    connection: AsyncConnection,
    draft: ArtifactDraft,
    inputs: Sequence[ArtifactInput] = (),
) -> ArtifactInput:
    await connection.execute(
        insert(records.artifacts).values(
            id=draft.id,
            logical_id=draft.logical_id,
            version=draft.version,
            experiment_id=draft.experiment_id,
            workflow_id=draft.workflow_id,
            agent_id=draft.agent_id,
            operation_id=draft.operation_id,
            kind=draft.kind,
            schema_version=draft.schema_version,
            payload=draft.payload,
            created_by=draft.created_by,
            created_at=draft.created_at,
        )
    )
    row = await _one(connection, records.artifacts, "id", draft.id)
    for item in inputs:
        await connection.execute(
            insert(records.artifact_links).values(
                consumer_id=draft.id,
                producer_id=item.artifact_id,
                experiment_id=draft.experiment_id,
                role=item.role,
                producer_kind=item.kind,
                producer_version=item.version,
                producer_hash=item.content_hash,
            )
        )
    return ArtifactInput(
        artifact_id=draft.id,
        kind=draft.kind,
        version=draft.version,
        content_hash=row["content_hash"],
        role="OUTREACH_INPUT",
    )


class OutreachRecordsRepository:
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

    async def _context_receipt(self, connection, context_id, command_id):
        row = await _one(connection, outreach.contexts, "id", context_id)
        return OutreachContextReceipt(
            command_id=command_id,
            result_id=context_id,
            id=context_id,
            artifact_id=row["artifact_id"],
            content_hash=row["lineage_hash"],
        )

    @safe_records
    async def freeze_context(
        self, request: FreezeOutreachContextRequest, *, command_key: UUID
    ) -> OutreachContextReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            member = (
                (
                    await connection.execute(
                        select(qualification.cohort_members).where(
                            qualification.cohort_members.c.cohort_id
                            == request.cohort_id,
                            qualification.cohort_members.c.decision_id
                            == request.decision_id,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if member is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            experiment_id = member["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "FREEZE_OUTREACH_CONTEXT", request_hash
            )
            if old:
                return await self._context_receipt(
                    connection, old["result_id"], old["id"]
                )
            decision = await _one(
                connection, qualification.decisions, "id", request.decision_id
            )
            matrix = await _one(
                connection, qualification.matrices, "id", decision["matrix_id"]
            )
            dossier = await _one(
                connection, qualification.dossiers, "id", decision["dossier_id"]
            )
            cohort = await _one(
                connection, qualification.cohorts, "id", request.cohort_id
            )
            policy = await _one(
                connection, offer.initial_outreach_policies, "id", decision["policy_id"]
            )
            contact = await _one(
                connection, supply.contacts, "candidate_id", decision["candidate_id"]
            )
            recipient_source = await _one(
                connection,
                organization.recipient_sources,
                "id",
                dossier["recipient_source_id"],
            )
            prompt = await _exact_artifact(connection, request.prompt_configuration)
            config = await _one(
                connection, governance.configs, "id", request.model_config_id
            )
            workflow_experiment = await connection.scalar(
                select(governance.workflows.c.experiment_id).where(
                    governance.workflows.c.id == config["workflow_id"]
                )
            )
            evidence_ids = set(
                (
                    await connection.execute(
                        select(qualification.evidence.c.id).where(
                            qualification.evidence.c.dossier_id == dossier["id"]
                        )
                    )
                ).scalars()
            )
            if {item.evidence_id for item in request.coverage} != evidence_ids:
                raise ProductRecordsDenied("INCOMPLETE_EVIDENCE_COVERAGE")
            now = self.clock()
            if (
                request.artifact.kind is not ArtifactKind.OUTREACH_CONTEXT_BUNDLE
                or request.prompt_configuration.kind
                is not ArtifactKind.OUTREACH_PROMPT_CONFIGURATION
                or request.artifact.experiment_id != experiment_id
                or prompt["experiment_id"] != experiment_id
                or workflow_experiment != experiment_id
                or config["capability"] != "OPENAI_GENERATE"
                or policy["max_sequence_steps"] is None
                or decision["valid_until"] <= now
                or contact["outcome"] != "SUPPORTED"
                or contact["source_id"] != recipient_source["source_fact_id"]
                or not contact["resolved_at"] <= now < contact["valid_until"]
                or await connection.scalar(
                    select(organization.releases.c.id).where(
                        organization.releases.c.reservation_id
                        == member["reservation_id"]
                    )
                )
                is not None
            ):
                raise ProductRecordsDenied("OUTREACH_CONTEXT_NOT_CURRENT")
            protection = await connection.scalar(
                text("SELECT record_org_block_reason(:org,:recipient,:exp)"),
                {
                    "org": decision["organization_id"],
                    "recipient": decision["recipient_id"],
                    "exp": experiment_id,
                },
            )
            if protection is not None:
                raise ProductRecordsDenied("PROTECTION_CONFLICT")
            exact = (
                decision["matrix_id"] == matrix["id"]
                and decision["dossier_id"] == dossier["id"]
                and cohort["offer_acceptance_id"] == decision["offer_acceptance_id"]
                and cohort["offer_id"] == decision["offer_id"]
                and cohort["profile_id"] == decision["profile_id"]
                and cohort["policy_id"] == decision["policy_id"]
                and member["candidate_id"] == decision["candidate_id"]
                and member["organization_id"] == decision["organization_id"]
                and member["recipient_id"] == decision["recipient_id"]
                and member["recipient_source_id"] == decision["recipient_source_id"]
                and policy["offer_id"] == decision["offer_id"]
            )
            if not exact:
                raise ProductRecordsDenied("LINEAGE_MISMATCH")
            mode = request.artifact.payload["recipient_mode"]
            label = request.artifact.payload["recipient_label"]
            greeting = request.artifact.payload["greeting"].strip()
            label_coverage = next(
                (
                    item
                    for item in request.coverage
                    if item.evidence_id == request.recipient_label_evidence_id
                ),
                None,
            )
            if (
                not greeting
                or (
                    mode == "GENERAL_BUSINESS_INBOX"
                    and (label is not None or greeting != "Hello team")
                )
                or (
                    mode in {"NAMED_PERSON", "ROLE_INBOX"}
                    and (
                        label_coverage is None
                        or label_coverage.disposition != "USED"
                        or greeting
                        != (
                            f"Hi {label}"
                            if mode == "NAMED_PERSON"
                            else f"Hello {label} team"
                        )
                    )
                )
            ):
                raise ProductRecordsDenied("RECIPIENT_GREETING_MISMATCH")
            await self.organizations._owner(
                connection, experiment_id, request.frozen_by
            )
            context_artifact = await _append_artifact(
                connection,
                request.artifact,
                (
                    request.prompt_configuration.model_copy(
                        update={"role": "PROMPT_CONFIGURATION"}
                    ),
                ),
            )
            context_id = uuid4()
            await connection.execute(
                insert(outreach.contexts).values(
                    id=context_id,
                    experiment_id=experiment_id,
                    artifact_id=context_artifact.artifact_id,
                    artifact_version=context_artifact.version,
                    artifact_hash=context_artifact.content_hash,
                    cohort_id=request.cohort_id,
                    decision_id=decision["id"],
                    matrix_id=matrix["id"],
                    dossier_id=dossier["id"],
                    candidate_id=decision["candidate_id"],
                    organization_id=decision["organization_id"],
                    recipient_id=decision["recipient_id"],
                    recipient_source_id=decision["recipient_source_id"],
                    contact_source_id=contact["source_id"],
                    contact_verification_id=contact["verification_id"],
                    contact_resolved_at=contact["resolved_at"],
                    contact_valid_until=contact["valid_until"],
                    reservation_id=member["reservation_id"],
                    offer_acceptance_id=decision["offer_acceptance_id"],
                    offer_id=decision["offer_id"],
                    profile_id=decision["profile_id"],
                    policy_id=decision["policy_id"],
                    prompt_artifact_id=prompt["id"],
                    prompt_version=prompt["version"],
                    prompt_hash=prompt["content_hash"],
                    model_config_id=config["id"],
                    model_config_workflow_id=config["workflow_id"],
                    model_config_version=config["version"],
                    recipient_mode=mode,
                    recipient_label=label,
                    recipient_label_evidence_id=request.recipient_label_evidence_id,
                    greeting=greeting,
                    frozen_by=request.frozen_by,
                    frozen_at=now,
                )
            )
            await connection.execute(
                insert(outreach.coverage),
                [
                    {
                        "context_id": context_id,
                        "dossier_id": dossier["id"],
                        **item.model_dump(exclude={"schema_version"}),
                    }
                    for item in request.coverage
                ],
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="FREEZE_OUTREACH_CONTEXT",
                request_hash=request_hash,
                result_type="OUTREACH_CONTEXT",
                result_id=context_id,
                now=now,
            )
            return await self._context_receipt(connection, context_id, command_id)

    async def _draft_receipt(self, connection, validation_id, command_id):
        row = await _one(connection, outreach.validations, "id", validation_id)
        return DraftValidationReceipt(
            command_id=command_id,
            result_id=validation_id,
            draft_id=row["draft_artifact_id"],
            validation_id=validation_id,
            disposition=row["disposition"],
            reason_codes=tuple(row["reason_codes"]),
        )

    @safe_records
    async def record_draft(
        self, request: DraftGraphRequest, *, command_key: UUID
    ) -> DraftValidationReceipt:
        async with self.engine.begin() as connection:
            await self.organizations._context(connection)
            context = await _one(
                connection, outreach.contexts, "id", request.context_id
            )
            experiment_id = context["experiment_id"]
            await lock_experiment(connection, experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_OUTREACH_DRAFT", request_hash
            )
            if old:
                return await self._draft_receipt(
                    connection, old["result_id"], old["id"]
                )
            now = self.clock()
            if await connection.scalar(
                select(organization.releases.c.id).where(
                    organization.releases.c.reservation_id == context["reservation_id"]
                )
            ):
                raise ProductRecordsDenied("STALE_CONTACT")
            policy = await _one(
                connection, offer.initial_outreach_policies, "id", context["policy_id"]
            )
            drafts = (
                request.narrative,
                request.strategy,
                request.sequence,
                request.draft,
            )
            expected_kinds = (
                ArtifactKind.LEAD_OPPORTUNITY_NARRATIVE,
                ArtifactKind.CONVERSATION_STRATEGY,
                ArtifactKind.OUTREACH_SEQUENCE_PLAN,
                ArtifactKind.EMAIL_DRAFT,
            )
            if any(
                draft.kind is not kind or draft.experiment_id != experiment_id
                for draft, kind in zip(drafts, expected_kinds, strict=True)
            ):
                raise ProductRecordsDenied("ARTIFACT_DRIFT")
            if len(request.sequence_steps) > policy[
                "max_sequence_steps"
            ] or request.sequence.payload["step_count"] != len(request.sequence_steps):
                raise ProductRecordsDenied("SEQUENCE_POLICY_LIMIT")
            if (
                request.draft.payload["recipient_mode"] != context["recipient_mode"]
                or request.draft.payload["greeting"].strip() != context["greeting"]
            ):
                raise ProductRecordsDenied("RECIPIENT_GREETING_MISMATCH")
            coverage_rows = (
                (
                    await connection.execute(
                        select(outreach.coverage).where(
                            outreach.coverage.c.context_id == request.context_id
                        )
                    )
                )
                .mappings()
                .all()
            )
            usable = {
                row["evidence_id"]
                for row in coverage_rows
                if row["disposition"] == "USED"
            }
            referenced = (
                {
                    evidence_id
                    for angle in request.angles
                    for evidence_id in angle.evidence_ids
                }
                | {
                    evidence_id
                    for subject in request.subjects
                    for evidence_id in subject.evidence_ids
                }
                | {
                    evidence_id
                    for claim in request.claims
                    for evidence_id in claim.evidence_ids
                }
            )
            if not referenced <= usable:
                raise ProductRecordsDenied("REJECTED_EVIDENCE_REFERENCE")
            angle_ids = {item.id for item in request.angles}
            if (
                request.primary_angle_id not in angle_ids
                or request.supporting_angle_id is not None
                and request.supporting_angle_id not in angle_ids
                or request.primary_angle_id == request.supporting_angle_id
            ):
                raise ProductRecordsDenied("ANGLE_CARDINALITY")
            subject = next(
                (item for item in request.subjects if item.id == request.subject_id),
                None,
            )
            if subject is None or subject.text != request.draft.payload["subject"]:
                raise ProductRecordsDenied("SUBJECT_MISMATCH")
            allowed_fields = set(
                (
                    await connection.execute(
                        select(offer.offer_field_sources.c.field_path).where(
                            offer.offer_field_sources.c.offer_id == context["offer_id"]
                        )
                    )
                ).scalars()
            )
            if any(
                not set(claim.offer_field_paths) <= allowed_fields
                for claim in request.claims
            ):
                raise ProductRecordsDenied("OFFER_FIELD_LINEAGE")
            await self.organizations._owner(
                connection, experiment_id, request.recorded_by
            )
            context_input = ArtifactInput(
                artifact_id=context["artifact_id"],
                kind=ArtifactKind.OUTREACH_CONTEXT_BUNDLE,
                version=context["artifact_version"],
                content_hash=context["artifact_hash"],
                role="OUTREACH_CONTEXT",
            )
            narrative = await _append_artifact(
                connection, request.narrative, (context_input,)
            )
            strategy = await _append_artifact(
                connection,
                request.strategy,
                (narrative.model_copy(update={"role": "NARRATIVE"}),),
            )
            sequence = await _append_artifact(
                connection,
                request.sequence,
                (strategy.model_copy(update={"role": "STRATEGY"}),),
            )
            draft = await _append_artifact(
                connection,
                request.draft,
                (
                    context_input,
                    narrative.model_copy(update={"role": "NARRATIVE"}),
                    strategy.model_copy(update={"role": "STRATEGY"}),
                    sequence.model_copy(update={"role": "SEQUENCE"}),
                ),
            )
            for item in (narrative, strategy, sequence, draft):
                await connection.execute(
                    insert(outreach.documents).values(
                        artifact_id=item.artifact_id,
                        experiment_id=experiment_id,
                        context_id=request.context_id,
                        kind=item.kind,
                        version=item.version,
                        content_hash=item.content_hash,
                    )
                )
            await connection.execute(
                insert(outreach.angles),
                [
                    {
                        "id": item.id,
                        "context_id": request.context_id,
                        "rank": item.rank,
                        "text": item.text,
                        "content_hash": _request_hash(angle=item),
                    }
                    for item in request.angles
                ],
            )
            await connection.execute(
                insert(outreach.angle_evidence),
                [
                    {
                        "angle_id": item.id,
                        "context_id": request.context_id,
                        "evidence_id": evidence_id,
                    }
                    for item in request.angles
                    for evidence_id in item.evidence_ids
                ],
            )
            await connection.execute(
                insert(outreach.subjects),
                [
                    {
                        "id": item.id,
                        "context_id": request.context_id,
                        "strategy_artifact_id": strategy.artifact_id,
                        "rank": item.rank,
                        "text": item.text,
                        "content_hash": _request_hash(subject=item),
                    }
                    for item in request.subjects
                ],
            )
            await connection.execute(
                insert(outreach.subject_evidence),
                [
                    {
                        "subject_id": item.id,
                        "context_id": request.context_id,
                        "evidence_id": evidence_id,
                    }
                    for item in request.subjects
                    for evidence_id in item.evidence_ids
                ],
            )
            await connection.execute(
                insert(outreach.sequence_steps),
                [
                    {
                        "sequence_artifact_id": sequence.artifact_id,
                        "context_id": request.context_id,
                        **item.model_dump(exclude={"schema_version"}),
                    }
                    for item in request.sequence_steps
                ],
            )
            await connection.execute(
                insert(outreach.claims),
                [
                    {
                        "artifact_id": item.artifact_id,
                        "context_id": request.context_id,
                        "ordinal": item.ordinal,
                        "kind": item.kind,
                        "text": item.text,
                    }
                    for item in request.claims
                ],
            )
            evidence_links = [
                {
                    "artifact_id": item.artifact_id,
                    "ordinal": item.ordinal,
                    "context_id": request.context_id,
                    "evidence_id": evidence_id,
                }
                for item in request.claims
                for evidence_id in item.evidence_ids
            ]
            if evidence_links:
                await connection.execute(
                    insert(outreach.claim_evidence), evidence_links
                )
            field_links = [
                {
                    "artifact_id": item.artifact_id,
                    "ordinal": item.ordinal,
                    "context_id": request.context_id,
                    "offer_id": context["offer_id"],
                    "field_path": field_path,
                }
                for item in request.claims
                for field_path in item.offer_field_paths
            ]
            if field_links:
                await connection.execute(
                    insert(outreach.claim_offer_fields), field_links
                )
            await connection.execute(
                insert(outreach.drafts).values(
                    artifact_id=draft.artifact_id,
                    context_id=request.context_id,
                    narrative_artifact_id=narrative.artifact_id,
                    strategy_artifact_id=strategy.artifact_id,
                    sequence_artifact_id=sequence.artifact_id,
                    subject_id=request.subject_id,
                    recipient_mode=context["recipient_mode"],
                    greeting=context["greeting"],
                )
            )
            angle_links = [
                {
                    "draft_artifact_id": draft.artifact_id,
                    "context_id": request.context_id,
                    "angle_id": angle_id,
                    "role": role,
                }
                for angle_id, role in (
                    (request.primary_angle_id, "PRIMARY"),
                    (request.supporting_angle_id, "SUPPORTING"),
                )
                if angle_id is not None
            ]
            await connection.execute(insert(outreach.draft_angles), angle_links)
            if request.cta is not None:
                await connection.execute(
                    insert(outreach.draft_ctas).values(
                        draft_artifact_id=draft.artifact_id, text=request.cta
                    )
                )
            input_hash = sha256(
                (context["lineage_hash"] + request_hash).encode()
            ).hexdigest()
            validation_draft = ArtifactDraft(
                id=uuid4(),
                logical_id=uuid4(),
                version=1,
                experiment_id=experiment_id,
                kind=ArtifactKind.DRAFT_VALIDATION_RESULT,
                payload={
                    "validator": request.validator,
                    "disposition": "PASS",
                    "input_hash": input_hash,
                    "reason_codes": [],
                },
                created_by=request.recorded_by,
                created_at=now,
            )
            validation_artifact = await _append_artifact(
                connection,
                validation_draft,
                (draft.model_copy(update={"role": "VALIDATED_DRAFT"}),),
            )
            validation_id = uuid4()
            await connection.execute(
                insert(outreach.validations).values(
                    id=validation_id,
                    artifact_id=validation_artifact.artifact_id,
                    experiment_id=experiment_id,
                    draft_artifact_id=draft.artifact_id,
                    validator=request.validator,
                    validator_version=request.validator_version,
                    input_hash=input_hash,
                    disposition="PASS",
                    reason_codes=[],
                    validated_at=now,
                )
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_id,
                kind="RECORD_OUTREACH_DRAFT",
                request_hash=request_hash,
                result_type="DRAFT_VALIDATION",
                result_id=validation_id,
                now=now,
            )
            return await self._draft_receipt(connection, validation_id, command_id)
