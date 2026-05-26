#!/usr/bin/env python3
"""R7b article-only top-up — adds more EN + ES templates to push article
count past 5000 without re-running game/betting paths.

Gated on `_r7b_marker` row in `sports`.
"""
import hashlib
import json
import os
import sqlite3
from datetime import date, timedelta

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  'instance_seed', 'espn.db')


def h(key: str, mod: int, offset: int = 0) -> int:
    return offset + int.from_bytes(
        hashlib.md5(key.encode()).digest()[:4], 'big') % mod


def fetch_one(cur, sql, args=()):
    cur.execute(sql, args)
    row = cur.fetchone()
    return row[0] if row else None


def already_extended(cur) -> bool:
    return bool(fetch_one(cur,
        "SELECT 1 FROM sports WHERE slug='_r7b_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (105, 'R7b marker', '_r7b_marker', 'r7b_extend applied',
         '/_internal/', 105, 0))


def normalize(cur):
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# 6 additional templates, EN.
TEMPLATES_R7B = {
    'longform-feature': (
        'Longform feature: how the {team} got here in {season}',
        'A deep-dive longform on the {team} {sport_upper} arc through '
        '{season}. We talk to assistant coaches, the equipment manager, '
        'and the lead scouts. The portrait is of a methodical rebuild '
        'that has avoided shortcuts and is now paying off.',
        ['longform', 'feature']),
    'practice-report': (
        'Practice report: notes from {team} morning shootaround in {season}',
        'Filed dispatch from the {team} {sport_upper} {season} shootaround. '
        'Status updates on three injured starters, a glimpse of the new '
        'pick-and-roll wrinkle the staff has been working on, and a quick '
        'note on the rookie\'s defensive footwork.',
        ['practice', 'beat-note']),
    'storyline-watch': (
        'Storyline Watch: three {team} threads we\'ll track in {season}',
        'ESPN sets the table on three storylines worth tracking around the '
        '{team} {sport_upper} {season} stretch. Topics include the closing '
        'lineup decision, the rookie\'s emerging role, and where the front '
        'office stands on a possible extension.',
        ['storyline', 'preview']),
    'matchup-pillars': (
        'Matchup pillars: what the {team} must win in {season}',
        'Tactical breakdown of the four pillars the {team} must win to '
        'survive their {season} {sport_upper} stretch. Transition defense, '
        'second-chance points, free-throw discipline, and turnover margin '
        'all get a frame-by-frame look.',
        ['matchup', 'tactics']),
    'one-on-one-interview': (
        'One-on-one: {team} captain on what {season} means',
        'An exclusive sit-down with the {team} {sport_upper} captain ahead '
        'of a critical {season} stretch. He talks legacy, the family\'s '
        'impact, the trust in his coach, and the locker-room\'s belief.',
        ['interview', 'one-on-one']),
    'numbers-game': (
        'Numbers Game: the {team} stats that explain {season}',
        'A pure-numbers post on the {team} this {season} {sport_upper} '
        'run. Net rating splits, three-point variance, turnover spread, '
        'and high-leverage minute usage all checked against last season '
        'and league averages.',
        ['numbers', 'stats']),
}


# 4 additional ES templates.
TEMPLATES_R7B_ES = {
    'longform-feature': (
        'Reportaje extenso: cómo los {team} llegaron aquí en {season}',
        'Un reportaje en profundidad sobre el arco de los {team} en '
        '{sport_upper} a lo largo de {season}. Hablamos con asistentes, '
        'el utilero y los principales ojeadores. El retrato es el de una '
        'reconstrucción metódica que ahora rinde frutos.',
        ['longform', 'feature', 'es', 'deportes']),
    'practice-report': (
        'Reporte de práctica: notas del entrenamiento de los {team} en {season}',
        'Despacho desde el entrenamiento de los {team} en {sport_upper} '
        '{season}. Actualizaciones de tres titulares lesionados, un vistazo '
        'al nuevo bloqueo y continuación, y una nota sobre los pies del '
        'novato en defensa.',
        ['practice', 'beat-note', 'es', 'deportes']),
    'storyline-watch': (
        'En la mira: tres tramas a seguir con los {team} en {season}',
        'ESPN deja servidas tres tramas a seguir alrededor de los {team} '
        'en este tramo de {sport_upper} {season}. Incluye el quinteto de '
        'cierre, el rol emergente del novato y la postura de la oficina '
        'sobre una posible extensión.',
        ['storyline', 'preview', 'es', 'deportes']),
    'numbers-game': (
        'Juego de números: las estadísticas de los {team} en {season}',
        'Un análisis puramente numérico de los {team} en este tramo de '
        '{sport_upper} {season}. Net rating, varianza desde el triple, '
        'margen de pérdidas y minutos de alto apalancamiento, todo '
        'comparado con la temporada pasada y los promedios de la liga.',
        ['numbers', 'stats', 'es', 'deportes']),
}


SPORT_PLANS_R7B = [
    ('nba', 'NBA', 'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
                   'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
                   'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
                   'Minnesota Timberwolves,Oklahoma City Thunder,'
                   'Cleveland Cavaliers,Indiana Pacers'.split(','),
     '2025-26'),
    ('nfl', 'NFL', 'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
                   'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
                   'Detroit Lions,Miami Dolphins,Green Bay Packers,'
                   'Cincinnati Bengals,Pittsburgh Steelers,Houston Texans'.split(','),
     '2025'),
    ('mlb', 'MLB', 'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
                   'Atlanta Braves,Houston Astros,Texas Rangers,'
                   'Philadelphia Phillies,Chicago Cubs,San Diego Padres,'
                   'Toronto Blue Jays'.split(','),
     '2025'),
    ('nhl', 'NHL', 'Boston Bruins,Edmonton Oilers,Vegas Golden Knights,'
                   'New York Rangers,Toronto Maple Leafs,Florida Panthers,'
                   'Colorado Avalanche,Tampa Bay Lightning'.split(','),
     '2025-26'),
    ('soccer', 'Soccer', 'Arsenal,Manchester City,Liverpool,'
                        'Real Madrid,Barcelona,Bayern Munich,'
                        'Paris Saint-Germain,Inter Milan'.split(','),
     '2025-26'),
    ('ncaaf', 'CFB', 'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
                     'USC,Notre Dame'.split(','),
     '2025'),
    ('ncaam', 'CBB', 'Duke,Kansas,Kentucky,Connecticut,North Carolina,'
                     'Houston,Purdue'.split(','),
     '2025-26'),
]

ES_SPORT_PLANS_R7B = [
    ('nba', 'NBA', 'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
                   'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
                   'Philadelphia 76ers,New York Knicks'.split(','),
     '2025-26'),
    ('nfl', 'NFL', 'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
                   'Baltimore Ravens,Dallas Cowboys'.split(','),
     '2025'),
    ('mlb', 'MLB', 'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
                   'Atlanta Braves,Houston Astros'.split(','),
     '2025'),
    ('soccer', 'Soccer', 'Real Madrid,Barcelona,Bayern Munich,'
                        'Paris Saint-Germain,Inter Milan,'
                        'Manchester City,Arsenal,Liverpool'.split(','),
     '2025-26'),
]


def make_articles(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM articles").fetchall())

    rows = []
    tpl_names = sorted(TEMPLATES_R7B.keys())
    for sport_slug, sport_upper, teams_list, season in SPORT_PLANS_R7B:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names:
                title_fmt, body_fmt, tag_kw = TEMPLATES_R7B[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'r7b-{sport_slug}-{team_slug}-{tpl_name}-{ti:02d}'
                if slug in existing:
                    continue
                existing.add(slug)
                title = title_fmt.format(team=team,
                                         sport_upper=sport_upper,
                                         season=season)
                body = body_fmt.format(team=team,
                                       sport_upper=sport_upper,
                                       season=season)
                tags = json.dumps([sport_upper, team] + tag_kw)
                day_off = h(f'r7b-art-pub-{slug}', 180)
                base_pub = date(2025, 11, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r7b-{ti}.jpg',
                    tags,
                    0,
                    1 if tpl_name in ('longform-feature',
                                      'numbers-game') and ti < 2 else 0,
                    pub_dt, pub_disp,
                ))
                next_id += 1

    tpl_names_es = sorted(TEMPLATES_R7B_ES.keys())
    for sport_slug, sport_upper, teams_list, season in ES_SPORT_PLANS_R7B:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names_es:
                title_fmt, body_fmt, tag_kw = TEMPLATES_R7B_ES[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'es-r7b-{sport_slug}-{team_slug}-{tpl_name}-{ti:02d}'
                if slug in existing:
                    continue
                existing.add(slug)
                title = title_fmt.format(team=team,
                                         sport_upper=sport_upper,
                                         season=season)
                body = body_fmt.format(team=team,
                                       sport_upper=sport_upper,
                                       season=season)
                tags = json.dumps([sport_upper, team] + tag_kw)
                day_off = h(f'es-r7b-art-pub-{slug}', 180)
                base_pub = date(2025, 11, 15) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Deportes',
                    f'/static/images/espn/articles/{sport_slug}/es-r7b-{ti}.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, "
        "body, author, image, tags, is_headline, is_featured, "
        "created_at, published_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R7b extension already applied — no-op.')
        conn.close()
        return
    n_ar = make_articles(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R7b inserted: articles={n_ar}')


if __name__ == '__main__':
    main()
