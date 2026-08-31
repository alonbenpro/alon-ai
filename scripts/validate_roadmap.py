"""Pure parsing and source-contract validation for roadmap tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass
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
_MILESTONES = frozenset(f"M{number}" for number in range(10))
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


@dataclass(frozen=True, slots=True)
class Roadmap:
    documents: tuple[ManifestDocument, ...]
    tasks: tuple[Task, ...]


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
    return _path_shaped(first) and second.startswith("M")


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

    def outside(pattern: str) -> re.Match[str] | None:
        return next(
            (
                match
                for match in re.finditer(pattern, verification)
                if not any(start < match.start() < end for start, end in code_ranges)
            ),
            None,
        )

    plural = outside(r"\bCommands:")
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
    marker = outside(r"\bCommand:")
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
        if candidate_cells and _path_shaped(candidate_cells[0]) and len(cells) != 2:
            raise ValidationError("manifest data row must have exactly two cells")
    documents: list[ManifestDocument] = []
    seen_paths: set[str] = set()
    for line in lines[start:end]:
        cells = _logical_cells(line)
        if not cells or not _path_shaped(cells[0]):
            continue
        path_cell, milestone = cells
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
    return tuple(documents)


def parse_roadmap(root: Path) -> Roadmap:
    documents = parse_manifest(root)
    tasks: list[Task] = []
    seen_document_ids: set[str] = set()
    for document in documents:
        source = (root / document.source).read_text(encoding="utf-8")
        source_lines = source.splitlines()
        id_lines = [
            line.removeprefix("**Document ID:** ")
            for line in source_lines
            if line.startswith("**Document ID:**")
        ]
        if len(id_lines) != 1 or _DOCUMENT_ID.fullmatch(id_lines[0]) is None:
            raise ValidationError("invalid document ID syntax/cardinality")
        if id_lines[0] in seen_document_ids:
            raise ValidationError("duplicate document ID")
        seen_document_ids.add(id_lines[0])
        start, end = _ordered_bounds(source_lines)
        if any(
            re.match(r"^- \[[xX]\](?: |$)", line) for line in source_lines[start:end]
        ):
            raise ValidationError("ordered task must be unchecked")
        checkbox_lines = [
            index
            for index in range(start, end)
            if re.match(r"^- \[ \](?: |$)", source_lines[index])
        ]
        if any(
            index == start
            or not source_lines[index - 1].startswith("<!-- roadmap-task ")
            for index in checkbox_lines
        ):
            raise ValidationError("unchecked box requires adjacent metadata")
        for index, line in enumerate(source_lines):
            if not line.startswith("<!-- roadmap-task"):
                continue
            if not (start <= index < end):
                raise ValidationError("orphan metadata outside ordered section")
            if index + 1 < end and source_lines[index + 1].startswith(
                "<!-- roadmap-task"
            ):
                raise ValidationError("duplicate metadata")
            if index + 1 >= end or not source_lines[index + 1].startswith("- [ ] "):
                raise ValidationError("orphan metadata")
        for index in checkbox_lines:
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
    for task in tasks:
        match = _TASK_ID.fullmatch(task.id)
        if match is None:
            raise ValidationError("invalid task ID syntax")
        if match.group("prefix") != task.document_id:
            raise ValidationError("task ID prefix does not match document ID")
    seen_task_ids: set[str] = set()
    for task in tasks:
        if task.id in seen_task_ids:
            raise ValidationError("duplicate task ID")
        seen_task_ids.add(task.id)
    counters: dict[str, int] = {}
    for task in tasks:
        counters[task.document_id] = counters.get(task.document_id, 0) + 1
        expected = f"{task.document_id}-T{counters[task.document_id]:02d}"
        if task.id != expected:
            raise ValidationError(f"non-contiguous task ID; expected {expected}")
    for task in tasks:
        if task.milestone not in _MILESTONES:
            raise ValidationError("invalid task milestone")
    previous_milestone: dict[str, int] = {}
    for task in tasks:
        value = int(task.milestone[1:])
        if value < previous_milestone.get(task.document_id, -1):
            raise ValidationError("task milestones decrease within document")
        previous_milestone[task.document_id] = value
    for task in tasks:
        if task.id in ROOT_TASK_IDS and task.depends_on:
            raise ValidationError("root allowlist task must use depends_on=-")
        if task.id not in ROOT_TASK_IDS and not task.depends_on:
            raise ValidationError("root allowlist rejects extra root")
    if not ROOT_TASK_IDS.issubset({task.id for task in tasks}):
        raise ValidationError("root allowlist task is missing")
    for task in tasks:
        for dependency in task.depends_on:
            if not dependency or _TASK_ID.fullmatch(dependency) is None:
                raise ValidationError("invalid dependency token")
        if len(task.depends_on) != len(set(task.depends_on)):
            raise ValidationError("duplicate dependency")
    known_ids = {task.id for task in tasks}
    tasks_by_id = {task.id: task for task in tasks}
    for task in tasks:
        if task.id in task.depends_on:
            raise ValidationError("self dependency")
        if any(dependency not in known_ids for dependency in task.depends_on):
            raise ValidationError("unknown dependency")
        if any(
            int(tasks_by_id[dependency].milestone[1:]) > int(task.milestone[1:])
            for dependency in task.depends_on
        ):
            raise ValidationError("dependency points to future milestone")
    for task in tasks:
        if task.mode not in {"parallel", "serial"}:
            raise ValidationError("invalid execution mode")
        if not task.locks or any(not lock for lock in task.locks):
            raise ValidationError("task requires nonempty lock list")
        if any(lock not in LOCKS for lock in task.locks):
            raise ValidationError("unknown lock")
        if len(task.locks) != len(set(task.locks)):
            raise ValidationError("duplicate lock")
        if task.mode != "serial" and any(
            lock in SERIAL_ONLY_LOCKS for lock in task.locks
        ):
            raise ValidationError("serial-only lock requires serial mode")
    return Roadmap(documents=documents, tasks=tuple(tasks))
