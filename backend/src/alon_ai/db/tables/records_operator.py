"""Operator identities and immutable profile-version table extensions."""

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
from alon_ai.db.tables import records

operators = Table(
    "record_operators",
    gov.metadata,
    gov.col("id", gov.U, primary_key=True),
    gov.col("auth_subject", String(255), nullable=True),
    gov.col("display_name", String(120)),
    gov.col("timezone", String(100)),
    gov.col("status", String(16)),
    gov.col("created_at", gov.T),
    gov.col("updated_at", gov.T),
    UniqueConstraint("auth_subject", name="uq_record_operator_subject"),
    CheckConstraint(
        "status IN ('ACTIVE','DISABLED')", name="ck_record_operator_status"
    ),
    CheckConstraint(
        "status<>'ACTIVE' OR auth_subject IS NOT NULL", name="ck_record_operator_bound"
    ),
    CheckConstraint(
        "length(btrim(display_name)) BETWEEN 1 AND 120", name="ck_record_operator_name"
    ),
    CheckConstraint(
        "auth_subject IS NULL OR auth_subject ~ '^[^[:space:][:cntrl:]]{1,255}$'",
        name="ck_record_operator_subject",
    ),
)
profiles = records.operator_profiles
profiles.append_column(gov.col("profile_schema_version", Integer, server_default="1"))
profiles.append_column(gov.col("delivery", JSONB, nullable=True))
profiles.append_column(gov.col("commercial", JSONB, nullable=True))
profiles.append_column(gov.col("approved_by", gov.U, nullable=True))
profiles.append_constraint(
    ForeignKeyConstraint(
        ["operator_id"], ["record_operators.id"], name="fk_record_profile_operator"
    )
)
profiles.append_constraint(
    ForeignKeyConstraint(
        ["approved_by"], ["record_operators.id"], name="fk_record_profile_approver"
    )
)
profiles.append_constraint(
    CheckConstraint(
        "profile_schema_version=1 OR (profile_schema_version=2 AND delivery IS NOT NULL AND commercial IS NOT NULL AND approved_by IS NOT NULL AND approved_by=operator_id)",
        name="ck_record_profile_shape",
    )
)
Index(
    "uq_record_profile_owner_version",
    profiles.c.operator_id,
    profiles.c.version,
    unique=True,
    postgresql_where=profiles.c.profile_schema_version == 2,
)
Index("ix_record_profile_approver", profiles.c.approved_by)
