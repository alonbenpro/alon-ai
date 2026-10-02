"""Agent-facing research operations delegated to a trusted governed service.

The service port must reserve and reconcile provider usage, enforce source rights,
and persist admitted evidence before returning a reference. These methods never
return provider responses or credentials directly to an agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import SecretStr

from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    Capability,
    CaptureFormat,
    FirecrawlCaptureRequest,
    FirecrawlMapRequest,
    ProviderErrorCode,
    ProviderFailure,
    public_url,
)
from alon_ai.provider_usage.schemas.accounting import AccountingDenied, Reason
from alon_ai.services.schemas.records import SourceReference


class ResearchToolError(Exception):
    """Safe error marker with no provider response or request text."""

    def __init__(
        self, code: str = "RESEARCH_TOOL_UNAVAILABLE", *, http_status: int | None = None
    ) -> None:
        self.code = code if code in _SAFE_CODES else "RESEARCH_TOOL_UNAVAILABLE"
        self.http_status = (
            http_status
            if type(http_status) is int and 100 <= http_status <= 599
            else None
        )
        super().__init__(self.code)


_SAFE_CODES = frozenset(
    {
        "RESEARCH_TOOL_UNAVAILABLE",
        *(reason.value for reason in Reason),
        *(code.value for code in ProviderErrorCode),
    }
)


def _research_tool_error(error: Exception) -> ResearchToolError:
    if isinstance(error, AccountingDenied):
        provider = _provider_cause(error)
        if error.reason is Reason.UNCERTAIN and provider is not None:
            return ResearchToolError(
                provider.code.value, http_status=provider.http_status
            )
        return ResearchToolError(error.reason.value)
    if isinstance(error, ProviderFailure):
        return ResearchToolError(error.code.value, http_status=error.http_status)
    return ResearchToolError()


def _provider_cause(error: Exception) -> ProviderFailure | None:
    """Read only a classified nested provider code, never an exception message."""

    initial = error.__cause__ or error.__context__
    current: Exception | None = initial if isinstance(initial, Exception) else None
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(seen) < 4:
        seen.add(id(current))
        if isinstance(current, ProviderFailure):
            return current
        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, Exception) else None
    return None


@dataclass(frozen=True)
class SavedEvidenceExcerpt:
    reference: SourceReference
    text: str


@dataclass(frozen=True, repr=False)
class TransientSearchUrls:
    """Runtime-only discovery hints; never evidence or a durable checkpoint."""

    urls: tuple[str, ...]

    def __repr__(self) -> str:
        return "TransientSearchUrls(<runtime-only>)"

    def __reduce_ex__(self, protocol):
        raise TypeError("transient discovery cannot be checkpointed")


class GovernedResearchPort(Protocol):
    async def search(
        self, experiment_id: UUID, request: BraveSearchRequest
    ) -> tuple[SourceReference, ...] | TransientSearchUrls: ...

    async def map(
        self, experiment_id: UUID, request: FirecrawlMapRequest
    ) -> tuple[SourceReference, ...]: ...

    async def capture(
        self, experiment_id: UUID, request: FirecrawlCaptureRequest
    ) -> tuple[SourceReference, ...]: ...

    async def read_saved_evidence(
        self, experiment_id: UUID, retained_id: UUID, *, max_chars: int
    ) -> SavedEvidenceExcerpt: ...


class ResearchTools:
    """Bounded tool facade scoped to one experiment and a trusted service port."""

    def __init__(
        self, experiment_id: UUID, port: GovernedResearchPort, *, max_results: int = 20
    ) -> None:
        if type(max_results) is not int or not 1 <= max_results <= 20:
            raise ValueError("invalid research result limit")
        self._experiment_id = experiment_id
        self._port = port
        self._max_results = max_results

    async def search_web(
        self, query: str, *, limit: int | None = None
    ) -> tuple[SourceReference, ...] | tuple[str, ...]:
        try:
            limit = 10 if limit is None else limit
            if not query.strip() or len(query) > 600 or not 1 <= limit <= 20:
                raise ValueError
            limit = min(limit, self._max_results)
            request = BraveSearchRequest(
                capability=Capability.BRAVE_WEB_COVERAGE,
                query=SecretStr(query),
                limit=limit,
            )
            result = await self._port.search(self._experiment_id, request)
            if isinstance(result, TransientSearchUrls):
                if not isinstance(result.urls, tuple) or len(result.urls) > limit:
                    raise ValueError
                # Native tool messages are serialized in process. The service
                # owns transient rights; this facade returns only validated URLs.
                # The orchestrator must never checkpoint tool message history.
                return tuple(public_url(url) for url in result.urls)
            return self._references(result)
        except Exception as error:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise _research_tool_error(error) from None

    async def map_site(
        self, url: str, *, limit: int | None = None
    ) -> tuple[SourceReference, ...]:
        try:
            limit = 10 if limit is None else limit
            if not 1 <= limit <= 20:
                raise ValueError
            limit = min(limit, self._max_results)
            request = FirecrawlMapRequest(url=public_url(url), limit=limit)
            return self._references(await self._port.map(self._experiment_id, request))
        except Exception as error:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise _research_tool_error(error) from None

    async def capture_page(
        self, url: str, *, js_wait_ms: int = 0
    ) -> tuple[SourceReference, ...]:
        try:
            if not 0 <= js_wait_ms <= 5000:
                raise ValueError
            request = FirecrawlCaptureRequest(
                capability=Capability.FIRECRAWL_JS_RETRIEVAL
                if js_wait_ms
                else Capability.FIRECRAWL_PAGE_CAPTURE,
                url=public_url(url),
                formats=(CaptureFormat.MARKDOWN,),
                wait_ms=js_wait_ms,
            )
            return self._references(
                await self._port.capture(self._experiment_id, request)
            )
        except Exception as error:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise _research_tool_error(error) from None

    async def capture_pdf(self, url: str) -> tuple[SourceReference, ...]:
        try:
            request = FirecrawlCaptureRequest(
                capability=Capability.FIRECRAWL_PDF_CAPTURE,
                url=public_url(url),
                formats=(CaptureFormat.MARKDOWN,),
            )
            return self._references(
                await self._port.capture(self._experiment_id, request)
            )
        except Exception as error:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise _research_tool_error(error) from None

    async def read_saved_evidence(
        self, retained_id: UUID, *, max_chars: int = 4000
    ) -> SavedEvidenceExcerpt:
        try:
            if not isinstance(retained_id, UUID) or not 1 <= max_chars <= 4000:
                raise ValueError
            excerpt = await self._port.read_saved_evidence(
                self._experiment_id, retained_id, max_chars=max_chars
            )
            if (
                not isinstance(excerpt, SavedEvidenceExcerpt)
                or excerpt.reference.kind != "RETAINED_CONTENT"
                or excerpt.reference.retained_id != retained_id
                or not isinstance(excerpt.text, str)
                or len(excerpt.text) > max_chars
            ):
                raise ValueError
            return excerpt
        except Exception as error:  # noqa: BLE001 - no repository details cross tool boundary
            raise _research_tool_error(error) from None

    @staticmethod
    def _references(value: tuple[SourceReference, ...]) -> tuple[SourceReference, ...]:
        if (
            not isinstance(value, tuple)
            or len(value) > 20
            or any(ref.kind != "RETAINED_CONTENT" for ref in value)
        ):
            raise ValueError
        return value
