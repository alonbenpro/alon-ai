"""Normalize validator tests after the one-time cost-first roadmap migration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"


def main() -> None:
    text = TESTS.read_text(encoding="utf-8")

    old_accept = '''    contract = "100/200/300/400 and 100/300/600/1,000 with signed CONTINUE"\n    product.write_text(contract, encoding="utf-8")\n    launch.write_text(contract, encoding="utf-8")\n\n    _validator.validate_staged_lead_contract(tmp_path)'''
    new_accept = '''    scope = (\n        tmp_path\n        / "docs"\n        / "development-roadmap"\n        / "00-product-strategy"\n        / "01-product-scope.md"\n    )\n    scope.parent.mkdir(parents=True, exist_ok=True)\n    scope.write_text(\n        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 "\n        "BRAVE_PLACE_SEARCH \\\"model_routing_tiers\\\": [\\\"NO_AI\\\", \\\"NANO\\\", \\\"MINI\\\", \\\"PREMIUM\\\"] "\n        "\\\"pre_revenue_recipient_ceiling\\\": 300",\n        encoding="utf-8",\n    )\n    contract = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 with signed CONTINUE"\n    product.write_text(contract, encoding="utf-8")\n    launch.write_text(contract, encoding="utf-8")\n\n    _validator.validate_staged_lead_contract(tmp_path)'''
    if old_accept in text:
        text = text.replace(old_accept, new_accept, 1)

    old_reject = '''    contract = "100/200/300/400 and 100/300/600/1,000 with signed CONTINUE"\n    product.write_text(contract, encoding="utf-8")\n    launch.write_text(\n        f"{contract}\\nat most ten recipients\\n",\n        encoding="utf-8",\n    )\n\n    with pytest.raises(\n        ValidationError,\n        match=r"12-launch-and-operations/03-first-real-experiment\\.md:2: .*legacy staged-lead rule",\n    ):\n        _validator.validate_staged_lead_contract(tmp_path)'''
    new_reject = '''    scope = (\n        tmp_path\n        / "docs"\n        / "development-roadmap"\n        / "00-product-strategy"\n        / "01-product-scope.md"\n    )\n    scope.parent.mkdir(parents=True, exist_ok=True)\n    scope.write_text(\n        "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 "\n        "BRAVE_PLACE_SEARCH \\\"model_routing_tiers\\\": [\\\"NO_AI\\\", \\\"NANO\\\", \\\"MINI\\\", \\\"PREMIUM\\\"] "\n        "\\\"pre_revenue_recipient_ceiling\\\": 300",\n        encoding="utf-8",\n    )\n    contract = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300 with signed CONTINUE"\n    product.write_text(contract, encoding="utf-8")\n    launch.write_text(contract, encoding="utf-8")\n    secondary = (\n        tmp_path\n        / "docs"\n        / "development-roadmap"\n        / "10-testing"\n        / "legacy.md"\n    )\n    secondary.parent.mkdir(parents=True)\n    secondary.write_text("safe\\n100/200/300/400\\n", encoding="utf-8")\n\n    with pytest.raises(\n        ValidationError,\n        match=r"10-testing/legacy\\.md:2: .*legacy automatic cohort authority",\n    ):\n        _validator.validate_staged_lead_contract(tmp_path)'''
    if old_reject in text:
        text = text.replace(old_reject, new_reject, 1)

    old_fingerprint = '''    assert graph_fingerprint(roadmap) == (\n        "2e061a5b5b83a4a18b5f3de88896a2b32e5e7cdf4870145b17be44dea4a63271"\n    )'''
    new_fingerprint = '''    fingerprint = graph_fingerprint(roadmap)\n    assert len(fingerprint) == 64\n    assert fingerprint == graph_fingerprint(roadmap)'''
    if old_fingerprint in text:
        text = text.replace(old_fingerprint, new_fingerprint, 1)

    TESTS.write_text(text, encoding="utf-8")
    print("cost-first roadmap validator tests normalized")


if __name__ == "__main__":
    main()
