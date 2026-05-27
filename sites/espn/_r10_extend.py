#!/usr/bin/env python3
"""R10 final polish extension for sites/espn — direct sqlite3 INSERT only.

Final iter (10/10). Continues gotcha #14 path: HF seed has drifted from
seed_data.py, so we extend the live DB with idempotent direct INSERTs.

R10 on top of R9 baseline (games 12026 / articles 9851 / betting 5510 /
parlays 115 / podcasts 194 / tasks 4705):

  * +3000+ games        (12026 → 15000+)  NBA 2028-29 full reg + sched,
                                          NHL 2027-28 reg-season,
                                          MLB 2027 reg + postseason,
                                          NFL 2027 reg-season + sched,
                                          soccer 27-28 league + cup,
                                          ncaaf 2027 reg, ncaam 27-28 reg,
                                          retroactive depth (NBA 21-22 +
                                          NFL 22 + MLB 25 + NHL 24-25).
  * +2200+ articles     (9851 → 12000+)   8 fresh R10 templates × 7 sports +
                                          ES Deportes + magazine cross-sport.
  * +2000+ betting_odds (5510 → 7500+)    cross-book on the new R10 games.
  * +20 parlays
  * Boxscore + PBP coverage for every new R10 final game in nba/nfl/nhl/
    mlb/soccer (3 home + 3 away player stats; 5 pbp lines per game).
  * Marker row sports.slug '_r10_marker' — idempotent.
  * Re-emit indexes alpha-sorted + VACUUM (gotcha #2) for byte-id reset.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r10_marker` row in `sports`.
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
        "SELECT 1 FROM sports WHERE slug='_r10_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (108, 'R10 marker', '_r10_marker', 'r10_extend applied',
         '/_internal/r10/', 108, 0))


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


# ─── Venue pools (kept consistent with R9) ───────────────────────────────────

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


# ─── 1. Games (+3000+) ────────────────────────────────────────────────────────

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
             postponed_every=0, key_prefix='r10'):
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

    # NBA 2028-29 full reg-season + scheduled tail
    emit('nba', '2028-29-final', teams['nba'], NBA_VENUES,
         date(2028, 10, 17), 540, 35, 95, 8, 'ESPN', 'Final',
         postponed_every=44)
    emit('nba', '2028-29-sched', teams['nba'], NBA_VENUES,
         None, 180, 0, 0, 0, 'TNT', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2028, 12, 15), 110))
    emit('nba', '2028-29-playoffs', teams['nba'], NBA_VENUES,
         date(2029, 4, 18), 80, 40, 95, 8, 'ABC', 'Final')

    # NHL 2027-28 reg-season + cup preview
    emit('nhl', '2027-28-reg', teams['nhl'], NHL_VENUES,
         date(2027, 10, 8), 360, 7, 1, 1, 'ESPN+', 'Final',
         postponed_every=42)
    emit('nhl', '2027-28-cup', teams['nhl'], NHL_VENUES,
         None, 70, 0, 0, 0, 'TNT', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2028, 4, 15), 60))

    # MLB 2027 reg + postseason
    emit('mlb', '2027-reg', teams['mlb'], MLB_VENUES,
         date(2027, 4, 1), 360, 14, 0, 0, 'MLB Network', 'Final',
         postponed_every=46)
    emit('mlb', '2027-postseason', teams['mlb'], MLB_VENUES,
         date(2027, 10, 2), 36, 12, 1, 1, 'FOX', 'Final')

    # NFL 2027 reg-season + scheduled tail
    emit('nfl', '2027-reg', teams['nfl'], NFL_VENUES,
         date(2027, 9, 11), 240, 38, 7, 7, 'CBS', 'Final',
         postponed_every=50)
    emit('nfl', '2027-sched', teams['nfl'], NFL_VENUES,
         None, 60, 0, 0, 0, 'NBC', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2027, 12, 1), 60))
    emit('nfl', '2027-postseason', teams['nfl'], NFL_VENUES,
         date(2028, 1, 9), 14, 38, 10, 10, 'FOX', 'Final')

    # Soccer 27-28 league + cup
    if teams['soccer']:
        emit('soccer', '2027-28-league', teams['soccer'], SOCCER_VENUES,
             date(2027, 9, 1), 330, 5, 0, 0, 'ESPN+', 'FT')
        emit('soccer', '2027-28-cup', teams['soccer'], SOCCER_VENUES,
             None, 60, 0, 0, 0, 'Peacock', 'Scheduled',
             status_default='scheduled',
             scheduled_window=(date(2028, 4, 1), 60))

    # NCAAF 2027 reg
    if teams['ncaaf']:
        emit('ncaaf', '2027-reg', teams['ncaaf'], NCAAF_VENUES,
             date(2027, 9, 6), 100, 56, 10, 12, 'ABC', 'Final')

    # NCAAM 2027-28 reg + preview
    if teams['ncaam']:
        emit('ncaam', '2027-28-reg', teams['ncaam'], NCAAM_VENUES,
             date(2027, 11, 12), 150, 95, 50, 8, 'CBS', 'Final')
        emit('ncaam', '2028-29-prev', teams['ncaam'], NCAAM_VENUES,
             None, 50, 0, 0, 0, 'ESPN', 'Scheduled',
             status_default='scheduled',
             scheduled_window=(date(2028, 11, 5), 120))

    # Retroactive depth — different prefix so no slug collision with R9.
    emit('nba', '2021-22-fill', teams['nba'], NBA_VENUES,
         date(2021, 11, 1), 240, 35, 95, 8, 'TNT', 'Final',
         postponed_every=50)
    emit('nfl', '2022-fill', teams['nfl'], NFL_VENUES,
         date(2022, 9, 8), 100, 38, 7, 7, 'NBC', 'Final')
    emit('mlb', '2025-fill', teams['mlb'], MLB_VENUES,
         date(2025, 6, 1), 110, 14, 0, 0, 'ESPN', 'Final')
    emit('nhl', '2024-25-fill', teams['nhl'], NHL_VENUES,
         date(2024, 11, 5), 110, 7, 1, 1, 'ESPN+', 'Final')
    if teams['soccer']:
        emit('soccer', '2023-24-fill', teams['soccer'], SOCCER_VENUES,
             date(2023, 11, 1), 90, 5, 0, 0, 'ESPN+', 'FT')

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    # Return the list of (id, sport, status, home_id, away_id, hs, as_)
    return rows


# ─── 2. Boxscore + PBP coverage for new R10 final games ──────────────────────

def make_box_and_pbp(cur, new_games):
    """For each R10 game with status='final' in nba/nfl/nhl/mlb/soccer,
    add 6 game_player_stats rows (3 home + 3 away) and 5 play_by_play
    rows. Deterministic from game id + team id."""
    stat_next = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM game_player_stats") or 0) + 1
    pbp_next = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM play_by_play") or 0) + 1
    stat_rows = []
    pbp_rows = []

    # Cache players per team for sports that have them.
    PLAYER_SPORTS = ('nba', 'nfl', 'nhl', 'mlb', 'soccer')
    team_players = {}
    for sp in PLAYER_SPORTS:
        tids = [r[0] for r in cur.execute(
            "SELECT id FROM teams WHERE sport_slug=?", (sp,)).fetchall()]
        for tid in tids:
            plist = cur.execute(
                "SELECT id, name FROM players WHERE team_id=? "
                "ORDER BY id LIMIT 6", (tid,)).fetchall()
            team_players[tid] = plist

    # Skip any (game_id, player_id) pair that already exists.
    existing_pairs = set(cur.execute(
        "SELECT game_id, player_id FROM game_player_stats").fetchall())
    existing_pbp_games = set(r[0] for r in cur.execute(
        "SELECT DISTINCT game_id FROM play_by_play").fetchall())

    for row in new_games:
        gid, sport, home_id, away_id, hs, as_, status = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[9])
        if status != 'final':
            continue

        # Boxscore for player-equipped sports.
        if sport in PLAYER_SPORTS:
            for side, tid, team_score in (('h', home_id, hs),
                                          ('a', away_id, as_)):
                players = team_players.get(tid) or []
                # take up to 3 players
                for pi, (pid, pname) in enumerate(players[:3]):
                    if (gid, pid) in existing_pairs:
                        continue
                    existing_pairs.add((gid, pid))
                    key = f'r10-box-{gid}-{pid}'
                    if sport == 'nba':
                        share = [0.45, 0.30, 0.25][pi]
                        pts = max(2, int(team_score * share))
                        reb = h(key + '-r', 9, 1)
                        ast = h(key + '-a', 7, 1)
                        stl = h(key + '-s', 3)
                        blk = h(key + '-b', 2)
                        mins = f'{20 + h(key + "-m", 18)}:{h(key + "-s2", 60):02d}'
                    elif sport == 'nfl':
                        pts = max(0, h(key + '-pts', max(team_score, 1)))
                        reb = h(key + '-yd', 60)  # rushing/rec yards
                        ast = h(key + '-c', 9)    # completions
                        stl = h(key + '-tk', 6)
                        blk = h(key + '-sk', 2)
                        mins = '—'
                    elif sport == 'nhl':
                        pts = max(0, h(key + '-pt', 4))   # points
                        reb = h(key + '-sog', 6, 1)        # shots on goal
                        ast = h(key + '-as', 3)            # assists
                        stl = h(key + '-tk', 3)            # takeaways
                        blk = h(key + '-bs', 3)            # blocked shots
                        mins = f'{12 + h(key + "-toi", 12)}:{h(key + "-toi2", 60):02d}'
                    elif sport == 'mlb':
                        pts = max(0, h(key + '-rbi', 4))   # RBI
                        reb = h(key + '-h', 4)             # hits
                        ast = h(key + '-r', 3)             # runs
                        stl = h(key + '-sb', 2)
                        blk = h(key + '-bb', 3)            # walks
                        mins = '—'
                    elif sport == 'soccer':
                        pts = max(0, h(key + '-g', 2))     # goals
                        reb = h(key + '-sh', 5, 1)         # shots
                        ast = h(key + '-as', 2)            # assists
                        stl = h(key + '-tk', 4)            # tackles
                        blk = h(key + '-pa', 60, 20)       # passes
                        mins = f'{60 + h(key + "-mp", 30)}'
                    else:
                        continue
                    stat_rows.append((stat_next, gid, pid, tid,
                                      pts, reb, ast, stl, blk, mins))
                    stat_next += 1

        # Five PBP lines per final game (skip if already has any).
        if gid in existing_pbp_games:
            continue
        existing_pbp_games.add(gid)
        # Pick actor names: from players if available, else team name.
        home_players = team_players.get(home_id) or []
        away_players = team_players.get(away_id) or []
        # Fallback team names
        home_team_name = cur.execute(
            "SELECT name FROM teams WHERE id=?", (home_id,)).fetchone()
        home_team_name = home_team_name[0] if home_team_name else 'Home'
        away_team_name = cur.execute(
            "SELECT name FROM teams WHERE id=?", (away_id,)).fetchone()
        away_team_name = away_team_name[0] if away_team_name else 'Away'

        def actor(side, idx):
            players = home_players if side == 'h' else away_players
            if players:
                return players[idx % len(players)][1]
            return f'{home_team_name if side == "h" else away_team_name} Player {idx + 1}'

        # Event vocab per sport
        if sport == 'nba':
            evs = [('Q1', '11:42', 'jumpshot', 'opens scoring with a jumper'),
                   ('Q2', '7:15', 'three-pointer', 'drains a three from the wing'),
                   ('Q3', '3:08', 'rebound', 'grabs defensive rebound'),
                   ('Q4', '5:30', 'foul', 'shooting foul drawn'),
                   ('Q4', '0:18', 'jumpshot', 'pull-up clutch jumper')]
            periods = ['Q1', 'Q2', 'Q3', 'Q4', 'Q4']
        elif sport == 'nfl':
            evs = [('Q1', '12:50', 'kickoff', 'opens the game with a kickoff'),
                   ('Q2', '6:22', 'touchdown', 'rushing touchdown'),
                   ('Q3', '8:11', 'interception', 'reads the route, picks it'),
                   ('Q4', '4:45', 'field-goal', '38-yard field goal'),
                   ('Q4', '0:24', 'touchdown', 'walk-off receiving touchdown')]
            periods = ['Q1', 'Q2', 'Q3', 'Q4', 'Q4']
        elif sport == 'nhl':
            evs = [('P1', '14:50', 'face-off', 'wins the opening face-off'),
                   ('P1', '5:14', 'goal', 'top-shelf goal'),
                   ('P2', '12:00', 'penalty', '2-min minor for hooking'),
                   ('P3', '7:42', 'goal', 'power-play goal'),
                   ('P3', '0:48', 'shot', 'shot saved by the goaltender')]
            periods = ['P1', 'P1', 'P2', 'P3', 'P3']
        elif sport == 'mlb':
            evs = [('1', '—', 'pitch', 'first-pitch strike'),
                   ('3', '—', 'single', 'lines a single to right'),
                   ('5', '—', 'home-run', 'sends one over the wall'),
                   ('7', '—', 'strikeout', 'swinging strikeout, fastball'),
                   ('9', '—', 'fly-out', 'fly-out to deep center to end it')]
            periods = ['1', '3', '5', '7', '9']
        elif sport == 'soccer':
            evs = [('H1', '12:30', 'shot', 'shot just wide of the post'),
                   ('H1', '38:14', 'goal', 'opens scoring from a set piece'),
                   ('H2', '52:11', 'yellow-card', 'booking for a late tackle'),
                   ('H2', '78:09', 'sub', 'tactical substitution'),
                   ('H2', '90:02', 'goal', 'late winner in stoppage time')]
            periods = ['H1', 'H1', 'H2', 'H2', 'H2']
        elif sport == 'ncaaf':
            evs = [('Q1', '13:01', 'kickoff', 'opening kickoff'),
                   ('Q2', '7:42', 'touchdown', 'rushing touchdown — 14 yards'),
                   ('Q3', '8:55', 'turnover', 'fumble recovered by defense'),
                   ('Q4', '6:10', 'field-goal', '42-yard field goal'),
                   ('Q4', '0:35', 'touchdown', 'go-ahead touchdown drive')]
            periods = ['Q1', 'Q2', 'Q3', 'Q4', 'Q4']
        elif sport == 'ncaam':
            evs = [('H1', '17:14', 'jumpshot', 'opens scoring with a jumper'),
                   ('H1', '4:30', 'three-pointer', 'corner three connects'),
                   ('H2', '15:00', 'rebound', 'gets the offensive board'),
                   ('H2', '5:08', 'foul', 'shooting foul drawn'),
                   ('H2', '0:18', 'jumpshot', 'pull-up clutch jumper')]
            periods = ['H1', 'H1', 'H2', 'H2', 'H2']
        else:
            continue

        # Running score accumulation
        run_h, run_a = 0, 0
        for i, (per, clk, etype, desc) in enumerate(evs):
            side = 'h' if (i % 2 == 0) else 'a'
            # rough score increments
            inc_h = 0
            inc_a = 0
            if etype in ('jumpshot', 'three-pointer'):
                v = 3 if etype == 'three-pointer' else 2
                if side == 'h': inc_h = v
                else: inc_a = v
            elif etype == 'touchdown':
                if side == 'h': inc_h = 7
                else: inc_a = 7
            elif etype == 'field-goal':
                if side == 'h': inc_h = 3
                else: inc_a = 3
            elif etype == 'goal':
                if side == 'h': inc_h = 1
                else: inc_a = 1
            elif etype == 'home-run':
                if side == 'h': inc_h = 1
                else: inc_a = 1
            run_h += inc_h
            run_a += inc_a
            actor_name = actor(side, i)
            tid = home_id if side == 'h' else away_id
            description = f'{actor_name} {desc}.'
            pbp_rows.append((pbp_next, gid, sport, i + 1, per, clk,
                             tid, actor_name, etype, description,
                             run_h, run_a))
            pbp_next += 1

    if stat_rows:
        cur.executemany(
            "INSERT INTO game_player_stats (id, game_id, player_id, team_id, "
            "points, rebounds, assists, steals, blocks, minutes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)", stat_rows)
    if pbp_rows:
        cur.executemany(
            "INSERT INTO play_by_play (id, game_id, sport_slug, sequence, "
            "period, clock, team_id, actor_name, event_type, description, "
            "score_home, score_away) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            pbp_rows)
    return len(stat_rows), len(pbp_rows)


# ─── 3. Articles (+2200+) ─────────────────────────────────────────────────────

ARTICLE_TEMPLATES_R10 = {
    'final-power-rankings': (
        '{team} final {season} power rankings: {sport_upper} dynasty watch',
        'A deep look at how {team} {sport_upper} {season} stacks up against '
        'the rest of the conference heading into the playoffs. We rank '
        'the dynasty windows, regression risks, and the rotation slot most '
        'likely to swing a postseason series. Includes a checklist for '
        'agents browsing /<sport>/standings → /team/<sport>/<slug>.',
        ['power-rankings', 'dynasty', 'r10']),
    'midseason-grade': (
        '{team} midseason grade: {sport_upper} {season} report card',
        'The {team} midseason grade for {sport_upper} {season} — offense, '
        'defense, depth, and front-office moves each get a letter grade. '
        'We compare against R9 power index, log the players whose stock '
        'rose the most, and project a finish range.',
        ['midseason', 'grade', 'r10']),
    'coaching-hot-seat': (
        '{team} coaching hot seat: who is on the bubble heading into {season}',
        'For {team} {sport_upper} {season}: which coordinators and assistants '
        'are on the bubble, the contract clauses that trigger renewals, and '
        'the buyout math the front office is running. A practical guide for '
        'fans tracking /<sport>/transactions.',
        ['coaching', 'hot-seat', 'r10']),
    'free-agent-spotlight': (
        '{team} free-agent spotlight: top {season} {sport_upper} targets',
        'Five free agents {team} should be tracking in {sport_upper} '
        '{season}, ordered by fit + cap fit. We log market value, last '
        'three-year production, and the comp pick downside. Pairs with '
        '/fantasy/<sport>/waiver-wire for fantasy implications.',
        ['free-agent', 'targets', 'r10']),
    'hof-watch': (
        '{team} Hall-of-Fame watch: which {season} contributors are climbing',
        'A look at the {team} {sport_upper} {season} roster through a '
        'Hall-of-Fame lens. We list the three most-likely first-ballot '
        'candidates, the dark-horse case for a longshot, and the legacy '
        'milestones to track this season.',
        ['hall-of-fame', 'legacy', 'r10']),
    'draft-tracker': (
        '{team} draft tracker: {season} {sport_upper} board and mock targets',
        'Live draft board for {team} {sport_upper} {season} prospects. We '
        'rank by need, athletic-profile fit, and projected board fall, and '
        'cross-reference five recent mock-draft consensus boards. Updated '
        'every week through draft night.',
        ['draft', 'tracker', 'r10']),
    'compound-walkthrough': (
        '{team} agent compound walkthrough: chaining 9 ESPN tools',
        'A nine-step compound walkthrough for {team} {sport_upper} {season} — '
        'home → /<sport>/scoreboard → /game/<id> → /<sport>/play-by-play → '
        '/article/<slug> → /podcast/<slug> → /fantasy/<sport> → '
        '/<sport>/odds → /watch/list. Each step has the precise assertion '
        'agents should make before advancing.',
        ['agent', 'compound', 'multi-step', 'r10']),
    'analytics-explainer': (
        '{team} advanced analytics explainer: {sport_upper} {season} deep dive',
        'Breaking down the advanced analytics powering {team} {sport_upper} '
        '{season} coverage on ESPN — pace, true shooting, win shares, '
        'expected points, and the proprietary indices we surface on '
        '/<sport>/stats. Includes a glossary linked from /stat-glossary.',
        ['analytics', 'explainer', 'r10']),
}


ARTICLE_TEMPLATES_R10_ES = {
    'rankings-es': (
        'Rankings finales {season}: {team} en {sport_upper}',
        'Una mirada profunda a cómo los {team} de {sport_upper} {season} '
        'se comparan con el resto de la conferencia. Cubrimos las ventanas '
        'de dinastía, riesgos de regresión, y la rotación que más puede '
        'influir en una serie de playoffs.',
        ['rankings', 'dinastia', 'r10']),
    'midseason-es': (
        'Calificaciones de media temporada: {team} {sport_upper} {season}',
        'La calificación de media temporada de los {team} para {sport_upper} '
        '{season} — ofensiva, defensiva, profundidad y movimientos de '
        'oficina principal reciben una calificación. Comparamos contra el '
        'power index de R9.',
        ['media-temporada', 'r10']),
    'draft-es': (
        'Seguimiento de draft: objetivos {season} de los {team} en {sport_upper}',
        'Tabla de draft en vivo para los prospectos {team} {sport_upper} '
        '{season}. Clasificamos por necesidad, perfil atlético y caída '
        'proyectada del board.',
        ['draft', 'r10']),
    'compound-es': (
        'Guía de agentes: encadenando nueve herramientas ESPN para {team}',
        'Un recorrido en nueve pasos para fanáticos {team} {sport_upper} '
        '{season} — inicio → marcador → detalles de juego → jugada por '
        'jugada → artículo → podcast → fantasy → cuotas → lista de visualización.',
        ['agente', 'compound', 'r10']),
}


SPORT_PLANS_R10 = [
    ('nba', 'NBA',
     'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
     'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
     'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
     'Oklahoma City Thunder,Cleveland Cavaliers,Indiana Pacers,'
     'Minnesota Timberwolves,New Orleans Pelicans,Sacramento Kings,'
     'Memphis Grizzlies,Atlanta Hawks,Brooklyn Nets,Chicago Bulls,'
     'Houston Rockets,LA Clippers,Orlando Magic,Toronto Raptors,'
     'Detroit Pistons,Charlotte Hornets,Utah Jazz,Washington Wizards,'
     'San Antonio Spurs,Portland Trail Blazers'.split(','),
     '2028-29'),
    ('nfl', 'NFL',
     'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
     'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
     'Detroit Lions,Miami Dolphins,Green Bay Packers,'
     'Cincinnati Bengals,Pittsburgh Steelers,Houston Texans,'
     'New York Giants,Los Angeles Rams,Tampa Bay Buccaneers,'
     'Atlanta Falcons,Seattle Seahawks,Minnesota Vikings,'
     'Las Vegas Raiders,Indianapolis Colts,Jacksonville Jaguars,'
     'Tennessee Titans,Carolina Panthers,Washington Commanders'.split(','),
     '2027'),
    ('mlb', 'MLB',
     'New York Yankees,Los Angeles Dodgers,Boston Red Sox,'
     'Atlanta Braves,Houston Astros,Texas Rangers,'
     'Philadelphia Phillies,Chicago Cubs,San Diego Padres,'
     'Toronto Blue Jays,New York Mets,Seattle Mariners,'
     'Baltimore Orioles,Cleveland Guardians,St. Louis Cardinals,'
     'Milwaukee Brewers,Arizona Diamondbacks,Tampa Bay Rays,'
     'Minnesota Twins,Detroit Tigers'.split(','),
     '2027'),
    ('nhl', 'NHL',
     'Boston Bruins,Edmonton Oilers,Vegas Golden Knights,'
     'New York Rangers,Toronto Maple Leafs,Florida Panthers,'
     'Colorado Avalanche,Tampa Bay Lightning,Carolina Hurricanes,'
     'Dallas Stars,Vancouver Canucks,New Jersey Devils,'
     'Pittsburgh Penguins,Washington Capitals'.split(','),
     '2027-28'),
    ('soccer', 'Soccer',
     'Arsenal,Manchester City,Liverpool,'
     'Real Madrid,Barcelona,Bayern Munich,'
     'Paris Saint-Germain,Inter Milan,Manchester United,'
     'Chelsea,Atletico Madrid,Juventus,Tottenham Hotspur,'
     'Borussia Dortmund'.split(','),
     '2027-28'),
    ('ncaaf', 'CFB',
     'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
     'USC,Notre Dame,Oregon,Penn State,Florida State,Clemson,'
     'Tennessee,Oklahoma'.split(','),
     '2027'),
    ('ncaam', 'CBB',
     'Duke,Kansas,Kentucky,Connecticut,North Carolina,'
     'Houston,Purdue,Arizona,UCLA,Tennessee,Auburn,'
     'Gonzaga,Baylor'.split(','),
     '2027-28'),
]

ES_SPORT_PLANS_R10 = [
    ('nba', 'NBA',
     'Boston Celtics,Los Angeles Lakers,Golden State Warriors,'
     'Milwaukee Bucks,Denver Nuggets,Miami Heat,Dallas Mavericks,'
     'Philadelphia 76ers,New York Knicks,Phoenix Suns,'
     'Oklahoma City Thunder,Cleveland Cavaliers'.split(','),
     '2028-29'),
    ('nfl', 'NFL',
     'Kansas City Chiefs,San Francisco 49ers,Buffalo Bills,'
     'Baltimore Ravens,Dallas Cowboys,Philadelphia Eagles,'
     'Detroit Lions,Miami Dolphins'.split(','),
     '2027'),
    ('soccer', 'Soccer',
     'Real Madrid,Barcelona,Bayern Munich,'
     'Paris Saint-Germain,Inter Milan,Manchester City,'
     'Arsenal,Liverpool,Atletico Madrid,Juventus'.split(','),
     '2027-28'),
    ('ncaaf', 'CFB',
     'Alabama,Georgia,Ohio State,Texas,Michigan,LSU,'
     'USC,Notre Dame,Oregon'.split(','),
     '2027'),
]


def make_articles(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM articles").fetchall())

    rows = []
    tpl_names = sorted(ARTICLE_TEMPLATES_R10.keys())
    for sport_slug, sport_upper, teams_list, season in SPORT_PLANS_R10:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R10[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'r10-{sport_slug}-{team_slug}-{tpl_name}-00'
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
                day_off = h(f'r10-art-pub-{slug}', 180)
                base_pub = date(2026, 5, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r10-{ti}.jpg',
                    tags,
                    1 if (tpl_name == 'final-power-rankings' and ti < 2) else 0,
                    1 if (tpl_name == 'compound-walkthrough' and ti < 1) else 0,
                    pub_dt, pub_disp,
                ))
                next_id += 1

    tpl_names_es = sorted(ARTICLE_TEMPLATES_R10_ES.keys())
    for sport_slug, sport_upper, teams_list, season in ES_SPORT_PLANS_R10:
        for ti, team in enumerate(teams_list):
            for tpl_name in tpl_names_es:
                title_fmt, body_fmt, tag_kw = ARTICLE_TEMPLATES_R10_ES[tpl_name]
                team_slug = team.lower().replace(' ', '-').replace('.', '')
                slug = f'es-r10-{sport_slug}-{team_slug}-{tpl_name}-00'
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
                day_off = h(f'es-r10-art-pub-{slug}', 180)
                base_pub = date(2026, 6, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Deportes',
                    f'/static/images/espn/articles/{sport_slug}/es-r10-{ti}.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    # Magazine cross-sport batch — themed weekly columns for R10.
    MAGAZINE_TOPICS = [
        ('rankings-spotlight',
         '{sport_upper} {season} power rankings spotlight: week {wk}',
         'Our weekly power-rankings recap for {sport_upper} {season} week '
         '{wk}. Movers, fallers, and the one upset that flipped the top of '
         'the board. Cross-references /<sport>/standings.',
         ['power-rankings', 'magazine', 'r10']),
        ('compound-tour',
         'Compound tour of the week: {sport_upper} {season} ({wk})',
         'This week\'s curated 9-step agent tour across {sport_upper} '
         '{season} URLs: home → scoreboard → game → play-by-play → article '
         '→ podcast → fantasy → odds → watch. Includes the assertion that '
         'unlocks the next hop.',
         ['multi-step', 'compound', 'agent', 'magazine', 'r10']),
        ('draft-night',
         'Draft night recap: {sport_upper} {season} week {wk}',
         'A retrospective on this week\'s {sport_upper} {season} draft '
         'movement. Trades, slot swaps, and the rookie most likely to swing '
         'the dynasty rankings.',
         ['draft', 'magazine', 'r10']),
        ('analytics-deep',
         'Analytics deep dive: {sport_upper} {season} week {wk}',
         'A deep-dive into the analytics powering this week\'s coverage. '
         'We surface pace, true shooting, expected points, and the dark-horse '
         'metric that quietly explains a top result.',
         ['analytics', 'magazine', 'r10']),
        ('hof-tracker',
         'Hall-of-Fame tracker: {sport_upper} {season} week {wk}',
         'Our weekly Hall-of-Fame tracker for {sport_upper} {season} week '
         '{wk}. We log milestone counts, dark-horse candidates, and the '
         'legacy storylines that emerged this week.',
         ['hall-of-fame', 'magazine', 'r10']),
        ('hot-seat',
         'Coaching hot-seat watch: {sport_upper} {season} week {wk}',
         'Who is on the coaching bubble in {sport_upper} {season} week {wk}? '
         'A rundown of contract clauses, buyout math, and the candidate '
         'lists already being assembled.',
         ['coaching', 'hot-seat', 'magazine', 'r10']),
    ]
    SPORTS_FOR_MAGAZINE = [('nba', 'NBA', '2028-29'),
                           ('nba', 'NBA', '2027-28'),
                           ('nfl', 'NFL', '2027'),
                           ('nfl', 'NFL', '2026'),
                           ('mlb', 'MLB', '2027'),
                           ('mlb', 'MLB', '2026'),
                           ('nhl', 'NHL', '2027-28'),
                           ('nhl', 'NHL', '2026-27'),
                           ('soccer', 'Soccer', '2027-28'),
                           ('soccer', 'Soccer', '2026-27'),
                           ('ncaaf', 'CFB', '2027'),
                           ('ncaaf', 'CFB', '2026'),
                           ('ncaam', 'CBB', '2027-28'),
                           ('ncaam', 'CBB', '2026-27')]
    for sport_slug, sport_upper, season in SPORTS_FOR_MAGAZINE:
        for tpl_name, title_fmt, body_fmt, tag_kw in MAGAZINE_TOPICS:
            for wk in range(1, 21):  # week 1..20
                slug = f'r10-mag-{sport_slug}-{season}-{tpl_name}-wk{wk:02d}'
                if slug in existing:
                    continue
                existing.add(slug)
                title = title_fmt.format(sport_upper=sport_upper,
                                         season=season, wk=wk)
                body = body_fmt.format(sport_upper=sport_upper,
                                       season=season, wk=wk)
                tags = json.dumps([sport_upper, season, 'magazine'] + tag_kw)
                day_off = h(f'r10-mag-pub-{slug}', 180)
                base_pub = date(2026, 2, 1) + timedelta(days=day_off)
                pub_dt = base_pub.strftime('%Y-%m-%d 00:00:00.000000')
                pub_disp = base_pub.strftime('%B %-d, %Y')
                rows.append((
                    next_id, sport_slug, title, slug, '', body,
                    'ESPN Staff',
                    f'/static/images/espn/articles/{sport_slug}/r10-mag.jpg',
                    tags, 0, 0, pub_dt, pub_disp,
                ))
                next_id += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, body, "
        "author, image, tags, is_headline, is_featured, created_at, "
        "published_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 4. Betting odds (+2000+) ─────────────────────────────────────────────────

BOOKS_R10 = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars',
             'PointsBet', 'BetRivers', 'Hard Rock Bet']


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
            "ORDER BY id DESC LIMIT 700", (sport,)).fetchall()]
        if not gids:
            return 0
        bks = BOOKS_R10
        nonlocal next_id
        for i, gid in enumerate(gids):
            if added >= target:
                break
            for b_idx in range(4):
                if added >= target:
                    break
                book = bks[(h(f'r10-bo-{sport}-{gid}-b{b_idx}', len(bks))
                            + b_idx) % len(bks)]
                if (gid, book) in existing_pairs:
                    continue
                existing_pairs.add((gid, book))
                key = f'r10-bo-{sport}-{gid}-{book}'
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
    n += emit_for_sport('nba', target=500)
    n += emit_for_sport('nfl', target=300)
    n += emit_for_sport('mlb', target=330)
    n += emit_for_sport('nhl', target=300)
    n += emit_for_sport('soccer', target=240)
    n += emit_for_sport('ncaaf', target=160)
    n += emit_for_sport('ncaam', target=180)

    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, home_moneyline, "
        "away_moneyline, spread_favorite, spread_line, total, over_odds, "
        "under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 5. Parlays (+20) ─────────────────────────────────────────────────────────

R10_PARLAYS = [
    ('r10-nba-2028-29-finals', '2028-29 Finals Double', 2, +1750, 18.50,
     'nba', 'ESPN BET',
     ['Celtics East 2028-29', 'Nuggets West 2028-29']),
    ('r10-nba-mvp-tier4', 'NBA MVP Tier-4 Trio 28-29', 3, +900, 10.00,
     'nba', 'DraftKings',
     ['Jokic top-3 MVP', 'Doncic top-3 MVP', 'Edwards top-3 MVP']),
    ('r10-nfl-2027-divisional', 'NFL 2027 Divisional Quartet',
     4, +1900, 20.00, 'nfl', 'BetMGM',
     ['Chiefs win AFC West', 'Lions NFC North', 'Bills AFC East',
      'Eagles NFC East']),
    ('r10-mlb-2027-postseason', 'MLB 2027 Postseason Trio',
     3, +1050, 11.50, 'mlb', 'FanDuel',
     ['Dodgers NL pennant', 'Yankees AL pennant',
      'Astros AL wild-card']),
    ('r10-nhl-27-28-cup', 'Stanley Cup 27-28 Trio', 3, +1500, 16.00,
     'nhl', 'Caesars',
     ['Oilers West', 'Panthers East', 'McDavid Conn Smythe']),
    ('r10-soccer-27-28-ucl', 'UCL 27-28 Quartet', 4, +2500, 26.00,
     'soccer', 'ESPN BET',
     ['Real Madrid SF', 'Manchester City SF', 'Bayern SF',
      'Inter Milan SF']),
    ('r10-ncaaf-2027-cfp', 'CFP 2027 Bracket Quartet', 4, +1700, 18.00,
     'ncaaf', 'DraftKings',
     ['Alabama semis', 'Ohio St semis', 'Georgia semis',
      'Texas semis']),
    ('r10-ncaam-2028-f4', '2028 Final Four Quartet', 4, +2700, 28.00,
     'ncaam', 'BetMGM',
     ['Duke F4', 'Houston F4', 'Connecticut F4', 'Kansas F4']),
    ('r10-deportes-uefa-trio', 'UEFA Trio (Deportes) 27-28',
     3, +520, 6.20, 'soccer', 'ESPN BET',
     ['Real Madrid UCL SF', 'Barcelona UCL QF',
      'Atletico UCL top-8']),
    ('r10-nba-coy-28-29', 'NBA COY 28-29 Trio', 3, +810, 9.10, 'nba',
     'PointsBet',
     ['Daigneault COY top-3', 'Mazzulla COY top-3', 'Spo COY top-3']),
    ('r10-nfl-coy-2027', 'NFL COY 2027 Double', 2, +680, 7.80,
     'nfl', 'BetRivers',
     ['Reid COY top-3', 'Campbell COY top-3']),
    ('r10-cross-app-sunday', 'Cross-App Sunday R10', 5, +2300, 24.00,
     'fantasy', 'FanDuel',
     ['LeBron 25+', 'Mahomes 275+', 'Judge HR',
      'McDavid 1A1G', 'Haaland brace']),
    ('r10-promo-stack-2', 'ESPN BET Promo Stack 2', 3, +500, 6.00,
     'nba', 'ESPN BET',
     ['SIGNUP100 boost', 'NBARESET boost', 'MVP25 boost']),
    ('r10-nfl-week-1-27', 'NFL Week 1 2027 Trio', 3, +560, 6.60,
     'nfl', 'DraftKings',
     ['Chiefs ML', 'Bills ML', 'Eagles ML']),
    ('r10-soccer-uefa-double', 'UEFA Champions League Double 27-28',
     2, +580, 6.80, 'soccer', 'BetMGM',
     ['Real Madrid SF', 'Manchester City SF']),
    ('r10-fantasy-veto-double', 'Fantasy Trade Veto Double 27-28',
     2, +410, 5.10, 'fantasy', 'FanDuel',
     ['League poll majority vote', 'Commissioner override pass']),
    ('r10-nil-trio', 'NIL Disclosure Trio 27', 3, +800, 9.00,
     'ncaaf', 'ESPN BET',
     ['Alabama disclosed deals top-3', 'Texas disclosed top-5',
      'Georgia collective top-3']),
    ('r10-tennis-27-major', 'Tennis 2027 Major Trio', 3, +1250, 13.50,
     'tennis', 'DraftKings',
     ['Sinner US Open', 'Alcaraz Wimbledon', 'Sabalenka AO']),
    ('r10-golf-27-major', '2027 Golf Major Double', 2, +1500, 16.00,
     'golf', 'BetMGM',
     ['Scheffler Masters', 'Schauffele Open Champ']),
    ('r10-mma-27-card', '2027 MMA Title Card Double', 2, +510, 6.10,
     'mma', 'BetRivers',
     ['Pereira retain LHW', 'Topuria FW future']),
]


def make_parlays(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM parlays") or 0) + 1
    existing = set(r[0] for r in cur.execute(
        "SELECT slug FROM parlays").fetchall())
    rows = []
    for slug, title, lc, ao, do, sp, book, legs in R10_PARLAYS:
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
        print('R10 extension already applied — no-op.')
        conn.close()
        return
    new_game_rows = make_games(cur)
    n_st, n_pbp = make_box_and_pbp(cur, new_game_rows)
    n_ar = make_articles(cur)
    n_bo = make_betting(cur)
    n_pl = make_parlays(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R10 inserted: games={len(new_game_rows)}, '
          f'game_player_stats={n_st}, play_by_play={n_pbp}, '
          f'articles={n_ar}, betting_odds={n_bo}, parlays={n_pl}')


if __name__ == '__main__':
    main()
