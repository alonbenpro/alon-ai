# Executable Roadmap Order

> Warning: generated; it does not prove implementation status. Edit source task metadata, never this file.

- Regenerate: `python3 scripts/validate_roadmap.py --write`
- Validate: `python3 scripts/validate_roadmap.py --check`
- Source-graph fingerprint: `8962eea55212f5c50dcce29ccbdbfbe1b35200ddab922cc25c75924fae469127`

## Totals

- Tasks: 406
- Documents: 77
- M0: 8
- M1: 33
- M2: 29
- M3: 75
- M4: 28
- M5: 9
- M6: 72
- M7: 42
- M8: 91
- M9: 19
- By document:
  - `PRODUCT-01`: 4
  - `PRODUCT-02`: 4
  - `PRODUCT-03`: 4
  - `ARCH-01`: 6
  - `ARCH-02`: 5
  - `ARCH-03`: 5
  - `WF-00`: 5
  - `WF-01`: 6
  - `DB-01`: 5
  - `DB-02`: 5
  - `DB-03`: 6
  - `DB-04`: 5
  - `DB-05`: 5
  - `DB-06`: 5
  - `AGENT-01`: 5
  - `AGENT-02`: 4
  - `AGENT-03`: 4
  - `AGENT-04`: 4
  - `AGENT-05`: 4
  - `AGENT-06`: 4
  - `AGENT-07`: 4
  - `AGENT-08`: 4
  - `AGENT-09`: 4
  - `AGENT-10`: 6
  - `PROVIDER-03`: 6
  - `PROVIDER-04`: 5
  - `PROVIDER-05`: 5
  - `PROVIDER-06`: 5
  - `WF-02`: 5
  - `WF-03`: 5
  - `BACKEND-01`: 6
  - `BACKEND-02`: 5
  - `WF-04`: 5
  - `PROVIDER-01`: 6
  - `PROVIDER-02`: 5
  - `WF-05`: 6
  - `WF-06`: 5
  - `BACKEND-03`: 5
  - `BACKEND-04`: 5
  - `BACKEND-05`: 7
  - `SEC-03`: 5
  - `SEC-04`: 6
  - `SEC-05`: 5
  - `OBS-01`: 7
  - `OBS-03`: 5
  - `TEST-03`: 7
  - `TEST-04`: 6
  - `FRONTEND-01`: 5
  - `FRONTEND-02`: 4
  - `FRONTEND-03`: 5
  - `FRONTEND-04`: 4
  - `FRONTEND-05`: 5
  - `FRONTEND-06`: 4
  - `FRONTEND-07`: 4
  - `FRONTEND-08`: 4
  - `FRONTEND-09`: 5
  - `BACKEND-06`: 5
  - `SEC-02`: 6
  - `SEC-01`: 5
  - `SEC-06`: 5
  - `OBS-02`: 5
  - `OBS-04`: 5
  - `OBS-05`: 6
  - `TEST-01`: 6
  - `TEST-02`: 7
  - `TEST-05`: 6
  - `TEST-06`: 6
  - `INFRA-01`: 8
  - `INFRA-02`: 6
  - `INFRA-03`: 8
  - `INFRA-04`: 8
  - `INFRA-05`: 8
  - `LAUNCH-01`: 6
  - `LAUNCH-02`: 5
  - `LAUNCH-03`: 5
  - `LAUNCH-04`: 5
  - `LAUNCH-05`: 5

## Frontier rule

A task is executable only when every dependency has retained passing evidence from an earlier completed wave.

## M0

1. `PRODUCT-01-T01` — Capture the M0 bet ([source](00-product-strategy/01-product-scope.md#L137)); dependencies: none
2. `PRODUCT-01-T02` — Run the narrowness test ([source](00-product-strategy/01-product-scope.md#L139)); dependencies: `PRODUCT-01-T01`
3. `PRODUCT-01-T03` — Register artifact and authority vocabulary ([source](00-product-strategy/01-product-scope.md#L141)); dependencies: `PRODUCT-01-T02`
4. `PRODUCT-01-T04` — Freeze non-goals for the first experiment ([source](00-product-strategy/01-product-scope.md#L143)); dependencies: `PRODUCT-01-T03`
5. `PRODUCT-02-T01` — Register metric and staged-decision definitions ([source](00-product-strategy/02-success-metrics.md#L122)); dependencies: `PRODUCT-01-T02`
6. `PRODUCT-02-T02` — Capture baseline evidence ([source](00-product-strategy/02-success-metrics.md#L124)); dependencies: `PRODUCT-02-T01`
7. `PRODUCT-03-T01` — Approve M0 risk posture ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L111)); dependencies: `PRODUCT-01-T02`, `PRODUCT-02-T01`
8. `PRODUCT-03-T02` — Review sunk-cost exposure at every gate ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L113)); dependencies: `PRODUCT-03-T01`

## M1

9. `WF-00-T01` — Freeze runtime responsibility map ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L67)); dependencies: `PRODUCT-01-T03`
10. `SEC-01-T01` — Freeze the planned asset and Critical threat-control registry ([source](08-security-and-compliance/01-threat-model.md#L101)); dependencies: `PRODUCT-03-T01`
11. `DB-03-T01` — Publish pure Gmail-facing composite contracts ([source](02-database/03-leads-campaigns-and-messages.md#L659)); dependencies: `PRODUCT-01-T03`, `SEC-01-T01`
12. `SEC-03-T01` — Implement the key/object contracts ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L82)); dependencies: `SEC-01-T01`
13. `PROVIDER-01-T01` — Freeze disposable Gmail OAuth and wire contracts ([source](05-providers/01-gmail-oauth-and-adapter.md#L165)); dependencies: `DB-03-T01`, `SEC-03-T01`
14. `PROVIDER-01-T02` — Implement strict send contracts and MIME builder ([source](05-providers/01-gmail-oauth-and-adapter.md#L167)); dependencies: `PROVIDER-01-T01`, `DB-03-T01`
15. `PROVIDER-02-T01` — Implement strict read adapter ([source](05-providers/02-gmail-history-sync.md#L85)); dependencies: `PROVIDER-01-T01`
16. `TEST-01-T01` — Freeze the coverage registry ([source](10-testing/01-testing-strategy.md#L144)); dependencies: `PRODUCT-01-T03`
17. `TEST-01-T02` — Freeze and parse the command registry ([source](10-testing/01-testing-strategy.md#L146)); dependencies: `TEST-01-T01`
18. `TEST-01-T03` — Build environment and fixture isolation ([source](10-testing/01-testing-strategy.md#L148)); dependencies: `TEST-01-T02`
19. `TEST-04-T01` — Build strict offline Gmail fixtures ([source](10-testing/04-gmail-side-effect-tests.md#L60)); dependencies: `PROVIDER-01-T02`, `TEST-01-T03`, `PROVIDER-01-T01`
20. `TEST-04-T02` — Close offline Gmail command ownership ([source](10-testing/04-gmail-side-effect-tests.md#L62)); dependencies: `TEST-04-T01`, `TEST-01-T02`, `PROVIDER-01-T01`
21. `TEST-01-T04` — Implement evidence capture ([source](10-testing/01-testing-strategy.md#L150)); dependencies: `TEST-01-T03`
22. `WF-01-T01` — Provision the isolated harness from attested external resources ([source](03-workflows/01-dbos-production-acceptance-spike.md#L196)); dependencies: `WF-00-T01`, `SEC-01-T01`, `TEST-01-T01`, `TEST-01-T02`, `TEST-01-T03`, `TEST-01-T04`
23. `WF-01-T02` — Implement typed finite fixture and sole gateway ([source](03-workflows/01-dbos-production-acceptance-spike.md#L198)); dependencies: `WF-01-T01`
24. `WF-01-T03` — Implement kill/reconciliation instrumentation ([source](03-workflows/01-dbos-production-acceptance-spike.md#L200)); dependencies: `WF-01-T02`
25. `PRODUCT-03-T03` — Encode the reusable fail-closed stop interface ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L115)); dependencies: `PRODUCT-03-T02`, `WF-01-T03`
26. `ARCH-01-T01` — Run M1 DBOS production acceptance ([source](01-architecture/01-target-system-architecture.md#L131)); dependencies: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`
27. `WF-00-T02` — Execute WF-01 acceptance suite ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L69)); dependencies: `WF-00-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`
28. `WF-01-T04` — Run eight-item matrix from clean state ([source](03-workflows/01-dbos-production-acceptance-spike.md#L202)); dependencies: `WF-01-T03`
29. `TEST-03-T01` — Build the process-level kill harness ([source](10-testing/03-workflow-recovery-tests.md#L63)); dependencies: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-01-T03`
30. `TEST-03-T02` — Execute the independent M1 runtime matrix ([source](10-testing/03-workflow-recovery-tests.md#L65)); dependencies: `TEST-03-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-01-T04`
31. `WF-01-T05` — Export evidence and dispose schema ([source](03-workflows/01-dbos-production-acceptance-spike.md#L204)); dependencies: `WF-01-T04`, `TEST-03-T02`
32. `TEST-03-T03` — Independently verify the exported M1 acceptance or rejection bundle ([source](10-testing/03-workflow-recovery-tests.md#L67)); dependencies: `TEST-03-T02`, `WF-01-T05`
33. `WF-00-T03` — Emit the signed discriminated DBOS gate ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L71)); dependencies: `WF-00-T02`, `TEST-03-T03`, `WF-01-T05`
34. `WF-00-T04` — Resolve one selected runtime and execute fallback only on rejection ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L73)); dependencies: `WF-00-T03`
35. `WF-00-T05` — Reconsider adjacent layers only from new evidence ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L75)); dependencies: `WF-00-T04`
36. `WF-01-T06` — Verify the converged selected-runtime branch ([source](03-workflows/01-dbos-production-acceptance-spike.md#L206)); dependencies: `WF-01-T05`, `WF-00-T04`
37. `INFRA-01-T01` — Freeze prerequisites and preflight ([source](11-infrastructure/01-local-development.md#L63)); dependencies: `TEST-01-T02`
38. `INFRA-01-T02` — Implement isolated host/Compose modes ([source](11-infrastructure/01-local-development.md#L65)); dependencies: `INFRA-01-T01`
39. `INFRA-01-T03` — Implement safe reset and cleanup ([source](11-infrastructure/01-local-development.md#L67)); dependencies: `INFRA-01-T02`
40. `INFRA-01-T04` — Document and retain local smoke evidence ([source](11-infrastructure/01-local-development.md#L69)); dependencies: `INFRA-01-T03`
41. `INFRA-01-T05` — Close local command ownership ([source](11-infrastructure/01-local-development.md#L71)); dependencies: `INFRA-01-T04`, `TEST-01-T01`, `TEST-01-T02`

## M2

42. `ARCH-03-T01` — Encode enums and transition tables at M2 ([source](01-architecture/03-domain-events-and-state-machines.md#L316)); dependencies: `PRODUCT-01-T03`
43. `ARCH-03-T02` — Persist events and idempotency atomically ([source](01-architecture/03-domain-events-and-state-machines.md#L318)); dependencies: `ARCH-03-T01`
44. `ARCH-03-T03` — Map runtime states explicitly ([source](01-architecture/03-domain-events-and-state-machines.md#L320)); dependencies: `ARCH-03-T02`, `WF-00-T04`
45. `DB-01-T01` — Create core domain types ([source](02-database/01-core-data-model.md#L266)); dependencies: `ARCH-03-T01`
46. `DB-01-T02` — Create the M2 core migration ([source](02-database/01-core-data-model.md#L268)); dependencies: `DB-01-T01`
47. `ARCH-02-T01` — Create inward contracts at M2 ([source](01-architecture/02-module-boundaries.md#L95)); dependencies: `ARCH-03-T01`, `DB-01-T02`
48. `ARCH-01-T02` — Build the M2 product core ([source](01-architecture/01-target-system-architecture.md#L133)); dependencies: `ARCH-01-T01`, `ARCH-02-T01`, `ARCH-03-T01`
49. `ARCH-02-T02` — Implement PostgreSQL unit of work ([source](01-architecture/02-module-boundaries.md#L97)); dependencies: `ARCH-02-T01`, `ARCH-03-T01`
50. `DB-01-T03` — Implement optimistic unit of work ([source](02-database/01-core-data-model.md#L270)); dependencies: `DB-01-T02`
51. `DB-01-T04` — Map runtime runs ([source](02-database/01-core-data-model.md#L272)); dependencies: `DB-01-T03`, `WF-00-T04`
52. `DB-01-T05` — Enforce both send controls default-off ([source](02-database/01-core-data-model.md#L274)); dependencies: `DB-01-T04`
53. `DB-02-T01` — Encode immutable brief and staged decision models ([source](02-database/02-experiment-and-offer-schema.md#L305)); dependencies: `PRODUCT-01-T03`, `PRODUCT-02-T01`
54. `DB-02-T02` — Migrate normalized experiment records ([source](02-database/02-experiment-and-offer-schema.md#L307)); dependencies: `DB-02-T01`
55. `DB-02-T03` — Implement version append repositories ([source](02-database/02-experiment-and-offer-schema.md#L309)); dependencies: `DB-02-T02`
56. `DB-02-T04` — Implement deterministic metric snapshot ([source](02-database/02-experiment-and-offer-schema.md#L311)); dependencies: `DB-02-T03`
57. `DB-02-T05` — Record operator decision atomically ([source](02-database/02-experiment-and-offer-schema.md#L313)); dependencies: `DB-02-T04`
58. `DB-03-T02` — Migrate identity and lead records ([source](02-database/03-leads-campaigns-and-messages.md#L661)); dependencies: `DB-03-T01`, `ARCH-03-T01`
59. `DB-04-T01` — Define typed envelopes and artifact registry ([source](02-database/04-agent-artifacts-and-evidence.md#L301)); dependencies: `PRODUCT-01-T03`
60. `DB-04-T02` — Migrate immutable run/artifact/evidence tables ([source](02-database/04-agent-artifacts-and-evidence.md#L303)); dependencies: `DB-04-T01`
61. `DB-05-T01` — Encode event schemas/catalog ([source](02-database/05-audit-events-and-idempotency.md#L324)); dependencies: `ARCH-03-T01`
62. `DB-05-T02` — Migrate append-only safety tables ([source](02-database/05-audit-events-and-idempotency.md#L326)); dependencies: `DB-05-T01`
63. `DB-03-T03` — Migrate staged campaigns, approvals, and suppression ([source](02-database/03-leads-campaigns-and-messages.md#L663)); dependencies: `DB-03-T02`, `ARCH-03-T01`, `DB-05-T02`
64. `DB-03-T04` — Migrate message and send ledger ([source](02-database/03-leads-campaigns-and-messages.md#L665)); dependencies: `DB-03-T03`, `ARCH-03-T01`
65. `DB-05-T03` — Implement idempotent command middleware ([source](02-database/05-audit-events-and-idempotency.md#L328)); dependencies: `DB-05-T02`
66. `DB-05-T04` — Implement outbox and internal consumer atomicity ([source](02-database/05-audit-events-and-idempotency.md#L330)); dependencies: `DB-05-T03`
67. `DB-06-T01` — Author the M2 revision chain ([source](02-database/06-migrations-seeding-and-retention.md#L317)); dependencies: `DB-01-T02`, `DB-02-T02`, `DB-03-T04`, `DB-04-T02`, `DB-05-T02`
68. `DB-06-T02` — Implement deterministic seeding ([source](02-database/06-migrations-seeding-and-retention.md#L319)); dependencies: `DB-06-T01`
69. `DB-06-T03` — Prove backup and fresh restore ([source](02-database/06-migrations-seeding-and-retention.md#L321)); dependencies: `DB-06-T02`
70. `SEC-06-T01` — Publish the early privacy/minimization interface ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L102)); dependencies: `PRODUCT-01-T03`, `DB-06-T01`

## M3

71. `DB-06-T04` — Implement the later-migration evidence gate ([source](02-database/06-migrations-seeding-and-retention.md#L323)); dependencies: `DB-06-T03`
72. `AGENT-01-T01` — Implement frozen shared models and registries ([source](04-agents/01-agent-runtime-and-contracts.md#L678)); dependencies: `DB-01-T02`, `DB-04-T02`
73. `AGENT-02-T01` — Encode input/output and prompt registry ([source](04-agents/02-idea-discovery-agent.md#L117)); dependencies: `DB-02-T01`, `DB-04-T01`
74. `AGENT-03-T01` — Encode offer schemas/prompt/config ([source](04-agents/03-offer-design-agent.md#L110)); dependencies: `DB-02-T01`, `DB-02-T03`
75. `AGENT-04-T01` — Encode market schemas and source policy ([source](04-agents/04-market-research-agent.md#L112)); dependencies: `DB-02-T03`
76. `AGENT-09-T01` — Encode frozen metric/evidence/recommendation schemas ([source](04-agents/09-experiment-evaluation-agent.md#L113)); dependencies: `DB-04-T01`, `DB-02-T04`
77. `AGENT-10-T01` — Freeze eight complete suites and the signed non-model M3 fixture manifest ([source](04-agents/10-agent-evals-and-versioning.md#L352)); dependencies: `DB-02-T03`, `DB-03-T03`, `DB-03-T04`, `DB-04-T01`
78. `AGENT-01-T02` — Implement least-authority dependency composition ([source](04-agents/01-agent-runtime-and-contracts.md#L680)); dependencies: `AGENT-01-T01`, `AGENT-10-T01`
79. `AGENT-02-T02` — Implement bounded agent and evidence tool ([source](04-agents/02-idea-discovery-agent.md#L119)); dependencies: `AGENT-02-T01`, `AGENT-01-T01`, `AGENT-01-T02`
80. `AGENT-03-T02` — Implement bounded execution ([source](04-agents/03-offer-design-agent.md#L112)); dependencies: `AGENT-03-T01`, `AGENT-01-T01`, `AGENT-01-T02`
81. `AGENT-04-T02` — Implement bounded read-only tool flow ([source](04-agents/04-market-research-agent.md#L114)); dependencies: `AGENT-04-T01`, `AGENT-01-T01`, `AGENT-01-T02`
82. `AGENT-05-T01` — Encode minimized schemas/source policy ([source](04-agents/05-lead-research-agent.md#L111)); dependencies: `DB-03-T03`, `AGENT-10-T01`
83. `AGENT-05-T02` — Implement bounded business tools ([source](04-agents/05-lead-research-agent.md#L113)); dependencies: `AGENT-05-T01`, `AGENT-01-T01`, `AGENT-01-T02`
84. `AGENT-06-T01` — Encode frozen criteria/assessment schemas ([source](04-agents/06-lead-qualification-agent.md#L112)); dependencies: `DB-03-T03`, `AGENT-10-T01`
85. `AGENT-06-T02` — Implement bounded evidence classification ([source](04-agents/06-lead-qualification-agent.md#L114)); dependencies: `AGENT-06-T01`, `AGENT-01-T01`, `AGENT-01-T02`
86. `AGENT-07-T01` — Encode no-authority draft schemas ([source](04-agents/07-outreach-drafting-agent.md#L107)); dependencies: `AGENT-10-T01`, `DB-02-T03`, `DB-03-T03`
87. `AGENT-07-T02` — Implement bounded drafting ([source](04-agents/07-outreach-drafting-agent.md#L109)); dependencies: `AGENT-07-T01`, `AGENT-01-T01`, `AGENT-01-T02`
88. `AGENT-08-T01` — Encode taxonomy/input/output/spans ([source](04-agents/08-reply-classification-agent.md#L116)); dependencies: `DB-03-T04`, `AGENT-10-T01`
89. `AGENT-08-T02` — Implement bounded hostile-content classification ([source](04-agents/08-reply-classification-agent.md#L118)); dependencies: `AGENT-08-T01`, `AGENT-01-T01`, `AGENT-01-T02`
90. `AGENT-09-T02` — Implement bounded evidence-grounded recommendation ([source](04-agents/09-experiment-evaluation-agent.md#L115)); dependencies: `AGENT-09-T01`, `AGENT-01-T01`, `AGENT-01-T02`
91. `PROVIDER-03-T01` — Implement exact model protocol ([source](05-providers/03-model-provider.md#L104)); dependencies: `AGENT-01-T01`, `DB-01-T01`
92. `PROVIDER-03-T02` — Implement OpenAI Responses adapter ([source](05-providers/03-model-provider.md#L106)); dependencies: `PROVIDER-03-T01`
93. `PROVIDER-03-T03` — Implement ceilings and cancellation ([source](05-providers/03-model-provider.md#L108)); dependencies: `PROVIDER-03-T02`
94. `PROVIDER-03-T04` — Implement signed live-capture/fixture adapters ([source](05-providers/03-model-provider.md#L110)); dependencies: `PROVIDER-03-T03`
95. `PROVIDER-04-T01` — Implement exact capability service ([source](05-providers/04-search-provider.md#L100)); dependencies: `AGENT-01-T01`, `DB-01-T01`
96. `PROVIDER-04-T02` — Implement Brave raw adapter and filters ([source](05-providers/04-search-provider.md#L102)); dependencies: `PROVIDER-04-T01`
97. `PROVIDER-05-T01` — Implement exact evidence/page contracts ([source](05-providers/05-page-fetching-and-extraction.md#L103)); dependencies: `AGENT-01-T01`, `DB-01-T01`
98. `DB-04-T03` — Implement evidence capture and linking ([source](02-database/04-agent-artifacts-and-evidence.md#L305)); dependencies: `DB-04-T02`, `PROVIDER-05-T01`
99. `PROVIDER-05-T02` — Implement scoped evidence reader ([source](05-providers/05-page-fetching-and-extraction.md#L105)); dependencies: `PROVIDER-05-T01`
100. `PROVIDER-06-T01` — Implement exact two-family contracts ([source](05-providers/06-enrichment-provider.md#L99)); dependencies: `AGENT-01-T01`, `DB-01-T01`
101. `BACKEND-01-T01` — Implement shared M3 recording and evaluation sole writers ([source](06-backend/01-domain-services.md#L95)); dependencies: `AGENT-01-T01`, `DB-04-T02`, `DB-05-T03`
102. `DB-04-T04` — Implement validation and acceptance transitions ([source](02-database/04-agent-artifacts-and-evidence.md#L307)); dependencies: `DB-04-T03`, `BACKEND-01-T01`, `ARCH-03-T01`
103. `OBS-01-T01` — Implement schema/registry/redaction ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L98)); dependencies: `SEC-06-T01`
104. `OBS-03-T01` — Implement currency/price/usage contracts ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L78)); dependencies: `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `PROVIDER-01-T01`
105. `OBS-03-T02` — Implement reservation/reconciliation ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L80)); dependencies: `OBS-03-T01`, `DB-05-T02`
106. `DB-05-T05` — Implement policy/cost reconciliation ([source](02-database/05-audit-events-and-idempotency.md#L332)); dependencies: `DB-05-T04`, `PROVIDER-03-T04`, `OBS-03-T02`
107. `PRODUCT-02-T03` — Implement gate queries in milestone order ([source](00-product-strategy/02-success-metrics.md#L126)); dependencies: `PRODUCT-02-T02`, `DB-05-T05`
108. `AGENT-01-T03` — Implement finite execution and ledger ([source](04-agents/01-agent-runtime-and-contracts.md#L682)); dependencies: `AGENT-01-T02`, `OBS-03-T02`
109. `AGENT-01-T04` — Implement deterministic validation/persistence handoff ([source](04-agents/01-agent-runtime-and-contracts.md#L684)); dependencies: `AGENT-01-T03`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
110. `AGENT-01-T05` — Prove authority and observability boundary ([source](04-agents/01-agent-runtime-and-contracts.md#L686)); dependencies: `AGENT-01-T04`
111. `AGENT-02-T03` — Implement deterministic validator/persistence handoff ([source](04-agents/02-idea-discovery-agent.md#L121)); dependencies: `AGENT-02-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`
112. `AGENT-03-T03` — Implement post-validation/persistence ([source](04-agents/03-offer-design-agent.md#L114)); dependencies: `AGENT-03-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`
113. `AGENT-04-T03` — Implement evidence ingest/post-validation/persistence ([source](04-agents/04-market-research-agent.md#L116)); dependencies: `AGENT-04-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`, `DB-04-T03`
114. `AGENT-06-T03` — Implement validator and deterministic gate handoff ([source](04-agents/06-lead-qualification-agent.md#L116)); dependencies: `AGENT-06-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`
115. `AGENT-07-T03` — Implement validator/persistence/review handoff ([source](04-agents/07-outreach-drafting-agent.md#L111)); dependencies: `AGENT-07-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`
116. `AGENT-08-T03` — Implement validator/persistence/safety handoff ([source](04-agents/08-reply-classification-agent.md#L120)); dependencies: `AGENT-08-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`
117. `AGENT-09-T03` — Implement deterministic validator and operator-decision handoff ([source](04-agents/09-experiment-evaluation-agent.md#L117)); dependencies: `AGENT-09-T02`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`
118. `PROVIDER-04-T03` — Implement evidence/ledger/cost handoff ([source](05-providers/04-search-provider.md#L104)); dependencies: `PROVIDER-04-T02`, `OBS-03-T02`, `DB-04-T03`
119. `PROVIDER-04-T04` — Implement capture and fixture modes ([source](05-providers/04-search-provider.md#L106)); dependencies: `PROVIDER-04-T03`
120. `PROVIDER-04-T05` — Prove replacement/authority boundary ([source](05-providers/04-search-provider.md#L108)); dependencies: `PROVIDER-04-T04`
121. `PROVIDER-05-T03` — Implement safe HTTP extractor ([source](05-providers/05-page-fetching-and-extraction.md#L107)); dependencies: `PROVIDER-05-T02`, `OBS-03-T02`, `DB-04-T03`
122. `PROVIDER-05-T04` — Implement hash/span and fixture gates ([source](05-providers/05-page-fetching-and-extraction.md#L109)); dependencies: `PROVIDER-05-T03`
123. `PROVIDER-05-T05` — Prove replacement/authority and retention ([source](05-providers/05-page-fetching-and-extraction.md#L111)); dependencies: `PROVIDER-05-T04`
124. `PROVIDER-06-T02` — Implement deterministic identity/locator composition ([source](05-providers/06-enrichment-provider.md#L101)); dependencies: `PROVIDER-06-T01`, `PROVIDER-04-T03`
125. `PROVIDER-06-T03` — Implement signed offline fixtures and replacement suite ([source](05-providers/06-enrichment-provider.md#L103)); dependencies: `PROVIDER-06-T02`
126. `ARCH-02-T03` — Wrap every provider-neutral recorded path at M3 ([source](01-architecture/02-module-boundaries.md#L99)); dependencies: `ARCH-02-T02`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `TEST-04-T01`
127. `AGENT-05-T03` — Implement capture/validator/persistence handoff ([source](04-agents/05-lead-research-agent.md#L115)); dependencies: `AGENT-05-T02`, `PROVIDER-05-T03`, `PROVIDER-06-T03`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `AGENT-01-T04`, `DB-04-T03`
128. `AGENT-10-T02` — Freeze implemented candidate configurations ([source](04-agents/10-agent-evals-and-versioning.md#L354)); dependencies: `AGENT-10-T01`, `AGENT-01-T01`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`, `AGENT-05-T03`, `AGENT-06-T03`, `AGENT-07-T03`, `AGENT-08-T03`, `AGENT-09-T03`
129. `AGENT-10-T03` — Implement isolated candidate capture ([source](04-agents/10-agent-evals-and-versioning.md#L356)); dependencies: `AGENT-10-T02`, `PROVIDER-03-T01`, `OBS-03-T02`, `AGENT-01-T01`, `AGENT-01-T04`, `PROVIDER-03-T02`, `BACKEND-01-T01`
130. `AGENT-10-T04` — Implement network-disabled deterministic scoring ([source](04-agents/10-agent-evals-and-versioning.md#L358)); dependencies: `AGENT-10-T03`
131. `AGENT-02-T04` — Build and gate the 48-case suite ([source](04-agents/02-idea-discovery-agent.md#L123)); dependencies: `AGENT-02-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
132. `AGENT-03-T04` — Build and gate 48-case suite ([source](04-agents/03-offer-design-agent.md#L116)); dependencies: `AGENT-03-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
133. `AGENT-04-T04` — Build and gate 60-case suite ([source](04-agents/04-market-research-agent.md#L118)); dependencies: `AGENT-04-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
134. `AGENT-05-T04` — Build and gate 60-case suite ([source](04-agents/05-lead-research-agent.md#L117)); dependencies: `AGENT-05-T03`, `AGENT-10-T01`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-10-T03`, `AGENT-10-T04`
135. `AGENT-06-T04` — Build and gate 80-case labeled suite ([source](04-agents/06-lead-qualification-agent.md#L118)); dependencies: `AGENT-06-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
136. `AGENT-07-T04` — Build and gate 64-case suite ([source](04-agents/07-outreach-drafting-agent.md#L113)); dependencies: `AGENT-07-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
137. `AGENT-08-T04` — Build and gate 120-case labeled suite ([source](04-agents/08-reply-classification-agent.md#L122)); dependencies: `AGENT-08-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
138. `AGENT-09-T04` — Build and gate 72-case suite ([source](04-agents/09-experiment-evaluation-agent.md#L119)); dependencies: `AGENT-09-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `AGENT-10-T04`
139. `AGENT-10-T05` — Implement comparison and operator promotion ([source](04-agents/10-agent-evals-and-versioning.md#L360)); dependencies: `AGENT-10-T04`, `AGENT-02-T04`, `AGENT-03-T04`, `AGENT-04-T04`, `AGENT-05-T04`, `AGENT-06-T04`, `AGENT-07-T04`, `AGENT-08-T04`, `AGENT-09-T04`
140. `DB-04-T05` — Gate agent promotion on evaluations ([source](02-database/04-agent-artifacts-and-evidence.md#L309)); dependencies: `DB-04-T04`, `AGENT-10-T05`
141. `ARCH-01-T03` — Add offline intelligence vertically ([source](01-architecture/01-target-system-architecture.md#L135)); dependencies: `ARCH-01-T02`, `ARCH-02-T01`, `AGENT-10-T05`, `DB-04-T05`, `ARCH-02-T03`
142. `AGENT-10-T06` — Implement runtime selection/monitoring/rollback ([source](04-agents/10-agent-evals-and-versioning.md#L362)); dependencies: `AGENT-10-T05`
143. `PROVIDER-03-T05` — Bind promoted product model activation ([source](05-providers/03-model-provider.md#L112)); dependencies: `PROVIDER-03-T04`, `AGENT-10-T05`
144. `PROVIDER-03-T06` — Prove replacement and authority seams ([source](05-providers/03-model-provider.md#L114)); dependencies: `PROVIDER-03-T05`
145. `OBS-03-T03` — Implement Bank of Israel FX capture ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L82)); dependencies: `OBS-03-T02`

## M4

146. `WF-03-T01` — Freeze M4 fixture/input contract ([source](03-workflows/03-idea-validation-workflow.md#L48)); dependencies: `AGENT-10-T05`, `DB-02-T03`, `DB-02-T04`, `PRODUCT-02-T01`
147. `WF-03-T02` — Implement typed artifact steps ([source](03-workflows/03-idea-validation-workflow.md#L50)); dependencies: `WF-03-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`, `BACKEND-01-T01`, `DB-04-T04`
148. `BACKEND-01-T02` — Implement pure domain values/transitions ([source](06-backend/01-domain-services.md#L97)); dependencies: `BACKEND-01-T01`, `ARCH-03-T01`, `DB-06-T01`
149. `BACKEND-01-T03` — Implement unit of work/idempotent executor ([source](06-backend/01-domain-services.md#L99)); dependencies: `BACKEND-01-T02`, `ARCH-02-T01`, `DB-05-T03`
150. `BACKEND-01-T04` — Implement M2/M4/M5 sole-writer authority ([source](06-backend/01-domain-services.md#L101)); dependencies: `BACKEND-01-T03`, `DB-06-T01`
151. `WF-02-T01` — Implement stage command service ([source](03-workflows/02-experiment-lifecycle.md#L56)); dependencies: `BACKEND-01-T04`, `AGENT-10-T05`, `PROVIDER-03-T06`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `WF-01-T05`, `WF-00-T04`
152. `WF-02-T02` — Implement finite coordinator ([source](03-workflows/02-experiment-lifecycle.md#L58)); dependencies: `WF-02-T01`
153. `WF-02-T03` — Implement completion/failure handlers ([source](03-workflows/02-experiment-lifecycle.md#L60)); dependencies: `WF-02-T02`
154. `WF-02-T04` — Enforce active-run exclusion and budgets ([source](03-workflows/02-experiment-lifecycle.md#L62)); dependencies: `WF-02-T03`
155. `WF-03-T03` — Implement validation/acceptance/materialization ([source](03-workflows/03-idea-validation-workflow.md#L52)); dependencies: `WF-03-T02`, `DB-04-T04`, `BACKEND-01-T04`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`
156. `WF-03-T04` — Complete evidence bundle and stage ([source](03-workflows/03-idea-validation-workflow.md#L54)); dependencies: `WF-03-T03`, `WF-02-T03`
157. `WF-03-T05` — Prove no-send boundary ([source](03-workflows/03-idea-validation-workflow.md#L56)); dependencies: `WF-03-T04`
158. `BACKEND-01-T05` — Implement side-effect orchestration ([source](06-backend/01-domain-services.md#L103)); dependencies: `BACKEND-01-T04`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`
159. `BACKEND-02-T01` — Implement the M4 private route foundation ([source](06-backend/02-api-contracts.md#L264)); dependencies: `BACKEND-01-T03`
160. `BACKEND-02-T02` — Implement M4/M5 no-send routes and client ([source](06-backend/02-api-contracts.md#L266)); dependencies: `BACKEND-02-T01`, `BACKEND-01-T04`
161. `FRONTEND-01-T01` — Generate and gate the product client ([source](07-frontend/01-information-architecture.md#L163)); dependencies: `BACKEND-02-T02`
162. `FRONTEND-01-T02` — Build the three-destination operator shell ([source](07-frontend/01-information-architecture.md#L165)); dependencies: `FRONTEND-01-T01`, `BACKEND-02-T01`
163. `FRONTEND-01-T03` — Implement shared query/mutation primitives ([source](07-frontend/01-information-architecture.md#L167)); dependencies: `FRONTEND-01-T02`
164. `FRONTEND-01-T04` — Prove frontend authority boundaries ([source](07-frontend/01-information-architecture.md#L169)); dependencies: `FRONTEND-01-T03`
165. `FRONTEND-02-T01` — Build the generated-schema form ([source](07-frontend/02-experiment-creation-flow.md#L72)); dependencies: `FRONTEND-01-T01`, `DB-02-T01`
166. `FRONTEND-02-T02` — Implement create/replay/navigation ([source](07-frontend/02-experiment-creation-flow.md#L74)); dependencies: `FRONTEND-02-T01`
167. `FRONTEND-02-T03` — Implement explicit scope approval and revision ([source](07-frontend/02-experiment-creation-flow.md#L76)); dependencies: `FRONTEND-02-T02`
168. `FRONTEND-02-T04` — Verify privacy and responsive access ([source](07-frontend/02-experiment-creation-flow.md#L78)); dependencies: `FRONTEND-02-T03`
169. `FRONTEND-03-T01` — Render exhaustive experiment/run truth ([source](07-frontend/03-experiment-control-center.md#L77)); dependencies: `FRONTEND-02-T03`, `FRONTEND-01-T01`
170. `FRONTEND-03-T02` — Implement stage and control commands ([source](07-frontend/03-experiment-control-center.md#L79)); dependencies: `FRONTEND-03-T01`
171. `INFRA-01-T06` — Implement product migration, seed, and generation workflow ([source](11-infrastructure/01-local-development.md#L73)); dependencies: `INFRA-01-T05`, `DB-06-T02`, `BACKEND-02-T02`
172. `INFRA-01-T07` — Complete product local reset and cleanup ([source](11-infrastructure/01-local-development.md#L75)); dependencies: `INFRA-01-T06`, `DB-01-T05`
173. `INFRA-01-T08` — Complete product smoke evidence and local command ownership ([source](11-infrastructure/01-local-development.md#L77)); dependencies: `INFRA-01-T07`, `TEST-01-T02`

## M5

174. `PROVIDER-06-T04` — Implement the terms-gated live enrichment adapter ([source](05-providers/06-enrichment-provider.md#L105)); dependencies: `PROVIDER-06-T03`, `OBS-03-T01`, `OBS-03-T02`
175. `PROVIDER-06-T05` — Prove minimization and authority ([source](05-providers/06-enrichment-provider.md#L107)); dependencies: `PROVIDER-06-T04`
176. `BACKEND-01-T06` — Prove boundary and current-truth gates ([source](06-backend/01-domain-services.md#L105)); dependencies: `BACKEND-01-T05`
177. `WF-04-T01` — Freeze criteria and candidate bounds ([source](03-workflows/04-lead-qualification-workflow.md#L48)); dependencies: `WF-03-T05`, `DB-02-T03`, `WF-03-T03`
178. `WF-04-T02` — Implement deterministic business identity ([source](03-workflows/04-lead-qualification-workflow.md#L50)); dependencies: `WF-04-T01`, `PROVIDER-06-T02`
179. `WF-04-T03` — Implement research/evidence subtask ([source](03-workflows/04-lead-qualification-workflow.md#L52)); dependencies: `WF-04-T02`, `PROVIDER-06-T01`, `PROVIDER-06-T03`, `PROVIDER-05-T01`, `AGENT-05-T03`
180. `WF-04-T04` — Implement qualification gate ([source](03-workflows/04-lead-qualification-workflow.md#L54)); dependencies: `WF-04-T03`, `AGENT-06-T03`, `BACKEND-01-T04`
181. `WF-04-T05` — Complete M5 and prove no-send ([source](03-workflows/04-lead-qualification-workflow.md#L56)); dependencies: `WF-04-T04`, `WF-02-T03`
182. `ARCH-01-T04` — Adjudicate the M4/M5 no-send architecture ([source](01-architecture/01-target-system-architecture.md#L137)); dependencies: `ARCH-01-T03`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-06-T03`, `WF-00-T04`

## M6

183. `BACKEND-03-T01` — Encode eligibility/basis/SEND facts and reason registry ([source](06-backend/03-policy-engine.md#L120)); dependencies: `DB-05-T02`, `ARCH-03-T01`, `DB-03-T01`
184. `BACKEND-03-T02` — Implement deterministic rule composition ([source](06-backend/03-policy-engine.md#L122)); dependencies: `BACKEND-03-T01`
185. `BACKEND-03-T03` — Implement PolicyEvaluationService ([source](06-backend/03-policy-engine.md#L124)); dependencies: `BACKEND-03-T02`
186. `BACKEND-04-T01` — Implement intent and gateway contracts ([source](06-backend/04-send-gateway.md#L84)); dependencies: `PROVIDER-02-T01`, `BACKEND-03-T01`, `ARCH-03-T01`, `PROVIDER-01-T02`, `DB-03-T01`
187. `BACKEND-05-T01` — Implement command envelope/registry/executor ([source](06-backend/05-approval-and-command-handling.md#L140)); dependencies: `DB-05-T02`, `DB-01-T01`, `DB-01-T02`
188. `SEC-04-T01` — Freeze isolated-test and prohibited-recipient policy ([source](08-security-and-compliance/04-outreach-compliance.md#L84)); dependencies: `SEC-06-T01`, `PRODUCT-01-T02`
189. `SEC-04-T02` — Implement recipient evidence contracts ([source](08-security-and-compliance/04-outreach-compliance.md#L86)); dependencies: `SEC-04-T01`
190. `SEC-04-T03` — Implement disclosures and prohibited-content validator ([source](08-security-and-compliance/04-outreach-compliance.md#L88)); dependencies: `SEC-04-T02`, `AGENT-07-T03`
191. `SEC-05-T01` — Seed and implement independent controls ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L90)); dependencies: `DB-05-T02`, `ARCH-03-T01`, `DB-01-T05`, `SEC-04-T01`
192. `SEC-05-T02` — Implement suppression under last-mile locks ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L92)); dependencies: `SEC-05-T01`, `DB-03-T03`, `DB-03-T04`, `DB-03-T01`
193. `SEC-05-T03` — Implement hierarchical reservations and rates ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L94)); dependencies: `SEC-05-T02`, `OBS-03-T02`
194. `SEC-02-T01` — Migrate and introspect the exact operational schema ([source](08-security-and-compliance/02-authentication-and-private-access.md#L992)); dependencies: `DB-01-T02`, `SEC-06-T01`
195. `SEC-02-T02` — Implement strict OIDC flow state ([source](08-security-and-compliance/02-authentication-and-private-access.md#L994)); dependencies: `SEC-02-T01`, `SEC-03-T01`
196. `SEC-02-T03` — Implement server-side sessions ([source](08-security-and-compliance/02-authentication-and-private-access.md#L996)); dependencies: `SEC-02-T02`
197. `SEC-02-T04` — Enforce private request boundary ([source](08-security-and-compliance/02-authentication-and-private-access.md#L998)); dependencies: `SEC-02-T03`, `BACKEND-02-T01`
198. `WF-06-T01` — Implement idempotent control command service ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L68)); dependencies: `SEC-02-T04`, `BACKEND-05-T01`
199. `WF-06-T02` — Implement cooperative acknowledgement ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L70)); dependencies: `WF-06-T01`
200. `WF-06-T03` — Implement guarded resume/retry ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L72)); dependencies: `WF-06-T02`
201. `WF-02-T05` — Wire pause/cancel/recovery ([source](03-workflows/02-experiment-lifecycle.md#L64)); dependencies: `WF-02-T04`, `BACKEND-05-T01`, `WF-06-T03`
202. `SEC-02-T05` — Implement lifecycle and emergency controls ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1000)); dependencies: `SEC-02-T04`
203. `BACKEND-05-T02` — Implement authenticated sensitive preview receipt service ([source](06-backend/05-approval-and-command-handling.md#L142)); dependencies: `BACKEND-05-T01`, `SEC-02-T04`, `SEC-02-T05`, `SEC-03-T01`, `DB-03-T04`, `PROVIDER-01-T02`
204. `BACKEND-05-T03` — Implement eligibility-bound manual approval lifecycle ([source](06-backend/05-approval-and-command-handling.md#L144)); dependencies: `BACKEND-05-T02`, `BACKEND-03-T03`
205. `BACKEND-03-T04` — Implement last-mile SEND, suppression, and rate reservation ([source](06-backend/03-policy-engine.md#L126)); dependencies: `BACKEND-03-T03`, `SEC-05-T03`, `BACKEND-05-T03`
206. `BACKEND-04-T02` — Implement exact pre-call transaction/order ([source](06-backend/04-send-gateway.md#L86)); dependencies: `BACKEND-04-T01`, `BACKEND-03-T04`, `SEC-05-T03`
207. `BACKEND-05-T04` — Implement stage/control/runtime handlers ([source](06-backend/05-approval-and-command-handling.md#L146)); dependencies: `BACKEND-05-T03`
208. `BACKEND-05-T05` — Implement all-current-eligible campaign snapshot creation ([source](06-backend/05-approval-and-command-handling.md#L148)); dependencies: `BACKEND-05-T04`, `DB-03-T03`
209. `BACKEND-05-T06` — Implement send/recovery/control enable gates ([source](06-backend/05-approval-and-command-handling.md#L150)); dependencies: `BACKEND-05-T05`, `SEC-05-T02`
210. `OBS-05-T01` — Implement incident/evidence contracts ([source](09-observability-and-evaluation/05-incident-response.md#L142)); dependencies: `ARCH-03-T01`, `DB-05-T01`, `PRODUCT-03-T01`
211. `OBS-05-T02` — Implement containment and recovery commands ([source](09-observability-and-evaluation/05-incident-response.md#L144)); dependencies: `OBS-05-T01`, `PRODUCT-03-T03`
212. `LAUNCH-01-T01` — Attest the isolated pilot construction target ([source](12-launch-and-operations/01-test-inbox-pilot.md#L92)); dependencies: `PRODUCT-03-T01`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `WF-01-T01`, `WF-00-T04`
213. `PROVIDER-01-T03` — Implement OAuth secret-store saga and command boundary ([source](05-providers/01-gmail-oauth-and-adapter.md#L169)); dependencies: `PROVIDER-01-T02`, `SEC-03-T01`, `SEC-02-T04`, `BACKEND-05-T01`, `DB-03-T04`, `DB-05-T03`, `LAUNCH-01-T01`
214. `PROVIDER-01-T04` — Implement one-call Gmail adapter ([source](05-providers/01-gmail-oauth-and-adapter.md#L171)); dependencies: `PROVIDER-01-T03`
215. `ARCH-02-T04` — Move send orchestration outward at M6 ([source](01-architecture/02-module-boundaries.md#L101)); dependencies: `ARCH-02-T03`, `DB-01-T05`, `DB-05-T05`, `PROVIDER-01-T02`, `PROVIDER-01-T04`
216. `BACKEND-04-T03` — Implement one provider call and result transactions ([source](06-backend/04-send-gateway.md#L88)); dependencies: `BACKEND-04-T02`, `PROVIDER-01-T04`
217. `PROVIDER-01-T05` — Integrate sole SendGateway path ([source](05-providers/01-gmail-oauth-and-adapter.md#L173)); dependencies: `PROVIDER-01-T04`, `BACKEND-04-T03`
218. `PROVIDER-02-T02` — Implement Sent reconciliation ([source](05-providers/02-gmail-history-sync.md#L87)); dependencies: `PROVIDER-02-T01`, `BACKEND-04-T03`, `DB-03-T01`, `PROVIDER-01-T03`
219. `ARCH-03-T04` — Implement message ambiguity path before Gmail activation ([source](01-architecture/03-domain-events-and-state-machines.md#L322)); dependencies: `ARCH-03-T03`, `DB-03-T04`, `PROVIDER-02-T02`
220. `PROVIDER-02-T03` — Implement atomic incremental pages ([source](05-providers/02-gmail-history-sync.md#L89)); dependencies: `PROVIDER-02-T02`
221. `PROVIDER-02-T04` — Implement 404 full-sync recovery ([source](05-providers/02-gmail-history-sync.md#L91)); dependencies: `PROVIDER-02-T03`
222. `BACKEND-04-T04` — Implement disjoint reconciliation/retry handoff ([source](06-backend/04-send-gateway.md#L90)); dependencies: `BACKEND-04-T03`, `PROVIDER-02-T02`
223. `DB-03-T05` — Implement sole send transaction boundaries ([source](02-database/03-leads-campaigns-and-messages.md#L667)); dependencies: `DB-03-T04`, `DB-01-T05`, `BACKEND-05-T03`, `BACKEND-04-T04`
224. `DB-03-T06` — Implement atomic history sync ([source](02-database/03-leads-campaigns-and-messages.md#L669)); dependencies: `DB-03-T05`, `PROVIDER-02-T01`, `PROVIDER-02-T03`
225. `WF-06-T04` — Implement send drain/reconciliation ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L74)); dependencies: `WF-06-T03`, `BACKEND-04-T04`, `PROVIDER-02-T02`
226. `SEC-03-T02` — Implement Gmail credential lifecycle ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L84)); dependencies: `SEC-03-T01`, `PROVIDER-01-T03`
227. `SEC-03-T03` — Apply exact access/redaction controls ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L86)); dependencies: `SEC-03-T02`
228. `SEC-03-T04` — Implement rotation, emergency revoke, and recovery-package refresh ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L88)); dependencies: `SEC-03-T03`
229. `OBS-01-T02` — Propagate correlation/causation ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L100)); dependencies: `OBS-01-T01`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `OBS-03-T02`
230. `OBS-01-T03` — Instrument exact boundaries ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L102)); dependencies: `OBS-01-T02`
231. `SEC-05-T04` — Wire deterministic kill triggers and alerts ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L96)); dependencies: `SEC-05-T03`, `OBS-01-T03`, `BACKEND-04-T03`, `PRODUCT-03-T03`
232. `BACKEND-02-T03` — Implement the isolated M6 owned-inbox API ([source](06-backend/02-api-contracts.md#L268)); dependencies: `BACKEND-02-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `BACKEND-03-T03`, `BACKEND-04-T04`, `BACKEND-05-T06`, `SEC-03-T02`, `SEC-04-T03`, `SEC-05-T04`, `SEC-02-T04`, `BACKEND-05-T02`
233. `TEST-04-T03` — Prove the six-point OAuth saga ([source](10-testing/04-gmail-side-effect-tests.md#L64)); dependencies: `TEST-04-T02`, `PROVIDER-01-T03`, `DB-03-T04`, `DB-05-T03`
234. `TEST-04-T04` — Prove 14-step gateway authority and results ([source](10-testing/04-gmail-side-effect-tests.md#L66)); dependencies: `TEST-04-T03`, `BACKEND-04-T04`, `SEC-05-T03`
235. `TEST-02-T01` — Freeze schema and digest manifests ([source](10-testing/02-contract-and-integration-tests.md#L420)); dependencies: `DB-01-T01`, `AGENT-01-T01`, `PROVIDER-01-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `TEST-01-T03`, `TEST-01-T02`
236. `TEST-02-T02` — Prove the complete PostgreSQL contract ([source](10-testing/02-contract-and-integration-tests.md#L422)); dependencies: `TEST-02-T01`, `DB-06-T01`, `SEC-06-T01`
237. `TEST-03-T04` — Prove every finite workflow and delivery edge ([source](10-testing/03-workflow-recovery-tests.md#L69)); dependencies: `TEST-03-T03`, `TEST-02-T02`, `ARCH-03-T01`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`
238. `TEST-03-T05` — Prove controls, versioning and migration ([source](10-testing/03-workflow-recovery-tests.md#L71)); dependencies: `TEST-03-T04`, `WF-06-T04`
239. `LAUNCH-01-T02` — Close offline Gmail and authority evidence ([source](12-launch-and-operations/01-test-inbox-pilot.md#L94)); dependencies: `LAUNCH-01-T01`, `TEST-04-T01`, `TEST-04-T03`, `TEST-04-T02`, `BACKEND-04-T04`, `PROVIDER-02-T04`, `SEC-05-T02`, `OBS-03-T02`, `BACKEND-01-T06`
240. `LAUNCH-01-T03` — Freeze the pilot entry and target ([source](12-launch-and-operations/01-test-inbox-pilot.md#L96)); dependencies: `LAUNCH-01-T02`, `PRODUCT-03-T01`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `WF-01-T01`, `WF-00-T04`, `PROVIDER-01-T03`, `SEC-05-T04`, `OBS-01-T03`
241. `PROVIDER-01-T06` — Build fixture and credential-security gates ([source](05-providers/01-gmail-oauth-and-adapter.md#L175)); dependencies: `PROVIDER-01-T05`, `LAUNCH-01-T03`
242. `PROVIDER-02-T05` — Gate M6 fixtures and operations ([source](05-providers/02-gmail-history-sync.md#L93)); dependencies: `PROVIDER-02-T04`, `LAUNCH-01-T03`
243. `WF-05-T01` — Provision isolated M6 authority ([source](03-workflows/05-outreach-and-reply-workflow.md#L71)); dependencies: `TEST-03-T03`, `SEC-05-T03`, `BACKEND-05-T06`, `PROVIDER-01-T03`, `SEC-02-T04`, `LAUNCH-01-T03`, `WF-00-T04`
244. `WF-05-T02` — Implement eligibility/approval/intent path ([source](03-workflows/05-outreach-and-reply-workflow.md#L73)); dependencies: `WF-05-T01`, `BACKEND-05-T03`, `WF-04-T04`, `AGENT-07-T03`
245. `WF-05-T03` — Implement gateway, rate lease, suppression, and reconciliation ([source](03-workflows/05-outreach-and-reply-workflow.md#L75)); dependencies: `WF-05-T02`, `SEC-05-T03`, `BACKEND-04-T04`
246. `WF-05-T04` — Implement recipient-signal sync/classification ([source](03-workflows/05-outreach-and-reply-workflow.md#L77)); dependencies: `WF-05-T03`, `PROVIDER-02-T04`, `AGENT-08-T03`, `SEC-05-T02`
247. `BACKEND-04-T05` — Prove M6 gateway, service authority, and observability ([source](06-backend/04-send-gateway.md#L92)); dependencies: `BACKEND-04-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `SEC-05-T04`, `TEST-03-T03`, `BACKEND-03-T03`, `BACKEND-05-T06`, `WF-00-T04`, `LAUNCH-01-T03`
248. `WF-05-T05` — Prove controls, rate, suppression, and campaign completion ([source](03-workflows/05-outreach-and-reply-workflow.md#L79)); dependencies: `WF-05-T04`, `BACKEND-04-T05`, `SEC-05-T04`, `WF-06-T04`, `LAUNCH-01-T03`
249. `TEST-04-T05` — Prove reconciliation and recipient signals ([source](10-testing/04-gmail-side-effect-tests.md#L68)); dependencies: `TEST-04-T04`, `PROVIDER-02-T04`, `WF-05-T04`
250. `TEST-04-T06` — Run the controlled M6 owned-alias gate and close live command ownership ([source](10-testing/04-gmail-side-effect-tests.md#L70)); dependencies: `TEST-04-T05`, `WF-05-T05`, `BACKEND-04-T05`, `SEC-05-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `LAUNCH-01-T03`
251. `WF-05-T06` — Keep product outreach disabled until gate record ([source](03-workflows/05-outreach-and-reply-workflow.md#L81)); dependencies: `WF-05-T05`, `TEST-04-T06`
252. `LAUNCH-01-T04` — Execute the exact live catalog one message at a time ([source](12-launch-and-operations/01-test-inbox-pilot.md#L98)); dependencies: `LAUNCH-01-T03`
253. `LAUNCH-01-T05` — Exercise signals and operator stop ([source](12-launch-and-operations/01-test-inbox-pilot.md#L100)); dependencies: `LAUNCH-01-T04`
254. `LAUNCH-01-T06` — Close cleanup and promotion ([source](12-launch-and-operations/01-test-inbox-pilot.md#L102)); dependencies: `LAUNCH-01-T05`

## M7

255. `ARCH-03-T05` — Generate API/UI state mappings ([source](01-architecture/03-domain-events-and-state-machines.md#L324)); dependencies: `ARCH-03-T04`
256. `BACKEND-06-T01` — Encode projection schemas/query versions ([source](06-backend/06-reporting-and-query-services.md#L100)); dependencies: `BACKEND-03-T01`, `SEC-04-T02`, `DB-05-T02`, `ARCH-03-T01`, `OBS-05-T01`
257. `BACKEND-02-T04` — Freeze the authenticated M7 report/recovery contract ([source](06-backend/02-api-contracts.md#L270)); dependencies: `BACKEND-02-T03`, `SEC-02-T04`, `BACKEND-06-T01`
258. `BACKEND-06-T02` — Implement overview/funnel/recovery queries ([source](06-backend/06-reporting-and-query-services.md#L102)); dependencies: `BACKEND-06-T01`
259. `BACKEND-06-T03` — Implement cost/provider queries ([source](06-backend/06-reporting-and-query-services.md#L104)); dependencies: `BACKEND-06-T02`, `OBS-03-T03`
260. `BACKEND-06-T04` — Implement repeatable-read/exported-snapshot pagination/API routes ([source](06-backend/06-reporting-and-query-services.md#L106)); dependencies: `BACKEND-06-T03`, `BACKEND-02-T04`
261. `BACKEND-02-T05` — Generate and gate the disabled-public API manifest and client ([source](06-backend/02-api-contracts.md#L272)); dependencies: `BACKEND-02-T04`, `BACKEND-06-T04`
262. `ARCH-02-T05` — Enforce frontend/API boundary at M7 ([source](01-architecture/02-module-boundaries.md#L103)); dependencies: `ARCH-02-T04`, `BACKEND-02-T05`
263. `BACKEND-03-T05` — Gate versions and operator explainability ([source](06-backend/03-policy-engine.md#L128)); dependencies: `BACKEND-03-T04`, `BACKEND-06-T02`, `BACKEND-06-T04`
264. `BACKEND-05-T07` — Prove OAuth saga, callback, and operator workflows ([source](06-backend/05-approval-and-command-handling.md#L152)); dependencies: `BACKEND-05-T06`, `SEC-03-T01`, `PROVIDER-01-T03`, `BACKEND-02-T03`, `BACKEND-02-T05`
265. `OBS-01-T04` — Integrate authenticated private and report correlation ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L104)); dependencies: `OBS-01-T03`, `SEC-02-T04`, `BACKEND-02-T05`
266. `FRONTEND-01-T05` — Integrate complete generated client and authenticated private shell ([source](07-frontend/01-information-architecture.md#L171)); dependencies: `FRONTEND-01-T04`, `BACKEND-02-T05`, `SEC-02-T04`, `SEC-02-T05`, `FRONTEND-02-T04`, `FRONTEND-03-T01`
267. `FRONTEND-03-T03` — Integrate complete control-center reports and operator controls ([source](07-frontend/03-experiment-control-center.md#L81)); dependencies: `FRONTEND-03-T02`, `FRONTEND-01-T05`, `BACKEND-02-T05`, `BACKEND-06-T04`, `BACKEND-05-T04`, `WF-06-T03`
268. `FRONTEND-03-T04` — Implement closed failure exits and campaign handoff ([source](07-frontend/03-experiment-control-center.md#L83)); dependencies: `FRONTEND-03-T03`
269. `FRONTEND-03-T05` — Implement immutable decision handoff ([source](07-frontend/03-experiment-control-center.md#L85)); dependencies: `FRONTEND-03-T04`, `BACKEND-06-T04`, `BACKEND-02-T05`
270. `FRONTEND-04-T01` — Implement generated reference components ([source](07-frontend/04-evidence-and-agent-artifacts.md#L72)); dependencies: `BACKEND-02-T05`
271. `FRONTEND-04-T02` — Implement report-backed provider/timeline evidence ([source](07-frontend/04-evidence-and-agent-artifacts.md#L74)); dependencies: `FRONTEND-04-T01`, `BACKEND-06-T04`
272. `FRONTEND-04-T03` — Prove artifact mutation remains server-authoritative ([source](07-frontend/04-evidence-and-agent-artifacts.md#L76)); dependencies: `FRONTEND-04-T02`, `BACKEND-02-T05`
273. `FRONTEND-04-T04` — Gate lifecycle actions on accepted artifacts ([source](07-frontend/04-evidence-and-agent-artifacts.md#L78)); dependencies: `FRONTEND-04-T03`, `BACKEND-02-T05`
274. `FRONTEND-05-T01` — Implement immutable all-eligible version creation/read ([source](07-frontend/05-lead-and-campaign-management.md#L76)); dependencies: `BACKEND-02-T05`, `BACKEND-02-T02`
275. `FRONTEND-05-T02` — Render exhaustive lead/member/message safety states ([source](07-frontend/05-lead-and-campaign-management.md#L78)); dependencies: `FRONTEND-05-T01`
276. `FRONTEND-05-T03` — Implement readiness and four campaign controls ([source](07-frontend/05-lead-and-campaign-management.md#L80)); dependencies: `FRONTEND-05-T02`, `BACKEND-05-T06`
277. `FRONTEND-05-T04` — Implement typed suppression management ([source](07-frontend/05-lead-and-campaign-management.md#L82)); dependencies: `FRONTEND-05-T03`, `BACKEND-02-T05`
278. `FRONTEND-05-T05` — Enforce API boundaries and authority ([source](07-frontend/05-lead-and-campaign-management.md#L84)); dependencies: `FRONTEND-05-T04`, `BACKEND-02-T05`
279. `FRONTEND-06-T01` — Implement queue/detail projections ([source](07-frontend/06-approval-inbox.md#L77)); dependencies: `BACKEND-02-T05`
280. `FRONTEND-06-T02` — Implement sensitive preview, approve, and deny ([source](07-frontend/06-approval-inbox.md#L79)); dependencies: `FRONTEND-06-T01`, `SEC-02-T04`, `BACKEND-02-T05`
281. `FRONTEND-06-T03` — Implement revoke and consumption visibility ([source](07-frontend/06-approval-inbox.md#L81)); dependencies: `FRONTEND-06-T02`
282. `FRONTEND-06-T04` — Prove eligibility/final-SEND separation ([source](07-frontend/06-approval-inbox.md#L83)); dependencies: `FRONTEND-06-T03`
283. `FRONTEND-07-T01` — Render message authority and chronology ([source](07-frontend/07-message-and-reply-timeline.md#L66)); dependencies: `BACKEND-02-T05`
284. `FRONTEND-07-T02` — Implement approval request ([source](07-frontend/07-message-and-reply-timeline.md#L68)); dependencies: `FRONTEND-07-T01`, `BACKEND-02-T05`
285. `FRONTEND-07-T03` — Implement send-intent authority action ([source](07-frontend/07-message-and-reply-timeline.md#L70)); dependencies: `FRONTEND-07-T02`, `BACKEND-05-T03`, `BACKEND-02-T05`
286. `FRONTEND-07-T04` — Implement ambiguity/recovery and retry abort ([source](07-frontend/07-message-and-reply-timeline.md#L72)); dependencies: `FRONTEND-07-T03`, `BACKEND-04-T04`, `WF-06-T04`, `BACKEND-02-T05`
287. `FRONTEND-08-T01` — Implement report provenance/query hooks ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L71)); dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
288. `FRONTEND-08-T02` — Implement funnel and accessible chart/table ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L73)); dependencies: `FRONTEND-08-T01`
289. `FRONTEND-08-T03` — Implement cost/provider evidence ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L75)); dependencies: `FRONTEND-08-T02`, `BACKEND-06-T03`
290. `FRONTEND-08-T04` — Implement immutable decision confirmation ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L77)); dependencies: `FRONTEND-08-T03`, `BACKEND-06-T02`, `BACKEND-02-T05`
291. `FRONTEND-09-T01` — Implement five-kind recovery overview ([source](07-frontend/09-error-recovery-and-accessibility.md#L112)); dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
292. `FRONTEND-09-T02` — Implement ambiguity and typed repair ([source](07-frontend/09-error-recovery-and-accessibility.md#L114)); dependencies: `FRONTEND-09-T01`, `BACKEND-04-T04`, `BACKEND-02-T05`
293. `FRONTEND-09-T03` — Implement kill controls and authority separation ([source](07-frontend/09-error-recovery-and-accessibility.md#L116)); dependencies: `FRONTEND-09-T02`, `SEC-05-T04`
294. `FRONTEND-09-T04` — Implement operator OIDC session and Gmail OAuth/mailbox saga UX ([source](07-frontend/09-error-recovery-and-accessibility.md#L118)); dependencies: `FRONTEND-09-T03`, `BACKEND-02-T05`
295. `ARCH-01-T05` — Adjudicate the M6/M7 private-operator architecture ([source](01-architecture/01-target-system-architecture.md#L139)); dependencies: `ARCH-01-T04`, `BACKEND-03-T03`, `PROVIDER-01-T03`, `DB-03-T06`, `WF-01-T01`, `TEST-04-T06`, `BACKEND-02-T05`, `FRONTEND-03-T05`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T04`, `FRONTEND-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
296. `BACKEND-06-T05` — Prove decision reproducibility, redaction, and UI contract ([source](06-backend/06-reporting-and-query-services.md#L108)); dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`

## M8

297. `OBS-01-T05` — Deploy private sink/self-health ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L106)); dependencies: `OBS-01-T04`
298. `OBS-01-T06` — Prove absence and usability ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L108)); dependencies: `OBS-01-T05`
299. `OBS-03-T04` — Implement reports/alerts/invoice review ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L84)); dependencies: `OBS-03-T03`
300. `OBS-03-T05` — Reconcile eval and runtime windows ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L86)); dependencies: `OBS-03-T04`, `AGENT-10-T01`, `AGENT-10-T05`
301. `FRONTEND-09-T05` — Apply and verify global accessibility/responsive contract ([source](07-frontend/09-error-recovery-and-accessibility.md#L120)); dependencies: `FRONTEND-09-T04`, `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-03-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T02`, `FRONTEND-08-T03`, `FRONTEND-03-T05`, `FRONTEND-08-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
302. `SEC-02-T06` — Prove bootstrap and restore ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1002)); dependencies: `SEC-02-T05`
303. `OBS-02-T01` — Implement exact metric/span registries ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L228)); dependencies: `OBS-01-T01`, `OBS-01-T03`
304. `OBS-04-T01` — Implement governed datasets/manifests ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L94)); dependencies: `AGENT-10-T01`
305. `OBS-04-T02` — Implement isolated capture and exact ownership ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L96)); dependencies: `OBS-04-T01`
306. `OBS-04-T03` — Implement deterministic scoring/promotion/rollback ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L98)); dependencies: `OBS-04-T02`, `AGENT-10-T04`, `AGENT-10-T05`
307. `TEST-05-T01` — Build isolated browser fixture composition ([source](10-testing/05-end-to-end-browser-tests.md#L56)); dependencies: `TEST-01-T03`, `BACKEND-02-T05`
308. `TEST-05-T02` — Implement private operator journeys ([source](10-testing/05-end-to-end-browser-tests.md#L58)); dependencies: `TEST-05-T01`, `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T03`, `FRONTEND-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
309. `TEST-05-T03` — Prove auth/OAuth/control/recovery security ([source](10-testing/05-end-to-end-browser-tests.md#L60)); dependencies: `TEST-05-T02`, `SEC-02-T06`, `PROVIDER-01-T06`, `FRONTEND-09-T05`
310. `TEST-05-T04` — Prove accessibility and responsive contract ([source](10-testing/05-end-to-end-browser-tests.md#L62)); dependencies: `TEST-05-T03`
311. `TEST-06-T01` — Freeze capacity and destructive-target guards ([source](10-testing/06-load-security-and-chaos-tests.md#L48)); dependencies: `TEST-01-T01`
312. `INFRA-02-T01` — Extend deterministic/deep CI gates ([source](11-infrastructure/02-ci-cd-and-release-process.md#L56)); dependencies: `TEST-01-T01`
313. `INFRA-02-T02` — Build immutable supply-chain candidate ([source](11-infrastructure/02-ci-cd-and-release-process.md#L58)); dependencies: `INFRA-02-T01`
314. `TEST-06-T02` — Measure private capacity/rate/budget ([source](10-testing/06-load-security-and-chaos-tests.md#L50)); dependencies: `TEST-06-T01`, `INFRA-02-T02`
315. `INFRA-03-T01` — Provision and attest the private host ([source](11-infrastructure/03-private-vps-deployment.md#L55)); dependencies: `INFRA-02-T02`
316. `INFRA-03-T02` — Deploy the modular-monolith topology ([source](11-infrastructure/03-private-vps-deployment.md#L57)); dependencies: `INFRA-03-T01`, `INFRA-02-T02`
317. `INFRA-03-T03` — Integrate managed secret/KMS adapter ([source](11-infrastructure/03-private-vps-deployment.md#L59)); dependencies: `INFRA-03-T02`, `SEC-03-T01`
318. `INFRA-03-T04` — Gate the sole off-provider recovery repository ([source](11-infrastructure/03-private-vps-deployment.md#L61)); dependencies: `INFRA-03-T03`
319. `INFRA-03-T05` — Configure private DNS/TLS/proxy/firewall ([source](11-infrastructure/03-private-vps-deployment.md#L63)); dependencies: `INFRA-03-T04`
320. `INFRA-04-T01` — Configure exact dual-repository WAL archiving ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L155)); dependencies: `INFRA-03-T04`
321. `INFRA-04-T02` — Implement signed per-repository backups ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L157)); dependencies: `INFRA-04-T01`
322. `SEC-03-T05` — Prove clean backup/restore ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L90)); dependencies: `SEC-03-T04`, `INFRA-04-T02`
323. `SEC-01-T02` — Close implemented security boundaries against the planned registry ([source](08-security-and-compliance/01-threat-model.md#L103)); dependencies: `SEC-01-T01`, `BACKEND-02-T05`, `OBS-01-T06`, `INFRA-03-T02`, `INFRA-04-T02`
324. `SEC-01-T03` — Build the Critical abuse corpus ([source](08-security-and-compliance/01-threat-model.md#L105)); dependencies: `SEC-01-T02`
325. `SEC-01-T04` — Exercise disable and recovery ([source](08-security-and-compliance/01-threat-model.md#L107)); dependencies: `SEC-01-T03`
326. `OBS-02-T02` — Instrument safety and service paths ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L230)); dependencies: `OBS-02-T01`, `BACKEND-02-T05`, `DB-06-T01`, `WF-05-T05`, `AGENT-10-T05`, `SEC-05-T04`, `OBS-03-T02`, `INFRA-04-T02`
327. `SEC-06-T02` — Complete the live inventory and approve authoritative retention ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L104)); dependencies: `SEC-06-T01`, `SEC-01-T02`, `SEC-02-T05`, `SEC-03-T04`, `INFRA-04-T02`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `PROVIDER-03-T06`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `PROVIDER-06-T05`, `OBS-02-T01`, `OBS-02-T02`, `OBS-04-T01`, `OBS-04-T02`
328. `DB-06-T05` — Implement the database retention engine and recovery graph ([source](02-database/06-migrations-seeding-and-retention.md#L325)); dependencies: `DB-06-T04`, `SEC-06-T02`
329. `OBS-02-T03` — Build five dashboards and SLO calculations ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L232)); dependencies: `OBS-02-T02`
330. `OBS-02-T04` — Implement alert routes/runbooks ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L234)); dependencies: `OBS-02-T03`
331. `OBS-02-T05` — Prove SLO and blind-spot gates ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L236)); dependencies: `OBS-02-T04`
332. `TEST-02-T03` — Prove authoritative retention, holds, purge and restored schemas ([source](10-testing/02-contract-and-integration-tests.md#L424)); dependencies: `TEST-02-T02`, `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T02`
333. `TEST-02-T04` — Prove provider, agent, evaluation and cost contracts ([source](10-testing/02-contract-and-integration-tests.md#L426)); dependencies: `TEST-02-T03`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-01-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `DB-05-T05`, `OBS-03-T02`
334. `TEST-02-T05` — Prove API and generated-client partition ([source](10-testing/02-contract-and-integration-tests.md#L428)); dependencies: `TEST-02-T04`, `BACKEND-02-T05`
335. `TEST-02-T06` — Prove policy and incident closure ([source](10-testing/02-contract-and-integration-tests.md#L430)); dependencies: `TEST-02-T05`, `BACKEND-03-T01`, `OBS-05-T01`
336. `TEST-02-T07` — Validate the script-derived lane ([source](10-testing/02-contract-and-integration-tests.md#L432)); dependencies: `TEST-02-T06`
337. `TEST-06-T03` — Execute T01-T16 and canary corpus ([source](10-testing/06-load-security-and-chaos-tests.md#L52)); dependencies: `TEST-06-T02`, `SEC-01-T02`
338. `INFRA-02-T03` — Implement safe migration/promotion ceremony ([source](11-infrastructure/02-ci-cd-and-release-process.md#L60)); dependencies: `INFRA-02-T02`, `INFRA-04-T02`
339. `INFRA-02-T04` — Implement application rollback ([source](11-infrastructure/02-ci-cd-and-release-process.md#L62)); dependencies: `INFRA-02-T03`
340. `TEST-06-T04` — Execute bounded chaos and rollback ([source](10-testing/06-load-security-and-chaos-tests.md#L54)); dependencies: `TEST-06-T03`, `INFRA-04-T02`, `INFRA-02-T04`
341. `TEST-06-T05` — Close adversarial command ownership ([source](10-testing/06-load-security-and-chaos-tests.md#L56)); dependencies: `TEST-06-T04`, `TEST-01-T01`
342. `INFRA-02-T05` — Exercise upgrade policy ([source](11-infrastructure/02-ci-cd-and-release-process.md#L64)); dependencies: `INFRA-02-T04`
343. `INFRA-02-T06` — Close CI/release command ownership ([source](11-infrastructure/02-ci-cd-and-release-process.md#L66)); dependencies: `INFRA-02-T05`
344. `INFRA-03-T06` — Stage but do not activate public unsubscribe edge ([source](11-infrastructure/03-private-vps-deployment.md#L65)); dependencies: `INFRA-03-T05`, `BACKEND-02-T05`, `SEC-01-T02`
345. `SEC-04-T04` — Implement the activation-ready reply and public-stop path ([source](08-security-and-compliance/04-outreach-compliance.md#L90)); dependencies: `SEC-04-T03`, `SEC-05-T02`, `BACKEND-02-T05`, `SEC-01-T02`, `INFRA-03-T06`, `PROVIDER-02-T01`
346. `INFRA-03-T07` — Prove capacity, upgrade and rollback ([source](11-infrastructure/03-private-vps-deployment.md#L67)); dependencies: `INFRA-03-T06`, `TEST-06-T02`, `INFRA-02-T04`
347. `INFRA-03-T08` — Close topology command ownership ([source](11-infrastructure/03-private-vps-deployment.md#L69)); dependencies: `INFRA-03-T07`
348. `INFRA-04-T03` — Implement the prepared/authorized/committed deletion ledger ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L159)); dependencies: `INFRA-04-T02`, `SEC-06-T02`
349. `INFRA-04-T04` — Implement policy-bounded pruning ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L161)); dependencies: `INFRA-04-T03`, `SEC-06-T02`, `DB-06-T05`
350. `SEC-06-T03` — Implement idempotent hold/redact/purge ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L106)); dependencies: `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T04`
351. `SEC-06-T04` — Implement verified rights workflow ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L108)); dependencies: `SEC-06-T03`
352. `SEC-06-T05` — Exercise privacy incident and provider exit ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L110)); dependencies: `SEC-06-T04`
353. `INFRA-04-T05` — Implement isolated PITR/full restore ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L163)); dependencies: `INFRA-04-T04`
354. `WF-06-T05` — Implement recovery/repair runbook command ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L76)); dependencies: `WF-06-T04`, `OBS-05-T01`, `INFRA-04-T05`
355. `TEST-03-T06` — Prove typed repair and isolated restore ([source](10-testing/03-workflow-recovery-tests.md#L73)); dependencies: `TEST-03-T05`, `INFRA-04-T02`, `WF-06-T05`
356. `TEST-03-T07` — Close command ownership ([source](10-testing/03-workflow-recovery-tests.md#L75)); dependencies: `TEST-03-T06`
357. `OBS-04-T04` — Implement workflow evaluation suites ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L100)); dependencies: `OBS-04-T03`, `ARCH-03-T01`, `DB-05-T01`, `ARCH-02-T01`, `BACKEND-01-T04`, `WF-00-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`, `WF-06-T05`, `PROVIDER-01-T01`, `TEST-03-T03`, `TEST-03-T04`, `TEST-03-T06`, `TEST-04-T06`, `WF-05-T05`, `WF-01-T03`, `TEST-04-T05`
358. `OBS-04-T05` — Operate shadow/drift/rolling gates ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L102)); dependencies: `OBS-04-T04`
359. `OBS-05-T03` — Complete all typed incident recovery runbooks ([source](09-observability-and-evaluation/05-incident-response.md#L146)); dependencies: `OBS-05-T02`, `PRODUCT-03-T03`, `SEC-02-T05`, `SEC-03-T04`, `INFRA-02-T04`, `INFRA-04-T05`, `WF-06-T05`
360. `PRODUCT-03-T04` — Exercise integrated operator recovery ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L117)); dependencies: `PRODUCT-03-T03`, `SEC-05-T04`, `OBS-05-T02`, `OBS-05-T03`
361. `OBS-05-T04` — Wire alerts/contacts/communications ([source](09-observability-and-evaluation/05-incident-response.md#L148)); dependencies: `OBS-05-T03`, `OBS-02-T04`
362. `OBS-05-T05` — Exercise all runbooks ([source](09-observability-and-evaluation/05-incident-response.md#L150)); dependencies: `OBS-05-T04`
363. `OBS-05-T06` — Implement post-incident and re-enable gate ([source](09-observability-and-evaluation/05-incident-response.md#L152)); dependencies: `OBS-05-T05`
364. `TEST-01-T05` — Wire CI/release gates ([source](10-testing/01-testing-strategy.md#L152)); dependencies: `TEST-01-T04`, `TEST-02-T07`, `TEST-05-T04`, `TEST-06-T04`, `TEST-03-T06`, `TEST-04-T06`, `TEST-03-T07`, `TEST-06-T05`
365. `TEST-01-T06` — Operate flake and quarantine policy ([source](10-testing/01-testing-strategy.md#L154)); dependencies: `TEST-01-T05`
366. `INFRA-05-T01` — Implement telemetry and authoritative comparisons ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L84)); dependencies: `OBS-02-T01`, `OBS-01-T03`, `BACKEND-06-T02`
367. `INFRA-05-T02` — Implement exact alert/incident routing ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L86)); dependencies: `INFRA-05-T01`, `OBS-02-T04`, `OBS-05-T01`, `OBS-05-T04`
368. `INFRA-05-T03` — Establish two independent on-call paths ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L88)); dependencies: `INFRA-05-T02`
369. `INFRA-05-T04` — Implement direct Critical signaling and the E2E watchdog ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L90)); dependencies: `INFRA-05-T03`, `OBS-05-T01`
370. `INFRA-05-T05` — Monitor the sole AWS S3 deletion witness ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L92)); dependencies: `INFRA-05-T04`, `INFRA-04-T03`
371. `INFRA-05-T06` — Execute every DR scenario ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L94)); dependencies: `INFRA-05-T05`, `INFRA-02-T04`, `SEC-03-T04`, `INFRA-04-T02`
372. `INFRA-04-T06` — Exercise clean-host recovery every 90 days ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L165)); dependencies: `INFRA-04-T05`, `INFRA-05-T06`
373. `INFRA-04-T07` — Exercise off-Google bootstrap and key rotation ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L167)); dependencies: `INFRA-04-T06`
374. `INFRA-04-T08` — Close backup/restore command ownership ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L169)); dependencies: `INFRA-04-T07`
375. `INFRA-05-T07` — Operate freshness and re-enable gates ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L96)); dependencies: `INFRA-05-T06`, `INFRA-04-T06`
376. `ARCH-01-T06` — Prove private operations ([source](01-architecture/01-target-system-architecture.md#L141)); dependencies: `ARCH-01-T05`, `INFRA-03-T07`, `INFRA-04-T06`, `INFRA-05-T07`, `OBS-05-T03`
377. `INFRA-05-T08` — Close command and DR scenario sets ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L98)); dependencies: `INFRA-05-T07`
378. `LAUNCH-02-T01` — Freeze the internal entry and authority-zero target ([source](12-launch-and-operations/02-controlled-internal-launch.md#L70)); dependencies: `LAUNCH-01-T06`, `INFRA-02-T04`, `INFRA-04-T06`, `OBS-02-T05`, `INFRA-05-T07`, `ARCH-01-T05`, `TEST-01-T02`, `TEST-01-T05`, `INFRA-03-T08`
379. `LAUNCH-02-T02` — Promote the private candidate safely ([source](12-launch-and-operations/02-controlled-internal-launch.md#L72)); dependencies: `LAUNCH-02-T01`, `INFRA-02-T02`, `INFRA-04-T02`
380. `LAUNCH-02-T03` — Run bounded synthetic/internal operations ([source](12-launch-and-operations/02-controlled-internal-launch.md#L74)); dependencies: `LAUNCH-02-T02`
381. `LAUNCH-02-T04` — Prove restore, witness, alerts and DR ([source](12-launch-and-operations/02-controlled-internal-launch.md#L76)); dependencies: `LAUNCH-02-T03`, `INFRA-03-T04`, `INFRA-04-T06`, `INFRA-05-T06`, `TEST-06-T04`
382. `LAUNCH-02-T05` — Close rollback and M8 exit ([source](12-launch-and-operations/02-controlled-internal-launch.md#L78)); dependencies: `LAUNCH-02-T04`
383. `LAUNCH-05-T01` — Build the reproducible advisory and inventory review ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L117)); dependencies: `INFRA-02-T02`
384. `LAUNCH-05-T02` — Produce pinned immutable candidates ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L119)); dependencies: `LAUNCH-05-T01`
385. `LAUNCH-05-T03` — Run class-specific migrations/evaluations ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L121)); dependencies: `LAUNCH-05-T02`
386. `LAUNCH-05-T04` — Canary, promote and prove rollback/restore ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L123)); dependencies: `LAUNCH-05-T03`, `INFRA-02-T04`, `INFRA-04-T02`
387. `LAUNCH-05-T05` — Operate cadence, EOL and emergency controls ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L125)); dependencies: `LAUNCH-05-T04`

## M9

388. `SEC-04-T05` — Obtain real-recipient counsel and provider-policy decision ([source](08-security-and-compliance/04-outreach-compliance.md#L92)); dependencies: `SEC-04-T04`, `PRODUCT-01-T02`, `SEC-06-T02`, `SEC-05-T04`
389. `SEC-01-T05` — Review residual risk before every authority increase ([source](08-security-and-compliance/01-threat-model.md#L109)); dependencies: `SEC-01-T04`, `OBS-04-T05`, `INFRA-04-T06`, `LAUNCH-05-T04`
390. `PRODUCT-02-T04` — Pre-register the staged M9 decision ([source](00-product-strategy/02-success-metrics.md#L128)); dependencies: `PRODUCT-02-T03`, `SEC-01-T05`
391. `TEST-05-T05` — Prove scanner-safe public unsubscribe ([source](10-testing/05-end-to-end-browser-tests.md#L64)); dependencies: `TEST-05-T04`, `SEC-04-T04`
392. `TEST-05-T06` — Close private/public browser command ownership ([source](10-testing/05-end-to-end-browser-tests.md#L66)); dependencies: `TEST-05-T05`, `TEST-01-T01`
393. `LAUNCH-03-T01` — Freeze one staged real-experiment entry ([source](12-launch-and-operations/03-first-real-experiment.md#L89)); dependencies: `LAUNCH-02-T05`, `SEC-01-T05`, `TEST-05-T05`, `DB-02-T03`, `BACKEND-05-T05`, `PROVIDER-01-T03`, `SEC-04-T02`, `SEC-05-T03`, `PRODUCT-02-T04`, `SEC-04-T05`
394. `LAUNCH-03-T02` — Publish and mode only scanner-safe suppression ingress ([source](12-launch-and-operations/03-first-real-experiment.md#L91)); dependencies: `LAUNCH-03-T01`, `INFRA-03-T06`, `BACKEND-02-T05`, `SEC-04-T04`, `SEC-04-T05`
395. `OBS-01-T07` — Integrate active public-edge correlation ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L110)); dependencies: `OBS-01-T06`, `LAUNCH-03-T02`, `SEC-04-T04`
396. `TEST-06-T06` — Prove active public route, WAF, and recipient-stop controls ([source](10-testing/06-load-security-and-chaos-tests.md#L58)); dependencies: `TEST-06-T05`, `LAUNCH-03-T02`, `BACKEND-02-T05`, `SEC-04-T04`, `OBS-01-T07`
397. `SEC-04-T06` — Prove the bounded authority ladder ([source](08-security-and-compliance/04-outreach-compliance.md#L94)); dependencies: `SEC-04-T05`, `TEST-06-T06`, `SEC-05-T04`, `OBS-03-T04`, `TEST-03-T06`
398. `SEC-05-T05` — Prove earned re-enable ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L98)); dependencies: `SEC-05-T04`, `SEC-04-T06`, `TEST-03-T06`, `OBS-05-T06`
399. `LAUNCH-03-T03` — Execute only the currently admitted stage ([source](12-launch-and-operations/03-first-real-experiment.md#L93)); dependencies: `LAUNCH-03-T02`, `SEC-04-T02`, `BACKEND-05-T03`, `BACKEND-03-T04`, `SEC-05-T03`, `SEC-04-T06`, `SEC-05-T05`, `TEST-06-T06`
400. `LAUNCH-03-T04` — Suppress every recipient signal and watch aborts ([source](12-launch-and-operations/03-first-real-experiment.md#L95)); dependencies: `LAUNCH-03-T03`, `INFRA-04-T07`, `INFRA-05-T07`
401. `LAUNCH-03-T05` — Close each stage window and record its barrier ([source](12-launch-and-operations/03-first-real-experiment.md#L97)); dependencies: `LAUNCH-03-T04`
402. `LAUNCH-04-T01` — Freeze levels, scopes and caps ([source](12-launch-and-operations/04-earned-autonomy.md#L80)); dependencies: `AGENT-01-T01`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `SEC-05-T03`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-01-T01`
403. `LAUNCH-04-T02` — Pre-register and compute promotion populations exactly ([source](12-launch-and-operations/04-earned-autonomy.md#L82)); dependencies: `LAUNCH-04-T01`
404. `LAUNCH-04-T03` — Require operator-signed one-level promotion ([source](12-launch-and-operations/04-earned-autonomy.md#L84)); dependencies: `LAUNCH-04-T02`, `LAUNCH-03-T05`, `AGENT-10-T05`, `LAUNCH-02-T05`, `OBS-04-T05`, `OBS-05-T06`, `INFRA-02-T04`
405. `LAUNCH-04-T04` — Enforce permanent authority boundaries ([source](12-launch-and-operations/04-earned-autonomy.md#L86)); dependencies: `LAUNCH-04-T03`
406. `LAUNCH-04-T05` — Implement demotion and rollback ([source](12-launch-and-operations/04-earned-autonomy.md#L88)); dependencies: `LAUNCH-04-T04`
