# Operator Information Architecture

**Document ID:** FRONTEND-01
**Status:** Planned operator product UI; only the polished readiness foundation page and generated health client exist today
**Milestone:** M4 no-send operator UI, M6 owned-inbox controls, M7 evidence and decision control plane
**Owner:** Solo operator
**Prerequisites:** [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), [BACKEND-02](../06-backend/02-api-contracts.md), [BACKEND-05](../06-backend/05-approval-and-command-handling.md), [BACKEND-06](../06-backend/06-reporting-and-query-services.md), and generated OpenAPI artifacts
**Outputs:** Smallest route map, exact 48-operation client inventory, frontend ownership boundary, planned source map, and global state/error policy
**Unlocks:** FRONTEND-02 through FRONTEND-09 and the M4-M7 browser acceptance journeys
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Build one private, keyboard-operable operator shell with three primary destinations: **Experiments**, **Approvals**, and **Recovery**. Experiment detail owns campaign, evidence, message, cost, funnel, and decision context; Recovery owns controls, Gmail mailbox authorization, ambiguous sends, incidents, repairs, and provider operations. This is the smallest structure that keeps safety work visible without turning the frontend into a second backend.

The shell begins at M4 with no-send research/qualification controls. M6 adds the isolated `TEST_INBOX_SENDING` pilot and Gmail recovery. M7 adds product approvals, reports, and decision recording. `PRODUCT_OUTREACH` remains a separately gated server control; neither UI availability nor M1/M6 completion is send authority.

## Current repository state

Implemented today: Next.js 16 App Router, React 19, TypeScript 5, TanStack Query 5, `openapi-fetch`, Tailwind 4, Vitest/Testing Library, `frontend/src/app/page.tsx`, the global layout, `QueryProvider`, `ApiStatus`, and generated `/health/live` and `/health/ready` types/client. The current page is a polished readiness foundation and says outreach is disabled.

Missing today: private operator authentication/delivery, product OpenAPI schemas, every `/api/v1` route, product layouts/pages, error boundaries, campaigns, approvals, Gmail OAuth, recovery, reports, controls, agent/evidence views, browser E2E, and accessibility verification. All product UI below is planned.

Pydantic AI and DBOS remain the selected backend agent/runtime stack; the mandatory Temporal fallback applies after any of the eight M1 disqualifying outcomes. The frontend imports neither runtime and renders only canonical application workflow state, never an engine-native substitute. The 46-table product model, agents, workflows, providers, command/query services, and their events are also planned; the frontend never treats planned data as implemented.

## Scope and non-goals

In scope: generated-client reads/commands, route/page/component ownership, query and mutation keys, server-result reconciliation, exact canonical-state display, stale/partial/redacted behavior, authentication-required gating, accessibility, responsive behavior, and safe telemetry.

Non-goals: Next.js API routes, route handlers, Server Actions for business mutations, provider SDKs, PostgreSQL access, Gmail/operator credential storage, policy/funnel/cost/approval/recovery calculation, locally inferred transitions, arbitrary CRUD, secrets in `NEXT_PUBLIC_*`, or a new endpoint/field/event. A frontend need absent from BACKEND-02 is a backend-contract gap and remains blocked.

## Exact planned implementation surfaces

### Minimal route map and ownership

| URL | App Router surface | Responsibility | Primary generated operations |
| --- | --- | --- | --- |
| `/` | `src/app/page.tsx` | Current readiness landing; later authenticated redirect to `/experiments` while health remains visible | `getReadiness`; optional diagnostic `getLiveness` |
| `/experiments` | `src/app/(operator)/experiments/page.tsx` | Stable experiment list, filters, terminal/nonterminal distinction | `listExperiments` |
| `/experiments/new` | `src/app/(operator)/experiments/new/page.tsx` | Create one strict experiment brief | `createExperiment` |
| `/experiments/[experimentId]` | `src/app/(operator)/experiments/[experimentId]/page.tsx` | Creation continuation, stage/control center, campaign launch, evidence references, reports, immutable decision | experiment/workflow/report operations |
| `/experiments/[experimentId]/campaigns/[campaignId]/versions/[campaignVersion]` | matching nested `page.tsx` | Exact immutable campaign version, members/messages/suppression states, campaign commands | campaign operations |
| `/approvals` | `src/app/(operator)/approvals/page.tsx` | Approval queue with current-authority validity and stale/revoked reasons | `listApprovals`, `getApprovalQueueReport` |
| `/approvals/[approvalId]` | matching detail `page.tsx` | Exact approval basis and decide/revoke commands | approval operations |
| `/messages/[messageId]` | `src/app/(operator)/messages/[messageId]/page.tsx` | Redacted message/send/reply timeline and final-intent/retry controls | message operations |
| `/recovery` | `src/app/(operator)/recovery/page.tsx` | Five-kind recovery overview, unresolved sends, incidents/repairs, both controls, OAuth/mailboxes, provider evidence | Gmail/control/recovery/provider operations |

Primary navigation contains only Experiments, Approvals, and Recovery. `/` health remains anonymous; the OAuth callback uses only its verified signed-flow authority; every product panel/query/command requires the active authenticated operator bearer boundary. A page may render its shell and authentication-required state without permission, but no product data or action. Badges are server counts already returned by their queries; the client does not derive authoritative queue health. Deep links preserve stable IDs, not email addresses, content, provider tokens, or opaque report cursors.

### Exact BACKEND-02 generated-client coverage

This is the complete 48-route/48-`operationId` inventory. The `Wire` column names the only request/response authority available to the UI. `R` means bearer-authenticated read; `M` means bearer-authenticated JSON mutation with caller `Idempotency-Key`; `MV` adds `If-Match` from the latest explicit aggregate ETag; `S` uses locked expected state/status from the generated request; `O` is the signed-state OAuth exception. All calls send/receive `X-Request-ID`/`X-Correlation-ID` as BACKEND-02 defines.

| Method/path | `operationId` | UI route/owner | Wire and cache identity |
| --- | --- | --- | --- |
| `GET /health/live` | `getLiveness` | `/`, recovery diagnostics | existing health payload; `R0`; `['health','live']` |
| `GET /health/ready` | `getReadiness` | `/`, shell banner | existing ready/degraded payload; `R0`; `['health','ready']` |
| `POST /api/v1/gmail/oauth/authorizations` | `startGmailAuthorization` | `/recovery` | `StartGmailAuthorizationRequestV1 -> GmailAuthorizationResponseV1`; `M`; `['gmail','oauth','start']` |
| `GET /api/v1/gmail/oauth/callback` | `completeGmailAuthorization` | provider redirect only | query `code,state`, registered command, fixed redirect; `O`; never a Query cache entry |
| `GET /api/v1/gmail/mailboxes` | `listGmailMailboxes` | `/recovery` | `PageResponseV1`, `(created_at,mailbox_id)`; `R`; `['gmail','mailboxes',{cursor,limit}]` |
| `DELETE /api/v1/gmail/mailboxes/{mailbox_id}/authorization` | `revokeGmailAuthorization` | `/recovery` | `RevokeGmailAuthorizationRequestV1 -> CommandReceiptV1`; `M+S`; `['gmail','mailbox',mailboxId,'revoke']` |
| `POST /api/v1/gmail/mailboxes/{mailbox_id}/commands/sync` | `syncGmailMailbox` | `/recovery` | `SyncGmailMailboxRequestV1 -> CommandReceiptV1`; `MV+S`; `['gmail','mailbox',mailboxId,'sync']` |
| `POST /api/v1/experiments` | `createExperiment` | `/experiments/new` | `CreateExperimentRequestV1 -> ResourceResponseV1`; `M`; `['experiment','create']` |
| `GET /api/v1/experiments` | `listExperiments` | `/experiments` | state/cursor/limit `PageResponseV1`; `R`; `['experiments',{state,cursor,limit}]` |
| `GET /api/v1/experiments/{experiment_id}` | `getExperiment` | experiment detail | brief/run/control summary resource; `R`; `['experiment',experimentId]` |
| `POST /api/v1/experiments/{experiment_id}/commands/approve-scope` | `approveExperimentScope` | experiment detail | `ApproveExperimentScopeRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'approve-scope']` |
| `POST /api/v1/experiments/{experiment_id}/commands/start-research` | `startExperimentResearch` | experiment detail | `StartStageRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'start-research']` |
| `POST /api/v1/experiments/{experiment_id}/commands/start-lead-qualification` | `startLeadQualification` | experiment detail | `StartStageRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'start-lead-qualification']` |
| `POST /api/v1/experiments/{experiment_id}/commands/pause` | `pauseExperiment` | experiment detail | `ControlExperimentRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'pause']` |
| `POST /api/v1/experiments/{experiment_id}/commands/resume` | `resumeExperiment` | experiment detail | `ControlExperimentRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'resume']` |
| `POST /api/v1/experiments/{experiment_id}/commands/cancel` | `cancelExperiment` | experiment detail | `ControlExperimentRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'cancel']` |
| `POST /api/v1/experiments/{experiment_id}/commands/retry-stage` | `retryExperimentStage` | experiment detail/recovery | `RetryExperimentStageRequestV1 -> CommandReceiptV1`; `MV`; `['experiment',id,'retry-stage']` |
| `POST /api/v1/experiments/{experiment_id}/commands/revise` | `reviseExperiment` | experiment detail | `ReviseExperimentRequestV1 -> ResourceResponseV1`; `MV`; `['experiment',id,'revise']` |
| `POST /api/v1/experiments/{experiment_id}/commands/record-decision` | `recordExperimentDecision` | experiment analytics | `RecordExperimentDecisionRequestV1 -> ResourceResponseV1`; `MV`; `['experiment',id,'record-decision']` |
| `GET /api/v1/workflow-runs/{workflow_run_id}` | `getWorkflowRun` | experiment detail | canonical run projection; `R`; `['workflow-run',workflowRunId]` |
| `POST /api/v1/experiments/{experiment_id}/campaigns` | `createCampaignVersion` | experiment detail | `CreateCampaignVersionRequestV1` resource; `M`; `['experiment',id,'campaign','create']` |
| `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}` | `getCampaignVersion` | campaign detail | exact immutable version resource; `R`; `['campaign',campaignId,campaignVersion]` |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/activate` | `activateCampaign` | campaign detail | `CampaignControlRequestV1 -> CommandReceiptV1`; `M+S`; `['campaign',id,version,'activate']` |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/pause` | `pauseCampaign` | campaign detail | `CampaignControlRequestV1 -> CommandReceiptV1`; `M+S`; `['campaign',id,version,'pause']` |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/resume` | `resumeCampaign` | campaign detail | `CampaignControlRequestV1 -> CommandReceiptV1`; `M+S`; `['campaign',id,version,'resume']` |
| `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/cancel` | `cancelCampaign` | campaign detail | `CampaignControlRequestV1 -> CommandReceiptV1`; `M+S`; `['campaign',id,version,'cancel']` |
| `GET /api/v1/approvals` | `listApprovals` | `/approvals` | state/cursor/limit page; `R`; `['approvals',{state,cursor,limit}]` |
| `GET /api/v1/approvals/{approval_id}` | `getApproval` | approval detail | exact approval resource; `R`; `['approval',approvalId]` |
| `POST /api/v1/approvals/{approval_id}/commands/approve` | `approveApproval` | approval detail | `DecideApprovalRequestV1 -> CommandReceiptV1`; `M+S`; `['approval',id,'approve']` |
| `POST /api/v1/approvals/{approval_id}/commands/deny` | `denyApproval` | approval detail | `DecideApprovalRequestV1 -> CommandReceiptV1`; `M+S`; `['approval',id,'deny']` |
| `POST /api/v1/approvals/{approval_id}/commands/revoke` | `revokeApproval` | approval detail | `RevokeApprovalRequestV1 -> CommandReceiptV1`; `M+S`; `['approval',id,'revoke']` |
| `GET /api/v1/messages/{message_id}` | `getOutreachMessage` | message detail | redacted message/send/reply timeline resource; `R`; `['message',messageId]` |
| `POST /api/v1/messages/{message_id}/commands/request-approval` | `requestMessageApproval` | message detail | `RequestApprovalRequestV1 -> approval resource`; `MV`; `['message',id,'request-approval']` |
| `POST /api/v1/messages/{message_id}/commands/record-send-intent` | `recordMessageSendIntent` | message/approval detail | `RecordSendIntentRequestV1 -> CommandReceiptV1`; `MV`; `['message',id,'record-send-intent']` |
| `POST /api/v1/messages/{message_id}/commands/abort-retry` | `abortMessageRetry` | message/recovery | `AbortSendRetryRequestV1 -> terminal result`; `MV`; `['message',id,'abort-retry']` |
| `GET /api/v1/controls` | `listSystemControls` | `/recovery` | control resources; `R`; `['controls']` |
| `POST /api/v1/controls/{control_name}/commands/enable` | `enableSystemControl` | `/recovery` | `ChangeControlRequestV1 -> CommandReceiptV1`; `MV`; `['control',name,'enable']` |
| `POST /api/v1/controls/{control_name}/commands/disable` | `disableSystemControl` | `/recovery` | `ChangeControlRequestV1 -> CommandReceiptV1`; `MV`; `['control',name,'disable']` |
| `GET /api/v1/recovery/overview` | `getRecoveryOverview` | `/recovery` | cursor/limit `PageResponseV1[RecoveryOverviewItemV1]`; `R`; `['recovery','overview',{cursor,limit}]` |
| `GET /api/v1/recovery/send-attempts` | `listUnresolvedSendAttempts` | `/recovery` | cursor/limit unresolved page; `R`; `['recovery','send-attempts',{cursor,limit}]` |
| `POST /api/v1/send-attempts/{send_attempt_id}/commands/reconcile` | `reconcileSendAttempt` | `/recovery` | `ReconcileSendAttemptRequestV1 -> CommandReceiptV1`; `M`; `['send-attempt',id,'reconcile']` |
| `POST /api/v1/incidents/{incident_id}/commands/repair` | `repairIncident` | `/recovery` | `RepairIncidentRequestV1 -> typed 200/202 result`; `M`; `['incident',id,'repair']` |
| `GET /api/v1/reports/experiments/{experiment_id}/overview` | `getExperimentOverviewReport` | experiment detail | `report.experiment_overview.v1`; `R`; `['report','experiment',id,'overview']` |
| `GET /api/v1/reports/experiments/{experiment_id}/funnel` | `getExperimentFunnelReport` | experiment detail | `report.experiment_funnel.v1`; `R`; `['report','experiment',id,'funnel']` |
| `GET /api/v1/reports/experiments/{experiment_id}/costs` | `getExperimentCostReport` | experiment detail | `report.experiment_costs.v1`; `R`; `['report','experiment',id,'costs']` |
| `GET /api/v1/reports/experiments/{experiment_id}/timeline` | `getExperimentTimelineReport` | experiment/message context | paged timeline; `R`; `['report','experiment',id,'timeline',{cursor,limit}]` |
| `GET /api/v1/reports/providers` | `getProviderOperationsReport` | `/recovery` | paged provider report; `R`; `['report','providers',{cursor,limit}]` |
| `GET /api/v1/reports/approvals` | `getApprovalQueueReport` | `/approvals` | paged approval projection; `R`; `['report','approvals',{cursor,limit}]` |

`R0` means the existing unauthenticated health contract. Read success is 200 except readiness may be 503 and the OAuth callback is 303. Success is 201 for `startGmailAuthorization`, `createExperiment`, `reviseExperiment`, `recordExperimentDecision`, `createCampaignVersion`, and `requestMessageApproval`; 200 for `approveExperimentScope`, approval decisions/revoke, `abortMessageRetry`, and control changes; 202 for mailbox revoke/sync, experiment stage/control/retry, campaign controls, `recordMessageSendIntent`, and `reconcileSendAttempt`; `repairIncident` is the declared 200/202 union. No UI normalizes one success status into another. The table does not assert undisclosed fields inside a named generated schema. Until `frontend/openapi.json` contains a product schema, a component may not hand-author its shape. Shared response fields are exactly `ResourceResponseV1={schema_version,data,version,correlation_id}`, `CommandReceiptV1={schema_version,command_type,command_scope,idempotency_key,status,aggregate_type,aggregate_id,aggregate_version,workflow_run_id,result_hash,correlation_id}`, `PageResponseV1={schema_version,items,next_cursor,as_of,projection_version,correlation_id}`, and reports add their BACKEND-06 `projection_version`, UTC `as_of`, high-watermark, `complete`, sorted warnings, and correlation.

### Frontend source, state, and authority boundaries

Create `src/app/(operator)/layout.tsx`, route-local `loading.tsx`/`error.tsx`, `src/features/{experiments,campaigns,approvals,messages,recovery,reports,gmail,controls}/`, `src/components/operator/{app-shell,status-badge,problem-panel,command-dialog,stale-banner,data-table-card-toggle}.tsx`, `src/lib/api/{client,query-keys,idempotency,problem}.ts`, and tests under matching feature folders plus `frontend/e2e/`. Keep generated `openapi.json` and `src/lib/api/schema.d.ts` paired.

App Router layouts/pages are Server Components for static shell, headings, navigation, and route-parameter validation only. Each authenticated data panel is a focused Client Component under `QueryProvider`; it calls `openapi-fetch` through typed feature hooks. No Server Component reads a bearer token and no Server Action mutates business state. TanStack Query owns remote snapshots only; local component state owns disclosure, filters, form drafts, focus return, and confirmation text. The backend owns every aggregate state, allowed action, policy fact, approval validity, report result, cost, and recovery instruction.

The authentication mechanism itself is not invented here. Product panels stay blocked until the approved private operator session can provide BACKEND-02 bearer authentication without localStorage, source-controlled tokens, query strings, or `NEXT_PUBLIC_*`. A `401 AUTHENTICATION_REQUIRED` renders a session-required boundary; it never falls back to anonymous product data.

### Global fetch, mutation, and state policy

- Queries use generated response models, abort signals, and exact keys above. Default refetch-on-focus is enabled for controls, approvals, recovery, message ambiguity, and active runs; static terminal resources may be `staleTime=60_000`. Controls/approval/recovery bypass client persistence and backend cache.
- Active workflow/message/campaign panels poll every 5 seconds; pause/cancel requested, `AMBIGUOUS`, `RECONCILING`, OAuth resumable, and open incidents poll every 3 seconds; stable nonterminal lists use 15 seconds; terminal/immutable records stop polling. `Retry-After` overrides the interval. Background-tab polling pauses except for an explicit operator-owned recovery session, which still caps at 15 seconds.
- Every mutation creates one visible-ASCII 16..200-character key once per confirmed submission (for example `ui:{operationId}:{uuid}`), retains it with the exact frozen request while pending/unknown, and reuses it only for exact replay. Edited payload means a new key. OAuth callback uses the server-derived key only.
- `If-Match` is copied from the latest generated resource ETag/version for experiment, outreach-message, system-control, and Gmail-history-cursor updates. Campaign version is immutable in the path plus generated `expected_state`; approval/mailbox commands use generated `expected_state`/`expected_status`. The client never fabricates a version for an aggregate without one.
- No authority/state mutation is optimistic. Buttons enter pending, remain protected from pointer/keyboard double-submit, and reconcile by rendering the receipt then refetching all affected exact keys. A 202 receipt means accepted work, never completed state.
- Invalidation follows resource ownership: experiment commands invalidate its resource/list/overview/timeline and referenced run; campaign commands invalidate campaign/experiment/overview/timeline; approval commands invalidate approval queues/detail/message/timeline; message commands invalidate message/approval/campaign/recovery/timeline; controls invalidate controls/overview/campaign/recovery; reconcile/repair invalidate both recovery pages, affected message/run/incident, provider and timeline reports; Gmail commands invalidate mailboxes/controls/recovery/provider reports.
- `ProblemDetailsV1` fields are the only error source. `412/409 VERSION_CONFLICT` refreshes and requires a fresh confirmation; `REPORT_SNAPSHOT_EXPIRED` discards all pages/cursor and restarts page one; `429` honors `Retry-After`; `503` remains visibly degraded; unknown status/schema fails closed.
- UTC persisted instants and server conversion evidence remain authoritative. `Intl.DateTimeFormat(...,{timeZone:'Asia/Jerusalem'})` is presentation only and every displayed time offers the UTC instant. Currency is never converted client-side; original minor amount/currency and server-recorded ILS evidence are shown separately.

### End-to-end operator journeys

1. Create one bounded brief with `createExperiment`, explicitly `approveExperimentScope`, start research and qualification, and observe new authoritative versions/runs without any send surface.
2. Pause, resume, and cancel an active experiment; verify 202 requested state, delayed runtime acknowledgement, conflict refetch, and terminal read-only behavior.
3. Create/activate a campaign version, request/review one immutable approval, record one send intent, then prove a changed suppression/control fact can still deny the later final SEND.
4. Lose a possible provider result, observe `AMBIGUOUS -> RECONCILING`, use `getRecoveryOverview` and `reconcileSendAttempt`, and reach direct evidence-backed terminal state without resend.
5. Start Gmail authorization, traverse signed callback success/restart/conflict paths, observe exact ACTIVE-plus-mailbox commit gating, sync, and revoke without browser credential access.
6. Disable `TEST_INBOX_SENDING` and `PRODUCT_OUTREACH` independently by keyboard, observe committed-versus-drained state, then prove re-enable denials for missing M1/M6 evidence or open incidents.
7. Read one repeatable overview/funnel/cost/timeline snapshot, preserve denominators/currency/warnings, and record one immutable decision that triggers no scale, spend, control, or send.

Each journey captures generated-client network allowlist, request/idempotency/ETag/correlation evidence, focus/live-region behavior, desktop/mobile rendering, and backend reconciliation.

## Ordered implementation tasks

- [ ] **Generate and gate the product client —** Input: composed BACKEND-02 OpenAPI. Operation: regenerate both artifacts, assert exactly 48 method/path/`operationId` pairs and strict error/status unions, and prohibit handwritten product DTOs. Output: typed product client. Test evidence: `test_openapi_generated_client_has_no_drift` plus TypeScript operation coverage. Failure behavior: product routes remain absent and outreach controls unavailable.
- [ ] **Build the three-destination operator shell —** Input: route map and private operator session boundary. Operation: add server shell, skip link, landmarks, responsive nav, route boundaries, and authenticated client panels. Output: keyboard-operable Experiments/Approvals/Recovery navigation. Test evidence: routing, auth-required, axe, keyboard, 320px/768px/1280px browser tests. Failure behavior: health landing remains; no anonymous product call.
- [ ] **Implement shared query/mutation primitives —** Input: generated types, ETags, idempotency, Problem Details. Operation: encode exact keys, aborts, polling, replay, invalidation, focus/error recovery, and no optimistic authority. Output: reusable safe hooks/dialogs. Test evidence: replay, double-submit, conflict, 202, snapshot-expiry, stale and partial tests. Failure behavior: command disabled and request retained for exact retry.
- [ ] **Prove frontend authority boundaries —** Input: built bundle/import graph. Operation: reject `src/app/api`, route handlers, business Server Actions, provider/database imports, handwritten product schemas, local policy/math, and secret-bearing telemetry. Output: generated-client-only UI. Test evidence: static import/AST and bundle scans. Failure behavior: CI blocks M4/M6/M7 UI release.

## Test strategy

- **Contract `test_frontend_operation_inventory_matches_backend02_exactly`:** 48 unique method/path/operation IDs, no extras.
- **Boundary `test_frontend_has_no_business_route_server_action_provider_sdk_or_database_write`:** static import and route scan.
- **State `test_every_canonical_enum_has_non_color_label_and_unknown_fails_closed`:** ARCH-03 exhaustive fixtures.
- **Mutation `test_double_submit_reuses_one_key_and_never_renders_202_as_completed`:** pointer/Enter/Space/reload matrix.
- **Concurrency `test_etag_conflict_refetches_and_requires_new_confirmation`:** no silent replay with changed facts.
- **Accessibility `test_shell_and_boundaries_pass_axe_keyboard_focus_and_live_region_matrix`:** all breakpoints.
- **E2E `test_operator_routes_use_generated_client_only`:** network allowlist rejects undocumented method/path.

## Security, privacy, compliance, idempotency, observability, and cost

The UI shows only response-allowlisted data. It never logs access tokens, Gmail state/code, addresses, bodies, prompts, raw evidence, source snippets, provider payloads, opaque cursors, idempotency keys, or approval facts. Safe telemetry contains route template, `operationId`, response status, duration bucket, retry/replay flag, safe aggregate IDs, generated schema/projection version, and correlation ID. Product analytics are disabled unless explicitly approved.

Operator authentication never grants more fields than a schema exposes. Browser history and document titles use safe IDs/labels. Confirmation text never asks the operator to paste secrets. Client caches are in-memory and cleared on session loss. Idempotency and ETag behavior follow BACKEND-02 exactly; client time, locale, charts, and labels have no authority. Frontend network and render cost are bounded by page limit 50, documented polling, aborts, and no unbounded prefetch.

## Failure, rollback, and operator recovery

Unknown generated schema, missing operation, auth loss, CORS failure, stale ETag, corrupt report, cursor expiry, or unsupported canonical enum renders a fail-closed problem panel with request/correlation IDs and a safe retry/refetch path. Commands remain unavailable while authority is unknown. Disable the product shell through release rollback; the backend remains authoritative and no queued work is inferred from browser state. Recovery uses only FRONTEND-09 typed operations, never console/localStorage/SQL/provider action.

## Acceptance and retained evidence

- [ ] All nine URLs have one owner, loading/empty/stale/error/partial/redacted/terminal behavior, and no horizontal page overflow.
- [ ] All 48 BACKEND-02 operation IDs appear exactly and no undocumented network call exists.
- [ ] Every mutation documents request type, result type, idempotency, expected version/state, confirmation, invalidation, and reconciliation.
- [ ] M1, M6 test-inbox, and product-outreach authority are visibly separate and never collapsed into one switch.
- [ ] Current readiness-only truth is explicit; planned product UI is never described as implemented.

Retain generated-contract diff, route/operation coverage output, import/bundle authority scan, query/mutation fixtures, browser network trace, responsive screenshots, axe/keyboard/focus reports, and telemetry redaction scan.

## Dependencies and next deliverable

FRONTEND-01 consumes the exact Task 1-4 authorities and unlocks [FRONTEND-02 experiment creation](02-experiment-creation-flow.md), [FRONTEND-03 control center](03-experiment-control-center.md), and the remaining feature documents. Missing artifact-detail, generic lead, suppression-command, and operator-session HTTP contracts remain explicit backend gaps; this plan does not fill them in the browser.
