# Deterministic Policy Engine

**Document ID:** BACKEND-03
**Status:** Planned M6 policy implementation; only a minimal asynchronous `SendPolicy` protocol exists today
**Milestone:** M6, with provider-budget admission used from M3
**Owner:** Solo operator
**Prerequisites:** [ARCH-03 policy events](../01-architecture/03-domain-events-and-state-machines.md#policy-approval-sending-and-replies), [DB-03](../02-database/03-leads-campaigns-and-messages.md), [DB-05](../02-database/05-audit-events-and-idempotency.md), and BACKEND-01
**Outputs:** Versioned policy facts/scope/hash, exact reason taxonomy, deterministic composition order, immutable decisions, and fail-closed re-evaluation
**Unlocks:** M6 campaign admission, [BACKEND-04 SendGateway](04-send-gateway.md), and control enablement
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Every paid or reputation-bearing action is allowed or denied by deterministic, versioned rules over a frozen fact set. The engine records what it evaluated and why; it never calls providers or mutates business aggregates. Approval is one fact, not an override. Suppression, disabled controls, missing gates, authority mismatch, budget, and unresolved ambiguity always fail closed.

## Current repository state

`PolicyDecision(allowed,reason)` and the `SendPolicy.evaluate(SendRequest)` protocol exist only to guard the foundation `SendGateway`. There is no rule registry, persisted `policy_decisions`, fact/scope hashing, suppression/budget/rate implementation, legal configuration, gate evidence, or product policy. The current protocol is not the target M6 contract.

## Scope and non-goals

In scope: scopes `EXPERIMENT`, `CAMPAIGN`, `SEND`, `PROVIDER`, `CONTROL`; exact facts/reasons; pure composition; immutable policy version; RFC 8785 hashes; deterministic time buckets/rate facts; persistence/event/audit; and replay. Non-goals: legal advice, model judgment, provider calls, SQL inside rules, mutating approval/control/budget/suppression, dynamic downloaded rules, probabilistic allow, or a generic “approved” bypass.

## Exact planned implementation surfaces

Create `domain/policy.py`, `policies/contracts.py`, `policies/rules.py`, `policies/registry.py`, `application/policies.py`, and tests/fixtures. `PolicyEvaluationService` is the only `policy_decisions` writer. Rule functions accept frozen facts plus registered `policy_version` and return reason codes; they have no I/O. Repositories assemble facts before evaluation.

### Two policy scopes and exact immutable basis

Approval and sending use two different decisions. `APPROVAL_ELIGIBILITY` may authorize only creation of a `PENDING` approval request; it cannot create an intent, consume an approval, reserve send capacity, enqueue, create an attempt, or call a provider. It deliberately excludes ApprovalRule because the approval row does not exist yet. Final `SEND` is always a new decision after operator approval and immediately before an attempt; it includes the approved row and current mutable safety/capacity facts.

`PolicyScopeV1` is the strict/frozen/extra-forbid discriminated scope union. Its only approval/send arm is `ApprovalBasisScopeV1` with literal `schema_version="policy.approval_basis.v1"` and exactly: experiment ID; campaign ID/version; `campaign_member_id`; lead ID; message ID/version/content hash; mailbox ID/provider-account hash; sorted general artifact ID/version/hash references; intended operation `SEND`; `max_send_count=1`; approval expiry; and exact immutable compliance references `recipient_identity_evidence_ref`, `jurisdiction_evidence_ref`, nullable `affirmative_consent_evidence_ref`, nullable `counsel_exception_evidence_ref`, `legal_review_ref`, `legal_policy_version`, `disclosure_sender_template_ref`, and `google_policy_review_ref`. Every `*_ref` is `{artifact_id,artifact_version,content_hash}` and byte-matches the accepted DB-04 artifact plus the DB-03 campaign-member columns. Exactly one of affirmative-consent or counsel-exception references is present. Its DB-01 envelope schema remains `policy.scope.approval_basis.v1`; the result is the immutable `scope_hash` copied byte-for-byte to the eligibility decision, approval, intent, final SEND decision, attempt, provider request, events, and audit. Any immutable content, recipient, evidence, legal-policy, sender/disclosure, or Google-review reference change requires a new eligibility decision and approval UUID.

`ApprovalEligibilityFactsV1` contains only that basis plus registered eligibility-policy/artifact-validation/configuration versions and immutable evidence hashes. Its DB-01 envelope is `policy.approval_eligibility.facts.v1`. It contains no approval state, suppression/control value, balance/counter, rate window, jurisdiction status, mutable campaign/message state, or clock-derived validity. An allowed eligibility decision therefore proves only that an exact review request may be created.

`SendPolicyFactsV1` contains the same immutable basis and `scope_hash`, plus exact approved row ID/state/decision/expiry validity/eligibility decision ID and basis hash; current experiment/campaign/member/lead/message/mailbox states and versions; active global/business/recipient suppression IDs; `PRODUCT_OUTREACH` and `TEST_INBOX_SENDING` values/versions; M1/M6 gate IDs/hashes; owned-test-alias match; budget account/reservation/current remaining amount; campaign daily/total/concurrency counts; send/reply window result; retry bounds/deadline; unresolved ambiguity; DBOS queue/limiter configuration; and locked `send_rate_reservations` window/slot/lease inputs.

Its compliance block is exact and mandatory: recipient identity status plus accepted evidence ref/retrieved/verified/expires timestamps; jurisdiction status/code plus accepted evidence ref/retrieved/published/expires timestamps; `authority_route=AFFIRMATIVE_CONSENT|COUNSEL_EXCEPTION`; consent status, captured/verified/expires timestamps and evidence ref when the consent arm is selected; counsel-exception decision/effective/expires timestamps and evidence ref when that arm is selected; legal-review ID/ref/status/effective/expires timestamps; legal policy version and current-version match; disclosure/sender identity template ID/version/content hash, validator version and validity; Google-policy review ID/ref/status/effective/expires timestamps and compatibility boolean; current reply/unsubscribe/hard-bounce/complaint booleans with sorted observation/reply evidence refs; soft-bounce count/limit/last-observed timestamp and evidence refs; and one injected `facts_observed_at`. Missing, null, conflicting, stale, superseded, future-dated, cross-recipient, or unaccepted evidence is an explicit denial, never absence-as-false. Its DB-01 envelope is `policy.send.facts.v1`. `campaign_member_id` is mandatory in both fact types and every policy scope/decision composite.

The two decisions must have the same `scope_hash` and may have different `facts_hash` values; equality of eligibility and final SEND facts hashes is forbidden because it would erase current mutable safety facts. `evaluated_at` remains decision metadata, not hashed facts. Empty/missing and JSON null are distinct.

`PolicyDecisionV1={policy_decision_id,scope,experiment_id,campaign_id,campaign_version,campaign_member_id,lead_id,message_id,mailbox_id,approval_id,policy_version,allowed,reason_codes,facts_schema_version,facts_json,facts_hash,scope_hash,correlation_id,idempotency_key,evaluated_at}` maps byte-for-byte to DB-05. Eligibility has `approval_id=null`; SEND requires the exact approved `approval_id`. The deterministic key is `policy:{scope}:{policy_version}:{scope_hash}:{facts_hash}`. Same scope/key/hash replays the same decision; a different request hash conflicts. `PolicyEvaluationService` inserts the decision, safe audit, and exact `policy.evaluated.v1` atomically.

### Scope-specific rule composition and reason codes

`APPROVAL_ELIGIBILITY` runs only these fixed rules: schema/version integrity; exact experiment/campaign/version/member/lead/message/mailbox relationship; immutable message content and accepted artifact references; registered eligibility policy/configuration; single-send cap; and expiry strictly after request time and within the configured maximum approval lifetime. It never runs ApprovalRule, suppression, controls, budget, rate, jurisdiction, send window, retry, or provider readiness. Its allowed result can be consumed only by `RequestApproval` in the same transaction.

Final `SEND` runs all applicable rules in this fixed order and collects every safe denial reason except where malformed authority makes further reads unsafe. Repositories lock the recipient/campaign/message, suppression, reply/provider-observation, policy/artifact-acceptance, control, budget, rate, and attempt rows and assemble facts at the same injected UTC instant; no queued or previously evaluated compliance fact is reusable:

1. identity/schema/version integrity including `campaign_member_id` and immutable basis hash;
2. ApprovalRule: exact approval exists, was operator-approved and is now `CONSUMED` exactly once by the unique current `send_intents.approval_id`, remains unexpired/unrevoked, cap one, and binds the eligibility decision/basis;
3. operator and global/test control plus M1/M6 evidence;
4. experiment/campaign/member/lead/message/mailbox canonical states and authority mode;
5. global, business, then recipient suppression;
6. verified recipient identity and exact identity-evidence binding;
7. confirmed jurisdiction and current jurisdiction evidence;
8. exactly one current authority route: affirmative consent or counsel-approved exception;
9. current legal review and exact legal-policy version;
10. validated disclosure/sender-identity template ID/version/hash;
11. current compatible Google-policy review;
12. reply, unsubscribe, hard-bounce, complaint, then soft-bounce-limit stop signals;
13. send/reply windows and campaign daily/total/concurrency caps;
14. budget reservation/account and provider cost ceiling;
15. application rate window/slot/concurrency lease and DBOS limiter configuration;
16. unresolved attempt/ambiguity and retry timing/attempt/deadline guards.

Exact `PolicyReasonCode` values are:

```text
AUTHORITY_TUPLE_MISMATCH, CAMPAIGN_MEMBER_MISMATCH,
APPROVAL_BASIS_MISMATCH, ELIGIBILITY_POLICY_DENIED,
OPERATOR_DISABLED, OUTREACH_DISABLED, TEST_INBOX_DISABLED,
M1_GATE_MISSING, M6_GATE_MISSING,
EXPERIMENT_STATE_INVALID, CAMPAIGN_STATE_INVALID, CAMPAIGN_VERSION_STALE,
LEAD_STATE_INVALID, MESSAGE_STATE_INVALID, MAILBOX_INACTIVE,
MAILBOX_AUTHORITY_INVALID, RECIPIENT_NOT_OWNED_TEST_ALIAS,
GLOBAL_SUPPRESSED, BUSINESS_SUPPRESSED, RECIPIENT_SUPPRESSED,
APPROVAL_MISSING, APPROVAL_NOT_APPROVED, APPROVAL_EXPIRED,
APPROVAL_REVOKED, APPROVAL_NOT_CONSUMED_BY_INTENT, APPROVAL_SCOPE_MISMATCH,
POLICY_VERSION_STALE, JURISDICTION_NOT_CONFIGURED,
RECIPIENT_IDENTITY_UNVERIFIED, RECIPIENT_JURISDICTION_UNKNOWN,
RECIPIENT_CONSENT_MISSING, RECIPIENT_CONSENT_EXPIRED,
COUNSEL_EXCEPTION_MISSING, LEGAL_REVIEW_MISSING, LEGAL_REVIEW_STALE,
DISCLOSURE_TEMPLATE_INVALID, GOOGLE_POLICY_DENIED,
RECIPIENT_REPLIED, RECIPIENT_OPTED_OUT, RECIPIENT_HARD_BOUNCED,
RECIPIENT_COMPLAINT, RECIPIENT_SOFT_BOUNCE_LIMIT,
SEND_WINDOW_CLOSED, REPLY_WINDOW_CLOSED,
DAILY_CAP_EXCEEDED, TOTAL_CAP_EXCEEDED, CONCURRENCY_CAP_EXCEEDED,
BUDGET_UNAVAILABLE, COST_CAP_EXCEEDED, RATE_LIMIT_EXCEEDED,
RATE_SLOT_CONFLICT, RATE_LEASE_ACTIVE,
UNRESOLVED_ATTEMPT, RETRY_NOT_DUE, RETRY_EXHAUSTED,
RETRY_DEADLINE_EXPIRED, FACTS_DIGEST_MISMATCH, SCOPE_DIGEST_MISMATCH.
```

Names are application API/event vocabulary; provider-native errors cannot appear. The dedicated compliance/signal codes above are mandatory and cannot be replaced by `AUTHORITY_TUPLE_MISMATCH`, `JURISDICTION_NOT_CONFIGURED`, free text, or a generic suppression code. An approved row, passing eligibility decision, `READY_FOR_OUTREACH`, `QUALIFIED`, mailbox eligibility, or a passing gate is individually insufficient for SEND.

### Approval-to-send sequence, suppression, rate, and errors

1. `RequestApproval` computes the immutable basis; evaluates `APPROVAL_ELIGIBILITY`; and, only if allowed, atomically inserts the eligibility decision, `PENDING` approval bound to its decision/basis/facts, `approval.requested.v1`, audit, idempotent result, and message transition. A denial inserts policy/audit/idempotent failure but no approval/event.
2. Operator approve/deny/revoke/expiry commands mutate only the approval/message lifecycle and canonical approval events. Eligibility cannot be refreshed in place; a stale basis requires a new request. Approval expiry/revocation prevents final SEND even if eligibility was allowed.
3. `RecordSendIntent` verifies an exact approved basis, creates the immutable unsent intent/stable RFC identity under unique `approval_id`, consumes the approval in the same transaction, reserves budget, queues after commit, but does not claim final SEND authority.
4. Last mile locks the full chain, rereads every compliance artifact acceptance/version/expiry and every reply/unsubscribe/bounce/complaint observation, rebuilds `SendPolicyFactsV1`, and records a new SEND decision. It never reuses the eligibility decision, queued facts, cached suppression, or a prior compliance decision and never requires the two facts hashes to match.
5. If the new SEND decision denies for suppression, one transaction commits policy denial, message `QUEUED -> SUPPRESSED`, `send.suppressed.v1`, one-way `send_intents.cancelled_at/cancellation_reason`, release of the unsent budget/queue reservation, safe audit/idempotent result/outbox, and zero `send_attempts`, rate reservations, or provider calls.
6. If SEND allows, the same serializable last-mile transaction locks the mailbox/window, inserts and consumes one `send_rate_reservations` slot/lease, inserts the attempt carrying that reservation and final decision, transitions `QUEUED -> SENDING`, emits `send.attempt_started.v1`, audit/idempotent result/outbox, and commits before the provider call. Unique slot/active-mailbox constraints choose one concurrent winner. DBOS remains the outer queue/limiter; PostgreSQL is the last-line capacity authority.

Eligibility denial maps to 403 `POLICY_DENIED`; stale/different immutable basis maps to 409 `VERSION_CONFLICT`; every final suppression/control/compliance/signal/approval denial maps to 403 `POLICY_DENIED` with its dedicated bounded reason; budget and rate capacity map to 429 `BUDGET_EXHAUSTED`/`RATE_LIMITED`; malformed authority maps to 409 `STATE_TRANSITION_DENIED`. Safe reason codes, accepted evidence reference IDs/versions/hashes, evidence timestamps/expiry, legal-policy/template/Google-review versions, and both policy decision IDs/hashes remain in restricted facts/audit/reporting. Provider requests carry only the resulting decision/scope/facts hashes and never the recipient/legal/consent payload.

### M6/later composition, races, and replacement

M6 final SEND requires `TEST_INBOX_SENDING=true`, `PRODUCT_OUTREACH=false`, exact owned-alias match, mailbox test authority, passing M1 evidence, an approved immutable basis, and all remaining rules. Later product SEND requires `PRODUCT_OUTREACH=true`, both M1/M6 evidence, experiment authority `BOUNDED_REAL_RECIPIENTS`, mailbox `PRODUCT_ELIGIBLE`, exact campaign/member/recipient/spend authority, approval, and every rule. Test control cannot satisfy product authority; enabling a control does not enqueue/send.

Use one injected UTC instant per evaluation. Time windows are half-open `[start,end)`. Rate facts come from locked PostgreSQL window/lease state, not logs or wall-clock guesses. A suppression/control/approval/budget/rate/jurisdiction change after queue changes the final SEND facts hash and can deny without mutating the immutable approval basis. A rule change creates a new policy version and fixtures; old decisions/approvals/intents remain immutable evidence and cannot be silently upgraded.

## Ordered implementation tasks

- [ ] **Encode eligibility/basis/SEND facts and reason registry —** Input: DB/ARCH/WF gates and exact names above. Operation: implement strict `APPROVAL_ELIGIBILITY` and final `SEND` schemas, shared immutable basis hash, independent facts hashes, `campaign_member_id`, rule/version registry, and reason enum. Output: pure policy package. Test evidence: eligibility-to-approval-to-final-SEND construction plus stale-basis/mutable-fact hash matrix. Failure behavior: no decision.
- [ ] **Implement deterministic rule composition —** Input: frozen facts/version. Operation: execute fixed ordered rules and collect sorted denial reasons without I/O. Output: reproducible allow/deny. Test evidence: exhaustive pairwise/boundary/property fixtures. Failure behavior: deny on unknown/incomplete fact.
- [ ] **Implement PolicyEvaluationService —** Input: fact assembly, scope, command key. Operation: verify hashes, replay/insert immutable decision plus audit/event atomically. Output: DB-05 policy authority. Test evidence: concurrency/replay/failure injection. Failure behavior: transaction rollback and side effect denied.
- [ ] **Implement last-mile SEND, suppression, and rate reservation —** Input: queued intent, approved basis, current rows, and DBOS admission. Operation: create a new SEND decision; commit suppression/no-attempt or consume one unique PostgreSQL rate lease with the attempt. Output: denied terminal suppression or exact pre-call authority. Test evidence: mutable-fact matrix, concurrent slot/lease, suppression event/no-call, and independent facts-hash tests. Failure behavior: no provider call/control enable.
- [ ] **Gate versions and operator explainability —** Input: frozen policy fixtures and report projection. Operation: reproduce decisions/reasons/hashes and show safe facts/reasons without PII. Output: M6 policy evidence. Test evidence: golden decision replay and redaction scan. Failure behavior: policy version not promoted.

## Test strategy

- **Unit `test_send_policy_rule_order_and_reason_enum_are_exact`:** every rule/reason accounted.
- **Property `test_same_facts_scope_version_produce_byte_same_decision_content`:** injected ID aside, canonical result matches.
- **Precedence `test_suppression_compliance_signals_and_controls_override_approval_qualification_and_gate_pass`:** no bypass.
- **Compliance `test_final_send_constructs_every_compliance_fact_and_each_dedicated_denial_fixture`:** identity, jurisdiction, consent/exception, legal review, disclosure/sender, Google policy, reply, opt-out, hard bounce, complaint, and soft-bounce limit each deny independently; generic reasons cannot substitute.
- **Concurrency `test_budget_rate_and_policy_admission_cannot_overbook`:** real PostgreSQL locks/reservations.
- **Recheck `test_mutable_fact_change_after_queue_prevents_gmail_call`:** exact new denial evidence.
- **Authority `test_policy_engine_has_no_provider_model_workflow_or_mutation_dependency`:** import/object graph.

## Security, privacy, compliance, idempotency, observability, and cost

Facts store necessary safe values and hashes; decrypted address/content and credentials are forbidden. Jurisdiction policy is versioned operator/legal configuration, not a compliance claim. Decision idempotency and canonical hashes make every allow/deny reproducible. Metrics expose policy/scope/version, allowed, safe reason counts, evaluation duration, stale decision, budget/rate utilization, and correlation—not sensitive facts. Policy cost is internal compute; it governs provider/spend reservations.

## Failure, rollback, and operator recovery

Unknown rule/version/reason, hash mismatch, impossible fact tuple, overbooking, or decision/event disagreement denies action, closes relevant dequeue/control, and opens an incident when safety is uncertain. Rollback activates the prior policy version only for new evaluations; stale approvals/intents require re-approval/new intent rather than mutation. Operators inspect safe decision facts/events and use audited commands, never SQL or reason suppression.

## Acceptance and retained evidence

- [ ] Every side-effect scope has exact frozen facts/scope/hash/version and one deterministic decision owner.
- [ ] Rule order/reasons and M6/product authority are explicit, exhaustive, and fail-closed.
- [ ] Last-mile changes cannot reuse stale approval/policy authority.
- [ ] Engine has no provider/mutation/model authority and records exact canonical policy event/audit.

Retain facts/scope schemas, digest vectors, reason/rule registry, golden policy fixtures, PostgreSQL concurrency/replay traces, last-mile race matrix, M1/M6/control evidence denials, safe explainability/redaction scan, and promotion/rollback record.

## Dependencies and next deliverable

BACKEND-03 depends on DB-03/05 and BACKEND-01. It unlocks [BACKEND-04 SendGateway](04-send-gateway.md) and [BACKEND-05 approval/control handlers](05-approval-and-command-handling.md); an allowed decision alone grants no external effect.
