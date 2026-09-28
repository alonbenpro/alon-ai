"""Durable operator admission and status for bounded Idea runs."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.records import table

runs = table(
    "agent_runs",
    gov.col("run_id", gov.U, primary_key=True),
    gov.col("command_key", gov.U),
    gov.col("experiment_id", gov.U),
    gov.col("operator_id", gov.U),
    gov.col("task_kind", String(32)),
    gov.col("request_hash", String(64)),
    gov.col("input_refs", JSONB),
    gov.col("profile_id", gov.U),
    gov.col("profile_version", Integer),
    gov.col("profile_hash", String(64)),
    gov.col("provider_mode", String(16)),
    gov.col("dbos_workflow_id", String(200)),
    gov.col("application_version", String(100)),
    gov.col("status", String(24)),
    gov.col("outcome", String(40), nullable=True),
    gov.col("blocked_reason", String(100), nullable=True),
    gov.col("events", JSONB),
    gov.col("cancel_key", gov.U, nullable=True),
    gov.col("cancel_requested_at", gov.T, nullable=True),
    gov.col("cancel_confirmed", Boolean, nullable=False),
    gov.col("review_key", gov.U, nullable=True),
    gov.col("review_status", String(16)),
    gov.col("review_reason", String(4000), nullable=True),
    gov.col("created_at", gov.T),
    gov.col("started_at", gov.T, nullable=True),
    gov.col("finished_at", gov.T, nullable=True),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    ForeignKeyConstraint(["operator_id"], ["record_operators.id"]),
    ForeignKeyConstraint(
        ["profile_id", "profile_version"],
        ["record_operator_profiles.id", "record_operator_profiles.version"],
    ),
    UniqueConstraint("command_key"),
    UniqueConstraint("run_id", "experiment_id"),
    UniqueConstraint("dbos_workflow_id"),
    CheckConstraint("task_kind IN ('IDEA_DISCOVERY','IDEA_REFINEMENT')"),
    CheckConstraint("provider_mode IN ('live','fake','disabled')"),
    CheckConstraint(
        "status IN ('QUEUED','RUNNING','SUCCEEDED','BLOCKED','FAILED','CANCELLED','OUTCOME_UNKNOWN')"
    ),
    CheckConstraint("review_status IN ('PENDING','ACCEPTED','REJECTED')"),
    CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'"),
    CheckConstraint("profile_hash ~ '^[0-9a-f]{64}$'"),
)
