"""Strict inputs for the immutable, offline-only learning ledger."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

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
