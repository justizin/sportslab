"""Base class every data source implements.

A source knows how to ``fetch`` raw files into a dated, immutable directory with a
manifest, and how to ``normalize`` the newest raw directory into parquet tables under
``data/parquet/<schema>/<table>/``.

Idempotence: ``fetch`` compares each remote file against the previous manifest. When the
server reports the same byte length (or the content hashes identically after download),
the previous file is hard-linked into the new dated dir instead of being stored twice.
If nothing changed at all, no new dated dir is created.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx
import polars as pl
import pyarrow.parquet as pq
from rich.console import Console

from sportslab.archive.http import client, download, head_size, is_missing
from sportslab.archive.manifest import Manifest, dated_dir, latest_fetch
from sportslab.paths import table_dir

console = Console(stderr=True)


@dataclass(frozen=True)
class Table:
    schema: str
    name: str
    description: str = ""

    @property
    def qualified(self) -> str:
        return f"{self.schema}.{self.name}"

    @property
    def path(self) -> Path:
        return table_dir(self.schema, self.name)


class Source:
    """Subclass and set the class attributes; implement ``fetch_into`` and ``normalize``."""

    name: str = ""
    sport: str = ""
    description: str = ""
    homepage: str = ""
    license: str = ""
    attribution: str = ""  # text that must accompany any published use
    tables: tuple[Table, ...] = ()
    opt_in: bool = False  # large sources are skipped by ``fetch --all`` unless named

    # ------------------------------------------------------------------ fetch
    def fetch(self, force: bool = False) -> Path | None:
        """Download into a new dated dir. Returns the dir, or None when nothing changed."""
        prev_dir = latest_fetch(self.name)
        prev = Manifest.read(prev_dir).by_name() if prev_dir else {}
        new_dir = dated_dir(self.name)
        if new_dir.exists() and not force and prev_dir == new_dir:
            console.print(f"[dim]{self.name}: already fetched today ({new_dir})[/dim]")
            return new_dir
        work = new_dir.with_name(new_dir.name + ".tmp")
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        manifest = Manifest.new(self.name, self.license, self.attribution)
        ctx = _FetchContext(self, work, prev_dir, prev, manifest, force)
        try:
            with client() as c:
                self.fetch_into(ctx, c)
        except BaseException:
            shutil.rmtree(work, ignore_errors=True)
            raise
        if ctx.changed == 0 and prev_dir is not None and not force:
            shutil.rmtree(work)
            console.print(f"[dim]{self.name}: unchanged since {prev_dir.name}[/dim]")
            return None
        manifest.write(work)
        if new_dir.exists():
            shutil.rmtree(new_dir)
        work.rename(new_dir)
        console.print(
            f"{self.name}: {len(manifest.files)} files, {ctx.changed} new or changed -> {new_dir}"
        )
        return new_dir

    def fetch_into(self, ctx: _FetchContext, c: httpx.Client) -> None:  # pragma: no cover
        raise NotImplementedError

    # -------------------------------------------------------------- normalize
    def normalize(self, raw: Path | None = None) -> dict[str, int]:
        """Build parquet tables from the newest (or given) raw dir. Returns rows per table."""
        raw = raw or latest_fetch(self.name)
        if raw is None:
            raise FileNotFoundError(f"{self.name}: nothing fetched yet; run `sportslab archive fetch {self.name}`")
        return self.build_tables(raw)

    def build_tables(self, raw: Path) -> dict[str, int]:  # pragma: no cover
        raise NotImplementedError

    # ----------------------------------------------------------------- status
    def status(self) -> dict:
        raw = latest_fetch(self.name)
        rows = {}
        for t in self.tables:
            files = list(t.path.rglob("*.parquet")) if t.path.exists() else []
            # row counts from parquet footers: fast, and indifferent to schema drift between seasons
            rows[t.qualified] = sum(pq.ParquetFile(f).metadata.num_rows for f in files) if files else None
        return {"source": self.name, "sport": self.sport, "last_fetch": raw.name if raw else None, "rows": rows}


class _FetchContext:
    """Hands a source the helpers it needs while fetching, and tracks what changed."""

    def __init__(self, source: Source, work: Path, prev_dir: Path | None, prev: dict, manifest: Manifest, force: bool):
        self.source = source
        self.work = work
        self.prev_dir = prev_dir
        self.prev = prev
        self.manifest = manifest
        self.force = force
        self.changed = 0

    def get(
        self,
        url: str,
        name: str,
        c: httpx.Client,
        check_size: bool = True,
        optional: bool = False,
        assume_unchanged: bool = False,
        remote_size: int | None = None,
    ) -> Path | None:
        """Fetch ``url`` as ``name`` under the work dir, reusing the previous copy when unchanged.

        - ``check_size``: compare a HEAD Content-Length with the previous manifest before downloading.
        - ``remote_size``: a size already known (e.g. from a release API) that replaces the HEAD.
        - ``assume_unchanged``: if the previous fetch had this URL, link it without asking the server
          (for frozen historical seasons).
        - ``optional``: swallow 403/404 for URLs that legitimately may not exist.
        """
        dest = self.work / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        old = self.prev.get(name)
        if old and old.url == url and not self.force and self.prev_dir is not None:
            size = None
            if assume_unchanged:
                size = old.bytes
            elif remote_size is not None:
                size = remote_size
            elif check_size:
                size = head_size(url, c)
            if size is not None and size == old.bytes and (self.prev_dir / old.name).exists():
                self._link(old.name, dest)
                self.manifest.files.append(old)
                return dest
        try:
            download(url, dest, c)
        except httpx.HTTPStatusError as e:
            if optional and is_missing(e.response.status_code):
                console.print(f"[dim]{self.source.name}: skip {name} ({e.response.status_code})[/dim]")
                return None
            raise
        rec = self.manifest.add(name, url, dest)
        if old and old.sha256 == rec.sha256:
            # same bytes as before, just a server without Content-Length
            dest.unlink()
            self._link(old.name, dest)
        else:
            self.changed += 1
        return dest

    def add_existing(self, path: Path, url: str) -> None:
        """Record a file produced by other means (e.g. a git clone) under the work dir."""
        name = str(path.relative_to(self.work))
        rec = self.manifest.add(name, url, path)
        old = self.prev.get(name)
        if not (old and old.sha256 == rec.sha256):
            self.changed += 1

    def _link(self, name: str, dest: Path) -> None:
        src = self.prev_dir / name  # type: ignore[operator]
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)


def write_table(table: Table, frame: pl.DataFrame | pl.LazyFrame, partition_by: str | None = None) -> int:
    """Replace ``table`` on disk with ``frame``. Returns row count."""
    df = frame.collect() if isinstance(frame, pl.LazyFrame) else frame
    out = table.path
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if partition_by:
        df.write_parquet(out, partition_by=partition_by, compression="zstd")
    else:
        df.write_parquet(out / "part-0.parquet", compression="zstd")
    return df.height


def concat_relaxed(frames: Iterable[pl.DataFrame]) -> pl.DataFrame:
    frames = [f for f in frames if f.height > 0]
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")
