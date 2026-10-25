"""Provenance for every raw download.

Each fetch of a source writes ``data/raw/<source>/<YYYY-MM-DD>/manifest.json`` next to the
files it downloaded. The manifest records where each file came from, its size and sha256,
and the license it was obtained under, so that any table in the archive can be traced
back to a byte-exact origin.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from sportslab.paths import raw_dir

MANIFEST_NAME = "manifest.json"


@dataclass
class FileRecord:
    name: str  # path relative to the dated raw dir
    url: str
    bytes: int
    sha256: str


@dataclass
class Manifest:
    source: str
    fetched_at: str  # ISO 8601, UTC
    license: str
    attribution: str
    files: list[FileRecord] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def new(cls, source: str, license: str, attribution: str, notes: str = "") -> Manifest:
        return cls(
            source=source,
            fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
            license=license,
            attribution=attribution,
            notes=notes,
        )

    def add(self, name: str, url: str, path: Path) -> FileRecord:
        rec = FileRecord(name=name, url=url, bytes=path.stat().st_size, sha256=sha256_of(path))
        self.files.append(rec)
        return rec

    def by_name(self) -> dict[str, FileRecord]:
        return {f.name: f for f in self.files}

    def write(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        out = directory / MANIFEST_NAME
        out.write_text(json.dumps(asdict(self), indent=2) + "\n")
        return out

    @classmethod
    def read(cls, directory: Path) -> Manifest:
        data = json.loads((directory / MANIFEST_NAME).read_text())
        files = [FileRecord(**f) for f in data.pop("files", [])]
        return cls(files=files, **data)


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def dated_dir(source: str, day: date | None = None) -> Path:
    day = day or date.today()
    return raw_dir(source) / day.isoformat()


def list_fetches(source: str) -> list[Path]:
    """All dated raw dirs for a source that have a manifest, oldest first."""
    base = raw_dir(source)
    if not base.exists():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and (p / MANIFEST_NAME).exists())


def latest_fetch(source: str) -> Path | None:
    fetches = list_fetches(source)
    return fetches[-1] if fetches else None
