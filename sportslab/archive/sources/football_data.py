"""football-data.co.uk: match results with bookmaker odds, 22 European divisions, 1993/94-.

Free to download; the site keeps all rights, so do not redistribute the files.
"""

from __future__ import annotations

import csv
import io
import time
from datetime import date
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, Table, concat_relaxed, write_table

BASE = "https://www.football-data.co.uk/mmz4281"
FIRST_SEASON = 1993

DIVISIONS = {
    "E0": ("England", "Premier League"), "E1": ("England", "Championship"), "E2": ("England", "League One"),
    "E3": ("England", "League Two"), "EC": ("England", "National League"),
    "SC0": ("Scotland", "Premiership"), "SC1": ("Scotland", "Championship"), "SC2": ("Scotland", "League One"),
    "SC3": ("Scotland", "League Two"),
    "D1": ("Germany", "Bundesliga"), "D2": ("Germany", "2. Bundesliga"),
    "I1": ("Italy", "Serie A"), "I2": ("Italy", "Serie B"),
    "SP1": ("Spain", "La Liga"), "SP2": ("Spain", "Segunda"),
    "F1": ("France", "Ligue 1"), "F2": ("France", "Ligue 2"),
    "N1": ("Netherlands", "Eredivisie"), "B1": ("Belgium", "Pro League"), "P1": ("Portugal", "Primeira Liga"),
    "T1": ("Turkey", "Super Lig"), "G1": ("Greece", "Super League"),
}

STRING_COLS = {"Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTR", "HTR", "Referee"}


def season_code(start_year: int) -> str:
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def current_season(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= 8 else today.year - 1


class FootballData(Source):
    name = "football-data"
    sport = "soccer"
    description = "football-data.co.uk results and bookmaker odds for European leagues"
    homepage = "https://www.football-data.co.uk/data.php"
    license = "Free to download for personal use; (c) Football-Data, all rights reserved. Not redistributable."
    attribution = "Match results and odds from football-data.co.uk."
    tables = (
        Table("soccer", "results", "one row per match: result, shots, cards, bookmaker odds; partitioned by season_start"),
    )

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        last = current_season()
        for start in range(FIRST_SEASON, last + 1):
            frozen = start < last - 1
            for div in DIVISIONS:
                ctx.get(f"{BASE}/{season_code(start)}/{div}.csv", f"{start}/{div}.csv", c,
                        check_size=not frozen, assume_unchanged=frozen, optional=True)
                if not frozen or ctx.changed:
                    time.sleep(0.2)

    def build_tables(self, raw: Path) -> dict[str, int]:
        frames = []
        for f in sorted(raw.glob("*/*.csv")):
            start = int(f.parent.name)
            df = read_fd_csv(f)
            if df.height == 0:
                continue
            country, league = DIVISIONS.get(f.stem, (None, None))
            df = df.with_columns(
                pl.lit(start).alias("season_start"),
                pl.lit(f"{start}/{(start + 1) % 100:02d}").alias("season"),
                pl.lit(country).alias("country"),
                pl.lit(league).alias("league"),
            )
            frames.append(df)
        (results,) = self.tables
        out = concat_relaxed(frames)
        if "Date" in out.columns:
            # dd/mm/yy before 2017/18, dd/mm/yyyy after; pick the format by length so "14/08/00" is 2000, not year 0
            out = out.with_columns(
                pl.when(pl.col("Date").str.len_chars() <= 8)
                .then(pl.col("Date").str.strptime(pl.Date, "%d/%m/%y", strict=False))
                .otherwise(pl.col("Date").str.strptime(pl.Date, "%d/%m/%Y", strict=False))
                .alias("match_date")
            )
        return {results.qualified: write_table(results, out, partition_by="season_start")}


def read_fd_csv(path: Path) -> pl.DataFrame:
    """Read one football-data CSV robustly: BOM, latin-1, blank trailing headers, ragged rows."""
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if len(rows) < 2:
        return pl.DataFrame()
    header = rows[0]
    keep = [i for i, h in enumerate(header) if h.strip()]
    names = [header[i].strip() for i in keep]
    # de-duplicate column names, which happens in a few early seasons
    seen: dict[str, int] = {}
    for j, n in enumerate(names):
        if n in seen:
            seen[n] += 1
            names[j] = f"{n}_{seen[n]}"
        else:
            seen[n] = 0
    data = {n: [] for n in names}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        for n, i in zip(names, keep):
            data[n].append(r[i].strip() if i < len(r) and r[i].strip() else None)
    df = pl.DataFrame(data, schema={n: pl.Utf8 for n in names})
    casts = [pl.col(n).cast(pl.Float64, strict=False) for n in names if n not in STRING_COLS]
    return df.with_columns(casts) if casts else df
