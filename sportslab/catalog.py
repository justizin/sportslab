"""DuckDB catalog: one view per parquet table directory, grouped into schemas by sport.

The database file holds only view definitions, so it is cheap to rebuild and safe to delete.
Query with ``sportslab sql`` or ``duckdb.connect(DB_PATH, read_only=True)``.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from sportslab.paths import DB_PATH, PARQUET_ROOT


def discover_tables(root: Path | None = None) -> list[tuple[str, str, Path]]:
    """(schema, table, dir) for every directory under root that holds parquet files."""
    root = root or PARQUET_ROOT
    out = []
    if not root.exists():
        return out
    for schema_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for table_dir in sorted(p for p in schema_dir.iterdir() if p.is_dir()):
            if any(table_dir.rglob("*.parquet")):
                out.append((schema_dir.name, table_dir.name, table_dir))
    return out


def build(db_path: Path | None = None, root: Path | None = None) -> list[str]:
    db_path = db_path or DB_PATH
    root = root or PARQUET_ROOT
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    created = []
    try:
        for schema, table, d in discover_tables(root):
            con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            glob = str(d / "**" / "*.parquet").replace("'", "''")
            con.execute(
                f'CREATE OR REPLACE VIEW "{schema}"."{table}" AS '
                f"SELECT * FROM read_parquet('{glob}', hive_partitioning = true, union_by_name = true)"
            )
            created.append(f"{schema}.{table}")
    finally:
        con.close()
    return created


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        build()
    return duckdb.connect(str(DB_PATH), read_only=read_only)
