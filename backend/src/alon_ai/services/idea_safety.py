"""Conservative deterministic checks before accepting a generated Idea brief."""

import re
from collections.abc import Mapping, Sequence


class IdeaSafetyError(ValueError):
    pass


_QUANTIFIED_CLAIM = re.compile(
    r"(?:[$€₪]\s*\d|\b\d+(?:[.,]\d+)?\s*%|\b\d{2,}(?:,\d{3})+\b)"
)
_GUARANTEE = re.compile(
    r"\b(?:guarantee[ds]?|proven\s+(?:roi|return|savings|revenue))\b", re.IGNORECASE
)
_REGULATED_CAPABILITIES = {
    "legal advice": "legal",
    "medical diagnosis": "medical",
    "tax representation": "tax",
    "investment advice": "investment",
}


def validate_idea_advice(
    advice: Mapping[str, object], *, seed: str, capabilities: Sequence[str]
) -> None:
    """Reject assertive claims that the supplied source/profile cannot support."""
    relationship = advice.get("intent_relationship")
    if relationship == "UNRELATED":
        raise IdeaSafetyError("IDEA_UNRELATED")
    if relationship == "MATERIAL_PIVOT" or advice.get("material_pivot") is True:
        raise IdeaSafetyError("MATERIAL_PIVOT_REQUIRES_APPROVAL")
    fields = [
        str(advice.get(name) or "")
        for name in ("customer", "problem", "service_hypothesis", "value_hypothesis")
    ]
    buyer = advice.get("buyer")
    if isinstance(buyer, Mapping):
        fields.extend(str(value) for value in buyer.values())
    claims = " ".join(fields)
    if _GUARANTEE.search(claims):
        raise IdeaSafetyError("UNSUPPORTED_FACT")
    source_quantities = set(_QUANTIFIED_CLAIM.findall(seed))
    if any(
        value not in source_quantities for value in _QUANTIFIED_CLAIM.findall(claims)
    ):
        raise IdeaSafetyError("UNSUPPORTED_FACT")
    capability_text = " ".join(capabilities).casefold()
    for phrase, required in _REGULATED_CAPABILITIES.items():
        if phrase in claims.casefold() and required not in capability_text:
            raise IdeaSafetyError("CAPABILITY_UNSUPPORTED")
