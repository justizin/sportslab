import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(r"""# Stage 2 solution: Four Factors regression (WNBA)""")
    return (mo,)


@app.cell
def _():
    import numpy as np
    import polars as pl
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    from sportslab import catalog

    con = catalog.connect()
    return con, np, pl, sm, variance_inflation_factor


@app.cell
def _(con):
    def team_season_totals(schema: str = "wnba", min_games: int = 20):
        return con.sql(
            f"""
            with box as (
                select game_id, season, team_id, team_display_name as team,
                       field_goals_made as fgm, field_goals_attempted as fga,
                       three_point_field_goals_made as fg3m,
                       free_throws_made as ftm, free_throws_attempted as fta,
                       offensive_rebounds as orb, defensive_rebounds as drb,
                       total_turnovers as tov, team_score as pts
                from {schema}.team_box
                where season_type = 2 and field_goals_attempted > 0
            )
            -- ::DOUBLE because DuckDB sums integers into a 128-bit type that pandas would carry as object
            select a.season, a.team_id, a.team, count(*)::DOUBLE as g,
                   sum(a.fgm)::DOUBLE fgm, sum(a.fga)::DOUBLE fga, sum(a.fg3m)::DOUBLE fg3m, sum(a.ftm)::DOUBLE ftm,
                   sum(a.fta)::DOUBLE fta, sum(a.orb)::DOUBLE orb, sum(a.drb)::DOUBLE drb, sum(a.tov)::DOUBLE tov,
                   sum(a.pts)::DOUBLE pts,
                   sum(b.fgm)::DOUBLE opp_fgm, sum(b.fga)::DOUBLE opp_fga, sum(b.fg3m)::DOUBLE opp_fg3m,
                   sum(b.ftm)::DOUBLE opp_ftm, sum(b.fta)::DOUBLE opp_fta, sum(b.orb)::DOUBLE opp_orb,
                   sum(b.drb)::DOUBLE opp_drb, sum(b.tov)::DOUBLE opp_tov, sum(b.pts)::DOUBLE opp_pts
            from box a
            join box b on a.game_id = b.game_id and a.team_id <> b.team_id
            group by a.season, a.team_id, a.team
            having count(*) >= {min_games}
            order by a.season, a.team
            """
        ).pl()

    totals = team_season_totals()
    totals.head()
    return (totals,)


@app.cell
def _(pl, totals):
    def four_factors(df: pl.DataFrame) -> pl.DataFrame:
        c = pl.col
        poss_own = c("fga") + 0.44 * c("fta") - c("orb") + c("tov")
        poss_opp = c("opp_fga") + 0.44 * c("opp_fta") - c("opp_orb") + c("opp_tov")
        return df.with_columns(
            ((c("fgm") + 0.5 * c("fg3m")) / c("fga")).alias("efg"),
            (c("tov") / (c("fga") + 0.44 * c("fta") + c("tov"))).alias("tov"),
            (c("orb") / (c("orb") + c("opp_drb"))).alias("orb"),
            (c("ftm") / c("fga")).alias("ftr"),
            ((c("opp_fgm") + 0.5 * c("opp_fg3m")) / c("opp_fga")).alias("opp_efg"),
            (c("opp_tov") / (c("opp_fga") + 0.44 * c("opp_fta") + c("opp_tov"))).alias("opp_tov"),
            (c("opp_orb") / (c("opp_orb") + c("drb"))).alias("opp_orb"),
            (c("opp_ftm") / c("opp_fga")).alias("opp_ftr"),
            (100 * (c("pts") - c("opp_pts")) / ((poss_own + poss_opp) / 2)).alias("net_rtg"),
        )

    ff = four_factors(totals)
    ff.select("season", "team", "g", "net_rtg", "efg", "tov", "orb", "ftr").sort("net_rtg", descending=True).head(8)
    return (ff,)


@app.cell
def _(ff, sm):
    FACTORS = ["efg", "tov", "orb", "ftr", "opp_efg", "opp_tov", "opp_orb", "opp_ftr"]

    def fit_ols(df, cols=FACTORS, y="net_rtg"):
        X = sm.add_constant(df.select(cols).to_pandas())
        return sm.OLS(df[y].to_pandas(), X).fit()

    model = fit_ols(ff)
    assert model.rsquared > 0.90, f"R² = {model.rsquared:.3f}"
    print(model.summary())
    return FACTORS, fit_ols, model


@app.cell
def _(FACTORS, ff, fit_ols, pl):
    z = ff.with_columns([((pl.col(c) - pl.col(c).mean()) / pl.col(c).std()).alias(c) for c in FACTORS])
    zmodel = fit_ols(z)
    coefs = zmodel.params.drop("const").abs()
    combined = {
        "shooting": coefs["efg"] + coefs["opp_efg"],
        "turnovers": coefs["tov"] + coefs["opp_tov"],
        "rebounding": coefs["orb"] + coefs["opp_orb"],
        "free throws": coefs["ftr"] + coefs["opp_ftr"],
    }
    total = sum(combined.values())
    shares = pl.DataFrame({
        "factor": list(combined),
        "share_of_standardized_effect": [round(v / total, 3) for v in combined.values()],
        "oliver": [0.40, 0.25, 0.20, 0.15],
    })
    shares
    return


@app.cell
def _(FACTORS, ff, np, pl, variance_inflation_factor):
    X = ff.select(FACTORS).to_numpy()
    X = np.column_stack([np.ones(len(X)), X])
    vif = pl.DataFrame({"factor": FACTORS, "vif": [round(variance_inflation_factor(X, i + 1), 2) for i in range(len(FACTORS))]})
    vif
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Reading the results

        - R² is very high because the eight factors almost define the score; the regression is
          recovering an accounting identity plus noise from the 0.44 free-throw approximation.
        - Shooting dominates the standardized effect, as Oliver said. The exact shares differ from
          40/25/20/15 because his weights came from a different decomposition, not a regression.
        - VIFs are modest: the factors were designed to be close to independent (that is the point of
          dividing by possessions rather than using raw counts). Try the same regression on raw
          counts (FGM, FGA, 3PM, ...) and watch the VIFs explode while R² barely moves. That is the
          multicollinearity lesson in one experiment.
        """
    )
    return


if __name__ == "__main__":
    app.run()
