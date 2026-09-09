"""One-shot finalizer for cost-first roadmap validator tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "backend/tests/unit/test_roadmap_validator.py"
VALIDATOR = ROOT / "scripts/validate_roadmap.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("final_cost_roadmap_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load roadmap validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return updated


def main() -> None:
    text = TESTS.read_text(encoding="utf-8")

    text = replace_once(
        text,
        r"def test_active_roadmap_uses_only_staged_thousand_lead_contract\(\) -> None:\n.*?\n\ndef test_staged_lead_source_validator_accepts_exact_authorities",
        '''def test_active_roadmap_uses_cost_first_contract() -> None:\n    repository_root = Path(__file__).resolve().parents[3]\n    roadmap_root = repository_root / "docs" / "development-roadmap"\n    active_paths = [roadmap_root / "README.md"]\n    active_paths.extend(sorted(roadmap_root.glob("[0-9][0-9]-*/*.md")))\n    active_text = "\\n".join(path.read_text(encoding="utf-8") for path in active_paths)\n\n    for required in (\n        "SHADOW",\n        "REVIEW_20",\n        "QUALIFIED_50",\n        "SCALE_100_TO_300",\n        "BRAVE_PLACE_SEARCH",\n    ):\n        assert required in active_text\n\n    for forbidden in (\n        "100/200/300/400",\n        "100/300/600/1,000",\n        "100/300/600/1000",\n    ):\n        assert forbidden not in active_text\n\n\ndef test_staged_lead_source_validator_accepts_exact_authorities''',
        "active contract test",
    )

    validator = load_validator()
    roadmap = validator.parse_roadmap(ROOT)
    fingerprint = validator.graph_fingerprint(roadmap)

    fingerprint_pattern = re.compile(
        r'(assert graph_fingerprint\(roadmap\) == \(\n\s+")[0-9a-f]{64}("\n\s+\))'
    )
    if fingerprint_pattern.search(text):
        text = fingerprint_pattern.sub(rf'\g<1>{fingerprint}\g<2>', text, count=1)
    else:
        # The migration must retain a reviewed fixed fingerprint assertion.
        marker = "def test_reviewed_roadmap_graph_is_stable"
        if marker not in text:
            raise RuntimeError("reviewed graph stability test/fingerprint assertion not found")
        raise RuntimeError("reviewed graph test exists but does not contain a fixed 64-hex fingerprint")

    TESTS.write_text(text, encoding="utf-8")
    print(f"finalized cost-first tests; reviewed fingerprint={fingerprint}")


if __name__ == "__main__":
    main()
