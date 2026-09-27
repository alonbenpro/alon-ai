"""L03 slice 1: immutable product roots and idea/research lineage."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import SQLAlchemyError

from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.db.repositories.records_operators import OperatorRepository
from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables import records
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    OperatorCapabilityProfile,
    ProductAgent,
    ProductExperiment,
    ProductRecordsDenied,
    ProductWorkflow,
    SourceReference,
)
from alon_ai.services.schemas.records_operator import (
    CommercialConstraints,
    DeliveryConstraints,
    OperatorIdentity,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 12, 12, tzinfo=UTC)


def artifact(
    experiment_id,
    kind,
    payload,
    *,
    logical_id=None,
    version=1,
    workflow_id=None,
    agent_id=None,
    operation_id=None,
):
    return ArtifactDraft(
        id=uuid4(),
        logical_id=logical_id or uuid4(),
        version=version,
        experiment_id=experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        operation_id=operation_id,
        kind=kind,
        payload=payload,
        created_by=UUID(int=1),
        created_at=NOW,
    )


async def register_test_operator(engine):
    await OperatorRepository(engine, clock=lambda: NOW).register_operator(
        OperatorIdentity(
            id=UUID(int=1),
            auth_subject="synthetic:operator",
            display_name="Synthetic operator",
        ),
        command_key=UUID(int=10001),
    )


async def accept_feedback(repo, experiment_id, feedback):
    validation = await repo.append_artifact(
        artifact(
            experiment_id,
            ArtifactKind.VALIDATION_RESULT,
            {
                "validator": "synthetic-return-validator",
                "disposition": "PASS",
                "reason": "Exact evidence justifies return",
            },
        ),
        inputs=(ArtifactInput.from_receipt(feedback, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(feedback, role="TARGET"),
        experiment_id=experiment_id,
        disposition="ACCEPTED",
        validation=ArtifactInput.from_receipt(validation, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )


async def roots(engine, *, suffix="root"):
    experiment_id, workflow_id, agent_id = uuid4(), uuid4(), uuid4()
    profile = OperatorCapabilityProfile(
        id=UUID(int=2),
        version=1,
        operator_id=UUID(int=1),
        capabilities=("Python backend development",),
        constraints=("Synthetic work only",),
        delivery=DeliveryConstraints(
            max_project_hours=Decimal(80),
            hours_per_week=Decimal(20),
            concurrent_projects=1,
        ),
        commercial=CommercialConstraints(
            currency="ILS",
            hourly_cost=Decimal(100),
            minimum_project_price=Decimal(5000),
            minimum_margin_rate=Decimal("0.4"),
            maximum_discount_rate=Decimal("0.1"),
            minimum_deposit_rate=Decimal("0.5"),
        ),
        approved_by=UUID(int=1),
        created_at=NOW,
    )
    async with engine.begin() as connection:
        await connection.execute(insert(gov.experiments).values(id=experiment_id))
        await connection.execute(
            insert(gov.workflows).values(id=workflow_id, experiment_id=experiment_id)
        )
        await connection.execute(
            insert(gov.agents).values(id=agent_id, workflow_id=workflow_id)
        )
    repo = ProductRecordsRepository(engine, clock=lambda: NOW)
    await register_test_operator(engine)
    await repo.register_profile(profile, command_key=UUID(int=10002))
    await repo.bind_roots(
        ProductExperiment(
            id=experiment_id,
            operator_profile_id=profile.id,
            operator_profile_version=1,
            name=f"synthetic-{suffix}",
            created_at=NOW,
        ),
        ProductWorkflow(
            id=workflow_id,
            experiment_id=experiment_id,
            role="IDEA_TO_RESEARCH",
            created_at=NOW,
        ),
        ProductAgent(
            id=agent_id,
            workflow_id=workflow_id,
            role="MARKET_RESEARCH",
            created_at=NOW,
        ),
        command_key=uuid4(),
    )
    return repo, profile, experiment_id, workflow_id, agent_id


async def test_roots_extend_governance_and_commands_replay_without_duplication(
    governance_engine,
):
    repo, profile, experiment_id, workflow_id, agent_id = await roots(governance_engine)
    command_key = uuid4()
    draft = artifact(
        experiment_id,
        ArtifactKind.EXPERIMENT_BRIEF,
        {"objective": "Prove a synthetic service hypothesis."},
        workflow_id=workflow_id,
        agent_id=agent_id,
    )

    first = await repo.append_artifact(draft, command_key=command_key)
    replay = await repo.append_artifact(draft, command_key=command_key)

    assert replay == first
    async with governance_engine.connect() as connection:
        stored = (
            (
                await connection.execute(
                    select(records.artifacts).where(records.artifacts.c.id == draft.id)
                )
            )
            .mappings()
            .one()
        )
        assert len(stored["content_hash"]) == 64
        assert stored["payload"] == draft.payload
        assert (
            await connection.scalar(
                select(records.commands.c.id).where(
                    records.commands.c.command_key == command_key
                )
            )
        ) is not None
        assert (
            await connection.scalar(
                select(records.outbox.c.aggregate_id).where(
                    records.outbox.c.command_id == first.command_id
                )
            )
        ) == draft.id
        assert (
            await connection.scalar(
                select(records.operator_profiles.c.operator_id).where(
                    records.operator_profiles.c.id == profile.id
                )
            )
        ) == UUID(int=1)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE record_artifacts SET payload='{}'::jsonb WHERE id=:id",
        "DELETE FROM record_artifacts WHERE id=:id",
    ],
)
async def test_artifact_history_rejects_raw_mutation(governance_engine, statement):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    seed = artifact(
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Synthetic seed."},
    )
    await repo.append_artifact(seed, command_key=uuid4())

    with pytest.raises(Exception, match="immutable product record"):
        async with governance_engine.begin() as connection:
            await connection.execute(text(statement), {"id": seed.id})


async def test_strict_payload_and_exact_cross_artifact_lineage_are_database_gates(
    governance_engine,
):
    repo, _, experiment_id, _, _ = await roots(governance_engine, suffix="one")
    _, _, other_experiment, _, _ = await roots(governance_engine, suffix="two")
    seed = artifact(
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Synthetic seed."},
    )
    receipt = await repo.append_artifact(seed, command_key=uuid4())
    plan = artifact(
        other_experiment,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["Is the pain expensive?"], "method": "Synthetic review."},
    )

    with pytest.raises(ProductRecordsDenied):
        await repo.append_artifact(
            plan,
            inputs=(
                ArtifactInput(
                    artifact_id=seed.id,
                    kind=seed.kind,
                    version=seed.version,
                    content_hash=receipt.content_hash,
                    role="INPUT",
                ),
            ),
            command_key=uuid4(),
        )

    with pytest.raises(SQLAlchemyError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.artifacts).values(
                    id=uuid4(),
                    logical_id=uuid4(),
                    version=1,
                    experiment_id=experiment_id,
                    kind="IDEA_SEED",
                    schema_version=1,
                    payload={"origin": "USER_SUPPLIED", "statement": 3},
                    created_by=UUID(int=1),
                    created_at=NOW,
                )
            )

    raw_id = uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(records.artifacts).values(
                id=raw_id,
                logical_id=uuid4(),
                version=1,
                experiment_id=experiment_id,
                kind="SERVICE_PROFILE",
                schema_version=1,
                payload={"name": "Synthetic service", "scope": "Synthetic scope."},
                content_hash="0" * 64,
                created_by=UUID(int=1),
                created_at=NOW,
            )
        )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.artifacts.c.content_hash).where(
                    records.artifacts.c.id == raw_id
                )
            )
            != "0" * 64
        )


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (
            ArtifactKind.COMPETITOR_PROFILE,
            {"name": "Synthetic competitor", "positioning": "Synthetic position."},
        ),
        (
            ArtifactKind.PRICE_OBSERVATION,
            {
                "status": "REQUIRED_UNAVAILABLE",
                "currency": None,
                "amount": None,
                "unit": "synthetic unit",
                "source_note": "A quote was required but unavailable.",
            },
        ),
        (
            ArtifactKind.ACCEPTANCE_RECEIPT,
            {"disposition": "REJECTED", "reason": "Synthetic rejection."},
        ),
    ],
)
async def test_remaining_typed_artifact_shapes_persist(
    governance_engine, kind, payload
):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    receipt = await repo.append_artifact(
        artifact(experiment_id, kind, payload), command_key=uuid4()
    )
    assert receipt.kind is kind


async def test_source_reference_is_exact_but_does_not_block_retention_purge(
    governance_engine,
):
    from test_governance import reserve, seed

    from alon_ai.db.repositories.accounting import GovernanceRepository
    from alon_ai.integrations.schemas.provider import ContentField
    from alon_ai.policies.provider_rights import RuntimeContent

    governance, _, attr, config, grant, now = await seed(governance_engine)
    call = await reserve(governance, attr, config)
    await governance.dispatch(call.call_id)
    retained_ids = await governance.retain_content(
        call.call_id,
        RuntimeContent(
            {ContentField.TEXT: ("licensed synthetic",)},
            grant=grant,
            intended_use=config.intended_use,
            observed_at=now,
        ),
    )
    async with governance_engine.connect() as connection:
        retained = (
            (
                await connection.execute(
                    select(gov.retained).where(gov.retained.c.id == retained_ids[0])
                )
            )
            .mappings()
            .one()
        )
    agent_id = uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(gov.agents).values(id=agent_id, workflow_id=attr.workflow_run_id)
        )
    product = ProductRecordsRepository(governance_engine, clock=lambda: now)
    profile = OperatorCapabilityProfile(
        id=UUID(int=2),
        version=1,
        operator_id=UUID(int=1),
        capabilities=("Python backend development",),
        constraints=("Synthetic work only",),
        delivery=DeliveryConstraints(
            max_project_hours=Decimal(80),
            hours_per_week=Decimal(20),
            concurrent_projects=1,
        ),
        commercial=CommercialConstraints(
            currency="ILS",
            hourly_cost=Decimal(100),
            minimum_project_price=Decimal(5000),
            minimum_margin_rate=Decimal("0.4"),
            maximum_discount_rate=Decimal("0.1"),
            minimum_deposit_rate=Decimal("0.5"),
        ),
        approved_by=UUID(int=1),
        created_at=now,
    )
    await register_test_operator(governance_engine)
    await product.register_profile(profile, command_key=UUID(int=10002))
    await product.bind_roots(
        ProductExperiment(
            id=attr.experiment_id,
            operator_profile_id=profile.id,
            operator_profile_version=1,
            name="synthetic-retention",
            created_at=now,
        ),
        ProductWorkflow(
            id=attr.workflow_run_id,
            experiment_id=attr.experiment_id,
            role="IDEA_TO_RESEARCH",
            created_at=now,
        ),
        ProductAgent(
            id=agent_id,
            workflow_id=attr.workflow_run_id,
            role="MARKET_RESEARCH",
            created_at=now,
        ),
        command_key=uuid4(),
    )
    evidence = artifact(
        attr.experiment_id,
        ArtifactKind.RESEARCH_EVIDENCE,
        {"claim": "Synthetic public claim.", "finding": "Synthetic finding."},
    )
    await product.append_artifact(
        evidence,
        sources=(
            SourceReference.retained_content(
                retained_id=retained["id"],
                call_id=retained["call_id"],
                grant_id=retained["grant_id"],
                grant_version=retained["grant_version"],
                field=retained["field"],
                expires_at=retained["expires_at"],
            ),
        ),
        command_key=uuid4(),
    )
    async with governance_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(records.source_refs).where(
                        records.source_refs.c.artifact_id == evidence.id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert row["retained_id"] == retained["id"]
        assert "licensed synthetic" not in str(row)
    expired = GovernanceRepository(
        governance_engine, clock=lambda: now + timedelta(seconds=61)
    )
    assert await expired.purge_expired() == 1
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(records.source_refs.c.retained_id).where(
                    records.source_refs.c.artifact_id == evidence.id
                )
            )
            == retained["id"]
        )


async def test_cycle_acceptance_verdict_return_and_material_pivot_gates(
    governance_engine,
):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    seed = artifact(
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Synthetic seed."},
    )
    seed_receipt = await repo.append_artifact(seed, command_key=uuid4())
    cycle = await repo.create_cycle(
        experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    idea = artifact(
        experiment_id,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Synthetic offer",
            "customer": "Synthetic operators",
            "problem": "Manual reconciliation",
            "core_intent": "reduce-reconciliation-work",
            "material_pivot": False,
        },
    )
    idea_receipt = await repo.append_artifact(idea, command_key=uuid4())
    accepted = await repo.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(idea_receipt, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    assert (await repo.current_idea(cycle.id)).artifact_id == idea.id

    with pytest.raises(ProductRecordsDenied):
        await repo.accept_idea(
            cycle.id,
            ArtifactInput.from_receipt(idea_receipt, role="ACCEPTED_IDEA"),
            accepted_by=UUID(int=1),
            command_key=uuid4(),
        )

    plan = artifact(
        experiment_id,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["Is the pain expensive?"], "method": "Synthetic review."},
    )
    plan_receipt = await repo.append_artifact(
        plan,
        inputs=(ArtifactInput.from_receipt(idea_receipt, role="ACCEPTED_IDEA"),),
        command_key=uuid4(),
    )
    attempt = await repo.start_market_research(
        experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea_receipt, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan_receipt, role="PLAN"),
        command_key=uuid4(),
    )
    report = artifact(
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "Evidence is incomplete.", "limitations": ["Synthetic only."]},
    )
    recommendation = artifact(
        experiment_id,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {
            "recommendation": "MATERIAL_PIVOT_RECOMMENDED",
            "rationale": "Need a narrower buyer.",
        },
    )
    report_receipt = await repo.append_artifact(
        report,
        inputs=(ArtifactInput.from_receipt(plan_receipt, role="PLAN"),),
        command_key=uuid4(),
    )
    recommendation_receipt = await repo.append_artifact(
        recommendation,
        inputs=(ArtifactInput.from_receipt(report_receipt, role="REPORT"),),
        command_key=uuid4(),
    )
    verdict = await repo.commit_verdict(
        attempt.id,
        report=ArtifactInput.from_receipt(report_receipt, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation_receipt, role="RECOMMENDATION"
        ),
        verdict="MATERIAL_PIVOT_RECOMMENDED",
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.commit_verdict(
            attempt.id,
            report=ArtifactInput.from_receipt(report_receipt, role="REPORT"),
            recommendation=ArtifactInput.from_receipt(
                recommendation_receipt, role="RECOMMENDATION"
            ),
            verdict="MATERIAL_PIVOT_RECOMMENDED",
            committed_by=UUID(int=1),
            command_key=uuid4(),
        )

    feedback = artifact(
        experiment_id,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        {"preserve": ["Core pain"], "change": ["Narrow buyer"]},
    )
    feedback_receipt = await repo.append_artifact(
        feedback,
        inputs=(
            ArtifactInput.from_receipt(idea_receipt, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report_receipt, role="REPORT"),
            ArtifactInput.from_receipt(recommendation_receipt, role="RECOMMENDATION"),
        ),
        command_key=uuid4(),
    )
    await accept_feedback(repo, experiment_id, feedback_receipt)
    next_cycle = await repo.return_to_refinement(
        verdict.id,
        feedback=ArtifactInput.from_receipt(feedback_receipt, role="FEEDBACK"),
        command_key=uuid4(),
    )
    pivot = artifact(
        experiment_id,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Different synthetic offer",
            "customer": "Synthetic shops",
            "problem": "Inventory",
            "core_intent": "replace-inventory-system",
            "material_pivot": True,
        },
    )
    pivot_receipt = await repo.append_artifact(pivot, command_key=uuid4())
    with pytest.raises(ProductRecordsDenied):
        await repo.accept_idea(
            next_cycle.id,
            ArtifactInput.from_receipt(pivot_receipt, role="ACCEPTED_IDEA"),
            accepted_by=UUID(int=1),
            command_key=uuid4(),
        )
    decision = await repo.approve_material_pivot(
        next_cycle.id,
        ArtifactInput.from_receipt(pivot_receipt, role="PIVOT_TARGET"),
        approved_by=UUID(int=1),
        command_key=uuid4(),
    )
    await repo.accept_idea(
        next_cycle.id,
        ArtifactInput.from_receipt(pivot_receipt, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        pivot_approval_id=decision.id,
        command_key=uuid4(),
    )

    reloaded = ProductRecordsRepository(governance_engine, clock=lambda: NOW)
    assert (await reloaded.current_idea(next_cycle.id)).artifact_id == pivot.id
    assert accepted.artifact_id == idea.id


async def test_acceptance_closes_the_exact_artifact_lineage_set(governance_engine):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    seed = artifact(
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Synthetic seed."},
    )
    seed_receipt = await repo.append_artifact(seed, command_key=uuid4())
    candidate = artifact(
        experiment_id,
        ArtifactKind.IDEA_CANDIDATE,
        {"title": "Synthetic candidate", "hypothesis": "Synthetic hypothesis."},
    )
    candidate_receipt = await repo.append_artifact(
        candidate,
        inputs=(ArtifactInput.from_receipt(seed_receipt, role="INPUT"),),
        command_key=uuid4(),
    )
    validation = artifact(
        experiment_id,
        ArtifactKind.VALIDATION_RESULT,
        {
            "validator": "synthetic-validator",
            "disposition": "PASS",
            "reason": "Fixture passes.",
        },
    )
    validation_receipt = await repo.append_artifact(
        validation,
        inputs=(ArtifactInput.from_receipt(candidate_receipt, role="TARGET"),),
        command_key=uuid4(),
    )
    await repo.record_disposition(
        ArtifactInput.from_receipt(candidate_receipt, role="TARGET"),
        experiment_id=experiment_id,
        disposition="ACCEPTED",
        validation=ArtifactInput.from_receipt(validation_receipt, role="VALIDATION"),
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )
    with pytest.raises(SQLAlchemyError, match="accepted artifact lineage is closed"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.artifact_links).values(
                    consumer_id=candidate.id,
                    producer_id=validation.id,
                    experiment_id=experiment_id,
                    role="LATE_INPUT",
                    producer_kind=validation.kind,
                    producer_version=validation.version,
                    producer_hash=validation_receipt.content_hash,
                )
            )


async def test_version_two_requires_exact_relational_predecessor(governance_engine):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    logical_id = uuid4()
    first = artifact(
        experiment_id,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["What is known?"], "method": "Synthetic review."},
        logical_id=logical_id,
    )
    first_receipt = await repo.append_artifact(first, command_key=uuid4())
    second = artifact(
        experiment_id,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["What changed?"], "method": "Synthetic rerun."},
        logical_id=logical_id,
        version=2,
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.append_artifact(second, command_key=uuid4())
    receipt = await repo.append_artifact(
        second,
        inputs=(ArtifactInput.from_receipt(first_receipt, role="SUPERSEDES"),),
        command_key=uuid4(),
    )
    assert receipt.version == 2


async def test_concurrent_idea_ownership_has_one_winner(governance_engine):
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    seed = artifact(
        experiment_id,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Synthetic seed."},
    )
    seed_receipt = await repo.append_artifact(seed, command_key=uuid4())
    cycle = await repo.create_cycle(
        experiment_id,
        seed=ArtifactInput.from_receipt(seed_receipt, role="SEED"),
        command_key=uuid4(),
    )
    ideas = [
        artifact(
            experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                "title": f"Synthetic idea {index}",
                "customer": "Synthetic operators",
                "problem": "Manual reconciliation",
                "core_intent": "reduce-reconciliation-work",
                "material_pivot": False,
            },
        )
        for index in range(2)
    ]
    receipts = [await repo.append_artifact(item, command_key=uuid4()) for item in ideas]
    results = await asyncio.gather(
        *(
            repo.accept_idea(
                cycle.id,
                ArtifactInput.from_receipt(item, role="ACCEPTED_IDEA"),
                accepted_by=UUID(int=1),
                command_key=uuid4(),
            )
            for item in receipts
        ),
        return_exceptions=True,
    )
    assert len([item for item in results if not isinstance(item, BaseException)]) == 1
    assert (
        len([item for item in results if isinstance(item, ProductRecordsDenied)]) == 1
    )
