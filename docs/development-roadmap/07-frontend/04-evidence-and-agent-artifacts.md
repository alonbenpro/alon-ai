# Evidence and Agent Artifacts

**Document ID:** FRONTEND-04
**Status:** Planned evidence review/acceptance UX over exact BACKEND-02 artifact/evidence/evaluation routes
**Milestone:** M4-M7, after accepted artifact/provider/report projections exist
**Owner:** Solo operator
**Prerequisites:** [DB-04](../02-database/04-agent-artifacts-and-evidence.md), [AGENT-01](../04-agents/01-agent-runtime-and-contracts.md), [AGENT-10](../04-agents/10-agent-evals-and-versioning.md), [BACKEND-06](../06-backend/06-reporting-and-query-services.md), and [FRONTEND-01](01-information-architecture.md)
**Outputs:** Provenance-first generated-client detail/evidence/evaluation components, explicit redaction/abstention/eval semantics, and exact accept/reject reconciliation
**Unlocks:** Evidence-aware approvals and experiment decisions without granting agent authority
**Risk:** High
**Complexity:** L

## Outcome and timing

The operator can distinguish a produced model artifact from a validated/accepted product input, inspect its safe provenance/evidence/evaluation facts, and explicitly accept or reject the exact version/hash through the generated client. The UI never calculates validation/acceptance, promotes an agent/config, repairs data, or reconstructs restricted content.

## Current repository state

No agents, product artifacts, evidence rows, evaluations, provider ledgers, product routes, or evidence components exist. The frontend has generated health types only. BACKEND-02 now defines exact artifact detail, paged evidence, evaluation-result, accept, and reject operations; none exists in current code yet.

## Scope and non-goals

In scope: artifact detail, evidence citations, evaluation detail, exact accept/reject commands, references returned by experiment/campaign/approval/message/report schemas, exact status/version/hash/provenance/eval presentation, redaction/retention states, and links among safe IDs.

Non-goals: raw source download, decrypted capture/body/prompt, chain-of-thought, provider payloads, live provider query, client-side validation/acceptance calculation, generic artifact CRUD, or a Next.js business/auth route.

## Exact planned implementation surfaces

Create `src/features/evidence/components/{artifact-reference-card,artifact-status,agent-run-summary,evidence-reference-list,provenance-chain,evaluation-summary,redaction-notice,provider-operation-table}.tsx`, `src/features/evidence/formatters.ts`, and embed them in experiment/campaign/approval/message/recovery pages; add generated hooks `src/features/evidence/hooks/{use-artifact,use-artifact-evidence,use-evaluation-result,use-artifact-command}.ts`. Stable artifact/evaluation links may use `/experiments/[experimentId]?artifact=[artifactId]` and safe in-page focus; URL values are UUIDs only.

### Exact facts and labels

When present in a generated response, render these DB-04 facts without renaming their canonical values:

| Record | Exact safe fields/values | Presentation rule |
| --- | --- | --- |
| agent run | `agent_run_id`, experiment/run IDs, `agent_type`, agent/prompt/model/toolset versions, input hash, state `PENDING/RUNNING/SUCCEEDED/FAILED`, abstention flag/reason, token/tool counts, original `cost_minor/currency`, safe error, correlation, UTC times | versions/hashes copyable; no prompt/input/output payload; `SUCCEEDED` does not mean artifact accepted |
| artifact | ID, type, schema/artifact version, status `PRODUCED/VALIDATED/REJECTED/ACCEPTED/SUPERSEDED`, content hash, confidence or abstention, supersedes ID, created UTC | immutable version chain; business materialization remains authoritative after acceptance |
| evidence | ID/type, DB-04-sanitized `citation_uri`/hash/policy/provider only if response permits, retrieval/publication UTC, content hash, MIME/language/license, retention `SENSITIVE_SHORT`, redaction `RAW_RESTRICTED/REDACTED/PURGED` | never fetch raw locator/ciphertext or `capture_ref`; `PURGED` retains hash/state and does not render as missing |
| evidence link | artifact/evidence IDs, JSON `claim_pointer`, `SUPPORTS/CONTRADICTS/CONTEXT`, excerpt hash | relationship uses text + icon/pattern, never color alone; no inferred claim truth |
| validation/acceptance | validator/gate version, booleans/reason codes/facts or scope hashes, acceptance mode `OPERATOR/DETERMINISTIC_GATE`, UTC | validation and acceptance are distinct; only `acceptArtifact` can request operator acceptance and the server decides |
| evaluation | suite/case/evaluator/config versions/hashes, scores, passed/hard-gate/reason fields, sensitivity `SYNTHETIC/REDACTED/RESTRICTED`, duration/original cost where exposed | evaluation evidence informs promotion; it is not production artifact authority |

Canonical product artifact labels are `ExperimentBrief`, `IdeaCandidate`, `OfferHypothesis`, `MarketEvidence`, `LeadEvidence`, `QualificationAssessment`, `OutreachDraft`, `ReplyClassification`, `MetricSnapshot`, `EvidenceBundle`, and `ExperimentDecision`. Canonical agent types are `IDEA_DISCOVERY`, `OFFER_DESIGN`, `MARKET_RESEARCH`, `LEAD_RESEARCH`, `LEAD_QUALIFICATION`, `OUTREACH_DRAFTING`, `REPLY_CLASSIFICATION`, and `EXPERIMENT_EVALUATION`. Unknown values block the affected card and preserve the raw safe enum for diagnosis.

### Exact API/query ownership

| Surface | Operation/query key | What may be rendered |
| --- | --- | --- |
| experiment evidence section | `getExperiment`, `['experiment',id]`; `getExperimentOverviewReport`, `['report','experiment',id,'overview']` | only embedded brief/run/evidence-bundle/decision refs actually present in generated `data`/report |
| experiment timeline | `getExperimentTimelineReport`, `['report','experiment',id,'timeline',{cursor,limit}]` | safe `artifact.produced/validated/rejected/accepted/superseded` events and authority IDs/hashes; not artifact payload reconstruction |
| campaign/message context | `getCampaignVersion`; `getOutreachMessage` | exact `OutreachDraft`, approval-basis, message/content-hash, reply-classification refs present in resources |
| approval scope | `getApproval` | sorted artifact ID/version/hash references copied from `ApprovalBasisScopeV1`; eligibility decision/version/facts/basis hashes and expiry/cap |
| provider/evidence health | `getProviderOperationsReport`, `['report','providers',{cursor,limit}]` | capability/operation/provider/config versions, calls/outcomes/errors/time/tokens/cost, evidence counts, ambiguity age, discrepancies; never prompts/content/addresses/credentials |
| artifact detail | `GET /api/v1/artifacts/{artifact_id}`, `getArtifact`, `["artifact",artifactId]` -> `ArtifactResponseV1` | schema/artifact versions, status/hash, agent config/run, latest deterministic validation and acceptance, supersession/redaction; 5-second poll nonterminal, stop terminal |
| evidence/citations | `GET /api/v1/artifacts/{artifact_id}/evidence`, `listArtifactEvidence`, `["artifact",artifactId,"evidence",{cursor,limit}]` -> `PageResponseV1[ArtifactEvidenceResponseV1]` | stable keyset pages; claim pointer, SUPPORTS/CONTRADICTS/CONTEXT, sanitized citation/hash/policy, content/excerpt hash, redaction/purge; no raw locator/query-secret field; snapshot expiry restarts |
| evaluation | `GET /api/v1/evaluation-results/{evaluation_result_id}`, `getEvaluationResult`, `["evaluation-result",id]` -> `EvaluationResultResponseV1` | case/suite/evaluator/config/scores/pass/reasons/version/hash/sensitivity; restricted payload omitted |
| accept | `POST /api/v1/artifacts/{artifact_id}/commands/accept`, `acceptArtifact`, `AcceptArtifactRequestV1 -> ArtifactResponseV1` | `["artifact",id,"accept"]`; exact artifact version/content hash/expected VALIDATED/reason, idempotency/CSRF; confirm validation/evidence/eval; no optimistic status; invalidate artifact/evidence/experiment/campaign/approval/message/reports |
| reject | `POST /api/v1/artifacts/{artifact_id}/commands/reject`, `rejectArtifact`, `RejectArtifactRequestV1 -> ArtifactResponseV1` | `["artifact",id,"reject"]`; exact version/hash/expected PRODUCED or VALIDATED/reason; destructive confirmation; stale/superseded/accepted fails and refetches |

All five operations require the active configured operator session; 403 keeps allowlisted evidence visible when permitted but disables decisions. The three detail panels are read-only queries. Accept/reject are the only feature mutations: each freezes the generated request and one idempotency key, has no optimistic update, and on 200 replaces the artifact snapshot then invalidates artifact/evidence/evaluation, experiment, campaign-readiness, approval/message, report, and recovery keys. Timeline/provider pagination uses server cursors; `REPORT_SNAPSHOT_EXPIRED` drops the whole traversal and restarts page one. Active runs refetch embedded evidence every 15 seconds; terminal experiments use 60 seconds/on-focus. Provider operations use manual pagination plus on-focus and no background poll unless `/recovery` is actively resolving an incident.

### Required rendering states and command reconciliation

Loading uses per-card skeletons. Empty distinguishes “no artifact reference returned,” “agent abstained,” “artifact rejected,” and “evidence purged.” Stale shows server `as_of`, high-watermark, projection version, and disables any parent authority dialog that depends on that reference. Partial displays `complete=false` and every server warning; an absent authoritative source is a 503 error, not partial success. Redacted and restricted states keep IDs/hashes/status visible without a reveal affordance. Superseded/rejected are terminal for that version and remain inspectable.

Accept/reject dialogs display exact artifact ID/type/schema/artifact version/content hash/status, latest validator version/schema/provenance booleans/reasons/facts hash, evidence relationship/citation/redaction summary, evaluation result/version/hash/pass/hard-gate/reasons when linked, supersession, and downstream lifecycle effects. Accept is enabled only on a fresh server-returned `VALIDATED` snapshot; reject only on fresh `PRODUCED`/`VALIDATED`. The server remains authoritative and stale/hash/superseded/terminal conflicts focus the error summary and require rereview. Parent lifecycle start/readiness actions refetch accepted artifacts and remain disabled while required acceptance is absent or stale.

## Ordered implementation tasks

- [ ] **Implement generated reference components —** Input: exact embedded generated unions. Operation: render exhaustive artifact/agent/evidence/eval statuses, IDs/versions/hashes, abstention, supersession, relationship, redaction, and UTC/presentation times. Output: provenance-first cards. Test evidence: every-state typed fixtures and unknown-union failure. Failure behavior: block only affected card and show correlation.
- [ ] **Implement report-backed provider/timeline evidence —** Input: exported-snapshot pages and provider report. Operation: render stable pages/data tables, preserve as-of/high-watermark/warnings, and restart expired snapshots. Output: reproducible evidence context. Test evidence: pagination concurrency/expiry, partial, cost-currency, and ambiguity fixtures. Failure behavior: discard mixed traversal; never merge snapshots.
- [ ] **Prove artifact mutation remains server-authoritative —** Input: route/import/network graph. Operation: assert only exact accept/reject mutations, no acceptance calculation, provider fetch, raw capture access, or inferred materialization. Output: evidence review UI with server-reconciled decisions. Test evidence: network allowlist, stale version/hash/supersession races, and static AST scan. Failure behavior: block release.
- [ ] **Gate lifecycle actions on accepted artifacts —** Input: UX acceptance criteria versus 66-operation manifest. Operation: require fresh accepted artifact IDs/versions/hashes before dependent research/campaign/approval/evaluation actions. Output: fail-closed lifecycle gate. Test evidence: operation/schema coverage diff. Failure behavior: refetch or block; never infer acceptance.

## Test strategy

- **Contract `test_evidence_components_accept_only_generated_embedded_types`:** no handwritten DTO.
- **Semantics `test_produced_validated_accepted_and_business_materialized_are_not_conflated`:** distinct labels.
- **Redaction `test_restricted_redacted_purged_and_missing_render_differently`:** no reveal control.
- **Evaluation `test_eval_pass_and_agent_success_never_render_as_artifact_acceptance`:** authority boundary.
- **Pagination `test_timeline_provider_snapshot_expiry_discards_all_pages`:** no mixed truth.
- **Security `test_evidence_dom_url_logs_and_telemetry_exclude_payloads_prompts_addresses_and_capture_refs`:** allowlist scan.
- **Accessibility `test_provenance_relationships_have_table_and_non_color_text_alternatives`:** keyboard/axe.

## Security, privacy, compliance, idempotency, observability, and cost

Schema-based redaction outranks operator curiosity. Never place raw source excerpts, capture refs, content JSON, prompts, hidden reasoning, provider payloads, or restricted values in DOM attributes, URL, analytics, clipboard defaults, or logs. External source links, if allowed by the generated schema, show domain and require an explicit new-tab warning. Safe telemetry records counts/status/version, not content. All costs retain original currency/minor units and only show server-recorded ILS evidence.

## Failure, rollback, and operator recovery

Unknown artifact/agent/provider status, impossible version chain, hash disagreement, privacy warning, or report corruption fails the affected view and links to `/recovery` when an incident is returned. Do not “repair” display data. Roll back the component version, clear in-memory query cache, and preserve server rows/events. An operator can act only through the parent typed commands defined elsewhere.

## Acceptance and retained evidence

- [ ] Every rendered artifact/evidence/agent/eval fact is traceable to a named generated response.
- [ ] Produced, validated, accepted, materialized, superseded, rejected, abstained, redacted, purged, partial, and missing remain distinct.
- [ ] Provider cost/latency/evidence/ambiguity views preserve server provenance and currency.
- [ ] Artifact/evidence/evaluation and accept/reject use only the five exact generated operations; no other CRUD is invented.
- [ ] Table/card alternatives, non-color relationships, keyboard paging, focus, and reduced-motion behavior pass.

Retain type fixtures, DOM/privacy scans, network allowlist, acceptance/rejection replay/conflict traces, pagination traces, and axe/keyboard results.

## Dependencies and next deliverable

FRONTEND-04 consumes DB-04/AGENT-01/10 and BACKEND-02's five exact artifact/evidence/evaluation operations. Its accepted, versioned references feed [FRONTEND-06 approvals](06-approval-inbox.md) and [FRONTEND-08 decisions](08-cost-funnel-and-decision-analytics.md); restricted captures, prompts, and generic artifact CRUD remain intentionally absent.
