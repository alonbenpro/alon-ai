# SendGateway and Gmail Side-Effect Protocol

**Document ID:** BACKEND-04
**Status:** Planned M6 full gateway; current implementation is a minimal in-memory guard only
**Milestone:** M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `BACKEND-04-T01 -> BACKEND-04-T02 -> BACKEND-04-T03 -> BACKEND-04-T04 -> BACKEND-04-T05`; cross-document task Inputs `BACKEND-04-T01 <- PROVIDER-02-T01,BACKEND-03-T01,ARCH-03-T01,PROVIDER-01-T02,DB-03-T01; BACKEND-04-T02 <- BACKEND-03-T04,SEC-05-T03; BACKEND-04-T03 <- PROVIDER-01-T04,AGENT-07-T04; BACKEND-04-T04 <- PROVIDER-02-T02; BACKEND-04-T05 <- PROVIDER-01-T06,PROVIDER-02-T05,SEC-05-T04,TEST-03-T03,BACKEND-03-T03,BACKEND-05-T06,WF-00-T04,LAUNCH-01-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [PROVIDER-01](../05-providers/01-gmail-oauth-and-adapter.md), [PROVIDER-02](../05-providers/02-gmail-history-sync.md), [BACKEND-03](03-policy-engine.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), and [WF-05](../03-workflows/05-outreach-and-reply-workflow.md)
**Outputs:** Sole Gmail send call path, exact last-mile ordering, attempt/result transactions, ambiguity/reconciliation, retry handoff, and crash evidence
**Unlocks:** M6 controlled owned-inbox pilot and later separately authorized bounded product outreach eligibility
**Risk:** Critical
**Complexity:** XL


## Outcome and current repository state

SendGateway is the only application owner allowed to invoke GmailWritePort.send. The foundation gateway/protocol exists but no product send transaction, policy/authorization schema, Gmail adapter or live action described here is implemented. M6 uses isolated owned aliases with product control false; M9 adds earned real-recipient authority. A passing gate is never a send instruction.

Agents, workflows, APIs, frontend, generic provider wrappers and read/sync services have no Gmail write capability. Complete evidence-backed conversations may create initial and response drafts, but every outgoing message follows this same deterministic boundary.

## Exact planned implementation surfaces

Create application/sending.py, strict SendExecutionRequestV1, intent/attempt/result repositories and call-path tests. Only gateway composition receives GmailWritePort. GmailReadPort supports bounded history/Sent reconciliation and has no send method. The existing GmailProvider combined protocol is retired at composition; no alternate production caller remains.

RecordSendIntent belongs to SendGateway through the registered BACKEND-05 handler. It atomically loads ActionAuthorityScopeV1, exact accepted draft/materialization, MemberRef, conversation/thread, offer/economics, strategy/activation, policy/commercial decision and generation. It verifies AUTHORIZED/unexpired/current scope, reserves budget, creates one consumption receipt, stable mailbox idempotency key/RFC Message-ID and immutable intent, then queues only after commit. AUTHORIZED is deterministic; operator preview is not in this path.

SendExecutionRequestV1 carries only send_intent_id, expected message version, workflow run/version, command key, correlation/causation and cancellation reference. The gateway reloads every authority field from PostgreSQL.

## Normative last-mile ordering

1. Check cancellation and process/global dequeue disable before unit of work.
2. Begin serializable transaction; lock the required rows in SEC-05's common order: controls/generations -> campaign/cohort/member and accepted offer/strategy/evidence -> conversation/recipient/thread/lead/business/mailbox/suppression -> authorization/intent/message/attempt -> rate/budget. Every competing signal/close/activation transaction uses that order.
3. Verify the immutable complete scope tuple, action kind/content/materialization, offer/strategy/activation and RFC identity byte-for-byte; expected versions and no unresolved STARTED/AMBIGUOUS/RECONCILING attempt. A cancelled/closed intent cannot run.
4. Require exact isolated-test or independently earned product mode; check all global/campaign/mailbox/provider/conversation kill controls and current control/checkpoint generations.
5. Require current campaign/cohort/member/final qualification, conversation/message/mailbox eligibility and open window. INITIAL_EMAIL cannot run after any inbound cold stop; REPLY_EMAIL requires accepted ReplyEvaluation/NegotiationDecision/objective and current bounded reply state.
6. Require authorization CONSUMED exactly once by this intent, unexpired/unrevoked, cap one and unchanged content/offer/recipient/thread/strategy/activation. Recompute deterministic rendered MIME/materialization hash. No per-message operator decision exists.
7. Build a new SendPolicyFactsV1 at one injected UTC instant from all current accepted identity, jurisdiction, consent-or-counsel-exception, legal review/policy, disclosure/sender template, Google/source review, claim evidence, offer/commercial result, reply/unsubscribe/bounce/complaint/negative-sentiment/terminal flags, conversation rounds/messages/frequency, stage/cumulative/capacity, rate/budget, retry and ambiguity facts. Reuse immutable scope_hash only; never reuse queued/creation facts or require creation_facts_hash equality.
8. Evaluate and persist a fresh SEND decision. Non-suppression denial records policy/audit/idempotent denial and exception as applicable with no attempt. Suppression denial atomically sets message SUPPRESSED, closes only a provably uncalled intent with one-way cancellation reason/time, emits send.suppressed.v1, releases unsent budget/queue reservation and commits with zero rate reservation, attempt, credential access or provider call. Cold-stop/terminal/negative-sentiment denials similarly close uncalled work under canonical state guards without creating durable suppression from an ordinary reply.
9. Only if SEND allows: allocate unique (mailbox_id,rate_policy_version,window_start,slot_number) and concurrency lease; insert RESERVED then CONSUMED reservation; insert STARTED attempt with exact fresh policy/scope/facts and immutable consumed token/non-null consumed_at; increment attempt count; transition QUEUED -> SENDING, set conservative provider_called_at=started_at; append policy.evaluated.v1/send.attempt_started.v1, immutable action attribution, audit/idempotency/outbox; commit. Unique active-mailbox lease and window slot choose one winner. DBOS is the outer limiter; PostgreSQL is final capacity authority.
10. Check cancellation/control generation again at the immediate pre-write boundary. Signed local proof that request bytes never left allows conclusive no-call recovery; incomplete proof means ambiguity and lease retention. A control acknowledgement means no new call can begin after the acknowledged generation boundary; in-flight possibly-called attempts remain visible.
11. Resolve credentials from the exact ACTIVE mailbox proof tuple, decrypt only exact recipient/subject/body in bounded gateway memory, invoke GmailWritePort.send once, and discard plaintext references. No database transaction is held across network.
12. Begin result transaction; lock exact intent/attempt/rate lease/message, reject identity/state mismatch, then GmailResultCaptureService stores immutable provider evidence before state/events.
13. Acceptance or conclusive rejection commits provider result, exact attempt/message transition/event, cost/budget reconciliation and RELEASED lease. Unknown/possibly-called failure records UNKNOWN and AMBIGUOUS/send.outcome_ambiguous.v1, retaining CONSUMED lease. Recovery releases only after terminal positive evidence or expires only with conclusive no-call/no-send proof; wall-clock lease expiry is insufficient.
14. Commit before finite follow-up/reconciliation scheduling. Replay returns stored command results and never reruns a provider step merely because workflow acknowledgement was lost.

Each attempt receives its own action_attribution_id binding governing offer, strategy package, producer strategy, activation, cohort and generations. A campaign-level version tag does not substitute.

## Provider result, retry and cancellation contract

| Evidence | Stored outcome / event | Allowed next action |
| --- | --- | --- |
| parsed direct Gmail acceptance with matching message/thread IDs | SENT; send.provider_accepted.v1 | bounded reply sync |
| explicit provider rejection or signed local pre-write proof | FAILED; send.failed.v1 | SendRecoveryService evaluates finite retry guards |
| timeout, transport/5xx, malformed success, crash with possible call | AMBIGUOUS; send.outcome_ambiguous.v1 | read-only authorized-mailbox reconciliation |
| exactly one matching authorized Sent observation after ambiguity | SENT; send.reconciled_as_sent.v1 | reconcile cost/lease and resume eligible work |
| zero Sent/history results at any age | SEARCH_ABSENT_INCONCLUSIVE, retain AMBIGUOUS/RECONCILING | read-only investigation; incident at 300 seconds, never retry |
| multiple, wrong mailbox/recipient/thread/RFC, malformed or conflicting matches | CONFLICT with consumed lease and incident | quarantine; never guess or retry |

SendRecoveryService alone owns FAILED_RETRYABLE -> QUEUED. It preserves exact intent/member/message/recipient/thread/authorization/offer/strategy/activation/mailbox/RFC identity and requires one of the two conclusive failure proofs, remaining attempts, due time before retry deadline, no unresolved ambiguity/consumed lease and every fresh safety/budget/rate/control guard. Each retry gets a fresh SEND decision and unique rate slot. Superseded authority or changed generation requires explicit safe re-authorization of provably uncalled action; it cannot create a replacement for possibly sent content.

Pause/cancel/kill prevents new calls at checked boundaries and waits for acknowledgements. It cannot turn a possibly-called attempt into CANCELLED or infer non-send from silence. Campaign/checkpoint closure may retain an unresolved safety flag and SAFETY_STOP; it cannot fabricate a terminal provider result. Global rollback pauses future actions and invalidates old generation before boundary activation, preserving historical attribution.

## Errors, fixtures, telemetry and privacy

BACKEND-02 error mapping is exact: control/policy/suppression/authority denial -> 403 POLICY_DENIED with bounded BACKEND-03 reason; stale scope/generation -> 409 VERSION_CONFLICT; state/cancel/result conflict -> 409 STATE_TRANSITION_DENIED; resend while unresolved -> 409 AMBIGUOUS_SEND_REQUIRES_RECONCILIATION; budget/rate -> 429 BUDGET_EXHAUSTED/RATE_LIMITED; conclusively failed dependency -> 503 DEPENDENCY_UNAVAILABLE only if awaiting HTTP result; persistence failure -> 500 INTERNAL_ERROR. Provider error text never becomes application vocabulary.

Fixtures bind immutable scope, accepted draft/MIME, conversation/offer/commercial/strategy evidence, creation and fresh final decisions, member identity, consumed rate lease, provider request/result/call UUID, expected rows/events/call count and RFC 8785 hashes. Crash points include before intent commit, after queue, after attempt before HTTP, during write, after provider acceptance before result, every result transaction write and reconciliation poll/commit, and post-result pre-workflow acknowledgement.

Telemetry uses bounded state/reason/version/count/duration/cost dimensions; safe correlation IDs appear only in restricted traces, not high-cardinality metric labels. No address, recipient lookup digest, MIME/body, legal/consent facts, calendar data, token or raw provider payload leaks. Product data and raw captures follow DB-06/SEC-06.

## Ordered implementation tasks

<!-- roadmap-task id=BACKEND-04-T01 milestone=M6 depends_on=PROVIDER-02-T01,BACKEND-03-T01,ARCH-03-T01,PROVIDER-01-T02,DB-03-T01 mode=parallel locks=backend-domain -->
- [ ] **Implement intent and gateway contracts —** Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts. Operation: encode execution request, errors, repositories, stable identity, and static sole-call rule. Output: importable application gateway. Test evidence: schema/composite/call-graph snapshots. Failure behavior: no provider composition.
<!-- roadmap-task id=BACKEND-04-T02 milestone=M6 depends_on=BACKEND-04-T01,BACKEND-03-T04,SEC-05-T03 mode=parallel locks=backend-domain -->
- [ ] **Implement exact pre-call transaction/order —** Input: queued action-authorized intent/current facts. Operation: lock/recheck, create fresh SEND decision, commit suppression with no attempt or atomically consume a unique rate lease plus attempt/state/events/idempotency/outbox. Output: terminal suppressed result or one conservative started attempt. Test evidence: stale/mutable-fact matrix, failure injection, concurrent lease/slot, suppression no-call, and one-field splice tests. Failure behavior: deterministic denial/rollback and no call.
<!-- roadmap-task id=BACKEND-04-T03 milestone=M6 depends_on=BACKEND-04-T02,PROVIDER-01-T04,AGENT-07-T04 mode=serial locks=gmail-side-effects,backend-domain -->
- [ ] **Implement one provider call and result transactions —** Input: committed attempt and strict provider result; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests. Operation: call once outside transaction, capture evidence, transition/event/cost atomically; implement and verify this path with Gmail network denied here; later live acceptance must consume full pilot-entry authorization. Output: accepted/conclusive/ambiguous result. Test evidence: provider status/exception/cancellation and crash matrix. Failure behavior: possible acceptance always ambiguity.
<!-- roadmap-task id=BACKEND-04-T04 milestone=M6 depends_on=BACKEND-04-T03,PROVIDER-02-T02 mode=serial locks=gmail-side-effects,backend-domain -->
- [ ] **Implement disjoint reconciliation/retry handoff —** Input: ambiguous attempt or separate explicit provider rejection/signed local pre-write proof; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests. Operation: send ambiguity only to positive-evidence mailbox reconciliation and permanent quarantine; send only the two admissible no-call/rejection proofs to deterministic retry guards; prohibit runtime/provider inference; implement and verify this path with Gmail network denied here; later live acceptance must consume full pilot-entry authorization. Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface. Test evidence: zero/one/many/delayed absence plus explicit-rejection/pre-write/exhaustion tests; every negative read proves zero queue transitions. Failure behavior: controls off/incident/operator-visible unresolved.
<!-- roadmap-task id=BACKEND-04-T05 milestone=M6 depends_on=BACKEND-04-T04,PROVIDER-01-T06,PROVIDER-02-T05,SEC-05-T04,TEST-03-T03,BACKEND-03-T03,BACKEND-05-T06,WF-00-T04,LAUNCH-01-T03 mode=serial locks=gmail-side-effects,milestone-gate,live-environment -->
- [ ] **Prove M6 gateway, service authority, and observability —** Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: prove the M6 provider/gateway behavior and enumerate/enforce every M6 sole writer, repository owner, command handler, table, and event without duplicating service logic; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed M6 provider/gateway/sole-writer authority and observability evidence. Test evidence: the current M6 gateway suite plus table-writer, handler, import/call, and real-service spies. Failure behavior: both controls remain false and M6 stays blocked.


## Verification and acceptance

Prove exactly one production GmailWritePort.send caller by direct/transitive import graph and runtime spy. Deny every one-field authority/offer/cohort/activation/recipient/thread/generation/rate splice before credential access. Test normal automatic sends/responses without operator approval, every mutable compliance and terminal-signal race, one winner under concurrent slot/lease allocation, and zero attempts/calls on suppression.

Retain full crash/replay/provider/reconciliation/retry matrices with zero uncontrolled duplicates, permanent quarantine on negative read evidence, and distinct direct versus reconciled acceptance events. Every unsafe sequence disables controls and opens an incident. Recovery uses typed commands and positive provider evidence, never SQL or a resend experiment. This document implements sending only; [BookingGateway](01-domain-services.md) independently owns all calendar changes.
