# Autonomous Sales-Validation Roadmap Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the complete roadmap from a manual, one-way validation assistant into the approved bounded autonomous sales-validation system and regenerate a semantically validated dependency-safe execution plan.

**Architecture:** One canonical machine-readable sales contract defines the runtime responsibilities, artifact authority, decisions, learning outcomes, and cohort schedule. Roadmap documents elaborate that contract across architecture, data, workflows, agents, services, UI, safety, evaluation, testing, and launch; typed validator rules enforce the invariants and generate the execution artifacts. Agents remain advisory, while deterministic services own sending, commercial calculations, booking writes, state transitions, activation, and all safety controls.

**Tech Stack:** Markdown roadmap sources, Python 3.13 roadmap validator, pytest, Pydantic AI planning boundary, DBOS/PostgreSQL roadmap contracts, Next.js/FastAPI planned surfaces, Graphify documentation graph.

**Spec:** `docs/superpowers/specs/2026-09-08-autonomous-sales-validation-roadmap-design.md`

## Global Constraints

- Preserve exact incremental cohorts `100/200/300/400`, cumulative checkpoints `100/300/600/1,000`, unique membership, and the 1,000 ceiling.
- The checkpoint result set is exactly `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP`; only `CONTINUE` can make a later cohort eligible.
- The global per-agent learning result set is exactly `PROMOTE|KEEP|ROLLBACK|INSUFFICIENT_EVIDENCE`; `NO_CHANGE` is behavior, not an extra serialized result.
- Runtime order is exactly Idea Discovery → Market Research → Offer Design → Lead Discovery/Prequalification → Deep Research → Final Qualification → Email Writing → Deterministic Sending → Reply Evaluation/Negotiation → Booking → Checkpoint Evaluation → Global Learning.
- `OfferPackage` is the sole downstream commercial authority and never provides input upstream to Idea Discovery or Market Research.
- `SendGateway` is the sole Gmail writer; `BookingGateway` is the sole calendar writer; neither is an agent.
- Routine per-message manual approval is removed. Exceptions, ambiguous results, safety incidents, protected legal decisions, kill/recovery, and out-of-envelope actions remain operator-controlled.
- Any reply stops the cold sequence. Only actual opt-out/complaint/bounce/legal signals create applicable durable suppression; eligible conversations may continue inside deterministic limits.
- Conversation memory is operational state, not learning. Global strategy changes occur only from immutable closed-checkpoint evidence and activate only at eligible cohort boundaries.
- Immutable safety, legal-policy, suppression, source, and commercial constraints are not learnable.
- Preserve existing strong Gmail ambiguity quarantine, idempotency, suppression, cap, budget, audit, and recovery guarantees.
- Do not claim product implementation, production readiness, legal authorization, real sends, or live calendar booking.
- Keep `graphify-out/` local and ignored.

---

### Task 1: Canonical authority, product, and architecture

**Files:**

- Create: `docs/superpowers/specs/2026-09-08-autonomous-sales-validation-roadmap-design.md`
- Create: `docs/superpowers/plans/2026-09-08-autonomous-sales-validation-roadmap-rewrite.md`
- Modify: `README.md`
- Modify: `docs/development-roadmap/README.md`
- Modify: `docs/development-roadmap/00-product-strategy/01-product-scope.md`
- Modify: `docs/development-roadmap/00-product-strategy/02-success-metrics.md`
- Modify: `docs/development-roadmap/00-product-strategy/03-risk-register-and-kill-criteria.md`
- Modify: `docs/development-roadmap/01-architecture/01-target-system-architecture.md`
- Modify: `docs/development-roadmap/01-architecture/02-module-boundaries.md`
- Modify: `docs/development-roadmap/01-architecture/03-domain-events-and-state-machines.md`
- Modify: `docs/superpowers/specs/2026-09-08-staged-thousand-lead-validation-design.md`
- Modify: `docs/superpowers/plans/2026-09-08-staged-thousand-lead-validation.md`

**Interfaces:**

- Consumes: the approved spec, the existing M0–M9 safety gates, and stable historical task IDs.
- Produces: one canonical structured sales contract; exact artifact/decision/result sets; state/event vocabulary; module ownership; supersession links; metrics and risk authority used by all later tasks.

- [ ] **Step 1: Add the canonical sales-contract block**

Add one fenced `json` block under an unambiguous `## Canonical autonomous sales contract` heading in PRODUCT-01. It must contain ordered `responsibilities`, their `kind`, `provider`, and output artifacts; the fifteen-artifact registry and producers; `commercial_authority: OfferPackage`; checkpoint decisions; learning results; cohort increments/cumulative maxima; `send_writer: SendGateway`; `booking_writer: BookingGateway`; and `strategy_activation_boundary: CHECKPOINT_ONLY`.

- [ ] **Step 2: Rewrite product scope, metrics, risks, and top-level navigation**

Make the approved system planned truth. Preserve the staged demand floors unless they conflict with the new exact result names. Remove `SCALE`, automatic-follow-up prohibition, routine approval, and one-way reply-stop statements. Add the complete sales/booking/learning funnel, metrics, launch ladder, exception model, strategy attribution, and new risks.

- [ ] **Step 3: Rewrite architecture and state authority**

Add deterministic `CommercialPolicyEngine`, `ActionAuthorizationService`, `BookingGateway`, `CheckpointEvaluationService`, and `StrategyActivationService`; separate Gmail/calendar read/write ports; add preliminary/final qualification, conversation, negotiation, booking, checkpoint, activation, and rollback states/events; preserve agents-as-advisors and sole side-effect writers.

- [ ] **Step 4: Supersede the old staged documents**

Replace their active content with a short historical notice linking the new spec/plan. Retain no contradictory normative requirement and do not copy banned legacy recipient phrases into active roadmap files.

- [ ] **Step 5: Verify Task 1 sources**

Run:

```bash
rg -n "Canonical autonomous sales contract|OfferPackage|BookingGateway|GlobalStrategyPackage" README.md docs/development-roadmap/00-product-strategy docs/development-roadmap/01-architecture
rg -n "automated follow-ups.*Never|routine manual|SCALE" README.md docs/development-roadmap/00-product-strategy docs/development-roadmap/01-architecture docs/superpowers/specs docs/superpowers/plans
```

Expected: the first command finds the new authority; the second finds no active contradictory rule except clearly labeled historical explanation if needed.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/development-roadmap/README.md docs/development-roadmap/00-product-strategy docs/development-roadmap/01-architecture docs/superpowers/specs docs/superpowers/plans
git commit -m "docs: define autonomous sales validation authority"
```

### Task 2: Agents, workflows, and provider sequence

**Files:**

- Modify/create/rename only: `docs/development-roadmap/03-workflows/*.md`
- Modify/create/rename only: `docs/development-roadmap/04-agents/*.md`
- Modify/create only: `docs/development-roadmap/05-providers/*.md`

**Interfaces:**

- Consumes: Task 1's canonical contract, states, ports, artifact names, and stable-ID migration rule.
- Produces: dependency-safe specialist contracts and finite workflows for idea through global learning; approved discovery/calendar adapters; exact agent capabilities; accepted artifacts for Task 3 services/data and Task 4 tests/UI.

- [ ] **Step 1: Put user-facing agent files in canonical order**

The active section must include:

```text
01-agent-runtime-and-contracts.md
02-idea-discovery-agent.md
03-market-research-agent.md
04-offer-design-agent.md
05-lead-discovery-agent.md
06-lead-research-agent.md
07-lead-qualification-agent.md
08-email-writing-agent.md
09-reply-evaluation-and-negotiation-agent.md
10-experiment-evaluation-agent.md
11-global-learning-engine.md
12-agent-evals-and-versioning.md
```

Preserve stable historical `Document ID` and task prefixes when practical; filename numbers are presentation order, not dependency authority. Add new IDs for Lead Discovery and Global Learning. Update every descriptive prerequisite and link.

- [ ] **Step 2: Define all agent artifacts and capabilities**

Every agent input/output uses the exact canonical artifact names and version/hash references. Idea bypass produces the same `IdeaBrief` shape. Market Research precedes Offer Design. Lead Discovery proposes candidates/prequalification without fabricating identities. Deep Research distinguishes facts/estimates/unknowns. Final Qualification consumes OfferPackage filters. Email Writing cannot send. Reply Evaluation produces exact objectives and bounded negotiation proposals. Checkpoint Evaluation uses frozen evidence. Global Learning consumes only closed checkpoint evidence and produces per-agent proposals without side effects.

- [ ] **Step 3: Rewrite finite workflows**

Cover optional idea bypass, corrected idea→research→offer order, multi-source discovery/prequalification, research/final qualification, automatic draft→policy→send, mailbox ingestion, finite reply→objective→draft→guarded-send loop, bounded negotiation, explicit confirmation→booking, checkpoint→global learning→boundary activation, and pause/replay/recovery/idempotency for every boundary.

Create dedicated Booking, Checkpoint Evaluation, and Global Learning workflow documents with new stable IDs rather than overloading unrelated tasks.

- [ ] **Step 4: Update provider contracts**

Keep Gmail write access gateway-only; make history sync ingest complete bounded thread state without suppressing every reply. Define approved multi-source discovery/provider evidence. Create a calendar-provider document with separate availability read and event write capabilities, Google Calendar as the first adapter, deterministic BookingGateway ownership, idempotency, timezone/DST, reschedule/cancel, and ambiguity reconciliation.

- [ ] **Step 5: Update task metadata without cycles**

Add explicit provider→consumer dependencies while avoiding feedback edges from M9 runtime evidence to M3 implementation. Keep shared evaluation infrastructure before specialist acceptance gates. Do not make concurrent per-lead runtime stages into implementation-time circular dependencies.

- [ ] **Step 6: Verify Task 2 sources**

Run:

```bash
rg -n "IdeaBrief|MarketResearchReport|OfferPackage|LeadDiscoveryCandidate|BookingIntent|CheckpointEvidenceBundle|GlobalStrategyPackage" docs/development-roadmap/03-workflows docs/development-roadmap/04-agents docs/development-roadmap/05-providers
rg -n "cannot draft.*response|automatic response.*excluded|every reply.*suppression|Offer Design.*before.*Market" docs/development-roadmap/03-workflows docs/development-roadmap/04-agents docs/development-roadmap/05-providers
```

Expected: canonical artifacts are owned and consumed; obsolete prohibitions/ordering are absent from active contracts.

- [ ] **Step 7: Commit**

```bash
git add docs/development-roadmap/03-workflows docs/development-roadmap/04-agents docs/development-roadmap/05-providers
git commit -m "docs: redesign agents and autonomous workflows"
```

### Task 3: Data, deterministic services, security, and retention

**Files:**

- Modify: `docs/development-roadmap/02-database/*.md`
- Modify: `docs/development-roadmap/06-backend/*.md`
- Modify: `docs/development-roadmap/08-security-and-compliance/*.md`

**Interfaces:**

- Consumes: Task 1 authority and Task 2 artifacts/workflows/providers.
- Produces: exact data ownership, deterministic policy/service boundaries, API/query surfaces, action authorization, commercial calculations, booking persistence, checkpoint/strategy persistence, privacy inventory, and safety gates consumed by UI/tests/launch.

- [ ] **Step 1: Expand the database contract**

Plan versioned records for offer packages/economics, business/person/contact/source/evidence identity, phased qualification, full encrypted conversations, replies, negotiation, budget assertions, booking, checkpoint evidence, immutable agent input/output snapshots, global strategies/activations/rollbacks, action-level strategy attribution, and cohort/checkpoint ownership.

Replace closed agent/artifact/table/foreign-key/retention manifests atomically. Remove workflow-input-hash equality that prevents distinct per-agent snapshots. Preserve append-only audit/idempotency/ledger ownership.

- [ ] **Step 2: Replace routine approvals with action authorization**

Introduce immutable `ActionAuthorityScopeV1` that binds action kind/content, offer, strategy activation, campaign/cohort/member, recipient/thread, policy facts/rules, commercial decision, expiry, and control generation. Refocus approval/command docs on exceptions, incidents, kill/recovery, protected legal decisions, and strategy controls.

- [ ] **Step 3: Define deterministic commercial and booking services**

Specify exact allowed/forbidden negotiation calculations and pure test vectors. Add booking command/result/reconciliation services. Keep agents unable to calculate authoritative price/margin or call Gmail/calendar writes. Add `calendar-side-effects` as a serial resource lock where relevant.

- [ ] **Step 4: Expand API and reporting surfaces**

Add projections and commands for offer packages/envelopes, lead discovery/dossiers/qualification, conversations/negotiation, send blocks, bookings/calendar, checkpoints, global strategies/evidence/activations/rollbacks, and exception handling. Do not hard-code obsolete operation counts.

- [ ] **Step 5: Strengthen security and privacy**

Distinguish cold-sequence stop from durable suppression. Add source-specific collection, minimization, truthful claims, frequency/round limits, negative-sentiment stops, prompt-injection isolation for web/email, sensitive-data redaction before model calls, action-level audit, kill switches, explicit per-field access/retention/deletion/backup expiry, and strategy/booking race controls.

- [ ] **Step 6: Verify Task 3 sources**

Run:

```bash
rg -n "ActionAuthorityScopeV1|CommercialPolicyEngine|STATED|INFERRED|BookingGateway|StrategyActivation" docs/development-roadmap/02-database docs/development-roadmap/06-backend docs/development-roadmap/08-security-and-compliance
rg -n "manual-only|operator-approved.*send|GMAIL_REPLY.*suppress|every reply.*suppress" docs/development-roadmap/02-database docs/development-roadmap/06-backend docs/development-roadmap/08-security-and-compliance
```

Expected: deterministic authority and data models are present; obsolete routine/manual and every-reply suppression contracts are absent.

- [ ] **Step 7: Commit**

```bash
git add docs/development-roadmap/02-database docs/development-roadmap/06-backend docs/development-roadmap/08-security-and-compliance
git commit -m "docs: add commercial booking and learning data controls"
```

### Task 4: Dashboard, metrics, tests, infrastructure, and launch

**Files:**

- Modify: `docs/development-roadmap/07-frontend/*.md`
- Modify: `docs/development-roadmap/09-observability-and-evaluation/*.md`
- Modify: `docs/development-roadmap/10-testing/*.md`
- Modify: `docs/development-roadmap/11-infrastructure/*.md`
- Modify: `docs/development-roadmap/12-launch-and-operations/*.md`

**Interfaces:**

- Consumes: Tasks 1–3 contracts, states, data, APIs, services, and safety gates.
- Produces: complete operator control-plane roadmap, measurable evaluation, full test matrix, recovery/deployment bindings, and earned-autonomy launch sequence.

- [ ] **Step 1: Rewrite all frontend roadmap files**

Cover manual/discovered idea, research/offer/envelope inspection, lead sources/dossiers/phased qualification, full conversation/negotiation/booking timeline, automatic-send status/blocks, `INTERESTED→NEGOTIATING→COMMITTED→BOOKED`, calendar, checkpoint evidence/decisions, global strategies/evidence/per-agent changes/activations/rollbacks, and exception queue. Replace all-currently-eligible preselection with current-stage server-owned membership snapshots.

- [ ] **Step 2: Expand metrics, events, costs, and evaluation**

Add every metric in the spec with cohort, agent, strategy version, and activation attribution. Define objection/negotiation/booking/checkpoint/learning events and alerts. Protect telemetry from PII/content. Make cost and margin truth prerequisites for commercial and checkpoint decisions.

- [ ] **Step 3: Rewrite the testing roadmap**

Add contract, order, hallucination/evidence, discovery/dedupe, phased qualification, email/send separation, reply-loop, commercial boundary, booking, checkpoint/global learning, cross-campaign activation, no-mid-cohort-mutation, weak-evidence, rollback, durable replay, browser-authority, and full simulation tests. Preserve the existing Gmail ambiguity, cap-race, suppression, recovery, and security cases.

- [ ] **Step 4: Bind infrastructure and recovery**

Release, backup, restore, rollback, monitoring, and disaster-recovery evidence must preserve offer/strategy/cohort/checkpoint/conversation/booking/suppression state and must not reopen admission or repeat a provider side effect.

- [ ] **Step 5: Replace launch and autonomy milestones**

Encode the exact eight-phase evidence ladder. Keep owned-alias tests excluded from real demand. Allow bounded in-envelope real replies/negotiation/booking only after all preceding gates. Remove per-message approval and zero-follow-up from M9. Make checkpoint learning and activation automatic but boundary-only. Never let CONTINUE exceed 1,000 or authorize a new program/source/legal policy.

- [ ] **Step 6: Verify Task 4 sources**

Run:

```bash
rg -n "NEGOTIATING|COMMITTED|BOOKED|calendar|exception|GlobalStrategy|rollback|cross-campaign" docs/development-roadmap/07-frontend docs/development-roadmap/09-observability-and-evaluation docs/development-roadmap/10-testing docs/development-roadmap/11-infrastructure docs/development-roadmap/12-launch-and-operations
rg -n "zero follow|follow-up count.*zero|individual approval|per-message approval|ALL_CURRENTLY_ELIGIBLE" docs/development-roadmap/07-frontend docs/development-roadmap/09-observability-and-evaluation docs/development-roadmap/10-testing docs/development-roadmap/12-launch-and-operations
```

Expected: the full lifecycle and safety evidence are present; old routine-approval/single-message rules remain only inside explicitly isolated owned-alias fixtures where they cannot govern M9.

- [ ] **Step 7: Commit**

```bash
git add docs/development-roadmap/07-frontend docs/development-roadmap/09-observability-and-evaluation docs/development-roadmap/10-testing docs/development-roadmap/11-infrastructure docs/development-roadmap/12-launch-and-operations
git commit -m "docs: plan autonomous dashboard tests and launch"
```

### Task 5: Semantic validator, dependencies, and generated execution artifacts

**Files:**

- Modify: `scripts/validate_roadmap.py`
- Modify: `backend/tests/unit/test_roadmap_validator.py`
- Modify: `docs/development-roadmap/README.md`
- Regenerate: `docs/development-roadmap/execution-manifest.json`
- Regenerate: `docs/development-roadmap/EXECUTION_ORDER.md`
- Regenerate: `docs/development-roadmap/AGENT_EXECUTION_PLAN.md`

**Interfaces:**

- Consumes: every authoritative source task from Tasks 1–4.
- Produces: parsed canonical contract, semantic invariants, provider-ancestor checks, calendar lock validation, fingerprint binding, current file manifest, valid DAG/waves, and byte-exact generated artifacts.

- [ ] **Step 1: Write failing semantic-validator tests**

Add tests for exact responsibility order/kinds; artifact/producers; Market Research before Offer Design; sole `OfferPackage` authority; rejection of agent send/booking writers; reply→negotiation→booking order and `BookingIntent`; closed-checkpoint learning; exact checkpoint/learning enums; weak-evidence no-mutation; checkpoint-only activation; no active-cohort mutation; exact cohorts; provider ancestry even when incidental sort order looks correct; canonical-contract fingerprint changes; missing authority failure; and failed-validation no-write behavior.

- [ ] **Step 2: Run the focused tests and verify failure**

```bash
uv run --project backend pytest backend/tests/unit/test_roadmap_validator.py -q
```

Expected: new tests fail because the semantic contract parser/validator/fingerprint fields do not exist.

- [ ] **Step 3: Implement the semantic parser and validators**

Parse the exact fenced contract from PRODUCT-01 into typed immutable structures. Validate exact values, unique providers, agent-versus-service kinds, provider ancestry, strategy-boundary rules, and source presence. Include the canonical contract and README document-gate data in the canonical fingerprint and generated JSON manifest. Add `calendar-side-effects` to allowed and serial-only locks.

- [ ] **Step 4: Repair every task dependency and README manifest row**

Ensure each new/renamed source document is listed once, `Document ID` matches its task prefix, task ordinals are contiguous, no future-milestone or cycle exists, consumers have provider ancestry, descriptive prerequisite headers match the new model, and no consumer builds before its contract.

- [ ] **Step 5: Regenerate artifacts**

```bash
python3 scripts/validate_roadmap.py --write
python3 scripts/validate_roadmap.py --check
```

Expected: all three artifacts are regenerated together and a second check is byte-exact.

- [ ] **Step 6: Run focused verification**

```bash
uv run --project backend pytest backend/tests/unit/test_roadmap_validator.py -q
make roadmap
```

Expected: all roadmap-validator tests pass and generated artifacts are current.

- [ ] **Step 7: Commit**

```bash
git add scripts/validate_roadmap.py backend/tests/unit/test_roadmap_validator.py docs/development-roadmap
git commit -m "docs: regenerate autonomous roadmap execution graph"
```

### Task 6: Integrated consistency, Graphify refresh, and final evidence

**Files:**

- Modify only if verification proves a defect: any tracked file changed by Tasks 1–5
- Local-only refresh: `graphify-out/`

**Interfaces:**

- Consumes: the complete branch.
- Produces: contradiction-free roadmap, passing repository gates, fresh documentation graph, and independent whole-branch review.

- [ ] **Step 1: Run canonical contradiction and coverage scans**

```bash
rg -n "SCALE|per-lead learning|campaign-isolated learning|manual-only|per-message approval|every reply.*suppression|zero follow" docs/development-roadmap README.md docs/superpowers/specs docs/superpowers/plans
rg -n "IdeaBrief|MarketResearchReport|OfferPackage|LeadDiscoveryCandidate|LeadResearchDossier|QualificationDecision|ConversationStrategy|EmailDraft|ReplyEvaluation|NegotiationDecision|BookingIntent|CheckpointEvidenceBundle|AgentLearningProposal|GlobalStrategyPackage|StrategyActivation" docs/development-roadmap
```

Classify every first-scan hit. Delete or rewrite active contradictions; allow only historical supersession notices and isolated owned-alias fixture constraints that explicitly cannot govern real campaigns.

- [ ] **Step 2: Run complete project gates**

```bash
make lint
make typecheck
make test
make build
git diff --check
python3 scripts/validate_roadmap.py --check
```

Expected: all available gates pass. Report Docker-only verification separately if Docker is unavailable.

- [ ] **Step 3: Refresh Graphify for changed documentation**

Run the installed documentation-aware Graphify incremental workflow on this exact worktree, then rerun the canonical roadmap query and save the result with an honest outcome. Do not substitute raw `graphify update .` for semantic Markdown refresh. Keep `graphify-out/` ignored.

- [ ] **Step 4: Run independent whole-branch review**

Review the full diff against the spec, paying special attention to provider/consumer authority, data-retention completeness, reply/suppression distinction, commercial and booking boundaries, checkpoint/global-learning activation, dependency cycles, generated artifacts, and planned-versus-implemented wording.

- [ ] **Step 5: Commit any reviewed integration fixes**

```bash
git add -u
git commit -m "docs: close autonomous roadmap consistency gaps"
```

Skip the commit if verification and review require no tracked fix.
