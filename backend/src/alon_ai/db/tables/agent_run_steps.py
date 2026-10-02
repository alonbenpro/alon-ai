"""Durable child checkpoints for an admitted Idea run."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)

from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.records import table

steps = table(
    "agent_run_steps",
    gov.col("run_id", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("step_key", gov.U, primary_key=True),
    gov.col("ordinal", Integer),
    gov.col("kind", String(40)),
    gov.col("candidate_artifact_id", gov.U, nullable=True),
    gov.col("candidate_kind", String(64), nullable=True),
    gov.col("candidate_version", Integer, nullable=True),
    gov.col("candidate_hash", String(64), nullable=True),
    gov.col("request_ref", gov.U),
    gov.col("request_version", Integer),
    gov.col("request_hash", String(64)),
    gov.col("config_ref", gov.U),
    gov.col("config_version", Integer),
    gov.col("config_hash", String(64)),
    gov.col("operation_id", gov.U, nullable=True),
    gov.col("operation_workflow_id", gov.U, nullable=True),
    gov.col("provider_call_id", gov.U, nullable=True),
    gov.col("status", String(24)),
    gov.col("reason_code", String(100), nullable=True),
    gov.col("result_artifact_id", gov.U, nullable=True),
    gov.col("result_kind", String(64), nullable=True),
    gov.col("result_version", Integer, nullable=True),
    gov.col("result_hash", String(64), nullable=True),
    gov.col("output_hash", String(64), nullable=True),
    gov.col("created_at", gov.T),
    gov.col("finished_at", gov.T, nullable=True),
    ForeignKeyConstraint(
        ["run_id", "experiment_id"],
        ["record_agent_runs.run_id", "record_agent_runs.experiment_id"],
    ),
    UniqueConstraint("provider_call_id"),
    ForeignKeyConstraint(
        [
            "candidate_artifact_id",
            "experiment_id",
            "candidate_kind",
            "candidate_version",
            "candidate_hash",
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
        ["operation_id", "operation_workflow_id", "experiment_id"],
        [
            "gov_operations.id",
            "gov_operations.workflow_id",
            "gov_operations.experiment_id",
        ],
    ),
    ForeignKeyConstraint(["provider_call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(
        [
            "result_artifact_id",
            "experiment_id",
            "result_kind",
            "result_version",
            "result_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    CheckConstraint("ordinal > 0"),
    CheckConstraint(
        "kind IN ('MODEL_REQUEST','BRAVE_SEARCH','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','ARTIFACT_SAVE')"
    ),
    CheckConstraint(
        "(candidate_artifact_id IS NULL AND candidate_kind IS NULL AND candidate_version IS NULL AND candidate_hash IS NULL) OR (candidate_artifact_id IS NOT NULL AND candidate_kind='IDEA_CANDIDATE' AND candidate_version > 0 AND candidate_hash ~ '^[0-9a-f]{64}$')"
    ),
    CheckConstraint(
        "request_version > 0 AND config_version > 0 AND request_hash ~ '^[0-9a-f]{64}$' AND config_hash ~ '^[0-9a-f]{64}$'"
    ),
    CheckConstraint("(operation_id IS NULL) = (operation_workflow_id IS NULL)"),
    CheckConstraint(
        "status IN ('CLAIMED','SUCCEEDED','BLOCKED','FAILED','OUTCOME_UNKNOWN')"
    ),
    CheckConstraint("reason_code IS NULL OR reason_code ~ '^[A-Z][A-Z0-9_]{0,99}$'"),
    CheckConstraint(
        "(result_artifact_id IS NULL AND result_kind IS NULL AND result_version IS NULL AND result_hash IS NULL) OR (result_artifact_id IS NOT NULL AND result_kind IS NOT NULL AND result_version > 0 AND result_hash ~ '^[0-9a-f]{64}$')"
    ),
    CheckConstraint(
        "output_hash IS NULL OR (kind='ARTIFACT_SAVE' AND status='SUCCEEDED' AND output_hash ~ '^[0-9a-f]{64}$')"
    ),
    CheckConstraint(
        "(status='CLAIMED' AND reason_code IS NULL AND result_artifact_id IS NULL AND finished_at IS NULL) OR (status='SUCCEEDED' AND reason_code IS NULL AND finished_at IS NOT NULL) OR (status IN ('BLOCKED','FAILED','OUTCOME_UNKNOWN') AND reason_code IS NOT NULL AND result_artifact_id IS NULL AND finished_at IS NOT NULL)"
    ),
)
