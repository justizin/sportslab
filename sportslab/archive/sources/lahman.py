"""Lahman Baseball Database, 1871-, as hosted by SABR on Box.

SABR publishes the CSV edition as a Box shared folder. Box offers no bulk download for
anonymous users, but each file in a shared folder can be fetched by id, and the share page
embeds the folder listing twenty items at a time. We walk the pages, then fetch each CSV.

License: the SABR page states no formal license; the Negro Leagues portion is licensed from
Seamheads.com. Earlier editions were CC BY-SA 3.0. Treat as attribution-required, personal use.
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import polars as pl

from sportslab.archive.base import Source, Table, console, write_table

PAGE = "https://sabr.org/lahman-database/"
SHARE = "y1prhc795jk8zvmelfd3jq7tl389y6cd"  # the "Comma-delimited version" folder, 1871-2025 edition
SHARE_URL = f"https://sabr.app.box.com/s/{SHARE}"
DOWNLOAD = "https://sabr.app.box.com/index.php?rm=box_download_shared_file&shared_name={share}&file_id={fid}"

ITEM_RE = re.compile(r'"typedID":"(f_\d+)"[^}]*?"name":"([^"]+)","itemSize":(\d+)')

TABLE_DOCS = {
    "People": "player biographical master (playerID, names, birth/death, debut)",
    "Batting": "batting by player-season-stint",
    "Pitching": "pitching by player-season-stint",
    "Fielding": "fielding by player-season-stint-position",
    "FieldingOF": "outfield games by position, pre-1956",
    "FieldingOFsplit": "outfield games by position, 1954-",
    "Appearances": "games played by position per player-season",
    "Teams": "team season totals, standings, park, attendance",
    "TeamsFranchises": "franchise master",
    "TeamsHalf": "split-season standings (1981)",
    "Parks": "park master",
    "HomeGames": "home games per team-park-season",
    "Managers": "manager season records",
    "ManagersHalf": "split-season manager records",
    "AllstarFull": "all-star game appearances",
    "AwardsPlayers": "player awards",
    "AwardsManagers": "manager awards",
    "AwardsSharePlayers": "player award voting shares",
    "AwardsShareManagers": "manager award voting shares",
    "HallOfFame": "Hall of Fame voting",
    "BattingPost": "postseason batting",
    "PitchingPost": "postseason pitching",
    "FieldingPost": "postseason fielding",
    "SeriesPost": "postseason series results",
    "Salaries": "player salaries, 1985-2016",
    "Schools": "school master",
    "CollegePlaying": "player college seasons",
}


class Lahman(Source):
    name = "lahman"
    sport = "mlb"
    description = "Lahman Baseball Database (SABR edition): season-level batting, pitching, fielding, teams, 1871-"
    homepage = PAGE
    license = "No formal license stated by SABR; Negro Leagues data licensed from Seamheads.com. Attribution required."
    attribution = "Lahman Baseball Database, Sean Lahman / SABR (https://sabr.org/lahman-database/); Negro Leagues data from Seamheads.com."
    tables = tuple(Table("mlb", n.lower(), d) for n, d in TABLE_DOCS.items())

    def fetch_into(self, ctx, c: httpx.Client) -> None:
        items = list_share(c)
        if len(items) < 20:
            raise RuntimeError(f"Box share listing returned only {len(items)} items; page layout may have changed")
        for fid, fname, size in items:
            ctx.get(DOWNLOAD.format(share=SHARE, fid=fid), fname, c, remote_size=size)

    def build_tables(self, raw: Path) -> dict[str, int]:
        rows = {}
        by_name = {t.name: t for t in self.tables}
        for f in sorted(raw.glob("*.csv")):
            t = by_name.get(f.stem.lower())
            if t is None:
                t = Table("mlb", f.stem.lower(), "")
                console.print(f"[yellow]lahman: table {f.stem} not in TABLE_DOCS; writing anyway[/yellow]")
            df = pl.read_csv(f, infer_schema_length=None, encoding="utf8-lossy", null_values=[""])
            rows[t.qualified] = write_table(t, df)
        return rows


def list_share(c: httpx.Client, max_pages: int = 10) -> list[tuple[str, str, int]]:
    """Walk the Box share page listing and return (file_id, name, bytes) for every file."""
    seen: dict[str, tuple[str, str, int]] = {}
    for page in range(1, max_pages + 1):
        r = c.get(SHARE_URL, params={"page": page})
        r.raise_for_status()
        found = ITEM_RE.findall(r.text)
        new = [(fid, name, int(size)) for fid, name, size in found if fid not in seen]
        if not new:
            break
        for item in new:
            seen[item[0]] = item
    return sorted(seen.values(), key=lambda x: x[1])
