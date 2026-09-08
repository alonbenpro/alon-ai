# Experiment Creation Flow

**Document ID:** FRONTEND-02
**Status:** Planned M4 operator flow; no product form or experiment API exists today
**Milestone:** M4 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `FRONTEND-02-T01 -> FRONTEND-02-T02 -> FRONTEND-02-T03 -> FRONTEND-02-T04`; cross-document task Inputs `FRONTEND-02-T01 <- FRONTEND-01-T01,DB-02-T01`. Descriptive source authorities/resources (not whole-document completion dependencies): [PRODUCT-01 M0 brief](../00-product-strategy/01-product-scope.md#m0-experiment-brief), [DB-02](../02-database/02-experiment-and-offer-schema.md), [BACKEND-02](../06-backend/02-api-contracts.md), and [FRONTEND-01](01-information-architecture.md)
**Outputs:** Typed creation/revision/scope-approval workflow with caps, authority, validation, confirmation, and exact reconciliation
**Unlocks:** FRONTEND-03 no-send research control and the first finite experiment run
**Risk:** High
**Complexity:** L

## Outcome and timing

The M9 rule preview is fixed and read-only: four new-recipient cohorts `100/200/300/400`, cumulative `100/300/600/1,000`, one observation window and signed barrier per stage, and the PRODUCT-02 demand floors. The operator may make a rule stricter or accept a lower legal/provider ceiling but cannot weaken it, reorder stages, enter arbitrary counts, or request all 1,000 immediately.

At `/experiments/new`, the operator can define one narrow, falsifiable `ExperimentBrief`, review the exact frozen server payload, create a `DRAFT` experiment, and then explicitly approve scope from its detail page. Creation defines bounds; it never starts research, outreach, provider work, spend, or sending. Revision is a separate immutable brief version and is legal only through `reviseExperiment` under the BACKEND-05/ARCH-03 guards.

## Current repository state

The frontend has no product route, form library, generated product schema, authentication, experiment list/detail, or mutation hook. The current `page.tsx` renders readiness only. The 46-table model and `CreateExperiment`/`ApproveExperimentScope`/`ReviseExperiment` services are planned. Do not describe the creation flow as live until those contracts and routes exist.

## Scope and non-goals

In scope: required brief fields, client-side usability validation that mirrors generated structural constraints, server validation display, frozen review, exact idempotency/version behavior, draft recovery, and accessible step navigation. Non-goals: client-generated policy, automatic narrowness/scoring, AI-filled legal conclusions, implicit scope approval, starting a workflow on creation, local currency conversion, saving secrets/contact data, or editing an existing brief in place.

## Exact planned implementation surfaces

Create `src/app/(operator)/experiments/new/page.tsx`, `src/features/experiments/components/experiment-brief-form.tsx`, `brief-review.tsx`, `authority-level-fieldset.tsx`, `caps-fieldset.tsx`, `rule-json-editor.tsx`, `src/features/experiments/hooks/use-create-experiment.ts`, `use-approve-experiment-scope.ts`, `use-revise-experiment.ts`, and matching unit/browser tests. The page shell is a Server Component; the form/review/mutations are Client Components.

`/experiments` is a complete page, not shell-only. Create `src/app/(operator)/experiments/{page,loading,error}.tsx`, `src/features/experiments/components/{experiment-list,experiment-table,experiment-cards,experiment-filters,experiment-list-pagination}.tsx`, and `src/features/experiments/hooks/use-experiments.ts`. It calls only `GET /api/v1/experiments` / `listExperiments` with query key `["experiments",{state,cursor,limit}]`; exact canonical-state filter is server-side, `limit` defaults 50 and remains 1..100, and opaque keyset pages keep `(updated_at DESC,experiment_id)` order. The active FastAPI operator session is required; no anonymous data or bearer token exists.

The list loading state preserves heading/filter/table-card geometry; empty distinguishes no experiments from a state-filter miss and focuses the empty heading after filter submit; stale shows last fetch time, permits navigation but disables no list-level authority because none exists, and refetches on focus/15 seconds for nonterminal pages/60 seconds terminal-only. Error renders `ProblemDetailsV1`, focuses the error summary, and preserves filters. Partial is unsupported for this authoritative resource page and becomes error; redacted safe labels/IDs remain explicit; terminal `DECIDED/CANCELLED` rows are text/icon/pattern-marked and read-only. At 0-767px cards expose identical fields/links; at 768px+ semantic table is used with bounded labeled scroll only if necessary; the page has no horizontal overflow, 44x44 targets, visible focus, keyboard pagination, and focus moves to the first new row heading after a page change.

### Exact form and server-field ownership

The generated `CreateExperimentRequestV1` is the wire authority. Its brief payload must expose the DB-02/M0 fields below and no UI-only field enters the request. UI step names are presentation only.

| Step | Exact persisted fields displayed/edited | UI rule; server remains authoritative |
| --- | --- | --- |
| Bet | `experiment_code`, `customer_segment`, `problem_hypothesis`, `offer_hypothesis`, `operator_advantage` | required text; show narrowness prompt, never compute readiness |
| Jurisdiction/baseline | `jurisdictions_schema_version`, `jurisdictions`, `baseline_method` | unknown jurisdiction is visibly blocking; no legal advice claim |
| Cash/time caps | `total_cash_cap_ils_minor`, `provider_cash_cap_ils_minor`, `operator_hours_cap` | integer minor units; provider cap cannot exceed total only as usability hint; server rejects invalid |
| Sample caps | `max_researched_leads`, `max_qualified_leads`, `max_contacted_leads`, `max_concurrently_active_leads` | integer hierarchy; no client-side derived budget or funnel authority |
| Authority | `authority_level` exact enum `NO_SEND`, `TEST_INBOX_ONLY`, `BOUNDED_REAL_RECIPIENTS` | show milestone meaning; choosing a value does not enable a control or prove a gate |
| Decision rules | `success_rule_schema_version`, `success_rule`, `kill_rule_schema_version`, `kill_rule`, `decision_date_condition` | strict generated JSON types; never execute or reinterpret rules in the browser |

Server-generated/read-only fields—IDs, `brief_version`, `content_hash`, operator ID, supersession ID, UTC timestamps, experiment state/version, correlation—are rendered only from `ResourceResponseV1`. They never come from hidden form inputs.

### Operations, query/mutation policy, and exact states

| Action | URL / `operationId` / wire | Key, concurrency, invalidation, reconciliation |
| --- | --- | --- |
| list experiments | `GET /api/v1/experiments`, `listExperiments`, state/cursor/limit page ordered `(updated_at DESC,experiment_id)` | `['experiments',{state,cursor,limit}]`; server state filter/keyset pagination; active operator session; no optimistic behavior; 15-second nonterminal/60-second terminal refetch |
| create | `POST /api/v1/experiments`, `createExperiment`, `CreateExperimentRequestV1 -> ResourceResponseV1` | mutation `['experiment','create']`; one `ui:createExperiment:{uuid}` key; no `If-Match`; no optimistic insert; on 201 store `Location`, invalidate experiment list, navigate to canonical returned ID |
| approve scope | `POST /api/v1/experiments/{experiment_id}/commands/approve-scope`, `approveExperimentScope`, `ApproveExperimentScopeRequestV1 -> CommandReceiptV1` | mutation `['experiment',id,'approve-scope']`; new key plus `If-Match` from latest experiment ETag; invalidate detail/list/overview/timeline; refetch until returned state/version visible |
| revise failed experiment | `POST /api/v1/experiments/{experiment_id}/commands/revise`, `reviseExperiment`, `ReviseExperimentRequestV1 -> ResourceResponseV1` | mutation `['experiment',id,'revise']`; key plus latest `If-Match`; no optimistic version; on 201 navigate/render returned brief version and invalidate all experiment/report/campaign approval keys |

No autosave API exists, so draft recovery is local form state only: `sessionStorage` may hold non-sensitive draft fields under a random tab key for at most the tab session, must never hold access tokens/idempotency keys/PII, and is deleted after committed creation or explicit discard. If this privacy posture is not approved, omit recovery rather than invent a server draft endpoint.

Loading shows labeled fieldset skeletons without a false state. Empty means a fresh form. Stale applies only to the source experiment during revision and blocks submit until refetched. Validation errors produce a linked error summary and focus the first invalid control. `401/403/409/412/428/429/503` render exact `ProblemDetailsV1`; conflict refetches and returns to review. A committed resource is terminal for that submission even if navigation fails; exact replay uses the same request/key.

### Confirmation, focus, and permission behavior

The final review lists every bound, exact authority enum, budget/sample caps, jurisdictions, success/kill rule summaries, and a permanent warning: “Creates a draft only; grants no research, send, spend, or product-outreach authority.” The create button is not destructive but still uses a review step. Scope approval is an authority action: open `CommandDialog`, require confirmation checkbox, show current experiment ID/brief version/content hash/state/version, place initial focus on the dialog heading, trap focus, Escape closes only while not pending, and return focus to the invoking button.

Revision from `FAILED` warns that it creates a new immutable brief version and invalidates prior approvals. It captures the exact generated reason field if `ReviseExperimentRequestV1` requires one; the UI does not invent free text. Pending disables all submit paths and exposes `role=status`. Only authenticated active operator permission renders enabled commands; a 403 keeps the facts visible and action disabled.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-02-T01 milestone=M4 depends_on=FRONTEND-01-T01,DB-02-T01 mode=serial locks=frontend-client -->
- [ ] **Build the generated-schema form —** Input: `CreateExperimentRequestV1` and DB-02 field contract. Operation: compose accessible fieldsets, structural hints, integer minor-unit inputs, literal authority choices, and strict rule editors without duplicating policy. Output: reviewable request. Test evidence: generated-type compile plus missing/boundary/extra-field fixtures. Failure behavior: no request and focus error summary.
<!-- roadmap-task id=FRONTEND-02-T02 milestone=M4 depends_on=FRONTEND-02-T01 mode=serial locks=frontend-client -->
- [ ] **Implement create/replay/navigation —** Input: frozen reviewed payload and fixture-only operator session. Operation: create one idempotency key, submit once, preserve exact payload/key through unknown outcome, and navigate by returned `Location`/ID; exercise only signed synthetic fixture sessions at M4; real SEC-02 session integration is the later frontend foundation gate. Output: authoritative `DRAFT` resource. Test evidence: double-click, Enter, timeout-after-commit, exact replay, hash-conflict tests. Failure behavior: retain review and safe IDs; never create a second key automatically.
<!-- roadmap-task id=FRONTEND-02-T03 milestone=M4 depends_on=FRONTEND-02-T02 mode=serial locks=frontend-client -->
- [ ] **Implement explicit scope approval and revision —** Input: latest ETag/resource and generated requests. Operation: confirm authority, attach `If-Match`, reconcile receipt/new resource, and invalidate exact dependencies. Output: server-owned version/state. Test evidence: stale ETag, illegal state, approval invalidation, immutable prior-version tests. Failure behavior: refetch and require a new review.
<!-- roadmap-task id=FRONTEND-02-T04 milestone=M4 depends_on=FRONTEND-02-T03 mode=serial locks=frontend-client -->
- [ ] **Verify privacy and responsive access —** Input: form at 320/768/1280 CSS pixels and keyboard/screen reader. Operation: verify no PII/secrets in storage/URL/telemetry, logical focus, help/error association, and no page overflow. Output: M4-ready creation UX evidence. Test evidence: axe/storage/network/screenshot matrix. Failure behavior: disable draft storage or release.

## Test strategy

- **List `test_experiment_list_filters_keyset_pages_states_focus_and_card_table_parity`:** exact generated page, no duplicate/skip/overflow.
- **Contract `test_create_form_serializes_only_generated_request_fields`:** exact schema and no hidden server fields.
- **Bounds `test_caps_and_authority_render_exact_server_units_and_enums`:** ILS minor units remain integers.
- **Idempotency `test_timeout_after_create_replays_same_payload_and_key`:** one experiment.
- **Concurrency `test_stale_scope_approval_or_revision_refetches_before_reconfirm`:** 412/409 paths.
- **Authority `test_create_and_authority_selection_never_enable_or_start_anything`:** network allowlist.
- **Accessibility `test_creation_error_summary_focus_and_field_descriptions`:** keyboard/axe at three breakpoints.

## Security, privacy, compliance, idempotency, observability, and cost

No Gmail secret, prospect data, unverified legal conclusion, token, raw evidence, or provider response belongs in this form or draft storage. Safe telemetry records route, operation ID, field error codes (not values), submit/replay outcome, duration, safe experiment ID, and correlation. The backend validates all constraints and hashes. The UI displays budget caps but cannot reserve, spend, convert currency, or predict provider cost.

## Failure, rollback, and operator recovery

If the generated schema changes, compile/contract tests block release. If creation outcome is unknown, keep exact frozen payload/key and offer “Check status / retry exact request”; do not create another experiment. If scope approval conflicts, refetch and show what version/state changed. A bad but committed draft is not edited: leave it `DRAFT`, cancel when legal, or use the server-authorized revision path after failure. Roll back the frontend route without changing backend rows.

## Acceptance and retained evidence

- [ ] Every M0/DB-02 brief field is visible, unit-labeled, reviewed, and serialized by the generated type.
- [ ] Creation, scope approval, and revision use exact operation IDs, keys, ETags, responses, invalidations, and no optimistic state.
- [ ] Authority-level display distinguishes no-send, test inbox, and bounded real recipients without enabling either control.
- [ ] Loading, fresh-empty, validation, stale, conflict, auth, dependency, committed, and terminal states are keyboard accessible.

Retain schema fixtures, serialized request snapshots, replay/conflict traces, focus/axe results, responsive screenshots, storage/privacy scan, and network allowlist output.

## Dependencies and next deliverable

FRONTEND-02 depends on generated product types and the private operator session. A committed, explicitly scope-approved server resource unlocks [FRONTEND-03](03-experiment-control-center.md); creation itself unlocks no provider call or outreach.
