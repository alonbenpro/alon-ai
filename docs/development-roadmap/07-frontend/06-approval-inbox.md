# Approval Inbox

**Document ID:** FRONTEND-06
**Status:** Planned M7 authority review; no approval routes, records, or UI exist today
**Milestone:** M7 after M6 gateway/control evidence; bounded real recipients remain M9-gated
**Owner:** Solo operator
**Prerequisites:** [BACKEND-03 approval basis](../06-backend/03-policy-engine.md), [BACKEND-05 approval lifecycle](../06-backend/05-approval-and-command-handling.md#exact-approval-authority-and-lifecycle), [BACKEND-02](../06-backend/02-api-contracts.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), and [FRONTEND-04](04-evidence-and-agent-artifacts.md)
**Outputs:** Exact pending queue, immutable-scope review, approve/deny/revoke controls, eligibility-versus-SEND explanation, and stale-authority blocking
**Unlocks:** One exact approval can later be consumed by `RecordSendIntent`; it does not itself send
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

The operator can review one immutable approval scope, see whether its original eligibility and current authority facts remain valid, and approve, deny, or revoke it with exact reason and expected-state semantics. The screen makes the crucial distinction unavoidable: `APPROVAL_ELIGIBILITY` allows creation/decision of a bounded approval; the later fresh final `SEND` policy is a new server decision over current mutable facts, and only `SendGateway` may call Gmail.

## Current repository state

There is no product approval table/service/API/authentication or UI. No current code can request, approve, consume, or send a product message. BACKEND-02 plans approval list/detail/three decisions plus message approval request and send-intent commands; all are missing today.

## Scope and non-goals

In scope: pending/terminal queues, exact basis, eligibility and current-authority validity, expiry/cap, artifact references, message/mailbox/campaign/member linkage, approve/deny/revoke confirmations, stale/revoked reasons, and message handoff. Non-goals: blanket campaign approval, mutable content approval, bulk approve, auto-approval, approval editing, local policy evaluation, final SEND decision, provider call, or displaying decrypted address/body.

## Exact planned implementation surfaces

Create `src/app/(operator)/approvals/page.tsx`, `src/app/(operator)/approvals/[approvalId]/page.tsx`, route-local `loading.tsx`/`error.tsx`, `src/features/approvals/components/{approval-queue,approval-card,approval-table,approval-scope,authority-validity,approval-decision-dialog,approval-state}.tsx`, `src/features/approvals/hooks/{use-approvals,use-approval,use-approval-report,use-approval-command}.ts`, exact enum formatters, and matching unit/browser tests. Pages provide shell/landmarks; panels are generated-client Client Components.

### Exact approval scope and state

Render exact `ApprovalState`: `PENDING`, `APPROVED`, `DENIED`, `EXPIRED`, `REVOKED`, `CONSUMED`. Only `PENDING` may be approved/denied; only `APPROVED` may be revoked; `CONSUMED` identifies the unique intent and is not revocable. Unknown state disables actions.

The detail view must show every safe field from strict `ApprovalBasisScopeV1`:

- experiment ID;
- campaign ID and immutable campaign version;
- `campaign_member_id` and lead ID;
- message ID, message version, and content hash;
- mailbox ID and provider-account hash;
- sorted artifact ID/version/hash references;
- intended operation exactly `SEND`;
- `max_send_count=1`;
- approval expiry;
- immutable `scope_hash`; exact accepted recipient-identity, jurisdiction, affirmative-consent-or-counsel-exception, legal-review, disclosure/sender-template, and Google-policy artifact ID/version/hash references plus legal-policy version; eligibility policy decision ID/version/facts hash/allowed result; approval ID/state; request/decision/revocation timestamps; and returned safe reason fields.

The queue report adds current `current_authority_valid` and server invalidation reason codes from current suppression/control/policy facts. It renders recipient identity/jurisdiction status, consent-or-exception and legal-review expiry, legal-policy/template/Google-review version/status, and reply/unsubscribe/hard-bounce/complaint/soft-bounce-limit observations only from the safe BACKEND-06 projection. Each failure uses the dedicated BACKEND-03 code; generic “jurisdiction,” “authority,” or “suppressed” copy cannot replace it. Changed immutable basis requires a new approval UUID. Changed mutable facts do not rewrite the row but can invalidate current send authority. The browser never compares hashes or recomputes validity.

### Exact operations, keys, polling, and reconciliation

| Surface/action | Contract | Behavior |
| --- | --- | --- |
| queue | `GET /api/v1/approvals`, `listApprovals`; state/cursor/limit ordered `(requested_at,approval_id)` | `['approvals',{state,cursor,limit}]`; pending page polls 10 seconds and refetches on focus; terminal pages 60 seconds |
| authority queue report | `GET /api/v1/reports/approvals`, `getApprovalQueueReport`; paged projection | `['report','approvals',{cursor,limit}]`; no cache persistence; snapshot expiry restarts page one |
| detail | `GET /api/v1/approvals/{approval_id}`, `getApproval` | `['approval',approvalId]`; 5 seconds while pending/approved, stop terminal/consumed; focus refetch |
| approve | `POST /api/v1/approvals/{approval_id}/commands/approve`, `approveApproval`, `DecideApprovalRequestV1 -> CommandReceiptV1` | `['approval',id,'approve']`; generated `schema_version`, `expected_state`, mandatory safe reason code; one key; no ETag invented; no optimistic state |
| deny | `POST /api/v1/approvals/{approval_id}/commands/deny`, `denyApproval`, `DecideApprovalRequestV1 -> CommandReceiptV1` | `['approval',id,'deny']`; destructive consequence for message; same expected-state/key/reconciliation policy |
| revoke | `POST /api/v1/approvals/{approval_id}/commands/revoke`, `revokeApproval`, `RevokeApprovalRequestV1 -> CommandReceiptV1` | `['approval',id,'revoke']`; exact expected state and generated reason; no optimistic state |
| request from message | `POST /api/v1/messages/{message_id}/commands/request-approval`, `requestMessageApproval`, `RequestApprovalRequestV1 -> ApprovalResponseV1` | owned by FRONTEND-07; invalidates both approval queries/report, message, campaign, experiment timeline |
| record intent | `POST /api/v1/messages/{message_id}/commands/record-send-intent`, `recordMessageSendIntent`, `RecordSendIntentRequestV1 -> CommandReceiptV1` | owned by FRONTEND-07; consumes an exact approved row atomically; never a hidden side effect of approve |

Successful approve/deny/revoke invalidates `['approval',id]`, all `['approvals',…]`, `['report','approvals',…]`, linked message/campaign/experiment timeline and recovery keys, then refetches. A 200 receipt proves the command committed. It does not prove a send intent or provider call. Same request/key replay renders the stored result; changed reason/expected state uses a new key only after fresh confirmation.

### Review, confirmation, and screen states

Queue rows/cards use age and expiry text/icon/pattern, never color alone. Filters use exact states. Each row exposes only “Review,” never inline approve. Detail places `ApprovalScope` before actions and includes an expandable “Why this is not SEND authority” deterministic explanation. Artifact refs link only where FRONTEND-04 has a valid generated target; otherwise they remain copyable safe refs. Before approve opens, each referenced artifact is refetched with `getArtifact` and the returned ID/version/hash/status is shown beside the immutable basis. Any missing, rejected, superseded, hash/version-mismatched, or stale reference blocks the dialog and defers to server `current_authority_valid`/reason codes; the browser never computes acceptance.

Approve dialog repeats campaign member/mailbox/message/content/policy basis, expiry and cap, `current_authority_valid`, invalidation warnings, and asks the operator to check “I reviewed this exact immutable scope.” It captures the exact generated reason code (example server contract `OPERATOR_REVIEWED_EXACT_SCOPE`), not arbitrary content. Deny requires consequence acknowledgement. Revoke requires typing the last eight approval-ID characters and explains that a consumed approval cannot be revoked and mail cannot be recalled.

Dialog initial focus is the heading; tab is trapped; Escape/close is unavailable while pending; focus returns to invoking review action. Pending disables every decision control and announces `role=status`. On 409 state/basis/expiry conflict, refetch and focus an error summary describing the returned safe reason. On expiry during review, actions disappear after refetch. Stale report or `current_authority_valid=false` disables approve in the UI as a guardrail but the server remains the authority. Loading preserves scope labels; empty pending queue says “No approvals await review”; partial report lists warnings; redacted fields state why; all terminal states are read-only.

## Ordered implementation tasks

- [ ] **Implement queue/detail projections —** Input: generated approval page/detail/report types. Operation: render exact state, age/expiry, scope, eligibility/current validity, reason, and artifact refs with snapshot pagination. Output: reviewable queue. Test evidence: every-state/expiry/redaction/partial/snapshot fixtures. Failure behavior: no decision action when detail or authority projection is unavailable.
- [ ] **Implement approve and deny —** Input: fresh exact scope, refetched artifact versions/hashes/statuses, generated expected state/reason, operator confirmation. Operation: create one key, submit once, render receipt, invalidate/refetch linked resources. Output: server-owned state. Test evidence: double-decision race, stale basis, expiry, hash conflict, timeout replay. Failure behavior: remain/refetch and never create intent.
- [ ] **Implement revoke and consumption visibility —** Input: approved/consumed detail. Operation: destructive revoke confirmation or read-only consumed-intent linkage. Output: accurate lifecycle. Test evidence: revoke race, already consumed, already revoked, and focus-return tests. Failure behavior: preserve original approval/evidence.
- [ ] **Prove eligibility/final-SEND separation —** Input: UI/network/state graph. Operation: verify approve makes no `recordMessageSendIntent` or provider call and mutable denials remain visible. Output: bounded authority UX. Test evidence: network allowlist, suppression/control change, approval-consumption/final-denial E2E. Failure behavior: M7/M9 approval release blocked.

## Test strategy

- **Scope `test_approval_detail_displays_campaign_member_mailbox_message_content_policy_expiry_cap_and_hash_refs`:** no omitted authority field.
- **Lifecycle `test_only_pending_decides_approved_revokes_and_consumed_is_readonly`:** exhaustive state matrix.
- **Race `test_two_tabs_deciding_same_approval_have_one_winner_and_loser_refetches`:** expected state/idempotency.
- **Authority `test_approve_never_records_intent_or_renders_send_complete`:** final SEND remains separate.
- **Staleness `test_changed_basis_artifact_version_hash_acceptance_or_current_authority_invalid_disables_and_server_denies`:** all 14 dedicated compliance/signal denial fixtures render distinct reason copy and safe evidence refs; generic substitutions fail.
- **Accessibility `test_queue_cards_table_dialog_error_summary_and_focus_are_keyboard_complete`:** axe/breakpoints.

## Security, privacy, compliance, idempotency, observability, and cost

Approval views use IDs/hashes and response-safe metadata, not address, subject/body, decrypted artifact content, raw eligibility facts, credentials, or provider text. Clipboard actions are limited to safe IDs/hashes. Telemetry records operation, state, age bucket, validity boolean, safe reason codes, status, duration, approval/correlation IDs; never reason free text or content. Approval grants no legal-compliance guarantee, spend reservation, rate slot, or provider authority.

## Failure, rollback, and operator recovery

On basis/version/state/expiry conflict, discard the decision draft, refetch, and require a new review. On unknown outcome, exact replay uses the retained request/key. On privacy/schema error, hide actions and link correlation to Recovery. Frontend rollback removes the queue without altering approvals. Never change approval rows, hashes, expiry, or state through console/SQL.

## Acceptance and retained evidence

- [ ] Exact scope includes member/mailbox/message/content/policy/artifact basis, expiry, cap, and eligibility/current-validity facts.
- [ ] Approve, deny, and revoke use exact operation IDs/generated requests/expected states/keys and server-result reconciliation.
- [ ] Approval eligibility, approval decision, intent consumption, and final SEND are visually and behaviorally separate.
- [ ] Suppression/stale/revoked/expired/consumed reasons remain visible and no bulk approval exists.
- [ ] Queue/detail loading/empty/stale/error/partial/redacted/terminal and keyboard/focus behavior pass.

Retain scope screenshots/fixtures, operation traces, concurrency/replay evidence, final-SEND separation network proof, privacy scan, and axe/keyboard reports.

## Dependencies and next deliverable

FRONTEND-06 consumes FRONTEND-04 references and BACKEND-05 approval authority. An approved exact row unlocks only the explicit [FRONTEND-07 message intent flow](07-message-and-reply-timeline.md), where the server may still deny or later fail final SEND.
