# Lead Discovery and Preliminary Qualification Agent

**Document ID:** AGENT-11
**Status:** Planned M3 specialist; no implementation exists
**Milestone:** M3 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact local order `AGENT-11-T01 -> AGENT-11-T02 -> AGENT-11-T03 -> AGENT-11-T04`; cross-document task Inputs `AGENT-11-T01 <- AGENT-03-T01,AGENT-10-T01,AGENT-01-T01,DB-03-T03; AGENT-11-T02 <- AGENT-01-T02; AGENT-11-T03 <- AGENT-01-T04,BACKEND-01-T01,DB-04-T04,OBS-03-T02,PROVIDER-08-T03; AGENT-11-T04 <- AGENT-10-T03,AGENT-10-T04`. Source authorities: [PRODUCT-01](../00-product-strategy/01-product-scope.md), [PROVIDER-08](../05-providers/08-lead-discovery-provider.md), [runtime](01-agent-runtime-and-contracts.md), and [shared evaluation](12-agent-evals-and-versioning.md).
**Outputs:** LeadDiscoveryCandidate and preliminary QualificationDecision (materialized by QualificationService)
**Unlocks:** [Deep Lead Research](06-lead-research-agent.md)
**Risk:** Critical
**Complexity:** M

## Outcome and timing

This specialist searches only the approved `LeadDiscoveryProvider`, whose automated v1 source is **Brave Place Search**. It performs inexpensive preliminary qualification before expensive research and retains exact discovery provenance. It never directly calls Google Maps, Instagram, TikTok, social networks, arbitrary crawlers, or generic web clients.

Manually reviewed social/public profiles may later appear as bounded evidence, but they are not automated discovery targets and cannot expand this agent's tool scope.

The agent proposes `LeadDiscoveryCandidate` and a PRELIMINARY qualification recommendation. `BusinessIdentityService` and `QualificationService` deterministically own accepted identity/dedupe and the authoritative PRELIMINARY `QualificationDecision`. Only accepted preliminary qualification unlocks deep research.

## Exact inputs and outputs

Inputs include accepted OfferPackage ID/version/hash; governing strategy activation; exact source registry/terms/adapter version; geography/query/filter version; query/result/cost/time ceilings; dedupe evidence; and deterministic prefilter results.

Output candidates retain Brave place/business ID, evidenced name/location/domain/website fields, source query/capture/hash/time, identity keys, `FACT|ESTIMATE|UNKNOWN` preliminary facts, contradictions, and per-filter PASS/FAIL/UNKNOWN recommendations.

Names, owner/person identity, role, email, phone, social handle, or business-person linkage are never invented. Unknown required facts fail closed or remain UNKNOWN according to the offer filter contract.

## Cost-first execution

Before model access, deterministic composition applies obvious filters and dedupe. When model help is needed for structured extraction/initial scoring, the governing `ModelRoutingPolicy` routes to **Nano** by default. This agent cannot choose Mini or Premium. Mini is reserved for downstream shortlisted/deep-research work. Premium requires a separate exact operator approval and is not an ordinary discovery path.

Allowed capabilities remain narrow: evidence.read and `lead.discover`; all write ports, generic HTTP, Gmail/calendar writes, direct repositories, policy mutation, and dynamic source expansion are forbidden.

## Persistence, recovery, and evidence

AgentRunRecordingService owns run lifecycle; ArtifactCommandService inserts produced agent artifacts; ArtifactValidation/Acceptance services and QualificationService own acceptance. Provider/result/cost ledgers are immutable and replay-safe. A persisted paid result is recovered by request/hash rather than silently repeated.

Every successful or failed run records routing tier/reason, provider calls/cost, exact source/filter versions and evidence hashes. Manual social/public evidence remains distinguishable from Brave automated observations.

## Ordered implementation tasks

<!-- roadmap-task id=AGENT-11-T01 milestone=M3 depends_on=AGENT-03-T01,AGENT-10-T01,AGENT-01-T01,DB-03-T03 mode=parallel locks=agent-runtime -->
- [ ] **Encode exact schemas and immutable configuration —** Input: canonical OfferPackage/source/model-routing contracts. Operation: implement typed inputs/output proposal schemas, prompt/config hashes, Brave source identity and phase/authority rules. Output: importable contract/registry entry. Test evidence: strict schema, wrong automated source, missing provider input and unsupported identity cases. Failure behavior: reject before provider/model access.
<!-- roadmap-task id=AGENT-11-T02 milestone=M3 depends_on=AGENT-11-T01,AGENT-01-T02 mode=parallel locks=agent-runtime -->
- [ ] **Implement bounded specialist execution —** Input: verified runtime envelope and scoped Brave/evidence capabilities. Operation: run deterministic filters first, then only policy-routed Nano if required, respecting cancellation/cost/tool ceilings and hostile evidence. Output: SUCCESS/ABSTAIN/FAILED with lineage/ledger. Test evidence: no-AI path, Nano routing, Mini/Premium/source escalation denial, timeout/cancellation. Failure behavior: no accepted partial output or side effect.
<!-- roadmap-task id=AGENT-11-T03 milestone=M3 depends_on=AGENT-11-T02,AGENT-01-T04,BACKEND-01-T01,DB-04-T04,OBS-03-T02,PROVIDER-08-T03 mode=parallel locks=agent-artifacts,backend-domain -->
- [ ] **Validate and connect the deterministic handoff —** Input: terminal outputs, shared validation/cost services and Brave fixtures. Operation: enforce source/provenance/dedupe/preliminary rules and delegate accepted writes to deterministic owners. Output: tested specialist identity/handoff. Test evidence: Brave duplicates/conflicts, preliminary rejection no deep research, fabricated owner/contact rejection, social automation rejection, manual-evidence separation. Failure behavior: reject unsafe output and preserve prior accepted versions.
<!-- roadmap-task id=AGENT-11-T04 milestone=M3 depends_on=AGENT-11-T03,AGENT-10-T03,AGENT-10-T04 mode=serial locks=agent-runtime,agent-artifacts -->
- [ ] **Gate specialist acceptance with shared evaluation —** Input: signed repeated fixture sets/scores. Operation: verify quality, factuality, source isolation, routing/cost/latency thresholds and immutable config. Output: acceptance evidence. Test evidence: missing capture, fixture drift, unsupported source/model-tier escalation and threshold-edge rejection. Failure behavior: candidate remains ineligible.

## Acceptance

- [ ] Automated discovery source is exactly Brave Place Search.
- [ ] Social/public profiles are manual evidence only and cannot call discovery tools.
- [ ] Deterministic filters run before model use; discovery does not select Mini/Premium.
- [ ] Every candidate has source/evidence/version/hash lineage and no fabricated identity.
- [ ] Only deterministic services accept identity/qualification or mutate state.
