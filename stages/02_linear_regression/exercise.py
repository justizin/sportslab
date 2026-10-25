import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        r"""
        # Stage 2: linear regression. Project B, Four Factors

        Fill in every `TODO`. Project A (run expectancy) lives in `README.md` until Chadwick is
        built; its cells are at the bottom as stubs.
        """
    )
    return (mo,)


@app.cell
def _():
    import numpy as np
    import polars as pl
    import statsmodels.api as sm

    from sportslab import catalog

    con = catalog.connect()
    return con, np, pl, sm


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. Team-season totals with opponent totals

        `wnba.team_box` has one row per team per game. Join each row to the opponent's row on
        `game_id` to get what the opponent did, then sum per `season, team_id`.

        Columns: `field_goals_made`, `field_goals_attempted`, `three_point_field_goals_made`,
        `free_throws_made`, `free_throws_attempted`, `offensive_rebounds`, `defensive_rebounds`,
        `total_turnovers`, `team_score`. Regular season is `season_type = 2`.
        """
    )
    return


@app.cell
def _(con):
    def team_season_totals(schema: str = "wnba", min_games: int = 20):
        # TODO: write the self-join and aggregation. Return one row per season-team with own
        # totals (prefix nothing) and opponent totals (prefix opp_), plus g.
        # Trap: cast the sums to DOUBLE in SQL (sum(x)::DOUBLE). DuckDB sums integers into a 128-bit
        # type, pandas carries that as `object`, and statsmodels then either errors or quietly fits
        # a worse model. The first version of the solution reported R² = 0.87 for exactly this reason.
        raise NotImplementedError

    totals = team_season_totals()
    assert totals.filter(totals["season"] == 2024).height >= 12
    totals.head()
    return (totals,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. The eight factors and net rating

        - eFG% = (FGM + 0.5 × 3PM) / FGA
        - TOV% = TOV / (FGA + 0.44 × FTA + TOV)
        - ORB% = ORB / (ORB + opponent DRB)
        - FTR = FTM / FGA
        - possessions ≈ FGA + 0.44 × FTA − ORB + TOV (average own and opponent)
        - net rating = 100 × (points − opponent points) / possessions

        The defensive factors are the opponent's eFG%, TOV%, ORB% (their ORB against your DRB), FTR.
        """
    )
    return


@app.cell
def _(pl, totals):
    def four_factors(df: pl.DataFrame) -> pl.DataFrame:
        # TODO: add columns efg, tov, orb, ftr, opp_efg, opp_tov, opp_orb, opp_ftr, net_rtg
        raise NotImplementedError

    ff = four_factors(totals)
    assert ff["efg"].is_between(0.35, 0.65).all()
    ff.select("season", "team", "net_rtg", "efg", "tov", "orb", "ftr", "opp_efg", "opp_tov", "opp_orb", "opp_ftr").head()
    return (ff,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. Fit OLS

        `statsmodels` gives you the full summary: coefficients, standard errors, t statistics,
        confidence intervals, R². Read every line of the summary once and look up anything you
        do not recognize.
        """
    )
    return


@app.cell
def _(ff, sm):
    FACTORS = ["efg", "tov", "orb", "ftr", "opp_efg", "opp_tov", "opp_orb", "opp_ftr"]

    def fit_ols(df, cols=FACTORS, y="net_rtg"):
        # TODO: X = add_constant(df[cols]), fit sm.OLS, return the results object
        raise NotImplementedError

    model = fit_ols(ff)
    assert model.rsquared > 0.90, f"R² = {model.rsquared:.3f}"
    print(model.summary())
    return FACTORS, fit_ols, model


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Standardize and compare to Oliver's 40/25/20/15

        Convert each factor to z-scores, refit, and compare the absolute standardized coefficients
        (offense and defense of the same factor added together) as shares of their total.
        """
    )
    return


@app.cell
def _(FACTORS, ff, fit_ols, pl):
    # TODO: z-score the factors, refit, compute shares
    shares = None
    shares
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. Multicollinearity

        Variance inflation factor for each predictor:
        `statsmodels.stats.outliers_influence.variance_inflation_factor`. A VIF above 5 is worth
        a comment; above 10 the coefficient's interpretation is shaky.
        """
    )
    return


@app.cell
def _(FACTORS, ff):
    # TODO: compute VIFs
    vif = None
    vif
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Project A: run expectancy (after building Chadwick)

        See README. Once you have `events_2024.csv`, load it here, compute runs-to-end-of-inning per
        plate appearance, group by `(START_BASES_CD, OUTS_CT)` for the 24-state matrix, then regress
        inning runs on event counts for linear weights.
        """
    )
    return


@app.cell
def _():
    # TODO: events_path = Path("...events_2024.csv"); re24 = ...
    return


if __name__ == "__main__":
    app.run()
