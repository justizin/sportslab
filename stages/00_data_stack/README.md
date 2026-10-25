# Stage 0: the data stack

**Concept.** Tidy data (one row per observation), joins, group-by aggregation, SQL through
DuckDB, and a first plot. Nothing statistical yet; this stage is about trusting your tools and
your data before you model anything.

**Read first.** Think Stats 3e, chapters 1 and 2 (https://allendowney.github.io/ThinkStats/).
DuckDB's SQL introduction (https://duckdb.org/docs/sql/introduction). Skim the Lahman
`readme2025.txt` in `data/raw/lahman/<date>/` for what the `Teams` table columns mean.

**Tables used.** `mlb.gamelog` (Retrosheet, one row per game), `mlb.teams` (Lahman, one row
per team-season), `nfl.schedules` (nflverse, one row per game).

## Task (worked in `exercise.py`)

1. Build the 2025 MLB standings from `mlb.gamelog`: wins, losses, runs scored and allowed per team.
   A game log row has a visiting and a home team, so each game contributes to two team rows.
2. Join those standings to Lahman's `mlb.teams` for 2025 and confirm the win and loss columns agree.
   Where they do not, find out why before moving on.
3. Build the 2024 NFL regular-season standings from `nfl.schedules`, counting ties as half a win.
4. Plot runs scored against runs allowed for every MLB team-season since 1901, coloring by
   winning percentage. You should see the diagonal, and you should see that the spread around it
   is wide. Stage 1 is about that spread.

## Acceptance check

- 2025 MLB: 30 teams, every team has 162 games (or 161/163 for a rained-out or tie-broken season),
  and your W/L match Lahman's for all 30.
- 2024 NFL: 32 teams, 17 games each, and the Detroit Lions and Kansas City Chiefs each have 15 wins.

## What to notice

- Lahman is season-level and curated; Retrosheet is game-level and raw. They agree on wins and
  losses, which is a useful check that you understood both. When two sources disagree, that is
  information, not noise.
- Everything you did here was aggregation. No model has been fit. Much of sports analytics is
  exactly this, done carefully.
