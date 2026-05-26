#!/usr/bin/env python3
"""R5 polish extension for sites/espn — direct sqlite3 INSERT only.

Continues gotcha #14 path: HF seed has drifted from seed_data.py, so we
extend the live DB with idempotent direct INSERTs.

R5 on top of R4:
  * +1250 games        → 3500+  (NBA 23-24 + 24-25 prev, NHL 23-24, MLB 23+24,
                                 NFL 23, soccer 23-24, ncaaf/ncaam)
  * +1525 player_stats → 4500+  (2023-24 season + earlier season fills)
  * +1900 play_by_play → 3000+  (~48 new marquee games × ~40 events)
  * +110 podcasts      →  150+  (team-specific + topic shows + draft/bet)
  * Marker row sports.slug '_r5_marker' (id=102) — idempotent.

Determinism: every value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r5_marker` row in `sports`.
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
        "SELECT 1 FROM sports WHERE slug='_r5_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (102, 'R5 marker', '_r5_marker', 'r5_extend applied',
         '/_internal/', 102, 0))


def normalize(cur):
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── Venues (reuse R4 sets, add a few) ────────────────────────────────────────

NBA_VENUES = ['TD Garden', 'Crypto.com Arena', 'Madison Square Garden',
              'Chase Center', 'Ball Arena', 'Paycom Center',
              'Kaseya Center', 'American Airlines Center',
              'Footprint Center', 'Fiserv Forum', 'Spectrum Center',
              'Smoothie King Center', 'Target Center', 'Moda Center',
              'Toyota Center', 'Wells Fargo Center', 'Gainbridge Fieldhouse']
NHL_VENUES = ['TD Garden', 'Madison Square Garden', 'United Center',
              'Rogers Arena', 'Scotiabank Arena', 'Bell Centre',
              'Wells Fargo Center', 'Capital One Arena',
              'Amerant Bank Arena', 'Honda Center', 'PPG Paints Arena',
              'Ball Arena', 'Climate Pledge Arena', 'Xcel Energy Center']
NFL_VENUES = ['Arrowhead Stadium', 'AT&T Stadium', 'SoFi Stadium',
              'Lambeau Field', 'Lincoln Financial Field', 'M&T Bank Stadium',
              'Highmark Stadium', 'GEHA Field', 'MetLife Stadium',
              "Levi's Stadium", 'Empower Field at Mile High',
              'Hard Rock Stadium', 'NRG Stadium', 'State Farm Stadium']
MLB_VENUES = ['Yankee Stadium', 'Fenway Park', 'Dodger Stadium',
              'Wrigley Field', 'Oracle Park', 'Tropicana Field',
              'Citi Field', 'Petco Park', 'Coors Field',
              'Camden Yards', 'Globe Life Field', 'PNC Park', 'Truist Park',
              'Citizens Bank Park', 'Minute Maid Park']
SOCCER_VENUES = ['Emirates Stadium', 'Old Trafford', 'Anfield',
                 'Stamford Bridge', 'Etihad Stadium',
                 'Tottenham Hotspur Stadium', 'Camp Nou', 'Santiago Bernabéu',
                 'Allianz Arena', 'San Siro', 'Parc des Princes',
                 'Signal Iduna Park']
NCAAF_VENUES = ['Bryant-Denny Stadium', 'Ohio Stadium', 'The Big House',
                'Sanford Stadium', 'Beaver Stadium', 'Kyle Field',
                'Tiger Stadium', 'Neyland Stadium']
NCAAM_VENUES = ['Cameron Indoor Stadium', 'Allen Fieldhouse', 'Phog Allen',
                'Rupp Arena', 'Carrier Dome', 'Pauley Pavilion']


# ─── 1. Games (~1250 new) ────────────────────────────────────────────────────

def make_games(cur):
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM games") or 0) + 1
    rows = []
    teams = {}
    for sp in ('nba', 'nhl', 'mlb', 'nfl', 'soccer'):
        teams[sp] = cur.execute(
            "SELECT id, full_name, slug FROM teams "
            "WHERE sport_slug=? ORDER BY id", (sp,)).fetchall()
    ncaaf_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='ncaaf' "
        "ORDER BY id").fetchall()
    ncaam_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='ncaam' "
        "ORDER BY id").fetchall()

    def star_for(team_id):
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (team_id,)).fetchone()
        return row or ('Star Player', 'F')

    def emit(sport, season_label, t_arr, venues, start, count, hi_score,
             lo_score, base_off, network, period_label, status_default='final',
             scheduled_window=None):
        nonlocal next_id
        if not t_arr:
            return 0
        n = 0
        for i in range(count):
            a = h(f'r5-{sport}-{season_label}-a-{i}', len(t_arr))
            b = h(f'r5-{sport}-{season_label}-b-{i}', len(t_arr))
            if a == b:
                b = (b + 1) % len(t_arr)
            home = t_arr[a]
            away = t_arr[b]
            if scheduled_window:
                gdate = scheduled_window[0] + timedelta(
                    days=h(f'r5-{sport}-{season_label}-d-{i}',
                          scheduled_window[1]))
                status = 'scheduled'
                period = 'Scheduled'
                hs, as_ = 0, 0
                recap = f'{season_label} {away[1]} at {home[1]}.'
            else:
                gdate = start + timedelta(
                    days=h(f'r5-{sport}-{season_label}-d-{i}', 175))
                status = status_default
                period = period_label
                hs = h(f'r5-{sport}-{season_label}-hs-{i}', hi_score, lo_score)
                as_ = h(f'r5-{sport}-{season_label}-as-{i}', hi_score,
                        max(0, lo_score - base_off))
                recap = f'({season_label}) {home[1]} {hs}-{as_} {away[1]}.'
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
            }) if status != 'scheduled' else '{}'
            rows.append((
                next_id, sport, home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                f"{7 + (i % 4)}:{30 if i % 2 else '00'} PM ET",
                status, period, network, ven, recap,
                'https://www.ticketmaster.com', leaders))
            next_id += 1
            n += 1
        return n

    # NBA: 2023-24 full + 2024-25 schedule preview
    emit('nba', '2023-24', teams['nba'], NBA_VENUES,
         date(2023, 10, 24), 300, 35, 95, 8, 'ESPN', 'Final')
    emit('nba', '2024-25-prev', teams['nba'], NBA_VENUES,
         None, 80, 0, 0, 0, 'ESPN', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2024, 10, 22), 180))

    # NHL: 2023-24 full + 2024-25 preview
    emit('nhl', '2023-24', teams['nhl'], NHL_VENUES,
         date(2023, 10, 10), 250, 7, 1, 1, 'ESPN+', 'Final')
    emit('nhl', '2024-25-prev', teams['nhl'], NHL_VENUES,
         None, 50, 0, 0, 0, 'ESPN+', 'Scheduled',
         status_default='scheduled',
         scheduled_window=(date(2024, 10, 8), 190))

    # MLB: 2023 + 2024 early-season
    emit('mlb', '2023', teams['mlb'], MLB_VENUES,
         date(2023, 3, 30), 180, 14, 0, 0, 'MLB Network', 'Final')
    emit('mlb', '2024-early', teams['mlb'], MLB_VENUES,
         date(2024, 3, 28), 70, 12, 0, 0, 'MLB Network', 'Final')

    # NFL: 2022 full + 2023 full
    emit('nfl', '2022', teams['nfl'], NFL_VENUES,
         date(2022, 9, 8), 50, 31, 7, 6, 'FOX', 'Final')
    emit('nfl', '2023', teams['nfl'], NFL_VENUES,
         date(2023, 9, 7), 60, 35, 10, 7, 'CBS', 'Final')

    # Soccer: 2023-24 + Champions League knockout
    emit('soccer', '2023-24', teams['soccer'], SOCCER_VENUES,
         date(2023, 8, 11), 80, 5, 0, 0, 'ESPN+', 'FT')
    emit('soccer', '2023-24-ucl', teams['soccer'], SOCCER_VENUES,
         date(2023, 9, 19), 40, 5, 0, 0, 'Paramount+', 'FT')

    # NCAAF: 2023 season (small)
    if ncaaf_teams:
        emit('ncaaf', '2023', ncaaf_teams, NCAAF_VENUES,
             date(2023, 9, 2), 50, 50, 14, 10, 'ABC', 'Final')
    # NCAAM: 2023-24 (small)
    if ncaam_teams:
        emit('ncaam', '2023-24', ncaam_teams, NCAAM_VENUES,
             date(2023, 11, 6), 50, 90, 55, 8, 'CBS', 'Final')

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 2. Player stats (+1525) ─────────────────────────────────────────────────

def _make_stat_row(sport_slug, pid, pos, season, next_id):
    key = f'r5-{season}-{sport_slug}-{pid}'
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
            base.update({'passing_yards': h(f'{key}-pyd', 3800, 2200),
                         'passing_tds': h(f'{key}-ptd', 32, 12),
                         'rushing_yards': h(f'{key}-ryd', 400, 50),
                         'rushing_tds': h(f'{key}-rtd', 7, 0)})
        elif p == 'RB':
            base.update({'rushing_yards': h(f'{key}-ryd', 1200, 600),
                         'rushing_tds': h(f'{key}-rtd', 14, 3),
                         'receptions': h(f'{key}-rec', 60, 18),
                         'receiving_yards': h(f'{key}-recy', 600, 130)})
        elif p in ('WR', 'TE'):
            base.update({'receptions': h(f'{key}-rec', 90, 40),
                         'receiving_yards': h(f'{key}-recy', 1200, 500),
                         'receiving_tds': h(f'{key}-rectd', 12, 3)})
        else:
            base.update({'tackles': h(f'{key}-tck', 90, 35),
                         'sacks': round(hf(f'{key}-sk', 0.5, 14), 1)})
    elif sport_slug == 'mlb':
        if 'P' in (pos or ''):
            base.update({'era': round(hf(f'{key}-era', 2.4, 5.6), 2),
                         'strikeouts': h(f'{key}-so', 230, 60),
                         'wins_pitcher': h(f'{key}-wp', 18, 4)})
        else:
            base.update({'batting_avg': round(hf(f'{key}-ba', 0.21, 0.34), 3),
                         'home_runs': h(f'{key}-hr', 42, 4),
                         'rbi': h(f'{key}-rbi', 105, 25),
                         'stolen_bases': h(f'{key}-sb', 28, 1)})
    elif sport_slug == 'nhl':
        base.update({'goals': h(f'{key}-g', 45, 5),
                     'hockey_assists': h(f'{key}-a', 55, 8),
                     'hockey_points': h(f'{key}-pt', 90, 15),
                     'plus_minus': h(f'{key}-pm', 60, -25),
                     'penalty_minutes': h(f'{key}-pim', 90, 4)})
    elif sport_slug == 'soccer':
        base.update({'soccer_goals': h(f'{key}-sg', 22, 1),
                     'soccer_assists': h(f'{key}-sa', 14, 1),
                     'soccer_appearances': h(f'{key}-sap', 38, 8),
                     'yellow_cards': h(f'{key}-yc', 10, 0),
                     'red_cards': h(f'{key}-rc', 2, 0)})
    cols = list(base.keys())
    return (cols, [base[c] for c in cols])


def make_player_stats(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM player_stats") or 0) + 1
    rows = []
    season_quotas = [
        ('2023-24', {'nba': 220, 'nhl': 180}),
        ('2023',    {'nfl': 150, 'mlb': 170}),
        ('2024-25-projection', {'nba': 90, 'nhl': 80, 'nfl': 70, 'mlb': 70}),
        ('2018-19', {'nba': 80, 'nhl': 70, 'mlb': 70, 'nfl': 50}),
        ('2017-18', {'nba': 70, 'nhl': 60, 'mlb': 60}),
        ('2023-24-soccer', {'soccer': 90}),
        ('2022-23-fill', {'nba': 50, 'nhl': 40, 'mlb': 40, 'nfl': 30}),
    ]
    for season, quotas in season_quotas:
        for sport_slug, q in quotas.items():
            players = cur.execute(
                "SELECT id, name, position FROM players "
                "WHERE sport_slug=? ORDER BY id LIMIT ?",
                (sport_slug, q)).fetchall()
            for pid, _n, pos in players:
                row = _make_stat_row(sport_slug, pid, pos, season, next_id)
                rows.append(row)
                next_id += 1
    by_cols = {}
    for cols, vals in rows:
        by_cols.setdefault(tuple(cols), []).append(vals)
    inserted = 0
    for cols, batch in by_cols.items():
        placeholders = ','.join('?' * len(cols))
        sql = (f"INSERT INTO player_stats ({','.join(cols)}) "
               f"VALUES ({placeholders})")
        cur.executemany(sql, batch)
        inserted += len(batch)
    return inserted


# ─── 3. Play-by-play (+1900) ─────────────────────────────────────────────────

NBA_PBP = [
    ('made_3pt', '{actor} makes a 3-pointer from the corner'),
    ('made_2pt', '{actor} sinks a mid-range jumper'),
    ('made_layup', '{actor} drives baseline for the layup'),
    ('made_dunk', '{actor} throws down a tomahawk dunk'),
    ('missed_3pt', '{actor} misses a step-back 3'),
    ('missed_layup', '{actor} misses the contested layup'),
    ('off_rebound', '{actor} cleans up the offensive board'),
    ('def_rebound', '{actor} secures the defensive rebound'),
    ('assist', '{actor} delivers the assist'),
    ('steal', '{actor} picks the pocket on the perimeter'),
    ('block', '{actor} swats the shot away'),
    ('foul', 'Personal foul on {actor}'),
    ('ft_made', '{actor} hits both free throws'),
    ('turnover', '{actor} loses the handle'),
    ('timeout', 'Full timeout called by the bench'),
]
NHL_PBP = [
    ('goal', '{actor} buries the rebound'),
    ('shot', '{actor} fires from the slot, saved'),
    ('hit', '{actor} levels a hit in the corner'),
    ('takeaway', '{actor} steals the puck on the forecheck'),
    ('giveaway', '{actor} fumbles a clearing attempt'),
    ('penalty', 'Penalty on {actor} for hooking'),
    ('faceoff_won', '{actor} wins the faceoff cleanly'),
    ('save', 'Goalie pads aside a {actor} wrister'),
    ('power_play', 'Power play begins'),
    ('period_end', 'End of period'),
]
MLB_PBP = [
    ('single', '{actor} lines a single to left'),
    ('double', '{actor} doubles into the gap'),
    ('triple', '{actor} hustles for a triple'),
    ('homer', '{actor} sends one over the wall'),
    ('strikeout', '{actor} strikes out looking'),
    ('walk', '{actor} draws a four-pitch walk'),
    ('groundout', '{actor} grounds out to second'),
    ('flyout', '{actor} flies out to left'),
    ('stolen_base', '{actor} swipes second'),
    ('pickoff', 'Caught stealing on a pickoff'),
]
NFL_PBP = [
    ('pass_complete', '{actor} completes a pass for a first down'),
    ('pass_incomplete', '{actor} airs it out, incomplete'),
    ('rush', '{actor} rushes for a short gain'),
    ('rush_td', '{actor} bulldozes in for a touchdown'),
    ('pass_td', '{actor} hits the receiver for a TD strike'),
    ('sack', '{actor} brings down the quarterback'),
    ('interception', '{actor} jumps the route for an INT'),
    ('punt', 'Punt downed inside the 20'),
    ('field_goal', '{actor} drills the field goal'),
    ('penalty', 'Holding called on {actor}'),
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

    # Avoid replaying any game already in play_by_play.
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
        ('nba', 18, NBA_PBP, ['Q1', 'Q2', 'Q3', 'Q4'], 40),
        ('nhl', 14, NHL_PBP, ['1st', '2nd', '3rd'], 40),
        ('mlb', 10, MLB_PBP, ['T1', 'B1', 'T2', 'B2', 'T3', 'B3',
                              'T4', 'B4', 'T5', 'B5'], 30),
        ('nfl', 8, NFL_PBP, ['Q1', 'Q2', 'Q3', 'Q4'], 35),
    ]
    for sport, ngames, events, periods, ev_count in plan:
        games = pick_games(sport, ngames)
        for gid, sport_slug, hid, aid, fhs, fas in games:
            home_actors = actor_names(hid)
            away_actors = actor_names(aid)
            score_h = 0
            score_a = 0
            for seq in range(ev_count):
                key = f'r5-pbp-{sport}-{gid}-{seq}'
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
                                 'made_dunk', 'ft_made'):
                    inc_h, inc_a = (2, 0) if is_home else (0, 2)
                elif ev_type == 'goal':
                    inc_h, inc_a = (1, 0) if is_home else (0, 1)
                elif ev_type == 'homer':
                    inc_h, inc_a = (1, 0) if is_home else (0, 1)
                elif ev_type in ('rush_td', 'pass_td'):
                    inc_h, inc_a = (7, 0) if is_home else (0, 7)
                elif ev_type == 'field_goal':
                    inc_h, inc_a = (3, 0) if is_home else (0, 3)
                score_h = min(score_h + inc_h, fhs or 999)
                score_a = min(score_a + inc_a, fas or 999)
                period = periods[seq % len(periods)]
                minute = 11 - (seq % 12)
                second = (seq * 7) % 60
                clock = f'{minute:02d}:{second:02d}'
                rows.append((
                    next_id, gid, sport_slug, seq + 1, period, clock,
                    team_id, actor, ev_type, desc, score_h, score_a))
                next_id += 1

    cur.executemany(
        "INSERT INTO play_by_play (id, game_id, sport_slug, sequence, "
        "period, clock, team_id, actor_name, event_type, description, "
        "score_home, score_away) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 4. Podcasts (+110) ──────────────────────────────────────────────────────

R5_PODCAST_SEED = [
    # NBA team-specific
    ('Celtics Talk', 'celtics-talk', 'Chris Forsberg', 'nba',
     'Boston Celtics coverage from the NBC Sports Boston desk.', 540,
     'Tatum heat-check and rotation tweaks', '2024-04-11', 35),
    ('Locked On Lakers', 'locked-on-lakers', 'Pete Zayas', 'nba',
     'Daily Los Angeles Lakers podcast.', 1100, 'LeBron load management',
     '2024-04-11', 28),
    ('Locked On Warriors', 'locked-on-warriors', 'Jack Winter', 'nba',
     'Daily Golden State Warriors podcast.', 1050,
     'Curry returns from injury', '2024-04-11', 28),
    ('Locked On Knicks', 'locked-on-knicks', 'Alex Wolfe', 'nba',
     'Daily New York Knicks podcast.', 980, 'Brunson MVP push',
     '2024-04-10', 28),
    ('Locked On Heat', 'locked-on-heat', 'AJ LaBella', 'nba',
     'Daily Miami Heat podcast.', 920, 'Butler injury update',
     '2024-04-10', 28),
    ('Locked On Mavs', 'locked-on-mavs', 'Nick Angstadt', 'nba',
     'Daily Dallas Mavericks podcast.', 990, 'Doncic triple-double watch',
     '2024-04-10', 28),
    ('Locked On Nuggets', 'locked-on-nuggets', 'Adam Mares', 'nba',
     'Daily Denver Nuggets podcast.', 870, 'Jokic back-to-back MVP odds',
     '2024-04-10', 28),
    ('Locked On Suns', 'locked-on-suns', 'Brendon Kleen', 'nba',
     'Daily Phoenix Suns podcast.', 940, 'KD-Booker chemistry',
     '2024-04-10', 28),
    ('Locked On Bucks', 'locked-on-bucks', 'Jordan Treske', 'nba',
     'Daily Milwaukee Bucks podcast.', 910, 'Giannis MVP case',
     '2024-04-10', 28),
    ('Locked On 76ers', 'locked-on-76ers', 'Keith Pompey', 'nba',
     'Daily Philadelphia 76ers podcast.', 860, 'Embiid return timeline',
     '2024-04-10', 28),
    ('Locked On Sixers Plus', 'locked-on-sixers-plus', 'Dei Lynam', 'nba',
     'Bonus 76ers content.', 320, 'Maxey All-Star push',
     '2024-04-10', 24),
    ('Locked On Cavaliers', 'locked-on-cavaliers', 'Evan Dammarell', 'nba',
     'Daily Cleveland Cavaliers podcast.', 770, 'Mitchell extension chatter',
     '2024-04-10', 25),
    ('Locked On Pelicans', 'locked-on-pelicans', 'Jamal Madison', 'nba',
     'Daily New Orleans Pelicans podcast.', 660, 'Zion fitness update',
     '2024-04-09', 25),
    ('Locked On Thunder', 'locked-on-thunder', 'Rylan Stiles', 'nba',
     'Daily OKC Thunder podcast.', 720, 'SGA MVP odds',
     '2024-04-09', 25),
    # NFL team-specific
    ('Locked On Cowboys', 'locked-on-cowboys', 'Marcus Mosher', 'nfl',
     'Daily Dallas Cowboys podcast.', 1500, 'Dak contract talks',
     '2024-04-11', 28),
    ('Locked On 49ers', 'locked-on-49ers', 'Brian Peacock', 'nfl',
     'Daily San Francisco 49ers podcast.', 1450, 'Brock Purdy ceiling debate',
     '2024-04-11', 28),
    ('Locked On Chiefs', 'locked-on-chiefs', 'Ron Kopp', 'nfl',
     'Daily Kansas City Chiefs podcast.', 1480, 'Mahomes-Kelce drama',
     '2024-04-11', 28),
    ('Locked On Eagles', 'locked-on-eagles', 'Geoff Mosher', 'nfl',
     'Daily Philadelphia Eagles podcast.', 1380, 'Hurts MVP odds',
     '2024-04-11', 28),
    ('Locked On Ravens', 'locked-on-ravens', 'Spencer Schultz', 'nfl',
     'Daily Baltimore Ravens podcast.', 1290, 'Lamar leans on legs',
     '2024-04-11', 28),
    ('Locked On Bills', 'locked-on-bills', 'Joe Marino', 'nfl',
     'Daily Buffalo Bills podcast.', 1250, 'Allen receiver options',
     '2024-04-11', 28),
    ('Locked On Lions', 'locked-on-lions', 'Matt Dumas', 'nfl',
     'Daily Detroit Lions podcast.', 1100, 'Goff extension framework',
     '2024-04-11', 28),
    ('Locked On Packers', 'locked-on-packers', 'Peter Bukowski', 'nfl',
     'Daily Green Bay Packers podcast.', 1220, 'Love takes the next step',
     '2024-04-11', 28),
    ('Locked On Dolphins', 'locked-on-dolphins', 'Travis Wingfield', 'nfl',
     'Daily Miami Dolphins podcast.', 1180, 'Tua health check',
     '2024-04-10', 26),
    ('Locked On Jets', 'locked-on-jets', 'John Butchko', 'nfl',
     'Daily New York Jets podcast.', 1150, 'Rodgers Achilles update',
     '2024-04-10', 26),
    ('Locked On Patriots', 'locked-on-patriots', 'Mark Schofield', 'nfl',
     'Daily New England Patriots podcast.', 1430, 'Drake Maye fit',
     '2024-04-10', 26),
    ('Locked On Steelers', 'locked-on-steelers', 'Chris Carter', 'nfl',
     'Daily Pittsburgh Steelers podcast.', 1360, 'Russell Wilson reset',
     '2024-04-10', 26),
    ('Locked On Bears', 'locked-on-bears', 'Lorin Cox', 'nfl',
     'Daily Chicago Bears podcast.', 1310, 'Caleb Williams hype',
     '2024-04-10', 26),
    ('Locked On Vikings', 'locked-on-vikings', 'Drew Mahowald', 'nfl',
     'Daily Minnesota Vikings podcast.', 1140, 'Cousins replacement plan',
     '2024-04-10', 26),
    ('Locked On Saints', 'locked-on-saints', 'Ross Jackson', 'nfl',
     'Daily New Orleans Saints podcast.', 1080, 'Carr accuracy concerns',
     '2024-04-10', 26),
    ('Locked On Falcons', 'locked-on-falcons', 'Aaron Freeman', 'nfl',
     'Daily Atlanta Falcons podcast.', 1020, 'Cousins lands in ATL',
     '2024-04-10', 26),
    ('Locked On Buccaneers', 'locked-on-buccaneers',
     'Jenna Laine', 'nfl',
     'Daily Tampa Bay Buccaneers podcast.', 990, 'Mayfield bridge year',
     '2024-04-10', 26),
    ('Locked On Texans', 'locked-on-texans', 'David Weeks', 'nfl',
     'Daily Houston Texans podcast.', 960, 'CJ Stroud Year 2',
     '2024-04-10', 26),
    # MLB team-specific
    ('Locked On Yankees', 'locked-on-yankees', 'Stacey Gotsulias', 'mlb',
     'Daily New York Yankees podcast.', 1620,
     'Soto looks at home in pinstripes', '2024-04-11', 28),
    ('Locked On Dodgers', 'locked-on-dodgers', 'Doug McKain', 'mlb',
     'Daily Los Angeles Dodgers podcast.', 1480, 'Ohtani MVP heat',
     '2024-04-11', 28),
    ('Locked On Red Sox', 'locked-on-red-sox', 'Drew Bonifant', 'mlb',
     'Daily Boston Red Sox podcast.', 1280, 'Yoshida streak',
     '2024-04-10', 26),
    ('Locked On Mets', 'locked-on-mets', 'Matt Cassidy', 'mlb',
     'Daily New York Mets podcast.', 1190, 'Lindor leadoff experiment',
     '2024-04-10', 26),
    ('Locked On Cubs', 'locked-on-cubs', 'Ryan Brady', 'mlb',
     'Daily Chicago Cubs podcast.', 1150, 'Suzuki middle-of-the-order role',
     '2024-04-10', 26),
    ('Locked On Phillies', 'locked-on-phillies', 'Tim Kelly', 'mlb',
     'Daily Philadelphia Phillies podcast.', 1130, 'Wheeler ace season',
     '2024-04-10', 26),
    ('Locked On Braves', 'locked-on-braves', 'Brandon Stoughton', 'mlb',
     'Daily Atlanta Braves podcast.', 1170, 'Acuna jr. encore',
     '2024-04-10', 26),
    ('Locked On Astros', 'locked-on-astros', 'Brandon Stoneman', 'mlb',
     'Daily Houston Astros podcast.', 1140, 'Verlander start watch',
     '2024-04-10', 26),
    ('Locked On Rangers', 'locked-on-rangers', 'TR Sullivan', 'mlb',
     'Daily Texas Rangers podcast.', 1080, 'Seager bounce-back',
     '2024-04-10', 26),
    # NHL team-specific
    ('Locked On Bruins', 'locked-on-bruins', 'Mick Colageo', 'nhl',
     'Daily Boston Bruins podcast.', 820, 'Marchand captaincy',
     '2024-04-11', 24),
    ('Locked On Oilers', 'locked-on-oilers', 'Curtis Stock', 'nhl',
     'Daily Edmonton Oilers podcast.', 940, 'McDavid Hart Trophy lead',
     '2024-04-11', 24),
    ('Locked On Rangers NHL', 'locked-on-rangers-nhl', 'Dan Rosen',
     'nhl', 'Daily New York Rangers podcast.', 760,
     'Shesterkin Vezina case', '2024-04-11', 24),
    ('Locked On Maple Leafs', 'locked-on-maple-leafs',
     'Anthony Petrielli', 'nhl',
     'Daily Toronto Maple Leafs podcast.', 880, 'Matthews 70-goal chase',
     '2024-04-11', 24),
    ('Locked On Panthers', 'locked-on-panthers', 'Colby Guy', 'nhl',
     'Daily Florida Panthers podcast.', 710, 'Tkachuk leadership group',
     '2024-04-11', 24),
    ('Locked On Golden Knights', 'locked-on-golden-knights',
     'Brian Costello', 'nhl',
     'Daily Vegas Golden Knights podcast.', 690, 'Defending the Cup',
     '2024-04-10', 24),
    # Soccer team-specific
    ('Locked On Arsenal', 'locked-on-arsenal', 'Brad Crooks', 'soccer',
     'Daily Arsenal FC podcast.', 1280, 'Saka injury concerns',
     '2024-04-11', 30),
    ('Locked On Manchester City', 'locked-on-manchester-city',
     'Sam Lee', 'soccer',
     'Daily Manchester City podcast.', 1170, 'Haaland Golden Boot lead',
     '2024-04-11', 30),
    ('Locked On Liverpool', 'locked-on-liverpool', 'Caoimhe ORN', 'soccer',
     'Daily Liverpool FC podcast.', 1250, 'Klopp farewell run',
     '2024-04-11', 30),
    ('Locked On Real Madrid', 'locked-on-real-madrid',
     'Mario Cortegana', 'soccer',
     'Daily Real Madrid podcast.', 1120, 'Bellingham Ballon d\'Or push',
     '2024-04-11', 30),
    ('Locked On Barcelona', 'locked-on-barcelona', 'Jose Alvarez',
     'soccer', 'Daily FC Barcelona podcast.', 1080, 'Lewandowski form',
     '2024-04-11', 30),
    # Topic shows
    ('Fantasy Focus Hoops', 'fantasy-focus-hoops', 'Jim McCormick',
     'fantasy', 'NBA fantasy basketball deep dives.', 380,
     'Punt-FT% league strategies', '2024-04-11', 40),
    ('Fantasy Focus Baseball', 'fantasy-focus-baseball',
     'Tristan H. Cockcroft', 'fantasy',
     'MLB fantasy baseball strategy show.', 410,
     'Early-season SP scoop', '2024-04-11', 40),
    ('Fantasy Focus Hockey', 'fantasy-focus-hockey', 'Sean Allen',
     'fantasy', 'Fantasy hockey roundtable.', 360,
     'Power-play QB sleeper picks', '2024-04-11', 40),
    ('Bet Sweats', 'bet-sweats', 'Doug Kezirian', 'fantasy',
     'Live betting reactions and bad-beat stories.', 240,
     'Sweating a 3-team teaser', '2024-04-11', 35),
    ('Daily Wager Pod', 'daily-wager-pod', 'Tyler Fulghum', 'fantasy',
     'ESPN BET daily picks pod.', 460, 'Tonight\'s top three plays',
     '2024-04-11', 30),
    ('Wright Thompson Reads', 'wright-thompson-reads',
     'Wright Thompson', 'nfl', 'Long-form ESPN feature reads.', 60,
     'A Sunday in the South', '2024-04-09', 60),
    ('Around the Horn Pod', 'around-the-horn-pod', 'Tony Reali', 'nba',
     'Daily debate roundtable companion.', 2200,
     'PTI rivals on Caitlin Clark', '2024-04-11', 28),
    ('Pardon My Take Sat', 'pardon-my-take-sat',
     'Big Cat and PFT', 'nfl',
     'Saturday hot-take edition.', 320, 'Mt. Rushmore of mascots',
     '2024-04-13', 60),
    ('NBA Draft Pod', 'nba-draft-pod', 'Mike Schmitz', 'nba',
     'Pre-draft scouting and mock draft show.', 130,
     'Lottery mock draft 4.0', '2024-04-11', 50),
    ('NFL Draft Pod', 'nfl-draft-pod', 'Field Yates', 'nfl',
     'Pre-draft scouting and trade chatter.', 145,
     'QB1 debate revisited', '2024-04-11', 55),
    ('Bracketology Pod', 'bracketology-pod', 'Joe Lunardi', 'ncaam',
     'Weekly Bracketology breakdown.', 95,
     'First Four bubble watch', '2024-04-08', 35),
    ('Recruiting Insider Pod', 'recruiting-insider-pod',
     'Tom VanHaaren', 'ncaaf',
     '247 composite recruiting deep dives.', 110,
     'Top-100 visit weekend recap', '2024-04-09', 40),
    ('Power Rankings Pod', 'power-rankings-pod', 'ESPN Insiders', 'nba',
     'Weekly power rankings discussion.', 80, 'Top tier tightens',
     '2024-04-09', 30),
    ('30 for 30 Pod Season X', '30-for-30-pod-season-x',
     'ESPN Films', 'nba',
     'Latest season of the 30 for 30 podcast.', 22, 'Episode 6 dropped',
     '2024-04-08', 55),
    ('UFC Unfiltered', 'ufc-unfiltered', 'Jim Norton', 'mma',
     'Weekly UFC card preview show.', 230, 'Pay-per-view headliner',
     '2024-04-10', 50),
    ('The PGA Tour Pod', 'pga-tour-pod', 'Brent Sobleski', 'golf',
     'Weekly PGA Tour event preview.', 145, 'Masters preview',
     '2024-04-08', 45),
    ('Tennis Talk Tonight', 'tennis-talk-tonight', 'Brad Gilbert',
     'tennis', 'ATP/WTA weekly recap.', 95, 'Clay-court tune-ups',
     '2024-04-09', 35),
    ('Pac-12 Apocalypse Pod', 'pac-12-apocalypse-pod',
     'Pat Forde', 'ncaaf', 'Conference realignment fallout.', 40,
     'Big Ten welcomes the West', '2024-04-08', 45),
    ('Champions League Daily', 'champions-league-daily',
     'Gab Marcotti', 'soccer',
     'Daily UCL recap during the knockout rounds.', 60,
     'Quarterfinals first leg recap', '2024-04-10', 35),
    ('La Liga Daily', 'la-liga-daily', 'Sid Lowe', 'soccer',
     'Daily La Liga recap.', 90, 'Title-race tightens',
     '2024-04-10', 30),
    ('Serie A Daily', 'serie-a-daily', 'James Horncastle', 'soccer',
     'Daily Serie A recap.', 80, 'Champions League race',
     '2024-04-10', 30),
    ('Bundesliga Daily', 'bundesliga-daily', 'Raphael Honigstein',
     'soccer', 'Daily Bundesliga recap.', 75, 'Top-four tightens',
     '2024-04-10', 30),
    ('Premier League Daily', 'premier-league-daily',
     'Jonathan Wilson', 'soccer',
     'Daily Premier League recap.', 110, 'Title-race three-way tie',
     '2024-04-11', 30),
    ('Marty & McGee', 'marty-and-mcgee', 'Marty Smith', 'ncaaf',
     'College football and culture show.', 280, 'Spring practice tour',
     '2024-04-09', 45),
    ('Game Day Greats', 'game-day-greats', 'Kirk Herbstreit', 'ncaaf',
     'College football GameDay companion pod.', 195,
     'Top-25 spring snapshot', '2024-04-09', 50),
    ('NFL Live Pod', 'nfl-live-pod', 'Marcus Spears', 'nfl',
     'Companion to the NFL Live TV show.', 220,
     'Combine takeaways', '2024-04-11', 30),
    ('NBA Today Pod', 'nba-today-pod', 'Malika Andrews', 'nba',
     'Companion to the NBA Today TV show.', 240,
     'MVP conversation refresh', '2024-04-11', 30),
    ('SportsCenter All Night', 'sportscenter-all-night',
     'Scott Van Pelt', 'nba',
     'Late-night SportsCenter highlight pod.', 320, 'One Big Thing tonight',
     '2024-04-11', 28),
    ('Get Up Pod', 'get-up-pod', 'Mike Greenberg', 'nfl',
     'Morning show companion pod.', 410, 'Today\'s top stories',
     '2024-04-11', 35),
    ('The Right Time', 'the-right-time', 'Bomani Jones', 'nba',
     'Bomani\'s weekly cultural take show.', 280,
     'NBA narrative deconstruction', '2024-04-09', 50),
    ('Lowe Post Friday', 'lowe-post-friday', 'Zach Lowe', 'nba',
     'End-of-week mailbag edition of The Lowe Post.', 380,
     'Mailbag: playoff seeding edition', '2024-04-12', 60),
    ('Hoop Collective Friday', 'hoop-collective-friday',
     'Brian Windhorst', 'nba',
     'Friday wrap of the Hoop Collective.', 220,
     'Western Conference final mock', '2024-04-12', 50),
    ('First Take Live', 'first-take-live', 'Stephen A. Smith', 'nba',
     'Live debate audio simulcast.', 1100, 'LeBron vs MJ revisited',
     '2024-04-11', 60),
    ('The Skipper Show', 'the-skipper-show', 'Skip Bayless', 'nfl',
     'Cross-sport opinion show.', 280, 'Cowboys offseason rant',
     '2024-04-10', 45),
    ('Daily Spread', 'daily-spread', 'Joe Fortenbaugh', 'fantasy',
     'Daily betting card breakdown.', 360, 'Tonight\'s NBA card',
     '2024-04-11', 25),
    ('Fantasy Football Now',
     'fantasy-football-now', 'Field Yates', 'fantasy',
     'Sunday-morning fantasy football setup show.', 165,
     'Week 1 of the simulated season', '2024-04-07', 40),
    ('Players Only', 'players-only', 'Eddie House', 'nba',
     'Former players analyze each night\'s games.', 140,
     'Three-point shooting trends', '2024-04-09', 40),
    ('Coach K Pod', 'coach-k-pod', 'Mike Krzyzewski', 'ncaam',
     'Hall of Fame coach roundtable.', 65, 'Final Four lessons',
     '2024-04-08', 50),
    ('Diamond Talk', 'diamond-talk', 'Buster Olney', 'mlb',
     'Mid-week MLB roundtable.', 210, 'Cy Young early returns',
     '2024-04-10', 35),
    ('Goalie Talk', 'goalie-talk', 'Kevin Weekes', 'nhl',
     'Weekly goalie-centric roundup.', 95, 'Save-share leaderboard',
     '2024-04-09', 30),
    ('Soccer Insider Pod', 'soccer-insider-pod',
     'Herculez Gomez', 'soccer',
     'Weekly transfer rumors and tactical talk.', 180,
     'Top-five summer windows', '2024-04-10', 40),
    ('March Madness Vault', 'march-madness-vault', 'ESPN Films',
     'ncaam', 'Throwback NCAA tournament moments.', 35,
     'Cinderella stories revisited', '2024-04-08', 40),
    ('Hot Stove Pod', 'hot-stove-pod', 'Jeff Passan', 'mlb',
     'Offseason MLB rumors and signings.', 60, 'Free-agent dominoes fall',
     '2024-04-08', 35),
    ('Combine Confidential', 'combine-confidential',
     'Daniel Jeremiah', 'nfl',
     'Inside the NFL Scouting Combine.', 35, 'Workout warriors',
     '2024-04-08', 50),
    ('Trade Deadline Pod', 'trade-deadline-pod',
     'Bobby Marks', 'nba',
     'NBA trade-deadline analysis.', 40, 'Salary-cap aprons',
     '2024-04-09', 45),
    ('Fantasy Hockey Tonight',
     'fantasy-hockey-tonight', 'Victoria Matiash', 'fantasy',
     'Nightly fantasy hockey streaming targets.', 320,
     'Goalie streamer alerts', '2024-04-11', 25),
    ('Watch List Pod', 'watch-list-pod', 'ESPN+ Editors', 'watch',
     'Weekly ESPN+ exclusive content highlights.', 80,
     'New 30 for 30 episode', '2024-04-09', 30),
    ('ESPN BET Weekly', 'espn-bet-weekly', 'Erin Dolan', 'fantasy',
     'Weekly ESPN BET wrap-up and best bets.', 75,
     'Top parlays of the week', '2024-04-12', 40),
    ('NHL Power Play Pod', 'nhl-power-play-pod', 'Greg Wyshynski',
     'nhl', 'Weekly NHL roundup.', 410, 'Goalie controversies',
     '2024-04-10', 50),
    ('Pickleball Pod', 'pickleball-pod', 'Anna Leigh Waters', 'tennis',
     'Pickleball mainstreaming coverage.', 25, 'PPA tour stop recap',
     '2024-04-09', 30),
    ('Around the NFL', 'around-the-nfl-espn', 'Dan Hanzus', 'nfl',
     'ESPN-adjacent NFL roundup.', 1500, 'Quarterback movement',
     '2024-04-11', 60),
    ('NCAA Tournament Daily',
     'ncaa-tournament-daily', 'Andy Katz', 'ncaam',
     'Daily NCAA tournament show during March.', 60,
     'Final Four set', '2024-04-07', 35),
    ('Bracket Voices', 'bracket-voices', 'Charlie Creme', 'ncaaw',
     'Women\'s tournament daily pod.', 45, 'Final Four set',
     '2024-04-07', 30),
    ('Caitlin Clark Watch', 'caitlin-clark-watch',
     'Holly Rowe', 'ncaaw',
     'Caitlin Clark season-long pod.', 30, 'NCAA records broken',
     '2024-04-07', 40),
    ('UFC Insider Pod', 'ufc-insider-pod', 'Brett Okamoto', 'mma',
     'UFC insider and pre-card analysis.', 165,
     'Pay-per-view headliner storylines', '2024-04-09', 45),
    ('Boxing Beat', 'boxing-beat', 'Mike Coppinger', 'mma',
     'Weekly boxing card preview.', 80, 'Pound-for-pound rankings',
     '2024-04-09', 40),
    ('Power Index Pod', 'power-index-pod',
     'Seth Walder', 'nfl', 'FPI deep dives and weekly forecasts.', 90,
     'Week 1 simulations', '2024-04-08', 45),
    ('Football Power Index Live',
     'football-power-index-live', 'Aaron Schatz', 'nfl',
     'Live FPI roundtable during the season.', 60,
     'Toughest schedules ranked', '2024-04-08', 40),
    ('NBA Today Friday', 'nba-today-friday', 'Malika Andrews', 'nba',
     'Friday wrap of NBA Today.', 90, 'Awards ballot debate',
     '2024-04-12', 30),
    ('NFL Insider Pod', 'nfl-insider-pod', 'Adam Schefter', 'nfl',
     'Schefter\'s insider conversations.', 360,
     'Free agency aftermath', '2024-04-11', 35),
    ('Tennis Channel ESPN Crossover',
     'tennis-channel-espn-crossover', 'Pam Shriver', 'tennis',
     'Joint coverage of Grand Slams.', 50, 'Roland Garros preview',
     '2024-04-09', 30),
    ('SEC Daily Pod', 'sec-daily-pod', 'Paul Finebaum', 'ncaaf',
     'Companion to the Paul Finebaum show.', 410,
     'Spring practice tour', '2024-04-09', 50),
]


def make_podcasts(cur):
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM podcasts") or 0) + 1
    rows = []
    for i, (title, slug, host, sport_slug, description, eps,
            latest_title, latest_date, dur) in enumerate(R5_PODCAST_SEED):
        rows.append((next_id + i, title, slug, host, sport_slug,
                     description, eps, latest_title, latest_date, dur))
    cur.executemany(
        "INSERT INTO podcasts (id, title, slug, host, sport_slug, "
        "description, episode_count, latest_episode_title, "
        "latest_episode_date, duration_minutes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R5 extension already applied — no-op.')
        conn.close()
        return
    n_gm  = make_games(cur)
    n_st  = make_player_stats(cur)
    n_pbp = make_play_by_play(cur)
    n_pc  = make_podcasts(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R5 inserted: games={n_gm}, player_stats={n_st}, '
          f'play_by_play={n_pbp}, podcasts={n_pc}')


if __name__ == '__main__':
    main()
