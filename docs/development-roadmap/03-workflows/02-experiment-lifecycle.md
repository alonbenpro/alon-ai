# Finite Experiment Lifecycle Coordination

**Document ID:** WF-02
**Status:** Planned product workflow; no implementation exists
**Milestone:** M4, M6 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-02-T01 -> WF-02-T02 -> WF-02-T03 -> WF-02-T04 -> WF-02-T05`; cross-document task Inputs `WF-02-T01 <- BACKEND-01-T04,AGENT-10-T05,PROVIDER-03-T06,PROVIDER-04-T05,PROVIDER-05-T05,WF-01-T05,WF-00-T04; WF-02-T05 <- BACKEND-05-T01,WF-06-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): M1 runtime accepted, M2 [DB-01](../02-database/01-core-data-model.md) through [DB-06](../02-database/06-migrations-seeding-and-retention.md), M3 promoted agent/provider contracts, and [ARCH-03 experiment state machine](../01-architecture/03-domain-events-and-state-machines.md#experiment-state-machine)
**Outputs:** Finite per-stage workflow identity, queue/control semantics, exact experiment/run transitions, and evidence handoffs
**Unlocks:** WF-03 idea validation, WF-04 lead qualification, WF-05 outreach/reply, and M7 controls
**Risk:** High
**Complexity:** L

## Outcome and timing

The product does not run one immortal “experiment agent.” Each active experiment stage is a finite durable run with frozen inputs, workflow version, attempt/time/cost bounds, explicit terminal result, and canonical application transition. The experiment aggregate outlives runs; a failed-stage retry creates a new `workflow_run_id`.

## Current repository state

There is no product experiment, transition service, workflow runtime adapter, DBOS workflow, queue, application unit of work, workflow projection, or stage command. The current worker only waits for termination. Every capability below is planned after M1-M3 evidence.

## Scope and non-goals

In scope: starting/ending research, lead, outreach, and evaluation stages; run identity; per-experiment exclusion; finite child workflow invocation; canonical state/event ownership; bounded failure; pause/cancel hooks; and correlation. Non-goals: a daemon per experiment, a workflow deciding business state, automatic `SCALE`, bypassing artifact gates, product send authority, or resuming a terminal failed run.

## Exact planned implementation surfaces

Create `application/experiments.py`, `workflows/experiment_lifecycle.py`, DBOS runtime registration/composition, and contract/recovery tests. Runtime workflow ID is `experiment:{experiment_id}:{stage}:v{workflow_version}:run:{workflow_run_id}`. Queue `alon-ai-experiment-v1` starts at global concurrency `2`, worker concurrency `2`, no start-rate limiter; configuration is pinned/evidenced per release. The database partial unique `uq_workflow_runs_active_experiment_type` on `(experiment_id,workflow_type)` for `PENDING/RUNNING/PAUSE_REQUESTED/PAUSED/CANCEL_REQUESTED` prevents overlapping same-stage runs.

The coordinator accepts IDs/versions only; it loads no live ORM object across steps. Every step invokes an idempotent application command with key `workflow:{workflow_run_id}:step:{step_name}:v{step_version}`.

Every stage producer constructs the DB-01 envelope `{"schema_version":<string>,"payload":<json>}`, RFC-8785-canonicalizes it to UTF-8, and stores the lowercase SHA-256 with the exact text version/payload. Every resume/child consumer recomputes and validates before decoding or upcasting. Only a successful run writes the result triplet; cancellation/failure keeps it SQL NULL. A validator migration verifies old bytes first and transforms only in memory; changed schema/payload starts a new run. WF-03, WF-04, WF-05, and WF-06 use the DB-01 golden vectors.

### Stage and transition contract

| Stage run | Start guard/transition | Completion transition | Failure transition/evidence |
| --- | --- | --- | --- |
| `IDEA_VALIDATION` | operator `StartResearch`; `READY_FOR_RESEARCH -> RESEARCHING`; create run and emit `workflow.run_started.v1` plus `experiment.state_changed.v1` atomically | accepted required artifacts; `RESEARCHING -> READY_FOR_LEADS`; `workflow.run_completed.v1` plus `experiment.state_changed.v1` | `RESEARCHING -> FAILED`; `experiment.failed.v1` and `workflow.run_failed.v1` with retry taxonomy |
| `LEAD_QUALIFICATION` | `StartLeadQualification`; `READY_FOR_LEADS -> QUALIFYING_LEADS`; same start events | lead/sample/evidence gate; `QUALIFYING_LEADS -> READY_FOR_OUTREACH`; completion/state events | `QUALIFYING_LEADS -> FAILED`; canonical failure events |
| `OUTREACH_AND_REPLY` | M6 authority/active campaign; `READY_FOR_OUTREACH -> OUTREACH_ACTIVE`; same start/state events | sample/window closed and all sends terminal/reconciled; `OUTREACH_ACTIVE -> EVALUATING`; completion/state events | only after all in-flight outcomes are terminal/reconciled: `OUTREACH_ACTIVE -> FAILED`; canonical failure events |
| `EXPERIMENT_EVALUATION` | `READY_FOR_OUTREACH` no-send decision or closed outreach; enter/remain `EVALUATING`; create run/start event | operator command records immutable decision; `EVALUATING -> DECIDED`; `experiment.decision_recorded.v1`, state change, and run completion | evaluation can pause; unrecoverable run failure emits `workflow.run_failed.v1` and operator chooses retry/revise/cancel under ARCH-03 |

### Exact table read/write map

| Command/step | Authoritative reads | Atomic writes/constraints | Events |
| --- | --- | --- | --- |
| start stage | `experiments`, active brief/artifact/metric/campaign gates, `system_controls` where relevant, active `workflow_runs` | update `experiments.version/state`; insert `workflow_runs`; `command_idempotency`, `domain_events`, `audit_events`, `outbox_messages`; active-run partial unique | `workflow.run_started.v1`, `experiment.state_changed.v1` |
| child artifact/lead work | immutable IDs decoded only after RFC 8785 envelope verification of `workflow_runs.input_schema_version/input_snapshot/input_hash`; repositories in WF-03/WF-04 | their agent/artifact/evidence/lead tables via application commands; `agent_runs` composite workflow/input-digest FK; command key uniques | artifact/lead catalog events |
| complete stage | run row, experiment expected version, exact acceptance/gate records | atomically store bounded `result_snapshot/result_schema_version/result_hash`, update run terminal + experiment state, and write event/audit/outbox/idempotency | `workflow.run_completed.v1` carries result schema/hash; `experiment.state_changed.v1` |
| fail stage | run/error taxonomy/current experiment | update run `FAILED`; update experiment `FAILED` with failure fields; same transactional safety tables | `workflow.run_failed.v1`, `experiment.failed.v1`, `experiment.state_changed.v1` |

## Ordered implementation tasks

<!-- roadmap-task id=WF-02-T01 milestone=M4 depends_on=BACKEND-01-T04,AGENT-10-T05,PROVIDER-03-T06,PROVIDER-04-T05,PROVIDER-05-T05,WF-01-T05,WF-00-T04 mode=parallel locks=workflow-runtime -->
- [ ] **Implement stage command service —** Input: expected experiment version, stage, frozen prerequisites, command key; signed SelectedRuntimeDecisionV1 selecting DBOS only on acceptance or Temporal only after the identical mandatory fallback suite passed. Operation: apply ARCH-03 transition and atomically create canonical run/events. Output: authoritative run ID/state. Test evidence: exhaustive start guard and duplicate-command tests. Failure behavior: typed denial; no run.
<!-- roadmap-task id=WF-02-T02 milestone=M4 depends_on=WF-02-T01 mode=parallel locks=workflow-runtime -->
- [ ] **Implement finite coordinator —** Input: run/experiment/version IDs. Operation: call the named child workflow/application commands, wait only on durable runtime primitives, and terminate with typed result/error. Output: finite stage result. Test evidence: success/failure/restart/version replay. Failure behavior: sanitized failure report; no direct aggregate write.
<!-- roadmap-task id=WF-02-T03 milestone=M4 depends_on=WF-02-T02 mode=parallel locks=workflow-runtime -->
- [ ] **Implement completion/failure handlers —** Input: child result and expected state/version. Operation: revalidate evidence, close run, transition aggregate, and emit exact events atomically. Output: versioned atomic completion-handler interface plus next canonical state. Test evidence: injected conflict/evidence-revocation/atomicity cases. Failure behavior: run enters operator-visible `FAILED` or result-awaiting-repair; never guess.
<!-- roadmap-task id=WF-02-T04 milestone=M4 depends_on=WF-02-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Enforce active-run exclusion and budgets —** Input: concurrent starts and run caps. Operation: rely on partial unique plus budget reservation before paid work. Output: at most one active same-stage run and bounded cost/time. Test evidence: real-PostgreSQL race and exhaustion tests. Failure behavior: reject second run/call.
<!-- roadmap-task id=WF-02-T05 milestone=M6 depends_on=WF-02-T04,BACKEND-05-T01,WF-06-T03 mode=parallel locks=workflow-runtime -->
- [ ] **Wire pause/cancel/recovery —** Input: the BACKEND-05 authenticated control command plus WF-06 exact ARCH-03 state/event transition result. Operation: invoke WF-06 cooperative/runtime control and recheck guards on resume. Output: complete versioned finite WF-02 workflow contract plus canonical run/experiment states. Test evidence: restart during each control boundary. Failure behavior: fail closed; outreach dequeue remains stopped.

## Test strategy

- **Unit `test_stage_transition_table_matches_arch03`:** exact states/owners/events.
- **Concurrency `test_same_experiment_stage_cannot_have_two_active_runs`:** partial unique is the last defense.
- **Integration `test_start_and_finish_bundle_is_atomic`:** state/run/event/audit/idempotency/outbox.
- **Digest `test_all_stage_inputs_and_results_match_rfc8785_sha256_vectors`:** independent encoders, null/result state, and schema upcast rules.
- **Recovery `test_stage_restarts_from_durable_step_without_repeating_accepted_artifact`:** replay command results.
- **Contract `test_workflow_cannot_mutate_repository_or_provider_directly`:** import/call boundary.
- **Cost `test_stage_stops_before_paid_step_when_reservation_fails`:** no negative budget.

## Security, privacy, compliance, idempotency, observability, and cost

Only authenticated application commands create/control runs. Workflow inputs contain stable IDs/hashes, not credentials or full sensitive content. Each step has a deterministic command key. Trace fields include experiment/run/runtime/workflow/step/version/correlation IDs, safe outcome/retry codes, duration, queue wait, and reserved/reconciled cost. An agent result never becomes a transition without deterministic validation.

## Failure, rollback, and operator recovery

Stop/dequeue controls remain independent of workflow code. A bad workflow version drains or uses the M1-proven patch/version strategy; incompatible in-flight runs never execute new order silently. A terminal failed run is retained; an allowed `RetryExperimentStage` creates a new run and increments retry count. Unknown state/version/evidence opens an incident and blocks mutation.

## Acceptance and retained evidence

- [ ] Every stage is finite, bounded, versioned, correlated, and terminal.
- [ ] Every read/write maps to exact M2 tables/constraints and every transition/event matches ARCH-03.
- [ ] Application command service, never runtime/agent/provider, owns aggregate state.
- [ ] Same-stage concurrency and command replay cannot duplicate work.
- [ ] Outreach stage is impossible without the M1/M6 authority rules.

Retain transition/guard snapshot, queue config, import rules, PostgreSQL races, restart/version/control traces, event fixtures, and cost-cap evidence.

## Dependencies and next deliverable

WF-02 depends on accepted runtime, complete M2 persistence, and promoted M3 contracts. It unlocks [WF-03](03-idea-validation-workflow.md), then [WF-04](04-lead-qualification-workflow.md), and only after M6 prerequisites [WF-05](05-outreach-and-reply-workflow.md).
