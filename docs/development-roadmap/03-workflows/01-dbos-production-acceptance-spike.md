# DBOS Gmail Production-Acceptance Spike

**Document ID:** WF-01
**Status:** Planned mandatory M1 experiment; no harness or send exists today
**Milestone:** M1
**Owner:** Solo operator
**Prerequisites:** accepted M0 scope/risk/metrics, [WF-00](00-dbos-selection-and-temporal-fallback.md), [ARCH-01 M1/M2 ruling](../01-architecture/01-target-system-architecture.md#persistence-boundaries-and-the-m1m2-ruling), isolated Gmail test project/credentials, and operator-owned test inbox aliases
**Outputs:** Kill-point harness, two-table disposable ledger, DBOS recovery/version/queue/control evidence, ambiguity reconciliation traces, and binary 8/8 gate decision
**Unlocks:** DBOS production acceptance or immediate mandatory Temporal migration
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

M1 proves the dangerous primitive before product data/workflows exist: a finite DBOS workflow can survive crashes and controls around an externally ambiguous Gmail send without uncontrolled duplicates or blind retries. The harness has no prospect, campaign, offer, approval, artifact, or product experiment table. Its only recipients are allowlisted aliases owned by the operator.

Passing M1 accepts DBOS mechanics only. Product outreach remains off until M6 also passes; real recipients remain blocked until later separate authority.

## Current repository state

DBOS and Pydantic AI dependencies are installed, but no workflow/queue/harness/agent fixture exists. Gmail configuration fields exist, but no OAuth, adapter, history/Sent reconciliation, or actual send exists. The worker is idle and the database has no product/spike table.

## Scope and non-goals

In scope: smallest disposable schema, one typed Pydantic AI fixture artifact, stable Gmail identity, `SendGateway` policy stub limited to test aliases, DBOS workflow/steps/queue/timer/versioning/recovery, eight criteria, kill points, repeated concurrency, evidence export, and cleanup. Non-goals: product schema, real prospects, reusable campaign code, polished UI, product outreach, agent-chosen recipients/content, or a provider exactly-once claim.

## Exact planned implementation surfaces

Create M1-only `backend/tests/production_acceptance/dbos_gmail/` harness modules/fixtures and worker entry point. None becomes a product module by copy. Register queue `m1-spike-send-v1` with global concurrency `1` and a pinned start-rate limit from the scenario manifest; verify the effective database-backed configuration before every run. Use stable DBOS workflow ID `m1:{scenario_name}:v{workflow_version}:run:{run_id}` and stable send idempotency key `m1:{scenario_name}:{run_id}:send:1`. The RFC `Message-ID` is derived deterministically from that key and a test-only controlled domain.

### Only permitted schema

Create schema `m1_spike` containing exactly:

- `spike_runs(run_id uuid primary key, scenario_name text, workflow_version text, state text, started_at timestamptz, finished_at timestamptz)`; and
- `spike_send_attempts(idempotency_key text primary key, run_id uuid references m1_spike.spike_runs, recipient_alias text, state text, rfc_message_id text, gmail_message_id text, gmail_thread_id text, attempted_at timestamptz, reconciled_at timestamptz)`.

Constraints: unique `rfc_message_id`; recipient alias must exist in the immutable operator-owned allowlist fixture; run state is `PENDING/RUNNING/PAUSE_REQUESTED/PAUSED/CANCEL_REQUESTED/CANCELLED/SUCCEEDED/FAILED`; attempt state is `INTENT_RECORDED/SENDING/AMBIGUOUS/RECONCILING/SENT/FAILED_CONCLUSIVE/CANCELLED`; provider IDs are both present for `SENT`; `reconciled_at` is present only after reconciliation. No third table or extra column is permitted. Scenario, policy, queue, typed-agent, kill schedule, expected Sent query, and evidence metadata live in immutable signed fixture/output files.

### Exact append-only evidence-file contract

The bundle is a filesystem protocol, never a third table. One run exclusively
creates `m1-gmail-evidence.v1-{bundle_id}`, with lowercase canonical UUID
`bundle_id`. Its only authoritative files, in manifest order, are:

1. `tables/spike_runs.v1.ndjson`;
2. `tables/spike_send_attempts.v1.ndjson`;
3. `streams/evidence_records.v1.ndjson`; and
4. `manifest.v1.json`, written last as the sole commit marker.

All NDJSON is UTF-8 without BOM. Every RFC 8785 canonical JSON record ends in
exactly one LF byte, including the final record; CR, blanks, trailing spaces,
alternate normalization, or a missing final LF is invalid. SQL `NULL` becomes
JSON `null`; UUIDs are lowercase `8-4-4-4-12`; timestamps are UTC
`YYYY-MM-DDTHH:MM:SS.ffffffZ` with six fractional digits; strings retain their
Unicode scalar sequence; integers use JSON integer notation. JSONB is parsed and
canonicalized as JSON, never hashed from PostgreSQL display text. Duplicate keys,
invalid Unicode, NaN, infinity, and non-I-JSON numbers fail export.

`spike_runs.v1.ndjson` records are exactly
`{run_id,scenario_name,workflow_version,state,started_at,finished_at}`, including
nullable `finished_at`, ordered by canonical run-ID ASCII bytes.
`spike_send_attempts.v1.ndjson` records are exactly
`{idempotency_key,run_id,recipient_alias,state,rfc_message_id,gmail_message_id,gmail_thread_id,attempted_at,reconciled_at}`,
including nullable provider/timestamp fields, ordered by raw UTF-8
`idempotency_key` bytes. Both exports use one repeatable-read, read-only
transaction and include every row.

Each evidence-stream core is exactly: `evidence_schema_version` literal
`m1.evidence-record.v1`; canonical `record_id` and `run_id`; positive
`sequence`; `prior_record_hash` null only at sequence 1 otherwise lowercase
64-hex; strings `scenario_name`, `workflow_version`, `kill_point`,
`record_type`, `occurred_at`, `idempotency_key`, `mailbox_alias`,
`rfc_message_id`; spike `attempt_state`; `provider_outcome` in
`NOT_CALLED/ACCEPTED/CONCLUSIVE_FAILURE/AMBIGUOUS/RECONCILED_SENT/RECONCILED_ABSENT/CONFLICT`;
nullable `error_code`, 64-hex `error_fingerprint`, `gmail_message_id`,
`gmail_thread_id`, and 64-hex `response_hash`; required 64-hex `request_hash`;
`candidate_matches`; literal `signature_algorithm="Ed25519"`; and
`signer_key_id`. A candidate is exactly
`{mailbox_alias,gmail_message_id,gmail_thread_id,rfc_message_id,observed_at,envelope_fingerprint,header_hash}`;
candidates sort by the raw UTF-8 tuple of their first four fields.

`signer_key_id` is `ed25519-sha256:<64 lowercase hex>`, SHA-256 of the raw
32-byte public key. Let `C` be RFC 8785 UTF-8 core bytes including algorithm
and key ID, excluding only `record_hash` and `signature`.
`record_hash=hex(SHA-256(C))`. The signature preimage is ASCII
`alon-ai:m1:evidence-record:v1\n` immediately followed by the raw 32 digest
bytes. `signature` is unpadded RFC 4648 base64url of the 64 Ed25519 bytes.
The final NDJSON record is the core plus `record_hash` and `signature`;
record N's prior hash equals record N-1's hash.

`manifest.v1.json` is exactly
`{manifest_schema_version:"m1.manifest.v1",bundle_id,run_id,scenario_name,workflow_version,fixture_hash,queue_config_hash,control_config_hash,final_state,created_at,files,signature_algorithm:"Ed25519",signer_key_id,signature}`.
`files` contains exactly the first three paths above in order. Each entry is
`{path,media_type:"application/x-ndjson",schema_version,row_count,size_bytes,sha256}`;
schema versions are `m1.spike-runs.v1`, `m1.spike-send-attempts.v1`, and
`m1.evidence-records.v1`. Every digest covers raw bytes including final LFs.
The manifest signature preimage is ASCII `alon-ai:m1:manifest:v1\n` plus raw
SHA-256 bytes of RFC 8785 manifest content excluding only `signature`.
The manifest has no BOM or trailing LF.

Golden signature fixture: test-only private seed
`000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f`;
raw public key `03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc8664125531b8`;
key ID `ed25519-sha256:56475aa75463474c0285df5dbf2bcab73da651358839e9b77481b2eab107708c`.
Its exact core values are:

| Field | Exact JSON value |
| --- | --- |
| `evidence_schema_version` | `"m1.evidence-record.v1"` |
| `record_id` | `"00000000-0000-4000-8000-000000000001"` |
| `sequence` / `prior_record_hash` | `1` / `null` |
| `run_id` | `"00000000-0000-4000-8000-000000000002"` |
| `scenario_name` / `workflow_version` | `"k4-ambiguous"` / `"1"` |
| `kill_point` / `record_type` | `"K4"` / `"PROVIDER_OUTCOME"` |
| `occurred_at` | `"2026-08-28T12:34:56.000000Z"` |
| `idempotency_key` | `"m1:k4-ambiguous:00000000-0000-4000-8000-000000000002:send:1"` |
| `mailbox_alias` / `rfc_message_id` | `"owned-test-1"` / `"<m1-k4@example.test>"` |
| `attempt_state` / `provider_outcome` | `"AMBIGUOUS"` / `"AMBIGUOUS"` |
| `error_code` | `"TIMEOUT"` |
| `error_fingerprint` | lowercase hex `11` repeated 32 times |
| `gmail_message_id` / `gmail_thread_id` | `null` / `null` |
| `request_hash` / `response_hash` | lowercase hex `22` repeated 32 times / `null` |
| `candidate_matches` | `[]` |
| `signature_algorithm` | `"Ed25519"` |
| `signer_key_id` | the key ID above |

Expected record hash is
`33308416927a8fb8155309709c62131c44e45ed8df97830f89e0b2b2baf8f711`;
expected signature is
`RHskwux8dDdTY0rNBzUL88u6CYPhgpaVhlvjrce8H8Vwgazc9oCHLCXFXBhTzN9l_BSc-ZzExJRTq4mVmfYjCg`.
Independent writers/verifiers must reproduce identical bytes and values.

The writer exclusively creates the final directory and fsyncs its parent. For
each data file in manifest order it creates `<path>.tmp` exclusively, writes,
fsyncs the file, closes, atomically renames to `<path>`, then fsyncs the
containing directory. After rereading and validating every digest/signature it
writes `manifest.v1.json.tmp`, fsyncs/closes, renames to `manifest.v1.json`,
fsyncs the bundle directory, then fsyncs its parent. Nothing is overwritten.

No manifest means `PARTIAL_EVIDENCE`: preserve all bytes and temp files, disable
the gateway, and restart export under a new bundle ID. With a manifest, validate
exact names/no extras, encoding/LFs, sizes/digests, counts/order/schema, key ID,
hash chain, candidate order, all signatures, and manifest signature before
semantic reads. A gap, duplicate, malformed null/UUID/timestamp/JSONB, bad
signature/hash, conflicting candidate, impossible outcome, extra path, or temp
file is `CORRUPT_EVIDENCE`; no repair, retry, or send is allowed.

Restore imports both table files into an empty exact two-table schema, checks
constraints, re-exports, and requires byte-for-byte equality and equal raw
digests. It replays evidence by sequence, compares ledger/provider candidates,
and requires the same final state before schema disposal.

### Finite workflow and authority

The DBOS workflow loads immutable fixture by `scenario_name`, obtains a typed Pydantic AI output from a deterministic local fixture model, validates the recipient alias/content, writes intent, enqueues/executes one guarded send step, records result or ambiguity, reconciles when needed, and terminates. The fixture agent cannot receive Gmail tools. The workflow cannot call Gmail: it invokes an M1 `SendGateway`, which rechecks harness-enabled flag, alias allowlist, cancellation/pause, rate/queue evidence, stable key, and attempt state before the Gmail adapter.

### Kill points

| ID | Process termination point | Required durable outcome before recovery may progress |
| --- | --- | --- |
| `K0` | before `spike_runs` insert | restart may create the same run only through the command key; no send |
| `K1` | after run commit, before enqueue | one run; recovery/enqueue remains idempotent |
| `K2` | after attempt intent commit, before dequeue | one intent/key/RFC ID; no provider call until gateway recheck |
| `K3` | after gateway policy/allowlist recheck, before Gmail call | attempt may restart only after durable state inspection; no duplicated start record |
| `K4` | after request bytes leave process, before response is known | attempt is `AMBIGUOUS`; blind retry forbidden; Sent reconciliation required |
| `K5` | after Gmail accepted/returned IDs, before local `SENT` commit | `AMBIGUOUS`; reconcile stable RFC ID/Gmail evidence before completion |
| `K6` | after `SENT` commit, before workflow completion | recovery replays result and makes no Gmail call |
| `K7` | during Sent reconciliation before local resolution | remains `RECONCILING/AMBIGUOUS`; restart resumes bounded reconciliation |
| `K8` | during concurrent dequeue/rate window and worker replacement | concurrency/rate bound remains unbroken globally |

The harness injects deterministic barriers and hard process termination, not exceptions that DBOS handles in-process.

### Eight-item scenario/evidence matrix

| Criterion | Required scenario and pass evidence | Disqualifying result |
| --- | --- | --- |
| restart recovery | every K0-K8 with cold worker/database connection recovery, repeated from clean schema | stuck/lost run, unbounded replay, manual DB edit, or missing completion/recovery state |
| cancellation | cancel before enqueue, queued, before provider, ambiguous, reconciling; zero post-confirmation provider calls | cancellation cannot reach bounded visible state or a provider call starts after confirmed control bound |
| ambiguous reconciliation | K4/K5/K7; query Sent by stable RFC ID plus fixture envelope; 100% ambiguity reaches conclusive/operator-visible state | blind retry, hidden ambiguity, cursor/evidence loss, or inability to distinguish zero/one/multiple candidates |
| duplicate prevention | repeated commands, worker races, K4/K5, duplicate queue delivery; compare inbox/Gmail IDs/RFC IDs/ledger | more than one message for one intent or ledger/provider divergence |
| workflow versioning | deploy breaking v2 with v1 in flight; exercise DBOS patch/version plus blue-green drain/recovery | nondeterminism, stranded run, wrong-version recovery, or manual history mutation |
| observability | correlate run, workflow version, queue, control, key, attempt, provider result, reconciliation, kill point, recovery | any step cannot be reconstructed without secrets/raw-address leakage |
| operator control | pause/resume/cancel/inspect from operator CLI while queued/running/reconciling | new provider call after confirmed pause/cancel bound or unsafe resume without gateway recheck |
| rate-limit under restart/concurrency | multiple workers/requests across K8 and rate-window boundary; measure starts from adapter evidence | configured global concurrency/rate start limit exceeded or reset by restart/version process |

Each scenario runs the approved repetition count with zero uncontrolled duplicates, zero blind retries, and no missing trace. Any flake is failure until root cause is proven and the complete suite reruns clean from a fresh schema.

### Ambiguous resolution algorithm

On unknown provider outcome, persist/retain `AMBIGUOUS`; schedule bounded reconciliation; transition to `RECONCILING`; search the Sent mailbox using the stable RFC ID and expected safe envelope/time bounds; capture every candidate's Gmail IDs/fingerprint; resolve `SENT` only for one conclusive match. Zero candidates before the full provider-consistency window remains ambiguous; conclusive absence after the window may become `FAILED_CONCLUSIVE` and only then can a bounded retry scenario be tested with the same key policy. Multiple/conflicting candidates stop sending, preserve evidence, and require operator-visible failure. No timeout alone proves no send.

## Ordered implementation tasks

- [ ] **Provision isolated harness —** Input: separate Gmail test project/scopes, owned aliases, fresh PostgreSQL schema, pinned build/fixtures. Operation: verify no product/prospect data and create exactly two tables/constraints. Output: signed isolation/schema manifest. Test evidence: recipient/schema allowlist introspection. Failure behavior: abort M1 and revoke credentials.
- [ ] **Implement typed finite fixture and sole gateway —** Input: deterministic Pydantic AI fixture and scenario. Operation: validate artifact/alias, derive identities, enforce queue/control, and expose Gmail only to gateway. Output: runnable no-branch workflow. Test evidence: import/call-path, schema, denial, replay tests. Failure behavior: no provider call.
- [ ] **Implement kill/reconciliation instrumentation —** Input: K0-K8 barriers, stable identity, and signed evidence schema. Operation: hard-kill, atomically append/fsync signed provider outcome/error/candidate records, and reconcile. Output: reproducible crash harness. Test evidence: termination plus signature/hash-chain validation. Failure behavior: invalid/corrupt scenario; gateway disabled and no gate credit.
- [ ] **Run eight-item matrix from clean state —** Input: approved repetitions/version/concurrency/rate manifest. Operation: execute every scenario, reconcile all attempts, and compare database/provider/evidence hashes. Output: raw evidence plus binary scorecard. Test evidence: automated manifest validator. Failure behavior: stop, disable, and mark DBOS rejected.
- [ ] **Export evidence and dispose schema —** Input: all runs terminal/reconciled and scorecard. Operation: write the three exact versioned RFC 8785 NDJSON files and manifest-last Ed25519 commit marker, restore into an empty two-table schema, and byte-compare re-export before dropping `m1_spike`. Output: interoperable gate bundle with no promoted product data. Test evidence: independent byte/hash/signature/golden/partial-write/restore validators plus schema-absent check. Failure behavior: retain isolated schema disabled; any partial/corrupt bundle blocks disposal.
- [ ] **Trigger Temporal handoff on any failure —** Input: first failed item/evidence. Operation: execute WF-00 stop/incident/migration procedure and rerun identical scenarios. Output: mandatory replacement evidence. Test evidence: Temporal adapter contract/eight-item matrix. Failure behavior: M2 product workflow work remains blocked.

## Test strategy

- **Schema `test_m1_schema_contains_exactly_two_tables_and_exact_columns`:** no product model smuggling.
- **Unit `test_identity_and_rfc_message_id_are_stable_across_replay`:** deterministic vectors.
- **Static `test_fixture_agent_and_workflow_cannot_call_gmail`:** only gateway adapter edge exists.
- **Recovery `test_every_kill_point_reaches_expected_state_without_blind_retry`:** K0-K8.
- **Concurrency `test_repeated_command_and_delivery_produce_one_provider_message`:** compare provider and ledger.
- **Versioning `test_v1_inflight_survives_v2_blue_green_upgrade`:** recover/drain evidence.
- **Security `test_recipient_aliases_are_owned_and_logs_are_redacted`:** no address/secret leaks.
- **Evidence `test_crash_safe_manifest_restore_rejects_gap_tamper_and_multiple_candidates`:** atomic manifest, signatures, hashes, exports, and fail-closed corruption.
- **Golden bytes `test_m1_exports_are_canonical_ndjson_with_exact_names_order_nulls_and_final_lf`:** independent writers produce byte-identical raw files.
- **Signature `test_m1_record_and_manifest_ed25519_preimages_match_golden_vector`:** exact domain separators, key ID, base64url, hash, and signature.
- **Partial write `test_m1_missing_manifest_or_leftover_tmp_fails_closed`:** manifest-last is the sole commit signal.
- **Restore `test_m1_restore_reexport_is_byte_identical_and_state_equivalent`:** both table files and evidence replay compare deterministically.

## Security, privacy, compliance, idempotency, observability, and cost

Use least Gmail scopes, isolated credentials, owned aliases, fixed message content, strict cash/send/time caps, and a harness kill flag independent of agent output. Evidence stores aliases/hashes, never tokens/full addresses. Stable keys and provider identities are retained through reconciliation. Metrics include actual Gmail calls/messages, queue starts, max concurrency/rate, time-to-control, ambiguity age, reconciliation candidates, workflow versions, DBOS recovery, and operator time/cost.

## Failure, rollback, and operator recovery

At any impossible state, duplicate, leakage, rate/control breach, or unresolved ambiguity: stop queue/workers, disable gateway, revoke credentials if needed, reconcile every attempt, preserve evidence, and open a critical incident. Do not drop the schema until all provider outcomes are terminal/operator-visible and export verifies. Do not patch product code around a failed DBOS criterion; execute mandatory Temporal migration.

## Acceptance and retained evidence

- [ ] Schema has exactly the two permitted tables and no product record.
- [ ] Every K0-K8 scenario and all eight criteria pass reproducibly with zero uncontrolled duplicate sends/blind retries.
- [ ] Every ambiguity has stable key/RFC ID, signed outcome/error/candidate records, ledger/result capture, Sent evidence, bounded reconciliation, and visible final/operator state.
- [ ] Independent implementations reproduce exact export filenames/bytes/digests, the signature golden vector, manifest-last crash behavior, and byte-identical restore.
- [ ] Only owned test aliases were used; M1 did not enable product outreach.
- [ ] Any single failure produced DBOS rejection and Temporal handoff rather than a waiver.

Retain pinned build/fixture hashes, schema/recipient manifests, per-run DBOS/queue/control/provider traces, redacted Gmail Sent evidence, attempt export, scorecard, cleanup/revocation proof, and gate/incident/fallback decision.

## Dependencies and next deliverable

WF-01 depends on WF-00 and M0/ARCH gates. A clean 8/8 pass unlocks [DB-01 M2](../02-database/01-core-data-model.md); any failure unlocks only the mandatory Temporal handoff, after which the same M1 acceptance gate must pass before M2.
