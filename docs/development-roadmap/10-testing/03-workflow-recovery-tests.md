# Durable Workflow, Crash, and Recovery Tests

**Document ID:** TEST-03
**Status:** Planned M1-M8 recovery suite; no DBOS product workflow, Temporal adapter, kill harness, workflow projection, or typed repair implementation exists today
**Milestone:** M1 runtime acceptance, M4-M6 finite workflows, M8 recovery gate
**Owner:** Solo operator
**Prerequisites:** [WF-00 runtime gate](../03-workflows/00-dbos-selection-and-temporal-fallback.md), [WF-01 production-acceptance spike](../03-workflows/01-dbos-production-acceptance-spike.md), WF-02 through WF-06, DB-01/05/06, OBS-04/05, TEST-01/02
**Outputs:** Finite-workflow transition matrix, kill-point harness, replay/version/cancellation proof, DBOS decision evidence or mandatory Temporal handoff, and no-SQL repair/restore evidence
**Unlocks:** M1 acceptance or Temporal migration, M6 controlled Gmail pilot, and M8 workflow operations
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Every finite workflow and control/recovery boundary survives hard process termination, duplicate delivery, replay, version change, cancellation, database failure, and operator retry without hidden state, immortal loops, external-effect replay, or direct SQL. DBOS remains eligible only after all eight M1 criteria pass across K0-K8; any canonical disqualifier immediately makes Temporal mandatory before M2 workflow work.

## Current repository state

The lockfile includes DBOS/Pydantic AI, but `workflows/` is a reserved marker and the worker only starts idle. No runtime adapter, queue, timer, schedule, product `workflow_runs`, kill barriers, recovery projection, version router, pause/cancel acknowledgment, Temporal worker, or signed M1 evidence exists. Current tests cannot claim durable recovery.

## Scope and non-goals

In scope: exact M1 two-table harness, K0-K8, eight non-waivable criteria, all legal/illegal experiment/run/campaign/message transitions, idea/offer/lead/outreach/reply/evaluation/history/retention workflows, snapshot digest verify-before-use, command/outbox dedupe, pause/cancel/resume/retry, runtime migration/version drain, OAuth handoff, typed repair and restore compatibility. Non-goals: killing by handled exceptions, engine history as product truth, infinite agent loops, provider retry from workflow code, manual DB correction, or averaging a flaky disqualifier.

## Exact planned implementation surfaces

Create `backend/tests/recovery/`, deterministic barrier controller `tests/recovery/kill_barriers.py`, disposable process supervisor, runtime-neutral scenario schema `workflow.recovery.scenario.v1`, and evidence collector that records process PID/start, runtime/application IDs, barrier, command/queue delivery, DB transaction boundaries, provider spy count, states/events/hashes, recovery duration and final invariant.

| Matrix family | Required boundaries | Hard pass |
| --- | --- | --- |
| M1 DBOS | exact K0 before run insert; K1 run/enqueue; K2 intent/dequeue; K3 gateway/call; K4 bytes left/unknown; K5 accepted/pre-commit; K6 sent/pre-completion; K7 reconciliation; K8 concurrent rate/window replacement | all eight WF-00 criteria pass every approved repetition; zero uncontrolled duplicate/blind retry; exact signed two-table evidence |
| finite lifecycle | before/after every command claim, aggregate/event/audit/idempotency/outbox commit, child start/result, snapshot read/result write and terminal transition | only ARCH-03 legal states/events; digest verified before use; one sole writer; bounded terminal/visible failed state |
| delivery | publisher before/after outbox receipt and duplicate/poison delivery | at-least-once transport, exactly-once business effect by consumer key; dead-letter incident; no external effect |
| controls | request commit, runtime signal, safe-boundary ack, process death, resume/retry/version drain | no new child/provider start after confirmed bound; pending remains visible; resume revalidates current authority |
| runtime version | v1 in flight while v2 deploys, rollback, patch/version mismatch and worker loss | correct version completes/drains or remains blocked; no history mutation/stranded run |
| repair/restore | runtime/product disagreement, corrupted projection, missing outbox link, isolated restore | registered repair kind with before/after hashes or restore; sessions revoked, controls false, no provider call |

Finite coverage includes `experiment_lifecycle`, `idea_validation`, `lead_qualification`, `outreach_and_reply`, `gmail_reconciliation`, `gmail_history_sync`, agent evaluation capture/scoring coordination, retention batches, backup verification, and incident exercises. The manifest derives exact workflow/run/campaign/message state and event sets from ARCH-03 and rejects unregistered names.

Every requirement in this document maps exactly to `T7-WORKFLOW-RECOVERY` in the [TEST-01 closed command manifest](01-testing-strategy.md#closed-command-manifest), invoked from the repository root as `./scripts/task7/run --manifest tests/manifests/task7-commands.v1.json --command T7-WORKFLOW-RECOVERY --run-id "$TASK7_RUN_ID" --evidence-root "$TASK7_EVIDENCE_ROOT" --profile DBOS_EPHEMERAL --target-manifest "$TASK7_TARGET_MANIFEST"`. The immutable scenario fixture supplies runtime/version, barrier, expected state/event/row/call sets and timeout; the runner proves the ephemeral database/system identifier and disposable process group before killing anything. A missing DBOS/Temporal binary exits `30`, a target/process mismatch exits `50`, and any incomplete kill/evidence set exits `40`; none is a pass.

Reference harness pseudocode:

```python
scenario.prepare_fresh_database_and_fixture()
supervisor.start(runtime=scenario.runtime_version)
barrier.arm(scenario.kill_point)
scenario.dispatch_same_command_key()
barrier.wait_until_reached(timeout=scenario.bound_seconds)
supervisor.hard_kill()  # OS process termination, not a handled exception
snapshot = evidence.capture_database_and_provider_spy()
supervisor.cold_start(runtime=scenario.recovery_version)
scenario.await_terminal_or_visible_blocked()
assert_invariants(snapshot, scenario.expected_rows_events_calls)
evidence.sign_manifest_last()
```

## Ordered implementation tasks

- [ ] **Build the process-level kill harness —** Input: runtime adapter, scenario/barrier manifest and fresh database. Operation: terminate API/worker at exact boundaries, cold-start with new connections, and capture before/after truth. Output: reproducible crash traces. Test evidence: harness self-test proves handled exceptions cannot masquerade as process death. Failure behavior: scenario invalid and no gate credit.
- [ ] **Execute the M1 DBOS matrix —** Input: exact WF-01 schema/fixtures/K0-K8/repetitions. Operation: run all eight criteria from clean state and validate signed canonical exports/restore. Output: `DBOS_ACCEPTED` only on 8/8. Test evidence: zero duplicates/blind retries and byte-identical evidence. Failure behavior: `DBOS_REJECTED`, controls false, critical incident and mandatory Temporal handoff.
- [ ] **Prove every finite workflow and delivery edge —** Input: ARCH-03 states/events, DB read/write maps and workflow versions. Operation: inject failures at each command/step/transaction/delivery/snapshot edge. Output: complete state-event-row-result matrix. Test evidence: legal/illegal transition and digest set equality. Failure behavior: owning milestone remains blocked.
- [ ] **Prove controls, versioning and migration —** Input: pause/cancel/resume/retry and v1/v2/rollback scenarios. Operation: kill around request/signal/ack, drain in-flight runs, and preserve application IDs/correlation. Output: operator-visible bounded recovery. Test evidence: no post-bound call and no wrong-version replay. Failure behavior: stop/dequeue disabled and incident open.
- [ ] **Prove typed repair and isolated restore —** Input: corrupted projection/outbox/runtime mapping fixtures and verified backup. Operation: compare authoritative records, run only compatible repair kind or isolated restore, then rerun affected matrix. Output: signed recovery proof. Test evidence: direct SQL/free-form repair/provider call spies remain zero. Failure behavior: system remains degraded/off.
- [ ] **Close command ownership —** Input: every M1/finite/delivery/control/version/repair scenario ID. Operation: prove exact set equality to `T7-WORKFLOW-RECOVERY`, its immutable fixture/profile, target guard and declared artifacts. Output: one signed command mapping. Test evidence: missing/duplicate scenario and unavailable-runtime negatives. Failure behavior: recovery gate remains failed.

## Test strategy

- **M1 `test_k0_through_k8_and_all_eight_dbos_criteria_pass_or_trigger_temporal`.**
- **Finite `test_every_registered_workflow_state_event_command_and_terminal_exit_is_closed`.**
- **Digest `test_workflow_input_and_result_snapshots_verify_rfc8785_before_dispatch_or_consumption`.**
- **Delivery `test_duplicate_and_poison_outbox_delivery_never_duplicates_business_or_external_effect`.**
- **Control `test_kill_at_request_signal_ack_and_resume_never_starts_work_after_confirmed_stop`.**
- **Version `test_v1_inflight_v2_deploy_and_rollback_route_to_compatible_worker_without_history_edit`.**
- **Repair `test_only_registered_repair_or_isolated_restore_resolves_runtime_product_disagreement`.**

## Security, privacy, compliance, idempotency, observability, and cost

The ordinary recovery suite uses provider spies and synthetic data. M1 uses only owned aliases, a separate Google project/credential and exact two-table schema under hard send/cash/time caps. Evidence is redacted and correlation-rich but excludes recipient/token/content. Same command key proves replay; a retryable failed stage creates a new application run ID exactly as WF-06 defines. Runtime metrics/logs are hints; database/provider evidence is authoritative.

## Failure, rollback, and operator recovery

Any duplicate, blind retry, post-control call, hidden ambiguity, rate/concurrency breach, wrong-version recovery, unverifiable snapshot, missing event, manual edit, or flake fails the owning gate. Stop queues/workers, keep both controls false, reconcile possible side effects, preserve signed evidence, and use the applicable IR-02/07 runbook. A DBOS M1 failure cannot be fixed by changing the criterion; execute the Temporal adapter handoff and rerun the identical matrix.

## Acceptance and retained evidence

- [ ] K0-K8 and all eight non-waivable M1 criteria have reproducible process-kill evidence.
- [ ] Every finite workflow has closed states/events/exits, verified snapshots and failure injection at every durable boundary.
- [ ] Pause/cancel/resume/retry/version drain and repair never hide work or require SQL.
- [ ] Any DBOS disqualifier produces Temporal migration evidence, never a waiver.

Retain scenario/barrier/runtime manifests, process and DB/provider traces, state/event/row/call matrices, canonical M1 files/signatures, version-drain evidence, repair/restore reports, incidents and cost/send-cap proofs.

## Dependencies and next deliverable

TEST-03 consumes TEST-02 boundary proof and supplies crash semantics to [TEST-04 Gmail](04-gmail-side-effect-tests.md), [INFRA-02 release](../11-infrastructure/02-ci-cd-and-release-process.md), and [INFRA-05 DR](../11-infrastructure/05-monitoring-and-disaster-recovery.md). A passing runtime suite only unlocks the next milestone gate; it never enables outreach.
