"""Read-only, deterministic PostgreSQL structure inventory for migration review.

No application rows, credentials, environment-specific owners or OIDs are exported.
Internal FK trigger names contain OIDs; their stable constraint/function/enablement
properties are recorded instead. Application trigger and function definitions are
included in full. This checks schema drift, not business correctness or privileges.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from alon_ai.config import get_settings

TABLE_FILTER = (
    "n.nspname='public' AND c.relkind IN ('r','p') AND c.relname<>'alembic_version'"
)

QUERIES = {
    "extensions": """
        SELECT e.extname AS name, e.extversion AS version, n.nspname AS schema
        FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
        WHERE e.extname<>'plpgsql'
    """,
    "views": """
        SELECT c.relname AS name, pg_get_viewdef(c.oid,true) AS definition
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind='v'
    """,
    "tables": f"""
        SELECT c.relname AS name, c.relkind AS kind, c.relrowsecurity AS row_security,
               c.relforcerowsecurity AS force_row_security
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE {TABLE_FILTER}
    """,
    "columns": f"""
        SELECT c.relname AS table_name, a.attname AS name,
               format_type(a.atttypid,a.atttypmod) AS type,
               a.attnotnull AS not_null, a.attidentity AS identity,
               a.attgenerated AS generated,
               pg_get_expr(d.adbin,d.adrelid,true) AS default_expression
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE {TABLE_FILTER} AND a.attnum>0 AND NOT a.attisdropped
    """,
    "constraints": f"""
        SELECT c.relname AS table_name, k.conname AS name, k.contype AS kind,
               pg_get_constraintdef(k.oid,true) AS definition,
               k.condeferrable AS deferrable, k.condeferred AS initially_deferred,
               k.convalidated AS validated, k.conenforced AS enforced
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_constraint k ON k.conrelid=c.oid
        WHERE {TABLE_FILTER}
    """,
    "indexes": f"""
        SELECT c.relname AS table_name, i.relname AS name,
               pg_get_indexdef(x.indexrelid) AS definition,
               x.indisvalid AS valid, x.indisready AS ready,
               x.indisunique AS unique_index, x.indisprimary AS primary_index
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_index x ON x.indrelid=c.oid JOIN pg_class i ON i.oid=x.indexrelid
        WHERE {TABLE_FILTER}
    """,
    "triggers": f"""
        SELECT c.relname AS table_name,
               CASE WHEN t.tgisinternal THEN NULL ELSE t.tgname END AS name,
               t.tgisinternal AS internal, t.tgenabled AS enabled,
               t.tgtype AS events, t.tgdeferrable AS deferrable,
               t.tginitdeferred AS initially_deferred,
               k.conname AS constraint_name, parent.relname AS constraint_table,
               pn.nspname || '.' || p.proname AS function_name,
               CASE WHEN t.tgisinternal THEN NULL
                    ELSE pg_get_triggerdef(t.oid,true) END AS definition
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_trigger t ON t.tgrelid=c.oid JOIN pg_proc p ON p.oid=t.tgfoid
        JOIN pg_namespace pn ON pn.oid=p.pronamespace
        LEFT JOIN pg_constraint k ON k.oid=t.tgconstraint
        LEFT JOIN pg_class parent ON parent.oid=k.conrelid
        WHERE {TABLE_FILTER}
    """,
    "functions": """
        SELECT p.proname AS name, pg_get_function_identity_arguments(p.oid) AS arguments,
               pg_get_functiondef(p.oid) AS definition
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.prokind='f'
    """,
}


def canonicalize_columns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exclude physical PostgreSQL attribute positions from logical schema review."""
    return sorted(
        ({key: value for key, value in row.items() if key != "ordinal"} for row in rows),
        key=lambda row: (row["table_name"], row["name"]),
    )


async def collect_schema(connection: AsyncConnection) -> dict[str, Any]:
    await connection.execute(text("SET LOCAL search_path TO public, pg_catalog"))
    version = int(
        (await connection.execute(text("SHOW server_version_num"))).scalar_one()
    )
    result: dict[str, Any] = {
        "manifest_version": 2,
        "postgres_major": version // 10000,
        "alembic_heads": sorted(
            (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalars()
        ),
    }
    for name, query in QUERIES.items():
        rows = [dict(row) for row in (await connection.execute(text(query))).mappings()]
        result[name] = (
            canonicalize_columns(rows)
            if name == "columns"
            else sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
        )
    return result


async def write_manifest(path: Path) -> None:
    engine = create_async_engine(
        get_settings().database_url.get_secret_value(), hide_parameters=True
    )
    try:
        async with engine.connect() as connection:
            result = await collect_schema(connection)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path, required=True)
    asyncio.run(write_manifest(parser.parse_args().write))
