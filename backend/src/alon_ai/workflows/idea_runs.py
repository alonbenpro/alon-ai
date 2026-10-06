"""DBOS execution of durably admitted operator Idea runs."""

from uuid import UUID

from dbos import DBOS, SetWorkflowID


@DBOS.step(name="execute_admitted_idea_run", retries_allowed=False, preemptible=True)
async def _execute_idea_run_step(run_id: str) -> None:
    from alon_ai.bootstrap import workflow_engine_scope
    from alon_ai.config import get_settings
    from alon_ai.services.agent_run_service import run_admitted_idea_job

    settings = get_settings()
    async with workflow_engine_scope() as engine:
        await run_admitted_idea_job(engine, settings, UUID(run_id))


@DBOS.workflow(name="admitted_idea_run")
async def admitted_idea_run_workflow(run_id: str) -> None:
    await _execute_idea_run_step(run_id)


async def dispatch_queued_idea_runs(engine) -> int:
    """Start queued bindings; stable workflow IDs make polling idempotent."""
    from alon_ai.services.agent_run_service import queued_idea_run_bindings

    rows = await queued_idea_run_bindings(engine)
    for row in rows:
        with SetWorkflowID(row["dbos_workflow_id"]):
            await DBOS.start_workflow_async(
                admitted_idea_run_workflow, str(row["run_id"])
            )
    return len(rows)
