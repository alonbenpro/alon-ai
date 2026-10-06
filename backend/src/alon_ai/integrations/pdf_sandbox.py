"""Resource-isolated PDF text extraction on Linux.

This bounds parser resource exhaustion, not arbitrary code execution: the child
still runs as the service user. No provider secret/environment is passed to it.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from io import BytesIO
from pathlib import Path


class PdfSandboxFailure(Exception):
    """A content-free failure that the provider adapter can safely classify."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(kind)


def pdf_sandbox_supported() -> bool:
    # RLIMIT_RSS is not an allocation ceiling. Only enable the tested Linux
    # RLIMIT_AS implementation; other platforms must not parse in the worker.
    return sys.platform == "linux"


def validate_pdf_limits(cpu_seconds: int, memory_bytes: int, wall_seconds: int) -> None:
    if (
        type(cpu_seconds) is not int
        or not 1 <= cpu_seconds <= 10
        or type(memory_bytes) is not int
        or not 64 * 1024**2 <= memory_bytes <= 512 * 1024**2
        or type(wall_seconds) is not int
        or not 1 <= wall_seconds <= 30
    ):
        raise ValueError("bounded PDF resource policy required")


async def extract_pdf(
    raw: bytes,
    *,
    max_bytes: int,
    max_pages: int,
    max_chars: int,
    cpu_seconds: int,
    memory_bytes: int,
    wall_seconds: int,
) -> str:
    """Send bounded input to a fresh interpreter; kill/reap it on any failure."""
    validate_pdf_limits(cpu_seconds, memory_bytes, wall_seconds)
    if not pdf_sandbox_supported():
        raise PdfSandboxFailure("unavailable")
    if len(raw) > max_bytes or not raw.startswith(b"%PDF-"):
        raise PdfSandboxFailure("malformed_response")
    process: asyncio.subprocess.Process | None = None
    try:
        async with asyncio.timeout(wall_seconds):
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",
                str(Path(__file__).resolve()),
                str(max_bytes),
                str(max_pages),
                str(max_chars),
                str(cpu_seconds),
                str(memory_bytes),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={},
                limit=16_384,
            )
            assert process.stdin is not None and process.stdout is not None

            async def write_input() -> None:
                assert process is not None and process.stdin is not None
                try:
                    # Never queue the full PDF in the subprocess transport.
                    for offset in range(0, len(raw), 16_384):
                        process.stdin.write(raw[offset : offset + 16_384])
                        await process.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    process.stdin.close()

            async def read_output() -> bytes:
                assert process is not None and process.stdout is not None
                output = bytearray()
                # UTF-8 needs at most four bytes per retained character.
                max_output = max_chars * 4
                while chunk := await process.stdout.read(
                    min(16_384, max_output + 1 - len(output))
                ):
                    output.extend(chunk)
                    if len(output) > max_output:
                        raise PdfSandboxFailure("malformed_response")
                return bytes(output)

            writer = asyncio.create_task(write_input())
            try:
                output = await read_output()
                await writer
                returncode = await process.wait()
            finally:
                if not writer.done():
                    writer.cancel()
                await asyncio.gather(writer, return_exceptions=True)
            if returncode == 3:
                raise PdfSandboxFailure("unavailable")
            if returncode == -signal.SIGXCPU:
                raise PdfSandboxFailure("timeout")
            if returncode != 0:
                raise PdfSandboxFailure("malformed_response")
            content = output.decode("utf-8", errors="strict")
            if not content.strip() or len(content) > max_chars:
                raise PdfSandboxFailure("malformed_response")
            return content
    except TimeoutError:
        raise PdfSandboxFailure("timeout") from None
    except UnicodeError:
        raise PdfSandboxFailure("malformed_response") from None
    except OSError:
        raise PdfSandboxFailure("unavailable") from None
    finally:
        # Also runs on task cancellation: no parser survives its caller.
        if process is not None:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            # Drain the finite pipe buffer after killing; asyncio Process.wait
            # can otherwise wait forever on a paused stdout transport.
            if process.stdout is not None:
                while await process.stdout.read(16_384):
                    pass
            await process.wait()


def _worker() -> int:
    if not pdf_sandbox_supported():
        return 3
    try:
        import resource

        max_bytes, max_pages, max_chars, cpu_seconds, memory_bytes = map(
            int, sys.argv[1:]
        )
        validate_pdf_limits(cpu_seconds, memory_bytes, 1)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    except (ImportError, AttributeError, OSError, ValueError):
        return 3
    try:
        # Limit allocation before importing the parser or reading any input.
        from pypdf import PdfReader

        raw = sys.stdin.buffer.read(max_bytes + 1)
        if len(raw) > max_bytes or not raw.startswith(b"%PDF-"):
            return 2
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= max_pages:
            return 2
        pages: list[str] = []
        size = 0
        for page in reader.pages:
            extracted = page.extract_text(extraction_mode="plain")
            if not isinstance(extracted, str):
                return 2
            size += len(extracted) + (2 if pages else 0)
            if size > max_chars:
                return 2
            pages.append(extracted)
        content = "\n\n".join(pages)
        if not content.strip():
            return 2
        sys.stdout.buffer.write(content.encode("utf-8"))
        return 0
    except ImportError:
        return 3
    except Exception:  # noqa: BLE001 - never emit parser errors or document bytes
        return 2


if __name__ == "__main__":
    sys.exit(_worker())
