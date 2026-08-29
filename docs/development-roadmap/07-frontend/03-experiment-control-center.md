# Experiment Control Center

**Document ID:** FRONTEND-03
**Status:** Planned M4-M7 operator surface; no product experiment page exists today
**Milestone:** M4 no-send stages, M5 qualification, M6 controlled pilot, M7 decision support
**Owner:** Solo operator
**Prerequisites:** [ARCH-03 experiment/run states](../01-architecture/03-domain-events-and-state-machines.md#experiment-state-machine), [WF-02](../03-workflows/02-experiment-lifecycle.md), [WF-06](../03-workflows/06-pause-cancel-resume-and-recovery.md), [BACKEND-02](../06-backend/02-api-contracts.md), and [FRONTEND-01](01-information-architecture.md)
**Outputs:** Exact experiment/run control page, requested-versus-acknowledged UX, failure exits, campaign entry, and immutable-decision handoff
**Unlocks:** Safe operator execution of M4-M7 and recovery deep links
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

At `/experiments/[experimentId]`, one operator can see canonical experiment and workflow-run truth, start the four BACKEND-02-exposed finite stages, cancel an eligible run, pause/resume/cancel the aggregate under exact guards, retry/revise a failed experiment, create a campaign version, and record an evidence-bound final decision. The page distinguishes command acceptance from workflow acknowledgement and never turns a runtime signal, button state, or progress animation into aggregate truth.

## Current repository state

Only readiness UI and health types exist. There is no experiment resource, workflow run, command endpoint, report, control, polling, authenticated shell, or product error boundary. The full experiment state machine and finite workflow rules are planned. The page and every component below are future work.

## Scope and non-goals

In scope: experiment/run summary, exact canonical states, current brief/version/caps/authority, all four server-exposed finite starts, exact workflow-run cancel, requested/acknowledged progress, failure recovery, campaign creation/deep link, accepted-artifact gate visibility, report panels, and immutable decision command. Non-goals: runtime-native control, client-side transition matrix authority, direct stage invocation absent from BACKEND-02, automatic retries, generic workflow mutation beyond `cancelWorkflowRun`, or local acceptance/decision calculation.

## Exact planned implementation surfaces

Create `src/app/(operator)/experiments/[experimentId]/page.tsx`, its route-local `loading.tsx`/`error.tsx`, `src/features/experiments/components/{experiment-header,authority-ladder,run-status,stage-actions,experiment-controls,failure-exits,campaign-launch,decision-panel}.tsx`, `src/features/experiments/hooks/{use-experiment,use-workflow-run,use-experiment-command}.ts`, `src/features/experiments/state-labels.ts`, and matching unit/browser tests. The Server Component validates the UUID-shaped route param and renders shell/landmarks; client panels own authenticated queries and dialogs.

### Canonical state rendering and authority separation

Render every exact `ExperimentState`: `DRAFT`, `READY_FOR_RESEARCH`, `RESEARCHING`, `READY_FOR_LEADS`, `QUALIFYING_LEADS`, `READY_FOR_OUTREACH`, `OUTREACH_ACTIVE`, `PAUSED`, `EVALUATING`, `DECIDED`, `CANCELLED`, `FAILED`. Render every exact `WorkflowRunState`: `PENDING`, `RUNNING`, `PAUSE_REQUESTED`, `PAUSED`, `CANCEL_REQUESTED`, `CANCELLED`, `SUCCEEDED`, `FAILED`. Unknown values produce a blocking “Unsupported server state” problem, not a fallback action.

The `AuthorityLadder` always shows three independent facts from server resources/reports:

1. M1 production-acceptance evidence state: isolated test infrastructure proof only.
2. M6 owned-inbox pilot evidence plus `TEST_INBOX_SENDING` control state: owned aliases only.
3. `PRODUCT_OUTREACH` control and current product authority: separately authenticated/gated and still not campaign/member/approval/SEND authority.

`READY_FOR_OUTREACH` is preparation, not enabled sending. An approved scope, active campaign, approved message, or enabled control is also insufficient alone. The page explains this deterministic server vocabulary but never combines facts into a client allow/deny.

### Exact operations and behavior

| Concern | URL / `operationId` / response fields | Query or mutation behavior |
| --- | --- | --- |
| experiment | `GET /api/v1/experiments/{experiment_id}`, `getExperiment`; resource `schema_version,data,version,correlation_id`, HTTP ETag | `['experiment',id]`; 5-second poll while active/requested, 15-second otherwise, stop for `DECIDED/CANCELLED`; focus refetch |
| active run | `GET /api/v1/workflow-runs/{workflow_run_id}`, `getWorkflowRun`; canonical projection | `['workflow-run',runId]`; 3-second poll for requested control, 5 seconds nonterminal, stop terminal |
| cancel active run | `POST /api/v1/workflow-runs/{workflow_run_id}/commands/cancel`, `cancelWorkflowRun`; `CancelWorkflowRunRequestV1={schema_version,expected_state:enum[PENDING,RUNNING,PAUSE_REQUESTED,PAUSED],reason_code} -> CommandReceiptV1`, 202 | mutation `["workflow-run",runId,"cancel"]`; active operator session, expected state + one key/CSRF; invalidate run/experiment/recovery/timeline; never infer aggregate cancellation |
| overview | `GET /api/v1/reports/experiments/{experiment_id}/overview`, `getExperimentOverviewReport`; schema/projection/as-of/high-watermark/complete/warnings/correlation plus canonical state/version/paused/failed/retry, caps/authority, run, campaign, controls, incidents, decision | `['report','experiment',id,'overview']`; 15 seconds active, 60 terminal; no local merge into authority |
| approve scope | `POST /api/v1/experiments/{experiment_id}/commands/approve-scope`, `approveExperimentScope`; `ApproveExperimentScopeRequestV1` -> `CommandReceiptV1` | idempotency + latest experiment `If-Match`; explicit authority confirmation; invalidate resource/list/overview/timeline |
| start research | `POST /api/v1/experiments/{experiment_id}/commands/start-research`, `startExperimentResearch`; `StartStageRequestV1 -> CommandReceiptV1` | latest ETag; no optimistic `RESEARCHING`; reconcile resource + returned run ID |
| start qualification | `POST /api/v1/experiments/{experiment_id}/commands/start-lead-qualification`, `startLeadQualification`; `StartStageRequestV1 -> CommandReceiptV1` | latest ETag; no optimistic `QUALIFYING_LEADS`; reconcile resource/run |
| start outreach/reply | `POST /api/v1/experiments/{experiment_id}/commands/start-outreach-and-reply`, `startOutreachAndReply`; `StartOutreachAndReplyRequestV1={schema_version,expected_campaign_id,expected_campaign_version,expected_campaign_state:"ACTIVE",m1_gate_id,m6_gate_id} -> CommandReceiptV1`, 202 | mutation `["experiment",id,"start-outreach-and-reply"]`; active operator session, latest experiment ETag + one key/CSRF; review exact campaign/M1/M6/control/accepted-artifact gates; no optimistic `OUTREACH_ACTIVE`; invalidate experiment/run/campaign/overview/recovery/timeline and poll returned run |
| start evaluation | `POST /api/v1/experiments/{experiment_id}/commands/start-evaluation`, `startExperimentEvaluation`; `StartExperimentEvaluationRequestV1={schema_version,expected_state:enum[READY_FOR_OUTREACH,EVALUATING],metric_snapshot_id,evidence_bundle_artifact_id,rule_version} -> CommandReceiptV1`, 202 | mutation `["experiment",id,"start-evaluation"]`; active operator session, latest experiment ETag + one key/CSRF; exact no-send or closed-outreach accepted evidence; invalidate experiment/run/overview/timeline and render/poll returned finite run; no local decision |
| pause/resume/cancel | `POST /api/v1/experiments/{experiment_id}/commands/pause` (`pauseExperiment`), `POST /api/v1/experiments/{experiment_id}/commands/resume` (`resumeExperiment`), `POST /api/v1/experiments/{experiment_id}/commands/cancel` (`cancelExperiment`); `ControlExperimentRequestV1 -> CommandReceiptV1` | latest ETag, generated reason fields, exact mutation keys `["experiment",id,"pause"]`, `["experiment",id,"resume"]`, or `["experiment",id,"cancel"]`, and one idempotency key; invalidate experiment/run/overview/timeline/recovery; poll requested state to acknowledgement |
| retry stage | `POST /api/v1/experiments/{experiment_id}/commands/retry-stage`, `retryExperimentStage`; `RetryExperimentStageRequestV1 -> CommandReceiptV1` | only server resource exposing `FAILED`; confirmation shows failed-from/retryable/count/limit; result must yield new run ID; never resume prior run |
| revise | `POST /api/v1/experiments/{experiment_id}/commands/revise`, `reviseExperiment`; `ReviseExperimentRequestV1 -> ResourceResponseV1` | latest ETag; link to FRONTEND-02 review; invalidates approvals/campaign/report context; no in-place edit |
| create campaign | `POST /api/v1/experiments/{experiment_id}/campaigns`, `createCampaignVersion`; `CreateCampaignVersionRequestV1 -> CampaignVersionResponseV1` | `['experiment',id,'campaign','create']`, idempotency; navigate to returned exact ID/version, where separate `readyCampaign` and `activateCampaign` are available |
| record decision | `POST /api/v1/experiments/{experiment_id}/commands/record-decision`, `recordExperimentDecision`; `RecordExperimentDecisionRequestV1 -> ResourceResponseV1` | latest ETag; display exact `SCALE/REVISE/KILL/INCONCLUSIVE`, metric snapshot/evidence/rule refs from server; invalidate detail/overview/timeline; no local decision |

The executable sequence is create campaign version -> `readyCampaign` -> `activateCampaign` -> `startOutreachAndReply`; each is a separate confirmed server commit and the stage command renders its finite `workflow_run_id`. Before research, qualification, readiness, outreach, evaluation, approval, or decision dialogs open, the page refetches every required artifact by ID and shows its server-returned status/version/hash; absent, stale, rejected, or superseded acceptance blocks the dialog without calculating acceptance locally. `startExperimentEvaluation` similarly creates a finite run from exact no-send or closed-outreach evidence. `cancelWorkflowRun` maps to internal `CancelRun`, produces only run `CANCEL_REQUESTED`, and never pretends the experiment/campaign is cancelled.

### Page components, states, and command reconciliation

`ExperimentHeader` shows safe code/ID, canonical state, ETag/version, brief version/hash, server UTC and Jerusalem presentation. `RunStatus` shows workflow type/version, run ID/state, attempt/time/cost bounds, requested/acknowledged distinction, and error/retry class only when present in the generated projection. `StageActions` and `FailureExits` render an exhaustive mapping of server-reported facts to known v1 operations; the presence of a button never asserts eligibility. A click always lets the server decide.

Each command uses `CommandDialog`: exact resource/state/version, consequence, reason controls defined by the generated request, and dependent warnings. Outreach/evaluation starts repeat every request evidence ID/version and resulting finite-run contract. Workflow-run cancel repeats run ID/type/state, aggregate effect boundary, evidence that cancellation is currently legal, requires its canonical reason plus the final eight run-ID characters, and after 202 displays/polls that same run. Cancel is destructive and requires typing the safe experiment code (or last eight safe ID characters when no code), plus explicit acknowledgement that cancel is terminal for that version and cannot erase provider outcomes. Pause/resume/retry do not require typed confirmation but require a review dialog. Pending traps repeat activation, sets `aria-busy`, announces receipt status, and preserves the exact request/key across a network-unknown result.

A 202 receipt displays “Request accepted; acknowledgement pending,” `workflow_run_id`, safe result hash/correlation, and polls. A 200 command receipt means command commit, not implied downstream completion. `PAUSE_REQUESTED`/`CANCEL_REQUESTED` remain visibly pending; timeout links to `/recovery`. A new authoritative version after refetch replaces the snapshot. No optimistic badge, progress step, or toast changes state.

Loading skeleton retains headings. Empty means a missing optional current run/campaign/decision and states why. Stale shows last server `as_of`/ETag, disables commands when the required authority snapshot is stale, and offers refetch. Partial report sections show `complete=false` and warnings only where BACKEND-06 permits; missing authoritative source is 503. Redacted values show “Restricted by schema,” not “missing.” `DECIDED` and `CANCELLED` render terminal read-only controls; `FAILED` exposes only retry/revise/cancel.

## Ordered implementation tasks

- [ ] **Render exhaustive experiment/run truth —** Input: generated resources and reports. Operation: map every ARCH-03 state to semantic text/icon/pattern, render versions/timestamps/warnings, and fail closed on unknown values. Output: authoritative control-center header/run view. Test evidence: every-state snapshots and unknown-enum test. Failure behavior: actions disabled with problem details.
- [ ] **Implement stage and control commands —** Input: latest resource ETag, generated requests, operator confirmation. Operation: generate one key, submit exact command, render receipt, invalidate/poll until authoritative state changes or recovery is needed. Output: safe stage-start/pause/resume/experiment-cancel/run-cancel behavior. Test evidence: legal/illegal, 202, signal-failure, double-submit, 412/409, and reload replay fixtures. Failure behavior: requested state remains visible; no false acknowledgement.
- [ ] **Implement closed failure exits and campaign handoff —** Input: server failed fields and campaign request. Operation: expose retry/revise/cancel only, verify new run/version identities, and navigate to exact campaign version. Output: no hidden rewind. Test evidence: five ARCH-03 exit fixtures, exhausted retry, unresolved ambiguity, and campaign create replay. Failure behavior: remain failed/read-only.
- [ ] **Implement immutable decision handoff —** Input: server metric snapshot/evidence/rule references. Operation: confirm one exact decision kind/request and render returned immutable result. Output: decision record, not authority to scale/spend. Test evidence: stale snapshot/version, duplicate decision, each decision kind, no local math. Failure behavior: stay `EVALUATING` and preserve evidence.

## Test strategy

- **States `test_control_center_renders_every_experiment_and_run_state_exhaustively`:** unknown blocks.
- **Acknowledgement `test_accepted_pause_cancel_never_render_acknowledged_before_refetch`:** requested-state polling.
- **Failure `test_failed_experiment_offers_only_retry_revise_cancel_and_retry_has_new_run`:** no terminal resume.
- **Authority `test_ready_for_outreach_and_m1_m6_controls_never_collapse_into_send_enabled`:** independent facts.
- **Contract `test_control_center_network_uses_only_documented_operation_ids`:** exact research/qualification/outreach/evaluation starts and workflow-run cancel; no other runtime endpoint.
- **Accessibility `test_control_dialog_keyboard_focus_live_status_and_terminal_readonly`:** 320/768/1280.

## Security, privacy, compliance, idempotency, observability, and cost

Render safe IDs/hashes and bounded errors, never addresses, content, provider payloads, credentials, or hidden reasoning. Telemetry records operation ID, canonical state before/after as returned, aggregate version, receipt status, polling duration, safe run/experiment IDs, and correlation. It does not record command reason text unless reason is a safe canonical code. Display server-recorded cost/caps only; pause may stop new cost but never subtract already incurred cost client-side.

## Failure, rollback, and operator recovery

On stale version, refresh resource and require re-confirmation. On accepted command without acknowledgement, keep requested state, controls conservative, and link the returned run/correlation to `/recovery`; never send a different command automatically. On unsupported state/schema, disable all commands. UI rollback removes the surface only; backend command/event history remains. Operator recovery uses typed reconcile/repair commands, never runtime console or SQL.

## Acceptance and retained evidence

- [ ] Exact experiment/run states, failure fields, campaign/version, controls, incidents, caps, authority, and decision facts are server-sourced.
- [ ] Every exposed action maps one-to-one to a BACKEND-02 operation and documents key/ETag/invalidation/polling.
- [ ] Requested versus acknowledged control is visible and 202 never claims completion.
- [ ] M1, M6 test inbox, product control, campaign, approval, and final SEND remain separate layers.
- [ ] All loading/empty/stale/error/partial/redacted/terminal states and destructive focus flows pass browser/accessibility tests.

Retain operation network traces, state/receipt fixtures, conflict and acknowledgement timelines, keyboard/axe reports, responsive screenshots, and no-local-authority static scan.

## Dependencies and next deliverable

FRONTEND-03 consumes FRONTEND-02 and BACKEND-02. Campaign creation unlocks [FRONTEND-05](05-lead-and-campaign-management.md); accepted artifacts/evidence and reports feed [FRONTEND-04](04-evidence-and-agent-artifacts.md) and [FRONTEND-08](08-cost-funnel-and-decision-analytics.md); unresolved work routes to [FRONTEND-09](09-error-recovery-and-accessibility.md).
