#!/usr/bin/env python3
"""Extend Craigslist listings via static search HTML.

Target: 441 -> 1000+ listings across multiple regions and categories.

Source / quirk:
- The conventional `?format=rss` endpoint is blocked from this host (403 + cl_b
  cookie blocklist token). The `/search/<cat>` static HTML page returns 200 with
  a Mozilla UA and embeds <li class="cl-static-search-result" title="..."> items
  with title, post URL, price and neighborhood — sufficient for a listing row.
- Each post URL encodes region path + 3-letter category code + slug + postid.html
  e.g. /brk/app/d/brooklyn-keurig-mini-plus/7937196072.html
  We use the post id (last numeric segment) to form a globally unique slug.
- Mozilla UA is mandatory; bot UAs trigger the cl_b block.
- 0.5 s sleep between requests per operator note (cl is aggressive).
"""
from __future__ import annotations
import sqlite3
import re
import sys
import time
import datetime as dt
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import UA, slugify  # noqa: E402

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/craigslist/instance/craigslist.db'

# (region subdomain → area name we store)
REGIONS = [
    ('sfbay',       'san francisco'),
    ('newyork',     'new york'),
    ('losangeles',  'los angeles'),
    ('chicago',     'chicago'),
    ('seattle',     'seattle'),
    ('boston',      'boston'),
    ('washingtondc','washington dc'),
]

# Top-level category code → fallback (category_id, category_slug, category_group)
# Used when we cannot map the URL-embedded 3-letter code to a real subcategory.
TOP_CATS = [
    ('sss', 1,  'furniture',  'for_sale'),
    ('hhh', 10, 'apartments', 'housing'),
    ('jjj', 18, 'general_labor', 'jobs'),
]

# URL-embedded category abbrev → (our category_slug, our group_slug).
# Populated lazily from the DB in main().

SLEEP = 0.5
ITEM_RE = re.compile(
    r'<li class="cl-static-search-result"[^>]*title="(?P<title>[^"]*)"[^>]*>\s*'
    r'<a href="(?P<url>[^"]+)">.*?'
    r'(?:<div class="price">(?P<price>[^<]+)</div>\s*)?'
    r'<div class="location">\s*(?P<loc>[^<]+?)\s*</div>',
    re.DOTALL,
)
POSTID_RE = re.compile(r'/(\d{8,12})\.html$')
PATH_RE = re.compile(r'craigslist\.org/(?:([a-z]{3})/)?([a-z]{3})/d/')


def fetch_html(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')


def parse_price(s):
    if not s:
        return None
    digits = re.sub(r'[^0-9]', '', s)
    return int(digits) if digits else None


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    before = cur.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    print(f'before: {before} listings')

    # Build category lookup from DB so we can map URL-embedded 3-letter abbrev.
    cat_by_abbrev = {abbr: (cid, slug, grp) for cid, slug, abbr, grp in cur.execute(
        'SELECT id, slug, abbrev, group_slug FROM categories')}
    existing_slugs = {r[0] for r in cur.execute('SELECT slug FROM listings')}
    print(f'  category abbrevs known: {len(cat_by_abbrev)}, existing slugs: {len(existing_slugs)}')

    added = 0
    for region, area_name in REGIONS:
        for top_code, default_cid, default_cslug, default_group in TOP_CATS:
            url = f'https://{region}.craigslist.org/search/{top_code}'
            try:
                html = fetch_html(url)
            except Exception as e:
                print(f'  {region}/{top_code} fetch fail: {e}')
                time.sleep(SLEEP)
                continue
            matches = list(ITEM_RE.finditer(html))
            page_added = 0
            now = dt.datetime.utcnow()
            for m in matches:
                title = unescape(m.group('title') or '').strip()[:220]
                href = m.group('url') or ''
                price = parse_price(m.group('price'))
                loc = unescape(m.group('loc') or '').strip()[:120]
                if not title or not href:
                    continue
                pid_m = POSTID_RE.search(href)
                if not pid_m:
                    continue
                post_id = pid_m.group(1)
                slug = f'{slugify(title, maxlen=200)}-{post_id}'[:240]
                if slug in existing_slugs:
                    continue
                cat_id, cat_slug, cat_group = default_cid, default_cslug, default_group
                pm = PATH_RE.search(href)
                if pm and pm.group(2) in cat_by_abbrev:
                    cat_id, cat_slug, cat_group = cat_by_abbrev[pm.group(2)]
                try:
                    cur.execute(
                        'INSERT OR IGNORE INTO listings '
                        '(title, slug, category_id, category_slug, category_group, '
                        'area, neighborhood, price, description, image, '
                        'posted_at, updated_at, status, view_count, flag_count) '
                        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (title, slug, cat_id, cat_slug, cat_group,
                         area_name, loc, price, None, None,
                         now, now, 'active', 0, 0))
                except sqlite3.IntegrityError:
                    continue
                if cur.rowcount:
                    existing_slugs.add(slug)
                    added += 1
                    page_added += 1
                    if added % 50 == 0:
                        con.commit()
            print(f'  {region}/{top_code}: parsed={len(matches)} +{page_added}')
            con.commit()
            time.sleep(SLEEP)

    con.commit()
    after = cur.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    print(f'after: {after} (+{added})')
    con.close()


if __name__ == '__main__':
    main()
