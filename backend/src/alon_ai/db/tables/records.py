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

from alon_ai.db.tables import accounting as gov
from alon_ai.services.schemas.records import ArtifactKind

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

candidate_selections = table(
    "candidate_selections",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("artifact_id", gov.U),
    gov.col("artifact_kind", String(64)),
    gov.col("artifact_version", Integer),
    gov.col("artifact_hash", String(64)),
    gov.col("workflow_id", gov.U),
    gov.col("agent_id", gov.U),
    gov.col("profile_id", gov.U),
    gov.col("profile_version", Integer),
    gov.col("selected_by", gov.U),
    gov.col("reason", String(4000)),
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
        ["workflow_id", "experiment_id"],
        ["record_workflows.id", "record_workflows.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["agent_id", "workflow_id"], ["record_agents.id", "record_agents.workflow_id"]
    ),
    ForeignKeyConstraint(
        ["profile_id", "profile_version"],
        ["record_operator_profiles.id", "record_operator_profiles.version"],
    ),
    UniqueConstraint("experiment_id"),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint(
        "artifact_kind='IDEA_CANDIDATE' AND length(btrim(reason)) BETWEEN 1 AND 4000"
    ),
)

cycles = table(
    "cycles",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("ordinal", Integer),
    gov.col("parent_cycle_id", gov.U, nullable=True),
    gov.col("idea_mode", String(32)),
    gov.col("selection_id", gov.U, nullable=True),
    gov.col("purpose", String(32)),
    gov.col("episode_id", gov.U),
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
    ForeignKeyConstraint(
        ["selection_id", "experiment_id"],
        ["record_candidate_selections.id", "record_candidate_selections.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["episode_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    CheckConstraint("ordinal > 0"),
    CheckConstraint(
        "(idea_mode='USER_SEEDED_REFINEMENT' AND seed_kind='IDEA_SEED' AND selection_id IS NULL) OR (idea_mode='SYSTEM_DISCOVERY' AND seed_kind='IDEA_CANDIDATE' AND selection_id IS NOT NULL)"
    ),
    gov.enumcheck(
        "purpose",
        [
            "INITIAL",
            "SAME_INTENT_RETURN",
            "MATERIAL_PIVOT_RETURN",
            "INCONCLUSIVE_SUPPLEMENT",
            "OFFER_GAP_RETURN",
        ],
    ),
)

pivot_decisions = table(
    "pivot_decisions",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("artifact_id", gov.U, nullable=True),
    gov.col("artifact_kind", String(64), nullable=True),
    gov.col("artifact_version", Integer, nullable=True),
    gov.col("artifact_hash", String(64), nullable=True),
    gov.col("approved_by", gov.U),
    gov.col("approved_at", gov.T),
    gov.col("decision", String(16), server_default="APPROVED"),
    gov.col("decision_ordinal", Integer, server_default="1"),
    gov.col("verdict_id", gov.U, nullable=True),
    gov.col("reason_code", String(64), nullable=True),
    ForeignKeyConstraint(
        ["verdict_id", "experiment_id"],
        ["record_verdicts.id", "record_verdicts.experiment_id"],
    ),
    CheckConstraint("decision IN ('APPROVED','DENIED') AND decision_ordinal>0"),
    CheckConstraint(
        "(decision='APPROVED' AND artifact_id IS NOT NULL AND artifact_kind IS NOT NULL AND artifact_version IS NOT NULL AND artifact_hash IS NOT NULL) OR (decision='DENIED' AND verdict_id IS NOT NULL AND reason_code IS NOT NULL AND artifact_id IS NULL AND artifact_kind IS NULL AND artifact_version IS NULL AND artifact_hash IS NULL)"
    ),
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
    UniqueConstraint(
        "id",
        "cycle_id",
        "experiment_id",
        "artifact_id",
        "artifact_kind",
        "artifact_version",
        "artifact_hash",
    ),
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

cycle_transitions = table(
    "cycle_transitions",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("ordinal", Integer),
    gov.col("from_state", String(32)),
    gov.col("to_state", String(32)),
    gov.col("idea_acceptance_id", gov.U),
    gov.col("idea_artifact_id", gov.U),
    gov.col("idea_kind", String(64)),
    gov.col("idea_version", Integer),
    gov.col("idea_hash", String(64)),
    gov.col("research_attempt_id", gov.U),
    gov.col("verdict_id", gov.U, nullable=True),
    gov.col("offer_design_run_id", gov.U, nullable=True),
    gov.col("offer_design_decision_id", gov.U, nullable=True),
    gov.col("command_id", gov.U),
    ForeignKeyConstraint(
        ["verdict_id", "experiment_id"],
        ["record_verdicts.id", "record_verdicts.experiment_id"],
    ),
    ForeignKeyConstraint(["offer_design_run_id"], ["record_offer_design_runs.id"]),
    ForeignKeyConstraint(
        ["offer_design_decision_id"], ["record_offer_design_decisions.id"]
    ),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        [
            "idea_acceptance_id",
            "cycle_id",
            "experiment_id",
            "idea_artifact_id",
            "idea_kind",
            "idea_version",
            "idea_hash",
        ],
        [
            "record_idea_acceptances.id",
            "record_idea_acceptances.cycle_id",
            "record_idea_acceptances.experiment_id",
            "record_idea_acceptances.artifact_id",
            "record_idea_acceptances.artifact_kind",
            "record_idea_acceptances.artifact_version",
            "record_idea_acceptances.artifact_hash",
        ],
    ),
    ForeignKeyConstraint(
        ["research_attempt_id", "cycle_id", "experiment_id"],
        [
            "record_research_attempts.id",
            "record_research_attempts.cycle_id",
            "record_research_attempts.experiment_id",
        ],
    ),
    ForeignKeyConstraint(["command_id"], ["record_commands.id"]),
    UniqueConstraint("cycle_id", "ordinal"),
    UniqueConstraint("id", "cycle_id", "experiment_id", "ordinal", "to_state"),
    CheckConstraint(
        "idea_kind='IDEA_BRIEF' AND ((ordinal=1 AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH' AND verdict_id IS NULL AND offer_design_run_id IS NULL AND offer_design_decision_id IS NULL) OR (ordinal=2 AND from_state='MARKET_RESEARCH' AND to_state IN ('PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW') AND verdict_id IS NOT NULL AND offer_design_run_id IS NULL AND offer_design_decision_id IS NULL) OR (ordinal=3 AND from_state IN ('WAITING_FOR_PIVOT_APPROVAL','INCONCLUSIVE_REVIEW') AND to_state='RETURN_FOR_REFINEMENT' AND verdict_id IS NOT NULL AND offer_design_run_id IS NULL AND offer_design_decision_id IS NULL) OR (from_state='PROCEED_TO_OFFER' AND to_state='OFFER_DESIGN' AND verdict_id IS NOT NULL AND offer_design_run_id IS NOT NULL AND offer_design_decision_id IS NULL) OR (from_state='OFFER_DESIGN' AND to_state IN ('OFFER_ACCEPTED','RETURN_FOR_TARGETED_RESEARCH','WAITING_FOR_OPERATOR_INPUT') AND verdict_id IS NOT NULL AND offer_design_run_id IS NOT NULL AND offer_design_decision_id IS NOT NULL) OR (from_state='WAITING_FOR_OPERATOR_INPUT' AND to_state='RETURN_FOR_IDEA_REFINEMENT' AND verdict_id IS NOT NULL AND offer_design_run_id IS NOT NULL AND offer_design_decision_id IS NOT NULL))"
    ),
)

cycle_states = table(
    "cycle_states",
    gov.col("cycle_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("state", String(32)),
    gov.col("transition_ordinal", Integer),
    gov.col("last_transition_id", gov.U, nullable=True),
    gov.col("updated_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        [
            "last_transition_id",
            "cycle_id",
            "experiment_id",
            "transition_ordinal",
            "state",
        ],
        [
            "record_cycle_transitions.id",
            "record_cycle_transitions.cycle_id",
            "record_cycle_transitions.experiment_id",
            "record_cycle_transitions.ordinal",
            "record_cycle_transitions.to_state",
        ],
    ),
    UniqueConstraint("cycle_id", "experiment_id"),
    CheckConstraint(
        "(state='IDEA_REFINEMENT' AND transition_ordinal=0 "
        "AND last_transition_id IS NULL) OR "
        "(state IN ('MARKET_RESEARCH','PROCEED_TO_OFFER','RETURN_FOR_REFINEMENT','WAITING_FOR_PIVOT_APPROVAL','KILLED','INCONCLUSIVE_REVIEW','OFFER_DESIGN','OFFER_ACCEPTED','RETURN_FOR_TARGETED_RESEARCH','RETURN_FOR_IDEA_REFINEMENT','WAITING_FOR_OPERATOR_INPUT') AND transition_ordinal BETWEEN 1 AND 5 AND last_transition_id IS NOT NULL)"
    ),
)

market_research_workflow_bindings = table(
    "market_research_workflow_bindings",
    gov.col("dbos_workflow_id", String(200), primary_key=True),
    gov.col("application_version", String(64)),
    gov.col("request_hash", String(64)),
    gov.col("business_command_key", gov.U),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("transition_kind", String(64)),
    gov.col("from_state", String(32)),
    gov.col("to_state", String(32)),
    gov.col("transition_id", gov.U, nullable=True),
    gov.col("command_id", gov.U, nullable=True),
    gov.col("delivery_state", String(32)),
    gov.col("created_at", gov.T),
    gov.col("updated_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(["transition_id"], ["record_cycle_transitions.id"]),
    ForeignKeyConstraint(["command_id"], ["record_commands.id"]),
    UniqueConstraint("business_command_key"),
    UniqueConstraint("cycle_id", "experiment_id", "transition_kind"),
    CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'"),
    CheckConstraint(
        "transition_kind='IDEA_REFINEMENT_TO_MARKET_RESEARCH' "
        "AND from_state='IDEA_REFINEMENT' AND to_state='MARKET_RESEARCH'"
    ),
    CheckConstraint(
        "delivery_state IN "
        "('PENDING','STARTED','BUSINESS_COMMITTED','RECEIPT_DELIVERED',"
        "'RUNTIME_COMPLETED','CANCELLED')"
    ),
    CheckConstraint(
        "(delivery_state IN ('PENDING','STARTED','CANCELLED') "
        "AND transition_id IS NULL AND command_id IS NULL) OR "
        "(delivery_state IN "
        "('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED') "
        "AND transition_id IS NOT NULL AND command_id IS NOT NULL)"
    ),
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
    gov.col("kind", String(32)),
    gov.col("applicable_scope_id", gov.U),
    gov.col("idea_artifact_id", gov.U),
    gov.col("offer_input_bundle_id", gov.U, nullable=True),
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
    ForeignKeyConstraint(
        ["offer_input_bundle_id", "experiment_id"],
        ["record_artifacts.id", "record_artifacts.experiment_id"],
    ),
    CheckConstraint("(kind='OFFER_GAP') = (offer_input_bundle_id IS NOT NULL)"),
    ForeignKeyConstraint(
        ["idea_artifact_id", "experiment_id"],
        ["record_artifacts.id", "record_artifacts.experiment_id"],
    ),
    UniqueConstraint("experiment_id", "kind", "applicable_scope_id", "ordinal"),
    CheckConstraint(
        "(kind='SAME_INTENT' AND ordinal BETWEEN 1 AND 2) OR (kind IN ('INCONCLUSIVE_SUPPLEMENT','OFFER_GAP') AND ordinal=1) OR (kind='MATERIAL_PIVOT' AND ordinal>0)"
    ),
    CheckConstraint(
        "(kind='OFFER_GAP' AND feedback_kind='OFFER_RESEARCH_GAP_BRIEF') OR (kind<>'OFFER_GAP' AND feedback_kind='RESEARCH_FEEDBACK_BRIEF')"
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

research_cycle_budgets = table(
    "research_cycle_budgets",
    gov.col("cycle_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("workflow_id", gov.U),
    gov.col("config_id", gov.U),
    gov.col("config_version", gov.U),
    gov.col("budget_account_id", gov.U),
    gov.col("max_search_results", Integer),
    gov.col("max_capture_pages", Integer),
    gov.col("max_openai_calls", Integer),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["workflow_id", "experiment_id"],
        ["record_workflows.id", "record_workflows.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["config_id", "workflow_id", "config_version"],
        ["gov_configs.id", "gov_configs.workflow_id", "gov_configs.version"],
    ),
    ForeignKeyConstraint(["budget_account_id"], ["gov_budget_accounts.id"]),
    UniqueConstraint("workflow_id"),
    CheckConstraint(
        "max_search_results>=0 AND max_capture_pages>=0 AND max_openai_calls>=0"
    ),
)

research_return_blocks = table(
    "research_return_blocks",
    gov.col("id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("verdict_id", gov.U),
    gov.col("return_kind", String(32)),
    gov.col("reason_code", String(64)),
    gov.col("decision_ordinal", Integer, nullable=True),
    gov.col("command_id", gov.U),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["verdict_id", "experiment_id"],
        ["record_verdicts.id", "record_verdicts.experiment_id"],
    ),
    ForeignKeyConstraint(["command_id"], ["record_commands.id"]),
    UniqueConstraint("command_id"),
    CheckConstraint(
        "return_kind IN ('SAME_INTENT','MATERIAL_PIVOT','INCONCLUSIVE_SUPPLEMENT')"
    ),
    CheckConstraint(
        "reason_code IN ('BUDGET_EXHAUSTED','UNFINALIZED_USAGE','SAME_INTENT_LIMIT_REACHED','SUPPLEMENT_LIMIT_REACHED','CANCELLED','STALE_INPUT','MISSING_EVIDENCE','REPEATED_BLOCKER')"
    ),
    CheckConstraint(
        "(return_kind='MATERIAL_PIVOT' AND decision_ordinal>0) OR "
        "(return_kind<>'MATERIAL_PIVOT' AND decision_ordinal IS NULL)"
    ),
)

market_research_decision_workflow_bindings = table(
    "market_research_decision_workflow_bindings",
    gov.col("dbos_workflow_id", String(200), primary_key=True),
    gov.col("application_version", String(64)),
    gov.col("contract_version", Integer),
    gov.col("operation_kind", String(32)),
    gov.col("operation_id", gov.U),
    gov.col("business_command_key", gov.U),
    gov.col("request_hash", String(64)),
    gov.col("request_payload", JSONB),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("command_id", gov.U, nullable=True),
    gov.col("result_id", gov.U, nullable=True),
    gov.col("failure_code", String(64), nullable=True),
    gov.col("delivery_state", String(32)),
    gov.col("created_at", gov.T),
    gov.col("updated_at", gov.T),
    ForeignKeyConstraint(
        ["cycle_id", "experiment_id"],
        ["record_cycles.id", "record_cycles.experiment_id"],
    ),
    ForeignKeyConstraint(["command_id"], ["record_commands.id"]),
    UniqueConstraint("business_command_key"),
    UniqueConstraint("operation_kind", "operation_id", "business_command_key"),
    CheckConstraint(
        "request_hash ~ '^[0-9a-f]{64}$' AND contract_version=1 AND jsonb_typeof(request_payload)='object'"
    ),
    CheckConstraint(
        "operation_kind IN ('OUTCOME','PIVOT_DECISION','INCONCLUSIVE_SUPPLEMENT')"
    ),
    CheckConstraint(
        "delivery_state IN ('PENDING','STARTED','BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED','CANCELLED','REJECTED')"
    ),
    CheckConstraint(
        "(delivery_state IN ('PENDING','STARTED','CANCELLED') AND command_id IS NULL AND result_id IS NULL AND failure_code IS NULL) OR "
        "(delivery_state='REJECTED' AND command_id IS NULL AND result_id IS NULL AND failure_code ~ '^[A-Z][A-Z0-9_]{0,63}$') OR "
        "(delivery_state IN ('BUSINESS_COMMITTED','RECEIPT_DELIVERED','RUNTIME_COMPLETED') AND command_id IS NOT NULL AND result_id IS NOT NULL AND failure_code IS NULL)"
    ),
)

Index(
    "uq_record_pivot_decision_verdict_ordinal",
    pivot_decisions.c.verdict_id,
    pivot_decisions.c.decision_ordinal,
    unique=True,
    postgresql_where=pivot_decisions.c.verdict_id.is_not(None),
)
Index(
    "uq_record_pivot_decision_approved_verdict",
    pivot_decisions.c.verdict_id,
    unique=True,
    postgresql_where=(
        pivot_decisions.c.verdict_id.is_not(None)
        & (pivot_decisions.c.decision == "APPROVED")
    ),
)

idea_refinements = table(
    "idea_refinements",
    gov.col("run_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("seed_artifact_id", gov.U),
    gov.col("operation_id", gov.U),
    gov.col("state", String(32)),
    gov.col("advice_source", String(16)),
    gov.col("advice", JSONB, nullable=True),
    gov.col("output_hash", String(64), nullable=True),
    gov.col("created_at", gov.T),
    gov.col("finished_at", gov.T, nullable=True),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    ForeignKeyConstraint(["cycle_id"], ["record_cycles.id"]),
    ForeignKeyConstraint(["seed_artifact_id"], ["record_artifacts.id"]),
    ForeignKeyConstraint(["operation_id"], ["gov_operations.id"]),
    CheckConstraint(
        "state IN ('RUNNING','SUCCEEDED','REFINEMENT_FAILED','REFINEMENT_BLOCKED')"
    ),
    CheckConstraint("advice_source IN ('RECORDED_FAKE','OPENAI')"),
    CheckConstraint(
        "(state='RUNNING' AND advice IS NULL AND output_hash IS NULL AND finished_at IS NULL) OR (state IN ('REFINEMENT_FAILED','REFINEMENT_BLOCKED') AND advice IS NULL AND output_hash IS NULL AND finished_at IS NOT NULL) OR (state='SUCCEEDED' AND advice IS NOT NULL AND output_hash ~ '^[0-9a-f]{64}$' AND finished_at IS NOT NULL)"
    ),
)
idea_discoveries = table(
    "idea_discoveries",
    gov.col("run_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("operation_id", gov.U),
    gov.col("state", String(32)),
    gov.col("advice_source", String(16)),
    gov.col("advice", JSONB, nullable=True),
    gov.col("output_hash", String(64), nullable=True),
    gov.col("candidate_ids", JSONB, nullable=True),
    gov.col("created_at", gov.T),
    gov.col("finished_at", gov.T, nullable=True),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    ForeignKeyConstraint(["operation_id"], ["gov_operations.id"]),
    CheckConstraint(
        "state IN ('RUNNING','SUCCEEDED','DISCOVERY_FAILED','DISCOVERY_BLOCKED')"
    ),
    CheckConstraint("advice_source IN ('RECORDED_FAKE','OPENAI')"),
    CheckConstraint(
        "(state='RUNNING' AND candidate_ids IS NULL AND finished_at IS NULL) OR (state='SUCCEEDED' AND advice IS NOT NULL AND output_hash ~ '^[0-9a-f]{64}$' AND jsonb_array_length(candidate_ids) BETWEEN 3 AND 5 AND finished_at IS NOT NULL) OR (state IN ('DISCOVERY_FAILED','DISCOVERY_BLOCKED') AND candidate_ids IS NULL AND finished_at IS NOT NULL)"
    ),
)
Index(
    "ix_record_idea_discoveries_experiment",
    idea_discoveries.c.experiment_id,
    idea_discoveries.c.created_at.desc(),
)
idea_intent_reviews = table(
    "idea_intent_reviews",
    gov.col("run_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("cycle_id", gov.U),
    gov.col("source_artifact_id", gov.U),
    gov.col("output_hash", String(64)),
    gov.col("relationship", String(32)),
    gov.col("rationale", String(4000)),
    gov.col("confirmed_by", gov.U),
    gov.col("command_key", gov.U, unique=True),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["run_id"], ["record_idea_refinements.run_id"]),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    ForeignKeyConstraint(["cycle_id"], ["record_cycles.id"]),
    ForeignKeyConstraint(["source_artifact_id"], ["record_artifacts.id"]),
    CheckConstraint(
        "relationship IN ('PRESERVES_CORE_INTENT','CLARIFIES_CORE_INTENT','NARROWS_CORE_INTENT')"
    ),
    CheckConstraint("length(btrim(rationale)) BETWEEN 1 AND 4000"),
    CheckConstraint("output_hash ~ '^[0-9a-f]{64}$'"),
)
Index(
    "ix_record_idea_refinements_cycle",
    idea_refinements.c.cycle_id,
    idea_refinements.c.created_at.desc(),
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
    candidate_selections,
    cycles,
    pivot_decisions,
    idea_acceptances,
    idea_refinements,
    idea_discoveries,
    idea_intent_reviews,
    research_attempts,
    cycle_transitions,
    cycle_states,
    research_cycle_budgets,
    research_return_blocks,
    market_research_decision_workflow_bindings,
    verdicts,
    returns,
    artifact_dispositions,
)

# Preserve indexes from applied migration04 when new foreign keys are added.
_ADDITIONAL_FK_INDEXES = {
    ("record_cycles", "episode_id"): "ix_record_cycles_episode",
    ("record_cycles", "selection_id"): "ix_record_cycles_selection",
    ("record_returns", "idea_artifact_id"): "ix_record_returns_idea",
    ("record_returns", "offer_input_bundle_id"): "ix_record_returns_offer_bundle",
}
for tab in RECORD_TABLES:
    existing_foreign_keys = []
    for fk in tab.foreign_key_constraints:
        first_column = fk.elements[0].parent.name
        explicit_name = _ADDITIONAL_FK_INDEXES.get((tab.name, first_column))
        if explicit_name:
            Index(
                explicit_name, *[tab.c[element.parent.name] for element in fk.elements]
            )
        else:
            existing_foreign_keys.append(fk)
    for index, fk in enumerate(
        sorted(
            existing_foreign_keys,
            key=lambda item: tuple(element.parent.name for element in item.elements),
        )
    ):
        Index(
            f"ix_{tab.name}_fk_{index}",
            *[tab.c[element.parent.name] for element in fk.elements],
        )
