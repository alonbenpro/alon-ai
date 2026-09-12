"""Fixed L02 supply policy. Provisional evidence grants no business effect authority."""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.providers.contracts import StrictDTO

Dimension = Literal["SOURCE", "QUERY", "CATEGORY", "GEOGRAPHY", "TRAIT"]
FactKind = Literal[
    "IDENTITY_CLEAR",
    "IDENTITY_EXCLUDED",
    "SOURCE_EMAIL",
    "EMAIL_ABSENT",
    "SOURCE_FAILURE",
    "VERIFIED",
    "VERIFICATION_REJECTED",
    "QUALIFIED",
    "REJECTED_FIT",
    "REJECTED_EVIDENCE",
]
StopReason = Literal[
    "CANCELLED",
    "BUDGET_EXHAUSTED",
    "DEADLINE_EXHAUSTED",
    "SOURCE_FAILURE",
    "PROVIDER_FAILURE",
    "SEARCH_EXHAUSTED",
    "SAFETY_STOP",
]


class SupplyDenied(Exception):
    def __init__(self, reason: str):
        # Only application-owned reason codes, never input/source text.
        self.reason = reason
        super().__init__("campaign supply denied: " + reason)


class SupplyPolicy(StrictDTO):
    qualified_contactable_target: Literal[50] = 50
    candidate_batch_size: Literal[100] = 100
    max_total_discovery_batches: Literal[3] = 3


class Filter(StrictDTO):
    dimension: Dimension
    value: UUID


class DiscoveryPlan(StrictDTO):
    qualification_rule_id: UUID
    filters: tuple[Filter, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def distinct(self) -> Self:
        if len(set(self.filters)) != len(self.filters):
            raise ValueError("duplicate planning selection")
        return self


class ReferenceEvidence(StrictDTO):
    """Trusted provisional customer definitions and independently permitted source roots."""

    id: UUID
    experiment_id: UUID
    kind: Literal[
        "FILTER", "VERIFICATION_POLICY", "QUALIFICATION_RULE", "INDEPENDENT_SOURCE"
    ]
    definition: str = Field(pattern=r"^[a-z0-9][a-z0-9 _-]{0,199}$")
    dimension: Dimension | None = None
    mode: Literal["SYNTHETIC", "TRUSTED_REFERENCE"]
    registered_by: UUID

    @model_validator(mode="after")
    def canonical(self) -> Self:
        if self.definition != " ".join(self.definition.split()) or (
            self.kind == "FILTER"
        ) != (self.dimension is not None):
            raise ValueError("noncanonical reference")
        return self


class IdentityEvidence(StrictDTO):
    id: UUID
    experiment_id: UUID
    provenance_ref: UUID
    normalized_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,127}$")
    mode: Literal["SYNTHETIC", "TRUSTED_REFERENCE"]
    registered_by: UUID
    observed_at: AwareDatetime
    valid_until: AwareDatetime

    @model_validator(mode="after")
    def times(self) -> Self:
        if self.observed_at >= self.valid_until:
            raise ValueError("invalid identity interval")
        return self


class SupplyFact(StrictDTO):
    id: UUID
    identity_id: UUID
    kind: FactKind
    mode: Literal["SYNTHETIC", "TRUSTED_REFERENCE"]
    registered_by: UUID
    observed_at: AwareDatetime
    valid_until: AwareDatetime
    contact_ref: UUID | None = None
    policy_ref: UUID | None = None

    @model_validator(mode="after")
    def shape(self) -> Self:
        if self.observed_at >= self.valid_until:
            raise ValueError("invalid fact interval")
        email = self.kind in {"SOURCE_EMAIL", "VERIFIED", "VERIFICATION_REJECTED"}
        policy = self.kind in {
            "VERIFIED",
            "VERIFICATION_REJECTED",
            "QUALIFIED",
            "REJECTED_FIT",
            "REJECTED_EVIDENCE",
        }
        if (self.contact_ref is not None) != email or (
            self.policy_ref is not None
        ) != policy:
            raise ValueError("invalid fact shape")
        return self


class DiscoveryCompletionEvidence(StrictDTO):
    id: UUID
    batch_id: UUID
    filter: Filter
    kind: Literal["QUERY_COMPLETE", "SEARCH_SPACE_EXHAUSTED"]
    mode: Literal["SYNTHETIC", "TRUSTED_REFERENCE"]
    registered_by: UUID
    observed_at: AwareDatetime


class SupplySnapshot(StrictDTO):
    experiment_id: UUID
    state: str
    batches_used: int
    logical_slots: tuple[int, ...]
    businesses_discovered: int
    supported_emails: int
    accepted: int
    current_qualified_contactable: int
    # This is a policy outcome only, never a send/admit/cohort capability.
    authority: Literal["PROVISIONAL_SUPPLY_ONLY"] = "PROVISIONAL_SUPPLY_ONLY"


def validate_change(
    prior: DiscoveryPlan,
    new: DiscoveryPlan,
    allowed: tuple[Filter, ...],
    failed: tuple[Filter, ...],
) -> None:
    old_set, new_set = set(prior.filters), set(new.filters)
    removed, added = old_set - new_set, new_set - old_set
    if prior.qualification_rule_id != new.qualification_rule_id or not new_set <= set(
        allowed
    ):
        raise SupplyDenied("PLAN_CONSTRAINT")
    # Reordering, new labels/IDs and metadata cannot satisfy this relation.
    if not removed and not added:
        raise SupplyDenied("UNCHANGED_PLAN")
    evidence_dimensions = {item.dimension for item in old_set & set(failed)}
    if not evidence_dimensions or any(
        item.dimension not in evidence_dimensions for item in removed | added
    ):
        raise SupplyDenied("UNJUSTIFIED_CHANGE")
