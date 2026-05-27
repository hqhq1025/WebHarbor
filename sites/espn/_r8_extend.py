#!/usr/bin/env python3
"""R8 polish extension for sites/espn — direct sqlite3 INSERT only.

Continues gotcha #14 path: HF seed has drifted from seed_data.py, so we
extend the live DB with idempotent direct INSERTs.

R8 on top of R7+R7b baseline (games 7060 / articles 5002 / betting 2600 /
parlays 75 / play_by_play 3728 / tasks 3383):

  * +2500+ games        (7060 → 9500+)  NBA 2026-27 reg-season expansion,
                                        NHL 2026-27, MLB 2026 early-season,
                                        NFL 2026 preseason + early reg,
                                        soccer 25-26 deeper, ncaaw 25-26
                                        coverage + tournament round, ncaaf
                                        2026 spring, NBA mid-week filler.
  * +2000+ articles     (5002 → 7000+)  6 new EN templates × 7 sports + ES
                                        translations + cross-sport magazine
                                        format.
  * +1400+ betting_odds (2600 → 4000+)  cross-book coverage of newer games
                                        across NBA / NFL / MLB / NHL /
                                        soccer / ncaaf / ncaam.
  * +20 parlays
  * Marker row sports.slug '_r8_marker' (id=106) — idempotent.
  * Re-emit indexes alpha-sorted + VACUUM (gotcha #2) for byte-id reset.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r8_marker` row in `sports`.
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
        "SELECT 1 FROM sports WHERE slug='_r8_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (106, 'R8 marker', '_r8_marker', 'r8_extend applied',
         '/_internal/', 106, 0))


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


# ─── Venues (re-use R7 sets, lightly expanded) ────────────────────────────────

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
             postponed_every=0, key_prefix='r8'):
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

    # NBA 2026-27 regular-season expansion (final + scheduled)
    emit('nba', '2026-27-final', teams['nba'], NBA_VENUES,
         date(2026, 10, 20), 360, 35, 95, 8, 'ESPN', 'Final',
         postponed_every=42)
    emit('nba', '2026-27-sched', teams['nba'], NBA_VENUES,
         None, 90, 0, 0, 0, 'ESPN', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2026, 12, 15), 90))
    # NBA mid-week filler 2025-26
    emit('nba', '2025-26-mid-fill', teams['nba'], NBA_VENUES,
         date(2025, 12, 1), 120, 35, 95, 8, 'TNT', 'Final')

    # NHL 2026-27 first half + 25-26 fill
    emit('nhl', '2026-27', teams['nhl'], NHL_VENUES,
         date(2026, 10, 7), 280, 7, 1, 1, 'ESPN+', 'Final',
         postponed_every=38)
    emit('nhl', '2025-26-fill', teams['nhl'], NHL_VENUES,
         date(2025, 12, 5), 70, 7, 1, 1, 'TNT', 'Final')

    # MLB 2026 early-season + 2025 late-season fill
    emit('mlb', '2026', teams['mlb'], MLB_VENUES,
         date(2026, 3, 26), 320, 14, 0, 0, 'MLB Network', 'Final',
         postponed_every=45)
    emit('mlb', '2025-late-fill', teams['mlb'], MLB_VENUES,
         date(2025, 8, 1), 100, 14, 0, 0, 'ESPN', 'Final')

    # NFL 2026 preseason + 2026 reg + 2025 playoffs fill
    emit('nfl', '2026-preseason', teams['nfl'], NFL_VENUES,
         date(2026, 8, 8), 36, 38, 7, 7, 'NFL Network', 'Final')
    emit('nfl', '2026-reg', teams['nfl'], NFL_VENUES,
         date(2026, 9, 10), 160, 38, 7, 7, 'CBS', 'Final')
    emit('nfl', '2025-playoffs-fill', teams['nfl'], NFL_VENUES,
         date(2026, 1, 10), 14, 38, 7, 7, 'FOX', 'Final')

    # Soccer 25-26 deeper coverage + 26-27 preview
    if teams['soccer']:
        emit('soccer', '2025-26-deep', teams['soccer'], SOCCER_VENUES,
             date(2025, 11, 1), 200, 5, 0, 0, 'ESPN+', 'FT')
        emit('soccer', '2026-27-prev', teams['soccer'], SOCCER_VENUES,
             None, 60, 0, 0, 0, 'Peacock', 'Scheduled',
             status_default='scheduled',
             scheduled_window=(date(2026, 8, 15), 120))

    # NCAAF 2026 spring + 2025 bowl fill
    if teams['ncaaf']:
        emit('ncaaf', '2026-spring', teams['ncaaf'], NCAAF_VENUES,
             date(2026, 4, 1), 40, 56, 10, 12, 'ESPN', 'Final')
        emit('ncaaf', '2025-bowls', teams['ncaaf'], NCAAF_VENUES,
             date(2025, 12, 20), 30, 56, 10, 12, 'ABC', 'Final')

    # NCAAM 2026-27 + 2025-26 late
    if teams['ncaam']:
        emit('ncaam', '2026-27', teams['ncaam'], NCAAM_VENUES,
             date(2026, 11, 5), 90, 95, 50, 8, 'CBS', 'Final')
        emit('ncaam', '2025-26-late', teams['ncaam'], NCAAM_VENUES,
             date(2026, 2, 1), 60, 95, 50, 8, 'TBS', 'Final')
        # March Madness 2027 first-round preview
        emit('ncaam', '2027-mm-prev', teams['ncaam'], NCAAM_VENUES,
             None, 32, 0, 0, 0, 'CBS', 'Scheduled',
             status_default='scheduled',
             scheduled_window=(date(2027, 3, 17), 4))

    # NBA 2027-28 schedule preview (next-season tasks)
    emit('nba', '2027-28-prev', teams['nba'], NBA_VENUES,
         None, 60, 0, 0, 0, 'ESPN', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2027, 10, 20), 180))

    # Extra retroactive depth — ensures /scoreboard / team schedule pages
    # have richer history when agents browse far back.
    emit('nba', '2023-24-fill', teams['nba'], NBA_VENUES,
         date(2023, 11, 1), 200, 35, 95, 8, 'ESPN', 'Final',
         postponed_every=50)
    emit('nfl', '2024-fill', teams['nfl'], NFL_VENUES,
         date(2024, 9, 5), 90, 38, 7, 7, 'CBS', 'Final')
    if teams['soccer']:
        emit('soccer', '2024-25-deeper', teams['soccer'], SOCCER_VENUES,
             date(2024, 9, 1), 80, 5, 0, 0, 'ESPN+', 'FT')

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 2. Articles (+2000) ──────────────────────────────────────────────────────

ARTICLE_TEMPLATES_R8 = {
    'gm-perspective': (
        '{team} GM perspective: roster math heading into {season}',
        'A close read of how the {team} front office is navigating roster '
        'math in {sport_upper} {season}. We cover their core contracts, '
        'available exceptions, trade-deadline posture, and the silent '
        'preference for picks over depth that has shaped recent moves. '
        'Sources inside the building describe a patient, asset-protective '
        'philosophy with one tradeable wing at the deadline.',
        ['gm', 'front-office', 'analysis']),
    'coach-clipboard': (
        '{team} clipboard study: what the coach is drawing up in {season}',
        "A whiteboard-level breakdown of what the {team} coaching staff is "
        "running in {sport_upper} {season}. Three sets surface against zone, "
        "two ATO calls have an 80% efficiency clip, and the late-game "
        "spread look has quietly become a league-leading tool. We diagram "
        "the actions and the personnel groupings.",
        ['coaching', 'film-room', 'analysis']),
    'health-report-monthly': (
        '{team} monthly health report: injury and minutes outlook for {season}',
        'Our {sport_upper} {season} monthly health report on the {team}: '
        'who is on a minutes restriction, who is post-rehab, and which '
        'players are graded as available pending pre-game shootaround. The '
        'staff is conservative on back-to-backs and aggressive about load '
        'days off the road.',
        ['injuries', 'health', 'minutes', 'report']),
    'travel-and-schedule': (
        '{team} travel and schedule notes: {season} road grind',
        'A look at the {team} {sport_upper} {season} road slate: the '
        'longest trip, the worst rest-day deficit, two stretches where '
        'they fly three time zones in a week. Plus a quick note on hotel '
        'choices and the role of the travel coordinator in their recent '
        'road wins.',
        ['travel', 'schedule', 'logistics']),
    'fan-voices': (
        'Fan voices: {team} {season} sentiment from the bleachers',
        'We polled and quoted a curated group of {team} fans on their '
        '{sport_upper} {season} reactions. Themes: cautious optimism on '
        'the rookie class, frustration with the bench rotation, broad '
        'patience with the GM. Includes a sidebar on the most viral fan '
        'video this month.',
        ['fans', 'community', 'voices']),
    'season-snapshot': (
        '{team} season snapshot: 30-second {season} read',
        'A compact, 30-second snapshot of where the {team} stand in '
        '{sport_upper} {season}: net rating, schedule-adjusted record, '
        'top three lineups, biggest weakness, and one number that should '
        'scare opponents. Shareable, sourced, and ready to forward.',
        ['snapshot', 'quick-read', 'summary']),
    'lineup-lab': (
        '{team} lineup lab: best 5-man combos in {season}',
        'The {team} lineup laboratory for {sport_upper} {season}: top '
        '5-man combinations by net rating, the unit that survives crunch, '
        'and the small-sample group that should get more minutes. We '
        'include the supporting numbers and the coaching staff response.',
        ['lineups', 'lab', 'analytics']),
    'tape-study': (
        '{team} tape study: three plays defining {season}',
        'A three-play breakdown that defines how the {team} look in '
        '{sport_upper} {season}: the early-clock action, the broken-play '
        'identity, and the late-game closer. Each clip ties back to a '
        'core principle the staff has emphasized.',
        ['tape-study', 'film', 'analysis']),
    'developer-corner-r8': (
        '{team} developer corner: building a fantasy app integration ({season})',
        "For developers and fantasy app builders covering the {team} in "
        "{sport_upper} {season}: API surface examples, recommended "
        "polling cadences, and the new /api/v3-graphql query patterns "
        "ESPN exposes for roster and box-score data. Includes a sample "
        "telemetry payload and webhook contract.",
        ['developer', 'api', 'fantasy-app', 'r8']),
    'broadcast-booth': (
        '{team} broadcast booth notes: how analysts are framing {season}',
        'How the national broadcast booth is framing the {team} in '
        '{sport_upper} {season}: the recurring talking points, the '
        'unforced narrative each crew leans on, and the under-discussed '
        'angle most booths miss. Includes side-by-side excerpts from '
        'three different broadcast crews.',
        ['broadcast', 'media', 'narrative']),
    'fantasy-app-spotlight-r8': (
        '{team} fantasy-app spotlight: roster choices to make in {season}',
        'A fantasy-app spotlight on the {team} for {sport_upper} '
        '{season}: who to start in standard scoring, who to stash in '
        'deep leagues, and the one waiver pick the consensus is missing. '
        'We close with a quick guide to how the ESPN fantasy app surfaces '
        "these picks via the /developer/fantasy-app endpoint.",
        ['fantasy', 'app', 'r8']),
    'history-corner': (
        '{team} history corner: archive notes for {season}',
        'A history-desk note on the {team} as they move through '
        '{sport_upper} {season}. Includes a quick parallel to past '
        'rosters, the franchise record their pace would tie, and the '
        'archival photo we recommend revisiting.',
        ['history', 'archive', 'long-read']),
}


ARTICLE_TEMPLATES_R8_ES = {
    'perspectiva-gm': (
        'Perspectiva del GM de los {team}: cuentas del plantel para {season}',
        'Una lectura cercana de cómo la oficina principal de los {team} '
        'maneja las cuentas del plantel en {sport_upper} {season}. '
        'Repasamos contratos núcleo, excepciones disponibles, postura '
        'para la fecha límite de canjes y la preferencia silenciosa por '
        'selecciones del draft sobre profundidad que ha guiado sus '
        'movimientos recientes. Las fuentes adentro del edificio '
        'describen una filosofía paciente y protectora de activos.',
        ['gm', 'oficina-principal', 'analisis', 'es', 'deportes']),
    'pizarra-tecnico': (
        'La pizarra de los {team}: lo que dibuja el técnico en {season}',
        'Un desglose al nivel de pizarra de lo que el cuerpo técnico de '
        'los {team} ejecuta en {sport_upper} {season}. Tres jugadas '
        'aparecen ante la zona, dos ATO tienen un 80% de eficiencia, y '
        'el set de cierre se ha convertido silenciosamente en una de las '
        'mejores herramientas de la liga.',
        ['tecnico', 'pizarra', 'analisis', 'es', 'deportes']),
    'snapshot-temporada': (
        'Foto rápida de los {team} en {season}: lectura de 30 segundos',
        'Una foto compacta de 30 segundos de dónde están los {team} en '
        '{sport_upper} {season}: net rating, récord ajustado por '
        'calendario, las tres mejores quintetas, la mayor debilidad y '
        'un número que debería asustar a sus rivales. Compartible, con '
        'fuentes y lista para reenviar.',
        ['snapshot', 'lectura-rapida', 'resumen', 'es', 'deportes']),
    'voces-aficion': (
        'Voces de la afición: sentimiento sobre los {team} en {season}',
        'Encuestamos y citamos a un grupo seleccionado de aficionados de '
        'los {team} sobre sus reacciones a {sport_upper} {season}. Los '
        'temas: optimismo cauteloso por la camada de novatos, '
        'frustración con la rotación del banco, y paciencia general con '
        'el gerente general. Incluye un comentario al margen sobre el '
        'video viral del mes.',
        ['aficion', 'comunidad', 'voces', 'es', 'deportes']),
    'salud-mensual': (
        'Reporte de salud mensual de los {team}: lesiones y minutos en {season}',
        'Nuestro reporte mensual de salud de los {team} para {sport_upper} '
        '{season}: quién está con restricción de minutos, quién está en '
        'rehabilitación, y qué jugadores son evaluados como disponibles '
        'a falta del entrenamiento previo. El cuerpo técnico es '
        'conservador con los back-to-back y agresivo con los días de '
        'descanso en viaje.',
        ['lesiones', 'salud', 'minutos', 'reporte', 'es', 'deportes']),
    'rincon-desarrollador': (
        'Rincón del desarrollador: integración con la app de fantasy de los {team}',
        'Para desarrolladores que cubren a los {team} en {sport_upper} '
        '{season}: ejemplos de la superficie de API, frecuencias '
        'recomendadas de polling, y los nuevos patrones de consulta '
        '/api/v3-graphql que ESPN expone para datos de planteles y '
        'estadísticas. Incluye un ejemplo de payload de telemetría.',
        ['desarrollador', 'api', 'fantasy-app', 'es', 'deportes']),
}


SPORT_PLANS_R8 = [
    ('nba', 'NBA',
     'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
     'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
     'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
     'Oklahoma City Thunder,Cleveland Cavaliers,Indiana Pacers,'
     'Minnesota Timberwolves,New Orleans Pelicans,Sacramento Kings,'
     'Memphis Grizzlies,Atlanta Hawks,Brooklyn Nets,Chicago Bulls,'
     'Houston Rockets,LA Clippers,Orlando Magic'.split(','),
     '2026-27'),
    ('nfl', 'NFL',
     'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
     'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
     'Detroit Lions,Miami Dolphins,Green Bay Packers,'
     'Cincinnati Bengals,Pittsburgh Steelers,Houston Texans,'
     'New York Giants,Los Angeles Rams,Tampa Bay Buccaneers,'
     'Atlanta Falcons,Seattle Seahawks,Minnesota Vikings'.split(','),
     '2026'),
    ('mlb', 'MLB',
     'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
     'Atlanta Braves,Houston Astros,Texas Rangers,'
     'Philadelphia Phillies,Chicago Cubs,San Diego Padres,'
     'Toronto Blue Jays,New York Mets,Seattle Mariners,'
     'Baltimore Orioles,Cleveland Guardians'.split(','),
     '2026'),
    ('nhl', 'NHL',
     'Boston Bruins,Edmonton Oilers,Vegas Golden Knights,'
     'New York Rangers,Toronto Maple Leafs,Florida Panthers,'
     'Colorado Avalanche,Tampa Bay Lightning,Carolina Hurricanes,'
     'Dallas Stars'.split(','),
     '2026-27'),
    ('soccer', 'Soccer',
     'Arsenal,Manchester City,Liverpool,'
     'Real Madrid,Barcelona,Bayern Munich,'
     'Paris Saint-Germain,Inter Milan,Manchester United,'
     'Chelsea,Atletico Madrid'.split(','),
     '2025-26'),
    ('ncaaf', 'CFB',
     'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
     'USC,Notre Dame,Oregon,Penn State'.split(','),
     '2026'),
    ('ncaam', 'CBB',
     'Duke,Kansas,Kentucky,Connecticut,North Carolina,'
     'Houston,Purdue,Arizona,UCLA'.split(','),
     '2026-27'),
]

ES_SPORT_PLANS_R8 = [
    ('nba', 'NBA',
     'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
     'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
     'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
     'Oklahoma City Thunder,Cleveland Cavaliers'.split(','),
     '2026-27'),
    ('nfl', 'NFL',
     'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
     'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
     'Detroit Lions,Miami Dolphins'.split(','),
     '2026'),
    ('mlb', 'MLB',
     'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
     'Atlanta Braves,Houston Astros,Texas Rangers'.split(','),
     '2026'),
    ('soccer', 'Soccer',
     'Real Madrid,Barcelona,Bayern Munich,'
     'Paris Saint-Germain,Inter Milan,'
     'Manchester City,Arsenal,Liverpool,'
     'Manchester United,Atletico Madrid'.split(','),
     '2025-26'),
]


def make_articles(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM articles").fetchall())

    rows = []
    tpl_names = sorted(ARTICLE_TEMPLATES_R8.keys())
    for sport_slug, sport_upper, teams_list, season in SPORT_PLANS_R8:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R8[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'r8-{sport_slug}-{team_slug}-{tpl_name}-00'
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
                day_off = h(f'r8-art-pub-{slug}', 180)
                base_pub = date(2026, 1, 5) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r8-{ti}.jpg',
                    tags,
                    1 if (tpl_name == 'season-snapshot' and ti < 2) else 0,
                    1 if (tpl_name == 'coach-clipboard' and ti < 1) else 0,
                    pub_dt, pub_disp,
                ))
                next_id += 1

    tpl_names_es = sorted(ARTICLE_TEMPLATES_R8_ES.keys())
    for sport_slug, sport_upper, teams_list, season in ES_SPORT_PLANS_R8:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names_es:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R8_ES[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'es-r8-{sport_slug}-{team_slug}-{tpl_name}-00'
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
                day_off = h(f'es-r8-art-pub-{slug}', 180)
                base_pub = date(2026, 2, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Deportes',
                    f'/static/images/espn/articles/{sport_slug}/es-r8-{ti}.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    # Magazine cross-sport batch — themed weekly columns, not per-team. This
    # pushes article count well past the 7000 target while leaving plenty of
    # named-team slugs above.
    MAGAZINE_TOPICS = [
        ('weekly-power-rankings',
         'Weekly power rankings: {sport_upper} week {wk}, {season}',
         'Our {sport_upper} {season} power rankings entering week {wk}. We '
         'walk team-by-team, citing schedule strength, recent form, and the '
         'underlying signals from our {sport_upper} efficiency models. '
         'Every move is sourced to a film note or a numbers-driven shift.',
         ['power-rankings', 'weekly', 'magazine']),
        ('week-in-quotes',
         'Week in quotes: the best {sport_upper} soundbites of week {wk} ({season})',
         'A roundup of the most telling {sport_upper} {season} quotes from '
         "week {wk}: locker-room candor, coach-speak deconstructed, and the "
         'front-office leak that moved the needle. Each quote is paired '
         'with the context that gives it weight.',
         ['quotes', 'magazine', 'media']),
        ('numbers-of-the-week',
         'Numbers of the week: {sport_upper} stat dump for week {wk} ({season})',
         'Five {sport_upper} {season} numbers from week {wk}: the silly '
         'one, the meaningful one, the historic one, the predictive one, '
         'and the one that ought to embarrass a front office. Sources and '
         'calculations included in the footer.',
         ['numbers', 'analytics', 'magazine']),
        ('what-we-learned',
         'What we learned: {sport_upper} reflections from week {wk} ({season})',
         'A wide-angle take on what week {wk} of {sport_upper} {season} '
         'taught us. We cover the surprise contender, the disappointment, '
         'the rising rookie, and the looming trade conversation. Designed '
         'to be read in 5 minutes.',
         ['reflection', 'magazine', 'weekly']),
        ('looking-ahead',
         'Looking ahead: the {sport_upper} games to watch in week {wk} ({season})',
         'Three games to circle in next week of {sport_upper} {season}, '
         'plus one prospect to track and a wild-card storyline. Each entry '
         'comes with a recommended viewing time, broadcast, and the angle '
         'most likely to deliver.',
         ['preview', 'magazine', 'viewing-guide']),
    ]
    SPORTS_FOR_MAGAZINE = [('nba', 'NBA', '2025-26'), ('nba', 'NBA', '2026-27'),
                           ('nfl', 'NFL', '2025'), ('nfl', 'NFL', '2026'),
                           ('mlb', 'MLB', '2025'), ('mlb', 'MLB', '2026'),
                           ('nhl', 'NHL', '2025-26'), ('nhl', 'NHL', '2026-27'),
                           ('soccer', 'Soccer', '2025-26'),
                           ('ncaaf', 'CFB', '2025'), ('ncaaf', 'CFB', '2026'),
                           ('ncaam', 'CBB', '2025-26'),
                           ('ncaam', 'CBB', '2026-27')]
    for sport_slug, sport_upper, season in SPORTS_FOR_MAGAZINE:
        for tpl_name, title_fmt, body_fmt, tag_kw in MAGAZINE_TOPICS:
            for wk in range(1, 15):  # week 1..14
                slug = f'r8-mag-{sport_slug}-{season}-{tpl_name}-wk{wk:02d}'
                if slug in existing:
                    continue
                existing.add(slug)
                title = title_fmt.format(sport_upper=sport_upper,
                                         season=season, wk=wk)
                body = body_fmt.format(sport_upper=sport_upper,
                                       season=season, wk=wk)
                tags = json.dumps([sport_upper, season, 'magazine'] + tag_kw)
                day_off = h(f'r8-mag-pub-{slug}', 180)
                base_pub = date(2026, 1, 10) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Magazine',
                    f'/static/images/espn/articles/{sport_slug}/r8-mag-{wk}.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, "
        "body, author, image, tags, is_headline, is_featured, "
        "created_at, published_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 3. Betting odds (+1400) ──────────────────────────────────────────────────

SPORTSBOOKS = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars',
               'PointsBet', 'BetRivers']


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
            "ORDER BY id DESC LIMIT 3500", (sport,)).fetchall()
        added = 0
        nonlocal next_id
        bks = books or SPORTSBOOKS
        for gid, in gs:
            if added >= target:
                break
            for b_idx in range(len(bks)):
                if added >= target:
                    break
                book = bks[(h(f'r8-bo-{sport}-{gid}-{b_idx}', len(bks))
                            + b_idx) % len(bks)]
                if (gid, book) in existing_pairs:
                    continue
                existing_pairs.add((gid, book))
                key = f'r8-bo-{sport}-{gid}-{book}'
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
    n += emit_for_sport('nba', target=350)
    n += emit_for_sport('nfl', target=240)
    n += emit_for_sport('mlb', target=260)
    n += emit_for_sport('nhl', target=240)
    n += emit_for_sport('soccer', target=140)
    n += emit_for_sport('ncaaf', target=90)
    n += emit_for_sport('ncaam', target=90)

    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, home_moneyline, "
        "away_moneyline, spread_favorite, spread_line, total, over_odds, "
        "under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 4. Parlays (+20) ─────────────────────────────────────────────────────────

R8_PARLAYS = [
    ('r8-nba-mvp-tier1', 'NBA MVP Tier-1 Double', 2, +395, 4.95, 'nba',
     'ESPN BET', ['Jokic MVP top-2', 'Doncic MVP top-3']),
    ('r8-nba-rookie-tier1', 'NBA Rookie Tier-1', 3, +880, 9.80, 'nba',
     'DraftKings', ['Castle ROY top-3', 'Sheppard ROY top-5',
                    'Edey All-Rookie']),
    ('r8-nfl-mvp-treble', 'NFL MVP Treble 26', 3, +540, 6.40, 'nfl',
     'BetMGM', ['Mahomes MVP top-3', 'Burrow MVP top-5',
                'Lamar MVP top-5']),
    ('r8-mlb-cy-young-double-2026', 'MLB Cy Young Double 26', 2, +560,
     6.60, 'mlb', 'FanDuel',
     ['Skenes NL Cy', 'Crochet AL Cy top-3']),
    ('r8-nhl-art-ross-future', 'Art Ross Future Trio', 3, +1100, 12.00,
     'nhl', 'Caesars',
     ['McDavid Art Ross', 'Draisaitl top-3', 'MacKinnon top-3']),
    ('r8-soccer-ucl-semis-quartet', 'UCL Semis Quartet 26',
     4, +1900, 20.00, 'soccer', 'ESPN BET',
     ['Real Madrid SF', 'Arsenal SF', 'Bayern SF', 'PSG SF']),
    ('r8-ncaaf-cfp-2026-quartet', 'CFP 2026 Quartet', 4, +1450, 15.50,
     'ncaaf', 'DraftKings',
     ['Georgia semis', 'Ohio St semis', 'Texas semis', 'Oregon semis']),
    ('r8-ncaam-2026-final-four', '2026 Final Four Quartet', 4, +2200,
     23.00, 'ncaam', 'BetMGM',
     ['Duke F4', 'UConn F4', 'Houston F4', 'Kansas F4']),
    ('r8-nba-finals-2026-2027', '2026/27 Finals Double', 2, +1600,
     17.00, 'nba', 'FanDuel',
     ['Celtics East', 'Thunder West']),
    ('r8-deportes-laliga-trio', 'La Liga Trio (Deportes)', 3, +450,
     5.50, 'soccer', 'ESPN BET',
     ['Real Madrid LaLiga', 'Atletico top-3', 'Barcelona top-3']),
    ('r8-mlb-postseason-quartet', 'MLB Postseason Quartet', 4, +1450,
     15.50, 'mlb', 'Caesars',
     ['Dodgers NL pennant', 'Yankees AL pennant', 'Phillies NLDS',
      'Astros ALDS']),
    ('r8-nfl-super-bowl-coach', 'Super Bowl Coach Double', 2, +650,
     7.50, 'nfl', 'ESPN BET',
     ['Reid COY top-3', 'Campbell COY top-3']),
    ('r8-nhl-stanley-cup-trio', 'Stanley Cup Future Trio', 3, +1300,
     14.00, 'nhl', 'BetMGM',
     ['Panthers East', 'Oilers West', 'McDavid Conn Smythe']),
    ('r8-nba-overs-three-team', 'Threes Overs Trio 26', 3, +480,
     5.80, 'nba', 'DraftKings',
     ['Curry o4.5 3PM', 'Tatum o3.5 3PM', 'Brunson o2.5 3PM']),
    ('r8-cross-sport-sunday', 'Cross-Sport Sunday R8', 5, +2100,
     22.00, 'fantasy', 'FanDuel',
     ['LeBron 25+', 'McDavid 1A1G', 'Mahomes 275+', 'Judge HR',
      'Mbappe ATG']),
    ('r8-nba-coy-trio', 'NBA COY Trio 26', 3, +780, 8.80, 'nba',
     'PointsBet', ['Daigneault COY top-3', 'Mazzulla COY top-3',
                   'Snyder COY top-3']),
    ('r8-mma-title-double', 'MMA Title Double', 2, +495, 5.95, 'mma',
     'BetRivers', ['Pereira to retain LHW', 'Topuria FW future']),
    ('r8-tennis-major-treble', 'Tennis Major Treble', 3, +1200, 13.00,
     'tennis', 'DraftKings',
     ['Sinner US Open', 'Alcaraz Wimbledon', 'Sabalenka AO']),
    ('r8-golf-major-double', 'Golf Major Double', 2, +1450, 15.50,
     'golf', 'BetMGM',
     ['Scheffler Masters', 'Schauffele Open Champ']),
    ('r8-fantasy-three-app', 'Fantasy App Triple', 3, +625, 7.25,
     'fantasy', 'FanDuel',
     ['Bijan 100+ rush', 'McCaffrey 90+ rush', 'Henry TD anytime']),
]


def make_parlays(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM parlays") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM parlays").fetchall())
    rows = []
    for slug, title, lc, ao, do, sp, book, legs in R8_PARLAYS:
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
        print('R8 extension already applied — no-op.')
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
    print(f'R8 inserted: games={n_gm}, articles={n_ar}, '
          f'betting_odds={n_bo}, parlays={n_pl}')


if __name__ == '__main__':
    main()
