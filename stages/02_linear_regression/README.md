# Stage 2: linear regression

**Concept.** Least squares with several predictors. Coefficients as marginal effects ("one more
unit of x, holding the rest fixed"), standard errors and confidence intervals, R² and what it
does not tell you, and multicollinearity: when predictors move together, individual coefficients
become unstable even if predictions do not.

**Read first.** ISLP chapters 2 and 3 (https://www.statlearning.com/), and do the chapter 3 lab.
StatQuest: "Linear Regression, Clearly Explained" and "Multiple Regression". For project A, the
run expectancy chapter of Analyzing Baseball Data with R (https://beanumber.github.io/abdwr3e/).
For project B, the Four Factors section of Dean Oliver's *Basketball on Paper*, or the summary at
https://www.basketball-reference.com/about/factors.html.

## Project B first: Four Factors (WNBA, and NBA if fetched)

Dean Oliver argued that basketball success comes down to four things on each end of the floor:
shooting (effective field goal percentage), turnovers (per possession), rebounding (offensive
rebound percentage), and free throws (made per field goal attempt). He weighted them 40 / 25 / 20 / 15.

1. From `wnba.team_box` (regular season, `season_type = 2`), build per team-season totals of made
   and attempted field goals, threes, free throws, offensive and defensive rebounds, turnovers, and
   points. Each game appears twice (once per team), and the opponent's row is in the same table
   with the same `game_id`, so a self-join gives you the opponent's totals.
2. Compute the eight factors: the four for the offense and the same four for the defense (what
   opponents did against you). Formulas are in `exercise.py`.
3. Regress net rating (point differential per 100 possessions) on the eight factors with
   statsmodels OLS. Report coefficients, confidence intervals, and R².
4. Standardize the predictors and refit. Compare the relative sizes of the coefficients to
   Oliver's 40/25/20/15.
5. Compute variance inflation factors. Which factors are entangled, and does it matter for
   prediction, for interpretation, or both?

**Acceptance check.** R² above 0.90 on season totals. Signs: shooting and rebounding positive,
turnovers negative, free-throw rate positive, with the defensive versions reversed. Shooting has
the largest standardized coefficient.

## Project A: run expectancy and linear weights (MLB)

The 24 base-out states (8 base configurations × 3 out counts) each have an expected number of
runs scored from that point to the end of the inning. The matrix of those expectations is the
foundation of modern baseball valuation: the run value of any event is the change in expectancy
plus the runs scored on the play, and averaging those changes per event type gives linear
weights, which is how wOBA is built.

This needs play-by-play, which means parsing Retrosheet's event files. The archive has them in
`data/raw/retrosheet/<date>/alldata.zip`, but parsing them needs Chadwick, which is not built yet.
That build is part of this stage:

```sh
git clone https://github.com/chadwickbureau/chadwick ~/src/chadwick
cd ~/src/chadwick && autoreconf -i && ./configure --prefix=$HOME/.local && make -j && make install
cd $(mktemp -d) && unzip -q ~/src/claude/sportslab/data/raw/retrosheet/*/alldata.zip '2024*' 'TEAM2024'
cwevent -y 2024 -f 0-96 -n 2024*.EV* > events_2024.csv
```

Then, in order:

1. Load `events_2024.csv` (97 fields, header row included because of `-n`). The columns you need:
   `INN_CT`, `BAT_HOME_ID`, `OUTS_CT`, `START_BASES_CD`, `EVENT_RUNS_CT`, `INN_END_FL`, and the
   `BAT_EVENT_FL` / `EVENT_CD` pair for event types.
2. For each plate appearance, compute runs scored from that point to the end of the half-inning
   (a cumulative sum within inning, reversed).
3. Average that by (bases, outs) to get the 24-cell matrix. Compare with the published 2024 matrix
   on FanGraphs or Baseball Prospectus.
4. Regress inning runs on counts of singles, doubles, triples, home runs, walks, hit-by-pitch and
   outs. The coefficients are the linear weights. Compare to the FanGraphs wOBA weights for 2024.

**Acceptance check.** Bases empty, no outs is about 0.5 runs; bases loaded, no outs about 2.3.
Linear weight of a home run about 1.4, a walk about 0.3, an out about -0.27.

Once Chadwick works, add a `mlb.events` normalizer to the archive (see `docs/roadmap.md`) so the
next stages can query events directly.

## What to notice

- Regression coefficients are *conditional* effects. The Four Factors coefficients tell you the
  value of a point of eFG% *given* the other factors. That is why they do not match Oliver's weights
  exactly: his are a different decomposition.
- R² near 1 on season totals is not impressive. The eight factors nearly *define* the score; the
  regression is recovering an identity plus noise. Ask what the model would be for if you already
  know the answer.
- The run expectancy matrix is not a regression at all. It is a group-by. Much of the field is
  careful averaging; regression enters when you want to attribute credit across correlated events.
