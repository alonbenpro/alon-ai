"""Bounded Firecrawl map, page, and flat-credit PDF capture.

A local DNS check is defense in depth. Firecrawl's remote fetch and redirects
also need provider-side egress controls before arbitrary URLs can be trusted.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import ipaddress
import json
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pydantic import SecretStr

from alon_ai.integrations.pdf_sandbox import (
    PdfSandboxFailure,
    extract_pdf,
    pdf_sandbox_supported,
    validate_pdf_limits,
)
from alon_ai.integrations.schemas.provider import (
    Capability,
    CaptureFormat,
    ContentField,
    CostKnowledge,
    FirecrawlCaptureRejection,
    FirecrawlCaptureRequest,
    FirecrawlMapRequest,
    FirecrawlRejectionReason,
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

_MAP_ENDPOINT = "https://api.firecrawl.dev/v2/map"
_SCRAPE_ENDPOINT = "https://api.firecrawl.dev/v2/scrape"
_SCRAPE_TIMEOUT_MS = 60_000
# Let Firecrawl finish its server deadline and deliver the response before the
# local read deadline expires. The governed executor still bounds the attempt.
_SCRAPE_CLIENT_TIMEOUT_SECONDS = 75.0
_MAX_RESPONSE_BYTES = 256_000


class _CaptureRejected(ValueError):
    def __init__(self, reason: FirecrawlRejectionReason):
        self.reason = reason
        super().__init__(reason.value)


def _resolve(host: str) -> tuple[str, ...]:
    return tuple({str(item[4][0]) for item in socket.getaddrinfo(host, None)})


class FirecrawlAdapter:
    """Low-level provider port; caller owns pricing, grants, and evidence storage."""

    def __init__(
        self,
        secret: SecretStr,
        *,
        grant: ProviderUsageGrant,
        intended_use: IntendedUse,
        events: Callable[[], tuple[GrantEvent, ...]],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        resolver: Callable[[str], tuple[str, ...]] = _resolve,
        transport: httpx.AsyncBaseTransport | None = None,
        max_pdf_bytes: int,
        max_pdf_pages: int,
        max_text_chars: int,
        pdf_cpu_seconds: int,
        pdf_memory_bytes: int,
        pdf_wall_seconds: int,
    ) -> None:
        if (
            not isinstance(secret, SecretStr)
            or not secret.get_secret_value()
            or type(max_pdf_bytes) is not int
            or type(max_pdf_pages) is not int
            or type(max_text_chars) is not int
            or not 1 <= max_pdf_bytes <= 10_000_000
            or not 1 <= max_pdf_pages <= 50
            or not 1 <= max_text_chars <= 100_000
        ):
            raise ValueError("bounded PDF policy required")
        validate_pdf_limits(pdf_cpu_seconds, pdf_memory_bytes, pdf_wall_seconds)
        self._pdf_cpu_seconds = pdf_cpu_seconds
        self._pdf_memory_bytes = pdf_memory_bytes
        self._pdf_wall_seconds = pdf_wall_seconds
        self._secret = secret
        self._grant = grant
        self._use = intended_use
        self._events = events
        self._clock = clock
        self._resolver = resolver
        self._transport = transport
        self._max_pdf_bytes = max_pdf_bytes
        self._max_pdf_pages = max_pdf_pages
        self._max_text_chars = max_text_chars

    def _authorize(self, capability: Capability) -> datetime:
        now = self._clock()
        if (
            capability is not self._use.capability
            or evaluate_rights(self._grant, self._events(), self._use, now=now).mode
            is RightsMode.DENIED
        ):
            raise ProviderFailure(ProviderErrorCode.DENIED)
        return now

    async def _public_target(self, url: str) -> str:
        try:
            public_url(url)
            host = urlsplit(url).hostname
            if host is None or urlsplit(url).scheme != "https":
                raise ValueError
            addresses = await asyncio.to_thread(self._resolver, host)
            if not addresses or any(
                not ipaddress.ip_address(address).is_global for address in addresses
            ):
                raise ValueError
        except (OSError, ValueError, TypeError):
            raise ProviderFailure(ProviderErrorCode.DENIED) from None
        return url

    async def _capture_source(self, metadata: dict, requested: str) -> str:
        # Firecrawl controls its own DNS resolution and redirect chain. Its API
        # has no documented redirect-disable option. Validate reported URLs as
        # defense in depth; this cannot prevent a provider-side internal fetch.
        status = metadata.get("statusCode", 200)
        if type(status) is not int:
            raise _CaptureRejected(FirecrawlRejectionReason.TARGET_STATUS_INVALID)
        if not 200 <= status < 300:
            raise _CaptureRejected(FirecrawlRejectionReason.TARGET_STATUS_UNSUCCESSFUL)
        if metadata.get("error"):
            raise _CaptureRejected(FirecrawlRejectionReason.TARGET_ERROR_REPORTED)
        source = metadata.get("sourceURL", requested)
        origin = urlsplit(requested)
        for reported in (source, metadata.get("url", source)):
            if not isinstance(reported, str):
                raise _CaptureRejected(FirecrawlRejectionReason.SOURCE_URL_TYPE_INVALID)
            try:
                target = urlsplit(reported)
                same_origin = (
                    target.scheme == origin.scheme
                    and target.hostname == origin.hostname
                    and (target.port or 443) == (origin.port or 443)
                )
            except ValueError:
                raise _CaptureRejected(
                    FirecrawlRejectionReason.SOURCE_URL_INVALID
                ) from None
            if not same_origin:
                raise _CaptureRejected(FirecrawlRejectionReason.SOURCE_ORIGIN_MISMATCH)
            await self._public_target(reported)
        return source

    async def _post(
        self,
        endpoint: str,
        body: dict[str, object],
        *,
        max_bytes: int = _MAX_RESPONSE_BYTES,
        timeout_seconds: float = 15.0,
    ) -> dict:
        try:
            async with (
                httpx.AsyncClient(
                    transport=self._transport,
                    follow_redirects=False,
                    timeout=timeout_seconds,
                ) as client,
                client.stream(
                    "POST",
                    endpoint,
                    json=body,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self._secret.get_secret_value()}",
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
                    if len(raw) > max_bytes:
                        raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE)
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("success") is not True:
                raise ValueError
            return payload
        except ProviderFailure:
            raise
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderFailure(ProviderErrorCode.TIMEOUT) from None
        except (httpx.HTTPError, OSError):
            raise ProviderFailure(ProviderErrorCode.UNAVAILABLE) from None
        except (ValueError, TypeError):
            raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE) from None

    def _result(
        self,
        capability: Capability,
        started: datetime,
        fields: dict[ContentField, tuple[str, ...]],
        *,
        component: UsageComponent,
        quantity: int = 1,
    ) -> ProviderCallResult[RuntimeContent]:
        finished = self._authorize(capability)
        metadata = ProviderResultMetadata(
            capability=capability,
            started_at=started,
            finished_at=finished,
            status=ResultStatus.SUCCEEDED,
            usage=(
                UsageObservation(
                    component=component,
                    quantity=Decimal(quantity),
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
                fields,
                grant=self._grant,
                intended_use=self._use,
                observed_at=finished,
            ),
        )

    async def map(
        self, request: FirecrawlMapRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, FirecrawlMapRequest) or request.limit > 20:
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        started = self._authorize(request.capability)
        await self._public_target(request.url)
        payload = await self._post(
            _MAP_ENDPOINT,
            {
                "url": request.url,
                "limit": request.limit,
                "includeSubdomains": False,
                "ignoreQueryParameters": True,
                "timeout": 15000,
            },
        )
        try:
            links = payload["links"]
            if not isinstance(links, list) or len(links) > request.limit:
                raise ValueError
            urls: list[str] = []
            for item in links:
                url = item if isinstance(item, str) else item["url"]
                urls.append(await self._public_target(url))
        except (ValueError, TypeError, KeyError, IndexError):
            raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE) from None
        return self._result(
            request.capability,
            started,
            {ContentField.URL: tuple(urls)},
            component=UsageComponent.REQUEST,
            quantity=len(urls),
        )

    async def capture(
        self, request: FirecrawlCaptureRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if not isinstance(request, FirecrawlCaptureRequest):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        if request.capability is Capability.FIRECRAWL_PDF_CAPTURE:
            return await self._capture_pdf(request)
        if (
            request.capability
            not in {
                Capability.FIRECRAWL_PAGE_CAPTURE,
                Capability.FIRECRAWL_JS_RETRIEVAL,
            }
            or len(request.formats) != 1
            or request.formats[0] not in {CaptureFormat.MARKDOWN, CaptureFormat.HTML}
            or request.wait_ms > 5000
        ):
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        started = self._authorize(request.capability)
        await self._public_target(request.url)
        field = "markdown" if request.formats[0] is CaptureFormat.MARKDOWN else "html"
        payload = await self._post(
            _SCRAPE_ENDPOINT,
            {
                "url": request.url,
                "formats": [field],
                "onlyMainContent": True,
                "waitFor": request.wait_ms,
                "timeout": _SCRAPE_TIMEOUT_MS,
                "proxy": "basic",
                "storeInCache": False,
                "skipTlsVerification": False,
                "removeBase64Images": True,
                "parsers": [],
            },
            timeout_seconds=_SCRAPE_CLIENT_TIMEOUT_SECONDS,
        )
        content = title = None
        metadata = {}
        try:
            data = payload["data"]
            if not isinstance(data, dict):
                raise _CaptureRejected(FirecrawlRejectionReason.DATA_SHAPE_INVALID)
            if field not in data:
                raise _CaptureRejected(FirecrawlRejectionReason.CONTENT_MISSING)
            content = data[field]
            metadata = data.get("metadata", {})
            if not isinstance(metadata, dict):
                raise _CaptureRejected(FirecrawlRejectionReason.METADATA_SHAPE_INVALID)
            title = metadata.get("title", "")
            source = await self._capture_source(metadata, request.url)
            if not isinstance(content, str):
                raise _CaptureRejected(FirecrawlRejectionReason.CONTENT_TYPE_INVALID)
            if not content:
                raise _CaptureRejected(FirecrawlRejectionReason.CONTENT_EMPTY)
            if len(content) > self._max_text_chars:
                raise _CaptureRejected(FirecrawlRejectionReason.CONTENT_LIMIT_EXCEEDED)
            if not isinstance(title, str):
                raise _CaptureRejected(FirecrawlRejectionReason.TITLE_TYPE_INVALID)
            if len(title) > 500:
                raise _CaptureRejected(FirecrawlRejectionReason.TITLE_LIMIT_EXCEEDED)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            # _post completed HTTP 200/success:true. The returned content is
            # unusable, but this is positive response-completion evidence.
            # Neither a billed quantity nor a price is known at this layer.
            finished = self._authorize(request.capability)
            target_status = (
                metadata.get("statusCode") if isinstance(metadata, dict) else None
            )
            rejection = FirecrawlCaptureRejection(
                reason=error.reason
                if isinstance(error, _CaptureRejected)
                else FirecrawlRejectionReason.DATA_SHAPE_INVALID,
                content_chars=len(content) if isinstance(content, str) else None,
                title_chars=len(title) if isinstance(title, str) else None,
                text_char_limit=self._max_text_chars,
                target_status=target_status
                if type(target_status) is int and 100 <= target_status <= 599
                else None,
            )
            return ProviderCallResult(
                ProviderResultMetadata(
                    capability=request.capability,
                    started_at=started,
                    finished_at=finished,
                    status=ResultStatus.FAILED,
                    error_code=ProviderErrorCode.MALFORMED_RESPONSE,
                    rejection=rejection,
                    usage=(
                        UsageObservation(
                            component=UsageComponent.CAPTURE_PAGE,
                            quantity=None,
                            currency="USD",
                            cost=None,
                            knowledge=CostKnowledge.UNAVAILABLE,
                            observation_key=uuid4(),
                        ),
                    ),
                ),
                None,
            )
        return self._result(
            request.capability,
            started,
            {
                ContentField.URL: (source,),
                ContentField.TITLE: (title,),
                ContentField.TEXT: (content,),
            },
            component=UsageComponent.CAPTURE_PAGE,
        )

    async def _capture_pdf(
        self, request: FirecrawlCaptureRequest
    ) -> ProviderCallResult[RuntimeContent]:
        if request.formats != (CaptureFormat.MARKDOWN,) or request.wait_ms:
            raise ProviderFailure(ProviderErrorCode.CAPABILITY_MISMATCH)
        started = self._authorize(request.capability)
        await self._public_target(request.url)
        if not pdf_sandbox_supported():
            raise ProviderFailure(ProviderErrorCode.UNAVAILABLE)
        # Firecrawl's documented parsers=[] path returns the original PDF as
        # base64 for a flat 1 credit. Its parser=["pdf"] bills per PDF page.
        payload = await self._post(
            _SCRAPE_ENDPOINT,
            {
                "url": request.url,
                "formats": ["rawBase64"],
                "parsers": [],
                "timeout": _SCRAPE_TIMEOUT_MS,
                "proxy": "basic",
                "storeInCache": False,
                "skipTlsVerification": False,
            },
            max_bytes=(self._max_pdf_bytes * 4 // 3) + 4096,
            timeout_seconds=_SCRAPE_CLIENT_TIMEOUT_SECONDS,
        )
        try:
            data = payload["data"]
            encoded = data["rawBase64"]
            metadata = data.get("metadata", {})
            source = await self._capture_source(metadata, request.url)
            if not isinstance(encoded, str) or len(encoded) > (
                self._max_pdf_bytes * 4 // 3 + 4
            ):
                raise ValueError
            raw = base64.b64decode(encoded, validate=True)
            if not raw.startswith(b"%PDF-") or len(raw) > self._max_pdf_bytes:
                raise ValueError
            content = await extract_pdf(
                raw,
                max_bytes=self._max_pdf_bytes,
                max_pages=self._max_pdf_pages,
                max_chars=self._max_text_chars,
                cpu_seconds=self._pdf_cpu_seconds,
                memory_bytes=self._pdf_memory_bytes,
                wall_seconds=self._pdf_wall_seconds,
            )
        except PdfSandboxFailure as error:
            code = {
                "timeout": ProviderErrorCode.TIMEOUT,
                "unavailable": ProviderErrorCode.UNAVAILABLE,
            }.get(error.kind, ProviderErrorCode.MALFORMED_RESPONSE)
            raise ProviderFailure(code) from None
        except ProviderFailure:
            raise
        except (ValueError, TypeError, KeyError, IndexError, binascii.Error):
            raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE) from None
        except Exception:  # noqa: BLE001 - PDF parser errors may contain source content
            raise ProviderFailure(ProviderErrorCode.MALFORMED_RESPONSE) from None
        return self._result(
            request.capability,
            started,
            {ContentField.URL: (source,), ContentField.TEXT: (content,)},
            component=UsageComponent.REQUEST,
        )
