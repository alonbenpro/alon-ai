# L03 lead readiness

Authority: [L03](https://www.notion.so/3d6caf700cba81a69cbcf699284206f7),
[discovery](https://www.notion.so/3d6caf700cba81aea8a2f2fa010e71bb),
[research/contactability](https://www.notion.so/3d6caf700cba81099597f6f16246f7f0),
and [offer calibration](https://www.notion.so/3d6caf700cba814db696cea2a5fc0469).

This checkpoint adds persistence and deterministic eligibility coordination. It
uses existing governed execution receipts; it introduces no provider transport,
credentials, sending, conversations, handoffs, learning, or frontend behavior.

## Retained history and current eligibility

Discovery and research records pin the existing supply batch/candidate, accepted
offer/profile/policy, artifact versions/hashes, and permitted source provenance.
Contact records reuse organization/recipient identity, source observations,
contact attempts and verification receipts. Provider content remains under the
existing retained-content grant, expiry and purge controls. Independent evidence
keeps its own source identity; transient Brave content is not copied into durable
facts.

Qualification dossiers, matrices and decisions remain append-only. The original
`supply_qualifications` row is preserved; `record_current_supply_qualifications`
projects the latest decision and current offer/contact/protection eligibility.
Historical target outcomes remain historical. Superseded passing decisions do
not revive when a newer decision fails. Cohort and outreach guards require the
current decision. Fixed-50 targeting, batch limits and feedback ownership remain
with the existing supply subsystem.

## Calibration boundaries

Only an accepted calibration awaiting fulfillment blocks cohort freeze. A
proposal, rejection or insufficient-evidence decision does not block normal work.
Acceptance requires repeated, evidenced mismatch across distinct otherwise-fit
leads and is limited to one accepted calibration before cohort freeze.

Calibration does not accept an offer. A calibrated package goes through the
existing offer validators and pins the authorizing calibration decision; the
original package is retained. Fulfillment pins the resulting accepted offer,
profile and policy and creates explicit affected-lead requalification lineage.
Requalification appends a new dossier/matrix/decision; a successful current result
can fulfill its obligation, while a rejected result remains excluded.

Commands use existing replay keys, request hashes, receipts, audit and outbox
records. Provider calls occur outside transactions. Calibration acceptance and
its affected set, fulfillment and obligations, qualification and completion,
and cohort freeze and reservations each commit atomically.

## Migration boundary

Migration `20260920_10` follows `0d1db464e1c2`. Clean-database downgrade and upgrade
are supported. Downgrade refuses before changing schema if calibrated offers or
appended requalification decisions exist: the previous schema cannot represent
that immutable history. It does not delete historical records to force rollback.

## Verification

All commands below ran from `backend/` using the existing virtualenv and isolated
PostgreSQL on port 55432.

- Focused readiness/contact/lineage/calibration/qualification/outreach checks:
  **14 passed in 146.75s**.
- Migration roundtrip, schema-manifest checks, and the final discovery/research
  lineage rerun: **5 passed in 17.44s** (three migration/manifest checks plus two
  lineage checks). Manifest head: `20260920_10`; 124 tables.
- Ruff check: passed. Pyright using `--pythonpath .venv/bin/python`: **0 errors,
  0 warnings, 0 informations**.
- The full backend suite ran **exactly once**: **710 passed, 1 failed in 445.61s**.
  The only failure was `test_real_postgres_is_ready`: the runner omitted the
  required `ALON_AI_DATABASE_URL` environment variable, causing `KeyError` before
  the database check. The unchanged test was rerun with the isolated local
  database URL configured: **1 passed in 0.12s**. No code change or second full
  run was used to resolve that environment-only failure.

Reproduction commands:

```sh
.venv/bin/pytest tests/integration/test_readiness_records.py tests/integration/test_readiness_lineage.py tests/integration/test_readiness_eligibility.py tests/integration/test_calibration_records.py tests/integration/test_qualification_cohorts.py -q
.venv/bin/pytest tests/integration/test_migration_roundtrip.py tests/integration/test_schema_manifest.py tests/integration/test_readiness_lineage.py -q
.venv/bin/ruff check .
.venv/bin/pyright --pythonpath .venv/bin/python
# Set ALON_AI_DATABASE_URL to the isolated local test database before a full run.
.venv/bin/pytest -q
.venv/bin/pytest tests/integration/test_database_readiness.py -q
```

The focused tests cover governed verifier success, invalid/unknown/catch-all
no-email decisions, exact discovery inputs and receipt replay, revoked source
rights, retained-content references instead of copied provider text, stale
research output, immutable requalification history, pending-calibration gates,
and a complete 50-lead calibrated-offer/requalification/cohort freeze. A populated
history downgrade refusal is checked without losing records.

At this lead-readiness checkpoint, L03 remained in progress. Conversation,
handoff, checkpoint, and learning persistence were completed in subsequent L03
checkpoints. Live execution belongs to later roadmap tasks.
