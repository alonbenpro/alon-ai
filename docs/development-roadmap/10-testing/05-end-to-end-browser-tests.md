# End-to-End Browser, Accessibility, and Responsive Tests

**Document ID:** TEST-05
**Status:** Planned M7-M8 browser suite; current frontend renders only readiness and has unit tests, not the product routes or browser automation described here
**Milestone:** M8, M9 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `TEST-05-T01 -> TEST-05-T02 -> TEST-05-T03 -> TEST-05-T04 -> TEST-05-T05 -> TEST-05-T06`; cross-document task Inputs `TEST-05-T01 <- TEST-01-T03,BACKEND-02-T05; TEST-05-T02 <- FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-08-T01,FRONTEND-08-T03,FRONTEND-09-T04,FRONTEND-01-T05,FRONTEND-03-T03; TEST-05-T03 <- SEC-02-T06,PROVIDER-01-T06,FRONTEND-09-T05; TEST-05-T05 <- SEC-04-T04; TEST-05-T06 <- TEST-01-T01`. Descriptive source authorities/resources (not whole-document completion dependencies): BACKEND-02/05/06, FRONTEND-01 through [FRONTEND-09](../07-frontend/09-error-recovery-and-accessibility.md), SEC-02, TEST-01/02/04, and representative real-PostgreSQL projections
**Outputs:** Deterministic operator-journey specs, accessibility/responsive evidence, auth/OAuth/recovery browser security proof, and public scanner-safe unsubscribe journey
**Unlocks:** M7 operator usability, M8 private release, and only the public-browser portion of the M9 gate
**Risk:** High
**Complexity:** L

## Outcome and timing

One operator can create, inspect, approve, pause, cancel, reconcile, repair, revoke, restore context, and make a decision using only server-authoritative generated contracts, with keyboard/screen-reader/responsive behavior and no secret/PII exposure. Browser success never implies a command completed until the returned receipt/projection says so.

The staged M9 journey shows `100 -> 100`, `200 -> 300`, `300 -> 600`, and `400 -> 1,000`; incremental/cumulative funnel evidence; observation-window status; and the signed barrier. Browser tests prove the next-stage control is inaccessible for missing/stale/non-`CONTINUE` decisions, double clicks replay one command, safety stop removes the action immediately, and no UI path offers an immediate-1,000 admission.

## Current repository state

Next.js currently has a readiness page, TanStack Query, generated health client types, Testing Library/Vitest and a production build. There are no product routes, OIDC session UI, Gmail OAuth flow, approval/recovery dashboards, Playwright dependency, axe runner, responsive screenshots, public unsubscribe page, or browser E2E CI lane.

## Scope and non-goals

In scope: all 64 private operation consumers, auth/session cookies and callback unions, Gmail OAuth saga presentation, experiment/lead/campaign/approval/message/cost/evidence/recovery journeys, five recovery kinds, incident/control commands, stale/partial/error states, exact 14 policy denial explanations, keyboard/focus/live regions, WCAG 2.2 AA target checks, breakpoints/zoom/forced colors/reduced motion, scanner-safe public GET/POST. Non-goals: browser-stored tokens, page objects that reconstruct policy truth, screenshot-only accessibility, arbitrary production crawling, automated provider-console repair, or public signup/API/webhook.

## Exact planned implementation surfaces

Add Playwright and axe to `frontend/`, create `frontend/tests/e2e/`, `frontend/tests/accessibility/`, `frontend/playwright.config.ts`, deterministic API/database fixture builders, and trace/screenshot redactor. Browser servers bind loopback in CI; each worker owns a database schema and session subject fixture. The public unsubscribe Playwright project navigates directly to the FastAPI origin with no Next.js server, route, bundle, generated client, operator cookie, or private route access.

| Journey | Required path | Failure/security assertions |
| --- | --- | --- |
| operator session | anonymous start -> strict Google callback fixture -> rotated opaque cookie -> session -> logout/reauth/expiry | no token/code/state in JS/storage/URL/log; wrong issuer/subject/CSRF/fixation/replay uniformly denied |
| experiment | create brief -> synthetic research/qualification -> review evidence -> campaign/approval -> pause/resume/cancel -> decision | server state/event/ETag/receipt wins; double click replay-safe; no send without gates |
| Gmail mailbox | start separate OAuth -> six saga outcomes -> ACTIVE/restart/conflict -> sync/revoke | browser sees no credential/code/state; success only after ACTIVE proof+DB commit |
| message/recovery | direct/ambiguous/reconciled/failed/suppressed timeline; five recovery kinds; typed incident repair | reconcile never calls send; cross-mailbox/unknown catalog/repair hash blocks; no SQL/provider console |
| kill/authority | keyboard disable test/product independently, pending acknowledgement, denied enable with missing evidence | disable commits once; enable creates no work/grant; stale version fails visibly |
| public unsubscribe | direct FastAPI scanner/navigation GET; explicit HTML-button POST; expired/invalid/already suppressed; abuse throttling | exact 1,057 bytes/hash/headers and zero writes on GET; POST exact Origin/fetch/CSRF; opaque uniform result; no Next request/bundle/private operation/cookie/identifier/third party |

Viewport matrix is exactly `320x568`, `768x1024`, `1280x800`, and 200% zoom at 1280 CSS-pixel width. Verify breakpoints `0-639`, `640-1023`, `>=1024`; 44x44 CSS-pixel touch targets; no horizontal page scroll; bounded labeled table regions plus cards below 768; 4.5:1 normal text and 3:1 large/UI/graphics. Run Chromium, Firefox and WebKit for core journeys; accessibility/manual screen-reader smoke uses the operator's supported production browser and VoiceOver on macOS, with browser/OS versions recorded.

Reference commands after implementation:

```sh
npm --prefix frontend run test -- --run
npm --prefix frontend run build
npm --prefix frontend exec playwright test --project=private-chromium --project=private-firefox --project=private-webkit
npm --prefix frontend exec playwright test --project=public-unsubscribe
```

The reference child commands are owned by two closed runner rows: all 64 private-operation, accessibility and viewport requirements map exactly to `T7-BROWSER-PRIVATE`; the scanner-safe pair maps exactly to `T7-BROWSER-PUBLIC`. The planned repository-root invocation is the [TEST-01 exact runner form](01-testing-strategy.md#closed-command-manifest) with the signed target manifest and literal `T7-BROWSER-PRIVATE|BROWSER_PRIVATE` or `T7-BROWSER-PUBLIC|BROWSER_PUBLIC_M9` row values. The public guard requires signed M9 legal/policy/public-ingress evidence, exact two-route edge hash, synthetic tokens and no private cookies/routes; absence of Playwright/browser or public M9 ingress exits `30`, never pass. Mapping set equality proves `private=64`, `public=2`, intersection empty and union 66.

## Ordered implementation tasks

<!-- roadmap-task id=TEST-05-T01 milestone=M8 depends_on=TEST-01-T03,BACKEND-02-T05 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Build isolated browser fixture composition —** Input: signed database/API fixtures and operation manifest. Operation: start per-worker API/frontend/schema/session contexts with provider network spies. Output: deterministic browser environment. Test evidence: parallel isolation, stale projection, API restart and forbidden network cases. Failure behavior: abort worker and retain trace; no shared fallback.
<!-- roadmap-task id=TEST-05-T02 milestone=M8 depends_on=TEST-05-T01,FRONTEND-01-T04,FRONTEND-02-T04,FRONTEND-03-T01,FRONTEND-03-T02,FRONTEND-04-T04,FRONTEND-05-T05,FRONTEND-06-T04,FRONTEND-07-T04,FRONTEND-08-T01,FRONTEND-08-T03,FRONTEND-09-T04,FRONTEND-01-T05,FRONTEND-03-T03 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Implement private operator journeys —** Input: exact FRONTEND route/action/state contracts; complete authenticated frontend foundation and integrated control-center report/control surface. Operation: execute session, experiment, evidence, lead/campaign, approval, timeline, cost, decision and recovery flows. Output: end-to-end receipts/projections. Test evidence: 64-operation consumer coverage and every empty/loading/stale/error/partial/redacted/pending/unknown/terminal state. Failure behavior: release blocked.
<!-- roadmap-task id=TEST-05-T03 milestone=M8 depends_on=TEST-05-T02,SEC-02-T06,PROVIDER-01-T06,FRONTEND-09-T05 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Prove auth/OAuth/control/recovery security —** Input: SEC-02/PROVIDER-01/FRONTEND-09 matrices. Operation: exercise callbacks, cookies, CSRF, saga kills, independent controls, ambiguity and incident repair. Output: no-secret auditable browser proof. Test evidence: request/network/storage/console scans and provider send spy. Failure behavior: controls false and affected capability unavailable.
<!-- roadmap-task id=TEST-05-T04 milestone=M8 depends_on=TEST-05-T03 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Prove accessibility and responsive contract —** Input: all routes/states and exact viewport matrix. Operation: run axe plus keyboard/focus/live/contrast/zoom/forced-color/reduced-motion/screen-reader checks. Output: signed screenshots/traces/manual checklist. Test evidence: no page overflow and every action operable without pointer/color. Failure behavior: M8 release blocked; no conformance claim.
<!-- roadmap-task id=TEST-05-T05 milestone=M9 depends_on=TEST-05-T04,SEC-04-T04 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Prove scanner-safe public unsubscribe —** Input: M9-gated two-route FastAPI fixture and synthetic token. Operation: run scanner GET, exact HTML hash/header/CSP checks, explicit button POST and abuse/security matrix with the Next server absent. Output: public-browser/WAF-compatible evidence. Test evidence: DB write spy zero and no Next asset/route request on GET, one idempotent suppression on POST, uniform/redacted errors. Failure behavior: public partition remains unavailable and product outreach false.
<!-- roadmap-task id=TEST-05-T06 milestone=M9 depends_on=TEST-05-T05,TEST-01-T01 mode=serial locks=test-command-registry,frontend-client -->
- [ ] **Close private/public browser command ownership —** Input: every journey/state/viewport/accessibility/route requirement. Operation: prove exact disjoint mapping to the two browser commands and verify profiles, target identity, artifacts and exit semantics. Output: signed browser command map. Test evidence: 64+2 equality, swapped-profile and unavailable-browser negatives. Failure behavior: affected M8/M9 gate remains failed.

## Test strategy

- **Coverage `test_private_browser_journeys_consume_all_64_operations_without_handwritten_contracts`.**
- **Session `test_oidc_cookie_rotation_expiry_logout_reauth_callback_and_csrf_never_expose_token`.**
- **Recovery `test_five_recovery_kinds_and_typed_repairs_never_resend_or_use_cross_mailbox_evidence`.**
- **Control `test_keyboard_kill_commits_once_and_enable_grants_no_downstream_authority`.**
- **Accessibility `test_routes_states_actions_pass_axe_keyboard_focus_live_contrast_motion_and_touch_matrix`.**
- **Responsive `test_no_page_overflow_at_320_768_1280_and_200_percent_zoom`.**
- **Public `test_scanner_get_is_read_only_and_only_explicit_same_origin_post_suppresses`.**

## Security, privacy, compliance, idempotency, observability, and cost

Use synthetic content and opaque IDs; traces/video/screenshots/console/network archives pass redaction before retention. Test cookies/tokens never leave the disposable environment. Every unsafe action carries exact Origin/fetch/CSRF/idempotency/If-Match semantics. Accessibility evidence supports a verified target, not a blanket compliance claim. Browser polling/load is bounded and included in capacity tests; no provider/model/Gmail spend occurs except the separately authorized owned-alias lane.

## Failure, rollback, and operator recovery

On token/PII exposure, provider call from UI/reconcile, inaccessible kill action, page overflow hiding authority, stale success, route widening, or scanner GET mutation: stop the suite/release, set controls false, preserve redacted trace and authoritative DB facts, revoke test sessions, and fix backend/frontend/edge contract together. Roll back frontend by immutable release digest. Never mark a visual snapshot as approved over a semantic/security failure.

## Acceptance and retained evidence

- [ ] All private journeys and canonical states/actions are server-authoritative, replay-safe and usable by keyboard.
- [ ] Auth/OAuth/recovery paths expose no secret and cannot bypass mailbox/catalog/control boundaries.
- [ ] Exact accessibility/responsive matrix has automated and manual evidence without a false compliance claim.
- [ ] Public GET is scanner-safe/read-only and POST alone performs opaque idempotent suppression.

Retain browser/runtime/version manifests, sanitized traces/screenshots/video/network logs, operation coverage, axe/contrast/keyboard/VoiceOver results, viewport/zoom evidence, database/provider call counts and release decisions.

## Dependencies and next deliverable

TEST-05 consumes TEST-02 contracts and TEST-04 Gmail semantics. Its private suite feeds INFRA-02/M8; its public subset feeds [TEST-06](06-load-security-and-chaos-tests.md) and [INFRA-03](../11-infrastructure/03-private-vps-deployment.md). Neither suite enables outreach or publishes a route.
