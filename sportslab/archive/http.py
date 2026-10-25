"""Polite, resumable-enough HTTP downloads with retries."""

from __future__ import annotations

import time
from pathlib import Path

import httpx


def is_missing(status: int) -> bool:
    """A status that means 'this URL has nothing for us' rather than 'try again later'."""
    return 300 <= status < 500 and status not in (408, 425, 429)


USER_AGENT = "sportslab/0.1 (personal research archive; https://github.com/justizin/sportslab)"
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=30.0)


def client(**kwargs) -> httpx.Client:
    headers = {"User-Agent": USER_AGENT}
    headers.update(kwargs.pop("headers", {}))
    # Bind to 0.0.0.0 to force IPv4: on hosts without a working IPv6 route, every AAAA record
    # costs a full connect timeout before falling back (Box took 30 s per hop).
    transport = kwargs.pop("transport", httpx.HTTPTransport(local_address="0.0.0.0", retries=1))
    return httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT, headers=headers, transport=transport, **kwargs)


def head_size(url: str, c: httpx.Client | None = None) -> int | None:
    """Content-Length from a HEAD request, or None if the server does not say."""
    own = c is None
    c = c or client()
    try:
        r = c.head(url)
        if r.status_code >= 400:
            return None
        cl = r.headers.get("content-length")
        return int(cl) if cl else None
    except httpx.HTTPError:
        return None
    finally:
        if own:
            c.close()


def download(
    url: str,
    dest: Path,
    c: httpx.Client | None = None,
    retries: int = 4,
    backoff: float = 2.0,
    min_bytes: int = 1,
) -> Path:
    """Stream ``url`` to ``dest`` atomically (via ``dest.part``), retrying on transient errors.

    Raises on a 4xx that is not worth retrying so the caller can decide whether a missing
    file is expected (e.g. a league-season that does not exist on football-data.co.uk).
    """
    own = c is None
    c = c or client()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        for attempt in range(retries):
            try:
                with c.stream("GET", url) as r:
                    if is_missing(r.status_code):
                        raise httpx.HTTPStatusError(
                            f"{r.status_code} for {url}", request=r.request, response=r
                        )
                    r.raise_for_status()
                    with part.open("wb") as fh:
                        for chunk in r.iter_bytes(1 << 20):
                            fh.write(chunk)
                if part.stat().st_size < min_bytes:
                    raise OSError(f"downloaded {part.stat().st_size} bytes from {url}")
                part.replace(dest)
                return dest
            except httpx.HTTPStatusError as e:
                if is_missing(e.response.status_code):
                    part.unlink(missing_ok=True)
                    raise
                if attempt == retries - 1:
                    raise
            except (httpx.HTTPError, OSError):
                if attempt == retries - 1:
                    raise
            time.sleep(backoff * (2**attempt))
        raise RuntimeError("unreachable")
    finally:
        if own:
            c.close()
