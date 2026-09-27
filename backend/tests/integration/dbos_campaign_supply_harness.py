"""Subprocess entry point for durable campaign-supply recovery tests."""

import argparse
import asyncio
import json
from pathlib import Path

from dbos import DBOS

from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine
from alon_ai.db.repositories.workflow_campaign_supply import (
    CampaignSupplyWorkflowRepository,
)
from alon_ai.worker.config import configure_dbos
from alon_ai.workflows.campaign_supply import (
    finalize_campaign_supply_workflow,
    recover_campaign_supply_workflows,
    start_campaign_supply_workflow,
)
from alon_ai.workflows.schemas.campaign_supply import (
    CampaignSupplyWorkflowRequest,
    campaign_supply_workflow_id,
)
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION


async def run(args: argparse.Namespace) -> None:
    engine = create_engine(get_settings())
    request = CampaignSupplyWorkflowRequest.model_validate_json(
        Path(args.request).read_text()
    )
    workflow_id = campaign_supply_workflow_id(request)
    try:
        configure_dbos(
            get_settings(),
            application_version=args.application_version,
            executor_id=args.executor_id,
        )
        DBOS.launch()
        runtime = CampaignSupplyWorkflowRepository(engine)
        if args.mode == "cancel":
            await runtime.bind(request, application_version=args.application_version)
            await runtime.cancel(workflow_id)
            await DBOS.cancel_workflow_async(workflow_id)
            return
        if args.mode == "start":
            handle = await start_campaign_supply_workflow(
                engine, request, application_version=args.application_version
            )
            result = await handle.get_result(polling_interval_sec=0.02)
            await finalize_campaign_supply_workflow(engine, workflow_id, result)
        else:
            result = (
                await recover_campaign_supply_workflows(
                    engine, args.application_version
                )
            )[workflow_id]
        if args.report_next_action:
            next_action = await runtime.next_action(request.experiment_id)
            print("NEXT_ACTION:" + next_action.model_dump_json(), flush=True)
        print("RESULT:" + json.dumps(result, sort_keys=True), flush=True)
    finally:
        await engine.dispose()
        DBOS.destroy(destroy_registry=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("start", "recover", "cancel"))
    parser.add_argument("--request", required=True)
    parser.add_argument("--application-version", default=DBOS_APPLICATION_VERSION)
    parser.add_argument("--executor-id", default="l04-supply-test")
    parser.add_argument("--report-next-action", action="store_true")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
