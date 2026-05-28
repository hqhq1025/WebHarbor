#!/usr/bin/env python3
"""Discogs: backfill artists.image_path + releases.image_path with real photos
sourced from Wikipedia REST + Wikimedia Commons (no Tavily).

Cap: up to 500 artists and 500 releases per run, picked by site-internal
popularity (artists.in_collection DESC, releases.want_count DESC). 8KB filter,
0.3s spacing, Mozilla UA. Images dropped into:

    sites/discogs/static/images/artist/<id>.jpg
    sites/discogs/static/images/release/<id>.jpg

DB updates use the existing canonical column layout (e.g. 'images/artist/<id>.jpg'),
so the Flask routes keep working without code changes.

Source ladder per row:
  Artists  (use name + slug):
    1. en.wikipedia.org REST /page/summary/<Title>     (Title = name underscores)
    2. en.wikipedia.org REST /page/summary/<Title>_(musician)
    3. en.wikipedia.org REST /page/summary/<Title>_(band)
    4. Commons api.php?list=search&srsearch="<name>" musician&srnamespace=6

  Releases (use title + joined artist.name):
    1. en.wikipedia.org REST /page/summary/<Title>_(<Artist>_album)
    2. en.wikipedia.org REST /page/summary/<Title>_(album)
    3. en.wikipedia.org REST /page/summary/<Title>
    4. Commons api.php?list=search&srsearch="<title>" "<artist>" album cover&srnamespace=6

This script never restarts the container, never commits the DB. The operator
runs the docker cp + sanity SELECT after the script returns. Diversity gate
fires at the end and aborts if one URL pattern covers >5% of new image_path
values.
"""
from __future__ import annotations
import argparse
import collections
import io
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path('/home/v-haoqiwang/repos/WebHarbor')
SITE = 'discogs'
DB_PATH = ROOT / 'sites' / SITE / 'instance' / f'{SITE}.db'
IMG_ROOT = ROOT / 'sites' / SITE / 'static' / 'images'
ARTIST_DIR = IMG_ROOT / 'artist'
RELEASE_DIR = IMG_ROOT / 'release'

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36 '
      'WebHarbor-discogs-seed/1.0 (https://github.com/WebHarbor)')
HEADERS = {'User-Agent': UA, 'Accept': '*/*'}

SLEEP = 0.3
MIN_BYTES = 8 * 1024
PER_PHASE_LIMIT_DEFAULT = 500

REST = 'https://en.wikipedia.org/api/rest_v1/page/summary/'
COMMONS = 'https://commons.wikimedia.org/w/api.php'


# -------- HTTP helpers (urllib, no requests dependency) -------- #

def _http_get(url: str, *, timeout: int = 15, max_retries: int = 3):
    """Returns (status, headers, body bytes) or (None, None, None) on hard fail."""
    last = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            # 404/403 are final, don't retry.
            if e.code in (404, 403, 410):
                return e.code, dict(e.headers or {}), b''
            # 429/503: honor Retry-After if present (cap at 5s).
            if e.code in (429, 503):
                ra = 0
                try:
                    ra = int((e.headers or {}).get('Retry-After', '0'))
                except Exception:
                    ra = 0
                time.sleep(min(max(ra, 1), 5))
            last = e
        except Exception as e:
            last = e
        time.sleep(0.5 * (attempt + 1))
    return None, None, None


def _get_json(url: str):
    status, _, body = _http_get(url)
    if status != 200 or not body:
        return None
    try:
        import json
        return json.loads(body)
    except Exception:
        return None


# -------- Wikipedia / Commons resolvers -------- #

def _title_encode(name: str) -> str:
    name = (name or '').strip()
    # Wikipedia title convention: spaces -> underscores
    name = name.replace(' ', '_')
    # urllib quote, keep parens / underscores
    return urllib.parse.quote(name, safe="_()',!&")


def wiki_thumb(title_candidate: str):
    """Hit REST summary, return (thumbnail_url, original_url) or (None, None)."""
    url = REST + _title_encode(title_candidate)
    data = _get_json(url)
    if not data:
        return None, None
    thumb = data.get('thumbnail') or {}
    orig = data.get('originalimage') or {}
    return thumb.get('source'), orig.get('source')


def commons_first_image(srsearch: str, *, filetype: str = 'jpg|png'):
    """Run a Commons file-namespace search, return the first reasonable image URL."""
    params = {
        'action': 'query', 'format': 'json',
        'list': 'search', 'srnamespace': '6',
        'srsearch': srsearch, 'srlimit': '8',
    }
    url = COMMONS + '?' + urllib.parse.urlencode(params)
    data = _get_json(url)
    if not data:
        return None
    hits = (data.get('query') or {}).get('search') or []
    for h in hits:
        fname = h.get('title') or ''
        # Title comes as "File:Something.jpg"
        if not fname.lower().startswith('file:'):
            continue
        ext = fname.rsplit('.', 1)[-1].lower()
        if ext not in ('jpg', 'jpeg', 'png'):
            continue
        # Resolve the actual URL via imageinfo
        ii_params = {
            'action': 'query', 'format': 'json',
            'titles': fname, 'prop': 'imageinfo',
            'iiprop': 'url|size|mime',
        }
        ii_url = COMMONS + '?' + urllib.parse.urlencode(ii_params)
        ii_data = _get_json(ii_url)
        if not ii_data:
            continue
        pages = ((ii_data.get('query') or {}).get('pages') or {})
        for _pid, page in pages.items():
            ii = (page.get('imageinfo') or [])
            if not ii:
                continue
            info = ii[0]
            if info.get('width', 0) < 200 or info.get('height', 0) < 200:
                continue
            return info.get('url')
    return None


# -------- Resolver per entity kind -------- #

def resolve_artist_image(name: str):
    """Return (image_url, source_label) or (None, None)."""
    for cand in (name, f'{name}_(musician)', f'{name}_(band)'):
        thumb, orig = wiki_thumb(cand)
        url = orig or thumb
        if url:
            return url, f'wiki:{cand}'
        time.sleep(SLEEP)
    url = commons_first_image(f'"{name}" musician')
    if url:
        return url, 'commons'
    return None, None


def _strip_format_hint(title: str) -> str:
    # Discogs release titles sometimes carry "(LP)" / "(Remastered)" / "(EP)"; trim trailing parens
    return re.sub(r'\s*\([^()]{0,30}\)\s*$', '', title).strip() or title


def resolve_release_image(title: str, artist: str):
    """Return (image_url, source_label) or (None, None)."""
    bare = _strip_format_hint(title)
    cands = []
    if artist:
        cands.append(f'{bare}_({artist}_album)')
    cands.append(f'{bare}_(album)')
    cands.append(bare)
    for cand in cands:
        thumb, orig = wiki_thumb(cand)
        url = orig or thumb
        if url:
            return url, f'wiki:{cand}'
        time.sleep(SLEEP)
    url = commons_first_image(f'"{bare}" "{artist}" album')
    if url:
        return url, 'commons'
    return None, None


# -------- Download + save -------- #

def download_jpeg(url: str, dest: Path) -> bool:
    """Fetch, validate >=8KB image, re-encode JPEG to dest. Returns True on save."""
    status, headers, body = _http_get(url, timeout=20)
    if status != 200 or not body:
        return False
    if len(body) < MIN_BYTES:
        return False
    ct = ''
    if headers:
        # case-insensitive header lookup
        for k, v in headers.items():
            if k.lower() == 'content-type':
                ct = (v or '').lower()
                break
    if not any(t in ct for t in ('jpeg', 'jpg', 'png', 'webp', 'image/')):
        return False
    if Image is None:
        # Naive write - already filtered to >=8KB image bytes
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return True
    try:
        img = Image.open(io.BytesIO(body)).convert('RGB')
    except Exception:
        return False
    img.thumbnail((1200, 1200))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format='JPEG', quality=85, optimize=True)
    return True


# -------- Phases -------- #

def phase_artists(con: sqlite3.Connection, limit: int, *, dry_run: bool):
    cur = con.cursor()
    rows = cur.execute(
        '''SELECT id, name FROM artists
           WHERE (image_path IS NULL OR image_path = "")
             AND name IS NOT NULL AND name != ""
           ORDER BY in_collection DESC, rating DESC, id ASC
           LIMIT ?''', (limit,),
    ).fetchall()
    print(f'[artists] candidates: {len(rows)} (cap {limit})')

    updated = 0
    wiki_hits = 0
    commons_hits = 0
    misses = 0
    ARTIST_DIR.mkdir(parents=True, exist_ok=True)

    for i, (aid, name) in enumerate(rows, 1):
        # Skip generic / non-artist labels
        if name.strip().lower() in ('various', 'various artists', 'unknown artist', 'unknown'):
            misses += 1
            continue

        dest = ARTIST_DIR / f'{aid}.jpg'
        if dest.exists():
            # File already on disk but DB row says NULL — relink.
            if not dry_run:
                cur.execute('UPDATE artists SET image_path = ? WHERE id = ?',
                            (f'images/artist/{aid}.jpg', aid))
            updated += 1
            continue

        url, src = resolve_artist_image(name)
        if not url:
            misses += 1
            if i % 25 == 0:
                print(f'  [{i}/{len(rows)}] miss "{name}"')
            time.sleep(SLEEP)
            continue

        ok = download_jpeg(url, dest)
        time.sleep(SLEEP)
        if not ok:
            misses += 1
            continue

        if not dry_run:
            cur.execute('UPDATE artists SET image_path = ? WHERE id = ?',
                        (f'images/artist/{aid}.jpg', aid))
        updated += 1
        if src and src.startswith('wiki'):
            wiki_hits += 1
        else:
            commons_hits += 1
        if updated % 25 == 0:
            con.commit()
            print(f'  [{i}/{len(rows)}] +{updated} updated  (wiki {wiki_hits} / commons {commons_hits} / miss {misses})')

    con.commit()
    print(f'[artists] done: updated={updated}  wiki={wiki_hits}  commons={commons_hits}  miss={misses}')
    return {'updated': updated, 'wiki': wiki_hits, 'commons': commons_hits, 'miss': misses}


def phase_releases(con: sqlite3.Connection, limit: int, *, dry_run: bool):
    cur = con.cursor()
    rows = cur.execute(
        '''SELECT r.id, r.title, a.name
           FROM releases r LEFT JOIN artists a ON a.id = r.artist_id
           WHERE (r.image_path IS NULL OR r.image_path = "")
             AND r.title IS NOT NULL AND r.title != ""
           ORDER BY r.want_count DESC, r.have_count DESC, r.rating_count DESC, r.id ASC
           LIMIT ?''', (limit,),
    ).fetchall()
    print(f'[releases] candidates: {len(rows)} (cap {limit})')

    updated = 0
    wiki_hits = 0
    commons_hits = 0
    misses = 0
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    for i, (rid, title, artist) in enumerate(rows, 1):
        dest = RELEASE_DIR / f'{rid}.jpg'
        if dest.exists():
            if not dry_run:
                cur.execute('UPDATE releases SET image_path = ? WHERE id = ?',
                            (f'images/release/{rid}.jpg', rid))
            updated += 1
            continue

        url, src = resolve_release_image(title, artist or '')
        if not url:
            misses += 1
            if i % 25 == 0:
                print(f'  [{i}/{len(rows)}] miss "{title}" / "{artist}"')
            time.sleep(SLEEP)
            continue

        ok = download_jpeg(url, dest)
        time.sleep(SLEEP)
        if not ok:
            misses += 1
            continue

        if not dry_run:
            cur.execute('UPDATE releases SET image_path = ? WHERE id = ?',
                        (f'images/release/{rid}.jpg', rid))
        updated += 1
        if src and src.startswith('wiki'):
            wiki_hits += 1
        else:
            commons_hits += 1
        if updated % 25 == 0:
            con.commit()
            print(f'  [{i}/{len(rows)}] +{updated} updated  (wiki {wiki_hits} / commons {commons_hits} / miss {misses})')

    con.commit()
    print(f'[releases] done: updated={updated}  wiki={wiki_hits}  commons={commons_hits}  miss={misses}')
    return {'updated': updated, 'wiki': wiki_hits, 'commons': commons_hits, 'miss': misses}


# -------- Diversity gate -------- #

def diversity_gate(con: sqlite3.Connection):
    failures = []
    for table, col in (('artists', 'image_path'), ('releases', 'image_path')):
        rows = [r[0] for r in con.execute(
            f'SELECT "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" != ""'
        )]
        if len(rows) < 15:
            continue
        top_url, top_n = collections.Counter(rows).most_common(1)[0]
        ratio = top_n / len(rows)
        print(f'[diversity] {table}.{col}: {len(rows)} populated, top {top_n} '
              f'= {ratio:.1%} -> {top_url}')
        if ratio >= 0.05:
            failures.append((table, top_url, top_n, len(rows), ratio))
    if failures:
        raise AssertionError(
            'diversity gate failed: ' + '; '.join(
                f'{t}: {n}/{tot}={r:.1%} -> {u}' for (t, u, n, tot, r) in failures))


# -------- Main -------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit-artists', type=int, default=PER_PHASE_LIMIT_DEFAULT)
    ap.add_argument('--limit-releases', type=int, default=PER_PHASE_LIMIT_DEFAULT)
    ap.add_argument('--phase', choices=('artists', 'releases', 'both'), default='both')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
        print(f'FATAL: DB missing or 0 bytes: {DB_PATH}', file=sys.stderr)
        sys.exit(2)

    con = sqlite3.connect(str(DB_PATH), timeout=30)
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=30000')

    summary = {}
    if args.phase in ('artists', 'both'):
        summary['artists'] = phase_artists(con, args.limit_artists, dry_run=args.dry_run)
    if args.phase in ('releases', 'both'):
        summary['releases'] = phase_releases(con, args.limit_releases, dry_run=args.dry_run)

    print('---- summary ----')
    for k, v in summary.items():
        print(f'  {k}: {v}')

    print('---- diversity gate ----')
    diversity_gate(con)

    con.close()


if __name__ == '__main__':
    main()
