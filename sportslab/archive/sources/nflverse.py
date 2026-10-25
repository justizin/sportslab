"""nflverse-data GitHub releases: play-by-play 1999-, players, rosters, schedules. CC-BY-4.0."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, Table, console, write_table

RELEASES = "https://github.com/nflverse/nflverse-data/releases/download"
FIRST_PBP_SEASON = 1999


def current_season(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= 9 else today.year - 1


class NFLverse(Source):
    name = "nflverse"
    sport = "nfl"
    description = "nflverse play-by-play (nflfastR schema), players, rosters and schedules"
    homepage = "https://github.com/nflverse/nflverse-data"
    license = "CC-BY-4.0"
    attribution = "Data from nflverse (https://nflverse.nflverse.com), CC-BY-4.0."
    tables = (
        Table("nfl", "pbp", "play-by-play, one row per play, 1999-; ~370 columns incl. EPA/WP"),
        Table("nfl", "players", "player master table"),
        Table("nfl", "rosters", "season rosters"),
        Table("nfl", "schedules", "games with scores, lines and rest days, 1999-"),
    )

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        last = current_season()
        for season in range(FIRST_PBP_SEASON, last + 1):
            # seasons more than one year old are frozen on the release; skip the HEAD check
            frozen = season < last - 1
            ctx.get(f"{RELEASES}/pbp/play_by_play_{season}.parquet", f"pbp/play_by_play_{season}.parquet", c,
                    check_size=not frozen, assume_unchanged=frozen, optional=season == last)
            ctx.get(f"{RELEASES}/rosters/roster_{season}.parquet", f"rosters/roster_{season}.parquet", c,
                    check_size=not frozen, assume_unchanged=frozen, optional=True)
        ctx.get(f"{RELEASES}/players/players.parquet", "players/players.parquet", c)
        ctx.get(f"{RELEASES}/schedules/games.csv", "schedules/games.csv", c)

    def build_tables(self, raw: Path) -> dict[str, int]:
        rows = {}
        pbp, players, rosters, schedules = self.tables
        rows[pbp.qualified] = _copy_by_season(pbp, raw / "pbp")
        rows[rosters.qualified] = _copy_by_season(rosters, raw / "rosters")
        rows[players.qualified] = write_table(players, pl.read_parquet(raw / "players/players.parquet"))
        games = pl.read_csv(raw / "schedules/games.csv", infer_schema_length=None, try_parse_dates=True)
        rows[schedules.qualified] = write_table(schedules, games)
        return rows


def _copy_by_season(table: Table, src_dir: Path) -> int:
    """Re-encode per-season parquet files into ``table/season=YYYY/part-0.parquet``."""
    import shutil

    if table.path.exists():
        shutil.rmtree(table.path)
    total = 0
    for f in sorted(src_dir.glob("*.parquet")):
        m = re.search(r"(\d{4})\.parquet$", f.name)
        if not m:
            console.print(f"[yellow]skip {f}: no season in name[/yellow]")
            continue
        df = pl.read_parquet(f)
        if "season" in df.columns:
            df = df.drop("season")  # hive partition supplies it
        out = table.path / f"season={m.group(1)}"
        out.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out / "part-0.parquet", compression="zstd")
        total += df.height
    return total
