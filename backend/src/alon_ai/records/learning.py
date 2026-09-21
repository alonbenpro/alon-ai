"""Atomic commands for the immutable, offline-only learning ledger."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records.learning_models import (
    EngineeringCapabilityRequestInput,
    LearningEvaluationReceipt,
    LearningEvaluationRequest,
    LearningProposalReceipt,
    LearningProposalRequest,
    LearningReviewControlRequest,
)
from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records


class LearningRecordsRepository:
    """Stores reviewable hypotheses only; it never changes runtime configuration."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.engine = engine
        self.clock = clock

    async def _proposal_receipt(self, connection, proposal_id: UUID, command_id: UUID):
        row = (
            (
                await connection.execute(
                    text("""SELECT p.id,r.id AS run_id,p.input_bundle_id,p.scope_id,c.id AS candidate_id
                    FROM record_learning_proposals p JOIN record_learning_runs r ON r.id=p.run_id
                    LEFT JOIN record_learning_candidate_versions c ON c.proposal_id=p.id WHERE p.id=:id"""),
                    {"id": proposal_id},
                )
            )
            .mappings()
            .one()
        )
        return LearningProposalReceipt(
            command_id=command_id,
            result_id=proposal_id,
            run_id=row["run_id"],
            input_bundle_id=row["input_bundle_id"],
            scope_id=row["scope_id"],
            proposal_id=proposal_id,
            candidate_id=row["candidate_id"],
        )

    @safe_records
    async def record_proposal(
        self, request: LearningProposalRequest, *, command_key: UUID
    ) -> LearningProposalReceipt:
        async with self.engine.begin() as connection:
            root = (
                (
                    await connection.execute(
                        text("""SELECT w.id AS workflow_id,a.id AS agent_id FROM record_workflows w
                        JOIN record_agents a ON a.workflow_id=w.id
                        WHERE w.id=:workflow_id AND w.experiment_id=:experiment_id AND a.id=:agent_id"""),
                        request.model_dump(include={"workflow_id", "experiment_id", "agent_id"}),
                    )
                )
                .mappings()
                .one_or_none()
            )
            if root is None:
                raise ProductRecordsDenied("LEARNING_LINEAGE_MISMATCH")
            await lock_experiment(connection, request.experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(connection, command_key, "RECORD_LEARNING_PROPOSAL", request_hash)
            if old:
                if old["result_id"] != request.id:
                    raise ProductRecordsDenied("COMMAND_CONFLICT")
                return await self._proposal_receipt(connection, request.id, old["id"])
            now = self.clock()
            run_id = uuid4()
            await connection.execute(
                text("""INSERT INTO record_learning_runs
                (id,experiment_id,workflow_id,agent_id,agent_version_hash,evaluator_version,evaluator_hash,content_hash,created_by,created_at)
                VALUES (:id,:experiment_id,:workflow_id,:agent_id,:agent_version_hash,:evaluator_version,:evaluator_hash,:content_hash,:created_by,:created_at)"""),
                {
                    "id": run_id,
                    "experiment_id": request.experiment_id,
                    "workflow_id": request.workflow_id,
                    "agent_id": request.agent_id,
                    "agent_version_hash": request.agent_version_hash,
                    "evaluator_version": request.evaluator_version,
                    "evaluator_hash": request.evaluator_hash,
                    "content_hash": request.content_hash,
                    "created_by": request.proposed_by,
                    "created_at": now,
                },
            )
            await connection.execute(
                text("""INSERT INTO record_learning_input_bundles (id,run_id,experiment_id,content_hash,created_at)
                VALUES (:id,:run_id,:experiment_id,:content_hash,:created_at)"""),
                {"id": request.inputs.id, "run_id": run_id, "experiment_id": request.experiment_id, "content_hash": request.inputs.content_hash, "created_at": now},
            )
            for item in request.inputs.artifacts:
                await connection.execute(
                    text("""INSERT INTO record_learning_input_artifacts
                    (bundle_id,role,artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash)
                    VALUES (:bundle_id,:role,:artifact_id,:experiment_id,:artifact_kind,:artifact_version,:artifact_hash)"""),
                    {"bundle_id": request.inputs.id, "role": item.role, "artifact_id": item.id, "experiment_id": request.experiment_id, "artifact_kind": item.kind, "artifact_version": item.version, "artifact_hash": item.content_hash},
                )
            for item in request.inputs.evidence:
                await connection.execute(text("INSERT INTO record_learning_input_evidence (bundle_id,role,evidence_id,call_id) VALUES (:bundle_id,:role,:evidence_id,:call_id)"), {"bundle_id": request.inputs.id, **item.model_dump()})
            for item in request.inputs.call_snapshots:
                await connection.execute(text("INSERT INTO record_learning_input_call_snapshots (bundle_id,role,call_id,snapshot,snapshot_hash) VALUES (:bundle_id,:role,:call_id,CAST(:snapshot AS jsonb),:snapshot_hash)"), {"bundle_id": request.inputs.id, "role": item.role, "call_id": item.call_id, "snapshot": json.dumps(item.snapshot, sort_keys=True), "snapshot_hash": item.snapshot_hash})
            for item in request.inputs.usage:
                await connection.execute(text("INSERT INTO record_learning_input_usage (bundle_id,role,usage_id,call_id,component) VALUES (:bundle_id,:role,:usage_id,:call_id,:component)"), {"bundle_id": request.inputs.id, **item.model_dump()})
            for item in request.inputs.costs:
                await connection.execute(text("INSERT INTO record_learning_input_costs (bundle_id,role,cost_id,call_id,kind) VALUES (:bundle_id,:role,:cost_id,:call_id,:kind)"), {"bundle_id": request.inputs.id, "role": item.role, "cost_id": item.id, "call_id": item.call_id, "kind": item.kind})
            await connection.execute(text("INSERT INTO record_learning_scopes (id,run_id,target_subsystem,protected_components,content_hash,created_at) VALUES (:id,:run_id,:target_subsystem,CAST(:protected_components AS jsonb),:content_hash,:created_at)"), {"id": request.scope.id, "run_id": run_id, "target_subsystem": request.scope.target_subsystem, "protected_components": json.dumps(request.scope.protected_components), "content_hash": request.scope.content_hash, "created_at": now})
            await connection.execute(
                text("""INSERT INTO record_learning_proposals
                (id,logical_id,version,run_id,input_bundle_id,scope_id,class,bottleneck,expected_effect,target_metrics,protected_metrics,confidence,sample_size,confounders,evaluation_criteria,rollback_criteria,content_hash,proposed_by,created_at)
                VALUES (:id,:logical_id,:version,:run_id,:input_bundle_id,:scope_id,:class,:bottleneck,CAST(:expected_effect AS jsonb),CAST(:target_metrics AS jsonb),CAST(:protected_metrics AS jsonb),:confidence,:sample_size,CAST(:confounders AS jsonb),CAST(:evaluation_criteria AS jsonb),CAST(:rollback_criteria AS jsonb),:content_hash,:proposed_by,:created_at)"""),
                {"id": request.id, "logical_id": request.logical_id, "version": request.version, "run_id": run_id, "input_bundle_id": request.inputs.id, "scope_id": request.scope.id, "class": request.proposal_class, "bottleneck": request.bottleneck, "expected_effect": json.dumps(request.expected_effect, sort_keys=True), "target_metrics": json.dumps([item.model_dump() for item in request.target_metrics], sort_keys=True), "protected_metrics": json.dumps([item.model_dump() for item in request.protected_metrics], sort_keys=True), "confidence": request.confidence, "sample_size": request.sample_size, "confounders": json.dumps(request.confounders), "evaluation_criteria": json.dumps(request.evaluation_criteria, sort_keys=True), "rollback_criteria": json.dumps(request.rollback_criteria, sort_keys=True), "content_hash": request.content_hash, "proposed_by": request.proposed_by, "created_at": now},
            )
            if request.candidate is not None:
                candidate = request.candidate
                await connection.execute(text("""INSERT INTO record_learning_candidate_versions
                (id,logical_id,version,proposal_id,baseline_artifact_id,baseline_experiment_id,baseline_artifact_kind,baseline_artifact_version,baseline_artifact_hash,candidate_configuration,config_diff,diff_hash,content_hash,created_at)
                VALUES (:id,:logical_id,:version,:proposal_id,:baseline_artifact_id,:baseline_experiment_id,:baseline_artifact_kind,:baseline_artifact_version,:baseline_artifact_hash,CAST(:candidate_configuration AS jsonb),CAST(:config_diff AS jsonb),:diff_hash,:content_hash,:created_at)"""), {"id": candidate.id, "logical_id": candidate.logical_id, "version": candidate.version, "proposal_id": request.id, "baseline_artifact_id": candidate.baseline_artifact.id, "baseline_experiment_id": request.experiment_id, "baseline_artifact_kind": candidate.baseline_artifact.kind, "baseline_artifact_version": candidate.baseline_artifact.version, "baseline_artifact_hash": candidate.baseline_artifact.content_hash, "candidate_configuration": json.dumps(candidate.candidate_configuration, sort_keys=True), "config_diff": json.dumps(candidate.config_diff), "diff_hash": candidate.diff_hash, "content_hash": candidate.content_hash, "created_at": now})
            command_id = await _complete(connection, command_key=command_key, experiment_id=request.experiment_id, kind="RECORD_LEARNING_PROPOSAL", request_hash=request_hash, result_type="LEARNING_PROPOSAL", result_id=request.id, now=now)
            return await self._proposal_receipt(connection, request.id, command_id)

    @safe_records
    async def record_evaluation(self, request: LearningEvaluationRequest, *, command_key: UUID) -> LearningEvaluationReceipt:
        async with self.engine.begin() as connection:
            proposal = ((await connection.execute(text("""SELECT p.id,r.experiment_id,p.input_bundle_id FROM record_learning_proposals p JOIN record_learning_runs r ON r.id=p.run_id WHERE p.id=:id"""), {"id": request.proposal_id})).mappings().one_or_none())
            if proposal is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, proposal["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(connection, command_key, "RECORD_LEARNING_EVALUATION", request_hash)
            if old:
                row = ((await connection.execute(text("SELECT id FROM record_learning_regression_assessments WHERE comparison_id=:id"), {"id": request.id})).mappings().one())
                return LearningEvaluationReceipt(command_id=old["id"], result_id=request.id, comparison_id=request.id, assessment_id=row["id"])
            now, assessment_id = self.clock(), uuid4()
            await connection.execute(text("""INSERT INTO record_learning_offline_comparisons (id,proposal_id,candidate_id,input_bundle_id,evaluator_version,evaluator_hash,baseline_hash,candidate_hash,metric_results,content_hash,created_at)
            VALUES (:id,:proposal_id,:candidate_id,:input_bundle_id,:evaluator_version,:evaluator_hash,:baseline_hash,:candidate_hash,CAST(:metric_results AS jsonb),:content_hash,:created_at)"""), {"id": request.id, "proposal_id": request.proposal_id, "candidate_id": request.candidate_id, "input_bundle_id": proposal["input_bundle_id"], "evaluator_version": request.evaluator_version, "evaluator_hash": request.evaluator_hash, "baseline_hash": request.baseline_hash, "candidate_hash": request.candidate_hash, "metric_results": json.dumps(request.metric_results, sort_keys=True), "content_hash": request.content_hash, "created_at": now})
            await connection.execute(text("INSERT INTO record_learning_regression_assessments (id,comparison_id,disposition,metric_results,rollback_satisfied,content_hash,created_at) VALUES (:id,:comparison_id,:disposition,CAST(:metric_results AS jsonb),:rollback_satisfied,:content_hash,:created_at)"), {"id": assessment_id, "comparison_id": request.id, "disposition": request.disposition, "metric_results": json.dumps(request.metric_results, sort_keys=True), "rollback_satisfied": request.rollback_satisfied, "content_hash": request.content_hash, "created_at": now})
            if request.failure_reason_codes:
                await connection.execute(text("INSERT INTO record_learning_failure_analyses (id,comparison_id,reason_codes,content_hash,created_at) VALUES (:id,:comparison_id,CAST(:reason_codes AS jsonb),:content_hash,:created_at)"), {"id": uuid4(), "comparison_id": request.id, "reason_codes": json.dumps(request.failure_reason_codes), "content_hash": request.content_hash, "created_at": now})
                await connection.execute(text("INSERT INTO record_negative_learning_records (id,proposal_id,comparison_id,classification,reason_codes,content_hash,created_at) VALUES (:id,:proposal_id,:comparison_id,:classification,CAST(:reason_codes AS jsonb),:content_hash,:created_at)"), {"id": uuid4(), "proposal_id": request.proposal_id, "comparison_id": request.id, "classification": request.negative_classification, "reason_codes": json.dumps(request.failure_reason_codes), "content_hash": request.content_hash, "created_at": now})
            command_id = await _complete(connection, command_key=command_key, experiment_id=proposal["experiment_id"], kind="RECORD_LEARNING_EVALUATION", request_hash=request_hash, result_type="LEARNING_COMPARISON", result_id=request.id, now=now)
            return LearningEvaluationReceipt(command_id=command_id, result_id=request.id, comparison_id=request.id, assessment_id=assessment_id)

    @safe_records
    async def record_engineering_capability_request(self, request: EngineeringCapabilityRequestInput, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            row = ((await connection.execute(text("""SELECT p.run_id,r.experiment_id FROM record_learning_proposals p JOIN record_learning_runs r ON r.id=p.run_id WHERE p.id=:id"""), {"id": request.proposal_id})).mappings().one_or_none())
            if row is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, row["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(connection, command_key, "RECORD_ENGINEERING_CAPABILITY_REQUEST", request_hash)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            now, gap_id = self.clock(), uuid4()
            await connection.execute(text("INSERT INTO record_capability_gaps (id,run_id,proposal_id,description,content_hash,created_at) VALUES (:id,:run_id,:proposal_id,:description,:content_hash,:created_at)"), {"id": gap_id, "run_id": row["run_id"], "proposal_id": request.proposal_id, "description": request.description, "content_hash": request.content_hash, "created_at": now})
            await connection.execute(text("INSERT INTO record_engineering_capability_requests (id,gap_id,proposal_id,description,boundary,expected_benefit,risk,content_hash,created_at) VALUES (:id,:gap_id,:proposal_id,:description,:boundary,:expected_benefit,:risk,:content_hash,:created_at)"), {"id": request.id, "gap_id": gap_id, "proposal_id": request.proposal_id, **request.model_dump(exclude={"id", "proposal_id"}), "created_at": now})
            command_id = await _complete(connection, command_key=command_key, experiment_id=row["experiment_id"], kind="RECORD_ENGINEERING_CAPABILITY_REQUEST", request_hash=request_hash, result_type="ENGINEERING_CAPABILITY_REQUEST", result_id=request.id, now=now)
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_review_control(self, request: LearningReviewControlRequest, *, command_key: UUID) -> CommandReceipt:
        async with self.engine.begin() as connection:
            row = ((await connection.execute(text("SELECT experiment_id FROM record_learning_runs WHERE id=:id"), {"id": request.run_id})).mappings().one_or_none())
            if row is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, row["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(connection, command_key, "RECORD_LEARNING_REVIEW_CONTROL", request_hash)
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            now = self.clock()
            await connection.execute(text("INSERT INTO record_learning_review_controls (id,run_id,kind,baseline_candidate_id,operator_id,content_hash,created_at) VALUES (:id,:run_id,:kind,:baseline_candidate_id,:operator_id,:content_hash,:created_at)"), {**request.model_dump(), "created_at": now})
            command_id = await _complete(connection, command_key=command_key, experiment_id=row["experiment_id"], kind="RECORD_LEARNING_REVIEW_CONTROL", request_hash=request_hash, result_type="LEARNING_REVIEW_CONTROL", result_id=request.id, now=now)
            return CommandReceipt(command_id=command_id, result_id=request.id)
