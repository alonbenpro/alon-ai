# Deterministic Action and Commercial Policy Engine

**Document ID:** BACKEND-03
**Status:** Planned M3 pure commercial/policy contracts and M6 final-effect implementation; only a minimal asynchronous `SendPolicy` protocol exists today
**Milestone:** M3, M6, M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `BACKEND-03-T01 -> BACKEND-03-T02 -> BACKEND-03-T03 -> BACKEND-03-T04 -> BACKEND-03-T05`; cross-document task Inputs `BACKEND-03-T01 <- DB-05-T02,ARCH-03-T01,DB-03-T01; BACKEND-03-T04 <- SEC-05-T03,BACKEND-05-T03; BACKEND-03-T05 <- BACKEND-06-T02,BACKEND-06-T04`. Descriptive source authorities/resources (not whole-document completion dependencies): [ARCH-03 policy events](../01-architecture/03-domain-events-and-state-machines.md#policy-action-authorization-sending-and-replies), [DB-03](../02-database/03-leads-campaigns-and-messages.md), [DB-05](../02-database/05-audit-events-and-idempotency.md), and BACKEND-01
**Outputs:** Versioned policy facts/scope/hash, exact reason taxonomy, deterministic composition order, immutable decisions, and fail-closed re-evaluation
**Unlocks:** M6 campaign admission, [BACKEND-04 SendGateway](04-send-gateway.md), and control enablement
**Risk:** Critical
**Complexity:** L


## Outcome and current repository state

PolicyEvaluationService persists decisions; all rule functions and CommercialPolicyEngine are pure deterministic code over stored versioned values with injected time. Only the foundation asynchronous SendPolicy protocol exists today. There is no product policy, commercial engine, action authorization or booking write.

Normal in-envelope actions run without individual operator approval. An immutable action scope binds one proposed effect and fresh gateway checks decide whether it can execute now. Missing/stale/ambiguous/unsafe/out-of-envelope facts deny and enter an exception. No model, UI, workflow or global-learning strategy can loosen safety/legal/source/suppression/commercial bounds.

## Exact scope and facts contract

ActionAuthorityScopeV1 is defined in [DB-03](../02-database/03-leads-campaigns-and-messages.md#immutable-action-authorization-and-send-schema). It binds action kind/ID/version/content/materialization, experiment/campaign/cohort/member, exact recipient/business/contact/conversation/thread, mailbox/calendar, accepted offer/version/hash, global package/agent strategy/activation, accepted evidence, commercial decision, policy rules and creation facts, expiry, single-effect cap and control/checkpoint generations.

ACTION_CREATION validates this immutable envelope and current required facts and allows ActionAuthorizationService to create an authorization. It cannot itself create an attempt or call a provider. There is no circular rule requiring a preexisting authorization to create one. The resulting authorization's lifecycle and unique consumption refer to the creation decision. SEND and BOOKING require that exact consumed authorization, reassemble all current facts and append a new decision immediately before their own provider attempts.

PolicyFactsV1 common fields are schema_version, scope, action/scope_hash, exact accepted input refs, rule/config versions, control/checkpoint generations, facts_observed_at, actor validity, expected aggregate versions, current state/expiry/supersession flags, offer/strategy/activation/hash matches, commercial_decision_id/hash, source_scope_version, suppression matches, current counters/windows, budget reservations, rate leases, provider readiness, ambiguity/retry evidence and all applicable kill controls. Facts are immutable/encrypted at rest; absent/null/unknown/future-dated/conflicting evidence is never absence-as-false.

SEND adds recipient identity status and accepted evidence/ref/retrieved/verified/expires times; jurisdiction status/code and accepted evidence/ref/retrieved/published/expires times; authority_route AFFIRMATIVE_CONSENT or COUNSEL_EXCEPTION with exactly the selected accepted evidence/timestamps; legal review status/effective/expiry and current legal-policy version; disclosure/sender template ID/version/hash/validator; Google-policy review status/compatibility/effective/expiry; current reply/unsubscribe/hard-bounce/complaint/soft-bounce count/threshold and exact observations; current conversation state/version/thread hash, cold stop, reply objective, round/message/frequency counters, negative sentiment/terminal stop; send/reply half-open windows; mailbox/recipient mode and owned alias test match; fresh stage/cumulative/unique-recipient counts; rate slot/lease and finite retry evidence.

An observed reply denies INITIAL_EMAIL via COLD_SEQUENCE_STOPPED. It does not blanket-deny REPLY_EMAIL: a newly accepted response objective, allowed conversation state and all current guards can allow the response. Decline stops persuasion; unsubscribe/no-future-contact/legal/bounce/complaint suppression and negative-sentiment stop win before any response. Generic RECIPIENT_REPLIED is an observation reason, never a permanent suppression predicate.

BOOKING adds qualified buying intent, accepted call-agreement/BookingIntent refs, optional purchase-acceptance ref, explicit slot confirmation/span, calendar account, allowed timezone/tzdb/UTC/offset/duration, fresh availability result/expiry, action kind and expected event/ETag, attendee set/notification mode/hash, booking policy, calendar lease and provider outcome ambiguity. CREATE/RESCHEDULE requires explicit exact confirmation; CANCEL requires a separate lead request or authorized operator/policy reason. A call may proceed for qualified INTERESTED/NEGOTIATING without purchase acceptance.

A decision binds policy_decision_id, scope/action/scope_hash, exact versioned facts/hash, allowed and sorted bounded reason_codes, rule_version, governing action attribution, correlation/idempotency and evaluated_at. Key = policy:<scope>:<rule_version>:<scope_hash>:<facts_hash>. Same bytes replay; changed bytes conflict. RFC 8785 envelope hashing follows DB-01. Creation and final facts may differ; equality is never required. The same scope hash proves fixed intent, while changed current facts may block it.


Creation hashing is acyclic: ActionProposalScopeV1 (action.proposal.scope.v1) contains immutable action/context/evidence/commercial fields and expiry/generations but excludes the creation decision/facts and final authority hash. Compute action_basis_hash first; ACTION_CREATION facts contain that basis hash, and its policy_decision.scope_hash is the basis hash. ActionAuthorizationService then builds ActionAuthorityScopeV1 from the basis plus exact creation decision ID/rules/facts_hash and computes the final authority scope_hash. SEND/BOOKING facts use that completed scope_hash. No hash includes its own digest/result, and creation-scope equality with final authority scope is not required.

M3 T01..T03 implements pure contracts, CommercialPolicyEngine and immutable policy recording against synthetic/recorded fixtures so M4 OfferPackage acceptance can verify economics. M6 T04 adds current live-state fact assembly and gateway policy handoff. This early implementation grants no provider write, control enable or real-recipient authority.

## Fixed final effect rule order and reason taxonomy

1. strict schema/digest and exact identity/content/member/thread/offer/activation scope;
2. authorization state/expiry/unique intent consumption and generation;
3. authenticated service, independent environment and scoped kill controls, earned M1/M6/M9 evidence;
4. canonical experiment/campaign/cohort/member/conversation/message/calendar/mailbox state;
5. current global/business/recipient suppression and cold/terminal/negative-sentiment stops;
6. identity/jurisdiction/consent-or-counsel/legal/template/provider/source evidence;
7. offer validity, claim coverage and fresh commercial engine decision;
8. phase/final qualification, bounded conversation rounds/message/frequency/expiry or booking confirmation/availability;
9. exact stage increments/cumulative ceiling/unique membership and prior CONTINUE;
10. budget, provider/call/token/cost and mailbox/calendar rate/concurrency reservations;
11. retry deadline/count and unresolved effect; conflict/ambiguity cannot authorize another call.

Every failure has a bounded reason; never replace a specific compliance denial with free text. Required reasons include AUTHORITY_TUPLE_MISMATCH, CAMPAIGN_MEMBER_MISMATCH, THREAD_IDENTITY_MISMATCH, CONTENT_STALE, AUTHORIZATION_MISSING, AUTHORIZATION_EXPIRED, AUTHORIZATION_REVOKED, AUTHORIZATION_NOT_CONSUMED_BY_INTENT, CONTROL_GENERATION_STALE, CHECKPOINT_GENERATION_STALE, OFFER_STALE, STRATEGY_ACTIVATION_STALE, COMMERCIAL_POLICY_DENIED, CLAIM_EVIDENCE_MISSING, FINAL_QUALIFICATION_MISSING, COLD_SEQUENCE_STOPPED, CONVERSATION_TERMINAL, NEGATIVE_SENTIMENT_STOP, ROUND_LIMIT_REACHED, MESSAGE_LIMIT_REACHED, FREQUENCY_LIMIT_REACHED, BOOKING_CONFIRMATION_MISSING, BOOKING_SLOT_STALE, SLOT_UNAVAILABLE, CALENDAR_IDENTITY_MISMATCH, CALENDAR_EVENT_CONFLICT.

Preserve OPERATOR_DISABLED, OUTREACH_DISABLED, TEST_INBOX_DISABLED, M1_GATE_MISSING, M6_GATE_MISSING, EXPERIMENT_STATE_INVALID, CAMPAIGN_STATE_INVALID, CAMPAIGN_VERSION_STALE, LEAD_STATE_INVALID, MESSAGE_STATE_INVALID, MAILBOX_INACTIVE, MAILBOX_AUTHORITY_INVALID, RECIPIENT_NOT_OWNED_TEST_ALIAS, GLOBAL_SUPPRESSED, BUSINESS_SUPPRESSED, RECIPIENT_SUPPRESSED, POLICY_VERSION_STALE, JURISDICTION_NOT_CONFIGURED, RECIPIENT_IDENTITY_UNVERIFIED, RECIPIENT_JURISDICTION_UNKNOWN, RECIPIENT_CONSENT_MISSING, RECIPIENT_CONSENT_EXPIRED, COUNSEL_EXCEPTION_MISSING, LEGAL_REVIEW_MISSING, LEGAL_REVIEW_STALE, DISCLOSURE_TEMPLATE_INVALID, GOOGLE_POLICY_DENIED, RECIPIENT_OPTED_OUT, RECIPIENT_HARD_BOUNCED, RECIPIENT_COMPLAINT, RECIPIENT_SOFT_BOUNCE_LIMIT, SEND_WINDOW_CLOSED, REPLY_WINDOW_CLOSED, DAILY_CAP_EXCEEDED, TOTAL_CAP_EXCEEDED, CONCURRENCY_CAP_EXCEEDED, BUDGET_UNAVAILABLE, COST_CAP_EXCEEDED, RATE_LIMIT_EXCEEDED, RATE_SLOT_CONFLICT, RATE_LEASE_ACTIVE, UNRESOLVED_ATTEMPT, RETRY_NOT_DUE, RETRY_EXHAUSTED, RETRY_DEADLINE_EXPIRED, FACTS_DIGEST_MISMATCH and SCOPE_DIGEST_MISMATCH. Add CALENDAR_WRITES_DISABLED and TEST_CALENDAR_DISABLED for independent calendar controls.

Denials map to 403 POLICY_DENIED with safe specific reasons; stale expected version/generation/content -> 409 VERSION_CONFLICT; malformed identity/state -> 409 STATE_TRANSITION_DENIED; unresolved send -> 409 AMBIGUOUS_SEND_REQUIRES_RECONCILIATION; budget/rate -> 429 BUDGET_EXHAUSTED/RATE_LIMITED. No denial serializes sensitive facts or provider-native errors.

## Pure CommercialPolicyEngine contract

CommercialInputsV1 contains accepted immutable OfferPackage/economics/version/hash, selected approved variant/pilot/bundle, permitted discount band and eligibility evidence, typed objective, exact budget assertion, approved delivery-cost assumptions, fee/tax/FX/rounding versions, timing and payment schedule, accepted claim evidence, current conversation counters/state and injected UTC instant. Proposed prices/margins are untrusted suggestions. The engine recalculates authoritative amounts.

Allowed objectives are EXPLAIN_OFFER, ANSWER_SUPPORTED_OBJECTION, SELECT_APPROVED_VARIANT, OFFER_APPROVED_PILOT, SELECT_APPROVED_DISCOUNT, ADJUST_APPROVED_TIMING, SELECT_APPROVED_BUNDLE, SELECT_APPROVED_PAYMENT_SCHEDULE, ASK_DECISION_INFORMATION, PROPOSE_CALL. Even explanatory/non-discount actions receive a decision binding the current authoritative terms. A new legal term, unsupported guarantee/proof/deliverable, fabricated urgency/familiarity/budget or unaccepted commitment is denied.

Money uses integer minor units, explicit ISO currency and rational/Decimal intermediates, never binary floats. RoundingVersionV1 uses ROUND_HALF_UP at each declared monetary boundary; percentages are integer basis points. For the selected immutable variant:

- discounted quote = round_half_up(base_quote_minor * (10000 - discount_bps) / 10000);
- if tax-exclusive, net = quote and tax = round_half_up(net * tax_bps / 10000); gross = net + tax;
- if tax-inclusive, net = round_half_up(quote * 10000 / (10000 + tax_bps)); gross = quote; tax = gross - net;
- variable fee = ceil(gross * variable_fee_bps / 10000), fees = fixed_fee_minor + variable fee;
- contribution = net - delivery_cost_minor - fees;
- minimum-price check compares net to the package/variant net minimum; margin-floor check is exact contribution * 10000 >= net * floor_bps, without rounding a ratio for authority;
- display margin_bps = floor(contribution * 10000 / net); payment instalments sum exactly to gross, with residual minor units assigned to the final permitted instalment;
- FX uses an unexpired stored exact rate numerator/denominator with source/time/version; convert cost/budget into offer currency using the registered conservative conversion direction before the above formulas. Unknown currency/rate/cost denies; no live quote or inferred rate.

Tax/fee/cost treatment changes require a new economics version outside an active cohort. All discount and pilot boundaries apply even if the buyer states a larger budget. Only a STATED assertion with exact lead source span/currency/range can satisfy a stated-budget predicate; INFERRED and UNKNOWN fail that predicate and are never rendered as what the lead said.

### Normative pure test vectors

Fixture base: ILS minor units; tax-exclusive base quote 100000; minimum net 85000; delivery 40000; fixed fee 1000; variable fee 300 bps of gross; tax 1800 bps; margin floor 5000 bps; allowed discount band max 1500 bps; exact approved scope/payment terms.

| Case | Exact expected result |
| --- | --- |
| 1000 bps discount | net 90000; tax 16200; gross 106200; variable fee 3186; fees 4186; contribution 45814; display margin 5090 bps; ALLOW if all other guards pass |
| 1500 bps discount | net 85000; tax 15300; gross 100300; fees 4009; contribution 40991; display margin 4822 bps; DENY MARGIN_FLOOR despite valid band/minimum |
| 1501 bps discount | DENY DISCOUNT_BAND_EXCEEDED before inventing a band |
| zero tax/fees, net 10000, delivery 5000, floor 5000 | equality ALLOW; delivery 5001 DENY MARGIN_FLOOR |
| minimum net 85000, candidate net 84999 | DENY MINIMUM_PRICE; a rounded UI value cannot allow |
| tax-inclusive quote 118000 at 1800 bps | net 100000; tax 18000; gross 118000 |
| quote 101 with 5000 bps discount | rounded quote 51; split approved gross 101 into two instalments 50/51; exact sum preserved |
| stated budget condition with same numeric range | STATED + valid span ALLOW predicate; INFERRED or UNKNOWN DENY STATED_BUDGET_REQUIRED; missing span/currency DENY BUDGET_EVIDENCE_INVALID |
| stored USD->ILS rate 7/2, 100 USD minor units | 350 ILS minor units; expired/missing/inverse mismatch rate DENY FX_EVIDENCE_INVALID |
| requested legal clause or new deliverable | DENY UNAUTHORIZED_TERMS/SCOPE_CHANGE even if price/margin pass |

NegotiationDecision persists input/result hashes, all monetary outputs and governing rule/offer/strategy/activation/evidence versions through CommercialDecisionService in the caller's unit of work. CommercialPolicyEngine itself has no database/provider/model dependency. Agent confidence cannot override denial.

## Races, replacement and bounded operation

Gateways lock current controls, source/legal acceptance, conversation/recipient/thread, offer/activation, cohort/capacity, budget/rate and attempts, then use one injected UTC instant. Authority creation/consumption and final policy read current generation; reply/control/checkpoint/rollback changes invalidate queued actions. A rule change creates a new immutable version and fixtures; prior decisions remain history.

M6 Gmail requires TEST_INBOX_SENDING=true and PRODUCT_OUTREACH=false, owned aliases and current pilot/M1 evidence; calendar tests require TEST_CALENDAR_WRITES=true and CALENDAR_WRITES=false with owned test calendar/attendees. Product Gmail/calendar additionally require independently earned legal/provider/security/launch evidence and their product control. No control, accepted offer, qualification, booking intent or strategy approval independently authorizes an effect.

## Ordered implementation tasks

<!-- roadmap-task id=BACKEND-03-T01 milestone=M3 depends_on=DB-05-T02,ARCH-03-T01,DB-03-T01 mode=parallel locks=backend-domain -->
- [ ] **Encode action/fresh-gateway facts and reason registry —** Input: DB-03 ActionAuthorityScopeV1, DB-05 policy and canonical offer/cohort/strategy contracts. Operation: implement strict ACTION_CREATION, SEND, BOOKING, COMMERCIAL, CHECKPOINT and STRATEGY schemas with immutable scope and independent fresh facts hashes. Output: pure policy interfaces and denial enum. Test evidence: scope/generation/recipient/thread/offer/activation splice and mutable-fact hash matrix. Failure behavior: deny unknown/incomplete facts before provider composition.
<!-- roadmap-task id=BACKEND-03-T02 milestone=M3 depends_on=BACKEND-03-T01 mode=parallel locks=backend-domain -->
- [ ] **Implement CommercialPolicyEngine and deterministic rule composition —** Input: accepted OfferPackage/economics/variants, typed proposal, STATED/INFERRED/UNKNOWN budget and stored tax/fee/cost/FX/rounding versions. Operation: implement the pure formulas, allowed objectives, exact boundary comparisons and prohibited-change checks below; return NegotiationDecision through the single persistence handler. Output: versioned CommercialPolicyEngine interface and deterministic calculated result, with no model arithmetic or provider calls. Test evidence: exact monetary vectors, one-unit floor boundaries, stated-budget/source-splice and scope/legal/guarantee negatives. Failure behavior: return typed denial and retain current commercial envelope.
<!-- roadmap-task id=BACKEND-03-T03 milestone=M3 depends_on=BACKEND-03-T02 mode=parallel locks=backend-domain -->
- [ ] **Implement PolicyEvaluationService —** Input: fact assembly, scope, command key. Operation: verify hashes, replay/insert immutable decision plus audit/event atomically. Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority. Test evidence: concurrency/replay/failure injection. Failure behavior: transaction rollback and side effect denied.
<!-- roadmap-task id=BACKEND-03-T04 milestone=M6 depends_on=BACKEND-03-T03,SEC-05-T03,BACKEND-05-T03 mode=parallel locks=backend-domain -->
- [ ] **Implement last-mile SEND, suppression, and rate reservation —** Input: queued intent, immutable ActionAuthorityScopeV1, current rows, and DBOS admission. Operation: assemble current locked facts and evaluate fresh SEND/BOOKING policy; hand the result to BACKEND-04 or BACKEND-01-T08 for their sole attempt/rate/state transaction, never create another transaction owner. Output: denied terminal suppression or exact pre-call authority. Test evidence: mutable-fact matrix, concurrent slot/lease, suppression event/no-call, and independent facts-hash tests. Failure behavior: no provider call/control enable.
<!-- roadmap-task id=BACKEND-03-T05 milestone=M7 depends_on=BACKEND-03-T04,BACKEND-06-T02,BACKEND-06-T04 mode=parallel locks=backend-domain -->
- [ ] **Gate versions and operator explainability —** Input: frozen policy fixtures and report projection. Operation: reproduce decisions/reasons/hashes and show safe facts/reasons without PII. Output: M6 policy evidence. Test evidence: golden decision replay and redaction scan. Failure behavior: policy version not promoted.


## Verification, failure and acceptance

Retain pure exact arithmetic vectors plus property boundaries for overflow, rounding, inclusive tax, fee base, installment residual, FX direction/expiry and budget source distinction. Reproduce scope/facts/result hashes independently. Test every mandatory denial, pairwise stop/authority priority and late mutable-fact race. Prove direct/transitive imports contain no provider/model/database in rule functions and no authoritative UI arithmetic.

Missing/unknown facts deny, preserve safe reason/evidence and create an exception or incident as applicable. Suppression and kill always win. Rollback selects a compatible prior rule only for new evaluations; stale actions require new authority and never mutation. [SendGateway](04-send-gateway.md), [action commands](05-approval-and-command-handling.md) and [booking services](01-domain-services.md) own their transactions.
