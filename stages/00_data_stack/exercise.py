import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        r"""
        # Stage 0: the data stack

        A worked example. Read every cell, change something, and watch the dependents re-run.
        The archive is queried through DuckDB; results come back as polars or pandas frames.
        """
    )
    return (mo,)


@app.cell
def _():
    import matplotlib.pyplot as plt
    import polars as pl

    from sportslab import catalog

    con = catalog.connect()
    return con, pl, plt


@app.cell
def _(con, mo):
    tables = con.sql(
        "select table_schema, table_name from information_schema.tables order by 1, 2"
    ).pl()
    mo.md(f"**Tables in the catalog**\n\n{mo.as_html(tables)}")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 1. MLB standings from game logs

        `mlb.gamelog` has one row per game with `v_name`, `h_name`, `v_score`, `h_score`.
        Each game contributes to two team-rows, so we stack a "visitor view" and a "home view"
        with `UNION ALL`, then aggregate. The table also holds postseason and All-Star games
        (`game_type`), which is the first thing that went wrong when this notebook was written:
        without the filter, 12 playoff teams had too many games and two "teams" were the All-Star squads.
        """
    )
    return


@app.cell
def _(con):
    standings_sql = """
    with team_games as (
        select season, v_name as team, v_score as rs, h_score as ra from mlb.gamelog where game_type = 'regular'
        union all
        select season, h_name as team, h_score as rs, v_score as ra from mlb.gamelog where game_type = 'regular'
    )
    select
        team,
        count(*)                              as g,
        sum(case when rs > ra then 1 else 0 end) as w,
        sum(case when rs < ra then 1 else 0 end) as l,
        sum(rs) as rs,
        sum(ra) as ra,
        round(w / (w + l), 3) as win_pct
    from team_games
    where season = 2025
    group by team
    order by win_pct desc
    """
    standings_2025 = con.sql(standings_sql).pl()
    standings_2025
    return (standings_2025,)


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 2. Cross-check against Lahman

        Lahman's `Teams` table carries `teamIDretro`, the Retrosheet code, so the join is exact.
        """
    )
    return


@app.cell
def _(con, pl, standings_2025):
    lahman_2025 = con.sql(
        """
        select teamIDretro as team, name, lgID, divID, W as w_lahman, L as l_lahman, R as r_lahman, RA as ra_lahman
        from mlb.teams where yearID = 2025
        """
    ).pl()
    check = standings_2025.join(lahman_2025, on="team", how="full", coalesce=True).with_columns(
        (pl.col("w") == pl.col("w_lahman")).alias("w_match"),
        (pl.col("l") == pl.col("l_lahman")).alias("l_match"),
    )
    mismatches = check.filter(~pl.col("w_match") | ~pl.col("l_match") | pl.col("name").is_null())
    print(f"{check.height} teams, {mismatches.height} mismatches")
    mismatches
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 3. NFL 2024 regular season

        `nfl.schedules` is also one row per game. Ties count as half a win here.
        """
    )
    return


@app.cell
def _(con):
    nfl_2024 = con.sql(
        """
        with team_games as (
            select season, home_team as team, home_score as pf, away_score as pa from nfl.schedules
            where game_type = 'REG'
            union all
            select season, away_team as team, away_score as pf, home_score as pa from nfl.schedules
            where game_type = 'REG'
        )
        select team,
               count(*) as g,
               sum(case when pf > pa then 1 else 0 end) as w,
               sum(case when pf < pa then 1 else 0 end) as l,
               sum(case when pf = pa then 1 else 0 end) as t,
               (w + 0.5 * t) / g as win_pct,
               sum(pf) as points_for, sum(pa) as points_against
        from team_games
        where season = 2024
        group by team
        order by win_pct desc, points_for - points_against desc
        """
    ).pl()
    nfl_2024
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 4. Runs scored vs runs allowed, 1901 to now

        Every MLB team-season as one dot. The diagonal is .500. The spread around it is what
        stage 1 tries to explain.
        """
    )
    return


@app.cell
def _(con, plt):
    rs_ra = con.sql(
        """
        select yearID, teamID, W, L, R, RA, W / (W + L) as win_pct
        from mlb.teams where yearID >= 1901 and G >= 100
        """
    ).pl()
    fig, ax = plt.subplots(figsize=(7, 7))
    sc = ax.scatter(rs_ra["RA"], rs_ra["R"], c=rs_ra["win_pct"], s=8, cmap="coolwarm", vmin=0.3, vmax=0.7)
    lim = [min(rs_ra["RA"].min(), rs_ra["R"].min()), max(rs_ra["RA"].max(), rs_ra["R"].max())]
    ax.plot(lim, lim, color="gray", lw=1)
    ax.set_xlabel("runs allowed")
    ax.set_ylabel("runs scored")
    ax.set_title(f"MLB team-seasons since 1901 (n={rs_ra.height})")
    fig.colorbar(sc, label="win %")
    fig
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Before you leave

        - Change `season = 2025` to a strike year (1981, 1994) and see what breaks in the acceptance check.
        - Rewrite cell 1 with polars instead of SQL (`pl.concat`, `group_by`, `agg`). Same answer?
        - Write `docs/notes/00_data_stack.md`: one paragraph on what the two sources disagreed about, if anything.
        """
    )
    return


if __name__ == "__main__":
    app.run()
