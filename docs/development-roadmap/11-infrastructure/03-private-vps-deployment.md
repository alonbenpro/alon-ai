# Private VPS Topology and Segmented Public Unsubscribe Ingress

**Document ID:** INFRA-03
**Status:** Planned M8 private deployment and M9-disabled public edge; no VPS, DNS, TLS, firewall, proxy, KMS, managed secret store, WAF, public route, or production container exists today
**Milestone:** M8 private single-operator operations; M9 scanner-safe public unsubscribe exception
**Owner:** Solo operator
**Prerequisites:** INFRA-01/02, TEST-01..06, SEC-01..06, OBS-01..05, exact BACKEND-02 64+2 partition, current M1/M6 evidence, and M9 legal/policy authority before public-edge activation
**Outputs:** Minimal host/network/process/storage topology, private ingress, separately gated public edge, secret/KMS boundary, firewall/TLS/DNS/WAF rules, capacity and deployment evidence
**Unlocks:** M8 private operation; only the infrastructure prerequisite for the M9 public unsubscribe pair
**Risk:** Critical
**Complexity:** XL

## Outcome and timing

One right-sized Linux VPS runs the modular monolith privately for one operator. The product API/UI is reachable only through an authenticated private network. A separately configured public hostname and proxy path can expose exactly the scanner-safe unsubscribe GET/POST pair only after M9 evidence; it is absent before then and can be disabled independently without affecting private recovery.

## Current repository state

The repository has local non-root images and loopback Compose but no deployment files or services. PostgreSQL, API, worker and frontend are planned only for local use. DBOS/Gmail/product schema/UI/public ingress/VPS remain unimplemented. Current Compose publishes PostgreSQL/API/frontend on loopback, has no proxy/TLS/firewall/read-only filesystem/resource limits/backup/telemetry/KMS, and must not be copied to a public host unchanged.

## Scope and non-goals

In scope: one Google Compute Engine custom VPS with 4 vCPU, 8 GiB RAM, a 30-GiB boot disk and a separate 160-GiB CMEK-encrypted balanced persistent data disk in an EU region approved by SEC-06; Debian 13 x86_64 pinned by image project/name; host firewall; private Tailscale operator network; Caddy reverse proxy; frontend/API/worker/PostgreSQL/OpenTelemetry containers; internal networks/volumes; Tailscale DNS/TLS; Google Cloud KMS plus Secret Manager; primary Google Cloud Storage backup repository; exactly one off-provider private Amazon S3 general-purpose bucket in `eu-central-1`, with versioning and Object Lock, for encrypted backup/WAL/tombstone recovery evidence and the sole deletion-commit witness; resource limits; exact M9 public edge via Cloudflare proxied DNS/WAF; hardening, capacity and rollback. Non-goals: high availability claim, hot or live multi-cloud compute, active multi-region compute, AWS application compute, Kubernetes, microservices, Redis/Celery, Kafka, self-hosted Vault, public signup/API/webhooks, SSH open to the Internet, or a second product backend.

## Exact planned implementation surfaces

Create `infra/production/compose.yaml`, `Caddyfile.private`, `Caddyfile.public`, `firewall.nft`, `systemd/alon-ai.service`, `public-route-policy.v1.json`, `resource-limits.v1.json`, hardening/sysctl files and verification scripts. Pin OS/package/image digests in the release manifest. Caddy automatic HTTPS and reverse-proxy behavior are documented by the official Caddy [automatic HTTPS](https://caddyserver.com/docs/automatic-https) and [reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) references, accessed 2026-08-29; deployment tests, not the documentation, establish this configuration.

```text
operator device -- Tailscale grants/Tailnet Lock --> private Caddy --> frontend / FastAPI
                                                     |--> PostgreSQL (internal only)
                                                     |--> worker (no listener)
                                                     |--> OTel collector (egress only)

Internet -- Cloudflare DNS/WAF [M9 only] --> public Caddy --> FastAPI public router
                                                   exact GET/POST /api/v1/public/unsubscribe/{token}
                                                   every other method/path = fixed 404
```

Private plane: Tailscale grants permit only the operator and separately enrolled recovery device; Tailnet Lock must sign the VPS node. Only the `tailscale0` interface accepts operator HTTPS and Tailscale SSH; the Google Cloud VPC firewall and host nftables drop public SSH/API/frontend/PostgreSQL. Caddy serves the `.ts.net` certificate on the tailnet listener, overwrites forwarded headers and trusts only explicit tailnet/proxy CIDRs. PostgreSQL binds only the internal container network; API/worker use distinct least-privilege roles; migration/retention/backup roles are invoked only by operator jobs. Containers run non-root, read-only root filesystems where compatible, drop capabilities, use `no-new-privileges`, explicit tmpfs, CPU/memory/PID limits and health checks. API and worker are separate processes from the same GHCR backend image digest. Tailscale's official security guidance for grants, HTTPS and Tailnet Lock was accessed 2026-08-29: [secure the network](https://tailscale.com/kb/1429/secure) and [HTTPS certificates](https://tailscale.com/docs/how-to/set-up-https-certificates).

Public plane: the `public-edge` Compose profile and DNS record are disabled/uncreated before M9. When approved, a separate Cloudflare-proxied hostname uses TLS, WAF method/path/token-shape/header/body limits and independent per-source/global rate buckets. Origin firewall accepts public HTTPS only from the current signed Cloudflare IP manifest; Caddy has a distinct listener/network/config, exact GET/POST matcher and fixed default deny. It proxies only to FastAPI's `PUBLIC_UNSUBSCRIBE` router, never frontend/private routes. GET is read-only; POST requires exact Origin, `Sec-Fetch-Site`, JSON/content length and CSRF intent. Dependency uncertainty disables `PRODUCT_OUTREACH`. WAF/CDN logs are minimized and never contain full URI/token/query/IP in application telemetry.

Secret boundary: Google Cloud KMS plus Secret Manager is the selected production adapter. Secret Manager uses user-managed EU replication and purpose-specific CMEK generations; the Compute Engine instance's attached least-privilege service account supplies workload identity without an exported service-account key. The adapter must satisfy SEC-03 `create|get strong|compare_and_swap|claim_lease|release_lease|revoke|reference-checked destroy` with its own versioned secret-object envelope and provider-accepted generation/ETag/lease/reference metadata contract. That credential metadata remains in the managed secret-store adapter contract and provider resources; it is not a product table, not either auth table, and never a third `security_runtime` operational table. `security_runtime` owns only OIDC-flow and operator-session CAS rows. Workloads receive scoped secret versions at runtime, never a committed `.env` or image layer. KMS purpose/environment generations are separate; backup key/recovery wrapping material is off-host in two encrypted copies. Google documents versioned secret payloads, user-managed replication and CMEK location binding in its [Secret Manager resource contract](https://cloud.google.com/secret-manager/docs/reference/rest/v1/projects.secrets), accessed 2026-08-29. If live adapter acceptance cannot prove the complete SEC-03 CAS/lease behavior over the selected managed resources, M8/M6 credential use is blocked and the adapter must be amended; no SQL metadata table, Vault or plaintext fallback is implied.

Google remains the only live production stack; AWS is backup/witness only and never hot application compute. Before the production bucket is accepted or provisioned, destructive command `T7-AWS-WITNESS-ACCEPT` must pass against a real disposable private S3 general-purpose bucket in `eu-central-1`, proving the INFRA-04 versioning/Object-Lock/bucket-policy/IAM/CAS/concurrency/lost-response/pgBackRest/recovery-package/account-lockout matrix with signed hashes. An emulator, LocalStack, moto, missing AWS authorization/credits or unavailable provider access cannot pass. Any failed documented semantic blocks M8 and requires a signed architecture amendment selecting another provider with documented and live-tested CAS/Object Lock; there is no fallback to non-CAS behavior and no third provider is preselected. M8 also retains legal basis, international-transfer/processor terms, region, account-recovery and monthly/egress cost evidence. Purpose-separated AWS IAM credentials and the pgBackRest repository cipher may be referenced from Secret Manager, while two encrypted recovery packages containing independently usable AWS S3 read credentials, exact region/bucket/repository configuration, pinned pgBackRest binary hash and repository cipher are held outside Google and the VPS under separate operator/recovery-device custody. Loss or unverified rotation blocks backup/restore credit. During a Google-wide outage, product, Gmail send, private compute and public ingress stay off; Amazon S3 supports only isolated independently decryptable data/evidence recovery. No full-service alternate-compute RTO is claimed.

Private host/topology requirements map to `T7-VPS-VERIFY`; public boundary requirements map to `T7-PUBLIC-EDGE-VERIFY`; AWS selection acceptance maps only to `T7-AWS-WITNESS-ACCEPT`; and ongoing backup/restore ownership remains exclusively `T7-BACKUP-BOTH|T7-RESTORE-PRIMARY|T7-RESTORE-DR`. Each uses the [TEST-01 closed invocation](../10-testing/01-testing-strategy.md#closed-command-manifest) and named immutable profile. Read-only verification never mutates the host; unavailable VPS/AWS/public-M9 access exits `30`, not pass. Exact set equality rejects duplicate ownership and proves the acceptance row is reachable before M8.

Capacity starts at TEST-06's measured 4-vCPU/8-GiB envelope. Resize vertically only after sustained evidence crosses a defined stop threshold; separate database/worker hosts are considered only after measured CPU/I/O/failure-domain constraints and a tested migration. No caching/queue platform is added because PostgreSQL/DBOS already own current state/durability.

## Ordered implementation tasks

- [ ] **Provision and attest the private host —** Input: supported image, 4/8/160 resources, operator recovery device and immutable release. Operation: patch, create non-root operator, configure overlay/firewall/disk/time/core-dump controls and capture provider/host IDs. Output: private unreachable-by-public-default host. Test evidence: external port scan, lost-overlay recovery and hardening audit. Failure behavior: destroy/recreate untrusted host; no app secrets.
- [ ] **Deploy the modular-monolith topology —** Input: signed image digests, internal networks/volumes/roles/resource limits. Operation: start private Caddy, frontend, API, stopped worker, PostgreSQL and collector; migrate, verify, then start compatible worker. Output: private service. Test evidence: network/capability/read-only/non-root/health/schema/controls tests. Failure behavior: stop candidate and roll back digest.
- [ ] **Integrate managed secret/KMS adapter —** Input: SEC-03 contract and provider feature evidence. Operation: configure workload identity, purpose KEKs, versioned objects and provider-backed generation/ETag/lease/CAS behavior through the selected managed adapter; if the managed adapter cannot supply any required primitive, fail closed and block credential use rather than add a product SQL credential-metadata surface; run OAuth/restore canaries. Output: no file-based production secret. Test evidence: cross-purpose/version/environment denial, rotation/revoke/restart/backup. Failure behavior: dependent services/credentials remain off.
- [ ] **Gate the sole off-provider recovery repository —** Input: real AWS authorization/credits, M8 legal/transfer/terms/region/Object-Lock/cost decision, purpose-separated IAM principals/keys and INFRA-04 config. Operation: run `T7-AWS-WITNESS-ACCEPT` against one real disposable `eu-central-1` bucket before accepting/provisioning the production bucket, then verify independently decryptable off-Google custody and prohibit AWS compute/runtime deployment. Output: signed acceptance and repository/bootstrap evidence. Test evidence: the complete CAS/Object-Lock/IAM/pgBackRest/account-lockout matrix, Google credential/KMS unavailable restore bootstrap, key rotation/loss and region mismatch; no emulator evidence. Failure behavior: M8 remains failed and a provider architecture amendment is required; no purge, non-CAS fallback or provider-outage recovery claim.
- [ ] **Configure private DNS/TLS/proxy/firewall —** Input: overlay identity, private hostname and trusted CIDRs. Operation: terminate TLS, overwrite forwarded headers, default-deny host/routes and expose only private UI/API/health as registered. Output: authenticated private ingress. Test evidence: Internet scan, spoofed forwarding, TLS renewal and wrong-host/path cases. Failure behavior: close listener and use console recovery.
- [ ] **Stage but do not activate public unsubscribe edge —** Input: exact 64+2 route manifest, M9 gate and Cloudflare policy. Operation: validate disabled profile first; when separately authorized create hostname/WAF/origin allowlist and exact default-deny proxy. Output: independently switchable two-operation ingress. Test evidence: TEST-05/06 scanner/abuse/set-equality matrix. Failure behavior: remove DNS/disable profile and set product outreach false.
- [ ] **Prove capacity, upgrade and rollback —** Input: TEST-06 envelope and INFRA-02 manifests. Operation: run load/soak, host reboot, image/config rollback and vertical-resize rehearsal. Output: measured limits and recovery evidence. Test evidence: no data/authority drift under resource pressure/reboot. Failure behavior: reduce caps/authority or resize; no architecture sprawl.
- [ ] **Close topology command ownership —** Input: every private/public/backup/restore requirement. Operation: prove exact non-overlapping command mapping, profile, target identity, evidence and unavailable semantics. Output: signed coverage. Test evidence: orphan/duplicate and unavailable-provider negatives. Failure behavior: M8/M9 remains blocked.

## Test strategy

- **Network `test_public_scan_reaches_no_private_ssh_database_api_frontend_or_health_port`.**
- **Topology `test_services_use_exact_internal_network_roles_volumes_digests_limits_and_nonroot_users`.**
- **Proxy `test_forwarded_headers_host_tls_route_and_body_limits_are_default_deny`.**
- **Secrets `test_no_production_secret_exists_in_env_file_image_volume_log_or_unscoped_workload`.**
- **Partition `test_public_profile_absent_pre_m9_and_when_enabled_exposes_exact_get_post_only`.**
- **Capacity `test_single_vps_meets_proven_envelope_and_fails_closed_at_stop_thresholds`.**
- **Rollback `test_host_reboot_and_prior_digest_restore_private_service_with_controls_false`.**

## Security, privacy, compliance, idempotency, observability, and cost

Disk/volume/backups are encrypted; host, KMS, secret, registry and overlay access is least-privilege and audited. Public token/IP/URI never becomes a metric label or normal log field. Public POST replay is token-JTI idempotent. TLS/DNS/WAF/overlay/VPS/object/KMS/telemetry costs are budgeted before selection; M8 records actual recurring spend. Region/transfer/provider terms require SEC-06 review and counsel where personal data applies.

## Failure, rollback, and operator recovery

On host compromise, exposed port, certificate/DNS/WAF drift, secret mismatch, route widening, full disk, clock failure, unsigned image or public dependency failure: disable public DNS/profile, set both controls false, stop workers/egress, revoke the credentials named by the scenario, snapshot minimal evidence, rebuild a clean host and restore through INFRA-04. Roll back immutable image/config; never repair a compromised host in place or enable public routes for diagnosis.

## Acceptance and retained evidence

- [ ] Private operator and public unsubscribe planes are network/config/process separated and independently disabled.
- [ ] The planned single VPS is least-privilege, encrypted, capacity-tested and recoverable without Kubernetes or extra brokers.
- [ ] Production secrets use the exact managed KMS/versioned-object contract; no plaintext fallback exists.
- [ ] Exactly one private versioned Object-Locked Amazon S3 general-purpose bucket in `eu-central-1` has real-provider M8 acceptance, legal/cost/terms evidence and independently decryptable off-Google bootstrap proof; AWS has no live product compute.
- [ ] Public ingress is absent pre-M9 and exposes exactly two scanner-safe operations only after separate evidence.

Retain provider/region review, host/firewall/overlay/DNS/TLS/proxy/WAF configs and scans, image/release/resource/network manifests, secret/KMS/IAM/rotation evidence without values, capacity/reboot/rollback results and public-off/on gate records.

## Dependencies and next deliverable

INFRA-03 requires [INFRA-04 backups](04-postgresql-backups-and-restores.md) and [INFRA-05 monitoring/DR](05-monitoring-and-disaster-recovery.md) before M8 acceptance. Public activation additionally requires M9 legal/policy/suppression evidence and never authorizes general public API/signup/webhooks.
