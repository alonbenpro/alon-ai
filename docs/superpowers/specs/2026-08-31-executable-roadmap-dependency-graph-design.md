# Executable Roadmap Dependency Graph Design

**Date:** 2026-08-31  
**Status:** Approved by the operator on 2026-08-31  
**Audience:** The solo developer and every agent executing the Alon AI roadmap

## Purpose

Turn the existing 77-file development roadmap from a human-readable set of subsystem documents into a deterministic, machine-validated execution graph. The M0-M9 ladder remains the product authority, but every implementation checkbox gains a stable identity, an exact milestone, and explicit prerequisites so an agent can select the next unblocked task without inferring order from folder names or prose.

This change fixes a real defect in the current documentation system: several multi-milestone files use whole-document prerequisites even though only an early subset is needed, which creates apparent future dependencies and cycles. Examples include the M3 lead-research task referring to M4 evidence, mutual SEC-02/SEC-03 and SEC-04/SEC-05 prerequisites, Gmail workflow/provider mutual references, and M1/M6 test work referring to M8 consolidation documents. The corrected graph must represent staged work directly instead of relying on a reader to reinterpret those statements.

## Scope

In scope:

- assign a stable task ID to every checkbox inside every `## Ordered implementation tasks` section;
- assign each task to exactly one milestone from M0 through M9;
- record every task prerequisite as an explicit task ID;
- declare every task's execution mode and exclusive resource locks;
- split multi-milestone document work logically through per-task milestone metadata without fragmenting the 77 reference documents;
- generate one machine-readable manifest, one human-readable topological execution order, and one exact multi-agent execution plan;
- reject cycles, future-milestone dependencies, missing tasks, invalid stage order, unsafe parallel waves, and generated-file drift;
- update misleading document-level prerequisite prose where it contradicts the executable graph;
- make roadmap validation part of local and CI checks; and
- refresh Graphify after the tracked documentation and validator changes.

Out of scope:

- implementing any product roadmap task;
- changing the selected Pydantic AI, DBOS, PostgreSQL, Gmail, FastAPI, Next.js, or infrastructure architecture;
- changing the M0-M9 product outcomes or authorizing outreach;
- splitting all 77 reference documents into hundreds of individual files;
- estimating dates, staffing a human team, or optimizing beyond the approved four-implementer safety cap; and
- treating generated task order as proof that any implementation milestone has passed.

## Approaches considered

### 1. Prose-only corrections

Edit the known contradictory prerequisite paragraphs and leave ordering to human interpretation. This has the smallest diff, but the same class of defect will recur because neither CI nor agents can prove that the prose is acyclic. Rejected.

### 2. Separate hand-maintained manifest

Keep the Markdown untouched and create a JSON or YAML task graph by hand. This is easy to parse, but it creates two authorities: checkbox prose and a separate graph. Drift is inevitable across 389 implementation checkboxes. Rejected.

### 3. Inline source metadata with generated views

Place one strict metadata comment immediately before each ordered implementation checkbox. Parse those comments as the source of truth, then generate JSON and Markdown views deterministically. This keeps the dependency declaration beside the task it governs, remains readable in ordinary Markdown, requires no new package, and lets CI detect drift. Selected.

## Source task contract

Every checkbox inside a `## Ordered implementation tasks` section has exactly one preceding metadata line:

```markdown
<!-- roadmap-task id=PRODUCT-01-T01 milestone=M0 depends_on=- mode=parallel locks=product-contracts -->
- [ ] **Capture the M0 bet —** Input: ...
```

The syntax is deliberately narrow:

- `id` matches `^[A-Z][A-Z0-9]*-[0-9]{2}-T[0-9]{2}$`;
- the document prefix equals the file's `**Document ID:**` value;
- task numbers start at `T01`, increase contiguously in source order, and never encode the milestone so moving a task between gates does not change its identity;
- `milestone` is exactly one of `M0` through `M9`;
- `depends_on` is `-` only for a true graph root, otherwise a comma-separated list of task IDs with no spaces;
- `mode` is exactly `parallel` or `serial`;
- `locks` is a comma-separated list from the closed lock vocabulary below, with no spaces or duplicates;
- the metadata line must be immediately followed by one unchecked implementation checkbox;
- acceptance, test-strategy, and maintenance checkboxes outside `## Ordered implementation tasks` are not execution nodes; and
- source order inside one document must be milestone-monotonic, although dependencies—not file position—remain authoritative.

Every non-root task must name at least one dependency. The default document-local relationship is sequential: `T02` depends on `T01`, and so on. A task may additionally depend on final prerequisite tasks from other documents. This intentionally favors a safe, comprehensible solo-developer sequence over speculative parallelism.

### Root authority and cross-document edge assignment

The sole true graph root is `PRODUCT-01-T01`. `scripts/validate_roadmap.py` owns this closed allowlist as a Python constant, `ROOT_TASK_IDS = frozenset({"PRODUCT-01-T01"})`; it is not another source field, config file, or user-selectable CLI input. A task may use `depends_on=-` if and only if its ID is in that constant, and every allowlisted root must use `depends_on=-`. The validator rejects every other root declaration, an allowlisted task with dependencies, and any non-root task without at least one dependency.

Assign cross-document dependencies by a reviewable source-to-source procedure, not by intuition about folders or document headers:

1. For each consumer task, first retain the default dependency on its immediately preceding task in the same document unless a documented graph root is intended.
2. Read the consumer checkbox's verbatim `Input:` clause and identify the exact provider task whose verbatim `Output:` clause supplies that input. Add only that provider task ID to `depends_on`; preserve a small review table for each non-local edge in the refactor review record: `provider ID + quoted Output -> consumer ID + quoted Input + applicable staging ruling`.
3. When more than one provider output is required, name each provider ID and quote the distinct input it satisfies. When an input is only a document-local continuation, do not invent an extra cross-document edge.
4. Check every proposed edge against the milestone-specific staging rulings below, especially the M1 harness, M3 offline-agent, Gmail-contract-before-workflow, security-interface-first, privacy/telemetry, cost-accounting, testing-ownership, and M8/M9 deployment boundaries. Split an early contract task from a later integration/evidence task when that is the only honest way to avoid a future dependency.
5. Reject blind whole-document prerequisites, automatically inferred folder-order edges, and dependencies justified only by a later consumer mentioning the provider. The metadata graph contains only task-level, evidence-backed edges; prose remains descriptive.

The review table is review evidence, not a second execution authority: the adjacent metadata remains the sole graph input. This procedure makes each cross-document edge explainable without adding a free-form metadata attribute that the validator cannot reliably enforce.

## Multi-agent execution contract

The roadmap supports bounded parallel implementation only after the dependency graph and resource locks prove that tasks are independent. Folder separation, different filenames, or a large ready frontier is insufficient evidence.

### Exact agent limits

- One coordinator agent, identified as `C0`, owns the integration branch, dependency-evidence checks, wave assignment, merge order, status records, and milestone gates.
- A wave may contain one to four implementation agents, identified as `I1` through `I4`. Four is the hard implementation-concurrency cap even when the graph exposes a wider frontier.
- Each completed implementation task receives one read-only review agent, identified as `R1` through `R4`, before merge. Reviewers may overlap unfinished implementers in the same wave.
- The absolute live-agent ceiling is nine: one coordinator, four implementers, and four reviewers. The number of worktrees with unmerged implementation changes remains at most four.
- A `serial` task is the only implementation task in its wave. Review and coordinator roles do not convert serial implementation into parallel implementation.
- A barrier closes every wave: all implementation tasks must be reviewed, merged in the generated order, retested after integration, and recorded complete before any task in the next wave starts.

These are project safety limits, not claims about the Codex platform's technical slot count. The cap reflects one solo operator's review and integration capacity.

### Closed exclusive-lock vocabulary

Locks represent shared implementation authority, not merely source directories:

- `roadmap-root`
- `product-contracts`
- `architecture-contracts`
- `database-schema`
- `migration-head`
- `workflow-runtime`
- `agent-runtime`
- `agent-artifacts`
- `provider-contracts`
- `gmail-side-effects`
- `backend-domain`
- `openapi-contract`
- `frontend-client`
- `security-runtime`
- `compliance-policy`
- `telemetry-catalog`
- `test-command-registry`
- `dependency-lockfiles`
- `compose-topology`
- `ci-release`
- `backup-restore`
- `live-environment`
- `milestone-gate`

Two tasks with any intersecting lock cannot share a wave. Every task declares at least one lock. Adding or renaming a lock requires an approved architecture-spec change; arbitrary per-task strings are invalid.

The following locks force `mode=serial`: `migration-head`, `gmail-side-effects`, `security-runtime`, `openapi-contract`, `frontend-client`, `test-command-registry`, `dependency-lockfiles`, `compose-topology`, `ci-release`, `backup-restore`, `live-environment`, and `milestone-gate`. This deliberately serializes migrations, canonical generated contracts, credentials, live external effects, releases, deployment, recovery, and gate evidence.

### Worktree, branch, and merge protocol

Every implementation task runs in a separate Git worktree and branch created from the exact integration-branch commit recorded at wave start:

```text
worktree: ../alon-ai-task-<lowercase-task-id>
branch:   agent/<lowercase-task-id>
```

An implementer receives only its task definition, dependency evidence, allowed locks/surfaces, acceptance commands, base commit, and report path. It may not start a dependent task, edit the integration checkout, merge, push, widen its locks, or spawn another implementation agent.

The coordinator assigns one reviewer to the task branch when the implementer reports completion. After approval, `C0` integrates branches one at a time in the generated merge order. Every branch after the first is rebased or merged onto the new integration head and reruns its declared verification before acceptance, even when Git reports no textual conflict. Failure returns only that task to its implementer/reviewer loop; it never permits the next wave to start.

### Deterministic wave construction

The generator builds waves within one milestone at a time:

1. A candidate is ready only when all dependencies completed in earlier waves. A dependency in the current wave does not count.
2. Candidates are scanned in deterministic topological order.
3. If the first candidate is `serial`, it forms a one-task wave.
4. Otherwise, add up to four `parallel` candidates whose lock sets do not intersect any selected task.
5. Deferred candidates remain eligible for the next wave; no candidate may skip an unfinished earlier milestone gate.
6. The generated merge order equals the selected task order.

This conservative greedy schedule is reproducible and reviewable. It does not claim theoretical maximum graph parallelism; it produces the exact safe plan this solo-operated project will use.

## Milestone-specific staging rules

Whole-document status and prerequisite prose is descriptive. The inline task graph is the executable authority. Multi-milestone documents must assign their tasks to the earliest gate at which that exact output is required, while preserving later operational completion tasks at their later gate.

The following rulings remove the known cycles:

1. **M1 testing is self-contained.** WF-01 owns the disposable DBOS/Gmail acceptance harness. TEST-01 defines the early test/evidence convention before that harness. TEST-03 and TEST-04 contain M1 scenario tasks that depend on those M1 foundations, while their product-wide recovery and Gmail suites remain M6/M8. No M1 task depends on an M8 task.
2. **M3 agents remain offline.** AGENT-05 depends on M3 recorded provider fixtures and frozen lead-research inputs, not passing M4 evidence. M4 evidence is an activation input for M5 workflow use. AGENT-07 depends on M3 content-policy fixtures; M6 approval and sending remain later consumers.
3. **Gmail contracts precede orchestration.** Provider wire contracts and recorded fixtures precede WF-05. The workflow then composes those contracts. Live provider acceptance and reconciliation tests follow the workflow and gateway. Provider documents may consume workflow identifiers for later integration tasks but cannot make their initial contract tasks depend on WF-05.
4. **Security is interface-first.** SEC-01 Critical send/credential threat analysis precedes M6 credential and send work. SEC-03 key/credential foundations precede SEC-02 authentication; SEC-02 session integration may later feed SEC-03 rotation evidence, but the dependency is between later tasks rather than the two whole documents. SEC-04 test-isolation and prohibited-recipient policy tasks precede SEC-05 controls; SEC-04 M9 counsel/recipient-authority tasks consume the completed controls.
5. **Privacy and telemetry are staged.** SEC-06 minimization/redaction/retention-class contracts precede OBS-01. OBS-01 then enables later privacy operations and OBS-02 through OBS-05. SEC-06 M8 deletion, rights, and retention-operation evidence may depend on the observability stack without making its early privacy contract do so.
6. **Cost accounting begins in M3.** OBS-03 provider-call ledger and evaluation-cost tasks belong to M3 and use recorded fixtures. M6 Gmail budgets and M8 invoice/alert operations remain later tasks. An M3 cost task cannot depend on M6 suppression controls or M8 dashboards.
7. **Test ownership precedes specialized suites.** TEST-01's taxonomy, fixture isolation, evidence schema, and command conventions occur before the specialized tests that consume them. Its M8 consolidation/release tasks depend on the completed TEST-02 through TEST-06 suites, not the reverse.
8. **M8 private deployment precedes M9 public activation.** INFRA-03 private-runtime tasks depend only on M8 prerequisites. Its public-unsubscribe activation task is M9 and may depend on M9 legal/policy evidence.

## Generated artifacts

### Machine-readable manifest

`docs/development-roadmap/execution-manifest.json` is generated with this shape:

```json
{
  "schema_version": 1,
  "milestones": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"],
  "tasks": [
    {
      "id": "PRODUCT-01-T01",
      "milestone": "M0",
      "document_id": "PRODUCT-01",
      "title": "Capture the M0 bet",
      "source": "docs/development-roadmap/00-product-strategy/01-product-scope.md",
      "line": 129,
      "depends_on": [],
      "mode": "parallel",
      "locks": ["product-contracts"]
    }
  ]
}
```

Tasks appear in the validator's deterministic topological order. JSON uses UTF-8, two-space indentation, sorted object keys, and a final newline.

### Human execution order

`docs/development-roadmap/EXECUTION_ORDER.md` is generated from the same graph. It contains:

- a warning that it is generated and does not prove implementation status;
- exact regeneration and validation commands;
- totals by milestone and document;
- one section per milestone in M0-M9 order;
- a globally numbered task list showing ID, title, source link, and dependency IDs; and
- a frontier rule explaining that a task is executable only when every dependency has retained passing evidence.

### Multi-agent execution plan

`docs/development-roadmap/AGENT_EXECUTION_PLAN.md` is generated from the validated graph and lock sets. It contains:

- the exact role limits: `C0`, `I1..I4`, and `R1..R4`;
- the absolute nine-agent ceiling and four-implementer ceiling;
- worktree, branch, prompt-scope, review, integration, cleanup, and evidence rules;
- one section per deterministic wave with milestone, agent count, base prerequisite barrier, exact task-to-agent assignment, source link, dependencies, mode, locks, branch/worktree names, acceptance-evidence reference, reviewer assignment, merge order, and newly unlocked tasks;
- explicit one-agent waves for every serial task;
- a prohibition on starting the next wave until the current barrier closes; and
- recovery instructions for failed, conflicting, stale-base, or abandoned task branches.

For every task assignment, the plan's acceptance-evidence reference is the source link and verbatim verification clause retained by the validator. The coordinator copies that reference into the implementer prompt unchanged; backticked commands are the only commands copied as acceptance commands. The coordinator may add normal repository verification required by the task's declared locks, but may not substitute, broaden, or fabricate evidence commands in place of the source clause.

The file is operationally exact only for the SHA-256 source-graph fingerprint printed in its header. Any source-task metadata change alters that fingerprint, makes the file stale, and blocks `--check` until regeneration. A Git commit hash is not embedded because generating a file containing its own eventual commit hash would be circular.

The fingerprint is the lowercase SHA-256 hexadecimal digest of exactly these UTF-8 bytes, with no trailing newline: `json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`. `payload` is an object with keys `schema_version`, `milestones`, `root_task_ids`, `manifest_documents`, and `tasks`; `schema_version` is `1`, `milestones` is `M0` through `M9` in that order, `root_task_ids` is the sorted allowlist, and `manifest_documents` is the root-manifest source-path list in manifest order. `tasks` is the validated deterministic topological order. Each task object contains exactly `id`, `milestone`, `document_id`, `title`, `source`, `line`, `depends_on`, `mode`, `locks`, and `verification`; dependency and lock arrays retain their validated source order, and `verification` is the extracted clause defined below. This is the canonical input for the header in both generated Markdown files; a renderer must not hash a rendered file, platform newline conversion, an absolute path, generated timestamp, or a Git revision.

The root roadmap README links to all three generated artifacts and states that subsystem directory order and prose prerequisites are non-authoritative when they conflict with validated task metadata.

## Validator architecture

Create `scripts/validate_roadmap.py` using only the Python standard library. It exposes pure parsing, validation, topological-sort, and rendering functions plus a CLI:

```text
python3 scripts/validate_roadmap.py --check
python3 scripts/validate_roadmap.py --write
```

`--check` is read-only and exits nonzero with deterministic, path-and-line diagnostics when any invariant fails or any generated artifact is stale. `--write` validates source metadata first, writes all three generated artifacts atomically, rereads them, and exits nonzero if the resulting files do not match the renderers.

The root manifest is parsed only from `docs/development-roadmap/README.md`, starting immediately after the unique `## Complete file manifest mapped to vertical gates` heading and ending immediately before the next level-two heading, currently `## Launch promotion ladder`. Within those boundaries, the parser accepts only manifest-table rows whose first cell is a single backticked relative POSIX path matching ``(?:[0-9]{2}-[a-z0-9-]+/)+[0-9]{2}-[a-z0-9-]+\.md`` and whose second cell is exactly `M0` through `M9`; it ignores the table header and subsection headings. The path is resolved only under `docs/development-roadmap/`; leading slashes, backslashes, `.` or `..` segments, duplicate rows, rows outside the boundaries, malformed code spans, and any resolved path outside that directory are validation errors. The parsed row order is the root-manifest document order used for deterministic tie-breaking.

For every parsed ordered checkbox, the validator retains its source path, checkbox line, complete checkbox body, and a verbatim verification clause. The verification clause is the text beginning with the literal `Test evidence:` marker and ending immediately before the literal `Failure behavior:` marker in that checkbox body. Missing, repeated, or reversed markers are validation errors. `AGENT_EXECUTION_PLAN.md` links to that checkbox line and reproduces this clause verbatim as the acceptance-evidence reference. Implementer prompts receive that same source link and clause; any backticked command inside it is copied verbatim as an acceptance command, while a clause without a command remains evidence-only and does not authorize the generator or coordinator to invent one. This uses the existing task prose and adds no metadata field.

The validator enforces:

1. all 77 roadmap task documents are present in the root manifest and have one unique document ID;
2. every ordered implementation checkbox has exactly one adjacent metadata record and no orphan metadata exists;
3. task IDs are unique, contiguous within their document, and match their document ID;
4. milestones are valid and nondecreasing within a document;
5. every non-root task has at least one known dependency, and root declarations exactly match the validator-owned sole-root allowlist;
6. no task depends on itself, a later milestone, or an unknown task;
7. the directed graph is acyclic, with an explicit cycle path in the diagnostic;
8. deterministic topological ordering uses milestone number, root-manifest document order, task number, and task ID as stable tie-breakers;
9. every task has a valid mode and nonempty lock set from the closed vocabulary;
10. every serial-only lock appears only on a `serial` task;
11. deterministic waves contain at most four implementers, remain within one milestone, use only dependencies completed in earlier waves, and have pairwise-disjoint locks;
12. every generated source path and Markdown link resolves, and every task has one extractable verbatim `Test evidence:` clause followed by `Failure behavior:`;
13. generated JSON and both generated Markdown files exactly equal current renderer output in `--check` mode; and
14. the final graph contains exactly the number of ordered implementation checkboxes parsed from source.

The script must never edit the 77 source documents. Source metadata edits remain reviewable changes made by the roadmap refactor; generation only changes the three declared artifacts.

## Test design

Add `backend/tests/unit/test_roadmap_validator.py`. Tests invoke real parser and renderer behavior against temporary miniature roadmap trees, using hand-written expected task orders and diagnostics. Required cases:

- a valid graph produces deterministic JSON and both Markdown artifacts;
- an ordered checkbox without metadata fails;
- orphan or duplicate metadata fails;
- duplicate/noncontiguous/wrong-prefix task IDs fail;
- unknown milestone and decreasing document milestone fail;
- unknown, empty, self, and future-milestone dependencies fail;
- a same-milestone cycle reports the concrete cycle;
- unknown/empty/duplicate locks and invalid execution modes fail;
- a serial-only lock on a parallel task fails;
- a wave with a current-wave dependency, milestone crossing, shared lock, or fifth implementer fails;
- stable tie-breaking produces the hand-checked order;
- deterministic wave construction produces hand-checked task/agent/merge assignments;
- only `PRODUCT-01-T01` may be a root, root/dependency mismatches fail, and malformed root-manifest boundaries or paths fail;
- a missing, repeated, or malformed verification clause fails, while a valid clause is copied verbatim into the generated plan and prompt data;
- canonical fingerprint bytes remain stable for identical validated payloads and change for a manifest-order, task-metadata, source-line, or verification-clause change;
- stale generated JSON, execution-order Markdown, or agent-plan Markdown fails in `--check` mode;
- `--write` followed by `--check` succeeds; and
- the real 77-file roadmap passes and contains the expected parsed task count.

Tests must follow red-green-refactor. The first test run must fail because the validator module is absent; implementation then proceeds only far enough to satisfy each failing behavior.

## Repository integration

- Add a `roadmap` Make target that runs `python3 scripts/validate_roadmap.py --check`.
- Make `lint`, `test`, and CI execute the roadmap check without requiring backend dependency installation.
- Update the root README and roadmap README with the new execution command and artifact links.
- Document that the generated agent plan—not folder order—is the sole authority for parallel dispatch.
- Keep Graphify output ignored. After all tracked changes, run the documented incremental Graphify update and save the useful result in local memory.

## Failure behavior

Any validator failure blocks roadmap execution and CI. Agents must not guess around a missing dependency, manually edit generated artifacts, treat a cycle as permission to implement both sides simultaneously, or add an unreviewed lock to force concurrency. They must repair the source metadata, lock assignment, execution mode, or milestone assignment, regenerate, and retain the validator output.

A task branch that edits outside its declared locks or source-task scope is rejected and rerun with corrected metadata or a narrower diff. A merge conflict, stale base, failed integration test, missing review, abandoned agent, or incomplete evidence keeps the task and wave open. The coordinator may replace the agent, but cannot promote another task past the barrier.

If a task legitimately needs an interface from a later operational stage, split the provider task into an earlier contract task and a later integration/evidence task. Lowering a milestone merely to silence the validator is forbidden because it hides work rather than removing the dependency.

## Migration sequence

1. Build the validator and fixture tests first.
2. Add task metadata to the smallest M0-M2 slice and verify generation.
3. Migrate M3-M5, correcting agent/provider activation dependencies.
4. Migrate M6-M7, correcting Gmail, security, privacy, telemetry, and operator-control staging.
5. Migrate M8-M9, correcting testing, infrastructure, launch, and public-ingress staging.
6. Assign execution modes and exclusive locks, then generate the complete manifest, execution order, and agent execution plan.
7. Update root instructions, Makefile, and CI.
8. Run focused tests, the validator, full repository verification, independent review, and Graphify incremental update.

During steps 2 through 5, every edited checkbox receives syntactically complete metadata, including mode and locks. Step 6 is the cross-corpus review and correction of those assignments before generation; it is not permission to leave required fields blank in an earlier slice. The real repository's `--check` and `--write` remain full-corpus operations: until all 77 documents are annotated, their failure is expected and `--write` must not create or refresh real generated artifacts. Verify each staged slice only through the validator's pure parsing/rendering functions against a self-contained temporary miniature roadmap tree in the focused tests. Do not add a partial CLI mode, a partial root manifest, or partial generated artifacts. After step 6 confirms the complete graph, run the real `--write` once, then require real `--check` to pass before the integration changes in step 7.

Each migration step must leave no duplicate task IDs and must not claim that a planned product capability exists.

## Acceptance criteria

- All 389 current ordered implementation checkboxes have stable task IDs, exact milestones, and explicit dependencies.
- All 389 tasks have a validated execution mode and at least one closed-vocabulary lock.
- The validator reports zero missing metadata, unknown dependencies, milestone inversions, cycles, unsafe lock overlaps, and invalid waves.
- The generated manifest contains exactly 389 tasks unless source task count changes intentionally in the same reviewed diff.
- `EXECUTION_ORDER.md` lists exactly the same task IDs once each in deterministic topological order.
- `AGENT_EXECUTION_PLAN.md` assigns every task exactly once to a deterministic wave, with one to four implementers, separate worktree/branch names, reviewer assignment, merge order, and no same-wave dependency or lock conflict.
- The plan never exceeds four implementation agents or nine total live agents and makes every serial-only task a one-implementer wave.
- Known cycles and forward references are eliminated through staged task dependencies rather than waived.
- Root and per-document prose no longer contradicts the executable graph.
- `make roadmap`, focused validator tests, existing backend/frontend tests, lint, typecheck, build, and generated-contract checks pass.
- Independent task and whole-branch review report no unresolved Critical or Important findings.
- Graphify is incrementally refreshed after the tracked changes.
- No generated Graphify artifact is committed and no roadmap task is marked complete merely because this dependency refactor is complete.
