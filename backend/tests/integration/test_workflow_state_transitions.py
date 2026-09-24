"""Focused PostgreSQL contract for the first L04 workflow transition."""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select, text, update
from test_product_record_guards import cycle_fixture
from test_product_records import NOW, artifact
from test_research_origins import research_verdict, return_feedback

from alon_ai.records import ArtifactInput, ArtifactKind, ProductRecordsDenied
from alon_ai.records import schema as records

pytestmark = pytest.mark.integration


async def test_start_market_research_commits_transition_and_attempt_atomically(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)

    receipt = await repo.start_market_research(
        experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )

    assert receipt.cycle_id == cycle.id
    assert receipt.ordinal == 1
    assert receipt.state == "MARKET_RESEARCH"
    async with governance_engine.connect() as connection:
        projection = (
            (
                await connection.execute(
                    select(records.cycle_states).where(
                        records.cycle_states.c.cycle_id == cycle.id
                    )
                )
            )
            .mappings()
            .one()
        )
        transition = (
            (
                await connection.execute(
                    select(records.cycle_transitions).where(
                        records.cycle_transitions.c.id == receipt.transition_id
                    )
                )
            )
            .mappings()
            .one()
        )
        acceptance_id = await connection.scalar(
            select(records.idea_acceptances.c.id).where(
                records.idea_acceptances.c.cycle_id == cycle.id
            )
        )
        command = (
            (
                await connection.execute(
                    select(records.commands).where(
                        records.commands.c.id == receipt.command_id
                    )
                )
            )
            .mappings()
            .one()
        )

        assert projection["state"] == "MARKET_RESEARCH"
        assert projection["transition_ordinal"] == 1
        assert projection["last_transition_id"] == receipt.transition_id
        assert transition["from_state"] == "IDEA_REFINEMENT"
        assert transition["to_state"] == "MARKET_RESEARCH"
        assert transition["idea_acceptance_id"] == acceptance_id
        assert transition["idea_artifact_id"] == idea.artifact_id
        assert transition["research_attempt_id"] == receipt.id
        assert transition["command_id"] == receipt.command_id
        assert command["kind"] == "START_MARKET_RESEARCH"
        assert command["result_id"] == receipt.id
        assert (
            await connection.scalar(
                select(records.audit.c.command_id).where(
                    records.audit.c.command_id == receipt.command_id
                )
            )
        ) == receipt.command_id
        assert (
            await connection.scalar(
                select(records.outbox.c.topic).where(
                    records.outbox.c.command_id == receipt.command_id
                )
            )
        ) == "product-record.start-market-research"
        rebuilt_state = await connection.scalar(
            select(records.cycle_transitions.c.to_state)
            .where(records.cycle_transitions.c.cycle_id == cycle.id)
            .order_by(records.cycle_transitions.c.ordinal.desc())
            .limit(1)
        )
        assert rebuilt_state == projection["state"]


async def test_start_market_research_rejects_missing_accepted_idea(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(
        governance_engine, accept=False
    )

    with pytest.raises(ProductRecordsDenied, match="MISSING_ACCEPTED_IDEA"):
        await repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            plan=ArtifactInput.from_receipt(plan, role="PLAN"),
            command_key=uuid4(),
        )

    async with governance_engine.connect() as connection:
        assert not (
            await connection.execute(
                select(records.research_attempts).where(
                    records.research_attempts.c.cycle_id == cycle.id
                )
            )
        ).all()
        state = await connection.scalar(
            select(records.cycle_states.c.state).where(
                records.cycle_states.c.cycle_id == cycle.id
            )
        )
        assert state == "IDEA_REFINEMENT"


async def test_start_market_research_rejects_stale_idea_version(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(
        governance_engine, accept=False
    )
    async with governance_engine.connect() as connection:
        logical_id = await connection.scalar(
            select(records.artifacts.c.logical_id).where(
                records.artifacts.c.id == idea.artifact_id
            )
        )
    replacement = await repo.append_artifact(
        artifact(
            experiment_id,
            ArtifactKind.IDEA_BRIEF,
            {
                "title": "Service v2",
                "customer": "Operators",
                "problem": "Manual work",
                "core_intent": "reduce-manual-work",
                "material_pivot": False,
            },
            logical_id=logical_id,
            version=2,
        ),
        inputs=(ArtifactInput.from_receipt(idea, role="SUPERSEDES"),),
        command_key=uuid4(),
    )
    assert replacement.version == 2
    await repo.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )

    with pytest.raises(ProductRecordsDenied, match="STALE_IDEA_LINEAGE"):
        await repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            plan=ArtifactInput.from_receipt(plan, role="PLAN"),
            command_key=uuid4(),
        )


async def test_start_market_research_rejects_superseded_or_mismatched_lineage(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    idea_ref = ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA")
    await repo.record_disposition(
        idea_ref,
        experiment_id=experiment_id,
        disposition="SUPERSEDED",
        decided_by=UUID(int=1),
        command_key=uuid4(),
    )

    for supplied in (
        idea_ref,
        idea_ref.model_copy(update={"content_hash": "0" * 64}),
    ):
        with pytest.raises(ProductRecordsDenied, match="STALE_IDEA_LINEAGE"):
            await repo.start_market_research(
                experiment_id,
                cycle.id,
                accepted_idea=supplied,
                plan=ArtifactInput.from_receipt(plan, role="PLAN"),
                command_key=uuid4(),
            )


async def test_start_market_research_replays_and_rejects_changed_request(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    key = uuid4()
    idea_ref = ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA")
    plan_ref = ArtifactInput.from_receipt(plan, role="PLAN")
    arguments = {
        "experiment_id": experiment_id,
        "cycle_id": cycle.id,
        "accepted_idea": idea_ref,
        "plan": plan_ref,
        "command_key": key,
    }

    original = await repo.start_market_research(**arguments)
    assert await repo.start_market_research(**arguments) == original
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=idea_ref,
            plan=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            command_key=key,
        )

    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycle_transitions)
                .where(records.cycle_transitions.c.cycle_id == cycle.id)
            )
        ) == 1
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.outbox)
                .where(records.outbox.c.command_id == original.command_id)
            )
        ) == 1


async def test_concurrent_start_market_research_advances_once(governance_engine):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    idea_ref = ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA")
    plan_ref = ArtifactInput.from_receipt(plan, role="PLAN")

    results = await asyncio.gather(
        repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=idea_ref,
            plan=plan_ref,
            command_key=uuid4(),
        ),
        repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=idea_ref,
            plan=plan_ref,
            command_key=uuid4(),
        ),
        return_exceptions=True,
    )

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, ProductRecordsDenied) for result in results) == 1
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.research_attempts)
                .where(records.research_attempts.c.cycle_id == cycle.id)
            )
        ) == 1
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycle_transitions)
                .where(records.cycle_transitions.c.cycle_id == cycle.id)
            )
        ) == 1


async def test_start_market_research_rolls_back_every_record_on_failure(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    async with governance_engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE FUNCTION fail_start_market_research_projection() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                  IF NEW.state='MARKET_RESEARCH' THEN
                    RAISE EXCEPTION 'synthetic projection failure';
                  END IF;
                  RETURN NEW;
                END $$;
                CREATE TRIGGER fail_start_market_research_projection
                BEFORE UPDATE ON record_cycle_states FOR EACH ROW
                EXECUTE FUNCTION fail_start_market_research_projection();
                """
            )
        )
    try:
        with pytest.raises(ProductRecordsDenied):
            await repo.start_market_research(
                experiment_id,
                cycle.id,
                accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
                plan=ArtifactInput.from_receipt(plan, role="PLAN"),
                command_key=uuid4(),
            )
    finally:
        async with governance_engine.begin() as connection:
            await connection.execute(
                text(
                    "DROP TRIGGER fail_start_market_research_projection "
                    "ON record_cycle_states; "
                    "DROP FUNCTION fail_start_market_research_projection()"
                )
            )

    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.research_attempts)
                .where(records.research_attempts.c.cycle_id == cycle.id)
            )
        ) == 0
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.cycle_transitions)
                .where(records.cycle_transitions.c.cycle_id == cycle.id)
            )
        ) == 0
        projection = (
            (
                await connection.execute(
                    select(records.cycle_states).where(
                        records.cycle_states.c.cycle_id == cycle.id
                    )
                )
            )
            .mappings()
            .one()
        )
        assert projection["state"] == "IDEA_REFINEMENT"
        assert projection["transition_ordinal"] == 0
        assert not (
            await connection.execute(
                select(records.commands).where(
                    records.commands.c.kind == "START_MARKET_RESEARCH"
                )
            )
        ).all()
        assert not (
            await connection.execute(
                select(records.audit).where(
                    records.audit.c.kind == "START_MARKET_RESEARCH"
                )
            )
        ).all()
        assert not (
            await connection.execute(
                select(records.outbox).where(
                    records.outbox.c.topic == "product-record.start-market-research"
                )
            )
        ).all()


async def test_cycle_state_and_transition_history_reject_inconsistent_mutation(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    receipt = await repo.start_market_research(
        experiment_id,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )

    with pytest.raises(Exception, match="immutable cycle transition"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                update(records.cycle_transitions)
                .where(records.cycle_transitions.c.id == receipt.transition_id)
                .values(to_state="IDEA_REFINEMENT")
            )
    with pytest.raises(Exception, match="cycle state must follow transition history"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                update(records.cycle_states)
                .where(records.cycle_states.c.cycle_id == cycle.id)
                .values(updated_at=NOW)
            )


async def test_raw_transition_without_audit_and_outbox_cannot_commit(
    governance_engine,
):
    _, experiment_id, _, cycle, idea, plan = await cycle_fixture(governance_engine)
    attempt_id, command_id, transition_id = uuid4(), uuid4(), uuid4()
    async with governance_engine.connect() as connection:
        acceptance = (
            (
                await connection.execute(
                    select(records.idea_acceptances).where(
                        records.idea_acceptances.c.cycle_id == cycle.id
                    )
                )
            )
            .mappings()
            .one()
        )

    with pytest.raises(Exception, match="missing command audit or outbox"):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.research_attempts).values(
                    id=attempt_id,
                    experiment_id=experiment_id,
                    cycle_id=cycle.id,
                    ordinal=1,
                    plan_artifact_id=plan.artifact_id,
                    plan_kind=plan.kind,
                    plan_version=plan.version,
                    plan_hash=plan.content_hash,
                    created_at=NOW,
                )
            )
            await connection.execute(
                insert(records.commands).values(
                    id=command_id,
                    command_key=uuid4(),
                    request_hash="0" * 64,
                    experiment_id=experiment_id,
                    kind="START_MARKET_RESEARCH",
                    result_type="RESEARCH_ATTEMPT",
                    result_id=attempt_id,
                    issued_at=NOW,
                )
            )
            await connection.execute(
                insert(records.cycle_transitions).values(
                    id=transition_id,
                    experiment_id=experiment_id,
                    cycle_id=cycle.id,
                    ordinal=1,
                    from_state="IDEA_REFINEMENT",
                    to_state="MARKET_RESEARCH",
                    idea_acceptance_id=acceptance["id"],
                    idea_artifact_id=idea.artifact_id,
                    idea_kind=idea.kind,
                    idea_version=idea.version,
                    idea_hash=idea.content_hash,
                    research_attempt_id=attempt_id,
                    command_id=command_id,
                    created_at=NOW,
                )
            )
            await connection.execute(
                update(records.cycle_states)
                .where(records.cycle_states.c.cycle_id == cycle.id)
                .values(
                    state="MARKET_RESEARCH",
                    transition_ordinal=1,
                    last_transition_id=transition_id,
                    updated_at=NOW,
                )
            )

    async with governance_engine.connect() as connection:
        assert not await connection.scalar(
            select(records.commands.c.id).where(records.commands.c.id == command_id)
        )
        assert not await connection.scalar(
            select(records.research_attempts.c.id).where(
                records.research_attempts.c.id == attempt_id
            )
        )


async def test_start_market_research_rejects_non_current_cycle(
    governance_engine,
):
    repo, experiment_id, _, cycle, idea, unused_plan = await cycle_fixture(
        governance_engine
    )
    verdict, report, recommendation = await research_verdict(
        repo, experiment_id, cycle, idea, "REFINE_SAME_IDEA"
    )
    feedback = await return_feedback(repo, experiment_id, idea, report, recommendation)
    await repo.return_to_refinement(
        verdict.id,
        feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
        command_key=uuid4(),
    )
    async with governance_engine.connect() as connection:
        attempts_before = await connection.scalar(
            select(func.count())
            .select_from(records.research_attempts)
            .where(records.research_attempts.c.cycle_id == cycle.id)
        )

    with pytest.raises(ProductRecordsDenied, match="NON_CURRENT_CYCLE"):
        await repo.start_market_research(
            experiment_id,
            cycle.id,
            accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            plan=ArtifactInput.from_receipt(unused_plan, role="PLAN"),
            command_key=uuid4(),
        )

    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                select(func.count())
                .select_from(records.research_attempts)
                .where(records.research_attempts.c.cycle_id == cycle.id)
            )
        ) == attempts_before
