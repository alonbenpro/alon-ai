"""Global organization identity and protected first-contact persistence."""

import pytest

pytestmark = pytest.mark.integration


def test_identity_snapshot_has_fixed_normalization_and_no_exclusive_domain():
    from alon_ai.services.schemas.records_organization import OrganizationSnapshot

    snapshot = OrganizationSnapshot(
        canonical_name="Fixture",
        organization_kind="LOCAL_BUSINESS",
        canonical_domain="shared.example",
        identifiers=(),
        aliases=(),
        locations=(),
    )
    assert snapshot.canonical_domain == "shared.example"


async def test_migration08_installs_normalized_protection(governance_engine):
    from sqlalchemy import inspect

    async with governance_engine.connect() as c:
        names = await c.run_sync(
            lambda connection: inspect(connection).get_table_names()
        )
    assert "record_org_observations" in names
    assert "record_org_keys" in names


from datetime import timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from test_contact_policy import NOW, candidate, setup
from test_governance import register
from test_product_records import roots

from alon_ai.db.repositories.accounting import (
    GovernanceProvisioner,
    GovernanceRepository,
)
from alon_ai.db.repositories.contact import (
    ContactAdmissionHook,
    ContactPolicyRepository,
)
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.repositories.records_organizations import OrganizationRepository
from alon_ai.db.repositories.supply import (
    ComposedContactSupplyHook,
    SupplyAdmissionHook,
)
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records_organization as org
from alon_ai.db.tables import supply as supply_schema
from alon_ai.integrations.schemas.provider import (
    CAPABILITIES,
    CallAttribution,
    Capability,
    ContentField,
    CostKnowledge,
    OperationRunKind,
    ProviderResultMetadata,
    Purpose,
    ResultStatus,
    SafeRequestMetadata,
    SystemActor,
    UsageComponent,
    UsageObservation,
)
from alon_ai.policies.provider_rights import (
    IntendedUse,
    ProviderUsageGrant,
    RuntimeContent,
)
from alon_ai.provider_usage.schemas.accounting import (
    CapabilityConfig,
    ControlPolicy,
    FxVersion,
    PriceBound,
    PriceVersion,
)
from alon_ai.provider_usage.service import ExecutionResult
from alon_ai.services.schemas.records import (
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
)
from alon_ai.services.schemas.records_organization import (
    GatewayEffectObservation,
    OrganizationSnapshot,
    RetainedOrganizationSource,
)

KEY = SecretStr("0123456789abcdef" * 2)
OWNER = UUID(int=1)
ServiceName = Literal[
    "provider-executor",
    "contact-resolution",
    "campaign-supply",
    "send-gateway",
    "calendar-gateway",
]
OrganizationKind = Literal["LOCAL_BUSINESS", "ONLINE_COMPANY"]


def snapshot(
    registered: str | None = "12345",
    kind: Literal["LOCAL_BUSINESS", "ONLINE_COMPANY"] = "LOCAL_BUSINESS",
):
    return OrganizationSnapshot.model_validate(
        {
            "canonical_name": "Synthetic branch company",
            "canonical_domain": "shared.example",
            "organization_kind": kind,
            "identifiers": (
                {"kind": "REGISTERED_ID", "namespace": "IL", "value": registered},
            )
            if registered
            else (),
            "aliases": ({"kind": "DOMAIN", "value": "former.example"},),
            "locations": (
                {
                    "country_code": "IL",
                    "city": "Fixture city",
                    "address": "Fixture street",
                    "branch_name": "North",
                },
            ),
        }
    )


async def provision_call(
    engine,
    exp,
    capability,
    fields,
    *,
    service: ServiceName = "provider-executor",
    contact_data=None,
    supply_data=None,
):
    attr = CallAttribution(
        experiment_id=exp,
        workflow_run_id=uuid4(),
        operation_run_id=uuid4(),
        operation_run_kind=OperationRunKind.SYSTEM,
        actor=SystemActor(service=service),
        correlation_id=uuid4(),
        logical_operation_id=uuid4(),
        config_version=uuid4(),
        deadline=NOW + timedelta(hours=1),
    )
    admin = GovernanceProvisioner(engine)
    await admin.scope(
        attr,
        gate_kind="CONTACT" if contact_data else "SUPPLY" if supply_data else "NONE",
    )
    use = IntendedUse(
        provider=CAPABILITIES[capability].provider,
        account_handle="fixture-" + uuid4().hex,
        capability=capability,
        plan_identifier="fixture",
        order_form_ref="fixture",
        terms_version="fixture",
        purpose=(
            Purpose.GATEWAY_EFFECT
            if capability == Capability.GMAIL_SEND
            else Purpose.GENERATION
            if capability == Capability.OPENAI_GENERATE
            else Purpose.LEAD_DISCOVERY
            if capability.name.startswith("BRAVE")
            else Purpose.RESEARCH
        ),
        required_fields=frozenset(fields),
    )
    policy = ControlPolicy(
        id=uuid4(),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        evidence_id=uuid4(),
        capability=capability,
        account_handle=use.account_handle,
        timeout_seconds=5,
        quota_limit=20,
        window_seconds=60,
        concurrency_limit=10,
        failure_threshold=3,
        failure_window_seconds=60,
        cooldown_seconds=10,
    )
    await register(admin, policy.evidence_id, "CONTROL", NOW)
    await admin.policy(policy)
    grant = ProviderUsageGrant(
        grant_id=uuid4(),
        version=1,
        **use.model_dump(exclude={"schema_version", "required_fields"}),
        outbound_use_permitted=True,
        storage_fields=use.required_fields,
        retention_rule_id=uuid4() if use.required_fields else None,
        retention_seconds=3600 if use.required_fields else None,
        approved_by=OWNER,
        approved_at=NOW - timedelta(days=2),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        supporting_evidence_ref=uuid4(),
    )
    await register(admin, grant.supporting_evidence_ref, "GRANT", NOW)
    await admin.grant(grant)
    price = PriceVersion(
        id=uuid4(),
        model_identifier="fixture-model"
        if capability == Capability.OPENAI_GENERATE
        else None,
        capability=capability,
        component=UsageComponent.REQUEST,
        currency="USD",
        unit_price=Decimal("0.01"),
        unit_quantity=Decimal(1),
        currency_quantum=Decimal(".01"),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        evidence_id=uuid4(),
    )
    fx = FxVersion(
        id=uuid4(),
        currency="USD",
        rate=Decimal("3.5"),
        effective_at=price.effective_at,
        expires_at=price.expires_at,
        evidence_id=uuid4(),
    )
    await register(admin, price.evidence_id, "PRICE", NOW)
    await admin.price(price)
    await register(admin, fx.evidence_id, "FX", NOW)
    await admin.fx(fx)
    config = CapabilityConfig(
        id=uuid4(),
        version=attr.config_version,
        workflow_id=attr.workflow_run_id,
        intended_use=use,
        prices=(PriceBound(price_id=price.id, max_quantity=Decimal(1)),),
        fx_id=fx.id,
        requested_count=1,
        adapter_version=uuid4(),
        model_identifier="fixture-model"
        if capability == Capability.OPENAI_GENERATE
        else None,
    )
    await admin.config(config)
    await admin.budgets(
        attr,
        provider=use.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(100),
        effective_at=price.effective_at,
        expires_at=price.expires_at,
    )
    hooks = {}
    if contact_data:
        supply, contact, batch, candidate_id = contact_data
        await supply.bind_operation(attr, batch, "CONTACT", config.id, candidate_id)
        await contact.bind_operation(attr, candidate_id, config.id)
        hooks = {
            "CONTACT": ComposedContactSupplyHook(
                supply, contact_owner=ContactAdmissionHook(contact)
            )
        }
    if supply_data:
        supply, batch = supply_data
        await supply.bind_operation(attr, batch, "DISCOVERY", config.id)
        hooks = {"SUPPLY": SupplyAdmissionHook(supply)}
    governed = GovernanceRepository(engine, clock=lambda: NOW, admission_hooks=hooks)
    if capability == Capability.GMAIL_SEND:
        # Fixture-only persisted call representing the future gateway, never a live send.
        call_id = uuid4()
        async with engine.begin() as c:
            await c.execute(
                insert(gov.calls).values(
                    id=call_id,
                    idempotency_key=uuid4(),
                    logical_operation_id=attr.logical_operation_id,
                    experiment_id=exp,
                    workflow_id=attr.workflow_run_id,
                    operation_id=attr.operation_run_id,
                    config_version=attr.config_version,
                    config_id=config.id,
                    attribution=attr.model_dump(mode="json"),
                    request=SafeRequestMetadata(config_ref=config.id).model_dump(
                        mode="json"
                    ),
                    grant_id=grant.grant_id,
                    grant_version=1,
                    currency="USD",
                    reserved=Decimal(".01"),
                    reserved_ils=Decimal(".04"),
                    state="RESERVED",
                    created_at=NOW,
                )
            )
        return governed, attr, config, grant, call_id, None
    receipt = await governed.reserve(
        attr, SafeRequestMetadata(config_ref=config.id), idempotency_key=uuid4()
    )
    receipt = await governed.dispatch(receipt.call_id)
    return governed, attr, config, grant, receipt.call_id, receipt


async def complete_content(engine, context, fields):
    governed, _attr, config, grant, call_id, receipt = context
    content = RuntimeContent(
        fields, grant=grant, intended_use=config.intended_use, observed_at=NOW
    )
    metadata = ProviderResultMetadata(
        capability=config.intended_use.capability,
        external_request_id="fixture-result",
        started_at=NOW,
        finished_at=NOW,
        status=ResultStatus.SUCCEEDED,
    )
    proof = await governed.finish_attempt(
        call_id, token=receipt.token, success=True, metadata=metadata
    )
    await governed.record_usage(
        call_id,
        (
            UsageObservation(
                component=UsageComponent.REQUEST,
                quantity=Decimal(1),
                currency="USD",
                cost=Decimal(".01"),
                knowledge=CostKnowledge.FINAL,
                observation_key=uuid4(),
            ),
        ),
        token=receipt.token,
    )
    final = await governed.reconcile(call_id, command_key=uuid4(), evidence_id=proof)
    retained = await governed.retain_content(call_id, content)
    return content, metadata, proof, final, retained


async def organization_fixture(
    engine,
    *,
    registered: str | None = "12345",
    kind: OrganizationKind = "LOCAL_BUSINESS",
    fields=None,
):
    supply, writer, exp, plan = await setup(engine)
    batch = await supply.begin_batch(exp, 1, plan, uuid4())
    candidate_id, fact = await candidate(supply, writer, exp, batch)
    context = await provision_call(
        engine,
        exp,
        Capability.FIRECRAWL_PAGE_CAPTURE,
        {ContentField.COMPANY, ContentField.URL} if fields is None else fields,
    )
    _, _, _, _, retained = await complete_content(
        engine,
        context,
        {ContentField.COMPANY: (snapshot(registered, kind).model_dump_json(),)},
    )
    _, profile, _, _, _ = await roots(engine)
    agent = uuid4()
    async with engine.begin() as c:
        await c.execute(
            insert(gov.agents).values(id=agent, workflow_id=context[1].workflow_run_id)
        )
        identity_id = await c.scalar(
            select(supply_schema.candidates.c.identity_id).where(
                supply_schema.candidates.c.id == candidate_id
            )
        )
    await ProductRecordsRepository(engine, clock=lambda: NOW).bind_roots(
        ProductExperiment(
            id=exp,
            operator_profile_id=profile.id,
            operator_profile_version=1,
            name="Organization fixture",
            created_at=NOW,
        ),
        ProductWorkflow(
            id=context[1].workflow_run_id,
            experiment_id=exp,
            role="DISCOVERY",
            created_at=NOW,
        ),
        ProductAgent(
            id=agent,
            workflow_id=context[1].workflow_run_id,
            role="DISCOVERY",
            created_at=NOW,
        ),
        command_key=uuid4(),
    )
    repository = OrganizationRepository(engine, lookup_key=KEY, clock=lambda: NOW)
    receipt = await repository.register_identity(
        exp,
        identity_id,
        RetainedOrganizationSource(
            retained_id=retained[0], value_index=0, observed_at=NOW
        ),
        registered_by=OWNER,
        command_key=uuid4(),
    )
    return (
        repository,
        receipt,
        (supply, writer, exp, plan, batch, candidate_id, fact),
        context,
    )


async def email_source(engine, fixture, *, email="shared@fixture.example"):
    repo, identity, data, _ = fixture
    supply, _, exp, _, batch, candidate_id, fact = data
    contact = ContactPolicyRepository(engine, supply, clock=lambda: NOW)
    context = await provision_call(
        engine,
        exp,
        Capability.BRAVE_LOCAL_DISCOVERY,
        {ContentField.EMAIL},
        service="contact-resolution",
        contact_data=(supply, contact, batch, candidate_id),
    )
    content, _metadata, _proof, final, retained = await complete_content(
        engine, context, {ContentField.EMAIL: (email,)}
    )
    source_fact = uuid4()
    await fact("SOURCE_EMAIL", contact_ref=source_fact)
    result = ExecutionResult(receipt=final, content=content)
    await contact.record_source(candidate_id, source_fact, result, uuid4())
    await repo.admit(identity.binding_id, acted_by=OWNER, command_key=uuid4())
    source = await repo.register_recipient(
        identity.binding_id,
        candidate_id,
        source_fact,
        RetainedOrganizationSource(
            retained_id=retained[0], value_index=0, observed_at=NOW
        ),
        acted_by=OWNER,
        command_key=uuid4(),
    )
    return source


async def test_registered_identity_converges_but_shared_domain_does_not(
    governance_engine,
):
    first = await organization_fixture(governance_engine)
    second = await organization_fixture(governance_engine, kind="ONLINE_COMPANY")
    unrelated = await organization_fixture(governance_engine, registered="67890")
    assert first[1].organization_id == second[1].organization_id
    assert first[1].organization_id != unrelated[1].organization_id
    assert (
        await first[0].identity(second[1].evidence_id)
    ).organization_kind == "ONLINE_COMPANY"
    async with governance_engine.connect() as c:
        assert len((await c.execute(select(org.locations))).all()) == 3
        assert "shared.example" not in str((await c.execute(select(org.keys))).all())


async def test_reservation_race_shared_mailbox_and_safe_release(governance_engine):
    import asyncio

    first = await organization_fixture(governance_engine)
    second = await organization_fixture(governance_engine, registered="67890")
    a = await email_source(governance_engine, first)
    b = await email_source(governance_engine, second)
    results = await asyncio.gather(
        first[0].reserve(a.result_id, acted_by=OWNER, command_key=uuid4()),
        second[0].reserve(b.result_id, acted_by=OWNER, command_key=uuid4()),
        return_exceptions=True,
    )
    assert sum(isinstance(r, ProductRecordsDenied) for r in results) == 1
    winner = next(r for r in results if not isinstance(r, Exception))
    async with governance_engine.connect() as c:
        r = (
            (
                await c.execute(
                    select(org.reservations).where(
                        org.reservations.c.id == winner.result_id
                    )
                )
            )
            .mappings()
            .one()
        )
    loser = second if r["experiment_id"] == first[2][2] else first
    assert await loser[0].working_candidates(loser[2][2]) == ()
    await first[0].release(winner.result_id, acted_by=OWNER, command_key=uuid4())
    assert len(await loser[0].working_candidates(loser[2][2])) == 1


async def test_retention_and_key_failure_do_not_leak_or_reuse_source_content(
    governance_engine,
):
    fixture = await organization_fixture(governance_engine)
    _repo, identity, data, _context = fixture
    bad = OrganizationRepository(
        governance_engine, lookup_key=SecretStr("x" * 32), clock=lambda: NOW
    )
    with pytest.raises(ProductRecordsDenied) as exc:
        await bad.identity(identity.evidence_id)
    assert "x" * 32 not in str(exc.value)
    assert KEY.get_secret_value() not in repr(exc.value)
    late = OrganizationRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW + timedelta(hours=2)
    )
    with pytest.raises(ProductRecordsDenied):
        await late.identity(identity.evidence_id)
    assert await late.working_candidates(data[2]) == ()
    assert (
        await GovernanceRepository(
            governance_engine, clock=lambda: NOW + timedelta(hours=2)
        ).purge_expired()
        == 1
    )
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(
                select(org.evidence.c.id).where(
                    org.evidence.c.id == identity.evidence_id
                )
            )
            == identity.evidence_id
        )


async def test_context_matches_quarantine_until_explicit_identity_resolution(
    governance_engine,
):
    first = await organization_fixture(governance_engine, registered=None)
    second = await organization_fixture(
        governance_engine, registered=None, kind="ONLINE_COMPANY"
    )
    async with governance_engine.connect() as c:
        conflict = (await c.execute(select(org.conflicts))).mappings().one()
    for fixture in (first, second):
        admission = await fixture[0].admit(
            fixture[1].binding_id, acted_by=OWNER, command_key=uuid4()
        )
        assert not admission.admitted and admission.reason == "IDENTITY_CONFLICT"
    await first[0].resolve_identity_conflict(
        conflict["id"],
        second[1].evidence_id,
        resolution="SAME_ORGANIZATION",
        acted_by=OWNER,
        reason_code="OFFICIAL_IDENTITY_CONFIRMED",
        command_key=uuid4(),
    )
    admitted = await first[0].admit(
        first[1].binding_id, acted_by=OWNER, command_key=uuid4()
    )
    assert admitted.admitted
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(
                text("SELECT record_org_canonical(:id)"),
                {"id": second[1].organization_id},
            )
            == first[1].organization_id
        )
    third = await organization_fixture(governance_engine, registered=None)
    async with governance_engine.connect() as c:
        conflicts = (
            (
                await c.execute(
                    select(org.conflicts).where(
                        org.conflicts.c.organization_id == third[1].organization_id
                    )
                )
            )
            .mappings()
            .all()
        )
    for pending in conflicts:
        await first[0].resolve_identity_conflict(
            pending["id"],
            third[1].evidence_id,
            resolution="INDEPENDENT_BUSINESS",
            acted_by=OWNER,
            reason_code="DISTINCT_LEGAL_BUSINESS",
            command_key=uuid4(),
        )
    assert (
        await third[0].admit(third[1].binding_id, acted_by=OWNER, command_key=uuid4())
    ).admitted


async def test_exact_gateway_outcome_quarantines_then_confirms_permanent_contact(
    governance_engine,
):
    fixture = await organization_fixture(governance_engine)
    repo, identity, data, _ = fixture
    source = await email_source(governance_engine, fixture)
    reservation = await repo.reserve(
        source.result_id, acted_by=OWNER, command_key=uuid4()
    )
    _governed, _attr, config, _grant, call_id, _ = await provision_call(
        governance_engine,
        data[2],
        Capability.GMAIL_SEND,
        {ContentField.MESSAGE},
        service="send-gateway",
    )
    effect = await repo.bind_effect(
        reservation.result_id,
        call_id,
        mailbox_id=uuid4(),
        rfc_message_id=uuid4(),
        acted_by=OWNER,
        command_key=uuid4(),
    )
    async with governance_engine.begin() as c:
        policy_id = await c.scalar(
            select(gov.authorities.c.policy_id).where(
                gov.authorities.c.account == config.intended_use.account_handle,
                gov.authorities.c.capability == "GMAIL_SEND",
            )
        )
        await c.execute(
            update(gov.calls)
            .where(gov.calls.c.id == call_id)
            .values(
                state="DISPATCHED",
                dispatch_at=NOW,
                lease_until=NOW + timedelta(seconds=5),
                token=uuid4(),
                policy_id=policy_id,
            )
        )
        await c.execute(
            update(gov.calls)
            .where(gov.calls.c.id == call_id)
            .values(state="RECONCILING")
        )
        row = dict(
            (
                await c.execute(
                    select(org.effects).where(org.effects.c.id == effect.result_id)
                )
            )
            .mappings()
            .one()
        )
    with pytest.raises(ProductRecordsDenied):
        await repo.release(reservation.result_id, acted_by=OWNER, command_key=uuid4())
    identity_fields = {k: v for k, v in row.items() if k not in {"id", "created_at"}}
    ambiguous = GatewayEffectObservation(
        id=uuid4(),
        effect_id=effect.result_id,
        **identity_fields,
        outcome="AMBIGUOUS",
        observed_at=NOW,
    )
    await repo.ingest_gateway_observation(ambiguous, command_key=uuid4())
    assert await repo.working_candidates(data[2]) == ()
    evidence_id = uuid4()
    from alon_ai.provider_usage.schemas.accounting import EvidenceRecord

    metadata = ProviderResultMetadata(
        capability=Capability.GMAIL_SEND,
        external_request_id="exact-request",
        started_at=NOW,
        finished_at=NOW,
        status=ResultStatus.SUCCEEDED,
    )
    async with governance_engine.begin() as c:
        await c.execute(
            update(gov.calls)
            .where(gov.calls.c.id == call_id)
            .values(
                state="FINAL",
                finished_at=NOW,
                result_metadata=metadata.model_dump(mode="json"),
            )
        )
    await GovernanceProvisioner(governance_engine).evidence(
        EvidenceRecord(
            id=evidence_id,
            kind="PROVIDER_RESULT",
            mode="TRUSTED_REFERENCE",
            registered_by=call_id,
            registered_at=NOW,
            call_id=call_id,
        )
    )
    confirmed = GatewayEffectObservation(
        id=uuid4(),
        effect_id=effect.result_id,
        **identity_fields,
        outcome="CONFIRMED",
        result_evidence_id=evidence_id,
        provider_request_id="exact-request",
        provider_message_id="exact-message",
        reconciles_id=ambiguous.id,
        observed_at=NOW,
    )
    for changed in [
        {"recipient_lookup_hash": "0" * 64},
        {"operation_id": uuid4()},
        {"provider_request_id": "other-request"},
        {"reconciles_id": None},
    ]:
        with pytest.raises(ProductRecordsDenied):
            await repo.ingest_gateway_observation(
                confirmed.model_copy(update=changed), command_key=uuid4()
            )
    await repo.ingest_gateway_observation(confirmed, command_key=uuid4())
    with pytest.raises(ProductRecordsDenied):
        await repo.release(reservation.result_id, acted_by=OWNER, command_key=uuid4())
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(
                text(
                    "SELECT state FROM record_org_contact_state WHERE organization_id=:id"
                ),
                {"id": identity.organization_id},
            )
            == "CONTACTED"
        )
    later = await organization_fixture(governance_engine, registered="different")
    await email_source(governance_engine, later)
    exclusion = await later[0].admit(
        later[1].binding_id, acted_by=OWNER, command_key=uuid4()
    )
    assert not exclusion.admitted and exclusion.reason == "CONTACTED"
    await repo.merge(
        identity.organization_id,
        later[1].organization_id,
        later[1].evidence_id,
        acted_by=OWNER,
        reason_code="CONFIRMED_SAME_LEGAL_IDENTITY",
        command_key=uuid4(),
    )
    assert await later[0].working_candidates(later[2][2]) == ()
    late = OrganizationRepository(
        governance_engine, lookup_key=KEY, clock=lambda: NOW + timedelta(hours=2)
    )
    assert await late.working_candidates(later[2][2]) == ()


async def test_raw_guards_and_separate_suppression_are_fail_closed(governance_engine):
    fixture = await organization_fixture(governance_engine)
    repo, identity, data, _ = fixture
    with pytest.raises(SQLAlchemyError):
        async with governance_engine.begin() as c:
            await c.execute(
                insert(org.admissions).values(
                    id=uuid4(),
                    binding_id=identity.binding_id,
                    organization_id=identity.organization_id,
                    experiment_id=data[2],
                    created_at=NOW,
                )
            )
    source = await email_source(governance_engine, fixture)
    async with governance_engine.connect() as c:
        recipient = await c.scalar(
            select(org.recipient_sources.c.recipient_id).where(
                org.recipient_sources.c.id == source.result_id
            )
        )
    await repo.suppress(
        recipient_id=recipient,
        acted_by=OWNER,
        reason_code="NO_FUTURE_CONTACT",
        command_key=uuid4(),
    )
    assert await repo.working_candidates(data[2]) == ()
    with pytest.raises(ProductRecordsDenied):
        await repo.reserve(source.result_id, acted_by=OWNER, command_key=uuid4())
    async with governance_engine.connect() as c:
        assert (
            await c.scalar(
                text(
                    "SELECT state FROM record_org_contact_state WHERE organization_id=:id"
                ),
                {"id": identity.organization_id},
            )
            == "NEVER_CONTACTED"
        )


async def test_company_container_cannot_bypass_url_field_rights(governance_engine):
    with pytest.raises(ProductRecordsDenied):
        await organization_fixture(governance_engine, fields={ContentField.COMPANY})
    async with governance_engine.connect() as c:
        assert not (await c.execute(select(org.organizations))).all()
        assert not (await c.execute(select(org.keys))).all()
