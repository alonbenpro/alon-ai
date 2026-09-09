from __future__ import annotations

import copy
import json
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "validate_experiment_brief.py"

_spec = spec_from_file_location("_experiment_brief_under_test", SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_validator = module_from_spec(_spec)
sys.modules[_spec.name] = _validator
_spec.loader.exec_module(_validator)

ExperimentBrief = _validator.ExperimentBrief
canonical_brief_digest = _validator.canonical_brief_digest


@pytest.fixture
def synthetic_brief() -> dict[str, object]:
    """A clearly synthetic contract fixture; it is not operator evidence."""
    return {
        "schema_version": "experiment_brief.v1",
        "revision": 1,
        "experiment_code": "SYNTHETIC-TEST-ONLY",
        "hypothesis": {
            "operator": "Synthetic test operator",
            "customer": "Synthetic neighborhood bakeries",
            "problem": "Synthetic manual order reconciliation",
            "deliverable": "Synthetic fixed-scope reconciliation prototype",
        },
        "idea_origin": "USER_SUPPLIED",
        "jurisdictions": ["SYNTHETIC-JURISDICTION"],
        "baseline": {
            "kind": "ZERO_HISTORY",
            "method": "Start with no historical result claims.",
            "references": [],
        },
        "budget_caps": {
            "currency": "ILS",
            "total_agorot": 10000,
            "model_agorot": 2500,
            "discovery_agorot": 1500,
            "operator_time_total_minutes": 600,
            "operator_time_weekly_minutes": 180,
        },
        "workflow_caps": {
            "research_businesses": 50,
            "qualification_businesses": 30,
            "contact_recipients": 20,
            "concurrent_conversations": 5,
        },
        "source_policy": {
            "policy_version": "synthetic-source-policy.v1",
            "automated_discovery_source": "BRAVE_PLACE_SEARCH",
            "manual_evidence_sources": [
                "SOCIAL_PROFILE",
                "PUBLIC_BUSINESS_PAGE",
            ],
            "manual_review_required": True,
            "provenance_required": True,
            "source_url_or_capture_required": True,
            "reviewer_and_time_required": True,
            "permitted_fields_required": True,
            "retention_policy_required": True,
            "redaction_policy_required": True,
            "cannot_expand_provider_capability": True,
            "unverified_contact_identity_forbidden": True,
        },
        "model_routing_policy": {
            "policy_version": "synthetic-model-policy.v1",
            "tiers": ["NO_AI", "NANO", "MINI", "PREMIUM"],
            "deterministic_application_routing": True,
            "agent_may_choose_tier": False,
            "premium_default_denied": True,
            "premium_requires_explicit_operator_approval": True,
            "premium_approval_requirements": [
                "EXACT_TASK_AND_RUN",
                "MODEL_AND_CONFIG",
                "MAXIMUM_SPEND_AGOROT",
                "EXPIRY",
                "REASON",
            ],
            "batch_non_urgent_research": True,
        },
        "evidence_policy": {
            "policy_version": "synthetic-evidence-policy.v1",
            "source_references_required": True,
            "model_call_records_required": True,
            "manual_evidence_records_required": True,
            "infrastructure_evidence_required": True,
        },
        "infrastructure_policy": {
            "vps_vcpu": 2,
            "vps_memory_gb": 4,
            "encrypted_local_storage": True,
            "backup_destination": "CLOUDFLARE_R2",
            "encrypt_backup_before_upload": True,
            "private_ingress": "CLOUDFLARE_TUNNEL_AND_ACCESS",
            "direct_public_service_exposure": False,
        },
        "launch_policy": {
            "pre_revenue_recipient_ceiling": 300,
            "stages": [
                {
                    "name": "SHADOW",
                    "min_real_businesses": 0,
                    "max_real_businesses": 0,
                    "manual_review_required": False,
                    "real_demand_learning": False,
                    "explicit_operator_authorization": False,
                },
                {
                    "name": "REVIEW_20",
                    "min_real_businesses": 0,
                    "max_real_businesses": 20,
                    "manual_review_required": True,
                    "real_demand_learning": True,
                    "explicit_operator_authorization": False,
                },
                {
                    "name": "QUALIFIED_50",
                    "min_real_businesses": 0,
                    "max_real_businesses": 50,
                    "manual_review_required": False,
                    "real_demand_learning": True,
                    "explicit_operator_authorization": False,
                },
                {
                    "name": "SCALE_100_TO_300",
                    "min_real_businesses": 100,
                    "max_real_businesses": 300,
                    "manual_review_required": False,
                    "real_demand_learning": True,
                    "explicit_operator_authorization": True,
                },
            ],
        },
        "conversation_booking_limits": {
            "messages_per_conversation": 8,
            "follow_ups_per_conversation": 2,
            "bookings_total": 5,
            "timezone_aware_slot_confirmation_required": True,
        },
        "baseline_strategy": {
            "strategy_version": "synthetic-strategy.v1",
            "description": "Synthetic direct evidence-led offer strategy.",
            "evidence_channel": "Synthetic operator-reviewed business conversations.",
        },
        "evaluation": {
            "success_rules": [
                {
                    "code": "SYNTHETIC-SUCCESS",
                    "metric": "booked_calls",
                    "comparator": "GREATER_THAN_OR_EQUAL",
                    "threshold": 2,
                    "evidence_required": "Confirmed synthetic booking records.",
                }
            ],
            "economic_rules": [
                {
                    "code": "SYNTHETIC-ECONOMICS",
                    "metric": "contribution_agorot",
                    "comparator": "GREATER_THAN_OR_EQUAL",
                    "threshold": 0,
                    "evidence_required": "Synthetic attributed cost and revenue records.",
                }
            ],
            "kill_rules": [
                {
                    "code": "SYNTHETIC-KILL",
                    "metric": "safety_incidents",
                    "comparator": "GREATER_THAN",
                    "threshold": 0,
                    "evidence_required": "Synthetic incident records.",
                }
            ],
            "decision_rules": [
                {
                    "decision": "INCONCLUSIVE",
                    "condition": "Required evidence is missing or too weak.",
                }
            ],
            "evidence_based_decision_condition": (
                "Use only retained evidence from a closed checkpoint."
            ),
        },
        "operator_signature": {
            "status": "PENDING",
            "signatory": None,
            "signed_at": None,
            "evidence_reference": None,
            "verification": "EXTERNAL_REQUIRED",
        },
    }


def test_validates_a_structurally_complete_unsigned_synthetic_draft(
    synthetic_brief: dict[str, object],
) -> None:
    brief = ExperimentBrief.model_validate(synthetic_brief)

    assert brief.experiment_code == "SYNTHETIC-TEST-ONLY"
    assert brief.operator_signature.status == "PENDING"
    assert brief.signature_record_present is False
    assert isinstance(brief.jurisdictions, tuple)
    with pytest.raises(ValidationError):
        brief.revision = 2


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("unexpected",), "secret-marker"),
        (("hypothesis", "problem"), "   "),
        (("budget_caps", "total_agorot"), True),
        (("budget_caps", "model_agorot"), 12.5),
        (("budget_caps", "discovery_agorot"), float("inf")),
    ],
)
def test_rejects_unknown_blank_and_non_strict_values(
    synthetic_brief: dict[str, object], path: tuple[str, ...], value: object
) -> None:
    target = synthetic_brief
    for part in path[:-1]:
        target = target[part]  # type: ignore[index,assignment]
    target[path[-1]] = value

    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


def test_requires_evidence_references_only_for_an_evidenced_baseline(
    synthetic_brief: dict[str, object],
) -> None:
    baseline = synthetic_brief["baseline"]
    assert isinstance(baseline, dict)
    baseline["kind"] = "EVIDENCED"

    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)

    baseline["references"] = [
        {
            "reference_id": "SYNTHETIC-EVIDENCE-1",
            "source": "Synthetic operator-owned record",
        }
    ]
    assert ExperimentBrief.model_validate(synthetic_brief).baseline.kind == "EVIDENCED"

    baseline["kind"] = "ZERO_HISTORY"
    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


def test_rejects_budget_subcaps_above_the_total(
    synthetic_brief: dict[str, object],
) -> None:
    caps = synthetic_brief["budget_caps"]
    assert isinstance(caps, dict)
    caps["model_agorot"] = 7000
    caps["discovery_agorot"] = 4000

    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


def test_rejects_incoherent_funnel_and_concurrency_caps(
    synthetic_brief: dict[str, object],
) -> None:
    caps = synthetic_brief["workflow_caps"]
    assert isinstance(caps, dict)
    caps["qualification_businesses"] = 51
    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)

    caps["qualification_businesses"] = 30
    caps["concurrent_conversations"] = 21
    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("source_policy", "automated_discovery_source", "GOOGLE_MAPS"),
        ("source_policy", "manual_review_required", 1),
        ("model_routing_policy", "agent_may_choose_tier", True),
        ("model_routing_policy", "agent_may_choose_tier", 0),
        ("model_routing_policy", "premium_default_denied", False),
        ("infrastructure_policy", "vps_vcpu", 4),
        ("infrastructure_policy", "vps_vcpu", 2.0),
        ("infrastructure_policy", "vps_memory_gb", 4.0),
        ("infrastructure_policy", "direct_public_service_exposure", True),
        ("launch_policy", "pre_revenue_recipient_ceiling", 600),
        ("launch_policy", "pre_revenue_recipient_ceiling", 300.0),
    ],
)
def test_rejects_widening_the_pinned_cost_first_policy(
    synthetic_brief: dict[str, object], section: str, field: str, value: object
) -> None:
    policy = synthetic_brief[section]
    assert isinstance(policy, dict)
    policy[field] = value

    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


def test_requires_the_exact_ordered_launch_program(
    synthetic_brief: dict[str, object],
) -> None:
    policy = synthetic_brief["launch_policy"]
    assert isinstance(policy, dict)
    stages = policy["stages"]
    assert isinstance(stages, list)
    stages[1], stages[2] = stages[2], stages[1]

    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


def test_signature_record_is_never_treated_as_verified_operator_evidence(
    synthetic_brief: dict[str, object],
) -> None:
    signature = synthetic_brief["operator_signature"]
    assert isinstance(signature, dict)
    signature.update(
        {
            "status": "PROVIDED_UNVERIFIED",
            "signatory": "Synthetic test operator",
            "signed_at": "2030-01-02T03:04:05Z",
            "evidence_reference": "SYNTHETIC-EXTERNAL-SIGNATURE-RECORD",
        }
    )
    brief = ExperimentBrief.model_validate(synthetic_brief)
    assert brief.signature_record_present is True
    assert brief.operator_signature.verification == "EXTERNAL_REQUIRED"

    signature["status"] = "SIGNED"
    with pytest.raises(ValidationError):
        ExperimentBrief.model_validate(synthetic_brief)


def test_canonical_digest_is_order_independent_and_content_sensitive(
    synthetic_brief: dict[str, object],
) -> None:
    brief = ExperimentBrief.model_validate(synthetic_brief)
    reordered = json.loads(json.dumps(synthetic_brief, sort_keys=True))
    same_brief = ExperimentBrief.model_validate(reordered)
    changed = copy.deepcopy(synthetic_brief)
    changed["revision"] = 2

    assert canonical_brief_digest(brief) == canonical_brief_digest(same_brief)
    assert canonical_brief_digest(brief) != canonical_brief_digest(
        ExperimentBrief.model_validate(changed)
    )
    assert len(canonical_brief_digest(brief)) == 64


def test_cli_reports_structural_validity_without_claiming_a_gate(
    synthetic_brief: dict[str, object], tmp_path: Path
) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(synthetic_brief), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["structural_valid"] is True
    assert output["signature_record_present"] is False
    assert output["operator_signature_verification"] == "external_required"
    assert "m0" not in result.stdout.lower()
    assert "unlock" not in result.stdout.lower()


def test_cli_errors_are_redacted_and_malformed_input_is_nonzero(
    synthetic_brief: dict[str, object], tmp_path: Path
) -> None:
    secret = "HIGHLY-SENSITIVE-SYNTHETIC-VALUE"
    hypothesis = synthetic_brief["hypothesis"]
    assert isinstance(hypothesis, dict)
    hypothesis["problem"] = secret
    hypothesis["unexpected"] = secret
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(synthetic_brief), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert secret not in result.stdout
    assert secret not in result.stderr
    error = json.loads(result.stderr)
    assert error["structural_valid"] is False
    assert error["errors"][0].keys() == {"location", "type"}

    path.write_text("{", encoding="utf-8")
    malformed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert malformed.returncode != 0
    assert json.loads(malformed.stderr)["errors"] == [
        {"location": "$", "type": "invalid_json"}
    ]


def test_cli_can_export_the_json_schema() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--schema"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    schema = json.loads(result.stdout)
    assert schema["title"] == "ExperimentBrief"
    assert schema["additionalProperties"] is False
