# Cost-Optimized Sales-Validation Roadmap Design

**Date:** 2026-09-09
**Status:** Approved
**Scope:** Roadmap/specification only; no product implementation or live-provider authority is claimed.

## Goal

Reduce pre-revenue infrastructure, discovery, and model spend while preserving Alon AI's deterministic sending, commercial-policy, booking, evidence, safety, and checkpoint-learning boundaries.

## Canonical cost-first changes

### Lead discovery

- Brave Place Search is the only planned automated v1 place/business discovery adapter.
- Google Maps, Instagram, TikTok, social networks, directories, and arbitrary crawling are not automated discovery targets in v1.
- Social profiles may be attached only as manually reviewed evidence under existing source, privacy, retention, provenance, and truthful-personalization rules.
- LeadDiscoveryProvider continues to return observations only. LeadDiscoveryAgent proposes candidates; deterministic identity/admission and QualificationService own accepted PRELIMINARY qualification.

### Pre-revenue infrastructure

The initial production target is one provider-neutral Linux VPS with **2 vCPU and 4 GB RAM**. It runs the modular monolith and PostgreSQL with explicit resource limits.

- Operator ingress uses Cloudflare Tunnel plus Cloudflare Access. No public SSH/API/database listener is required.
- Product data is stored on encrypted local VPS storage.
- Backups are application-encrypted before upload to Cloudflare R2 and must pass restore drills.
- Recovery key/config material is held off-host under operator control.
- Multi-cloud backup witnesses, managed KMS/Secret Manager, a dedicated 160-GB data disk, and enterprise hardening are deferred until revenue or measured operational evidence justifies them.
- Deferred controls are upgrade targets, not M8 prerequisites.

### Model routing

Model selection is deterministic application policy, never an agent choice.

1. **NO_AI** — deterministic filters, deduplication, simple arithmetic/policy checks, and obvious eligibility decisions use no model call.
2. **NANO** — default model tier for structured extraction, normalization, classification, and initial scoring where deterministic code is insufficient.
3. **MINI** — allowed only for leads that already passed the cheap shortlist/preliminary gate, for deeper research/synthesis and message work that needs more reasoning.
4. **PREMIUM** — default denied; requires explicit operator approval binding the exact task/run, model/configuration, maximum spend, and expiry. Approval does not weaken safety or artifact gates.
5. **BATCH** — non-urgent research should use provider batch processing when the selected provider/tier supports it and latency is not user-facing.

Every model call records routing reason, tier, urgency/batch mode, governing configuration, tokens, cost, and strategy attribution. Model routing cannot grant Gmail/calendar write capability or commercial authority.

### Cost-first launch stages

The old automatic `100/200/300/400` incremental cohorts and `100/300/600/1,000` cumulative checkpoints are superseded.

The initial real-validation program is:

1. **SHADOW** — full pipeline runs without real recipient sends. It validates artifact quality, cost, routing, policy, and operator workflow. It does not count as real demand.
2. **REVIEW_20** — exactly up to 20 manually reviewed businesses. The operator reviews business/identity/evidence before real admission. The stage closes before further expansion.
3. **QUALIFIED_50** — up to 50 finally qualified businesses under the same bounded program and current safety/legal/provider envelope. The stage closes before expansion.
4. **SCALE_100_TO_300** — only after the 50-stage closes with sufficient meetings/revenue/economic evidence and no safety/reputation failure. The operator explicitly authorizes one concrete next tranche between 100 and 300 unique businesses. There is no automatic progression and no 600/1,000 path in the pre-revenue roadmap.

`CONTINUE|REVISE|KILL|INCONCLUSIVE|SAFETY_STOP` remain the checkpoint decisions. A later stage is never opened merely because the prior numeric sample was reached. Expansion requires evidence plus explicit operator scope authorization.

Global learning remains checkpoint-only. SHADOW may produce offline evaluation evidence but not real-demand learning. REVIEW_20 and QUALIFIED_50 close checkpoint evidence bundles; weak samples naturally yield KEEP/INSUFFICIENT_EVIDENCE in strategy evaluation. SCALE_100_TO_300 closes at its explicitly authorized tranche boundary. Strategy versions never mutate halfway through an active stage/tranche.

## Preserved boundaries

The following remain unchanged:

- OfferPackage is the sole downstream commercial authority.
- SendGateway is the sole Gmail writer and ambiguous send outcomes remain quarantined/reconciled before retry.
- CommercialPolicyEngine deterministically enforces minimum price, margin, allowed scope/discount/payment variants, truthful claims, and conversation limits.
- BookingGateway is the sole calendar writer and requires explicit timezone-aware confirmation.
- Global learning uses immutable checkpoint evidence, protected evaluation/rollback rules, and boundary-only activation.
- Opt-out/suppression, source restrictions, prompt-injection resistance, data minimization, auditability, and kill switches remain fail-closed.

## Deferred-after-revenue upgrade triggers

The roadmap may add managed KMS, multi-provider backup/witnessing, larger disks/hosts, stronger isolation, or premium model defaults only after an explicit architecture/cost review supported by revenue or measured capacity/recovery evidence. None is implied by ordinary growth.
