"""Global identity indexes reference governed content instead of copying it."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)

from alon_ai.accounting import schema as g


def table(name, *parts):
    return Table("record_org_" + name, g.metadata, *parts)


def fk(column, target):
    return ForeignKeyConstraint([column], [target])


policy = table(
    "policy",
    g.col("id", Integer, primary_key=True),
    g.col("key_fingerprint", String(64), nullable=True),
    g.col("owns_pgcrypto", Boolean),
    CheckConstraint("id=1 AND key_fingerprint ~ '^[0-9a-f]{64}$'"),
)
organizations = table(
    "organizations", g.col("id", g.U, primary_key=True), g.col("created_at", g.T)
)
evidence = table(
    "evidence",
    g.col("id", g.U, primary_key=True),
    g.col("organization_id", g.U),
    g.col("experiment_id", g.U),
    g.col("operation_id", g.U),
    g.col("call_id", g.U),
    g.col("grant_id", g.U),
    g.col("grant_version", Integer),
    g.col("retained_id", g.U),
    g.col("value_index", Integer),
    g.col("snapshot_hash", String(64)),
    g.col("expires_at", g.T),
    g.col("observed_at", g.T),
    fk("organization_id", "record_org_organizations.id"),
    fk("experiment_id", "record_experiments.id"),
    fk("operation_id", "gov_operations.id"),
    fk("call_id", "gov_calls.id"),
    ForeignKeyConstraint(
        ["grant_id", "grant_version"], ["gov_grants.id", "gov_grants.version"]
    ),
    UniqueConstraint("id", "organization_id"),
    CheckConstraint(
        "value_index>=0 AND value_index<=999 AND snapshot_hash ~ '^[0-9a-f]{64}$'"
    ),
)
keys = table(
    "keys",
    g.col("id", g.U, primary_key=True),
    g.col("organization_id", g.U),
    g.col("evidence_id", g.U),
    g.col("kind", String(32)),
    g.col("namespace", String(100)),
    g.col("lookup_hash", String(64)),
    g.col("source_index", Integer),
    ForeignKeyConstraint(
        ["evidence_id", "organization_id"],
        ["record_org_evidence.id", "record_org_evidence.organization_id"],
    ),
    g.enumcheck(
        "kind",
        [
            "REGISTERED_ID",
            "PROVIDER_ID",
            "OFFICIAL_URL",
            "NAME",
            "DOMAIN",
            "URL",
            "FORMER_NAME",
        ],
    ),
    CheckConstraint("lookup_hash ~ '^[0-9a-f]{64}$'"),
    UniqueConstraint("evidence_id", "kind", "namespace", "lookup_hash"),
)
Index("ix_record_org_key_lookup", keys.c.kind, keys.c.namespace, keys.c.lookup_hash)
Index(
    "uq_record_org_registered",
    keys.c.kind,
    keys.c.namespace,
    keys.c.lookup_hash,
    unique=True,
    postgresql_where=keys.c.kind == "REGISTERED_ID",
)
locations = table(
    "locations",
    g.col("id", g.U, primary_key=True),
    g.col("organization_id", g.U),
    g.col("evidence_id", g.U),
    g.col("source_index", Integer),
    ForeignKeyConstraint(
        ["evidence_id", "organization_id"],
        ["record_org_evidence.id", "record_org_evidence.organization_id"],
    ),
    UniqueConstraint("evidence_id", "source_index"),
    CheckConstraint("source_index>=0 AND source_index<100"),
)
bindings = table(
    "bindings",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("organization_id", g.U),
    g.col("identity_id", g.U),
    g.col("evidence_id", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["identity_id", "experiment_id"],
        ["supply_identities.id", "supply_identities.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["evidence_id", "organization_id"],
        ["record_org_evidence.id", "record_org_evidence.organization_id"],
    ),
    UniqueConstraint("identity_id"),
    UniqueConstraint("id", "experiment_id", "organization_id"),
)
recipients = table(
    "recipients",
    g.col("id", g.U, primary_key=True),
    g.col("lookup_hash", String(64), unique=True),
    g.col("created_at", g.T),
    CheckConstraint("lookup_hash ~ '^[0-9a-f]{64}$'"),
)
recipient_sources = table(
    "recipient_sources",
    g.col("id", g.U, primary_key=True),
    g.col("recipient_id", g.U),
    g.col("organization_id", g.U),
    g.col("experiment_id", g.U),
    g.col("binding_id", g.U),
    g.col("candidate_id", g.U),
    g.col("source_fact_id", g.U),
    g.col("retained_id", g.U),
    g.col("value_index", Integer),
    g.col("created_at", g.T),
    fk("recipient_id", "record_org_recipients.id"),
    ForeignKeyConstraint(
        ["binding_id", "experiment_id", "organization_id"],
        [
            "record_org_bindings.id",
            "record_org_bindings.experiment_id",
            "record_org_bindings.organization_id",
        ],
    ),
    ForeignKeyConstraint(
        ["candidate_id", "experiment_id"],
        ["supply_candidates.id", "supply_candidates.experiment_id"],
    ),
    ForeignKeyConstraint(
        ["source_fact_id", "experiment_id"],
        ["supply_facts.id", "supply_facts.experiment_id"],
    ),
    UniqueConstraint("id", "experiment_id", "organization_id", "recipient_id"),
    CheckConstraint("value_index>=0 AND value_index<=999"),
)
admissions = table(
    "admissions",
    g.col("id", g.U, primary_key=True),
    g.col("binding_id", g.U),
    g.col("experiment_id", g.U),
    g.col("organization_id", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["binding_id", "experiment_id", "organization_id"],
        [
            "record_org_bindings.id",
            "record_org_bindings.experiment_id",
            "record_org_bindings.organization_id",
        ],
    ),
    UniqueConstraint("experiment_id", "organization_id"),
)
reservations = table(
    "reservations",
    g.col("id", g.U, primary_key=True),
    g.col("organization_id", g.U),
    g.col("recipient_id", g.U),
    g.col("experiment_id", g.U),
    g.col("source_id", g.U),
    g.col("created_at", g.T),
    ForeignKeyConstraint(
        ["source_id", "experiment_id", "organization_id", "recipient_id"],
        [
            "record_org_recipient_sources.id",
            "record_org_recipient_sources.experiment_id",
            "record_org_recipient_sources.organization_id",
            "record_org_recipient_sources.recipient_id",
        ],
    ),
    UniqueConstraint("id", "experiment_id", "organization_id", "recipient_id"),
)
releases = table(
    "releases",
    g.col("id", g.U, primary_key=True),
    g.col("reservation_id", g.U, unique=True),
    g.col("evidence_id", g.U, nullable=True),
    g.col("released_by", g.U),
    g.col("created_at", g.T),
    fk("reservation_id", "record_org_reservations.id"),
    fk("evidence_id", "gov_evidence.id"),
)
effects = table(
    "effects",
    g.col("id", g.U, primary_key=True),
    g.col("reservation_id", g.U, unique=True),
    g.col("experiment_id", g.U),
    g.col("call_id", g.U, unique=True),
    g.col("operation_id", g.U),
    g.col("mailbox_id", g.U),
    g.col("rfc_message_id", g.U, unique=True),
    g.col("recipient_lookup_hash", String(64)),
    g.col("created_at", g.T),
    fk("reservation_id", "record_org_reservations.id"),
    fk("experiment_id", "record_experiments.id"),
    fk("call_id", "gov_calls.id"),
    fk("operation_id", "gov_operations.id"),
    UniqueConstraint(
        "id",
        "call_id",
        "operation_id",
        "experiment_id",
        "reservation_id",
        "recipient_lookup_hash",
        "mailbox_id",
        "rfc_message_id",
    ),
)
observations = table(
    "observations",
    g.col("id", g.U, primary_key=True),
    g.col("effect_id", g.U),
    g.col("call_id", g.U),
    g.col("operation_id", g.U),
    g.col("experiment_id", g.U),
    g.col("reservation_id", g.U),
    g.col("recipient_lookup_hash", String(64)),
    g.col("mailbox_id", g.U),
    g.col("rfc_message_id", g.U),
    g.col("outcome", String(16)),
    g.col("result_evidence_id", g.U, nullable=True),
    g.col("provider_request_id", String(100), nullable=True),
    g.col("provider_message_id", String(100), nullable=True),
    g.col("reconciles_id", g.U, nullable=True),
    g.col("observed_at", g.T),
    ForeignKeyConstraint(
        [
            "effect_id",
            "call_id",
            "operation_id",
            "experiment_id",
            "reservation_id",
            "recipient_lookup_hash",
            "mailbox_id",
            "rfc_message_id",
        ],
        [
            "record_org_effects.id",
            "record_org_effects.call_id",
            "record_org_effects.operation_id",
            "record_org_effects.experiment_id",
            "record_org_effects.reservation_id",
            "record_org_effects.recipient_lookup_hash",
            "record_org_effects.mailbox_id",
            "record_org_effects.rfc_message_id",
        ],
    ),
    fk("result_evidence_id", "gov_evidence.id"),
    fk("reconciles_id", "record_org_observations.id"),
    UniqueConstraint("effect_id", "outcome"),
    g.enumcheck("outcome", ["CONFIRMED", "AMBIGUOUS", "NO_EFFECT"]),
    CheckConstraint(
        "(outcome='CONFIRMED' AND result_evidence_id IS NOT NULL AND provider_request_id IS NOT NULL AND provider_message_id IS NOT NULL) OR (outcome='AMBIGUOUS' AND result_evidence_id IS NULL AND provider_request_id IS NULL AND provider_message_id IS NULL) OR (outcome='NO_EFFECT' AND result_evidence_id IS NOT NULL AND provider_request_id IS NULL AND provider_message_id IS NULL)"
    ),
)
suppressions = table(
    "suppressions",
    g.col("id", g.U, primary_key=True),
    g.col("organization_id", g.U, nullable=True),
    g.col("recipient_id", g.U, nullable=True),
    g.col("global_scope", Boolean),
    g.col("reason_code", String(64)),
    g.col("acted_by", g.U),
    g.col("created_at", g.T),
    fk("organization_id", "record_org_organizations.id"),
    fk("recipient_id", "record_org_recipients.id"),
    CheckConstraint(
        "(global_scope AND organization_id IS NULL AND recipient_id IS NULL) OR (NOT global_scope AND (organization_id IS NULL)<>(recipient_id IS NULL))"
    ),
    CheckConstraint("reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"),
)
merges = table(
    "merges",
    g.col("id", g.U, primary_key=True),
    g.col("losing_id", g.U, unique=True),
    g.col("surviving_id", g.U),
    g.col("evidence_id", g.U),
    g.col("acted_by", g.U),
    g.col("reason_code", String(64)),
    g.col("created_at", g.T),
    fk("losing_id", "record_org_organizations.id"),
    fk("surviving_id", "record_org_organizations.id"),
    fk("evidence_id", "record_org_evidence.id"),
    CheckConstraint(
        "losing_id<>surviving_id AND reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"
    ),
)
exclusions = table(
    "exclusions",
    g.col("id", g.U, primary_key=True),
    g.col("experiment_id", g.U),
    g.col("organization_id", g.U),
    g.col("reason", String(32)),
    g.col("created_at", g.T),
    fk("experiment_id", "record_experiments.id"),
    fk("organization_id", "record_org_organizations.id"),
    g.enumcheck(
        "reason",
        [
            "CONTACTED",
            "CONTACT_AMBIGUOUS",
            "RESERVED_ELSEWHERE",
            "SUPPRESSED",
            "IDENTITY_MERGED",
            "IDENTITY_CONFLICT",
            "SOURCE_UNAVAILABLE",
        ],
    ),
)
conflicts = table(
    "conflicts",
    g.col("id", g.U, primary_key=True),
    g.col("organization_id", g.U),
    g.col("matched_id", g.U),
    g.col("evidence_id", g.U),
    g.col("created_at", g.T),
    fk("organization_id", "record_org_organizations.id"),
    fk("matched_id", "record_org_organizations.id"),
    fk("evidence_id", "record_org_evidence.id"),
    CheckConstraint("organization_id<>matched_id"),
    UniqueConstraint("organization_id", "matched_id", "evidence_id"),
)
identity_decisions = table(
    "identity_decisions",
    g.col("id", g.U, primary_key=True),
    g.col("conflict_id", g.U, unique=True),
    g.col("evidence_id", g.U),
    g.col("resolution", String(32)),
    g.col("acted_by", g.U),
    g.col("reason_code", String(64)),
    g.col("created_at", g.T),
    fk("conflict_id", "record_org_conflicts.id"),
    fk("evidence_id", "record_org_evidence.id"),
    g.enumcheck("resolution", ["SAME_ORGANIZATION", "INDEPENDENT_BUSINESS"]),
    CheckConstraint("reason_code ~ '^[A-Z][A-Z0-9_]{0,63}$'"),
)
TABLES = (
    policy,
    organizations,
    evidence,
    keys,
    locations,
    bindings,
    recipients,
    recipient_sources,
    admissions,
    reservations,
    releases,
    effects,
    observations,
    suppressions,
    merges,
    exclusions,
    conflicts,
    identity_decisions,
)
for tab in TABLES:
    for i, constraint in enumerate(
        sorted(
            tab.foreign_key_constraints,
            key=lambda item: tuple(e.parent.name for e in item.elements),
        )
    ):
        Index(
            f"ix_{tab.name}_fk_{i}",
            *[tab.c[e.parent.name] for e in constraint.elements],
        )
