# Executable Roadmap Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for serial implementation/review loops and superpowers:dispatching-parallel-agents only for the four explicitly independent read-only semantic-audit slices. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the interrupted executable-roadmap refactor and generate an exact, dependency-safe multi-agent plan for all 389 Alon AI implementation tasks.

**Architecture:** Resume from the reviewed validator/generator at integration commit `2343eb1`, not from the original design commit. Four read-only agents independently audit disjoint consumer-milestone slices of the candidate dependency matrix; one adjudicator owns any matrix corrections; one source-application task then writes the reviewed metadata and generated artifacts. Product development remains blocked until the complete graph, generated plan, repository checks, and independent final review pass.

**Tech Stack:** Python 3.13 standard library, pytest, Ruff, Pyright, Markdown, JSON, Git worktrees, GitHub Actions, Graphify

**Spec:** `docs/superpowers/specs/2026-08-31-executable-roadmap-dependency-graph-design.md`

## Recovered state

- Integration branch: `codex/development-roadmap`
- Integration head: `2343eb1d5aea11237758df4476a9795d775c0be3`
- Reviewed validator implementation: `scripts/validate_roadmap.py`
- Reviewed validator tests: `backend/tests/unit/test_roadmap_validator.py`
- Candidate builder: `/private/tmp/alon-ai-executable-roadmap/build_final_candidate.py`
- Candidate matrix: `/private/tmp/alon-ai-executable-roadmap/metadata-matrix-final.md`
- Candidate validation: `/private/tmp/alon-ai-executable-roadmap/metadata-matrix-final-validation.json`
- Candidate state: 389 tasks, 892 edges, 580 cross-document edges, 344 waves, maximum wave size 3, zero structural errors, semantic status `requires_independent_review`
- Pending isolated fix: commit `54f3ecd9aa3125eedf90a103a7ca51fb90fc71fb` on `agent/roadmap-test-import`

## Global constraints

- Do not add, remove, or implement a product capability outside the approved roadmap.
- Do not begin any product task until the executable-roadmap validator and all three generated artifacts pass.
- Preserve exactly 389 ordered implementation tasks unless an independently reviewed semantic defect proves that a split is unavoidable.
- Preserve the exact M0-M9 milestone order and sole root `PRODUCT-01-T01`.
- A dependency edge is valid only when the provider task's verbatim `Output:` supplies a requirement in the consumer task's verbatim `Input:`.
- Do not infer edges from folder order, whole-document prerequisites, similar names, or downstream mentions.
- Keep all source task `Input:`, `Operation:`, `Output:`, `Test evidence:`, and `Failure behavior:` clauses semantically intact unless a review finding identifies a concrete contradiction.
- One coordinator owns the integration checkout. Audit agents are read-only. Any implementation agent works in its own worktree and branch.
- Never run more than four implementation agents or nine total live agents. The parallel audit below uses four read-only agents and one coordinator.
- The four semantic-audit slices are partitioned by consumer milestone, so every cross-document edge appears in exactly one slice.
- No source edit occurs until all four audit reports and the split-preservation review are adjudicated.
- Every implementation change gets an independent spec/quality review before integration.
- Follow strict red-green-refactor for any new behavior. Existing reviewed behavior is characterized and verified, not silently rewritten.
- Use Graphify before broad repository discovery and refresh it after final tracked changes.
- Do not push until the full repository verification and final review pass.

---

### Task 1: Verify and integrate the backend-cwd test import repair

**Files:**

- Modify through cherry-pick: `backend/tests/unit/test_roadmap_validator.py`
- Read: `/private/tmp/alon-ai-executable-roadmap/test-import-fix-report.md`
- Review range: `2343eb1d5aea11237758df4476a9795d775c0be3..54f3ecd9aa3125eedf90a103a7ca51fb90fc71fb`

**Interfaces:**

- Consumes: the reviewed validator API at integration head `2343eb1`.
- Produces: validator tests importable from repository root and from `backend/`, without making `scripts` a Python package or changing production code.

- [ ] **Step 1: Reproduce the integration failure at the current integration head.**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/unit/test_roadmap_validator.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'scripts'` before the repair is integrated.

- [ ] **Step 2: Independently review the isolated fix.**

Dispatch one reviewer with the exact diff range, report path, and these requirements: only the test import boundary may change; real validator behavior and assertions must remain unchanged; backend-cwd pytest and Pyright must resolve the test module.

Expected: spec-compliance and quality verdicts, with no unresolved Critical or Important finding.

- [ ] **Step 3: Integrate the reviewed commit.**

Run from the integration checkout:

```bash
git cherry-pick 54f3ecd9aa3125eedf90a103a7ca51fb90fc71fb
```

Expected: one-file clean cherry-pick.

- [ ] **Step 4: Verify both invocation boundaries.**

Run:

```bash
backend/.venv/bin/python -m pytest backend/tests/unit/test_roadmap_validator.py -q
cd backend && .venv/bin/python -m pytest tests/unit -q
cd backend && .venv/bin/pyright --pythonpath .venv/bin/python
backend/.venv/bin/ruff check backend/tests/unit/test_roadmap_validator.py
backend/.venv/bin/ruff format --check backend/tests/unit/test_roadmap_validator.py
```

Expected: 159 focused validator tests pass, all backend unit tests pass, Pyright reports zero errors, and Ruff passes.

- [ ] **Step 5: Record the integrated head and evidence in the continuation ledger.**

Output: exact commit, commands, counts, and reviewer verdict. Failure behavior: revert only the cherry-pick with a new commit or resume the fix agent; do not modify validator behavior to hide an import defect.

### Task 2: Audit all candidate dependency edges in four parallel read-only slices

**Files:**

- Read: `/private/tmp/alon-ai-executable-roadmap/metadata-matrix-final.md`
- Read: `/private/tmp/alon-ai-executable-roadmap/metadata-matrix-final-validation.json`
- Read: all 77 files under `docs/development-roadmap/00-product-strategy/` through `12-launch-and-operations/`
- Create outside Git: `/private/tmp/alon-ai-executable-roadmap/audits/m0-m2.md`
- Create outside Git: `/private/tmp/alon-ai-executable-roadmap/audits/m3-m5.md`
- Create outside Git: `/private/tmp/alon-ai-executable-roadmap/audits/m6-m7.md`
- Create outside Git: `/private/tmp/alon-ai-executable-roadmap/audits/m8-m9.md`

**Interfaces:**

- Consumes: the complete candidate graph and source-quoted cross-document edge appendix.
- Produces: four non-overlapping semantic verdict sets whose union covers every one of the 580 cross-document edges, every count-neutral source reorder in the slice, every prerequisite-header rewrite in the slice, and the relevant subset of 24 rejected split proposals.

- [ ] **Step 1: Freeze audit ownership by consumer milestone.**

Assign exactly:

- Agent A: consumers in M0, M1, or M2.
- Agent B: consumers in M3, M4, or M5.
- Agent C: consumers in M6 or M7.
- Agent D: consumers in M8 or M9.

Each agent is read-only for the repository and candidate builder. It writes only its assigned report path and may not spawn another agent.

- [ ] **Step 2: Run the four audits concurrently.**

Each agent must verdict every assigned edge as `KEEP`, `REMOVE`, `REPLACE`, or `BLOCKED`, quoting the provider `Output:`, consumer `Input:`, and exact reason. It must also verdict every assigned task milestone/mode/lock tuple, source reorder, prerequisite-header rewrite, and rejected split preservation claim.

Required rejection rules:

- an output does not actually supply the named input;
- the edge exists only to impose order;
- the dependency comes from a later milestone;
- a local predecessor or static/external input was lost;
- a distinct deliverable was collapsed to preserve the 389 count;
- a serial authority task was marked parallel;
- two tasks can share a generated wave despite touching the same lock; or
- task prose was rewritten to manufacture evidence for an edge.

- [ ] **Step 3: Verify coverage mechanically.**

Run a read-only checker that compares report consumer/provider pairs with the candidate JSON. Expected: exactly 580 unique reviewed cross-document pairs, zero missing, zero duplicate, zero out-of-slice assignment.

- [ ] **Step 4: Keep the repository unchanged.**

Run:

```bash
git status --short
```

Expected: no tracked change from the four audit agents. Failure behavior: discard the offending audit worktree/report and rerun that slice read-only.

### Task 3: Adjudicate semantic findings and finalize the 389-task matrix

**Files:**

- Modify outside Git: `/private/tmp/alon-ai-executable-roadmap/build_final_candidate.py`
- Regenerate outside Git: `/private/tmp/alon-ai-executable-roadmap/metadata-matrix-final.md`
- Regenerate outside Git: `/private/tmp/alon-ai-executable-roadmap/metadata-matrix-final-validation.json`
- Read: the four Task 2 audit reports

**Interfaces:**

- Consumes: complete four-slice semantic review evidence.
- Produces: one candidate in which every retained edge has an independent `KEEP` verdict, every `REMOVE`/`REPLACE` finding is applied, and every rejected split has a reviewed preservation ruling.

- [ ] **Step 1: Dispatch one adjudicator after all four audits complete.**

The adjudicator may modify only the scratch builder and scratch outputs. It must not edit repository sources. It resolves every non-`KEEP` row individually and records the before/after edge set and any task-clause change.

- [ ] **Step 2: Regenerate the candidate.**

Run:

```bash
python3 /private/tmp/alon-ai-executable-roadmap/build_final_candidate.py
```

Expected structural evidence: 389 tasks, 389 topological nodes, zero unknown dependencies, zero duplicate dependencies, zero future edges, zero cycles, zero milestone inversions, zero serial-lock violations, complete wave coverage, maximum wave size at most four, and zero placeholders.

- [ ] **Step 3: Require semantic closure.**

The final audit summary must contain exactly the retained cross-document edge count, with every retained pair mapped to one audit `KEEP` verdict. Any unresolved `BLOCKED`, missing pair, circularly rewritten input, or unreviewed split keeps Task 3 open.

- [ ] **Step 4: Run an independent whole-matrix reviewer.**

The reviewer receives the approved spec, four slice reports, final candidate Markdown/JSON, and builder diff. It checks semantic sufficiency, the DBOS/Temporal convergence branch, M1/M6/M8/M9 gates, all 24 split rulings, and exact source amendment instructions.

Expected: spec compliant and quality approved with no Critical or Important finding.

### Task 4: Apply the reviewed source metadata and task corrections

**Files:**

- Modify: the 77 root-manifest task documents under `docs/development-roadmap/`
- Modify: `docs/development-roadmap/README.md`
- Do not modify: generated artifacts, `scripts/validate_roadmap.py`, tests, Makefile, CI, application code

**Interfaces:**

- Consumes: the independently approved candidate matrix and exact source amendment plan.
- Produces: all 389 source checkboxes with adjacent task metadata, corrected milestone staging, reviewed dependencies, mode/locks, and aligned prerequisite prose.

- [ ] **Step 1: Apply only the candidate's exact source amendments.**

Use one implementation agent because the candidate is a single cross-corpus authority. Mechanical file partitioning is forbidden here: independent agents could each produce locally valid slices while breaking the global fingerprint or reorders.

- [ ] **Step 2: Verify source coverage before generation.**

Run:

```bash
python3 scripts/validate_roadmap.py --check
```

Expected: validation reaches only the missing/stale generated-artifact errors; it reports no source metadata, graph, milestone, lock, clause, link, or manifest error.

- [ ] **Step 3: Review the complete source diff.**

Dispatch one reviewer with the approved candidate, source diff, and spec. Expected: every source change is candidate-backed, all 389 identities are preserved, and no product implementation/readiness claim is introduced.

### Task 5: Generate artifacts and wire the repository gate

**Files:**

- Generate: `docs/development-roadmap/execution-manifest.json`
- Generate: `docs/development-roadmap/EXECUTION_ORDER.md`
- Generate: `docs/development-roadmap/AGENT_EXECUTION_PLAN.md`
- Modify: `README.md`
- Modify: `docs/development-roadmap/README.md`
- Modify: `Makefile`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**

- Consumes: the complete validated 389-task source graph.
- Produces: the exact human and machine execution views plus mandatory local/CI validation.

- [ ] **Step 1: Generate all three artifacts atomically per file.**

Run:

```bash
python3 scripts/validate_roadmap.py --write
python3 scripts/validate_roadmap.py --check
```

Expected: `roadmap artifacts are current`, identical graph fingerprints in both Markdown files, exactly 389 manifest tasks, and exactly one wave assignment per task.

- [ ] **Step 2: Add the repository validation entry points.**

Add `roadmap` to `.PHONY`; implement it as `python3 scripts/validate_roadmap.py --check`; make local validation and CI run it without requiring backend dependency installation. Link the three generated artifacts from both README surfaces without copying their contents.

- [ ] **Step 3: Verify the generated multi-agent contract.**

Assert mechanically: no wave has more than four implementers; no same-wave dependency exists; no same-wave lock intersection exists; every serial task is alone; milestones never mix; worktree/branch names are unique; reviewer/merge assignments exist; and the cross-document appendix equals the retained edge set.

- [ ] **Step 4: Independently review the generated plan and integration diff.**

Expected: a new agent can identify the exact first wave, number of agents, task IDs, worktrees, dependencies, locks, review assignments, merge order, and barrier without reading folder order as execution order.

### Task 6: Run the final repository gate, refresh Graphify, and publish the branch

**Files:**

- Verify all tracked changes
- Update ignored local `graphify-out/`
- Push branch `codex/development-roadmap`

**Interfaces:**

- Consumes: Tasks 1-5 reviewed commits.
- Produces: a pushed branch whose roadmap plan is executable and whose first product wave is discoverable without starting blocked work.

- [ ] **Step 1: Run fresh complete verification.**

Run:

```bash
UV_CACHE_DIR=/private/tmp/alon-ai-roadmap-uv-cache make roadmap
UV_CACHE_DIR=/private/tmp/alon-ai-roadmap-uv-cache make generate
UV_CACHE_DIR=/private/tmp/alon-ai-roadmap-uv-cache make lint
UV_CACHE_DIR=/private/tmp/alon-ai-roadmap-uv-cache make typecheck
UV_CACHE_DIR=/private/tmp/alon-ai-roadmap-uv-cache make test
UV_CACHE_DIR=/private/tmp/alon-ai-roadmap-uv-cache make build
python3 scripts/check_secrets.py
git diff --check
git status --short
```

Expected: every command exits zero, generated OpenAPI/client files have no unintended drift, and only intended tracked files are changed before commit.

- [ ] **Step 2: Run the final whole-branch review.**

Review from initial completion-plan base through current head against the approved spec, this plan, the continuation ledger, all deferred findings, and the exact generated artifacts. One fix wave and one scoped re-review are allowed; unresolved load-bearing findings block publication.

- [ ] **Step 3: Refresh Graphify after the tracked files are final.**

Run the repository's documented incremental update, confirm graph health, query the executable-roadmap/agent-wave concepts, and save the useful result. Keep all Graphify outputs ignored.

- [ ] **Step 4: Commit and push.**

Use focused commit messages for the source graph and generated/integration gate. Then run:

```bash
git push origin codex/development-roadmap
git rev-parse HEAD
git ls-remote origin refs/heads/codex/development-roadmap
```

Expected: local and remote branch hashes are identical. Failure behavior: report the exact failed gate and do not claim the roadmap or branch is complete.
