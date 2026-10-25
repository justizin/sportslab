"""Where things live on disk.

Everything under ``data/`` is gitignored. Override the root with ``SPORTSLAB_DATA``
if you want the archive on a different volume.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get("SPORTSLAB_DATA", REPO_ROOT / "data"))

RAW_ROOT = DATA_ROOT / "raw"  # immutable downloads, one dated dir per fetch
PARQUET_ROOT = DATA_ROOT / "parquet"  # normalized tables: <schema>/<table>/[partition=.../]*.parquet
DB_PATH = DATA_ROOT / "sportslab.duckdb"  # DuckDB catalog of views over the parquet tree


def raw_dir(source: str) -> Path:
    return RAW_ROOT / source


def table_dir(schema: str, table: str) -> Path:
    return PARQUET_ROOT / schema / table
