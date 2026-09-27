import asyncio
import signal
from typing import cast

import structlog
from dbos import DBOS

from alon_ai.config import Settings, get_settings
from alon_ai.db.engine import create_engine
from alon_ai.logging import configure_logging
from alon_ai.worker.config import configure_dbos
from alon_ai.workflows.campaign_supply import (
    assert_campaign_supply_compatible_application_version,
    recover_campaign_supply_workflows,
)
from alon_ai.workflows.market_research import (
    assert_compatible_application_version,
    recover_market_research_decision_workflows,
    recover_market_research_workflows,
)
from alon_ai.workflows.offer_design import (
    assert_offer_design_compatible_application_version,
    recover_offer_design_workflows,
)
from alon_ai.workflows.schemas.runtime import (
    DBOS_APPLICATION_NAME,
    DBOS_APPLICATION_VERSION,
)

DBOS_EXECUTOR_ID = "alon-ai-worker"


def build_worker_startup_event(settings: Settings) -> dict[str, str | bool]:
    return {
        "event": "worker_ready",
        "service": "worker",
        "outreach_enabled": settings.outreach_enabled,
        "dbos_application": DBOS_APPLICATION_NAME,
        "dbos_application_version": DBOS_APPLICATION_VERSION,
        "dbos_executor_id": DBOS_EXECUTOR_ID,
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


async def run_worker(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        await assert_compatible_application_version(engine, DBOS_APPLICATION_VERSION)
        await assert_offer_design_compatible_application_version(
            engine, DBOS_APPLICATION_VERSION
        )
        await assert_campaign_supply_compatible_application_version(
            engine, DBOS_APPLICATION_VERSION
        )
        configure_dbos(settings, executor_id=DBOS_EXECUTOR_ID)
        DBOS.launch()
        try:
            await recover_market_research_workflows(engine, DBOS_APPLICATION_VERSION)
            await recover_market_research_decision_workflows(
                engine, DBOS_APPLICATION_VERSION
            )
            await recover_offer_design_workflows(engine, DBOS_APPLICATION_VERSION)
            await recover_campaign_supply_workflows(engine, DBOS_APPLICATION_VERSION)
            startup_event = build_worker_startup_event(settings)
            structlog.get_logger().info(
                cast(str, startup_event["event"]),
                service=cast(str, startup_event["service"]),
                outreach_enabled=cast(bool, startup_event["outreach_enabled"]),
                dbos_application=cast(str, startup_event["dbos_application"]),
                dbos_application_version=cast(
                    str, startup_event["dbos_application_version"]
                ),
                dbos_executor_id=cast(str, startup_event["dbos_executor_id"]),
            )
            await wait_for_termination()
        finally:
            DBOS.destroy(workflow_completion_timeout_sec=5)
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run_worker(settings))


if __name__ == "__main__":
    main()
