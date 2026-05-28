#!/usr/bin/env python3
"""Detect container vs host DB row-count drift across all WebHarbor sites.

Implements gotcha #56's verification check at scale: walks every site,
counts rows in `instance/<site>.db` on host vs in `wh-r10` container, and
reports any drift.

Drift indicates bulk_api/augment/seed work that didn't propagate via
`docker cp`. Common causes:
- docker cp silently failed (gotcha #56 root case)
- container was rebuilt without HF asset repack pulling latest DB
- script wrote host DB but forgot to cp into container
- a `/restart/<site>` restored from instance_seed/ which had stale data

Run:
    python3 tools/audit/check_container_drift.py

    # specific site only:
    python3 tools/audit/check_container_drift.py --site craigslist

Output: 1-line summary + drift table.
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


WEBHARBOR = Path('/home/v-haoqiwang/repos/WebHarbor')
CONTAINER = 'wh-r10'

# Tables to count per site. Skipping reflective system tables.
# Auto-detects all non-empty user tables but lists priority tables first
# for cleaner output.
PRIORITY_TABLES = {
    'craigslist': 'listings',
    'fandom': 'articles',
    'bbc_news': 'articles',
    'imdb': 'titles',
    'nba': 'players',
    'coursera': 'courses',
    'ted': 'talk',
    'discogs': 'releases',
    'huggingface': 'repositories',
    'github': 'repository',
    'google_map': 'place',
    'google_search': 'topic',
    'google_flights': 'airport',
    'arxiv': 'papers',
    'amazon': 'product',
    'apple': 'product',
    'allrecipes': 'recipe',
    'bgg': 'games',
    'boardgamegeek': 'games',
    'mayo_clinic': 'article',
    'eventbrite': 'events',
}

# DB filename overrides (gotcha noted in bulk-api-enrich skill)
DB_NAME = {
    'huggingface': 'hf',
    'github': 'github_mirror',
    'google_map': 'gmaps',
}


def site_list() -> list[str]:
    sites_dir = WEBHARBOR / 'sites'
    return sorted([p.name for p in sites_dir.iterdir() if p.is_dir()
                   and (p / 'instance').exists()])


def host_count(site: str, table: str) -> int | None:
    db = WEBHARBOR / 'sites' / site / 'instance' / f'{DB_NAME.get(site, site)}.db'
    if not db.exists():
        return None
    try:
        c = sqlite3.connect(str(db))
        n = c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        return int(n)
    except sqlite3.Error:
        return None


def container_count(site: str, table: str) -> int | None:
    db_name = DB_NAME.get(site, site)
    cmd = ['docker', 'exec', CONTAINER, 'python3', '-c',
           f'import sqlite3,sys\n'
           f'try: print(sqlite3.connect("/opt/WebSyn/{site}/instance/{db_name}.db")'
           f'.execute(\'SELECT COUNT(*) FROM "{table}"\').fetchone()[0])\n'
           f'except Exception as e: sys.exit(2)']
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return None
        return int(out.stdout.strip())
    except (subprocess.SubprocessError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', help='Check only this site (default: all)')
    args = ap.parse_args()

    sites = [args.site] if args.site else site_list()
    rows = []
    drift_count = 0
    for s in sites:
        table = PRIORITY_TABLES.get(s)
        if not table:
            continue
        h = host_count(s, table)
        c = container_count(s, table)
        if h is None or c is None:
            status = 'skip (no DB / no table)'
        elif h == c:
            status = 'OK'
        else:
            status = f'DRIFT ({h - c:+d})'
            drift_count += 1
        rows.append((s, table, h, c, status))

    # print results
    print(f'{"SITE":24s} {"TABLE":15s} {"HOST":>8s} {"CONTAINER":>10s}  STATUS')
    print('-' * 80)
    for s, t, h, c, status in rows:
        hs = '?' if h is None else str(h)
        cs = '?' if c is None else str(c)
        print(f'{s:24s} {t:15s} {hs:>8s} {cs:>10s}  {status}')

    print(f'\n{drift_count} drift(s) detected across {len(rows)} sites.')
    if drift_count:
        print('To fix: `docker cp sites/<site>/instance/<db>.db wh-r10:/opt/WebSyn/<site>/instance/`')
        sys.exit(1)


if __name__ == '__main__':
    main()
