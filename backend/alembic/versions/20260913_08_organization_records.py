"""Global organization identity and first-contact protection.

Revision ID: 20260913_08
Revises: 20260913_07
"""

from alembic import op

revision = "20260913_08"
down_revision = "20260913_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_extension WHERE extname='pgcrypto') THEN CREATE EXTENSION pgcrypto; CREATE TEMP TABLE org_extension_installed_by_migration(value boolean) ON COMMIT DROP; END IF; END $$;

CREATE TABLE record_org_policy (
	id SERIAL NOT NULL, 
	key_fingerprint VARCHAR(64), 
	owns_pgcrypto BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (id=1 AND key_fingerprint ~ '^[0-9a-f]{64}$')
)

;

CREATE TABLE record_org_organizations (
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE record_org_evidence (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	operation_id UUID NOT NULL, 
	call_id UUID NOT NULL, 
	grant_id UUID NOT NULL, 
	grant_version INTEGER NOT NULL, 
	retained_id UUID NOT NULL, 
	value_index INTEGER NOT NULL, 
	snapshot_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES record_org_organizations (id), 
	FOREIGN KEY(experiment_id) REFERENCES record_experiments (id), 
	FOREIGN KEY(operation_id) REFERENCES gov_operations (id), 
	FOREIGN KEY(call_id) REFERENCES gov_calls (id), 
	FOREIGN KEY(grant_id, grant_version) REFERENCES gov_grants (id, version), 
	UNIQUE (id, organization_id), 
	CHECK (value_index>=0 AND value_index<=999 AND snapshot_hash ~ '^[0-9a-f]{64}$')
)

;
CREATE INDEX ix_record_org_evidence_fk_0 ON record_org_evidence (call_id);
CREATE INDEX ix_record_org_evidence_fk_1 ON record_org_evidence (experiment_id);
CREATE INDEX ix_record_org_evidence_fk_2 ON record_org_evidence (grant_id, grant_version);
CREATE INDEX ix_record_org_evidence_fk_3 ON record_org_evidence (operation_id);
CREATE INDEX ix_record_org_evidence_fk_4 ON record_org_evidence (organization_id);

CREATE TABLE record_org_keys (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	evidence_id UUID NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	namespace VARCHAR(100) NOT NULL, 
	lookup_hash VARCHAR(64) NOT NULL, 
	source_index INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id, organization_id) REFERENCES record_org_evidence (id, organization_id), 
	CHECK (kind IN ('REGISTERED_ID','PROVIDER_ID','OFFICIAL_URL','NAME','DOMAIN','URL','FORMER_NAME')), 
	CHECK (lookup_hash ~ '^[0-9a-f]{64}$'), 
	UNIQUE (evidence_id, kind, namespace, lookup_hash)
)

;
CREATE INDEX ix_record_org_key_lookup ON record_org_keys (kind, namespace, lookup_hash);
CREATE INDEX ix_record_org_keys_fk_0 ON record_org_keys (evidence_id, organization_id);
CREATE UNIQUE INDEX uq_record_org_registered ON record_org_keys (kind, namespace, lookup_hash) WHERE kind = 'REGISTERED_ID';

CREATE TABLE record_org_locations (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	evidence_id UUID NOT NULL, 
	source_index INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(evidence_id, organization_id) REFERENCES record_org_evidence (id, organization_id), 
	UNIQUE (evidence_id, source_index), 
	CHECK (source_index>=0 AND source_index<100)
)

;
CREATE INDEX ix_record_org_locations_fk_0 ON record_org_locations (evidence_id, organization_id);

CREATE TABLE record_org_bindings (
	id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	identity_id UUID NOT NULL, 
	evidence_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(identity_id, experiment_id) REFERENCES supply_identities (id, experiment_id), 
	FOREIGN KEY(evidence_id, organization_id) REFERENCES record_org_evidence (id, organization_id), 
	UNIQUE (identity_id), 
	UNIQUE (id, experiment_id, organization_id)
)

;
CREATE INDEX ix_record_org_bindings_fk_0 ON record_org_bindings (evidence_id, organization_id);
CREATE INDEX ix_record_org_bindings_fk_1 ON record_org_bindings (identity_id, experiment_id);

CREATE TABLE record_org_recipients (
	id UUID NOT NULL, 
	lookup_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (lookup_hash ~ '^[0-9a-f]{64}$'), 
	UNIQUE (lookup_hash)
)

;

CREATE TABLE record_org_recipient_sources (
	id UUID NOT NULL, 
	recipient_id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	binding_id UUID NOT NULL, 
	candidate_id UUID NOT NULL, 
	source_fact_id UUID NOT NULL, 
	retained_id UUID NOT NULL, 
	value_index INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(recipient_id) REFERENCES record_org_recipients (id), 
	FOREIGN KEY(binding_id, experiment_id, organization_id) REFERENCES record_org_bindings (id, experiment_id, organization_id), 
	FOREIGN KEY(candidate_id, experiment_id) REFERENCES supply_candidates (id, experiment_id), 
	FOREIGN KEY(source_fact_id, experiment_id) REFERENCES supply_facts (id, experiment_id), 
	UNIQUE (id, experiment_id, organization_id, recipient_id), 
	CHECK (value_index>=0 AND value_index<=999)
)

;
CREATE INDEX ix_record_org_recipient_sources_fk_0 ON record_org_recipient_sources (binding_id, experiment_id, organization_id);
CREATE INDEX ix_record_org_recipient_sources_fk_1 ON record_org_recipient_sources (candidate_id, experiment_id);
CREATE INDEX ix_record_org_recipient_sources_fk_2 ON record_org_recipient_sources (recipient_id);
CREATE INDEX ix_record_org_recipient_sources_fk_3 ON record_org_recipient_sources (source_fact_id, experiment_id);

CREATE TABLE record_org_admissions (
	id UUID NOT NULL, 
	binding_id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(binding_id, experiment_id, organization_id) REFERENCES record_org_bindings (id, experiment_id, organization_id), 
	UNIQUE (experiment_id, organization_id)
)

;
CREATE INDEX ix_record_org_admissions_fk_0 ON record_org_admissions (binding_id, experiment_id, organization_id);

CREATE TABLE record_org_reservations (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	recipient_id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	source_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_id, experiment_id, organization_id, recipient_id) REFERENCES record_org_recipient_sources (id, experiment_id, organization_id, recipient_id), 
	UNIQUE (id, experiment_id, organization_id, recipient_id)
)

;
CREATE INDEX ix_record_org_reservations_fk_0 ON record_org_reservations (source_id, experiment_id, organization_id, recipient_id);

CREATE TABLE record_org_releases (
	id UUID NOT NULL, 
	reservation_id UUID NOT NULL, 
	evidence_id UUID, 
	released_by UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reservation_id) REFERENCES record_org_reservations (id), 
	FOREIGN KEY(evidence_id) REFERENCES gov_evidence (id), 
	UNIQUE (reservation_id)
)

;
CREATE INDEX ix_record_org_releases_fk_0 ON record_org_releases (evidence_id);
CREATE INDEX ix_record_org_releases_fk_1 ON record_org_releases (reservation_id);

CREATE TABLE record_org_effects (
	id UUID NOT NULL, 
	reservation_id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	call_id UUID NOT NULL, 
	operation_id UUID NOT NULL, 
	mailbox_id UUID NOT NULL, 
	rfc_message_id UUID NOT NULL, 
	recipient_lookup_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reservation_id) REFERENCES record_org_reservations (id), 
	FOREIGN KEY(experiment_id) REFERENCES record_experiments (id), 
	FOREIGN KEY(call_id) REFERENCES gov_calls (id), 
	FOREIGN KEY(operation_id) REFERENCES gov_operations (id), 
	UNIQUE (id, call_id, operation_id, experiment_id, reservation_id, recipient_lookup_hash, mailbox_id, rfc_message_id), 
	UNIQUE (reservation_id), 
	UNIQUE (call_id), 
	UNIQUE (rfc_message_id)
)

;
CREATE INDEX ix_record_org_effects_fk_0 ON record_org_effects (call_id);
CREATE INDEX ix_record_org_effects_fk_1 ON record_org_effects (experiment_id);
CREATE INDEX ix_record_org_effects_fk_2 ON record_org_effects (operation_id);
CREATE INDEX ix_record_org_effects_fk_3 ON record_org_effects (reservation_id);

CREATE TABLE record_org_observations (
	id UUID NOT NULL, 
	effect_id UUID NOT NULL, 
	call_id UUID NOT NULL, 
	operation_id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	reservation_id UUID NOT NULL, 
	recipient_lookup_hash VARCHAR(64) NOT NULL, 
	mailbox_id UUID NOT NULL, 
	rfc_message_id UUID NOT NULL, 
	outcome VARCHAR(16) NOT NULL, 
	result_evidence_id UUID, 
	provider_request_id VARCHAR(100), 
	provider_message_id VARCHAR(100), 
	reconciles_id UUID, 
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(effect_id, call_id, operation_id, experiment_id, reservation_id, recipient_lookup_hash, mailbox_id, rfc_message_id) REFERENCES record_org_effects (id, call_id, operation_id, experiment_id, reservation_id, recipient_lookup_hash, mailbox_id, rfc_message_id), 
	FOREIGN KEY(result_evidence_id) REFERENCES gov_evidence (id), 
	FOREIGN KEY(reconciles_id) REFERENCES record_org_observations (id), 
	UNIQUE (effect_id, outcome), 
	CHECK (outcome IN ('CONFIRMED','AMBIGUOUS','NO_EFFECT')), 
	CHECK ((outcome='CONFIRMED' AND result_evidence_id IS NOT NULL AND provider_request_id IS NOT NULL AND provider_message_id IS NOT NULL) OR (outcome='AMBIGUOUS' AND result_evidence_id IS NULL AND provider_request_id IS NULL AND provider_message_id IS NULL) OR (outcome='NO_EFFECT' AND result_evidence_id IS NOT NULL AND provider_request_id IS NULL AND provider_message_id IS NULL))
)

;
CREATE INDEX ix_record_org_observations_fk_0 ON record_org_observations (effect_id, call_id, operation_id, experiment_id, reservation_id, recipient_lookup_hash, mailbox_id, rfc_message_id);
CREATE INDEX ix_record_org_observations_fk_1 ON record_org_observations (reconciles_id);
CREATE INDEX ix_record_org_observations_fk_2 ON record_org_observations (result_evidence_id);

CREATE TABLE record_org_suppressions (
	id UUID NOT NULL, 
	organization_id UUID, 
	recipient_id UUID, 
	global_scope BOOLEAN NOT NULL, 
	reason_code VARCHAR(64) NOT NULL, 
	acted_by UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES record_org_organizations (id), 
	FOREIGN KEY(recipient_id) REFERENCES record_org_recipients (id), 
	CHECK ((global_scope AND organization_id IS NULL AND recipient_id IS NULL) OR (NOT global_scope AND (organization_id IS NULL)<>(recipient_id IS NULL))), 
	CHECK (reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$')
)

;
CREATE INDEX ix_record_org_suppressions_fk_0 ON record_org_suppressions (organization_id);
CREATE INDEX ix_record_org_suppressions_fk_1 ON record_org_suppressions (recipient_id);

CREATE TABLE record_org_merges (
	id UUID NOT NULL, 
	losing_id UUID NOT NULL, 
	surviving_id UUID NOT NULL, 
	evidence_id UUID NOT NULL, 
	acted_by UUID NOT NULL, 
	reason_code VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(losing_id) REFERENCES record_org_organizations (id), 
	FOREIGN KEY(surviving_id) REFERENCES record_org_organizations (id), 
	FOREIGN KEY(evidence_id) REFERENCES record_org_evidence (id), 
	CHECK (losing_id<>surviving_id AND reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'), 
	UNIQUE (losing_id)
)

;
CREATE INDEX ix_record_org_merges_fk_0 ON record_org_merges (evidence_id);
CREATE INDEX ix_record_org_merges_fk_1 ON record_org_merges (losing_id);
CREATE INDEX ix_record_org_merges_fk_2 ON record_org_merges (surviving_id);

CREATE TABLE record_org_exclusions (
	id UUID NOT NULL, 
	experiment_id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	reason VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(experiment_id) REFERENCES record_experiments (id), 
	FOREIGN KEY(organization_id) REFERENCES record_org_organizations (id), 
	CHECK (reason IN ('CONTACTED','CONTACT_AMBIGUOUS','RESERVED_ELSEWHERE','SUPPRESSED','IDENTITY_MERGED','IDENTITY_CONFLICT','SOURCE_UNAVAILABLE'))
)

;
CREATE INDEX ix_record_org_exclusions_fk_0 ON record_org_exclusions (experiment_id);
CREATE INDEX ix_record_org_exclusions_fk_1 ON record_org_exclusions (organization_id);

CREATE TABLE record_org_conflicts (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	matched_id UUID NOT NULL, 
	evidence_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES record_org_organizations (id), 
	FOREIGN KEY(matched_id) REFERENCES record_org_organizations (id), 
	FOREIGN KEY(evidence_id) REFERENCES record_org_evidence (id), 
	CHECK (organization_id<>matched_id), 
	UNIQUE (organization_id, matched_id, evidence_id)
)

;
CREATE INDEX ix_record_org_conflicts_fk_0 ON record_org_conflicts (evidence_id);
CREATE INDEX ix_record_org_conflicts_fk_1 ON record_org_conflicts (matched_id);
CREATE INDEX ix_record_org_conflicts_fk_2 ON record_org_conflicts (organization_id);

CREATE TABLE record_org_identity_decisions (
	id UUID NOT NULL, 
	conflict_id UUID NOT NULL, 
	evidence_id UUID NOT NULL, 
	resolution VARCHAR(32) NOT NULL, 
	acted_by UUID NOT NULL, 
	reason_code VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conflict_id) REFERENCES record_org_conflicts (id), 
	FOREIGN KEY(evidence_id) REFERENCES record_org_evidence (id), 
	CHECK (resolution IN ('SAME_ORGANIZATION','INDEPENDENT_BUSINESS')), 
	CHECK (reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'), 
	UNIQUE (conflict_id)
)

;
CREATE INDEX ix_record_org_identity_decisions_fk_0 ON record_org_identity_decisions (conflict_id);
CREATE INDEX ix_record_org_identity_decisions_fk_1 ON record_org_identity_decisions (evidence_id);
INSERT INTO record_org_policy(id,key_fingerprint,owns_pgcrypto) VALUES(1,NULL,to_regclass('pg_temp.org_extension_installed_by_migration') IS NOT NULL);
CREATE FUNCTION record_org_now() RETURNS timestamptz LANGUAGE sql STABLE AS $$ SELECT COALESCE(NULLIF(current_setting('alon.organization_now',true),''),statement_timestamp()::text)::timestamptz $$;
CREATE FUNCTION record_org_require_key() RETURNS void LANGUAGE plpgsql AS $$
DECLARE k text;
BEGIN
 k:=current_setting('alon.organization_key',true);
 IF k IS NULL OR octet_length(convert_to(k,'UTF8'))<>32 OR NOT EXISTS(SELECT 1 FROM record_org_policy WHERE id=1 AND key_fingerprint=encode(sha256(convert_to(k,'UTF8')),'hex')) THEN RAISE EXCEPTION 'identity key policy mismatch'; END IF;
END $$;
CREATE FUNCTION record_org_lookup(value text) RETURNS text LANGUAGE plpgsql AS $$
BEGIN
 PERFORM record_org_require_key();
 IF value IS NULL OR length(btrim(value))=0 THEN RAISE EXCEPTION 'missing identity value'; END IF;
 RETURN encode(hmac(convert_to(lower(btrim(regexp_replace(value,'[[:space:]]+',' ','g'))),'UTF8'),convert_to(current_setting('alon.organization_key'),'UTF8'),'sha256'),'hex');
END $$;
CREATE FUNCTION record_org_source_current(retained_id uuid,required_field text) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE r gov_retained; g gov_grants; c gov_calls; config gov_configs;
BEGIN
 SELECT * INTO r FROM gov_retained WHERE id=retained_id;
 IF r.id IS NULL THEN RETURN false; END IF;
 SELECT * INTO g FROM gov_grants WHERE id=r.grant_id AND version=r.grant_version;
 SELECT * INTO c FROM gov_calls WHERE id=r.call_id;
 SELECT * INTO config FROM gov_configs WHERE id=c.config_id;
 PERFORM 1 FROM gov_authorities WHERE account=g.account AND capability=g.capability FOR SHARE;
 RETURN COALESCE(r.field=required_field AND r.expires_at>record_org_now() AND g.effective_at<=record_org_now() AND g.expires_at>record_org_now()
  AND (g.data->>'outbound_use_permitted')::boolean AND g.data->'storage_fields' ? required_field
  AND config.account=g.account AND config.capability=g.capability
  AND config.data->'intended_use'->>'purpose'=g.data->>'purpose'
  AND config.data->'intended_use'->'required_fields' ? required_field
  AND g.data->>'purpose' IN ('RESEARCH','LEAD_DISCOVERY','CONTACT_DISCOVERY')
  AND NOT EXISTS(SELECT 1 FROM gov_grants newer WHERE newer.data->>'supersedes_id'=g.id::text AND newer.effective_at<=record_org_now() AND newer.expires_at>record_org_now())
  AND c.grant_id=g.id AND c.grant_version=g.version AND c.state='FINAL'
  AND EXISTS(SELECT 1 FROM gov_authorities WHERE account=g.account AND capability=g.capability AND enabled)
  AND NOT EXISTS(SELECT 1 FROM gov_grant_events e WHERE e.grant_id=g.id AND e.grant_version=g.version AND (e.data->>'effective_at')::timestamptz<=record_org_now() AND e.data->>'kind'<>'ACTIVATED'),false);
END $$;
CREATE FUNCTION record_org_snapshot(retained_id uuid,idx integer) RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE result jsonb; r gov_retained; grant_data jsonb;
BEGIN
 PERFORM record_org_require_key();
 IF record_org_source_current(retained_id,'COMPANY') IS NOT TRUE THEN RAISE EXCEPTION 'organization source unavailable'; END IF;
 SELECT * INTO r FROM gov_retained WHERE id=retained_id;
 IF idx<0 OR idx>=jsonb_array_length(r.values) THEN RAISE EXCEPTION 'source index invalid'; END IF;
 result:=(r.values->>idx)::jsonb;
 IF record_json_exact(result,ARRAY['schema_version','canonical_name','canonical_domain','organization_kind','identifiers','aliases','locations']) IS NOT TRUE
 OR result->>'schema_version'<>'1' OR record_nonempty_text(result->'canonical_name') IS NOT TRUE
 OR (result->>'organization_kind' IN ('LOCAL_BUSINESS','ONLINE_COMPANY','HYBRID','UNKNOWN')) IS NOT TRUE
 OR jsonb_typeof(result->'identifiers') IS DISTINCT FROM 'array' OR jsonb_typeof(result->'aliases') IS DISTINCT FROM 'array' OR jsonb_typeof(result->'locations') IS DISTINCT FROM 'array'
 THEN RAISE EXCEPTION 'invalid organization snapshot'; END IF;
 IF jsonb_array_length(result->'identifiers')>30 OR jsonb_array_length(result->'aliases')>50 OR jsonb_array_length(result->'locations')>100
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(result->'identifiers') ident WHERE record_json_exact(ident,ARRAY['schema_version','kind','namespace','value']) IS NOT TRUE OR ident->>'schema_version' IS DISTINCT FROM '1' OR (ident->>'kind' IN ('REGISTERED_ID','PROVIDER_ID','OFFICIAL_URL')) IS NOT TRUE OR record_nonempty_text(ident->'namespace') IS NOT TRUE OR record_nonempty_text(ident->'value') IS NOT TRUE OR (ident->>'kind'='REGISTERED_ID' AND ident->>'namespace' !~ '^[A-Z]{2}$'))
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(result->'aliases') alias WHERE record_json_exact(alias,ARRAY['schema_version','kind','value']) IS NOT TRUE OR alias->>'schema_version' IS DISTINCT FROM '1' OR (alias->>'kind' IN ('NAME','DOMAIN','URL','FORMER_NAME')) IS NOT TRUE OR record_nonempty_text(alias->'value') IS NOT TRUE)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(result->'locations') location WHERE record_json_exact(location,ARRAY['schema_version','branch_name','country_code','city','address','latitude','longitude']) IS NOT TRUE OR location->>'schema_version' IS DISTINCT FROM '1' OR (location->>'country_code' ~ '^[A-Z]{2}$') IS NOT TRUE OR record_nonempty_text(location->'city') IS NOT TRUE OR record_nonempty_text(location->'address') IS NOT TRUE OR (location->>'latitude' IS NULL)<>(location->>'longitude' IS NULL) OR (location->>'latitude')::numeric NOT BETWEEN -90 AND 90 OR (location->>'longitude')::numeric NOT BETWEEN -180 AND 180)
 THEN RAISE EXCEPTION 'invalid typed identity content'; END IF;
 SELECT data INTO grant_data FROM gov_grants WHERE id=r.grant_id AND version=r.grant_version;
 IF (result->>'canonical_domain' IS NOT NULL OR EXISTS(SELECT 1 FROM jsonb_array_elements(result->'aliases') a WHERE a->>'kind' IN ('DOMAIN','URL')) OR EXISTS(SELECT 1 FROM jsonb_array_elements(result->'identifiers') a WHERE a->>'kind'='OFFICIAL_URL')) AND (NOT grant_data->'storage_fields' ? 'URL' OR NOT EXISTS(SELECT 1 FROM gov_calls call JOIN gov_configs config ON config.id=call.config_id WHERE call.id=r.call_id AND config.data->'intended_use'->'required_fields' ? 'URL'))
 THEN RAISE EXCEPTION 'URL storage entitlement required'; END IF;
 RETURN result;
EXCEPTION WHEN invalid_text_representation THEN RAISE EXCEPTION 'invalid organization snapshot';
END $$;
CREATE FUNCTION record_org_email_lookup(retained_id uuid,idx integer) RETURNS text LANGUAGE plpgsql AS $$
DECLARE value text;
BEGIN
 PERFORM record_org_require_key();
 IF record_org_source_current(retained_id,'EMAIL') IS NOT TRUE THEN RAISE EXCEPTION 'email source unavailable'; END IF;
 SELECT values->>idx INTO value FROM gov_retained WHERE id=retained_id;
 IF value IS NULL OR value !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' THEN RAISE EXCEPTION 'unsupported email'; END IF;
 RETURN record_org_lookup(value);
END $$;
CREATE FUNCTION record_org_canonical(target uuid) RETURNS uuid LANGUAGE sql STABLE AS $$
 WITH RECURSIVE lineage(id,path) AS (SELECT target,ARRAY[target] UNION ALL SELECT m.surviving_id,path||m.surviving_id FROM record_org_merges m JOIN lineage l ON m.losing_id=l.id WHERE NOT m.surviving_id=ANY(path))
 SELECT id FROM lineage ORDER BY cardinality(path) DESC LIMIT 1
$$;
CREATE FUNCTION record_org_evidence_current(target uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT COALESCE((SELECT record_org_source_current(e.retained_id,'COMPANY') FROM record_org_evidence e WHERE e.id=target),false)
$$;
CREATE FUNCTION record_org_reservation_live(target uuid) RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT EXISTS(SELECT 1 FROM record_org_reservations WHERE id=target) AND NOT EXISTS(SELECT 1 FROM record_org_releases WHERE reservation_id=target) AND NOT EXISTS(SELECT 1 FROM record_org_observations WHERE reservation_id=target AND outcome='NO_EFFECT') $$;
CREATE FUNCTION record_org_block_reason(org uuid,recipient uuid,exp uuid) RETURNS text LANGUAGE plpgsql STABLE AS $$
DECLARE canonical uuid:=record_org_canonical(org);
BEGIN
 IF EXISTS(SELECT 1 FROM record_org_suppressions s WHERE s.global_scope OR record_org_canonical(s.organization_id)=canonical OR s.recipient_id=recipient OR s.recipient_id IN (SELECT recipient_id FROM record_org_recipient_sources rs WHERE record_org_canonical(rs.organization_id)=canonical)) THEN RETURN 'SUPPRESSED'; END IF;
 IF EXISTS(SELECT 1 FROM record_org_observations o JOIN record_org_reservations r ON r.id=o.reservation_id WHERE o.outcome='CONFIRMED' AND (record_org_canonical(r.organization_id)=canonical OR r.recipient_id=recipient OR r.recipient_id IN (SELECT recipient_id FROM record_org_recipient_sources rs WHERE record_org_canonical(rs.organization_id)=canonical))) THEN RETURN 'CONTACTED'; END IF;
 IF EXISTS(SELECT 1 FROM record_org_observations o JOIN record_org_reservations r ON r.id=o.reservation_id WHERE o.outcome='AMBIGUOUS' AND NOT EXISTS(SELECT 1 FROM record_org_observations resolution WHERE resolution.reconciles_id=o.id AND resolution.outcome IN ('CONFIRMED','NO_EFFECT')) AND (record_org_canonical(r.organization_id)=canonical OR r.recipient_id=recipient OR r.recipient_id IN (SELECT recipient_id FROM record_org_recipient_sources rs WHERE record_org_canonical(rs.organization_id)=canonical))) THEN RETURN 'CONTACT_AMBIGUOUS'; END IF;
 IF EXISTS(SELECT 1 FROM record_org_reservations r WHERE record_org_reservation_live(r.id) AND r.experiment_id IS DISTINCT FROM exp AND (record_org_canonical(r.organization_id)=canonical OR r.recipient_id=recipient OR r.recipient_id IN (SELECT recipient_id FROM record_org_recipient_sources rs WHERE record_org_canonical(rs.organization_id)=canonical))) THEN RETURN 'RESERVED_ELSEWHERE'; END IF;
 IF EXISTS(SELECT 1 FROM record_org_conflicts conflict WHERE (record_org_canonical(conflict.organization_id)=canonical OR record_org_canonical(conflict.matched_id)=canonical) AND NOT EXISTS(SELECT 1 FROM record_org_identity_decisions d WHERE d.conflict_id=conflict.id)) THEN RETURN 'IDENTITY_CONFLICT'; END IF;
 IF canonical IS DISTINCT FROM org THEN RETURN 'IDENTITY_MERGED'; END IF;
 RETURN NULL;
END $$;
CREATE FUNCTION record_org_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE e record_org_evidence; snapshot jsonb; value text; namespace text; r record_org_reservations; source record_org_recipient_sources;
 b record_org_bindings; retained gov_retained; call gov_calls; operation gov_operations; config gov_configs; proof gov_evidence;
 effect record_org_effects; prior record_org_observations; actor uuid;
BEGIN
 PERFORM pg_advisory_xact_lock(730803);
 IF TG_TABLE_NAME='record_org_policy' THEN
  IF TG_OP='UPDATE' AND OLD.key_fingerprint IS NULL AND NEW.id=OLD.id AND NEW.owns_pgcrypto=OLD.owns_pgcrypto AND NEW.key_fingerprint=encode(sha256(convert_to(current_setting('alon.organization_key',true),'UTF8')),'hex') AND octet_length(convert_to(current_setting('alon.organization_key',true),'UTF8'))=32 THEN RETURN NEW; END IF;
  RAISE EXCEPTION 'immutable identity key policy';
 END IF;
 PERFORM record_org_require_key();
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable organization record'; END IF;
 IF TG_TABLE_NAME='record_org_evidence' THEN
  SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
  SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
  snapshot:=record_org_snapshot(NEW.retained_id,NEW.value_index);
  IF ROW(retained.call_id,retained.grant_id,retained.grant_version,retained.expires_at,call.operation_id,call.experiment_id) IS DISTINCT FROM ROW(NEW.call_id,NEW.grant_id,NEW.grant_version,NEW.expires_at,NEW.operation_id,NEW.experiment_id)
   OR NEW.snapshot_hash IS DISTINCT FROM encode(sha256(convert_to(retained.values->>NEW.value_index,'UTF8')),'hex') OR NEW.observed_at>record_org_now()
  THEN RAISE EXCEPTION 'exact organization provenance required'; END IF;
 ELSIF TG_TABLE_NAME IN ('record_org_keys','record_org_locations') THEN
  SELECT * INTO e FROM record_org_evidence WHERE id=NEW.evidence_id;
  snapshot:=record_org_snapshot(e.retained_id,e.value_index);
  IF TG_TABLE_NAME='record_org_locations' THEN
   IF NEW.source_index>=jsonb_array_length(snapshot->'locations') THEN RAISE EXCEPTION 'invalid location evidence'; END IF;
  ELSE
   IF NEW.source_index=-1 AND NEW.kind='NAME' THEN value:=snapshot->>'canonical_name'; namespace:='global';
   ELSIF NEW.source_index=-1 AND NEW.kind='DOMAIN' THEN value:=snapshot->>'canonical_domain'; namespace:='global';
   ELSIF NEW.kind IN ('REGISTERED_ID','PROVIDER_ID','OFFICIAL_URL') THEN
    IF snapshot->'identifiers'->NEW.source_index->>'kind' IS DISTINCT FROM NEW.kind THEN RAISE EXCEPTION 'identifier kind mismatch'; END IF;
    value:=snapshot->'identifiers'->NEW.source_index->>'value'; namespace:=snapshot->'identifiers'->NEW.source_index->>'namespace';
   ELSE
    IF snapshot->'aliases'->NEW.source_index->>'kind' IS DISTINCT FROM NEW.kind THEN RAISE EXCEPTION 'alias kind mismatch'; END IF;
    value:=snapshot->'aliases'->NEW.source_index->>'value'; namespace:='global';
   END IF;
   IF NEW.namespace IS DISTINCT FROM namespace OR NEW.lookup_hash IS DISTINCT FROM record_org_lookup(value) OR (NEW.kind='REGISTERED_ID' AND namespace !~ '^[A-Z]{2}$') THEN RAISE EXCEPTION 'invalid identity lookup'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_org_bindings' THEN
  SELECT * INTO e FROM record_org_evidence WHERE id=NEW.evidence_id;
  IF e.experiment_id IS DISTINCT FROM NEW.experiment_id OR NOT EXISTS(SELECT 1 FROM supply_identities i WHERE i.id=NEW.identity_id AND i.experiment_id=NEW.experiment_id AND i.valid_until>record_org_now()) THEN RAISE EXCEPTION 'invalid provisional identity binding'; END IF;
  snapshot:=record_org_snapshot(e.retained_id,e.value_index);
  IF EXISTS(SELECT 1 FROM jsonb_array_elements(snapshot->'identifiers') ident WHERE ident->>'kind'='REGISTERED_ID' AND NOT EXISTS(SELECT 1 FROM record_org_keys k WHERE k.kind='REGISTERED_ID' AND k.namespace=ident->>'namespace' AND k.lookup_hash=record_org_lookup(ident->>'value') AND (record_org_canonical(k.organization_id)=record_org_canonical(NEW.organization_id) OR EXISTS(SELECT 1 FROM record_org_conflicts conflict WHERE conflict.organization_id=NEW.organization_id AND conflict.matched_id=k.organization_id AND conflict.evidence_id=NEW.evidence_id)))) THEN RAISE EXCEPTION 'registered identity claim missing'; END IF;
 ELSIF TG_TABLE_NAME='record_org_identity_decisions' THEN
  IF NOT EXISTS(SELECT 1 FROM record_operators WHERE id=NEW.acted_by AND status='ACTIVE' AND auth_subject IS NOT NULL)
   OR record_org_evidence_current(NEW.evidence_id) IS NOT TRUE
   OR NOT EXISTS(SELECT 1 FROM record_org_conflicts conflict WHERE conflict.id=NEW.conflict_id AND EXISTS(SELECT 1 FROM record_org_evidence ev WHERE ev.id=NEW.evidence_id AND ev.organization_id IN (conflict.organization_id,conflict.matched_id)) AND ((NEW.resolution='SAME_ORGANIZATION' AND record_org_canonical(conflict.organization_id)=record_org_canonical(conflict.matched_id)) OR (NEW.resolution='INDEPENDENT_BUSINESS' AND record_org_canonical(conflict.organization_id)<>record_org_canonical(conflict.matched_id))))
  THEN RAISE EXCEPTION 'supported operator identity resolution required'; END IF;
 ELSIF TG_TABLE_NAME='record_org_recipient_sources' THEN
  SELECT * INTO b FROM record_org_bindings WHERE id=NEW.binding_id;
  SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
  IF (SELECT lookup_hash FROM record_org_recipients WHERE id=NEW.recipient_id) IS DISTINCT FROM record_org_email_lookup(NEW.retained_id,NEW.value_index)
   OR NOT EXISTS(SELECT 1 FROM supply_candidates c WHERE c.id=NEW.candidate_id AND c.identity_id=b.identity_id AND c.experiment_id=NEW.experiment_id)
   OR NOT EXISTS(SELECT 1 FROM supply_facts f WHERE f.id=NEW.source_fact_id AND f.identity_id=b.identity_id AND f.kind='SOURCE_EMAIL' AND f.contact_ref=f.id AND f.valid_until>record_org_now())
   OR NOT (EXISTS(SELECT 1 FROM contact_cases cc WHERE cc.candidate_id=NEW.candidate_id AND cc.source_fact_id=NEW.source_fact_id AND cc.brave_call_id=retained.call_id AND cc.presence='PRESENT' AND cc.valid_until>record_org_now()) OR EXISTS(SELECT 1 FROM contact_attempts ca WHERE ca.candidate_id=NEW.candidate_id AND ca.output_fact_id=NEW.source_fact_id AND ca.call_id=retained.call_id AND ca.outcome='FOUND' AND ca.valid_until>record_org_now()))
  THEN RAISE EXCEPTION 'exact supported contact source required'; END IF;
 ELSIF TG_TABLE_NAME='record_org_admissions' THEN
  SELECT * INTO b FROM record_org_bindings WHERE id=NEW.binding_id;
  IF record_org_block_reason(NEW.organization_id,NULL,NEW.experiment_id) IS NOT NULL OR record_org_evidence_current(b.evidence_id) IS NOT TRUE THEN RAISE EXCEPTION 'protected working candidate'; END IF;
 ELSIF TG_TABLE_NAME='record_org_reservations' THEN
  SELECT * INTO source FROM record_org_recipient_sources WHERE id=NEW.source_id;
  IF record_org_block_reason(NEW.organization_id,NEW.recipient_id,NEW.experiment_id) IS NOT NULL
   OR record_org_email_lookup(source.retained_id,source.value_index) IS DISTINCT FROM (SELECT lookup_hash FROM record_org_recipients WHERE id=NEW.recipient_id)
   OR NOT EXISTS(SELECT 1 FROM record_org_admissions a WHERE a.organization_id=NEW.organization_id AND a.experiment_id=NEW.experiment_id)
   OR EXISTS(SELECT 1 FROM record_org_reservations reserved_row WHERE record_org_reservation_live(reserved_row.id) AND (record_org_canonical(reserved_row.organization_id)=record_org_canonical(NEW.organization_id) OR reserved_row.recipient_id=NEW.recipient_id))
  THEN RAISE EXCEPTION 'organization or recipient reservation conflict'; END IF;
 ELSIF TG_TABLE_NAME='record_org_effects' THEN
  SELECT * INTO r FROM record_org_reservations WHERE id=NEW.reservation_id;
  SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id FOR UPDATE;
  SELECT * INTO operation FROM gov_operations WHERE id=NEW.operation_id;
  SELECT * INTO config FROM gov_configs WHERE id=call.config_id;
  IF call.state IS DISTINCT FROM 'RESERVED' OR call.dispatch_at IS NOT NULL OR record_org_reservation_live(r.id) IS NOT TRUE
   OR operation.service IS DISTINCT FROM 'send-gateway' OR operation.agent_id IS NOT NULL OR config.capability IS DISTINCT FROM 'GMAIL_SEND'
   OR ROW(call.operation_id,call.experiment_id,r.experiment_id) IS DISTINCT FROM ROW(NEW.operation_id,NEW.experiment_id,NEW.experiment_id)
   OR NEW.recipient_lookup_hash IS DISTINCT FROM (SELECT lookup_hash FROM record_org_recipients WHERE id=r.recipient_id)
   OR record_org_block_reason(r.organization_id,r.recipient_id,r.experiment_id) IS NOT NULL
  THEN RAISE EXCEPTION 'invalid gateway effect binding'; END IF;
 ELSIF TG_TABLE_NAME='record_org_observations' THEN
  SELECT * INTO effect FROM record_org_effects WHERE id=NEW.effect_id;
  SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id FOR UPDATE;
  SELECT * INTO proof FROM gov_evidence WHERE id=NEW.result_evidence_id;
  SELECT * INTO prior FROM record_org_observations WHERE effect_id=NEW.effect_id AND outcome='AMBIGUOUS';
  IF NEW.observed_at>record_org_now() OR EXISTS(SELECT 1 FROM record_org_releases WHERE reservation_id=NEW.reservation_id) OR EXISTS(SELECT 1 FROM record_org_observations WHERE effect_id=NEW.effect_id AND outcome IN ('CONFIRMED','NO_EFFECT')) THEN RAISE EXCEPTION 'terminal or invalid gateway observation'; END IF;
  IF NEW.outcome='AMBIGUOUS' THEN
   IF call.state IS DISTINCT FROM 'RECONCILING' OR call.dispatch_at IS NULL OR NEW.reconciles_id IS NOT NULL THEN RAISE EXCEPTION 'uncertain dispatched call required'; END IF;
  ELSIF NEW.outcome='CONFIRMED' THEN
   IF call.state IS DISTINCT FROM 'FINAL' OR call.result_metadata->>'status' IS DISTINCT FROM 'SUCCEEDED'
    OR call.result_metadata->>'capability' IS DISTINCT FROM 'GMAIL_SEND' OR call.result_metadata->>'external_request_id' IS DISTINCT FROM NEW.provider_request_id
    OR ROW(proof.call_id,proof.kind,proof.mode,proof.registered_by) IS DISTINCT FROM ROW(NEW.call_id,'PROVIDER_RESULT'::text,'TRUSTED_REFERENCE'::text,NEW.call_id)
    OR NEW.reconciles_id IS DISTINCT FROM prior.id
   THEN RAISE EXCEPTION 'positive correlated gateway evidence required'; END IF;
  ELSE
   IF call.state IS DISTINCT FROM 'RELEASED' OR call.dispatch_at IS NOT NULL OR NEW.reconciles_id IS NOT NULL OR prior.id IS NOT NULL
    OR NOT EXISTS(SELECT 1 FROM gov_settlements settlement WHERE settlement.call_id=NEW.call_id AND settlement.kind='PROVEN_UNUSED' AND settlement.evidence_id=NEW.result_evidence_id)
   THEN RAISE EXCEPTION 'proven unused effect required'; END IF;
  END IF;
 ELSIF TG_TABLE_NAME='record_org_releases' THEN
  SELECT * INTO r FROM record_org_reservations WHERE id=NEW.reservation_id;
  IF record_operator_authorized(r.experiment_id,NEW.released_by) IS NOT TRUE OR EXISTS(SELECT 1 FROM record_org_observations WHERE reservation_id=r.id AND outcome IN ('CONFIRMED','AMBIGUOUS')) THEN RAISE EXCEPTION 'unsafe reservation release'; END IF;
  SELECT * INTO effect FROM record_org_effects WHERE reservation_id=r.id;
  IF effect.id IS NOT NULL THEN
   SELECT * INTO call FROM gov_calls WHERE id=effect.call_id FOR UPDATE;
   IF call.state IS DISTINCT FROM 'RELEASED' OR call.dispatch_at IS NOT NULL OR NOT EXISTS(SELECT 1 FROM gov_settlements st WHERE st.call_id=call.id AND st.kind='PROVEN_UNUSED' AND st.evidence_id=NEW.evidence_id) THEN RAISE EXCEPTION 'effect cancellation proof required'; END IF;
  ELSIF NEW.evidence_id IS NOT NULL THEN RAISE EXCEPTION 'unrelated release evidence'; END IF;
 ELSIF TG_TABLE_NAME IN ('record_org_suppressions','record_org_merges') THEN
  IF NOT EXISTS(SELECT 1 FROM record_operators WHERE id=NEW.acted_by AND status='ACTIVE' AND auth_subject IS NOT NULL) THEN RAISE EXCEPTION 'active operator required'; END IF;
  IF TG_TABLE_NAME='record_org_merges' THEN
   IF record_org_canonical(NEW.surviving_id)=NEW.losing_id OR record_org_canonical(NEW.losing_id)<>NEW.losing_id OR record_org_canonical(NEW.surviving_id)<>NEW.surviving_id
    OR NOT EXISTS(SELECT 1 FROM record_org_evidence ev WHERE ev.id=NEW.evidence_id AND ev.organization_id IN (NEW.losing_id,NEW.surviving_id) AND record_org_evidence_current(ev.id))
    OR (SELECT count(*) FROM record_org_reservations reserved_row WHERE record_org_reservation_live(reserved_row.id) AND record_org_canonical(reserved_row.organization_id) IN (NEW.losing_id,NEW.surviving_id) AND NOT EXISTS(SELECT 1 FROM record_org_observations WHERE reservation_id=reserved_row.id AND outcome='CONFIRMED'))>1
   THEN RAISE EXCEPTION 'unsafe organization merge'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE VIEW record_org_working_candidates AS SELECT a.* FROM record_org_admissions a JOIN record_org_bindings b ON b.id=a.binding_id WHERE record_org_block_reason(a.organization_id,NULL,a.experiment_id) IS NULL AND record_org_evidence_current(b.evidence_id);
CREATE VIEW record_org_contact_state AS SELECT org.id AS organization_id, CASE WHEN EXISTS(SELECT 1 FROM record_org_observations o JOIN record_org_reservations r ON r.id=o.reservation_id WHERE record_org_canonical(r.organization_id)=record_org_canonical(org.id) AND o.outcome='CONFIRMED') THEN 'CONTACTED' WHEN EXISTS(SELECT 1 FROM record_org_observations o JOIN record_org_reservations r ON r.id=o.reservation_id WHERE record_org_canonical(r.organization_id)=record_org_canonical(org.id) AND o.outcome='AMBIGUOUS' AND NOT EXISTS(SELECT 1 FROM record_org_observations resolved WHERE resolved.reconciles_id=o.id)) THEN 'CONTACT_AMBIGUOUS' WHEN EXISTS(SELECT 1 FROM record_org_reservations r WHERE record_org_canonical(r.organization_id)=record_org_canonical(org.id) AND record_org_reservation_live(r.id)) THEN 'RESERVED_BY_EXPERIMENT' ELSE 'NEVER_CONTACTED' END AS state FROM record_org_organizations org;

CREATE TRIGGER record_org_policy_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_policy FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_organizations_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_organizations FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_evidence_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_evidence FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_keys_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_keys FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_locations_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_locations FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_bindings_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_bindings FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_recipients_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_recipients FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_recipient_sources_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_recipient_sources FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_admissions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_admissions FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_reservations_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_reservations FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_releases_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_releases FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_effects_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_effects FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_observations_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_observations FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_suppressions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_suppressions FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_merges_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_merges FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_exclusions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_exclusions FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_conflicts_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_conflicts FOR EACH ROW EXECUTE FUNCTION record_org_guard();
CREATE TRIGGER record_org_identity_decisions_guard BEFORE INSERT OR UPDATE OR DELETE ON record_org_identity_decisions FOR EACH ROW EXECUTE FUNCTION record_org_guard();""")


def downgrade() -> None:
    op.execute(r"""CREATE TEMP TABLE org_extension_remove(value boolean) ON COMMIT DROP; INSERT INTO org_extension_remove SELECT owns_pgcrypto FROM record_org_policy WHERE id=1;
DROP VIEW record_org_working_candidates; DROP VIEW record_org_contact_state;
DROP TRIGGER record_org_policy_guard ON record_org_policy;
DROP TRIGGER record_org_organizations_guard ON record_org_organizations;
DROP TRIGGER record_org_evidence_guard ON record_org_evidence;
DROP TRIGGER record_org_keys_guard ON record_org_keys;
DROP TRIGGER record_org_locations_guard ON record_org_locations;
DROP TRIGGER record_org_bindings_guard ON record_org_bindings;
DROP TRIGGER record_org_recipients_guard ON record_org_recipients;
DROP TRIGGER record_org_recipient_sources_guard ON record_org_recipient_sources;
DROP TRIGGER record_org_admissions_guard ON record_org_admissions;
DROP TRIGGER record_org_reservations_guard ON record_org_reservations;
DROP TRIGGER record_org_releases_guard ON record_org_releases;
DROP TRIGGER record_org_effects_guard ON record_org_effects;
DROP TRIGGER record_org_observations_guard ON record_org_observations;
DROP TRIGGER record_org_suppressions_guard ON record_org_suppressions;
DROP TRIGGER record_org_merges_guard ON record_org_merges;
DROP TRIGGER record_org_exclusions_guard ON record_org_exclusions;
DROP TRIGGER record_org_conflicts_guard ON record_org_conflicts;
DROP TRIGGER record_org_identity_decisions_guard ON record_org_identity_decisions;
DROP FUNCTION record_org_guard();
DROP FUNCTION record_org_block_reason(uuid,uuid,uuid);
DROP FUNCTION record_org_reservation_live(uuid);
DROP FUNCTION record_org_evidence_current(uuid);
DROP FUNCTION record_org_canonical(uuid);
DROP FUNCTION record_org_email_lookup(uuid,integer);
DROP FUNCTION record_org_snapshot(uuid,integer);
DROP FUNCTION record_org_source_current(uuid,text);
DROP FUNCTION record_org_lookup(text);
DROP FUNCTION record_org_require_key();
DROP FUNCTION record_org_now();
DROP TABLE record_org_identity_decisions;
DROP TABLE record_org_conflicts;
DROP TABLE record_org_exclusions;
DROP TABLE record_org_merges;
DROP TABLE record_org_suppressions;
DROP TABLE record_org_observations;
DROP TABLE record_org_effects;
DROP TABLE record_org_releases;
DROP TABLE record_org_reservations;
DROP TABLE record_org_admissions;
DROP TABLE record_org_recipient_sources;
DROP TABLE record_org_recipients;
DROP TABLE record_org_bindings;
DROP TABLE record_org_locations;
DROP TABLE record_org_keys;
DROP TABLE record_org_evidence;
DROP TABLE record_org_organizations;
DROP TABLE record_org_policy;
DO $$ BEGIN IF (SELECT value FROM org_extension_remove) THEN DROP EXTENSION pgcrypto; END IF; END $$;""")
