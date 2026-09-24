"""Revocable sessions for the existing single-operator identity.

Revision ID: 20260923_21
Revises: 20260923_20
"""

from alembic import op

revision = "20260923_21"
down_revision = "20260923_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
CREATE TABLE operator_sessions (
 id UUID PRIMARY KEY,
 operator_id UUID NOT NULL REFERENCES record_operators(id),
 issued_at TIMESTAMPTZ NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL,
 revoked_at TIMESTAMPTZ,
 CHECK (expires_at > issued_at),
 CHECK (revoked_at IS NULL OR revoked_at >= issued_at)
);
CREATE INDEX ix_operator_sessions_active ON operator_sessions(operator_id, expires_at)
 WHERE revoked_at IS NULL;
CREATE TABLE operator_login_failures (
 id UUID PRIMARY KEY,
 auth_subject VARCHAR(255) NOT NULL,
 attempted_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_operator_login_failures_window
 ON operator_login_failures(auth_subject, attempted_at DESC);
CREATE FUNCTION operator_login_failure_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'operator login failure history is immutable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER operator_login_failure_guard BEFORE UPDATE OR DELETE ON operator_login_failures
 FOR EACH ROW EXECUTE FUNCTION operator_login_failure_guard();
CREATE FUNCTION operator_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'operator session history cannot be deleted'; END IF;
 IF TG_OP = 'UPDATE' THEN
  IF ROW(NEW.id, NEW.operator_id, NEW.issued_at, NEW.expires_at)
     IS DISTINCT FROM ROW(OLD.id, OLD.operator_id, OLD.issued_at, OLD.expires_at)
     OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL
  THEN RAISE EXCEPTION 'operator session history is immutable'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER operator_session_guard BEFORE UPDATE OR DELETE ON operator_sessions
 FOR EACH ROW EXECUTE FUNCTION operator_session_guard();
""")


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM operator_sessions)
    OR EXISTS (SELECT 1 FROM operator_login_failures) THEN
  RAISE EXCEPTION 'cannot discard operator session history';
 END IF;
END $$;
DROP TABLE operator_sessions;
DROP FUNCTION operator_session_guard();
DROP TABLE operator_login_failures;
DROP FUNCTION operator_login_failure_guard();
""")
