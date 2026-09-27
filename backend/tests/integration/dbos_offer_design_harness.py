"""Subprocess harness for Offer Design DBOS recovery tests."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dbos import DBOS

from alon_ai.config import get_settings
from alon_ai.db.engine import create_engine
from alon_ai.db.repositories.workflow_offer_design import OfferDesignWorkflowRepository
from alon_ai.worker.config import configure_dbos
from alon_ai.workflows.offer_design import (
    finalize_offer_design_workflow,
    recover_offer_design_workflows,
    start_offer_design_workflow,
)
from alon_ai.workflows.schemas.offer_design import (
    OfferDesignDecisionWorkflowRequest,
    OfferIdeaRefinementWorkflowRequest,
    OfferTargetedResearchWorkflowRequest,
    offer_design_decision_workflow_id,
    offer_idea_refinement_workflow_id,
)
from alon_ai.workflows.schemas.runtime import DBOS_APPLICATION_VERSION


async def run(args: argparse.Namespace) -> None:
    engine = create_engine(get_settings())
    payload = json.loads(Path(args.request).read_text())
    raw = payload["request"]
    if "gap" in raw:
        request = OfferTargetedResearchWorkflowRequest.model_validate_json(
            json.dumps(payload)
        )
        workflow_id = offer_design_decision_workflow_id(
            request.request.run_id, request.command_key
        )
    elif "proposed_idea" in raw:
        request = OfferIdeaRefinementWorkflowRequest.model_validate_json(
            json.dumps(payload)
        )
        workflow_id = offer_idea_refinement_workflow_id(
            request.request.decision_id, request.command_key
        )
    else:
        request = OfferDesignDecisionWorkflowRequest.model_validate_json(
            json.dumps(payload)
        )
        workflow_id = offer_design_decision_workflow_id(
            request.request.run_id, request.command_key
        )
    try:
        configure_dbos(
            get_settings(),
            application_version=args.application_version,
            executor_id=args.executor_id,
        )
        DBOS.launch()
        runtime = OfferDesignWorkflowRepository(engine)
        if args.mode == "cancel":
            binding = await runtime.bind(
                request, application_version=args.application_version
            )
            await runtime.cancel(binding.dbos_workflow_id)
            await DBOS.cancel_workflow_async(workflow_id)
            return
        if args.mode == "start":
            handle = await start_offer_design_workflow(
                engine, request, application_version=args.application_version
            )
            result = await handle.get_result(polling_interval_sec=0.02)
            await finalize_offer_design_workflow(engine, workflow_id, result)
        else:
            result = (
                await recover_offer_design_workflows(engine, args.application_version)
            )[workflow_id]
        print("RESULT:" + json.dumps(result, sort_keys=True), flush=True)
    finally:
        await engine.dispose()
        DBOS.destroy(destroy_registry=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("start", "recover", "cancel"))
    parser.add_argument("--request", required=True)
    parser.add_argument("--application-version", default=DBOS_APPLICATION_VERSION)
    parser.add_argument("--executor-id", default="l04-offer-test")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
