# Executable Roadmap Order

> Warning: generated; it does not prove implementation status. Edit source task metadata, never this file.

- Regenerate: `python3 scripts/validate_roadmap.py --write`
- Validate: `python3 scripts/validate_roadmap.py --check`
- Source-graph fingerprint: `2e061a5b5b83a4a18b5f3de88896a2b32e5e7cdf4870145b17be44dea4a63271`

## Totals

- Tasks: 438
- Documents: 84
- M0: 8
- M1: 33
- M2: 29
- M3: 91
- M4: 28
- M5: 11
- M6: 86
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
  - `AGENT-04`: 4
  - `AGENT-03`: 4
  - `AGENT-11`: 4
  - `AGENT-05`: 4
  - `AGENT-06`: 4
  - `AGENT-07`: 4
  - `AGENT-08`: 4
  - `AGENT-09`: 4
  - `AGENT-12`: 4
  - `AGENT-10`: 6
  - `PROVIDER-03`: 6
  - `PROVIDER-04`: 5
  - `PROVIDER-05`: 5
  - `PROVIDER-06`: 5
  - `PROVIDER-07`: 4
  - `PROVIDER-08`: 4
  - `WF-02`: 5
  - `WF-03`: 5
  - `BACKEND-01`: 10
  - `BACKEND-02`: 5
  - `WF-04`: 5
  - `PROVIDER-01`: 6
  - `PROVIDER-02`: 5
  - `WF-05`: 6
  - `WF-06`: 5
  - `WF-07`: 4
  - `WF-08`: 4
  - `WF-09`: 4
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

1. `PRODUCT-01-T01` — Capture the M0 bet ([source](00-product-strategy/01-product-scope.md#L211)); dependencies: none
2. `PRODUCT-01-T02` — Run the narrowness test ([source](00-product-strategy/01-product-scope.md#L213)); dependencies: `PRODUCT-01-T01`
3. `PRODUCT-01-T03` — Register artifact and authority vocabulary ([source](00-product-strategy/01-product-scope.md#L215)); dependencies: `PRODUCT-01-T02`
4. `PRODUCT-01-T04` — Freeze non-goals for the first experiment ([source](00-product-strategy/01-product-scope.md#L217)); dependencies: `PRODUCT-01-T03`
5. `PRODUCT-02-T01` — Register metric and staged-decision definitions ([source](00-product-strategy/02-success-metrics.md#L142)); dependencies: `PRODUCT-01-T02`
6. `PRODUCT-02-T02` — Capture baseline evidence ([source](00-product-strategy/02-success-metrics.md#L144)); dependencies: `PRODUCT-02-T01`
7. `PRODUCT-03-T01` — Approve M0 risk posture ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L124)); dependencies: `PRODUCT-01-T02`, `PRODUCT-02-T01`
8. `PRODUCT-03-T02` — Review sunk-cost exposure at every gate ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L126)); dependencies: `PRODUCT-03-T01`

## M1

9. `WF-00-T01` — Freeze runtime responsibility map ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L67)); dependencies: `PRODUCT-01-T03`
10. `SEC-01-T01` — Freeze the planned asset and Critical threat-control registry ([source](08-security-and-compliance/01-threat-model.md#L119)); dependencies: `PRODUCT-03-T01`
11. `DB-03-T01` — Publish pure Gmail-facing composite contracts ([source](02-database/03-leads-campaigns-and-messages.md#L254)); dependencies: `PRODUCT-01-T03`, `SEC-01-T01`
12. `SEC-03-T01` — Implement the key/object contracts ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L93)); dependencies: `SEC-01-T01`
13. `PROVIDER-01-T01` — Freeze disposable Gmail OAuth and wire contracts ([source](05-providers/01-gmail-oauth-and-adapter.md#L150)); dependencies: `DB-03-T01`, `SEC-03-T01`
14. `PROVIDER-01-T02` — Implement strict send contracts and MIME builder ([source](05-providers/01-gmail-oauth-and-adapter.md#L152)); dependencies: `PROVIDER-01-T01`, `DB-03-T01`
15. `PROVIDER-02-T01` — Implement strict read adapter ([source](05-providers/02-gmail-history-sync.md#L90)); dependencies: `PROVIDER-01-T01`
16. `TEST-01-T01` — Freeze the coverage registry ([source](10-testing/01-testing-strategy.md#L161)); dependencies: `PRODUCT-01-T03`
17. `TEST-01-T02` — Freeze and parse the command registry ([source](10-testing/01-testing-strategy.md#L163)); dependencies: `TEST-01-T01`
18. `TEST-01-T03` — Build environment and fixture isolation ([source](10-testing/01-testing-strategy.md#L165)); dependencies: `TEST-01-T02`
19. `TEST-04-T01` — Build strict offline Gmail fixtures ([source](10-testing/04-gmail-side-effect-tests.md#L72)); dependencies: `PROVIDER-01-T02`, `TEST-01-T03`, `PROVIDER-01-T01`
20. `TEST-04-T02` — Close offline Gmail command ownership ([source](10-testing/04-gmail-side-effect-tests.md#L74)); dependencies: `TEST-04-T01`, `TEST-01-T02`, `PROVIDER-01-T01`
21. `TEST-01-T04` — Implement evidence capture ([source](10-testing/01-testing-strategy.md#L167)); dependencies: `TEST-01-T03`
22. `WF-01-T01` — Provision the isolated harness from attested external resources ([source](03-workflows/01-dbos-production-acceptance-spike.md#L196)); dependencies: `WF-00-T01`, `SEC-01-T01`, `TEST-01-T01`, `TEST-01-T02`, `TEST-01-T03`, `TEST-01-T04`
23. `WF-01-T02` — Implement typed finite fixture and sole gateway ([source](03-workflows/01-dbos-production-acceptance-spike.md#L198)); dependencies: `WF-01-T01`
24. `WF-01-T03` — Implement kill/reconciliation instrumentation ([source](03-workflows/01-dbos-production-acceptance-spike.md#L200)); dependencies: `WF-01-T02`
25. `PRODUCT-03-T03` — Encode the reusable fail-closed stop interface ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L128)); dependencies: `PRODUCT-03-T02`, `WF-01-T03`
26. `ARCH-01-T01` — Run M1 DBOS production acceptance ([source](01-architecture/01-target-system-architecture.md#L160)); dependencies: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`
27. `WF-00-T02` — Execute WF-01 acceptance suite ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L69)); dependencies: `WF-00-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`
28. `WF-01-T04` — Run eight-item matrix from clean state ([source](03-workflows/01-dbos-production-acceptance-spike.md#L202)); dependencies: `WF-01-T03`
29. `TEST-03-T01` — Build the process-level kill harness ([source](10-testing/03-workflow-recovery-tests.md#L82)); dependencies: `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-01-T03`
30. `TEST-03-T02` — Execute the independent M1 runtime matrix ([source](10-testing/03-workflow-recovery-tests.md#L84)); dependencies: `TEST-03-T01`, `WF-01-T01`, `WF-01-T02`, `WF-01-T03`, `TEST-01-T04`
31. `WF-01-T05` — Export evidence and dispose schema ([source](03-workflows/01-dbos-production-acceptance-spike.md#L204)); dependencies: `WF-01-T04`, `TEST-03-T02`
32. `TEST-03-T03` — Independently verify the exported M1 acceptance or rejection bundle ([source](10-testing/03-workflow-recovery-tests.md#L86)); dependencies: `TEST-03-T02`, `WF-01-T05`
33. `WF-00-T03` — Emit the signed discriminated DBOS gate ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L71)); dependencies: `WF-00-T02`, `TEST-03-T03`, `WF-01-T05`
34. `WF-00-T04` — Resolve one selected runtime and execute fallback only on rejection ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L73)); dependencies: `WF-00-T03`
35. `WF-00-T05` — Reconsider adjacent layers only from new evidence ([source](03-workflows/00-dbos-selection-and-temporal-fallback.md#L75)); dependencies: `WF-00-T04`
36. `WF-01-T06` — Verify the converged selected-runtime branch ([source](03-workflows/01-dbos-production-acceptance-spike.md#L206)); dependencies: `WF-01-T05`, `WF-00-T04`
37. `INFRA-01-T01` — Freeze prerequisites and preflight ([source](11-infrastructure/01-local-development.md#L73)); dependencies: `TEST-01-T02`
38. `INFRA-01-T02` — Implement isolated host/Compose modes ([source](11-infrastructure/01-local-development.md#L75)); dependencies: `INFRA-01-T01`
39. `INFRA-01-T03` — Implement safe reset and cleanup ([source](11-infrastructure/01-local-development.md#L77)); dependencies: `INFRA-01-T02`
40. `INFRA-01-T04` — Document and retain local smoke evidence ([source](11-infrastructure/01-local-development.md#L79)); dependencies: `INFRA-01-T03`
41. `INFRA-01-T05` — Close local command ownership ([source](11-infrastructure/01-local-development.md#L81)); dependencies: `INFRA-01-T04`, `TEST-01-T01`, `TEST-01-T02`

## M2

42. `ARCH-03-T01` — Encode enums and transition tables at M2 ([source](01-architecture/03-domain-events-and-state-machines.md#L388)); dependencies: `PRODUCT-01-T03`
43. `ARCH-03-T02` — Persist events and idempotency atomically ([source](01-architecture/03-domain-events-and-state-machines.md#L390)); dependencies: `ARCH-03-T01`
44. `ARCH-03-T03` — Map runtime states explicitly ([source](01-architecture/03-domain-events-and-state-machines.md#L392)); dependencies: `ARCH-03-T02`, `WF-00-T04`
45. `DB-01-T01` — Create core domain types ([source](02-database/01-core-data-model.md#L277)); dependencies: `ARCH-03-T01`
46. `DB-01-T02` — Create the M2 core migration ([source](02-database/01-core-data-model.md#L279)); dependencies: `DB-01-T01`
47. `ARCH-02-T01` — Create inward contracts at M2 ([source](01-architecture/02-module-boundaries.md#L114)); dependencies: `ARCH-03-T01`, `DB-01-T02`
48. `ARCH-01-T02` — Build the M2 product core ([source](01-architecture/01-target-system-architecture.md#L162)); dependencies: `ARCH-01-T01`, `ARCH-02-T01`, `ARCH-03-T01`
49. `ARCH-02-T02` — Implement PostgreSQL unit of work ([source](01-architecture/02-module-boundaries.md#L116)); dependencies: `ARCH-02-T01`, `ARCH-03-T01`
50. `DB-01-T03` — Implement optimistic unit of work ([source](02-database/01-core-data-model.md#L281)); dependencies: `DB-01-T02`
51. `DB-01-T04` — Map runtime runs ([source](02-database/01-core-data-model.md#L283)); dependencies: `DB-01-T03`, `WF-00-T04`
52. `DB-01-T05` — Enforce all independent effect controls default-off ([source](02-database/01-core-data-model.md#L285)); dependencies: `DB-01-T04`
53. `DB-02-T01` — Encode immutable brief and staged decision models ([source](02-database/02-experiment-and-offer-schema.md#L54)); dependencies: `PRODUCT-01-T03`, `PRODUCT-02-T01`
54. `DB-02-T02` — Migrate normalized experiment records ([source](02-database/02-experiment-and-offer-schema.md#L56)); dependencies: `DB-02-T01`
55. `DB-02-T03` — Implement version append repositories ([source](02-database/02-experiment-and-offer-schema.md#L58)); dependencies: `DB-02-T02`
56. `DB-02-T04` — Implement deterministic metric snapshot ([source](02-database/02-experiment-and-offer-schema.md#L60)); dependencies: `DB-02-T03`
57. `DB-02-T05` — Record checkpoint decision atomically ([source](02-database/02-experiment-and-offer-schema.md#L62)); dependencies: `DB-02-T04`
58. `DB-03-T02` — Migrate identity and lead records ([source](02-database/03-leads-campaigns-and-messages.md#L256)); dependencies: `DB-03-T01`, `ARCH-03-T01`
59. `DB-04-T01` — Define typed envelopes and artifact registry ([source](02-database/04-agent-artifacts-and-evidence.md#L102)); dependencies: `PRODUCT-01-T03`
60. `DB-04-T02` — Migrate immutable run/artifact/evidence tables ([source](02-database/04-agent-artifacts-and-evidence.md#L104)); dependencies: `DB-04-T01`
61. `DB-05-T01` — Encode event schemas/catalog ([source](02-database/05-audit-events-and-idempotency.md#L327)); dependencies: `ARCH-03-T01`
62. `DB-05-T02` — Migrate append-only safety tables ([source](02-database/05-audit-events-and-idempotency.md#L329)); dependencies: `DB-05-T01`
63. `DB-03-T03` — Migrate staged campaigns, action authorizations, and suppression ([source](02-database/03-leads-campaigns-and-messages.md#L258)); dependencies: `DB-03-T02`, `ARCH-03-T01`, `DB-05-T02`
64. `DB-03-T04` — Migrate message and send ledger ([source](02-database/03-leads-campaigns-and-messages.md#L260)); dependencies: `DB-03-T03`, `ARCH-03-T01`
65. `DB-05-T03` — Implement idempotent command middleware ([source](02-database/05-audit-events-and-idempotency.md#L331)); dependencies: `DB-05-T02`
66. `DB-05-T04` — Implement outbox and internal consumer atomicity ([source](02-database/05-audit-events-and-idempotency.md#L333)); dependencies: `DB-05-T03`
67. `DB-06-T01` — Author the M2 revision chain ([source](02-database/06-migrations-seeding-and-retention.md#L189)); dependencies: `DB-01-T02`, `DB-02-T02`, `DB-03-T04`, `DB-04-T02`, `DB-05-T02`
68. `DB-06-T02` — Implement deterministic seeding ([source](02-database/06-migrations-seeding-and-retention.md#L191)); dependencies: `DB-06-T01`
69. `DB-06-T03` — Prove backup and fresh restore ([source](02-database/06-migrations-seeding-and-retention.md#L193)); dependencies: `DB-06-T02`
70. `SEC-06-T01` — Publish the early privacy/minimization interface ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L127)); dependencies: `PRODUCT-01-T03`, `DB-06-T01`

## M3

71. `DB-06-T04` — Implement the later-migration evidence gate ([source](02-database/06-migrations-seeding-and-retention.md#L195)); dependencies: `DB-06-T03`
72. `AGENT-01-T01` — Implement frozen shared models and registries ([source](04-agents/01-agent-runtime-and-contracts.md#L697)); dependencies: `DB-01-T02`, `DB-04-T02`
73. `AGENT-10-T01` — Freeze ten complete suites and the signed non-model M3 fixture manifest ([source](04-agents/12-agent-evals-and-versioning.md#L365)); dependencies: `DB-02-T03`, `DB-03-T03`, `DB-03-T04`, `DB-04-T01`
74. `AGENT-01-T02` — Implement least-authority dependency composition ([source](04-agents/01-agent-runtime-and-contracts.md#L699)); dependencies: `AGENT-01-T01`, `AGENT-10-T01`
75. `AGENT-02-T01` — Encode exact schemas and immutable configuration ([source](04-agents/02-idea-discovery-agent.md#L57)); dependencies: `DB-02-T01`, `DB-04-T01`, `AGENT-10-T01`, `AGENT-01-T01`
76. `AGENT-02-T02` — Implement bounded specialist execution ([source](04-agents/02-idea-discovery-agent.md#L59)); dependencies: `AGENT-02-T01`, `AGENT-01-T02`
77. `AGENT-04-T01` — Encode exact schemas and immutable configuration ([source](04-agents/03-market-research-agent.md#L57)); dependencies: `AGENT-02-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-04-T01`
78. `AGENT-04-T02` — Implement bounded specialist execution ([source](04-agents/03-market-research-agent.md#L59)); dependencies: `AGENT-04-T01`, `AGENT-01-T02`
79. `AGENT-03-T01` — Encode exact schemas and immutable configuration ([source](04-agents/04-offer-design-agent.md#L59)); dependencies: `AGENT-02-T01`, `AGENT-04-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-02-T03`
80. `AGENT-03-T02` — Implement bounded specialist execution ([source](04-agents/04-offer-design-agent.md#L61)); dependencies: `AGENT-03-T01`, `AGENT-01-T02`
81. `AGENT-11-T01` — Encode exact schemas and immutable configuration ([source](04-agents/05-lead-discovery-agent.md#L56)); dependencies: `AGENT-03-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T03`
82. `AGENT-11-T02` — Implement bounded specialist execution ([source](04-agents/05-lead-discovery-agent.md#L58)); dependencies: `AGENT-11-T01`, `AGENT-01-T02`
83. `AGENT-05-T01` — Encode exact schemas and immutable configuration ([source](04-agents/06-lead-research-agent.md#L57)); dependencies: `AGENT-11-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T03`
84. `AGENT-05-T02` — Implement bounded specialist execution ([source](04-agents/06-lead-research-agent.md#L59)); dependencies: `AGENT-05-T01`, `AGENT-01-T02`
85. `AGENT-06-T01` — Encode exact schemas and immutable configuration ([source](04-agents/07-lead-qualification-agent.md#L56)); dependencies: `AGENT-03-T01`, `AGENT-05-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T03`
86. `AGENT-06-T02` — Implement bounded specialist execution ([source](04-agents/07-lead-qualification-agent.md#L58)); dependencies: `AGENT-06-T01`, `AGENT-01-T02`
87. `AGENT-07-T01` — Encode exact schemas and immutable configuration ([source](04-agents/08-email-writing-agent.md#L56)); dependencies: `AGENT-03-T01`, `AGENT-05-T01`, `AGENT-06-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T04`
88. `AGENT-07-T02` — Implement bounded specialist execution ([source](04-agents/08-email-writing-agent.md#L58)); dependencies: `AGENT-07-T01`, `AGENT-01-T02`
89. `AGENT-08-T01` — Encode exact schemas and immutable configuration ([source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L58)); dependencies: `AGENT-03-T01`, `AGENT-07-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-03-T04`
90. `AGENT-08-T02` — Implement bounded specialist execution ([source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L60)); dependencies: `AGENT-08-T01`, `AGENT-01-T02`
91. `AGENT-09-T01` — Encode exact schemas and immutable configuration ([source](04-agents/10-experiment-evaluation-agent.md#L56)); dependencies: `AGENT-03-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-02-T04`, `DB-04-T01`
92. `AGENT-09-T02` — Implement bounded specialist execution ([source](04-agents/10-experiment-evaluation-agent.md#L58)); dependencies: `AGENT-09-T01`, `AGENT-01-T02`
93. `AGENT-12-T01` — Encode exact schemas and immutable configuration ([source](04-agents/11-global-learning-engine.md#L57)); dependencies: `AGENT-09-T01`, `AGENT-10-T01`, `AGENT-01-T01`, `DB-04-T01`
94. `AGENT-12-T02` — Implement bounded specialist execution ([source](04-agents/11-global-learning-engine.md#L59)); dependencies: `AGENT-12-T01`, `AGENT-01-T02`
95. `PROVIDER-03-T01` — Implement exact model protocol ([source](05-providers/03-model-provider.md#L106)); dependencies: `AGENT-01-T01`, `DB-01-T01`
96. `PROVIDER-03-T02` — Implement OpenAI Responses adapter ([source](05-providers/03-model-provider.md#L108)); dependencies: `PROVIDER-03-T01`
97. `PROVIDER-03-T03` — Implement ceilings and cancellation ([source](05-providers/03-model-provider.md#L110)); dependencies: `PROVIDER-03-T02`
98. `PROVIDER-03-T04` — Implement signed live-capture/fixture adapters ([source](05-providers/03-model-provider.md#L112)); dependencies: `PROVIDER-03-T03`
99. `PROVIDER-04-T01` — Implement exact capability service ([source](05-providers/04-search-provider.md#L102)); dependencies: `AGENT-01-T01`, `DB-01-T01`
100. `PROVIDER-04-T02` — Implement Brave raw adapter and filters ([source](05-providers/04-search-provider.md#L104)); dependencies: `PROVIDER-04-T01`
101. `PROVIDER-05-T01` — Implement exact evidence/page contracts ([source](05-providers/05-page-fetching-and-extraction.md#L107)); dependencies: `AGENT-01-T01`, `DB-01-T01`
102. `DB-04-T03` — Implement evidence capture and linking ([source](02-database/04-agent-artifacts-and-evidence.md#L106)); dependencies: `DB-04-T02`, `PROVIDER-05-T01`
103. `PROVIDER-05-T02` — Implement scoped evidence reader ([source](05-providers/05-page-fetching-and-extraction.md#L109)); dependencies: `PROVIDER-05-T01`
104. `PROVIDER-06-T01` — Implement exact two-family contracts ([source](05-providers/06-enrichment-provider.md#L101)); dependencies: `AGENT-01-T01`, `DB-01-T01`
105. `PROVIDER-07-T01` — Define neutral split capabilities ([source](05-providers/07-calendar-provider.md#L56)); dependencies: `ARCH-02-T01`, `ARCH-03-T01`
106. `PROVIDER-07-T02` — Implement signed fixtures and replacement adapter ([source](05-providers/07-calendar-provider.md#L58)); dependencies: `PROVIDER-07-T01`
107. `PROVIDER-08-T01` — Encode discovery capability and source registry ([source](05-providers/08-lead-discovery-provider.md#L51)); dependencies: `AGENT-01-T01`, `DB-01-T01`
108. `PROVIDER-08-T02` — Implement multiple recorded source adapters ([source](05-providers/08-lead-discovery-provider.md#L53)); dependencies: `PROVIDER-08-T01`
109. `BACKEND-01-T01` — Implement shared M3 recording and evaluation sole writers ([source](06-backend/01-domain-services.md#L86)); dependencies: `AGENT-01-T01`, `DB-04-T02`, `DB-05-T03`
110. `DB-04-T04` — Implement validation and acceptance transitions ([source](02-database/04-agent-artifacts-and-evidence.md#L108)); dependencies: `DB-04-T03`, `BACKEND-01-T01`, `ARCH-03-T01`
111. `BACKEND-03-T01` — Encode action/fresh-gateway facts and reason registry ([source](06-backend/03-policy-engine.md#L121)); dependencies: `DB-05-T02`, `ARCH-03-T01`, `DB-03-T01`
112. `BACKEND-03-T02` — Implement CommercialPolicyEngine and deterministic rule composition ([source](06-backend/03-policy-engine.md#L123)); dependencies: `BACKEND-03-T01`
113. `BACKEND-03-T03` — Implement PolicyEvaluationService ([source](06-backend/03-policy-engine.md#L125)); dependencies: `BACKEND-03-T02`
114. `OBS-01-T01` — Implement schema/registry/redaction ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L110)); dependencies: `SEC-06-T01`
115. `OBS-03-T01` — Implement currency/price/usage contracts ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L106)); dependencies: `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `PROVIDER-01-T01`
116. `OBS-03-T02` — Implement reservation/reconciliation ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L108)); dependencies: `OBS-03-T01`, `DB-05-T02`
117. `DB-05-T05` — Implement policy/cost reconciliation ([source](02-database/05-audit-events-and-idempotency.md#L335)); dependencies: `DB-05-T04`, `PROVIDER-03-T04`, `OBS-03-T02`
118. `PRODUCT-02-T03` — Implement gate queries in milestone order ([source](00-product-strategy/02-success-metrics.md#L146)); dependencies: `PRODUCT-02-T02`, `DB-05-T05`
119. `AGENT-01-T03` — Implement finite execution and ledger ([source](04-agents/01-agent-runtime-and-contracts.md#L701)); dependencies: `AGENT-01-T02`, `OBS-03-T02`
120. `AGENT-01-T04` — Implement deterministic validation/persistence handoff ([source](04-agents/01-agent-runtime-and-contracts.md#L703)); dependencies: `AGENT-01-T03`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
121. `AGENT-01-T05` — Prove authority and observability boundary ([source](04-agents/01-agent-runtime-and-contracts.md#L705)); dependencies: `AGENT-01-T04`
122. `AGENT-02-T03` — Validate and connect the deterministic handoff ([source](04-agents/02-idea-discovery-agent.md#L61)); dependencies: `AGENT-02-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
123. `AGENT-03-T03` — Validate and connect the deterministic handoff ([source](04-agents/04-offer-design-agent.md#L63)); dependencies: `AGENT-03-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `BACKEND-03-T03`
124. `AGENT-06-T03` — Validate and connect the deterministic handoff ([source](04-agents/07-lead-qualification-agent.md#L60)); dependencies: `AGENT-06-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
125. `AGENT-07-T03` — Validate and connect the deterministic handoff ([source](04-agents/08-email-writing-agent.md#L60)); dependencies: `AGENT-07-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
126. `AGENT-08-T03` — Validate and connect the deterministic handoff ([source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L62)); dependencies: `AGENT-08-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `BACKEND-03-T03`
127. `AGENT-09-T03` — Validate and connect the deterministic handoff ([source](04-agents/10-experiment-evaluation-agent.md#L60)); dependencies: `AGENT-09-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
128. `AGENT-12-T03` — Validate and connect the deterministic handoff ([source](04-agents/11-global-learning-engine.md#L61)); dependencies: `AGENT-12-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`
129. `PROVIDER-04-T03` — Implement evidence/ledger/cost handoff ([source](05-providers/04-search-provider.md#L106)); dependencies: `PROVIDER-04-T02`, `OBS-03-T02`, `DB-04-T03`
130. `PROVIDER-04-T04` — Implement capture and fixture modes ([source](05-providers/04-search-provider.md#L108)); dependencies: `PROVIDER-04-T03`
131. `PROVIDER-04-T05` — Prove replacement/authority boundary ([source](05-providers/04-search-provider.md#L110)); dependencies: `PROVIDER-04-T04`
132. `PROVIDER-05-T03` — Implement safe HTTP extractor ([source](05-providers/05-page-fetching-and-extraction.md#L111)); dependencies: `PROVIDER-05-T02`, `OBS-03-T02`, `DB-04-T03`
133. `PROVIDER-05-T04` — Implement hash/span and fixture gates ([source](05-providers/05-page-fetching-and-extraction.md#L113)); dependencies: `PROVIDER-05-T03`
134. `AGENT-04-T03` — Validate and connect the deterministic handoff ([source](04-agents/03-market-research-agent.md#L61)); dependencies: `AGENT-04-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `PROVIDER-04-T04`, `PROVIDER-05-T04`
135. `PROVIDER-05-T05` — Prove replacement/authority and retention ([source](05-providers/05-page-fetching-and-extraction.md#L115)); dependencies: `PROVIDER-05-T04`
136. `PROVIDER-06-T02` — Implement deterministic identity/locator composition ([source](05-providers/06-enrichment-provider.md#L103)); dependencies: `PROVIDER-06-T01`, `PROVIDER-04-T03`
137. `PROVIDER-06-T03` — Implement signed offline fixtures and replacement suite ([source](05-providers/06-enrichment-provider.md#L105)); dependencies: `PROVIDER-06-T02`
138. `ARCH-02-T03` — Wrap every provider-neutral recorded path at M3 ([source](01-architecture/02-module-boundaries.md#L118)); dependencies: `ARCH-02-T02`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `TEST-04-T01`
139. `AGENT-05-T03` — Validate and connect the deterministic handoff ([source](04-agents/06-lead-research-agent.md#L61)); dependencies: `AGENT-05-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `PROVIDER-05-T04`, `PROVIDER-06-T03`
140. `PROVIDER-08-T03` — Prove evidence/cost and replacement handoff ([source](05-providers/08-lead-discovery-provider.md#L55)); dependencies: `PROVIDER-08-T02`, `PROVIDER-05-T03`
141. `AGENT-11-T03` — Validate and connect the deterministic handoff ([source](04-agents/05-lead-discovery-agent.md#L60)); dependencies: `AGENT-11-T02`, `AGENT-01-T04`, `BACKEND-01-T01`, `DB-04-T04`, `OBS-03-T02`, `PROVIDER-08-T03`
142. `AGENT-10-T02` — Freeze implemented candidate configurations ([source](04-agents/12-agent-evals-and-versioning.md#L367)); dependencies: `AGENT-10-T01`, `AGENT-01-T01`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`, `AGENT-05-T03`, `AGENT-06-T03`, `AGENT-07-T03`, `AGENT-08-T03`, `AGENT-09-T03`, `AGENT-11-T03`, `AGENT-12-T03`, `PROVIDER-08-T03`
143. `AGENT-10-T03` — Implement isolated candidate capture ([source](04-agents/12-agent-evals-and-versioning.md#L369)); dependencies: `AGENT-10-T02`, `PROVIDER-03-T01`, `OBS-03-T02`, `AGENT-01-T01`, `AGENT-01-T04`, `PROVIDER-03-T02`, `BACKEND-01-T01`
144. `AGENT-10-T04` — Implement network-disabled deterministic scoring ([source](04-agents/12-agent-evals-and-versioning.md#L371)); dependencies: `AGENT-10-T03`
145. `AGENT-02-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/02-idea-discovery-agent.md#L63)); dependencies: `AGENT-02-T03`, `AGENT-10-T03`, `AGENT-10-T04`
146. `AGENT-04-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/03-market-research-agent.md#L63)); dependencies: `AGENT-04-T03`, `AGENT-10-T03`, `AGENT-10-T04`
147. `AGENT-03-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/04-offer-design-agent.md#L65)); dependencies: `AGENT-03-T03`, `AGENT-10-T03`, `AGENT-10-T04`
148. `AGENT-11-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/05-lead-discovery-agent.md#L62)); dependencies: `AGENT-11-T03`, `AGENT-10-T03`, `AGENT-10-T04`
149. `AGENT-05-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/06-lead-research-agent.md#L63)); dependencies: `AGENT-05-T03`, `AGENT-10-T03`, `AGENT-10-T04`
150. `AGENT-06-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/07-lead-qualification-agent.md#L62)); dependencies: `AGENT-06-T03`, `AGENT-10-T03`, `AGENT-10-T04`
151. `AGENT-07-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/08-email-writing-agent.md#L62)); dependencies: `AGENT-07-T03`, `AGENT-10-T03`, `AGENT-10-T04`
152. `AGENT-08-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/09-reply-evaluation-and-negotiation-agent.md#L64)); dependencies: `AGENT-08-T03`, `AGENT-10-T03`, `AGENT-10-T04`
153. `AGENT-09-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/10-experiment-evaluation-agent.md#L62)); dependencies: `AGENT-09-T03`, `AGENT-10-T03`, `AGENT-10-T04`
154. `AGENT-12-T04` — Gate specialist acceptance with shared evaluation ([source](04-agents/11-global-learning-engine.md#L63)); dependencies: `AGENT-12-T03`, `AGENT-10-T03`, `AGENT-10-T04`
155. `AGENT-10-T05` — Implement comparison and operator promotion ([source](04-agents/12-agent-evals-and-versioning.md#L373)); dependencies: `AGENT-10-T04`, `AGENT-02-T04`, `AGENT-03-T04`, `AGENT-04-T04`, `AGENT-05-T04`, `AGENT-06-T04`, `AGENT-07-T04`, `AGENT-08-T04`, `AGENT-09-T04`, `AGENT-11-T04`, `AGENT-12-T04`
156. `DB-04-T05` — Gate agent promotion on evaluations ([source](02-database/04-agent-artifacts-and-evidence.md#L110)); dependencies: `DB-04-T04`, `AGENT-10-T05`
157. `ARCH-01-T03` — Add offline intelligence vertically ([source](01-architecture/01-target-system-architecture.md#L164)); dependencies: `ARCH-01-T02`, `ARCH-02-T01`, `AGENT-10-T05`, `DB-04-T05`, `ARCH-02-T03`
158. `AGENT-10-T06` — Implement runtime selection/monitoring/rollback ([source](04-agents/12-agent-evals-and-versioning.md#L375)); dependencies: `AGENT-10-T05`
159. `PROVIDER-03-T05` — Bind promoted product model activation ([source](05-providers/03-model-provider.md#L114)); dependencies: `PROVIDER-03-T04`, `AGENT-10-T05`
160. `PROVIDER-03-T06` — Prove replacement and authority seams ([source](05-providers/03-model-provider.md#L116)); dependencies: `PROVIDER-03-T05`
161. `OBS-03-T03` — Implement Bank of Israel FX capture ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L110)); dependencies: `OBS-03-T02`

## M4

162. `WF-03-T01` — Freeze origin and input contracts ([source](03-workflows/03-idea-validation-workflow.md#L48)); dependencies: `AGENT-10-T05`, `DB-02-T03`, `DB-02-T04`, `PRODUCT-02-T01`
163. `BACKEND-01-T02` — Implement pure domain values/transitions ([source](06-backend/01-domain-services.md#L88)); dependencies: `BACKEND-01-T01`, `ARCH-03-T01`, `DB-06-T01`
164. `BACKEND-01-T03` — Implement unit of work/idempotent executor ([source](06-backend/01-domain-services.md#L90)); dependencies: `BACKEND-01-T02`, `ARCH-02-T01`, `DB-05-T03`
165. `BACKEND-01-T04` — Implement M2/M4/M5 sole-writer authority ([source](06-backend/01-domain-services.md#L92)); dependencies: `BACKEND-01-T03`, `DB-06-T01`, `BACKEND-03-T03`
166. `WF-02-T01` — Encode finite stage registry ([source](03-workflows/02-experiment-lifecycle.md#L49)); dependencies: `BACKEND-01-T04`, `AGENT-10-T05`, `PROVIDER-03-T06`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `WF-01-T05`, `WF-00-T04`
167. `WF-02-T02` — Implement idempotent start and completion ([source](03-workflows/02-experiment-lifecycle.md#L51)); dependencies: `WF-02-T01`
168. `WF-02-T03` — Implement failure and resume guards ([source](03-workflows/02-experiment-lifecycle.md#L53)); dependencies: `WF-02-T02`
169. `WF-02-T04` — Verify no-send lifecycle ([source](03-workflows/02-experiment-lifecycle.md#L55)); dependencies: `WF-02-T03`
170. `WF-03-T02` — Implement idea then research ([source](03-workflows/03-idea-validation-workflow.md#L50)); dependencies: `WF-03-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`, `BACKEND-01-T01`, `DB-04-T04`, `BACKEND-01-T04`
171. `WF-03-T03` — Implement authoritative offer handoff ([source](03-workflows/03-idea-validation-workflow.md#L52)); dependencies: `WF-03-T02`, `DB-04-T04`, `BACKEND-01-T04`, `AGENT-02-T03`, `AGENT-03-T03`, `AGENT-04-T03`
172. `WF-03-T04` — Prove crash and cancel recovery ([source](03-workflows/03-idea-validation-workflow.md#L54)); dependencies: `WF-03-T03`, `WF-02-T03`
173. `WF-03-T05` — Retain the synthetic M4 gate ([source](03-workflows/03-idea-validation-workflow.md#L56)); dependencies: `WF-03-T04`
174. `BACKEND-01-T05` — Implement side-effect orchestration ([source](06-backend/01-domain-services.md#L94)); dependencies: `BACKEND-01-T04`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `OBS-03-T02`
175. `BACKEND-02-T01` — Implement the M4 private route foundation ([source](06-backend/02-api-contracts.md#L316)); dependencies: `BACKEND-01-T03`
176. `BACKEND-02-T02` — Implement M4/M5 no-send routes and client ([source](06-backend/02-api-contracts.md#L318)); dependencies: `BACKEND-02-T01`, `BACKEND-01-T04`
177. `FRONTEND-01-T01` — Map the private sales shell ([source](07-frontend/01-information-architecture.md#L38)); dependencies: `BACKEND-02-T02`
178. `FRONTEND-01-T02` — Build server-state plumbing ([source](07-frontend/01-information-architecture.md#L40)); dependencies: `FRONTEND-01-T01`, `BACKEND-02-T01`
179. `FRONTEND-01-T03` — Implement canonical state rendering ([source](07-frontend/01-information-architecture.md#L42)); dependencies: `FRONTEND-01-T02`
180. `FRONTEND-01-T04` — Implement resilient navigation ([source](07-frontend/01-information-architecture.md#L44)); dependencies: `FRONTEND-01-T03`
181. `FRONTEND-02-T01` — Render exact pre-run brief ([source](07-frontend/02-experiment-creation-flow.md#L28)); dependencies: `FRONTEND-01-T01`, `DB-02-T01`
182. `FRONTEND-02-T02` — Materialize user ideas and baseline ([source](07-frontend/02-experiment-creation-flow.md#L30)); dependencies: `FRONTEND-02-T01`
183. `FRONTEND-02-T03` — Inspect research and commercial envelope ([source](07-frontend/02-experiment-creation-flow.md#L32)); dependencies: `FRONTEND-02-T02`
184. `FRONTEND-02-T04` — Verify creation journey ([source](07-frontend/02-experiment-creation-flow.md#L34)); dependencies: `FRONTEND-02-T03`
185. `FRONTEND-03-T01` — Render the accepted experiment chain ([source](07-frontend/03-experiment-control-center.md#L28)); dependencies: `FRONTEND-02-T03`, `FRONTEND-01-T01`
186. `FRONTEND-03-T02` — Implement guarded basic controls ([source](07-frontend/03-experiment-control-center.md#L30)); dependencies: `FRONTEND-03-T01`
187. `INFRA-01-T06` — Implement product migration, seed, and generation workflow ([source](11-infrastructure/01-local-development.md#L83)); dependencies: `INFRA-01-T05`, `DB-06-T02`, `BACKEND-02-T02`
188. `INFRA-01-T07` — Complete product local reset and cleanup ([source](11-infrastructure/01-local-development.md#L85)); dependencies: `INFRA-01-T06`, `DB-01-T05`
189. `INFRA-01-T08` — Complete product smoke evidence and local command ownership ([source](11-infrastructure/01-local-development.md#L87)); dependencies: `INFRA-01-T07`, `TEST-01-T02`

## M5

190. `PROVIDER-06-T04` — Implement the terms-gated live enrichment adapter ([source](05-providers/06-enrichment-provider.md#L107)); dependencies: `PROVIDER-06-T03`, `OBS-03-T01`, `OBS-03-T02`
191. `PROVIDER-06-T05` — Prove minimization and authority ([source](05-providers/06-enrichment-provider.md#L109)); dependencies: `PROVIDER-06-T04`
192. `PROVIDER-08-T04` — Gate source-specific live discovery ([source](05-providers/08-lead-discovery-provider.md#L57)); dependencies: `PROVIDER-08-T03`, `OBS-03-T02`
193. `BACKEND-01-T06` — Prove boundary and current-truth gates ([source](06-backend/01-domain-services.md#L96)); dependencies: `BACKEND-01-T05`
194. `BACKEND-01-T07` — Implement BusinessIdentityService and phased QualificationService ([source](06-backend/01-domain-services.md#L100)); dependencies: `BACKEND-01-T06`, `DB-03-T02`, `DB-04-T04`, `AGENT-11-T03`, `AGENT-06-T03`
195. `WF-04-T01` — Freeze source and offer-filter plan ([source](03-workflows/04-lead-qualification-workflow.md#L47)); dependencies: `WF-03-T05`, `DB-02-T03`, `WF-03-T03`, `BACKEND-01-T07`, `PROVIDER-08-T03`
196. `WF-04-T02` — Implement discovery and preliminary admission ([source](03-workflows/04-lead-qualification-workflow.md#L49)); dependencies: `WF-04-T01`, `PROVIDER-08-T03`, `AGENT-11-T04`
197. `WF-04-T03` — Research only admitted candidates ([source](03-workflows/04-lead-qualification-workflow.md#L51)); dependencies: `WF-04-T02`, `PROVIDER-06-T01`, `PROVIDER-06-T03`, `PROVIDER-05-T04`, `AGENT-05-T04`
198. `WF-04-T04` — Apply final immutable filters ([source](03-workflows/04-lead-qualification-workflow.md#L53)); dependencies: `WF-04-T03`, `AGENT-06-T04`, `BACKEND-01-T04`
199. `WF-04-T05` — Retain M5 end-to-end recovery evidence ([source](03-workflows/04-lead-qualification-workflow.md#L55)); dependencies: `WF-04-T04`, `WF-02-T03`, `PROVIDER-08-T04`
200. `ARCH-01-T04` — Adjudicate the M4/M5 no-send architecture ([source](01-architecture/01-target-system-architecture.md#L166)); dependencies: `ARCH-01-T03`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-06-T03`, `WF-00-T04`

## M6

201. `BACKEND-04-T01` — Implement intent and gateway contracts ([source](06-backend/04-send-gateway.md#L73)); dependencies: `PROVIDER-02-T01`, `BACKEND-03-T01`, `ARCH-03-T01`, `PROVIDER-01-T02`, `DB-03-T01`
202. `BACKEND-05-T01` — Implement command envelope/registry/executor ([source](06-backend/05-approval-and-command-handling.md#L118)); dependencies: `DB-05-T02`, `DB-01-T01`, `DB-01-T02`
203. `SEC-04-T01` — Freeze isolated-test and prohibited-recipient policy ([source](08-security-and-compliance/04-outreach-compliance.md#L97)); dependencies: `SEC-06-T01`, `PRODUCT-01-T02`
204. `SEC-04-T02` — Implement recipient evidence contracts ([source](08-security-and-compliance/04-outreach-compliance.md#L99)); dependencies: `SEC-04-T01`
205. `SEC-04-T03` — Implement disclosures and prohibited-content validator ([source](08-security-and-compliance/04-outreach-compliance.md#L101)); dependencies: `SEC-04-T02`, `AGENT-07-T03`
206. `SEC-05-T01` — Seed and implement independent controls ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L107)); dependencies: `DB-05-T02`, `ARCH-03-T01`, `DB-01-T05`, `SEC-04-T01`
207. `SEC-05-T02` — Implement suppression under last-mile locks ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L109)); dependencies: `SEC-05-T01`, `DB-03-T03`, `DB-03-T04`, `DB-03-T01`
208. `SEC-05-T03` — Implement hierarchical reservations and rates ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L111)); dependencies: `SEC-05-T02`, `OBS-03-T02`
209. `SEC-02-T01` — Migrate and introspect the exact operational schema ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1000)); dependencies: `DB-01-T02`, `SEC-06-T01`
210. `SEC-02-T02` — Implement strict OIDC flow state ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1002)); dependencies: `SEC-02-T01`, `SEC-03-T01`
211. `SEC-02-T03` — Implement server-side sessions ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1004)); dependencies: `SEC-02-T02`
212. `SEC-02-T04` — Enforce private request boundary ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1006)); dependencies: `SEC-02-T03`, `BACKEND-02-T01`
213. `PROVIDER-07-T03` — Implement Google Calendar composition ([source](05-providers/07-calendar-provider.md#L60)); dependencies: `PROVIDER-07-T02`, `SEC-02-T04`, `SEC-03-T01`
214. `PROVIDER-07-T04` — Verify BookingGateway-only mutation and reconciliation ([source](05-providers/07-calendar-provider.md#L62)); dependencies: `PROVIDER-07-T03`
215. `WF-06-T01` — Implement idempotent control command service ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L85)); dependencies: `SEC-02-T04`, `BACKEND-05-T01`
216. `WF-06-T02` — Implement cooperative acknowledgement ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L87)); dependencies: `WF-06-T01`
217. `WF-06-T03` — Implement guarded resume/retry ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L89)); dependencies: `WF-06-T02`
218. `WF-02-T05` — Bind conversation/checkpoint controls ([source](03-workflows/02-experiment-lifecycle.md#L57)); dependencies: `WF-02-T04`, `BACKEND-05-T01`, `WF-06-T03`
219. `SEC-02-T05` — Implement lifecycle and emergency controls ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1008)); dependencies: `SEC-02-T04`
220. `BACKEND-05-T02` — Implement authenticated exception inspection and receipt service ([source](06-backend/05-approval-and-command-handling.md#L120)); dependencies: `BACKEND-05-T01`, `SEC-02-T04`, `SEC-02-T05`, `SEC-03-T01`, `DB-03-T04`, `PROVIDER-01-T02`
221. `BACKEND-05-T03` — Implement ActionAuthorizationService ([source](06-backend/05-approval-and-command-handling.md#L122)); dependencies: `BACKEND-05-T02`, `BACKEND-03-T03`
222. `BACKEND-03-T04` — Implement last-mile SEND, suppression, and rate reservation ([source](06-backend/03-policy-engine.md#L127)); dependencies: `BACKEND-03-T03`, `SEC-05-T03`, `BACKEND-05-T03`
223. `BACKEND-01-T08` — Implement BookingGateway and read reconciliation ([source](06-backend/01-domain-services.md#L102)); dependencies: `BACKEND-01-T07`, `BACKEND-05-T03`, `BACKEND-03-T03`, `PROVIDER-07-T02`, `DB-03-T04`, `BACKEND-03-T04`
224. `BACKEND-01-T09` — Implement CheckpointEvaluationService ([source](06-backend/01-domain-services.md#L104)); dependencies: `BACKEND-01-T08`, `DB-04-T04`, `AGENT-09-T04`
225. `BACKEND-01-T10` — Implement StrategyActivationService ([source](06-backend/01-domain-services.md#L106)); dependencies: `BACKEND-01-T09`, `AGENT-12-T04`, `AGENT-10-T06`
226. `BACKEND-04-T02` — Implement exact pre-call transaction/order ([source](06-backend/04-send-gateway.md#L75)); dependencies: `BACKEND-04-T01`, `BACKEND-03-T04`, `SEC-05-T03`
227. `BACKEND-05-T04` — Implement stage/control/runtime and exception handlers ([source](06-backend/05-approval-and-command-handling.md#L124)); dependencies: `BACKEND-05-T03`
228. `BACKEND-05-T05` — Implement all-current-eligible campaign snapshot creation ([source](06-backend/05-approval-and-command-handling.md#L126)); dependencies: `BACKEND-05-T04`, `DB-03-T03`
229. `BACKEND-05-T06` — Implement send/recovery/control enable gates ([source](06-backend/05-approval-and-command-handling.md#L128)); dependencies: `BACKEND-05-T05`, `SEC-05-T02`
230. `OBS-05-T01` — Implement incident/evidence contracts ([source](09-observability-and-evaluation/05-incident-response.md#L161)); dependencies: `ARCH-03-T01`, `DB-05-T01`, `PRODUCT-03-T01`
231. `OBS-05-T02` — Implement containment and recovery commands ([source](09-observability-and-evaluation/05-incident-response.md#L163)); dependencies: `OBS-05-T01`, `PRODUCT-03-T03`
232. `LAUNCH-01-T01` — Attest the isolated pilot construction target ([source](12-launch-and-operations/01-test-inbox-pilot.md#L117)); dependencies: `PRODUCT-03-T01`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `WF-01-T01`, `WF-00-T04`
233. `PROVIDER-01-T03` — Implement OAuth secret-store saga and command boundary ([source](05-providers/01-gmail-oauth-and-adapter.md#L154)); dependencies: `PROVIDER-01-T02`, `SEC-03-T01`, `SEC-02-T04`, `BACKEND-05-T01`, `DB-03-T04`, `DB-05-T03`, `LAUNCH-01-T01`
234. `PROVIDER-01-T04` — Implement one-call Gmail adapter ([source](05-providers/01-gmail-oauth-and-adapter.md#L156)); dependencies: `PROVIDER-01-T03`
235. `ARCH-02-T04` — Enforce gateway orchestration boundaries at M6 ([source](01-architecture/02-module-boundaries.md#L120)); dependencies: `ARCH-02-T03`, `DB-01-T05`, `DB-05-T05`, `PROVIDER-01-T02`, `PROVIDER-01-T04`
236. `BACKEND-04-T03` — Implement one provider call and result transactions ([source](06-backend/04-send-gateway.md#L77)); dependencies: `BACKEND-04-T02`, `PROVIDER-01-T04`, `AGENT-07-T04`
237. `PROVIDER-01-T05` — Integrate sole SendGateway path ([source](05-providers/01-gmail-oauth-and-adapter.md#L158)); dependencies: `PROVIDER-01-T04`, `BACKEND-04-T03`
238. `PROVIDER-02-T02` — Implement Sent reconciliation ([source](05-providers/02-gmail-history-sync.md#L92)); dependencies: `PROVIDER-02-T01`, `BACKEND-04-T03`, `DB-03-T01`, `PROVIDER-01-T03`
239. `ARCH-03-T04` — Implement send/booking and conversation recovery before activation ([source](01-architecture/03-domain-events-and-state-machines.md#L394)); dependencies: `ARCH-03-T03`, `DB-03-T04`, `PROVIDER-02-T02`
240. `PROVIDER-02-T03` — Implement atomic incremental pages ([source](05-providers/02-gmail-history-sync.md#L94)); dependencies: `PROVIDER-02-T02`
241. `PROVIDER-02-T04` — Implement 404 full-sync recovery ([source](05-providers/02-gmail-history-sync.md#L96)); dependencies: `PROVIDER-02-T03`
242. `BACKEND-04-T04` — Implement disjoint reconciliation/retry handoff ([source](06-backend/04-send-gateway.md#L79)); dependencies: `BACKEND-04-T03`, `PROVIDER-02-T02`
243. `DB-03-T05` — Implement sole send transaction boundaries ([source](02-database/03-leads-campaigns-and-messages.md#L262)); dependencies: `DB-03-T04`, `DB-01-T05`, `BACKEND-05-T03`, `BACKEND-04-T04`
244. `DB-03-T06` — Implement atomic history sync ([source](02-database/03-leads-campaigns-and-messages.md#L264)); dependencies: `DB-03-T05`, `PROVIDER-02-T01`, `PROVIDER-02-T03`
245. `WF-06-T04` — Implement send drain/reconciliation ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L91)); dependencies: `WF-06-T03`, `BACKEND-04-T04`, `PROVIDER-02-T02`, `PROVIDER-07-T02`
246. `SEC-03-T02` — Implement Gmail credential lifecycle ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L95)); dependencies: `SEC-03-T01`, `PROVIDER-01-T03`
247. `SEC-03-T03` — Apply exact access/redaction controls ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L97)); dependencies: `SEC-03-T02`
248. `SEC-03-T04` — Implement rotation, emergency revoke, and recovery-package refresh ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L99)); dependencies: `SEC-03-T03`
249. `OBS-01-T02` — Propagate correlation/causation ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L112)); dependencies: `OBS-01-T01`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `OBS-03-T02`
250. `OBS-01-T03` — Instrument exact boundaries ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L114)); dependencies: `OBS-01-T02`
251. `SEC-05-T04` — Wire deterministic kill triggers and alerts ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L113)); dependencies: `SEC-05-T03`, `OBS-01-T03`, `BACKEND-04-T03`, `PRODUCT-03-T03`
252. `BACKEND-02-T03` — Implement the isolated M6 owned-inbox API ([source](06-backend/02-api-contracts.md#L320)); dependencies: `BACKEND-02-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `BACKEND-03-T03`, `BACKEND-04-T04`, `BACKEND-05-T06`, `SEC-03-T02`, `SEC-04-T03`, `SEC-05-T04`, `SEC-02-T04`, `BACKEND-05-T02`, `BACKEND-01-T10`
253. `TEST-04-T03` — Prove the six-point OAuth saga ([source](10-testing/04-gmail-side-effect-tests.md#L76)); dependencies: `TEST-04-T02`, `PROVIDER-01-T03`, `DB-03-T04`, `DB-05-T03`
254. `TEST-04-T04` — Prove 14-step gateway authority and results ([source](10-testing/04-gmail-side-effect-tests.md#L78)); dependencies: `TEST-04-T03`, `BACKEND-04-T04`, `SEC-05-T03`
255. `TEST-02-T01` — Freeze complete contract and fixture registries ([source](10-testing/02-contract-and-integration-tests.md#L62)); dependencies: `DB-01-T01`, `AGENT-01-T01`, `PROVIDER-01-T02`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `TEST-01-T03`, `TEST-01-T02`
256. `TEST-02-T02` — Prove schema and transaction boundaries ([source](10-testing/02-contract-and-integration-tests.md#L64)); dependencies: `TEST-02-T01`, `DB-06-T01`, `SEC-06-T01`
257. `TEST-03-T04` — Prove every finite workflow and delivery edge ([source](10-testing/03-workflow-recovery-tests.md#L88)); dependencies: `TEST-03-T03`, `TEST-02-T02`, `ARCH-03-T01`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`
258. `TEST-03-T05` — Prove controls, versioning and migration ([source](10-testing/03-workflow-recovery-tests.md#L90)); dependencies: `TEST-03-T04`, `WF-06-T04`
259. `LAUNCH-01-T02` — Close offline Gmail and authority evidence ([source](12-launch-and-operations/01-test-inbox-pilot.md#L119)); dependencies: `LAUNCH-01-T01`, `TEST-04-T01`, `TEST-04-T03`, `TEST-04-T02`, `BACKEND-04-T04`, `PROVIDER-02-T04`, `SEC-05-T02`, `OBS-03-T02`, `BACKEND-01-T06`
260. `LAUNCH-01-T03` — Freeze the pilot entry and target ([source](12-launch-and-operations/01-test-inbox-pilot.md#L121)); dependencies: `LAUNCH-01-T02`, `PRODUCT-03-T01`, `DB-06-T03`, `AGENT-10-T05`, `WF-03-T05`, `WF-04-T05`, `WF-01-T01`, `WF-00-T04`, `PROVIDER-01-T03`, `SEC-05-T04`, `OBS-01-T03`
261. `PROVIDER-01-T06` — Build fixture and credential-security gates ([source](05-providers/01-gmail-oauth-and-adapter.md#L160)); dependencies: `PROVIDER-01-T05`, `LAUNCH-01-T03`
262. `PROVIDER-02-T05` — Gate M6 fixtures and operations ([source](05-providers/02-gmail-history-sync.md#L98)); dependencies: `PROVIDER-02-T04`, `LAUNCH-01-T03`
263. `WF-05-T01` — Bind isolated M6 campaign entry ([source](03-workflows/05-outreach-and-reply-workflow.md#L61)); dependencies: `TEST-03-T03`, `SEC-05-T03`, `BACKEND-05-T06`, `PROVIDER-01-T03`, `SEC-02-T04`, `LAUNCH-01-T03`, `WF-00-T04`, `AGENT-08-T04`, `BACKEND-04-T04`
264. `WF-05-T02` — Implement automatic draft and action authorization ([source](03-workflows/05-outreach-and-reply-workflow.md#L63)); dependencies: `WF-05-T01`, `BACKEND-05-T03`, `WF-04-T04`, `AGENT-07-T04`
265. `WF-05-T03` — Connect sole gateway and reconciliation ([source](03-workflows/05-outreach-and-reply-workflow.md#L65)); dependencies: `WF-05-T02`, `SEC-05-T03`, `BACKEND-04-T04`
266. `WF-05-T04` — Implement finite reply and negotiation loop ([source](03-workflows/05-outreach-and-reply-workflow.md#L67)); dependencies: `WF-05-T03`, `PROVIDER-02-T04`, `AGENT-08-T04`, `SEC-05-T02`
267. `WF-07-T01` — Encode booking intent and state guards ([source](03-workflows/07-booking-workflow.md#L49)); dependencies: `WF-05-T04`, `PROVIDER-07-T02`, `ARCH-03-T01`, `BACKEND-01-T08`
268. `WF-07-T02` — Implement slot proposal and confirmation ([source](03-workflows/07-booking-workflow.md#L51)); dependencies: `WF-07-T01`, `PROVIDER-07-T03`
269. `WF-07-T03` — Implement guarded create/change recovery ([source](03-workflows/07-booking-workflow.md#L53)); dependencies: `WF-07-T02`, `PROVIDER-07-T04`
270. `WF-07-T04` — Retain owned-calendar M6 proof ([source](03-workflows/07-booking-workflow.md#L55)); dependencies: `WF-07-T03`, `LAUNCH-01-T03`
271. `WF-08-T01` — Encode finite closure and evidence interfaces ([source](03-workflows/08-checkpoint-evaluation-workflow.md#L47)); dependencies: `WF-05-T04`, `AGENT-09-T04`, `ARCH-03-T01`, `BACKEND-01-T09`
272. `WF-08-T02` — Implement immutable evidence freeze ([source](03-workflows/08-checkpoint-evaluation-workflow.md#L49)); dependencies: `WF-08-T01`
273. `WF-08-T03` — Commit deterministic decision and learning trigger ([source](03-workflows/08-checkpoint-evaluation-workflow.md#L51)); dependencies: `WF-08-T02`
274. `WF-08-T04` — Retain checkpoint recovery simulation ([source](03-workflows/08-checkpoint-evaluation-workflow.md#L53)); dependencies: `WF-08-T03`
275. `WF-09-T01` — Encode checkpoint-only learning trigger ([source](03-workflows/09-global-learning-workflow.md#L50)); dependencies: `WF-08-T03`, `AGENT-12-T04`, `AGENT-10-T06`, `ARCH-03-T01`, `BACKEND-01-T10`
276. `WF-09-T02` — Implement deterministic proposal gate ([source](03-workflows/09-global-learning-workflow.md#L52)); dependencies: `WF-09-T01`
277. `WF-09-T03` — Implement campaign-boundary activation and rollback ([source](03-workflows/09-global-learning-workflow.md#L54)); dependencies: `WF-09-T02`
278. `WF-09-T04` — Retain global learning simulation ([source](03-workflows/09-global-learning-workflow.md#L56)); dependencies: `WF-09-T03`
279. `BACKEND-04-T05` — Prove M6 gateway, service authority, and observability ([source](06-backend/04-send-gateway.md#L81)); dependencies: `BACKEND-04-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `SEC-05-T04`, `TEST-03-T03`, `BACKEND-03-T03`, `BACKEND-05-T06`, `WF-00-T04`, `LAUNCH-01-T03`
280. `WF-05-T05` — Verify controls and recovery ([source](03-workflows/05-outreach-and-reply-workflow.md#L69)); dependencies: `WF-05-T04`, `BACKEND-04-T05`, `SEC-05-T04`, `WF-06-T04`, `LAUNCH-01-T03`
281. `TEST-04-T05` — Prove reconciliation and recipient signals ([source](10-testing/04-gmail-side-effect-tests.md#L80)); dependencies: `TEST-04-T04`, `PROVIDER-02-T04`, `WF-05-T04`
282. `TEST-04-T06` — Run the controlled M6 owned-alias gate and close live command ownership ([source](10-testing/04-gmail-side-effect-tests.md#L82)); dependencies: `TEST-04-T05`, `WF-05-T05`, `BACKEND-04-T05`, `SEC-05-T04`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `LAUNCH-01-T03`
283. `WF-05-T06` — Retain full M6 conversation-to-learning gate ([source](03-workflows/05-outreach-and-reply-workflow.md#L71)); dependencies: `WF-05-T05`, `TEST-04-T06`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`
284. `LAUNCH-01-T04` — Execute the exact live catalog one message at a time ([source](12-launch-and-operations/01-test-inbox-pilot.md#L123)); dependencies: `LAUNCH-01-T03`
285. `LAUNCH-01-T05` — Exercise signals and operator stop ([source](12-launch-and-operations/01-test-inbox-pilot.md#L125)); dependencies: `LAUNCH-01-T04`
286. `LAUNCH-01-T06` — Close cleanup and promotion ([source](12-launch-and-operations/01-test-inbox-pilot.md#L127)); dependencies: `LAUNCH-01-T05`

## M7

287. `ARCH-03-T05` — Generate API/UI state mappings ([source](01-architecture/03-domain-events-and-state-machines.md#L396)); dependencies: `ARCH-03-T04`
288. `BACKEND-06-T01` — Encode projection schemas/query versions ([source](06-backend/06-reporting-and-query-services.md#L124)); dependencies: `BACKEND-03-T01`, `SEC-04-T02`, `DB-05-T02`, `ARCH-03-T01`, `OBS-05-T01`
289. `BACKEND-02-T04` — Freeze the authenticated M7 report/recovery contract ([source](06-backend/02-api-contracts.md#L322)); dependencies: `BACKEND-02-T03`, `SEC-02-T04`, `BACKEND-06-T01`
290. `BACKEND-06-T02` — Implement overview/funnel/recovery queries ([source](06-backend/06-reporting-and-query-services.md#L126)); dependencies: `BACKEND-06-T01`
291. `BACKEND-06-T03` — Implement cost/provider queries ([source](06-backend/06-reporting-and-query-services.md#L128)); dependencies: `BACKEND-06-T02`, `OBS-03-T03`
292. `BACKEND-06-T04` — Implement repeatable-read/exported-snapshot pagination/API routes ([source](06-backend/06-reporting-and-query-services.md#L130)); dependencies: `BACKEND-06-T03`, `BACKEND-02-T04`
293. `BACKEND-02-T05` — Generate and gate the disabled-public API manifest and client ([source](06-backend/02-api-contracts.md#L324)); dependencies: `BACKEND-02-T04`, `BACKEND-06-T04`
294. `ARCH-02-T05` — Enforce frontend/API boundary at M7 ([source](01-architecture/02-module-boundaries.md#L122)); dependencies: `ARCH-02-T04`, `BACKEND-02-T05`
295. `BACKEND-03-T05` — Gate versions and operator explainability ([source](06-backend/03-policy-engine.md#L129)); dependencies: `BACKEND-03-T04`, `BACKEND-06-T02`, `BACKEND-06-T04`
296. `BACKEND-05-T07` — Prove OAuth saga, callback, and operator workflows ([source](06-backend/05-approval-and-command-handling.md#L130)); dependencies: `BACKEND-05-T06`, `SEC-03-T01`, `PROVIDER-01-T03`, `BACKEND-02-T03`, `BACKEND-02-T05`
297. `OBS-01-T04` — Integrate authenticated private and report correlation ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L116)); dependencies: `OBS-01-T03`, `SEC-02-T04`, `BACKEND-02-T05`
298. `FRONTEND-01-T05` — Integrate the full control plane ([source](07-frontend/01-information-architecture.md#L46)); dependencies: `FRONTEND-01-T04`, `BACKEND-02-T05`, `SEC-02-T04`, `SEC-02-T05`, `FRONTEND-02-T04`, `FRONTEND-03-T01`
299. `FRONTEND-03-T03` — Integrate cohort and conversation control ([source](07-frontend/03-experiment-control-center.md#L32)); dependencies: `FRONTEND-03-T02`, `FRONTEND-01-T05`, `BACKEND-02-T05`, `BACKEND-06-T04`, `BACKEND-05-T04`, `WF-06-T03`
300. `FRONTEND-03-T04` — Render checkpoint evidence and decision ([source](07-frontend/03-experiment-control-center.md#L34)); dependencies: `FRONTEND-03-T03`, `BACKEND-01-T09`, `WF-08-T04`
301. `FRONTEND-03-T05` — Expose strategy activation and rollback ([source](07-frontend/03-experiment-control-center.md#L36)); dependencies: `FRONTEND-03-T04`, `BACKEND-06-T04`, `BACKEND-02-T05`, `BACKEND-01-T10`, `WF-09-T04`
302. `FRONTEND-04-T01` — Build artifact renderer registry ([source](07-frontend/04-evidence-and-agent-artifacts.md#L28)); dependencies: `BACKEND-02-T05`
303. `FRONTEND-04-T02` — Trace provider-before-consumer lineage ([source](07-frontend/04-evidence-and-agent-artifacts.md#L30)); dependencies: `FRONTEND-04-T01`, `BACKEND-06-T04`
304. `FRONTEND-04-T03` — Inspect minimized business/commercial evidence ([source](07-frontend/04-evidence-and-agent-artifacts.md#L32)); dependencies: `FRONTEND-04-T02`, `BACKEND-02-T05`
305. `FRONTEND-04-T04` — Inspect checkpoint and strategy evidence ([source](07-frontend/04-evidence-and-agent-artifacts.md#L34)); dependencies: `FRONTEND-04-T03`, `BACKEND-02-T05`
306. `FRONTEND-05-T01` — Render discovery and sources ([source](07-frontend/05-lead-and-campaign-management.md#L28)); dependencies: `BACKEND-02-T05`, `BACKEND-02-T02`
307. `FRONTEND-05-T02` — Render phased qualification ([source](07-frontend/05-lead-and-campaign-management.md#L30)); dependencies: `FRONTEND-05-T01`, `BACKEND-01-T07`
308. `FRONTEND-05-T03` — Create server-owned stage membership ([source](07-frontend/05-lead-and-campaign-management.md#L32)); dependencies: `FRONTEND-05-T02`, `BACKEND-05-T06`
309. `FRONTEND-05-T04` — Operate campaign safety controls ([source](07-frontend/05-lead-and-campaign-management.md#L34)); dependencies: `FRONTEND-05-T03`, `BACKEND-02-T05`
310. `FRONTEND-05-T05` — Verify full lead-to-conversation view ([source](07-frontend/05-lead-and-campaign-management.md#L36)); dependencies: `FRONTEND-05-T04`, `BACKEND-02-T05`
311. `FRONTEND-06-T01` — Render exception queue ([source](07-frontend/06-approval-inbox.md#L28)); dependencies: `BACKEND-02-T05`
312. `FRONTEND-06-T02` — Implement purpose-bound sensitive inspection ([source](07-frontend/06-approval-inbox.md#L30)); dependencies: `FRONTEND-06-T01`, `SEC-02-T04`, `BACKEND-02-T05`
313. `FRONTEND-06-T03` — Resolve through deterministic corrections ([source](07-frontend/06-approval-inbox.md#L32)); dependencies: `FRONTEND-06-T02`
314. `FRONTEND-06-T04` — Verify queue and safety actions ([source](07-frontend/06-approval-inbox.md#L34)); dependencies: `FRONTEND-06-T03`
315. `FRONTEND-07-T01` — Render complete ordered conversation ([source](07-frontend/07-message-and-reply-timeline.md#L30)); dependencies: `BACKEND-02-T05`
316. `FRONTEND-07-T02` — Explain replies and commercial decisions ([source](07-frontend/07-message-and-reply-timeline.md#L32)); dependencies: `FRONTEND-07-T01`, `BACKEND-02-T05`
317. `FRONTEND-07-T03` — Explain automatic sending and booking ([source](07-frontend/07-message-and-reply-timeline.md#L34)); dependencies: `FRONTEND-07-T02`, `BACKEND-05-T03`, `BACKEND-02-T05`
318. `FRONTEND-07-T04` — Implement safe timeline recovery ([source](07-frontend/07-message-and-reply-timeline.md#L36)); dependencies: `FRONTEND-07-T03`, `BACKEND-04-T04`, `WF-06-T04`, `BACKEND-02-T05`, `BACKEND-01-T08`, `WF-07-T03`
319. `FRONTEND-08-T01` — Render attributed funnel ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L28)); dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
320. `FRONTEND-08-T02` — Render objections and negotiation outcomes ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L30)); dependencies: `FRONTEND-08-T01`
321. `FRONTEND-08-T03` — Render cost and commercial truth ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L32)); dependencies: `FRONTEND-08-T02`, `BACKEND-06-T03`
322. `FRONTEND-08-T04` — Compare checkpoint and global strategies ([source](07-frontend/08-cost-funnel-and-decision-analytics.md#L34)); dependencies: `FRONTEND-08-T03`, `BACKEND-06-T02`, `BACKEND-02-T05`, `BACKEND-01-T09`, `BACKEND-01-T10`
323. `FRONTEND-09-T01` — Render expanded recovery union ([source](07-frontend/09-error-recovery-and-accessibility.md#L30)); dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`
324. `FRONTEND-09-T02` — Implement provider recovery commands ([source](07-frontend/09-error-recovery-and-accessibility.md#L32)); dependencies: `FRONTEND-09-T01`, `BACKEND-04-T04`, `BACKEND-02-T05`
325. `FRONTEND-09-T03` — Implement kill and boundary rollback UX ([source](07-frontend/09-error-recovery-and-accessibility.md#L34)); dependencies: `FRONTEND-09-T02`, `SEC-05-T04`
326. `FRONTEND-09-T04` — Implement auth/privacy/error boundaries ([source](07-frontend/09-error-recovery-and-accessibility.md#L36)); dependencies: `FRONTEND-09-T03`, `BACKEND-02-T05`
327. `ARCH-01-T05` — Adjudicate the M6/M7 private-operator architecture ([source](01-architecture/01-target-system-architecture.md#L168)); dependencies: `ARCH-01-T04`, `BACKEND-03-T03`, `PROVIDER-01-T03`, `DB-03-T06`, `WF-01-T01`, `TEST-04-T06`, `BACKEND-02-T05`, `FRONTEND-03-T05`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T04`, `FRONTEND-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
328. `BACKEND-06-T05` — Prove decision reproducibility, redaction, and UI contract ([source](06-backend/06-reporting-and-query-services.md#L132)); dependencies: `BACKEND-06-T04`, `BACKEND-02-T05`

## M8

329. `OBS-01-T05` — Deploy private sink/self-health ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L118)); dependencies: `OBS-01-T04`
330. `OBS-01-T06` — Prove absence and usability ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L120)); dependencies: `OBS-01-T05`
331. `OBS-03-T04` — Implement reports/alerts/invoice review ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L112)); dependencies: `OBS-03-T03`
332. `OBS-03-T05` — Reconcile eval and runtime windows ([source](09-observability-and-evaluation/03-provider-cost-accounting.md#L114)); dependencies: `OBS-03-T04`, `AGENT-10-T01`, `AGENT-10-T05`
333. `FRONTEND-09-T05` — Verify every operator journey ([source](07-frontend/09-error-recovery-and-accessibility.md#L38)); dependencies: `FRONTEND-09-T04`, `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-03-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T02`, `FRONTEND-08-T03`, `FRONTEND-03-T05`, `FRONTEND-08-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`
334. `SEC-02-T06` — Prove bootstrap and restore ([source](08-security-and-compliance/02-authentication-and-private-access.md#L1010)); dependencies: `SEC-02-T05`
335. `OBS-02-T01` — Implement exact metric/span registries ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L327)); dependencies: `OBS-01-T01`, `OBS-01-T03`
336. `OBS-04-T01` — Freeze complete governed suite manifests ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L53)); dependencies: `AGENT-10-T01`
337. `OBS-04-T02` — Execute isolated capture ownership ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L55)); dependencies: `OBS-04-T01`
338. `OBS-04-T03` — Apply deterministic scoring and strategy gates ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L57)); dependencies: `OBS-04-T02`, `AGENT-10-T04`, `AGENT-10-T05`
339. `TEST-05-T01` — Compose isolated browser fixtures ([source](10-testing/05-end-to-end-browser-tests.md#L48)); dependencies: `TEST-01-T03`, `BACKEND-02-T05`
340. `TEST-05-T02` — Execute complete private sales journeys ([source](10-testing/05-end-to-end-browser-tests.md#L50)); dependencies: `TEST-05-T01`, `FRONTEND-01-T04`, `FRONTEND-02-T04`, `FRONTEND-03-T01`, `FRONTEND-03-T02`, `FRONTEND-04-T04`, `FRONTEND-05-T05`, `FRONTEND-06-T04`, `FRONTEND-07-T04`, `FRONTEND-08-T01`, `FRONTEND-08-T03`, `FRONTEND-09-T04`, `FRONTEND-01-T05`, `FRONTEND-03-T03`
341. `TEST-05-T03` — Attack auth and provider-action boundaries ([source](10-testing/05-end-to-end-browser-tests.md#L52)); dependencies: `TEST-05-T02`, `SEC-02-T06`, `PROVIDER-01-T06`, `FRONTEND-09-T05`
342. `TEST-05-T04` — Verify accessible responsive behavior ([source](10-testing/05-end-to-end-browser-tests.md#L54)); dependencies: `TEST-05-T03`
343. `TEST-06-T01` — Freeze capacity and destructive-target guards ([source](10-testing/06-load-security-and-chaos-tests.md#L60)); dependencies: `TEST-01-T01`
344. `INFRA-02-T01` — Extend deterministic/deep CI gates ([source](11-infrastructure/02-ci-cd-and-release-process.md#L68)); dependencies: `TEST-01-T01`
345. `INFRA-02-T02` — Build immutable supply-chain candidate ([source](11-infrastructure/02-ci-cd-and-release-process.md#L70)); dependencies: `INFRA-02-T01`
346. `TEST-06-T02` — Measure private capacity/rate/budget ([source](10-testing/06-load-security-and-chaos-tests.md#L62)); dependencies: `TEST-06-T01`, `INFRA-02-T02`
347. `INFRA-03-T01` — Provision and attest the private host ([source](11-infrastructure/03-private-vps-deployment.md#L65)); dependencies: `INFRA-02-T02`
348. `INFRA-03-T02` — Deploy the modular-monolith topology ([source](11-infrastructure/03-private-vps-deployment.md#L67)); dependencies: `INFRA-03-T01`, `INFRA-02-T02`
349. `INFRA-03-T03` — Integrate managed secret/KMS adapter ([source](11-infrastructure/03-private-vps-deployment.md#L69)); dependencies: `INFRA-03-T02`, `SEC-03-T01`
350. `INFRA-03-T04` — Gate the sole off-provider recovery repository ([source](11-infrastructure/03-private-vps-deployment.md#L71)); dependencies: `INFRA-03-T03`
351. `INFRA-03-T05` — Configure private DNS/TLS/proxy/firewall ([source](11-infrastructure/03-private-vps-deployment.md#L73)); dependencies: `INFRA-03-T04`
352. `INFRA-04-T01` — Configure exact dual-repository WAL archiving ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L169)); dependencies: `INFRA-03-T04`
353. `INFRA-04-T02` — Implement signed per-repository backups ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L171)); dependencies: `INFRA-04-T01`
354. `SEC-03-T05` — Prove clean backup/restore ([source](08-security-and-compliance/03-secrets-and-oauth-token-security.md#L101)); dependencies: `SEC-03-T04`, `INFRA-04-T02`
355. `SEC-01-T02` — Close implemented security boundaries against the planned registry ([source](08-security-and-compliance/01-threat-model.md#L121)); dependencies: `SEC-01-T01`, `BACKEND-02-T05`, `OBS-01-T06`, `INFRA-03-T02`, `INFRA-04-T02`
356. `SEC-01-T03` — Build the Critical abuse corpus ([source](08-security-and-compliance/01-threat-model.md#L123)); dependencies: `SEC-01-T02`
357. `SEC-01-T04` — Exercise disable and recovery ([source](08-security-and-compliance/01-threat-model.md#L125)); dependencies: `SEC-01-T03`
358. `OBS-02-T02` — Instrument safety and service paths ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L329)); dependencies: `OBS-02-T01`, `BACKEND-02-T05`, `DB-06-T01`, `WF-05-T05`, `AGENT-10-T05`, `SEC-05-T04`, `OBS-03-T02`, `INFRA-04-T02`
359. `SEC-06-T02` — Complete the live inventory and approve authoritative retention ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L129)); dependencies: `SEC-06-T01`, `SEC-01-T02`, `SEC-02-T05`, `SEC-03-T04`, `INFRA-04-T02`, `PROVIDER-01-T06`, `PROVIDER-02-T05`, `PROVIDER-03-T06`, `PROVIDER-04-T05`, `PROVIDER-05-T05`, `PROVIDER-06-T05`, `OBS-02-T01`, `OBS-02-T02`, `OBS-04-T01`, `OBS-04-T02`
360. `DB-06-T05` — Implement the database retention engine and recovery graph ([source](02-database/06-migrations-seeding-and-retention.md#L197)); dependencies: `DB-06-T04`, `SEC-06-T02`
361. `OBS-02-T03` — Build five dashboards and SLO calculations ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L331)); dependencies: `OBS-02-T02`
362. `OBS-02-T04` — Implement alert routes/runbooks ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L333)); dependencies: `OBS-02-T03`
363. `OBS-02-T05` — Prove SLO and blind-spot gates ([source](09-observability-and-evaluation/02-metrics-tracing-and-alerting.md#L335)); dependencies: `OBS-02-T04`
364. `TEST-02-T03` — Prove retention and restored schemas ([source](10-testing/02-contract-and-integration-tests.md#L66)); dependencies: `TEST-02-T02`, `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T02`
365. `TEST-02-T04` — Prove all agent/provider/artifact contracts ([source](10-testing/02-contract-and-integration-tests.md#L68)); dependencies: `TEST-02-T03`, `PROVIDER-01-T04`, `PROVIDER-02-T01`, `PROVIDER-03-T04`, `PROVIDER-04-T04`, `PROVIDER-05-T04`, `PROVIDER-06-T03`, `AGENT-01-T03`, `AGENT-10-T01`, `AGENT-10-T03`, `DB-05-T05`, `OBS-03-T02`
366. `TEST-02-T05` — Prove generated APIs and browser authority boundary ([source](10-testing/02-contract-and-integration-tests.md#L70)); dependencies: `TEST-02-T04`, `BACKEND-02-T05`
367. `TEST-02-T06` — Prove policy and incident routing ([source](10-testing/02-contract-and-integration-tests.md#L72)); dependencies: `TEST-02-T05`, `BACKEND-03-T01`, `OBS-05-T01`
368. `TEST-02-T07` — Close contract command ownership ([source](10-testing/02-contract-and-integration-tests.md#L74)); dependencies: `TEST-02-T06`
369. `TEST-06-T03` — Execute T01-T16 and canary corpus ([source](10-testing/06-load-security-and-chaos-tests.md#L64)); dependencies: `TEST-06-T02`, `SEC-01-T02`
370. `INFRA-02-T03` — Implement safe migration/promotion ceremony ([source](11-infrastructure/02-ci-cd-and-release-process.md#L72)); dependencies: `INFRA-02-T02`, `INFRA-04-T02`
371. `INFRA-02-T04` — Implement application rollback ([source](11-infrastructure/02-ci-cd-and-release-process.md#L74)); dependencies: `INFRA-02-T03`
372. `TEST-06-T04` — Execute bounded chaos and rollback ([source](10-testing/06-load-security-and-chaos-tests.md#L66)); dependencies: `TEST-06-T03`, `INFRA-04-T02`, `INFRA-02-T04`
373. `TEST-06-T05` — Close adversarial command ownership ([source](10-testing/06-load-security-and-chaos-tests.md#L68)); dependencies: `TEST-06-T04`, `TEST-01-T01`
374. `INFRA-02-T05` — Exercise upgrade policy ([source](11-infrastructure/02-ci-cd-and-release-process.md#L76)); dependencies: `INFRA-02-T04`
375. `INFRA-02-T06` — Close CI/release command ownership ([source](11-infrastructure/02-ci-cd-and-release-process.md#L78)); dependencies: `INFRA-02-T05`
376. `INFRA-03-T06` — Stage but do not activate public unsubscribe edge ([source](11-infrastructure/03-private-vps-deployment.md#L75)); dependencies: `INFRA-03-T05`, `BACKEND-02-T05`, `SEC-01-T02`
377. `SEC-04-T04` — Implement the activation-ready reply and public-stop path ([source](08-security-and-compliance/04-outreach-compliance.md#L103)); dependencies: `SEC-04-T03`, `SEC-05-T02`, `BACKEND-02-T05`, `SEC-01-T02`, `INFRA-03-T06`, `PROVIDER-02-T01`
378. `INFRA-03-T07` — Prove capacity, upgrade and rollback ([source](11-infrastructure/03-private-vps-deployment.md#L77)); dependencies: `INFRA-03-T06`, `TEST-06-T02`, `INFRA-02-T04`
379. `INFRA-03-T08` — Close topology command ownership ([source](11-infrastructure/03-private-vps-deployment.md#L79)); dependencies: `INFRA-03-T07`
380. `INFRA-04-T03` — Implement the prepared/authorized/committed deletion ledger ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L173)); dependencies: `INFRA-04-T02`, `SEC-06-T02`
381. `INFRA-04-T04` — Implement policy-bounded pruning ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L175)); dependencies: `INFRA-04-T03`, `SEC-06-T02`, `DB-06-T05`
382. `SEC-06-T03` — Implement idempotent hold/redact/purge ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L131)); dependencies: `SEC-06-T02`, `DB-06-T05`, `INFRA-04-T04`
383. `SEC-06-T04` — Implement verified rights workflow ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L133)); dependencies: `SEC-06-T03`
384. `SEC-06-T05` — Exercise privacy incident and provider exit ([source](08-security-and-compliance/06-data-privacy-and-retention.md#L135)); dependencies: `SEC-06-T04`
385. `INFRA-04-T05` — Implement isolated PITR/full restore ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L177)); dependencies: `INFRA-04-T04`
386. `WF-06-T05` — Implement recovery/repair runbook command ([source](03-workflows/06-pause-cancel-resume-and-recovery.md#L93)); dependencies: `WF-06-T04`, `OBS-05-T01`, `INFRA-04-T05`
387. `TEST-03-T06` — Prove typed repair and isolated restore ([source](10-testing/03-workflow-recovery-tests.md#L92)); dependencies: `TEST-03-T05`, `INFRA-04-T02`, `WF-06-T05`
388. `TEST-03-T07` — Close command ownership ([source](10-testing/03-workflow-recovery-tests.md#L94)); dependencies: `TEST-03-T06`
389. `OBS-04-T04` — Verify every durable sales workflow ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L59)); dependencies: `OBS-04-T03`, `ARCH-03-T01`, `DB-05-T01`, `ARCH-02-T01`, `BACKEND-01-T04`, `WF-00-T01`, `PROVIDER-01-T02`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`, `WF-06-T05`, `PROVIDER-01-T01`, `TEST-03-T03`, `TEST-03-T04`, `TEST-03-T06`, `TEST-04-T06`, `WF-05-T05`, `WF-01-T03`, `TEST-04-T05`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `BACKEND-01-T08`, `BACKEND-01-T09`, `BACKEND-01-T10`
390. `OBS-04-T05` — Operate attributed deterioration monitoring ([source](09-observability-and-evaluation/04-agent-and-workflow-evaluations.md#L61)); dependencies: `OBS-04-T04`
391. `OBS-05-T03` — Complete all typed incident recovery runbooks ([source](09-observability-and-evaluation/05-incident-response.md#L165)); dependencies: `OBS-05-T02`, `PRODUCT-03-T03`, `SEC-02-T05`, `SEC-03-T04`, `INFRA-02-T04`, `INFRA-04-T05`, `WF-06-T05`
392. `PRODUCT-03-T04` — Exercise integrated operator recovery ([source](00-product-strategy/03-risk-register-and-kill-criteria.md#L130)); dependencies: `PRODUCT-03-T03`, `SEC-05-T04`, `OBS-05-T02`, `OBS-05-T03`
393. `OBS-05-T04` — Wire alerts/contacts/communications ([source](09-observability-and-evaluation/05-incident-response.md#L167)); dependencies: `OBS-05-T03`, `OBS-02-T04`
394. `OBS-05-T05` — Exercise all runbooks ([source](09-observability-and-evaluation/05-incident-response.md#L169)); dependencies: `OBS-05-T04`
395. `OBS-05-T06` — Implement post-incident and re-enable gate ([source](09-observability-and-evaluation/05-incident-response.md#L171)); dependencies: `OBS-05-T05`
396. `TEST-01-T05` — Wire CI/release gates ([source](10-testing/01-testing-strategy.md#L169)); dependencies: `TEST-01-T04`, `TEST-02-T07`, `TEST-05-T04`, `TEST-06-T04`, `TEST-03-T06`, `TEST-04-T06`, `TEST-03-T07`, `TEST-06-T05`
397. `TEST-01-T06` — Operate flake and quarantine policy ([source](10-testing/01-testing-strategy.md#L171)); dependencies: `TEST-01-T05`
398. `INFRA-05-T01` — Implement telemetry and authoritative comparisons ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L98)); dependencies: `OBS-02-T01`, `OBS-01-T03`, `BACKEND-06-T02`
399. `INFRA-05-T02` — Implement exact alert/incident routing ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L100)); dependencies: `INFRA-05-T01`, `OBS-02-T04`, `OBS-05-T01`, `OBS-05-T04`
400. `INFRA-05-T03` — Establish two independent on-call paths ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L102)); dependencies: `INFRA-05-T02`
401. `INFRA-05-T04` — Implement direct Critical signaling and the E2E watchdog ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L104)); dependencies: `INFRA-05-T03`, `OBS-05-T01`
402. `INFRA-05-T05` — Monitor the sole AWS S3 deletion witness ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L106)); dependencies: `INFRA-05-T04`, `INFRA-04-T03`
403. `INFRA-05-T06` — Execute every DR scenario ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L108)); dependencies: `INFRA-05-T05`, `INFRA-02-T04`, `SEC-03-T04`, `INFRA-04-T02`
404. `INFRA-04-T06` — Exercise clean-host recovery every 90 days ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L179)); dependencies: `INFRA-04-T05`, `INFRA-05-T06`
405. `INFRA-04-T07` — Exercise off-Google bootstrap and key rotation ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L181)); dependencies: `INFRA-04-T06`
406. `INFRA-04-T08` — Close backup/restore command ownership ([source](11-infrastructure/04-postgresql-backups-and-restores.md#L183)); dependencies: `INFRA-04-T07`
407. `INFRA-05-T07` — Operate freshness and re-enable gates ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L110)); dependencies: `INFRA-05-T06`, `INFRA-04-T06`
408. `ARCH-01-T06` — Prove private operations ([source](01-architecture/01-target-system-architecture.md#L170)); dependencies: `ARCH-01-T05`, `INFRA-03-T07`, `INFRA-04-T06`, `INFRA-05-T07`, `OBS-05-T03`
409. `INFRA-05-T08` — Close command and DR scenario sets ([source](11-infrastructure/05-monitoring-and-disaster-recovery.md#L112)); dependencies: `INFRA-05-T07`
410. `LAUNCH-02-T01` — Freeze the internal entry and authority-zero target ([source](12-launch-and-operations/02-controlled-internal-launch.md#L80)); dependencies: `LAUNCH-01-T06`, `INFRA-02-T04`, `INFRA-04-T06`, `OBS-02-T05`, `INFRA-05-T07`, `ARCH-01-T05`, `TEST-01-T02`, `TEST-01-T05`, `INFRA-03-T08`
411. `LAUNCH-02-T02` — Promote the private candidate safely ([source](12-launch-and-operations/02-controlled-internal-launch.md#L82)); dependencies: `LAUNCH-02-T01`, `INFRA-02-T02`, `INFRA-04-T02`
412. `LAUNCH-02-T03` — Run bounded synthetic/internal operations ([source](12-launch-and-operations/02-controlled-internal-launch.md#L84)); dependencies: `LAUNCH-02-T02`
413. `LAUNCH-02-T04` — Prove restore, witness, alerts and DR ([source](12-launch-and-operations/02-controlled-internal-launch.md#L86)); dependencies: `LAUNCH-02-T03`, `INFRA-03-T04`, `INFRA-04-T06`, `INFRA-05-T06`, `TEST-06-T04`
414. `LAUNCH-02-T05` — Close rollback and M8 exit ([source](12-launch-and-operations/02-controlled-internal-launch.md#L88)); dependencies: `LAUNCH-02-T04`, `WF-07-T04`, `WF-08-T04`, `WF-09-T04`, `TEST-05-T02`
415. `LAUNCH-05-T01` — Build the reproducible advisory and inventory review ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L129)); dependencies: `INFRA-02-T02`
416. `LAUNCH-05-T02` — Produce pinned immutable candidates ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L131)); dependencies: `LAUNCH-05-T01`
417. `LAUNCH-05-T03` — Run class-specific migrations/evaluations ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L133)); dependencies: `LAUNCH-05-T02`
418. `LAUNCH-05-T04` — Canary, promote and prove rollback/restore ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L135)); dependencies: `LAUNCH-05-T03`, `INFRA-02-T04`, `INFRA-04-T02`
419. `LAUNCH-05-T05` — Operate cadence, EOL and emergency controls ([source](12-launch-and-operations/05-maintenance-and-upgrade-policy.md#L137)); dependencies: `LAUNCH-05-T04`

## M9

420. `SEC-04-T05` — Obtain real-recipient counsel and provider-policy decision ([source](08-security-and-compliance/04-outreach-compliance.md#L105)); dependencies: `SEC-04-T04`, `PRODUCT-01-T02`, `SEC-06-T02`, `SEC-05-T04`
421. `SEC-01-T05` — Review residual risk before every authority increase ([source](08-security-and-compliance/01-threat-model.md#L127)); dependencies: `SEC-01-T04`, `OBS-04-T05`, `INFRA-04-T06`, `LAUNCH-05-T04`
422. `PRODUCT-02-T04` — Pre-register the staged M9 decision ([source](00-product-strategy/02-success-metrics.md#L148)); dependencies: `PRODUCT-02-T03`, `SEC-01-T05`
423. `TEST-05-T05` — Verify scanner-safe public unsubscribe ([source](10-testing/05-end-to-end-browser-tests.md#L56)); dependencies: `TEST-05-T04`, `SEC-04-T04`
424. `TEST-05-T06` — Close browser command mapping ([source](10-testing/05-end-to-end-browser-tests.md#L58)); dependencies: `TEST-05-T05`, `TEST-01-T01`
425. `LAUNCH-03-T01` — Freeze controlled real-campaign entry ([source](12-launch-and-operations/03-first-real-experiment.md#L72)); dependencies: `LAUNCH-02-T05`, `SEC-01-T05`, `TEST-05-T05`, `DB-02-T03`, `BACKEND-05-T05`, `PROVIDER-01-T03`, `SEC-04-T02`, `SEC-05-T03`, `PRODUCT-02-T04`, `SEC-04-T05`
426. `LAUNCH-03-T02` — Publish scanner-safe suppression ingress ([source](12-launch-and-operations/03-first-real-experiment.md#L74)); dependencies: `LAUNCH-03-T01`, `INFRA-03-T06`, `BACKEND-02-T05`, `SEC-04-T04`, `SEC-04-T05`
427. `OBS-01-T07` — Integrate active public-edge correlation ([source](09-observability-and-evaluation/01-structured-events-and-correlation.md#L122)); dependencies: `OBS-01-T06`, `LAUNCH-03-T02`, `SEC-04-T04`
428. `TEST-06-T06` — Prove active public route, WAF, and recipient-stop controls ([source](10-testing/06-load-security-and-chaos-tests.md#L70)); dependencies: `TEST-06-T05`, `LAUNCH-03-T02`, `BACKEND-02-T05`, `SEC-04-T04`, `OBS-01-T07`
429. `SEC-04-T06` — Prove the bounded authority ladder ([source](08-security-and-compliance/04-outreach-compliance.md#L107)); dependencies: `SEC-04-T05`, `TEST-06-T06`, `SEC-05-T04`, `OBS-03-T04`, `TEST-03-T06`
430. `SEC-05-T05` — Prove earned re-enable ([source](08-security-and-compliance/05-suppression-budgets-and-kill-switch.md#L115)); dependencies: `SEC-05-T04`, `SEC-04-T06`, `TEST-03-T06`, `OBS-05-T06`
431. `LAUNCH-03-T03` — Execute bounded current-stage conversations ([source](12-launch-and-operations/03-first-real-experiment.md#L76)); dependencies: `LAUNCH-03-T02`, `SEC-04-T02`, `BACKEND-05-T03`, `BACKEND-03-T04`, `SEC-05-T03`, `SEC-04-T06`, `SEC-05-T05`, `TEST-06-T06`
432. `LAUNCH-03-T04` — Operate booking, recipient stops and exceptions ([source](12-launch-and-operations/03-first-real-experiment.md#L78)); dependencies: `LAUNCH-03-T03`, `INFRA-04-T07`, `INFRA-05-T07`, `BACKEND-01-T08`, `WF-07-T04`
433. `LAUNCH-03-T05` — Close checkpoints and activate eligible learning ([source](12-launch-and-operations/03-first-real-experiment.md#L80)); dependencies: `LAUNCH-03-T04`, `BACKEND-01-T09`, `BACKEND-01-T10`, `WF-08-T04`, `WF-09-T04`
434. `LAUNCH-04-T01` — Freeze bounded autonomy contract ([source](12-launch-and-operations/04-earned-autonomy.md#L66)); dependencies: `AGENT-01-T01`, `PROVIDER-02-T01`, `PROVIDER-03-T01`, `PROVIDER-04-T01`, `PROVIDER-05-T01`, `PROVIDER-06-T01`, `SEC-05-T03`, `WF-02-T05`, `WF-03-T05`, `WF-04-T05`, `PROVIDER-01-T01`
435. `LAUNCH-04-T02` — Calculate evidence and economics without selection bias ([source](12-launch-and-operations/04-earned-autonomy.md#L68)); dependencies: `LAUNCH-04-T01`
436. `LAUNCH-04-T03` — Enable only earned in-envelope execution ([source](12-launch-and-operations/04-earned-autonomy.md#L70)); dependencies: `LAUNCH-04-T02`, `LAUNCH-03-T05`, `AGENT-10-T05`, `LAUNCH-02-T05`, `OBS-04-T05`, `OBS-05-T06`, `INFRA-02-T04`, `BACKEND-01-T08`, `BACKEND-01-T10`, `WF-09-T04`
437. `LAUNCH-04-T04` — Prove permanent authority boundaries ([source](12-launch-and-operations/04-earned-autonomy.md#L72)); dependencies: `LAUNCH-04-T03`
438. `LAUNCH-04-T05` — Operate automatic deterioration and boundary rollback ([source](12-launch-and-operations/04-earned-autonomy.md#L74)); dependencies: `LAUNCH-04-T04`
