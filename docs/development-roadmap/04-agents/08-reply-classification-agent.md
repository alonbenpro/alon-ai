# Typed Reply Classification Agent

**Document ID:** AGENT-08
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3; first workflow use at M6
**Owner:** Solo operator
**Prerequisites:** [AGENT-01](01-agent-runtime-and-contracts.md), DB-03/DB-04, recorded reply fixtures, and deterministic unsubscribe/bounce safety rules
**Outputs:** Versioned `ReplyClassification` `PRODUCED` artifact, abstention/failure results, labeled fixtures, scores, and review evidence
**Unlocks:** WF-05 reply classification/triage; never automatic response authority
**Risk:** Critical
**Complexity:** M

## Outcome and timing

The agent classifies one already captured, mailbox-bound reply into a small explicit taxonomy and cites the input text spans that support it. Deterministic application rules retain authority for unsubscribe/suppression, bounce handling, attachment to `replies`, campaign/experiment changes, and any response. No classification sends or drafts a reply.

## Current repository state

There is no Gmail history sync, reply row, classifier, prompt, labeled dataset, suppression implementation, or response workflow. No live reply has been processed.

## Scope and non-goals

In scope: multi-signal reply classification, confidence, supporting spans, ambiguity, language, and review priority. Non-goals: suppression mutation, policy/compliance decision, sentiment surveillance beyond task need, automatic reply/draft, lead/campaign/experiment transition, Gmail access, raw attachment processing, or autonomous conversation.

## Exact typed contract and implementation surfaces

Create `agents/reply_classification.py`, `agents/prompts/reply_classification/v1.md`, `ReplyClassificationValidatorV1`, and `backend/tests/fixtures/evals/reply_classification/v1/`.

```python
class ReplyClassificationLabel(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    QUESTION = "QUESTION"
    OBJECTION = "OBJECTION"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    BOUNCE = "BOUNCE"
    OTHER = "OTHER"
    UNCERTAIN = "UNCERTAIN"

class ReplyClassificationInputV1(StrictAgentModel):
    schema_version: Literal["reply.classification.input.v1"]
    reply_id: UUID
    message_id: UUID
    mailbox_id: UUID
    provider_observation_id: UUID
    gmail_message_id_hash: Sha256Hex
    gmail_thread_id_hash: Sha256Hex
    received_at: datetime
    locale_hint: str | None = Field(default=None, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    subject_text: str = Field(max_length=200)
    body_text: str = Field(min_length=1, max_length=10_000)
    original_message_artifact_id: UUID
    original_message_content_hash: Sha256Hex
    deterministic_signal_codes: tuple[str, ...] = Field(max_length=20)

class ReplyEvidenceSpanV1(StrictAgentModel):
    start: int = Field(ge=0, le=10_000)
    end: int = Field(gt=0, le=10_000)
    span_hash: Sha256Hex

class ReplyClassificationArtifactV1(StrictAgentModel):
    schema_version: Literal["artifact.reply_classification.v1"]
    artifact_type: Literal["ReplyClassification"]
    reply_id: UUID
    primary_classification: ReplyClassificationLabel
    secondary_classifications: tuple[ReplyClassificationLabel, ...] = Field(max_length=3)
    evidence_spans: tuple[ReplyEvidenceSpanV1, ...] = Field(min_length=1, max_length=8)
    rationale: str = Field(min_length=10, max_length=500)
    language: str = Field(pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=3)
    operator_review_priority: Literal["NORMAL", "HIGH", "URGENT"]

class ReplyClassificationAbstentionV1(StrictAgentModel):
    schema_version: Literal["reply.classification.abstention.v1"]
    intended_artifact_type: Literal["ReplyClassification"]
    reason_code: Literal["EMPTY_AFTER_SANITIZATION", "UNSUPPORTED_LANGUAGE", "MALFORMED_CONTENT", "CONFLICTING_SIGNALS", "ATTACHMENT_REQUIRED"]
    safe_detail: TrimmedStr = Field(min_length=10, max_length=300)
    evidence_item_ids: tuple[Uuid4, ...] = Field(max_length=20)

ReplyClassificationTerminalResultV1: TypeAlias = AgentTerminalResultV1[
    ReplyClassificationArtifactV1, ReplyClassificationAbstentionV1
]

```

Spans are half-open, ordered, non-overlapping, within `body_text`, and hashed from the exact UTF-8 substring with `digest.reply_span.v1`. Primary cannot appear in secondary; `UNCERTAIN` has no secondary classes, confidence `<=0.50`, and review `HIGH`/`URGENT`. `UNSUBSCRIBE` and `BOUNCE` always use `URGENT`. `ReplyClassificationAbstentionV1` reasons are `EMPTY_AFTER_SANITIZATION`, `UNSUPPORTED_LANGUAGE`, `MALFORMED_CONTENT`, `CONFLICTING_SIGNALS`, or `ATTACHMENT_REQUIRED`; DB confidence is `NULL`. Execution failure uses AGENT-01 taxonomy.

`ReplyClassificationTerminalResultV1` is the only execution return type. Its `outcome` discriminator is exactly `SUCCESS`, `ABSTAIN`, or `FAILED`; every branch carries the exact `AgentConfigurationRefV1`, `AgentUsageV1`, and `ProviderUseLedgerEntryV1` tuple, while only success carries the product artifact and only failure carries `AgentFailureArtifactV1`.

## Dependencies, tools, evidence, and authority

Injected dependencies: AGENT-01 context/clock/cancellation, `EvidenceReadPort` for the declared original draft only, and promoted model. Allowed tool: `evidence.read`, maximum one call. The reply body is frozen input, not a tool result. Gmail/history/provider ports, search/page/business/contact tools, repositories/commands, `SuppressionCommandService`, policy/approval/budget/control, campaign/lead/experiment services, `SendGateway`, credentials, auto-response/drafting tools, and arbitrary HTTP are forbidden.

Reply content is hostile and cannot add instructions/tools. Evidence spans must support the label without copying the body into persisted telemetry. Deterministic unsubscribe/bounce signal rules run before and after the model. A model may increase review urgency but cannot override a deterministic `UNSUBSCRIBE`/`BOUNCE` signal to a less safe label; disagreement rejects the artifact and the deterministic safety command proceeds independently.

## Ceilings, cancellation, deterministic validation, and persistence

Ceilings: `timeout_seconds=20`, 3500 input tokens, 500 output tokens, 1 tool call, 2 model requests (JSON repair only), and 5 USD minor. Evidence deadline 3s; model <=14s. Cancellation yields no attached classification.

`ReplyClassificationValidatorV1` checks exact reply/message/mailbox/observation tuple; span boundaries/hashes; label/secondary/confidence/priority rules; deterministic-signal compatibility; language; no response/send/suppression/state fields; injection patterns; and ledger totals. Ownership handoff follows DB-04: `AgentRunRecordingService` alone stores/closes `agent_runs`; `EvidenceIngestService` alone stores any new `evidence_items`; `ArtifactCommandService` writes only the `PRODUCED` artifact row plus `artifact.produced.v1`; `ProviderCostReconciliationService` owns `cost_entries`; and only the later `ArtifactValidationService` transaction writes `artifact_evidence_links`, `artifact_validations`, validation status, and `artifact.validated.v1`/`artifact.rejected.v1`. Only validation/acceptance/application services attach `replies.classification_artifact_id` and emit canonical `reply.classified.v1`; separate deterministic services own suppression and every state transition.

## Offline evaluation and operator review

Suite `reply_classification.v1` contains exactly 120 labeled cases: 24 positive/question, 20 negative/objection, 20 unsubscribe, 16 out-of-office/bounce, 12 other/uncertain, 12 Hebrew/mixed-language, and 16 quoted-thread/injection/spoofed-header/authority cases. Scores: hard authority/injection/privacy/schema safety; macro F1 across nine labels; unsubscribe recall/precision; bounce recall; evidence-span exact/overlap score; uncertainty calibration; deterministic-signal agreement.

Promotion follows AGENT-10 two-phase evaluation: generate three independently signed, network-enabled candidate-model captures per case while every non-model capability uses frozen fixtures and no product authority exists; then disable all network and score each repetition independently. Replaying an identical model fixture cannot count as a capture. The rolling rollback population uses two adjacent non-overlapping `30`-invocation windows exactly as AGENT-10 defines.

Promotion requires 120/120 schema-valid; zero authority/response/suppression/injection hard failures; macro F1 `>=0.94`; unsubscribe recall `=1.00` and precision `>=0.98`; bounce recall `>=0.99`; evidence-span score `>=0.95`; expected-calibration error `<=0.05`; deterministic-signal agreement `=1.00` on mandatory signals; aggregate `>=0.94`; bottom decile `>=0.82`; p95 duration `<=16s`; mean/p95/max cost `<=4/5/5 USD minor`. Any unsubscribe/bounce false-negative regression blocks; other component regression `>0.01` or aggregate `>0.005` blocks.

Operator review is mandatory for `POSITIVE`, `QUESTION`, `OBJECTION`, `OTHER`, `UNCERTAIN`, any confidence `<0.85`, and any deterministic/model disagreement. `UNSUBSCRIBE`/`BOUNCE` safety action is deterministic and may run without accepting the model artifact, but is always operator-visible. No classification automatically drafts/responds. Immediate rollback follows one unsubscribe false negative, authority/response/suppression attempt, body leakage, or injection success; otherwise two consecutive 30-run windows with corrected classification `>3%`, post-validation failure `>1%`, calibration error `>0.08`, or nearest-rank p95 cost `>5 USD minor` or p95 duration `>16s` over the AGENT-10 terminal-invocation population trigger rollback.

## Ordered implementation tasks

- [ ] **Encode taxonomy/input/output/spans —** Input: reply identity and safety rules. Operation: implement strict models, prompt/config/hash and sanitizer contract. Output: typed classifier. Test evidence: enum/schema/span boundary snapshots. Failure behavior: malformed input blocks model.
- [ ] **Implement bounded hostile-content classification —** Input: verified reply envelope. Operation: apply pre-rules, one optional evidence read, structured classify, post-rules, ceilings/cancellation. Output: classification/abstention/failure. Test evidence: fake model/injection/timeout matrix. Failure behavior: deterministic safety signals remain available; no artifact attachment.
- [ ] **Implement validator/persistence/safety handoff —** Input: output/ledger/signals. Operation: verify spans/labels, persist only `PRODUCED`, and keep reply attachment/suppression in separate services. Output: immutable review artifact. Test evidence: atomic reply-event and suppression-independence cases. Failure behavior: classification absent/rejected, cursor history unaffected.
- [ ] **Build and gate 120-case labeled suite —** Input: frozen bilingual/adversarial cases. Operation: generate and sign three fresh candidate-model captures per case with frozen non-model fixtures, then disable network and run byte-exact Pydantic Evals scoring/regression gates for each repetition. Output: three full repetition summaries, suite summary, and promotion/rejection evidence. Test evidence: unique provider call/request IDs, complete capture-set signatures, no model replay, non-model zero-network proof, scoring golden vectors, and per-repetition threshold audit. Failure behavior: prior promoted version remains.

## Test strategy

- **Schema `test_reply_models_enforce_taxonomy_confidence_priority_and_spans`.**
- **Safety `test_unsubscribe_and_bounce_mandatory_signals_cannot_be_overridden`.**
- **Adversarial `test_reply_text_cannot_request_tools_response_suppression_or_send`.**
- **Privacy `test_reply_body_and_spans_never_appear_in_logs_events_or_failure`.**
- **Authority `test_agent_cannot_attach_reply_mutate_suppression_or_call_gmail`.**
- **Evaluation `test_reply_v1_macro_safety_calibration_and_regression_thresholds`.**

## Security, privacy, compliance, idempotency, observability, and cost

Reply content is `SENSITIVE_SHORT`, sanitized and never logged. The model receives no credentials/recipient address beyond task-minimized text. Input/config hashes prevent duplicate classification; provider usage is costed. Telemetry contains safe IDs/hashes, label/confidence bucket, signals/disagreement, duration/tokens/cost and ILS projection—never content or reasoning.

Retention follows AGENT-01 and DB-04/05/06 exactly: run/evaluation evidence is `EVALUATION_VERSIONED`, product artifacts/links are `BUSINESS_ACTIVE`, captures are `SENSITIVE_SHORT`, validation/acceptance/cost/event evidence is `SAFETY_LONG`, and only `RetentionCommandService` purges or redacts.

## Failure, rollback, and operator recovery

Malformed/unsupported/conflicting content abstains without cursor rollback or hidden state. Mandatory safety signals take the deterministic path even when the model fails. Corrections create a new immutable artifact; operators compare captured observation, sanitizer/span hashes, signal/version, run/validator/eval and roll back config. No response is issued during recovery.

## Acceptance and retained evidence

- [ ] Exact models/taxonomy/tools/evidence/confidence/abstention, ceilings/cancellation, failure, deterministic signals, validator, persistence/event map are implemented.
- [ ] All 120 cases meet numeric promotion/regression/rollback thresholds, including perfect unsubscribe recall in the suite.
- [ ] Agent produces only immutable `ReplyClassification` `PRODUCED`; deterministic services own attachment, suppression, state and response.
- [ ] No Gmail/history/provider credential, suppression/policy/approval/budget/control, campaign/lead/experiment mutation, response/draft/send, repository or web authority exists.

Retain sanitizer/signal/schema/prompt/config hashes, labeled fixtures/digests, confusion/calibration/span/eval reports, adversarial outputs, ledger/cost, validator/reply event/review, promotion/rollback records.

## Dependencies and next deliverable

A promoted AGENT-08 unlocks WF-05's post-sync classification/review step. It does not advance Gmail cursors, suppress, change a campaign/experiment, or respond.
