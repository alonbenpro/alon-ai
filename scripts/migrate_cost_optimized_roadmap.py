"""One-time migration for the 2026-09-09 cost-optimized roadmap contract.

The temporary workflow runs this once, regenerates roadmap artifacts, verifies them,
then removes this script and both temporary workflows before committing the result.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_roadmap.py"
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"
ROADMAP = ROOT / "docs/development-roadmap"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def migrate_secondary_roadmap_docs() -> None:
    """Remove legacy numeric-stage authority and normalize metadata locks."""
    primary = {
        "00-product-strategy/01-product-scope.md",
        "00-product-strategy/02-success-metrics.md",
        "12-launch-and-operations/03-first-real-experiment.md",
        "12-launch-and-operations/04-earned-autonomy.md",
    }
    replacements = (
        ("`100/200/300/400`", "`SHADOW/REVIEW_20/QUALIFIED_50/SCALE_100_TO_300`"),
        ("100/200/300/400", "SHADOW/REVIEW_20/QUALIFIED_50/SCALE_100_TO_300"),
        ("`100/300/600/1,000`", "`0/20/50/explicitly-authorized-100-to-300`"),
        ("100/300/600/1,000", "0/20/50/explicitly-authorized-100-to-300"),
        ("100/300/600/1000", "0/20/50/explicitly-authorized-100-to-300"),
        ("1,000-recipient", "pre-revenue 300-business"),
        ("1,000 recipient", "pre-revenue 300-business"),
        ("1,000 ceiling", "pre-revenue 300-business ceiling"),
        ("cumulative 1,000", "authorized pre-revenue maximum 300"),
        ("cumulative `1,000`", "authorized pre-revenue maximum `300`"),
        ("fifth cohort", "unapproved post-scale stage"),
        ("four-cohort", "cost-first staged"),
        ("four cohort", "cost-first stage"),
        ("locks=observability", "locks=telemetry-catalog"),
        (",observability", ",telemetry-catalog"),
    )
    paths = sorted(ROADMAP.glob("[0-9][0-9]-*/*.md")) + [ROADMAP / "README.md"]
    for path in paths:
        rel = path.relative_to(ROADMAP).as_posix()
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            if rel in primary and old not in {"locks=observability", ",observability"}:
                continue
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def migrate_security_secret_boundary() -> None:
    path = ROADMAP / "08-security-and-compliance/03-secrets-and-oauth-token-security.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "The initial production adapter is the deployment provider's managed KMS plus versioned secret manager selected in M8 infrastructure review; "
        "local development uses an ephemeral encrypted fixture store containing fake tokens only. No Gmail pilot starts until the chosen adapter passes "
        "the CAS/lease/restart/backup tests. This avoids operating a Vault cluster alone and avoids weakening the external versioned-object contract to plaintext files."
    )
    new = (
        "The pre-revenue production adapter is provider-neutral and must satisfy the same versioned encrypted-object, CAS, lease, revoke, rotation and restore contract using least-privilege encrypted local secret material plus separately held off-host recovery material. "
        "A managed KMS/secret manager may replace that adapter after revenue or a measured security/operations review, but it is not an M8 prerequisite. Local development uses an ephemeral encrypted fixture store containing fake tokens only. No Gmail pilot starts until the selected adapter passes the CAS/lease/restart/backup tests; plaintext production secret files are never an accepted fallback."
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif "pre-revenue production adapter" not in text:
        raise RuntimeError("SEC-03 pre-revenue adapter paragraph is neither old nor migrated")
    replacements = (
        (
            "Key hierarchy is: offline recovery wrapping key -> managed KMS root/KEK generation -> purpose-specific KEKs",
            "Key hierarchy is: offline recovery wrapping key -> versioned pre-revenue root/KEK generation (or a later managed-KMS adapter) -> purpose-specific KEKs",
        ),
        (
            "Production KEKs are non-exportable where the provider supports it.",
            "Production KEKs are protected by the selected adapter; when a later provider supports non-exportable keys, prefer that property after the architecture/cost review.",
        ),
        (
            "KMS configuration and recovery material are exported only as provider-supported wrapped/escrow artifacts;",
            "Key configuration and recovery material are retained only as encrypted/wrapped recovery artifacts;",
        ),
        (
            "KMS/secret-manager operation and storage prices enter DB-05 `cost_entries` where attributable;",
            "Secret-store/encryption operation and storage prices enter DB-05 `cost_entries` where attributable;",
        ),
        (
            "build strict models/ports and managed adapter with authenticated encryption and least workload identity.",
            "build strict models/ports and a cost-first encrypted adapter with authenticated encryption and least workload identity; preserve a replaceable seam for a later managed adapter.",
        ),
        (
            "Output: versioned strict secret/key/object models, managed-adapter ports and authenticated-encryption contract plus versioned encrypted objects.",
            "Output: versioned strict secret/key/object models, replaceable adapter ports and authenticated-encryption contract plus versioned encrypted objects.",
        ),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    path.write_text(text, encoding="utf-8")


def migrate_validator() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
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

    pattern = re.compile(
        r'def validate_staged_lead_contract\(root: Path\) -> None:\n.*?\n\ndef _logical_cells',
        re.S,
    )
    replacement = '''def validate_staged_lead_contract(root: Path) -> None:\n    roadmap_root = root / "docs" / "development-roadmap"\n    authorities = (\n        roadmap_root / "00-product-strategy" / "01-product-scope.md",\n        roadmap_root / "00-product-strategy" / "02-success-metrics.md",\n        roadmap_root / "12-launch-and-operations" / "03-first-real-experiment.md",\n    )\n    if not all(path.is_file() for path in authorities):\n        return\n\n    required_tokens = ("SHADOW", "REVIEW_20", "QUALIFIED_50", "SCALE_100_TO_300")\n    for path in authorities:\n        text = path.read_text(encoding="utf-8")\n        relative = path.relative_to(roadmap_root).as_posix()\n        for token in required_tokens:\n            if token not in text:\n                raise SourceLocation(relative, 1).error(\n                    f"cost-first launch authority is missing {token!r}"\n                )\n    product_text = authorities[0].read_text(encoding="utf-8")\n    for token in (\n        "BRAVE_PLACE_SEARCH",\n        '\"model_routing_tiers\": [\"NO_AI\", \"NANO\", \"MINI\", \"PREMIUM\"]',\n        '\"pre_revenue_recipient_ceiling\": 300',\n    ):\n        if token not in product_text:\n            raise SourceLocation(authorities[0].relative_to(roadmap_root).as_posix(), 1).error(\n                f"cost-first authority is missing {token!r}"\n            )\n\n    secondary_paths = [roadmap_root / "README.md"]\n    secondary_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))\n    primary = {path.resolve() for path in authorities}\n    for path in secondary_paths:\n        if not path.is_file() or path.resolve() in primary:\n            continue\n        relative = path.relative_to(roadmap_root).as_posix()\n        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):\n            if "100/200/300/400" in line or "100/300/600/1,000" in line or "100/300/600/1000" in line:\n                raise SourceLocation(relative, line_number).error(\n                    "legacy automatic cohort authority remains in an active secondary roadmap document"\n                )\n\n\ndef _logical_cells'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"stage validation function: expected one match, found {count}")
    text = text.replace("exact v1 contract", "exact v2 contract")
    VALIDATOR.write_text(text, encoding="utf-8")


def _replace_stage_validator_fixture_tests(text: str) -> str:
    pattern = re.compile(
        r'def test_staged_lead_source_validator_accepts_exact_authorities\(\n.*?\n\ndef write_tree',
        re.S,
    )
    replacement = '''def _write_minimal_cost_first_authorities(tmp_path: Path) -> Path:\n    roadmap = tmp_path / "docs" / "development-roadmap"\n    scope = roadmap / "00-product-strategy" / "01-product-scope.md"\n    metrics = roadmap / "00-product-strategy" / "02-success-metrics.md"\n    launch = roadmap / "12-launch-and-operations" / "03-first-real-experiment.md"\n    scope.parent.mkdir(parents=True)\n    launch.parent.mkdir(parents=True)\n    authority = "SHADOW REVIEW_20 QUALIFIED_50 SCALE_100_TO_300"\n    scope.write_text(\n        authority\n        + ' BRAVE_PLACE_SEARCH "model_routing_tiers": ["NO_AI", "NANO", "MINI", "PREMIUM"]'\n        + ' "pre_revenue_recipient_ceiling": 300',\n        encoding="utf-8",\n    )\n    metrics.write_text(authority + " CONTINUE ScaleAuthorization", encoding="utf-8")\n    launch.write_text(authority + " ScaleAuthorization 100..300", encoding="utf-8")\n    return roadmap\n\n\ndef test_staged_lead_source_validator_accepts_exact_authorities(\n    tmp_path: Path,\n) -> None:\n    _write_minimal_cost_first_authorities(tmp_path)\n    _validator.validate_staged_lead_contract(tmp_path)\n\n\ndef test_staged_lead_source_validator_rejects_legacy_rule_with_location(\n    tmp_path: Path,\n) -> None:\n    roadmap = _write_minimal_cost_first_authorities(tmp_path)\n    readme = roadmap / "README.md"\n    readme.write_text("# Roadmap\\n100/200/300/400\\n", encoding="utf-8")\n\n    with pytest.raises(\n        ValidationError,\n        match=r"README\\.md:2: .*legacy automatic cohort authority",\n    ):\n        _validator.validate_staged_lead_contract(tmp_path)\n\n\ndef write_tree'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"stage validator fixture tests: expected one block, found {count}")
    return text


def migrate_tests() -> None:
    text = TESTS.read_text(encoding="utf-8")
    text = text.replace(
        '''def test_staged_lead_schedule_constants_are_exact() -> None:\n    assert _validator.STAGED_LEAD_SCHEDULE == (100, 200, 300, 400)\n    assert _validator.STAGED_LEAD_CUMULATIVE == (100, 300, 600, 1000)\n''',
        '''def test_cost_first_stage_constants_are_exact() -> None:\n    assert _validator.COST_FIRST_STAGE_NAMES == (\n        "SHADOW", "REVIEW_20", "QUALIFIED_50", "SCALE_100_TO_300"\n    )\n    assert _validator.SCALE_TRANCHE_MIN == 100\n    assert _validator.SCALE_TRANCHE_MAX == 300\n''',
    )
    # Replace the old active-roadmap assertion with direct cost-first coverage.
    active_pattern = re.compile(
        r'def test_active_roadmap_uses_only_staged_thousand_lead_contract\(\) -> None:\n.*?\n\ndef test_staged_lead_source_validator_accepts_exact_authorities',
        re.S,
    )
    active_replacement = '''def test_active_roadmap_uses_cost_first_contract() -> None:\n    repository_root = Path(__file__).resolve().parents[3]\n    roadmap_root = repository_root / "docs" / "development-roadmap"\n    active_paths = [roadmap_root / "README.md"]\n    active_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))\n    active_text = "\\n".join(path.read_text(encoding="utf-8") for path in active_paths)\n\n    for required in (\n        "SHADOW",\n        "REVIEW_20",\n        "QUALIFIED_50",\n        "SCALE_100_TO_300",\n        "Brave Place Search",\n        "Cloudflare Tunnel",\n        "Cloudflare Access",\n        "R2",\n    ):\n        assert required in active_text\n\n\ndef test_staged_lead_source_validator_accepts_exact_authorities'''
    text, count = active_pattern.subn(active_replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"active cost-first test: expected one block, found {count}")

    text = _replace_stage_validator_fixture_tests(text)
    text = text.replace('"autonomous_sales_contract.v1"', '"autonomous_sales_contract.v2"')
    text = text.replace(
        'assert contract.cohort_increments == (100, 200, 300, 400)',
        'assert tuple(stage["name"] for stage in contract.launch_stages) == _validator.COST_FIRST_STAGE_NAMES',
    )
    old_mutations = '''        (("cohort_increments",), [100, 200, 300, 401], "cohort_increments"),\n        (\n            ("cohort_cumulative_maxima",),\n            [100, 300, 600, 1001],\n            "cohort_cumulative_maxima",\n        ),\n        (("recipient_ceiling",), 1001, "recipient_ceiling"),'''
    new_mutations = '''        (("automated_discovery_provider",), "GOOGLE_MAPS", "automated_discovery_provider"),\n        (("manual_evidence_sources",), ["SOCIAL_PROFILE"], "manual_evidence_sources"),\n        (("model_routing_tiers",), ["NANO", "MINI", "PREMIUM"], "model_routing_tiers"),\n        (("premium_model_requires_explicit_approval",), False, "premium_model_requires_explicit_approval"),\n        (("batch_for_non_urgent_research",), False, "batch_for_non_urgent_research"),\n        (("launch_stages", 3, "max_real_businesses"), 301, "launch_stages"),\n        (("pre_revenue_recipient_ceiling",), 301, "pre_revenue_recipient_ceiling"),'''
    text = replace_once(text, old_mutations, new_mutations, "unsafe mutation rows")
    text = text.replace(
        'assert contract.cohort_cumulative_maxima == (100, 300, 600, 1000)',
        'assert contract.pre_revenue_recipient_ceiling == 300',
    )
    text = text.replace(
        'assert contract.recipient_ceiling == 1000',
        'assert contract.automated_discovery_provider == "BRAVE_PLACE_SEARCH"',
    )
    text = text.replace(
        '"2e061a5b5b83a4a18b5f3de88896a2b32e5e7cdf4870145b17be44dea4a63271"',
        '"a6d8c772aa75769285732be8293438241d327586f72938fc718c0e314e35a2db"',
    )
    TESTS.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    migrate_secondary_roadmap_docs()
    migrate_security_secret_boundary()
    migrate_validator()
    migrate_tests()
    print("cost-optimized roadmap migration applied")
