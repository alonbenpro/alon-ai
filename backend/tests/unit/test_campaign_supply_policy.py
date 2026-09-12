"""Fixed supply rules and evidence-driven plan transitions."""

from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_policy_cannot_lower_target_or_increase_entitlement():
    from alon_ai.policies.campaign_supply import SupplyPolicy

    assert SupplyPolicy().qualified_contactable_target == 50
    for key, value in [
        ("qualified_contactable_target", 49),
        ("qualified_contactable_target", 51),
        ("candidate_batch_size", 101),
        ("max_total_discovery_batches", 4),
    ]:
        with pytest.raises(ValidationError):
            SupplyPolicy.model_validate({key: value})


def test_material_change_must_respond_to_observed_failure_without_changing_rules():
    from alon_ai.policies.campaign_supply import (
        DiscoveryPlan,
        Filter,
        SupplyDenied,
        validate_change,
    )

    rule = uuid4()
    old_filter, new_filter = (
        Filter(dimension="QUERY", value=uuid4()),
        Filter(dimension="QUERY", value=uuid4()),
    )
    old = DiscoveryPlan(qualification_rule_id=rule, filters=(old_filter,))
    new = DiscoveryPlan(qualification_rule_id=rule, filters=(new_filter,))
    validate_change(old, new, (old_filter, new_filter), (old_filter,))
    for proposal, failures in [
        (old, (old_filter,)),
        (new, ()),
        (
            DiscoveryPlan(qualification_rule_id=uuid4(), filters=(new_filter,)),
            (old_filter,),
        ),
    ]:
        with pytest.raises(SupplyDenied):
            validate_change(old, proposal, (old_filter, new_filter), failures)
