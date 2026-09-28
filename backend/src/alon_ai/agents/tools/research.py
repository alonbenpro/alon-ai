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
    public_url,
)
from alon_ai.services.schemas.records import SourceReference


class ResearchToolError(Exception):
    """Safe error marker with no provider response or request text."""

    def __init__(self) -> None:
        super().__init__("RESEARCH_TOOL_UNAVAILABLE")


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

    def __init__(self, experiment_id: UUID, port: GovernedResearchPort) -> None:
        self._experiment_id = experiment_id
        self._port = port

    async def search_web(
        self, query: str, *, limit: int = 10
    ) -> tuple[SourceReference, ...] | tuple[str, ...]:
        try:
            if not query.strip() or len(query) > 600 or not 1 <= limit <= 20:
                raise ValueError
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
        except Exception:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise ResearchToolError() from None

    async def map_site(
        self, url: str, *, limit: int = 10
    ) -> tuple[SourceReference, ...]:
        try:
            if not 1 <= limit <= 20:
                raise ValueError
            request = FirecrawlMapRequest(url=public_url(url), limit=limit)
            return self._references(await self._port.map(self._experiment_id, request))
        except Exception:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise ResearchToolError() from None

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
        except Exception:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise ResearchToolError() from None

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
        except Exception:  # noqa: BLE001 - no request/provider details cross tool boundary
            raise ResearchToolError() from None

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
        except Exception:  # noqa: BLE001 - no repository details cross tool boundary
            raise ResearchToolError() from None

    @staticmethod
    def _references(value: tuple[SourceReference, ...]) -> tuple[SourceReference, ...]:
        if (
            not isinstance(value, tuple)
            or len(value) > 20
            or any(ref.kind != "RETAINED_CONTENT" for ref in value)
        ):
            raise ValueError
        return value
