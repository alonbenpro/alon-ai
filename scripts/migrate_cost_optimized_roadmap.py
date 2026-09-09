"""One-time migration for the 2026-09-09 cost-optimized roadmap contract.

Run once on the cost-optimized-roadmap branch before regenerating roadmap artifacts.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_roadmap.py"
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def migrate_validator() -> None:
    text = VALIDATOR.read_text()
    text = replace_once(
        text,
        'STAGED_LEAD_SCHEDULE = (100, 200, 300, 400)\nSTAGED_LEAD_CUMULATIVE = (100, 300, 600, 1000)',
        'COST_FIRST_STAGE_NAMES = ("SHADOW", "REVIEW_20", "QUALIFIED_50", "SCALE_100_TO_300")\nSCALE_TRANCHE_MIN = 100\nSCALE_TRANCHE_MAX = 300',
        "constants",
    )
    old_fields = '''    no_mutation_learning_results: tuple[str, ...]\n    cohort_increments: tuple[int, ...]\n    cohort_cumulative_maxima: tuple[int, ...]\n    recipient_ceiling: int\n    send_writer: str'''
    new_fields = '''    no_mutation_learning_results: tuple[str, ...]\n    automated_discovery_provider: str\n    manual_evidence_sources: tuple[str, ...]\n    model_routing_tiers: tuple[str, ...]\n    premium_model_requires_explicit_approval: bool\n    batch_for_non_urgent_research: bool\n    launch_stages: tuple[dict[str, object], ...]\n    pre_revenue_recipient_ceiling: int\n    send_writer: str'''
    text = replace_once(text, old_fields, new_fields, "SalesContract fields")
    text = replace_once(
        text,
        '    schema_version="autonomous_sales_contract.v1",',
        '    schema_version="autonomous_sales_contract.v2",',
        "schema version",
    )
    old_tail = '''    no_mutation_learning_results=("KEEP", "INSUFFICIENT_EVIDENCE"),\n    cohort_increments=STAGED_LEAD_SCHEDULE,\n    cohort_cumulative_maxima=STAGED_LEAD_CUMULATIVE,\n    recipient_ceiling=1000,\n    send_writer="SendGateway",'''
    new_tail = '''    no_mutation_learning_results=("KEEP", "INSUFFICIENT_EVIDENCE"),\n    automated_discovery_provider="BRAVE_PLACE_SEARCH",\n    manual_evidence_sources=("SOCIAL_PROFILE", "PUBLIC_BUSINESS_PAGE"),\n    model_routing_tiers=("NO_AI", "NANO", "MINI", "PREMIUM"),\n    premium_model_requires_explicit_approval=True,\n    batch_for_non_urgent_research=True,\n    launch_stages=(\n        {"name": "SHADOW", "max_real_businesses": 0, "manual_review_required": False, "real_demand_learning": False},\n        {"name": "REVIEW_20", "max_real_businesses": 20, "manual_review_required": True, "real_demand_learning": True},\n        {"name": "QUALIFIED_50", "max_real_businesses": 50, "manual_review_required": False, "real_demand_learning": True},\n        {"name": "SCALE_100_TO_300", "min_real_businesses": 100, "max_real_businesses": 300, "manual_review_required": False, "real_demand_learning": True, "explicit_operator_authorization": True},\n    ),\n    pre_revenue_recipient_ceiling=300,\n    send_writer="SendGateway",'''
    text = replace_once(text, old_tail, new_tail, "expected contract tail")

    pattern = re.compile(r'def validate_staged_lead_contract\(root: Path\) -> None:\n.*?\n\ndef _logical_cells', re.S)
    replacement = '''def validate_staged_lead_contract(root: Path) -> None:\n    roadmap_root = root / "docs" / "development-roadmap"\n    authorities = (\n        roadmap_root / "00-product-strategy" / "01-product-scope.md",\n        roadmap_root / "00-product-strategy" / "02-success-metrics.md",\n        roadmap_root / "12-launch-and-operations" / "03-first-real-experiment.md",\n    )\n    if not all(path.is_file() for path in authorities):\n        return\n\n    required_tokens = (\n        "SHADOW",\n        "REVIEW_20",\n        "QUALIFIED_50",\n        "SCALE_100_TO_300",\n        "BRAVE_PLACE_SEARCH",\n    )\n    for path in authorities:\n        text = path.read_text(encoding="utf-8")\n        relative = path.relative_to(roadmap_root).as_posix()\n        for token in required_tokens[:4]:\n            if token not in text:\n                raise SourceLocation(relative, 1).error(\n                    f"cost-first launch authority is missing {token!r}"\n                )\n    product_text = authorities[0].read_text(encoding="utf-8")\n    if "BRAVE_PLACE_SEARCH" not in product_text:\n        raise SourceLocation(authorities[0].relative_to(roadmap_root).as_posix(), 1).error(\n            "cost-first discovery authority is missing Brave Place Search"\n        )\n\n    forbidden = (\n        "100/200/300/400",\n        "100/300/600/1,000",\n        "100/300/600/1000",\n        "recipient_ceiling=1000",\n        "cohort_increments",\n        "cohort_cumulative_maxima",\n    )\n    active_paths = [roadmap_root / "README.md"]\n    active_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))\n    for path in active_paths:\n        if not path.is_file():\n            continue\n        relative = path.relative_to(roadmap_root).as_posix()\n        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):\n            if any(token in line for token in forbidden):\n                raise SourceLocation(relative, line_number).error(\n                    "legacy 100/200/300/400 or 1,000-recipient authority is forbidden"\n                )\n\n\ndef _logical_cells'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"stage validation function: expected one match, found {count}")
    text = text.replace("exact v1 contract", "exact v2 contract")
    VALIDATOR.write_text(text)


def migrate_tests() -> None:
    text = TESTS.read_text()
    text = text.replace(
        '''def test_staged_lead_schedule_constants_are_exact() -> None:\n    assert _validator.STAGED_LEAD_SCHEDULE == (100, 200, 300, 400)\n    assert _validator.STAGED_LEAD_CUMULATIVE == (100, 300, 600, 1000)\n''',
        '''def test_cost_first_stage_constants_are_exact() -> None:\n    assert _validator.COST_FIRST_STAGE_NAMES == (\n        "SHADOW", "REVIEW_20", "QUALIFIED_50", "SCALE_100_TO_300"\n    )\n    assert _validator.SCALE_TRANCHE_MIN == 100\n    assert _validator.SCALE_TRANCHE_MAX == 300\n''',
    )
    text = text.replace('"autonomous_sales_contract.v1"', '"autonomous_sales_contract.v2"')
    text = text.replace('assert contract.cohort_increments == (100, 200, 300, 400)', 'assert tuple(stage["name"] for stage in contract.launch_stages) == _validator.COST_FIRST_STAGE_NAMES')
    text = text.replace('assert contract.cohort_cumulative_maxima == (100, 300, 600, 1000)', 'assert contract.pre_revenue_recipient_ceiling == 300')
    text = text.replace('assert contract.recipient_ceiling == 1000', 'assert contract.automated_discovery_provider == "BRAVE_PLACE_SEARCH"')
    TESTS.write_text(text)


if __name__ == "__main__":
    migrate_validator()
    migrate_tests()
    print("cost-optimized roadmap validator migration applied")
