"""Strict inputs for the immutable, offline-only learning ledger."""

from __future__ import annotations

import math
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.providers.contracts import StrictDTO
from alon_ai.records.models import CommandReceipt

ProposalClass = Literal[
    "PROMPT_CHANGE",
    "CONFIG_CHANGE",
    "STRATEGY_CHANGE",
    "OFFER_OR_PRODUCT_CHANGE",
    "ENGINEERING_CAPABILITY_REQUEST",
]
TargetSubsystem = Literal[
    "PROMPT_CONFIGURATION",
    "MODEL_CONFIGURATION",
    "DISCOVERY_STRATEGY",
    "QUALIFICATION_STRATEGY",
    "OUTREACH_STRATEGY",
    "REPLY_STRATEGY",
    "PRODUCT_REVIEW",
    "ENGINEERING_REVIEW",
]
EvaluationDisposition = Literal["PASS", "FAIL", "INCONCLUSIVE", "REJECTED"]

_PROTECTED = (
    "AUTHORIZATION",
    "COMPLIANCE",
    "COMMERCIAL_POLICY",
    "OFFER_ACCEPTANCE",
    "PRODUCT_POLICY",
)
_CANDIDATE_CLASSES = {"PROMPT_CHANGE", "CONFIG_CHANGE", "STRATEGY_CHANGE"}


class LearningArtifactReference(StrictDTO):
    id: UUID
    kind: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")


class LearningEvidenceReference(StrictDTO):
    evidence_id: UUID
    call_id: UUID
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")


class LearningCallSnapshot(StrictDTO):
    call_id: UUID
    snapshot: dict
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")


class LearningUsageReference(StrictDTO):
    usage_id: UUID
    call_id: UUID
    component: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")


class LearningCostReference(StrictDTO):
    id: UUID
    call_id: UUID
    kind: Literal["SETTLEMENT", "CASH_ENTRY"]
    role: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")


class LearningInputBundleInput(StrictDTO):
    id: UUID
    artifacts: tuple[LearningArtifactReference, ...] = Field(min_length=1, max_length=100)
    evidence: tuple[LearningEvidenceReference, ...] = Field(default=(), max_length=100)
    call_snapshots: tuple[LearningCallSnapshot, ...] = Field(default=(), max_length=100)
    usage: tuple[LearningUsageReference, ...] = Field(default=(), max_length=100)
    costs: tuple[LearningCostReference, ...] = Field(default=(), max_length=100)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def references_have_distinct_roles(self):
        roles = [item.role for item in self.artifacts]
        roles += [item.role for item in self.evidence]
        roles += [item.role for item in self.call_snapshots]
        roles += [item.role for item in self.usage]
        roles += [item.role for item in self.costs]
        if len(roles) != len(set(roles)):
            raise ValueError("learning input roles must be unique")
        return self


class LearningScopeInput(StrictDTO):
    id: UUID
    target_subsystem: TargetSubsystem
    protected_components: tuple[str, ...]
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def protected_components_are_canonical(self):
        if self.protected_components != _PROTECTED:
            raise ValueError("protected components are fixed non-learnable invariants")
        return self


class LearningMetric(StrictDTO):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    comparator: Literal["GTE", "LTE", "EQ"]
    threshold: float


class LearningCandidateInput(StrictDTO):
    id: UUID
    logical_id: UUID
    version: int = Field(ge=1)
    baseline_artifact: LearningArtifactReference
    candidate_configuration: dict
    config_diff: tuple[dict, ...] = Field(min_length=1, max_length=100)
    diff_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def diff_is_a_bounded_json_patch(self):
        for patch in self.config_diff:
            if set(patch) != {"op", "path", "value"}:
                raise ValueError("config diff must be an explicit JSON patch")
            if patch["op"] not in {"ADD", "REMOVE", "REPLACE"} or not isinstance(
                patch["path"], str
            ) or not patch["path"].startswith("/"):
                raise ValueError("config diff must be a bounded JSON patch")
            if any(
                protected.lower() in patch["path"].lower()
                for protected in _PROTECTED
            ):
                raise ValueError("config diff cannot change protected components")
        return self


class LearningProposalRequest(StrictDTO):
    id: UUID
    logical_id: UUID
    version: int = Field(ge=1)
    experiment_id: UUID
    workflow_id: UUID
    agent_id: UUID
    agent_version_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluator_version: str = Field(min_length=1, max_length=100)
    evaluator_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    inputs: LearningInputBundleInput
    scope: LearningScopeInput
    proposal_class: ProposalClass
    bottleneck: str = Field(min_length=1, max_length=4000)
    expected_effect: dict
    target_metrics: tuple[LearningMetric, ...] = Field(min_length=1, max_length=30)
    protected_metrics: tuple[LearningMetric, ...] = Field(min_length=1, max_length=30)
    confidence: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=1)
    confounders: tuple[str, ...] = Field(max_length=30)
    evaluation_criteria: dict
    rollback_criteria: dict
    candidate: LearningCandidateInput | None = None
    proposed_by: UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def proposal_class_has_only_allowed_effect(self):
        has_candidate = self.candidate is not None
        if (self.proposal_class in _CANDIDATE_CLASSES) != has_candidate:
            raise ValueError("only prompt, config, and strategy proposals require a candidate")
        expected_target = {
            "OFFER_OR_PRODUCT_CHANGE": "PRODUCT_REVIEW",
            "ENGINEERING_CAPABILITY_REQUEST": "ENGINEERING_REVIEW",
        }.get(self.proposal_class)
        if expected_target is not None and self.scope.target_subsystem != expected_target:
            raise ValueError("review-only proposals have a review-only target")
        if expected_target is None and self.scope.target_subsystem in {
            "PRODUCT_REVIEW",
            "ENGINEERING_REVIEW",
        }:
            raise ValueError("executable learning proposals require an allowed subsystem")
        if len({item.code for item in self.target_metrics}) != len(self.target_metrics):
            raise ValueError("target metrics must be unique")
        if len({item.code for item in self.protected_metrics}) != len(
            self.protected_metrics
        ):
            raise ValueError("protected metrics must be unique")
        return self


class LearningEvaluationRequest(StrictDTO):
    id: UUID
    proposal_id: UUID
    candidate_id: UUID | None = None
    evaluator_version: str = Field(min_length=1, max_length=100)
    evaluator_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    metric_results: dict
    disposition: EvaluationDisposition
    rollback_satisfied: bool
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    failure_reason_codes: tuple[str, ...] = Field(max_length=30)
    negative_classification: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def terminal_negative_evaluations_have_retained_analysis(self):
        negative = self.disposition in {"FAIL", "INCONCLUSIVE", "REJECTED"}
        if negative != bool(self.failure_reason_codes):
            raise ValueError("negative evaluations require failure analysis")
        if negative != bool(self.negative_classification):
            raise ValueError("negative evaluations require a retained negative record")
        return self


class EngineeringCapabilityRequestInput(StrictDTO):
    id: UUID
    proposal_id: UUID
    description: str = Field(min_length=1, max_length=4000)
    boundary: str = Field(min_length=1, max_length=4000)
    expected_benefit: str = Field(min_length=1, max_length=4000)
    risk: str = Field(min_length=1, max_length=4000)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class LearningReviewControlRequest(StrictDTO):
    id: UUID
    run_id: UUID
    kind: Literal["PAUSE_OFFLINE_REVIEW", "PIN_BASELINE"]
    baseline_candidate_id: UUID | None = None
    operator_id: UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def pin_requires_a_candidate_and_pause_does_not(self):
        if (self.kind == "PIN_BASELINE") != (self.baseline_candidate_id is not None):
            raise ValueError("only baseline pin controls reference a candidate")
        return self


class LearningProposalReceipt(CommandReceipt):
    run_id: UUID
    input_bundle_id: UUID
    scope_id: UUID
    proposal_id: UUID
    candidate_id: UUID | None


class LearningEvaluationReceipt(CommandReceipt):
    comparison_id: UUID
    assessment_id: UUID


StrategyRole = Literal["DISCOVERY", "QUALIFICATION", "OUTREACH", "REPLY"]
ReasoningEffort = Literal["NONE", "MINIMAL", "LOW", "MEDIUM", "HIGH", "XHIGH"]

STRATEGY_BUDGET_POLICY_VERSION = "STRATEGY_BUDGET_LIMITS_V1"
MAX_STRATEGY_TOOL_CALLS = 100
MAX_STRATEGY_SEARCHES = 100
MAX_STRATEGY_PAGES = 500


class DiscoveryStrategyConfiguration(StrictDTO):
    role: Literal["DISCOVERY"]
    discovery_rule_version: str = Field(min_length=1, max_length=100)
    source_order: tuple[
        Literal["BRAVE_LOCAL", "BRAVE_COMPANY", "OFFICIAL_WEB"], ...
    ] = Field(min_length=1, max_length=3)


class QualificationStrategyConfiguration(StrictDTO):
    role: Literal["QUALIFICATION"]
    matrix_rule_version: str = Field(min_length=1, max_length=100)
    revalidation_rule_version: str = Field(min_length=1, max_length=100)


class OutreachStrategyConfiguration(StrictDTO):
    role: Literal["OUTREACH"]
    drafting_rule_version: str = Field(min_length=1, max_length=100)
    validation_rule_version: str = Field(min_length=1, max_length=100)


class ReplyStrategyConfiguration(StrictDTO):
    role: Literal["REPLY"]
    interpretation_rule_version: str = Field(min_length=1, max_length=100)
    response_rule_version: str = Field(min_length=1, max_length=100)


StrategyConfiguration = Annotated[
    DiscoveryStrategyConfiguration
    | QualificationStrategyConfiguration
    | OutreachStrategyConfiguration
    | ReplyStrategyConfiguration,
    Field(discriminator="role"),
]


class StrategyAgentVersionInput(StrictDTO):
    id: UUID
    logical_id: UUID
    version: int = Field(ge=1)
    supersedes_id: UUID | None = None
    origin_candidate_id: UUID | None = None
    prompt: LearningArtifactReference
    few_shot: LearningArtifactReference | None = None
    model_identifier: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    reasoning_effort: ReasoningEffort
    budget_policy_version: Literal["STRATEGY_BUDGET_LIMITS_V1"] = (
        STRATEGY_BUDGET_POLICY_VERSION
    )
    max_tool_calls: int = Field(ge=0, le=MAX_STRATEGY_TOOL_CALLS)
    max_searches: int = Field(ge=0, le=MAX_STRATEGY_SEARCHES)
    max_pages: int = Field(ge=0, le=MAX_STRATEGY_PAGES)
    configuration: StrategyConfiguration

    @model_validator(mode="after")
    def exact_role_and_budgets(self):
        if not any((self.max_tool_calls, self.max_searches, self.max_pages)):
            raise ValueError("strategy budgets cannot all be zero")
        return self


class GlobalStrategyPackageRequest(StrictDTO):
    id: UUID
    logical_id: UUID
    version: int = Field(ge=1)
    supersedes_id: UUID | None = None
    members: tuple[StrategyAgentVersionInput, ...] = Field(min_length=4, max_length=4)
    created_by: UUID

    @model_validator(mode="after")
    def complete_role_set(self):
        if {item.configuration.role for item in self.members} != {
            "DISCOVERY",
            "QUALIFICATION",
            "OUTREACH",
            "REPLY",
        }:
            raise ValueError("strategy package requires exactly one member per role")
        return self


class StrategyPackageReceipt(CommandReceipt):
    package_id: UUID
    package_version: int
    package_hash: str


class FreezeExperimentStrategyRequest(StrictDTO):
    experiment_id: UUID
    package_id: UUID
    frozen_by: UUID


class StrategyExecutionBindingRequest(StrictDTO):
    id: UUID
    experiment_id: UUID
    workflow_id: UUID
    agent_id: UUID
    operation_id: UUID
    package_id: UUID
    agent_version_id: UUID
    role: StrategyRole
    model_config_id: UUID
    model_config_workflow_id: UUID
    model_config_version: UUID


class PromotionDecisionRequest(StrictDTO):
    id: UUID
    proposal_id: UUID
    candidate_id: UUID
    comparison_id: UUID
    assessment_id: UUID
    baseline_package_id: UUID
    disposition: Literal["ACCEPTED", "REJECTED"]
    package: GlobalStrategyPackageRequest | None = None
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=30)
    policy_version: Literal["STRATEGY_PROMOTION_V1"] = "STRATEGY_PROMOTION_V1"
    decided_by: UUID

    @model_validator(mode="after")
    def accepted_decisions_create_exactly_one_package(self):
        if (self.disposition == "ACCEPTED") != (self.package is not None):
            raise ValueError("accepted promotion requires a package")
        return self


class LiveStrategyMetricInput(StrictDTO):
    category: Literal["COMMERCIAL", "QUALITY", "SAFETY", "LATENCY", "COST"]
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,31}$")


class LiveStrategyObservationRequest(StrictDTO):
    id: UUID
    execution_binding_id: UUID
    segment_kind: Literal[
        "GLOBAL", "OFFER", "INDUSTRY", "ORGANIZATION_TYPE", "RECIPIENT_MODE"
    ]
    segment_key: str = Field(min_length=1, max_length=200)
    inputs: LearningInputBundleInput
    metrics: tuple[LiveStrategyMetricInput, ...] = Field(min_length=5, max_length=50)
    observed_from: AwareDatetime
    observed_to: AwareDatetime
    recorded_by: UUID

    @model_validator(mode="after")
    def complete_observation(self):
        if self.observed_to < self.observed_from:
            raise ValueError("observation window is invalid")
        if {item.category for item in self.metrics} != {
            "COMMERCIAL",
            "QUALITY",
            "SAFETY",
            "LATENCY",
            "COST",
        }:
            raise ValueError("live observation requires all metric categories")
        if len({(item.category, item.code) for item in self.metrics}) != len(
            self.metrics
        ):
            raise ValueError("live observation metrics must be unique")
        if not self.inputs.usage or not self.inputs.costs:
            raise ValueError("live observation requires exact usage and cost lineage")
        return self


class LiveRegressionAssessmentRequest(StrictDTO):
    id: UUID
    package_id: UUID
    observation_ids: tuple[UUID, ...] = Field(min_length=1, max_length=1000)
    evaluator_version: str = Field(min_length=1, max_length=100)
    evaluator_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    disposition: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    metric_results: dict[str, float]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    sample_size: int = Field(ge=1)
    rollback_satisfied: bool
    failure_reason_codes: tuple[str, ...] = Field(default=(), max_length=30)
    negative_classification: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def negative_assessment_retains_analysis(self):
        negative = self.disposition in {"FAIL", "INCONCLUSIVE"}
        if negative != bool(self.failure_reason_codes) or negative != bool(
            self.negative_classification
        ):
            raise ValueError("negative live assessment requires retained analysis")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("live assessment observations must be unique")
        if not all(math.isfinite(value) for value in self.metric_results.values()):
            raise ValueError("live assessment metrics must be finite")
        return self


class RollbackCandidateInput(StrictDTO):
    package_id: UUID
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    eligible: bool
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=30)


class RollbackDecisionRequest(StrictDTO):
    id: UUID
    current_package_id: UUID
    target_package_id: UUID
    assessment_id: UUID
    candidates: tuple[RollbackCandidateInput, ...] = Field(min_length=1, max_length=100)
    forced: bool = False
    policy_version: Literal["HIGHEST_CONFIDENCE_ELIGIBLE_V1"] = (
        "HIGHEST_CONFIDENCE_ELIGIBLE_V1"
    )
    decided_by: UUID
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def target_is_highest_confidence_eligible(self):
        if self.current_package_id == self.target_package_id:
            raise ValueError("rollback target must differ from current package")
        if len({item.package_id for item in self.candidates}) != len(self.candidates):
            raise ValueError("rollback candidates must be unique")
        eligible = [item for item in self.candidates if item.eligible]
        if not eligible:
            raise ValueError("rollback requires an eligible retained package")
        highest = max(item.confidence for item in eligible)
        winners = sorted(
            (item for item in eligible if item.confidence == highest),
            key=lambda item: str(item.package_id),
        )
        if self.target_package_id != winners[0].package_id:
            raise ValueError("rollback target is not the deterministic highest confidence package")
        return self


class StrategyControlRequest(StrictDTO):
    id: UUID
    kind: Literal["PAUSE", "RESUME", "PIN", "UNPIN", "FORCED_ROLLBACK"]
    package_id: UUID | None = None
    rollback_decision_id: UUID | None = None
    operator_id: UUID
    reason_codes: tuple[str, ...] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def exact_control_target(self):
        if self.kind == "PIN" and self.package_id is None:
            raise ValueError("pin requires a package")
        if self.kind == "FORCED_ROLLBACK" and self.rollback_decision_id is None:
            raise ValueError("forced rollback requires a decision")
        if self.kind in {"PAUSE", "RESUME", "UNPIN"} and (
            self.package_id is not None or self.rollback_decision_id is not None
        ):
            raise ValueError("control target does not match control kind")
        return self
