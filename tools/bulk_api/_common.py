"""Shared helpers for tools/bulk_api/ site fetchers.

Goals:
- Single place for UA, retry/backoff, slugify, idempotent UPSERT helpers.
- Per-site scripts should remain ~100 lines: import these helpers, build the
  candidate pool from the site's API, then INSERT-OR-IGNORE into the mirror DB.

Conventions every fetcher follows:
- Target DB:  /home/v-haoqiwang/repos/WebHarbor/sites/<site>/instance/<site>.db
  (NOT instance_seed/ — that's a snapshot we copy from at the end via
   normalize_seed_db_layout. Editing instance/ keeps reset-invariant
   intact because /reset/<site> recreates from instance_seed/ anyway.)
- Always periodic con.commit() every ~50 rows — subagent runs can stall and
  we want progress to land on disk.
- INSERT OR IGNORE on the canonical unique key (slug / tt_id / pageid / etc).
- Never touch the 4 benchmark users or any PINNED bcrypt rows.
- Never INSERT placeholder image URLs; leave NULL when API has no image —
  scrape-real-images Phase 5b will fill it from Wikipedia later.
"""
from __future__ import annotations
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

# Mozilla UA — required by wikipedia/upload CDNs and most public API gateways.
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

DEFAULT_TIMEOUT = 20
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.8


def fetch(url: str, *, headers: Optional[Dict[str, str]] = None,
          timeout: int = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> bytes:
    """GET with UA + retry/backoff. Returns raw bytes."""
    h = {'User-Agent': UA}
    if headers:
        h.update(headers)
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(DEFAULT_BACKOFF * (2 ** attempt))
    raise RuntimeError(f'fetch failed after {retries} retries: {url} :: {last_err}')


def fetch_json(url: str, **kw) -> Any:
    return json.loads(fetch(url, **kw))


def slugify(s: str, maxlen: int = 100) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')
    return s[:maxlen]


def open_db(site: str) -> sqlite3.Connection:
    """Open the live mirror DB. /reset/<site> rebuilds from instance_seed/."""
    p = Path(f'/home/v-haoqiwang/repos/WebHarbor/sites/{site}/instance/{site}.db')
    if not p.exists():
        raise FileNotFoundError(f'DB not found: {p} (is the container down?)')
    con = sqlite3.connect(str(p))
    con.execute('PRAGMA foreign_keys=ON')
    return con


def upsert_count(con: sqlite3.Connection, table: str) -> int:
    return con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def insert_or_ignore(con: sqlite3.Connection, table: str, row: Dict[str, Any]) -> Optional[int]:
    """INSERT OR IGNORE; returns lastrowid or None if dup."""
    cols = list(row.keys())
    placeholders = ','.join('?' * len(cols))
    quoted = ','.join(f'"{c}"' for c in cols)
    cur = con.execute(
        f'INSERT OR IGNORE INTO "{table}" ({quoted}) VALUES ({placeholders})',
        [row[c] for c in cols],
    )
    return cur.lastrowid if cur.rowcount else None


def periodic_commit(con: sqlite3.Connection, added: int, every: int = 50) -> None:
    if added and added % every == 0:
        con.commit()


# ---------- diversity gate (call at end of each script) ---------- #

def assert_image_diversity(con: sqlite3.Connection, table: str, column: str,
                            threshold: float = 0.05, min_rows: int = 15) -> None:
    """Reject seeds where one image URL covers >5% of rows.

    Mirrors scrape-real-images Phase 5c. Call at end of bulk_api fetcher
    so we fail loudly instead of shipping silently-duplicated placeholders.
    """
    rows = [r[0] for r in con.execute(
        f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL AND "{column}" != ""'
    )]
    if len(rows) < min_rows:
        return
    import collections
    counter = collections.Counter(rows)
    top_url, top_n = counter.most_common(1)[0]
    ratio = top_n / len(rows)
    if ratio >= threshold:
        raise AssertionError(
            f'{table}.{column} diversity gate failed: {top_n}/{len(rows)} '
            f'= {ratio:.1%} share goes to {top_url!r} (threshold {threshold:.0%})'
        )


# ---------- pagination helpers ---------- #

def paged(start_urls: Iterable[str], next_key: str = 'next',
          sleep: float = 0.3) -> Iterable[Any]:
    """Walk a JSON API that returns {'results': [...], 'next': 'url'}."""
    queue = list(start_urls)
    seen = set()
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            payload = fetch_json(url)
        except Exception:
            continue
        yield payload
        nxt = payload.get(next_key) if isinstance(payload, dict) else None
        if nxt:
            queue.append(nxt)
        time.sleep(sleep)
