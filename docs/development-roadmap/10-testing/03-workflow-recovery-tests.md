# Durable Workflow, Crash, and Recovery Tests

**Document ID:** TEST-03
**Status:** Planned M1-M8 recovery suite; no DBOS product workflow, Temporal adapter, kill harness, workflow projection, or typed repair implementation exists today
**Milestone:** M1, M6, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `TEST-03-T01 -> TEST-03-T02 -> TEST-03-T03 -> TEST-03-T04 -> TEST-03-T05 -> TEST-03-T06 -> TEST-03-T07`; cross-document task Inputs `TEST-03-T01 <- WF-01-T01,WF-01-T02,WF-01-T03,TEST-01-T03; TEST-03-T02 <- WF-01-T01,WF-01-T02,WF-01-T03,TEST-01-T04; TEST-03-T03 <- WF-01-T05; TEST-03-T04 <- TEST-02-T02,ARCH-03-T01,WF-02-T05,WF-03-T05,WF-04-T05; TEST-03-T05 <- WF-06-T04; TEST-03-T06 <- INFRA-04-T02,WF-06-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [WF-00 runtime gate](../03-workflows/00-dbos-selection-and-temporal-fallback.md), [WF-01 production-acceptance spike](../03-workflows/01-dbos-production-acceptance-spike.md), WF-02 through WF-06, DB-01/05/06, OBS-04/05, TEST-01/02
**Outputs:** Finite-workflow transition matrix, kill-point harness, replay/version/cancellation proof, DBOS decision evidence or mandatory Temporal handoff, and no-SQL repair/restore evidence
**Unlocks:** M1 acceptance or Temporal migration, M6 controlled Gmail pilot, and M8 workflow operations
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Staged-validation recovery kills the process before/after membership claim, final capacity reservation, send intent, provider ambiguity, observation close, barrier commit, and next-stage admission. Every replay retains the exact stage/membership hash, never exceeds incremental or cumulative capacity, never reuses a recipient, and never opens Stage 2-4 unless the immediately prior decision is durably signed `CONTINUE`.

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

Every requirement in this document maps exactly to `T7-WORKFLOW-RECOVERY` in the [TEST-01 closed command manifest](01-testing-strategy.md#closed-command-manifest). The launcher first loads readonly `TASK7_SIGNED_CHECKOUT` from the verified repository-identity manifest and requires it to be the physical absolute signed checkout with no symlink; from repository root, `backend/`, `frontend/`, or `/tmp`, the exact invocation is `"$TASK7_SIGNED_CHECKOUT/scripts/task7/run" --manifest tests/manifests/task7-commands.v1.json --command T7-WORKFLOW-RECOVERY --run-id "$TASK7_RUN_ID" --evidence-root "$TASK7_EVIDENCE_ROOT" --profile DBOS_EPHEMERAL --target-manifest "$TASK7_TARGET_MANIFEST"`. Only argv[0] is materialized from that manifest-bound absolute root; the remaining normalized arguments byte-match TEST-01 and are resolved by the runner against its own verified root, never caller cwd. The immutable scenario fixture supplies runtime/version, barrier, expected state/event/row/call sets and timeout; the runner proves the ephemeral database/system identifier and disposable process group before killing anything. A missing DBOS/Temporal binary exits `30`, a target/process mismatch exits `50`, and any incomplete kill/evidence set exits `40`; none is a pass.

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

<!-- roadmap-task id=TEST-03-T01 milestone=M1 depends_on=WF-01-T01,WF-01-T02,WF-01-T03,TEST-01-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Build the process-level kill harness —** Input: runtime adapter, scenario/barrier manifest and fresh database. Operation: terminate API/worker at exact boundaries, cold-start with new connections, and capture before/after truth. Output: reproducible crash traces. Test evidence: harness self-test proves handled exceptions cannot masquerade as process death. Failure behavior: scenario invalid and no gate credit.
<!-- roadmap-task id=TEST-03-T02 milestone=M1 depends_on=TEST-03-T01,WF-01-T01,WF-01-T02,WF-01-T03,TEST-01-T04 mode=serial locks=workflow-runtime,gmail-side-effects,milestone-gate,live-environment -->
- [ ] **Execute the independent M1 runtime matrix —** Input: WF-01 disposable schema, runnable typed fixture, K0-K8 crash harness, exact repetition/version manifest, and TEST-01 signed evidence conventions; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: run the exact independent M1 matrix and retain all raw traces and a discriminated pass/rejection scorecard; a conclusive DBOS failure is retained rejection evidence, not a missing task result; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed independent raw run/scorecard evidence, including terminal/reconciled state or explicitly identified unresolved isolated state and DBOS rejection reasons. Test evidence: all required cases/repetitions have hashes and recorded outcomes; incomplete/corrupt execution is distinguished from a conclusive rejected runtime. Failure behavior: corrupt/missing/incomplete evidence blocks; a complete signed rejection closes this adjudication task with controls off so fallback remains schedulable.
<!-- roadmap-task id=TEST-03-T03 milestone=M1 depends_on=TEST-03-T02,WF-01-T05 mode=serial locks=milestone-gate,workflow-runtime -->
- [ ] **Independently verify the exported M1 acceptance or rejection bundle —** Input: WF-01 interoperable exported gate bundle and TEST-03 independent raw traces/scorecard with exact schema/fixture/K0-K8/repetition identities; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: independently validate canonical exports, hashes, fresh restore/re-export and complete success-or-rejection evidence against the original exact M1 matrix; certify acceptance only on 8/8 and otherwise certify the complete reasoned DBOS rejection; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: independently checked complete signed M1 acceptance-or-rejection evidence manifest, with DBOS acceptance only on 8/8. Test evidence: accepted branch requires the original exact 8/8/K0-K8 matrix, zero duplicates/blind retries and byte-identical authenticated exports; rejected branch requires complete authentic failed-criterion evidence and correct DBOS_REJECTED classification with all controls off, including a negative fixture containing a real recorded duplicate or blind retry that completes rejection adjudication but cannot yield DBOS acceptance; malformed/incomplete/tampered evidence remains blocking. Failure behavior: incomplete/corrupt evidence blocks; a conclusive signed DBOS rejection completes evidence adjudication and requires mandatory Temporal acceptance before any product runtime selection.
<!-- roadmap-task id=TEST-03-T04 milestone=M6 depends_on=TEST-03-T03,TEST-02-T02,ARCH-03-T01,WF-02-T05,WF-03-T05,WF-04-T05 mode=parallel locks=workflow-runtime -->
- [ ] **Prove every finite workflow and delivery edge —** Input: ARCH-03 canonical states/events, TEST-02 DB read/write maps, and complete versioned WF-02, WF-03, and WF-04 workflow contracts. Operation: inject failures at each command/step/transaction/delivery/snapshot edge. Output: executable versioned finite-workflow/delivery-edge failure-injection suite plus complete state-event-row-result matrix. Test evidence: legal/illegal transition and digest set equality. Failure behavior: owning milestone remains blocked.
<!-- roadmap-task id=TEST-03-T05 milestone=M6 depends_on=TEST-03-T04,WF-06-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Prove controls, versioning and migration —** Input: WF-06 terminal-or-quarantined control ledger plus pause/cancel/resume/retry and v1/v2/rollback scenarios. Operation: kill around request/signal/ack, drain in-flight runs, and preserve application IDs/correlation. Output: operator-visible bounded recovery. Test evidence: no post-bound call and no wrong-version replay. Failure behavior: stop/dequeue disabled and incident open.
<!-- roadmap-task id=TEST-03-T06 milestone=M8 depends_on=TEST-03-T05,INFRA-04-T02,WF-06-T05 mode=serial locks=backup-restore,workflow-runtime -->
- [ ] **Prove typed repair and isolated restore —** Input: WF-06 auditable recovery service/evidence, corrupted projection/outbox/runtime-mapping fixtures, and an independently verified backup chain. Operation: compare authoritative records, run only compatible repair kind or isolated restore, then rerun affected matrix. Output: executable versioned typed-repair/isolated-restore recovery-matrix suite interface plus signed recovery proof. Test evidence: direct SQL/free-form repair/provider call spies remain zero. Failure behavior: system remains degraded/off.
<!-- roadmap-task id=TEST-03-T07 milestone=M8 depends_on=TEST-03-T06 mode=serial locks=test-command-registry -->
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
