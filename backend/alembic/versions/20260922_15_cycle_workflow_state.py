"""transactional idea-refinement to market-research state

Revision ID: 20260922_15
Revises: 20260921_14
"""

from alembic import op

revision = "20260922_15"
down_revision = "20260921_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
ALTER TABLE record_idea_acceptances
 ADD CONSTRAINT uq_record_idea_acceptance_exact_cycle
 UNIQUE(id,cycle_id,experiment_id,artifact_id,artifact_kind,artifact_version,artifact_hash);

CREATE TABLE record_cycle_transitions (
 id UUID PRIMARY KEY,
 experiment_id UUID NOT NULL,
 cycle_id UUID NOT NULL,
 ordinal INTEGER NOT NULL,
 from_state VARCHAR(32) NOT NULL,
 to_state VARCHAR(32) NOT NULL,
 idea_acceptance_id UUID NOT NULL,
 idea_artifact_id UUID NOT NULL,
 idea_kind VARCHAR(64) NOT NULL,
 idea_version INTEGER NOT NULL,
 idea_hash VARCHAR(64) NOT NULL,
 research_attempt_id UUID NOT NULL,
 command_id UUID NOT NULL,
 created_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(cycle_id,experiment_id)
  REFERENCES record_cycles(id,experiment_id),
 FOREIGN KEY(idea_acceptance_id,cycle_id,experiment_id,idea_artifact_id,idea_kind,idea_version,idea_hash)
  REFERENCES record_idea_acceptances(id,cycle_id,experiment_id,artifact_id,artifact_kind,artifact_version,artifact_hash),
 FOREIGN KEY(research_attempt_id,cycle_id,experiment_id)
  REFERENCES record_research_attempts(id,cycle_id,experiment_id),
 FOREIGN KEY(command_id) REFERENCES record_commands(id),
 UNIQUE(cycle_id,ordinal),
 UNIQUE(research_attempt_id),
 UNIQUE(command_id),
 UNIQUE(id,cycle_id,experiment_id,ordinal,to_state),
 CHECK(ordinal=1 AND from_state='IDEA_REFINEMENT'
  AND to_state='MARKET_RESEARCH' AND idea_kind='IDEA_BRIEF')
);
CREATE INDEX ix_record_cycle_transitions_cycle
 ON record_cycle_transitions(cycle_id,experiment_id);
CREATE INDEX ix_record_cycle_transitions_acceptance
 ON record_cycle_transitions(idea_acceptance_id,cycle_id,experiment_id,idea_artifact_id,idea_kind,idea_version,idea_hash);
CREATE INDEX ix_record_cycle_transitions_attempt
 ON record_cycle_transitions(research_attempt_id,cycle_id,experiment_id);
CREATE INDEX ix_record_cycle_transitions_command
 ON record_cycle_transitions(command_id);

CREATE TABLE record_cycle_states (
 cycle_id UUID PRIMARY KEY,
 experiment_id UUID NOT NULL,
 state VARCHAR(32) NOT NULL,
 transition_ordinal INTEGER NOT NULL,
 last_transition_id UUID,
 updated_at TIMESTAMPTZ NOT NULL,
 FOREIGN KEY(cycle_id,experiment_id)
  REFERENCES record_cycles(id,experiment_id),
 FOREIGN KEY(last_transition_id,cycle_id,experiment_id,transition_ordinal,state)
  REFERENCES record_cycle_transitions(id,cycle_id,experiment_id,ordinal,to_state),
 UNIQUE(cycle_id,experiment_id),
 CHECK((state='IDEA_REFINEMENT' AND transition_ordinal=0 AND last_transition_id IS NULL)
    OR (state='MARKET_RESEARCH' AND transition_ordinal=1 AND last_transition_id IS NOT NULL))
);
CREATE INDEX ix_record_cycle_states_cycle
 ON record_cycle_states(cycle_id,experiment_id);
CREATE INDEX ix_record_cycle_states_transition
 ON record_cycle_states(last_transition_id,cycle_id,experiment_id,transition_ordinal,state);

INSERT INTO record_cycle_states(cycle_id,experiment_id,state,transition_ordinal,last_transition_id,updated_at)
SELECT id,experiment_id,'IDEA_REFINEMENT',0,NULL,created_at FROM record_cycles;

CREATE FUNCTION record_cycle_state_initialize() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO record_cycle_states(cycle_id,experiment_id,state,transition_ordinal,last_transition_id,updated_at)
 VALUES(NEW.id,NEW.experiment_id,'IDEA_REFINEMENT',0,NULL,NEW.created_at);
 RETURN NEW;
END $$;

CREATE FUNCTION record_cycle_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
 current_state record_cycle_states;
 acceptance record_idea_acceptances;
 attempt record_research_attempts;
 accepted_artifact record_artifacts;
 command record_commands;
BEGIN
 IF TG_OP<>'INSERT' THEN
  RAISE EXCEPTION 'immutable cycle transition';
 END IF;
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO current_state FROM record_cycle_states
  WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id FOR UPDATE;
 SELECT * INTO acceptance FROM record_idea_acceptances
  WHERE id=NEW.idea_acceptance_id AND cycle_id=NEW.cycle_id
   AND experiment_id=NEW.experiment_id AND artifact_id=NEW.idea_artifact_id
   AND artifact_kind=NEW.idea_kind AND artifact_version=NEW.idea_version
   AND artifact_hash=NEW.idea_hash;
 SELECT * INTO attempt FROM record_research_attempts
  WHERE id=NEW.research_attempt_id AND cycle_id=NEW.cycle_id
   AND experiment_id=NEW.experiment_id;
 SELECT * INTO accepted_artifact FROM record_artifacts
  WHERE id=NEW.idea_artifact_id AND experiment_id=NEW.experiment_id
   AND kind=NEW.idea_kind AND version=NEW.idea_version
   AND content_hash=NEW.idea_hash;
 SELECT * INTO command FROM record_commands WHERE id=NEW.command_id;
 IF current_state.cycle_id IS NULL
    OR current_state.state IS DISTINCT FROM NEW.from_state
    OR current_state.transition_ordinal+1 IS DISTINCT FROM NEW.ordinal
    OR acceptance.id IS NULL OR attempt.id IS NULL OR accepted_artifact.id IS NULL
    OR attempt.ordinal<>1
    OR NEW.cycle_id IS DISTINCT FROM (
       SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id
       ORDER BY ordinal DESC LIMIT 1)
    OR EXISTS(SELECT 1 FROM record_artifacts later
       WHERE later.logical_id=accepted_artifact.logical_id
        AND later.version>accepted_artifact.version)
    OR EXISTS(SELECT 1 FROM record_artifact_dispositions disposition
       WHERE disposition.artifact_id=accepted_artifact.id
        AND disposition.disposition='SUPERSEDED')
    OR (SELECT count(*) FROM record_artifact_links
        WHERE consumer_id=attempt.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
    OR NOT EXISTS(SELECT 1 FROM record_artifact_links
        WHERE consumer_id=attempt.plan_artifact_id
         AND producer_id=accepted_artifact.id AND role='ACCEPTED_IDEA')
    OR command.id IS NULL OR command.experiment_id IS DISTINCT FROM NEW.experiment_id
    OR command.kind<>'START_MARKET_RESEARCH'
    OR command.result_type<>'RESEARCH_ATTEMPT'
    OR command.result_id IS DISTINCT FROM NEW.research_attempt_id
 THEN RAISE EXCEPTION 'invalid idea-to-research transition'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION record_cycle_state_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'cycle state projection cannot be deleted';
 ELSIF TG_OP='INSERT' THEN
  IF NEW.state<>'IDEA_REFINEMENT' OR NEW.transition_ordinal<>0
     OR NEW.last_transition_id IS NOT NULL
     OR EXISTS(SELECT 1 FROM record_cycle_transitions WHERE cycle_id=NEW.cycle_id)
  THEN RAISE EXCEPTION 'invalid initial cycle state'; END IF;
  RETURN NEW;
 END IF;
 IF OLD.state<>'IDEA_REFINEMENT' OR OLD.transition_ordinal<>0
    OR OLD.last_transition_id IS NOT NULL
    OR NEW.state<>'MARKET_RESEARCH' OR NEW.transition_ordinal<>1
    OR NEW.last_transition_id IS NULL
    OR NOT EXISTS(SELECT 1 FROM record_cycle_transitions transition
       WHERE transition.id=NEW.last_transition_id
        AND transition.cycle_id=NEW.cycle_id
        AND transition.experiment_id=NEW.experiment_id
        AND transition.ordinal=NEW.transition_ordinal
        AND transition.from_state=OLD.state
        AND transition.to_state=NEW.state)
    OR NEW.transition_ordinal IS DISTINCT FROM (
       SELECT max(ordinal) FROM record_cycle_transitions
        WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'cycle state must follow transition history'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION record_cycle_transition_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM record_cycle_states state
  WHERE state.cycle_id=NEW.cycle_id AND state.experiment_id=NEW.experiment_id
   AND state.state=NEW.to_state AND state.transition_ordinal=NEW.ordinal
   AND state.last_transition_id=NEW.id)
 THEN RAISE EXCEPTION 'cycle state projection is inconsistent with history';
 ELSIF NOT EXISTS(SELECT 1 FROM record_audit audit
   WHERE audit.command_id=NEW.command_id
    AND audit.experiment_id=NEW.experiment_id
    AND audit.kind='START_MARKET_RESEARCH'
    AND audit.aggregate_id=NEW.research_attempt_id)
   OR NOT EXISTS(SELECT 1 FROM record_outbox outbox
   WHERE outbox.command_id=NEW.command_id
    AND outbox.experiment_id=NEW.experiment_id
    AND outbox.topic='product-record.start-market-research'
    AND outbox.aggregate_type='RESEARCH_ATTEMPT'
    AND outbox.aggregate_id=NEW.research_attempt_id)
 THEN RAISE EXCEPTION 'missing command audit or outbox'; END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION record_first_attempt_requires_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.ordinal=1 AND NOT EXISTS(SELECT 1 FROM record_cycle_transitions transition
  WHERE transition.research_attempt_id=NEW.id AND transition.cycle_id=NEW.cycle_id
   AND transition.experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'first research attempt requires workflow transition'; END IF;
 RETURN NULL;
END $$;

CREATE TRIGGER record_cycle_state_initialize
 AFTER INSERT ON record_cycles FOR EACH ROW EXECUTE FUNCTION record_cycle_state_initialize();
CREATE TRIGGER record_cycle_transitions_guard
 BEFORE INSERT OR UPDATE OR DELETE ON record_cycle_transitions
 FOR EACH ROW EXECUTE FUNCTION record_cycle_transition_guard();
CREATE TRIGGER record_cycle_states_guard
 BEFORE INSERT OR UPDATE OR DELETE ON record_cycle_states
 FOR EACH ROW EXECUTE FUNCTION record_cycle_state_guard();
CREATE CONSTRAINT TRIGGER record_cycle_transition_consistency
 AFTER INSERT ON record_cycle_transitions DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION record_cycle_transition_consistency();
CREATE CONSTRAINT TRIGGER record_first_attempt_requires_transition
 AFTER INSERT ON record_research_attempts DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION record_first_attempt_requires_transition();
""")


def downgrade() -> None:
    op.execute(r"""
DROP TRIGGER record_first_attempt_requires_transition ON record_research_attempts;
DROP TRIGGER record_cycle_transition_consistency ON record_cycle_transitions;
DROP TRIGGER record_cycle_states_guard ON record_cycle_states;
DROP TRIGGER record_cycle_transitions_guard ON record_cycle_transitions;
DROP TRIGGER record_cycle_state_initialize ON record_cycles;
DROP FUNCTION record_first_attempt_requires_transition();
DROP FUNCTION record_cycle_transition_consistency();
DROP FUNCTION record_cycle_state_guard();
DROP FUNCTION record_cycle_transition_guard();
DROP FUNCTION record_cycle_state_initialize();
DROP TABLE record_cycle_states;
DROP TABLE record_cycle_transitions;
ALTER TABLE record_idea_acceptances
 DROP CONSTRAINT uq_record_idea_acceptance_exact_cycle;
""")
