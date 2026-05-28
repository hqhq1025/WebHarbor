#!/usr/bin/env python3
"""Scrape real per-post images for craigslist `listings.image`.

Why: 7147/7578 listings have NULL image (94%). This script fetches each post's
detail HTML upstream, extracts the canonical `og:image` (a real
`images.craigslist.org/<id>_<dim>x<dim>.jpg` photo uploaded by the seller), and
stores it on the row. Real-image-only — no placeholder fabrication.

Source ladder (no Tavily):
1. Reconstruct the canonical region + top-category from each row, then ask the
   craigslist static search endpoint `/search/<top>?query=<post_id>` to resolve
   the current canonical post URL (anchor with `/<post_id>.html` suffix).
2. GET that post URL and pull `<meta property="og:image" content="...">`.
3. HEAD the resulting image URL — drop anything < 8 KB (1x1 tracking pixel,
   craigslist "no image" stub, etc).

Hard limits:
- Cap at 1000 rows ordered by id ASC (earliest first — see operator note).
- 0.5s sleep between rows (craigslist anti-bot is aggressive).
- Mozilla UA mandatory (bot UAs trigger cl_b blocklist token).
- Bail on a streak of 10 consecutive 403/timeout responses (IP throttle).
- Never fabricate — if any step fails, leave image NULL.
- Periodic commit every 50 successful updates so a mid-run kill keeps progress.

Output: rows updated + failure breakdown + post-fix top-image diversity.
"""
from __future__ import annotations
import argparse
import re
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import UA, assert_image_diversity  # noqa: E402

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/craigslist/instance/craigslist.db'

AREA_TO_REGION = {
    'san francisco': 'sfbay',
    'new york':      'newyork',
    'los angeles':   'losangeles',
    'chicago':       'chicago',
    'seattle':       'seattle',
    'boston':        'boston',
    'washington dc': 'washingtondc',
    # sfbay sub-regions stored as their own area name in some early rows
    'east bay':      'sfbay',
    'south bay':     'sfbay',
    'peninsula':     'sfbay',
    'north bay':     'sfbay',
    'santa cruz':    'sfbay',
}

# category_group → craigslist top-level category code used in /search/<code>
CAT_GROUP_TO_TOP = {
    'for_sale': 'sss',
    'housing':  'hhh',
    'jobs':     'jjj',
}

POSTID_RE = re.compile(r'-(\d{8,12})$')
HREF_RE_TMPL = r'href="(https://[^"]+/{post_id}\.html)"'
OG_IMAGE_RE = re.compile(
    r'<meta\s+property="og:image"\s+content="(https://images\.craigslist\.org/[^"]+)"',
    re.IGNORECASE,
)
# Fallback for posts that store the first slide img alongside og.
SLIDE_IMG_RE = re.compile(
    r'<img[^>]+src="(https://images\.craigslist\.org/[^"]+\.jpg)"',
    re.IGNORECASE,
)

SLEEP = 0.5
BAIL_STREAK = 10
TIMEOUT = 15
MIN_BYTES = 8 * 1024


def http_get(url: str) -> tuple[int, bytes]:
    """GET → (status, body). Raises on transport error so caller can bail-count."""
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''


def http_head_len(url: str) -> int:
    """HEAD → content-length, or -1 on transport error / missing header."""
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        cl = r.headers.get('Content-Length')
        return int(cl) if cl and cl.isdigit() else -1


def resolve_post_url(region: str, top_cat: str, post_id: str) -> str | None:
    search = f'https://{region}.craigslist.org/search/{top_cat}?query={post_id}'
    status, body = http_get(search)
    if status != 200 or not body:
        return None
    html = body.decode('utf-8', errors='replace')
    m = re.search(HREF_RE_TMPL.format(post_id=re.escape(post_id)), html)
    return unescape(m.group(1)) if m else None


def extract_og_image(post_html: str) -> str | None:
    m = OG_IMAGE_RE.search(post_html)
    if m:
        return unescape(m.group(1))
    # fallback: first inline craigslist slide img
    m = SLIDE_IMG_RE.search(post_html)
    return unescape(m.group(1)) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=1000)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute(
        'SELECT id, slug, area, category_group FROM listings '
        'WHERE (image IS NULL OR image = "") '
        "  AND category_group IN ('for_sale','housing','jobs') "
        'ORDER BY id ASC LIMIT ?',
        (args.limit,),
    ).fetchall()
    print(f'candidates: {len(rows)} (id ASC, image NULL)')

    fail_streak = 0
    stats = {
        'updated': 0,
        'no_postid': 0,
        'no_region': 0,
        'no_top': 0,
        'search_miss': 0,
        'no_og_image': 0,
        'too_small': 0,
        'head_fail': 0,
        'http_error': 0,
        'timeout': 0,
        'bailed': False,
    }

    for row_idx, (lid, slug, area, group) in enumerate(rows):
        # 1. resolve region + top-cat
        region = AREA_TO_REGION.get((area or '').strip().lower())
        if not region:
            stats['no_region'] += 1
            continue
        top_cat = CAT_GROUP_TO_TOP.get((group or '').strip().lower())
        if not top_cat:
            stats['no_top'] += 1
            continue
        m = POSTID_RE.search(slug or '')
        if not m:
            stats['no_postid'] += 1
            continue
        post_id = m.group(1)

        # 2. find canonical URL via search
        try:
            post_url = resolve_post_url(region, top_cat, post_id)
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            stats['timeout'] += 1
            fail_streak += 1
            if fail_streak >= BAIL_STREAK:
                stats['bailed'] = True
                print(f'  bail: {fail_streak} consecutive transport errors')
                break
            time.sleep(SLEEP)
            continue
        if post_url is None:
            stats['search_miss'] += 1
            fail_streak = 0
            time.sleep(SLEEP)
            continue

        # 3. fetch post HTML
        try:
            status, body = http_get(post_url)
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            stats['timeout'] += 1
            fail_streak += 1
            if fail_streak >= BAIL_STREAK:
                stats['bailed'] = True
                print(f'  bail: {fail_streak} consecutive transport errors')
                break
            time.sleep(SLEEP)
            continue

        if status == 403:
            stats['http_error'] += 1
            fail_streak += 1
            if fail_streak >= BAIL_STREAK:
                stats['bailed'] = True
                print(f'  bail: {fail_streak} consecutive 403s')
                break
            time.sleep(SLEEP)
            continue
        if status != 200 or not body:
            stats['http_error'] += 1
            fail_streak = 0
            time.sleep(SLEEP)
            continue

        fail_streak = 0
        post_html = body.decode('utf-8', errors='replace')
        img_url = extract_og_image(post_html)
        if not img_url:
            stats['no_og_image'] += 1
            time.sleep(SLEEP)
            continue

        # 4. HEAD filter — drop placeholders / 1x1 trackers
        try:
            content_len = http_head_len(img_url)
        except Exception:
            stats['head_fail'] += 1
            time.sleep(SLEEP)
            continue
        if 0 <= content_len < MIN_BYTES:
            stats['too_small'] += 1
            time.sleep(SLEEP)
            continue

        # 5. persist
        if not args.dry_run:
            cur.execute('UPDATE listings SET image=? WHERE id=?', (img_url, lid))
            if stats['updated'] and stats['updated'] % 50 == 0:
                con.commit()
        stats['updated'] += 1

        if (row_idx + 1) % 25 == 0:
            print(f'  [{row_idx+1}/{len(rows)}] updated={stats["updated"]} '
                  f'miss={stats["search_miss"]} no_og={stats["no_og_image"]} '
                  f'small={stats["too_small"]} http_err={stats["http_error"]}')
        time.sleep(SLEEP)

    if not args.dry_run:
        con.commit()

    print()
    print('=== final stats ===')
    for k, v in stats.items():
        print(f'  {k}: {v}')

    # post-fix diversity gate
    try:
        assert_image_diversity(con, 'listings', 'image', threshold=0.05)
        print('diversity gate: PASS')
    except AssertionError as e:
        print(f'diversity gate: FAIL — {e}')

    # report top images
    print()
    print('top 5 image URLs (sanity):')
    for url, n in cur.execute(
        'SELECT image, COUNT(*) FROM listings '
        'WHERE image IS NOT NULL AND image != "" '
        'GROUP BY image ORDER BY 2 DESC LIMIT 5'
    ):
        print(f'  {n:5d} {url}')

    con.close()


if __name__ == '__main__':
    main()
