"""Explicit operator identities and typed delivery/commercial profile versions."""

from alembic import op

revision = "20260913_05"
down_revision = "20260912_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE record_operators (
 id uuid PRIMARY KEY,
 auth_subject varchar(255), display_name varchar(120) NOT NULL,
 timezone varchar(100) NOT NULL, status varchar(16) NOT NULL,
 created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
 CONSTRAINT uq_record_operator_subject UNIQUE(auth_subject),
 CONSTRAINT ck_record_operator_status CHECK(status IN ('ACTIVE','DISABLED')),
 CONSTRAINT ck_record_operator_bound CHECK(status<>'ACTIVE' OR auth_subject IS NOT NULL),
 CONSTRAINT ck_record_operator_name CHECK(length(btrim(display_name)) BETWEEN 1 AND 120),
 CONSTRAINT ck_record_operator_subject CHECK(auth_subject IS NULL OR auth_subject ~ '^[^[:space:][:cntrl:]]{1,255}$')
);
-- Preserve historical references without inventing authenticated identities or
-- granting their old permission-like capability labels any new authority.
INSERT INTO record_operators(id,auth_subject,display_name,timezone,status,created_at,updated_at)
 SELECT operator_id,NULL,'Unbound historical operator','Asia/Jerusalem','DISABLED',min(created_at),min(created_at)
 FROM record_operator_profiles GROUP BY operator_id;
ALTER TABLE record_operator_profiles
 ADD COLUMN profile_schema_version integer NOT NULL DEFAULT 1,
 ADD COLUMN delivery jsonb, ADD COLUMN commercial jsonb, ADD COLUMN approved_by uuid,
 ADD CONSTRAINT fk_record_profile_operator FOREIGN KEY(operator_id) REFERENCES record_operators(id),
 ADD CONSTRAINT fk_record_profile_approver FOREIGN KEY(approved_by) REFERENCES record_operators(id),
 ADD CONSTRAINT ck_record_profile_shape CHECK(profile_schema_version=1 OR
  (profile_schema_version=2 AND delivery IS NOT NULL AND commercial IS NOT NULL
   AND approved_by IS NOT NULL AND approved_by=operator_id));
CREATE UNIQUE INDEX uq_record_profile_owner_version ON record_operator_profiles(operator_id,version) WHERE profile_schema_version=2;
CREATE INDEX ix_record_profile_approver ON record_operator_profiles(approved_by);

CREATE FUNCTION record_operator_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'operator history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (
    NEW.id IS DISTINCT FROM OLD.id OR NEW.created_at IS DISTINCT FROM OLD.created_at
    OR (OLD.auth_subject IS NOT NULL AND ROW(NEW.auth_subject,NEW.display_name,NEW.timezone)
        IS DISTINCT FROM ROW(OLD.auth_subject,OLD.display_name,OLD.timezone)))
 THEN RAISE EXCEPTION 'operator identity binding is immutable' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=NEW.timezone)
 THEN RAISE EXCEPTION 'invalid operator timezone' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER record_operator_guard BEFORE INSERT OR UPDATE OR DELETE ON record_operators
 FOR EACH ROW EXECUTE FUNCTION record_operator_guard();

CREATE FUNCTION record_profile_number(value jsonb, max_value numeric, places integer, positive boolean DEFAULT false, inclusive boolean DEFAULT true)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE number numeric;
BEGIN
 IF jsonb_typeof(value) IS DISTINCT FROM 'string' OR (value#>>'{}') !~ '^(0|[1-9][0-9]*)(\.[0-9]+)?$' THEN RETURN false; END IF;
 IF length(value#>>'{}')>32 THEN RETURN false; END IF;
 number := (value#>>'{}')::numeric;
 RETURN number>=0 AND (NOT positive OR number>0) AND scale(number)<=places
    AND ((inclusive AND number<=max_value) OR (NOT inclusive AND number<max_value));
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;
CREATE FUNCTION record_profile_entries(value jsonb, required boolean) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
 IF jsonb_typeof(value) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 RETURN jsonb_array_length(value) BETWEEN CASE WHEN required THEN 1 ELSE 0 END AND 100
    AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(value) x
      WHERE jsonb_typeof(x) IS DISTINCT FROM 'string' OR length(btrim(x#>>'{}')) NOT BETWEEN 1 AND 1000)
    AND jsonb_array_length(value)=(SELECT count(DISTINCT x) FROM jsonb_array_elements(value) x);
END $$;
CREATE FUNCTION record_profile_guard_v2() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable product record' USING ERRCODE='23514'; END IF;
 PERFORM 1 FROM record_operators WHERE id=NEW.operator_id AND auth_subject IS NOT NULL AND status='ACTIVE' FOR SHARE;
 IF NOT FOUND OR NEW.profile_schema_version IS DISTINCT FROM 2 OR NEW.approved_by IS DISTINCT FROM NEW.operator_id
 THEN RAISE EXCEPTION 'profile requires bound active owner approval' USING ERRCODE='23514'; END IF;
 IF NEW.version>1 AND NOT EXISTS(SELECT 1 FROM record_operator_profiles
   WHERE id=NEW.id AND version=NEW.version-1 AND operator_id=NEW.operator_id AND profile_schema_version=2)
 THEN RAISE EXCEPTION 'profile requires exact previous version' USING ERRCODE='23514'; END IF;
 IF record_profile_entries(NEW.capabilities,true) IS NOT TRUE OR record_profile_entries(NEW.constraints,false) IS NOT TRUE
 THEN RAISE EXCEPTION 'invalid profile entries' USING ERRCODE='23514'; END IF;
 IF (record_json_exact(NEW.delivery,ARRAY['schema_version','max_project_hours','hours_per_week','concurrent_projects'])
    AND NEW.delivery->'schema_version'='1'::jsonb
    AND record_profile_number(NEW.delivery->'max_project_hours',100000,2,true)
    AND record_profile_number(NEW.delivery->'hours_per_week',168,2,true)
    AND jsonb_typeof(NEW.delivery->'concurrent_projects')='number'
    AND (NEW.delivery->>'concurrent_projects') ~ '^[1-9][0-9]{0,2}$'
    AND (NEW.delivery->>'concurrent_projects')::numeric<=100) IS NOT TRUE
 THEN RAISE EXCEPTION 'invalid delivery limits' USING ERRCODE='23514'; END IF;
 IF (record_json_exact(NEW.commercial,ARRAY['schema_version','currency','hourly_cost','minimum_project_price',
       'minimum_margin_rate','maximum_discount_rate','minimum_deposit_rate'])
    AND NEW.commercial->'schema_version'='1'::jsonb
    AND NEW.commercial->>'currency' ~ '^[A-Z]{3}$'
    AND record_profile_number(NEW.commercial->'hourly_cost',1000000000000,6,false,false)
    AND record_profile_number(NEW.commercial->'minimum_project_price',1000000000000,6,false,false)
    AND record_profile_number(NEW.commercial->'minimum_margin_rate',1,6)
    AND record_profile_number(NEW.commercial->'maximum_discount_rate',1,6)
    AND record_profile_number(NEW.commercial->'minimum_deposit_rate',1,6)) IS NOT TRUE
 THEN RAISE EXCEPTION 'invalid commercial limits' USING ERRCODE='23514'; END IF;
 NEW.content_hash:=encode(sha256(convert_to(jsonb_build_object('profile_schema_version',NEW.profile_schema_version,
   'operator_id',NEW.operator_id,'capabilities',NEW.capabilities,'constraints',NEW.constraints,
   'delivery',NEW.delivery,'commercial',NEW.commercial,'approved_by',NEW.approved_by)::text,'UTF8')),'hex');
 RETURN NEW;
END $$;
DROP TRIGGER record_operator_profiles_guard ON record_operator_profiles;
CREATE TRIGGER record_operator_profiles_guard BEFORE INSERT OR UPDATE OR DELETE ON record_operator_profiles
 FOR EACH ROW EXECUTE FUNCTION record_profile_guard_v2();

CREATE FUNCTION record_profile_authorized(profile_id uuid, profile_version integer, actor_id uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 PERFORM 1 FROM record_operator_profiles p JOIN record_operators o ON o.id=p.operator_id
  WHERE p.id=profile_id AND p.version=profile_version AND p.profile_schema_version=2
    AND p.approved_by=p.operator_id AND p.operator_id=actor_id AND o.status='ACTIVE'
    AND o.auth_subject IS NOT NULL FOR SHARE OF o;
 RETURN FOUND;
END $$;
CREATE FUNCTION record_operator_authorized(experiment_id uuid, actor_id uuid)
RETURNS boolean LANGUAGE sql VOLATILE AS $$
 SELECT coalesce((SELECT record_profile_authorized(e.operator_profile_id,e.operator_profile_version,actor_id)
   FROM record_experiments e WHERE e.id=experiment_id),false)
$$;
""")


def downgrade() -> None:
    op.execute(r"""
DROP FUNCTION record_operator_authorized(uuid,uuid);
DROP FUNCTION record_profile_authorized(uuid,integer,uuid);
DROP TRIGGER record_operator_profiles_guard ON record_operator_profiles;
CREATE TRIGGER record_operator_profiles_guard BEFORE INSERT OR UPDATE OR DELETE ON record_operator_profiles
 FOR EACH ROW EXECUTE FUNCTION record_guard();
DROP FUNCTION record_profile_guard_v2();
DROP FUNCTION record_profile_entries(jsonb,boolean);
DROP FUNCTION record_profile_number(jsonb,numeric,integer,boolean,boolean);
DROP INDEX uq_record_profile_owner_version;
DROP INDEX ix_record_profile_approver;
ALTER TABLE record_operator_profiles DROP CONSTRAINT fk_record_profile_operator,
 DROP CONSTRAINT fk_record_profile_approver, DROP CONSTRAINT ck_record_profile_shape,
 DROP COLUMN approved_by, DROP COLUMN commercial, DROP COLUMN delivery, DROP COLUMN profile_schema_version;
DROP TABLE record_operators;
DROP FUNCTION record_operator_guard();
""")
