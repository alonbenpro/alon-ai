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

### Exact facts, hashes, and decision contract

`PolicyFactsV1` is strict/frozen/extra-forbid with literal `schema_version="policy.facts.v1"`. SEND facts contain: experiment ID/state/version/authority level and M1/M6 evidence IDs+hashes; campaign ID/version/state/policy version/window-open result/window version/caps/requested units; lead ID/state/business ID; message ID/state/version/content hash; mailbox ID/status/authority mode/provider-account hash; recipient hash and owned-test-alias-manifest hash/match; approval ID/state/scope hash/policy/facts hashes/expiry-valid result/max count; active global/business/recipient suppression IDs; `PRODUCT_OUTREACH` and `TEST_INBOX_SENDING` values/versions; jurisdiction configuration version/result/evidence; budget account ID/version/limit/currency/requested amount; rate-policy version/window/cap/requested units and queue-admission configuration hash; retry-policy version/max attempts/deadline-valid result and unresolved-ambiguity result; actor and correlation IDs. `evaluated_at`, live counters, remaining balances, and incidental timestamps are decision metadata or separately locked capacity observations, not hashed policy facts; their inclusion would make an otherwise unchanged exact-scope decision unreplayable. Non-SEND scopes use the registered strict subset, never JSON omission with ambiguous meaning.

`facts_hash` is DB-01 lowercase SHA-256 over RFC 8785 UTF-8 `{"schema_version":"policy.facts.v1","payload":facts_without_schema_version}`. `PolicyScopeV1` for SEND contains exactly experiment/campaign-version/lead/message/mailbox/approval/artifact-version refs plus intended operation `SEND`; `scope_hash` uses schema `policy.scope.send.v1`. Empty/missing and JSON null are distinct and validated before evaluation.

`PolicyDecisionV1={policy_decision_id,scope,policy_version,allowed,reason_codes,facts_schema_version=1,facts_json,facts_hash,scope_hash,correlation_id,idempotency_key,evaluated_at}` maps byte-for-byte to DB-05. `idempotency_key="policy:{scope}:{policy_version}:{scope_hash}:{facts_hash}"`. Same inputs replay the same decision ID/result. Reason codes are sorted unique ASCII; allowed has an empty tuple, denied has at least one. The service inserts `policy_decisions`, safe audit, and exact `policy.evaluated.v1` in one transaction; it does not change message/campaign/control.

### Exact rule composition and reason codes

Every SEND evaluation runs all applicable rules in this fixed order and returns every denial reason; it does not short-circuit evidence collection except when the authority tuple itself is malformed and further reads would be unsafe.

1. identity/schema/version integrity;
2. operator and global/test control plus M1/M6 evidence;
3. experiment/campaign/lead/message/mailbox canonical states and authority mode;
4. exact campaign-member-message-mailbox-approval-policy scope tuple;
5. global, business, then recipient suppression;
6. approval state, expiry, cap, content/artifact/policy/facts scope;
7. jurisdiction/configuration evidence;
8. send/reply windows, campaign daily/total/concurrency caps;
9. budget reservation/account and provider cost ceiling;
10. application rate window/cap/reservation;
11. unresolved attempt/ambiguity and retry timing/attempt/deadline guards.

Exact `PolicyReasonCode` values are:

```text
AUTHORITY_TUPLE_MISMATCH, OPERATOR_DISABLED, OUTREACH_DISABLED,
TEST_INBOX_DISABLED, M1_GATE_MISSING, M6_GATE_MISSING,
EXPERIMENT_STATE_INVALID, CAMPAIGN_STATE_INVALID, CAMPAIGN_VERSION_STALE,
LEAD_STATE_INVALID, MESSAGE_STATE_INVALID, MAILBOX_INACTIVE,
MAILBOX_AUTHORITY_INVALID, RECIPIENT_NOT_OWNED_TEST_ALIAS,
GLOBAL_SUPPRESSED, BUSINESS_SUPPRESSED, RECIPIENT_SUPPRESSED,
APPROVAL_MISSING, APPROVAL_NOT_APPROVED, APPROVAL_EXPIRED,
APPROVAL_REVOKED, APPROVAL_SCOPE_MISMATCH, POLICY_VERSION_STALE,
JURISDICTION_NOT_CONFIGURED, SEND_WINDOW_CLOSED, REPLY_WINDOW_CLOSED,
DAILY_CAP_EXCEEDED, TOTAL_CAP_EXCEEDED, CONCURRENCY_CAP_EXCEEDED,
BUDGET_UNAVAILABLE, COST_CAP_EXCEEDED, RATE_LIMIT_EXCEEDED,
UNRESOLVED_ATTEMPT, RETRY_NOT_DUE, RETRY_EXHAUSTED,
RETRY_DEADLINE_EXPIRED, FACTS_DIGEST_MISMATCH, SCOPE_DIGEST_MISMATCH.
```

Names are application API/event vocabulary; provider-native errors cannot appear. `READY_FOR_OUTREACH`, `QUALIFIED`, `APPROVED`, mailbox `PRODUCT_ELIGIBLE`, an allowed earlier policy decision, or a passing gate is individually insufficient.

### M6 and later authority composition

M6 test send requires `TEST_INBOX_SENDING=true`, `PRODUCT_OUTREACH=false`, exact owned-alias match, mailbox `TEST_INBOX_ONLY` or otherwise explicitly test-eligible, passing M1 evidence, and all remaining rules. It never requires or permits product outreach true.

Later product send requires `PRODUCT_OUTREACH=true`, both M1 and M6 evidence IDs/hashes, experiment authority `BOUNDED_REAL_RECIPIENTS`, mailbox `PRODUCT_ELIGIBLE`, exact recipient/campaign/spend authority, and every remaining rule. `TEST_INBOX_SENDING` cannot satisfy product authority. Enabling product control is a separate authenticated CONTROL policy/command and does not enqueue/send anything.

Provider policy uses the same deterministic engine for operation enablement, provider allowlist/version, source domains, data/terms status, budget/rate, and sensitive-data class. It records scope `PROVIDER` but cannot widen AGENT-01 capability schemas/errors/ceilings.

### Re-evaluation, races, time, and replacement

Campaign admission evaluates and stores the decision referenced by an approval/intent. Immediately before Gmail, BACKEND-04 rebuilds the decision-relevant normalized facts under lock at a new `evaluated_at`. It may replay the exact `policy_decision_id` only when `policy_version`, `scope_hash`, and `facts_hash` byte-match and the decision remains allowed. Separately locked live budget reservation, rate capacity, campaign counts, time-window edge, and unresolved-attempt observations must also pass before the attempt transaction; they cannot grant authority or be smuggled into a different policy decision. Any decision-relevant fact change denies and records a new denied decision, while the immutable intent/attempt remains bound to its original allowed decision. Suppression/control changes after queue but before call therefore block.

Use the injected UTC clock once per evaluation. Time windows use half-open `[start,end)` and explicit timezone conversions from stored UTC; no local system timezone. Rate facts come from locked PostgreSQL reservations, not log counts or wall-clock guesses. A rule change creates a new immutable `policy_version` and fixtures; in-flight approvals/intents with stale facts cannot be silently upgraded.

## Ordered implementation tasks

- [ ] **Encode facts/scope/reason registry —** Input: DB/ARCH/WF gates and exact names above. Operation: implement strict scope-specific schemas, DB-01 hashes, rule/version registry, and reason enum. Output: pure policy package. Test evidence: schema/digest/reason snapshots and unknown-version denial. Failure behavior: no decision.
- [ ] **Implement deterministic rule composition —** Input: frozen facts/version. Operation: execute fixed ordered rules and collect sorted denial reasons without I/O. Output: reproducible allow/deny. Test evidence: exhaustive pairwise/boundary/property fixtures. Failure behavior: deny on unknown/incomplete fact.
- [ ] **Implement PolicyEvaluationService —** Input: fact assembly, scope, command key. Operation: verify hashes, replay/insert immutable decision plus audit/event atomically. Output: DB-05 policy authority. Test evidence: concurrency/replay/failure injection. Failure behavior: transaction rollback and side effect denied.
- [ ] **Implement last-mile re-evaluation and control/provider scopes —** Input: queued intent or provider/control request plus current rows. Operation: rebuild exact facts and reject stale/different authority. Output: allowed same-scope decision or explicit denial. Test evidence: changed suppression/approval/control/gate/window/budget/rate matrix. Failure behavior: no provider call/control enable.
- [ ] **Gate versions and operator explainability —** Input: frozen policy fixtures and report projection. Operation: reproduce decisions/reasons/hashes and show safe facts/reasons without PII. Output: M6 policy evidence. Test evidence: golden decision replay and redaction scan. Failure behavior: policy version not promoted.

## Test strategy

- **Unit `test_send_policy_rule_order_and_reason_enum_are_exact`:** every rule/reason accounted.
- **Property `test_same_facts_scope_version_produce_byte_same_decision_content`:** injected ID aside, canonical result matches.
- **Precedence `test_suppression_and_controls_override_approval_qualification_and_gate_pass`:** no bypass.
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
