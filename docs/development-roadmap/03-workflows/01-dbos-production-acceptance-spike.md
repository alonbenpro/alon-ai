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

The evidence bundle is a filesystem protocol, never a third database table. Each `records/{sequence:020d}-{record_id}.json` is RFC 8785 canonical JSON with these required fields and types: `evidence_schema_version` integer; `record_id` UUID; `sequence` positive integer; `prior_record_hash` null only at sequence 1 otherwise 64-hex; `run_id` UUID; `scenario_name`, `workflow_version`, `kill_point`, `record_type`, `occurred_at`, `idempotency_key`, `mailbox_alias`, and `rfc_message_id` strings; `attempt_state` from the spike enum; `provider_outcome` from `NOT_CALLED/ACCEPTED/CONCLUSIVE_FAILURE/AMBIGUOUS/RECONCILED_SENT/RECONCILED_ABSENT/CONFLICT`; nullable `error_code`, 64-hex `error_fingerprint`, `gmail_message_id`, and `gmail_thread_id`; 64-hex `request_hash` and nullable `response_hash`; `candidate_matches` array; 64-hex `record_hash`; `signer_key_id`; and base64 Ed25519 `signature`.
Each candidate is exactly `{mailbox_alias,gmail_message_id,gmail_thread_id,rfc_message_id,observed_at,envelope_fingerprint,header_hash}`, with both hashes 64-hex. `record_hash` is SHA-256 over the canonical record with `record_hash` and `signature` omitted; the signature covers that hash, prior hash, run ID, and sequence.

The signed canonical `manifest.json` is exactly `{manifest_schema_version,run_id,scenario_name,workflow_version,fixture_hash,queue_config_hash,control_config_hash,records:[{path,sequence,record_id,record_hash}],spike_runs_export_hash,spike_send_attempts_export_hash,final_state,created_at,signer_key_id,signature}`. Hashes are lowercase SHA-256; the Ed25519 signature covers the RFC 8785 manifest with `signature` omitted.

Every record/export is exclusive-created as a same-directory `.tmp`, fully written and file-`fsync`ed, atomically renamed, then parent-directory-`fsync`ed. The manifest is written last with the same protocol and is the commit point. Recovery ignores orphan temp files but validates schema, signatures, path, strict sequence/prior-hash chain, content/export hashes, and database/provider identity agreement. It may rebuild a missing manifest only from a complete valid signed chain and freshly validated exports, after appending a signed recovery record. A gap, duplicate, invalid signature/hash, mismatched export, malformed/multiple candidate, or impossible provider outcome fails closed: disable gateway, preserve bytes, expose `CORRUPT_EVIDENCE`, and prohibit retry/send. Restore unpacks fresh, validates every byte/signature, loads both exports into an empty two-table schema, and runs the no-send reconciliation validator.

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
- [ ] **Export evidence and dispose schema —** Input: all runs terminal/reconciled and scorecard. Operation: export signed/redacted ledger/traces/config/Gmail evidence, verify restore/readability, then drop `m1_spike` and revoke test credentials when no longer needed. Output: gate bundle with no promoted product data. Test evidence: export hash verification and schema-absent check. Failure behavior: retain isolated schema disabled until evidence/reconciliation is complete.
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

## Security, privacy, compliance, idempotency, observability, and cost

Use least Gmail scopes, isolated credentials, owned aliases, fixed message content, strict cash/send/time caps, and a harness kill flag independent of agent output. Evidence stores aliases/hashes, never tokens/full addresses. Stable keys and provider identities are retained through reconciliation. Metrics include actual Gmail calls/messages, queue starts, max concurrency/rate, time-to-control, ambiguity age, reconciliation candidates, workflow versions, DBOS recovery, and operator time/cost.

## Failure, rollback, and operator recovery

At any impossible state, duplicate, leakage, rate/control breach, or unresolved ambiguity: stop queue/workers, disable gateway, revoke credentials if needed, reconcile every attempt, preserve evidence, and open a critical incident. Do not drop the schema until all provider outcomes are terminal/operator-visible and export verifies. Do not patch product code around a failed DBOS criterion; execute mandatory Temporal migration.

## Acceptance and retained evidence

- [ ] Schema has exactly the two permitted tables and no product record.
- [ ] Every K0-K8 scenario and all eight criteria pass reproducibly with zero uncontrolled duplicate sends/blind retries.
- [ ] Every ambiguity has stable key/RFC ID, signed outcome/error/candidate records, ledger/result capture, Sent evidence, bounded reconciliation, and visible final/operator state.
- [ ] Only owned test aliases were used; M1 did not enable product outreach.
- [ ] Any single failure produced DBOS rejection and Temporal handoff rather than a waiver.

Retain pinned build/fixture hashes, schema/recipient manifests, per-run DBOS/queue/control/provider traces, redacted Gmail Sent evidence, attempt export, scorecard, cleanup/revocation proof, and gate/incident/fallback decision.

## Dependencies and next deliverable

WF-01 depends on WF-00 and M0/ARCH gates. A clean 8/8 pass unlocks [DB-01 M2](../02-database/01-core-data-model.md); any failure unlocks only the mandatory Temporal handoff, after which the same M1 acceptance gate must pass before M2.
