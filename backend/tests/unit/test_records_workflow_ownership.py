"""Structural contracts protecting the records and durable-command extraction."""

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "src" / "alon_ai"


@pytest.mark.parametrize(
    "name",
    [
        "records",
        "records_offer",
        "records_organization",
        "records_outreach",
        "records_qualification",
        "records_readiness",
        "records_calibration",
        "supply",
        "contact",
    ],
)
def test_record_tables_have_canonical_owners(name):
    assert (SOURCE / "db" / "tables" / f"{name}.py").is_file()


@pytest.mark.parametrize("name", ["market_research", "offer_design", "campaign_supply"])
def test_durable_workflows_do_not_execute_sql(name):
    tree = ast.parse((SOURCE / "workflows" / f"{name}.py").read_text())
    forbidden = {"execute", "scalar", "connect", "begin"}
    assert not [
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in forbidden
    ]
    assert not [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("alon_ai.db.repositories")
    ]


def test_workflow_registration_names_are_preserved():
    expected = {
        "market_research": {
            "start_market_research_business_command",
            "deliver_market_research_receipt",
            "idea_refinement_to_market_research",
            "commit_market_research_outcome_business_command",
            "deliver_market_research_outcome_receipt",
            "market_research_outcome",
            "decide_material_pivot_business_command",
            "start_inconclusive_supplement_business_command",
            "deliver_material_pivot_receipt",
            "deliver_inconclusive_supplement_receipt",
            "material_pivot_decision",
            "inconclusive_supplement",
        },
        "offer_design": {
            "offer_design_business_command",
            "deliver_offer_design_receipt",
            "offer_design_command",
        },
        "campaign_supply": {
            "campaign_supply_business_command",
            "deliver_campaign_supply_receipt",
            "campaign_supply_command",
        },
    }
    for module, names in expected.items():
        tree = ast.parse((SOURCE / "workflows" / f"{module}.py").read_text())
        actual = {
            keyword.value.value
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef)
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
            for keyword in decorator.keywords
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant)
        }
        assert actual == names


@pytest.mark.asyncio
async def test_workflow_engine_scope_disposes_after_failure():
    from alon_ai.bootstrap import workflow_engine_scope

    engine = None
    pool = None
    with pytest.raises(RuntimeError, match="step failed"):
        async with workflow_engine_scope() as scoped:
            engine = scoped
            pool = scoped.pool
            raise RuntimeError("step failed")
    assert engine is not None
    assert engine.pool is not pool
