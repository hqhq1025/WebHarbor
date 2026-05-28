#!/usr/bin/env python3
"""Fill NULL image columns from harvest_spider's `_image_urls.jsonl`.

After ``tools/harvest/augment_seed_from_extruct.py`` ingests Movie/Person
JSON-LD into ``imdb.db`` and ``nba.db``, a handful of image columns may still
be NULL because the schema.org payload omitted them or the row was synthetic
to begin with. This script provides a second-pass fallback that consults the
already-on-disk image URL inventory the spider emitted (one JSONL row per
``<img>``/srcset URL found while crawling).

Strategy (per task spec):

* Read ``<snapshot-root>/<site>/_image_urls.jsonl``.
* Group URLs by the ``page`` field — the spider records which route directory
  the URL came from. For imdb that is ``tt<digits>_<hash>`` (per-title page)
  and for nba it is ``<slug>_<hash>`` (per-player or per-team page).
* For each entity row whose image column is currently NULL/empty:
    - For imdb titles: prefer the best ``m.media-amazon.com/images/M/MV5B...``
      poster from the matching ``tt_id`` page (largest variant, ending in
      ``_V1_.jpg`` or stripped of size suffix).
    - For nba players: prefer ``cdn.nba.com/headshots/nba/.../1040x760/...png``
      from the matching player-slug page.
    - For nba teams: prefer ``cdn.nba.com/logos/nba/<nba_team_id>/...`` from
      any page where alt text mentions the team.
* Update ONLY rows where the current column value is NULL or empty. Never
  overwrite an existing URL (especially placeholder mirror paths — those are
  served by the site's own static handler and are valid).
* Diversity gate: per the project's scrape-real-images rule, if the single
  most-repeated URL covers >5% of all updates, abort that site (treat as a
  default avatar leak) — except when only one row is being updated, in which
  case 100% is allowed by definition.
* No fabrication: rows that don't match any harvested URL stay NULL.

Run::

    python3 tools/bulk_api/harvest_image_backfill.py \
        --site all \
        --snapshot-root /home/v-haoqiwang/webvoyager-analysis/real_components/snapshots \
        --copy-to-seed

``--copy-to-seed`` mirrors the augment tool: after the in-place UPDATE on
``instance/<site>.db``, copy the file over ``instance_seed/<site>.db`` so that
the byte-identical /restart endpoint preserves the new state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
SITES_ROOT = REPO_ROOT / 'sites'

# Per the project rule (.claude/skills/scrape-real-images), if a single URL
# dominates >5% of the updates, that's a default-avatar leak — abort. When
# only one row is being updated, this gate doesn't apply (top_n must be > 1).
DIVERSITY_PCT = 5.0


# ---------------- helpers ----------------

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _copy_to_seed(site: str, db_name: str) -> None:
    src = SITES_ROOT / site / 'instance' / db_name
    dst = SITES_ROOT / site / 'instance_seed' / db_name
    shutil.copyfile(src, dst)
    print(f'  copied {src.name} -> instance_seed; md5={_md5(dst)}')


def _load_image_urls(jsonl: Path) -> dict[str, list[dict]]:
    """Group rows by `page`. Each row = {url, alt, kind, ...}."""
    out: dict[str, list[dict]] = defaultdict(list)
    if not jsonl.is_file():
        return out
    with jsonl.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            page = row.get('page')
            url = row.get('url')
            if isinstance(page, str) and isinstance(url, str):
                out[page].append(row)
    return out


def _diversity_ok(urls: Iterable[str], label: str) -> bool:
    """Reject if the single most-common URL covers >DIVERSITY_PCT of the set.

    Single-row updates always pass (top_n must be > 1 to count as a violation,
    per the May-2026 update to scrape-real-images).
    """
    urls = list(urls)
    if len(urls) <= 1:
        return True
    counts = Counter(urls)
    top_url, top_n = counts.most_common(1)[0]
    if top_n <= 1:
        return True
    pct = 100.0 * top_n / len(urls)
    if pct > DIVERSITY_PCT:
        print(f'  ABORT {label}: top URL covers {top_n}/{len(urls)} '
              f'({pct:.1f}%) > {DIVERSITY_PCT}% gate', file=sys.stderr)
        print(f'  offending URL: {top_url}', file=sys.stderr)
        return False
    return True


# ---------------- imdb ----------------

def _best_imdb_poster(urls: list[dict]) -> str | None:
    """Pick the best MV5B poster URL from a page's img-src/img-srcset rows.

    Prefer: full ``m.media-amazon.com/images/M/MV5B...._V1_.jpg`` (no crop/size
    suffix) > ``..._V1_FMjpg_UX1000_.jpg`` family > anything else.
    """
    by_quality: list[tuple[int, str]] = []
    for r in urls:
        u = r.get('url') or ''
        if 'm.media-amazon.com/images/M/MV5B' not in u:
            continue
        # Drop trailing thumbnail / crop suffixes (these point at low-res
        # variants — but the canonical _V1_.jpg base is highest quality).
        if u.endswith('_V1_.jpg'):
            score = 100
        elif '_V1_FMjpg_' in u and u.endswith('.jpg'):
            score = 80
        elif '_V1_' in u and u.endswith('.jpg'):
            score = 50
        else:
            continue
        by_quality.append((score, u))
    if not by_quality:
        return None
    by_quality.sort(key=lambda t: -t[0])
    return by_quality[0][1]


def backfill_imdb(snapshot_root: Path) -> int:
    db = SITES_ROOT / 'imdb' / 'instance' / 'imdb.db'
    jsonl = snapshot_root / 'imdb_com' / '_image_urls.jsonl'
    if not db.is_file():
        print(f'  no imdb db at {db}; skip')
        return 0
    if not jsonl.is_file():
        print(f'  no {jsonl}; skip')
        return 0
    pages = _load_image_urls(jsonl)
    print(f'  loaded {sum(len(v) for v in pages.values())} image URLs across '
          f'{len(pages)} pages')

    # Build tt_id -> [candidate URLs] from pages whose name starts with tt<digits>_
    tt_to_urls: dict[str, list[dict]] = defaultdict(list)
    for page, rows in pages.items():
        m = re.match(r'^(tt\d+)_', page)
        if m:
            tt_to_urls[m.group(1)].extend(rows)

    conn = sqlite3.connect(db)
    try:
        # titles.poster_path
        null_titles = conn.execute(
            "SELECT tt_id FROM titles WHERE poster_path IS NULL OR poster_path=''"
        ).fetchall()
        title_picks: dict[str, str] = {}
        for (tt_id,) in null_titles:
            cand = tt_to_urls.get(tt_id)
            if not cand:
                continue
            best = _best_imdb_poster(cand)
            if best:
                title_picks[tt_id] = best
        if not _diversity_ok(title_picks.values(), 'imdb.titles.poster_path'):
            return 0

        n_titles = 0
        for tt_id, url in title_picks.items():
            cur = conn.execute(
                "UPDATE titles SET poster_path=? WHERE tt_id=? "
                "AND (poster_path IS NULL OR poster_path='')",
                (url, tt_id))
            n_titles += cur.rowcount
        conn.commit()
        print(f'  imdb.titles.poster_path: {n_titles} filled '
              f'(NULL pool was {len(null_titles)})')
        return n_titles
    finally:
        conn.close()


# ---------------- nba ----------------

def _best_nba_headshot(urls: list[dict]) -> str | None:
    for r in urls:
        u = r.get('url') or ''
        if 'cdn.nba.com/headshots/nba' in u and u.endswith('.png'):
            # The 1040x760 variant is the largest official headshot.
            if '1040x760' in u:
                return u
    # Fallback: any headshot URL on the page
    for r in urls:
        u = r.get('url') or ''
        if 'cdn.nba.com/headshots/nba' in u:
            return u
    return None


def _best_nba_team_logo(urls: list[dict], team_name: str) -> str | None:
    name_lc = team_name.lower()
    for r in urls:
        u = r.get('url') or ''
        alt = (r.get('alt') or '').lower()
        if 'cdn.nba.com/logos/nba/' in u and name_lc in alt:
            return u
    return None


def backfill_nba(snapshot_root: Path) -> int:
    db = SITES_ROOT / 'nba' / 'instance' / 'nba.db'
    jsonl = snapshot_root / 'nba_com' / '_image_urls.jsonl'
    if not db.is_file():
        print(f'  no nba db at {db}; skip')
        return 0
    if not jsonl.is_file():
        print(f'  no {jsonl}; skip')
        return 0
    pages = _load_image_urls(jsonl)
    print(f'  loaded {sum(len(v) for v in pages.values())} image URLs across '
          f'{len(pages)} pages')

    # Player pages: <slug>_<hash> (slug never contains '_')
    slug_to_urls: dict[str, list[dict]] = defaultdict(list)
    for page, rows in pages.items():
        m = re.match(r'^([a-z][a-z0-9-]*)_[a-f0-9]+$', page)
        if m:
            slug_to_urls[m.group(1)].extend(rows)
    # Team pages: numeric NBA team_id prefix
    team_id_to_urls: dict[str, list[dict]] = defaultdict(list)
    for page, rows in pages.items():
        m = re.match(r'^(\d{10})_[a-f0-9]+$', page)
        if m:
            team_id_to_urls[m.group(1)].extend(rows)

    conn = sqlite3.connect(db)
    total = 0
    try:
        # players.image
        null_players = conn.execute(
            "SELECT slug, name FROM players WHERE image IS NULL OR image=''"
        ).fetchall()
        player_picks: dict[str, str] = {}
        for slug, _name in null_players:
            cand = slug_to_urls.get(slug)
            if not cand:
                continue
            best = _best_nba_headshot(cand)
            if best:
                player_picks[slug] = best
        if not _diversity_ok(player_picks.values(), 'nba.players.image'):
            return total

        n_players = 0
        for slug, url in player_picks.items():
            cur = conn.execute(
                "UPDATE players SET image=? WHERE slug=? "
                "AND (image IS NULL OR image='')",
                (url, slug))
            n_players += cur.rowcount
        total += n_players
        print(f'  nba.players.image: {n_players} filled '
              f'(NULL pool was {len(null_players)})')

        # teams.logo
        null_teams = conn.execute(
            "SELECT slug, name FROM teams WHERE logo IS NULL OR logo=''"
        ).fetchall()
        team_picks: dict[str, str] = {}
        # We don't know the NBA team_id directly, so scan all team pages.
        for slug, name in null_teams:
            for _tid, cand in team_id_to_urls.items():
                best = _best_nba_team_logo(cand, name)
                if best:
                    team_picks[slug] = best
                    break
        if not _diversity_ok(team_picks.values(), 'nba.teams.logo'):
            return total
        n_teams = 0
        for slug, url in team_picks.items():
            cur = conn.execute(
                "UPDATE teams SET logo=? WHERE slug=? "
                "AND (logo IS NULL OR logo='')",
                (url, slug))
            n_teams += cur.rowcount
        total += n_teams
        print(f'  nba.teams.logo: {n_teams} filled '
              f'(NULL pool was {len(null_teams)})')

        conn.commit()
        return total
    finally:
        conn.close()


# ---------------- driver ----------------

SITES = {
    'imdb': ('imdb.db', backfill_imdb),
    'nba':  ('nba.db',  backfill_nba),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--site', choices=list(SITES) + ['all'], default='all')
    p.add_argument('--snapshot-root', required=True,
                   help='Directory containing <site>_com/_image_urls.jsonl')
    p.add_argument('--copy-to-seed', action='store_true',
                   help='After write, cp instance/<db> -> instance_seed/<db>.')
    args = p.parse_args()
    snapshot_root = Path(args.snapshot_root)
    targets = list(SITES) if args.site == 'all' else [args.site]
    for site in targets:
        db_name, fn = SITES[site]
        print(f'== {site} ==')
        n = fn(snapshot_root)
        if args.copy_to_seed and n > 0:
            _copy_to_seed(site, db_name)


if __name__ == '__main__':
    main()
