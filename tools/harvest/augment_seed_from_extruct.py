"""Augment mirror DBs with REAL upstream metadata extracted from harvest extruct.json.

Reads /datadrive/harvest/snapshots/<site>/<route>/extruct.json (JSON-LD / microdata /
RDFa / OpenGraph) and INSERT-OR-UPDATEs corresponding rows in each site's
instance/<site>.db so synthetic seed data carries a few real anchor entities.

Design notes:
- Per-site dispatch (see SITE_HANDLERS at bottom). One CLI entrypoint per spec.
- Existing rows matched by upstream unique key (tt_id / slug / bgg_id / ...) are
  UPDATEd field-by-field; missing rows are INSERTed via raw INSERT OR REPLACE.
- We touch only top-level entity tables — no FK fan-out (cast/credits/etc.) to
  keep diffs small and reversible.
- After write, `cp instance/<db> instance_seed/<db>` is left to the caller (or
  invoke with --copy-to-seed). md5 check is logged.

Spec source: ~/webvoyager-analysis/CLAUDE.md (current task).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

HARVEST_ROOT = Path('/datadrive/harvest/snapshots')
REPO_ROOT = Path(__file__).resolve().parents[2]
SITES_ROOT = REPO_ROOT / 'sites'


# ---------------- helpers ----------------

def _load_extruct(site_dir: str) -> dict[str, dict[str, Any]]:
    """Return {route_name: extruct_payload} for every route with extruct.json."""
    out: dict[str, dict[str, Any]] = {}
    base = HARVEST_ROOT / site_dir
    if not base.is_dir():
        return out
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        ex = entry / 'extruct.json'
        if not ex.is_file():
            continue
        try:
            out[entry.name] = json.loads(ex.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f'  WARN: failed to parse {ex}: {exc}', file=sys.stderr)
    return out


def _clean(s: str | None) -> str | None:
    if not s:
        return s
    return html.unescape(s).strip()


def _iso_duration_to_min(d: str | None) -> int | None:
    """PT2H22M → 142, PT45M → 45."""
    if not d or not isinstance(d, str):
        return None
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d)
    if not m:
        return None
    h, mn, se = (int(g or 0) for g in m.groups())
    total = h * 60 + mn + (1 if se >= 30 else 0)
    return total or None


def _open_db(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys=OFF')
    return conn


def _set_fields(conn: sqlite3.Connection, table: str, where: dict[str, Any],
                updates: dict[str, Any]) -> int:
    updates = {k: v for k, v in updates.items() if v is not None}
    if not updates:
        return 0
    cols = ', '.join(f'{k}=?' for k in updates)
    wcols = ' AND '.join(f'{k}=?' for k in where)
    args = list(updates.values()) + list(where.values())
    cur = conn.execute(f'UPDATE {table} SET {cols} WHERE {wcols}', args)
    return cur.rowcount


def _row_exists(conn: sqlite3.Connection, table: str, where: dict[str, Any]) -> bool:
    wcols = ' AND '.join(f'{k}=?' for k in where)
    cur = conn.execute(f'SELECT 1 FROM {table} WHERE {wcols} LIMIT 1',
                       list(where.values()))
    return cur.fetchone() is not None


def _next_id(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table}').fetchone()
    return int(row[0])


def _person_list_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, dict):
        value = [value]
    out: list[str] = []
    for v in value:
        if isinstance(v, dict):
            n = v.get('name')
            if isinstance(n, str):
                out.append(n)
    return out


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _copy_to_seed(site: str, db_name: str) -> None:
    src = SITES_ROOT / site / 'instance' / db_name
    dst = SITES_ROOT / site / 'instance_seed' / db_name
    shutil.copyfile(src, dst)
    print(f'  copied {src.name} → instance_seed; md5={_md5(dst)}')


# ---------------- per-site handlers ----------------

def handle_imdb(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """UPDATE/INSERT real Movie + Person rows in imdb.db titles/persons."""
    db = SITES_ROOT / 'imdb' / 'instance' / 'imdb.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        # Movie record from movie/extruct.json
        m_route = routes.get('movie', {})
        for ld in m_route.get('json-ld', []):
            if ld.get('@type') != 'Movie':
                continue
            url = ld.get('url') or ''
            mm = re.search(r'/title/(tt\d+)', url)
            if not mm:
                continue
            tt_id = mm.group(1)
            agg = ld.get('aggregateRating') or {}
            updates = {
                'primary_title': _clean(ld.get('name')),
                'plot_short': _clean(ld.get('description')),
                'plot': _clean(ld.get('description')),
                'rating_avg': agg.get('ratingValue'),
                'num_votes': agg.get('ratingCount'),
                'mpaa_rating': ld.get('contentRating'),
                'release_date': ld.get('datePublished'),
                'poster_path': ld.get('image'),
                'runtime_min': _iso_duration_to_min(ld.get('duration')),
                'year': int(ld['datePublished'][:4]) if isinstance(ld.get('datePublished'), str) else None,
            }
            if _row_exists(conn, 'titles', {'tt_id': tt_id}):
                upd += _set_fields(conn, 'titles', {'tt_id': tt_id}, updates)
            else:
                new_id = _next_id(conn, 'titles')
                conn.execute(
                    'INSERT INTO titles (id, tt_id, title_type, primary_title, '
                    'plot, plot_short, rating_avg, num_votes, mpaa_rating, '
                    'release_date, poster_path, runtime_min, year) VALUES '
                    '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (new_id, tt_id, 'movie', updates['primary_title'],
                     updates['plot'], updates['plot_short'], updates['rating_avg'],
                     updates['num_votes'], updates['mpaa_rating'],
                     updates['release_date'], updates['poster_path'],
                     updates['runtime_min'], updates['year']))
                ins += 1

        # Person record from person/extruct.json
        p_route = routes.get('person', {})
        for ld in p_route.get('json-ld', []):
            url = ld.get('url') or ''
            pm = re.search(r'/name/(nm\d+)', url)
            if not pm:
                # Try mainEntity nested
                me = ld.get('mainEntity') or {}
                pm = re.search(r'/name/(nm\d+)', me.get('url', ''))
                if not pm:
                    continue
            nm_id = pm.group(1)
            me = ld.get('mainEntity') or {}
            name = _clean(ld.get('name') or me.get('name'))
            bio = _clean(ld.get('description') or me.get('description'))
            photo = ld.get('image') or me.get('image')
            jobs = me.get('jobTitle') or []
            if isinstance(jobs, str):
                jobs = [jobs]
            prof = ', '.join(jobs) if jobs else None
            birth = me.get('birthDate') or ld.get('birthDate')
            birth_year = int(birth[:4]) if isinstance(birth, str) and len(birth) >= 4 and birth[:4].isdigit() else None
            updates = {
                'name': name,
                'bio': bio,
                'photo_path': photo,
                'primary_profession': prof,
                'birth_year': birth_year,
            }
            if _row_exists(conn, 'persons', {'nm_id': nm_id}):
                upd += _set_fields(conn, 'persons', {'nm_id': nm_id}, updates)
            else:
                new_id = _next_id(conn, 'persons')
                conn.execute(
                    'INSERT INTO persons (id, nm_id, name, bio, photo_path, '
                    'primary_profession, birth_year) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (new_id, nm_id, name, bio, photo, prof, birth_year))
                ins += 1

        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_allrecipes(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'allrecipes' / 'instance' / 'allrecipes.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        r_route = routes.get('recipe', {})
        for ld in r_route.get('json-ld', []):
            t = ld.get('@type')
            if isinstance(t, list):
                t = next((x for x in t if x == 'Recipe'), None)
            if t != 'Recipe':
                continue
            name = _clean(ld.get('name') or ld.get('headline'))
            if not name:
                continue
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:200]
            img = ld.get('image')
            if isinstance(img, dict):
                img = img.get('url')
            elif isinstance(img, list) and img:
                first = img[0]
                img = first.get('url') if isinstance(first, dict) else first
            authors = _person_list_names(ld.get('author'))
            agg = ld.get('aggregateRating') or {}
            nutr = ld.get('nutrition') or {}
            cal = None
            if isinstance(nutr, dict):
                c = nutr.get('calories')
                if isinstance(c, str):
                    cm = re.search(r'\d+', c)
                    cal = int(cm.group()) if cm else None
            updates = {
                'title': name,
                'description': _clean(ld.get('description')),
                'image': img,
                'prep_time': ld.get('prepTime'),
                'cook_time': ld.get('cookTime'),
                'total_time': ld.get('totalTime'),
                'prep_time_mins': _iso_duration_to_min(ld.get('prepTime')),
                'cook_time_mins': _iso_duration_to_min(ld.get('cookTime')),
                'total_time_mins': _iso_duration_to_min(ld.get('totalTime')),
                'servings': str(ld.get('recipeYield')) if ld.get('recipeYield') is not None else None,
                'calories': cal,
                'avg_rating': agg.get('ratingValue'),
                'review_count': agg.get('ratingCount') or agg.get('reviewCount'),
                'author_name': authors[0] if authors else None,
                'ingredients_json': json.dumps(ld.get('recipeIngredient') or []),
                'instructions_json': json.dumps(ld.get('recipeInstructions') or []),
            }
            if _row_exists(conn, 'recipe', {'slug': slug}):
                upd += _set_fields(conn, 'recipe', {'slug': slug}, updates)
            else:
                new_id = _next_id(conn, 'recipe')
                cols = ['id', 'slug'] + list(updates.keys())
                vals = [new_id, slug] + list(updates.values())
                ph = ', '.join('?' * len(cols))
                conn.execute(f'INSERT INTO recipe ({", ".join(cols)}) VALUES ({ph})', vals)
                ins += 1
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_bbc_news(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'bbc_news' / 'instance' / 'bbc_news.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        a_route = routes.get('article', {})
        for ld in a_route.get('json-ld', []):
            if ld.get('@type') not in ('ReportageNewsArticle', 'NewsArticle', 'Article'):
                continue
            url = ld.get('url') or ld.get('mainEntityOfPage') or ''
            sm = re.search(r'/articles/([a-z0-9]+)', url)
            if not sm:
                continue
            slug = sm.group(1)
            img = ld.get('image')
            if isinstance(img, dict):
                img = img.get('url')
            authors = _person_list_names(ld.get('author'))
            updates = {
                'headline': _clean(ld.get('headline')),
                'summary': _clean(ld.get('description')),
                'author': ', '.join(authors) if authors else None,
                'hero_image': img,
                'published_at': ld.get('datePublished'),
                'source_url': url,
                'section_slug': 'climate',
                'content_type': 'article',
            }
            if _row_exists(conn, 'articles', {'slug': slug}):
                upd += _set_fields(conn, 'articles', {'slug': slug}, updates)
            else:
                new_id = _next_id(conn, 'articles')
                cols = ['id', 'slug'] + list(updates.keys())
                vals = [new_id, slug] + list(updates.values())
                ph = ', '.join('?' * len(cols))
                conn.execute(f'INSERT INTO articles ({", ".join(cols)}) VALUES ({ph})', vals)
                ins += 1
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_coursera(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'coursera' / 'instance' / 'coursera.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        c_route = routes.get('course', {})
        for ld in c_route.get('json-ld', []):
            if ld.get('@type') != 'Course':
                continue
            name = _clean(ld.get('name'))
            if not name:
                continue
            cid = ld.get('@id') or ''
            sm = re.search(r'/learn/([^/?#]+)', cid)
            slug = sm.group(1) if sm else re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:200]
            img = ld.get('image')
            if isinstance(img, list) and img:
                img = img[0]
            updates = {
                'title': name,
                'description': _clean(ld.get('description')),
                'has_certificate': 1,
                'is_free': 0,
                'preview_video_url': ld.get('video', {}).get('contentUrl') if isinstance(ld.get('video'), dict) else None,
            }
            if _row_exists(conn, 'courses', {'slug': slug}):
                upd += _set_fields(conn, 'courses', {'slug': slug}, updates)
            else:
                new_id = _next_id(conn, 'courses')
                cols = ['id', 'slug'] + list(updates.keys())
                vals = [new_id, slug] + list(updates.values())
                ph = ', '.join('?' * len(cols))
                conn.execute(f'INSERT INTO courses ({", ".join(cols)}) VALUES ({ph})', vals)
                ins += 1
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_fandom(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'fandom' / 'instance' / 'fandom.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        for route_name, wiki_id, wiki_host_re in [
            ('mcu_article', 1, r'marvelcinematicuniverse\.fandom\.com'),
            ('starwars_article', 2, r'starwars\.fandom\.com'),
        ]:
            payload = routes.get(route_name, {})
            for ld in payload.get('json-ld', []):
                if ld.get('@type') != 'Article':
                    continue
                url = ld.get('url') or ''
                if not re.search(wiki_host_re, url):
                    continue
                sm = re.search(r'/wiki/([^/?#]+)', url)
                if not sm:
                    continue
                slug = sm.group(1)
                me = ld.get('mainEntity') or ld.get('about') or {}
                name = _clean(ld.get('name') or me.get('name'))
                image = me.get('image') if isinstance(me, dict) else None
                if not image:
                    image = ld.get('image')
                infobox = None
                kind = None
                if isinstance(me, dict) and me.get('@type') == 'Person':
                    infobox = {k: v for k, v in me.items()
                               if k in ('gender', 'height', 'weight', 'birthDate',
                                        'birthPlace', 'homeLocation')}
                    kind = 'character'
                where = {'wiki_id': wiki_id, 'slug': slug}
                updates = {
                    'title': name,
                    'image': image,
                    'infobox_kind': kind,
                    'infobox_json': json.dumps(infobox) if infobox else None,
                }
                if _row_exists(conn, 'articles', where):
                    upd += _set_fields(conn, 'articles', where, updates)
                else:
                    new_id = _next_id(conn, 'articles')
                    cols = ['id', 'wiki_id', 'slug'] + list(updates.keys())
                    vals = [new_id, wiki_id, slug] + list(updates.values())
                    ph = ', '.join('?' * len(cols))
                    conn.execute(
                        f'INSERT INTO articles ({", ".join(cols)}) VALUES ({ph})',
                        vals)
                    ins += 1
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_nba(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'nba' / 'instance' / 'nba.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        # SportsTeam (Lakers)
        t_route = routes.get('team_detail', {})
        for ld in t_route.get('json-ld', []):
            if ld.get('@type') != 'SportsTeam':
                continue
            tid = ld.get('@id') or ''
            sm = re.search(r'/team/(\d+)/([^/?#]+)', tid)
            if not sm:
                continue
            slug = sm.group(2)
            loc = ld.get('location') or {}
            coach = ld.get('coach') or {}
            updates = {
                'logo': ld.get('logo'),
                'arena': loc.get('name') if isinstance(loc, dict) else None,
                'coach': coach.get('name') if isinstance(coach, dict) else None,
            }
            if _row_exists(conn, 'teams', {'slug': slug}):
                upd += _set_fields(conn, 'teams', {'slug': slug}, updates)
            # No INSERT path: teams are pinned at 30 — never add a new one.

        # Player (LeBron)
        p_route = routes.get('player', {})
        for ld in p_route.get('json-ld', []):
            if str(ld.get('@type', '')).lower() != 'person':
                continue
            pid = ld.get('@id') or ''
            sm = re.search(r'/player/(\d+)(?:/([^/?#]+))?', pid)
            if not sm:
                continue
            name = _clean(ld.get('givenName'))
            slug = sm.group(2) or (
                re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') if name else None)
            if not slug:
                continue
            img = ld.get('image')
            if isinstance(img, dict):
                img = img.get('contentUrl') or img.get('url')
            updates = {
                'image': img,
                'height': ld.get('height'),
                'bio': f"Born {ld.get('birthDate')}." if ld.get('birthDate') else None,
            }
            if _row_exists(conn, 'players', {'slug': slug}):
                upd += _set_fields(conn, 'players', {'slug': slug}, updates)
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_boardgamegeek(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'boardgamegeek' / 'instance' / 'boardgamegeek.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        # Microdata only — Products on the game/videos/files routes
        for route_name in ('game', 'videos', 'files'):
            payload = routes.get(route_name, {})
            for item in payload.get('microdata', []):
                t = item.get('type') or []
                if isinstance(t, str):
                    t = [t]
                if not any('Game' in x or 'Product' in x for x in t):
                    continue
                props = item.get('properties') or {}
                gid = item.get('id') or props.get('url') or ''
                gm = re.search(r'/boardgame/(\d+)/?', gid)
                if not gm:
                    continue
                bgg_id = int(gm.group(1))
                agg = props.get('aggregateRating') or {}
                agg_props = agg.get('properties') if isinstance(agg, dict) else {}
                npl = props.get('numberOfPlayers') or {}
                npl_props = npl.get('properties') if isinstance(npl, dict) else {}
                aud = props.get('audience') or {}
                aud_props = aud.get('properties') if isinstance(aud, dict) else {}
                def _f(v):  # safe float
                    try:
                        return float(v) if v is not None else None
                    except (TypeError, ValueError):
                        return None
                def _i(v):
                    try:
                        return int(v) if v is not None else None
                    except (TypeError, ValueError):
                        return None
                updates = {
                    'name': _clean(props.get('name')),
                    'short_description': _clean(props.get('description')),
                    'image_filename': props.get('image'),
                    'avg_rating': _f(agg_props.get('ratingValue')) if agg_props else None,
                    'num_ratings': _i(agg_props.get('reviewCount')) if agg_props else None,
                    'minplayers': _i(npl_props.get('minValue')) if npl_props else None,
                    'maxplayers': _i(npl_props.get('maxValue')) if npl_props else None,
                    'minage': _i(aud_props.get('suggestedMinAge')) if aud_props else None,
                }
                if _row_exists(conn, 'games', {'bgg_id': bgg_id}):
                    upd += _set_fields(conn, 'games', {'bgg_id': bgg_id}, updates)
                # No INSERT: games table is pinned, only enrich.
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_github(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    db = SITES_ROOT / 'github' / 'instance' / 'github_mirror.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        # SoftwareSourceCode microdata on repo routes
        repo_routes = ('cpython', 'flask', 'linux', 'repo', 'repo_issues',
                       'repo_pulls')
        for rn in repo_routes:
            payload = routes.get(rn, {})
            for item in payload.get('microdata', []):
                t = item.get('type') or ''
                if 'SoftwareSourceCode' not in (t if isinstance(t, str) else ' '.join(t)):
                    continue
                props = item.get('properties') or {}
                owner_name = props.get('author')
                repo_name = props.get('name')
                if not isinstance(owner_name, str) or not isinstance(repo_name, str):
                    continue
                full = f'{owner_name}/{repo_name}'
                readme_text = props.get('text')
                if not _row_exists(conn, 'repository', {'full_name': full}):
                    # Need owner; resolve or skip
                    owner_row = conn.execute(
                        'SELECT id FROM user WHERE username=?',
                        (owner_name,)).fetchone()
                    if not owner_row:
                        continue
                    new_id = _next_id(conn, 'repository')
                    conn.execute(
                        'INSERT INTO repository (id, owner_id, name, full_name, '
                        'readme, has_readme, is_public) VALUES (?, ?, ?, ?, ?, 1, 1)',
                        (new_id, owner_row[0], repo_name, full, readme_text))
                    ins += 1
                else:
                    if isinstance(readme_text, str):
                        upd += _set_fields(conn, 'repository', {'full_name': full},
                                           {'readme': readme_text,
                                            'has_readme': 1})

        # Person microdata on user route
        u_payload = routes.get('user', {})
        for item in u_payload.get('microdata', []):
            t = item.get('type') or ''
            if 'Person' not in (t if isinstance(t, str) else ' '.join(t)):
                continue
            props = item.get('properties') or {}
            login = props.get('additionalName') or props.get('alternateName')
            name = props.get('name')
            if not login or not isinstance(login, str):
                # Try parse from URL
                url = item.get('id') or ''
                m = re.search(r'github\.com/([^/?#]+)', url)
                if not m:
                    continue
                login = m.group(1)
            updates: dict[str, Any] = {}
            if isinstance(name, str):
                updates['name'] = name
            bio = props.get('description')
            if isinstance(bio, str):
                updates['bio'] = bio[:250]
            if updates and _row_exists(conn, 'user', {'username': login}):
                upd += _set_fields(conn, 'user', {'username': login}, updates)
        conn.commit()
    finally:
        conn.close()
    return upd, ins


# ---------------- registry ----------------

SITE_HANDLERS: dict[str, dict[str, Any]] = {
    'imdb':           {'harvest_dir': 'imdb_com',           'db': 'imdb.db',           'fn': handle_imdb},
    'allrecipes':     {'harvest_dir': 'allrecipes_com',     'db': 'allrecipes.db',     'fn': handle_allrecipes},
    'bbc_news':       {'harvest_dir': 'bbc_com',            'db': 'bbc_news.db',       'fn': handle_bbc_news},
    'coursera':       {'harvest_dir': 'coursera_org',       'db': 'coursera.db',       'fn': handle_coursera},
    'fandom':         {'harvest_dir': 'fandom_com',         'db': 'fandom.db',         'fn': handle_fandom},
    'nba':            {'harvest_dir': 'nba_com',            'db': 'nba.db',            'fn': handle_nba},
    'boardgamegeek':  {'harvest_dir': 'boardgamegeek_com',  'db': 'boardgamegeek.db',  'fn': handle_boardgamegeek},
    'github':         {'harvest_dir': 'github_com',         'db': 'github_mirror.db',  'fn': handle_github},
}


def run_site(site: str, copy_to_seed: bool) -> None:
    cfg = SITE_HANDLERS[site]
    print(f'== {site} (harvest={cfg["harvest_dir"]}) ==')
    routes = _load_extruct(cfg['harvest_dir'])
    if not routes:
        print(f'  no extruct routes — skip')
        return
    upd, ins = cfg['fn'](routes)
    print(f'  updated={upd}  inserted={ins}')
    if copy_to_seed and (upd or ins):
        _copy_to_seed(site, cfg['db'])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--site', choices=list(SITE_HANDLERS) + ['all'], required=True)
    p.add_argument('--copy-to-seed', action='store_true',
                   help='After write, cp instance/<db> → instance_seed/<db>.')
    args = p.parse_args()
    targets = list(SITE_HANDLERS) if args.site == 'all' else [args.site]
    for s in targets:
        run_site(s, args.copy_to_seed)


if __name__ == '__main__':
    main()
