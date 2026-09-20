"""Relational authority for offer design and accepted commercial records."""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.accounting import schema as gov
from alon_ai.records import schema as records

metadata = gov.metadata
operator_profiles = records.operator_profiles


def table(name, *parts):
    return Table("record_" + name, metadata, *parts)


offer_bundles = table(
    "offer_bundles",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("idea_acceptance_id", gov.U),
    gov.col("idea_artifact_id", gov.U),
    gov.col("verdict_id", gov.U),
    gov.col("report_artifact_id", gov.U),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(["idea_acceptance_id"], ["record_idea_acceptances.id"]),
    ForeignKeyConstraint(["verdict_id"], ["record_verdicts.id"]),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    UniqueConstraint("verdict_id"),
    CheckConstraint("artifact_kind='OFFER_DESIGN_INPUT_BUNDLE'"),
)

offer_bundle_inputs = table(
    "offer_bundle_inputs",
    gov.col("bundle_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("role", String(64), primary_key=True),
    gov.col("artifact_id", gov.U, primary_key=True),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    ForeignKeyConstraint(
        ["bundle_id", "experiment_id"],
        ["record_offer_bundles.id", "record_offer_bundles.experiment_id"],
    ),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    CheckConstraint("role ~ '^[A-Z][A-Z0-9_]{0,63}$'"),
)

commercial_envelopes = table(
    "commercial_envelopes",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("bundle_id", gov.U),
    gov.col("operator_profile_id", gov.U),
    gov.col("operator_profile_version", Integer),
    gov.col("scope_artifact_id", gov.U),
    gov.col("status", String(32)),
    gov.col("currency", String(3)),
    gov.col("service_hours", Numeric(18, 2)),
    gov.col("delivery_cost", Numeric(18, 2), nullable=True),
    gov.col("minimum_price", Numeric(18, 2), nullable=True),
    gov.col("minimum_margin_rate", Numeric(8, 6)),
    gov.col("maximum_discount_rate", Numeric(8, 6)),
    gov.col("minimum_deposit_rate", Numeric(8, 6)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["bundle_id", "experiment_id"],
        ["record_offer_bundles.id", "record_offer_bundles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["operator_profile_id", "operator_profile_version"],
        ["record_operator_profiles.id", "record_operator_profiles.version"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    UniqueConstraint("bundle_id"),
    CheckConstraint("artifact_kind='COMMERCIAL_DESIGN_ENVELOPE'"),
    gov.enumcheck(
        "status",
        [
            "READY",
            "IMPOSSIBLE_ECONOMICS",
            "CURRENCY_MISMATCH",
            "DELIVERY_CAPACITY_EXCEEDED",
        ],
    ),
    CheckConstraint(
        "(status='READY' AND delivery_cost IS NOT NULL AND minimum_price IS NOT NULL) OR "
        "(status<>'READY' AND delivery_cost IS NULL AND minimum_price IS NULL)"
    ),
)

offer_proposals = table(
    "offer_proposals",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("bundle_id", gov.U),
    gov.col("envelope_id", gov.U),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["bundle_id", "experiment_id"],
        ["record_offer_bundles.id", "record_offer_bundles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["envelope_id", "experiment_id"],
        ["record_commercial_envelopes.id", "record_commercial_envelopes.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    CheckConstraint("artifact_kind='OFFER_DESIGN_PROPOSAL'"),
)

offer_proposal_invalidations = table(
    "offer_proposal_invalidations",
    gov.col("proposal_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("superseding_bundle_id", gov.U),
    gov.col("reason", String(64)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["proposal_id", "experiment_id"],
        ["record_offer_proposals.id", "record_offer_proposals.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["superseding_bundle_id", "experiment_id"],
        ["record_offer_bundles.id", "record_offer_bundles.experiment_id"],
    ),
    CheckConstraint("reason='SUPERSEDED_RESEARCH'"),
)

offer_packages = table(
    "offer_packages",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("proposal_id", gov.U),
    gov.col("bundle_id", gov.U),
    gov.col("envelope_id", gov.U),
    gov.col("currency", String(3)),
    gov.col("base_price", Numeric(18, 2)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["proposal_id", "experiment_id"],
        ["record_offer_proposals.id", "record_offer_proposals.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    UniqueConstraint("proposal_id"),
    UniqueConstraint("bundle_id"),
    CheckConstraint("artifact_kind='OFFER_PACKAGE'"),
)

offer_field_sources = table(
    "offer_field_sources",
    gov.col("offer_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("bundle_id", gov.U),
    gov.col("field_path", String(64), primary_key=True),
    gov.col("source_artifact_id", gov.U, nullable=True),
    gov.col("source_kind", String(64), nullable=True),
    gov.col("source_role", String(64), nullable=True),
    gov.col("source_version", Integer, nullable=True),
    gov.col("source_hash", String(64), nullable=True),
    gov.col("operator_constraint", String(32), nullable=True),
    ForeignKeyConstraint(
        ["offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["bundle_id", "experiment_id"],
        ["record_offer_bundles.id", "record_offer_bundles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["bundle_id", "source_role", "source_artifact_id"],
        [
            "record_offer_bundle_inputs.bundle_id",
            "record_offer_bundle_inputs.role",
            "record_offer_bundle_inputs.artifact_id",
        ],
    ),
    ForeignKeyConstraint(
        [
            "source_artifact_id",
            "experiment_id",
            "source_kind",
            "source_version",
            "source_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    CheckConstraint(
        "(source_artifact_id IS NOT NULL AND source_kind IS NOT NULL AND source_role IS NOT NULL AND source_version IS NOT NULL AND source_hash IS NOT NULL AND operator_constraint IS NULL) OR "
        "(source_artifact_id IS NULL AND source_kind IS NULL AND source_role IS NULL AND source_version IS NULL AND source_hash IS NULL AND operator_constraint IS NOT NULL)"
    ),
    CheckConstraint(
        "field_path IN ('target_customer','buyer','problem','solution_mechanism','credible_outcome','positioning','scope','deliverables','exclusions','prerequisites','timeline','customer_responsibilities','currency','base_price','pilot_terms','third_party_costs','payment_terms','validity','claims','ideal_fit','disqualifiers','negotiation_variables')"
    ),
    CheckConstraint(
        "operator_constraint IS NULL OR operator_constraint IN ('CURRENCY','DELIVERY_CAPACITY','HOURLY_COST','MINIMUM_PRICE','MINIMUM_MARGIN_RATE','MAXIMUM_DISCOUNT_RATE','MINIMUM_DEPOSIT_RATE')"
    ),
)

offer_qualification_profiles = table(
    "offer_qualification_profiles",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("offer_id", gov.U),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    UniqueConstraint("offer_id"),
    CheckConstraint("artifact_kind='OFFER_QUALIFICATION_PROFILE'"),
)

qualification_criteria = table(
    "qualification_criteria",
    gov.col("profile_id", gov.U, primary_key=True),
    gov.col("code", String(32), primary_key=True),
    gov.col("category", String(40)),
    gov.col("requirement", String(1000)),
    gov.col("question", String(1000)),
    gov.col("rule_kind", String(24)),
    gov.col("comparison", String(16)),
    gov.col("threshold", String(200), nullable=True),
    gov.col("required_evidence_kind", String(32)),
    gov.col("unknown_behavior", String(16)),
    ForeignKeyConstraint(["profile_id"], ["record_offer_qualification_profiles.id"]),
    CheckConstraint(
        "rule_kind IN ('HARD_GATE','SOFT_SIGNAL','FATAL_DISQUALIFIER') AND "
        "comparison IN ('PRESENT','BOOLEAN_TRUE','GTE','LTE','EQUALS','ASSESSMENT') AND "
        "required_evidence_kind IN ('RESEARCH_EVIDENCE','PRICE_OBSERVATION','DELIVERY_SCOPE_ESTIMATE','OPERATOR_CONSTRAINT') AND "
        "unknown_behavior IN ('BLOCK','NOT_APPLICABLE')"
    ),
    CheckConstraint(
        "category IN ('REQUIRED_FIT','POSITIVE_SIGNAL','FATAL_DISQUALIFIER','EVIDENCE_QUESTION','TECHNICAL_FIT','ECONOMIC_FIT','BUYER_FIT','CONTACT_FIT','PILOT_FIT','OFFER_SPECIFIC_ASSESSMENT')"
    ),
    CheckConstraint("(comparison IN ('GTE','LTE','EQUALS')) = (threshold IS NOT NULL)"),
    CheckConstraint("rule_kind='SOFT_SIGNAL' OR unknown_behavior='BLOCK'"),
    CheckConstraint(
        "(category='FATAL_DISQUALIFIER') = (rule_kind='FATAL_DISQUALIFIER')"
    ),
)

initial_outreach_policies = table(
    "initial_outreach_policies",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("offer_id", gov.U),
    gov.col("pricing", String(16)),
    gov.col("formal_proposal", String(16)),
    gov.col("detailed_scope", String(16)),
    gov.col("budget_question", String(16)),
    gov.col("primary_goal", String(40)),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    UniqueConstraint("offer_id"),
    CheckConstraint(
        "pricing='OMIT' AND formal_proposal='FORBIDDEN' AND detailed_scope='OMIT' AND "
        "budget_question='FORBIDDEN' AND primary_goal='START_RELEVANT_CONVERSATION'"
    ),
)

offer_acceptances = table(
    "offer_acceptances",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("offer_id", gov.U),
    gov.col("offer_artifact_id", gov.U),
    gov.col("profile_id", gov.U),
    gov.col("profile_artifact_id", gov.U),
    gov.col("policy_id", gov.U),
    gov.col("policy_artifact_id", gov.U),
    gov.col("accepted_by", gov.U),
    gov.col("accepted_at", gov.T),
    ForeignKeyConstraint(
        ["offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    ForeignKeyConstraint(["profile_id"], ["record_offer_qualification_profiles.id"]),
    ForeignKeyConstraint(["policy_id"], ["record_initial_outreach_policies.id"]),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("offer_id"),
)

offer_gap_briefs = table(
    "offer_gap_briefs",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("proposal_id", gov.U),
    gov.col("bundle_id", gov.U),
    gov.col("missing_fields", ARRAY(String(64))),
    gov.col("contradictory_fields", ARRAY(String(64))),
    gov.col("required_source_types", ARRAY(String(64))),
    gov.col("targeted_questions", ARRAY(String(1000))),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["proposal_id", "experiment_id"],
        ["record_offer_proposals.id", "record_offer_proposals.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["bundle_id", "experiment_id"],
        ["record_offer_bundles.id", "record_offer_bundles.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("artifact_id"),
    CheckConstraint("artifact_kind='OFFER_RESEARCH_GAP_BRIEF'"),
    CheckConstraint(
        "cardinality(missing_fields) + cardinality(contradictory_fields) > 0"
    ),
    CheckConstraint(
        "cardinality(required_source_types) > 0 AND cardinality(targeted_questions) > 0"
    ),
)

OFFER_TABLES = (
    offer_bundles,
    offer_bundle_inputs,
    commercial_envelopes,
    offer_proposals,
    offer_proposal_invalidations,
    offer_packages,
    offer_field_sources,
    offer_qualification_profiles,
    qualification_criteria,
    initial_outreach_policies,
    offer_acceptances,
    offer_gap_briefs,
)

for offer_table in OFFER_TABLES:
    for index, constraint in enumerate(
        sorted(
            offer_table.foreign_key_constraints,
            key=lambda item: tuple(element.parent.name for element in item.elements),
        )
    ):
        Index(
            f"ix_{offer_table.name}_fk_{index}",
            *[offer_table.c[element.parent.name] for element in constraint.elements],
        )
