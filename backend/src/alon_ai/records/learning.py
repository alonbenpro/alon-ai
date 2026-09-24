"""Atomic commands for the immutable, offline-only learning ledger."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.accounting.repository import lock_experiment
from alon_ai.records.learning_models import (
    EngineeringCapabilityRequestInput,
    FreezeExperimentStrategyRequest,
    GlobalStrategyPackageRequest,
    LearningEvaluationReceipt,
    LearningEvaluationRequest,
    LearningProposalReceipt,
    LearningProposalRequest,
    LearningReviewControlRequest,
    LiveRegressionAssessmentRequest,
    LiveStrategyObservationRequest,
    PromotionDecisionRequest,
    RollbackDecisionRequest,
    StrategyControlRequest,
    StrategyExecutionBindingRequest,
    StrategyPackageReceipt,
)
from alon_ai.records.models import CommandReceipt, ProductRecordsDenied
from alon_ai.records.repository import _complete, _existing, _request_hash, safe_records


def _canonical_hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


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

    async def _insert_strategy_package(self, connection, request, now):
        member_hashes: list[tuple[str, UUID, str]] = []
        for member in request.members:
            configuration = member.configuration.model_dump(mode="json")
            configuration_hash = _canonical_hash(
                {
                    "prompt": member.prompt.model_dump(mode="json"),
                    "few_shot": member.few_shot.model_dump(mode="json")
                    if member.few_shot
                    else None,
                    "model_identifier": member.model_identifier,
                    "reasoning_effort": member.reasoning_effort,
                    "budget_policy_version": member.budget_policy_version,
                    "max_tool_calls": member.max_tool_calls,
                    "max_searches": member.max_searches,
                    "max_pages": member.max_pages,
                    "configuration": configuration,
                }
            )
            few_shot = member.few_shot
            prompt_experiment_id = await connection.scalar(
                text("SELECT experiment_id FROM record_artifacts WHERE id=:id"),
                {"id": member.prompt.id},
            )
            few_shot_experiment_id = (
                await connection.scalar(
                    text("SELECT experiment_id FROM record_artifacts WHERE id=:id"),
                    {"id": few_shot.id},
                )
                if few_shot
                else None
            )
            await connection.execute(
                text("""INSERT INTO record_strategy_agent_versions
                (id,logical_id,version,supersedes_id,origin_candidate_id,role,
                 prompt_artifact_id,prompt_experiment_id,prompt_kind,prompt_version,prompt_hash,
                 few_shot_artifact_id,few_shot_experiment_id,few_shot_kind,few_shot_version,few_shot_hash,
                 model_identifier,reasoning_effort,budget_policy_version,max_tool_calls,max_searches,max_pages,
                 configuration,configuration_hash,created_at)
                VALUES (:id,:logical_id,:version,:supersedes_id,:origin_candidate_id,:role,
                 :prompt_artifact_id,:prompt_experiment_id,:prompt_kind,:prompt_version,:prompt_hash,
                 :few_shot_artifact_id,:few_shot_experiment_id,:few_shot_kind,:few_shot_version,:few_shot_hash,
                 :model_identifier,:reasoning_effort,:budget_policy_version,:max_tool_calls,:max_searches,:max_pages,
                 CAST(:configuration AS jsonb),:configuration_hash,:created_at)"""),
                {
                    "id": member.id,
                    "logical_id": member.logical_id,
                    "version": member.version,
                    "supersedes_id": member.supersedes_id,
                    "origin_candidate_id": member.origin_candidate_id,
                    "role": member.configuration.role,
                    "prompt_artifact_id": member.prompt.id,
                    "prompt_experiment_id": prompt_experiment_id,
                    "prompt_kind": member.prompt.kind,
                    "prompt_version": member.prompt.version,
                    "prompt_hash": member.prompt.content_hash,
                    "few_shot_artifact_id": few_shot.id if few_shot else None,
                    "few_shot_experiment_id": few_shot_experiment_id,
                    "few_shot_kind": few_shot.kind if few_shot else None,
                    "few_shot_version": few_shot.version if few_shot else None,
                    "few_shot_hash": few_shot.content_hash if few_shot else None,
                    "model_identifier": member.model_identifier,
                    "reasoning_effort": member.reasoning_effort,
                    "budget_policy_version": member.budget_policy_version,
                    "max_tool_calls": member.max_tool_calls,
                    "max_searches": member.max_searches,
                    "max_pages": member.max_pages,
                    "configuration": json.dumps(configuration, sort_keys=True),
                    "configuration_hash": configuration_hash,
                    "created_at": now,
                },
            )
            member_hashes.append(
                (member.configuration.role, member.id, configuration_hash)
            )
        package_hash = _canonical_hash(
            {
                "logical_id": request.logical_id,
                "version": request.version,
                "supersedes_id": request.supersedes_id,
                "members": sorted(member_hashes),
            }
        )
        await connection.execute(
            text("""INSERT INTO record_global_strategy_packages
            (id,logical_id,version,supersedes_id,package_hash,created_by,created_at)
            VALUES (:id,:logical_id,:version,:supersedes_id,:package_hash,:created_by,:created_at)"""),
            {
                "id": request.id,
                "logical_id": request.logical_id,
                "version": request.version,
                "supersedes_id": request.supersedes_id,
                "package_hash": package_hash,
                "created_by": request.created_by,
                "created_at": now,
            },
        )
        for role, agent_version_id, configuration_hash in member_hashes:
            await connection.execute(
                text(
                    "INSERT INTO record_strategy_package_members (package_id,role,agent_version_id,configuration_hash) VALUES (:package_id,:role,:agent_version_id,:configuration_hash)"
                ),
                {
                    "package_id": request.id,
                    "role": role,
                    "agent_version_id": agent_version_id,
                    "configuration_hash": configuration_hash,
                },
            )
        await connection.execute(
            text(
                "INSERT INTO record_strategy_package_seals (package_id,member_count,member_set_hash,sealed_at) VALUES (:package_id,4,:member_set_hash,:sealed_at)"
            ),
            {
                "package_id": request.id,
                "member_set_hash": _canonical_hash(sorted(member_hashes)),
                "sealed_at": now,
            },
        )
        return package_hash

    async def _insert_live_input_bundle(
        self, connection, *, request: LiveStrategyObservationRequest, binding, now
    ) -> None:
        inputs = request.inputs
        run_id = uuid4()
        run_hash = _canonical_hash(
            {
                "execution_binding_id": request.execution_binding_id,
                "input_bundle_id": inputs.id,
            }
        )
        await connection.execute(
            text("""INSERT INTO record_learning_runs
            (id,experiment_id,workflow_id,agent_id,agent_version_hash,evaluator_version,
             evaluator_hash,content_hash,created_by,created_at)
            VALUES (:id,:experiment_id,:workflow_id,:agent_id,:agent_version_hash,
             'LIVE_OBSERVATION_V1',:evaluator_hash,:content_hash,:created_by,:created_at)"""),
            {
                "id": run_id,
                "experiment_id": binding["experiment_id"],
                "workflow_id": binding["workflow_id"],
                "agent_id": binding["agent_id"],
                "agent_version_hash": binding["configuration_hash"],
                "evaluator_hash": run_hash,
                "content_hash": run_hash,
                "created_by": request.recorded_by,
                "created_at": now,
            },
        )

        await connection.execute(
            text("""INSERT INTO record_learning_input_bundles
            (id,run_id,experiment_id,content_hash,created_at)
            VALUES (:id,:run_id,:experiment_id,:content_hash,:created_at)"""),
            {
                "id": inputs.id,
                "run_id": run_id,
                "experiment_id": binding["experiment_id"],
                "content_hash": inputs.content_hash,
                "created_at": now,
            },
        )

        for item in inputs.artifacts:
            await connection.execute(
                text("""INSERT INTO record_learning_input_artifacts
                (bundle_id,role,artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash)
                VALUES (:bundle_id,:role,:artifact_id,:experiment_id,:artifact_kind,:artifact_version,:artifact_hash)"""),
                {
                    "bundle_id": inputs.id,
                    "role": item.role,
                    "artifact_id": item.id,
                    "experiment_id": binding["experiment_id"],
                    "artifact_kind": item.kind,
                    "artifact_version": item.version,
                    "artifact_hash": item.content_hash,
                },
            )
        for item in inputs.evidence:
            await connection.execute(
                text("""INSERT INTO record_learning_input_evidence
                (bundle_id,role,evidence_id,call_id)
                VALUES (:bundle_id,:role,:evidence_id,:call_id)"""),
                {"bundle_id": inputs.id, **item.model_dump()},
            )
        for item in inputs.call_snapshots:
            await connection.execute(
                text("""INSERT INTO record_learning_input_call_snapshots
                (bundle_id,role,call_id,snapshot,snapshot_hash)
                VALUES (:bundle_id,:role,:call_id,CAST(:snapshot AS jsonb),:snapshot_hash)"""),
                {
                    "bundle_id": inputs.id,
                    "role": item.role,
                    "call_id": item.call_id,
                    "snapshot": json.dumps(item.snapshot, sort_keys=True),
                    "snapshot_hash": item.snapshot_hash,
                },
            )
        for item in inputs.usage:
            await connection.execute(
                text("""INSERT INTO record_learning_input_usage
                (bundle_id,role,usage_id,call_id,component)
                VALUES (:bundle_id,:role,:usage_id,:call_id,:component)"""),
                {"bundle_id": inputs.id, **item.model_dump()},
            )
        for item in inputs.costs:
            await connection.execute(
                text("""INSERT INTO record_learning_input_costs
                (bundle_id,role,cost_id,call_id,kind)
                VALUES (:bundle_id,:role,:cost_id,:call_id,:kind)"""),
                {
                    "bundle_id": inputs.id,
                    "role": item.role,
                    "cost_id": item.id,
                    "call_id": item.call_id,
                    "kind": item.kind,
                },
            )
        reference_count = sum(
            len(items)
            for items in (
                inputs.artifacts,
                inputs.evidence,
                inputs.call_snapshots,
                inputs.usage,
                inputs.costs,
            )
        )
        await connection.execute(
            text("""INSERT INTO record_learning_input_bundle_seals
            (bundle_id,reference_count,reference_set_hash,sealed_at)
            VALUES (:bundle_id,:reference_count,:reference_set_hash,:sealed_at)"""),
            {
                "bundle_id": inputs.id,
                "reference_count": reference_count,
                "reference_set_hash": inputs.content_hash,
                "sealed_at": now,
            },
        )

    async def _insert_registry_event(
        self,
        connection,
        *,
        event_id: UUID,
        kind: str,
        operator_id: UUID,
        package_id: UUID | None,
        rollback_decision_id: UUID | None,
        reason_codes: tuple[str, ...],
        content_hash: str,
        now: datetime,
    ) -> None:
        await connection.execute(
            text("SELECT id FROM record_strategy_registry WHERE id=1 FOR UPDATE")
        )
        prior_event_id = await connection.scalar(
            text("""SELECT id FROM record_learning_review_controls
            WHERE registry_scope ORDER BY event_ordinal DESC LIMIT 1""")
        )
        await connection.execute(
            text("""INSERT INTO record_learning_review_controls
            (id,run_id,kind,baseline_candidate_id,operator_id,content_hash,created_at,
             registry_scope,package_id,rollback_decision_id,reason_codes,prior_event_id)
            VALUES (:id,NULL,:kind,NULL,:operator_id,:content_hash,:created_at,true,
             :package_id,:rollback_decision_id,CAST(:reason_codes AS jsonb),:prior_event_id)"""),
            {
                "id": event_id,
                "kind": kind,
                "operator_id": operator_id,
                "content_hash": content_hash,
                "created_at": now,
                "package_id": package_id,
                "rollback_decision_id": rollback_decision_id,
                "reason_codes": json.dumps(reason_codes),
                "prior_event_id": prior_event_id,
            },
        )

    @safe_records
    async def record_strategy_package(
        self, request: GlobalStrategyPackageRequest, *, command_key: UUID
    ) -> StrategyPackageReceipt:
        request_hash = _request_hash(request=request)
        async with self.engine.begin() as connection:
            await connection.execute(
                text("SELECT id FROM record_strategy_registry WHERE id=1 FOR UPDATE")
            )
            old = await _existing(
                connection, command_key, "RECORD_STRATEGY_PACKAGE", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            text(
                                "SELECT version,package_hash FROM record_global_strategy_packages WHERE id=:id"
                            ),
                            {"id": old["result_id"]},
                        )
                    )
                    .mappings()
                    .one()
                )
                return StrategyPackageReceipt(
                    command_id=old["id"],
                    result_id=old["result_id"],
                    package_id=old["result_id"],
                    package_version=row["version"],
                    package_hash=row["package_hash"],
                )
            if request.version != 1 or request.supersedes_id is not None:
                raise ProductRecordsDenied("PROMOTION_REQUIRED")
            now = self.clock()
            package_hash = await self._insert_strategy_package(connection, request, now)
            prior_event_id = await connection.scalar(
                text(
                    "SELECT id FROM record_learning_review_controls WHERE registry_scope ORDER BY event_ordinal DESC LIMIT 1"
                )
            )
            await connection.execute(
                text("""INSERT INTO record_learning_review_controls
                (id,run_id,kind,baseline_candidate_id,operator_id,content_hash,created_at,registry_scope,package_id,reason_codes,prior_event_id)
                VALUES (:id,NULL,'BOOTSTRAP_PACKAGE',NULL,:operator_id,:content_hash,:created_at,true,:package_id,CAST(:reason_codes AS jsonb),:prior_event_id)"""),
                {
                    "id": uuid4(),
                    "operator_id": request.created_by,
                    "content_hash": package_hash,
                    "created_at": now,
                    "package_id": request.id,
                    "reason_codes": json.dumps(["BOOTSTRAP_PACKAGE"]),
                    "prior_event_id": prior_event_id,
                },
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=None,
                kind="RECORD_STRATEGY_PACKAGE",
                request_hash=request_hash,
                result_type="GLOBAL_STRATEGY_PACKAGE",
                result_id=request.id,
                now=now,
            )
            return StrategyPackageReceipt(
                command_id=command_id,
                result_id=request.id,
                package_id=request.id,
                package_version=request.version,
                package_hash=package_hash,
            )

    @safe_records
    async def freeze_experiment_strategy(
        self, request: FreezeExperimentStrategyRequest, *, command_key: UUID
    ) -> CommandReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, request.experiment_id)
            await connection.execute(
                text("SELECT id FROM record_strategy_registry WHERE id=1 FOR UPDATE")
            )
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "FREEZE_EXPERIMENT_STRATEGY", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            if await connection.scalar(
                text("SELECT EXISTS(SELECT 1 FROM gov_calls WHERE experiment_id=:id)"),
                {"id": request.experiment_id},
            ):
                raise ProductRecordsDenied("STRATEGY_MUST_FREEZE_BEFORE_EXECUTION")
            control_rows = (
                (
                    await connection.execute(
                        text("""SELECT DISTINCT ON (family) family,kind,package_id FROM (
                    SELECT CASE WHEN kind IN ('PAUSE','RESUME') THEN 'PAUSE'
                                WHEN kind IN ('PIN','UNPIN') THEN 'PIN'
                                ELSE 'SELECTION' END AS family,
                           kind,package_id,event_ordinal
                    FROM record_learning_review_controls WHERE registry_scope
                    ) events ORDER BY family,event_ordinal DESC""")
                    )
                )
                .mappings()
                .all()
            )
            state = {row["family"]: row for row in control_rows}
            if state.get("PAUSE", {}).get("kind") == "PAUSE":
                raise ProductRecordsDenied("STRATEGY_REGISTRY_PAUSED")
            expected_package = (
                state["PIN"]["package_id"]
                if state.get("PIN", {}).get("kind") == "PIN"
                else state.get("SELECTION", {}).get("package_id")
            )
            if expected_package != request.package_id:
                raise ProductRecordsDenied("STRATEGY_PACKAGE_NOT_SELECTED")
            package = (
                (
                    await connection.execute(
                        text("""SELECT p.id,p.version,p.package_hash FROM record_global_strategy_packages p
                        JOIN record_strategy_package_seals s ON s.package_id=p.id WHERE p.id=:id"""),
                        {"id": request.package_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if package is None:
                raise ProductRecordsDenied("UNSEALED_STRATEGY_PACKAGE")
            now = self.clock()
            content_hash = _canonical_hash(request.model_dump(mode="json"))
            await connection.execute(
                text("""INSERT INTO record_experiment_strategy_bindings
                (experiment_id,package_id,package_version,package_hash,frozen_by,content_hash,frozen_at)
                VALUES (:experiment_id,:package_id,:package_version,:package_hash,:frozen_by,:content_hash,:frozen_at)"""),
                {
                    **request.model_dump(),
                    "package_version": package["version"],
                    "package_hash": package["package_hash"],
                    "content_hash": content_hash,
                    "frozen_at": now,
                },
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=request.experiment_id,
                kind="FREEZE_EXPERIMENT_STRATEGY",
                request_hash=request_hash,
                result_type="EXPERIMENT_STRATEGY_BINDING",
                result_id=request.experiment_id,
                now=now,
            )
            return CommandReceipt(
                command_id=command_id, result_id=request.experiment_id
            )

    @safe_records
    async def bind_strategy_execution(
        self, request: StrategyExecutionBindingRequest, *, command_key: UUID
    ) -> CommandReceipt:
        async with self.engine.begin() as connection:
            await lock_experiment(connection, request.experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "BIND_STRATEGY_EXECUTION", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            configuration_hash = await connection.scalar(
                text(
                    "SELECT configuration_hash FROM record_strategy_agent_versions WHERE id=:id AND role=:role"
                ),
                {"id": request.agent_version_id, "role": request.role},
            )
            if configuration_hash is None:
                raise ProductRecordsDenied("STRATEGY_EXECUTION_LINEAGE")
            now = self.clock()
            await connection.execute(
                text("""INSERT INTO record_strategy_execution_bindings
                (id,experiment_id,workflow_id,agent_id,operation_id,package_id,role,agent_version_id,configuration_hash,
                 model_config_id,model_config_workflow_id,model_config_version,content_hash,created_at)
                VALUES (:id,:experiment_id,:workflow_id,:agent_id,:operation_id,:package_id,:role,:agent_version_id,:configuration_hash,
                 :model_config_id,:model_config_workflow_id,:model_config_version,:content_hash,:created_at)"""),
                {
                    **request.model_dump(),
                    "configuration_hash": configuration_hash,
                    "content_hash": _canonical_hash(request.model_dump(mode="json")),
                    "created_at": now,
                },
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=request.experiment_id,
                kind="BIND_STRATEGY_EXECUTION",
                request_hash=request_hash,
                result_type="STRATEGY_EXECUTION_BINDING",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

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
                        request.model_dump(
                            include={"workflow_id", "experiment_id", "agent_id"}
                        ),
                    )
                )
                .mappings()
                .one_or_none()
            )
            if root is None:
                raise ProductRecordsDenied("LEARNING_LINEAGE_MISMATCH")
            await lock_experiment(connection, request.experiment_id)
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_LEARNING_PROPOSAL", request_hash
            )
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
                {
                    "id": request.inputs.id,
                    "run_id": run_id,
                    "experiment_id": request.experiment_id,
                    "content_hash": request.inputs.content_hash,
                    "created_at": now,
                },
            )
            for item in request.inputs.artifacts:
                await connection.execute(
                    text("""INSERT INTO record_learning_input_artifacts
                    (bundle_id,role,artifact_id,experiment_id,artifact_kind,artifact_version,artifact_hash)
                    VALUES (:bundle_id,:role,:artifact_id,:experiment_id,:artifact_kind,:artifact_version,:artifact_hash)"""),
                    {
                        "bundle_id": request.inputs.id,
                        "role": item.role,
                        "artifact_id": item.id,
                        "experiment_id": request.experiment_id,
                        "artifact_kind": item.kind,
                        "artifact_version": item.version,
                        "artifact_hash": item.content_hash,
                    },
                )
            for item in request.inputs.evidence:
                await connection.execute(
                    text(
                        "INSERT INTO record_learning_input_evidence (bundle_id,role,evidence_id,call_id) VALUES (:bundle_id,:role,:evidence_id,:call_id)"
                    ),
                    {"bundle_id": request.inputs.id, **item.model_dump()},
                )
            for item in request.inputs.call_snapshots:
                await connection.execute(
                    text(
                        "INSERT INTO record_learning_input_call_snapshots (bundle_id,role,call_id,snapshot,snapshot_hash) VALUES (:bundle_id,:role,:call_id,CAST(:snapshot AS jsonb),:snapshot_hash)"
                    ),
                    {
                        "bundle_id": request.inputs.id,
                        "role": item.role,
                        "call_id": item.call_id,
                        "snapshot": json.dumps(item.snapshot, sort_keys=True),
                        "snapshot_hash": item.snapshot_hash,
                    },
                )
            for item in request.inputs.usage:
                await connection.execute(
                    text(
                        "INSERT INTO record_learning_input_usage (bundle_id,role,usage_id,call_id,component) VALUES (:bundle_id,:role,:usage_id,:call_id,:component)"
                    ),
                    {"bundle_id": request.inputs.id, **item.model_dump()},
                )
            for item in request.inputs.costs:
                await connection.execute(
                    text(
                        "INSERT INTO record_learning_input_costs (bundle_id,role,cost_id,call_id,kind) VALUES (:bundle_id,:role,:cost_id,:call_id,:kind)"
                    ),
                    {
                        "bundle_id": request.inputs.id,
                        "role": item.role,
                        "cost_id": item.id,
                        "call_id": item.call_id,
                        "kind": item.kind,
                    },
                )
            reference_count = (
                len(request.inputs.artifacts)
                + len(request.inputs.evidence)
                + len(request.inputs.call_snapshots)
                + len(request.inputs.usage)
                + len(request.inputs.costs)
            )
            await connection.execute(
                text("""INSERT INTO record_learning_input_bundle_seals
                (bundle_id,reference_count,reference_set_hash,sealed_at)
                VALUES (:bundle_id,:reference_count,:reference_set_hash,:sealed_at)"""),
                {
                    "bundle_id": request.inputs.id,
                    "reference_count": reference_count,
                    "reference_set_hash": request.inputs.content_hash,
                    "sealed_at": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO record_learning_scopes (id,run_id,target_subsystem,protected_components,content_hash,created_at) VALUES (:id,:run_id,:target_subsystem,CAST(:protected_components AS jsonb),:content_hash,:created_at)"
                ),
                {
                    "id": request.scope.id,
                    "run_id": run_id,
                    "target_subsystem": request.scope.target_subsystem,
                    "protected_components": json.dumps(
                        request.scope.protected_components
                    ),
                    "content_hash": request.scope.content_hash,
                    "created_at": now,
                },
            )
            await connection.execute(
                text("""INSERT INTO record_learning_proposals
                (id,logical_id,version,run_id,input_bundle_id,scope_id,class,bottleneck,expected_effect,target_metrics,protected_metrics,confidence,sample_size,confounders,evaluation_criteria,rollback_criteria,content_hash,proposed_by,created_at)
                VALUES (:id,:logical_id,:version,:run_id,:input_bundle_id,:scope_id,:class,:bottleneck,CAST(:expected_effect AS jsonb),CAST(:target_metrics AS jsonb),CAST(:protected_metrics AS jsonb),:confidence,:sample_size,CAST(:confounders AS jsonb),CAST(:evaluation_criteria AS jsonb),CAST(:rollback_criteria AS jsonb),:content_hash,:proposed_by,:created_at)"""),
                {
                    "id": request.id,
                    "logical_id": request.logical_id,
                    "version": request.version,
                    "run_id": run_id,
                    "input_bundle_id": request.inputs.id,
                    "scope_id": request.scope.id,
                    "class": request.proposal_class,
                    "bottleneck": request.bottleneck,
                    "expected_effect": json.dumps(
                        request.expected_effect, sort_keys=True
                    ),
                    "target_metrics": json.dumps(
                        [item.model_dump() for item in request.target_metrics],
                        sort_keys=True,
                    ),
                    "protected_metrics": json.dumps(
                        [item.model_dump() for item in request.protected_metrics],
                        sort_keys=True,
                    ),
                    "confidence": request.confidence,
                    "sample_size": request.sample_size,
                    "confounders": json.dumps(request.confounders),
                    "evaluation_criteria": json.dumps(
                        request.evaluation_criteria, sort_keys=True
                    ),
                    "rollback_criteria": json.dumps(
                        request.rollback_criteria, sort_keys=True
                    ),
                    "content_hash": request.content_hash,
                    "proposed_by": request.proposed_by,
                    "created_at": now,
                },
            )
            if request.candidate is not None:
                candidate = request.candidate
                await connection.execute(
                    text("""INSERT INTO record_learning_candidate_versions
                (id,logical_id,version,proposal_id,baseline_artifact_id,baseline_experiment_id,baseline_artifact_kind,baseline_artifact_version,baseline_artifact_hash,candidate_configuration,config_diff,diff_hash,content_hash,created_at)
                VALUES (:id,:logical_id,:version,:proposal_id,:baseline_artifact_id,:baseline_experiment_id,:baseline_artifact_kind,:baseline_artifact_version,:baseline_artifact_hash,CAST(:candidate_configuration AS jsonb),CAST(:config_diff AS jsonb),:diff_hash,:content_hash,:created_at)"""),
                    {
                        "id": candidate.id,
                        "logical_id": candidate.logical_id,
                        "version": candidate.version,
                        "proposal_id": request.id,
                        "baseline_artifact_id": candidate.baseline_artifact.id,
                        "baseline_experiment_id": request.experiment_id,
                        "baseline_artifact_kind": candidate.baseline_artifact.kind,
                        "baseline_artifact_version": candidate.baseline_artifact.version,
                        "baseline_artifact_hash": candidate.baseline_artifact.content_hash,
                        "candidate_configuration": json.dumps(
                            candidate.candidate_configuration, sort_keys=True
                        ),
                        "config_diff": json.dumps(candidate.config_diff),
                        "diff_hash": candidate.diff_hash,
                        "content_hash": candidate.content_hash,
                        "created_at": now,
                    },
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=request.experiment_id,
                kind="RECORD_LEARNING_PROPOSAL",
                request_hash=request_hash,
                result_type="LEARNING_PROPOSAL",
                result_id=request.id,
                now=now,
            )
            return await self._proposal_receipt(connection, request.id, command_id)

    @safe_records
    async def record_evaluation(
        self, request: LearningEvaluationRequest, *, command_key: UUID
    ) -> LearningEvaluationReceipt:
        async with self.engine.begin() as connection:
            proposal = (
                (
                    await connection.execute(
                        text(
                            """SELECT p.id,r.experiment_id,p.input_bundle_id FROM record_learning_proposals p JOIN record_learning_runs r ON r.id=p.run_id WHERE p.id=:id"""
                        ),
                        {"id": request.proposal_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if proposal is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, proposal["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_LEARNING_EVALUATION", request_hash
            )
            if old:
                row = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id FROM record_learning_regression_assessments WHERE comparison_id=:id"
                            ),
                            {"id": request.id},
                        )
                    )
                    .mappings()
                    .one()
                )
                return LearningEvaluationReceipt(
                    command_id=old["id"],
                    result_id=request.id,
                    comparison_id=request.id,
                    assessment_id=row["id"],
                )
            now, assessment_id = self.clock(), uuid4()
            await connection.execute(
                text("""INSERT INTO record_learning_offline_comparisons (id,proposal_id,candidate_id,input_bundle_id,evaluator_version,evaluator_hash,baseline_hash,candidate_hash,metric_results,content_hash,created_at)
            VALUES (:id,:proposal_id,:candidate_id,:input_bundle_id,:evaluator_version,:evaluator_hash,:baseline_hash,:candidate_hash,CAST(:metric_results AS jsonb),:content_hash,:created_at)"""),
                {
                    "id": request.id,
                    "proposal_id": request.proposal_id,
                    "candidate_id": request.candidate_id,
                    "input_bundle_id": proposal["input_bundle_id"],
                    "evaluator_version": request.evaluator_version,
                    "evaluator_hash": request.evaluator_hash,
                    "baseline_hash": request.baseline_hash,
                    "candidate_hash": request.candidate_hash,
                    "metric_results": json.dumps(
                        request.metric_results, sort_keys=True
                    ),
                    "content_hash": request.content_hash,
                    "created_at": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO record_learning_regression_assessments (id,comparison_id,disposition,metric_results,rollback_satisfied,content_hash,created_at) VALUES (:id,:comparison_id,:disposition,CAST(:metric_results AS jsonb),:rollback_satisfied,:content_hash,:created_at)"
                ),
                {
                    "id": assessment_id,
                    "comparison_id": request.id,
                    "disposition": request.disposition,
                    "metric_results": json.dumps(
                        request.metric_results, sort_keys=True
                    ),
                    "rollback_satisfied": request.rollback_satisfied,
                    "content_hash": request.content_hash,
                    "created_at": now,
                },
            )
            if request.failure_reason_codes:
                await connection.execute(
                    text(
                        "INSERT INTO record_learning_failure_analyses (id,comparison_id,reason_codes,content_hash,created_at) VALUES (:id,:comparison_id,CAST(:reason_codes AS jsonb),:content_hash,:created_at)"
                    ),
                    {
                        "id": uuid4(),
                        "comparison_id": request.id,
                        "reason_codes": json.dumps(request.failure_reason_codes),
                        "content_hash": request.content_hash,
                        "created_at": now,
                    },
                )
                await connection.execute(
                    text(
                        "INSERT INTO record_negative_learning_records (id,proposal_id,comparison_id,classification,reason_codes,content_hash,created_at) VALUES (:id,:proposal_id,:comparison_id,:classification,CAST(:reason_codes AS jsonb),:content_hash,:created_at)"
                    ),
                    {
                        "id": uuid4(),
                        "proposal_id": request.proposal_id,
                        "comparison_id": request.id,
                        "classification": request.negative_classification,
                        "reason_codes": json.dumps(request.failure_reason_codes),
                        "content_hash": request.content_hash,
                        "created_at": now,
                    },
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=proposal["experiment_id"],
                kind="RECORD_LEARNING_EVALUATION",
                request_hash=request_hash,
                result_type="LEARNING_COMPARISON",
                result_id=request.id,
                now=now,
            )
            return LearningEvaluationReceipt(
                command_id=command_id,
                result_id=request.id,
                comparison_id=request.id,
                assessment_id=assessment_id,
            )

    @safe_records
    async def record_engineering_capability_request(
        self, request: EngineeringCapabilityRequestInput, *, command_key: UUID
    ) -> CommandReceipt:
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            """SELECT p.run_id,r.experiment_id FROM record_learning_proposals p JOIN record_learning_runs r ON r.id=p.run_id WHERE p.id=:id"""
                        ),
                        {"id": request.proposal_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, row["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection,
                command_key,
                "RECORD_ENGINEERING_CAPABILITY_REQUEST",
                request_hash,
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            now, gap_id = self.clock(), uuid4()
            await connection.execute(
                text(
                    "INSERT INTO record_capability_gaps (id,run_id,proposal_id,description,content_hash,created_at) VALUES (:id,:run_id,:proposal_id,:description,:content_hash,:created_at)"
                ),
                {
                    "id": gap_id,
                    "run_id": row["run_id"],
                    "proposal_id": request.proposal_id,
                    "description": request.description,
                    "content_hash": request.content_hash,
                    "created_at": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO record_engineering_capability_requests (id,gap_id,proposal_id,description,boundary,expected_benefit,risk,content_hash,created_at) VALUES (:id,:gap_id,:proposal_id,:description,:boundary,:expected_benefit,:risk,:content_hash,:created_at)"
                ),
                {
                    "id": request.id,
                    "gap_id": gap_id,
                    "proposal_id": request.proposal_id,
                    **request.model_dump(exclude={"id", "proposal_id"}),
                    "created_at": now,
                },
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=row["experiment_id"],
                kind="RECORD_ENGINEERING_CAPABILITY_REQUEST",
                request_hash=request_hash,
                result_type="ENGINEERING_CAPABILITY_REQUEST",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_review_control(
        self, request: LearningReviewControlRequest, *, command_key: UUID
    ) -> CommandReceipt:
        async with self.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT experiment_id FROM record_learning_runs WHERE id=:id"
                        ),
                        {"id": request.run_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise ProductRecordsDenied("MISSING_REFERENCE")
            await lock_experiment(connection, row["experiment_id"])
            request_hash = _request_hash(request=request)
            old = await _existing(
                connection, command_key, "RECORD_LEARNING_REVIEW_CONTROL", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            now = self.clock()
            await connection.execute(
                text(
                    "INSERT INTO record_learning_review_controls (id,run_id,kind,baseline_candidate_id,operator_id,content_hash,created_at) VALUES (:id,:run_id,:kind,:baseline_candidate_id,:operator_id,:content_hash,:created_at)"
                ),
                {**request.model_dump(), "created_at": now},
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=row["experiment_id"],
                kind="RECORD_LEARNING_REVIEW_CONTROL",
                request_hash=request_hash,
                result_type="LEARNING_REVIEW_CONTROL",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_promotion(
        self, request: PromotionDecisionRequest, *, command_key: UUID
    ) -> CommandReceipt:
        request_hash = _request_hash(request=request)
        async with self.engine.begin() as connection:
            await connection.execute(
                text("SELECT id FROM record_strategy_registry WHERE id=1 FOR UPDATE")
            )
            old = await _existing(
                connection, command_key, "RECORD_STRATEGY_PROMOTION", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            if await connection.scalar(
                text("""SELECT kind='PAUSE' FROM record_learning_review_controls
                WHERE registry_scope AND kind IN ('PAUSE','RESUME')
                ORDER BY event_ordinal DESC LIMIT 1""")
            ):
                raise ProductRecordsDenied("STRATEGY_REGISTRY_PAUSED")
            evidence = (
                (
                    await connection.execute(
                        text("""SELECT c.candidate_configuration,c.baseline_artifact_id,
                               c.baseline_artifact_kind,c.baseline_artifact_version,
                               c.baseline_artifact_hash,a.disposition
                        FROM record_learning_offline_comparisons o
                        JOIN record_learning_regression_assessments a ON a.comparison_id=o.id
                        JOIN record_learning_candidate_versions c ON c.id=o.candidate_id
                        WHERE o.id=:comparison_id AND a.id=:assessment_id
                          AND o.proposal_id=:proposal_id AND o.candidate_id=:candidate_id"""),
                        request.model_dump(
                            include={
                                "comparison_id",
                                "assessment_id",
                                "proposal_id",
                                "candidate_id",
                            }
                        ),
                    )
                )
                .mappings()
                .one_or_none()
            )
            if evidence is None or evidence["disposition"] != "PASS":
                raise ProductRecordsDenied("PROMOTION_EVIDENCE_MISMATCH")
            now = self.clock()
            promoted_package_id = None
            if request.package is not None:
                package = request.package
                if package.supersedes_id != request.baseline_package_id:
                    raise ProductRecordsDenied("PROMOTION_LINEAGE_MISMATCH")
                origins = [
                    member
                    for member in package.members
                    if member.origin_candidate_id == request.candidate_id
                ]
                if (
                    len(origins) != 1
                    or origins[0].configuration.model_dump(
                        mode="json", exclude={"schema_version"}
                    )
                    != evidence["candidate_configuration"]
                ):
                    raise ProductRecordsDenied("PROMOTION_CANDIDATE_MISMATCH")
                if any(
                    member.origin_candidate_id not in {None, request.candidate_id}
                    for member in package.members
                ):
                    raise ProductRecordsDenied("UNEVALUATED_STRATEGY_CHANGE")
                predecessor_rows = (
                    (
                        await connection.execute(
                            text("""SELECT m.role,v.* FROM record_strategy_package_members m
                        JOIN record_strategy_agent_versions v ON v.id=m.agent_version_id
                        WHERE m.package_id=:package_id"""),
                            {"package_id": request.baseline_package_id},
                        )
                    )
                    .mappings()
                    .all()
                )
                predecessors = {row["role"]: row for row in predecessor_rows}
                for member in package.members:
                    prior = predecessors.get(member.configuration.role)
                    if prior is None or member.supersedes_id != prior["id"]:
                        raise ProductRecordsDenied("PROMOTION_LINEAGE_MISMATCH")
                    unchanged = {
                        "prompt_artifact_id": member.prompt.id,
                        "prompt_kind": member.prompt.kind,
                        "prompt_version": member.prompt.version,
                        "prompt_hash": member.prompt.content_hash,
                        "few_shot_artifact_id": member.few_shot.id
                        if member.few_shot
                        else None,
                        "few_shot_kind": member.few_shot.kind
                        if member.few_shot
                        else None,
                        "few_shot_version": member.few_shot.version
                        if member.few_shot
                        else None,
                        "few_shot_hash": member.few_shot.content_hash
                        if member.few_shot
                        else None,
                        "model_identifier": member.model_identifier,
                        "reasoning_effort": member.reasoning_effort,
                        "budget_policy_version": member.budget_policy_version,
                        "max_tool_calls": member.max_tool_calls,
                        "max_searches": member.max_searches,
                        "max_pages": member.max_pages,
                    }
                    if any(prior[key] != value for key, value in unchanged.items()):
                        raise ProductRecordsDenied("UNEVALUATED_STRATEGY_CHANGE")
                    if member.origin_candidate_id is not None and (
                        prior["prompt_artifact_id"] != evidence["baseline_artifact_id"]
                        or prior["prompt_kind"] != evidence["baseline_artifact_kind"]
                        or prior["prompt_version"]
                        != evidence["baseline_artifact_version"]
                        or prior["prompt_hash"] != evidence["baseline_artifact_hash"]
                    ):
                        raise ProductRecordsDenied("PROMOTION_CANDIDATE_MISMATCH")
                    if member.origin_candidate_id is None and (
                        member.configuration.model_dump(mode="json")
                        != prior["configuration"]
                    ):
                        raise ProductRecordsDenied("UNEVALUATED_STRATEGY_CHANGE")
                await self._insert_strategy_package(connection, package, now)
                promoted_package_id = package.id
            content_hash = _canonical_hash(request.model_dump(mode="json"))
            await connection.execute(
                text("""INSERT INTO record_strategy_promotion_decisions
                (id,proposal_id,candidate_id,comparison_id,assessment_id,baseline_package_id,
                 promoted_package_id,disposition,reason_codes,policy_version,decided_by,content_hash,decided_at)
                VALUES (:id,:proposal_id,:candidate_id,:comparison_id,:assessment_id,:baseline_package_id,
                 :promoted_package_id,:disposition,CAST(:reason_codes AS jsonb),:policy_version,
                 :decided_by,:content_hash,:decided_at)"""),
                {
                    **request.model_dump(exclude={"package", "reason_codes"}),
                    "promoted_package_id": promoted_package_id,
                    "reason_codes": json.dumps(request.reason_codes),
                    "content_hash": content_hash,
                    "decided_at": now,
                },
            )
            if request.disposition == "ACCEPTED":
                await self._insert_registry_event(
                    connection,
                    event_id=uuid4(),
                    kind="PROMOTE_PACKAGE",
                    operator_id=request.decided_by,
                    package_id=promoted_package_id,
                    rollback_decision_id=None,
                    reason_codes=request.reason_codes,
                    content_hash=content_hash,
                    now=now,
                )
            else:
                await connection.execute(
                    text("""INSERT INTO record_negative_learning_records
                    (id,proposal_id,comparison_id,promotion_decision_id,classification,
                     reason_codes,content_hash,created_at)
                    VALUES (:id,:proposal_id,:comparison_id,:promotion_decision_id,
                     'REJECTED_PROMOTION',CAST(:reason_codes AS jsonb),:content_hash,:created_at)"""),
                    {
                        "id": uuid4(),
                        "proposal_id": request.proposal_id,
                        "comparison_id": request.comparison_id,
                        "promotion_decision_id": request.id,
                        "reason_codes": json.dumps(request.reason_codes),
                        "content_hash": content_hash,
                        "created_at": now,
                    },
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=None,
                kind="RECORD_STRATEGY_PROMOTION",
                request_hash=request_hash,
                result_type="STRATEGY_PROMOTION_DECISION",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_live_observation(
        self, request: LiveStrategyObservationRequest, *, command_key: UUID
    ) -> CommandReceipt:
        request_hash = _request_hash(request=request)
        async with self.engine.begin() as connection:
            binding = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM record_strategy_execution_bindings WHERE id=:id"
                        ),
                        {"id": request.execution_binding_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if binding is None:
                raise ProductRecordsDenied("STRATEGY_EXECUTION_LINEAGE")
            await lock_experiment(connection, binding["experiment_id"])
            old = await _existing(
                connection,
                command_key,
                "RECORD_LIVE_STRATEGY_OBSERVATION",
                request_hash,
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            now = self.clock()
            await self._insert_live_input_bundle(
                connection, request=request, binding=binding, now=now
            )
            segment_hash = _canonical_hash(
                {"kind": request.segment_kind, "key": request.segment_key}
            )
            content_hash = _canonical_hash(request.model_dump(mode="json"))
            await connection.execute(
                text("""INSERT INTO record_live_strategy_observations
                (id,execution_binding_id,experiment_id,package_id,agent_version_id,role,
                 input_bundle_id,segment_kind,segment_key,segment_hash,observed_from,observed_to,
                 content_hash,recorded_by,recorded_at)
                VALUES (:id,:execution_binding_id,:experiment_id,:package_id,:agent_version_id,:role,
                 :input_bundle_id,:segment_kind,:segment_key,:segment_hash,:observed_from,:observed_to,
                 :content_hash,:recorded_by,:recorded_at)"""),
                {
                    "id": request.id,
                    "execution_binding_id": request.execution_binding_id,
                    "experiment_id": binding["experiment_id"],
                    "package_id": binding["package_id"],
                    "agent_version_id": binding["agent_version_id"],
                    "role": binding["role"],
                    "input_bundle_id": request.inputs.id,
                    "segment_kind": request.segment_kind,
                    "segment_key": request.segment_key,
                    "segment_hash": segment_hash,
                    "observed_from": request.observed_from,
                    "observed_to": request.observed_to,
                    "content_hash": content_hash,
                    "recorded_by": request.recorded_by,
                    "recorded_at": now,
                },
            )
            metric_rows = []
            for metric in request.metrics:
                metric_hash = _canonical_hash(metric.model_dump(mode="json"))
                metric_rows.append(
                    (
                        metric.category,
                        metric.code,
                        metric.value,
                        metric.unit,
                        metric_hash,
                    )
                )
                await connection.execute(
                    text("""INSERT INTO record_live_strategy_metrics
                    (observation_id,category,code,value,unit,content_hash)
                    VALUES (:observation_id,:category,:code,:value,:unit,:content_hash)"""),
                    {
                        "observation_id": request.id,
                        **metric.model_dump(),
                        "content_hash": metric_hash,
                    },
                )
            await connection.execute(
                text("""INSERT INTO record_live_strategy_observation_seals
                (observation_id,metric_count,metric_set_hash,sealed_at)
                VALUES (:observation_id,:metric_count,:metric_set_hash,:sealed_at)"""),
                {
                    "observation_id": request.id,
                    "metric_count": len(metric_rows),
                    "metric_set_hash": _canonical_hash(sorted(metric_rows)),
                    "sealed_at": now,
                },
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=binding["experiment_id"],
                kind="RECORD_LIVE_STRATEGY_OBSERVATION",
                request_hash=request_hash,
                result_type="LIVE_STRATEGY_OBSERVATION",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_live_regression_assessment(
        self, request: LiveRegressionAssessmentRequest, *, command_key: UUID
    ) -> CommandReceipt:
        request_hash = _request_hash(request=request)
        async with self.engine.begin() as connection:
            experiment_ids = (
                (
                    await connection.execute(
                        text("""SELECT DISTINCT experiment_id FROM record_live_strategy_observations
                    WHERE id=ANY(:ids) AND package_id=:package_id"""),
                        {
                            "ids": list(request.observation_ids),
                            "package_id": request.package_id,
                        },
                    )
                )
                .scalars()
                .all()
            )
            if len(experiment_ids) != 1:
                raise ProductRecordsDenied("LIVE_ASSESSMENT_LINEAGE")
            await lock_experiment(connection, experiment_ids[0])
            old = await _existing(
                connection,
                command_key,
                "RECORD_LIVE_REGRESSION_ASSESSMENT",
                request_hash,
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            content_hash = _canonical_hash(request.model_dump(mode="json"))
            now = self.clock()
            await connection.execute(
                text("""INSERT INTO record_learning_regression_assessments
                (id,comparison_id,disposition,metric_results,rollback_satisfied,content_hash,
                 created_at,subject_kind,live_package_id,confidence,sample_size,
                 live_evaluator_version,live_evaluator_hash)
                VALUES (:id,NULL,:disposition,CAST(:metric_results AS jsonb),:rollback_satisfied,
                 :content_hash,:created_at,'LIVE',:live_package_id,:confidence,:sample_size,
                 :live_evaluator_version,:live_evaluator_hash)"""),
                {
                    "id": request.id,
                    "disposition": request.disposition,
                    "metric_results": json.dumps(
                        request.metric_results, sort_keys=True
                    ),
                    "rollback_satisfied": request.rollback_satisfied,
                    "content_hash": content_hash,
                    "created_at": now,
                    "live_package_id": request.package_id,
                    "confidence": request.confidence,
                    "sample_size": request.sample_size,
                    "live_evaluator_version": request.evaluator_version,
                    "live_evaluator_hash": request.evaluator_hash,
                },
            )
            for observation_id in request.observation_ids:
                await connection.execute(
                    text("""INSERT INTO record_live_regression_observations
                    (assessment_id,observation_id) VALUES (:assessment_id,:observation_id)"""),
                    {"assessment_id": request.id, "observation_id": observation_id},
                )
            await connection.execute(
                text("""INSERT INTO record_live_regression_assessment_seals
                (assessment_id,observation_count,observation_set_hash,sealed_at)
                VALUES (:assessment_id,:observation_count,:observation_set_hash,:sealed_at)"""),
                {
                    "assessment_id": request.id,
                    "observation_count": len(request.observation_ids),
                    "observation_set_hash": _canonical_hash(
                        sorted(request.observation_ids)
                    ),
                    "sealed_at": now,
                },
            )
            if request.failure_reason_codes:
                reasons = json.dumps(request.failure_reason_codes)
                await connection.execute(
                    text("""INSERT INTO record_learning_failure_analyses
                    (id,comparison_id,live_assessment_id,reason_codes,content_hash,created_at)
                    VALUES (:id,NULL,:assessment_id,CAST(:reason_codes AS jsonb),:content_hash,:created_at)"""),
                    {
                        "id": uuid4(),
                        "assessment_id": request.id,
                        "reason_codes": reasons,
                        "content_hash": content_hash,
                        "created_at": now,
                    },
                )
                await connection.execute(
                    text("""INSERT INTO record_negative_learning_records
                    (id,proposal_id,comparison_id,live_assessment_id,strategy_package_id,
                     classification,reason_codes,content_hash,created_at)
                    VALUES (:id,NULL,NULL,:assessment_id,:package_id,:classification,
                     CAST(:reason_codes AS jsonb),:content_hash,:created_at)"""),
                    {
                        "id": uuid4(),
                        "assessment_id": request.id,
                        "package_id": request.package_id,
                        "classification": request.negative_classification,
                        "reason_codes": reasons,
                        "content_hash": content_hash,
                        "created_at": now,
                    },
                )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=experiment_ids[0],
                kind="RECORD_LIVE_REGRESSION_ASSESSMENT",
                request_hash=request_hash,
                result_type="LIVE_REGRESSION_ASSESSMENT",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_rollback(
        self, request: RollbackDecisionRequest, *, command_key: UUID
    ) -> CommandReceipt:
        request_hash = _request_hash(request=request)
        async with self.engine.begin() as connection:
            await connection.execute(
                text("SELECT id FROM record_strategy_registry WHERE id=1 FOR UPDATE")
            )
            old = await _existing(
                connection, command_key, "RECORD_STRATEGY_ROLLBACK", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            assessment = (
                (
                    await connection.execute(
                        text("""SELECT disposition,rollback_satisfied FROM record_learning_regression_assessments
                        WHERE id=:id AND subject_kind='LIVE' AND live_package_id=:package_id"""),
                        {
                            "id": request.assessment_id,
                            "package_id": request.current_package_id,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            if assessment is None or (
                not request.forced and not assessment["rollback_satisfied"]
            ):
                raise ProductRecordsDenied("ROLLBACK_EVIDENCE_MISMATCH")
            now = self.clock()
            current = (
                (
                    await connection.execute(
                        text(
                            "SELECT logical_id,version,created_at FROM record_global_strategy_packages WHERE id=:id"
                        ),
                        {"id": request.current_package_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            eligible_ids = [
                item.package_id for item in request.candidates if item.eligible
            ]
            valid_ids = (
                (
                    await connection.execute(
                        text("""SELECT p.id FROM record_global_strategy_packages p
                    JOIN record_strategy_package_seals s ON s.package_id=p.id
                    WHERE p.id=ANY(:ids) AND p.logical_id=:logical_id AND p.version<:version
                      AND p.created_at<=:created_at
                      AND NOT EXISTS(SELECT 1 FROM record_strategy_rollback_decisions r
                                     WHERE r.current_package_id=p.id)"""),
                        {
                            "ids": eligible_ids,
                            "logical_id": current["logical_id"] if current else None,
                            "version": current["version"] if current else 0,
                            "created_at": current["created_at"] if current else now,
                        },
                    )
                )
                .scalars()
                .all()
            )
            if current is None or set(valid_ids) != set(eligible_ids):
                raise ProductRecordsDenied("ROLLBACK_TARGET_NOT_ELIGIBLE")
            content_hash = _canonical_hash(request.model_dump(mode="json"))
            await connection.execute(
                text("""INSERT INTO record_strategy_rollback_decisions
                (id,current_package_id,target_package_id,assessment_id,forced,policy_version,
                 decided_by,reason_codes,content_hash,decided_at)
                VALUES (:id,:current_package_id,:target_package_id,:assessment_id,:forced,:policy_version,
                 :decided_by,CAST(:reason_codes AS jsonb),:content_hash,:decided_at)"""),
                {
                    **request.model_dump(exclude={"candidates", "reason_codes"}),
                    "reason_codes": json.dumps(request.reason_codes),
                    "content_hash": content_hash,
                    "decided_at": now,
                },
            )
            candidate_rows = []
            for candidate in request.candidates:
                candidate_rows.append(candidate.model_dump(mode="json"))
                await connection.execute(
                    text("""INSERT INTO record_strategy_rollback_candidates
                    (rollback_id,package_id,confidence,eligible,reason_codes)
                    VALUES (:rollback_id,:package_id,:confidence,:eligible,CAST(:reason_codes AS jsonb))"""),
                    {
                        "rollback_id": request.id,
                        **candidate.model_dump(exclude={"reason_codes"}),
                        "reason_codes": json.dumps(candidate.reason_codes),
                    },
                )
            await connection.execute(
                text("""INSERT INTO record_strategy_rollback_seals
                (rollback_id,candidate_count,candidate_set_hash,sealed_at)
                VALUES (:rollback_id,:candidate_count,:candidate_set_hash,:sealed_at)"""),
                {
                    "rollback_id": request.id,
                    "candidate_count": len(candidate_rows),
                    "candidate_set_hash": _canonical_hash(
                        sorted(candidate_rows, key=lambda item: str(item["package_id"]))
                    ),
                    "sealed_at": now,
                },
            )
            await connection.execute(
                text("""INSERT INTO record_learning_failure_analyses
                (id,comparison_id,live_assessment_id,rollback_decision_id,
                 reason_codes,content_hash,created_at)
                VALUES (:id,NULL,NULL,:rollback_decision_id,
                 CAST(:reason_codes AS jsonb),:content_hash,:created_at)"""),
                {
                    "id": uuid4(),
                    "rollback_decision_id": request.id,
                    "reason_codes": json.dumps(request.reason_codes),
                    "content_hash": content_hash,
                    "created_at": now,
                },
            )
            await connection.execute(
                text("""INSERT INTO record_negative_learning_records
                (id,proposal_id,comparison_id,live_assessment_id,strategy_package_id,
                 rollback_decision_id,classification,reason_codes,content_hash,created_at)
                VALUES (:id,NULL,NULL,:assessment_id,:package_id,:rollback_decision_id,
                 'ROLLED_BACK_STRATEGY',CAST(:reason_codes AS jsonb),:content_hash,:created_at)"""),
                {
                    "id": uuid4(),
                    "assessment_id": request.assessment_id,
                    "package_id": request.current_package_id,
                    "rollback_decision_id": request.id,
                    "reason_codes": json.dumps(request.reason_codes),
                    "content_hash": content_hash,
                    "created_at": now,
                },
            )
            await self._insert_registry_event(
                connection,
                event_id=uuid4(),
                kind="FORCED_ROLLBACK" if request.forced else "ASSESSED_ROLLBACK",
                operator_id=request.decided_by,
                package_id=request.target_package_id,
                rollback_decision_id=request.id,
                reason_codes=request.reason_codes,
                content_hash=content_hash,
                now=now,
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=None,
                kind="RECORD_STRATEGY_ROLLBACK",
                request_hash=request_hash,
                result_type="STRATEGY_ROLLBACK_DECISION",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)

    @safe_records
    async def record_strategy_control(
        self, request: StrategyControlRequest, *, command_key: UUID
    ) -> CommandReceipt:
        request_hash = _request_hash(request=request)
        async with self.engine.begin() as connection:
            await connection.execute(
                text("SELECT id FROM record_strategy_registry WHERE id=1 FOR UPDATE")
            )
            old = await _existing(
                connection, command_key, "RECORD_STRATEGY_CONTROL", request_hash
            )
            if old:
                return CommandReceipt(command_id=old["id"], result_id=old["result_id"])
            package_id = request.package_id
            if request.kind == "FORCED_ROLLBACK":
                package_id = await connection.scalar(
                    text(
                        "SELECT target_package_id FROM record_strategy_rollback_decisions WHERE id=:id AND forced"
                    ),
                    {"id": request.rollback_decision_id},
                )
                if package_id is None:
                    raise ProductRecordsDenied("ROLLBACK_EVIDENCE_MISMATCH")
            content_hash = _canonical_hash(request.model_dump(mode="json"))
            now = self.clock()
            await self._insert_registry_event(
                connection,
                event_id=request.id,
                kind=request.kind,
                operator_id=request.operator_id,
                package_id=package_id,
                rollback_decision_id=request.rollback_decision_id,
                reason_codes=request.reason_codes,
                content_hash=content_hash,
                now=now,
            )
            command_id = await _complete(
                connection,
                command_key=command_key,
                experiment_id=None,
                kind="RECORD_STRATEGY_CONTROL",
                request_hash=request_hash,
                result_type="STRATEGY_REGISTRY_CONTROL",
                result_id=request.id,
                now=now,
            )
            return CommandReceipt(command_id=command_id, result_id=request.id)
