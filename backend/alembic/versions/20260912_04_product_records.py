"""L03 product roots and immutable idea/research lineage."""

from alembic import op

revision = "20260912_04"
down_revision = "20260912_03"
branch_labels = None
depends_on = None


# Frozen migration definitions; never import mutable application metadata.
TABLE_NAMES = (
    "record_operator_profiles",
    "record_experiments",
    "record_workflows",
    "record_agents",
    "record_artifacts",
    "record_artifact_links",
    "record_source_refs",
    "record_commands",
    "record_audit",
    "record_outbox",
    "record_cycles",
    "record_pivot_decisions",
    "record_idea_acceptances",
    "record_research_attempts",
    "record_verdicts",
    "record_returns",
    "record_artifact_dispositions",
)

TABLE_DDL = r"""
CREATE TABLE record_operator_profiles (
	id UUID NOT NULL,
	version INTEGER NOT NULL,
	operator_id UUID NOT NULL,
	capabilities JSONB NOT NULL,
	constraints JSONB NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id, version),
	CHECK (version > 0)
);

CREATE TABLE record_experiments (
	id UUID NOT NULL,
	operator_profile_id UUID NOT NULL,
	operator_profile_version INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id) REFERENCES gov_experiments (id),
	FOREIGN KEY(operator_profile_id, operator_profile_version) REFERENCES record_operator_profiles (id, version),
	CHECK (length(btrim(name)) BETWEEN 1 AND 120)
);

CREATE INDEX ix_record_experiments_fk_0 ON record_experiments (id);

CREATE INDEX ix_record_experiments_fk_1 ON record_experiments (operator_profile_id, operator_profile_version);

CREATE TABLE record_workflows (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	role VARCHAR(100) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id, experiment_id) REFERENCES gov_workflows (id, experiment_id),
	UNIQUE (id, experiment_id),
	CHECK (role ~ '^[A-Z][A-Z0-9_]{0,99}$')
);

CREATE INDEX ix_record_workflows_fk_0 ON record_workflows (id, experiment_id);

CREATE TABLE record_agents (
	id UUID NOT NULL,
	workflow_id UUID NOT NULL,
	role VARCHAR(100) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(id, workflow_id) REFERENCES gov_agents (id, workflow_id),
	UNIQUE (id, workflow_id),
	CHECK (role ~ '^[A-Z][A-Z0-9_]{0,99}$')
);

CREATE INDEX ix_record_agents_fk_0 ON record_agents (id, workflow_id);

CREATE TABLE record_artifacts (
	id UUID NOT NULL,
	logical_id UUID NOT NULL,
	version INTEGER NOT NULL,
	experiment_id UUID NOT NULL,
	workflow_id UUID,
	agent_id UUID,
	operation_id UUID,
	kind VARCHAR(64) NOT NULL,
	schema_version INTEGER NOT NULL,
	payload JSONB NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(experiment_id) REFERENCES record_experiments (id),
	FOREIGN KEY(workflow_id, experiment_id) REFERENCES record_workflows (id, experiment_id),
	FOREIGN KEY(agent_id, workflow_id) REFERENCES record_agents (id, workflow_id),
	FOREIGN KEY(operation_id, workflow_id, experiment_id) REFERENCES gov_operations (id, workflow_id, experiment_id),
	UNIQUE (id, experiment_id),
	UNIQUE (logical_id, version),
	UNIQUE (id, experiment_id, kind, version, content_hash),
	CHECK (version > 0 AND schema_version=1),
	CHECK (kind IN ('EXPERIMENT_BRIEF','IDEA_SEED','IDEA_CANDIDATE','IDEA_BRIEF','RESEARCH_PLAN','RESEARCH_EVIDENCE','COMPETITOR_PROFILE','SERVICE_PROFILE','PRICE_OBSERVATION','MARKET_RESEARCH_REPORT','MARKET_RESEARCH_RECOMMENDATION','RESEARCH_FEEDBACK_BRIEF','VALIDATION_RESULT','ACCEPTANCE_RECEIPT')),
	CHECK (agent_id IS NULL OR workflow_id IS NOT NULL),
	CHECK (operation_id IS NULL OR workflow_id IS NOT NULL)
);

CREATE INDEX ix_record_artifacts_fk_0 ON record_artifacts (agent_id, workflow_id);

CREATE INDEX ix_record_artifacts_fk_1 ON record_artifacts (experiment_id);

CREATE INDEX ix_record_artifacts_fk_2 ON record_artifacts (operation_id, workflow_id, experiment_id);

CREATE INDEX ix_record_artifacts_fk_3 ON record_artifacts (workflow_id, experiment_id);

CREATE TABLE record_artifact_links (
	consumer_id UUID NOT NULL,
	producer_id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	role VARCHAR(64) NOT NULL,
	producer_kind VARCHAR(64) NOT NULL,
	producer_version INTEGER NOT NULL,
	producer_hash VARCHAR(64) NOT NULL,
	PRIMARY KEY (consumer_id, producer_id, role),
	FOREIGN KEY(consumer_id, experiment_id) REFERENCES record_artifacts (id, experiment_id),
	FOREIGN KEY(producer_id, experiment_id, producer_kind, producer_version, producer_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	CHECK (consumer_id <> producer_id)
);

CREATE INDEX ix_record_artifact_links_fk_0 ON record_artifact_links (consumer_id, experiment_id);

CREATE INDEX ix_record_artifact_links_fk_1 ON record_artifact_links (producer_id, experiment_id, producer_kind, producer_version, producer_hash);

CREATE TABLE record_source_refs (
	id UUID NOT NULL,
	artifact_id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	kind VARCHAR(32) NOT NULL,
	evidence_id UUID,
	retained_id UUID,
	call_id UUID,
	grant_id UUID,
	grant_version INTEGER,
	field VARCHAR,
	expires_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(artifact_id, experiment_id) REFERENCES record_artifacts (id, experiment_id),
	FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id),
	UNIQUE NULLS NOT DISTINCT (artifact_id, kind, evidence_id, retained_id),
	CHECK (kind IN ('RETAINED_CONTENT','GOVERNANCE_EVIDENCE')),
	CHECK ((kind='GOVERNANCE_EVIDENCE' AND evidence_id IS NOT NULL AND retained_id IS NULL AND call_id IS NULL AND grant_id IS NULL AND grant_version IS NULL AND field IS NULL AND expires_at IS NULL) OR (kind='RETAINED_CONTENT' AND evidence_id IS NULL AND retained_id IS NOT NULL AND call_id IS NOT NULL AND grant_id IS NOT NULL AND grant_version IS NOT NULL AND field IS NOT NULL AND expires_at IS NOT NULL))
);

CREATE INDEX ix_record_source_refs_fk_0 ON record_source_refs (artifact_id, experiment_id);

CREATE INDEX ix_record_source_refs_fk_1 ON record_source_refs (evidence_id);

CREATE TABLE record_commands (
	id UUID NOT NULL,
	command_key UUID NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	experiment_id UUID,
	kind VARCHAR(64) NOT NULL,
	result_type VARCHAR(64) NOT NULL,
	result_id UUID NOT NULL,
	issued_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(experiment_id) REFERENCES gov_experiments (id),
	UNIQUE (command_key)
);

CREATE INDEX ix_record_commands_fk_0 ON record_commands (experiment_id);

CREATE TABLE record_audit (
	id UUID NOT NULL,
	command_id UUID NOT NULL,
	experiment_id UUID,
	kind VARCHAR(64) NOT NULL,
	aggregate_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(command_id) REFERENCES record_commands (id),
	FOREIGN KEY(experiment_id) REFERENCES gov_experiments (id),
	UNIQUE (command_id)
);

CREATE INDEX ix_record_audit_fk_0 ON record_audit (command_id);

CREATE INDEX ix_record_audit_fk_1 ON record_audit (experiment_id);

CREATE TABLE record_outbox (
	id UUID NOT NULL,
	command_id UUID NOT NULL,
	experiment_id UUID,
	topic VARCHAR(100) NOT NULL,
	aggregate_type VARCHAR(64) NOT NULL,
	aggregate_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(command_id) REFERENCES record_commands (id),
	FOREIGN KEY(experiment_id) REFERENCES gov_experiments (id),
	UNIQUE (command_id)
);

CREATE INDEX ix_record_outbox_fk_0 ON record_outbox (command_id);

CREATE INDEX ix_record_outbox_fk_1 ON record_outbox (experiment_id);

CREATE TABLE record_cycles (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	parent_cycle_id UUID,
	seed_artifact_id UUID NOT NULL,
	seed_kind VARCHAR(64) NOT NULL,
	seed_version INTEGER NOT NULL,
	seed_hash VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(experiment_id) REFERENCES record_experiments (id),
	FOREIGN KEY(parent_cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(seed_artifact_id, experiment_id, seed_kind, seed_version, seed_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (id, experiment_id),
	UNIQUE (experiment_id, ordinal),
	CHECK (ordinal BETWEEN 1 AND 3 AND seed_kind='IDEA_SEED')
);

CREATE INDEX ix_record_cycles_fk_0 ON record_cycles (experiment_id);

CREATE INDEX ix_record_cycles_fk_1 ON record_cycles (parent_cycle_id, experiment_id);

CREATE INDEX ix_record_cycles_fk_2 ON record_cycles (seed_artifact_id, experiment_id, seed_kind, seed_version, seed_hash);

CREATE TABLE record_pivot_decisions (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	cycle_id UUID NOT NULL,
	artifact_id UUID NOT NULL,
	artifact_kind VARCHAR(64) NOT NULL,
	artifact_version INTEGER NOT NULL,
	artifact_hash VARCHAR(64) NOT NULL,
	approved_by UUID NOT NULL,
	approved_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (cycle_id, artifact_id),
	CHECK (artifact_kind='IDEA_BRIEF')
);

CREATE INDEX ix_record_pivot_decisions_fk_0 ON record_pivot_decisions (artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash);

CREATE INDEX ix_record_pivot_decisions_fk_1 ON record_pivot_decisions (cycle_id, experiment_id);

CREATE TABLE record_idea_acceptances (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	cycle_id UUID NOT NULL,
	artifact_id UUID NOT NULL,
	artifact_kind VARCHAR(64) NOT NULL,
	artifact_version INTEGER NOT NULL,
	artifact_hash VARCHAR(64) NOT NULL,
	pivot_approval_id UUID,
	accepted_by UUID NOT NULL,
	accepted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	FOREIGN KEY(pivot_approval_id) REFERENCES record_pivot_decisions (id),
	UNIQUE (cycle_id),
	UNIQUE (artifact_id),
	CHECK (artifact_kind='IDEA_BRIEF')
);

CREATE INDEX ix_record_idea_acceptances_fk_0 ON record_idea_acceptances (artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash);

CREATE INDEX ix_record_idea_acceptances_fk_1 ON record_idea_acceptances (cycle_id, experiment_id);

CREATE INDEX ix_record_idea_acceptances_fk_2 ON record_idea_acceptances (pivot_approval_id);

CREATE TABLE record_research_attempts (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	cycle_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	plan_artifact_id UUID NOT NULL,
	plan_kind VARCHAR(64) NOT NULL,
	plan_version INTEGER NOT NULL,
	plan_hash VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(plan_artifact_id, experiment_id, plan_kind, plan_version, plan_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (id, cycle_id, experiment_id),
	UNIQUE (cycle_id, ordinal),
	UNIQUE (plan_artifact_id),
	CHECK (ordinal BETWEEN 1 AND 3 AND plan_kind='RESEARCH_PLAN')
);

CREATE INDEX ix_record_research_attempts_fk_0 ON record_research_attempts (cycle_id, experiment_id);

CREATE INDEX ix_record_research_attempts_fk_1 ON record_research_attempts (plan_artifact_id, experiment_id, plan_kind, plan_version, plan_hash);

CREATE TABLE record_verdicts (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	cycle_id UUID NOT NULL,
	attempt_id UUID NOT NULL,
	report_artifact_id UUID NOT NULL,
	report_kind VARCHAR(64) NOT NULL,
	report_version INTEGER NOT NULL,
	report_hash VARCHAR(64) NOT NULL,
	recommendation_artifact_id UUID NOT NULL,
	recommendation_kind VARCHAR(64) NOT NULL,
	recommendation_version INTEGER NOT NULL,
	recommendation_hash VARCHAR(64) NOT NULL,
	verdict VARCHAR(32) NOT NULL,
	committed_by UUID NOT NULL,
	committed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(attempt_id, cycle_id, experiment_id) REFERENCES record_research_attempts (id, cycle_id, experiment_id),
	FOREIGN KEY(report_artifact_id, experiment_id, report_kind, report_version, report_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	FOREIGN KEY(recommendation_artifact_id, experiment_id, recommendation_kind, recommendation_version, recommendation_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (id, experiment_id),
	UNIQUE (cycle_id),
	UNIQUE (attempt_id),
	UNIQUE (report_artifact_id),
	UNIQUE (recommendation_artifact_id),
	CHECK (verdict IN ('PROCEED_TO_OFFER','REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED','KILL_IDEA','INCONCLUSIVE')),
	CHECK (report_kind='MARKET_RESEARCH_REPORT' AND recommendation_kind='MARKET_RESEARCH_RECOMMENDATION')
);

CREATE INDEX ix_record_verdicts_fk_0 ON record_verdicts (attempt_id, cycle_id, experiment_id);

CREATE INDEX ix_record_verdicts_fk_1 ON record_verdicts (recommendation_artifact_id, experiment_id, recommendation_kind, recommendation_version, recommendation_hash);

CREATE INDEX ix_record_verdicts_fk_2 ON record_verdicts (report_artifact_id, experiment_id, report_kind, report_version, report_hash);

CREATE TABLE record_returns (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	from_cycle_id UUID NOT NULL,
	verdict_id UUID NOT NULL,
	to_cycle_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	feedback_artifact_id UUID NOT NULL,
	feedback_kind VARCHAR(64) NOT NULL,
	feedback_version INTEGER NOT NULL,
	feedback_hash VARCHAR(64) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(from_cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(verdict_id, experiment_id) REFERENCES record_verdicts (id, experiment_id),
	FOREIGN KEY(to_cycle_id, experiment_id) REFERENCES record_cycles (id, experiment_id),
	FOREIGN KEY(feedback_artifact_id, experiment_id, feedback_kind, feedback_version, feedback_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (verdict_id),
	UNIQUE (to_cycle_id),
	UNIQUE (experiment_id, ordinal),
	CHECK (ordinal BETWEEN 1 AND 2 AND feedback_kind='RESEARCH_FEEDBACK_BRIEF')
);

CREATE INDEX ix_record_returns_fk_0 ON record_returns (feedback_artifact_id, experiment_id, feedback_kind, feedback_version, feedback_hash);

CREATE INDEX ix_record_returns_fk_1 ON record_returns (from_cycle_id, experiment_id);

CREATE INDEX ix_record_returns_fk_2 ON record_returns (to_cycle_id, experiment_id);

CREATE INDEX ix_record_returns_fk_3 ON record_returns (verdict_id, experiment_id);

CREATE TABLE record_artifact_dispositions (
	id UUID NOT NULL,
	experiment_id UUID NOT NULL,
	artifact_id UUID NOT NULL,
	artifact_kind VARCHAR(64) NOT NULL,
	artifact_version INTEGER NOT NULL,
	artifact_hash VARCHAR(64) NOT NULL,
	validation_artifact_id UUID,
	validation_kind VARCHAR(64),
	validation_version INTEGER,
	validation_hash VARCHAR(64),
	disposition VARCHAR(16) NOT NULL,
	decided_by UUID NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	FOREIGN KEY(validation_artifact_id, experiment_id, validation_kind, validation_version, validation_hash) REFERENCES record_artifacts (id, experiment_id, kind, version, content_hash),
	UNIQUE (artifact_id, disposition),
	CHECK (disposition IN ('VALIDATED','ACCEPTED','REJECTED','SUPERSEDED')),
	CHECK ((disposition IN ('VALIDATED','ACCEPTED') AND validation_artifact_id IS NOT NULL AND validation_kind='VALIDATION_RESULT' AND validation_version IS NOT NULL AND validation_hash IS NOT NULL) OR (disposition IN ('REJECTED','SUPERSEDED') AND validation_artifact_id IS NULL AND validation_kind IS NULL AND validation_version IS NULL AND validation_hash IS NULL))
);

CREATE INDEX ix_record_artifact_dispositions_fk_0 ON record_artifact_dispositions (artifact_id, experiment_id, artifact_kind, artifact_version, artifact_hash);

CREATE INDEX ix_record_artifact_dispositions_fk_1 ON record_artifact_dispositions (validation_artifact_id, experiment_id, validation_kind, validation_version, validation_hash);
"""


def upgrade() -> None:
    op.execute(TABLE_DDL)
    op.execute(
        r"""
CREATE FUNCTION record_json_exact(value jsonb, keys text[]) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(value)='object' AND value ?& keys AND value-keys='{}'::jsonb,false)
$$;
CREATE FUNCTION record_nonempty_text(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(value)='string' AND length(btrim(value#>>'{}')) BETWEEN 1 AND 4000,false)
$$;
CREATE FUNCTION record_nonempty_text_array(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(value)='array' AND jsonb_array_length(value)>0
   AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(value) item WHERE NOT record_nonempty_text(item)),false)
$$;
CREATE FUNCTION record_payload_valid(kind text, value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE kind
  WHEN 'EXPERIMENT_BRIEF' THEN record_json_exact(value,ARRAY['objective']) AND record_nonempty_text(value->'objective')
  WHEN 'IDEA_SEED' THEN record_json_exact(value,ARRAY['origin','statement']) AND value->>'origin' IN ('USER_SUPPLIED','AGENT_DISCOVERED') AND record_nonempty_text(value->'statement')
  WHEN 'IDEA_CANDIDATE' THEN record_json_exact(value,ARRAY['title','hypothesis']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'hypothesis')
  WHEN 'IDEA_BRIEF' THEN record_json_exact(value,ARRAY['title','customer','problem','core_intent','material_pivot']) AND record_nonempty_text(value->'title') AND record_nonempty_text(value->'customer') AND record_nonempty_text(value->'problem') AND record_nonempty_text(value->'core_intent') AND jsonb_typeof(value->'material_pivot')='boolean'
  WHEN 'RESEARCH_PLAN' THEN record_json_exact(value,ARRAY['questions','method']) AND record_nonempty_text_array(value->'questions') AND record_nonempty_text(value->'method')
  WHEN 'RESEARCH_EVIDENCE' THEN record_json_exact(value,ARRAY['claim','finding']) AND record_nonempty_text(value->'claim') AND record_nonempty_text(value->'finding')
  WHEN 'COMPETITOR_PROFILE' THEN record_json_exact(value,ARRAY['name','positioning']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'positioning')
  WHEN 'SERVICE_PROFILE' THEN record_json_exact(value,ARRAY['name','scope']) AND record_nonempty_text(value->'name') AND record_nonempty_text(value->'scope')
  WHEN 'PRICE_OBSERVATION' THEN record_json_exact(value,ARRAY['status','currency','amount','unit','source_note']) AND record_nonempty_text(value->'unit') AND record_nonempty_text(value->'source_note') AND ((value->>'status'='QUOTED' AND value->>'currency' ~ '^[A-Z]{3}$' AND value->>'amount' ~ '^[0-9]+(\.[0-9]{1,6})?$' AND (value->>'amount')::numeric>0 AND (value->>'amount')::numeric<1000000000000) OR (value->>'status'='REQUIRED_UNAVAILABLE' AND value->'currency'='null'::jsonb AND value->'amount'='null'::jsonb))
  WHEN 'MARKET_RESEARCH_REPORT' THEN record_json_exact(value,ARRAY['finding','limitations']) AND record_nonempty_text(value->'finding') AND record_nonempty_text_array(value->'limitations')
  WHEN 'MARKET_RESEARCH_RECOMMENDATION' THEN record_json_exact(value,ARRAY['recommendation','rationale']) AND value->>'recommendation' IN ('PROCEED_TO_OFFER','REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED','KILL_IDEA','INCONCLUSIVE') AND record_nonempty_text(value->'rationale')
  WHEN 'RESEARCH_FEEDBACK_BRIEF' THEN record_json_exact(value,ARRAY['preserve','change']) AND record_nonempty_text_array(value->'preserve') AND record_nonempty_text_array(value->'change')
  WHEN 'VALIDATION_RESULT' THEN record_json_exact(value,ARRAY['validator','disposition','reason']) AND record_nonempty_text(value->'validator') AND value->>'disposition' IN ('PASS','FAIL') AND record_nonempty_text(value->'reason')
  WHEN 'ACCEPTANCE_RECEIPT' THEN record_json_exact(value,ARRAY['disposition','reason']) AND value->>'disposition' IN ('ACCEPTED','REJECTED','SUPERSEDED') AND record_nonempty_text(value->'reason')
  ELSE false END
$$;
CREATE FUNCTION record_lineage_closed(target uuid, scope uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
 WITH RECURSIVE authoritative(id) AS (
  SELECT artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND disposition IN ('ACCEPTED','VALIDATED')
  UNION SELECT validation_artifact_id FROM record_artifact_dispositions WHERE experiment_id=scope AND validation_artifact_id IS NOT NULL
  UNION SELECT seed_artifact_id FROM record_cycles WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_idea_acceptances WHERE experiment_id=scope
  UNION SELECT artifact_id FROM record_pivot_decisions WHERE experiment_id=scope
  UNION SELECT plan_artifact_id FROM record_research_attempts WHERE experiment_id=scope
  UNION SELECT report_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT recommendation_artifact_id FROM record_verdicts WHERE experiment_id=scope
  UNION SELECT feedback_artifact_id FROM record_returns WHERE experiment_id=scope
 ), lineage(id) AS (
  SELECT id FROM authoritative
  UNION
  SELECT link.producer_id FROM record_artifact_links link JOIN lineage ON lineage.id=link.consumer_id WHERE link.experiment_id=scope
 ) SELECT EXISTS(SELECT 1 FROM lineage WHERE id=target)
$$;
CREATE FUNCTION record_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a record_artifacts; c record_cycles; parent_idea record_artifacts;
        decision record_pivot_decisions; proof gov_evidence; retained gov_retained;
        call gov_calls; validation record_artifacts; recommendation record_artifacts;
        committed record_verdicts; attempt record_research_attempts; parent_cycle record_cycles;
BEGIN
 IF TG_OP='UPDATE' OR TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable product record' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME<>'record_operator_profiles' AND to_jsonb(NEW)->>'experiment_id' IS NOT NULL THEN
  PERFORM 1 FROM gov_experiments WHERE id=(to_jsonb(NEW)->>'experiment_id')::uuid FOR UPDATE;
 END IF;
 IF TG_TABLE_NAME='record_operator_profiles' THEN
  NEW.content_hash:=encode(sha256(convert_to(NEW.capabilities::text || E'\n' || NEW.constraints::text, 'UTF8')), 'hex');
  IF jsonb_typeof(NEW.capabilities)<>'array' OR jsonb_array_length(NEW.capabilities)=0
     OR jsonb_typeof(NEW.constraints)<>'array' OR jsonb_array_length(NEW.constraints)=0
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.capabilities) x WHERE NOT record_nonempty_text(x))
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(NEW.constraints) x WHERE NOT record_nonempty_text(x))
     OR jsonb_array_length(NEW.capabilities)<>(SELECT count(DISTINCT x) FROM jsonb_array_elements(NEW.capabilities) x)
     OR jsonb_array_length(NEW.constraints)<>(SELECT count(DISTINCT x) FROM jsonb_array_elements(NEW.constraints) x)
  THEN RAISE EXCEPTION 'invalid operator profile'; END IF;
 ELSIF TG_TABLE_NAME='record_artifacts' THEN
  NEW.content_hash:=encode(sha256(convert_to(NEW.payload::text, 'UTF8')), 'hex');
  IF record_payload_valid(NEW.kind,NEW.payload) IS NOT TRUE THEN RAISE EXCEPTION 'invalid artifact payload'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_links' THEN
  IF record_lineage_closed(NEW.consumer_id,NEW.experiment_id)
  THEN RAISE EXCEPTION 'accepted artifact lineage is closed'; END IF;
 ELSIF TG_TABLE_NAME='record_source_refs' THEN
  IF record_lineage_closed(NEW.artifact_id,NEW.experiment_id)
  THEN RAISE EXCEPTION 'accepted artifact lineage is closed'; END IF;
  IF NEW.kind='GOVERNANCE_EVIDENCE' THEN
   SELECT * INTO proof FROM gov_evidence WHERE id=NEW.evidence_id;
   IF NOT FOUND OR (proof.call_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM gov_calls WHERE id=proof.call_id AND experiment_id=NEW.experiment_id))
   THEN RAISE EXCEPTION 'invalid evidence scope'; END IF;
  ELSE
   SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
   SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
   IF retained.id IS NULL OR call.id IS NULL OR retained.call_id IS DISTINCT FROM NEW.call_id OR retained.grant_id IS DISTINCT FROM NEW.grant_id
      OR retained.grant_version IS DISTINCT FROM NEW.grant_version OR retained.field IS DISTINCT FROM NEW.field
      OR retained.expires_at IS DISTINCT FROM NEW.expires_at OR call.experiment_id IS DISTINCT FROM NEW.experiment_id
   THEN RAISE EXCEPTION 'invalid retained source scope'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_cycles' THEN
  IF NEW.ordinal <> (SELECT count(*)+1 FROM record_cycles WHERE experiment_id=NEW.experiment_id)
  THEN RAISE EXCEPTION 'noncontiguous research cycle'; END IF;
  IF NEW.ordinal=1 THEN
   IF NEW.parent_cycle_id IS NOT NULL THEN RAISE EXCEPTION 'initial cycle cannot have a parent'; END IF;
  ELSE
   SELECT * INTO parent_cycle FROM record_cycles WHERE id=NEW.parent_cycle_id AND experiment_id=NEW.experiment_id;
   IF parent_cycle.id IS NULL OR parent_cycle.ordinal<>NEW.ordinal-1
      OR ROW(NEW.seed_artifact_id,NEW.seed_kind,NEW.seed_version,NEW.seed_hash)
         IS DISTINCT FROM ROW(parent_cycle.seed_artifact_id,parent_cycle.seed_kind,parent_cycle.seed_version,parent_cycle.seed_hash)
   THEN RAISE EXCEPTION 'research cycle must preserve original seed and exact parent'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_pivot_decisions' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF a.payload->'material_pivot'<>'true'::jsonb OR c.parent_cycle_id IS NULL OR NOT EXISTS(
    SELECT 1 FROM record_experiments e JOIN record_operator_profiles p
      ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version
    WHERE e.id=NEW.experiment_id AND p.operator_id=NEW.approved_by
      AND p.capabilities @> '["MATERIAL_PIVOT_APPROVAL"]'::jsonb)
  THEN RAISE EXCEPTION 'invalid material pivot approval'; END IF;
 ELSIF TG_TABLE_NAME='record_idea_acceptances' THEN
  SELECT * INTO a FROM record_artifacts WHERE id=NEW.artifact_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.cycle_id;
  IF c.parent_cycle_id IS NOT NULL THEN
   SELECT prior_artifact.* INTO parent_idea FROM record_idea_acceptances prior
    JOIN record_artifacts prior_artifact ON prior_artifact.id=prior.artifact_id
    WHERE prior.cycle_id=c.parent_cycle_id;
   SELECT prior_verdict.* INTO committed FROM record_returns r
    JOIN record_verdicts prior_verdict ON prior_verdict.id=r.verdict_id
    WHERE r.to_cycle_id=NEW.cycle_id;
  END IF;
  IF c.parent_cycle_id IS NOT NULL AND parent_idea.id IS NULL THEN RAISE EXCEPTION 'missing parent accepted idea'; END IF;
  IF NOT EXISTS(
    SELECT 1 FROM record_experiments e JOIN record_operator_profiles p
      ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version
    WHERE e.id=NEW.experiment_id AND p.operator_id=NEW.accepted_by
      AND p.capabilities @> '["RESEARCH_REVIEW"]'::jsonb)
  THEN RAISE EXCEPTION 'idea acceptance requires operator capability'; END IF;
  IF committed.verdict='MATERIAL_PIVOT_RECOMMENDED' AND parent_idea.payload->>'core_intent' IS NOT DISTINCT FROM a.payload->>'core_intent'
  THEN RAISE EXCEPTION 'material pivot must change core intent'; END IF;
  IF c.parent_cycle_id IS NOT NULL AND parent_idea.payload->>'core_intent' IS DISTINCT FROM a.payload->>'core_intent' THEN
   IF a.payload->'material_pivot'<>'true'::jsonb OR NEW.pivot_approval_id IS NULL THEN RAISE EXCEPTION 'material pivot requires approval'; END IF;
  ELSIF a.payload->'material_pivot'='true'::jsonb OR NEW.pivot_approval_id IS NOT NULL THEN
   RAISE EXCEPTION 'invalid pivot classification';
  END IF;
  IF NEW.pivot_approval_id IS NOT NULL THEN
   SELECT * INTO decision FROM record_pivot_decisions WHERE id=NEW.pivot_approval_id;
   IF decision.cycle_id IS DISTINCT FROM NEW.cycle_id OR decision.artifact_id IS DISTINCT FROM NEW.artifact_id OR decision.approved_by IS DISTINCT FROM NEW.accepted_by
   THEN RAISE EXCEPTION 'invalid pivot approval binding'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_research_attempts' THEN
  IF NOT EXISTS(SELECT 1 FROM record_idea_acceptances WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
     OR EXISTS(SELECT 1 FROM record_verdicts WHERE cycle_id=NEW.cycle_id)
     OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
     OR NEW.ordinal <> (SELECT count(*)+1 FROM record_research_attempts WHERE cycle_id=NEW.cycle_id)
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.plan_artifact_id AND role='ACCEPTED_IDEA')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links link JOIN record_idea_acceptances idea ON idea.artifact_id=link.producer_id
         WHERE link.consumer_id=NEW.plan_artifact_id AND link.role='ACCEPTED_IDEA' AND idea.cycle_id=NEW.cycle_id)
  THEN RAISE EXCEPTION 'research attempt requires current accepted idea and exact plan lineage'; END IF;
 ELSIF TG_TABLE_NAME='record_verdicts' THEN
  SELECT * INTO attempt FROM record_research_attempts WHERE id=NEW.attempt_id;
  IF attempt.id IS NULL
     OR NOT EXISTS(SELECT 1 FROM record_idea_acceptances WHERE cycle_id=NEW.cycle_id AND experiment_id=NEW.experiment_id)
     OR NEW.cycle_id IS DISTINCT FROM (SELECT id FROM record_cycles WHERE experiment_id=NEW.experiment_id ORDER BY ordinal DESC LIMIT 1)
     OR attempt.ordinal IS DISTINCT FROM (SELECT max(ordinal) FROM record_research_attempts WHERE cycle_id=NEW.cycle_id)
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.report_artifact_id AND role='PLAN')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.report_artifact_id AND producer_id=attempt.plan_artifact_id AND role='PLAN')
     OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=NEW.recommendation_artifact_id AND role='REPORT')<>1
     OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=NEW.recommendation_artifact_id AND producer_id=NEW.report_artifact_id AND role='REPORT')
  THEN RAISE EXCEPTION 'verdict requires current attempt and exact report lineage'; END IF;
  SELECT * INTO recommendation FROM record_artifacts WHERE id=NEW.recommendation_artifact_id;
  IF recommendation.payload->>'recommendation' IS DISTINCT FROM NEW.verdict OR NOT EXISTS(
    SELECT 1 FROM record_experiments e JOIN record_operator_profiles p
      ON p.id=e.operator_profile_id AND p.version=e.operator_profile_version
    WHERE e.id=NEW.experiment_id AND p.operator_id=NEW.committed_by
      AND p.capabilities @> '["RESEARCH_REVIEW"]'::jsonb)
  THEN RAISE EXCEPTION 'verdict recommendation or operator mismatch'; END IF;
 ELSIF TG_TABLE_NAME='record_returns' THEN
  SELECT * INTO committed FROM record_verdicts WHERE id=NEW.verdict_id;
  SELECT * INTO c FROM record_cycles WHERE id=NEW.to_cycle_id;
  IF committed.id IS NULL OR c.id IS NULL OR committed.cycle_id IS DISTINCT FROM NEW.from_cycle_id OR committed.verdict NOT IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED')
     OR c.parent_cycle_id IS DISTINCT FROM NEW.from_cycle_id OR c.ordinal<>NEW.ordinal+1
     OR NEW.ordinal IS DISTINCT FROM (SELECT ordinal FROM record_cycles WHERE id=NEW.from_cycle_id)
  THEN RAISE EXCEPTION 'invalid research return'; END IF;
 ELSIF TG_TABLE_NAME='record_artifact_dispositions' THEN
  IF NEW.disposition IN ('VALIDATED','ACCEPTED') THEN
   SELECT * INTO validation FROM record_artifacts WHERE id=NEW.validation_artifact_id AND experiment_id=NEW.experiment_id;
   IF validation.kind IS DISTINCT FROM 'VALIDATION_RESULT' OR validation.payload->>'disposition' IS DISTINCT FROM 'PASS'
      OR (SELECT count(*) FROM record_artifact_links WHERE consumer_id=validation.id AND role='TARGET')<>1
      OR NOT EXISTS(SELECT 1 FROM record_artifact_links WHERE consumer_id=validation.id AND role='TARGET'
          AND producer_id=NEW.artifact_id AND producer_kind=NEW.artifact_kind
          AND producer_version=NEW.artifact_version AND producer_hash=NEW.artifact_hash)
   THEN RAISE EXCEPTION 'passing validation required'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_cycle_return_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.ordinal>1 AND NOT EXISTS(
  SELECT 1 FROM record_returns r JOIN record_verdicts v ON v.id=r.verdict_id
  WHERE r.to_cycle_id=NEW.id AND r.from_cycle_id=NEW.parent_cycle_id
    AND r.experiment_id=NEW.experiment_id AND r.ordinal=NEW.ordinal-1
    AND v.cycle_id=NEW.parent_cycle_id AND v.verdict IN ('REFINE_SAME_IDEA','MATERIAL_PIVOT_RECOMMENDED'))
 THEN RAISE EXCEPTION 'research cycle requires exact committed return'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION record_artifact_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.version=1 THEN
  IF EXISTS(SELECT 1 FROM record_artifacts WHERE logical_id=NEW.logical_id AND version<>1)
  THEN RAISE EXCEPTION 'invalid initial artifact version'; END IF;
 ELSIF NOT EXISTS(
   SELECT 1 FROM record_artifact_links link
   JOIN record_artifacts prior ON prior.id=link.producer_id
   WHERE link.consumer_id=NEW.id AND link.role='SUPERSEDES'
     AND prior.logical_id=NEW.logical_id AND prior.version=NEW.version-1
     AND prior.experiment_id=NEW.experiment_id)
 THEN RAISE EXCEPTION 'missing exact artifact predecessor';
 END IF;
 RETURN NULL;
END $$;
"""
    )
    for table_name in TABLE_NAMES:
        op.execute(
            f"CREATE TRIGGER {table_name}_guard BEFORE INSERT OR UPDATE OR DELETE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION record_guard()"
        )
    op.execute(
        "CREATE CONSTRAINT TRIGGER record_cycle_return_guard "
        "AFTER INSERT ON record_cycles DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION record_cycle_return_guard()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER record_artifact_version_guard "
        "AFTER INSERT ON record_artifacts DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION record_artifact_version_guard()"
    )


def downgrade() -> None:
    for table_name in reversed(TABLE_NAMES):
        op.drop_table(table_name)
    op.execute("DROP FUNCTION record_guard()")
    op.execute("DROP FUNCTION record_lineage_closed(uuid,uuid)")
    op.execute("DROP FUNCTION record_cycle_return_guard()")
    op.execute("DROP FUNCTION record_artifact_version_guard()")
    op.execute("DROP FUNCTION record_payload_valid(text,jsonb)")
    op.execute("DROP FUNCTION record_nonempty_text_array(jsonb)")
    op.execute("DROP FUNCTION record_nonempty_text(jsonb)")
    op.execute("DROP FUNCTION record_json_exact(jsonb,text[])")
