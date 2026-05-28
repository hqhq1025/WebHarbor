#!/usr/bin/env python3
"""Generic static-asset image downloader from harvest `_image_urls.jsonl`.

Pattern (coursera 2026-05-28): the mirror's template renders images via a
`site_thumb(entity)` helper that resolves to a LOCAL file path —
`static/images/<dir>/<slug>.jpg` — instead of using a DB column. So image
backfill is a static-asset task: download from harvested URLs to the
expected local path.

When to use this (instead of `*_image_backfill.py` which writes to a DB column):
- Site's model has NO image_url column (verify schema first!)
- Templates use `url_for('static', filename=f'images/<dir>/{slug}.jpg')` pattern
- harvest_spider has populated `_image_urls.jsonl` with source-page-attributed URLs

Copy this file to <site>_thumb_download.py and fill in the 4 TODOs.

Real impact reference (coursera, pending result):
  ~600 expected downloads / ~5 min @ 0.3s pacing / fork commit lands new script + size report
"""
from __future__ import annotations
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError:
    print('PIL required: pip install pillow', file=sys.stderr)
    sys.exit(2)

# TODO #1: site identifier
SITE = '<site_slug>'

# TODO #2: source-page URL pattern → entity slug
# e.g. coursera: '/learn/<slug>'  /  imdb: '/title/<tt_id>/'  /  bgg: '/boardgame/<id>/'
SOURCE_PAGE_PATTERN = re.compile(r'/learn/([^/?#]+)')

# TODO #3: local static path template, relative to sites/<site>/static/
LOCAL_TPL = 'images/courses/real/{slug}.jpg'  # → sites/<site>/static/images/courses/real/<slug>.jpg

# TODO #4: input snapshot + size + pacing knobs
HARVEST_JSONL = f'/home/v-haoqiwang/webvoyager-analysis/real_components/snapshots/<site>_org/_image_urls.jsonl'
MAX_DOWNLOADS = 800              # safety cap
MAX_SIDE = 600                   # resize to this max edge
JPEG_QUALITY = 85
MIN_BYTES = 4096                 # skip icons/placeholders (4 KB filter)
SLEEP = 0.3
CONSECUTIVE_FAIL_BAIL = 10

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

WEBHARBOR = Path('/home/v-haoqiwang/repos/WebHarbor')
STATIC_DIR = WEBHARBOR / 'sites' / SITE / 'static'


def best_src_per_slug() -> dict[str, str]:
    """Aggregate harvest entries → {slug: best_src_url}.

    Heuristics for "best":
    - URL containing 1200/1024/hero/cover/og: → prefer
    - URL containing icon/logo/avatar/sprite: → skip
    - Otherwise: keep first
    """
    SKIP = re.compile(r'icon|logo|avatar|sprite|svg|favicon', re.I)
    PREFER = re.compile(r'1200|1024|hero|cover|og:image', re.I)
    by_slug: dict[str, tuple[int, str]] = {}  # slug → (score, url)
    with open(HARVEST_JSONL) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            src = entry.get('src') or entry.get('url') or ''
            page = entry.get('source_page') or entry.get('page') or ''
            if not src or not page or src.startswith('data:'):
                continue
            if SKIP.search(src):
                continue
            m = SOURCE_PAGE_PATTERN.search(page)
            if not m:
                continue
            slug = m.group(1)
            score = 2 if PREFER.search(src) else 1
            cur = by_slug.get(slug)
            if cur is None or cur[0] < score:
                by_slug[slug] = (score, src)
    return {slug: url for slug, (_, url) in by_slug.items()}


def fetch_and_resize(url: str) -> Optional[bytes]:
    """Download, validate size, resize, re-encode JPEG. None on any failure."""
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            # case-insensitive header lookup (gotcha: urlopen lowercases keys)
            cl_raw = r.headers.get('Content-Length') or r.headers.get('content-length')
            if cl_raw and int(cl_raw) < MIN_BYTES:
                return None
            data = r.read()
    except (urllib.error.HTTPError, urllib.error.URLError, ConnectionError, TimeoutError, OSError):
        return None
    if len(data) < MIN_BYTES:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return None
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    try:
        img.convert('RGB').save(out, 'JPEG', quality=JPEG_QUALITY, optimize=True)
    except Exception:
        return None
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=MAX_DOWNLOADS)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    pairs = best_src_per_slug()
    print(f'candidate slugs: {len(pairs)}')

    out_dir = STATIC_DIR / Path(LOCAL_TPL).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = defaultdict(int)
    consec_fail = 0
    downloaded = 0

    for slug, src in pairs.items():
        if downloaded >= args.limit:
            break
        target = STATIC_DIR / LOCAL_TPL.format(slug=slug)
        if target.exists():
            counts['existing'] += 1
            continue
        if args.dry_run:
            counts['would_download'] += 1
            continue
        data = fetch_and_resize(src)
        if data is None:
            counts['failed'] += 1
            consec_fail += 1
            if consec_fail >= CONSECUTIVE_FAIL_BAIL:
                print(f'BAIL: {consec_fail} consecutive failures — likely IP-blocked')
                break
            time.sleep(SLEEP)
            continue
        consec_fail = 0
        target.write_bytes(data)
        downloaded += 1
        counts['downloaded'] += 1
        if downloaded % 50 == 0:
            print(f'  progress: downloaded={downloaded}, failed={counts["failed"]}')
        time.sleep(SLEEP)

    print(f'\nresult: downloaded={counts["downloaded"]} '
          f'existing={counts["existing"]} failed={counts["failed"]}')
    print(f'output dir: {out_dir}')

    # Gotcha #56 reminder: docker cp static dir + verify
    print(f'\nNext: docker cp + container verify:')
    print(f'  docker cp sites/{SITE}/static/{Path(LOCAL_TPL).parent} \\\n'
          f'      wh-r10:/opt/WebSyn/{SITE}/static/{Path(LOCAL_TPL).parent.parent}')
    print(f'  docker exec wh-r10 ls /opt/WebSyn/{SITE}/static/{Path(LOCAL_TPL).parent} | wc -l')


if __name__ == '__main__':
    main()
