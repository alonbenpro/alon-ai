# Graphify-First Repository Navigation

**Status:** Required engineering workflow
**Audience:** Repository agents and maintainers
**Source of authority:** Root [`AGENTS.md`](../../AGENTS.md)

## Why this exists

Graphify is the repository map; source and versioned documentation remain the authority. Querying the graph first narrows discovery to likely files, symbols, paths, and known gaps. Targeted reads then verify the result. This prevents repeated whole-repository scans without allowing a stale graph to overrule source.

`graphify-out/` is ignored local state. It contains the graph, report, lessons, query memory, vocabulary, and visualizations. None of it belongs in a commit.

## 1. Bootstrap from the active checkout

Always establish and enter the active checkout root:

```sh
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
```

Do not use a graph located in another clone, parent repository, sibling worktree, or previously active checkout. Confirm the graph belongs to the current root:

```sh
test -f graphify-out/.graphify_root && cat graphify-out/.graphify_root
git rev-parse --show-toplevel
```

The resolved paths must identify the same checkout. If `graphify-out/graph.json` is absent, invoke the installed Graphify skill/workflow on `.` from this root. In clients that expose slash commands, the request is:

```text
/graphify .
```

Do not replace the workflow with a blind recursive search. When only the CLI is available, `graphify extract .` is the headless full-extraction entry point; follow Graphify's backend and corpus warnings rather than claiming an incomplete extraction is current.

## 2. Reflect before every graph-assisted task

Refresh deterministic work-memory lessons, then read them:

```sh
graphify reflect --if-stale
sed -n '1,240p' graphify-out/reflections/LESSONS.md
```

Preferred sources are starting points, not proof. Skip known dead ends unless relevant files changed. Apply recorded corrections, then verify them against the current source.

## 3. Expand the question using graph vocabulary

Graphify matches literal label tokens; it does not stem words or invent synonyms. Build the vocabulary from the active graph:

```sh
graphify_python="$(cat graphify-out/.graphify_python)"
"$graphify_python" -c '
import json, re
from pathlib import Path

data = json.loads(Path("graphify-out/graph.json").read_text(encoding="utf-8"))
vocab = set()
for node in data["nodes"]:
    for chunk in re.findall(r"[^\W\d_]+", node.get("label", "") or "", re.UNICODE):
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+", chunk) or [chunk]
        for part in parts:
            token = part.lower()
            if 3 <= len(token) <= 30:
                vocab.add(token)
Path("graphify-out/.vocab.txt").write_text("\n".join(sorted(vocab)), encoding="utf-8")
print(f"vocab: {len(vocab)} tokens")
'
```

Read `graphify-out/.vocab.txt` and select at most 12 tokens that match the question. Every selected token must appear verbatim in that file. Omit concepts with no plausible token. If no token matches, record that the graph has no relevant vocabulary and use the exception path below; do not fabricate an expanded query.

Before traversal, make the expansion auditable:

```text
Query expanded to (from graph vocab, N tokens): [token1, token2, ...]
```

## 4. Query before broad search

Use breadth-first traversal for broad ownership and neighborhood questions:

```sh
graphify query "token1 token2 token3" --budget 3000
```

Use depth-first traversal for a specific dependency or data-flow chain:

```sh
graphify query "token1 token2 token3" --dfs --budget 3000
```

Answer only from nodes and edges returned by the graph at this stage. Cite `source_location` when relying on a specific fact. Treat `AMBIGUOUS` edges as leads to verify, never as facts. If output is truncated, narrow the tokens/context or increase the budget deliberately.

## 5. Validate with targeted source inspection

After Graphify names likely locations, inspect only those locations first:

```sh
rg -n "ExactSymbol|exact_event_name" path/selected/by/graph
sed -n 'START,ENDp' path/selected/by/graph/file.ext
```

Expand outward only when the selected location is stale, missing, or explicitly points to another owner. Source, tests, lockfiles, migrations, ADRs, and approved specifications overrule stale graph statements. Record the discrepancy as a corrected/dead-end memory and update the graph.

## 6. Save work memory

Save the original question, verified answer, cited node labels, vocabulary expansion, and outcome:

```sh
graphify save-result \
  --question "ORIGINAL QUESTION" \
  --answer "Expanded via graph vocab: [token1, token2]. VERIFIED ANSWER" \
  --type query \
  --nodes "Node One" "Node Two" \
  --outcome useful
```

Use `--outcome dead_end` when the traversal did not help. Use `--outcome corrected --correction "VERIFIED CORRECTION"` when source contradicts the saved/graph answer. Do not mark a result useful merely because the command ran.

## 7. Update after tracked changes

After tracked code or documentation changes, run the Graphify incremental-update workflow from the active root:

```text
/graphify . --update
```

This workflow detects changed/deleted files, re-extracts the applicable code and semantic documentation, replaces stale nodes, saves the new manifest, runs graph health checks, and keeps generated output in `graphify-out/`.

The raw command below updates code structurally but does not semantically re-extract changed documentation, so it is not sufficient after Markdown or other documentation changes:

```sh
graphify update .
```

If the Graphify client exposes the skill as `$graphify` rather than a slash command, invoke that skill with `. --update`. If semantic extraction is unavailable, report the graph as stale for changed documents and do not claim the update passed.

After an update, rerun the vocabulary expansion/query when the answer may have changed. Never use `--force` merely to silence the graph shrink guard; investigate deletions/refactors first.

## 8. Post-commit hook

The current clone has the local hook installed. Verify it with:

```sh
graphify hook status
```

Install or repair it only when authorized:

```sh
graphify hook install
```

The post-commit hook updates changed code using deterministic AST extraction and refreshes lessons when query memory exists. It runs in the common Git directory and deliberately skips linked worktrees, rebases, merges, and cherry-picks. It ignores documentation/image semantic extraction, so documentation commits still require the explicit incremental workflow in section 7. Inspect hook failures in the path printed by the hook (normally `~/.cache/graphify-rebuild.log`).

## 9. Exceptions and failure handling

Graphify-first does not mean Graphify-only.

| Condition | Required behavior |
| --- | --- |
| exact file path, test, build, formatter, or Git status/diff was requested | run it directly; no discovery query is needed |
| graph is absent | invoke the full Graphify workflow on the active root, then query |
| graph belongs to another checkout | stop, change to the active root, build/query its graph |
| lessons/vocabulary cannot refresh | disclose the failure, read the last retained lessons/vocabulary if present, and use narrow targeted inspection |
| no graph vocabulary matches | say so, use the narrowest `rg`/exact-file fallback, then update/save a dead-end or corrected outcome |
| query points to stale/missing source | trust current source, save a corrected outcome, run incremental update |
| graph health warns of dangling/missing/collapsed edges | disclose reduced confidence and verify every relied-on edge directly |
| changed documentation cannot be semantically updated | mark the graph stale for those docs; do not claim Graphify freshness |
| urgent safety incident | execute the exact kill/revocation/runbook action first, then use Graphify for diagnosis |

Broad repository search is the fallback of last resort, not the opening move. A Graphify failure never justifies guessing about architecture.

## 10. Session checklist

- [ ] Active checkout root confirmed; no sibling-worktree graph used.
- [ ] `graphify reflect --if-stale` run and lessons read.
- [ ] Question expanded using only current graph vocabulary.
- [ ] BFS/DFS query run before broad discovery.
- [ ] Graph-selected facts verified with targeted source/test/doc reads.
- [ ] Query memory saved with an honest outcome.
- [ ] Incremental update run after tracked changes; documentation freshness stated truthfully.
- [ ] `graphify-out/` remains ignored and absent from the commit.
