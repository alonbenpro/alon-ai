"""Finish one-time cost-roadmap validator-test migration.

Temporary helper removed by the migration workflow after a green run.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"


def main() -> None:
    text = TESTS.read_text(encoding="utf-8")

    # The old location test used an obsolete contract string and expected the old
    # error wording. Make the fixture otherwise-valid under the new authority and
    # add one forbidden legacy line in LAUNCH-03 so location reporting is tested.
    pattern = re.compile(
        r'''def test_staged_lead_source_validator_rejects_legacy_rule_with_location\(\n    tmp_path: Path,\n\) -> None:\n.*?\n\n(?=def )''',
        re.DOTALL,
    )
    replacement = '''def test_staged_lead_source_validator_rejects_legacy_rule_with_location(
    tmp_path: Path,
) -> None:
    roadmap_root = tmp_path / "docs" / "development-roadmap"
    product_scope = roadmap_root / "00-product-strategy" / "01-product-scope.md"
    product_metrics = roadmap_root / "00-product-strategy" / "02-success-metrics.md"
    launch = roadmap_root / "12-launch-and-operations" / "03-first-real-experiment.md"
    product_scope.parent.mkdir(parents=True)
    launch.parent.mkdir(parents=True)

    product_scope.write_text(
        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 "
        "BRAVE_PLACE_SEARCH "
        '\\"model_routing_tiers\\": [\\"NO_AI\\", \\"NANO\\", \\"MINI\\", \\"PREMIUM\\"] '
        '\\"pre_revenue_recipient_ceiling\\": 300',
        encoding="utf-8",
    )
    product_metrics.write_text(
        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 CONTINUE ScaleAuthorization",
        encoding="utf-8",
    )
    launch.write_text(
        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 ScaleAuthorization\\n"
        "100/200/300/400\\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValidationError,
        match=r"12-launch-and-operations/03-first-real-experiment\\.md:2: .*legacy automatic cohort authority",
    ):
        _validator.validate_staged_lead_contract(tmp_path)


'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"legacy-location test replacement expected 1 match, got {count}")

    # Keep the reviewed graph invariant exact, but update it to the fingerprint
    # produced by this cost-first source graph. This still detects accidental graph
    # drift in later edits.
    text, count = re.subn(
        r'''assert graph_fingerprint\(roadmap\) == \(\n        "[0-9a-f]{64}"\n    \)''',
        '''assert graph_fingerprint(roadmap) == (
        "a6d8c772aa75769285732be8293438241d327586f72938fc718c0e314e35a2db"
    )''',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"graph fingerprint assertion replacement expected 1 match, got {count}")

    TESTS.write_text(text, encoding="utf-8")
    print("cost-first validator test expectations repaired")


if __name__ == "__main__":
    main()
