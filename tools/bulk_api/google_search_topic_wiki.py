#!/usr/bin/env python3
"""Fill google_search.topic.hero_image NULLs from Wikipedia REST summary.

Strategy:
- 1153/1323 rows have hero_image NULL. Names are real entities
  (movies, athletes, teams, products, places).
- For each NULL row: GET en.wikipedia.org/api/rest_v1/page/summary/<name>
  -> thumbnail.source. Download with Mozilla UA (upload.wikimedia.org 403s
  on bot UA — scrape-real-images gotcha #1).
- Save to sites/google_search/static/images/topics_wiki/<slug>.<ext>,
  store path as /static/images/topics_wiki/<slug>.<ext>.
- Reject < 8 KB (favicon/pixel — scrape-real-images gotcha #5).
- No Tavily fallback. Miss -> leave NULL.
"""
from __future__ import annotations
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import slugify  # noqa: E402

SITE = 'google_search'
DB_PATH = Path(f'/home/v-haoqiwang/repos/WebHarbor/sites/{SITE}/instance/{SITE}.db')
IMG_DIR = Path(f'/home/v-haoqiwang/repos/WebHarbor/sites/{SITE}/static/images/topics_wiki')
WEB_PREFIX = '/static/images/topics_wiki'

API_UA = 'WebHarbor/1.0 (haoqiwang@msr)'
DOWNLOAD_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
               'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36')
SLEEP = 1.0          # 1 req/s — be polite, MediaWiki shared-IP limits bite hard
DL_SLEEP = 0.4       # space out upload.wikimedia.org fetches
MIN_BYTES = 8 * 1024
TIMEOUT = 15


def http_get(url: str, ua: str, timeout: int = TIMEOUT,
             retries_on_429: int = 4) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    delay = 8.0
    for attempt in range(retries_on_429 + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), r.headers.get('Content-Type', '')
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries_on_429:
                time.sleep(delay)
                delay *= 2
                continue
            return e.code, b'', ''
        except Exception:
            return 0, b'', ''
    return 0, b'', ''


BATCH_TITLES = 12  # 12 originals x ~4 candidates = ~48 titles per request


# Suffixes commonly appended in google_search topic queries that we strip
# to recover the underlying Wikipedia entity. Order matters: longer first.
_STRIP_SUFFIXES = [
    'latest game score', 'most recent game', 'current game',
    'latest news', 'latest update', 'latest commit', 'latest post',
    'upcoming projects', 'upcoming games', 'upcoming releases',
    'bio', 'biography', 'wiki', 'wikipedia',
    'movie ratings', 'movie scores', 'movie review', 'movie reviews',
    'game scores', 'score',
    'current air quality', 'air quality', 'air pollution',
    'elevation', 'altitude', 'population', 'gdp',
    'most touchdowns season', 'most goals season',
    'most recent', 'most popular', 'most played', 'most watched',
    'top 10 songs', 'top 5 movies', 'top 3 players',
    'children', 'kids', 'family',
    'mac requirements', 'requirements',
    'github latest commit', 'github commits', 'github stars',
    'login', 'sign in', 'sign up',
    'reddit community', 'twitter account', 'instagram',
    'world record', 'world records', 'records',
    'final recent', 'recent final', 'final',
    'global top 50', 'top 50', 'top 100', 'top 200',
    'differences', 'comparison', 'vs', 'versus',
    'release date', 'release year', 'release',
    'box office', 'gross', 'earnings',
    'home stadium', 'stadium', 'arena', 'court',
    'roster', 'lineup', 'team',
    'official site', 'official website', 'website',
]


def entity_extract(name: str) -> list[str]:
    """Return ordered candidate Wikipedia titles for a search-query-style name.

    Heuristic: strip trailing descriptive phrases until what remains looks like
    a named entity (e.g. 'Phoenix Suns Latest Game Score' -> 'Phoenix Suns').
    Always also keeps the original name as a candidate.
    """
    cands: list[str] = []

    def add(c: str) -> None:
        c = re.sub(r'\s+', ' ', c).strip(' .,-:')
        if c and c not in cands:
            cands.append(c)

    base = (name or '').strip()
    if not base:
        return []
    add(base)

    low = base.lower()
    for suf in _STRIP_SUFFIXES:
        if low.endswith(' ' + suf):
            stripped = base[: len(base) - len(suf)].rstrip(' -:,.')
            if stripped and stripped.lower() != low:
                add(stripped)
                low = stripped.lower()
                base = stripped

    # if base has multiple tokens, also try first-3 / first-2 (gives "Phoenix Suns")
    parts = base.split()
    if len(parts) > 3:
        add(' '.join(parts[:3]))
    if len(parts) > 2:
        add(' '.join(parts[:2]))
    return cands[:4]  # cap to keep batches small


def wiki_thumb_batch(names: list[str]) -> dict[str, str]:
    """Resolve a batch of names -> {original_name: thumb_url}.

    For each `name` in `names`, try the candidates returned by
    `entity_extract(name)` in order; the first batch hit wins. We send all
    requested candidate titles as one MediaWiki `titles=A|B|C` query.
    """
    if not names:
        return {}
    # Map every candidate title back to the originals that requested it.
    cand_to_origs: dict[str, list[str]] = {}
    orig_to_cands: dict[str, list[str]] = {}
    for n in names:
        if not n:
            continue
        cands = entity_extract(n)
        orig_to_cands[n] = cands
        for c in cands:
            cand_to_origs.setdefault(c.replace(' ', '_'), []).append(n)
    if not cand_to_origs:
        return {}
    params = urllib.parse.urlencode({
        'action': 'query',
        'prop': 'pageimages|pageprops',
        'titles': '|'.join(cand_to_origs.keys()),
        'format': 'json',
        'pithumbsize': 1280,
        'redirects': 1,
    })
    url = f'https://en.wikipedia.org/w/api.php?{params}'
    status, body, _ = http_get(url, API_UA)
    if status != 200 or not body:
        return {}
    try:
        import json
        data = json.loads(body)
    except Exception:
        return {}
    query = data.get('query') or {}

    # Build alias map from sent title (with underscores) to candidate string
    alias: dict[str, str] = {}
    for k in cand_to_origs:
        alias[k] = k.replace('_', ' ')
        alias[k.replace('_', ' ')] = k.replace('_', ' ')
    for entry in query.get('normalized', []) or []:
        src, dst = entry.get('from'), entry.get('to')
        if src in alias:
            alias[dst] = alias[src]
    for entry in query.get('redirects', []) or []:
        src, dst = entry.get('from'), entry.get('to')
        if src in alias:
            alias[dst] = alias[src]

    # Best thumb per candidate string (humanized)
    cand_thumb: dict[str, str] = {}
    for _, page in (query.get('pages') or {}).items():
        page_title = page.get('title') or ''
        if (page.get('pageprops') or {}).get('disambiguation') is not None:
            continue
        thumb = (page.get('thumbnail') or {}).get('source')
        if not thumb:
            continue
        cand = alias.get(page_title) or alias.get(page_title.replace(' ', '_')) or page_title
        cand_thumb[cand] = re.sub(r'/\d+px-', '/1280px-', thumb)

    # For each original, pick the first candidate (in priority order) that hit
    out: dict[str, str] = {}
    for orig, cands in orig_to_cands.items():
        for c in cands:
            t = cand_thumb.get(c) or cand_thumb.get(c.replace('_', ' '))
            if t:
                out[orig] = t
                break
    return out


# Backwards-compatible single-name helper (unused by main() now)
def wiki_summary_thumb(name: str) -> str | None:
    return wiki_thumb_batch([name]).get(name)


def ext_for(content_type: str, fallback_url: str) -> str:
    ct = (content_type or '').lower()
    if 'jpeg' in ct or 'jpg' in ct:
        return '.jpg'
    if 'png' in ct:
        return '.png'
    if 'webp' in ct:
        return '.webp'
    if 'svg' in ct:
        return '.svg'
    # infer from URL
    low = fallback_url.lower()
    for e in ('.jpg', '.jpeg', '.png', '.webp', '.svg'):
        if low.endswith(e):
            return '.jpg' if e == '.jpeg' else e
    return '.jpg'


def main() -> int:
    if not DB_PATH.exists():
        print(f'DB not found: {DB_PATH}', file=sys.stderr)
        return 2
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    rows = cur.execute(
        'SELECT id, name FROM topic '
        'WHERE (hero_image IS NULL OR hero_image = "") '
        'ORDER BY id'
    ).fetchall()
    total = cur.execute('SELECT COUNT(*) FROM topic').fetchone()[0]
    print(f'before: total={total}, null candidates={len(rows)}')

    updated = miss_api = miss_dl = too_small = 0
    used_slugs: set[str] = set()

    # Process in batches of BATCH_TITLES to cut API request count ~25x
    by_id: dict[int, str] = {rid: name for rid, name in rows if name}
    rid_list = [rid for rid, name in rows if name]
    miss_api += sum(1 for rid, name in rows if not name)

    for i in range(0, len(rid_list), BATCH_TITLES):
        chunk_ids = rid_list[i : i + BATCH_TITLES]
        chunk_names = [by_id[rid] for rid in chunk_ids]
        thumbs = wiki_thumb_batch(chunk_names)
        time.sleep(SLEEP)
        for rid, name in zip(chunk_ids, chunk_names):
            src = thumbs.get(name)
            if not src:
                miss_api += 1
                continue
            status, content, ctype = http_get(src, DOWNLOAD_UA)
            time.sleep(DL_SLEEP)
            if status != 200 or len(content) < MIN_BYTES:
                if status == 200 and content:
                    too_small += 1
                else:
                    miss_dl += 1
                continue
            slug = slugify(name) or f'topic-{rid}'
            if slug in used_slugs:
                slug = f'{slug}-{rid}'
            used_slugs.add(slug)
            ext = ext_for(ctype, src)
            out_path = IMG_DIR / f'{slug}{ext}'
            out_path.write_bytes(content)
            web_path = f'{WEB_PREFIX}/{slug}{ext}'
            con.execute('UPDATE topic SET hero_image = ? WHERE id = ?', (web_path, rid))
            updated += 1
        con.commit()
        print(f'  batch done at id={chunk_ids[-1]}: updated={updated} '
              f'miss_api={miss_api} miss_dl={miss_dl} too_small={too_small}',
              flush=True)
    con.commit()

    after_filled = cur.execute(
        'SELECT COUNT(*) FROM topic WHERE hero_image IS NOT NULL AND hero_image != ""'
    ).fetchone()[0]
    print(f'after: total={total} filled={after_filled} '
          f'newly_updated={updated} miss_api={miss_api} miss_dl={miss_dl} too_small={too_small}')

    # diversity gate on the newly filled column
    import collections
    new_rows = [r[0] for r in con.execute(
        'SELECT hero_image FROM topic WHERE hero_image IS NOT NULL AND hero_image != ""'
    )]
    if len(new_rows) >= 15:
        top_url, top_n = collections.Counter(new_rows).most_common(1)[0]
        ratio = top_n / len(new_rows)
        print(f'diversity: top {top_n}/{len(new_rows)} = {ratio:.1%} ({top_url})')
        assert ratio < 0.05, f'diversity gate fail {ratio:.1%}'

    con.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
