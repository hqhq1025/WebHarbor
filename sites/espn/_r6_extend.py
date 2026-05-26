#!/usr/bin/env python3
"""R6 polish extension for sites/espn — direct sqlite3 INSERT only.

Continues gotcha #14 path: HF seed has drifted from seed_data.py, so we
extend the live DB with idempotent direct INSERTs.

R6 on top of R5 baseline:
  * +1700 games        (3511 → 5200+) NBA 24-25 full, NHL 24-25 full,
                                       MLB 2024 full, NFL 2024 full,
                                       soccer 23-24 + 24-25, ncaaf 2024,
                                       ncaam 2024-25
  * +1300 articles     (2238 → 3500+)  team × topic templated coverage
  * +700 betting_odds  (540 → 1240+)   NFL was only 1; fill NFL/MLB/NHL
  * +30 podcasts       (164 → 200+)
  * +30 parlays        (30 → 60+)
  * +600 play_by_play  (2990 → 3600+)  more marquee games covered
  * Marker row sports.slug '_r6_marker' (id=103) — idempotent.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r6_marker` row in `sports`.
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
        "SELECT 1 FROM sports WHERE slug='_r6_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (103, 'R6 marker', '_r6_marker', 'r6_extend applied',
         '/_internal/', 103, 0))


def normalize(cur):
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── Venues (extended from R5) ────────────────────────────────────────────────

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


# ─── 1. Games (+1700) ────────────────────────────────────────────────────────

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
             postponed_every=0):
        """postponed_every>0 → mark every Nth game status='postponed'."""
        nonlocal next_id
        if not t_arr:
            return 0
        n = 0
        for i in range(count):
            a = h(f'r6-{sport}-{season_label}-a-{i}', len(t_arr))
            b = h(f'r6-{sport}-{season_label}-b-{i}', len(t_arr))
            if a == b:
                b = (b + 1) % len(t_arr)
            home = t_arr[a]
            away = t_arr[b]
            if scheduled_window:
                gdate = scheduled_window[0] + timedelta(
                    days=h(f'r6-{sport}-{season_label}-d-{i}',
                          scheduled_window[1]))
                status = 'scheduled'
                period = 'Scheduled'
                hs, as_ = 0, 0
                recap = f'{season_label} {away[1]} at {home[1]}.'
            else:
                gdate = start + timedelta(
                    days=h(f'r6-{sport}-{season_label}-d-{i}', 175))
                status = status_default
                period = period_label
                hs = h(f'r6-{sport}-{season_label}-hs-{i}', hi_score, lo_score)
                as_ = h(f'r6-{sport}-{season_label}-as-{i}', hi_score,
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

    # NBA 2024-25 full + 2025-26 preview
    emit('nba', '2024-25', teams['nba'], NBA_VENUES,
         date(2024, 10, 22), 380, 35, 95, 8, 'ESPN', 'Final',
         postponed_every=40)
    emit('nba', '2025-26-prev', teams['nba'], NBA_VENUES,
         None, 60, 0, 0, 0, 'ESPN', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2025, 10, 21), 180))

    # NHL 2024-25 full + 2025-26 preview
    emit('nhl', '2024-25', teams['nhl'], NHL_VENUES,
         date(2024, 10, 8), 300, 7, 1, 1, 'ESPN+', 'Final',
         postponed_every=35)
    emit('nhl', '2025-26-prev', teams['nhl'], NHL_VENUES,
         None, 50, 0, 0, 0, 'ESPN+', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2025, 10, 7), 190))

    # MLB 2024 full + 2025 early
    emit('mlb', '2024', teams['mlb'], MLB_VENUES,
         date(2024, 3, 28), 240, 14, 0, 0, 'MLB Network', 'Final',
         postponed_every=45)
    emit('mlb', '2025-early', teams['mlb'], MLB_VENUES,
         date(2025, 3, 27), 60, 12, 0, 0, 'MLB Network', 'Final')

    # NFL 2024 full + 2025 preview
    emit('nfl', '2024', teams['nfl'], NFL_VENUES,
         date(2024, 9, 5), 180, 38, 7, 7, 'CBS', 'Final')
    emit('nfl', '2025-prev', teams['nfl'], NFL_VENUES,
         None, 40, 0, 0, 0, 'NBC', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2025, 9, 4), 130))

    # Soccer 2024-25 league + UCL knockout
    if teams['soccer']:
        emit('soccer', '2024-25', teams['soccer'], SOCCER_VENUES,
             date(2024, 8, 16), 90, 5, 0, 0, 'ESPN+', 'FT')
        emit('soccer', '2024-25-ucl', teams['soccer'], SOCCER_VENUES,
             date(2024, 9, 17), 50, 5, 0, 0, 'Paramount+', 'FT')

    # NCAAF 2024
    if teams['ncaaf']:
        emit('ncaaf', '2024', teams['ncaaf'], NCAAF_VENUES,
             date(2024, 8, 31), 50, 56, 10, 12, 'ABC', 'Final')

    # NCAAM 2024-25
    if teams['ncaam']:
        emit('ncaam', '2024-25', teams['ncaam'], NCAAM_VENUES,
             date(2024, 11, 4), 50, 95, 50, 8, 'CBS', 'Final')

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 2. Articles (+1300) ─────────────────────────────────────────────────────

ARTICLE_TEMPLATES = {
    # (slug_suffix, title_fmt, body_fmt, tag_keywords)
    'inside-locker-room': (
        'Inside the {team} locker room: rotation tweaks coming',
        'Sources tell ESPN the {team} are weighing a fresh look at the '
        'closing lineup. Coaches have been studying recent {sport_upper} '
        'film and the staff favors a smaller, more switchable group in '
        'crunch time. The {team} have been competitive but inconsistent '
        'across {season} and want answers before the postseason picture '
        'sharpens.',
        ['lockerroom', 'rotation']),
    'trade-deadline-buzz': (
        '{team} trade-deadline buzz: front office working the phones',
        'Around the league, executives expect the {team} to be active '
        'as the {season} {sport_upper} deadline approaches. ESPN sources '
        'say the front office has had preliminary conversations on a '
        'rotation upgrade and a contract-matching salary piece. Nothing '
        'is imminent, but a deal in the next ten days is in play.',
        ['trade', 'deadline', 'rumors']),
    'power-rankings-week': (
        'Power Rankings: {team} climb after recent {sport_upper} run',
        'In this week\'s ESPN Power Rankings, the {team} jump on the '
        'strength of their last five {sport_upper} {season} games. The '
        'panel weighs net rating, schedule difficulty, and injury status. '
        'The full top-30 board is updated weekly throughout the season.',
        ['rankings', 'analysis']),
    'injury-status-update': (
        'Injury report: {team} star questionable, decision before tip',
        'The {team} listed their leading scorer as questionable for '
        'tonight\'s {sport_upper} {season} game with a lingering '
        'ankle issue. The team trainer described the player as a game-time '
        'decision and indicated a return-to-play protocol is in motion. '
        'Backups have been preparing for an expanded role.',
        ['injury', 'status']),
    'coach-roundtable': (
        'Coaches roundtable: what makes the {team} dangerous in {season}',
        'ESPN\'s coaches roundtable digs into the {team}\'s scheme and '
        'tactical wrinkles that have made them a tough out this {season} '
        '{sport_upper} season. Spacing, defensive switching, and bench '
        'depth are highlighted, with opposing coaches calling them one '
        'of the harder game-plan opponents in the league.',
        ['coaching', 'tactics']),
    'fpi-deep-dive': (
        'FPI deep dive: how the {team} model in {season}',
        'ESPN\'s Football Power Index sees the {team} as a fringe top-ten '
        'team this {season} season, with strength of schedule swinging '
        'projections by several percentage points. The simulations weigh '
        'recent {sport_upper} performance against returning production '
        'and injury context.',
        ['fpi', 'analytics']),
    'fantasy-rest-of-season': (
        'Fantasy {sport_upper} rest-of-season: {team} player you must hold',
        'Fantasy managers in deeper leagues should hang on to the {team} '
        'rotation piece who has quietly emerged in {season}. Usage trends '
        'point to a sustained role even after starters return, making him '
        'a quality value at his current ESPN Fantasy ADP.',
        ['fantasy', 'ros']),
    'betting-line-watch': (
        'Line Watch: where the smart money is on the {team} this {season}',
        'On the ESPN BET board, the {team} have seen sharp action on the '
        'team total this {season} {sport_upper} stretch. Closing lines '
        'have moved against the public over the last five games. Where to '
        'find the highest-EV side is the question for the betting desk.',
        ['betting', 'bet', 'line-movement']),
    'draft-pipeline-outlook': (
        'Draft pipeline: what the {team} need ahead of {season}',
        'The {team} front office is doing draft homework on positional '
        'fits that complement the current core. Scouts have crossed off '
        'two early-round prospects on rotation tape, and one {sport_upper} '
        'workout invitee has buzzed up draft boards this winter.',
        ['draft', 'scouting']),
    'home-run-derby': (
        '{team} home stand preview: three games, three tests',
        'The {team} return home for a {season} {sport_upper} home stand '
        'against three contenders, a chance to swing seeding before the '
        'next road trip. Pitching matchups and rotation order are reviewed '
        'in this preview, including the closer\'s availability.',
        ['preview', 'homestand']),
    'recruit-commit-recap': (
        'Commit recap: where the {team} class stands for {season}',
        'The {team} added another piece to their {season} {sport_upper} '
        'recruiting class this week. ESPN\'s 247Composite-style board '
        'lists the new commit as a top-150 prospect; the staff likes the '
        'character and lateral quickness on tape.',
        ['recruiting', 'commit']),
    'roster-positional-look': (
        'Roster look: who plays the wing for the {team} in {season}',
        'After a busy offseason, the {team} have several candidates for '
        'the wing rotation in {season} {sport_upper}. ESPN beat writers '
        'walk through the options, including a sophomore who may push for '
        'starter minutes.',
        ['roster', 'depth']),
    'breakdown-tape': (
        'Tape breakdown: what {team} film tells us in {season}',
        'ESPN\'s tape room sat with film of the {team}\'s last three '
        '{season} {sport_upper} games. Off-ball movement, defensive '
        'rotations, and special-teams (or special-units) wrinkles each '
        'get a frame-by-frame look. The biggest takeaway: opponents are '
        'forcing the ball away from the primary creator.',
        ['film', 'tape']),
    'historical-context': (
        'Historical context: putting {team} in {season} into perspective',
        'A look back at the {team} historical record and where {season} '
        'fits in. The franchise has reached the conference round in three '
        'of the last six {sport_upper} seasons and now sits with the best '
        'point-differential since the previous core era.',
        ['history', 'all-time']),
    'fan-experience': (
        'Fan experience: the {team} home-game atmosphere in {season}',
        'ESPN reporters visited a {team} {sport_upper} home game during '
        '{season} for a notebook on the matchday experience. Crowd noise, '
        'the in-arena DJ, and the team\'s tribute-night nights all factor '
        'into the league\'s top-tier home environments this year.',
        ['gameday', 'fans']),
}

SPORT_PLANS = [
    ('nba', 'NBA', 'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
                   'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
                   'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
                   'Minnesota Timberwolves,Oklahoma City Thunder,'
                   'Cleveland Cavaliers,Indiana Pacers,New Orleans Pelicans,'
                   'Sacramento Kings,Memphis Grizzlies,Atlanta Hawks,'
                   'Orlando Magic,Houston Rockets'.split(','),
     '2024-25'),
    ('nfl', 'NFL', 'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
                   'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
                   'Detroit Lions,Miami Dolphins,Green Bay Packers,'
                   'Cincinnati Bengals,Pittsburgh Steelers,Houston Texans,'
                   'Minnesota Vikings,Los Angeles Rams,New York Jets,'
                   'Jacksonville Jaguars,Cleveland Browns,Atlanta Falcons'.split(','),
     '2024'),
    ('mlb', 'MLB', 'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
                   'Atlanta Braves,Houston Astros,Texas Rangers,'
                   'Philadelphia Phillies,Chicago Cubs,San Diego Padres,'
                   'Toronto Blue Jays,Baltimore Orioles,Seattle Mariners,'
                   'New York Mets,Milwaukee Brewers'.split(','),
     '2024'),
    ('nhl', 'NHL', 'Boston Bruins,Edmonton Oilers,Vegas Golden Knights,'
                   'New York Rangers,Toronto Maple Leafs,Florida Panthers,'
                   'Colorado Avalanche,Tampa Bay Lightning,Dallas Stars,'
                   'Carolina Hurricanes'.split(','),
     '2024-25'),
    ('soccer', 'Soccer', 'Arsenal,Manchester City,Liverpool,'
                        'Real Madrid,Barcelona,Bayern Munich,'
                        'Paris Saint-Germain,Inter Milan,'
                        'Borussia Dortmund,Manchester United'.split(','),
     '2024-25'),
    ('ncaaf', 'CFB', 'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
                     'USC,Notre Dame,Oklahoma,Penn State'.split(','),
     '2024'),
    ('ncaam', 'CBB', 'Duke,Kansas,Kentucky,Connecticut,North Carolina,'
                     'Houston,Purdue,Tennessee,Arizona,Marquette'.split(','),
     '2024-25'),
]


def make_articles(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1

    # Read existing slugs once to never collide.
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM articles").fetchall())

    rows = []
    tpl_names = sorted(ARTICLE_TEMPLATES.keys())
    for sport_slug, sport_upper, teams_list, season in SPORT_PLANS:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = (f'r6-{sport_slug}-{team_slug}-{tpl_name}-'
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
                # spread published_date deterministically across season
                day_off = h(f'r6-art-pub-{slug}', 180)
                base_pub = date(2024, 9, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '',
                    body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r6-{ti}.jpg',
                    tags,
                    1 if (ti == 0 and tpl_name == 'inside-locker-room') else 0,
                    1 if tpl_name in ('power-rankings-week',
                                      'fpi-deep-dive') and ti < 3 else 0,
                    pub_dt, pub_disp,
                ))
                next_id += 1
    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, "
        "body, author, image, tags, is_headline, is_featured, "
        "created_at, published_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 3. Betting odds (+700) ──────────────────────────────────────────────────

SPORTSBOOKS = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars']


def make_betting(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM betting_odds") or 0) + 1

    existing_pairs = set(
        (r[0], r[1]) for r in cur.execute(
            "SELECT game_id, sportsbook FROM betting_odds").fetchall())

    rows = []

    def emit_for_sport(sport, limit_books=None, target=200):
        """Walk newest games of <sport>, attach odds rows until target."""
        gs = cur.execute(
            "SELECT id FROM games WHERE sport_slug=? "
            "ORDER BY id DESC LIMIT 2000", (sport,)).fetchall()
        added = 0
        nonlocal next_id
        books = limit_books or SPORTSBOOKS
        # Cycle book per game; if not enough games, also add a second book
        # for some games.
        for gid, in gs:
            if added >= target:
                break
            book = books[h(f'r6-bo-{sport}-{gid}', len(books))]
            if (gid, book) in existing_pairs:
                continue
            existing_pairs.add((gid, book))
            key = f'r6-bo-{sport}-{gid}'
            favored_home = h(f'{key}-side', 2) == 0
            ml_strong = h(f'{key}-ml', 220, 110)
            home_ml = (-ml_strong) if favored_home else (ml_strong + 30)
            away_ml = (ml_strong + 30) if favored_home else (-ml_strong)
            spread_line = round(hf(f'{key}-spr', 1.5, 11.5), 1)
            spread_fav = 'home' if favored_home else 'away'
            if sport in ('nhl',):
                spread_line = round(hf(f'{key}-spr', 0.5, 1.5), 1)
            if sport in ('mlb',):
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
    n += emit_for_sport('nfl', target=250)
    n += emit_for_sport('mlb', target=180)
    n += emit_for_sport('nhl', target=130)
    n += emit_for_sport('soccer', target=80)
    n += emit_for_sport('ncaaf', target=40)
    n += emit_for_sport('ncaam', target=40)
    n += emit_for_sport('nba', target=120)
    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, home_moneyline, "
        "away_moneyline, spread_favorite, spread_line, total, over_odds, "
        "under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 4. Parlays (+30) ────────────────────────────────────────────────────────

R6_PARLAYS = [
    ('chiefs-bills-bears-survive', 'Chiefs/Bills/Bears Survive', 3,
     +485, 5.85, 'nfl', 'ESPN BET',
     ['Chiefs ML', 'Bills -3.5', 'Bears +6.5']),
    ('lakers-warriors-celtics-overs', 'Lakers/Warriors/Celtics Overs', 3,
     +610, 7.10, 'nba', 'DraftKings',
     ['Lakers o228.5', 'Warriors o235.5', 'Celtics o221.5']),
    ('yankees-dodgers-braves-runline', 'Yankees/Dodgers/Braves RunLine', 3,
     +505, 6.05, 'mlb', 'FanDuel',
     ['Yankees -1.5', 'Dodgers -1.5', 'Braves -1.5']),
    ('mcdavid-matthews-anytime', 'McDavid/Matthews/Pastrnak ATG', 3,
     +940, 10.40, 'nhl', 'BetMGM',
     ['McDavid ATG', 'Matthews ATG', 'Pastrnak ATG']),
    ('mahomes-allen-burrow-passing-tds', 'QB Passing TD Multi', 3,
     +750, 8.50, 'nfl', 'Caesars',
     ['Mahomes o1.5 pTD', 'Allen o1.5 pTD', 'Burrow o1.5 pTD']),
    ('curry-tatum-doncic-threes', 'Threes Made Trifecta', 3,
     +600, 7.00, 'nba', 'ESPN BET',
     ['Curry o4.5 3PM', 'Tatum o3.5 3PM', 'Doncic o3.5 3PM']),
    ('saturday-college-favorites', 'Saturday CFB Favorites', 4,
     +405, 5.05, 'ncaaf', 'DraftKings',
     ['Bama -10.5', 'UGA -7.5', 'OSU -14.5', 'Texas -6.5']),
    ('manchester-derby-overs', 'EPL Big-6 Overs', 3,
     +355, 4.55, 'soccer', 'FanDuel',
     ['Arsenal o1.5', 'ManCity o2.5', 'Liverpool o2.5']),
    ('judge-ohtani-acuna-hr-day', 'HR Race Stars Day', 3,
     +1850, 19.50, 'mlb', 'ESPN BET',
     ['Judge HR', 'Ohtani HR', 'Acuna HR']),
    ('panthers-rangers-stars-ml', 'Cup Contenders ML', 3,
     +360, 4.60, 'nhl', 'BetMGM',
     ['Panthers ML', 'Rangers ML', 'Stars ML']),
    ('sundays-best-overs-nfl', 'Sunday Overs Five-Pack', 5,
     +1450, 15.50, 'nfl', 'Caesars',
     ['KC o48.5', 'BUF o51.5', 'DAL o49.5', 'BAL o47.5', 'PHI o45.5']),
    ('three-team-chalk-cbb', 'CBB Three-Team Chalk', 3,
     +220, 3.20, 'ncaam', 'DraftKings',
     ['Duke ML', 'UConn ML', 'Kansas ML']),
    ('lakers-celtics-bucks-spreads', 'Star-Spread Treble', 3,
     +625, 7.25, 'nba', 'BetMGM',
     ['Lakers -3.5', 'Celtics -5.5', 'Bucks -4.5']),
    ('ucl-knockout-double', 'UCL Knockout Double', 2,
     +275, 3.75, 'soccer', 'ESPN BET',
     ['Real Madrid to advance', 'Man City to advance']),
    ('all-sport-saturday-cross', 'Cross-Sport Saturday', 4,
     +990, 10.90, 'fantasy', 'FanDuel',
     ['LeBron 25+', 'McDavid ATG', 'Mahomes 275+ pass yds',
      'Judge HR']),
    ('thursday-night-nfl', 'TNF Anytime + Spread', 2,
     +325, 4.25, 'nfl', 'Caesars',
     ['CeeDee Lamb ATG', 'Cowboys -2.5']),
    ('cup-final-future-double', 'Stanley Cup x World Series', 2,
     +1400, 15.00, 'fantasy', 'ESPN BET',
     ['Panthers Stanley Cup', 'Dodgers World Series']),
    ('nba-mvp-doncic-anytime-3', 'Doncic Triple-Double Multi', 3,
     +680, 7.80, 'nba', 'DraftKings',
     ['Doncic triple-double', 'Doncic o31.5 pts', 'Doncic o9.5 ast']),
    ('mlb-ace-strikeouts-trio', 'Ace Strikeouts Trio', 3,
     +800, 9.00, 'mlb', 'BetMGM',
     ['Skenes o7.5 K', 'Sale o6.5 K', 'Wheeler o6.5 K']),
    ('soccer-anytime-scorer-treble', 'EPL Anytime Treble', 3,
     +680, 7.80, 'soccer', 'FanDuel',
     ['Haaland ATG', 'Salah ATG', 'Saka ATG']),
    ('cfb-conference-favorites', 'CFB Conference Favorites', 4,
     +445, 5.45, 'ncaaf', 'ESPN BET',
     ['UGA SEC', 'tOSU B1G', 'Texas B12', 'Oregon Pac/B1G']),
    ('nfl-rookie-passing-multi', 'Rookie QB Multi', 3,
     +1100, 12.00, 'nfl', 'DraftKings',
     ['Caleb o225 pass', 'Maye o18 pass att', 'Daniels o45 rush']),
    ('curry-mvp-and-warriors-overs', 'Curry MVP / Warriors Wins', 2,
     +2200, 23.00, 'fantasy', 'ESPN BET',
     ['Curry MVP', 'Warriors o49.5 wins']),
    ('hockey-rookie-multi', 'NHL Rookie Multi', 3,
     +950, 10.50, 'nhl', 'BetMGM',
     ['Bedard ATG', 'Hutson o0.5 ast', 'Fantilli o0.5 pts']),
    ('three-team-cbb-overs', 'CBB Three-Pack Overs', 3,
     +405, 5.05, 'ncaam', 'DraftKings',
     ['Duke o145.5', 'Kansas o140.5', 'UConn o150.5']),
    ('nba-rookie-roy-prop', 'NBA ROY Multi', 2,
     +480, 5.80, 'nba', 'FanDuel',
     ['Wembanyama ROY', 'Wembanyama o19.5 pts']),
    ('nfl-prime-time-overs', 'Prime-Time Triple Overs', 3,
     +540, 6.40, 'nfl', 'ESPN BET',
     ['MNF o45.5', 'TNF o44.5', 'SNF o49.5']),
    ('mlb-postseason-futures-double',
     'Postseason Futures Double', 2,
     +1750, 18.50, 'mlb', 'BetMGM',
     ['Dodgers NL Pennant', 'Yankees AL Pennant']),
    ('soccer-clean-sheet-trio', 'Clean Sheet Trio', 3,
     +900, 10.00, 'soccer', 'Caesars',
     ['Arsenal CS', 'ManCity CS', 'Liverpool CS']),
    ('nba-finals-mvp-double',
     'Finals MVP Future Double', 2,
     +900, 10.00, 'nba', 'ESPN BET',
     ['Tatum Finals MVP', 'Celtics Champ']),
]


def make_parlays(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM parlays") or 0) + 1

    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM parlays").fetchall())
    rows = []
    for slug, title, lc, ao, do, sp, book, legs in R6_PARLAYS:
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


# ─── 5. Podcasts (+30) ───────────────────────────────────────────────────────

R6_PODCAST_SEED = [
    ('Beyond the Boxscore', 'beyond-the-boxscore', 'Tim MacMahon',
     'nba', 'Deep NBA tape and analytics rounds.', 220,
     'Closing lineup math', '2025-01-08', 50),
    ('Pelton Hoop Collective', 'pelton-hoop-collective', 'Kevin Pelton',
     'nba', 'Pelton-led roundtable across the NBA week.', 180,
     'Trade deadline winners', '2025-01-09', 55),
    ('Inside The Crease', 'inside-the-crease', 'Linda Cohn', 'nhl',
     'Insider voices on the NHL grind.', 140,
     'Goalie rotation experiments', '2025-01-09', 45),
    ('On the Pine', 'on-the-pine', 'Jeff Passan', 'mlb',
     'MLB roster construction and pitching.', 260,
     'Bullpen ace usage', '2025-01-09', 50),
    ('Total Yards', 'total-yards', 'Mina Kimes', 'nfl',
     'Kimes-led NFL film & analytics.', 210,
     'Film: rookie QB tape week 18', '2025-01-08', 50),
    ('Soccer Fix', 'soccer-fix', 'Luis Miguel Echegaray', 'soccer',
     'Daily soccer dish.', 320,
     'Champions League draw fallout', '2025-01-09', 35),
    ('CFB Insider Show', 'cfb-insider-show', 'Pete Thamel', 'ncaaf',
     'Insider CFB show.', 150,
     'Playoff committee weekly meeting', '2025-01-08', 50),
    ('CBB Today', 'cbb-today', 'Andy Katz', 'ncaam',
     'Daily CBB pod.', 110,
     'Big Monday preview', '2025-01-09', 35),
    ('Track & Trade', 'track-and-trade', 'Bobby Marks', 'nba',
     'Salary cap, trade, and front office show.', 200,
     'Tax aprons explained', '2025-01-09', 55),
    ('Fantasy Hockey Tuesday', 'fantasy-hockey-tuesday',
     'Victoria Matiash', 'fantasy',
     'Weekly fantasy hockey roundup.', 90,
     'Goalie streamers week 13', '2025-01-07', 40),
    ('Court Side With Doris', 'court-side-with-doris', 'Doris Burke',
     'nba', 'Burke-led NBA breakdown.', 140,
     'Game 1 of the road trip', '2025-01-08', 50),
    ('Schefty Pod', 'schefty-pod', 'Adam Schefter', 'nfl',
     'Schefter daily.', 480, 'Coaching carousel update',
     '2025-01-09', 40),
    ('Bracket Watch Daily', 'bracket-watch-daily',
     'Joe Lunardi', 'ncaam', 'Daily NCAA bracket reads.', 70,
     'New conference resume bumps', '2025-01-09', 30),
    ('UFC Pre-Show Live', 'ufc-pre-show-live', 'Brett Okamoto',
     'mma', 'Pre-card MMA roundtable.', 130,
     'PPV main-event scouting', '2025-01-08', 50),
    ('Premier League Daily', 'premier-league-daily-r6',
     'Mark Ogden', 'soccer', 'Daily EPL show.', 410,
     'Top-four scrum', '2025-01-09', 35),
    ('PGA Tour Daily', 'pga-tour-daily', 'Mark Schlabach',
     'golf', 'PGA news & wagers.', 95,
     'Saturday lead breakdown', '2025-01-09', 40),
    ('Tennis Beat', 'tennis-beat', 'D\'Arcy Maine', 'tennis',
     'Tennis daily.', 90, 'Grand Slam quarter draw',
     '2025-01-09', 35),
    ('Fantasy Football Locker', 'fantasy-football-locker',
     'Field Yates', 'fantasy',
     'Locked-and-loaded fantasy show.', 410,
     'Championship week plays', '2025-01-08', 55),
    ('Champions League Now', 'champions-league-now', 'Gab Marcotti',
     'soccer', 'UCL coverage.', 120,
     'Round of 16 lookahead', '2025-01-09', 40),
    ('NBA Today Saturday', 'nba-today-saturday',
     'Malika Andrews', 'nba',
     'Saturday wrap of NBA Today.', 80,
     'Eastern Conference watch', '2025-01-11', 30),
    ('Caitlin Clark Watch Pod II', 'caitlin-clark-watch-2',
     'Holly Rowe', 'ncaaw',
     'Caitlin Clark pro debut tracking.', 25,
     'WNBA preseason debut', '2025-01-09', 30),
    ('Around Hockey', 'around-hockey', 'Greg Wyshynski',
     'nhl', 'Around-the-league hockey show.', 220,
     'Goalie controversies week 12', '2025-01-09', 50),
    ('Around College Football', 'around-college-football',
     'Heather Dinich', 'ncaaf',
     'CFB roundtable.', 160,
     'Bowl season hangover', '2025-01-09', 45),
    ('March Madness Vault II', 'march-madness-vault-r6',
     'Andy Katz', 'ncaam',
     'Replay/breakdown vault for big-game vibe.', 50,
     'Final Four set', '2025-01-09', 40),
    ('NFL Insider Live', 'nfl-insider-live',
     'Dan Graziano', 'nfl',
     'Graziano insider show.', 240,
     'Free agency early prep', '2025-01-09', 40),
    ('ESPN BET Daily', 'espn-bet-daily', 'Erin Dolan',
     'fantasy', 'Daily ESPN BET picks pod.', 110,
     'Sunday card best bets', '2025-01-12', 30),
    ('Fantasy Baseball Today II', 'fantasy-baseball-today-r6',
     'Tristan Cockcroft', 'fantasy',
     'Spring preview fantasy show.', 60,
     'Top-10 ADP movers', '2025-01-09', 45),
    ('Power Index Live II', 'power-index-live-r6',
     'Seth Walder', 'nfl',
     'FPI Live for week-of forecasts.', 90,
     'Wild Card simulations', '2025-01-08', 45),
    ('Soccer Power Index Live',
     'soccer-power-index-live', 'Tom Hamilton', 'soccer',
     'SPI live show.', 60,
     'Premier League playoff race', '2025-01-09', 35),
    ('Hammer & Rails Daily', 'hammer-and-rails-daily',
     'Pete Thamel', 'ncaaf',
     'Daily CFB recruiting & coaching.', 130,
     'Signing day recap', '2025-01-09', 45),
]


def make_podcasts(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM podcasts") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM podcasts").fetchall())
    rows = []
    for title, slug, host, sport_slug, desc, eps, le, ld, dur in R6_PODCAST_SEED:
        if slug in existing:
            continue
        existing.add(slug)
        rows.append((next_id, title, slug, host, sport_slug,
                     desc, eps, le, ld, dur))
        next_id += 1
    cur.executemany(
        "INSERT INTO podcasts (id, title, slug, host, sport_slug, "
        "description, episode_count, latest_episode_title, "
        "latest_episode_date, duration_minutes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 6. Play-by-play (+600) ──────────────────────────────────────────────────

NBA_PBP = [
    ('made_3pt', '{actor} drains a 3 from the top'),
    ('made_2pt', '{actor} hits the pull-up jumper'),
    ('made_layup', '{actor} converts the and-1 layup'),
    ('made_dunk', '{actor} alley-oop slam'),
    ('missed_3pt', '{actor} misses the catch-and-shoot 3'),
    ('off_rebound', '{actor} grabs the offensive board'),
    ('def_rebound', '{actor} pulls down the defensive rebound'),
    ('assist', '{actor} dishes the assist'),
    ('steal', '{actor} jumps the passing lane for a steal'),
    ('block', '{actor} swats it'),
    ('foul', 'Personal foul on {actor}'),
    ('ft_made', '{actor} converts both at the line'),
    ('turnover', '{actor} loses control'),
]
NHL_PBP = [
    ('goal', '{actor} roofs one top shelf'),
    ('shot', '{actor} fires from distance, saved'),
    ('hit', '{actor} delivers a clean check'),
    ('takeaway', '{actor} pickpockets at the blue line'),
    ('penalty', 'Penalty on {actor} for tripping'),
    ('faceoff_won', '{actor} cleanly wins the draw'),
    ('save', 'Goalie kicks aside a {actor} wrister'),
]
MLB_PBP = [
    ('single', '{actor} singles up the middle'),
    ('double', '{actor} doubles down the line'),
    ('homer', '{actor} crushes a no-doubter'),
    ('strikeout', '{actor} strikes out swinging'),
    ('walk', '{actor} draws the walk'),
    ('groundout', '{actor} grounds out to short'),
    ('flyout', '{actor} flies out to right'),
]
NFL_PBP = [
    ('pass_complete', '{actor} hits the slant for a first down'),
    ('rush', '{actor} bounces it outside for a gain of 6'),
    ('pass_td', '{actor} fires a strike for a TD'),
    ('sack', '{actor} takes down the QB'),
    ('field_goal', '{actor} drills the field goal'),
    ('punt', 'Punt fair-caught at the 12'),
]


def make_play_by_play(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM play_by_play") or 0) + 1
    rows = []

    def actor_names(team_id):
        rs = cur.execute(
            "SELECT name FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 8", (team_id,)).fetchall()
        return [r[0] for r in rs] if rs else [f'Player #{team_id}']

    existing_gids = set(r[0] for r in cur.execute(
        "SELECT DISTINCT game_id FROM play_by_play").fetchall())

    def pick_games(sport, n):
        candidates = cur.execute(
            "SELECT id, sport_slug, home_team_id, away_team_id, "
            "       home_score, away_score "
            "FROM games WHERE sport_slug=? AND status='final' "
            "ORDER BY id DESC", (sport,)).fetchall()
        out = []
        for c in candidates:
            if c[0] in existing_gids:
                continue
            out.append(c)
            if len(out) >= n:
                break
        return out

    plan = [
        ('nba', 8,  NBA_PBP, ['Q1', 'Q2', 'Q3', 'Q4'], 30),
        ('nhl', 6,  NHL_PBP, ['1st', '2nd', '3rd'],    30),
        ('mlb', 6,  MLB_PBP, ['T1', 'B1', 'T2', 'B2',
                              'T3', 'B3', 'T4', 'B4'], 25),
        ('nfl', 6,  NFL_PBP, ['Q1', 'Q2', 'Q3', 'Q4'], 28),
    ]
    for sport, ngames, events, periods, ev_count in plan:
        games = pick_games(sport, ngames)
        for gid, sport_slug, hid, aid, fhs, fas in games:
            home_actors = actor_names(hid)
            away_actors = actor_names(aid)
            score_h = 0
            score_a = 0
            for seq in range(ev_count):
                key = f'r6-pbp-{sport}-{gid}-{seq}'
                ev_idx = h(f'{key}-ev', len(events))
                ev_type, tpl = events[ev_idx]
                is_home = (h(f'{key}-side', 2) == 0)
                team_id = hid if is_home else aid
                pool = home_actors if is_home else away_actors
                actor = pool[h(f'{key}-act', len(pool))]
                desc = tpl.format(actor=actor)
                inc_h, inc_a = 0, 0
                if ev_type == 'made_3pt':
                    inc_h, inc_a = (3, 0) if is_home else (0, 3)
                elif ev_type in ('made_2pt', 'made_layup',
                                 'made_dunk'):
                    inc_h, inc_a = (2, 0) if is_home else (0, 2)
                elif ev_type == 'goal':
                    inc_h, inc_a = (1, 0) if is_home else (0, 1)
                elif ev_type in ('single', 'double', 'walk',
                                 'homer'):
                    inc_h, inc_a = (1, 0) if is_home else (0, 1)
                elif ev_type == 'pass_td':
                    inc_h, inc_a = (7, 0) if is_home else (0, 7)
                elif ev_type == 'field_goal':
                    inc_h, inc_a = (3, 0) if is_home else (0, 3)
                elif ev_type == 'ft_made':
                    inc_h, inc_a = (2, 0) if is_home else (0, 2)
                score_h += inc_h
                score_a += inc_a
                period_label = periods[seq * len(periods) // ev_count]
                clock = f'{11 - (seq % 12)}:{(seq * 7) % 60:02d}'
                rows.append((next_id, gid, sport_slug, seq, period_label,
                             clock, team_id, actor, ev_type, desc,
                             score_h, score_a))
                next_id += 1
    cur.executemany(
        "INSERT INTO play_by_play (id, game_id, sport_slug, sequence, "
        "period, clock, team_id, actor_name, event_type, description, "
        "score_home, score_away) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R6 extension already applied — no-op.')
        conn.close()
        return
    n_gm  = make_games(cur)
    n_ar  = make_articles(cur)
    n_bo  = make_betting(cur)
    n_pl  = make_parlays(cur)
    n_pc  = make_podcasts(cur)
    n_pbp = make_play_by_play(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R6 inserted: games={n_gm}, articles={n_ar}, '
          f'betting_odds={n_bo}, parlays={n_pl}, podcasts={n_pc}, '
          f'play_by_play={n_pbp}')


if __name__ == '__main__':
    main()
