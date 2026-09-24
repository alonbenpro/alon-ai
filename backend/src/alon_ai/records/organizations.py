"""Trusted organization ingestion and global protection; no provider execution.

The composition root resolves one preassigned SecretStore handle. The fixed key
is transaction-local, never part of DTOs, fingerprints, records or exceptions.
Only a trusted Gmail adapter may ingest GatewayEffectObservation. Its exact
prebound effect/call/run and positive provider evidence are validated in SQL.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting import schema as gov
from alon_ai.records import organization_schema as s
from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
from alon_ai.records.organization_models import (
    GatewayEffectObservation,
    OrganizationAdmissionReceipt,
    OrganizationIdentityReceipt,
    OrganizationSnapshot,
    RetainedOrganizationSource,
)
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records


class OrganizationRepository:
    def __init__(
        self,
        engine: AsyncEngine,
        *,
        lookup_key: SecretStr,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        if len(lookup_key.get_secret_value().encode()) != 32:
            raise ValueError("identity lookup key must be exactly 32 bytes")
        self.engine, self.clock, self._lookup_key = engine, clock, lookup_key

    async def _context(self, connection):
        # Parameters are deliberately never reflected into a domain error.
        await connection.execute(text("SELECT pg_advisory_xact_lock(730803)"))
        await connection.execute(
            text(
                "SELECT set_config('alon.organization_key',:key,true),set_config('alon.organization_now',:now,true)"
            ),
            {
                "key": self._lookup_key.get_secret_value(),
                "now": self.clock().isoformat(),
            },
        )
        fingerprint = sha256(self._lookup_key.get_secret_value().encode()).hexdigest()
        row = (
            (await connection.execute(select(s.policy).where(s.policy.c.id == 1)))
            .mappings()
            .one()
        )
        if row["key_fingerprint"] is None:
            await connection.execute(
                update(s.policy)
                .where(s.policy.c.id == 1)
                .values(key_fingerprint=fingerprint)
            )
        elif row["key_fingerprint"] != fingerprint:
            raise ProductRecordsDenied("IDENTITY_KEY_POLICY")

    async def _owner(self, connection, experiment_id, actor):
        if not await connection.scalar(
            text("SELECT record_operator_authorized(:exp,:actor)"),
            {"exp": experiment_id, "actor": actor},
        ):
            raise ProductRecordsDenied("OPERATOR_AUTHORITY")

    async def _finish(self, c, exp, kind, request_hash, result_id, command_key):
        return await _complete(
            c,
            command_key=command_key,
            experiment_id=exp,
            kind=kind,
            request_hash=request_hash,
            result_type=kind,
            result_id=result_id,
            now=self.clock(),
        )

    @safe_records
    async def register_identity(
        self,
        experiment_id: UUID,
        identity_id: UUID,
        source: RetainedOrganizationSource,
        *,
        registered_by: UUID,
        command_key: UUID,
    ) -> OrganizationIdentityReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            await self._owner(c, experiment_id, registered_by)
            fingerprint = _request_hash(
                experiment_id=experiment_id,
                identity_id=identity_id,
                source=source,
                registered_by=registered_by,
            )
            old = await _existing(c, command_key, "REGISTER_ORGANIZATION", fingerprint)
            if old:
                binding = (
                    (
                        await c.execute(
                            select(s.bindings).where(
                                s.bindings.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one()
                )
                return OrganizationIdentityReceipt(
                    command_id=old["id"],
                    organization_id=binding["organization_id"],
                    evidence_id=binding["evidence_id"],
                    binding_id=binding["id"],
                )
            data = await c.scalar(
                text("SELECT record_org_snapshot(:retained,:idx)"),
                {"retained": source.retained_id, "idx": source.value_index},
            )
            snapshot = OrganizationSnapshot.model_validate_json(json.dumps(data))
            # Exclusivity is limited to country-registered legal business IDs.
            strong = []
            for identifier in snapshot.identifiers:
                if identifier.kind == "REGISTERED_ID":
                    digest = await c.scalar(
                        text("SELECT record_org_lookup(:value)"),
                        {"value": identifier.value},
                    )
                    found = await c.scalar(
                        select(s.keys.c.organization_id).where(
                            s.keys.c.kind == "REGISTERED_ID",
                            s.keys.c.namespace == identifier.namespace,
                            s.keys.c.lookup_hash == digest,
                        )
                    )
                    if found:
                        strong.append(
                            await c.scalar(
                                text("SELECT record_org_canonical(:id)"), {"id": found}
                            )
                        )
            matches = set(strong) if len(set(strong)) > 1 else set()
            if not any(v.kind == "REGISTERED_ID" for v in snapshot.identifiers):
                for kind, value in [
                    ("NAME", snapshot.canonical_name),
                    ("DOMAIN", snapshot.canonical_domain),
                ]:
                    if value:
                        digest = await c.scalar(
                            text("SELECT record_org_lookup(:value)"), {"value": value}
                        )
                        matches.update(
                            (
                                await c.execute(
                                    select(s.keys.c.organization_id).where(
                                        s.keys.c.kind == kind,
                                        s.keys.c.lookup_hash == digest,
                                    )
                                )
                            ).scalars()
                        )
            org_id = strong[0] if len(set(strong)) == 1 else uuid4()
            if len(set(strong)) != 1:
                await c.execute(
                    insert(s.organizations).values(id=org_id, created_at=self.clock())
                )
            retained = (
                (
                    await c.execute(
                        select(gov.retained).where(
                            gov.retained.c.id == source.retained_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            call = (
                (
                    await c.execute(
                        select(gov.calls).where(gov.calls.c.id == retained["call_id"])
                    )
                )
                .mappings()
                .one()
            )
            evidence_id = uuid4()
            await c.execute(
                insert(s.evidence).values(
                    id=evidence_id,
                    organization_id=org_id,
                    experiment_id=experiment_id,
                    operation_id=call["operation_id"],
                    call_id=call["id"],
                    grant_id=retained["grant_id"],
                    grant_version=retained["grant_version"],
                    retained_id=source.retained_id,
                    value_index=source.value_index,
                    snapshot_hash=sha256(
                        retained["values"][source.value_index].encode()
                    ).hexdigest(),
                    expires_at=retained["expires_at"],
                    observed_at=source.observed_at,
                )
            )
            entries = [("NAME", "global", snapshot.canonical_name, -1)]
            if snapshot.canonical_domain:
                entries.append(("DOMAIN", "global", snapshot.canonical_domain, -1))
            entries.extend(
                (v.kind, v.namespace, v.value, i)
                for i, v in enumerate(snapshot.identifiers)
            )
            entries.extend(
                (v.kind, "global", v.value, i) for i, v in enumerate(snapshot.aliases)
            )
            for kind, namespace, value, index in entries:
                digest = await c.scalar(
                    text("SELECT record_org_lookup(:value)"), {"value": value}
                )
                if kind == "REGISTERED_ID" and await c.scalar(
                    select(s.keys.c.id).where(
                        s.keys.c.kind == kind,
                        s.keys.c.namespace == namespace,
                        s.keys.c.lookup_hash == digest,
                    )
                ):
                    continue
                await c.execute(
                    insert(s.keys).values(
                        id=uuid4(),
                        organization_id=org_id,
                        evidence_id=evidence_id,
                        kind=kind,
                        namespace=namespace,
                        lookup_hash=digest,
                        source_index=index,
                    )
                )
            for i, _ in enumerate(snapshot.locations):
                await c.execute(
                    insert(s.locations).values(
                        id=uuid4(),
                        organization_id=org_id,
                        evidence_id=evidence_id,
                        source_index=i,
                    )
                )
            for matched_id in matches:
                if matched_id != org_id:
                    await c.execute(
                        insert(s.conflicts).values(
                            id=uuid4(),
                            organization_id=org_id,
                            matched_id=matched_id,
                            evidence_id=evidence_id,
                            created_at=self.clock(),
                        )
                    )
            binding_id = uuid4()
            await c.execute(
                insert(s.bindings).values(
                    id=binding_id,
                    experiment_id=experiment_id,
                    organization_id=org_id,
                    identity_id=identity_id,
                    evidence_id=evidence_id,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                c,
                experiment_id,
                "REGISTER_ORGANIZATION",
                fingerprint,
                binding_id,
                command_key,
            )
            return OrganizationIdentityReceipt(
                command_id=command_id,
                organization_id=org_id,
                evidence_id=evidence_id,
                binding_id=binding_id,
            )

    @safe_records
    async def identity(self, evidence_id: UUID) -> OrganizationSnapshot:
        async with self.engine.begin() as c:
            await self._context(c)
            evidence = (
                (
                    await c.execute(
                        select(s.evidence).where(s.evidence.c.id == evidence_id)
                    )
                )
                .mappings()
                .one()
            )
            data = await c.scalar(
                text("SELECT record_org_snapshot(:retained,:idx)"),
                {"retained": evidence["retained_id"], "idx": evidence["value_index"]},
            )
            return OrganizationSnapshot.model_validate_json(json.dumps(data))

    @safe_records
    async def admit(
        self, binding_id: UUID, *, acted_by: UUID, command_key: UUID
    ) -> OrganizationAdmissionReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            binding = (
                (
                    await c.execute(
                        select(s.bindings).where(s.bindings.c.id == binding_id)
                    )
                )
                .mappings()
                .one()
            )
            exp, org = binding["experiment_id"], binding["organization_id"]
            await self._owner(c, exp, acted_by)
            fingerprint = _request_hash(binding_id=binding_id, acted_by=acted_by)
            old = await _existing(c, command_key, "ADMIT_ORGANIZATION", fingerprint)
            if old:
                exclusion = (
                    (
                        await c.execute(
                            select(s.exclusions).where(
                                s.exclusions.c.id == old["result_id"]
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                return OrganizationAdmissionReceipt(
                    command_id=old["id"],
                    result_id=old["result_id"],
                    admitted=exclusion is None,
                    reason=exclusion["reason"] if exclusion else None,
                )
            reason = await c.scalar(
                text("SELECT record_org_block_reason(:org,NULL,:exp)"),
                {"org": org, "exp": exp},
            )
            if reason is None and not await c.scalar(
                text("SELECT record_org_evidence_current(:id)"),
                {"id": binding["evidence_id"]},
            ):
                reason = "SOURCE_UNAVAILABLE"
            result_id = uuid4()
            if reason:
                await c.execute(
                    insert(s.exclusions).values(
                        id=result_id,
                        experiment_id=exp,
                        organization_id=org,
                        reason=reason,
                        created_at=self.clock(),
                    )
                )
            else:
                await c.execute(
                    insert(s.admissions).values(
                        id=result_id,
                        binding_id=binding_id,
                        experiment_id=exp,
                        organization_id=org,
                        created_at=self.clock(),
                    )
                )
            command_id = await self._finish(
                c, exp, "ADMIT_ORGANIZATION", fingerprint, result_id, command_key
            )
            return OrganizationAdmissionReceipt(
                command_id=command_id,
                result_id=result_id,
                admitted=reason is None,
                reason=reason,
            )

    @safe_records
    async def working_candidates(self, experiment_id: UUID) -> tuple[UUID, ...]:
        async with self.engine.begin() as c:
            await self._context(c)
            return tuple(
                (
                    await c.execute(
                        text(
                            "SELECT id FROM record_org_working_candidates WHERE experiment_id=:exp ORDER BY id"
                        ),
                        {"exp": experiment_id},
                    )
                ).scalars()
            )

    @safe_records
    async def register_recipient(
        self,
        binding_id: UUID,
        candidate_id: UUID,
        source_fact_id: UUID,
        source: RetainedOrganizationSource,
        *,
        acted_by: UUID,
        command_key: UUID,
    ) -> CommandReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            binding = (
                (
                    await c.execute(
                        select(s.bindings).where(s.bindings.c.id == binding_id)
                    )
                )
                .mappings()
                .one()
            )
            exp = binding["experiment_id"]
            await self._owner(c, exp, acted_by)
            fingerprint = _request_hash(
                binding_id=binding_id,
                candidate_id=candidate_id,
                source_fact_id=source_fact_id,
                source=source,
                acted_by=acted_by,
            )
            old = await _existing(c, command_key, "REGISTER_ORG_RECIPIENT", fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            digest = await c.scalar(
                text("SELECT record_org_email_lookup(:retained,:idx)"),
                {"retained": source.retained_id, "idx": source.value_index},
            )
            recipient_id = await c.scalar(
                select(s.recipients.c.id).where(s.recipients.c.lookup_hash == digest)
            )
            if recipient_id is None:
                recipient_id = uuid4()
                await c.execute(
                    insert(s.recipients).values(
                        id=recipient_id, lookup_hash=digest, created_at=self.clock()
                    )
                )
            result_id = uuid4()
            await c.execute(
                insert(s.recipient_sources).values(
                    id=result_id,
                    recipient_id=recipient_id,
                    organization_id=binding["organization_id"],
                    experiment_id=exp,
                    binding_id=binding_id,
                    candidate_id=candidate_id,
                    source_fact_id=source_fact_id,
                    retained_id=source.retained_id,
                    value_index=source.value_index,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                c, exp, "REGISTER_ORG_RECIPIENT", fingerprint, result_id, command_key
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def reserve(
        self, source_id: UUID, *, acted_by: UUID, command_key: UUID
    ) -> CommandReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            source = (
                (
                    await c.execute(
                        select(s.recipient_sources).where(
                            s.recipient_sources.c.id == source_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            exp = source["experiment_id"]
            await self._owner(c, exp, acted_by)
            fingerprint = _request_hash(source_id=source_id, acted_by=acted_by)
            old = await _existing(c, command_key, "RESERVE_ORGANIZATION", fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            result_id = uuid4()
            await c.execute(
                insert(s.reservations).values(
                    id=result_id,
                    organization_id=source["organization_id"],
                    recipient_id=source["recipient_id"],
                    experiment_id=exp,
                    source_id=source_id,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                c, exp, "RESERVE_ORGANIZATION", fingerprint, result_id, command_key
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def bind_effect(
        self,
        reservation_id: UUID,
        call_id: UUID,
        *,
        mailbox_id: UUID,
        rfc_message_id: UUID,
        acted_by: UUID,
        command_key: UUID,
    ) -> CommandReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            reservation = (
                (
                    await c.execute(
                        select(s.reservations).where(
                            s.reservations.c.id == reservation_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            call = (
                (await c.execute(select(gov.calls).where(gov.calls.c.id == call_id)))
                .mappings()
                .one()
            )
            exp = reservation["experiment_id"]
            await self._owner(c, exp, acted_by)
            fingerprint = _request_hash(
                reservation_id=reservation_id,
                call_id=call_id,
                mailbox_id=mailbox_id,
                rfc_message_id=rfc_message_id,
                acted_by=acted_by,
            )
            old = await _existing(c, command_key, "BIND_ORG_EFFECT", fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            digest = await c.scalar(
                select(s.recipients.c.lookup_hash).where(
                    s.recipients.c.id == reservation["recipient_id"]
                )
            )
            result_id = uuid4()
            await c.execute(
                insert(s.effects).values(
                    id=result_id,
                    reservation_id=reservation_id,
                    experiment_id=exp,
                    call_id=call_id,
                    operation_id=call["operation_id"],
                    mailbox_id=mailbox_id,
                    rfc_message_id=rfc_message_id,
                    recipient_lookup_hash=digest,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                c, exp, "BIND_ORG_EFFECT", fingerprint, result_id, command_key
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def ingest_gateway_observation(
        self, observation: GatewayEffectObservation, *, command_key: UUID
    ) -> CommandReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            fingerprint = _request_hash(observation=observation)
            old = await _existing(c, command_key, "OBSERVE_ORG_EFFECT", fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            await c.execute(
                insert(s.observations).values(
                    **observation.model_dump(exclude={"schema_version"})
                )
            )
            command_id = await self._finish(
                c,
                observation.experiment_id,
                "OBSERVE_ORG_EFFECT",
                fingerprint,
                observation.id,
                command_key,
            )
            return CommandReceipt(command_id=command_id, result_id=observation.id)

    @safe_records
    async def release(
        self,
        reservation_id: UUID,
        *,
        acted_by: UUID,
        command_key: UUID,
        evidence_id: UUID | None = None,
    ) -> CommandReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            reservation = (
                (
                    await c.execute(
                        select(s.reservations).where(
                            s.reservations.c.id == reservation_id
                        )
                    )
                )
                .mappings()
                .one()
            )
            exp = reservation["experiment_id"]
            await self._owner(c, exp, acted_by)
            fingerprint = _request_hash(
                reservation_id=reservation_id,
                acted_by=acted_by,
                evidence_id=evidence_id,
            )
            old = await _existing(c, command_key, "RELEASE_ORGANIZATION", fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            result_id = uuid4()
            await c.execute(
                insert(s.releases).values(
                    id=result_id,
                    reservation_id=reservation_id,
                    evidence_id=evidence_id,
                    released_by=acted_by,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                c, exp, "RELEASE_ORGANIZATION", fingerprint, result_id, command_key
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)

    @safe_records
    async def suppress(
        self,
        *,
        acted_by: UUID,
        reason_code: str,
        command_key: UUID,
        organization_id: UUID | None = None,
        recipient_id: UUID | None = None,
        global_scope: bool = False,
    ) -> CommandReceipt:
        return await self._global_change(
            s.suppressions,
            "SUPPRESS_ORGANIZATION",
            {
                "organization_id": organization_id,
                "recipient_id": recipient_id,
                "global_scope": global_scope,
                "reason_code": reason_code,
                "acted_by": acted_by,
            },
            command_key,
        )

    @safe_records
    async def merge(
        self,
        losing_id: UUID,
        surviving_id: UUID,
        evidence_id: UUID,
        *,
        acted_by: UUID,
        reason_code: str,
        command_key: UUID,
    ) -> CommandReceipt:
        return await self._global_change(
            s.merges,
            "MERGE_ORGANIZATION",
            {
                "losing_id": losing_id,
                "surviving_id": surviving_id,
                "evidence_id": evidence_id,
                "acted_by": acted_by,
                "reason_code": reason_code,
            },
            command_key,
        )

    @safe_records
    async def resolve_identity_conflict(
        self,
        conflict_id: UUID,
        evidence_id: UUID,
        *,
        resolution: str,
        acted_by: UUID,
        reason_code: str,
        command_key: UUID,
    ) -> CommandReceipt:
        async with self.engine.begin() as c:
            await self._context(c)
            fingerprint = _request_hash(
                conflict_id=conflict_id,
                evidence_id=evidence_id,
                resolution=resolution,
                acted_by=acted_by,
                reason_code=reason_code,
            )
            old = await _existing(c, command_key, "RESOLVE_ORG_IDENTITY", fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            conflict = (
                (
                    await c.execute(
                        select(s.conflicts).where(s.conflicts.c.id == conflict_id)
                    )
                )
                .mappings()
                .one()
            )
            if resolution == "SAME_ORGANIZATION":
                await c.execute(
                    insert(s.merges).values(
                        id=uuid4(),
                        losing_id=conflict["organization_id"],
                        surviving_id=conflict["matched_id"],
                        evidence_id=evidence_id,
                        acted_by=acted_by,
                        reason_code=reason_code,
                        created_at=self.clock(),
                    )
                )
            result_id = uuid4()
            await c.execute(
                insert(s.identity_decisions).values(
                    id=result_id,
                    conflict_id=conflict_id,
                    evidence_id=evidence_id,
                    resolution=resolution,
                    acted_by=acted_by,
                    reason_code=reason_code,
                    created_at=self.clock(),
                )
            )
            command_id = await self._finish(
                c, None, "RESOLVE_ORG_IDENTITY", fingerprint, result_id, command_key
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)

    async def _global_change(self, table, kind, data, command_key):
        async with self.engine.begin() as c:
            await self._context(c)
            fingerprint = _request_hash(**data)
            old = await _existing(c, command_key, kind, fingerprint)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            result_id = uuid4()
            await c.execute(
                insert(table).values(id=result_id, **data, created_at=self.clock())
            )
            command_id = await self._finish(
                c, None, kind, fingerprint, result_id, command_key
            )
            return CommandReceipt(command_id=command_id, result_id=result_id)
