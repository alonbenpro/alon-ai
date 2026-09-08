# Gmail OAuth, Side-Effect, and Reconciliation Tests

**Document ID:** TEST-04
**Status:** Planned M1/M6 Gmail safety suite; current repository has only a provider protocol, a minimal guarded SendGateway, and no OAuth/API call or send implementation
**Milestone:** M1, M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `TEST-04-T01 <- PROVIDER-01-T02,TEST-01-T03,PROVIDER-01-T01; TEST-04-T02 <- TEST-04-T01,TEST-01-T02,PROVIDER-01-T01; TEST-04-T03 <- TEST-04-T02,PROVIDER-01-T03,DB-03-T04,DB-05-T03; TEST-04-T04 <- TEST-04-T03,BACKEND-04-T04,SEC-05-T03; TEST-04-T05 <- TEST-04-T04,PROVIDER-02-T04,WF-05-T04; TEST-04-T06 <- TEST-04-T05,WF-05-T05,BACKEND-04-T05,SEC-05-T04,PROVIDER-01-T06,PROVIDER-02-T05,LAUNCH-01-T03`; descriptive contract sources are linked in this document and do not imply whole-document completion dependencies
**Outputs:** OAuth crash/CAS proof, exact gateway ordering/call-count matrix, provider ambiguity/reconciliation evidence, atomic recipient-signal suppression, and owned-alias M6 gate bundle
**Unlocks:** M6 only on complete owned-inbox evidence; M9 remains separately gated by legal/policy/public-ingress evidence
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Every Gmail credential and send outcome is classified, durably captured, mailbox-bound, reconciled, suppressible, and operator-visible. Agents/workflows/routes never call Gmail; only deterministic policy plus `SendGateway` reaches `GmailProvider.send`. Any possible provider acceptance enters ambiguity and is never blindly retried.

The M9 extension repeats the final-slot and crash matrix at stage boundaries `100`, `300`, `600`, and `1,000`. Provider spies prove that concurrent contenders cannot create call 101/301/601/1001, a recipient from an earlier stage produces zero call, and any ambiguous attempt consumes/quarantines its capacity until positive reconciliation rather than opening a replacement slot.

## Current repository state

No Google project configuration, Gmail OAuth flow, versioned secret object, mailbox row, Gmail adapter, Sent search/history cursor, MIME capture, product send ledger, suppression transaction, test-inbox pilot, or provider evidence exists. `ALON_AI_OUTREACH_ENABLED=false` and unit spies around the minimal gateway are foundation guards only.

## Scope and non-goals

In scope: least-scope OAuth, exact six-point secret saga, mailbox/account binding, send request/result unions, 14-step last-mile order, K-style provider boundaries, cancellation, rate/budget/action-authority/final-SEND/suppression, stable RFC identity, direct acceptance vs rejection vs unknown, zero/one/many/cross-mailbox Sent reconciliation, permanent ambiguity quarantine, history cursor/full sync, cold-reply stops and qualifying unsubscribe/bounce/complaint suppression, atomicity, redaction, revoke/rotation and cleanup. Non-goals: prospect recipients before M9, Gmail sandbox as an exactly-once claim, API-level automatic retry, provider-console repair, broad mail scope, or raw MIME/token evidence in ordinary artifacts.

## Exact planned implementation surfaces

Create `backend/tests/gmail/{contract,oauth,recovery,reconciliation,history,signals,live_owned_alias}`, `tests/fixtures/gmail/manifest.v1.json`, network-call recorder, hard barriers around the exact BACKEND-04 order, and signed live-capture scrubber. Ordinary PR lanes use `RECORDED_FIXTURE` with socket denial. `LIVE_OWNED_ALIAS` requires an isolated Google project, dedicated mailbox, exact owned alias allowlist, separate secret generation, fresh schema, `TEST_INBOX_SENDING=true`, `PRODUCT_OUTREACH=false`, approved send count/cash/time cap and cleanup/revocation checklist.

| Matrix | Exact cases | Pass evidence | Failure action |
| --- | --- | --- | --- |
| OAuth saga | before exchange; exchange/pre-STAGE; STAGE/pre-ACTIVATE; ACTIVE/pre-DB; DB/pre-HTTP; handler/bind vs GC CAS | one exchange, resumable STAGED/ACTIVE, exact ACTIVE proof+mailbox tuple, replayed stored 303, one cleanup winner | mailbox/both controls off; restart or typed `ABORT_OAUTH_SAGA`; never patch secret/DB |
| send authority | deny at every BACKEND-04 step 1..10 and all 14 dedicated compliance/signal denials | zero credential access/call before committed consumed rate reservation+attempt; one call maximum afterward | disable controls, incident on ordering/call breach |
| provider result | parsed 2xx IDs; conclusive 4xx/rate/quota; timeout/reset/5xx/malformed 2xx; crash before/after call/result commit | exact `ACCEPTED|CONCLUSIVE_REJECTION|UNKNOWN`, correct event, row/cost/lease state and call count | possible call -> `AMBIGUOUS`; no adapter retry |
| Sent reconciliation | delayed zero polls at 0/5/15/30/60/120/300 and far beyond; one; many; cross-mailbox; incomplete query; credential change | one match -> reconciled sent; every zero/many/conflict case retains quarantine; 300 seconds only raises incident | retain ambiguity/lease, mailbox dequeue off, no retry/replacement, incident |
| history/signals | duplicate/out-of-order page; cursor 404/full-sync race; reply, unsubscribe, hard/soft bounce, complaint; crash after every row | observation/reply/suppression/intent/events/cursor atomic, no next SEND after committed stop | cursor unchanged, product control false, typed replay/repair |
| controls/rate | concurrent workers, window boundary, pause/cancel/global stop, worker replacement | one mailbox lease/slot/call; zero starts after confirmed bound | both controls false and M6 fails |

The 14 dedicated denial set is imported from TEST-02 and must remain exact. The gateway success fixture includes the full immutable campaign/member/lead/message/mailbox/ActionAuthorityScopeV1/eligibility basis, fresh final `SEND` decision, consumed rate reservation, stable idempotency/RFC IDs, and expected row/event/call counts. Plaintext exists only in bounded adapter memory and is replaced with canaries in tests.

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

Offline OAuth/provider/result/reconciliation/suppression requirements map exactly to `T7-GMAIL-OFFLINE`. After the same manifest-bound physical absolute `TASK7_SIGNED_CHECKOUT` precondition as TEST-03, the invocation from any cwd is `"$TASK7_SIGNED_CHECKOUT/scripts/task7/run" --manifest tests/manifests/task7-commands.v1.json --command T7-GMAIL-OFFLINE --run-id "$TASK7_RUN_ID" --evidence-root "$TASK7_EVIDENCE_ROOT" --profile GMAIL_RECORDED --target-manifest "$TASK7_TARGET_MANIFEST"`. Only the bounded M6 owned-alias rows map to `T7-GMAIL-LIVE`, invoked by substituting `--command T7-GMAIL-LIVE --profile GMAIL_OWNED_ALIAS` in that exact normalized argv. Relative argv[0], caller-cwd resolution, symlink/equal-inode/copy, or a checkout not bound by the signed repository identity exits before target or credential access. The signed fixture manifest, isolated database/system ID, Google project/mailbox binding, owned-alias allowlist, call/send/cost cap and both control values are required inputs; the live target guard refuses any non-owned address or `PRODUCT_OUTREACH=true` before credential access. Provider unavailability exits `30`; any possibly accepted but incomplete outcome exits `60` and enters reconciliation, never pass/retry. The mapping domains are disjoint and their union equals every TEST-04 requirement.

## Autonomous reply and action-authority regression cases

The legacy dedicated compliance/signal family now uses COLD_SEQUENCE_STOPPED in place of the obsolete all-reply denial and retains all other applicable identity/jurisdiction/consent/legal/disclosure/Google/opt-out/bounce/complaint cases from TEST-02. Derive the complete additional denial set from BACKEND-03. Test that a reply denies INITIAL_EMAIL immediately while a new evidence-backed REPLY_EMAIL can pass its bounded conversation objective; any claimed global ban on every reply is a regression.

Add explicit writer/send separation: EmailWritingAgent has sanitized dossier/final qualification/offer/strategy/full thread/objective and no Gmail credential/write capability. ActionAuthorizationService creates ActionAuthorityScopeV1; only SendGateway commits/consumes the send intent and calls Gmail after fresh facts. Mutate recipient/thread/message/content/offer/strategy/activation/cohort/checkpoint/control generation, claim evidence, commercial decision, expiry, rate and budget between creation and final SEND. Each stale/unsafe case denies without credential access/call; current facts need not equal creation-time hashes.

Inbound observation/reply/full conversation message/cold stop/generation invalidation/events/outbox/cursor are atomic. Race inbound positive/question/objection/rejection/opt-out/complaint/bounce with queued initial send, authorized reply, provider call entry and result persistence. Qualifying durable suppression alone writes a suppression entry; ordinary decline closes persuasion without inferring no-future-contact authority. A possibly-called attempt retains AMBIGUOUS/RECONCILING plus stop blocker.

Bounded reply cases cover round/message/frequency/window exhaustion, stale full-thread version, duplicate or out-of-order replies, negative-sentiment pause, clear rejection falsely relabelled as objection, terminal reopening and BOOKED ending sales outreach. Evidence-backed scheduling changes are independent BookingGateway actions and cannot restart persuasion.

Keep the six-point OAuth saga, fourteen-step SendGateway order, mailbox/account binding, RFC/idempotency/lease/cap-race proofs and unlimited uncertainty quarantine. Missing/zero/multiple/cross-mailbox Sent observations never prove non-send, even after 300 seconds; that time is escalation only. The original M6-L01..L09 single-message owned-alias catalog remains isolated fixture evidence under LAUNCH-01 and does not impose its single-message structure on M9.

## Ordered implementation tasks

<!-- roadmap-task id=TEST-04-T01 milestone=M1 depends_on=PROVIDER-01-T02,TEST-01-T03,PROVIDER-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Build strict offline Gmail fixtures —** Input: PROVIDER-01/02 request/result/error/MIME/history contracts and TEST-01 reproducible clean test contexts. Operation: capture or construct redacted signed fixtures for every branch and deny network. Output: deterministic provider simulator. Test evidence: schema/hash/PII/secret/cross-mailbox/tamper matrix. Failure behavior: fixture rejected; no live fallback.
<!-- roadmap-task id=TEST-04-T02 milestone=M1 depends_on=TEST-04-T01,TEST-01-T02,PROVIDER-01-T01 mode=serial locks=test-command-registry -->
- [ ] **Close offline Gmail command ownership —** Input: deterministic provider simulator, PROVIDER-01 signed disposable OAuth/wire fixtures, document-local offline Gmail matrix, and TEST-01 signed task7-commands.v1.json. Operation: prove exact `T7-GMAIL-OFFLINE|GMAIL_RECORDED` command/fixture/profile mapping, network denial, target guard, and exit semantics. Output: signed offline Gmail command/fixture/profile mapping. Test evidence: live-row-in-offline, network escape, wrong fixture/profile/target, tamper, unavailable, and ambiguity negatives. Failure behavior: no offline/M1 gate credit.
<!-- roadmap-task id=TEST-04-T03 milestone=M6 depends_on=TEST-04-T02,PROVIDER-01-T03,DB-03-T04,DB-05-T03 mode=serial locks=security-runtime -->
- [ ] **Prove the six-point OAuth saga —** Input: fake versioned secret store plus real transactional PostgreSQL; implemented product OAuth saga, complete mailbox/idempotency schema and command replay boundary. Operation: hard-kill at each flow/object/DB/HTTP/GC boundary and replay exact callback. Output: one exchange and safe terminal/resumable result. Test evidence: CAS generation, lease expiry, strong reads, ACTIVE proof and cleanup winner. Failure behavior: no mailbox success; restart/typed repair only.
<!-- roadmap-task id=TEST-04-T04 milestone=M6 depends_on=TEST-04-T03,BACKEND-04-T04,SEC-05-T03 mode=serial locks=gmail-side-effects -->
- [ ] **Prove 14-step gateway authority and results —** Input: the BACKEND-04 guarded gateway/reconciliation implementation, SEC-05 admission decision service, exact product fixture, and provider call recorder. Operation: deny/inject crash at every step and map all provider observations. Output: exact rows/states/events/leases/cost/call counts. Test evidence: one-field authority splices, 14 no-call denials, concurrency and cancellation. Failure behavior: ambiguity or deterministic denial; never blind retry.
<!-- roadmap-task id=TEST-04-T05 milestone=M6 depends_on=TEST-04-T04,PROVIDER-02-T04,WF-05-T04 mode=serial locks=gmail-side-effects -->
- [ ] **Prove reconciliation and recipient signals —** Input: PROVIDER-02 history/cursor recovery, WF-05 recipient-stop implementation, and mailbox-bound Sent/history fixtures. Operation: exercise bounded polls, cursor recovery and atomic stop-signal transaction under replay/concurrency. Output: terminal or explicit unresolved state plus only evidence-qualified durable suppression; completed executable versioned Gmail history/suppression suite with its recorded-fixture/scenario manifest. Test evidence: zero/one/many/cross-account and every write-boundary crash. Failure behavior: mailbox/product off; cursor not advanced.
<!-- roadmap-task id=TEST-04-T06 milestone=M6 depends_on=TEST-04-T05,WF-05-T05,BACKEND-04-T05,SEC-05-T04,PROVIDER-01-T06,PROVIDER-02-T05,LAUNCH-01-T03 mode=serial locks=gmail-side-effects,milestone-gate,test-command-registry,live-environment -->
- [ ] **Run the controlled M6 owned-alias gate and close live command ownership —** Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: execute approved scenarios, reconcile every call, revoke/clean up, and prove disjoint `T7-GMAIL-LIVE` command/profile/target/cap set equality; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed M6 bundle including live command-ownership evidence. Test evidence: zero duplicates/blind retries/post-control calls plus complete Gmail and command-mapping assertions. Failure behavior: M6 fails and both controls remain false.

## Test strategy

- **Authority `test_only_sendgateway_reaches_users_messages_send_and_calls_once_after_committed_authority`.**
- **OAuth `test_six_oauth_kill_points_have_one_exchange_safe_replay_and_one_gc_winner`.**
- **Policy `test_all_fourteen_compliance_signal_denials_have_zero_credential_and_gmail_calls`.**
- **Ambiguity `test_timeout_reset_5xx_malformed_success_and_post_accept_crash_never_escape_quarantine_on_negative_reads`.**
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
