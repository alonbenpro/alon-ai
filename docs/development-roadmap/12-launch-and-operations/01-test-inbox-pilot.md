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

The phase is complete only when the exact eight-ID live catalog below runs without omission or substitution, its 12 provider calls reconcile to 12 unique `SENT` messages, its zero-call control stays at zero, every expected reply/signal is linked and suppressive, all kill/restart rows pass, and both controls return to false. Missing or ambiguous evidence is a block, not an invitation to run more live messages.

## Current repository state

The repository currently has foundation health/CI/Compose, typed Gmail/policy gateway contracts, and outreach disabled by default. It has no DBOS workflow, Temporal adapter, 46-table product schema, Gmail OAuth/API adapter, history cursor, test mailbox, suppression transaction, 66-operation product API, operator UI, M6 runner, or live-provider evidence. Foundation tests and the historical container CI run do not satisfy any M6 row.

## Scope and non-goals

In scope: one isolated Google project, one dedicated mailbox, one signed allowlist of four to five operator-controlled recipient aliases so `M6-L01` can use four distinct scenario/alias pairs, exact runtime/release/config bindings, manual approval for each live test message, bounded sends, crash/restart/ambiguity/reconciliation/history/reply/suppression/control evidence, cleanup, credential revocation, and a signed gate decision.

Non-goals: prospects or any address not controlled by the operator, legal/consent evidence, product outreach, public unsubscribe publication, volume testing, automated follow-up, model-selected recipients, direct Gmail access by an agent/workflow, a product schema in M1, or promotion from test evidence into real-recipient authority.

## Exact planned implementation surfaces

This gate creates no new product table, endpoint, event, agent artifact, provider capability, service, or command ID. It executes the existing `T7-GMAIL-OFFLINE` and `T7-GMAIL-LIVE` rows, canonical 46-table owners, 14-step `SendGateway`, 14 final-SEND compliance/signal denials, six provider capability families, and M1 `K0..K8`/eight-disqualifier contracts. The signed gate record is immutable release evidence, not a product artifact or authority row.

### Entry manifest and prerequisites

The signed entry record binds literal phase `TEST_INBOX_PILOT`, source commit/tree with `dirty=false`, `ReleaseManifestV1`, selected runtime/version, database system/schema ID, all 46-table/API/policy/provider/event/metric/incident manifest hashes, active `PromotionManifestV1` references, exact model/prompt/tool/provider versions, Google project/mailbox/account hash, credential generation references without values, owned-alias allowlist hash, the exact ordered eight-ID catalog and scenario/alias allocation below, send/cost/time caps, M1/M2/M3/M4/M5 evidence IDs/hashes/freshness, planned `T7-GMAIL-LIVE` command/fixture/`GMAIL_OWNED_ALIAS` profile hashes, operator approval, start/expiry UTC, and both expected control versions.

| Entry prerequisite | Required immutable evidence | Failure behavior |
| --- | --- | --- |
| M0-M5 | signed brief/decision rules, M2 46-table/restore set equality, promoted M3 configs, one accepted M4 synthetic bundle, M5 provenance/dedupe/precision gate | no credential construction; pilot blocked |
| M1 runtime | every `K0..K8` row and all eight criteria pass; after any canonical DBOS disqualifier, a completed Temporal migration plus the same application-level matrix | DBOS is permanently ineligible after one disqualifier; no waiver or rerun erases it |
| M6 implementation | exact Gmail OAuth/history/result unions, policy/approval/suppression/budget/rate/control owners and `T7-GMAIL-OFFLINE` exit `0` | both controls false; no live lane |
| Test identity | isolated Google project, one dedicated mailbox, four-to-five owned aliases, exact mailbox/account binding and separate credential/schema generations | wrong/unknown target exits before credential access |
| Visibility and stop | authoritative DB queries, correlated audit/provider/cost evidence, local disable path and alert delivery visible before the first call | both controls false; no call |

### Execution envelope and operator steps

| Bound | Exact pilot value |
| --- | --- |
| Recipients | four to five operator-controlled aliases required by the frozen allocation; zero real recipients |
| Mailbox/project | exactly one dedicated mailbox in one isolated Google project |
| Send cap | exactly 12 catalog provider calls and 12 unique delivered messages plus one zero-call control scenario; never more than 5 messages in any rolling 24 hours or 20 messages total |
| Per-recipient cap | at most one live message per approved scenario/alias pair; no automated follow-up |
| Concurrency | one in-flight Gmail send per mailbox |
| Controls/routes | `TEST_INBOX_SENDING=true` only for the live window; `PRODUCT_OUTREACH=false` always; public unsubscribe GET/POST absent and unpublished |
| Approval | one fresh persisted operator approval per message version before `RecordSendIntent`; no batch approval |
| Provider behavior | `SendGateway` is the sole Gmail path; any possible acceptance is `AMBIGUOUS`/`RECONCILING` until evidence resolves it; no blind retry |

### Frozen `T7-GMAIL-LIVE` scenario catalog

The signed entry freezes this exact set and order under command `T7-GMAIL-LIVE` and profile `GMAIL_OWNED_ALIAS`. Every call-bearing row uses a fresh manually approved message and a distinct approved scenario/alias pair; `M6-L01` allocates four distinct owned aliases. The two suppressive signal rows use different owned aliases, and no alias is used after its suppression commits.

| Scenario ID | Command deliveries | Provider calls / unique delivered messages | Required terminal evidence |
| --- | ---: | ---: | --- |
| `M6-L01_DIRECT_ACCEPTED` | 4 | 4 / 4 | four distinct approved scenario/alias pairs each produce one unique `SENT` outcome |
| `M6-L02_DUPLICATE_COMMAND_REPLAY` | 2 | 1 / 1 | duplicate command delivery returns the same result; exactly one provider call and one unique `SENT` message |
| `M6-L03_ACCEPTED_RESULT_PERSIST_CRASH` | 2 | 2 / 2 | each run is killed after provider acceptance and before result persistence; both reconcile to `SENT` with zero duplicate |
| `M6-L04_TIMEOUT_UNKNOWN_RECONCILE` | 2 | 2 / 2 | each injected post-call timeout/unknown result reaches bounded reconciled `SENT` truth with zero blind retry or duplicate |
| `M6-L05_HISTORY_CURSOR_RESTART` | 1 | 1 / 1 | cursor/page restart yields one observation, one terminal `SENT` truth and zero duplicate |
| `M6-L06_REPLY_SUPPRESSION` | 1 | 1 / 1 | owned-alias reply atomically records reply evidence, creates suppression and proves no next `SEND` |
| `M6-L07_UNSUBSCRIBE_REPLY_SUPPRESSION` | 1 | 1 / 1 | deterministic supported unsubscribe reply phrase creates canonical suppression and proves no next `SEND`; this is mailbox reply handling, never the M9 public route |
| `M6-L08_PRECALL_CONTROL_KILL` | 1 | 0 / 0 | control closes after admission and before the provider call; terminal denied/cancelled evidence and exact zero provider calls/messages |
| **Exact total** | **14** | **12 / 12** | **all eight IDs present, all required outcomes satisfied and the zero-call row remains zero** |

No row may be skipped, replaced, renamed, repeated to erase a failure, or excluded after execution. Provider unavailability, missing credit/authentication, unavailable failure injection, an omitted ID, wrong order, wrong command/profile, or any per-row/total count mismatch is `BLOCKED`/unavailable and cannot pass. `T7-GMAIL-OFFLINE` remains necessary but cannot substitute any live row.

The operator verifies the signed target and evidence directory, proves both controls false, loads the isolated credential reference, and schedules the 12 calls across at least three cap-safe windows: calls 1-5, calls 6-10, then calls 11-12, with the rolling-24-hour guard authoritative at every admission. The operator enables only `TEST_INBOX_SENDING` at the expected version, approves one exact message, runs the next frozen row, reconciles it to required terminal evidence before advancing, checks reply/suppression/history/cost/audit truth, and immediately disables the test control on any mismatch. `M6-L08_PRECALL_CONTROL_KILL` consumes no send capacity. After the last row, the operator reconciles every attempt, disables the test control, revokes or parks the credential generation under policy, retains cleanup evidence, and signs pass/block. No row is a follow-up.

| Decision point | Exact rule |
| --- | --- |
| Success | exact catalog set/order equality; exact 12 provider calls/12 unique `SENT` messages plus one zero-call control row; every required outcome and no-skip rule satisfied; zero wrong-target, duplicate, blind-retry, suppression, budget, rate, post-disable, audit, history-cursor, or unresolved-ambiguity failures; every required M6 row exit `0`; both controls false after cleanup |
| Immediate abort | any identity/target/control/version drift; possible unrecorded call; duplicate; unresolved ambiguity outside the bounded reconciliation row; suppression/reply/cursor/cost/audit mismatch; credential leak; telemetry blindness; cap breach; or any M1 disqualifier |
| Rollback/demotion | commit both controls false, stop dequeues, preserve consumed leases/evidence, reconcile all possible calls, revoke affected credentials, open the canonical incident, and return to the failed M1/M6 gate |
| Re-entry | new signed entry record after the incident is resolved, exact fix/release/config/eval evidence is current, all affected offline/recovery rows pass, and caps are no larger than before |
| Downstream unlock | M6 technical gate only; LAUNCH-02 may begin when its independent M7/M8 prerequisites pass |

## Ordered implementation tasks

- [ ] **Freeze the pilot entry and target —** Input: current M0-M5 gates, runtime decision, release/config/eval hashes, isolated project/mailbox, owned aliases and the exact eight-ID catalog/allocation. Operation: verify every entry row, catalog set/order/count and cap-safe windows, then sign the immutable envelope before credential access. Output: one bounded entry record. Test evidence: stale/missing/cross-project/real-address/catalog/cap/control/version negatives. Failure behavior: both controls false; no credential construction.
- [ ] **Close offline Gmail and authority evidence —** Input: exact fixtures and `T7-GMAIL-OFFLINE`. Operation: prove OAuth saga, 14-step gateway, 14 denials, reconciliation, suppression, history, budgets and call graph with network denied. Output: complete offline prerequisite bundle. Test evidence: every planned negative and exact zero-call spy. Failure behavior: live lane unavailable.
- [ ] **Execute the exact live catalog one message at a time —** Input: signed eight-ID entry, fresh approval, required injection and remaining caps. Operation: run `M6-L01` through `M6-L08` in order solely through `SendGateway`, reconcile the required terminal truth before the next admission and preserve the zero-call control. Output: exact 12-call/12-delivery transcript plus zero-call denial and authoritative DB/event/cost comparison. Test evidence: scenario set/order equality, each row's terminal outcome, duplicate replay, accepted-result crash, timeout/unknown reconciliation, cursor restart and rolling-window admission. Failure behavior: abort, controls false and reconcile; omission/unavailable injection/count mismatch is blocked, never pass.
- [ ] **Exercise signals and operator stop —** Input: owned replies/unsubscribe/bounce fixtures and control commands. Operation: prove atomic suppression/history/cursor behavior and zero calls after committed disable/cancel. Output: stop/suppression evidence. Test evidence: reply, opt-out, hard/soft-bounce-limit, crash and replay cases. Failure behavior: M6 blocked and incident open.
- [ ] **Close cleanup and promotion —** Input: every terminal attempt, credential/control state and immutable run artifacts. Operation: reconcile, disable, revoke/park, compare exact sets/counts and sign pass/block. Output: M6 gate record with no residual authority. Test evidence: missing transcript, open lease, unresolved attempt, active control or stale credential rejects. Failure behavior: no downstream credit.

## Test strategy

- **Entry `test_test_inbox_entry_rejects_non_owned_target_stale_gate_or_product_control_true`.**
- **Authority `test_only_sendgateway_can_reach_gmail_and_each_message_has_fresh_operator_approval`.**
- **Caps `test_test_inbox_caps_are_five_per_rolling_day_twenty_total_and_one_inflight`.**
- **Catalog `test_m6_live_catalog_is_exact_eight_id_set_in_order_with_twelve_calls_twelve_unique_sent_and_one_zero_call_row`.**
- **No substitution `test_m6_live_catalog_rejects_skip_replacement_posthoc_exclusion_unavailable_injection_or_offline_substitution`.**
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
- [ ] The signed live catalog is exact and complete: eight IDs in order, 12 calls, 12 unique `SENT` deliveries, one zero-call control, no skip/replacement/exclusion and no offline substitution.
- [ ] Cleanup returns both controls false and leaves all provider/cost/history/suppression evidence reconciled.

Retain entry/gate signatures, release/runtime/config/eval/fixture hashes, owned-alias hash, approvals, command exits, provider/Sent/history/cost/control/audit comparisons, kill/restart traces, incidents, cleanup and credential-control evidence. Retained values exclude addresses, tokens, bodies and the restricted recipient lookup hash.

## Dependencies and next deliverable

LAUNCH-01 consumes M0-M6 and supplies only the M6 technical evidence record. It unlocks [LAUNCH-02](02-controlled-internal-launch.md) after M7 and M8 entry prerequisites exist; it never unlocks a real recipient, `PRODUCT_OUTREACH`, or the public unsubscribe pair.
