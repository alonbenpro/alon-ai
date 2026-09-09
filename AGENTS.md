# Repository Agent Instructions

These instructions apply to the entire checkout.

## Roadmap authority

[Founder OS](https://www.notion.so/3d6caf700cba81a7a26bcb3b258f6ee1) is the sole authority for current roadmap tasks, specifications, dependencies, milestones, and acceptance gates. GitHub is authoritative for implemented code, tests, migrations, schemas, ADRs, runbooks, and retained implementation evidence.

Before starting new roadmap-dependent work, read the current Founder OS task and its specification, dependencies, milestone, and acceptance gate. If Founder OS cannot be accessed, stop and report the blocker. The retained repository roadmap, generated planning artifacts, roadmap validator and its tests, planning history, historical roadmap commits, caches, remembered planning content, and Graphify output are non-authoritative planning references and cannot override Founder OS.

## Graphify-first repository discovery

Use Graphify before broad discovery whenever the task asks how the repository works, where behavior lives, what depends on what, or which files implement an architectural concept.

1. Work from the active checkout root returned by `git rev-parse --show-toplevel`. Never query a graph from another clone or worktree.
2. If `graphify-out/graph.json` exists, run `graphify reflect --if-stale`, read `graphify-out/reflections/LESSONS.md`, expand the question using only tokens present in the graph vocabulary, and run `graphify query` before broad `rg`, directory scans, or opening many files.
3. If the graph is absent, invoke the Graphify workflow on the active checkout root, then query it.
4. After Graphify identifies likely files, symbols, or missing coverage, validate with targeted `rg`, exact file reads, and direct symbol inspection.
5. Save each useful, dead-end, or corrected query with `graphify save-result` and the matching `--outcome`.
6. After tracked code or documentation changes, run the Graphify incremental-update workflow. The installed post-commit hook updates code automatically; documentation changes still require the explicit update.
7. Keep `graphify-out/` local and ignored. Never commit the graph, query memory, lessons, vocabulary, or generated visualizations.

Exact-path edits, focused tests, builds, formatting commands, and Git status/diff checks do not require a graph query because they are not discovery. If Graphify is absent, corrupt, stale, or has no vocabulary for the question, state the exception, use the narrowest targeted fallback, and repair or update the graph before returning to broad discovery.

The exact commands, vocabulary-expansion script, update rules, memory protocol, hook behavior, and failure exceptions are in [docs/engineering/graphify-first-navigation.md](docs/engineering/graphify-first-navigation.md).
