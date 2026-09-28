"""Explicit operator-approved bounds for live research; no credential values."""

from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from alon_ai.integrations.schemas.provider import (
    Capability,
    ContentField,
    Purpose,
    StrictDTO,
)
from alon_ai.policies.provider_rights import ProviderUsageGrant
from alon_ai.provider_usage.schemas.accounting import CapabilityConfig, Money

RESEARCH_CAPABILITIES = frozenset(
    {
        Capability.BRAVE_WEB_COVERAGE,
        Capability.FIRECRAWL_MAP,
        Capability.FIRECRAWL_PAGE_CAPTURE,
        Capability.FIRECRAWL_PDF_CAPTURE,
        Capability.FIRECRAWL_JS_RETRIEVAL,
    }
)


class ResearchRunPolicy(StrictDTO):
    approved_by: UUID
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    max_calls: int = Field(ge=1, le=100)
    max_pages: int = Field(ge=1, le=100)
    timeout_seconds: int = Field(ge=1, le=3600)
    max_spend_usd: Money = Field(gt=0)
    max_results: int = Field(ge=1, le=20)
    max_pdf_bytes: int = Field(ge=1, le=10_000_000)
    max_pdf_pages: int = Field(ge=1, le=50)
    max_text_chars: int = Field(ge=1, le=100_000)
    pdf_cpu_seconds: int = Field(ge=1, le=10)
    pdf_memory_bytes: int = Field(ge=64 * 1024 * 1024, le=512 * 1024 * 1024)
    pdf_wall_seconds: int = Field(ge=1, le=30)

    @model_validator(mode="after")
    def timeline(self) -> Self:
        if self.effective_at >= self.expires_at:
            raise ValueError("invalid research policy validity")
        return self


class ResearchCapabilityBinding(StrictDTO):
    config: CapabilityConfig
    grant: ProviderUsageGrant

    @model_validator(mode="after")
    def research_only(self) -> Self:
        use = self.config.intended_use
        transient = (
            use.capability is Capability.BRAVE_WEB_COVERAGE
            and use.purpose is Purpose.OFFICIAL_SOURCE_IDENTIFICATION
            and not use.required_fields
            and not self.grant.storage_fields
        )
        if (
            use.capability not in RESEARCH_CAPABILITIES
            or (not transient and use.purpose is not Purpose.RESEARCH)
            or self.config.secret_handle is None
            or self.config.requested_count != 1
            or (not transient and not use.required_fields)
            or not use.required_fields
            <= {ContentField.URL, ContentField.TITLE, ContentField.TEXT}
            or not use.required_fields <= self.grant.storage_fields
            or any(
                getattr(use, field) != getattr(self.grant, field)
                for field in (
                    "provider",
                    "capability",
                    "account_handle",
                    "plan_identifier",
                    "order_form_ref",
                    "terms_version",
                    "purpose",
                )
            )
        ):
            raise ValueError("invalid research authority binding")
        return self
