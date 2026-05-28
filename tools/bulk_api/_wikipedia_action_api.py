#!/usr/bin/env python3
"""Wikipedia MediaWiki action API helper — batched image + extract lookup.

Replaces single-entity REST `/page/summary/` calls. The action API:
  - accepts batched `titles=A|B|C|...` (up to 50 per call)
  - returns thumbnails via `pithumbsize=N` already pointing at /thumb/ (no 429)
  - follows redirects via `redirects=1` (so "Italian" auto → "Italian cuisine")
  - returns image URL + extract paragraph + page metadata in one query

Real impact (google_search topic 2026-05-28):
  Switched from REST (170/1323 fillable, hard-rate-limited) to action API:
  556/1323 backfilled (~48% of NULL candidates) — no rate-limit stall.

Use this for:
  - Bulk image lookup (>50 entities)
  - When entity names need redirect resolution
  - When you also want page extracts in same call

Don't use this for:
  - Single-entity lookups (REST `/page/summary/` is fine, 1 fewer URL roundtrip)
  - When you specifically need `originalimage` (action API gives only thumb)

Example:
    from _wikipedia_action_api import batched_image_lookup
    result = batched_image_lookup(
        ['Phoenix Suns', 'Italian cuisine', 'Chicken as food'],
        thumb_size=1280, ua='WebHarbor/1.0 (haoqiwang@msr)')
    # → {'Phoenix Suns': 'https://upload.wikimedia.org/.../thumb/.../1280px-...png',
    #    'Italian cuisine': '...', ...}
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, Optional


WIKI_API = 'https://en.wikipedia.org/w/api.php'
DEFAULT_UA = 'WebHarbor/1.0 (haoqiwang@msr)'

# Mozilla UA only for upload.wikimedia.org CDN downloads (different host).
# action API itself prefers polite WebHarbor UA — see scrape-real-images SKILL gotcha #1.
DOWNLOAD_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
               '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')


def _api_call(params: dict, ua: str, timeout: int = 15) -> dict:
    url = f'{WIKI_API}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = int(e.headers.get('Retry-After', '60') or '60')
                time.sleep(min(ra, 120))
                last_err = e
            else:
                last_err = e
                break
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f'action API failed: {last_err}')


def batched_image_lookup(titles: Iterable[str], *, thumb_size: int = 800,
                          ua: str = DEFAULT_UA, batch_size: int = 50,
                          sleep: float = 1.0) -> dict[str, Optional[str]]:
    """Look up thumbnail URL for many titles.

    Returns {title_as_passed: thumb_url_or_None}. Redirects are followed,
    so the returned key matches the title you passed in (not the redirect
    target). Missing pages → None.

    Cost: ~1 second per batch of 50 titles = 50 titles/sec.
    """
    titles = list(titles)
    out: dict[str, Optional[str]] = {t: None for t in titles}
    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'pageimages',
            'titles': '|'.join(batch),
            'pithumbsize': thumb_size,
            'redirects': '1',
        }
        try:
            payload = _api_call(params, ua)
        except RuntimeError:
            continue
        query = payload.get('query', {})
        # Map redirected target → original requested title
        rdmap = {r['to']: r['from'] for r in query.get('redirects', []) or []}
        for page in (query.get('pages') or {}).values():
            wikipedia_title = page.get('title')
            thumb = (page.get('thumbnail') or {}).get('source')
            if not thumb:
                continue
            requested = rdmap.get(wikipedia_title, wikipedia_title)
            if requested in out:
                out[requested] = thumb
        time.sleep(sleep)
    return out


def batched_summary_lookup(titles: Iterable[str], *, ua: str = DEFAULT_UA,
                            batch_size: int = 50, sleep: float = 1.0,
                            extract_chars: int = 600) -> dict[str, Optional[str]]:
    """Look up intro paragraph (extract) for many titles.

    Returns {title: plain_text_extract_or_None}. Uses TextExtracts.
    """
    titles = list(titles)
    out: dict[str, Optional[str]] = {t: None for t in titles}
    for i in range(0, len(titles), batch_size):
        batch = titles[i:i + batch_size]
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'extracts',
            'titles': '|'.join(batch),
            'exintro': '1',
            'explaintext': '1',
            'exchars': extract_chars,
            'redirects': '1',
        }
        try:
            payload = _api_call(params, ua)
        except RuntimeError:
            continue
        query = payload.get('query', {})
        rdmap = {r['to']: r['from'] for r in query.get('redirects', []) or []}
        for page in (query.get('pages') or {}).values():
            wikipedia_title = page.get('title')
            extract = page.get('extract')
            if not extract:
                continue
            requested = rdmap.get(wikipedia_title, wikipedia_title)
            if requested in out:
                out[requested] = extract
        time.sleep(sleep)
    return out


# ---------- entity-name rewriter heuristics ---------- #

import re

# Strip trailing query-style phrases that prevent Wikipedia title lookup.
# Real cases from google_search topic backfill:
#   "Phoenix Suns Latest Game Score" → "Phoenix Suns"
#   "iPhone AirDrop Over Web Requirements" → "iPhone AirDrop"
#   "Top Comedy Movies by User Ratings" → "Comedy Movies"
_QUERY_TAIL_PATTERNS = [
    r'\s+(latest|today|this\s+week|trending|recent)\s+(score|game|news|update)s?\b.*',
    r'\s+by\s+(user\s+)?(rating|score|popular|trend)s?\b.*',
    r'\s+(bio|biography|stats|statistics|wiki)\b.*',
    r'\s+(movie|film|tv|show)\s+(rating|score|review)s?\b.*',
    r'\s+(over|on)\s+(web|mobile|desktop)\s+\w+\b.*',
    r'\s+(top|best|worst)\s+\d+.*',
    r'^(top|best|trending|popular)\s+',
]


def strip_query_tail(name: str) -> str:
    """Strip trailing query-style phrases from a search query string.

    Returns the candidate Wikipedia entity title. If nothing matches, returns
    the input unchanged.
    """
    s = name.strip()
    for pat in _QUERY_TAIL_PATTERNS:
        s = re.sub(pat, '', s, flags=re.IGNORECASE).strip()
    return s


# Domain-specific candidate-title rewriters: try multiple variants in order.
# Returns list — caller hands these to batched_image_lookup and uses the
# first that resolves.
CUISINE_TO_WIKIPEDIA = {
    'italian': ['Italian cuisine'],
    'chinese': ['Chinese cuisine'],
    'mexican': ['Mexican cuisine'],
    'french': ['French cuisine'],
    'japanese': ['Japanese cuisine'],
    'indian': ['Indian cuisine'],
    'thai': ['Thai cuisine'],
    'mediterranean': ['Mediterranean cuisine'],
    'greek': ['Greek cuisine'],
    'korean': ['Korean cuisine'],
}

FOOD_TYPE_TO_WIKIPEDIA = {
    'chicken': ['Chicken as food', 'Chicken'],
    'desserts': ['Dessert'],
    'salads': ['Salad'],
    'soups': ['Soup'],
    'breads': ['Bread'],
    'pastas': ['Pasta'],
    'pizzas': ['Pizza'],
}


def candidate_titles(name: str) -> list[str]:
    """Generate Wikipedia-title candidates for a search/category name.

    Domain hints come from CUISINE_TO_WIKIPEDIA, FOOD_TYPE_TO_WIKIPEDIA, etc.
    Falls back to: original name, name stripped of trailing query, capitalized
    singular form.
    """
    base = strip_query_tail(name)
    out: list[str] = [base]
    lc = base.lower()
    if lc in CUISINE_TO_WIKIPEDIA:
        out = CUISINE_TO_WIKIPEDIA[lc] + out
    elif lc in FOOD_TYPE_TO_WIKIPEDIA:
        out = FOOD_TYPE_TO_WIKIPEDIA[lc] + out
    # plural → singular common form
    if lc.endswith('s') and not lc.endswith('ss'):
        out.append(base[:-1])
    # de-dup while preserving order
    seen = set()
    deduped = []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            deduped.append(t)
    return deduped


if __name__ == '__main__':
    # Quick smoke test
    titles = ['Phoenix Suns', 'Italian cuisine', 'Algebra', 'Nonexistentpage12345']
    print('image lookup:')
    for k, v in batched_image_lookup(titles).items():
        print(f'  {k!r:30s} → {v}')
    print('\nentity strip:')
    for name in ['Phoenix Suns Latest Game Score', 'iPhone AirDrop Over Web Requirements',
                 'Top 10 Comedy Movies by Rating']:
        print(f'  {name!r:50s} → {strip_query_tail(name)!r}')
    print('\ncandidate titles for "Italian":', candidate_titles('Italian'))
    print('candidate titles for "Chicken":', candidate_titles('Chicken'))
