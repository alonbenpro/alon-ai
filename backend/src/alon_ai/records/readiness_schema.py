"""Immutable lead-readiness records layered over the existing supply graph.

These tables deliberately retain only governed receipt/provenance identities and
hashes.  Provider response content remains in ``gov_retained`` under its own
rights and expiry controls; the encrypted recipient source remains the only
address owner.
"""

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.accounting import schema as g


def table(name, *parts):
    return Table("record_readiness_" + name, g.metadata, *parts)


provider_results = table(
    "provider_results",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("candidate_id", g.U, nullable=True),
    g.col("batch_id", g.U),
    g.col("call_id", g.U, unique=True),
    g.col("operation_id", g.U),
    g.col("config_id", g.U),
    g.col("config_version", g.U),
    g.col("grant_id", g.U),
    g.col("grant_version", Integer),
    g.col("result_evidence_id", g.U, unique=True),
    g.col("retained_id", g.U, nullable=True),
    g.col("rights_mode", String(32)),
    g.col("rights_reason", String(32)),
    g.col("result_hash", String(64)),
    g.col("observed_at", g.T),
    g.col("valid_until", g.T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(["call_id"], ["gov_calls.id"]),
    ForeignKeyConstraint(["operation_id"], ["gov_operations.id"]),
    ForeignKeyConstraint(["config_id"], ["gov_configs.id"]),
    ForeignKeyConstraint(
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
    ForeignKeyConstraint(["result_evidence_id"], ["gov_evidence.id"]),
    ForeignKeyConstraint(["retained_id"], ["gov_retained.id"]),
    UniqueConstraint("id", "experiment_id", "candidate_id"),
    UniqueConstraint("id", "experiment_id", "batch_id"),
    CheckConstraint(
        "observed_at<valid_until AND result_hash ~ '^[0-9a-f]{64}$' AND batch_id IS NOT NULL"
    ),
    g.enumcheck("rights_mode", ["RETAIN_SCOPED_CONTENT"]),
    g.enumcheck("rights_reason", ["ALLOWED"]),
)

contactability_decisions = table(
    "contactability_decisions",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U, nullable=True),
    g.col("recipient_id", g.U, nullable=True),
    g.col("recipient_source_id", g.U, nullable=True),
    g.col("source_fact_id", g.U, nullable=True),
    g.col("verification_fact_id", g.U, nullable=True),
    g.col("provider_result_id", g.U, nullable=True),
    g.col("version", Integer),
    g.col("outcome", String(32)),
    g.col("reason_code", String(64)),
    g.col("payload_hash", String(64)),
    g.col("decided_by", g.U),
    g.col("decided_at", g.T),
    g.col("valid_until", g.T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["recipient_source_id", "experiment_id", "organization_id", "recipient_id"],
        [
            "record_org_recipient_sources.id",
            "record_org_recipient_sources.experiment_id",
            "record_org_recipient_sources.organization_id",
            "record_org_recipient_sources.recipient_id",
        ],
    ),
    ForeignKeyConstraint(
        ["source_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["verification_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["provider_result_id", "experiment_id", "candidate_id"],
        [
            "record_readiness_provider_results.id",
            "record_readiness_provider_results.experiment_id",
            "record_readiness_provider_results.candidate_id",
        ],
    ),
    UniqueConstraint("candidate_id", "version"),
    UniqueConstraint("id", "experiment_id", "candidate_id"),
    g.enumcheck("outcome", ["SUPPORTED_CONTACT_ADDRESS", "EMAIL_NOT_FOUND"]),
    CheckConstraint(
        "version>0 AND decided_at<valid_until AND payload_hash ~ '^[0-9a-f]{64}$'"
    ),
    CheckConstraint(
        "(outcome='SUPPORTED_CONTACT_ADDRESS' AND organization_id IS NOT NULL AND recipient_id IS NOT NULL AND recipient_source_id IS NOT NULL AND source_fact_id IS NOT NULL) OR (outcome='EMAIL_NOT_FOUND' AND organization_id IS NOT NULL AND recipient_id IS NULL AND recipient_source_id IS NULL AND source_fact_id IS NULL AND verification_fact_id IS NULL)"
    ),
)

research_plans = table(
    "research_plans",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("candidate_id", g.U),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("recipient_source_id", g.U),
    g.col("contactability_id", g.U, nullable=True),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("profile_criteria_hash", String(64)),
    g.col("artifact_id", g.U, unique=True),
    g.col("artifact_kind", String(64)),
    g.col("artifact_version", Integer),
    g.col("artifact_hash", String(64)),
    g.col("created_by", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["recipient_source_id", "experiment_id", "organization_id", "recipient_id"],
        [
            "record_org_recipient_sources.id",
            "record_org_recipient_sources.experiment_id",
            "record_org_recipient_sources.organization_id",
            "record_org_recipient_sources.recipient_id",
        ],
    ),
    ForeignKeyConstraint(
        ["contactability_id", "experiment_id", "candidate_id"],
        [
            "record_readiness_contactability_decisions.id",
            "record_readiness_contactability_decisions.experiment_id",
            "record_readiness_contactability_decisions.candidate_id",
        ],
    ),
    ForeignKeyConstraint(
        ["offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    ForeignKeyConstraint(
        [
            "artifact_id",
            "experiment_id",
            "artifact_kind",
            "artifact_version",
            "artifact_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("id", "experiment_id", "candidate_id"),
    CheckConstraint(
        "artifact_kind='RESEARCH_PLAN' AND artifact_version>0 AND artifact_hash ~ '^[0-9a-f]{64}$' AND profile_criteria_hash ~ '^[0-9a-f]{64}$'"
    ),
)

discovery_plans = table(
    "discovery_plans",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("batch_id", g.U, unique=True),
    g.col("offer_acceptance_id", g.U),
    g.col("offer_id", g.U),
    g.col("profile_id", g.U),
    g.col("policy_id", g.U),
    g.col("mode", String(24)),
    g.col("geography_filter_ids", ARRAY(g.U)),
    g.col("idea_artifact_id", g.U),
    g.col("idea_kind", String(64)),
    g.col("idea_version", Integer),
    g.col("idea_hash", String(64)),
    g.col("research_artifact_id", g.U),
    g.col("research_kind", String(64)),
    g.col("research_version", Integer),
    g.col("research_hash", String(64)),
    g.col("batch_plan_hash", String(64)),
    g.col("created_by", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["batch_id", "experiment_id"],
        ["supply_batches.id", "supply_batches.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["offer_acceptance_id", "experiment_id"],
        ["record_offer_acceptances.id", "record_offer_acceptances.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["idea_artifact_id", "experiment_id", "idea_kind", "idea_version", "idea_hash"],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    ForeignKeyConstraint(
        [
            "research_artifact_id",
            "experiment_id",
            "research_kind",
            "research_version",
            "research_hash",
        ],
        [
            "record_artifacts.id",
            "record_artifacts.experiment_id",
            "record_artifacts.kind",
            "record_artifacts.version",
            "record_artifacts.content_hash",
        ],
    ),
    UniqueConstraint("id", "experiment_id", "batch_id"),
    g.enumcheck("mode", ["LOCAL_BUSINESS", "ONLINE_COMPANY", "HYBRID"]),
    CheckConstraint(
        "idea_kind='IDEA_BRIEF' AND research_kind='MARKET_RESEARCH_REPORT' AND idea_version>0 AND research_version>0 AND idea_hash ~ '^[0-9a-f]{64}$' AND research_hash ~ '^[0-9a-f]{64}$' AND batch_plan_hash ~ '^[0-9a-f]{64}$'"
    ),
    CheckConstraint("mode='ONLINE_COMPANY' OR cardinality(geography_filter_ids)>0"),
)

research_runs = table(
    "research_runs",
    g.col("id", g.U, primary_key=True),
    g.col("plan_id", g.U),
    g.col("experiment_id", g.U),
    g.col("candidate_id", g.U),
    g.col("provider_result_id", g.U, nullable=True),
    g.col("independent_source_id", g.U, nullable=True),
    g.col("payload_hash", String(64)),
    g.col("completed_by", g.U),
    g.col("completed_at", g.T),
    ForeignKeyConstraint(
        ["plan_id", "experiment_id", "candidate_id"],
        [
            "record_readiness_research_plans.id",
            "record_readiness_research_plans.experiment_id",
            "record_readiness_research_plans.candidate_id",
        ],
    ),
    ForeignKeyConstraint(
        ["provider_result_id", "experiment_id", "candidate_id"],
        [
            "record_readiness_provider_results.id",
            "record_readiness_provider_results.experiment_id",
            "record_readiness_provider_results.candidate_id",
        ],
    ),
    ForeignKeyConstraint(
        ["independent_source_id", "experiment_id"],
        ["supply_references.id", "supply_references.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id", "candidate_id"),
    UniqueConstraint("id", "experiment_id"),
    CheckConstraint(
        "(provider_result_id IS NULL)<>(independent_source_id IS NULL) AND payload_hash ~ '^[0-9a-f]{64}$'"
    ),
)

evidence_links = table(
    "evidence_links",
    g.col("id", g.U, primary_key=True),
    g.col("run_id", g.U),
    g.col("dossier_id", g.U),
    g.col("dossier_evidence_id", g.U),
    g.col("experiment_id", g.U),
    g.col("payload_hash", String(64)),
    g.col("linked_by", g.U),
    g.col("linked_at", g.T),
    ForeignKeyConstraint(
        ["run_id", "experiment_id"],
        [
            "record_readiness_research_runs.id",
            "record_readiness_research_runs.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        ["dossier_id", "experiment_id"],
        [
            "record_qualification_dossiers.id",
            "record_qualification_dossiers.experiment_id",
        ],
    ),
    ForeignKeyConstraint(
        ["dossier_evidence_id", "dossier_id"],
        [
            "record_qualification_evidence.id",
            "record_qualification_evidence.dossier_id",
        ],
    ),
    UniqueConstraint("run_id", "dossier_evidence_id"),
    CheckConstraint("payload_hash ~ '^[0-9a-f]{64}$'"),
)

TABLES = (
    provider_results,
    contactability_decisions,
    research_plans,
    discovery_plans,
    research_runs,
    evidence_links,
)
IMMUTABLE_TABLES = tuple(table.name for table in TABLES)

# The migration installs these after creating TABLES.  The application performs
# richer current-rights checks; these guards make direct SQL unable to forge the
# normalized receipt/provenance graph or mutate its immutable history.
GUARD_SQL = r"""
CREATE FUNCTION record_readiness_provider_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE call gov_calls; operation supply_operations; proof gov_evidence; retained gov_retained;
BEGIN
 SELECT * INTO call FROM gov_calls WHERE id=NEW.call_id;
 SELECT * INTO operation FROM supply_operations WHERE operation_id=NEW.operation_id;
 SELECT * INTO proof FROM gov_evidence WHERE id=NEW.result_evidence_id;
 IF call.id IS NULL OR operation.operation_id IS NULL OR proof.id IS NULL
    OR call.state<>'FINAL' OR proof.kind<>'PROVIDER_RESULT' OR proof.call_id<>call.id
    OR NEW.experiment_id<>call.experiment_id OR NEW.operation_id<>call.operation_id
    OR NEW.config_id<>call.config_id OR NEW.config_version<>call.config_version
    OR NEW.grant_id<>call.grant_id OR NEW.grant_version<>call.grant_version
    OR NEW.batch_id<>operation.batch_id
    OR NEW.candidate_id IS DISTINCT FROM operation.candidate_id
 THEN RAISE EXCEPTION 'invalid readiness provider lineage'; END IF;
 IF NEW.observed_at>record_org_now() OR NEW.valid_until<=record_org_now() OR NOT EXISTS(
   SELECT 1 FROM gov_grants g JOIN gov_configs cfg ON cfg.id=call.config_id
   JOIN gov_authorities a ON a.account=g.account AND a.capability=g.capability
   WHERE g.id=call.grant_id AND g.version=call.grant_version
     AND g.effective_at<=record_org_now() AND g.expires_at>record_org_now()
     AND NEW.valid_until<=least(g.expires_at,NEW.observed_at+make_interval(secs=>(g.data->>'retention_seconds')::integer))
     AND (g.data->>'outbound_use_permitted')::boolean
     AND (g.data->'storage_fields') @> (cfg.data->'intended_use'->'required_fields')
     AND cfg.data->'intended_use'->>'purpose'=g.data->>'purpose' AND a.enabled
     AND NOT EXISTS(SELECT 1 FROM gov_grants newer WHERE newer.data->>'supersedes_id'=g.id::text AND newer.effective_at<=record_org_now() AND newer.expires_at>record_org_now())
     AND NOT EXISTS(SELECT 1 FROM gov_grant_events e WHERE e.grant_id=g.id AND e.grant_version=g.version AND (e.data->>'effective_at')::timestamptz<=record_org_now() AND e.data->>'kind'<>'ACTIVATED')
 ) THEN RAISE EXCEPTION 'provider source rights unavailable'; END IF;
 IF NEW.retained_id IS NOT NULL THEN
  SELECT * INTO retained FROM gov_retained WHERE id=NEW.retained_id;
  IF retained.id IS NULL OR retained.call_id<>call.id OR retained.grant_id<>call.grant_id
     OR retained.grant_version<>call.grant_version OR retained.expires_at<NEW.valid_until
     OR record_org_source_current(retained.id,retained.field) IS NOT TRUE
  THEN RAISE EXCEPTION 'invalid retained provider lineage'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_research_plan_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate supply_candidates; source record_org_recipient_sources; acceptance record_offer_acceptances; artifact record_artifacts;
BEGIN
 SELECT * INTO candidate FROM supply_candidates WHERE id=NEW.candidate_id;
 SELECT * INTO source FROM record_org_recipient_sources WHERE id=NEW.recipient_source_id;
 SELECT * INTO acceptance FROM record_offer_acceptances WHERE id=NEW.offer_acceptance_id;
 SELECT * INTO artifact FROM record_artifacts WHERE id=NEW.artifact_id;
 IF candidate.id IS NULL OR source.id IS NULL OR acceptance.id IS NULL OR artifact.id IS NULL
    OR candidate.experiment_id<>NEW.experiment_id OR source.experiment_id<>NEW.experiment_id
    OR source.candidate_id<>NEW.candidate_id OR source.organization_id<>NEW.organization_id OR source.recipient_id<>NEW.recipient_id
    OR acceptance.experiment_id<>NEW.experiment_id OR acceptance.offer_id<>NEW.offer_id OR acceptance.profile_id<>NEW.profile_id OR acceptance.policy_id<>NEW.policy_id
    OR artifact.experiment_id<>NEW.experiment_id OR artifact.kind<>NEW.artifact_kind OR artifact.version<>NEW.artifact_version OR artifact.content_hash<>NEW.artifact_hash
 THEN RAISE EXCEPTION 'invalid research plan lineage'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_research_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE plan record_readiness_research_plans; result record_readiness_provider_results; source supply_references;
BEGIN
 SELECT * INTO plan FROM record_readiness_research_plans WHERE id=NEW.plan_id;
 IF plan.id IS NULL OR plan.experiment_id<>NEW.experiment_id OR plan.candidate_id<>NEW.candidate_id THEN RAISE EXCEPTION 'invalid research run plan'; END IF;
 IF NEW.provider_result_id IS NOT NULL THEN
  SELECT * INTO result FROM record_readiness_provider_results WHERE id=NEW.provider_result_id;
  IF result.id IS NULL OR result.experiment_id<>NEW.experiment_id OR result.candidate_id<>NEW.candidate_id OR result.retained_id IS NULL THEN RAISE EXCEPTION 'invalid provider research provenance'; END IF;
 ELSE
  SELECT * INTO source FROM supply_references WHERE id=NEW.independent_source_id;
  IF source.id IS NULL OR source.experiment_id<>NEW.experiment_id OR source.kind<>'INDEPENDENT_SOURCE' THEN RAISE EXCEPTION 'invalid independent research provenance'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_evidence_link_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE run record_readiness_research_runs; plan record_readiness_research_plans; dossier record_qualification_dossiers; evidence record_qualification_evidence;
BEGIN
 SELECT * INTO run FROM record_readiness_research_runs WHERE id=NEW.run_id;
 SELECT * INTO dossier FROM record_qualification_dossiers WHERE id=NEW.dossier_id;
 SELECT * INTO evidence FROM record_qualification_evidence WHERE id=NEW.dossier_evidence_id;
 IF run.id IS NULL OR dossier.id IS NULL OR evidence.id IS NULL OR run.experiment_id<>NEW.experiment_id
    OR dossier.experiment_id<>NEW.experiment_id OR evidence.dossier_id<>dossier.id OR dossier.candidate_id<>run.candidate_id THEN RAISE EXCEPTION 'invalid research evidence lineage'; END IF;
 SELECT * INTO plan FROM record_readiness_research_plans WHERE id=run.plan_id;
 IF plan.offer_acceptance_id<>dossier.offer_acceptance_id THEN RAISE EXCEPTION 'stale research evidence offer'; END IF;
 IF run.provider_result_id IS NOT NULL AND evidence.source_ref<>('provider-result:'||run.provider_result_id::text) THEN RAISE EXCEPTION 'provider evidence provenance mismatch'; END IF;
 IF run.independent_source_id IS NOT NULL AND evidence.source_ref<>('independent-source:'||run.independent_source_id::text) THEN RAISE EXCEPTION 'independent evidence provenance mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION record_readiness_contact_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate supply_candidates; contact supply_contacts; source record_org_recipient_sources; binding record_org_bindings;
BEGIN
 SELECT * INTO candidate FROM supply_candidates WHERE id=NEW.candidate_id;
 SELECT * INTO contact FROM supply_contacts WHERE candidate_id=NEW.candidate_id;
 IF candidate.id IS NULL OR contact.candidate_id IS NULL OR candidate.experiment_id<>NEW.experiment_id
    OR NEW.valid_until>contact.valid_until THEN RAISE EXCEPTION 'invalid contactability lineage'; END IF;
 IF NEW.provider_result_id IS NULL OR NOT EXISTS(
  SELECT 1 FROM record_readiness_provider_results pr WHERE pr.id=NEW.provider_result_id AND pr.candidate_id=NEW.candidate_id
  AND (EXISTS(SELECT 1 FROM contact_cases cc WHERE cc.candidate_id=NEW.candidate_id AND cc.brave_call_id=pr.call_id)
   OR EXISTS(SELECT 1 FROM contact_attempts a WHERE a.candidate_id=NEW.candidate_id AND a.call_id=pr.call_id AND a.output_fact_id IN (contact.source_id,contact.verification_id)))
 ) THEN RAISE EXCEPTION 'missing governed contact receipt'; END IF;
 IF contact.verification_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM contact_attempts a JOIN contact_operations o ON o.operation_id=a.operation_id
  WHERE a.candidate_id=NEW.candidate_id AND a.output_fact_id=contact.verification_id
  AND o.source_fact_id=contact.source_id AND o.capability='HUNTER_EMAIL_VERIFICATION'
  AND ((NEW.outcome='SUPPORTED_CONTACT_ADDRESS' AND a.outcome='VALID')
   OR (NEW.outcome='EMAIL_NOT_FOUND' AND a.outcome IN ('INVALID','ACCEPT_ALL','UNKNOWN')))
 ) THEN RAISE EXCEPTION 'missing governed verification'; END IF;
 IF NEW.outcome='SUPPORTED_CONTACT_ADDRESS' THEN
  SELECT * INTO source FROM record_org_recipient_sources WHERE id=NEW.recipient_source_id;
  IF source.id IS NULL OR source.experiment_id<>NEW.experiment_id OR source.candidate_id<>NEW.candidate_id
     OR source.organization_id<>NEW.organization_id OR source.recipient_id<>NEW.recipient_id
     OR source.source_fact_id<>NEW.source_fact_id OR contact.outcome<>'SUPPORTED'
     OR contact.source_id<>NEW.source_fact_id OR contact.verification_id IS DISTINCT FROM NEW.verification_fact_id
  THEN RAISE EXCEPTION 'invalid supported contactability'; END IF;
ELSEIF contact.outcome NOT IN ('EMAIL_NOT_FOUND','VERIFICATION_REJECTED') THEN
  RAISE EXCEPTION 'invalid no-email contactability';
 ELSE
  SELECT * INTO binding FROM record_org_bindings WHERE experiment_id=NEW.experiment_id AND identity_id=candidate.identity_id;
  IF binding.id IS NULL OR binding.organization_id<>NEW.organization_id THEN RAISE EXCEPTION 'missing no-email organization'; END IF;
 END IF;
 RETURN NEW;
END $$;
"""
