import asyncio
import signal
from typing import cast

import structlog

from alon_ai.config import Settings, get_settings
from alon_ai.logging import configure_logging


def build_worker_startup_event(settings: Settings) -> dict[str, str | bool]:
    return {
        "event": "worker_ready",
        "service": "worker",
        "outreach_enabled": settings.outreach_enabled,
    }


async def wait_for_termination() -> None:
    terminated = asyncio.Event()
    loop = asyncio.get_running_loop()
    for termination_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(termination_signal, terminated.set)
        except NotImplementedError:
            pass
    await terminated.wait()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    startup_event = build_worker_startup_event(settings)
    structlog.get_logger().info(
        cast(str, startup_event["event"]),
        service=cast(str, startup_event["service"]),
        outreach_enabled=cast(bool, startup_event["outreach_enabled"]),
    )
    asyncio.run(wait_for_termination())


if __name__ == "__main__":
    main()
