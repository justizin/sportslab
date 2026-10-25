"""StatsBomb open data: event-level soccer data for 100+ competition-seasons.

The data lives in a git repository (several GB). We keep a persistent sparse mirror under
``data/raw/statsbomb/repo`` and hard-link its data files into each dated fetch dir, so a
re-fetch is a ``git pull`` rather than a fresh multi-gigabyte download. 360 freeze-frame
files are excluded unless ``SPORTSLAB_STATSBOMB_360=1``.

Terms: https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf - credit StatsBomb and
use their logo when publishing anything derived from the data.
"""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, Table, concat_relaxed, console, write_table
from sportslab.paths import raw_dir

REPO = "https://github.com/statsbomb/open-data.git"
SPARSE = ["data/competitions.json", "data/matches", "data/lineups", "data/events"]


class StatsBombOpen(Source):
    name = "statsbomb"
    sport = "soccer"
    opt_in = True  # multi-GB git mirror
    description = "StatsBomb open event data: World Cups, Euros, Messi-era La Liga, women's leagues, more"
    homepage = "https://github.com/statsbomb/open-data"
    license = "StatsBomb Public Data User Agreement (non-commercial research; credit StatsBomb, display logo)."
    attribution = "Event data from StatsBomb open data (https://github.com/statsbomb/open-data), used under its public data agreement."
    tables = (
        Table("soccer", "sb_competitions", "competition-seasons available in the open data"),
        Table("soccer", "sb_matches", "one row per match with teams, score, stage, stadium, referee"),
        Table("soccer", "sb_lineups", "players per team per match"),
        Table("soccer", "sb_events", "curated flat view of every event; partitioned by competition_id"),
        Table("soccer", "sb_shot_freeze_frames", "player positions at the moment of each shot"),
    )

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        repo = raw_dir(self.name) / "repo"
        if not (repo / ".git").exists():
            repo.parent.mkdir(parents=True, exist_ok=True)
            console.print("statsbomb: sparse-cloning open-data (this is several GB)")
            subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(repo)], check=True)
        sparse = SPARSE + (["data/three-sixty"] if os.environ.get("SPORTSLAB_STATSBOMB_360") == "1" else [])
        subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "--no-cone", *sparse], check=True)
        subprocess.run(["git", "-C", str(repo), "pull", "--ff-only", "--depth", "1"], check=True)
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        ctx.manifest.notes = f"open-data commit {sha}"
        data = repo / "data"
        for f in sorted(data.rglob("*.json")):
            rel = f.relative_to(data)
            dest = ctx.work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(f, dest)
            except OSError:
                import shutil

                shutil.copy2(f, dest)
            ctx.add_existing(dest, f"{REPO}#{sha}:data/{rel}")

    def build_tables(self, raw: Path) -> dict[str, int]:
        comps_t, matches_t, lineups_t, events_t, ff_t = self.tables
        rows = {}
        comps = pl.DataFrame(json.loads((raw / "competitions.json").read_text()), infer_schema_length=None)
        rows[comps_t.qualified] = write_table(comps_t, comps)

        match_rows = []
        for f in sorted((raw / "matches").rglob("*.json")):
            for m in json.loads(f.read_text()):
                match_rows.append(flatten_match(m))
        matches = pl.DataFrame(match_rows, infer_schema_length=None)
        rows[matches_t.qualified] = write_table(matches_t, matches)
        comp_of = dict(zip(matches["match_id"].to_list(), matches["competition_id"].to_list()))

        lineup_files = sorted((raw / "lineups").glob("*.json"))
        event_files = sorted((raw / "events").glob("*.json"))
        with ProcessPoolExecutor(max_workers=8) as ex:
            lineups = concat_relaxed(ex.map(_lineups_of, lineup_files, chunksize=50))
            rows[lineups_t.qualified] = write_table(lineups_t, lineups)
            ev_frames, ff_frames = [], []
            for ev, ff in ex.map(_events_of, event_files, chunksize=20):
                ev_frames.append(ev)
                ff_frames.append(ff)
        events = concat_relaxed(ev_frames).with_columns(
            pl.col("match_id").replace_strict(comp_of, default=None).alias("competition_id")
        )
        rows[events_t.qualified] = write_table(events_t, events, partition_by="competition_id")
        rows[ff_t.qualified] = write_table(ff_t, concat_relaxed(ff_frames))
        return rows


def _name(d: dict | None) -> str | None:
    return d.get("name") if isinstance(d, dict) else None


def _id(d: dict | None) -> int | None:
    return d.get("id") if isinstance(d, dict) else None


def flatten_match(m: dict) -> dict:
    return {
        "match_id": m["match_id"],
        "match_date": m.get("match_date"),
        "kick_off": m.get("kick_off"),
        "competition_id": _id(m.get("competition")) or m.get("competition", {}).get("competition_id"),
        "competition_name": m.get("competition", {}).get("competition_name"),
        "country_name": m.get("competition", {}).get("country_name"),
        "season_id": m.get("season", {}).get("season_id"),
        "season_name": m.get("season", {}).get("season_name"),
        "home_team_id": m.get("home_team", {}).get("home_team_id"),
        "home_team": m.get("home_team", {}).get("home_team_name"),
        "home_team_gender": m.get("home_team", {}).get("home_team_gender"),
        "away_team_id": m.get("away_team", {}).get("away_team_id"),
        "away_team": m.get("away_team", {}).get("away_team_name"),
        "away_team_gender": m.get("away_team", {}).get("away_team_gender"),
        "home_score": m.get("home_score"),
        "away_score": m.get("away_score"),
        "match_week": m.get("match_week"),
        "competition_stage": _name(m.get("competition_stage")),
        "stadium": _name(m.get("stadium")),
        "referee": _name(m.get("referee")),
        "match_status": m.get("match_status"),
        "last_updated": m.get("last_updated"),
    }


def _lineups_of(path: Path) -> pl.DataFrame:
    match_id = int(path.stem)
    rows = []
    for team in json.loads(path.read_text()):
        for p in team.get("lineup", []):
            positions = p.get("positions") or [{}]
            rows.append({
                "match_id": match_id,
                "team_id": team.get("team_id"),
                "team": team.get("team_name"),
                "player_id": p.get("player_id"),
                "player": p.get("player_name"),
                "player_nickname": p.get("player_nickname"),
                "jersey_number": p.get("jersey_number"),
                "country": _name(p.get("country")),
                "first_position": positions[0].get("position"),
                "started": positions[0].get("start_reason") == "Starting XI" if positions[0] else False,
                "n_positions": len(p.get("positions") or []),
                "n_cards": len(p.get("cards") or []),
            })
    return pl.DataFrame(rows, infer_schema_length=None)


def _xy(loc) -> tuple:
    if isinstance(loc, list) and len(loc) >= 2:
        return (loc[0], loc[1], loc[2] if len(loc) > 2 else None)
    return (None, None, None)


def _events_of(path: Path) -> tuple[pl.DataFrame, pl.DataFrame]:
    match_id = int(path.stem)
    rows, ff_rows = [], []
    for e in json.loads(path.read_text()):
        x, y, _ = _xy(e.get("location"))
        p = e.get("pass") or {}
        s = e.get("shot") or {}
        carry = e.get("carry") or {}
        px, py, _ = _xy(p.get("end_location"))
        sx, sy, sz = _xy(s.get("end_location"))
        cx, cy, _ = _xy(carry.get("end_location"))
        rows.append({
            "match_id": match_id,
            "id": e.get("id"),
            "index": e.get("index"),
            "period": e.get("period"),
            "timestamp": e.get("timestamp"),
            "minute": e.get("minute"),
            "second": e.get("second"),
            "type": _name(e.get("type")),
            "possession": e.get("possession"),
            "possession_team": _name(e.get("possession_team")),
            "play_pattern": _name(e.get("play_pattern")),
            "team": _name(e.get("team")),
            "team_id": _id(e.get("team")),
            "player": _name(e.get("player")),
            "player_id": _id(e.get("player")),
            "position": _name(e.get("position")),
            "x": x, "y": y,
            "duration": e.get("duration"),
            "under_pressure": bool(e.get("under_pressure", False)),
            "counterpress": bool(e.get("counterpress", False)),
            "out": bool(e.get("out", False)),
            "pass_end_x": px, "pass_end_y": py,
            "pass_length": p.get("length"), "pass_angle": p.get("angle"),
            "pass_height": _name(p.get("height")), "pass_recipient": _name(p.get("recipient")),
            "pass_outcome": _name(p.get("outcome")), "pass_type": _name(p.get("type")),
            "pass_body_part": _name(p.get("body_part")),
            "pass_cross": bool(p.get("cross", False)), "pass_shot_assist": bool(p.get("shot_assist", False)),
            "pass_goal_assist": bool(p.get("goal_assist", False)),
            "shot_statsbomb_xg": s.get("statsbomb_xg"), "shot_outcome": _name(s.get("outcome")),
            "shot_type": _name(s.get("type")), "shot_body_part": _name(s.get("body_part")),
            "shot_technique": _name(s.get("technique")), "shot_first_time": bool(s.get("first_time", False)),
            "shot_one_on_one": bool(s.get("one_on_one", False)), "shot_open_goal": bool(s.get("open_goal", False)),
            "shot_aerial_won": bool(s.get("aerial_won", False)),
            "shot_end_x": sx, "shot_end_y": sy, "shot_end_z": sz,
            "shot_key_pass_id": s.get("key_pass_id"),
            "shot_freeze_frame_n": len(s.get("freeze_frame") or []) if s else None,
            "carry_end_x": cx, "carry_end_y": cy,
            "dribble_outcome": _name((e.get("dribble") or {}).get("outcome")),
            "duel_type": _name((e.get("duel") or {}).get("type")),
            "duel_outcome": _name((e.get("duel") or {}).get("outcome")),
            "goalkeeper_type": _name((e.get("goalkeeper") or {}).get("type")),
            "goalkeeper_outcome": _name((e.get("goalkeeper") or {}).get("outcome")),
            "foul_committed_card": _name((e.get("foul_committed") or {}).get("card")),
            "bad_behaviour_card": _name((e.get("bad_behaviour") or {}).get("card")),
            "substitution_replacement": _name((e.get("substitution") or {}).get("replacement")),
        })
        for f in s.get("freeze_frame") or []:
            fx, fy, _ = _xy(f.get("location"))
            ff_rows.append({
                "match_id": match_id, "shot_id": e.get("id"),
                "player": _name(f.get("player")), "player_id": _id(f.get("player")),
                "position": _name(f.get("position")), "teammate": bool(f.get("teammate", False)),
                "x": fx, "y": fy,
            })
    return (pl.DataFrame(rows, infer_schema_length=None), pl.DataFrame(ff_rows, infer_schema_length=None))
