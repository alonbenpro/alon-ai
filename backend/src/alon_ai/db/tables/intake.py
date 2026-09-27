"""Durable intake commands; immutable identity with bounded progress updates."""

from sqlalchemy import Boolean, CheckConstraint, ForeignKeyConstraint, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from alon_ai.db.tables import accounting as gov
from alon_ai.db.tables.records import table

intakes = table(
    "intakes",
    gov.col("experiment_id", gov.U, primary_key=True),
    gov.col("command_key", gov.U),
    gov.col("operator_id", gov.U),
    gov.col("idea_seed", String(4000), nullable=True),
    gov.col("profile_id", gov.U),
    gov.col("profile_version", Integer),
    gov.col("budget_usd", String(64)),
    gov.col("created_at", gov.T),
    gov.col("draft", Boolean),
    gov.col("blocked_reason", String(100), nullable=True),
    ForeignKeyConstraint(
        ["profile_id", "profile_version"],
        ["record_operator_profiles.id", "record_operator_profiles.version"],
    ),
)
commands = table(
    "intake_commands",
    gov.col("command_key", gov.U, primary_key=True),
    gov.col("experiment_id", gov.U),
    gov.col("request_hash", String(64)),
    gov.col("action", String(16)),
    gov.col("state", String(16)),
    gov.col("payload", JSONB),
    gov.col("result", JSONB, nullable=True),
    gov.col("created_at", gov.T),
    ForeignKeyConstraint(["experiment_id"], ["record_experiments.id"]),
    CheckConstraint("state IN ('RUNNING','COMPLETE','BLOCKED')"),
)
