# Lead and Campaign Management

**Document ID:** FRONTEND-05
**Status:** Planned bounded campaign and suppression UI over exact BACKEND-02 contracts
**Milestone:** M7 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `FRONTEND-05-T01 -> FRONTEND-05-T02 -> FRONTEND-05-T03 -> FRONTEND-05-T04 -> FRONTEND-05-T05`; cross-document task Inputs `FRONTEND-05-T01 <- BACKEND-02-T05,BACKEND-02-T02; FRONTEND-05-T03 <- BACKEND-05-T06; FRONTEND-05-T04 <- BACKEND-02-T05; FRONTEND-05-T05 <- BACKEND-02-T05`. Descriptive source authorities/resources (not whole-document completion dependencies): [DB-03](../02-database/03-leads-campaigns-and-messages.md), [ARCH-03 lead/campaign/message states](../01-architecture/03-domain-events-and-state-machines.md#lead-state-machine), [WF-04](../03-workflows/04-lead-qualification-workflow.md), [WF-05](../03-workflows/05-outreach-and-reply-workflow.md), and [BACKEND-02](../06-backend/02-api-contracts.md)
**Outputs:** Immutable campaign-version page, server-sourced member/lead/suppression state, and exact campaign control behavior
**Unlocks:** Approval/message navigation and controlled M6 campaign operation
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Campaign membership views group qualified leads by immutable validation stage and show unassigned reserve separately. They identify duplicate/conflicting identities without exposing restricted hashes, prevent drag/drop or bulk actions from moving recipients between cohorts, and display remaining stage/cumulative capacity from the server projection rather than browser arithmetic.

The operator can create one immutable campaign version from the server's complete currently-eligible experiment snapshot, inspect that frozen membership, commit its separate readiness transition, see exact member/lead/message and suppression/conflict facts, manage versioned suppression entries, and activate/pause/resume/cancel through the generated client. There is no lead preselection or subset picker. Qualification and campaign readiness never imply send authority; suppression is always visible and wins over qualification/approval.

## Current repository state

No product business, lead, assessment, campaign, member, message, suppression, policy, or campaign API exists today. The frontend has no campaign route or components. Planned BACKEND-02 v1 now includes create/read/readiness/four campaign controls plus typed list/create/deactivate suppression operations; generic lead list/detail and CRUD remain absent.

## Scope and non-goals

In scope: campaign creation entry from experiment detail using only the aggregate eligibility summary, exact version detail/readiness, members/leads/messages as embedded post-creation data, suppression list/create/fail-closed deactivate, filters, suppression/conflict states, deep links to message/approval, and campaign control commands. Non-goals: pre-campaign lead list, manual member selection/subset/exclusion, CRM editing, bulk CSV import, ad-hoc lead CRUD, client deduplication/qualification, recipient reveal, local eligibility/suppression matching, or any unlisted API call.

## Exact planned implementation surfaces

Create `src/app/(operator)/experiments/[experimentId]/campaigns/[campaignId]/versions/[campaignVersion]/page.tsx`, its `loading.tsx`/`error.tsx`, `src/features/campaigns/components/{campaign-header,campaign-authority-summary,campaign-member-table,campaign-member-cards,campaign-controls,suppression-banner,create-campaign-dialog,suppression-manager,suppression-list,suppression-filters,create-suppression-dialog,deactivate-suppression-dialog}.tsx`, `src/features/campaigns/hooks/{use-campaign-version,use-create-campaign-version,use-campaign-command,use-suppressions,use-create-suppression,use-deactivate-suppression}.ts`, exhaustive enum formatters, and matching unit/browser tests.

### Exact state and record presentation

Render canonical `CampaignState` exactly: `DRAFT`, `READY`, `ACTIVE`, `PAUSED`, `COMPLETED`, `CANCELLED`, `FAILED`. `COMPLETED/CANCELLED/FAILED` are terminal for that version. Render canonical `LeadState`: `DISCOVERED`, `RESEARCH_PENDING`, `RESEARCHED`, `QUALIFICATION_PENDING`, `QUALIFIED`, `DISQUALIFIED`, `SUPPRESSED`, `ARCHIVED`. Render canonical `MessageState`: `DRAFT`, `APPROVAL_PENDING`, `APPROVED`, `SEND_INTENT_RECORDED`, `QUEUED`, `SENDING`, `AMBIGUOUS`, `RECONCILING`, `SENT`, `FAILED_RETRYABLE`, `FAILED_PERMANENT`, `SUPPRESSED`, `CANCELLED`.

The campaign header displays returned campaign ID/version, experiment/offer/policy refs, state, immutable caps/window/mailbox refs, server UTC times, and correlation/version facts present in `CampaignVersionResponseV1`. The member table/card alternative displays only generated safe internal IDs/hashes and state/status/reason fields; never derive “eligible” from a qualified lead. `QUALIFIED` is advisory gate output, `READY` is campaign preparation, `ACTIVE` only admits possible intents, and every actual send still requires approval, final current SEND policy, controls, budget/rate, mailbox, and gateway authority.

Suppression banners use returned `SUPPRESSED` lead/message/member facts and current report warnings. They never infer a suppression match from an address/domain in the browser. Identity `CONFLICT`/quarantine remains distinct from disqualification and is never auto-merged. A member/message in `AMBIGUOUS` or `RECONCILING` remains prominent and links to `/recovery`; campaign cancellation cannot overwrite it.

### Exact operations, request/response, and cache behavior

| Action | Contract | Client policy |
| --- | --- | --- |
| create version | `POST /api/v1/experiments/{experiment_id}/campaigns`, `createCampaignVersion`, exact `CreateCampaignVersionRequestV1` with `ALL_CURRENTLY_ELIGIBLE` expected snapshot/query/hash/count/cap and no lead IDs -> `CampaignVersionResponseV1`, 201 + `Location` | mutation `['experiment',experimentId,'campaign','create']`; copy only the fresh aggregate summary plus selected offer/policy/windows/caps; one key; no optimistic row; invalidate experiment/overview/timeline and navigate to returned `(campaign_id,campaign_version)` |
| read version | `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}`, `getCampaignVersion` | query `['campaign',campaignId,campaignVersion]`; 5 seconds active, 15 paused/draft/ready, stop terminal; focus refetch |
| ready | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/ready`, `readyCampaign`, `ReadyCampaignRequestV1={schema_version,expected_state:"DRAFT",offer_id,offer_version,policy_version} -> CampaignVersionResponseV1`, 200 | mutation `["campaign",id,version,"ready"]`; exact path version/`expected_state=DRAFT`, idempotency/CSRF; render exact guard denial; invalidate campaign/experiment/timeline; no optimistic state |
| activate | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/activate`, `activateCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `['campaign',id,version,'activate']`; request contains exact generated `expected_state`; idempotency; no ETag invented; invalidate campaign/experiment/overview/timeline/recovery; poll authoritative state |
| pause | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/pause`, `pauseCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `["campaign",id,version,"pause"]`; same expected-state/idempotency/invalidation policy; display accepted versus admission/dequeue acknowledgement; no optimistic `PAUSED` |
| resume | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/resume`, `resumeCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `["campaign",id,version,"resume"]`; same policy; re-confirm current authority warnings; server rechecks every guard; no cached allow |
| cancel | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/cancel`, `cancelCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `["campaign",id,version,"cancel"]`; same policy plus destructive typed confirmation; server may remain active/paused while provider work drains; never render terminal until refetch |

`CampaignControlRequestV1` is the only request-field authority; the UI sends its generated `schema_version`, exact `expected_state`, and generated reason fields, and adds the required `Idempotency-Key`. Campaign version is the positive path value, not a mutable ETag. `CommandReceiptV1` fields are rendered as defined in FRONTEND-01.

| Suppression action | Contract | Client policy |
| --- | --- | --- |
| list/filter | `GET /api/v1/suppressions`, `listSuppressions`, `scope`, `active`, `cursor`, `limit` -> `PageResponseV1[SuppressionResponseV1]`, 200 | query `["suppressions",{scope,active,cursor,limit}]`; `staleTime=0`, no persistence, refetch on mount/focus and every 5 seconds while manager visible; server order `(created_at,suppression_entry_id)` |
| create | `POST /api/v1/suppressions`, `createSuppression`, strict `CreateSuppressionRequestV1` union `GLOBAL={schema_version,scope,reason_code}` / `BUSINESS={schema_version,scope,business_id,reason_code}` / `RECIPIENT={schema_version,scope,recipient_source_ref_id,reason_code}` -> `SuppressionResponseV1`, 201 | mutation `["suppression","create"]`; recipient source ref is an existing opaque campaign-member ID selected from an allowlisted server response, never an address/hash/digest or the durable target ref; one key, CSRF, no ETag/optimistic row; invalidate every suppression page and campaign/message/approval/recovery/control key |
| deactivate | `POST /api/v1/suppressions/{suppression_entry_id}/commands/deactivate`, `deactivateSuppression`, `DeactivateSuppressionRequestV1={schema_version,expected_active:true,reason_code}` -> `SuppressionResponseV1`, 200 | mutation `["suppression",id,"deactivate"]`; exact row ETag via `If-Match`, one key, CSRF, no optimistic removal; retain active display until response/refetch proves inactive |

Campaign creation renders the safe aggregate count/hash/snapshot/query version and explicit warning “all currently eligible leads will be included”; it never renders or accepts pre-creation member IDs, checkboxes, exclusions, or manual count edits. If the set is zero, over the signed cap, stale, or changes between review and submit, the server denies and the UI refetches the aggregate before an entirely new confirmation. Success returns `CampaignVersionResponseV1`; only then may embedded members be displayed. The operator then uses `readyCampaign` and only after authoritative `READY` may use `activateCampaign`. Readiness refetches required artifact IDs and displays exact accepted version/hash; missing, stale, rejected, or superseded evidence blocks the dialog while the server remains the decision owner. The gateway never consumes frontend query cache and always performs its own locked authoritative suppression read after dequeue.

### Interaction, confirmation, and screen states

Only an active configured operator session may read or mutate campaign/suppression data; 403 preserves safe facts, disables actions, and focuses the denial summary. Create-version review shows exact experiment/offer/policy refs, membership mode, aggregate eligible count/hash/snapshot/query version, member/daily/total caps, authority level, and no-send warning—never a selectable lead list. Ready/activate/resume dialogs show current campaign state/version, experiment state, M1/M6/product control facts, mailbox, approval summary, suppression/conflict/ambiguity warnings, budget/rate/cap facts returned by server, and state clearly that the server may deny. Pause explains that new admissions/dequeues stop but in-flight/possibly-called sends remain quarantined until positive evidence resolves them. Cancel requires typing the final eight campaign-ID characters and entering the generated reason; it is terminal for the version only after legal closure, cancels only provably unsent work, and cannot recall mail.

Create-suppression confirmation displays exact scope and only its applicable safe input, requires the generated canonical reason, and requires typing `GLOBAL`, the final eight `business_id` characters, or the final eight selected opaque `recipient_source_ref_id` characters. The RECIPIENT source ref comes from an allowlisted campaign-member projection; the browser never accepts an address, recipient lookup hash/digest, ciphertext, or a caller-chosen target ref. After success, the UI renders the server-returned opaque `recipient_target_ref_id` as the stable target identity and never derives it from the source. Deactivation is a higher-risk removal: it displays the full safe row/version/creation reason, requires a generated reason plus the final eight suppression-ID characters, explains both controls must be off and in-flight/ambiguous work denies removal, and initially focuses the dialog heading. Escape closes only before pending; Tab stays trapped; completion/error returns focus to the invoker.

Suppression loading preserves filter/list geometry. Empty distinguishes no entries from a filter miss. Because every page is immediately stale, stale entries remain visibly labeled and never enable an authority action; focus/mount/manual refresh replaces the whole page. A partial page without its declared cursor/snapshot metadata is an error. Redacted targets retain scope plus the stored opaque `recipient_target_ref_id` for RECIPIENT (or safe `business_id` for BUSINESS), with no address/hash/digest/ciphertext field or reveal action; the target ref remains listable after source-member cleanup. Inactive rows are terminal/read-only. At 0-767px suppression cards have field/action parity; at 768px+ use the same bounded labeled table-scroll rule and never overflow the page. `ProblemDetailsV1` errors focus the summary; 409 guard reasons preserve active state, and 412 refetches before a completely new confirmation.

Pending blocks duplicate pointer/Enter/Space activation and returns focus after completion/error. Loading preserves table headings. Empty members means the returned version has none; it is not eligibility. Stale disables activate/resume/cancel until refetch when expected state may differ. Partial embedded data is labeled only if the schema provides `complete/warnings`; otherwise omission is an error/blocked feature. Redacted cells use explicit text. Terminal campaign versions are read-only and retain message/recovery links.

The desktop table is inside a labeled, keyboard-focusable bounded horizontal-scroll region only when columns cannot collapse; the page itself never overflows. At 767px and below, the table switches to ordered member cards with identical fields/actions. Filters are client presentation over the currently returned bounded page only unless a generated server filter exists.

## Ordered implementation tasks

<!-- roadmap-task id=FRONTEND-05-T01 milestone=M7 depends_on=BACKEND-02-T05,BACKEND-02-T02 mode=serial locks=frontend-client -->
- [ ] **Implement immutable all-eligible version creation/read —** Input: BACKEND-02 canonical generated create/read types, implemented no-send campaign-readiness query contract, and its fresh runtime aggregate eligibility summary. Operation: confirm the complete snapshot/caps with no lead selector, submit one request/key, navigate by returned ID/version, and render exact resource without writable copies. Output: campaign detail. Test evidence: replay/Location/version/unknown-field plus zero/overflow/drift/no-subset fixtures. Failure behavior: refetch summary; no guessed membership or local campaign row.
<!-- roadmap-task id=FRONTEND-05-T02 milestone=M7 depends_on=FRONTEND-05-T01 mode=serial locks=frontend-client -->
- [ ] **Render exhaustive lead/member/message safety states —** Input: embedded generated resource. Operation: map all canonical enums, suppression/conflict/ambiguity, and safe deep links with table/card parity. Output: bounded management view. Test evidence: every-state, redacted, empty, responsive, and unknown-enum tests. Failure behavior: affected action disabled.
<!-- roadmap-task id=FRONTEND-05-T03 milestone=M7 depends_on=FRONTEND-05-T02,BACKEND-05-T06 mode=serial locks=frontend-client -->
- [ ] **Implement readiness and four campaign controls —** Input: current expected state, fresh accepted artifacts, and generated reason fields. Operation: confirm, submit with one key, render the exact 200 readiness resource or 202 control receipt, invalidate/poll, and distinguish draining from terminal. Output: server-reconciled transition. Test evidence: stale state, double-submit, signal delay, ambiguity, cancel-drain matrices. Failure behavior: keep conservative prior/requested state and link recovery.
<!-- roadmap-task id=FRONTEND-05-T04 milestone=M7 depends_on=FRONTEND-05-T03,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Implement typed suppression management —** Input: fresh generated page/row ETag and exact target/reason requests. Operation: list/filter/page, confirm create/deactivate, freeze one key/request, reconcile response, and invalidate every authority consumer without optimistic removal. Output: audited suppression view. Test evidence: target-union, stale ETag, in-flight/ambiguity/control guard, replay, no-stale-send, focus, and mobile fixtures. Failure behavior: retain active suppression and block authority.
<!-- roadmap-task id=FRONTEND-05-T05 milestone=M7 depends_on=FRONTEND-05-T04,BACKEND-02-T05 mode=serial locks=frontend-client -->
- [ ] **Enforce API boundaries and authority —** Input: BACKEND-02 manifest. Operation: assert no generic lead CRUD, local qualification/suppression matching, auto-merge, or derived eligibility. Output: exact v1 surface. Test evidence: network/AST operation allowlist. Failure behavior: block unsupported controls and record backend need.

## Test strategy

- **Contract `test_campaign_feature_calls_exact_seven_campaign_and_three_suppression_operations`:** create/read/ready/four controls plus list/create/deactivate suppression.
- **States `test_campaign_lead_message_states_are_exhaustive_and_non_color`:** unknown blocks.
- **Suppression `test_suppressed_member_never_renders_as_sendable_despite_qualification_or_approval`:** no derived allow.
- **Ambiguity `test_cancel_drain_keeps_ambiguous_reconciling_visible_and_nonterminal`:** no false cancel.
- **Idempotency `test_campaign_command_double_activation_has_one_key_and_one_receipt`:** exact replay.
- **Membership `test_campaign_creation_can_only_submit_all_currently_eligible_snapshot_and_no_lead_selection_surface`:** exact aggregate copied; stale/overflow/subset attempts fail closed.
- **Responsive `test_member_table_card_parity_and_no_page_overflow_at_320_768_1280`:** keyboard scroll region.

## Security, privacy, compliance, idempotency, observability, and cost

List safe internal IDs/hashes and server-provided business display fields only; never expose decrypted recipient address, message body, source capture, provider account text, or suppression key. Client filters do not enter telemetry. Safe telemetry contains operation, safe campaign/version/member/message IDs, returned state, status, duration, and correlation. Costs/caps are server facts; the client neither reserves nor converts.

## Failure, rollback, and operator recovery

On stale expected state, refetch and require a new confirmation. On a 202 command whose state does not converge, keep admission assumptions closed and link correlation/resource to `/recovery`. On identity conflict or unknown suppression, remove authority actions for that row. On UI rollback, keep server campaign/version/event records. Resolve ambiguity/incident only through FRONTEND-09 typed commands.

## Acceptance and retained evidence

- [ ] Campaign version identity is immutable and every action uses exact path version plus generated expected state.
- [ ] Qualification, readiness, active state, approval, controls, and final SEND are never collapsed.
- [ ] Suppression, identity conflict, ambiguity, reconciliation, failure, and terminal states are explicit.
- [ ] Only the seven campaign and three suppression operations are used; no generic lead or CRUD endpoint is invented.
- [ ] Destructive confirmation, pending protection, focus, table/card parity, and bounded scroll pass.

Retain generated wire fixtures, network allowlist, state/command/replay traces, cancel-drain evidence, privacy scan, axe/keyboard output, and responsive screenshots.

## Dependencies and next deliverable

FRONTEND-05 consumes M5/M6 server projections. Exact messages and approvals link to [FRONTEND-06](06-approval-inbox.md) and [FRONTEND-07](07-message-and-reply-timeline.md). Generic lead CRUD remains outside v1; typed suppression management is fully specified above.
