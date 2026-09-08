# Staged Thousand-Lead Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the contradictory ten/50-recipient experiment rules with one dependency-safe 100/200/300/400 staged program capped at 1,000 unique delivered recipients.

**Architecture:** PRODUCT-02 remains the sole numeric decision authority; downstream database, workflow, backend, frontend, safety, observability, testing, and launch documents consume that versioned contract. LAUNCH-03 executes four immutable incremental cohorts with a signed barrier after each, while the roadmap validator and focused tests reject legacy caps, incremental/cumulative ambiguity, duplicate membership, and later-stage admission without `CONTINUE`.

**Tech Stack:** Markdown roadmap contracts, Python 3.13 roadmap validator/tests, deterministic JSON/Markdown artifact generator, pytest, Ruff, Pyright, ESLint, TypeScript, Next.js, Graphify.

**Spec:** `docs/superpowers/specs/2026-09-08-staged-thousand-lead-validation-design.md`

## Global Constraints

- Cohort increments are exactly `100`, `200`, `300`, and `400`; cumulative maxima are exactly `100`, `300`, `600`, and `1,000`.
- The 1,000 value is a ceiling, never a requirement to consume the full reachable market.
- Every recipient identity belongs to at most one stage in one experiment version.
- Only a signed `CONTINUE` decision opens the next stage; `REVISE`, `KILL`, `INCONCLUSIVE`, and `SAFETY_STOP` prohibit later-stage admission.
- Any major-hypothesis change closes the active version and creates a new immutable version.
- Agent research may establish test-worthiness but may not claim demand validation or authorize sending.
- Existing consent, legal review, suppression, approval, Gmail reconciliation, budget, rate, public opt-out, audit, and kill-switch authorities remain fail-closed.
- Real-recipient authority is never delegated to an agent or LAUNCH-04 earned autonomy.
- PRODUCT-02 owns exact metric thresholds and canonical stage-decision semantics; consumers may be stricter but never weaker.
- Generated roadmap artifacts are outputs of the annotated source documents and must never be hand-edited.
- Work directly on `main`, as requested by the operator; do not create worktrees or feature branches.

---

### Task 1: Lock the staged-program regression contract

**Files:**
- Modify: `backend/tests/unit/test_roadmap_validator.py`
- Modify: `scripts/validate_roadmap.py`

**Interfaces:**
- Consumes: the approved exact schedule and legacy-rule rejection requirements from the design spec.
- Produces: `STAGED_LEAD_SCHEDULE`, `STAGED_LEAD_CUMULATIVE`, source-contract validation errors with path/line context, and focused regression tests used by every later task.

- [ ] **Step 1: Add failing constant and source-scan tests**

Add tests asserting the validator exports these exact immutable tuples:

```python
assert roadmap_validator.STAGED_LEAD_SCHEDULE == (100, 200, 300, 400)
assert roadmap_validator.STAGED_LEAD_CUMULATIVE == (100, 300, 600, 1000)
```

Add a repository test that reads non-generated active roadmap Markdown and asserts:

```python
assert "at most ten recipients" not in active_text
assert "one-to-ten" not in active_text
assert "10-total" not in active_text
assert "11th recipient" not in active_text
assert "50 delivered unique recipients" not in active_text
assert "100/200/300/400" in active_text
```

Exclude `AGENT_EXECUTION_PLAN.md`, `EXECUTION_ORDER.md`, historical specs, and the approved design's problem statement from the legacy-source scan.

- [ ] **Step 2: Run the focused tests and capture RED**

Run:

```bash
cd backend && uv run pytest tests/unit/test_roadmap_validator.py -k "staged_lead or legacy_recipient" -q
```

Expected: failures because the constants and canonical staged source contract do not exist yet.

- [ ] **Step 3: Add the minimal validator constants and contextual checks**

Define:

```python
STAGED_LEAD_SCHEDULE = (100, 200, 300, 400)
STAGED_LEAD_CUMULATIVE = (100, 300, 600, 1000)
```

Add one validation function that scans active source documents, rejects the four legacy phrases, requires the canonical schedule in PRODUCT-02 and LAUNCH-03, and raises the existing contextual `ValidationError` form with the offending path and line. Do not parse generated artifacts as source authority.

- [ ] **Step 4: Run the focused tests and confirm the intended remaining failures**

Run the same focused command. Constant tests must pass; repository-source tests must remain RED until Tasks 2-5 update the contracts.

- [ ] **Step 5: Commit the regression harness**

```bash
git add scripts/validate_roadmap.py backend/tests/unit/test_roadmap_validator.py
git commit -m "test: lock staged thousand-lead roadmap contract"
```

### Task 2: Make PRODUCT-02 the canonical staged-decision authority

**Files:**
- Modify: `docs/development-roadmap/00-product-strategy/01-product-scope.md`
- Modify: `docs/development-roadmap/00-product-strategy/02-success-metrics.md`
- Modify: `docs/development-roadmap/00-product-strategy/03-risk-register-and-kill-criteria.md`
- Modify: `docs/development-roadmap/02-database/02-experiment-and-offer-schema.md`
- Modify: `docs/development-roadmap/02-database/03-leads-campaigns-and-messages.md`
- Modify: `docs/development-roadmap/02-database/05-audit-events-and-idempotency.md`

**Interfaces:**
- Consumes: `STAGED_LEAD_SCHEDULE`, `STAGED_LEAD_CUMULATIVE`, existing ExperimentBrief/Decision authority, immutable product record rules.
- Produces: canonical `StagedValidationRuleV1`, `StageDecisionV1`, cohort membership uniqueness, stage admission facts, and deterministic decision/kill evidence for downstream workflows.

- [ ] **Step 1: Replace the single final-sample rule in PRODUCT-02**

Encode this exact authority table:

```markdown
| Stage | New delivered recipients | Cumulative maximum | Required terminal barrier |
| `STAGE_1_SIGNAL` | `100` | `100` | `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` |
| `STAGE_2_CONFIRM` | `200` | `300` | `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` |
| `STAGE_3_REPEAT` | `300` | `600` | `CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` |
| `STAGE_4_ESTIMATE` | `400` | `1,000` | final `SCALE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` |
```

Define the default demand floors below. A pre-registered rule may be stricter, never weaker.

```markdown
| Barrier | Default demand floor after the complete observation window |
| Stage 1 | at least `3` positive human replies or at least `1` qualified conversation |
| Stage 2 | cumulative at least `6` positive human replies and `2` qualified conversations, or at least `1` verified paid commitment |
| Stage 3 | cumulative at least `12` positive human replies, `4` qualified conversations, and `1` verified paid commitment |
| Stage 4 `SCALE` | cumulative at least `20` positive human replies, `8` qualified conversations, `2` verified paid commitments, and projected contribution margin `> 0` |
```

Every `CONTINUE` also requires deliverability `>=0.90`, zero complaints, zero unresolved ambiguous sends, every safety gate green, and no registered economic kill. Raw replies alone cannot yield final `SCALE`. Preserve a pre-registered observation window per stage and require `INCONCLUSIVE` when the denominator/window cannot support another decision.

- [ ] **Step 2: Update scope and risk authorities**

Make PRODUCT-01 describe a four-stage capped program rather than an undifferentiated sample cap. Make PRODUCT-03 add stage-overrun, cross-stage recipient reuse, uncontrolled variable drift, and premature continuation as High risks with deterministic stop actions.

- [ ] **Step 3: Add immutable database contracts**

Specify a versioned staged rule and stage-run/decision representation using the existing experiment, campaign, lead, metric, audit, and decision ownership boundaries. Require unique `(experiment_version, recipient_identity)` membership, one stage ordinal per member, stage-local incremental cap, cumulative cap, signed prior decision reference, immutable allocation/subsegment, and serializable admission.

- [ ] **Step 4: Update Product/DB task evidence without changing task identities unnecessarily**

Revise existing task Inputs, Operations, Outputs, test evidence, and failure behavior so downstream consumers receive the staged rule and admission authority. Add a new task only if no existing task can honestly own stage-decision persistence; if added, assign the next contiguous document-local ID and repair every dependent metadata edge.

- [ ] **Step 5: Run source parsing and focused Product/DB checks**

```bash
python3 scripts/validate_roadmap.py --check
cd backend && uv run pytest tests/unit/test_roadmap_validator.py -k "parse or staged_lead or product or database" -q
```

Expected: source parsing succeeds; generated drift is expected until Task 6, but no cycle, ID, dependency, or contextual-diagnostic regression is permitted.

- [ ] **Step 6: Commit the authority layer**

```bash
git add docs/development-roadmap/00-product-strategy docs/development-roadmap/02-database
git commit -m "docs: define staged thousand-lead authority"
```

### Task 3: Propagate stage admission through workflows and backend

**Files:**
- Modify: `docs/development-roadmap/03-workflows/02-experiment-lifecycle.md`
- Modify: `docs/development-roadmap/03-workflows/04-lead-qualification-workflow.md`
- Modify: `docs/development-roadmap/03-workflows/05-outreach-and-reply-workflow.md`
- Modify: `docs/development-roadmap/03-workflows/06-pause-cancel-resume-and-recovery.md`
- Modify: `docs/development-roadmap/06-backend/02-api-contracts.md`
- Modify: `docs/development-roadmap/06-backend/03-policy-engine.md`
- Modify: `docs/development-roadmap/06-backend/04-send-gateway.md`
- Modify: `docs/development-roadmap/06-backend/05-approval-and-command-handling.md`
- Modify: `docs/development-roadmap/06-backend/06-reporting-and-query-services.md`

**Interfaces:**
- Consumes: canonical staged rule, prior signed barrier, immutable cohort membership, existing SendGateway/suppression/provider authority.
- Produces: stage-aware lifecycle transitions, `admitNextValidationStage`, stage-scoped outreach/recovery, and incremental/cumulative funnel reports.

- [ ] **Step 1: Define the stage lifecycle**

Add explicit stage states or a versioned stage aggregate whose legal sequence is:

```text
PLANNED -> ADMITTING -> SENDING -> OBSERVING -> EVALUATING ->
CONTINUE | REVISE | KILL | INCONCLUSIVE | SAFETY_STOP
```

Stages 1-3 may transition from `CONTINUE` to creation of the next ordinal only. Stage 4 closes into the existing authoritative experiment decision. Pause/recovery must restore the exact stage and remaining incremental/cumulative capacity without readmitting members.

- [ ] **Step 2: Scale qualification without pre-authorizing sends**

Update WF-04 so it can research and qualify enough candidates for the next cohort plus an explicitly bounded reserve. `READY_FOR_OUTREACH` remains preparation only. Qualification must deduplicate across all completed/current cohorts and preserve source/subsegment allocation.

- [ ] **Step 3: Bind WF-05 and policy admission to the signed barrier**

Require every enqueue/final-send decision to prove current stage ordinal, membership, remaining incremental capacity, remaining 1,000 cumulative capacity, prior-stage `CONTINUE` when ordinal is greater than one, current safety facts, and no cross-stage reuse. Reservation and membership admission must be atomic under concurrent workers.

- [ ] **Step 4: Define API, command, approval, and reporting contracts**

Add typed operations to start/evaluate a stage and admit the next stage. Expose incremental and cumulative counts separately. UI/API clients may request the next transition but cannot choose counts, bypass a barrier, or translate `REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` into continuation.

- [ ] **Step 5: Update task metadata and validate dependencies**

Ensure Product/DB outputs are dependencies of the earliest workflow/backend consumer tasks. Preserve serial locks for Gmail side effects, policy authority, OpenAPI generation, and milestone gates.

- [ ] **Step 6: Run focused validation**

```bash
python3 scripts/validate_roadmap.py --check
cd backend && uv run pytest tests/unit/test_roadmap_validator.py -k "staged_lead or workflow or backend or dependency" -q
```

- [ ] **Step 7: Commit workflow/backend propagation**

```bash
git add docs/development-roadmap/03-workflows docs/development-roadmap/06-backend
git commit -m "docs: propagate staged cohort admission"
```

### Task 4: Propagate operator UX, safety, observability, and test evidence

**Files:**
- Modify: `docs/development-roadmap/07-frontend/02-experiment-creation-flow.md`
- Modify: `docs/development-roadmap/07-frontend/03-experiment-control-center.md`
- Modify: `docs/development-roadmap/07-frontend/05-lead-and-campaign-management.md`
- Modify: `docs/development-roadmap/07-frontend/06-approval-inbox.md`
- Modify: `docs/development-roadmap/07-frontend/08-cost-funnel-and-decision-analytics.md`
- Modify: `docs/development-roadmap/08-security-and-compliance/04-outreach-compliance.md`
- Modify: `docs/development-roadmap/08-security-and-compliance/05-suppression-budgets-and-kill-switch.md`
- Modify: `docs/development-roadmap/09-observability-and-evaluation/02-metrics-tracing-and-alerting.md`
- Modify: `docs/development-roadmap/09-observability-and-evaluation/03-provider-cost-accounting.md`
- Modify: `docs/development-roadmap/10-testing/02-contract-and-integration-tests.md`
- Modify: `docs/development-roadmap/10-testing/03-workflow-recovery-tests.md`
- Modify: `docs/development-roadmap/10-testing/04-gmail-side-effect-tests.md`
- Modify: `docs/development-roadmap/10-testing/05-end-to-end-browser-tests.md`
- Modify: `docs/development-roadmap/10-testing/06-load-security-and-chaos-tests.md`

**Interfaces:**
- Consumes: stage-aware commands/reports and all existing safety authority.
- Produces: operator-visible stage controls, stage/cumulative alerts and costs, and executable safety/recovery/race evidence.

- [ ] **Step 1: Specify the operator-facing staged experience**

Show the fixed table `100 -> 100`, `200 -> 300`, `300 -> 600`, `400 -> 1,000`; current stage; admitted/delivered/remaining counts; observation-window status; demand/economic evidence; safety status; and signed barrier. The next-stage control is disabled unless the server reports eligible `CONTINUE`; no UI arithmetic creates authority.

- [ ] **Step 2: Expand safety and compliance contracts**

Require legal/policy review for the full program and any stage-specific restriction; enforce suppression at admission/approval/send/signal; add hard stops for stage/cumulative overrun, identity reuse, allocation drift, uncontrolled variant drift, complaint, bounce, opt-out, ambiguity, budget, and telemetry blindness. A lower counsel/provider cap wins.

- [ ] **Step 3: Add stage-scoped metrics and costs**

Define stage and cumulative dimensions for delivery, reply, positive reply, qualified conversation, paid commitment, spend, operator time, and contribution margin. Alerts distinguish a stage cap breach from a 1,000-total breach and never expose recipient identities.

- [ ] **Step 4: Add exact test matrices**

Require boundary cases at `99/100`, `199/200`, `299/300`, `399/400`, and cumulative `999/1,000`; concurrent final-slot admission; duplicate identity across stages; every non-`CONTINUE` barrier; stale/replayed signature; recovery at each state; provider ambiguity; complaint/suppression race; lower legal cap; incremental/cumulative report correctness; and UI disabled-state behavior.

- [ ] **Step 5: Validate source graph and locks**

```bash
python3 scripts/validate_roadmap.py --check
cd backend && uv run pytest tests/unit/test_roadmap_validator.py -k "staged_lead or security or testing or frontend or observability" -q
```

- [ ] **Step 6: Commit UX/safety/evidence propagation**

```bash
git add docs/development-roadmap/07-frontend docs/development-roadmap/08-security-and-compliance docs/development-roadmap/09-observability-and-evaluation docs/development-roadmap/10-testing
git commit -m "docs: specify staged validation controls and evidence"
```

### Task 5: Replace LAUNCH-03 with the four-stage program

**Files:**
- Modify: `docs/development-roadmap/12-launch-and-operations/03-first-real-experiment.md`
- Modify: `docs/development-roadmap/12-launch-and-operations/04-earned-autonomy.md`
- Modify: `docs/development-roadmap/12-launch-and-operations/05-maintenance-and-upgrade-policy.md`
- Modify: `docs/development-roadmap/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: every staged authority and safety/evidence interface from Tasks 2-4.
- Produces: the canonical operational sequence, final launch tasks, and repository navigation explaining the 1,000-recipient ceiling.

- [ ] **Step 1: Rewrite the LAUNCH-03 outcome and envelope**

Replace the ten-recipient pilot with one program containing the four exact incremental cohorts. Preserve one offer/version per program, immutable stage allocation, current legal/provider evidence, safe public suppression modes, manual/operator authority where already required, and all provider-ambiguity rules.

- [ ] **Step 2: Split LAUNCH-03 task execution by stage barriers**

Retain stable task IDs where semantics still match. Add contiguous tasks when necessary so source metadata represents: freeze program; activate suppression ingress; execute Stage 1; evaluate Stage 1; execute/evaluate Stage 2; execute/evaluate Stage 3; execute/evaluate Stage 4; close final decision. Every execution task depends on the prior barrier task and uses serial live/Gmail/milestone locks.

- [ ] **Step 3: Prevent LAUNCH-04 from granting real-recipient autonomy**

State explicitly that no result, including final `SCALE`, permits autonomous recipient admission, send approval, legal judgment, cap modification, hypothesis mutation, or a second program. Scaling requires a separately approved experiment/version.

- [ ] **Step 4: Update maintenance and indexes**

Make rollback/maintenance preserve the current stage, delivered cohort, suppression obligations, and remaining caps. Link the design and staged program from the roadmap and root README without presenting planned behavior as implemented.

- [ ] **Step 5: Make the legacy-rule regression test GREEN**

```bash
cd backend && uv run pytest tests/unit/test_roadmap_validator.py -k "staged_lead or legacy_recipient" -q
```

Expected: all focused staged-program tests pass.

- [ ] **Step 6: Commit launch authority**

```bash
git add README.md docs/development-roadmap/README.md docs/development-roadmap/12-launch-and-operations
git commit -m "docs: stage the first thousand-lead validation"
```

### Task 6: Regenerate and prove the executable roadmap

**Files:**
- Regenerate: `docs/development-roadmap/execution-manifest.json`
- Regenerate: `docs/development-roadmap/EXECUTION_ORDER.md`
- Regenerate: `docs/development-roadmap/AGENT_EXECUTION_PLAN.md`
- Modify if required by deterministic contract: `backend/tests/unit/test_roadmap_validator.py`

**Interfaces:**
- Consumes: every annotated source task and validator rule from Tasks 1-5.
- Produces: one current manifest, topological order, safe agent waves, new fingerprint, and exact regression evidence.

- [ ] **Step 1: Regenerate from source**

```bash
python3 scripts/validate_roadmap.py --write
```

- [ ] **Step 2: Validate current artifacts and graph invariants**

```bash
python3 scripts/validate_roadmap.py --check
```

Confirm one root, no cycles, no future-milestone dependency, no missing task, no lock collision within a wave, every task assigned exactly once, and all new LAUNCH-03 stage tasks ordered behind their prior barrier.

- [ ] **Step 3: Run all validator tests from both supported working directories**

```bash
uv run --directory backend pytest tests/unit/test_roadmap_validator.py -q
cd backend && uv run pytest tests/unit/test_roadmap_validator.py -q
```

- [ ] **Step 4: Record deterministic hashes in the review evidence**

```bash
shasum -a 256 docs/development-roadmap/execution-manifest.json docs/development-roadmap/EXECUTION_ORDER.md docs/development-roadmap/AGENT_EXECUTION_PLAN.md
```

- [ ] **Step 5: Commit generated artifacts**

```bash
git add docs/development-roadmap/execution-manifest.json docs/development-roadmap/EXECUTION_ORDER.md docs/development-roadmap/AGENT_EXECUTION_PLAN.md backend/tests/unit/test_roadmap_validator.py scripts/validate_roadmap.py
git commit -m "docs: regenerate staged validation roadmap"
```

### Task 7: Refresh Graphify and run final repository verification

**Files:**
- Local ignored outputs only: `graphify-out/`

**Interfaces:**
- Consumes: the complete committed roadmap revision.
- Produces: a current local project graph and final publication evidence; no tracked Graphify output.

- [ ] **Step 1: Run Graphify incremental/full repair**

The current post-commit graph contains only the latest changed document and is incomplete. Rebuild the active checkout corpus following the Graphify skill, then query for the staged validation program. The answer must identify PRODUCT-02 authority, LAUNCH-03 stages, workflow/backend consumers, safety overrides, tests, and generated plan.

- [ ] **Step 2: Save the verified Graphify query result**

```bash
graphify save-result --question "How does the staged 100/200/300/400 thousand-lead validation program work?" --answer "PRODUCT-02 owns the immutable stage schedule and decision floors; LAUNCH-03 admits 100, then 200, then 300, then 400 new unique recipients only after signed CONTINUE barriers, while all safety stops override demand and the final cumulative ceiling is 1,000." --type query --outcome useful --nodes "Staged Validation Rule" "First Real Experiment"
graphify reflect
```

- [ ] **Step 3: Run all repository gates**

```bash
make lint
make typecheck
make test
make build
python3 scripts/check_secrets.py
git diff --check origin/main..HEAD
```

Expected: roadmap current; Ruff/ESLint/Pyright/TypeScript clean; all backend/frontend tests pass; backend wheel/sdist and Next.js production build succeed; secret scan and diff integrity pass.

- [ ] **Step 4: Review the complete main-branch diff**

Check for contradictory counts, stale generated line references, missing stage dependencies, unbounded sending authority, lost suppression obligations, and any statement that agent research proves demand. Resolve every Critical, Important, and Minor finding before publication.

- [ ] **Step 5: Push verified main**

```bash
git push origin main
git ls-remote --heads origin main
```

Confirm the remote SHA equals local `HEAD` and `git status --short --branch` is clean and synchronized.
