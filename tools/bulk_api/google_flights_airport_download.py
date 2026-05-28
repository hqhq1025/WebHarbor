#!/usr/bin/env python3
"""Download-only resume helper for google_flights_airport_wiki.

Reads /tmp/gf_wiki/resolved_urls.json (produced by the main fetcher's
URL-resolution phase), then downloads each image from upload.wikimedia.org
at a slow polite rate. Writes to sites/google_flights/static/images/airports/
and updates airport.image in the live DB. Idempotent: skips files already
on disk.

Why a separate script? -- the main fetcher's URL-lookup phase burns through
the Wikipedia api.php rate-limit bucket. If the download phase then trips
upload.wikimedia.org 429's, the script has no way to resume without
re-doing all the api calls. This helper bypasses the entire api phase by
relying on the persisted resolved-URL cache.
"""
from __future__ import annotations

import io
import json
import sqlite3
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import assert_image_diversity  # noqa: E402

SITE_ROOT = Path('/home/v-haoqiwang/repos/WebHarbor/sites/google_flights')
DB_PATH = SITE_ROOT / 'instance' / 'google_flights.db'
IMG_DIR = SITE_ROOT / 'static' / 'images' / 'airports'
CACHE = Path('/tmp/gf_wiki/resolved_urls.json')

DOWNLOAD_UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
)
DL_SLEEP = 7.0          # polite spacing; manual tests show >=2.5s avoids 429
                         # but a banned upload session won't recover, so we go
                         # a bit more conservative on restarts.
DL_429_COOLDOWN = 60.0  # cap honoured Retry-After at 60s; sometimes server says 600
DL_429_CAP = 90.0       # never sleep longer than this; abort URL instead
DL_RETRIES = 1          # don't compound throttle; give up early on 429
INITIAL_WARMUP = 5.0    # short warmup; bucket already verified full
MIN_BYTES = 8 * 1024
MAX_DIM = 1600
JPEG_QUALITY = 85
TIMEOUT = 15

DL = requests.Session()
DL.headers['User-Agent'] = DOWNLOAD_UA


def _download_and_encode(url: str, dest: Path) -> tuple[bool, str]:
    host = urllib.parse.urlparse(url).netloc or '?'
    body: bytes | None = None
    for attempt in range(DL_RETRIES + 1):
        try:
            r = DL.get(url, timeout=TIMEOUT)
        except Exception:
            return False, host
        if r.status_code == 429:
            ra = r.headers.get('Retry-After')
            try:
                wait = float(ra) if ra else DL_429_COOLDOWN
            except ValueError:
                wait = DL_429_COOLDOWN
            wait = min(max(wait, DL_429_COOLDOWN), DL_429_CAP)
            print(f'    [429] sleeping {wait:.0f}s')
            time.sleep(wait)
            continue
        if r.status_code != 200 or len(r.content) < MIN_BYTES:
            return False, host
        body = r.content
        ctype = (r.headers.get('content-type') or '').lower()
        if not any(t in ctype for t in ('image/jpeg', 'image/png', 'image/webp', 'image/jpg')):
            head = body[:8]
            if not (head[:3] == b'\xff\xd8\xff'
                    or head[:8] == b'\x89PNG\r\n\x1a\n'
                    or (head[:4] == b'RIFF' and body[8:12] == b'WEBP')):
                return False, host
        break
    if body is None:
        return False, host
    try:
        img = Image.open(io.BytesIO(body)).convert('RGB')
        img.thumbnail((MAX_DIM, MAX_DIM))
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, 'JPEG', quality=JPEG_QUALITY, optimize=True)
    except Exception:
        return False, host
    return True, host


def main() -> int:
    if not CACHE.exists():
        raise SystemExit(f'cache not found: {CACHE} (run google_flights_airport_wiki.py first)')
    cache: dict[int, str] = {int(k): v for k, v in json.loads(CACHE.read_text()).items() if v}
    print(f'cache: {len(cache)} resolved URLs')

    con = sqlite3.connect(str(DB_PATH))
    id_to_iata = dict(con.execute(
        'SELECT id, iata FROM airport WHERE id IN ({})'.format(
            ','.join('?' * len(cache))), list(cache.keys())).fetchall())
    print(f'db: matched {len(id_to_iata)} aids')

    ok = miss = skip = 0
    domain_count: dict[str, int] = {}
    items = list(cache.items())
    print(f'warmup: sleeping {INITIAL_WARMUP:.0f}s so upload bucket has time to refill')
    time.sleep(INITIAL_WARMUP)
    for n, (aid, url) in enumerate(items, 1):
        iata = id_to_iata.get(aid)
        if not iata:
            miss += 1
            continue
        iata_lower = iata.lower()
        dest = IMG_DIR / f'{iata_lower}.jpg'
        rel = f'/static/images/airports/{iata_lower}.jpg'
        if dest.exists():
            con.execute('UPDATE airport SET image=? WHERE id=?', (rel, aid))
            skip += 1
            if (ok + skip) % 25 == 0:
                con.commit()
            continue
        success, host = _download_and_encode(url, dest)
        if success:
            domain_count[host] = domain_count.get(host, 0) + 1
            con.execute('UPDATE airport SET image=? WHERE id=?', (rel, aid))
            ok += 1
            if ok % 10 == 0:
                con.commit()
                print(f'  [{n}/{len(items)}] ok={ok} skip={skip} miss={miss}')
        else:
            miss += 1
        time.sleep(DL_SLEEP)

    con.commit()
    print()
    print(f'done: ok={ok} skipped_existing={skip} miss={miss} of {len(items)}')
    top = sorted(domain_count.items(), key=lambda kv: -kv[1])[:3]
    print('top 3 source domains:')
    for d, c in top:
        print(f'  {d}  {c}')

    assert_image_diversity(con, 'airport', 'image', threshold=0.05, min_rows=15)
    print('image diversity gate: PASS')
    con.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
