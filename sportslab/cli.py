"""Command line entry point: ``sportslab archive ...``, ``sportslab catalog ...``, ``sportslab sql``."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table as RichTable

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Local sports data archive and learning stages.")
archive_app = typer.Typer(no_args_is_help=True, help="Fetch raw data and normalize it to parquet.")
catalog_app = typer.Typer(no_args_is_help=True, help="DuckDB views over the parquet tree.")
app.add_typer(archive_app, name="archive")
app.add_typer(catalog_app, name="catalog")

out = Console()


def _select(names: list[str], all_: bool):
    from sportslab.archive import registry

    if all_:
        return registry.all_sources(include_opt_in=False) + [registry.get(n) for n in names if registry.SOURCES[n].opt_in]
    if not names:
        raise typer.BadParameter("name one or more sources, or pass --all")
    return [registry.get(n) for n in names]


@archive_app.command("list")
def archive_list():
    """Show the known sources."""
    from sportslab.archive import registry

    t = RichTable("source", "sport", "opt-in", "tables", "description")
    for cls in registry.SOURCES.values():
        t.add_row(cls.name, cls.sport, "yes" if cls.opt_in else "", str(len(cls.tables)), cls.description)
    out.print(t)


@archive_app.command()
def fetch(
    names: list[str] = typer.Argument(None, help="source names; see `archive list`"),
    all_: bool = typer.Option(False, "--all", help="every source that is not opt-in"),
    force: bool = typer.Option(False, "--force", help="re-download even if unchanged"),
):
    """Download raw files into data/raw/<source>/<today>/ with a provenance manifest."""
    for s in _select(names or [], all_):
        s.fetch(force=force)


@archive_app.command()
def normalize(
    names: list[str] = typer.Argument(None),
    all_: bool = typer.Option(False, "--all"),
):
    """Build parquet tables from the newest raw fetch of each source."""
    for s in _select(names or [], all_):
        rows = s.normalize()
        for table, n in rows.items():
            out.print(f"  {table}: {n:,} rows")


@archive_app.command()
def status():
    """Last fetch date and row counts per table."""
    from sportslab.archive import registry

    t = RichTable("source", "last fetch", "table", "rows")
    for s in registry.all_sources(include_opt_in=True):
        st = s.status()
        first = True
        for table, n in st["rows"].items():
            t.add_row(s.name if first else "", (st["last_fetch"] or "-") if first else "",
                      table, f"{n:,}" if n is not None else "-")
            first = False
    out.print(t)


@catalog_app.command("build")
def catalog_build():
    """(Re)create data/sportslab.duckdb with a view per parquet table."""
    from sportslab import catalog

    views = catalog.build()
    out.print(f"{len(views)} views in {catalog.DB_PATH}")
    for v in views:
        out.print(f"  {v}")


@app.command()
def sql(query: str, limit: int = typer.Option(50, help="rows to print")):
    """Run a SQL query against the catalog and print the result."""
    from sportslab import catalog

    con = catalog.connect()
    rel = con.sql(query)
    if rel is None:
        return
    df = rel.limit(limit).pl()
    if df.height == 0:
        out.print("[dim]no rows[/dim]")
        return
    t = RichTable(*df.columns)
    for row in df.iter_rows():
        t.add_row(*["" if v is None else str(v) for v in row])
    out.print(t)
    total = rel.aggregate("count(*)").fetchone()[0]
    if total > limit:
        out.print(f"[dim]{total:,} rows, showing {limit}; use --limit[/dim]")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
