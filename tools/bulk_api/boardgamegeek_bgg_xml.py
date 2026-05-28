#!/usr/bin/env python3
"""Extend BoardGameGeek games via BGG XML API v2.

Target: 5669 games / 2880 people / 80 categories (already saturated;
this script is reproducibility reference).
Source:
  - Hot list:   https://boardgamegeek.com/xmlapi2/hot?type=boardgame
  - Detail:     https://boardgamegeek.com/xmlapi2/thing?id=<i,j,...>&stats=1

Pitfalls already hit:
  - 2026-05 BREAKING: BGG XML API now requires Bearer auth
    (`WWW-Authenticate: Bearer realm="xml api"`). All unauthenticated
    requests return HTTP 401 from both boardgamegeek.com and api.geekdo.com.
    Set env var `BGG_BEARER=<token>` to enable; otherwise this script logs
    the auth-required state and exits cleanly without mutating the DB.
  - BGG queues large `thing?id=` batches and returns 202 with Retry-After
    (when auth works); treat as not-ready, sleep, re-fetch.
  - XML, not JSON: use xml.etree.ElementTree.
  - <name> elements: pick the one with type="primary".
  - One game can have multiple boardgamedesigner / boardgameartist /
    boardgamecategory <link> entries.
"""
from __future__ import annotations
import os
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import (  # noqa: E402
    fetch, slugify, open_db, insert_or_ignore, periodic_commit, upsert_count,
)

API = 'https://boardgamegeek.com/xmlapi2'
BATCH = 20  # ids per /thing? request
BEARER = os.environ.get('BGG_BEARER')
AUTH_HEADERS = {'Authorization': f'Bearer {BEARER}'} if BEARER else {}


def fetch_xml(url: str, max_poll: int = 6) -> ET.Element:
    """Fetch XML; if BGG returns 202 (queued), poll until ready."""
    for attempt in range(max_poll):
        raw = fetch(url, headers=AUTH_HEADERS)
        # BGG returns <message>...please try again</message> when queued.
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            time.sleep(2.0)
            continue
        if root.tag == 'message' or root.find('message') is not None:
            time.sleep(2.0 + attempt)
            continue
        return root
    raise RuntimeError(f'BGG never returned a ready XML for {url}')


def parse_int(s):
    try:
        return int(s) if s not in (None, '', '0') else None
    except Exception:
        return None


def main():
    con = open_db('boardgamegeek')
    cur = con.cursor()
    before_games = upsert_count(con, 'games')
    before_people = upsert_count(con, 'people')
    before_cats = upsert_count(con, 'categories')
    print(f'before: games={before_games} people={before_people} categories={before_cats}')

    existing_games = {r[0] for r in cur.execute('SELECT bgg_id FROM games')}
    existing_people = {r[0] for r in cur.execute('SELECT bgg_id FROM people WHERE bgg_id IS NOT NULL')}
    existing_cats = {r[0] for r in cur.execute('SELECT bgg_id FROM categories WHERE bgg_id IS NOT NULL')}

    # Hot list -> candidate bgg_ids
    try:
        hot = fetch_xml(f'{API}/hot?type=boardgame')
    except (urllib.error.HTTPError, RuntimeError) as e:
        # 2026-05: BGG XML API requires Bearer auth — see module docstring.
        print(f'BGG hot list unreachable ({e}). '
              f'Set BGG_BEARER env var to enable. DB unchanged.')
        con.close()
        return
    hot_ids = [int(item.get('id')) for item in hot.findall('item')]
    print(f'hot list: {len(hot_ids)} entries')
    new_ids = [i for i in hot_ids if i not in existing_games]
    print(f'new candidates: {len(new_ids)}')

    added_g = added_p = added_c = 0
    for i in range(0, len(new_ids), BATCH):
        batch = new_ids[i:i + BATCH]
        url = f'{API}/thing?id={",".join(map(str, batch))}&stats=1'
        try:
            root = fetch_xml(url)
        except Exception as e:
            print(f'  batch {i//BATCH} failed: {e}')
            continue
        for item in root.findall('item'):
            bgg_id = int(item.get('id'))
            name_el = next((n for n in item.findall('name') if n.get('type') == 'primary'), None)
            if name_el is None or not name_el.get('value'):
                continue
            name = name_el.get('value')
            year_el = item.find('yearpublished')
            stats = item.find('statistics/ratings') if item.find('statistics') is not None else None
            avg = stats.find('average').get('value') if stats is not None and stats.find('average') is not None else None
            bayes = stats.find('bayesaverage').get('value') if stats is not None and stats.find('bayesaverage') is not None else None
            weight_el = stats.find('averageweight') if stats is not None else None
            row = {
                'bgg_id': bgg_id,
                'name': name,
                'slug': slugify(name, maxlen=200),
                'subtype': item.get('type') or 'boardgame',
                'year_published': parse_int(year_el.get('value') if year_el is not None else None),
                'minplayers': parse_int(item.find('minplayers').get('value') if item.find('minplayers') is not None else None),
                'maxplayers': parse_int(item.find('maxplayers').get('value') if item.find('maxplayers') is not None else None),
                'minplaytime': parse_int(item.find('minplaytime').get('value') if item.find('minplaytime') is not None else None),
                'maxplaytime': parse_int(item.find('maxplaytime').get('value') if item.find('maxplaytime') is not None else None),
                'minage': parse_int(item.find('minage').get('value') if item.find('minage') is not None else None),
                'short_description': (item.findtext('description') or '')[:500],
                'description_html': item.findtext('description') or '',
                'image_filename': None,
                'thumb_filename': None,
                'avg_rating': float(avg) if avg else None,
                'bayes_average': float(bayes) if bayes else None,
                'weight': float(weight_el.get('value')) if weight_el is not None and weight_el.get('value') else None,
                'featured': 1,
            }
            new_gid = insert_or_ignore(con, 'games', row)
            if new_gid is None:
                continue
            added_g += 1
            # Link designers / artists / categories
            for link in item.findall('link'):
                ltype = link.get('type')
                lid = parse_int(link.get('id'))
                lname = link.get('value') or ''
                if not lid or not lname:
                    continue
                if ltype in ('boardgamedesigner', 'boardgameartist'):
                    if lid not in existing_people:
                        pid = insert_or_ignore(con, 'people', {
                            'bgg_id': lid, 'name': lname, 'slug': slugify(lname, maxlen=180),
                        })
                        if pid is not None:
                            added_p += 1
                            existing_people.add(lid)
                    person_row = cur.execute('SELECT id FROM people WHERE bgg_id=?', (lid,)).fetchone()
                    if person_row:
                        tbl = 'game_designers' if ltype == 'boardgamedesigner' else 'game_artists'
                        insert_or_ignore(con, tbl, {'game_id': new_gid, 'person_id': person_row[0]})
                elif ltype == 'boardgamecategory':
                    if lid not in existing_cats:
                        cid = insert_or_ignore(con, 'categories', {
                            'bgg_id': lid, 'name': lname, 'slug': slugify(lname, maxlen=110),
                        })
                        if cid is not None:
                            added_c += 1
                            existing_cats.add(lid)
                    cat_row = cur.execute('SELECT id FROM categories WHERE bgg_id=?', (lid,)).fetchone()
                    if cat_row:
                        insert_or_ignore(con, 'game_categories', {'game_id': new_gid, 'category_id': cat_row[0]})
            periodic_commit(con, added_g, every=20)
        con.commit()
        time.sleep(2.0)  # BGG asks for ~2s between thing? calls

    con.commit()
    print(f'after: games={upsert_count(con, "games")} (+{added_g}) '
          f'people={upsert_count(con, "people")} (+{added_p}) '
          f'categories={upsert_count(con, "categories")} (+{added_c})')
    con.close()


if __name__ == '__main__':
    main()
