# DBOS Selection, Production Acceptance, and Mandatory Temporal Fallback

**Document ID:** WF-00
**Status:** Selected architecture; DBOS production use blocked on M1
**Milestone:** M1 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `WF-00-T01 -> WF-00-T02 -> WF-00-T03 -> WF-00-T04 -> WF-00-T05`; cross-document task Inputs `WF-00-T01 <- PRODUCT-01-T03; WF-00-T02 <- WF-01-T01,WF-01-T02,WF-01-T03; WF-00-T03 <- TEST-03-T03,WF-01-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [master roadmap stack decision](../README.md#selected-agent-and-durable-workflow-stack), [ADR 0002](../../decisions/0002-dbos-workflow-runtime.md), [ARCH-01](../01-architecture/01-target-system-architecture.md), and [M0 risk criteria](../00-product-strategy/03-risk-register-and-kill-criteria.md)
**Outputs:** Layer classification, official capability evidence, fixed eight-item DBOS acceptance gate, and executable Temporal migration trigger/handoff
**Unlocks:** WF-01 M1 spike and, only after passing or migrating, M2 product persistence/workflows
**Risk:** Critical
**Complexity:** M

## Outcome and timing

Alon AI selects Pydantic AI plus DBOS on PostgreSQL. This file does not reopen a vendor bakeoff: it records why the layers fit and defines how production evidence can reject DBOS. Pydantic AI owns typed agent execution/artifacts; DBOS owns finite durable coordination; deterministic application policy owns product transitions, budgets, suppression, authorization, and Gmail side effects through `SendGateway`.

M1 is necessary but insufficient. Its isolated disposable harness may send only to operator-owned test inboxes. Product outreach remains disabled until both M1 and M6 pass and later authority is separately granted.

## Current repository state

The lockfile contains Pydantic AI and DBOS, the Python package has empty `agents/` and `workflows/` markers, and the worker is idle. No DBOS workflow, queue, schedule, timer, rate limit, recovery monitor, version upgrade, Gmail adapter, test-inbox send, or Temporal adapter exists. `SendGateway` is a minimal protocol-level guard, not the durable product path.

## Scope and non-goals

In scope: selected runtime responsibilities, official-source capability claims, M1 evidence gate, adjacent-framework classification, fallback trigger, and migration boundary. Non-goals: a scoring exercise that can overrule a safety failure, implementing adjacent frameworks, using workflow runtime history as product state, direct agent/workflow Gmail calls, or claiming DBOS/Temporal eliminates Gmail ambiguity.

## Exact planned implementation surfaces

The initial implementation surface is `backend/src/alon_ai/workflows/dbos_runtime.py`, M1-only harness modules/tests from WF-01, worker composition, and a runtime-neutral `WorkflowRuntime` port. If any disqualifier fails, stop DBOS product work and create `workflows/temporal_runtime.py`, Temporal worker composition, replay/version fixtures, and a signed migration decision before M2 workflow implementation resumes.

### Official capability and layer record

| Component | Accurate layer/capability | Decision for Alon AI | Primary documentation |
| --- | --- | --- | --- |
| Pydantic AI | typed agent framework with model/tool boundaries and structured outputs | selected agent layer; never durable-product authority or Gmail caller | [Pydantic AI agents](https://ai.pydantic.dev/agents/) and [output](https://ai.pydantic.dev/output/) |
| DBOS | Python durable workflows persisted/recovered around steps; PostgreSQL-backed queues provide concurrency/rate controls; workflow upgrades use patching/versioning | selected finite workflow runtime because it fits Python/PostgreSQL and the solo-operator surface; conditional on all M1 evidence | [workflows](https://docs.dbos.dev/python/tutorials/workflow-tutorial), [production recovery](https://docs.dbos.dev/production/workflow-recovery), [queues/rate limits](https://docs.dbos.dev/python/tutorials/queue-tutorial), [upgrading workflow code](https://docs.dbos.dev/python/tutorials/upgrading-workflows) |
| Temporal | durable workflow execution with event-history replay; Python supports Worker Versioning/patching for in-flight compatibility | mandatory fallback, not an optional future candidate, after any M1 disqualifier | [workflow execution/replay](https://docs.temporal.io/workflow-execution), [Python workflow versioning](https://docs.temporal.io/develop/python/workflows/versioning), [Python cancellation](https://docs.temporal.io/develop/python/workflows/cancellation) |
| LangGraph | low-level agent orchestration runtime with persistence, durable execution, and human-in-the-loop | excluded initial second agent-orchestration abstraction; not the chosen business workflow runtime | [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) and [persistence](https://docs.langchain.com/oss/python/langgraph/persistence) |
| LangChain | agent/application framework with prebuilt agent architecture and model/tool integrations | excluded because Pydantic AI already owns the typed agent layer | [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview) |
| Restate | separate durable-execution server/runtime with services, virtual objects, workflows, journal replay, timers/signals | excluded runtime alternative; decision history only, not an agent-framework synonym | [Restate workflows](https://docs.restate.dev/tour/workflows) and [service types](https://docs.restate.dev/foundations/services) |
| Prefect | workflow/task orchestration centered on flows, tasks, deployments, schedules, states, retries, and data-pipeline operation | excluded pipeline/task orchestrator; does not improve the Gmail ambiguity gate | [Prefect flows](https://docs.prefect.io/v3/concepts/flows) and [quickstart/data-pipeline framing](https://docs.prefect.io/v3/get-started/quickstart) |

These sources establish capabilities, not fitness. Fitness is an Alon AI inference tested by M1. DBOS queue limits govern starts/concurrency; they do not prove provider-side exactly-once. Temporal replay/versioning likewise does not eliminate an external API's ambiguous success. In either runtime, stable application identity, attempt ledger, provider-result capture, Sent reconciliation, and operator-visible permanent quarantine remain mandatory. A zero-result search never becomes negative proof; retry is limited to explicit rejection or local pre-write proof.

### Eight non-waivable M1 disqualifiers

DBOS is rejected if it cannot reproducibly pass even one item under the defined restart/concurrency matrix:

1. restart recovery;
2. cancellation;
3. ambiguous Gmail outcome reconciliation;
4. duplicate-send prevention;
5. workflow versioning with safe in-flight recovery/drain;
6. correlated operator-visible observability;
7. operator pause/cancel/recovery control; or
8. rate-limit enforcement under restart and concurrency.

No weighted score, majority pass, convenience, lockfile presence, sunk work, or manual explanation can waive failure. A flaky/non-reproducible item is a failure.

### Temporal fallback handoff

The first disqualifying result atomically produces: `DBOS_REJECTED` gate record with item/scenario/build/evidence hashes; product outreach `false`; stopped DBOS queues/workers; exported M1 evidence; open critical incident; and a Temporal migration work item. The handoff preserves canonical ARCH-03 states/events and the runtime-neutral workflow ID/correlation contract. It discards `m1_spike`, does not migrate engine history as product truth, and reruns the identical eight-item suite against Temporal before M2 product workflow work resumes.

## Ordered implementation tasks

<!-- roadmap-task id=WF-00-T01 milestone=M1 depends_on=PRODUCT-01-T03 mode=parallel locks=architecture-contracts,workflow-runtime -->
- [ ] **Freeze runtime responsibility map —** Input: PRODUCT-01 frozen artifact/authority vocabulary crosswalk, architecture/ADR, and official runtime sources above. Operation: encode imports/ports so Pydantic AI, runtime, application policy, persistence, and provider authority cannot overlap; bind port, event and authority names to the frozen PRODUCT-01 crosswalk and reject vocabulary drift. Output: runtime-neutral interface and forbidden-import rules. Test evidence: `test_agents_and_workflows_cannot_import_gmail_send`. Failure behavior: block M1 harness composition.
<!-- roadmap-task id=WF-00-T02 milestone=M1 depends_on=WF-00-T01,WF-01-T01,WF-01-T02,WF-01-T03 mode=serial locks=workflow-runtime,gmail-side-effects,milestone-gate -->
- [ ] **Execute WF-01 acceptance suite —** Input: pinned build, disposable schema, fixtures, kill matrix, test inboxes; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: run every scenario repeatedly under restart/concurrency and retain raw/correlated evidence; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: per-item pass or first failure. Test evidence: named WF-01 suite. Failure behavior: retain a complete signed first-failure/runtime-rejection result with controls off for mandatory fallback; missing, corrupt or incomplete evidence remains a blocker and never counts as runtime acceptance.
<!-- roadmap-task id=WF-00-T03 milestone=M1 depends_on=WF-00-T02,TEST-03-T03,WF-01-T05 mode=serial locks=workflow-runtime,milestone-gate -->
- [ ] **Emit the signed discriminated DBOS gate —** Input: the complete independently checked WF-01 and TEST-03 evidence manifests; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: verify hashes, repetitions, all eight criteria, zero uncontrolled duplicates/blind retries, and operator visibility, then sign exactly one terminal `DBOS_ACCEPTED` or `DBOS_REJECTED` gate with the retained evidence reference; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: signed discriminated `DBOS_ACCEPTED|DBOS_REJECTED` gate. Test evidence: independent manifest checker proves 8/8 yields only `DBOS_ACCEPTED` and every failed/missing criterion yields only `DBOS_REJECTED`. Failure behavior: emit `DBOS_REJECTED`; never infer acceptance.
<!-- roadmap-task id=WF-00-T04 milestone=M1 depends_on=WF-00-T03 mode=serial locks=workflow-runtime,dependency-lockfiles,compose-topology,milestone-gate,gmail-side-effects,live-environment -->
- [ ] **Resolve one selected runtime and execute fallback only on rejection —** Input: the signed discriminated WF-00 runtime gate and its retained acceptance or rejection evidence; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: for `DBOS_ACCEPTED`, select DBOS and prove no Temporal adapter/suite execution occurred; for `DBOS_REJECTED`, stop DBOS, keep outreach off, implement the Temporal adapter, translate runtime mappings, rerun the identical eight-item suite, and select Temporal only after it passes; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: one signed `SelectedRuntimeDecisionV1` naming `DBOS|TEMPORAL`, the branch gate, evidence hashes, adapter version when applicable, and zero third-runtime authority. Test evidence: accepted-branch no-Temporal spy plus rejected-branch Temporal adapter contract/eight-item suite and invalid/missing/disagreeing gate cases. Failure behavior: remain blocked with no selected runtime; mandatory Temporal fallback cannot be skipped after `DBOS_REJECTED`.
<!-- roadmap-task id=WF-00-T05 milestone=M1 depends_on=WF-00-T04 mode=serial locks=architecture-contracts,milestone-gate -->
- [ ] **Reconsider adjacent layers only from new evidence —** Input: the signed `SelectedRuntimeDecisionV1`, a newly named unmet adjacent-layer requirement, and retained failure trace; fresh operator-signed spend/time/failed-gate/product-signal review snapshot for this gate. Operation: reconsider only the implicated adjacent layer without changing the selected-runtime decision or canonical authority; retain this gate's signed continue/revise/park/kill review and permit a later milestone only on the applicable continue decision. Output: an optional adjacent-layer ADR or no change; never a selected-runtime decision. Test evidence: proof the already selected layers cannot satisfy the newly named requirement and that no runtime pointer changes. Failure behavior: no dependency addition and no selected-runtime mutation.

## Test strategy

- **Static `test_runtime_sdk_imports_are_confined_to_adapters`:** DBOS/Temporal do not leak into domain/agents/API DTOs.
- **Contract `test_runtime_adapter_maps_every_workflow_run_state`:** unknown engine state fails closed.
- **Acceptance `test_dbos_gate_requires_all_eight_results`:** one missing/failing/flaky item rejects.
- **Migration `test_temporal_adapter_preserves_application_ids_events_and_guards`:** only runtime mechanics change.
- **Security `test_m1_recipient_allowlist_is_operator_owned_and_isolated`:** no product/prospect address.

## Security, privacy, compliance, idempotency, observability, and cost

M1 credentials/inboxes are isolated and least-scope; evidence redacts secrets and addresses to aliases. Runtime IDs map to application correlation IDs. Gmail idempotency/reconciliation remains application-owned. Queue/runtime metrics include workflow version, scenario, kill point, queue wait/start, provider attempt, reconciliation, control response, and cost. A small solo-operator surface is valuable only if safety evidence is complete.

## Failure, rollback, and operator recovery

On any disqualifier: stop new starts/dequeues, disable the provider path, preserve evidence, reconcile all ambiguous attempts, open an incident, export and drop the spike only after verification, then execute the Temporal handoff. DBOS can be reconsidered only under a later ADR after the failed capability is fixed and the full suite passes; product implementation cannot wait on hoped-for fixes.

## Acceptance and retained evidence

- [ ] Initial stack and every adjacent component are classified at the correct layer with official sources.
- [ ] The eight criteria are exact, binary, reproducible, and non-waivable.
- [ ] M1 authority is disposable-test-inbox-only and does not satisfy M6.
- [ ] Fallback preserves product vocabulary/ports and reruns the same suite.
- [ ] Gmail ambiguity remains application responsibility under either runtime.

Retain official-source URLs/access date, pinned dependency/build manifest, responsibility/import report, eight-item scorecard, raw traces, gate signature, incident/rejection record, and Temporal handoff evidence if triggered.

## Dependencies and next deliverable

WF-00 depends on M0/ARCH/ADR decisions and unlocks [WF-01 DBOS production acceptance](01-dbos-production-acceptance-spike.md). Only a passing DBOS result or passing mandatory Temporal replacement unlocks M2 database work and [WF-02](02-experiment-lifecycle.md).
