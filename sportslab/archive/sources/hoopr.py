"""NBA play-by-play, box scores and shots, 2002-, from sportsdataverse (hoopR) releases."""

from sportslab.archive.base import Table
from sportslab.archive.sources.sportsdataverse import SportsdataverseSource


class HoopRNBA(SportsdataverseSource):
    name = "hoopr"
    sport = "nba"
    schema = "nba"
    opt_in = True  # ~450 MB of play-by-play; named explicitly rather than pulled by --all
    description = "NBA play-by-play, team and player box scores, schedules (ESPN via hoopR)"
    homepage = "https://github.com/sportsdataverse/hoopR-nba-data"
    license = "Package MIT; data is ESPN's. Research use; do not redistribute."
    attribution = "NBA data from sportsdataverse/hoopR (ESPN-sourced)."
    release_tags = {
        "pbp": "espn_nba_pbp",
        "team_box": "espn_nba_team_boxscores",
        "player_box": "espn_nba_player_boxscores",
        "schedules": "espn_nba_schedules",
    }
    tables = (
        Table("nba", "pbp", "play-by-play, one row per event, 2002-; partitioned by season"),
        Table("nba", "team_box", "team box scores per game"),
        Table("nba", "player_box", "player box scores per game"),
        Table("nba", "schedules", "games and results"),
    )
