"""Deterministic supply-plan and evidence freshness guards."""

from alon_ai.policies.campaign_supply import SupplyDenied


def require_active_plan(plan, now):
    if plan["state"] != "ACTIVE":
        raise SupplyDenied("TERMINAL")
    if now >= plan["deadline"]:
        raise SupplyDenied("DEADLINE_EXHAUSTED")


def require_current_evidence(proof, now):
    if not proof["observed_at"] <= now < proof["valid_until"]:
        raise SupplyDenied("STALE_EVIDENCE")
