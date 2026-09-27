"""Identity content is retained by source rights; these DTOs grant no send authority."""

from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from alon_ai.integrations.schemas.provider import StrictDTO


class OrganizationIdentifier(StrictDTO):
    kind: Literal["REGISTERED_ID", "PROVIDER_ID", "OFFICIAL_URL"]
    namespace: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def exclusive_registered_namespace(self) -> Self:
        if self.kind == "REGISTERED_ID" and (
            len(self.namespace) != 2
            or not self.namespace.isupper()
            or not self.namespace.isalpha()
        ):
            raise ValueError("registered identity requires country namespace")
        return self


class OrganizationAlias(StrictDTO):
    kind: Literal["NAME", "DOMAIN", "URL", "FORMER_NAME"]
    value: str = Field(min_length=1, max_length=400)


class OrganizationLocation(StrictDTO):
    branch_name: str | None = Field(default=None, max_length=200)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    city: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=500)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def paired_coordinates(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("coordinates require an exact pair")
        return self


class OrganizationSnapshot(StrictDTO):
    canonical_name: str = Field(min_length=1, max_length=300)
    canonical_domain: str | None = Field(
        default=None, pattern=r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}$"
    )
    organization_kind: Literal["LOCAL_BUSINESS", "ONLINE_COMPANY", "HYBRID", "UNKNOWN"]
    identifiers: tuple[OrganizationIdentifier, ...] = Field(max_length=30)
    aliases: tuple[OrganizationAlias, ...] = Field(max_length=50)
    locations: tuple[OrganizationLocation, ...] = Field(max_length=100)

    @field_validator("canonical_name")
    @classmethod
    def meaningful_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("empty canonical name")
        return value


class RetainedOrganizationSource(StrictDTO):
    retained_id: UUID
    value_index: int = Field(ge=0, le=999)
    observed_at: AwareDatetime


class GatewayEffectObservation(StrictDTO):
    """Only a trusted gateway adapter may construct this correlation receipt.

    API provenance is validated against the bound call and its immutable trusted
    evidence. This contract never executes Gmail or independently grants a send.
    """

    id: UUID
    effect_id: UUID
    call_id: UUID
    operation_id: UUID
    experiment_id: UUID
    reservation_id: UUID
    recipient_lookup_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    mailbox_id: UUID
    rfc_message_id: UUID
    outcome: Literal["CONFIRMED", "AMBIGUOUS", "NO_EFFECT"]
    result_evidence_id: UUID | None = None
    provider_request_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )
    provider_message_id: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )
    reconciles_id: UUID | None = None
    observed_at: AwareDatetime

    @model_validator(mode="after")
    def exact_outcome_evidence(self) -> Self:
        if self.outcome == "CONFIRMED" and (
            self.result_evidence_id is None
            or self.provider_message_id is None
            or self.provider_request_id is None
        ):
            raise ValueError("confirmation requires positive exact provider evidence")
        if self.outcome == "AMBIGUOUS" and (
            self.provider_message_id is not None
            or self.provider_request_id is not None
            or self.result_evidence_id is not None
        ):
            raise ValueError("ambiguity cannot assert provider acceptance")
        if self.outcome == "NO_EFFECT" and (
            self.result_evidence_id is None
            or self.provider_message_id is not None
            or self.provider_request_id is not None
        ):
            raise ValueError("no effect requires unused-call evidence")
        return self


class OrganizationIdentityReceipt(StrictDTO):
    command_id: UUID
    organization_id: UUID
    evidence_id: UUID
    binding_id: UUID


class OrganizationAdmissionReceipt(StrictDTO):
    command_id: UUID
    result_id: UUID
    admitted: bool
    reason: str | None = None
