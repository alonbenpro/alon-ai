# Metrics, Tracing, SLOs, Dashboards, and Alerts

**Document ID:** OBS-02
**Status:** Planned M8 operations gate; liveness/readiness and structured foundation logs exist, but no OTel metrics/traces, SLOs, alert manager, dashboards, or notification path exists
**Milestone:** M6 safety metrics, M7 operator dashboards, M8 monitored private deployment
**Owner:** Solo operator
**Prerequisites:** OBS-01, DB-01/03/05, WF-01/05/06, AGENT-10, PROVIDER-01/02, BACKEND-04/06, SEC-01/02/05/06
**Outputs:** Exact low-cardinality metrics, span model, SLO/error budgets, dashboards, alert rules/routes, and telemetry-health gates
**Unlocks:** M8 monitored operation and OBS-05 incident detection
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Alon can answer five questions without querying raw personal data: is the private service usable; are workflows/agents/providers healthy and bounded; is any send/control/suppression/ambiguity invariant at risk; are costs complete and within budget; and can incidents/backups/recovery be trusted. Alerts are actionable for one operator, not a noisy imitation of a large SRE team.

The implementation follows OpenTelemetry [metric](https://opentelemetry.io/docs/specs/semconv/general/metrics/) and [trace](https://opentelemetry.io/docs/specs/semconv/general/trace/) semantics as applicable, accessed 2026-08-29. Custom metrics use an `alon_ai.` namespace and documented units/labels.

## Current repository state

The API exposes `/health/live` and DB-backed `/health/ready`; Compose defines container health; CI verifies services. No production metric endpoint/exporter, histogram, distributed trace, dashboard, alert rule, on-call channel, SLO, error budget, telemetry canary, backup/restore signal, or incident integration exists. Any numeric target below is planned and must be measured before being called achieved.

## Scope and non-goals

In scope: API/database/worker/runtime, queue/workflow, agents/evaluations, six provider capabilities, Gmail OAuth/send/history/replies, policy/approval/suppression/controls, budgets/costs, sessions/security, retention/backups, telemetry pipeline, SLOs, alerts and dashboards.

Non-goals: per-recipient/mailbox/session/experiment labels; public status page; 24/7 staffing claim; alerts that mutate product state before canonical control commands except explicitly defined fail-closed local watchdog; tracing as audit; one giant dashboard; availability SLO that tolerates any unauthorized send; or measuring only happy-path latency.

## Exact planned implementation surfaces

Create `observability/metrics.py`, `observability/spans.py`, `observability/slo.py`, `observability/alerts.py`, collector/dashboard/alert configuration under deployment infrastructure, and tests. Instrument through OBS-01 contexts. Dashboard query services may read authoritative DB projections; metric exporter never writes product tables. Alert actions open `incidents` through `IncidentCommandService` or page the operator after/alongside canonical truth; they do not send Gmail.

### Exact metric registry and label budget

All names below use OpenTelemetry dotted form; Prometheus translation may replace dots with underscores. Counters end conceptually in `.count`, histograms declare units, gauges describe current bounded state. Every label combination has a fixed registry and cardinality budget verified in CI.

| Instrument (unit/type) | Allowed labels only | Purpose |
| --- | --- | --- |
| `alon_ai.http.server.request.duration` (`s`, histogram) | `service.name`, route template, method, status class | private API latency/availability |
| `alon_ai.http.server.request.count` (counter) | same | rate/errors; no actual path/ID |
| `alon_ai.command.execution.duration` (`s`, histogram) | command type enum, outcome, replay boolean | command/idempotency health |
| `alon_ai.command.execution.count` | command type, outcome, safe error code | conflicts/denials/failures |
| `alon_ai.workflow.run.count` | workflow type/version, terminal state, runtime | finite-run outcomes |
| `alon_ai.workflow.step.duration` (`s`) | workflow type/version, step enum, outcome, replay boolean | stall/version/replay diagnosis |
| `alon_ai.workflow.active` (up-down counter) | workflow type, canonical state | bounded concurrency |
| `alon_ai.agent.run.duration` (`s`) / `.count` | agent type/version, terminal state, fixture mode | runtime quality/latency population |
| `alon_ai.provider.call.duration` (`s`) / `.count` | provider registry name, six-capability enum, outcome, safe error code, fixture mode | dependency/capability health |
| `alon_ai.provider.usage` (counter) | provider, capability, usage kind `input_token\|output_token\|request\|byte\|result` | bounded usage; value only |
| `alon_ai.policy.decision.count` | scope, policy version, allowed, safe reason code | deterministic denials/drift |
| `alon_ai.suppression.denial.count` | scope `GLOBAL\|BUSINESS\|RECIPIENT` | last-mile stop evidence |
| `alon_ai.control.state` (gauge 0/1) | exact control name | independent authority status |
| `alon_ai.control.acknowledgement.duration` (`s`) | control name, action, outcome | commit-to-runtime propagation |
| `alon_ai.gmail.send.attempt.count` | attempt terminal/current state, outcome, authority mode `TEST\|PRODUCT` | send ledger safety |
| `alon_ai.gmail.send.boundary.duration` (`s`) | boundary enum, outcome | kill-point latency |
| `alon_ai.gmail.ambiguity.age` (`s`, histogram/gauge aggregate) | age bucket/outcome only | unresolved visibility; no attempt ID label |
| `alon_ai.gmail.history.page.count` / `.duration` | outcome, gap boolean | sync/cursor health |
| `alon_ai.gmail.reply.count` | safe class `REPLY\|UNSUBSCRIBE_SUSPECTED\|BOUNCE\|OTHER`, deterministic-stop boolean | no content/recipient |
| `alon_ai.oauth.saga.count` / `.age` | identity kind `OPERATOR\|GMAIL`, registered state/outcome/reason | flow/replay/stuck/GC health |
| `alon_ai.session.lifecycle.count` | action/outcome/reason | auth/rotation/revoke health |
| `alon_ai.budget.reservation.count` | scope, currency, state | reservation lifecycle |
| `alon_ai.cost.amount` (minor-unit counter) | provider, operation class, original currency | original-currency cost only; OBS-03 |
| `alon_ai.cost.reconciliation.age` (`s`) | provider, state | missing/late charges |
| `alon_ai.evaluation.case.count` | suite/agent type, repetition, passed, hard-safety boolean | promotion/continuous eval |
| `alon_ai.incident.open` (gauge) | canonical severity, trigger category | active operational risk |
| `alon_ai.backup.age` / `alon_ai.restore.proof.age` (`s`) | data kind `DATABASE\|SECRET_OBJECT\|TELEMETRY_CONFIG`, outcome | recovery freshness |
| `alon_ai.telemetry.export.count` / `.lag` (`s`) | signal, outcome/drop reason | self-observation |

Forbidden metric labels include every UUID/record ID, hashes/digests, idempotency/request/correlation/trace IDs, subject/session/IP/user agent, recipient/business/mailbox/campaign/experiment, actual URL/path/query, prompt/model input/output, exception/error/detail text, provider request ID, source URI/domain, free-form reason, cost-entry/invoice/FX source ID, or timestamps. `model_name`/release commit may appear in logs/traces and dashboards as filters only after bounded registry review, not high-churn metric labels. CI fails when projected series exceed the per-instrument budget (default 500, total 10,000 for the solo deployment).

### Span model and durable execution

Root/server spans: `HTTP {method} {route}`. Internal spans: `command {type}`, `workflow {type}`, `workflow.step {step}`, `agent {agent_type}`, `provider {capability}`, `gmail.oauth {operation}`, `gmail.send {boundary}`, `gmail.history {operation}`, `db.transaction {operation_class}`, `cost.reconcile`, `backup {operation}`, and `incident {operation}`. Use standard `SpanKind` and HTTP/DB semantic attributes where safe; never SQL parameters or actual URL.

Status `ERROR` means the operation failed unexpectedly, not a normal deterministic policy denial; denial outcome is an event/attribute with span status unset unless system failure occurred. Durable resume/replay creates a new trace with an OTel span link to persisted prior context and constant correlation, as OBS-01 defines. Trace sampling retains 100% of security/auth denials, controls, final-SEND attempts, ambiguity/reconciliation, incidents/repairs, backup/restore, promotion/rollback, and unexpected errors; ordinary read/success traces start at 10% and are tuned only after cost/diagnostic evidence. No sampling changes authoritative counters.

### Planned SLOs and zero-tolerance safety objectives

| Objective | Window/target | Measurement and error-budget action |
| --- | --- | --- |
| private API authenticated availability | rolling 30 days >=99.5%, excluding declared operator maintenance and client 4xx | server 5xx/timeout over eligible requests; budget burn pauses feature releases |
| command commit latency | rolling 7 days p95 <=1s; control disable p95 <=2s healthy DB | command histogram; breach pages if control, ticket otherwise |
| kill propagation | p95 <=5s commit-to-dequeue acknowledgement | control ack; timeout leaves disabled and opens incident |
| unauthorized/duplicate/suppressed/wrong-mailbox/post-disable provider calls | exactly 0 in every window | DB/provider invariant; one occurrence is Critical, both controls false, no error budget |
| ambiguous send visibility | 100% possibly-called outcomes recorded `AMBIGUOUS` within result transaction/restart recovery; operator alert <=60s; M6 test reconciliation target <=15m | authoritative attempts plus alert timestamps; one hidden/blind retry is Critical |
| workflow finite completion | >=99% terminal within frozen run deadline; zero immortal active run | workflow rows/snapshots; stall alert at min(5m, configured deadline threshold) |
| provider result/cost completeness | 100% provider calls have terminal typed result/ledger; 100% incurred costs reconciled <=15m or held/incident | provider/cost rows, not metric inference; missing blocks new paid calls |
| eval promotion integrity | 100% promotions have 552 cases × three fresh candidate captures and all AGENT-10 gates | manifest/result count/hashes; one missing rejects promotion |
| telemetry safety availability | exporter lag <2m; no >5m gap for Critical signals | self-health plus DB canary; >5m forces send controls false |
| backup/restore | successful encrypted backup <=24h old; clean restore proof <=90d old | signed manifests/drill; stale/failed proof blocks M8/control enable |
| privacy | zero secret/PII/content canary detections in telemetry/eval/Graphify | scans; one finding is Critical leak response |

SLO percentages never offset a safety objective. Low traffic uses event-count plus synthetic canary evidence; a month with no sends does not prove send safety. Targets are provisional until load/security/chaos tests validate measurement and capacity.

### Dashboards and alert rules

Five dashboards only initially:

1. **Safety and authority:** both controls, M1/M6/current SEC evidence age, open incidents, suppression denials, final-SEND outcomes, ambiguity age, last provider call and post-disable invariant.
2. **Workflow/agent/provider:** run states/deadlines/replays, queue age, agent terminal outcomes, six capability latency/errors/usage, active promotion/version.
3. **Gmail/OAuth/replies:** saga states/age/replay, mailbox consistency, send boundary/outcome, rate lease, history cursor gap/age, replies/unsubscribe/bounces—with no recipient/mailbox labels.
4. **Cost/budget/evaluation:** reservation/reconciliation, original currencies and ILS reporting in panels (not combined metric), caps/burn, eval suite/repetition/hard gates/rolling windows.
5. **Platform/recovery/privacy:** API/DB/worker, telemetry export, disk/cert/clock, backup/restore age, retention/rights jobs, auth/security events, release provenance.

Alerts are symptoms with an owner/runbook and dedupe key; no per-record page storm. `CRITICAL` pages immediately through one primary and one tested out-of-band channel independent of Alon AI Gmail credentials, while persisting an incident attempt locally. `HIGH` pages within five minutes; `MEDIUM` notifies and creates same-day task; `LOW/INFO` dashboard/review. Notification destination/provider is selected at M8 and allowlisted outbound-only—no generic inbound webhook/control endpoint. Every route has quarterly test, acknowledgement/escalation after 10 minutes for Critical, and safe content: severity/trigger/runbook/correlation/incident ID only.

Required alerts: any zero-tolerance violation; control disable ack timeout; ambiguity >60s and >15m; Gmail/provider identity conflict; OAuth replay/stuck/mismatch; session allowlist/fixation/CSRF anomaly; DB unavailable/invariant failure; budget/cost overrun or missing reconciliation; provider hard error/latency/quota; workflow deadline/replay/version mismatch; telemetry lag/drop/canary; disk/cert/clock; backup >24h/failed or restore >90d; evaluation hard/window/max-cost regression; retention/rights/hold failure; supply-chain/release mismatch; complaint/unsubscribe/Google-policy kill.

## Ordered implementation tasks

- [ ] **Implement exact metric/span registries —** Input: OBS-01 and every application boundary. Operation: define instruments/units/labels/series budgets and spans/links/sampling. Output: versioned telemetry package. Test evidence: registry/schema/cardinality/sampling tests. Failure behavior: reject unregistered signal/release.
- [ ] **Instrument safety and service paths —** Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup. Operation: emit authoritative-record-derived counters/gauges and spans without replay duplication. Output: complete signals. Test evidence: golden count/latency/exemplar fixtures at each crash boundary. Failure behavior: applicable milestone blocked.
- [ ] **Build five dashboards and SLO calculations —** Input: low-card metrics plus authoritative projections. Operation: implement exact panels/queries/windows/burn rules and show data freshness. Output: one-operator operational views. Test evidence: empty/low-volume/stale/gap/timezone/currency fixtures. Failure behavior: display unknown and disable unsafe interpretation.
- [ ] **Implement alert routes/runbooks —** Input: thresholds, severity mapping and notification endpoints. Operation: dedupe/page/persist/ack/escalate/test with safe payload. Output: actionable alerts. Test evidence: fire every rule and disable each channel. Failure behavior: Critical local incident plus controls false when safety channel unavailable.
- [ ] **Prove SLO and blind-spot gates —** Input: load/security/chaos/restore scenarios. Operation: validate measurements/targets and reconcile metrics to DB rows. Output: signed M8 SLO baseline. Test evidence: injected gaps/replay/counter reset/sampling/cardinality. Failure behavior: no production-readiness claim/control enable.

## Test strategy

- **Registry `test_metric_names_types_units_labels_and_series_budgets_are_exact`.**
- **Privacy `test_no_id_hash_path_text_recipient_mailbox_session_prompt_or_provider_payload_is_a_metric_label`.**
- **Trace `test_durable_replay_links_new_trace_and_critical_sampling_is_one_hundred_percent`.**
- **Counts `test_metrics_reconcile_to_authoritative_commands_runs_calls_attempts_costs_and_evals_without_replay_double_count`.**
- **SLO `test_zero_tolerance_safety_event_cannot_be_hidden_by_availability_error_budget`.**
- **Alerts `test_every_critical_rule_pages_safely_opens_incident_and_links_one_runbook_when_channels_fail`.**
- **Dashboards `test_unknown_stale_empty_low_volume_and_currency_states_are_not_rendered_as_success`.**

## Security, privacy, compliance, idempotency, observability, and cost

Collector/dashboard/alert access is SEC-02 authenticated/private, encrypted and audited. Labels are bounded/non-PII; exemplars contain trace IDs only inside restricted tooling. Metric recording is idempotent at authoritative record consumption or tolerant to monotonic exporter reset; dashboards never write product truth. Telemetry storage/notification costs are capped and reviewed; sampling cannot remove Critical evidence.

## Failure, rollback, and operator recovery

On bad instrumentation/cardinality/leak/false count/alert outage, stop or roll back the exporter/rule, preserve authoritative DB truth, and use local safe queries. A safety-blind condition beyond five minutes commits controls false. Rebuild dashboards from low-cardinality metrics and reconcile exact row/event counts before trusting them. Never “fix” an SLO by excluding failures, relabeling a Critical event, relaxing the zero-tolerance objective, or deleting series.

## Acceptance and retained evidence

- [ ] Exact metrics/labels/series budgets, spans/links/sampling, SLOs, dashboards and alerts cover every product/security/cost/eval/recovery boundary.
- [ ] Safety objectives are zero-tolerance and telemetry truth reconciles to authoritative records.
- [ ] Critical signals are private, PII-free, actionable, independently routed, tested, and linked to one runbook.
- [ ] Current planned-versus-implemented truth and data freshness are explicit.

Retain registry/cardinality report, sanitized trace examples, authoritative reconciliation queries/results, SLO formulas/baseline, dashboard exports/screenshots, alert rules/routes/safe payloads, notification drills, load/chaos/gap tests, and cost/retention settings.

## Dependencies and next deliverable

OBS-02 consumes OBS-01 and feeds [OBS-05 incident response](05-incident-response.md). Its M6 signals are required for the Gmail pilot and its full evidence unlocks M8 monitored deployment; no alert/dashboard grants business authority.
