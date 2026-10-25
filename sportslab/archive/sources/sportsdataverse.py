"""Shared machinery for sportsdataverse (hoopR / wehoop) parquet releases.

The data is ESPN-derived and published as GitHub release assets on
``sportsdataverse/sportsdataverse-data``, one parquet file per season per table.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, console

API = "https://api.github.com/repos/sportsdataverse/sportsdataverse-data/releases/tags/{tag}"


def release_assets(tag: str, c: httpx.Client) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = c.get(API.format(tag=tag), headers=headers)
    if r.status_code == 404:
        console.print(f"[yellow]release tag {tag} not found[/yellow]")
        return []
    r.raise_for_status()
    return [a for a in r.json().get("assets", []) if a["name"].endswith(".parquet")]


class SportsdataverseSource(Source):
    schema: str = ""
    release_tags: dict[str, str] = {}  # table name -> release tag

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        for table, tag in self.release_tags.items():
            for a in release_assets(tag, c):
                ctx.get(a["browser_download_url"], f"{table}/{a['name']}", c, remote_size=a["size"])

    def build_tables(self, raw: Path) -> dict[str, int]:
        rows = {}
        for t in self.tables:
            src = raw / t.name
            if t.path.exists():
                shutil.rmtree(t.path)
            total = 0
            files = sorted(src.glob("*.parquet")) if src.exists() else []
            seasonal = [f for f in files if re.search(r"(\d{4})\.parquet$", f.name)]
            if seasonal:
                # releases also ship an all-seasons "master" file; it duplicates the per-season ones
                files = seasonal
            for i, f in enumerate(files):
                df = pl.read_parquet(f)
                m = re.search(r"(\d{4})\.parquet$", f.name)
                if m:
                    if "season" in df.columns:
                        df = df.drop("season")
                    out = t.path / f"season={m.group(1)}"
                else:
                    out = t.path
                out.mkdir(parents=True, exist_ok=True)
                df.write_parquet(out / f"part-{i}.parquet", compression="zstd")
                total += df.height
            rows[t.qualified] = total
        return rows
