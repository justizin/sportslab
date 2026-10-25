"""Smoke tests for the archive core, with no network access: manifests, normalizers, catalog."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import duckdb
import polars as pl
import pytest

from sportslab import catalog
from sportslab.archive import manifest as mf
from sportslab.archive.base import Table, write_table
from sportslab.archive.sources import cricsheet, football_data, retrosheet


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    """Point every path constant at a temp dir for the duration of a test."""
    from sportslab import paths

    monkeypatch.setattr(paths, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(paths, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(paths, "PARQUET_ROOT", tmp_path / "parquet")
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "test.duckdb")
    monkeypatch.setattr(catalog, "PARQUET_ROOT", tmp_path / "parquet")
    monkeypatch.setattr(catalog, "DB_PATH", tmp_path / "test.duckdb")
    return tmp_path


def test_manifest_round_trip(tmp_path: Path):
    f = tmp_path / "a.csv"
    f.write_text("x,y\n1,2\n")
    m = mf.Manifest.new("demo", "CC0", "nobody")
    rec = m.add("a.csv", "https://example.org/a.csv", f)
    assert rec.bytes == 8 and len(rec.sha256) == 64
    m.write(tmp_path)
    back = mf.Manifest.read(tmp_path)
    assert back.source == "demo" and back.by_name()["a.csv"].sha256 == rec.sha256
    assert json.loads((tmp_path / "manifest.json").read_text())["license"] == "CC0"


def test_retrosheet_gamelog_columns_are_161():
    assert len(retrosheet.GAMELOG_COLUMNS) == 161
    assert len(set(retrosheet.GAMELOG_COLUMNS)) == 161
    assert retrosheet.GAMELOG_COLUMNS[0] == "date"
    assert retrosheet.GAMELOG_COLUMNS[160] == "acquisition_info"
    assert retrosheet.GAMELOG_COLUMNS[105] == "v_player_1_id"  # field 106, first visitor starter


def test_cricsheet_flatten_match():
    doc = {
        "meta": {"data_version": "1.1.0"},
        "info": {
            "match_type": "T20", "gender": "male", "season": "2023/24", "dates": ["2024-01-01"],
            "teams": ["A", "B"], "toss": {"winner": "A", "decision": "bat"},
            "outcome": {"winner": "B", "by": {"wickets": 4}},
            "players": {"A": ["p1"], "B": ["p2"]}, "registry": {"people": {"p1": "id1", "p2": "id2"}},
            "overs": 20,
        },
        "innings": [
            {"team": "A", "overs": [{"over": 0, "deliveries": [
                {"batter": "p1", "bowler": "p2", "non_striker": "p1", "runs": {"batter": 4, "extras": 0, "total": 4}},
                {"batter": "p1", "bowler": "p2", "non_striker": "p1", "runs": {"batter": 0, "extras": 1, "total": 1},
                 "extras": {"wides": 1}},
                {"batter": "p1", "bowler": "p2", "non_striker": "p1", "runs": {"batter": 0, "extras": 0, "total": 0},
                 "wickets": [{"player_out": "p1", "kind": "bowled"}]},
            ]}]},
            {"team": "B", "target": {"runs": 6, "overs": 20}, "overs": []},
        ],
    }
    m, players, deliveries = cricsheet.flatten_match("m1", doc)
    assert m["season_start_year"] == 2023 and m["winner"] == "B" and m["won_by_wickets"] == 4
    assert {p["player_id"] for p in players} == {"id1", "id2"}
    assert len(deliveries) == 3
    assert deliveries[1]["wides"] == 1 and deliveries[1]["bowling_team"] == "B"
    assert deliveries[2]["is_wicket"] and deliveries[2]["wicket_kind"] == "bowled"
    assert deliveries[0]["ball"] == 1 and deliveries[0]["innings"] == 1


def test_football_data_reader_handles_blank_headers_and_ragged_rows(tmp_path: Path):
    f = tmp_path / "E0.csv"
    f.write_text(
        "﻿Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,,,\n"
        "E0,14/08/93,Arsenal,Coventry,0,3,A,,,\n"
        "E0,14/08/93,Chelsea,Blackburn,1,2,A\n"
        ",,,,,,\n"
    )
    df = football_data.read_fd_csv(f)
    assert df.columns == ["Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
    assert df.height == 2
    assert df["FTHG"].dtype == pl.Float64 and df["FTHG"].to_list() == [0.0, 1.0]
    assert football_data.season_code(1993) == "9394" and football_data.season_code(2025) == "2526"


def test_write_table_and_catalog(data_root: Path):
    t = Table("demo", "things")
    df = pl.DataFrame({"season": [2001, 2001, 2002], "v": [1, 2, 3]})
    assert write_table(t, df, partition_by="season") == 3
    assert (t.path / "season=2001").exists()
    views = catalog.build()
    assert views == ["demo.things"]
    con = duckdb.connect(str(catalog.DB_PATH), read_only=True)
    assert con.sql("select count(*) from demo.things where season = 2001").fetchone()[0] == 2


def test_retrosheet_normalize_from_zip(data_root: Path, tmp_path: Path):
    raw = tmp_path / "raw" / "retrosheet" / "2026-01-01"
    raw.mkdir(parents=True)
    row = ["20250327", "0", "Thu", "NYA", "AL", "1", "BOS", "AL", "1", "5", "3", "54"] + [""] * (161 - 12)
    line = ",".join(f'"{v}"' for v in row)
    with zipfile.ZipFile(raw / "gl1871_2025.zip", "w") as z:
        z.writestr("GL2025.TXT", line + "\n")
    mf.Manifest.new("retrosheet", "x", "y").write(raw)
    rows = retrosheet.Retrosheet().normalize(raw)
    assert rows == {"mlb.gamelog": 1}
    df = pl.read_parquet(Table("mlb", "gamelog").path / "part-0.parquet")
    assert df["season"][0] == 2025 and df["v_score"][0] == 5 and df.width == 164
    assert df["game_type"][0] == "regular"
