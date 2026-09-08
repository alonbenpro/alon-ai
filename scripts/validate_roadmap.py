"""Pure parsing and source-contract validation for roadmap tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import pairwise
from pathlib import Path

_PATH = re.compile(r"(?:[0-9]{2}-[a-z0-9-]+/)+[0-9]{2}-[a-z0-9-]+\.md")
ROOT_TASK_IDS = frozenset({"PRODUCT-01-T01"})
LOCKS = frozenset(
    {
        "roadmap-root",
        "product-contracts",
        "architecture-contracts",
        "database-schema",
        "migration-head",
        "workflow-runtime",
        "agent-runtime",
        "agent-artifacts",
        "provider-contracts",
        "gmail-side-effects",
        "backend-domain",
        "openapi-contract",
        "frontend-client",
        "security-runtime",
        "compliance-policy",
        "telemetry-catalog",
        "test-command-registry",
        "dependency-lockfiles",
        "compose-topology",
        "ci-release",
        "backup-restore",
        "live-environment",
        "milestone-gate",
    }
)
SERIAL_ONLY_LOCKS = frozenset(
    {
        "migration-head",
        "gmail-side-effects",
        "security-runtime",
        "openapi-contract",
        "frontend-client",
        "test-command-registry",
        "dependency-lockfiles",
        "compose-topology",
        "ci-release",
        "backup-restore",
        "live-environment",
        "milestone-gate",
    }
)
ARTIFACT_PATHS = (
    "docs/development-roadmap/execution-manifest.json",
    "docs/development-roadmap/EXECUTION_ORDER.md",
    "docs/development-roadmap/AGENT_EXECUTION_PLAN.md",
)
MILESTONES = tuple(f"M{number}" for number in range(10))
_MILESTONES = frozenset(MILESTONES)
_DOCUMENT_ID = re.compile(r"[A-Z][A-Z0-9]*-[0-9]{2}")
_TASK_ID = re.compile(r"(?P<prefix>[A-Z][A-Z0-9]*-[0-9]{2})-T[0-9]{2}")
_MARKERS = ("Input:", "Operation:", "Output:", "Test evidence:", "Failure behavior:")
_METADATA = re.compile(
    r"<!-- roadmap-task id=(.*?) milestone=(.*?) depends_on=(.*?) "
    r"mode=(.*?) locks=(.*?) -->"
)


class ValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    source: str
    line: int
    task_id: str | None = None

    def error(self, message: str) -> ValidationError:
        context = f"{self.task_id}: " if self.task_id else ""
        return ValidationError(f"{self.source}:{self.line}: {context}{message}")


@dataclass(frozen=True, slots=True)
class ManifestDocument:
    source: str
    milestone: str


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    milestone: str
    document_id: str
    title: str
    body: str
    source: str
    line: int
    depends_on: tuple[str, ...]
    mode: str
    locks: tuple[str, ...]
    input: str
    operation: str
    output: str
    verification: str
    failure_behavior: str
    acceptance_commands: tuple[str, ...]

    @property
    def location(self) -> SourceLocation:
        return SourceLocation(self.source, self.line, self.id)


@dataclass(frozen=True, slots=True)
class Roadmap:
    documents: tuple[ManifestDocument, ...]
    tasks: tuple[Task, ...]


@dataclass(frozen=True, slots=True)
class WaveAssignment:
    task: Task
    implementer: str
    reviewer: str
    merge_order: int


@dataclass(frozen=True, slots=True)
class Wave:
    index: int
    milestone: str
    assignments: tuple[WaveAssignment, ...]
    newly_unlocked: tuple[str, ...]


def _logical_cells(line: str) -> list[str]:
    stripped = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in stripped.split("|")]


def _candidate_cells(line: str) -> list[str]:
    cells = _logical_cells(line)
    while cells and not cells[0]:
        cells.pop(0)
    while cells and not cells[-1]:
        cells.pop()
    return cells


def _manifest_like(line: str) -> bool:
    cells = _candidate_cells(line)
    if len(cells) < 2:
        return False
    first, second = cells[:2]
    return _path_shaped(first) and len(second) > 1 and second.startswith("M")


def _path_shaped(cell: str) -> bool:
    return "/" in cell or (cell.startswith("`") and cell.endswith("`"))


def _ordered_bounds(lines: list[str]) -> tuple[int, int]:
    heading = "## Ordered implementation tasks"
    matches = [index for index, line in enumerate(lines) if line == heading]
    if len(matches) != 1:
        raise ValidationError("ordered section must be unique")
    start = matches[0] + 1
    ends = [
        index for index in range(start, len(lines)) if lines[index].startswith("## ")
    ]
    if not ends:
        raise ValidationError("ordered section must have boundary")
    return start, ends[0]


def parse_dependency_list(value: str) -> tuple[str, ...]:
    return () if value == "-" else tuple(value.split(","))


def _make_task(
    metadata_line: str,
    body: str,
    document_id: str,
    source: str,
    line: int,
) -> Task:
    metadata = _METADATA.fullmatch(metadata_line)
    if metadata is None:
        raise ValidationError("malformed task metadata")
    title = re.match(r"^\*\*(.+?) —\*\*\s+", body)
    if title is None:
        raise ValidationError("invalid task title")
    positions = [body.index(marker) for marker in _MARKERS]
    clauses = tuple(
        body[positions[index] : positions[index + 1]].strip()
        if index < 4
        else body[positions[index] :].strip()
        for index in range(5)
    )
    raw_dependencies = metadata.group(3)
    return Task(
        id=metadata.group(1),
        milestone=metadata.group(2),
        document_id=document_id,
        title=title.group(1),
        body=body,
        source=source,
        line=line,
        depends_on=parse_dependency_list(raw_dependencies),
        mode=metadata.group(4),
        locks=tuple(metadata.group(5).split(",")),
        input=clauses[0],
        operation=clauses[1],
        output=clauses[2],
        verification=clauses[3],
        failure_behavior=clauses[4],
        acceptance_commands=_commands(clauses[3]),
    )


def _commands(verification: str) -> tuple[str, ...]:
    code_ranges = [
        (match.start(), match.end())
        for match in re.finditer(r"`[^`\n]*`", verification)
    ]

    def outside(pattern: str) -> list[re.Match[str]]:
        return [
            match
            for match in re.finditer(pattern, verification)
            if not any(start < match.start() < end for start, end in code_ranges)
        ]

    plural_markers = outside(r"\bCommands:")
    singular_markers = outside(r"\bCommand:")
    if len(plural_markers) + len(singular_markers) > 1:
        raise ValidationError("multiple command markers")
    plural = plural_markers[0] if plural_markers else None
    if plural is not None:
        tail = verification[plural.end() :].lstrip()
        spans = list(re.finditer(r"`([^`\n]*)`", tail))
        if (
            not spans
            or spans[0].start() != 0
            or any(not span.group(1) for span in spans)
        ):
            raise ValidationError("plural Commands require nonempty spans")
        for previous, current in pairwise(spans):
            if tail[previous.end() : current.start()].strip() != ",":
                raise ValidationError("plural Commands require comma separators")
        return tuple(span.group(1) for span in spans)
    marker = singular_markers[0] if singular_markers else None
    if marker is None:
        return ()
    tail = verification[marker.end() :].lstrip()
    span = re.match(r"`([^`\n]+)`", tail)
    if span is None or re.search(r"`[^`\n]*`", tail[span.end() :]):
        raise ValidationError("singular Command requires exactly one nonempty span")
    return (span.group(1),)


def parse_manifest(root: Path) -> tuple[ManifestDocument, ...]:
    lines = (
        (root / "docs/development-roadmap/README.md")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    heading = "## Complete file manifest mapped to vertical gates"
    found = [index for index, line in enumerate(lines) if line == heading]
    if len(found) != 1:
        raise ValidationError("manifest heading must be unique")
    start = found[0] + 1
    boundaries = [
        index for index in range(start, len(lines)) if lines[index].startswith("## ")
    ]
    if not boundaries:
        raise ValidationError("manifest requires closing boundary")
    end = boundaries[0]
    for index, line in enumerate(lines):
        if not (start <= index < end) and _manifest_like(line):
            raise ValidationError("manifest-like row outside manifest section")
    for line in lines[start:end]:
        cells = _logical_cells(line)
        candidate_cells = _candidate_cells(line)
        if candidate_cells and _path_shaped(candidate_cells[0]):
            if (cells and not cells[0]) or (len(cells) > 2 and not cells[-1]):
                raise ValidationError("manifest data row has invalid outer delimiters")
            if len(cells) < 2:
                raise ValidationError("manifest data row requires path and milestone")
    documents: list[ManifestDocument] = []
    seen_paths: set[str] = set()
    for line in lines[start:end]:
        cells = _logical_cells(line)
        if not cells or not _path_shaped(cells[0]):
            continue
        path_cell, milestone = cells[:2]
        if (
            len(path_cell) < 2
            or not path_cell.startswith("`")
            or not path_cell.endswith("`")
            or _PATH.fullmatch(path_cell[1:-1]) is None
        ):
            raise ValidationError("invalid manifest path")
        if milestone not in _MILESTONES:
            raise ValidationError("invalid manifest milestone")
        relative_path = path_cell[1:-1]
        if relative_path in seen_paths:
            raise ValidationError("duplicate manifest path")
        seen_paths.add(relative_path)
        roadmap_root = root / "docs/development-roadmap"
        document_path = roadmap_root / relative_path
        try:
            document_path.resolve().relative_to(roadmap_root.resolve())
        except ValueError as error:
            raise ValidationError(
                "manifest path resolves outside roadmap root"
            ) from error
        if not document_path.is_file():
            raise ValidationError("missing manifest document")
        documents.append(
            ManifestDocument(f"docs/development-roadmap/{relative_path}", milestone)
        )
    roadmap_root = root / "docs/development-roadmap"
    eligible_paths: set[str] = set()
    for document_path in sorted(roadmap_root.rglob("*.md")):
        relative = document_path.relative_to(roadmap_root)
        if (
            len(relative.parts) < 2
            or re.fullmatch(r"[0-9]{2}-[a-z0-9-]+", relative.parts[0]) is None
        ):
            continue
        if (
            "## Ordered implementation tasks"
            in document_path.read_text(encoding="utf-8").splitlines()
        ):
            eligible_paths.add(relative.as_posix())
    missing = sorted(eligible_paths - seen_paths)
    extra = sorted(seen_paths - eligible_paths)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing manifest paths: {', '.join(missing)}")
        if extra:
            details.append(
                "extra manifest paths (ordered section missing): " + ", ".join(extra)
            )
        raise SourceLocation("docs/development-roadmap/README.md", found[0] + 1).error(
            "; ".join(details)
        )
    return tuple(documents)


def _line_location(source: str, lines: list[str], index: int) -> SourceLocation:
    metadata = lines[index] if lines else ""
    if not metadata.startswith("<!-- roadmap-task") and index > 0:
        metadata = lines[index - 1]
    match = (
        re.search(r"\s+id=([^\s]+)", metadata)
        if metadata.startswith("<!-- roadmap-task")
        else None
    )
    return SourceLocation(source, index + 1, match.group(1) if match else None)


def parse_roadmap(root: Path) -> Roadmap:
    documents = parse_manifest(root)
    tasks: list[Task] = []
    seen_document_ids: set[str] = set()
    for document in documents:
        source = (root / document.source).read_text(encoding="utf-8")
        source_lines = source.splitlines()
        id_indices = [
            index
            for index, line in enumerate(source_lines)
            if line.startswith("**Document ID:**")
        ]
        id_lines = [
            source_lines[index].removeprefix("**Document ID:** ")
            for index in id_indices
        ]
        id_location = SourceLocation(
            document.source, id_indices[0] + 1 if id_indices else 1
        )
        if len(id_lines) != 1 or _DOCUMENT_ID.fullmatch(id_lines[0]) is None:
            raise id_location.error("invalid document ID syntax/cardinality")
        if id_lines[0] in seen_document_ids:
            raise id_location.error("duplicate document ID")
        seen_document_ids.add(id_lines[0])
        try:
            start, end = _ordered_bounds(source_lines)
        except ValidationError as error:
            heading_index = next(
                (
                    index
                    for index, line in enumerate(source_lines)
                    if line == "## Ordered implementation tasks"
                ),
                0,
            )
            raise SourceLocation(document.source, heading_index + 1).error(
                str(error)
            ) from error
        for index in range(start, end):
            if re.match(r"^- \[[xX]\](?: |$)", source_lines[index]):
                raise _line_location(document.source, source_lines, index).error(
                    "ordered task must be unchecked"
                )
        checkbox_lines = [
            index
            for index in range(start, end)
            if re.match(r"^- \[ \](?: |$)", source_lines[index])
        ]
        for index in checkbox_lines:
            if index == start or not source_lines[index - 1].startswith(
                "<!-- roadmap-task "
            ):
                raise _line_location(document.source, source_lines, index).error(
                    "unchecked box requires adjacent metadata"
                )
        for index, line in enumerate(source_lines):
            if not line.startswith("<!-- roadmap-task"):
                continue
            location = _line_location(document.source, source_lines, index)
            if not (start <= index < end):
                raise location.error("orphan metadata outside ordered section")
            if index + 1 < end and source_lines[index + 1].startswith(
                "<!-- roadmap-task"
            ):
                raise location.error("duplicate metadata")
            if index + 1 >= end or not source_lines[index + 1].startswith("- [ ] "):
                raise location.error("orphan metadata")
        for index in checkbox_lines:
            if _METADATA.fullmatch(source_lines[index - 1]) is None:
                raise _line_location(document.source, source_lines, index - 1).error(
                    "malformed task metadata"
                )
            try:
                body = source_lines[index][len("- [ ]") :].removeprefix(" ")
                title_match = re.match(r"^\*\*(.+?) —\*\*\s+", body)
                if title_match is None:
                    raise ValidationError("invalid task title")
                if any(marker not in body for marker in _MARKERS):
                    raise ValidationError("missing task clause marker")
                if any(body.count(marker) > 1 for marker in _MARKERS):
                    raise ValidationError("duplicate task clause marker")
                positions = [body.index(marker) for marker in _MARKERS]
                if positions != sorted(positions):
                    raise ValidationError("invalid task clause order")
                if title_match.end() != positions[0]:
                    raise ValidationError("invalid task title boundary")
                tasks.append(
                    _make_task(
                        source_lines[index - 1],
                        body,
                        id_lines[0],
                        document.source,
                        index + 1,
                    )
                )
            except ValidationError as error:
                raise _line_location(document.source, source_lines, index).error(
                    str(error)
                ) from error
    for task in tasks:
        match = _TASK_ID.fullmatch(task.id)
        if match is None:
            raise task.location.error("invalid task ID syntax")
        if match.group("prefix") != task.document_id:
            raise task.location.error("task ID prefix does not match document ID")
    seen_task_ids: set[str] = set()
    for task in tasks:
        if task.id in seen_task_ids:
            raise task.location.error("duplicate task ID")
        seen_task_ids.add(task.id)
    counters: dict[str, int] = {}
    for task in tasks:
        counters[task.document_id] = counters.get(task.document_id, 0) + 1
        expected = f"{task.document_id}-T{counters[task.document_id]:02d}"
        if task.id != expected:
            raise task.location.error(f"non-contiguous task ID; expected {expected}")
    for task in tasks:
        if task.milestone not in _MILESTONES:
            raise task.location.error("invalid task milestone")
    previous_milestone: dict[str, int] = {}
    for task in tasks:
        value = int(task.milestone[1:])
        if value < previous_milestone.get(task.document_id, -1):
            raise task.location.error("task milestones decrease within document")
        previous_milestone[task.document_id] = value
    for task in tasks:
        if task.id in ROOT_TASK_IDS and task.depends_on:
            raise task.location.error("root allowlist task must use depends_on=-")
        if task.id not in ROOT_TASK_IDS and not task.depends_on:
            raise task.location.error("root allowlist rejects extra root")
    if not ROOT_TASK_IDS.issubset({task.id for task in tasks}):
        raise SourceLocation("docs/development-roadmap/README.md", 1).error(
            "root allowlist task is missing"
        )
    for task in tasks:
        for dependency in task.depends_on:
            if not dependency or _TASK_ID.fullmatch(dependency) is None:
                raise task.location.error("invalid dependency token")
        if len(task.depends_on) != len(set(task.depends_on)):
            raise task.location.error("duplicate dependency")
    known_ids = {task.id for task in tasks}
    tasks_by_id = {task.id: task for task in tasks}
    for task in tasks:
        if task.id in task.depends_on:
            raise task.location.error("self dependency")
        if any(dependency not in known_ids for dependency in task.depends_on):
            raise task.location.error("unknown dependency")
        if any(
            int(tasks_by_id[dependency].milestone[1:]) > int(task.milestone[1:])
            for dependency in task.depends_on
        ):
            raise task.location.error("dependency points to future milestone")
    for task in tasks:
        if task.mode not in {"parallel", "serial"}:
            raise task.location.error("invalid execution mode")
        if not task.locks or any(not lock for lock in task.locks):
            raise task.location.error("task requires nonempty lock list")
        if any(lock not in LOCKS for lock in task.locks):
            raise task.location.error("unknown lock")
        if len(task.locks) != len(set(task.locks)):
            raise task.location.error("duplicate lock")
        if task.mode != "serial" and any(
            lock in SERIAL_ONLY_LOCKS for lock in task.locks
        ):
            raise task.location.error("serial-only lock requires serial mode")
    return Roadmap(documents=documents, tasks=tuple(tasks))


def _task_key(roadmap: Roadmap, task: Task) -> tuple[int, int, int, str]:
    document_order = {
        document.source: index for index, document in enumerate(roadmap.documents)
    }
    return (
        int(task.milestone[1:]),
        document_order[task.source],
        int(task.id.rsplit("T", 1)[1]),
        task.id,
    )


def _cycle_path(roadmap: Roadmap, remaining: set[str]) -> tuple[str, ...]:
    tasks = {task.id: task for task in roadmap.tasks}
    state: dict[str, int] = {}
    stack: list[str] = []
    positions: dict[str, int] = {}

    def visit(task_id: str) -> tuple[str, ...] | None:
        state[task_id] = 1
        positions[task_id] = len(stack)
        stack.append(task_id)
        dependencies = sorted(
            (
                dependency
                for dependency in tasks[task_id].depends_on
                if dependency in remaining
            ),
            key=lambda dependency: _task_key(roadmap, tasks[dependency]),
        )
        for dependency in dependencies:
            if state.get(dependency, 0) == 0:
                cycle = visit(dependency)
                if cycle is not None:
                    return cycle
            elif state[dependency] == 1:
                return tuple(stack[positions[dependency] :]) + (dependency,)
        stack.pop()
        positions.pop(task_id)
        state[task_id] = 2
        return None

    for task_id in sorted(
        remaining, key=lambda candidate: _task_key(roadmap, tasks[candidate])
    ):
        if state.get(task_id, 0) == 0:
            cycle = visit(task_id)
            if cycle is not None:
                return cycle
    raise AssertionError("remaining graph must contain a cycle")


def topological_order(roadmap: Roadmap) -> tuple[Task, ...]:
    """Return the graph's stable dependency order or a concrete cycle diagnostic."""
    tasks = {task.id: task for task in roadmap.tasks}
    indegree = {task.id: len(task.depends_on) for task in roadmap.tasks}
    consumers: dict[str, list[str]] = {task.id: [] for task in roadmap.tasks}
    for task in roadmap.tasks:
        for dependency in task.depends_on:
            consumers[dependency].append(task.id)
    ready: list[tuple[tuple[int, int, int, str], str]] = []
    for task in roadmap.tasks:
        if indegree[task.id] == 0:
            heappush(ready, (_task_key(roadmap, task), task.id))
    ordered: list[Task] = []
    while ready:
        _, task_id = heappop(ready)
        ordered.append(tasks[task_id])
        for consumer in consumers[task_id]:
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                heappush(ready, (_task_key(roadmap, tasks[consumer]), consumer))
    if len(ordered) != len(roadmap.tasks):
        remaining = {task_id for task_id, degree in indegree.items() if degree > 0}
        cycle = _cycle_path(roadmap, remaining)
        raise tasks[cycle[0]].location.error(f"dependency cycle: {' -> '.join(cycle)}")
    return tuple(ordered)


def build_waves(roadmap: Roadmap) -> tuple[Wave, ...]:
    """Build the exact conservative milestone-by-milestone wave schedule."""
    ordered = topological_order(roadmap)
    position = {task.id: index for index, task in enumerate(ordered)}
    completed: set[str] = set()
    waves: list[Wave] = []
    while len(completed) < len(ordered):
        unfinished = [task for task in ordered if task.id not in completed]
        milestone_number = min(int(task.milestone[1:]) for task in unfinished)
        milestone = f"M{milestone_number}"
        ready_before = [
            task
            for task in unfinished
            if task.milestone == milestone and set(task.depends_on) <= completed
        ]
        if not ready_before:
            raise ValidationError(f"no ready task in unfinished milestone {milestone}")
        first = ready_before[0]
        if first.mode == "serial":
            selected = [first]
        else:
            selected = []
            selected_locks: set[str] = set()
            for candidate in ready_before:
                if candidate.mode != "parallel":
                    continue
                if selected_locks.isdisjoint(candidate.locks):
                    selected.append(candidate)
                    selected_locks.update(candidate.locks)
                if len(selected) == 4:
                    break
        before_ids = {task.id for task in ready_before}
        completed.update(task.id for task in selected)
        newly_unlocked = tuple(
            task.id
            for task in ordered
            if task.id not in completed
            and task.id not in before_ids
            and set(task.depends_on) <= completed
        )
        assignments = tuple(
            WaveAssignment(
                task=task,
                implementer=f"I{index}",
                reviewer=f"R{index}",
                merge_order=index,
            )
            for index, task in enumerate(selected, start=1)
        )
        waves.append(
            Wave(
                index=len(waves) + 1,
                milestone=milestone,
                assignments=assignments,
                newly_unlocked=tuple(
                    sorted(newly_unlocked, key=lambda task_id: position[task_id])
                ),
            )
        )
    return tuple(waves)


def validate_waves(roadmap: Roadmap, waves: tuple[Wave, ...]) -> None:
    """Validate a supplied plan against the deterministic wave contract."""
    planned_ids = [
        assignment.task.id for wave in waves for assignment in wave.assignments
    ]
    expected_ids = {task.id for task in roadmap.tasks}
    if len(planned_ids) != len(set(planned_ids)):
        raise ValidationError("duplicate task in wave plan")
    if expected_ids - set(planned_ids):
        raise ValidationError("missing task in wave plan")
    if set(planned_ids) - expected_ids:
        raise ValidationError("unknown task in wave plan")
    tasks_by_id = {task.id: task for task in roadmap.tasks}
    completed: set[str] = set()
    for wave in waves:
        if len(wave.assignments) > 4:
            raise ValidationError("wave permits at most four implementers")
        for position, assignment in enumerate(wave.assignments, start=1):
            if (
                assignment.implementer != f"I{position}"
                or assignment.reviewer != f"R{position}"
            ):
                raise ValidationError("agent assignment drift")
            if assignment.merge_order != position:
                raise ValidationError("merge-order drift")
        if len(wave.assignments) > 1 and any(
            assignment.task.mode == "serial" for assignment in wave.assignments
        ):
            raise ValidationError("serial task must be alone in wave")
        if any(
            assignment.task.milestone != wave.milestone
            for assignment in wave.assignments
        ):
            raise ValidationError("milestone crossing")
        unfinished = expected_ids - completed
        expected_milestone = min(
            int(tasks_by_id[task_id].milestone[1:]) for task_id in unfinished
        )
        if wave.milestone != f"M{expected_milestone}":
            raise ValidationError("milestone skipping")
        current = {assignment.task.id for assignment in wave.assignments}
        seen_locks: set[str] = set()
        for assignment in wave.assignments:
            overlap = seen_locks.intersection(assignment.task.locks)
            if overlap:
                raise ValidationError("shared lock in wave")
            seen_locks.update(assignment.task.locks)
        if any(
            dependency in current
            for assignment in wave.assignments
            for dependency in assignment.task.depends_on
        ):
            raise ValidationError("current-wave dependency")
        if any(
            dependency not in completed
            for assignment in wave.assignments
            for dependency in assignment.task.depends_on
        ):
            raise ValidationError("task requires dependency from an earlier wave")
        completed.update(current)
    if waves != build_waves(roadmap):
        raise ValidationError("wave plan drifts from deterministic schedule")


def canonical_fingerprint_bytes(roadmap: Roadmap) -> bytes:
    """Serialize the complete source graph contract into canonical JSON bytes."""
    payload = {
        "schema_version": 1,
        "milestones": list(MILESTONES),
        "root_task_ids": sorted(ROOT_TASK_IDS),
        "manifest_documents": [document.source for document in roadmap.documents],
        "tasks": [
            {
                "id": task.id,
                "milestone": task.milestone,
                "document_id": task.document_id,
                "title": task.title,
                "source": task.source,
                "line": task.line,
                "depends_on": list(task.depends_on),
                "mode": task.mode,
                "locks": list(task.locks),
                "input": task.input,
                "operation": task.operation,
                "output": task.output,
                "verification": task.verification,
                "failure_behavior": task.failure_behavior,
            }
            for task in topological_order(roadmap)
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def graph_fingerprint(roadmap: Roadmap) -> str:
    return hashlib.sha256(canonical_fingerprint_bytes(roadmap)).hexdigest()


def _manifest_task(task: Task) -> dict[str, object]:
    return {
        "id": task.id,
        "milestone": task.milestone,
        "document_id": task.document_id,
        "title": task.title,
        "source": task.source,
        "line": task.line,
        "depends_on": list(task.depends_on),
        "mode": task.mode,
        "locks": list(task.locks),
    }


def _source_link(task: Task) -> str:
    prefix = "docs/development-roadmap/"
    if not task.source.startswith(prefix):
        raise ValidationError(
            f"generated source path is outside roadmap: {task.source}"
        )
    return f"{task.source.removeprefix(prefix)}#L{task.line}"


def render_execution_manifest(roadmap: Roadmap) -> str:
    payload = {
        "schema_version": 1,
        "milestones": list(MILESTONES),
        "tasks": [_manifest_task(task) for task in topological_order(roadmap)],
    }
    return (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        )
        + "\n"
    )


def render_execution_order(roadmap: Roadmap) -> str:
    ordered = topological_order(roadmap)
    lines = [
        "# Executable Roadmap Order",
        "",
        "> Warning: generated; it does not prove implementation status. Edit source task metadata, never this file.",
        "",
        "- Regenerate: `python3 scripts/validate_roadmap.py --write`",
        "- Validate: `python3 scripts/validate_roadmap.py --check`",
        f"- Source-graph fingerprint: `{graph_fingerprint(roadmap)}`",
        "",
        "## Totals",
        "",
        f"- Tasks: {len(ordered)}",
        f"- Documents: {len(roadmap.documents)}",
    ]
    for milestone in MILESTONES:
        count = sum(task.milestone == milestone for task in ordered)
        lines.append(f"- {milestone}: {count}")
    lines.extend(["- By document:"])
    for document in roadmap.documents:
        document_tasks = [task for task in ordered if task.source == document.source]
        if document_tasks:
            lines.append(
                f"  - `{document_tasks[0].document_id}`: {len(document_tasks)}"
            )
    lines.extend(
        [
            "",
            "## Frontier rule",
            "",
            "A task is executable only when every dependency has retained passing evidence from an earlier completed wave.",
        ]
    )
    global_position = {task.id: index for index, task in enumerate(ordered, start=1)}
    for milestone in MILESTONES:
        lines.extend(["", f"## {milestone}", ""])
        milestone_tasks = [task for task in ordered if task.milestone == milestone]
        if not milestone_tasks:
            lines.append("No tasks.")
            continue
        for task in milestone_tasks:
            dependencies = ", ".join(f"`{item}`" for item in task.depends_on) or "none"
            lines.append(
                f"{global_position[task.id]}. `{task.id}` — {task.title} "
                f"([source]({_source_link(task)})); dependencies: {dependencies}"
            )
    return "\n".join(lines) + "\n"


def render_agent_plan(roadmap: Roadmap) -> str:
    waves = build_waves(roadmap)
    validate_waves(roadmap, waves)
    ordered = topological_order(roadmap)
    task_by_id = {task.id: task for task in ordered}
    lines = [
        "# Agent Execution Plan",
        "",
        "> Warning: generated for the source graph below; it does not prove implementation status.",
        "",
        f"- Source-graph fingerprint: `{graph_fingerprint(roadmap)}`",
        "- Regenerate: `python3 scripts/validate_roadmap.py --write`",
        "- Validate: `python3 scripts/validate_roadmap.py --check`",
        "",
        "## Operating contract",
        "",
        "- C0 owns integration, dependency evidence, wave assignment, merge order, status, and milestone gates.",
        "- Implementers are I1..I4; read-only reviewers are R1..R4.",
        "- The absolute live-agent ceiling is nine and the implementation/worktree ceiling is four.",
        "- Each task uses its listed `agent/<task-id>` branch and sibling `../alon-ai-task-<task-id>` worktree from the exact wave-base integration commit.",
        "- Prompts include only the assigned task, dependency evidence, declared locks/surfaces, source acceptance evidence, optional marked commands, base commit, and report path.",
        "- Implementers may not start dependent tasks, edit the integration checkout, merge, push, widen declared locks, or spawn implementation agents.",
        "- Generic or unmarked code spans in task evidence are evidence-only; only grammar-valid explicit `Command:` or `Commands:` spans become optional acceptance commands.",
        "- C0 may add normal repository verification required by declared locks, but may not substitute, broaden, or fabricate evidence commands.",
        "- Each reviewer checks only its completed task before C0 merges branches one at a time in generated merge order.",
        "- After the first branch in a wave, each later branch is rebased or merged onto the updated integration head and reruns its declared verification before acceptance.",
        "- C0 reruns declared verification after each integration, records retained evidence, and cleans up merged branches/worktrees.",
        "- The next wave cannot start until every implementation is reviewed, merged, retested, recorded, and the barrier closes.",
        "- A failed task returns only that task to its implementer/reviewer loop and never opens the next wave.",
        "- Conflict, stale base, or abandonment keeps the task and wave open; repair or replace that task branch without promoting later work.",
    ]
    completed_before: set[str] = set()
    for wave in waves:
        prerequisite_ids = tuple(
            task_id
            for task_id in (task.id for task in ordered)
            if task_id in completed_before
            and any(
                task_id in assignment.task.depends_on for assignment in wave.assignments
            )
        )
        barrier = (
            ", ".join(f"`{task_id}`" for task_id in prerequisite_ids)
            or "none (graph root)"
        )
        lines.extend(
            [
                "",
                f"## Wave {wave.index} — {wave.milestone}",
                "",
                f"- Agent count: {len(wave.assignments)} implementer(s) and {len(wave.assignments)} reviewer(s)",
                f"- Base prerequisite barrier: {barrier}",
            ]
        )
        for assignment in wave.assignments:
            task = assignment.task
            dependencies = ", ".join(f"`{item}`" for item in task.depends_on) or "none"
            commands = (
                ", ".join(f"`{command}`" for command in task.acceptance_commands)
                if task.acceptance_commands
                else "none"
            )
            slug = task.id.lower()
            lines.extend(
                [
                    "",
                    f"### {assignment.implementer} / {assignment.reviewer} — `{task.id}`",
                    "",
                    f"- Source: [source]({_source_link(task)})",
                    f"- Dependencies: {dependencies}",
                    f"- Mode: `{task.mode}`",
                    f"- Locks: {', '.join(f'`{lock}`' for lock in task.locks)}",
                    f"- Branch: `agent/{slug}`",
                    f"- Worktree: `../alon-ai-task-{slug}`",
                    f"- Acceptance evidence: [source]({_source_link(task)}) — {task.verification}",
                    f"- Optional acceptance commands: {commands}",
                    f"- Merge order: {assignment.merge_order}",
                ]
            )
        unlocked = (
            ", ".join(f"`{task_id}`" for task_id in wave.newly_unlocked) or "none"
        )
        lines.extend(
            [
                "",
                f"- Newly unlocked tasks: {unlocked}",
                "- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.",
            ]
        )
        completed_before.update(assignment.task.id for assignment in wave.assignments)
    lines.extend(["", "## Cross-document edge appendix", ""])
    edge_lines: list[str] = []
    for consumer in ordered:
        for dependency in consumer.depends_on:
            provider = task_by_id[dependency]
            if provider.document_id != consumer.document_id:
                edge_lines.append(
                    f"- Provider `{provider.id}` — {provider.output}; "
                    f"Consumer `{consumer.id}` — {consumer.input}"
                )
    lines.extend(edge_lines or ["- None."])
    return "\n".join(lines) + "\n"


def render_artifacts(roadmap: Roadmap) -> dict[str, str]:
    return {
        ARTIFACT_PATHS[0]: render_execution_manifest(roadmap),
        ARTIFACT_PATHS[1]: render_execution_order(roadmap),
        ARTIFACT_PATHS[2]: render_agent_plan(roadmap),
    }


def _validate_rendered_artifacts(
    root: Path, roadmap: Roadmap, contents: dict[str, str]
) -> None:
    if tuple(contents) != ARTIFACT_PATHS:
        raise ValidationError("renderer produced an invalid artifact set")
    if any(not content.endswith("\n") for content in contents.values()):
        raise ValidationError("generated artifact requires final newline")
    try:
        for content in contents.values():
            content.encode("utf-8")
        manifest = json.loads(contents[ARTIFACT_PATHS[0]])
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError("generated artifact is not valid UTF-8/JSON") from error
    ordered_ids = [task.id for task in topological_order(roadmap)]
    if [task["id"] for task in manifest.get("tasks", [])] != ordered_ids:
        raise ValidationError("generated manifest task order drift")
    validate_waves(roadmap, build_waves(roadmap))
    markdown = contents[ARTIFACT_PATHS[1]] + contents[ARTIFACT_PATHS[2]]
    roadmap_root = (root / "docs/development-roadmap").resolve()
    for relative, line_text in re.findall(
        r"\[source\]\(([^)#]+)#L([0-9]+)\)", markdown
    ):
        target = (roadmap_root / relative).resolve()
        try:
            target.relative_to(roadmap_root)
        except ValueError as error:
            raise ValidationError(
                f"generated link escapes roadmap: {relative}"
            ) from error
        if not target.is_file():
            raise ValidationError(f"generated link target is missing: {relative}")
        line = int(line_text)
        if line < 1 or line > len(target.read_text(encoding="utf-8").splitlines()):
            raise ValidationError(f"generated link line is invalid: {relative}#L{line}")


def check_artifacts(root: Path) -> None:
    roadmap = parse_roadmap(root)
    expected = render_artifacts(roadmap)
    _validate_rendered_artifacts(root, roadmap, expected)
    diagnostics: list[str] = []
    for relative in ARTIFACT_PATHS:
        target = root / relative
        if not target.is_file():
            diagnostics.append(f"missing artifact: {relative}")
        elif target.read_bytes() != expected[relative].encode("utf-8"):
            diagnostics.append(f"stale artifact: {relative}")
    if diagnostics:
        raise ValidationError("\n".join(diagnostics))


def write_artifacts(
    root: Path,
    *,
    replace_func: Callable[[str | Path, str | Path], None] | None = None,
) -> None:
    roadmap = parse_roadmap(root)
    contents = render_artifacts(roadmap)
    _validate_rendered_artifacts(root, roadmap, contents)
    encoded_contents = {
        relative: content.encode("utf-8") for relative, content in contents.items()
    }
    temporary_paths: dict[str, Path] = {}
    try:
        for relative in ARTIFACT_PATHS:
            target = root / relative
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(encoded_contents[relative])
                temporary_paths[relative] = Path(handle.name)
    except OSError as error:
        for temporary in temporary_paths.values():
            temporary.unlink(missing_ok=True)
        raise ValidationError(
            f"artifact staging failed before replacement: {error}"
        ) from error

    replaced = 0
    replace = replace_func or os.replace
    try:
        for relative in ARTIFACT_PATHS:
            replace(temporary_paths[relative], root / relative)
            replaced += 1
    except OSError as error:
        raise ValidationError(
            "per-file atomic write failed after "
            f"{replaced} replacement(s); artifact set may be partially updated: {error}"
        ) from error
    finally:
        for temporary in temporary_paths.values():
            temporary.unlink(missing_ok=True)

    for relative in ARTIFACT_PATHS:
        if (root / relative).read_bytes() != encoded_contents[relative]:
            raise ValidationError(f"artifact reread mismatch: {relative}")


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate executable roadmap artifacts"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check source and artifacts")
    mode.add_argument("--write", action="store_true", help="regenerate all artifacts")
    arguments = parser.parse_args(argv)
    repository_root = root or Path(__file__).resolve().parents[1]
    try:
        if arguments.write:
            write_artifacts(repository_root)
            print("roadmap artifacts written and verified")
        else:
            check_artifacts(repository_root)
            print("roadmap artifacts are current")
    except (ValidationError, OSError, UnicodeError) as error:
        print(f"roadmap validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
