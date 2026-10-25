"""Retrosheet: game logs 1871- (normalized now) and event files (kept raw for stage 2).

Retrosheet's notice must accompany any use:
"The information used here was obtained free of charge from and is copyrighted by Retrosheet.
Interested parties may contact Retrosheet at www.retrosheet.org."
"""

from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, Table, concat_relaxed, console, write_table

GAMELOGS = "https://www.retrosheet.org/gamelogs"
ALLDATA = "https://www.retrosheet.org/downloads/alldata.zip"
FIELDS = "https://www.retrosheet.org/gamelogs/glfields.txt"

NOTICE = (
    "The information used here was obtained free of charge from and is copyrighted by Retrosheet. "
    "Interested parties may contact Retrosheet at www.retrosheet.org."
)


def _side(prefix: str) -> list[str]:
    offense = ["at_bats", "hits", "doubles", "triples", "homeruns", "rbi", "sacrifice_hits", "sacrifice_flies",
               "hit_by_pitch", "walks", "intentional_walks", "strikeouts", "stolen_bases", "caught_stealing",
               "grounded_into_double", "first_catcher_interference", "left_on_base"]
    pitching = ["pitchers_used", "individual_earned_runs", "team_earned_runs", "wild_pitches", "balks"]
    defense = ["putouts", "assists", "errors", "passed_balls", "double_plays", "triple_plays"]
    return [f"{prefix}_{c}" for c in offense + pitching + defense]


def _lineup(prefix: str) -> list[str]:
    cols = []
    for i in range(1, 10):
        cols += [f"{prefix}_player_{i}_id", f"{prefix}_player_{i}_name", f"{prefix}_player_{i}_def_pos"]
    return cols


# The 161 fields documented at https://www.retrosheet.org/gamelogs/glfields.txt, in order.
GAMELOG_COLUMNS: list[str] = (
    ["date", "number_of_game", "day_of_week", "v_name", "v_league", "v_game_number", "h_name", "h_league",
     "h_game_number", "v_score", "h_score", "length_outs", "day_night", "completion", "forfeit", "protest",
     "park_id", "attendance", "length_minutes", "v_line_score", "h_line_score"]
    + _side("v") + _side("h")
    + ["hp_umpire_id", "hp_umpire_name", "1b_umpire_id", "1b_umpire_name", "2b_umpire_id", "2b_umpire_name",
       "3b_umpire_id", "3b_umpire_name", "lf_umpire_id", "lf_umpire_name", "rf_umpire_id", "rf_umpire_name",
       "v_manager_id", "v_manager_name", "h_manager_id", "h_manager_name",
       "winning_pitcher_id", "winning_pitcher_name", "losing_pitcher_id", "losing_pitcher_name",
       "saving_pitcher_id", "saving_pitcher_name", "winning_rbi_batter_id", "winning_rbi_batter_name",
       "v_starting_pitcher_id", "v_starting_pitcher_name", "h_starting_pitcher_id", "h_starting_pitcher_name"]
    + _lineup("v") + _lineup("h")
    + ["additional_info", "acquisition_info"]
)
assert len(GAMELOG_COLUMNS) == 161, len(GAMELOG_COLUMNS)

INT_COLS = {"v_game_number", "h_game_number", "v_score", "h_score", "length_outs", "attendance", "length_minutes"} | {
    c for c in GAMELOG_COLUMNS if c.startswith(("v_", "h_")) and c.split("_", 1)[1] in {
        s.split("_", 1)[1] for s in _side("v")}
} | {c for c in GAMELOG_COLUMNS if c.endswith("_def_pos")}


GAME_TYPES = {"WS": "world_series", "LC": "lcs", "DV": "division_series", "WC": "wild_card", "AS": "all_star"}


class Retrosheet(Source):
    name = "retrosheet"
    sport = "mlb"
    description = "Retrosheet game logs (1871-) and play-by-play event files (1908-)"
    homepage = "https://www.retrosheet.org/"
    license = "Copyright Retrosheet; free for any use provided the Retrosheet notice is displayed."
    attribution = NOTICE
    tables = (
        Table("mlb", "gamelog", "one row per game, 1871-: teams, score, line scores, box totals, umpires, lineups; "
                                "game_type = regular | world_series | lcs | division_series | wild_card | all_star"),
    )

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        year = date.today().year
        got = None
        for y in (year, year - 1):
            got = ctx.get(f"{GAMELOGS}/gl1871_{y}.zip", f"gl1871_{y}.zip", c, optional=True)
            if got:
                break
        if got is None:
            raise FileNotFoundError("could not find the Retrosheet all-years game log zip")
        ctx.get(FIELDS, "glfields.txt", c)
        ctx.get(ALLDATA, "alldata.zip", c)  # event files, rosters, team files; parsed with Chadwick in stage 2

    def build_tables(self, raw: Path) -> dict[str, int]:
        (gamelog,) = self.tables
        zpath = next(raw.glob("gl1871_*.zip"))
        frames = []
        with zipfile.ZipFile(zpath) as z:
            for n in sorted(z.namelist()):
                if not n.upper().endswith(".TXT") or not n.upper().startswith("GL"):
                    continue
                df = pl.read_csv(z.read(n), has_header=False, new_columns=GAMELOG_COLUMNS, infer_schema=False,
                                 quote_char='"', encoding="utf8-lossy", truncate_ragged_lines=True)
                if df.width != 161:
                    console.print(f"[yellow]{n}: {df.width} columns, expected 161[/yellow]")
                # GL2025.TXT is the regular season; GLWS/GLLC/GLDV/GLWC/GLAS hold postseason and All-Star games
                stem = n.rsplit("/", 1)[-1].split(".")[0].upper()
                game_type = "regular" if stem[2:].isdigit() else GAME_TYPES.get(stem[2:], stem[2:].lower())
                frames.append(df.with_columns(pl.lit(game_type).alias("game_type")))
        df = concat_relaxed(frames)
        df = df.with_columns(
            [pl.col(c).cast(pl.Int32, strict=False) for c in INT_COLS if c in df.columns]
            + [pl.col("date").str.strptime(pl.Date, "%Y%m%d", strict=False).alias("game_date")]
        ).with_columns(pl.col("game_date").dt.year().alias("season"))
        return {gamelog.qualified: write_table(gamelog, df)}
