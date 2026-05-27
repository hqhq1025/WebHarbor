#!/usr/bin/env python3
"""R9 polish extension for sites/espn — direct sqlite3 INSERT only.

Continues gotcha #14 path: HF seed has drifted from seed_data.py, so we
extend the live DB with idempotent direct INSERTs.

R9 on top of R8 baseline (games 9552 / articles 7268 / betting 4010 /
parlays 95 / tasks 4132):

  * +2500+ games        (9552 → 12000+)  NBA 2027-28 reg-season, NHL 26-27
                                         deepen, MLB 2026 late-season, NFL
                                         2026 reg deepen, soccer 26-27 full,
                                         ncaaf 2026 reg, ncaam 26-27 deepen.
  * +2300+ articles     (7268 → 9500+)   6 EN ESPN BET / fantasy / NIL
                                         templates × 7 sports + ES + deeper
                                         magazine cross-sport.
  * +1500+ betting_odds (4010 → 5500+)   cross-book coverage of R9 games.
  * +20 parlays
  * Marker row sports.slug '_r9_marker' — idempotent.
  * Re-emit indexes alpha-sorted + VACUUM (gotcha #2) for byte-id reset.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r9_marker` row in `sports`.
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
        "SELECT 1 FROM sports WHERE slug='_r9_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (107, 'R9 marker', '_r9_marker', 'r9_extend applied',
         '/_internal/', 107, 0))


def normalize(cur):
    """Drop+recreate every ix_* index in alpha order — gotcha #2."""
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── Venues (re-use R8 sets) ──────────────────────────────────────────────────

NBA_VENUES = ['TD Garden', 'Crypto.com Arena', 'Madison Square Garden',
              'Chase Center', 'Ball Arena', 'Paycom Center',
              'Kaseya Center', 'American Airlines Center',
              'Footprint Center', 'Fiserv Forum', 'Spectrum Center',
              'Smoothie King Center', 'Target Center', 'Moda Center',
              'Toyota Center', 'Wells Fargo Center', 'Gainbridge Fieldhouse',
              'Barclays Center', 'United Center',
              'Rocket Mortgage FieldHouse', 'Little Caesars Arena',
              'FedExForum', 'Frost Bank Center', 'State Farm Arena',
              'Kia Center', 'Delta Center', 'Intuit Dome']
NHL_VENUES = ['TD Garden', 'Madison Square Garden', 'United Center',
              'Rogers Arena', 'Scotiabank Arena', 'Bell Centre',
              'Wells Fargo Center', 'Capital One Arena',
              'Amerant Bank Arena', 'Honda Center', 'PPG Paints Arena',
              'Ball Arena', 'Climate Pledge Arena', 'Xcel Energy Center',
              'T-Mobile Arena', 'American Airlines Center',
              'Enterprise Center', 'Nationwide Arena', 'KeyBank Center']
NFL_VENUES = ['Arrowhead Stadium', 'AT&T Stadium', 'SoFi Stadium',
              'Lambeau Field', 'Lincoln Financial Field', 'M&T Bank Stadium',
              'Highmark Stadium', 'GEHA Field', 'MetLife Stadium',
              "Levi's Stadium", 'Empower Field at Mile High',
              'Hard Rock Stadium', 'NRG Stadium', 'State Farm Stadium',
              'Acrisure Stadium', 'Allegiant Stadium', 'Caesars Superdome',
              'Lumen Field', 'Soldier Field', 'Paycor Stadium',
              'Gillette Stadium', 'EverBank Stadium']
MLB_VENUES = ['Yankee Stadium', 'Fenway Park', 'Dodger Stadium',
              'Wrigley Field', 'Oracle Park', 'Tropicana Field',
              'Citi Field', 'Petco Park', 'Coors Field',
              'Camden Yards', 'Globe Life Field', 'PNC Park', 'Truist Park',
              'Citizens Bank Park', 'Minute Maid Park', 'Busch Stadium',
              'Target Field', 'Great American Ball Park', 'Comerica Park',
              'American Family Field', 'loanDepot Park', 'Rogers Centre']
SOCCER_VENUES = ['Emirates Stadium', 'Old Trafford', 'Anfield',
                 'Stamford Bridge', 'Etihad Stadium',
                 'Tottenham Hotspur Stadium', 'Camp Nou', 'Santiago Bernabéu',
                 'Allianz Arena', 'San Siro', 'Parc des Princes',
                 'Signal Iduna Park', 'Goodison Park',
                 'BBVA Stadium', 'Chase Stadium', 'BMO Stadium',
                 'Mercedes-Benz Stadium', 'Audi Field']
NCAAF_VENUES = ['Bryant-Denny Stadium', 'Ohio Stadium', 'The Big House',
                'Sanford Stadium', 'Beaver Stadium', 'Kyle Field',
                'Tiger Stadium', 'Neyland Stadium', 'Memorial Stadium',
                'Doak Campbell Stadium', 'Autzen Stadium']
NCAAM_VENUES = ['Cameron Indoor Stadium', 'Allen Fieldhouse', 'Phog Allen',
                'Rupp Arena', 'Carrier Dome', 'Pauley Pavilion',
                'Crisler Center', 'Dean E. Smith Center']


# ─── 1. Games (+2500) ─────────────────────────────────────────────────────────

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
             postponed_every=0, key_prefix='r9'):
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
                hs = h(f'{key_prefix}-{sport}-{season_label}-hs-{i}',
                       hi_score, lo_score)
                as_ = h(f'{key_prefix}-{sport}-{season_label}-as-{i}',
                        hi_score, max(0, lo_score - base_off))
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

    # NBA 2027-28 full season opener arc
    emit('nba', '2027-28-final', teams['nba'], NBA_VENUES,
         date(2027, 10, 19), 480, 35, 95, 8, 'ESPN', 'Final',
         postponed_every=44)
    emit('nba', '2027-28-sched', teams['nba'], NBA_VENUES,
         None, 140, 0, 0, 0, 'ABC', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2027, 12, 20), 100))

    # NHL 2026-27 deepen
    emit('nhl', '2026-27-deep', teams['nhl'], NHL_VENUES,
         date(2026, 11, 1), 240, 7, 1, 1, 'ESPN+', 'Final',
         postponed_every=40)

    # MLB 2026 late-season
    emit('mlb', '2026-late', teams['mlb'], MLB_VENUES,
         date(2026, 7, 5), 320, 14, 0, 0, 'MLB Network', 'Final',
         postponed_every=45)
    emit('mlb', '2026-postseason', teams['mlb'], MLB_VENUES,
         date(2026, 10, 2), 50, 12, 1, 1, 'FOX', 'Final')

    # NFL 2026 reg-season deepen + 2026 postseason fill
    emit('nfl', '2026-reg-deep', teams['nfl'], NFL_VENUES,
         date(2026, 10, 5), 180, 38, 7, 7, 'CBS', 'Final',
         postponed_every=48)
    emit('nfl', '2026-postseason', teams['nfl'], NFL_VENUES,
         date(2027, 1, 9), 14, 38, 10, 10, 'FOX', 'Final')

    # Soccer 26-27 full
    if teams['soccer']:
        emit('soccer', '2026-27-deep', teams['soccer'], SOCCER_VENUES,
             date(2026, 9, 10), 280, 5, 0, 0, 'ESPN+', 'FT')
        emit('soccer', '2026-27-cup-prev', teams['soccer'], SOCCER_VENUES,
             None, 60, 0, 0, 0, 'Peacock', 'Scheduled',
             status_default='scheduled',
             scheduled_window=(date(2027, 4, 1), 60))

    # NCAAF 2026 reg-season deeper
    if teams['ncaaf']:
        emit('ncaaf', '2026-reg-deep', teams['ncaaf'], NCAAF_VENUES,
             date(2026, 10, 5), 90, 56, 10, 12, 'ABC', 'Final')

    # NCAAM 2026-27 deepen + 2027-28 schedule preview
    if teams['ncaam']:
        emit('ncaam', '2026-27-deep', teams['ncaam'], NCAAM_VENUES,
             date(2026, 12, 5), 130, 95, 50, 8, 'CBS', 'Final')
        emit('ncaam', '2027-28-prev', teams['ncaam'], NCAAM_VENUES,
             None, 40, 0, 0, 0, 'ESPN', 'Scheduled',
             status_default='scheduled',
             scheduled_window=(date(2027, 11, 5), 120))

    # Extra retroactive depth — 2022-23 NBA fill, NFL 2023 fill, MLB 2024 fill
    emit('nba', '2022-23-fill', teams['nba'], NBA_VENUES,
         date(2022, 11, 1), 200, 35, 95, 8, 'TNT', 'Final',
         postponed_every=50)
    emit('nfl', '2023-fill', teams['nfl'], NFL_VENUES,
         date(2023, 9, 5), 80, 38, 7, 7, 'NBC', 'Final')
    emit('mlb', '2024-fill', teams['mlb'], MLB_VENUES,
         date(2024, 6, 1), 90, 14, 0, 0, 'ESPN', 'Final')
    if teams['soccer']:
        emit('soccer', '2024-25-extra', teams['soccer'], SOCCER_VENUES,
             date(2024, 11, 1), 80, 5, 0, 0, 'ESPN+', 'FT')

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 2. Articles (+2300) ──────────────────────────────────────────────────────

ARTICLE_TEMPLATES_R9 = {
    'espn-bet-promo-deep': (
        '{team} betting outlook: ESPN BET promo codes worth tracking in {season}',
        'A deep look at how {team} {sport_upper} {season} bets pair with the '
        'current ESPN BET promo codes. We walk through SIGNUP100, NBARESET, '
        'and the rotating MVP25 boost, plus a guide to /espn-bet/promo for '
        'agents and aggregators trying to confirm a code is still live.',
        ['espn-bet', 'promo', 'betting', 'r9']),
    'fantasy-commissioner-tools': (
        '{team} fantasy commissioner tools: leagues to watch in {season}',
        'For commissioners running {team}-themed leagues in {sport_upper} '
        '{season}: a tour of /fantasy/league/<id>/commissioner — the new '
        'lineup-veto controls, custom scoring overrides, and how to push a '
        'manual playoff bracket. We close with a checklist for the trade '
        'deadline freeze.',
        ['fantasy', 'commissioner', 'r9']),
    'trade-veto-vote': (
        '{team} trade-veto vote explainer: how {sport_upper} {season} leagues handle it',
        'A primer on /fantasy/trade/<id>/veto-vote for {team} fans running '
        '{sport_upper} {season} leagues. We cover the 24-hour league-poll '
        'window, the commissioner override path, and three real-world veto '
        'examples that shaped public sentiment this season.',
        ['fantasy', 'trade', 'veto', 'r9']),
    'recruiting-247-flip': (
        '{team} 247 board flip watch: {season} commitments under pressure',
        'A snapshot of /recruiting/247-board for {team} fans tracking '
        '{sport_upper} {season} commits. We list five names with rising '
        'flip risk, the OOS visit calendar that drives them, and the booster '
        'collective that is pushing back. Updated weekly.',
        ['recruiting', '247', 'flip', 'r9']),
    'nil-deals-tracker': (
        '{team} NIL deals tracker: top {season} contracts and collectives',
        'The {team} entry on /nil/tracker for {sport_upper} {season}. We '
        'cover the largest disclosed deals, the booster-collective behind '
        'each, projected season-long valuations, and the league-office '
        'reporting requirements that will reshape disclosures in 2027.',
        ['nil', 'tracker', 'collective', 'r9']),
    'live-stream-drm': (
        '{team} live-stream DRM region notes: watching {season} from anywhere',
        'A working guide to /watch/live/<event>/drm for {team} {sport_upper} '
        '{season} broadcasts. We cover region-locked content, what the '
        'DRM widevine/playready/fairplay matrix looks like at the player '
        'level, and the ESPN+ entitlement check that fronts every stream.',
        ['watch', 'drm', 'live-stream', 'r9']),
    'multi-step-guide': (
        '{team} agent guide: chaining ESPN tools across {season}',
        'A practical guide for agents browsing {team} {sport_upper} {season} '
        'content. We walk a five-step chain — scoreboard → game detail → '
        'play-by-play → odds → fantasy waiver — and call out the URL '
        'patterns that always survive a reset.',
        ['agent', 'multi-step', 'guide', 'r9']),
}


ARTICLE_TEMPLATES_R9_ES = {
    'espn-bet-promo-es': (
        'Códigos promo de ESPN BET para los {team} en {season}',
        'Una mirada práctica a cómo combinar los códigos promo activos de '
        'ESPN BET con las apuestas más populares de los {team} en {sport_upper} '
        '{season}. Cubrimos SIGNUP100, NBARESET y la herramienta '
        '/espn-bet/promo para verificar códigos.',
        ['espn-bet', 'promo', 'r9']),
    'fantasy-commissioner-es': (
        'Herramientas de comisionado fantasy para los {team} en {season}',
        'Para comisionados de ligas con tema {team} en {sport_upper} '
        '{season}: un recorrido por /fantasy/league/<id>/commissioner, '
        'incluyendo vetos de alineación y ajustes de puntuación.',
        ['fantasy', 'comisionado', 'r9']),
    'nil-deals-es': (
        'NIL tracker {team}: principales contratos en {season}',
        'Una nota desde /nil/tracker sobre los {team} en {sport_upper} '
        '{season}. Cubrimos los acuerdos divulgados más grandes, los '
        'colectivos de boosters detrás de cada uno y la valoración '
        'proyectada para la temporada.',
        ['nil', 'r9']),
    'live-stream-drm-es': (
        'Notas DRM por región para transmisiones en vivo de los {team}',
        'Una guía operativa de /watch/live/<event>/drm para las '
        'transmisiones de {team} {sport_upper} {season}. Cubrimos contenido '
        'bloqueado por región y la verificación de derechos ESPN+.',
        ['watch', 'drm', 'r9']),
}


SPORT_PLANS_R9 = [
    ('nba', 'NBA',
     'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
     'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
     'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
     'Oklahoma City Thunder,Cleveland Cavaliers,Indiana Pacers,'
     'Minnesota Timberwolves,New Orleans Pelicans,Sacramento Kings,'
     'Memphis Grizzlies,Atlanta Hawks,Brooklyn Nets,Chicago Bulls,'
     'Houston Rockets,LA Clippers,Orlando Magic,Toronto Raptors,'
     'Detroit Pistons'.split(','),
     '2027-28'),
    ('nfl', 'NFL',
     'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
     'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
     'Detroit Lions,Miami Dolphins,Green Bay Packers,'
     'Cincinnati Bengals,Pittsburgh Steelers,Houston Texans,'
     'New York Giants,Los Angeles Rams,Tampa Bay Buccaneers,'
     'Atlanta Falcons,Seattle Seahawks,Minnesota Vikings,'
     'Las Vegas Raiders,Indianapolis Colts'.split(','),
     '2026'),
    ('mlb', 'MLB',
     'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
     'Atlanta Braves,Houston Astros,Texas Rangers,'
     'Philadelphia Phillies,Chicago Cubs,San Diego Padres,'
     'Toronto Blue Jays,New York Mets,Seattle Mariners,'
     'Baltimore Orioles,Cleveland Guardians,St. Louis Cardinals,'
     'Milwaukee Brewers'.split(','),
     '2026'),
    ('nhl', 'NHL',
     'Boston Bruins,Edmonton Oilers,Vegas Golden Knights,'
     'New York Rangers,Toronto Maple Leafs,Florida Panthers,'
     'Colorado Avalanche,Tampa Bay Lightning,Carolina Hurricanes,'
     'Dallas Stars,Vancouver Canucks,New Jersey Devils'.split(','),
     '2026-27'),
    ('soccer', 'Soccer',
     'Arsenal,Manchester City,Liverpool,'
     'Real Madrid,Barcelona,Bayern Munich,'
     'Paris Saint-Germain,Inter Milan,Manchester United,'
     'Chelsea,Atletico Madrid,Juventus,Tottenham Hotspur'.split(','),
     '2026-27'),
    ('ncaaf', 'CFB',
     'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
     'USC,Notre Dame,Oregon,Penn State,Florida State,Clemson'.split(','),
     '2026'),
    ('ncaam', 'CBB',
     'Duke,Kansas,Kentucky,Connecticut,North Carolina,'
     'Houston,Purdue,Arizona,UCLA,Tennessee,Auburn'.split(','),
     '2026-27'),
]

ES_SPORT_PLANS_R9 = [
    ('nba', 'NBA',
     'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
     'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
     'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
     'Oklahoma City Thunder'.split(','),
     '2027-28'),
    ('nfl', 'NFL',
     'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
     'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
     'Detroit Lions'.split(','),
     '2026'),
    ('soccer', 'Soccer',
     'Real Madrid,Barcelona,Bayern Munich,'
     'Paris Saint-Germain,Inter Milan,Manchester City,'
     'Arsenal,Liverpool,Atletico Madrid'.split(','),
     '2026-27'),
    ('ncaaf', 'CFB',
     'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
     'USC,Notre Dame'.split(','),
     '2026'),
]


def make_articles(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM articles").fetchall())

    rows = []
    tpl_names = sorted(ARTICLE_TEMPLATES_R9.keys())
    for sport_slug, sport_upper, teams_list, season in SPORT_PLANS_R9:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R9[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'r9-{sport_slug}-{team_slug}-{tpl_name}-00'
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
                day_off = h(f'r9-art-pub-{slug}', 180)
                base_pub = date(2026, 3, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r9-{ti}.jpg',
                    tags,
                    1 if (tpl_name == 'nil-deals-tracker' and ti < 2) else 0,
                    1 if (tpl_name == 'espn-bet-promo-deep' and ti < 1) else 0,
                    pub_dt, pub_disp,
                ))
                next_id += 1

    tpl_names_es = sorted(ARTICLE_TEMPLATES_R9_ES.keys())
    for sport_slug, sport_upper, teams_list, season in ES_SPORT_PLANS_R9:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names_es:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R9_ES[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'es-r9-{sport_slug}-{team_slug}-{tpl_name}-00'
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
                day_off = h(f'es-r9-art-pub-{slug}', 180)
                base_pub = date(2026, 4, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Deportes',
                    f'/static/images/espn/articles/{sport_slug}/es-r9-{ti}.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    # Magazine cross-sport batch — themed weekly columns for R9.
    MAGAZINE_TOPICS = [
        ('promo-spotlight-week',
         'ESPN BET promo spotlight: {sport_upper} week {wk} ({season})',
         'A weekly look at how this week\'s ESPN BET promo codes line up '
         'against the {sport_upper} {season} slate. We rank the best-value '
         'boosts, flag the ones that close inside 24 hours, and link to '
         '/espn-bet/promo for the full live registry.',
         ['promo', 'espn-bet', 'magazine', 'r9']),
        ('league-commish-corner',
         'League commissioner corner: {sport_upper} week {wk} ({season})',
         'For fantasy commissioners running {sport_upper} {season} leagues '
         'in week {wk}: lineup-veto patterns, trade-deadline rulings, and '
         'the most-discussed dispute we tracked across public leagues. '
         'Includes links to /fantasy/league/<id>/commissioner walkthroughs.',
         ['fantasy', 'commissioner', 'magazine', 'r9']),
        ('nil-week',
         'NIL week: {sport_upper} {season} disclosures in week {wk}',
         'Tracking five fresh NIL deals announced this {sport_upper} '
         '{season} week {wk}. We size each by booster collective, '
         'percent of position-group cap consumed, and downstream effect '
         'on the 247 board. Full data on /nil/tracker.',
         ['nil', 'magazine', 'r9']),
        ('drm-region-watch',
         'DRM region watch: streaming {sport_upper} {season} in week {wk}',
         'A by-region breakdown of which {sport_upper} {season} broadcasts '
         'in week {wk} are subject to geo-fencing on ESPN+. Includes a '
         'pointer to /watch/live/<event>/drm for per-event detail and a '
         'note on the fallback unlock path.',
         ['watch', 'drm', 'magazine', 'r9']),
        ('multi-step-chain',
         'Multi-step chain of the week: {sport_upper} {season} ({wk})',
         'This week\'s curated agent walkthrough across {sport_upper} '
         '{season} URLs: home → /sport/scoreboard → /game/<id> → '
         '/sport/odds → /fantasy/<sport>. Each step has the assertion an '
         'agent should make before moving to the next.',
         ['multi-step', 'agent', 'magazine', 'r9']),
        ('flip-watch',
         'Recruiting flip watch: {sport_upper} {season} commits in week {wk}',
         'Our weekly flip-risk read on top {sport_upper} {season} '
         'commitments. We rank by OOS visit count, social-media silence, '
         'and on-campus collective spend. Full board on '
         '/recruiting/247-board.',
         ['recruiting', 'flip', 'magazine', 'r9']),
    ]
    SPORTS_FOR_MAGAZINE = [('nba', 'NBA', '2026-27'), ('nba', 'NBA', '2027-28'),
                           ('nfl', 'NFL', '2026'), ('nfl', 'NFL', '2027'),
                           ('mlb', 'MLB', '2026'), ('mlb', 'MLB', '2027'),
                           ('nhl', 'NHL', '2026-27'), ('nhl', 'NHL', '2027-28'),
                           ('soccer', 'Soccer', '2026-27'),
                           ('soccer', 'Soccer', '2027-28'),
                           ('ncaaf', 'CFB', '2026'), ('ncaaf', 'CFB', '2027'),
                           ('ncaam', 'CBB', '2026-27'),
                           ('ncaam', 'CBB', '2027-28')]
    for sport_slug, sport_upper, season in SPORTS_FOR_MAGAZINE:
        for tpl_name, title_fmt, body_fmt, tag_kw in MAGAZINE_TOPICS:
            for wk in range(1, 21):  # week 1..20
                slug = f'r9-mag-{sport_slug}-{season}-{tpl_name}-wk{wk:02d}'
                if slug in existing:
                    continue
                existing.add(slug)
                title = title_fmt.format(sport_upper=sport_upper,
                                         season=season, wk=wk)
                body = body_fmt.format(sport_upper=sport_upper,
                                       season=season, wk=wk)
                tags = json.dumps([sport_upper, season, 'magazine'] + tag_kw)
                day_off = h(f'r9-mag-pub-{slug}', 180)
                base_pub = date(2026, 1, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r9-mag.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, body, "
        "author, image, tags, is_headline, is_featured, created_at, "
        "published_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 3. Betting odds (+1500) ──────────────────────────────────────────────────

BOOKS_R9 = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars',
            'PointsBet', 'BetRivers']


def make_betting(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) "
                              "FROM betting_odds") or 0) + 1
    rows = []
    existing_pairs = set(cur.execute(
        "SELECT game_id, sportsbook FROM betting_odds").fetchall())

    def emit_for_sport(sport, target):
        added = 0
        gids = [r[0] for r in cur.execute(
            "SELECT id FROM games WHERE sport_slug=? "
            "AND status IN ('final','scheduled') "
            "ORDER BY id DESC LIMIT 500", (sport,)).fetchall()]
        if not gids:
            return 0
        bks = BOOKS_R9
        nonlocal next_id
        for i, gid in enumerate(gids):
            if added >= target:
                break
            for b_idx in range(3):
                if added >= target:
                    break
                book = bks[(h(f'r9-bo-{sport}-{gid}-b{b_idx}', len(bks))
                            + b_idx) % len(bks)]
                if (gid, book) in existing_pairs:
                    continue
                existing_pairs.add((gid, book))
                key = f'r9-bo-{sport}-{gid}-{book}'
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
                    'nba': round(hf(f'{key}-t', 210, 245), 1),
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
                opened = ['T-3d', 'T-2d', 'T-1d', 'T-6h',
                          'T-1h'][h(f'{key}-op', 5)]
                rows.append((next_id, gid, sport, home_ml, away_ml,
                             spread_fav, spread_line, total,
                             over_odds, under_odds, opened, status, book))
                next_id += 1
                added += 1
        return added

    n = 0
    n += emit_for_sport('nba', target=360)
    n += emit_for_sport('nfl', target=240)
    n += emit_for_sport('mlb', target=260)
    n += emit_for_sport('nhl', target=240)
    n += emit_for_sport('soccer', target=160)
    n += emit_for_sport('ncaaf', target=110)
    n += emit_for_sport('ncaam', target=130)

    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, home_moneyline, "
        "away_moneyline, spread_favorite, spread_line, total, over_odds, "
        "under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 4. Parlays (+20) ─────────────────────────────────────────────────────────

R9_PARLAYS = [
    ('r9-nba-2027-28-finals', '2027-28 Finals Double', 2, +1700, 18.00,
     'nba', 'ESPN BET',
     ['Celtics East 2027-28', 'Thunder West 2027-28']),
    ('r9-nba-mvp-tier3', 'NBA MVP Tier-3 Trio 27-28', 3, +880, 9.80,
     'nba', 'DraftKings',
     ['Jokic top-3 MVP', 'Doncic top-3 MVP', 'Edwards top-5 MVP']),
    ('r9-nfl-postseason-26', 'NFL 2026 Postseason Quartet', 4, +1800, 19.00,
     'nfl', 'BetMGM',
     ['Chiefs AFC', 'Lions NFC', 'Bills top-2 seed AFC',
      'Eagles top-2 seed NFC']),
    ('r9-mlb-postseason-26', 'MLB 2026 Postseason Trio', 3, +990, 10.90,
     'mlb', 'FanDuel',
     ['Dodgers NL pennant', 'Yankees AL pennant', 'Phillies NLCS']),
    ('r9-nhl-26-27-cup', 'Stanley Cup 26-27 Trio', 3, +1450, 15.50,
     'nhl', 'Caesars',
     ['Oilers West', 'Panthers East', 'McDavid Conn Smythe']),
    ('r9-soccer-26-27-ucl', 'UCL 26-27 Quartet', 4, +2400, 25.00,
     'soccer', 'ESPN BET',
     ['Real Madrid SF', 'Manchester City SF', 'Bayern SF',
      'Inter Milan SF']),
    ('r9-ncaaf-2026-cfp-r9', 'CFP 2026 Bracket Quartet', 4, +1650, 17.50,
     'ncaaf', 'DraftKings',
     ['Alabama semis', 'Ohio St semis', 'Georgia semis',
      'Texas semis']),
    ('r9-ncaam-2027-f4', '2027 Final Four Quartet', 4, +2600, 27.00,
     'ncaam', 'BetMGM',
     ['Duke F4', 'Houston F4', 'Connecticut F4', 'Kansas F4']),
    ('r9-deportes-uefa-trio', 'UEFA Trio (Deportes) 26-27', 3, +500, 6.00,
     'soccer', 'ESPN BET',
     ['Real Madrid UCL SF', 'Barcelona UCL QF',
      'Atletico UCL top-8']),
    ('r9-nba-coy-trio-27-28', 'NBA COY 27-28 Trio', 3, +780, 8.80,
     'nba', 'PointsBet',
     ['Daigneault COY top-3', 'Mazzulla COY top-3',
      'Spo COY top-3']),
    ('r9-nfl-coy-2026', 'NFL COY 2026 Double', 2, +650, 7.50,
     'nfl', 'BetRivers',
     ['Reid COY top-3', 'Campbell COY top-3']),
    ('r9-nba-cross-app', 'Cross-App Sunday R9', 5, +2200, 23.00,
     'fantasy', 'FanDuel',
     ['LeBron 25+', 'Mahomes 275+', 'Judge HR',
      'McDavid 1A1G', 'Mbappe ATG']),
    ('r9-promo-stack-1', 'ESPN BET Promo Stack 1', 3, +480, 5.80,
     'nba', 'ESPN BET',
     ['SIGNUP100 boost', 'NBARESET boost', 'MVP25 boost']),
    ('r9-nfl-week-1-26', 'NFL Week 1 2026 Trio', 3, +540, 6.40, 'nfl',
     'DraftKings',
     ['Chiefs ML', 'Bills ML', 'Eagles ML']),
    ('r9-soccer-uefa-double', 'UEFA Champions League Double 26-27',
     2, +560, 6.60, 'soccer', 'BetMGM',
     ['Real Madrid SF', 'Manchester City SF']),
    ('r9-fantasy-veto-double', 'Fantasy Trade Veto Double 26-27',
     2, +395, 4.95, 'fantasy', 'FanDuel',
     ['League poll majority vote', 'Commissioner override pass']),
    ('r9-nil-disclosure-trio', 'NIL Disclosure Trio 26-27', 3, +780, 8.80,
     'ncaaf', 'ESPN BET',
     ['Alabama disclosed deals top-3', 'Texas disclosed top-5',
      'Georgia collective top-3']),
    ('r9-tennis-26-major', 'Tennis 2026 Major Trio', 3, +1200, 13.00,
     'tennis', 'DraftKings',
     ['Sinner US Open', 'Alcaraz Wimbledon', 'Sabalenka AO']),
    ('r9-golf-26-major', '2026 Golf Major Double', 2, +1450, 15.50,
     'golf', 'BetMGM',
     ['Scheffler Masters', 'Schauffele Open Champ']),
    ('r9-mma-26-card', '2026 MMA Title Card Double', 2, +495, 5.95,
     'mma', 'BetRivers',
     ['Pereira retain LHW', 'Topuria FW future']),
]


def make_parlays(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM parlays") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM parlays").fetchall())
    rows = []
    for slug, title, lc, ao, do, sp, book, legs in R9_PARLAYS:
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


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R9 extension already applied — no-op.')
        conn.close()
        return
    n_gm = make_games(cur)
    n_ar = make_articles(cur)
    n_bo = make_betting(cur)
    n_pl = make_parlays(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R9 inserted: games={n_gm}, articles={n_ar}, '
          f'betting_odds={n_bo}, parlays={n_pl}')


if __name__ == '__main__':
    main()
