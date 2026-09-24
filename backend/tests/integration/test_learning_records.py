"""Phase 3A contract: offline learning records are available as a separate ledger."""

from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from test_product_records import NOW, artifact, roots

from alon_ai import records
from alon_ai.records import (
    ArtifactKind,
    EngineeringCapabilityRequestInput,
    LearningArtifactReference,
    LearningCandidateInput,
    LearningEvaluationRequest,
    LearningInputBundleInput,
    LearningMetric,
    LearningProposalRequest,
    LearningReviewControlRequest,
    LearningScopeInput,
    ProductRecordsDenied,
)
from alon_ai.records.learning_models import ProposalClass, TargetSubsystem

pytestmark = pytest.mark.integration


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def test_offline_learning_ledger_is_a_public_record_contract():
    """The learning ledger must remain distinct from runtime strategy execution."""
    assert hasattr(records, "LearningRecordsRepository")
    assert hasattr(records, "LearningProposalRequest")


async def proposal_request(
    engine,
    *,
    proposal_class: ProposalClass = "PROMPT_CHANGE",
    candidate: bool = True,
):
    product, _, experiment_id, workflow_id, agent_id = await roots(
        engine, suffix="learning"
    )
    baseline = artifact(
        experiment_id,
        ArtifactKind.OUTREACH_PROMPT_CONFIGURATION,
        {"template": "Synthetic approved baseline."},
        workflow_id=workflow_id,
        agent_id=agent_id,
    )
    receipt = await product.append_artifact(baseline, command_key=uuid4())
    reference = LearningArtifactReference(
        id=receipt.artifact_id,
        kind=receipt.kind.value,
        version=receipt.version,
        content_hash=receipt.content_hash,
        role="BASELINE",
    )
    review_target: TargetSubsystem = "PROMPT_CONFIGURATION"
    if proposal_class == "OFFER_OR_PRODUCT_CHANGE":
        review_target = "PRODUCT_REVIEW"
    elif proposal_class == "ENGINEERING_CAPABILITY_REQUEST":
        review_target = "ENGINEERING_REVIEW"
    candidate_input = (
        LearningCandidateInput(
            id=uuid4(),
            logical_id=uuid4(),
            version=1,
            baseline_artifact=reference,
            candidate_configuration={
                "role": "OUTREACH",
                "drafting_rule_version": "draft-v1",
                "validation_rule_version": "validate-v1",
            },
            config_diff=(
                {
                    "op": "REPLACE",
                    "path": "/drafting_rule_version",
                    "value": "draft-v1",
                },
            ),
            diff_hash=digest("diff"),
            content_hash=digest("candidate"),
        )
        if candidate
        else None
    )
    request = LearningProposalRequest(
        id=uuid4(),
        logical_id=uuid4(),
        version=1,
        experiment_id=experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        agent_version_hash=digest("agent-version"),
        evaluator_version="offline-evaluator-v1",
        evaluator_hash=digest("evaluator"),
        inputs=LearningInputBundleInput(
            id=uuid4(), artifacts=(reference,), content_hash=digest("inputs")
        ),
        scope=LearningScopeInput(
            id=uuid4(),
            target_subsystem=review_target,
            protected_components=(
                "AUTHORIZATION",
                "COMPLIANCE",
                "COMMERCIAL_POLICY",
                "OFFER_ACCEPTANCE",
                "PRODUCT_POLICY",
            ),
            content_hash=digest("scope"),
        ),
        proposal_class=proposal_class,
        bottleneck="Synthetic offline evaluation bottleneck.",
        expected_effect={"metric": "SYNTHETIC_RESPONSE_QUALITY"},
        target_metrics=(
            LearningMetric(
                code="SYNTHETIC_RESPONSE_QUALITY", comparator="GTE", threshold=0.8
            ),
        ),
        protected_metrics=(
            LearningMetric(code="SYNTHETIC_SAFETY", comparator="GTE", threshold=1),
        ),
        confidence=0.7,
        sample_size=20,
        confounders=("SYNTHETIC_DATA",),
        evaluation_criteria={"rule": "deterministic"},
        rollback_criteria={"rule": "no protected regression"},
        candidate=candidate_input,
        proposed_by=UUID(int=1),
        content_hash=digest("proposal"),
    )
    return records.LearningRecordsRepository(engine, clock=lambda: NOW), request


async def test_learning_proposal_replays_and_retains_exact_offline_lineage(
    governance_engine,
):
    repository, request = await proposal_request(governance_engine)
    key = uuid4()
    first = await repository.record_proposal(request, command_key=key)
    replay = await repository.record_proposal(request, command_key=key)

    assert replay == first
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM record_learning_proposals WHERE id=:id"),
                {"id": request.id},
            )
            == 1
        )
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM record_outbox WHERE aggregate_id=:id"),
                {"id": request.id},
            )
            == 1
        )
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repository.record_proposal(
            request.model_copy(update={"bottleneck": "Changed immutable request."}),
            command_key=key,
        )


async def test_only_allowed_classes_can_create_candidates_and_protected_diff_is_rejected(
    governance_engine,
):
    _, prompt = await proposal_request(governance_engine)
    assert prompt.candidate is not None
    with pytest.raises(ValueError, match="invalid provider contract"):
        LearningCandidateInput(
            id=uuid4(),
            logical_id=uuid4(),
            version=1,
            baseline_artifact=prompt.candidate.baseline_artifact,
            candidate_configuration={"mode": "open"},
            config_diff=(
                {"op": "REPLACE", "path": "/authorization/mode", "value": "open"},
            ),
            diff_hash=digest("bad-diff"),
            content_hash=digest("bad-candidate"),
        )
    with pytest.raises(ValueError, match="invalid provider contract"):
        await proposal_request(
            governance_engine, proposal_class="OFFER_OR_PRODUCT_CHANGE", candidate=True
        )


async def test_negative_evaluation_is_retained_immutably_and_rolls_back_without_partial_graph(
    governance_engine,
):
    repository, request = await proposal_request(governance_engine)
    assert request.candidate is not None
    proposal = await repository.record_proposal(request, command_key=uuid4())
    evaluation = LearningEvaluationRequest(
        id=uuid4(),
        proposal_id=proposal.proposal_id,
        candidate_id=proposal.candidate_id,
        evaluator_version="offline-evaluator-v1",
        evaluator_hash=digest("evaluator"),
        baseline_hash=request.candidate.baseline_artifact.content_hash,
        candidate_hash=request.candidate.content_hash,
        metric_results={"SYNTHETIC_RESPONSE_QUALITY": 0.1},
        disposition="FAIL",
        rollback_satisfied=True,
        content_hash=digest("evaluation"),
        failure_reason_codes=("REGRESSION",),
        negative_classification="DISPROVEN_HYPOTHESIS",
    )
    result = await repository.record_evaluation(evaluation, command_key=uuid4())
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_learning_failure_analyses WHERE comparison_id=:id"
                ),
                {"id": result.comparison_id},
            )
            == 1
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_negative_learning_records WHERE comparison_id=:id"
                ),
                {"id": result.comparison_id},
            )
            == 1
        )
    async with governance_engine.begin() as connection:
        with pytest.raises(SQLAlchemyError):
            await connection.execute(
                text(
                    "UPDATE record_learning_offline_comparisons SET content_hash=:hash WHERE id=:id"
                ),
                {"hash": digest("changed"), "id": result.comparison_id},
            )

    bad = request.model_copy(
        update={
            "id": uuid4(),
            "inputs": request.inputs.model_copy(
                update={
                    "id": uuid4(),
                    "artifacts": (
                        request.inputs.artifacts[0].model_copy(update={"id": uuid4()}),
                    ),
                }
            ),
            "scope": request.scope.model_copy(update={"id": uuid4()}),
            "logical_id": uuid4(),
            "candidate": request.candidate.model_copy(
                update={"id": uuid4(), "logical_id": uuid4()}
            ),
        }
    )
    with pytest.raises(ProductRecordsDenied):
        await repository.record_proposal(bad, command_key=uuid4())
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM record_learning_proposals WHERE id=:id"),
                {"id": bad.id},
            )
            == 0
        )


async def test_engineering_request_and_review_controls_remain_descriptive_records(
    governance_engine,
):
    repository, request = await proposal_request(
        governance_engine,
        proposal_class="ENGINEERING_CAPABILITY_REQUEST",
        candidate=False,
    )
    proposal = await repository.record_proposal(request, command_key=uuid4())
    engineering = EngineeringCapabilityRequestInput(
        id=uuid4(),
        proposal_id=proposal.proposal_id,
        description="A descriptive request for human engineering review.",
        boundary="No runtime execution or strategy activation.",
        expected_benefit="Offline evaluation coverage.",
        risk="Requires operator review.",
        content_hash=digest("engineering"),
    )
    await repository.record_engineering_capability_request(
        engineering, command_key=uuid4()
    )
    await repository.record_review_control(
        LearningReviewControlRequest(
            id=uuid4(),
            run_id=proposal.run_id,
            kind="PAUSE_OFFLINE_REVIEW",
            operator_id=UUID(int=1),
            content_hash=digest("pause"),
        ),
        command_key=uuid4(),
    )
    async with governance_engine.connect() as connection:
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM record_engineering_capability_requests WHERE id=:id"
                ),
                {"id": engineering.id},
            )
            == 1
        )
        assert await connection.scalar(text("SELECT count(*) FROM gov_operations")) == 0
