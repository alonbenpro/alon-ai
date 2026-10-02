"""Offline contract tests for bounded research retrieval and agent tools."""

import asyncio
import base64
import sys
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from alon_ai.agents.tools.research import (
    ResearchToolError,
    ResearchTools,
    SavedEvidenceExcerpt,
)
from alon_ai.integrations.brave import BraveSearchAdapter
from alon_ai.integrations.firecrawl import FirecrawlAdapter
from alon_ai.integrations.schemas.provider import (
    BraveSearchRequest,
    Capability,
    ContentField,
    CostKnowledge,
    FirecrawlCaptureRequest,
    FirecrawlMapRequest,
    Provider,
    ProviderErrorCode,
    ProviderFailure,
    Purpose,
)
from alon_ai.policies.provider_rights import (
    IntendedUse,
    ProviderUsageGrant,
)
from alon_ai.provider_usage.schemas.accounting import AccountingDenied, Reason
from alon_ai.services.schemas.records import SourceReference

NOW = datetime(2026, 9, 28, tzinfo=UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [None, 10, 3])
async def test_research_tool_requests_respect_the_approved_result_limit(limit):
    requests = []

    class Port:
        async def search(self, experiment_id, request):
            requests.append(request)
            return ()

        async def map(self, experiment_id, request):
            requests.append(request)
            return ()

        async def capture(self, experiment_id, request):
            raise AssertionError("not used by this test")

        async def read_saved_evidence(self, experiment_id, retained_id, *, max_chars):
            raise AssertionError("not used by this test")

    tools = ResearchTools(uuid4(), Port(), max_results=5)
    kwargs = {} if limit is None else {"limit": limit}
    await tools.search_web("clinic workflows", **kwargs)
    await tools.map_site("https://example.com", **kwargs)
    assert [request.limit for request in requests] == [min(limit or 10, 5)] * 2


def authority(capability: Capability, fields: frozenset[ContentField]):
    provider = (
        Provider.BRAVE if capability.name.startswith("BRAVE") else Provider.FIRECRAWL
    )
    common = {
        "provider": provider,
        "account_handle": "research-test",
        "capability": capability,
        "plan_identifier": "test-plan",
        "order_form_ref": "test-order",
        "terms_version": "test-v1",
        "purpose": Purpose.RESEARCH,
    }
    grant = ProviderUsageGrant(
        **common,
        grant_id=uuid4(),
        version=1,
        outbound_use_permitted=False,
        storage_fields=fields,
        retention_rule_id=uuid4(),
        retention_seconds=3600,
        approved_by=uuid4(),
        approved_at=NOW - timedelta(days=1),
        effective_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=1),
        supporting_evidence_ref=uuid4(),
    )
    use = IntendedUse(**common, required_fields=fields)
    return grant, use


def firecrawl(capability, body, *, resolver=lambda _: ("93.184.215.14",), **policy):
    fields = (
        frozenset({ContentField.URL})
        if capability is Capability.FIRECRAWL_MAP
        else frozenset({ContentField.URL, ContentField.TEXT})
    )
    grant, use = authority(capability, fields)
    seen = []

    def handler(request):
        seen.append(request)
        if isinstance(body, int):
            return httpx.Response(body, headers={"Location": "http://127.0.0.1"})
        return httpx.Response(200, json=body)

    adapter = FirecrawlAdapter(
        SecretStr("never-log-this"),
        grant=grant,
        intended_use=use,
        events=lambda: (),
        clock=lambda: NOW,
        resolver=resolver,
        transport=httpx.MockTransport(handler),
        max_pdf_bytes=policy.get("max_pdf_bytes", 10_000),
        max_pdf_pages=policy.get("max_pdf_pages", 2),
        max_text_chars=policy.get("max_text_chars", 4000),
        pdf_cpu_seconds=policy.get("pdf_cpu_seconds", 2),
        pdf_memory_bytes=policy.get("pdf_memory_bytes", 268_435_456),
        pdf_wall_seconds=policy.get("pdf_wall_seconds", 5),
    )
    return adapter, grant, seen


@pytest.mark.asyncio
async def test_brave_one_bounded_call_and_retained_fields():
    grant, use = authority(
        Capability.BRAVE_WEB_COVERAGE,
        frozenset({ContentField.URL, ContentField.TITLE, ContentField.TEXT}),
    )
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.com/market",
                            "title": "Market",
                            "description": "Demand signal",
                        }
                    ]
                }
            },
        )

    adapter = BraveSearchAdapter(
        SecretStr("never-log-this"),
        grant=grant,
        intended_use=use,
        events=lambda: (),
        clock=lambda: NOW,
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.search(
        BraveSearchRequest(
            capability=Capability.BRAVE_WEB_COVERAGE,
            query=SecretStr("small business intake"),
            limit=2,
        )
    )
    assert len(seen) == 1
    assert seen[0].url.params["count"] == "2"
    assert seen[0].headers["x-subscription-token"] == "never-log-this"
    assert "never-log-this" not in repr(result)
    assert result.content is not None
    retained = result.content.retain(current_grant=grant, events=(), now=NOW)
    assert retained.fields[ContentField.URL] == ("https://example.com/market",)
    assert retained.fields[ContentField.TEXT] == ("Demand signal",)
    assert retained.expires_at == NOW + timedelta(hours=1)


@pytest.mark.asyncio
async def test_brave_denied_rights_and_redirects_before_exposing_content():
    grant, use = authority(Capability.BRAVE_WEB_COVERAGE, frozenset({ContentField.URL}))
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1"})

    adapter = BraveSearchAdapter(
        SecretStr("never-log-this"),
        grant=grant,
        intended_use=use,
        events=lambda: (),
        clock=lambda: NOW,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.search(
            BraveSearchRequest(
                capability=Capability.BRAVE_WEB_COVERAGE,
                query=SecretStr("test"),
            )
        )
    assert error.value.code is ProviderErrorCode.DENIED
    assert len(seen) == 1
    adapter._clock = lambda: NOW + timedelta(hours=2)
    with pytest.raises(ProviderFailure) as expired:
        await adapter.search(
            BraveSearchRequest(
                capability=Capability.BRAVE_WEB_COVERAGE,
                query=SecretStr("test"),
            )
        )
    assert expired.value.code is ProviderErrorCode.DENIED
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_firecrawl_map_denies_private_dns_and_redirect():
    adapter, _, seen = firecrawl(
        Capability.FIRECRAWL_MAP,
        {"success": True, "links": ["https://example.com/a"]},
        resolver=lambda _: ("127.0.0.1",),
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.map(FirecrawlMapRequest(url="https://example.com"))
    assert error.value.code is ProviderErrorCode.DENIED
    assert not seen
    adapter, _, seen = firecrawl(Capability.FIRECRAWL_MAP, 302)
    with pytest.raises(ProviderFailure) as error:
        await adapter.map(FirecrawlMapRequest(url="https://example.com"))
    assert error.value.code is ProviderErrorCode.DENIED
    assert len(seen) == 1
    adapter, _, _ = firecrawl(
        Capability.FIRECRAWL_MAP,
        {"success": True, "links": ["http://127.0.0.1/internal"]},
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.map(FirecrawlMapRequest(url="https://example.com"))
    assert error.value.code is ProviderErrorCode.DENIED


@pytest.mark.asyncio
async def test_firecrawl_map_and_page_use_fixed_options():
    adapter, grant, seen = firecrawl(
        Capability.FIRECRAWL_MAP,
        {
            "success": True,
            "links": [
                {"url": "https://example.com/a"},
                {"url": "https://example.com/b"},
            ],
        },
    )
    mapped = await adapter.map(FirecrawlMapRequest(url="https://example.com", limit=2))
    assert len(seen) == 1
    assert seen[0].url.path == "/v2/map"
    assert b'"limit":2' in seen[0].content
    assert mapped.metadata.usage[0].quantity == 2
    assert mapped.metadata.usage[0].cost is None
    assert mapped.metadata.usage[0].knowledge is CostKnowledge.UNAVAILABLE
    assert mapped.content is not None
    assert mapped.content.retain(current_grant=grant, events=(), now=NOW).fields == {
        ContentField.URL: ("https://example.com/a", "https://example.com/b")
    }
    adapter, grant, seen = firecrawl(
        Capability.FIRECRAWL_PAGE_CAPTURE,
        {
            "success": True,
            "data": {
                "markdown": "Evidence",
                "metadata": {"title": "T", "sourceURL": "https://example.com/a"},
            },
        },
    )
    result = await adapter.capture(FirecrawlCaptureRequest(url="https://example.com/a"))
    assert len(seen) == 1
    assert b'"proxy":"basic"' in seen[0].content
    assert b'"parsers":[]' in seen[0].content
    assert b'"skipTlsVerification":false' in seen[0].content
    assert result.content is not None
    assert result.content.retain(current_grant=grant, events=(), now=NOW).fields[
        ContentField.TEXT
    ] == ("Evidence",)


@pytest.mark.asyncio
async def test_firecrawl_map_empty_and_over_limit_do_not_invent_usage():
    adapter, _, _ = firecrawl(Capability.FIRECRAWL_MAP, {"success": True, "links": []})
    empty = await adapter.map(FirecrawlMapRequest(url="https://example.com", limit=2))
    assert empty.metadata.usage[0].quantity == 0
    assert empty.metadata.usage[0].cost is None
    assert empty.metadata.usage[0].knowledge is CostKnowledge.UNAVAILABLE
    adapter, _, _ = firecrawl(
        Capability.FIRECRAWL_MAP,
        {"success": True, "links": ["https://example.com/a", "https://example.com/b"]},
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.map(FirecrawlMapRequest(url="https://example.com", limit=1))
    assert error.value.code is ProviderErrorCode.MALFORMED_RESPONSE


def _pdf(text: str, *, pages: int = 1) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in range(3, 3 + pages))}] /Count {pages} >>".encode(),
    ]
    for index in range(pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {3 + pages + index} 0 R /Resources << /Font << /F1 {3 + 2 * pages} 0 R >> >> >>".encode()
        )
    for _ in range(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF".encode()
    )
    return bytes(output)


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform != "linux", reason="requires Linux address-space limits"
)
async def test_flat_credit_pdf_extracts_locally_with_byte_and_page_caps():
    pytest.importorskip("pypdf")
    raw = _pdf("Evidence")
    adapter, grant, seen = firecrawl(
        Capability.FIRECRAWL_PDF_CAPTURE,
        {"success": True, "data": {"rawBase64": base64.b64encode(raw).decode()}},
    )
    result = await adapter.capture(
        FirecrawlCaptureRequest(
            capability=Capability.FIRECRAWL_PDF_CAPTURE,
            url="https://example.com/report.pdf",
        )
    )
    assert len(seen) == 1
    assert b'"parsers":[]' in seen[0].content
    assert b'"formats":["rawBase64"]' in seen[0].content
    assert result.content is not None
    assert (
        "Evidence"
        in result.content.retain(current_grant=grant, events=(), now=NOW).fields[
            ContentField.TEXT
        ][0]
    )
    for policy in (
        {"max_pdf_bytes": len(raw) - 1},
        {"max_pdf_pages": 1},
        {"max_text_chars": 3},
    ):
        body = {
            "success": True,
            "data": {"rawBase64": base64.b64encode(_pdf("Evidence", pages=2)).decode()},
        }
        adapter, _, _ = firecrawl(Capability.FIRECRAWL_PDF_CAPTURE, body, **policy)
        with pytest.raises(ProviderFailure):
            await adapter.capture(
                FirecrawlCaptureRequest(
                    capability=Capability.FIRECRAWL_PDF_CAPTURE,
                    url="https://example.com/report.pdf",
                )
            )


@pytest.mark.asyncio
async def test_invalid_pdf_and_tool_errors_are_redacted(monkeypatch):
    # Malformed input never reaches the child parser on any platform.
    monkeypatch.setattr(
        "alon_ai.integrations.firecrawl.pdf_sandbox_supported", lambda: True
    )
    pytest.importorskip("pypdf")
    adapter, _, _ = firecrawl(
        Capability.FIRECRAWL_PDF_CAPTURE,
        {
            "success": True,
            "data": {"rawBase64": base64.b64encode(b"not a pdf").decode()},
        },
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.capture(
            FirecrawlCaptureRequest(
                capability=Capability.FIRECRAWL_PDF_CAPTURE,
                url="https://example.com/report.pdf",
            )
        )
    assert error.value.code is ProviderErrorCode.MALFORMED_RESPONSE
    adapter, _, _ = firecrawl(
        Capability.FIRECRAWL_PDF_CAPTURE,
        {
            "success": True,
            "data": {
                "rawBase64": base64.b64encode(_pdf("Evidence")).decode(),
                "metadata": {"sourceURL": "http://127.0.0.1/internal"},
            },
        },
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.capture(
            FirecrawlCaptureRequest(
                capability=Capability.FIRECRAWL_PDF_CAPTURE,
                url="https://example.com/report.pdf",
            )
        )
    assert error.value.code is ProviderErrorCode.MALFORMED_RESPONSE

    class Port:
        async def search(self, experiment_id, request):
            raise RuntimeError("provider key: never-log-this")

        async def map(self, experiment_id, request):
            raise RuntimeError("provider key: never-log-this")

        async def capture(self, experiment_id, request):
            raise RuntimeError("provider key: never-log-this")

        async def read_saved_evidence(self, experiment_id, retained_id, *, max_chars):
            return SavedEvidenceExcerpt(
                SourceReference.governance_evidence(uuid4()), "not retained"
            )

    tools = ResearchTools(uuid4(), Port())
    with pytest.raises(ResearchToolError) as error:
        await tools.search_web("test")
    assert "never-log-this" not in str(error.value)
    with pytest.raises(ResearchToolError):
        await tools.read_saved_evidence(uuid4())


@pytest.mark.asyncio
async def test_research_tools_preserve_safe_accounting_denial_code():
    class Port:
        async def search(self, experiment_id, request):
            raise AccountingDenied(Reason.CONCURRENCY)

        async def map(self, experiment_id, request):
            raise AccountingDenied(Reason.CONCURRENCY)

        async def capture(self, experiment_id, request):
            raise AccountingDenied(Reason.CONCURRENCY)

        async def read_saved_evidence(self, experiment_id, retained_id, *, max_chars):
            raise AccountingDenied(Reason.CONCURRENCY)

    with pytest.raises(ResearchToolError) as raised:
        await ResearchTools(uuid4(), Port()).search_web("clinic workflows")

    assert raised.value.code == "CONCURRENCY"


@pytest.mark.asyncio
async def test_research_tools_preserve_safe_provider_cause_of_uncertain_outcome():
    class Port:
        async def search(self, experiment_id, request):
            try:
                raise ProviderFailure(ProviderErrorCode.UNAVAILABLE)
            except ProviderFailure as error:
                raise AccountingDenied(Reason.UNCERTAIN) from error

        async def map(self, experiment_id, request):
            raise AssertionError

        async def capture(self, experiment_id, request):
            raise AssertionError

        async def read_saved_evidence(self, experiment_id, retained_id, *, max_chars):
            raise AssertionError

    with pytest.raises(ResearchToolError) as raised:
        await ResearchTools(uuid4(), Port()).search_web("clinic workflows")

    assert raised.value.code == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_research_tools_reject_unbounded_requests_before_service_dispatch():
    class Port:
        calls = 0

        async def search(self, experiment_id, request):
            self.calls += 1
            return ()

        async def map(self, experiment_id, request):
            self.calls += 1
            return ()

        async def capture(self, experiment_id, request):
            self.calls += 1
            return ()

        async def read_saved_evidence(self, experiment_id, retained_id, *, max_chars):
            self.calls += 1
            raise AssertionError

    port = Port()
    tools = ResearchTools(uuid4(), port)
    with pytest.raises(ResearchToolError):
        await tools.search_web("query", limit=21)
    with pytest.raises(ResearchToolError):
        await tools.map_site("https://example.com", limit=21)
    with pytest.raises(ResearchToolError):
        await tools.capture_page("https://example.com", js_wait_ms=5001)
    with pytest.raises(ResearchToolError):
        await tools.read_saved_evidence(uuid4(), max_chars=4001)
    assert port.calls == 0


@pytest.mark.asyncio
async def test_pdf_unavailable_sandbox_fails_before_provider_call(monkeypatch):
    monkeypatch.setattr(
        "alon_ai.integrations.firecrawl.pdf_sandbox_supported",
        lambda: False,
        raising=False,
    )
    adapter, _, seen = firecrawl(
        Capability.FIRECRAWL_PDF_CAPTURE,
        {
            "success": True,
            "data": {"rawBase64": base64.b64encode(_pdf("Evidence")).decode()},
        },
    )
    with pytest.raises(ProviderFailure) as error:
        await adapter.capture(
            FirecrawlCaptureRequest(
                capability=Capability.FIRECRAWL_PDF_CAPTURE,
                url="https://example.com/report.pdf",
            )
        )
    assert error.value.code is ProviderErrorCode.UNAVAILABLE
    assert not seen


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "behavior,expected",
    [
        ("import time; time.sleep(60)", "timeout"),
        (
            "import sys; sys.stdout.write('x' * 1000000); sys.stdout.flush()",
            "malformed_response",
        ),
    ],
)
async def test_pdf_worker_timeout_and_output_cap_kill_child(
    monkeypatch, behavior, expected
):
    from alon_ai.integrations import pdf_sandbox

    processes = []
    spawn = asyncio.create_subprocess_exec

    async def hostile_worker(*args, **kwargs):
        process = await spawn(sys.executable, "-I", "-c", behavior, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(pdf_sandbox, "pdf_sandbox_supported", lambda: True)
    monkeypatch.setattr(pdf_sandbox.asyncio, "create_subprocess_exec", hostile_worker)
    with pytest.raises(pdf_sandbox.PdfSandboxFailure) as error:
        await pdf_sandbox.extract_pdf(
            _pdf("Evidence"),
            max_bytes=10000,
            max_pages=2,
            max_chars=4000,
            cpu_seconds=1,
            memory_bytes=268435456,
            wall_seconds=1,
        )
    assert error.value.kind == expected
    assert len(processes) == 1
    assert processes[0].returncode is not None


@pytest.mark.parametrize(
    "policy",
    [
        {"pdf_cpu_seconds": True},
        {"pdf_cpu_seconds": 0},
        {"pdf_memory_bytes": 0},
        {"pdf_memory_bytes": 2**40},
        {"pdf_wall_seconds": float("inf")},
        {"pdf_wall_seconds": 0},
    ],
)
def test_pdf_resource_policy_is_required_and_bounded(policy):
    with pytest.raises(ValueError):
        firecrawl(Capability.FIRECRAWL_PDF_CAPTURE, {}, **policy)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {"sourceURL": "https://example.com/a", "url": "http://127.0.0.1/internal"},
        {"sourceURL": "https://example.com/a", "url": "https://other.example/a"},
        {"sourceURL": "https://example.com:8443/a"},
        {"statusCode": 302},
        {"statusCode": True},
        {"error": "fetch failed"},
    ],
)
async def test_firecrawl_rejects_unsafe_reported_fetch_metadata(metadata):
    adapter, _, _ = firecrawl(
        Capability.FIRECRAWL_PAGE_CAPTURE,
        {"success": True, "data": {"markdown": "Evidence", "metadata": metadata}},
    )
    with pytest.raises(ProviderFailure):
        await adapter.capture(FirecrawlCaptureRequest(url="https://example.com/a"))


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform != "linux", reason="requires Linux address-space limits"
)
@pytest.mark.parametrize(
    "parser_body,expected",
    [
        ("while True: pass", "timeout"),
        (
            (
                "bytearray(256 * 1024**2); return types.SimpleNamespace("
                "is_encrypted=False, pages=[types.SimpleNamespace("
                "extract_text=lambda **kwargs: 'escaped')])"
            ),
            "malformed_response",
        ),
    ],
)
async def test_pdf_worker_enforces_os_cpu_and_memory_limits(
    monkeypatch, parser_body, expected
):
    from alon_ai.integrations import pdf_sandbox

    spawn = asyncio.create_subprocess_exec

    async def hostile_parser(*args, **kwargs):
        # Substitute only the parser. The real worker installs OS limits before
        # invoking it; failures disappear if those production limits are removed.
        script = (
            "import runpy, sys, types\n"
            "fake = types.ModuleType('pypdf')\n"
            "def reader(*args, **kwargs):\n"
            f"    {parser_body}\n"
            "fake.PdfReader = reader\n"
            "sys.modules['pypdf'] = fake\n"
            f"sys.argv = {list(args[2:])!r}\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n"
        )
        return await spawn(sys.executable, "-I", "-c", script, **kwargs)

    monkeypatch.setattr(pdf_sandbox.asyncio, "create_subprocess_exec", hostile_parser)
    started = time.monotonic()
    with pytest.raises(pdf_sandbox.PdfSandboxFailure) as error:
        await pdf_sandbox.extract_pdf(
            _pdf("Evidence"),
            max_bytes=10000,
            max_pages=2,
            max_chars=4000,
            cpu_seconds=1,
            memory_bytes=128 * 1024**2,
            wall_seconds=5,
        )
    assert error.value.kind == expected

    # CPU enforcement must fire before the separate five-second wall timeout.
    assert time.monotonic() - started < 4


@pytest.mark.asyncio
async def test_cancelled_pdf_extraction_reaps_child(monkeypatch):
    from alon_ai.integrations import pdf_sandbox

    spawn = asyncio.create_subprocess_exec
    ready = asyncio.Event()
    processes = []

    async def sleeping_parser(*args, **kwargs):
        process = await spawn(
            sys.executable, "-I", "-c", "import time; time.sleep(60)", **kwargs
        )
        processes.append(process)
        ready.set()
        return process

    monkeypatch.setattr(pdf_sandbox, "pdf_sandbox_supported", lambda: True)
    monkeypatch.setattr(pdf_sandbox.asyncio, "create_subprocess_exec", sleeping_parser)
    task = asyncio.create_task(
        pdf_sandbox.extract_pdf(
            _pdf("Evidence"),
            max_bytes=10000,
            max_pages=2,
            max_chars=4000,
            cpu_seconds=2,
            memory_bytes=268435456,
            wall_seconds=5,
        )
    )
    await asyncio.wait_for(ready.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert processes[0].returncode is not None
