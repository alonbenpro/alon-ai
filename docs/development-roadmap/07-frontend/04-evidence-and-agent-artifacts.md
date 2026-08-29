# Evidence and Agent Artifacts

**Document ID:** FRONTEND-04
**Status:** Planned read-only evidence UX; BACKEND-02 currently defines no generic artifact/evidence detail route
**Milestone:** M4-M7, after accepted artifact/provider/report projections exist
**Owner:** Solo operator
**Prerequisites:** [DB-04](../02-database/04-agent-artifacts-and-evidence.md), [AGENT-01](../04-agents/01-agent-runtime-and-contracts.md), [AGENT-10](../04-agents/10-agent-evals-and-versioning.md), [BACKEND-06](../06-backend/06-reporting-and-query-services.md), and [FRONTEND-01](01-information-architecture.md)
**Outputs:** Provenance-first read components over existing v1 projections, explicit redaction/abstention/eval semantics, and a documented API coverage gap
**Unlocks:** Evidence-aware approvals and experiment decisions without granting agent authority
**Risk:** High
**Complexity:** L

## Outcome and timing

The operator can distinguish a produced model artifact from a validated/accepted product input, inspect the safe provenance and provider/evaluation facts that existing v1 resources expose, and understand missing, contradicted, abstained, rejected, superseded, redacted, and purged evidence. The UI never promotes, accepts, repairs, or reconstructs an artifact.

## Current repository state

No agents, product artifacts, evidence rows, evaluations, provider ledgers, product routes, or evidence components exist. The frontend has generated health types only. BACKEND-02 defines reports, experiment/campaign/approval/message resources, but no generic artifact/evidence detail operation or artifact acceptance/rejection route. Therefore a complete artifact browser cannot honestly be implemented from the exact v1 API today.

## Scope and non-goals

In scope: read-only artifact/evidence/provider references already returned by `getExperiment`, `getCampaignVersion`, `getApproval`, `getOutreachMessage`, `getExperimentTimelineReport`, `getProviderOperationsReport`, and report schemas; exact status/version/hash/provenance/eval presentation; redaction/retention states; links among safe IDs.

Non-goals: raw source download, decrypted capture/body/prompt, chain-of-thought, provider payloads, live provider query, client-side validation/acceptance, generic artifact CRUD, model comparison inferred from aggregate telemetry, or adding the missing endpoint in Next.js.

## Exact planned implementation surfaces

Create `src/features/evidence/components/{artifact-reference-card,artifact-status,agent-run-summary,evidence-reference-list,provenance-chain,evaluation-summary,redaction-notice,provider-operation-table}.tsx`, `src/features/evidence/formatters.ts`, and embed them only in experiment/campaign/approval/message/recovery pages. Do not create a standalone `/artifacts/[id]` route until BACKEND-02 adds an authoritative operation through the normal API-change process.

### Exact facts and labels

When present in a generated response, render these DB-04 facts without renaming their canonical values:

| Record | Exact safe fields/values | Presentation rule |
| --- | --- | --- |
| agent run | `agent_run_id`, experiment/run IDs, `agent_type`, agent/prompt/model/toolset versions, input hash, state `PENDING/RUNNING/SUCCEEDED/FAILED`, abstention flag/reason, token/tool counts, original `cost_minor/currency`, safe error, correlation, UTC times | versions/hashes copyable; no prompt/input/output payload; `SUCCEEDED` does not mean artifact accepted |
| artifact | ID, type, schema/artifact version, status `PRODUCED/VALIDATED/REJECTED/ACCEPTED/SUPERSEDED`, content hash, confidence or abstention, supersedes ID, created UTC | immutable version chain; business materialization remains authoritative after acceptance |
| evidence | ID/type, safe source URI/provider only if response permits, retrieval/publication UTC, content hash, MIME/language/license, retention `SENSITIVE_SHORT`, redaction `RAW_RESTRICTED/REDACTED/PURGED` | never fetch `capture_ref`; `PURGED` retains hash/state and does not render as missing |
| evidence link | artifact/evidence IDs, JSON `claim_pointer`, `SUPPORTS/CONTRADICTS/CONTEXT`, excerpt hash | relationship uses text + icon/pattern, never color alone; no inferred claim truth |
| validation/acceptance | validator/gate version, booleans/reason codes/facts or scope hashes, acceptance mode `OPERATOR/DETERMINISTIC_GATE`, UTC | validation and acceptance are distinct; frontend cannot create either |
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

All panels are read-only queries; there are no mutation keys, optimistic updates, or invalidations owned by this feature. Parent commands invalidate the relevant query keys as FRONTEND-01 defines. Timeline/provider pagination uses server cursors; `REPORT_SNAPSHOT_EXPIRED` drops the whole traversal and restarts page one. Active runs refetch embedded evidence every 15 seconds; terminal experiments use 60 seconds/on-focus. Provider operations use manual pagination plus on-focus and no background poll unless `/recovery` is actively resolving an incident.

### Required rendering states and API gap

Loading uses per-card skeletons. Empty distinguishes “no artifact reference returned,” “agent abstained,” “artifact rejected,” and “evidence purged.” Stale shows server `as_of`, high-watermark, projection version, and disables any parent authority dialog that depends on that reference. Partial displays `complete=false` and every server warning; an absent authoritative source is a 503 error, not partial success. Redacted and restricted states keep IDs/hashes/status visible without a reveal affordance. Superseded/rejected are terminal for that version and remain inspectable.

The absence of generic artifact/evidence read operations is a release-blocking gap for any requirement to inspect full artifact content, validations, acceptances, evidence claims, or eval results. The only compliant M4-M7 v1 UI is a reference/provenance view over the operations above. If detailed inspection is required, BACKEND-02 must be amended with reviewed schemas/status/privacy/cursors before frontend work; no `/api/*` proxy or handwritten response is acceptable.

## Ordered implementation tasks

- [ ] **Implement generated reference components —** Input: exact embedded generated unions. Operation: render exhaustive artifact/agent/evidence/eval statuses, IDs/versions/hashes, abstention, supersession, relationship, redaction, and UTC/presentation times. Output: provenance-first cards. Test evidence: every-state typed fixtures and unknown-union failure. Failure behavior: block only affected card and show correlation.
- [ ] **Implement report-backed provider/timeline evidence —** Input: exported-snapshot pages and provider report. Operation: render stable pages/data tables, preserve as-of/high-watermark/warnings, and restart expired snapshots. Output: reproducible evidence context. Test evidence: pagination concurrency/expiry, partial, cost-currency, and ambiguity fixtures. Failure behavior: discard mixed traversal; never merge snapshots.
- [ ] **Prove no artifact authority in the browser —** Input: route/import/network graph. Operation: assert no artifact mutation, acceptance calculation, provider fetch, raw capture access, or inferred materialization. Output: read-only evidence UI. Test evidence: network allowlist and static AST scan. Failure behavior: block release.
- [ ] **Gate detailed browser requirements on API coverage —** Input: UX acceptance criteria versus 48-operation manifest. Operation: list every unavailable field/action and require a BACKEND-02 change before implementation. Output: explicit gap record. Test evidence: operation/schema coverage diff. Failure behavior: render safe “detail unavailable in v1,” not fabricated data.

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
- [ ] No artifact/evidence detail or mutation endpoint is invented; the v1 coverage gap is explicit.
- [ ] Table/card alternatives, non-color relationships, keyboard paging, focus, and reduced-motion behavior pass.

Retain type fixtures, DOM/privacy scans, network allowlist, pagination traces, axe/keyboard results, and the API-gap coverage report.

## Dependencies and next deliverable

FRONTEND-04 consumes DB-04/AGENT-01/10 and the limited BACKEND-02 projections. Its safe references feed [FRONTEND-06 approvals](06-approval-inbox.md) and [FRONTEND-08 decisions](08-cost-funnel-and-decision-analytics.md). Full artifact inspection remains blocked on an explicit backend contract revision.
