"""Read-only projections of authoritative provider call activity."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class OperatorActivityRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def status_counts(self):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        text(
                            "SELECT state,count(*) AS total FROM gov_calls GROUP BY state"
                        )
                    )
                )
                .mappings()
                .all()
            )

    async def activity_rows(self, experiment_id: UUID | None):
        async with self.engine.connect() as connection:
            return (
                (
                    await connection.execute(
                        text("""SELECT c.id, o.kind, c.state,
                    coalesce(c.finished_at,c.created_at) AS occurred_at
                    FROM gov_calls c JOIN gov_operations o ON o.id=c.operation_id
                    WHERE (CAST(:experiment_id AS UUID) IS NULL OR c.experiment_id=:experiment_id)
                    ORDER BY c.created_at DESC,c.id DESC LIMIT 50"""),
                        {"experiment_id": experiment_id},
                    )
                )
                .mappings()
                .all()
            )
