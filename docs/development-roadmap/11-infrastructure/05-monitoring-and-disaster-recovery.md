# Monitoring, On-Call, and Disaster Recovery

**Document ID:** INFRA-05
**Status:** Planned M8 operations gate; current foundation has safe logs and health endpoints but no telemetry backend, alert routes, on-call channels, production backups, incident tooling, or DR exercise
**Milestone:** M8 private operations and recurring readiness; M9 safety prerequisite
**Owner:** Solo operator wearing incident roles sequentially; provider/counsel specialists join only when incident facts require them
**Prerequisites:** OBS-01..05 exact registries/runbooks, TEST-01..06, INFRA-02..04, SEC-01..06, and a promoted private release
**Outputs:** Telemetry topology, exact alert/incident routing, independent paging, service/capacity dashboards, RPO/RTO catalog, DR scenarios/runbooks/drills, evidence freshness and re-enable rules
**Unlocks:** M8 private-operations acceptance and bounded M9 readiness review
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

One operator is alerted through channels independent of Alon AI Gmail, can determine authoritative state, contain harm, restore a clean host/database/secrets/config, measure data loss and recovery time, and resume only by a separate gated command. Dashboards aid diagnosis but never replace PostgreSQL/provider/backup evidence.

## Current repository state

The API has liveness/readiness and sanitized structured logs; the worker emits `worker_ready`. The complete OBS-01 event schema, OBS-02 39-instrument/4,656-series registry and alerts, cost/evaluation telemetry, incident tables/catalog/IR-01..13, notification adapters, external heartbeats, backup metrics, recovery commands and drills remain planned. No on-call or disaster-recovery claim is currently supported.

## Scope and non-goals

In scope: local OpenTelemetry collector, managed encrypted logs/metrics/traces, DB-authoritative dashboards, telemetry self-health, exact OBS alert registry, incident tuple routing, primary/secondary external page channels, offline contacts, capacity/disk/cert/backup/release/provider/Gmail/security alerts, DR objectives/scenarios, clean rebuild/restore, exercises and evidence freshness. Non-goals: 24x7 staffed-SOC claim, Gmail as page channel, auto-remediation/auto-enable, high-cardinality identifiers, logs as product truth, undefined catch-all alerts, or hiding an outage because the monitoring vendor is down.

## Exact planned implementation surfaces

Create `infra/observability/otel-collector.yaml`, managed sink dashboards, `alert-routes.v1.json`, `heartbeat-jobs.v1.json`, `dr-objectives.v1.json`, local read-only diagnostic commands, offline encrypted contact sheet, and `scripts/dr/{preflight,rebuild,verify}.sh`. `alert-routes.v1.json` must equal OBS-02/OBS-05 alert IDs and exact `incident.catalog.v1` trigger/alert/runbook tuples; unknown/missing/cross-paired values fail deployment.

The host collector receives OTLP only on the internal network, applies OBS-01 allowlist/redaction/cardinality processors, buffers boundedly on encrypted local disk, exports over authenticated TLS to Google Cloud Monitoring, Logging and Trace, and emits its own drop/lag/queue/disk/clock health. Application metrics match the exact OBS-02 names/units/labels/buckets; Cloud Monitoring dashboards query authoritative read-only DB projections for controls, unresolved Gmail/cost/incidents and compare them to telemetry counts. No telemetry sink has an inbound control webhook.

Primary paging is PagerDuty mobile push/SMS/phone invoked by Cloud Monitoring alert policies. Secondary paging is Healthchecks.io heartbeat expiry invoked directly by host systemd timers, bypassing the application and OpenTelemetry collector. Neither uses Alon AI Gmail credentials or the same telemetry export path. Provider account recovery, Israeli phone delivery, data region/terms and monthly cost are reviewed and signed at M8; the interface is not satisfied until both pass loss-of-primary/collector/Internet-path tests. Offline contacts include Google Cloud, Tailscale, Cloudflare, GitHub/GHCR, Gmail, PagerDuty, Healthchecks.io and Israeli/recipient-jurisdiction counsel.

| Data/service | Initial objective | Proof and safety behavior |
| --- | --- | --- |
| PostgreSQL product + security runtime | RPO <=5m; full private service RTO <=4h | exact WAL target and clean-host drill; sessions revoked, controls/public off |
| secret objects/KMS references | RPO <=24h for encrypted backup; recovery/reauthorization RTO <=8h | version/state/linkage restore or revoke+fresh authorization; no token patch |
| signed release/config/migration/agent manifests | RPO 0 from immutable registry/Git/offline copy; RTO <=2h | signature/hash and prior-digest deployment |
| private DNS/TLS/overlay/proxy | RPO 0 config; RTO <=2h | clean host configuration plus external/private scans |
| public unsubscribe edge | RPO 0 config; RTO <=8h; safe downtime preferred | remove DNS/profile while unavailable; product outreach false if suppression cannot be observed |
| telemetry/paging | operational RPO <=1h; primary visibility RTO <=2h | local DB queries plus independent secondary page; both controls false after >5m send-safety blindness |

Objectives are planned maximums that drills must measure; a miss is a failed gate, not a revised timestamp after the fact.

DR scenarios are exact: total VPS loss; PostgreSQL corruption/unsafe migration; base/WAL gap; object-store or KMS/recovery-key loss; compromised release/supply chain; private overlay/operator device loss; DNS/TLS/proxy/WAF takeover; secret/Gmail/OIDC compromise; telemetry/primary-page blindness; region/provider outage; and accidental retention/purge. Each scenario maps to IR-03/05/07/08/09/11/13 as applicable, begins with the canonical first containment, resolves exact target/backup/release identities, and uses INFRA-04 isolated restore or clean host rebuild.

Clean rebuild order: open signed offline journal if DB is down; disable public DNS/edge and provider egress; provision/attest new private host; install firewall/overlay/runtime; verify release/config/KMS identities; restore PostgreSQL isolated; replay tombstones/revoke sessions/controls; verify 46 tables/runtime/Gmail/cost/incidents; start API/private UI without worker; restore telemetry/pages; start compatible worker with dequeues/provider calls disabled; run tests/soak; record resolution. Any control/public enable is a later separate command.

## Ordered implementation tasks

- [ ] **Implement telemetry and authoritative comparisons —** Input: exact OBS-01/02 registries and product queries. Operation: instrument collector/export/dashboards and reconcile metrics to DB/event/provider counts. Output: safe actionable visibility. Test evidence: label/cardinality/canary/drop/restart/count mismatch cases. Failure behavior: reject config; controls false when safety visibility is unavailable.
- [ ] **Implement exact alert/incident routing —** Input: OBS-02 alerts and OBS-05 tuples/objectives. Operation: compile routes to incident command/runbook/page with closed values and applicability. Output: deterministic pages/incidents. Test evidence: every positive tuple, cross-pair/unknown and resolution applicability. Failure behavior: alert deployment/release blocked.
- [ ] **Establish two independent on-call paths —** Input: signed provider/contact selection and synthetic Critical alert. Operation: send primary and secondary pages, acknowledge/escalate and exercise loss of each provider/collector/network path. Output: reachable operator and offline fallback. Test evidence: delivery/ack timestamps and no Gmail dependency. Failure behavior: M8 blocked and local control fallback documented.
- [ ] **Execute every DR scenario —** Input: clean candidate host, signed releases/backups/keys and exact scenario. Operation: contain, rebuild/restore/reconcile/verify and measure RPO/RTO using no SQL/provider send. Output: signed scenario report. Test evidence: VPS/DB/WAL/KMS/release/overlay/DNS/telemetry/retention cases. Failure behavior: open incident, controls/public off and objective failed.
- [ ] **Operate freshness and re-enable gates —** Input: daily backup/telemetry checks, monthly alert test, quarterly IR rotation/contact/channel test and <=90-day clean restore. Operation: expire stale evidence, create maintenance incident and require separate expected-version enable. Output: ongoing readiness. Test evidence: stale/missing/larger-authority/automatic-enable denials. Failure behavior: release/authority remains at or below last proven bound.

## Test strategy

- **Registry `test_observability_instruments_alerts_incident_tuples_and_runbooks_equal_canonical_sets`.**
- **Privacy `test_telemetry_and_page_payloads_contain_only_allowlisted_bounded_non_pii_fields`.**
- **Blindness `test_collector_sink_primary_page_and_clock_failures_trigger_secondary_and_local_fallback`.**
- **DR `test_clean_host_restore_meets_each_rpo_rto_or_records_a_failed_objective`.**
- **Safety `test_rebuild_restore_and_resolved_incident_leave_sessions_revoked_controls_and_public_ingress_off`.**
- **Provider `test_dr_reconciliation_calls_no_gmail_send_model_search_or_enrichment_provider`.**
- **Freshness `test_stale_restore_alert_contact_policy_or_security_evidence_blocks_release_and_enable`.**

## Security, privacy, compliance, idempotency, observability, and cost

Collector/sinks/pages use scoped credentials, TLS, encryption, bounded retention and no inbound authority. Incident/page payloads expose only catalog values/safe refs. Repeated alerts/incidents dedupe by canonical key without losing occurrences. External monitor/legal/support/restore costs are budgeted and recorded. Counsel decides notification and communications; the system records references without privileged content. Exercise data is synthetic/minimized.

## Failure, rollback, and operator recovery

On missing/contradictory telemetry, page failure, breached objective, corrupt restore, provider/KMS uncertainty, route/config mismatch or unknown incident tuple: choose containment and unknown, disable both controls/public edge as applicable, use local read-only queries/offline journal, preserve evidence and execute the mapped IR runbook. Roll back collector/dashboard/alert/release configs by signed digest. Never resolve because a dashboard returned green, rewrite history, send a test to a real recipient, or auto-enable after recovery.

## Acceptance and retained evidence

- [ ] Exact telemetry/alert/incident registries are deployed with bounded privacy-safe labels and DB comparisons.
- [ ] Two independent non-Gmail page paths and offline contacts reach the solo operator under failure.
- [ ] Every DR scenario has an executable clean rebuild/restore with measured RPO/RTO and no provider send.
- [ ] Ongoing evidence freshness and separate re-enable prevent stale drills from granting authority.

Retain collector/dashboard/alert/heartbeat configs and hashes, safe sample payloads, registry set-equality output, page/contact test receipts, local/managed outage traces, signed DR timelines/RPO/RTO/restore reports, incidents/postmortems, cost records and re-enable denials.

## Dependencies and next deliverable

INFRA-05 closes the Task 7 testing/infrastructure plan. Passing TEST-01..06 and INFRA-01..05 completes only the M8 private-operations evidence gate. A real-recipient M9 experiment still requires current M1/M6, legal/policy/recipient/campaign/budget authority and the separately disabled/public-route activation evidence.
