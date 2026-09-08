# Autonomous Sales-Validation Roadmap Design

**Date:** 2026-09-08

**Status:** Approved through the referenced design conversation and the user's instruction to proceed

**Audience:** The solo operator, roadmap maintainers, and every agent implementing Alon AI

## Purpose

Replace the roadmap's validation-assistant model with an autonomous but bounded sales-validation system. The system discovers or accepts an idea, researches the market, creates one authoritative commercial offer, discovers and qualifies businesses, conducts evidence-backed email conversations inside deterministic safety and commercial limits, books a qualified call after explicit confirmation, evaluates every cohort checkpoint, and learns globally through versioned strategies.

This design supersedes the staged-validation design where that document requires routine manual message approval, one-way outreach, zero follow-ups, campaign-isolated learning, or no booking. It preserves the exact `100/200/300/400` incremental cohorts, `100/300/600/1,000` cumulative checkpoints, the 1,000-recipient ceiling, and the deterministic `SendGateway`.

## Product boundary

Alon AI is planned as a private, single-operator system. It is not an unrestricted autonomous closer. Its objective is to maximize qualified commitments and confirmed booked calls while preserving truthful claims, recipient choice, provider rules, legal-policy evidence, margin floors, and sender reputation.

The optional user-supplied idea is the only manual bypass inside the normal agent pipeline. The operator may also configure or tighten the pre-run offer economics, source allowlist, commercial envelope, legal-policy facts, budgets, and kill switches. Routine in-envelope drafts, replies, negotiations, checkpoint transitions, and bookings do not wait for per-message approval. Unsafe, ambiguous, stale, or out-of-envelope cases enter an exception and incident queue.

No roadmap statement authorizes real outreach by itself. Live operation remains gated by retained provider, security, legal-policy, deliverability, recovery, and launch evidence.

## Canonical runtime sequence

| Order | Responsibility | Kind | Authoritative output or transition |
| ---: | --- | --- | --- |
| 1 | Idea Discovery | agent, optional | `IdeaBrief` |
| 2 | Market Research | agent | `MarketResearchReport` |
| 3 | Offer Design | agent | `OfferPackage` |
| 4 | Lead Discovery and Preliminary Qualification | agent proposal plus deterministic admission | `LeadDiscoveryCandidate` and preliminary `QualificationDecision` |
| 5 | Deep Lead Research | agent | `LeadResearchDossier` |
| 6 | Final Lead Qualification | agent proposal plus deterministic gate | final `QualificationDecision` |
| 7 | Personalized Email Writing | agent | `ConversationStrategy` and `EmailDraft` |
| 8 | Deterministic Email Sending | application service | immutable action authorization, send intent, provider attempt, and reconciled result |
| 9 | Reply Evaluation, Negotiation, and Conversation Control | agent proposal plus deterministic policy | `ReplyEvaluation` and `NegotiationDecision` |
| 10 | Call Booking | deterministic booking service/provider boundary | `BookingIntent` and reconciled booking state |
| 11 | Checkpoint Experiment Evaluation | agent proposal plus deterministic stage transition | `CheckpointEvidenceBundle` and authoritative checkpoint decision |
| 12 | Global Checkpoint Learning | agent analysis plus deterministic promotion/activation | `AgentLearningProposal`, `GlobalStrategyPackage`, and `StrategyActivation` |

The pipeline may execute per-lead work concurrently inside a frozen cohort, but no consumer may run before its authoritative provider exists. Runtime order is enforced by artifact references and state-machine guards, not by filenames.

## Idea origin and commercial authority

An experiment has exactly one idea origin:

- `DISCOVERED`: Idea Discovery produces the immutable `IdeaBrief`.
- `USER_SUPPLIED`: the frontend accepts the idea and a deterministic materializer creates the same validated `IdeaBrief` shape while recording the bypass and user provenance.

Market Research always consumes an accepted `IdeaBrief`. Offer Design always consumes both `IdeaBrief` and `MarketResearchReport`.

Offer Design is the sole commercial authority for every downstream step. Its immutable `OfferPackage` contains the target customer, problem, solution, positioning, scope, deliverables, base price, cost assumptions, currency and rounding version, minimum price, margin floor, discount bands, payment terms, qualification filters, approved pilots and scope variants, negotiation options, exclusions, proof, claim-to-evidence mappings, outreach claims, booking constraints, validity interval, version, and content hash.

No downstream agent may invent or independently redefine price, margin, scope, deliverables, guarantees, claims, exclusions, qualification rules, or commercial terms. Offer Design provides nothing upstream to Idea Discovery or Market Research.

## Versioned inter-agent artifacts

The exact canonical artifact set is:

1. `IdeaBrief`
2. `MarketResearchReport`
3. `OfferPackage`
4. `LeadDiscoveryCandidate`
5. `LeadResearchDossier`
6. `QualificationDecision`
7. `ConversationStrategy`
8. `EmailDraft`
9. `ReplyEvaluation`
10. `NegotiationDecision`
11. `BookingIntent`
12. `CheckpointEvidenceBundle`
13. `AgentLearningProposal`
14. `GlobalStrategyPackage`
15. `StrategyActivation`

Every artifact has an immutable ID, schema version, producer, producer strategy version, input snapshot ID/hash, output hash, evidence references, created timestamp, disposition, and supersession linkage. Every downstream input traces to its provider's accepted artifact version and hash.

`QualificationDecision` carries `PRELIMINARY` or `FINAL` phase so there is one artifact name with an explicit stage rather than two ambiguous aliases. `ConversationStrategy` does not establish commercial terms; it references the governing `OfferPackage` and selects only permitted messaging objectives. `GlobalStrategyPackage` can change agent strategies but cannot change immutable safety or commercial bounds.

## Lead discovery, research, and qualification

Lead Discovery searches only approved adapters and source-specific scopes, initially including Google Maps and other reviewed public business sources. Social and directory sources are added only through explicit provider contracts; the roadmap must not promise Instagram, TikTok, or arbitrary crawling before the relevant adapter, terms review, and evidence tests exist.

Discovery records source provenance, source time, query/filter version, business identity evidence, deduplication keys, preliminary facts, unknowns, and an inexpensive preliminary qualification result. It never fabricates a person, role, owner, email address, phone number, or linkage.

Only preliminarily qualified candidates receive expensive Deep Lead Research. Deep research records the business, decision-maker or owner when supported, services, size signals, likely problems, relevant events, technologies, reputation, and personalization evidence. Every field is `FACT`, `ESTIMATE`, or `UNKNOWN`, with source evidence and confidence.

Final Lead Qualification re-applies the immutable filters from the governing `OfferPackage` to the research dossier. It produces an evidence-backed qualify/reject result. Deterministic identity, suppression, legal-policy, capacity, and cohort admission checks remain separate and cannot be overridden by the agent's recommendation.

## Autonomous conversation and deterministic sending

The Email Writer creates initial and reply drafts. It receives only authorized business/person facts, the accepted research dossier, final qualification, the governing offer and strategy versions, the complete sanitized conversation state, and exact instructions from Reply Evaluation. It never receives Gmail credentials or a send capability.

`SendGateway` remains the sole application path that can invoke the Gmail send port. No agent, workflow, API route, or generic provider wrapper may bypass it. Routine manual message approval is removed from the normal path. Before every send, deterministic code freshly validates:

- suppression, unsubscribe, complaint, bounce, and contact-frequency state;
- recipient and thread identity;
- campaign, cohort, stage, and remaining capacity;
- conversation state and reply-loop limit;
- accepted `OfferPackage`, `GlobalStrategyPackage`, and `StrategyActivation` versions;
- claim-to-evidence coverage and draft freshness;
- provider, jurisdiction, and legal-policy restrictions;
- rate, cost, and budget reservations;
- duplicate, stale, superseded, or already-reconciled messages;
- commercial price, margin, scope, discount, timing, and payment limits;
- current campaign/checkpoint/control generation; and
- global, campaign, mailbox, provider, and conversation kill switches.

Each authorization, intent, attempt, provider observation, and result is immutable and idempotent. An ambiguous provider result is quarantined. Zero search/history results do not prove non-send and never authorize a blind retry.

Any inbound reply atomically stops the cold sequence. It does not automatically create permanent suppression. Clear unsubscribe, complaint, rejection with no permitted future contact, hard bounce, or applicable legal signal creates the appropriate stop/suppression. Positive replies, questions, and genuine objections may enter the bounded response loop. Unsafe or ambiguous intent pauses the conversation and enters the exception queue.

## Deterministic commercial policy and bounded negotiation

`CommercialPolicyEngine` is pure deterministic code over stored, versioned inputs. Model output may propose an action, but the engine calculates and approves the commercial result.

Allowed proposals are limited to:

- explain the accepted offer;
- answer an evidence-backed objection;
- select an approved scope variant;
- offer an approved pilot;
- choose an approved discount band;
- adjust timing, bundle, or payment schedule inside the package;
- ask for missing decision information; and
- propose a call.

The system may never:

- go below the minimum price or contribution-margin floor;
- treat inferred budget as stated budget;
- invent budget, urgency, facts, proof, results, or familiarity;
- promise unsupported outcomes or create unauthorized deliverables;
- change legal terms;
- ignore a rejection, unsubscribe, complaint, suppression, or safety stop;
- exceed round, message, frequency, or time-window limits; or
- represent an unaccepted proposal as a commitment or deal.

Every budget assertion is `STATED`, `INFERRED`, or `UNKNOWN`, with currency, range, source span, confidence, and timestamp. Only `STATED` budget may satisfy a stated-budget condition. Taxes, fees, delivery cost, currency conversion, rounding, margin, and discount calculations use stored deterministic versions.

## Booking

A booking begins only after qualified buying intent and an accepted `BookingIntent`. The scheduling boundary exposes separate read and write ports. A calendar adapter may read bounded availability; only `BookingGateway` may create, reschedule, or cancel an event.

The first planned adapter is Google Calendar, but calendar-provider interfaces are product-owned so no workflow depends directly on Google-specific types. The booking flow:

1. derives available slots from the authorized calendar and booking policy;
2. presents timezone-aware slots with explicit timezone labels;
3. records the lead's explicit slot confirmation;
4. revalidates identity, availability, offer/context, and conversation state;
5. creates the event idempotently;
6. reconciles ambiguous provider outcomes before any retry; and
7. attaches business, contact, campaign, conversation, offer, and evidence references to the dashboard booking projection.

Ambiguous agreement is not confirmation. Event creation, rescheduling, cancellation, duplicate callbacks, DST boundaries, attendee notification behavior, and provider conflicts are independently idempotent and auditable.

## Checkpoints and global learning

The incremental cohorts remain `100`, `200`, `300`, and `400`, with cumulative checkpoints at `100`, `300`, `600`, and `1,000`. At every checkpoint, Checkpoint Experiment Evaluation produces exactly one authoritative result:

- `CONTINUE`
- `REVISE`
- `KILL`
- `INCONCLUSIVE`
- `SAFETY_STOP`

Only `CONTINUE` can make a campaign eligible for its next stage, and deterministic capacity/safety checks still control actual admission. At the 1,000 ceiling, `CONTINUE` records a positive terminal checkpoint but never opens an unregistered fifth cohort or exceeds the ceiling.

There is one strategy-learning mechanism. Operational per-thread memory is not learning.

Whenever a campaign closes a checkpoint:

1. freeze an immutable `CheckpointEvidenceBundle` for the newly completed stage;
2. treat that triggering campaign and stage as primary evidence;
3. use similar campaigns as secondary evidence;
4. use all relevant historical campaigns, failures, and incidents as guardrail evidence;
5. evaluate every applicable agent; and
6. produce versioned, measurable, reversible proposals.

The exact per-agent result set is:

- `PROMOTE`
- `KEEP`
- `ROLLBACK`
- `INSUFFICIENT_EVIDENCE`

`KEEP` means evidence supports retaining the current strategy. `INSUFFICIENT_EVIDENCE` means no change is justified. Both are no-mutation behavior; `NO_CHANGE` may be used in explanatory prose but is not a fifth serialized result.

The learning engine cannot freely rewrite production prompts or policies. Promotion requires immutable lineage, minimum evidence, offline evaluation, comparison with the current version, protected holdout cases, cross-campaign guardrails, expected metrics, confidence, and rollback conditions. Immutable safety, legal-policy, suppression, source, and commercial constraints are never learnable.

Activation rules are exact:

- the triggering campaign adopts the approved version only at its next cohort boundary and only if its checkpoint result is `CONTINUE`;
- other active campaigns adopt it only when they reach their own next checkpoint;
- future campaigns start with the newest approved global version;
- a running cohort never changes offer, strategy, qualification rules, causal variables, or evidence definitions halfway through;
- a rollback affects future actions and never rewrites historical attribution; and
- monitored deterioration triggers automatic rollback according to the stored rule.

Every individual agent call, policy decision, draft, send, negotiation proposal, booking action, checkpoint, and learning decision records the exact strategy version and activation that governed it.

## Data, retention, and privacy

The roadmap must plan explicit records for offer economics; businesses, people, identities, sources, and evidence; preliminary and final qualification; complete threads and reply classifications; negotiation state and proposals; stated/inferred budget; booking intent/slots/status/provider events; cohort membership and checkpoint ownership; immutable agent inputs/outputs; checkpoint evidence; strategy versions/activations/rollback; and action-level governing versions.

"Save what learning needs" is not permission to retain everything forever. Every table and sensitive field has a purpose, sensitivity class, encryption/redaction rule, allowed readers/writers, telemetry prohibition, retention clock, legal-hold behavior, deletion order, backup expiry, and restoration rule. Raw contact data, message bodies, calendar details, and sensitive inferred attributes are excluded from metrics and global learning unless a minimized, approved evidence transform exists.

Web pages and inbound email are untrusted data, never instructions. Prompt-injection indicators are evidence, not a sufficient safety proof. Tool scopes, typed inputs, provenance, content redaction, deterministic post-model validation, and least-privilege provider capabilities remain mandatory.

## Frontend

The dashboard exposes server-authoritative views for:

- discovered versus user-supplied idea origin;
- market research and accepted offer package;
- offer economics and immutable negotiation envelope;
- lead sources, filters, candidates, dossiers, and preliminary/final decisions;
- complete redacted message, reply, negotiation, and booking timeline;
- automatic-send state and deterministic blocked reasons;
- `INTERESTED`, `NEGOTIATING`, `COMMITTED`, and `BOOKED` pipeline states;
- timezone-aware calendar and booking status;
- checkpoint evidence and stage decision;
- global strategy versions, per-agent results, evidence, activations, and rollbacks; and
- exception and incident queue.

The approval inbox is not part of the routine send path. The UI cannot manufacture authorization, recalculate commercial policy, call provider write operations, mutate a frozen cohort, or activate a strategy mid-cohort.

## Observability and evaluation

Metrics are attributable to both agent strategy version and cohort. Required measures include discovery yield/duplicates, research coverage/factual accuracy, qualification precision, personalization evidence coverage, delivery/bounce/complaint/reply rates, positive replies, qualified commitments, objection categories/resolution, negotiation outcome/discount/margin/scope change, booking/show rate, cost per qualified lead/commitment/booking, pre/post activation performance, learning promotion/rollback rate, and cross-campaign transfer performance.

Telemetry uses low-cardinality IDs and versions; it excludes message bodies, recipient identities, inferred sensitive attributes, calendar descriptions, and credentials.

## Testing and launch

The roadmap must require contract tests for all fifteen artifacts; dependency order; hallucination/evidence failures; multi-source deduplication; preliminary-versus-final qualification; email-writing/sending separation; reply loops and terminal states; commercial boundaries; booking idempotency/timezones/rescheduling/cancellation; checkpoint-triggered learning; cross-campaign activation; no mid-cohort mutation; weak-evidence no-change; rollback; crash/replay at every durable boundary; and a complete campaign simulation.

Launch evidence progresses in this order:

1. synthetic agent pipeline;
2. recorded provider fixtures;
3. owned test-inbox conversations;
4. simulated objections and negotiation;
5. test calendar bookings;
6. checkpoint and global-learning simulation;
7. tightly controlled real campaign; and
8. earned autonomous sending and negotiation.

The first six phases cannot count as real demand evidence. Real cohorts remain capped by the smaller applicable legal, provider, reputation, budget, and configured limits.

## Roadmap migration rules

- Rename user-facing agent documents into canonical sequence while preserving stable historical `Document ID`/task prefixes where that avoids unsafe mass dependency churn. Runtime order is established by artifact and task dependencies, never filename numbers.
- Add new documents for Lead Discovery, Global Learning, Booking workflow/provider, Checkpoint workflow, and Global Learning workflow.
- Keep shared agent evaluation/versioning after Global Learning and extend its registries to every agent.
- Replace routine approval contracts with deterministic `ActionAuthorityScopeV1`; retain operator intervention only for exceptions, incidents, kill/recovery, protected legal decisions, and explicit strategy controls.
- Split Gmail read/sync capability from the gateway-only write capability. Add independent calendar read/write capability and a serial `calendar-side-effects` lock.
- Replace closed table, operation, agent, artifact, event, metric, and retention manifests atomically; do not leave outdated exact counts.
- Add a machine-readable canonical sales contract to product scope. The roadmap validator parses it, verifies semantic invariants, and includes it in the generated fingerprint/manifest.
- Regenerate `execution-manifest.json`, `EXECUTION_ORDER.md`, and `AGENT_EXECUTION_PLAN.md` only after every authoritative source task is updated.
- Supersede the old staged-validation spec and plan rather than retaining contradictory non-goals.
- Run Graphify's documentation-aware incremental workflow after tracked roadmap changes; generated graph files remain local and ignored.

## Non-goals

This roadmap rewrite does not implement the product, authorize a real campaign, provide legal advice, promise that every source can be scraped, add payment collection, allow direct agent access to Gmail or a calendar write API, permit uncontrolled prompt rewriting, or allow campaign volume above 1,000. Payment remains a future end state; version one ends at an explicit qualified commitment and confirmed booked call.
