"""L03 product record tables share the L02 governance metadata and roots."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from alon_ai.accounting import schema as gov
from alon_ai.records.models import ArtifactKind

metadata = gov.metadata


def table(name, *parts):
    return Table("record_" + name, metadata, *parts)


operator_profiles = table(
    "operator_profiles",
    gov.col("id", gov.U, primary_key=True),
    gov.col("version", Integer, primary_key=True),
    gov.col("operator_id", gov.U),
    gov.col("capabilities", JSONB),
    gov.col("constraints", JSONB),
    gov.col("content_hash", String(64)),
    gov.col("created_at", gov.T),
    CheckConstraint("version > 0"),
)

experiments = table(
    "experiments",
    gov.col("id", gov.U, primary_key=True),
    gov.col("operator_profile_id", gov.U),
    gov.col("operator_profile_version", Integer),
    gov.col("name", String(120)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["id"], ["gov_experiments.id"]),
    ForeignKeyConstraint(
        ["operator_profile_id", "operator_profile_version"],
        ["record_operator_profiles.id", "record_operator_profiles.version"],
    ),
    CheckConstraint("length(btrim(name)) BETWEEN 1 AND 120"),
)
workflows = table(
    "workflows",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("role", String(100)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["id", "experiment_id"], ["gov_workflows.id", "gov_workflows.experiment_id"]
    ),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint("role ~ '^[A-Z][A-Z0-9_]{0,99}$'"),
)
agents = table(
    "agents",
    gov.col("id", gov.U, primary_key=True),
    gov.col("workflow_id", gov.U),
    gov.col("role", String(100)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["id", "workflow_id"], ["gov_agents.id", "gov_agents.workflow_id"]
    ),
    UniqueConstraint("id", "workflow_id"),
    CheckConstraint("role ~ '^[A-Z][A-Z0-9_]{0,99}$'"),
)

artifacts = table(
    "artifacts",
    gov.col("id", gov.U, primary_key=True),
    gov.col("logical_id", gov.U),
    gov.col("version", Integer),
    gov.col("experiment_id", gov.U),
    gov.col("workflow_id", gov.U, nullable=True),
    gov.col("agent_id", gov.U, nullable=True),
    gov.col("operation_id", gov.U, nullable=True),
    gov.col("kind", String(64)),
    gov.col("schema_version", Integer),
    gov.col("payload", JSONB),
    gov.col("content_hash", String(64)),
    gov.col("created_by", gov.U),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    ForeignKeyConstraint(
        ["workflow_id", "experiment_id"],
        ["record_workflows.id", "record_workflows.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["agent_id", "workflow_id"], ["record_agents.id", "record_agents.workflow_id"]
    ),
    ForeignKeyConstraint(
        ["operation_id", "workflow_id", "experiment_id"],
        [
            "gov_operations.id",
            "gov_operations.workflow_id",
            "gov_operations.experiment_id",
        ],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("logical_id", "version"),
    UniqueConstraint("id", "experiment_id", "kind", "version", "content_hash"),
    CheckConstraint("version > 0 AND schema_version=1"),
    gov.enumcheck("kind", list(ArtifactKind)),
    CheckConstraint("agent_id IS NULL OR workflow_id IS NOT NULL"),
    CheckConstraint("operation_id IS NULL OR workflow_id IS NOT NULL"),
)

artifact_links = table(
    "artifact_links",
    gov.col("consumer_id", gov.U, primary_key=True),
    gov.col("producer_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("role", String(64), primary_key=True),
    gov.col("producer_kind", String(64)),
    gov.col("producer_version", Integer),
    gov.col("producer_hash", String(64)),
    ForeignKeyConstraint(
        ["consumer_id", "experiment_id"],
        ["record_artifacts.id", "record_artifacts.experiment_id"],
    ),
    ForeignKeyConstraint(
        [
            "producer_id",
            "experiment_id",
            "producer_kind",
            "producer_version",
            "producer_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    CheckConstraint("consumer_id <> producer_id"),
)

source_refs = table(
    "source_refs",
    gov.col("id", gov.U, primary_key=True),
    gov.col("artifact_id", gov.U),
    gov.col("experiment_id", gov.U),
    gov.col("kind", String(32)),
    gov.col("evidence_id", gov.U, nullable=True),
    gov.col("retained_id", gov.U, nullable=True),
    gov.col("call_id", gov.U, nullable=True),
    gov.col("grant_id", gov.U, nullable=True),
    gov.col("grant_version", Integer, nullable=True),
    gov.col("field", String, nullable=True),
    gov.col("expires_at", gov.T, nullable=True),
    ForeignKeyConstraint(
        ["artifact_id", "experiment_id"],
        ["record_artifacts.id", "record_artifacts.experiment_id"],
    ),
    ForeignKeyConstraint(["evidence_id"], ["gov_evidence.id"]),
    UniqueConstraint(
        "artifact_id",
        "kind",
        "evidence_id",
        "retained_id",
        postgresql_nulls_not_distinct=True,
    ),
    gov.enumcheck("kind", ["RETAINED_CONTENT", "GOVERNANCE_EVIDENCE"]),
    CheckConstraint(
        "(kind='GOVERNANCE_EVIDENCE' AND evidence_id IS NOT NULL AND retained_id IS NULL AND call_id IS NULL AND grant_id IS NULL AND grant_version IS NULL AND field IS NULL AND expires_at IS NULL) OR "
        "(kind='RETAINED_CONTENT' AND evidence_id IS NULL AND retained_id IS NOT NULL AND call_id IS NOT NULL AND grant_id IS NOT NULL AND grant_version IS NOT NULL AND field IS NOT NULL AND expires_at IS NOT NULL)"
    ),
)

commands = table(
    "commands",
    gov.col("id", gov.U, primary_key=True),
    gov.col("command_key", gov.U, unique=True),
    gov.col("request_hash", String(64)),
    gov.col("experiment_id", gov.U, nullable=True),
    gov.col("kind", String(64)),
    gov.col("result_type", String(64)),
    gov.col("result_id", gov.U),
    gov.col("issued_at", gov.T),
    ForeignKeyConstraint(["experiment_id"], ["gov_experiments.id"]),
)
audit = table(
    "audit",
    gov.col("id", gov.U, primary_key=True),
    gov.col("command_id", gov.U),
    gov.col("experiment_id", gov.U, nullable=True),
    gov.col("kind", String(64)),
    gov.col("aggregate_id", gov.U),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["command_id"], ["record_commands.id"]),
    ForeignKeyConstraint(["experiment_id"], ["gov_experiments.id"]),
    UniqueConstraint("command_id"),
)
outbox = table(
    "outbox",
    gov.col("id", gov.U, primary_key=True),
    gov.col("command_id", gov.U),
    gov.col("experiment_id", gov.U, nullable=True),
    gov.col("topic", String(100)),
    gov.col("aggregate_type", String(64)),
    gov.col("aggregate_id", gov.U),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["command_id"], ["record_commands.id"]),
    ForeignKeyConstraint(["experiment_id"], ["gov_experiments.id"]),
    UniqueConstraint("command_id"),
)

cycles = table(
    "cycles",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("ordinal", Integer),
    gov.col("parent_cycle_id", gov.U, nullable=True),
    gov.col("seed_artifact_id", gov.U),
    gov.col("seed_kind", String(64)),
    gov.col("seed_version", Integer),
    gov.col("seed_hash", String(64)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    ForeignKeyConstraint(
        ["parent_cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["seed_artifact_id", "experiment_id", "seed_kind", "seed_version", "seed_hash"],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("experiment_id", "ordinal"),
    CheckConstraint("ordinal BETWEEN 1 AND 3 AND seed_kind='IDEA_SEED'"),
)

pivot_decisions = table(
    "pivot_decisions",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("approved_by", gov.U),
    gov.col("approved_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
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
    UniqueConstraint("cycle_id", "artifact_id"),
    CheckConstraint("artifact_kind='IDEA_BRIEF'"),
)

idea_acceptances = table(
    "idea_acceptances",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("pivot_approval_id", gov.U, nullable=True),
    gov.col("accepted_by", gov.U),
    gov.col("accepted_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
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
    ForeignKeyConstraint(["pivot_approval_id"], ["record_pivot_decisions.id"]),
    UniqueConstraint("cycle_id"),
    UniqueConstraint("artifact_id"),
    CheckConstraint("artifact_kind='IDEA_BRIEF'"),
)

research_attempts = table(
    "research_attempts",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("ordinal", Integer),
    gov.col("plan_artifact_id", gov.U),
    gov.col("plan_kind", String(64)),
    gov.col("plan_version", Integer),
    gov.col("plan_hash", String(64)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["plan_artifact_id", "experiment_id", "plan_kind", "plan_version", "plan_hash"],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("id", "cycle_id", "experiment_id"),
    UniqueConstraint("cycle_id", "ordinal"),
    UniqueConstraint("plan_artifact_id"),
    CheckConstraint("ordinal BETWEEN 1 AND 3 AND plan_kind='RESEARCH_PLAN'"),
)

verdicts = table(
    "verdicts",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("attempt_id", gov.U),
    gov.col("report_artifact_id", gov.U),
    gov.col("report_kind", String(64)),
    gov.col("report_version", Integer),
    gov.col("report_hash", String(64)),
    gov.col("recommendation_artifact_id", gov.U),
    gov.col("recommendation_kind", String(64)),
    gov.col("recommendation_version", Integer),
    gov.col("recommendation_hash", String(64)),
    gov.col("verdict", String(32)),
    gov.col("committed_by", gov.U),
    gov.col("committed_at", gov.T),
    ForeignKeyConstraint(
        ["attempt_id", "cycle_id", "experiment_id"],
        [
            "record_research_attempts.id",
            "record_research_attempts.cycle_id",
            "record_research_attempts.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        [
            "report_artifact_id",
            "experiment_id",
            "report_kind",
            "report_version",
            "report_hash",
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
        [
            "recommendation_artifact_id",
            "experiment_id",
            "recommendation_kind",
            "recommendation_version",
            "recommendation_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("cycle_id"),
    UniqueConstraint("attempt_id"),
    UniqueConstraint("report_artifact_id"),
    UniqueConstraint("recommendation_artifact_id"),
    gov.enumcheck(
        "verdict",
        [
            "PROCEED_TO_OFFER",
            "REFINE_SAME_IDEA",
            "MATERIAL_PIVOT_RECOMMENDED",
            "KILL_IDEA",
            "INCONCLUSIVE",
        ],
    ),
    CheckConstraint(
        "report_kind='MARKET_RESEARCH_REPORT' AND recommendation_kind='MARKET_RESEARCH_RECOMMENDATION'"
    ),
)

returns = table(
    "returns",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("from_cycle_id", gov.U),
    gov.col("verdict_id", gov.U),
    gov.col("to_cycle_id", gov.U),
    gov.col("ordinal", Integer),
    gov.col("feedback_artifact_id", gov.U),
    gov.col("feedback_kind", String(64)),
    gov.col("feedback_version", Integer),
    gov.col("feedback_hash", String(64)),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["from_cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["verdict_id", "experiment_id"],
        ["record_verdicts.id", "record_verdicts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["to_cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        [
            "feedback_artifact_id",
            "experiment_id",
            "feedback_kind",
            "feedback_version",
            "feedback_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("verdict_id"),
    UniqueConstraint("to_cycle_id"),
    UniqueConstraint("experiment_id", "ordinal"),
    CheckConstraint(
        "ordinal BETWEEN 1 AND 2 AND feedback_kind='RESEARCH_FEEDBACK_BRIEF'"
    ),
)

artifact_dispositions = table(
    "artifact_dispositions",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("validation_artifact_id", gov.U, nullable=True),
    gov.col("validation_kind", String(64), nullable=True),
    gov.col("validation_version", Integer, nullable=True),
    gov.col("validation_hash", String(64), nullable=True),
    gov.col("disposition", String(16)),
    gov.col("decided_by", gov.U),
    gov.col("decided_at", gov.T),
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
        [
            "validation_artifact_id",
            "experiment_id",
            "validation_kind",
            "validation_version",
            "validation_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("artifact_id", "disposition"),
    gov.enumcheck("disposition", ["VALIDATED", "ACCEPTED", "REJECTED", "SUPERSEDED"]),
    CheckConstraint(
        "(disposition IN ('VALIDATED','ACCEPTED') AND validation_artifact_id IS NOT NULL AND validation_kind='VALIDATION_RESULT' AND validation_version IS NOT NULL AND validation_hash IS NOT NULL) OR "
        "(disposition IN ('REJECTED','SUPERSEDED') AND validation_artifact_id IS NULL AND validation_kind IS NULL AND validation_version IS NULL AND validation_hash IS NULL)"
    ),
)

RECORD_TABLES = (
    operator_profiles,
    experiments,
    workflows,
    agents,
    artifacts,
    artifact_links,
    source_refs,
    commands,
    audit,
    outbox,
    cycles,
    pivot_decisions,
    idea_acceptances,
    research_attempts,
    verdicts,
    returns,
    artifact_dispositions,
)

for tab in RECORD_TABLES:
    for index, fk in enumerate(
        sorted(
            tab.foreign_key_constraints,
            key=lambda item: tuple(element.parent.name for element in item.elements),
        )
    ):
        Index(
            f"ix_{tab.name}_fk_{index}",
            *[tab.c[element.parent.name] for element in fk.elements],
        )
