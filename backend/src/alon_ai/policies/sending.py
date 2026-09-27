from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from alon_ai.integrations.gmail import SendRequest


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str = Field(min_length=1)


@runtime_checkable
class SendPolicy(Protocol):
    async def evaluate(self, request: SendRequest) -> PolicyDecision: ...
