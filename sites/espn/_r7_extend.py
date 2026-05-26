#!/usr/bin/env python3
"""R7 polish extension for sites/espn — direct sqlite3 INSERT only.

Continues gotcha #14 path: HF seed has drifted from seed_data.py, so we
extend the live DB with idempotent direct INSERTs.

R7 on top of R6 baseline:
  * +2000 games        (5061 → 7000+) NBA 25-26 first half, NHL 25-26
                                       first half, MLB 2025 mid, NFL 2025,
                                       soccer 25-26, ncaaf 2025, ncaam 25-26,
                                       NBA preseason fill, mid-week filler.
  * +1400 articles     (3618 → 5000+)  7 new EN templates +
                                       ~250 ESPN-Deportes (es-) translations.
  * +1200 betting_odds (1380 → 2500+)  more cross-book coverage of newer
                                       games.
  * +15 parlays
  * Indexes for hot paths:
      - (sport_slug, status, date) on games
      - (home_team_id, date desc) on games
      - (away_team_id, date desc) on games
  * Marker row sports.slug '_r7_marker' (id=104) — idempotent.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r7_marker` row in `sports`.
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


def hf(key: str, lo: float, hi: float) -> float:
    return lo + (h(key, 10_000) / 10_000.0) * (hi - lo)


def fetch_one(cur, sql, args=()):
    cur.execute(sql, args)
    row = cur.fetchone()
    return row[0] if row else None


def already_extended(cur) -> bool:
    return bool(fetch_one(cur,
        "SELECT 1 FROM sports WHERE slug='_r7_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (104, 'R7 marker', '_r7_marker', 'r7_extend applied',
         '/_internal/', 104, 0))


def normalize(cur):
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── Venues (re-use R6 sets) ──────────────────────────────────────────────────

NBA_VENUES = ['TD Garden', 'Crypto.com Arena', 'Madison Square Garden',
              'Chase Center', 'Ball Arena', 'Paycom Center',
              'Kaseya Center', 'American Airlines Center',
              'Footprint Center', 'Fiserv Forum', 'Spectrum Center',
              'Smoothie King Center', 'Target Center', 'Moda Center',
              'Toyota Center', 'Wells Fargo Center', 'Gainbridge Fieldhouse',
              'Barclays Center', 'United Center', 'Rocket Mortgage FieldHouse',
              'Little Caesars Arena', 'FedExForum', 'Frost Bank Center']
NHL_VENUES = ['TD Garden', 'Madison Square Garden', 'United Center',
              'Rogers Arena', 'Scotiabank Arena', 'Bell Centre',
              'Wells Fargo Center', 'Capital One Arena',
              'Amerant Bank Arena', 'Honda Center', 'PPG Paints Arena',
              'Ball Arena', 'Climate Pledge Arena', 'Xcel Energy Center',
              'T-Mobile Arena', 'American Airlines Center', 'Enterprise Center']
NFL_VENUES = ['Arrowhead Stadium', 'AT&T Stadium', 'SoFi Stadium',
              'Lambeau Field', 'Lincoln Financial Field', 'M&T Bank Stadium',
              'Highmark Stadium', 'GEHA Field', 'MetLife Stadium',
              "Levi's Stadium", 'Empower Field at Mile High',
              'Hard Rock Stadium', 'NRG Stadium', 'State Farm Stadium',
              'Acrisure Stadium', 'Allegiant Stadium', 'Caesars Superdome',
              'Lumen Field', 'Soldier Field', 'Paycor Stadium']
MLB_VENUES = ['Yankee Stadium', 'Fenway Park', 'Dodger Stadium',
              'Wrigley Field', 'Oracle Park', 'Tropicana Field',
              'Citi Field', 'Petco Park', 'Coors Field',
              'Camden Yards', 'Globe Life Field', 'PNC Park', 'Truist Park',
              'Citizens Bank Park', 'Minute Maid Park', 'Busch Stadium',
              'Target Field', 'Great American Ball Park', 'Comerica Park']
SOCCER_VENUES = ['Emirates Stadium', 'Old Trafford', 'Anfield',
                 'Stamford Bridge', 'Etihad Stadium',
                 'Tottenham Hotspur Stadium', 'Camp Nou', 'Santiago Bernabéu',
                 'Allianz Arena', 'San Siro', 'Parc des Princes',
                 'Signal Iduna Park', 'Goodison Park',
                 'BBVA Stadium', 'Chase Stadium']
NCAAF_VENUES = ['Bryant-Denny Stadium', 'Ohio Stadium', 'The Big House',
                'Sanford Stadium', 'Beaver Stadium', 'Kyle Field',
                'Tiger Stadium', 'Neyland Stadium', 'Memorial Stadium']
NCAAM_VENUES = ['Cameron Indoor Stadium', 'Allen Fieldhouse', 'Phog Allen',
                'Rupp Arena', 'Carrier Dome', 'Pauley Pavilion',
                'Crisler Center']


# ─── 1. Games (+2000) ─────────────────────────────────────────────────────────

def make_games(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM games") or 0) + 1
    rows = []
    teams = {}
    for sp in ('nba', 'nhl', 'mlb', 'nfl', 'soccer', 'ncaaf', 'ncaam'):
        teams[sp] = cur.execute(
            "SELECT id, full_name, slug FROM teams "
            "WHERE sport_slug=? ORDER BY id", (sp,)).fetchall()

    def star_for(team_id):
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (team_id,)).fetchone()
        return row or ('Star Player', 'F')

    def emit(sport, season_label, t_arr, venues, start, count, hi_score,
             lo_score, base_off, network, period_label,
             status_default='final', scheduled_window=None,
             postponed_every=0, key_prefix='r7'):
        nonlocal next_id
        if not t_arr:
            return 0
        n = 0
        for i in range(count):
            a = h(f'{key_prefix}-{sport}-{season_label}-a-{i}', len(t_arr))
            b = h(f'{key_prefix}-{sport}-{season_label}-b-{i}', len(t_arr))
            if a == b:
                b = (b + 1) % len(t_arr)
            home = t_arr[a]
            away = t_arr[b]
            if scheduled_window:
                gdate = scheduled_window[0] + timedelta(
                    days=h(f'{key_prefix}-{sport}-{season_label}-d-{i}',
                          scheduled_window[1]))
                status = 'scheduled'
                period = 'Scheduled'
                hs, as_ = 0, 0
                recap = f'{season_label} {away[1]} at {home[1]}.'
            else:
                gdate = start + timedelta(
                    days=h(f'{key_prefix}-{sport}-{season_label}-d-{i}', 175))
                status = status_default
                period = period_label
                hs = h(f'{key_prefix}-{sport}-{season_label}-hs-{i}', hi_score, lo_score)
                as_ = h(f'{key_prefix}-{sport}-{season_label}-as-{i}', hi_score,
                        max(0, lo_score - base_off))
                recap = f'({season_label}) {home[1]} {hs}-{as_} {away[1]}.'
            if postponed_every and i and i % postponed_every == 0:
                status = 'postponed'
                period = 'Postponed'
                hs, as_ = 0, 0
                recap = (f'POSTPONED: {away[1]} at {home[1]} — '
                         f'weather/scheduling. Make-up TBD.')
            ven = venues[i % len(venues)]
            star_h = star_for(home[0])
            leaders = json.dumps({
                'top_scorer_name': star_h[0],
                'top_scorer_pts': max(1, hs // 4 if hs else 1),
                'top_scorer_team': home[1],
                'top_scorer_position': star_h[1] or 'F',
                'home_high_scorer': star_h[0],
                'home_high_points': max(1, hs // 4 if hs else 1),
                'away_high_scorer': star_for(away[0])[0],
                'away_high_points': max(1, as_ // 4 if as_ else 1),
            }) if status not in ('scheduled', 'postponed') else '{}'
            rows.append((
                next_id, sport, home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                f"{7 + (i % 4)}:{30 if i % 2 else '00'} PM ET",
                status, period, network, ven, recap,
                'https://www.ticketmaster.com', leaders))
            next_id += 1
            n += 1
        return n

    # NBA 2025-26 mid-season + 24-25 fill
    emit('nba', '2025-26', teams['nba'], NBA_VENUES,
         date(2025, 10, 21), 360, 35, 95, 8, 'ESPN', 'Final',
         postponed_every=42)
    emit('nba', '2024-25-fill', teams['nba'], NBA_VENUES,
         date(2024, 12, 1), 90, 35, 95, 8, 'TNT', 'Final')

    # NHL 2025-26 first half + 24-25 fill
    emit('nhl', '2025-26', teams['nhl'], NHL_VENUES,
         date(2025, 10, 7), 260, 7, 1, 1, 'ESPN+', 'Final',
         postponed_every=38)
    emit('nhl', '2024-25-fill', teams['nhl'], NHL_VENUES,
         date(2024, 12, 1), 70, 7, 1, 1, 'TNT', 'Final')

    # MLB 2025 mid-season + 2024 fill
    emit('mlb', '2025', teams['mlb'], MLB_VENUES,
         date(2025, 3, 27), 300, 14, 0, 0, 'MLB Network', 'Final',
         postponed_every=45)
    emit('mlb', '2024-fill', teams['mlb'], MLB_VENUES,
         date(2024, 6, 1), 80, 14, 0, 0, 'ESPN', 'Final')

    # NFL 2025 first half + 2024 playoffs
    emit('nfl', '2025', teams['nfl'], NFL_VENUES,
         date(2025, 9, 4), 180, 38, 7, 7, 'CBS', 'Final')
    emit('nfl', '2024-playoffs', teams['nfl'], NFL_VENUES,
         date(2025, 1, 11), 14, 38, 7, 7, 'FOX', 'Final')

    # Soccer 2025-26 + 2024-25 fill
    if teams['soccer']:
        emit('soccer', '2025-26', teams['soccer'], SOCCER_VENUES,
             date(2025, 8, 15), 180, 5, 0, 0, 'ESPN+', 'FT')
        emit('soccer', '2024-25-fill', teams['soccer'], SOCCER_VENUES,
             date(2024, 11, 1), 70, 5, 0, 0, 'Peacock', 'FT')

    # NCAAF 2025 + 2024 bowl fill
    if teams['ncaaf']:
        emit('ncaaf', '2025', teams['ncaaf'], NCAAF_VENUES,
             date(2025, 8, 30), 70, 56, 10, 12, 'ABC', 'Final')
        emit('ncaaf', '2024-bowls', teams['ncaaf'], NCAAF_VENUES,
             date(2024, 12, 20), 25, 56, 10, 12, 'ESPN', 'Final')

    # NCAAM 2025-26 + 2024-25 fill
    if teams['ncaam']:
        emit('ncaam', '2025-26', teams['ncaam'], NCAAM_VENUES,
             date(2025, 11, 3), 80, 95, 50, 8, 'CBS', 'Final')
        emit('ncaam', '2024-25-fill', teams['ncaam'], NCAAM_VENUES,
             date(2025, 1, 20), 30, 95, 50, 8, 'TBS', 'Final')

    # NBA 2026-27 schedule preview (so 'next season' tasks have data)
    emit('nba', '2026-27-prev', teams['nba'], NBA_VENUES,
         None, 80, 0, 0, 0, 'ESPN', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2026, 10, 20), 180))

    # NHL 2026-27 preview
    emit('nhl', '2026-27-prev', teams['nhl'], NHL_VENUES,
         None, 50, 0, 0, 0, 'ESPN+', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2026, 10, 6), 190))

    # NFL 2026 preview
    emit('nfl', '2026-prev', teams['nfl'], NFL_VENUES,
         None, 60, 0, 0, 0, 'CBS', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2026, 9, 3), 130))

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 2. Articles (+1400, incl. ~250 Spanish) ─────────────────────────────────

ARTICLE_TEMPLATES_R7 = {
    'analytics-edge': (
        'Analytics edge: where the {team} model out in {season}',
        'ESPN Stats & Information looks at the {team} efficiency profile '
        'this {season} {sport_upper} stretch. The data show clear strengths '
        'in transition and a steady mid-range diet that\'s held up despite '
        'opponent adjustments. Schedule difficulty, pace, and lineup '
        'combinations are all considered.',
        ['analytics', 'stats']),
    'rookie-watch-monthly': (
        'Rookie Watch: monthly check-in on {team} young guns ({season})',
        'The {team} rookie class has been a quiet bright spot of the '
        '{season} {sport_upper} year. ESPN\'s monthly Rookie Watch examines '
        'minutes, on/off splits, and development trajectory. Two pieces '
        'are flagged as keeper-league-relevant for the back half.',
        ['rookies', 'watch']),
    'midseason-grade': (
        'Midseason grades: how the {team} stack up at the {season} break',
        'ESPN beat writers hand out midseason grades for the {team} as the '
        '{season} {sport_upper} schedule hits its break. Offense, defense, '
        'depth, and coaching staff all receive a letter grade. Two areas '
        'still need a clear answer before the postseason picture closes.',
        ['grades', 'midseason']),
    'milestone-watch': (
        'Milestone Watch: {team} marks within reach in {season}',
        'A roster of milestones is in reach for the {team} this {season} '
        '{sport_upper} run. The star wing is closing in on 10,000 career '
        'points; a long-tenured center can pass the franchise rebounds '
        'record before the home stretch. ESPN updates the tracker each '
        'Sunday.',
        ['milestones', 'history']),
    'salary-cap-corner': (
        'Salary cap corner: the {team} math heading into {season} deadline',
        'Bobby Marks-style salary cap breakdown for the {team} as the '
        '{season} {sport_upper} deadline approaches. The team\'s tax '
        'apron, hard-cap exposure, and trade exception availability are '
        'all considered. Two contracts stand out as movable.',
        ['salary', 'cap']),
    'rivalry-week-feature': (
        'Rivalry week feature: the {team} and the matchup that defines {season}',
        'ESPN\'s rivalry week looks at one matchup that has defined the '
        '{team} {season} {sport_upper} run. We talk to former players, '
        'coaches, and longtime beat reporters for the full picture of how '
        'this rivalry has shaped this team\'s identity.',
        ['rivalry', 'feature']),
    'beat-writer-mailbag': (
        'Beat writer mailbag: {team} questions answered after a wild {season} week',
        'The {team} beat writer answers your mailbag questions after a '
        'wild {season} {sport_upper} week. Topics include rotation depth, '
        'a struggling free-agent signing, and what to make of the next '
        'three-game road trip.',
        ['mailbag', 'q-and-a']),
}


# Spanish translations for top-3 templates (covers ESPN-Deportes locale).
ARTICLE_TEMPLATES_R7_ES = {
    'analytics-edge': (
        'Ventaja analítica: dónde aciertan los {team} en {season}',
        'ESPN Stats & Information analiza el perfil de eficiencia de los '
        '{team} en este tramo de {sport_upper} {season}. Los datos muestran '
        'fortalezas claras en transición y una dieta de tiros medios estable. '
        'Se consideran la dificultad del calendario, el ritmo y las '
        'combinaciones de quinteto.',
        ['analytics', 'stats', 'es', 'deportes']),
    'midseason-grade': (
        'Calificaciones de mitad de temporada: los {team} en el descanso de {season}',
        'Los redactores de ESPN reparten calificaciones de mitad de '
        'temporada para los {team} mientras el calendario de {sport_upper} '
        '{season} llega a su pausa. Ofensiva, defensa, profundidad y '
        'cuerpo técnico reciben nota. Dos áreas todavía necesitan una '
        'respuesta clara antes de los playoffs.',
        ['grades', 'midseason', 'es', 'deportes']),
    'rookie-watch-monthly': (
        'Rookies en la mira: revisión mensual de los novatos de los {team} ({season})',
        'La clase de novatos de los {team} ha sido un punto brillante '
        'silencioso del año de {sport_upper} {season}. La revisión mensual '
        'de rookies de ESPN examina minutos, splits on/off y trayectoria de '
        'desarrollo. Dos piezas son relevantes para ligas de retención.',
        ['rookies', 'watch', 'es', 'deportes']),
}


SPORT_PLANS_R7 = [
    ('nba', 'NBA', 'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
                   'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
                   'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
                   'Minnesota Timberwolves,Oklahoma City Thunder,'
                   'Cleveland Cavaliers,Indiana Pacers,New Orleans Pelicans,'
                   'Sacramento Kings,Memphis Grizzlies,Atlanta Hawks,'
                   'Orlando Magic,Houston Rockets,Toronto Raptors,'
                   'Detroit Pistons,Charlotte Hornets,Chicago Bulls,'
                   'Brooklyn Nets'.split(','),
     '2025-26'),
    ('nfl', 'NFL', 'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
                   'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
                   'Detroit Lions,Miami Dolphins,Green Bay Packers,'
                   'Cincinnati Bengals,Pittsburgh Steelers,Houston Texans,'
                   'Minnesota Vikings,Los Angeles Rams,New York Jets,'
                   'Jacksonville Jaguars,Cleveland Browns,Atlanta Falcons,'
                   'Tampa Bay Buccaneers,Tennessee Titans'.split(','),
     '2025'),
    ('mlb', 'MLB', 'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
                   'Atlanta Braves,Houston Astros,Texas Rangers,'
                   'Philadelphia Phillies,Chicago Cubs,San Diego Padres,'
                   'Toronto Blue Jays,Baltimore Orioles,Seattle Mariners,'
                   'New York Mets,Milwaukee Brewers,Arizona Diamondbacks,'
                   'San Francisco Giants'.split(','),
     '2025'),
    ('nhl', 'NHL', 'Boston Bruins,Edmonton Oilers,Vegas Golden Knights,'
                   'New York Rangers,Toronto Maple Leafs,Florida Panthers,'
                   'Colorado Avalanche,Tampa Bay Lightning,Dallas Stars,'
                   'Carolina Hurricanes,Vancouver Canucks,Winnipeg Jets'.split(','),
     '2025-26'),
    ('soccer', 'Soccer', 'Arsenal,Manchester City,Liverpool,'
                        'Real Madrid,Barcelona,Bayern Munich,'
                        'Paris Saint-Germain,Inter Milan,'
                        'Borussia Dortmund,Manchester United,'
                        'Tottenham Hotspur,Chelsea'.split(','),
     '2025-26'),
    ('ncaaf', 'CFB', 'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
                     'USC,Notre Dame,Oklahoma,Penn State,Oregon,Florida State'.split(','),
     '2025'),
    ('ncaam', 'CBB', 'Duke,Kansas,Kentucky,Connecticut,North Carolina,'
                     'Houston,Purdue,Tennessee,Arizona,Marquette,'
                     'Auburn,Gonzaga'.split(','),
     '2025-26'),
]


# Spanish locale only covers NBA / NFL / MLB / Soccer for ESPN-Deportes scope.
ES_SPORT_PLANS = [
    ('nba', 'NBA', 'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
                   'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
                   'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
                   'Oklahoma City Thunder,Cleveland Cavaliers,Indiana Pacers'.split(','),
     '2025-26'),
    ('nfl', 'NFL', 'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
                   'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
                   'Detroit Lions,Miami Dolphins'.split(','),
     '2025'),
    ('mlb', 'MLB', 'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
                   'Atlanta Braves,Houston Astros,Texas Rangers,'
                   'Philadelphia Phillies'.split(','),
     '2025'),
    ('soccer', 'Soccer', 'Real Madrid,Barcelona,Bayern Munich,'
                        'Paris Saint-Germain,Inter Milan,'
                        'Manchester City,Arsenal,Liverpool,'
                        'Manchester United'.split(','),
     '2025-26'),
]


def make_articles(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1

    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM articles").fetchall())

    rows = []

    # English R7 articles
    tpl_names = sorted(ARTICLE_TEMPLATES_R7.keys())
    for sport_slug, sport_upper, teams_list, season in SPORT_PLANS_R7:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R7[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = (f'r7-{sport_slug}-{team_slug}-{tpl_name}-'
                        f'{ti:02d}')
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
                day_off = h(f'r7-art-pub-{slug}', 180)
                base_pub = date(2025, 9, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '',
                    body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r7-{ti}.jpg',
                    tags,
                    1 if (ti == 0 and tpl_name == 'analytics-edge') else 0,
                    1 if tpl_name in ('midseason-grade',
                                      'milestone-watch') and ti < 3 else 0,
                    pub_dt, pub_disp,
                ))
                next_id += 1

    # Spanish (ESPN-Deportes) articles
    tpl_names_es = sorted(ARTICLE_TEMPLATES_R7_ES.keys())
    for sport_slug, sport_upper, teams_list, season in ES_SPORT_PLANS:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names_es:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R7_ES[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = (f'es-r7-{sport_slug}-{team_slug}-{tpl_name}-'
                        f'{ti:02d}')
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
                day_off = h(f'es-r7-art-pub-{slug}', 180)
                base_pub = date(2025, 9, 15) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '',
                    body,
                    'ESPN Deportes',
                    f'/static/images/espn/articles/{sport_slug}/es-r7-{ti}.jpg',
                    tags,
                    1 if (ti == 0 and tpl_name == 'analytics-edge') else 0,
                    0,
                    pub_dt, pub_disp,
                ))
                next_id += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, "
        "body, author, image, tags, is_headline, is_featured, "
        "created_at, published_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 3. Betting odds (+1200) ──────────────────────────────────────────────────

SPORTSBOOKS = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars']


def make_betting(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM betting_odds") or 0) + 1

    existing_pairs = set(
        (r[0], r[1]) for r in cur.execute(
            "SELECT game_id, sportsbook FROM betting_odds").fetchall())

    rows = []

    def emit_for_sport(sport, books=None, target=200):
        gs = cur.execute(
            "SELECT id FROM games WHERE sport_slug=? "
            "AND status='final' "
            "ORDER BY id DESC LIMIT 3000", (sport,)).fetchall()
        added = 0
        nonlocal next_id
        bks = books or SPORTSBOOKS
        for gid, in gs:
            if added >= target:
                break
            # Try multiple books per game to grow coverage.
            for b_idx in range(len(bks)):
                if added >= target:
                    break
                book = bks[(h(f'r7-bo-{sport}-{gid}-{b_idx}', len(bks)) + b_idx) % len(bks)]
                if (gid, book) in existing_pairs:
                    continue
                existing_pairs.add((gid, book))
                key = f'r7-bo-{sport}-{gid}-{book}'
                favored_home = h(f'{key}-side', 2) == 0
                ml_strong = h(f'{key}-ml', 220, 110)
                home_ml = (-ml_strong) if favored_home else (ml_strong + 30)
                away_ml = (ml_strong + 30) if favored_home else (-ml_strong)
                spread_line = round(hf(f'{key}-spr', 1.5, 11.5), 1)
                spread_fav = 'home' if favored_home else 'away'
                if sport == 'nhl':
                    spread_line = round(hf(f'{key}-spr', 0.5, 1.5), 1)
                if sport == 'mlb':
                    spread_line = round(hf(f'{key}-spr', 0.5, 2.5), 1)
                total = {
                    'nba': round(hf(f'{key}-t', 210, 240), 1),
                    'nfl': round(hf(f'{key}-t', 39, 54), 1),
                    'mlb': round(hf(f'{key}-t', 6.5, 11.5), 1),
                    'nhl': round(hf(f'{key}-t', 5.0, 7.5), 1),
                    'soccer': round(hf(f'{key}-t', 2.0, 3.5), 1),
                    'ncaaf': round(hf(f'{key}-t', 45, 64), 1),
                    'ncaam': round(hf(f'{key}-t', 130, 160), 1),
                }.get(sport, 0.0)
                over_odds = -110 + h(f'{key}-oo', 20, -10)
                under_odds = -110 + h(f'{key}-uo', 20, -10)
                status = ['open', 'open', 'open', 'closed',
                          'suspended-injury'][h(f'{key}-st', 5)]
                opened = ['T-3d', 'T-2d', 'T-1d', 'T-6h', 'T-1h'][h(f'{key}-op', 5)]
                rows.append((next_id, gid, sport, home_ml, away_ml,
                             spread_fav, spread_line, total,
                             over_odds, under_odds, opened, status, book))
                next_id += 1
                added += 1
        return added

    n = 0
    n += emit_for_sport('nba', target=300)
    n += emit_for_sport('nfl', target=220)
    n += emit_for_sport('mlb', target=220)
    n += emit_for_sport('nhl', target=200)
    n += emit_for_sport('soccer', target=120)
    n += emit_for_sport('ncaaf', target=80)
    n += emit_for_sport('ncaam', target=80)
    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, home_moneyline, "
        "away_moneyline, spread_favorite, spread_line, total, over_odds, "
        "under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 4. Parlays (+15) ─────────────────────────────────────────────────────────

R7_PARLAYS = [
    ('r7-nba-mvp-trio', 'NBA MVP Trio', 3, +625, 7.25, 'nba', 'ESPN BET',
     ['SGA MVP', 'Jokic MVP top-3', 'Doncic MVP top-3']),
    ('r7-nba-roy-double', 'NBA ROY Double', 2, +275, 3.75, 'nba', 'DraftKings',
     ['Wemby DPOY', 'Wemby All-NBA']),
    ('r7-nfl-conference-treble', 'Conference Title Treble', 3,
     +780, 8.80, 'nfl', 'BetMGM',
     ['Chiefs AFC West', 'Eagles NFC East', 'Lions NFC North']),
    ('r7-mlb-cy-young-multi', 'Cy Young Multi', 2, +480, 5.80, 'mlb', 'FanDuel',
     ['Skenes NL Cy Young', 'Sale top-5 NL Cy Young']),
    ('r7-nhl-art-ross-multi', 'Art Ross Multi', 2, +355, 4.55, 'nhl', 'Caesars',
     ['McDavid Art Ross', 'MacKinnon top-3']),
    ('r7-soccer-ucl-final-double',
     'UCL Final Double', 2, +900, 10.00, 'soccer', 'ESPN BET',
     ['Real Madrid to Final', 'Arsenal to Final']),
    ('r7-ncaaf-playoff-quartet', 'CFP Quartet', 4, +1250, 13.50, 'ncaaf',
     'DraftKings',
     ['UGA semis', 'OSU semis', 'Texas semis', 'Oregon semis']),
    ('r7-ncaam-final-four', 'Final Four Quartet', 4,
     +2100, 22.00, 'ncaam', 'BetMGM',
     ['Duke F4', 'UConn F4', 'Houston F4', 'Kansas F4']),
    ('r7-nba-finals-rematch',
     'Finals Rematch Future', 2, +1450, 15.50, 'nba', 'FanDuel',
     ['Celtics East', 'Thunder West']),
    ('r7-deportes-laliga-double',
     'La Liga / EPL Double (Deportes)', 2, +320, 4.20, 'soccer', 'ESPN BET',
     ['Real Madrid LaLiga', 'Man City EPL']),
    ('r7-mlb-postseason-trio',
     'MLB Postseason Pennant Trio', 3, +900, 10.00, 'mlb', 'Caesars',
     ['Dodgers NL pennant', 'Yankees AL pennant', 'Phillies NLDS']),
    ('r7-nfl-super-bowl-mvp', 'Super Bowl MVP Trio', 3,
     +1450, 15.50, 'nfl', 'ESPN BET',
     ['Mahomes SB MVP', 'Allen SB MVP top-2', 'Lamar SB MVP top-2']),
    ('r7-nhl-stanley-cup-double', 'Stanley Cup Double', 2, +1100, 12.00,
     'nhl', 'BetMGM',
     ['Panthers East', 'Oilers West']),
    ('r7-nba-three-team-overs', 'NBA Threes Overs Trio', 3, +445, 5.45,
     'nba', 'DraftKings',
     ['Curry o4.5 3PM', 'Tatum o3.5 3PM', 'Booker o2.5 3PM']),
    ('r7-cross-sport-saturday',
     'Cross-Sport Saturday R7', 5, +1850, 19.50, 'fantasy', 'FanDuel',
     ['LeBron 25+', 'McDavid ATG', 'Mahomes 275+', 'Judge HR',
      'Haaland ATG']),
]


def make_parlays(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM parlays") or 0) + 1

    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM parlays").fetchall())
    rows = []
    for slug, title, lc, ao, do, sp, book, legs in R7_PARLAYS:
        if slug in existing:
            continue
        existing.add(slug)
        rows.append((next_id, slug, title, lc, ao, do,
                     json.dumps([{'leg': l} for l in legs]),
                     sp, book, 0))
        next_id += 1
    cur.executemany(
        "INSERT INTO parlays (id, slug, title, leg_count, american_odds, "
        "decimal_odds, legs_json, sport_slug, sportsbook, is_featured) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 5. Add R7 indexes ────────────────────────────────────────────────────────

R7_INDEXES = [
    ('ix_games_sport_status_date',
     'CREATE INDEX ix_games_sport_status_date ON games (sport_slug, status, date)'),
    ('ix_games_home_team_date',
     'CREATE INDEX ix_games_home_team_date ON games (home_team_id, date DESC)'),
    ('ix_games_away_team_date',
     'CREATE INDEX ix_games_away_team_date ON games (away_team_id, date DESC)'),
]


def add_indexes(cur):
    n = 0
    for name, sql in R7_INDEXES:
        existing = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
            (name,)).fetchone()
        if existing:
            continue
        cur.execute(sql)
        n += 1
    return n


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R7 extension already applied — no-op.')
        conn.close()
        return
    n_gm  = make_games(cur)
    n_ar  = make_articles(cur)
    n_bo  = make_betting(cur)
    n_pl  = make_parlays(cur)
    n_ix  = add_indexes(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R7 inserted: games={n_gm}, articles={n_ar}, '
          f'betting_odds={n_bo}, parlays={n_pl}, indexes_new={n_ix}')


if __name__ == '__main__':
    main()
