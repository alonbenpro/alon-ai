"""Temporary test migration for the 2026-09-09 cost-first roadmap rewrite."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"
VALIDATOR = ROOT / "scripts/validate_roadmap.py"


def replace_block(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected one block, found {count}")
    return updated


def load_validator():
    spec = importlib.util.spec_from_file_location("cost_roadmap_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load roadmap validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    text = TESTS.read_text(encoding="utf-8")

    text = replace_block(
        text,
        r"def test_active_roadmap_uses_only_staged_thousand_lead_contract\(\) -> None:\n.*?\n\ndef test_staged_lead_source_validator_accepts_exact_authorities",
        '''def test_active_roadmap_uses_only_cost_first_contract() -> None:\n    repository_root = Path(__file__).resolve().parents[3]\n    roadmap_root = repository_root / "docs" / "development-roadmap"\n    active_paths = [roadmap_root / "README.md"]\n    active_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))\n    active_text = "\\n".join(path.read_text(encoding="utf-8") for path in active_paths)\n\n    for forbidden in (\n        "100/200/300/400",\n        "100/300/600/1,000",\n        "100/300/600/1000",\n    ):\n        assert forbidden not in active_text\n\n    for required in (\n        "SHADOW",\n        "REVIEW_20",\n        "QUALIFIED_50",\n        "SCALE_100_TO_300",\n        "BRAVE_PLACE_SEARCH",\n    ):\n        assert required in active_text\n\n\ndef test_staged_lead_source_validator_accepts_exact_authorities''',
        "active roadmap contract test",
    )

    text = replace_block(
        text,
        r"def test_staged_lead_source_validator_accepts_exact_authorities\(\n.*?\n\ndef write_tree",
        '''def _write_cost_first_authorities(tmp_path: Path) -> Path:\n    roadmap = tmp_path / "docs" / "development-roadmap"\n    product = roadmap / "00-product-strategy" / "01-product-scope.md"\n    metrics = roadmap / "00-product-strategy" / "02-success-metrics.md"\n    launch = roadmap / "12-launch-and-operations" / "03-first-real-experiment.md"\n    product.parent.mkdir(parents=True)\n    launch.parent.mkdir(parents=True)\n    stages = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300"\n    product.write_text(\n        stages\n        + '\\nBRAVE_PLACE_SEARCH'\n        + '\\n"model_routing_tiers": ["NO_AI", "NANO", "MINI", "PREMIUM"]'\n        + '\\n"pre_revenue_recipient_ceiling": 300\\n',\n        encoding="utf-8",\n    )\n    metrics.write_text(stages + "\\n", encoding="utf-8")\n    launch.write_text(stages + "\\n", encoding="utf-8")\n    return roadmap\n\n\ndef test_cost_first_source_validator_accepts_exact_authorities(tmp_path: Path) -> None:\n    _write_cost_first_authorities(tmp_path)\n    _validator.validate_staged_lead_contract(tmp_path)\n\n\ndef test_cost_first_source_validator_rejects_legacy_secondary_rule_with_location(\n    tmp_path: Path,\n) -> None:\n    roadmap = _write_cost_first_authorities(tmp_path)\n    (roadmap / "README.md").write_text(\n        "# Roadmap\\n100/200/300/400\\n", encoding="utf-8"\n    )\n\n    with pytest.raises(\n        ValidationError,\n        match=r"README\\.md:2: .*legacy automatic cohort authority",\n    ):\n        _validator.validate_staged_lead_contract(tmp_path)\n\n\ndef write_tree''',
        "source validator tests",
    )

    validator = load_validator()
    roadmap = validator.parse_roadmap(ROOT)
    fingerprint = validator.graph_fingerprint(roadmap)
    text, count = re.subn(
        r'(assert graph_fingerprint\(roadmap\) == \(\n\s+")[0-9a-f]{64}("\n\s+\))',
        rf'\g<1>{fingerprint}\g<2>',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("reviewed fingerprint assertion not found")

    TESTS.write_text(text, encoding="utf-8")
    print(f"cost-first roadmap tests patched for fingerprint {fingerprint}")


if __name__ == "__main__":
    main()
