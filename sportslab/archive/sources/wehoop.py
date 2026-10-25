"""WNBA play-by-play and box scores, 2002-, from sportsdataverse (wehoop) releases."""

from sportslab.archive.base import Table
from sportslab.archive.sources.sportsdataverse import SportsdataverseSource


class WehoopWNBA(SportsdataverseSource):
    name = "wehoop"
    sport = "wnba"
    schema = "wnba"
    description = "WNBA play-by-play, team and player box scores, schedules (ESPN via wehoop)"
    homepage = "https://github.com/sportsdataverse/wehoop-wnba-data"
    license = "Package MIT; data is ESPN's. Research use; do not redistribute."
    attribution = "WNBA data from sportsdataverse/wehoop (ESPN-sourced)."
    release_tags = {
        "pbp": "espn_wnba_pbp",
        "team_box": "espn_wnba_team_boxscores",
        "player_box": "espn_wnba_player_boxscores",
        "schedules": "espn_wnba_schedules",
    }
    tables = (
        Table("wnba", "pbp", "play-by-play, one row per event, 2002-; partitioned by season"),
        Table("wnba", "team_box", "team box scores per game"),
        Table("wnba", "player_box", "player box scores per game"),
        Table("wnba", "schedules", "games and results"),
    )
