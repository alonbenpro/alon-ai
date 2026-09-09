# Small Private VPS Topology with Cloudflare Access

**Document ID:** INFRA-03
**Status:** Planned M8 private deployment and M9-disabled public edge; no production VPS/tunnel/storage/backup service exists today
**Milestone:** M8 (exact scope and prerequisites are declared per task)
**Owner:** Solo operator
**Prerequisites:** exact task Inputs `INFRA-03-T01 <- INFRA-02-T02; INFRA-03-T02 <- INFRA-03-T01,INFRA-02-T02; INFRA-03-T03 <- INFRA-03-T02,SEC-03-T01; INFRA-03-T04 <- INFRA-03-T03; INFRA-03-T05 <- INFRA-03-T04; INFRA-03-T06 <- INFRA-03-T05,BACKEND-02-T05,SEC-01-T02; INFRA-03-T07 <- INFRA-03-T06,TEST-06-T02,INFRA-02-T04; INFRA-03-T08 <- INFRA-03-T07`; descriptive sources do not imply whole-document dependencies
**Outputs:** 2-vCPU/4-GB private host topology, Cloudflare Tunnel/Access ingress, encrypted local storage, encrypted R2 backup boundary, capacity/deployment evidence, separately gated public unsubscribe edge
**Unlocks:** M8 private operation and the infrastructure prerequisite for M9 public unsubscribe
**Risk:** Critical
**Complexity:** L

## Outcome and timing

Pre-revenue production starts with one provider-neutral Linux VPS sized at **2 vCPU / 4 GB RAM**. It runs the modular monolith and PostgreSQL with strict resource limits. The operator UI/API is reachable only through **Cloudflare Tunnel + Cloudflare Access**; the host does not expose the product API, frontend, PostgreSQL, or SSH directly to the public Internet.

PostgreSQL/application state uses encrypted local VPS storage. Backups are encrypted by application/backup tooling before upload to **Cloudflare R2**. A fresh-host restore drill and off-host recovery material are mandatory. Managed KMS, multi-cloud backup/witnessing, dedicated 160-GB disks, larger hosts, and enterprise hardening are explicitly deferred until revenue or measured operational evidence justifies an architecture amendment.

## Current repository state

The repository has local non-root images and loopback Compose but no production deployment, Cloudflare tunnel/access configuration, encrypted production volume, R2 backup repository, or production recovery evidence. Roadmap requirements remain planned only.

## Scope and non-goals

In scope: one Linux VPS from any provider meeting current region/legal/cost requirements; 2 vCPU/4 GB baseline; modest provider disk sized from measured data with encryption at rest where the provider supports it plus application/database protection; host firewall; Cloudflare Tunnel outbound connector; Cloudflare Access operator identity/policy; frontend/API/worker/PostgreSQL/telemetry containers; internal networks/volumes; non-root/read-only/no-new-privileges/resource limits; local encrypted data; application-encrypted R2 backups; clean-host restore; image/config rollback; measured vertical-resize trigger; and a separately gated scanner-safe public unsubscribe route.

Non-goals pre-revenue: Google-Cloud-specific compute dependency, Tailscale/Caddy as required ingress, managed KMS/Secret Manager as an M8 prerequisite, GCS+AWS dual repositories, Object-Lock witness semantics, a dedicated 160-GB data disk, HA/multi-region compute, Kubernetes, microservices, public product signup/API, or infrastructure added for hypothetical scale.

## Planned topology

```text
operator browser -> Cloudflare Access -> Cloudflare Tunnel -> private web/API listener
                                                     |-> PostgreSQL (container-internal only)
                                                     |-> worker (no public listener)
                                                     |-> telemetry collector

VPS encrypted local state -> encrypted backup artifact -> Cloudflare R2

M9-only public unsubscribe hostname -> exact scanner-safe unsubscribe router
(no operator/private product route shares this public authority)
```

The tunnel initiates outbound connectivity; no inbound product port needs to be open on the VPS. Cloudflare Access policy admits only the operator's approved identity/account and recovery path. Host firewall/default-deny still applies so disabling/misconfiguring the tunnel cannot expose private services.

## Secret and encryption posture

Before revenue, the roadmap does not require a managed KMS. Production secrets remain server-side, least-privilege, never committed or baked into images, and protected by the existing SEC-03 lifecycle/rotation/revoke contracts. Recovery encryption key material for backups is not stored solely on the VPS or solely in R2; retain at least one independently usable encrypted off-host operator-controlled copy and test it in restore drills.

A future revenue-backed architecture review may adopt managed KMS/secret management, hardware-backed keys, multi-provider backup/witnessing, or stronger custody separation. That future review must preserve current secret/rotation/reference guarantees and cannot be treated as pre-approved scope.

## R2 backup boundary

R2 is the sole required pre-revenue off-host backup repository. Backup objects are encrypted before upload; provider-side encryption alone is insufficient evidence. Repository/bucket credentials are purpose-specific and cannot access application APIs or Gmail/calendar credentials. Restore tests prove the repository can be read and decrypted from a clean target with VPS unavailable.

Deletion/retention remains governed by DB-06/SEC-06 and the backup ledger, but M8 no longer depends on a second cloud provider or Object-Lock/CAS witness. Where R2 lacks a former witness primitive, the roadmap uses signed append-only application/audit evidence plus conservative deletion rules and periodic restore verification rather than pretending equivalent provider semantics exist.

## Capacity and cost

`2 vCPU / 4 GB` is the default initial envelope. TEST-06 measures realistic private workloads, PostgreSQL memory, worker concurrency, provider call concurrency, and disk growth. If the workload cannot remain safe in the envelope, reduce concurrency/caps first. Resize vertically only after measured sustained CPU/memory/I/O pressure or restore/disk growth evidence. Larger infrastructure never becomes a prerequisite merely because a future 100–300 validation tranche exists.

## Independent calendar, send, and public boundaries

SendGateway remains the sole Gmail writer. BookingGateway remains the sole calendar writer. Cloudflare private ingress does not grant either provider capability. The public unsubscribe pair, when M9 enables it, remains independently switchable/default-deny and cannot route to private dashboard/API surfaces.

Recovery/release evidence preserves offer/strategy/stage/tranche/conversation/booking/suppression/action-authorization/cost/control state and reconciles possibly-called Gmail/calendar operations before re-enable.

## Ordered implementation tasks

<!-- roadmap-task id=INFRA-03-T01 milestone=M8 depends_on=INFRA-02-T02 mode=serial locks=live-environment -->
- [ ] **Provision and attest the small private host —** Input: supported provider/region/image, 2-vCPU/4-GB target, measured disk requirement, operator recovery path and immutable release. Operation: patch, configure non-root operator, firewall, encrypted storage/time/core-dump controls and capture host/provider IDs/cost. Output: private-by-default host. Test evidence: public port scan, reboot/recovery, storage encryption and resource-envelope audit. Failure behavior: destroy/recreate untrusted host; no app secrets.
<!-- roadmap-task id=INFRA-03-T02 milestone=M8 depends_on=INFRA-03-T01,INFRA-02-T02 mode=serial locks=compose-topology -->
- [ ] **Deploy the resource-limited modular monolith —** Input: signed image digests, internal networks/volumes/roles and 2/4 resource budget. Operation: start frontend/API/worker/PostgreSQL/collector with non-root/read-only/no-new-privileges limits, migrate and verify. Output: private service. Test evidence: network/capability/health/schema/memory-pressure tests. Failure behavior: stop candidate and roll back digest/caps.
<!-- roadmap-task id=INFRA-03-T03 milestone=M8 depends_on=INFRA-03-T02,SEC-03-T01 mode=serial locks=security-runtime -->
- [ ] **Integrate pre-revenue secret and encryption boundary —** Input: SEC-03 lifecycle plus off-host recovery-key procedure. Operation: provision server-side secrets without committed files/images, validate rotation/revoke/restart and local-data/backup encryption; explicitly do not require managed KMS. Output: accepted pre-revenue secret/encryption posture. Test evidence: secret leak/cross-purpose/recovery-key-loss/rotation cases. Failure behavior: dependent credentials remain disabled.
<!-- roadmap-task id=INFRA-03-T04 milestone=M8 depends_on=INFRA-03-T03 mode=serial locks=backup-restore,live-environment -->
- [ ] **Gate encrypted Cloudflare R2 recovery repository —** Input: R2 account/bucket, purpose-specific credentials, backup encryption configuration and off-host recovery material. Operation: upload signed encrypted test backup and restore/decrypt from a clean target with VPS unavailable. Output: accepted sole pre-revenue off-host repository. Test evidence: bad key/credential/bucket/region-like endpoint, truncated object, VPS-loss and cost/egress evidence. Failure behavior: M8 remains blocked; no multi-cloud requirement is invented.
<!-- roadmap-task id=INFRA-03-T05 milestone=M8 depends_on=INFRA-03-T04 mode=serial locks=live-environment -->
- [ ] **Configure Cloudflare Tunnel and Access —** Input: private hostname, operator identity policy, tunnel credentials and host firewall. Operation: expose UI/API only through Access-protected Tunnel while keeping direct listeners unreachable publicly. Output: authenticated private ingress. Test evidence: unauthenticated access, direct-IP scan, wrong-host/path, tunnel-down and identity-recovery cases. Failure behavior: close tunnel/listener and use console recovery.
<!-- roadmap-task id=INFRA-03-T06 milestone=M8 depends_on=INFRA-03-T05,BACKEND-02-T05,SEC-01-T02 mode=serial locks=live-environment -->
- [ ] **Stage but do not activate public unsubscribe edge —** Input: disabled-public route manifest and exact M9 activation condition. Operation: construct a separate default-deny public Cloudflare route/profile exposing only the unsubscribe pair when later authorized; keep it absent/disabled during M8. Output: independently switchable staged public ingress. Test evidence: private-route isolation, method/path set equality and disabled state. Failure behavior: remove public route and set outreach false.
<!-- roadmap-task id=INFRA-03-T07 milestone=M8 depends_on=INFRA-03-T06,TEST-06-T02,INFRA-02-T04 mode=serial locks=live-environment -->
- [ ] **Prove 2/4 capacity, resize trigger, and rollback —** Input: TEST-06 envelope and release manifests. Operation: run load/soak, host reboot, image/config rollback and vertical-resize rehearsal. Output: measured pre-revenue limits/upgrade trigger. Test evidence: no data/authority drift under pressure/reboot and exact trigger evidence. Failure behavior: reduce concurrency/caps or resize; no architecture sprawl.
<!-- roadmap-task id=INFRA-03-T08 milestone=M8 depends_on=INFRA-03-T07 mode=serial locks=compose-topology -->
- [ ] **Close topology command ownership and deferred-upgrade registry —** Input: private/public/backup/restore requirements and deferred enterprise controls. Operation: prove non-overlapping command ownership and record managed KMS/multi-cloud/large-disk/enterprise hardening as post-revenue triggers, not prerequisites. Output: signed M8 topology coverage. Test evidence: orphan/duplicate/legacy-GCE-or-AWS-mandatory assertions fail. Failure behavior: M8 remains blocked.

## Acceptance

- [ ] Initial production target is provider-neutral 2 vCPU / 4 GB.
- [ ] Operator product ingress is Cloudflare Tunnel + Access and direct product ports are closed.
- [ ] Local state and R2 backup artifacts are encrypted; clean-host restore passes with VPS unavailable.
- [ ] Managed KMS, multi-cloud backup/witnessing, 160-GB disk and enterprise hardening are deferred until revenue/measured evidence.
- [ ] Gmail/calendar/public-unsubscribe authorities remain isolated and fail closed.
