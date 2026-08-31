# Test-Inbox Pilot and M6 Promotion

**Document ID:** LAUNCH-01
**Status:** Planned M6 launch gate; no Gmail adapter, owned-alias pilot, product workflow, M6 evidence, or send exists today
**Milestone:** M6
**Owner:** Solo operator
**Prerequisites:** Passing M0-M5; [DBOS/Temporal runtime decision](../03-workflows/00-dbos-selection-and-temporal-fallback.md); [M6 outreach workflow](../03-workflows/05-outreach-and-reply-workflow.md); [Gmail side-effect tests](../10-testing/04-gmail-side-effect-tests.md); deterministic policy, approval, suppression, budgets, Gmail OAuth/history, observability, and operator controls
**Outputs:** Signed immutable M6 gate record, capped owned-alias transcript, reconciliation/suppression/control evidence, rollback result, and explicit pass or block decision
**Unlocks:** [LAUNCH-02 controlled internal launch](02-controlled-internal-launch.md) and technical eligibility for later product-outreach review; never real-recipient authority
**Risk:** Critical
**Complexity:** L

## Outcome and timing

M6 proves the product-shaped Gmail loop only against operator-controlled addresses and test resources. The pilot is allowed to establish technical safety, not recipient consent, legal authority, public-ingress readiness, production reliability, or demand. `TEST_INBOX_SENDING` may be true only inside the signed envelope; `PRODUCT_OUTREACH` stays false throughout.

The phase is complete only when the exact ten-ID, two-lane catalog below runs without omission or substitution: its nine live IDs make exactly 13 Gmail provider calls that produce 13 unique `SENT` messages, `M6-L08` and the `M6-L09` losing contender remain exact zero-call live outcomes, and the one recorded offline ID produces canonical conclusive-rejection/`FAILED` evidence with zero live call, delivery, Sent reconciliation or retry. Every expected reply/signal must be linked and suppressive, all kill/restart rows must pass, and both controls must return to false. Missing or ambiguous evidence is a block, not an invitation to run more live messages.

## Current repository state

The repository currently has foundation health/CI/Compose, typed Gmail/policy gateway contracts, and outreach disabled by default. It has no DBOS workflow, Temporal adapter, 46-table product schema, Gmail OAuth/API adapter, history cursor, test mailbox, suppression transaction, 66-operation product API, operator UI, M6 runner, or live-provider evidence. Foundation tests and the historical container CI run do not satisfy any M6 row.

## Scope and non-goals

In scope: one isolated Google project, one dedicated mailbox, one signed allowlist of four to five operator-controlled recipient aliases so `M6-L01` can use four distinct scenario/alias pairs, one signed recorded conclusive-rejection fixture, exact runtime/release/config bindings, manual approval for each live test message, bounded sends, crash/restart/ambiguity/reconciliation/history/reply/suppression/control/concurrent-admission evidence, cleanup, credential revocation, and a signed gate decision.

Non-goals: prospects or any address not controlled by the operator, legal/consent evidence, product outreach, public unsubscribe publication, volume testing, automated follow-up, model-selected recipients, direct Gmail access by an agent/workflow, a product schema in M1, or promotion from test evidence into real-recipient authority.

## Exact planned implementation surfaces

This gate creates no new product table, endpoint, event, agent artifact, provider capability, service, or command ID. It executes the existing `T7-GMAIL-OFFLINE` and `T7-GMAIL-LIVE` rows, canonical 46-table owners, 14-step `SendGateway`, 14 final-SEND compliance/signal denials, six provider capability families, and M1 `K0..K8`/eight-disqualifier contracts. The signed gate record is immutable release evidence, not a product artifact or authority row.

### Entry manifest and prerequisites

The signed entry record binds literal phase `TEST_INBOX_PILOT`, source commit/tree with `dirty=false`, `ReleaseManifestV1`, selected runtime/version, database system/schema ID, all 46-table/API/policy/provider/event/metric/incident manifest hashes, active `PromotionManifestV1` references, exact model/prompt/tool/provider versions, Google project/mailbox/account hash, credential generation references without values, owned-alias allowlist hash, the exact ordered ten-ID catalog and scenario/alias allocation below, send/cost/time caps, M1/M2/M3/M4/M5 evidence IDs/hashes/freshness, planned `T7-GMAIL-LIVE` command/fixture/`GMAIL_OWNED_ALIAS` and `T7-GMAIL-OFFLINE` command/fixture/`GMAIL_RECORDED` hashes, operator approval, start/expiry UTC, and both expected control versions.

| Entry prerequisite | Required immutable evidence | Failure behavior |
| --- | --- | --- |
| M0-M5 | signed brief/decision rules, M2 46-table/restore set equality, promoted M3 configs, one accepted M4 synthetic bundle, M5 provenance/dedupe/precision gate | no credential construction; pilot blocked |
| M1 runtime | every `K0..K8` row and all eight criteria pass; after any canonical DBOS disqualifier, a completed Temporal migration plus the same application-level matrix | DBOS is permanently ineligible after one disqualifier; no waiver or rerun erases it |
| M6 implementation | exact Gmail OAuth/history/result unions, policy/approval/suppression/budget/rate/control owners and `T7-GMAIL-OFFLINE|GMAIL_RECORDED` exit `0`, including exact `M6-O01` provider-result evidence | both controls false; no live lane |
| Test identity | isolated Google project, one dedicated mailbox, four-to-five owned aliases, exact mailbox/account binding and separate credential/schema generations | wrong/unknown target exits before credential access |
| Visibility and stop | authoritative DB queries, correlated audit/provider/cost evidence, local disable path and alert delivery visible before the first call | both controls false; no call |

### Execution envelope and operator steps

| Bound | Exact pilot value |
| --- | --- |
| Recipients | four to five operator-controlled aliases required by the frozen allocation; zero real recipients |
| Mailbox/project | exactly one dedicated mailbox in one isolated Google project |
| Send cap | live lane: exactly 13 Gmail provider calls and 13 unique delivered messages, plus the two zero-call live outcomes in `M6-L08` and the `M6-L09` loser; recorded lane: exactly one recorded invocation/result and zero live calls/deliveries; never more than 5 live messages in any rolling 24 hours or 20 live messages total |
| Per-recipient cap | at most one live message per approved scenario/alias pair; no automated follow-up |
| Concurrency | one in-flight Gmail provider call per mailbox; only `M6-L09` starts two simultaneous admission contenders, and PostgreSQL must choose one winner before the single call while the loser stays call-free |
| Controls/routes | `TEST_INBOX_SENDING=true` only for the live window; `PRODUCT_OUTREACH=false` always; public unsubscribe GET/POST absent and unpublished |
| Approval | one fresh persisted operator approval per live message version before `RecordSendIntent`; no batch approval; the recorded offline rejection fixture grants no live authority |
| Provider behavior | `SendGateway` is the sole Gmail path; any possible acceptance is `AMBIGUOUS`/`RECONCILING` until evidence resolves it; no blind retry |

### Frozen M6 live and recorded scenario catalog

The signed entry freezes this exact ten-ID set and comparison order: `M6-L01` through `M6-L09`, then `M6-O01`. `M6-L01..M6-L09` map only to command `T7-GMAIL-LIVE` and profile `GMAIL_OWNED_ALIAS`; `M6-O01` maps only to command `T7-GMAIL-OFFLINE` and profile `GMAIL_RECORDED`. Operationally the operator closes the offline prerequisite, including `M6-O01`, before opening the live window; that prerequisite sequence does not change the signed catalog comparison order. Every live call-bearing row uses a fresh manually approved message and a distinct approved scenario/alias pair; `M6-L01` allocates four distinct owned aliases. The two suppressive signal rows use different owned aliases, and no alias is used after its suppression commits.

| Lane / profile | Scenario ID | Command deliveries / contenders | Provider effects | Required terminal evidence |
| --- | --- | ---: | ---: | --- |
| live / `GMAIL_OWNED_ALIAS` | `M6-L01_DIRECT_ACCEPTED` | 4 | 4 live calls / 4 unique `SENT` | four distinct approved scenario/alias pairs each produce one unique `SENT` outcome |
| live / `GMAIL_OWNED_ALIAS` | `M6-L02_DUPLICATE_COMMAND_REPLAY` | 2 | 1 live call / 1 unique `SENT` | duplicate command delivery returns the same result; exactly one provider call and one unique `SENT` message |
| live / `GMAIL_OWNED_ALIAS` | `M6-L03_ACCEPTED_RESULT_PERSIST_CRASH` | 2 | 2 live calls / 2 unique `SENT` | each run is killed after provider acceptance and before result persistence; both reconcile to `SENT` with zero duplicate |
| live / `GMAIL_OWNED_ALIAS` | `M6-L04_TIMEOUT_UNKNOWN_RECONCILE` | 2 | 2 live calls / 2 unique `SENT` | each injected post-call timeout/unknown result reaches bounded reconciled `SENT` truth with zero blind retry or duplicate |
| live / `GMAIL_OWNED_ALIAS` | `M6-L05_HISTORY_CURSOR_RESTART` | 1 | 1 live call / 1 unique `SENT` | cursor/page restart yields one observation, one terminal `SENT` truth and zero duplicate |
| live / `GMAIL_OWNED_ALIAS` | `M6-L06_REPLY_SUPPRESSION` | 1 | 1 live call / 1 unique `SENT` | owned-alias reply atomically records reply evidence, creates suppression and proves no next `SEND` |
| live / `GMAIL_OWNED_ALIAS` | `M6-L07_UNSUBSCRIBE_REPLY_SUPPRESSION` | 1 | 1 live call / 1 unique `SENT` | deterministic supported unsubscribe reply phrase creates canonical suppression and proves no next `SEND`; this is mailbox reply handling, never the M9 public route |
| live / `GMAIL_OWNED_ALIAS` | `M6-L08_PRECALL_CONTROL_KILL` | 1 | 0 live calls / 0 deliveries | control closes after admission and before the provider call; terminal denied/cancelled evidence and exact zero provider calls/messages |
| live / `GMAIL_OWNED_ALIAS` | `M6-L09_CONCURRENT_ADMISSION` | 2 simultaneous contenders | 1 live winner call / 1 unique `SENT`; loser 0 calls / 0 deliveries | for the same frozen scenario/message/lease boundary, exactly one PostgreSQL winner atomically commits final admission, consumed rate reservation and attempt; the loser persists canonical `RATE_LIMITED` concurrency/admission denial and audit evidence, cannot retry into another send, and replay after the winner's DBOS `K8` concurrent-rate/window-replacement restart boundary returns stored truth with no second call |
| recorded / `GMAIL_RECORDED` | `M6-O01_CONCLUSIVE_PROVIDER_REJECTION` | 1 fixture execution | 1 recorded provider invocation/result; 0 live calls / 0 deliveries | one exact non-ambiguous conclusive provider-rejection fixture traverses `SendGateway` -> `GmailProvider`, then `GmailResultCaptureService`, captures `CONCLUSIVE_REJECTION`, reaches canonical attempt `FAILED` and message `FAILED_PERMANENT`, performs zero Sent reconciliation and zero retry, and never substitutes a local policy/pre-call denial or risky live Gmail error |
| **Exact live total** | **9 IDs** | **16 deliveries/contenders** | **13 live calls / 13 unique `SENT`** | **`M6-L08` and the `M6-L09` loser are the two exact zero-call live outcomes** |
| **Exact recorded total** | **1 ID** | **1 fixture execution** | **1 recorded invocation/result; 0 live calls / 0 deliveries** | **terminal `FAILED`; zero Sent reconciliation, retry or `SENT`** |

No row may be skipped, replaced, renamed, repeated to erase a failure, or excluded after execution. The signed validator proves exact ten-ID order/set equality and disjoint lane equality to both command/profile pairs, as well as exact provider-spy, terminal-state, event, call, delivery, denial and audit counts. Provider unavailability, missing credit/authentication, unavailable failure injection or recorded fixture, an omitted ID, wrong order, wrong command/profile, or any per-row/lane/total count mismatch is `BLOCKED`/unavailable and cannot pass. Offline scenarios remain necessary but cannot substitute a live row, and the live lane cannot substitute `M6-O01`.

The operator verifies the signed target and evidence directory, proves both controls false, and first executes the signed `M6-O01` recorded fixture with network denied. Only after its exact failure evidence passes does the operator load the isolated credential reference and schedule the 13 live calls across at least three cap-safe windows: calls 1-5, calls 6-10, then calls 11-13, with the rolling-24-hour guard authoritative at every admission. The operator enables only `TEST_INBOX_SENDING` at the expected version, approves one exact live message, runs the next frozen live row, reconciles it to required terminal evidence before advancing, checks reply/suppression/history/cost/audit truth, and immediately disables the test control on any mismatch. `M6-L08_PRECALL_CONTROL_KILL` consumes no send capacity. `M6-L09_CONCURRENT_ADMISSION` hard-restarts after the winning admission/attempt commit but before workflow acknowledgement and replays both simultaneous contenders at the upstream `K8` rate/window-replacement boundary; only the stored winner may proceed to one call and the loser must remain denied. After the last row, the operator reconciles every attempt, disables the test control, revokes or parks the credential generation under policy, retains cleanup evidence, and signs pass/block. No row is a follow-up.

| Decision point | Exact rule |
| --- | --- |
| Success | exact ten-ID catalog set/order and disjoint two-lane mapping equality; live lane exact 13 provider calls/13 unique `SENT` messages plus the two zero-call outcomes; recorded lane exact one invocation/result, terminal `FAILED`, zero live call/delivery/Sent reconciliation/retry; every required outcome and no-skip rule satisfied; zero wrong-target, duplicate, blind-retry, suppression, budget, rate, post-disable, audit, history-cursor, or unresolved-ambiguity failures; every required M6 row exit `0`; both controls false after cleanup |
| Immediate abort | any identity/target/control/version drift; possible unrecorded call; duplicate; unresolved ambiguity outside the bounded reconciliation row; suppression/reply/cursor/cost/audit mismatch; credential leak; telemetry blindness; cap breach; or any M1 disqualifier |
| Rollback/demotion | commit both controls false, stop dequeues, preserve consumed leases/evidence, reconcile all possible calls, revoke affected credentials, open the canonical incident, and return to the failed M1/M6 gate |
| Re-entry | new signed entry record after the incident is resolved, exact fix/release/config/eval evidence is current, all affected offline/recovery rows pass, and caps are no larger than before |
| Downstream unlock | M6 technical gate only; LAUNCH-02 may begin when its independent M7/M8 prerequisites pass |

## Ordered implementation tasks

- [ ] **Freeze the pilot entry and target —** Input: current M0-M5 gates, runtime decision, release/config/eval hashes, isolated project/mailbox, owned aliases and the exact ten-ID/two-lane catalog/allocation. Operation: verify every entry row, catalog/lane set and order, per-lane counts, upstream `K8`/gateway/result bindings and cap-safe windows, then sign the immutable envelope before credential access. Output: one bounded entry record. Test evidence: stale/missing/cross-project/real-address/catalog/lane/cap/control/version negatives. Failure behavior: both controls false; no credential construction.
- [ ] **Close offline Gmail and authority evidence —** Input: exact fixtures and `T7-GMAIL-OFFLINE|GMAIL_RECORDED`. Operation: prove OAuth saga, 14-step gateway, 14 denials, reconciliation, suppression, history, budgets and call graph with network denied, including `M6-O01` as one recorded conclusive provider rejection through `GmailProvider`, `GmailResultCaptureService` and `SendGateway`. Output: complete offline prerequisite bundle with canonical `FAILED` evidence, zero Sent reconciliation/retry and zero live effect. Test evidence: exact recorded provider invocation/result and terminal/event/provider-spy counts; a local policy/pre-call denial cannot satisfy the row. Failure behavior: live lane unavailable.
- [ ] **Execute the exact live catalog one message at a time —** Input: signed nine-live-ID entry, fresh approval, required injection and remaining caps. Operation: run `M6-L01` through `M6-L09` in order solely through `SendGateway`, reconcile the required terminal truth before the next admission, preserve both zero-call outcomes, and replay the `M6-L09` contenders across the upstream DBOS `K8` restart boundary without another call. Output: exact 13-call/13-delivery transcript plus pre-call and concurrent-loser denials and authoritative DB/event/cost comparison. Test evidence: scenario set/order equality, each row's terminal outcome, duplicate replay, accepted-result crash, timeout/unknown reconciliation, cursor restart, atomic concurrent winner/loser, stored-denial replay and rolling-window admission. Failure behavior: abort, controls false and reconcile; omission/unavailable injection/count mismatch is blocked, never pass.
- [ ] **Exercise signals and operator stop —** Input: owned replies/unsubscribe/bounce fixtures and control commands. Operation: prove atomic suppression/history/cursor behavior and zero calls after committed disable/cancel. Output: stop/suppression evidence. Test evidence: reply, opt-out, hard/soft-bounce-limit, crash and replay cases. Failure behavior: M6 blocked and incident open.
- [ ] **Close cleanup and promotion —** Input: every terminal attempt, credential/control state and immutable run artifacts. Operation: reconcile, disable, revoke/park, compare exact sets/counts and sign pass/block. Output: M6 gate record with no residual authority. Test evidence: missing transcript, open lease, unresolved attempt, active control or stale credential rejects. Failure behavior: no downstream credit.

## Test strategy

- **Entry `test_test_inbox_entry_rejects_non_owned_target_stale_gate_or_product_control_true`.**
- **Authority `test_only_sendgateway_can_reach_gmail_and_each_message_has_fresh_operator_approval`.**
- **Caps `test_test_inbox_caps_are_five_per_rolling_day_twenty_total_and_one_inflight`.**
- **Catalog `test_m6_catalog_is_exact_ten_id_ordered_set_with_nine_live_one_recorded_thirteen_live_calls_thirteen_unique_sent_and_two_zero_call_live_outcomes`.**
- **Lanes `test_m6_catalog_set_equals_disjoint_live_owned_alias_and_offline_recorded_command_lanes`.**
- **Concurrency `test_m6_l09_has_one_atomic_admission_reservation_attempt_call_and_sent_winner_one_zero_call_denied_loser_and_no_second_send_after_dbos_restart_replay`.**
- **Rejection `test_m6_o01_recorded_conclusive_rejection_reaches_failed_with_zero_live_call_sent_reconciliation_retry_or_sent`.**
- **No substitution `test_m6_catalog_rejects_skip_replacement_posthoc_exclusion_unavailable_injection_live_for_recorded_or_recorded_for_live_substitution`.**
- **Ambiguity `test_possible_acceptance_reconciles_before_any_next_call_and_never_blind_retries`.**
- **Signals `test_every_owned_reply_and_stop_signal_commits_suppression_before_next_send`.**
- **Exit `test_m6_pass_requires_all_attempts_terminal_cleanup_complete_and_both_controls_false`.**

## Security, privacy, compliance, idempotency, observability, and cost

Aliases and credentials are restricted and absent from normal logs/artifacts; safe evidence uses mailbox/account hashes and opaque IDs. Stable command/send/RFC identities make replay observable but cannot claim provider exactly-once. Calls reserve budget/rate/cost before provider access and reconcile original currency afterward. Telemetry must expose every workflow, policy, attempt, provider observation, suppression and recovery fact without message bodies, tokens or addresses. Test resources create no recipient consent, jurisdiction, legal-policy, public-ingress, or real-user evidence.

## Failure, rollback, and operator recovery

On any abort trigger, use the authenticated local disable path first, stop dequeue/provider construction, retain every possibly consumed rate/cost lease, reconcile Gmail Sent/history by the immutable mailbox/RFC tuple, rotate/revoke credentials when indicated, and preserve the canonical incident timeline. Never edit Gmail/DB state, delete an unresolved attempt, raise a cap, change the allowlist mid-run, retry an ambiguous send, or interpret a later clean row as erasing an earlier M1 disqualifier.

## Acceptance and retained evidence

- [ ] Entry record is complete, signed, immutable and bound to exact source/runtime/release/config/provider/target/caps.
- [ ] Every live recipient is operator-controlled; zero real-recipient, public-route or product-control authority exists.
- [ ] Every offline/live/recovery/signal row passes with zero uncontrolled duplicate or blind retry and no unresolved attempt.
- [ ] The signed two-lane catalog is exact and complete: ten IDs in order, nine live plus one recorded, 13 live calls, 13 unique `SENT` deliveries, two zero-call live outcomes, one recorded conclusive rejection ending `FAILED` with zero live call/delivery/reconciliation/retry, and no skip/replacement/exclusion or cross-lane substitution.
- [ ] Cleanup returns both controls false and leaves all provider/cost/history/suppression evidence reconciled.

Retain entry/gate signatures, release/runtime/config/eval/fixture hashes, owned-alias hash, approvals, command exits, provider/Sent/history/cost/control/audit comparisons, kill/restart traces, incidents, cleanup and credential-control evidence. Retained values exclude addresses, tokens, bodies and the restricted recipient lookup hash.

## Dependencies and next deliverable

LAUNCH-01 consumes M0-M6 and supplies only the M6 technical evidence record. It unlocks [LAUNCH-02](02-controlled-internal-launch.md) after M7 and M8 entry prerequisites exist; it never unlocks a real recipient, `PRODUCT_OUTREACH`, or the public unsubscribe pair.
