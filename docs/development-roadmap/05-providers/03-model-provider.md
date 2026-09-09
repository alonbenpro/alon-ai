# Structured Model Provider and Cost-First Routing

**Document ID:** PROVIDER-03
**Status:** Planned M3 provider; no model client, routing policy, live call, or fixture adapter exists today
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `PROVIDER-03-T01 -> PROVIDER-03-T02 -> PROVIDER-03-T03 -> PROVIDER-03-T04 -> PROVIDER-03-T05 -> PROVIDER-03-T06`; cross-document task Inputs `PROVIDER-03-T01 <- AGENT-01-T01,DB-01-T01; PROVIDER-03-T05 <- AGENT-10-T05`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [AGENT-01](../04-agents/01-agent-runtime-and-contracts.md), DB-01/04/05 and OBS-03 cost ledgers.
**Outputs:** Byte-exact structured-model protocol, deterministic ModelRoutingPolicy, OpenAI adapter, typed failures, live-capture/fixture/batch modes, cost and replacement contract
**Unlocks:** Offline candidate capture and specialist promotion
**Risk:** High
**Complexity:** L

## Outcome

The application—not an agent—decides whether AI is needed and, if so, the cheapest permitted tier. The exact routing order is:

1. `NO_AI` for obvious filters, dedupe, arithmetic, commercial/policy checks, and deterministic eligibility.
2. `NANO` for structured extraction, normalization, classification and initial scoring where code is insufficient.
3. `MINI` only for shortlisted/preliminarily admitted leads or other explicitly registered higher-reasoning tasks.
4. `PREMIUM` default denied; one exact operator approval must bind task/run, model/configuration, maximum spend, purpose and expiry.
5. Non-urgent research uses `BATCH` processing when the selected provider/tier supports it and no user-facing latency requirement exists.

Agents receive only a scoped structured-model capability. They cannot select or escalate tiers, bypass shortlist requirements, change urgency, approve Premium, or turn provider output into business authority.

## ModelRoutingPolicy contract

`ModelRoutingDecisionV1` is deterministic and versioned. It records: task/capability; routing policy version/hash; `NO_AI|NANO|MINI|PREMIUM`; reason code; shortlist/preliminary evidence when Mini is selected; exact PremiumApproval reference when Premium is selected; `REALTIME|BATCH` execution mode; deadline; max tokens/calls/cost; governing agent configuration/strategy activation; and decision hash.

Allowed routing reasons are closed and testable, including `DETERMINISTIC_RULE_SUFFICIENT`, `STRUCTURED_EXTRACTION`, `INITIAL_SCORING`, `SHORTLISTED_DEEP_RESEARCH`, `SHORTLISTED_MESSAGE_REASONING`, `CHECKPOINT_EVALUATION`, `GLOBAL_LEARNING_EVALUATION`, and `PREMIUM_OPERATOR_EXCEPTION`. A routing reason never grants side-effect, commercial, suppression, legal, or strategy authority.

`PremiumApprovalV1` binds exact operator identity, task/run/config/model identifier, spend ceiling, justification, issued/expiry times and signature/hash. It is one-use or explicitly bounded-use according to its signed scope and never creates a reusable “premium enabled” flag.

## Structured provider wire

The provider-neutral `StructuredModelProvider.complete_structured` request/result remains strict/frozen/extra-forbid with exact schema/prompt/model/config hashes, timeout, token ceilings, no tools, no conversation state, no hidden retries, `store=false`, and typed usage/cost reconciliation. Provider SDK retries remain zero.

The request must include the accepted `ModelRoutingDecisionV1`. Composition rejects a model identifier incompatible with its tier, a Mini request without shortlist evidence, Premium without current approval, or a real-time request that is registered batch-only absent an explicit latency reason.

The initial live adapter uses OpenAI Responses structured output. Concrete model identifiers are configuration data and may change without changing the tier contract; `NANO`, `MINI`, and `PREMIUM` are application routing classes, not promises that a particular provider will keep a product name forever.

## Batch processing

`BATCH` is an execution mode, not another model tier. It is preferred for non-urgent research/evaluation work when supported. Batch jobs retain exact request/config/routing hashes and reconcile each item/result/cost. Missing/expired/partial batch results remain incomplete; they cannot be silently reissued in real time merely to reduce latency.

User-facing reply generation, live negotiation turns, and other registered interactive deadlines may use real-time mode. The routing record must retain why batch was ineligible.

## Cost, retries, privacy, and authority

Reserve cost before every network request or batch submission. Every actual provider request has a distinct call/ledger row. Timeout with uncertain charge opens a discrepancy and blocks blind retry. Inputs are minimized/redacted under SEC-06; telemetry contains safe IDs/hashes/tier/mode/tokens/cost/status, not prompts or sensitive evidence content.

No model call can create Gmail/calendar access, accepted commercial decisions, qualification authority, strategy activation, suppression, or legal evidence. Deterministic materializers/services retain those responsibilities.

## Modes and fixtures

- `RECORDED_FIXTURE`: zero network, byte/hash-verified replay.
- `LIVE_CAPTURE`: isolated M3 evaluation candidate capture only under exact signed/budgeted configuration.
- `PRODUCT_REALTIME`: promoted product configuration plus valid routing decision.
- `PRODUCT_BATCH`: promoted product configuration plus valid batch routing decision and batch-capable adapter.

Replacement providers must satisfy the same routing/tier/mode/schema/cost/timeout/cancellation/fixture contract.

## Ordered implementation tasks

<!-- roadmap-task id=PROVIDER-03-T01 milestone=M3 depends_on=AGENT-01-T01,DB-01-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement exact model protocol and routing contracts —** Input: AGENT-01 family, DB-01 canonicalizer and PRODUCT-01 routing policy. Operation: encode strict model request/result plus ModelRoutingDecisionV1, PremiumApprovalV1, tier/mode/reason registries and digest validation. Output: provider-neutral protocol. Test evidence: exact schema, NO_AI/no-call, tier/reason, Mini-shortlist, Premium-approval and batch-mode negatives. Failure behavior: reject before credential/provider access.
<!-- roadmap-task id=PROVIDER-03-T02 milestone=M3 depends_on=PROVIDER-03-T01 mode=parallel locks=provider-contracts -->
- [ ] **Implement OpenAI structured and batch adapters —** Input: routing-approved request, reservation, provider capability manifest. Operation: translate one strict no-tool/no-store real-time request or eligible batch item, with no hidden retry. Output: exact typed result/ledger; no business authority. Test evidence: fake HTTP/batch status/refusal/schema/usage/partial-result matrix and tier mismatch denial. Failure behavior: typed failure; no partial accepted artifact.
<!-- roadmap-task id=PROVIDER-03-T03 milestone=M3 depends_on=PROVIDER-03-T02 mode=parallel locks=provider-contracts -->
- [ ] **Implement routing ceilings, cancellation, and cost reconciliation —** Input: routing decision, run/provider deadlines and cost reservation. Operation: enforce call/token/cost/batch ceilings and reconcile actual usage. Output: bounded cost evidence. Test evidence: deterministic opportunities make zero model calls; Mini/Premium escalation attempts fail; timeout/cancel/discrepancy exact call counts. Failure behavior: no next call until authorized/reconciled.
<!-- roadmap-task id=PROVIDER-03-T04 milestone=M3 depends_on=PROVIDER-03-T03 mode=parallel locks=provider-contracts -->
- [ ] **Implement signed capture and fixture adapters —** Input: sanitized candidate captures by tier/mode. Operation: build/replay fixtures with network unavailable and retain routing decisions. Output: deterministic evaluation input. Test evidence: tamper/cross-tier/cross-mode/extra-field/zero-network cases. Failure behavior: fixture rejected.
<!-- roadmap-task id=PROVIDER-03-T05 milestone=M3 depends_on=PROVIDER-03-T04,AGENT-10-T05 mode=serial locks=provider-contracts,milestone-gate -->
- [ ] **Bind promoted product routing activation —** Input: promoted agent/model configurations plus routing policy and cost evidence. Operation: enable only configurations whose tier/mode requirements passed evaluation; keep Premium default-off and require exact runtime approval. Output: promoted cost-first product model composition. Test evidence: stale/unpromoted/routing-spliced/Premium-without-approval/batch-bypass denial. Failure behavior: model path remains disabled or falls back only to a cheaper already-authorized path, never upward.
<!-- roadmap-task id=PROVIDER-03-T06 milestone=M3 depends_on=PROVIDER-03-T05 mode=parallel locks=provider-contracts -->
- [ ] **Prove replacement and authority seams —** Input: fake second provider and import/runtime graph. Operation: run shared routing/provider suite and assert no credential/state/send/calendar/commercial reachability. Output: replaceable least-authority boundary. Test evidence: provider parity by tier/mode and authority graph. Failure behavior: adapter/config promotion blocked.

## Acceptance

- [ ] Deterministic opportunities use zero AI calls.
- [ ] Nano is the default model tier for cheap structured work.
- [ ] Mini requires shortlist/preliminary evidence.
- [ ] Premium requires exact explicit approval and cannot become globally enabled.
- [ ] Eligible non-urgent research uses batch or retains an explicit ineligibility reason.
- [ ] Every call records tier/mode/routing reason/usage/cost/strategy attribution.
- [ ] Agents cannot select models or gain side-effect/business authority.
