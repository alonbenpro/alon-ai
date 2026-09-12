"""L02 provisional campaign supply; immutable SQL snapshot."""

from alembic import op

revision = "20260912_02"
down_revision = "20260912_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE supply_references (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tdefinition VARCHAR NOT NULL, \n\tdimension VARCHAR, \n\tmode VARCHAR NOT NULL, \n\tregistered_by UUID NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(experiment_id) REFERENCES gov_experiments (id), \n\tUNIQUE (id, experiment_id), \n\tUNIQUE NULLS NOT DISTINCT (experiment_id, kind, dimension, definition), \n\tCHECK (kind IN ('FILTER','VERIFICATION_POLICY','QUALIFICATION_RULE','INDEPENDENT_SOURCE')), \n\tCHECK (dimension IN ('SOURCE','QUERY','CATEGORY','GEOGRAPHY','TRAIT')), \n\tCHECK (mode IN ('SYNTHETIC','TRUSTED_REFERENCE')), \n\tCHECK (definition ~ '^[a-z0-9][a-z0-9 _-]{0,199}$' AND definition = btrim(regexp_replace(definition, ' +', ' ', 'g'))), \n\tCHECK ((kind='FILTER') = (dimension IS NOT NULL))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_plans (\n\texperiment_id UUID NOT NULL, \n\tinitial_plan JSONB NOT NULL, \n\tallowed JSONB NOT NULL, \n\tverification_policy_id UUID NOT NULL, \n\tdeadline TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstate VARCHAR DEFAULT 'ACTIVE' NOT NULL, \n\tqualified_contactable_target INTEGER DEFAULT '50' NOT NULL, \n\tcandidate_batch_size INTEGER DEFAULT '100' NOT NULL, \n\tmax_total_discovery_batches INTEGER DEFAULT '3' NOT NULL, \n\tPRIMARY KEY (experiment_id), \n\tFOREIGN KEY(experiment_id) REFERENCES gov_experiments (id), \n\tFOREIGN KEY(verification_policy_id, experiment_id) REFERENCES supply_references (id, experiment_id), \n\tCHECK (qualified_contactable_target=50 AND candidate_batch_size=100 AND max_total_discovery_batches=3), \n\tCHECK (state IN ('ACTIVE','TARGET_50_REACHED','EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2','QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3','CANCELLED','BUDGET_EXHAUSTED','DEADLINE_EXHAUSTED','SOURCE_FAILURE','PROVIDER_FAILURE','SEARCH_EXHAUSTED','SAFETY_STOP')), \n\tCHECK (isfinite(deadline))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_identities (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tprovenance_ref UUID NOT NULL, \n\tnormalized_key VARCHAR NOT NULL, \n\tmode VARCHAR NOT NULL, \n\tregistered_by UUID NOT NULL, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(experiment_id) REFERENCES gov_experiments (id), \n\tFOREIGN KEY(provenance_ref, experiment_id) REFERENCES supply_references (id, experiment_id), \n\tUNIQUE (id, experiment_id), \n\tUNIQUE (experiment_id, normalized_key), \n\tCHECK (normalized_key ~ '^[a-z0-9][a-z0-9_-]{0,127}$'), \n\tCHECK (observed_at < valid_until), \n\tCHECK (mode IN ('SYNTHETIC','TRUSTED_REFERENCE')), \n\tCHECK (isfinite(observed_at) AND isfinite(valid_until))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_facts (\n\tid UUID NOT NULL, \n\tidentity_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tmode VARCHAR NOT NULL, \n\tregistered_by UUID NOT NULL, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcontact_ref UUID, \n\tpolicy_ref UUID, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(identity_id, experiment_id) REFERENCES supply_identities (id, experiment_id), \n\tFOREIGN KEY(policy_ref, experiment_id) REFERENCES supply_references (id, experiment_id), \n\tUNIQUE (id, identity_id, experiment_id), \n\tUNIQUE (id, experiment_id), \n\tCHECK (observed_at < valid_until), \n\tCHECK (mode IN ('SYNTHETIC','TRUSTED_REFERENCE')), \n\tCHECK (kind IN ('IDENTITY_CLEAR','IDENTITY_EXCLUDED','SOURCE_EMAIL','EMAIL_ABSENT','SOURCE_FAILURE','VERIFIED','VERIFICATION_REJECTED','QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE')), \n\tCHECK ((kind IN ('SOURCE_EMAIL','VERIFIED','VERIFICATION_REJECTED')) = (contact_ref IS NOT NULL)), \n\tCHECK ((kind IN ('VERIFIED','VERIFICATION_REJECTED','QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE')) = (policy_ref IS NOT NULL)), \n\tFOREIGN KEY(contact_ref, identity_id, experiment_id) REFERENCES supply_facts (id, identity_id, experiment_id) DEFERRABLE INITIALLY DEFERRED, \n\tCHECK (isfinite(observed_at) AND isfinite(valid_until))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_batches (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tslot INTEGER NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tplan JSONB NOT NULL, \n\tfeedback_id UUID, \n\tstage VARCHAR DEFAULT 'CONTACT' NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(experiment_id) REFERENCES supply_plans (experiment_id), \n\tUNIQUE (id, experiment_id), \n\tUNIQUE (experiment_id, slot), \n\tCHECK (slot BETWEEN 1 AND 3), \n\tCHECK ((slot=1) = (feedback_id IS NULL)), \n\tCHECK (stage IN ('CONTACT','EMAIL_RETRY_READY','QUALIFICATION','QUALIFICATION_RETRY_READY','DONE')), \n\tUNIQUE (command_key), \n\tCHECK (isfinite(started_at) AND (completed_at IS NULL OR (isfinite(completed_at) AND completed_at>=started_at)))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_outcomes (\n\texperiment_id UUID NOT NULL, \n\tcommand_key UUID NOT NULL, \n\treason VARCHAR NOT NULL, \n\tachieved INTEGER NOT NULL, \n\tbatches_used INTEGER NOT NULL, \n\tbusinesses_discovered INTEGER NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (experiment_id), \n\tFOREIGN KEY(experiment_id) REFERENCES supply_plans (experiment_id), \n\tCHECK (achieved BETWEEN 0 AND 50 AND batches_used BETWEEN 0 AND 3 AND businesses_discovered BETWEEN 0 AND 300), \n\tCHECK ((reason='TARGET_50_REACHED') = (achieved=50)), \n\tUNIQUE (command_key)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_candidates (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tidentity_id UUID NOT NULL, \n\tclearance_id UUID NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tordinal INTEGER NOT NULL, \n\tobservations JSONB NOT NULL, \n\tdeep_started BOOLEAN DEFAULT 'false' NOT NULL, \n\tstopped BOOLEAN DEFAULT 'false' NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tFOREIGN KEY(clearance_id, identity_id, experiment_id) REFERENCES supply_facts (id, identity_id, experiment_id), \n\tUNIQUE (id, experiment_id), \n\tUNIQUE (id, batch_id, experiment_id), \n\tUNIQUE (experiment_id, identity_id), \n\tUNIQUE (batch_id, ordinal), \n\tCHECK (ordinal BETWEEN 1 AND 100), \n\tUNIQUE (command_key)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_feedback (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tgate VARCHAR NOT NULL, \n\tpayload JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tUNIQUE (id, experiment_id), \n\tUNIQUE (batch_id, gate), \n\tCHECK (gate IN ('EMAIL','QUALIFICATION'))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_discovery_completions (\n\tid UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tfilter JSONB NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tmode VARCHAR NOT NULL, \n\tregistered_by UUID NOT NULL, \n\tobserved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tUNIQUE (batch_id, filter), \n\tCHECK (kind IN ('QUERY_COMPLETE','SEARCH_SPACE_EXHAUSTED')), \n\tCHECK (mode IN ('SYNTHETIC','TRUSTED_REFERENCE')), \n\tCHECK (isfinite(observed_at))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_contacts (\n\tcandidate_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tsource_id UUID NOT NULL, \n\tverification_id UUID, \n\toutcome VARCHAR NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tvalid_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (candidate_id), \n\tFOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id), \n\tFOREIGN KEY(source_id, experiment_id) REFERENCES supply_facts (id, experiment_id), \n\tFOREIGN KEY(verification_id, experiment_id) REFERENCES supply_facts (id, experiment_id), \n\tCHECK (outcome IN ('SUPPORTED','EMAIL_NOT_FOUND','VERIFICATION_REJECTED','IDENTITY_EXCLUDED','SOURCE_FAILURE'))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_contact_failures (\n\tsource_id UUID NOT NULL, \n\tcandidate_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tPRIMARY KEY (source_id), \n\tFOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id), \n\tFOREIGN KEY(source_id, experiment_id) REFERENCES supply_facts (id, experiment_id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_qualifications (\n\tcandidate_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tfact_id UUID NOT NULL, \n\taccepted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\toutcome VARCHAR NOT NULL, \n\tPRIMARY KEY (candidate_id), \n\tFOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id), \n\tFOREIGN KEY(fact_id, experiment_id) REFERENCES supply_facts (id, experiment_id), \n\tCHECK (outcome IN ('QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE')), \n\tUNIQUE (fact_id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_closures (\n\tcommand_key UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tgate VARCHAR NOT NULL, \n\tfeedback_id UUID, \n\tPRIMARY KEY (command_key), \n\tFOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tFOREIGN KEY(feedback_id, experiment_id) REFERENCES supply_feedback (id, experiment_id), \n\tUNIQUE (batch_id, gate), \n\tCHECK (gate IN ('EMAIL','QUALIFICATION'))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_operations (\n\toperation_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tworkflow_id UUID NOT NULL, \n\tconfig_id UUID NOT NULL, \n\tconfig_version UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tcandidate_id UUID, \n\tkind VARCHAR NOT NULL, \n\tPRIMARY KEY (operation_id), \n\tFOREIGN KEY(operation_id, workflow_id, experiment_id, config_version) REFERENCES gov_operations (id, workflow_id, experiment_id, config_version), \n\tFOREIGN KEY(config_id, workflow_id, config_version) REFERENCES gov_configs (id, workflow_id, version), \n\tFOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tFOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id), \n\tCHECK (kind IN ('DISCOVERY','CONTACT','DEEP')), \n\tCHECK ((kind='DISCOVERY') = (candidate_id IS NULL))\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE supply_plan_changes (\n\tbatch_id UUID NOT NULL, \n\texperiment_id UUID NOT NULL, \n\tsource_batch_id UUID NOT NULL, \n\tfeedback_id UUID NOT NULL, \n\tprior_plan JSONB NOT NULL, \n\tnew_plan JSONB NOT NULL, \n\tPRIMARY KEY (batch_id), \n\tFOREIGN KEY(batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tFOREIGN KEY(source_batch_id, experiment_id) REFERENCES supply_batches (id, experiment_id), \n\tFOREIGN KEY(feedback_id, experiment_id) REFERENCES supply_feedback (id, experiment_id)\n)\n\n"
    )
    op.execute(
        "ALTER TABLE supply_batches ADD CONSTRAINT fk_supply_batch_feedback FOREIGN KEY(feedback_id, experiment_id) REFERENCES supply_feedback (id, experiment_id)"
    )
    op.execute(
        "\nCREATE FUNCTION supply_filters_valid(items jsonb, exp uuid) RETURNS boolean LANGUAGE plpgsql STABLE AS $$\nDECLARE item jsonb;\nBEGIN\n IF jsonb_typeof(items) <> 'array' OR jsonb_array_length(items)>100 THEN RETURN false; END IF;\n IF (SELECT count(*) FROM jsonb_array_elements(items)) <> (SELECT count(DISTINCT v) FROM jsonb_array_elements(items) v) THEN RETURN false; END IF;\n FOR item IN SELECT * FROM jsonb_array_elements(items) LOOP\n  IF NOT gov_json_object(item, ARRAY['schema_version','dimension','value']) OR item->>'schema_version'<>'1' OR NOT gov_json_uuid(item->'value') OR NOT EXISTS(SELECT 1 FROM supply_references r WHERE r.id=(item->>'value')::uuid AND r.experiment_id=exp AND r.kind='FILTER' AND r.dimension=item->>'dimension') THEN RETURN false; END IF;\n END LOOP;\n RETURN true;\nEND $$\n"
    )
    op.execute(
        "\nCREATE FUNCTION supply_plan_valid(data jsonb, exp uuid) RETURNS boolean LANGUAGE sql STABLE AS $$\n SELECT gov_json_object(data, ARRAY['schema_version','qualification_rule_id','filters']) AND data->>'schema_version'='1' AND gov_json_uuid(data->'qualification_rule_id') AND supply_filters_valid(data->'filters', exp) AND jsonb_array_length(data->'filters')>0 AND EXISTS(SELECT 1 FROM supply_references WHERE id=(data->>'qualification_rule_id')::uuid AND experiment_id=exp AND kind='QUALIFICATION_RULE')\n$$\n"
    )
    op.execute(
        "\nCREATE FUNCTION supply_feedback_payload(batch uuid, gate text) RETURNS jsonb LANGUAGE sql STABLE AS $$\n WITH b AS (SELECT * FROM supply_batches WHERE id=batch), results AS (\n  SELECT c.id,c.observations,CASE WHEN gate='EMAIL' THEN coalesce(t.outcome,'PENDING') ELSE coalesce(q.outcome,t.outcome,'PENDING') END reason\n  FROM supply_candidates c JOIN b ON b.experiment_id=c.experiment_id LEFT JOIN supply_contacts t ON t.candidate_id=c.id LEFT JOIN supply_qualifications q ON q.candidate_id=c.id\n ), reasons AS (SELECT reason,count(*) n FROM results GROUP BY reason), performance AS (\n  SELECT f->>'dimension' dimension,f->>'value' value,reason,count(*) n FROM results CROSS JOIN LATERAL jsonb_array_elements(observations) f GROUP BY 1,2,3\n  UNION ALL SELECT dc.filter->>'dimension',dc.filter->>'value','QUERY_YIELD_SHORTFALL',(SELECT count(*) FROM results WHERE observations @> jsonb_build_array(dc.filter)) FROM supply_discovery_completions dc WHERE dc.batch_id=batch AND gate='EMAIL' AND (SELECT count(*) FROM results WHERE reason='SUPPORTED')<50\n )\n SELECT jsonb_build_object('prior_plan',b.plan,'deficit',50-(SELECT count(*) FROM results WHERE reason=CASE WHEN gate='EMAIL' THEN 'SUPPORTED' ELSE 'QUALIFIED' END),\n 'reasons',coalesce((SELECT jsonb_agg(jsonb_build_object('reason',reason,'count',n) ORDER BY reason) FROM reasons),'[]'::jsonb),\n 'performance',coalesce((SELECT jsonb_agg(jsonb_build_object('dimension',dimension,'value',value,'reason',reason,'count',n) ORDER BY dimension,value,reason) FROM performance),'[]'::jsonb)) FROM b\n$$\n"
    )
    op.execute(
        "\nCREATE FUNCTION supply_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE p supply_plans; b supply_batches; i supply_identities; f supply_facts; v supply_facts; cl supply_facts; c supply_candidates; fb supply_feedback; op gov_operations; cfg gov_configs; payload jsonb; expected text; total integer; item jsonb; prior jsonb; diff jsonb; dim text;\nBEGIN\n PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;\n IF TG_OP='UPDATE' THEN\n  IF TG_TABLE_NAME='supply_plans' THEN\n   IF (to_jsonb(NEW)-'state')<>(to_jsonb(OLD)-'state') OR OLD.state<>'ACTIVE' OR NOT EXISTS(SELECT 1 FROM supply_outcomes WHERE experiment_id=NEW.experiment_id AND reason=NEW.state) THEN RAISE EXCEPTION 'invalid supply transition'; END IF;\n  ELSIF TG_TABLE_NAME='supply_batches' THEN\n   IF (to_jsonb(NEW)-ARRAY['stage','completed_at'])<>(to_jsonb(OLD)-ARRAY['stage','completed_at']) OR (OLD.completed_at IS NOT NULL AND NEW.completed_at IS DISTINCT FROM OLD.completed_at) OR NOT ((OLD.stage='CONTACT' AND NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION','DONE')) OR (OLD.stage='QUALIFICATION' AND NEW.stage IN ('QUALIFICATION_RETRY_READY','DONE'))) THEN RAISE EXCEPTION 'invalid batch transition'; END IF;\n   IF OLD.stage='CONTACT' AND EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.batch_id=NEW.id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE')) THEN RAISE EXCEPTION 'unresolved contact gate'; END IF;\n   IF NEW.stage='QUALIFICATION' AND (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 THEN RAISE EXCEPTION 'email shortage'; END IF;\n   IF NEW.stage IN ('EMAIL_RETRY_READY','QUALIFICATION_RETRY_READY') AND NOT EXISTS(SELECT 1 FROM supply_feedback WHERE batch_id=NEW.id AND gate=CASE WHEN NEW.stage='EMAIL_RETRY_READY' THEN 'EMAIL' ELSE 'QUALIFICATION' END) THEN RAISE EXCEPTION 'missing feedback'; END IF;\n  ELSIF TG_TABLE_NAME='supply_candidates' THEN\n   IF (to_jsonb(NEW)-ARRAY['deep_started','stopped'])<>(to_jsonb(OLD)-ARRAY['deep_started','stopped']) OR (OLD.deep_started AND NOT NEW.deep_started) OR (OLD.stopped AND NOT NEW.stopped) THEN RAISE EXCEPTION 'immutable candidate intent'; END IF;\n   IF NEW.deep_started AND NOT OLD.deep_started THEN\n    IF NEW.stopped OR NOT EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE') OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=NEW.id AND outcome='SUPPORTED') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')<50 OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') THEN RAISE EXCEPTION 'deep work denied'; END IF;\n   END IF;\n  ELSE RAISE EXCEPTION 'immutable supply fact'; END IF;\n  RETURN NEW;\n END IF;\n SELECT * INTO p FROM supply_plans WHERE experiment_id=NEW.experiment_id;\n IF TG_TABLE_NAME='supply_plans' THEN\n  IF NEW.state<>'ACTIVE' OR NOT supply_plan_valid(NEW.initial_plan,NEW.experiment_id) OR NOT supply_filters_valid(NEW.allowed,NEW.experiment_id) OR NOT NEW.allowed @> (NEW.initial_plan->'filters') OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.verification_policy_id AND kind='VERIFICATION_POLICY') THEN RAISE EXCEPTION 'invalid supply plan'; END IF;\n ELSIF TG_TABLE_NAME='supply_identities' THEN\n  IF NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.provenance_ref AND experiment_id=NEW.experiment_id AND kind='INDEPENDENT_SOURCE' AND mode=NEW.mode) THEN RAISE EXCEPTION 'missing permitted provenance'; END IF;\n ELSIF TG_TABLE_NAME='supply_facts' THEN\n  SELECT * INTO i FROM supply_identities WHERE id=NEW.identity_id;\n  IF i.mode<>NEW.mode THEN RAISE EXCEPTION 'mixed evidence mode'; END IF;\n  IF NEW.kind='SOURCE_EMAIL' AND NEW.contact_ref<>NEW.id THEN RAISE EXCEPTION 'source contact identity'; END IF;\n  IF NEW.kind IN ('VERIFIED','VERIFICATION_REJECTED') AND (NOT EXISTS(SELECT 1 FROM supply_facts WHERE id=NEW.contact_ref AND identity_id=NEW.identity_id AND kind='SOURCE_EMAIL' AND observed_at<=NEW.observed_at) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='VERIFICATION_POLICY')) THEN RAISE EXCEPTION 'invalid verification lineage'; END IF;\n  IF NEW.kind IN ('QUALIFIED','REJECTED_FIT','REJECTED_EVIDENCE') AND NOT EXISTS(SELECT 1 FROM supply_references WHERE id=NEW.policy_ref AND kind='QUALIFICATION_RULE') THEN RAISE EXCEPTION 'invalid qualification rule'; END IF;\n ELSIF TG_TABLE_NAME='supply_batches' THEN\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.stage<>'CONTACT' OR NOT supply_plan_valid(NEW.plan,NEW.experiment_id) OR NOT p.allowed @> (NEW.plan->'filters') OR NEW.plan->>'qualification_rule_id'<>p.initial_plan->>'qualification_rule_id' THEN RAISE EXCEPTION 'invalid batch plan'; END IF;\n  IF NEW.slot=1 THEN\n   IF EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.plan<>p.initial_plan THEN RAISE EXCEPTION 'initial batch conflict'; END IF;\n  ELSE\n   SELECT * INTO b FROM supply_batches WHERE experiment_id=NEW.experiment_id ORDER BY slot DESC LIMIT 1;\n   SELECT * INTO fb FROM supply_feedback WHERE id=NEW.feedback_id;\n   IF fb.experiment_id IS DISTINCT FROM NEW.experiment_id OR fb.batch_id IS DISTINCT FROM b.id OR fb.payload IS DISTINCT FROM supply_feedback_payload(b.id,fb.gate) OR (NEW.slot=2 AND (b.slot<>1 OR b.stage<>'EMAIL_RETRY_READY' OR fb.gate<>'EMAIL')) OR (NEW.slot=3 AND (b.slot NOT IN (1,2) OR b.stage<>'QUALIFICATION_RETRY_READY' OR fb.gate<>'QUALIFICATION')) THEN RAISE EXCEPTION 'stale or wrong feedback'; END IF;\n   prior:=b.plan->'filters'; diff:='[]'::jsonb;\n   FOR item IN SELECT value FROM jsonb_array_elements(prior || (NEW.plan->'filters')) LOOP\n    IF (prior @> jsonb_build_array(item)) <> ((NEW.plan->'filters') @> jsonb_build_array(item)) THEN diff:=diff || jsonb_build_array(item); END IF;\n   END LOOP;\n   IF jsonb_array_length(diff)=0 THEN RAISE EXCEPTION 'cosmetic plan change'; END IF;\n   FOR item IN SELECT * FROM jsonb_array_elements(diff) LOOP\n    dim:=item->>'dimension';\n    IF NOT EXISTS(SELECT 1 FROM jsonb_array_elements(fb.payload->'performance') x WHERE x->>'dimension'=dim AND x->>'reason' NOT IN ('SUPPORTED','QUALIFIED','PENDING','SOURCE_FAILURE') AND EXISTS(SELECT 1 FROM jsonb_array_elements(prior) y WHERE y->>'dimension'=dim AND y->>'value'=x->>'value')) THEN RAISE EXCEPTION 'unjustified plan change'; END IF;\n   END LOOP;\n  END IF;\n ELSIF TG_TABLE_NAME='supply_candidates' THEN\n  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;\n  SELECT * INTO f FROM supply_facts WHERE id=NEW.clearance_id;\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.kind NOT IN ('IDENTITY_CLEAR','IDENTITY_EXCLUDED') OR NEW.deep_started OR NEW.stopped OR NOT supply_filters_valid(NEW.observations,NEW.experiment_id) OR NOT (b.plan->'filters') @> NEW.observations OR NEW.ordinal<>(SELECT count(*)+1 FROM supply_candidates WHERE batch_id=NEW.batch_id) THEN RAISE EXCEPTION 'candidate admission denied'; END IF;\n ELSIF TG_TABLE_NAME='supply_contacts' THEN\n  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;\n  SELECT * INTO b FROM supply_batches WHERE id=c.batch_id;\n  SELECT * INTO i FROM supply_identities WHERE id=c.identity_id;\n  SELECT * INTO cl FROM supply_facts WHERE id=c.clearance_id;\n  SELECT * INTO f FROM supply_facts WHERE id=NEW.source_id;\n  SELECT * INTO v FROM supply_facts WHERE id=NEW.verification_id;\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR b.stage<>'CONTACT' OR f.identity_id<>c.identity_id THEN RAISE EXCEPTION 'contact scope or phase'; END IF;\n  expected:=CASE WHEN cl.kind='IDENTITY_EXCLUDED' AND f.id=cl.id THEN 'IDENTITY_EXCLUDED' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='EMAIL_ABSENT' THEN 'EMAIL_NOT_FOUND' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_FAILURE' THEN 'SOURCE_FAILURE' WHEN cl.kind='IDENTITY_CLEAR' AND f.kind='SOURCE_EMAIL' AND v.identity_id=c.identity_id AND v.contact_ref=f.id AND v.policy_ref=p.verification_policy_id THEN CASE v.kind WHEN 'VERIFIED' THEN 'SUPPORTED' WHEN 'VERIFICATION_REJECTED' THEN 'VERIFICATION_REJECTED' END END;\n  IF expected IS NULL OR NEW.outcome<>expected OR (NEW.verification_id IS NOT NULL)<>(expected IN ('SUPPORTED','VERIFICATION_REJECTED')) OR NEW.resolved_at<greatest(i.observed_at,cl.observed_at,f.observed_at,coalesce(v.observed_at,f.observed_at)) OR NEW.resolved_at>=NEW.valid_until OR NEW.valid_until<>least(i.valid_until,cl.valid_until,f.valid_until,coalesce(v.valid_until,f.valid_until)) THEN RAISE EXCEPTION 'invalid contact evidence'; END IF;\n ELSIF TG_TABLE_NAME='supply_contact_failures' THEN\n  IF NOT EXISTS(SELECT 1 FROM supply_candidates cand JOIN supply_facts proof ON proof.id=NEW.source_id AND proof.identity_id=cand.identity_id WHERE cand.id=NEW.candidate_id AND proof.kind='SOURCE_FAILURE') THEN RAISE EXCEPTION 'invalid failure lineage'; END IF;\n ELSIF TG_TABLE_NAME='supply_qualifications' THEN\n  SELECT * INTO c FROM supply_candidates WHERE id=NEW.candidate_id;\n  SELECT * INTO f FROM supply_facts WHERE id=NEW.fact_id;\n  IF NOT f.observed_at<=NEW.accepted_at OR NEW.accepted_at>=f.valid_until OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND resolved_at<=NEW.accepted_at AND valid_until>NEW.accepted_at) OR EXISTS(SELECT 1 FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND accepted_at>NEW.accepted_at) OR EXISTS(SELECT 1 FROM supply_qualifications q JOIN supply_facts proof ON proof.id=q.fact_id JOIN supply_contacts t ON t.candidate_id=q.candidate_id WHERE q.experiment_id=NEW.experiment_id AND q.outcome='QUALIFIED' AND (proof.valid_until<=NEW.accepted_at OR t.valid_until<=NEW.accepted_at)) THEN RAISE EXCEPTION 'expired accepted evidence'; END IF;\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT c.deep_started OR c.stopped OR f.identity_id<>c.identity_id OR f.kind<>NEW.outcome OR f.policy_ref::text<>p.initial_plan->>'qualification_rule_id' OR NOT EXISTS(SELECT 1 FROM supply_contacts WHERE candidate_id=c.id AND outcome='SUPPORTED') OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND stage='QUALIFICATION') OR (NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')>=50) THEN RAISE EXCEPTION 'qualification denied'; END IF;\n ELSIF TG_TABLE_NAME='supply_feedback' THEN\n  SELECT * INTO b FROM supply_batches WHERE id=NEW.batch_id;\n  payload:=supply_feedback_payload(NEW.batch_id,NEW.gate);\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.payload IS DISTINCT FROM payload OR (payload->>'deficit')::int NOT BETWEEN 1 AND 50 OR b.slot=3 OR (NEW.gate='EMAIL' AND (b.slot<>1 OR b.stage<>'CONTACT')) OR (NEW.gate='QUALIFICATION' AND b.stage<>'QUALIFICATION') OR EXISTS(SELECT 1 FROM jsonb_array_elements(payload->'reasons') x WHERE x->>'reason' IN ('PENDING','SOURCE_FAILURE') OR (NEW.gate='QUALIFICATION' AND x->>'reason'='SUPPORTED')) THEN RAISE EXCEPTION 'incomplete or malformed feedback'; END IF;\n ELSIF TG_TABLE_NAME='supply_operations' THEN\n  SELECT * INTO op FROM gov_operations WHERE id=NEW.operation_id;\n  SELECT * INTO cfg FROM gov_configs WHERE id=NEW.config_id;\n  IF op.gate_kind IS DISTINCT FROM (CASE WHEN NEW.kind='CONTACT' THEN 'CONTACT' ELSE 'SUPPLY' END) OR p.state IS DISTINCT FROM 'ACTIVE' THEN RAISE EXCEPTION 'unbound supply gate'; END IF;\n  IF (NEW.kind='DISCOVERY' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','BRAVE_WEB_COVERAGE')) OR (NEW.kind='CONTACT' AND cfg.capability NOT IN ('BRAVE_LOCAL_DISCOVERY','BRAVE_COMPANY_DISCOVERY','HUNTER_DOMAIN_SEARCH','HUNTER_EMAIL_FINDER','HUNTER_COMPANY_ENRICHMENT','HUNTER_PERSON_ENRICHMENT','HUNTER_EMAIL_VERIFICATION','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL')) OR (NEW.kind='DEEP' AND cfg.capability NOT IN ('OPENAI_GENERATE','FIRECRAWL_MAP','FIRECRAWL_PAGE_CAPTURE','FIRECRAWL_PDF_CAPTURE','FIRECRAWL_JS_RETRIEVAL','BRAVE_WEB_COVERAGE')) THEN RAISE EXCEPTION 'work capability mismatch'; END IF;\n ELSIF TG_TABLE_NAME='supply_discovery_completions' THEN\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR NOT supply_filters_valid(jsonb_build_array(NEW.filter),NEW.experiment_id) OR NOT EXISTS(SELECT 1 FROM supply_batches WHERE id=NEW.batch_id AND stage='CONTACT' AND plan->'filters' @> jsonb_build_array(NEW.filter)) OR NOT EXISTS(SELECT 1 FROM supply_references WHERE id=(NEW.filter->>'value')::uuid AND mode=NEW.mode) THEN RAISE EXCEPTION 'invalid discovery completion'; END IF;\n ELSIF TG_TABLE_NAME='supply_plan_changes' THEN\n  IF NOT EXISTS(SELECT 1 FROM supply_batches batch JOIN supply_feedback brief ON brief.id=batch.feedback_id WHERE batch.id=NEW.batch_id AND batch.plan=NEW.new_plan AND brief.id=NEW.feedback_id AND brief.batch_id=NEW.source_batch_id AND brief.payload->'prior_plan'=NEW.prior_plan) THEN RAISE EXCEPTION 'invalid plan change lineage'; END IF;\n ELSIF TG_TABLE_NAME='supply_outcomes' THEN\n  SELECT count(*) INTO total FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED';\n  IF NEW.reason='EMAIL_SUPPLY_INSUFFICIENT_AFTER_BATCH_2' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=2 AND stage='CONTACT') OR (SELECT count(*) FROM supply_contacts WHERE experiment_id=NEW.experiment_id AND outcome='SUPPORTED')>=50 OR EXISTS(SELECT 1 FROM supply_candidates cand LEFT JOIN supply_contacts t ON t.candidate_id=cand.id WHERE cand.experiment_id=NEW.experiment_id AND (t.candidate_id IS NULL OR t.outcome='SOURCE_FAILURE'))) THEN RAISE EXCEPTION 'invalid email shortage'; END IF;\n  IF NEW.reason='QUALIFIED_SUPPLY_INSUFFICIENT_AFTER_BATCH_3' AND (NOT EXISTS(SELECT 1 FROM supply_batches WHERE experiment_id=NEW.experiment_id AND slot=3 AND stage='QUALIFICATION') OR EXISTS(SELECT 1 FROM supply_contacts t LEFT JOIN supply_qualifications q ON q.candidate_id=t.candidate_id WHERE t.experiment_id=NEW.experiment_id AND t.outcome='SUPPORTED' AND q.candidate_id IS NULL)) THEN RAISE EXCEPTION 'invalid qualification shortage'; END IF;\n  IF p.state IS DISTINCT FROM 'ACTIVE' OR NEW.achieved<>total OR NEW.batches_used<>(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id) OR NEW.businesses_discovered<>(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id) OR NEW.reason='ACTIVE' THEN RAISE EXCEPTION 'invalid outcome facts'; END IF;\n END IF;\n RETURN NEW;\nEND $$\n"
    )
    op.execute(
        "\nCREATE FUNCTION supply_after_fact() RETURNS trigger LANGUAGE plpgsql AS $$\nBEGIN\n IF TG_TABLE_NAME='supply_batches' THEN\n  IF NEW.slot>1 THEN\n   INSERT INTO supply_plan_changes SELECT NEW.id,NEW.experiment_id,f.batch_id,f.id,f.payload->'prior_plan',NEW.plan FROM supply_feedback f WHERE f.id=NEW.feedback_id;\n  END IF;\n ELSIF TG_TABLE_NAME='supply_outcomes' THEN\n  UPDATE supply_plans SET state=NEW.reason WHERE experiment_id=NEW.experiment_id;\n  UPDATE supply_candidates SET stopped=true WHERE experiment_id=NEW.experiment_id AND NOT deep_started;\n ELSIF NEW.outcome='QUALIFIED' AND (SELECT count(*) FROM supply_qualifications WHERE experiment_id=NEW.experiment_id AND outcome='QUALIFIED')=50 THEN\n  INSERT INTO supply_outcomes SELECT NEW.experiment_id,NEW.fact_id,'TARGET_50_REACHED',50,(SELECT count(*) FROM supply_batches WHERE experiment_id=NEW.experiment_id),(SELECT count(*) FROM supply_candidates WHERE experiment_id=NEW.experiment_id);\n END IF;\n RETURN NEW;\nEND $$\n"
    )
    op.execute(
        "\nCREATE FUNCTION supply_call_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE binding supply_operations;\nBEGIN\n IF EXISTS(SELECT 1 FROM gov_operations WHERE id=NEW.operation_id AND gate_kind IN ('SUPPLY','CONTACT')) AND EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id) THEN\n  PERFORM 1 FROM gov_experiments WHERE id=NEW.experiment_id FOR UPDATE;\n  SELECT * INTO binding FROM supply_operations WHERE operation_id=NEW.operation_id;\n  IF binding.config_id IS DISTINCT FROM NEW.config_id THEN RAISE EXCEPTION 'supply call not bound to exact configuration'; END IF;\n  IF (TG_OP='INSERT' OR (OLD.state='RESERVED' AND NEW.state='DISPATCHED')) AND NOT EXISTS(SELECT 1 FROM supply_plans WHERE experiment_id=NEW.experiment_id AND state='ACTIVE') THEN RAISE EXCEPTION 'terminal supply'; END IF;\n END IF;\n RETURN NEW;\nEND $$\n"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_references FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_references FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_plans FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_plans FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_identities FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_identities FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_facts FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_facts FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_batches FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_batches FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_candidates FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_candidates FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_contacts FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_contacts FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_contact_failures FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_contact_failures FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_qualifications FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_qualifications FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_feedback FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_feedback FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_closures FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_closures FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_operations FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_operations FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_outcomes FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_outcomes FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_plan_changes FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_plan_changes FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_guard BEFORE INSERT OR UPDATE ON supply_discovery_completions FOR EACH ROW EXECUTE FUNCTION supply_guard()"
    )
    op.execute(
        "CREATE TRIGGER supply_no_delete BEFORE DELETE ON supply_discovery_completions FOR EACH ROW EXECUTE FUNCTION gov_immutable()"
    )
    op.execute(
        "CREATE TRIGGER supply_after_fact AFTER INSERT ON supply_qualifications FOR EACH ROW EXECUTE FUNCTION supply_after_fact()"
    )
    op.execute(
        "CREATE TRIGGER supply_after_fact AFTER INSERT ON supply_outcomes FOR EACH ROW EXECUTE FUNCTION supply_after_fact()"
    )
    op.execute(
        "CREATE TRIGGER supply_after_fact AFTER INSERT ON supply_batches FOR EACH ROW EXECUTE FUNCTION supply_after_fact()"
    )
    op.execute(
        "CREATE TRIGGER supply_call_guard BEFORE INSERT OR UPDATE ON gov_calls FOR EACH ROW EXECUTE FUNCTION supply_call_guard()"
    )


def downgrade():
    op.execute("DROP TRIGGER supply_call_guard ON gov_calls")
    op.execute("ALTER TABLE supply_batches DROP CONSTRAINT fk_supply_batch_feedback")
    op.execute("DROP TABLE supply_discovery_completions CASCADE")
    op.execute("DROP TABLE supply_plan_changes CASCADE")
    op.execute("DROP TABLE supply_outcomes CASCADE")
    op.execute("DROP TABLE supply_operations CASCADE")
    op.execute("DROP TABLE supply_closures CASCADE")
    op.execute("DROP TABLE supply_feedback CASCADE")
    op.execute("DROP TABLE supply_qualifications CASCADE")
    op.execute("DROP TABLE supply_contact_failures CASCADE")
    op.execute("DROP TABLE supply_contacts CASCADE")
    op.execute("DROP TABLE supply_candidates CASCADE")
    op.execute("DROP TABLE supply_batches CASCADE")
    op.execute("DROP TABLE supply_facts CASCADE")
    op.execute("DROP TABLE supply_identities CASCADE")
    op.execute("DROP TABLE supply_plans CASCADE")
    op.execute("DROP TABLE supply_references CASCADE")
    op.execute("DROP FUNCTION supply_call_guard()")
    op.execute("DROP FUNCTION supply_after_fact()")
    op.execute("DROP FUNCTION supply_guard()")
    op.execute("DROP FUNCTION supply_feedback_payload(uuid,text)")
    op.execute("DROP FUNCTION supply_plan_valid(jsonb,uuid)")
    op.execute("DROP FUNCTION supply_filters_valid(jsonb,uuid)")
