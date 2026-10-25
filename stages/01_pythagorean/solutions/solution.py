import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        r"""
        # Stage 1 solution: Pythagorean expectation across five sports

        One way to do it. Yours may differ in the details (how you handle ties, which seasons you
        keep); what matters is that you can defend each choice.
        """
    )
    return (mo,)


@app.cell
def _():
    import matplotlib.pyplot as plt
    import numpy as np
    import polars as pl

    from sportslab import catalog

    con = catalog.connect()
    return con, np, pl, plt


@app.cell
def _(con):
    mlb = con.sql(
        """
        select 'MLB' as sport, yearID as season, teamID as team, G as g, W as w, L as l, 0 as t,
               W / (W + L) as win_pct, R as scored, RA as allowed
        from mlb.teams
        where yearID >= 1901 and G >= 100
        """
    ).pl()
    return (mlb,)


@app.cell
def _(con):
    nfl = con.sql(
        """
        with team_games as (
            select season, home_team as team, home_score as pf, away_score as pa
            from nfl.schedules where game_type = 'REG' and home_score is not null
            union all
            select season, away_team as team, away_score as pf, home_score as pa
            from nfl.schedules where game_type = 'REG' and away_score is not null
        )
        select 'NFL' as sport, season, team,
               count(*) as g,
               count(*) filter (where pf > pa) as w,
               count(*) filter (where pf < pa) as l,
               count(*) filter (where pf = pa) as t,
               (w + 0.5 * t) / g as win_pct,
               sum(pf) as scored, sum(pa) as allowed
        from team_games
        group by season, team
        having g >= 16
        """
    ).pl()
    return (nfl,)


@app.cell
def _(con):
    # ESPN season_type: 1 preseason, 2 regular season, 3 postseason
    wnba = con.sql(
        """
        select 'WNBA' as sport, season, team_display_name as team,
               count(*) as g,
               count(*) filter (where team_winner) as w,
               count(*) filter (where not team_winner) as l,
               0 as t,
               w / g as win_pct,
               sum(team_score) as scored, sum(opponent_team_score) as allowed
        from wnba.team_box
        where season_type = 2
        group by season, team_display_name
        having g >= 20
        """
    ).pl()
    return (wnba,)


@app.cell
def _(con):
    # English Premier League only; win_pct is points earned over points available
    soccer = con.sql(
        """
        with team_games as (
            select season_start as season, HomeTeam as team, FTHG as gf, FTAG as ga,
                   case FTR when 'H' then 3 when 'D' then 1 else 0 end as pts
            from soccer.results where Div = 'E0' and FTR is not null
            union all
            select season_start, AwayTeam, FTAG, FTHG,
                   case FTR when 'A' then 3 when 'D' then 1 else 0 end
            from soccer.results where Div = 'E0' and FTR is not null
        )
        select 'EPL' as sport, season, team,
               count(*) as g,
               count(*) filter (where pts = 3) as w,
               count(*) filter (where pts = 0) as l,
               count(*) filter (where pts = 1) as t,
               sum(pts) / (3.0 * g) as win_pct,
               sum(gf) as scored, sum(ga) as allowed
        from team_games
        group by season, team
        having g >= 30
        """
    ).pl()
    return (soccer,)


@app.cell
def _(con, pl):
    # NBA only if the opt-in hoopR source has been fetched
    try:
        nba = con.sql(
            """
            select 'NBA' as sport, season, team_display_name as team,
                   count(*) as g,
                   count(*) filter (where team_winner) as w,
                   count(*) filter (where not team_winner) as l,
                   0 as t, w / g as win_pct,
                   sum(team_score) as scored, sum(opponent_team_score) as allowed
            from nba.team_box where season_type = 2
            group by season, team_display_name having g >= 60
            """
        ).pl()
    except Exception:
        nba = pl.DataFrame()
    return (nba,)


@app.cell
def _(mlb, nba, nfl, pl, soccer, wnba):
    frames = [f for f in (mlb, nfl, wnba, soccer, nba) if f.height]
    seasons = pl.concat(frames, how="vertical_relaxed").with_columns(
        pl.col("win_pct").cast(pl.Float64), pl.col("scored").cast(pl.Float64), pl.col("allowed").cast(pl.Float64)
    )
    seasons.group_by("sport", maintain_order=True).agg(
        pl.len().alias("team_seasons"), pl.col("g").mean().round(1).alias("mean_games"),
        (pl.col("scored") / pl.col("g")).mean().round(2).alias("scored_per_game"),
    )
    return (seasons,)


@app.cell
def _(np):
    def pythag(scored, allowed, k):
        return scored**k / (scored**k + allowed**k)

    def fit_k_grid(scored, allowed, win_pct, ks=np.linspace(1.0, 3.0, 401)):
        sse = np.array([np.sum((pythag(scored, allowed, k) - win_pct) ** 2) for k in ks])
        return float(ks[sse.argmin()]), sse

    def fit_k_log(w, l, scored, allowed):
        # log(w/l) = k * log(scored/allowed); least squares through the origin is a dot-product ratio.
        # Teams with zero wins or zero losses have no finite log-odds and are dropped (a handful, all pre-1920).
        mask = (w > 0) & (l > 0)
        x = np.log(scored[mask] / allowed[mask])
        y = np.log(w[mask] / l[mask])
        return float((x @ y) / (x @ x))

    return fit_k_grid, fit_k_log, pythag


@app.cell
def _(fit_k_grid, fit_k_log, pl, seasons):
    fits = []
    for (_sport,), _df in seasons.group_by("sport", maintain_order=True):
        _s, _a, _wp = _df["scored"].to_numpy(), _df["allowed"].to_numpy(), _df["win_pct"].to_numpy()
        _k_grid, _ = fit_k_grid(_s, _a, _wp)
        _k_log = fit_k_log(_df["w"].to_numpy().astype(float), _df["l"].to_numpy().astype(float), _s, _a)
        fits.append({"sport": _sport, "k_grid": _k_grid, "k_log": round(_k_log, 3)})
    fits = pl.DataFrame(fits)
    mlb_k = fits.filter(pl.col("sport") == "MLB")["k_grid"][0]
    assert 1.80 <= mlb_k <= 1.90, f"MLB k = {mlb_k:.3f}"
    fits
    return (fits,)


@app.cell
def _(fits, pl, seasons):
    resid = (
        seasons.join(fits.select("sport", "k_grid"), on="sport")
        .with_columns(
            (pl.col("scored").pow(pl.col("k_grid")) / (pl.col("scored").pow(pl.col("k_grid")) + pl.col("allowed").pow(pl.col("k_grid"))))
            .alias("pred")
        )
        .with_columns((pl.col("win_pct") - pl.col("pred")).alias("resid"))
    )
    spread = resid.group_by("sport", maintain_order=True).agg(
        pl.col("resid").std().round(4).alias("resid_sd"),
        pl.col("resid").mean().round(4).alias("resid_mean"),
        pl.col("g").mean().round(1).alias("games"),
        (1 - (pl.col("resid") ** 2).sum() / ((pl.col("win_pct") - pl.col("win_pct").mean()) ** 2).sum()).round(3).alias("r_squared"),
    ).sort("resid_sd", descending=True)
    spread
    return (resid,)


@app.cell
def _(plt, resid):
    sports = resid["sport"].unique(maintain_order=True).to_list()
    fig, axes = plt.subplots(1, len(sports), figsize=(3.2 * len(sports), 3), sharex=True)
    for _ax, _sport in zip(axes, sports):
        _r = resid.filter(resid["sport"] == _sport)["resid"].to_numpy()
        _ax.hist(_r, bins=40, color="steelblue")
        _ax.set_title(f"{_sport}  sd={_r.std():.3f}")
        _ax.axvline(0, color="gray", lw=1)
    axes[0].set_ylabel("team-seasons")
    fig.suptitle("Pythagorean residuals (actual minus predicted win%)")
    fig.tight_layout()
    fig
    return


@app.cell
def _(pl, resid):
    nxt = resid.select("sport", "team", (pl.col("season") - 1).alias("season"), pl.col("win_pct").alias("next_win_pct"))
    with_next = resid.join(nxt, on=["sport", "team", "season"], how="left")
    luck = (
        with_next.with_columns(pl.col("resid").rank(descending=True).over("sport").alias("lucky_rank"),
                               pl.col("resid").rank().over("sport").alias("unlucky_rank"))
        .filter((pl.col("lucky_rank") <= 5) | (pl.col("unlucky_rank") <= 5))
        .sort("sport", "resid", descending=[False, True])
        .select("sport", "season", "team", "g", "win_pct", "pred", "resid", "next_win_pct")
    )
    # the regression check: lucky teams' next-season win% drops toward their prediction on average
    summary = (
        luck.filter(pl.col("next_win_pct").is_not_null())
        .with_columns(pl.when(pl.col("resid") > 0).then(pl.lit("lucky")).otherwise(pl.lit("unlucky")).alias("group"))
        .group_by("sport", "group").agg(
            pl.col("win_pct").mean().round(3).alias("this_season"),
            pl.col("next_win_pct").mean().round(3).alias("next_season"),
            pl.len().alias("n"),
        ).sort("sport", "group")
    )
    summary
    return (luck,)


@app.cell
def _(luck):
    luck
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Reading the results

        - **k**: MLB lands near 1.83 by both methods. NFL is higher (roughly 2.5): a point in football
          is a smaller unit of scoring than a run, so the same point ratio implies more dominance.
          Basketball is higher still (around 14 in the classic formulation, because scores are so large
          that ratios are compressed near 1; the grid here caps at 3, so widen it for NBA/WNBA and see).
        - **Residual spread** tracks games per season. 17 NFL games cannot pin down a team's quality
          the way 162 can, so the sd of residuals is several times MLB's. The grid and log estimators
          agree closely except where there are team-seasons with extreme ratios.
        - **Regression to the mean**: lucky teams' next-season win% falls back toward what their run
          ratio predicted, and unlucky teams' rises. That is not a force acting on them; it is the
          luck not repeating.
        - **Soccer** fits worse because draws are a third outcome, three points for a win makes the
          objective asymmetric, and goals are rare (sequencing matters more). Models built for soccer
          (Poisson goals, stage 3 and 6) handle this directly.
        """
    )
    return


if __name__ == "__main__":
    app.run()
