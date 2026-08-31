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
- split multi-milestone document work logically through per-task milestone metadata without fragmenting the 77 reference documents;
- generate one machine-readable manifest and one human-readable topological execution order;
- reject cycles, future-milestone dependencies, missing tasks, invalid stage order, and generated-file drift;
- update misleading document-level prerequisite prose where it contradicts the executable graph;
- make roadmap validation part of local and CI checks; and
- refresh Graphify after the tracked documentation and validator changes.

Out of scope:

- implementing any product roadmap task;
- changing the selected Pydantic AI, DBOS, PostgreSQL, Gmail, FastAPI, Next.js, or infrastructure architecture;
- changing the M0-M9 product outcomes or authorizing outreach;
- splitting all 77 reference documents into hundreds of individual files;
- estimating dates or parallel team capacity; and
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
<!-- roadmap-task id=PRODUCT-01-T01 milestone=M0 depends_on=ROADMAP-ROOT-T01 -->
- [ ] **Capture the M0 bet —** Input: ...
```

The syntax is deliberately narrow:

- `id` matches `^[A-Z][A-Z0-9]*-[0-9]{2}-T[0-9]{2}$`, except the root index may use `ROADMAP-ROOT-TNN`;
- the document prefix equals the file's `**Document ID:**` value;
- task numbers start at `T01`, increase contiguously in source order, and never encode the milestone so moving a task between gates does not change its identity;
- `milestone` is exactly one of `M0` through `M9`;
- `depends_on` is `-` only for a true graph root, otherwise a comma-separated list of task IDs with no spaces;
- the metadata line must be immediately followed by one unchecked implementation checkbox;
- acceptance, test-strategy, and maintenance checkboxes outside `## Ordered implementation tasks` are not execution nodes; and
- source order inside one document must be milestone-monotonic, although dependencies—not file position—remain authoritative.

Every non-root task must name at least one dependency. The default document-local relationship is sequential: `T02` depends on `T01`, and so on. A task may additionally depend on final prerequisite tasks from other documents. This intentionally favors a safe, comprehensible solo-developer sequence over speculative parallelism.

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
      "depends_on": ["ROADMAP-ROOT-T01"]
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

The root roadmap README links to both generated artifacts and states that subsystem directory order and prose prerequisites are non-authoritative when they conflict with validated task metadata.

## Validator architecture

Create `scripts/validate_roadmap.py` using only the Python standard library. It exposes pure parsing, validation, topological-sort, and rendering functions plus a CLI:

```text
python3 scripts/validate_roadmap.py --check
python3 scripts/validate_roadmap.py --write
```

`--check` is read-only and exits nonzero with deterministic, path-and-line diagnostics when any invariant fails or either generated artifact is stale. `--write` validates source metadata first, writes both generated artifacts atomically, rereads them, and exits nonzero if the resulting files do not match the renderers.

The validator enforces:

1. all 77 roadmap task documents are present in the root manifest and have one unique document ID;
2. every ordered implementation checkbox has exactly one adjacent metadata record and no orphan metadata exists;
3. task IDs are unique, contiguous within their document, and match their document ID;
4. milestones are valid and nondecreasing within a document;
5. every non-root task has at least one known dependency and root tasks are explicitly allowlisted;
6. no task depends on itself, a later milestone, or an unknown task;
7. the directed graph is acyclic, with an explicit cycle path in the diagnostic;
8. deterministic topological ordering uses milestone number, root-manifest document order, task number, and task ID as stable tie-breakers;
9. every generated source path and Markdown link resolves;
10. generated JSON and Markdown exactly equal current renderer output in `--check` mode; and
11. the final graph contains exactly the number of ordered implementation checkboxes parsed from source.

The script must never edit the 77 source documents. Source metadata edits remain reviewable changes made by the roadmap refactor; generation only changes the two declared artifacts.

## Test design

Add `backend/tests/unit/test_roadmap_validator.py`. Tests invoke real parser and renderer behavior against temporary miniature roadmap trees, using hand-written expected task orders and diagnostics. Required cases:

- a valid graph produces deterministic JSON and Markdown;
- an ordered checkbox without metadata fails;
- orphan or duplicate metadata fails;
- duplicate/noncontiguous/wrong-prefix task IDs fail;
- unknown milestone and decreasing document milestone fail;
- unknown, empty, self, and future-milestone dependencies fail;
- a same-milestone cycle reports the concrete cycle;
- stable tie-breaking produces the hand-checked order;
- stale generated JSON or Markdown fails in `--check` mode;
- `--write` followed by `--check` succeeds; and
- the real 77-file roadmap passes and contains the expected parsed task count.

Tests must follow red-green-refactor. The first test run must fail because the validator module is absent; implementation then proceeds only far enough to satisfy each failing behavior.

## Repository integration

- Add a `roadmap` Make target that runs `python3 scripts/validate_roadmap.py --check`.
- Make `lint`, `test`, and CI execute the roadmap check without requiring backend dependency installation.
- Update the root README and roadmap README with the new execution command and artifact links.
- Keep Graphify output ignored. After all tracked changes, run the documented incremental Graphify update and save the useful result in local memory.

## Failure behavior

Any validator failure blocks roadmap execution and CI. Agents must not guess around a missing dependency, manually edit generated artifacts, or treat a cycle as permission to implement both sides simultaneously. They must repair the source metadata or milestone assignment, regenerate, and retain the validator output.

If a task legitimately needs an interface from a later operational stage, split the provider task into an earlier contract task and a later integration/evidence task. Lowering a milestone merely to silence the validator is forbidden because it hides work rather than removing the dependency.

## Migration sequence

1. Build the validator and fixture tests first.
2. Add task metadata to the smallest M0-M2 slice and verify generation.
3. Migrate M3-M5, correcting agent/provider activation dependencies.
4. Migrate M6-M7, correcting Gmail, security, privacy, telemetry, and operator-control staging.
5. Migrate M8-M9, correcting testing, infrastructure, launch, and public-ingress staging.
6. Generate the complete manifest and execution order.
7. Update root instructions, Makefile, and CI.
8. Run focused tests, the validator, full repository verification, independent review, and Graphify incremental update.

Each migration step must leave no duplicate task IDs and must not claim that a planned product capability exists.

## Acceptance criteria

- All 389 current ordered implementation checkboxes have stable task IDs, exact milestones, and explicit dependencies.
- The validator reports zero missing metadata, unknown dependencies, milestone inversions, and cycles.
- The generated manifest contains exactly 389 tasks unless source task count changes intentionally in the same reviewed diff.
- `EXECUTION_ORDER.md` lists exactly the same task IDs once each in deterministic topological order.
- Known cycles and forward references are eliminated through staged task dependencies rather than waived.
- Root and per-document prose no longer contradicts the executable graph.
- `make roadmap`, focused validator tests, existing backend/frontend tests, lint, typecheck, build, and generated-contract checks pass.
- Independent task and whole-branch review report no unresolved Critical or Important findings.
- Graphify is incrementally refreshed after the tracked changes.
- No generated Graphify artifact is committed and no roadmap task is marked complete merely because this dependency refactor is complete.
