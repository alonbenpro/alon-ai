# Suppression, Budgets, Rate Limits, and Kill Controls

**Document ID:** SEC-05
**Status:** Planned M6 safety control plane; only foundation `OUTREACH_ENABLED=false` and minimal no-call guard exist today
**Milestone:** M6, M9 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `SEC-05-T01 -> SEC-05-T02 -> SEC-05-T03 -> SEC-05-T04 -> SEC-05-T05`; cross-document task Inputs `SEC-05-T01 <- DB-05-T02,ARCH-03-T01,DB-01-T05,SEC-04-T01; SEC-05-T02 <- DB-03-T03,DB-03-T04,DB-03-T01; SEC-05-T03 <- OBS-03-T02; SEC-05-T04 <- OBS-01-T03,BACKEND-04-T03,PRODUCT-03-T03; SEC-05-T05 <- SEC-04-T06,TEST-03-T06,OBS-05-T06`. Descriptive source authorities/resources (not whole-document completion dependencies): [DB-01 controls/budgets](../02-database/01-core-data-model.md), [DB-03 suppression/rate/send ledger](../02-database/03-leads-campaigns-and-messages.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [WF-05/06](../03-workflows/05-outreach-and-reply-workflow.md), [BACKEND-03](../06-backend/03-policy-engine.md), [BACKEND-04](../06-backend/04-send-gateway.md), [BACKEND-05](../06-backend/05-approval-and-command-handling.md), and SEC-04
**Outputs:** Fail-closed suppression, cost/call/rate/window budgets, independent test/product controls, deterministic kill/acknowledgement, and earned re-enable protocol
**Unlocks:** M6 test-alias pilot and M7 safety UI; later product eligibility remains SEC-04/M9-gated
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Global/business/recipient suppression, money/token/call/message budgets, mailbox rate leases, campaign windows/caps, and independent Gmail/calendar and scoped action controls are authoritative PostgreSQL facts rechecked under lock immediately before a provider attempt. An operator can always commit disable quickly; disable stops new admissions/dequeues/provider calls but never hides or blindly retries an in-flight/ambiguous Gmail outcome. No control or budget automatically increases or re-enables.

## Current repository state

`Settings.outreach_enabled` defaults false, validates static Gmail config if manually enabled, and the current unit-tested `SendGateway` avoids policy/provider calls when disabled. There are no `system_controls`, `suppression_entries`, budget/rate tables, product SendGateway, queue, control API/UI, authenticated operator, alerts, incident/repair path, or Gmail call. The foundation boolean is not either canonical versioned control and must not be presented as M6 safety evidence.

## Scope and non-goals

In scope: exact DB-01/03/05 rows and owners; `GLOBAL|BUSINESS|RECIPIENT` suppression; `TEST_INBOX_SENDING` and `PRODUCT_OUTREACH`; provider/workflow/experiment/campaign/mailbox/recipient budgets; PostgreSQL rate slots/leases; DBOS outer limits; emergency disable; acknowledgement/drain; bounce/complaint/cost/security kill triggers; stale/restore/startup defaults; and evidence-based re-enable.

Non-goals: a single master toggle, cache-authoritative suppression, optimistic UI enable, rate limits based only on provider quota or DBOS, wall-clock lease expiry granting retry, auto-unsuppress, auto-raise budget, auto-reenable, pausing as proof an external call stopped, or M1/M6 granting product authority.

## Exact planned implementation surfaces

Use only canonical `system_controls`, `budget_accounts`, `budget_reservations`, `suppression_entries`, `campaigns`, `campaign_members`, `outreach_messages`, `send_intents`, `send_rate_reservations`, `send_attempts`, `policy_decisions`, `cost_entries`, `incidents`, `repair_actions`, events, audit, idempotency and outbox. Owners remain exactly `ControlCommandService`, `BudgetService`, `SuppressionCommandService`/`SuppressionQueryService`, `CampaignCommandService`, application `SendGateway`, `SendRateReservationService`, `SendRecoveryService`, `ProviderCostReconciliationService`, `IncidentCommandService`, and `RecoveryCommandService`.

Create policy/config models `BudgetPolicyV1`, `RatePolicyV1`, `KillPolicyV1`, and projections/alerts; use the exact DB-01 effect/scoped-control and DB-03 trigger registries, with versioned schema fixtures; no generic bypass flag.

### Independent control contract

| Control | May be enabled only for | Mandatory evidence | Explicitly cannot do |
| --- | --- | --- | --- |
| `TEST_INBOX_SENDING` | exact operator-owned Gmail aliases in isolated M6 mode | passing M1, current M6 pilot manifest/owned-alias hashes, active exact mailbox, no blocker/ambiguity, security subset | enable product, admit a real recipient, create campaign/member/message/action authorization/intent/reservation/attempt |
| `PRODUCT_OUTREACH` | separately bounded M9 authority | current M1 and M6 gate IDs/hashes, SEC-01/03/04/06 and OBS evidence, counsel-approved policy/cohort, no incident/ambiguity, explicit reason | satisfy final `SEND`, override suppression/action authorization/budget/rate/jurisdiction, create work, auto-renew |

Both rows exist from seed/restore as `false`, versioned and changed only by `ControlCommandService`. `DisableSystemControl` is always available to an active authenticated operator and to exactly DB-01's six registered internal fail-closed actor IDs; system actors may only disable, carry their real ID plus canonical reason/evidence, and never impersonate the operator. Both paths commit row/event/audit/idempotent result/outbox before worker notification; the operator path needs no slow typed phrase. `system.outreach_disabled.v1` is only the product-wide canonical disable event; test-control changes use safe audit/control projection and must not invent an event alias. `EnableSystemControl` is operator-only; product enable emits `system.outreach_enabled.v1` only after exact gates. Enabling either row grants no downstream authority.

Processes additionally require deployment configuration to permit the relevant mode. Missing/stale configuration, database/readiness loss, unknown control row/version, restored database, secret/mailbox mismatch, telemetry blindness for safety signals, clock anomaly, policy expiry, or runtime/product disagreement is treated as false. Configuration may veto; it cannot turn a false DB row true.

### Suppression creation, matching, and removal

Canonical scopes and unique active indexes remain DB-03. Operator RECIPIENT input is safe opaque `recipient_source_ref_id=campaign_member_id`; `SuppressionCommandService` resolves the restricted SHA-256 address hash internally and allocates one random UUIDv4 `recipient_target_ref_id` for the new row. The source ref is create-only; list/response/event/replay use the stored target ref, which has no source-member FK and survives removal/permitted purge. Neither raw address, hash, address ciphertext nor lookup digest enters HTTP/event/report/export. Manual create locks target plus affected lead/message/intent authority, inserts active version 1 with `source=OPERATOR`/actor `OPERATOR`, emits the hash-free `suppression.created.v1`, transitions matching nonarchived leads through `lead.suppressed.v1`, invalidates final-SEND facts, and cancels only provably unsent work through canonical transitions.

Observed durable sources are the DB-03 enum GMAIL_UNSUBSCRIBE/GMAIL_HARD_BOUNCE/GMAIL_COMPLAINT/GMAIL_SOFT_BOUNCE_LIMIT/PUBLIC_UNSUBSCRIBE/QUALIFIED_NO_FUTURE_CONTACT/LEGAL_PROHIBITION, with exact DurableSuppressionTriggerV1 evidence. RecipientSignalSuppressionService coordinates but does not become a second suppression writer. Every inbound reply first atomically stores observation/full reply, stops cold sequence, invalidates old generation/authority, closes provably uncalled cold intents, writes events/audit/outbox and advances cursor. Positive replies/questions/objections can then receive a new bounded response after accepted evaluation/commercial decision. A clear rejection ends persuasion; ordinary reply/offer decline alone does not permanently suppress. Ambiguous or negative sentiment pauses into exception. When the durable predicate holds, the same transaction invokes SuppressionCommandService.record_observed_signal, creates/idempotently returns the active entry and stored target ref, suppresses affected leads/pre-call messages and invalidates all later action authority. A crash rolls back the entire cursor/result/stop bundle; failure independently sets product controls false, pages ALERT_COMPLIANCE_SUPPRESSION and denies acknowledgement until repair.

The public unsubscribe pair is the sole public-API exception and remains disabled/unpublished before M9. Its GET is scanner-safe/read-only; its POST requires exact public Origin/fetch/CSRF/JSON confirmation, token-derived replay, independent WAF/request/rate limits and recipient-opaque errors. Future Task 7 infrastructure and security/load suites must prove the exact listed private plus two public route partition, pre-M9 absence, token-abuse bounds, no sensitive logs, dependency fail-close and recovery before real-recipient release.

The deterministic SHA-256 recipient lookup remains a documented v1 residual risk. It is pseudonymous, equality-revealing and offline enumerable, never anonymous or non-reversible. Compensating controls are least PostgreSQL column privilege, purpose-bound/rate-limited queries, safe access audit and `ALERT_RECIPIENT_HASH_ENUMERATION`, no API/log/event/report/export/fixture exposure, encrypted volume/WAL/snapshot/backups, counsel-approved retention/holds, and IR-12/IR-04 response.

Suppression lookup bypasses caches and reads locked PostgreSQL rows in final-SEND steps 2/7. Precedence is global, business, recipient; any match denies. If intent is queued and unattempted, the exact BACKEND-04 step-8 bundle commits denied `SEND`, message `SUPPRESSED`, one-way intent cancellation, `send.suppressed.v1`, budget/queue release, and zero rate reservation/attempt/credential/provider call. Once a call may have begun, suppression blocks future attempts but preserves/reconciles the existing outcome.

Deactivation requires `If-Match`, active expected state, authenticated reason, all applicable effect controls false, no matching nonterminal message/intent/attempt, no ambiguity/reconciliation or blocker incident, and locks all affected rows. It emits `suppression.deactivated.v1`; it never requalifies a lead, reactivates a campaign, recreates an action authorization/intent, or enables. Consent withdrawal/opt-out/complaint and unresolved legal/identity conflicts cannot be deactivated without the SEC-04 counsel/evidence path.

### Budget, rate, time, and reservation hierarchy

The most restrictive applicable bound wins. All amounts are integer minor units and original ISO currency; no floating admission math.

1. Provider-call budget: per capability/provider/config max calls, input/output tokens/bytes/results, per-call cost, timeout and concurrent calls; reserve before each registered capability call.
2. Workflow/run budget: max steps/attempts/duration/provider calls and original-currency spend in the frozen workflow snapshot; a retry/new run never silently inherits extra budget.
3. Experiment budget: DB-01 `budget_accounts` by exact experiment/scope/currency and `budget_reservations`; every paid call reserves under a serializable transaction and reconciles to one DB-05 `cost_entries` row.
4. Campaign/send budget: immutable stage/campaign daily/total caps, exact `100/200/300/400` incremental and `100/300/600/1,000` cumulative maxima, unique cross-stage recipient identity, signed prior `CONTINUE`, send/reply half-open windows, retry cap/deadline, and Gmail provider/account terms. Final SEND uses the minimum signed stage, campaign, experiment, provider, account, legal-policy, reputation, and live-control ceiling; any missing/stale/conflicting input denies.
5. Mailbox rate: DB-03 unique `(mailbox_id,rate_policy_version,window_start,slot_number)` plus one active mailbox lease. DBOS is an outer queue/start limiter; PostgreSQL is the final concurrency authority.
6. Product/deployment budget: hard monthly provider/monitoring/legal/hosting caps and operator review thresholds; a currency without a configured account/FX reporting policy denies.

Reservation states remain `RESERVED|RELEASED|RECONCILED|EXPIRED`; rate states remain `RESERVED|CONSUMED|RELEASED|EXPIRED`. A paid call cannot start without enough reservation. Result capture reconciles exact actual cost; an overage cannot be hidden by clamping. Consumed Gmail rate lease is released only with terminal provider evidence or marked expired only after conclusive no-call/no-send evidence; passage of time alone cannot authorize another call. Unknown provider cost keeps the budget held, opens reconciliation, and may kill new calls at the conservative ceiling.

### Kill triggers, response, and proof

| Trigger | Automatic action | Operator/action evidence | Recovery gate |
| --- | --- | --- | --- |
| unauthorized, duplicate, suppressed, wrong-mailbox or post-disable call | commit both controls false, stop dequeues, Critical incident | exact intent/attempt/control/provider chain | reconcile all attempts; root cause/security/counsel review; new gate |
| any complaint/abuse signal or unsubscribe breach | product control false; recipient suppression path; incident | Gmail observation/operator/provider evidence | remediation and SEC-04 review; smaller/equal cohort |
| credential/session/provider compromise | affected capability/mailbox off; both controls false for Gmail | revoke/rotation evidence | SEC-02/03 reauth/reauthorize and consistency proof |
| budget overage, unpriced call, one agent max-cost breach, reservation mismatch | stop affected provider/stage; product control false if send/reputation involved | reservation/cost/invoice/FX rows | reconcile and approve new config; never raise cap in incident |
| DB/runtime/snapshot/hash/restore invariant failure | stop writers/workers/dequeues; controls false | invariant/restore report | typed repair or isolated restore; all unresolved sends reconciled |
| policy/legal/Google-policy expiry/change or unknown jurisdiction | product control false | source/policy/legal review IDs | new current SEC-04 policy and reaction authorization |
| telemetry/alert blind spot for send safety beyond five minutes | product control false; test control false during M6 | local DB health/canary/alert evidence | telemetry proof plus authoritative state comparison |

Disable acceptance target: authenticated command commit p95 <=2 seconds on a healthy DB; worker/dequeue signal p95 <=5 seconds; zero new provider calls whose pre-call transaction begins after the committed disabled version. These are M8 SLOs, not current claims. Calls already possibly begun enter ambiguity. Signal timeout leaves disable committed and opens incident; UI must say acknowledgement pending.

Re-enable is never automatic. Operator proves trigger closed, exact control version, no pending/ambiguous attempts, current gates/policy/security/telemetry/backup/evaluation, all costs reconciled, and a bounded cohort/cap no larger than prior authority unless a new earned-authority review says otherwise. A successful enable creates no work.


### Calendar, conversation, checkpoint and strategy controls

DB-01 adds CALENDAR_WRITES=false and TEST_CALENDAR_WRITES=false independent of Gmail controls, plus action_controls for GLOBAL/CAMPAIGN/MAILBOX/PROVIDER/CONVERSATION/CALENDAR with positive generations and default-deny missing rows. M6 owned-calendar authority cannot enable product calendar or Gmail. Every action requires its environment mode and all applicable current scoped controls.

ActionAuthorizationService pins control/checkpoint generation in immutable ActionAuthorityScopeV1; gateways re-read immediately before attempts. Disable increments generation and prevents subsequent calls after acknowledged boundary, while retaining possibly-called attempts for reconciliation. Reply/cold stop, terminal rejection, negative sentiment, offer expiry, strategy rollback, calendar conflict and checkpoint close invalidate obsolete authority.

Conversation policies store immutable max_rounds, max_messages, minimum_contact_interval, daily/total contact windows and conversation_expiry. All counters reserve under conversation/member locks; concurrent writer tasks cannot exceed limits. An unknown counter/window fails closed. No model, learning promotion, timer or exception resolution can raise a limit, restart persuasion after decline, invent STATED budget or cross a commercial floor.

Calendar writes use calendar-side-effects, exact account/event/ETag, confirmed slot/attendee/notification hash and one unresolved-action lease per calendar. Timeout/absence/conflict retains lease and AMBIGUOUS/RECONCILING; wall-clock expiry never permits duplicate invitations or an unchecked compensating cancel.

Checkpoint closure stops admission before freezing evidence. Cohort final-slot admission, close, strategy promotion/activation/rollback and action dequeue use a shared documented lock order (controls -> campaign/cohort -> conversation/recipient -> action/attempt -> rate/budget) and compare-and-swap generations; implementations must use that order consistently. A promoted global package cannot change an active cohort. Stored deterioration triggers pause affected future actions, close the checkpoint and boundary-only compatible rollback; historical action attributions remain immutable.

Disable acknowledgement is fenced against provider-call entry: the same per-provider call-entry coordinator first closes admission/increments generation, then waits until each registered entry section has either begun its recorded in-flight network attempt or produced conclusive no-call evidence. Only then may disable acknowledge; a stale reserved task cannot begin later. No database transaction spans the network call. Lost worker/coordinator proof leaves disable unacknowledged, closes process/egress capability and requires recovery; it never assumes a possibly-called attempt stopped. Test the exact scheduler race between final check and network entry for Gmail and calendar.

Required security fixtures cover late reply/negative sentiment versus queued send, control disable versus pre-write, last cohort slot, simultaneous checkpoint close/strategy activation/new campaign start, rollback during negotiation/booking, and revoked calendar credential. Every loser must deny with zero new provider calls and retained safe reason/evidence. All default-off controls and scoped generations are restored safely before readiness.

## Ordered implementation tasks

<!-- roadmap-task id=SEC-05-T01 milestone=M6 depends_on=DB-05-T02,ARCH-03-T01,DB-01-T05,SEC-04-T01 mode=serial locks=security-runtime -->
- [ ] **Seed and implement independent controls —** Input: the DB-01 M2 separated default-off control contract plus canonical DB-05 rows, ARCH-03 events, and SEC-04 signed isolated-test/prohibited-recipient control gate. Operation: seed false, implement authenticated versioned enable/disable and post-commit runtime signal. Output: two auditable controls. Test evidence: restore/startup/stale/concurrent/signal-failure matrix. Failure behavior: false or committed-disable/ack-pending.
<!-- roadmap-task id=SEC-05-T02 milestone=M6 depends_on=SEC-05-T01,DB-03-T03,DB-03-T04,DB-03-T01 mode=serial locks=security-runtime -->
- [ ] **Implement suppression under last-mile locks —** Input: canonical safe source ref/target/version/reason and send authority rows. Operation: create/deactivate through sole owner; persist immutable RECIPIENT target ref; bypass cache; commit terminal no-call bundle on match. Output: implemented versioned RecipientSignalSuppressionService sole-writer interface with unconditional suppression precedence and purge-stable projection. Test evidence: global/business/recipient create/deactivate/race, source-purge/list/replay stability and exact zero-call counts. Failure behavior: active/unknown suppression denies.
<!-- roadmap-task id=SEC-05-T03 milestone=M6 depends_on=SEC-05-T02,OBS-03-T02 mode=serial locks=security-runtime -->
- [ ] **Implement hierarchical reservations and rates —** Input: provider/run/experiment/campaign/mailbox policies, and OBS-03 complete reservation/reconciliation cost chain. Operation: reserve serially before paid/call work, consume unique Gmail slot/lease, capture and reconcile actual cost. Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence. Test evidence: concurrency/replay/expiry/unknown-cost/overage. Failure behavior: held reservation and no new call.
<!-- roadmap-task id=SEC-05-T04 milestone=M6 depends_on=SEC-05-T03,OBS-01-T03,BACKEND-04-T03,PRODUCT-03-T03 mode=serial locks=security-runtime -->
- [ ] **Wire deterministic kill triggers and alerts —** Input: security/compliance/send/cost/recovery/telemetry signals, and PRODUCT-03 versioned stop-control interface; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests. Operation: commit control false, stop dequeue, open incident, notify after truth commit; implement and verify this path with Gmail network denied here; later live acceptance must consume full pilot-entry authorization. Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement. Test evidence: inject each trigger and DB/signal failure. Failure behavior: disable stays committed and recovery remains blocked.
<!-- roadmap-task id=SEC-05-T05 milestone=M9 depends_on=SEC-05-T04,SEC-04-T06,TEST-03-T06,OBS-05-T06 mode=serial locks=security-runtime,milestone-gate -->
- [ ] **Prove earned re-enable —** Input: closed incident/current gate/policy/eval/restore/cohort evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: execute exact enable command and assert no downstream row/call creation; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: eligibility only plus signed expected-version control-enable evidence, without creating downstream rows or provider calls. Test evidence: each missing/stale condition, larger-cap request, and replay. Failure behavior: false.

## Test strategy

- **Control `test_two_controls_are_independent_default_false_and_enable_creates_no_work`.**
- **Kill `test_disable_commit_precedes_signal_and_no_post_commit_gateway_transaction_calls_provider`.**
- **Suppression `test_locked_global_business_recipient_match_commits_exact_no_attempt_no_call_bundle`.**
- **Observed suppression `test_every_reply_commits_cold_stop_and_only_durable_triggers_commit_suppression_or_force_product_off`:** reply/cold-stop/positive-response and unsubscribe/bounce/complaint/soft-limit/public-token crash races prove no stale next action.
- **Public boundary `test_public_unsubscribe_is_m9_gated_scanner_safe_rate_bounded_and_fail_closed`:** exact private/two-public route partition, pre-M9 absence, public WAF/CSRF/token-abuse/redaction and dependency-kill/recovery fixtures.
- **Target reference `test_recipient_suppression_projection_survives_member_purge_without_hash_reconstruction`:** stored opaque target ref byte-matches create/list/event/replay before and after allowed source cleanup; HTTP schemas contain no recipient hash/ciphertext/digest.
- **Hash privacy `test_recipient_hash_is_pseudonymous_restricted_and_absent_from_every_external_surface`:** offline-enumeration/query-rate fixtures trigger the closed alert/incident path; any claim of anonymity or non-reversibility fails the scan.
- **Removal `test_deactivate_requires_controls_off_fresh_version_and_no_inflight_or_ambiguity`.**
- **Budget `test_concurrent_provider_work_cannot_exceed_original_currency_account_or_per_call_cap`.**
- **Rate `test_one_mailbox_lease_slot_wins_and_elapsed_time_alone_never_permits_retry`.**
- **Authority `test_m1_m6_control_action authorization_and_budget_cannot_override_missing_sec04_recipient_evidence`.**
- **Restore `test_restore_and_unknown_control_policy_telemetry_state_force_false`.**

## Security, privacy, compliance, idempotency, observability, and cost

Controls/suppressions/budgets are security authority and require session, CSRF, expected versions, idempotency, safe reasons and immutable audit. Metrics use control/scope/state/reason enums only—never recipient hash, business ID, mailbox, campaign, or session as labels. Monetary truth remains original currency; ILS is reporting evidence under OBS-03, never admission substitution. Active suppression and unresolved/incident holds follow SEC-06.

## Failure, rollback, and operator recovery

Any impossible row/lease/reservation/control sequence, failed disable acknowledgement, suppressed/duplicate/unauthorized call, or unknown cost is treated as unsafe: commit controls false if possible, halt at process/queue/provider boundary, reconcile, and open incident. Roll back code/config without deleting rows. Recover with canonical commands and provider/DB evidence; direct SQL, expired-lease guessing, blind retry, cap increase, suppression deletion, or automatic re-enable is forbidden.

## Acceptance and retained evidence

- [ ] Two independent controls default/restore false and their enable grants no downstream authority.
- [ ] Suppression is locked, uncached, unconditional and produces exact no-call behavior at the last mile.
- [ ] Every paid/reputation-bearing action is bounded by reservations, caps, windows and final PostgreSQL rate authority.
- [ ] Every kill trigger has commit/signal/alert/evidence/recovery, and no ambiguous call is hidden or retried.
- [ ] Re-enable requires current evidence and is never automatic.

Retain seeded/control versions, gate/control command fixtures, suppression race/no-call traces, budget/rate reservation/cost reconciliation, kill latency and post-disable call counts, signal-ack evidence, incidents/repairs, restore false-state proof, and re-enable denials/action authorization.

## Dependencies and next deliverable

SEC-05 composes BACKEND-03/04/05 with [SEC-04](04-outreach-compliance.md), OBS-02/03/05, and recovery. Passing its M6 subset permits only owned test aliases. M9 product eligibility additionally requires current SEC-04 legal/recipient evidence and separate bounded authority.
