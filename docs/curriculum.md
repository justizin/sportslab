# Curriculum: machine learning and statistics through sports data

Written 2026-10-25 for a strong programmer with little ML or statistics background. Every stage
pairs one bounded concept with one canonical sports project on data already in the archive. Do
them in order; each project's acceptance check is something you can verify yourself.

Time budget guess: 2 to 4 weeks per stage at a few hours a week. Stages 0 to 2 are faster.

## The spine (read alongside every stage)

| Resource | What it is for | Cost | Link |
|---|---|---|---|
| **An Introduction to Statistical Learning, Python edition (ISLP)** | The textbook. Regression, classification, resampling, regularization, trees, in that order. Each chapter has a Python lab. | Free PDF | https://www.statlearning.com/ |
| **StatQuest** (Josh Starmer) | Ten-minute intuition videos for every ISLP concept. Watch before reading the chapter. | Free | https://statquest.org/ and https://www.youtube.com/@statquest |
| **Think Stats, 3rd ed.** (Allen Downey) | Exploratory statistics in Python: distributions, variance, correlation, hypothesis tests. Stages 0 and 1. | Free, CC, runnable notebooks | https://allendowney.github.io/ThinkStats/ |
| **Analyzing Baseball Data with R, 3rd ed.** (Albert, Baumer, Marchi) | The best book on sabermetric *method*: run expectancy, Retrosheet, Statcast. It is in R; translate the exercises to Python, which is itself good practice. | Free online | https://beanumber.github.io/abdwr3e/ |
| **FanGraphs Sabermetrics Library** | Concept dictionary: wOBA, FIP, WAR, Pythagorean record, RE24, regression to the mean. | Free | https://library.fangraphs.com/ |
| **scikit-learn user guide** | Pipelines, cross-validation, model selection. Reference, not a course. | Free | https://scikit-learn.org/stable/user_guide.html |

Optional alternatives to the ISLP spine, if you prefer video: Andrew Ng's Machine Learning
Specialization (Coursera, audit free, https://www.coursera.org/specializations/machine-learning-introduction).
Pick one spine and stick to it.

## Sports-specific supplements

- **SportsDataTutorials** (https://sportsdatatutorials.com/tracks/): 11 free Python tracks covering Statcast, the NBA API, StatsBomb and xG, and nflverse. Anonymous author, unvetted, but it is the closest free Python-first match to this curriculum. Use it when you want a second worked example.
- **Soccermatics / Mathematical Modelling of Football** (Uppsala, David Sumpter, https://soccermatics.readthedocs.io/): free lessons on xG, action valuation and pitch control using StatsBomb data. Stage 3.
- **Open Source Football** (https://www.opensourcefootball.com/): the blog behind nflfastR's EP and WP models. Stage 5.
- **nflverse** (https://nflverse.nflverse.com/) and **nflreadpy** (https://github.com/nflverse/nflreadpy): data dictionary for `nfl.pbp`.
- **Cleaning the Glass** (https://cleaningtheglass.com/): NBA stats with garbage time removed; paid, but the free articles explain why that matters.
- **U-Michigan Sports Performance Analytics** (Coursera, https://www.coursera.org/specializations/sports-analytics): shallow on ML, fine as a guided warm-up; its "Intro to ML in Sports Analytics" course is probably the paid "learn ML with baseball" tutorial you remember.
- Books worth owning later: *The Book: Playing the Percentages in Baseball* (Tango, Lichtman, Dolphin), *Basketball on Paper* (Dean Oliver), *Mathletics* 2nd ed. (Winston, Nestler, Pelechrinis), *Soccermatics* (Sumpter).

## Tooling

pandas, scikit-learn and statsmodels for the learning stages, because that is what ISLP and every
tutorial use. polars and DuckDB for anything touching the full archive. XGBoost from stage 5.
PyMC from stage 7. Notebooks are marimo (`uv run marimo edit stages/<stage>/exercise.py`): plain
Python files, no hidden state, diffs cleanly.

## Stages

### Stage 0: the data stack

- **Concept**: tidy data, joins, group-by, SQL via DuckDB, plotting. Think Stats ch 1 to 2; DuckDB SQL intro (https://duckdb.org/docs/sql/introduction).
- **Project**: rebuild the 2025 MLB standings from `mlb.teams` and the 2024 NFL standings from `nfl.schedules`. Plot runs scored vs runs allowed for every team-season since 1901.
- **Check**: your standings match Baseball-Reference and Pro-Football-Reference exactly.
- **Data**: Lahman, nflverse.

### Stage 1: distributions, variance and one-parameter fits

- **Concept**: histograms and CDFs, mean vs median, variance, correlation, fitting one parameter by minimizing squared error, residuals, what "luck" means statistically. Think Stats ch 3 to 7; StatQuest "Statistics Fundamentals" playlist.
- **Project**: **Pythagorean expectation**. Fit the exponent in `win% = RS^k / (RS^k + RA^k)` for MLB, then repeat for NFL points, WNBA and NBA points, and soccer goals. Compare residual spread across sports and relate it to season length and scoring frequency.
- **Check**: MLB exponent lands between 1.8 and 1.9. Residual standard deviation is largest in the sport with the fewest games.
- **Data**: Lahman `mlb.teams`, `nfl.schedules`, `wnba.team_box`, `nba.team_box`, `soccer.results`.
- **Reading**: FanGraphs Library on Pythagorean record; Wikipedia's derivation of the 1.83 exponent.

### Stage 2: linear regression

- **Concept**: least squares, coefficients as marginal effects, confidence intervals, multicollinearity, R². ISLP ch 2 to 3; StatQuest linear regression videos.
- **Project A**: **run expectancy and linear weights**. Build the 24-state run expectancy matrix from Retrosheet event files (parse with Chadwick, see roadmap), then regress runs on event counts to recover the linear weights behind wOBA. ABDwR chapter on run expectancy.
- **Project B**: **Four Factors**. Regress team point differential on effective FG%, turnover rate, offensive rebound rate and free-throw rate from `wnba.team_box` and `nba.team_box`. Compare the coefficients to Dean Oliver's weights.
- **Check**: linear weight for a home run is near 1.4 runs and a walk near 0.3; Four Factors R² above 0.9 on season totals.
- **Data**: Retrosheet, wehoop, hoopR.

### Stage 3: classification, calibration, cross-validation

- **Concept**: logistic regression, log loss and Brier score, calibration curves, train/test split, k-fold cross-validation, the bootstrap. ISLP ch 4 to 5.
- **Project**: **expected goals (xG)**. From `soccer.sb_events` shots, fit logistic regression on distance and angle to goal, then add body part, technique, under pressure and freeze-frame defender counts. Plot calibration. Compare your log loss to StatsBomb's own `shot_statsbomb_xg`.
- **Check**: your simple model's log loss beats "always predict the base rate"; calibration curve lies near the diagonal; adding freeze-frame features improves held-out log loss.
- **Reading**: Soccermatics lesson 2 (https://soccermatics.readthedocs.io/en/latest/gallery/lesson2/plot_xGModelFit.html).

### Stage 4: regularization, shrinkage and regression to the mean

- **Concept**: ridge and lasso, choosing lambda by cross-validation, why shrinkage is the same idea as regression to the mean, survivor bias. ISLP ch 6.
- **Project A**: **RAPM**. Build stints from `nba.pbp` and `wnba.pbp` (who was on the floor, point margin per possession), encode players as plus/minus one indicators, fit ridge regression. Watch what happens to the coefficients as lambda moves.
- **Project B**: **Marcel projections** for batting (three-year weighted average, regress to the mean, age adjustment) from Lahman, then **aging curves** with the delta method and a note on survivor bias.
- **Check**: top RAPM names look like All-NBA players and the unregularized fit is nonsense; Marcel beats "repeat last year" on held-out seasons.
- **Reading**: Tango's Marcel page (http://www.tangotiger.net/marcel/); Squared2020 RAPM walkthrough (https://squared2020.com/2017/09/18/deep-dive-on-regularized-adjusted-plus-minus-ii-basic-application-to-2017-nba-data-with-r/); Hardball Times aging curves (https://tht.fangraphs.com/how-do-baseball-players-age-part-1/).

### Stage 5: trees and gradient boosting

- **Concept**: decision trees, random forests, gradient boosting, leave-one-season-out validation, feature leakage. ISLP ch 8.
- **Project A**: **NFL win probability and expected points** with XGBoost on `nfl.pbp`: down, distance, yard line, time, score differential, timeouts, Vegas spread. Validate by holding out whole seasons. Compare to nflfastR's `wp` column.
- **Project B**: **T20 win probability** from `cricket.deliveries`: balls remaining, runs required, wickets in hand, venue. Then derive per-player win probability added.
- **Check**: held-out log loss within a few percent of nflfastR's; your T20 model is well calibrated in the last five overs.
- **Reading**: Open Source Football on nflfastR EP/WP (https://www.opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/).

### Stage 6: rating systems and evaluating against a market

- **Concept**: sequential updating, Elo and its parameters (K, home advantage, margin of victory, season regression), proper scoring rules, what it means to beat bookmaker odds.
- **Project**: one Elo implementation run over all six sports' schedules. Tune per sport by log loss. For soccer, compare your probabilities to the Bet365 and Pinnacle closing odds in `soccer.results`.
- **Check**: your tuned Elo beats a home-win baseline everywhere and loses to the Pinnacle closing line everywhere. Both are the expected result.
- **Reading**: FiveThirtyEight's Elo methodology via archive.org (the original pages are gone); the data lives on at https://github.com/fivethirtyeight/data/tree/master/nfl-elo. Neil Paine's revival: https://neilpaine.substack.com/p/nfl-elo-ratings-are-back.

### Stage 7: Bayesian modelling

- **Concept**: priors, posteriors, hierarchical models, posterior predictive checks. Statistical Rethinking 2026 lectures (https://github.com/rmcelreath/stat_rethinking_2026) with the PyMC port (https://github.com/dustinstansbury/statistical-rethinking-2023).
- **Project A**: hierarchical model of batting average or three-point percentage where each player's true talent is drawn from a league distribution. This is stage 4's shrinkage done properly, with uncertainty.
- **Project B**: fit your own **Duckworth-Lewis-Stern** resource table from `cricket.deliveries` (resources remaining as a function of overs left and wickets lost) and compare to the official table (ECB methodology PDF: https://resources.ecb.co.uk/ecb/document/2026/03/24/0ec6d250-8e00-4150-b3b3-1afb64e4853b/Duckworth-Lewis-Stern-Methodology.pdf).
- **Check**: posterior means for low-sample players shrink toward the league mean more than high-sample players; your resource table is monotone and within a few percent of the official one in the middle of the innings.

### Stage 8: writing it up

- **Project**: pick one piece (cricket win probability and DLS is the least crowded space; cross-sport Elo is the most general) and write it up with figures in `docs/notes/`. Publish as a static site, the way `edge-models` does.
- **Check**: someone who has not seen the code can reproduce the headline figure from the README alone.

## Likely candidates for the course you bought

The "learn machine learning with baseball" tutorial was most likely one of: the University of
Michigan Coursera course "Introduction to Machine Learning in Sports Analytics" (MLB data,
scikit-learn), DataCamp's two-part scikit-learn baseball tutorial
(https://www.datacamp.com/tutorial/scikit-learn-tutorial-baseball-1), or a Udemy "Sports
Analytics in Python" course. None is required here; all of them cover stage 1 to 3 material.
