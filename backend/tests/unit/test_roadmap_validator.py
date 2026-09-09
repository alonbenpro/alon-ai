import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

# The repository script is outside the backend package and its import path.
_spec = spec_from_file_location(
    "_roadmap_validator_under_test",
    Path(__file__).resolve().parents[3] / "scripts" / "validate_roadmap.py",
)
assert _spec is not None and _spec.loader is not None
_validator = module_from_spec(_spec)
# Dataclasses resolve postponed annotations through the registered module.
sys.modules[_spec.name] = _validator
_spec.loader.exec_module(_validator)

ARTIFACT_PATHS = _validator.ARTIFACT_PATHS
Roadmap = _validator.Roadmap
ValidationError = _validator.ValidationError
Wave = _validator.Wave
build_waves = _validator.build_waves
canonical_fingerprint_bytes = _validator.canonical_fingerprint_bytes
graph_fingerprint = _validator.graph_fingerprint
parse_dependency_list = _validator.parse_dependency_list
parse_manifest = _validator.parse_manifest
render_agent_plan = _validator.render_agent_plan
render_execution_manifest = _validator.render_execution_manifest
render_execution_order = _validator.render_execution_order
topological_order = _validator.topological_order
validate_waves = _validator.validate_waves


# Existing miniature corpora test the structural parser and atomic artifact I/O.
# The public parser is separately exercised against the complete sales corpus below.
def parse_roadmap(root):
    return _validator.parse_task_graph(root)


def _structural_operation(operation, *args, **kwargs):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(_validator, "parse_roadmap", parse_roadmap)
        return operation(*args, **kwargs)


def write_artifacts(*args, **kwargs):
    return _structural_operation(_validator.write_artifacts, *args, **kwargs)


def check_artifacts(*args, **kwargs):
    return _structural_operation(_validator.check_artifacts, *args, **kwargs)


def main(*args, **kwargs):
    return _structural_operation(_validator.main, *args, **kwargs)


SALES_SOURCE = "docs/development-roadmap/00-product-strategy/01-product-scope.md"


def sales_contract_payload():
    source = (Path(__file__).resolve().parents[3] / SALES_SOURCE).read_text()
    return json.loads(re.search(r"```json\n(.*?)\n```", source, re.DOTALL).group(1))


def write_sales_contract(root, payload):
    target = root / SALES_SOURCE
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        source = target.read_text()
        source = re.sub(
            r"```json\n.*?\n```",
            lambda _: "```json\n" + json.dumps(payload) + "\n```",
            source,
            count=1,
            flags=re.DOTALL,
        )
    else:
        source = (
            "## Canonical autonomous sales contract\n\n```json\n"
            + json.dumps(payload)
            + "\n```\n"
        )
    target.write_text(source)


@pytest.fixture
def sales_tree(tmp_path):
    repository = Path(__file__).resolve().parents[3]
    shutil.copytree(
        repository / "docs/development-roadmap", tmp_path / "docs/development-roadmap"
    )
    return tmp_path


def test_sales_contract_parser_returns_deeply_immutable_typed_data(tmp_path):
    write_sales_contract(tmp_path, sales_contract_payload())
    contract = _validator.parse_sales_contract(tmp_path)
    assert contract.responsibilities[1].provider == "MarketResearchAgent"
    assert contract.artifacts[10].producer == "BookingGateway"
    assert contract.cohort_increments == (100, 200, 300, 400)
    with pytest.raises(FrozenInstanceError):
        contract.send_writer = "EmailWritingAgent"
    with pytest.raises(FrozenInstanceError):
        contract.responsibilities[0].provider = "OtherAgent"
    with pytest.raises(TypeError):
        contract.responsibilities[0].outputs[0] = "OtherArtifact"


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (("responsibilities", 1, "order"), 3, "responsibilities"),
        (("responsibilities", 1, "name"), "Offer Design", "responsibilities"),
        (("responsibilities", 1, "provider"), "OfferDesignAgent", "responsibilities"),
        (("responsibilities", 2, "inputs"), ["IdeaBrief"], "responsibilities"),
        (("responsibilities", 0, "inputs"), ["OfferPackage"], "responsibilities"),
        (("responsibilities", 7, "kind"), "agent", "responsibilities"),
        (
            ("responsibilities", 9, "kind"),
            "agent_with_deterministic_gate",
            "responsibilities",
        ),
        (
            ("responsibilities", 8, "gate_owner"),
            "ReplyEvaluationAgent",
            "responsibilities",
        ),
        (
            ("responsibilities", 9, "inputs"),
            ["OfferPackage", "ReplyEvaluation"],
            "responsibilities",
        ),
        (("responsibilities", 9, "outputs"), [], "responsibilities"),
        (("responsibilities", 11, "inputs"), ["EmailDraft"], "responsibilities"),
        (
            ("responsibilities", 4, "input_phases"),
            {"QualificationDecision": "FINAL"},
            "responsibilities",
        ),
        (("artifacts", 2, "producer"), "EmailWritingAgent", "artifacts"),
        (("artifacts", 5, "phases"), ["FINAL", "PRELIMINARY"], "artifacts"),
        (("artifacts", 9, "producer"), "ReplyEvaluationAgent", "artifacts"),
        (("artifacts", 10, "name"), "CalendarEvent", "artifacts"),
        (("commercial_authority",), "ConversationStrategy", "commercial_authority"),
        (("send_writer",), "EmailWritingAgent", "send_writer"),
        (("booking_writer",), "ReplyEvaluationAgent", "booking_writer"),
        (
            ("checkpoint_decisions",),
            ["CONTINUE", "REVISE", "KILL", "INCONCLUSIVE"],
            "checkpoint_decisions",
        ),
        (
            ("learning_results",),
            ["PROMOTE", "KEEP", "ROLLBACK", "INSUFFICIENT_EVIDENCE", "NO_CHANGE"],
            "learning_results",
        ),
        (("no_mutation_learning_results",), ["KEEP"], "no_mutation_learning_results"),
        (
            ("strategy_activation_boundary",),
            "ANY_ACTION",
            "strategy_activation_boundary",
        ),
        (("learning_trigger",), "ANY_REPLY", "learning_trigger"),
        (("active_cohort_mutation",), True, "active_cohort_mutation"),
        (("active_cohort_mutation",), 0, "active_cohort_mutation"),
        (("cohort_increments",), [100, 200, 300, 401], "cohort_increments"),
        (
            ("cohort_cumulative_maxima",),
            [100, 300, 600, 1001],
            "cohort_cumulative_maxima",
        ),
        (("recipient_ceiling",), 1001, "recipient_ceiling"),
        (("idea_origins",), ["DISCOVERED"], "idea_origins"),
        (("idea_bypass_materializer",), "OfferDesignAgent", "idea_bypass_materializer"),
    ],
)
def test_sales_contract_rejects_unsafe_semantic_mutations(
    sales_tree, path, value, reason
):
    payload = sales_contract_payload()
    cursor = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    write_sales_contract(sales_tree, payload)
    with pytest.raises(ValidationError, match=reason):
        _validator.parse_roadmap(sales_tree)


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "malformed", "duplicate-key", "unknown-key"]
)
def test_sales_contract_fails_closed_on_missing_or_ambiguous_authority(
    tmp_path, mutation
):
    write_sales_contract(tmp_path, sales_contract_payload())
    target = tmp_path / SALES_SOURCE
    source = target.read_text()
    if mutation == "missing":
        target.unlink()
    elif mutation == "duplicate":
        target.write_text(source + source)
    elif mutation == "malformed":
        target.write_text(source.replace('"responsibilities":', '"responsibilities"'))
    elif mutation == "duplicate-key":
        target.write_text(
            source.replace('"send_writer":', '"send_writer": "Agent", "send_writer":')
        )
    else:
        payload = sales_contract_payload()
        payload["allow_stale_activation"] = True
        write_sales_contract(tmp_path, payload)
    with pytest.raises(ValidationError, match="canonical sales contract"):
        _validator.parse_sales_contract(tmp_path)


def test_public_sales_parser_and_manifest_bind_complete_contract(sales_tree):
    roadmap = _validator.parse_roadmap(sales_tree)
    manifest = json.loads(render_execution_manifest(roadmap))
    assert manifest["sales_contract"]["send_writer"] == "SendGateway"
    assert manifest["sales_contract"]["learning_trigger"] == "CLOSED_CHECKPOINT"
    assert manifest["source_graph_fingerprint"] == graph_fingerprint(roadmap)
    assert manifest["manifest_documents"][0]["milestone"] == "M0"
    assert len(manifest["sales_contract"]["artifacts"]) == 15


def test_contract_and_document_gate_changes_affect_fingerprint(sales_tree):
    roadmap = _validator.parse_roadmap(sales_tree)
    changed = replace(
        roadmap,
        sales_contract=replace(roadmap.sales_contract, send_writer="OtherWriter"),
    )
    assert graph_fingerprint(changed) != graph_fingerprint(roadmap)
    changed = replace(
        roadmap,
        documents=(
            replace(roadmap.documents[0], milestone="M1"),
            *roadmap.documents[1:],
        ),
    )
    assert graph_fingerprint(changed) != graph_fingerprint(roadmap)
    changed = replace(
        roadmap,
        documents=(
            replace(roadmap.documents[0], gate_description="Changed gate"),
            *roadmap.documents[1:],
        ),
    )
    assert graph_fingerprint(changed) != graph_fingerprint(roadmap)


def test_public_sales_parser_rejects_document_gate_drift(sales_tree):
    readme = sales_tree / "docs/development-roadmap/README.md"
    readme.write_text(
        readme.read_text().replace(
            "`00-product-strategy/01-product-scope.md` | M0",
            "`00-product-strategy/01-product-scope.md` | M1",
        )
    )
    with pytest.raises(ValidationError, match="document gate"):
        _validator.parse_roadmap(sales_tree)


def test_sales_api_cannot_build_before_activation_and_booking_services(sales_tree):
    roadmap = _validator.parse_roadmap(sales_tree)
    task = next(task for task in roadmap.tasks if task.id == "BACKEND-02-T03")
    target = sales_tree / task.source
    target.write_text(
        re.sub(
            r"(<!-- roadmap-task id=BACKEND-02-T03 milestone=M6 depends_on=)[^ ]+",
            r"\g<1>PRODUCT-01-T01",
            target.read_text(),
        )
    )
    with pytest.raises(ValidationError, match="provider ancestor"):
        _validator.parse_roadmap(sales_tree)


def test_booking_service_requires_fresh_booking_policy_provider(sales_tree):
    roadmap = _validator.parse_roadmap(sales_tree)
    task = next(task for task in roadmap.tasks if task.id == "BACKEND-01-T08")
    target = sales_tree / task.source
    source = target.read_text()
    metadata = next(
        line
        for line in source.splitlines()
        if line.startswith("<!-- roadmap-task id=BACKEND-01-T08 ")
    )
    target.write_text(source.replace(metadata, metadata.replace(",BACKEND-03-T04", "")))
    with pytest.raises(ValidationError, match="provider ancestor.*BACKEND-03-T04"):
        _validator.parse_roadmap(sales_tree)


def test_idea_workflow_requires_materializer_before_accepted_artifacts(sales_tree):
    target = (
        sales_tree
        / "docs/development-roadmap/03-workflows/03-idea-validation-workflow.md"
    )
    source = target.read_text()
    metadata = next(
        line
        for line in source.splitlines()
        if line.startswith("<!-- roadmap-task id=WF-03-T02 ")
    )
    without_provider = metadata.replace(",BACKEND-01-T04", "")
    with_provider = without_provider.replace(" mode=", ",BACKEND-01-T04 mode=")
    target.write_text(source.replace(metadata, with_provider))
    _validator.parse_roadmap(sales_tree)

    target.write_text(source.replace(metadata, without_provider))
    with pytest.raises(
        ValidationError, match="WF-03-T02:.*provider ancestor BACKEND-01-T04"
    ):
        _validator.parse_roadmap(sales_tree)


def test_public_sales_parser_rejects_empty_manifest_document(sales_tree):
    target = sales_tree / "docs/development-roadmap/99-empty/01-empty.md"
    target.parent.mkdir()
    target.write_text(
        "# Empty\n**Document ID:** EMPTY-01\n## Ordered implementation tasks\n## Acceptance\n"
    )
    readme = sales_tree / "docs/development-roadmap/README.md"
    readme.write_text(
        readme.read_text().replace(
            "## Launch promotion ladder",
            "| `99-empty/01-empty.md` | M0 | Empty gate |\n\n## Launch promotion ladder",
        )
    )
    with pytest.raises(ValidationError, match="document.*no tasks"):
        _validator.parse_roadmap(sales_tree)


def test_rendered_contract_drift_fails_before_any_artifact_replacement(
    sales_tree, monkeypatch
):
    real_render = _validator.render_artifacts
    before = {
        relative: (sales_tree / relative).read_bytes() for relative in ARTIFACT_PATHS
    }

    def changed_contract(roadmap):
        contents = real_render(roadmap)
        manifest = json.loads(contents[ARTIFACT_PATHS[0]])
        manifest["sales_contract"]["booking_writer"] = "ReplyEvaluationAgent"
        contents[ARTIFACT_PATHS[0]] = json.dumps(manifest) + "\n"
        return contents

    monkeypatch.setattr(_validator, "render_artifacts", changed_contract)
    with pytest.raises(ValidationError, match="sales contract drift"):
        _validator.write_artifacts(sales_tree)
    assert {
        relative: (sales_tree / relative).read_bytes() for relative in ARTIFACT_PATHS
    } == before


@pytest.mark.parametrize(
    ("consumer", "provider"),
    [
        ("AGENT-03-T01", "AGENT-04-T01"),
        ("AGENT-05-T01", "AGENT-11-T01"),
        ("AGENT-11-T03", "PROVIDER-08-T03"),
        ("WF-04-T01", "BACKEND-01-T07"),
        ("WF-07-T01", "BACKEND-01-T08"),
        ("WF-08-T01", "BACKEND-01-T09"),
        ("WF-09-T01", "BACKEND-01-T10"),
    ],
)
def test_sales_dependencies_require_reachable_providers_even_when_sort_order_looks_safe(
    sales_tree, consumer, provider
):
    roadmap = _validator.parse_roadmap(sales_tree)
    tasks = {task.id: task for task in roadmap.tasks}
    # Remove every path to the provider from this consumer while keeping a valid DAG.
    target = sales_tree / tasks[consumer].source
    target.write_text(
        re.sub(
            r"(<!-- roadmap-task id=" + consumer + r" milestone=\w+ depends_on=)[^ ]+",
            r"\g<1>PRODUCT-01-T01",
            target.read_text(),
        )
    )
    structural = _validator.parse_task_graph(sales_tree)
    # Manifest/milestone tie breaks can put provider first; that is not a dependency.
    ordered = [task.id for task in topological_order(structural)]
    if tasks[provider].milestone < tasks[consumer].milestone:
        assert ordered.index(provider) < ordered.index(consumer)
    with pytest.raises(ValidationError, match="provider ancestor"):
        _validator.parse_roadmap(sales_tree)


@pytest.mark.parametrize("mutation", ["authority", "source", "strategy"])
def test_semantic_failure_cannot_replace_generated_artifacts(
    sales_tree, capsys, mutation
):
    for relative in ARTIFACT_PATHS:
        (sales_tree / relative).write_bytes(b"preserve existing evidence\n")
    if mutation == "authority":
        (sales_tree / SALES_SOURCE).unlink()
    elif mutation == "source":
        (
            sales_tree / "docs/development-roadmap/05-providers/07-calendar-provider.md"
        ).unlink()
    else:
        payload = sales_contract_payload()
        payload["active_cohort_mutation"] = True
        write_sales_contract(sales_tree, payload)
    assert _validator.main(["--write"], root=sales_tree) == 1
    assert "roadmap validation failed" in capsys.readouterr().err
    assert all(
        (sales_tree / relative).read_bytes() == b"preserve existing evidence\n"
        for relative in ARTIFACT_PATHS
    )


@pytest.mark.parametrize("mode", ["serial", "parallel"])
def test_calendar_write_lock_is_registered_and_serial_only(tmp_path, mode):
    roadmap = write_tree(tmp_path)
    target = roadmap / "00-product/01-scope.md"
    target.write_text(
        target.read_text()
        .replace("locks=product-contracts", "locks=calendar-side-effects")
        .replace("mode=parallel", "mode=" + mode)
    )
    if mode == "serial":
        assert parse_roadmap(tmp_path).tasks[0].locks == ("calendar-side-effects",)
    else:
        with pytest.raises(ValidationError, match="serial-only lock"):
            parse_roadmap(tmp_path)


ROOT_ROW = "| `00-product/01-scope.md` | M0 |"
ROOT_META = "<!-- roadmap-task id=PRODUCT-01-T01 milestone=M0 depends_on=- mode=parallel locks=product-contracts -->"
ROOT_BOX = "- [ ] **Capture scope —** Input: brief. Operation: freeze. Output: contract. Test evidence: review. Failure behavior: block."


def test_staged_lead_schedule_constants_are_exact() -> None:
    assert _validator.STAGED_LEAD_SCHEDULE == (100, 200, 300, 400)
    assert _validator.STAGED_LEAD_CUMULATIVE == (100, 300, 600, 1000)


def test_active_roadmap_uses_only_staged_thousand_lead_contract() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    roadmap_root = repository_root / "docs" / "development-roadmap"
    active_paths = [roadmap_root / "README.md"]
    active_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))
    active_text = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)

    for forbidden in (
        "at most ten recipients",
        "one-to-ten",
        "10-total",
        "11th recipient",
        "50 delivered unique recipients",
    ):
        assert forbidden not in active_text

    assert "100/200/300/400" in active_text
    assert "100/300/600/1,000" in active_text


def test_staged_lead_source_validator_accepts_exact_authorities(
    tmp_path: Path,
) -> None:
    product = (
        tmp_path
        / "docs"
        / "development-roadmap"
        / "00-product-strategy"
        / "02-success-metrics.md"
    )
    launch = (
        tmp_path
        / "docs"
        / "development-roadmap"
        / "12-launch-and-operations"
        / "03-first-real-experiment.md"
    )
    product.parent.mkdir(parents=True)
    launch.parent.mkdir(parents=True)
    contract = "100/200/300/400 and 100/300/600/1,000 with signed CONTINUE"
    product.write_text(contract, encoding="utf-8")
    launch.write_text(contract, encoding="utf-8")

    _validator.validate_staged_lead_contract(tmp_path)


def test_staged_lead_source_validator_rejects_legacy_rule_with_location(
    tmp_path: Path,
) -> None:
    product = (
        tmp_path
        / "docs"
        / "development-roadmap"
        / "00-product-strategy"
        / "02-success-metrics.md"
    )
    launch = (
        tmp_path
        / "docs"
        / "development-roadmap"
        / "12-launch-and-operations"
        / "03-first-real-experiment.md"
    )
    product.parent.mkdir(parents=True)
    launch.parent.mkdir(parents=True)
    contract = "100/200/300/400 and 100/300/600/1,000 with signed CONTINUE"
    product.write_text(contract, encoding="utf-8")
    launch.write_text(
        f"{contract}\nat most ten recipients\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match=r"12-launch-and-operations/03-first-real-experiment\.md:2: .*legacy staged-lead rule",
    ):
        _validator.validate_staged_lead_contract(tmp_path)


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


def test_make_test_runs_roadmap_gate_first() -> None:
    result = subprocess.run(
        ["make", "--no-print-directory", "-n", "test"],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.splitlines() == [
        "python3 scripts/validate_roadmap.py --check",
        "cd backend && uv run pytest tests/unit -q",
        "npm --prefix frontend test -- --run",
    ]


@pytest.mark.parametrize("operation", ["parse", "--check", "--write"])
def test_omitted_leaf_manifest_row_rejects_before_artifact_replacement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], operation: str
) -> None:
    roadmap = write_tree(tmp_path)
    write_artifacts(tmp_path)
    add_document(
        roadmap,
        relative="01-arch/01-system.md",
        document_id="ARCH-01",
        milestone="M0",
        tasks=[("ARCH-01-T01", "PRODUCT-01-T01", "parallel", "architecture-contracts")],
    )
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "| `01-arch/01-system.md` | M0 |\n", ""
        ),
        encoding="utf-8",
    )
    if operation == "--write":
        for relative in ARTIFACT_PATHS:
            (tmp_path / relative).write_bytes(f"preserve {relative}\n".encode())
    before = {
        relative: (tmp_path / relative).read_bytes() for relative in ARTIFACT_PATHS
    }

    if operation == "parse":
        with pytest.raises(ValidationError, match="missing.*01-arch/01-system.md"):
            parse_roadmap(tmp_path)
    else:
        assert main([operation], root=tmp_path) == 1
        assert "missing" in capsys.readouterr().err
    assert {
        relative: (tmp_path / relative).read_bytes() for relative in ARTIFACT_PATHS
    } == before


def test_manifest_reports_sorted_missing_and_extra_corpus_paths(tmp_path: Path) -> None:
    roadmap = write_tree(tmp_path)
    for relative in ("02-extra/01-last.md", "01-extra/01-first.md"):
        target = roadmap / relative
        target.parent.mkdir()
        target.write_text("## Ordered implementation tasks\n", encoding="utf-8")
    (roadmap / "00-product/01-scope.md").write_text("# Notes\n", encoding="utf-8")

    with pytest.raises(ValidationError) as error:
        parse_manifest(tmp_path)

    message = str(error.value)
    assert "missing" in message and "extra" in message
    assert message.index("01-extra/01-first.md") < message.index("02-extra/01-last.md")
    assert "00-product/01-scope.md" in message


@pytest.mark.parametrize(
    "relative", ["00-product/notes.md", "00-product/nested/extra.md"]
)
def test_corpus_discovery_covers_task_sections_below_numbered_top_directory(
    tmp_path: Path, relative: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / relative
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text("## Ordered implementation tasks\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="missing manifest paths") as error:
        parse_manifest(tmp_path)

    assert relative in str(error.value)


def test_corpus_discovery_ignores_reference_docs_and_generated_artifacts(
    tmp_path: Path,
) -> None:
    roadmap = write_tree(tmp_path)
    for relative, content in (
        ("00-product/02-notes.md", "# Notes\n"),
        ("reference/01-example.md", "## Ordered implementation tasks\n"),
        ("EXECUTION_ORDER.md", "## Ordered implementation tasks\n"),
    ):
        document = roadmap / relative
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(content, encoding="utf-8")

    assert len(parse_manifest(tmp_path)) == 1


@pytest.mark.parametrize(
    ("old", "new", "line", "task_id", "reason"),
    [
        ("**Document ID:** PRODUCT-01", "**Document ID:** bad", 3, None, "document ID"),
        ("milestone=M0", "milestone=MX", 8, "PRODUCT-01-T01", "task milestone"),
        ("mode=parallel", "mode=bad", 8, "PRODUCT-01-T01", "execution mode"),
        ("locks=product-contracts", "locks=bad", 8, "PRODUCT-01-T01", "unknown lock"),
        (" locks=", " extra=", 7, "PRODUCT-01-T01", "malformed task metadata"),
        (
            "id=PRODUCT-01-T01 milestone=M0",
            "milestone=M0 id=PRODUCT-01-T01",
            7,
            "PRODUCT-01-T01",
            "malformed task metadata",
        ),
        ("Input:", "Inputs:", 8, "PRODUCT-01-T01", "task clause"),
        (
            "Test evidence: review.",
            "Test evidence: Command:",
            8,
            "PRODUCT-01-T01",
            "singular Command",
        ),
    ],
)
def test_source_diagnostics_preserve_location_and_task_context(
    tmp_path: Path, old: str, new: str, line: int, task_id: str | None, reason: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product/01-scope.md"
    document.write_text(
        document.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
    )

    with pytest.raises(ValidationError, match=reason) as error:
        parse_roadmap(tmp_path)

    assert f"docs/development-roadmap/00-product/01-scope.md:{line}:" in str(
        error.value
    )
    if task_id is not None:
        assert task_id in str(error.value)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize("depends", ["UNKNOWN-01-T01", "PRODUCT-01-T02"])
def test_dependency_diagnostics_preserve_consumer_source_context(
    tmp_path: Path, depends: str
) -> None:
    roadmap = write_tree(tmp_path)
    append_second(roadmap, depends=depends)

    with pytest.raises(ValidationError, match="dependency") as error:
        parse_roadmap(tmp_path)

    assert "docs/development-roadmap/00-product/01-scope.md:11:" in str(error.value)
    assert "PRODUCT-01-T02" in str(error.value)


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


@pytest.mark.parametrize(
    ("old", "new", "line", "reason"),
    [
        (
            "## Complete file manifest mapped to vertical gates",
            "## Wrong",
            1,
            "manifest heading",
        ),
        (
            "## Launch promotion ladder",
            "## Complete file manifest mapped to vertical gates",
            9,
            "manifest heading",
        ),
        (
            "## Launch promotion ladder",
            "### No closing boundary",
            3,
            "closing boundary",
        ),
        (
            "## Launch promotion ladder",
            f"## Launch promotion ladder\n{ROOT_ROW}",
            10,
            "outside manifest",
        ),
        (ROOT_ROW, "|| `00-product/01-scope.md` | M0 ||", 7, "outer delimiters"),
        (ROOT_ROW, "| `00-product/01-scope.md` |", 7, "requires path and milestone"),
        (ROOT_ROW, "| `00-product/01-scope.md` | |", 7, "manifest milestone"),
        (ROOT_ROW, "| bad/path | M0 |", 7, "manifest path"),
        (ROOT_ROW, "| `00-product/01-scope.md` | MZ |", 7, "manifest milestone"),
        (ROOT_ROW, f"{ROOT_ROW}\n{ROOT_ROW}", 8, "duplicate manifest path"),
    ],
)
def test_manifest_diagnostics_include_exact_readme_location(
    tmp_path: Path, old: str, new: str, line: int, reason: str
) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
    )

    with pytest.raises(ValidationError, match=reason) as error:
        parse_manifest(tmp_path)

    assert f"docs/development-roadmap/README.md:{line}:" in str(error.value)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize("mutation", ["missing", "escaped"])
def test_manifest_document_diagnostics_include_row_and_target(
    tmp_path: Path, mutation: str
) -> None:
    roadmap = write_tree(tmp_path)
    document = roadmap / "00-product/01-scope.md"
    document.unlink()
    if mutation == "escaped":
        outside = tmp_path / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        document.symlink_to(outside)

    with pytest.raises(ValidationError) as error:
        parse_manifest(tmp_path)

    assert "docs/development-roadmap/README.md:7:" in str(error.value)
    assert "00-product/01-scope.md" in str(error.value)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_cli_manifest_milestone_diagnostic_retains_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    roadmap = write_tree(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("| M0 |", "| MZ |"), encoding="utf-8"
    )

    assert main([mode], root=tmp_path) == 1
    assert "docs/development-roadmap/README.md:7:" in capsys.readouterr().err


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
    ) as error:
        topological_order(parsed)

    assert "docs/development-roadmap/01-arch/01-system.md:8:" in str(error.value)


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

    with pytest.raises(ValidationError, match="current-wave dependency") as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/01-arch/01-system.md:10: ARCH-01-T02:" in str(
        error.value
    )


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

    with pytest.raises(ValidationError, match="milestone crossing") as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/01-arch/01-system.md:8: ARCH-01-T01:" in str(
        error.value
    )


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

    with pytest.raises(ValidationError, match="shared lock") as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/01-arch/01-system.md:10: ARCH-01-T02:" in str(
        error.value
    )


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

    with pytest.raises(ValidationError, match="serial task must be alone") as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/01-arch/01-system.md:8: ARCH-01-T01:" in str(
        error.value
    )


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

    with pytest.raises(ValidationError, match="at most four implementers") as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/01-arch/01-system.md:16: ARCH-01-T05:" in str(
        error.value
    )


def test_wave_validation_rejects_missing_task(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)

    with pytest.raises(ValidationError, match="missing task") as error:
        validate_waves(roadmap, waves[:-1])

    assert "docs/development-roadmap/01-arch/01-system.md:16: ARCH-01-T05:" in str(
        error.value
    )


def test_wave_validation_rejects_duplicate_task(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    invalid = waves + (replace(waves[0], index=4, newly_unlocked=()),)

    with pytest.raises(ValidationError, match="duplicate task") as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/00-product/01-scope.md:8: PRODUCT-01-T01:" in str(
        error.value
    )


def test_wave_validation_rejects_agent_assignment_drift(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    assignment = replace(waves[1].assignments[0], implementer="I2")
    invalid_wave = replace(
        waves[1], assignments=(assignment, *waves[1].assignments[1:])
    )

    with pytest.raises(ValidationError, match="agent assignment drift") as error:
        validate_waves(roadmap, (waves[0], invalid_wave, waves[2]))

    assert "docs/development-roadmap/01-arch/01-system.md:8: ARCH-01-T01:" in str(
        error.value
    )


def test_wave_validation_rejects_merge_order_drift(tmp_path: Path) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    assignment = replace(waves[1].assignments[0], merge_order=2)
    invalid_wave = replace(
        waves[1], assignments=(assignment, *waves[1].assignments[1:])
    )

    with pytest.raises(ValidationError, match="merge-order drift") as error:
        validate_waves(roadmap, (waves[0], invalid_wave, waves[2]))

    assert "docs/development-roadmap/01-arch/01-system.md:8: ARCH-01-T01:" in str(
        error.value
    )


def test_wave_validation_requires_dependencies_in_earlier_waves(
    tmp_path: Path,
) -> None:
    roadmap = write_chain_tree(tmp_path)
    first, second, third = build_waves(roadmap)

    with pytest.raises(
        ValidationError, match="dependency from an earlier wave"
    ) as error:
        validate_waves(roadmap, (first, third, second))

    assert "docs/development-roadmap/01-arch/01-system.md:10: ARCH-01-T02:" in str(
        error.value
    )


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

    with pytest.raises(ValidationError, match="milestone skipping") as error:
        validate_waves(roadmap, (first, third, second))

    assert "docs/development-roadmap/02-data/01-schema.md:8: DATA-01-T01:" in str(
        error.value
    )


@pytest.mark.parametrize("mutation", ["unknown", "schedule", "empty"])
def test_supplied_wave_plan_errors_include_artifact_row_context(
    tmp_path: Path, mutation: str
) -> None:
    roadmap = write_wave_tree(tmp_path)
    waves = build_waves(roadmap)
    if mutation == "unknown":
        assignment = replace(
            waves[0].assignments[0], task=replace(roadmap.tasks[0], id="UNKNOWN-01-T01")
        )
        invalid = (*waves, replace(waves[0], index=4, assignments=(assignment,)))
        row = 4
    elif mutation == "empty":
        invalid = (*waves, replace(waves[0], index=4, assignments=()))
        row = 4
    else:
        invalid = (replace(waves[0], newly_unlocked=()), *waves[1:])
        row = 1

    with pytest.raises(ValidationError) as error:
        validate_waves(roadmap, invalid)

    assert "docs/development-roadmap/AGENT_EXECUTION_PLAN.md" in str(error.value)
    assert f"wave row {row}" in str(error.value)
    if mutation == "unknown":
        assert "UNKNOWN-01-T01" in str(error.value)


def test_blocked_milestone_schedule_includes_owning_task_location(
    tmp_path: Path,
) -> None:
    roadmap = write_chain_tree(tmp_path)
    invalid = replace(
        roadmap, tasks=(replace(roadmap.tasks[0], milestone="M1"), *roadmap.tasks[1:])
    )

    with pytest.raises(ValidationError, match="no ready task") as error:
        build_waves(invalid)

    assert "docs/development-roadmap/01-arch/01-system.md:8: ARCH-01-T01:" in str(
        error.value
    )


@pytest.mark.parametrize(
    ("mutation", "artifact", "reason"),
    [
        ("set", ARTIFACT_PATHS[1], "invalid artifact set"),
        ("newline", ARTIFACT_PATHS[1], "final newline"),
        ("unicode", ARTIFACT_PATHS[1], "UTF-8/JSON"),
        ("json", ARTIFACT_PATHS[0], "UTF-8/JSON"),
        ("order", ARTIFACT_PATHS[0], "task order drift"),
        ("escape", ARTIFACT_PATHS[1], "link escapes"),
        ("missing", ARTIFACT_PATHS[1], "link target is missing"),
        ("line", ARTIFACT_PATHS[1], "link line is invalid"),
    ],
)
def test_generated_artifact_diagnostics_include_owning_path_and_line(
    tmp_path: Path, mutation: str, artifact: str, reason: str
) -> None:
    write_tree(tmp_path)
    roadmap = parse_roadmap(tmp_path)
    contents = _validator.render_artifacts(roadmap)
    line = 1
    if mutation == "set":
        contents.pop(artifact)
    elif mutation == "newline":
        contents[artifact] = "# No final newline"
    elif mutation == "unicode":
        contents[artifact] = "# Header\n\ud800\n"
        line = 2
    elif mutation == "json":
        contents[artifact] = "\ninvalid JSON\n"
        line = 2
    elif mutation == "order":
        contents[artifact] = '{"tasks": []}\n'
    else:
        target = {
            "escape": "../escape.md#L1",
            "missing": "00-product/02-missing.md#L1",
            "line": "00-product/01-scope.md#L999",
        }[mutation]
        contents[artifact] = f"# Header\n[source]({target})\n"
        line = 2

    with pytest.raises(ValidationError, match=reason) as error:
        _validator._validate_rendered_artifacts(tmp_path, roadmap, contents)

    assert f"{artifact}:{line}:" in str(error.value)


def test_canonical_fingerprint_bytes_and_digest_are_exact(tmp_path: Path) -> None:
    write_tree(tmp_path)
    roadmap = parse_roadmap(tmp_path)
    expected = (
        b'{"manifest_documents":[{"gate_description":"","milestone":"M0",'
        b'"source":"docs/development-roadmap/00-product/01-scope.md"}],'
        b'"milestones":["M0","M1","M2","M3","M4","M5","M6","M7","M8","M9"],'
        b'"root_task_ids":["PRODUCT-01-T01"],"sales_contract":null,"schema_version":2,"tasks":['
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
  "manifest_documents": [
    {
      "gate_description": "",
      "milestone": "M0",
      "source": "docs/development-roadmap/00-product/01-scope.md"
    }
  ],
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
  "sales_contract": null,
  "schema_version": 2,
  "source_graph_fingerprint": "f4ef5d9ca474df829a4142978bbcccbef32c08dbdd677f4a9f02eb94e917637e",
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
- Source-graph fingerprint: `f4ef5d9ca474df829a4142978bbcccbef32c08dbdd677f4a9f02eb94e917637e`

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

- Source-graph fingerprint: `f4ef5d9ca474df829a4142978bbcccbef32c08dbdd677f4a9f02eb94e917637e`
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
        scoped.setattr(_validator.os, "replace", fail_second)
        assert main(["--write"], root=tmp_path) == 1
    assert main(["--check"], root=tmp_path) == 1
    assert main(["--write"], root=tmp_path) == 0
    assert main(["--check"], root=tmp_path) == 0


def test_real_repository_source_graph_matches_reviewed_contract() -> None:
    repository_root = Path(__file__).resolve().parents[3]

    roadmap = _validator.parse_roadmap(repository_root)
    ordered = topological_order(roadmap)
    waves = build_waves(roadmap)
    validate_waves(roadmap, waves)
    tasks_by_id = {task.id: task for task in roadmap.tasks}
    cross_document_dependency_pairs = tuple(
        (dependency, task.id)
        for task in roadmap.tasks
        for dependency in task.depends_on
        if tasks_by_id[dependency].document_id != task.document_id
    )

    assert len(roadmap.documents) == 84
    assert len(roadmap.tasks) == 438
    assert len(ordered) == 438
    assert tuple(task.id for task in roadmap.tasks if not task.depends_on) == (
        "PRODUCT-01-T01",
    )
    assert len(waves) == 394
    assert max(len(wave.assignments) for wave in waves) == 4
    assert len(cross_document_dependency_pairs) == 926
    assert graph_fingerprint(roadmap) == (
        "2e061a5b5b83a4a18b5f3de88896a2b32e5e7cdf4870145b17be44dea4a63271"
    )
