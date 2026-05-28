#!/usr/bin/env python3
"""Extend Fandom articles via MediaWiki allpages API.

Target: 183 -> 1000+ articles by adding 3 new wikis on top of mcu/starwars/genshin.
Source: https://<wiki>.fandom.com/api.php?action=query&list=allpages

Constraints (from operator note 2026-05-28):
- Fandom container may still be serving 500 (sprites_inline issue) — another
  agent is fixing templates. We MUST NOT docker restart and MUST NOT touch
  templates here. We touch only the DB.
- Live DB lives inside wh-r10 at /opt/WebSyn/fandom/instance/fandom.db.
  There's no sites/fandom/instance/ locally — we docker cp out, modify,
  docker cp back. The DB cp is safe (no schema or template change).
- TextExtracts and PageImages extensions are NOT enabled on Fandom mediawiki,
  so we cannot pull summary/image from the API; leave NULL and let phase 5b
  fill images from Wikipedia / fandom thumbs later.
"""
from __future__ import annotations
import sqlite3
import subprocess
import sys
import time
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import fetch_json  # noqa: E402

CONTAINER = 'wh-r10'
CONTAINER_DB = '/opt/WebSyn/fandom/instance/fandom.db'
LOCAL_DIR = Path('/home/v-haoqiwang/repos/WebHarbor/sites/fandom/instance')
LOCAL_DB = LOCAL_DIR / 'fandom.db'

# New wikis to add. (slug, name, tagline, accent).
NEW_WIKIS = [
    ('harrypotter',    'Harry Potter Wiki',     'The Harry Potter encyclopedia',         '#7B1B2C'),
    ('gameofthrones',  'A Wiki of Ice and Fire','The unofficial Game of Thrones wiki',   '#1F3A5F'),
    ('lotr',           'The One Wiki to Rule Them All', 'The Lord of the Rings wiki',    '#3B5A30'),
]

PER_WIKI_TARGET = 350           # adds up to 1050 across 3 wikis
APLIMIT = 500                    # MediaWiki allpages cap
SLEEP = 0.3


def _pull_db():
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['docker', 'cp', f'{CONTAINER}:{CONTAINER_DB}', str(LOCAL_DB)],
        check=True)


def _push_db():
    subprocess.run(
        ['docker', 'cp', str(LOCAL_DB), f'{CONTAINER}:{CONTAINER_DB}'],
        check=True)


def _ensure_wiki(cur, slug, name, tagline, accent):
    row = cur.execute('SELECT id FROM wikis WHERE slug=?', (slug,)).fetchone()
    if row:
        return row[0]
    cur.execute(
        'INSERT INTO wikis (slug, name, tagline, hero_image, accent, '
        'description, featured_article_slug, article_count, page_count, '
        'discussion_count, members_count) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (slug, name, tagline, None, accent, None, None, 0, 0, 0, 0))
    return cur.lastrowid


def _harvest(wiki_slug):
    """Pull up to PER_WIKI_TARGET (title, pageid) pairs from a Fandom wiki."""
    base = f'https://{wiki_slug}.fandom.com/api.php'
    apfrom = None
    out = []
    while len(out) < PER_WIKI_TARGET:
        url = (f'{base}?action=query&list=allpages&aplimit={APLIMIT}'
               f'&apnamespace=0&format=json&apfilterredir=nonredirects')
        if apfrom:
            import urllib.parse as up
            url += '&apfrom=' + up.quote(apfrom)
        try:
            payload = fetch_json(url)
        except Exception as e:
            print(f'  fetch fail for {wiki_slug} at apfrom={apfrom!r}: {e}')
            break
        pages = (payload.get('query') or {}).get('allpages') or []
        if not pages:
            break
        for p in pages:
            out.append((p.get('title') or '', int(p.get('pageid') or 0)))
        cont = payload.get('continue') or {}
        nxt = cont.get('apcontinue')
        if not nxt:
            break
        apfrom = nxt
        time.sleep(SLEEP)
    return out[:PER_WIKI_TARGET]


def main():
    print(f'pulling DB from {CONTAINER}:{CONTAINER_DB}')
    _pull_db()
    con = sqlite3.connect(str(LOCAL_DB))
    cur = con.cursor()
    before = cur.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
    before_wikis = cur.execute('SELECT COUNT(*) FROM wikis').fetchone()[0]
    print(f'before: articles={before} wikis={before_wikis}')

    added = 0
    for wiki_slug, name, tagline, accent in NEW_WIKIS:
        wiki_id = _ensure_wiki(cur, wiki_slug, name, tagline, accent)
        existing = {r[0] for r in cur.execute(
            'SELECT slug FROM articles WHERE wiki_id=?', (wiki_id,))}
        print(f'{wiki_slug}: wiki_id={wiki_id}, harvesting up to {PER_WIKI_TARGET}')
        pages = _harvest(wiki_slug)
        wiki_added = 0
        now = dt.datetime.utcnow()
        for title, pageid in pages:
            if not title:
                continue
            slug = title.replace(' ', '_')[:240]
            if slug in existing:
                continue
            existing.add(slug)
            try:
                cur.execute(
                    'INSERT OR IGNORE INTO articles '
                    '(wiki_id, title, slug, summary, content, infobox_kind, '
                    'infobox_json, image, created_at, updated_at, view_count, '
                    'is_featured, namespace) '
                    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (wiki_id, title[:240], slug, None, None, None,
                     None, None, now, now, 0, 0, 'main'))
            except sqlite3.IntegrityError:
                continue
            if cur.rowcount:
                wiki_added += 1
                added += 1
                if added % 50 == 0:
                    con.commit()
        cur.execute('UPDATE wikis SET article_count=(SELECT COUNT(*) FROM articles WHERE wiki_id=?) '
                    'WHERE id=?', (wiki_id, wiki_id))
        con.commit()
        print(f'  {wiki_slug}: +{wiki_added}')

    con.commit()
    after = cur.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
    after_wikis = cur.execute('SELECT COUNT(*) FROM wikis').fetchone()[0]
    print(f'after: articles={after} (+{added}) wikis={after_wikis}')
    con.close()

    print(f'pushing DB back to {CONTAINER}:{CONTAINER_DB}')
    _push_db()
    print('done (no docker restart).')


if __name__ == '__main__':
    main()
