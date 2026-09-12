# L02 Provider Governance Implementation Plan

> **For agentic workers:** Execute with subagent-driven-development. Read the live Notion task before relying on this implementation plan. This file does not replace the roadmap.

**Goal:** Implement every L02 configuration, provider, secret, budget, contact-source and campaign-supply acceptance gate with offline adapters and PostgreSQL-backed replay protection.

**Architecture:** Typed provider ports and deterministic policies sit behind one governed execution service. PostgreSQL owns budget reservations, usage reconciliation, quotas, circuit state, call identities and supply-command state. Production provider adapters and full product workflows remain with their later owning tasks; in-memory stores are test doubles only.

**Tech Stack:** Existing Python 3.13/FastAPI/Pydantic/SQLAlchemy/Psycopg/Alembic; exact Decimal arithmetic; cryptography AES-GCM for encrypted secret envelopes; pytest with real PostgreSQL integration checks. Retain the existing Next.js contract.

**Spec:** [L02](https://app.notion.com/p/3d6caf700cba8161adbce9744c53f31a), [active roadmap](https://app.notion.com/p/3d6caf700cba81dbb43fd57b1e534684), [stack](https://app.notion.com/p/3d9caf700cba8112b061dc1679344a05), [schema](https://app.notion.com/p/3d9caf700cba81e79d83d96a23e1d2aa). Dependency L01 is Done with commit `5795d55` and passing CI.

## Global constraints

- Work in the user's current local checkout on `codex/lean-foundation`; preserve unrelated untracked files and ignored prototype backup. User authorized implementation, commits and pushes in this directory.
- OpenAI is the sole generative provider. Firecrawl is limited to deterministic map/capture; no extract/summary/agentic fallback.
- No live provider calls, new credentials, real messages/bookings or fabricated grants. Fake fixtures contain synthetic, clearly identified evidence.
- Missing/expired/revoked/ambiguous/mismatched source grants deny use. No storage permission means no returned source content, snippets, rankings, raw responses or content fingerprints in DB/logs/checkpoints. Explicitly permitted transient official-source location remains a distinct purpose.
- All paid work requires versioned price/FX basis, attribution, reservation and every applicable cap before invocation. Unknown charges remain reserved/reconciling; no blind retry. Use Decimal/exact PostgreSQL numeric, never binary floats for money.
- Source presence is PRESENT/ABSENT/NOT_AVAILABLE. Only evidenced ABSENT unlocks Hunter discovery/enrichment. Verification is independent; failed Brave verification cannot unlock Hunter discovery.
- Fixed versioned supply policy: target50, per-batch new-business cap100, max3 total batches. Logical slots1 INITIAL,2 EMAIL_RETRY,3 QUALIFICATION_RETRY; slot2 may be skipped when initial supported-email supply already reaches50. Restart cannot reset counters. No slot4. Failed slot2 below50 stops. Slot3 requires sufficient supported emails and a qualification deficit. Every return consumes persisted feedback and materially changed discovery configuration. Stop untouched paid work at the50th accepted lead.
- Generic provider execution cannot grant Gmail/Calendar writes or any product transition. Preserve the existing SendGateway boundary; later gateways integrate through separate explicit authority.
- Tests cover adversarial inputs, concurrent caps, restart/replay, no-retention and negative paths. New persistent invariants require actual PostgreSQL tests.

## Task 1: Typed configuration and encrypted least-authority secrets

**Files:** modify `backend/src/alon_ai/config.py`, `backend/src/alon_ai/logging.py`, `backend/src/alon_ai/api/middleware/request_logging.py`, `backend/src/alon_ai/db/engine.py`, `backend/alembic/env.py`, relevant existing config/logging/alembic tests, `.env.example`, backend dependency manifests, and CI's synthetic-stack environment if required. Create `backend/src/alon_ai/security/secrets.py`, `backend/src/alon_ai/security/__init__.py`, `backend/tests/unit/test_secrets.py`.

**Consumes:** existing Settings/get_settings/create_engine interfaces. **Produces:** secret-safe Settings plus SecretStore protocol and an encrypted file-backed implementation scoped to explicitly allowed consumer/handle pairs; secret values return as SecretStr and never enter normal serialization. Encryption keys are supplied outside stored envelopes/backups. No consumers depend on an unreviewed implementation-specific format.

1. Write failing tests for malformed URL/log/provider values, missing explicit production settings, configuration repr/JSON/errors leaking DB/API/OAuth secrets, nested structured logs and foreign-logger messages, and existing valid percent-encoded DSNs.
2. Protect DB and DBOS credential URLs with SecretStr; adapt only exact consumers. Strictly validate PostgreSQL driver/database and allowed log levels. Add default-disabled provider mode and sole OpenAI generative selection. Production must require explicit non-example database configuration and HTTPS frontend origin; fake CI smoke should run as test, with separate production-settings unit tests.
3. Preserve existing no-outreach defaults and completeness checks. A flag or configured credential never authorizes provider work. Raw environment secret fields may remain development compatibility inputs, but production provider secret resolution uses opaque handles through the store.
4. Use the already locked cryptography50.0.1 as an explicit direct dependency. Implement AES-GCM envelope encryption with a fresh nonce, authenticated handle/consumer/key-version binding, owner-only directory/file permissions, atomic writes, bounded handle syntax, and rejection of symlinks/path traversal, wrong keys, tampering and unauthorized consumers. The external master key is never written alongside ciphertext. Include explicit key-version/rotation support without erasing access to earlier authorized versions during rotation.
5. Add recursive log redaction for sensitive keys, configured secret strings and credential-bearing URLs; strip exception payloads. Do not log raw provider output. Preserve existing safe correlation/request metadata. Sanitize unsafe object arguments before interpolation and redact formatted output afterward, including decoded credential query names. Request logs use trusted matched route templates or a fixed unmatched marker instead of arbitrary raw paths.
6. Prove secret round-trip, ciphertext-at-rest, permissions, denied consumer, tamper/wrong-key/swap, redacted error and key rotation behavior. Run unit tests, Ruff, Pyright, migration setup and API contract generation. Record exact results, then request task review before commit/push.

## Task 2: Provider contracts, source grants and offline adapters

**Files:** new `backend/src/alon_ai/providers/contracts.py`, `rights.py`, `fakes.py`, `fixtures/`; tests in `backend/tests/unit/test_provider_contracts.py` and `test_provider_rights.py`. Preserve `providers/gmail.py` compatibility.

**Produces:** strict versioned capability/provider registry; immutable CallAttribution, safe request metadata, typed provider errors/results; ProviderUsageGrant and deterministic decision including retention field scope and expiry; narrow OpenAI/Brave/Firecrawl/contact discovery/verification/Gmail/Calendar protocols and recorded synthetic fakes. No generic arbitrary tool payload allows a second generative API or write authority.

- Test every fake without network access, capability mismatch and unknown capability rejection, sole-AI provider and Firecrawl operation allowlists, grant freshness/account/plan/purpose/revocation/storage/outreach checks, retained-field minimization and transient mode.
- Shared execution/persistence interfaces must be frozen in the task report before dependent implementation.
- Enumerate providers OPENAI/BRAVE/FIRECRAWL/HUNTER/GMAIL/GOOGLE_CALENDAR and separate generation, Brave coverage/local/company discovery, deterministic map/capture, Hunter domain/finder/company/person/verification, Gmail read/send, and Calendar read/write capabilities. Derive provider/nature from the capability registry; a request cannot relabel a write as a read.
- CallAttribution contains experiment/workflow/operation-run IDs, a discriminated agent-run or explicit system-service actor, safe correlation/logical operation identity, immutable config version and aware deadline. Do not manufacture an agent UUID for deterministic work. Later repository-controlled scope resolution must choose budgets; the caller cannot provide an arbitrary subset.
- ProviderUsageGrant binds grant ID/version, provider/account/capability, exact plan/order-form/terms/purpose, approval actor/date, effective/expiry time, supporting evidence and explicit storage fields/retention policy. Revocation/review events are separate. A pure evaluator takes the current grant/events and trusted intended use, never treats a key or subscription label as permission, and returns typed denial/transient/scoped-retention decisions.
- Ordinary lead-discovery capability requires explicit outreach purpose and necessary storage rights; it cannot silently downgrade to a retaining consumer. Only an explicitly licensed OFFICIAL_SOURCE_IDENTIFICATION request may receive transient results without storage rights. Transient results must be nonserializable and safe in repr; no payload hash/cache key belongs in persisted metadata. Retention must re-evaluate current grants and exact allowed fields after completion.
- Deterministic Firecrawl request types enumerate formats/options and reject prompts, summaries, extract/agent endpoints or generative parsers. URLs may not carry credentials or private-network targets; no arbitrary HTTP method/body port. Future concrete adapters must also enforce DNS/redirect egress policy, which these offline request contracts do not pretend to implement.
- Contact observation distinguishes any Brave candidate PRESENT from evidenced ABSENT and unavailable NOT_AVAILABLE, binding business/source/observed-time/grant provenance. Keep separate verification status/policy and business-match references. A malformed or rejected Brave candidate remains PRESENT for fallback denial.
- Fixture adapters return typed usage/status data and provenance-labeled synthetic content. Keep runtime content outside generic serializable audit DTOs, safe external request IDs bounded, and raw upstream failure text out of raised errors. A narrow payload-consumption/retention method must enforce the evaluator; do not implement serialization that quietly copies transient data. Existing GmailProvider/SendRequest/SendResult compatibility remains intact.

## Task 3: PostgreSQL-backed budgets and governed provider execution

**Files:** new `backend/src/alon_ai/accounting/`, provider execution service, SQLAlchemy metadata/repositories and one initial governance Alembic migration; focused unit/integration tests. Register metadata in Alembic. Do not create the complete L03 product schema prematurely.

**Consumes:** Task2 contracts and Task1 secret resolver. **Produces:** transactional reserve/dispatch/reconcile/query API; exact usage and FX lineage; durable quota/concurrency/circuit state; safe immutable audit metadata. Attribution includes experiment/workflow/agent/operation run and reservation; operation run distinguishes research, discovery, enrichment and verification.

- Require all applicable global/experiment/workflow/run/provider caps, exact currencies and current price/FX versions. Lock accounts in deterministic order. Conservative ceiling-rounded reservation, exact sub-cent accrual and explicit settlement prevent zero-cost rounding or double charging.
- Same idempotency key plus same safe request returns prior identity/state; different request conflicts. Commit reservation and dispatch intent before provider call. Never hold a SQL transaction across HTTP. Timeout/cancellation/crash ambiguity quarantines cost/retry; proven pre-call cancellation may release.
- Typed errors never retain raw provider content/secrets. Persist result content only through an explicit valid retention decision; transient results are not replay-cached in durable provider records.
- Test concurrent reservations and leases, quota/circuit failure/half-open behavior, timeout, crash/restart, uncertain/final/overrun reconciliation, cross-scope/currency conflicts, repeated settlement and omission of forbidden data using real PostgreSQL.

## Task 4: Replay-safe campaign-supply policy

**Files:** new `backend/src/alon_ai/policies/campaign_supply.py`, associated application service/repository/migration and unit/integration tests.

**Consumes:** persisted per-experiment state and Task3 command transaction conventions. **Produces:** finite deterministic admission/reconciliation/feedback policy for logical batch slots, per-candidate processing and early-stop decisions; no business discovery adapter or campaign activation yet.

- Persist identity of every admitted candidate and batch command; enforce uniqueness, cap100 and total<=300, fixed target50, max3 attempts and denied slot4 before provider access.
- Require all applicable contactability outcomes before expensive research, enough supported email supply, terminal reason-coded qualification and exact count deduplication. EMAIL_NOT_FOUND never admits enrichment. A50th accepted qualified contactable lead stops untouched work atomically.
- Persist immutable failure feedback with source batch/reasons/deficit and exact prior/new planning configuration; retry requires material change within accepted constraints, never weakening qualification rules.
- Prove logical slots1only,1→2,1→3 and1→2→3, insufficient-email hard stop, qualification-only slot3, concurrent commands, snapshot reopen/restart and replay without resetting counts.

## Task 5: Governed contact-source resolution

**Files:** new contactability application policy/service and tests; no direct Gmail/Calendar or arbitrary research paths.

**Consumes:** Task2 provider contracts/grants and Task3 governed calls; Task4 paid-work eligibility. **Produces:** strict source-precedence result with immutable source/date/verification/business-match lineage, permitted diagnostic attempts and avoided-Hunter accounting metadata.

- PRESENT Brave email → verification only, no Hunter discovery/enrichment even on failure. ABSENT → bounded Hunter fallback then separate verification. NOT_AVAILABLE → typed nonterminal pause/denial, never assumed absence.
- Only current valid verification and exact organization-match evidence support an address. Invalid, unknown, catch-all, stale or unproven results do not count. No guessed email fills missing evidence. Distinguish EMAIL_NOT_FOUND from provider failure.
- Verify source/rights/eligibility before every paid branch; limit fallback attempts and record caps/timeout/reconciliation through Task3. Test actual fake invocation counts, absence of network, no content retention without grants and avoided cost attribution.

## Task 6: Integrated acceptance, evidence and Notion completion

**Files:** exact integration fixes, `docs/implementation/l02-provider-governance.md`, local runbook/environment reference, README implementation inventory.

- Map every L02 requirement to meaningful tests and current source; inspect gaps rather than infer coverage from test names.
- Run fresh PostgreSQL migrations, all backend tests and type/lint gates, generated OpenAPI checks, frontend checks, package/container builds and smoke tests as affected.
- Independently review the full L02 diff for security, races, stale grants, no-retention, state replay, precision and scope. Fix concrete blockers and rerun covering checks.
- Commit/push verified steps with bounded staging; wait for GitHub CI. Update Graphify structurally and changed-doc semantics, preserving current results after the known lossy hook normalization.
- Record exact commit/CI/test evidence in Notion. Mark L02 Done only after all gates pass, promote the next dependency-satisfied task and continue under the active goal.
