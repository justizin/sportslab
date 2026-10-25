# sportslab

Learning machine learning and statistics through sports data, on top of a local historical
archive that does not depend on anyone's API staying up.

Six sports (MLB, NBA, WNBA, NFL, soccer, cricket), one archive layout, one curriculum.
The curriculum is in `docs/curriculum.md`; the stages under `stages/` are exercises, not lectures.

## Layout

| Path | What |
|---|---|
| `sportslab/archive/sources/` | one module per data source: `fetch` raw files with a provenance manifest, `normalize` to parquet |
| `sportslab/catalog.py` | DuckDB views over the parquet tree (`data/sportslab.duckdb`) |
| `sportslab/cli.py` | `sportslab archive fetch|normalize|status`, `sportslab catalog build`, `sportslab sql` |
| `data/raw/<source>/<date>/` | immutable downloads + `manifest.json` (gitignored) |
| `data/parquet/<schema>/<table>/` | normalized tables, Hive-partitioned where it helps (gitignored) |
| `stages/NN_<topic>/` | one learning stage: README (concept, reading, task, check) + marimo exercise; solutions alongside |
| `docs/curriculum.md` | the learning path, stage by stage, with the free resources behind each |
| `docs/sources.md` | every dataset: URL, coverage, license, attribution text, row counts |
| `docs/roadmap.md` | what is not built yet |
| `docs/notes/` | one-page writeups per stage |

## Setup

```sh
uv sync                                  # creates .venv with everything in pyproject.toml
uv run sportslab archive fetch --all     # ~1.5 GB without the opt-in sources
uv run sportslab archive normalize --all
uv run sportslab catalog build
uv run sportslab sql "select yearID, count(*) from mlb.teams group by 1 order by 1 desc limit 5"
uv run marimo edit stages/00_data_stack/exercise.py
```

Large sources are opt-in by name: `uv run sportslab archive fetch hoopr statsbomb`.
Put the archive on another volume with `SPORTSLAB_DATA=/path uv run sportslab ...`.

Host notes: the dev box is a pre-AVX2 Xeon, so `pyproject.toml` uses `polars[rtcompat]` and pins
`duckdb<2` (both default wheels crash with SIGILL there); on an AVX2 machine either can be relaxed.
The HTTP client forces IPv4 because the box has AAAA resolution without an IPv6 route, which
otherwise costs a connect timeout per dual-stack host.

## Data attribution

The data is not in this repository and is not redistributed by it. If you publish anything
built on the archive, carry the notices in `docs/sources.md`. In particular:

- Retrosheet: "The information used here was obtained free of charge from and is copyrighted by
  Retrosheet. Interested parties may contact Retrosheet at www.retrosheet.org."
- StatsBomb open data: credit StatsBomb and use their logo per the repository terms.
- Cricsheet: Open Data Commons Attribution License (ODC-By).
- nflverse: CC-BY-4.0.
- Lahman Baseball Database (SABR), sportsdataverse (ESPN-derived), football-data.co.uk: see `docs/sources.md`.
