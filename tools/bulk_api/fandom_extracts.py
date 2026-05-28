#!/usr/bin/env python3
"""Fill summary + image for Fandom articles via MediaWiki API.

Re-tested 2026-05-28: prior assumption that TextExtracts is unavailable was
half-right. `prop=extracts` is still NOT enabled, but:

  - `prop=pageimages` IS enabled → use for image thumbnails.
  - `action=parse&prop=text&section=0` IS enabled → parse first section HTML
    and pick the first real <p> outside infobox/notice/disambig tables.

Target: 1051 articles with NULL summary (350 each in harrypotter / gameofthrones
/ lotr, plus 1 in mcu). Image column was also NULL for those 1050.

Workflow:
  1. SELECT id, wiki_id, title from articles WHERE summary IS NULL OR summary=''
  2. Resolve wiki_id → wiki_slug.
  3. For each, call action=parse (summary) + prop=pageimages (image).
  4. UPDATE articles SET summary=?, image=? WHERE id=?; commit every 50.
  5. Mirror DB back into container + instance_seed.

Constraints (from operator note):
  - No docker restart (another audit may be running on wh-r10/fandom).
  - No git restore.
  - Don't fabricate — leave NULL when parsing fails.
  - Skip articles that already have a summary.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import requests
from lxml import html as lh

ROOT = Path('/home/v-haoqiwang/repos/WebHarbor/sites/fandom')
LOCAL_DB = ROOT / 'instance' / 'fandom.db'
SEED_DB = ROOT / 'instance_seed' / 'fandom.db'
CONTAINER = 'wh-r10'
CONTAINER_DB = '/opt/WebSyn/fandom/instance/fandom.db'
CONTAINER_SEED_DB = '/opt/WebSyn/fandom/instance_seed/fandom.db'

UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36 WebHarborBot/1.0')
HEADERS = {'User-Agent': UA}
SLEEP = 0.3
COMMIT_EVERY = 50
TIMEOUT = 20
MIN_SUMMARY = 60     # below this, treat as failed extraction
MAX_SUMMARY = 1200   # truncate at sentence boundary near this length


def fetch_section0_html(wiki: str, title: str) -> str | None:
    url = f'https://{wiki}.fandom.com/api.php'
    params = {
        'action': 'parse', 'page': title, 'prop': 'text', 'section': '0',
        'format': 'json', 'redirects': 1, 'disableeditsection': 1,
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        return f'__ERR__net:{e}'
    if r.status_code != 200:
        return f'__ERR__http:{r.status_code}'
    try:
        j = r.json()
    except ValueError:
        return '__ERR__json'
    if 'parse' not in j:
        # MediaWiki returns {"error":{"code":"missingtitle",...}} for missing page
        code = (j.get('error') or {}).get('code', 'no_parse')
        return f'__ERR__api:{code}'
    return j['parse']['text']['*']


def extract_first_paragraph(section_html: str) -> str | None:
    try:
        tree = lh.fromstring('<div>' + section_html + '</div>')
    except Exception:
        return None
    # Skip <p> nested inside layout chrome: infoboxes, notice banners,
    # disambig tables, asides, navboxes.
    xp = ('//p['
          'not(ancestor::table) and '
          'not(ancestor::aside) and '
          'not(ancestor::*[contains(@class,"portable-infobox")]) and '
          'not(ancestor::*[contains(@class,"notice")]) and '
          'not(ancestor::*[contains(@class,"navbox")]) and '
          'not(ancestor::*[contains(@class,"mw-collapsible")])'
          ']')
    for p in tree.xpath(xp):
        txt = ' '.join(p.text_content().split())
        if len(txt) >= MIN_SUMMARY:
            if len(txt) > MAX_SUMMARY:
                cut = txt.rfind('. ', 0, MAX_SUMMARY)
                txt = txt[:cut + 1] if cut > MIN_SUMMARY else txt[:MAX_SUMMARY]
            return txt
    return None


def fetch_pageimage(wiki: str, title: str) -> str | None:
    url = f'https://{wiki}.fandom.com/api.php'
    params = {
        'action': 'query', 'titles': title, 'prop': 'pageimages',
        'pithumbsize': 500, 'format': 'json', 'redirects': 1,
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        j = r.json()
    except ValueError:
        return None
    pages = (j.get('query') or {}).get('pages') or {}
    for _, p in pages.items():
        thumb = (p.get('thumbnail') or {}).get('source')
        if thumb:
            return thumb
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0,
                    help='Cap rows processed (0=all NULL).')
    ap.add_argument('--wiki', type=str, default=None,
                    help='Only one wiki slug.')
    ap.add_argument('--push', action='store_true',
                    help='After update, copy DB into container + seed dir.')
    args = ap.parse_args()

    con = sqlite3.connect(LOCAL_DB)
    cur = con.cursor()

    wikis = {}
    for wid, slug in cur.execute('SELECT id, slug FROM wikis'):
        wikis[wid] = slug

    sql = ("SELECT id, wiki_id, title FROM articles "
           "WHERE (summary IS NULL OR summary='') ")
    if args.wiki:
        wid = next((k for k, v in wikis.items() if v == args.wiki), None)
        if wid is None:
            print(f'unknown wiki slug {args.wiki!r}', file=sys.stderr)
            sys.exit(2)
        sql += f"AND wiki_id={wid} "
    sql += 'ORDER BY wiki_id, id'
    if args.limit > 0:
        sql += f' LIMIT {args.limit}'

    rows = cur.execute(sql).fetchall()
    total = len(rows)
    print(f'rows to fill: {total}', flush=True)

    n_summary = 0
    n_image = 0
    n_both = 0
    n_neither = 0
    fail_classes: dict[str, int] = {}
    pending = 0

    for i, (aid, wiki_id, title) in enumerate(rows, 1):
        slug = wikis.get(wiki_id)
        if not slug:
            continue

        html_or_err = fetch_section0_html(slug, title)
        summary = None
        if html_or_err and not html_or_err.startswith('__ERR__'):
            summary = extract_first_paragraph(html_or_err)
        else:
            cls = (html_or_err or '__ERR__none').split('__ERR__', 1)[-1][:30]
            fail_classes[f'parse:{cls}'] = fail_classes.get(f'parse:{cls}', 0) + 1

        image = fetch_pageimage(slug, title)

        if summary and image:
            n_both += 1
        elif summary:
            pass
        elif image:
            pass
        else:
            n_neither += 1
        if summary:
            n_summary += 1
        if image:
            n_image += 1

        cur.execute(
            'UPDATE articles SET summary=COALESCE(?,summary), '
            'image=COALESCE(?,image) WHERE id=?',
            (summary, image, aid))
        pending += 1

        if pending >= COMMIT_EVERY:
            con.commit()
            pending = 0
            print(f'  [{i}/{total}] commit. summary+={n_summary} '
                  f'image+={n_image} both={n_both} neither={n_neither}',
                  flush=True)

        time.sleep(SLEEP)

    if pending:
        con.commit()
    con.close()

    print('-' * 60)
    print(f'done. total={total}  summary+={n_summary} ({n_summary*100/max(total,1):.1f}%)  '
          f'image+={n_image} ({n_image*100/max(total,1):.1f}%)  '
          f'both={n_both}  neither={n_neither}')
    if fail_classes:
        print('failure classes:')
        for k, v in sorted(fail_classes.items(), key=lambda kv: -kv[1]):
            print(f'  {k}: {v}')

    if args.push:
        SEED_DB.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['cp', str(LOCAL_DB), str(SEED_DB)], check=True)
        subprocess.run(['docker', 'cp', str(LOCAL_DB),
                        f'{CONTAINER}:{CONTAINER_DB}'], check=True)
        subprocess.run(['docker', 'cp', str(LOCAL_DB),
                        f'{CONTAINER}:{CONTAINER_SEED_DB}'], check=True)
        print('pushed DB → instance_seed/ + container instance/ + container instance_seed/')


if __name__ == '__main__':
    main()
