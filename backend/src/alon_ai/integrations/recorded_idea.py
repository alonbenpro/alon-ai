"""Explicit local recorded transport through the governed L06 IdeaRuntime.

This is available only with provider_mode=fake outside production. It never
opens a network connection or produces real market evidence.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import SecretStr


class _RecordedSecrets:
    def get(self, handle: str) -> SecretStr:
        if handle != "l07-recorded-only":
            raise ValueError("unknown recorded transport handle")
        return SecretStr("recorded-only")


class _RecordedResponses:
    async def create(self, **kwargs: object) -> dict[str, Any]:
        raw = kwargs.get("input_json")
        if not isinstance(raw, str):
            raise TypeError("recorded input missing")
        bound = json.loads(raw)
        artifacts = bound.get("artifacts", [])
        if len(artifacts) not in {1, 2}:
            raise ValueError("recorded transport requires exact Idea inputs")
        kind = artifacts[0].get("kind")
        if kind == "EXPERIMENT_BRIEF":
            brief = artifacts[0]["payload"]
            capability = bound["operator_profiles"][0]["capabilities"][0]
            approaches = (
                ("self-service form", "a self-service form to collect requests"),
                ("staff triage queue", "a staff queue to prioritize requests"),
                ("workflow status dashboard", "a dashboard to track request progress"),
            )
            advice = {
                "candidates": [
                    {
                        "title": f"{brief['target_customer']} {name}",
                        "hypothesis": f"Use {capability} to explore {approach} for {brief['target_customer']} facing {brief['problem']} in {brief['geographies'][0]}; demand is unverified",
                        "demand_status": "UNVERIFIED",
                        "grounding_refs": ["OPERATOR_PROFILE"],
                        "uncertainties": [
                            "Customer demand and delivery fit are unverified"
                        ],
                    }
                    for name, approach in approaches
                ]
            }
        elif kind in {"IDEA_SEED", "IDEA_CANDIDATE", "IDEA_BRIEF"}:
            is_return = kind == "IDEA_BRIEF"
            if is_return and (
                len(artifacts) != 2
                or artifacts[1].get("kind") != "RESEARCH_FEEDBACK_BRIEF"
            ):
                raise ValueError("recorded return requires feedback")
            statement = (
                artifacts[0]["payload"]["statement"]
                if kind == "IDEA_SEED"
                else artifacts[0]["payload"].get("hypothesis")
                or artifacts[0]["payload"]["core_intent"]
            ).strip()
            advice = {
                "title": statement[:120],
                "customer": "Customer stated in original seed; verify before research",
                "problem": "Problem stated in original seed; verify before research",
                "core_intent": statement,
                "intent_relationship": "PRESERVES_CORE_INTENT",
                "material_pivot": False,
                "buyer": {
                    "segment": "Customer stated in original input",
                    "role": "Buyer role remains unverified",
                },
                "service_hypothesis": "Recorded local service hypothesis; verify before research",
                "value_hypothesis": "Recorded local value hypothesis; verify before research",
                "assumptions": ["Recorded local assumptions require operator review"],
                "exclusions": ["No market claim or provider action is authorized"],
                "research_questions": ["Which buyer evidence would validate this?"],
                "grounding_refs": (
                    ["PRIOR_IDEA_BRIEF", "RESEARCH_FEEDBACK"]
                    if is_return
                    else ["SEED" if kind == "IDEA_SEED" else "SELECTED_CANDIDATE"]
                ),
                "uncertainties": [
                    "Synthetic recorded advice; customer, problem and demand are unverified"
                ],
            }
        else:
            raise ValueError("recorded transport requires exact Idea origin")
        return {
            "id": "resp_l07_recorded",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(advice)}],
                }
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
                "input_tokens_details": {"cached_tokens": 0},
            },
        }
