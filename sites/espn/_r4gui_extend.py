#!/usr/bin/env python3
"""R4 GUI extension for sites/espn — fantasy lineup / waiver / trade tables.

Adds the data backing the new R4 GUI surface (lineup builder, waiver wire
window, trade analyzer, head-to-head matchup) on top of the live seed DB.

Strict gotcha #14 compliance: writes directly via sqlite3 INSERTs into
instance_seed/espn.db, never via SQLAlchemy / from app import.

Determinism: every value derived from md5 of a stable key. Re-running the
script is a no-op (gated on `_r4gui_marker` row in `sports`). After insert
we drop+recreate all ix_* indexes in sorted order, then VACUUM, so two
clean runs produce byte-identical DBs.
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
        "SELECT 1 FROM sports WHERE slug='_r4gui_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (130, 'R4 GUI marker', '_r4gui_marker', 'r4 gui applied',
         '/_internal/', 130, 0))


def slugify(text: str) -> str:
    out = (text.lower().replace("'", '').replace('"', '').replace('&', 'and')
           .replace('.', '').replace(',', '').replace('?', '')
           .replace(':', '').replace('/', '-').replace('—', '-')
           .replace(' ', '-'))
    out = ''.join(c for c in out if c.isalnum() or c == '-')
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')


# ─── Tables ──────────────────────────────────────────────────────────────────

NEW_TABLES = [
    """CREATE TABLE IF NOT EXISTS r4_fantasy_leagues (
        id INTEGER PRIMARY KEY,
        slug VARCHAR(60) NOT NULL,
        name VARCHAR(120),
        sport_slug VARCHAR(10),
        season VARCHAR(20),
        league_size INTEGER,
        scoring_type VARCHAR(20),
        roster_size INTEGER,
        current_week INTEGER,
        is_public INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS r4_fantasy_teams (
        id INTEGER PRIMARY KEY,
        league_id INTEGER NOT NULL,
        slug VARCHAR(60),
        team_name VARCHAR(120),
        manager_name VARCHAR(120),
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        ties INTEGER DEFAULT 0,
        points_for FLOAT DEFAULT 0,
        points_against FLOAT DEFAULT 0,
        rank INTEGER,
        waiver_priority INTEGER,
        moves_used INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS r4_fantasy_lineups (
        id INTEGER PRIMARY KEY,
        team_id INTEGER NOT NULL,
        week INTEGER,
        slot VARCHAR(10),
        player_id INTEGER,
        player_name VARCHAR(150),
        player_team VARCHAR(60),
        nfl_team_abbr VARCHAR(8),
        opponent VARCHAR(60),
        projected_points FLOAT,
        actual_points FLOAT,
        is_starter INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS r4_fantasy_waiver_claims (
        id INTEGER PRIMARY KEY,
        league_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        slug VARCHAR(80),
        add_player_id INTEGER,
        add_player_name VARCHAR(150),
        add_player_pos VARCHAR(10),
        drop_player_id INTEGER,
        drop_player_name VARCHAR(150),
        drop_player_pos VARCHAR(10),
        bid_amount INTEGER,
        priority INTEGER,
        status VARCHAR(20),
        process_date VARCHAR(20)
    )""",
    """CREATE TABLE IF NOT EXISTS r4_fantasy_trades (
        id INTEGER PRIMARY KEY,
        league_id INTEGER NOT NULL,
        slug VARCHAR(80),
        team_a_id INTEGER,
        team_b_id INTEGER,
        players_a_json TEXT,
        players_b_json TEXT,
        value_a FLOAT,
        value_b FLOAT,
        status VARCHAR(20),
        proposed_date VARCHAR(20),
        note VARCHAR(255)
    )""",
    """CREATE TABLE IF NOT EXISTS r4_fantasy_matchups (
        id INTEGER PRIMARY KEY,
        league_id INTEGER NOT NULL,
        week INTEGER,
        team_a_id INTEGER,
        team_b_id INTEGER,
        score_a FLOAT,
        score_b FLOAT,
        projected_a FLOAT,
        projected_b FLOAT,
        winner_team_id INTEGER,
        is_final INTEGER DEFAULT 0
    )""",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_leagues_slug ON r4_fantasy_leagues (slug)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_leagues_sport_slug ON r4_fantasy_leagues (sport_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_teams_league_id ON r4_fantasy_teams (league_id)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_teams_slug ON r4_fantasy_teams (slug)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_lineups_team_id ON r4_fantasy_lineups (team_id)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_lineups_week ON r4_fantasy_lineups (week)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_waiver_claims_league_id ON r4_fantasy_waiver_claims (league_id)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_waiver_claims_team_id ON r4_fantasy_waiver_claims (team_id)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_waiver_claims_slug ON r4_fantasy_waiver_claims (slug)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_trades_league_id ON r4_fantasy_trades (league_id)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_trades_slug ON r4_fantasy_trades (slug)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_matchups_league_id ON r4_fantasy_matchups (league_id)",
    "CREATE INDEX IF NOT EXISTS ix_r4_fantasy_matchups_week ON r4_fantasy_matchups (week)",
]


def create_tables(cur):
    for sql in NEW_TABLES:
        cur.execute(sql)


def normalize(cur):
    """Drop+recreate every ix_* index in sorted order — yields byte-identical DB."""
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── Fantasy NFL roster slots ───────────────────────────────────────────────
NFL_SLOTS = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'DST', 'K']
NBA_SLOTS = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL1', 'UTIL2']
MLB_SLOTS = ['C', '1B', '2B', '3B', 'SS', 'OF1', 'OF2', 'OF3', 'SP1', 'SP2', 'RP']

LEAGUE_NAMES_NFL = [
    'Sunday Funday', 'Touchdown Titans', 'Gridiron Gladiators',
    'Pigskin Prophets', 'End Zone Elite', 'Hail Mary Heroes',
    'Red Zone Renegades', 'Fourth & Long', 'Field Goal Fanatics',
    'Blitz Brigade', 'Pocket Passers', 'Two Minute Drill',
]
LEAGUE_NAMES_NBA = [
    'Hardwood Heroes', 'Hoop Dreams', 'Pick & Roll',
    'Triple Double Club', 'Buzzer Beaters', 'Court Vision',
]
LEAGUE_NAMES_MLB = [
    'Bases Loaded', 'Grand Slam Society', 'Strikeout Kings',
    'Diamond Dynasty', 'Bullpen Bandits',
]

MANAGER_NAMES = [
    'Alice Johnson', 'Bob Chen', 'Carol Davis', 'David Kim',  # benchmark users
    'Ethan Rivera', 'Fiona Park', 'Grace Liu', 'Henry Walsh',
    'Isabella Cruz', 'Jasper Mehta', 'Kayla Nguyen', 'Liam Carter',
    'Maya Sullivan', 'Noah Bennett', 'Olivia Foster', 'Paulo Reyes',
    'Quinn Hayes', 'Ravi Patel', 'Sienna Brooks', 'Tomas Vega',
    'Uma Singh', 'Vivian Chen', 'Wesley Owens', 'Xander Hill',
]

TEAM_NAME_ADJECTIVES = ['Mighty', 'Crimson', 'Iron', 'Silver', 'Thunder',
                         'Royal', 'Wild', 'Steel', 'Phantom', 'Lightning',
                         'Velvet', 'Obsidian']
TEAM_NAME_NOUNS = ['Stallions', 'Bandits', 'Vipers', 'Crusaders', 'Hawks',
                    'Reapers', 'Wolves', 'Outlaws', 'Surge', 'Comets',
                    'Sentinels', 'Pirates']


def make_leagues(cur):
    """Create 12 fantasy leagues across NFL/NBA/MLB."""
    rows = []
    league_id = 1
    for sport, names, scoring, size in [
            ('nfl', LEAGUE_NAMES_NFL, 'PPR', 12),
            ('nba', LEAGUE_NAMES_NBA, 'Category', 10),
            ('mlb', LEAGUE_NAMES_MLB, 'Roto', 10)]:
        for nm in names:
            slug = slugify(nm) + f'-{sport}'
            roster_size = {'nfl': 16, 'nba': 13, 'mlb': 21}[sport]
            cur_week = {'nfl': 14, 'nba': 22, 'mlb': 8}[sport]
            rows.append((league_id, slug, nm, sport, '2023-24',
                         size, scoring, roster_size, cur_week, 1))
            league_id += 1
    cur.executemany(
        "INSERT INTO r4_fantasy_leagues (id, slug, name, sport_slug, "
        "season, league_size, scoring_type, roster_size, current_week, "
        "is_public) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def make_teams(cur):
    """Create 10-12 fantasy teams per league. Benchmark users (Alice/Bob/Carol/David)
    each manage exactly ONE team in each league — used for disambiguation tasks."""
    leagues = cur.execute(
        "SELECT id, sport_slug, league_size FROM r4_fantasy_leagues "
        "ORDER BY id").fetchall()
    rows = []
    team_id = 1
    for lid, sport, size in leagues:
        for i in range(size):
            mgr_idx = h(f'r4-mgr-{lid}-{i}', len(MANAGER_NAMES))
            mgr = MANAGER_NAMES[mgr_idx]
            # Ensure first 4 slots in every league go to benchmark users
            if i < 4:
                mgr = MANAGER_NAMES[i]
            adj = TEAM_NAME_ADJECTIVES[h(f'r4-adj-{lid}-{i}',
                                          len(TEAM_NAME_ADJECTIVES))]
            noun = TEAM_NAME_NOUNS[h(f'r4-noun-{lid}-{i}',
                                       len(TEAM_NAME_NOUNS))]
            tname = f'{adj} {noun}'
            slug = slugify(tname) + f'-l{lid}-t{i+1}'
            wins = h(f'r4-w-{lid}-{i}', 12)
            losses = h(f'r4-l-{lid}-{i}', 12)
            ties = 0
            pf = round(hf(f'r4-pf-{lid}-{i}', 800.0, 1850.0), 2)
            pa = round(hf(f'r4-pa-{lid}-{i}', 800.0, 1850.0), 2)
            rank = i + 1
            wp = (i + 7) % size + 1  # rotating waiver priority
            moves = h(f'r4-mv-{lid}-{i}', 15)
            rows.append((team_id, lid, slug, tname, mgr, wins, losses, ties,
                         pf, pa, rank, wp, moves))
            team_id += 1
    cur.executemany(
        "INSERT INTO r4_fantasy_teams (id, league_id, slug, team_name, "
        "manager_name, wins, losses, ties, points_for, points_against, "
        "rank, waiver_priority, moves_used) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows)
    return len(rows)


def make_lineups(cur):
    """For each fantasy team, build a starting lineup using real players from
    the players table. Week is the league's current_week."""
    rows = []
    lineup_id = 1
    leagues = {row[0]: row for row in cur.execute(
        "SELECT id, sport_slug, current_week FROM r4_fantasy_leagues").fetchall()}
    teams = cur.execute(
        "SELECT id, league_id FROM r4_fantasy_teams ORDER BY id").fetchall()

    # Cache players per sport+position to avoid repeated SELECTs
    players_by = {}
    for sport, slots in [('nfl', NFL_SLOTS), ('nba', NBA_SLOTS),
                          ('mlb', MLB_SLOTS)]:
        # Map slot → list of positions to draw from
        slot_pos = {
            'QB': ['QB'], 'RB1': ['RB'], 'RB2': ['RB'],
            'WR1': ['WR'], 'WR2': ['WR'], 'TE': ['TE'],
            'FLEX': ['RB', 'WR', 'TE'], 'K': ['K'], 'DST': ['DST'],
            'PG': ['PG'], 'SG': ['SG'], 'SF': ['SF'], 'PF': ['PF'],
            'C': ['C'], 'G': ['PG', 'SG'], 'F': ['SF', 'PF'],
            'UTIL1': ['PG', 'SG', 'SF', 'PF', 'C'],
            'UTIL2': ['PG', 'SG', 'SF', 'PF', 'C'],
            '1B': ['1B', 'C'], '2B': ['2B', 'C'], '3B': ['3B', 'C'],
            'SS': ['SS', 'C'], 'OF1': ['OF', 'CF', 'LF', 'RF'],
            'OF2': ['OF', 'CF', 'LF', 'RF'],
            'OF3': ['OF', 'CF', 'LF', 'RF'],
            'SP1': ['SP', 'P'], 'SP2': ['SP', 'P'], 'RP': ['RP', 'P', 'CL'],
        }
        for slot in slots:
            positions = slot_pos.get(slot, ['UTIL'])
            placeholders = ','.join(['?'] * len(positions))
            sql = (f"SELECT id, name, position, team_id FROM players "
                   f"WHERE sport_slug=? AND position IN ({placeholders}) "
                   f"ORDER BY id")
            pl = cur.execute(sql, (sport,) + tuple(positions)).fetchall()
            players_by[(sport, slot)] = pl

    # team abbreviations
    team_abbr = {row[0]: row[1] for row in cur.execute(
        "SELECT id, abbreviation FROM teams").fetchall()}
    team_name = {row[0]: row[1] for row in cur.execute(
        "SELECT id, full_name FROM teams").fetchall()}

    OPPONENTS = {
        'nfl': ['vs CHI', 'vs DAL', '@PHI', '@SF', 'vs MIA', '@KC',
                'vs LAR', '@DEN', 'vs GB', '@NYJ'],
        'nba': ['vs LAL', 'vs BOS', '@DEN', 'vs MIA', '@MIL',
                'vs OKC', '@PHX', 'vs DAL'],
        'mlb': ['vs NYY', 'vs LAD', '@HOU', 'vs BOS', '@PHI',
                'vs ATL', '@CHC'],
    }

    for tid, lid in teams:
        sport, week = leagues[lid][1], leagues[lid][2]
        slots = {'nfl': NFL_SLOTS, 'nba': NBA_SLOTS,
                 'mlb': MLB_SLOTS}[sport]
        for slot in slots:
            pool = players_by.get((sport, slot), [])
            if not pool:
                # Fallback: any player from sport
                pool = cur.execute(
                    "SELECT id, name, position, team_id FROM players "
                    "WHERE sport_slug=? ORDER BY id LIMIT 200",
                    (sport,)).fetchall()
            idx = h(f'r4-lineup-{tid}-{slot}', len(pool))
            pid, pname, ppos, p_tid = pool[idx]
            if slot == 'DST':
                # Defense is a team, not a player
                tids = list(team_abbr.keys())
                idx2 = h(f'r4-dst-{tid}', len(tids))
                p_tid = tids[idx2]
                pname = (team_name.get(p_tid, 'D/ST') or 'D/ST') + ' D/ST'
                pid = None
            abbr = (team_abbr.get(p_tid, '—') or '—')
            opp_list = OPPONENTS[sport]
            opp = opp_list[h(f'r4-opp-{tid}-{slot}', len(opp_list))]
            # Projected points: deterministic
            proj_base = {'QB': 22, 'RB1': 14, 'RB2': 11, 'WR1': 13,
                          'WR2': 10, 'TE': 8, 'FLEX': 9, 'K': 7, 'DST': 7,
                          'PG': 38, 'SG': 33, 'SF': 32, 'PF': 30,
                          'C': 36, 'G': 34, 'F': 31, 'UTIL1': 28,
                          'UTIL2': 26,
                          '1B': 6, '2B': 5, '3B': 5, 'SS': 5,
                          'OF1': 6, 'OF2': 5, 'OF3': 5,
                          'SP1': 8, 'SP2': 7, 'RP': 4}.get(slot, 8)
            proj = round(proj_base + hf(f'r4-proj-{tid}-{slot}',
                                          -4.0, 8.0), 2)
            actual = round(proj + hf(f'r4-act-{tid}-{slot}', -6.0, 8.0), 2)
            rows.append((lineup_id, tid, week, slot, pid, pname,
                         team_name.get(p_tid, ''), abbr, opp, proj, actual, 1))
            lineup_id += 1
    cur.executemany(
        "INSERT INTO r4_fantasy_lineups (id, team_id, week, slot, "
        "player_id, player_name, player_team, nfl_team_abbr, opponent, "
        "projected_points, actual_points, is_starter) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def make_waiver_claims(cur):
    """3-4 pending waiver claims per league. Status = 'pending', 'awarded',
    'failed'. Benchmark users (Alice, Bob, Carol, David) each have ≥1 PENDING
    claim in their primary league — supports disambiguation."""
    rows = []
    claim_id = 1
    leagues = cur.execute(
        "SELECT id, sport_slug FROM r4_fantasy_leagues ORDER BY id").fetchall()

    players_by_sport = {}
    for sport in ('nfl', 'nba', 'mlb'):
        players_by_sport[sport] = cur.execute(
            "SELECT id, name, position FROM players WHERE sport_slug=? "
            "ORDER BY id", (sport,)).fetchall()

    for lid, sport in leagues:
        teams = cur.execute(
            "SELECT id, manager_name FROM r4_fantasy_teams "
            "WHERE league_id=? ORDER BY id", (lid,)).fetchall()
        n_claims = h(f'r4-wn-{lid}', 4, 4)  # 4-7 per league
        pl = players_by_sport[sport]
        for i in range(n_claims):
            tidx = h(f'r4-wt-{lid}-{i}', len(teams))
            tid, mgr = teams[tidx]
            pa = pl[h(f'r4-wa-{lid}-{i}', len(pl))]
            pd = pl[h(f'r4-wd-{lid}-{i}', len(pl))]
            bid = h(f'r4-wb-{lid}-{i}', 80, 1)
            prio = (i % 10) + 1
            status_pool = ['pending', 'pending', 'awarded', 'failed']
            status = status_pool[h(f'r4-ws-{lid}-{i}', len(status_pool))]
            # Force first 4 leagues' first 4 claims (one per benchmark user)
            # to PENDING for disambiguation reliability
            if i < 4:
                # Assign claim's team to the i-th benchmark user's team in this league
                btid, bmgr = teams[i]
                tid, mgr = btid, bmgr
                status = 'pending'
            proc_date = '2024-04-10'
            slug = f'l{lid}-c{claim_id}'
            rows.append((claim_id, lid, tid, slug,
                         pa[0], pa[1], pa[2],
                         pd[0], pd[1], pd[2],
                         bid, prio, status, proc_date))
            claim_id += 1
    cur.executemany(
        "INSERT INTO r4_fantasy_waiver_claims (id, league_id, team_id, slug, "
        "add_player_id, add_player_name, add_player_pos, drop_player_id, "
        "drop_player_name, drop_player_pos, bid_amount, priority, status, "
        "process_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def make_trades(cur):
    """Multi-player trade proposals. Each league has 2-3 trades — at least one
    proposed BY a benchmark user, one proposed TO a benchmark user."""
    rows = []
    trade_id = 1
    leagues = cur.execute(
        "SELECT id, sport_slug FROM r4_fantasy_leagues ORDER BY id").fetchall()
    for lid, sport in leagues:
        teams = cur.execute(
            "SELECT id, team_name, manager_name FROM r4_fantasy_teams "
            "WHERE league_id=? ORDER BY id", (lid,)).fetchall()
        pl = cur.execute(
            "SELECT id, name, position FROM players "
            "WHERE sport_slug=? ORDER BY id", (sport,)).fetchall()
        n_trades = 3
        for i in range(n_trades):
            # First trade: Alice (team 0) → Bob (team 1)
            if i == 0:
                a_idx, b_idx = 0, 1
            elif i == 1:
                a_idx, b_idx = 2, 3
            else:
                a_idx = h(f'r4-ta-{lid}-{i}', len(teams))
                b_idx = (a_idx + 3) % len(teams)
            a_id, a_name, a_mgr = teams[a_idx]
            b_id, b_name, b_mgr = teams[b_idx]
            # players_a: 1-2 players going from team_a to team_b
            n_a = 1 + (i % 2)
            n_b = 1 + ((i + 1) % 2)
            players_a = []
            for j in range(n_a):
                idx = h(f'r4-trd-pa-{lid}-{i}-{j}', len(pl))
                p = pl[idx]
                players_a.append({'id': p[0], 'name': p[1], 'pos': p[2]})
            players_b = []
            for j in range(n_b):
                idx = h(f'r4-trd-pb-{lid}-{i}-{j}', len(pl))
                p = pl[idx]
                players_b.append({'id': p[0], 'name': p[1], 'pos': p[2]})
            value_a = round(hf(f'r4-trd-va-{lid}-{i}', 60.0, 180.0), 2)
            value_b = round(hf(f'r4-trd-vb-{lid}-{i}', 60.0, 180.0), 2)
            status_pool = ['pending', 'pending', 'accepted', 'rejected',
                            'expired']
            status = status_pool[h(f'r4-trd-st-{lid}-{i}',
                                     len(status_pool))]
            if i == 0:
                status = 'pending'  # Reliable for tasks targeting Alice
            slug = f'l{lid}-trade-{trade_id}'
            note = ('Offered before the {} trade deadline; analyzer rates this '
                     '{}.').format(sport.upper(),
                                    'favorable' if value_a < value_b
                                    else 'risky')
            rows.append((trade_id, lid, slug, a_id, b_id,
                         json.dumps(players_a), json.dumps(players_b),
                         value_a, value_b, status, '2024-04-08', note))
            trade_id += 1
    cur.executemany(
        "INSERT INTO r4_fantasy_trades (id, league_id, slug, team_a_id, "
        "team_b_id, players_a_json, players_b_json, value_a, value_b, "
        "status, proposed_date, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        rows)
    return len(rows)


def make_matchups(cur):
    """One head-to-head matchup per team-pair per current week."""
    rows = []
    m_id = 1
    leagues = cur.execute(
        "SELECT id, current_week FROM r4_fantasy_leagues ORDER BY id").fetchall()
    for lid, wk in leagues:
        teams = [r[0] for r in cur.execute(
            "SELECT id FROM r4_fantasy_teams WHERE league_id=? ORDER BY id",
            (lid,)).fetchall()]
        # Pair teams 0v1, 2v3, ...
        for i in range(0, len(teams) - 1, 2):
            a, b = teams[i], teams[i + 1]
            sa = round(hf(f'r4-mu-sa-{lid}-{i}', 75.0, 145.0), 2)
            sb = round(hf(f'r4-mu-sb-{lid}-{i}', 75.0, 145.0), 2)
            pa = round(hf(f'r4-mu-pa-{lid}-{i}', 95.0, 135.0), 2)
            pb = round(hf(f'r4-mu-pb-{lid}-{i}', 95.0, 135.0), 2)
            winner = a if sa >= sb else b
            rows.append((m_id, lid, wk, a, b, sa, sb, pa, pb, winner, 0))
            m_id += 1
    cur.executemany(
        "INSERT INTO r4_fantasy_matchups (id, league_id, week, team_a_id, "
        "team_b_id, score_a, score_b, projected_a, projected_b, "
        "winner_team_id, is_final) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R4 GUI extension already applied — no-op.')
        conn.close()
        return
    create_tables(cur)
    n_lg = make_leagues(cur)
    n_tm = make_teams(cur)
    n_lu = make_lineups(cur)
    n_wv = make_waiver_claims(cur)
    n_td = make_trades(cur)
    n_mu = make_matchups(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R4 GUI inserted: leagues={n_lg} teams={n_tm} lineups={n_lu} '
          f'waivers={n_wv} trades={n_td} matchups={n_mu}')


if __name__ == '__main__':
    main()
