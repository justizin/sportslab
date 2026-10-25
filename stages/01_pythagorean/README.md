# Stage 1: distributions, residuals, and fitting one parameter

**Concept.** Histograms and cumulative distributions; mean, variance and standard deviation;
correlation; fitting a single parameter by minimizing squared error; residuals; and the
statistical meaning of "luck": the part of an outcome a model with the right inputs still cannot
explain.

**Read first.** Think Stats 3e chapters 3 to 7. StatQuest "Statistics Fundamentals" playlist, at
least the videos on the mean, variance, and least squares. FanGraphs Library on Pythagorean
record (https://library.fangraphs.com/principles/expected-wins-and-losses/).

**Tables used.** `mlb.teams`, `nfl.schedules`, `wnba.team_box`, `soccer.results`, and
`nba.team_box` if you fetched the opt-in hoopR source.

## Task

Bill James noticed that a baseball team's winning percentage is well predicted by

    win% ≈ RS^k / (RS^k + RA^k)

with k near 2. Later work put k at about 1.83. Your job is to find k yourself, for five sports,
and then think about what the residuals mean.

1. **Build the team-season table** for each sport: games, wins, losses (ties as half), points or
   runs or goals scored and allowed. The stubs in `exercise.py` tell you which columns to use.
2. **Fit k** two ways. First, a grid search over k from 1.0 to 3.0 minimizing the sum of squared
   errors between predicted and actual win%. Second, the linear trick: taking logs gives
   `log(W/L) = k · log(RS/RA)`, which is a straight line through the origin, so k is a slope you
   can get from least squares. Do the two methods agree? When would they not?
3. **Look at residuals** (actual minus predicted win%). Plot a histogram per sport. Compute the
   standard deviation. Which sport has the widest residual spread, and why? Think about games per
   season and points per game.
4. **Pick out the luckiest and unluckiest team-seasons** in each sport. Look a few up. Did the
   lucky teams regress the following season?
5. **Soccer is different.** Draws are common and three points for a win changes the objective.
   Fit anyway, with win% defined as points earned divided by points available. The fit will be
   worse. Say why in a sentence.

## Acceptance check

- MLB: k between 1.80 and 1.90 by both methods, on team-seasons since 1901 with at least 100 games.
- NFL: k is larger than MLB's (published values run 2.4 to 2.7).
- Residual standard deviation ranks NFL > WNBA ≈ NBA > MLB, or you can explain why it does not.
- Your residual histogram is roughly bell-shaped and centered near zero for every sport.

## What to notice

- A one-parameter model explaining 85 to 90 percent of the variance in wins is unusual. Most of
  what is left is sequencing (when the runs happened), which is the formal content of "luck".
- Fewer games means more noise. A 17-game NFL season can never be as informative as 162 games.
  This is the first appearance of sample size, which will run through every later stage.
- Two reasonable methods give slightly different k. There is no single right answer to "what is k";
  there is a right answer to "what did you minimize".
