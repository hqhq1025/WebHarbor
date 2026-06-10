#!/usr/bin/env python3
"""Extend IMDb titles via OMDB free key.

Target: 392 -> 1000+ titles
Source: OMDB (www.omdbapi.com) free key 'trilogy'
Strategy:
  1. Build tt_id candidate pool via OMDB search across (genre seed words x recent years).
  2. Dedup vs existing 392.
  3. Fetch detail by id, insert into titles + title_genre.
Skip: persons / credits (would require synthetic nm_ids).
"""
import sqlite3
import urllib.request
import urllib.parse
import json
import re
import time

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/imdb/instance/imdb.db'
KEY = 'trilogy'

# Seed search terms (broad, mostly genre-anchored words yielding diverse hits)
SEED_TERMS = [
    'love', 'war', 'man', 'last', 'star', 'dark', 'night', 'day', 'world',
    'life', 'king', 'house', 'city', 'time', 'home', 'fire', 'water',
    'ghost', 'space', 'final', 'shadow', 'silver', 'spider', 'super',
    'black', 'red', 'blue', 'lost', 'killer', 'father', 'mother', 'son',
    'mission', 'hunt', 'rise', 'fall', 'return', 'dream', 'secret', 'wild',
    'iron', 'wonder', 'first', 'great', 'avengers', 'hero',
]
YEARS = list(range(2010, 2026))

UA = 'Mozilla/5.0 WebHarbor-seed-bot/1.0'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:140]


def search_pool(existing_tt_ids, target=900):
    """Collect tt_ids via OMDB search until we have `target` new candidates."""
    pool = set()
    queries = []
    for term in SEED_TERMS:
        for y in YEARS:
            queries.append((term, y))
    # randomize search order to avoid burning OMDB on same term
    import random
    random.seed(20260528)
    random.shuffle(queries)
    n = 0
    for term, y in queries:
        if len(pool) >= target:
            break
        try:
            params = urllib.parse.urlencode({'s': term, 'y': y, 'type': 'movie', 'apikey': KEY})
            data = fetch('http://www.omdbapi.com/?' + params)
        except Exception as e:
            continue
        if data.get('Response') != 'True':
            continue
        for item in data.get('Search', []):
            tid = item.get('imdbID')
            if tid and tid not in existing_tt_ids and tid not in pool:
                pool.add(tid)
        n += 1
        if n % 25 == 0:
            print(f'  search progress: {n}/{len(queries)} queries, pool={len(pool)}')
        time.sleep(0.15)
    return list(pool)


def fetch_detail(tt_id):
    params = urllib.parse.urlencode({'i': tt_id, 'plot': 'full', 'apikey': KEY})
    return fetch('http://www.omdbapi.com/?' + params)


def parse_int(s):
    if not s or s in ('N/A', ''):
        return None
    try:
        return int(re.sub(r'[^0-9]', '', s))
    except Exception:
        return None


def parse_float(s):
    if not s or s in ('N/A', ''):
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_money(s):
    if not s or s in ('N/A', ''):
        return None
    try:
        return int(re.sub(r'[^0-9]', '', s))
    except Exception:
        return None


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    existing = {r[0] for r in cur.execute('SELECT tt_id FROM titles').fetchall()}
    before = len(existing)
    print(f'before: {before} titles')

    genre_map = {r[1]: r[0] for r in cur.execute('SELECT id, name FROM genres').fetchall()}

    target_new = 700
    candidates = search_pool(existing, target=target_new + 100)
    print(f'candidate pool: {len(candidates)}')

    added = 0
    for tt_id in candidates[: target_new + 200]:
        if added >= target_new:
            break
        try:
            d = fetch_detail(tt_id)
        except Exception:
            time.sleep(0.5)
            continue
        if d.get('Response') != 'True':
            continue
        title_type = (d.get('Type') or 'movie').lower()
        year_str = d.get('Year', '')
        ym = re.match(r'(\d{4})', year_str or '')
        year = int(ym.group(1)) if ym else None
        runtime = parse_int(d.get('Runtime'))
        poster = d.get('Poster') if d.get('Poster') and d['Poster'] != 'N/A' else ''
        plot = d.get('Plot') if d.get('Plot') != 'N/A' else ''
        primary_title = d.get('Title', '')
        if not primary_title:
            continue
        rating_avg = parse_float(d.get('imdbRating'))
        num_votes = parse_int(d.get('imdbVotes'))
        metascore = parse_int(d.get('Metascore'))
        box_world = parse_money(d.get('BoxOffice'))
        country = (d.get('Country') or '')[:80]
        language = (d.get('Language') or '')[:80]
        rated = (d.get('Rated') or '')[:10]
        release_date = (d.get('Released') or '')[:20]
        plot_short = plot[:500]

        try:
            cur.execute('''INSERT INTO titles
                (tt_id, title_type, primary_title, original_title, year, end_year,
                 runtime_min, mpaa_rating, plot_short, plot, rating_avg, num_votes,
                 metascore, popularity_rank, top_rank, box_office_us, box_office_world,
                 box_office_opening, budget, release_date, country, language,
                 poster_path, taglines_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (tt_id, title_type, primary_title, primary_title, year, None,
                 runtime, rated, plot_short, plot, rating_avg, num_votes,
                 metascore, None, None, None, box_world,
                 None, None, release_date, country, language,
                 poster, '[]'))
            new_title_id = cur.lastrowid
        except sqlite3.IntegrityError:
            continue

        # Map genres
        for g in (d.get('Genre') or '').split(', '):
            g = g.strip()
            gid = genre_map.get(g)
            if gid:
                try:
                    cur.execute('INSERT OR IGNORE INTO title_genre (title_id, genre_id) VALUES (?,?)',
                                (new_title_id, gid))
                except Exception:
                    pass
        added += 1
        if added % 50 == 0:
            print(f'  added {added}/{target_new}')
            con.commit()
        time.sleep(0.12)

    con.commit()
    after = cur.execute('SELECT COUNT(*) FROM titles').fetchone()[0]
    print(f'after: {after} (+{added})')
    con.close()


if __name__ == '__main__':
    main()
