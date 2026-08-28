from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    to: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    body_text: str = Field(min_length=1)


class SendRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    idempotency_key: UUID
    draft: EmailDraft


class SendResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_message_id: str
    provider_thread_id: str


@runtime_checkable
class GmailProvider(Protocol):
    async def send(self, request: SendRequest) -> SendResult: ...
