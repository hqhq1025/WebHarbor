#!/usr/bin/env python3
"""Fill allrecipes.category.image NULLs from Wikipedia REST summary.

54/54 rows NULL. Names are food categories like 'Italian', 'Vegetarian',
'Chicken', 'Dinner', 'Desserts'. Map to plausible Wikipedia titles
(e.g. 'Italian' -> 'Italian cuisine', 'Chicken' -> 'Chicken as food',
'Desserts' -> 'Dessert') with a short ordered-title-attempt list.
Pull thumbnail.source. Same Mozilla download UA + 8 KB filter as
google_search_topic_wiki.py.
"""
from __future__ import annotations
import json
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

SITE = 'allrecipes'
DB_PATH = Path(f'/home/v-haoqiwang/repos/WebHarbor/sites/{SITE}/instance/{SITE}.db')
IMG_DIR = Path(f'/home/v-haoqiwang/repos/WebHarbor/sites/{SITE}/static/images/categories_wiki')
WEB_PREFIX = '/static/images/categories_wiki'

API_UA = 'WebHarbor/1.0 (haoqiwang@msr)'
DOWNLOAD_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
               'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36')
SLEEP = 0.3
MIN_BYTES = 8 * 1024
TIMEOUT = 15


def http_get(url: str, ua: str, timeout: int = TIMEOUT,
             retries_on_429: int = 4) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    delay = 2.0
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


def candidate_titles(name: str) -> list[str]:
    """Ordered list of Wikipedia titles to try for a food-category name."""
    n = (name or '').strip()
    if not n:
        return []
    base = n
    seen: list[str] = []

    def add(t: str) -> None:
        t = t.strip()
        if t and t not in seen:
            seen.append(t)

    low = base.lower()
    # Cuisine-style (Italian, Mexican, Asian, Mediterranean, ...)
    cuisine_words = ('italian', 'mexican', 'chinese', 'japanese', 'korean',
                     'thai', 'indian', 'french', 'greek', 'mediterranean',
                     'asian', 'american', 'cuban', 'german', 'spanish',
                     'middle eastern', 'british', 'caribbean', 'african',
                     'irish', 'vietnamese', 'turkish', 'lebanese')
    if low in cuisine_words:
        add(f'{base} cuisine')

    # Cleanup '&' and 'and'
    cleaned = re.sub(r'\s*&\s*', ' and ', base)
    # Split on '&'/'and' and try first half
    parts = re.split(r'\s+and\s+|\s*&\s*', base)
    first = parts[0].strip() if parts else base

    # Direct attempts
    add(base)
    if cleaned != base:
        add(cleaned)
    if first and first != base:
        add(first)

    # Domain-specific rewrites
    rewrites = {
        'breakfast & brunch': ['Breakfast', 'Brunch'],
        'breakfast and brunch': ['Breakfast', 'Brunch'],
        'dinner': ['Dinner', 'Meal'],
        'lunch': ['Lunch'],
        'appetizers & snacks': ['Appetizer', 'Hors d\'oeuvre'],
        'appetizers and snacks': ['Appetizer'],
        'desserts': ['Dessert'],
        'dessert': ['Dessert'],
        'chicken': ['Chicken as food'],
        'beef': ['Beef'],
        'pork': ['Pork'],
        'seafood': ['Seafood'],
        'fish': ['Fish as food'],
        'vegetarian': ['Vegetarianism'],
        'vegan': ['Veganism'],
        'gluten free': ['Gluten-free diet'],
        'gluten-free': ['Gluten-free diet'],
        'keto': ['Ketogenic diet'],
        'paleo': ['Paleolithic diet'],
        'low carb': ['Low-carbohydrate diet'],
        'low-carb': ['Low-carbohydrate diet'],
        'salads': ['Salad'],
        'salad': ['Salad'],
        'soups': ['Soup'],
        'soup': ['Soup'],
        'stews': ['Stew'],
        'pasta': ['Pasta'],
        'pizza': ['Pizza'],
        'sandwiches': ['Sandwich'],
        'sandwich': ['Sandwich'],
        'burgers': ['Hamburger'],
        'burger': ['Hamburger'],
        'tacos': ['Taco'],
        'taco': ['Taco'],
        'bbq': ['Barbecue'],
        'barbecue & grilling': ['Barbecue'],
        'grilling': ['Grilling'],
        'baking': ['Baking'],
        'breads': ['Bread'],
        'bread': ['Bread'],
        'cakes': ['Cake'],
        'cake': ['Cake'],
        'cookies': ['Cookie'],
        'cookie': ['Cookie'],
        'pies': ['Pie'],
        'pie': ['Pie'],
        'ice cream': ['Ice cream'],
        'drinks': ['Drink'],
        'beverages': ['Drink'],
        'cocktails': ['Cocktail'],
        'smoothies': ['Smoothie'],
        'side dishes': ['Side dish'],
        'sides': ['Side dish'],
        'sauces & condiments': ['Sauce', 'Condiment'],
        'sauces and condiments': ['Sauce', 'Condiment'],
        'sauces': ['Sauce'],
        'condiments': ['Condiment'],
        'main dishes': ['Main course'],
        'entrees': ['Main course'],
        'casseroles': ['Casserole'],
        'slow cooker': ['Slow cooker'],
        'instant pot': ['Instant Pot'],
        'air fryer': ['Air fryer'],
        'holidays': ['Holiday'],
        'thanksgiving': ['Thanksgiving dinner'],
        'christmas': ['Christmas dinner'],
        'easter': ['Easter food'],
        'halloween': ['Halloween'],
        'fourth of july': ['Independence Day (United States)'],
        'kid-friendly': ['Children\'s food'],
        'kids': ['Children\'s food'],
        'healthy': ['Healthy diet'],
        'quick & easy': ['Cooking'],
        'quick and easy': ['Cooking'],
        'one pot': ['One-pot synthesis'],  # likely miss; fallback to 'Stew' below
        'comfort food': ['Comfort food'],
        'snacks': ['Snack'],
        'snack': ['Snack'],
        'dairy-free': ['Milk allergy', 'Dairy product'],
        'dairy free': ['Milk allergy', 'Dairy product'],
        'whole30': ['Whole30'],
        'low-gi': ['Glycemic index'],
        'low gi': ['Glycemic index'],
        'easter': ['Easter food', 'Easter'],
        "valentine's day": ["Valentine's Day"],
        'valentines day': ["Valentine's Day"],
        '4th of july': ['Independence Day (United States)'],
        'breads': ['Bread'],
        'pastries': ['Pastry'],
        'middle eastern': ['Middle Eastern cuisine'],
        'african': ['African cuisine'],
        'caribbean': ['Caribbean cuisine'],
    }
    for v in rewrites.get(low, []):
        add(v)

    # generic '<X> dish' / '<X> (food)' / '<X> cuisine'
    add(f'{base} (food)')
    add(f'{base} dish')
    return seen


def wiki_summary_thumb(name: str) -> tuple[str | None, str | None]:
    """Return (thumb_url, title_used) or (None, None).

    Uses MediaWiki action API `prop=pageimages` (REST `/page/summary/` is
    rate-limited on this host). Walks the candidate title list until one
    page returns a thumbnail.
    """
    for title in candidate_titles(name):
        params = urllib.parse.urlencode({
            'action': 'query',
            'prop': 'pageimages|pageprops',
            'titles': title.replace(' ', '_'),
            'format': 'json',
            'pithumbsize': 1280,
            'redirects': 1,
        })
        url = f'https://en.wikipedia.org/w/api.php?{params}'
        status, body, _ = http_get(url, API_UA)
        time.sleep(SLEEP)
        if status != 200 or not body:
            continue
        try:
            data = json.loads(body)
        except Exception:
            continue
        pages = ((data.get('query') or {}).get('pages') or {})
        for _, page in pages.items():
            if (page.get('pageprops') or {}).get('disambiguation') is not None:
                continue
            thumb = page.get('thumbnail') or {}
            src = thumb.get('source')
            if not src:
                continue
            return re.sub(r'/\d+px-', '/1280px-', src), title
    return None, None


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
        'SELECT id, name FROM category '
        'WHERE (image IS NULL OR image = "") '
        'ORDER BY id'
    ).fetchall()
    total = cur.execute('SELECT COUNT(*) FROM category').fetchone()[0]
    print(f'before: total={total}, null candidates={len(rows)}')

    updated = miss_api = miss_dl = too_small = 0
    used_slugs: set[str] = set()
    for rid, name in rows:
        src, title_used = wiki_summary_thumb(name)
        if not src:
            print(f'  miss api: id={rid} name={name!r}')
            miss_api += 1
            continue
        status, content, ctype = http_get(src, DOWNLOAD_UA)
        if status != 200 or len(content) < MIN_BYTES:
            if status == 200 and content:
                too_small += 1
                print(f'  too small: id={rid} name={name!r} ({len(content)} B)')
            else:
                miss_dl += 1
                print(f'  miss dl: id={rid} name={name!r} status={status}')
            continue
        slug = slugify(name) or f'category-{rid}'
        if slug in used_slugs:
            slug = f'{slug}-{rid}'
        used_slugs.add(slug)
        ext = ext_for(ctype, src)
        out_path = IMG_DIR / f'{slug}{ext}'
        out_path.write_bytes(content)
        web_path = f'{WEB_PREFIX}/{slug}{ext}'
        con.execute('UPDATE category SET image = ? WHERE id = ?', (web_path, rid))
        updated += 1
        print(f'  ok: id={rid} name={name!r} -> {title_used!r} ({len(content) // 1024} KB)')
    con.commit()

    after_filled = cur.execute(
        'SELECT COUNT(*) FROM category WHERE image IS NOT NULL AND image != ""'
    ).fetchone()[0]
    print(f'after: total={total} filled={after_filled} '
          f'newly_updated={updated} miss_api={miss_api} miss_dl={miss_dl} too_small={too_small}')

    import collections
    new_rows = [r[0] for r in con.execute(
        'SELECT image FROM category WHERE image IS NOT NULL AND image != ""'
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
