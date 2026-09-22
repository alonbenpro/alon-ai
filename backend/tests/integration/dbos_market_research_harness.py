"""Subprocess entry point for destructive DBOS recovery tests."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from dbos import DBOS

from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine
from alon_ai.workflows import market_research
from alon_ai.workflows.market_research import (
    MarketResearchWorkflowRepository,
    MarketResearchWorkflowRequest,
    finalize_market_research_workflow,
    recover_market_research_workflows,
)


async def _barrier(phase: str) -> None:
    if phase != os.environ.get("ALON_AI_DBOS_TEST_BARRIER"):
        return
    ready = Path(os.environ["ALON_AI_DBOS_TEST_READY"])
    release = Path(os.environ["ALON_AI_DBOS_TEST_RELEASE"])
    ready.write_text(phase)
    while not release.exists():
        await asyncio.sleep(0.02)


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    request = (
        MarketResearchWorkflowRequest.model_validate_json(
            Path(args.request).read_text()
        )
        if args.request
        else None
    )
    market_research._set_test_barrier_for_testing(_barrier)
    try:
        if args.mode == "cancel":
            assert request is not None
            repository = MarketResearchWorkflowRepository(engine)
            binding = await repository.bind(
                request, application_version=args.application_version
            )
            await repository.cancel(binding.dbos_workflow_id)
        await market_research.assert_compatible_application_version(
            engine, args.application_version
        )
        market_research.configure_dbos(
            settings,
            application_version=args.application_version,
            executor_id=args.executor_id,
        )
        DBOS.launch()
        if args.mode == "launch":
            return
        assert request is not None
        if args.mode == "start":
            handle = await market_research.start_market_research_workflow(
                engine, request, application_version=args.application_version
            )
            result = await handle.get_result(polling_interval_sec=0.02)
            workflow_id = market_research.market_research_workflow_id(
                request.cycle_id, request.request_hash
            )
            await finalize_market_research_workflow(engine, workflow_id, result)
        elif args.mode == "recover":
            workflow_id = market_research.market_research_workflow_id(
                request.cycle_id, request.request_hash
            )
            recovered = await recover_market_research_workflows(
                engine, args.application_version
            )
            result = recovered[workflow_id]
        elif args.mode == "cancel":
            workflow_id = market_research.market_research_workflow_id(
                request.cycle_id, request.request_hash
            )
            await DBOS.cancel_workflow_async(workflow_id)
            return
        else:
            raise AssertionError(args.mode)
        print("RESULT:" + json.dumps(result, sort_keys=True), flush=True)
    finally:
        await engine.dispose()
        DBOS.destroy(destroy_registry=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("start", "recover", "cancel", "launch"))
    parser.add_argument("--request")
    parser.add_argument("--application-version", required=True)
    parser.add_argument("--executor-id", required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
