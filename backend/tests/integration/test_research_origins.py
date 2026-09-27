"""Explicit discovery origins and separately bounded research returns."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_product_record_guards import put
from test_product_records import artifact, roots

from alon_ai.records import ArtifactInput, ArtifactKind, ProductRecordsDenied
from alon_ai.records import schema as records

pytestmark = pytest.mark.integration


async def test_first_refinement_material_pivot_requires_exact_approval(
    governance_engine,
):
    repo, _, exp, _, _ = await roots(governance_engine)
    seed = await put(
        repo,
        exp,
        ArtifactKind.IDEA_SEED,
        {"origin": "USER_SUPPLIED", "statement": "Original work."},
    )
    cycle = await repo.create_cycle(
        exp, seed=ArtifactInput.from_receipt(seed, role="SEED"), command_key=uuid4()
    )
    idea = await put(
        repo,
        exp,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Changed",
            "customer": "Other buyer",
            "problem": "Other pain",
            "core_intent": "different",
            "material_pivot": True,
        },
    )
    target = ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA")
    with pytest.raises(ProductRecordsDenied):
        await repo.accept_idea(
            cycle.id, target, accepted_by=UUID(int=1), command_key=uuid4()
        )
    approval = await repo.approve_material_pivot(
        cycle.id, target, approved_by=UUID(int=1), command_key=uuid4()
    )
    accepted = await repo.accept_idea(
        cycle.id,
        target,
        accepted_by=UUID(int=1),
        pivot_approval_id=approval.id,
        command_key=uuid4(),
    )
    assert accepted.artifact_id == idea.artifact_id


async def test_system_discovery_requires_selection_without_fabricated_seed(
    governance_engine,
):
    repo, _, exp, workflow, agent = await roots(governance_engine)
    candidate = await repo.append_artifact(
        artifact(
            exp,
            ArtifactKind.IDEA_CANDIDATE,
            {"title": "Candidate", "hypothesis": "Demand"},
            workflow_id=workflow,
            agent_id=agent,
        ),
        command_key=uuid4(),
    )
    target = ArtifactInput.from_receipt(candidate, role="CANDIDATE")
    selection = await repo.select_idea_candidate(
        exp,
        target,
        selected_by=UUID(int=1),
        reason="Fits delivery skills",
        command_key=uuid4(),
    )
    cycle = await repo.create_cycle(
        exp, candidate=target, selection_id=selection.result_id, command_key=uuid4()
    )
    async with governance_engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(records.cycles).where(records.cycles.c.id == cycle.id)
                )
            )
            .mappings()
            .one()
        )
        assert row["idea_mode"] == "SYSTEM_DISCOVERY"
        assert row["selection_id"] == selection.result_id
        assert not await connection.scalar(
            select(records.artifacts.c.id).where(
                records.artifacts.c.experiment_id == exp,
                records.artifacts.c.kind == "IDEA_SEED",
            )
        )


async def research_verdict(repo, exp, cycle, idea, verdict_kind, feedback=None):
    inputs = [ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA")]
    if feedback is not None:
        inputs.append(ArtifactInput.from_receipt(feedback, role="RETURN_FEEDBACK"))
    plan = await put(
        repo,
        exp,
        ArtifactKind.RESEARCH_PLAN,
        {
            "questions": ["Can buyers justify spend?"],
            "method": "Targeted evidence review",
        },
        inputs=inputs,
    )
    attempt = await repo.start_market_research(
        exp,
        cycle.id,
        accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        plan=ArtifactInput.from_receipt(plan, role="PLAN"),
        command_key=uuid4(),
    )
    report = await put(
        repo,
        exp,
        ArtifactKind.MARKET_RESEARCH_REPORT,
        {"finding": "Observed evidence", "limitations": ["Bounded sample"]},
        inputs=(ArtifactInput.from_receipt(plan, role="PLAN"),),
    )
    recommendation = await put(
        repo,
        exp,
        ArtifactKind.MARKET_RESEARCH_RECOMMENDATION,
        {
            "recommendation": verdict_kind,
            "rationale": "Evidence supports this disposition",
        },
        inputs=(ArtifactInput.from_receipt(report, role="REPORT"),),
    )
    verdict = await repo.commit_verdict(
        attempt.id,
        report=ArtifactInput.from_receipt(report, role="REPORT"),
        recommendation=ArtifactInput.from_receipt(
            recommendation, role="RECOMMENDATION"
        ),
        verdict=verdict_kind,
        committed_by=UUID(int=1),
        command_key=uuid4(),
    )
    return verdict, report, recommendation


async def return_feedback(
    repo, exp, idea, report, recommendation, *, gap=False, dimensions=None
):
    from test_product_records import accept_feedback

    kind = (
        ArtifactKind.OFFER_RESEARCH_GAP_BRIEF
        if gap
        else ArtifactKind.RESEARCH_FEEDBACK_BRIEF
    )
    payload = (
        {
            "required_evidence": ["Missing supplier quote"],
            "justification": "Price cannot be responsibly set",
        }
        if gap
        else {
            "preserve": ["Original pain and buyer intent"],
            "change": ["Obtain missing willingness-to-pay evidence"],
            "failed_dimensions": list(dimensions or ("WILLINGNESS_TO_PAY",)),
            "research_questions": ["What price range is credible?"],
        }
    )
    feedback = await put(
        repo,
        exp,
        kind,
        payload,
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
    )
    await accept_feedback(repo, exp, feedback)
    return feedback


async def accepted_idea(repo, exp, cycle):
    idea = await put(
        repo,
        exp,
        ArtifactKind.IDEA_BRIEF,
        {
            "title": "Service",
            "customer": "Operators",
            "problem": "Manual work",
            "core_intent": "reduce-manual-work",
            "material_pivot": False,
        },
    )
    await repo.accept_idea(
        cycle.id,
        ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
        accepted_by=UUID(int=1),
        command_key=uuid4(),
    )
    return idea


async def test_same_intent_return_requires_committed_exact_feedback_and_preserves_prior_idea(
    governance_engine,
):
    """The L07 return command cannot be forged from a bare feedback artifact."""
    from test_product_record_guards import cycle_fixture

    repo, exp, seed, cycle, idea, _ = await cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "REFINE_SAME_IDEA"
    )
    feedback = await return_feedback(repo, exp, idea, report, recommendation)

    receipt = await repo.start_same_intent_refinement_return(
        verdict.id,
        feedback=ArtifactInput.from_receipt(feedback, role="RESEARCH_FEEDBACK"),
        command_key=uuid4(),
    )

    assert receipt.experiment_id == exp
    async with governance_engine.connect() as connection:
        returned = (
            (
                await connection.execute(
                    select(records.cycles).where(records.cycles.c.id == receipt.id)
                )
            )
            .mappings()
            .one()
        )
        lineage = (
            (
                await connection.execute(
                    select(records.returns).where(
                        records.returns.c.to_cycle_id == receipt.id
                    )
                )
            )
            .mappings()
            .one()
        )
    assert returned["purpose"] == "SAME_INTENT_RETURN"
    assert returned["seed_artifact_id"] == seed.artifact_id
    assert lineage["idea_artifact_id"] == idea.artifact_id
    assert lineage["feedback_artifact_id"] == feedback.artifact_id

    forged = ArtifactInput.from_receipt(feedback, role="RESEARCH_FEEDBACK")
    with pytest.raises(ProductRecordsDenied, match="STALE_INPUT"):
        await repo.start_same_intent_refinement_return(
            verdict.id,
            feedback=forged.model_copy(update={"content_hash": "0" * 64}),
            command_key=uuid4(),
        )


async def test_l07_return_payload_migration_preserves_unrelated_artifact_validation(
    governance_engine,
):
    """The rich L07 payload validator must retain the prior artifact contract."""
    repo, _, experiment_id, _, _ = await roots(governance_engine)
    receipt = await put(
        repo,
        experiment_id,
        ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE,
        {
            "status": "FROZEN",
        },
    )
    assert receipt.kind is ArtifactKind.OFFER_DESIGN_INPUT_BUNDLE


async def test_same_intent_return_rejects_uncommitted_and_forged_feedback(
    governance_engine,
):
    repo, exp, _, cycle, idea, _ = await __import__(
        "test_product_record_guards", fromlist=["cycle_fixture"]
    ).cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "REFINE_SAME_IDEA"
    )
    payload = {
        "preserve": ["Original buyer"],
        "change": ["Clarify pricing evidence"],
        "failed_dimensions": ["WILLINGNESS_TO_PAY"],
        "research_questions": ["Which price range is credible?"],
    }
    uncommitted = await put(
        repo,
        exp,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        payload,
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(report, role="REPORT"),
            ArtifactInput.from_receipt(recommendation, role="RECOMMENDATION"),
        ),
    )
    with pytest.raises(ProductRecordsDenied, match="UNCOMMITTED_FEEDBACK"):
        await repo.start_same_intent_refinement_return(
            verdict.id,
            feedback=ArtifactInput.from_receipt(uncommitted, role="RESEARCH_FEEDBACK"),
            command_key=uuid4(),
        )
    forged = await put(
        repo,
        exp,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        payload | {"failed_dimensions": ["DELIVERY_FIT"]},
        inputs=(ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),),
    )
    from test_product_records import accept_feedback

    await accept_feedback(repo, exp, forged)
    with pytest.raises(ProductRecordsDenied, match="FORGED_RESEARCH_FEEDBACK"):
        await repo.start_same_intent_refinement_return(
            verdict.id,
            feedback=ArtifactInput.from_receipt(forged, role="RESEARCH_FEEDBACK"),
            command_key=uuid4(),
        )


async def test_same_intent_returns_block_repeated_dimensions_and_third_return(
    governance_engine,
):
    from test_product_record_guards import cycle_fixture

    repo, exp, _, cycle, idea, _ = await cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "REFINE_SAME_IDEA"
    )
    feedback = await return_feedback(
        repo, exp, idea, report, recommendation, dimensions=("PRICE",)
    )
    first = await repo.start_same_intent_refinement_return(
        verdict.id,
        feedback=ArtifactInput.from_receipt(feedback, role="RESEARCH_FEEDBACK"),
        command_key=uuid4(),
    )
    assert first.outcome == "STARTED"
    idea = await accepted_idea(repo, exp, first)
    verdict, report, recommendation = await research_verdict(
        repo, exp, first, idea, "REFINE_SAME_IDEA", feedback
    )
    repeated = await return_feedback(
        repo, exp, idea, report, recommendation, dimensions=("PRICE",)
    )
    blocked = await repo.start_same_intent_refinement_return(
        verdict.id,
        feedback=ArtifactInput.from_receipt(repeated, role="RESEARCH_FEEDBACK"),
        command_key=uuid4(),
    )
    assert blocked.outcome == "REVIEW_REQUIRED"
    assert blocked.reason_code == "REPEATED_BLOCKER"

    # Distinct feedback may return once more, but the third automatic return is
    # retained as an operator-review block rather than changing direction.
    distinct = await return_feedback(
        repo, exp, idea, report, recommendation, dimensions=("DELIVERY",)
    )
    second = await repo.start_same_intent_refinement_return(
        verdict.id,
        feedback=ArtifactInput.from_receipt(distinct, role="RESEARCH_FEEDBACK"),
        command_key=uuid4(),
    )
    assert second.outcome == "STARTED"
    next_idea = await accepted_idea(repo, exp, second)
    verdict, report, recommendation = await research_verdict(
        repo, exp, second, next_idea, "REFINE_SAME_IDEA", distinct
    )
    third_feedback = await return_feedback(
        repo, exp, next_idea, report, recommendation, dimensions=("EVIDENCE",)
    )
    limited = await repo.start_same_intent_refinement_return(
        verdict.id,
        feedback=ArtifactInput.from_receipt(third_feedback, role="RESEARCH_FEEDBACK"),
        command_key=uuid4(),
    )
    assert limited.outcome == "REVIEW_REQUIRED"
    assert limited.reason_code == "SAME_INTENT_LIMIT_REACHED"


async def test_return_quotas_are_scoped_and_cannot_reset_episode(governance_engine):
    from test_product_record_guards import cycle_fixture

    repo, exp, seed, cycle, idea, _ = await cycle_fixture(governance_engine)
    feedback = None
    for expected_ordinal, verdict_kind, return_kind in [
        (2, "REFINE_SAME_IDEA", "SAME_INTENT"),
        (3, "INCONCLUSIVE", "INCONCLUSIVE_SUPPLEMENT"),
        (4, "REFINE_SAME_IDEA", "SAME_INTENT"),
    ]:
        verdict, report, recommendation = await research_verdict(
            repo, exp, cycle, idea, verdict_kind, feedback
        )
        feedback = await return_feedback(repo, exp, idea, report, recommendation)
        key = uuid4()
        next_cycle = await repo.return_to_research(
            verdict.id,
            kind=return_kind,
            feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
            command_key=key,
        )
        assert next_cycle.ordinal == expected_ordinal
        assert next_cycle == await repo.return_to_research(
            verdict.id,
            kind=return_kind,
            feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
            command_key=key,
        )
        if return_kind == "INCONCLUSIVE_SUPPLEMENT":
            assert (
                await repo.current_idea(next_cycle.id)
            ).artifact_id == idea.artifact_id
        else:
            idea = await accepted_idea(repo, exp, next_cycle)
        cycle = next_cycle
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "INCONCLUSIVE", feedback
    )
    feedback = await return_feedback(repo, exp, idea, report, recommendation)
    with pytest.raises(ProductRecordsDenied):
        await repo.return_to_research(
            verdict.id,
            kind="INCONCLUSIVE_SUPPLEMENT",
            feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
            command_key=uuid4(),
        )
    async with governance_engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(records.returns).where(
                        records.returns.c.experiment_id == exp
                    )
                )
            )
            .mappings()
            .all()
        )
        assert sorted(
            row["ordinal"] for row in rows if row["kind"] == "SAME_INTENT"
        ) == [1, 2]
        assert {
            row["applicable_scope_id"] for row in rows if row["kind"] == "SAME_INTENT"
        } == {seed.artifact_id}
        assert (
            len(
                (
                    await connection.execute(
                        select(records.verdicts).where(
                            records.verdicts.c.experiment_id == exp
                        )
                    )
                ).all()
            )
            == 4
        )


async def test_third_same_intent_return_is_denied(governance_engine):
    from test_product_record_guards import cycle_fixture

    repo, exp, _, cycle, idea, _ = await cycle_fixture(governance_engine)
    feedback = None
    for index in range(3):
        verdict, report, recommendation = await research_verdict(
            repo, exp, cycle, idea, "REFINE_SAME_IDEA", feedback
        )
        feedback = await return_feedback(repo, exp, idea, report, recommendation)
        if index == 2:
            with pytest.raises(ProductRecordsDenied):
                await repo.return_to_refinement(
                    verdict.id,
                    feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
                    command_key=uuid4(),
                )
        else:
            cycle = await repo.return_to_refinement(
                verdict.id,
                feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
                command_key=uuid4(),
            )
            idea = await accepted_idea(repo, exp, cycle)


async def test_offer_gap_activation_requires_real_accepted_offer_input_bundle(
    governance_engine,
):
    from test_product_record_guards import cycle_fixture

    repo, exp, _, cycle, idea, _ = await cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "PROCEED_TO_OFFER"
    )
    feedback = await return_feedback(repo, exp, idea, report, recommendation, gap=True)
    for bundle in [None, report.artifact_id, uuid4()]:
        with pytest.raises(ProductRecordsDenied):
            await repo.return_to_research(
                verdict.id,
                kind="OFFER_GAP",
                feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
                offer_input_bundle_id=bundle,
                command_key=uuid4(),
            )
    assert (await repo.current_idea(cycle.id)).artifact_id == idea.artifact_id


async def test_concurrent_return_commands_create_one_child(governance_engine):
    import asyncio

    from test_product_record_guards import cycle_fixture

    repo, exp, _, cycle, idea, _ = await cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "INCONCLUSIVE"
    )
    feedback = await return_feedback(repo, exp, idea, report, recommendation)
    results = await asyncio.gather(
        *(
            repo.return_to_research(
                verdict.id,
                kind="INCONCLUSIVE_SUPPLEMENT",
                feedback=ArtifactInput.from_receipt(feedback, role="FEEDBACK"),
                command_key=uuid4(),
            )
            for _ in range(2)
        ),
        return_exceptions=True,
    )
    assert sum(isinstance(result, ProductRecordsDenied) for result in results) == 1
    async with governance_engine.connect() as connection:
        assert (
            len(
                (
                    await connection.execute(
                        select(records.returns).where(
                            records.returns.c.experiment_id == exp
                        )
                    )
                ).all()
            )
            == 1
        )
        assert (
            len(
                (
                    await connection.execute(
                        select(records.cycles).where(
                            records.cycles.c.experiment_id == exp
                        )
                    )
                ).all()
            )
            == 2
        )


async def test_raw_episode_reset_and_selection_tuple_changes_fail(governance_engine):
    from sqlalchemy import insert
    from sqlalchemy.exc import SQLAlchemyError
    from test_product_record_guards import cycle_fixture

    repo, exp, _, cycle, idea, _ = await cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "INCONCLUSIVE"
    )
    feedback = await return_feedback(repo, exp, idea, report, recommendation)
    async with governance_engine.connect() as connection:
        parent = dict(
            (
                await connection.execute(
                    select(records.cycles).where(records.cycles.c.id == cycle.id)
                )
            )
            .mappings()
            .one()
        )
    child_id = uuid4()
    for changed in [
        {"episode_id": child_id},
        {"selection_id": uuid4()},
        {"idea_mode": "SYSTEM_DISCOVERY"},
    ]:
        with pytest.raises(SQLAlchemyError):
            async with governance_engine.begin() as connection:
                await connection.execute(
                    insert(records.cycles).values(
                        **(
                            parent
                            | {
                                "id": child_id,
                                "ordinal": 2,
                                "parent_cycle_id": cycle.id,
                                "purpose": "INCONCLUSIVE_SUPPLEMENT",
                            }
                            | changed
                        )
                    )
                )
    # A valid child still cannot be committed with a forged quota scope.
    with pytest.raises(SQLAlchemyError):
        async with governance_engine.begin() as connection:
            await connection.execute(
                insert(records.cycles).values(
                    **(
                        parent
                        | {
                            "id": child_id,
                            "ordinal": 2,
                            "parent_cycle_id": cycle.id,
                            "purpose": "INCONCLUSIVE_SUPPLEMENT",
                        }
                    )
                )
            )
            await connection.execute(
                insert(records.returns).values(
                    id=uuid4(),
                    experiment_id=exp,
                    from_cycle_id=cycle.id,
                    verdict_id=verdict.id,
                    to_cycle_id=child_id,
                    ordinal=1,
                    kind="INCONCLUSIVE_SUPPLEMENT",
                    applicable_scope_id=uuid4(),
                    idea_artifact_id=idea.artifact_id,
                    feedback_artifact_id=feedback.artifact_id,
                    feedback_kind=feedback.kind,
                    feedback_version=feedback.version,
                    feedback_hash=feedback.content_hash,
                    created_at=parent["created_at"],
                )
            )


async def test_missing_or_other_cycle_feedback_cannot_authorize_return(
    governance_engine,
):
    from test_product_record_guards import cycle_fixture
    from test_product_records import accept_feedback

    repo, exp, _, cycle, idea, _ = await cycle_fixture(governance_engine)
    verdict, report, recommendation = await research_verdict(
        repo, exp, cycle, idea, "INCONCLUSIVE"
    )
    unbound = await put(
        repo,
        exp,
        ArtifactKind.RESEARCH_FEEDBACK_BRIEF,
        {"preserve": ["Original intent"], "change": ["Research supplement"]},
    )
    await accept_feedback(repo, exp, unbound)
    with pytest.raises(ProductRecordsDenied):
        await repo.return_to_research(
            verdict.id,
            kind="INCONCLUSIVE_SUPPLEMENT",
            feedback=ArtifactInput.from_receipt(unbound, role="FEEDBACK"),
            command_key=uuid4(),
        )
    valid = await return_feedback(repo, exp, idea, report, recommendation)
    next_cycle = await repo.return_to_research(
        verdict.id,
        kind="INCONCLUSIVE_SUPPLEMENT",
        feedback=ArtifactInput.from_receipt(valid, role="FEEDBACK"),
        command_key=uuid4(),
    )
    plan = await put(
        repo,
        exp,
        ArtifactKind.RESEARCH_PLAN,
        {"questions": ["Missing question"], "method": "Supplement"},
        inputs=(
            ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            ArtifactInput.from_receipt(unbound, role="RETURN_FEEDBACK"),
        ),
    )
    with pytest.raises(ProductRecordsDenied):
        await repo.start_market_research(
            exp,
            next_cycle.id,
            accepted_idea=ArtifactInput.from_receipt(idea, role="ACCEPTED_IDEA"),
            plan=ArtifactInput.from_receipt(plan, role="PLAN"),
            command_key=uuid4(),
        )
