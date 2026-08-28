from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from alon_ai.domain.sending import (
    EmailDraft,
    OutreachDisabledError,
    SendGateway,
    SendRejectedError,
    SendRequest,
)
from alon_ai.policies.sending import PolicyDecision, SendPolicy
from alon_ai.providers.gmail import GmailProvider, SendResult


def make_request() -> SendRequest:
    return SendRequest(
        idempotency_key=uuid4(),
        draft=EmailDraft(
            to="prospect@example.com",
            subject="A useful idea",
            body_text="Hello from Alon AI.",
        ),
    )


async def test_send_does_not_evaluate_policy_or_call_provider_when_outreach_is_disabled() -> (
    None
):
    policy = AsyncMock(spec=SendPolicy)
    provider = AsyncMock(spec=GmailProvider)
    gateway = SendGateway(
        outreach_enabled=False,
        policy=policy,
        provider=provider,
    )

    with pytest.raises(OutreachDisabledError):
        await gateway.send(make_request())

    policy.evaluate.assert_not_awaited()
    provider.send.assert_not_awaited()


async def test_send_does_not_call_provider_when_policy_denies_the_request() -> None:
    policy = AsyncMock(spec=SendPolicy)
    policy.evaluate.return_value = PolicyDecision(
        allowed=False, reason="recipient opted out"
    )
    provider = AsyncMock(spec=GmailProvider)
    gateway = SendGateway(
        outreach_enabled=True,
        policy=policy,
        provider=provider,
    )

    with pytest.raises(SendRejectedError, match="recipient opted out"):
        await gateway.send(make_request())

    provider.send.assert_not_awaited()


async def test_send_returns_the_provider_result_when_policy_allows_the_request() -> (
    None
):
    request = make_request()
    expected = SendResult(
        provider_message_id="message-123",
        provider_thread_id="thread-456",
    )
    policy = AsyncMock(spec=SendPolicy)
    policy.evaluate.return_value = PolicyDecision(allowed=True, reason="approved")
    provider = AsyncMock(spec=GmailProvider)
    provider.send.return_value = expected
    gateway = SendGateway(
        outreach_enabled=True,
        policy=policy,
        provider=provider,
    )

    result = await gateway.send(request)

    assert result == expected
    provider.send.assert_awaited_once_with(request)
