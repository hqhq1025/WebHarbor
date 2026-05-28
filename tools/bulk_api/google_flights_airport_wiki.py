#!/usr/bin/env python3
"""Fill google_flights.airport.image from Wikipedia (batched api.php).

State: airport.image is NULL for 8523/8618 rows (~99 %). This script scrapes
Wikipedia for the canonical photo / lead image of each airport and writes a
per-airport JPG to `static/images/airports/<iata_lower>.jpg`.

Why batched api.php rather than REST? -- cloud-VM IP shares a tight Wikipedia
rate-limit bucket (~10 burst then ~0.4 req/s sustained). Sequential REST
calls saturate after ~10 hits and trigger escalating Retry-After's. The
batch `action=query&prop=pageimages&titles=A|B|C|...|Z` accepts up to 50
titles per call and returns each title's thumbnail in one shot, slashing
call count ~50x.

Strategy
--------
1. Pick the best-guess title per airport (name+" Airport", name, city+" Airport", iata+" Airport").
2. Batch 50 titles per query -- one HTTP call per 50 airports.
3. Multi-pass: for each variant, batch the remaining unresolved airports
   until the variant list is exhausted.
4. Reject SVG-rendered thumbs (Wikipedia infoboxes often surface logos);
   ditto for any URL matching logo/flag/map tokens.
5. Validate downloaded image: HTTP 200, >= 8 KB, image content-type.
6. Re-encode to JPEG <= 1600 px, quality 85.

UA discipline (scrape-real-images skill gotcha #1):
  API_UA       = 'WebHarbor/1.0 (haoqiwang@msr)'
  DOWNLOAD_UA  = Mozilla 5.0 (upload.wikimedia.org 403's on bot UA)

Limits
------
- 1000 airports per run (is_popular DESC, iata ASC).
- 2.5 s between api.php calls (1 batch == 50 airports, so effective per-airport sleep is tiny).
- 0.4 s between image downloads (upload.wikimedia.org separate bucket).
- 8 KB byte floor.

Idempotent: airports already present on disk are re-linked into the DB without re-downloading.

Run::

    .venv/bin/python3 tools/bulk_api/google_flights_airport_wiki.py
"""
from __future__ import annotations

import io
import re
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

API_UA = 'WebHarbor/1.0 (haoqiwang@msr)'
DOWNLOAD_UA = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
)

LIMIT = 1000
BATCH_SIZE = 50              # api.php caps titles at 50 per request
API_SLEEP = 2.5              # cloud-VM IP saturates Wikipedia bucket near ~0.4 req/s
DL_SLEEP = 2.5               # upload.wikimedia.org 429's hard at <1 req/s sustained
SEARCH_FALLBACK_BUDGET = 0   # search calls per run; the per-IP rate limit on
                              # `list=search` is much tighter than `prop=pageimages`,
                              # so we skip it. Use REST variants only.
MIN_BYTES = 8 * 1024
MAX_DIM = 1600
JPEG_QUALITY = 85
TIMEOUT = 15
DL_RETRIES = 4               # transient 429's on upload.wikimedia.org
DL_429_COOLDOWN = 20.0       # min cool-down on a 429 from upload CDN

# Cache resolved {aid: url} between runs so download-phase 429's don't waste
# our Wikipedia-API budget when we resume.
RESOLVED_CACHE_PATH = Path('/tmp/gf_wiki/resolved_urls.json')

API_SESSION = requests.Session()
API_SESSION.headers['User-Agent'] = API_UA
DL_SESSION = requests.Session()
DL_SESSION.headers['User-Agent'] = DOWNLOAD_UA

_SVG_LOGO_TOKENS = ('logo', 'flag_of', 'coat_of_arms', 'location_map',
                    'locator', 'wappen', 'seal_of')


def _looks_like_photo(url: str) -> bool:
    """Reject Wikipedia SVG-rendered thumbs (logos / maps / flags)."""
    lower = url.lower()
    if '.svg.png' in lower or lower.endswith('.svg'):
        return False
    if any(tok in lower for tok in _SVG_LOGO_TOKENS):
        return False
    return True


def _bump_thumb_width(url: str, width: int = 1280) -> str:
    return re.sub(r'/\d+px-', f'/{width}px-', url)


def _api_get(params: dict, *, retries: int = 4) -> dict | None:
    """GET https://en.wikipedia.org/w/api.php with backoff on 429."""
    base = 'https://en.wikipedia.org/w/api.php'
    url = base + '?' + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(retries + 1):
        try:
            r = API_SESSION.get(url, timeout=TIMEOUT)
        except Exception as e:
            print(f'    api error {e!r}')
            return None
        if r.status_code == 429:
            ra = r.headers.get('Retry-After')
            try:
                wait = float(ra) if ra else 30.0
            except ValueError:
                wait = 30.0
            wait = max(wait, 30.0) + 5.0
            print(f'    [429] sleeping {wait:.0f}s (attempt {attempt+1}/{retries+1})')
            time.sleep(wait)
            continue
        if r.status_code != 200:
            return None
        try:
            return r.json()
        except Exception:
            return None
    return None


def _title_variants(name: str | None, city: str | None, iata: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(t: str | None):
        if not t:
            return
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(t)

    if name:
        if 'airport' not in name.lower():
            add(f'{name} Airport')
            add(f'{name} International Airport')
        add(name)
    if city:
        add(f'{city} Airport')
        add(f'{city} International Airport')
        if name and 'airport' not in name.lower():
            # Wikipedia often titles like "Amsterdam Airport Schiphol"
            add(f'{city} Airport {name}')
            # or "<City>-<Name> Airport" (Malaga-Costa del Sol Airport)
            add(f'{city}-{name} Airport')
    add(f'{iata} Airport')
    return out


def _batch_pageimages(titles: list[str]) -> dict[str, str | None]:
    """Return {requested_title: thumb_url or None} for up to BATCH_SIZE titles.

    Honors Wikipedia title normalization + redirects, so a request for
    `Heathrow_Airport` may surface as `Heathrow Airport` in the response.
    We map back via the `normalized` + `redirects` arrays.
    """
    result: dict[str, str | None] = {t: None for t in titles}
    if not titles:
        return result
    js = _api_get({
        'action': 'query',
        'prop': 'pageimages|description',
        'piprop': 'thumbnail',
        'pithumbsize': 1280,
        'titles': '|'.join(titles),
        'redirects': 1,
        'format': 'json',
    })
    time.sleep(API_SLEEP)
    if not js:
        return result

    # Build a chain: requested -> normalized -> redirect target
    chain: dict[str, str] = {}
    for nm in (js.get('query', {}).get('normalized') or []):
        chain[nm['from']] = nm['to']
    for rd in (js.get('query', {}).get('redirects') or []):
        # apply on top of normalized -- need to compose
        chain_src = rd['from']
        chain[chain_src] = rd['to']

    # Build canonical title -> page mapping
    pages = (js.get('query', {}).get('pages') or {})
    title_to_thumb: dict[str, str | None] = {}
    title_to_desc: dict[str, str] = {}
    for _, page in pages.items():
        t = page.get('title')
        if not t:
            continue
        thumb = (page.get('thumbnail') or {}).get('source')
        title_to_thumb[t] = thumb
        title_to_desc[t] = (page.get('description') or '').lower()

    def resolve(req: str) -> str:
        seen = set()
        cur = req
        while cur in chain and cur not in seen:
            seen.add(cur)
            cur = chain[cur]
        return cur

    for req in titles:
        canon = resolve(req)
        thumb = title_to_thumb.get(canon)
        if not thumb:
            continue
        desc = title_to_desc.get(canon, '')
        # Confirm the page is about an airport (defends against
        # title collisions like "Malaga-Costa del Sol" -> the comarca).
        if 'airport' not in desc and 'airfield' not in desc and 'aerodrome' not in desc:
            continue
        if not _looks_like_photo(thumb):
            continue
        result[req] = _bump_thumb_width(thumb, 1280)
    return result


def _mediawiki_search_first(query: str) -> str | None:
    """Single MediaWiki search; return top hit title (for last-resort lookup)."""
    js = _api_get({
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': 1,
        'srnamespace': 0,
        'format': 'json',
    })
    time.sleep(API_SLEEP)
    if not js:
        return None
    hits = (js.get('query', {}).get('search') or [])
    return hits[0]['title'] if hits else None


def _download_and_encode(url: str, dest: Path) -> tuple[bool, str]:
    host = urllib.parse.urlparse(url).netloc or '?'
    body: bytes | None = None
    for attempt in range(DL_RETRIES + 1):
        try:
            r = DL_SESSION.get(url, timeout=TIMEOUT)
        except Exception:
            return False, host
        if r.status_code == 429:
            ra = r.headers.get('Retry-After')
            try:
                wait = float(ra) if ra else DL_429_COOLDOWN
            except ValueError:
                wait = DL_429_COOLDOWN
            # Server's Retry-After is often 1s (too short for bucket refill).
            wait = max(wait, DL_429_COOLDOWN)
            time.sleep(wait)
            continue
        if r.status_code != 200:
            return False, host
        if len(r.content) < MIN_BYTES:
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


def _load_resolved_cache() -> dict[int, str]:
    if not RESOLVED_CACHE_PATH.exists():
        return {}
    try:
        import json
        data = json.loads(RESOLVED_CACHE_PATH.read_text())
        # JSON keys are strings -- coerce back to int aid
        return {int(k): v for k, v in data.items() if v}
    except Exception:
        return {}


def _save_resolved_cache(resolved: dict[int, str]) -> None:
    import json
    RESOLVED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = RESOLVED_CACHE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps({str(k): v for k, v in resolved.items()}))
    tmp.replace(RESOLVED_CACHE_PATH)


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f'DB not found: {DB_PATH}')
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(DB_PATH))
    rows = con.execute(
        'SELECT id, iata, name, city, country '
        'FROM airport '
        "WHERE image IS NULL OR image = '' "
        'ORDER BY is_popular DESC, iata ASC '
        f'LIMIT {LIMIT}'
    ).fetchall()
    total = len(rows)
    print(f'targets: {total} airports (cap {LIMIT})')

    # Pre-link airports whose file already exists on disk.
    updated = 0
    by_id: dict[int, tuple[str, str | None, str, str | None]] = {}
    pending: list[int] = []
    variants_per_id: dict[int, list[str]] = {}
    for aid, iata, name, city, country in rows:
        iata_lower = (iata or '').lower()
        dest = IMG_DIR / f'{iata_lower}.jpg'
        rel = f'/static/images/airports/{iata_lower}.jpg'
        if dest.exists():
            con.execute('UPDATE airport SET image=? WHERE id=?', (rel, aid))
            updated += 1
            continue
        by_id[aid] = (iata, name, city, country)
        variants_per_id[aid] = _title_variants(name, city, iata)
        pending.append(aid)
    con.commit()
    print(f'pre-linked {updated} idempotent; new lookups needed for {len(pending)}')

    # Resume any URL resolution work that survived a prior killed run.
    resolved: dict[int, str] = {}
    cache = _load_resolved_cache()
    if cache:
        for aid in list(pending):
            if aid in cache:
                resolved[aid] = cache[aid]
        # Trim pending to those still needing API lookup
        pending = [a for a in pending if a not in resolved]
        print(f'cache: pre-loaded {len(resolved)} resolved URLs from prior run; '
              f'{len(pending)} still need API lookup')

    # Multi-pass batched lookup: pass k uses variant[k] for all still-unresolved airports.
    max_variants = max((len(v) for v in variants_per_id.values()), default=0)
    for pass_idx in range(max_variants):
        if not pending:
            break
        batch_titles: list[str] = []
        title_to_aids: dict[str, list[int]] = {}
        for aid in pending:
            vs = variants_per_id[aid]
            if pass_idx >= len(vs):
                continue
            t = vs[pass_idx]
            batch_titles.append(t)
            title_to_aids.setdefault(t, []).append(aid)
        if not batch_titles:
            continue

        print(f'pass {pass_idx+1}: {len(batch_titles)} titles to lookup '
              f'({len(pending)} airports still unresolved)')
        # Chunk by BATCH_SIZE
        all_results: dict[str, str | None] = {}
        # api.php dedupes within a single batch, so pre-dedupe.
        unique = sorted(set(batch_titles))
        for i in range(0, len(unique), BATCH_SIZE):
            chunk = unique[i:i+BATCH_SIZE]
            res = _batch_pageimages(chunk)
            all_results.update(res)
            hits = sum(1 for v in res.values() if v)
            print(f'  chunk {i//BATCH_SIZE+1}: +{hits}/{len(chunk)} hits')

        # Apply results
        still_pending: list[int] = []
        for aid in pending:
            vs = variants_per_id[aid]
            if pass_idx >= len(vs):
                # No more variants for this aid -> leave for search fallback
                still_pending.append(aid)
                continue
            t = vs[pass_idx]
            url = all_results.get(t)
            if url:
                resolved[aid] = url
            else:
                still_pending.append(aid)
        pending = still_pending

    print(f'after REST variants: resolved={len(resolved)}, still_pending={len(pending)}')

    # Persist resolved URLs so a killed download phase can resume without
    # redoing the entire API lookup (Wikipedia rate-limits us hard).
    _save_resolved_cache(resolved)
    print(f'resolved-URL cache saved to {RESOLVED_CACHE_PATH}')

    # Search fallback (one query per remaining airport) -- bounded by
    # SEARCH_FALLBACK_BUDGET so we don't burn 30+ min on long-tail IATAs
    # that almost certainly have no Wikipedia article anyway.
    search_resolved = 0
    if pending:
        budget = min(SEARCH_FALLBACK_BUDGET, len(pending))
        targets = pending[:budget]
        print(f'search fallback: {budget}/{len(pending)} airports '
              f'(budget cap; rest will stay NULL)')
        search_target_titles: list[str] = []
        aid_to_search_title: dict[int, str] = {}
        for n_done, aid in enumerate(targets, 1):
            iata, name, city, country = by_id[aid]
            q = f'{name} airport {city}' if (name and city) else (name or f'{iata} airport')
            title = _mediawiki_search_first(q)
            if title:
                aid_to_search_title[aid] = title
                search_target_titles.append(title)
            if n_done % 20 == 0:
                print(f'  search {n_done}/{budget} ({len(search_target_titles)} hits)')
        unique = sorted(set(search_target_titles))
        title_url: dict[str, str | None] = {}
        for i in range(0, len(unique), BATCH_SIZE):
            chunk = unique[i:i+BATCH_SIZE]
            res = _batch_pageimages(chunk)
            title_url.update(res)
        for aid, title in aid_to_search_title.items():
            url = title_url.get(title)
            if url and aid not in resolved:
                resolved[aid] = url
                search_resolved += 1
        print(f'  search resolved {search_resolved}/{budget}')

    print(f'about to download {len(resolved)} images...')

    misses = total - updated - len(resolved)
    domain_count: dict[str, int] = {}
    downloaded = 0
    skipped_existing = 0
    pending_urls = list(resolved.items())
    for n, (aid, url) in enumerate(pending_urls, 1):
        iata = by_id[aid][0]
        iata_lower = iata.lower()
        dest = IMG_DIR / f'{iata_lower}.jpg'
        rel = f'/static/images/airports/{iata_lower}.jpg'
        # Mid-run resume: file may already exist from a prior killed run.
        if dest.exists():
            con.execute('UPDATE airport SET image=? WHERE id=?', (rel, aid))
            updated += 1
            skipped_existing += 1
            if (downloaded + skipped_existing) % 25 == 0:
                con.commit()
            continue
        ok, host = _download_and_encode(url, dest)
        if not ok:
            misses += 1
            time.sleep(DL_SLEEP)
            continue
        domain_count[host] = domain_count.get(host, 0) + 1
        con.execute('UPDATE airport SET image=? WHERE id=?', (rel, aid))
        downloaded += 1
        updated += 1
        if downloaded % 10 == 0:
            con.commit()
            print(f'  download {n}/{len(pending_urls)}: ok={downloaded} '
                  f'skip_existing={skipped_existing} miss={misses}')
        time.sleep(DL_SLEEP)

    con.commit()
    print()
    print(f'done: updated={updated} downloaded_new={downloaded} '
          f'skipped_existing={skipped_existing} misses={misses} of {total}')
    top_domains = sorted(domain_count.items(), key=lambda kv: -kv[1])[:3]
    print('top 3 source domains:')
    for d, c in top_domains:
        print(f'  {d}  {c}')

    assert_image_diversity(con, 'airport', 'image', threshold=0.05, min_rows=15)
    print('image diversity gate: PASS')
    con.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
