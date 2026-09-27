from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.db.tables import accounting as gov
from alon_ai.integrations.schemas.provider import (
    Capability,
    EmailPresence,
)


def _table(name: str, *columns) -> Table:
    return Table("contact_" + name, gov.metadata, *columns)


cases = _table(
    "cases",
    gov.col("candidate_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("source_fact_id", gov.U),
    gov.col("brave_call_id", gov.U, unique=True),
    gov.col("result_evidence_id", gov.U, unique=True),
    gov.col("config_id", gov.U),
    gov.col("config_version", gov.U),
    gov.col("grant_id", gov.U),
    gov.col("grant_version", Integer),
    gov.col("presence", String),
    gov.col("decision", String),
    gov.col("command_key", gov.U, unique=True),
    gov.col("observed_at", gov.T),
    gov.col("valid_until", gov.T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(["brave_call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
    ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
    ForeignKeyConstraint(
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
    UniqueConstraint("candidate_id", "experiment_id"),
    CheckConstraint("observed_at < valid_until"),
    gov.enumcheck("presence", list(EmailPresence)),
    gov.enumcheck("decision", ["AVOIDED_HUNTER", "FALLBACK_ALLOWED", "PAUSED"]),
    CheckConstraint(
        "(presence='PRESENT' AND decision='AVOIDED_HUNTER') OR "
        "(presence='ABSENT' AND decision='FALLBACK_ALLOWED') OR "
        "(presence='NOT_AVAILABLE' AND decision='PAUSED')"
    ),
)


operations = _table(
    "operations",
    gov.col("operation_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("candidate_id", gov.U),
    gov.col("config_id", gov.U),
    gov.col("config_version", gov.U),
    gov.col("case_id", gov.U, nullable=True),
    gov.col("source_fact_id", gov.U, nullable=True),
    gov.col("verification_policy_id", gov.U, nullable=True),
    gov.col("capability", String),
    ForeignKeyConstraint(["operation_id"], ["supply_operations.operation_id"]),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["case_id", "experiment_id"],
        ["contact_cases.candidate_id", "contact_cases.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["verification_policy_id", "experiment_id"],
        ["supply_references.id", "supply_references.experiment_id"],
    ),
    ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
    UniqueConstraint("operation_id", "candidate_id", "experiment_id"),
    gov.enumcheck(
        "capability",
        [
            Capability.BRAVE_LOCAL_DISCOVERY,
            Capability.BRAVE_COMPANY_DISCOVERY,
            Capability.HUNTER_DOMAIN_SEARCH,
            Capability.HUNTER_EMAIL_FINDER,
            Capability.HUNTER_COMPANY_ENRICHMENT,
            Capability.HUNTER_PERSON_ENRICHMENT,
            Capability.HUNTER_EMAIL_VERIFICATION,
        ],
    ),
    CheckConstraint(
        "(capability IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY') "
        "AND case_id IS NULL AND source_fact_id IS NULL AND verification_policy_id IS NULL) OR "
        "(capability IN ('HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT') "
        "AND case_id IS NOT NULL AND source_fact_id IS NULL AND verification_policy_id IS NULL) OR "
        "(capability='HUNTER_EMAIL_VERIFICATION' AND case_id IS NOT NULL "
        "AND source_fact_id IS NOT NULL AND verification_policy_id IS NOT NULL)"
    ),
)


attempts = _table(
    "attempts",
    gov.col("call_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("operation_id", gov.U),
    gov.col("candidate_id", gov.U),
    gov.col("result_evidence_id", gov.U, unique=True),
    gov.col("output_fact_id", gov.U, nullable=True),
    gov.col("outcome", String),
    gov.col("command_key", gov.U, unique=True),
    gov.col("observed_at", gov.T),
    gov.col("valid_until", gov.T),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(
        ["operation_id", "candidate_id", "experiment_id"],
        [
            "contact_operations.operation_id",
            "contact_operations.candidate_id",
            "contact_operations.experiment_id",
        ],
    ),
    ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
    ForeignKeyConstraint(
        ["output_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    UniqueConstraint("output_fact_id"),
    CheckConstraint("observed_at < valid_until"),
    gov.enumcheck(
        "outcome",
        [
            "FOUND",
            "NOT_FOUND",
            "VALID",
            "INVALID",
            "ACCEPT_ALL",
            "UNKNOWN",
            "TEMPORARY_FAILURE",
            "TRANSIENT",
        ],
    ),
)


CONTACT_TABLES = (cases, operations, attempts)
