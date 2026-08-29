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

The phase is complete only when every planned live call is reconciled, every expected reply/signal is linked and suppressive, all kill/restart rows pass, and both controls return to false. Missing or ambiguous evidence is a block, not an invitation to run more live messages.

## Current repository state

The repository currently has foundation health/CI/Compose, typed Gmail/policy gateway contracts, and outreach disabled by default. It has no DBOS workflow, Temporal adapter, 46-table product schema, Gmail OAuth/API adapter, history cursor, test mailbox, suppression transaction, 66-operation product API, operator UI, M6 runner, or live-provider evidence. Foundation tests and the historical container CI run do not satisfy any M6 row.

## Scope and non-goals

In scope: one isolated Google project, one dedicated mailbox, one signed allowlist of one to five operator-controlled recipient aliases, exact runtime/release/config bindings, manual approval for each live test message, bounded sends, crash/restart/ambiguity/reconciliation/history/reply/suppression/control evidence, cleanup, credential revocation, and a signed gate decision.

Non-goals: prospects or any address not controlled by the operator, legal/consent evidence, product outreach, public unsubscribe publication, volume testing, automated follow-up, model-selected recipients, direct Gmail access by an agent/workflow, a product schema in M1, or promotion from test evidence into real-recipient authority.

## Exact planned implementation surfaces

This gate creates no new product table, endpoint, event, agent artifact, provider capability, service, or command ID. It executes the existing `T7-GMAIL-OFFLINE` and `T7-GMAIL-LIVE` rows, canonical 46-table owners, 14-step `SendGateway`, 14 final-SEND compliance/signal denials, six provider capability families, and M1 `K0..K8`/eight-disqualifier contracts. The signed gate record is immutable release evidence, not a product artifact or authority row.

### Entry manifest and prerequisites

The signed entry record binds literal phase `TEST_INBOX_PILOT`, source commit/tree with `dirty=false`, `ReleaseManifestV1`, selected runtime/version, database system/schema ID, all 46-table/API/policy/provider/event/metric/incident manifest hashes, active `PromotionManifestV1` references, exact model/prompt/tool/provider versions, Google project/mailbox/account hash, credential generation references without values, owned-alias allowlist hash, send/cost/time caps, M1/M2/M3/M4/M5 evidence IDs/hashes/freshness, planned Task 7 command/fixture/profile hashes, operator approval, start/expiry UTC, and both expected control versions.

| Entry prerequisite | Required immutable evidence | Failure behavior |
| --- | --- | --- |
| M0-M5 | signed brief/decision rules, M2 46-table/restore set equality, promoted M3 configs, one accepted M4 synthetic bundle, M5 provenance/dedupe/precision gate | no credential construction; pilot blocked |
| M1 runtime | every `K0..K8` row and all eight criteria pass; after any canonical DBOS disqualifier, a completed Temporal migration plus the same application-level matrix | DBOS is permanently ineligible after one disqualifier; no waiver or rerun erases it |
| M6 implementation | exact Gmail OAuth/history/result unions, policy/approval/suppression/budget/rate/control owners and `T7-GMAIL-OFFLINE` exit `0` | both controls false; no live lane |
| Test identity | isolated Google project, one dedicated mailbox, one-to-five owned aliases, exact mailbox/account binding and separate credential/schema generations | wrong/unknown target exits before credential access |
| Visibility and stop | authoritative DB queries, correlated audit/provider/cost evidence, local disable path and alert delivery visible before the first call | both controls false; no call |

### Execution envelope and operator steps

| Bound | Exact pilot value |
| --- | --- |
| Recipients | one to five operator-controlled aliases; zero real recipients |
| Mailbox/project | exactly one dedicated mailbox in one isolated Google project |
| Send cap | at most 5 messages in any rolling 24 hours and 20 messages total |
| Per-recipient cap | at most one live message per approved scenario/alias pair; no automated follow-up |
| Concurrency | one in-flight Gmail send per mailbox |
| Controls/routes | `TEST_INBOX_SENDING=true` only for the live window; `PRODUCT_OUTREACH=false` always; public unsubscribe GET/POST absent and unpublished |
| Approval | one fresh persisted operator approval per message version before `RecordSendIntent`; no batch approval |
| Provider behavior | `SendGateway` is the sole Gmail path; any possible acceptance is `AMBIGUOUS`/`RECONCILING` until evidence resolves it; no blind retry |

The operator verifies the signed target and evidence directory, proves both controls false, loads the isolated credential reference, enables only `TEST_INBOX_SENDING` at the expected version, approves one exact message, runs one scenario, reconciles it to terminal evidence before the next scenario, checks reply/suppression/history/cost/audit truth, and immediately disables the test control on any mismatch. After the last row, the operator reconciles every attempt, disables the test control, revokes or parks the credential generation under policy, retains cleanup evidence, and signs pass/block.

| Decision point | Exact rule |
| --- | --- |
| Success | zero wrong-target, duplicate, blind-retry, suppression, budget, rate, post-disable, audit, history-cursor, or unresolved-ambiguity failures; every required M6 row exit `0`; both controls false after cleanup |
| Immediate abort | any identity/target/control/version drift; possible unrecorded call; duplicate; unresolved ambiguity outside the bounded reconciliation row; suppression/reply/cursor/cost/audit mismatch; credential leak; telemetry blindness; cap breach; or any M1 disqualifier |
| Rollback/demotion | commit both controls false, stop dequeues, preserve consumed leases/evidence, reconcile all possible calls, revoke affected credentials, open the canonical incident, and return to the failed M1/M6 gate |
| Re-entry | new signed entry record after the incident is resolved, exact fix/release/config/eval evidence is current, all affected offline/recovery rows pass, and caps are no larger than before |
| Downstream unlock | M6 technical gate only; LAUNCH-02 may begin when its independent M7/M8 prerequisites pass |

## Ordered implementation tasks

- [ ] **Freeze the pilot entry and target —** Input: current M0-M5 gates, runtime decision, release/config/eval hashes, isolated project/mailbox and owned aliases. Operation: verify every entry row and sign the immutable envelope before credential access. Output: one bounded entry record. Test evidence: stale/missing/cross-project/real-address/cap/control/version negatives. Failure behavior: both controls false; no credential construction.
- [ ] **Close offline Gmail and authority evidence —** Input: exact fixtures and `T7-GMAIL-OFFLINE`. Operation: prove OAuth saga, 14-step gateway, 14 denials, reconciliation, suppression, history, budgets and call graph with network denied. Output: complete offline prerequisite bundle. Test evidence: every planned negative and exact zero-call spy. Failure behavior: live lane unavailable.
- [ ] **Execute one-message-at-a-time live rows —** Input: signed entry, fresh approval and remaining caps. Operation: enable only test control, send solely through `SendGateway`, reconcile terminal truth, then admit the next row. Output: capped provider transcript and authoritative DB/event/cost comparison. Test evidence: direct acceptance, conclusive rejection, ambiguity, restart and concurrency rows. Failure behavior: abort, controls false and reconcile.
- [ ] **Exercise signals and operator stop —** Input: owned replies/unsubscribe/bounce fixtures and control commands. Operation: prove atomic suppression/history/cursor behavior and zero calls after committed disable/cancel. Output: stop/suppression evidence. Test evidence: reply, opt-out, hard/soft-bounce-limit, crash and replay cases. Failure behavior: M6 blocked and incident open.
- [ ] **Close cleanup and promotion —** Input: every terminal attempt, credential/control state and immutable run artifacts. Operation: reconcile, disable, revoke/park, compare exact sets/counts and sign pass/block. Output: M6 gate record with no residual authority. Test evidence: missing transcript, open lease, unresolved attempt, active control or stale credential rejects. Failure behavior: no downstream credit.

## Test strategy

- **Entry `test_test_inbox_entry_rejects_non_owned_target_stale_gate_or_product_control_true`.**
- **Authority `test_only_sendgateway_can_reach_gmail_and_each_message_has_fresh_operator_approval`.**
- **Caps `test_test_inbox_caps_are_five_per_rolling_day_twenty_total_and_one_inflight`.**
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
- [ ] Cleanup returns both controls false and leaves all provider/cost/history/suppression evidence reconciled.

Retain entry/gate signatures, release/runtime/config/eval/fixture hashes, owned-alias hash, approvals, command exits, provider/Sent/history/cost/control/audit comparisons, kill/restart traces, incidents, cleanup and credential-control evidence. Retained values exclude addresses, tokens, bodies and the restricted recipient lookup hash.

## Dependencies and next deliverable

LAUNCH-01 consumes M0-M6 and supplies only the M6 technical evidence record. It unlocks [LAUNCH-02](02-controlled-internal-launch.md) after M7 and M8 entry prerequisites exist; it never unlocks a real recipient, `PRODUCT_OUTREACH`, or the public unsubscribe pair.
