#!/usr/bin/env python3
"""Multi-site small image-gap backfill.

Targets four small NULL pockets in image columns:

* imdb.titles.poster_path     (20 NULL) - re-query OMDB, fall back to Wikipedia
* nba.players.image           (15 NULL) - Wikipedia search by player name
* bbc_news.articles.hero_image (53 NULL) - re-fetch source_url, scrape og:image
* eventbrite.blog_posts.cover_image (20 NULL) - Wikipedia search by tag+keyword

Skipped intentionally:
* allrecipes.user.avatar_url - these are mirror-internal user accounts; no real avatars.

Common policy:
* 8 KB minimum file size (skip placeholder icons)
* 0.4 s sleep between outbound requests
* API UA `WebHarbor-bot/1.0 (haoqiw@microsoft.com)` for Wikimedia/OMDB
* Browser UA for HTML scrapes (BBC, etc.)
* No fabrication: rows that yield nothing stay NULL.

Usage::

    python3 tools/bulk_api/small_image_gaps.py            # run all four phases
    python3 tools/bulk_api/small_image_gaps.py imdb nba   # run a subset

Each phase prints `N updated / N skipped`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request

REPO = pathlib.Path('/home/v-haoqiwang/repos/WebHarbor')
MIN_BYTES = 8 * 1024
SLEEP_S = 0.4
TIMEOUT = 15

API_UA = 'WebHarbor-bot/1.0 (haoqiw@microsoft.com)'
BROWSER_UA = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
)

OMDB_KEY = 'trilogy'


# ---------- HTTP helpers ----------


def http_json(url: str, ua: str = API_UA) -> dict | None:
    req = urllib.request.Request(url, headers={'User-Agent': ua, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except Exception as exc:
        sys.stderr.write(f'  http_json fail {url[:80]}: {exc}\n')
        return None


def http_get(url: str, ua: str = BROWSER_UA, referer: str | None = None) -> tuple[bytes, str]:
    headers = {'User-Agent': ua, 'Accept-Language': 'en-US,en;q=0.9'}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        ct = r.headers.get('Content-Type', '')
        return r.read(), ct


def download_image(url: str, dest: pathlib.Path, referer: str | None = None) -> tuple[bool, str]:
    """Download image, validate ≥8KB and correct content-type, write to dest.

    Returns (ok, reason). reason '' on success.
    """
    try:
        body, ct = http_get(url, ua=BROWSER_UA, referer=referer)
    except Exception as exc:
        return False, f'net:{type(exc).__name__}'
    ct_low = ct.lower()
    if not any(t in ct_low for t in ('jpeg', 'jpg', 'png', 'webp', 'gif')):
        # Some Wikimedia URLs return application/octet-stream; trust the URL extension.
        if not any(url.lower().endswith(e) for e in ('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return False, f'ct:{ct[:30]}'
    if len(body) < MIN_BYTES:
        return False, f'small:{len(body)}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return True, ''


def wiki_search_image(query: str, thumbsize: int = 300) -> str:
    """Return first Wikipedia search result's thumbnail URL or ''.

    We deliberately use a small `pithumbsize` (default 300) and only return
    `thumbnail.source`. Two reasons:

    * Wikimedia rate-limits direct downloads from the bare
      ``upload.wikimedia.org/wikipedia/commons/<a>/<ab>/<file>`` path; only
      ``/wikipedia/commons/thumb/...`` URLs are reliably cacheable.
    * Asking for a thumb size *smaller* than the original guarantees the API
      returns a `/thumb/` URL. If the file is smaller than the requested size
      the API hands back the bare original which trips the 429.

    300 px is plenty: a 300 px wide JPEG is typically 30-60 KB, well above the
    8 KB minimum, and rendered at <=360 px in the target templates.
    """
    params = urllib.parse.urlencode({
        'action': 'query',
        'generator': 'search',
        'gsrsearch': query,
        'gsrlimit': 1,
        'prop': 'pageimages',
        'piprop': 'thumbnail',
        'pithumbsize': thumbsize,
        'format': 'json',
    })
    data = http_json('https://en.wikipedia.org/w/api.php?' + params, ua=API_UA)
    if not data:
        return ''
    pages = (data.get('query') or {}).get('pages') or {}
    for _pid, p in pages.items():
        thumb = (p.get('thumbnail') or {}).get('source', '')
        # Sanity: only trust /thumb/ URLs.
        if '/thumb/' in thumb:
            return thumb
    return ''


# ---------- Phase 1: IMDb poster_path ----------


def phase_imdb() -> dict:
    db_path = REPO / 'sites/imdb/instance/imdb.db'
    dest_dir = REPO / 'sites/imdb/static/images/imdb_real'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, tt_id, primary_title FROM titles "
        "WHERE poster_path IS NULL OR poster_path = ''"
    ).fetchall()
    print(f'[imdb] candidates={len(rows)}', flush=True)

    updated, skipped = 0, []
    for row_id, tt_id, title in rows:
        poster_url = ''
        # 1) OMDB re-fetch (in case poster updated since first seed).
        d = http_json(
            'http://www.omdbapi.com/?' + urllib.parse.urlencode({'i': tt_id, 'apikey': OMDB_KEY}),
            ua=API_UA,
        )
        if d and d.get('Response') == 'True':
            p = d.get('Poster', '')
            if p and p != 'N/A':
                poster_url = p
        time.sleep(SLEEP_S)

        # 2) Wikipedia fallback: search "<title> film".
        if not poster_url:
            for q in (f'{title} film', title):
                poster_url = wiki_search_image(q)
                time.sleep(SLEEP_S)
                if poster_url:
                    break

        if not poster_url:
            skipped.append((tt_id, title, 'no-source'))
            continue

        ext = '.jpg'
        for cand in ('.jpg', '.jpeg', '.png', '.webp'):
            if poster_url.lower().endswith(cand):
                ext = '.jpg' if cand == '.jpeg' else cand
                break
        h = hashlib.md5(poster_url.encode()).hexdigest()[:8]
        rel = f'imdb_real/h_{h}{ext}'
        dest = REPO / 'sites/imdb/static/images' / rel

        ok, reason = download_image(poster_url, dest, referer='https://www.imdb.com/')
        if not ok:
            skipped.append((tt_id, title, reason))
            continue
        cur.execute('UPDATE titles SET poster_path = ? WHERE id = ?', (rel, row_id))
        updated += 1
        time.sleep(SLEEP_S)

    con.commit()
    con.close()
    return _report('imdb', updated, skipped)


# ---------- Phase 2: NBA player image ----------


def phase_nba() -> dict:
    db_path = REPO / 'sites/nba/instance/nba.db'
    dest_dir = REPO / 'sites/nba/static/images/wiki'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, name, slug FROM players WHERE image IS NULL OR image = ''"
    ).fetchall()
    print(f'[nba] candidates={len(rows)}', flush=True)

    updated, skipped = 0, []
    for row_id, name, slug in rows:
        img_url = ''
        for q in (f'{name} basketball', name):
            img_url = wiki_search_image(q, thumbsize=300)
            time.sleep(SLEEP_S)
            if img_url:
                break
        if not img_url:
            skipped.append((slug, name, 'no-source'))
            continue
        ext = '.jpg'
        for cand in ('.jpg', '.jpeg', '.png', '.webp'):
            if img_url.lower().endswith(cand):
                ext = '.jpg' if cand == '.jpeg' else cand
                break
        dest = dest_dir / f'{slug}{ext}'
        ok, reason = download_image(img_url, dest, referer='https://en.wikipedia.org/')
        if not ok:
            skipped.append((slug, name, reason))
            continue
        rel = f'/static/images/wiki/{slug}{ext}'
        cur.execute('UPDATE players SET image = ? WHERE id = ?', (rel, row_id))
        updated += 1
        time.sleep(SLEEP_S)

    con.commit()
    con.close()
    return _report('nba', updated, skipped)


# ---------- Phase 3: BBC hero_image ----------


_OG_IMAGE_RE = re.compile(
    rb'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _strip_rss_query(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.query and 'at_medium=RSS' in p.query:
        p = p._replace(query='')
    return urllib.parse.urlunsplit(p)


def phase_bbc() -> dict:
    db_path = REPO / 'sites/bbc_news/instance/bbc_news.db'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, source_url FROM articles "
        "WHERE (hero_image IS NULL OR hero_image = '') "
        "AND source_url IS NOT NULL AND source_url != ''"
    ).fetchall()
    print(f'[bbc_news] candidates={len(rows)}', flush=True)

    updated, skipped = 0, []
    consec_fail = 0
    for row_id, src in rows:
        clean = _strip_rss_query(src)
        try:
            body, _ct = http_get(clean, ua=BROWSER_UA)
            consec_fail = 0
        except Exception as exc:
            consec_fail += 1
            skipped.append((row_id, clean, f'net:{type(exc).__name__}'))
            if consec_fail >= 10:
                print('  [bbc_news] aborting after 10 consecutive net failures', flush=True)
                break
            time.sleep(SLEEP_S)
            continue
        m = _OG_IMAGE_RE.search(body)
        if not m:
            skipped.append((row_id, clean, 'no-og-image'))
            time.sleep(SLEEP_S)
            continue
        og_url = m.group(1).decode('utf-8', 'ignore')
        # Established BBC pattern: store the ichef CDN URL directly (624 rows already do this).
        cur.execute('UPDATE articles SET hero_image = ? WHERE id = ?', (og_url, row_id))
        updated += 1
        if updated % 25 == 0:
            con.commit()
            print(f'  [bbc_news] progress {updated}/{len(rows)}', flush=True)
        time.sleep(SLEEP_S)

    con.commit()
    con.close()
    return _report('bbc_news', updated, skipped)


# ---------- Phase 4: Eventbrite cover_image ----------


# Per-post Wikipedia query mapping. Each post id maps to fallback queries (tried in order).
EVENTBRITE_QUERIES = {
    1:  ['Event management', 'Eventbrite'],
    2:  ['Concert ticket', 'Ticket pricing'],
    3:  ['Roof terrace', 'Rooftop bar', 'Rooftop'],
    4:  ['Artificial intelligence conference', 'Tech conference'],
    5:  ['Community organizing', 'Meetup'],
    6:  ['Drag show', 'Drag brunch'],
    7:  ['Conference', 'Convention center'],
    8:  ['Customer service', 'Refund', 'Consumer protection'],
    9:  ['Digital advertising', 'Online advertising'],
    10: ['South by Southwest', 'SXSW'],
    11: ['Yoga', 'Outdoor yoga'],
    12: ['Block party', 'Street party'],
    13: ['Saxophone', 'Jazz', 'Jazz festival'],
    14: ['Charity gala', 'Gala dinner'],
    15: ['Webinar', 'Live streaming'],
    16: ['Food festival', 'Street food'],
    17: ['Vinyl record', 'Record store'],
    18: ['Mental health', 'Mental health awareness'],
    19: ['Volunteering', 'Volunteer management'],
    20: ['Convention center', 'Convention', 'Business conference'],
}


def phase_eventbrite() -> dict:
    db_path = REPO / 'sites/eventbrite/instance/eventbrite.db'
    dest_dir = REPO / 'sites/eventbrite/static/images/blog'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, slug, title, tag FROM blog_posts WHERE cover_image IS NULL OR cover_image = ''"
    ).fetchall()
    print(f'[eventbrite] candidates={len(rows)}', flush=True)

    updated, skipped = 0, []
    for row_id, slug, title, tag in rows:
        queries = EVENTBRITE_QUERIES.get(row_id, [])
        if not queries:
            queries = [f'{tag} event', tag or title]
        img_url = ''
        for q in queries:
            img_url = wiki_search_image(q, thumbsize=400)
            time.sleep(SLEEP_S)
            if img_url:
                break
        if not img_url:
            skipped.append((slug, queries, 'no-source'))
            continue
        ext = '.jpg'
        for cand in ('.jpg', '.jpeg', '.png', '.webp'):
            if img_url.lower().endswith(cand):
                ext = '.jpg' if cand == '.jpeg' else cand
                break
        dest = dest_dir / f'{slug}{ext}'
        ok, reason = download_image(img_url, dest, referer='https://en.wikipedia.org/')
        if not ok:
            skipped.append((slug, queries, reason))
            continue
        rel = f'blog/{slug}{ext}'  # template prepends 'images/'
        cur.execute('UPDATE blog_posts SET cover_image = ? WHERE id = ?', (rel, row_id))
        updated += 1
        time.sleep(SLEEP_S)

    con.commit()
    con.close()
    return _report('eventbrite', updated, skipped)


# ---------- Reporter ----------


def _report(site: str, updated: int, skipped: list) -> dict:
    print(f'[{site}] DONE updated={updated} skipped={len(skipped)}', flush=True)
    if skipped:
        # Bucket reasons
        buckets: dict[str, int] = {}
        for tup in skipped:
            reason = tup[-1]
            buckets[reason] = buckets.get(reason, 0) + 1
        print(f'  skip reasons: {buckets}', flush=True)
        for tup in skipped[:5]:
            print(f'  ex: {tup}', flush=True)
    return {'site': site, 'updated': updated, 'skipped': len(skipped)}


# ---------- Entrypoint ----------


PHASES = {
    'imdb': phase_imdb,
    'nba': phase_nba,
    'bbc_news': phase_bbc,
    'bbc': phase_bbc,
    'eventbrite': phase_eventbrite,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('phases', nargs='*', help='subset of phases (default: all)')
    args = ap.parse_args()

    order = ['imdb', 'nba', 'bbc_news', 'eventbrite']
    todo = args.phases or order
    # Normalise aliases.
    todo = ['bbc_news' if p == 'bbc' else p for p in todo]
    seen = set()
    todo = [p for p in todo if not (p in seen or seen.add(p))]

    results = []
    for p in todo:
        fn = PHASES.get(p)
        if not fn:
            print(f'unknown phase: {p}', file=sys.stderr)
            continue
        results.append(fn())

    print()
    print('=== SUMMARY ===')
    for r in results:
        print(f'  {r["site"]:12s} updated={r["updated"]:3d}  skipped={r["skipped"]:3d}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
