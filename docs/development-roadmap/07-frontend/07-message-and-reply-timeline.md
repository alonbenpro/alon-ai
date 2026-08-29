# Message and Reply Timeline

**Document ID:** FRONTEND-07
**Status:** Planned M6-M7 redacted message surface; no product messages, sends, replies, or route exist today
**Milestone:** M6 owned-inbox evidence, M7 operator diagnosis, M9 bounded product use only after gates
**Owner:** Solo operator
**Prerequisites:** [ARCH-03 message states/events](../01-architecture/03-domain-events-and-state-machines.md#campaign-and-message-state-machines), [WF-05](../03-workflows/05-outreach-and-reply-workflow.md), [BACKEND-04](../06-backend/04-send-gateway.md), [BACKEND-05](../06-backend/05-approval-and-command-handling.md), and [BACKEND-02](../06-backend/02-api-contracts.md)
**Outputs:** Redacted message/send/reply chronology, approval/intention controls, ambiguity quarantine, retry-abort control, and exact authoritative reconciliation
**Unlocks:** Diagnosis of one message without Gmail-console action or unsafe resend
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

At `/messages/[messageId]`, the operator can understand one immutable message’s campaign/member/mailbox/approval/policy lineage, request approval, explicitly record one send intent after approval, observe the gateway result/reconciliation/replies, and abort a conclusively retryable message. `AMBIGUOUS` and `RECONCILING` are first-class quarantine states with no resend button.

## Current repository state

The current repository has no product message/intent/attempt/result/observation/reply rows, Gmail adapter, approval, SendGateway, or product client. BACKEND-02 plans one redacted message resource and three message commands. The existing frontend has no message route.

## Scope and non-goals

In scope: safe message identity/version/hash, state, campaign/member/mailbox/approval/intent/attempt/policy/provider/reply references returned by the resource, exact chronology, request approval, record intent, abort retry, and recovery links. Non-goals: composing/editing plaintext, rendering decrypted body/recipient, direct Gmail send/retry/search, reply writing, manual provider-result override, local delivery inference, or raw provider payloads.

## Exact planned implementation surfaces

Create `src/app/(operator)/messages/[messageId]/page.tsx`, its `loading.tsx`/`error.tsx`, `src/features/messages/components/{message-header,message-authority-chain,message-timeline,message-timeline-item,approval-request-dialog,send-intent-dialog,abort-retry-dialog,ambiguity-callout,reply-summary}.tsx`, `src/features/messages/hooks/{use-message,use-message-command}.ts`, enum/event formatters, and matching unit/browser tests. The page shell is server-rendered; authenticated query/command panels are client-rendered.

### Exact message states, authority chain, and events

Render exact `MessageState`: `DRAFT`, `APPROVAL_PENDING`, `APPROVED`, `SEND_INTENT_RECORDED`, `QUEUED`, `SENDING`, `AMBIGUOUS`, `RECONCILING`, `SENT`, `FAILED_RETRYABLE`, `FAILED_PERMANENT`, `SUPPRESSED`, `CANCELLED`. `SENT`, `FAILED_PERMANENT`, `SUPPRESSED`, and `CANCELLED` are terminal. `AMBIGUOUS` cannot transition directly to `QUEUED`; timeout/connection loss/worker death/missing local commit never becomes conclusive failure in the UI.

The authority chain renders only safe generated fields and makes each layer distinct:

`experiment -> campaign/version -> campaign_member -> lead -> message/version/content_hash -> mailbox/provider-account hash -> eligibility decision/basis -> approval -> send intent/RFC identity -> fresh final SEND decision/facts -> numbered attempt/rate lease -> provider result/observation -> reply/classification`.

The timeline uses server order and exact canonical events when returned: `approval.requested.v1`, `approval.decided.v1`, `approval.revoked.v1`, `send.intent_recorded.v1`, `send.queued.v1`, `send.attempt_started.v1`, `send.provider_accepted.v1`, `send.outcome_ambiguous.v1`, `send.reconciliation_started.v1`, `send.reconciled_as_sent.v1`, `send.failed.v1`, `send.retry_scheduled.v1`, `send.retry_exhausted.v1`, `send.suppressed.v1`, `reply.received.v1`, `reply.classified.v1`, plus safe policy/control/audit records actually present. Direct acceptance and reconciled acceptance use different labels.

The nullable `final_send_compliance` block is server truth for the last evaluation. Render its exact identity/jurisdiction/authority-route statuses and evidence/retrieved/published/verified/effective/expiry times; consent-or-exception/legal-review decision and expiry; legal-policy current flag/version; disclosure/sender-template and Google-review ID/version/content hash/status/validator/effective/expiry; reply/unsubscribe/hard-bounce/complaint flags; soft-bounce count/limit/last-observed time; exact safe evidence artifact ID/version/hash tuples and observation references; and dedicated reason codes. Every one of `RECIPIENT_IDENTITY_UNVERIFIED`, `RECIPIENT_JURISDICTION_UNKNOWN`, `RECIPIENT_CONSENT_MISSING`, `RECIPIENT_CONSENT_EXPIRED`, `COUNSEL_EXCEPTION_MISSING`, `LEGAL_REVIEW_MISSING`, `LEGAL_REVIEW_STALE`, `DISCLOSURE_TEMPLATE_INVALID`, `GOOGLE_POLICY_DENIED`, `RECIPIENT_REPLIED`, `RECIPIENT_OPTED_OUT`, `RECIPIENT_HARD_BOUNCED`, `RECIPIENT_COMPLAINT`, and `RECIPIENT_SOFT_BOUNCE_LIMIT` has distinct generated copy and fixture. Before evaluation, render “Not yet evaluated,” not passing. Unknown/missing status or reason blocks authority actions; the UI never substitutes a generic jurisdiction/authority/suppression label.

Reply classification is advisory. Render primary label/action/confidence/evidence-span hashes only when returned and accepted; abstained/rejected/unaccepted classification does not become positive reply truth. The operator does not edit classification through an absent API.

### Exact operations, headers, query keys, and invalidation

| Surface/action | Contract | Client behavior |
| --- | --- | --- |
| message detail/timeline | `GET /api/v1/messages/{message_id}`, `getOutreachMessage`; redacted message/send/reply timeline resource | `['message',messageId]`; 3-second poll for `SENDING/AMBIGUOUS/RECONCILING`, 5 for other nonterminal, stop terminal; focus refetch |
| report context | `GET /api/v1/reports/experiments/{experiment_id}/timeline`, `getExperimentTimelineReport` when experiment ID is returned | `['report','experiment',experimentId,'timeline',{cursor,limit}]`; server snapshot/order only; link, do not splice into message resource truth |
| request approval | `POST /api/v1/messages/{message_id}/commands/request-approval`, `requestMessageApproval`, `RequestApprovalRequestV1 -> ApprovalResponseV1`, 201 | mutation `['message',id,'request-approval']`; one key + latest message `If-Match`; exact generated request fields; invalidate message/approval queues/report/campaign/timeline |
| record send intent | `POST /api/v1/messages/{message_id}/commands/record-send-intent`, `recordMessageSendIntent`, `RecordSendIntentRequestV1 -> CommandReceiptV1`, 202 | mutation `['message',id,'record-send-intent']`; one key + latest `If-Match`; consume approval/reserve/queue atomically only on server; invalidate message/approval/campaign/overview/recovery/timeline |
| abort retry | `POST /api/v1/messages/{message_id}/commands/abort-retry`, `abortMessageRetry`, `AbortSendRetryRequestV1 -> OutreachMessageResponseV1`, 200 | mutation `['message',id,'abort-retry']`; one key + latest `If-Match`; generated reason; invalidate message/recovery/campaign/timeline |

The message resource ETag/version is the only `If-Match` source. A request cannot reuse a version after refetch. Same frozen request/key may replay after unknown transport outcome. No mutation is optimistic. `requestMessageApproval` returning an approval does not approve it. `recordMessageSendIntent` returning 202 means the atomic intent/queue command committed; the UI then polls and does not claim Gmail was called or accepted. Final SEND policy is created later inside the gateway.

### Confirmation and state-specific actions

`DRAFT` may show Request approval only when all required generated scope references exist and `getArtifact` refetches each referenced artifact to the exact accepted version/hash/status in the proposed basis. Missing, stale, rejected, or superseded references block review; the client does not calculate acceptance. `APPROVAL_PENDING` links to the exact approval. `APPROVED` may show Record send intent after a fresh detail/refetch; the dialog repeats exact campaign/member/message/content/mailbox/approval scope, expiry/cap, current controls/suppression/budget/rate warnings returned by server, and states final SEND can still deny. Require typing `SEND` plus a scope-review checkbox. This is an authority action even though it still does not call Gmail.

`FAILED_RETRYABLE` shows Abort retry and server retry deadline/count/cap when returned. Abort requires typed last-eight message ID and generated reason; it yields `FAILED_PERMANENT` and cannot be undone. There is no manual RetrySend endpoint. `SENDING` has no cancel action. `AMBIGUOUS` and `RECONCILING` show a persistent high-severity non-color callout, immutable authorized mailbox, attempt/RFC/evidence refs, ambiguity age, and “Open Recovery”; never “Try send again.” `SENT/SUPPRESSED/CANCELLED/FAILED_PERMANENT` are read-only.

Dialogs follow heading-first focus, trap, pending no-close, focus return, Enter/Space double-submit protection, and live status. `409 AMBIGUOUS_SEND_REQUIRES_RECONCILIATION` replaces any attempted action with the quarantine callout. `412/409 VERSION_CONFLICT` refetches and requires re-confirmation. Loading preserves chronology geometry; empty replies say none observed at server `as_of`, not no reply forever; stale disables authority actions; redacted content is explicit; partial timeline is allowed only through documented report warnings; terminal state stops polling.

## Ordered implementation tasks

- [ ] **Render message authority and chronology —** Input: generated redacted resource and canonical events. Operation: show exact state/version/IDs/hashes, separate direct/reconciled outcomes, reply/classification semantics, and server UTC/Jerusalem presentation. Output: diagnosable timeline. Test evidence: every state/event/outcome/redaction fixture. Failure behavior: unsupported record blocks actions.
- [ ] **Implement approval request —** Input: latest message ETag, refetched accepted artifact versions/hashes, and generated scope request. Operation: review, submit one key, render returned approval, invalidate/refetch. Output: `APPROVAL_PENDING` server state. Test evidence: eligibility denial, stale basis, replay, and no-intent/provider-call tests. Failure behavior: remain draft and preserve denial reasons.
- [ ] **Implement send-intent authority action —** Input: exact approved message/approval snapshot. Operation: typed confirmation, submit one key + ETag, render 202 as queued-intent acceptance only, and poll. Output: server intent/queue state. Test evidence: approval consumed once, mutable final denial, double-submit, unknown outcome, no optimistic send. Failure behavior: no second intent and no client retry.
- [ ] **Implement ambiguity/recovery and retry abort —** Input: server attempt/reconciliation/retry facts. Operation: remove send actions, deep-link typed recovery, or confirm terminal abort. Output: no blind retry. Test evidence: timeout/crash/zero-one-many Sent matches, abort race/exhaustion, and cross-mailbox denial. Failure behavior: quarantine and both controls conservative.

## Test strategy

- **States `test_message_page_exhaustively_renders_all_fourteen_states`:** unknown blocks.
- **Authority `test_record_intent_confirmation_displays_full_scope_and_does_not_claim_final_send`:** gateway remains sole authority.
- **Compliance `test_all_fourteen_final_send_denials_render_distinct_safe_facts_reasons_and_evidence_refs`:** missing/unknown/generic mappings block actions.
- **Ambiguity `test_ambiguous_and_reconciling_have_no_send_or_retry_action`:** only recovery deep link.
- **Events `test_direct_provider_acceptance_and_reconciled_acceptance_are_never_interchanged`:** exact labels.
- **Concurrency `test_message_etag_conflict_refetches_and_requires_reconfirmation`:** no stale intent/abort.
- **Privacy `test_message_dom_url_logs_clipboard_exclude_address_subject_body_provider_payload`:** redacted schema.
- **Accessibility `test_timeline_list_dialogs_callouts_and_live_updates_are_keyboard_screenreader_complete`:** reduced motion.

## Security, privacy, compliance, idempotency, observability, and cost

The route uses safe internal IDs/hashes and redacted summaries only. No address, subject/body, MIME, OAuth data, raw provider error/result, evidence excerpt, or hidden reasoning enters DOM/URL/log/telemetry. Safe telemetry records operation, message/attempt state, attempt number, ambiguity age bucket, receipt/status/duration, safe IDs/hashes, and correlation. Original/server-converted costs may be linked from analytics; the message page does not compute them.

## Failure, rollback, and operator recovery

Unknown outcome retains exact request/key and refetches before exact replay. Any possible provider call becomes/stays ambiguous until the typed reconciliation operation resolves it. Cross-mailbox evidence, multiple matches, impossible state, or DB/provider disagreement disables message actions and opens Recovery. UI rollback cannot cancel or resend; backend rows/events/provider evidence remain authoritative.

## Acceptance and retained evidence

- [ ] Every message state and canonical direct/ambiguous/reconciled/retry/suppression/reply fact is distinct and server-sourced.
- [ ] Request approval, record intent, and abort retry use exact operation IDs/types/ETags/keys/confirmations/invalidations.
- [ ] Approval eligibility, consumed intent, fresh final SEND, provider call, acceptance, and reply are never conflated.
- [ ] `AMBIGUOUS/RECONCILING` have no resend/requeue action and retain mailbox-bound evidence.
- [ ] Loading/empty/stale/error/partial/redacted/terminal, focus/live regions, and reduced-motion behavior pass.

Retain typed/network fixtures, timeline snapshots, idempotency/ETag traces, ambiguity/reconciliation E2E, privacy scan, and accessibility evidence.

## Dependencies and next deliverable

FRONTEND-07 consumes [FRONTEND-06](06-approval-inbox.md). Ambiguous/incident outcomes route to [FRONTEND-09](09-error-recovery-and-accessibility.md); message/reply counts feed only server-owned [FRONTEND-08 reports](08-cost-funnel-and-decision-analytics.md).
