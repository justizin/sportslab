# Roadmap

What exists: the archive layer with eight bulk sources, a DuckDB catalog, and stages 0 to 2
scaffolded. What follows is not built yet, roughly in the order it will be needed.

## Archive

- **Retrosheet event files** (stage 2). `alldata.zip` is fetched but only the game logs are
  normalized. Build Chadwick from source (https://github.com/chadwickbureau/chadwick; not in
  Debian stable) and add a `cwevent`-based normalizer producing `mlb.events` with the standard
  97 fields, partitioned by season.
- **Statcast** (stage 7+). Day-chunked backfill from Baseball Savant via `pybaseball.statcast`
  (the 25,000-row cap means one request per day of games), 2015 to present, into
  `mlb.statcast` partitioned by season. Values for prior seasons are revised retroactively, so
  consider DuckLake (https://ducklake.select) snapshots instead of overwriting parquet.
- **nba_api incremental collector** for the current NBA and WNBA seasons (`league_id='10'`),
  with one-second sleeps and run from this host only, since stats.nba.com blocks cloud IP ranges.
- **Understat and FBref** through `soccerdata`, with its cache enabled. Shot-level xG for the top
  five leagues 2014/15 onward to extend stage 3 beyond StatsBomb's competitions.
- **Rate-limit awareness**: the GitHub API calls in the sportsdataverse sources are unauthenticated
  (60 per hour). Set `GITHUB_TOKEN` if you fetch often.
- **Lahman license**: SABR's page states no formal license for the current edition. Confirm with
  lahmandb@sabr.org before publishing anything derived from it.

## Stages

- Stages 3 to 8 need their exercise notebooks written; the curriculum describes each.
- Stage 2 needs Chadwick (above) before run expectancy can be computed.
- Stage 4 RAPM needs a stint builder over `nba.pbp` and `wnba.pbp`; the ESPN play-by-play has
  substitution events but no explicit on-court lineup, so lineups must be reconstructed from
  starters plus substitutions. That reconstruction is its own small exercise.

## Repo

- `docs/sources.md` row counts are filled in by hand after a build; a `sportslab docs sources`
  command that regenerates the table from `archive status` would remove that step.
- Static site for `docs/notes/` (stage 8).
- CI: run `pytest` and `ruff` on push; no data access needed.
