# Staged Thousand-Lead Validation Design

**Date:** 2026-09-08<br>
**Status:** Approved in chat; awaiting written-spec review<br>
**Audience:** Solo operator and every agent implementing or running Alon AI experiments

## Purpose

Replace the roadmap's underpowered first-real-experiment envelope with one pre-registered, staged validation program that may reach 1,000 unique delivered recipients. The program uses four incremental cohorts of 100, 200, 300, and 400 new recipients. Each cohort closes behind an evidence barrier before another recipient can be admitted.

The change preserves an important distinction: agent research establishes that an idea and offer are plausible enough to test, but only observed buyer behavior establishes demand. Market research, contradictions, citations, scoring, and operator review remain prerequisites; they do not count as replies, qualified conversations, or paid commitments.

## Problem being corrected

The current roadmap has two incompatible demand-testing contracts:

- PRODUCT-02 defaults to 50 delivered recipients before a negative demand decision can be made.
- LAUNCH-03 limits the first real experiment to ten recipients and therefore normally forces `INCONCLUSIVE`.

Ten recipients are useful for proving safe delivery mechanics, not for evaluating a low-frequency B2B funnel. Conversely, releasing all 1,000 recipients at once would waste scarce prospects and destroy causal clarity if targeting, positioning, deliverability, or the offer is wrong. The staged program must support a serious sample while retaining stop-loss controls.

## Fixed cohort schedule

| Stage | New unique delivered recipients | Cumulative maximum | Primary purpose |
| --- | ---: | ---: | --- |
| `STAGE_1_SIGNAL` | 100 | 100 | Detect catastrophic targeting, message, deliverability, or demand failure |
| `STAGE_2_CONFIRM` | 200 | 300 | Confirm the signal across at least two pre-registered subsegments |
| `STAGE_3_REPEAT` | 300 | 600 | Test repeatability and identify the strongest supported subsegment |
| `STAGE_4_ESTIMATE` | 400 | 1,000 | Estimate the complete delivered-to-reply-to-conversation-to-paid-commitment funnel |

The numbers are incremental, not cumulative batch sizes. A recipient belongs to exactly one cohort and may receive at most the campaign's approved message sequence. The same business, person, normalized recipient identity, or suppression identity cannot be recycled into a later cohort to satisfy a count.

The 1,000-recipient value is a hard program ceiling, not a target the system must consume. A stop, kill, revise, expired window, exhausted reachable market, compliance restriction, or economic failure can close the program below 1,000.

## Entry prerequisites

No real-recipient cohort opens until the existing M0-M8 safety, workflow, provider, policy, security, test-inbox, observability, backup, and recovery gates pass. In addition, the operator freezes and signs:

- one experiment brief and idea version;
- one offer version and pricing hypothesis;
- one campaign/message-strategy version;
- one mailbox and sender identity;
- one jurisdiction, compliance policy, disclosure, and legal-review tuple;
- qualification criteria and recipient-source allowlist;
- the four cohort sizes and subsegment allocation;
- stage-specific budgets, delivery-rate caps, reply windows, and decision thresholds;
- the exact metrics and queries used by every barrier; and
- immutable accepted agent artifacts and market evidence, including contradictions and disconfirming signals.

Changing a major hypothesis after entry never mutates the active program. It closes the current version and creates a new experiment, offer, campaign, and decision-rule version as applicable.

## Stage execution contract

Each stage follows the same finite state sequence:

1. Admit only the next cohort's qualified, deduplicated, unsuppressed, policy-eligible recipients.
2. Reserve the stage budget before provider work.
3. Create and approve immutable message versions through the existing policy and approval authority.
4. Deliver under the configured daily/hourly provider limits and global controls.
5. Reconcile every attempted send, ambiguous outcome, bounce, complaint, opt-out, reply, cost, and suppression effect.
6. Wait until the pre-registered observation window closes.
7. Freeze a stage snapshot from authoritative records.
8. Apply exactly one barrier decision before any next-stage admission.

The workflow may prepare later candidates, but it may not approve, enqueue, or send to them while the current barrier is open. Cohort admission and the cumulative delivered count use serializable database authority so concurrent workers cannot exceed a cap.

## Barrier decisions

Every stage ends in exactly one of these outcomes:

- `CONTINUE`: all safety gates are green and the stage meets its pre-registered demand, deliverability, quality, and economic continuation thresholds. Only this decision opens the next cohort.
- `REVISE`: evidence identifies one correctable major hypothesis. The active program closes; the operator changes exactly one major hypothesis and starts a separately versioned program. Uncontacted recipients may be reconsidered only after fresh qualification and policy checks.
- `KILL`: demand, contribution margin, market reachability, or another product criterion fails its registered kill rule. No later cohort opens.
- `INCONCLUSIVE`: the window or eligible sample ends without adequate evidence. No later cohort opens automatically; the operator must register a separately justified experiment.
- `SAFETY_STOP`: any complaint, suppression, consent, policy, provider ambiguity, credential, budget, audit, telemetry, backup, or deliverability safety trigger fires. Sending stops immediately regardless of demand.

`CONTINUE` is permission to expose only the next cohort. It is not an assertion that the idea is validated, and it never overrides a safety stop.

## Demand and economic evidence

The program records raw counts and pre-registered rates for:

- admitted, attempted, delivered, bounced, complained, opted-out, replied, and positively replied recipients;
- qualified conversations, explicit paid commitments, and realized initial revenue;
- source and subsegment coverage;
- provider spend and operator time;
- cost per qualified lead, positive reply, qualified conversation, and paid commitment;
- projected contribution margin at the tested price; and
- uncertainty intervals or an explicit statement that the sample is not adequate for the claimed precision.

Automated replies, duplicate recipients, internal/test addresses, undelivered messages, late observations outside the registered window, and unverified commitments are excluded from demand numerators. A positive reply alone is not final validation. The final recommendation must consider paid commitment evidence, delivery feasibility, contribution margin, operator capacity, and unresolved contradictions.

Exact numeric continuation and kill thresholds must be defined in the roadmap's PRODUCT-02 authority before implementation. They must be internally consistent across all four stages and supported by deterministic query fixtures. No downstream document may invent weaker thresholds.

## Subsegment discipline

Stage 1 may test one narrowly defined ICP. Before Stage 2, the program freezes at least two meaningful subsegments or records why the reachable ICP is legitimately indivisible. Stages 2 and 3 preserve allocation counts so the system can distinguish a broad offer signal from one winning niche. Stage 4 allocates recipients according to the pre-registered estimation design; it may not silently concentrate only on early winners and then claim whole-market performance.

Message personalization may vary by recipient facts, but the promise, price, call to action, and other causal offer variables remain version-locked. An approved experiment may compare variants only if allocation, sample, metrics, and stopping rules were registered before exposure.

## Safety and compliance invariants

Scaling the sample does not weaken the existing authority model:

- agents cannot authorize Gmail sends, legal conclusions, policy exceptions, suppression changes, or cap increases;
- every recipient must have the evidence required by the active compliance policy and legal review;
- suppression is checked at admission, approval, final send, and immediately after recipient signals;
- replies, opt-outs, complaints, hard bounces, and configured soft-bounce limits prevent later sends as already defined by policy;
- every send remains idempotent and every ambiguous provider outcome remains quarantined until reconciled;
- the global kill switch and separate product-outreach control remain authoritative;
- public unsubscribe/suppression obligations survive campaign or program closure; and
- legal and provider-policy requirements may impose a lower cap or narrower channel than this product ceiling.

The implementation must not encode “1,000” as permission to send cold email regardless of jurisdiction, consent, provider terms, reputation, or legal review.

## Roadmap changes required

The implementation plan must inspect and update every source contract that owns or consumes real-experiment volume, including at minimum:

- PRODUCT-02 metrics, thresholds, decisions, and tests;
- PRODUCT-03 risk and kill criteria;
- DB-02 experiment/campaign cohort and decision records;
- DB-03 lead/campaign/message uniqueness and cohort membership;
- DB-05 budgets, suppression, caps, and idempotency;
- WF-02 experiment lifecycle;
- WF-04 lead discovery and qualification capacity;
- WF-05 outreach, reply, pause, resume, and recovery behavior;
- BACKEND-02, BACKEND-03, BACKEND-04, BACKEND-05, and BACKEND-06 commands, policies, sending, controls, and reporting;
- FRONTEND experiment setup, campaign control, approvals, funnel, and decision views;
- SEC-04 and SEC-05 compliance, suppression, budgets, rate limits, and kill-switch rules;
- OBS-02 and OBS-03 metrics, alerts, and cost accounting;
- TEST-02 through TEST-06 contract, recovery, Gmail, browser, load, security, and chaos evidence;
- LAUNCH-03 first real experiment; and
- LAUNCH-04 earned-autonomy boundaries, which must not convert staged real-recipient sending into autonomous authority.

The executable roadmap metadata, manifest, topological order, and agent execution plan must be regenerated from the changed source tasks. The validator must reject legacy ten-recipient rules, conflicting 50-recipient final-decision rules, cumulative/incremental ambiguity, missing barriers, duplicate cohort membership, and any path that admits a later cohort without the prior signed decision.

## Verification requirements

Roadmap completion requires:

- exact-text scans proving one canonical `100/200/300/400` incremental schedule and 1,000 cumulative ceiling;
- zero contradictory ten-recipient, 50-recipient, or immediate-1,000-send authority remaining in active contracts;
- dependency validation, cycle detection, lock validation, and regenerated artifact checks;
- deterministic stage-transition and cap boundary fixtures;
- duplicate-recipient and cross-cohort race tests;
- tests proving every non-`CONTINUE` decision prevents later admission;
- tests proving safety triggers override `CONTINUE` and demand evidence;
- reporting tests that show incremental and cumulative denominators separately;
- full lint, type-check, test, build, secret-scan, and diff-integrity gates; and
- a final whole-branch review before publication to `main`.

## Non-goals

This design does not authorize real sending, select exact legal rules, guarantee that 1,000 eligible leads exist, guarantee statistical significance, automate offer pivots, add automated follow-ups, or claim that agent research proves product-market fit. It changes the planned experiment envelope and evidence system; implementation of the roadmap remains separate.
