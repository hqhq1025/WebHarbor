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


def _set_harvest_root(p: str | Path) -> None:
    """Override the harvest root (e.g. for snapshots stored outside /datadrive)."""
    global HARVEST_ROOT
    HARVEST_ROOT = Path(p)


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


def _iso_duration_to_sec(d: str | None) -> int | None:
    """PT2H22M → 8520, PT4M47S → 287, PT45S → 45."""
    if not d or not isinstance(d, str):
        return None
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', d)
    if not m:
        return None
    h, mn, se = (int(g or 0) for g in m.groups())
    total = h * 3600 + mn * 60 + se
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
    """UPDATE/INSERT real Movie + Person rows in imdb.db titles/persons.

    Walks ALL routes (per-title `tt<digits>_<hash>/extruct.json` and per-person
    `person/extruct.json`) — not just the single `movie`/`person` routes the
    original tiny harvest produced. Movie matched by tt_id (parsed from `url` or
    `@id`); Person matched by nm_id (parsed from outer url, mainEntity.url, or
    @id).
    """
    db = SITES_ROOT / 'imdb' / 'instance' / 'imdb.db'
    conn = _open_db(db)
    upd = ins = 0
    seen_tt: set[str] = set()
    seen_nm: set[str] = set()
    try:
        for route_name, payload in routes.items():
            for ld in payload.get('json-ld', []):
                if not isinstance(ld, dict):
                    continue
                t = ld.get('@type')

                # ---------- Movie ----------
                if t == 'Movie':
                    url = ld.get('url') or ld.get('@id') or ''
                    mm = re.search(r'/title/(tt\d+)', url)
                    if not mm:
                        continue
                    tt_id = mm.group(1)
                    if tt_id in seen_tt:
                        continue
                    seen_tt.add(tt_id)
                    agg = ld.get('aggregateRating') or {}
                    poster = ld.get('image')
                    if isinstance(poster, dict):
                        poster = poster.get('url') or poster.get('contentUrl')
                    elif isinstance(poster, list) and poster:
                        first = poster[0]
                        poster = first.get('url') if isinstance(first, dict) else first
                    updates = {
                        'primary_title': _clean(ld.get('name')),
                        'plot_short': _clean(ld.get('description')),
                        'plot': _clean(ld.get('description')),
                        'rating_avg': agg.get('ratingValue'),
                        'num_votes': agg.get('ratingCount'),
                        'mpaa_rating': ld.get('contentRating'),
                        'release_date': ld.get('datePublished'),
                        'poster_path': poster,
                        'runtime_min': _iso_duration_to_min(ld.get('duration')),
                        'year': int(ld['datePublished'][:4]) if isinstance(ld.get('datePublished'), str) and ld['datePublished'][:4].isdigit() else None,
                    }
                    if _row_exists(conn, 'titles', {'tt_id': tt_id}):
                        upd += _set_fields(conn, 'titles', {'tt_id': tt_id}, updates)
                    else:
                        if not updates['primary_title']:
                            continue
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
                    continue

                # ---------- Person (sometimes wrapped in Article + mainEntity) ----------
                # Find nm_id in url / @id / mainEntity.url
                me = ld.get('mainEntity') if isinstance(ld.get('mainEntity'), dict) else {}
                candidates = [
                    ld.get('url'), ld.get('@id'),
                    me.get('url'), me.get('@id'),
                ]
                nm = None
                for c in candidates:
                    if isinstance(c, str):
                        pm = re.search(r'/name/(nm\d+)', c)
                        if pm:
                            nm = pm.group(1)
                            break
                if not nm:
                    continue
                # Only treat as person record if outer or mainEntity declares Person/Article-with-Person
                outer_t = t if isinstance(t, str) else None
                inner_t = me.get('@type') if me else None
                if outer_t not in ('Person', 'Article') and inner_t != 'Person':
                    continue
                if nm in seen_nm:
                    continue
                seen_nm.add(nm)

                name = _clean(ld.get('name') or me.get('name'))
                bio = _clean(ld.get('description') or me.get('description'))
                photo = ld.get('image') or me.get('image')
                if isinstance(photo, dict):
                    photo = photo.get('url') or photo.get('contentUrl')
                elif isinstance(photo, list) and photo:
                    first = photo[0]
                    photo = first.get('url') if isinstance(first, dict) else first
                jobs = me.get('jobTitle') or ld.get('jobTitle') or []
                if isinstance(jobs, str):
                    jobs = [jobs]
                prof = ', '.join(jobs) if jobs else None
                birth = me.get('birthDate') or ld.get('birthDate')
                birth_year = (int(birth[:4]) if isinstance(birth, str)
                              and len(birth) >= 4 and birth[:4].isdigit() else None)
                updates = {
                    'name': name,
                    'bio': bio,
                    'photo_path': photo,
                    'primary_profession': prof,
                    'birth_year': birth_year,
                }
                if _row_exists(conn, 'persons', {'nm_id': nm}):
                    upd += _set_fields(conn, 'persons', {'nm_id': nm}, updates)
                else:
                    if not name:
                        continue
                    new_id = _next_id(conn, 'persons')
                    conn.execute(
                        'INSERT INTO persons (id, nm_id, name, bio, photo_path, '
                        'primary_profession, birth_year) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (new_id, nm, name, bio, photo, prof, birth_year))
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
    """Upsert real Coursera Course rows from JSON-LD.

    Walks every route in `routes` (named harvest routes + spider <slug>_<hash>
    snapshots), dedupes by slug parsed from @id `/learn/<slug>/`, and merges
    multiple snapshot copies into the richest record. UPDATE is conservative:
    only fills NULL/short fields (matches the existing real seed data we do
    not want to clobber). INSERT covers brand-new slugs with full payload.
    """
    db = SITES_ROOT / 'coursera' / 'instance' / 'coursera.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        # ---- collect: slug -> merged record ----
        merged: dict[str, dict[str, Any]] = {}
        for payload in routes.values():
            for ld in payload.get('json-ld') or []:
                if ld.get('@type') != 'Course':
                    continue
                name = _clean(ld.get('name'))
                if not name:
                    continue
                cid = ld.get('@id') or ld.get('url') or ''
                sm = re.search(r'/learn/([^/?#]+)', cid)
                if not sm:
                    continue
                slug = sm.group(1).rstrip('/')[:300]
                provider = ld.get('provider') or {}
                provider_name = provider.get('name') if isinstance(provider, dict) else None
                agg = ld.get('aggregateRating') or {}
                if not isinstance(agg, dict):
                    agg = {}
                rating = agg.get('ratingValue')
                review_count = agg.get('ratingCount') or agg.get('reviewCount')
                # syllabusSections timeRequired -> total hours
                total_sec = 0
                for sec in ld.get('syllabusSections') or []:
                    if isinstance(sec, dict):
                        s = _iso_duration_to_sec(sec.get('timeRequired'))
                        if s:
                            total_sec += s
                duration_hours = round(total_sec / 3600, 2) if total_sec else None
                level = ld.get('educationalLevel')
                if isinstance(level, str):
                    level = level.strip() or None
                enrolled = ld.get('totalHistoricalEnrollment')
                video = ld.get('video')
                video_url = None
                if isinstance(video, dict):
                    video_url = video.get('contentUrl') or video.get('url')
                rec = {
                    'title': name,
                    'description': _clean(ld.get('description')),
                    'level': level,
                    'duration_hours': duration_hours,
                    'provider_name': _clean(provider_name) if provider_name else None,
                    'rating': float(rating) if isinstance(rating, (int, float)) else None,
                    'review_count': int(review_count) if isinstance(review_count, (int, float)) else None,
                    'enrolled_count': int(enrolled) if isinstance(enrolled, (int, float)) else None,
                    'preview_video_url': video_url,
                }
                prev = merged.get(slug) or {}
                # Take the first non-None value across snapshot variants
                for k, v in rec.items():
                    if prev.get(k) is None and v is not None:
                        prev[k] = v
                merged[slug] = prev

        # ---- partner lookup cache (case-insensitive name match) ----
        partner_by_name = {n.lower(): pid for pid, n in
                           conn.execute('SELECT id, name FROM partners').fetchall()}

        for slug, rec in merged.items():
            partner_id = None
            pn = (rec.get('provider_name') or '').lower()
            if pn and pn in partner_by_name:
                partner_id = partner_by_name[pn]

            full_payload = {
                'title': rec.get('title'),
                'description': rec.get('description'),
                'level': rec.get('level'),
                'duration_hours': rec.get('duration_hours'),
                'partner_id': partner_id,
                'rating': rec.get('rating'),
                'review_count': rec.get('review_count'),
                'enrolled_count': rec.get('enrolled_count'),
                'preview_video_url': rec.get('preview_video_url'),
                'has_certificate': 1,
                'is_free': 0,
            }

            row = conn.execute(
                'SELECT id, description, level, duration_hours, partner_id, '
                'rating, review_count, enrolled_count, preview_video_url '
                'FROM courses WHERE slug=?', (slug,)).fetchone()
            if row:
                (_, cur_desc, cur_level, cur_dur, cur_partner,
                 cur_rating, cur_revcnt, cur_enr, cur_video) = row
                # Conservative: only touch NULL/short rows for description;
                # only NULL for the other fields.
                conservative: dict[str, Any] = {}
                new_desc = full_payload['description']
                if new_desc and (cur_desc is None or len(cur_desc) < 50):
                    conservative['description'] = new_desc
                if cur_level is None and full_payload['level']:
                    conservative['level'] = full_payload['level']
                if cur_dur is None and full_payload['duration_hours']:
                    conservative['duration_hours'] = full_payload['duration_hours']
                if cur_partner is None and full_payload['partner_id']:
                    conservative['partner_id'] = full_payload['partner_id']
                if cur_rating is None and full_payload['rating']:
                    conservative['rating'] = full_payload['rating']
                if cur_revcnt is None and full_payload['review_count']:
                    conservative['review_count'] = full_payload['review_count']
                if cur_enr is None and full_payload['enrolled_count']:
                    conservative['enrolled_count'] = full_payload['enrolled_count']
                if cur_video is None and full_payload['preview_video_url']:
                    conservative['preview_video_url'] = full_payload['preview_video_url']
                if conservative:
                    upd += _set_fields(conn, 'courses', {'slug': slug},
                                       conservative)
            else:
                # INSERT — only include columns we actually have values for,
                # plus required (id, title, slug).
                if not full_payload.get('title'):
                    continue
                new_id = _next_id(conn, 'courses')
                cols = ['id', 'slug']
                vals: list[Any] = [new_id, slug]
                for c in ('title', 'description', 'level', 'duration_hours',
                          'partner_id', 'rating', 'review_count',
                          'enrolled_count', 'preview_video_url',
                          'has_certificate', 'is_free'):
                    v = full_payload.get(c)
                    if v is not None:
                        cols.append(c)
                        vals.append(v)
                ph = ', '.join('?' * len(cols))
                conn.execute(
                    f'INSERT INTO courses ({", ".join(cols)}) VALUES ({ph})',
                    vals)
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
    """UPDATE/INSERT real SportsTeam + Person rows in nba.db teams/players.

    Walks ALL routes (per-team `<slug>_<hash>/extruct.json` and per-player
    `<player-slug>_<hash>/extruct.json`) — not just `team_detail` / `player`.
    Teams matched by slug parsed from `@id=/team/<nba_team_id>/<slug>`.
    Players matched by slug parsed from `@id=/player/<nba_player_id>/<slug>`;
    when slug is missing, fall back to a slugified givenName.
    """
    db = SITES_ROOT / 'nba' / 'instance' / 'nba.db'
    conn = _open_db(db)
    upd = ins = 0
    seen_team: set[str] = set()
    seen_player: set[str] = set()
    try:
        # Pre-build name → team_id map for player INSERT lookups
        team_name_to_id: dict[str, int] = {}
        for tid, name, slug in conn.execute(
                'SELECT id, name, slug FROM teams').fetchall():
            team_name_to_id[name.lower()] = tid
            team_name_to_id[slug.lower()] = tid

        for route_name, payload in routes.items():
            for ld in payload.get('json-ld', []):
                if not isinstance(ld, dict):
                    continue
                t = str(ld.get('@type', ''))

                # ---------- SportsTeam ----------
                if t == 'SportsTeam':
                    tid = ld.get('@id') or ld.get('url') or ''
                    sm = re.search(r'/team/(\d+)/([^/?#]+)', tid)
                    if not sm:
                        continue
                    slug = sm.group(2)
                    if slug in seen_team:
                        continue
                    seen_team.add(slug)
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
                    continue

                # ---------- Player (Person) ----------
                if t.lower() != 'person':
                    continue
                pid = ld.get('@id') or ld.get('url') or ''
                sm = re.search(r'/player/(\d+)(?:/([^/?#]+))?', pid)
                if not sm:
                    continue
                name = _clean(ld.get('givenName') or ld.get('name'))
                slug = sm.group(2) or (
                    re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') if name else None)
                if not slug:
                    continue
                if slug in seen_player:
                    continue
                seen_player.add(slug)

                img = ld.get('image')
                if isinstance(img, dict):
                    img = img.get('contentUrl') or img.get('url')
                elif isinstance(img, list) and img:
                    first = img[0]
                    img = (first.get('contentUrl') or first.get('url')
                           if isinstance(first, dict) else first)
                birth = ld.get('birthDate')
                updates = {
                    'image': img,
                    'height': ld.get('height'),
                    'bio': f"Born {birth}." if birth else None,
                }
                if _row_exists(conn, 'players', {'slug': slug}):
                    upd += _set_fields(conn, 'players', {'slug': slug}, updates)
                else:
                    if not name:
                        continue
                    # Resolve team_id via memberOf
                    team_id = None
                    mo = ld.get('memberOf')
                    if isinstance(mo, list) and mo:
                        mo0 = mo[0]
                        if isinstance(mo0, dict):
                            t_name = mo0.get('name')
                            if isinstance(t_name, str):
                                # Strip city prefix: "Toronto Raptors" → match "Raptors"
                                team_id = team_name_to_id.get(t_name.lower())
                                if team_id is None:
                                    parts = t_name.split()
                                    if len(parts) > 1:
                                        team_id = team_name_to_id.get(parts[-1].lower())
                    if team_id is None:
                        # Cannot insert without a team — skip rather than fabricate
                        continue
                    new_id = _next_id(conn, 'players')
                    conn.execute(
                        'INSERT INTO players (id, team_id, name, slug, '
                        'height, bio, image) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (new_id, team_id, name, slug,
                         ld.get('height'),
                         f"Born {birth}." if birth else None,
                         img))
                    ins += 1
        conn.commit()
    finally:
        conn.close()
    return upd, ins


def handle_boardgamegeek(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """Upsert real BGG game rows from schema.org microdata.

    Walks every route in `routes` (named harvest + spider <bgg_id>_<hash>),
    parses microdata Product/Game items, dedupes by bgg_id, and merges
    snapshot variants (e.g. the same game's main page + forums + videos
    pages each carry the same microdata block — we keep the richest copy).
    INSERT new bgg_ids; UPDATE existing rows with non-NULL fields.
    """
    db = SITES_ROOT / 'boardgamegeek' / 'instance' / 'boardgamegeek.db'
    conn = _open_db(db)
    upd = ins = 0

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

    try:
        merged: dict[int, dict[str, Any]] = {}
        for payload in routes.values():
            for item in payload.get('microdata') or []:
                t = item.get('type') or []
                if isinstance(t, str):
                    t = [t]
                if not any('Game' in x or 'Product' in x for x in t):
                    continue
                props = item.get('properties') or {}
                gid = item.get('id') or props.get('url') or ''
                gm = re.search(r'/boardgame/(\d+)/([^/?#]+)?', gid)
                if not gm:
                    continue
                bgg_id = int(gm.group(1))
                slug_from_url = gm.group(2) or None
                agg = props.get('aggregateRating') or {}
                agg_props = agg.get('properties') if isinstance(agg, dict) else {}
                npl = props.get('numberOfPlayers') or {}
                npl_props = npl.get('properties') if isinstance(npl, dict) else {}
                aud = props.get('audience') or {}
                aud_props = aud.get('properties') if isinstance(aud, dict) else {}
                rec = {
                    'name': _clean(props.get('name')),
                    'slug': slug_from_url,
                    'short_description': _clean(props.get('description')),
                    'image_filename': props.get('image'),
                    'avg_rating': _f(agg_props.get('ratingValue')) if agg_props else None,
                    'num_ratings': _i(agg_props.get('reviewCount')) if agg_props else None,
                    'minplayers': _i(npl_props.get('minValue')) if npl_props else None,
                    'maxplayers': _i(npl_props.get('maxValue')) if npl_props else None,
                    'minage': _i(aud_props.get('suggestedMinAge')) if aud_props else None,
                }
                prev = merged.get(bgg_id) or {}
                for k, v in rec.items():
                    if prev.get(k) is None and v is not None:
                        prev[k] = v
                merged[bgg_id] = prev

        for bgg_id, rec in merged.items():
            db_updates = {k: v for k, v in rec.items() if k != 'slug' and v is not None}
            if _row_exists(conn, 'games', {'bgg_id': bgg_id}):
                upd += _set_fields(conn, 'games', {'bgg_id': bgg_id}, db_updates)
            else:
                name = rec.get('name')
                slug = rec.get('slug') or (
                    re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:200]
                    if name else None)
                if not name or not slug:
                    continue
                new_id = _next_id(conn, 'games')
                cols = ['id', 'bgg_id', 'name', 'slug']
                vals: list[Any] = [new_id, bgg_id, name, slug]
                for c in ('short_description', 'image_filename', 'avg_rating',
                          'num_ratings', 'minplayers', 'maxplayers', 'minage'):
                    v = rec.get(c)
                    if v is not None:
                        cols.append(c)
                        vals.append(v)
                # Mark as a boardgame subtype so existing browse pages can
                # surface it without further enrichment.
                cols.append('subtype')
                vals.append('boardgame')
                ph = ', '.join('?' * len(cols))
                conn.execute(
                    f'INSERT INTO games ({", ".join(cols)}) VALUES ({ph})',
                    vals)
                ins += 1
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


def handle_ted(routes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """UPDATE/INSERT TED talks from VideoObject JSON-LD.

    The harvest layout for ted_com differs from other sites: each subdir is a
    per-talk page (not a per-route variant). Each page's extruct.json carries a
    @graph containing one VideoObject for the talk on that URL.

    Match key: canonical_url == https://www.ted.com/talks/<underscored_slug>.
    The DB's `talk.slug` column uses dashes (kebab-case); we look up by
    canonical_url and fall back to the kebab slug.

    Per task spec: only touch NULL or weak (placeholder) cells; never overwrite
    real upstream data. Specifically:
      - description: replace only when current length < 150 chars and new is longer
      - image:       replace only when current looks like a local placeholder
                     ('images/talks/%') or is NULL/empty
      - duration_seconds: fill only when current is 0/NULL
      - views:       fill only when current is NULL/0
      - published_at / title / speaker: left untouched on existing rows
      - new VideoObjects (not present in talk) are INSERTed
    """
    db = SITES_ROOT / 'ted' / 'instance' / 'ted.db'
    conn = _open_db(db)
    upd = ins = 0
    try:
        # Build lookup once: canonical_url → (id, slug, description, image,
        # duration_seconds, views)
        existing: dict[str, dict[str, Any]] = {}
        for row in conn.execute(
            'SELECT id, slug, canonical_url, description, image, '
            'duration_seconds, views FROM talk').fetchall():
            cid = row[2]
            if cid:
                existing[cid] = {
                    'id': row[0], 'slug': row[1], 'description': row[3],
                    'image': row[4], 'duration_seconds': row[5], 'views': row[6],
                }

        # Also a kebab-slug index for fallback matching
        by_slug = {v['slug']: v for v in existing.values()}

        seen_keys: set[str] = set()
        for route_name, payload in routes.items():
            for ld in payload.get('json-ld', []):
                graph = ld.get('@graph') if isinstance(ld, dict) else None
                items = graph if isinstance(graph, list) else [ld]
                for v in items:
                    if not isinstance(v, dict):
                        continue
                    if v.get('@type') != 'VideoObject':
                        continue
                    vid = v.get('@id') or v.get('url') or ''
                    sm = re.search(r'/talks/([^/?#]+?)(?:#|$|\?)', vid)
                    if not sm:
                        continue
                    underscored = sm.group(1)
                    canonical = f'https://www.ted.com/talks/{underscored}'
                    kebab = underscored.replace('_', '-')
                    if canonical in seen_keys:
                        continue
                    seen_keys.add(canonical)

                    name = _clean(v.get('name'))
                    desc = _clean(v.get('description'))
                    thumb = v.get('thumbnailUrl')
                    if isinstance(thumb, list) and thumb:
                        thumb = thumb[0]
                    duration_sec = _iso_duration_to_sec(v.get('duration'))
                    published_at = v.get('uploadDate') or v.get('datePublished')
                    if isinstance(published_at, str):
                        published_at = published_at[:10]  # YYYY-MM-DD
                    # views from interactionStatistic
                    views = None
                    isn = v.get('interactionStatistic')
                    if isinstance(isn, dict):
                        c = isn.get('userInteractionCount')
                        try:
                            views = int(c) if c is not None else None
                        except (TypeError, ValueError):
                            views = None
                    # speaker name from author[]
                    speaker_names = _person_list_names(v.get('author'))
                    speaker_name = speaker_names[0] if speaker_names else None
                    speaker_slug = None
                    if isinstance(v.get('author'), list) and v['author']:
                        au0 = v['author'][0]
                        if isinstance(au0, dict):
                            au_url = au0.get('@id') or au0.get('url') or ''
                            asm = re.search(r'/speakers/([^/?#]+?)(?:#|$)', au_url)
                            if asm:
                                speaker_slug = asm.group(1).replace('_', '-')

                    cur = existing.get(canonical) or by_slug.get(kebab)
                    if cur is not None:
                        updates: dict[str, Any] = {}
                        cur_desc = cur.get('description') or ''
                        if desc and len(cur_desc) < 150 and len(desc) > len(cur_desc):
                            updates['description'] = desc
                        cur_img = cur.get('image') or ''
                        if thumb and (not cur_img or cur_img.startswith('images/talks')):
                            updates['image'] = thumb
                        if duration_sec and not (cur.get('duration_seconds') or 0):
                            updates['duration_seconds'] = duration_sec
                        if views is not None and not (cur.get('views') or 0):
                            updates['views'] = views
                        if updates:
                            upd += _set_fields(conn, 'talk',
                                               {'id': cur['id']}, updates)
                    else:
                        # INSERT new talk — populate required NOT NULL columns
                        if not name:
                            continue
                        new_id = _next_id(conn, 'talk')
                        # source_id must be unique; derive from URL hash
                        source_id = f'h{abs(hash(canonical)) % (10**8):08d}'
                        conn.execute(
                            'INSERT INTO talk (id, source_id, slug, title, '
                            'speaker, speaker_slug, event, talk_type, '
                            'duration_seconds, published_at, recorded_on, '
                            'views, image, canonical_url, description, '
                            'topics_json) VALUES '
                            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (new_id, source_id, kebab, name,
                             speaker_name or 'TED', speaker_slug or 'ted',
                             'TED', 'Talk',
                             duration_sec or 0, published_at or '',
                             published_at or '',
                             views, thumb, canonical, desc or '',
                             '[]'))
                        ins += 1
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
    'ted':            {'harvest_dir': 'ted_com',            'db': 'ted.db',            'fn': handle_ted},
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
    p.add_argument('--harvest-root', default=None,
                   help='Override HARVEST_ROOT (default /datadrive/harvest/snapshots).')
    args = p.parse_args()
    if args.harvest_root:
        _set_harvest_root(args.harvest_root)
    targets = list(SITE_HANDLERS) if args.site == 'all' else [args.site]
    for s in targets:
        run_site(s, args.copy_to_seed)


if __name__ == '__main__':
    main()
