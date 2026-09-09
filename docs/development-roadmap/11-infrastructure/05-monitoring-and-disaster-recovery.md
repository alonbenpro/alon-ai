# Monitoring, On-Call, and Disaster Recovery

**Document ID:** INFRA-05
**Status:** Planned M8 operations gate; current foundation has safe logs/health but no production telemetry, alerting, R2 recovery drills, or DR evidence
**Milestone:** M8
**Owner:** Solo operator wearing incident roles sequentially
**Prerequisites:** exact task Inputs `INFRA-05-T01 <- OBS-02-T01,OBS-01-T03,BACKEND-06-T02; INFRA-05-T02 <- INFRA-05-T01,OBS-02-T04,OBS-05-T01,OBS-05-T04; INFRA-05-T03 <- INFRA-05-T02; INFRA-05-T04 <- INFRA-05-T03,OBS-05-T01; INFRA-05-T05 <- INFRA-05-T04,INFRA-04-T03; INFRA-05-T06 <- INFRA-05-T05,INFRA-02-T04,SEC-03-T04,INFRA-04-T02; INFRA-05-T07 <- INFRA-05-T06,INFRA-04-T06; INFRA-05-T08 <- INFRA-05-T07`
**Outputs:** telemetry/alerting, small-VPS capacity dashboards, encrypted-R2 backup freshness, DR scenarios/runbooks/drills, evidence freshness and re-enable rules
**Unlocks:** M8 private operations and bounded M9 readiness
**Risk:** Critical
**Complexity:** L

## Outcome

One operator can detect unsafe state, determine authoritative database/provider/control truth, contain harm, restore a clean small VPS from encrypted R2 plus off-host recovery material, measure actual RPO/RTO, and re-enable only through a separate gated command.

The pre-revenue design does **not** require two cloud providers, an AWS deletion witness, managed KMS, or enterprise on-call infrastructure. Monitoring must be reliable and independent enough to detect a dead/unreachable VPS, backup failure, capacity pressure, provider ambiguity, safety stop, or public-unsubscribe failure without creating more fixed cost than the experiment justifies.

## Monitoring priorities

Required dashboards/alerts emphasize:

- 2-vCPU/4-GB CPU, memory, swap/OOM, disk use/I/O, process/container health and restart loops;
- Cloudflare Tunnel/Access reachability and authentication failures;
- PostgreSQL health, connection saturation, WAL/backup lag and restore-freshness age;
- encrypted R2 upload/manifest/freshness failures;
- application health, queue depth, provider/model cost and routing-tier anomalies;
- SendGateway ambiguity/duplicate/suppression/rate/cap state;
- BookingGateway ambiguity/duplicate/confirmation state;
- stage/tranche capacity, checkpoint closure and strategy-activation boundaries;
- public unsubscribe route health only when that M9 edge is enabled.

Telemetry must remain minimized: safe IDs/hashes/counts, not message bodies, raw social/business content, contacts, prompts, secrets, calendar descriptions or sensitive inferred budget.

## Independent alert path

The operator must have at least one alert path independent of the application Gmail account and private web UI (for example Cloudflare/VPS/provider alerting to a separate operator channel). A second paid on-call platform is not required pre-revenue. The exact channel is versioned and tested; failure of the sole independent alert path expires M8/re-enable evidence until repaired.

## DR scenarios

At minimum exercise:

1. VPS process/container crash and reboot;
2. VPS total loss with provider console inaccessible from application state;
3. local encrypted volume corruption/loss;
4. Cloudflare Tunnel/Access failure while provider console remains available;
5. R2 upload failure/stale backup chain;
6. clean-host restore from R2 using only off-host recovery material;
7. R2 credential/encryption-key rotation and recovery;
8. PostgreSQL PITR/latest restore with product writers/providers disabled;
9. unresolved Gmail send or calendar action across restore;
10. kill switch/suppression/stage/checkpoint/strategy generation preserved across restore;
11. public unsubscribe dependency failure when M9 public edge is active.

Multi-cloud provider loss is a **post-revenue** architecture scenario, not an M8 precondition.

## Re-enable gate

After any serious incident/restore, keep PRODUCT_OUTREACH, CALENDAR_WRITES, stage admission and strategy activation off until:

- restored schema/data/audit/suppression/idempotency invariants pass;
- current R2 backup/manifest/recovery package is proven;
- possibly-called Gmail/calendar actions are reconciled;
- current offer/strategy/stage/tranche/checkpoint generations match authoritative evidence;
- capacity is safe under the 2-vCPU/4-GB envelope or a signed measured resize amendment exists;
- Cloudflare private ingress/auth is healthy;
- alerts/telemetry are current; and
- the owning incident/recovery command records explicit re-enable evidence.

## Cost-aware capacity policy

The default response to pressure is first to lower concurrency, model/provider parallelism, batch size, retention/cache footprint or stage admission rate. Vertical VPS resize is allowed after measured evidence; splitting database/worker hosts or adding managed services is deferred until measurements and revenue justify the extra cost/failure domain.

## Ordered implementation tasks

<!-- roadmap-task id=INFRA-05-T01 milestone=M8 depends_on=OBS-02-T01,OBS-01-T03,BACKEND-06-T02 mode=parallel locks=observability -->
- [ ] **Implement telemetry and authoritative comparisons —** Input: OBS registries and reporting projections. Operation: expose safe small-VPS, Cloudflare, PostgreSQL, R2, provider/model, stage/checkpoint and action-control metrics with authoritative query links. Output: private monitoring view. Test evidence: missing/late/PII/redaction and authoritative-vs-cache divergence cases. Failure behavior: unknown truth blocks positive readiness.
<!-- roadmap-task id=INFRA-05-T02 milestone=M8 depends_on=INFRA-05-T01,OBS-02-T04,OBS-05-T01,OBS-05-T04 mode=parallel locks=observability -->
- [ ] **Implement exact alert/incident routing —** Input: alert rules/runbooks and incident registry. Operation: map critical VPS/R2/tunnel/safety/provider-action/cost conditions to typed incidents and independent operator alert. Output: tested routing. Test evidence: duplicate/suppressed/missing alert and dead-UI cases. Failure behavior: M8 freshness expires.
<!-- roadmap-task id=INFRA-05-T03 milestone=M8 depends_on=INFRA-05-T02 mode=parallel locks=observability -->
- [ ] **Establish independent operator alert path —** Input: one non-application channel/account. Operation: configure and exercise dead-VPS/private-UI-unreachable notification and recovery contact data. Output: signed independent alert evidence. Test evidence: application Gmail/UI unavailable. Failure behavior: operations gate blocked.
<!-- roadmap-task id=INFRA-05-T04 milestone=M8 depends_on=INFRA-05-T03,OBS-05-T01 mode=parallel locks=observability -->
- [ ] **Implement Critical watchdog and capacity alarms —** Input: health/capacity/control signals. Operation: independently detect tunnel/product/backup/OOM/disk/provider ambiguity and missing heartbeat states. Output: Critical signal evidence. Test evidence: process kill, tunnel stop, backup stale, OOM/disk thresholds and telemetry blind spot. Failure behavior: fail closed/reduce authority.
<!-- roadmap-task id=INFRA-05-T05 milestone=M8 depends_on=INFRA-05-T04,INFRA-04-T03 mode=parallel locks=backup-restore,observability -->
- [ ] **Monitor R2 backup, retention and recovery-package freshness —** Input: INFRA-04 manifest/deletion/hold ledger. Operation: alert on missing/corrupt/stale chain, expiring credentials/key package and failed retention jobs. Output: restore-readiness metric. Test evidence: wrong key, stale manifest, missing WAL/object and expired recovery package. Failure behavior: backup/re-enable credit revoked.
<!-- roadmap-task id=INFRA-05-T06 milestone=M8 depends_on=INFRA-05-T05,INFRA-02-T04,SEC-03-T04,INFRA-04-T02 mode=serial locks=backup-restore,live-environment -->
- [ ] **Execute every pre-revenue DR scenario —** Input: current small-VPS release, encrypted R2 chain and runbooks. Operation: perform documented crash/loss/tunnel/R2/restore/action-ambiguity/control-generation scenarios and measure actual RPO/RTO. Output: signed DR evidence. Test evidence: scenario set equality and first-failure retention. Failure behavior: M8 remains blocked.
<!-- roadmap-task id=INFRA-05-T07 milestone=M8 depends_on=INFRA-05-T06,INFRA-04-T06 mode=serial locks=backup-restore,live-environment -->
- [ ] **Operate freshness and re-enable gates —** Input: current DR/restore/alert/capacity evidence. Operation: expire old evidence, deny re-enable on missing R2/Cloudflare/action reconciliation and require fresh command authority. Output: bounded operations gate. Test evidence: stale drill, capacity breach, unresolved send/booking and tunnel-alert failure. Failure behavior: relevant authority remains off.
<!-- roadmap-task id=INFRA-05-T08 milestone=M8 depends_on=INFRA-05-T07 mode=parallel locks=observability -->
- [ ] **Close command/DR scenario sets and deferred enterprise upgrades —** Input: all M8 ops requirements. Operation: prove exact coverage and mark multi-cloud/managed-KMS/HA/enterprise-on-call scenarios post-revenue rather than hidden prerequisites. Output: signed coverage. Test evidence: orphan/duplicate/hidden-enterprise-dependency negatives. Failure behavior: M8 remains open.

## Acceptance

- [ ] Small-VPS/Cloudflare/R2 failures are observable without the private app UI.
- [ ] Clean-host restore and action reconciliation are exercised.
- [ ] Actual RPO/RTO and 2-vCPU/4-GB capacity limits are measured.
- [ ] Re-enable fails closed on stale backup/alert/capacity/provider truth.
- [ ] Multi-cloud/KMS/HA/enterprise on-call remain deferred until revenue or evidence justifies them.
