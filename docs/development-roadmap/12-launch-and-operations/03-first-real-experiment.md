# First Real Experiment

**Document ID:** LAUNCH-03
**Status:** Planned M9 bounded experiment; no real-recipient authority, legal evidence, public unsubscribe ingress, product Gmail implementation, deployment, or real send exists today
**Milestone:** M9
**Owner:** Solo operator; qualified legal counsel owns legal conclusions and the operator owns every recipient/message approval
**Prerequisites:** Passing M0-M8 including [LAUNCH-01](01-test-inbox-pilot.md) and [LAUNCH-02](02-controlled-internal-launch.md); [PRODUCT-02 decision rule](../00-product-strategy/02-success-metrics.md#first-real-experiment-decision-rule); [SEC-04 recipient authority](../08-security-and-compliance/04-outreach-compliance.md); [SEC-05 suppression/budgets](../08-security-and-compliance/05-suppression-budgets-and-kill-switch.md); exact M9 public-boundary evidence
**Outputs:** One pre-registered capped real experiment, recipient/message approval and delivery/suppression evidence, 14-day reply-window snapshot, cost/operator-time record, incident history, and operator `SCALE|REVISE|KILL|INCONCLUSIVE` decision
**Unlocks:** A separate reviewed next experiment or delivery-feasibility review; never automatic scaling, follow-up, cap increase, concurrent portfolio, or Gmail authority
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

The first real experiment is exactly one offer, one immutable campaign version, one mailbox, one configured jurisdiction/legal-policy/disclosure set, and at most ten recipients. Every recipient has recipient-specific affirmative-consent evidence. Every recipient may receive one manually approved initial message and zero automated follow-ups.

The demand window closes 14 days after the last reconciled delivery. Because this cap is smaller than PRODUCT-02's default 50 delivered recipients, the result is `INCONCLUSIVE` unless a stronger registered decision condition is actually met; the operator may not manufacture a validation claim from ten quiet inboxes. Safety failure stops the experiment regardless of demand.

## Current repository state

The repository sends nothing and lacks the planned product data/workflows/Gmail/provider/UI/deployment/public edge, counsel-approved policy, consent artifacts, recipient cohort, sender/disclosure template, suppression ingress, M8 evidence and M9 decision record. `ALON_AI_OUTREACH_ENABLED=false` plus foundation tests are not launch evidence. No current address or artifact is authorized for this phase.

## Scope and non-goals

In scope: one accepted offer and campaign version; one product-eligible mailbox; one recipient jurisdiction set; one current `CompliancePolicyV1`, `LegalReviewRecordV1`, `DisclosureSenderTemplateV1` and `GooglePolicyReviewV1`; one-to-ten consented recipients; individual artifact acceptance, approval, final-SEND evaluation and initial send; exact scanner-safe unsubscribe GET/explicit-POST publication; replies/bounces/complaints/opt-outs/suppression; cost/time/funnel evidence; 14-day decision window; and safe shutdown.

Non-goals: scraped, purchased, harvested, inferred, cold or unsolicited recipients; a counsel-exception route; more than one offer/campaign/mailbox/policy/jurisdiction set; follow-up; resend after ambiguity; automatic reply; recipient scoring as consent; cap expansion; concurrent experiment; agent Gmail/control/approval/legal authority; public signup/API/webhook; or a claim that ten recipients statistically validate a market.

## Exact planned implementation surfaces

This phase adds no endpoint, table, event, artifact, provider capability, service, metric, incident, command or DR name. It uses the canonical 46 tables, 66 operations (64 private plus exact public GET/POST), events/owners, six provider families, 39 metrics, 18 incident routes, 24 Task 7 commands, 14 final-SEND denials and `DR01..DR11`. The public operations are exactly `GET /api/v1/public/unsubscribe/{token}` (`getUnsubscribeConfirmation`, read-only) and explicit `POST /api/v1/public/unsubscribe/{token}` (`confirmUnsubscribe`, suppression mutation); no other public surface exists.

### Immutable entry manifest and gate closure

The signed entry record binds literal phase `FIRST_REAL_EXPERIMENT`, clean source/release/config/runtime/schema/OpenAPI/catalog hashes, M0-M8 gate IDs/hashes/freshness, `ReleaseManifestV1`, active `PromotionManifestV1` references, exact model/prompt/tool/provider versions, one `ExperimentBrief` and pre-registered decision-rule version, one offer ID/version/hash, one campaign ID/version/hash, one mailbox/account/credential generation, one jurisdiction/policy/legal-review/disclosure/Google-review tuple, one-to-ten opaque campaign-member IDs with exact accepted affirmative-consent artifact references, individual sensitive-preview/manual-approval requirement, 5/day and 10-total caps, budgets/reply window, expected control/route versions, public DNS/TLS/WAF/64+2 evidence, signed `retention.policy.v1` hash proving token `<=90 days`, verification/decryption overlap `>=97 days`, and backup sets `14 daily + 4 weekly` with no personal-data recovery point `>35 days`, latest restore/AWS witness/telemetry/incident evidence, operator signature, start and expiry UTC. It contains no address, recipient hash, token, content, legal text or credential.

| Necessary gate | Exact evidence | Why it is not sufficient alone |
| --- | --- | --- |
| M1 engineering | selected runtime passed every canonical row, or mandatory Temporal migration completed after any DBOS disqualifier | proves durable-runtime behavior only |
| M6 engineering | LAUNCH-01/M6 owned-alias Gmail, reconciliation, suppression, rate, control and audit gate current | test identities create no recipient/legal authority |
| M8 operations | LAUNCH-02 private release, current restore/AWS witness/telemetry/security/DR evidence and no blocking incident | infrastructure health grants no send |
| M9 recipient/legal | exact consent-only recipient cohort, confirmed jurisdiction, current counsel/legal/Google policy, sender/disclosure and immutable message/campaign authority | still requires individual approval and fresh final-SEND facts |
| M9 public boundary | exact 64-private/2-public route diff, scanner GET-write-zero, POST/CSRF/token/replay/WAF/redaction/dependency-repair evidence | public route cannot enqueue/send or authenticate operator |

### Final-SEND facts and execution envelope

Each last-mile transaction must lock and freshly verify recipient identity, confirmed jurisdiction, `AFFIRMATIVE_CONSENT` status/capture/verification/expiry and exact purpose/channel/sender scope, current accepted legal/Google/disclosure artifact tuples, campaign/member/message/mailbox/control/approval/eligibility/budget/rate/time/reply/suppression/ambiguity state, content/template/policy hashes and public-unsubscribe readiness. The counsel-exception route is forbidden for this experiment. All 14 dedicated denials are evaluated by their exact applicability and never replaced by a generic reason: `RECIPIENT_IDENTITY_UNVERIFIED`, `RECIPIENT_JURISDICTION_UNKNOWN`, `RECIPIENT_CONSENT_MISSING`, `RECIPIENT_CONSENT_EXPIRED`, `COUNSEL_EXCEPTION_MISSING`, `LEGAL_REVIEW_MISSING`, `LEGAL_REVIEW_STALE`, `DISCLOSURE_TEMPLATE_INVALID`, `GOOGLE_POLICY_DENIED`, `RECIPIENT_REPLIED`, `RECIPIENT_OPTED_OUT`, `RECIPIENT_HARD_BOUNCED`, `RECIPIENT_COMPLAINT`, `RECIPIENT_SOFT_BOUNCE_LIMIT`. Unknown, stale, conflicting or inapplicable-route misuse denies.

| Bound | Exact first-experiment value |
| --- | --- |
| Offer/campaign/mailbox | exactly one offer, one immutable campaign version and one mailbox |
| Legal configuration | exactly one configured recipient-jurisdiction set and one current legal-policy/disclosure/Google-review set |
| Recipient cohort | one to ten recipients, each with recipient-specific accepted affirmative-consent evidence; no exception route |
| Send cap | at most 5 in any rolling 24 hours, 10 total, one initial message per recipient and one in-flight send per mailbox |
| Follow-up | zero automated or manual campaign follow-up under this version |
| Approval | one step-up sensitive preview and fresh receipt-bound manual operator approval per recipient-specific immutable message version; no auto/batch approval |
| Reply window | 14 days after the last reconciled delivery; new sends stop when the 10-total cap or any abort fires |
| Public surface | exact FastAPI-owned scanner-safe HTML GET/explicit POST pair only, token lifetime <=90 days and key overlap >=97 days, published for this policy/release and independently disableable |

### Public unsubscribe route-mode truth table

An experiment abort always immediately commits `PRODUCT_OUTREACH=false`, closes/cancels provably unsent intent and work through canonical command authority, stops new admission/dequeue/provider construction, and keeps every agent, scheduler, worker and send authority off. Abort does **not** by itself remove an opt-out mechanism from recipients who already received a message. The signed route-mode record binds the exact release/policy/token-key/cohort, expected route/control versions, active-token expiry envelope, public/suppression/witness/telemetry health checks, operator/counsel decision, UTC and evidence hashes.

| Route mode | Entry condition | Exact reachable surface and authority | Required operator action and evidence | Exit |
| --- | --- | --- | --- | --- |
| `ACTIVE` | M9 entry is open, the exact public/suppression/witness/telemetry dependencies are healthy and the experiment has not aborted | exactly the scanner-safe GET and explicit POST; private/product/send routes remain unreachable publicly; `PRODUCT_OUTREACH` is a separate versioned fact and no public call can authorize send | continuously prove 64-private/2-public set equality, GET write-zero, POST atomic suppression, token/replay/WAF/redaction and dependency health | normal close or any abort commits product off and re-evaluates into `SUPPRESSION_ONLY` or `DISABLED_UNSAFE` |
| `SUPPRESSION_ONLY` | experiment closed/aborted while an active token, policy or delivered-recipient obligation remains, and the edge plus `RecipientSignalSuppressionService`, PostgreSQL, token/replay, witness and telemetry dependencies are all proven healthy | retain exactly the same GET/POST pair in an isolated suppression-only deployment; every agent/worker/send/private/product route and `PRODUCT_OUTREACH` stay off | keep health/route/suppression evidence current for the full obligation, process POST idempotently, monitor the mailbox reply opt-out path manually, reconcile signals/backlog and retain daily cohort/token/route evidence | restore `ACTIVE` only for a separately valid non-aborted entry; otherwise retire the deployment only after the signed retirement criteria below |
| `DISABLED_UNSAFE` | any public/suppression/token/DB/WAF/witness/telemetry dependency is unsafe or its truth is unknown | pair is immediately unpublished; no public route remains and all product/send/agent/worker authority stays off | proactively create active recipient suppression for **every delivered cohort member** through canonical `SuppressionCommandService` authority using opaque member refs; preserve and manually monitor reply-based opt-out plus the exact counsel-approved alternate channel; page `ALERT_COMPLIANCE_SUPPRESSION`, open `COMPLIANCE_OR_SUPPRESSION_BREACH` under `IR-12`, notify counsel and record the counsel decision; retain DNS/WAF/route/backlog/cohort/suppression set-equality evidence | only `SUPPRESSION_ONLY`, never `ACTIVE`, after exact recovery, backlog replay and operator/counsel sign-off; product remains false |

Restoration from `DISABLED_UNSAFE` requires a clean immutable release/config; exact `T7-PUBLIC-EDGE-VERIFY` exit `0`; 64+2 route set equality; scanner GET write-zero; POST Origin/CSRF/content-type/token/replay/WAF/redaction and serializable suppression tests; dependency-failure and repair tests; complete replay of every queued public/reply/alternate-channel observation; delivered-cohort-to-active-suppression set equality for the outage interval; zero no-next-`SEND` violations; current witness/telemetry; closed or explicitly contained `IR-12`; and signed operator/counsel evidence. Re-publication enters `SUPPRESSION_ONLY` and cannot revive the aborted campaign.

Safe retirement is not `DISABLED_UNSAFE`: after all active tokens have expired or been fulfilled, the full counsel-defined policy and delivered-recipient obligation has ended, all observations/backlogs are terminal, no route/suppression incident remains and counsel/operator sign the evidence, the isolated pair may be unpublished and its route-mode record closed. Retirement never deactivates suppression or deletes token, signal, incident or recipient-obligation evidence.

The operator signs entry, confirms all recipients/consents without exporting address/hash material, verifies both controls false, publishes/verifies only the public pair, then separately enables `PRODUCT_OUTREACH` at the expected version. For each recipient the operator refetches exact accepted artifacts and final facts, reviews the rendered message/sender/disclosure/unsubscribe scope, types `SEND`, persists approval, records one intent and observes terminal/reconciled evidence before admitting the next send. The operator reviews replies/signals/suppression/telemetry/cost and route-mode health daily, closes sending at cap or abort, commits product control false, applies the truth table for the full approved policy/token/recipient obligation, waits the reply window, and signs the decision.

| Decision point | Exact rule |
| --- | --- |
| Success | envelope never breached; every send has consent/approval/final-SEND/provider/audit/cost evidence; every reply/signal suppresses before any next send; all attempts terminal; reply window complete; signed decision uses retained raw counts |
| Immediate abort | any authority ambiguity, policy denial, suppression uncertainty, possible wrong recipient/mailbox/content, duplicate or blind retry, any unresolved provider ambiguity (which remains permanently quarantined), budget/cap breach, control/telemetry/backup/AWS witness blindness, complaint, hard bounce, legal/Google/policy/evidence drift, public dependency failure, credential/privacy incident or untrusted audit truth |
| Rollback/demotion | immediately commit product control false, close provably unsent work, stop agents/workers/dequeues/provider construction, preserve evidence/leases, reconcile every possible call, revoke affected credentials/approvals and open the exact incident; retain the exact pair in `SUPPRESSION_ONLY` when its complete dependency chain is healthy, otherwise execute `DISABLED_UNSAFE`; return to the failed gate |
| Re-entry | never resume the old immutable campaign after an abort; close incident/root cause/counsel obligations, issue new policy/message/campaign/release versions as applicable, rerun affected M1/M6/M8/M9 evidence and obtain a new entry/individual approvals with equal-or-lower caps |
| Downstream unlock | signed `SCALE` candidate triggers delivery-feasibility review only; `REVISE` creates one changed hypothesis/version; `KILL` closes; `INCONCLUSIVE` authorizes no claim or cap increase |

Every reply, opt-out, hard bounce, complaint or configured soft-bounce-limit signal invokes the canonical suppression transaction immediately; the classifier never delays it. A complaint or any hard bounce also aborts this tiny cohort under the stricter SEC-04 kill rules. A reply ends further outreach to that recipient regardless of sentiment. No signal creates an automated response.

## Ordered implementation tasks

- [ ] **Freeze one real-experiment entry —** Input: current M0-M8 records, exact offer/campaign/mailbox/legal/consent cohort, caps, decision rule and public evidence. Operation: verify complete immutable bindings and sign entry while controls/public are off. Output: one eligible bounded envelope. Test evidence: second offer/campaign/mailbox/policy, 11th recipient, exception route, stale consent/gate and address/hash exposure negatives. Failure behavior: no enable/publish.
- [ ] **Publish and mode only scanner-safe suppression ingress —** Input: signed release/policy/key/WAF/route-mode manifest. Operation: publish exact GET/POST pair, prove GET write-zero and POST atomic suppression/replay/redaction/fail-close, then exercise `ACTIVE|SUPPRESSION_ONLY|DISABLED_UNSAFE` without exposing any private/product/send route. Output: recipient-opaque public capability plus immutable mode transitions. Test evidence: scanner, invalid/expired token, CSRF/Origin/content-type/rate/dependency/64+2 diff, healthy abort retention, unsafe unpublish/cohort suppression/alternate channel/IR-12 and recovery/backlog replay. Failure behavior: product false; select `SUPPRESSION_ONLY` only when the full dependency chain is proven healthy, otherwise execute `DISABLED_UNSAFE`.
- [ ] **Approve and send each initial message manually —** Input: fresh recipient-specific artifacts/facts/message and remaining caps. Operation: operator reviews/approves, `RecordSendIntent` persists authority, final policy locks every fact and `SendGateway` calls Gmail once at most. Output: terminal or quarantined attempt evidence. Test evidence: all 14 denial/applicability, stale-race, wrong-scope, concurrency and call-count cases. Failure behavior: deny or reconcile; never blind retry.
- [ ] **Suppress every recipient signal and watch aborts —** Input: Gmail/public observations, replies, bounce/complaint/soft-limit and operational controls. Operation: atomically record/suppress/close provably unsent work, monitor cost/telemetry/backup/witness and kill on the exact triggers. Output: no-next-SEND proof and incident when required. Test evidence: each signal/write-boundary and blindness/cap/evidence-drift injection. Failure behavior: abort globally when specified.
- [ ] **Close the window and record the decision —** Input: reconciled deliveries/signals/replies/cost/time/metric snapshots after 14 days. Operation: disable sending, recompute from authoritative records and apply the pre-registered rule without rewriting history. Output: operator `SCALE|REVISE|KILL|INCONCLUSIVE` record. Test evidence: underpowered/no-denominator/late-reply/duplicate-observation and safety-override cases. Failure behavior: `INCONCLUSIVE` or stopped; no scale claim.

## Test strategy

- **Manifest `test_first_real_entry_is_one_offer_campaign_mailbox_policy_and_at_most_ten_consented_recipients`.**
- **Public `test_only_scanner_safe_unsubscribe_get_and_explicit_post_are_public_and_m9_gated`.**
- **Abort mode `test_abort_commits_product_off_and_selects_exact_active_suppression_only_or_disabled_unsafe_route_truth`.**
- **Unsafe public recovery `test_disabled_unsafe_suppresses_delivered_cohort_preserves_alternate_channel_and_republishes_only_after_recovery_and_backlog_replay`.**
- **Authority `test_every_real_send_has_fresh_consent_individual_approval_and_all_final_send_facts`.**
- **Caps `test_real_experiment_is_five_per_day_ten_total_one_per_recipient_and_zero_followups`.**
- **Signals `test_reply_optout_hard_bounce_complaint_and_soft_limit_suppress_before_any_next_send`.**
- **Decision `test_ten_recipient_result_is_inconclusive_without_registered_strong_positive_and_safety_always_overrides`.**

## Security, privacy, compliance, idempotency, observability, and cost

Recipient addresses, content and consent/legal sources remain restricted; the deterministic SHA-256 recipient lookup is pseudonymous, equality-revealing and offline enumerable residual-risk data, never anonymous and never HTTP/log/event/report/export material. Opaque target refs and accepted artifact references cross safe surfaces. Every send/POST/cost mutation is idempotent and reconciled; GET is write-zero. Audit/metrics expose bounded IDs, versions, reason codes, counts and UTC only. Original-currency reservations and ILS evidence must remain authoritative and below the stricter manifest/provider/counsel cap. Legal conclusions belong to counsel, not an agent or deterministic metric.

## Failure, rollback, and operator recovery

Disable sending first and preserve truth. Product control, agents, workers, send/dequeue authority and every possibly called attempt stay stopped until each suppression signal, cost reservation, credential/public dependency and incident is reconciled. The public pair follows only the route-mode truth table: healthy recipient-suppression obligations remain reachable in `SUPPRESSION_ONLY`; an unsafe pair executes `DISABLED_UNSAFE`, cohort-wide proactive suppression, alternate-channel monitoring and `IR-12`, then can return only to `SUPPRESSION_ONLY` after exact recovery evidence. Use canonical commands and immutable versions; do not delete evidence, deactivate suppression, edit provider/DB state, reopen the campaign, substitute GCS for AWS witness authority, raise a cap, or ask an agent to classify authority. If evidence cannot prove what happened, sending remains stopped and public ingress is treated as unsafe.

## Acceptance and retained evidence

- [ ] Exact one/one/one legal configuration and one-to-ten consent-only recipient cohort are immutable before enable.
- [ ] Each recipient receives at most one individually approved initial message through `SendGateway`; follow-up count is zero.
- [ ] Exact public pair, 14 final-SEND denials, signals/suppression, caps, ambiguity, costs and aborts behave fail closed.
- [ ] Every abort proves exact route-mode selection, delivered-cohort and alternate-path obligations, recovery/backlog replay or signed safe-retirement evidence without exposing a third public route.
- [ ] Sending ends with all attempts/costs/signals reconciled, product control false and an honest signed 14-day decision.

Retain entry/release/gate/policy/public-route signatures and hashes; route-mode transitions and dependency health; opaque recipient/artifact/approval/intent/attempt references; provider/reconciliation/suppression/audit/cost/time/metric evidence; public scanner/WAF/POST receipts; delivered-cohort suppression set equality; backlog replay; alternate-channel and counsel decisions; `IR-12` incidents/repairs; safe-retirement evidence; control/credential cleanup; and the signed decision. Restricted evidence follows SEC-06/holds; no normal retained bundle contains recipient hash/address, token, content or privileged legal text.

## Dependencies and next deliverable

LAUNCH-03 is the final M9 bounded-authority gate. Its result feeds [LAUNCH-04 earned autonomy](04-earned-autonomy.md) only for reversible internal capabilities; real-recipient sending, approvals, controls, legal decisions and cap changes never become autonomous at any result.
