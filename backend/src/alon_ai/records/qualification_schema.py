"""Immutable offer-specific qualification and exact cohort records."""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.accounting import schema as g


def table(name, *parts):
    return Table("record_qualification_" + name, g.metadata, *parts)


dossiers = table(
    "dossiers",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("binding_id", g.U),
    g.col("admission_id", g.U),
    g.col("recipient_source_id", g.U),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("version", Integer),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["binding_id", "experiment_id", "organization_id"],
        [
            "record_org_bindings.id",
            "record_org_bindings.experiment_id",
            "record_org_bindings.organization_id",
        ],
    ),
    ForeignKeyConstraint(["admission_id"], ["record_org_admissions.id"]),
    ForeignKeyConstraint(
        ["recipient_source_id", "experiment_id", "organization_id", "recipient_id"],
        [
            "record_org_recipient_sources.id",
            "record_org_recipient_sources.experiment_id",
            "record_org_recipient_sources.organization_id",
            "record_org_recipient_sources.recipient_id",
        ],
    ),
    ForeignKeyConstraint(
        ["offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["offer_id", "experiment_id"],
        ["record_offer_packages.id", "record_offer_packages.experiment_id"],
    ),
    ForeignKeyConstraint(["profile_id"], ["record_offer_qualification_profiles.id"]),
    ForeignKeyConstraint(["policy_id"], ["record_initial_outreach_policies.id"]),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("candidate_id", "version"),
    CheckConstraint("version>0"),
)

evidence = table(
    "evidence",
    g.col("id", g.U, primary_key=True),
    g.col("dossier_id", g.U),
    g.col("experiment_id", g.U),
    g.col("code", String(64)),
    g.col("kind", String(24)),
    g.col("source_ref", String(1000)),
    g.col("excerpt", String(4000)),
    g.col("observed_at", g.T),
    g.col("valid_until", g.T),
    g.col("confidence", Numeric(5, 4)),
    ForeignKeyConstraint(
        ["dossier_id", "experiment_id"],
        [
            "record_qualification_dossiers.id",
            "record_qualification_dossiers.experiment_id",
        ],
    ),
    UniqueConstraint("id", "dossier_id"),
    UniqueConstraint("dossier_id", "code"),
    g.enumcheck("kind", ["OBSERVED_FACT", "HYPOTHESIS", "CONTRADICTION", "UNKNOWN"]),
    CheckConstraint("observed_at<valid_until AND confidence BETWEEN 0 AND 1"),
)

matrices = table(
    "matrices",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("dossier_id", g.U, unique=True),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("recipient_source_id", g.U),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["dossier_id", "experiment_id"],
        [
            "record_qualification_dossiers.id",
            "record_qualification_dossiers.experiment_id",
        ],
    ),
    UniqueConstraint("id", "profile_id"),
    UniqueConstraint("id", "dossier_id"),
)

criterion_results = table(
    "criterion_results",
    g.col("matrix_id", g.U, primary_key=True),
    g.col("profile_id", g.U),
    g.col("criterion_code", String(32), primary_key=True),
    g.col("status", String(24)),
    g.col("rationale", String(2000)),
    ForeignKeyConstraint(
        ["matrix_id", "profile_id"],
        [
            "record_qualification_matrices.id",
            "record_qualification_matrices.profile_id",
        ],
    ),
    ForeignKeyConstraint(
        ["profile_id", "criterion_code"],
        [
            "record_qualification_criteria.profile_id",
            "record_qualification_criteria.code",
        ],
    ),
    g.enumcheck(
        "status",
        ["SATISFIED", "PARTIAL", "NOT_SATISFIED", "UNKNOWN", "CONTRADICTED"],
    ),
)

result_evidence = table(
    "result_evidence",
    g.col("matrix_id", g.U, primary_key=True),
    g.col("criterion_code", String(32), primary_key=True),
    g.col("dossier_id", g.U),
    g.col("evidence_id", g.U, primary_key=True),
    ForeignKeyConstraint(
        ["matrix_id", "criterion_code"],
        [
            "record_qualification_criterion_results.matrix_id",
            "record_qualification_criterion_results.criterion_code",
        ],
    ),
    ForeignKeyConstraint(
        ["matrix_id", "dossier_id"],
        [
            "record_qualification_matrices.id",
            "record_qualification_matrices.dossier_id",
        ],
    ),
    ForeignKeyConstraint(
        ["evidence_id", "dossier_id"],
        [
            "record_qualification_evidence.id",
            "record_qualification_evidence.dossier_id",
        ],
    ),
)

decisions = table(
    "decisions",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("matrix_id", g.U, unique=True),
    g.col("dossier_id", g.U, unique=True),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("recipient_source_id", g.U),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("proposal_fact_id", g.U, unique=True),
    g.col("outcome", String(48)),
    g.col("reason_code", String(64)),
    g.col("finding_codes", ARRAY(String(64))),
    g.col("valid_until", g.T),
    g.col("decided_by", g.U),
    g.col("decided_at", g.T),
    ForeignKeyConstraint(
        ["matrix_id", "dossier_id"],
        [
            "record_qualification_matrices.id",
            "record_qualification_matrices.dossier_id",
        ],
    ),
    ForeignKeyConstraint(
        ["proposal_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("id", "offer_acceptance_id"),
    g.enumcheck(
        "outcome",
        [
            "QUALIFIED_CONTACTABLE",
            "PILOT_FIT_CONTACTABLE",
            "REJECTED_NOT_A_FIT",
            "REJECTED_NO_RELEVANT_PROBLEM_SIGNAL",
            "REJECTED_ALREADY_ADEQUATELY_SOLVED",
            "REJECTED_TECHNICAL_MISMATCH",
            "REJECTED_ECONOMIC_MISMATCH",
            "REJECTED_BUYER_MISMATCH",
            "REJECTED_INSUFFICIENT_EVIDENCE",
            "BLOCKED_POLICY_OR_IDENTITY",
            "REVIEW_REQUIRED",
        ],
    ),
    CheckConstraint("cardinality(finding_codes)>0 AND decided_at<valid_until"),
)

cohorts = table(
    "cohorts",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U, unique=True),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("target_size", Integer),
    g.col("frozen_by", g.U),
    g.col("frozen_at", g.T),
    ForeignKeyConstraint(
        ["offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint("target_size=50"),
)

cohort_members = table(
    "cohort_members",
    g.col("cohort_id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("ordinal", Integer, primary_key=True),
    g.col("decision_id", g.U),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("recipient_source_id", g.U),
    g.col("reservation_id", g.U, unique=True),
    ForeignKeyConstraint(
        ["cohort_id", "experiment_id"],
        [
            "record_qualification_cohorts.id",
            "record_qualification_cohorts.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        ["decision_id", "experiment_id"],
        [
            "record_qualification_decisions.id",
            "record_qualification_decisions.experiment_id",
        ],
    ),
    ForeignKeyConstraint(["reservation_id"], ["record_org_reservations.id"]),
    UniqueConstraint("cohort_id", "decision_id"),
    UniqueConstraint("cohort_id", "candidate_id"),
    UniqueConstraint("cohort_id", "organization_id"),
    UniqueConstraint("cohort_id", "recipient_id"),
    UniqueConstraint("cohort_id", "recipient_source_id"),
    CheckConstraint("ordinal BETWEEN 1 AND 50"),
)

TABLES = (
    dossiers,
    evidence,
    matrices,
    criterion_results,
    result_evidence,
    decisions,
    cohorts,
    cohort_members,
)
