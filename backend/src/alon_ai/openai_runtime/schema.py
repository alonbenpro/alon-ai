"""Content-free evidence for one application-owned OpenAI execution intent."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY

from alon_ai.accounting import schema as gov

run_intents = Table(
    "openai_run_intents",
    gov.metadata,
    gov.col("idempotency_key", gov.U, primary_key=True),
    gov.col("config_id", gov.U),
    gov.col("config_version", gov.U),
    gov.col("experiment_id", gov.U),
    gov.col("workflow_id", gov.U),
    gov.col("operation_id", gov.U),
    gov.col("agent_run_id", gov.U, nullable=True),
    gov.col("prompt_version", String(64)),
    gov.col("prompt_hash", String(64)),
    gov.col("schema_version", String(64)),
    gov.col("output_schema_hash", String(64)),
    gov.col("model_identifier", String(100)),
    gov.col("reasoning_effort", String(16)),
    gov.col("accepted_input_refs", ARRAY(gov.U)),
    gov.col("input_hash", String(64)),
    gov.col("client_request_id", gov.U),
    gov.col("created_at", gov.T),
    gov.col("call_id", gov.U, nullable=True),
    gov.col("outcome", String(32)),
    gov.col("output_hash", String(64), nullable=True),
    gov.col("finished_at", gov.T, nullable=True),
    ForeignKeyConstraint(
        ["config_id", "workflow_id", "config_version"],
        ["gov_configs.id", "gov_configs.workflow_id", "gov_configs.version"],
    ),
    ForeignKeyConstraint(
        ["operation_id", "workflow_id", "experiment_id", "config_version"],
        [
            "gov_operations.id",
            "gov_operations.workflow_id",
            "gov_operations.experiment_id",
            "gov_operations.config_version",
        ],
    ),
    ForeignKeyConstraint(["agent_run_id"], ["gov_agents.id"]),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    UniqueConstraint("call_id"),
    CheckConstraint("input_hash ~ '^[0-9a-f]{64}$'"),
    CheckConstraint("prompt_hash ~ '^[0-9a-f]{64}$'"),
    CheckConstraint("output_schema_hash ~ '^[0-9a-f]{64}$'"),
    CheckConstraint("output_hash IS NULL OR output_hash ~ '^[0-9a-f]{64}$'"),
    CheckConstraint("length(prompt_version) BETWEEN 1 AND 64"),
    CheckConstraint("length(schema_version) BETWEEN 1 AND 64"),
    CheckConstraint("length(model_identifier) BETWEEN 1 AND 100"),
    CheckConstraint(
        "reasoning_effort IN ('none','minimal','low','medium','high','xhigh')"
    ),
    CheckConstraint(
        "outcome IN ('NO_AI','READY','SUCCEEDED','REFUSED','SCHEMA_MISMATCH',"
        "'INCOMPLETE','TIMEOUT','FAILED','UNCERTAIN','CANCELLED')"
    ),
    CheckConstraint(
        "(outcome='READY' AND call_id IS NULL AND output_hash IS NULL AND finished_at IS NULL)"
        " OR (outcome<>'READY' AND finished_at IS NOT NULL)"
    ),
    CheckConstraint("outcome<>'NO_AI' OR call_id IS NULL"),
)

Index(
    "ix_openai_run_intents_operation",
    run_intents.c.operation_id,
    run_intents.c.created_at,
)
