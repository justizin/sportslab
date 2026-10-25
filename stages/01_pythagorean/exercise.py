import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        r"""
        # Stage 1: Pythagorean expectation across five sports

        Fill in every `TODO`. The cells after each stub assert what they can, so a wrong answer
        fails loudly. Read `README.md` in this directory first.
        """
    )
    return (mo,)


@app.cell
def _():
    import numpy as np
    import matplotlib.pyplot as plt
    import polars as pl

    from sportslab import catalog

    con = catalog.connect()
    return con, np, pl, plt


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. Team-season tables

        Build one polars frame per sport with the columns
        `sport, season, team, g, w, l, t, win_pct, scored, allowed`.
        Ties count as half a win in `win_pct`. Use SQL or polars, your choice.
        """
    )
    return


@app.cell
def _(con):
    def mlb_seasons():
        """Lahman mlb.teams: yearID, teamID, G, W, L, R, RA. Seasons >= 1901 with G >= 100.
        Lahman has no tie column; treat ties as zero."""
        # TODO: write the query
        return con.sql(
            """
            select 'MLB' as sport, yearID as season, teamID as team, G as g, W as w, L as l, 0 as t,
                   W / (W + L) as win_pct, R as scored, RA as allowed
            from mlb.teams
            where yearID >= 1901 and G >= 100
            """
        ).pl()

    mlb = mlb_seasons()
    assert mlb.height > 2000 and mlb["win_pct"].is_between(0, 1).all()
    mlb.head()
    return (mlb,)


@app.cell
def _(con):
    def nfl_seasons():
        """nfl.schedules: one row per game, game_type = 'REG'. Stack home and away views,
        then aggregate per season and team. Ties exist."""
        # TODO: write the query (see stage 0, cell 3, for the pattern)
        raise NotImplementedError

    nfl = nfl_seasons()
    assert nfl.filter(pl.col("season") == 2024).height == 32
    nfl.head()
    return (nfl,)


@app.cell
def _(con):
    def wnba_seasons():
        """wnba.team_box: one row per team per game. season_type = 2 is the regular season.
        Columns: season, team_display_name, team_score, opponent_team_score, team_winner."""
        # TODO
        raise NotImplementedError

    wnba = wnba_seasons()
    assert wnba["g"].max() <= 44
    wnba.head()
    return (wnba,)


@app.cell
def _(con):
    def soccer_seasons():
        """soccer.results: one row per match. FTHG/FTAG are full-time goals, FTR is H/D/A.
        Define win_pct as points earned (3/1/0) over points available (3 per match).
        Keep one league to start, e.g. Div = 'E0'."""
        # TODO
        raise NotImplementedError

    soccer = soccer_seasons()
    soccer.head()
    return (soccer,)


@app.cell
def _(mlb, nfl, pl, soccer, wnba):
    seasons = pl.concat([mlb, nfl, wnba, soccer], how="vertical_relaxed")
    seasons.group_by("sport").agg(pl.len().alias("team_seasons"), pl.col("g").mean().alias("mean_games"))
    return (seasons,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. Fit the exponent

        Two estimators. `fit_k_grid` minimizes squared error over a grid; `fit_k_log` takes the
        slope of `log(W/L)` on `log(scored/allowed)` through the origin. Teams with zero wins or
        losses break the log version; decide what to do with them and say so.
        """
    )
    return


@app.cell
def _(np):
    def pythag(scored, allowed, k):
        return scored**k / (scored**k + allowed**k)

    def fit_k_grid(scored, allowed, win_pct, ks=np.linspace(1.0, 3.0, 401)):
        """Return the k with the smallest sum of squared errors, and the SSE curve."""
        # TODO
        raise NotImplementedError

    def fit_k_log(w, l, scored, allowed):
        """Least-squares slope through the origin of log(w/l) on log(scored/allowed)."""
        # TODO
        raise NotImplementedError

    return fit_k_grid, fit_k_log, pythag


@app.cell
def _(fit_k_grid, fit_k_log, pl, seasons):
    fits = []
    # marimo: a name may be defined in only one cell; loop variables with a leading underscore are cell-private
    for (_sport,), _df in seasons.group_by("sport", maintain_order=True):
        _k_grid, _ = fit_k_grid(_df["scored"].to_numpy(), _df["allowed"].to_numpy(), _df["win_pct"].to_numpy())
        _k_log = fit_k_log(_df["w"].to_numpy(), _df["l"].to_numpy(), _df["scored"].to_numpy(), _df["allowed"].to_numpy())
        fits.append({"sport": _sport, "k_grid": _k_grid, "k_log": _k_log})
    fits = pl.DataFrame(fits)
    mlb_k = fits.filter(pl.col("sport") == "MLB")["k_grid"][0]
    assert 1.80 <= mlb_k <= 1.90, f"MLB k = {mlb_k:.3f}; expected about 1.83"
    fits
    return (fits,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Residuals

        Predicted minus actual win%, per sport, using each sport's own `k_grid`.
        Histogram each; report the standard deviation; explain the ranking.
        """
    )
    return


@app.cell
def _(fits, plt, pythag, seasons):
    # TODO: add a `pred` and `resid` column to `seasons` using the per-sport k, then plot
    resid = None
    fig = None
    fig
    return (resid,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Luck, and what happened next

        For each sport, list the five team-seasons with the largest positive residual (lucky) and
        the five most negative (unlucky). Then join each to the same team's next season and
        compare actual win% to this season's. Did the lucky ones come back down?
        """
    )
    return


@app.cell
def _(resid):
    # TODO
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. Write it up

        `docs/notes/01_pythagorean.md`, one page: the five k values, the residual ranking and
        your explanation of it, and one sentence on why soccer fits worse. Include one figure.
        """
    )
    return


if __name__ == "__main__":
    app.run()
