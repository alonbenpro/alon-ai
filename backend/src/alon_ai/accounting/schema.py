"""Only L02 governance roots; L03 must bind these to its business records.

Immutable facts have database UPDATE/DELETE guards installed by migration.
Numeric is deliberately unscaled with explicit bounds/scale checks: typmod numeric
would silently round invalid input before a CHECK could reject it.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alon_ai.providers.contracts import Capability, OperationRunKind, Provider

metadata = MetaData()
U = UUID(as_uuid=True)
T = DateTime(timezone=True)
N = Numeric()


def col(name, typ, **kw):
    return Column(name, typ, nullable=kw.pop("nullable", False), **kw)


def table(name, *parts):
    return Table("gov_" + name, metadata, *parts)


def enumcheck(name, values):
    return CheckConstraint(
        name + " IN (" + ",".join("'" + v + "'" for v in values) + ")"
    )


def money(name, *, positive=False, scale=24):
    return CheckConstraint(
        f"{name} {'>' if positive else '>='} 0 AND {name} < 1000000000000000000000000 AND scale({name}) <= {scale}"
    )


def timeline():
    return CheckConstraint("effective_at < expires_at")


experiments = table(
    "experiments",
    col("id", U, primary_key=True),
    col("enabled", Boolean, server_default="true"),
)
workflows = table(
    "workflows",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    ForeignKeyConstraint(["experiment_id"], ["gov_experiments.id"]),
    UniqueConstraint("id", "experiment_id"),
)
agents = table(
    "agents",
    col("id", U, primary_key=True),
    col("workflow_id", U),
    ForeignKeyConstraint(["workflow_id"], ["gov_workflows.id"]),
    UniqueConstraint("id", "workflow_id"),
)
operations = table(
    "operations",
    col("id", U, primary_key=True),
    col("experiment_id", U),
    col("workflow_id", U),
    col("kind", String),
    col("agent_id", U, nullable=True),
    col("service", String, nullable=True),
    col("config_version", U),
    col("gate_kind", String),
    ForeignKeyConstraint(
        ["workflow_id", "experiment_id"],
        ["gov_workflows.id", "gov_workflows.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["agent_id", "workflow_id"], ["gov_agents.id", "gov_agents.workflow_id"]
    ),
    UniqueConstraint("id", "workflow_id", "experiment_id", "config_version"),
    UniqueConstraint("id", "workflow_id", "experiment_id"),
    enumcheck("kind", list(OperationRunKind)),
    enumcheck("gate_kind", ["NONE", "SUPPLY", "CONTACT"]),
    CheckConstraint(
        "(agent_id IS NOT NULL AND service IS NULL) OR (agent_id IS NULL AND service IN ('provider-executor','contact-resolution','campaign-supply','send-gateway','calendar-gateway'))"
    ),
    CheckConstraint("agent_id IS NOT NULL OR service IS NOT NULL"),
)

# One authority root serializes policy activation, grant insertion/revocation and dispatch/retention.
authorities = table(
    "authorities",
    col("account", String, primary_key=True),
    col("capability", String, primary_key=True),
    col("enabled", Boolean, server_default="true"),
    col("policy_id", U, nullable=True),
    col("window_start", T, nullable=True),
    col("quota_used", Integer, server_default="0"),
    col("active", Integer, server_default="0"),
    col("failures", Integer, server_default="0"),
    col("failure_start", T, nullable=True),
    col("open_until", T, nullable=True),
    col("probe_id", U, nullable=True),
    UniqueConstraint("account", "capability"),
    enumcheck("capability", list(Capability)),
    CheckConstraint("account ~ '^[A-Za-z0-9_-]{1,100}$'"),
    CheckConstraint("quota_used>=0 AND active>=0 AND failures>=0"),
)
policies = table(
    "policies",
    col("id", U, primary_key=True),
    col("account", String),
    col("capability", String),
    col("data", JSONB),
    ForeignKeyConstraint(
        ["account", "capability"],
        ["gov_authorities.account", "gov_authorities.capability"],
    ),
)
# policy FK intentionally from policies to authority; activate only exact account/capability in repository.
grants = table(
    "grants",
    col("id", U, primary_key=True),
    col("version", Integer, primary_key=True),
    col("account", String),
    col("capability", String),
    col("effective_at", T),
    col("expires_at", T),
    col("data", JSONB),
    timeline(),
    CheckConstraint("version > 0"),
    ForeignKeyConstraint(
        ["account", "capability"],
        ["gov_authorities.account", "gov_authorities.capability"],
    ),
)
grant_events = table(
    "grant_events",
    col("id", U, primary_key=True),
    col("grant_id", U),
    col("grant_version", Integer),
    col("data", JSONB),
    ForeignKeyConstraint(
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
)
prices = table(
    "prices",
    col("id", U, primary_key=True),
    col("capability", String),
    col("component", String),
    col("currency", String(3)),
    col("unit_price", N),
    col("unit_quantity", N),
    col("currency_quantum", N),
    col("effective_at", T),
    col("expires_at", T),
    col("evidence_id", U),
    col("rounding_version", String),
    timeline(),
    money("unit_price", scale=12),
    money("unit_quantity", positive=True, scale=12),
    enumcheck("capability", list(Capability)),
    CheckConstraint("currency ~ '^[A-Z]{3}$'"),
    CheckConstraint("currency_quantum IN (1,.1,.01,.001,.0001)"),
)
fx = table(
    "fx",
    col("id", U, primary_key=True),
    col("currency", String(3)),
    col("quote_currency", String(3)),
    col("rate", N),
    col("effective_at", T),
    col("expires_at", T),
    col("evidence_id", U),
    col("rounding_version", String),
    timeline(),
    money("rate", positive=True, scale=12),
    CheckConstraint("currency ~ '^[A-Z]{3}$' AND quote_currency='ILS'"),
    CheckConstraint("currency <> 'ILS' OR rate=1"),
)
configs = table(
    "configs",
    col("id", U, primary_key=True),
    col("workflow_id", U),
    col("version", U),
    col("account", String),
    col("capability", String),
    col("fx_id", U),
    col("data", JSONB),
    ForeignKeyConstraint(["workflow_id"], ["gov_workflows.id"]),
    ForeignKeyConstraint(["fx_id"], ["gov_fx.id"]),
    ForeignKeyConstraint(
        ["account", "capability"],
        ["gov_authorities.account", "gov_authorities.capability"],
    ),
    UniqueConstraint("id", "workflow_id", "version"),
)
config_prices = table(
    "config_prices",
    col("config_id", U, primary_key=True),
    col("price_id", U, primary_key=True),
    col("max_quantity", N),
    ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
    ForeignKeyConstraint(["price_id"], ["gov_prices.id"]),
    money("max_quantity", positive=True, scale=12),
)

budget_accounts = table(
    "budget_accounts",
    col("id", U, primary_key=True),
    col("scope", String),
    col("experiment_id", U, nullable=True),
    col("workflow_id", U, nullable=True),
    col("operation_id", U, nullable=True),
    col("provider", String, nullable=True),
    col("currency", String(3)),
    col("effective_at", T),
    col("expires_at", T),
    col("limit", N),
    col("reserved", N, server_default="0"),
    col("accrued", N, server_default="0"),
    col("frozen", Boolean, server_default="false"),
    ForeignKeyConstraint(["experiment_id"], ["gov_experiments.id"]),
    ForeignKeyConstraint(
        ["workflow_id", "experiment_id"],
        ["gov_workflows.id", "gov_workflows.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["operation_id", "workflow_id", "experiment_id"],
        [
            "gov_operations.id",
            "gov_operations.workflow_id",
            "gov_operations.experiment_id",
        ],
    ),
    CheckConstraint(
        "(scope='GLOBAL' AND experiment_id IS NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NULL) OR (scope='PROVIDER' AND experiment_id IS NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NOT NULL) OR (scope='EXPERIMENT' AND experiment_id IS NOT NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NULL) OR (scope='EXPERIMENT_PROVIDER' AND experiment_id IS NOT NULL AND workflow_id IS NULL AND operation_id IS NULL AND provider IS NOT NULL) OR (scope='WORKFLOW' AND experiment_id IS NOT NULL AND workflow_id IS NOT NULL AND operation_id IS NULL AND provider IS NULL) OR (scope='OPERATION' AND experiment_id IS NOT NULL AND workflow_id IS NOT NULL AND operation_id IS NOT NULL AND provider IS NULL)"
    ),
    CheckConstraint("currency ~ '^[A-Z]{3}$'"),
    enumcheck("provider", list(Provider)),
    timeline(),
    money('"limit"'),
    money("reserved"),
    money("accrued"),
    UniqueConstraint(
        "scope",
        "experiment_id",
        "workflow_id",
        "operation_id",
        "provider",
        "currency",
        "effective_at",
        postgresql_nulls_not_distinct=True,
    ),
)

calls = table(
    "calls",
    col("id", U, primary_key=True),
    col("idempotency_key", U, unique=True),
    col("logical_operation_id", U, unique=True),
    col("experiment_id", U),
    col("workflow_id", U),
    col("operation_id", U),
    col("config_version", U),
    col("config_id", U),
    col("attribution", JSONB),
    col("request", JSONB),
    col("grant_id", U),
    col("grant_version", Integer),
    col("currency", String(3)),
    col("reserved", N),
    col("reserved_ils", N),
    col("accrued", N, server_default="0"),
    col("accrued_ils", N, server_default="0"),
    col("state", String),
    col("created_at", T),
    col("dispatch_at", T, nullable=True),
    col("lease_until", T, nullable=True),
    col("token", U, nullable=True),
    col("finished_at", T, nullable=True),
    col("policy_id", U, nullable=True),
    col("error", String, nullable=True),
    col("result_metadata", JSONB, nullable=True),
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
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
    enumcheck("state", ["RESERVED", "DISPATCHED", "RECONCILING", "FINAL", "RELEASED"]),
    CheckConstraint(
        "(state IN ('RESERVED','RELEASED') AND token IS NULL AND dispatch_at IS NULL AND lease_until IS NULL) OR (state IN ('DISPATCHED','RECONCILING','FINAL') AND token IS NOT NULL AND dispatch_at IS NOT NULL AND lease_until IS NOT NULL)"
    ),
    money("reserved"),
    money("reserved_ils"),
    money("accrued"),
    money("accrued_ils"),
)
allocations = table(
    "allocations",
    col("call_id", U, primary_key=True),
    col("account_id", U, primary_key=True),
    col("amount", N),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(["account_id"], ["gov_budget_accounts.id"]),
    money("amount"),
)
usage = table(
    "usage",
    col("id", U, primary_key=True),
    col("call_id", U),
    col("observation_key", U),
    col("component", String),
    col("price_id", U),
    col("currency", String(3)),
    col("quantity", N, nullable=True),
    col("cost", N, nullable=True),
    col("knowledge", String),
    col("supersedes_id", U, nullable=True),
    col("observed_at", T),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(["price_id"], ["gov_prices.id"]),
    ForeignKeyConstraint(
        ["supersedes_id", "call_id", "component"],
        ["gov_usage.id", "gov_usage.call_id", "gov_usage.component"],
    ),
    UniqueConstraint("id", "call_id", "component"),
    UniqueConstraint("call_id", "observation_key"),
    UniqueConstraint("supersedes_id"),
    money("cost"),
    money("quantity", scale=12),
    enumcheck("knowledge", ["ESTIMATE", "FINAL", "UNAVAILABLE"]),
    CheckConstraint(
        "(knowledge='UNAVAILABLE' AND cost IS NULL) OR (knowledge IN ('ESTIMATE','FINAL') AND cost IS NOT NULL)"
    ),
)
settlements = table(
    "settlements",
    col("id", U, primary_key=True),
    col("call_id", U),
    col("command_key", U),
    col("kind", String),
    col("cost", N),
    col("cost_ils", N),
    col("previous_cost", N),
    col("previous_ils", N),
    col("evidence_id", U),
    col("created_at", T),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    UniqueConstraint("call_id", "command_key"),
    enumcheck("kind", ["FINAL", "ADJUSTMENT", "PROVEN_UNUSED"]),
    money("cost"),
    money("cost_ils"),
    money("previous_cost"),
    money("previous_ils"),
)
cash_entries = table(
    "cash_entries",
    col("id", U, primary_key=True),
    col("command_key", U, unique=True),
    col("call_id", U),
    col("amount", N),
    col("amount_ils", N),
    col("evidence_id", U),
    col("corrects_id", U, nullable=True),
    col("created_at", T),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(["corrects_id"], ["gov_cash_entries.id"]),
    money("amount"),
    money("amount_ils"),
    UniqueConstraint("corrects_id"),
)
audit = table(
    "audit",
    col("id", U, primary_key=True),
    col("call_id", U, nullable=True),
    col("experiment_id", U, nullable=True),
    col("correlation_id", U, nullable=True),
    col("kind", String),
    col("reason", String, nullable=True),
    col("created_at", T),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
)
retained = table(
    "retained",
    col("id", U, primary_key=True),
    col("call_id", U),
    col("grant_id", U),
    col("grant_version", Integer),
    col("field", String),
    col("values", JSONB),
    col("expires_at", T),
    col("retention_rule_id", U),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
    UniqueConstraint("call_id", "field"),
    enumcheck(
        "field",
        ["URL", "TITLE", "TEXT", "EMAIL", "COMPANY", "RANKING", "MESSAGE", "EVENT"],
    ),
)

IMMUTABLE = (
    workflows,
    agents,
    operations,
    policies,
    grants,
    grant_events,
    prices,
    fx,
    configs,
    config_prices,
    allocations,
    usage,
    settlements,
    cash_entries,
    audit,
)
# Leading FK indexes for all joins/reconciliation/retention and dependent-scope lookup.
for tab in metadata.tables.values():
    for i, fk in enumerate(
        sorted(
            tab.foreign_key_constraints,
            key=lambda f: tuple(e.parent.name for e in f.elements),
        )
    ):
        Index(f"ix_{tab.name}_fk_{i}", *[tab.c[e.parent.name] for e in fk.elements])
Index(
    "ix_gov_grants_current",
    grants.c.account,
    grants.c.capability,
    grants.c.effective_at,
    grants.c.expires_at,
)
Index(
    "ix_gov_budget_current",
    budget_accounts.c.scope,
    budget_accounts.c.currency,
    budget_accounts.c.effective_at,
)
Index("ix_gov_retained_expiry", retained.c.expires_at)

# Exact binding for authority activation and dispatch policy, including circular FK.
policies.append_constraint(UniqueConstraint("id", "account", "capability"))
authorities.append_constraint(
    ForeignKeyConstraint(
        ["policy_id", "account", "capability"],
        ["gov_policies.id", "gov_policies.account", "gov_policies.capability"],
        use_alter=True,
        name="fk_gov_current_policy",
    )
)
calls.append_constraint(
    ForeignKeyConstraint(
        ["policy_id"], ["gov_policies.id"], name="fk_gov_dispatch_policy"
    )
)
retained.append_constraint(
    ForeignKeyConstraint(
        ["call_id", "grant_id", "grant_version"],
        ["gov_calls.id", "gov_calls.grant_id", "gov_calls.grant_version"],
        name="fk_gov_retained_call_grant",
    )
)
calls.append_constraint(UniqueConstraint("id", "grant_id", "grant_version"))
cash_entries.append_constraint(UniqueConstraint("id", "call_id"))
cash_entries.append_constraint(
    ForeignKeyConstraint(
        ["corrects_id", "call_id"],
        ["gov_cash_entries.id", "gov_cash_entries.call_id"],
        name="fk_gov_cash_correction_call",
    )
)
grants.append_constraint(
    CheckConstraint(
        "data->>'grant_id'=id::text AND (data->>'version')::integer=version AND data->>'account_handle'=account AND data->>'capability'=capability AND (data->>'effective_at')::timestamptz=effective_at AND (data->>'expires_at')::timestamptz=expires_at"
    )
)
configs.append_constraint(
    CheckConstraint(
        "data->>'id'=id::text AND data->>'workflow_id'=workflow_id::text AND data->>'version'=version::text AND data->>'fx_id'=fx_id::text AND data->'intended_use'->>'account_handle'=account AND data->'intended_use'->>'capability'=capability"
    )
)

grant_events.append_constraint(
    CheckConstraint(
        "((data->>'event_id')::uuid=id AND (data->>'grant_id')::uuid=grant_id AND (data->>'grant_version')::integer=grant_version) IS TRUE"
    )
)

evidence = table(
    "evidence",
    col("id", U, primary_key=True),
    col("kind", String),
    col("mode", String),
    col("registered_by", U),
    col("registered_at", T),
    col("call_id", U, nullable=True),
    enumcheck(
        "kind",
        [
            "PRICE",
            "FX",
            "GRANT",
            "GRANT_EVENT",
            "CONTROL",
            "RECONCILIATION",
            "INVOICE",
            "PROVIDER_RESULT",
        ],
    ),
    enumcheck("mode", ["SYNTHETIC", "TRUSTED_REFERENCE"]),
    CheckConstraint(
        "(kind IN ('RECONCILIATION','INVOICE','PROVIDER_RESULT') AND call_id IS NOT NULL) OR (kind NOT IN ('RECONCILIATION','INVOICE','PROVIDER_RESULT') AND call_id IS NULL)"
    ),
    ForeignKeyConstraint(
        ["call_id"], ["gov_calls.id"], use_alter=True, name="fk_gov_evidence_call"
    ),
)
for tab in (prices, fx, settlements, cash_entries):
    tab.append_constraint(
        ForeignKeyConstraint(
            ["evidence_id"], ["gov_evidence.id"], name="fk_" + tab.name + "_evidence"
        )
    )
# JSON proof IDs also have relational columns, checked by the immutable writer.
grants.append_column(col("evidence_id", U))
grant_events.append_column(col("evidence_id", U))
policies.append_column(col("evidence_id", U))
for tab in (grants, grant_events, policies):
    tab.append_constraint(
        ForeignKeyConstraint(
            ["evidence_id"], ["gov_evidence.id"], name="fk_" + tab.name + "_evidence"
        )
    )
IMMUTABLE = IMMUTABLE + (evidence,)
Index("ix_gov_evidence_call", evidence.c.call_id)
for tab in (prices, fx, settlements, cash_entries, grants, grant_events, policies):
    Index("ix_" + tab.name + "_evidence", tab.c.evidence_id)

prices.append_column(col("model_identifier", String, nullable=True))
prices.append_constraint(
    CheckConstraint("currency IN ('USD','ILS') AND currency_quantum=.01")
)
prices.append_constraint(
    CheckConstraint(
        "(capability='OPENAI_GENERATE' AND model_identifier IS NOT NULL) OR (capability<>'OPENAI_GENERATE' AND model_identifier IS NULL)"
    )
)
fx.append_constraint(CheckConstraint("currency IN ('USD','ILS')"))

# Frozen by the initial migration; closed SQL backstops for provider-record JSON.
# Root/config IDs are normalized columns. JSON copies must match those identities,
# and result usage references already-recorded immutable usage facts.
CALL_JSON_GUARD_SQL = r"""
CREATE FUNCTION gov_json_object(value jsonb, keys text[]) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(value)='object' AND value ?& keys
   AND value-keys='{}'::jsonb AND value->>'schema_version'='1'
   AND jsonb_typeof(value->'schema_version')='number',false)
$$;
CREATE FUNCTION gov_json_uuid(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(value)='string' AND value#>>'{}' ~
 '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',false)
$$;
CREATE FUNCTION gov_json_time(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
 RETURN COALESCE(jsonb_typeof(value)='string' AND value#>>'{}' ~
   '^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*(Z|[+-][0-9]{2}:[0-9]{2})$'
   AND isfinite((value#>>'{}')::timestamptz),false);
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;
CREATE FUNCTION gov_json_quantity(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
 IF value='null'::jsonb THEN RETURN true; END IF;
 RETURN COALESCE(jsonb_typeof(value)='string' AND value#>>'{}' ~
   '^[0-9]+(\.[0-9]+)?([Ee][+-]?[0-9]+)?$'
   AND (value#>>'{}')::numeric>=0 AND (value#>>'{}')::numeric<1e24
   AND scale((value#>>'{}')::numeric)<=12,false);
EXCEPTION WHEN OTHERS THEN RETURN false;
END $$;
CREATE FUNCTION gov_validate_call_json(item gov_calls) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE operation gov_operations; config gov_configs; a jsonb; r jsonb; m jsonb; u jsonb; actor jsonb;
BEGIN
 SELECT * INTO operation FROM gov_operations WHERE id=item.operation_id;
 SELECT * INTO config FROM gov_configs WHERE id=item.config_id;
 a:=item.attribution; r:=item.request; m:=item.result_metadata;
 IF operation.agent_id IS NOT NULL THEN
  actor:=jsonb_build_object('schema_version',1,'kind','agent','agent_run_id',operation.agent_id::text);
 ELSE
  actor:=jsonb_build_object('schema_version',1,'kind','system','service',operation.service);
 END IF;
 IF NOT gov_json_object(a,ARRAY['schema_version','experiment_id','workflow_run_id','operation_run_id',
   'operation_run_kind','actor','correlation_id','logical_operation_id','config_version','deadline'])
   OR NOT (a->>'experiment_id'=item.experiment_id::text AND a->>'workflow_run_id'=item.workflow_id::text
    AND a->>'operation_run_id'=item.operation_id::text AND a->>'config_version'=item.config_version::text
    AND a->>'logical_operation_id'=item.logical_operation_id::text AND a->>'operation_run_kind'=operation.kind
    AND a->'actor'=actor AND a->'actor'->>'schema_version'='1') IS TRUE
   OR NOT gov_json_uuid(a->'correlation_id') OR NOT gov_json_time(a->'deadline') THEN
  RAISE EXCEPTION 'invalid governance attribution' USING ERRCODE='23514';
 END IF;
 IF NOT gov_json_object(r,ARRAY['schema_version','config_ref','requested_count'])
   OR NOT (r->>'config_ref'=item.config_id::text AND jsonb_typeof(r->'requested_count')='number'
    AND r->>'requested_count' ~ '^[1-9][0-9]*$' AND (r->>'requested_count')::integer BETWEEN 1 AND 100
    AND r->'requested_count'=config.data->'requested_count') IS TRUE THEN
  RAISE EXCEPTION 'invalid governance request metadata' USING ERRCODE='23514';
 END IF;
 IF m IS NULL THEN RETURN; END IF;
 IF NOT gov_json_object(m,ARRAY['schema_version','capability','external_request_id','started_at','finished_at','status','error_code','usage'])
   OR NOT (m->>'capability'=config.capability AND item.state IN ('DISPATCHED','RECONCILING','FINAL')
    AND item.token IS NOT NULL AND item.finished_at IS NOT NULL
    AND m->>'status' IN ('SUCCEEDED','REFUSED','FAILED')
    AND ((m->>'status'='SUCCEEDED' AND m->'error_code'='null'::jsonb)
     OR (m->>'status'<>'SUCCEEDED' AND m->>'error_code' IN ('DENIED','CAPABILITY_MISMATCH','TIMEOUT','UNAVAILABLE','MALFORMED_RESPONSE','REFUSED','WRITE_AUTHORITY_REQUIRED')))
    AND (m->'external_request_id'='null'::jsonb OR (jsonb_typeof(m->'external_request_id')='string' AND m->>'external_request_id' ~ '^[A-Za-z0-9_-]{1,100}$'))
    AND jsonb_typeof(m->'usage')='array') IS TRUE
   OR NOT gov_json_time(m->'started_at') OR NOT gov_json_time(m->'finished_at') THEN
  RAISE EXCEPTION 'invalid governance result metadata' USING ERRCODE='23514';
 END IF;
 IF (m->>'finished_at')::timestamptz < (m->>'started_at')::timestamptz THEN
  RAISE EXCEPTION 'invalid governance result timing' USING ERRCODE='23514';
 END IF;
 FOR u IN SELECT value FROM jsonb_array_elements(m->'usage') LOOP
  IF NOT gov_json_object(u,ARRAY['schema_version','component','quantity','currency','cost','knowledge','observation_key'])
    OR NOT gov_json_uuid(u->'observation_key') OR NOT gov_json_quantity(u->'quantity') OR NOT gov_json_quantity(u->'cost')
    OR NOT (u->>'currency'=item.currency AND u->>'knowledge' IN ('ESTIMATE','FINAL','UNAVAILABLE')
      AND ((u->>'knowledge'='UNAVAILABLE' AND u->'cost'='null'::jsonb)
       OR (u->>'knowledge'<>'UNAVAILABLE' AND u->'cost'<>'null'::jsonb))) IS TRUE THEN
   RAISE EXCEPTION 'invalid governance usage metadata' USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM gov_usage existing WHERE existing.call_id=item.id
    AND existing.observation_key::text=u->>'observation_key' AND existing.component=u->>'component'
    AND existing.currency=u->>'currency' AND existing.knowledge=u->>'knowledge'
    AND existing.quantity IS NOT DISTINCT FROM (u->>'quantity')::numeric
    AND existing.cost IS NOT DISTINCT FROM (u->>'cost')::numeric) THEN
   RAISE EXCEPTION 'governance usage metadata binding' USING ERRCODE='23514';
  END IF;
 END LOOP;
END $$;
"""
