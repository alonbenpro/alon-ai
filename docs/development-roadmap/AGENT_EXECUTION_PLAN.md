# Agent Execution Plan

> Warning: generated for the source graph below; it does not prove implementation status.

- Source-graph fingerprint: `2e061a5b5b83a4a18b5f3de88896a2b32e5e7cdf4870145b17be44dea4a63271`
- Regenerate: `python3 scripts/validate_roadmap.py --write`
- Validate: `python3 scripts/validate_roadmap.py --check`

## Operating contract

- C0 owns integration, dependency evidence, wave assignment, merge order, status, and milestone gates.
- Implementers are I1..I4; read-only reviewers are R1..R4.
- The absolute live-agent ceiling is nine and the implementation/worktree ceiling is four.
- Each task uses its listed `agent/<task-id>` branch and sibling `../alon-ai-task-<task-id>` worktree from the exact wave-base integration commit.
- Prompts include only the assigned task, dependency evidence, declared locks/surfaces, source acceptance evidence, optional marked commands, base commit, and report path.
- Implementers may not start dependent tasks, edit the integration checkout, merge, push, widen declared locks, or spawn implementation agents.
- Generic or unmarked code spans in task evidence are evidence-only; only grammar-valid explicit `Command:` or `Commands:` spans become optional acceptance commands.
- C0 may add normal repository verification required by declared locks, but may not substitute, broaden, or fabricate evidence commands.
- Each reviewer checks only its completed task before C0 merges branches one at a time in generated merge order.
- After the first branch in a wave, each later branch is rebased or merged onto the updated integration head and reruns its declared verification before acceptance.
- C0 reruns declared verification after each integration, records retained evidence, and cleans up merged branches/worktrees.
- The next wave cannot start until every implementation is reviewed, merged, retested, recorded, and the barrier closes.
- A failed task returns only that task to its implementer/reviewer loop and never opens the next wave.
- Conflict, stale base, or abandonment keeps the task and wave open; repair or replace that task branch without promoting later work.

## Wave 1 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: none (graph root)

### I1 / R1 — `PRODUCT-01-T01`

- Source: [source](00-product-strategy/01-product-scope.md#L211)
- Dependencies: none
- Mode: `parallel`
- Locks: `product-contracts`
- Branch: `agent/product-01-t01`
- Worktree: `../alon-ai-task-product-01-t01`
- Acceptance evidence: [source](00-product-strategy/01-product-scope.md#L211) — Test evidence: schema validation plus operator signature.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-01-T02`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 2 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T01`

### I1 / R1 — `PRODUCT-01-T02`

- Source: [source](00-product-strategy/01-product-scope.md#L213)
- Dependencies: `PRODUCT-01-T01`
- Mode: `parallel`
- Locks: `product-contracts`
- Branch: `agent/product-01-t02`
- Worktree: `../alon-ai-task-product-01-t02`
- Acceptance evidence: [source](00-product-strategy/01-product-scope.md#L213) — Test evidence: completed M0 scope checklist.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-01-T03`, `PRODUCT-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 3 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T02`

### I1 / R1 — `PRODUCT-01-T03`

- Source: [source](00-product-strategy/01-product-scope.md#L215)
- Dependencies: `PRODUCT-01-T02`
- Mode: `parallel`
- Locks: `product-contracts`, `architecture-contracts`
- Branch: `agent/product-01-t03`
- Worktree: `../alon-ai-task-product-01-t03`
- Acceptance evidence: [source](00-product-strategy/01-product-scope.md#L215) — Test evidence: parsed exact-set/order and provider-before-consumer tests; reject extra artifacts/results, downstream commercial invention, agent side effects, and active-cohort mutation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-01-T04`, `WF-00-T01`, `TEST-01-T01`, `ARCH-03-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 4 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`

### I1 / R1 — `PRODUCT-01-T04`

- Source: [source](00-product-strategy/01-product-scope.md#L217)
- Dependencies: `PRODUCT-01-T03`
- Mode: `parallel`
- Locks: `product-contracts`
- Branch: `agent/product-01-t04`
- Worktree: `../alon-ai-task-product-01-t04`
- Acceptance evidence: [source](00-product-strategy/01-product-scope.md#L217) — Test evidence: every planned feature points to a milestone gate.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-00-T01`, `TEST-01-T01`, `ARCH-03-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 5 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T02`

### I1 / R1 — `PRODUCT-02-T01`

- Source: [source](00-product-strategy/02-success-metrics.md#L142)
- Dependencies: `PRODUCT-01-T02`
- Mode: `parallel`
- Locks: `product-contracts`
- Branch: `agent/product-02-t01`
- Worktree: `../alon-ai-task-product-02-t01`
- Acceptance evidence: [source](00-product-strategy/02-success-metrics.md#L142) — Test evidence: schema, tuple/set equality, demand-floor boundary, and duplicate-name/version tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-02-T02`, `PRODUCT-03-T01`, `WF-00-T01`, `TEST-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 6 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-02-T01`

### I1 / R1 — `PRODUCT-02-T02`

- Source: [source](00-product-strategy/02-success-metrics.md#L144)
- Dependencies: `PRODUCT-02-T01`
- Mode: `parallel`
- Locks: `product-contracts`
- Branch: `agent/product-02-t02`
- Worktree: `../alon-ai-task-product-02-t02`
- Acceptance evidence: [source](00-product-strategy/02-success-metrics.md#L144) — Test evidence: completeness query and operator signature.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-00-T01`, `TEST-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 7 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T02`, `PRODUCT-02-T01`

### I1 / R1 — `PRODUCT-03-T01`

- Source: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L124)
- Dependencies: `PRODUCT-01-T02`, `PRODUCT-02-T01`
- Mode: `serial`
- Locks: `product-contracts`, `compliance-policy`, `milestone-gate`
- Branch: `agent/product-03-t01`
- Worktree: `../alon-ai-task-product-03-t01`
- Acceptance evidence: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L124) — Test evidence: no Critical/High risk lacks owner, trigger, and response.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-03-T02`, `WF-00-T01`, `SEC-01-T01`, `TEST-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 8 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T01`

### I1 / R1 — `PRODUCT-03-T02`

- Source: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L126)
- Dependencies: `PRODUCT-03-T01`
- Mode: `serial`
- Locks: `product-contracts`, `milestone-gate`
- Branch: `agent/product-03-t02`
- Worktree: `../alon-ai-task-product-03-t02`
- Acceptance evidence: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L126) — Test evidence: operator signature linked to metric snapshot.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-00-T01`, `SEC-01-T01`, `TEST-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 9 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`

### I1 / R1 — `WF-00-T01`

- Source: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L67)
- Dependencies: `PRODUCT-01-T03`
- Mode: `parallel`
- Locks: `architecture-contracts`, `workflow-runtime`
- Branch: `agent/wf-00-t01`
- Worktree: `../alon-ai-task-wf-00-t01`
- Acceptance evidence: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L67) — Test evidence: `test_agents_and_workflows_cannot_import_gmail_send`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 10 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T01`

### I1 / R1 — `SEC-01-T01`

- Source: [source](08-security-and-compliance/01-threat-model.md#L119)
- Dependencies: `PRODUCT-03-T01`
- Mode: `parallel`
- Locks: `architecture-contracts`, `compliance-policy`
- Branch: `agent/sec-01-t01`
- Worktree: `../alon-ai-task-sec-01-t01`
- Acceptance evidence: [source](08-security-and-compliance/01-threat-model.md#L119) — Test evidence: static contract set equality with no owner/control gap.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-03-T01`, `SEC-03-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 11 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`, `SEC-01-T01`

### I1 / R1 — `DB-03-T01`

- Source: [source](02-database/03-leads-campaigns-and-messages.md#L254)
- Dependencies: `PRODUCT-01-T03`, `SEC-01-T01`
- Mode: `parallel`
- Locks: `architecture-contracts`, `provider-contracts`
- Branch: `agent/db-03-t01`
- Worktree: `../alon-ai-task-db-03-t01`
- Acceptance evidence: [source](02-database/03-leads-campaigns-and-messages.md#L254) — Test evidence: schema/discriminator/hash/golden-vector coverage and forbidden SQLAlchemy/runtime imports.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 12 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-01-T01`

### I1 / R1 — `SEC-03-T01`

- Source: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L93)
- Dependencies: `SEC-01-T01`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-03-t01`
- Worktree: `../alon-ai-task-sec-03-t01`
- Acceptance evidence: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L93) — Test evidence: tamper, nonce uniqueness, cross-purpose/environment/version denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 13 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `SEC-03-T01`

### I1 / R1 — `PROVIDER-01-T01`

- Source: [source](05-providers/01-gmail-oauth-and-adapter.md#L150)
- Dependencies: `DB-03-T01`, `SEC-03-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-01-t01`
- Worktree: `../alon-ai-task-provider-01-t01`
- Acceptance evidence: [source](05-providers/01-gmail-oauth-and-adapter.md#L150) — Test evidence: schema/discriminator, MIME golden vectors, fixture hash, no-network and no-product-row tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-01-T02`, `PROVIDER-02-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 14 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `PROVIDER-01-T01`

### I1 / R1 — `PROVIDER-01-T02`

- Source: [source](05-providers/01-gmail-oauth-and-adapter.md#L152)
- Dependencies: `PROVIDER-01-T01`, `DB-03-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-01-t02`
- Worktree: `../alon-ai-task-provider-01-t02`
- Acceptance evidence: [source](05-providers/01-gmail-oauth-and-adapter.md#L152) — Test evidence: `test_gmail_mime_is_rfc_stable_and_rejects_header_injection_or_second_recipient`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 15 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T01`

### I1 / R1 — `PROVIDER-02-T01`

- Source: [source](05-providers/02-gmail-history-sync.md#L90)
- Dependencies: `PROVIDER-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-02-t01`
- Worktree: `../alon-ai-task-provider-02-t01`
- Acceptance evidence: [source](05-providers/02-gmail-history-sync.md#L90) — Test evidence: `test_gmail_read_contract_error_timeout_nfc_and_size_matrix`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 16 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`

### I1 / R1 — `TEST-01-T01`

- Source: [source](10-testing/01-testing-strategy.md#L161)
- Dependencies: `PRODUCT-01-T03`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-01-t01`
- Worktree: `../alon-ai-task-test-01-t01`
- Acceptance evidence: [source](10-testing/01-testing-strategy.md#L161) — Test evidence: source-anchor resolver plus set-equality counts.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-01-T02`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 17 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T01`

### I1 / R1 — `TEST-01-T02`

- Source: [source](10-testing/01-testing-strategy.md#L163)
- Dependencies: `TEST-01-T01`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-01-t02`
- Worktree: `../alon-ai-task-test-01-t02`
- Acceptance evidence: [source](10-testing/01-testing-strategy.md#L163) — Test evidence: `T7-DOC-CONTRACT`, including exact 24 calls/zero runner recursion, `/tmp` positive, malicious handler/runner symlink/wrong-root/hash, unavailable=`30`, target mismatch=`50`, missing artifact=`40`, the reachable `T7-AWS-WITNESS-ACCEPT` row, and set-equality negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-01-T03`, `INFRA-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 18 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T02`

### I1 / R1 — `TEST-01-T03`

- Source: [source](10-testing/01-testing-strategy.md#L165)
- Dependencies: `TEST-01-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-01-t03`
- Worktree: `../alon-ai-task-test-01-t03`
- Acceptance evidence: [source](10-testing/01-testing-strategy.md#L165) — Test evidence: parallel-run collision, forbidden socket, real-address canary, stale fixture and cleanup-crash cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-04-T01`, `TEST-01-T04`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 19 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T01`, `PROVIDER-01-T02`, `TEST-01-T03`

### I1 / R1 — `TEST-04-T01`

- Source: [source](10-testing/04-gmail-side-effect-tests.md#L72)
- Dependencies: `PROVIDER-01-T02`, `TEST-01-T03`, `PROVIDER-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/test-04-t01`
- Worktree: `../alon-ai-task-test-04-t01`
- Acceptance evidence: [source](10-testing/04-gmail-side-effect-tests.md#L72) — Test evidence: schema/hash/PII/secret/cross-mailbox/tamper matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-04-T02`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 20 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T01`, `TEST-01-T02`, `TEST-04-T01`

### I1 / R1 — `TEST-04-T02`

- Source: [source](10-testing/04-gmail-side-effect-tests.md#L74)
- Dependencies: `TEST-04-T01`, `TEST-01-T02`, `PROVIDER-01-T01`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-04-t02`
- Worktree: `../alon-ai-task-test-04-t02`
- Acceptance evidence: [source](10-testing/04-gmail-side-effect-tests.md#L74) — Test evidence: live-row-in-offline, network escape, wrong fixture/profile/target, tamper, unavailable, and ambiguity negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 21 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T03`

### I1 / R1 — `TEST-01-T04`

- Source: [source](10-testing/01-testing-strategy.md#L167)
- Dependencies: `TEST-01-T03`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-01-t04`
- Worktree: `../alon-ai-task-test-01-t04`
- Acceptance evidence: [source](10-testing/01-testing-strategy.md#L167) — Test evidence: missing file, changed byte, interrupted upload, wrong commit and replay tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-01-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 22 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T01`, `SEC-01-T01`, `TEST-01-T01`, `TEST-01-T02`, `TEST-01-T03`, `TEST-01-T04`

### I1 / R1 — `WF-01-T01`

- Source: [source](03-workflows/01-dbos-production-acceptance-spike.md#L196)
- Dependencies: `WF-00-T01`, `SEC-01-T01`, `TEST-01-T01`, `TEST-01-T02`, `TEST-01-T03`, `TEST-01-T04`
- Mode: `serial`
- Locks: `database-schema`, `workflow-runtime`, `gmail-side-effects`, `live-environment`
- Branch: `agent/wf-01-t01`
- Worktree: `../alon-ai-task-wf-01-t01`
- Acceptance evidence: [source](03-workflows/01-dbos-production-acceptance-spike.md#L196) — Test evidence: project/scope/alias/recipient/schema/credential allowlist introspection and revocation drill.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-01-T02`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 23 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T01`

### I1 / R1 — `WF-01-T02`

- Source: [source](03-workflows/01-dbos-production-acceptance-spike.md#L198)
- Dependencies: `WF-01-T01`
- Mode: `serial`
- Locks: `workflow-runtime`, `agent-runtime`, `provider-contracts`, `gmail-side-effects`, `live-environment`
- Branch: `agent/wf-01-t02`
- Worktree: `../alon-ai-task-wf-01-t02`
- Acceptance evidence: [source](03-workflows/01-dbos-production-acceptance-spike.md#L198) — Test evidence: import/call-path, schema, denial, replay tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-01-T03`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 24 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T02`

### I1 / R1 — `WF-01-T03`

- Source: [source](03-workflows/01-dbos-production-acceptance-spike.md#L200)
- Dependencies: `WF-01-T02`
- Mode: `serial`
- Locks: `workflow-runtime`, `gmail-side-effects`, `security-runtime`, `telemetry-catalog`, `live-environment`
- Branch: `agent/wf-01-t03`
- Worktree: `../alon-ai-task-wf-01-t03`
- Acceptance evidence: [source](03-workflows/01-dbos-production-acceptance-spike.md#L200) — Test evidence: termination plus signature/hash-chain validation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-03-T03`, `ARCH-01-T01`, `WF-00-T02`, `WF-01-T04`, `TEST-03-T01`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 25 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T02`, `WF-01-T03`

### I1 / R1 — `PRODUCT-03-T03`

- Source: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L128)
- Dependencies: `PRODUCT-03-T02`, `WF-01-T03`
- Mode: `serial`
- Locks: `security-runtime`, `compliance-policy`
- Branch: `agent/product-03-t03`
- Worktree: `../alon-ai-task-product-03-t03`
- Acceptance evidence: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L128) — Test evidence: the M1 harness proves disable-before-effect, retained evidence, idempotent acknowledgement, and no automatic re-enable.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 26 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`

### I1 / R1 — `ARCH-01-T01`

- Source: [source](01-architecture/01-target-system-architecture.md#L160)
- Dependencies: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`
- Mode: `serial`
- Locks: `architecture-contracts`, `workflow-runtime`, `gmail-side-effects`, `milestone-gate`
- Branch: `agent/arch-01-t01`
- Worktree: `../alon-ai-task-arch-01-t01`
- Acceptance evidence: [source](01-architecture/01-target-system-architecture.md#L160) — Test evidence: restart, cancellation, ambiguity, duplicate-send, workflow-version, observability, operator-control, and rate-limit-under-restart/concurrency results.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 27 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`

### I1 / R1 — `WF-00-T02`

- Source: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L69)
- Dependencies: `WF-00-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`
- Mode: `serial`
- Locks: `workflow-runtime`, `gmail-side-effects`, `milestone-gate`
- Branch: `agent/wf-00-t02`
- Worktree: `../alon-ai-task-wf-00-t02`
- Acceptance evidence: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L69) — Test evidence: named WF-01 suite.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 28 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T03`

### I1 / R1 — `WF-01-T04`

- Source: [source](03-workflows/01-dbos-production-acceptance-spike.md#L202)
- Dependencies: `WF-01-T03`
- Mode: `serial`
- Locks: `workflow-runtime`, `gmail-side-effects`, `telemetry-catalog`, `milestone-gate`, `live-environment`
- Branch: `agent/wf-01-t04`
- Worktree: `../alon-ai-task-wf-01-t04`
- Acceptance evidence: [source](03-workflows/01-dbos-production-acceptance-spike.md#L202) — Test evidence: automated manifest validator.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 29 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T03`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`

### I1 / R1 — `TEST-03-T01`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L82)
- Dependencies: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-01-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/test-03-t01`
- Worktree: `../alon-ai-task-test-03-t01`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L82) — Test evidence: harness self-test proves handled exceptions cannot masquerade as process death.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-03-T02`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 30 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T04`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-03-T01`

### I1 / R1 — `TEST-03-T02`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L84)
- Dependencies: `TEST-03-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-01-T04`
- Mode: `serial`
- Locks: `workflow-runtime`, `gmail-side-effects`, `milestone-gate`, `live-environment`
- Branch: `agent/test-03-t02`
- Worktree: `../alon-ai-task-test-03-t02`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L84) — Test evidence: all required cases/repetitions have hashes and recorded outcomes; incomplete/corrupt execution is distinguished from a conclusive rejected runtime.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-01-T05`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 31 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T04`, `TEST-03-T02`

### I1 / R1 — `WF-01-T05`

- Source: [source](03-workflows/01-dbos-production-acceptance-spike.md#L204)
- Dependencies: `WF-01-T04`, `TEST-03-T02`
- Mode: `serial`
- Locks: `database-schema`, `workflow-runtime`, `gmail-side-effects`, `backup-restore`, `milestone-gate`
- Branch: `agent/wf-01-t05`
- Worktree: `../alon-ai-task-wf-01-t05`
- Acceptance evidence: [source](03-workflows/01-dbos-production-acceptance-spike.md#L204) — Test evidence: independent byte/hash/signature/golden/partial-write/restore validators plus schema-absent check.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-03-T03`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 32 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-03-T02`, `WF-01-T05`

### I1 / R1 — `TEST-03-T03`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L86)
- Dependencies: `TEST-03-T02`, `WF-01-T05`
- Mode: `serial`
- Locks: `milestone-gate`, `workflow-runtime`
- Branch: `agent/test-03-t03`
- Worktree: `../alon-ai-task-test-03-t03`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L86) — Test evidence: accepted branch requires the original exact 8/8/K0-K8 matrix, zero duplicates/blind retries and byte-identical authenticated exports; rejected branch requires complete authentic failed-criterion evidence and correct DBOS_REJECTED classification with all controls off, including a negative fixture containing a real recorded duplicate or blind retry that completes rejection adjudication but cannot yield DBOS acceptance; malformed/incomplete/tampered evidence remains blocking.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-00-T03`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 33 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T02`, `WF-01-T05`, `TEST-03-T03`

### I1 / R1 — `WF-00-T03`

- Source: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L71)
- Dependencies: `WF-00-T02`, `TEST-03-T03`, `WF-01-T05`
- Mode: `serial`
- Locks: `workflow-runtime`, `milestone-gate`
- Branch: `agent/wf-00-t03`
- Worktree: `../alon-ai-task-wf-00-t03`
- Acceptance evidence: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L71) — Test evidence: independent manifest checker proves 8/8 yields only `DBOS_ACCEPTED` and every failed/missing criterion yields only `DBOS_REJECTED`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-00-T04`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 34 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T03`

### I1 / R1 — `WF-00-T04`

- Source: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L73)
- Dependencies: `WF-00-T03`
- Mode: `serial`
- Locks: `workflow-runtime`, `dependency-lockfiles`, `compose-topology`, `milestone-gate`, `gmail-side-effects`, `live-environment`
- Branch: `agent/wf-00-t04`
- Worktree: `../alon-ai-task-wf-00-t04`
- Acceptance evidence: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L73) — Test evidence: accepted-branch no-Temporal spy plus rejected-branch Temporal adapter contract/eight-item suite and invalid/missing/disagreeing gate cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-00-T05`, `WF-01-T06`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 35 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T04`

### I1 / R1 — `WF-00-T05`

- Source: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L75)
- Dependencies: `WF-00-T04`
- Mode: `serial`
- Locks: `architecture-contracts`, `milestone-gate`
- Branch: `agent/wf-00-t05`
- Worktree: `../alon-ai-task-wf-00-t05`
- Acceptance evidence: [source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L75) — Test evidence: proof the already selected layers cannot satisfy the newly named requirement and that no runtime pointer changes.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 36 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T05`, `WF-00-T04`

### I1 / R1 — `WF-01-T06`

- Source: [source](03-workflows/01-dbos-production-acceptance-spike.md#L206)
- Dependencies: `WF-01-T05`, `WF-00-T04`
- Mode: `serial`
- Locks: `architecture-contracts`, `workflow-runtime`, `dependency-lockfiles`, `compose-topology`, `milestone-gate`
- Branch: `agent/wf-01-t06`
- Worktree: `../alon-ai-task-wf-01-t06`
- Acceptance evidence: [source](03-workflows/01-dbos-production-acceptance-spike.md#L206) — Test evidence: DBOS no-fallback spy, Temporal identical-suite/adapter checks, branch/evidence mismatch, and missing decision cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 37 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T02`

### I1 / R1 — `INFRA-01-T01`

- Source: [source](11-infrastructure/01-local-development.md#L73)
- Dependencies: `TEST-01-T02`
- Mode: `serial`
- Locks: `dependency-lockfiles`
- Branch: `agent/infra-01-t01`
- Worktree: `../alon-ai-task-infra-01-t01`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L73) — Test evidence: wrong version/root/tracked-env/provider-secret negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-01-T02`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 38 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-01-T01`

### I1 / R1 — `INFRA-01-T02`

- Source: [source](11-infrastructure/01-local-development.md#L75)
- Dependencies: `INFRA-01-T01`
- Mode: `serial`
- Locks: `compose-topology`
- Branch: `agent/infra-01-t02`
- Worktree: `../alon-ai-task-infra-01-t02`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L75) — Test evidence: parallel project, port collision, cross-database and forbidden-network tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-01-T03`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 39 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-01-T02`

### I1 / R1 — `INFRA-01-T03`

- Source: [source](11-infrastructure/01-local-development.md#L77)
- Dependencies: `INFRA-01-T02`
- Mode: `serial`
- Locks: `compose-topology`
- Branch: `agent/infra-01-t03`
- Worktree: `../alon-ai-task-infra-01-t03`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L77) — Test evidence: empty/wildcard/wrong-system-ID/production-like target refusal.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-01-T04`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 40 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-01-T03`

### I1 / R1 — `INFRA-01-T04`

- Source: [source](11-infrastructure/01-local-development.md#L79)
- Dependencies: `INFRA-01-T03`
- Mode: `serial`
- Locks: `compose-topology`
- Branch: `agent/infra-01-t04`
- Worktree: `../alon-ai-task-infra-01-t04`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L79) — Test evidence: unavailable Docker/provider reported as unavailable, not passed.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-01-T05`, `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 41 — M1

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T01`, `TEST-01-T02`, `INFRA-01-T04`

### I1 / R1 — `INFRA-01-T05`

- Source: [source](11-infrastructure/01-local-development.md#L81)
- Dependencies: `INFRA-01-T04`, `TEST-01-T01`, `TEST-01-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/infra-01-t05`
- Worktree: `../alon-ai-task-infra-01-t05`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L81) — Test evidence: unavailable Docker=`30` and pre-delete wrong identity=`50`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T01`, `DB-02-T01`, `DB-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 42 — M2

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`

### I1 / R1 — `ARCH-03-T01`

- Source: [source](01-architecture/03-domain-events-and-state-machines.md#L388)
- Dependencies: `PRODUCT-01-T03`
- Mode: `parallel`
- Locks: `architecture-contracts`, `backend-domain`
- Branch: `agent/arch-03-t01`
- Worktree: `../alon-ai-task-arch-03-t01`
- Acceptance evidence: [source](01-architecture/03-domain-events-and-state-machines.md#L388) — Test evidence: table-driven legal/illegal transition matrix.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `DB-04-T01`

- Source: [source](02-database/04-agent-artifacts-and-evidence.md#L102)
- Dependencies: `PRODUCT-01-T03`
- Mode: `parallel`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/db-04-t01`
- Worktree: `../alon-ai-task-db-04-t01`
- Acceptance evidence: [source](02-database/04-agent-artifacts-and-evidence.md#L102) — Test evidence: test_artifact_ref_constructs_before_acceptance, test_accepted_ref_requires_matching_passed_receipt and test_every_artifact_type_has_schema_validator_and_owner.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `ARCH-03-T02`, `DB-01-T01`, `DB-03-T02`, `DB-04-T02`, `DB-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 43 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`

### I1 / R1 — `ARCH-03-T02`

- Source: [source](01-architecture/03-domain-events-and-state-machines.md#L390)
- Dependencies: `ARCH-03-T01`
- Mode: `parallel`
- Locks: `architecture-contracts`, `database-schema`, `backend-domain`
- Branch: `agent/arch-03-t02`
- Worktree: `../alon-ai-task-arch-03-t02`
- Acceptance evidence: [source](01-architecture/03-domain-events-and-state-machines.md#L390) — Test evidence: rollback injection and concurrency tests on real PostgreSQL.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T03`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 44 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T04`, `ARCH-03-T02`

### I1 / R1 — `ARCH-03-T03`

- Source: [source](01-architecture/03-domain-events-and-state-machines.md#L392)
- Dependencies: `ARCH-03-T02`, `WF-00-T04`
- Mode: `parallel`
- Locks: `architecture-contracts`, `workflow-runtime`, `backend-domain`
- Branch: `agent/arch-03-t03`
- Worktree: `../alon-ai-task-arch-03-t03`
- Acceptance evidence: [source](01-architecture/03-domain-events-and-state-machines.md#L392) — Test evidence: restart/pause/cancel/failure contract suite.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 45 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`

### I1 / R1 — `DB-01-T01`

- Source: [source](02-database/01-core-data-model.md#L277)
- Dependencies: `ARCH-03-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/db-01-t01`
- Worktree: `../alon-ai-task-db-01-t01`
- Acceptance evidence: [source](02-database/01-core-data-model.md#L277) — Test evidence: `test_core_value_types_reject_invalid_values` and exhaustive enum snapshot.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-01-T02`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 46 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`

### I1 / R1 — `DB-01-T02`

- Source: [source](02-database/01-core-data-model.md#L279)
- Dependencies: `DB-01-T01`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`
- Branch: `agent/db-01-t02`
- Worktree: `../alon-ai-task-db-01-t02`
- Acceptance evidence: [source](02-database/01-core-data-model.md#L279) — Test evidence: `test_m2_core_upgrade_and_downgrade_on_real_postgres`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-02-T01`, `DB-01-T03`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 47 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `DB-01-T02`

### I1 / R1 — `ARCH-02-T01`

- Source: [source](01-architecture/02-module-boundaries.md#L114)
- Dependencies: `ARCH-03-T01`, `DB-01-T02`
- Mode: `parallel`
- Locks: `architecture-contracts`, `backend-domain`
- Branch: `agent/arch-02-t01`
- Worktree: `../alon-ai-task-arch-02-t01`
- Acceptance evidence: [source](01-architecture/02-module-boundaries.md#L114) — Test evidence: type checks and forbidden-import scan.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-01-T02`, `ARCH-02-T02`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 48 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-01-T01`, `ARCH-03-T01`, `ARCH-02-T01`

### I1 / R1 — `ARCH-01-T02`

- Source: [source](01-architecture/01-target-system-architecture.md#L162)
- Dependencies: `ARCH-01-T01`, `ARCH-02-T01`, `ARCH-03-T01`
- Mode: `serial`
- Locks: `architecture-contracts`, `database-schema`, `migration-head`, `milestone-gate`
- Branch: `agent/arch-01-t02`
- Worktree: `../alon-ai-task-arch-01-t02`
- Acceptance evidence: [source](01-architecture/01-target-system-architecture.md#L162) — Test evidence: migration, constraints, transitions, concurrency, audit, and fresh-restore tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 49 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `ARCH-02-T01`

### I1 / R1 — `ARCH-02-T02`

- Source: [source](01-architecture/02-module-boundaries.md#L116)
- Dependencies: `ARCH-02-T01`, `ARCH-03-T01`
- Mode: `parallel`
- Locks: `architecture-contracts`, `database-schema`, `backend-domain`
- Branch: `agent/arch-02-t02`
- Worktree: `../alon-ai-task-arch-02-t02`
- Acceptance evidence: [source](01-architecture/02-module-boundaries.md#L116) — Test evidence: real-PostgreSQL rollback/concurrency/replay tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 50 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T02`

### I1 / R1 — `DB-01-T03`

- Source: [source](02-database/01-core-data-model.md#L281)
- Dependencies: `DB-01-T02`
- Mode: `parallel`
- Locks: `database-schema`, `backend-domain`
- Branch: `agent/db-01-t03`
- Worktree: `../alon-ai-task-db-01-t03`
- Acceptance evidence: [source](02-database/01-core-data-model.md#L281) — Test evidence: `test_concurrent_experiment_commands_have_one_winner`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-01-T04`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 51 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T04`, `DB-01-T03`

### I1 / R1 — `DB-01-T04`

- Source: [source](02-database/01-core-data-model.md#L283)
- Dependencies: `DB-01-T03`, `WF-00-T04`
- Mode: `parallel`
- Locks: `database-schema`, `workflow-runtime`, `backend-domain`
- Branch: `agent/db-01-t04`
- Worktree: `../alon-ai-task-db-01-t04`
- Acceptance evidence: [source](02-database/01-core-data-model.md#L283) — Test evidence: `test_unknown_runtime_state_fails_closed`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-01-T05`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 52 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T04`

### I1 / R1 — `DB-01-T05`

- Source: [source](02-database/01-core-data-model.md#L285)
- Dependencies: `DB-01-T04`
- Mode: `serial`
- Locks: `database-schema`, `security-runtime`
- Branch: `agent/db-01-t05`
- Worktree: `../alon-ai-task-db-01-t05`
- Acceptance evidence: [source](02-database/01-core-data-model.md#L285) — Test evidence: migration/default/version/hash/independence tests prove neither row enables the other and no M6 evidence is consumed.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 53 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`, `PRODUCT-02-T01`

### I1 / R1 — `DB-02-T01`

- Source: [source](02-database/02-experiment-and-offer-schema.md#L54)
- Dependencies: `PRODUCT-01-T03`, `PRODUCT-02-T01`
- Mode: `parallel`
- Locks: `product-contracts`, `backend-domain`
- Branch: `agent/db-02-t01`
- Worktree: `../alon-ai-task-db-02-t01`
- Acceptance evidence: [source](02-database/02-experiment-and-offer-schema.md#L54) — Test evidence: `test_brief_requires_every_m0_field`, `test_stage_tuple_is_exact`, prior-`CONTINUE`, and immutability tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-02-T02`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 54 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T01`

### I1 / R1 — `DB-02-T02`

- Source: [source](02-database/02-experiment-and-offer-schema.md#L56)
- Dependencies: `DB-02-T01`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`
- Branch: `agent/db-02-t02`
- Worktree: `../alon-ai-task-db-02-t02`
- Acceptance evidence: [source](02-database/02-experiment-and-offer-schema.md#L56) — Test evidence: real-PostgreSQL constraint matrix plus produced-candidate -> validation-without-receipt -> acceptance -> materialization, and candidate validation must not satisfy an action-authority FK.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-02-T03`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 55 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T02`

### I1 / R1 — `DB-02-T03`

- Source: [source](02-database/02-experiment-and-offer-schema.md#L58)
- Dependencies: `DB-02-T02`
- Mode: `parallel`
- Locks: `database-schema`, `backend-domain`
- Branch: `agent/db-02-t03`
- Worktree: `../alon-ai-task-db-02-t03`
- Acceptance evidence: [source](02-database/02-experiment-and-offer-schema.md#L58) — Test evidence: `test_concurrent_offer_version_append_has_one_winner`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-02-T04`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 56 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T03`

### I1 / R1 — `DB-02-T04`

- Source: [source](02-database/02-experiment-and-offer-schema.md#L60)
- Dependencies: `DB-02-T03`
- Mode: `parallel`
- Locks: `database-schema`, `backend-domain`, `telemetry-catalog`
- Branch: `agent/db-02-t04`
- Worktree: `../alon-ai-task-db-02-t04`
- Acceptance evidence: [source](02-database/02-experiment-and-offer-schema.md#L60) — Test evidence: `test_metric_snapshot_recomputes_byte_equivalent`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-02-T05`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 57 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T04`

### I1 / R1 — `DB-02-T05`

- Source: [source](02-database/02-experiment-and-offer-schema.md#L62)
- Dependencies: `DB-02-T04`
- Mode: `serial`
- Locks: `database-schema`, `backend-domain`, `milestone-gate`
- Branch: `agent/db-02-t05`
- Worktree: `../alon-ai-task-db-02-t05`
- Acceptance evidence: [source](02-database/02-experiment-and-offer-schema.md#L62) — Test evidence: command replay and two-writer race.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 58 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `ARCH-03-T01`

### I1 / R1 — `DB-03-T02`

- Source: [source](02-database/03-leads-campaigns-and-messages.md#L256)
- Dependencies: `DB-03-T01`, `ARCH-03-T01`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`
- Branch: `agent/db-03-t02`
- Worktree: `../alon-ai-task-db-03-t02`
- Acceptance evidence: [source](02-database/03-leads-campaigns-and-messages.md#L256) — Test evidence: `test_concurrent_same_business_discovery_creates_one_lead`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 59 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-04-T01`

### I1 / R1 — `DB-04-T02`

- Source: [source](02-database/04-agent-artifacts-and-evidence.md#L104)
- Dependencies: `DB-04-T01`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`, `agent-artifacts`
- Branch: `agent/db-04-t02`
- Worktree: `../alon-ai-task-db-04-t02`
- Acceptance evidence: [source](02-database/04-agent-artifacts-and-evidence.md#L104) — Test evidence: real-PostgreSQL migration/constraint tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-01-T01`, `PROVIDER-07-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 60 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`

### I1 / R1 — `DB-05-T01`

- Source: [source](02-database/05-audit-events-and-idempotency.md#L327)
- Dependencies: `ARCH-03-T01`
- Mode: `parallel`
- Locks: `architecture-contracts`, `backend-domain`
- Branch: `agent/db-05-t01`
- Worktree: `../alon-ai-task-db-05-t01`
- Acceptance evidence: [source](02-database/05-audit-events-and-idempotency.md#L327) — Test evidence: `test_arch03_event_catalog_is_exact_and_complete`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-05-T02`, `AGENT-01-T01`, `PROVIDER-07-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 61 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-05-T01`

### I1 / R1 — `DB-05-T02`

- Source: [source](02-database/05-audit-events-and-idempotency.md#L329)
- Dependencies: `DB-05-T01`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`
- Branch: `agent/db-05-t02`
- Worktree: `../alon-ai-task-db-05-t02`
- Acceptance evidence: [source](02-database/05-audit-events-and-idempotency.md#L329) — Test evidence: migration introspection and mutation-denial tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-03-T03`, `DB-05-T03`, `AGENT-01-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `BACKEND-05-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 62 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `DB-03-T02`, `DB-05-T02`

### I1 / R1 — `DB-03-T03`

- Source: [source](02-database/03-leads-campaigns-and-messages.md#L258)
- Dependencies: `DB-03-T02`, `ARCH-03-T01`, `DB-05-T02`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`, `compliance-policy`
- Branch: `agent/db-03-t03`
- Worktree: `../alon-ai-task-db-03-t03`
- Acceptance evidence: [source](02-database/03-leads-campaigns-and-messages.md#L258) — Test evidence: `test_suppression_overrides_qualification_and_action authorization`, `test_concurrent_stage_final_slot_never_over_admits`, `test_recipient_cannot_reappear_in_another_stage`, and target-ref constraint introspection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-03-T04`, `AGENT-01-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `BACKEND-05-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 63 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `DB-03-T03`

### I1 / R1 — `DB-03-T04`

- Source: [source](02-database/03-leads-campaigns-and-messages.md#L260)
- Dependencies: `DB-03-T03`, `ARCH-03-T01`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`
- Branch: `agent/db-03-t04`
- Worktree: `../alon-ai-task-db-03-t04`
- Acceptance evidence: [source](02-database/03-leads-campaigns-and-messages.md#L260) — Test evidence: exhaustive PostgreSQL constraint and transition tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-06-T01`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `BACKEND-05-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 64 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-05-T02`

### I1 / R1 — `DB-05-T03`

- Source: [source](02-database/05-audit-events-and-idempotency.md#L331)
- Dependencies: `DB-05-T02`
- Mode: `parallel`
- Locks: `database-schema`, `backend-domain`
- Branch: `agent/db-05-t03`
- Worktree: `../alon-ai-task-db-05-t03`
- Acceptance evidence: [source](02-database/05-audit-events-and-idempotency.md#L331) — Test evidence: concurrent duplicate and hash-conflict tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-05-T04`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `BACKEND-05-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 65 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-05-T03`

### I1 / R1 — `DB-05-T04`

- Source: [source](02-database/05-audit-events-and-idempotency.md#L333)
- Dependencies: `DB-05-T03`
- Mode: `parallel`
- Locks: `database-schema`, `workflow-runtime`, `backend-domain`
- Branch: `agent/db-05-t04`
- Worktree: `../alon-ai-task-db-05-t04`
- Acceptance evidence: [source](02-database/05-audit-events-and-idempotency.md#L333) — Test evidence: crash before business write, between business write and receipt, before commit, and after commit.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `BACKEND-05-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 66 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T02`, `DB-02-T02`, `DB-04-T02`, `DB-05-T02`, `DB-03-T04`

### I1 / R1 — `DB-06-T01`

- Source: [source](02-database/06-migrations-seeding-and-retention.md#L189)
- Dependencies: `DB-01-T02`, `DB-02-T02`, `DB-03-T04`, `DB-04-T02`, `DB-05-T02`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`
- Branch: `agent/db-06-t01`
- Worktree: `../alon-ai-task-db-06-t01`
- Acceptance evidence: [source](02-database/06-migrations-seeding-and-retention.md#L189) — Test evidence: upgrade from base and downgrade where declared safe; compile every pg_catalog column and nested typed-schema leaf through data.inventory.rules.v1, assert exact table/field set equality and all privacy axes, reject unknown table/source hash drift/unexpanded JSON and any broadened reader/model grant.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-06-T02`, `SEC-06-T01`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `BACKEND-05-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 67 — M2

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T03`, `DB-06-T01`

### I1 / R1 — `DB-06-T02`

- Source: [source](02-database/06-migrations-seeding-and-retention.md#L191)
- Dependencies: `DB-06-T01`
- Mode: `parallel`
- Locks: `database-schema`
- Branch: `agent/db-06-t02`
- Worktree: `../alon-ai-task-db-06-t02`
- Acceptance evidence: [source](02-database/06-migrations-seeding-and-retention.md#L191) — Test evidence: two-run no-diff and secret/PII scan.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `SEC-06-T01`

- Source: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L127)
- Dependencies: `PRODUCT-01-T03`, `DB-06-T01`
- Mode: `parallel`
- Locks: `compliance-policy`
- Branch: `agent/sec-06-t01`
- Worktree: `../alon-ai-task-sec-06-t01`
- Acceptance evidence: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L127) — Test evidence: M2/M3 schema/event/provider/log field-set equality, ordered-rule determinism, exact owner/reader equality, source-schema drift, unknown/nested-field rejection, positive schema-bound booking_count/scope/payment leaves, wrong-type/hash/prohibited-descendant/container negatives, internal suppression lookup versus hash-free HTTP/report serialization, raw secret/contact/budget/thread/global-model denials, minimum-cell 4/5 boundary, full-span coverage and shorter-payload-clock/35-day-backup/hold/restore fixtures.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `DB-06-T03`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `OBS-01-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 68 — M2

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-06-T02`

### I1 / R1 — `DB-06-T03`

- Source: [source](02-database/06-migrations-seeding-and-retention.md#L193)
- Dependencies: `DB-06-T02`
- Mode: `serial`
- Locks: `database-schema`, `backup-restore`, `milestone-gate`
- Branch: `agent/db-06-t03`
- Worktree: `../alon-ai-task-db-06-t03`
- Acceptance evidence: [source](02-database/06-migrations-seeding-and-retention.md#L193) — Test evidence: automated `test_m2_backup_restores_to_fresh_postgres`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-06-T04`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-07-T01`, `BACKEND-03-T01`, `OBS-01-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 69 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-06-T03`

### I1 / R1 — `DB-06-T04`

- Source: [source](02-database/06-migrations-seeding-and-retention.md#L195)
- Dependencies: `DB-06-T03`
- Mode: `serial`
- Locks: `database-schema`, `migration-head`, `ci-release`, `milestone-gate`
- Branch: `agent/db-06-t04`
- Worktree: `../alon-ai-task-db-06-t04`
- Acceptance evidence: [source](02-database/06-migrations-seeding-and-retention.md#L195) — Test evidence: missing, stale, mixed-version, schema-diff, and rollback-negative fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 70 — M3

- Agent count: 4 implementer(s) and 4 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `ARCH-03-T01`, `DB-01-T02`, `ARCH-02-T01`, `DB-04-T02`, `DB-05-T02`, `SEC-06-T01`

### I1 / R1 — `AGENT-01-T01`

- Source: [source](04-agents/01-agent-runtime-and-contracts.md#L697)
- Dependencies: `DB-01-T02`, `DB-04-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-01-t01`
- Worktree: `../alon-ai-task-agent-01-t01`
- Acceptance evidence: [source](04-agents/01-agent-runtime-and-contracts.md#L697) — Test evidence: `test_agent_contracts_reject_extra_coercion_unknown_versions_and_bad_digest`.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-07-T01`

- Source: [source](05-providers/07-calendar-provider.md#L56)
- Dependencies: `ARCH-02-T01`, `ARCH-03-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-07-t01`
- Worktree: `../alon-ai-task-provider-07-t01`
- Acceptance evidence: [source](05-providers/07-calendar-provider.md#L56) — Test evidence: schema/bounds and forbidden write-capability graph.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `BACKEND-03-T01`

- Source: [source](06-backend/03-policy-engine.md#L121)
- Dependencies: `DB-05-T02`, `ARCH-03-T01`, `DB-03-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-03-t01`
- Worktree: `../alon-ai-task-backend-03-t01`
- Acceptance evidence: [source](06-backend/03-policy-engine.md#L121) — Test evidence: scope/generation/recipient/thread/offer/activation splice and mutable-fact hash matrix.
- Optional acceptance commands: none
- Merge order: 3

### I4 / R4 — `OBS-01-T01`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L110)
- Dependencies: `SEC-06-T01`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-01-t01`
- Worktree: `../alon-ai-task-obs-01-t01`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L110) — Test evidence: property/fuzz/leak/schema tests.
- Optional acceptance commands: none
- Merge order: 4

- Newly unlocked tasks: `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `PROVIDER-07-T02`, `PROVIDER-08-T01`, `BACKEND-01-T01`, `BACKEND-03-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 71 — M3

- Agent count: 3 implementer(s) and 3 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`, `DB-02-T03`, `DB-04-T01`, `DB-03-T03`, `DB-03-T04`, `AGENT-01-T01`, `BACKEND-03-T01`

### I1 / R1 — `AGENT-10-T01`

- Source: [source](04-agents/12-agent-evals-and-versioning.md#L365)
- Dependencies: `DB-02-T03`, `DB-03-T03`, `DB-03-T04`, `DB-04-T01`
- Mode: `parallel`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-10-t01`
- Worktree: `../alon-ai-task-agent-10-t01`
- Acceptance evidence: [source](04-agents/12-agent-evals-and-versioning.md#L365) — Test evidence: count, tag, provenance, hash, sensitivity, zero-network, and zero-product-authority coverage.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-03-T01`

- Source: [source](05-providers/03-model-provider.md#L106)
- Dependencies: `AGENT-01-T01`, `DB-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-03-t01`
- Worktree: `../alon-ai-task-provider-03-t01`
- Acceptance evidence: [source](05-providers/03-model-provider.md#L106) — Test evidence: `test_model_capability_wire_is_byte_exact_with_agent01`.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `BACKEND-03-T02`

- Source: [source](06-backend/03-policy-engine.md#L123)
- Dependencies: `BACKEND-03-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-03-t02`
- Worktree: `../alon-ai-task-backend-03-t02`
- Acceptance evidence: [source](06-backend/03-policy-engine.md#L123) — Test evidence: candidate-without-receipt validation then acceptance, no candidate-result action authority, FIRST_CONTACT/no-reply UNKNOWN positive, reply-driven missing-evidence negative, exact monetary/one-unit/source-splice/scope/legal vectors.
- Optional acceptance commands: none
- Merge order: 3

- Newly unlocked tasks: `AGENT-01-T02`, `AGENT-02-T01`, `PROVIDER-03-T02`, `BACKEND-03-T03`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 72 — M3

- Agent count: 3 implementer(s) and 3 reviewer(s)
- Base prerequisite barrier: `DB-04-T02`, `DB-05-T03`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-03-T01`

### I1 / R1 — `AGENT-01-T02`

- Source: [source](04-agents/01-agent-runtime-and-contracts.md#L699)
- Dependencies: `AGENT-01-T01`, `AGENT-10-T01`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-01-t02`
- Worktree: `../alon-ai-task-agent-01-t02`
- Acceptance evidence: [source](04-agents/01-agent-runtime-and-contracts.md#L699) — Test evidence: `test_agent_dependency_graph_has_no_repository_command_send_or_credential_edge`; fake-HTTP execution of a fresh unpromoted signed candidate-configuration fixture succeeds under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-03-T02`

- Source: [source](05-providers/03-model-provider.md#L108)
- Dependencies: `PROVIDER-03-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-03-t02`
- Worktree: `../alon-ai-task-provider-03-t02`
- Acceptance evidence: [source](05-providers/03-model-provider.md#L108) — Test evidence: fake HTTP status/status-output/refusal/schema/usage matrix; fake-HTTP execution of a fresh unpromoted signed candidate-configuration fixture succeeds under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `BACKEND-01-T01`

- Source: [source](06-backend/01-domain-services.md#L86)
- Dependencies: `AGENT-01-T01`, `DB-04-T02`, `DB-05-T03`
- Mode: `parallel`
- Locks: `backend-domain`, `agent-artifacts`
- Branch: `agent/backend-01-t01`
- Worktree: `../alon-ai-task-backend-01-t01`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L86) — Test evidence: sole-writer/import checks, strict fixture integration, start/close/result crash/replay and event atomicity tests; no acceptance or product-state writes.
- Optional acceptance commands: none
- Merge order: 3

- Newly unlocked tasks: `PROVIDER-03-T03`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 73 — M3

- Agent count: 3 implementer(s) and 3 reviewer(s)
- Base prerequisite barrier: `DB-02-T01`, `DB-04-T01`, `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-03-T02`, `BACKEND-03-T02`

### I1 / R1 — `AGENT-02-T01`

- Source: [source](04-agents/02-idea-discovery-agent.md#L57)
- Dependencies: `DB-02-T01`, `DB-04-T01`, `AGENT-10-T01`, `AGENT-01-T01`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-02-t01`
- Worktree: `../alon-ai-task-agent-02-t01`
- Acceptance evidence: [source](04-agents/02-idea-discovery-agent.md#L57) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-03-T03`

- Source: [source](05-providers/03-model-provider.md#L110)
- Dependencies: `PROVIDER-03-T02`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-03-t03`
- Worktree: `../alon-ai-task-provider-03-t03`
- Acceptance evidence: [source](05-providers/03-model-provider.md#L110) — Test evidence: `test_model_deadline_cancel_rate_token_and_cost_boundaries_have_exact_call_count`.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `BACKEND-03-T03`

- Source: [source](06-backend/03-policy-engine.md#L125)
- Dependencies: `BACKEND-03-T02`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-03-t03`
- Worktree: `../alon-ai-task-backend-03-t03`
- Acceptance evidence: [source](06-backend/03-policy-engine.md#L125) — Test evidence: concurrency/replay/failure injection.
- Optional acceptance commands: none
- Merge order: 3

- Newly unlocked tasks: `AGENT-02-T02`, `AGENT-04-T01`, `PROVIDER-03-T04`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 74 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T02`, `AGENT-02-T01`, `PROVIDER-03-T03`

### I1 / R1 — `AGENT-02-T02`

- Source: [source](04-agents/02-idea-discovery-agent.md#L59)
- Dependencies: `AGENT-02-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-02-t02`
- Worktree: `../alon-ai-task-agent-02-t02`
- Acceptance evidence: [source](04-agents/02-idea-discovery-agent.md#L59) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-03-T04`

- Source: [source](05-providers/03-model-provider.md#L112)
- Dependencies: `PROVIDER-03-T03`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-03-t04`
- Worktree: `../alon-ai-task-provider-03-t04`
- Acceptance evidence: [source](05-providers/03-model-provider.md#L112) — Test evidence: tamper/cross-capability/extra-field/zero-network tests.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 75 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`, `DB-04-T01`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-02-T01`

### I1 / R1 — `AGENT-04-T01`

- Source: [source](04-agents/03-market-research-agent.md#L57)
- Dependencies: `AGENT-02-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-04-T01`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-04-t01`
- Worktree: `../alon-ai-task-agent-04-t01`
- Acceptance evidence: [source](04-agents/03-market-research-agent.md#L57) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-04-T01`

- Source: [source](05-providers/04-search-provider.md#L102)
- Dependencies: `AGENT-01-T01`, `DB-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-04-t01`
- Worktree: `../alon-ai-task-provider-04-t01`
- Acceptance evidence: [source](05-providers/04-search-provider.md#L102) — Test evidence: `test_search_capability_wire_and_fixture_are_agent01_exact`.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-04-T02`, `AGENT-03-T01`, `PROVIDER-04-T02`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 76 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T02`, `AGENT-04-T01`, `PROVIDER-04-T01`

### I1 / R1 — `AGENT-04-T02`

- Source: [source](04-agents/03-market-research-agent.md#L59)
- Dependencies: `AGENT-04-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-04-t02`
- Worktree: `../alon-ai-task-agent-04-t02`
- Acceptance evidence: [source](04-agents/03-market-research-agent.md#L59) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-04-T02`

- Source: [source](05-providers/04-search-provider.md#L104)
- Dependencies: `PROVIDER-04-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-04-t02`
- Worktree: `../alon-ai-task-provider-04-t02`
- Acceptance evidence: [source](05-providers/04-search-provider.md#L104) — Test evidence: HTTP/domain/Unicode/status matrix.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 77 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`, `DB-02-T03`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-02-T01`, `AGENT-04-T01`

### I1 / R1 — `AGENT-03-T01`

- Source: [source](04-agents/04-offer-design-agent.md#L59)
- Dependencies: `AGENT-02-T01`, `AGENT-04-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-02-T03`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-03-t01`
- Worktree: `../alon-ai-task-agent-03-t01`
- Acceptance evidence: [source](04-agents/04-offer-design-agent.md#L59) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-05-T01`

- Source: [source](05-providers/05-page-fetching-and-extraction.md#L107)
- Dependencies: `AGENT-01-T01`, `DB-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-05-t01`
- Worktree: `../alon-ai-task-provider-05-t01`
- Acceptance evidence: [source](05-providers/05-page-fetching-and-extraction.md#L107) — Test evidence: `test_evidence_and_page_wire_parity_with_agent01`.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-03-T02`, `AGENT-11-T01`, `AGENT-09-T01`, `DB-04-T03`, `PROVIDER-05-T02`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 78 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-04-T02`, `AGENT-01-T02`, `AGENT-03-T01`, `PROVIDER-05-T01`

### I1 / R1 — `AGENT-03-T02`

- Source: [source](04-agents/04-offer-design-agent.md#L61)
- Dependencies: `AGENT-03-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-03-t02`
- Worktree: `../alon-ai-task-agent-03-t02`
- Acceptance evidence: [source](04-agents/04-offer-design-agent.md#L61) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `DB-04-T03`

- Source: [source](02-database/04-agent-artifacts-and-evidence.md#L106)
- Dependencies: `DB-04-T02`, `PROVIDER-05-T01`
- Mode: `parallel`
- Locks: `agent-artifacts`, `provider-contracts`, `compliance-policy`
- Branch: `agent/db-04-t03`
- Worktree: `../alon-ai-task-db-04-t03`
- Acceptance evidence: [source](02-database/04-agent-artifacts-and-evidence.md#L106) — Test evidence: malicious URI/content/type fixtures.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `DB-04-T04`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 79 — M3

- Agent count: 3 implementer(s) and 3 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `DB-03-T03`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-03-T01`, `PROVIDER-05-T01`, `DB-04-T03`, `BACKEND-01-T01`

### I1 / R1 — `AGENT-11-T01`

- Source: [source](04-agents/05-lead-discovery-agent.md#L56)
- Dependencies: `AGENT-03-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T03`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-11-t01`
- Worktree: `../alon-ai-task-agent-11-t01`
- Acceptance evidence: [source](04-agents/05-lead-discovery-agent.md#L56) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-05-T02`

- Source: [source](05-providers/05-page-fetching-and-extraction.md#L109)
- Dependencies: `PROVIDER-05-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-05-t02`
- Worktree: `../alon-ai-task-provider-05-t02`
- Acceptance evidence: [source](05-providers/05-page-fetching-and-extraction.md#L109) — Test evidence: missing/purged/restricted/corrupt/cancel matrix.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `DB-04-T04`

- Source: [source](02-database/04-agent-artifacts-and-evidence.md#L108)
- Dependencies: `DB-04-T03`, `BACKEND-01-T01`, `ARCH-03-T01`
- Mode: `parallel`
- Locks: `database-schema`, `agent-artifacts`, `backend-domain`
- Branch: `agent/db-04-t04`
- Worktree: `../alon-ai-task-db-04-t04`
- Acceptance evidence: [source](02-database/04-agent-artifacts-and-evidence.md#L108) — Test evidence: exhaustive artifact-state matrix and command replay.
- Optional acceptance commands: none
- Merge order: 3

- Newly unlocked tasks: `AGENT-11-T02`, `AGENT-05-T01`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 80 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`, `AGENT-01-T01`, `AGENT-01-T02`, `AGENT-11-T01`

### I1 / R1 — `AGENT-11-T02`

- Source: [source](04-agents/05-lead-discovery-agent.md#L58)
- Dependencies: `AGENT-11-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-11-t02`
- Worktree: `../alon-ai-task-agent-11-t02`
- Acceptance evidence: [source](04-agents/05-lead-discovery-agent.md#L58) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-06-T01`

- Source: [source](05-providers/06-enrichment-provider.md#L101)
- Dependencies: `AGENT-01-T01`, `DB-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-06-t01`
- Worktree: `../alon-ai-task-provider-06-t01`
- Acceptance evidence: [source](05-providers/06-enrichment-provider.md#L101) — Test evidence: `test_business_capabilities_are_wire_exact_with_agent01`.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `OBS-03-T01`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 81 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-03-T03`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-11-T01`, `PROVIDER-07-T01`

### I1 / R1 — `AGENT-05-T01`

- Source: [source](04-agents/06-lead-research-agent.md#L57)
- Dependencies: `AGENT-11-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T03`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-05-t01`
- Worktree: `../alon-ai-task-agent-05-t01`
- Acceptance evidence: [source](04-agents/06-lead-research-agent.md#L57) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-07-T02`

- Source: [source](05-providers/07-calendar-provider.md#L58)
- Dependencies: `PROVIDER-07-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-07-t02`
- Worktree: `../alon-ai-task-provider-07-t02`
- Acceptance evidence: [source](05-providers/07-calendar-provider.md#L58) — Test evidence: exact request/result/ledger hashes and no hidden writes.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-05-T02`, `AGENT-06-T01`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 82 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`, `AGENT-01-T01`, `AGENT-01-T02`, `AGENT-05-T01`

### I1 / R1 — `AGENT-05-T02`

- Source: [source](04-agents/06-lead-research-agent.md#L59)
- Dependencies: `AGENT-05-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-05-t02`
- Worktree: `../alon-ai-task-agent-05-t02`
- Acceptance evidence: [source](04-agents/06-lead-research-agent.md#L59) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-08-T01`

- Source: [source](05-providers/08-lead-discovery-provider.md#L51)
- Dependencies: `AGENT-01-T01`, `DB-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-08-t01`
- Worktree: `../alon-ai-task-provider-08-t01`
- Acceptance evidence: [source](05-providers/08-lead-discovery-provider.md#L51) — Test evidence: schema/hash/timeout/unknown-source/cursor-splice negatives.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `PROVIDER-08-T02`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 83 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-03-T03`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-03-T01`, `AGENT-05-T01`, `PROVIDER-08-T01`

### I1 / R1 — `AGENT-06-T01`

- Source: [source](04-agents/07-lead-qualification-agent.md#L56)
- Dependencies: `AGENT-03-T01`, `AGENT-05-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T03`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-06-t01`
- Worktree: `../alon-ai-task-agent-06-t01`
- Acceptance evidence: [source](04-agents/07-lead-qualification-agent.md#L56) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-08-T02`

- Source: [source](05-providers/08-lead-discovery-provider.md#L53)
- Dependencies: `PROVIDER-08-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-08-t02`
- Worktree: `../alon-ai-task-provider-08-t02`
- Acceptance evidence: [source](05-providers/08-lead-discovery-provider.md#L53) — Test evidence: duplicates, conflicting names/locations, missing identities, prompt injection and zero network.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-06-T02`, `AGENT-07-T01`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 84 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `AGENT-01-T02`, `AGENT-06-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`

### I1 / R1 — `AGENT-06-T02`

- Source: [source](04-agents/07-lead-qualification-agent.md#L58)
- Dependencies: `AGENT-06-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-06-t02`
- Worktree: `../alon-ai-task-agent-06-t02`
- Acceptance evidence: [source](04-agents/07-lead-qualification-agent.md#L58) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `OBS-03-T01`

- Source: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L106)
- Dependencies: `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `PROVIDER-01-T01`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/obs-03-t01`
- Worktree: `../alon-ai-task-obs-03-t01`
- Acceptance evidence: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L106) — Test evidence: tier/minimum/cancel/failure/version boundary golden vectors.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `OBS-03-T02`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 85 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-05-T02`, `DB-03-T04`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-03-T01`, `AGENT-05-T01`, `AGENT-06-T01`, `OBS-03-T01`

### I1 / R1 — `AGENT-07-T01`

- Source: [source](04-agents/08-email-writing-agent.md#L56)
- Dependencies: `AGENT-03-T01`, `AGENT-05-T01`, `AGENT-06-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T04`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-07-t01`
- Worktree: `../alon-ai-task-agent-07-t01`
- Acceptance evidence: [source](04-agents/08-email-writing-agent.md#L56) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `OBS-03-T02`

- Source: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L108)
- Dependencies: `OBS-03-T01`, `DB-05-T02`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/obs-03-t02`
- Worktree: `../alon-ai-task-obs-03-t02`
- Acceptance evidence: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L108) — Test evidence: concurrency/replay/crash/unknown/overage/zero/retry matrix plus calendar positive allocations, cross-branch splices and missing/wrong attribution negatives.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-07-T02`, `AGENT-08-T01`, `DB-05-T05`, `AGENT-01-T03`, `PROVIDER-04-T03`, `PROVIDER-05-T03`, `OBS-03-T03`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 86 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-05-T04`, `AGENT-01-T02`, `AGENT-07-T01`, `PROVIDER-03-T04`, `OBS-03-T02`

### I1 / R1 — `AGENT-07-T02`

- Source: [source](04-agents/08-email-writing-agent.md#L58)
- Dependencies: `AGENT-07-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-07-t02`
- Worktree: `../alon-ai-task-agent-07-t02`
- Acceptance evidence: [source](04-agents/08-email-writing-agent.md#L58) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `DB-05-T05`

- Source: [source](02-database/05-audit-events-and-idempotency.md#L335)
- Dependencies: `DB-05-T04`, `PROVIDER-03-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `database-schema`, `provider-contracts`, `backend-domain`, `telemetry-catalog`
- Branch: `agent/db-05-t05`
- Worktree: `../alon-ai-task-db-05-t05`
- Acceptance evidence: [source](02-database/05-audit-events-and-idempotency.md#L335) — Test evidence: overspend, duplicate invoice, currency, and missing-result tests.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `PRODUCT-02-T03`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 87 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PRODUCT-02-T02`, `DB-03-T04`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-03-T01`, `AGENT-07-T01`, `DB-05-T05`

### I1 / R1 — `AGENT-08-T01`

- Source: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L58)
- Dependencies: `AGENT-03-T01`, `AGENT-07-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T04`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-08-t01`
- Worktree: `../alon-ai-task-agent-08-t01`
- Acceptance evidence: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L58) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PRODUCT-02-T03`

- Source: [source](00-product-strategy/02-success-metrics.md#L146)
- Dependencies: `PRODUCT-02-T02`, `DB-05-T05`
- Mode: `parallel`
- Locks: `backend-domain`, `telemetry-catalog`
- Branch: `agent/product-02-t03`
- Worktree: `../alon-ai-task-product-02-t03`
- Acceptance evidence: [source](00-product-strategy/02-success-metrics.md#L146) — Test evidence: golden datasets including zero denominators, duplicates, late replies, bounces, FX conversion, negotiated margins, cancelled/rescheduled bookings, and cross-campaign strategy attribution.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-08-T02`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 88 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T02`, `AGENT-08-T01`, `PROVIDER-04-T02`, `DB-04-T03`, `OBS-03-T02`

### I1 / R1 — `AGENT-08-T02`

- Source: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L60)
- Dependencies: `AGENT-08-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-08-t02`
- Worktree: `../alon-ai-task-agent-08-t02`
- Acceptance evidence: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L60) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-04-T03`

- Source: [source](05-providers/04-search-provider.md#L106)
- Dependencies: `PROVIDER-04-T02`, `OBS-03-T02`, `DB-04-T03`
- Mode: `parallel`
- Locks: `provider-contracts`, `backend-domain`, `agent-artifacts`
- Branch: `agent/provider-04-t03`
- Worktree: `../alon-ai-task-provider-04-t03`
- Acceptance evidence: [source](05-providers/04-search-provider.md#L106) — Test evidence: failure injection and total/hash equality.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `PROVIDER-04-T04`, `PROVIDER-06-T02`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 89 — M3

- Agent count: 3 implementer(s) and 3 reviewer(s)
- Base prerequisite barrier: `DB-02-T04`, `DB-04-T01`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-03-T01`, `OBS-03-T02`, `PROVIDER-04-T03`

### I1 / R1 — `AGENT-09-T01`

- Source: [source](04-agents/10-experiment-evaluation-agent.md#L56)
- Dependencies: `AGENT-03-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-02-T04`, `DB-04-T01`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-09-t01`
- Worktree: `../alon-ai-task-agent-09-t01`
- Acceptance evidence: [source](04-agents/10-experiment-evaluation-agent.md#L56) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-04-T04`

- Source: [source](05-providers/04-search-provider.md#L108)
- Dependencies: `PROVIDER-04-T03`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-04-t04`
- Worktree: `../alon-ai-task-provider-04-t04`
- Acceptance evidence: [source](05-providers/04-search-provider.md#L108) — Test evidence: tamper, extra-field, cross-capability, zero-network tests.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `OBS-03-T03`

- Source: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L110)
- Dependencies: `OBS-03-T02`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/obs-03-t03`
- Worktree: `../alon-ai-task-obs-03-t03`
- Acceptance evidence: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L110) — Test evidence: weekend/holiday/100-unit/currency-exponent/rounding/missing/tamper vectors.
- Optional acceptance commands: none
- Merge order: 3

- Newly unlocked tasks: `AGENT-09-T02`, `AGENT-12-T01`, `PROVIDER-04-T05`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 90 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T02`, `AGENT-09-T01`, `PROVIDER-04-T04`

### I1 / R1 — `AGENT-09-T02`

- Source: [source](04-agents/10-experiment-evaluation-agent.md#L58)
- Dependencies: `AGENT-09-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-09-t02`
- Worktree: `../alon-ai-task-agent-09-t02`
- Acceptance evidence: [source](04-agents/10-experiment-evaluation-agent.md#L58) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-04-T05`

- Source: [source](05-providers/04-search-provider.md#L110)
- Dependencies: `PROVIDER-04-T04`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-04-t05`
- Worktree: `../alon-ai-task-provider-04-t05`
- Acceptance evidence: [source](05-providers/04-search-provider.md#L110) — Test evidence: contract suite and secret/PII log scan.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 91 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `DB-04-T01`, `AGENT-01-T01`, `AGENT-10-T01`, `AGENT-09-T01`, `DB-04-T03`, `PROVIDER-05-T02`, `OBS-03-T02`

### I1 / R1 — `AGENT-12-T01`

- Source: [source](04-agents/11-global-learning-engine.md#L57)
- Dependencies: `AGENT-09-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-04-T01`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-12-t01`
- Worktree: `../alon-ai-task-agent-12-t01`
- Acceptance evidence: [source](04-agents/11-global-learning-engine.md#L57) — Test evidence: strict schema, hash/version and missing-provider-input cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-05-T03`

- Source: [source](05-providers/05-page-fetching-and-extraction.md#L111)
- Dependencies: `PROVIDER-05-T02`, `OBS-03-T02`, `DB-04-T03`
- Mode: `parallel`
- Locks: `provider-contracts`, `backend-domain`, `agent-artifacts`
- Branch: `agent/provider-05-t03`
- Worktree: `../alon-ai-task-provider-05-t03`
- Acceptance evidence: [source](05-providers/05-page-fetching-and-extraction.md#L111) — Test evidence: SSRF and hostile-content suite.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-12-T02`, `PROVIDER-05-T04`, `PROVIDER-08-T03`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 92 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T02`, `AGENT-12-T01`, `PROVIDER-05-T03`

### I1 / R1 — `AGENT-12-T02`

- Source: [source](04-agents/11-global-learning-engine.md#L59)
- Dependencies: `AGENT-12-T01`, `AGENT-01-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-12-t02`
- Worktree: `../alon-ai-task-agent-12-t02`
- Acceptance evidence: [source](04-agents/11-global-learning-engine.md#L59) — Test evidence: tool denial, timeout, cancellation and all numeric boundary cases.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-05-T04`

- Source: [source](05-providers/05-page-fetching-and-extraction.md#L113)
- Dependencies: `PROVIDER-05-T03`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-05-t04`
- Worktree: `../alon-ai-task-provider-05-t04`
- Acceptance evidence: [source](05-providers/05-page-fetching-and-extraction.md#L113) — Test evidence: independent hash encoders and Unicode boundary suite.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `PROVIDER-05-T05`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 93 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T02`, `OBS-03-T02`, `PROVIDER-05-T04`

### I1 / R1 — `AGENT-01-T03`

- Source: [source](04-agents/01-agent-runtime-and-contracts.md#L701)
- Dependencies: `AGENT-01-T02`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-01-t03`
- Worktree: `../alon-ai-task-agent-01-t03`
- Acceptance evidence: [source](04-agents/01-agent-runtime-and-contracts.md#L701) — Test evidence: fake-model/tool timeout/cancel/budget boundary matrix; fake-HTTP execution of a fresh unpromoted signed candidate-configuration fixture succeeds under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-05-T05`

- Source: [source](05-providers/05-page-fetching-and-extraction.md#L115)
- Dependencies: `PROVIDER-05-T04`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-05-t05`
- Worktree: `../alon-ai-task-provider-05-t05`
- Acceptance evidence: [source](05-providers/05-page-fetching-and-extraction.md#L115) — Test evidence: graph, log/PII scan, purge/incident fixtures.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-01-T04`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 94 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PROVIDER-06-T01`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T03`, `PROVIDER-04-T03`

### I1 / R1 — `AGENT-01-T04`

- Source: [source](04-agents/01-agent-runtime-and-contracts.md#L703)
- Dependencies: `AGENT-01-T03`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-01-t04`
- Worktree: `../alon-ai-task-agent-01-t04`
- Acceptance evidence: [source](04-agents/01-agent-runtime-and-contracts.md#L703) — Test evidence: failure injection at every write and event payload snapshot.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `PROVIDER-06-T02`

- Source: [source](05-providers/06-enrichment-provider.md#L103)
- Dependencies: `PROVIDER-06-T01`, `PROVIDER-04-T03`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-06-t02`
- Worktree: `../alon-ai-task-provider-06-t02`
- Acceptance evidence: [source](05-providers/06-enrichment-provider.md#L103) — Test evidence: Unicode/domain/country/concurrency/conflict vectors.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `AGENT-01-T05`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-06-T03`, `AGENT-07-T03`, `AGENT-08-T03`, `AGENT-09-T03`, `AGENT-12-T03`, `AGENT-04-T03`, `PROVIDER-06-T03`, `BACKEND-01-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 95 — M3

- Agent count: 3 implementer(s) and 3 reviewer(s)
- Base prerequisite barrier: `AGENT-02-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`, `PROVIDER-06-T02`

### I1 / R1 — `AGENT-01-T05`

- Source: [source](04-agents/01-agent-runtime-and-contracts.md#L705)
- Dependencies: `AGENT-01-T04`
- Mode: `parallel`
- Locks: `agent-runtime`
- Branch: `agent/agent-01-t05`
- Worktree: `../alon-ai-task-agent-01-t05`
- Acceptance evidence: [source](04-agents/01-agent-runtime-and-contracts.md#L705) — Test evidence: static architecture test and log/trace secret/PII scan.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `AGENT-02-T03`

- Source: [source](04-agents/02-idea-discovery-agent.md#L61)
- Dependencies: `AGENT-02-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-02-t03`
- Worktree: `../alon-ai-task-agent-02-t03`
- Acceptance evidence: [source](04-agents/02-idea-discovery-agent.md#L61) — Test evidence: idea_bypass_shape_and_provenance; missing_scope_abstains; evidence_fact_hypothesis_separation; offer_input_is_forbidden.
- Optional acceptance commands: none
- Merge order: 2

### I3 / R3 — `PROVIDER-06-T03`

- Source: [source](05-providers/06-enrichment-provider.md#L105)
- Dependencies: `PROVIDER-06-T02`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-06-t03`
- Worktree: `../alon-ai-task-provider-06-t03`
- Acceptance evidence: [source](05-providers/06-enrichment-provider.md#L105) — Test evidence: tamper, cross-capability, zero-network, usage, and parity tests.
- Optional acceptance commands: none
- Merge order: 3

- Newly unlocked tasks: `ARCH-02-T03`, `AGENT-05-T03`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 96 — M3

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `TEST-04-T01`, `ARCH-02-T02`, `AGENT-03-T02`, `PROVIDER-03-T04`, `BACKEND-01-T01`, `DB-04-T04`, `BACKEND-03-T03`, `OBS-03-T02`, `AGENT-01-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`

### I1 / R1 — `AGENT-03-T03`

- Source: [source](04-agents/04-offer-design-agent.md#L63)
- Dependencies: `AGENT-03-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `BACKEND-03-T03`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-03-t03`
- Worktree: `../alon-ai-task-agent-03-t03`
- Acceptance evidence: [source](04-agents/04-offer-design-agent.md#L63) — Test evidence: offer_requires_idea_and_market_versions; complete_commercial_envelope_and_margin_floor; claim_evidence_coverage; downstream_commercial_redefinition_is_rejected.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `ARCH-02-T03`

- Source: [source](01-architecture/02-module-boundaries.md#L118)
- Dependencies: `ARCH-02-T02`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `TEST-04-T01`
- Mode: `parallel`
- Locks: `architecture-contracts`, `provider-contracts`
- Branch: `agent/arch-02-t03`
- Worktree: `../alon-ai-task-arch-02-t03`
- Acceptance evidence: [source](01-architecture/02-module-boundaries.md#L118) — Test evidence: each contract suite passes against its signed fixture/simulator and a fake replacement adapter.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 97 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-06-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`

### I1 / R1 — `AGENT-06-T03`

- Source: [source](04-agents/07-lead-qualification-agent.md#L60)
- Dependencies: `AGENT-06-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-06-t03`
- Worktree: `../alon-ai-task-agent-06-t03`
- Acceptance evidence: [source](04-agents/07-lead-qualification-agent.md#L60) — Test evidence: final_phase_and_offer_filter_exactness; required_unknown_or_failure_cannot_qualify; estimate_cannot_satisfy_fact_condition; qualification_does_not_authorize_send.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 98 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-07-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`

### I1 / R1 — `AGENT-07-T03`

- Source: [source](04-agents/08-email-writing-agent.md#L60)
- Dependencies: `AGENT-07-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-07-t03`
- Worktree: `../alon-ai-task-agent-07-t03`
- Acceptance evidence: [source](04-agents/08-email-writing-agent.md#L60) — Test evidence: initial_and_response_evidence_coverage; reply_objective_and_terms_are_exact; stale_thread_invalidates_draft; writer_has_no_send_or_calendar_authority.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 99 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-08-T02`, `BACKEND-01-T01`, `DB-04-T04`, `BACKEND-03-T03`, `OBS-03-T02`, `AGENT-01-T04`

### I1 / R1 — `AGENT-08-T03`

- Source: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L62)
- Dependencies: `AGENT-08-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `BACKEND-03-T03`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-08-t03`
- Worktree: `../alon-ai-task-agent-08-t03`
- Acceptance evidence: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L62) — Test evidence: ordinary_reply_and_rejection_do_not_invent_suppression; genuine_objection_vs_rejection; stated_budget_and_commercial_floor_matrix; call_agreement_is_not_purchase_or_slot_acceptance; terminal_round_limit_and_stale_thread.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 100 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-09-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`

### I1 / R1 — `AGENT-09-T03`

- Source: [source](04-agents/10-experiment-evaluation-agent.md#L60)
- Dependencies: `AGENT-09-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-09-t03`
- Worktree: `../alon-ai-task-agent-09-t03`
- Acceptance evidence: [source](04-agents/10-experiment-evaluation-agent.md#L60) — Test evidence: frozen_checkpoint_splice_and_cutoff; exact_five_decisions; insufficient_or_unsafe_evidence_cannot_continue; final_continue_has_no_fifth_cohort.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 101 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-12-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`

### I1 / R1 — `AGENT-12-T03`

- Source: [source](04-agents/11-global-learning-engine.md#L61)
- Dependencies: `AGENT-12-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-12-t03`
- Worktree: `../alon-ai-task-agent-12-t03`
- Acceptance evidence: [source](04-agents/11-global-learning-engine.md#L61) — Test evidence: only_closed_checkpoint_triggers_learning; all_applicable_agents_exact_four_results; weak_evidence_keeps_strategy; protected_holdout_and_cross_campaign_guardrails; boundary_activation_and_rollback_preserve_history.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 102 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-04-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`

### I1 / R1 — `AGENT-04-T03`

- Source: [source](04-agents/03-market-research-agent.md#L61)
- Dependencies: `AGENT-04-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `PROVIDER-04-T04`, `PROVIDER-05-T04`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-04-t03`
- Worktree: `../alon-ai-task-agent-04-t03`
- Acceptance evidence: [source](04-agents/03-market-research-agent.md#L61) — Test evidence: market_requires_accepted_idea; offer_cannot_feed_market_research; stale_numeric_conflict_and_injection_matrix; unsupported_demand_abstains.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 103 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-05-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`

### I1 / R1 — `AGENT-05-T03`

- Source: [source](04-agents/06-lead-research-agent.md#L61)
- Dependencies: `AGENT-05-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `PROVIDER-05-T04`, `PROVIDER-06-T03`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-05-t03`
- Worktree: `../alon-ai-task-agent-05-t03`
- Acceptance evidence: [source](04-agents/06-lead-research-agent.md#L61) — Test evidence: research_requires_preliminary_phase; fact_estimate_unknown_and_source_spans; owner_business_linkage_requires_evidence; sparse_and_conflicting_sources_abstain.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 104 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-08-T02`, `PROVIDER-05-T03`

### I1 / R1 — `PROVIDER-08-T03`

- Source: [source](05-providers/08-lead-discovery-provider.md#L55)
- Dependencies: `PROVIDER-08-T02`, `PROVIDER-05-T03`
- Mode: `parallel`
- Locks: `provider-contracts`, `agent-artifacts`
- Branch: `agent/provider-08-t03`
- Worktree: `../alon-ai-task-provider-08-t03`
- Acceptance evidence: [source](05-providers/08-lead-discovery-provider.md#L55) — Test evidence: request/result/ledger parity, redaction, cross-source identity conflicts and no qualification/merge writes.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-11-T03`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 105 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-11-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`, `PROVIDER-08-T03`

### I1 / R1 — `AGENT-11-T03`

- Source: [source](04-agents/05-lead-discovery-agent.md#L60)
- Dependencies: `AGENT-11-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `PROVIDER-08-T03`
- Mode: `parallel`
- Locks: `agent-artifacts`, `backend-domain`
- Branch: `agent/agent-11-t03`
- Worktree: `../alon-ai-task-agent-11-t03`
- Acceptance evidence: [source](04-agents/05-lead-discovery-agent.md#L60) — Test evidence: cross_source_deduplication_and_identity_conflict; preliminary_rejection_has_no_deep_research; unknown_required_filter_fails_closed; fabricated_identity_and_unapproved_source_rejected.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-10-T02`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 106 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T01`, `AGENT-10-T01`, `PROVIDER-03-T04`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-06-T03`, `AGENT-07-T03`, `AGENT-08-T03`, `AGENT-09-T03`, `AGENT-12-T03`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `AGENT-04-T03`, `PROVIDER-06-T03`, `AGENT-05-T03`, `PROVIDER-08-T03`, `AGENT-11-T03`

### I1 / R1 — `AGENT-10-T02`

- Source: [source](04-agents/12-agent-evals-and-versioning.md#L367)
- Dependencies: `AGENT-10-T01`, `AGENT-01-T01`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`, `AGENT-05-T03`, `AGENT-06-T03`, `AGENT-07-T03`, `AGENT-08-T03`, `AGENT-09-T03`, `AGENT-11-T03`, `AGENT-12-T03`, `PROVIDER-08-T03`
- Mode: `parallel`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-10-t02`
- Worktree: `../alon-ai-task-agent-10-t02`
- Acceptance evidence: [source](04-agents/12-agent-evals-and-versioning.md#L367) — Test evidence: configuration/fixture/code hash mismatch, missing specialist, disallowed search.query for lead research, and unsigned candidate negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-10-T03`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 107 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-01-T01`, `PROVIDER-03-T01`, `PROVIDER-03-T02`, `BACKEND-01-T01`, `OBS-03-T02`, `AGENT-01-T04`, `AGENT-10-T02`

### I1 / R1 — `AGENT-10-T03`

- Source: [source](04-agents/12-agent-evals-and-versioning.md#L369)
- Dependencies: `AGENT-10-T02`, `PROVIDER-03-T01`, `OBS-03-T02`, `AGENT-01-T01`, `AGENT-01-T04`, `PROVIDER-03-T02`, `BACKEND-01-T01`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`, `live-environment`
- Branch: `agent/agent-10-t03`
- Worktree: `../alon-ai-task-agent-10-t03`
- Acceptance evidence: [source](04-agents/12-agent-evals-and-versioning.md#L369) — Test evidence: live fake-model/provider-ID, replay-rejection, missing-capture, cancel, timeout, token/cost-bound, signature, and no-product-authority tests; fresh unpromoted code-bound signed candidate captures under isolated evaluation authority with all ceilings intact; the identical context fails product composition before credential access; missing signature/reservation, drift and non-model/product authority fail closed.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-10-T04`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 108 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T03`

### I1 / R1 — `AGENT-10-T04`

- Source: [source](04-agents/12-agent-evals-and-versioning.md#L371)
- Dependencies: `AGENT-10-T03`
- Mode: `parallel`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-10-t04`
- Worktree: `../alon-ai-task-agent-10-t04`
- Acceptance evidence: [source](04-agents/12-agent-evals-and-versioning.md#L371) — Test evidence: all normative golden vectors in independent Decimal/Fraction implementations plus threshold, tie, and missing-prediction cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-02-T04`, `AGENT-04-T04`, `AGENT-03-T04`, `AGENT-11-T04`, `AGENT-05-T04`, `AGENT-06-T04`, `AGENT-07-T04`, `AGENT-08-T04`, `AGENT-09-T04`, `AGENT-12-T04`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 109 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-02-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-02-T04`

- Source: [source](04-agents/02-idea-discovery-agent.md#L63)
- Dependencies: `AGENT-02-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-02-t04`
- Worktree: `../alon-ai-task-agent-02-t04`
- Acceptance evidence: [source](04-agents/02-idea-discovery-agent.md#L63) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 110 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-04-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-04-T04`

- Source: [source](04-agents/03-market-research-agent.md#L63)
- Dependencies: `AGENT-04-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-04-t04`
- Worktree: `../alon-ai-task-agent-04-t04`
- Acceptance evidence: [source](04-agents/03-market-research-agent.md#L63) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 111 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-03-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-03-T04`

- Source: [source](04-agents/04-offer-design-agent.md#L65)
- Dependencies: `AGENT-03-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-03-t04`
- Worktree: `../alon-ai-task-agent-03-t04`
- Acceptance evidence: [source](04-agents/04-offer-design-agent.md#L65) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 112 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-11-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-11-T04`

- Source: [source](04-agents/05-lead-discovery-agent.md#L62)
- Dependencies: `AGENT-11-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-11-t04`
- Worktree: `../alon-ai-task-agent-11-t04`
- Acceptance evidence: [source](04-agents/05-lead-discovery-agent.md#L62) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 113 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-05-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-05-T04`

- Source: [source](04-agents/06-lead-research-agent.md#L63)
- Dependencies: `AGENT-05-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-05-t04`
- Worktree: `../alon-ai-task-agent-05-t04`
- Acceptance evidence: [source](04-agents/06-lead-research-agent.md#L63) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 114 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-06-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-06-T04`

- Source: [source](04-agents/07-lead-qualification-agent.md#L62)
- Dependencies: `AGENT-06-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-06-t04`
- Worktree: `../alon-ai-task-agent-06-t04`
- Acceptance evidence: [source](04-agents/07-lead-qualification-agent.md#L62) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 115 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-07-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-07-T04`

- Source: [source](04-agents/08-email-writing-agent.md#L62)
- Dependencies: `AGENT-07-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-07-t04`
- Worktree: `../alon-ai-task-agent-07-t04`
- Acceptance evidence: [source](04-agents/08-email-writing-agent.md#L62) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 116 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-08-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-08-T04`

- Source: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L64)
- Dependencies: `AGENT-08-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-08-t04`
- Worktree: `../alon-ai-task-agent-08-t04`
- Acceptance evidence: [source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L64) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 117 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-09-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-09-T04`

- Source: [source](04-agents/10-experiment-evaluation-agent.md#L62)
- Dependencies: `AGENT-09-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-09-t04`
- Worktree: `../alon-ai-task-agent-09-t04`
- Acceptance evidence: [source](04-agents/10-experiment-evaluation-agent.md#L62) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 118 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-12-T03`, `AGENT-10-T03`, `AGENT-10-T04`

### I1 / R1 — `AGENT-12-T04`

- Source: [source](04-agents/11-global-learning-engine.md#L63)
- Dependencies: `AGENT-12-T03`, `AGENT-10-T03`, `AGENT-10-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`
- Branch: `agent/agent-12-t04`
- Worktree: `../alon-ai-task-agent-12-t04`
- Acceptance evidence: [source](04-agents/11-global-learning-engine.md#L63) — Test evidence: missing capture, fixture drift, hard failure and threshold-edge rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `AGENT-10-T05`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 119 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T04`, `AGENT-02-T04`, `AGENT-04-T04`, `AGENT-03-T04`, `AGENT-11-T04`, `AGENT-05-T04`, `AGENT-06-T04`, `AGENT-07-T04`, `AGENT-08-T04`, `AGENT-09-T04`, `AGENT-12-T04`

### I1 / R1 — `AGENT-10-T05`

- Source: [source](04-agents/12-agent-evals-and-versioning.md#L373)
- Dependencies: `AGENT-10-T04`, `AGENT-02-T04`, `AGENT-03-T04`, `AGENT-04-T04`, `AGENT-05-T04`, `AGENT-06-T04`, `AGENT-07-T04`, `AGENT-08-T04`, `AGENT-09-T04`, `AGENT-11-T04`, `AGENT-12-T04`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`, `milestone-gate`, `ci-release`
- Branch: `agent/agent-10-t05`
- Worktree: `../alon-ai-task-agent-10-t05`
- Acceptance evidence: [source](04-agents/12-agent-evals-and-versioning.md#L373) — Test evidence: missing component/repetition, threshold equality, one-unit failure, concurrent/stale registry and tamper cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-04-T05`, `AGENT-10-T06`, `PROVIDER-03-T05`, `WF-03-T01`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 120 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-04-T04`, `AGENT-10-T05`

### I1 / R1 — `DB-04-T05`

- Source: [source](02-database/04-agent-artifacts-and-evidence.md#L110)
- Dependencies: `DB-04-T04`, `AGENT-10-T05`
- Mode: `parallel`
- Locks: `agent-runtime`, `agent-artifacts`, `telemetry-catalog`
- Branch: `agent/db-04-t05`
- Worktree: `../alon-ai-task-db-04-t05`
- Acceptance evidence: [source](02-database/04-agent-artifacts-and-evidence.md#L110) — Test evidence: deterministic fixture rerun.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-01-T03`, `WF-03-T01`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 121 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-02-T01`, `ARCH-01-T02`, `ARCH-02-T03`, `AGENT-10-T05`, `DB-04-T05`

### I1 / R1 — `ARCH-01-T03`

- Source: [source](01-architecture/01-target-system-architecture.md#L164)
- Dependencies: `ARCH-01-T02`, `ARCH-02-T01`, `AGENT-10-T05`, `DB-04-T05`, `ARCH-02-T03`
- Mode: `parallel`
- Locks: `architecture-contracts`, `agent-runtime`, `agent-artifacts`, `provider-contracts`
- Branch: `agent/arch-01-t03`
- Worktree: `../alon-ai-task-arch-01-t03`
- Acceptance evidence: [source](01-architecture/01-target-system-architecture.md#L164) — Test evidence: schema, provenance, adversarial quality, cost, and regression reports.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-03-T01`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 122 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T05`

### I1 / R1 — `AGENT-10-T06`

- Source: [source](04-agents/12-agent-evals-and-versioning.md#L375)
- Dependencies: `AGENT-10-T05`
- Mode: `serial`
- Locks: `agent-runtime`, `ci-release`
- Branch: `agent/agent-10-t06`
- Worktree: `../alon-ai-task-agent-10-t06`
- Acceptance evidence: [source](04-agents/12-agent-evals-and-versioning.md#L375) — Test evidence: manifest drift, hard incident, two-window breach and incompatible in-flight run drills.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-03-T01`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 123 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-03-T04`, `AGENT-10-T05`

### I1 / R1 — `PROVIDER-03-T05`

- Source: [source](05-providers/03-model-provider.md#L114)
- Dependencies: `PROVIDER-03-T04`, `AGENT-10-T05`
- Mode: `serial`
- Locks: `provider-contracts`, `milestone-gate`
- Branch: `agent/provider-03-t05`
- Worktree: `../alon-ai-task-provider-03-t05`
- Acceptance evidence: [source](05-providers/03-model-provider.md#L114) — Test evidence: unpromoted/stale/spliced configuration, disabled evaluation credential, missing reservation and exact promoted positive fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-03-T06`, `WF-03-T01`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 124 — M3

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-03-T05`

### I1 / R1 — `PROVIDER-03-T06`

- Source: [source](05-providers/03-model-provider.md#L116)
- Dependencies: `PROVIDER-03-T05`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-03-t06`
- Worktree: `../alon-ai-task-provider-03-t06`
- Acceptance evidence: [source](05-providers/03-model-provider.md#L116) — Test evidence: provider parity and static/runtime graph.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-03-T01`, `BACKEND-01-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 125 — M4

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PRODUCT-02-T01`, `ARCH-03-T01`, `DB-02-T03`, `DB-02-T04`, `DB-06-T01`, `BACKEND-01-T01`, `AGENT-10-T05`

### I1 / R1 — `WF-03-T01`

- Source: [source](03-workflows/03-idea-validation-workflow.md#L48)
- Dependencies: `AGENT-10-T05`, `DB-02-T03`, `DB-02-T04`, `PRODUCT-02-T01`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-03-t01`
- Worktree: `../alon-ai-task-wf-03-t01`
- Acceptance evidence: [source](03-workflows/03-idea-validation-workflow.md#L48) — Test evidence: origin exclusivity, duplicate bypass and provenance checks.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `BACKEND-01-T02`

- Source: [source](06-backend/01-domain-services.md#L88)
- Dependencies: `BACKEND-01-T01`, `ARCH-03-T01`, `DB-06-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-01-t02`
- Worktree: `../alon-ai-task-backend-01-t02`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L88) — Test evidence: exhaustive state/guard/property snapshots.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `BACKEND-01-T03`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 126 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-02-T01`, `DB-05-T03`, `BACKEND-01-T02`

### I1 / R1 — `BACKEND-01-T03`

- Source: [source](06-backend/01-domain-services.md#L90)
- Dependencies: `BACKEND-01-T02`, `ARCH-02-T01`, `DB-05-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-01-t03`
- Worktree: `../alon-ai-task-backend-01-t03`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L90) — Test evidence: real-PostgreSQL concurrency/failure injection at every write.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T04`, `BACKEND-02-T01`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 127 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-06-T01`, `BACKEND-03-T03`, `BACKEND-01-T03`

### I1 / R1 — `BACKEND-01-T04`

- Source: [source](06-backend/01-domain-services.md#L92)
- Dependencies: `BACKEND-01-T03`, `DB-06-T01`, `BACKEND-03-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-01-t04`
- Worktree: `../alon-ai-task-backend-01-t04`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L92) — Test evidence: table-writer/import rules and M2/M4/M5 integration cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-02-T01`, `WF-03-T02`, `BACKEND-01-T05`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 128 — M4

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `WF-01-T05`, `WF-00-T04`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `AGENT-10-T05`, `PROVIDER-03-T06`, `BACKEND-01-T04`

### I1 / R1 — `WF-02-T01`

- Source: [source](03-workflows/02-experiment-lifecycle.md#L49)
- Dependencies: `BACKEND-01-T04`, `AGENT-10-T05`, `PROVIDER-03-T06`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `WF-01-T05`, `WF-00-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-02-t01`
- Worktree: `../alon-ai-task-wf-02-t01`
- Acceptance evidence: [source](03-workflows/02-experiment-lifecycle.md#L49) — Test evidence: provider-before-consumer and missing-artifact failures.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `BACKEND-01-T05`

- Source: [source](06-backend/01-domain-services.md#L94)
- Dependencies: `BACKEND-01-T04`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `backend-domain`, `provider-contracts`
- Branch: `agent/backend-01-t05`
- Worktree: `../alon-ai-task-backend-01-t05`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L94) — Test evidence: kill/cancel/provider status matrix.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `WF-02-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 129 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-02-T01`

### I1 / R1 — `WF-02-T02`

- Source: [source](03-workflows/02-experiment-lifecycle.md#L51)
- Dependencies: `WF-02-T01`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-02-t02`
- Worktree: `../alon-ai-task-wf-02-t02`
- Acceptance evidence: [source](03-workflows/02-experiment-lifecycle.md#L51) — Test evidence: duplicate start, transaction crash and hash-splice matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-02-T03`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 130 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-02-T02`

### I1 / R1 — `WF-02-T03`

- Source: [source](03-workflows/02-experiment-lifecycle.md#L53)
- Dependencies: `WF-02-T02`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-02-t03`
- Worktree: `../alon-ai-task-wf-02-t03`
- Acceptance evidence: [source](03-workflows/02-experiment-lifecycle.md#L53) — Test evidence: all legal/illegal exits and stale generation cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-02-T04`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 131 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-02-T03`

### I1 / R1 — `WF-02-T04`

- Source: [source](03-workflows/02-experiment-lifecycle.md#L55)
- Dependencies: `WF-02-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-02-t04`
- Worktree: `../alon-ai-task-wf-02-t04`
- Acceptance evidence: [source](03-workflows/02-experiment-lifecycle.md#L55) — Test evidence: finite completion/cancellation and zero Gmail/calendar access.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 132 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `WF-03-T01`, `BACKEND-01-T04`

### I1 / R1 — `WF-03-T02`

- Source: [source](03-workflows/03-idea-validation-workflow.md#L50)
- Dependencies: `WF-03-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`, `BACKEND-01-T01`, `DB-04-T04`, `BACKEND-01-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`, `agent-artifacts`
- Branch: `agent/wf-03-t02`
- Worktree: `../alon-ai-task-wf-03-t02`
- Acceptance evidence: [source](03-workflows/03-idea-validation-workflow.md#L50) — Test evidence: bypass equivalence, missing idea, stale source and injection cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-03-T03`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 133 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-04-T04`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`, `BACKEND-01-T04`, `WF-03-T02`

### I1 / R1 — `WF-03-T03`

- Source: [source](03-workflows/03-idea-validation-workflow.md#L52)
- Dependencies: `WF-03-T02`, `DB-04-T04`, `BACKEND-01-T04`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`, `agent-artifacts`
- Branch: `agent/wf-03-t03`
- Worktree: `../alon-ai-task-wf-03-t03`
- Acceptance evidence: [source](03-workflows/03-idea-validation-workflow.md#L52) — Test evidence: reversed order, incomplete economics and downstream authority denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-03-T04`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 134 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-02-T03`, `WF-03-T03`

### I1 / R1 — `WF-03-T04`

- Source: [source](03-workflows/03-idea-validation-workflow.md#L54)
- Dependencies: `WF-03-T03`, `WF-02-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-03-t04`
- Worktree: `../alon-ai-task-wf-03-t04`
- Acceptance evidence: [source](03-workflows/03-idea-validation-workflow.md#L54) — Test evidence: no repeated paid call, double materialization or stale consumer.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-03-T05`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 135 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-03-T04`

### I1 / R1 — `WF-03-T05`

- Source: [source](03-workflows/03-idea-validation-workflow.md#L56)
- Dependencies: `WF-03-T04`
- Mode: `serial`
- Locks: `workflow-runtime`, `milestone-gate`
- Branch: `agent/wf-03-t05`
- Worktree: `../alon-ai-task-wf-03-t05`
- Acceptance evidence: [source](03-workflows/03-idea-validation-workflow.md#L56) — Test evidence: both origins complete exactly idea -> research -> offer.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 136 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T03`

### I1 / R1 — `BACKEND-02-T01`

- Source: [source](06-backend/02-api-contracts.md#L316)
- Dependencies: `BACKEND-01-T03`
- Mode: `serial`
- Locks: `openapi-contract`
- Branch: `agent/backend-02-t01`
- Worktree: `../alon-ai-task-backend-02-t01`
- Acceptance evidence: [source](06-backend/02-api-contracts.md#L316) — Test evidence: fixture-actor, header, replay, error, and correlation snapshot matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-02-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 137 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T04`, `BACKEND-02-T01`

### I1 / R1 — `BACKEND-02-T02`

- Source: [source](06-backend/02-api-contracts.md#L318)
- Dependencies: `BACKEND-02-T01`, `BACKEND-01-T04`
- Mode: `serial`
- Locks: `openapi-contract`
- Branch: `agent/backend-02-t02`
- Worktree: `../alon-ai-task-backend-02-t02`
- Acceptance evidence: [source](06-backend/02-api-contracts.md#L318) — Test evidence: OpenAPI generation and real-service integration tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-01-T01`, `INFRA-01-T06`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 138 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T02`

### I1 / R1 — `FRONTEND-01-T01`

- Source: [source](07-frontend/01-information-architecture.md#L38)
- Dependencies: `BACKEND-02-T02`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-01-t01`
- Worktree: `../alon-ai-task-frontend-01-t01`
- Acceptance evidence: [source](07-frontend/01-information-architecture.md#L38) — Test evidence: every operation has one owner; forbidden provider/DB imports fail.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-01-T02`, `FRONTEND-02-T01`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 139 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T01`, `FRONTEND-01-T01`

### I1 / R1 — `FRONTEND-01-T02`

- Source: [source](07-frontend/01-information-architecture.md#L40)
- Dependencies: `FRONTEND-01-T01`, `BACKEND-02-T01`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-01-t02`
- Worktree: `../alon-ai-task-frontend-01-t02`
- Acceptance evidence: [source](07-frontend/01-information-architecture.md#L40) — Test evidence: 401/403, expired cursors, partial snapshots and unknown enums remain visible.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-01-T03`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 140 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-01-T02`

### I1 / R1 — `FRONTEND-01-T03`

- Source: [source](07-frontend/01-information-architecture.md#L42)
- Dependencies: `FRONTEND-01-T02`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-01-t03`
- Worktree: `../alon-ai-task-frontend-01-t03`
- Acceptance evidence: [source](07-frontend/01-information-architecture.md#L42) — Test evidence: forged browser state cannot enable a command.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-01-T04`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 141 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-01-T03`

### I1 / R1 — `FRONTEND-01-T04`

- Source: [source](07-frontend/01-information-architecture.md#L44)
- Dependencies: `FRONTEND-01-T03`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-01-t04`
- Worktree: `../alon-ai-task-frontend-01-t04`
- Acceptance evidence: [source](07-frontend/01-information-architecture.md#L44) — Test evidence: keyboard, screen-reader, mobile, no-store and logout tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 142 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T01`, `FRONTEND-01-T01`

### I1 / R1 — `FRONTEND-02-T01`

- Source: [source](07-frontend/02-experiment-creation-flow.md#L28)
- Dependencies: `FRONTEND-01-T01`, `DB-02-T01`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-02-t01`
- Worktree: `../alon-ai-task-frontend-02-t01`
- Acceptance evidence: [source](07-frontend/02-experiment-creation-flow.md#L28) — Test evidence: unknown fields/origin, duplicate submission and invalid budgets fail.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-02-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 143 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-02-T01`

### I1 / R1 — `FRONTEND-02-T02`

- Source: [source](07-frontend/02-experiment-creation-flow.md#L30)
- Dependencies: `FRONTEND-02-T01`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-02-t02`
- Worktree: `../alon-ai-task-frontend-02-t02`
- Acceptance evidence: [source](07-frontend/02-experiment-creation-flow.md#L30) — Test evidence: no upstream OfferPackage input, no research before accepted IdeaBrief.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-02-T03`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 144 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-02-T02`

### I1 / R1 — `FRONTEND-02-T03`

- Source: [source](07-frontend/02-experiment-creation-flow.md#L32)
- Dependencies: `FRONTEND-02-T02`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-02-t03`
- Worktree: `../alon-ai-task-frontend-02-t03`
- Acceptance evidence: [source](07-frontend/02-experiment-creation-flow.md#L32) — Test evidence: stale ETag, unsupported terms and active-cohort mutation deny.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-02-T04`, `FRONTEND-03-T01`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 145 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-02-T03`

### I1 / R1 — `FRONTEND-02-T04`

- Source: [source](07-frontend/02-experiment-creation-flow.md#L34)
- Dependencies: `FRONTEND-02-T03`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-02-t04`
- Worktree: `../alon-ai-task-frontend-02-t04`
- Acceptance evidence: [source](07-frontend/02-experiment-creation-flow.md#L34) — Test evidence: same key replays one experiment; no provider side effect or invented acceptance.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 146 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-01-T01`, `FRONTEND-02-T03`

### I1 / R1 — `FRONTEND-03-T01`

- Source: [source](07-frontend/03-experiment-control-center.md#L28)
- Dependencies: `FRONTEND-02-T03`, `FRONTEND-01-T01`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-03-t01`
- Worktree: `../alon-ai-task-frontend-03-t01`
- Acceptance evidence: [source](07-frontend/03-experiment-control-center.md#L28) — Test evidence: missing provider artifact prevents consumer affordance.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-03-T02`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 147 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-03-T01`

### I1 / R1 — `FRONTEND-03-T02`

- Source: [source](07-frontend/03-experiment-control-center.md#L30)
- Dependencies: `FRONTEND-03-T01`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-03-t02`
- Worktree: `../alon-ai-task-frontend-03-t02`
- Acceptance evidence: [source](07-frontend/03-experiment-control-center.md#L30) — Test evidence: pause acknowledgement, stale generation and terminal-resume tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 148 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-01-T05`, `DB-06-T02`, `BACKEND-02-T02`

### I1 / R1 — `INFRA-01-T06`

- Source: [source](11-infrastructure/01-local-development.md#L83)
- Dependencies: `INFRA-01-T05`, `DB-06-T02`, `BACKEND-02-T02`
- Mode: `serial`
- Locks: `migration-head`, `openapi-contract`, `frontend-client`
- Branch: `agent/infra-01-t06`
- Worktree: `../alon-ai-task-infra-01-t06`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L83) — Test evidence: catalog/seed hash and generated no-diff.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-01-T07`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 149 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T05`, `INFRA-01-T06`

### I1 / R1 — `INFRA-01-T07`

- Source: [source](11-infrastructure/01-local-development.md#L85)
- Dependencies: `INFRA-01-T06`, `DB-01-T05`
- Mode: `serial`
- Locks: `compose-topology`, `migration-head`
- Branch: `agent/infra-01-t07`
- Worktree: `../alon-ai-task-infra-01-t07`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L85) — Test evidence: empty/wildcard/wrong-system-ID/production-like target refusal.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-01-T08`, `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 150 — M4

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T02`, `INFRA-01-T07`

### I1 / R1 — `INFRA-01-T08`

- Source: [source](11-infrastructure/01-local-development.md#L87)
- Dependencies: `INFRA-01-T07`, `TEST-01-T02`
- Mode: `serial`
- Locks: `compose-topology`, `test-command-registry`
- Branch: `agent/infra-01-t08`
- Worktree: `../alon-ai-task-infra-01-t08`
- Acceptance evidence: [source](11-infrastructure/01-local-development.md#L87) — Test evidence: unavailable Docker/provider reported as unavailable, not passed. Complete original target/version/hash/exit mapping negatives remain required.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T04`, `PROVIDER-08-T04`, `BACKEND-01-T06`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 151 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-03-T01`, `OBS-03-T02`, `PROVIDER-06-T03`

### I1 / R1 — `PROVIDER-06-T04`

- Source: [source](05-providers/06-enrichment-provider.md#L107)
- Dependencies: `PROVIDER-06-T03`, `OBS-03-T01`, `OBS-03-T02`
- Mode: `serial`
- Locks: `provider-contracts`, `live-environment`
- Branch: `agent/provider-06-t04`
- Worktree: `../alon-ai-task-provider-06-t04`
- Acceptance evidence: [source](05-providers/06-enrichment-provider.md#L107) — Test evidence: gate denial plus fake HTTP, field, terms, quota, and cost cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-06-T05`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 152 — M5

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T05`, `PROVIDER-06-T04`

### I1 / R1 — `PROVIDER-06-T05`

- Source: [source](05-providers/06-enrichment-provider.md#L109)
- Dependencies: `PROVIDER-06-T04`
- Mode: `parallel`
- Locks: `provider-contracts`
- Branch: `agent/provider-06-t05`
- Worktree: `../alon-ai-task-provider-06-t05`
- Acceptance evidence: [source](05-providers/06-enrichment-provider.md#L109) — Test evidence: forbidden-field and call-graph tests.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `BACKEND-01-T06`

- Source: [source](06-backend/01-domain-services.md#L96)
- Dependencies: `BACKEND-01-T05`
- Mode: `parallel`
- Locks: `architecture-contracts`
- Branch: `agent/backend-01-t06`
- Worktree: `../alon-ai-task-backend-01-t06`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L96) — Test evidence: static graph plus integration spies.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `BACKEND-01-T07`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 153 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-03-T02`, `PROVIDER-08-T03`

### I1 / R1 — `PROVIDER-08-T04`

- Source: [source](05-providers/08-lead-discovery-provider.md#L57)
- Dependencies: `PROVIDER-08-T03`, `OBS-03-T02`
- Mode: `serial`
- Locks: `provider-contracts`, `live-environment`
- Branch: `agent/provider-08-t04`
- Worktree: `../alon-ai-task-provider-08-t04`
- Acceptance evidence: [source](05-providers/08-lead-discovery-provider.md#L57) — Test evidence: unreviewed social/directory source denial, cap/cursor/revocation and factual-provenance cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 154 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T02`, `DB-04-T04`, `AGENT-06-T03`, `AGENT-11-T03`, `BACKEND-01-T06`

### I1 / R1 — `BACKEND-01-T07`

- Source: [source](06-backend/01-domain-services.md#L100)
- Dependencies: `BACKEND-01-T06`, `DB-03-T02`, `DB-04-T04`, `AGENT-11-T03`, `AGENT-06-T03`
- Mode: `parallel`
- Locks: `backend-domain`, `agent-artifacts`
- Branch: `agent/backend-01-t07`
- Worktree: `../alon-ai-task-backend-01-t07`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L100) — Test evidence: multi-source collision, unsupported person/linkage, preliminary/final phase, stale filter, costly research admission and writer-boundary tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-04-T01`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 155 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T03`, `PROVIDER-08-T03`, `WF-03-T03`, `WF-03-T05`, `BACKEND-01-T07`

### I1 / R1 — `WF-04-T01`

- Source: [source](03-workflows/04-lead-qualification-workflow.md#L47)
- Dependencies: `WF-03-T05`, `DB-02-T03`, `WF-03-T03`, `BACKEND-01-T07`, `PROVIDER-08-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-04-t01`
- Worktree: `../alon-ai-task-wf-04-t01`
- Acceptance evidence: [source](03-workflows/04-lead-qualification-workflow.md#L47) — Test evidence: missing/changed offer and unapproved-source denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-04-T02`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 156 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-08-T03`, `AGENT-11-T04`, `WF-04-T01`

### I1 / R1 — `WF-04-T02`

- Source: [source](03-workflows/04-lead-qualification-workflow.md#L49)
- Dependencies: `WF-04-T01`, `PROVIDER-08-T03`, `AGENT-11-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-04-t02`
- Worktree: `../alon-ai-task-wf-04-t02`
- Acceptance evidence: [source](03-workflows/04-lead-qualification-workflow.md#L49) — Test evidence: cross-source duplicates, false identity and preliminary rejection cost checks.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-04-T03`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 157 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-06-T01`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-05-T04`, `WF-04-T02`

### I1 / R1 — `WF-04-T03`

- Source: [source](03-workflows/04-lead-qualification-workflow.md#L51)
- Dependencies: `WF-04-T02`, `PROVIDER-06-T01`, `PROVIDER-06-T03`, `PROVIDER-05-T04`, `AGENT-05-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-04-t03`
- Worktree: `../alon-ai-task-wf-04-t03`
- Acceptance evidence: [source](03-workflows/04-lead-qualification-workflow.md#L51) — Test evidence: no research before preliminary pass and identity/source conflict cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-04-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 158 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-06-T04`, `BACKEND-01-T04`, `WF-04-T03`

### I1 / R1 — `WF-04-T04`

- Source: [source](03-workflows/04-lead-qualification-workflow.md#L53)
- Dependencies: `WF-04-T03`, `AGENT-06-T04`, `BACKEND-01-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-04-t04`
- Worktree: `../alon-ai-task-wf-04-t04`
- Acceptance evidence: [source](03-workflows/04-lead-qualification-workflow.md#L53) — Test evidence: required UNKNOWN/FAIL, phase splice and qualification-without-send authority.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-04-T05`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 159 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-02-T03`, `PROVIDER-08-T04`, `WF-04-T04`

### I1 / R1 — `WF-04-T05`

- Source: [source](03-workflows/04-lead-qualification-workflow.md#L55)
- Dependencies: `WF-04-T04`, `WF-02-T03`, `PROVIDER-08-T04`
- Mode: `serial`
- Locks: `workflow-runtime`, `milestone-gate`
- Branch: `agent/wf-04-t05`
- Worktree: `../alon-ai-task-wf-04-t05`
- Acceptance evidence: [source](03-workflows/04-lead-qualification-workflow.md#L55) — Test evidence: no duplicate decision/spend or active-cohort mutation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-01-T04`, `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `LAUNCH-01-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 160 — M5

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T04`, `PROVIDER-06-T03`, `ARCH-01-T03`, `WF-03-T05`, `WF-04-T05`

### I1 / R1 — `ARCH-01-T04`

- Source: [source](01-architecture/01-target-system-architecture.md#L166)
- Dependencies: `ARCH-01-T03`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-06-T03`, `WF-00-T04`
- Mode: `serial`
- Locks: `architecture-contracts`, `workflow-runtime`, `agent-artifacts`, `backend-domain`, `milestone-gate`
- Branch: `agent/arch-01-t04`
- Worktree: `../alon-ai-task-arch-01-t04`
- Acceptance evidence: [source](01-architecture/01-target-system-architecture.md#L166) — Test evidence: complete synthetic M4 and M5 runs, restart, provenance, cost, state, and zero-send assertions.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-04-T01`, `BACKEND-05-T01`, `SEC-04-T01`, `SEC-02-T01`, `OBS-05-T01`, `LAUNCH-01-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 161 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `ARCH-03-T01`, `BACKEND-03-T01`

### I1 / R1 — `BACKEND-04-T01`

- Source: [source](06-backend/04-send-gateway.md#L73)
- Dependencies: `PROVIDER-02-T01`, `BACKEND-03-T01`, `ARCH-03-T01`, `PROVIDER-01-T02`, `DB-03-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-04-t01`
- Worktree: `../alon-ai-task-backend-04-t01`
- Acceptance evidence: [source](06-backend/04-send-gateway.md#L73) — Test evidence: schema/composite/call-graph snapshots.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 162 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T01`, `DB-01-T02`, `DB-05-T02`

### I1 / R1 — `BACKEND-05-T01`

- Source: [source](06-backend/05-approval-and-command-handling.md#L118)
- Dependencies: `DB-05-T02`, `DB-01-T01`, `DB-01-T02`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-05-t01`
- Worktree: `../alon-ai-task-backend-05-t01`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L118) — Test evidence: schema/registry/concurrency/failure-injection matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 163 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T02`, `SEC-06-T01`

### I1 / R1 — `SEC-04-T01`

- Source: [source](08-security-and-compliance/04-outreach-compliance.md#L97)
- Dependencies: `SEC-06-T01`, `PRODUCT-01-T02`
- Mode: `serial`
- Locks: `compliance-policy`, `milestone-gate`
- Branch: `agent/sec-04-t01`
- Worktree: `../alon-ai-task-sec-04-t01`
- Acceptance evidence: [source](08-security-and-compliance/04-outreach-compliance.md#L97) — Test evidence: non-owned/unknown/cross-project mailbox, real recipient, missing attestation, excess scope/cap and attempted product enable all reject.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T02`, `SEC-05-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 164 — M6

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T01`, `ARCH-03-T01`, `DB-05-T01`, `SEC-04-T01`

### I1 / R1 — `SEC-04-T02`

- Source: [source](08-security-and-compliance/04-outreach-compliance.md#L99)
- Dependencies: `SEC-04-T01`
- Mode: `parallel`
- Locks: `compliance-policy`
- Branch: `agent/sec-04-t02`
- Worktree: `../alon-ai-task-sec-04-t02`
- Acceptance evidence: [source](08-security-and-compliance/04-outreach-compliance.md#L99) — Test evidence: unknown/conflict/stale/withdrawn/superseded matrix.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `OBS-05-T01`

- Source: [source](09-observability-and-evaluation/05-incident-response.md#L161)
- Dependencies: `ARCH-03-T01`, `DB-05-T01`, `PRODUCT-03-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/obs-05-t01`
- Worktree: `../alon-ai-task-obs-05-t01`
- Acceptance evidence: [source](09-observability-and-evaluation/05-incident-response.md#L161) — Test evidence: idempotency/concurrency/tamper/redaction/DB-unavailable journal import.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `SEC-04-T03`, `OBS-05-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 165 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-07-T03`, `SEC-04-T02`

### I1 / R1 — `SEC-04-T03`

- Source: [source](08-security-and-compliance/04-outreach-compliance.md#L101)
- Dependencies: `SEC-04-T02`, `AGENT-07-T03`
- Mode: `parallel`
- Locks: `compliance-policy`
- Branch: `agent/sec-04-t03`
- Worktree: `../alon-ai-task-sec-04-t03`
- Acceptance evidence: [source](08-security-and-compliance/04-outreach-compliance.md#L101) — Test evidence: deceptive/missing/hidden/tracking/sensitive-target fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 166 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `DB-01-T05`, `DB-05-T02`, `SEC-04-T01`

### I1 / R1 — `SEC-05-T01`

- Source: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L107)
- Dependencies: `DB-05-T02`, `ARCH-03-T01`, `DB-01-T05`, `SEC-04-T01`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-05-t01`
- Worktree: `../alon-ai-task-sec-05-t01`
- Acceptance evidence: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L107) — Test evidence: restore/startup/stale/concurrent/signal-failure matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-05-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 167 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `DB-03-T03`, `DB-03-T04`, `SEC-05-T01`

### I1 / R1 — `SEC-05-T02`

- Source: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L109)
- Dependencies: `SEC-05-T01`, `DB-03-T03`, `DB-03-T04`, `DB-03-T01`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-05-t02`
- Worktree: `../alon-ai-task-sec-05-t02`
- Acceptance evidence: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L109) — Test evidence: global/business/recipient create/deactivate/race, source-purge/list/replay stability and exact zero-call counts.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-05-T03`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 168 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-03-T02`, `SEC-05-T02`

### I1 / R1 — `SEC-05-T03`

- Source: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L111)
- Dependencies: `SEC-05-T02`, `OBS-03-T02`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-05-t03`
- Worktree: `../alon-ai-task-sec-05-t03`
- Acceptance evidence: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L111) — Test evidence: concurrency/replay/expiry/unknown-cost/overage.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 169 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T02`, `SEC-06-T01`

### I1 / R1 — `SEC-02-T01`

- Source: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1000)
- Dependencies: `DB-01-T02`, `SEC-06-T01`
- Mode: `serial`
- Locks: `security-runtime`, `migration-head`
- Branch: `agent/sec-02-t01`
- Worktree: `../alon-ai-task-sec-02-t01`
- Acceptance evidence: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1000) — Test evidence: catalog equality, role-denial, dump/restore, expiry/prune boundaries, and worker/product-role no-access fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-02-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 170 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `SEC-02-T01`

### I1 / R1 — `SEC-02-T02`

- Source: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1002)
- Dependencies: `SEC-02-T01`, `SEC-03-T01`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-02-t02`
- Worktree: `../alon-ai-task-sec-02-t02`
- Acceptance evidence: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1002) — Test evidence: exact success `{code,state,iss,scope?}` and error `{error,state,iss,error_description?}` arms; callback `iss=https://accounts.google.com` accepts while callback legacy/bogus/missing/duplicate issuer rejects; verified ID-token issuer accepts each of the separate two exact values and rejects every other value; state/nonce/PKCE/audience/subject/error/replay plus two-claimer/expired-lease/stale-version matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-02-T03`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 171 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-02-T02`

### I1 / R1 — `SEC-02-T03`

- Source: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1004)
- Dependencies: `SEC-02-T02`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-02-t03`
- Worktree: `../alon-ai-task-sec-02-t03`
- Acceptance evidence: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1004) — Test evidence: fixation, parallel rotation, prior-handle overlap, expiry, restart, logout, third-session eviction.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-02-T04`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 172 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T01`, `SEC-02-T03`

### I1 / R1 — `SEC-02-T04`

- Source: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1006)
- Dependencies: `SEC-02-T03`, `BACKEND-02-T01`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-02-t04`
- Worktree: `../alon-ai-task-sec-02-t04`
- Acceptance evidence: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1006) — Test evidence: cross-origin/XSS/enumeration/header-spoof suite.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T03`, `WF-06-T01`, `SEC-02-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 173 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `PROVIDER-07-T02`, `SEC-02-T04`

### I1 / R1 — `PROVIDER-07-T03`

- Source: [source](05-providers/07-calendar-provider.md#L60)
- Dependencies: `PROVIDER-07-T02`, `SEC-02-T04`, `SEC-03-T01`
- Mode: `serial`
- Locks: `provider-contracts`, `security-runtime`
- Branch: `agent/provider-07-t03`
- Worktree: `../alon-ai-task-provider-07-t03`
- Acceptance evidence: [source](05-providers/07-calendar-provider.md#L60) — Test evidence: wrong scope/calendar, revoked credential, bounds and safe telemetry tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-07-T04`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 174 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-07-T03`

### I1 / R1 — `PROVIDER-07-T04`

- Source: [source](05-providers/07-calendar-provider.md#L62)
- Dependencies: `PROVIDER-07-T03`
- Mode: `serial`
- Locks: `provider-contracts`, `calendar-side-effects`
- Branch: `agent/provider-07-t04`
- Worktree: `../alon-ai-task-provider-07-t04`
- Acceptance evidence: [source](05-providers/07-calendar-provider.md#L62) — Test evidence: fake HTTP/PostgreSQL crash matrix, zero duplicate events/notifications and no negative-read retry.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 175 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-05-T01`, `SEC-02-T04`

### I1 / R1 — `WF-06-T01`

- Source: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L85)
- Dependencies: `SEC-02-T04`, `BACKEND-05-T01`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-06-t01`
- Worktree: `../alon-ai-task-wf-06-t01`
- Acceptance evidence: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L85) — Test evidence: command replay, stale version, illegal state matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-06-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 176 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-06-T01`

### I1 / R1 — `WF-06-T02`

- Source: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L87)
- Dependencies: `WF-06-T01`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-06-t02`
- Worktree: `../alon-ai-task-wf-06-t02`
- Acceptance evidence: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L87) — Test evidence: kill/restart at request, signal, step, acknowledgement.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-06-T03`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 177 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-06-T02`

### I1 / R1 — `WF-06-T03`

- Source: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L89)
- Dependencies: `WF-06-T02`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-06-t03`
- Worktree: `../alon-ai-task-wf-06-t03`
- Acceptance evidence: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L89) — Test evidence: changed artifact/policy/suppression/gate and retry-exhaustion cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-02-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 178 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-02-T04`, `BACKEND-05-T01`, `WF-06-T03`

### I1 / R1 — `WF-02-T05`

- Source: [source](03-workflows/02-experiment-lifecycle.md#L57)
- Dependencies: `WF-02-T04`, `BACKEND-05-T01`, `WF-06-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/wf-02-t05`
- Worktree: `../alon-ai-task-wf-02-t05`
- Acceptance evidence: [source](03-workflows/02-experiment-lifecycle.md#L57) — Test evidence: pause/replay/ceiling/final-CONTINUE tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 179 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-02-T04`

### I1 / R1 — `SEC-02-T05`

- Source: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1008)
- Dependencies: `SEC-02-T04`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-02-t05`
- Worktree: `../alon-ai-task-sec-02-t05`
- Acceptance evidence: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1008) — Test evidence: stolen current/previous cookie and emergency-revoke propagation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-05-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 180 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `PROVIDER-01-T02`, `DB-03-T04`, `BACKEND-05-T01`, `SEC-02-T04`, `SEC-02-T05`

### I1 / R1 — `BACKEND-05-T02`

- Source: [source](06-backend/05-approval-and-command-handling.md#L120)
- Dependencies: `BACKEND-05-T01`, `SEC-02-T04`, `SEC-02-T05`, `SEC-03-T01`, `DB-03-T04`, `PROVIDER-01-T02`
- Mode: `serial`
- Locks: `backend-domain`, `security-runtime`
- Branch: `agent/backend-05-t02`
- Worktree: `../alon-ai-task-backend-05-t02`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L120) — Test evidence: cross-session/recipient/content/stale/replay/cache/telemetry negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-05-T03`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 181 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-03-T03`, `BACKEND-05-T02`

### I1 / R1 — `BACKEND-05-T03`

- Source: [source](06-backend/05-approval-and-command-handling.md#L122)
- Dependencies: `BACKEND-05-T02`, `BACKEND-03-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-05-t03`
- Worktree: `../alon-ai-task-backend-05-t03`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L122) — Test evidence: normal in-envelope action without operator preview, all one-field scope/expiry/generation splices, consumption race, commercial denial and stale reply tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-03-T04`, `BACKEND-05-T04`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 182 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-03-T03`, `SEC-05-T03`, `BACKEND-05-T03`

### I1 / R1 — `BACKEND-03-T04`

- Source: [source](06-backend/03-policy-engine.md#L127)
- Dependencies: `BACKEND-03-T03`, `SEC-05-T03`, `BACKEND-05-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-03-t04`
- Worktree: `../alon-ai-task-backend-03-t04`
- Acceptance evidence: [source](06-backend/03-policy-engine.md#L127) — Test evidence: mutable-fact matrix, concurrent slot/lease, suppression event/no-call, and independent facts-hash tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T08`, `BACKEND-04-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 183 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T04`, `PROVIDER-07-T02`, `BACKEND-03-T03`, `BACKEND-01-T07`, `BACKEND-05-T03`, `BACKEND-03-T04`

### I1 / R1 — `BACKEND-01-T08`

- Source: [source](06-backend/01-domain-services.md#L102)
- Dependencies: `BACKEND-01-T07`, `BACKEND-05-T03`, `BACKEND-03-T03`, `PROVIDER-07-T02`, `DB-03-T04`, `BACKEND-03-T04`
- Mode: `serial`
- Locks: `calendar-side-effects`, `backend-domain`
- Branch: `agent/backend-01-t08`
- Worktree: `../alon-ai-task-backend-01-t08`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L102) — Test evidence: no-purchase call, timezone/DST/expiry/ETag/notification, duplicate callback, scope splice and every crash/replay boundary.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T09`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 184 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-04-T04`, `AGENT-09-T04`, `BACKEND-01-T08`

### I1 / R1 — `BACKEND-01-T09`

- Source: [source](06-backend/01-domain-services.md#L104)
- Dependencies: `BACKEND-01-T08`, `DB-04-T04`, `AGENT-09-T04`
- Mode: `parallel`
- Locks: `backend-domain`, `agent-artifacts`
- Branch: `agent/backend-01-t09`
- Worktree: `../alon-ai-task-backend-01-t09`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L104) — Test evidence: all four exact stage tuples, terminal CONTINUE at 1000, missing/late/ambiguous/synthetic data, duplicate trigger and crash/CAS tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-01-T10`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 185 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-12-T04`, `AGENT-10-T06`, `BACKEND-01-T09`

### I1 / R1 — `BACKEND-01-T10`

- Source: [source](06-backend/01-domain-services.md#L106)
- Dependencies: `BACKEND-01-T09`, `AGENT-12-T04`, `AGENT-10-T06`
- Mode: `parallel`
- Locks: `backend-domain`, `agent-artifacts`
- Branch: `agent/backend-01-t10`
- Worktree: `../alon-ai-task-backend-01-t10`
- Acceptance evidence: [source](06-backend/01-domain-services.md#L106) — Test evidence: all-agent completeness, weak-evidence no-mutation, protected-bound violation, cross-campaign timing, future baseline, no mid-cohort mutation and rollback/history races.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 186 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-04-T01`, `SEC-05-T03`, `BACKEND-03-T04`

### I1 / R1 — `BACKEND-04-T02`

- Source: [source](06-backend/04-send-gateway.md#L75)
- Dependencies: `BACKEND-04-T01`, `BACKEND-03-T04`, `SEC-05-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-04-t02`
- Worktree: `../alon-ai-task-backend-04-t02`
- Acceptance evidence: [source](06-backend/04-send-gateway.md#L75) — Test evidence: stale/mutable-fact matrix, failure injection, concurrent lease/slot, suppression no-call, and one-field splice tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 187 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-05-T03`

### I1 / R1 — `BACKEND-05-T04`

- Source: [source](06-backend/05-approval-and-command-handling.md#L124)
- Dependencies: `BACKEND-05-T03`
- Mode: `parallel`
- Locks: `backend-domain`, `workflow-runtime`
- Branch: `agent/backend-05-t04`
- Worktree: `../alon-ai-task-backend-05-t04`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L124) — Test evidence: kill/restart at request/signal/ack boundaries.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-05-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 188 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T03`, `BACKEND-05-T04`

### I1 / R1 — `BACKEND-05-T05`

- Source: [source](06-backend/05-approval-and-command-handling.md#L126)
- Dependencies: `BACKEND-05-T04`, `DB-03-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-05-t05`
- Worktree: `../alon-ai-task-backend-05-t05`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L126) — Test evidence: zero/overflow/drift/subset/duplicate/cross-experiment/concurrent-qualification negatives and exact-set positive.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-05-T06`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 189 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T02`, `BACKEND-05-T05`

### I1 / R1 — `BACKEND-05-T06`

- Source: [source](06-backend/05-approval-and-command-handling.md#L128)
- Dependencies: `BACKEND-05-T05`, `SEC-05-T02`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-05-t06`
- Worktree: `../alon-ai-task-backend-05-t06`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L128) — Test evidence: missing/stale gate, ambiguity, suppression, and repair matrices.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 190 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T03`, `OBS-05-T01`

### I1 / R1 — `OBS-05-T02`

- Source: [source](09-observability-and-evaluation/05-incident-response.md#L163)
- Dependencies: `OBS-05-T01`, `PRODUCT-03-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/obs-05-t02`
- Worktree: `../alon-ai-task-obs-05-t02`
- Acceptance evidence: [source](09-observability-and-evaluation/05-incident-response.md#L163) — Test evidence: owned-inbox stop/revoke/reconcile, idempotent acknowledgement, evidence retention and no automatic enable; no claim of unavailable M8 restore/rollback completion.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 191 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T01`, `WF-01-T01`, `WF-00-T04`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`

### I1 / R1 — `LAUNCH-01-T01`

- Source: [source](12-launch-and-operations/01-test-inbox-pilot.md#L117)
- Dependencies: `PRODUCT-03-T01`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `WF-01-T01`, `WF-00-T04`
- Mode: `serial`
- Locks: `milestone-gate`, `live-environment`
- Branch: `agent/launch-01-t01`
- Worktree: `../alon-ai-task-launch-01-t01`
- Acceptance evidence: [source](12-launch-and-operations/01-test-inbox-pilot.md#L117) — Test evidence: stale prior gate, wrong target/alias, cap drift and missing signature reject before credential construction; attempted live pilot with this record is denied.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-01-T03`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 192 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `PROVIDER-01-T02`, `DB-03-T04`, `DB-05-T03`, `BACKEND-05-T01`, `SEC-02-T04`, `LAUNCH-01-T01`

### I1 / R1 — `PROVIDER-01-T03`

- Source: [source](05-providers/01-gmail-oauth-and-adapter.md#L154)
- Dependencies: `PROVIDER-01-T02`, `SEC-03-T01`, `SEC-02-T04`, `BACKEND-05-T01`, `DB-03-T04`, `DB-05-T03`, `LAUNCH-01-T01`
- Mode: `serial`
- Locks: `security-runtime`, `provider-contracts`, `database-schema`, `backend-domain`, `live-environment`
- Branch: `agent/provider-01-t03`
- Worktree: `../alon-ai-task-provider-01-t03`
- Acceptance evidence: [source](05-providers/01-gmail-oauth-and-adapter.md#L154) — Test evidence: executable six-point kill matrix, CAS replay/conflict, TTL/GC race, consistency-disable, and single-exchange proof.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-01-T04`, `SEC-03-T02`, `TEST-04-T03`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 193 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T03`

### I1 / R1 — `PROVIDER-01-T04`

- Source: [source](05-providers/01-gmail-oauth-and-adapter.md#L156)
- Dependencies: `PROVIDER-01-T03`
- Mode: `serial`
- Locks: `provider-contracts`, `gmail-side-effects`, `live-environment`
- Branch: `agent/provider-01-t04`
- Worktree: `../alon-ai-task-provider-01-t04`
- Acceptance evidence: [source](05-providers/01-gmail-oauth-and-adapter.md#L156) — Test evidence: `test_gmail_send_status_transport_and_malformed_success_matrix_has_no_hidden_retry`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-02-T04`, `BACKEND-04-T03`, `OBS-01-T02`, `TEST-02-T01`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 194 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T02`, `DB-01-T05`, `DB-05-T05`, `ARCH-02-T03`, `PROVIDER-01-T04`

### I1 / R1 — `ARCH-02-T04`

- Source: [source](01-architecture/02-module-boundaries.md#L120)
- Dependencies: `ARCH-02-T03`, `DB-01-T05`, `DB-05-T05`, `PROVIDER-01-T02`, `PROVIDER-01-T04`
- Mode: `serial`
- Locks: `architecture-contracts`, `provider-contracts`, `gmail-side-effects`, `calendar-side-effects`, `backend-domain`, `security-runtime`
- Branch: `agent/arch-02-t04`
- Worktree: `../alon-ai-task-arch-02-t04`
- Acceptance evidence: [source](01-architecture/02-module-boundaries.md#L120) — Test evidence: import graph plus mock and isolated inbox/calendar call-path proof.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 195 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-07-T04`, `BACKEND-04-T02`, `PROVIDER-01-T04`

### I1 / R1 — `BACKEND-04-T03`

- Source: [source](06-backend/04-send-gateway.md#L77)
- Dependencies: `BACKEND-04-T02`, `PROVIDER-01-T04`, `AGENT-07-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`, `backend-domain`
- Branch: `agent/backend-04-t03`
- Worktree: `../alon-ai-task-backend-04-t03`
- Acceptance evidence: [source](06-backend/04-send-gateway.md#L77) — Test evidence: provider status/exception/cancellation and crash matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-01-T05`, `PROVIDER-02-T02`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 196 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T04`, `BACKEND-04-T03`

### I1 / R1 — `PROVIDER-01-T05`

- Source: [source](05-providers/01-gmail-oauth-and-adapter.md#L158)
- Dependencies: `PROVIDER-01-T04`, `BACKEND-04-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `provider-contracts`
- Branch: `agent/provider-01-t05`
- Worktree: `../alon-ai-task-provider-01-t05`
- Acceptance evidence: [source](05-providers/01-gmail-oauth-and-adapter.md#L158) — Test evidence: `test_only_sendgateway_reaches_gmailprovider_send` and kill points before/after POST/result commit.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 197 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-03-T01`, `PROVIDER-02-T01`, `PROVIDER-01-T03`, `BACKEND-04-T03`

### I1 / R1 — `PROVIDER-02-T02`

- Source: [source](05-providers/02-gmail-history-sync.md#L92)
- Dependencies: `PROVIDER-02-T01`, `BACKEND-04-T03`, `DB-03-T01`, `PROVIDER-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `backend-domain`
- Branch: `agent/provider-02-t02`
- Worktree: `../alon-ai-task-provider-02-t02`
- Acceptance evidence: [source](05-providers/02-gmail-history-sync.md#L92) — Test evidence: `test_sent_reconciliation_zero_one_many_cross_mailbox_and_delayed_index_matrix`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T04`, `PROVIDER-02-T03`, `BACKEND-04-T04`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 198 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T03`, `DB-03-T04`, `PROVIDER-02-T02`

### I1 / R1 — `ARCH-03-T04`

- Source: [source](01-architecture/03-domain-events-and-state-machines.md#L394)
- Dependencies: `ARCH-03-T03`, `DB-03-T04`, `PROVIDER-02-T02`
- Mode: `serial`
- Locks: `architecture-contracts`, `gmail-side-effects`, `calendar-side-effects`, `backend-domain`, `security-runtime`
- Branch: `agent/arch-03-t04`
- Worktree: `../alon-ai-task-arch-03-t04`
- Acceptance evidence: [source](01-architecture/03-domain-events-and-state-machines.md#L394) — Test evidence: exhaustive crash matrix and provider-observation dedupe tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 199 — M6

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T01`, `OBS-01-T01`, `OBS-03-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T02`

### I1 / R1 — `PROVIDER-02-T03`

- Source: [source](05-providers/02-gmail-history-sync.md#L94)
- Dependencies: `PROVIDER-02-T02`
- Mode: `parallel`
- Locks: `provider-contracts`, `backend-domain`
- Branch: `agent/provider-02-t03`
- Worktree: `../alon-ai-task-provider-02-t03`
- Acceptance evidence: [source](05-providers/02-gmail-history-sync.md#L94) — Test evidence: crash injection before/after every row/event/cursor write.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `OBS-01-T02`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L112)
- Dependencies: `OBS-01-T01`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `OBS-03-T02`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-01-t02`
- Worktree: `../alon-ai-task-obs-01-t02`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L112) — Test evidence: happy/crash/replay/async/callback/public-unsubscribe E2E.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `PROVIDER-02-T04`, `OBS-01-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 200 — M6

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T03`, `OBS-01-T02`

### I1 / R1 — `PROVIDER-02-T04`

- Source: [source](05-providers/02-gmail-history-sync.md#L96)
- Dependencies: `PROVIDER-02-T03`
- Mode: `parallel`
- Locks: `provider-contracts`, `backend-domain`
- Branch: `agent/provider-02-t04`
- Worktree: `../alon-ai-task-provider-02-t04`
- Acceptance evidence: [source](05-providers/02-gmail-history-sync.md#L96) — Test evidence: concurrent incoming message, pagination, cancellation, cap, and restart fixtures.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `OBS-01-T03`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L114)
- Dependencies: `OBS-01-T02`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-01-t03`
- Worktree: `../alon-ai-task-obs-01-t03`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L114) — Test evidence: expected event/span count at every Gmail kill point and provider failure.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `SEC-05-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 201 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-04-T03`, `PROVIDER-02-T02`

### I1 / R1 — `BACKEND-04-T04`

- Source: [source](06-backend/04-send-gateway.md#L79)
- Dependencies: `BACKEND-04-T03`, `PROVIDER-02-T02`
- Mode: `serial`
- Locks: `gmail-side-effects`, `backend-domain`
- Branch: `agent/backend-04-t04`
- Worktree: `../alon-ai-task-backend-04-t04`
- Acceptance evidence: [source](06-backend/04-send-gateway.md#L79) — Test evidence: zero/one/many/delayed absence plus explicit-rejection/pre-write/exhaustion tests; every negative read proves zero queue transitions.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-03-T05`, `WF-06-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 202 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-01-T05`, `DB-03-T04`, `BACKEND-05-T03`, `BACKEND-04-T04`

### I1 / R1 — `DB-03-T05`

- Source: [source](02-database/03-leads-campaigns-and-messages.md#L262)
- Dependencies: `DB-03-T04`, `DB-01-T05`, `BACKEND-05-T03`, `BACKEND-04-T04`
- Mode: `serial`
- Locks: `database-schema`, `gmail-side-effects`, `backend-domain`, `security-runtime`
- Branch: `agent/db-03-t05`
- Worktree: `../alon-ai-task-db-03-t05`
- Acceptance evidence: [source](02-database/03-leads-campaigns-and-messages.md#L262) — Test evidence: kill point before/after each boundary.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-03-T06`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 203 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T01`, `PROVIDER-02-T03`, `DB-03-T05`

### I1 / R1 — `DB-03-T06`

- Source: [source](02-database/03-leads-campaigns-and-messages.md#L264)
- Dependencies: `DB-03-T05`, `PROVIDER-02-T01`, `PROVIDER-02-T03`
- Mode: `serial`
- Locks: `database-schema`, `gmail-side-effects`, `backend-domain`
- Branch: `agent/db-03-t06`
- Worktree: `../alon-ai-task-db-03-t06`
- Acceptance evidence: [source](02-database/03-leads-campaigns-and-messages.md#L264) — Test evidence: crash on every row/cursor boundary.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 204 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-07-T02`, `WF-06-T03`, `PROVIDER-02-T02`, `BACKEND-04-T04`

### I1 / R1 — `WF-06-T04`

- Source: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L91)
- Dependencies: `WF-06-T03`, `BACKEND-04-T04`, `PROVIDER-02-T02`, `PROVIDER-07-T02`
- Mode: `serial`
- Locks: `gmail-side-effects`, `calendar-side-effects`, `workflow-runtime`
- Branch: `agent/wf-06-t04`
- Worktree: `../alon-ai-task-wf-06-t04`
- Acceptance evidence: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L91) — Test evidence: cancel at every WF-05 network boundary plus zero/many/delayed-search non-escape.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 205 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `PROVIDER-01-T03`

### I1 / R1 — `SEC-03-T02`

- Source: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L95)
- Dependencies: `SEC-03-T01`, `PROVIDER-01-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-03-t02`
- Worktree: `../alon-ai-task-sec-03-t02`
- Acceptance evidence: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L95) — Test evidence: six kill points, three strong reads, handler/bind/GC CAS races, mismatch.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-03-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 206 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T02`

### I1 / R1 — `SEC-03-T03`

- Source: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L97)
- Dependencies: `SEC-03-T02`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-03-t03`
- Worktree: `../alon-ai-task-sec-03-t03`
- Acceptance evidence: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L97) — Test evidence: compromised agent/workflow/frontend/telemetry attempts.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-03-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 207 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T03`

### I1 / R1 — `SEC-03-T04`

- Source: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L99)
- Dependencies: `SEC-03-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-03-t04`
- Worktree: `../alon-ai-task-sec-03-t04`
- Acceptance evidence: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L99) — Test evidence: rotation/revocation cases plus wrong-key, missing-generation, tamper, custody, and tmpfs-cleanup negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 208 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T03`, `SEC-05-T03`, `BACKEND-04-T03`, `OBS-01-T03`

### I1 / R1 — `SEC-05-T04`

- Source: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L113)
- Dependencies: `SEC-05-T03`, `OBS-01-T03`, `BACKEND-04-T03`, `PRODUCT-03-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-05-t04`
- Worktree: `../alon-ai-task-sec-05-t04`
- Acceptance evidence: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L113) — Test evidence: inject each trigger and DB/signal failure.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-02-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 209 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T01`, `BACKEND-03-T03`, `BACKEND-02-T02`, `SEC-04-T03`, `SEC-02-T04`, `BACKEND-05-T02`, `BACKEND-01-T10`, `BACKEND-05-T06`, `PROVIDER-01-T04`, `BACKEND-04-T04`, `SEC-03-T02`, `SEC-05-T04`

### I1 / R1 — `BACKEND-02-T03`

- Source: [source](06-backend/02-api-contracts.md#L320)
- Dependencies: `BACKEND-02-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `BACKEND-03-T03`, `BACKEND-04-T04`, `BACKEND-05-T06`, `SEC-03-T02`, `SEC-04-T03`, `SEC-05-T04`, `SEC-02-T04`, `BACKEND-05-T02`, `BACKEND-01-T10`
- Mode: `serial`
- Locks: `openapi-contract`, `security-runtime`
- Branch: `agent/backend-02-t03`
- Worktree: `../alon-ai-task-backend-02-t03`
- Acceptance evidence: [source](06-backend/02-api-contracts.md#L320) — Test evidence: OAuth, command, authority, ambiguity, recovery, and status E2E cases under the isolated M6 profile.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 210 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-04-T02`, `DB-03-T04`, `DB-05-T03`, `PROVIDER-01-T03`

### I1 / R1 — `TEST-04-T03`

- Source: [source](10-testing/04-gmail-side-effect-tests.md#L76)
- Dependencies: `TEST-04-T02`, `PROVIDER-01-T03`, `DB-03-T04`, `DB-05-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/test-04-t03`
- Worktree: `../alon-ai-task-test-04-t03`
- Acceptance evidence: [source](10-testing/04-gmail-side-effect-tests.md#L76) — Test evidence: CAS generation, lease expiry, strong reads, ACTIVE proof and cleanup winner.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-04-T04`, `LAUNCH-01-T02`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 211 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T03`, `BACKEND-04-T04`, `TEST-04-T03`

### I1 / R1 — `TEST-04-T04`

- Source: [source](10-testing/04-gmail-side-effect-tests.md#L78)
- Dependencies: `TEST-04-T03`, `BACKEND-04-T04`, `SEC-05-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`
- Branch: `agent/test-04-t04`
- Worktree: `../alon-ai-task-test-04-t04`
- Acceptance evidence: [source](10-testing/04-gmail-side-effect-tests.md#L78) — Test evidence: one-field authority splices, 14 no-call denials, concurrency and cancellation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 212 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T02`, `PROVIDER-02-T01`, `TEST-01-T02`, `TEST-01-T03`, `DB-01-T01`, `AGENT-01-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `PROVIDER-01-T04`

### I1 / R1 — `TEST-02-T01`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L62)
- Dependencies: `DB-01-T01`, `AGENT-01-T01`, `PROVIDER-01-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `TEST-01-T03`, `TEST-01-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-02-t01`
- Worktree: `../alon-ai-task-test-02-t01`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L62) — Test evidence: exact-set/unknown/duplicate and target guard checks.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-02-T02`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 213 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-06-T01`, `SEC-06-T01`, `TEST-02-T01`

### I1 / R1 — `TEST-02-T02`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L64)
- Dependencies: `TEST-02-T01`, `DB-06-T01`, `SEC-06-T01`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-02-t02`
- Worktree: `../alon-ai-task-test-02-t02`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L64) — Test evidence: catalog, row/event/outbox/idempotency and call-spy equality.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-03-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 214 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-03-T03`, `ARCH-03-T01`, `WF-03-T05`, `WF-04-T05`, `WF-02-T05`, `TEST-02-T02`

### I1 / R1 — `TEST-03-T04`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L88)
- Dependencies: `TEST-03-T03`, `TEST-02-T02`, `ARCH-03-T01`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/test-03-t04`
- Worktree: `../alon-ai-task-test-03-t04`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L88) — Test evidence: legal/illegal transition and digest set equality.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-03-T05`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 215 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-06-T04`, `TEST-03-T04`

### I1 / R1 — `TEST-03-T05`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L90)
- Dependencies: `TEST-03-T04`, `WF-06-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`
- Branch: `agent/test-03-t05`
- Worktree: `../alon-ai-task-test-03-t05`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L90) — Test evidence: no post-bound call and no wrong-version replay.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 216 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-04-T01`, `TEST-04-T02`, `OBS-03-T02`, `BACKEND-01-T06`, `SEC-05-T02`, `LAUNCH-01-T01`, `PROVIDER-02-T04`, `BACKEND-04-T04`, `TEST-04-T03`

### I1 / R1 — `LAUNCH-01-T02`

- Source: [source](12-launch-and-operations/01-test-inbox-pilot.md#L119)
- Dependencies: `LAUNCH-01-T01`, `TEST-04-T01`, `TEST-04-T03`, `TEST-04-T02`, `BACKEND-04-T04`, `PROVIDER-02-T04`, `SEC-05-T02`, `OBS-03-T02`, `BACKEND-01-T06`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-01-t02`
- Worktree: `../alon-ai-task-launch-01-t02`
- Acceptance evidence: [source](12-launch-and-operations/01-test-inbox-pilot.md#L119) — Test evidence: exact recorded provider invocation/result and terminal/event/provider-spy counts; a local policy/pre-call denial cannot satisfy the row.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-01-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 217 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T01`, `WF-01-T01`, `WF-00-T04`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-01-T03`, `OBS-01-T03`, `SEC-05-T04`, `LAUNCH-01-T02`

### I1 / R1 — `LAUNCH-01-T03`

- Source: [source](12-launch-and-operations/01-test-inbox-pilot.md#L121)
- Dependencies: `LAUNCH-01-T02`, `PRODUCT-03-T01`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `WF-01-T01`, `WF-00-T04`, `PROVIDER-01-T03`, `SEC-05-T04`, `OBS-01-T03`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-01-t03`
- Worktree: `../alon-ai-task-launch-01-t03`
- Acceptance evidence: [source](12-launch-and-operations/01-test-inbox-pilot.md#L121) — Test evidence: stale/missing/cross-project/real-address/catalog/lane/cap/control/version negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PROVIDER-01-T06`, `PROVIDER-02-T05`, `WF-05-T01`, `LAUNCH-01-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 218 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T05`, `LAUNCH-01-T03`

### I1 / R1 — `PROVIDER-01-T06`

- Source: [source](05-providers/01-gmail-oauth-and-adapter.md#L160)
- Dependencies: `PROVIDER-01-T05`, `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `security-runtime`, `provider-contracts`, `live-environment`
- Branch: `agent/provider-01-t06`
- Worktree: `../alon-ai-task-provider-01-t06`
- Acceptance evidence: [source](05-providers/01-gmail-oauth-and-adapter.md#L160) — Test evidence: fixture byte/hash test, secret/PII scan, rotation/revocation recovery.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 219 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T04`, `LAUNCH-01-T03`

### I1 / R1 — `PROVIDER-02-T05`

- Source: [source](05-providers/02-gmail-history-sync.md#L98)
- Dependencies: `PROVIDER-02-T04`, `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`, `live-environment`
- Branch: `agent/provider-02-t05`
- Worktree: `../alon-ai-task-provider-02-t05`
- Acceptance evidence: [source](05-providers/02-gmail-history-sync.md#L98) — Test evidence: fixture hashes and end-to-end reply/reconciliation traces.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-04-T05`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 220 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-03-T03`, `WF-00-T04`, `AGENT-08-T04`, `SEC-05-T03`, `SEC-02-T04`, `BACKEND-05-T06`, `PROVIDER-01-T03`, `BACKEND-04-T04`, `LAUNCH-01-T03`

### I1 / R1 — `WF-05-T01`

- Source: [source](03-workflows/05-outreach-and-reply-workflow.md#L61)
- Dependencies: `TEST-03-T03`, `SEC-05-T03`, `BACKEND-05-T06`, `PROVIDER-01-T03`, `SEC-02-T04`, `LAUNCH-01-T03`, `WF-00-T04`, `AGENT-08-T04`, `BACKEND-04-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`, `workflow-runtime`, `live-environment`
- Branch: `agent/wf-05-t01`
- Worktree: `../alon-ai-task-wf-05-t01`
- Acceptance evidence: [source](03-workflows/05-outreach-and-reply-workflow.md#L61) — Test evidence: real recipient, missing evidence and stale control denials.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-05-T02`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 221 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-07-T04`, `WF-04-T04`, `BACKEND-05-T03`, `WF-05-T01`

### I1 / R1 — `WF-05-T02`

- Source: [source](03-workflows/05-outreach-and-reply-workflow.md#L63)
- Dependencies: `WF-05-T01`, `BACKEND-05-T03`, `WF-04-T04`, `AGENT-07-T04`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-05-t02`
- Worktree: `../alon-ai-task-wf-05-t02`
- Acceptance evidence: [source](03-workflows/05-outreach-and-reply-workflow.md#L63) — Test evidence: content/phase/thread/offer splice and no per-message approval path.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-05-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 222 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T03`, `BACKEND-04-T04`, `WF-05-T02`

### I1 / R1 — `WF-05-T03`

- Source: [source](03-workflows/05-outreach-and-reply-workflow.md#L65)
- Dependencies: `WF-05-T02`, `SEC-05-T03`, `BACKEND-04-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`, `workflow-runtime`, `live-environment`
- Branch: `agent/wf-05-t03`
- Worktree: `../alon-ai-task-wf-05-t03`
- Acceptance evidence: [source](03-workflows/05-outreach-and-reply-workflow.md#L65) — Test evidence: kill matrix, negative-search quarantine and retry exhaustion.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-05-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 223 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-08-T04`, `SEC-05-T02`, `PROVIDER-02-T04`, `WF-05-T03`

### I1 / R1 — `WF-05-T04`

- Source: [source](03-workflows/05-outreach-and-reply-workflow.md#L67)
- Dependencies: `WF-05-T03`, `PROVIDER-02-T04`, `AGENT-08-T04`, `SEC-05-T02`
- Mode: `serial`
- Locks: `gmail-side-effects`, `workflow-runtime`
- Branch: `agent/wf-05-t04`
- Worktree: `../alon-ai-task-wf-05-t04`
- Acceptance evidence: [source](03-workflows/05-outreach-and-reply-workflow.md#L67) — Test evidence: positive response, objection/rejection, budget/floor/terminal limits and stale response races.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-07-T01`, `WF-08-T01`, `TEST-04-T05`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 224 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `PROVIDER-07-T02`, `BACKEND-01-T08`, `WF-05-T04`

### I1 / R1 — `WF-07-T01`

- Source: [source](03-workflows/07-booking-workflow.md#L49)
- Dependencies: `WF-05-T04`, `PROVIDER-07-T02`, `ARCH-03-T01`, `BACKEND-01-T08`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-07-t01`
- Worktree: `../alon-ai-task-wf-07-t01`
- Acceptance evidence: [source](03-workflows/07-booking-workflow.md#L49) — Test evidence: call without purchase succeeds; no qualification/agreement fails.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-07-T02`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 225 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-07-T03`, `WF-07-T01`

### I1 / R1 — `WF-07-T02`

- Source: [source](03-workflows/07-booking-workflow.md#L51)
- Dependencies: `WF-07-T01`, `PROVIDER-07-T03`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-07-t02`
- Worktree: `../alon-ai-task-wf-07-t02`
- Acceptance evidence: [source](03-workflows/07-booking-workflow.md#L51) — Test evidence: timezone/DST/ambiguous agreement/stale availability tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-07-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 226 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-07-T04`, `WF-07-T02`

### I1 / R1 — `WF-07-T03`

- Source: [source](03-workflows/07-booking-workflow.md#L53)
- Dependencies: `WF-07-T02`, `PROVIDER-07-T04`
- Mode: `serial`
- Locks: `calendar-side-effects`, `workflow-runtime`
- Branch: `agent/wf-07-t03`
- Worktree: `../alon-ai-task-wf-07-t03`
- Acceptance evidence: [source](03-workflows/07-booking-workflow.md#L53) — Test evidence: crash every boundary, duplicate callback, notification and ETag conflict.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-07-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 227 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-01-T03`, `WF-07-T03`

### I1 / R1 — `WF-07-T04`

- Source: [source](03-workflows/07-booking-workflow.md#L55)
- Dependencies: `WF-07-T03`, `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `calendar-side-effects`, `workflow-runtime`, `milestone-gate`, `live-environment`
- Branch: `agent/wf-07-t04`
- Worktree: `../alon-ai-task-wf-07-t04`
- Acceptance evidence: [source](03-workflows/07-booking-workflow.md#L55) — Test evidence: one event/change per action with exact timezone and no real demand claim.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 228 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `AGENT-09-T04`, `BACKEND-01-T09`, `WF-05-T04`

### I1 / R1 — `WF-08-T01`

- Source: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L47)
- Dependencies: `WF-05-T04`, `AGENT-09-T04`, `ARCH-03-T01`, `BACKEND-01-T09`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-08-t01`
- Worktree: `../alon-ai-task-wf-08-t01`
- Acceptance evidence: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L47) — Test evidence: unknown ordinal, duplicate closure and incomplete outcome cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-08-T02`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 229 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-08-T01`

### I1 / R1 — `WF-08-T02`

- Source: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L49)
- Dependencies: `WF-08-T01`
- Mode: `parallel`
- Locks: `workflow-runtime`, `agent-artifacts`
- Branch: `agent/wf-08-t02`
- Worktree: `../alon-ai-task-wf-08-t02`
- Acceptance evidence: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L49) — Test evidence: late observation, hash splice, missing cost and denominator cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-08-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 230 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-08-T02`

### I1 / R1 — `WF-08-T03`

- Source: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L51)
- Dependencies: `WF-08-T02`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-08-t03`
- Worktree: `../alon-ai-task-wf-08-t03`
- Acceptance evidence: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L51) — Test evidence: only CONTINUE advances, terminal 1,000 ceiling and replay uniqueness.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-08-T04`, `WF-09-T01`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 231 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-08-T03`

### I1 / R1 — `WF-08-T04`

- Source: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L53)
- Dependencies: `WF-08-T03`
- Mode: `serial`
- Locks: `workflow-runtime`, `milestone-gate`
- Branch: `agent/wf-08-t04`
- Worktree: `../alon-ai-task-wf-08-t04`
- Acceptance evidence: [source](03-workflows/08-checkpoint-evaluation-workflow.md#L53) — Test evidence: no fifth cohort, lost trigger, mutable evidence or double decision.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 232 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `AGENT-12-T04`, `AGENT-10-T06`, `BACKEND-01-T10`, `WF-08-T03`

### I1 / R1 — `WF-09-T01`

- Source: [source](03-workflows/09-global-learning-workflow.md#L50)
- Dependencies: `WF-08-T03`, `AGENT-12-T04`, `AGENT-10-T06`, `ARCH-03-T01`, `BACKEND-01-T10`
- Mode: `parallel`
- Locks: `workflow-runtime`, `agent-artifacts`
- Branch: `agent/wf-09-t01`
- Worktree: `../alon-ai-task-wf-09-t01`
- Acceptance evidence: [source](03-workflows/09-global-learning-workflow.md#L50) — Test evidence: open checkpoint, duplicate trigger, missing agent and invalid evidence denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-09-T02`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 233 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-09-T01`

### I1 / R1 — `WF-09-T02`

- Source: [source](03-workflows/09-global-learning-workflow.md#L52)
- Dependencies: `WF-09-T01`
- Mode: `parallel`
- Locks: `workflow-runtime`, `agent-artifacts`
- Branch: `agent/wf-09-t02`
- Worktree: `../alon-ai-task-wf-09-t02`
- Acceptance evidence: [source](03-workflows/09-global-learning-workflow.md#L52) — Test evidence: weak evidence, unsafe mutation and self-certified promotion failures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-09-T03`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 234 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-09-T02`

### I1 / R1 — `WF-09-T03`

- Source: [source](03-workflows/09-global-learning-workflow.md#L54)
- Dependencies: `WF-09-T02`
- Mode: `parallel`
- Locks: `workflow-runtime`, `backend-domain`
- Branch: `agent/wf-09-t03`
- Worktree: `../alon-ai-task-wf-09-t03`
- Acceptance evidence: [source](03-workflows/09-global-learning-workflow.md#L54) — Test evidence: mid-cohort race, cross-campaign timing, future initialization and rollback compatibility.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-09-T04`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 235 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-09-T03`

### I1 / R1 — `WF-09-T04`

- Source: [source](03-workflows/09-global-learning-workflow.md#L56)
- Dependencies: `WF-09-T03`
- Mode: `serial`
- Locks: `workflow-runtime`, `milestone-gate`
- Branch: `agent/wf-09-t04`
- Worktree: `../alon-ai-task-wf-09-t04`
- Acceptance evidence: [source](03-workflows/09-global-learning-workflow.md#L56) — Test evidence: no lost result, duplicate promotion, fifth result or historical mutation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 236 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-03-T03`, `WF-00-T04`, `BACKEND-03-T03`, `BACKEND-05-T06`, `BACKEND-04-T04`, `SEC-05-T04`, `LAUNCH-01-T03`, `PROVIDER-01-T06`, `PROVIDER-02-T05`

### I1 / R1 — `BACKEND-04-T05`

- Source: [source](06-backend/04-send-gateway.md#L81)
- Dependencies: `BACKEND-04-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `SEC-05-T04`, `TEST-03-T03`, `BACKEND-03-T03`, `BACKEND-05-T06`, `WF-00-T04`, `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`, `live-environment`
- Branch: `agent/backend-04-t05`
- Worktree: `../alon-ai-task-backend-04-t05`
- Acceptance evidence: [source](06-backend/04-send-gateway.md#L81) — Test evidence: the current M6 gateway suite plus table-writer, handler, import/call, and real-service spies.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-05-T05`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 237 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-06-T04`, `SEC-05-T04`, `LAUNCH-01-T03`, `WF-05-T04`, `BACKEND-04-T05`

### I1 / R1 — `WF-05-T05`

- Source: [source](03-workflows/05-outreach-and-reply-workflow.md#L69)
- Dependencies: `WF-05-T04`, `BACKEND-04-T05`, `SEC-05-T04`, `WF-06-T04`, `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`, `live-environment`
- Branch: `agent/wf-05-t05`
- Worktree: `../alon-ai-task-wf-05-t05`
- Acceptance evidence: [source](03-workflows/05-outreach-and-reply-workflow.md#L69) — Test evidence: no lost reply, repeated round, duplicate send or premature terminal effect.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 238 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T04`, `TEST-04-T04`, `WF-05-T04`

### I1 / R1 — `TEST-04-T05`

- Source: [source](10-testing/04-gmail-side-effect-tests.md#L80)
- Dependencies: `TEST-04-T04`, `PROVIDER-02-T04`, `WF-05-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`
- Branch: `agent/test-04-t05`
- Worktree: `../alon-ai-task-test-04-t05`
- Acceptance evidence: [source](10-testing/04-gmail-side-effect-tests.md#L80) — Test evidence: zero/one/many/cross-account and every write-boundary crash.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-04-T06`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 239 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T04`, `LAUNCH-01-T03`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `BACKEND-04-T05`, `WF-05-T05`, `TEST-04-T05`

### I1 / R1 — `TEST-04-T06`

- Source: [source](10-testing/04-gmail-side-effect-tests.md#L82)
- Dependencies: `TEST-04-T05`, `WF-05-T05`, `BACKEND-04-T05`, `SEC-05-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`, `test-command-registry`, `live-environment`
- Branch: `agent/test-04-t06`
- Worktree: `../alon-ai-task-test-04-t06`
- Acceptance evidence: [source](10-testing/04-gmail-side-effect-tests.md#L82) — Test evidence: zero duplicates/blind retries/post-control calls plus complete Gmail and command-mapping assertions.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-05-T06`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 240 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `WF-05-T05`, `TEST-04-T06`

### I1 / R1 — `WF-05-T06`

- Source: [source](03-workflows/05-outreach-and-reply-workflow.md#L71)
- Dependencies: `WF-05-T05`, `TEST-04-T06`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/wf-05-t06`
- Worktree: `../alon-ai-task-wf-05-t06`
- Acceptance evidence: [source](03-workflows/05-outreach-and-reply-workflow.md#L71) — Test evidence: end-to-end finite campaign simulation; no real demand claim.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 241 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-01-T03`

### I1 / R1 — `LAUNCH-01-T04`

- Source: [source](12-launch-and-operations/01-test-inbox-pilot.md#L123)
- Dependencies: `LAUNCH-01-T03`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`, `live-environment`
- Branch: `agent/launch-01-t04`
- Worktree: `../alon-ai-task-launch-01-t04`
- Acceptance evidence: [source](12-launch-and-operations/01-test-inbox-pilot.md#L123) — Test evidence: scenario set/order equality, each row's terminal outcome, duplicate replay, accepted-result crash, timeout/unknown reconciliation, cursor restart, atomic concurrent winner/loser, stored-denial replay and rolling-window admission.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-01-T05`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 242 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-01-T04`

### I1 / R1 — `LAUNCH-01-T05`

- Source: [source](12-launch-and-operations/01-test-inbox-pilot.md#L125)
- Dependencies: `LAUNCH-01-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`, `live-environment`
- Branch: `agent/launch-01-t05`
- Worktree: `../alon-ai-task-launch-01-t05`
- Acceptance evidence: [source](12-launch-and-operations/01-test-inbox-pilot.md#L125) — Test evidence: reply, opt-out, hard/soft-bounce-limit, crash and replay cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-01-T06`, `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 243 — M6

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-01-T05`

### I1 / R1 — `LAUNCH-01-T06`

- Source: [source](12-launch-and-operations/01-test-inbox-pilot.md#L127)
- Dependencies: `LAUNCH-01-T05`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-01-t06`
- Worktree: `../alon-ai-task-launch-01-t06`
- Acceptance evidence: [source](12-launch-and-operations/01-test-inbox-pilot.md#L127) — Test evidence: missing transcript, open lease, unresolved attempt, active control or stale credential rejects.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-03-T05`, `BACKEND-06-T01`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 244 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T04`

### I1 / R1 — `ARCH-03-T05`

- Source: [source](01-architecture/03-domain-events-and-state-machines.md#L396)
- Dependencies: `ARCH-03-T04`
- Mode: `serial`
- Locks: `architecture-contracts`, `openapi-contract`, `frontend-client`
- Branch: `agent/arch-03-t05`
- Worktree: `../alon-ai-task-arch-03-t05`
- Acceptance evidence: [source](01-architecture/03-domain-events-and-state-machines.md#L396) — Test evidence: backend enum schema tests, generated drift test, frontend exhaustive-state and E2E recovery tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 245 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-03-T01`, `DB-05-T02`, `BACKEND-03-T01`, `SEC-04-T02`, `OBS-05-T01`

### I1 / R1 — `BACKEND-06-T01`

- Source: [source](06-backend/06-reporting-and-query-services.md#L124)
- Dependencies: `BACKEND-03-T01`, `SEC-04-T02`, `DB-05-T02`, `ARCH-03-T01`, `OBS-05-T01`
- Mode: `serial`
- Locks: `openapi-contract`, `backend-domain`
- Branch: `agent/backend-06-t01`
- Worktree: `../alon-ai-task-backend-06-t01`
- Acceptance evidence: [source](06-backend/06-reporting-and-query-services.md#L124) — Test evidence: schema snapshots, every final-SEND denial fixture, and every incident/catalog fixture.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-02-T04`, `BACKEND-06-T02`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 246 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-02-T04`, `BACKEND-02-T03`, `BACKEND-06-T01`

### I1 / R1 — `BACKEND-02-T04`

- Source: [source](06-backend/02-api-contracts.md#L322)
- Dependencies: `BACKEND-02-T03`, `SEC-02-T04`, `BACKEND-06-T01`
- Mode: `serial`
- Locks: `openapi-contract`, `security-runtime`
- Branch: `agent/backend-02-t04`
- Worktree: `../alon-ai-task-backend-02-t04`
- Acceptance evidence: [source](06-backend/02-api-contracts.md#L322) — Test evidence: schema, scope, session, Origin/CSRF, pagination, cursor, error, redaction, and zero-route-implementation tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 247 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-06-T01`

### I1 / R1 — `BACKEND-06-T02`

- Source: [source](06-backend/06-reporting-and-query-services.md#L126)
- Dependencies: `BACKEND-06-T01`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-06-t02`
- Worktree: `../alon-ai-task-backend-06-t02`
- Acceptance evidence: [source](06-backend/06-reporting-and-query-services.md#L126) — Test evidence: real-PostgreSQL boundary/duplicate/ambiguous/suppression/recovery fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T03`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 248 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-03-T03`, `BACKEND-06-T02`

### I1 / R1 — `BACKEND-06-T03`

- Source: [source](06-backend/06-reporting-and-query-services.md#L128)
- Dependencies: `BACKEND-06-T02`, `OBS-03-T03`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-06-t03`
- Worktree: `../alon-ai-task-backend-06-t03`
- Acceptance evidence: [source](06-backend/06-reporting-and-query-services.md#L128) — Test evidence: currency/rounding/duplicate/missing-FX/provider parity fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-06-T04`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 249 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T04`, `BACKEND-06-T03`

### I1 / R1 — `BACKEND-06-T04`

- Source: [source](06-backend/06-reporting-and-query-services.md#L130)
- Dependencies: `BACKEND-06-T03`, `BACKEND-02-T04`
- Mode: `serial`
- Locks: `openapi-contract`, `backend-domain`
- Branch: `agent/backend-06-t04`
- Worktree: `../alon-ai-task-backend-06-t04`
- Acceptance evidence: [source](06-backend/06-reporting-and-query-services.md#L130) — Test evidence: concurrent commits cannot alter report/page, snapshot expiry/restart, serialization retry, cursor tamper, page continuity, and OpenAPI tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `BACKEND-02-T05`, `BACKEND-03-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 250 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T04`, `BACKEND-06-T04`

### I1 / R1 — `BACKEND-02-T05`

- Source: [source](06-backend/02-api-contracts.md#L324)
- Dependencies: `BACKEND-02-T04`, `BACKEND-06-T04`
- Mode: `serial`
- Locks: `openapi-contract`, `frontend-client`
- Branch: `agent/backend-02-t05`
- Worktree: `../alon-ai-task-backend-02-t05`
- Acceptance evidence: [source](06-backend/02-api-contracts.md#L324) — Test evidence: generated drift, route/status uniqueness, authentication binding, private-only deployment, and disabled-public synthetic edge tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-02-T05`, `BACKEND-05-T07`, `OBS-01-T04`, `FRONTEND-01-T05`, `FRONTEND-04-T01`, `FRONTEND-05-T01`, `FRONTEND-06-T01`, `FRONTEND-07-T01`, `FRONTEND-08-T01`, `FRONTEND-09-T01`, `BACKEND-06-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 251 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-02-T04`, `BACKEND-02-T05`

### I1 / R1 — `ARCH-02-T05`

- Source: [source](01-architecture/02-module-boundaries.md#L122)
- Dependencies: `ARCH-02-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `architecture-contracts`, `openapi-contract`, `frontend-client`
- Branch: `agent/arch-02-t05`
- Worktree: `../alon-ai-task-arch-02-t05`
- Acceptance evidence: [source](01-architecture/02-module-boundaries.md#L122) — Test evidence: generation drift, contract, and E2E tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 252 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-03-T04`, `BACKEND-06-T02`, `BACKEND-06-T04`

### I1 / R1 — `BACKEND-03-T05`

- Source: [source](06-backend/03-policy-engine.md#L129)
- Dependencies: `BACKEND-03-T04`, `BACKEND-06-T02`, `BACKEND-06-T04`
- Mode: `parallel`
- Locks: `backend-domain`
- Branch: `agent/backend-03-t05`
- Worktree: `../alon-ai-task-backend-03-t05`
- Acceptance evidence: [source](06-backend/03-policy-engine.md#L129) — Test evidence: golden decision replay and redaction scan.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 253 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `BACKEND-05-T06`, `PROVIDER-01-T03`, `BACKEND-02-T03`, `BACKEND-02-T05`

### I1 / R1 — `BACKEND-05-T07`

- Source: [source](06-backend/05-approval-and-command-handling.md#L130)
- Dependencies: `BACKEND-05-T06`, `SEC-03-T01`, `PROVIDER-01-T03`, `BACKEND-02-T03`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `openapi-contract`, `milestone-gate`
- Branch: `agent/backend-05-t07`
- Worktree: `../alon-ai-task-backend-05-t07`
- Acceptance evidence: [source](06-backend/05-approval-and-command-handling.md#L130) — Test evidence: executable state-machine, browser replay, DB proof tuple, TTL/GC, incident fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 254 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-02-T04`, `OBS-01-T03`, `BACKEND-02-T05`

### I1 / R1 — `OBS-01-T04`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L116)
- Dependencies: `OBS-01-T03`, `SEC-02-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `telemetry-catalog`, `security-runtime`
- Branch: `agent/obs-01-t04`
- Worktree: `../alon-ai-task-obs-01-t04`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L116) — Test evidence: session/command/query/report/incident traces, missing-ID rejection, no sensitive fields and fake-to-real boundary tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 255 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-03-T01`, `SEC-02-T04`, `SEC-02-T05`, `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-01-T05`

- Source: [source](07-frontend/01-information-architecture.md#L46)
- Dependencies: `FRONTEND-01-T04`, `BACKEND-02-T05`, `SEC-02-T04`, `SEC-02-T05`, `FRONTEND-02-T04`, `FRONTEND-03-T01`
- Mode: `serial`
- Locks: `frontend-client`, `security-runtime`
- Branch: `agent/frontend-01-t05`
- Worktree: `../alon-ai-task-frontend-01-t05`
- Acceptance evidence: [source](07-frontend/01-information-architecture.md#L46) — Test evidence: full route/operation coverage and API bypass-denial browser evidence.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-03-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 256 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-03-T02`, `WF-06-T03`, `BACKEND-05-T04`, `BACKEND-06-T04`, `BACKEND-02-T05`, `FRONTEND-01-T05`

### I1 / R1 — `FRONTEND-03-T03`

- Source: [source](07-frontend/03-experiment-control-center.md#L32)
- Dependencies: `FRONTEND-03-T02`, `FRONTEND-01-T05`, `BACKEND-02-T05`, `BACKEND-06-T04`, `BACKEND-05-T04`, `WF-06-T03`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-03-t03`
- Worktree: `../alon-ai-task-frontend-03-t03`
- Acceptance evidence: [source](07-frontend/03-experiment-control-center.md#L32) — Test evidence: cold-reply races and server-only eligibility tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-03-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 257 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T09`, `WF-08-T04`, `FRONTEND-03-T03`

### I1 / R1 — `FRONTEND-03-T04`

- Source: [source](07-frontend/03-experiment-control-center.md#L34)
- Dependencies: `FRONTEND-03-T03`, `BACKEND-01-T09`, `WF-08-T04`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-03-t04`
- Worktree: `../alon-ai-task-frontend-03-t04`
- Acceptance evidence: [source](07-frontend/03-experiment-control-center.md#L34) — Test evidence: weak evidence, late evidence and terminal 1,000 cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-03-T05`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 258 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T10`, `WF-09-T04`, `BACKEND-06-T04`, `BACKEND-02-T05`, `FRONTEND-03-T04`

### I1 / R1 — `FRONTEND-03-T05`

- Source: [source](07-frontend/03-experiment-control-center.md#L36)
- Dependencies: `FRONTEND-03-T04`, `BACKEND-06-T04`, `BACKEND-02-T05`, `BACKEND-01-T10`, `WF-09-T04`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-03-t05`
- Worktree: `../alon-ai-task-frontend-03-t05`
- Acceptance evidence: [source](07-frontend/03-experiment-control-center.md#L36) — Test evidence: cross-campaign activation timing and no mid-cohort mutation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 259 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-04-T01`

- Source: [source](07-frontend/04-evidence-and-agent-artifacts.md#L28)
- Dependencies: `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-04-t01`
- Worktree: `../alon-ai-task-frontend-04-t01`
- Acceptance evidence: [source](07-frontend/04-evidence-and-agent-artifacts.md#L28) — Test evidence: exact name set and unknown schema fallback tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-04-T02`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 260 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-06-T04`, `FRONTEND-04-T01`

### I1 / R1 — `FRONTEND-04-T02`

- Source: [source](07-frontend/04-evidence-and-agent-artifacts.md#L30)
- Dependencies: `FRONTEND-04-T01`, `BACKEND-06-T04`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-04-t02`
- Worktree: `../alon-ai-task-frontend-04-t02`
- Acceptance evidence: [source](07-frontend/04-evidence-and-agent-artifacts.md#L30) — Test evidence: hash splice, stale acceptance and missing phase fail visibly.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-04-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 261 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `FRONTEND-04-T02`

### I1 / R1 — `FRONTEND-04-T03`

- Source: [source](07-frontend/04-evidence-and-agent-artifacts.md#L32)
- Dependencies: `FRONTEND-04-T02`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-04-t03`
- Worktree: `../alon-ai-task-frontend-04-t03`
- Acceptance evidence: [source](07-frontend/04-evidence-and-agent-artifacts.md#L32) — Test evidence: invented identity/claims, inference-as-fact and unsafe markup tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-04-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 262 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `FRONTEND-04-T03`

### I1 / R1 — `FRONTEND-04-T04`

- Source: [source](07-frontend/04-evidence-and-agent-artifacts.md#L34)
- Dependencies: `FRONTEND-04-T03`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-04-t04`
- Worktree: `../alon-ai-task-frontend-04-t04`
- Acceptance evidence: [source](07-frontend/04-evidence-and-agent-artifacts.md#L34) — Test evidence: no protected holdout payload, raw PII or mutable cohort evidence.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 263 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T02`, `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-05-T01`

- Source: [source](07-frontend/05-lead-and-campaign-management.md#L28)
- Dependencies: `BACKEND-02-T05`, `BACKEND-02-T02`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-05-t01`
- Worktree: `../alon-ai-task-frontend-05-t01`
- Acceptance evidence: [source](07-frontend/05-lead-and-campaign-management.md#L28) — Test evidence: unknown adapter, unsupported social source and invented linkage cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-05-T02`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 264 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T07`, `FRONTEND-05-T01`

### I1 / R1 — `FRONTEND-05-T02`

- Source: [source](07-frontend/05-lead-and-campaign-management.md#L30)
- Dependencies: `FRONTEND-05-T01`, `BACKEND-01-T07`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-05-t02`
- Worktree: `../alon-ai-task-frontend-05-t02`
- Acceptance evidence: [source](07-frontend/05-lead-and-campaign-management.md#L30) — Test evidence: no deep research before preliminary pass; no send before final pass.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-05-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 265 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-05-T06`, `FRONTEND-05-T02`

### I1 / R1 — `FRONTEND-05-T03`

- Source: [source](07-frontend/05-lead-and-campaign-management.md#L32)
- Dependencies: `FRONTEND-05-T02`, `BACKEND-05-T06`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-05-t03`
- Worktree: `../alon-ai-task-frontend-05-t03`
- Acceptance evidence: [source](07-frontend/05-lead-and-campaign-management.md#L32) — Test evidence: client-selected additions, stale snapshot, duplicate identity and cap races deny.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-05-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 266 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `FRONTEND-05-T03`

### I1 / R1 — `FRONTEND-05-T04`

- Source: [source](07-frontend/05-lead-and-campaign-management.md#L34)
- Dependencies: `FRONTEND-05-T03`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-05-t04`
- Worktree: `../alon-ai-task-frontend-05-t04`
- Acceptance evidence: [source](07-frontend/05-lead-and-campaign-management.md#L34) — Test evidence: stale generation, stop races and browser bypass evidence.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-05-T05`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 267 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `FRONTEND-05-T04`

### I1 / R1 — `FRONTEND-05-T05`

- Source: [source](07-frontend/05-lead-and-campaign-management.md#L36)
- Dependencies: `FRONTEND-05-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-05-t05`
- Worktree: `../alon-ai-task-frontend-05-t05`
- Acceptance evidence: [source](07-frontend/05-lead-and-campaign-management.md#L36) — Test evidence: stable pagination, dedupe, cross-campaign activation and unavailable-data cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 268 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-06-T01`

- Source: [source](07-frontend/06-approval-inbox.md#L28)
- Dependencies: `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-06-t01`
- Worktree: `../alon-ai-task-frontend-06-t01`
- Acceptance evidence: [source](07-frontend/06-approval-inbox.md#L28) — Test evidence: pagination, stale generation and severity routing tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-06-T02`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 269 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-02-T04`, `BACKEND-02-T05`, `FRONTEND-06-T01`

### I1 / R1 — `FRONTEND-06-T02`

- Source: [source](07-frontend/06-approval-inbox.md#L30)
- Dependencies: `FRONTEND-06-T01`, `SEC-02-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-06-t02`
- Worktree: `../alon-ai-task-frontend-06-t02`
- Acceptance evidence: [source](07-frontend/06-approval-inbox.md#L30) — Test evidence: auth/CSRF/purpose/expiry/cache/logging denial tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-06-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 270 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-06-T02`

### I1 / R1 — `FRONTEND-06-T03`

- Source: [source](07-frontend/06-approval-inbox.md#L32)
- Dependencies: `FRONTEND-06-T02`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-06-t03`
- Worktree: `../alon-ai-task-frontend-06-t03`
- Acceptance evidence: [source](07-frontend/06-approval-inbox.md#L32) — Test evidence: cannot waive suppression/economics/caps or create action authority.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-06-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 271 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-06-T03`

### I1 / R1 — `FRONTEND-06-T04`

- Source: [source](07-frontend/06-approval-inbox.md#L34)
- Dependencies: `FRONTEND-06-T03`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-06-t04`
- Worktree: `../alon-ai-task-frontend-06-t04`
- Acceptance evidence: [source](07-frontend/06-approval-inbox.md#L34) — Test evidence: ambiguous outcomes remain quarantined and resolving never resumes automatically.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 272 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-07-T01`

- Source: [source](07-frontend/07-message-and-reply-timeline.md#L30)
- Dependencies: `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-07-t01`
- Worktree: `../alon-ai-task-frontend-07-t01`
- Acceptance evidence: [source](07-frontend/07-message-and-reply-timeline.md#L30) — Test evidence: pagination never drops intervening messages; unavailable bodies remain explicit.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-07-T02`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 273 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `FRONTEND-07-T01`

### I1 / R1 — `FRONTEND-07-T02`

- Source: [source](07-frontend/07-message-and-reply-timeline.md#L32)
- Dependencies: `FRONTEND-07-T01`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-07-t02`
- Worktree: `../alon-ai-task-frontend-07-t02`
- Acceptance evidence: [source](07-frontend/07-message-and-reply-timeline.md#L32) — Test evidence: STATED/INFERRED/UNKNOWN, rejection and unsupported-claim cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-07-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 274 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-05-T03`, `BACKEND-02-T05`, `FRONTEND-07-T02`

### I1 / R1 — `FRONTEND-07-T03`

- Source: [source](07-frontend/07-message-and-reply-timeline.md#L34)
- Dependencies: `FRONTEND-07-T02`, `BACKEND-05-T03`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-07-t03`
- Worktree: `../alon-ai-task-frontend-07-t03`
- Acceptance evidence: [source](07-frontend/07-message-and-reply-timeline.md#L34) — Test evidence: read-only UI cannot send; call agreement cannot become purchase acceptance.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-07-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 275 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T08`, `BACKEND-04-T04`, `WF-06-T04`, `WF-07-T03`, `BACKEND-02-T05`, `FRONTEND-07-T03`

### I1 / R1 — `FRONTEND-07-T04`

- Source: [source](07-frontend/07-message-and-reply-timeline.md#L36)
- Dependencies: `FRONTEND-07-T03`, `BACKEND-04-T04`, `WF-06-T04`, `BACKEND-02-T05`, `BACKEND-01-T08`, `WF-07-T03`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-07-t04`
- Worktree: `../alon-ai-task-frontend-07-t04`
- Acceptance evidence: [source](07-frontend/07-message-and-reply-timeline.md#L36) — Test evidence: duplicate callback, DST, ETag, notification and timeout/replay browser cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 276 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-06-T04`, `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-08-T01`

- Source: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L28)
- Dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-08-t01`
- Worktree: `../alon-ai-task-frontend-08-t01`
- Acceptance evidence: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L28) — Test evidence: zero/missing/unresolved data and call-versus-purchase tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-08-T02`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 277 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-08-T01`

### I1 / R1 — `FRONTEND-08-T02`

- Source: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L30)
- Dependencies: `FRONTEND-08-T01`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-08-t02`
- Worktree: `../alon-ai-task-frontend-08-t02`
- Acceptance evidence: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L30) — Test evidence: unknown cost or outcomes remain unavailable.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-08-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 278 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-06-T03`, `FRONTEND-08-T02`

### I1 / R1 — `FRONTEND-08-T03`

- Source: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L32)
- Dependencies: `FRONTEND-08-T02`, `BACKEND-06-T03`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-08-t03`
- Worktree: `../alon-ai-task-frontend-08-t03`
- Acceptance evidence: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L32) — Test evidence: mixed currency, unreconciled cost, missing time and floor boundary cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-08-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 279 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T09`, `BACKEND-01-T10`, `BACKEND-06-T02`, `BACKEND-02-T05`, `FRONTEND-08-T03`

### I1 / R1 — `FRONTEND-08-T04`

- Source: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L34)
- Dependencies: `FRONTEND-08-T03`, `BACKEND-06-T02`, `BACKEND-02-T05`, `BACKEND-01-T09`, `BACKEND-01-T10`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-08-t04`
- Worktree: `../alon-ai-task-frontend-08-t04`
- Acceptance evidence: [source](07-frontend/08-cost-funnel-and-decision-analytics.md#L34) — Test evidence: no causal claim from correlation, no mid-cohort mutation or client promotion.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 280 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-06-T04`, `BACKEND-02-T05`

### I1 / R1 — `FRONTEND-09-T01`

- Source: [source](07-frontend/09-error-recovery-and-accessibility.md#L30)
- Dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-09-t01`
- Worktree: `../alon-ai-task-frontend-09-t01`
- Acceptance evidence: [source](07-frontend/09-error-recovery-and-accessibility.md#L30) — Test evidence: unknown kinds and stale snapshots fail visibly.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-09-T02`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 281 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-04-T04`, `BACKEND-02-T05`, `FRONTEND-09-T01`

### I1 / R1 — `FRONTEND-09-T02`

- Source: [source](07-frontend/09-error-recovery-and-accessibility.md#L32)
- Dependencies: `FRONTEND-09-T01`, `BACKEND-04-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-09-t02`
- Worktree: `../alon-ai-task-frontend-09-t02`
- Acceptance evidence: [source](07-frontend/09-error-recovery-and-accessibility.md#L32) — Test evidence: zero search result, duplicate callback and ambiguous write cannot retry.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-09-T03`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 282 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T04`, `FRONTEND-09-T02`

### I1 / R1 — `FRONTEND-09-T03`

- Source: [source](07-frontend/09-error-recovery-and-accessibility.md#L34)
- Dependencies: `FRONTEND-09-T02`, `SEC-05-T04`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-09-t03`
- Worktree: `../alon-ai-task-frontend-09-t03`
- Acceptance evidence: [source](07-frontend/09-error-recovery-and-accessibility.md#L34) — Test evidence: kill races, terminal state and active-cohort rollback tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `FRONTEND-09-T04`, `OBS-01-T05`, `OBS-03-T04`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 283 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `FRONTEND-09-T03`

### I1 / R1 — `FRONTEND-09-T04`

- Source: [source](07-frontend/09-error-recovery-and-accessibility.md#L36)
- Dependencies: `FRONTEND-09-T03`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-09-t04`
- Worktree: `../alon-ai-task-frontend-09-t04`
- Acceptance evidence: [source](07-frontend/09-error-recovery-and-accessibility.md#L36) — Test evidence: browser bypass, cache/logout, redaction and hostile text tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-01-T05`, `OBS-01-T05`, `OBS-03-T04`, `FRONTEND-09-T05`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 284 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-01-T01`, `BACKEND-03-T03`, `ARCH-01-T04`, `PROVIDER-01-T03`, `DB-03-T06`, `TEST-04-T06`, `BACKEND-02-T05`, `FRONTEND-01-T05`, `FRONTEND-03-T03`, `FRONTEND-03-T05`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T04`, `FRONTEND-09-T04`

### I1 / R1 — `ARCH-01-T05`

- Source: [source](01-architecture/01-target-system-architecture.md#L168)
- Dependencies: `ARCH-01-T04`, `BACKEND-03-T03`, `PROVIDER-01-T03`, `DB-03-T06`, `WF-01-T01`, `TEST-04-T06`, `BACKEND-02-T05`, `FRONTEND-03-T05`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T04`, `FRONTEND-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
- Mode: `serial`
- Locks: `architecture-contracts`, `gmail-side-effects`, `openapi-contract`, `frontend-client`, `security-runtime`, `milestone-gate`
- Branch: `agent/arch-01-t05`
- Worktree: `../alon-ai-task-arch-01-t05`
- Acceptance evidence: [source](01-architecture/01-target-system-architecture.md#L168) — Test evidence: Gmail authority, generated-client drift, session, accessibility, exhaustive-state, recovery, and browser-journey suites.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `FRONTEND-09-T05`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 285 — M7

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-06-T04`, `BACKEND-02-T05`

### I1 / R1 — `BACKEND-06-T05`

- Source: [source](06-backend/06-reporting-and-query-services.md#L132)
- Dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `milestone-gate`, `backend-domain`
- Branch: `agent/backend-06-t05`
- Worktree: `../alon-ai-task-backend-06-t05`
- Acceptance evidence: [source](06-backend/06-reporting-and-query-services.md#L132) — Test evidence: query/gate comparison, privacy scan, browser E2E/accessibility.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T05`, `OBS-03-T04`, `FRONTEND-09-T05`, `SEC-02-T06`, `OBS-02-T01`, `OBS-04-T01`, `TEST-05-T01`, `TEST-06-T01`, `INFRA-02-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 286 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-01-T04`

### I1 / R1 — `OBS-01-T05`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L118)
- Dependencies: `OBS-01-T04`
- Mode: `serial`
- Locks: `live-environment`, `telemetry-catalog`
- Branch: `agent/obs-01-t05`
- Worktree: `../alon-ai-task-obs-01-t05`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L118) — Test evidence: sink outage/full disk/tamper/clock/skew/access tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T06`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 287 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-01-T05`

### I1 / R1 — `OBS-01-T06`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L120)
- Dependencies: `OBS-01-T05`
- Mode: `serial`
- Locks: `milestone-gate`, `telemetry-catalog`
- Branch: `agent/obs-01-t06`
- Worktree: `../alon-ai-task-obs-01-t06`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L120) — Test evidence: independent manual/query and automated scan.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 288 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-03-T03`

### I1 / R1 — `OBS-03-T04`

- Source: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L112)
- Dependencies: `OBS-03-T03`
- Mode: `serial`
- Locks: `live-environment`, `telemetry-catalog`
- Branch: `agent/obs-03-t04`
- Worktree: `../alon-ai-task-obs-03-t04`
- Acceptance evidence: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L112) — Test evidence: read/write/result/cost ID-set dedupe, cross-cohort/activation denial, unlike currency/discrepancy/80-100% thresholds and calendar-content canaries.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-03-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 289 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T01`, `AGENT-10-T05`, `OBS-03-T04`

### I1 / R1 — `OBS-03-T05`

- Source: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L114)
- Dependencies: `OBS-03-T04`, `AGENT-10-T01`, `AGENT-10-T05`
- Mode: `serial`
- Locks: `milestone-gate`, `telemetry-catalog`
- Branch: `agent/obs-03-t05`
- Worktree: `../alon-ai-task-obs-03-t05`
- Acceptance evidence: [source](09-observability-and-evaluation/03-provider-cost-accounting.md#L114) — Test evidence: failed/cancelled billed calls and boundary rounding.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 290 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`, `FRONTEND-03-T04`, `FRONTEND-03-T05`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T02`, `FRONTEND-08-T03`, `FRONTEND-08-T04`, `FRONTEND-09-T04`

### I1 / R1 — `FRONTEND-09-T05`

- Source: [source](07-frontend/09-error-recovery-and-accessibility.md#L38)
- Dependencies: `FRONTEND-09-T04`, `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-03-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T02`, `FRONTEND-08-T03`, `FRONTEND-03-T05`, `FRONTEND-08-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`
- Mode: `serial`
- Locks: `frontend-client`
- Branch: `agent/frontend-09-t05`
- Worktree: `../alon-ai-task-frontend-09-t05`
- Acceptance evidence: [source](07-frontend/09-error-recovery-and-accessibility.md#L38) — Test evidence: full simulation, timezone/DST, exception correction and no provider-write capability.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 291 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-02-T05`

### I1 / R1 — `SEC-02-T06`

- Source: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1010)
- Dependencies: `SEC-02-T05`
- Mode: `serial`
- Locks: `security-runtime`, `backup-restore`, `milestone-gate`
- Branch: `agent/sec-02-t06`
- Worktree: `../alon-ai-task-sec-02-t06`
- Acceptance evidence: [source](08-security-and-compliance/02-authentication-and-private-access.md#L1010) — Test evidence: no bypass cookie or restored session.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 292 — M8

- Agent count: 2 implementer(s) and 2 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T01`, `OBS-01-T01`, `OBS-01-T03`

### I1 / R1 — `OBS-02-T01`

- Source: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L327)
- Dependencies: `OBS-01-T01`, `OBS-01-T03`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-02-t01`
- Worktree: `../alon-ai-task-obs-02-t01`
- Acceptance evidence: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L327) — Test evidence: registry/schema/cardinality/sampling tests.
- Optional acceptance commands: none
- Merge order: 1

### I2 / R2 — `OBS-04-T01`

- Source: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L53)
- Dependencies: `AGENT-10-T01`
- Mode: `parallel`
- Locks: `agent-artifacts`
- Branch: `agent/obs-04-t01`
- Worktree: `../alon-ai-task-obs-04-t01`
- Acceptance evidence: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L53) — Test evidence: exact set/count/hash/privacy and unknown-agent negatives.
- Optional acceptance commands: none
- Merge order: 2

- Newly unlocked tasks: `OBS-04-T02`, `INFRA-05-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 293 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-04-T01`

### I1 / R1 — `OBS-04-T02`

- Source: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L55)
- Dependencies: `OBS-04-T01`
- Mode: `serial`
- Locks: `agent-artifacts`, `live-environment`
- Branch: `agent/obs-04-t02`
- Worktree: `../alon-ai-task-obs-04-t02`
- Acceptance evidence: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L55) — Test evidence: crash/replay/missing/tamper/provider-network cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-04-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 294 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T04`, `AGENT-10-T05`, `OBS-04-T02`

### I1 / R1 — `OBS-04-T03`

- Source: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L57)
- Dependencies: `OBS-04-T02`, `AGENT-10-T04`, `AGENT-10-T05`
- Mode: `serial`
- Locks: `agent-runtime`, `agent-artifacts`, `milestone-gate`
- Branch: `agent/obs-04-t03`
- Worktree: `../alon-ai-task-obs-04-t03`
- Acceptance evidence: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L57) — Test evidence: weak evidence, immutable-bound and favorable-average denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 295 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T03`, `BACKEND-02-T05`

### I1 / R1 — `TEST-05-T01`

- Source: [source](10-testing/05-end-to-end-browser-tests.md#L48)
- Dependencies: `TEST-01-T03`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `test-command-registry`, `frontend-client`
- Branch: `agent/test-05-t01`
- Worktree: `../alon-ai-task-test-05-t01`
- Acceptance evidence: [source](10-testing/05-end-to-end-browser-tests.md#L48) — Test evidence: cross-worker pollution, restart and forbidden egress fail.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-05-T02`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 296 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-01-T05`, `FRONTEND-03-T03`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T03`, `FRONTEND-09-T04`, `TEST-05-T01`

### I1 / R1 — `TEST-05-T02`

- Source: [source](10-testing/05-end-to-end-browser-tests.md#L50)
- Dependencies: `TEST-05-T01`, `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T03`, `FRONTEND-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
- Mode: `serial`
- Locks: `test-command-registry`, `frontend-client`
- Branch: `agent/test-05-t02`
- Worktree: `../alon-ai-task-test-05-t02`
- Acceptance evidence: [source](10-testing/05-end-to-end-browser-tests.md#L50) — Test evidence: all exact state/error modes and no client authority.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-05-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 297 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T06`, `FRONTEND-09-T05`, `SEC-02-T06`, `TEST-05-T02`

### I1 / R1 — `TEST-05-T03`

- Source: [source](10-testing/05-end-to-end-browser-tests.md#L52)
- Dependencies: `TEST-05-T02`, `SEC-02-T06`, `PROVIDER-01-T06`, `FRONTEND-09-T05`
- Mode: `serial`
- Locks: `test-command-registry`, `frontend-client`
- Branch: `agent/test-05-t03`
- Worktree: `../alon-ai-task-test-05-t03`
- Acceptance evidence: [source](10-testing/05-end-to-end-browser-tests.md#L52) — Test evidence: CSRF, stale generation, slot, cohort and activation denials.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-05-T04`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 298 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-05-T03`

### I1 / R1 — `TEST-05-T04`

- Source: [source](10-testing/05-end-to-end-browser-tests.md#L54)
- Dependencies: `TEST-05-T03`
- Mode: `serial`
- Locks: `test-command-registry`, `frontend-client`
- Branch: `agent/test-05-t04`
- Worktree: `../alon-ai-task-test-05-t04`
- Acceptance evidence: [source](10-testing/05-end-to-end-browser-tests.md#L54) — Test evidence: every action usable without pointer/color or hidden timezone context.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 299 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T01`

### I1 / R1 — `TEST-06-T01`

- Source: [source](10-testing/06-load-security-and-chaos-tests.md#L60)
- Dependencies: `TEST-01-T01`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-06-t01`
- Worktree: `../alon-ai-task-test-06-t01`
- Acceptance evidence: [source](10-testing/06-load-security-and-chaos-tests.md#L60) — Test evidence: production-like name, unresolved variable, wrong DB/system ID and threshold-stop self-tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 300 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T01`

### I1 / R1 — `INFRA-02-T01`

- Source: [source](11-infrastructure/02-ci-cd-and-release-process.md#L68)
- Dependencies: `TEST-01-T01`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/infra-02-t01`
- Worktree: `../alon-ai-task-infra-02-t01`
- Acceptance evidence: [source](11-infrastructure/02-ci-cd-and-release-process.md#L68) — Test evidence: skipped/stale/tampered/missing lane negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-02-T02`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 301 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T01`

### I1 / R1 — `INFRA-02-T02`

- Source: [source](11-infrastructure/02-ci-cd-and-release-process.md#L70)
- Dependencies: `INFRA-02-T01`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/infra-02-t02`
- Worktree: `../alon-ai-task-infra-02-t02`
- Acceptance evidence: [source](11-infrastructure/02-ci-cd-and-release-process.md#L70) — Test evidence: modified lock/image/manifest/signature and mutable-tag rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-06-T02`, `INFRA-03-T01`, `LAUNCH-05-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 302 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-06-T01`, `INFRA-02-T02`

### I1 / R1 — `TEST-06-T02`

- Source: [source](10-testing/06-load-security-and-chaos-tests.md#L62)
- Dependencies: `TEST-06-T01`, `INFRA-02-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-06-t02`
- Worktree: `../alon-ai-task-test-06-t02`
- Acceptance evidence: [source](10-testing/06-load-security-and-chaos-tests.md#L62) — Test evidence: latency/errors/resources/rows/leases/cost exactness.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 303 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T02`

### I1 / R1 — `INFRA-03-T01`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L65)
- Dependencies: `INFRA-02-T02`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-03-t01`
- Worktree: `../alon-ai-task-infra-03-t01`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L65) — Test evidence: external port scan, lost-overlay recovery and hardening audit.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-03-T02`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 304 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T02`, `INFRA-03-T01`

### I1 / R1 — `INFRA-03-T02`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L67)
- Dependencies: `INFRA-03-T01`, `INFRA-02-T02`
- Mode: `serial`
- Locks: `compose-topology`
- Branch: `agent/infra-03-t02`
- Worktree: `../alon-ai-task-infra-03-t02`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L67) — Test evidence: network/capability/read-only/non-root/health/schema/controls tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-03-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 305 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T01`, `INFRA-03-T02`

### I1 / R1 — `INFRA-03-T03`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L69)
- Dependencies: `INFRA-03-T02`, `SEC-03-T01`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/infra-03-t03`
- Worktree: `../alon-ai-task-infra-03-t03`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L69) — Test evidence: cross-purpose/version/environment denial, rotation/revoke/restart/backup.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-03-T04`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 306 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-03-T03`

### I1 / R1 — `INFRA-03-T04`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L71)
- Dependencies: `INFRA-03-T03`
- Mode: `serial`
- Locks: `backup-restore`, `live-environment`
- Branch: `agent/infra-03-t04`
- Worktree: `../alon-ai-task-infra-03-t04`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L71) — Test evidence: the complete CAS/Object-Lock/IAM/pgBackRest/account-lockout matrix, Google credential/KMS unavailable restore bootstrap, key rotation/loss and region mismatch; no emulator evidence.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-03-T05`, `INFRA-04-T01`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 307 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-03-T04`

### I1 / R1 — `INFRA-03-T05`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L73)
- Dependencies: `INFRA-03-T04`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-03-t05`
- Worktree: `../alon-ai-task-infra-03-t05`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L73) — Test evidence: Internet scan, spoofed forwarding, TLS renewal and wrong-host/path cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 308 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-03-T04`

### I1 / R1 — `INFRA-04-T01`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L169)
- Dependencies: `INFRA-03-T04`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t01`
- Worktree: `../alon-ai-task-infra-04-t01`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L169) — Test evidence: duplicate, conflict, divergence, network, full-disk, key, clock, timeline, and Object-Lock cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-04-T02`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 309 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T01`

### I1 / R1 — `INFRA-04-T02`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L171)
- Dependencies: `INFRA-04-T01`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t02`
- Worktree: `../alon-ai-task-infra-04-t02`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L171) — Test evidence: interrupted/corrupt/wrong-version/missing-WAL/manifest/key/repository-divergence cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-03-T05`, `SEC-01-T02`, `OBS-02-T02`, `INFRA-02-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 310 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T04`, `INFRA-04-T02`

### I1 / R1 — `SEC-03-T05`

- Source: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L101)
- Dependencies: `SEC-03-T04`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `security-runtime`, `backup-restore`, `milestone-gate`
- Branch: `agent/sec-03-t05`
- Worktree: `../alon-ai-task-sec-03-t05`
- Acceptance evidence: [source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L101) — Test evidence: missing/corrupt key/object/manifest variants.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 311 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-01-T01`, `BACKEND-02-T05`, `OBS-01-T06`, `INFRA-03-T02`, `INFRA-04-T02`

### I1 / R1 — `SEC-01-T02`

- Source: [source](08-security-and-compliance/01-threat-model.md#L121)
- Dependencies: `SEC-01-T01`, `BACKEND-02-T05`, `OBS-01-T06`, `INFRA-03-T02`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-01-t02`
- Worktree: `../alon-ai-task-sec-01-t02`
- Acceptance evidence: [source](08-security-and-compliance/01-threat-model.md#L121) — Test evidence: named closure tests, route-set diff, backup/surface set equality, and public-off/private-only fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-01-T03`, `TEST-06-T03`, `INFRA-03-T06`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 312 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-01-T02`

### I1 / R1 — `SEC-01-T03`

- Source: [source](08-security-and-compliance/01-threat-model.md#L123)
- Dependencies: `SEC-01-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/sec-01-t03`
- Worktree: `../alon-ai-task-sec-01-t03`
- Acceptance evidence: [source](08-security-and-compliance/01-threat-model.md#L123) — Test evidence: each Critical row has a fresh pass.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-01-T04`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 313 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-01-T03`

### I1 / R1 — `SEC-01-T04`

- Source: [source](08-security-and-compliance/01-threat-model.md#L125)
- Dependencies: `SEC-01-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-01-t04`
- Worktree: `../alon-ai-task-sec-01-t04`
- Acceptance evidence: [source](08-security-and-compliance/01-threat-model.md#L125) — Test evidence: no blind send, SQL patch, stale authority, or automatic re-enable.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 314 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-06-T01`, `OBS-03-T02`, `AGENT-10-T05`, `SEC-05-T04`, `WF-05-T05`, `BACKEND-02-T05`, `OBS-02-T01`, `INFRA-04-T02`

### I1 / R1 — `OBS-02-T02`

- Source: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L329)
- Dependencies: `OBS-02-T01`, `BACKEND-02-T05`, `DB-06-T01`, `WF-05-T05`, `AGENT-10-T05`, `SEC-05-T04`, `OBS-03-T02`, `INFRA-04-T02`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-02-t02`
- Worktree: `../alon-ai-task-obs-02-t02`
- Acceptance evidence: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L329) — Test evidence: golden count/latency/exemplar fixtures at each crash boundary.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-06-T02`, `OBS-02-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 315 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-06-T01`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `PROVIDER-03-T06`, `PROVIDER-06-T05`, `SEC-02-T05`, `SEC-03-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `OBS-02-T01`, `OBS-04-T01`, `OBS-04-T02`, `INFRA-04-T02`, `SEC-01-T02`, `OBS-02-T02`

### I1 / R1 — `SEC-06-T02`

- Source: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L129)
- Dependencies: `SEC-06-T01`, `SEC-01-T02`, `SEC-02-T05`, `SEC-03-T04`, `INFRA-04-T02`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `PROVIDER-03-T06`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `PROVIDER-06-T05`, `OBS-02-T01`, `OBS-02-T02`, `OBS-04-T01`, `OBS-04-T02`
- Mode: `serial`
- Locks: `compliance-policy`, `milestone-gate`, `security-runtime`, `backup-restore`, `database-schema`
- Branch: `agent/sec-06-t02`
- Worktree: `../alon-ai-task-sec-06-t02`
- Acceptance evidence: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L129) — Test evidence: exact inventory path/value equality with the deterministic rules, negative newly introduced field/table/reader/transform fixtures, all declared external-object policy axes, and exact policy row-key/value equality across all consumers.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `DB-06-T05`, `INFRA-04-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 316 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-06-T04`, `SEC-06-T02`

### I1 / R1 — `DB-06-T05`

- Source: [source](02-database/06-migrations-seeding-and-retention.md#L197)
- Dependencies: `DB-06-T04`, `SEC-06-T02`
- Mode: `serial`
- Locks: `database-schema`, `backend-domain`, `security-runtime`, `compliance-policy`
- Branch: `agent/db-06-t05`
- Worktree: `../alon-ai-task-db-06-t05`
- Acceptance evidence: [source](02-database/06-migrations-seeding-and-retention.md#L197) — Test evidence: fixture matrix for holds, unresolved ambiguity, 24/72 clocks/escalation, missed-SLA control closure, no-partial-mutation, suppression target-ref/list/replay stability after source purge, foreign-key closure, replay, and restore.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-02-T03`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 317 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-02-T02`

### I1 / R1 — `OBS-02-T03`

- Source: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L331)
- Dependencies: `OBS-02-T02`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-02-t03`
- Worktree: `../alon-ai-task-obs-02-t03`
- Acceptance evidence: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L331) — Test evidence: empty/low-volume/stale/gap/timezone/currency fixtures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-02-T04`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 318 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-02-T03`

### I1 / R1 — `OBS-02-T04`

- Source: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L333)
- Dependencies: `OBS-02-T03`
- Mode: `serial`
- Locks: `telemetry-catalog`, `live-environment`
- Branch: `agent/obs-02-t04`
- Worktree: `../alon-ai-task-obs-02-t04`
- Acceptance evidence: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L333) — Test evidence: fire every rule and disable each channel.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-02-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 319 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-02-T04`

### I1 / R1 — `OBS-02-T05`

- Source: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L335)
- Dependencies: `OBS-02-T04`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/obs-02-t05`
- Worktree: `../alon-ai-task-obs-02-t05`
- Acceptance evidence: [source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L335) — Test evidence: injected gaps/replay/counter reset/sampling/cardinality.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 320 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-02-T02`, `INFRA-04-T02`, `SEC-06-T02`, `DB-06-T05`

### I1 / R1 — `TEST-02-T03`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L66)
- Dependencies: `TEST-02-T02`, `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `test-command-registry`, `database-schema`, `backup-restore`, `milestone-gate`
- Branch: `agent/test-02-t03`
- Worktree: `../alon-ai-task-test-02-t03`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L66) — Test evidence: no revived contact/evidence/action or admission.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-02-T04`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 321 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T01`, `AGENT-10-T01`, `PROVIDER-03-T04`, `OBS-03-T02`, `DB-05-T05`, `AGENT-01-T03`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-10-T03`, `PROVIDER-01-T04`, `TEST-02-T03`

### I1 / R1 — `TEST-02-T04`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L68)
- Dependencies: `TEST-02-T03`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-01-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `DB-05-T05`, `OBS-03-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-02-t04`
- Worktree: `../alon-ai-task-test-02-t04`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L68) — Test evidence: three-capture completeness, separated read/write ports and immutable bounds.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-02-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 322 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `TEST-02-T04`

### I1 / R1 — `TEST-02-T05`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L70)
- Dependencies: `TEST-02-T04`, `BACKEND-02-T05`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-02-t05`
- Worktree: `../alon-ai-task-test-02-t05`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L70) — Test evidence: forged membership/price/confirmation/activation and stale snapshots deny.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-02-T06`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 323 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-03-T01`, `OBS-05-T01`, `TEST-02-T05`

### I1 / R1 — `TEST-02-T06`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L72)
- Dependencies: `TEST-02-T05`, `BACKEND-03-T01`, `OBS-05-T01`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-02-t06`
- Worktree: `../alon-ai-task-test-02-t06`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L72) — Test evidence: zero credential/provider calls and exhaustive cross-pair denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-02-T07`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 324 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-02-T06`

### I1 / R1 — `TEST-02-T07`

- Source: [source](10-testing/02-contract-and-integration-tests.md#L74)
- Dependencies: `TEST-02-T06`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-02-t07`
- Worktree: `../alon-ai-task-test-02-t07`
- Acceptance evidence: [source](10-testing/02-contract-and-integration-tests.md#L74) — Test evidence: missing/duplicate requirement and unavailable suite block.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 325 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-06-T02`, `SEC-01-T02`

### I1 / R1 — `TEST-06-T03`

- Source: [source](10-testing/06-load-security-and-chaos-tests.md#L64)
- Dependencies: `TEST-06-T02`, `SEC-01-T02`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-06-t03`
- Worktree: `../alon-ai-task-test-06-t03`
- Acceptance evidence: [source](10-testing/06-load-security-and-chaos-tests.md#L64) — Test evidence: no orphan threat and zero uncontrolled data/authority path.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 326 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T02`, `INFRA-04-T02`

### I1 / R1 — `INFRA-02-T03`

- Source: [source](11-infrastructure/02-ci-cd-and-release-process.md#L72)
- Dependencies: `INFRA-02-T02`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/infra-02-t03`
- Worktree: `../alon-ai-task-infra-02-t03`
- Acceptance evidence: [source](11-infrastructure/02-ci-cd-and-release-process.md#L72) — Test evidence: wrong target, stale backup, low disk, active ambiguity, incompatible runtime and migration-failure cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-02-T04`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 327 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T03`

### I1 / R1 — `INFRA-02-T04`

- Source: [source](11-infrastructure/02-ci-cd-and-release-process.md#L74)
- Dependencies: `INFRA-02-T03`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/infra-02-t04`
- Worktree: `../alon-ai-task-infra-02-t04`
- Acceptance evidence: [source](11-infrastructure/02-ci-cd-and-release-process.md#L74) — Test evidence: mid-promotion crash and incompatible in-flight run cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-06-T04`, `INFRA-02-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 328 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T02`, `TEST-06-T03`, `INFRA-02-T04`

### I1 / R1 — `TEST-06-T04`

- Source: [source](10-testing/06-load-security-and-chaos-tests.md#L66)
- Dependencies: `TEST-06-T03`, `INFRA-04-T02`, `INFRA-02-T04`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-06-t04`
- Worktree: `../alon-ai-task-test-06-t04`
- Acceptance evidence: [source](10-testing/06-load-security-and-chaos-tests.md#L66) — Test evidence: each fault meets its RPO/RTO/invariant or records failure.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-06-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 329 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T01`, `TEST-06-T04`

### I1 / R1 — `TEST-06-T05`

- Source: [source](10-testing/06-load-security-and-chaos-tests.md#L68)
- Dependencies: `TEST-06-T04`, `TEST-01-T01`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-06-t05`
- Worktree: `../alon-ai-task-test-06-t05`
- Acceptance evidence: [source](10-testing/06-load-security-and-chaos-tests.md#L68) — Test evidence: orphan/duplicate/unsafe/unavailable negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 330 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T04`

### I1 / R1 — `INFRA-02-T05`

- Source: [source](11-infrastructure/02-ci-cd-and-release-process.md#L76)
- Dependencies: `INFRA-02-T04`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/infra-02-t05`
- Worktree: `../alon-ai-task-infra-02-t05`
- Acceptance evidence: [source](11-infrastructure/02-ci-cd-and-release-process.md#L76) — Test evidence: PostgreSQL major upgrade clone, secret generation rotation, provider schema drift and rollback.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-02-T06`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 331 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T05`

### I1 / R1 — `INFRA-02-T06`

- Source: [source](11-infrastructure/02-ci-cd-and-release-process.md#L78)
- Dependencies: `INFRA-02-T05`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/infra-02-t06`
- Worktree: `../alon-ai-task-infra-02-t06`
- Acceptance evidence: [source](11-infrastructure/02-ci-cd-and-release-process.md#L78) — Test evidence: orphan/duplicate, unavailable, wrong target and partial-promotion negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 332 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `INFRA-03-T05`, `SEC-01-T02`

### I1 / R1 — `INFRA-03-T06`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L75)
- Dependencies: `INFRA-03-T05`, `BACKEND-02-T05`, `SEC-01-T02`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-03-t06`
- Worktree: `../alon-ai-task-infra-03-t06`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L75) — Test evidence: TEST-05/06 scanner/abuse/set-equality matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T04`, `INFRA-03-T07`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 333 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-02-T01`, `SEC-04-T03`, `SEC-05-T02`, `BACKEND-02-T05`, `SEC-01-T02`, `INFRA-03-T06`

### I1 / R1 — `SEC-04-T04`

- Source: [source](08-security-and-compliance/04-outreach-compliance.md#L103)
- Dependencies: `SEC-04-T03`, `SEC-05-T02`, `BACKEND-02-T05`, `SEC-01-T02`, `INFRA-03-T06`, `PROVIDER-02-T01`
- Mode: `serial`
- Locks: `gmail-side-effects`, `compliance-policy`
- Branch: `agent/sec-04-t04`
- Worktree: `../alon-ai-task-sec-04-t04`
- Acceptance evidence: [source](08-security-and-compliance/04-outreach-compliance.md#L103) — Test evidence: offline/synthetic provider, token, scanner, method, Origin/fetch/CSRF, rate, redaction, and dependency-fail-close matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 334 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-06-T02`, `INFRA-02-T04`, `INFRA-03-T06`

### I1 / R1 — `INFRA-03-T07`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L77)
- Dependencies: `INFRA-03-T06`, `TEST-06-T02`, `INFRA-02-T04`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-03-t07`
- Worktree: `../alon-ai-task-infra-03-t07`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L77) — Test evidence: no data/authority drift under resource pressure/reboot.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-03-T08`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 335 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-03-T07`

### I1 / R1 — `INFRA-03-T08`

- Source: [source](11-infrastructure/03-private-vps-deployment.md#L79)
- Dependencies: `INFRA-03-T07`
- Mode: `serial`
- Locks: `compose-topology`
- Branch: `agent/infra-03-t08`
- Worktree: `../alon-ai-task-infra-03-t08`
- Acceptance evidence: [source](11-infrastructure/03-private-vps-deployment.md#L79) — Test evidence: orphan/duplicate and unavailable-provider negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 336 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T02`, `SEC-06-T02`

### I1 / R1 — `INFRA-04-T03`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L173)
- Dependencies: `INFRA-04-T02`, `SEC-06-T02`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t03`
- Worktree: `../alon-ai-task-infra-04-t03`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L173) — Test evidence: P0-P9, exact marker/certificate/head preimages and receipts, one-authority validator, provider-survival truth table, prepared-only quarantine, authorization concurrency/fences, concurrent genesis/update, `200|409|412|timeout` strong-read reconciliation, version/ETag/checksum/Object-Lock/IAM negatives, committed-without-applied replay and applied-without-committed structural negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-04-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 337 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T03`

### I1 / R1 — `INFRA-04-T04`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L175)
- Dependencies: `INFRA-04-T03`, `SEC-06-T02`, `DB-06-T05`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t04`
- Worktree: `../alon-ai-task-infra-04-t04`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L175) — Test evidence: attempted legal/incident hold extension, chain dependency, wrong bucket/ID, overlong Object Lock and partial-delete replay.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-06-T03`, `INFRA-04-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 338 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T04`

### I1 / R1 — `SEC-06-T03`

- Source: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L131)
- Dependencies: `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T04`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/sec-06-t03`
- Worktree: `../alon-ai-task-sec-06-t03`
- Acceptance evidence: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L131) — Test evidence: FK/hold/crash/retry/restore matrix across all product tables.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-06-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 339 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-06-T03`

### I1 / R1 — `SEC-06-T04`

- Source: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L133)
- Dependencies: `SEC-06-T03`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/sec-06-t04`
- Worktree: `../alon-ai-task-sec-06-t04`
- Acceptance evidence: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L133) — Test evidence: impersonation, mixed-person, held/immutable, backup propagation.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-06-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 340 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-06-T04`

### I1 / R1 — `SEC-06-T05`

- Source: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L135)
- Dependencies: `SEC-06-T04`
- Mode: `serial`
- Locks: `compliance-policy`, `security-runtime`, `live-environment`
- Branch: `agent/sec-06-t05`
- Worktree: `../alon-ai-task-sec-06-t05`
- Acceptance evidence: [source](08-security-and-compliance/06-data-privacy-and-retention.md#L135) — Test evidence: provider/traces/backups/prompts/evals.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 341 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T04`

### I1 / R1 — `INFRA-04-T05`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L177)
- Dependencies: `INFRA-04-T04`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t05`
- Worktree: `../alon-ai-task-infra-04-t05`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L177) — Test evidence: latest/point-in-time/corrupt/key-loss/expired-session/unresolved-attempt variants.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `WF-06-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 342 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-05-T01`, `WF-06-T04`, `INFRA-04-T05`

### I1 / R1 — `WF-06-T05`

- Source: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L93)
- Dependencies: `WF-06-T04`, `OBS-05-T01`, `INFRA-04-T05`
- Mode: `serial`
- Locks: `backup-restore`, `workflow-runtime`
- Branch: `agent/wf-06-t05`
- Worktree: `../alon-ai-task-wf-06-t05`
- Acceptance evidence: [source](03-workflows/06-pause-cancel-resume-and-recovery.md#L93) — Test evidence: corrupted/unknown-state fixtures and restore drill.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-03-T06`, `OBS-05-T03`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 343 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-03-T05`, `INFRA-04-T02`, `WF-06-T05`

### I1 / R1 — `TEST-03-T06`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L92)
- Dependencies: `TEST-03-T05`, `INFRA-04-T02`, `WF-06-T05`
- Mode: `serial`
- Locks: `backup-restore`, `workflow-runtime`
- Branch: `agent/test-03-t06`
- Worktree: `../alon-ai-task-test-03-t06`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L92) — Test evidence: direct SQL/free-form repair/provider call spies remain zero.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-03-T07`, `OBS-04-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 344 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-03-T06`

### I1 / R1 — `TEST-03-T07`

- Source: [source](10-testing/03-workflow-recovery-tests.md#L94)
- Dependencies: `TEST-03-T06`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-03-t07`
- Worktree: `../alon-ai-task-test-03-t07`
- Acceptance evidence: [source](10-testing/03-workflow-recovery-tests.md#L94) — Test evidence: missing/duplicate scenario and unavailable-runtime negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-01-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 345 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-00-T01`, `PROVIDER-01-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `WF-01-T03`, `TEST-03-T03`, `ARCH-03-T01`, `ARCH-02-T01`, `DB-05-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `BACKEND-01-T04`, `WF-03-T05`, `WF-04-T05`, `WF-02-T05`, `BACKEND-01-T08`, `BACKEND-01-T09`, `BACKEND-01-T10`, `TEST-03-T04`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `WF-05-T05`, `TEST-04-T05`, `TEST-04-T06`, `OBS-04-T03`, `WF-06-T05`, `TEST-03-T06`

### I1 / R1 — `OBS-04-T04`

- Source: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L59)
- Dependencies: `OBS-04-T03`, `ARCH-03-T01`, `DB-05-T01`, `ARCH-02-T01`, `BACKEND-01-T04`, `WF-00-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`, `WF-06-T05`, `PROVIDER-01-T01`, `TEST-03-T03`, `TEST-03-T04`, `TEST-03-T06`, `TEST-04-T06`, `WF-05-T05`, `WF-01-T03`, `TEST-04-T05`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `BACKEND-01-T08`, `BACKEND-01-T09`, `BACKEND-01-T10`
- Mode: `serial`
- Locks: `workflow-runtime`, `backup-restore`, `milestone-gate`
- Branch: `agent/obs-04-t04`
- Worktree: `../alon-ai-task-obs-04-t04`
- Acceptance evidence: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L59) — Test evidence: every durable boundary and no duplicate side effect.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-04-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 346 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-04-T04`

### I1 / R1 — `OBS-04-T05`

- Source: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L61)
- Dependencies: `OBS-04-T04`
- Mode: `parallel`
- Locks: `telemetry-catalog`
- Branch: `agent/obs-04-t05`
- Worktree: `../alon-ai-task-obs-04-t05`
- Acceptance evidence: [source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L61) — Test evidence: cross-campaign timing, mid-cohort blocking and unchanged historical hashes.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 347 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T03`, `SEC-02-T05`, `OBS-05-T02`, `SEC-03-T04`, `INFRA-02-T04`, `INFRA-04-T05`, `WF-06-T05`

### I1 / R1 — `OBS-05-T03`

- Source: [source](09-observability-and-evaluation/05-incident-response.md#L165)
- Dependencies: `OBS-05-T02`, `PRODUCT-03-T03`, `SEC-02-T05`, `SEC-03-T04`, `INFRA-02-T04`, `INFRA-04-T05`, `WF-06-T05`
- Mode: `serial`
- Locks: `security-runtime`, `backup-restore`
- Branch: `agent/obs-05-t03`
- Worktree: `../alon-ai-task-obs-05-t03`
- Acceptance evidence: [source](09-observability-and-evaluation/05-incident-response.md#L165) — Test evidence: inject every unavailable-layer/crash/replay variant.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-03-T04`, `OBS-05-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 348 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-03-T03`, `OBS-05-T02`, `SEC-05-T04`, `OBS-05-T03`

### I1 / R1 — `PRODUCT-03-T04`

- Source: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L130)
- Dependencies: `PRODUCT-03-T03`, `SEC-05-T04`, `OBS-05-T02`, `OBS-05-T03`
- Mode: `serial`
- Locks: `security-runtime`, `milestone-gate`
- Branch: `agent/product-03-t04`
- Worktree: `../alon-ai-task-product-03-t04`
- Acceptance evidence: [source](00-product-strategy/03-risk-register-and-kill-criteria.md#L130) — Test evidence: event timelines prove no unauthorized action after stop.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 349 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-02-T04`, `OBS-05-T03`

### I1 / R1 — `OBS-05-T04`

- Source: [source](09-observability-and-evaluation/05-incident-response.md#L167)
- Dependencies: `OBS-05-T03`, `OBS-02-T04`
- Mode: `serial`
- Locks: `telemetry-catalog`, `live-environment`
- Branch: `agent/obs-05-t04`
- Worktree: `../alon-ai-task-obs-05-t04`
- Acceptance evidence: [source](09-observability-and-evaluation/05-incident-response.md#L167) — Test evidence: primary/out-of-band/provider/counsel channel outage.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-05-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 350 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-05-T04`

### I1 / R1 — `OBS-05-T05`

- Source: [source](09-observability-and-evaluation/05-incident-response.md#L169)
- Dependencies: `OBS-05-T04`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/obs-05-t05`
- Worktree: `../alon-ai-task-obs-05-t05`
- Acceptance evidence: [source](09-observability-and-evaluation/05-incident-response.md#L169) — Test evidence: IR-01..13 matrix and 90-day restore.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-05-T06`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 351 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-05-T05`

### I1 / R1 — `OBS-05-T06`

- Source: [source](09-observability-and-evaluation/05-incident-response.md#L171)
- Dependencies: `OBS-05-T05`
- Mode: `serial`
- Locks: `security-runtime`
- Branch: `agent/obs-05-t06`
- Worktree: `../alon-ai-task-obs-05-t06`
- Acceptance evidence: [source](09-observability-and-evaluation/05-incident-response.md#L171) — Test evidence: missing/stale/larger-cohort/automatic-enable denials.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 352 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T04`, `TEST-04-T06`, `TEST-05-T04`, `TEST-02-T07`, `TEST-06-T04`, `TEST-06-T05`, `TEST-03-T06`, `TEST-03-T07`

### I1 / R1 — `TEST-01-T05`

- Source: [source](10-testing/01-testing-strategy.md#L169)
- Dependencies: `TEST-01-T04`, `TEST-02-T07`, `TEST-05-T04`, `TEST-06-T04`, `TEST-03-T06`, `TEST-04-T06`, `TEST-03-T07`, `TEST-06-T05`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-01-t05`
- Worktree: `../alon-ai-task-test-01-t05`
- Acceptance evidence: [source](10-testing/01-testing-strategy.md#L169) — Test evidence: stale/failed/wrong-environment/wrong-fixture/M1-waiver negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-01-T06`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 353 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T05`

### I1 / R1 — `TEST-01-T06`

- Source: [source](10-testing/01-testing-strategy.md#L171)
- Dependencies: `TEST-01-T05`
- Mode: `serial`
- Locks: `test-command-registry`
- Branch: `agent/test-01-t06`
- Worktree: `../alon-ai-task-test-01-t06`
- Acceptance evidence: [source](10-testing/01-testing-strategy.md#L171) — Test evidence: injected intermittent safety failure cannot be averaged or retried away.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 354 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-01-T03`, `BACKEND-06-T02`, `OBS-02-T01`

### I1 / R1 — `INFRA-05-T01`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L98)
- Dependencies: `OBS-02-T01`, `OBS-01-T03`, `BACKEND-06-T02`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t01`
- Worktree: `../alon-ai-task-infra-05-t01`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L98) — Test evidence: label/cardinality/canary/drop/restart/count mismatch cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-05-T02`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 355 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-05-T01`, `OBS-02-T04`, `OBS-05-T04`, `INFRA-05-T01`

### I1 / R1 — `INFRA-05-T02`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L100)
- Dependencies: `INFRA-05-T01`, `OBS-02-T04`, `OBS-05-T01`, `OBS-05-T04`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t02`
- Worktree: `../alon-ai-task-infra-05-t02`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L100) — Test evidence: every positive tuple, cross-pair/unknown and resolution applicability.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-05-T03`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 356 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-05-T02`

### I1 / R1 — `INFRA-05-T03`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L102)
- Dependencies: `INFRA-05-T02`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t03`
- Worktree: `../alon-ai-task-infra-05-t03`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L102) — Test evidence: delivery/ack timestamps and no Gmail dependency.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-05-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 357 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-05-T01`, `INFRA-05-T03`

### I1 / R1 — `INFRA-05-T04`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L104)
- Dependencies: `INFRA-05-T03`, `OBS-05-T01`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t04`
- Worktree: `../alon-ai-task-infra-05-t04`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L104) — Test evidence: every split-stage plus simultaneous Google/PagerDuty/Healthchecks loss.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-05-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 358 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T03`, `INFRA-05-T04`

### I1 / R1 — `INFRA-05-T05`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L106)
- Dependencies: `INFRA-05-T04`, `INFRA-04-T03`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t05`
- Worktree: `../alon-ai-task-infra-05-t05`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L106) — Test evidence: normal, GCS-data-only, AWS-S3-data-only, Google-wide and isolated restore paths plus unavailable/ambiguous/stale/forked/missing/version/checksum negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-05-T06`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 359 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-03-T04`, `INFRA-04-T02`, `INFRA-02-T04`, `INFRA-05-T05`

### I1 / R1 — `INFRA-05-T06`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L108)
- Dependencies: `INFRA-05-T05`, `INFRA-02-T04`, `SEC-03-T04`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t06`
- Worktree: `../alon-ai-task-infra-05-t06`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L108) — Test evidence: VPS/DB/WAL/KMS/release/overlay/DNS/telemetry/retention cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-04-T06`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 360 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T05`, `INFRA-05-T06`

### I1 / R1 — `INFRA-04-T06`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L179)
- Dependencies: `INFRA-04-T05`, `INFRA-05-T06`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t06`
- Worktree: `../alon-ai-task-infra-04-t06`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L179) — Test evidence: no provider call, controls/public off and exact data/runtime compatibility.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-04-T07`, `INFRA-05-T07`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 361 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T06`

### I1 / R1 — `INFRA-04-T07`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L181)
- Dependencies: `INFRA-04-T06`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t07`
- Worktree: `../alon-ai-task-infra-04-t07`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L181) — Test evidence: Google KMS/Secret Manager/GCS unavailable, old/new/lost key, AWS account lockout, S3 Object Lock and simultaneous-failure matrix.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `INFRA-04-T08`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 362 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T07`

### I1 / R1 — `INFRA-04-T08`

- Source: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L183)
- Dependencies: `INFRA-04-T07`
- Mode: `serial`
- Locks: `backup-restore`
- Branch: `agent/infra-04-t08`
- Worktree: `../alon-ai-task-infra-04-t08`
- Acceptance evidence: [source](11-infrastructure/04-postgresql-backups-and-restores.md#L183) — Test evidence: orphan/duplicate/unavailable/integrity/unsafe/partial negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 363 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-05-T06`, `INFRA-04-T06`

### I1 / R1 — `INFRA-05-T07`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L110)
- Dependencies: `INFRA-05-T06`, `INFRA-04-T06`
- Mode: `serial`
- Locks: `live-environment`
- Branch: `agent/infra-05-t07`
- Worktree: `../alon-ai-task-infra-05-t07`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L110) — Test evidence: stale/missing/larger-authority/automatic-enable denials.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `ARCH-01-T06`, `INFRA-05-T08`, `LAUNCH-02-T01`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 364 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `ARCH-01-T05`, `INFRA-03-T07`, `OBS-05-T03`, `INFRA-04-T06`, `INFRA-05-T07`

### I1 / R1 — `ARCH-01-T06`

- Source: [source](01-architecture/01-target-system-architecture.md#L170)
- Dependencies: `ARCH-01-T05`, `INFRA-03-T07`, `INFRA-04-T06`, `INFRA-05-T07`, `OBS-05-T03`
- Mode: `serial`
- Locks: `architecture-contracts`, `compose-topology`, `backup-restore`, `live-environment`, `milestone-gate`
- Branch: `agent/arch-01-t06`
- Worktree: `../alon-ai-task-arch-01-t06`
- Acceptance evidence: [source](01-architecture/01-target-system-architecture.md#L170) — Test evidence: fresh-server restore and incident drills.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 365 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-05-T07`

### I1 / R1 — `INFRA-05-T08`

- Source: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L112)
- Dependencies: `INFRA-05-T07`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/infra-05-t08`
- Worktree: `../alon-ai-task-infra-05-t08`
- Acceptance evidence: [source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L112) — Test evidence: missing/duplicate/unknown/cross-pair and unavailable-path negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 366 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T02`, `LAUNCH-01-T06`, `ARCH-01-T05`, `OBS-02-T05`, `INFRA-02-T04`, `INFRA-03-T08`, `TEST-01-T05`, `INFRA-04-T06`, `INFRA-05-T07`

### I1 / R1 — `LAUNCH-02-T01`

- Source: [source](12-launch-and-operations/02-controlled-internal-launch.md#L80)
- Dependencies: `LAUNCH-01-T06`, `INFRA-02-T04`, `INFRA-04-T06`, `OBS-02-T05`, `INFRA-05-T07`, `ARCH-01-T05`, `TEST-01-T02`, `TEST-01-T05`, `INFRA-03-T08`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-02-t01`
- Worktree: `../alon-ai-task-launch-02-t01`
- Acceptance evidence: [source](12-launch-and-operations/02-controlled-internal-launch.md#L80) — Test evidence: stale, wrong-target, catalog drift, open incident and authority-edge negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-02-T02`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 367 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T02`, `INFRA-04-T02`, `LAUNCH-02-T01`

### I1 / R1 — `LAUNCH-02-T02`

- Source: [source](12-launch-and-operations/02-controlled-internal-launch.md#L82)
- Dependencies: `LAUNCH-02-T01`, `INFRA-02-T02`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `live-environment`, `milestone-gate`
- Branch: `agent/launch-02-t02`
- Worktree: `../alon-ai-task-launch-02-t02`
- Acceptance evidence: [source](12-launch-and-operations/02-controlled-internal-launch.md#L82) — Test evidence: mid-promotion crash, incompatible workflow/schema, stale backup and rollback.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-02-T03`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 368 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-02-T02`

### I1 / R1 — `LAUNCH-02-T03`

- Source: [source](12-launch-and-operations/02-controlled-internal-launch.md#L84)
- Dependencies: `LAUNCH-02-T02`
- Mode: `serial`
- Locks: `live-environment`, `milestone-gate`
- Branch: `agent/launch-02-t03`
- Worktree: `../alon-ai-task-launch-02-t03`
- Acceptance evidence: [source](12-launch-and-operations/02-controlled-internal-launch.md#L84) — Test evidence: cap/concurrency/replay/cost/privacy/zero-Gmail assertions.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-02-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 369 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-03-T04`, `TEST-06-T04`, `INFRA-05-T06`, `INFRA-04-T06`, `LAUNCH-02-T03`

### I1 / R1 — `LAUNCH-02-T04`

- Source: [source](12-launch-and-operations/02-controlled-internal-launch.md#L86)
- Dependencies: `LAUNCH-02-T03`, `INFRA-03-T04`, `INFRA-04-T06`, `INFRA-05-T06`, `TEST-06-T04`
- Mode: `serial`
- Locks: `backup-restore`, `live-environment`, `milestone-gate`
- Branch: `agent/launch-02-t04`
- Worktree: `../alon-ai-task-launch-02-t04`
- Acceptance evidence: [source](12-launch-and-operations/02-controlled-internal-launch.md#L86) — Test evidence: provider unavailable=`30`, integrity=`40`, unsafe target=`50`, partial external=`60` all reject.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-02-T05`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 370 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `TEST-05-T02`, `LAUNCH-02-T04`

### I1 / R1 — `LAUNCH-02-T05`

- Source: [source](12-launch-and-operations/02-controlled-internal-launch.md#L88)
- Dependencies: `LAUNCH-02-T04`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `TEST-05-T02`
- Mode: `serial`
- Locks: `ci-release`, `live-environment`, `milestone-gate`
- Branch: `agent/launch-02-t05`
- Worktree: `../alon-ai-task-launch-02-t05`
- Acceptance evidence: [source](12-launch-and-operations/02-controlled-internal-launch.md#L88) — Test evidence: missing/stale/larger-authority and automatic-enable negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 371 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-02-T02`

### I1 / R1 — `LAUNCH-05-T01`

- Source: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L129)
- Dependencies: `INFRA-02-T02`
- Mode: `serial`
- Locks: `dependency-lockfiles`, `ci-release`
- Branch: `agent/launch-05-t01`
- Worktree: `../alon-ai-task-launch-05-t01`
- Acceptance evidence: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L129) — Test evidence: reproduction, mutated/mutable-only source, missing raw object/signature/ID/`NONE_FOUND`/timestamp/hash/final URL, transitive dependency, false-unaffected and missing-SBOM cases.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-05-T02`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 372 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-05-T01`

### I1 / R1 — `LAUNCH-05-T02`

- Source: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L131)
- Dependencies: `LAUNCH-05-T01`
- Mode: `serial`
- Locks: `dependency-lockfiles`, `ci-release`
- Branch: `agent/launch-05-t02`
- Worktree: `../alon-ai-task-launch-05-t02`
- Acceptance evidence: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L131) — Test evidence: floating/mutable tag, dirty tree, missing signature/license/advisory decision rejection.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-05-T03`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 373 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-05-T02`

### I1 / R1 — `LAUNCH-05-T03`

- Source: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L133)
- Dependencies: `LAUNCH-05-T02`
- Mode: `serial`
- Locks: `ci-release`
- Branch: `agent/launch-05-t03`
- Worktree: `../alon-ai-task-launch-05-t03`
- Acceptance evidence: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L133) — Test evidence: unavailable, partial, stale, incompatible and hard-safety negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-05-T04`, `SEC-04-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 374 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `INFRA-04-T02`, `INFRA-02-T04`, `LAUNCH-05-T03`

### I1 / R1 — `LAUNCH-05-T04`

- Source: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L135)
- Dependencies: `LAUNCH-05-T03`, `INFRA-02-T04`, `INFRA-04-T02`
- Mode: `serial`
- Locks: `ci-release`, `backup-restore`, `live-environment`
- Branch: `agent/launch-05-t04`
- Worktree: `../alon-ai-task-launch-05-t04`
- Acceptance evidence: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L135) — Test evidence: mid-migration/deploy, schema/runtime drift, alert, backup and authority-head failures.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-05-T05`, `SEC-04-T05`, `SEC-01-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 375 — M8

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-05-T04`

### I1 / R1 — `LAUNCH-05-T05`

- Source: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L137)
- Dependencies: `LAUNCH-05-T04`
- Mode: `serial`
- Locks: `ci-release`, `milestone-gate`
- Branch: `agent/launch-05-t05`
- Worktree: `../alon-ai-task-launch-05-t05`
- Acceptance evidence: [source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L137) — Test evidence: missed cadence, operator-unavailable, EOL and automatic-reenable negatives.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T05`, `SEC-01-T05`, `TEST-05-T05`, `LAUNCH-04-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 376 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-01-T02`, `SEC-05-T04`, `SEC-06-T02`, `SEC-04-T04`

### I1 / R1 — `SEC-04-T05`

- Source: [source](08-security-and-compliance/04-outreach-compliance.md#L105)
- Dependencies: `SEC-04-T04`, `PRODUCT-01-T02`, `SEC-06-T02`, `SEC-05-T04`
- Mode: `serial`
- Locks: `compliance-policy`, `milestone-gate`
- Branch: `agent/sec-04-t05`
- Worktree: `../alon-ai-task-sec-04-t05`
- Acceptance evidence: [source](08-security-and-compliance/04-outreach-compliance.md#L105) — Test evidence: scope/source/version/expiry completeness.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: none
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 377 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-01-T04`, `OBS-04-T05`, `INFRA-04-T06`, `LAUNCH-05-T04`

### I1 / R1 — `SEC-01-T05`

- Source: [source](08-security-and-compliance/01-threat-model.md#L127)
- Dependencies: `SEC-01-T04`, `OBS-04-T05`, `INFRA-04-T06`, `LAUNCH-05-T04`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/sec-01-t05`
- Worktree: `../alon-ai-task-sec-01-t05`
- Acceptance evidence: [source](08-security-and-compliance/01-threat-model.md#L127) — Test evidence: stale/missing evidence denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `PRODUCT-02-T04`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 378 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PRODUCT-02-T03`, `SEC-01-T05`

### I1 / R1 — `PRODUCT-02-T04`

- Source: [source](00-product-strategy/02-success-metrics.md#L148)
- Dependencies: `PRODUCT-02-T03`, `SEC-01-T05`
- Mode: `serial`
- Locks: `product-contracts`, `compliance-policy`, `milestone-gate`
- Branch: `agent/product-02-t04`
- Worktree: `../alon-ai-task-product-02-t04`
- Acceptance evidence: [source](00-product-strategy/02-success-metrics.md#L148) — Test evidence: audit query proves it predates the first send intent and boundary/race fixtures prove no later-stage admission without the prior authoritative `CONTINUE`.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: none
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 379 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-05-T04`, `SEC-04-T04`

### I1 / R1 — `TEST-05-T05`

- Source: [source](10-testing/05-end-to-end-browser-tests.md#L56)
- Dependencies: `TEST-05-T04`, `SEC-04-T04`
- Mode: `serial`
- Locks: `test-command-registry`, `frontend-client`
- Branch: `agent/test-05-t05`
- Worktree: `../alon-ai-task-test-05-t05`
- Acceptance evidence: [source](10-testing/05-end-to-end-browser-tests.md#L56) — Test evidence: no Next.js dependency or private data/route leakage.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-05-T06`, `LAUNCH-03-T01`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 380 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `TEST-01-T01`, `TEST-05-T05`

### I1 / R1 — `TEST-05-T06`

- Source: [source](10-testing/05-end-to-end-browser-tests.md#L58)
- Dependencies: `TEST-05-T05`, `TEST-01-T01`
- Mode: `serial`
- Locks: `test-command-registry`, `frontend-client`
- Branch: `agent/test-05-t06`
- Worktree: `../alon-ai-task-test-05-t06`
- Acceptance evidence: [source](10-testing/05-end-to-end-browser-tests.md#L58) — Test evidence: missing journey, swapped profile or unavailable environment denies gate.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: none
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 381 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `DB-02-T03`, `SEC-04-T02`, `SEC-05-T03`, `BACKEND-05-T05`, `PROVIDER-01-T03`, `LAUNCH-02-T05`, `SEC-04-T05`, `SEC-01-T05`, `PRODUCT-02-T04`, `TEST-05-T05`

### I1 / R1 — `LAUNCH-03-T01`

- Source: [source](12-launch-and-operations/03-first-real-experiment.md#L72)
- Dependencies: `LAUNCH-02-T05`, `SEC-01-T05`, `TEST-05-T05`, `DB-02-T03`, `BACKEND-05-T05`, `PROVIDER-01-T03`, `SEC-04-T02`, `SEC-05-T03`, `PRODUCT-02-T04`, `SEC-04-T05`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-03-t01`
- Worktree: `../alon-ai-task-launch-03-t01`
- Acceptance evidence: [source](12-launch-and-operations/03-first-real-experiment.md#L72) — Test evidence: missing/expired phase, larger cap, second program and raw identity exposure deny.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-03-T02`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 382 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `INFRA-03-T06`, `SEC-04-T04`, `SEC-04-T05`, `LAUNCH-03-T01`

### I1 / R1 — `LAUNCH-03-T02`

- Source: [source](12-launch-and-operations/03-first-real-experiment.md#L74)
- Dependencies: `LAUNCH-03-T01`, `INFRA-03-T06`, `BACKEND-02-T05`, `SEC-04-T04`, `SEC-04-T05`
- Mode: `serial`
- Locks: `live-environment`, `milestone-gate`
- Branch: `agent/launch-03-t02`
- Worktree: `../alon-ai-task-launch-03-t02`
- Acceptance evidence: [source](12-launch-and-operations/03-first-real-experiment.md#L74) — Test evidence: scanner write-zero, explicit POST replay, opaque errors and unsafe-dependency fallback.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `OBS-01-T07`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 383 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `OBS-01-T06`, `SEC-04-T04`, `LAUNCH-03-T02`

### I1 / R1 — `OBS-01-T07`

- Source: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L122)
- Dependencies: `OBS-01-T06`, `LAUNCH-03-T02`, `SEC-04-T04`
- Mode: `serial`
- Locks: `telemetry-catalog`, `live-environment`
- Branch: `agent/obs-01-t07`
- Worktree: `../alon-ai-task-obs-01-t07`
- Acceptance evidence: [source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L122) — Test evidence: GET write-zero, POST replay, token redaction, no private route exposure and fail-closed upstream/telemetry tests.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `TEST-06-T06`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 384 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-02-T05`, `TEST-06-T05`, `SEC-04-T04`, `LAUNCH-03-T02`, `OBS-01-T07`

### I1 / R1 — `TEST-06-T06`

- Source: [source](10-testing/06-load-security-and-chaos-tests.md#L70)
- Dependencies: `TEST-06-T05`, `LAUNCH-03-T02`, `BACKEND-02-T05`, `SEC-04-T04`, `OBS-01-T07`
- Mode: `serial`
- Locks: `test-command-registry`, `live-environment`
- Branch: `agent/test-06-t06`
- Worktree: `../alon-ai-task-test-06-t06`
- Acceptance evidence: [source](10-testing/06-load-security-and-chaos-tests.md#L70) — Test evidence: route equality, database writes, provider calls, events/telemetry, suppression, and dependency `PRODUCT_OUTREACH` fail-close counts.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-04-T06`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 385 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T04`, `OBS-03-T04`, `TEST-03-T06`, `SEC-04-T05`, `TEST-06-T06`

### I1 / R1 — `SEC-04-T06`

- Source: [source](08-security-and-compliance/04-outreach-compliance.md#L107)
- Dependencies: `SEC-04-T05`, `TEST-06-T06`, `SEC-05-T04`, `OBS-03-T04`, `TEST-03-T06`
- Mode: `serial`
- Locks: `milestone-gate`, `compliance-policy`
- Branch: `agent/sec-04-t06`
- Worktree: `../alon-ai-task-sec-04-t06`
- Acceptance evidence: [source](08-security-and-compliance/04-outreach-compliance.md#L107) — Test evidence: each missing, stale, spliced, reused-recipient, wrong-stage, over-cap, or escalated fact is denied, including active public-stop evidence gaps.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `SEC-05-T05`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 386 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-05-T04`, `TEST-03-T06`, `OBS-05-T06`, `SEC-04-T06`

### I1 / R1 — `SEC-05-T05`

- Source: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L115)
- Dependencies: `SEC-05-T04`, `SEC-04-T06`, `TEST-03-T06`, `OBS-05-T06`
- Mode: `serial`
- Locks: `security-runtime`, `milestone-gate`
- Branch: `agent/sec-05-t05`
- Worktree: `../alon-ai-task-sec-05-t05`
- Acceptance evidence: [source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L115) — Test evidence: each missing/stale condition, larger-cap request, and replay.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-03-T03`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 387 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `SEC-04-T02`, `SEC-05-T03`, `BACKEND-05-T03`, `BACKEND-03-T04`, `LAUNCH-03-T02`, `TEST-06-T06`, `SEC-04-T06`, `SEC-05-T05`

### I1 / R1 — `LAUNCH-03-T03`

- Source: [source](12-launch-and-operations/03-first-real-experiment.md#L76)
- Dependencies: `LAUNCH-03-T02`, `SEC-04-T02`, `BACKEND-05-T03`, `BACKEND-03-T04`, `SEC-05-T03`, `SEC-04-T06`, `SEC-05-T05`, `TEST-06-T06`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`
- Branch: `agent/launch-03-t03`
- Worktree: `../alon-ai-task-launch-03-t03`
- Acceptance evidence: [source](12-launch-and-operations/03-first-real-experiment.md#L76) — Test evidence: all current policy denials, final-slot races, terminal/rejection and no gateway bypass.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-03-T04`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 388 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T08`, `WF-07-T04`, `INFRA-04-T07`, `INFRA-05-T07`, `LAUNCH-03-T03`

### I1 / R1 — `LAUNCH-03-T04`

- Source: [source](12-launch-and-operations/03-first-real-experiment.md#L78)
- Dependencies: `LAUNCH-03-T03`, `INFRA-04-T07`, `INFRA-05-T07`, `BACKEND-01-T08`, `WF-07-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`, `live-environment`, `milestone-gate`, `calendar-side-effects`
- Branch: `agent/launch-03-t04`
- Worktree: `../alon-ai-task-launch-03-t04`
- Acceptance evidence: [source](12-launch-and-operations/03-first-real-experiment.md#L78) — Test evidence: DST/ambiguity/duplicate callbacks, rejection-vs-opt-out, floor and kill races.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-03-T05`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 389 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `BACKEND-01-T09`, `BACKEND-01-T10`, `WF-08-T04`, `WF-09-T04`, `LAUNCH-03-T04`

### I1 / R1 — `LAUNCH-03-T05`

- Source: [source](12-launch-and-operations/03-first-real-experiment.md#L80)
- Dependencies: `LAUNCH-03-T04`, `BACKEND-01-T09`, `BACKEND-01-T10`, `WF-08-T04`, `WF-09-T04`
- Mode: `serial`
- Locks: `gmail-side-effects`, `milestone-gate`
- Branch: `agent/launch-03-t05`
- Worktree: `../alon-ai-task-launch-03-t05`
- Acceptance evidence: [source](12-launch-and-operations/03-first-real-experiment.md#L80) — Test evidence: weak evidence, cross-campaign timing, late data, active-cohort mutation and fifth-cohort denial.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: none
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 390 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `PROVIDER-01-T01`, `PROVIDER-02-T01`, `AGENT-01-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `WF-03-T05`, `WF-04-T05`, `SEC-05-T03`, `WF-02-T05`

### I1 / R1 — `LAUNCH-04-T01`

- Source: [source](12-launch-and-operations/04-earned-autonomy.md#L66)
- Dependencies: `AGENT-01-T01`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `SEC-05-T03`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-01-T01`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-04-t01`
- Worktree: `../alon-ai-task-launch-04-t01`
- Acceptance evidence: [source](12-launch-and-operations/04-earned-autonomy.md#L66) — Test evidence: skipped phase, new source/program, unregistered action and cap expansion deny.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T02`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 391 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-04-T01`

### I1 / R1 — `LAUNCH-04-T02`

- Source: [source](12-launch-and-operations/04-earned-autonomy.md#L68)
- Dependencies: `LAUNCH-04-T01`
- Mode: `serial`
- Locks: `milestone-gate`
- Branch: `agent/launch-04-t02`
- Worktree: `../alon-ai-task-launch-04-t02`
- Acceptance evidence: [source](12-launch-and-operations/04-earned-autonomy.md#L68) — Test evidence: post-hoc exclusion, stale costs, unknown attendance and weak evidence cannot pass.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T03`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 392 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `AGENT-10-T05`, `BACKEND-01-T08`, `BACKEND-01-T10`, `WF-09-T04`, `INFRA-02-T04`, `OBS-04-T05`, `OBS-05-T06`, `LAUNCH-02-T05`, `LAUNCH-03-T05`, `LAUNCH-04-T02`

### I1 / R1 — `LAUNCH-04-T03`

- Source: [source](12-launch-and-operations/04-earned-autonomy.md#L70)
- Dependencies: `LAUNCH-04-T02`, `LAUNCH-03-T05`, `AGENT-10-T05`, `LAUNCH-02-T05`, `OBS-04-T05`, `OBS-05-T06`, `INFRA-02-T04`, `BACKEND-01-T08`, `BACKEND-01-T10`, `WF-09-T04`
- Mode: `serial`
- Locks: `milestone-gate`, `calendar-side-effects`
- Branch: `agent/launch-04-t03`
- Worktree: `../alon-ai-task-launch-04-t03`
- Acceptance evidence: [source](12-launch-and-operations/04-earned-autonomy.md#L70) — Test evidence: per-message gate absent, sole gateways intact, no mid-cohort change or fifth cohort.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T04`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 393 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-04-T03`

### I1 / R1 — `LAUNCH-04-T04`

- Source: [source](12-launch-and-operations/04-earned-autonomy.md#L72)
- Dependencies: `LAUNCH-04-T03`
- Mode: `serial`
- Locks: `security-runtime`, `milestone-gate`
- Branch: `agent/launch-04-t04`
- Worktree: `../alon-ai-task-launch-04-t04`
- Acceptance evidence: [source](12-launch-and-operations/04-earned-autonomy.md#L72) — Test evidence: agents/browser/provider wrapper cannot bypass deterministic owners.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: `LAUNCH-04-T05`
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Wave 394 — M9

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: `LAUNCH-04-T04`

### I1 / R1 — `LAUNCH-04-T05`

- Source: [source](12-launch-and-operations/04-earned-autonomy.md#L74)
- Dependencies: `LAUNCH-04-T04`
- Mode: `serial`
- Locks: `ci-release`, `milestone-gate`
- Branch: `agent/launch-04-t05`
- Worktree: `../alon-ai-task-launch-04-t05`
- Acceptance evidence: [source](12-launch-and-operations/04-earned-autonomy.md#L74) — Test evidence: cross-campaign race, weak evidence, crash/replay and incompatible rollback remain safe.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: none
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Cross-document edge appendix

- Provider `PRODUCT-01-T02` — Output: pass or a smaller brief.; Consumer `PRODUCT-02-T01` — Input: this file and the approved `ExperimentBrief`.
- Provider `PRODUCT-01-T02` — Output: pass or a smaller brief.; Consumer `PRODUCT-03-T01` — Input: scope, metrics, risk table.
- Provider `PRODUCT-02-T01` — Output: immutable metric registry and `StagedValidationRuleV1` contract for M2 consumers.; Consumer `PRODUCT-03-T01` — Input: scope, metrics, risk table.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `WF-00-T01` — Input: PRODUCT-01 frozen artifact/authority vocabulary crosswalk, architecture/ADR, and official runtime sources above.
- Provider `PRODUCT-03-T01` — Output: signed risk register.; Consumer `SEC-01-T01` — Input: approved M0 scope/risk posture and the document-local static planned product-table, security-runtime/session, provider/agent/Gmail/runtime/backup/telemetry contracts.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `DB-03-T01` — Input: the PRODUCT-01 vocabulary crosswalk, SEC-01 Critical send/credential interface, and the document-local DB-03 table/state contract.
- Provider `SEC-01-T01` — Output: signed planned asset/boundary registry plus approved Critical credential/send threat-control interface.; Consumer `DB-03-T01` — Input: the PRODUCT-01 vocabulary crosswalk, SEC-01 Critical send/credential interface, and the document-local DB-03 table/state contract.
- Provider `SEC-01-T01` — Output: signed planned asset/boundary registry plus approved Critical credential/send threat-control interface.; Consumer `SEC-03-T01` — Input: secret classes, key hierarchy, canonical AAD, CAS/lease states.
- Provider `DB-03-T01` — Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence.; Consumer `PROVIDER-01-T01` — Input: DB-03 pure composite wire/authority contracts, SEC-03 strict key/object contracts, and document-local Gmail request/result/error/MIME/history/flow specifications with recorded credential fixtures.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `PROVIDER-01-T01` — Input: DB-03 pure composite wire/authority contracts, SEC-03 strict key/object contracts, and document-local Gmail request/result/error/MIME/history/flow specifications with recorded credential fixtures.
- Provider `DB-03-T01` — Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence.; Consumer `PROVIDER-01-T02` — Input: DB-03 composite intent/attempt and encrypted message fields.
- Provider `PROVIDER-01-T01` — Output: versioned Gmail OAuth/credential-binding/request/result/error/MIME/history contract bundle and signed disposable fixtures.; Consumer `PROVIDER-02-T01` — Input: the PROVIDER-01 pure Gmail credential-binding/request/history contract bundle and signed recorded mailbox-bound credential/request fixtures.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `TEST-01-T01` — Input: the PRODUCT-01 vocabulary crosswalk, canonical roadmap source documents, and exact document-local TEST-02..06 matrices.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `TEST-04-T01` — Input: PROVIDER-01/02 request/result/error/MIME/history contracts and TEST-01 reproducible clean test contexts.
- Provider `TEST-01-T03` — Output: reproducible clean test contexts.; Consumer `TEST-04-T01` — Input: PROVIDER-01/02 request/result/error/MIME/history contracts and TEST-01 reproducible clean test contexts.
- Provider `PROVIDER-01-T01` — Output: versioned Gmail OAuth/credential-binding/request/result/error/MIME/history contract bundle and signed disposable fixtures.; Consumer `TEST-04-T01` — Input: PROVIDER-01/02 request/result/error/MIME/history contracts and TEST-01 reproducible clean test contexts.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `TEST-04-T02` — Input: deterministic provider simulator, PROVIDER-01 signed disposable OAuth/wire fixtures, document-local offline Gmail matrix, and TEST-01 signed task7-commands.v1.json.
- Provider `PROVIDER-01-T01` — Output: versioned Gmail OAuth/credential-binding/request/result/error/MIME/history contract bundle and signed disposable fixtures.; Consumer `TEST-04-T02` — Input: deterministic provider simulator, PROVIDER-01 signed disposable OAuth/wire fixtures, document-local offline Gmail matrix, and TEST-01 signed task7-commands.v1.json.
- Provider `WF-00-T01` — Output: runtime-neutral interface and forbidden-import rules.; Consumer `WF-01-T01` — Input: the WF-00 runtime-neutral acceptance contract, SEC-01 Critical credential/send threat-control interface, and an operator-attested external manifest naming a separate Gmail project, approved scopes, owned mailbox/aliases, opaque credential references, fresh PostgreSQL instance, pinned build version/hash, pinned fixtures, TEST-01 signed command/coverage conventions, clean isolated test contexts, and auditable evidence-capture conventions.
- Provider `SEC-01-T01` — Output: signed planned asset/boundary registry plus approved Critical credential/send threat-control interface.; Consumer `WF-01-T01` — Input: the WF-00 runtime-neutral acceptance contract, SEC-01 Critical credential/send threat-control interface, and an operator-attested external manifest naming a separate Gmail project, approved scopes, owned mailbox/aliases, opaque credential references, fresh PostgreSQL instance, pinned build version/hash, pinned fixtures, TEST-01 signed command/coverage conventions, clean isolated test contexts, and auditable evidence-capture conventions.
- Provider `TEST-01-T01` — Output: signed `coverage.v1.json`.; Consumer `WF-01-T01` — Input: the WF-00 runtime-neutral acceptance contract, SEC-01 Critical credential/send threat-control interface, and an operator-attested external manifest naming a separate Gmail project, approved scopes, owned mailbox/aliases, opaque credential references, fresh PostgreSQL instance, pinned build version/hash, pinned fixtures, TEST-01 signed command/coverage conventions, clean isolated test contexts, and auditable evidence-capture conventions.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `WF-01-T01` — Input: the WF-00 runtime-neutral acceptance contract, SEC-01 Critical credential/send threat-control interface, and an operator-attested external manifest naming a separate Gmail project, approved scopes, owned mailbox/aliases, opaque credential references, fresh PostgreSQL instance, pinned build version/hash, pinned fixtures, TEST-01 signed command/coverage conventions, clean isolated test contexts, and auditable evidence-capture conventions.
- Provider `TEST-01-T03` — Output: reproducible clean test contexts.; Consumer `WF-01-T01` — Input: the WF-00 runtime-neutral acceptance contract, SEC-01 Critical credential/send threat-control interface, and an operator-attested external manifest naming a separate Gmail project, approved scopes, owned mailbox/aliases, opaque credential references, fresh PostgreSQL instance, pinned build version/hash, pinned fixtures, TEST-01 signed command/coverage conventions, clean isolated test contexts, and auditable evidence-capture conventions.
- Provider `TEST-01-T04` — Output: versioned evidence-capture/convention contract and auditable pass/fail bundle.; Consumer `WF-01-T01` — Input: the WF-00 runtime-neutral acceptance contract, SEC-01 Critical credential/send threat-control interface, and an operator-attested external manifest naming a separate Gmail project, approved scopes, owned mailbox/aliases, opaque credential references, fresh PostgreSQL instance, pinned build version/hash, pinned fixtures, TEST-01 signed command/coverage conventions, clean isolated test contexts, and auditable evidence-capture conventions.
- Provider `WF-01-T03` — Output: reproducible crash harness.; Consumer `PRODUCT-03-T03` — Input: the signed risk register, WF-01 reproducible crash harness, and the document-local active-trigger catalog.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `ARCH-01-T01` — Input: disposable `m1_spike` schema, Pydantic AI typed fixture, test-inbox fixtures, and kill-point matrix; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T02` — Output: runnable no-branch workflow.; Consumer `ARCH-01-T01` — Input: disposable `m1_spike` schema, Pydantic AI typed fixture, test-inbox fixtures, and kill-point matrix; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T03` — Output: reproducible crash harness.; Consumer `ARCH-01-T01` — Input: disposable `m1_spike` schema, Pydantic AI typed fixture, test-inbox fixtures, and kill-point matrix; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `WF-00-T02` — Input: pinned build, disposable schema, fixtures, kill matrix, test inboxes; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T02` — Output: runnable no-branch workflow.; Consumer `WF-00-T02` — Input: pinned build, disposable schema, fixtures, kill matrix, test inboxes; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T03` — Output: reproducible crash harness.; Consumer `WF-00-T02` — Input: pinned build, disposable schema, fixtures, kill matrix, test inboxes; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `TEST-03-T01` — Input: runtime adapter, scenario/barrier manifest and fresh database.
- Provider `WF-01-T02` — Output: runnable no-branch workflow.; Consumer `TEST-03-T01` — Input: runtime adapter, scenario/barrier manifest and fresh database.
- Provider `WF-01-T03` — Output: reproducible crash harness.; Consumer `TEST-03-T01` — Input: runtime adapter, scenario/barrier manifest and fresh database.
- Provider `TEST-01-T03` — Output: reproducible clean test contexts.; Consumer `TEST-03-T01` — Input: runtime adapter, scenario/barrier manifest and fresh database.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `TEST-03-T02` — Input: WF-01 disposable schema, runnable typed fixture, K0-K8 crash harness, exact repetition/version manifest, and TEST-01 signed evidence conventions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T02` — Output: runnable no-branch workflow.; Consumer `TEST-03-T02` — Input: WF-01 disposable schema, runnable typed fixture, K0-K8 crash harness, exact repetition/version manifest, and TEST-01 signed evidence conventions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T03` — Output: reproducible crash harness.; Consumer `TEST-03-T02` — Input: WF-01 disposable schema, runnable typed fixture, K0-K8 crash harness, exact repetition/version manifest, and TEST-01 signed evidence conventions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-01-T04` — Output: versioned evidence-capture/convention contract and auditable pass/fail bundle.; Consumer `TEST-03-T02` — Input: WF-01 disposable schema, runnable typed fixture, K0-K8 crash harness, exact repetition/version manifest, and TEST-01 signed evidence conventions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-03-T02` — Output: signed independent raw run/scorecard evidence, including terminal/reconciled state or explicitly identified unresolved isolated state and DBOS rejection reasons.; Consumer `WF-01-T05` — Input: WF-01 raw evidence/scorecard and TEST-03 independent raw run/scorecard, including exact terminal/reconciled or explicitly unresolved isolated-state inventory; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T05` — Output: interoperable gate bundle with no promoted product data.; Consumer `TEST-03-T03` — Input: WF-01 interoperable exported gate bundle and TEST-03 independent raw traces/scorecard with exact schema/fixture/K0-K8/repetition identities; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-03-T03` — Output: independently checked complete signed M1 acceptance-or-rejection evidence manifest, with DBOS acceptance only on 8/8.; Consumer `WF-00-T03` — Input: the complete independently checked WF-01 and TEST-03 evidence manifests; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T05` — Output: interoperable gate bundle with no promoted product data.; Consumer `WF-00-T03` — Input: the complete independently checked WF-01 and TEST-03 evidence manifests; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `WF-01-T06` — Input: the local interoperable gate bundle and WF-00 signed `SelectedRuntimeDecisionV1`; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `INFRA-01-T01` — Input: lockfiles, runtime floors, repository root, environment enum and TEST-01 signed task7-commands.v1.json checkout/root/profile contract.
- Provider `TEST-01-T01` — Output: signed `coverage.v1.json`.; Consumer `INFRA-01-T05` — Input: implemented M1 foundation setup/smoke/reset requirements and TEST-01 signed coverage/command registries.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `INFRA-01-T05` — Input: implemented M1 foundation setup/smoke/reset requirements and TEST-01 signed coverage/command registries.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `ARCH-03-T01` — Input: the PRODUCT-01 signed vocabulary crosswalk and the document-local canonical state/guard catalog.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `ARCH-03-T03` — Input: WF-00 signed `SelectedRuntimeDecisionV1` naming the accepted DBOS runtime or validated mandatory Temporal fallback.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `DB-01-T01` — Input: ARCH-03 enums and identifier rules.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `ARCH-02-T01` — Input: ARCH-03 names and M2 schema.
- Provider `DB-01-T02` — Output: fresh PostgreSQL schema.; Consumer `ARCH-02-T01` — Input: ARCH-03 names and M2 schema.
- Provider `ARCH-02-T01` — Output: stable interfaces.; Consumer `ARCH-01-T02` — Input: ARCH-02/03 contracts; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `ARCH-01-T02` — Input: ARCH-02/03 contracts; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `ARCH-02-T02` — Input: domain aggregates, events, idempotent command envelope.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `DB-01-T04` — Input: WF-00 signed `SelectedRuntimeDecisionV1` naming the accepted DBOS adapter or the validated mandatory Temporal adapter.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `DB-02-T01` — Input: M0 artifact/metric contracts and PRODUCT-02 `100/200/300/400` staged rule.
- Provider `PRODUCT-02-T01` — Output: immutable metric registry and `StagedValidationRuleV1` contract for M2 consumers.; Consumer `DB-02-T01` — Input: M0 artifact/metric contracts and PRODUCT-02 `100/200/300/400` staged rule.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `DB-03-T02` — Input: canonicalization rules and ARCH-03 `LeadState`.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `DB-04-T01` — Input: canonical artifact names and Pydantic AI boundary.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `DB-05-T01` — Input: every ARCH-03 `.v1` name/payload.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `DB-03-T03` — Input: the final DB-03 wire/authority contracts, PRODUCT-02 stage tuples, ARCH-03 lead/campaign/action authorization states, DB-05 policy-table and foreign-key constraints, and document-local canonicalization and static policy rules.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `DB-03-T03` — Input: the final DB-03 wire/authority contracts, PRODUCT-02 stage tuples, ARCH-03 lead/campaign/action authorization states, DB-05 policy-table and foreign-key constraints, and document-local canonicalization and static policy rules.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `DB-03-T04` — Input: ARCH-03 message transitions.
- Provider `DB-01-T02` — Output: fresh PostgreSQL schema.; Consumer `DB-06-T01` — Input: DB-01 through DB-05 exact tables/constraints.
- Provider `DB-02-T02` — Output: empty M2 schema.; Consumer `DB-06-T01` — Input: DB-01 through DB-05 exact tables/constraints.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `DB-06-T01` — Input: DB-01 through DB-05 exact tables/constraints.
- Provider `DB-04-T02` — Output: M2 schema.; Consumer `DB-06-T01` — Input: DB-01 through DB-05 exact tables/constraints.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `DB-06-T01` — Input: DB-01 through DB-05 exact tables/constraints.
- Provider `PRODUCT-01-T03` — Output: immutable vocabulary crosswalk consumed by architecture, data, agents, workflows, providers, services, and UI.; Consumer `SEC-06-T01` — Input: M0 product vocabulary, the consolidated M2 schema/contracts, and the document-local known provider/agent/Gmail/telemetry surfaces.
- Provider `DB-06-T01` — Output: fresh schema.; Consumer `SEC-06-T01` — Input: M0 product vocabulary, the consolidated M2 schema/contracts, and the document-local known provider/agent/Gmail/telemetry surfaces.
- Provider `DB-01-T02` — Output: fresh PostgreSQL schema.; Consumer `AGENT-01-T01` — Input: DB-01/04 schemas and the models above.
- Provider `DB-04-T02` — Output: M2 schema.; Consumer `AGENT-01-T01` — Input: DB-01/04 schemas and the models above.
- Provider `DB-02-T03` — Output: versioned brief/idea/offer.; Consumer `AGENT-10-T01` — Input: exact suite/case/adversarial allocations, DB-02 versioned brief/idea/offer, DB-03 identity/reply schemas, DB-04 serializable contracts, and the document-local static M3 fixture/rule definitions.
- Provider `DB-03-T03` — Output: deterministic staged admission substrate over the separately migrated identity/lead schema.; Consumer `AGENT-10-T01` — Input: exact suite/case/adversarial allocations, DB-02 versioned brief/idea/offer, DB-03 identity/reply schemas, DB-04 serializable contracts, and the document-local static M3 fixture/rule definitions.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `AGENT-10-T01` — Input: exact suite/case/adversarial allocations, DB-02 versioned brief/idea/offer, DB-03 identity/reply schemas, DB-04 serializable contracts, and the document-local static M3 fixture/rule definitions.
- Provider `DB-04-T01` — Output: serializable contracts.; Consumer `AGENT-10-T01` — Input: exact suite/case/adversarial allocations, DB-02 versioned brief/idea/offer, DB-03 identity/reply schemas, DB-04 serializable contracts, and the document-local static M3 fixture/rule definitions.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-01-T02` — Input: AGENT-10 signed static candidate parameter templates and the document-local specialist capability list; exact code-bound configurations are frozen before later capture.
- Provider `DB-02-T01` — Output: domain values and migration model.; Consumer `AGENT-02-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-04-T01` — Output: serializable contracts.; Consumer `AGENT-02-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-02-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-02-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-02-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-02-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-04-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-04-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-04-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-04-T01` — Output: serializable contracts.; Consumer `AGENT-04-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-04-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-02-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-03-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-04-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-03-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-03-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-03-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-02-T03` — Output: versioned brief/idea/offer.; Consumer `AGENT-03-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-03-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-03-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-11-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-11-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-11-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-03-T03` — Output: deterministic staged admission substrate over the separately migrated identity/lead schema.; Consumer `AGENT-11-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-11-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-11-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-05-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-05-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-05-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-03-T03` — Output: deterministic staged admission substrate over the separately migrated identity/lead schema.; Consumer `AGENT-05-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-05-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-03-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-06-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-05-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-06-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-06-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-06-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-03-T03` — Output: deterministic staged admission substrate over the separately migrated identity/lead schema.; Consumer `AGENT-06-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-06-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-03-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-07-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-05-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-07-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-06-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-07-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-07-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-07-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `AGENT-07-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-07-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-03-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-08-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-07-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-08-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-08-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-08-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `AGENT-08-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-08-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-03-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-09-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-09-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-09-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-02-T04` — Output: reproducible decision input.; Consumer `AGENT-09-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-04-T01` — Output: serializable contracts.; Consumer `AGENT-09-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-09-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-09-T01` — Output: importable contract and schema registry entry.; Consumer `AGENT-12-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `AGENT-12-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-12-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `DB-04-T01` — Output: serializable contracts.; Consumer `AGENT-12-T01` — Input: canonical upstream artifact contracts and signed shared fixture templates.
- Provider `AGENT-01-T02` — Output: immutable `AgentDependenciesV1`.; Consumer `AGENT-12-T02` — Input: verified runtime envelope and exact scoped capabilities.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `PROVIDER-03-T01` — Input: AGENT-01 family and DB-01 canonicalizer.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `PROVIDER-03-T01` — Input: AGENT-01 family and DB-01 canonicalizer.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `PROVIDER-04-T01` — Input: AGENT-01 models and DB-01 canonicalizer.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `PROVIDER-04-T01` — Input: AGENT-01 models and DB-01 canonicalizer.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `PROVIDER-05-T01` — Input: AGENT-01 families and DB-01 canonicalizer.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `PROVIDER-05-T01` — Input: AGENT-01 families and DB-01 canonicalizer.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `DB-04-T03` — Input: strict PROVIDER-05 URI/result contracts, migrated evidence schema and signed bounded synthetic provider-result fixtures.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `PROVIDER-06-T01` — Input: AGENT-01 models and DB-01 canonicalizer.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `PROVIDER-06-T01` — Input: AGENT-01 models and DB-01 canonicalizer.
- Provider `ARCH-02-T01` — Output: stable interfaces.; Consumer `PROVIDER-07-T01` — Input: canonical booking states/authority and provider-neutral types.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `PROVIDER-07-T01` — Input: canonical booking states/authority and provider-neutral types.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `PROVIDER-08-T01` — Input: shared strict provider contracts and canonical discovery scope.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `PROVIDER-08-T01` — Input: shared strict provider contracts and canonical discovery scope.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `BACKEND-01-T01` — Input: AGENT-01 strict terminal/provider contracts, DB-04 artifact/evidence schema and DB-05 atomic command replay implementation; signed synthetic terminal and evaluation fixtures.
- Provider `DB-04-T02` — Output: M2 schema.; Consumer `BACKEND-01-T01` — Input: AGENT-01 strict terminal/provider contracts, DB-04 artifact/evidence schema and DB-05 atomic command replay implementation; signed synthetic terminal and evaluation fixtures.
- Provider `DB-05-T03` — Output: implemented versioned IdempotentCommandExecutor atomic claim/replay/UnitOfWork interface plus one command effect.; Consumer `BACKEND-01-T01` — Input: AGENT-01 strict terminal/provider contracts, DB-04 artifact/evidence schema and DB-05 atomic command replay implementation; signed synthetic terminal and evaluation fixtures.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `DB-04-T04` — Input: `PRODUCED` artifact and frozen validator/gate; implemented ArtifactCommandService PRODUCED/event interface and canonical artifact state/guard contract.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `DB-04-T04` — Input: `PRODUCED` artifact and frozen validator/gate; implemented ArtifactCommandService PRODUCED/event interface and canonical artifact state/guard contract.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `BACKEND-03-T01` — Input: DB-03 ActionAuthorityScopeV1, DB-05 policy and canonical offer/cohort/strategy contracts.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `BACKEND-03-T01` — Input: DB-03 ActionAuthorityScopeV1, DB-05 policy and canonical offer/cohort/strategy contracts.
- Provider `DB-03-T01` — Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence.; Consumer `BACKEND-03-T01` — Input: DB-03 ActionAuthorityScopeV1, DB-05 policy and canonical offer/cohort/strategy contracts.
- Provider `SEC-06-T01` — Output: versioned early privacy/minimization/redaction/retention-class contract.; Consumer `OBS-01-T01` — Input: exact allowlist/denylist and current foundation logs.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `PROVIDER-04-T01` — Output: `MarketSearchPort`.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `PROVIDER-06-T01` — Output: provider-neutral port plus disabled adapter.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `PROVIDER-01-T01` — Output: versioned Gmail OAuth/credential-binding/request/result/error/MIME/history contract bundle and signed disposable fixtures.; Consumer `OBS-03-T01` — Input: exact provider contracts and official price manifests.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `OBS-03-T02` — Input: budget account, provider call/result/ledger/price, DB-05's exact allocation branches and existing action attribution.
- Provider `PROVIDER-03-T04` — Output: deterministic evaluation input.; Consumer `DB-05-T05` — Input: frozen facts/provider usage.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `DB-05-T05` — Input: frozen facts/provider usage.
- Provider `DB-05-T05` — Output: explainable gate and cost ledger.; Consumer `PRODUCT-02-T03` — Input: event/audit/cost records introduced from M2 onward.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-01-T03` — Input: verified typed envelope fixtures, reserved cost-chain fixture and static candidate parameter fixture in an evaluation-only authority context; product invocation later requires an immutable promotion binding.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-01-T04` — Input: terminal result and ledger; implemented recording/PRODUCED-insertion, artifact-validation/acceptance and cost-reconciliation service interfaces.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-01-T04` — Input: terminal result and ledger; implemented recording/PRODUCED-insertion, artifact-validation/acceptance and cost-reconciliation service interfaces.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-01-T04` — Input: terminal result and ledger; implemented recording/PRODUCED-insertion, artifact-validation/acceptance and cost-reconciliation service interfaces.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-02-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-02-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-02-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-02-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-03-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-03-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-03-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-03-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `AGENT-03-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-06-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-06-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-06-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-06-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-07-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-07-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-07-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-07-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-08-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-08-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-08-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-08-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `AGENT-08-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-09-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-09-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-09-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-09-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-12-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-12-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-12-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-12-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `PROVIDER-04-T03` — Input: eligible raw results, and OBS-03 complete reservation/reconciliation cost chain; implemented EvidenceIngestService sole-writer interface.
- Provider `DB-04-T03` — Output: implemented versioned EvidenceIngestService interface and provenance-complete fixture evidence.; Consumer `PROVIDER-04-T03` — Input: eligible raw results, and OBS-03 complete reservation/reconciliation cost chain; implemented EvidenceIngestService sole-writer interface.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `PROVIDER-05-T03` — Input: strict URI/source policy/reservation; implemented EvidenceIngestService sole-writer interface.
- Provider `DB-04-T03` — Output: implemented versioned EvidenceIngestService interface and provenance-complete fixture evidence.; Consumer `PROVIDER-05-T03` — Input: strict URI/source policy/reservation; implemented EvidenceIngestService sole-writer interface.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-04-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-04-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-04-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-04-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-04-T04` — Output: M3 evaluation inputs.; Consumer `AGENT-04-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-05-T04` — Output: deterministic evaluation data.; Consumer `AGENT-04-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-04-T03` — Output: evidence-backed response.; Consumer `PROVIDER-06-T02` — Input: frozen candidate evidence.
- Provider `PROVIDER-03-T04` — Output: deterministic evaluation input.; Consumer `ARCH-02-T03` — Input: the model, search, page, enrichment, approved discovery, Gmail read/write, and calendar read/write ports plus deterministic recorded fixtures and the Gmail simulator.
- Provider `PROVIDER-04-T04` — Output: M3 evaluation inputs.; Consumer `ARCH-02-T03` — Input: the model, search, page, enrichment, approved discovery, Gmail read/write, and calendar read/write ports plus deterministic recorded fixtures and the Gmail simulator.
- Provider `PROVIDER-05-T04` — Output: deterministic evaluation data.; Consumer `ARCH-02-T03` — Input: the model, search, page, enrichment, approved discovery, Gmail read/write, and calendar read/write ports plus deterministic recorded fixtures and the Gmail simulator.
- Provider `PROVIDER-06-T03` — Output: deterministic M3 enrichment fixture containing frozen provider result/meta/usage plus replacement evidence.; Consumer `ARCH-02-T03` — Input: the model, search, page, enrichment, approved discovery, Gmail read/write, and calendar read/write ports plus deterministic recorded fixtures and the Gmail simulator.
- Provider `TEST-04-T01` — Output: deterministic provider simulator.; Consumer `ARCH-02-T03` — Input: the model, search, page, enrichment, approved discovery, Gmail read/write, and calendar read/write ports plus deterministic recorded fixtures and the Gmail simulator.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-05-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-05-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-05-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-05-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-05-T04` — Output: deterministic evaluation data.; Consumer `AGENT-05-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-06-T03` — Output: deterministic M3 enrichment fixture containing frozen provider result/meta/usage plus replacement evidence.; Consumer `AGENT-05-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-05-T03` — Output: capture-backed page payload.; Consumer `PROVIDER-08-T03` — Input: source fixtures and EvidenceIngestService interface.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-11-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-11-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `AGENT-11-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-11-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `PROVIDER-08-T03` — Output: signed discovery capability fixtures for AGENT-11 and AGENT-10.; Consumer `AGENT-11-T03` — Input: terminal outputs, implemented shared recording/validation/cost services and signed fixture rows.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `PROVIDER-03-T04` — Output: deterministic evaluation input.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `PROVIDER-04-T04` — Output: M3 evaluation inputs.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `PROVIDER-05-T04` — Output: deterministic evaluation data.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `PROVIDER-06-T03` — Output: deterministic M3 enrichment fixture containing frozen provider result/meta/usage plus replacement evidence.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-02-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-03-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-04-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-05-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-06-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-07-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-08-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-09-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-11-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `AGENT-12-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `PROVIDER-08-T03` — Output: signed discovery capability fixtures for AGENT-11 and AGENT-10.; Consumer `AGENT-10-T02` — Input: signed static suite/fixture templates; completed AGENT-02..09/11/12 specialist implementation/configuration identities; recorded model/search/page/business fixtures; AGENT-01 typed capability contracts.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `AGENT-10-T03` — Input: AGENT-01 terminal/provider schemas, the final AGENT-10 suite cases and exact candidate configuration, signed non-model fixture manifest, and reserved three-repetition budget, and AGENT-01 tested terminal-result persistence handoff integration contract; signed exact implemented candidate configuration manifest and executable isolated candidate-model adapter; implemented AgentRunRecordingService start/close interface from the M3 shared-service owner.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `AGENT-10-T03` — Input: AGENT-01 terminal/provider schemas, the final AGENT-10 suite cases and exact candidate configuration, signed non-model fixture manifest, and reserved three-repetition budget, and AGENT-01 tested terminal-result persistence handoff integration contract; signed exact implemented candidate configuration manifest and executable isolated candidate-model adapter; implemented AgentRunRecordingService start/close interface from the M3 shared-service owner.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `AGENT-10-T03` — Input: AGENT-01 terminal/provider schemas, the final AGENT-10 suite cases and exact candidate configuration, signed non-model fixture manifest, and reserved three-repetition budget, and AGENT-01 tested terminal-result persistence handoff integration contract; signed exact implemented candidate configuration manifest and executable isolated candidate-model adapter; implemented AgentRunRecordingService start/close interface from the M3 shared-service owner.
- Provider `AGENT-01-T04` — Output: tested versioned terminal-result persistence/validation handoff integration contract and immutable reviewable artifact or retained failed-run evidence.; Consumer `AGENT-10-T03` — Input: AGENT-01 terminal/provider schemas, the final AGENT-10 suite cases and exact candidate configuration, signed non-model fixture manifest, and reserved three-repetition budget, and AGENT-01 tested terminal-result persistence handoff integration contract; signed exact implemented candidate configuration manifest and executable isolated candidate-model adapter; implemented AgentRunRecordingService start/close interface from the M3 shared-service owner.
- Provider `PROVIDER-03-T02` — Output: executable isolated candidate-model adapter and exact result union; no promoted product activation.; Consumer `AGENT-10-T03` — Input: AGENT-01 terminal/provider schemas, the final AGENT-10 suite cases and exact candidate configuration, signed non-model fixture manifest, and reserved three-repetition budget, and AGENT-01 tested terminal-result persistence handoff integration contract; signed exact implemented candidate configuration manifest and executable isolated candidate-model adapter; implemented AgentRunRecordingService start/close interface from the M3 shared-service owner.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `AGENT-10-T03` — Input: AGENT-01 terminal/provider schemas, the final AGENT-10 suite cases and exact candidate configuration, signed non-model fixture manifest, and reserved three-repetition budget, and AGENT-01 tested terminal-result persistence handoff integration contract; signed exact implemented candidate configuration manifest and executable isolated candidate-model adapter; implemented AgentRunRecordingService start/close interface from the M3 shared-service owner.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-02-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-02-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-04-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-04-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-03-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-03-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-11-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-11-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-05-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-05-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-06-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-06-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-07-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-07-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-08-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-08-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-09-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-09-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `AGENT-12-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `AGENT-12-T04` — Input: AGENT-10 signed three-capture sets and deterministic scores for the exact declared suite.
- Provider `AGENT-02-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-03-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-04-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-05-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-06-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-07-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-08-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-09-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-11-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-12-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `AGENT-10-T05` — Input: signed candidate/baseline capture manifests, three full repetition summaries, suite summary, dependency/authority/cost evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `DB-04-T05` — Input: the AGENT-10 immutable evaluation/configuration decision binding suite identity, PromotionManifestV1 and registry version.
- Provider `ARCH-02-T01` — Output: stable interfaces.; Consumer `ARCH-01-T03` — Input: product records and provider ports; completed immutable promotion decision, persisted registry evidence and replaceable recorded provider boundaries.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `ARCH-01-T03` — Input: product records and provider ports; completed immutable promotion decision, persisted registry evidence and replaceable recorded provider boundaries.
- Provider `DB-04-T05` — Output: persisted immutable promotion decision and DB registry evidence.; Consumer `ARCH-01-T03` — Input: product records and provider ports; completed immutable promotion decision, persisted registry evidence and replaceable recorded provider boundaries.
- Provider `ARCH-02-T03` — Output: replaceable M3 provider adapter boundaries with no live authority.; Consumer `ARCH-01-T03` — Input: product records and provider ports; completed immutable promotion decision, persisted registry evidence and replaceable recorded provider boundaries.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `PROVIDER-03-T05` — Input: implemented candidate adapter, recorded fixture compatibility, and AGENT-10 immutable approved PromotionManifestV1/configuration/registry binding; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `WF-03-T01` — Input: canonical IdeaBrief and accepted scope.
- Provider `DB-02-T03` — Output: versioned brief/idea/offer.; Consumer `WF-03-T01` — Input: canonical IdeaBrief and accepted scope.
- Provider `DB-02-T04` — Output: reproducible decision input.; Consumer `WF-03-T01` — Input: canonical IdeaBrief and accepted scope.
- Provider `PRODUCT-02-T01` — Output: immutable metric registry and `StagedValidationRuleV1` contract for M2 consumers.; Consumer `WF-03-T01` — Input: canonical IdeaBrief and accepted scope.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `BACKEND-01-T02` — Input: ARCH-03 enums/guards/events and DB constraints.
- Provider `DB-06-T01` — Output: fresh schema.; Consumer `BACKEND-01-T02` — Input: ARCH-03 enums/guards/events and DB constraints.
- Provider `ARCH-02-T01` — Output: stable interfaces.; Consumer `BACKEND-01-T03` — Input: strict command envelope and expected version; implemented atomic IdempotentCommandExecutor/UnitOfWork claim-replay interface.
- Provider `DB-05-T03` — Output: implemented versioned IdempotentCommandExecutor atomic claim/replay/UnitOfWork interface plus one command effect.; Consumer `BACKEND-01-T03` — Input: strict command envelope and expected version; implemented atomic IdempotentCommandExecutor/UnitOfWork claim-replay interface.
- Provider `DB-06-T01` — Output: fresh schema.; Consumer `BACKEND-01-T04` — Input: the fresh consolidated M2 schema plus frozen M4/M5 no-send contracts and gates.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `BACKEND-01-T04` — Input: the fresh consolidated M2 schema plus frozen M4/M5 no-send contracts and gates.
- Provider `BACKEND-01-T04` — Output: versioned validated-actor, sole-writer service, repository-owner, command-registry, and table/event authority contracts plus no-send product operations, accepted deterministic offer economics and StrategyActivationService.initialize_baseline without provider leakage.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `PROVIDER-03-T06` — Output: replaceable least-authority boundary.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `PROVIDER-04-T05` — Output: replacement evidence.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `PROVIDER-05-T05` — Output: least-authority provider evidence.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `WF-01-T05` — Output: interoperable gate bundle with no promoted product data.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `WF-02-T01` — Input: canonical states/accepted runtime.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `PROVIDER-04-T01` — Output: `MarketSearchPort`.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `BACKEND-01-T01` — Output: implemented versioned AgentRunRecordingService, ArtifactCommandService, EvaluationSuiteCommandService and EvaluationExecutionService interfaces with atomic event/replay behavior.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `BACKEND-01-T04` — Output: versioned validated-actor, sole-writer service, repository-owner, command-registry, and table/event authority contracts plus no-send product operations, accepted deterministic offer economics and StrategyActivationService.initialize_baseline without provider leakage.; Consumer `WF-03-T02` — Input: typed origin, IdeaBriefMaterializer and source fixtures.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `WF-03-T03` — Input: both accepted upstream artifacts and frozen economics.
- Provider `BACKEND-01-T04` — Output: versioned validated-actor, sole-writer service, repository-owner, command-registry, and table/event authority contracts plus no-send product operations, accepted deterministic offer economics and StrategyActivationService.initialize_baseline without provider leakage.; Consumer `WF-03-T03` — Input: both accepted upstream artifacts and frozen economics.
- Provider `AGENT-02-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `WF-03-T03` — Input: both accepted upstream artifacts and frozen economics.
- Provider `AGENT-03-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `WF-03-T03` — Input: both accepted upstream artifacts and frozen economics.
- Provider `AGENT-04-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `WF-03-T03` — Input: both accepted upstream artifacts and frozen economics.
- Provider `WF-02-T03` — Output: closed recovery mapping.; Consumer `WF-03-T04` — Input: stored step outputs and workflow versions.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `BACKEND-01-T05` — Input: committed intent/reservation and strict provider ports.
- Provider `PROVIDER-04-T01` — Output: `MarketSearchPort`.; Consumer `BACKEND-01-T05` — Input: committed intent/reservation and strict provider ports.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `BACKEND-01-T05` — Input: committed intent/reservation and strict provider ports.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `BACKEND-01-T05` — Input: committed intent/reservation and strict provider ports.
- Provider `BACKEND-01-T03` — Output: implemented M4 product-command UnitOfWork/replay integration interface plus one committed command result.; Consumer `BACKEND-02-T01` — Input: the BACKEND-01 committed command-result/error boundary plus the document-local frozen M4 actor/route fixture and HTTP metadata contract.
- Provider `BACKEND-01-T04` — Output: versioned validated-actor, sole-writer service, repository-owner, command-registry, and table/event authority contracts plus no-send product operations, accepted deterministic offer economics and StrategyActivationService.initialize_baseline without provider leakage.; Consumer `BACKEND-02-T02` — Input: BACKEND-01 no-send services and the M4 private route foundation.
- Provider `BACKEND-02-T02` — Output: M4/M5 no-send OpenAPI and generated client.; Consumer `FRONTEND-01-T01` — Input: generated BACKEND-02 operations and canonical sales states.
- Provider `BACKEND-02-T01` — Output: versioned private route-boundary and HTTP-metadata contract usable with fixture actors before OIDC integration.; Consumer `FRONTEND-01-T02` — Input: generated request/response/error types.
- Provider `FRONTEND-01-T01` — Output: route-owner and generated-client coverage registry.; Consumer `FRONTEND-02-T01` — Input: createExperiment DTO and PRODUCT-01 constraints.
- Provider `DB-02-T01` — Output: domain values and migration model.; Consumer `FRONTEND-02-T01` — Input: createExperiment DTO and PRODUCT-01 constraints.
- Provider `FRONTEND-02-T03` — Output: versioned setup and accepted-offer inspection.; Consumer `FRONTEND-03-T01` — Input: M4 creation receipts and workflow projections.
- Provider `FRONTEND-01-T01` — Output: route-owner and generated-client coverage registry.; Consumer `FRONTEND-03-T01` — Input: M4 creation receipts and workflow projections.
- Provider `DB-06-T02` — Output: repeatable local/test foundation plus outreach-off production control.; Consumer `INFRA-01-T06` — Input: DB-06 deterministic seed output and BACKEND-02 M4/M5 no-send OpenAPI/client contract.
- Provider `BACKEND-02-T02` — Output: M4/M5 no-send OpenAPI and generated client.; Consumer `INFRA-01-T06` — Input: DB-06 deterministic seed output and BACKEND-02 M4/M5 no-send OpenAPI/client contract.
- Provider `DB-01-T05` — Output: versioned M2 separated-control contract with both controls default-off.; Consumer `INFRA-01-T07` — Input: deterministic M4 migration/seed/generated-client truth, explicit confirmed local project/database/resource labels and outreach-off product control schema.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `INFRA-01-T08` — Input: clean reset product environment, generated no-send client/schema truth, TEST-01 signed command/coverage registries and exact product setup/smoke/reset requirements.
- Provider `OBS-03-T01` — Output: reproducible maximum/actual cost.; Consumer `PROVIDER-06-T04` — Input: the disabled provider-neutral port, proposed field mask, current external provider terms/privacy record, OBS-03 cost ceiling, explicit operator approval, key, request, and reservation.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `PROVIDER-06-T04` — Input: the disabled provider-neutral port, proposed field mask, current external provider terms/privacy record, OBS-03 cost ceiling, explicit operator approval, key, request, and reservation.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `PROVIDER-08-T04` — Input: current adapter/terms/fields/privacy/attribution/retention review, pre-run operator source allowlist and bounded cost/query/page plan.
- Provider `DB-03-T02` — Output: deduplicated M5-ready schema.; Consumer `BACKEND-01-T07` — Input: accepted discovery/final proposals, approved source evidence, immutable OfferPackage filters and recorded identity fixtures.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `BACKEND-01-T07` — Input: accepted discovery/final proposals, approved source evidence, immutable OfferPackage filters and recorded identity fixtures.
- Provider `AGENT-11-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `BACKEND-01-T07` — Input: accepted discovery/final proposals, approved source evidence, immutable OfferPackage filters and recorded identity fixtures.
- Provider `AGENT-06-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `BACKEND-01-T07` — Input: accepted discovery/final proposals, approved source evidence, immutable OfferPackage filters and recorded identity fixtures.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `WF-04-T01` — Input: accepted OfferPackage and source scopes.
- Provider `DB-02-T03` — Output: versioned brief/idea/offer.; Consumer `WF-04-T01` — Input: accepted OfferPackage and source scopes.
- Provider `WF-03-T03` — Output: accepted commercial package and READY_FOR_LEADS.; Consumer `WF-04-T01` — Input: accepted OfferPackage and source scopes.
- Provider `BACKEND-01-T07` — Output: exact BusinessIdentityService and QualificationService interfaces with single identity/decision ownership.; Consumer `WF-04-T01` — Input: accepted OfferPackage and source scopes.
- Provider `PROVIDER-08-T03` — Output: signed discovery capability fixtures for AGENT-11 and AGENT-10.; Consumer `WF-04-T01` — Input: accepted OfferPackage and source scopes.
- Provider `PROVIDER-08-T03` — Output: signed discovery capability fixtures for AGENT-11 and AGENT-10.; Consumer `WF-04-T02` — Input: approved multi-source fixtures and LeadDiscoveryCandidate.
- Provider `AGENT-11-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-04-T02` — Input: approved multi-source fixtures and LeadDiscoveryCandidate.
- Provider `PROVIDER-06-T01` — Output: provider-neutral port plus disabled adapter.; Consumer `WF-04-T03` — Input: accepted preliminary artifacts and bounded evidence ports.
- Provider `PROVIDER-06-T03` — Output: deterministic M3 enrichment fixture containing frozen provider result/meta/usage plus replacement evidence.; Consumer `WF-04-T03` — Input: accepted preliminary artifacts and bounded evidence ports.
- Provider `PROVIDER-05-T04` — Output: deterministic evaluation data.; Consumer `WF-04-T03` — Input: accepted preliminary artifacts and bounded evidence ports.
- Provider `AGENT-05-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-04-T03` — Input: accepted preliminary artifacts and bounded evidence ports.
- Provider `AGENT-06-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-04-T04` — Input: dossier and governing OfferPackage.
- Provider `BACKEND-01-T04` — Output: versioned validated-actor, sole-writer service, repository-owner, command-registry, and table/event authority contracts plus no-send product operations, accepted deterministic offer economics and StrategyActivationService.initialize_baseline without provider leakage.; Consumer `WF-04-T04` — Input: dossier and governing OfferPackage.
- Provider `WF-02-T03` — Output: closed recovery mapping.; Consumer `WF-04-T05` — Input: source activation record and finite pool scenarios.
- Provider `PROVIDER-08-T04` — Output: source activation receipt and captured observations.; Consumer `WF-04-T05` — Input: source activation record and finite pool scenarios.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `ARCH-01-T04` — Input: M3-promoted artifacts, the signed selected-runtime decision, complete WF-03 M4 no-send evidence, the complete WF-04 M5 finite-workflow contract, and reproducible enrichment evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-04-T05` — Output: M5 gate bundle.; Consumer `ARCH-01-T04` — Input: M3-promoted artifacts, the signed selected-runtime decision, complete WF-03 M4 no-send evidence, the complete WF-04 M5 finite-workflow contract, and reproducible enrichment evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-06-T03` — Output: deterministic M3 enrichment fixture containing frozen provider result/meta/usage plus replacement evidence.; Consumer `ARCH-01-T04` — Input: M3-promoted artifacts, the signed selected-runtime decision, complete WF-03 M4 no-send evidence, the complete WF-04 M5 finite-workflow contract, and reproducible enrichment evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `ARCH-01-T04` — Input: M3-promoted artifacts, the signed selected-runtime decision, complete WF-03 M4 no-send evidence, the complete WF-04 M5 finite-workflow contract, and reproducible enrichment evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `BACKEND-04-T01` — Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts.
- Provider `BACKEND-03-T01` — Output: pure policy interfaces and denial enum.; Consumer `BACKEND-04-T01` — Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `BACKEND-04-T01` — Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `BACKEND-04-T01` — Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts.
- Provider `DB-03-T01` — Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence.; Consumer `BACKEND-04-T01` — Input: DB-03 composites, ARCH-03 states/events, provider/policy contracts.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `BACKEND-05-T01` — Input: DB-01/05 hashes/tables and registry above.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `BACKEND-05-T01` — Input: DB-01/05 hashes/tables and registry above.
- Provider `DB-01-T02` — Output: fresh PostgreSQL schema.; Consumer `BACKEND-05-T01` — Input: DB-01/05 hashes/tables and registry above.
- Provider `SEC-06-T01` — Output: versioned early privacy/minimization/redaction/retention-class contract.; Consumer `SEC-04-T01` — Input: approved Israeli solo-business scope, SEC-06 early minimization contract, operator-attested owned test project/mailbox/aliases/scopes and the document-local prohibited-recipient rules; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PRODUCT-01-T02` — Output: pass or a smaller brief.; Consumer `SEC-04-T01` — Input: approved Israeli solo-business scope, SEC-06 early minimization contract, operator-attested owned test project/mailbox/aliases/scopes and the document-local prohibited-recipient rules; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-07-T03` — Output: tested immutable specialist implementation/configuration identity and handoff.; Consumer `SEC-04-T03` — Input: accepted draft and template/policy versions.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `SEC-05-T01` — Input: the DB-01 M2 separated default-off control contract plus canonical DB-05 rows, ARCH-03 events, and SEC-04 signed isolated-test/prohibited-recipient control gate.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `SEC-05-T01` — Input: the DB-01 M2 separated default-off control contract plus canonical DB-05 rows, ARCH-03 events, and SEC-04 signed isolated-test/prohibited-recipient control gate.
- Provider `DB-01-T05` — Output: versioned M2 separated-control contract with both controls default-off.; Consumer `SEC-05-T01` — Input: the DB-01 M2 separated default-off control contract plus canonical DB-05 rows, ARCH-03 events, and SEC-04 signed isolated-test/prohibited-recipient control gate.
- Provider `SEC-04-T01` — Output: signed isolated-test/prohibited-recipient policy and control gate with product outreach denied.; Consumer `SEC-05-T01` — Input: the DB-01 M2 separated default-off control contract plus canonical DB-05 rows, ARCH-03 events, and SEC-04 signed isolated-test/prohibited-recipient control gate.
- Provider `DB-03-T03` — Output: deterministic staged admission substrate over the separately migrated identity/lead schema.; Consumer `SEC-05-T02` — Input: canonical safe source ref/target/version/reason and send authority rows.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `SEC-05-T02` — Input: canonical safe source ref/target/version/reason and send authority rows.
- Provider `DB-03-T01` — Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence.; Consumer `SEC-05-T02` — Input: canonical safe source ref/target/version/reason and send authority rows.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `SEC-05-T03` — Input: provider/run/experiment/campaign/mailbox policies, and OBS-03 complete reservation/reconciliation cost chain.
- Provider `DB-01-T02` — Output: fresh PostgreSQL schema.; Consumer `SEC-02-T01` — Input: DB-01 operators and the normative DDL; early privacy/retention-class contract and document-local exact operational expiry/restore fixtures.
- Provider `SEC-06-T01` — Output: versioned early privacy/minimization/redaction/retention-class contract.; Consumer `SEC-02-T01` — Input: DB-01 operators and the normative DDL; early privacy/retention-class contract and document-local exact operational expiry/restore fixtures.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `SEC-02-T02` — Input: exact config, return path, Origin, anonymous key, and SEC-03 versioned key/object encryption contracts.
- Provider `BACKEND-02-T01` — Output: versioned private route-boundary and HTTP-metadata contract usable with fixture actors before OIDC integration.; Consumer `SEC-02-T04` — Input: session plus HTTP metadata.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `PROVIDER-07-T03` — Input: neutral ports, scoped credential policy and fake HTTP fixtures.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `PROVIDER-07-T03` — Input: neutral ports, scoped credential policy and fake HTTP fixtures.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `WF-06-T01` — Input: SEC-02 real authenticated operator context, expected versions, reason, command key and BACKEND-05 implemented command bus.
- Provider `BACKEND-05-T01` — Output: command bus.; Consumer `WF-06-T01` — Input: SEC-02 real authenticated operator context, expected versions, reason, command key and BACKEND-05 implemented command bus.
- Provider `BACKEND-05-T01` — Output: command bus.; Consumer `WF-02-T05` — Input: current product control and cohort fixtures.
- Provider `WF-06-T03` — Output: implemented versioned guarded resume/retry transition and acknowledgement handler interface plus exact ARCH-03 states/events.; Consumer `WF-02-T05` — Input: current product control and cohort fixtures.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `BACKEND-05-T02` — Input: SEC-02 session/reauthentication, SEC-03 signing/encryption, DB-03 content and PROVIDER-01 deterministic MIME construction.
- Provider `SEC-02-T05` — Output: implemented versioned session lifecycle/reauthentication/emergency-revocation interface plus bounded invalidation evidence.; Consumer `BACKEND-05-T02` — Input: SEC-02 session/reauthentication, SEC-03 signing/encryption, DB-03 content and PROVIDER-01 deterministic MIME construction.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `BACKEND-05-T02` — Input: SEC-02 session/reauthentication, SEC-03 signing/encryption, DB-03 content and PROVIDER-01 deterministic MIME construction.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `BACKEND-05-T02` — Input: SEC-02 session/reauthentication, SEC-03 signing/encryption, DB-03 content and PROVIDER-01 deterministic MIME construction.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `BACKEND-05-T02` — Input: SEC-02 session/reauthentication, SEC-03 signing/encryption, DB-03 content and PROVIDER-01 deterministic MIME construction.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `BACKEND-05-T03` — Input: ActionAuthorityScopeV1, accepted offer/strategy/activation/member/thread/evidence, deterministic commercial result, current policy facts and generations.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `BACKEND-03-T04` — Input: queued intent, immutable ActionAuthorityScopeV1, current rows, and DBOS admission.
- Provider `BACKEND-05-T03` — Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts.; Consumer `BACKEND-03-T04` — Input: queued intent, immutable ActionAuthorityScopeV1, current rows, and DBOS admission.
- Provider `BACKEND-05-T03` — Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts.; Consumer `BACKEND-01-T08` — Input: accepted qualification/buying-intent/call agreement, BookingIntent contract, ActionAuthorityScopeV1, CalendarReadPort/CalendarWritePort recorded fixtures and DB-03 booking ledger.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `BACKEND-01-T08` — Input: accepted qualification/buying-intent/call agreement, BookingIntent contract, ActionAuthorityScopeV1, CalendarReadPort/CalendarWritePort recorded fixtures and DB-03 booking ledger.
- Provider `PROVIDER-07-T02` — Output: recorded contract suite and fake replacement proof.; Consumer `BACKEND-01-T08` — Input: accepted qualification/buying-intent/call agreement, BookingIntent contract, ActionAuthorityScopeV1, CalendarReadPort/CalendarWritePort recorded fixtures and DB-03 booking ledger.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `BACKEND-01-T08` — Input: accepted qualification/buying-intent/call agreement, BookingIntent contract, ActionAuthorityScopeV1, CalendarReadPort/CalendarWritePort recorded fixtures and DB-03 booking ledger.
- Provider `BACKEND-03-T04` — Output: denied terminal suppression or exact pre-call authority.; Consumer `BACKEND-01-T08` — Input: accepted qualification/buying-intent/call agreement, BookingIntent contract, ActionAuthorityScopeV1, CalendarReadPort/CalendarWritePort recorded fixtures and DB-03 booking ledger.
- Provider `DB-04-T04` — Output: implemented versioned ArtifactValidationService and ArtifactAcceptanceService interfaces plus eligible accepted fixture artifact or retained rejection.; Consumer `BACKEND-01-T09` — Input: exact cohort/cutoff/member set, accepted OfferPackage, frozen definitions, immutable provider/conversation/negotiation/booking/cost evidence and evaluator recommendation fixtures.
- Provider `AGENT-09-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `BACKEND-01-T09` — Input: exact cohort/cutoff/member set, accepted OfferPackage, frozen definitions, immutable provider/conversation/negotiation/booking/cost evidence and evaluator recommendation fixtures.
- Provider `AGENT-12-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `BACKEND-01-T10` — Input: closed checkpoint, all-agent AgentLearningProposal results, immutable offline/comparison/holdout/transfer evidence, approved baseline and stored rollback rules.
- Provider `AGENT-10-T06` — Output: reproducible selection and bounded recovery.; Consumer `BACKEND-01-T10` — Input: closed checkpoint, all-agent AgentLearningProposal results, immutable offline/comparison/holdout/transfer evidence, approved baseline and stored rollback rules.
- Provider `BACKEND-03-T04` — Output: denied terminal suppression or exact pre-call authority.; Consumer `BACKEND-04-T02` — Input: queued action-authorized intent/current facts.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `BACKEND-04-T02` — Input: queued action-authorized intent/current facts.
- Provider `DB-03-T03` — Output: deterministic staged admission substrate over the separately migrated identity/lead schema.; Consumer `BACKEND-05-T05` — Input: expected experiment/offer/query/hash/count/caps, exact stage/strategy activation and prior checkpoint only.
- Provider `SEC-05-T02` — Output: implemented versioned RecipientSignalSuppressionService sole-writer interface with unconditional suppression precedence and purge-stable projection.; Consumer `BACKEND-05-T06` — Input: frozen M1/M6 evidence-verification and separated-control decision contracts, intent/attempt/control/incident fixtures, and existing suppression authority.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `OBS-05-T01` — Input: canonical states/events/severity/triggers and the document-local normative incident.catalog.v1 and secure IncidentEvidenceBundle signing schema.
- Provider `DB-05-T01` — Output: executable catalog.; Consumer `OBS-05-T01` — Input: canonical states/events/severity/triggers and the document-local normative incident.catalog.v1 and secure IncidentEvidenceBundle signing schema.
- Provider `PRODUCT-03-T01` — Output: signed risk register.; Consumer `OBS-05-T01` — Input: canonical states/events/severity/triggers and the document-local normative incident.catalog.v1 and secure IncidentEvidenceBundle signing schema.
- Provider `PRODUCT-03-T03` — Output: exercised M1 kill baseline plus a versioned stop-control interface.; Consumer `OBS-05-T02` — Input: IR-01..13 exact first actions and record evidence, and PRODUCT-03 versioned stop-control interface.
- Provider `PRODUCT-03-T01` — Output: signed risk register.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `DB-06-T03` — Output: signed restore report.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-04-T05` — Output: M5 gate bundle.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `LAUNCH-01-T01` — Input: current signed M0-M5 passing gates, risk register, restored M2 schema evidence, selected-runtime acceptance and WF-01 signed isolation/schema manifest; immutable release/config bindings, operator-provisioned isolated project/mailbox/owned-alias resources, exact catalog/allocation and hard send/cost/time caps; both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `PROVIDER-01-T03` — Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version; real authenticated request boundary, registered Gmail start command, mailbox/idempotency schema and atomic command replay service; signed isolated target/resource/cap credential-construction attestation, with no live-send authority.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `PROVIDER-01-T03` — Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version; real authenticated request boundary, registered Gmail start command, mailbox/idempotency schema and atomic command replay service; signed isolated target/resource/cap credential-construction attestation, with no live-send authority.
- Provider `BACKEND-05-T01` — Output: command bus.; Consumer `PROVIDER-01-T03` — Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version; real authenticated request boundary, registered Gmail start command, mailbox/idempotency schema and atomic command replay service; signed isolated target/resource/cap credential-construction attestation, with no live-send authority.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `PROVIDER-01-T03` — Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version; real authenticated request boundary, registered Gmail start command, mailbox/idempotency schema and atomic command replay service; signed isolated target/resource/cap credential-construction attestation, with no live-send authority.
- Provider `DB-05-T03` — Output: implemented versioned IdempotentCommandExecutor atomic claim/replay/UnitOfWork interface plus one command effect.; Consumer `PROVIDER-01-T03` — Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version; real authenticated request boundary, registered Gmail start command, mailbox/idempotency schema and atomic command replay service; signed isolated target/resource/cap credential-construction attestation, with no live-send authority.
- Provider `LAUNCH-01-T01` — Output: signed isolated target/resource/cap and credential-construction attestation; no pilot-entry authorization and no live-send authority.; Consumer `PROVIDER-01-T03` — Input: authenticated start command, signed/encrypted flow state, secret-store TTL/PKCE, callback code, preallocated mailbox/version; real authenticated request boundary, registered Gmail start command, mailbox/idempotency schema and atomic command replay service; signed isolated target/resource/cap credential-construction attestation, with no live-send authority.
- Provider `DB-01-T05` — Output: versioned M2 separated-control contract with both controls default-off.; Consumer `ARCH-02-T04` — Input: current contract, persistence, policies, separate Gmail/calendar read/write ports.
- Provider `DB-05-T05` — Output: explainable gate and cost ledger.; Consumer `ARCH-02-T04` — Input: current contract, persistence, policies, separate Gmail/calendar read/write ports.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `ARCH-02-T04` — Input: current contract, persistence, policies, separate Gmail/calendar read/write ports.
- Provider `PROVIDER-01-T04` — Output: implemented versioned one-call Gmail adapter/result interface plus recorded accepted, conclusive-rejection or unknown evidence; no live-send acceptance claim.; Consumer `ARCH-02-T04` — Input: current contract, persistence, policies, separate Gmail/calendar read/write ports.
- Provider `PROVIDER-01-T04` — Output: implemented versioned one-call Gmail adapter/result interface plus recorded accepted, conclusive-rejection or unknown evidence; no live-send acceptance claim.; Consumer `BACKEND-04-T03` — Input: committed attempt and strict provider result; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `AGENT-07-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `BACKEND-04-T03` — Input: committed attempt and strict provider result; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `BACKEND-04-T03` — Output: accepted/conclusive/ambiguous result.; Consumer `PROVIDER-01-T05` — Input: provider result and original authority tuple.
- Provider `BACKEND-04-T03` — Output: accepted/conclusive/ambiguous result.; Consumer `PROVIDER-02-T02` — Input: exact DB-03 authority tuple and ambiguity; product ACTIVE mailbox/credential binding from the completed OAuth saga; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `DB-03-T01` — Output: versioned DB-03 composite wire/authority contracts consumed by the M1 Gmail adapters and later M2/M6 persistence.; Consumer `PROVIDER-02-T02` — Input: exact DB-03 authority tuple and ambiguity; product ACTIVE mailbox/credential binding from the completed OAuth saga; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `PROVIDER-02-T02` — Input: exact DB-03 authority tuple and ambiguity; product ACTIVE mailbox/credential binding from the completed OAuth saga; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `ARCH-03-T04` — Input: send/booking intent/attempt states, explicit booking confirmation, thread signals and provider reconciliation evidence.
- Provider `PROVIDER-02-T02` — Output: implemented versioned Sent reconciliation interface plus positively reconciled SENT or permanently quarantined inconclusive-absence/conflict fixture evidence; never terminal non-send.; Consumer `ARCH-03-T04` — Input: send/booking intent/attempt states, explicit booking confirmation, thread signals and provider reconciliation evidence.
- Provider `PROVIDER-02-T02` — Output: implemented versioned Sent reconciliation interface plus positively reconciled SENT or permanently quarantined inconclusive-absence/conflict fixture evidence; never terminal non-send.; Consumer `BACKEND-04-T04` — Input: ambiguous attempt or separate explicit provider rejection/signed local pre-write proof; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `DB-01-T05` — Output: versioned M2 separated-control contract with both controls default-off.; Consumer `DB-03-T05` — Input: authorized message/current controls, completed BACKEND-04 SendGateway transaction interface and BACKEND-05 immutable action authorization basis; implemented sole gateway execution/result transaction interface.
- Provider `BACKEND-05-T03` — Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts.; Consumer `DB-03-T05` — Input: authorized message/current controls, completed BACKEND-04 SendGateway transaction interface and BACKEND-05 immutable action authorization basis; implemented sole gateway execution/result transaction interface.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `DB-03-T05` — Input: authorized message/current controls, completed BACKEND-04 SendGateway transaction interface and BACKEND-05 immutable action authorization basis; implemented sole gateway execution/result transaction interface.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `DB-03-T06` — Input: mailbox cursor/provider page and the PROVIDER-02 atomic observation/reply/event/cursor transaction implementation.
- Provider `PROVIDER-02-T03` — Output: implemented versioned GmailHistorySyncService observation/reply/event/cursor transaction interface plus replay-safe cursor.; Consumer `DB-03-T06` — Input: mailbox cursor/provider page and the PROVIDER-02 atomic observation/reply/event/cursor transaction implementation.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `WF-06-T04` — Input: all nonterminal messages/attempts/provider evidence.
- Provider `PROVIDER-02-T02` — Output: implemented versioned Sent reconciliation interface plus positively reconciled SENT or permanently quarantined inconclusive-absence/conflict fixture evidence; never terminal non-send.; Consumer `WF-06-T04` — Input: all nonterminal messages/attempts/provider evidence.
- Provider `PROVIDER-07-T02` — Output: recorded contract suite and fake replacement proof.; Consumer `WF-06-T04` — Input: all nonterminal messages/attempts/provider evidence.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `SEC-03-T02` — Input: PROVIDER-01 flow and ACTIVE tuple.
- Provider `PROVIDER-01-T04` — Output: implemented versioned one-call Gmail adapter/result interface plus recorded accepted, conclusive-rejection or unknown evidence; no live-send acceptance claim.; Consumer `OBS-01-T02` — Input: implemented M6 command/event/outbox/workflow/agent/provider/Gmail/cost/evaluation paths and signed fake private/public HTTP metadata fixtures.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `OBS-01-T02` — Input: implemented M6 command/event/outbox/workflow/agent/provider/Gmail/cost/evaluation paths and signed fake private/public HTTP metadata fixtures.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `OBS-01-T02` — Input: implemented M6 command/event/outbox/workflow/agent/provider/Gmail/cost/evaluation paths and signed fake private/public HTTP metadata fixtures.
- Provider `OBS-01-T03` — Output: implemented bounded M6 telemetry instrumentation and its exact correlated boundary/alert evidence.; Consumer `SEC-05-T04` — Input: security/compliance/send/cost/recovery/telemetry signals, and PRODUCT-03 versioned stop-control interface; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `BACKEND-04-T03` — Output: accepted/conclusive/ambiguous result.; Consumer `SEC-05-T04` — Input: security/compliance/send/cost/recovery/telemetry signals, and PRODUCT-03 versioned stop-control interface; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `PRODUCT-03-T03` — Output: exercised M1 kill baseline plus a versioned stop-control interface.; Consumer `SEC-05-T04` — Input: security/compliance/send/cost/recovery/telemetry signals, and PRODUCT-03 versioned stop-control interface; signed recorded/fake provider/credential/signal fixtures and real isolated PostgreSQL for pre-entry implementation tests.
- Provider `PROVIDER-01-T04` — Output: implemented versioned one-call Gmail adapter/result interface plus recorded accepted, conclusive-rejection or unknown evidence; no live-send acceptance claim.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `BACKEND-05-T06` — Output: implemented versioned send/recovery/control-enable command-gate interfaces plus safe queued/reconcile/retry/control result.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `SEC-03-T02` — Output: mailbox-scoped retrievable credential.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `SEC-04-T03` — Output: reviewable eligible content only.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `BACKEND-05-T02` — Output: purpose-scoped sensitive inspection interface.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `BACKEND-02-T03` — Input: Gmail provider results, DB-05 policy authority, SendGateway result/recovery service, command/control result, eligible-content/control evidence, signed mailbox credential state, and the M4 route foundation; real SEC-02 authenticated session/request boundary and implemented sensitive preview receipt service.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `TEST-04-T03` — Input: fake versioned secret store plus real transactional PostgreSQL; implemented product OAuth saga, complete mailbox/idempotency schema and command replay boundary.
- Provider `DB-03-T04` — Output: migrated immutable message/intent/attempt/result/observation/reply/cursor schema and complete ambiguity-chain constraints.; Consumer `TEST-04-T03` — Input: fake versioned secret store plus real transactional PostgreSQL; implemented product OAuth saga, complete mailbox/idempotency schema and command replay boundary.
- Provider `DB-05-T03` — Output: implemented versioned IdempotentCommandExecutor atomic claim/replay/UnitOfWork interface plus one command effect.; Consumer `TEST-04-T03` — Input: fake versioned secret store plus real transactional PostgreSQL; implemented product OAuth saga, complete mailbox/idempotency schema and command replay boundary.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `TEST-04-T04` — Input: the BACKEND-04 guarded gateway/reconciliation implementation, SEC-05 admission decision service, exact product fixture, and provider call recorder.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `TEST-04-T04` — Input: the BACKEND-04 guarded gateway/reconciliation implementation, SEC-05 admission decision service, exact product fixture, and provider call recorder.
- Provider `DB-01-T01` — Output: inward-facing types.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-01-T04` — Output: implemented versioned one-call Gmail adapter/result interface plus recorded accepted, conclusive-rejection or unknown evidence; no live-send acceptance claim.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-04-T01` — Output: `MarketSearchPort`.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `PROVIDER-06-T01` — Output: provider-neutral port plus disabled adapter.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `TEST-01-T03` — Output: reproducible clean test contexts.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `TEST-02-T01` — Input: canonical sales/table/API/provider/state/incident sets.
- Provider `DB-06-T01` — Output: fresh schema.; Consumer `TEST-02-T02` — Input: real isolated PostgreSQL and DB owner contracts.
- Provider `SEC-06-T01` — Output: versioned early privacy/minimization/redaction/retention-class contract.; Consumer `TEST-02-T02` — Input: real isolated PostgreSQL and DB owner contracts.
- Provider `TEST-02-T02` — Output: M6 PostgreSQL invariant suite.; Consumer `TEST-03-T04` — Input: ARCH-03 canonical states/events, TEST-02 DB read/write maps, and complete versioned WF-02, WF-03, and WF-04 workflow contracts.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `TEST-03-T04` — Input: ARCH-03 canonical states/events, TEST-02 DB read/write maps, and complete versioned WF-02, WF-03, and WF-04 workflow contracts.
- Provider `WF-02-T05` — Output: M6 lifecycle control contract.; Consumer `TEST-03-T04` — Input: ARCH-03 canonical states/events, TEST-02 DB read/write maps, and complete versioned WF-02, WF-03, and WF-04 workflow contracts.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `TEST-03-T04` — Input: ARCH-03 canonical states/events, TEST-02 DB read/write maps, and complete versioned WF-02, WF-03, and WF-04 workflow contracts.
- Provider `WF-04-T05` — Output: M5 gate bundle.; Consumer `TEST-03-T04` — Input: ARCH-03 canonical states/events, TEST-02 DB read/write maps, and complete versioned WF-02, WF-03, and WF-04 workflow contracts.
- Provider `WF-06-T04` — Output: terminal or permanently quarantined operator-visible ledger.; Consumer `TEST-03-T05` — Input: WF-06 terminal-or-quarantined control ledger plus pause/cancel/resume/retry and v1/v2/rollback scenarios.
- Provider `TEST-04-T01` — Output: deterministic provider simulator.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-04-T03` — Output: one exchange and safe terminal/resumable result.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-04-T02` — Output: signed offline Gmail command/fixture/profile mapping.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-02-T04` — Output: implemented versioned 404 full-sync recovery interface plus recovered fixture cursor or visible degraded state.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-05-T02` — Output: implemented versioned RecipientSignalSuppressionService sole-writer interface with unconditional suppression precedence and purge-stable projection.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-01-T06` — Output: architecture evidence.; Consumer `LAUNCH-01-T02` — Input: exact offline fixtures and mapping plus BACKEND-04 gateway/reconciliation, PROVIDER-02 history recovery, SEC-05 suppression, OBS-03 cost-chain, and BACKEND-01 architecture evidence; signed construction target/resource/cap attestation with both controls false; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PRODUCT-03-T01` — Output: signed risk register.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `DB-06-T03` — Output: signed restore report.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-04-T05` — Output: M5 gate bundle.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-01-T03` — Output: implemented bounded M6 telemetry instrumentation and its exact correlated boundary/alert evidence.; Consumer `LAUNCH-01-T03` — Input: construction-only target attestation; complete passing T7-GMAIL-OFFLINE/GMAIL_RECORDED exit-0 bundle including exact M6-O01; implemented OAuth/history/gateway/policy/action-authorization/suppression/budget/rate/control owners; exact ACTIVE credential generation and mailbox binding; visible correlated audit/cost/alerts and implemented local disable; current M0-M5 gates, selected runtime, release/config/promotion hashes, ten-ID catalog, caps and expected control versions; passing offline bundle, ACTIVE credential binding, implemented stop/control and visible correlated audit/alert evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `PROVIDER-01-T06` — Input: sanitized live captures and key-rotation/revocation scenarios; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `PROVIDER-02-T05` — Input: recorded/live owned-mailbox scenarios; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-03-T03` — Output: independently checked complete signed M1 acceptance-or-rejection evidence manifest, with DBOS acceptance only on 8/8.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `BACKEND-05-T06` — Output: implemented versioned send/recovery/control-enable command-gate interfaces plus safe queued/reconcile/retry/control result.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `AGENT-08-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `WF-05-T01` — Input: signed owned-project/mailbox/alias caps and complete pilot authorization.
- Provider `BACKEND-05-T03` — Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts.; Consumer `WF-05-T02` — Input: accepted writer artifacts and action/policy service interfaces.
- Provider `WF-04-T04` — Output: qualified/rejected pool and readiness.; Consumer `WF-05-T02` — Input: accepted writer artifacts and action/policy service interfaces.
- Provider `AGENT-07-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-05-T02` — Input: accepted writer artifacts and action/policy service interfaces.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `WF-05-T03` — Input: durable intent/current policy/rate reservation.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `WF-05-T03` — Input: durable intent/current policy/rate reservation.
- Provider `PROVIDER-02-T04` — Output: implemented versioned 404 full-sync recovery interface plus recovered fixture cursor or visible degraded state.; Consumer `WF-05-T04` — Input: complete sanitized thread, reply objective and CommercialPolicyEngine interface.
- Provider `AGENT-08-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-05-T04` — Input: complete sanitized thread, reply objective and CommercialPolicyEngine interface.
- Provider `SEC-05-T02` — Output: implemented versioned RecipientSignalSuppressionService sole-writer interface with unconditional suppression precedence and purge-stable projection.; Consumer `WF-05-T04` — Input: complete sanitized thread, reply objective and CommercialPolicyEngine interface.
- Provider `WF-05-T04` — Output: bounded conversation/negotiation history.; Consumer `WF-07-T01` — Input: canonical BookingIntent/BookingState and fixture-backed BookingGateway interface.
- Provider `PROVIDER-07-T02` — Output: recorded contract suite and fake replacement proof.; Consumer `WF-07-T01` — Input: canonical BookingIntent/BookingState and fixture-backed BookingGateway interface.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `WF-07-T01` — Input: canonical BookingIntent/BookingState and fixture-backed BookingGateway interface.
- Provider `BACKEND-01-T08` — Output: implemented BookingGateway sole writer and AvailabilityService/BookingReconciliationService read interfaces for WF-07/PROVIDER-07.; Consumer `WF-07-T01` — Input: canonical BookingIntent/BookingState and fixture-backed BookingGateway interface.
- Provider `PROVIDER-07-T03` — Output: disabled-by-default first adapter.; Consumer `WF-07-T02` — Input: bounded availability and booking policy.
- Provider `PROVIDER-07-T04` — Output: adapter acceptance interface for WF-07 live test gate.; Consumer `WF-07-T03` — Input: BookingGateway action authorization and provider fixtures.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `WF-07-T04` — Input: complete isolated pilot entry and dedicated test calendar/attendees.
- Provider `WF-05-T04` — Output: bounded conversation/negotiation history.; Consumer `WF-08-T01` — Input: canonical checkpoint states/rules and CheckpointEvaluationService interface.
- Provider `AGENT-09-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-08-T01` — Input: canonical checkpoint states/rules and CheckpointEvaluationService interface.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `WF-08-T01` — Input: canonical checkpoint states/rules and CheckpointEvaluationService interface.
- Provider `BACKEND-01-T09` — Output: implemented CheckpointEvaluationService for WF-08 and next-stage eligibility.; Consumer `WF-08-T01` — Input: canonical checkpoint states/rules and CheckpointEvaluationService interface.
- Provider `WF-08-T03` — Output: authoritative decision/eligibility interface.; Consumer `WF-09-T01` — Input: closed checkpoint/bundle and GlobalLearningEngine contract.
- Provider `AGENT-12-T04` — Output: specialist acceptance evidence for shared promotion; no second promotion writer.; Consumer `WF-09-T01` — Input: closed checkpoint/bundle and GlobalLearningEngine contract.
- Provider `AGENT-10-T06` — Output: reproducible selection and bounded recovery.; Consumer `WF-09-T01` — Input: closed checkpoint/bundle and GlobalLearningEngine contract.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `WF-09-T01` — Input: closed checkpoint/bundle and GlobalLearningEngine contract.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `WF-09-T01` — Input: closed checkpoint/bundle and GlobalLearningEngine contract.
- Provider `PROVIDER-01-T06` — Output: M6 provider evidence.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-02-T05` — Output: retained M6 read/recovery evidence.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-03-T03` — Output: independently checked complete signed M1 acceptance-or-rejection evidence manifest, with DBOS acceptance only on 8/8.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-05-T06` — Output: implemented versioned send/recovery/control-enable command-gate interfaces plus safe queued/reconcile/retry/control result.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-00-T04` — Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `BACKEND-04-T05` — Input: owned aliases, M1 evidence, controls, provider/gateway evidence, BACKEND-03 policy authority, BACKEND-05 command/control services, queue/rate manifest, fixtures, and live captures; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-04-T05` — Output: signed M6 provider/gateway/sole-writer authority and observability evidence.; Consumer `WF-05-T05` — Input: owned-inbox traces and immutable action lineage.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `WF-05-T05` — Input: owned-inbox traces and immutable action lineage.
- Provider `WF-06-T04` — Output: terminal or permanently quarantined operator-visible ledger.; Consumer `WF-05-T05` — Input: owned-inbox traces and immutable action lineage.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `WF-05-T05` — Input: owned-inbox traces and immutable action lineage.
- Provider `PROVIDER-02-T04` — Output: implemented versioned 404 full-sync recovery interface plus recovered fixture cursor or visible degraded state.; Consumer `TEST-04-T05` — Input: PROVIDER-02 history/cursor recovery, WF-05 recipient-stop implementation, and mailbox-bound Sent/history fixtures.
- Provider `WF-05-T04` — Output: bounded conversation/negotiation history.; Consumer `TEST-04-T05` — Input: PROVIDER-02 history/cursor recovery, WF-05 recipient-stop implementation, and mailbox-bound Sent/history fixtures.
- Provider `WF-05-T05` — Output: M6 control/recovery evidence.; Consumer `TEST-04-T06` — Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-04-T05` — Output: signed M6 provider/gateway/sole-writer authority and observability evidence.; Consumer `TEST-04-T06` — Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `TEST-04-T06` — Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-01-T06` — Output: M6 provider evidence.; Consumer `TEST-04-T06` — Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-02-T05` — Output: retained M6 read/recovery evidence.; Consumer `TEST-04-T06` — Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `LAUNCH-01-T03` — Output: complete signed immutable pilot-entry authorization satisfying every original entry prerequisite; bounded owned-alias live window only, never product outreach.; Consumer `TEST-04-T06` — Input: the completed M6 Gmail matrix, signed preflight, isolated credential/schema, hard caps, and the document-local live command rows; signed bounded M6 entry/preflight with isolated project/mailbox/aliases and hard caps; complete signed pilot-entry authorization after passing offline M6-O01 and all original entry rows; construction-only attestation is insufficient; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-04-T06` — Output: signed M6 bundle including live command-ownership evidence.; Consumer `WF-05-T06` — Input: inbox, negotiation, test booking and checkpoint/global-learning simulations.
- Provider `WF-07-T04` — Output: signed booking gate evidence.; Consumer `WF-05-T06` — Input: inbox, negotiation, test booking and checkpoint/global-learning simulations.
- Provider `WF-08-T04` — Output: M6 checkpoint evidence.; Consumer `WF-05-T06` — Input: inbox, negotiation, test booking and checkpoint/global-learning simulations.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `WF-05-T06` — Input: inbox, negotiation, test booking and checkpoint/global-learning simulations.
- Provider `BACKEND-03-T01` — Output: pure policy interfaces and denial enum.; Consumer `BACKEND-06-T01` — Input: canonical tables/states/events/metrics, BACKEND-03 dedicated final-SEND reasons, exact compliance evidence tuples, and `incident.catalog.v1`.
- Provider `SEC-04-T02` — Output: exact final-SEND compliance facts.; Consumer `BACKEND-06-T01` — Input: canonical tables/states/events/metrics, BACKEND-03 dedicated final-SEND reasons, exact compliance evidence tuples, and `incident.catalog.v1`.
- Provider `DB-05-T02` — Output: M2 event/audit/idempotency/outbox/policy/cost schema.; Consumer `BACKEND-06-T01` — Input: canonical tables/states/events/metrics, BACKEND-03 dedicated final-SEND reasons, exact compliance evidence tuples, and `incident.catalog.v1`.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `BACKEND-06-T01` — Input: canonical tables/states/events/metrics, BACKEND-03 dedicated final-SEND reasons, exact compliance evidence tuples, and `incident.catalog.v1`.
- Provider `OBS-05-T01` — Output: versioned incident.catalog.v1 and secure signable IncidentEvidenceBundle contracts plus authoritative incident record.; Consumer `BACKEND-06-T01` — Input: canonical tables/states/events/metrics, BACKEND-03 dedicated final-SEND reasons, exact compliance evidence tuples, and `incident.catalog.v1`.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `BACKEND-02-T04` — Input: the M6 owned-inbox API, SEC-02 authenticated session/request boundary, and BACKEND-06 stable projection/query schemas.
- Provider `BACKEND-06-T01` — Output: stable report contracts.; Consumer `BACKEND-02-T04` — Input: the M6 owned-inbox API, SEC-02 authenticated session/request boundary, and BACKEND-06 stable projection/query schemas.
- Provider `OBS-03-T03` — Output: DB-05 valid ILS evidence.; Consumer `BACKEND-06-T03` — Input: reservations/cost/provider ledgers and conversion evidence.
- Provider `BACKEND-02-T04` — Output: versioned authenticated M7 private/report/recovery OpenAPI contract.; Consumer `BACKEND-06-T04` — Input: the BACKEND-02 authenticated M7 report/recovery OpenAPI contract plus a frozen MVCC snapshot and event/audit/provider/recovery records.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `BACKEND-02-T05` — Input: the authenticated M7 contract, BACKEND-06 implemented report/recovery routes, composed FastAPI app, and document-local frozen public-ingress requirements.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `ARCH-02-T05` — Input: OpenAPI and route needs.
- Provider `BACKEND-06-T02` — Output: operator diagnosis through exact BACKEND-02 routes.; Consumer `BACKEND-03-T05` — Input: frozen policy fixtures and report projection.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `BACKEND-03-T05` — Input: frozen policy fixtures and report projection.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `BACKEND-05-T07` — Input: versioned flow/credential objects, ACTIVE proofs, command/OpenAPI fixtures; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `BACKEND-05-T07` — Input: versioned flow/credential objects, ACTIVE proofs, command/OpenAPI fixtures; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-02-T03` — Output: authenticated M6 owned-inbox command/query/preview API and generated contract; later M7 full private/report manifest remains separate.; Consumer `BACKEND-05-T07` — Input: versioned flow/credential objects, ACTIVE proofs, command/OpenAPI fixtures; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `BACKEND-05-T07` — Input: versioned flow/credential objects, ACTIVE proofs, command/OpenAPI fixtures; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `OBS-01-T04` — Input: bounded M6 telemetry contract, SEC-02 authenticated session/request boundary and BACKEND-02 complete M7 private/report/incident generated API implementation.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `OBS-01-T04` — Input: bounded M6 telemetry contract, SEC-02 authenticated session/request boundary and BACKEND-02 complete M7 private/report/incident generated API implementation.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-01-T05` — Input: completed private OpenAPI/client, session and M4 creation/control views.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `FRONTEND-01-T05` — Input: completed private OpenAPI/client, session and M4 creation/control views.
- Provider `SEC-02-T05` — Output: implemented versioned session lifecycle/reauthentication/emergency-revocation interface plus bounded invalidation evidence.; Consumer `FRONTEND-01-T05` — Input: completed private OpenAPI/client, session and M4 creation/control views.
- Provider `FRONTEND-02-T04` — Output: M4 no-send browser evidence.; Consumer `FRONTEND-01-T05` — Input: completed private OpenAPI/client, session and M4 creation/control views.
- Provider `FRONTEND-03-T01` — Output: no-send stage view.; Consumer `FRONTEND-01-T05` — Input: completed private OpenAPI/client, session and M4 creation/control views.
- Provider `FRONTEND-01-T05` — Output: M7 integrated operator shell.; Consumer `FRONTEND-03-T03` — Input: M7 client, workflow controls and reporting services.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-03-T03` — Input: M7 client, workflow controls and reporting services.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `FRONTEND-03-T03` — Input: M7 client, workflow controls and reporting services.
- Provider `BACKEND-05-T04` — Output: implemented versioned authenticated stage/control/runtime command-handler interfaces plus canonical control states/events.; Consumer `FRONTEND-03-T03` — Input: M7 client, workflow controls and reporting services.
- Provider `WF-06-T03` — Output: implemented versioned guarded resume/retry transition and acknowledgement handler interface plus exact ARCH-03 states/events.; Consumer `FRONTEND-03-T03` — Input: M7 client, workflow controls and reporting services.
- Provider `BACKEND-01-T09` — Output: implemented CheckpointEvaluationService for WF-08 and next-stage eligibility.; Consumer `FRONTEND-03-T04` — Input: CheckpointEvaluationService/WF-08 projections.
- Provider `WF-08-T04` — Output: M6 checkpoint evidence.; Consumer `FRONTEND-03-T04` — Input: CheckpointEvaluationService/WF-08 projections.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `FRONTEND-03-T05` — Input: StrategyActivationService/WF-09 projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-03-T05` — Input: StrategyActivationService/WF-09 projections.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `FRONTEND-03-T05` — Input: StrategyActivationService/WF-09 projections.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `FRONTEND-03-T05` — Input: StrategyActivationService/WF-09 projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-04-T01` — Input: canonical fifteen-artifact contract and generated DTOs.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `FRONTEND-04-T02` — Input: accepted artifact refs and normalized input snapshots.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-04-T03` — Input: offer/dossier/qualification responses.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-04-T04` — Input: checkpoint/global-strategy protected summaries.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-05-T01` — Input: lead source/candidate/dossier/qualification and cohort DTOs.
- Provider `BACKEND-02-T02` — Output: M4/M5 no-send OpenAPI and generated client.; Consumer `FRONTEND-05-T01` — Input: lead source/candidate/dossier/qualification and cohort DTOs.
- Provider `BACKEND-01-T07` — Output: exact BusinessIdentityService and QualificationService interfaces with single identity/decision ownership.; Consumer `FRONTEND-05-T02` — Input: accepted offer, candidates, dossier and both decisions.
- Provider `BACKEND-05-T06` — Output: implemented versioned send/recovery/control-enable command-gate interfaces plus safe queued/reconcile/retry/control result.; Consumer `FRONTEND-05-T03` — Input: campaign creation API and current-stage eligibility snapshot.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-05-T04` — Input: campaign commands and fresh automatic-send block projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-05-T05` — Input: accepted membership and conversation/booking projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-06-T01` — Input: listExceptions/getExceptionQueueReport and exact incident catalog.
- Provider `SEC-02-T04` — Output: implemented versioned authenticated private-request boundary interface plus authenticated generated API call.; Consumer `FRONTEND-06-T02` — Input: getExceptionSensitivePreview and SEC-02 step-up session.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-06-T02` — Input: getExceptionSensitivePreview and SEC-02 step-up session.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-07-T01` — Input: getConversation and timeline projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-07-T02` — Input: ReplyEvaluation, NegotiationDecision and governing offer.
- Provider `BACKEND-05-T03` — Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts.; Consumer `FRONTEND-07-T03` — Input: ActionAuthorityScopeV1, send blocks and booking projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-07-T03` — Input: ActionAuthorityScopeV1, send blocks and booking projections.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `FRONTEND-07-T04` — Input: typed pause/send/calendar reconciliation and scheduling commands.
- Provider `WF-06-T04` — Output: terminal or permanently quarantined operator-visible ledger.; Consumer `FRONTEND-07-T04` — Input: typed pause/send/calendar reconciliation and scheduling commands.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-07-T04` — Input: typed pause/send/calendar reconciliation and scheduling commands.
- Provider `BACKEND-01-T08` — Output: implemented BookingGateway sole writer and AvailabilityService/BookingReconciliationService read interfaces for WF-07/PROVIDER-07.; Consumer `FRONTEND-07-T04` — Input: typed pause/send/calendar reconciliation and scheduling commands.
- Provider `WF-07-T03` — Output: booking state and provider evidence chain.; Consumer `FRONTEND-07-T04` — Input: typed pause/send/calendar reconciliation and scheduling commands.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `FRONTEND-08-T01` — Input: BACKEND-06 frozen metric projections.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-08-T01` — Input: BACKEND-06 frozen metric projections.
- Provider `BACKEND-06-T03` — Output: budget/cost diagnosis.; Consumer `FRONTEND-08-T03` — Input: OBS-03 reconciled cost/FX/operator-time evidence.
- Provider `BACKEND-06-T02` — Output: operator diagnosis through exact BACKEND-02 routes.; Consumer `FRONTEND-08-T04` — Input: checkpoint bundles and strategy/activation reports.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-08-T04` — Input: checkpoint bundles and strategy/activation reports.
- Provider `BACKEND-01-T09` — Output: implemented CheckpointEvaluationService for WF-08 and next-stage eligibility.; Consumer `FRONTEND-08-T04` — Input: checkpoint bundles and strategy/activation reports.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `FRONTEND-08-T04` — Input: checkpoint bundles and strategy/activation reports.
- Provider `BACKEND-06-T04` — Output: replayable report/recovery API.; Consumer `FRONTEND-09-T01` — Input: getRecoveryOverview and safe generated discriminated unions.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-09-T01` — Input: getRecoveryOverview and safe generated discriminated unions.
- Provider `BACKEND-04-T04` — Output: `SENT`/quarantine for ambiguity or one guarded queued next attempt for eligible failure plus implemented SendGateway execution/result/reconciliation interface.; Consumer `FRONTEND-09-T02` — Input: existing send/calendar reconciliation and repair owners.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-09-T02` — Input: existing send/calendar reconciliation and repair owners.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `FRONTEND-09-T03` — Input: server controls/generations and stored rollback rules.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `FRONTEND-09-T04` — Input: BACKEND-02 errors and private-session contracts.
- Provider `BACKEND-03-T03` — Output: implemented versioned PolicyEvaluationService interface plus immutable DB-05 policy authority.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `DB-03-T06` — Output: lossless replayable sync.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-01-T01` — Output: signed isolation/schema manifest referencing the external resource attestation.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-04-T06` — Output: signed M6 bundle including live command-ownership evidence.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-03-T05` — Output: global-learning control panel.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-04-T04` — Output: M7 evidence browser.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-05-T05` — Output: M7 campaign evidence.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-06-T04` — Output: M7 queue acceptance evidence.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-07-T04` — Output: guarded timeline actions.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-08-T04` — Output: learning analytics.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-09-T04` — Output: accessible failure states.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-01-T05` — Output: M7 integrated operator shell.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-03-T03` — Output: campaign control center.; Consumer `ARCH-01-T05` — Input: signed M6 owned-inbox evidence, DB-05 policy authority, ACTIVE mailbox credential, lossless history sync, isolated-inbox evidence, the exact private operator/public-unsubscribe manifest/client, and completed private operator UI surfaces; complete authenticated frontend foundation and integrated control-center report/control surface; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `BACKEND-06-T05` — Input: metric/report fixtures, retention/redaction states, generated client; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `OBS-03-T05` — Input: exact AGENT-10 populations and active config; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `OBS-03-T05` — Input: exact AGENT-10 populations and active config; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `FRONTEND-01-T04` — Output: responsive accessible shell.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-02-T04` — Output: M4 no-send browser evidence.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-04-T04` — Output: M7 evidence browser.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-05-T05` — Output: M7 campaign evidence.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-06-T04` — Output: M7 queue acceptance evidence.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-07-T04` — Output: guarded timeline actions.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-03-T01` — Output: no-send stage view.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-03-T02` — Output: M4 safe control component.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-03-T04` — Output: checkpoint panel.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-08-T01` — Output: funnel analytics.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-08-T02` — Output: commercial analytics.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-08-T03` — Output: cost evidence panel.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-03-T05` — Output: global-learning control panel.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-08-T04` — Output: learning analytics.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-01-T05` — Output: M7 integrated operator shell.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `FRONTEND-03-T03` — Output: campaign control center.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `WF-07-T04` — Output: signed booking gate evidence.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `WF-08-T04` — Output: M6 checkpoint evidence.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `FRONTEND-09-T05` — Input: all frontend views plus implemented booking/checkpoint/learning owners.
- Provider `OBS-01-T01` — Output: valid `OperationalEventV1`.; Consumer `OBS-02-T01` — Input: OBS-01 and every application boundary.
- Provider `OBS-01-T03` — Output: implemented bounded M6 telemetry instrumentation and its exact correlated boundary/alert evidence.; Consumer `OBS-02-T01` — Input: OBS-01 and every application boundary.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `OBS-04-T01` — Input: AGENT-10 exact suite/rubric/provider sets.
- Provider `AGENT-10-T04` — Output: versioned deterministic scorer package with exact AGENT-10 functions plus `EvaluationScoresV1`, three independently auditable `RepetitionSummaryV1` records, and `SuiteRunSummaryV1`.; Consumer `OBS-04-T03` — Input: AGENT-10 scorer and StrategyActivationService promotion interface.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `OBS-04-T03` — Input: AGENT-10 scorer and StrategyActivationService promotion interface.
- Provider `TEST-01-T03` — Output: reproducible clean test contexts.; Consumer `TEST-05-T01` — Input: signed canonical API/database/provider manifests.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `TEST-05-T01` — Input: signed canonical API/database/provider manifests.
- Provider `FRONTEND-01-T04` — Output: responsive accessible shell.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-02-T04` — Output: M4 no-send browser evidence.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-03-T01` — Output: no-send stage view.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-03-T02` — Output: M4 safe control component.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-04-T04` — Output: M7 evidence browser.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-05-T05` — Output: M7 campaign evidence.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-06-T04` — Output: M7 queue acceptance evidence.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-07-T04` — Output: guarded timeline actions.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-08-T01` — Output: funnel analytics.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-08-T03` — Output: cost evidence panel.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-09-T04` — Output: accessible failure states.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-01-T05` — Output: M7 integrated operator shell.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `FRONTEND-03-T03` — Output: campaign control center.; Consumer `TEST-05-T02` — Input: all FRONTEND views and backend owners.
- Provider `SEC-02-T06` — Output: signed recovery evidence.; Consumer `TEST-05-T03` — Input: session/OAuth/control/booking/checkpoint/strategy handlers.
- Provider `PROVIDER-01-T06` — Output: M6 provider evidence.; Consumer `TEST-05-T03` — Input: session/OAuth/control/booking/checkpoint/strategy handlers.
- Provider `FRONTEND-09-T05` — Output: M8 accessible browser evidence bundle.; Consumer `TEST-05-T03` — Input: session/OAuth/control/booking/checkpoint/strategy handlers.
- Provider `TEST-01-T01` — Output: signed `coverage.v1.json`.; Consumer `TEST-06-T01` — Input: the TEST-01 signed coverage manifest plus document-local planned VPS resources, SLOs, pools/queues/caps, and an operator-selected disposable target.
- Provider `TEST-01-T01` — Output: signed `coverage.v1.json`.; Consumer `INFRA-02-T01` — Input: TEST coverage manifest and current jobs.
- Provider `INFRA-02-T02` — Output: digest-addressed candidate.; Consumer `TEST-06-T02` — Input: representative synthetic dataset and candidate image.
- Provider `INFRA-02-T02` — Output: digest-addressed candidate.; Consumer `INFRA-03-T01` — Input: supported image, 4/8/160 resources, operator recovery device and immutable release.
- Provider `INFRA-02-T02` — Output: digest-addressed candidate.; Consumer `INFRA-03-T02` — Input: signed image digests, internal networks/volumes/roles/resource limits.
- Provider `SEC-03-T01` — Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.; Consumer `INFRA-03-T03` — Input: SEC-03 contract and provider feature evidence.
- Provider `INFRA-03-T04` — Output: signed acceptance and repository/bootstrap evidence.; Consumer `INFRA-04-T01` — Input: INFRA-03 signed accepted repository/bootstrap evidence plus the document-local explicit cluster/system ID, pgBackRest version, backup role, GCS repository, accepted S3 repository, client keys, and five-minute objective.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `SEC-03-T05` — Input: encrypted object/DB backups and separate recovery artifacts; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `SEC-01-T02` — Input: the planned registry, BACKEND-02 exact disabled-public private-plus-two-public manifest, implemented import/call/dataflow graphs, privacy-safe telemetry evidence, private service configuration, and independently restorable encrypted backup chains.
- Provider `OBS-01-T06` — Output: trace evidence with zero sensitive match.; Consumer `SEC-01-T02` — Input: the planned registry, BACKEND-02 exact disabled-public private-plus-two-public manifest, implemented import/call/dataflow graphs, privacy-safe telemetry evidence, private service configuration, and independently restorable encrypted backup chains.
- Provider `INFRA-03-T02` — Output: private service.; Consumer `SEC-01-T02` — Input: the planned registry, BACKEND-02 exact disabled-public private-plus-two-public manifest, implemented import/call/dataflow graphs, privacy-safe telemetry evidence, private service configuration, and independently restorable encrypted backup chains.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `SEC-01-T02` — Input: the planned registry, BACKEND-02 exact disabled-public private-plus-two-public manifest, implemented import/call/dataflow graphs, privacy-safe telemetry evidence, private service configuration, and independently restorable encrypted backup chains.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `DB-06-T01` — Output: fresh schema.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `WF-05-T05` — Output: M6 control/recovery evidence.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `OBS-02-T02` — Input: API/DB/runtime/agent/provider/Gmail/policy/control/cost/eval/backup; implemented API/schema/workflow/agent/control/cost/backup boundaries and their record schemas.
- Provider `SEC-01-T02` — Output: signed complete implementation-closure registry plus deny-by-default/private-deployment ingress/security/load/log evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-02-T05` — Output: implemented versioned session lifecycle/reauthentication/emergency-revocation interface plus bounded invalidation evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-03-T04` — Output: current inventory, retired-key proof, and signed offline recovery-key package.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-01-T06` — Output: M6 provider evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-02-T05` — Output: retained M6 read/recovery evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-03-T06` — Output: replaceable least-authority boundary.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-04-T05` — Output: replacement evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-05-T05` — Output: least-authority provider evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `PROVIDER-06-T05` — Output: safety/terms evidence.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-02-T01` — Output: versioned telemetry package.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-02-T02` — Output: complete signals.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-04-T01` — Output: immutable dataset/fixture manifest.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-04-T02` — Output: 2,076 signed candidate captures and reconciled results.; Consumer `SEC-06-T02` — Input: the early privacy interface; completed SEC-02 session lifecycle, SEC-03 secret/key inventory, OBS-02 telemetry operations, OBS-04 evaluation operations, all final provider implementation evidence bundles, including approved discovery and calendar, independently restorable backup/object-store chains, and external provisional schedule, recipient jurisdictions, counsel, and accounting decisions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-06-T02` — Output: signed complete `DataInventoryV1` plus versioned `retention.policy.v1` and executable durations, holds, key-overlap, and backup schedule projected to every consumer.; Consumer `DB-06-T05` — Input: SEC-06 authoritative `retention.policy.v1`, mechanically resolved DataInventoryV1 field rules, exact table/field set equality, cutoffs, holds, and the current database dependency graph.
- Provider `SEC-06-T02` — Output: signed complete `DataInventoryV1` plus versioned `retention.policy.v1` and executable durations, holds, key-overlap, and backup schedule projected to every consumer.; Consumer `TEST-02-T03` — Input: SEC-06 policy, DB-06 deletion graph and backup chains.
- Provider `DB-06-T05` — Output: versioned database retention/recovery graph plus minimized data or explicitly owned deferral.; Consumer `TEST-02-T03` — Input: SEC-06 policy, DB-06 deletion graph and backup chains.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `TEST-02-T03` — Input: SEC-06 policy, DB-06 deletion graph and backup chains.
- Provider `PROVIDER-01-T04` — Output: implemented versioned one-call Gmail adapter/result interface plus recorded accepted, conclusive-rejection or unknown evidence; no live-send acceptance claim.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `PROVIDER-03-T04` — Output: deterministic evaluation input.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `PROVIDER-04-T04` — Output: M3 evaluation inputs.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `PROVIDER-05-T04` — Output: deterministic evaluation data.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `PROVIDER-06-T03` — Output: deterministic M3 enrichment fixture containing frozen provider result/meta/usage plus replacement evidence.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `AGENT-01-T03` — Output: terminal execution result.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `AGENT-10-T01` — Output: signed non-model M3 fixture manifest plus ten exact suites containing 692 versioned cases with frozen rubrics/fixtures/sensitivity review and candidate parameter templates; no implemented candidate configuration is certified here.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `AGENT-10-T03` — Output: exactly `case_count*3` signed `CandidateGenerationCaptureV1` records plus the complete signed capture-set manifest.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `DB-05-T05` — Output: explainable gate and cost ledger.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `OBS-03-T02` — Output: implemented versioned budget-reservation and ProviderCostReconciliationService interfaces with atomic replay semantics, including distinct calendar-read and booking-write cost chains.; Consumer `TEST-02-T04` — Input: fifteen-artifact set, current capability/suite manifests and costs.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `TEST-02-T05` — Input: BACKEND-02 complete generated operation set.
- Provider `BACKEND-03-T01` — Output: pure policy interfaces and denial enum.; Consumer `TEST-02-T06` — Input: BACKEND-03 reasons and incident.catalog.v1.
- Provider `OBS-05-T01` — Output: versioned incident.catalog.v1 and secure signable IncidentEvidenceBundle contracts plus authoritative incident record.; Consumer `TEST-02-T06` — Input: BACKEND-03 reasons and incident.catalog.v1.
- Provider `SEC-01-T02` — Output: signed complete implementation-closure registry plus deny-by-default/private-deployment ingress/security/load/log evidence.; Consumer `TEST-06-T03` — Input: SEC-01 closure matrix, secret/PII/hash canaries and candidate artifacts.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `INFRA-02-T03` — Input: verified candidate, exact target, backup and runtime state.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `TEST-06-T04` — Input: disposable environment, fault schedule, backup and last release.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `TEST-06-T04` — Input: disposable environment, fault schedule, backup and last release.
- Provider `TEST-01-T01` — Output: signed `coverage.v1.json`.; Consumer `TEST-06-T05` — Input: every capacity/security/privacy/public/fault requirement and TEST-01 registry.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `INFRA-03-T06` — Input: the exact BACKEND-02 disabled-public private-plus-two-public route manifest, SEC-01 closure evidence, and the document-local static M9 activation condition and Cloudflare policy.
- Provider `SEC-01-T02` — Output: signed complete implementation-closure registry plus deny-by-default/private-deployment ingress/security/load/log evidence.; Consumer `INFRA-03-T06` — Input: the exact BACKEND-02 disabled-public private-plus-two-public route manifest, SEC-01 closure evidence, and the document-local static M9 activation condition and Cloudflare policy.
- Provider `SEC-05-T02` — Output: implemented versioned RecipientSignalSuppressionService sole-writer interface with unconditional suppression precedence and purge-stable projection.; Consumer `SEC-04-T04` — Input: Gmail history observations, unconditional precedence for an existing suppression, the exact disabled-public private-plus-two-public manifest/client, SEC-01 implementation-closure evidence, and the disabled M8 ingress profile.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `SEC-04-T04` — Input: Gmail history observations, unconditional precedence for an existing suppression, the exact disabled-public private-plus-two-public manifest/client, SEC-01 implementation-closure evidence, and the disabled M8 ingress profile.
- Provider `SEC-01-T02` — Output: signed complete implementation-closure registry plus deny-by-default/private-deployment ingress/security/load/log evidence.; Consumer `SEC-04-T04` — Input: Gmail history observations, unconditional precedence for an existing suppression, the exact disabled-public private-plus-two-public manifest/client, SEC-01 implementation-closure evidence, and the disabled M8 ingress profile.
- Provider `INFRA-03-T06` — Output: staged, disabled, and independently switchable two-operation public ingress configuration.; Consumer `SEC-04-T04` — Input: Gmail history observations, unconditional precedence for an existing suppression, the exact disabled-public private-plus-two-public manifest/client, SEC-01 implementation-closure evidence, and the disabled M8 ingress profile.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `SEC-04-T04` — Input: Gmail history observations, unconditional precedence for an existing suppression, the exact disabled-public private-plus-two-public manifest/client, SEC-01 implementation-closure evidence, and the disabled M8 ingress profile.
- Provider `TEST-06-T02` — Output: safe envelope or smaller/resized recommendation.; Consumer `INFRA-03-T07` — Input: TEST-06 envelope and INFRA-02 manifests.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `INFRA-03-T07` — Input: TEST-06 envelope and INFRA-02 manifests.
- Provider `SEC-06-T02` — Output: signed complete `DataInventoryV1` plus versioned `retention.policy.v1` and executable durations, holds, key-overlap, and backup schedule projected to every consumer.; Consumer `INFRA-04-T03` — Input: retention command, authoritative policy, exact target snapshot, two healthy repositories and existing idempotency/audit tables.
- Provider `SEC-06-T02` — Output: signed complete `DataInventoryV1` plus versioned `retention.policy.v1` and executable durations, holds, key-overlap, and backup schedule projected to every consumer.; Consumer `INFRA-04-T04` — Input: exact recovery dependency graph, DB-06/SEC-06 policy and live-record holds.
- Provider `DB-06-T05` — Output: versioned database retention/recovery graph plus minimized data or explicitly owned deferral.; Consumer `INFRA-04-T04` — Input: exact recovery dependency graph, DB-06/SEC-06 policy and live-record holds.
- Provider `DB-06-T05` — Output: versioned database retention/recovery graph plus minimized data or explicitly owned deferral.; Consumer `SEC-06-T03` — Input: DB-06 graph, object store, expiry/holds/tombstones.
- Provider `INFRA-04-T04` — Output: exact 14-daily/4-weekly sets with no older personal-data recovery point.; Consumer `SEC-06-T03` — Input: DB-06 graph, object store, expiry/holds/tombstones.
- Provider `OBS-05-T01` — Output: versioned incident.catalog.v1 and secure signable IncidentEvidenceBundle contracts plus authoritative incident record.; Consumer `WF-06-T05` — Input: incident, product/runtime/provider comparison, signed evidence.
- Provider `INFRA-04-T05` — Output: executable versioned isolated PITR/full-restore runner interface plus signed restore report.; Consumer `WF-06-T05` — Input: incident, product/runtime/provider comparison, signed evidence.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `TEST-03-T06` — Input: WF-06 auditable recovery service/evidence, corrupted projection/outbox/runtime-mapping fixtures, and an independently verified backup chain.
- Provider `WF-06-T05` — Output: implemented versioned idempotent typed recovery/repair command interface and auditable recovery evidence without SQL.; Consumer `TEST-03-T06` — Input: WF-06 auditable recovery service/evidence, corrupted projection/outbox/runtime-mapping fixtures, and an independently verified backup chain.
- Provider `ARCH-03-T01` — Output: canonical `.v1` names and payload schemas, versioned states, guards, legal transition tables, typed decisions, and event intents.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `DB-05-T01` — Output: executable catalog.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `ARCH-02-T01` — Output: stable interfaces.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `BACKEND-01-T04` — Output: versioned validated-actor, sole-writer service, repository-owner, command-registry, and table/event authority contracts plus no-send product operations, accepted deterministic offer economics and StrategyActivationService.initialize_baseline without provider leakage.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-00-T01` — Output: runtime-neutral interface and forbidden-import rules.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-01-T02` — Output: in-memory `GmailSendRequestV1`.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-04-T01` — Output: `MarketSearchPort`.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-06-T01` — Output: provider-neutral port plus disabled adapter.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-02-T05` — Output: M6 lifecycle control contract.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-04-T05` — Output: M5 gate bundle.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-06-T05` — Output: implemented versioned idempotent typed recovery/repair command interface and auditable recovery evidence without SQL.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PROVIDER-01-T01` — Output: versioned Gmail OAuth/credential-binding/request/result/error/MIME/history contract bundle and signed disposable fixtures.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `TEST-03-T03` — Output: independently checked complete signed M1 acceptance-or-rejection evidence manifest, with DBOS acceptance only on 8/8.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `TEST-03-T04` — Output: executable versioned finite-workflow/delivery-edge failure-injection suite plus complete state-event-row-result matrix.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `TEST-03-T06` — Output: executable versioned typed-repair/isolated-restore recovery-matrix suite interface plus signed recovery proof.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `TEST-04-T06` — Output: signed M6 bundle including live command-ownership evidence.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-05-T05` — Output: M6 control/recovery evidence.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-01-T03` — Output: reproducible crash harness.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `TEST-04-T05` — Output: terminal or explicit unresolved state plus only evidence-qualified durable suppression; completed executable versioned Gmail history/suppression suite with its recorded-fixture/scenario manifest.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-07-T04` — Output: signed booking gate evidence.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-08-T04` — Output: M6 checkpoint evidence.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `BACKEND-01-T08` — Output: implemented BookingGateway sole writer and AvailabilityService/BookingReconciliationService read interfaces for WF-07/PROVIDER-07.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `BACKEND-01-T09` — Output: implemented CheckpointEvaluationService for WF-08 and next-stage eligibility.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `OBS-04-T04` — Input: WF-07/08/09 and existing M1/Gmail/restore harnesses.
- Provider `PRODUCT-03-T03` — Output: exercised M1 kill baseline plus a versioned stop-control interface.; Consumer `OBS-05-T03` — Input: M6 containment services and StopControlV1; SEC-02 session invalidation, SEC-03 key/credential rotation, INFRA-02 rollback release, INFRA-04 restore implementation and WF-06 typed recovery service.
- Provider `SEC-02-T05` — Output: implemented versioned session lifecycle/reauthentication/emergency-revocation interface plus bounded invalidation evidence.; Consumer `OBS-05-T03` — Input: M6 containment services and StopControlV1; SEC-02 session invalidation, SEC-03 key/credential rotation, INFRA-02 rollback release, INFRA-04 restore implementation and WF-06 typed recovery service.
- Provider `SEC-03-T04` — Output: current inventory, retired-key proof, and signed offline recovery-key package.; Consumer `OBS-05-T03` — Input: M6 containment services and StopControlV1; SEC-02 session invalidation, SEC-03 key/credential rotation, INFRA-02 rollback release, INFRA-04 restore implementation and WF-06 typed recovery service.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `OBS-05-T03` — Input: M6 containment services and StopControlV1; SEC-02 session invalidation, SEC-03 key/credential rotation, INFRA-02 rollback release, INFRA-04 restore implementation and WF-06 typed recovery service.
- Provider `INFRA-04-T05` — Output: executable versioned isolated PITR/full-restore runner interface plus signed restore report.; Consumer `OBS-05-T03` — Input: M6 containment services and StopControlV1; SEC-02 session invalidation, SEC-03 key/credential rotation, INFRA-02 rollback release, INFRA-04 restore implementation and WF-06 typed recovery service.
- Provider `WF-06-T05` — Output: implemented versioned idempotent typed recovery/repair command interface and auditable recovery evidence without SQL.; Consumer `OBS-05-T03` — Input: M6 containment services and StopControlV1; SEC-02 session invalidation, SEC-03 key/credential rotation, INFRA-02 rollback release, INFRA-04 restore implementation and WF-06 typed recovery service.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `PRODUCT-03-T04` — Input: synthetic incident scenarios R01-R27 plus SEC-05 bounded-stop evidence and OBS-05 typed containment/recovery services; completed IR-01..13 typed recovery/restore/rollback runbook services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-05-T02` — Output: implemented M6 IR-01/02/03/12 bounded containment services with typed acknowledgements; later full restore/rollback runbooks remain separate.; Consumer `PRODUCT-03-T04` — Input: synthetic incident scenarios R01-R27 plus SEC-05 bounded-stop evidence and OBS-05 typed containment/recovery services; completed IR-01..13 typed recovery/restore/rollback runbook services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-05-T03` — Output: complete implemented IR-01..13 bounded-harm/typed-recovery service and runbook set with all original first-action evidence.; Consumer `PRODUCT-03-T04` — Input: synthetic incident scenarios R01-R27 plus SEC-05 bounded-stop evidence and OBS-05 typed containment/recovery services; completed IR-01..13 typed recovery/restore/rollback runbook services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-02-T04` — Output: actionable alerts.; Consumer `OBS-05-T04` — Input: OBS-02 alerts, offline contacts and counsel/provider templates.
- Provider `TEST-02-T07` — Output: signed coverage and evidence report.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `TEST-05-T04` — Output: safe screenshots/traces/manual evidence.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `TEST-06-T04` — Output: recovery-time/data-loss measurements.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `TEST-03-T06` — Output: executable versioned typed-repair/isolated-restore recovery-matrix suite interface plus signed recovery proof.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `TEST-04-T06` — Output: signed M6 bundle including live command-ownership evidence.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `TEST-03-T07` — Output: one signed command mapping.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `TEST-06-T05` — Output: signed command-coverage report.; Consumer `TEST-01-T05` — Input: deterministic, recovery, browser, security, restore and provider evidence, including TEST-03 signed command mapping and TEST-06 signed command-coverage report.
- Provider `OBS-02-T01` — Output: versioned telemetry package.; Consumer `INFRA-05-T01` — Input: exact OBS-01/02 registries and product queries.
- Provider `OBS-01-T03` — Output: implemented bounded M6 telemetry instrumentation and its exact correlated boundary/alert evidence.; Consumer `INFRA-05-T01` — Input: exact OBS-01/02 registries and product queries.
- Provider `BACKEND-06-T02` — Output: operator diagnosis through exact BACKEND-02 routes.; Consumer `INFRA-05-T01` — Input: exact OBS-01/02 registries and product queries.
- Provider `OBS-02-T04` — Output: actionable alerts.; Consumer `INFRA-05-T02` — Input: OBS-02 alerts and OBS-05 tuples/objectives.
- Provider `OBS-05-T01` — Output: versioned incident.catalog.v1 and secure signable IncidentEvidenceBundle contracts plus authoritative incident record.; Consumer `INFRA-05-T02` — Input: OBS-02 alerts and OBS-05 tuples/objectives.
- Provider `OBS-05-T04` — Output: actionable one-operator coordination.; Consumer `INFRA-05-T02` — Input: OBS-02 alerts and OBS-05 tuples/objectives.
- Provider `OBS-05-T01` — Output: versioned incident.catalog.v1 and secure signable IncidentEvidenceBundle contracts plus authoritative incident record.; Consumer `INFRA-05-T04` — Input: every redacted Critical incident and daily fixed canary.
- Provider `INFRA-04-T03` — Output: canonical deletion authority head/version, signed deletion certificate chain, refreshed recovery package, and evidence that privacy deletion survives PITR.; Consumer `INFRA-05-T05` — Input: independent recovery package, authority head exact version/ETag/checksum, certificate chain and canonical backup/restore alert route.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `INFRA-05-T06` — Input: clean candidate host, signed releases/backups/keys and exact scenario.
- Provider `SEC-03-T04` — Output: current inventory, retired-key proof, and signed offline recovery-key package.; Consumer `INFRA-05-T06` — Input: clean candidate host, signed releases/backups/keys and exact scenario.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `INFRA-05-T06` — Input: clean candidate host, signed releases/backups/keys and exact scenario.
- Provider `INFRA-05-T06` — Output: executable DR01-DR11 scenario harness plus signed scenario report.; Consumer `INFRA-04-T06` — Input: newest eligible chain and clean host; implemented executable DR01-DR11 scenario harness.
- Provider `INFRA-04-T06` — Output: M8/ongoing restore evidence.; Consumer `INFRA-05-T07` — Input: daily backup/telemetry checks, monthly alert test, quarterly IR rotation/contact/channel test and <=90-day clean restore.
- Provider `INFRA-03-T07` — Output: measured limits and recovery evidence.; Consumer `ARCH-01-T06` — Input: complete private product; measured private deployment/load-rehearsal limits, clean restore evidence, current monitoring readiness and implemented full incident recovery services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-04-T06` — Output: M8/ongoing restore evidence.; Consumer `ARCH-01-T06` — Input: complete private product; measured private deployment/load-rehearsal limits, clean restore evidence, current monitoring readiness and implemented full incident recovery services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-05-T07` — Output: ongoing readiness.; Consumer `ARCH-01-T06` — Input: complete private product; measured private deployment/load-rehearsal limits, clean restore evidence, current monitoring readiness and implemented full incident recovery services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-05-T03` — Output: complete implemented IR-01..13 bounded-harm/typed-recovery service and runbook set with all original first-action evidence.; Consumer `ARCH-01-T06` — Input: complete private product; measured private deployment/load-rehearsal limits, clean restore evidence, current monitoring readiness and implemented full incident recovery services; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `LAUNCH-01-T06` — Output: M6 gate record with no residual authority.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-04-T06` — Output: M8/ongoing restore evidence.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-02-T05` — Output: signed M8 SLO baseline.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-05-T07` — Output: ongoing readiness.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `ARCH-01-T05` — Output: signed M7 private-operator architecture gate referencing distinct retained M6 and M7 evidence.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-01-T02` — Output: signed `task7-commands.v1.json`.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-01-T05` — Output: promotion decision, never authority enable.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-03-T08` — Output: signed coverage.; Consumer `LAUNCH-02-T01` — Input: current M0-M7 gates, release/target/recovery/visibility evidence and closed catalogs, completed TEST-01 M8 consolidation evidence and INFRA-03 private deployment command-ownership evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-02-T02` — Output: digest-addressed candidate.; Consumer `LAUNCH-02-T02` — Input: signed candidate, additive migration and current backup; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `LAUNCH-02-T02` — Input: signed candidate, additive migration and current backup; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-03-T04` — Output: signed acceptance and repository/bootstrap evidence.; Consumer `LAUNCH-02-T04` — Input: Task-7 profiles, isolated targets, accepted AWS S3 identity, INFRA-04 restore evidence, INFRA-05 DR harness/report, and TEST-06 recovery-time/data-loss measurements; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-04-T06` — Output: M8/ongoing restore evidence.; Consumer `LAUNCH-02-T04` — Input: Task-7 profiles, isolated targets, accepted AWS S3 identity, INFRA-04 restore evidence, INFRA-05 DR harness/report, and TEST-06 recovery-time/data-loss measurements; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-05-T06` — Output: executable DR01-DR11 scenario harness plus signed scenario report.; Consumer `LAUNCH-02-T04` — Input: Task-7 profiles, isolated targets, accepted AWS S3 identity, INFRA-04 restore evidence, INFRA-05 DR harness/report, and TEST-06 recovery-time/data-loss measurements; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-06-T04` — Output: recovery-time/data-loss measurements.; Consumer `LAUNCH-02-T04` — Input: Task-7 profiles, isolated targets, accepted AWS S3 identity, INFRA-04 restore evidence, INFRA-05 DR harness/report, and TEST-06 recovery-time/data-loss measurements; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-07-T04` — Output: signed booking gate evidence.; Consumer `LAUNCH-02-T05` — Input: all windows/commands/incidents/cost and release pointers; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-08-T04` — Output: M6 checkpoint evidence.; Consumer `LAUNCH-02-T05` — Input: all windows/commands/incidents/cost and release pointers; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `LAUNCH-02-T05` — Input: all windows/commands/incidents/cost and release pointers; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-05-T02` — Output: private-route coverage and server receipts.; Consumer `LAUNCH-02-T05` — Input: all windows/commands/incidents/cost and release pointers; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-02-T02` — Output: digest-addressed candidate.; Consumer `LAUNCH-05-T01` — Input: locks, image/action digests, SBOM, direct official release/advisory candidates discovered from owner feeds and EOL registry.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `LAUNCH-05-T04` — Input: signed candidate, clean target, backup and rollback target.
- Provider `INFRA-04-T02` — Output: two independently restorable encrypted chains.; Consumer `LAUNCH-05-T04` — Input: signed candidate, clean target, backup and rollback target.
- Provider `PRODUCT-01-T02` — Output: pass or a smaller brief.; Consumer `SEC-04-T05` — Input: the PRODUCT-01 approved Israeli solo-business use case, SEC-06 early privacy/minimization contract, and external Google account/scopes, recipient cohorts/sources/content, and applicable jurisdictions. Completed SEC-06 authoritative inventory/retention policy and implemented suppression/control evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-06-T02` — Output: signed complete `DataInventoryV1` plus versioned `retention.policy.v1` and executable durations, holds, key-overlap, and backup schedule projected to every consumer.; Consumer `SEC-04-T05` — Input: the PRODUCT-01 approved Israeli solo-business use case, SEC-06 early privacy/minimization contract, and external Google account/scopes, recipient cohorts/sources/content, and applicable jurisdictions. Completed SEC-06 authoritative inventory/retention policy and implemented suppression/control evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `SEC-04-T05` — Input: the PRODUCT-01 approved Israeli solo-business use case, SEC-06 early privacy/minimization contract, and external Google account/scopes, recipient cohorts/sources/content, and applicable jurisdictions. Completed SEC-06 authoritative inventory/retention policy and implemented suppression/control evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-04-T05` — Output: automatic rollback/exception evidence.; Consumer `SEC-01-T05` — Input: current threat register, release/provider/policy/eval/restore evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `INFRA-04-T06` — Output: M8/ongoing restore evidence.; Consumer `SEC-01-T05` — Input: current threat register, release/provider/policy/eval/restore evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `LAUNCH-05-T04` — Output: signed acceptance or rejection.; Consumer `SEC-01-T05` — Input: current threat register, release/provider/policy/eval/restore evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-01-T05` — Output: signed gate record.; Consumer `PRODUCT-02-T04` — Input: safety gates, exact `100/200/300/400` increments, `100/300/600/1,000` cumulative maxima, stage reply windows, subsegment allocation, price, delivery-cost assumptions, and the default-or-stricter demand floors; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-04-T04` — Output: activation-ready reply/public-stop implementation with exact trigger-backed suppression, no public activation authority.; Consumer `TEST-05-T05` — Input: M9 synthetic token and FastAPI two-operation fixture.
- Provider `TEST-01-T01` — Output: signed `coverage.v1.json`.; Consumer `TEST-05-T06` — Input: all private/public journeys and exact operations.
- Provider `LAUNCH-02-T05` — Output: M8 gate record.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `SEC-01-T05` — Output: signed gate record.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `TEST-05-T05` — Output: public edge/browser evidence.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `DB-02-T03` — Output: versioned brief/idea/offer.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `BACKEND-05-T05` — Output: one immutable cohort membership snapshot.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `PROVIDER-01-T03` — Output: implemented versioned OAuth secret-store saga/command interface plus stored opaque redirect and mailbox referencing one exact ACTIVE credential generation.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `SEC-04-T02` — Output: exact final-SEND compliance facts.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `PRODUCT-02-T04` — Output: signed staged decision-rule version.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `SEC-04-T05` — Output: immutable `LegalReviewRecordV1` and `CompliancePolicyV1`.; Consumer `LAUNCH-03-T01` — Input: all six phase exits, M0–M8 gates and exact legal/provider/economic envelope.
- Provider `INFRA-03-T06` — Output: staged, disabled, and independently switchable two-operation public ingress configuration.; Consumer `LAUNCH-03-T02` — Input: signed M9 route authorization, staged edge and current SEC-04 implementation.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `LAUNCH-03-T02` — Input: signed M9 route authorization, staged edge and current SEC-04 implementation.
- Provider `SEC-04-T04` — Output: activation-ready reply/public-stop implementation with exact trigger-backed suppression, no public activation authority.; Consumer `LAUNCH-03-T02` — Input: signed M9 route authorization, staged edge and current SEC-04 implementation.
- Provider `SEC-04-T05` — Output: immutable `LegalReviewRecordV1` and `CompliancePolicyV1`.; Consumer `LAUNCH-03-T02` — Input: signed M9 route authorization, staged edge and current SEC-04 implementation.
- Provider `LAUNCH-03-T02` — Output: public capability and recovery evidence.; Consumer `OBS-01-T07` — Input: bounded private telemetry contract, LAUNCH-03 activated two-operation capability and SEC-04 public-stop implementation.
- Provider `SEC-04-T04` — Output: activation-ready reply/public-stop implementation with exact trigger-backed suppression, no public activation authority.; Consumer `OBS-01-T07` — Input: bounded private telemetry contract, LAUNCH-03 activated two-operation capability and SEC-04 public-stop implementation.
- Provider `LAUNCH-03-T02` — Output: public capability and recovery evidence.; Consumer `TEST-06-T06` — Input: the SEC-04 activation-ready stop path, LAUNCH-03 recipient-opaque activated public capability, BACKEND-02 exact disabled-public private-plus-two-public manifest, and TEST-06-owned synthetic unsubscribe tokens; active-public safe correlation/redaction evidence.
- Provider `BACKEND-02-T05` — Output: one API source of truth plus exact disabled-public private-plus-two-public route map and generated client.; Consumer `TEST-06-T06` — Input: the SEC-04 activation-ready stop path, LAUNCH-03 recipient-opaque activated public capability, BACKEND-02 exact disabled-public private-plus-two-public manifest, and TEST-06-owned synthetic unsubscribe tokens; active-public safe correlation/redaction evidence.
- Provider `SEC-04-T04` — Output: activation-ready reply/public-stop implementation with exact trigger-backed suppression, no public activation authority.; Consumer `TEST-06-T06` — Input: the SEC-04 activation-ready stop path, LAUNCH-03 recipient-opaque activated public capability, BACKEND-02 exact disabled-public private-plus-two-public manifest, and TEST-06-owned synthetic unsubscribe tokens; active-public safe correlation/redaction evidence.
- Provider `OBS-01-T07` — Output: complete active-public correlation/redaction evidence for the exact bounded GET/POST pair.; Consumer `TEST-06-T06` — Input: the SEC-04 activation-ready stop path, LAUNCH-03 recipient-opaque activated public capability, BACKEND-02 exact disabled-public private-plus-two-public manifest, and TEST-06-owned synthetic unsubscribe tokens; active-public safe correlation/redaction evidence.
- Provider `TEST-06-T06` — Output: scanner-safe active public-ingress and recipient-suppression evidence.; Consumer `SEC-04-T06` — Input: M1/M6 policy/legal/source/recipient-evidence/template/suppression/mailbox/cost/recovery evidence, PRODUCT-02 staged rule, prior barrier when applicable, activation-ready stop path, and TEST-06 active public-ingress/recipient-suppression evidence; fresh signed real-recipient LegalReviewRecordV1 and CompliancePolicyV1 for the exact scope; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-05-T04` — Output: implemented versioned deterministic stop/incident/alert handler interface plus bounded stop with visible acknowledgement.; Consumer `SEC-04-T06` — Input: M1/M6 policy/legal/source/recipient-evidence/template/suppression/mailbox/cost/recovery evidence, PRODUCT-02 staged rule, prior barrier when applicable, activation-ready stop path, and TEST-06 active public-ingress/recipient-suppression evidence; fresh signed real-recipient LegalReviewRecordV1 and CompliancePolicyV1 for the exact scope; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-03-T04` — Output: operator cost control with exact action attribution and no PII leakage.; Consumer `SEC-04-T06` — Input: M1/M6 policy/legal/source/recipient-evidence/template/suppression/mailbox/cost/recovery evidence, PRODUCT-02 staged rule, prior barrier when applicable, activation-ready stop path, and TEST-06 active public-ingress/recipient-suppression evidence; fresh signed real-recipient LegalReviewRecordV1 and CompliancePolicyV1 for the exact scope; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-03-T06` — Output: executable versioned typed-repair/isolated-restore recovery-matrix suite interface plus signed recovery proof.; Consumer `SEC-04-T06` — Input: M1/M6 policy/legal/source/recipient-evidence/template/suppression/mailbox/cost/recovery evidence, PRODUCT-02 staged rule, prior barrier when applicable, activation-ready stop path, and TEST-06 active public-ingress/recipient-suppression evidence; fresh signed real-recipient LegalReviewRecordV1 and CompliancePolicyV1 for the exact scope; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-04-T06` — Output: M9 stage eligibility, not send.; Consumer `SEC-05-T05` — Input: closed incident/current gate/policy/eval/restore/cohort evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `TEST-03-T06` — Output: executable versioned typed-repair/isolated-restore recovery-matrix suite interface plus signed recovery proof.; Consumer `SEC-05-T05` — Input: closed incident/current gate/policy/eval/restore/cohort evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `OBS-05-T06` — Output: lessons and bounded eligibility.; Consumer `SEC-05-T05` — Input: closed incident/current gate/policy/eval/restore/cohort evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate.
- Provider `SEC-04-T02` — Output: exact final-SEND compliance facts.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `BACKEND-05-T03` — Output: implemented ActionAuthorizationService with immutable authority and append-only consumption receipts; gateways still rebuild fresh facts.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `BACKEND-03-T04` — Output: denied terminal suppression or exact pre-call authority.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `SEC-04-T06` — Output: M9 stage eligibility, not send.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `SEC-05-T05` — Output: eligibility only plus signed expected-version control-enable evidence, without creating downstream rows or provider calls.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `TEST-06-T06` — Output: scanner-safe active public-ingress and recipient-suppression evidence.; Consumer `LAUNCH-03-T03` — Input: fresh authority/offer/strategy/member facts and remaining effective cap.
- Provider `INFRA-04-T07` — Output: independent data-recovery proof, not a live service.; Consumer `LAUNCH-03-T04` — Input: reply/calendar observations and implemented BookingGateway/current controls.
- Provider `INFRA-05-T07` — Output: ongoing readiness.; Consumer `LAUNCH-03-T04` — Input: reply/calendar observations and implemented BookingGateway/current controls.
- Provider `BACKEND-01-T08` — Output: implemented BookingGateway sole writer and AvailabilityService/BookingReconciliationService read interfaces for WF-07/PROVIDER-07.; Consumer `LAUNCH-03-T04` — Input: reply/calendar observations and implemented BookingGateway/current controls.
- Provider `WF-07-T04` — Output: signed booking gate evidence.; Consumer `LAUNCH-03-T04` — Input: reply/calendar observations and implemented BookingGateway/current controls.
- Provider `BACKEND-01-T09` — Output: implemented CheckpointEvaluationService for WF-08 and next-stage eligibility.; Consumer `LAUNCH-03-T05` — Input: frozen stage/cumulative outcomes and verified costs/time plus global-learning owners.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `LAUNCH-03-T05` — Input: frozen stage/cumulative outcomes and verified costs/time plus global-learning owners.
- Provider `WF-08-T04` — Output: M6 checkpoint evidence.; Consumer `LAUNCH-03-T05` — Input: frozen stage/cumulative outcomes and verified costs/time plus global-learning owners.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `LAUNCH-03-T05` — Input: frozen stage/cumulative outcomes and verified costs/time plus global-learning owners.
- Provider `AGENT-01-T01` — Output: importable versioned contracts.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `PROVIDER-02-T01` — Output: strict versioned Gmail read/history result contracts plus signed recorded provider results.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `PROVIDER-03-T01` — Output: provider-neutral protocol.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `PROVIDER-04-T01` — Output: `MarketSearchPort`.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `PROVIDER-05-T01` — Output: two read-only ports.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `PROVIDER-06-T01` — Output: provider-neutral port plus disabled adapter.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `SEC-05-T03` — Output: versioned hierarchical budget/rate-admission service contract plus no-over-admission evidence.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `WF-02-T05` — Output: M6 lifecycle control contract.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `WF-03-T05` — Output: M4 gate bundle.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `WF-04-T05` — Output: M5 gate bundle.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `PROVIDER-01-T01` — Output: versioned Gmail OAuth/credential-binding/request/result/error/MIME/history contract bundle and signed disposable fixtures.; Consumer `LAUNCH-04-T01` — Input: canonical sales owners and complete eight-phase ladder.
- Provider `LAUNCH-03-T05` — Output: immutable checkpoint/package/activation/rollback evidence.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `AGENT-10-T05` — Output: versioned sole-owner promotion-gate interface plus immutable promotion decision binding suite/configuration identity, `PromotionManifestV1`, registry version, and one eligible configuration or rejection.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `LAUNCH-02-T05` — Output: M8 gate record.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `OBS-04-T05` — Output: automatic rollback/exception evidence.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `OBS-05-T06` — Output: lessons and bounded eligibility.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `INFRA-02-T04` — Output: signed rollback release.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `BACKEND-01-T08` — Output: implemented BookingGateway sole writer and AvailabilityService/BookingReconciliationService read interfaces for WF-07/PROVIDER-07.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `BACKEND-01-T10` — Output: implemented StrategyActivationService promotion/activation/rollback interface for WF-09 with immutable action attribution.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
- Provider `WF-09-T04` — Output: M6 learning/activation evidence.; Consumer `LAUNCH-04-T03` — Input: current phase-7 checkpoint and all retained safety/recovery/strategy evidence.
