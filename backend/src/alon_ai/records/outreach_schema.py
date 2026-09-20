"""Immutable outreach context, drafting, and validation lineage."""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.accounting import schema as g


def table(name, *parts):
    return Table("record_outreach_" + name, g.metadata, *parts)


contexts = table(
    "contexts",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("artifact_id", g.U, unique=True),
    g.col("artifact_version", Integer),
    g.col("artifact_hash", String(64)),
    g.col("lineage_hash", String(64)),
    g.col("cohort_id", g.U),
    g.col("decision_id", g.U, unique=True),
    g.col("matrix_id", g.U),
    g.col("dossier_id", g.U),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("recipient_source_id", g.U),
    g.col("contact_source_id", g.U),
    g.col("contact_verification_id", g.U),
    g.col("contact_resolved_at", g.T),
    g.col("contact_valid_until", g.T),
    g.col("reservation_id", g.U),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("prompt_artifact_id", g.U),
    g.col("prompt_version", Integer),
    g.col("prompt_hash", String(64)),
    g.col("model_config_id", g.U),
    g.col("model_config_workflow_id", g.U),
    g.col("model_config_version", g.U),
    g.col("recipient_mode", String(32)),
    g.col("recipient_label", String(200), nullable=True),
    g.col("recipient_label_evidence_id", g.U, nullable=True),
    g.col("greeting", String(200)),
    g.col("frozen_by", g.U),
    g.col("frozen_at", g.T),
    ForeignKeyConstraint(["artifact_id"], ["record_artifacts.id"]),
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
    ForeignKeyConstraint(
        ["contact_source_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["contact_verification_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(["prompt_artifact_id"], ["record_artifacts.id"]),
    ForeignKeyConstraint(
        ["recipient_label_evidence_id", "dossier_id"],
        [
            "record_qualification_evidence.id",
            "record_qualification_evidence.dossier_id",
        ],
    ),
    ForeignKeyConstraint(
        ["model_config_id", "model_config_workflow_id", "model_config_version"],
        ["gov_configs.id", "gov_configs.workflow_id", "gov_configs.version"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("id", "dossier_id"),
    g.enumcheck(
        "recipient_mode", ["NAMED_PERSON", "ROLE_INBOX", "GENERAL_BUSINESS_INBOX"]
    ),
    CheckConstraint(
        "artifact_version>0 AND prompt_version>0 AND "
        "contact_resolved_at<contact_valid_until AND "
        "lineage_hash ~ '^[0-9a-f]{64}$'"
    ),
    CheckConstraint(
        "(recipient_mode='GENERAL_BUSINESS_INBOX' AND recipient_label IS NULL AND "
        "recipient_label_evidence_id IS NULL AND greeting='Hello team') OR "
        "(recipient_mode='NAMED_PERSON' AND recipient_label IS NOT NULL AND "
        "recipient_label_evidence_id IS NOT NULL AND greeting='Hi '||recipient_label) OR "
        "(recipient_mode='ROLE_INBOX' AND recipient_label IS NOT NULL AND "
        "recipient_label_evidence_id IS NOT NULL AND greeting='Hello '||recipient_label||' team')"
    ),
)

coverage = table(
    "coverage",
    g.col("context_id", g.U, primary_key=True),
    g.col("dossier_id", g.U),
    g.col("evidence_id", g.U, primary_key=True),
    g.col("disposition", String(32)),
    g.col("reason_code", String(64), nullable=True),
    ForeignKeyConstraint(
        ["context_id", "dossier_id"],
        ["record_outreach_contexts.id", "record_outreach_contexts.dossier_id"],
    ),
    ForeignKeyConstraint(
        ["evidence_id", "dossier_id"],
        [
            "record_qualification_evidence.id",
            "record_qualification_evidence.dossier_id",
        ],
    ),
    g.enumcheck(
        "disposition",
        [
            "USED",
            "NOT_USED",
            "REJECTED_SENSITIVE",
            "REJECTED_INTRUSIVE",
            "REJECTED_IRRELEVANT",
            "REJECTED_UNSUPPORTED",
        ],
    ),
    CheckConstraint("(disposition='USED')=(reason_code IS NULL)"),
)

angles = table(
    "angles",
    g.col("id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("rank", Integer),
    g.col("text", String(2000)),
    g.col("content_hash", String(64)),
    ForeignKeyConstraint(["context_id"], ["record_outreach_contexts.id"]),
    UniqueConstraint("context_id", "rank"),
    UniqueConstraint("id", "context_id"),
    CheckConstraint("rank>0"),
)

angle_evidence = table(
    "angle_evidence",
    g.col("angle_id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("evidence_id", g.U, primary_key=True),
    ForeignKeyConstraint(
        ["angle_id", "context_id"],
        ["record_outreach_angles.id", "record_outreach_angles.context_id"],
    ),
    ForeignKeyConstraint(
        ["context_id", "evidence_id"],
        ["record_outreach_coverage.context_id", "record_outreach_coverage.evidence_id"],
    ),
)

documents = table(
    "documents",
    g.col("artifact_id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("context_id", g.U),
    g.col("kind", String(64)),
    g.col("version", Integer),
    g.col("content_hash", String(64)),
    ForeignKeyConstraint(
        ["artifact_id", "experiment_id", "kind", "version", "content_hash"],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["context_id", "experiment_id"],
        ["record_outreach_contexts.id", "record_outreach_contexts.experiment_id"],
    ),
    UniqueConstraint("artifact_id", "context_id"),
    g.enumcheck(
        "kind",
        [
            "LEAD_OPPORTUNITY_NARRATIVE",
            "CONVERSATION_STRATEGY",
            "OUTREACH_SEQUENCE_PLAN",
            "EMAIL_DRAFT",
        ],
    ),
)

claims = table(
    "claims",
    g.col("artifact_id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("ordinal", Integer, primary_key=True),
    g.col("kind", String(16)),
    g.col("text", String(4000)),
    ForeignKeyConstraint(
        ["artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    UniqueConstraint("artifact_id", "ordinal"),
    UniqueConstraint("artifact_id", "ordinal", "context_id"),
    g.enumcheck("kind", ["FACTUAL", "COMMERCIAL"]),
    CheckConstraint("ordinal>0"),
)

claim_evidence = table(
    "claim_evidence",
    g.col("artifact_id", g.U, primary_key=True),
    g.col("ordinal", Integer, primary_key=True),
    g.col("context_id", g.U),
    g.col("evidence_id", g.U, primary_key=True),
    ForeignKeyConstraint(
        ["artifact_id", "ordinal", "context_id"],
        [
            "record_outreach_claims.artifact_id",
            "record_outreach_claims.ordinal",
            "record_outreach_claims.context_id",
        ],
    ),
    ForeignKeyConstraint(
        ["context_id", "evidence_id"],
        ["record_outreach_coverage.context_id", "record_outreach_coverage.evidence_id"],
    ),
)

claim_offer_fields = table(
    "claim_offer_fields",
    g.col("artifact_id", g.U, primary_key=True),
    g.col("ordinal", Integer, primary_key=True),
    g.col("context_id", g.U),
    g.col("offer_id", g.U),
    g.col("field_path", String(64), primary_key=True),
    ForeignKeyConstraint(
        ["artifact_id", "ordinal", "context_id"],
        [
            "record_outreach_claims.artifact_id",
            "record_outreach_claims.ordinal",
            "record_outreach_claims.context_id",
        ],
    ),
    ForeignKeyConstraint(
        ["offer_id", "field_path"],
        [
            "record_offer_field_sources.offer_id",
            "record_offer_field_sources.field_path",
        ],
    ),
)

subjects = table(
    "subjects",
    g.col("id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("strategy_artifact_id", g.U),
    g.col("rank", Integer),
    g.col("text", String(998)),
    g.col("content_hash", String(64)),
    ForeignKeyConstraint(["context_id"], ["record_outreach_contexts.id"]),
    ForeignKeyConstraint(
        ["strategy_artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    UniqueConstraint("id", "context_id"),
    UniqueConstraint("context_id", "rank"),
    CheckConstraint("rank>0"),
)

subject_evidence = table(
    "subject_evidence",
    g.col("subject_id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("evidence_id", g.U, primary_key=True),
    ForeignKeyConstraint(
        ["subject_id", "context_id"],
        ["record_outreach_subjects.id", "record_outreach_subjects.context_id"],
    ),
    ForeignKeyConstraint(
        ["context_id", "evidence_id"],
        ["record_outreach_coverage.context_id", "record_outreach_coverage.evidence_id"],
    ),
)

sequence_steps = table(
    "sequence_steps",
    g.col("sequence_artifact_id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("ordinal", Integer, primary_key=True),
    g.col("delay_days", Integer),
    g.col("objective", String(1000)),
    ForeignKeyConstraint(
        ["sequence_artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    CheckConstraint("ordinal>0 AND delay_days>=0"),
)

drafts = table(
    "drafts",
    g.col("artifact_id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("narrative_artifact_id", g.U),
    g.col("strategy_artifact_id", g.U),
    g.col("sequence_artifact_id", g.U),
    g.col("subject_id", g.U),
    g.col("recipient_mode", String(32)),
    g.col("greeting", String(200)),
    ForeignKeyConstraint(
        ["artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    ForeignKeyConstraint(
        ["narrative_artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    ForeignKeyConstraint(
        ["strategy_artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    ForeignKeyConstraint(
        ["sequence_artifact_id", "context_id"],
        [
            "record_outreach_documents.artifact_id",
            "record_outreach_documents.context_id",
        ],
    ),
    ForeignKeyConstraint(
        ["subject_id", "context_id"],
        ["record_outreach_subjects.id", "record_outreach_subjects.context_id"],
    ),
    UniqueConstraint("artifact_id", "context_id"),
    g.enumcheck(
        "recipient_mode", ["NAMED_PERSON", "ROLE_INBOX", "GENERAL_BUSINESS_INBOX"]
    ),
)

draft_angles = table(
    "draft_angles",
    g.col("draft_artifact_id", g.U, primary_key=True),
    g.col("context_id", g.U),
    g.col("angle_id", g.U),
    g.col("role", String(16), primary_key=True),
    ForeignKeyConstraint(
        ["draft_artifact_id", "context_id"],
        ["record_outreach_drafts.artifact_id", "record_outreach_drafts.context_id"],
    ),
    ForeignKeyConstraint(
        ["angle_id", "context_id"],
        ["record_outreach_angles.id", "record_outreach_angles.context_id"],
    ),
    g.enumcheck("role", ["PRIMARY", "SUPPORTING"]),
)

draft_ctas = table(
    "draft_ctas",
    g.col("draft_artifact_id", g.U, primary_key=True),
    g.col("text", String(1000)),
    ForeignKeyConstraint(["draft_artifact_id"], ["record_outreach_drafts.artifact_id"]),
)

validations = table(
    "validations",
    g.col("id", g.U, primary_key=True),
    g.col("artifact_id", g.U, unique=True),
    g.col("experiment_id", g.U),
    g.col("draft_artifact_id", g.U),
    g.col("validator", String(100)),
    g.col("validator_version", Integer),
    g.col("input_hash", String(64)),
    g.col("disposition", String(8)),
    g.col("reason_codes", ARRAY(String(64))),
    g.col("validated_at", g.T),
    ForeignKeyConstraint(
        ["artifact_id", "experiment_id"],
        ["record_artifacts.id", "record_artifacts.experiment_id"],
    ),
    ForeignKeyConstraint(["draft_artifact_id"], ["record_outreach_drafts.artifact_id"]),
    UniqueConstraint("draft_artifact_id", "validator", "validator_version"),
    g.enumcheck("disposition", ["PASS", "FAIL"]),
    CheckConstraint("validator_version>0 AND cardinality(reason_codes)>=0"),
)

TABLES = (
    contexts,
    coverage,
    angles,
    angle_evidence,
    documents,
    claims,
    claim_evidence,
    claim_offer_fields,
    subjects,
    subject_evidence,
    sequence_steps,
    drafts,
    draft_angles,
    draft_ctas,
    validations,
)
