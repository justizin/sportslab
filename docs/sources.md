# Data sources

Every dataset the archive knows how to fetch, with the terms it was obtained under. Row counts
are from the build on 2026-10-25; rerun `uv run sportslab archive status` for current numbers.
None of this data is committed to the repository or redistributed by it.

| Source | Sport | Granularity | Coverage | Raw size | License / terms | Fetch |
|---|---|---|---|---|---|---|
| [Lahman Baseball Database](https://sabr.org/lahman-database/) (SABR edition) | MLB | player-season, team-season | 1871–2025 | 42 MB, 28 files | No formal license stated by SABR; Negro Leagues data licensed from Seamheads.com. Attribution required; confirm before publishing derivatives. | Box shared folder, per-file |
| [Retrosheet](https://www.retrosheet.org/) | MLB | game (logs), play (event files) | logs 1871–2025; events 1908–2025 | 380 MB | Copyright Retrosheet, free for any use with the notice below | direct zip |
| [nflverse-data](https://github.com/nflverse/nflverse-data) | NFL | play, game, player, roster | pbp 1999–2026 | 489 MB | CC-BY-4.0 | GitHub release assets |
| [Cricsheet](https://cricsheet.org/) | cricket | ball | 2001–2026, 23,132 matches | 148 MB | ODC-By | direct zip |
| [StatsBomb open data](https://github.com/statsbomb/open-data) | soccer | event | 116 competition-seasons | several GB | StatsBomb public data agreement: credit and logo required, non-commercial | sparse git mirror (opt-in) |
| [football-data.co.uk](https://www.football-data.co.uk/data.php) | soccer | match + odds | 22 divisions, 1993/94–2026/27 | 95 MB, 716 files | Free to download; all rights reserved; do not redistribute | per-division CSVs |
| [wehoop (sportsdataverse)](https://github.com/sportsdataverse/wehoop-wnba-data) | WNBA | play, game | 2002–2026 | 73 MB | Code MIT; data is ESPN's. Research use, do not redistribute | GitHub release assets |
| [hoopR (sportsdataverse)](https://github.com/sportsdataverse/hoopR-nba-data) | NBA | play, game | 2002–2026 | ~450 MB | Same as wehoop | GitHub release assets (opt-in) |

## Tables and row counts

| Table | Rows | Notes |
|---|---|---|
| `mlb.teams` | 3,614 | Lahman team-seasons; `teamIDretro` joins to Retrosheet |
| `mlb.batting` / `mlb.pitching` / `mlb.fielding` | 128,598 / 57,630 / 174,332 | player-season-stint |
| `mlb.people` | 24,270 | biographical master |
| `mlb.appearances`, `mlb.allstarfull`, `mlb.awards*`, `mlb.halloffame`, `mlb.*post`, `mlb.salaries`, `mlb.schools`, `mlb.collegeplaying`, `mlb.parks`, `mlb.homegames`, `mlb.managers*`, `mlb.teamsfranchises`, `mlb.teamshalf`, `mlb.fieldingof*` | see `archive status` | the rest of Lahman |
| `mlb.gamelog` | 235,607 | Retrosheet, 161 fields plus `game_date`, `season` |
| `nfl.pbp` | 1,296,179 | nflfastR schema, partitioned by season |
| `nfl.schedules` | 7,548 | games with scores and lines |
| `nfl.players` / `nfl.rosters` | 24,861 / 69,534 | |
| `cricket.deliveries` | 11,689,170 | partitioned by `match_type` (MDM, T20, Test, ODI, ODM, IT20) |
| `cricket.matches` / `cricket.match_players` / `cricket.people` | 23,132 / 510,300 / 18,651 | |
| `soccer.results` | 244,929 | partitioned by `season_start`; `match_date` parsed; odds columns are Float64 |
| `wnba.pbp` | 2,297,117 | partitioned by season |
| `wnba.team_box` / `wnba.player_box` / `wnba.schedules` | 11,298 / 129,865 / 6,620 | `season_type` 2 = regular season |
| `soccer.sb_*`, `nba.*` | not fetched | opt-in: `uv run sportslab archive fetch statsbomb hoopr` |

## Required notices

**Retrosheet.** "The information used here was obtained free of charge from and is copyrighted by
Retrosheet. Interested parties may contact Retrosheet at www.retrosheet.org."

**StatsBomb.** Credit StatsBomb as the source and display the StatsBomb logo on any published
visualization or analysis, per https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf.

**Cricsheet.** Data from Cricsheet (https://cricsheet.org), licensed under the Open Data Commons
Attribution License (ODC-By).

**nflverse.** Data from nflverse (https://nflverse.nflverse.com), CC-BY-4.0.

**Lahman.** Lahman Baseball Database, Sean Lahman / SABR. Negro Leagues statistics from Seamheads.com.

**sportsdataverse.** ESPN-derived data via hoopR / wehoop. Keep local.

**football-data.co.uk.** Keep local; link to the site rather than sharing files.

## Provenance

Each fetch writes `data/raw/<source>/<YYYY-MM-DD>/manifest.json` recording, per file, the URL,
byte count and sha256, plus the license text at the time of download. Re-fetching links unchanged
files from the previous dated directory instead of downloading them again, so the history of what
changed upstream is kept at no storage cost.

## Known gaps

- Statcast (pitch-level MLB, 2015–) is not in the archive. See `docs/roadmap.md`.
- Retrosheet event files are downloaded but not parsed; that needs Chadwick (stage 2).
- The GitHub API calls behind the sportsdataverse sources are unauthenticated (60/hour). Set
  `GITHUB_TOKEN` if you refetch often.
- Lahman's SABR page states no formal license for the current edition. Ask lahmandb@sabr.org before publishing derivatives.
