from pathlib import Path

import pytest
from scripts.validate_roadmap import (
    ValidationError,
    parse_dependency_list,
    parse_manifest,
    parse_roadmap,
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


def test_manifest_data_row_has_exactly_two_cells(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            ROOT_ROW, "| `00-product/01-scope.md` | M0 | extra |"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="exactly two cells"):
        parse_manifest(tmp_path)


def test_manifest_extra_outer_delimiters_count_as_cells(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            ROOT_ROW, "|| `00-product/01-scope.md` | M0 ||"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="exactly two cells"):
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
