"""Synthetic contact precedence through real PostgreSQL and the governed executor."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr

from alon_ai.db.repositories.accounting import GovernanceProvisioner
from alon_ai.integrations.fakes import (
    FakeBraveProvider,
    FakeContactDiscoveryProvider,
    FakeEmailVerificationProvider,
    FakeSession,
    FixtureScenario,
)
from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    CallAttribution,
    Capability,
    ContactDiscoveryRequest,
    ContentField,
    EmailPresence,
    EmailSourceObservation,
    EmailVerificationRequest,
    OperationRunKind,
    Provider,
    ProviderCallResult,
    Purpose,
    SafeRequestMetadata,
    SystemActor,
    UsageComponent,
    VerificationStatus,
)
from alon_ai.policies.campaign_supply import (
    DiscoveryPlan,
    Filter,
    IdentityEvidence,
    ReferenceEvidence,
    SupplyFact,
)
from alon_ai.policies.provider_rights import (
    GrantEvent,
    GrantEventKind,
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

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 12, 12, tzinfo=UTC)


async def register(admin, id_, kind, now, call_id=None):
    from alon_ai.provider_usage.schemas.accounting import EvidenceRecord

    await admin.evidence(
        EvidenceRecord(
            id=id_,
            kind=kind,
            mode="SYNTHETIC",
            registered_by=UUID(int=1),
            registered_at=now,
            call_id=call_id,
        )
    )


async def setup(engine):
    from sqlalchemy import insert

    from alon_ai.db.repositories.supply import (
        CampaignSupplyRepository,
        SupplyEvidenceWriter,
    )
    from alon_ai.db.tables.accounting import experiments

    exp, rule, verifier = uuid4(), uuid4(), uuid4()
    async with engine.begin() as connection:
        await connection.execute(insert(experiments).values(id=exp))
    supply = CampaignSupplyRepository(engine, clock=lambda: NOW)
    writer = SupplyEvidenceWriter(engine)
    query = Filter(dimension="QUERY", value=uuid4())
    for ref, kind, definition, dimension in (
        (rule, "QUALIFICATION_RULE", "synthetic fixed rules", None),
        (verifier, "VERIFICATION_POLICY", "synthetic verifier", None),
        (query.value, "FILTER", "synthetic query", query.dimension),
    ):
        await writer.reference(
            ReferenceEvidence(
                id=ref,
                experiment_id=exp,
                kind=kind,  # pyright: ignore[reportArgumentType]
                definition=definition,
                dimension=dimension,  # pyright: ignore[reportArgumentType]
                mode="SYNTHETIC",
                registered_by=uuid4(),
            )
        )
    plan = DiscoveryPlan(qualification_rule_id=rule, filters=(query,))
    await supply.create(exp, plan, (query,), verifier, NOW + timedelta(hours=1))
    return supply, writer, exp, plan


async def candidate(supply, writer, exp, batch):
    provenance = uuid4()
    await writer.reference(
        ReferenceEvidence(
            id=provenance,
            experiment_id=exp,
            kind="INDEPENDENT_SOURCE",
            definition="synthetic permitted source",
            mode="SYNTHETIC",
            registered_by=uuid4(),
        )
    )
    identity = IdentityEvidence(
        id=uuid4(),
        experiment_id=exp,
        provenance_ref=provenance,
        normalized_key="synthetic-contact-candidate",
        mode="SYNTHETIC",
        registered_by=uuid4(),
        observed_at=NOW,
        valid_until=NOW + timedelta(hours=2),
    )
    await writer.identity(identity)

    async def fact(kind, **values):
        fact_id = (
            values.get("contact_ref", uuid4()) if kind == "SOURCE_EMAIL" else uuid4()
        )
        await writer.fact(
            SupplyFact(
                id=fact_id,
                identity_id=identity.id,
                kind=kind,
                mode="SYNTHETIC",
                registered_by=identity.registered_by,
                observed_at=NOW,
                valid_until=NOW + timedelta(hours=2),
                **values,
            )
        )
        return fact_id

    clearance = await fact("IDENTITY_CLEAR")
    candidate_id = await supply.admit_candidate(
        batch,
        identity.id,
        clearance,
        uuid4(),
        observations=(await supply.batch_plan(batch)).filters,
    )
    return candidate_id, fact


async def provision(
    engine,
    supply,
    contact,
    *,
    experiment_id,
    workflow_id,
    batch_id,
    candidate_id,
    capability,
    component,
    source_case_id=None,
    source_fact_id=None,
    deadline_minutes=30,
):
    kind = (
        OperationRunKind.VERIFICATION
        if capability is Capability.HUNTER_EMAIL_VERIFICATION
        else OperationRunKind.ENRICHMENT
        if capability
        in {
            Capability.HUNTER_COMPANY_ENRICHMENT,
            Capability.HUNTER_PERSON_ENRICHMENT,
        }
        else OperationRunKind.DISCOVERY
    )
    attr = CallAttribution(
        experiment_id=experiment_id,
        workflow_run_id=workflow_id,
        operation_run_id=uuid4(),
        operation_run_kind=kind,
        actor=SystemActor(service="contact-resolution"),
        correlation_id=uuid4(),
        logical_operation_id=uuid4(),
        config_version=uuid4(),
        deadline=NOW + timedelta(minutes=deadline_minutes),
    )
    admin = GovernanceProvisioner(engine)
    await admin.scope(attr, gate_kind="CONTACT")
    provider = (
        Provider.BRAVE if capability.name.startswith("BRAVE") else Provider.HUNTER
    )
    purpose = (
        Purpose.LEAD_DISCOVERY
        if provider is Provider.BRAVE
        else Purpose.EMAIL_VERIFICATION
        if capability is Capability.HUNTER_EMAIL_VERIFICATION
        else Purpose.CONTACT_DISCOVERY
    )
    field = (
        ContentField.TEXT
        if capability is Capability.HUNTER_EMAIL_VERIFICATION
        else ContentField.EMAIL
    )
    use = IntendedUse(
        provider=provider,
        account_handle="synthetic-" + capability.value.lower().replace("_", "-"),
        capability=capability,
        plan_identifier="synthetic-plan",
        order_form_ref="synthetic-order",
        terms_version="synthetic-v1",
        purpose=purpose,
        required_fields=frozenset({field}),
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
        retention_rule_id=uuid4(),
        retention_seconds=3600,
        approved_by=UUID(int=1),
        approved_at=NOW - timedelta(days=2),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        supporting_evidence_ref=uuid4(),
    )
    await register(admin, grant.supporting_evidence_ref, "GRANT", NOW)
    await admin.grant(grant)
    price = PriceVersion(
        id=uuid4(),
        capability=capability,
        component=component,
        currency="USD",
        unit_price=Decimal("0.01"),
        unit_quantity=Decimal(1),
        currency_quantum=Decimal("0.01"),
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
    for proof_id, proof_kind in ((price.evidence_id, "PRICE"), (fx.evidence_id, "FX")):
        await register(admin, proof_id, proof_kind, NOW)
    await admin.price(price)
    await admin.fx(fx)
    config = CapabilityConfig(
        id=uuid4(),
        version=attr.config_version,
        workflow_id=workflow_id,
        intended_use=use,
        prices=(PriceBound(price_id=price.id, max_quantity=Decimal(1)),),
        fx_id=fx.id,
        requested_count=1,
        adapter_version=uuid4(),
    )
    await admin.config(config)
    await admin.budgets(
        attr,
        provider=provider,
        currencies=("USD", "ILS"),
        limit=Decimal(100),
        effective_at=price.effective_at,
        expires_at=price.expires_at,
    )
    await supply.bind_operation(attr, batch_id, "CONTACT", config.id, candidate_id)
    await contact.bind_operation(
        attr,
        candidate_id,
        config.id,
        source_case_id=source_case_id,
        source_fact_id=source_fact_id,
    )
    return attr, config, grant, use


@pytest.mark.parametrize("revoke_before_resolve", [False, True])
async def test_brave_present_blocks_all_hunter_discovery_and_verifies_separately(
    governance_engine, revoke_before_resolve
):
    from alon_ai.db.repositories.accounting import GovernanceRepository
    from alon_ai.db.repositories.contact import (
        ContactAdmissionHook,
        ContactPolicyRepository,
    )
    from alon_ai.db.repositories.supply import ComposedContactSupplyHook
    from alon_ai.integrations.contact import ConfiguredContactAdapter
    from alon_ai.policies.contact import (
        ContactPolicyDenied,
        observe_email_presence,
        observe_verification_status,
    )
    from alon_ai.provider_usage.schemas.accounting import (
        AccountingDenied,
        CallState,
        Reason,
    )
    from alon_ai.provider_usage.service import GovernedExecutor

    supply, writer, exp, plan = await setup(governance_engine)
    batch = await supply.begin_batch(exp, 1, plan, uuid4())
    candidate_id, fact = await candidate(supply, writer, exp, batch)
    contact = ContactPolicyRepository(governance_engine, supply, clock=lambda: NOW)
    hook = ComposedContactSupplyHook(
        supply, contact_owner=ContactAdmissionHook(contact)
    )
    workflow = uuid4()

    brave_attr, brave_config, brave_grant, brave_use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        component=UsageComponent.REQUEST,
    )
    brave_session = FakeSession(
        grants={Capability.BRAVE_LOCAL_DISCOVERY: brave_grant},
        intended_uses={Capability.BRAVE_LOCAL_DISCOVERY: brave_use},
        clock=lambda: NOW,
    )
    brave_adapter = ConfiguredContactAdapter(
        FakeBraveProvider(brave_session),
        BraveSearchRequest(
            capability=Capability.BRAVE_LOCAL_DISCOVERY,
            query=SecretStr("synthetic query"),
            limit=1,
        ),
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
    )
    governed = GovernanceRepository(
        governance_engine, clock=lambda: NOW, admission_hooks={"CONTACT": hook}
    )
    brave_result = await GovernedExecutor(
        governed, adapters={brave_config.adapter_version: brave_adapter}
    ).execute(
        brave_attr,
        SafeRequestMetadata(config_ref=brave_config.id),
        idempotency_key=uuid4(),
    )
    assert brave_result.receipt.state is CallState.FINAL
    assert brave_result.content is not None
    assert (
        observe_email_presence(brave_result.content, brave_grant, (), now=NOW)
        is EmailPresence.PRESENT
    )
    false_absent = await fact("EMAIL_ABSENT")
    with pytest.raises(ContactPolicyDenied, match="SOURCE_FACT"):
        await contact.record_source(
            candidate_id,
            false_absent,
            brave_result,
            uuid4(),
        )
    source_fact = uuid4()
    await fact("SOURCE_EMAIL", contact_ref=source_fact)
    decision = await contact.record_source(
        candidate_id,
        source_fact,
        brave_result,
        uuid4(),
    )
    assert decision.decision == "AVOIDED_HUNTER"
    assert decision.counterfactual_savings == "UNAVAILABLE"

    hunter = {
        Capability.HUNTER_DOMAIN_SEARCH: ("domain_search", UsageComponent.DISCOVERY),
        Capability.HUNTER_EMAIL_FINDER: ("email_finder", UsageComponent.DISCOVERY),
        Capability.HUNTER_COMPANY_ENRICHMENT: (
            "company_enrichment",
            UsageComponent.ENRICHMENT,
        ),
        Capability.HUNTER_PERSON_ENRICHMENT: (
            "person_enrichment",
            UsageComponent.ENRICHMENT,
        ),
    }
    for capability, (_method, component) in hunter.items():
        attr, config, grant, use = await provision(
            governance_engine,
            supply,
            contact,
            experiment_id=exp,
            workflow_id=workflow,
            batch_id=batch,
            candidate_id=candidate_id,
            capability=capability,
            component=component,
            source_case_id=candidate_id,
        )
        source = EmailSourceObservation(
            business_id=candidate_id,
            provider_call_id=brave_result.receipt.call_id,
            capability=Capability.BRAVE_LOCAL_DISCOVERY,
            grant_id=brave_grant.grant_id,
            grant_version=1,
            evidence_ref=source_fact,
            observed_at=NOW,
            presence=EmailPresence.PRESENT,
        )
        request = ContactDiscoveryRequest(
            business_id=candidate_id,
            brave_observation=source,
            domain=SecretStr("example.test"),
        )
        session = FakeSession(
            grants={capability: grant},
            intended_uses={capability: use},
            clock=lambda: NOW,
        )
        adapter = ConfiguredContactAdapter(
            FakeContactDiscoveryProvider(session), request, capability=capability
        )
        with pytest.raises(AccountingDenied) as denied:
            await GovernedExecutor(
                governed, adapters={config.adapter_version: adapter}
            ).execute(
                attr,
                SafeRequestMetadata(config_ref=config.id),
                idempotency_key=uuid4(),
            )
        assert denied.value.reason is Reason.GATE
        assert session.invocations == ()

    verifier_attr, verifier_config, verifier_grant, verifier_use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=Capability.HUNTER_EMAIL_VERIFICATION,
        component=UsageComponent.VERIFICATION,
        source_case_id=candidate_id,
        source_fact_id=source_fact,
    )
    verifier_session = FakeSession(
        grants={Capability.HUNTER_EMAIL_VERIFICATION: verifier_grant},
        intended_uses={Capability.HUNTER_EMAIL_VERIFICATION: verifier_use},
        clock=lambda: NOW,
    )
    verifier_request = EmailVerificationRequest(
        business_id=candidate_id,
        email_candidate_id=source_fact,
        source_evidence_ref=source_fact,
        business_match_ref=source_fact,
        address=SecretStr("synthetic@example.test"),
    )
    verifier_adapter = ConfiguredContactAdapter(
        FakeEmailVerificationProvider(verifier_session),
        verifier_request,
        capability=Capability.HUNTER_EMAIL_VERIFICATION,
    )
    verification_key = uuid4()
    verification_result = await GovernedExecutor(
        governed, adapters={verifier_config.adapter_version: verifier_adapter}
    ).execute(
        verifier_attr,
        SafeRequestMetadata(config_ref=verifier_config.id),
        idempotency_key=verification_key,
    )
    assert verification_result.content is not None
    assert (
        observe_verification_status(
            verification_result.content, verifier_grant, (), now=NOW
        )
        is VerificationStatus.VALID
    )
    policy_id = await supply.verification_policy(exp)
    verified_fact = await fact(
        "VERIFIED", contact_ref=source_fact, policy_ref=policy_id
    )
    await contact.record_attempt(
        verification_result, uuid4(), output_fact_id=verified_fact
    )
    if revoke_before_resolve:
        admin = GovernanceProvisioner(governance_engine)
        revoked = GrantEvent(
            event_id=uuid4(),
            grant_id=brave_grant.grant_id,
            grant_version=brave_grant.version,
            kind=GrantEventKind.REVOKED,
            effective_at=NOW,
            actor_id=uuid4(),
            evidence_ref=uuid4(),
        )
        await register(admin, revoked.evidence_ref, "GRANT_EVENT", NOW)
        await admin.grant_event(revoked)
        with pytest.raises(ContactPolicyDenied, match="SOURCE_RIGHTS"):
            await contact.resolve(candidate_id)
        from sqlalchemy import select

        from alon_ai.db.tables import supply as contact_supply_schema

        async with governance_engine.connect() as connection:
            assert (
                await connection.execute(
                    select(contact_supply_schema.contacts).where(
                        contact_supply_schema.contacts.c.candidate_id == candidate_id
                    )
                )
            ).one_or_none() is None
        return
    assert await contact.resolve(candidate_id) == "SUPPORTED"
    assert [x.capability for x in verifier_session.invocations] == [
        Capability.HUNTER_EMAIL_VERIFICATION
    ]
    replay = await GovernedExecutor(
        governed, adapters={verifier_config.adapter_version: verifier_adapter}
    ).execute(
        verifier_attr,
        SafeRequestMetadata(config_ref=verifier_config.id),
        idempotency_key=verification_key,
    )
    assert replay.content is None
    assert len(verifier_session.invocations) == 1
    with pytest.raises(ContactPolicyDenied, match="MISSING_PROOF"):
        await contact.bind_operation(
            verifier_attr,
            candidate_id,
            verifier_config.id,
            source_case_id=candidate_id,
            source_fact_id=uuid4(),
        )

    admin = GovernanceProvisioner(governance_engine)
    future_activation = GrantEvent(
        event_id=uuid4(),
        grant_id=brave_grant.grant_id,
        grant_version=brave_grant.version,
        kind=GrantEventKind.ACTIVATED,
        effective_at=NOW + timedelta(minutes=3),
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    await register(admin, future_activation.evidence_ref, "GRANT_EVENT", NOW)
    await admin.grant_event(future_activation)
    async with governance_engine.begin() as connection:
        await ContactAdmissionHook(contact).admit(
            connection,
            verifier_attr,
            verification_result.receipt.call_id,
            "DISPATCH",
        )
    future_grant = brave_grant.model_copy(
        update={
            "grant_id": uuid4(),
            "effective_at": NOW + timedelta(minutes=20),
            "supporting_evidence_ref": uuid4(),
        }
    )
    await register(admin, future_grant.supporting_evidence_ref, "GRANT", NOW)
    await admin.grant(future_grant)
    with pytest.raises(AccountingDenied) as future_grant_denied:
        async with governance_engine.begin() as connection:
            await ContactAdmissionHook(contact).admit(
                connection,
                verifier_attr,
                verification_result.receipt.call_id,
                "DISPATCH",
            )
    assert future_grant_denied.value.reason is Reason.GATE
    short_attr = verifier_attr.model_copy(
        update={"deadline": NOW + timedelta(minutes=5)}
    )
    async with governance_engine.begin() as connection:
        await ContactAdmissionHook(contact).admit(
            connection,
            short_attr,
            verification_result.receipt.call_id,
            "DISPATCH",
        )
    future_revocation = GrantEvent(
        event_id=uuid4(),
        grant_id=brave_grant.grant_id,
        grant_version=brave_grant.version,
        kind=GrantEventKind.REVOKED,
        effective_at=NOW + timedelta(minutes=10),
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    await register(admin, future_revocation.evidence_ref, "GRANT_EVENT", NOW)
    await admin.grant_event(future_revocation)
    with pytest.raises(AccountingDenied) as future_event_denied:
        async with governance_engine.begin() as connection:
            await ContactAdmissionHook(contact).admit(
                connection,
                verifier_attr.model_copy(
                    update={"deadline": NOW + timedelta(minutes=15)}
                ),
                verification_result.receipt.call_id,
                "DISPATCH",
            )
    assert future_event_denied.value.reason is Reason.GATE
    async with governance_engine.begin() as connection:
        await ContactAdmissionHook(contact).admit(
            connection,
            short_attr,
            verification_result.receipt.call_id,
            "DISPATCH",
        )
    revoked = GrantEvent(
        event_id=uuid4(),
        grant_id=brave_grant.grant_id,
        grant_version=brave_grant.version,
        kind=GrantEventKind.REVOKED,
        effective_at=NOW,
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    await register(admin, revoked.evidence_ref, "GRANT_EVENT", NOW)
    await admin.grant_event(revoked)
    with pytest.raises(AccountingDenied) as source_denied:
        async with governance_engine.begin() as connection:
            await ContactAdmissionHook(contact).admit(
                connection,
                verifier_attr,
                verification_result.receipt.call_id,
                "DISPATCH",
            )
    assert source_denied.value.reason is Reason.RIGHTS

    import hashlib

    from sqlalchemy import select

    from alon_ai.db.tables import accounting as governance_schema

    sentinel = "synthetic@example.test"
    digest = hashlib.sha256(sentinel.encode()).hexdigest()
    async with governance_engine.connect() as connection:
        for table in governance_schema.metadata.sorted_tables:
            dump = str((await connection.execute(select(table))).mappings().all())
            assert sentinel not in dump and digest not in dump


@pytest.mark.parametrize("revoke_selected_before_resolve", [False, True])
async def test_evidenced_absence_allows_bounded_fallback_but_invalid_is_no_email(
    governance_engine, revoke_selected_before_resolve
):
    from alon_ai.db.repositories.accounting import GovernanceRepository
    from alon_ai.db.repositories.contact import (
        ContactAdmissionHook,
        ContactPolicyRepository,
    )
    from alon_ai.db.repositories.supply import ComposedContactSupplyHook
    from alon_ai.integrations.contact import ConfiguredContactAdapter
    from alon_ai.policies.contact import (
        ContactPolicyDenied,
        observe_email_presence,
        observe_verification_status,
    )
    from alon_ai.provider_usage.schemas.accounting import AccountingDenied, Reason
    from alon_ai.provider_usage.service import GovernedExecutor

    supply, writer, exp, plan = await setup(governance_engine)
    batch = await supply.begin_batch(exp, 1, plan, uuid4())
    candidate_id, fact = await candidate(supply, writer, exp, batch)
    contact = ContactPolicyRepository(governance_engine, supply, clock=lambda: NOW)
    hook = ComposedContactSupplyHook(
        supply, contact_owner=ContactAdmissionHook(contact)
    )
    governed = GovernanceRepository(
        governance_engine, clock=lambda: NOW, admission_hooks={"CONTACT": hook}
    )
    workflow = uuid4()
    brave_attr, brave_config, brave_grant, brave_use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        component=UsageComponent.REQUEST,
        deadline_minutes=50,
    )
    brave_session = FakeSession(
        grants={Capability.BRAVE_LOCAL_DISCOVERY: brave_grant},
        intended_uses={Capability.BRAVE_LOCAL_DISCOVERY: brave_use},
        clock=lambda: NOW,
    )

    class AbsentBrave:
        async def search(self, request):
            base = await FakeBraveProvider(brave_session).search(request)
            return ProviderCallResult(
                base.metadata,
                RuntimeContent(
                    {ContentField.EMAIL: ()},
                    grant=brave_grant,
                    intended_use=brave_use,
                    observed_at=NOW,
                ),
            )

    brave = await GovernedExecutor(
        governed,
        adapters={
            brave_config.adapter_version: ConfiguredContactAdapter(
                AbsentBrave(),
                BraveSearchRequest(
                    capability=Capability.BRAVE_LOCAL_DISCOVERY,
                    query=SecretStr("synthetic query"),
                    limit=1,
                ),
                capability=Capability.BRAVE_LOCAL_DISCOVERY,
            )
        },
    ).execute(
        brave_attr,
        SafeRequestMetadata(config_ref=brave_config.id),
        idempotency_key=uuid4(),
    )
    assert brave.content is not None
    assert (
        observe_email_presence(brave.content, brave_grant, (), now=NOW)
        is EmailPresence.ABSENT
    )
    absent_fact = await fact("EMAIL_ABSENT")
    source = await contact.record_source(
        candidate_id,
        absent_fact,
        brave,
        uuid4(),
    )
    assert source.decision == "FALLBACK_ALLOWED"

    hunter_capability = Capability.HUNTER_DOMAIN_SEARCH
    hunter_attr, hunter_config, hunter_grant, hunter_use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=hunter_capability,
        component=UsageComponent.DISCOVERY,
        source_case_id=candidate_id,
        deadline_minutes=10,
    )
    hunter_session = FakeSession(
        grants={hunter_capability: hunter_grant},
        intended_uses={hunter_capability: hunter_use},
        clock=lambda: NOW,
    )
    hunter_request = ContactDiscoveryRequest(
        business_id=candidate_id,
        brave_observation=EmailSourceObservation(
            business_id=candidate_id,
            provider_call_id=brave.receipt.call_id,
            capability=Capability.BRAVE_LOCAL_DISCOVERY,
            grant_id=brave_grant.grant_id,
            grant_version=1,
            evidence_ref=absent_fact,
            observed_at=NOW,
            presence=EmailPresence.ABSENT,
        ),
        domain=SecretStr("example.test"),
    )
    hunter = await GovernedExecutor(
        governed,
        adapters={
            hunter_config.adapter_version: ConfiguredContactAdapter(
                FakeContactDiscoveryProvider(hunter_session),
                hunter_request,
                capability=hunter_capability,
            )
        },
    ).execute(
        hunter_attr,
        SafeRequestMetadata(config_ref=hunter_config.id),
        idempotency_key=uuid4(),
    )
    discovered_fact = uuid4()
    await fact("SOURCE_EMAIL", contact_ref=discovered_fact)
    await contact.record_attempt(hunter, uuid4(), output_fact_id=discovered_fact)
    assert [x.capability for x in hunter_session.invocations] == [hunter_capability]

    verify_attr, verify_config, verify_grant, verify_use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=Capability.HUNTER_EMAIL_VERIFICATION,
        component=UsageComponent.VERIFICATION,
        source_case_id=candidate_id,
        source_fact_id=discovered_fact,
        deadline_minutes=5,
    )
    verify_session = FakeSession(
        grants={Capability.HUNTER_EMAIL_VERIFICATION: verify_grant},
        intended_uses={Capability.HUNTER_EMAIL_VERIFICATION: verify_use},
        clock=lambda: NOW,
    )

    class InvalidVerifier:
        async def verify(self, request):
            base = await FakeEmailVerificationProvider(verify_session).verify(request)
            return ProviderCallResult(
                base.metadata,
                RuntimeContent(
                    {ContentField.TEXT: ("INVALID",)},
                    grant=verify_grant,
                    intended_use=verify_use,
                    observed_at=NOW,
                ),
            )

    verification = await GovernedExecutor(
        governed,
        adapters={
            verify_config.adapter_version: ConfiguredContactAdapter(
                InvalidVerifier(),
                EmailVerificationRequest(
                    business_id=candidate_id,
                    email_candidate_id=discovered_fact,
                    source_evidence_ref=discovered_fact,
                    business_match_ref=discovered_fact,
                    address=SecretStr("synthetic@example.test"),
                ),
                capability=Capability.HUNTER_EMAIL_VERIFICATION,
            )
        },
    ).execute(
        verify_attr,
        SafeRequestMetadata(config_ref=verify_config.id),
        idempotency_key=uuid4(),
    )
    assert verification.content is not None
    assert (
        observe_verification_status(verification.content, verify_grant, (), now=NOW)
        is VerificationStatus.INVALID
    )
    forged_valid = await fact(
        "VERIFIED",
        contact_ref=discovered_fact,
        policy_ref=await supply.verification_policy(exp),
    )
    with pytest.raises(ContactPolicyDenied, match="ATTEMPT_FACT"):
        await contact.record_attempt(verification, uuid4(), output_fact_id=forged_valid)
    rejected = await fact(
        "VERIFICATION_REJECTED",
        contact_ref=discovered_fact,
        policy_ref=await supply.verification_policy(exp),
    )
    await contact.record_attempt(verification, uuid4(), output_fact_id=rejected)
    if revoke_selected_before_resolve:
        admin = GovernanceProvisioner(governance_engine)
        revoked = GrantEvent(
            event_id=uuid4(),
            grant_id=hunter_grant.grant_id,
            grant_version=hunter_grant.version,
            kind=GrantEventKind.REVOKED,
            effective_at=NOW,
            actor_id=uuid4(),
            evidence_ref=uuid4(),
        )
        await register(admin, revoked.evidence_ref, "GRANT_EVENT", NOW)
        await admin.grant_event(revoked)
        with pytest.raises(ContactPolicyDenied, match="SOURCE_RIGHTS"):
            await contact.resolve(candidate_id)
        from sqlalchemy import select

        from alon_ai.db.tables import supply as contact_supply_schema

        async with governance_engine.connect() as connection:
            assert (
                await connection.execute(
                    select(contact_supply_schema.contacts).where(
                        contact_supply_schema.contacts.c.candidate_id == candidate_id
                    )
                )
            ).one_or_none() is None
        return
    assert await contact.resolve(candidate_id) == "EMAIL_NOT_FOUND"
    snapshot = await supply.snapshot(exp)
    assert snapshot.supported_emails == 0
    assert [x.capability for x in verify_session.invocations] == [
        Capability.HUNTER_EMAIL_VERIFICATION
    ]

    async with governance_engine.begin() as connection:
        await ContactAdmissionHook(contact).admit(
            connection,
            verify_attr,
            verification.receipt.call_id,
            "DISPATCH",
        )
    async with governance_engine.begin() as connection:
        await ContactAdmissionHook(contact).admit(
            connection,
            verify_attr.model_copy(update={"deadline": NOW + timedelta(minutes=7)}),
            verification.receipt.call_id,
            "DISPATCH",
        )
    with pytest.raises(AccountingDenied) as selected_expiry_denied:
        async with governance_engine.begin() as connection:
            await ContactAdmissionHook(contact).admit(
                connection,
                verify_attr.model_copy(
                    update={"deadline": NOW + timedelta(minutes=15)}
                ),
                verification.receipt.call_id,
                "DISPATCH",
            )
    assert selected_expiry_denied.value.reason is Reason.GATE
    admin = GovernanceProvisioner(governance_engine)
    revoked = GrantEvent(
        event_id=uuid4(),
        grant_id=hunter_grant.grant_id,
        grant_version=hunter_grant.version,
        kind=GrantEventKind.REVOKED,
        effective_at=NOW,
        actor_id=uuid4(),
        evidence_ref=uuid4(),
    )
    await register(admin, revoked.evidence_ref, "GRANT_EVENT", NOW)
    await admin.grant_event(revoked)
    with pytest.raises(AccountingDenied) as denied:
        async with governance_engine.begin() as connection:
            await ContactAdmissionHook(contact).admit(
                connection,
                verify_attr,
                verification.receipt.call_id,
                "DISPATCH",
            )
    assert denied.value.reason is Reason.RIGHTS


async def test_not_available_pauses_and_never_becomes_hunter_absence(
    governance_engine,
):
    from alon_ai.db.repositories.accounting import GovernanceRepository
    from alon_ai.db.repositories.contact import (
        ContactAdmissionHook,
        ContactPolicyRepository,
    )
    from alon_ai.db.repositories.supply import ComposedContactSupplyHook
    from alon_ai.integrations.contact import ConfiguredContactAdapter
    from alon_ai.policies.contact import ContactPolicyDenied
    from alon_ai.provider_usage.schemas.accounting import AccountingDenied, Reason
    from alon_ai.provider_usage.service import GovernedExecutor

    supply, writer, exp, plan = await setup(governance_engine)
    batch = await supply.begin_batch(exp, 1, plan, uuid4())
    candidate_id, fact = await candidate(supply, writer, exp, batch)
    contact = ContactPolicyRepository(governance_engine, supply, clock=lambda: NOW)
    hook = ComposedContactSupplyHook(
        supply, contact_owner=ContactAdmissionHook(contact)
    )
    governed = GovernanceRepository(
        governance_engine, clock=lambda: NOW, admission_hooks={"CONTACT": hook}
    )
    workflow = uuid4()
    brave_attr, brave_config, brave_grant, brave_use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=Capability.BRAVE_LOCAL_DISCOVERY,
        component=UsageComponent.REQUEST,
    )
    brave_session = FakeSession(
        grants={Capability.BRAVE_LOCAL_DISCOVERY: brave_grant},
        intended_uses={Capability.BRAVE_LOCAL_DISCOVERY: brave_use},
        clock=lambda: NOW,
        scenario=FixtureScenario.ERROR,
    )
    brave = await GovernedExecutor(
        governed,
        adapters={
            brave_config.adapter_version: ConfiguredContactAdapter(
                FakeBraveProvider(brave_session),
                BraveSearchRequest(
                    capability=Capability.BRAVE_LOCAL_DISCOVERY,
                    query=SecretStr("synthetic query"),
                    limit=1,
                ),
                capability=Capability.BRAVE_LOCAL_DISCOVERY,
            )
        },
    ).execute(
        brave_attr,
        SafeRequestMetadata(config_ref=brave_config.id),
        idempotency_key=uuid4(),
    )
    failure_fact = await fact("SOURCE_FAILURE")
    paused = await contact.record_source(
        candidate_id,
        failure_fact,
        brave,
        uuid4(),
    )
    assert paused.decision == "PAUSED"
    with pytest.raises(ContactPolicyDenied, match="PAUSED"):
        await contact.resolve(candidate_id)

    capability = Capability.HUNTER_EMAIL_FINDER
    attr, config, grant, use = await provision(
        governance_engine,
        supply,
        contact,
        experiment_id=exp,
        workflow_id=workflow,
        batch_id=batch,
        candidate_id=candidate_id,
        capability=capability,
        component=UsageComponent.DISCOVERY,
        source_case_id=candidate_id,
    )
    session = FakeSession(
        grants={capability: grant}, intended_uses={capability: use}, clock=lambda: NOW
    )
    adapter = ConfiguredContactAdapter(
        FakeContactDiscoveryProvider(session),
        ContactDiscoveryRequest(
            business_id=candidate_id,
            brave_observation=EmailSourceObservation(
                business_id=candidate_id,
                provider_call_id=brave.receipt.call_id,
                capability=Capability.BRAVE_LOCAL_DISCOVERY,
                grant_id=brave_grant.grant_id,
                grant_version=1,
                evidence_ref=None,
                observed_at=NOW,
                presence=EmailPresence.NOT_AVAILABLE,
            ),
            domain=SecretStr("example.test"),
        ),
        capability=capability,
    )
    with pytest.raises(AccountingDenied) as denied:
        await GovernedExecutor(
            governed, adapters={config.adapter_version: adapter}
        ).execute(
            attr,
            SafeRequestMetadata(config_ref=config.id),
            idempotency_key=uuid4(),
        )
    assert denied.value.reason is Reason.GATE
    assert session.invocations == ()
