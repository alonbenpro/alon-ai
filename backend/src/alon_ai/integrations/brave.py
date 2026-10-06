"""One bounded Brave Web Search request under an already approved source grant."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
from pydantic import SecretStr

from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    Capability,
    ContentField,
    CostKnowledge,
    ProviderCallResult,
    ProviderErrorCode,
    ProviderFailure,
    ProviderResultMetadata,
    ResultStatus,
    UsageComponent,
    UsageObservation,
    public_url,
)
from alon_ai.policies.provider_rights import (
    GrantEvent,
    IntendedUse,
    ProviderUsageGrant,
    RightsMode,
    RuntimeContent,
    evaluate_rights,
)

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_MAX_RESPONSE_BYTES = 256_000


class BraveSearchAdapter:
    """Low-level provider port; the caller owns governance and evidence persistence."""

    def __init__(
        self,
        secret: SecretStr,
        *,
        grant: ProviderUsageGrant,
        intended_use: IntendedUse,
        events: Callable[[], tuple[GrantEvent, ...]],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not isinstance(secret, SecretStr) or not secret.get_secret_value():
            raise ValueError("provider secret required")
        self._secret = secret
        self._grant = grant
        self._use = intended_use
        self._events = events
        self._clock = clock
        self._transport = transport

    async def search(
        self, request: BraveSearchRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if (
            not isinstance(request, BraveSearchRequest)
            or request.capability is not Capability.BRAVE_WEB_COVERAGE
            or request.capability is not self._use.capability
            or request.limit > 20
        ):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        now = self._clock()
        if (
            evaluate_rights(self._grant, self._events(), self._use, now=now).mode
            is RightsMode.DENIED
        ):
            raise ProviderFailure(ProviderErrorCode.DENIED)
        query = request.query.get_secret_value()
        if not query.strip() or len(query) > 600 or len(query.split()) > 75:
            raise ProviderFailure(ProviderErrorCode.DENIED)
        started = now
        try:
            async with (
                httpx.AsyncClient(
                    transport=self._transport, follow_redirects=False, timeout=10.0
                ) as client,
                client.stream(
                    "GET",
                    _ENDPOINT,
                    params={"q": query, "count": request.limit},
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": self._secret.get_secret_value(),
                    },
                ) as response,
            ):
                if response.is_redirect:
                    raise ProviderFailure(
                        ProviderErrorCode.DENIED, http_status=response.status_code
                    )
                if response.status_code != 200:
                    raise ProviderFailure(
                        ProviderErrorCode.UNAVAILABLE,
                        http_status=response.status_code,
                    )
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > _MAX_RESPONSE_BYTES:
                        raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE)
            payload = json.loads(raw)
            results = payload["web"]["results"]
            if not isinstance(results, list) or len(results) > request.limit:
                raise ValueError
            urls: list[str] = []
            titles: list[str] = []
            texts: list[str] = []
            for item in results:
                url = public_url(item["url"])
                title = item.get("title", "")
                description = item.get("description", "")
                if not isinstance(title, str) or not isinstance(description, str):
                    raise TypeError
                urls.append(url)
                titles.append(title[:500])
                texts.append(description[:2000])
        except ProviderFailure:
            raise
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderFailure(ProviderErrorCode.TIMEOUT) from None
        except (httpx.HTTPError, OSError):
            raise ProviderFailure(ProviderErrorCode.UNAVAILABLE) from None
        except (ValueError, TypeError, KeyError, IndexError):
            raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE) from None
        finished = self._clock()
        if (
            evaluate_rights(self._grant, self._events(), self._use, now=finished).mode
            is RightsMode.DENIED
        ):
            raise ProviderFailure(ProviderErrorCode.DENIED)
        metadata = ProviderResultMetadata(
            capability=request.capability,
            started_at=started,
            finished_at=finished,
            status=ResultStatus.SUCCEEDED,
            usage=(
                UsageObservation(
                    component=UsageComponent.REQUEST,
                    quantity=Decimal(1),
                    currency="USD",
                    cost=None,
                    knowledge=CostKnowledge.UNAVAILABLE,
                    observation_key=uuid4(),
                ),
            ),
        )
        return ProviderCallResult(
            metadata,
            RuntimeContent(
                {
                    ContentField.URL: tuple(urls),
                    ContentField.TITLE: tuple(titles),
                    ContentField.TEXT: tuple(texts),
                },
                grant=self._grant,
                intended_use=self._use,
                observed_at=finished,
            ),
        )
