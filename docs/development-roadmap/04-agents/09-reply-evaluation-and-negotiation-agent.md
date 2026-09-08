# Reply Evaluation, Negotiation, and Conversation Control Agent

**Document ID:** AGENT-08
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `AGENT-08-T01 -> AGENT-08-T02 -> AGENT-08-T03 -> AGENT-08-T04`; cross-document task Inputs `AGENT-08-T01 <- AGENT-03-T01,AGENT-07-T01,AGENT-10-T01,AGENT-01-T01,DB-03-T04; AGENT-08-T02 <- AGENT-01-T02; AGENT-08-T03 <- AGENT-01-T04,BACKEND-01-T01,DB-04-T04,OBS-03-T02; AGENT-08-T04 <- AGENT-10-T03,AGENT-10-T04`. Source authorities: [canonical product contract](../00-product-strategy/01-product-scope.md#canonical-autonomous-sales-contract), [module boundaries](../01-architecture/02-module-boundaries.md), [runtime](01-agent-runtime-and-contracts.md), and [shared evaluation](12-agent-evals-and-versioning.md).
**Outputs:** ReplyEvaluation and NegotiationDecision (materialized by CommercialPolicyEngine)
**Unlocks:** [Email Writing](08-email-writing-agent.md) for a bounded response or [Booking](../03-workflows/07-booking-workflow.md)
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Produces a precise objective and proposal. CommercialPolicyEngine alone computes/accepts NegotiationDecision from stored versions and the immutable OfferPackage. It rejects below-minimum price or margin, unauthorized deliverables/legal terms/guarantees and unsupported claims. Any inbound reply has already stopped the cold sequence. Questions and genuine objections may continue within round/message/frequency/time bounds; clear rejection closes persuasion and cannot be relabeled as an objection. Durable suppression requires PRODUCT-01 DurableSuppressionTriggerV1; ordinary reply or offer decline is insufficient. Ambiguous/unsafe intent enters PAUSED/exception. A proposal or inferred budget is not a commitment. PURCHASE_PROPOSAL acceptance alone permits COMMITTED; CALL_NEXT_STEP agreement may enter BOOKING_PENDING from qualified INTERESTED/NEGOTIATING without purchase acceptance, but calendar writing still needs exact slot confirmation.

Filename order is presentation. Stable Document ID/task prefixes survive renames; accepted artifact references and deterministic state guards enforce runtime order. M3 implements this contract against signed fixtures; product runtime and live authority belong to later workflow/provider gates.

## Current repository state and implementation surfaces

This agent, its canonical artifacts, prompt, validator, fixtures and promotion do not exist today. Plan `backend/src/alon_ai/agents/reply_evaluation.py`, `agents/prompts/reply_evaluation/v1.md`, a deterministic post-validator and `backend/tests/fixtures/evals/reply_evaluation/v1/`. Services own persistence and transitions.

## Exact input/output contract

Input: Accepted OfferPackage, ConversationStrategy and last EmailDraft refs; complete sanitized conversation snapshot/hash, inbound observation identities/spans, final qualification, current counters/limits, commercial calculation inputs and strategy activation.

All inputs use AGENT-01 strict/frozen extra-forbid schemas. Every canonical output carries immutable artifact ID, schema version, producer, producer strategy version, its own input snapshot ID/hash, output hash, evidence refs, created timestamp, disposition and supersession linkage. Every consumer pins accepted upstream versions/hashes, governing GlobalStrategyPackage and StrategyActivation. Workflow correlation does not force independent agent snapshots to share a hash.

| Field group | Required content and validator rule |
| --- | --- |
| ReplyEvaluation | Conversation/thread version/hash, input draft/offer refs, classifications, evidence spans, confidence and contradictions |
| classification | POSITIVE, QUESTION, OBJECTION, REJECTION, OPT_OUT, COMPLAINT, BOUNCE, OUT_OF_OFFICE, OTHER or UNCERTAIN; deterministic signals outrank model classification |
| next objective | Exactly one of EXPLAIN_OFFER, ANSWER_OBJECTION, SELECT_APPROVED_VARIANT, OFFER_APPROVED_PILOT, APPLY_APPROVED_DISCOUNT, ADJUST_ALLOWED_TERMS, ASK_DECISION_INFORMATION, PROPOSE_CALL, PRESENT_SLOTS, CONFIRM_BOOKING, STOP or ESCALATE |
| writer instructions | Specific question/objection, permitted claim refs, proposal/variant/band IDs, required response constraints and conversation counters |
| budget assertion | STATED/INFERRED/UNKNOWN; currency, range, source span, confidence and timestamp; only STATED satisfies a stated-budget predicate |
| proposed negotiation | Allowed action/variant/pilot/discount/timing/bundle/payment refs, never arbitrary new price/scope/legal text |
| NegotiationDecision | Deterministic allowed/denied result, exact computed terms, offer refs, tax/fee/cost/FX/rounding versions, floor/margin checks and reasons |

The specialist execution result is a strict `SUCCESS|ABSTAIN|FAILED` union with configuration, usage and per-call ledger on every branch. Agent-owned canonical outputs can only begin as `PRODUCED`; gate-owned outputs remain execution proposals until their named deterministic materializer accepts them. Execution recommendations, abstentions and failures are run records, not additional artifact registry names. Every success payload has advisory confidence as Decimal 0..1 with at most three fractional digits; abstention/failure confidence is null. Abstention reasons are exactly INSUFFICIENT_INPUT, INSUFFICIENT_EVIDENCE, EVIDENCE_CONFLICT or UNSAFE_INPUT, with safe details and input evidence refs, and no accepted partial output. AGENT-01 owns execution-failure codes. Confidence cannot grant authority.

## Dependencies, tools, evidence and ceilings

Allowed capabilities: evidence.read <=1; no mailbox history client, price calculator with mutation, calendar or external write capability. Structured model access is bounded by the runtime. Every other capability, provider credential, ORM/repository, application mutation command, Gmail/calendar write port, workflow launch and dynamic subagent tool is forbidden.

Exact maximum execution ceilings: 45 seconds; 12,000 input / 2,500 output tokens; 1 tool call; 2 model requests (second only schema repair); 15 USD minor. The earlier of per-capability deadline and remaining run deadline wins. Composition reserves cost before calls; checks cancellation before and after calls and before persistence; reconciles each provider ledger entry with usage/cost. The optional second model request can repair schema only and cannot retry until a preferred decision appears.

Evidence/source text is untrusted data. Validators check source authorization, field-level facts/estimates/unknowns, evidence ID/hash/span, current accepted inputs, strategy attribution, exact allowed enums, numeric/identity rules and absence of authority leakage. Missing required facts cannot be guessed.

## Persistence, idempotency and recovery

AgentRunRecordingService alone starts/closes runs; ArtifactCommandService inserts agent-owned `PRODUCED` outputs; ArtifactValidationService owns evidence links and validation; ArtifactAcceptanceService and the named domain materializers own acceptance. ProviderCostReconciliationService owns cost records. Workflow command/run/config/input keys deduplicate work. A response persisted before crash is recovered by identity/hash; replay cannot silently repeat a paid call or rewrite a prior artifact.

Rejected outputs cannot drive consumers. A safe retry is finite under AGENT-01 taxonomy and creates retained lineage; corrections supersede immutably outside active cohorts. Promotion or rollback is governed by the approved global package and boundary activation, not a local prompt-pointer change. Failure opens a typed exception when input/authority recovery is required.

## Ordered implementation tasks

<!-- roadmap-task id=AGENT-08-T01 milestone=M3 depends_on=AGENT-03-T01,AGENT-07-T01,AGENT-10-T01,AGENT-01-T01,DB-03-T04 mode=parallel locks=agent-runtime -->
- [ ] **Encode exact schemas and immutable configuration —** Input: canonical upstream artifact contracts and signed shared fixture templates. Operation: implement typed inputs, output/proposal schemas, prompt/configuration hashes and phase/authority rules. Output: importable contract and schema registry entry. Test evidence: strict schema, hash/version and missing-provider-input cases. Failure behavior: reject before model access.
<!-- roadmap-task id=AGENT-08-T02 milestone=M3 depends_on=AGENT-08-T01,AGENT-01-T02 mode=parallel locks=agent-runtime -->
- [ ] **Implement bounded specialist execution —** Input: verified runtime envelope and exact scoped capabilities. Operation: enforce the declared ceilings, cancellation and hostile-evidence handling with fake/recorded tools. Output: SUCCESS, ABSTAIN or FAILED with immutable lineage/ledger. Test evidence: tool denial, timeout, cancellation and all numeric boundary cases. Failure behavior: no accepted partial output or side effect.
<!-- roadmap-task id=AGENT-08-T03 milestone=M3 depends_on=AGENT-08-T02,AGENT-01-T04,BACKEND-01-T01,DB-04-T04,OBS-03-T02 mode=parallel locks=agent-artifacts,backend-domain -->
- [ ] **Validate and connect the deterministic handoff —** Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows. Operation: enforce the specialist rules and delegate each owned write; use fixture-backed domain gate interfaces without depending on later runtime evidence. Output: tested immutable specialist implementation/configuration identity and handoff. Test evidence: ordinary_reply_and_rejection_do_not_invent_suppression; genuine_objection_vs_rejection; stated_budget_and_commercial_floor_matrix; call_agreement_is_not_purchase_or_slot_acceptance; terminal_round_limit_and_stale_thread. Failure behavior: reject unsafe output and preserve prior accepted versions.
<!-- roadmap-task id=AGENT-08-T04 milestone=M3 depends_on=AGENT-08-T03,AGENT-10-T03,AGENT-10-T04 mode=serial locks=agent-runtime,agent-artifacts -->
- [ ] **Gate specialist acceptance with shared evaluation —** Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite. Operation: independently verify every repetition, hard rule, quality/cost/latency/regression threshold and immutable configuration hash. Output: specialist acceptance evidence for shared promotion; no second promotion writer. Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection. Failure behavior: candidate remains ineligible.

## Test strategy and retained evidence

Required focused cases: `ordinary_reply_and_rejection_do_not_invent_suppression`, `genuine_objection_vs_rejection`, `stated_budget_and_commercial_floor_matrix`, `call_agreement_is_not_purchase_or_slot_acceptance`, `terminal_round_limit_and_stale_thread`. Retain exact input/output schemas, provider and artifact hash vectors, fixtures, adversarial results, all three per-case captures, per-repetition scores, cost/latency/quality gates, authority graph and replay traces. Suite counts/allocations and numeric thresholds are owned by AGENT-10; a discrepancy blocks promotion.

## Safety, privacy, observability and acceptance

Telemetry records safe IDs, versions, hashes, counts, error/reason codes, latency and currency cost with ILS projection. It excludes raw contact data, message/calendar bodies, sensitive budget spans, prompts, secrets and hidden reasoning. Restricted evidence uses approved minimization, encryption and DB-06 retention; operational memory cannot enter global learning without a minimized evidence transform.

- [ ] All required accepted inputs precede their consumer, with exact version/hash lineage.
- [ ] Every output and deterministic owner matches the fifteen-artifact registry.
- [ ] Tools, evidence, ceilings, abstention and terminal recovery are verified.
- [ ] No agent has side-effect, commercial-policy, suppression or activation authority.
- [ ] Shared evaluation passes before product selection; live operation still requires later retained gates.
