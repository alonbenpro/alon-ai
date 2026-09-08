# Error Recovery and Accessibility

**Document ID:** FRONTEND-09
**Status:** Planned cross-cutting M4-M8 safety UX; only readiness loading/error status exists today
**Milestone:** M7, M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `FRONTEND-09-T01 -> FRONTEND-09-T02 -> FRONTEND-09-T03 -> FRONTEND-09-T04 -> FRONTEND-09-T05`; cross-document task Inputs `FRONTEND-09-T01 <- BACKEND-06-T04,BACKEND-02-T05; FRONTEND-09-T02 <- BACKEND-04-T04,BACKEND-02-T05; FRONTEND-09-T03 <- SEC-05-T04; FRONTEND-09-T04 <- BACKEND-02-T05; FRONTEND-09-T05 <- FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-03-T04,FRONTEND-08-T01,FRONTEND-08-T02,FRONTEND-08-T03,FRONTEND-03-T05,FRONTEND-08-T04,FRONTEND-01-T05,FRONTEND-03-T03`. Descriptive source authorities/resources (not whole-document completion dependencies): [WF-06](../03-workflows/06-pause-cancel-resume-and-recovery.md), [PROVIDER-01 OAuth saga](../05-providers/01-gmail-oauth-and-adapter.md), [PROVIDER-02](../05-providers/02-gmail-history-sync.md), [BACKEND-02](../06-backend/02-api-contracts.md), [BACKEND-05](../06-backend/05-approval-and-command-handling.md), [BACKEND-06 recovery projection](../06-backend/06-reporting-and-query-services.md), and FRONTEND-01 through FRONTEND-08
**Outputs:** Five-kind recovery dashboard, OAuth/mailbox UX, ambiguity/incident repair, test/product kill controls, global error semantics, WCAG-focused interaction, and tested responsive contract
**Unlocks:** Safe M6/M7 operation without SQL/provider-console recovery and M8 private-release evidence
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

At `/recovery`, the operator can see every authoritative attention item, disable either send control immediately, distinguish M1/M6/product authority, connect/sync/revoke Gmail safely, reconcile ambiguous attempts, execute only a typed incident repair, and return to affected resources. Across every route, keyboard, screen-reader, low-vision, reduced-motion, touch, stale/error, and destructive workflows remain complete.

## Current repository state

The current frontend has one responsive readiness page, a polite status region, and component tests. There is no product authentication, recovery overview, unresolved-send page, incident/repair route, system control, OAuth, mailbox, product error boundary, command dialog, E2E harness, axe gate, or full responsive product shell. All recovery and accessibility surfaces below are planned.

## Scope and non-goals

In scope: exact recovery projections/commands, controls, OAuth saga outcomes, mailboxes/sync/revoke, ambiguity, incidents/repairs, Problem Details, stale/snapshot recovery, destructive confirmations, focus/live regions, semantic alternatives, responsive breakpoints, and end-to-end recovery journeys.

Non-goals: log scraping as truth, direct runtime/provider/secret-store console action, SQL patch, free-form repair, blind resend, client auto-resolution, local gate calculation, exposing token/state/code/provider error, public accessibility claim without test evidence, or substituting animation/color for state.

## Exact planned implementation surfaces

Create `src/app/(operator)/recovery/{page,loading,error}.tsx`, `src/features/recovery/components/{recovery-overview,recovery-item,recovery-table,recovery-cards,send-attempt-recovery,incident-repair-dialog,kill-controls,control-card}.tsx`, `src/features/gmail/components/{mailbox-list,oauth-start-dialog,oauth-result,sync-mailbox-dialog,revoke-mailbox-dialog}.tsx`, `src/features/recovery/hooks/{use-recovery-overview,use-unresolved-send-attempts,use-recovery-command}.ts`, `src/features/gmail/hooks/{use-mailboxes,use-gmail-command}.ts`, `src/features/controls/hooks/use-controls.ts`, `src/features/auth/components/{session-boundary,sign-in-panel,session-expired-dialog,reauth-banner,sign-out-button}.tsx`, `src/features/auth/hooks/use-operator-session.ts`, shared `ProblemPanel`, `ErrorSummary`, `CommandDialog`, `StaleBanner`, and `LiveCommandStatus`, plus Playwright-equivalent E2E/accessibility coverage under `frontend/e2e/` using the repository-selected runner when added.

### Recovery overview and typed actions

`getRecoveryOverview` is the sole recovery truth and returns `PageResponseV1[RecoveryOverviewItemV1]` ordered `(attention_since,record_kind,record_id)`. Render all exact kinds: `WORKFLOW_RUN`, `COMMAND`, `SEND_ATTEMPT`, `CURSOR_INCIDENT`, `REPAIR_ACTION`. Each item shows stable safe ID, attention time, state/reason, safe authority/evidence IDs, and exact server-returned next allowed commands. Unknown kind or action disables it; the client does not construct recovery items from logs, timelines, or parallel queries.

| Operation | Contract, key, policy |
| --- | --- |
| `getRecoveryOverview` | `GET /api/v1/recovery/overview`, cursor/limit; `['recovery','overview',{cursor,limit}]`; 3-second poll while any attention item/pending command, 15 seconds empty, focus refetch; snapshot expiry discards all pages |
| `listUnresolvedSendAttempts` | `GET /api/v1/recovery/send-attempts`, `(started_at,send_attempt_id)`; `['recovery','send-attempts',{cursor,limit}]`; same high-attention policy |
| `reconcileSendAttempt` | `POST /api/v1/send-attempts/{send_attempt_id}/commands/reconcile`; `ReconcileSendAttemptRequestV1 -> CommandReceiptV1`; mutation `['send-attempt',id,'reconcile']`; one key, no invented ETag, no optimistic resolution; 202 polls both recovery/message/provider/timeline |
| `repairIncident` | `POST /api/v1/incidents/{incident_id}/commands/repair`; `RepairIncidentRequestV1 -> IncidentRepairResponseV1`; mutation `['incident',id,'repair']`; one key; generated `incident.catalog.v1` repair kind, expected-before hash, desired-after hash/evidence fields only; invalidate all affected keys |

Reconciliation dialog repeats exact authorized mailbox/account hash, campaign/member/message/intent/attempt/RFC/final-SEND/rate-lease references and warns that it reads provider history only; it never sends. A 202 remains `AMBIGUOUS/RECONCILING` until server state resolves. Multiple/cross-mailbox/malformed evidence stays failed/conflict and opens incident.

Repair dialog lists only generated `incident.catalog.v1` repair kinds and the server-provided next allowed commands. It renders returned `trigger_code`, `runbook_id`, `alert_id`, `resolution_code`, and `catalog_version` only through exhaustive generated enum maps; an unknown value or cross-catalog tuple blocks the action, shows `INCIDENT_CATALOG_MISMATCH`, and never falls back to free text. It displays before/evidence hashes and consequence, requires typing the repair kind plus exact generated reason/evidence fields, and never accepts SQL/path/value patches. `ABORT_OAUTH_SAGA` is legal only through server proof. A completed repair remains an immutable `REPAIR_ACTION` record.

### System kill controls and authority ladder

`listSystemControls` query key is `['controls']`, polled every 3 seconds while changing/incident-open and 10 seconds otherwise, always refetched on focus. Render `TEST_INBOX_SENDING` and `PRODUCT_OUTREACH` as separate versioned cards, never one master switch. Each shows returned boolean/state/version, changed UTC, exact `OPERATOR` or registered `SYSTEM` actor type/ID, reason/evidence, M1/M6 gate refs, blocking incidents/ambiguities, and correlation fields present in generated resources; a system disable is never labeled as operator action.

`enableSystemControl` and `disableSystemControl` use exact `POST /api/v1/controls/{control_name}/commands/enable` and `POST /api/v1/controls/{control_name}/commands/disable`, each with `ChangeControlRequestV1 -> CommandReceiptV1` and key `["control",name,"enable"]` or `["control",name,"disable"]`, one idempotency key, and `If-Match` from the specific control ETag/version. The request contains only generated `schema_version`, reason/evidence/gate fields. Invalidations cover controls, recovery, experiment/campaign overview, approvals/messages, provider/timeline reports.

Disable is always available to an authenticated active operator and is visually primary during risk. It requires a review dialog and reason capture defined by the schema but no typed phrase that slows an emergency kill. On receipt commit, the UI announces “Disable committed; runtime/provider drain status pending” and refetches; it does not optimistically show every worker stopped. Enable is more deliberate: type the exact control name, review M1/M6/current incident/compliance/security facts, and understand that enable creates no campaign/member/message/approval/intent/reservation/send. `TEST_INBOX_SENDING` requires owned-alias evidence and cannot enable product. `PRODUCT_OUTREACH` requires retained M1 and M6 gate evidence and no blockers, yet still grants no downstream authority.

### FastAPI-owned operator OIDC session UX

`src/features/auth/components/{session-boundary,sign-in-panel,session-expired-dialog,reauth-banner,sign-out-button}.tsx` and `src/features/auth/hooks/use-operator-session.ts` consume only the four generated auth operations. `getOperatorSession` key `["auth","session"]` bootstraps before any product query; all API calls set `credentials:"include"`, while JavaScript never reads the opaque `__Host-alon_ai_session` or flow cookie. Missing/expired/revoked/reauth-required session clears every product query and focuses the sign-in/reauth heading without displaying stale authority actions.

| Operation | Exact frontend behavior |
| --- | --- |
| `startOperatorAuthorization` | `POST /api/v1/auth/authorizations`; `StartOperatorAuthorizationRequestV1 -> OperatorAuthorizationResponseV1`; mutation `["auth","start"]`, one anonymous-flow idempotency key, safe current relative return path, browser-supplied exact Origin/fetch metadata; navigate only to the returned allowlisted Google authorization URL/`Location` |
| `completeOperatorAuthorization` | FastAPI handles `GET /api/v1/auth/callback` as success `{code,state,iss,scope?}` or error `{error,state,iss,error_description?}` plus HttpOnly flow cookie; duplicate, cross-arm, missing required, any other parameter, or callback issuer not byte-equal to `https://accounts.google.com` is rejected; the later verified ID-token issuer separately allows exactly `{accounts.google.com,https://accounts.google.com}`; success uses stored allowlisted return path, failure is exactly `/?operator_auth=auth_invalid`, `/?operator_auth=auth_denied`, or `/?operator_auth=auth_expired`; Next.js never handles/logs/stores provider code/state/error/claims and only renders those three safe labels |
| `getOperatorSession` | `GET /api/v1/auth/session -> OperatorSessionResponseV1`; key `["auth","session"]`; render safe operator ID/subject hash and idle/absolute expiry/reauth only; refetch on focus and at most every 5 minutes/returned rotation deadline |
| `endOperatorSession` | `DELETE /api/v1/auth/session -> OperatorSessionEndedResponseV1`; mutation `["auth","end"]`; exact Origin/fetch metadata and `X-CSRF-Intent: operator-session-v1`; on 200 clear all queries, announce ended, focus sign-in |

Session bootstrap loading renders only shell landmarks and one polite status; no product query starts. Empty is the explicit signed-out state. A session snapshot becomes stale immediately at its returned idle/absolute deadline and blocks commands until refetch; it is never extended by client time. `401` reasons distinguish missing, idle-expired, absolute-expired, revoked, and reauth-required copy while sharing the fail-closed boundary. `403` configured-subject/CSRF denial focuses the safe error summary and offers no product retry; `503` offers bounded session retry without retaining product facts. Partial or unknown/redacted session schema is invalid, clears cache, and signs the view out. Logout, expiry, and revocation are terminal for that handle; a new authorization creates a new server session rather than reviving it. Callback result focus lands on the sign-in error or restored page heading. The boundary reflows at 320/768/1280, has 44×44 actions, visible focus, no page overflow, and no motion-dependent state.

Session cookie behavior is exactly BACKEND-02: opaque 256-bit, Secure, HttpOnly, SameSite=Strict, Path=/, Domain absent, 30-minute idle, fixed 8-hour absolute expiry/remaining `Max-Age`, 15-minute rotation and 30-second overlap; OIDC flow cookie is Lax/Path `/`/Domain-absent/10-minute/single-use. The UI stores no access/refresh/identity/session token in URL, JavaScript, localStorage, sessionStorage, logs, or telemetry. Product mutations add `X-CSRF-Intent: operator-command-v1`; 403 `CSRF_CHECK_FAILED` is terminal for that submission and triggers no replay until a fresh same-origin session check. Task 6 deepens storage/security implementation without changing these generated flows.

### Gmail OAuth and mailbox saga UX

| Operation | Contract and behavior |
| --- | --- |
| `startGmailAuthorization` | `POST /api/v1/gmail/oauth/authorizations`; exact `StartGmailAuthorizationRequestV1 -> GmailAuthorizationResponseV1`, 201 `Location`; mutation `['gmail','oauth','start']`, one key; navigate only to returned Location after explicit scope/account warning |
| `completeGmailAuthorization` | provider calls `GET /api/v1/gmail/oauth/callback?code&state`; no caller key/auth header; backend derives flow key and returns only fixed 303 outcomes after saga rules; frontend never reads/logs/persists `code` or `state` |
| `listGmailMailboxes` | `GET /api/v1/gmail/mailboxes`; paged `(created_at,mailbox_id)`; `['gmail','mailboxes',{cursor,limit}]`; 15 seconds/on-focus, 3 seconds during explicit saga/revoke/sync recovery |
| `syncGmailMailbox` | `POST /api/v1/gmail/mailboxes/{mailbox_id}/commands/sync`; `SyncGmailMailboxRequestV1 -> CommandReceiptV1`, 202 receipt; `['gmail','mailbox',id,'sync']`; one key + `If-Match` from the current generated Gmail history-cursor ETag/version plus generated expected status/state; invalidate mailbox/recovery/message/provider/timeline |
| `revokeGmailAuthorization` | `DELETE /api/v1/gmail/mailboxes/{mailbox_id}/authorization`; `RevokeGmailAuthorizationRequestV1 -> CommandReceiptV1`, 202 receipt; `['gmail','mailbox',id,'revoke']`; one key + generated expected status/state; destructive confirmation; invalidate mailbox/controls/recovery/provider |

OAuth presentation reflects exact saga facts only when returned: flow claim `IN_PROGRESS`; exchange begun; flow-indexed `STAGED`; exact `ACTIVE` credential proof; mailbox bind; command `SUCCEEDED`; fixed result `oauth_connected`, `oauth_conflict`, `oauth_invalid`, or `oauth_restart_required`; resumable dependency exhaustion stays `IN_PROGRESS` with `Retry-After`. Only exact ACTIVE proof plus committed mailbox+SUCCEEDED can show connected. A staged/active secret object without DB commit is not connected. `EXCHANGE_STARTED` with no discoverable credential requires restart and never a browser re-exchange. DB/secret tuple mismatch shows mailbox disabled/incident and both controls conservative.

Start dialog shows exact requested Gmail scopes/account/owned-alias purpose returned/defined by generated request, warns credentials never enter frontend, and opens returned Google URL in the same top-level context to preserve accessible navigation. Revoke requires typing the last eight mailbox ID characters, explains that revocation disables/reconciles and may be denied while safety is unresolved, and never claims provider deletion before server reconciliation. Sync is non-destructive but confirmed and 202/polled.

### Global error, confirmation, and server-result reconciliation

All errors render strict `ProblemDetailsV1={type,title,status,detail,instance,error_code,request_id,correlation_id,reason_codes,current_version}`. The UI maps exact error codes, preserves safe detail ≤300 characters, provides copy buttons for request/correlation IDs, and never displays provider/raw exceptions.

- 400/422 validation: focus error summary; field links only where generated pointers exist.
- 401: clear in-memory product cache and render session-required boundary.
- 403: keep read facts, disable denied action, show safe policy/authorization reasons.
- 404: safe not-found with parent navigation; no resource existence leak beyond authenticated schema.
- 409 idempotency/version/state/ambiguity: exact replay or refetch/reconfirm; ambiguity only to recovery.
- 412/428: refetch ETag or require missing generated precondition; never guess.
- 429: render budget/rate reason and bounded `Retry-After`; no automatic mutation retry.
- 503: degraded, retain last snapshot as visibly stale only if schema permits; no authority actions.
- 500: opaque incident reference/correlation and Recovery link; no stack/provider payload.

Every destructive/authority action uses a modal dialog (`role=dialog`, `aria-modal=true`, labelled heading/description), exact scope/consequence, required generated reason/evidence, and confirmation strength proportional to harm. Pending buttons are disabled and guarded in the mutation function; reactivation returns the same promise/key. Closing/navigating warns when an outcome is unknown. Receipt/result is rendered before invalidation/refetch; 200/201/202 semantics remain distinct.

### WCAG-focused responsive and interaction contract

Target WCAG 2.2 AA for the private app and verify, do not merely claim. Tested viewport/zoom matrix: 320×568 CSS px, 768×1024, 1280×800, and 200% browser zoom at 1280 width. CSS breakpoints are small `0-639px`, medium `640-1023px`, and wide `>=1024px`. Content reflows without horizontal **page** scrolling; dense tables may horizontally scroll only inside a bounded region with `role=region`, accessible label, visible keyboard focus, and card alternative below 768px. Touch targets are at least 44×44 CSS px.

Every page has skip link, one `main`, ordered headings, nav label/current page, semantic lists/tables/forms, programmatic labels/descriptions, visible 2px+ focus indicator not obscured, and logical DOM/tab order independent of visual grid. Keyboard-only supports all dialogs, menus, tabs if used, paging, filters, table regions, confirmations, and recovery actions; no drag-only behavior. Focus moves to the page heading on navigation, error summary on failed submit, status heading on destructive success, and back to invoker on dialog close.

Async query state uses `role=status`/polite for routine updates; destructive failure/kill confirmation uses assertive alert sparingly. `aria-busy` marks the scoped region. Do not repeatedly announce 3-second polling when content is unchanged. Status always has text and icon/pattern, never color alone. Charts have data tables as FRONTEND-08 defines. Time/currency units are spoken. Error suggestions do not rely on position/color. `prefers-reduced-motion` removes nonessential transitions and no essential status is animated. High contrast/forced colors retain borders/focus/icons. Target contrast: 4.5:1 normal text, 3:1 large text/UI/meaningful graphics.

Loading skeletons are `aria-hidden` with one status message. Empty, stale, error, partial, redacted, pending, unknown, and terminal states have unique copy. Server UTC is available beside Asia/Jerusalem presentation. All list/table pagination retains focus at the first new heading/row and announces count without moving focus unexpectedly.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-09-T01 milestone=M7 depends_on=BACKEND-06-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement five-kind recovery overview —** Input: `RecoveryOverviewItemV1` and snapshot cursor, using BACKEND-02 canonical generated client/types. Operation: render exhaustive kinds/actions, stable pages, attention age/state/reasons/authority refs, and deep links. Output: one recovery queue. Test evidence: all kinds, unknown, concurrent commits, cursor expiry, empty/stale/503 fixtures. Failure behavior: no reconstructed/log-derived recovery truth.
<!-- roadmap-task id=FRONTEND-09-T02 milestone=M7 depends_on=FRONTEND-09-T01,BACKEND-04-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement ambiguity and typed repair —** Input: unresolved attempt and exact `incident.catalog.v1` generated schemas. Operation: confirm mailbox-bound reconcile or registered repair with exact catalog/trigger/runbook/alert/resolution/kind tuple, key/evidence, render 200/202, invalidate/poll. Output: auditable recovery without resend/SQL. Test evidence: zero/one/many/cross-mailbox, repair hash conflict, catalog mismatch/unknown-code rejection, double-submit, crash/replay. Failure behavior: both controls conservative and incident remains open.
<!-- roadmap-task id=FRONTEND-09-T03 milestone=M7 depends_on=FRONTEND-09-T02,SEC-05-T04 mode=serial locks=frontend-client -->
- [ ] **Implement kill controls and authority separation —** Input: versioned controls and gate/incident facts. Operation: fast confirmed disable, deliberate enable, `If-Match`, idempotency, receipt/ack distinction, and broad invalidation. Output: independent test/product controls. Test evidence: emergency keyboard kill, stale version, missing M1/M6, ambiguity blocker, signal-delay tests. Failure behavior: controls remain/return false and no downstream authority.
<!-- roadmap-task id=FRONTEND-09-T04 milestone=M7 depends_on=FRONTEND-09-T03,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement operator OIDC session and Gmail OAuth/mailbox saga UX —** Input: four generated operator-session operations plus generated Gmail start/list/sync/revoke and fixed callback outcomes. Operation: navigate to returned Location, expose no code/state/token, render exact ACTIVE/bind/success or restart/conflict/degraded states, and reconcile commands. Output: safe mailbox management. Test evidence: six kill points, exact replay, staged/active resume, exchange gap restart, mismatch disable, revoke/sync 202. Failure behavior: fresh flow/incident; no browser retry exchange.
<!-- roadmap-task id=FRONTEND-09-T05 milestone=M8 depends_on=FRONTEND-09-T04,FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-03-T04,FRONTEND-08-T01,FRONTEND-08-T02,FRONTEND-08-T03,FRONTEND-03-T05,FRONTEND-08-T04,FRONTEND-01-T05,FRONTEND-03-T03 mode=serial locks=frontend-client -->
- [ ] **Apply and verify global accessibility/responsive contract —** Input: all FRONTEND routes/components/states; complete authenticated frontend foundation and integrated control-center report/control surface. Operation: semantic/focus/live/error/keyboard/touch/reflow/non-color/reduced-motion/table-card/contrast implementation and automated+manual matrix. Output: M8 evidence. Test evidence: axe, keyboard scripts, screen-reader smoke, screenshots at exact matrix, 200% zoom, forced colors. Failure behavior: release blocked; no unverified compliance claim.

## Test strategy

- **Recovery `test_recovery_overview_renders_exact_five_kinds_and_only_server_allowed_commands`:** unknown blocks.
- **Ambiguity `test_reconcile_never_calls_send_and_cross_mailbox_evidence_stays_incident`:** network/authority proof.
- **Kill `test_keyboard_disable_commits_once_and_does_not_claim_runtime_ack`:** both controls independently.
- **Session `test_oidc_cookie_rotation_expiry_logout_reauth_csrf_and_exact_google_callback_union_have_no_js_token`:** configured operator only; callback `iss=https://accounts.google.com` passes and legacy callback `iss=accounts.google.com` fails; both spellings pass only for the separately verified ID-token issuer fixture; every allowed optional parameter plus missing/duplicate/extra/cross-arm fixtures.
- **Incident catalog `test_incident_ui_rejects_unknown_or_cross_version_trigger_runbook_alert_resolution_and_repair_kind`:** no generic fallback or mutation.
- **OAuth `test_ui_never_observes_code_state_token_and_connected_requires_committed_active_result`:** privacy/saga matrix.
- **Errors `test_every_problem_code_has_focus_safe_copy_and_no_raw_payload`:** exact status mapping.
- **Responsive `test_no_horizontal_page_overflow_at_320_768_1280_and_200_percent_zoom`:** bounded table regions only.
- **Accessibility `test_all_routes_actions_states_pass_axe_keyboard_focus_live_region_contrast_and_reduced_motion`:** manual evidence retained.
- **E2E `test_operator_can_pause_kill_reconcile_repair_revoke_and_return_without_sql_or_provider_console`:** complete safe journey.

## Security, privacy, compliance, idempotency, observability, and cost

Never expose identity/access/refresh/session tokens, OAuth state/code, credential handles/versions/keys, Gmail tokens, addresses/content, provider payloads, raw logs, repair sensitive evidence, or cursors. Safe telemetry uses route template, operation ID, safe record/control/mailbox/incident IDs, returned state/error/reason, request/correlation ID, duration/poll count, and accessibility interaction failures without field values. Disable/repair/OAuth actions are audited by backend; frontend history is not audit authority. Pause/disable may prevent new cost but never rewrites incurred cost.

## Failure, rollback, and operator recovery

If control acknowledgement exceeds the tested bound, OAuth tuple disagrees, report snapshot is corrupt, runtime/product/provider states disagree, or the frontend cannot render a canonical state, keep both controls disabled, stop presenting authority actions, preserve the last safe server facts as stale, and direct the operator to the exact recovery/incident record. Roll back frontend code independently; never mutate product/secret/provider state. Restore/SQL/provider-console actions are not browser recovery paths.

## Acceptance and retained evidence

- [ ] Recovery shows all five kinds, exact next allowed commands, ambiguity/repair evidence, and no log-derived truth.
- [ ] M1, M6 `TEST_INBOX_SENDING`, and `PRODUCT_OUTREACH` controls/gates are separate; disable is fast and enable grants nothing downstream.
- [ ] OAuth success cannot render before exact ACTIVE proof plus committed mailbox/SUCCEEDED; secrets/code/state remain absent.
- [ ] All destructive/authority actions have scope, reason/evidence, confirmation, pending protection, focus, receipt, invalidation, and server reconciliation.
- [ ] WCAG-focused semantics, keyboard, focus, live regions, table/card/chart alternatives, non-color, reduced motion, touch targets, contrast, exact breakpoints, zoom, and no page overflow are verified.

Retain recovery/OAuth/control network and crash traces, request/receipt/reconciliation fixtures, privacy/secret scan, exact breakpoint/zoom screenshots, axe/contrast/keyboard/screen-reader results, and full operator recovery E2E video/log with sensitive data redacted.

## Dependencies and next deliverable

FRONTEND-09 closes the Task 5 operator plan and is required by every earlier frontend document. Passing its M6/M7 journeys plus M8 private-access/operations evidence unlocks only the separately pre-registered, capped M9 experiment; it never authorizes autonomous scale or public launch.
