# L02 provider governance evidence

The L02 foundation is implemented. Founder OS remains the roadmap authority; this file records implemented boundaries and verification, not a replacement plan. The task's completion entry links the final commit and CI result.

## Implemented foundation

| Boundary | Implementation | Evidence |
| --- | --- | --- |
| Settings and secrets | Strict production settings; disabled defaults; AES-GCM envelopes bound to consumer/handle; rotation and sanitized logging | `5ef6879`; configuration, secrets and logging tests |
| Provider contracts | Typed capabilities, exact versioned grants, deterministic Firecrawl requests, separate discovery/verification ports and packaged synthetic fixtures | `a93152a`, JSON hydration correction `2c00b15`; provider contracts/rights tests |
| Cost and execution | PostgreSQL reservations across all applicable native/ILS accounts; immutable price/FX/usage provenance; unknown-cost exposure, reconciliation, quota/concurrency/circuit state and governed dispatch | `34d3063`; accounting tests and real PostgreSQL governance tests |
| Supply | Fixed target50, up to100 new unique candidates per logical batch, slots1/2/3 with feedback, terminal shortage rules, contactability-first processing, replay and atomic final acceptance | `6bec9d6`; 56 scoped checks and 599 full backend tests passed before contact integration |
| Contact policy | Governed results determine source presence and verification status; Brave PRESENT blocks all four Hunter discovery/enrichment capabilities; ABSENT permits fallback; NOT_AVAILABLE pauses; verification remains separate | `test_contact_adapters.py` and `test_contact_policy.py`; real PostgreSQL, offline invocation counts, false-label rejection, current-rights checks and immutable proof lineage |
| Schema integrity | Fresh migrations are compared with an explicit structural inventory, including database guards | `test_schema_manifest.py`; deliberate column/index/trigger drift is detected |

The supply commit passed [all four CI jobs](https://github.com/alonbenpro/alon-ai/actions/runs/34715186767). Review reproduced and closed a contact-gate downgrade and an expired accepted-contact dependency gap. The final suite observes actual PostgreSQL lock waits, protected-candidate denial, exact final-slot contention, low-yield feedback and post-target reconciliation.

CONTACT operations require `ComposedContactSupplyHook` with an explicit contact-policy owner. Standalone `SupplyAdmissionHook` only owns SUPPLY. Both use the accounting transaction's experiment fence. Call deadlines cannot exceed the validity of any required proof, including the supported-email quorum and previously accepted members.

Contact ingestion derives labels from licensed runtime content inside the ingestion method; a caller cannot substitute an ABSENT or VALID label. Final contact resolution locks the relevant authorities, checks exact current Brave/Hunter/verifier grants and materializes the supply result in one transaction. Admission deadlines are bounded by source/attempt expiry, scheduled invalidation events and future grant activation so a later accounting lock wait cannot outlive the source authority. Invalid, accept-all and unknown verification are rejected; temporary provider failure remains nonterminal. Avoided-Hunter calls are recorded without inventing monetary savings when a valid counterfactual price is unavailable.

## Schema inventory

`schema-manifest.json` records the reviewed Alembic heads and every public application table, column, constraint, index, trigger and function. `alon_ai.db.schema_manifest` reads structure only. The integration check compares a fresh migrated database to that committed inventory and proves that added columns/indexes and disabled guards are detected.

Internal PostgreSQL trigger names contain database-specific OIDs, so the inventory records their stable constraint, function, event and enablement properties. It excludes application rows, credentials, object OIDs and environment-specific owners. It is a drift check alongside behavioral tests, not proof of business semantics or deployment privileges. Catalog definitions follow PostgreSQL18's [constraint](https://www.postgresql.org/docs/18/catalog-pg-constraint.html) and [trigger](https://www.postgresql.org/docs/18/catalog-pg-trigger.html) references.

Regenerate deliberately from a fresh disposable database after reviewing migration changes, using the configured `ALON_AI_DATABASE_URL`:

```sh
cd backend
uv run python -m alon_ai.db.schema_manifest --write ../docs/implementation/schema-manifest.json
uv run pytest tests/integration/test_schema_manifest.py -q
```

## Local verification and boundaries

The final integration run passed 625 backend tests, Ruff, Pyright and package builds. Focused PostgreSQL regressions additionally cover the final scheduled-authority/dependency deadline correction; GitHub CI runs the complete committed snapshot, frontend checks, secret scan and container migration/startup smoke checks. Generated API contracts are unchanged.

The integration fixture creates and removes only its own random `alon_ai_test_<uuid>` databases; its validation role needs `CREATEDB`. Local integration tests require PostgreSQL on port55432 because an unrelated database may occupy5432. GitHub CI uses its own ephemeral PostgreSQL service.

```sh
cd backend
ALON_AI_DATABASE_URL=postgresql+psycopg://alon_ai:alon_ai@localhost:55432/alon_ai uv run pytest tests -q
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Do not globally override `ALON_AI_ENVIRONMENT` for this suite: configuration tests also verify development defaults. Synthetic credentials and fixtures above grant no real provider or business authority.

The governance/supply roots are explicitly provisional internal records. Later owning tasks bind real organizations, current global contact protection, offers, full qualification and final cohorts. Current fake success cannot send, book or advance business state. Production grants, prices, FX, credentials and retention policies are not fabricated. Live adapters, DBOS workflows and the operator UI remain with their owning roadmap tasks.
