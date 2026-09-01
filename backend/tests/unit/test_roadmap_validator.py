import os
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from scripts.validate_roadmap import (
    ARTIFACT_PATHS,
    Roadmap,
    ValidationError,
    Wave,
    build_waves,
    canonical_fingerprint_bytes,
    check_artifacts,
    graph_fingerprint,
    main,
    parse_dependency_list,
    parse_manifest,
    parse_roadmap,
    render_agent_plan,
    render_execution_manifest,
    render_execution_order,
    topological_order,
    validate_waves,
    write_artifacts,
)

ROOT_ROW = "| `00-product/01-scope.md` | M0 |"
ROOT_META = "<!-- roadmap-task id=PRODUCT-01-T01 milestone=M0 depends_on=- mode=parallel locks=product-contracts -->"
ROOT_BOX = "- [ ] **Capture scope —** Input: brief. Operation: freeze. Output: contract. Test evidence: review. Failure behavior: block."


def write_tree(tmp_path: Path) -> Path:
    roadmap = tmp_path / "docs" / "development-roadmap"
    document = roadmap / "00-product" / "01-scope.md"
    document.parent.mkdir(parents=True)
    (roadmap / "README.md").write_text(
        f"""# Roadmap

## Complete file manifest mapped to vertical gates

| File | Gate |
| --- | --- |
{ROOT_ROW}

## Launch promotion ladder
""",
        encoding="utf-8",
    )
    document.write_text(
        f"""# Scope

**Document ID:** PRODUCT-01

## Ordered implementation tasks

{ROOT_META}
{ROOT_BOX}

## Acceptance
""",
        encoding="utf-8",
    )
    return roadmap


def append_second(roadmap: Path, *, depends: str, milestone: str = "M0") -> None:
    document = roadmap / "00-product" / "01-scope.md"
    metadata = (
        f"<!-- roadmap-task id=PRODUCT-01-T02 milestone={milestone} "
        f"depends_on={depends} mode=parallel locks=product-contracts -->"
    )
    box = ROOT_BOX.replace("Capture scope", "Second")
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "\n## Acceptance", f"\n{metadata}\n{box}\n## Acceptance"
        ),
        encoding="utf-8",
    )


def add_document(
    roadmap: Path,
    *,
    relative: str,
    document_id: str,
    milestone: str,
    tasks: list[tuple[str, str, str, str]],
) -> None:
    """Add tasks as (id, depends_on, mode, locks) to a miniature roadmap."""
    readme = roadmap / "README.md"
    row = f"| `{relative}` | {milestone} |"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(ROOT_ROW, f"{ROOT_ROW}\n{row}"),
        encoding="utf-8",
    )
    body = []
    for task_id, depends_on, mode, locks in tasks:
        body.extend(
            [
                f"<!-- roadmap-task id={task_id} milestone={milestone} depends_on={depends_on} mode={mode} locks={locks} -->",
                f"- [ ] **{task_id} title —** Input: input for {task_id}. Operation: operate {task_id}. Output: output from {task_id}. Test evidence: review {task_id}. Failure behavior: block {task_id}.",
            ]
        )
    document = roadmap / relative
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(
        "\n".join(
            [
                f"# {document_id}",
                "",
                f"**Document ID:** {document_id}",
                "",
                "## Ordered implementation tasks",
                "",
                *body,
                "",
                "## Acceptance",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_wave_tree(tmp_path: Path):
    roadmap = write_tree(tmp_path)
    add_document(
        roadmap,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
            ("ARCH-01-T02", "PRODUCT-01-T01", "parallel", "database-schema"),
            ("ARCH-01-T03", "PRODUCT-01-T01", "parallel", "agent-runtime"),
            ("ARCH-01-T04", "PRODUCT-01-T01", "parallel", "provider-contracts"),
            (
                "ARCH-01-T05",
                "ARCH-01-T01,ARCH-01-T02,ARCH-01-T03,ARCH-01-T04",
                "parallel",
                "backend-domain",
            ),
        ],
    )
    return parse_roadmap(tmp_path)


def write_chain_tree(tmp_path: Path):
    roadmap = write_tree(tmp_path)
    add_document(
        roadmap,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
            ("ARCH-01-T02", "ARCH-01-T01", "parallel", "backend-domain"),
        ],
    )
    return parse_roadmap(tmp_path)


def test_valid_minimal_tree_parses(tmp_path: Path) -> None:
    write_tree(tmp_path)

    result = parse_roadmap(tmp_path)

    assert result.tasks[0].id == "PRODUCT-01-T01"


@pytest.mark.parametrize("count", [0, 2])
def test_manifest_heading_is_unique(tmp_path: Path, count: int) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    text = readme.read_text(encoding="utf-8")
    heading = "## Complete file manifest mapped to vertical gates"
    if count == 0:
        text = text.replace(heading, "## Wrong")
    else:
        text += f"\n{heading}\n"
    readme.write_text(text, encoding="utf-8")

    with pytest.raises(ValidationError, match="manifest heading"):
        parse_manifest(tmp_path)


def test_manifest_requires_closing_level_two_boundary(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "## Launch promotion ladder", "### Launch promotion ladder"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="closing boundary"):
        parse_manifest(tmp_path)


@pytest.mark.parametrize(
    ("row", "fails"),
    [
        (ROOT_ROW, True),
        ("`00-product/01-scope.txt` | M0", True),
        ("| bad/path | MX |", True),
        ("| `candidate` | M10 |", True),
        ("| Name | Value |", False),
    ],
)
def test_manifest_like_rows_outside_authority_are_owned(
    tmp_path: Path, row: str, fails: bool
) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + f"\n{row}\n", encoding="utf-8"
    )

    if fails:
        with pytest.raises(ValidationError, match="outside manifest"):
            parse_manifest(tmp_path)
    else:
        assert parse_manifest(tmp_path)[0].source.endswith("01-scope.md")


def test_route_row_with_bare_m_is_not_manifest_like(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\n| /route | M |\n",
        encoding="utf-8",
    )

    assert parse_manifest(tmp_path)[0].source.endswith("01-scope.md")


def test_manifest_data_row_may_retain_descriptive_columns(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            ROOT_ROW, "| `00-product/01-scope.md` | M0 | extra |"
        ),
        encoding="utf-8",
    )

    assert parse_manifest(tmp_path)[0].source.endswith("01-scope.md")


def test_manifest_extra_outer_delimiters_count_as_cells(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            ROOT_ROW, "|| `00-product/01-scope.md` | M0 ||"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="outer delimiters"):
        parse_manifest(tmp_path)


@pytest.mark.parametrize(
    "cell",
    [
        "00-product/01-scope.md",
        "``00-product/01-scope.md``",
        "`/00-product/01-scope.md`",
        "`00-product\\01-scope.md`",
        "`./00-product/01-scope.md`",
        "`00-product/../01-scope.md`",
        "`00-product/01-scope.txt`",
    ],
)
def test_manifest_path_cell_has_strict_safe_syntax(tmp_path: Path, cell: str) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(ROOT_ROW, f"| {cell} | M0 |"),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="manifest path"):
        parse_manifest(tmp_path)


@pytest.mark.parametrize("milestone", ["M10", "MX", "m0", ""])
def test_manifest_milestone_cell_is_m0_through_m9(
    tmp_path: Path, milestone: str
) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            ROOT_ROW, f"| `00-product/01-scope.md` | {milestone} |"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="manifest milestone"):
        parse_manifest(tmp_path)


def test_manifest_paths_are_unique(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(ROOT_ROW, f"{ROOT_ROW}\n{ROOT_ROW}"),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate manifest path"):
        parse_manifest(tmp_path)


def test_manifest_document_must_exist(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    (roadmap / "00-product" / "01-scope.md").unlink()

    with pytest.raises(ValidationError, match="missing manifest document"):
        parse_manifest(tmp_path)


def test_manifest_resolution_stays_under_roadmap_root(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.unlink()
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    document.symlink_to(outside)

    with pytest.raises(ValidationError, match="outside roadmap root"):
        parse_manifest(tmp_path)


def test_manifest_order_is_retained_for_documents_and_tasks(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    other_row = "| `01-arch/01-system.md` | M0 |"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            ROOT_ROW, f"{other_row}\n{ROOT_ROW}"
        ),
        encoding="utf-8",
    )
    other = roadmap / "01-arch" / "01-system.md"
    other.parent.mkdir()
    other.write_text(
        """# System
**Document ID:** ARCH-01
## Ordered implementation tasks
<!-- roadmap-task id=ARCH-01-T01 milestone=M0 depends_on=PRODUCT-01-T01 mode=parallel locks=architecture-contracts -->
- [ ] **System —** Input: contract. Operation: define. Output: system. Test evidence: review. Failure behavior: block.
## Acceptance
""",
        encoding="utf-8",
    )

    result = parse_roadmap(tmp_path)

    assert tuple(document.source for document in result.documents) == (
        "docs/development-roadmap/01-arch/01-system.md",
        "docs/development-roadmap/00-product/01-scope.md",
    )
    assert tuple(task.id for task in result.tasks) == ("ARCH-01-T01", "PRODUCT-01-T01")


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "syntax"])
def test_document_id_has_strict_syntax_and_cardinality(
    tmp_path: Path, mutation: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    text = document.read_text(encoding="utf-8")
    line = "**Document ID:** PRODUCT-01"
    if mutation == "missing":
        text = text.replace(line, "")
    elif mutation == "duplicate":
        text = text.replace(line, f"{line}\n{line}")
    else:
        text = text.replace(line, "**Document ID:** product-1")
    document.write_text(text, encoding="utf-8")

    with pytest.raises(ValidationError, match="document ID"):
        parse_roadmap(tmp_path)


def test_document_ids_are_unique_across_documents(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    row = "| `01-arch/01-system.md` | M0 |"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(ROOT_ROW, f"{ROOT_ROW}\n{row}"),
        encoding="utf-8",
    )
    other = roadmap / "01-arch" / "01-system.md"
    other.parent.mkdir()
    other.write_text(
        """**Document ID:** PRODUCT-01
## Ordered implementation tasks
<!-- roadmap-task id=PRODUCT-01-T02 milestone=M0 depends_on=PRODUCT-01-T01 mode=parallel locks=architecture-contracts -->
- [ ] **System —** Input: contract. Operation: define. Output: system. Test evidence: review. Failure behavior: block.
## Acceptance
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate document ID"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unbounded"])
def test_ordered_section_has_one_bounded_region(tmp_path: Path, mutation: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    text = document.read_text(encoding="utf-8")
    heading = "## Ordered implementation tasks"
    if mutation == "missing":
        text = text.replace(heading, "## Wrong")
    elif mutation == "duplicate":
        text += f"\n{heading}\n"
    else:
        text = text.replace("## Acceptance", "### Acceptance")
    document.write_text(text, encoding="utf-8")

    with pytest.raises(ValidationError, match="ordered section"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize("metadata", [True, False])
def test_checked_box_inside_ordered_section_always_fails(
    tmp_path: Path, metadata: bool
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    text = document.read_text(encoding="utf-8").replace("- [ ] ", "- [X] ")
    if not metadata:
        text = text.replace(f"{ROOT_META}\n", "")
    document.write_text(text, encoding="utf-8")

    with pytest.raises(ValidationError, match="unchecked"):
        parse_roadmap(tmp_path)


def test_bare_checked_box_inside_ordered_section_fails(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            f"{ROOT_META}\n{ROOT_BOX}", "- [x]"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="unchecked"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize("mutation", ["missing", "blank"])
def test_unchecked_box_requires_immediately_adjacent_metadata(
    tmp_path: Path, mutation: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    text = document.read_text(encoding="utf-8")
    replacement = "" if mutation == "missing" else f"{ROOT_META}\n\n"
    text = text.replace(f"{ROOT_META}\n", replacement)
    document.write_text(text, encoding="utf-8")

    with pytest.raises(ValidationError, match="adjacent metadata"):
        parse_roadmap(tmp_path)


def test_bare_unchecked_box_requires_adjacent_metadata(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            f"{ROOT_META}\n{ROOT_BOX}", "- [ ]"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="adjacent metadata"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize("location", ["inside", "outside"])
def test_metadata_cannot_be_orphaned(tmp_path: Path, location: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    text = document.read_text(encoding="utf-8")
    if location == "inside":
        text = text.replace(ROOT_BOX, "")
    else:
        text += f"\n{ROOT_META}\n"
    document.write_text(text, encoding="utf-8")

    with pytest.raises(ValidationError, match="orphan metadata"):
        parse_roadmap(tmp_path)


def test_metadata_cannot_be_duplicated_for_one_checkbox(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            ROOT_META, f"{ROOT_META}\n{ROOT_META}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate metadata"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    "bad_title",
    ["Capture scope", "**Capture scope**", "** —**", "**Capture scope —** stray"],
)
def test_task_title_has_exact_bold_em_dash_shape(
    tmp_path: Path, bad_title: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace("**Capture scope —**", bad_title),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="task title"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    "marker", ["Input:", "Operation:", "Output:", "Test evidence:", "Failure behavior:"]
)
def test_each_task_clause_marker_is_present(tmp_path: Path, marker: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(marker, marker.replace(":", "s:")),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="missing task clause"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    "marker", ["Input:", "Operation:", "Output:", "Test evidence:", "Failure behavior:"]
)
def test_each_task_clause_marker_is_unique(tmp_path: Path, marker: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            marker, f"{marker} duplicate. {marker}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate task clause"):
        parse_roadmap(tmp_path)


def test_task_clause_markers_have_exact_order(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "Input: brief. Operation: freeze.",
            "Operation: freeze. Input: brief.",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="task clause order"):
        parse_roadmap(tmp_path)


def test_task_record_retains_full_source_contract(tmp_path: Path) -> None:
    write_tree(tmp_path)

    task = parse_roadmap(tmp_path).tasks[0]

    assert task.id == "PRODUCT-01-T01"
    assert task.milestone == "M0"
    assert task.document_id == "PRODUCT-01"
    assert task.title == "Capture scope"
    assert task.body == ROOT_BOX.removeprefix("- [ ] ")
    assert task.source == "docs/development-roadmap/00-product/01-scope.md"
    assert task.line == 8
    assert task.depends_on == ()
    assert task.mode == "parallel"
    assert task.locks == ("product-contracts",)
    assert task.input == "Input: brief."
    assert task.operation == "Operation: freeze."
    assert task.output == "Output: contract."
    assert task.verification == "Test evidence: review."
    assert task.failure_behavior == "Failure behavior: block."
    assert task.acceptance_commands == ()


def test_literal_command_marker_is_recognized(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "Test evidence: review.", "Test evidence: Command: `pytest -q`."
        ),
        encoding="utf-8",
    )

    assert parse_roadmap(tmp_path).tasks[0].acceptance_commands == ("pytest -q",)


@pytest.mark.parametrize(
    "declaration",
    [
        "Command:",
        "Command: ``",
        "Command: `pytest -q`, `ruff check .`",
        "Command: `pytest -q` then inspect `log.txt`",
    ],
)
def test_singular_command_has_exactly_one_nonempty_span(
    tmp_path: Path, declaration: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "Test evidence: review.", f"Test evidence: {declaration}."
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="singular Command"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("Commands: `pytest -q`", ("pytest -q",)),
        ("Commands: `pytest -q`, `ruff check .`", ("pytest -q", "ruff check .")),
        ("Commands:", None),
        ("Commands: ``", None),
        ("Commands: `a`; `b`", None),
        ("Commands: `a` and `b`", None),
        ("Commands: `a` or `b`", None),
        ("Commands: `a` / `b`", None),
        ("Commands: `a` then `b`", None),
        ("Commands: `a` + `b`", None),
        ("Commands: `a` `b`", None),
    ],
)
def test_plural_commands_use_only_comma_separators(
    tmp_path: Path, declaration: str, expected: tuple[str, ...] | None
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "Test evidence: review.", f"Test evidence: {declaration}."
        ),
        encoding="utf-8",
    )

    if expected is None:
        with pytest.raises(ValidationError, match="plural Commands"):
            parse_roadmap(tmp_path)
    else:
        assert parse_roadmap(tmp_path).tasks[0].acceptance_commands == expected


@pytest.mark.parametrize(
    "declaration",
    [
        "Command: `first` then Commands: `second`",
        "Commands: `first` then Command: `second`",
    ],
)
def test_multiple_outside_code_command_markers_fail(
    tmp_path: Path, declaration: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "Test evidence: review.", f"Test evidence: {declaration}."
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="multiple command markers"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    "evidence", ["inspect `fixture.json`", "describe literal `Command:` marker"]
)
def test_generic_code_spans_are_evidence_only(tmp_path: Path, evidence: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "Test evidence: review.", f"Test evidence: {evidence}."
        ),
        encoding="utf-8",
    )

    assert parse_roadmap(tmp_path).tasks[0].acceptance_commands == ()


@pytest.mark.parametrize("bad_id", ["product-01-T01", "PRODUCT-1-T01", "PRODUCT-01-T1"])
def test_task_id_has_exact_syntax(tmp_path: Path, bad_id: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace("PRODUCT-01-T01", bad_id),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="task ID syntax"):
        parse_roadmap(tmp_path)


def test_task_id_prefix_matches_document_id(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace("PRODUCT-01-T01", "OTHER-01-T01"),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="task ID prefix"):
        parse_roadmap(tmp_path)


def test_task_ids_are_contiguous_in_document_source_order(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    extra = ROOT_META.replace("T01", "T03").replace(
        "depends_on=-", "depends_on=PRODUCT-01-T01"
    )
    box = ROOT_BOX.replace("Capture scope", "Later")
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "\n## Acceptance", f"\n{extra}\n{box}\n## Acceptance"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="contiguous task ID"):
        parse_roadmap(tmp_path)


def test_task_ids_are_globally_unique(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    extra = ROOT_META.replace("depends_on=-", "depends_on=PRODUCT-01-T01")
    box = ROOT_BOX.replace("Capture scope", "Duplicate")
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "\n## Acceptance", f"\n{extra}\n{box}\n## Acceptance"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate task ID"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize("milestone", ["M10", "MX", "m0", ""])
def test_task_milestone_is_in_valid_set(tmp_path: Path, milestone: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "milestone=M0", f"milestone={milestone}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="task milestone"):
        parse_roadmap(tmp_path)


def test_task_milestones_are_nondecreasing_per_document(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    first = document.read_text(encoding="utf-8").replace(
        "milestone=M0", "milestone=M1", 1
    )
    extra = ROOT_META.replace("T01", "T02").replace(
        "depends_on=-", "depends_on=PRODUCT-01-T01"
    )
    document.write_text(
        first.replace(
            "\n## Acceptance",
            f"\n{extra}\n{ROOT_BOX.replace('Capture scope', 'Second')}\n## Acceptance",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="milestones decrease"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize("mutation", ["extra-root", "root-has-dependency"])
def test_roots_exactly_match_sole_allowlist(tmp_path: Path, mutation: str) -> None:
    roadmap = write_tree(tmp_path)
    if mutation == "extra-root":
        append_second(roadmap, depends="-")
    else:
        document = roadmap / "00-product" / "01-scope.md"
        document.write_text(
            document.read_text(encoding="utf-8").replace(
                "depends_on=-", "depends_on=PRODUCT-01-T02", 1
            ),
            encoding="utf-8",
        )
        append_second(roadmap, depends="PRODUCT-01-T01")

    with pytest.raises(ValidationError, match="root allowlist"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    "depends", ["", "product-01-T01", "PRODUCT-01-T1", "PRODUCT-01-T01, BAD"]
)
def test_dependency_tokens_have_strict_nonempty_grammar(
    tmp_path: Path, depends: str
) -> None:
    roadmap = write_tree(tmp_path)
    append_second(roadmap, depends=depends)

    with pytest.raises(ValidationError, match="dependency token"):
        parse_roadmap(tmp_path)


def test_dependency_ids_are_unique_per_task(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    append_second(roadmap, depends="PRODUCT-01-T01,PRODUCT-01-T01")

    with pytest.raises(ValidationError, match="duplicate dependency"):
        parse_roadmap(tmp_path)


def test_dependency_id_must_be_known(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    append_second(roadmap, depends="MISSING-01-T01")

    with pytest.raises(ValidationError, match="unknown dependency"):
        parse_roadmap(tmp_path)


def test_task_cannot_depend_on_itself(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    append_second(roadmap, depends="PRODUCT-01-T02")

    with pytest.raises(ValidationError, match="self dependency"):
        parse_roadmap(tmp_path)


def test_dependency_cannot_point_to_future_milestone(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    append_second(roadmap, depends="PRODUCT-01-T03")
    document = roadmap / "00-product" / "01-scope.md"
    third = (
        "<!-- roadmap-task id=PRODUCT-01-T03 milestone=M1 "
        "depends_on=PRODUCT-01-T01 mode=parallel locks=product-contracts -->"
    )
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "\n## Acceptance",
            f"\n{third}\n{ROOT_BOX.replace('Capture scope', 'Third')}\n## Acceptance",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="future milestone"):
        parse_roadmap(tmp_path)


def test_dependency_source_order_is_retained() -> None:
    assert parse_dependency_list("PRODUCT-01-T02,PRODUCT-01-T01") == (
        "PRODUCT-01-T02",
        "PRODUCT-01-T01",
    )


@pytest.mark.parametrize("mode", ["concurrent", "", "Parallel"])
def test_execution_mode_is_parallel_or_serial(tmp_path: Path, mode: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace("mode=parallel", f"mode={mode}"),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="execution mode"):
        parse_roadmap(tmp_path)


def test_lock_list_is_nonempty(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "locks=product-contracts", "locks="
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="nonempty lock"):
        parse_roadmap(tmp_path)


def test_locks_come_from_closed_vocabulary(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "locks=product-contracts", "locks=invented-lock"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="unknown lock"):
        parse_roadmap(tmp_path)


def test_lock_list_has_no_duplicates(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "locks=product-contracts", "locks=product-contracts,product-contracts"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate lock"):
        parse_roadmap(tmp_path)


@pytest.mark.parametrize(
    "lock",
    [
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
    ],
)
def test_serial_only_locks_require_serial_mode(tmp_path: Path, lock: str) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product" / "01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(
            "locks=product-contracts", f"locks={lock}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="serial-only lock"):
        parse_roadmap(tmp_path)


def test_same_milestone_cycle_reports_concrete_path(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    add_document(
        roadmap,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "ARCH-01-T02", "parallel", "architecture-contracts"),
            ("ARCH-01-T02", "ARCH-01-T01", "parallel", "backend-domain"),
        ],
    )

    parsed = parse_roadmap(tmp_path)

    with pytest.raises(
        ValidationError,
        match=r"cycle: ARCH-01-T01 -> ARCH-01-T02 -> ARCH-01-T01",
    ):
        topological_order(parsed)


def test_topological_order_uses_stable_milestone_manifest_task_tie_breaks(
    tmp_path: Path,
) -> None:
    roadmap = write_tree(tmp_path)
    add_document(
        roadmap,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
            ("ARCH-01-T02", "ARCH-01-T01", "parallel", "backend-domain"),
        ],
    )
    add_document(
        roadmap,
        relative="02-data/01-schema.md",
        document_id="DATA-01",
        milestone="M0",
        tasks=[
            ("DATA-01-T01", "PRODUCT-01-T01", "parallel", "database-schema"),
        ],
    )

    order = topological_order(parse_roadmap(tmp_path))

    assert tuple(task.id for task in order) == (
        "PRODUCT-01-T01",
        "DATA-01-T01",
        "ARCH-01-T01",
        "ARCH-01-T02",
    )


def test_waves_have_hand_checked_assignments_merge_order_and_unlocks(
    tmp_path: Path,
) -> None:
    roadmap = write_wave_tree(tmp_path)

    waves = build_waves(roadmap)

    assert [
        (
            wave.index,
            wave.milestone,
            tuple(
                (
                    assignment.task.id,
                    assignment.implementer,
                    assignment.reviewer,
                    assignment.merge_order,
                )
                for assignment in wave.assignments
            ),
            wave.newly_unlocked,
        )
        for wave in waves
    ] == [
        (
            1,
            "M0",
            (("PRODUCT-01-T01", "I1", "R1", 1),),
            ("ARCH-01-T01", "ARCH-01-T02", "ARCH-01-T03", "ARCH-01-T04"),
        ),
        (
            2,
            "M0",
            (
                ("ARCH-01-T01", "I1", "R1", 1),
                ("ARCH-01-T02", "I2", "R2", 2),
                ("ARCH-01-T03", "I3", "R3", 3),
                ("ARCH-01-T04", "I4", "R4", 4),
            ),
            ("ARCH-01-T05",),
        ),
        (
            3,
            "M0",
            (("ARCH-01-T05", "I1", "R1", 1),),
            (),
        ),
    ]
    validate_waves(roadmap, waves)


def test_wave_validation_rejects_current_wave_dependency(tmp_path: Path) -> None:
    roadmap = write_chain_tree(tmp_path)
    first, second, third = build_waves(roadmap)
    invalid = (
        first,
        Wave(
            index=2,
            milestone="M0",
            assignments=(
                second.assignments[0],
                replace(
                    third.assignments[0],
                    implementer="I2",
                    reviewer="R2",
                    merge_order=2,
                ),
            ),
            newly_unlocked=(),
        ),
    )

    with pytest.raises(ValidationError, match="current-wave dependency"):
        validate_waves(roadmap, invalid)


def test_wave_validation_rejects_milestone_crossing(tmp_path: Path) -> None:
    roadmap_root = write_tree(tmp_path)
    add_document(
        roadmap_root,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M1",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
        ],
    )
    roadmap = parse_roadmap(tmp_path)
    first, second = build_waves(roadmap)
    invalid = (first, replace(second, milestone="M0"))

    with pytest.raises(ValidationError, match="milestone crossing"):
        validate_waves(roadmap, invalid)


def test_wave_validation_rejects_shared_lock(tmp_path: Path) -> None:
    roadmap_root = write_tree(tmp_path)
    add_document(
        roadmap_root,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "backend-domain"),
            ("ARCH-01-T02", "PRODUCT-01-T01", "parallel", "backend-domain"),
        ],
    )
    roadmap = parse_roadmap(tmp_path)
    first, second, third = build_waves(roadmap)
    invalid = (
        first,
        Wave(
            index=2,
            milestone="M0",
            assignments=(
                second.assignments[0],
                replace(
                    third.assignments[0],
                    implementer="I2",
                    reviewer="R2",
                    merge_order=2,
                ),
            ),
            newly_unlocked=(),
        ),
    )

    with pytest.raises(ValidationError, match="shared lock"):
        validate_waves(roadmap, invalid)


def test_wave_validation_rejects_serial_co_tenancy(tmp_path: Path) -> None:
    roadmap_root = write_tree(tmp_path)
    add_document(
        roadmap_root,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "serial", "migration-head"),
            ("ARCH-01-T02", "PRODUCT-01-T01", "parallel", "backend-domain"),
        ],
    )
    roadmap = parse_roadmap(tmp_path)
    first, second, third = build_waves(roadmap)
    invalid = (
        first,
        Wave(
            index=2,
            milestone="M0",
            assignments=(
                second.assignments[0],
                replace(
                    third.assignments[0],
                    implementer="I2",
                    reviewer="R2",
                    merge_order=2,
                ),
            ),
            newly_unlocked=(),
        ),
    )

    with pytest.raises(ValidationError, match="serial task must be alone"):
        validate_waves(roadmap, invalid)


def test_wave_validation_rejects_fifth_implementer(tmp_path: Path) -> None:
    roadmap_root = write_tree(tmp_path)
    add_document(
        roadmap_root,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
            ("ARCH-01-T02", "PRODUCT-01-T01", "parallel", "database-schema"),
            ("ARCH-01-T03", "PRODUCT-01-T01", "parallel", "agent-runtime"),
            ("ARCH-01-T04", "PRODUCT-01-T01", "parallel", "provider-contracts"),
            ("ARCH-01-T05", "PRODUCT-01-T01", "parallel", "backend-domain"),
        ],
    )
    roadmap = parse_roadmap(tmp_path)
    first, second, third = build_waves(roadmap)
    fifth = replace(
        third.assignments[0],
        implementer="I5",
        reviewer="R5",
        merge_order=5,
    )
    invalid = (first, replace(second, assignments=second.assignments + (fifth,)))

    with pytest.raises(ValidationError, match="at most four implementers"):
        validate_waves(roadmap, invalid)


def test_wave_validation_rejects_missing_task(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)

    with pytest.raises(ValidationError, match="missing task"):
        validate_waves(roadmap, waves[:-1])


def test_wave_validation_rejects_duplicate_task(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    invalid = waves + (replace(waves[0], index=4, newly_unlocked=()),)

    with pytest.raises(ValidationError, match="duplicate task"):
        validate_waves(roadmap, invalid)


def test_wave_validation_rejects_agent_assignment_drift(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    assignment = replace(waves[1].assignments[0], implementer="I2")
    invalid_wave = replace(
        waves[1], assignments=(assignment, *waves[1].assignments[1:])
    )

    with pytest.raises(ValidationError, match="agent assignment drift"):
        validate_waves(roadmap, (waves[0], invalid_wave, waves[2]))


def test_wave_validation_rejects_merge_order_drift(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    assignment = replace(waves[1].assignments[0], merge_order=2)
    invalid_wave = replace(
        waves[1], assignments=(assignment, *waves[1].assignments[1:])
    )

    with pytest.raises(ValidationError, match="merge-order drift"):
        validate_waves(roadmap, (waves[0], invalid_wave, waves[2]))


def test_wave_validation_requires_dependencies_in_earlier_waves(
    tmp_path: Path,
) -> None:
    roadmap = write_chain_tree(tmp_path)
    first, second, third = build_waves(roadmap)

    with pytest.raises(ValidationError, match="dependency from an earlier wave"):
        validate_waves(roadmap, (first, third, second))


def test_wave_validation_rejects_milestone_skipping(tmp_path: Path) -> None:
    roadmap_root = write_tree(tmp_path)
    add_document(
        roadmap_root,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
        ],
    )
    add_document(
        roadmap_root,
        relative="02-data/01-schema.md",
        document_id="DATA-01",
        milestone="M1",
        tasks=[
            ("DATA-01-T01", "PRODUCT-01-T01", "parallel", "database-schema"),
        ],
    )
    roadmap = parse_roadmap(tmp_path)
    first, second, third = build_waves(roadmap)

    with pytest.raises(ValidationError, match="milestone skipping"):
        validate_waves(roadmap, (first, third, second))


def test_canonical_fingerprint_bytes_and_digest_are_exact(tmp_path: Path) -> None:
    write_tree(tmp_path)
    roadmap = parse_roadmap(tmp_path)
    expected = (
        b'{"manifest_documents":["docs/development-roadmap/00-product/01-scope.md"],'
        b'"milestones":["M0","M1","M2","M3","M4","M5","M6","M7","M8","M9"],'
        b'"root_task_ids":["PRODUCT-01-T01"],"schema_version":1,"tasks":['
        b'{"depends_on":[],"document_id":"PRODUCT-01","failure_behavior":"Failure behavior: block.",'
        b'"id":"PRODUCT-01-T01","input":"Input: brief.","line":8,'
        b'"locks":["product-contracts"],"milestone":"M0","mode":"parallel",'
        b'"operation":"Operation: freeze.","output":"Output: contract.",'
        b'"source":"docs/development-roadmap/00-product/01-scope.md",'
        b'"title":"Capture scope","verification":"Test evidence: review."}]}'
    )

    assert canonical_fingerprint_bytes(roadmap) == expected
    assert graph_fingerprint(roadmap) == sha256(expected).hexdigest()


@pytest.mark.parametrize(
    "mutation",
    [
        "manifest_order",
        "source_line",
        "task_metadata",
        "input",
        "operation",
        "output",
        "verification",
        "failure_behavior",
    ],
)
def test_fingerprint_binds_every_authoritative_input(
    tmp_path: Path, mutation: str
) -> None:
    roadmap = write_chain_tree(tmp_path)
    baseline = graph_fingerprint(roadmap)
    tasks = list(roadmap.tasks)
    documents = roadmap.documents
    if mutation == "manifest_order":
        documents = tuple(reversed(documents))
    else:
        field = {
            "source_line": "line",
            "task_metadata": "mode",
            "input": "input",
            "operation": "operation",
            "output": "output",
            "verification": "verification",
            "failure_behavior": "failure_behavior",
        }[mutation]
        value = getattr(tasks[-1], field)
        tasks[-1] = replace(
            tasks[-1], **{field: value + 1 if field == "line" else f"{value} changed"}
        )
    changed = Roadmap(documents=documents, tasks=tuple(tasks))

    assert graph_fingerprint(roadmap) == baseline
    assert graph_fingerprint(changed) != baseline


def test_valid_graph_renders_hand_checked_deterministic_artifacts(
    tmp_path: Path,
) -> None:
    write_tree(tmp_path)
    roadmap = parse_roadmap(tmp_path)

    manifest = render_execution_manifest(roadmap)
    execution = render_execution_order(roadmap)
    agents = render_agent_plan(roadmap)

    expected_manifest = """{
  "milestones": [
    "M0",
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M7",
    "M8",
    "M9"
  ],
  "schema_version": 1,
  "tasks": [
    {
      "depends_on": [],
      "document_id": "PRODUCT-01",
      "id": "PRODUCT-01-T01",
      "line": 8,
      "locks": [
        "product-contracts"
      ],
      "milestone": "M0",
      "mode": "parallel",
      "source": "docs/development-roadmap/00-product/01-scope.md",
      "title": "Capture scope"
    }
  ]
}
"""
    expected_execution = """# Executable Roadmap Order

> Warning: generated; it does not prove implementation status. Edit source task metadata, never this file.

- Regenerate: `python3 scripts/validate_roadmap.py --write`
- Validate: `python3 scripts/validate_roadmap.py --check`
- Source-graph fingerprint: `f0dc57de7c221d5544df3159f52d50f0a391aea13c9ff65ebdb1431bbf384400`

## Totals

- Tasks: 1
- Documents: 1
- M0: 1
- M1: 0
- M2: 0
- M3: 0
- M4: 0
- M5: 0
- M6: 0
- M7: 0
- M8: 0
- M9: 0
- By document:
  - `PRODUCT-01`: 1

## Frontier rule

A task is executable only when every dependency has retained passing evidence from an earlier completed wave.

## M0

1. `PRODUCT-01-T01` — Capture scope ([source](00-product/01-scope.md#L8)); dependencies: none

## M1

No tasks.

## M2

No tasks.

## M3

No tasks.

## M4

No tasks.

## M5

No tasks.

## M6

No tasks.

## M7

No tasks.

## M8

No tasks.

## M9

No tasks.
"""
    expected_agents = """# Agent Execution Plan

> Warning: generated for the source graph below; it does not prove implementation status.

- Source-graph fingerprint: `f0dc57de7c221d5544df3159f52d50f0a391aea13c9ff65ebdb1431bbf384400`
- Regenerate: `python3 scripts/validate_roadmap.py --write`
- Validate: `python3 scripts/validate_roadmap.py --check`

## Operating contract

- C0 owns integration, dependency evidence, wave assignment, merge order, status, and milestone gates.
- Implementers are I1..I4; read-only reviewers are R1..R4.
- The absolute live-agent ceiling is nine and the implementation/worktree ceiling is four.
- Each task uses its listed `agent/<task-id>` branch and sibling `../alon-ai-task-<task-id>` worktree from the exact wave-base integration commit.
- Prompts include only the assigned task, dependency evidence, declared locks/surfaces, source acceptance evidence, optional marked commands, base commit, and report path.
- Implementers may not start dependent tasks, edit the integration checkout, merge, push, widen declared locks, or spawn implementation agents.
- Generic or unmarked code spans in task evidence are evidence-only; only grammar-valid explicit `Command:` or `Commands:` spans become optional acceptance commands.
- C0 may add normal repository verification required by declared locks, but may not substitute, broaden, or fabricate evidence commands.
- Each reviewer checks only its completed task before C0 merges branches one at a time in generated merge order.
- After the first branch in a wave, each later branch is rebased or merged onto the updated integration head and reruns its declared verification before acceptance.
- C0 reruns declared verification after each integration, records retained evidence, and cleans up merged branches/worktrees.
- The next wave cannot start until every implementation is reviewed, merged, retested, recorded, and the barrier closes.
- A failed task returns only that task to its implementer/reviewer loop and never opens the next wave.
- Conflict, stale base, or abandonment keeps the task and wave open; repair or replace that task branch without promoting later work.

## Wave 1 — M0

- Agent count: 1 implementer(s) and 1 reviewer(s)
- Base prerequisite barrier: none (graph root)

### I1 / R1 — `PRODUCT-01-T01`

- Source: [source](00-product/01-scope.md#L8)
- Dependencies: none
- Mode: `parallel`
- Locks: `product-contracts`
- Branch: `agent/product-01-t01`
- Worktree: `../alon-ai-task-product-01-t01`
- Acceptance evidence: [source](00-product/01-scope.md#L8) — Test evidence: review.
- Optional acceptance commands: none
- Merge order: 1

- Newly unlocked tasks: none
- Barrier: all assignments above must be reviewed, merged in order, retested, and recorded before the next wave starts.

## Cross-document edge appendix

- None.
"""

    assert manifest == expected_manifest
    assert execution == expected_execution
    assert agents == expected_agents


def test_cross_document_appendix_is_ordered_and_preserves_literal_pipes(
    tmp_path: Path,
) -> None:
    roadmap_root = write_tree(tmp_path)
    root_document = roadmap_root / "00-product" / "01-scope.md"
    root_document.write_text(
        root_document.read_text(encoding="utf-8").replace(
            "Output: contract.", "Output: contract | signed."
        ),
        encoding="utf-8",
    )
    add_document(
        roadmap_root,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[
            ("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts"),
            (
                "ARCH-01-T02",
                "PRODUCT-01-T01,ARCH-01-T01",
                "parallel",
                "backend-domain",
            ),
        ],
    )
    consumer = roadmap_root / "01-arch" / "01-system.md"
    consumer.write_text(
        consumer.read_text(encoding="utf-8").replace(
            "Input: input for ARCH-01", "Input: contract | signed for ARCH-01"
        ),
        encoding="utf-8",
    )

    rendered = render_agent_plan(parse_roadmap(tmp_path))
    appendix = rendered.split("## Cross-document edge appendix\n\n", 1)[1]

    assert appendix == (
        "- Provider `PRODUCT-01-T01` — Output: contract | signed.; "
        "Consumer `ARCH-01-T01` — Input: contract | signed for ARCH-01-T01.\n"
        "- Provider `PRODUCT-01-T01` — Output: contract | signed.; "
        "Consumer `ARCH-01-T02` — Input: contract | signed for ARCH-01-T02.\n"
    )
    assert "\\|" not in appendix


@pytest.mark.parametrize("relative_path", ARTIFACT_PATHS)
@pytest.mark.parametrize("state", ["missing", "stale"])
def test_check_reports_each_missing_or_stale_artifact_separately(
    tmp_path: Path, relative_path: str, state: str
) -> None:
    write_tree(tmp_path)
    write_artifacts(tmp_path)
    target = tmp_path / relative_path
    if state == "missing":
        target.unlink()
    else:
        target.write_text(
            target.read_text(encoding="utf-8") + "stale\n", encoding="utf-8"
        )

    with pytest.raises(ValidationError, match=rf"{state} artifact: {relative_path}"):
        check_artifacts(tmp_path)


def test_check_treats_crlf_artifact_bytes_as_stale(tmp_path: Path) -> None:
    write_tree(tmp_path)
    write_artifacts(tmp_path)
    target = tmp_path / ARTIFACT_PATHS[1]
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))

    with pytest.raises(ValidationError, match=f"stale artifact: {ARTIFACT_PATHS[1]}"):
        check_artifacts(tmp_path)


def test_write_reread_rejects_crlf_byte_drift(tmp_path: Path) -> None:
    write_tree(tmp_path)

    def replace_with_crlf(source: str | Path, destination: str | Path) -> None:
        os.replace(source, destination)
        target = Path(destination)
        target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))

    with pytest.raises(
        ValidationError, match=f"artifact reread mismatch: {ARTIFACT_PATHS[0]}"
    ):
        write_artifacts(tmp_path, replace_func=replace_with_crlf)


def test_write_then_check_succeeds_for_complete_miniature_repository(
    tmp_path: Path,
) -> None:
    write_tree(tmp_path)

    write_artifacts(tmp_path)

    check_artifacts(tmp_path)
    assert all((tmp_path / relative).is_file() for relative in ARTIFACT_PATHS)


def test_second_replace_failure_fails_closed_and_later_write_repairs(
    tmp_path: Path,
) -> None:
    write_tree(tmp_path)
    calls = 0

    def fail_second(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second replacement failure")
        os.replace(source, destination)

    with pytest.raises(ValidationError, match="partially updated"):
        write_artifacts(tmp_path, replace_func=fail_second)
    assert calls == 2
    with pytest.raises(ValidationError):
        check_artifacts(tmp_path)

    write_artifacts(tmp_path)
    check_artifacts(tmp_path)


def test_cli_write_then_check_and_stale_failure_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_tree(tmp_path)

    assert main(["--write"], root=tmp_path) == 0
    assert main(["--check"], root=tmp_path) == 0
    target = tmp_path / ARTIFACT_PATHS[1]
    target.write_text(target.read_text(encoding="utf-8") + "stale\n", encoding="utf-8")
    assert main(["--check"], root=tmp_path) == 1
    assert f"stale artifact: {ARTIFACT_PATHS[1]}" in capsys.readouterr().err


@pytest.mark.parametrize("arguments", [[], ["--check", "--write"]])
def test_bad_cli_invocation_exits_two(tmp_path: Path, arguments: list[str]) -> None:
    write_tree(tmp_path)

    with pytest.raises(SystemExit) as error:
        main(arguments, root=tmp_path)

    assert error.value.code == 2


def test_cli_second_replace_failure_returns_one_then_repairs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_tree(tmp_path)
    real_replace = os.replace
    calls = 0

    def fail_second(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected CLI replacement failure")
        real_replace(source, destination)

    with monkeypatch.context() as scoped:
        scoped.setattr("scripts.validate_roadmap.os.replace", fail_second)
        assert main(["--write"], root=tmp_path) == 1
    assert main(["--check"], root=tmp_path) == 1
    assert main(["--write"], root=tmp_path) == 0
    assert main(["--check"], root=tmp_path) == 0


def test_real_repository_is_blocked_only_by_pending_metadata_migration() -> None:
    repository_root = Path(__file__).resolve().parents[3]

    with pytest.raises(ValidationError, match="adjacent metadata"):
        parse_roadmap(repository_root)
