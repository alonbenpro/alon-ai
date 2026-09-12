"""Bind L02 contact precedence to governed calls and supply facts.

Revision ID: 20260912_03
Revises: 20260912_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260912_03"
down_revision: str | None = "20260912_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

U = postgresql.UUID(as_uuid=True)
T = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "contact_cases",
        sa.Column("candidate_id", U, primary_key=True),
        sa.Column("experiment_id", U, nullable=False),
        sa.Column("source_fact_id", U, nullable=False),
        sa.Column("brave_call_id", U, nullable=False, unique=True),
        sa.Column("result_evidence_id", U, nullable=False, unique=True),
        sa.Column("config_id", U, nullable=False),
        sa.Column("config_version", U, nullable=False),
        sa.Column("grant_id", U, nullable=False),
        sa.Column("grant_version", sa.Integer, nullable=False),
        sa.Column("presence", sa.String, nullable=False),
        sa.Column("decision", sa.String, nullable=False),
        sa.Column("command_key", U, nullable=False, unique=True),
        sa.Column("observed_at", T, nullable=False),
        sa.Column("valid_until", T, nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id", "experiment_id"],
            ["supply_candidates.id", "supply_candidates.experiment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id", "experiment_id"],
            ["supply_facts.id", "supply_facts.experiment_id"],
        ),
        sa.ForeignKeyConstraint(["brave_call_id"], ["gov_calls.id"]),
        sa.ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
        sa.ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
        sa.ForeignKeyConstraint(
            ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
        ),
        sa.UniqueConstraint("candidate_id", "experiment_id"),
        sa.CheckConstraint("observed_at < valid_until"),
        sa.CheckConstraint("presence IN ('PRESENT','ABSENT','NOT_AVAILABLE')"),
        sa.CheckConstraint(
            "decision IN ('AVOIDED_HUNTER','FALLBACK_ALLOWED','PAUSED')"
        ),
        sa.CheckConstraint(
            "(presence='PRESENT' AND decision='AVOIDED_HUNTER') OR "
            "(presence='ABSENT' AND decision='FALLBACK_ALLOWED') OR "
            "(presence='NOT_AVAILABLE' AND decision='PAUSED')"
        ),
    )
    op.create_table(
        "contact_operations",
        sa.Column("operation_id", U, primary_key=True),
        sa.Column("experiment_id", U, nullable=False),
        sa.Column("candidate_id", U, nullable=False),
        sa.Column("config_id", U, nullable=False),
        sa.Column("config_version", U, nullable=False),
        sa.Column("case_id", U),
        sa.Column("source_fact_id", U),
        sa.Column("verification_policy_id", U),
        sa.Column("capability", sa.String, nullable=False),
        sa.ForeignKeyConstraint(["operation_id"], ["supply_operations.operation_id"]),
        sa.ForeignKeyConstraint(
            ["candidate_id", "experiment_id"],
            ["supply_candidates.id", "supply_candidates.experiment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "experiment_id"],
            ["contact_cases.candidate_id", "contact_cases.experiment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id", "experiment_id"],
            ["supply_facts.id", "supply_facts.experiment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["verification_policy_id", "experiment_id"],
            ["supply_references.id", "supply_references.experiment_id"],
        ),
        sa.ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
        sa.UniqueConstraint("operation_id", "candidate_id", "experiment_id"),
        sa.CheckConstraint(
            "capability IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY',"
            "'HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT',"
            "'HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION')"
        ),
        sa.CheckConstraint(
            "(capability IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY') "
            "AND case_id IS NULL AND source_fact_id IS NULL AND verification_policy_id IS NULL) OR "
            "(capability IN ('HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT') "
            "AND case_id IS NOT NULL AND source_fact_id IS NULL AND verification_policy_id IS NULL) OR "
            "(capability='HUNTER_EMAIL_VERIFICATION' AND case_id IS NOT NULL "
            "AND source_fact_id IS NOT NULL AND verification_policy_id IS NOT NULL)"
        ),
    )
    op.create_table(
        "contact_attempts",
        sa.Column("call_id", U, primary_key=True),
        sa.Column("experiment_id", U, nullable=False),
        sa.Column("operation_id", U, nullable=False),
        sa.Column("candidate_id", U, nullable=False),
        sa.Column("result_evidence_id", U, nullable=False, unique=True),
        sa.Column("output_fact_id", U),
        sa.Column("outcome", sa.String, nullable=False),
        sa.Column("command_key", U, nullable=False, unique=True),
        sa.Column("observed_at", T, nullable=False),
        sa.Column("valid_until", T, nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
        sa.ForeignKeyConstraint(
            ["operation_id", "candidate_id", "experiment_id"],
            [
                "contact_operations.operation_id",
                "contact_operations.candidate_id",
                "contact_operations.experiment_id",
            ],
        ),
        sa.ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
        sa.ForeignKeyConstraint(
            ["output_fact_id", "experiment_id"],
            ["supply_facts.id", "supply_facts.experiment_id"],
        ),
        sa.UniqueConstraint("output_fact_id"),
        sa.CheckConstraint("observed_at < valid_until"),
        sa.CheckConstraint(
            "outcome IN ('FOUND','NOT_FOUND','VALID','INVALID','ACCEPT_ALL','UNKNOWN',"
            "'TEMPORARY_FAILURE','TRANSIENT')"
        ),
    )
    op.execute(
        """
CREATE FUNCTION contact_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c supply_candidates; f supply_facts; call gov_calls; proof gov_evidence;
        binding supply_operations; cfg gov_configs; root contact_cases; out_fact supply_facts;
        contact_op contact_operations;
BEGIN
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'immutable contact record'; END IF;
 IF TG_TABLE_NAME='contact_cases' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.source_fact_id;
  SELECT * INTO call FROM gov_calls WHERE id=NEW.brave_call_id;
  SELECT * INTO proof FROM gov_evidence WHERE id=NEW.result_evidence_id;
  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;
  SELECT * INTO contact_op FROM contact_operations WHERE operation_id=call.operation_id;
  IF c.experiment_id IS DISTINCT FROM NEW.experiment_id OR f.identity_id IS DISTINCT FROM c.identity_id
     OR call.experiment_id IS DISTINCT FROM NEW.experiment_id OR call.config_id IS DISTINCT FROM NEW.config_id
     OR call.config_version IS DISTINCT FROM NEW.config_version OR call.grant_id IS DISTINCT FROM NEW.grant_id
     OR call.grant_version IS DISTINCT FROM NEW.grant_version OR call.state<>'FINAL'
     OR contact_op.candidate_id IS DISTINCT FROM NEW.candidate_id OR contact_op.config_id IS DISTINCT FROM NEW.config_id
     OR cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY')
     OR proof.call_id IS DISTINCT FROM call.id OR proof.kind<>'PROVIDER_RESULT'
     OR (NEW.presence='PRESENT' AND f.kind<>'SOURCE_EMAIL')
     OR (NEW.presence='ABSENT' AND f.kind<>'EMAIL_ABSENT')
     OR (NEW.presence='NOT_AVAILABLE' AND f.kind<>'SOURCE_FAILURE')
     OR ((call.result_metadata->>'status'='SUCCEEDED') IS DISTINCT FROM (NEW.presence<>'NOT_AVAILABLE'))
     OR NEW.observed_at IS DISTINCT FROM (call.result_metadata->>'finished_at')::timestamptz
     OR NEW.valid_until>least(f.valid_until,(SELECT expires_at FROM gov_grants WHERE id=NEW.grant_id AND version=NEW.grant_version),(call.attribution->>'deadline')::timestamptz)
  THEN RAISE EXCEPTION 'invalid contact source binding'; END IF;
 ELSIF TG_TABLE_NAME='contact_operations' THEN
  SELECT * INTO binding FROM supply_operations WHERE operation_id=NEW.operation_id;
  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO root FROM contact_cases WHERE candidate_id=NEW.case_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.source_fact_id;
  IF binding.kind<>'CONTACT' OR binding.candidate_id IS DISTINCT FROM NEW.candidate_id
     OR binding.config_id IS DISTINCT FROM NEW.config_id OR binding.config_version IS DISTINCT FROM NEW.config_version
     OR cfg.capability IS DISTINCT FROM NEW.capability
     OR (NEW.case_id IS NOT NULL AND (root.experiment_id IS DISTINCT FROM NEW.experiment_id OR NEW.case_id IS DISTINCT FROM NEW.candidate_id))
     OR (NEW.source_fact_id IS NOT NULL AND (f.kind<>'SOURCE_EMAIL' OR f.identity_id IS DISTINCT FROM c.identity_id))
     OR (NEW.verification_policy_id IS NOT NULL AND NEW.verification_policy_id IS DISTINCT FROM (SELECT verification_policy_id FROM supply_plans WHERE experiment_id=NEW.experiment_id))
  THEN RAISE EXCEPTION 'invalid contact operation binding'; END IF;
 ELSE
 SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
  SELECT * INTO proof FROM gov_evidence WHERE id=NEW.result_evidence_id;
  SELECT * INTO out_fact FROM supply_facts WHERE id=NEW.output_fact_id;
  SELECT * INTO contact_op FROM contact_operations WHERE operation_id=NEW.operation_id;
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO root FROM contact_cases WHERE candidate_id=NEW.candidate_id;
  IF call.operation_id IS DISTINCT FROM NEW.operation_id OR call.experiment_id IS DISTINCT FROM NEW.experiment_id
     OR call.state<>'FINAL' OR call.result_metadata->>'status'<>'SUCCEEDED'
     OR proof.call_id IS DISTINCT FROM call.id OR proof.kind<>'PROVIDER_RESULT'
     OR NEW.observed_at IS DISTINCT FROM (call.result_metadata->>'finished_at')::timestamptz
     OR NEW.valid_until>least(root.valid_until,coalesce(out_fact.valid_until,root.valid_until),(call.attribution->>'deadline')::timestamptz)
     OR (NEW.output_fact_id IS NOT NULL AND (out_fact.experiment_id IS DISTINCT FROM NEW.experiment_id OR out_fact.identity_id IS DISTINCT FROM c.identity_id))
     OR (contact_op.capability='HUNTER_EMAIL_VERIFICATION' AND NEW.outcome NOT IN ('VALID','INVALID','ACCEPT_ALL','UNKNOWN','TEMPORARY_FAILURE','TRANSIENT'))
     OR (contact_op.capability<>'HUNTER_EMAIL_VERIFICATION' AND NEW.outcome NOT IN ('FOUND','NOT_FOUND','TRANSIENT'))
     OR (contact_op.capability='HUNTER_EMAIL_VERIFICATION' AND NEW.outcome='VALID' AND (out_fact.kind IS DISTINCT FROM 'VERIFIED' OR out_fact.contact_ref IS DISTINCT FROM contact_op.source_fact_id OR out_fact.policy_ref IS DISTINCT FROM contact_op.verification_policy_id))
     OR (contact_op.capability='HUNTER_EMAIL_VERIFICATION' AND NEW.outcome IN ('INVALID','ACCEPT_ALL','UNKNOWN') AND (out_fact.kind IS DISTINCT FROM 'VERIFICATION_REJECTED' OR out_fact.contact_ref IS DISTINCT FROM contact_op.source_fact_id OR out_fact.policy_ref IS DISTINCT FROM contact_op.verification_policy_id))
     OR (contact_op.capability='HUNTER_EMAIL_VERIFICATION' AND NEW.outcome IN ('TEMPORARY_FAILURE','TRANSIENT') AND NEW.output_fact_id IS NOT NULL)
     OR (contact_op.capability<>'HUNTER_EMAIL_VERIFICATION' AND NEW.outcome='FOUND' AND out_fact.kind IS DISTINCT FROM 'SOURCE_EMAIL')
     OR (contact_op.capability<>'HUNTER_EMAIL_VERIFICATION' AND NEW.outcome IN ('NOT_FOUND','TRANSIENT') AND NEW.output_fact_id IS NOT NULL)
  THEN RAISE EXCEPTION 'invalid contact attempt binding'; END IF;
 END IF;
 RETURN NEW;
END $$
"""
    )
    for table in ("contact_cases", "contact_operations", "contact_attempts"):
        op.execute(
            f"CREATE TRIGGER contact_guard BEFORE INSERT OR UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION contact_guard()"
        )
        op.execute(
            f"CREATE TRIGGER contact_no_delete BEFORE DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
        )


def downgrade() -> None:
    for table in ("contact_attempts", "contact_operations", "contact_cases"):
        op.drop_table(table)
    op.execute("DROP FUNCTION contact_guard()")
