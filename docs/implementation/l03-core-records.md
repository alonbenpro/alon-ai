# L03 product-record evidence

[Founder OS L03](https://www.notion.so/3d6caf700cba81a69cbcf699284206f7) owns the requirements and task status. This file records implementation evidence; it does not replace the roadmap.

## Product roots and immutable lineage

The first implementation checkpoint adds product experiment, workflow and agent details using the existing governance identities. The record layer stores immutable, versioned artifacts and explicit input/evidence relationships. Research recommendations remain proposals until a deterministic command commits a verdict. This checkpoint covers seeded research lineage; the remaining L03 paths are listed below.

Database guards preserve the original seed, require contiguous cycles with a committed return, and require an accepted idea before a research attempt. Plans pin their accepted idea, reports pin their plan, recommendations pin their report, and passing validations pin their exact target. Acceptance freezes the artifact's input/source set and its consumed ancestors. A full command fingerprint makes changed-request retries conflict while identical retries return their original receipt. Invalid payloads, including SQL NULL validation results, fail closed.

The migration roundtrip test creates a disposable PostgreSQL database through the existing fixture, rolls the complete migration chain back to an empty application schema, then reapplies it and compares all tables, columns, constraints, indexes, triggers and functions. It never alters an existing project database.

Source references must not duplicate provider text or prevent licensed content from expiring. The existing governance retention boundary remains responsible for permitted content, current grant checks, licensed reads and purge. Retained historical lineage does not authorize cross-experiment research reuse.

## Verification

Independent review identified and closed cycle/return bypasses, late changes to accepted lineage, raw attempts without an accepted idea, conflicting command replays, unrelated validation targets and SQL NULL validation. The corrected checkpoint passed 43 focused PostgreSQL checks covering the record commands, direct database guards, migration roundtrip and schema inventory. Ruff checked 74 formatted files and Pyright reported zero diagnostics. The preceding full backend regression run passed 638 tests; GitHub CI verifies the complete committed snapshot and links its result from Founder OS.

The frozen `20260912_04` migration adds 17 product tables without importing mutable application metadata. The full inventory now has 56 tables, 454 columns, 766 constraints, 204 indexes, 582 triggers and 23 functions. These counts are structural evidence; the behavioral checks above establish the implemented gates.

Local PostgreSQL integration tests use the isolated validation service on port55432. The fixture creates and drops only its own random test database. GitHub CI uses its own PostgreSQL service.

```sh
cd backend
ALON_AI_DATABASE_URL=postgresql+psycopg://alon_ai:alon_ai@localhost:55432/alon_ai uv run pytest tests/integration/test_product_records.py tests/integration/test_product_record_guards.py tests/integration/test_migration_roundtrip.py tests/integration/test_schema_manifest.py -q
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

L03 remains incomplete until its other record families and gates pass: explicit system-discovery candidate selection without a fabricated user seed; bounded inconclusive/offer-research returns; offer, organization/contact protection, qualification/cohort, outreach/conversation/handoff and learning persistence. Live agents, provider integrations and workflows belong to their later owning tasks. No fixture result establishes real sending, booking or commercial authority.
