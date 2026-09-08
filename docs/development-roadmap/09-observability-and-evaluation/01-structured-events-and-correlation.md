# Structured Operational Events and End-to-End Correlation

**Document ID:** OBS-01
**Status:** Planned M6-M8 telemetry contract; current foundation has sanitized structured request/worker logs and request IDs, but no product event schema, distributed tracing, durable correlation, exporter, or dashboards
**Milestone:** M3, M6, M7, M8, M9 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `OBS-01-T01 -> OBS-01-T02 -> OBS-01-T03 -> OBS-01-T04 -> OBS-01-T05 -> OBS-01-T06 -> OBS-01-T07`; cross-document task Inputs `OBS-01-T01 <- SEC-06-T01; OBS-01-T02 <- PROVIDER-01-T04,PROVIDER-02-T01,OBS-03-T02; OBS-01-T04 <- SEC-02-T04,BACKEND-02-T05; OBS-01-T07 <- LAUNCH-03-T02,SEC-04-T04`. Descriptive source authorities/resources (not whole-document completion dependencies): [ARCH-03 EventEnvelope](../01-architecture/03-domain-events-and-state-machines.md), [DB-05](../02-database/05-audit-events-and-idempotency.md), workflow/agent/provider/Gmail contracts, BACKEND-01/02/04, SEC-01/03/06, and [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)
**Outputs:** Exact operational-event schema, correlation/causation propagation, redaction/allowlists, durable-resume trace links, sink integrity, and tests
**Unlocks:** OBS-02 metrics/traces/alerts, OBS-03 cost correlation, OBS-04 runtime evaluation, and OBS-05 incidents
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Starting from one browser request or workflow schedule, Alon can follow safe identities through HTTP, canonical command, domain/audit event, DBOS/Temporal run and step, agent run, one of six provider calls, cost entry, Gmail intent/attempt/result/observation/reply, and incident/repair without copying a secret, recipient, message, prompt, evidence, or provider payload into telemetry. Correlation aids diagnosis; PostgreSQL/event/provider records remain authority.

The design follows OpenTelemetry [semantic conventions 1.44.0](https://opentelemetry.io/docs/specs/semconv/) and [stable Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/), accessed 2026-08-29. Alon AI custom fields are versioned and use OTel standard attributes when meanings match. This is no claim of OpenTelemetry certification.

## Current repository state

`structlog` emits sanitized JSON in production; request middleware accepts or generates a request ID, removes the query string, returns it in a response header, and tests exclude secrets/exception detail. Worker startup logs safe state. There is no UUIDv4 `correlation_id`, `causation_id`, trace/span context, OTel SDK/collector/exporter, structured product/provider/security log contract, sink access/retention, sampling, telemetry health, or log-to-record linkage. Domain events and all product records are still planned.

## Scope and non-goals

In scope: logs/operational events, trace context, metric exemplars, safe resource attributes, HTTP/command/workflow/agent/provider/Gmail/cost/security/recovery correlation, durable resume/replay links, redaction, sink auth/availability, sampling and retained evidence.

Non-goals: logs as product truth, full event sourcing, putting raw identifiers into metric labels, storing request/response/prompt/body/token data, distributed tracing as an exactly-once mechanism, logging every SQL statement/parameter, provider-native unbounded error text, or renaming canonical domain events.

## Exact planned implementation surfaces

Create `observability/schema.py`, `observability/context.py`, `observability/logging.py`, `observability/tracing.py`, `observability/redaction.py`, `observability/export.py`, FastAPI/worker/runtime/provider instrumentation, and `tests/observability/`. Extend current logging rather than creating a parallel logger. Use W3C `traceparent`/`tracestate` only across trusted internal boundaries; no external website receives internal baggage or credentials.

### Exact `OperationalEventV1` schema

Every application-originated log/event is strict, extra-forbid, and serialized as one JSON object:

```text
schema_version = "telemetry.operational_event.v1"
event_id: UUIDv4
timestamp: UTC RFC3339 nanosecond-capable string
observed_timestamp: UTC RFC3339 string
event_name: registered enum
severity_text: TRACE|DEBUG|INFO|WARN|ERROR|FATAL
severity_number: exact base OpenTelemetry severity number TRACE=1, DEBUG=5, INFO=9, WARN=13, ERROR=17, FATAL=21
body: registered safe message template ID, never interpolated payload
resource: {service.name,service.version,deployment.environment,process.role,service.instance.id_hash}
trace: {trace_id?,span_id?,trace_flags?}
context: {request_id?,correlation_id?,causation_id?,idempotency_key_hash?}
operation: {operation_kind,operation_name,outcome,error_code?,reason_codes?,duration_ms?}
references: allowlisted UUID/version/hash references below
attributes: registered bounded scalar attributes below
exception: {type_enum?,fingerprint?}
```

Required always: schema/event ID/timestamps/name/severity/body/resource/operation outcome. Timestamps are UTC with `Z`, RFC 3339 syntax and at most nine fractional digits; offsets and naive time are invalid. IDs are lowercase fixed-length hex or UUIDv4 according to their upstream contract; trace ID is 32 lowercase hex characters, span ID is 16, and all-zero values are invalid. `reason_codes` are sorted, unique, and registry-bounded (maximum 20). `duration_ms` is a non-negative integer. Serialized UTF-8 is at most 16,384 bytes, attribute count at most 64, each string at most 200 Unicode code points, and each array at most 20 items. Unknown/oversized field, name, reason or attribute is rejected at the producer boundary in test and dropped with a safe telemetry-schema counter in production; it is never stringified wholesale.

Registered `event_name` values are operational facts, not ARCH-03 domain events: `http.server.completed`, `command.completed`, `domain.event.recorded`, `workflow.run.observed`, `workflow.step.completed`, `agent.run.completed`, `provider.call.completed`, `gmail.send.boundary`, `gmail.history.page.completed`, `security.authentication.completed`, `security.authorization.denied`, `security.secret.operation`, `control.operation.completed`, `retention.operation.completed`, `evaluation.operation.completed`, `backup.operation.completed`, `incident.operation.completed`, and `telemetry.pipeline.health`. When mirroring a canonical business event, use `event_name="domain.event.recorded"` only with `references.domain_event_id` and `attributes.domain_event_type` containing the exact ARCH-03 `.v1` name; do not create `evaluation.*`, `agent.promoted.*`, OAuth, or other fake domain-event aliases.

### Exact safe reference and attribute allowlists

References may contain only applicable internal IDs: `operator_id`, `experiment_id`, `workflow_run_id`, `command_id`, `domain_event_id`, `audit_event_id`, `campaign_id` plus numeric `campaign_version`, `campaign_member_id`, `lead_id`, `message_id`, `approval_id`, `send_intent_id`, `send_rate_reservation_id`, `send_attempt_id`, `provider_result_id`, `provider_observation_id`, `reply_id`, `agent_run_id`, `artifact_id`, `evaluation_case_id`, `evaluation_result_id`, `policy_decision_id`, `budget_account_id`, `budget_reservation_id`, `cost_entry_id`, `incident_id`, `repair_action_id`, `mailbox_id`, and OAuth/session/secret object UUIDs only in their restricted security events. These IDs are log fields for point diagnosis, never metric labels. The durable `recipient_target_ref_id` is allowlisted only in the canonical `suppression.created.v1` event and operator suppression HTTP projection, not `OperationalEventV1`, log/trace/metric attributes or exports. Recipient/address/content/scope/facts hashes are not telemetry references.

Bounded attributes are: route template, HTTP method/status class; command type/scope class and replay boolean; workflow type/version/step/state/replay boolean/runtime; agent type/version/config/suite version and terminal state; provider name/capability/fixture mode/outcome/safe error enum; Gmail boundary enum/attempt number/state/retry class/reconciliation outcome; policy scope/version/allowed and safe reason enum; control name/value/version; suppression scope/source and denial boolean; incident catalog version/severity/state/trigger code/runbook ID/alert ID/resolution code/repair kind from `incident.catalog.v1`; retention class/action; evaluation suite/agent type/repetition/pass; currency ISO code and integer amount only in log body fields; deployment/release/schema/key generations; and telemetry signal/export outcome/drop reason. Provider/model names and versions are allowlisted registry values, not caller text. Unknown incident or repair catalog values reject at the producer and DB boundaries; incident/recipient/session/record IDs remain references only and never metric labels.

### Absolute secret/PII denylist and transformation rules

Never record: raw URL/query/fragment; request/response headers or bodies; cookies; Authorization/idempotency/state/nonce/PKCE/code/token/client/API/DB/KMS secrets or their prefixes; OIDC claims/email/IP/user-agent string; raw recipient address/name/domain or deterministic recipient SHA-256 hash; subject/body/reply/MIME/RFC Message-ID; evidence/source excerpt/capture; prompt/model input/output/hidden reasoning; provider request/result/error bodies; SQL/parameters; stack locals/environment/config; raw webhook/callback/unsubscribe token or query; legal/consent text; or unbounded exception messages. Recipient hashes are pseudonymous and offline enumerable, not anonymized telemetry-safe identifiers.

Route is the registered FastAPI template, never actual path; the public unsubscribe token path always collapses to `/api/v1/public/unsubscribe/{token}` and carries bounded `route.partition=PUBLIC_UNSUBSCRIBE`, never its token/query. `idempotency_key_hash` is an environment-specific HMAC digest only where replay diagnosis requires it and is forbidden for public token replay. IP may become an ephemeral in-memory prefix rate bucket, not telemetry. Public WAF/rate/CSRF outcomes use only registered outcome/reason/route-partition fields; no token/JTI/IP/referrer/user-agent reaches a sink. Exceptions map to a registered `type_enum` plus SHA-256 fingerprint over sanitized exception class/top application frames/release, with no message/locals; full sensitive forensic detail, if essential, is a separately encrypted incident artifact under SEC-06. Error `detail` from RFC 9457 is not copied.

Redaction is allowlist-first, then deny-pattern defense. Producers construct typed fields; the sink runs a second independent scrubber for credentials, email/phone patterns, cookies/JWTs, query strings and canaries. On a match, replace the entire offending field with `[REDACTED]`, increment a bounded counter, quarantine the batch in encrypted restricted storage only if incident evidence requires it, and open an incident for secret/PII classes. Never log the matched value or a reversible substring.

### Correlation and causation propagation

| Boundary | Exact propagation |
| --- | --- |
| browser -> HTTP | optional caller `X-Request-ID` must be UUIDv4 per BACKEND-02; server returns it and creates/continues trace; a new UUIDv4 `correlation_id` starts unless an authenticated internal command continuation supplies its persisted value |
| HTTP -> command | `causation_id=request_id`; actor comes from SEC-02 server session; command stores correlation/causation; idempotent replay returns stored correlation/result and emits replay telemetry only |
| command -> domain/audit/outbox | exact ARCH-03 envelope copies correlation; causation is command ID/request ID as frozen; internal consumer uses source event/outbox ID as causation |
| command -> workflow | `workflow_runs.correlation_id` persists the chain; run start event causes first step; workflow input/result snapshot hashes verify before use |
| durable step/resume | create a new trace/span execution and add an OTel span link to the persisted prior trace/span if retained; correlation stays constant; `workflow_replay=true`; never assume trace parent continuity across crash |
| workflow -> agent | agent execution envelope carries correlation, causation event/step, `workflow_run_id`, deadline/budgets; `AgentRunRecordingService` owns run row |
| agent -> six capabilities | `ProviderCallContextV1` carries canonical run/call/idempotency/correlation fields; provider adapter returns exact call ID/meta/ledger; no external untrusted trace context becomes parent |
| send chain -> Gmail | eligibility/approval/intent/queue/final `SEND`/rate/attempt/provider result/observation/reply retain one correlation with direct causation IDs; Gmail raw headers are not trace transport |
| cost/evaluation/incident/repair | DB record references exact agent/workflow/attempt and correlation where schema provides it; telemetry links them without inventing DB FKs/events |

`trace_id`/`span_id` are diagnostics, not canonical causation. DBOS/Temporal replay must not double-insert business metrics/cost/events; instrumentation executes outside replay-sensitive business decisions or marks replay and relies on metric idempotency at the authoritative record consumer. Sampling never drops Critical security/control/send/ambiguity/incident/backup/evaluation-promotion events; ordinary success traces may be head/tail sampled under a versioned policy while logs/metrics preserve counts.

### Sink security, integrity, retention, and self-observation

API/worker export over authenticated TLS to a private collector with per-service identity, bounded queue/batch/retry/disk buffer, no inbound control plane, and an allowlisted destination. Collector adds ingestion time and immutable batch checksum/signature, restricts one operator's read access, records access audit, and follows SEC-06 30-day logs/7-day traces/13-month bounded metrics unless a reviewed policy changes. Telemetry is not sent to model providers.

Export failure cannot block a safe disable or authoritative transaction. It increments local counters, writes a minimal local rotating safe record, alerts through an independent channel, and after five minutes of blindness forces both send controls false where send-safety visibility is required. On recovery compare DB authoritative counts/events/attempts/cost with sink counts; never backfill raw payload.

## Ordered implementation tasks

<!-- roadmap-task id=OBS-01-T01 milestone=M3 depends_on=SEC-06-T01 mode=parallel locks=telemetry-catalog -->
- [ ] **Implement schema/registry/redaction —** Input: exact allowlist/denylist and current foundation logs. Operation: type every producer, centralize safe enums/templates, add independent sink scrubber and canaries. Output: valid `OperationalEventV1`. Test evidence: property/fuzz/leak/schema tests. Failure behavior: drop/quarantine offending event safely and alert.
<!-- roadmap-task id=OBS-01-T02 milestone=M6 depends_on=OBS-01-T01,PROVIDER-01-T04,PROVIDER-02-T01,OBS-03-T02 mode=parallel locks=telemetry-catalog -->
- [ ] **Propagate correlation/causation —** Input: implemented M6 command/event/outbox/workflow/agent/provider/Gmail/cost/evaluation paths and signed fake private/public HTTP metadata fixtures. Operation: propagate canonical correlation across implemented M6 paths and prove fake HTTP metadata boundaries; real private reporting/session and active public ingress integrations remain separate later tasks. Output: correlated M6 implementation paths and validated fake HTTP instrumentation contract; no later live-path completion claim. Test evidence: happy/crash/replay/async/callback/public-unsubscribe E2E. Failure behavior: business action remains authoritative; missing safety correlation opens telemetry incident and blocks release.
<!-- roadmap-task id=OBS-01-T03 milestone=M6 depends_on=OBS-01-T02 mode=parallel locks=telemetry-catalog -->
- [ ] **Instrument exact boundaries —** Input: registered operations and owners, scoped to implemented M6 boundaries and signed future-path fixtures; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests. Operation: emit start only where useful and one terminal event/spans/metrics without duplicate replay; certify only the implemented M6 boundary set here; implement and verify this path with Gmail network denied here; later live acceptance must consume full pilot-entry authorization. Output: implemented bounded M6 telemetry instrumentation and its exact correlated boundary/alert evidence. Test evidence: expected event/span count at every Gmail kill point and provider failure. Failure behavior: no invented product success.
<!-- roadmap-task id=OBS-01-T04 milestone=M7 depends_on=OBS-01-T03,SEC-02-T04,BACKEND-02-T05 mode=serial locks=telemetry-catalog,security-runtime -->
- [ ] **Integrate authenticated private and report correlation —** Input: bounded M6 telemetry contract, SEC-02 authenticated session/request boundary and BACKEND-02 complete M7 private/report/incident generated API implementation. Operation: propagate canonical correlation through real private auth/session/report/incident paths and verify safe ID lineage, redaction and bounded fields against implemented handlers. Output: complete authenticated private/report/session correlation integration and safe trace evidence. Test evidence: session/command/query/report/incident traces, missing-ID rejection, no sensitive fields and fake-to-real boundary tests. Failure behavior: private integration gate remains blocked and affected telemetry is marked incomplete.
<!-- roadmap-task id=OBS-01-T05 milestone=M8 depends_on=OBS-01-T04 mode=serial locks=live-environment,telemetry-catalog -->
- [ ] **Deploy private sink/self-health —** Input: signed operator-attested collector/storage/access/bounded-retention configuration with exact endpoint, role, key-reference, checksum and capacity identities, plus the completed bounded private telemetry contract. Operation: authenticate, buffer, checksum, alert gaps, and reconcile against DB. Output: privacy-safe searchable telemetry. Test evidence: sink outage/full disk/tamper/clock/skew/access tests. Failure behavior: controls false after safety-blind threshold.
<!-- roadmap-task id=OBS-01-T06 milestone=M8 depends_on=OBS-01-T05 mode=serial locks=milestone-gate,telemetry-catalog -->
- [ ] **Prove absence and usability —** Input: synthetic plus canary scenarios; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: reconstruct one complete chain and scan every field/sink/backup/export; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: trace evidence with zero sensitive match. Test evidence: independent manual/query and automated scan. Failure behavior: telemetry release rejected.
<!-- roadmap-task id=OBS-01-T07 milestone=M9 depends_on=OBS-01-T06,LAUNCH-03-T02,SEC-04-T04 mode=serial locks=telemetry-catalog,live-environment -->
- [ ] **Integrate active public-edge correlation —** Input: bounded private telemetry contract, LAUNCH-03 activated two-operation capability and SEC-04 public-stop implementation. Operation: verify canonical safe correlation across scanner-safe GET and atomic POST/recipient-stop/incident paths under the active M9 ingress, including redaction and dependency failure. Output: complete active-public correlation/redaction evidence for the exact bounded GET/POST pair. Test evidence: GET write-zero, POST replay, token redaction, no private route exposure and fail-closed upstream/telemetry tests. Failure behavior: disable unsafe public mutation and product outreach; retain evidence.

## Test strategy

- **Schema `test_all_operational_events_are_strict_registered_and_size_bounded`.**
- **Correlation `test_http_command_event_workflow_agent_provider_gmail_cost_incident_chain_is_complete`.**
- **Replay `test_durable_resume_uses_span_link_and_does_not_double_count_or_emit_business_success`.**
- **Redaction `test_secret_pii_prompt_body_query_header_and_provider_canaries_never_reach_any_sink`.**
- **Cardinality `test_metric_attributes_exclude_all_record_ids_hashes_paths_text_and_unknown_values`.**
- **Outage `test_collector_failure_preserves_authoritative_commit_and_triggers_safety_blind_kill`.**
- **Domain `test_operational_names_never_alias_or_invent_arch03_domain_events`.**

## Security, privacy, compliance, idempotency, observability, and cost

Telemetry is sensitive operational data, encrypted/access-audited/retained under SEC-06. Event producers are idempotent around authoritative record identity; sink duplicates are tolerable and deduped by event ID where assigned, never used to decide business truth. Export/storage cost is budgeted and sampled without dropping Critical evidence. Privacy scans are release gates; pseudonymized high-cardinality identifiers remain personal-risk data and stay out of labels.

## Failure, rollback, and operator recovery

On schema/leak/correlation/sink-integrity failure, stop the exporter, quarantine only the minimum encrypted evidence, rotate exposed credentials, delete affected copies under SEC-06/counsel, and open an incident. Roll back instrumentation/collector config without rolling back business rows. Diagnose from PostgreSQL and provider evidence while telemetry is untrusted. Restore sink from clean configuration, replay only privacy-safe derived events if necessary, reconcile counts, then re-enable visibility-dependent controls manually.

## Acceptance and retained evidence

- [ ] Exact schema, names, allowlists/denylist, correlation/causation, durable links, sampling and sink contract are implemented.
- [ ] One chain spans HTTP through workflow/agent/provider/Gmail/cost/incident with canonical record references and no domain-event aliases.
- [ ] No secret/PII/content/prompt/provider payload or unbounded label reaches logs/traces/metrics/errors/exports.
- [ ] Telemetry gaps are detectable and never become product truth or hidden send authority.

Retain schema/registry versions, instrumentation map, sample sanitized chain, canary/redaction/cardinality results, event/span/metric count fixtures, exporter/sink access/retention config, outage/tamper/reconciliation drills, and release evidence.

## Dependencies and next deliverable

OBS-01 consumes every frozen Task 1-5 identity and feeds [OBS-02](02-metrics-tracing-and-alerting.md), [OBS-03](03-provider-cost-accounting.md), [OBS-04](04-agent-and-workflow-evaluations.md), and [OBS-05](05-incident-response.md). It unlocks observability only; it grants no workflow, provider, policy, or SEND authority.
