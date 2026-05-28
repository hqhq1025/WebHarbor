#!/usr/bin/env python3
"""Extend Allrecipes recipes by scraping category-listing + recipe pages.

Target: 31114 recipes / 54 categories (already saturated; this script is
reproducibility reference). Allrecipes has no public JSON API, so we walk
the A-Z categorical index and pull each recipe's JSON-LD Recipe schema.

Pitfalls already hit:
  - JSON-LD on a recipe page may be a list (`@graph`) or a single object;
    handle both. Inside, the entity we want has @type == 'Recipe' (or list
    containing 'Recipe').
  - Some recipes have only a thumb on the listing card — full image is
    inside the recipe page's JSON-LD `image` field (str or {url} or list).
  - recipeIngredient is a flat list of strings.
  - recipeCuisine, recipeYield, prepTime, totalTime can each be a LIST or
    a dict, not a plain string. Use `_to_str()` before slicing into DB
    columns or sqlite will raise `type 'list' is not supported`.
  - datePublished is ISO-8601, sometimes missing.
  - Cloudflare bot-management (cf-bm cookie) escalates from 200 -> 403 ->
    402 within minutes of moderate scraping from a single IP. Re-using
    the cf_bm cookie from the first response via cookiejar keeps the
    session alive longer; once blocked, wait ~30min or rotate IP.
  - 1.0s between recipe pages and 0.5s between listing pages keeps us
    under their radar for the initial window.
"""
from __future__ import annotations
import http.cookiejar
import json
import re
import sys
import time
import datetime as dt
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import slugify, open_db, insert_or_ignore, periodic_commit, upsert_count, UA  # noqa: E402

INDEX_URL = 'https://www.allrecipes.com/recipes-a-z-6735880'
JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
RECIPE_HREF_RE = re.compile(r'href="(https://www\.allrecipes\.com/recipe/(\d+)/[a-z0-9\-]+/?)"')
CATEGORY_HREF_RE = re.compile(r'href="(https://www\.allrecipes\.com/recipes/(\d+)/[a-z0-9\-]+/?)"')

MAX_NEW = 800  # absolute cap to keep one run bounded

# Persistent cookie jar — keeps Cloudflare cf_bm + AKA cookies across reqs,
# so we survive longer before CF flips us into 402/403.
_COOKIE_JAR = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_COOKIE_JAR))


def fetch_html(url: str, retries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.allrecipes.com/',
        })
        try:
            with _OPENER.open(req, timeout=20) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(0.8 * (2 ** attempt))
    raise RuntimeError(f'fetch failed after {retries} retries: {url} :: {last}')

INDEX_URL = 'https://www.allrecipes.com/recipes-a-z-6735880'
JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
RECIPE_HREF_RE = re.compile(r'href="(https://www\.allrecipes\.com/recipe/(\d+)/[a-z0-9\-]+/?)"')
CATEGORY_HREF_RE = re.compile(r'href="(https://www\.allrecipes\.com/recipes/(\d+)/[a-z0-9\-]+/?)"')

MAX_NEW = 800  # absolute cap to keep one run bounded


def extract_jsonld(html: bytes) -> list[dict]:
    out: list[dict] = []
    for m in JSONLD_RE.finditer(html.decode('utf-8', 'replace')):
        blob = m.group(1).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        if isinstance(data, list):
            out.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            if '@graph' in data and isinstance(data['@graph'], list):
                out.extend(d for d in data['@graph'] if isinstance(d, dict))
            else:
                out.append(data)
    return out


def _is_recipe(node: dict) -> bool:
    t = node.get('@type')
    if isinstance(t, list):
        return 'Recipe' in t
    return t == 'Recipe'


def _to_image(val) -> str | None:
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get('url')
    if isinstance(val, list) and val:
        return _to_image(val[0])
    return None


def _to_minutes(iso_dur) -> int | None:
    if not iso_dur:
        return None
    if isinstance(iso_dur, list):
        iso_dur = iso_dur[0] if iso_dur else None
    if not isinstance(iso_dur, str):
        return None
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', iso_dur)
    if not m:
        return None
    h = int(m.group(1) or 0)
    mn = int(m.group(2) or 0)
    return h * 60 + mn or None


def _to_str(val) -> str:
    """Coerce schema.org fields that may be list/dict/str into a flat string."""
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return ', '.join(_to_str(v) for v in val if v)
    if isinstance(val, dict):
        return str(val.get('@value') or val.get('name') or val.get('text') or '')
    return str(val)


def main():
    con = open_db('allrecipes')
    cur = con.cursor()
    before = upsert_count(con, 'recipe')
    print(f'before: {before} recipes')
    existing_slugs = {r[0] for r in cur.execute('SELECT slug FROM recipe')}

    # Step 1: harvest category URLs from the A-Z index
    try:
        index_html = fetch_html(INDEX_URL).decode('utf-8', 'replace')
    except Exception as e:
        print(f'A-Z index unreachable ({e}). DB unchanged.')
        con.close()
        return
    cat_urls = sorted({m.group(1) for m in CATEGORY_HREF_RE.finditer(index_html)})
    print(f'categories: {len(cat_urls)}')

    # Step 2: harvest recipe URLs across categories (page 1 only — listing
    # pages are heavy and we mostly look for *new* ids vs the saturated DB).
    recipe_urls: list[str] = []
    for cu in cat_urls[:80]:
        try:
            html = fetch_html(cu).decode('utf-8', 'replace')
        except Exception:
            continue
        for m in RECIPE_HREF_RE.finditer(html):
            recipe_urls.append(m.group(1))
        time.sleep(0.5)
        if len(recipe_urls) >= 4000:
            break
    # Dedup, preserve order
    seen_u: set[str] = set()
    recipe_urls = [u for u in recipe_urls if not (u in seen_u or seen_u.add(u))]
    print(f'recipe url pool: {len(recipe_urls)}')

    # Pick the first unknown-slug recipes to fetch in detail
    candidate_urls = []
    for u in recipe_urls:
        # slug is the trailing path segment
        slug_match = re.search(r'/recipe/\d+/([a-z0-9\-]+)/?', u)
        if not slug_match:
            continue
        slug = slugify(slug_match.group(1), maxlen=200)
        if slug in existing_slugs:
            continue
        candidate_urls.append((u, slug))
        if len(candidate_urls) >= MAX_NEW:
            break
    print(f'new candidates: {len(candidate_urls)}')

    added = 0
    for url, slug in candidate_urls:
        try:
            html = fetch_html(url)
        except Exception:
            time.sleep(1.0)
            continue
        nodes = extract_jsonld(html)
        recipe = next((n for n in nodes if _is_recipe(n)), None)
        if recipe is None:
            continue
        title = (recipe.get('name') or '').strip()
        if not title:
            continue
        author_val = recipe.get('author')
        if isinstance(author_val, list) and author_val:
            author_val = author_val[0]
        author = (author_val or {}).get('name') if isinstance(author_val, dict) else (author_val or '')
        ingredients = recipe.get('recipeIngredient') or []
        if not isinstance(ingredients, list):
            ingredients = []
        instructions = recipe.get('recipeInstructions') or []
        instr_texts: list[str] = []
        for ins in instructions if isinstance(instructions, list) else []:
            if isinstance(ins, str):
                instr_texts.append(ins)
            elif isinstance(ins, dict):
                instr_texts.append(ins.get('text') or ins.get('name') or '')
        row = {
            'title': _to_str(title)[:200],
            'slug': slug,
            'description': _to_str(recipe.get('description'))[:1000],
            'category_id': None,
            'cuisine': (_to_str(recipe.get('recipeCuisine'))[:100]) or None,
            'image': _to_image(recipe.get('image')),
            'prep_time': _to_str(recipe.get('prepTime')) or None,
            'cook_time': _to_str(recipe.get('cookTime')) or None,
            'total_time': _to_str(recipe.get('totalTime')) or None,
            'servings': _to_str(recipe.get('recipeYield'))[:20] or None,
            'ingredients_json': json.dumps(ingredients),
            'instructions_json': json.dumps(instr_texts),
            'nutrition_json': json.dumps(recipe.get('nutrition') or {}),
            'tags_json': '[]',
            'gallery_json': '[]',
            'is_featured': 0,
            'is_editors_pick': 0,
            'avg_rating': float((recipe.get('aggregateRating') or {}).get('ratingValue') or 0) or None,
            'review_count': int((recipe.get('aggregateRating') or {}).get('ratingCount') or 0) or None,
            'author_name': _to_str(author)[:100] or None,
            'prep_time_mins': _to_minutes(recipe.get('prepTime')),
            'cook_time_mins': _to_minutes(recipe.get('cookTime')),
            'total_time_mins': _to_minutes(recipe.get('totalTime')),
            'ingredient_count': len(ingredients) or None,
            'created_at': dt.datetime.utcnow(),
        }
        if insert_or_ignore(con, 'recipe', row) is not None:
            added += 1
            existing_slugs.add(slug)
            periodic_commit(con, added, every=50)
        time.sleep(1.0)

    con.commit()
    after = upsert_count(con, 'recipe')
    print(f'after: {after} recipes (+{added})')
    con.close()


if __name__ == '__main__':
    main()
