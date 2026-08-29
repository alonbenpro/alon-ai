# Gmail OAuth, Side-Effect, and Reconciliation Tests

**Document ID:** TEST-04
**Status:** Planned M1/M6 Gmail safety suite; current repository has only a provider protocol, a minimal guarded SendGateway, and no OAuth/API call or send implementation
**Milestone:** M1 disposable runtime acceptance; M6 owned-inbox pilot; M9 real-recipient prerequisite
**Owner:** Solo operator
**Prerequisites:** PROVIDER-01/02, DB-03/05/06, WF-01/05/06, BACKEND-03/04/05, SEC-03/04/05, OBS-01/02/05, and TEST-01..03
**Outputs:** OAuth crash/CAS proof, exact gateway ordering/call-count matrix, provider ambiguity/reconciliation evidence, atomic recipient-signal suppression, and owned-alias M6 gate bundle
**Unlocks:** M6 only on complete owned-inbox evidence; M9 remains separately gated by legal/policy/public-ingress evidence
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Every Gmail credential and send outcome is classified, durably captured, mailbox-bound, reconciled, suppressible, and operator-visible. Agents/workflows/routes never call Gmail; only deterministic policy plus `SendGateway` reaches `GmailProvider.send`. Any possible provider acceptance enters ambiguity and is never blindly retried.

## Current repository state

No Google project configuration, Gmail OAuth flow, versioned secret object, mailbox row, Gmail adapter, Sent search/history cursor, MIME capture, product send ledger, suppression transaction, test-inbox pilot, or provider evidence exists. `ALON_AI_OUTREACH_ENABLED=false` and unit spies around the minimal gateway are foundation guards only.

## Scope and non-goals

In scope: least-scope OAuth, exact six-point secret saga, mailbox/account binding, send request/result unions, 14-step last-mile order, K-style provider boundaries, cancellation, rate/budget/approval/final-SEND/suppression, stable RFC identity, direct acceptance vs rejection vs unknown, zero/one/many/cross-mailbox Sent reconciliation, bounded absence, history cursor/full sync, reply/unsubscribe/bounce/complaint suppression, atomicity, redaction, revoke/rotation and cleanup. Non-goals: prospect recipients before M9, Gmail sandbox as an exactly-once claim, API-level automatic retry, provider-console repair, broad mail scope, or raw MIME/token evidence in ordinary artifacts.

## Exact planned implementation surfaces

Create `backend/tests/gmail/{contract,oauth,recovery,reconciliation,history,signals,live_owned_alias}`, `tests/fixtures/gmail/manifest.v1.json`, network-call recorder, hard barriers around the exact BACKEND-04 order, and signed live-capture scrubber. Ordinary PR lanes use `RECORDED_FIXTURE` with socket denial. `LIVE_OWNED_ALIAS` requires an isolated Google project, dedicated mailbox, exact owned alias allowlist, separate secret generation, fresh schema, `TEST_INBOX_SENDING=true`, `PRODUCT_OUTREACH=false`, approved send count/cash/time cap and cleanup/revocation checklist.

| Matrix | Exact cases | Pass evidence | Failure action |
| --- | --- | --- | --- |
| OAuth saga | before exchange; exchange/pre-STAGE; STAGE/pre-ACTIVATE; ACTIVE/pre-DB; DB/pre-HTTP; handler/bind vs GC CAS | one exchange, resumable STAGED/ACTIVE, exact ACTIVE proof+mailbox tuple, replayed stored 303, one cleanup winner | mailbox/both controls off; restart or typed `ABORT_OAUTH_SAGA`; never patch secret/DB |
| send authority | deny at every BACKEND-04 step 1..10 and all 14 dedicated compliance/signal denials | zero credential access/call before committed consumed rate reservation+attempt; one call maximum afterward | disable controls, incident on ordering/call breach |
| provider result | parsed 2xx IDs; conclusive 4xx/rate/quota; timeout/reset/5xx/malformed 2xx; crash before/after call/result commit | exact `ACCEPTED|CONCLUSIVE_REJECTION|UNKNOWN`, correct event, row/cost/lease state and call count | possible call -> `AMBIGUOUS`; no adapter retry |
| Sent reconciliation | delayed zero polls at 0/5/15/30/60/120/300; one; many; cross-mailbox; incomplete query; credential change | one match -> reconciled sent; successful bounded absence only after required polls; conflicts visible | retain ambiguity/lease, mailbox dequeue off, incident |
| history/signals | duplicate/out-of-order page; cursor 404/full-sync race; reply, unsubscribe, hard/soft bounce, complaint; crash after every row | observation/reply/suppression/intent/events/cursor atomic, no next SEND after committed stop | cursor unchanged, product control false, typed replay/repair |
| controls/rate | concurrent workers, window boundary, pause/cancel/global stop, worker replacement | one mailbox lease/slot/call; zero starts after confirmed bound | both controls false and M6 fails |

The 14 dedicated denial set is imported from TEST-02 and must remain exact. The gateway success fixture includes the full immutable campaign/member/lead/message/mailbox/approval/eligibility basis, fresh final `SEND` decision, consumed rate reservation, stable idempotency/RFC IDs, and expected row/event/call counts. Plaintext exists only in bounded adapter memory and is replaced with canaries in tests.

Reference live lane preflight pseudocode:

```python
assert environment == "LIVE_OWNED_ALIAS"
assert recipient in signed_owned_alias_allowlist
assert controls == {"TEST_INBOX_SENDING": True, "PRODUCT_OUTREACH": False}
assert gate_manifest.m1_passed and send_budget.remaining >= scenario.send_count
assert gmail_call_recorder.count == 0
run_scenario()
assert gmail_call_recorder.count == expected_call_count
reconcile_all_attempts_before_cleanup()
```

## Ordered implementation tasks

- [ ] **Build strict offline Gmail fixtures —** Input: PROVIDER-01/02 request/result/error/MIME/history contracts. Operation: capture or construct redacted signed fixtures for every branch and deny network. Output: deterministic provider simulator. Test evidence: schema/hash/PII/secret/cross-mailbox/tamper matrix. Failure behavior: fixture rejected; no live fallback.
- [ ] **Prove the six-point OAuth saga —** Input: fake versioned secret store plus real transactional PostgreSQL. Operation: hard-kill at each flow/object/DB/HTTP/GC boundary and replay exact callback. Output: one exchange and safe terminal/resumable result. Test evidence: CAS generation, lease expiry, strong reads, ACTIVE proof and cleanup winner. Failure behavior: no mailbox success; restart/typed repair only.
- [ ] **Prove 14-step gateway authority and results —** Input: exact product fixture and provider call recorder. Operation: deny/inject crash at every step and map all provider observations. Output: exact rows/states/events/leases/cost/call counts. Test evidence: one-field authority splices, 14 no-call denials, concurrency and cancellation. Failure behavior: ambiguity or deterministic denial; never blind retry.
- [ ] **Prove reconciliation and recipient signals —** Input: mailbox-bound Sent/history fixtures. Operation: exercise bounded polls, cursor recovery and atomic stop-signal transaction under replay/concurrency. Output: terminal or explicit unresolved state plus active suppression. Test evidence: zero/one/many/cross-account and every write-boundary crash. Failure behavior: mailbox/product off; cursor not advanced.
- [ ] **Run controlled M6 owned-alias gate —** Input: signed preflight, isolated credential/schema and hard caps. Operation: execute approved scenarios, reconcile every call, compare Gmail IDs/RFC IDs/ledger and revoke/clean up. Output: signed M6 bundle. Test evidence: zero duplicates/blind retries/post-control calls and complete suppression/reply evidence. Failure behavior: M6 fails and both controls false.

## Test strategy

- **Authority `test_only_sendgateway_reaches_users_messages_send_and_calls_once_after_committed_authority`.**
- **OAuth `test_six_oauth_kill_points_have_one_exchange_safe_replay_and_one_gc_winner`.**
- **Policy `test_all_fourteen_compliance_signal_denials_have_zero_credential_and_gmail_calls`.**
- **Ambiguity `test_timeout_reset_5xx_malformed_success_and_post_accept_crash_reconcile_before_retry`.**
- **Mailbox `test_zero_one_many_cross_mailbox_and_delayed_sent_candidates_follow_exact_outcomes`.**
- **Signals `test_reply_unsubscribe_bounce_complaint_suppression_and_cursor_commit_atomically`.**
- **Control `test_pause_cancel_global_stop_and_concurrency_prevent_new_mailbox_calls`.**
- **Leak `test_tokens_addresses_mime_and_provider_bodies_are_absent_from_all_retained_outputs`.**

## Security, privacy, compliance, idempotency, observability, and cost

Live sends use only operator-owned aliases before M9 and least `gmail.modify` scope. Call, idempotency and RFC identities connect restricted evidence without logging addresses. Provider calls reserve send/rate/cost budgets and stop at the manifest cap. Suppression wins at the last-mile locked read and on observed signals. Legal/policy gates remain inputs owned by operator/counsel; M1/M6 passing is never sufficient real-recipient authority.

## Failure, rollback, and operator recovery

On leaked credential, wrong mailbox, duplicate, hidden/old ambiguity, suppression/rate/control breach, cursor gap, impossible CAS/result/state or cleanup race: stop dequeues, set both controls false, retain consumed lease and evidence, reconcile every possibly called attempt, revoke/rotate when indicated, and open the exact incident. Roll back code/config only after drain and full rerun. Never resend, re-exchange a code, edit provider/DB state manually, or delete an unresolved credential/attempt.

## Acceptance and retained evidence

- [ ] Six OAuth kill points prove one exchange, exact ACTIVE binding, replay and reference-safe cleanup.
- [ ] Fourteen-step gateway order and all dedicated denials prove zero premature credential/provider access.
- [ ] Every provider/Sent/history/signal outcome has exact mailbox-bound rows/states/events/cost/lease/recovery.
- [ ] M6 evidence uses owned aliases with product outreach false and contains zero uncontrolled duplicates/blind retries.

Retain fixture/call-graph hashes, OAuth lifecycle/CAS traces, authority/order/kill matrices, provider/Sent/history captures with sensitive data removed, row/event/cost/call comparisons, control/rate/suppression evidence, cleanup/revocation proof and signed M6 result.

## Dependencies and next deliverable

TEST-04 supplies the M6 safety bundle to [TEST-05 operator journeys](05-end-to-end-browser-tests.md), INFRA-02 and launch Task 6. It never unlocks a real recipient by itself; M9 additionally requires current legal/policy and the scanner-safe public-ingress evidence from TEST-06/INFRA-03.
