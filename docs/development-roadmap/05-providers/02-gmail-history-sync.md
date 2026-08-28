# Gmail History Sync, Sent Reconciliation, and Cursor Recovery

**Document ID:** PROVIDER-02
**Status:** Planned M6 read integration; no Gmail read, cursor, reconciliation, or reply sync exists today
**Milestone:** M6
**Owner:** Solo operator
**Prerequisites:** [PROVIDER-01](01-gmail-oauth-and-adapter.md), [DB-03](../02-database/03-leads-campaigns-and-messages.md), [ARCH-03](../01-architecture/03-domain-events-and-state-machines.md), and [WF-05](../03-workflows/05-outreach-and-reply-workflow.md)
**Outputs:** Read-only Gmail port, mailbox-bound Sent reconciliation, atomic history paging, stale-cursor full sync, and reply observation recovery
**Unlocks:** M6 send/reconcile/reply evidence and [BACKEND-04](../06-backend/04-send-gateway.md) recovery completion
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

Every possibly accepted Gmail send becomes either proven sent, conclusively absent after a bounded window, or an operator-visible conflict. Separately, every Gmail history page records its observations/replies/events before advancing the mailbox cursor. Read recovery never gains send authority: `GmailMailboxReadProvider` is a separate port from PROVIDER-01 `GmailProvider`, and only `SendGateway` can receive the latter.

## Current repository state

No read provider, Sent search, `provider_observations`, `replies`, `gmail_history_cursors`, cursor worker, full sync, or classification handoff exists. The minimal provider protocol can send only in interface shape and has no implementation. All behavior here is planned and remains disabled until M6.

## Scope and non-goals

In scope: message listing/get, Sent candidate verification, incremental history pages, full-sync recovery after expired cursor, MIME sanitization/NFC normalization, reply identity, transactional cursor movement, typed read errors, fixtures, and bounded scheduling. Non-goals: Inbox UI parity, modifying labels, deleting mail, contacts, auto-response, inferring delivery/read, cross-mailbox evidence, cursor advancement on partial success, or treating Gmail history as aggregate truth.

## Exact planned implementation surfaces

Create `providers/gmail/read_contracts.py`, `providers/gmail/history_adapter.py`, `application/gmail_reconciliation.py`, `application/gmail_sync.py`, provider fixtures, and finite workflows `workflows/gmail_reconciliation.py` and `workflows/gmail_history_sync.py`. Exact sole writers remain DB-03: `GmailResultCaptureService` -> `provider_results`; `GmailObservationService` -> `provider_observations`; `GmailReplySyncService` -> `replies`; `GmailHistorySyncService` -> `gmail_history_cursors`; `SendRecoveryService` owns only the documented attempt/message recovery transitions.

### Read-only provider protocol

| Method | Strict request | Strict result and limit |
| --- | --- | --- |
| `find_sent_candidates` | `gmail.sent_search.request.v1`: call/mailbox IDs, exact `rfc_message_id`, UTC lower/upper bounds, `timeout_ms=1..20_000` | `gmail.sent_search.result.v1`: ordered tuple of at most 20 `SentCandidateV1`; default 8s. Query is `in:sent rfc822msgid:{rfc_message_id}` using `messages.list`, then `messages.get(format=METADATA)` for `Message-ID`, `From`, `To`, `Date`; all candidates retain the authorized `mailbox_id`. |
| `list_history_page` | `gmail.history_page.request.v1`: call/mailbox IDs, exact `start_history_id`, optional page token, `max_results=1..500`, history types, `timeout_ms=1..20_000` | `gmail.history_page.result.v1`: chronological history records, optional next token, returned current history ID; default 10s. |
| `get_message_capture` | `gmail.message_capture.request.v1`: call/mailbox/message IDs, allowed format/header/body policy, `max_bytes=1..5_000_000`, `timeout_ms=1..20_000` | `gmail.message_capture.result.v1`: message/thread/history IDs, direction, selected header hashes, sanitized body capture ref/hash/MIME/language, observed time; default 10s. |
| `get_profile_cursor` | `gmail.profile_cursor.request.v1`: call/mailbox IDs, `timeout_ms=1..10_000` | verified provider-account hash plus current history ID; default 5s. |

Every result is strict/frozen/extra-forbid and carries call ID, provider request ID when supplied, started/finished UTC, Gmail error code or success, response fingerprint, and no credential. `SentCandidateV1` is exactly `{mailbox_id,gmail_message_id,gmail_thread_id,rfc_message_id,observed_at,envelope_fingerprint,header_hash}` and sorts by raw UTF-8 `(gmail_message_id,gmail_thread_id,rfc_message_id)`. Gmail API message search accepts Gmail search syntax, including an `rfc822msgid` query, but API search behavior differs from the UI: [search/filter guide](https://developers.google.com/workspace/gmail/api/guides/filtering) and [messages list](https://developers.google.com/workspace/gmail/api/guides/list-messages). Message metadata is fetched by ID: [messages.get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get).

Provider text is untrusted. Decode MIME with a size/depth/part-count allowlist; reject active content and zip bombs; normalize extracted subject/body/source strings to Unicode NFC. Any provider byte span is converted before typed construction to zero-based, half-open Unicode code-point indexes over the exact NFC string. Decomposed accents, Hebrew, emoji, invalid UTF-8, surrogate, and split-multibyte fixtures are mandatory. No byte offset may reach `ReplyClassificationV1`.

### Exact ambiguous-send reconciliation

1. `SendRecoveryService` loads the complete immutable DB-03 experiment/campaign-version/lead/message/mailbox/approval/policy/scope/facts/RFC tuple and verifies the attempt composite FK identity. Any mismatch becomes conflict without a provider query.
2. It commits `AMBIGUOUS -> RECONCILING`, attempt `RECONCILING`, strategy literal `gmail.sent-rfc822.v1`, and `send.reconciliation_started.v1` with attempt/mailbox/RFC identity.
3. The read adapter searches only credentials bound to `send_intents.mailbox_id`. It records every candidate as restricted provider evidence; evidence from another mailbox is rejected even if headers match.
4. Exactly one candidate whose `Message-ID` byte-equals the stable RFC ID and whose safe envelope hashes match permits `provider_results(outcome='RECONCILED_SENT')`, attempt/message `SENT`, and only `send.reconciled_as_sent.v1`.
5. Zero candidates is not immediately conclusive. Initial M6 schedule is elapsed seconds `0, 5, 15, 30, 60, 120, 300`; each poll is a successful complete mailbox query. Only the successful 300-second poll with at least two prior successful zero-result polls after the uncertainty began may capture `RECONCILED_ABSENT` and allow `FAILED_RETRYABLE` evaluation.
6. More than one match, malformed identity, query incompleteness, credential/account change, or candidate disagreement captures `CONFLICT`, moves to `FAILED_PERMANENT` only through deterministic recovery, disables dequeue for that mailbox, opens an incident, and requires an audited operator command. Absence-window expiry with unsuccessful polls remains unresolved; it is not absence.

Direct provider success never enters this algorithm and emits `send.provider_accepted.v1`, not the reconciliation event. `AMBIGUOUS` never transitions directly to `QUEUED`.

### Atomic incremental history and stale-cursor recovery

Gmail history is chronological but IDs have gaps. `startHistoryId` may expire and typically returns HTTP 404; Google requires a full sync, and a returned page without `nextPageToken` supplies the new history ID: [users.history.list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list).

For every incremental page, `GmailHistorySyncService` locks `gmail_history_cursors(mailbox_id)`, verifies expected version/history ID, deduplicates each observation on DB-03 mailbox composites, inserts replies, emits `reply.received.v1` where applicable, inserts the page's `gmail.history_cursor_advanced.v1`, and updates the cursor in one PostgreSQL transaction. A crash rolls back all page writes and the same page is fetched again. Classification runs afterward through AGENT-08 and cannot affect cursor success.

On first connect or 404:

1. keep the old cursor and record safe degraded audit/incident evidence;
2. obtain a verified profile history ID `H0`;
3. enumerate relevant messages over the policy-versioned bounded sync horizon using finite pages, capture/dedupe observations and replies without moving the product cursor;
4. replay `history.list(startHistoryId=H0)` to close changes racing with enumeration;
5. in the final transaction, verify account/cursor ownership, commit remaining observations/events, and install the returned history ID with incremented version;
6. if any page is incomplete, token/account changes, or limits expire, retain the prior cursor/degraded state and restart the same idempotent recovery. Never guess a cursor from max message history IDs.

Initial M6 horizon is 30 days and maximum 500 messages per finite recovery run; exceeding either yields operator-visible `HISTORY_FULL_SYNC_LIMIT_EXCEEDED` and another bounded run, never silent truncation.

### Error, retry, fixtures, telemetry, and replacement

Read errors reuse PROVIDER-01 `GmailErrorCode` plus exact recovery codes `HISTORY_CURSOR_EXPIRED`, `HISTORY_PAGE_INVALID`, `HISTORY_FULL_SYNC_LIMIT_EXCEEDED`, `SENT_CANDIDATE_CONFLICT`, and `MIME_CAPTURE_INVALID`. Authentication/account mismatch is nonretryable and disables the mailbox. HTTP 429/parsed transient 403 and 5xx or transport failure on these read-only calls may retry at most three total attempts with full jitter and provider retry hints, within the request deadline and workflow budget. HTTP 404 for `history.list` is cursor recovery, not retry. Cancellation is checked before/after every page/capture and before transaction commit.

`LIVE_CAPTURE` uses the read-only Gmail API and writes sanitized capture refs through sole-writer services. `RECORDED_FIXTURE` accepts signed strict `gmail.read.fixture.v1` pages/candidates/captures and has no network/credential. Fixtures cover duplicate/out-of-order history, 404, empty pages with a final history ID, cross-mailbox candidates, multiple Sent matches, delayed indexing, malformed MIME, NFC/byte-offset conversion, cancellation, and every crash boundary. Replacement providers must preserve mailbox/RFC semantics and exact result/error/fixture shapes; a provider without message-ID search and stable account scope is ineligible.

Telemetry contains mailbox/call/run/request IDs, page/candidate counts, safe history IDs or hashes, cursor versions, durations, status/error, ambiguity age, and fingerprints. It excludes tokens, addresses, bodies, subjects, snippets, raw headers, and provider error text.

## Ordered implementation tasks

- [ ] **Implement strict read adapter —** Input: mailbox-bound credentials and requests above. Operation: implement list/get/profile/history calls, bounds, MIME sanitizer, NFC and byte-to-code-point conversion, typed errors, cancellation, and read-only retries. Output: strict provider results. Test evidence: `test_gmail_read_contract_error_timeout_nfc_and_size_matrix`. Failure behavior: no product mutation; disable on account mismatch.
- [ ] **Implement Sent reconciliation —** Input: exact DB-03 authority tuple and ambiguity. Operation: execute strategy/schedule, persist candidates/results, and delegate exact state/events. Output: sent, conclusively absent, or conflict. Test evidence: `test_sent_reconciliation_zero_one_many_cross_mailbox_and_delayed_index_matrix`. Failure behavior: never requeue unresolved ambiguity.
- [ ] **Implement atomic incremental pages —** Input: locked cursor and strict history page. Operation: dedupe observations/replies/events and advance cursor in one transaction. Output: replay-safe cursor. Test evidence: crash injection before/after every row/event/cursor write. Failure behavior: rollback entire page.
- [ ] **Implement 404 full-sync recovery —** Input: expired cursor, profile baseline, bounded horizon. Operation: enumerate, replay race history, and install new cursor only after completeness proof. Output: recovered cursor or visible degraded state. Test evidence: concurrent incoming message, pagination, cancellation, cap, and restart fixtures. Failure behavior: preserve prior cursor; no skipped message.
- [ ] **Gate M6 fixtures and operations —** Input: recorded/live owned-mailbox scenarios. Operation: prove zero-network fixture mode, source/secret scan, schedule bounds, and operator timeline. Output: retained M6 read/recovery evidence. Test evidence: fixture hashes and end-to-end reply/reconciliation traces. Failure behavior: M6 fails and both send controls remain false.

## Test strategy

- **Recovery `test_ambiguous_attempt_has_no_path_to_retry_before_conclusive_absence`:** exhaustive transition proof.
- **Atomicity `test_observation_reply_events_and_cursor_commit_as_one_page`:** real PostgreSQL crash matrix.
- **Identity `test_reply_cursor_and_candidate_require_same_mailbox_provider_identity`:** composite splice denial.
- **Unicode `test_provider_byte_offsets_convert_to_nfc_code_point_half_open_spans`:** accents/Hebrew/emoji.
- **Security `test_gmail_read_port_cannot_send_modify_labels_or_expose_content_in_telemetry`:** capability/call graph.
- **Recovery `test_expired_history_id_full_sync_closes_baseline_race`:** no gap around `H0`.

## Security, privacy, compliance, idempotency, observability, and cost

Read credentials stay in the provider boundary and inherit the exact mailbox/account binding. Captured bodies are `SENSITIVE_SHORT`; cursor/attempt/result minimum is `SAFETY_LONG`; ambiguity/incident holds override purge. Every page/candidate/capture has stable call/request/fingerprint evidence and application dedupe keys. Metrics alert on cursor age, 404 recovery, page lag, repeated MIME rejection, hidden ambiguity, conflict, and calls after disable. Gmail API has no direct per-call fee recorded here; operational usage remains measurable.

## Failure, rollback, and operator recovery

On cross-account evidence, cursor regression, hidden gap, multiple Sent matches, or corrupted capture: stop that mailbox's sync/dequeue, disable send controls when send safety is affected, open an incident, retain restricted evidence, and use typed reconcile/repair commands. Rollback code without rewriting cursor/observations. Restore into an isolated database if composite invariants fail; never fix the cursor with direct SQL.

## Acceptance and retained evidence

- [ ] Read-only services cannot reach Gmail send or leak credentials/content.
- [ ] Zero/one/many Sent outcomes and bounded absence are explicit and mailbox-bound.
- [ ] Direct and reconciled acceptance events remain semantically distinct.
- [ ] Every history page and full-sync recovery is atomic, replay-safe, and gap-aware.
- [ ] Provider offsets are NFC-normalized code-point spans before typed construction.

Retain read-contract schemas, error/retry matrix, candidate/history/MIME fixtures and hashes, atomicity/crash traces, 404 full-sync proof, call graph, secret/PII scan, cursor/ambiguity metrics, and official-source access date.

## Dependencies and next deliverable

PROVIDER-02 depends on PROVIDER-01 credentials and DB-03/ARCH-03 identity/state. It completes the provider half of [BACKEND-04 SendGateway](../06-backend/04-send-gateway.md) recovery and the M6 WF-05 gate; it grants no send authority itself.
