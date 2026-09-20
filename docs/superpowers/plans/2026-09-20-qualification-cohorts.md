# Qualification Matrices and Cohorts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist offer-specific qualification matrices and atomically freeze an exact 50-member protected cohort.

**Architecture:** Add one records subsystem beside existing offer and organization records. It references existing supply candidates/contact facts and organization bindings/recipients/reservations, mirrors accepted qualification into the existing supply gate, and uses existing record commands for replay protection.

**Tech Stack:** Python 3.13, Pydantic 2, SQLAlchemy 2, PostgreSQL, Alembic, pytest.

**Spec:** `docs/superpowers/specs/2026-09-20-qualification-cohorts-design.md`

## Global Constraints

- Additive changes only; preserve existing supply behavior.
- Exact immutable offer, profile, candidate, organization, recipient source, dossier, and evidence lineage.
- Exactly one result per profile criterion and at least one retained evidence reference per result.
- Stable deterministic rejection reason codes.
- Exactly 50 currently valid decisions and reservations in one cohort-freeze transaction.
- No stage registry, provider workflow, outreach, frontend change, or dependency.
- Never stage `frontend/AGENTS.md` or `frontend/CLAUDE.md`.

## Review Focus

- A matrix missing one criterion is rejected as `MISSING_CRITERION_RESULT`.
- A hard gate that is not satisfied is rejected as `FAILED_HARD_GATE`.
- A satisfied fatal-disqualifier criterion is rejected as `FATAL_DISQUALIFIER`.
- An expired supported contact or superseded offer is rejected with its exact stale reason.
- A protection conflict or any invalid member rolls back all cohort members and reservations.

---

### Task 1: Qualification and cohort persistence

**Files:**
- Create: `backend/src/alon_ai/records/qualification_models.py`
- Create: `backend/src/alon_ai/records/qualification_schema.py`
- Create: `backend/src/alon_ai/records/qualifications.py`
- Create: `backend/alembic/versions/20260920_09_qualification_cohorts.py`
- Create: `backend/tests/integration/test_qualification_cohorts.py`
- Modify: `backend/src/alon_ai/records/__init__.py`
- Modify: `backend/alembic/env.py`
- Modify: `docs/implementation/schema-manifest.json`

**Interfaces:**
- Consumes: accepted offer/profile/policy records, supply candidate/contact/qualification records, organization binding/admission/recipient-source/protection/reservation records, and record command helpers.
- Produces: `QualificationCohortRepository.record_dossier`, `QualificationCohortRepository.decide`, and `QualificationCohortRepository.freeze_cohort`, each returning replayable typed receipts.

- [ ] **Step 1: Write failing focused PostgreSQL tests**

Create fixtures that use the existing accepted-offer, supply, and organization helpers. Test successful exact matrix and 50-member freeze, missing evidence, failed hard gate, fatal disqualifier, stale contact, stale offer, protection conflict, transaction rollback, and command replay.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest backend/tests/integration/test_qualification_cohorts.py -q`
Expected: collection fails because the qualification contracts and repository do not exist.

- [ ] **Step 3: Add typed contracts, schema, migration, and repository commands**

Implement immutable dossier evidence and matrix/result tables, authoritative decision records with stable reason codes, exact supply qualification mirroring, and an atomic exact-50 cohort freeze that inserts existing organization reservations and record-command/audit/outbox receipts in one transaction.

- [ ] **Step 4: Run focused and existing persistence tests**

Run: `pytest backend/tests/integration/test_qualification_cohorts.py backend/tests/integration/test_offer_records.py backend/tests/integration/test_organization_records.py backend/tests/integration/test_campaign_supply.py -q`
Expected: all selected tests pass.

- [ ] **Step 5: Run migration and manifest verification**

Run: `pytest backend/tests/integration/test_migration_roundtrip.py backend/tests/integration/test_schema_manifest.py -q`, regenerate `docs/implementation/schema-manifest.json`, and rerun the same tests.
Expected: roundtrip and reviewed manifest pass at migration head `20260920_09`.

- [ ] **Step 6: Run static and full-suite verification**

Run the repository Ruff and Pyright commands, then run the full backend test suite once.
Expected: Ruff passes, Pyright reports zero errors, and the full backend suite passes.

- [ ] **Step 7: Commit, push, and document**

Stage only the checkpoint files, create one commit, push the current branch, and update L03 implementation evidence with the commit hash, verification results, and remaining L03 scope.
