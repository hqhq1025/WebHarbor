#!/usr/bin/env python3
"""Backfill rotten_tomatoes.critics.photo from Wikipedia REST.

Strategy (per operator note 2026-05-28):
  1. Wikipedia REST `/page/summary/<critic name>` — pick originalimage,
     fall back to thumbnail. Skip 404 / disambig / non-person hits.
  2. NO Tavily, NO fabrication. Critics without a Wikipedia page stay NULL.

Expected hit rate ~30-50% (a lot of small-paper critics have no wiki page).

Image lands at:
  sites/rotten_tomatoes/static/images/critics/<slug>.jpg
DB:
  /static/images/critics/<slug>.jpg

Container DB path: /opt/WebSyn/rotten_tomatoes/instance/rotten_tomatoes.db
Local mirror:       sites/rotten_tomatoes/instance/rotten_tomatoes.db (we
docker cp from container if missing, write here, push back via the operator's
verify step — script itself does NOT cp/restart).
"""
from __future__ import annotations
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

SITE_ROOT = Path('/home/v-haoqiwang/repos/WebHarbor/sites/rotten_tomatoes')
DB_PATH   = SITE_ROOT / 'instance' / 'rotten_tomatoes.db'
IMG_DIR   = SITE_ROOT / 'static' / 'images' / 'critics'
URL_PFX   = '/static/images/critics/'

# Wikimedia requires a polite UA with contact info (see https://w.wiki/4wJS).
# Using Mozilla on bulk uploads triggers 429. Use the WebHarbor identity for
# both the REST API and upload.wikimedia.org so we obey the policy.
POLITE_UA   = ('WebHarbor/1.0 (https://github.com/MaitrixOrg/WebHarbor; '
               'haoqiwang+webharbor@microsoft.com)')
API_UA      = {'User-Agent': POLITE_UA, 'Accept': 'application/json'}
DL_HEADERS  = {'User-Agent': POLITE_UA, 'Accept': 'image/*'}
WIKI_REST   = 'https://en.wikipedia.org/api/rest_v1/page/summary/{}'
SLEEP       = 1.2          # between Wikipedia REST calls
DL_SLEEP    = 1.5          # between upload.wikimedia.org downloads
MIN_BYTES   = 8 * 1024
DL_RETRIES  = 5


def wiki_summary(name: str):
    """Return (image_url, page_type) or (None, reason)."""
    title = name.strip()
    if not title:
        return None, 'empty'
    url = WIKI_REST.format(urllib.parse.quote(title.replace(' ', '_'), safe=''))
    try:
        req = urllib.request.Request(url, headers=API_UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            import json
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None, f'http{e.code}'
    except Exception as e:
        return None, f'err:{type(e).__name__}'
    if d.get('type') in ('disambiguation', 'no-extract'):
        return None, d.get('type')
    # Wikipedia REST returns:
    #   thumbnail.source   -> e.g. .../thumb/.../330px-Name.jpg
    #   originalimage.source -> raw upload (works, just larger)
    # Wikimedia restricts bulk callers to specific thumbnail sizes
    # (https://w.wiki/GHai — empirically 330 / 1280 / 1920 only).
    # Originals always succeed under a polite UA, so prefer the original
    # and rewrite the thumbnail width to 1280 when we have to fall back.
    img_thumb = (d.get('thumbnail') or {}).get('source')
    img_orig  = (d.get('originalimage') or {}).get('source')
    orig_w    = (d.get('originalimage') or {}).get('width') or 0
    img = img_orig or img_thumb
    if not img:
        return None, 'no-image'
    # if original is >2000px wide, fall back to 1280px thumb to be polite
    if img_orig and orig_w >= 2000 and img_thumb and '/thumb/' in img_thumb:
        import re as _re
        img = _re.sub(r'/(\d+)px-', '/1280px-', img_thumb)
    blob = (d.get('extract') or '').lower()
    if blob and not any(k in blob for k in (
            'critic', 'film', 'writer', 'journalist', 'review', 'reporter',
            'editor', 'columnist', 'author', 'cinema', 'screen')):
        return None, 'unrelated-bio'
    return img, d.get('type')


def download(url: str, dst: Path) -> bool:
    """GET with polite UA and Retry-After backoff for upload.wikimedia.org."""
    last_err = None
    for attempt in range(DL_RETRIES):
        try:
            req = urllib.request.Request(url, headers=DL_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < MIN_BYTES:
                print(f'    too-small: {len(data)}B')
                return False
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            return True
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                # honor Retry-After if present, else exponential 4/8/16/32s
                ra = e.headers.get('Retry-After') if e.headers else None
                try:
                    wait = int(ra) if ra else 4 * (2 ** attempt)
                except ValueError:
                    wait = 4 * (2 ** attempt)
                wait = min(wait, 60)
                print(f'    429, sleeping {wait}s (attempt {attempt+1}/{DL_RETRIES})')
                time.sleep(wait)
                continue
            print(f'    http{e.code}')
            return False
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    print(f'    download fail after {DL_RETRIES} retries: {last_err}')
    return False


def main():
    assert DB_PATH.exists(), f'DB missing: {DB_PATH}'
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    rows = cur.execute(
        'SELECT id, slug, name FROM critics '
        'WHERE photo IS NULL OR photo = "" '
        'ORDER BY id'
    ).fetchall()
    total = len(rows)
    print(f'rotten_tomatoes: {total} critics with NULL photo')

    updated = 0
    skipped = []  # list of (slug, reason)
    for i, (cid, slug, name) in enumerate(rows, 1):
        print(f'[{i:3d}/{total}] {name}')
        img_url, reason = wiki_summary(name)
        if not img_url:
            print(f'    skip ({reason})')
            skipped.append((slug, reason))
            time.sleep(SLEEP)
            continue
        ext = '.jpg'
        url_l = img_url.lower()
        if url_l.endswith('.png'):
            ext = '.png'
        elif url_l.endswith('.jpeg'):
            ext = '.jpg'
        dst = IMG_DIR / f'{slug}{ext}'
        if dst.exists() and dst.stat().st_size >= MIN_BYTES:
            print(f'    have cached file {dst.name}')
        else:
            if not download(img_url, dst):
                skipped.append((slug, 'dl-fail'))
                time.sleep(SLEEP)
                continue
            time.sleep(DL_SLEEP)
        web_path = URL_PFX + dst.name
        cur.execute('UPDATE critics SET photo=? WHERE id=?', (web_path, cid))
        updated += 1
        if updated % 10 == 0:
            con.commit()
        time.sleep(SLEEP)

    con.commit()

    # diversity gate
    photos = [r[0] for r in cur.execute(
        'SELECT photo FROM critics WHERE photo IS NOT NULL AND photo != ""')]
    print(f'\nupdated: {updated}/{total}  hit-rate: {updated/total:.1%}')
    if photos:
        import collections
        top_url, top_n = collections.Counter(photos).most_common(1)[0]
        ratio = top_n / len(photos)
        print(f'diversity top: {top_url} = {top_n}/{len(photos)} = {ratio:.1%}')
        # Each row gets a unique slug-named file, so top_n==1 means structurally
        # no duplicate. Fail only on actual duplicates (top_n > 1) above the
        # 5% threshold — otherwise small-N runs would always trip the gate.
        if top_n > 1 and ratio >= 0.05 and len(photos) >= 15:
            raise SystemExit(
                f'diversity gate FAILED: {ratio:.1%} share to {top_url}')
    con.close()
    print('done.')


if __name__ == '__main__':
    main()
