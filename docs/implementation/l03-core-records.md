# L03 product-record evidence

[Founder OS L03](https://www.notion.so/3d6caf700cba81a69cbcf699284206f7) owns the requirements and task status. This file records implementation evidence; it does not replace the roadmap.

## Product roots and immutable lineage

The first implementation checkpoint adds product experiment, workflow and agent details using the existing governance identities. The record layer stores immutable, versioned artifacts and explicit input/evidence relationships. Research recommendations remain proposals until a deterministic command commits a verdict. The record layer now covers user-seeded and explicitly selected system-discovery origins, operator profile ownership and bounded research returns; the remaining L03 paths are listed below.

Database guards preserve the original seed, require contiguous cycles with a committed return, and require an accepted idea before a research attempt. Plans pin their accepted idea, reports pin their plan, recommendations pin their report, and passing validations pin their exact target. Acceptance freezes the artifact's input/source set and its consumed ancestors. A full command fingerprint makes changed-request retries conflict while identical retries return their original receipt. Invalid payloads, including SQL NULL validation results, fail closed.

The migration roundtrip test creates a disposable PostgreSQL database through the existing fixture, rolls the complete migration chain back to an empty application schema, then reapplies it and compares all tables, columns, constraints, indexes, triggers and functions. It never alters an existing project database.

Source references must not duplicate provider text or prevent licensed content from expiring. The existing governance retention boundary remains responsible for permitted content, current grant checks, licensed reads and purge. Retained historical lineage does not authorize cross-experiment research reuse.

## Operator profiles and explicit research origins

Frozen migrations `20260913_05` and `20260913_06` add bound operator identities, immutable delivery/commercial profile versions, exact candidate selections and typed research returns. Authorization follows the active profile owner; descriptive skill labels do not grant permission. Legacy profiles retain their hashes and receive disabled, unbound identity records until explicitly bound. Authentication and allowlisting remain the responsibility of the later authentication task.

System discovery requires an explicit selection of the exact candidate and does not fabricate a user seed. Both first-refinement and later material pivots require exact operator approval. Same-intent returns are capped at two on the original lineage, inconclusive supplements at one per governed episode, and material pivots are tracked separately. Return feedback pins the accepted idea, report and recommendation; subsequent plans pin that feedback. Offer-gap records and their one-return constraint are present, but activation requires the real accepted Offer Design input bundle in the next offer checkpoint.

## Verification

Independent review identified and closed cycle/return bypasses, late changes to accepted lineage, raw attempts without an accepted idea, conflicting command replays, unrelated validation targets and SQL NULL validation. The corrected checkpoint passed 43 focused PostgreSQL checks covering the record commands, direct database guards, migration roundtrip and schema inventory. Ruff checked 74 formatted files and Pyright reported zero diagnostics. The preceding full backend regression run passed 638 tests; GitHub CI verifies the complete committed snapshot and links its result from Founder OS.

The frozen `20260912_04` migration adds 17 product tables without importing mutable application metadata. With the two subsequent migrations, the full inventory has 58 tables, 486 columns, 816 constraints, 218 indexes, 629 triggers and 30 functions. These counts are structural evidence; the behavioral checks above establish the implemented gates.

Local PostgreSQL integration tests use the isolated validation service on port55432. The fixture creates and drops only its own random test database. GitHub CI uses its own PostgreSQL service.

```sh
cd backend
ALON_AI_DATABASE_URL=postgresql+psycopg://alon_ai:alon_ai@localhost:55432/alon_ai uv run pytest tests/integration/test_product_records.py tests/integration/test_product_record_guards.py tests/integration/test_migration_roundtrip.py tests/integration/test_schema_manifest.py -q
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

The operator/origin checkpoint passed 55 focused PostgreSQL tests, including clean migration rollback and reapplication; Ruff and Pyright passed.

L03 remains incomplete until its other record families and gates pass: complete offer and offer-research-return activation, organization/contact protection, qualification/cohort, outreach/conversation/handoff and learning persistence. Live agents, provider integrations and workflows belong to their later owning tasks. No fixture result establishes real sending, booking or commercial authority.
