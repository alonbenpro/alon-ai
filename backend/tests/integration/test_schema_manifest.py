"""Compare the complete migrated application schema to its reviewed inventory."""

import json
from pathlib import Path

from sqlalchemy import text

from alon_ai.db.schema_manifest import collect_schema


async def test_migrated_schema_matches_reviewed_manifest(governance_engine):
    expected = json.loads(
        (
            Path(__file__).parents[3] / "docs/implementation/schema-manifest.json"
        ).read_text()
    )
    async with governance_engine.connect() as connection:
        actual = await collect_schema(connection)
    assert actual == expected


async def test_manifest_detects_columns_indexes_and_disabled_guards(governance_engine):
    # This fixture owns a disposable database; no application schema is altered.
    async with governance_engine.begin() as connection:
        before = await collect_schema(connection)
        await connection.execute(
            text("ALTER TABLE gov_calls ADD COLUMN unintended text")
        )
        await connection.execute(
            text("CREATE INDEX schema_manifest_probe ON gov_calls(created_at)")
        )
        await connection.execute(text("ALTER TABLE gov_calls DISABLE TRIGGER ALL"))
        await connection.execute(
            text("CREATE VIEW schema_manifest_probe_view AS SELECT 1 AS unexpected")
        )
        after = await collect_schema(connection)
    for component in ("columns", "indexes", "triggers", "views"):
        assert before[component] != after[component], component
