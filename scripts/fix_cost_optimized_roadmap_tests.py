"""Normalize validator tests after the one-time cost-first roadmap migration."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"


def main() -> None:
    text = TESTS.read_text(encoding="utf-8")

    # Replace the two source-validator fixture tests as whole functions. This is
    # intentionally regex-based so it works regardless of earlier formatting edits.
    accept_pattern = re.compile(
        r"def test_staged_lead_source_validator_accepts_exact_authorities\(tmp_path: Path\) -> None:\n.*?(?=\ndef )",
        re.DOTALL,
    )
    accept_replacement = '''def test_staged_lead_source_validator_accepts_exact_authorities(tmp_path: Path) -> None:
    roadmap_root = tmp_path / "docs" / "development-roadmap"
    scope = roadmap_root / "00-product-strategy" / "01-product-scope.md"
    product = roadmap_root / "00-product-strategy" / "02-success-metrics.md"
    launch = roadmap_root / "12-launch-and-operations" / "03-first-real-experiment.md"
    scope.parent.mkdir(parents=True)
    launch.parent.mkdir(parents=True)
    scope.write_text(
        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 "
        "BRAVE_PLACE_SEARCH "
        '\\"model_routing_tiers\\": [\\"NO_AI\\", \\"NANO\\", \\"MINI\\", \\"PREMIUM\\"] '
        '\\"pre_revenue_recipient_ceiling\\": 300',
        encoding="utf-8",
    )
    contract = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 with signed CONTINUE"
    product.write_text(contract, encoding="utf-8")
    launch.write_text(contract, encoding="utf-8")

    _validator.validate_staged_lead_contract(tmp_path)

'''
    text, count = accept_pattern.subn(accept_replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"accept-authorities test replacement expected 1 match, got {count}")

    reject_pattern = re.compile(
        r"def test_staged_lead_source_validator_rejects_legacy_rule_with_location\(\n\s*tmp_path: Path,\n\) -> None:\n.*?(?=\ndef )",
        re.DOTALL,
    )
    reject_replacement = '''def test_staged_lead_source_validator_rejects_legacy_rule_with_location(
    tmp_path: Path,
) -> None:
    roadmap_root = tmp_path / "docs" / "development-roadmap"
    scope = roadmap_root / "00-product-strategy" / "01-product-scope.md"
    product = roadmap_root / "00-product-strategy" / "02-success-metrics.md"
    launch = roadmap_root / "12-launch-and-operations" / "03-first-real-experiment.md"
    secondary = roadmap_root / "10-testing" / "legacy.md"
    scope.parent.mkdir(parents=True)
    launch.parent.mkdir(parents=True)
    secondary.parent.mkdir(parents=True)
    scope.write_text(
        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 "
        "BRAVE_PLACE_SEARCH "
        '\\"model_routing_tiers\\": [\\"NO_AI\\", \\"NANO\\", \\"MINI\\", \\"PREMIUM\\"] '
        '\\"pre_revenue_recipient_ceiling\\": 300',
        encoding="utf-8",
    )
    contract = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 with signed CONTINUE"
    product.write_text(contract, encoding="utf-8")
    launch.write_text(contract, encoding="utf-8")
    secondary.write_text("safe\\n100/200/300/400\\n", encoding="utf-8")

    with pytest.raises(
        ValidationError,
        match=r"10-testing/legacy\\.md:2: .*legacy automatic cohort authority",
    ):
        _validator.validate_staged_lead_contract(tmp_path)

'''
    text, count = reject_pattern.subn(reject_replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"reject-legacy test replacement expected 1 match, got {count}")

    # Pin the reviewed cost-first graph fingerprint. The generator run preceding
    # pytest already established this exact value for the migrated branch.
    fingerprint_pattern = re.compile(
        r'''assert graph_fingerprint\(roadmap\) == \(\n\s*"[0-9a-f]{64}"\n\s*\)'''
    )
    fingerprint_replacement = '''assert graph_fingerprint(roadmap) == (
        "a6d8c772aa75769285732be8293438241d327586f72938fc718c0e314e35a2db"
    )'''
    text, count = fingerprint_pattern.subn(fingerprint_replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"graph fingerprint assertion replacement expected 1 match, got {count}")

    TESTS.write_text(text, encoding="utf-8")
    print("cost-first roadmap validator tests normalized")


if __name__ == "__main__":
    main()
