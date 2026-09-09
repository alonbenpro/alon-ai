# Metrics, Tracing, SLOs, Dashboards, and Alerts

**Document ID:** OBS-02
**Status:** Planned M8 operations gate; liveness/readiness and structured foundation logs exist, but no OTel metrics/traces, SLOs, alert manager, dashboards, or notification path exists
**Milestone:** M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `OBS-02-T01 <- OBS-01-T01,OBS-01-T03; OBS-02-T02 <- OBS-02-T01,BACKEND-02-T05,DB-06-T01,WF-05-T05,AGENT-10-T05,SEC-05-T04,OBS-03-T02,INFRA-04-T02; OBS-02-T03 <- OBS-02-T02; OBS-02-T04 <- OBS-02-T03; OBS-02-T05 <- OBS-02-T04`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** Exact low-cardinality metrics, span model, SLO/error budgets, dashboards, alert rules/routes, and telemetry-health gates
**Unlocks:** M8 monitored operation and OBS-05 incident detection
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Staged-validation telemetry adds safe stage ordinal, canonical increment, cumulative maximum, admitted/delivered counts, remaining capacity, barrier kind, and rule version—never recipient identity. Separate alerts fire for stage overrun, authorized pre-revenue maximum `300` overrun, cross-stage reuse, missing/stale prior `CONTINUE`, admission during observation, and immediate-1,000 attempts. Each alert disables new admission and follows the existing send-safety incident path.

Alon can answer five questions without querying raw personal data: is the private service usable; are workflows/agents/providers healthy and bounded; is any send/control/suppression/ambiguity invariant at risk; are costs complete and within budget; and can incidents/backups/recovery be trusted. Alerts are actionable for one operator, not a noisy imitation of a large SRE team.

The implementation follows OpenTelemetry [metric](https://opentelemetry.io/docs/specs/semconv/general/metrics/) and [trace](https://opentelemetry.io/docs/specs/semconv/general/trace/) semantics as applicable, accessed 2026-08-29. Custom metrics use an `alon_ai.` namespace and documented units/labels.

## Current repository state

The API exposes `/health/live` and DB-backed `/health/ready`; Compose defines container health; CI verifies services. No production metric endpoint/exporter, histogram, distributed trace, dashboard, alert rule, on-call channel, SLO, error budget, telemetry canary, backup/restore signal, or incident integration exists. Any numeric target below is planned and must be measured before being called achieved.

## Scope and non-goals

In scope: API/database/worker/runtime, queue/workflow, agents/evaluations, registered provider capabilities, Gmail OAuth/send/history/replies, policy/action-authorization/suppression/controls, budgets/costs, sessions/security, retention/backups, telemetry pipeline, SLOs, alerts and dashboards.

Non-goals: per-recipient/mailbox/session/experiment labels; public status page; 24/7 staffing claim; alerts that mutate product state before canonical control commands except explicitly defined fail-closed local watchdog; tracing as audit; one giant dashboard; availability SLO that tolerates any unauthorized send; or measuring only happy-path latency.

## Exact planned implementation surfaces

Create `observability/metrics.py`, `observability/spans.py`, `observability/slo.py`, `observability/alerts.py`, collector/dashboard/alert configuration under deployment infrastructure, and tests. Instrument through OBS-01 contexts. Dashboard query services may read authoritative DB projections; metric exporter never writes product tables. Alert actions open `incidents` through `IncidentCommandService` or page the operator after/alongside canonical truth; they do not send Gmail.

### Exact metric registry and label budget

All names below use OpenTelemetry dotted form; Prometheus translation may replace dots with underscores. Counters end conceptually in `.count`, histograms declare units, gauges describe current bounded state. Every label combination comes from signed `MetricAttributeRegistryV1` version `metrics.attributes.v1`; unknown values are rejected before recording. Software/release/model/prompt/tool/workflow/agent/policy/config versions are categorically absent from metric attributes and remain only in bounded logs, traces, evidence and dashboard joins.

The following JSON is the normative, signed input to code generation. A literal domain is exactly the listed values. A tuple domain admits only the listed complete rows, never its Cartesian product. An import is legal only because the named source section enumerates every value/tuple and CI derives that exact set—not merely its stated count—before accepting the cardinality. No other source or runtime-discovered value is admitted.

<!-- METRIC_ATTRIBUTE_REGISTRY_V1_BEGIN -->
```json
{
  "schema_version": "metrics.attributes.v1",
  "unknown_value_action": "REJECT_BEFORE_RECORD",
  "literal_domains": {
    "service.name": ["alon-ai-api"],
    "http.response.status_class": ["2xx","3xx","4xx","5xx"],
    "operation.outcome": ["SUCCEEDED","DENIED","FAILED","UNAVAILABLE","CANCELLED"],
    "command.replay": [false,true],
    "workflow.type": ["IDEA_VALIDATION","LEAD_QUALIFICATION","OUTREACH_AND_REPLY","EXPERIMENT_EVALUATION","CALL_BOOKING","CHECKPOINT_EVALUATION","GLOBAL_LEARNING"],
    "workflow.terminal_state": ["SUCCEEDED","FAILED","CANCELLED"],
    "workflow.runtime": ["DBOS","TEMPORAL"],
    "workflow.replay": [false,true],
    "workflow.state": ["PENDING","RUNNING","PAUSE_REQUESTED","PAUSED","CANCEL_REQUESTED","CANCELLED","SUCCEEDED","FAILED"],
    "agent.type": ["IDEA_DISCOVERY","MARKET_RESEARCH","OFFER_DESIGN","LEAD_DISCOVERY","LEAD_RESEARCH","LEAD_QUALIFICATION","EMAIL_WRITING","REPLY_EVALUATION","EXPERIMENT_EVALUATION","GLOBAL_LEARNING"],
    "agent.terminal_state": ["SUCCESS","ABSTAIN","FAILED"],
    "execution.mode": ["LIVE","RECORDED","SYNTHETIC"],
    "provider.capability": ["model.complete_structured","evidence.read","search.query","page.extract","business.search","business.details","lead.discover"],
    "policy.scope": ["ACTION_CREATION","SEND","BOOKING","COMMERCIAL","CHECKPOINT","STRATEGY"],
    "policy.allowed": [false,true],
    "suppression.scope": ["GLOBAL","BUSINESS","RECIPIENT"],
    "suppression.source": ["OPERATOR","GMAIL_UNSUBSCRIBE","GMAIL_HARD_BOUNCE","GMAIL_COMPLAINT","GMAIL_SOFT_BOUNCE_LIMIT","PUBLIC_UNSUBSCRIBE","QUALIFIED_NO_FUTURE_CONTACT","LEGAL_PROHIBITION"],
    "control.name": ["PRODUCT_OUTREACH","TEST_INBOX_SENDING","CALENDAR_WRITES","TEST_CALENDAR_WRITES"],
    "control.action": ["DISABLE","ENABLE"],
    "send.attempt_state": ["STARTED","AMBIGUOUS","RECONCILING","SENT","FAILED"],
    "send.authority_mode": ["TEST_INBOX_ONLY","PRODUCT_ELIGIBLE"],
    "gmail.boundary": ["CANCEL_PRE_UOW","LOCK_AUTHORITY","VERIFY_IMMUTABLE","VERIFY_MODE","VERIFY_ELIGIBILITY","VERIFY_ACTION_AUTHORITY","BUILD_CURRENT_FACTS","EVALUATE_SEND_POLICY","COMMIT_ATTEMPT","CANCEL_PRE_CALL","GMAIL_CALL","LOCK_RESULT","COMMIT_RESULT","SCHEDULE_FOLLOWUP"],
    "gmail.cursor_gap": [false,true],
    "gmail.signal_kind": ["NONE","REPLY","UNSUBSCRIBE","HARD_BOUNCE","SOFT_BOUNCE","COMPLAINT"],
    "suppression.committed": [false,true],
    "session.action": ["CREATED","TOUCHED","ROTATED","REAUTHENTICATED","LOGGED_OUT","REVOKED","EXPIRED","EVICTED"],
    "budget.scope": ["PROVIDER_CALL","WORKFLOW_RUN","EXPERIMENT","CAMPAIGN_SEND"],
    "currency": ["ILS","USD"],
    "budget.state": ["RESERVED","RELEASED","RECONCILED","EXPIRED"],
    "provider.operation_class": ["MODEL","SEARCH","PAGE","BUSINESS_DATA","GMAIL","IDENTITY_SECRET","INFRASTRUCTURE","CALENDAR"],
    "cost.state": ["PENDING_USAGE","PENDING_FX","PENDING_INVOICE","DISCREPANCY"],
    "evaluation.repetition": [1,2,3],
    "evaluation.passed": [false,true],
    "evaluation.hard_safety": [false,true],
    "backup.data_kind": ["PRIMARY","DR"],
    "telemetry.signal": ["LOG","METRIC","TRACE"],
    "qualification.phase": ["PRELIMINARY","FINAL"],
    "booking.action": ["CREATE","RESCHEDULE","CANCEL"],
    "booking.state": ["INTENT_RECORDED","SLOTS_PROPOSED","CONFIRMATION_PENDING","CONFIRMED","CREATING","AMBIGUOUS","RECONCILING","BOOKED","RESCHEDULE_PENDING","CANCEL_PENDING","CANCELLED","EXPIRED","FAILED"],
    "checkpoint.decision": ["CONTINUE","REVISE","KILL","INCONCLUSIVE","SAFETY_STOP"],
    "learning.result": ["PROMOTE","KEEP","ROLLBACK","INSUFFICIENT_EVIDENCE"],
    "strategy.action": ["PROMOTE","ACTIVATE","ROLLBACK"],
    "objection.category": ["PRICE","SCOPE","TIMING","TRUST","AUTHORITY","NEED","UNKNOWN"],
    "objection.resolution": ["RESOLVED","UNRESOLVED","DECLINED","UNKNOWN"]
  },
  "tuple_domains": {
    "workflow.type|workflow.step": [
      ["IDEA_VALIDATION","IDEA"],
      ["IDEA_VALIDATION","MARKET_RESEARCH"],
      ["IDEA_VALIDATION","OFFER"],
      ["IDEA_VALIDATION","BUNDLE"],
      ["LEAD_QUALIFICATION","DISCOVERY"],
      ["LEAD_QUALIFICATION","PRELIMINARY"],
      ["LEAD_QUALIFICATION","LEAD_RESEARCH"],
      ["LEAD_QUALIFICATION","FINAL"],
      ["OUTREACH_AND_REPLY","PREPARE_AUTHORITY"],
      ["OUTREACH_AND_REPLY","SEND"],
      ["OUTREACH_AND_REPLY","RECONCILE"],
      ["OUTREACH_AND_REPLY","HISTORY_SYNC"],
      ["OUTREACH_AND_REPLY","RECIPIENT_SIGNAL"],
      ["OUTREACH_AND_REPLY","REPLY_EVALUATE"],
      ["OUTREACH_AND_REPLY","NEGOTIATE"],
      ["EXPERIMENT_EVALUATION","EVALUATE"],
      ["CALL_BOOKING","SLOTS"],
      ["CALL_BOOKING","CONFIRM"],
      ["CALL_BOOKING","WRITE"],
      ["CALL_BOOKING","RECONCILE"],
      ["CHECKPOINT_EVALUATION","CLOSE"],
      ["CHECKPOINT_EVALUATION","FREEZE"],
      ["CHECKPOINT_EVALUATION","DECIDE"],
      ["GLOBAL_LEARNING","EVALUATE"],
      ["GLOBAL_LEARNING","PROMOTE"],
      ["GLOBAL_LEARNING","ACTIVATE"],
      ["GLOBAL_LEARNING","ROLLBACK"]
    ],
    "oauth.identity_kind|oauth.state": [
      ["OIDC","PENDING"],
      ["OIDC","CLAIMED"],
      ["OIDC","CONSUMED"],
      ["OIDC","EXPIRED"],
      ["GMAIL","ISSUED"],
      ["GMAIL","CLAIMED"],
      ["GMAIL","EXCHANGE_STARTED"],
      ["GMAIL","CREDENTIAL_STAGED"],
      ["GMAIL","CREDENTIAL_ACTIVE"],
      ["GMAIL","DB_COMMITTED"],
      ["GMAIL","CONSUMED_SUCCESS"],
      ["GMAIL","CONSUMED_FAILURE"]
    ],
    "operation.outcome|telemetry.drop_reason": [
      ["SUCCEEDED","NONE"],
      ["DENIED","POLICY"],
      ["DENIED","PRIVACY_FILTER"],
      ["FAILED","EXPORT_ERROR"],
      ["UNAVAILABLE","SINK_UNAVAILABLE"],
      ["CANCELLED","SHUTDOWN"]
    ]
  },
  "imports": {
    "http.route|http.request.method": {"catalog":"BackendOperationCatalogV1","source":"BACKEND-02#exact-route-and-openapi-operation-manifest+BACKEND-02#autonomous-sales-api-operations","cardinality_rule":"EXACT_IMPORTED_SET_SIZE"},
    "command.type": {"catalog":"CommandCatalogV1","source":"BACKEND-05#exact-command-registry-and-authority","cardinality_rule":"EXACT_IMPORTED_SET_SIZE"},
    "policy.reason_code": {"catalog":"PolicyReasonCodeV1PlusNone","source":"BACKEND-03#fixed-final-effect-rule-order-and-reason-taxonomy","cardinality_rule":"EXACT_IMPORTED_SET_SIZE"},
    "evaluation.suite|agent.type": {"catalog":"AgentEvaluationSuiteMapV1","source":"AGENT-10#exact-suite-manifests-and-promotion-thresholds","cardinality_rule":"EXACT_IMPORTED_SET_SIZE"},
    "incident.severity|incident.trigger_code|incident.alert_id|incident.runbook_id": {"catalog":"IncidentRouteV1","source":"OBS-05#closed-incident-alert-runbook-resolution-and-repair-catalogs","cardinality_rule":"EXACT_IMPORTED_SET_SIZE"}
  }
}
```
<!-- METRIC_ATTRIBUTE_REGISTRY_V1_END -->

CI requires every instrument attribute to have exactly one literal, tuple or imported owner; duplicated/missing ownership, empty/repeated values, source drift or count without set equality fails closed. Derive imported sets from actual canonical rows and hash the resolved registry. Provider classes are allocation classes, not provider strings. The Gmail boundary tuple maps in order to BACKEND-04's fourteen steps. Workflow tuple labels are the exact local instrumentation projection of the named WF-03/04/05/07/08/09 boundaries; they do not create domain workflow enums.

| Instrument | OTel instrument | UCUM unit | Aggregation / temporality | Allowed attributes only | Max series |
| --- | --- | --- | --- | --- | ---: |
| `alon_ai.http.server.request.duration` | Histogram | `s` | `FAST_SECONDS`, cumulative | `service.name`, valid `(http.route,http.request.method)`, `http.response.status_class` | derived exact allowed tuple-domain product |
| `alon_ai.http.server.request.count` | Counter | `{request}` | monotonic sum, cumulative | `service.name`, valid `(http.route,http.request.method)`, `http.response.status_class` | derived exact allowed tuple-domain product |
| `alon_ai.command.execution.duration` | Histogram | `s` | `FAST_SECONDS`, cumulative | `command.type`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.command.execution.count` | Counter | `{command}` | monotonic sum, cumulative | `command.type`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.workflow.run.count` | Counter | `{run}` | monotonic sum, cumulative | `workflow.type`, `workflow.terminal_state`, `workflow.runtime` | derived exact allowed tuple-domain product |
| `alon_ai.workflow.step.duration` | Histogram | `s` | `DURABLE_SECONDS`, cumulative | valid `(workflow.type,workflow.step)`, `operation.outcome`, `workflow.replay` | derived exact allowed tuple-domain product |
| `alon_ai.workflow.active` | UpDownCounter | `{run}` | nonmonotonic sum, cumulative | `workflow.type`, `workflow.state` | derived exact allowed tuple-domain product |
| `alon_ai.agent.run.duration` | Histogram | `s` | `DURABLE_SECONDS`, cumulative | `agent.type`, `agent.terminal_state`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.agent.run.count` | Counter | `{run}` | monotonic sum, cumulative | `agent.type`, `agent.terminal_state`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.call.duration` | Histogram | `s` | `DURABLE_SECONDS`, cumulative | `provider.capability`, `operation.outcome`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.request.count` | Counter | `{request}` | monotonic sum, cumulative | `provider.capability`, `operation.outcome`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.input_token.count` | Counter | `{token}` | monotonic sum, cumulative | `provider.capability`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.output_token.count` | Counter | `{token}` | monotonic sum, cumulative | `provider.capability`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.request.size` | Histogram | `By` | `BYTE_SIZE`, cumulative | `provider.capability`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.response.size` | Histogram | `By` | `BYTE_SIZE`, cumulative | `provider.capability`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.provider.result.count` | Counter | `{result}` | monotonic sum, cumulative | `provider.capability`, `operation.outcome`, `execution.mode` | derived exact allowed tuple-domain product |
| `alon_ai.policy.decision.count` | Counter | `{decision}` | monotonic sum, cumulative | `policy.allowed`, `policy.reason_code` | derived exact allowed tuple-domain product |
| `alon_ai.suppression.denial.count` | Counter | `{denial}` | monotonic sum, cumulative | `suppression.scope`, `suppression.source` | derived exact allowed tuple-domain product |
| `alon_ai.control.state` | ObservableGauge | `1` | last value, instantaneous (temporality N/A) | `control.name` | derived exact allowed tuple-domain product |
| `alon_ai.control.acknowledgement.duration` | Histogram | `s` | `FAST_SECONDS`, cumulative | `control.name`, `control.action`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.send.attempt.count` | Counter | `{attempt}` | monotonic sum, cumulative | `send.attempt_state`, `operation.outcome`, `send.authority_mode` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.send.boundary.duration` | Histogram | `s` | `DURABLE_SECONDS`, cumulative | `gmail.boundary`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.ambiguity.oldest_age` | ObservableGauge | `s` | last value, instantaneous (temporality N/A) | `send.authority_mode` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.ambiguity.resolution.duration` | Histogram | `s` | `AGE_SECONDS`, cumulative | `operation.outcome`, `send.authority_mode` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.history.page.count` | Counter | `{page}` | monotonic sum, cumulative | `operation.outcome`, `gmail.cursor_gap` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.history.page.duration` | Histogram | `s` | `DURABLE_SECONDS`, cumulative | `operation.outcome`, `gmail.cursor_gap` | derived exact allowed tuple-domain product |
| `alon_ai.gmail.recipient_signal.count` | Counter | `{signal}` | monotonic sum, cumulative | `gmail.signal_kind`, `suppression.committed` | derived exact allowed tuple-domain product |
| `alon_ai.oauth.saga.count` | Counter | `{saga}` | monotonic sum, cumulative | valid `(oauth.identity_kind,oauth.state)`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.oauth.saga.oldest_age` | ObservableGauge | `s` | last value, instantaneous (temporality N/A) | valid `(oauth.identity_kind,oauth.state)` | derived exact allowed tuple-domain product |
| `alon_ai.session.lifecycle.count` | Counter | `{session}` | monotonic sum, cumulative | `session.action`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.budget.reservation.count` | Counter | `{reservation}` | monotonic sum, cumulative | `budget.scope`, `currency`, `budget.state` | derived exact allowed tuple-domain product |
| `alon_ai.cost.amount` | Counter | `{currency_minor}` | monotonic sum, cumulative; group by `currency` before sum | `provider.operation_class`, `currency` | derived exact allowed tuple-domain product |
| `alon_ai.cost.reconciliation.oldest_age` | ObservableGauge | `s` | last value, instantaneous (temporality N/A) | `provider.operation_class`, `cost.state` | derived exact allowed tuple-domain product |
| `alon_ai.evaluation.case.count` | Counter | `{case}` | monotonic sum, cumulative | valid `(evaluation.suite,agent.type)`, `evaluation.repetition`, `evaluation.passed`, `evaluation.hard_safety` | derived exact allowed tuple-domain product |
| `alon_ai.incident.open` | ObservableGauge | `{incident}` | last value, instantaneous (temporality N/A) | valid `(incident.severity,incident.trigger_code,incident.alert_id,incident.runbook_id)` | derived exact allowed tuple-domain product |
| `alon_ai.backup.oldest_age` | ObservableGauge | `s` | last value, instantaneous (temporality N/A) | `backup.data_kind`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.restore.proof.oldest_age` | ObservableGauge | `s` | last value, instantaneous (temporality N/A) | `backup.data_kind`, `operation.outcome` | derived exact allowed tuple-domain product |
| `alon_ai.telemetry.export.count` | Counter | `{export}` | monotonic sum, cumulative | `telemetry.signal`, valid `(operation.outcome,telemetry.drop_reason)` | derived exact allowed tuple-domain product |
| `alon_ai.telemetry.export.lag` | Histogram | `s` | `AGE_SECONDS`, cumulative | `telemetry.signal`, `operation.outcome` | derived exact allowed tuple-domain product |

The aggregation registry is closed: `FAST_SECONDS=[0.005,0.01,0.025,0.05,0.1,0.25,0.5,1,2,5,10]`, `DURABLE_SECONDS=[0.01,0.05,0.1,0.25,0.5,1,2,5,10,30,60,120,300,900,3600]`, `AGE_SECONDS=[1,5,15,30,60,120,300,900,3600,21600,86400,604800,7776000]`, and `BYTE_SIZE=[128,512,1024,4096,16384,65536,262144,1048576,5000000]`. Values use exact base units before recording; milliseconds, token/request/result counts, and bytes never share an instrument. Counters reject negative values; duration/size histograms reject negative/non-finite values; gauges publish one value per allowed attribute set per collection.

Canonical vectors: one provider call with 17 input tokens, 4 output tokens, 1,024 request bytes and 2,048 response bytes records `1` call, `17` and `4` on the two token counters, one `1024`/`2048` size observation and one result—never a value `3094` on a combined usage series. An ambiguity open for 61 seconds records gauge `61`; when resolved at 75 seconds it records resolution histogram `75` and disappears from the next gauge collection. A `USD 123` minor-unit cost and `ILS 456` minor-unit cost remain two currency groups; a query that drops `currency` before summing is invalid. CI golden vectors cover bucket boundaries, cumulative reset handling, missing attributes, unknown enum values and observable-gauge disappearance.

Forbidden metric labels include every UUID/record ID, hashes/digests, idempotency/request/correlation/trace IDs, subject/session/IP/user agent, recipient/business/mailbox/campaign/experiment, actual URL/path/query, prompt/model input/output, exception/error/detail text, provider request ID, source URI/domain, free-form reason, cost-entry/invoice/FX source ID, or timestamps. `model_name`/release commit may appear in logs/traces and dashboards as filters only after bounded registry review, not high-churn metric labels. CI fails when projected series exceed the per-instrument budget (default 500, total 10,000 for the solo deployment).

Unknown instrument/type/unit/aggregation/temporality/attribute/value rejects before recording. CI parses the complete instrument table and additive sales rows, resolves every literal/import/valid tuple, computes exact per-instrument series as the product of independent domain sizes with tuple sizes counted once, and signs the ordered instrument/attribute/budget manifest. Command replay and policy scope remain in operational records instead of multiplying the counter label sets. Default budget is 500 per instrument and 10,000 total; any excess blocks instrumentation until dimensions are narrowed by an explicit reviewed registry version. Do not silently truncate values, sample counters or raise a limit. No fixed historical count/vector is authoritative. Repeated/missing rows, cardinality drift, or any version/record-ID dimension fail. Units, native currencies and semantic event populations remain separate.

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
| eval promotion integrity | 100% promotions have the complete AGENT-10 suite set × three fresh candidate captures and all AGENT-10 gates | manifest/result count/hashes; one missing rejects promotion |
| telemetry safety availability | exporter lag <2m; no >5m gap for Critical signals | self-health plus DB canary; >5m forces send controls false |
| backup/restore | successful encrypted backup <=24h old; clean restore proof <=90d old | signed manifests/drill; stale/failed proof blocks M8/control enable |
| privacy | zero secret/PII/content canary detections in telemetry/eval/Graphify | scans; one finding is Critical leak response |

SLO percentages never offset a safety objective. Low traffic uses event-count plus synthetic canary evidence; a month with no sends does not prove send safety. Targets are provisional until load/security/chaos tests validate measurement and capacity.

### Dashboards and alert rules

Five dashboards only initially:

1. **Safety and authority:** both controls, M1/M6/current SEC evidence age, open incidents, suppression denials, final-SEND outcomes, ambiguity age, last provider call and post-disable invariant.
2. **Workflow/agent/provider:** run states/deadlines/replays, queue age, agent terminal outcomes, registered capability latency/errors/usage, active promotion/version.
3. **Gmail/OAuth/replies:** saga states/age/replay, mailbox consistency, send boundary/outcome, rate lease, history cursor gap/age, replies/unsubscribe/bounces, public-route availability/rate/WAF outcomes—with no recipient/mailbox/token/IP labels.
4. **Cost/budget/evaluation:** reservation/reconciliation, original currencies and ILS reporting in panels (not combined metric), caps/burn, eval suite/repetition/hard gates/rolling windows.
5. **Platform/recovery/privacy:** API/DB/worker, telemetry export, disk/cert/clock, backup/restore age, retention/rights jobs, auth/security events, release provenance.

Alerts are symptoms with an owner/runbook and dedupe key; no per-record page storm. `CRITICAL` pages immediately through one primary and one tested out-of-band channel independent of Alon AI Gmail credentials, while persisting an incident attempt locally. `HIGH` pages within five minutes; `MEDIUM` notifies and creates same-day task; `LOW/INFO` dashboard/review. Notification destination/provider is selected at M8 and allowlisted outbound-only—no generic inbound webhook/control endpoint. Every route has quarterly test, acknowledgement/escalation after 10 minutes for Critical, and safe content: severity/trigger/runbook/correlation/incident ID only.

Required alerts: any zero-tolerance violation; control disable ack timeout; ambiguity >60s and >15m; Gmail/provider identity conflict; OAuth replay/stuck/mismatch; session allowlist/fixation/CSRF anomaly; DB unavailable/invariant failure; budget/cost overrun or missing reconciliation; provider hard error/latency/quota; workflow deadline/replay/version mismatch; telemetry lag/drop/canary; disk/cert/clock; backup >24h/failed or restore >90d; evaluation hard/window/max-cost regression; retention/rights/hold failure; supply-chain/release mismatch; complaint/unsubscribe/Google-policy kill.

`AlertRuleV1={catalog_version:"incident.catalog.v1",alert_id,trigger_code,runbook_id,severity,condition_version,for_duration,clear_condition,dedupe_key_template}` is a closed registry. Alert instances may carry safe incident/correlation IDs, but only the catalog fields are labels. Exact v1 routing/thresholds are:

| Alert ID -> severity -> trigger -> runbook | Exact opening/escalation condition |
| --- | --- |
| `ALERT_AGENT_INJECTION -> CRITICAL -> AGENT_PROMPT_INJECTION_OR_POISONING -> IR-06` | one hard authority/injection/poisoning evaluation failure in a promoted/candidate path |
| `ALERT_PROVIDER_EXFILTRATION -> CRITICAL -> PROVIDER_EXFILTRATION -> IR-06` | one secret/PII canary or unauthorized provider field/egress finding |
| `ALERT_CREDENTIAL_OR_SESSION -> CRITICAL -> AUTH_OR_SECRET_COMPROMISE -> IR-03` | confirmed credential exposure, token/session replay, subject mismatch, or five auth anomalies in 5m |
| `ALERT_WEB_BOUNDARY -> CRITICAL -> WEB_SESSION_BOUNDARY_ATTACK -> IR-05` | one successful/bypass-indicating CSRF/XSS/session-fixation/open-redirect invariant or 20 blocked probes in 5m |
| `ALERT_EGRESS_SSRF -> CRITICAL -> SSRF_OR_DNS_REBINDING -> IR-05` | one private/link-local/metadata connection success or ten blocked target changes in 5m |
| `ALERT_CALLBACK_ABUSE -> CRITICAL -> CALLBACK_ABUSE -> IR-05` | one consumed-state/code splice or public unsubscribe WAF/CSRF/token-boundary bypass; or ten invalid callback arms/public token-method-CSRF probes in 5m, counted only by bounded route partition/reason |
| `ALERT_SEND_AUTHORITY_VIOLATION -> CRITICAL -> SEND_AUTHORITY_VIOLATION -> IR-01` | one unauthorized, duplicate, suppressed, wrong-mailbox or post-disable provider call |
| `ALERT_SUPPLY_CHAIN -> CRITICAL -> SUPPLY_CHAIN_COMPROMISE -> IR-09` | one signature/provenance/SBOM/image/lock mismatch in promoted release |
| `ALERT_WORKFLOW_REPLAY -> CRITICAL -> WORKFLOW_REPLAY_OR_VERSION_DRIFT -> IR-07` | one snapshot/digest/version/replay side-effect invariant failure or immortal run |
| `ALERT_BACKUP_RESTORE -> CRITICAL -> DATASTORE_OR_RESTORE_FAILURE -> IR-08` | backup age >24h, failed signature/backup, restore proof >90d, or one restore invariant failure |
| `ALERT_OPERATOR_REPAIR -> CRITICAL -> OPERATOR_OR_RECOVERY_ERROR -> IR-13` | one unknown/mismatched repair kind/hash/catalog or prohibited recovery action |
| `ALERT_AUTHORIZATION_ENUMERATION -> CRITICAL -> AUTHORIZATION_OR_ENUMERATION -> IR-05` | 20 uniform authorization misses in 5m from one ephemeral prefix bucket or one protected lookup bypass |
| `ALERT_COST_QUOTA -> CRITICAL -> COST_OR_QUOTA_RUNAWAY -> IR-10` | hard budget/max-cost/quota exceeded or reconciliation missing >15m |
| `ALERT_TELEMETRY_PRIVACY -> CRITICAL -> TELEMETRY_PRIVACY_LEAK -> IR-04` | one secret/PII/content/hash canary in telemetry/eval/Graphify/export |
| `ALERT_COMPLIANCE_SUPPRESSION -> CRITICAL -> COMPLIANCE_OR_SUPPRESSION_BREACH -> IR-12` | complaint/unsubscribe/hard-bounce signal, any post-signal eligibility, public unsubscribe dependency failure, or atomic suppression/sync failure |
| `ALERT_TELEMETRY_BLINDNESS -> CRITICAL -> TELEMETRY_OR_ALERT_BLINDNESS -> IR-11` | Critical exporter/alert gap >5m or both notification paths fail a canary |
| `ALERT_GMAIL_AMBIGUITY -> HIGH -> GMAIL_AMBIGUITY_STALE -> IR-02` | oldest ambiguity >60s opens immutable `HIGH`; notification projection escalates to `SEV1` after 15m without a second incident or row mutation |
| `ALERT_RECIPIENT_HASH_ENUMERATION -> CRITICAL -> RECIPIENT_HASH_ENUMERATION -> IR-04` | ten denied restricted-hash queries in 60s or 100 total queries/hour outside a registered batch purpose |

Unknown/mismatched severity/alert/trigger/runbook/version is rejected before notification and incident insert, increments only a bounded registry-error counter, forces the affected safety control false, and pages through the local fallback using the full `CRITICAL -> ALERT_TELEMETRY_BLINDNESS -> TELEMETRY_OR_ALERT_BLINDNESS -> IR-11` route. Alert replay uses `(catalog_version,alert_id,dedupe_window)` and cannot change routing. Clear/resolve is evidence-driven and never enables a control.

## Sales metrics, attribution, and alerts

The following analytical registry is normative for metric definitions, not a browser calculation or additional high-cardinality time series. MetricSnapshotService/BACKEND-06 derive it from immutable authoritative ID sets using a frozen cutoff, evidence transform and definition version. Every row retains numerator/denominator, status, cohort, agent strategy version, GlobalStrategyPackage and StrategyActivation in private evidence/report joins. Null means unavailable/insufficient; zero is recorded only with complete evidence. Release/configuration/activation IDs never become OTel labels.

| Metric key | Exact population and calculation |
| --- | --- |
| discovery.yield | accepted distinct LeadDiscoveryCandidate identities / raw observed candidate identities within the approved source/query snapshot |
| discovery.duplicate_rate | observations deterministically linked to an already represented business / all observed candidates; source conflicts remain separate unknowns |
| research.coverage | required dossier fields with accepted FACT evidence / required fields; ESTIMATE/UNKNOWN do not pass factual coverage |
| research.factual_accuracy | independently verified correct fact claims / reviewed factual claims, with label coverage/confidence; unreviewed claims never count correct |
| qualification.precision | independently verified true-qualified decisions / reviewed positive decisions, reported separately for PRELIMINARY and FINAL under the same offer filters |
| personalization.evidence_coverage | personalized factual claims with accepted supporting spans / all personalized factual claims; no-claim case has ZERO_DENOMINATOR |
| delivery.rate | unique contacted recipients with verified delivery evidence / unique provider-accepted contacted recipients; Gmail acceptance alone is not delivery and unavailable delivery stays unknown |
| bounce.rate | unique provider-accepted recipients with qualifying bounce observation / unique provider-accepted contacted recipients; show hard and soft categories separately |
| complaint.rate | unique contacted recipients with verified complaint / unique provider-accepted contacted recipients |
| reply.rate | unique contacted recipients with accepted inbound reply / unique provider-accepted contacted recipients |
| reply.positive_rate | recipients with accepted positive ReplyEvaluation / recipients with classified replies; display classification coverage and positive/contacted separately |
| commitment.rate | distinct qualified PURCHASE_PROPOSAL commitments / unique provider-accepted contacted recipients; CALL_NEXT_STEP is not purchase commitment |
| objection.category_count | one accepted objection occurrence per reply/proposal/canonical category key; count by the minimized closed category transform |
| objection.resolution_rate | objection occurrences with independently evidenced resolution / mature objection occurrences with known outcomes; show unknown/censored count |
| negotiation.outcome_rate | terminal proposal count for accepted/rejected/expired/exception/closed disposition / terminal proposals; active proposals remain separate |
| negotiation.discount_bps | exact server effective discount versus the selected accepted offer variant's undiscounted net price; report count/mean/p95 by complete decision population |
| negotiation.margin_bps | exact CommercialPolicyEngine contribution / authoritative net revenue times 10,000 under stored rounding; retain minimum/distribution and any floor violation |
| negotiation.scope_change_rate | presented proposals selecting an approved non-baseline scope variant / all presented proposals; unauthorized scope is a safety violation |
| booking.rate | distinct BookingIntents with positive CREATE confirmation / distinct qualified CALL_NEXT_STEP agreements; reschedule never adds a booking |
| booking.show_rate | verified attended calls / due confirmed calls not cancelled before their scheduled start; unknown attendance/censored calls are explicit and prevent complete-rate claims |
| cost.per_qualified_lead | reconciled allocated acquisition spend / distinct FINAL-qualified leads at the same frozen cutoff |
| cost.per_commitment | complete reconciled allocated experiment/cohort spend / distinct qualified PURCHASE_PROPOSAL commitments |
| cost.per_booking | complete reconciled allocated experiment/cohort spend / distinct confirmed BookingIntents; all failed/cancelled/reconciliation costs remain included |
| strategy.pre_post_delta | difference and uncertainty between comparable frozen pre/post activation metric populations using each action's original strategy/activation; list confounders and never claim causality from correlation |
| learning.promotion_rate | per-agent PROMOTE results passing deterministic promotion / all closed per-agent learning results; separately show proposal versus successful package promotion |
| learning.rollback_rate | applied compatible rollback activations / active/past activations eligible for the signed observation window; pending/failed requests remain separate |
| strategy.cross_campaign_transfer | comparable target-campaign post-boundary metric delta versus its frozen prior baseline and approved holdout, stratified by triggering/secondary/guardrail evidence; negative and missing results cannot be excluded |

Objection telemetry uses only the explicit enum transform in the registry; UNKNOWN is a minimized classification, not an invented objection. Denominators freeze before evaluation, mature windows are pre-registered, event retries/late evidence cannot inflate counts, and synthetic/recorded/owned-alias populations remain separate from real demand. Qualified call intent is distinct from purchase acceptance throughout.

Additional exact operational instruments join the instrument table above:

| Instrument | OTel instrument | UCUM unit | Aggregation / temporality | Allowed attributes only | Max series |
| --- | --- | --- | --- | --- | --- |
| alon_ai.booking.action.count | Counter | {action} | monotonic sum, cumulative | booking.action, operation.outcome, execution.mode | derived exact allowed tuple-domain product |
| alon_ai.booking.ambiguity.oldest_age | ObservableGauge | s | last value, instantaneous | booking.action | derived exact allowed tuple-domain product |
| alon_ai.booking.action.duration | Histogram | s | DURABLE_SECONDS, cumulative | booking.action, operation.outcome | derived exact allowed tuple-domain product |
| alon_ai.commercial.decision.count | Counter | {decision} | monotonic sum, cumulative | policy.allowed, execution.mode | derived exact allowed tuple-domain product |
| alon_ai.objection.outcome.count | Counter | {objection} | monotonic sum, cumulative | objection.category, objection.resolution, execution.mode | derived exact allowed tuple-domain product |
| alon_ai.checkpoint.decision.count | Counter | {checkpoint} | monotonic sum, cumulative | checkpoint.decision, execution.mode | derived exact allowed tuple-domain product |
| alon_ai.learning.result.count | Counter | {result} | monotonic sum, cumulative | agent.type, learning.result, execution.mode | derived exact allowed tuple-domain product |
| alon_ai.strategy.action.count | Counter | {activation} | monotonic sum, cumulative | strategy.action, operation.outcome, execution.mode | derived exact allowed tuple-domain product |

Only the unique committed record/outbox consumption increments counters; provider retries, restored events and duplicated callbacks do not. Booking ambiguity appears within the result/recovery transaction and alerts within 60 seconds, escalating investigation after 15 minutes without a blind retry. Any unauthorized booking, fabricated commitment, commercial floor breach, mid-cohort mutation, unknown serialized checkpoint/learning result or 1,000-ceiling breach is a zero-tolerance safety condition. Missing checkpoint cost/evidence closes admission; stale or incompatible activation blocks affected actions; stored monitored deterioration triggers automatic pause/checkpoint closure and boundary rollback.

Use the exact existing routes in OBS-05's sales-funnel incident table for commercial, booking, checkpoint/strategy and learning-privacy alerts. Add booking/calendar, checkpoint evidence and global strategy/transfer panels to the existing five dashboard destinations. A metric alert never grants send/booking authority, increases capacity, or mutates a running cohort.

## Ordered implementation tasks

<!-- roadmap-task id=OBS-02-T01 milestone=M8 depends_on=OBS-01-T01,OBS-01-T03 mode=parallel locks=telemetry-catalog -->
- [ ] **Implement exact metric/span registries —** Input: OBS-01 and every application boundary. Operation: define instruments/units/labels/series budgets and spans/links/sampling. Output: versioned telemetry package. Test evidence: registry/schema/cardinality/sampling tests. Failure behavior: reject unregistered signal/release.
<!-- roadmap-task id=OBS-02-T02 milestone=M8 depends_on=OBS-02-T01,BACKEND-02-T05,DB-06-T01,WF-05-T05,AGENT-10-T05,SEC-05-T04,OBS-03-T02,INFRA-04-T02 mode=parallel locks=telemetry-catalog -->
- [ ] **Instrument safety and service paths —** Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas. Operation: emit authoritative-record-derived counters/gauges and spans without replay duplication. Output: complete signals. Test evidence: golden count/latency/exemplar fixtures at each crash boundary. Failure behavior: applicable milestone blocked.
<!-- roadmap-task id=OBS-02-T03 milestone=M8 depends_on=OBS-02-T02 mode=parallel locks=telemetry-catalog -->
- [ ] **Build five dashboards and SLO calculations —** Input: low-card metrics plus authoritative projections. Operation: implement exact panels/queries/windows/burn rules and show data freshness. Output: one-operator operational views. Test evidence: empty/low-volume/stale/gap/timezone/currency fixtures. Failure behavior: display unknown and disable unsafe interpretation.
<!-- roadmap-task id=OBS-02-T04 milestone=M8 depends_on=OBS-02-T03 mode=serial locks=telemetry-catalog,live-environment -->
- [ ] **Implement alert routes/runbooks —** Input: thresholds, severity mapping and notification endpoints. Operation: dedupe/page/persist/ack/escalate/test with safe payload. Output: actionable alerts. Test evidence: fire every rule and disable each channel. Failure behavior: Critical local incident plus controls false when safety channel unavailable.
<!-- roadmap-task id=OBS-02-T05 milestone=M8 depends_on=OBS-02-T04 mode=serial locks=milestone-gate -->
- [ ] **Prove SLO and blind-spot gates —** Input: load/security/chaos/restore scenarios; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: validate measurements/targets and reconcile metrics to DB rows; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed M8 SLO baseline. Test evidence: injected gaps/replay/counter reset/sampling/cardinality. Failure behavior: no production-readiness claim/control enable.

## Test strategy

- **Registry `test_metric_names_types_units_labels_and_series_budgets_are_exact`.**
- **Vectors `test_metric_registry_bucket_unit_temporality_and_recording_vectors_are_exact`:** provider tokens/bytes/results, ambiguity age versus resolution, original currencies, resets and gauge disappearance.
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
