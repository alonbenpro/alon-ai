"""Narrow offline contact adapters for the governed executor.

Each instance closes over one immutable typed request. Runtime callers supply only
the registered capability configuration and resolved secret required by the
generic executor; they cannot substitute a domain, address, source observation,
or provider method at dispatch time.
"""

from __future__ import annotations

from pydantic import SecretStr

from alon_ai.accounting.models import CapabilityConfig
from alon_ai.providers.contracts import (
    BraveProvider,
    BraveSearchRequest,
    Capability,
    ContactDiscoveryProvider,
    ContactDiscoveryRequest,
    EmailVerificationProvider,
    EmailVerificationRequest,
    ProviderCallResult,
)
from alon_ai.providers.rights import RuntimeContent

_DISCOVERY_METHODS = {
    Capability.HUNTER_DOMAIN_SEARCH: "domain_search",
    Capability.HUNTER_EMAIL_FINDER: "email_finder",
    Capability.HUNTER_COMPANY_ENRICHMENT: "company_enrichment",
    Capability.HUNTER_PERSON_ENRICHMENT: "person_enrichment",
}


class ConfiguredContactAdapter:
    """ConfiguredAdapter bridge for Brave, Hunter discovery and verification fakes."""

    def __init__(
        self,
        provider: BraveProvider | ContactDiscoveryProvider | EmailVerificationProvider,
        request: BraveSearchRequest
        | ContactDiscoveryRequest
        | EmailVerificationRequest,
        *,
        capability: Capability,
    ) -> None:
        method = (
            "search"
            if isinstance(request, BraveSearchRequest)
            else "verify"
            if isinstance(request, EmailVerificationRequest)
            else _DISCOVERY_METHODS.get(capability)
        )
        if (
            method is None
            or (
                isinstance(request, BraveSearchRequest)
                and request.capability is not capability
            )
            or (
                isinstance(request, EmailVerificationRequest)
                and capability is not Capability.HUNTER_EMAIL_VERIFICATION
            )
        ):
            raise ValueError("configured contact adapter mismatch")
        self._provider = provider
        self._request = request
        self.capability = capability
        self.method = method

    def validate_config(self, config: CapabilityConfig) -> None:
        requested_count = (
            self._request.limit if isinstance(self._request, BraveSearchRequest) else 1
        )
        if (
            config.intended_use.capability is not self.capability
            or config.requested_count != requested_count
        ):
            raise ValueError("configured contact adapter mismatch")

    async def invoke(
        self, config: CapabilityConfig, secret: SecretStr | None, /
    ) -> ProviderCallResult[RuntimeContent]:
        del secret  # Fakes perform no network authentication.
        self.validate_config(config)
        operation = getattr(self._provider, self.method)
        return await operation(self._request)
