"""Cricsheet: ball-by-ball JSON for 23k+ matches, 2001-. ODC-By license.

Download is a single ``all_json.zip``; normalization flattens each match into
``cricket.matches``, ``cricket.match_players`` and ``cricket.deliveries``.
"""

from __future__ import annotations

import json
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, Table, concat_relaxed, write_table

ALL_JSON = "https://cricsheet.org/downloads/all_json.zip"
PEOPLE = "https://cricsheet.org/register/people.csv"


class Cricsheet(Source):
    name = "cricsheet"
    sport = "cricket"
    description = "Cricsheet ball-by-ball data for international and franchise cricket"
    homepage = "https://cricsheet.org/"
    license = "ODC-By (Open Data Commons Attribution License)"
    attribution = "Ball-by-ball data from Cricsheet (https://cricsheet.org), ODC-By."
    tables = (
        Table("cricket", "matches", "one row per match: teams, venue, toss, outcome, event"),
        Table("cricket", "match_players", "players named in each match with Cricsheet person ids"),
        Table("cricket", "deliveries", "one row per ball; partitioned by match_type"),
        Table("cricket", "people", "Cricsheet people register with external identifiers"),
    )

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        ctx.get(ALL_JSON, "all_json.zip", c)
        ctx.get(PEOPLE, "people.csv", c)

    def build_tables(self, raw: Path) -> dict[str, int]:
        matches_t, players_t, deliveries_t, people_t = self.tables
        zpath = raw / "all_json.zip"
        with zipfile.ZipFile(zpath) as z:
            names = sorted(n for n in z.namelist() if n.endswith(".json"))
        chunks = [names[i::16] for i in range(16)]
        matches, players, deliveries = [], [], []
        with ProcessPoolExecutor(max_workers=8) as ex:
            for m, p, d in ex.map(_parse_chunk, [(str(zpath), ch) for ch in chunks]):
                matches.append(m)
                players.append(p)
                deliveries.append(d)
        rows = {}
        rows[matches_t.qualified] = write_table(matches_t, concat_relaxed(matches))
        rows[players_t.qualified] = write_table(players_t, concat_relaxed(players))
        rows[deliveries_t.qualified] = write_table(deliveries_t, concat_relaxed(deliveries), partition_by="match_type")
        people = pl.read_csv(raw / "people.csv", infer_schema_length=None, encoding="utf8-lossy")
        rows[people_t.qualified] = write_table(people_t, people)
        return rows


def _parse_chunk(args: tuple[str, list[str]]) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    zpath, names = args
    m_rows, p_rows, d_rows = [], [], []
    with zipfile.ZipFile(zpath) as z:
        for n in names:
            with z.open(n) as fh:
                doc = json.load(fh)
            match_id = n.rsplit("/", 1)[-1][:-5]
            m, p, d = flatten_match(match_id, doc)
            m_rows.append(m)
            p_rows.extend(p)
            d_rows.extend(d)
    return (
        pl.DataFrame(m_rows, infer_schema_length=None),
        pl.DataFrame(p_rows, infer_schema_length=None),
        pl.DataFrame(d_rows, infer_schema_length=None, schema_overrides=_DELIVERY_TYPES),
    )


_DELIVERY_TYPES = {
    "match_id": pl.Utf8, "match_type": pl.Utf8, "innings": pl.Int8, "batting_team": pl.Utf8,
    "bowling_team": pl.Utf8, "over": pl.Int16, "ball": pl.Int8, "batter": pl.Utf8, "bowler": pl.Utf8,
    "non_striker": pl.Utf8, "runs_batter": pl.Int8, "runs_extras": pl.Int8, "runs_total": pl.Int8,
    "wides": pl.Int8, "noballs": pl.Int8, "byes": pl.Int8, "legbyes": pl.Int8, "penalty": pl.Int8,
    "is_wicket": pl.Boolean, "wickets": pl.Int8, "wicket_kind": pl.Utf8, "player_out": pl.Utf8,
    "is_super_over": pl.Boolean, "target_runs": pl.Int16, "target_overs": pl.Float32,
}


def flatten_match(match_id: str, doc: dict) -> tuple[dict, list[dict], list[dict]]:
    info = doc.get("info", {})
    teams = info.get("teams", [None, None]) + [None]
    outcome = info.get("outcome", {})
    by = outcome.get("by", {})
    toss = info.get("toss", {})
    event = info.get("event", {})
    dates = info.get("dates", [])
    season = str(info.get("season", ""))
    match = {
        "match_id": match_id,
        "match_type": info.get("match_type"),
        "team_type": info.get("team_type"),
        "gender": info.get("gender"),
        "season": season,
        "season_start_year": int(season[:4]) if season[:4].isdigit() else None,
        "start_date": dates[0] if dates else None,
        "n_days": len(dates),
        "venue": info.get("venue"),
        "city": info.get("city"),
        "team1": teams[0],
        "team2": teams[1],
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "winner": outcome.get("winner"),
        "result": outcome.get("result"),  # tie / no result / draw when there is no winner
        "won_by_runs": by.get("runs"),
        "won_by_wickets": by.get("wickets"),
        "won_by_innings": by.get("innings"),
        "method": outcome.get("method"),  # D/L, DLS, VJD, Awarded
        "event_name": event.get("name"),
        "event_match_number": event.get("match_number"),
        "event_stage": event.get("stage"),
        "overs": info.get("overs"),
        "balls_per_over": info.get("balls_per_over", 6),
        "player_of_match": (info.get("player_of_match") or [None])[0],
        "umpires": ", ".join(info.get("officials", {}).get("umpires", [])) or None,
        "data_version": doc.get("meta", {}).get("data_version"),
    }
    registry = info.get("registry", {}).get("people", {})
    players = [
        {"match_id": match_id, "team": team, "player": name, "player_id": registry.get(name)}
        for team, names in info.get("players", {}).items()
        for name in names
    ]
    deliveries = []
    for i, inn in enumerate(doc.get("innings", []), start=1):
        batting = inn.get("team")
        bowling = teams[1] if batting == teams[0] else teams[0]
        target = inn.get("target", {})
        super_over = bool(inn.get("super_over", False))
        for over in inn.get("overs", []):
            onum = over.get("over")
            for b, d in enumerate(over.get("deliveries", []), start=1):
                runs = d.get("runs", {})
                extras = d.get("extras", {})
                wickets = d.get("wickets", [])
                first = wickets[0] if wickets else {}
                deliveries.append({
                    "match_id": match_id,
                    "match_type": match["match_type"],
                    "innings": i,
                    "batting_team": batting,
                    "bowling_team": bowling,
                    "over": onum,
                    "ball": b,
                    "batter": d.get("batter"),
                    "bowler": d.get("bowler"),
                    "non_striker": d.get("non_striker"),
                    "runs_batter": runs.get("batter", 0),
                    "runs_extras": runs.get("extras", 0),
                    "runs_total": runs.get("total", 0),
                    "wides": extras.get("wides", 0),
                    "noballs": extras.get("noballs", 0),
                    "byes": extras.get("byes", 0),
                    "legbyes": extras.get("legbyes", 0),
                    "penalty": extras.get("penalty", 0),
                    "is_wicket": bool(wickets),
                    "wickets": len(wickets),
                    "wicket_kind": first.get("kind"),
                    "player_out": first.get("player_out"),
                    "is_super_over": super_over,
                    "target_runs": target.get("runs"),
                    "target_overs": target.get("overs"),
                })
    return match, players, deliveries
