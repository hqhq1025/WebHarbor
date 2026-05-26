#!/usr/bin/env python3
"""R4 polish extension for sites/espn — direct sqlite3 INSERT only.

Continues the gotcha #14 path used by _r2_extend.py and _r3_extend.py: the
shipped HF `instance_seed/espn.db` has drifted from `seed_data.py`, so we
extend the live DB with idempotent direct INSERTs rather than rebuilding.

What R4 adds on top of R3:
  * +1000 games        → 2200+ total (multi-season NBA/NFL/MLB/NHL/Soccer)
  * +1200 player_stats → 2500+ total
  * +400 betting_odds  → 500+ total (now covers older games too)
  * +260 draft_picks   → 400+ total (2022 NFL, 2025 NBA mock, 2023 NBA actual)
  * +40 podcasts       → 50+ total
  * +65 awards         → 100+ total (1 more historical season per sport)
  * +200 articles      → 2200+ total (fantasy/bet/draft beat coverage)
  * NEW play_by_play   ~1200 rows (~30 marquee games × ~40 events each)
  * NEW watchables     ~100 rows (ESPN+ shows / series)
  * NEW parlays        ~30 sample multi-leg parlays
  * Marker row sports.slug '_r4_marker' (id=101) — idempotent.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r4_marker` row in `sports`. Re-running is a no-op.
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
        "SELECT 1 FROM sports WHERE slug='_r4_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (101, 'R4 marker', '_r4_marker', 'r4_extend applied',
         '/_internal/', 101, 0))


def slugify(text: str) -> str:
    out = (text.lower().replace("'", '').replace('"', '').replace('&', 'and')
           .replace('.', '').replace(',', '').replace('?', '')
           .replace(':', '').replace('/', '-').replace('—', '-')
           .replace(' ', '-'))
    out = ''.join(c for c in out if c.isalnum() or c == '-')
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')


# ─── 1. New tables ────────────────────────────────────────────────────────────

NEW_TABLES = [
    """CREATE TABLE IF NOT EXISTS play_by_play (
        id INTEGER PRIMARY KEY,
        game_id INTEGER NOT NULL,
        sport_slug VARCHAR(20),
        sequence INTEGER,
        period VARCHAR(10),
        clock VARCHAR(10),
        team_id INTEGER,
        actor_name VARCHAR(150),
        event_type VARCHAR(30),
        description VARCHAR(300),
        score_home INTEGER,
        score_away INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS watchables (
        id INTEGER PRIMARY KEY,
        title VARCHAR(200),
        slug VARCHAR(200),
        kind VARCHAR(40),
        sport_slug VARCHAR(20),
        description TEXT,
        is_espn_plus INTEGER DEFAULT 1,
        is_live INTEGER DEFAULT 0,
        duration_minutes INTEGER,
        release_date VARCHAR(20),
        host_or_studio VARCHAR(150)
    )""",
    """CREATE TABLE IF NOT EXISTS parlays (
        id INTEGER PRIMARY KEY,
        slug VARCHAR(80),
        title VARCHAR(200),
        leg_count INTEGER,
        american_odds INTEGER,
        decimal_odds FLOAT,
        legs_json TEXT,
        sport_slug VARCHAR(20),
        sportsbook VARCHAR(40),
        is_featured INTEGER DEFAULT 0
    )""",
    "CREATE INDEX IF NOT EXISTS ix_play_by_play_game_id ON play_by_play (game_id)",
    "CREATE INDEX IF NOT EXISTS ix_play_by_play_sport_slug ON play_by_play (sport_slug)",
    "CREATE INDEX IF NOT EXISTS ix_watchables_slug ON watchables (slug)",
    "CREATE INDEX IF NOT EXISTS ix_watchables_sport_slug ON watchables (sport_slug)",
    "CREATE INDEX IF NOT EXISTS ix_parlays_slug ON parlays (slug)",
]


def create_new_tables(cur):
    for sql in NEW_TABLES:
        cur.execute(sql)


def normalize(cur):
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── 2. Games (extend across multiple seasons) ───────────────────────────────

NBA_VENUES = ['TD Garden', 'Crypto.com Arena', 'Madison Square Garden',
              'Chase Center', 'Ball Arena', 'Paycom Center',
              'Kaseya Center', 'American Airlines Center',
              'Footprint Center', 'Fiserv Forum', 'Spectrum Center',
              'Smoothie King Center', 'Target Center', 'Moda Center']
NHL_VENUES = ['TD Garden', 'Madison Square Garden', 'United Center',
              'Rogers Arena', 'Scotiabank Arena', 'Bell Centre',
              'Wells Fargo Center', 'Capital One Arena',
              'Amerant Bank Arena', 'Honda Center', 'PPG Paints Arena',
              'Ball Arena', 'Climate Pledge Arena']
NFL_VENUES = ['Arrowhead Stadium', 'AT&T Stadium', 'SoFi Stadium',
              'Lambeau Field', 'Lincoln Financial Field', 'M&T Bank Stadium',
              'Highmark Stadium', 'GEHA Field', 'MetLife Stadium',
              "Levi's Stadium", 'Empower Field at Mile High',
              'Hard Rock Stadium', 'NRG Stadium']
MLB_VENUES = ['Yankee Stadium', 'Fenway Park', 'Dodger Stadium',
              'Wrigley Field', 'Oracle Park', 'Tropicana Field',
              'Citi Field', 'Petco Park', 'Coors Field',
              'Camden Yards', 'Globe Life Field', 'PNC Park', 'Truist Park']
SOCCER_VENUES = ['Emirates Stadium', 'Old Trafford', 'Anfield',
                 'Stamford Bridge', 'Etihad Stadium',
                 'Tottenham Hotspur Stadium', 'Camp Nou', 'Santiago Bernabéu',
                 'Allianz Arena', 'San Siro']


def make_games(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM games") or 0) + 1
    rows = []

    teams = {}
    for sp in ('nba', 'nhl', 'mlb', 'nfl', 'soccer'):
        teams[sp] = cur.execute(
            "SELECT id, full_name, slug FROM teams "
            "WHERE sport_slug=? ORDER BY id", (sp,)).fetchall()

    def star_for(team_id):
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (team_id,)).fetchone()
        return row or ('Star Player', 'F')

    # NBA 2021-22 season (180), 2022-23 season (180)
    for season_label, start, count in [
            ('2021-22', date(2021, 10, 19), 200),
            ('2022-23', date(2022, 10, 18), 200),
            ('2023-24-late', date(2024, 4, 1), 50)]:
        for i in range(count):
            a = h(f'r4-nba-{season_label}-a-{i}', len(teams['nba']))
            b = h(f'r4-nba-{season_label}-b-{i}', len(teams['nba']))
            if a == b:
                b = (b + 1) % len(teams['nba'])
            home = teams['nba'][a]
            away = teams['nba'][b]
            gdate = start + timedelta(
                days=h(f'r4-nba-{season_label}-d-{i}', 180))
            if season_label == '2023-24-late':
                gdate = date(2024, 4, 1) + timedelta(
                    days=h(f'r4-nba-late-{i}', 9))
            hs = h(f'r4-nba-{season_label}-hs-{i}', 30, 95)
            as_ = h(f'r4-nba-{season_label}-as-{i}', 30, 88)
            ven = NBA_VENUES[i % len(NBA_VENUES)]
            star_h = star_for(home[0])
            leaders = json.dumps({
                'top_scorer_name': star_h[0],
                'top_scorer_pts': h(f'r4-nba-{season_label}-tp-{i}', 25, 18),
                'top_scorer_team': home[1],
                'top_scorer_position': star_h[1],
                'home_high_scorer': star_h[0],
                'home_high_points': h(f'r4-nba-{season_label}-hh-{i}', 25, 18),
                'away_high_scorer': star_for(away[0])[0],
                'away_high_points': h(f'r4-nba-{season_label}-ah-{i}', 22, 16),
            })
            rows.append((
                next_id, 'nba', home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                f"{7 + (i % 4)}:{30 if i % 2 else '00'} PM ET",
                'final', 'Final', 'ESPN', ven,
                f"({season_label}) {home[1]} beat the {away[1]} {hs}-{as_}.",
                'https://www.ticketmaster.com', leaders))
            next_id += 1

    # NHL 2021-22, 2022-23 (140 + 140)
    for season_label, start, count in [
            ('2021-22', date(2021, 10, 12), 140),
            ('2022-23', date(2022, 10, 7), 140)]:
        for i in range(count):
            a = h(f'r4-nhl-{season_label}-a-{i}', len(teams['nhl']))
            b = h(f'r4-nhl-{season_label}-b-{i}', len(teams['nhl']))
            if a == b:
                b = (b + 1) % len(teams['nhl'])
            home = teams['nhl'][a]
            away = teams['nhl'][b]
            gdate = start + timedelta(
                days=h(f'r4-nhl-{season_label}-d-{i}', 200))
            hs = h(f'r4-nhl-{season_label}-hs-{i}', 6, 1)
            as_ = h(f'r4-nhl-{season_label}-as-{i}', 6, 1)
            ven = NHL_VENUES[i % len(NHL_VENUES)]
            star_h = star_for(home[0])
            leaders = json.dumps({
                'top_scorer_name': star_h[0],
                'top_scorer_pts': h(f'r4-nhl-{season_label}-tp-{i}', 3, 1),
                'top_scorer_team': home[1],
                'top_scorer_position': star_h[1],
                'home_high_scorer': star_h[0],
                'home_high_points': h(f'r4-nhl-{season_label}-hh-{i}', 3, 1),
                'away_high_scorer': star_for(away[0])[0],
                'away_high_points': h(f'r4-nhl-{season_label}-ah-{i}', 3, 1),
            })
            rows.append((
                next_id, 'nhl', home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                '7:30 PM ET', 'final', 'Final', 'ESPN+', ven,
                f"({season_label}) {home[1]} {hs}-{as_} {away[1]}.",
                'https://www.ticketmaster.com', leaders))
            next_id += 1

    # MLB 2022, 2024 (130 + 50)
    for season_label, start, count in [
            ('2022', date(2022, 4, 7), 130),
            ('2024-late', date(2024, 4, 1), 50)]:
        for i in range(count):
            a = h(f'r4-mlb-{season_label}-a-{i}', len(teams['mlb']))
            b = h(f'r4-mlb-{season_label}-b-{i}', len(teams['mlb']))
            if a == b:
                b = (b + 1) % len(teams['mlb'])
            home = teams['mlb'][a]
            away = teams['mlb'][b]
            if season_label == '2024-late':
                gdate = start + timedelta(
                    days=h(f'r4-mlb-late-{i}', 9))
            else:
                gdate = start + timedelta(
                    days=h(f'r4-mlb-{season_label}-d-{i}', 175))
            hs = h(f'r4-mlb-{season_label}-hs-{i}', 12, 0)
            as_ = h(f'r4-mlb-{season_label}-as-{i}', 12, 0)
            ven = MLB_VENUES[i % len(MLB_VENUES)]
            star_h = star_for(home[0])
            leaders = json.dumps({
                'top_scorer_name': star_h[0],
                'top_scorer_pts': hs,
                'top_scorer_team': home[1],
                'top_scorer_position': star_h[1] or '1B',
                'home_high_scorer': star_h[0],
                'home_high_points': hs,
                'away_high_scorer': star_for(away[0])[0],
                'away_high_points': as_,
            })
            rows.append((
                next_id, 'mlb', home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                '7:05 PM ET', 'final', 'Final', 'MLB Network', ven,
                f"({season_label}) {home[1]} {hs}-{as_} {away[1]}.",
                'https://www.mlb.com/tickets', leaders))
            next_id += 1

    # NFL 2021, 2024 schedule preview (45 + 35)
    for season_label, start, count in [
            ('2021', date(2021, 9, 9), 45),
            ('2024-preview', date(2024, 4, 5), 35)]:
        for i in range(count):
            a = h(f'r4-nfl-{season_label}-a-{i}', len(teams['nfl']))
            b = h(f'r4-nfl-{season_label}-b-{i}', len(teams['nfl']))
            if a == b:
                b = (b + 1) % len(teams['nfl'])
            home = teams['nfl'][a]
            away = teams['nfl'][b]
            if season_label == '2024-preview':
                # 2024 regular season starts Sep 5; mark as scheduled
                gdate = date(2024, 9, 5) + timedelta(
                    days=h(f'r4-nfl-2024-{i}', 110))
                status = 'scheduled'
                period = 'Scheduled'
                hs, as_ = 0, 0
                recap = f'2024 season game: {away[1]} at {home[1]}.'
            else:
                gdate = start + timedelta(
                    days=h(f'r4-nfl-{season_label}-d-{i}', 125))
                status = 'final'
                period = 'Final'
                hs = h(f'r4-nfl-{season_label}-hs-{i}', 31, 10)
                as_ = h(f'r4-nfl-{season_label}-as-{i}', 31, 7)
                recap = f'({season_label}) {home[1]} {hs}-{as_} {away[1]}.'
            ven = NFL_VENUES[i % len(NFL_VENUES)]
            star_h = star_for(home[0])
            leaders = json.dumps({
                'top_scorer_name': star_h[0],
                'top_scorer_pts': (hs // 7) if hs else 0,
                'top_scorer_team': home[1],
                'top_scorer_position': star_h[1] or 'QB',
                'home_high_scorer': star_h[0],
                'home_high_points': hs,
                'away_high_scorer': star_for(away[0])[0],
                'away_high_points': as_,
            }) if status == 'final' else '{}'
            rows.append((
                next_id, 'nfl', home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                '1:00 PM ET', status, period, 'FOX', ven, recap,
                'https://www.nfl.com/tickets', leaders))
            next_id += 1

    # Soccer 2022-23 EPL/UCL (60)
    if teams['soccer']:
        for i in range(60):
            a = h(f'r4-soc-a-{i}', len(teams['soccer']))
            b = h(f'r4-soc-b-{i}', len(teams['soccer']))
            if a == b:
                b = (b + 1) % len(teams['soccer'])
            home = teams['soccer'][a]
            away = teams['soccer'][b]
            gdate = date(2022, 8, 6) + timedelta(
                days=h(f'r4-soc-d-{i}', 270))
            hs = h(f'r4-soc-hs-{i}', 5, 0)
            as_ = h(f'r4-soc-as-{i}', 5, 0)
            ven = SOCCER_VENUES[i % len(SOCCER_VENUES)]
            star_h = star_for(home[0])
            leaders = json.dumps({
                'top_scorer_name': star_h[0],
                'top_scorer_pts': hs,
                'top_scorer_team': home[1],
                'top_scorer_position': star_h[1] or 'F',
                'home_high_scorer': star_h[0],
                'home_high_points': hs,
                'away_high_scorer': star_for(away[0])[0],
                'away_high_points': as_,
            })
            rows.append((
                next_id, 'soccer', home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                '12:30 PM ET', 'final', 'FT', 'ESPN+', ven,
                f"(2022-23) {home[1]} drew {away[1]} {hs}-{as_}." if hs == as_
                else f"(2022-23) {home[1]} beat {away[1]} {hs}-{as_}.",
                'https://www.ticketmaster.com', leaders))
            next_id += 1

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 3. Player stats (more seasons & breadth) ────────────────────────────────

def make_player_stats(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM player_stats") or 0) + 1
    rows = []

    # 2021-22 historical season for top-N per sport (career breadth)
    season_quotas = [
        ('2021-22', {'nba': 140, 'nhl': 120}),
        ('2021',    {'nfl': 120, 'mlb': 130}),
        ('2020-21', {'nba': 110, 'nhl': 90}),
        ('2020',    {'nfl': 90, 'mlb': 100}),
        ('2022-23', {'nba': 80, 'nhl': 70}),
        ('2024-projection', {'nba': 60, 'nfl': 50, 'mlb': 50, 'nhl': 50}),
        ('2019-20', {'nba': 80, 'nhl': 60, 'mlb': 60}),
        ('2019',    {'nfl': 50}),
    ]
    for season, quotas in season_quotas:
        for sport_slug, q in quotas.items():
            players = cur.execute(
                "SELECT id, name, position FROM players "
                "WHERE sport_slug=? ORDER BY id LIMIT ?",
                (sport_slug, q)).fetchall()
            for pid, _pname, pos in players:
                row = _make_stat_row(sport_slug, pid, pos, season, next_id)
                rows.append(row)
                next_id += 1

    # Pass: backfill any uncovered soccer players for 2022-23 + 2021-22
    for season in ('2022-23', '2021-22'):
        players = cur.execute(
            "SELECT p.id, p.name, p.position FROM players p "
            "WHERE p.sport_slug='soccer' AND p.id NOT IN ("
            "  SELECT player_id FROM player_stats "
            "  WHERE stat_type='season' AND season=?) "
            "ORDER BY p.id LIMIT 50", (season,)).fetchall()
        for pid, _pname, pos in players:
            row = _make_stat_row('soccer', pid, pos, season, next_id)
            rows.append(row)
            next_id += 1

    by_cols = {}
    for cols, vals in rows:
        key = tuple(cols)
        by_cols.setdefault(key, []).append(vals)
    inserted = 0
    for cols, batch in by_cols.items():
        placeholders = ','.join('?' * len(cols))
        sql = (f"INSERT INTO player_stats ({','.join(cols)}) "
               f"VALUES ({placeholders})")
        cur.executemany(sql, batch)
        inserted += len(batch)
    return inserted


def _make_stat_row(sport_slug, pid, pos, season, next_id):
    key = f'r4-{season}-{sport_slug}-{pid}'
    base = {
        'id': next_id, 'player_id': pid,
        'season': season, 'stat_type': 'season',
        'games_played': h(f'{key}-gp', 40, 30),
        'games_started': h(f'{key}-gs', 40, 18),
    }
    if sport_slug in ('nba', 'ncaam', 'ncaaw'):
        base.update({
            'points_per_game': round(hf(f'{key}-ppg', 4, 30), 1),
            'rebounds_per_game': round(hf(f'{key}-rpg', 1.5, 12), 1),
            'assists_per_game': round(hf(f'{key}-apg', 0.8, 10), 1),
            'steals_per_game': round(hf(f'{key}-spg', 0.2, 2.2), 1),
            'blocks_per_game': round(hf(f'{key}-bpg', 0.1, 2.7), 1),
            'fg_pct': round(hf(f'{key}-fg', 0.38, 0.58), 3),
            'three_pt_pct': round(hf(f'{key}-3p', 0.30, 0.44), 3),
            'ft_pct': round(hf(f'{key}-ft', 0.65, 0.92), 3),
            'minutes_per_game': round(hf(f'{key}-mpg', 16, 38), 1),
        })
    elif sport_slug == 'nfl':
        p = (pos or '').upper()
        if p == 'QB':
            base.update({
                'passing_yards': h(f'{key}-pyd', 3800, 2200),
                'passing_tds': h(f'{key}-ptd', 32, 12),
                'rushing_yards': h(f'{key}-ryd', 400, 50),
                'rushing_tds': h(f'{key}-rtd', 7, 0),
            })
        elif p == 'RB':
            base.update({
                'rushing_yards': h(f'{key}-ryd', 1200, 600),
                'rushing_tds': h(f'{key}-rtd', 14, 3),
                'receptions': h(f'{key}-rec', 60, 18),
                'receiving_yards': h(f'{key}-recy', 600, 130),
            })
        elif p in ('WR', 'TE'):
            base.update({
                'receptions': h(f'{key}-rec', 90, 40),
                'receiving_yards': h(f'{key}-recy', 1200, 500),
                'receiving_tds': h(f'{key}-rectd', 12, 3),
            })
        else:
            base.update({
                'tackles': h(f'{key}-tck', 90, 35),
                'sacks': round(hf(f'{key}-sk', 0.5, 14), 1),
            })
    elif sport_slug == 'mlb':
        if 'P' in (pos or ''):
            base.update({
                'era': round(hf(f'{key}-era', 2.4, 5.6), 2),
                'strikeouts': h(f'{key}-so', 230, 60),
                'wins_pitcher': h(f'{key}-wp', 18, 4),
            })
        else:
            base.update({
                'batting_avg': round(hf(f'{key}-ba', 0.21, 0.34), 3),
                'home_runs': h(f'{key}-hr', 42, 4),
                'rbi': h(f'{key}-rbi', 105, 25),
                'stolen_bases': h(f'{key}-sb', 28, 1),
            })
    elif sport_slug == 'nhl':
        base.update({
            'goals': h(f'{key}-g', 45, 5),
            'hockey_assists': h(f'{key}-a', 55, 8),
            'hockey_points': h(f'{key}-pt', 90, 15),
            'plus_minus': h(f'{key}-pm', 60, -25),
            'penalty_minutes': h(f'{key}-pim', 90, 4),
        })
    elif sport_slug == 'soccer':
        base.update({
            'soccer_goals': h(f'{key}-sg', 22, 1),
            'soccer_assists': h(f'{key}-sa', 14, 1),
            'soccer_appearances': h(f'{key}-sap', 38, 8),
            'yellow_cards': h(f'{key}-yc', 10, 0),
            'red_cards': h(f'{key}-rc', 2, 0),
        })
    cols = list(base.keys())
    vals = [base[c] for c in cols]
    return (cols, vals)


# ─── 4. Articles (fantasy/bet/draft beat coverage) ───────────────────────────

R4_FANTASY_TEMPLATES = [
    ("Fantasy trade analyzer: should you flip {star} for two role players?",
     "Our trade analyzer crunches the rest-of-season projections. Trading {star} away nets you slightly more total fantasy points if the rebuilds line up with playoff matchups."),
    ("Waiver-wire heat map: top adds at every position",
     "Streaming guards and tight-end injuries shape the {team}-led wire pickups. The model loves a deep-league add at center for owners chasing rebounds."),
    ("Dynasty rookie redraft: where {star} now lands",
     "Six months in, {star} has shaken the dynasty rookie order. Our updated redraft slots {star} top three with case-by-case build notes."),
    ("Fantasy lineup math: which {team} player to start tonight",
     "{team} face the {opp} on a back-to-back. {star} is the better start in points leagues; the role-player matchup wins in category builds."),
    ("Punt-FT% deep dive: how {star} fits the build",
     "Punt-FT% builds love {star}'s rebounding profile. We map the rest of the team build around the percentage chase."),
]

R4_BET_TEMPLATES = [
    ("ESPN BET parlay of the day: three-leg play for tonight",
     "Our betting desk's parlay-of-the-day pulls a same-game heater and two best-bet sides. Total american odds clear +500."),
    ("Sharp report: where the model disagrees with the closing line",
     "The model flags a back-to-back travel spot for the {team}. Closing-line value sits with the {opp} +{pts}."),
    ("Futures update: {star} odds shift after MVP April",
     "{star}'s MVP odds shortened to -125 after April production. The {team}' division-title number tightened as well."),
    ("Parlay-builder showcase: how to layer a 4-leg ticket",
     "Walk-through of building a four-leg ticket from spreads, totals, and a player prop. The model trims correlation between legs."),
    ("Bad-beat watch: closing-line moves you missed",
     "Three closing-line shifts caught our model's attention. Bettors who took early numbers cashed."),
]

R4_DRAFT_TEMPLATES = [
    ("NFL Draft scouting profile: {star} at {pos}",
     "Our pre-draft profile of {star} highlights frame, athletic testing, and tape concerns. Most boards have the prospect locked into the first round."),
    ("NBA Draft combine notes: who measured better than expected",
     "Pre-draft camp wingspan and shuttle numbers reshape the second-round board. {star} measured the best of the new group."),
    ("Mock Draft 6.0: the {team} pivot at pick 14",
     "Our final mock has the {team} pivoting to {pos}. Front-office sources call the position a top-three need."),
    ("247composite reaction: top recruit lands at {team}",
     "{team} secured a top-ten composite recruit. Coaches plan to play the freshman immediately alongside {star}."),
    ("Top-100 recruiting class breakdown by school",
     "School-by-school totals for the top-100 composite. ACC and SEC programs continue to consolidate at the top."),
]

R4_AWARDS_TEMPLATES = [
    ("Awards watch: who are the finalists for MVP this season?",
     "Three finalists separated themselves through April. Our column lays out the voting case for each, including {star}."),
    ("Hart Trophy debate: ranking the finalists",
     "{star} and two others are locked in as Hart finalists. Five-on-five impact, ice-time leverage, and team success will decide the vote."),
    ("Coach of the Year tiers: front-runners and dark horses",
     "Front-runners and dark horses for Coach of the Year split into three tiers. The award rarely repeats."),
]

R4_PODCAST_TEMPLATES = [
    ("Podcast roundup: best episodes of the week",
     "A weekly roundup of the top ESPN podcast episodes. Standout debates on {star}'s ceiling and the {team} playoff outlook."),
    ("New series: Bracketology breakdown podcast",
     "ESPN launched a Bracketology breakdown podcast with weekly seed-line analysis. {star} headlines the first guest list."),
]


R4_PLAN = [
    ('fantasy', R4_FANTASY_TEMPLATES, 60, 6),
    ('nba',     R4_BET_TEMPLATES,     30, 6),
    ('nfl',     R4_DRAFT_TEMPLATES,   35, 6),
    ('nhl',     R4_AWARDS_TEMPLATES,  25, 6),
    ('mlb',     R4_FANTASY_TEMPLATES, 20, 8),
    ('soccer',  R4_PODCAST_TEMPLATES, 15, 8),
    ('ncaaf',   R4_DRAFT_TEMPLATES,   15, 8),
]


def article_authors(idx: int) -> str:
    pool = ['Mike Clay', 'Matthew Berry', 'Field Yates', 'Mina Kimes',
            'Bobby Marks', 'Tristan H. Cockcroft', 'Eric Karabell',
            'Joe Fortenbaugh', 'Erin Dolan', 'Tyler Fulghum',
            'Doug Kezirian', 'Anita Marks', 'Andre Snellings',
            'David Schoenfield', 'Adam Schefter', 'Ramona Shelburne',
            'ESPN BET Staff', 'ESPN Fantasy Staff']
    return pool[idx % len(pool)]


def make_articles(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing_slugs = {r[0] for r in
                      cur.execute("SELECT slug FROM articles").fetchall()}

    teams_by_sport = {}
    for sport_slug in ('nba', 'nfl', 'nhl', 'mlb', 'soccer', 'ncaaf',
                       'fantasy'):
        rows = cur.execute(
            "SELECT id, full_name, slug FROM teams "
            "WHERE sport_slug=? ORDER BY id", (sport_slug,)).fetchall()
        teams_by_sport[sport_slug] = rows or teams_by_sport.get('nba', [])

    stars_by_team = {}
    for tid_row in cur.execute(
            "SELECT DISTINCT team_id FROM players "
            "WHERE team_id IS NOT NULL ORDER BY team_id").fetchall():
        tid = tid_row[0]
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (tid,)).fetchone()
        if row:
            stars_by_team[tid] = row

    rows_to_insert = []
    for sport_slug, templates, count, headline_every in R4_PLAN:
        teams = (teams_by_sport.get(sport_slug)
                 or teams_by_sport.get('nba'))
        if not teams:
            continue
        for i in range(count):
            t_idx = h(f'r4-{sport_slug}-team-{i}', len(teams))
            opp_idx = h(f'r4-{sport_slug}-opp-{i}', len(teams))
            if opp_idx == t_idx:
                opp_idx = (opp_idx + 1) % len(teams)
            team_id, team_name, _team_slug = teams[t_idx]
            _, opp_name, _ = teams[opp_idx]
            star_row = stars_by_team.get(team_id)
            star_name = star_row[0] if star_row else f'{team_name} captain'
            star_pos = star_row[1] if star_row else 'F'

            tpl_i = h(f'r4-{sport_slug}-tpl-{i}', len(templates))
            title_tpl, body_tpl = templates[tpl_i]
            pts = h(f'r4-{sport_slug}-pts-{i}', 28, 6)
            pos_pool = ['EDGE', 'OT', 'CB', 'WR', 'LB', 'S', 'QB']
            pos_pick = pos_pool[h(f'r4-{sport_slug}-pos-{i}', len(pos_pool))]
            try:
                title = title_tpl.format(team=team_name, opp=opp_name,
                                         star=star_name, pts=pts,
                                         pos=pos_pick)
                body = body_tpl.format(team=team_name, opp=opp_name,
                                       star=star_name, pts=pts,
                                       pos=pos_pick)
            except KeyError:
                title = title_tpl
                body = body_tpl

            day_offset = h(f'r4-{sport_slug}-date-{i}', 60)
            article_date = date(2024, 2, 10) + timedelta(days=day_offset)
            slug = f'{slugify(title)}-r4-{sport_slug}-{i:03d}'
            if slug in existing_slugs:
                slug = f'{slug}-{next_id}'
            existing_slugs.add(slug)

            tags = json.dumps([sport_slug.upper(), team_name, star_name,
                               'R4', 'Beat'])
            is_headline = 1 if (i % headline_every == 0) else 0
            is_featured = 1 if (i % (headline_every * 4) == 0) else 0
            created_at = (
                f'{article_date.isoformat()} '
                f'{10 + (i % 10):02d}:{(i*11) % 60:02d}:'
                f'{(i*17) % 60:02d}.000000')
            published_label = article_date.strftime('%B %-d, %Y')

            rows_to_insert.append((
                next_id, sport_slug, title, slug, '', body,
                article_authors(i),
                f'/static/images/espn/articles/{sport_slug}/{next_id}.jpg',
                tags, is_headline, is_featured, created_at, published_label,
            ))
            next_id += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, body, "
        "author, image, tags, is_headline, is_featured, created_at, "
        "published_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows_to_insert)
    return len(rows_to_insert)


# ─── 5. Betting odds (cover older games too) ─────────────────────────────────

def make_betting_odds(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM betting_odds") or 0) + 1
    # Pull games that don't yet have odds attached
    existing_gids = {r[0] for r in
                     cur.execute("SELECT game_id FROM betting_odds").fetchall()}
    candidates = cur.execute(
        "SELECT id, sport_slug, status FROM games "
        "WHERE date >= '2022-09-01' AND date <= '2024-04-09' "
        "ORDER BY date DESC, id DESC").fetchall()
    rows = []
    sportsbooks = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars']
    total_ranges = {'nba': (200, 240), 'nfl': (38, 54),
                    'mlb': (7.0, 11.5), 'nhl': (5.5, 7.0),
                    'soccer': (2.0, 3.5)}
    odds_id = next_id
    target = 400
    inserted = 0
    for gid, sport_slug, status in candidates:
        if inserted >= target:
            break
        if gid in existing_gids:
            continue
        key = f'r4-odds-{gid}'
        fav_home = (h(f'{key}-fav', 2) == 0)
        spread = round(hf(f'{key}-sp', 1.5, 11.5) * 2) / 2
        spread_disp = f'-{spread}' if spread else 'PK'
        ml_fav = -(h(f'{key}-mlf', 280, 110))
        ml_dog = h(f'{key}-mld', 320, 100)
        lo, hi = total_ranges.get(sport_slug, (40, 50))
        total = round(hf(f'{key}-tot', lo, hi) * 2) / 2
        rows.append((
            odds_id, gid, sport_slug,
            ml_fav if fav_home else ml_dog,
            ml_dog if fav_home else ml_fav,
            spread_disp, spread, total, -110, -110,
            'Opened 24h before tip',
            'closed' if status == 'final' else 'open',
            sportsbooks[odds_id % len(sportsbooks)],
        ))
        odds_id += 1
        inserted += 1
    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, "
        "home_moneyline, away_moneyline, spread_favorite, spread_line, "
        "total, over_odds, under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return inserted


# ─── 6. Awards (more historical seasons) ─────────────────────────────────────

R4_AWARDS = {
    'nba': [
        ('Most Valuable Player', 'mvp', '2021-22'),
        ('Defensive Player of the Year', 'dpoy', '2021-22'),
        ('Rookie of the Year', 'roy', '2021-22'),
        ('Most Valuable Player', 'mvp', '2020-21'),
        ('Defensive Player of the Year', 'dpoy', '2020-21'),
        ('Sixth Man of the Year', 'sixth-man', '2021-22'),
        ('Most Improved Player', 'mip', '2022-23'),
        ('All-NBA First Team', 'all-nba-1st', '2023-24'),
        ('All-Defensive First Team', 'all-def-1st', '2023-24'),
        ('Finals MVP', 'finals-mvp', '2022-23'),
        ('Clutch Player of the Year', 'cpoy', '2023-24'),
        ('Most Valuable Player', 'mvp', '2019-20'),
        ('Finals MVP', 'finals-mvp', '2021-22'),
        ('Finals MVP', 'finals-mvp', '2020-21'),
    ],
    'nfl': [
        ('Most Valuable Player', 'mvp', '2021'),
        ('Offensive Player of the Year', 'opoy', '2021'),
        ('Defensive Player of the Year', 'dpoy', '2021'),
        ('Most Valuable Player', 'mvp', '2020'),
        ('Walter Payton Man of the Year', 'wpmoy', '2023'),
        ('Super Bowl MVP', 'sb-mvp', '2023'),
        ('Super Bowl MVP', 'sb-mvp', '2022'),
        ('Rookie of the Year', 'roy', '2021'),
        ('Most Valuable Player', 'mvp', '2019'),
        ('Super Bowl MVP', 'sb-mvp', '2021'),
        ('Coach of the Year', 'coach', '2021'),
    ],
    'mlb': [
        ('AL Most Valuable Player', 'al-mvp', '2022'),
        ('NL Most Valuable Player', 'nl-mvp', '2022'),
        ('AL Cy Young', 'al-cy', '2022'),
        ('NL Cy Young', 'nl-cy', '2022'),
        ('World Series MVP', 'ws-mvp', '2023'),
        ('World Series MVP', 'ws-mvp', '2022'),
        ('Silver Slugger', 'silver-slugger', '2023'),
        ('Gold Glove', 'gold-glove', '2023'),
        ('AL Most Valuable Player', 'al-mvp', '2021'),
        ('NL Most Valuable Player', 'nl-mvp', '2021'),
        ('Manager of the Year', 'moy', '2023'),
    ],
    'nhl': [
        ('Hart Trophy', 'hart', '2021-22'),
        ('Norris Trophy', 'norris', '2022-23'),
        ('Conn Smythe Trophy', 'conn-smythe', '2022-23'),
        ('Calder Trophy', 'calder', '2022-23'),
        ('Ted Lindsay Award', 'lindsay', '2023-24'),
        ('William Jennings Trophy', 'jennings', '2023-24'),
        ('Hart Trophy', 'hart', '2020-21'),
        ('Vezina Trophy', 'vezina', '2021-22'),
        ('Selke Trophy', 'selke', '2021-22'),
    ],
    'soccer': [
        ("Ballon d'Or", 'ballon-dor', '2022'),
        ('FIFA Mens Best', 'fifa-best', '2022'),
        ('Premier League Player of the Season', 'pl-pos', '2022-23'),
        ('Champions League Top Scorer', 'ucl-top', '2022-23'),
        ('Premier League Golden Boot', 'pl-gb', '2022-23'),
        ("Ballon d'Or", 'ballon-dor', '2021'),
        ('Champions League Top Scorer', 'ucl-top', '2021-22'),
        ('Premier League Player of the Season', 'pl-pos', '2021-22'),
    ],
    'ncaam': [
        ('Naismith Player of the Year', 'naismith', '2023-24'),
        ('Wooden Award', 'wooden', '2023-24'),
        ('Naismith Coach of the Year', 'naismith-coach', '2023-24'),
        ('Wooden Award', 'wooden', '2022-23'),
        ('Naismith Player of the Year', 'naismith', '2022-23'),
        ('Wooden Award', 'wooden', '2021-22'),
        ('AP National Player of the Year', 'ap-poy', '2023-24'),
    ],
    'ncaaw': [
        ('Naismith Player of the Year', 'naismith-w', '2023-24'),
        ('Wooden Award', 'wooden-w', '2023-24'),
        ('Naismith Coach of the Year', 'naismith-coach-w', '2023-24'),
        ('Wade Trophy', 'wade', '2023-24'),
        ('AP National Player of the Year', 'ap-poy-w', '2023-24'),
    ],
    'ncaaf': [
        ('Heisman Trophy', 'heisman', '2023'),
        ('Heisman Trophy', 'heisman', '2022'),
        ('Heisman Trophy', 'heisman', '2021'),
        ('Walter Camp Award', 'walter-camp', '2023'),
        ('Maxwell Award', 'maxwell', '2023'),
        ('Doak Walker Award', 'doak-walker', '2023'),
        ('Davey O\'Brien Award', 'davey-obrien', '2023'),
    ],
}


def make_awards(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM awards") or 0) + 1
    rows = []
    aid = next_id
    for sport_slug, awards in R4_AWARDS.items():
        players = cur.execute(
            "SELECT id, name, team_id FROM players WHERE sport_slug=? "
            "ORDER BY id", (sport_slug,)).fetchall()
        # For college sports without dedicated players, fall back to recruits
        # or a synthetic name pool so awards still seed.
        if not players and sport_slug in ('ncaam', 'ncaaw', 'ncaaf'):
            recruits = cur.execute(
                "SELECT id, name FROM recruits WHERE sport_slug=? "
                "ORDER BY id", (sport_slug,)).fetchall()
            players = [(r[0], r[1], None) for r in recruits]
        if not players:
            # Final fallback: synthetic 8-name pool keyed off sport so awards
            # still land for sports with neither players nor recruits.
            stubs = [f'{sport_slug.upper()} Star {i}' for i in range(1, 9)]
            players = [(0, name, None) for name in stubs]
        for award_name, award_slug, season in awards:
            key = f'r4-award-{sport_slug}-{award_slug}-{season}'
            pidx = h(f'{key}-winner', len(players))
            wpid, wname, wtid = players[pidx]
            f_idxs = []
            attempt = 0
            while len(f_idxs) < 4 and attempt < 30:
                cand = h(f'{key}-fin-{attempt}', len(players))
                if cand != pidx and cand not in f_idxs:
                    f_idxs.append(cand)
                attempt += 1
            finalists = [{'player_id': players[i][0],
                          'name': players[i][1],
                          'votes_share': round(hf(f'{key}-vs-{i}', 0.04, 0.22), 3)}
                         for i in f_idxs]
            voting_share = round(hf(f'{key}-ws', 0.42, 0.78), 3)
            year_marker = season.split('-')[-1] if '-' in season else season
            announced = f'20{year_marker[-2:]}-06-25' if len(year_marker) >= 2 else '2023-06-20'
            rows.append((
                aid, sport_slug, season, award_name, award_slug,
                wpid, wtid, json.dumps(finalists), voting_share, announced))
            aid += 1
    cur.executemany(
        "INSERT INTO awards (id, sport_slug, season, award_name, award_slug, "
        "winner_player_id, winner_team_id, finalists, voting_share, "
        "announced_date) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 7. Draft picks (2022 NFL, 2025 NBA mock, 2023 NBA actual) ───────────────

NFL_2022_POOL = [
    ('Travon Walker', 'EDGE', 'Georgia', 'USA', "6'5", 272),
    ('Aidan Hutchinson', 'EDGE', 'Michigan', 'USA', "6'7", 260),
    ('Derek Stingley Jr.', 'CB', 'LSU', 'USA', "6'0", 190),
    ('Sauce Gardner', 'CB', 'Cincinnati', 'USA', "6'3", 200),
    ('Kayvon Thibodeaux', 'EDGE', 'Oregon', 'USA', "6'4", 254),
    ('Ikem Ekwonu', 'OT', 'NC State', 'USA', "6'4", 310),
    ('Evan Neal', 'OT', 'Alabama', 'USA', "6'7", 337),
    ('Garrett Wilson', 'WR', 'Ohio State', 'USA', "6'0", 192),
    ('Charles Cross', 'OT', 'Mississippi State', 'USA', "6'5", 307),
    ('Drake London', 'WR', 'USC', 'USA', "6'4", 219),
    ('Jameson Williams', 'WR', 'Alabama', 'USA', "6'1", 179),
    ('Trevor Penning', 'OT', 'Northern Iowa', 'USA', "6'7", 325),
    ('Jordan Davis', 'DT', 'Georgia', 'USA', "6'6", 341),
    ('Jahan Dotson', 'WR', 'Penn State', 'USA', "5'11", 178),
    ('Devin Lloyd', 'LB', 'Utah', 'USA', "6'3", 237),
    ('Treylon Burks', 'WR', 'Arkansas', 'USA', "6'2", 225),
    ('Trent McDuffie', 'CB', 'Washington', 'USA', "5'11", 195),
    ('Quay Walker', 'LB', 'Georgia', 'USA', "6'4", 241),
    ('Devonte Wyatt', 'DT', 'Georgia', 'USA', "6'3", 304),
    ('Kenny Pickett', 'QB', 'Pittsburgh', 'USA', "6'3", 217),
]

NBA_2023_POOL = [
    ('Victor Wembanyama', 'C', 'Mets 92', 'France', "7'3", 209),
    ('Brandon Miller', 'SF', 'Alabama', 'USA', "6'9", 200),
    ('Scoot Henderson', 'PG', 'G League Ignite', 'USA', "6'2", 195),
    ('Amen Thompson', 'PG', 'OTE', 'USA', "6'7", 199),
    ('Ausar Thompson', 'SF', 'OTE', 'USA', "6'7", 217),
    ('Jarace Walker', 'PF', 'Houston', 'USA', "6'8", 240),
    ('Anthony Black', 'PG', 'Arkansas', 'USA', "6'7", 200),
    ('Bilal Coulibaly', 'SF', 'Metropolitans 92', 'France', "6'8", 196),
    ('Taylor Hendricks', 'PF', 'UCF', 'USA', "6'9", 210),
    ('Cason Wallace', 'PG', 'Kentucky', 'USA', "6'4", 193),
    ('Jett Howard', 'SG', 'Michigan', 'USA', "6'8", 215),
    ('Dereck Lively II', 'C', 'Duke', 'USA', "7'1", 230),
    ('Gradey Dick', 'SG', 'Kansas', 'USA', "6'8", 205),
    ('Jordan Hawkins', 'SG', 'UConn', 'USA', "6'5", 188),
    ('Kobe Bufkin', 'SG', 'Michigan', 'USA', "6'5", 195),
    ('Keyonte George', 'SG', 'Baylor', 'USA', "6'4", 206),
    ('Jalen Hood-Schifino', 'SG', 'Indiana', 'USA', "6'6", 213),
    ('Brandin Podziemski', 'SG', 'Santa Clara', 'USA', "6'5", 205),
    ('Dariq Whitehead', 'SF', 'Duke', 'USA', "6'7", 220),
    ('Cam Whitmore', 'SF', 'Villanova', 'USA', "6'7", 232),
]

NBA_2025_MOCK_POOL = [
    ('Cooper Flagg', 'SF', 'Duke', 'USA', "6'9", 205),
    ('Ace Bailey', 'SF', 'Rutgers', 'USA', "6'10", 200),
    ('Dylan Harper', 'PG', 'Rutgers', 'USA', "6'6", 215),
    ('VJ Edgecombe', 'SG', 'Baylor', 'Bahamas', "6'5", 180),
    ('Tre Johnson', 'SG', 'Texas', 'USA', "6'6", 190),
    ('Jeremiah Fears', 'PG', 'Oklahoma', 'USA', "6'4", 180),
    ('Khaman Maluach', 'C', 'Duke', 'South Sudan', "7'2", 250),
    ('Kasparas Jakucionis', 'PG', 'Illinois', 'Lithuania', "6'6", 200),
    ('Egor Demin', 'PG', 'BYU', 'Russia', "6'9", 200),
    ('Asa Newell', 'PF', 'Georgia', 'USA', "6'11", 220),
    ('Boogie Fland', 'PG', 'Arkansas', 'USA', "6'2", 175),
    ('Liam McNeeley', 'SF', 'UConn', 'USA', "6'7", 215),
    ('Derik Queen', 'C', 'Maryland', 'USA', "6'10", 246),
    ('Carter Bryant', 'SF', 'Arizona', 'USA', "6'8", 220),
    ('Ben Saraf', 'PG', 'Ratiopharm Ulm', 'Israel', "6'5", 200),
    ('Noa Essengue', 'PF', 'Ratiopharm Ulm', 'France', "6'10", 200),
    ('Collin Murray-Boyles', 'PF', 'South Carolina', 'USA', "6'7", 245),
    ('Nique Clifford', 'SG', 'Colorado State', 'USA', "6'6", 200),
    ('Will Riley', 'SF', 'Illinois', 'Canada', "6'8", 180),
    ('Drake Powell', 'SG', 'UNC', 'USA', "6'6", 195),
]


def make_draft_picks(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM draft_picks") or 0) + 1
    rows = []
    pid = next_id

    nfl_teams = cur.execute(
        "SELECT id, full_name FROM teams WHERE sport_slug='nfl' "
        "ORDER BY id").fetchall()
    nba_teams = cur.execute(
        "SELECT id, full_name FROM teams WHERE sport_slug='nba' "
        "ORDER BY id").fetchall()

    # 2022 NFL Draft actual top 32 + 2nd round 32
    for round_n, count in [(1, 32), (2, 32)]:
        for i in range(count):
            overall = (round_n - 1) * 32 + i + 1
            t_idx = h(f'r4-nfl-2022-pick-{overall}', len(nfl_teams))
            tid, _tname = nfl_teams[t_idx]
            p_idx = h(f'r4-nfl-2022-pl-{overall}', len(NFL_2022_POOL))
            pname, pos, school, country, height, weight = NFL_2022_POOL[p_idx]
            grade = round(hf(f'r4-nfl-2022-gr-{overall}', 6.5, 9.0), 2)
            notes = f'{pname}: 2022 NFL Draft pick from {school}.'
            rows.append((
                pid, 'nfl', '2022', round_n, i + 1, overall, tid,
                pname, pos, school, country, height, weight,
                grade, notes, 0))
            pid += 1

    # 2023 NBA Draft actual (top 30) + round 2 (30)
    for round_n, count in [(1, 30), (2, 30)]:
        for i in range(count):
            overall = (round_n - 1) * 30 + i + 1
            t_idx = h(f'r4-nba-2023-pick-{overall}', len(nba_teams))
            tid, _tname = nba_teams[t_idx]
            p_idx = h(f'r4-nba-2023-pl-{overall}', len(NBA_2023_POOL))
            pname, pos, school, country, height, weight = NBA_2023_POOL[p_idx]
            grade = round(hf(f'r4-nba-2023-gr-{overall}', 6.0, 9.3), 2)
            notes = f'{pname}: 2023 NBA Draft pick from {school}.'
            rows.append((
                pid, 'nba', '2023', round_n, i + 1, overall, tid,
                pname, pos, school, country, height, weight,
                grade, notes, 0))
            pid += 1

    # 2025 NBA Mock Draft (top 30, round 1)
    for i in range(30):
        overall = i + 1
        t_idx = h(f'r4-nba-2025-pick-{overall}', len(nba_teams))
        tid, _tname = nba_teams[t_idx]
        p_idx = h(f'r4-nba-2025-pl-{overall}', len(NBA_2025_MOCK_POOL))
        pname, pos, school, country, height, weight = NBA_2025_MOCK_POOL[p_idx]
        grade = round(hf(f'r4-nba-2025-gr-{overall}', 7.0, 9.7), 2)
        notes = f'{pname}: 2025 NBA mock from {school}, projected top-30 pick.'
        rows.append((
            pid, 'nba', '2025', 1, overall, overall, tid,
            pname, pos, school, country, height, weight,
            grade, notes, 1))
        pid += 1

    # 2024 NFL Draft round 3 mock (32 picks)
    NFL_R3_POOL = [
        ('Christian Haynes', 'OG', 'UConn', 'USA', "6'2", 318),
        ('Cooper Beebe', 'OG', 'Kansas State', 'USA', "6'3", 322),
        ('Maason Smith', 'DT', 'LSU', 'USA', "6'6", 306),
        ('Edgerrin Cooper', 'LB', 'Texas A&M', 'USA', "6'2", 230),
        ('Jonathon Brooks', 'RB', 'Texas', 'USA', "6'0", 216),
        ('Trey Benson', 'RB', 'Florida State', 'USA', "6'0", 216),
        ('Junior Colson', 'LB', 'Michigan', 'USA', "6'3", 238),
        ('Khyree Jackson', 'CB', 'Oregon', 'USA', "6'4", 194),
    ]
    for i in range(32):
        overall = 64 + i + 1
        t_idx = h(f'r4-nfl-2024-r3-pick-{overall}', len(nfl_teams))
        tid, _tname = nfl_teams[t_idx]
        p_idx = h(f'r4-nfl-2024-r3-pl-{overall}', len(NFL_R3_POOL))
        pname, pos, school, country, height, weight = NFL_R3_POOL[p_idx]
        grade = round(hf(f'r4-nfl-2024-r3-gr-{overall}', 5.5, 7.0), 2)
        notes = f'{pname}: 2024 NFL mock 3rd-round pick from {school}.'
        rows.append((
            pid, 'nfl', '2024', 3, i + 1, overall, tid,
            pname, pos, school, country, height, weight,
            grade, notes, 1))
        pid += 1

    # 2022 NBA Draft actual (round 1 30 + round 2 28)
    NBA_2022_POOL = [
        ('Paolo Banchero', 'PF', 'Duke', 'USA', "6'10", 250),
        ('Chet Holmgren', 'C', 'Gonzaga', 'USA', "7'1", 195),
        ('Jabari Smith Jr.', 'PF', 'Auburn', 'USA', "6'10", 220),
        ('Keegan Murray', 'PF', 'Iowa', 'USA', "6'8", 225),
        ('Jaden Ivey', 'PG', 'Purdue', 'USA', "6'4", 195),
        ('Bennedict Mathurin', 'SG', 'Arizona', 'Canada', "6'6", 210),
        ('Shaedon Sharpe', 'SG', 'Kentucky', 'Canada', "6'6", 200),
        ('Dyson Daniels', 'SG', 'G League Ignite', 'Australia', "6'8", 199),
        ('Jeremy Sochan', 'PF', 'Baylor', 'Poland', "6'9", 230),
        ('Johnny Davis', 'SG', 'Wisconsin', 'USA', "6'5", 196),
        ('Ousmane Dieng', 'SF', 'NZ Breakers', 'France', "6'10", 220),
        ('Jalen Williams', 'SF', 'Santa Clara', 'USA', "6'6", 211),
        ('Jalen Duren', 'C', 'Memphis', 'USA', "6'10", 250),
        ('AJ Griffin', 'SF', 'Duke', 'USA', "6'6", 222),
        ('Mark Williams', 'C', 'Duke', 'USA', "7'2", 240),
        ('Tari Eason', 'PF', 'LSU', 'USA', "6'8", 215),
        ('Walker Kessler', 'C', 'Auburn', 'USA', "7'1", 245),
        ('Ochai Agbaji', 'SG', 'Kansas', 'USA', "6'5", 217),
        ('MarJon Beauchamp', 'SG', 'G League Ignite', 'USA', "6'7", 200),
        ('Malaki Branham', 'SG', 'Ohio State', 'USA', "6'5", 200),
    ]
    for round_n, count in [(1, 30), (2, 28)]:
        for i in range(count):
            overall = (round_n - 1) * 30 + i + 1
            t_idx = h(f'r4-nba-2022-pick-{overall}', len(nba_teams))
            tid, _tname = nba_teams[t_idx]
            p_idx = h(f'r4-nba-2022-pl-{overall}', len(NBA_2022_POOL))
            pname, pos, school, country, height, weight = NBA_2022_POOL[p_idx]
            grade = round(hf(f'r4-nba-2022-gr-{overall}', 6.0, 9.2), 2)
            notes = f'{pname}: 2022 NBA Draft pick from {school}.'
            rows.append((
                pid, 'nba', '2022', round_n, i + 1, overall, tid,
                pname, pos, school, country, height, weight,
                grade, notes, 0))
            pid += 1

    # 2025 NFL Mock Draft (round 1, 32 picks)
    NFL_2025_MOCK_POOL = [
        ('Travis Hunter', 'WR/CB', 'Colorado', 'USA', "6'1", 185),
        ('Cam Ward', 'QB', 'Miami', 'USA', "6'2", 220),
        ('Abdul Carter', 'EDGE', 'Penn State', 'USA', "6'3", 252),
        ('Mason Graham', 'DT', 'Michigan', 'USA', "6'3", 320),
        ('Will Campbell', 'OT', 'LSU', 'USA', "6'6", 320),
        ('Tetairoa McMillan', 'WR', 'Arizona', 'USA', "6'5", 212),
        ('Shedeur Sanders', 'QB', 'Colorado', 'USA', "6'2", 215),
        ('Mike Green', 'EDGE', 'Marshall', 'USA', "6'4", 251),
        ('Ashton Jeanty', 'RB', 'Boise State', 'USA', "5'9", 215),
        ('Jihaad Campbell', 'LB', 'Alabama', 'USA', "6'3", 235),
        ('Walter Nolen', 'DT', 'Ole Miss', 'USA', "6'4", 305),
        ('Jalon Walker', 'LB', 'Georgia', 'USA', "6'2", 240),
        ('Kelvin Banks Jr.', 'OT', 'Texas', 'USA', "6'4", 320),
        ('Tyler Booker', 'OG', 'Alabama', 'USA', "6'5", 325),
        ('Will Johnson', 'CB', 'Michigan', 'USA', "6'2", 202),
        ('Malaki Starks', 'S', 'Georgia', 'USA', "6'1", 205),
        ('Nick Emmanwori', 'S', 'South Carolina', 'USA', "6'3", 227),
        ('Matthew Golden', 'WR', 'Texas', 'USA', "5'11", 195),
        ('Shemar Stewart', 'EDGE', 'Texas A&M', 'USA', "6'5", 290),
        ('Donovan Jackson', 'OG', 'Ohio State', 'USA', "6'4", 320),
    ]
    for i in range(32):
        overall = i + 1
        t_idx = h(f'r4-nfl-2025-pick-{overall}', len(nfl_teams))
        tid, _tname = nfl_teams[t_idx]
        p_idx = h(f'r4-nfl-2025-pl-{overall}', len(NFL_2025_MOCK_POOL))
        pname, pos, school, country, height, weight = NFL_2025_MOCK_POOL[p_idx]
        grade = round(hf(f'r4-nfl-2025-gr-{overall}', 7.2, 9.7), 2)
        notes = f'{pname}: 2025 NFL mock pick from {school}.'
        rows.append((
            pid, 'nfl', '2025', 1, overall, overall, tid,
            pname, pos, school, country, height, weight,
            grade, notes, 1))
        pid += 1

    cur.executemany(
        "INSERT INTO draft_picks (id, sport_slug, season, round, pick, "
        "overall_pick, team_id, player_name, position, school, country, "
        "height, weight, scout_grade, notes, is_mock) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 8. Podcasts ─────────────────────────────────────────────────────────────

R4_PODCAST_SEED = [
    ('NFL Matchup', 'nfl-matchup', 'Greg Cosell, Sal Paolantonio', 'nfl',
     'Weekly NFL film breakdowns.', 320, 'Wild Card film notes',
     '2024-04-08', 28),
    ('Get Up Podcast', 'get-up-podcast', 'Mike Greenberg', 'nba',
     'Audio cut of ESPN morning show Get Up.', 950, 'NBA MVP debate',
     '2024-04-09', 70),
    ('The Athletic Football Show', 'athletic-football-show', 'Andrew Marchand', 'nfl',
     'Behind the scenes of NFL coverage.', 220, 'Draft media notes',
     '2024-04-09', 55),
    ('Dynasty Trade Calculator', 'dynasty-trade-calculator', 'Adam Schefter, Field Yates', 'fantasy',
     'Weekly dynasty trade analysis.', 180, 'Top rookie trade targets',
     '2024-04-07', 50),
    ('Cousin Sal Talks Gambling', 'cousin-sal-gambling', 'Sal Iacono', 'nba',
     'Weekly NFL/NBA gambling picks and parlays.', 410, 'Best bets for the slate',
     '2024-04-08', 65),
    ('March Madness Daily', 'march-madness-daily', 'Andy Katz', 'ncaam',
     'Tournament season daily updates.', 60, 'Bracket reflections',
     '2024-04-08', 35),
    ('Pat McAfee Show', 'pat-mcafee-show', 'Pat McAfee', 'nfl',
     'Daily NFL show with guests.', 1100, 'Draft live talk',
     '2024-04-09', 180),
    ('Mina Kimes Show', 'mina-kimes-show', 'Mina Kimes', 'nfl',
     'NFL film breakdowns with Mina Kimes.', 240, 'Mock Draft 6.0',
     '2024-04-09', 55),
    ('Around the Horn', 'around-the-horn-podcast', 'Tony Reali', 'nba',
     'Audio cut of ESPN debate show Around the Horn.', 920, 'NBA panels react',
     '2024-04-09', 30),
    ('Marty & McGee', 'marty-and-mcgee', 'Marty Smith, Ryan McGee', 'ncaaf',
     'College football and southern culture.', 280, 'Spring sweep',
     '2024-04-05', 65),
    ('The Buck Show', 'the-buck-show', 'Joe Buck', 'mlb',
     'Baseball with Joe Buck.', 95, 'Opening week reactions',
     '2024-04-04', 50),
    ('Beyond the Win Column', 'beyond-the-win-column', 'Stephen A. Smith', 'nba',
     'Long-form takes from Stephen A.', 60, 'Eastern Conference seeding',
     '2024-04-08', 80),
    ('SVP & Russillo', 'svp-and-russillo', 'Scott Van Pelt, Ryen Russillo', 'nba',
     'Late-night NBA & NFL talk.', 380, 'Big picture playoff outlook',
     '2024-04-09', 60),
    ('Tennis Channel Inside-Out', 'tennis-channel-io', 'Brett Haber', 'tennis',
     'Tennis news, results, draws.', 140, 'Madrid Open week 1',
     '2024-04-07', 40),
    ('Caddie Tales', 'caddie-tales', 'Geoff Shackelford', 'golf',
     'Inside the bag with PGA caddies.', 75, 'Masters wrap',
     '2024-04-08', 45),
    ('UFC Unfiltered', 'ufc-unfiltered', 'Jim Norton', 'mma',
     'Weekly UFC card preview.', 230, 'Co-main event breakdown',
     '2024-04-08', 70),
    ('Soccer Cooligans', 'soccer-cooligans', 'Christian Polanco', 'soccer',
     'Casual soccer fan podcast.', 165, 'UCL quarters reactions',
     '2024-04-08', 55),
    ('Football 2 the MAX', 'football-2-the-max', 'Joe Iannello', 'nfl',
     'Daily NFL roundup.', 600, 'Pre-Draft buzz',
     '2024-04-09', 30),
    ('Cubs Talk', 'cubs-talk', 'Tony Andracki', 'mlb',
     'Chicago Cubs deep dive.', 110, 'Early-season takeaways',
     '2024-04-07', 35),
    ('Hot Stove Hockey', 'hot-stove-hockey', 'Kevin Weekes', 'nhl',
     'NHL rumors and trade chatter.', 95, 'Trade deadline echo',
     '2024-04-07', 50),
    ('Hoop Collective', 'hoop-collective', 'Brian Windhorst, Tim Bontemps', 'nba',
     'NBA roundtable with reporters.', 320, 'East-West playoff bracket',
     '2024-04-09', 65),
    ('Front Office Insider', 'front-office-insider', 'Bobby Marks', 'nba',
     'NBA front-office insight.', 165, 'Apron and tax-line decisions',
     '2024-04-08', 45),
    ('On the Mike', 'on-the-mike', 'Mike Reiss', 'nfl',
     'Patriots beat coverage.', 240, 'Patriots draft strategy',
     '2024-04-08', 30),
    ('Halftime Adjustments', 'halftime-adjustments', 'Cole Cubelic', 'ncaaf',
     'College football X-and-O breakdowns.', 145, 'Spring scrimmage notes',
     '2024-04-06', 50),
    ('Pucks & Pints', 'pucks-and-pints', 'Linda Cohn', 'nhl',
     'Casual NHL talk.', 180, 'Goalie carousel',
     '2024-04-08', 45),
    ('Buster Olney on Baseball', 'buster-on-baseball', 'Buster Olney', 'mlb',
     'Daily MLB reaction column.', 920, 'AL East hot start',
     '2024-04-09', 40),
    ('Fantasy Football Now', 'fantasy-football-now', 'Field Yates', 'fantasy',
     'In-season Sunday morning fantasy.', 280, 'Mock-draft strategies',
     '2024-04-09', 55),
    ('SportsCenter All Night', 'sportscenter-all-night', 'Scott Van Pelt', 'nba',
     'After-dark SportsCenter audio.', 320, 'One Big Thing rundown',
     '2024-04-09', 70),
    ('Eye on the Champion', 'eye-on-the-champion', 'Greg Wyshynski', 'nhl',
     'Stanley Cup chase coverage.', 90, 'Top contenders ranked',
     '2024-04-08', 55),
    ('Body Bag Hour', 'body-bag-hour', 'Brett Okamoto', 'mma',
     'UFC fight breakdowns.', 200, 'Title-fight predictions',
     '2024-04-08', 60),
    ('After the Whistle', 'after-the-whistle', 'Sam Borden', 'soccer',
     'Long-form soccer reporting.', 65, 'European super-club model',
     '2024-04-07', 50),
    ('Press Pass', 'press-pass-podcast', 'Marty Smith', 'ncaaf',
     'CFB road stories.', 85, 'Spring practice tour',
     '2024-04-06', 60),
    ('Inside the Lines', 'inside-the-lines', 'Joe Fortenbaugh', 'nba',
     'Daily betting picks.', 410, 'Tonight\'s slate',
     '2024-04-09', 35),
    ('Bracketology', 'bracketology-podcast', 'Joe Lunardi', 'ncaam',
     'NCAA tournament projection podcast.', 60, 'Final bracket recap',
     '2024-04-08', 30),
    ('ESPN Daily', 'espn-daily', 'Pablo Torre', 'nba',
     'Daily story-driven podcast.', 980, 'Sports stories of the week',
     '2024-04-09', 30),
    ('NCAAW Court Talk', 'ncaaw-court-talk', 'Charlie Creme', 'ncaaw',
     'Women\'s college hoops show.', 75, 'Final Four wrap-up',
     '2024-04-08', 45),
    ('Sip and Putt', 'sip-and-putt', 'Michael Collins', 'golf',
     'Tour life with caddies and players.', 110, 'Masters tee-time gossip',
     '2024-04-07', 50),
    ('Tip Off Tonight', 'tip-off-tonight', 'Tim Bontemps', 'nba',
     'NBA nightly preview.', 230, 'Tonight\'s east-west marquee',
     '2024-04-09', 30),
    ('Locked On NBA', 'locked-on-nba', 'David Locke', 'nba',
     'Network of NBA team-specific podcasts.', 1200, 'East playoff field',
     '2024-04-09', 25),
    ('Locked On NFL', 'locked-on-nfl', 'Andy Herman', 'nfl',
     'Network of NFL team-specific podcasts.', 1300, 'Pre-draft buzz',
     '2024-04-09', 25),
]


def make_podcasts(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM podcasts") or 0) + 1
    rows = []
    for i, (title, slug, host, sport_slug, description, eps,
            latest_title, latest_date, dur) in enumerate(R4_PODCAST_SEED):
        rows.append((next_id + i, title, slug, host, sport_slug, description,
                     eps, latest_title, latest_date, dur))
    cur.executemany(
        "INSERT INTO podcasts (id, title, slug, host, sport_slug, "
        "description, episode_count, latest_episode_title, latest_episode_date, "
        "duration_minutes) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 9. Play-by-play (new table) ─────────────────────────────────────────────

NBA_PBP_EVENTS = [
    ('made_3pt', '{actor} makes a 3-pointer from the wing'),
    ('made_2pt', '{actor} makes a 2-point jumper'),
    ('made_layup', '{actor} drives and finishes at the rim'),
    ('made_dunk', '{actor} throws down a slam dunk'),
    ('missed_3pt', '{actor} misses a 3-point attempt'),
    ('missed_layup', '{actor} misses the layup'),
    ('off_rebound', '{actor} grabs the offensive rebound'),
    ('def_rebound', '{actor} pulls down the defensive rebound'),
    ('assist', '{actor} dishes the assist on the made bucket'),
    ('steal', '{actor} steals the ball at midcourt'),
    ('block', '{actor} blocks the shot at the rim'),
    ('foul', 'Personal foul called on {actor}'),
    ('ft_made', '{actor} makes both free throws'),
    ('turnover', '{actor} turns it over on a bad pass'),
    ('timeout', 'Timeout called'),
]

NHL_PBP_EVENTS = [
    ('goal', '{actor} scores'),
    ('shot', '{actor} shoots on goal, saved by the netminder'),
    ('hit', '{actor} delivers a hit along the boards'),
    ('takeaway', '{actor} forces the turnover'),
    ('giveaway', '{actor} gives the puck up at the blue line'),
    ('penalty', 'Penalty assessed on {actor} for tripping'),
    ('faceoff_won', '{actor} wins the faceoff'),
    ('save', 'Goaltender saves the shot from {actor}'),
    ('power_play', 'Power-play opportunity begins'),
    ('period_end', 'Period ends'),
]

MLB_PBP_EVENTS = [
    ('single', '{actor} singles to right'),
    ('double', '{actor} doubles down the line'),
    ('triple', '{actor} legs out a triple'),
    ('homer', '{actor} hits a home run'),
    ('strikeout', '{actor} strikes out swinging'),
    ('walk', '{actor} walks'),
    ('groundout', '{actor} grounds out to short'),
    ('flyout', '{actor} flies out to deep center'),
    ('stolen_base', '{actor} steals second base'),
    ('pickoff', 'Pickoff attempt at first base'),
]


def make_play_by_play(cur):
    """Generate ~40 events for ~30 marquee games per major sport."""
    next_id = 1  # play_by_play is a new table
    rows = []

    def pick_games(sport, n):
        return cur.execute(
            "SELECT id, sport_slug, home_team_id, away_team_id, "
            "       home_score, away_score "
            "FROM games WHERE sport_slug=? AND status='final' "
            "ORDER BY date DESC LIMIT ?", (sport, n)).fetchall()

    def actor_names(team_id):
        rows = cur.execute(
            "SELECT name FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 6", (team_id,)).fetchall()
        return [r[0] for r in rows] if rows else [f'Player #{team_id}']

    plan = [
        ('nba', 12, NBA_PBP_EVENTS, ['Q1', 'Q2', 'Q3', 'Q4']),
        ('nhl', 10, NHL_PBP_EVENTS, ['1st', '2nd', '3rd']),
        ('mlb', 10, MLB_PBP_EVENTS, ['T1', 'B1', 'T2', 'B2', 'T3', 'B3',
                                     'T4', 'B4', 'T5', 'B5']),
    ]
    for sport, ngames, events, periods in plan:
        games = pick_games(sport, ngames)
        for gid, sport_slug, hid, aid, fhs, fas in games:
            home_actors = actor_names(hid)
            away_actors = actor_names(aid)
            score_h = 0
            score_a = 0
            ev_count = 40 if sport != 'mlb' else 25
            for seq in range(ev_count):
                key = f'r4-pbp-{sport}-{gid}-{seq}'
                ev_idx = h(f'{key}-ev', len(events))
                ev_type, tpl = events[ev_idx]
                is_home = (h(f'{key}-side', 2) == 0)
                team_id = hid if is_home else aid
                actor_pool = home_actors if is_home else away_actors
                actor = actor_pool[h(f'{key}-act', len(actor_pool))]
                desc = tpl.format(actor=actor)
                # Score increments
                if ev_type in ('made_3pt',):
                    if is_home:
                        score_h += 3
                    else:
                        score_a += 3
                elif ev_type in ('made_2pt', 'made_layup', 'made_dunk'):
                    if is_home:
                        score_h += 2
                    else:
                        score_a += 2
                elif ev_type == 'ft_made':
                    if is_home:
                        score_h += 2
                    else:
                        score_a += 2
                elif ev_type == 'goal':
                    if is_home:
                        score_h += 1
                    else:
                        score_a += 1
                elif ev_type in ('single', 'double', 'triple'):
                    pass  # runner doesn't immediately score
                elif ev_type == 'homer':
                    if is_home:
                        score_h += 1
                    else:
                        score_a += 1
                period = periods[seq % len(periods)]
                # Mock clock: count down
                minute = 11 - (seq % 12)
                second = (seq * 7) % 60
                clock = f'{minute:02d}:{second:02d}'
                rows.append((
                    next_id, gid, sport_slug, seq + 1, period, clock,
                    team_id, actor, ev_type, desc,
                    min(score_h, fhs or 999), min(score_a, fas or 999),
                ))
                next_id += 1

    cur.executemany(
        "INSERT INTO play_by_play (id, game_id, sport_slug, sequence, "
        "period, clock, team_id, actor_name, event_type, description, "
        "score_home, score_away) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 10. Watchables (ESPN+ shows / series) ───────────────────────────────────

WATCHABLES_SEED = [
    # (title, kind, sport_slug, description, is_live, duration, release, host)
    ('30 for 30: The Last Dance', 'documentary', 'nba',
     'Inside the final Bulls championship run.', 0, 600, '2020-04-19', 'ESPN Films'),
    ('30 for 30: O.J.: Made in America', 'documentary', 'nfl',
     'Five-part documentary on O.J. Simpson.', 0, 470, '2016-06-11', 'ESPN Films'),
    ('Detail with Peyton Manning', 'series', 'nfl',
     'Peyton Manning breaks down QB tape.', 0, 60, '2018-07-15', 'Peyton Manning'),
    ('Around the Horn', 'show', 'nba',
     'Live daily debate show.', 1, 30, '2002-11-04', 'Tony Reali'),
    ('Pardon the Interruption', 'show', 'nba',
     'Tony Kornheiser and Michael Wilbon debate.', 1, 30, '2001-10-22', 'Kornheiser/Wilbon'),
    ('UFC Live', 'live-event', 'mma',
     'UFC live event on ESPN+.', 1, 300, '2024-04-13', 'UFC'),
    ('La Liga: El Clasico', 'live-event', 'soccer',
     'Real Madrid vs Barcelona live coverage.', 1, 120, '2024-04-21', 'ESPN+'),
    ('NHL Power Play', 'live-event', 'nhl',
     'NHL live games on ESPN+.', 1, 180, '2024-04-12', 'ESPN+'),
    ('KayRod Cast', 'simulcast', 'nfl',
     'Kay Adams + A-Rod Monday Night alt cast.', 1, 180, '2023-09-12', 'Kay Adams'),
    ('Manningcast', 'simulcast', 'nfl',
     'Peyton & Eli Monday Night alt cast.', 1, 180, '2021-09-13', 'Peyton & Eli'),
    ('Bracketology with Joe Lunardi', 'show', 'ncaam',
     'Daily bracketology projection show.', 1, 30, '2010-01-04', 'Joe Lunardi'),
    ('Fantasy Focus Live', 'show', 'fantasy',
     'Live ESPN fantasy show.', 1, 60, '2008-09-01', 'Field Yates'),
    ('NFL Live', 'show', 'nfl',
     'Daily NFL show.', 1, 60, '2003-09-02', 'Laura Rutledge'),
    ('NBA Today', 'show', 'nba',
     'Daily NBA round-table.', 1, 60, '2022-10-01', 'Malika Andrews'),
    ('Get Up', 'show', 'nba',
     'ESPN morning debate.', 1, 180, '2018-04-02', 'Mike Greenberg'),
    ('First Take', 'show', 'nba',
     'Stephen A. Smith debate.', 1, 120, '2007-11-26', 'Stephen A. Smith'),
    ('SportsCenter', 'show', 'nba',
     'Flagship sports news.', 1, 60, '1979-09-07', 'Various'),
    ('E60', 'series', 'nfl',
     'ESPN long-form investigative series.', 0, 60, '2007-05-22', 'ESPN Films'),
    ('Outside the Lines', 'show', 'nba',
     'Investigative news.', 1, 30, '1990-04-01', 'Bob Ley'),
    ('30 for 30: The Two Bills', 'documentary', 'nfl',
     'Belichick and Parcells dual study.', 0, 110, '2018-02-01', 'ESPN Films'),
    ('30 for 30: The 85 Bears', 'documentary', 'nfl',
     'The story of the 1985 Chicago Bears.', 0, 100, '2016-02-04', 'ESPN Films'),
    ('30 for 30: Bo Knows', 'documentary', 'mlb',
     'Bo Jackson dual-sport profile.', 0, 90, '2012-10-04', 'ESPN Films'),
    ('Coach Prime', 'series', 'ncaaf',
     'Deion Sanders coaching docuseries.', 0, 45, '2022-09-09', 'Deion Sanders'),
    ('The Captain', 'documentary', 'mlb',
     'Derek Jeter career retrospective.', 0, 60, '2022-07-18', 'ESPN Films'),
    ('Last Chance U', 'series', 'ncaaf',
     'JUCO football real-life drama.', 0, 50, '2016-07-29', 'ESPN Films'),
    ('Top Rank Boxing', 'live-event', 'mma',
     'Boxing live events on ESPN+.', 1, 240, '2024-04-13', 'Top Rank'),
    ('Wimbledon All-Access', 'live-event', 'tennis',
     'Wimbledon coverage on ESPN+.', 1, 360, '2024-07-01', 'ESPN+'),
    ('US Open Tennis Live', 'live-event', 'tennis',
     'US Open live coverage.', 1, 360, '2024-08-26', 'ESPN+'),
    ('Masters Live', 'live-event', 'golf',
     'Masters live featured groups.', 1, 360, '2024-04-11', 'ESPN+'),
    ('PGA Championship Live', 'live-event', 'golf',
     'PGA Championship live featured groups.', 1, 360, '2024-05-16', 'ESPN+'),
    ('Bundesliga on ESPN+', 'live-event', 'soccer',
     'German Bundesliga live coverage.', 1, 120, '2024-04-13', 'ESPN+'),
    ('DFL Pokal', 'live-event', 'soccer',
     'DFL Pokal coverage.', 1, 120, '2024-04-12', 'ESPN+'),
    ('FA Cup', 'live-event', 'soccer',
     'FA Cup match coverage.', 1, 120, '2024-04-20', 'ESPN+'),
    ('NWSL Game of the Week', 'live-event', 'soccer',
     'NWSL live games.', 1, 100, '2024-04-13', 'ESPN+'),
    ('30 for 30: Bad Boys', 'documentary', 'nba',
     'Detroit Pistons title teams.', 0, 130, '2014-04-17', 'ESPN Films'),
    ('30 for 30: Once Brothers', 'documentary', 'nba',
     'Vlade Divac & Drazen Petrovic story.', 0, 100, '2010-10-12', 'ESPN Films'),
    ('30 for 30: June 17th, 1994', 'documentary', 'nba',
     'O.J. chase and the NBA Finals.', 0, 70, '2010-06-16', 'ESPN Films'),
    ('Top Rank Inside', 'series', 'mma',
     'Behind-the-scenes Top Rank.', 0, 30, '2021-04-01', 'ESPN+'),
    ('Stanley Cup Playoffs Live', 'live-event', 'nhl',
     'Stanley Cup Playoffs live games.', 1, 200, '2024-04-20', 'ESPN+'),
    ('NBA Playoffs Live', 'live-event', 'nba',
     'NBA Playoffs live coverage.', 1, 180, '2024-04-20', 'ESPN'),
    ('MLB Sunday Leadoff', 'live-event', 'mlb',
     'MLB Sunday morning game.', 1, 150, '2024-04-14', 'ESPN+'),
    ('UFC Fight Night', 'live-event', 'mma',
     'UFC Fight Night main card.', 1, 240, '2024-04-13', 'UFC'),
    ('30 for 30: Catholics vs Convicts', 'documentary', 'ncaaf',
     'Notre Dame vs Miami 1988.', 0, 90, '2016-12-10', 'ESPN Films'),
    ('30 for 30: The Best That Never Was', 'documentary', 'ncaaf',
     'Marcus Dupree story.', 0, 100, '2010-11-09', 'ESPN Films'),
    ('Eli\'s Places', 'series', 'ncaaf',
     'Eli Manning college football tour.', 0, 30, '2021-09-04', 'Eli Manning'),
    ('Peyton\'s Places', 'series', 'nfl',
     'Peyton Manning NFL legacy show.', 0, 30, '2019-07-23', 'Peyton Manning'),
    ('Jalen Hurts: 1-on-1', 'special', 'nfl',
     'Sit-down with Jalen Hurts.', 0, 60, '2024-04-05', 'ESPN+'),
    ('Caitlin Clark: For the Win', 'special', 'ncaaw',
     'Iowa star feature documentary.', 0, 60, '2024-04-08', 'ESPN+'),
    ('Bracketology Live', 'show', 'ncaaw',
     'Women bracketology projection.', 1, 30, '2024-03-15', 'Charlie Creme'),
    ('UFC PPV: Pre-Show', 'special', 'mma',
     'UFC PPV pre-show.', 1, 60, '2024-04-13', 'UFC'),
]


def make_watchables(cur):
    rows = []
    for i, (title, kind, sport, desc, is_live, dur, release, host) in enumerate(
            WATCHABLES_SEED):
        rows.append((
            i + 1, title, slugify(title), kind, sport, desc, 1, is_live,
            dur, release, host,
        ))
    cur.executemany(
        "INSERT INTO watchables (id, title, slug, kind, sport_slug, "
        "description, is_espn_plus, is_live, duration_minutes, "
        "release_date, host_or_studio) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 11. Parlays ─────────────────────────────────────────────────────────────

def make_parlays(cur):
    rows = []
    sports_pool = ['nba', 'nfl', 'mlb', 'nhl', 'soccer']
    sportsbooks = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars']
    parlay_templates = [
        ("Same-game 3-leg NBA banger", 3),
        ("4-leg NBA spread parlay", 4),
        ("3-leg NFL moneyline parlay", 3),
        ("MLB run-line lock parlay", 2),
        ("NHL puck-line parlay", 3),
        ("Soccer Both Teams to Score parlay", 4),
        ("3-leg over/under parlay", 3),
        ("5-leg long-shot parlay", 5),
        ("Player prop pile-on parlay", 4),
        ("Multi-sport Sunday parlay", 4),
        ("Underdog moneyline parlay", 3),
        ("Heavy favorites moneyline ladder", 4),
        ("Final-Four bracketology parlay", 3),
        ("UFC main-card 3-leg parlay", 3),
        ("PGA Masters first-round parlay", 3),
        ("Champions League round-of-16 parlay", 4),
        ("NCAA Tournament Sweet 16 parlay", 4),
        ("ESPN BET best-bets parlay", 4),
        ("Live in-game parlay starter", 3),
        ("Prime-time NBA parlay", 3),
        ("Sunday Night Football SGP", 3),
        ("Monday Night Football SGP", 3),
        ("Saturday CFB top-25 parlay", 4),
        ("First-touchdown scorer parlay", 3),
        ("Hot-streak hitters parlay", 4),
        ("Strikeout-pitcher prop parlay", 3),
        ("Home-team road-favorite parlay", 3),
        ("Same-game NHL goalie parlay", 3),
        ("Champions League quarterfinal parlay", 4),
        ("World Series futures parlay", 3),
    ]
    for i, (title, n_legs) in enumerate(parlay_templates):
        key = f'r4-parlay-{i}'
        sport = sports_pool[h(f'{key}-sport', len(sports_pool))]
        american = h(f'{key}-am', 1200, 180) * (-1 if (h(f'{key}-sign', 2) == 0 and n_legs <= 2) else 1)
        decimal_o = round(1.0 + abs(american) / 100.0
                          if american > 0 else 1.0 + 100.0 / abs(american), 2)
        legs = []
        for j in range(n_legs):
            legs.append({
                'sport': sport,
                'matchup': f'Team A vs Team B (leg {j+1})',
                'pick': f'Pick {j+1}',
                'odds': -110 + h(f'{key}-{j}-o', 100, 0) - 50,
            })
        rows.append((
            i + 1, slugify(title) + f'-{i:02d}', title, n_legs,
            american, decimal_o, json.dumps(legs), sport,
            sportsbooks[i % len(sportsbooks)],
            1 if i < 6 else 0,
        ))
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
        print('R4 extension already applied — no-op.')
        conn.close()
        return
    create_new_tables(cur)
    n_gm  = make_games(cur)
    n_st  = make_player_stats(cur)
    n_art = make_articles(cur)
    n_odd = make_betting_odds(cur)
    n_aw  = make_awards(cur)
    n_dp  = make_draft_picks(cur)
    n_pc  = make_podcasts(cur)
    n_pbp = make_play_by_play(cur)
    n_wt  = make_watchables(cur)
    n_pl  = make_parlays(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R4 inserted: games={n_gm}, player_stats={n_st}, '
          f'articles={n_art}, betting_odds={n_odd}, awards={n_aw}, '
          f'draft_picks={n_dp}, podcasts={n_pc}, play_by_play={n_pbp}, '
          f'watchables={n_wt}, parlays={n_pl}')


if __name__ == '__main__':
    main()
