#!/usr/bin/env python3
"""Backfill phet_simulations.team_member.photo from Wikipedia REST.

Strategy (per operator note 2026-05-28):
  1. Wikipedia REST `/page/summary/<full name>` — pick originalimage or thumb.
     Notable PhET PIs (Carl Wieman, Kathy Perkins) have wiki pages; most
     engineers/designers do not.
  2. NO Tavily, NO fabrication. Misses stay NULL — about_team.html already
     renders SVG-style initials avatar, so NULL is the correct fallback.
  3. Only 20 rows — full pass, no batch logic.

Image lands at:
  sites/phet_simulations/static/images/team/<slug>.jpg
DB:
  /static/images/team/<slug>.jpg
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

SITE_ROOT = Path('/home/v-haoqiwang/repos/WebHarbor/sites/phet_simulations')
DB_PATH   = SITE_ROOT / 'instance' / 'phet_simulations.db'
IMG_DIR   = SITE_ROOT / 'static' / 'images' / 'team'
URL_PFX   = '/static/images/team/'

POLITE_UA  = ('WebHarbor/1.0 (https://github.com/MaitrixOrg/WebHarbor; '
              'haoqiwang+webharbor@microsoft.com)')
API_UA     = {'User-Agent': POLITE_UA, 'Accept': 'application/json'}
DL_HEADERS = {'User-Agent': POLITE_UA, 'Accept': 'image/*'}
WIKI_REST  = 'https://en.wikipedia.org/api/rest_v1/page/summary/{}'
SLEEP      = 1.2
DL_SLEEP   = 1.5
MIN_BYTES  = 8 * 1024
DL_RETRIES = 5

# tighter person-relevance keywords for academic / education context
RELEVANCE = (
    'physic', 'chemistry', 'educator', 'professor', 'researcher',
    'phet', 'colorado', 'university', 'science', 'nobel', 'cu boulder',
    'cu-boulder', 'wieman', 'simulation', 'instruct', 'teaching',
    'pedagogy', 'engineer',
)


def wiki_summary(name: str):
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
    img_thumb = (d.get('thumbnail') or {}).get('source')
    img_orig  = (d.get('originalimage') or {}).get('source')
    orig_w    = (d.get('originalimage') or {}).get('width') or 0
    img = img_orig or img_thumb
    if not img:
        return None, 'no-image'
    if img_orig and orig_w >= 2000 and img_thumb and '/thumb/' in img_thumb:
        import re as _re
        img = _re.sub(r'/(\d+)px-', '/1280px-', img_thumb)
    blob = (d.get('extract') or '').lower()
    if blob and not any(k in blob for k in RELEVANCE):
        return None, 'unrelated-bio'
    return img, d.get('type')


def download(url: str, dst: Path) -> bool:
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
        'SELECT id, slug, name, role FROM team_member '
        'WHERE photo IS NULL OR photo = "" '
        'ORDER BY id'
    ).fetchall()
    total = len(rows)
    print(f'phet_simulations: {total} team_member rows with NULL photo')

    updated = 0
    skipped = []
    for i, (mid, slug, name, role) in enumerate(rows, 1):
        print(f'[{i:2d}/{total}] {name}  ({role})')
        # try the bare name first; Wieman / Perkins resolve fine
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
        cur.execute('UPDATE team_member SET photo=? WHERE id=?', (web_path, mid))
        updated += 1
        con.commit()
        time.sleep(SLEEP)

    photos = [r[0] for r in cur.execute(
        'SELECT photo FROM team_member WHERE photo IS NOT NULL AND photo != ""')]
    print(f'\nupdated: {updated}/{total}  hit-rate: {updated/total:.1%}')
    if photos and len(photos) >= 15:
        import collections
        top_url, top_n = collections.Counter(photos).most_common(1)[0]
        ratio = top_n / len(photos)
        print(f'diversity top: {top_url} = {top_n}/{len(photos)} = {ratio:.1%}')
        if top_n > 1 and ratio >= 0.05:
            raise SystemExit(
                f'diversity gate FAILED: {ratio:.1%} share to {top_url}')
    elif photos:
        print(f'diversity gate skipped (only {len(photos)} photos < 15)')
    con.close()
    print('done.')


if __name__ == '__main__':
    main()
