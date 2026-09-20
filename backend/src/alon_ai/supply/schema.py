"""Normalized L02 supply roots. Frozen DDL is retained in its own migration."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    UniqueConstraint,
    column,
    text,
)
from sqlalchemy import (
    table as sql_table,
)
from sqlalchemy.dialects.postgresql import JSONB

from alon_ai.accounting.schema import T, U, col, enumcheck, metadata


def table(name, *columns):
    return Table("supply_" + name, metadata, *columns)


def exp_fk():
    return ForeignKeyConstraint(["experiment_id"], ["gov_experiments.id"])


references = table(
    "references",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("kind", String),
    col("definition", String),
    col("dimension", String, nullable=True),
    col("mode", String),
    col("registered_by", U),
    exp_fk(),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint(
        "experiment_id",
        "kind",
        "dimension",
        "definition",
        postgresql_nulls_not_distinct=True,
    ),
    enumcheck(
        "kind",
        ["FILTER", "VERIFICATION_POLICY", "QUALIFICATION_RULE", "INDEPENDENT_SOURCE"],
    ),
    enumcheck("dimension", ["SOURCE", "QUERY", "CATEGORY", "GEOGRAPHY", "TRAIT"]),
    enumcheck("mode", ["SYNTHETIC", "TRUSTED_REFERENCE"]),
    CheckConstraint(
        "definition ~ '^[a-z0-9][a-z0-9 _-]{0,199}$' AND definition = btrim(regexp_replace(definition, ' +', ' ', 'g'))"
    ),
    CheckConstraint("(kind='FILTER') = (dimension IS NOT NULL)"),
)
plans = table(
    "plans",
    col("experiment_id", U, primary_key=True),
    col("initial_plan", JSONB),
    col("allowed", JSONB),
    col("verification_policy_id", U),
    col("deadline", T),
    col("state", String, server_default="ACTIVE"),
    col("qualified_contactable_target", Integer, server_default="50"),
    col("candidate_batch_size", Integer, server_default="100"),
    col("max_total_discovery_batches", Integer, server_default="3"),
    exp_fk(),
    ForeignKeyConstraint(
        ["verification_policy_id", "experiment_id"],
        ["supply_references.id", "supply_references.experiment_id"],
    ),
    CheckConstraint(
        "qualified_contactable_target=50 AND candidate_batch_size=100 AND max_total_discovery_batches=3"
    ),
    enumcheck(
        "state",
        [
            "ACTIVE",
            "TARGET_50_REACHED",
            "EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2",
            "QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3",
            "CANCELLED",
            "BUDGET_EXHAUSTED",
            "DEADLINE_EXHAUSTED",
            "SOURCE_FAILURE",
            "PROVIDER_FAILURE",
            "SEARCH_EXHAUSTED",
            "SAFETY_STOP",
        ],
    ),
)
identities = table(
    "identities",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("provenance_ref", U),
    col("normalized_key", String),
    col("mode", String),
    col("registered_by", U),
    col("observed_at", T),
    col("valid_until", T),
    exp_fk(),
    ForeignKeyConstraint(
        ["provenance_ref", "experiment_id"],
        ["supply_references.id", "supply_references.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("experiment_id", "normalized_key"),
    CheckConstraint("normalized_key ~ '^[a-z0-9][a-z0-9_-]{0,127}$'"),
    CheckConstraint("observed_at < valid_until"),
    enumcheck("mode", ["SYNTHETIC", "TRUSTED_REFERENCE"]),
)
facts = table(
    "facts",
    col("id", U, primary_key=True),
    col("identity_id", U),
    col("experiment_id", U),
    col("kind", String),
    col("mode", String),
    col("registered_by", U),
    col("observed_at", T),
    col("valid_until", T),
    col("contact_ref", U, nullable=True),
    col("policy_ref", U, nullable=True),
    ForeignKeyConstraint(
        ["identity_id", "experiment_id"],
        ["supply_identities.id", "supply_identities.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["policy_ref", "experiment_id"],
        ["supply_references.id", "supply_references.experiment_id"],
    ),
    UniqueConstraint("id", "identity_id", "experiment_id"),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint("observed_at < valid_until"),
    enumcheck("mode", ["SYNTHETIC", "TRUSTED_REFERENCE"]),
    enumcheck(
        "kind",
        [
            "IDENTITY_CLEAR",
            "IDENTITY_EXCLUDED",
            "SOURCE_EMAIL",
            "EMAIL_ABSENT",
            "SOURCE_FAILURE",
            "VERIFIED",
            "VERIFICATION_REJECTED",
            "QUALIFIED",
            "REJECTED_FIT",
            "REJECTED_EVIDENCE",
        ],
    ),
    CheckConstraint(
        "(kind IN ('SOURCE_EMAIL','VERIFIED','VERIFICATION_REJECTED')) = (contact_ref IS NOT NULL)"
    ),
    CheckConstraint(
        "(kind IN ('VERIFIED','VERIFICATION_REJECTED','QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE')) = (policy_ref IS NOT NULL)"
    ),
)
# Contact reference is the source fact's own ID, not an unbound caller UUID. The
# composite self FK binds verification to that source and its same identity.
facts.append_constraint(
    ForeignKeyConstraint(
        ["contact_ref", "identity_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.identity_id", "supply_facts.experiment_id"],
        deferrable=True,
        initially="DEFERRED",
    )
)
batches = table(
    "batches",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("slot", Integer),
    col("command_key", U, unique=True),
    col("plan", JSONB),
    col("feedback_id", U, nullable=True),
    col("stage", String, server_default="CONTACT"),
    col("started_at", T, server_default=text("CURRENT_TIMESTAMP")),
    col("completed_at", T, nullable=True),
    ForeignKeyConstraint(["experiment_id"], ["supply_plans.experiment_id"]),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("experiment_id", "slot"),
    CheckConstraint("slot BETWEEN 1 AND 3"),
    CheckConstraint("(slot=1) = (feedback_id IS NULL)"),
    enumcheck(
        "stage",
        [
            "CONTACT",
            "EMAIL_RETRY_READY",
            "QUALIFICATION",
            "QUALIFICATION_RETRY_READY",
            "DONE",
        ],
    ),
)
candidates = table(
    "candidates",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("batch_id", U),
    col("identity_id", U),
    col("clearance_id", U),
    col("command_key", U, unique=True),
    col("ordinal", Integer),
    col("observations", JSONB),
    col("deep_started", Boolean, server_default="false"),
    col("stopped", Boolean, server_default="false"),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["clearance_id", "identity_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.identity_id", "supply_facts.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("id", "batch_id", "experiment_id"),
    UniqueConstraint("experiment_id", "identity_id"),
    UniqueConstraint("batch_id", "ordinal"),
    CheckConstraint("ordinal BETWEEN 1 AND 100"),
)
contacts = table(
    "contacts",
    col("candidate_id", U, primary_key=True),
    col("experiment_id", U),
    col("source_id", U),
    col("verification_id", U, nullable=True),
    col("outcome", String),
    col("resolved_at", T),
    col("valid_until", T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["verification_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    enumcheck(
        "outcome",
        [
            "SUPPORTED",
            "EMAIL_NOT_FOUND",
            "VERIFICATION_REJECTED",
            "IDENTITY_EXCLUDED",
            "SOURCE_FAILURE",
        ],
    ),
)
contact_failures = table(
    "contact_failures",
    col("source_id", U, primary_key=True),
    col("candidate_id", U),
    col("experiment_id", U),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
)

qualifications = table(
    "qualifications",
    col("candidate_id", U, primary_key=True),
    col("experiment_id", U),
    col("fact_id", U, unique=True),
    col("accepted_at", T),
    col("outcome", String),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["fact_id", "experiment_id"], ["supply_facts.id", "supply_facts.experiment_id"]
    ),
    UniqueConstraint("candidate_id", "experiment_id", "fact_id"),
    enumcheck("outcome", ["QUALIFIED", "REJECTED_FIT", "REJECTED_EVIDENCE"]),
)
feedback = table(
    "feedback",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("batch_id", U),
    col("gate", String),
    col("payload", JSONB),
    col("created_at", T, server_default=text("CURRENT_TIMESTAMP")),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id"),
    UniqueConstraint("batch_id", "gate"),
    enumcheck("gate", ["EMAIL", "QUALIFICATION"]),
)
batches.append_constraint(
    ForeignKeyConstraint(
        ["feedback_id", "experiment_id"],
        ["supply_feedback.id", "supply_feedback.experiment_id"],
        name="fk_supply_batch_feedback",
        use_alter=True,
    )
)
closures = table(
    "closures",
    col("command_key", U, primary_key=True),
    col("experiment_id", U),
    col("batch_id", U),
    col("gate", String),
    col("feedback_id", U, nullable=True),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["feedback_id", "experiment_id"],
        ["supply_feedback.id", "supply_feedback.experiment_id"],
    ),
    UniqueConstraint("batch_id", "gate"),
    enumcheck("gate", ["EMAIL", "QUALIFICATION"]),
)
operations = table(
    "operations",
    col("operation_id", U, primary_key=True),
    col("experiment_id", U),
    col("workflow_id", U),
    col("config_id", U),
    col("config_version", U),
    col("batch_id", U),
    col("candidate_id", U, nullable=True),
    col("kind", String),
    ForeignKeyConstraint(
        ["operation_id", "workflow_id", "experiment_id", "config_version"],
        [
            "gov_operations.id",
            "gov_operations.workflow_id",
            "gov_operations.experiment_id",
            "gov_operations.config_version",
        ],
    ),
    ForeignKeyConstraint(
        ["config_id", "workflow_id", "config_version"],
        ["gov_configs.id", "gov_configs.workflow_id", "gov_configs.version"],
    ),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    enumcheck("kind", ["DISCOVERY", "CONTACT", "DEEP"]),
    CheckConstraint("(kind='DISCOVERY') = (candidate_id IS NULL)"),
)
outcomes = table(
    "outcomes",
    col("experiment_id", U, primary_key=True),
    col("command_key", U, unique=True),
    col("reason", String),
    col("achieved", Integer),
    col("batches_used", Integer),
    col("businesses_discovered", Integer),
    col("recorded_at", T, server_default=text("CURRENT_TIMESTAMP")),
    ForeignKeyConstraint(["experiment_id"], ["supply_plans.experiment_id"]),
    CheckConstraint(
        "achieved BETWEEN 0 AND 50 AND batches_used BETWEEN 0 AND 3 AND businesses_discovered BETWEEN 0 AND 300"
    ),
    CheckConstraint("(reason='TARGET_50_REACHED') = (achieved=50)"),
)
discovery_completions = table(
    "discovery_completions",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("batch_id", U),
    col("filter", JSONB),
    col("kind", String),
    col("mode", String),
    col("registered_by", U),
    col("observed_at", T),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    UniqueConstraint("batch_id", "filter"),
    enumcheck("kind", ["QUERY_COMPLETE", "SEARCH_SPACE_EXHAUSTED"]),
    enumcheck("mode", ["SYNTHETIC", "TRUSTED_REFERENCE"]),
    CheckConstraint("isfinite(observed_at)"),
)

plan_changes = table(
    "plan_changes",
    col("batch_id", U, primary_key=True),
    col("experiment_id", U),
    col("source_batch_id", U),
    col("feedback_id", U),
    col("prior_plan", JSONB),
    col("new_plan", JSONB),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["feedback_id", "experiment_id"],
        ["supply_feedback.id", "supply_feedback.experiment_id"],
    ),
)
for timed_table in (identities, facts):
    timed_table.append_constraint(
        CheckConstraint("isfinite(observed_at) AND isfinite(valid_until)")
    )
plans.append_constraint(CheckConstraint("isfinite(deadline)"))
batches.append_constraint(
    CheckConstraint(
        "isfinite(started_at) AND (completed_at IS NULL OR (isfinite(completed_at) AND completed_at>=started_at))"
    )
)

TABLES = [
    references,
    plans,
    identities,
    facts,
    batches,
    candidates,
    contacts,
    contact_failures,
    qualifications,
    feedback,
    closures,
    operations,
    outcomes,
    plan_changes,
    discovery_completions,
]

FUNCTIONS = [
    r"""
CREATE FUNCTION supply_filters_valid(items jsonb, exp uuid) RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE item jsonb;
BEGIN
 IF jsonb_typeof(items) <> 'array' OR jsonb_array_length(items)>100 THEN RETURN false; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements(items)) <> (SELECT count(DISTINCT v) FROM jsonb_array_elements(items) v) THEN RETURN false; END IF;
 FOR item IN SELECT * FROM jsonb_array_elements(items) LOOP
  IF NOT gov_json_object(item, ARRAY['schema_version','dimension','value']) OR item->>'schema_version'<>'1' OR NOT gov_json_uuid(item->'value') OR NOT EXISTS(SELECT 1 FROM supply_references r WHERE r.id=(item->>'value')::uuid AND r.experiment_id=exp AND r.kind='FILTER' AND r.dimension=item->>'dimension') THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
END $$
""",
    r"""
CREATE FUNCTION supply_plan_valid(data jsonb, exp uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT gov_json_object(data, ARRAY['schema_version','qualification_rule_id','filters']) AND data->>'schema_version'='1' AND gov_json_uuid(data->'qualification_rule_id') AND supply_filters_valid(data->'filters', exp) AND jsonb_array_length(data->'filters')>0 AND EXISTS(SELECT 1 FROM supply_references WHERE id=(data->>'qualification_rule_id')::uuid AND experiment_id=exp AND kind='QUALIFICATION_RULE')
$$
""",
    r"""
CREATE FUNCTION supply_feedback_payload(batch uuid, gate text) RETURNS jsonb LANGUAGE sql STABLE AS $$
 WITH b AS (SELECT * FROM supply_batches WHERE id=batch), results AS (
  SELECT c.id,c.observations,CASE WHEN gate='EMAIL' THEN coalesce(t.outcome,'PENDING') ELSE coalesce(q.outcome,t.outcome,'PENDING') END reason
  FROM supply_candidates c JOIN b ON b.experiment_id=c.experiment_id LEFT JOIN supply_contacts t ON t.candidate_id=c.id LEFT JOIN supply_qualifications q ON q.candidate_id=c.id
 ), reasons AS (SELECT reason,count(*) n FROM results GROUP BY reason), performance AS (
  SELECT f->>'dimension' dimension,f->>'value' value,reason,count(*) n FROM results CROSS JOIN LATERAL jsonb_array_elements(observations) f GROUP BY 1,2,3
  UNION ALL SELECT dc.filter->>'dimension',dc.filter->>'value','QUERY_YIELD_SHORTFALL',(SELECT count(*) FROM results WHERE observations @> jsonb_build_array(dc.filter)) FROM supply_discovery_completions dc WHERE dc.batch_id=batch AND gate='EMAIL' AND (SELECT count(*) FROM results WHERE reason='SUPPORTED')<50
 )
 SELECT jsonb_build_object('prior_plan',b.plan,'deficit',50-(SELECT count(*) FROM results WHERE reason=CASE WHEN gate='EMAIL' THEN 'SUPPORTED' ELSE 'QUALIFIED' END),
 'reasons',coalesce((SELECT jsonb_agg(jsonb_build_object('reason',reason,'count',n) ORDER BY reason) FROM reasons),'[]'::jsonb),
 'performance',coalesce((SELECT jsonb_agg(jsonb_build_object('dimension',dimension,'value',value,'reason',reason,'count',n) ORDER BY dimension,value,reason) FROM performance),'[]'::jsonb)) FROM b
$$
""",
    r"""
CREATE FUNCTION supply_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p supply_plans; b supply_batches; i supply_identities; f supply_facts; v supply_facts; cl supply_facts; c supply_candidates; fb supply_feedback; op gov_operations; cfg gov_configs; payload jsonb; expected text; total integer; item jsonb; prior jsonb; diff jsonb; dim text;
BEGIN
 PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN
  IF TG_TABLE_NAME='supply_plans' THEN
   IF (to_jsonb(NEW)-'state')<>(to_jsonb(OLD)-'state') OR OLD.state<>'ACTIVE' OR NOT EXISTS(SELECT 1 FROM supply_outcomes WHERE experiment_id=NEW.experiment_id AND reason=NEW.state) THEN RAISE EXCEPTION 'invalid supply transition'; END IF;
  ELSIF TG_TABLE_NAME='supply_batches' THEN
   IF (to_jsonb(NEW)-ARRAY['stage','completed_at'])<>(to_jsonb(OLD)-ARRAY['stage','completed_at']) OR (OLD.completed_at IS NOT NULL AND NEW.completed_at IS DISTINCT FROM OLD.completed_at) OR NOT ((OLD.stage='CONTACT' AND NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION','DONE')) OR (OLD.stage='QUALIFICATION' AND NEW.stage IN ('QUALIFICATION_RETRY_READY','DONE'))) THEN RAISE EXCEPTION 'invalid batch transition'; END IF;
   IF OLD.stage='CONTACT' AND EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.batch_id=NEW.id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE')) THEN RAISE EXCEPTION 'unresolved contact gate'; END IF;
   IF NEW.stage='QUALIFICATION' AND (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 THEN RAISE EXCEPTION 'email shortage'; END IF;
   IF NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION_RETRY_READY') AND NOT EXISTS(SELECT 1 FROM supply_feedback WHERE batch_id=NEW.id AND gate=CASE WHEN NEW.stage='EMAIL_RETRY_READY' THEN 'EMAIL' ELSE 'QUALIFICATION' END) THEN RAISE EXCEPTION 'missing feedback'; END IF;
  ELSIF TG_TABLE_NAME='supply_candidates' THEN
   IF (to_jsonb(NEW)-ARRAY['deep_started','stopped'])<>(to_jsonb(OLD)-ARRAY['deep_started','stopped']) OR (OLD.deep_started AND NOT NEW.deep_started) OR (OLD.stopped AND NOT NEW.stopped) THEN RAISE EXCEPTION 'immutable candidate intent'; END IF;
   IF NEW.deep_started AND NOT OLD.deep_started THEN
    IF NEW.stopped OR NOT EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE') OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=NEW.id AND outcome='SUPPORTED') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') THEN RAISE EXCEPTION 'deep work denied'; END IF;
   END IF;
  ELSE RAISE EXCEPTION 'immutable supply fact'; END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO p FROM supply_plans WHERE experiment_id=NEW.experiment_id;
 IF TG_TABLE_NAME='supply_plans' THEN
  IF NEW.state<>'ACTIVE' OR NOT supply_plan_valid(NEW.initial_plan,NEW.experiment_id) OR NOT supply_filters_valid(NEW.allowed,NEW.experiment_id) OR NOT NEW.allowed @> (NEW.initial_plan->'filters') OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.verification_policy_id AND kind='VERIFICATION_POLICY') THEN RAISE EXCEPTION 'invalid supply plan'; END IF;
 ELSIF TG_TABLE_NAME='supply_identities' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.provenance_ref AND experiment_id=NEW.experiment_id AND kind='INDEPENDENT_SOURCE' AND mode=NEW.mode) THEN RAISE EXCEPTION 'missing permitted provenance'; END IF;
 ELSIF TG_TABLE_NAME='supply_facts' THEN
  SELECT * INTO i FROM supply_identities WHERE id=NEW.identity_id;
  IF i.mode<>NEW.mode THEN RAISE EXCEPTION 'mixed evidence mode'; END IF;
  IF NEW.kind='SOURCE_EMAIL' AND NEW.contact_ref<>NEW.id THEN RAISE EXCEPTION 'source contact identity'; END IF;
  IF NEW.kind IN ('VERIFIED','VERIFICATION_REJECTED') AND (NOT EXISTS(SELECT 1 FROM supply_facts WHERE id=NEW.contact_ref AND identity_id=NEW.identity_id AND kind='SOURCE_EMAIL' AND observed_at<=NEW.observed_at) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='VERIFICATION_POLICY')) THEN RAISE EXCEPTION 'invalid verification lineage'; END IF;
  IF NEW.kind IN ('QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE') AND NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='QUALIFICATION_RULE') THEN RAISE EXCEPTION 'invalid qualification rule'; END IF;
 ELSIF TG_TABLE_NAME='supply_batches' THEN
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.stage<>'CONTACT' OR NOT supply_plan_valid(NEW.plan,NEW.experiment_id) OR NOT p.allowed @> (NEW.plan->'filters') OR NEW.plan->>'qualification_rule_id'<>p.initial_plan->>'qualification_rule_id' THEN RAISE EXCEPTION 'invalid batch plan'; END IF;
  IF NEW.slot=1 THEN
   IF EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.plan<>p.initial_plan THEN RAISE EXCEPTION 'initial batch conflict'; END IF;
  ELSE
   SELECT * INTO b FROM supply_batches WHERE experiment_id=NEW.experiment_id ORDER BY slot DESC LIMIT 1;
   SELECT * INTO fb FROM supply_feedback WHERE id=NEW.feedback_id;
   IF fb.experiment_id IS DISTINCT FROM NEW.experiment_id OR fb.batch_id IS DISTINCT FROM b.id OR fb.payload IS DISTINCT FROM supply_feedback_payload(b.id,fb.gate) OR (NEW.slot=2 AND (b.slot<>1 OR b.stage<>'EMAIL_RETRY_READY' OR fb.gate<>'EMAIL')) OR (NEW.slot=3 AND (b.slot NOT IN (1,2) OR b.stage<>'QUALIFICATION_RETRY_READY' OR fb.gate<>'QUALIFICATION')) THEN RAISE EXCEPTION 'stale or wrong feedback'; END IF;
   prior:=b.plan->'filters'; diff:='[]'::jsonb;
   FOR item IN SELECT value FROM jsonb_array_elements(prior || (NEW.plan->'filters')) LOOP
    IF (prior @> jsonb_build_array(item)) <> ((NEW.plan->'filters') @> jsonb_build_array(item)) THEN diff:=diff || jsonb_build_array(item); END IF;
   END LOOP;
   IF jsonb_array_length(diff)=0 THEN RAISE EXCEPTION 'cosmetic plan change'; END IF;
   FOR item IN SELECT * FROM jsonb_array_elements(diff) LOOP
    dim:=item->>'dimension';
    IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(fb.payload->'performance') x WHERE x->>'dimension'=dim AND x->>'reason' NOT IN ('SUPPORTED','QUALIFIED','PENDING','SOURCE_FAILURE') AND EXISTS(SELECT 1 FROM jsonb_array_elements(prior) y WHERE y->>'dimension'=dim AND y->>'value'=x->>'value')) THEN RAISE EXCEPTION 'unjustified plan change'; END IF;
   END LOOP;
  END IF;
 ELSIF TG_TABLE_NAME='supply_candidates' THEN
  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.clearance_id;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.kind NOT IN ('IDENTITY_CLEAR','IDENTITY_EXCLUDED') OR NEW.deep_started OR NEW.stopped OR NOT supply_filters_valid(NEW.observations,NEW.experiment_id) OR NOT (b.plan->'filters') @> NEW.observations OR NEW.ordinal<>(SELECT count(*)+1 FROM supply_candidates WHERE batch_id=NEW.batch_id) THEN RAISE EXCEPTION 'candidate admission denied'; END IF;
 ELSIF TG_TABLE_NAME='supply_contacts' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO b FROM supply_batches WHERE id=c.batch_id;
  SELECT * INTO i FROM supply_identities WHERE id=c.identity_id;
  SELECT * INTO cl FROM supply_facts WHERE id=c.clearance_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.source_id;
  SELECT * INTO v FROM supply_facts WHERE id=NEW.verification_id;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.identity_id<>c.identity_id THEN RAISE EXCEPTION 'contact scope or phase'; END IF;
  expected:=CASE WHEN cl.kind='IDENTITY_EXCLUDED' AND f.id=cl.id THEN 'IDENTITY_EXCLUDED' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='EMAIL_ABSENT' THEN 'EMAIL_NOT_FOUND' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_FAILURE' THEN 'SOURCE_FAILURE' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_EMAIL' AND v.identity_id=c.identity_id AND v.contact_ref=f.id AND v.policy_ref=p.verification_policy_id THEN CASE v.kind WHEN 'VERIFIED' THEN 'SUPPORTED' WHEN 'VERIFICATION_REJECTED' THEN 'VERIFICATION_REJECTED' END END;
  IF expected IS NULL OR NEW.outcome<>expected OR (NEW.verification_id IS NOT NULL)<>(expected IN ('SUPPORTED','VERIFICATION_REJECTED')) OR NEW.resolved_at<greatest(i.observed_at,cl.observed_at,f.observed_at,coalesce(v.observed_at,f.observed_at)) OR NEW.resolved_at>=NEW.valid_until OR NEW.valid_until<>least(i.valid_until,cl.valid_until,f.valid_until,coalesce(v.valid_until,f.valid_until)) THEN RAISE EXCEPTION 'invalid contact evidence'; END IF;
 ELSIF TG_TABLE_NAME='supply_contact_failures' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_candidates cand JOIN supply_facts proof ON proof.id=NEW.source_id AND proof.identity_id=cand.identity_id WHERE cand.id=NEW.candidate_id AND proof.kind='SOURCE_FAILURE') THEN RAISE EXCEPTION 'invalid failure lineage'; END IF;
 ELSIF TG_TABLE_NAME='supply_qualifications' THEN
  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;
  SELECT * INTO f FROM supply_facts WHERE id=NEW.fact_id;
  IF NOT f.observed_at<=NEW.accepted_at OR NEW.accepted_at>=f.valid_until OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND resolved_at<=NEW.accepted_at AND valid_until>NEW.accepted_at) OR EXISTS(SELECT 1 FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND accepted_at>NEW.accepted_at) OR EXISTS(SELECT 1 FROM supply_qualifications q JOIN supply_facts proof ON proof.id=q.fact_id JOIN supply_contacts t ON t.candidate_id=q.candidate_id WHERE q.experiment_id=NEW.experiment_id AND q.outcome='QUALIFIED' AND (proof.valid_until<=NEW.accepted_at OR t.valid_until<=NEW.accepted_at)) THEN RAISE EXCEPTION 'expired accepted evidence'; END IF;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT c.deep_started OR c.stopped OR f.identity_id<>c.identity_id OR f.kind<>NEW.outcome OR f.policy_ref::text<>p.initial_plan->>'qualification_rule_id' OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND outcome='SUPPORTED') OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') OR (NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')>=50) THEN RAISE EXCEPTION 'qualification denied'; END IF;
 ELSIF TG_TABLE_NAME='supply_feedback' THEN
  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;
  payload:=supply_feedback_payload(NEW.batch_id,NEW.gate);
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.payload IS DISTINCT FROM payload OR (payload->>'deficit')::int NOT BETWEEN 1 AND 50 OR b.slot=3 OR (NEW.gate='EMAIL' AND (b.slot<>1 OR b.stage<>'CONTACT')) OR (NEW.gate='QUALIFICATION' AND b.stage<>'QUALIFICATION') OR EXISTS(SELECT 1 FROM jsonb_array_elements(payload->'reasons') x WHERE x->>'reason' IN ('PENDING','SOURCE_FAILURE') OR (NEW.gate='QUALIFICATION' AND x->>'reason'='SUPPORTED')) THEN RAISE EXCEPTION 'incomplete or malformed feedback'; END IF;
 ELSIF TG_TABLE_NAME='supply_operations' THEN
  SELECT * INTO op FROM gov_operations WHERE id=NEW.operation_id;
  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;
  IF op.gate_kind IS DISTINCT FROM (CASE WHEN NEW.kind='CONTACT' THEN 'CONTACT' ELSE 'SUPPLY' END) OR p.state IS DISTINCT FROM 'ACTIVE' THEN RAISE EXCEPTION 'unbound supply gate'; END IF;
  IF (NEW.kind='DISCOVERY' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','BRAVE_WEB_COVERAGE')) OR (NEW.kind='CONTACT' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL')) OR (NEW.kind='DEEP' AND cfg.capability NOT IN ('OPENAI_GENERATE','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','BRAVE_WEB_COVERAGE')) THEN RAISE EXCEPTION 'work capability mismatch'; END IF;
 ELSIF TG_TABLE_NAME='supply_discovery_completions' THEN
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT supply_filters_valid(jsonb_build_array(NEW.filter),NEW.experiment_id) OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE id=NEW.batch_id AND stage='CONTACT' AND plan->'filters' @> jsonb_build_array(NEW.filter)) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=(NEW.filter->>'value')::uuid AND mode=NEW.mode) THEN RAISE EXCEPTION 'invalid discovery completion'; END IF;
 ELSIF TG_TABLE_NAME='supply_plan_changes' THEN
  IF NOT EXISTS(SELECT 1 FROM supply_batches batch JOIN supply_feedback brief ON brief.id=batch.feedback_id WHERE batch.id=NEW.batch_id AND batch.plan=NEW.new_plan AND brief.id=NEW.feedback_id AND brief.batch_id=NEW.source_batch_id AND brief.payload->'prior_plan'=NEW.prior_plan) THEN RAISE EXCEPTION 'invalid plan change lineage'; END IF;
 ELSIF TG_TABLE_NAME='supply_outcomes' THEN
  SELECT count(*) INTO total FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED';
  IF NEW.reason='EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=2 AND stage='CONTACT') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')>=50 OR EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.experiment_id=NEW.experiment_id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE'))) THEN RAISE EXCEPTION 'invalid email shortage'; END IF;
  IF NEW.reason='QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=3 AND stage='QUALIFICATION') OR EXISTS(SELECT 1 FROM supply_contacts t LEFT JOIN supply_qualifications q ON q.candidate_id=t.candidate_id WHERE t.experiment_id=NEW.experiment_id AND t.outcome='SUPPORTED' AND q.candidate_id IS NULL)) THEN RAISE EXCEPTION 'invalid qualification shortage'; END IF;
  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.achieved<>total OR NEW.batches_used<>(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.businesses_discovered<>(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id) OR NEW.reason='ACTIVE' THEN RAISE EXCEPTION 'invalid outcome facts'; END IF;
 END IF;
 RETURN NEW;
END $$
""",
    r"""
CREATE FUNCTION supply_after_fact() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='supply_batches' THEN
  IF NEW.slot>1 THEN
   INSERT INTO supply_plan_changes SELECT NEW.id,NEW.experiment_id,f.batch_id,f.id,f.payload->'prior_plan',NEW.plan FROM supply_feedback f WHERE f.id=NEW.feedback_id;
  END IF;
 ELSIF TG_TABLE_NAME='supply_outcomes' THEN
  UPDATE supply_plans SET state=NEW.reason WHERE experiment_id=NEW.experiment_id;
  UPDATE supply_candidates SET stopped=true WHERE experiment_id=NEW.experiment_id AND NOT deep_started;
 ELSIF NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN
  INSERT INTO supply_outcomes SELECT NEW.experiment_id,NEW.fact_id,'TARGET_50_REACHED',50,(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);
 END IF;
 RETURN NEW;
END $$
""",
    r"""
CREATE FUNCTION supply_call_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE binding supply_operations;
BEGIN
 IF EXISTS(SELECT 1 FROM gov_operations WHERE id=NEW.operation_id AND gate_kind IN ('SUPPLY','CONTACT')) AND EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id) THEN
  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;
  SELECT * INTO binding FROM supply_operations WHERE operation_id=NEW.operation_id;
  IF binding.config_id IS DISTINCT FROM NEW.config_id THEN RAISE EXCEPTION 'supply call not bound to exact configuration'; END IF;
  IF (TG_OP='INSERT' OR (OLD.state='RESERVED' AND NEW.state='DISPATCHED')) AND NOT EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE') THEN RAISE EXCEPTION 'terminal supply'; END IF;
 END IF;
 RETURN NEW;
END $$
""",
]

# Read-only projection: historical first results remain in supply_qualifications.
current_qualifications = sql_table(
    "record_current_supply_qualifications",
    column("candidate_id", U),
    column("experiment_id", U),
    column("fact_id", U),
    column("accepted_at", T),
    column("outcome", String),
)
