# Lead and Campaign Management

**Document ID:** FRONTEND-05
**Status:** Planned bounded campaign UI; BACKEND-02 defines campaign-version commands but no generic lead or suppression mutation API
**Milestone:** M5 read-only qualification visibility and M6-M7 campaign control
**Owner:** Solo operator
**Prerequisites:** [DB-03](../02-database/03-leads-campaigns-and-messages.md), [ARCH-03 lead/campaign/message states](../01-architecture/03-domain-events-and-state-machines.md#lead-state-machine), [WF-04](../03-workflows/04-lead-qualification-workflow.md), [WF-05](../03-workflows/05-outreach-and-reply-workflow.md), and [BACKEND-02](../06-backend/02-api-contracts.md)
**Outputs:** Immutable campaign-version page, server-sourced member/lead/suppression state, and exact campaign control behavior
**Unlocks:** Approval/message navigation and controlled M6 campaign operation
**Risk:** Critical
**Complexity:** L

## Outcome and timing

The operator can create and inspect one immutable campaign version, see the exact member/lead/message states and suppression/conflict facts returned by that resource, and activate/pause/resume/cancel it through the generated client. Qualification and campaign readiness never imply send authority; suppression is always visible and wins over qualification/approval.

## Current repository state

No product business, lead, assessment, campaign, member, message, suppression, policy, or campaign API exists today. The frontend has no campaign route or components. BACKEND-02 v1 includes `createCampaignVersion`, `getCampaignVersion`, and four campaign controls. It includes neither a lead list/detail route nor `SuppressRecipient`, `SuppressBusiness`, `EnableGlobalSuppression`, `DeactivateSuppression`, or `ReadyCampaign` operations, even though backend command/domain documents name those internal commands.

## Scope and non-goals

In scope: campaign creation entry from experiment detail, exact version detail, members/leads/messages as embedded generated data, filters, suppression/conflict states, deep links to message/approval, and campaign control commands. Non-goals: CRM editing, bulk CSV import, ad-hoc lead CRUD, client deduplication/qualification, suppression mutation, “mark ready,” recipient reveal, local eligibility calculation, or any unlisted API call.

## Exact planned implementation surfaces

Create `src/app/(operator)/experiments/[experimentId]/campaigns/[campaignId]/versions/[campaignVersion]/page.tsx`, its `loading.tsx`/`error.tsx`, `src/features/campaigns/components/{campaign-header,campaign-authority-summary,campaign-member-table,campaign-member-cards,campaign-controls,suppression-banner,create-campaign-dialog}.tsx`, `src/features/campaigns/hooks/{use-campaign-version,use-create-campaign-version,use-campaign-command}.ts`, exhaustive enum formatters, and matching unit/browser tests.

### Exact state and record presentation

Render canonical `CampaignState` exactly: `DRAFT`, `READY`, `ACTIVE`, `PAUSED`, `COMPLETED`, `CANCELLED`, `FAILED`. `COMPLETED/CANCELLED/FAILED` are terminal for that version. Render canonical `LeadState`: `DISCOVERED`, `RESEARCH_PENDING`, `RESEARCHED`, `QUALIFICATION_PENDING`, `QUALIFIED`, `DISQUALIFIED`, `SUPPRESSED`, `ARCHIVED`. Render canonical `MessageState`: `DRAFT`, `APPROVAL_PENDING`, `APPROVED`, `SEND_INTENT_RECORDED`, `QUEUED`, `SENDING`, `AMBIGUOUS`, `RECONCILING`, `SENT`, `FAILED_RETRYABLE`, `FAILED_PERMANENT`, `SUPPRESSED`, `CANCELLED`.

The campaign header displays returned campaign ID/version, experiment/offer/policy refs, state, immutable caps/window/mailbox refs, server UTC times, and correlation/version facts actually present in the generated resource. The member table/card alternative displays only generated safe internal IDs/hashes and state/status/reason fields; never derive “eligible” from a qualified lead. `QUALIFIED` is advisory gate output, `READY` is campaign preparation, `ACTIVE` only admits possible intents, and every actual send still requires approval, final current SEND policy, controls, budget/rate, mailbox, and gateway authority.

Suppression banners use returned `SUPPRESSED` lead/message/member facts and current report warnings. They never infer a suppression match from an address/domain in the browser. Identity `CONFLICT`/quarantine remains distinct from disqualification and is never auto-merged. A member/message in `AMBIGUOUS` or `RECONCILING` remains prominent and links to `/recovery`; campaign cancellation cannot overwrite it.

### Exact operations, request/response, and cache behavior

| Action | Contract | Client policy |
| --- | --- | --- |
| create version | `POST /api/v1/experiments/{experiment_id}/campaigns`, `createCampaignVersion`, `CreateCampaignVersionRequestV1 ->` generated resource, 201 + `Location` | mutation `['experiment',experimentId,'campaign','create']`; one key; no optimistic row; invalidate experiment/overview/timeline and navigate to returned `(campaign_id,campaign_version)` |
| read version | `GET /api/v1/campaigns/{campaign_id}/versions/{campaign_version}`, `getCampaignVersion` | query `['campaign',campaignId,campaignVersion]`; 5 seconds active, 15 paused/draft/ready, stop terminal; focus refetch |
| activate | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/activate`, `activateCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `['campaign',id,version,'activate']`; request contains exact generated `expected_state`; idempotency; no ETag invented; invalidate campaign/experiment/overview/timeline/recovery; poll authoritative state |
| pause | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/pause`, `pauseCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `["campaign",id,version,"pause"]`; same expected-state/idempotency/invalidation policy; display accepted versus admission/dequeue acknowledgement; no optimistic `PAUSED` |
| resume | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/resume`, `resumeCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `["campaign",id,version,"resume"]`; same policy; re-confirm current authority warnings; server rechecks every guard; no cached allow |
| cancel | `POST /api/v1/campaigns/{campaign_id}/versions/{campaign_version}/commands/cancel`, `cancelCampaign`, `CampaignControlRequestV1 -> CommandReceiptV1`, 202 | mutation `["campaign",id,version,"cancel"]`; same policy plus destructive typed confirmation; server may remain active/paused while provider work drains; never render terminal until refetch |

`CampaignControlRequestV1` is the only request-field authority; the UI sends its generated `schema_version`, exact `expected_state`, and generated reason fields, and adds the required `Idempotency-Key`. Campaign version is the positive path value, not a mutable ETag. `CommandReceiptV1` fields are rendered as defined in FRONTEND-01.

The campaign page has no operation for `ReadyCampaign`; it may display server-returned `READY` but cannot create it. It has no lead pagination contract independent of `getCampaignVersion`; if the generated campaign resource does not carry bounded member rows or links, the lead/member table is blocked. It has no suppression command. These are backend-contract gaps, not permission to build Next.js routes.

### Interaction, confirmation, and screen states

Create-version review shows exact experiment and source refs, member selection/caps included by the generated request, authority level, and no-send warning. Activate/resume dialogs show current campaign state/version, experiment state, M1/M6/product control facts, mailbox, approval summary, suppression/conflict/ambiguity warnings, budget/rate/cap facts returned by server, and state clearly that the server may deny. Pause explains that new admissions/dequeues stop but in-flight/possibly-called sends must resolve. Cancel requires typing the final eight campaign-ID characters and entering the generated reason; it is terminal for the version, cancels only legally unsent work, and cannot recall mail.

Pending blocks duplicate pointer/Enter/Space activation and returns focus after completion/error. Loading preserves table headings. Empty members means the returned version has none; it is not eligibility. Stale disables activate/resume/cancel until refetch when expected state may differ. Partial embedded data is labeled only if the schema provides `complete/warnings`; otherwise omission is an error/blocked feature. Redacted cells use explicit text. Terminal campaign versions are read-only and retain message/recovery links.

The desktop table is inside a labeled, keyboard-focusable bounded horizontal-scroll region only when columns cannot collapse; the page itself never overflows. At 767px and below, the table switches to ordered member cards with identical fields/actions. Filters are client presentation over the currently returned bounded page only unless a generated server filter exists.

## Ordered implementation tasks

- [ ] **Implement immutable version creation/read —** Input: generated create/read types. Operation: confirm one request/key, navigate by returned ID/version, and render exact resource without writable copies. Output: campaign detail. Test evidence: replay/Location/version/unknown-field fixtures. Failure behavior: no guessed version or local campaign row.
- [ ] **Render exhaustive lead/member/message safety states —** Input: embedded generated resource. Operation: map all canonical enums, suppression/conflict/ambiguity, and safe deep links with table/card parity. Output: bounded management view. Test evidence: every-state, redacted, empty, responsive, and unknown-enum tests. Failure behavior: affected action disabled.
- [ ] **Implement four campaign controls —** Input: current expected state and generated reason fields. Operation: confirm, submit with one key, render 202 receipt, invalidate/poll, and distinguish draining from terminal. Output: server-reconciled transition. Test evidence: stale state, double-submit, signal delay, ambiguity, cancel-drain matrices. Failure behavior: keep conservative prior/requested state and link recovery.
- [ ] **Enforce API gaps and authority —** Input: BACKEND-02 manifest. Operation: assert no lead/suppression/ready mutation, local qualification, auto-merge, or derived eligibility. Output: exact v1 surface. Test evidence: network/AST operation allowlist. Failure behavior: block unsupported controls and record backend need.

## Test strategy

- **Contract `test_campaign_feature_calls_only_six_backend02_campaign_operations`:** create/read/four controls.
- **States `test_campaign_lead_message_states_are_exhaustive_and_non_color`:** unknown blocks.
- **Suppression `test_suppressed_member_never_renders_as_sendable_despite_qualification_or_approval`:** no derived allow.
- **Ambiguity `test_cancel_drain_keeps_ambiguous_reconciling_visible_and_nonterminal`:** no false cancel.
- **Idempotency `test_campaign_command_double_activation_has_one_key_and_one_receipt`:** exact replay.
- **Responsive `test_member_table_card_parity_and_no_page_overflow_at_320_768_1280`:** keyboard scroll region.

## Security, privacy, compliance, idempotency, observability, and cost

List safe internal IDs/hashes and server-provided business display fields only; never expose decrypted recipient address, message body, source capture, provider account text, or suppression key. Client filters do not enter telemetry. Safe telemetry contains operation, safe campaign/version/member/message IDs, returned state, status, duration, and correlation. Costs/caps are server facts; the client neither reserves nor converts.

## Failure, rollback, and operator recovery

On stale expected state, refetch and require a new confirmation. On a 202 command whose state does not converge, keep admission assumptions closed and link correlation/resource to `/recovery`. On identity conflict or unknown suppression, remove authority actions for that row. On UI rollback, keep server campaign/version/event records. Resolve ambiguity/incident only through FRONTEND-09 typed commands.

## Acceptance and retained evidence

- [ ] Campaign version identity is immutable and every action uses exact path version plus generated expected state.
- [ ] Qualification, readiness, active state, approval, controls, and final SEND are never collapsed.
- [ ] Suppression, identity conflict, ambiguity, reconciliation, failure, and terminal states are explicit.
- [ ] No lead, suppression, ready, or generic CRUD endpoint is invented.
- [ ] Destructive confirmation, pending protection, focus, table/card parity, and bounded scroll pass.

Retain generated wire fixtures, network allowlist, state/command/replay traces, cancel-drain evidence, privacy scan, axe/keyboard output, and responsive screenshots.

## Dependencies and next deliverable

FRONTEND-05 consumes M5/M6 server projections. Exact messages and approvals link to [FRONTEND-06](06-approval-inbox.md) and [FRONTEND-07](07-message-and-reply-timeline.md). Generic lead/suppression management remains blocked until a reviewed BACKEND-02 revision.
