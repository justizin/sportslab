"""Name -> Source lookup. Import a source module here to register it."""

from __future__ import annotations

from sportslab.archive.base import Source
from sportslab.archive.sources import (
    cricsheet,
    football_data,
    hoopr,
    lahman,
    nflverse,
    retrosheet,
    statsbomb,
    wehoop,
)

SOURCES: dict[str, type[Source]] = {
    cls.name: cls
    for cls in (
        lahman.Lahman,
        retrosheet.Retrosheet,
        nflverse.NFLverse,
        cricsheet.Cricsheet,
        statsbomb.StatsBombOpen,
        football_data.FootballData,
        wehoop.WehoopWNBA,
        hoopr.HoopRNBA,
    )
}


def get(name: str) -> Source:
    try:
        return SOURCES[name]()
    except KeyError:
        raise SystemExit(f"unknown source {name!r}; known: {', '.join(SOURCES)}") from None


def all_sources(include_opt_in: bool = False) -> list[Source]:
    return [cls() for cls in SOURCES.values() if include_opt_in or not cls.opt_in]
