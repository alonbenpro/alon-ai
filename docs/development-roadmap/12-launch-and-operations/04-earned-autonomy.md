# Earned Autonomy for Reversible Internal Work

**Document ID:** LAUNCH-04
**Status:** Planned post-M9 internal capability ladder; no agent runtime, scheduler, promotion registry, operating population, or earned autonomy exists today
**Milestone:** M9 and post-M9 operations
**Owner:** Solo operator
**Prerequisites:** Current M0-M8 safety/operations gates, a closed [LAUNCH-03](03-first-real-experiment.md) decision, promoted [AGENT-10 configurations](../04-agents/10-agent-evals-and-versioning.md), continuous [OBS-04 evaluation](../09-observability-and-evaluation/04-agent-and-workflow-evaluations.md), exact budgets and no unresolved blocking incident
**Outputs:** Finite capability-level definitions, signed promotion/demotion records, observation populations/windows, scheduler caps, human boundaries, version bindings and rollback evidence
**Unlocks:** Only the next explicitly named reversible internal capability level; never recipient, Gmail, approval, policy, legal, control, credential, deletion, recovery-cutover or scaling authority
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Autonomy is earned capability by capability from retained behavior, not granted because an experiment had a promising reply. The highest level may schedule only reversible internal research, typed artifact production, deterministic evaluation and bounded no-send workflows. Every output remains advisory or awaiting the existing deterministic/operator owner.

Observation windows below are minimum operational-control populations, not delivery estimates. Before a window starts, the operator signs the exact chronological cohort query and representative workload/evaluation allocation. Every attempt admitted under that frozen rule counts in order, including degraded, billed, cancelled and missing-terminal attempts. Binding drift closes the cohort as failed/incomplete and requires a reviewed new version and new cohort; it never licenses an exclusion or query rewrite.

## Current repository state

Pydantic AI, Pydantic Evals and DBOS are locked dependencies, but agents/workflows are empty boundaries and DBOS M1 is unrun. There are no 46 product tables, scheduler, eight-suite/552-case evaluation system, `PromotionManifestV1` registry, artifact acceptance flow, provider implementation, rolling runtime population, autonomy record, or production/internal run. All autonomy starts at zero.

## Scope and non-goals

In scope: four exact levels; exact provider/agent/workflow capability sets; minimum populations/windows; promotion thresholds; daily/total/concurrency/cost caps; operator approvals; immediate/rolling demotion; configuration/model/provider/version binding; immutable records; rollback; and evidence retention.

Non-goals: self-modifying prompts/models/tools/policy, automatic promotion, online learning, hidden chain-of-thought, Gmail/send/reply actions, real-recipient selection, artifact acceptance, qualification/state authority, approvals, control enable, suppression deactivation, budget/cap changes, legal/consent decisions, credential access, evidence deletion, restore cutover, incident resolution, release promotion, autonomous scale/revise/kill, or bypassing `SendGateway`.

## Exact planned implementation surfaces

This ladder adds no product table, endpoint, event, provider capability, agent artifact, workflow, service or Task 7 command. Signed level decisions remain immutable gate/release audit evidence. Agent configuration eligibility continues to use the existing `PromotionManifestV1`; product artifacts remain the canonical types; capability calls remain exactly `model.complete_structured`, `evidence.read`, `search.query`, `page.extract`, `business.search`, and `business.details`; agent types remain the exact eight AGENT-01 values; finite internal workflow scope is only WF-02/03/04. WF-05 outreach/reply and every Gmail capability are permanently outside the ladder.

### Exact levels and execution envelopes

| Level | Newly permitted scheduled capability | Daily/total/concurrency envelope | Minimum evidence to request promotion |
| --- | --- | --- | --- |
| `EA0_OPERATOR_STARTED` | none; operator explicitly starts each eligible internal research, artifact, evaluation or no-send workflow run | scheduled starts `0`; each operator-started run still obeys its immutable brief/run/provider budgets | baseline level; no earned grant |
| `EA1_RESEARCH_SCHEDULED` | schedule approved read-only research using only the exact allowlisted provider capabilities and promoted typed research configuration; no artifact acceptance/materialization | at most 5 starts per rolling 24 hours, 25 per immutable brief version, 1 active run | at least 30 admitted EA0 operator-started research attempts across 14 consecutive complete days and at least 5 admitted terminal calls for every requested provider capability |
| `EA2_ARTIFACT_EVAL_SCHEDULED` | additionally schedule promoted typed agent artifact production and network-disabled deterministic validation/evaluation; outputs remain `PRODUCED`/review-pending | at most 10 starts per rolling 24 hours, 50 per immutable brief version, 2 active runs | at least 60 admitted EA1 scheduled research attempts across 30 consecutive complete days and at least 10 admitted terminal calls per promoted provider capability |
| `EA3_INTERNAL_WORKFLOW_SCHEDULED` | additionally schedule finite no-send WF-02/03/04 runs inside one operator-approved immutable brief/version; no WF-05/send/reply stage | at most 20 starts per rolling 24 hours, 100 per immutable brief version, 2 active workflow runs | at least 120 admitted EA2 artifact/evaluation attempts across 60 consecutive complete days, at least 20 admitted attempts per requested agent type and 10 per requested WF-02/03/04 workflow type |

The most restrictive brief, provider, run, experiment, deployment and level cap wins. No level carries unused quota forward or raises a budget. Each scheduled run has a finite deadline/step/tool/model/cost envelope and creates no successor beyond the remaining signed total.

### Promotion thresholds and signed binding

Before the first admission in any observation window, the operator signs: requested capability and current level; chronological `[start_at,end_at)` boundaries and minimum `N`; the exact authoritative cohort-query text/hash; source/release/runtime/database/config/model/prompt/tool/provider/request/result/schema/validator/policy bindings; the representative workload/evaluation slice IDs, allocations and seeds; the eligible-input predicate; admission point; terminal taxonomy; applicable provenance gates; ceilings/thresholds; and immutable rollback target. The query returns run IDs mechanically in chronological `(admitted_at, run_id)` order. Neither the operator nor an agent may provide a hand-picked run-ID list.

Admission commits before execution or any provider call. Every admitted attempt inside `[start_at,end_at)` remains in the denominator: success, billed/conclusive failure, provider timeout or ambiguity, abstention, cancellation, schema/validation failure, provenance failure, ledger/cost/authority failure, cap/deadline failure, or missing terminal evidence. Only an input rejected before admission by the frozen eligible-input rule is outside the denominator, and its immutable rejection record must contain the signed reason and input/slice/query binding. There is no post-hoc exclusion, relabel, expected-outcome rewrite, slice reallocation or cohort-query change.

Every requested capability must independently satisfy all thresholds over its full admitted denominator and minimum population: zero authority/import/network-policy violation; zero secret/PII/recipient-hash leak; zero unrecorded provider call or cost; 100% strict terminal schema, signature/hash and ledger completeness; 100% hard-safety gate pass; 100% of all applicable deterministic provenance gates; at least 95% successful terminal outcomes within time/cost ceilings; zero unresolved Critical/High incident; and exact authoritative DB/telemetry/cohort-query counts. Abstention and typed failure can be safe runtime behavior, but remain promotion-denominator failures.

The operator reviews and signs each one-level promotion. The immutable decision binds prior/new level, exact capability/agent/workflow allowlists, the pre-signed query and mechanically returned run IDs, window boundaries/minimum `N`, eligible/rejected/admitted set equality, workload/evaluation allocation, terminal-taxonomy counts, threshold calculations, source/release/runtime/database schema, active `PromotionManifestV1` IDs, model/prompt/tool/provider/request/result/fixture/policy/validator versions and hashes, budgets/caps, current M1/M6/M8 evidence, incidents, approval UTC/expiry and rollback target. Promotion of one capability does not promote another; levels cannot be skipped.

### Human boundaries and permanent forbidden actions

| Action | Human/deterministic owner at every level |
| --- | --- |
| create/change `ExperimentBrief`, offer, campaign, recipient cohort, success/kill rule or cap | operator, new immutable version |
| promote/rollback model, prompt, tool, provider, runtime, release or autonomy level | operator after exact evaluation/recovery evidence |
| validate/accept/reject/supersede product artifact or materialize business state | canonical deterministic validator/service plus operator where specified |
| decide qualification, state transition, policy, suppression, jurisdiction, consent, legal compliance or budget admission | existing deterministic owner; counsel/operator own legal/approval decisions |
| approve message, create send intent, enable either control, access Gmail credential or call Gmail | operator/deterministic policy/`SendGateway`; never an agent or autonomy scheduler |
| deactivate suppression, delete evidence/data, commit purge, restore/cut over, resolve incident or re-enable after recovery | authenticated operator through canonical command/runbook and separate evidence |

Permanent forbidden actions are direct/indirect Gmail access; `SendGateway` bypass; recipient selection/contact/follow-up; operator approval; policy/control/legal/consent/credential decisions; suppression deactivation; budget/cap increase; evidence mutation/deletion; unregistered provider/tool/network access; raw SQL/business-state mutation; public ingress publication; incident closure; backup deletion/restore cutover; release promotion; and autonomous `SCALE|REVISE|KILL`. Tool indirection, workflow nesting or “highest autonomy” never changes the prohibition.

### Demotion, rollback and re-entry

Any authority edge, wrong/unknown network call, secret/PII/recipient-hash leak, unrecorded or ambiguous provider/cost result, hard-safety failure, post-admission provenance/evidence-integrity failure, budget/cap/concurrency breach, cohort-query/manifest/config drift, post-hoc exclusion/relabel, Critical/High incident, policy/legal/security/backup/AWS witness/telemetry blindness, failed restore, or unapproved schedule immediately sets the affected capability to `EA0_OPERATOR_STARTED`, stops new schedules, preserves in-flight evidence and invokes the canonical incident/control path. Sending controls remain false where relevant. One post-admission provenance or evidence-integrity failure is enough: pause the capability, demote immediately to EA0, open the incident, complete operator review, issue a new reviewed version and start a wholly new pre-registered cohort.

Two adjacent non-overlapping windows of 20 admitted runs with successful-terminal rate below 95%, deterministic non-provenance validation pass below 95%, or p95 duration/cost above the registered ceiling demote exactly one level; a single max-cost breach, hard failure or any applicable provenance/evidence-integrity failure demotes immediately to EA0. Windows order by `(admitted_at, run_id)`, include every admitted failure and missing terminal, and reset only after a reviewed promotion/rollback/version change.

Rollback disables the scheduler before changing pointers, drains or version-routes compatible in-flight runs, changes new-run agent/runtime/release pointers only through the existing signed promotion/release process, records a new immutable demotion decision referencing the prior record, and keeps historical outputs/ledgers. Re-entry requires root-cause/incident closure, fresh version-specific evaluation, a new signed cohort query/allocation, the full minimum population/window at the lower level and a new operator signature; old observations, failed cohorts and observations under a changed binding cannot be reused.

## Ordered implementation tasks

- [ ] **Freeze levels, scopes and caps —** Input: this exact four-level set, provider/agent/workflow registries and budget hierarchy. Operation: implement deny-by-default scheduler admission with one-level scope and immutable version binding. Output: bounded internal eligibility. Test evidence: unknown/skip/cross-capability/WF-05/cap-carryover negatives. Failure behavior: EA0 and no schedule.
- [ ] **Pre-register and compute promotion populations exactly —** Input: signed `[start_at,end_at)`/minimum-`N` cohort query, representative slice allocation, eligible-input/admission rule, terminal taxonomy, chronological attempts, ledgers, validations, provenance, costs and incidents. Operation: admit before execution/provider access, include every admitted attempt, allow only signed pre-admission rejection outside the denominator, and calculate exact set equality/populations/windows/thresholds. Output: reviewable non-cherry-picked promotion calculation. Test evidence: query/boundary/count/day, hand-picked ID, post-hoc exclusion/relabel, rejected-before-admission, billed failure, timeout, abstention, cancellation, missing terminal, percentile and reset cases. Failure behavior: no promotion; provenance/evidence-integrity failure immediately pauses and demotes to EA0.
- [ ] **Require operator-signed one-level promotion —** Input: complete calculation, active release/config/gates and rollback target. Operation: review capability-specific scope and sign immutable decision. Output: exact new allowlist/caps for new runs. Test evidence: concurrency/stale signature/level-skip/cap-increase/model-drift rejection. Failure behavior: prior level remains.
- [ ] **Enforce permanent authority boundaries —** Input: scheduler/tool/import/call graph and runtime spies. Operation: permit only internal typed calls and prove every forbidden owner/path unreachable. Output: no-authority evidence. Test evidence: Gmail/SendGateway/control/approval/policy/legal/credential/delete/public/restore/release probes. Failure behavior: immediate EA0/incident.
- [ ] **Implement demotion and rollback —** Input: immediate triggers and exact rolling windows. Operation: stop schedules, preserve/drain, change version pointers through existing owners and require fresh lower-level re-entry. Output: fail-closed autonomy reduction. Test evidence: every trigger, two-window threshold, mid-run crash and incompatible rollback. Failure behavior: affected internal stage remains paused.

## Test strategy

- **Levels `test_autonomy_levels_equal_exact_ea0_through_ea3_set_and_cannot_skip`.**
- **Populations `test_each_promotion_requires_exact_minimum_runs_days_per_capability_and_binding`.**
- **Cohort `test_promotion_query_and_representative_slice_are_signed_before_window_and_return_every_admitted_attempt_in_order`.**
- **Denominator `test_billed_failure_timeout_abstention_cancellation_schema_provenance_ledger_cost_authority_and_missing_terminal_all_count_as_failures`.**
- **Provenance `test_one_post_admission_provenance_or_evidence_integrity_failure_pauses_capability_demotes_ea0_and_requires_new_version_and_cohort`.**
- **Caps `test_level_daily_total_concurrency_and_budget_caps_use_the_most_restrictive_bound`.**
- **Authority `test_highest_autonomy_cannot_send_approve_control_decide_delete_restore_publish_or_promote_itself`.**
- **Demotion `test_immediate_triggers_force_ea0_and_two_bad_twenty_run_windows_drop_one_level`.**
- **Rollback `test_changed_model_prompt_tool_provider_runtime_or_release_invalidates_affected_observation_window`.**

## Security, privacy, compliance, idempotency, observability, and cost

Scheduler identity has no operator, credential, control, Gmail, public-edge, deletion or restore role. Every start is idempotent by immutable brief/capability/config/schedule identity; replay cannot exceed caps. Inputs/outputs follow DB-06 sensitivity and contain no recipient hash/address/secret in telemetry. OBS records bounded level/capability/config/outcome/reason labels and authoritative population/cost counts. Calls reserve/reconcile original currency and ILS evidence before more work. Higher throughput is never compensation for low evidence quality or operator overload.

## Failure, rollback, and operator recovery

The safe default is EA0 with schedules off. On a trigger, stop admission before analysis, preserve the frozen query/allocation and all admitted/rejected/run/cost/provider/provenance evidence, disable affected provider credentials when needed, open the canonical incident and compare PostgreSQL to provider/telemetry truth. Do not edit a population/query/slice, hand-pick IDs, relabel or exclude a failure, delete a hard case, loosen a threshold, expand a window/cap, automatically re-enable, or allow a successful later run to cancel a prior authority or provenance violation.

## Acceptance and retained evidence

- [ ] Exact four levels, finite capabilities and caps are implemented deny-by-default and version-bound.
- [ ] Promotions use pre-registered chronological queries/representative slices, complete admitted denominators/minimum populations/windows and all 100%-provenance/zero-tolerance/95%-success thresholds with one explicit operator signature per level.
- [ ] Permanent forbidden actions remain unreachable at EA3, including Gmail/approval/control/legal/consent/credential/evidence-deletion authority.
- [ ] Immediate and rolling demotion, pointer rollback and fresh re-entry preserve history and fail closed.

Retain level decisions, capability allowlists, pre-window query text/hash/signature, `[start_at,end_at)`/minimum `N`, representative slice allocation/seeds, eligible-input/admission rule, pre-admission rejection reasons, mechanically returned run IDs, admitted-denominator/terminal-taxonomy counts, config/model/prompt/tool/provider/runtime/release hashes, validation/provenance/cost/ledger results, authority graphs/spies, incidents, scheduler admission/denial records, demotion/rollback/drain/new-cohort evidence and operator signatures under the applicable evaluation/safety retention classes.

## Dependencies and next deliverable

LAUNCH-04 depends on an operated, evidence-bearing system and cannot be pre-granted by roadmap prose. Each accepted level unlocks only its next internal capability. [LAUNCH-05 maintenance](05-maintenance-and-upgrade-policy.md) can invalidate any level when a dependency, provider, model, policy, configuration or evidence binding changes.
