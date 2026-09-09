# Cost-Optimized Validation Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace pre-revenue discovery, infrastructure, model, and launch-cost assumptions with the approved cost-first design while preserving safety and deterministic authority.

**Architecture:** Keep the existing 438-task roadmap topology and stable task IDs where the implementation responsibility is unchanged. Rewrite provider/infrastructure/model/launch contracts and semantic validator invariants, then regenerate the generated execution artifacts from the revised canonical contract. GitHub remains canonical; Notion is reconciled after the branch is validated.

**Tech Stack:** Markdown roadmap sources, Python 3.13 roadmap validator, pytest, OpenAI provider abstraction, Brave Place Search, Cloudflare Tunnel/Access/R2, PostgreSQL/DBOS, Notion execution surface.

**Spec:** `docs/superpowers/specs/2026-09-09-cost-optimized-validation-roadmap-design.md`

## Global Constraints

- Automated v1 place/business discovery uses Brave Place Search only.
- Social profiles are manual-review evidence, never automated scraping targets.
- Initial production target is one provider-neutral 2-vCPU/4-GB VPS with Cloudflare Tunnel/Access, encrypted local storage, and application-encrypted R2 backups.
- Managed KMS, multi-cloud backup witnesses, dedicated 160-GB data disk, and enterprise hardening are post-revenue upgrade targets, not M8 prerequisites.
- Deterministic model routing is NO_AI → NANO → MINI; PREMIUM requires explicit bounded operator approval; non-urgent supported work prefers BATCH.
- Launch stages are SHADOW → REVIEW_20 → QUALIFIED_50 → explicitly authorized SCALE_100_TO_300.
- Remove the old 100/200/300/400 and 100/300/600/1,000 progression as normative pre-revenue authority.
- Preserve SendGateway, BookingGateway, CommercialPolicyEngine, provider-ambiguity quarantine, checkpoint decision enums, strategy-learning result enums, immutable evidence, and no-mid-stage strategy mutation.
- Do not claim implementation or live-provider readiness.

---

### Task 1: Canonical product and experiment contract

**Files:**
- Modify: `docs/development-roadmap/00-product-strategy/01-product-scope.md`
- Modify: `docs/development-roadmap/00-product-strategy/02-success-metrics.md`
- Modify: `README.md`
- Modify: `docs/development-roadmap/README.md`

**Interfaces:**
- Consumes: approved cost-first spec.
- Produces: canonical provider/model/infrastructure/launch vocabulary used by all later tasks.

- [ ] Replace old cohort arrays/ceiling with named cost-first stages and exact max business counts.
- [ ] Add explicit operator authorization for the 100–300 scale tranche and checkpoint-only strategy activation at stage boundaries.
- [ ] Preserve safety/decision/result enums and sole-writer authority.
- [ ] Update top-level scope/navigation and mark old scale assumptions superseded.

### Task 2: Discovery and model provider costs

**Files:**
- Modify: `docs/development-roadmap/05-providers/08-lead-discovery-provider.md`
- Modify: `docs/development-roadmap/04-agents/05-lead-discovery-agent.md`
- Modify: `docs/development-roadmap/05-providers/03-model-provider.md`
- Modify: relevant agent/runtime/evaluation docs where model selection is described.

**Interfaces:**
- Consumes: canonical source/model policy.
- Produces: Brave-only automated discovery and deterministic model-tier routing.

- [ ] Replace Google Maps/multi-source automated adapters with Brave Place Search as the sole v1 automated adapter.
- [ ] Keep social profiles as manual evidence only and preserve provenance/minimization rules.
- [ ] Add deterministic NO_AI/NANO/MINI/PREMIUM/BATCH routing with exact approval/cost attribution.
- [ ] Add tests/acceptance language proving agents cannot choose their own tier or escalate spend.

### Task 3: Pre-revenue infrastructure simplification

**Files:**
- Modify: `docs/development-roadmap/11-infrastructure/03-private-vps-deployment.md`
- Modify: `docs/development-roadmap/11-infrastructure/04-postgresql-backups-and-restores.md`
- Modify: `docs/development-roadmap/11-infrastructure/05-monitoring-and-disaster-recovery.md`
- Modify: security/retention docs referencing KMS/multi-cloud requirements.

**Interfaces:**
- Consumes: pre-revenue topology.
- Produces: M8 acceptance based on 2-vCPU/4-GB VPS + Cloudflare Tunnel/Access + local encryption + encrypted R2 restore evidence.

- [ ] Remove GCE-specific 4/8/160 baseline, Tailscale/Caddy dependency, managed KMS/Secret Manager requirement, GCS+AWS witness requirement from M8 minimum.
- [ ] Define provider-neutral VPS, Cloudflare private ingress, encrypted local data, application-encrypted R2 backups, off-host recovery key/config, and restore tests.
- [ ] Move multi-cloud/KMS/larger-disk/enterprise hardening to explicit post-revenue upgrade triggers.
- [ ] Preserve fail-closed restore, suppression, provider-action reconciliation, and private-by-default product ingress.

### Task 4: Launch, learning, testing, and frontend semantics

**Files:**
- Modify: `docs/development-roadmap/12-launch-and-operations/*.md`
- Modify: `docs/development-roadmap/03-workflows/08-checkpoint-evaluation-workflow.md`
- Modify: `docs/development-roadmap/03-workflows/09-global-learning-workflow.md`
- Modify: `docs/development-roadmap/07-frontend/*.md`
- Modify: `docs/development-roadmap/09-observability-and-evaluation/*.md`
- Modify: `docs/development-roadmap/10-testing/*.md`

**Interfaces:**
- Consumes: named cost-first launch stages.
- Produces: dashboard, metric, checkpoint, learning, and test contracts aligned to SHADOW/20/50/100–300.

- [ ] Replace old four-cohort assumptions with SHADOW, REVIEW_20, QUALIFIED_50, SCALE_100_TO_300.
- [ ] Require explicit operator scope approval before scale tranche admission.
- [ ] Keep learning checkpoint-only; SHADOW cannot produce real-demand learning; weak early evidence cannot mutate strategy.
- [ ] Add cost metrics for model-tier routing, batch savings, provider spend, meetings, revenue, and economics before scale.
- [ ] Update tests for exact stage order, manual-review gate, 50-stage economics gate, scale authorization, and no 600/1,000 path.

### Task 5: Validator and generated graph

**Files:**
- Modify: `scripts/validate_roadmap.py`
- Modify: `backend/tests/unit/test_roadmap_validator.py`
- Regenerate: `docs/development-roadmap/execution-manifest.json`
- Regenerate: `docs/development-roadmap/EXECUTION_ORDER.md`
- Regenerate: `docs/development-roadmap/AGENT_EXECUTION_PLAN.md`

**Interfaces:**
- Consumes: revised canonical contract and unchanged/stable task topology.
- Produces: semantic enforcement, new source-graph fingerprint, and current generated artifacts.

- [ ] Replace exact legacy cohort invariants with exact stage definitions and scale bounds.
- [ ] Add semantic checks for Brave-only automated discovery, model routing, and pre-revenue infrastructure minimum/deferred controls.
- [ ] Preserve provider ancestry, side-effect writers, artifact authority, and graph-DAG checks.
- [ ] Regenerate all three artifacts together and verify a second check is byte-exact.

### Task 6: Reconcile Notion

**Files:** Notion Founder OS only after GitHub validation.

**Interfaces:**
- Consumes: validated execution order/fingerprint.
- Produces: task graph/reference/evidence record aligned to GitHub.

- [ ] Update changed task names/dependencies/orders only if generated graph changes them.
- [ ] Keep 438 tasks if topology remains stable; otherwise reconcile exact new count.
- [ ] Add an accepted Roadmap Change record summarizing cost-first migration.
- [ ] Update Roadmap Reference with branch/head/fingerprint and new stage/provider/infrastructure/model policy.
