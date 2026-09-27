from alon_ai.integrations.gmail import (
    EmailDraft,
    GmailProvider,
    SendRequest,
    SendResult,
)
from alon_ai.policies.sending import SendPolicy

__all__ = [
    "EmailDraft",
    "OutreachDisabledError",
    "SendGateway",
    "SendRejectedError",
    "SendRequest",
    "SendResult",
]


class OutreachDisabledError(Exception):
    """Raised when sending is disabled for the deployment."""


class SendRejectedError(Exception):
    """Raised when the sending policy denies a request."""


class SendGateway:
    def __init__(
        self,
        *,
        outreach_enabled: bool,
        policy: SendPolicy,
        provider: GmailProvider,
    ) -> None:
        self._outreach_enabled = outreach_enabled
        self._policy = policy
        self._provider = provider

    async def send(self, request: SendRequest) -> SendResult:
        if not self._outreach_enabled:
            raise OutreachDisabledError
        decision = await self._policy.evaluate(request)
        if not decision.allowed:
            raise SendRejectedError(decision.reason)
        return await self._provider.send(request)
