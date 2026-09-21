"""Phase 3B strategy-package and governed execution persistence."""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import SQLAlchemyError
from test_learning_records import NOW, digest, proposal_request
from test_organization_records import complete_content, provision_call

from alon_ai import records
from alon_ai.accounting import schema as governance
from alon_ai.accounting.repository import GovernanceProvisioner
from alon_ai.providers.contracts import (
    AgentActor,
    CallAttribution,
    Capability,
    ContentField,
    OperationRunKind,
    SafeRequestMetadata,
)
from alon_ai.records import (
    FreezeExperimentStrategyRequest,
    GlobalStrategyPackageRequest,
    LearningCallSnapshot,
    LearningCostReference,
    LearningEvaluationRequest,
    LearningEvidenceReference,
    LearningInputBundleInput,
    LearningUsageReference,
    LiveRegressionAssessmentRequest,
    LiveStrategyMetricInput,
    LiveStrategyObservationRequest,
    ProductRecordsDenied,
    PromotionDecisionRequest,
    RollbackCandidateInput,
    RollbackDecisionRequest,
    StrategyAgentVersionInput,
    StrategyControlRequest,
    StrategyExecutionBindingRequest,
)
from alon_ai.records import schema as product_schema
from alon_ai.records.learning_models import (
    DiscoveryStrategyConfiguration,
    OutreachStrategyConfiguration,
    QualificationStrategyConfiguration,
    ReplyStrategyConfiguration,
)

pytestmark = pytest.mark.integration


def test_strategy_package_contract_is_public():
    assert hasattr(records, "StrategyAgentVersionInput")
    assert hasattr(records, "GlobalStrategyPackageRequest")
    assert hasattr(records.LearningRecordsRepository, "record_strategy_package")


def test_promotion_observation_rollback_and_control_contracts_are_public():
    for name in (
        "PromotionDecisionRequest",
        "LiveStrategyObservationRequest",
        "LiveRegressionAssessmentRequest",
        "RollbackDecisionRequest",
        "StrategyControlRequest",
    ):
        assert hasattr(records, name)


async def strategy_package(engine, *, version=1, supersedes_id=None):
    repository, proposal_request_value = await proposal_request(engine)
    proposal = await repository.record_proposal(
        proposal_request_value, command_key=uuid4()
    )
    prompt = proposal_request_value.inputs.artifacts[0]
    configurations = (
        DiscoveryStrategyConfiguration(
            role="DISCOVERY",
            discovery_rule_version="discovery-v1",
            source_order=("BRAVE_LOCAL", "OFFICIAL_WEB"),
        ),
        QualificationStrategyConfiguration(
            role="QUALIFICATION",
            matrix_rule_version="matrix-v1",
            revalidation_rule_version="revalidate-v1",
        ),
        OutreachStrategyConfiguration(
            role="OUTREACH",
            drafting_rule_version="draft-v1",
            validation_rule_version="validate-v1",
        ),
        ReplyStrategyConfiguration(
            role="REPLY",
            interpretation_rule_version="interpret-v1",
            response_rule_version="respond-v1",
        ),
    )
    members = tuple(
        StrategyAgentVersionInput(
            id=uuid4(),
            logical_id=uuid4(),
            version=version,
            prompt=prompt,
            model_identifier="fixture-model",
            reasoning_effort="MEDIUM",
            max_tool_calls=12,
            max_searches=8,
            max_pages=20,
            configuration=configuration,
        )
        for configuration in configurations
    )
    request = GlobalStrategyPackageRequest(
        id=uuid4(),
        logical_id=uuid4() if version == 1 else UUID(int=9000),
        version=version,
        supersedes_id=supersedes_id,
        members=members,
        created_by=UUID(int=1),
    )
    return repository, proposal_request_value, proposal, request, None


async def bound_strategy(engine):
    repository, request, proposal, package, _governed = await strategy_package(engine)
    await repository.record_strategy_package(package, command_key=uuid4())
    return await bind_recorded_package(
        engine, repository=repository, request=request, proposal=proposal, package=package
    )


async def bind_recorded_package(engine, *, repository, request, proposal, package):
    await repository.freeze_experiment_strategy(
        FreezeExperimentStrategyRequest(
            experiment_id=request.experiment_id,
            package_id=package.id,
            frozen_by=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    governed = await provision_call(
        engine,
        request.experiment_id,
        Capability.OPENAI_GENERATE,
        {ContentField.COMPANY},
    )
    _governance_repository, attribution, config, _grant, _call_id, _receipt = governed
    workflow_id, agent_id, operation_id = attribution.workflow_run_id, uuid4(), uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            insert(governance.agents).values(id=agent_id, workflow_id=workflow_id)
        )
        await connection.execute(
            insert(product_schema.workflows).values(
                id=workflow_id,
                experiment_id=request.experiment_id,
                role="STRATEGY_EXECUTION",
                created_at=NOW,
            )
        )
        await connection.execute(
            insert(product_schema.agents).values(
                id=agent_id,
                workflow_id=workflow_id,
                role="OUTREACH",
                created_at=NOW,
            )
        )
        await connection.execute(
            insert(governance.operations).values(
                id=operation_id,
                experiment_id=request.experiment_id,
                workflow_id=workflow_id,
                kind="RESEARCH",
                agent_id=agent_id,
                config_version=attribution.config_version,
                gate_kind="NONE",
            )
        )
    outreach = next(
        item for item in package.members if item.configuration.role == "OUTREACH"
    )
    binding = StrategyExecutionBindingRequest(
        id=uuid4(),
        experiment_id=request.experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        operation_id=operation_id,
        package_id=package.id,
        agent_version_id=outreach.id,
        role="OUTREACH",
        model_config_id=config.id,
        model_config_workflow_id=config.workflow_id,
        model_config_version=config.version,
    )
    await repository.bind_strategy_execution(binding, command_key=uuid4())
    governance_repository, attribution, config, grant, _call_id, _receipt = governed
    exact_attribution = CallAttribution(
        experiment_id=request.experiment_id,
        workflow_run_id=workflow_id,
        operation_run_id=operation_id,
        operation_run_kind=OperationRunKind.RESEARCH,
        actor=AgentActor(agent_run_id=agent_id),
        correlation_id=uuid4(),
        logical_operation_id=uuid4(),
        config_version=config.version,
        deadline=attribution.deadline,
    )
    await GovernanceProvisioner(engine).budgets(
        exact_attribution,
        provider=config.intended_use.provider,
        currencies=("USD", "ILS"),
        limit=Decimal(100),
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
    )
    exact_receipt = await governance_repository.reserve(
        exact_attribution,
        SafeRequestMetadata(config_ref=config.id),
        idempotency_key=uuid4(),
    )
    exact_receipt = await governance_repository.dispatch(exact_receipt.call_id)
    exact_governed = (
        governance_repository,
        exact_attribution,
        config,
        grant,
        exact_receipt.call_id,
        exact_receipt,
    )
    return repository, request, proposal, package, exact_governed, binding


async def live_observation_request(engine, *, binding_fixture):
    repository, request, _proposal, _package, governed, binding = binding_fixture
    _content, _metadata, evidence_id, _final, _retained = await complete_content(
        engine, governed, {ContentField.COMPANY: ("observed",)}
    )
    call_id = governed[4]
    async with engine.connect() as connection:
        usage = (
            (
                await connection.execute(
                    text("SELECT id,component FROM gov_usage WHERE call_id=:id"),
                    {"id": call_id},
                )
            )
            .mappings()
            .one()
        )
        settlement_id = await connection.scalar(
            text("SELECT id FROM gov_settlements WHERE call_id=:id"), {"id": call_id}
        )
    inputs = LearningInputBundleInput(
        id=uuid4(),
        artifacts=(request.inputs.artifacts[0].model_copy(update={"role": "ARTIFACT"}),),
        evidence=(
            LearningEvidenceReference(
                evidence_id=evidence_id, call_id=call_id, role="EVIDENCE"
            ),
        ),
        call_snapshots=(
            LearningCallSnapshot(
                call_id=call_id,
                snapshot={"status": "SUCCEEDED"},
                snapshot_hash=digest("call-snapshot"),
                role="CALL",
            ),
        ),
        usage=(
            LearningUsageReference(
                usage_id=usage["id"],
                call_id=call_id,
                component=usage["component"],
                role="USAGE",
            ),
        ),
        costs=(
            LearningCostReference(
                id=settlement_id, call_id=call_id, kind="SETTLEMENT", role="COST"
            ),
        ),
        content_hash=digest("live-inputs"),
    )
    observation = LiveStrategyObservationRequest(
        id=uuid4(),
        execution_binding_id=binding.id,
        segment_kind="INDUSTRY",
        segment_key="LOCAL_SERVICES",
        inputs=inputs,
        metrics=(
            LiveStrategyMetricInput(
                category="COMMERCIAL", code="REPLY_RATE", value=0.2, unit="RATIO"
            ),
            LiveStrategyMetricInput(
                category="QUALITY", code="VALIDATION_RATE", value=1.0, unit="RATIO"
            ),
            LiveStrategyMetricInput(
                category="SAFETY", code="SAFETY_FAILURES", value=0.0, unit="COUNT"
            ),
            LiveStrategyMetricInput(
                category="LATENCY", code="P95_LATENCY", value=120.0, unit="MILLISECONDS"
            ),
            LiveStrategyMetricInput(
                category="COST", code="UNIT_COST", value=0.01, unit="USD"
            ),
        ),
        observed_from=NOW,
        observed_to=NOW,
        recorded_by=UUID(int=1),
    )
    return repository, observation


async def promote_strategy(repository, *, request, proposal, baseline, label):
    assert request.candidate is not None
    evaluation = await repository.record_evaluation(
        LearningEvaluationRequest(
            id=uuid4(),
            proposal_id=proposal.proposal_id,
            candidate_id=proposal.candidate_id,
            evaluator_version="offline-evaluator-v1",
            evaluator_hash=digest(f"{label}-evaluator"),
            baseline_hash=request.candidate.baseline_artifact.content_hash,
            candidate_hash=request.candidate.content_hash,
            metric_results={"SYNTHETIC_RESPONSE_QUALITY": 0.9},
            disposition="PASS",
            rollback_satisfied=False,
            content_hash=digest(f"{label}-evaluation"),
            failure_reason_codes=(),
        ),
        command_key=uuid4(),
    )
    members = tuple(
        item.model_copy(
            update={
                "id": uuid4(),
                "version": baseline.version + 1,
                "supersedes_id": item.id,
                "origin_candidate_id": proposal.candidate_id
                if item.configuration.role == "OUTREACH"
                else None,
            }
        )
        for item in baseline.members
    )
    promoted = GlobalStrategyPackageRequest(
        id=uuid4(),
        logical_id=baseline.logical_id,
        version=baseline.version + 1,
        supersedes_id=baseline.id,
        members=members,
        created_by=UUID(int=1),
    )
    await repository.record_promotion(
        PromotionDecisionRequest(
            id=uuid4(),
            proposal_id=proposal.proposal_id,
            candidate_id=proposal.candidate_id,
            comparison_id=evaluation.comparison_id,
            assessment_id=evaluation.assessment_id,
            baseline_package_id=baseline.id,
            disposition="ACCEPTED",
            package=promoted,
            reason_codes=("OFFLINE_PASS",),
            decided_by=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    return promoted


def test_strategy_models_reject_unknown_fields_unsupported_reasoning_and_unbounded_budgets():
    base = {
        "id": uuid4(),
        "logical_id": uuid4(),
        "version": 1,
        "prompt": {
            "id": uuid4(),
            "kind": "OUTREACH_PROMPT_CONFIGURATION",
            "version": 1,
            "content_hash": digest("prompt"),
            "role": "PROMPT",
        },
        "model_identifier": "fixture-model",
        "reasoning_effort": "MEDIUM",
        "max_tool_calls": 1,
        "max_searches": 1,
        "max_pages": 1,
        "configuration": {
            "role": "OUTREACH",
            "drafting_rule_version": "draft-v1",
            "validation_rule_version": "validate-v1",
        },
    }
    for update in (
        {"unknown": "field"},
        {"reasoning_effort": "UNLIMITED"},
        {"max_tool_calls": 101},
    ):
        with pytest.raises(ValueError, match="invalid provider contract"):
            StrategyAgentVersionInput.model_validate({**base, **update})
    with pytest.raises(ValueError, match="invalid provider contract"):
        LiveStrategyMetricInput(
            category="QUALITY", code="QUALITY", value=float("inf"), unit="RATIO"
        )


async def test_complete_package_is_sealed_replay_safe_and_phase3a_inputs_reject_late_children(
    governance_engine,
):
    repository, _request, proposal, package, _governed = await strategy_package(
        governance_engine
    )
    key = uuid4()
    first = await repository.record_strategy_package(package, command_key=key)
    replay = await repository.record_strategy_package(package, command_key=key)
    assert replay == first
    async with governance_engine.connect() as connection:
        assert await connection.scalar(
            text("SELECT count(*) FROM record_strategy_package_members WHERE package_id=:id"),
            {"id": first.package_id},
        ) == 4
        assert await connection.scalar(
            text("SELECT count(*) FROM record_strategy_package_seals WHERE package_id=:id"),
            {"id": first.package_id},
        ) == 1
    async with governance_engine.begin() as connection:
        with pytest.raises(SQLAlchemyError):
            await connection.execute(
                text("""INSERT INTO record_learning_input_artifacts
                (bundle_id,role,artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash)
                SELECT input_bundle_id,'LATE_INPUT',baseline_artifact_id,baseline_experiment_id,
                       baseline_artifact_kind,baseline_artifact_version,baseline_artifact_hash
                FROM record_learning_proposals p JOIN record_learning_candidate_versions c ON c.proposal_id=p.id
                WHERE p.id=:proposal_id"""),
                {"proposal_id": proposal.proposal_id},
            )


async def test_experiment_freezes_one_package_and_execution_binding_requires_exact_lineage(
    governance_engine,
):
    repository, request, _proposal, package, _governed = await strategy_package(
        governance_engine
    )
    package_receipt = await repository.record_strategy_package(
        package, command_key=uuid4()
    )
    freeze = FreezeExperimentStrategyRequest(
        experiment_id=request.experiment_id,
        package_id=package_receipt.package_id,
        frozen_by=UUID(int=1),
    )
    first = await repository.freeze_experiment_strategy(freeze, command_key=uuid4())
    assert first.result_id == request.experiment_id
    with pytest.raises(ProductRecordsDenied):
        await repository.freeze_experiment_strategy(
            freeze.model_copy(update={"package_id": uuid4()}), command_key=uuid4()
        )

    governed = await provision_call(
        governance_engine,
        request.experiment_id,
        Capability.OPENAI_GENERATE,
        {ContentField.COMPANY},
    )
    _governance_repository, attribution, config, _grant, _call_id, _receipt = governed

    workflow_id, agent_id, operation_id = attribution.workflow_run_id, uuid4(), uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(governance.agents).values(id=agent_id, workflow_id=workflow_id)
        )
        await connection.execute(
            insert(product_schema.workflows).values(
                id=workflow_id,
                experiment_id=request.experiment_id,
                role="STRATEGY_EXECUTION",
                created_at=NOW,
            )
        )
        await connection.execute(
            insert(product_schema.agents).values(
                id=agent_id,
                workflow_id=workflow_id,
                role="OUTREACH",
                created_at=NOW,
            )
        )
        await connection.execute(
            insert(governance.operations).values(
                id=operation_id,
                experiment_id=request.experiment_id,
                workflow_id=workflow_id,
                kind="RESEARCH",
                agent_id=agent_id,
                config_version=attribution.config_version,
                gate_kind="NONE",
            )
        )
    outreach = next(
        item for item in package.members if item.configuration.role == "OUTREACH"
    )
    binding = StrategyExecutionBindingRequest(
        id=uuid4(),
        experiment_id=request.experiment_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        operation_id=operation_id,
        package_id=package_receipt.package_id,
        agent_version_id=outreach.id,
        role="OUTREACH",
        model_config_id=config.id,
        model_config_workflow_id=config.workflow_id,
        model_config_version=config.version,
    )
    receipt = await repository.bind_strategy_execution(binding, command_key=uuid4())
    assert receipt.result_id == binding.id
    with pytest.raises(ProductRecordsDenied):
        await repository.bind_strategy_execution(
            binding.model_copy(update={"agent_version_id": package.members[0].id}),
            command_key=uuid4(),
        )


async def test_promotion_uses_exact_passing_assessment_and_changes_only_future_selection(
    governance_engine,
):
    repository, request, proposal, baseline, _governed = await strategy_package(
        governance_engine
    )
    assert request.candidate is not None
    baseline_receipt = await repository.record_strategy_package(
        baseline, command_key=uuid4()
    )
    await repository.freeze_experiment_strategy(
        FreezeExperimentStrategyRequest(
            experiment_id=request.experiment_id,
            package_id=baseline_receipt.package_id,
            frozen_by=UUID(int=1),
        ),
        command_key=uuid4(),
    )
    evaluation = await repository.record_evaluation(
        LearningEvaluationRequest(
            id=uuid4(),
            proposal_id=proposal.proposal_id,
            candidate_id=proposal.candidate_id,
            evaluator_version="offline-evaluator-v1",
            evaluator_hash=digest("evaluator"),
            baseline_hash=request.candidate.baseline_artifact.content_hash,
            candidate_hash=request.candidate.content_hash,
            metric_results={"SYNTHETIC_RESPONSE_QUALITY": 0.9},
            disposition="PASS",
            rollback_satisfied=False,
            content_hash=digest("passing-evaluation"),
            failure_reason_codes=(),
        ),
        command_key=uuid4(),
    )
    promoted_members = tuple(
        item.model_copy(
            update={
                "id": uuid4(),
                "version": 2,
                "supersedes_id": item.id,
                "origin_candidate_id": proposal.candidate_id
                if item.configuration.role == "OUTREACH"
                else None,
            }
        )
        for item in baseline.members
    )
    promoted = GlobalStrategyPackageRequest(
        id=uuid4(),
        logical_id=baseline.logical_id,
        version=2,
        supersedes_id=baseline.id,
        members=promoted_members,
        created_by=UUID(int=1),
    )
    decision = PromotionDecisionRequest(
        id=uuid4(),
        proposal_id=proposal.proposal_id,
        candidate_id=proposal.candidate_id,
        comparison_id=evaluation.comparison_id,
        assessment_id=evaluation.assessment_id,
        baseline_package_id=baseline.id,
        disposition="ACCEPTED",
        package=promoted,
        reason_codes=("OFFLINE_PASS",),
        decided_by=UUID(int=1),
    )
    tampered_members = tuple(
        item.model_copy(update={"model_identifier": "unevaluated-model"})
        if item.configuration.role == "DISCOVERY"
        else item
        for item in promoted.members
    )
    with pytest.raises(ProductRecordsDenied, match="UNEVALUATED_STRATEGY_CHANGE"):
        await repository.record_promotion(
            decision.model_copy(
                update={
                    "id": uuid4(),
                    "package": promoted.model_copy(update={"members": tampered_members}),
                }
            ),
            command_key=uuid4(),
        )
    pause = StrategyControlRequest(
        id=uuid4(),
        kind="PAUSE",
        operator_id=UUID(int=1),
        reason_codes=("OPERATOR_REVIEW",),
    )
    await repository.record_strategy_control(pause, command_key=uuid4())
    with pytest.raises(ProductRecordsDenied, match="STRATEGY_REGISTRY_PAUSED"):
        await repository.record_promotion(decision, command_key=uuid4())
    await repository.record_strategy_control(
        StrategyControlRequest(
            id=uuid4(),
            kind="RESUME",
            operator_id=UUID(int=1),
            reason_codes=("OPERATOR_APPROVED",),
        ),
        command_key=uuid4(),
    )
    receipt = await repository.record_promotion(decision, command_key=uuid4())
    assert receipt.result_id == decision.id
    async with governance_engine.connect() as connection:
        frozen_package = await connection.scalar(
            text("SELECT package_id FROM record_experiment_strategy_bindings WHERE experiment_id=:id"),
            {"id": request.experiment_id},
        )
        selected_package = await connection.scalar(
            text("SELECT package_id FROM record_learning_review_controls WHERE registry_scope AND kind='PROMOTE_PACKAGE' ORDER BY event_ordinal DESC LIMIT 1")
        )
    assert frozen_package == baseline.id
    assert selected_package == promoted.id


async def test_rejected_promotion_retains_candidate_and_negative_learning(
    governance_engine,
):
    repository, request, proposal, baseline, _governed = await strategy_package(
        governance_engine
    )
    assert request.candidate is not None
    await repository.record_strategy_package(baseline, command_key=uuid4())
    evaluation = await repository.record_evaluation(
        LearningEvaluationRequest(
            id=uuid4(),
            proposal_id=proposal.proposal_id,
            candidate_id=proposal.candidate_id,
            evaluator_version="offline-evaluator-v1",
            evaluator_hash=digest("reject-evaluator"),
            baseline_hash=request.candidate.baseline_artifact.content_hash,
            candidate_hash=request.candidate.content_hash,
            metric_results={"SYNTHETIC_RESPONSE_QUALITY": 0.8},
            disposition="PASS",
            rollback_satisfied=False,
            content_hash=digest("reject-evaluation"),
            failure_reason_codes=(),
        ),
        command_key=uuid4(),
    )
    decision = PromotionDecisionRequest(
        id=uuid4(),
        proposal_id=proposal.proposal_id,
        candidate_id=proposal.candidate_id,
        comparison_id=evaluation.comparison_id,
        assessment_id=evaluation.assessment_id,
        baseline_package_id=baseline.id,
        disposition="REJECTED",
        reason_codes=("OPERATOR_REJECTED",),
        decided_by=UUID(int=1),
    )
    await repository.record_promotion(decision, command_key=uuid4())
    async with governance_engine.connect() as connection:
        assert await connection.scalar(
            text("SELECT count(*) FROM record_learning_candidate_versions WHERE id=:id"),
            {"id": proposal.candidate_id},
        ) == 1
        assert await connection.scalar(
            text("SELECT count(*) FROM record_negative_learning_records WHERE promotion_decision_id=:id"),
            {"id": decision.id},
        ) == 1


async def test_live_observation_and_negative_assessment_are_sealed_replay_safe_and_immutable(
    governance_engine,
):
    fixture = await bound_strategy(governance_engine)
    repository, observation = await live_observation_request(
        governance_engine, binding_fixture=fixture
    )
    observation_key = uuid4()
    first = await repository.record_live_observation(
        observation, command_key=observation_key
    )
    assert await repository.record_live_observation(
        observation, command_key=observation_key
    ) == first
    with pytest.raises(ProductRecordsDenied, match="COMMAND_CONFLICT"):
        await repository.record_live_observation(
            observation.model_copy(update={"segment_key": "OTHER"}),
            command_key=observation_key,
        )

    assessment = LiveRegressionAssessmentRequest(
        id=uuid4(),
        package_id=fixture[3].id,
        observation_ids=(observation.id,),
        evaluator_version="live-regression-v1",
        evaluator_hash=digest("live-evaluator"),
        disposition="FAIL",
        metric_results={"REPLY_RATE": 0.2, "SAFETY_FAILURES": 0.0},
        confidence=0.9,
        sample_size=50,
        rollback_satisfied=True,
        failure_reason_codes=("QUALITY_REGRESSION",),
        negative_classification="DISPROVEN_LIVE_STRATEGY",
    )
    assessment_key = uuid4()
    assessment_receipt = await repository.record_live_regression_assessment(
        assessment, command_key=assessment_key
    )
    assert await repository.record_live_regression_assessment(
        assessment, command_key=assessment_key
    ) == assessment_receipt
    async with governance_engine.begin() as connection:
        with pytest.raises(SQLAlchemyError):
            await connection.execute(
                text("UPDATE record_live_strategy_observations SET segment_key='changed' WHERE id=:id"),
                {"id": observation.id},
            )
    async with governance_engine.connect() as connection:
        evaluator = (
            (
                await connection.execute(
                    text("""SELECT live_evaluator_version,live_evaluator_hash
                    FROM record_learning_regression_assessments WHERE id=:id"""),
                    {"id": assessment.id},
                )
            )
            .mappings()
            .one()
        )
        assert await connection.scalar(
            text("SELECT count(*) FROM record_learning_failure_analyses WHERE live_assessment_id=:id"),
            {"id": assessment.id},
        ) == 1
        assert await connection.scalar(
            text("SELECT count(*) FROM record_negative_learning_records WHERE live_assessment_id=:id"),
            {"id": assessment.id},
        ) == 1
    assert dict(evaluator) == {
        "live_evaluator_version": assessment.evaluator_version,
        "live_evaluator_hash": assessment.evaluator_hash,
    }


async def test_rollback_selects_highest_confidence_retained_package_and_controls_append(
    governance_engine,
):
    repository, first_request, first_proposal, baseline, _governed = (
        await strategy_package(governance_engine)
    )
    await repository.record_strategy_package(baseline, command_key=uuid4())
    second = await promote_strategy(
        repository,
        request=first_request,
        proposal=first_proposal,
        baseline=baseline,
        label="second",
    )
    assert first_request.candidate is not None
    execution_request = first_request.model_copy(
        update={
            "id": uuid4(),
            "logical_id": uuid4(),
            "inputs": first_request.inputs.model_copy(
                update={"id": uuid4(), "content_hash": digest("third-inputs")}
            ),
            "scope": first_request.scope.model_copy(
                update={"id": uuid4(), "content_hash": digest("third-scope")}
            ),
            "candidate": first_request.candidate.model_copy(
                update={
                    "id": uuid4(),
                    "logical_id": uuid4(),
                    "content_hash": digest("third-candidate"),
                    "diff_hash": digest("third-diff"),
                }
            ),
            "content_hash": digest("third-proposal"),
        }
    )
    execution_proposal = await repository.record_proposal(
        execution_request, command_key=uuid4()
    )
    third = await promote_strategy(
        repository,
        request=execution_request,
        proposal=execution_proposal,
        baseline=second,
        label="third",
    )
    fixture = await bind_recorded_package(
        governance_engine,
        repository=repository,
        request=execution_request,
        proposal=execution_proposal,
        package=third,
    )
    repository, observation = await live_observation_request(
        governance_engine, binding_fixture=fixture
    )
    await repository.record_live_observation(observation, command_key=uuid4())
    assessment = LiveRegressionAssessmentRequest(
        id=uuid4(),
        package_id=third.id,
        observation_ids=(observation.id,),
        evaluator_version="live-regression-v1",
        evaluator_hash=digest("rollback-evaluator"),
        disposition="FAIL",
        metric_results={"REPLY_RATE": 0.1},
        confidence=0.95,
        sample_size=50,
        rollback_satisfied=True,
        failure_reason_codes=("COMMERCIAL_REGRESSION",),
        negative_classification="ROLLED_BACK_HYPOTHESIS",
    )
    await repository.record_live_regression_assessment(assessment, command_key=uuid4())

    rollback = RollbackDecisionRequest(
        id=uuid4(),
        current_package_id=third.id,
        target_package_id=baseline.id,
        assessment_id=assessment.id,
        candidates=(
            RollbackCandidateInput(
                package_id=second.id,
                confidence=0.7,
                eligible=True,
                reason_codes=("RETAINED_PASS",),
            ),
            RollbackCandidateInput(
                package_id=baseline.id,
                confidence=0.9,
                eligible=True,
                reason_codes=("RETAINED_PASS",),
            ),
        ),
        decided_by=UUID(int=1),
        reason_codes=("LIVE_REGRESSION",),
    )
    rollback_key = uuid4()
    first = await repository.record_rollback(rollback, command_key=rollback_key)
    assert await repository.record_rollback(rollback, command_key=rollback_key) == first

    controls = (
        StrategyControlRequest(
            id=uuid4(), kind="PAUSE", operator_id=UUID(int=1), reason_codes=("REVIEW",)
        ),
        StrategyControlRequest(
            id=uuid4(), kind="PIN", package_id=second.id,
            operator_id=UUID(int=1), reason_codes=("KNOWN_GOOD",)
        ),
        StrategyControlRequest(
            id=uuid4(), kind="RESUME", operator_id=UUID(int=1), reason_codes=("REVIEWED",)
        ),
        StrategyControlRequest(
            id=uuid4(), kind="UNPIN", operator_id=UUID(int=1), reason_codes=("EXPIRED",)
        ),
    )
    for control in controls:
        key = uuid4()
        receipt = await repository.record_strategy_control(control, command_key=key)
        assert await repository.record_strategy_control(control, command_key=key) == receipt
    async with governance_engine.connect() as connection:
        selected = await connection.scalar(
            text("""SELECT package_id FROM record_learning_review_controls
            WHERE rollback_decision_id=:id AND kind='ASSESSED_ROLLBACK'"""),
            {"id": rollback.id},
        )
        retained = await connection.scalar(
            text("""SELECT count(*) FROM record_negative_learning_records
            WHERE live_assessment_id=:id AND classification='ROLLED_BACK_STRATEGY'"""),
            {"id": assessment.id},
        )
        kinds = (
            await connection.execute(
                text("""SELECT kind FROM record_learning_review_controls
                WHERE id=ANY(:ids) ORDER BY event_ordinal"""),
                {"ids": [item.id for item in controls]},
            )
        ).scalars().all()
    assert selected == baseline.id
    assert retained == 1
    assert kinds == ["PAUSE", "PIN", "RESUME", "UNPIN"]
