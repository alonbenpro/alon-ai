# Validate an M0 experiment brief

The offline validator supports [PRODUCT-01-T01](https://app.notion.com/p/3d6caf700cba8188a754fa4a742ef838) and the current [Product Scope and Bounded Bet](https://app.notion.com/p/3d6caf700cba8159b94eeabfb489f336) specification in Notion. It checks a declaration, not a runtime policy engine or an accepted milestone.

From the repository root:

```sh
backend/.venv/bin/python scripts/validate_experiment_brief.py --schema
backend/.venv/bin/python scripts/validate_experiment_brief.py /absolute/path/to/brief.json
```

The schema describes required customer/problem/deliverable, jurisdiction, baseline, budget, source, routing, launch, evidence, conversation, booking and decision fields. Currency caps use integer ILS agorot; time caps use integer minutes. A draft may explicitly have a pending operator signature.

Validation produces a canonical content digest for review. A signature record is not authenticated by this program, and a successful exit does not pass M0, unlock M1, establish legal clearance, or enable outreach. The operator must review the exact version and its evidence independently. Missing or invalid fields produce a nonzero exit with diagnostics that omit supplied values.

The test fixture is synthetic and must never be used as Alon's approved experiment. Alon has deferred selecting real experiment bounds while developing the separate user-supplied live-research slice. No actual signed brief is included.

```sh
backend/.venv/bin/python -m pytest backend/tests/unit/test_experiment_brief.py -q
```
