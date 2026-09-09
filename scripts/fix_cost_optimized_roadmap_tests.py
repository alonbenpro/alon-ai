"""Normalize roadmap-validator tests after the cost-first contract migration."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"


def main() -> None:
    text = TESTS.read_text(encoding="utf-8")

    text = text.replace(
        "def test_staged_lead_schedule_constants_are_exact() -> None:\n"
        "    assert _validator.STAGED_LEAD_SCHEDULE == (100, 200, 300, 400)\n"
        "    assert _validator.STAGED_LEAD_CUMULATIVE == (100, 300, 600, 1000)\n",
        "def test_cost_first_stage_constants_are_exact() -> None:\n"
        "    assert _validator.COST_FIRST_STAGE_NAMES == (\n"
        "        \"SHADOW\", \"REVIEW_20\", \"QUALIFIED_50\", \"SCALE_100_TO_300\"\n"
        "    )\n"
        "    assert _validator.SCALE_TRANCHE_MIN == 100\n"
        "    assert _validator.SCALE_TRANCHE_MAX == 300\n",
    )

    active_pattern = re.compile(
        r"def test_active_roadmap_uses_only_staged_thousand_lead_contract\(\) -> None:\n.*?"
        r"(?=\ndef test_staged_lead_source_validator_accepts_exact_authorities)",
        re.S,
    )
    active_replacement = '''def test_active_roadmap_uses_cost_first_contract() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    roadmap_root = repository_root / "docs" / "development-roadmap"
    active_paths = [roadmap_root / "README.md"]
    active_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))
    active_text = "\\n".join(path.read_text(encoding="utf-8") for path in active_paths)

    for required in (
        "SHADOW",
        "REVIEW_20",
        "QUALIFIED_50",
        "SCALE_100_TO_300",
        "Brave Place Search",
        "Cloudflare Tunnel",
        "Cloudflare Access",
        "R2",
    ):
        assert required in active_text

'''
    text = active_pattern.sub(active_replacement, text, count=1)

    fixture_pattern = re.compile(
        r"def test_staged_lead_source_validator_accepts_exact_authorities\(\n.*?"
        r"(?=\ndef write_tree)",
        re.S,
    )
    fixture_replacement = '''def _write_minimal_cost_first_authorities(tmp_path: Path) -> Path:
    roadmap = tmp_path / "docs" / "development-roadmap"
    scope = roadmap / "00-product-strategy" / "01-product-scope.md"
    metrics = roadmap / "00-product-strategy" / "02-success-metrics.md"
    launch = roadmap / "12-launch-and-operations" / "03-first-real-experiment.md"
    scope.parent.mkdir(parents=True)
    launch.parent.mkdir(parents=True)
    authority = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300"
    scope.write_text(
        authority
        + ' BRAVE_PLACE_SEARCH "model_routing_tiers": ["NO_AI", "NANO", "MINI", "PREMIUM"]'
        + ' "pre_revenue_recipient_ceiling": 300',
        encoding="utf-8",
    )
    metrics.write_text(authority + " CONTINUE ScaleAuthorization", encoding="utf-8")
    launch.write_text(authority + " ScaleAuthorization 100..300", encoding="utf-8")
    return roadmap


def test_staged_lead_source_validator_accepts_exact_authorities(
    tmp_path: Path,
) -> None:
    _write_minimal_cost_first_authorities(tmp_path)
    _validator.validate_staged_lead_contract(tmp_path)


def test_staged_lead_source_validator_rejects_legacy_rule_with_location(
    tmp_path: Path,
) -> None:
    roadmap = _write_minimal_cost_first_authorities(tmp_path)
    readme = roadmap / "README.md"
    readme.write_text("# Roadmap\\n100/200/300/400\\n", encoding="utf-8")

    with pytest.raises(
        ValidationError,
        match=r"README\\.md:2: .*legacy automatic cohort authority",
    ):
        _validator.validate_staged_lead_contract(tmp_path)

'''
    text = fixture_pattern.sub(fixture_replacement, text, count=1)

    text = text.replace('"autonomous_sales_contract.v1"', '"autonomous_sales_contract.v2"')
    text = text.replace(
        'assert contract.cohort_increments == (100, 200, 300, 400)',
        'assert tuple(stage["name"] for stage in contract.launch_stages) == _validator.COST_FIRST_STAGE_NAMES',
    )
    text = text.replace(
        'assert contract.cohort_cumulative_maxima == (100, 300, 600, 1000)',
        'assert contract.pre_revenue_recipient_ceiling == 300',
    )
    text = text.replace(
        'assert contract.recipient_ceiling == 1000',
        'assert contract.automated_discovery_provider == "BRAVE_PLACE_SEARCH"',
    )

    old_mutations = '''        (("cohort_increments",), [100, 200, 300, 401], "cohort_increments"),
        (
            ("cohort_cumulative_maxima",),
            [100, 300, 600, 1001],
            "cohort_cumulative_maxima",
        ),
        (("recipient_ceiling",), 1001, "recipient_ceiling"),'''
    new_mutations = '''        (("automated_discovery_provider",), "GOOGLE_MAPS", "automated_discovery_provider"),
        (("manual_evidence_sources",), ["SOCIAL_PROFILE"], "manual_evidence_sources"),
        (("model_routing_tiers",), ["NANO", "MINI", "PREMIUM"], "model_routing_tiers"),
        (("premium_model_requires_explicit_approval",), False, "premium_model_requires_explicit_approval"),
        (("batch_for_non_urgent_research",), False, "batch_for_non_urgent_research"),
        (("launch_stages", 3, "max_real_businesses"), 301, "launch_stages"),
        (("pre_revenue_recipient_ceiling",), 301, "pre_revenue_recipient_ceiling"),'''
    text = text.replace(old_mutations, new_mutations)

    # The cost-first source graph produced by the migrated roadmap before this
    # normalizer is stable; test changes do not affect the roadmap fingerprint.
    text = text.replace(
        '"2e061a5b5b83a4a18b5f3de88896a2b32e5e7cdf4870145b17be44dea4a63271"',
        '"a6d8c772aa75769285732be8293438241d327586f72938fc718c0e314e35a2db"',
    )

    TESTS.write_text(text, encoding="utf-8")
    print("cost-first roadmap validator tests normalized")


if __name__ == "__main__":
    main()
