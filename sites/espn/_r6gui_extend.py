#!/usr/bin/env python3
"""R6 GUI extension for sites/espn — fantasy/bracket/community interactivity.

Adds the data backing the new R6 GUI POST surface (lineup save / waiver claim /
trade propose+accept+reject+counter / league create+invite+join+draft+settings /
team rename+avatar / bracket pick+champion+submit+tiebreaker / bracket pool
create+join+invite / article comment+upvote+reply / team+player follow /
watchlist+alert subscribe / poll vote).

Strict gotcha #14: direct sqlite3 INSERTs into instance_seed/espn.db. We do NOT
rebuild the seed from seed_data.py — drift is already real and known.

Determinism: every seed value derived from md5 of a stable key. No wall-clock.
Idempotent: gated on `_r6gui_marker` row in `sports`. After insert we drop+
recreate ix_* indices in sorted order, then VACUUM — yields byte-identical DBs
across runs.

Marker: sports.slug='_r6gui_marker' (id=151).
"""
import hashlib
import os
import sqlite3

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
        "SELECT 1 FROM sports WHERE slug='_r6gui_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (151, 'R6 GUI marker', '_r6gui_marker', 'r6 gui applied',
         '/_internal/', 151, 0))


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
    # Community: article comments (with parent_id for replies)
    """CREATE TABLE IF NOT EXISTS r6_comments (
        id INTEGER PRIMARY KEY,
        article_slug VARCHAR(160) NOT NULL,
        parent_id INTEGER,
        author_name VARCHAR(120),
        author_email VARCHAR(160),
        body TEXT,
        upvotes INTEGER DEFAULT 0,
        created_at VARCHAR(32),
        is_flagged INTEGER DEFAULT 0
    )""",
    # Community: follow team / player
    """CREATE TABLE IF NOT EXISTS r6_follows (
        id INTEGER PRIMARY KEY,
        user_email VARCHAR(160) NOT NULL,
        entity_kind VARCHAR(16) NOT NULL,
        entity_sport VARCHAR(20),
        entity_slug VARCHAR(160) NOT NULL,
        followed_at VARCHAR(32)
    )""",
    # Community: watchlist (team / game / show)
    """CREATE TABLE IF NOT EXISTS r6_watchlist (
        id INTEGER PRIMARY KEY,
        user_email VARCHAR(160) NOT NULL,
        kind VARCHAR(20) NOT NULL,
        ref_slug VARCHAR(160) NOT NULL,
        label VARCHAR(255),
        added_at VARCHAR(32)
    )""",
    # Community: live game alert subscriptions
    """CREATE TABLE IF NOT EXISTS r6_alerts (
        id INTEGER PRIMARY KEY,
        user_email VARCHAR(160) NOT NULL,
        alert_kind VARCHAR(40) NOT NULL,
        ref_slug VARCHAR(160) NOT NULL,
        channel VARCHAR(20),
        is_active INTEGER DEFAULT 1,
        subscribed_at VARCHAR(32)
    )""",
    # Community: polls
    """CREATE TABLE IF NOT EXISTS r6_polls (
        id INTEGER PRIMARY KEY,
        slug VARCHAR(120) NOT NULL,
        sport_slug VARCHAR(20),
        question VARCHAR(255),
        is_closed INTEGER DEFAULT 0,
        closes_at VARCHAR(32)
    )""",
    """CREATE TABLE IF NOT EXISTS r6_poll_options (
        id INTEGER PRIMARY KEY,
        poll_id INTEGER NOT NULL,
        position INTEGER,
        label VARCHAR(200),
        votes INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS r6_poll_votes (
        id INTEGER PRIMARY KEY,
        poll_id INTEGER NOT NULL,
        option_id INTEGER NOT NULL,
        user_email VARCHAR(160),
        voted_at VARCHAR(32)
    )""",
    # Bracket pools (group prediction pools)
    """CREATE TABLE IF NOT EXISTS r6_bracket_pools (
        id INTEGER PRIMARY KEY,
        slug VARCHAR(120) NOT NULL,
        bracket_slug VARCHAR(120) NOT NULL,
        name VARCHAR(200),
        owner_email VARCHAR(160),
        scoring VARCHAR(40) DEFAULT 'standard',
        is_locked INTEGER DEFAULT 0,
        member_count INTEGER DEFAULT 1,
        created_at VARCHAR(32),
        invite_code VARCHAR(20)
    )""",
    """CREATE TABLE IF NOT EXISTS r6_bracket_pool_members (
        id INTEGER PRIMARY KEY,
        pool_id INTEGER NOT NULL,
        user_email VARCHAR(160) NOT NULL,
        display_name VARCHAR(120),
        joined_at VARCHAR(32),
        score INTEGER DEFAULT 0
    )""",
    # User bracket picks (one row per matchup pick)
    """CREATE TABLE IF NOT EXISTS r6_bracket_picks (
        id INTEGER PRIMARY KEY,
        user_email VARCHAR(160) NOT NULL,
        bracket_slug VARCHAR(120) NOT NULL,
        pool_slug VARCHAR(120),
        matchup_id INTEGER,
        picked_team VARCHAR(120),
        round_num INTEGER,
        is_champion_pick INTEGER DEFAULT 0,
        tiebreaker_score INTEGER,
        is_locked INTEGER DEFAULT 0,
        picked_at VARCHAR(32)
    )""",
    # Fantasy league live draft picks
    """CREATE TABLE IF NOT EXISTS r6_draft_picks (
        id INTEGER PRIMARY KEY,
        league_slug VARCHAR(120) NOT NULL,
        pick_num INTEGER NOT NULL,
        round_num INTEGER,
        team_slug VARCHAR(120),
        team_name VARCHAR(160),
        player_name VARCHAR(160),
        player_pos VARCHAR(10),
        nfl_team_abbr VARCHAR(8),
        picked_at VARCHAR(32)
    )""",
    # Fantasy league invites
    """CREATE TABLE IF NOT EXISTS r6_league_invites (
        id INTEGER PRIMARY KEY,
        league_slug VARCHAR(120) NOT NULL,
        invite_code VARCHAR(20) NOT NULL,
        recipient_email VARCHAR(160),
        message VARCHAR(255),
        status VARCHAR(20) DEFAULT 'pending',
        sent_at VARCHAR(32)
    )""",
    # Lineup save event log (POST /fantasy/lineup/save writes here)
    """CREATE TABLE IF NOT EXISTS r6_lineup_events (
        id INTEGER PRIMARY KEY,
        team_slug VARCHAR(120) NOT NULL,
        kind VARCHAR(20) NOT NULL,
        slot VARCHAR(10),
        in_player VARCHAR(160),
        out_player VARCHAR(160),
        week INTEGER,
        saved_at VARCHAR(32)
    )""",
    # Team rename / avatar audit
    """CREATE TABLE IF NOT EXISTS r6_team_audit (
        id INTEGER PRIMARY KEY,
        team_slug VARCHAR(120) NOT NULL,
        change_kind VARCHAR(20) NOT NULL,
        old_value VARCHAR(255),
        new_value VARCHAR(255),
        actor_email VARCHAR(160),
        changed_at VARCHAR(32)
    )""",
    # Indices (must come in sorted order at end of file — handled by normalize)
    "CREATE INDEX IF NOT EXISTS ix_r6_alerts_ref_slug ON r6_alerts (ref_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_alerts_user_email ON r6_alerts (user_email)",
    "CREATE INDEX IF NOT EXISTS ix_r6_bracket_picks_bracket_slug ON r6_bracket_picks (bracket_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_bracket_picks_pool_slug ON r6_bracket_picks (pool_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_bracket_picks_user_email ON r6_bracket_picks (user_email)",
    "CREATE INDEX IF NOT EXISTS ix_r6_bracket_pool_members_pool_id ON r6_bracket_pool_members (pool_id)",
    "CREATE INDEX IF NOT EXISTS ix_r6_bracket_pools_bracket_slug ON r6_bracket_pools (bracket_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_bracket_pools_slug ON r6_bracket_pools (slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_comments_article_slug ON r6_comments (article_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_comments_parent_id ON r6_comments (parent_id)",
    "CREATE INDEX IF NOT EXISTS ix_r6_draft_picks_league_slug ON r6_draft_picks (league_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_follows_entity_slug ON r6_follows (entity_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_follows_user_email ON r6_follows (user_email)",
    "CREATE INDEX IF NOT EXISTS ix_r6_league_invites_invite_code ON r6_league_invites (invite_code)",
    "CREATE INDEX IF NOT EXISTS ix_r6_league_invites_league_slug ON r6_league_invites (league_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_lineup_events_team_slug ON r6_lineup_events (team_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_poll_options_poll_id ON r6_poll_options (poll_id)",
    "CREATE INDEX IF NOT EXISTS ix_r6_poll_votes_poll_id ON r6_poll_votes (poll_id)",
    "CREATE INDEX IF NOT EXISTS ix_r6_polls_slug ON r6_polls (slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_team_audit_team_slug ON r6_team_audit (team_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_watchlist_ref_slug ON r6_watchlist (ref_slug)",
    "CREATE INDEX IF NOT EXISTS ix_r6_watchlist_user_email ON r6_watchlist (user_email)",
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


# ─── Seed content ────────────────────────────────────────────────────────────

POLL_DEFS = [
    ('nba-mvp-2024', 'nba',
     'Who is your 2023-24 NBA MVP?',
     ['Nikola Jokic', 'Shai Gilgeous-Alexander', 'Luka Doncic',
      'Giannis Antetokounmpo', 'Jayson Tatum']),
    ('nfl-rookie-2024', 'nfl',
     'Who wins NFL Offensive Rookie of the Year 2024?',
     ['C.J. Stroud', 'Bijan Robinson', 'Puka Nacua', 'Sam LaPorta',
      'Jahmyr Gibbs']),
    ('mlb-ws-2024', 'mlb',
     'Which team wins the 2024 World Series?',
     ['Los Angeles Dodgers', 'Atlanta Braves', 'Houston Astros',
      'Baltimore Orioles', 'Philadelphia Phillies']),
    ('ncaam-champion-2024', 'ncaam',
     'Who wins the 2024 March Madness mens tournament?',
     ['UConn Huskies', 'Purdue Boilermakers', 'Houston Cougars',
      'North Carolina Tar Heels', 'Tennessee Volunteers']),
    ('nhl-cup-2024', 'nhl',
     'Which team wins the 2024 Stanley Cup?',
     ['Boston Bruins', 'Florida Panthers', 'Edmonton Oilers',
      'Colorado Avalanche', 'New York Rangers']),
    ('soccer-ucl-2024', 'soccer',
     'Who wins the 2023-24 UEFA Champions League?',
     ['Manchester City', 'Real Madrid', 'Bayern Munich',
      'Paris Saint-Germain', 'Arsenal']),
]

DEMO_USERS = [
    ('alice.j@test.com',  'Alice Johnson'),
    ('bob.c@test.com',    'Bob Chen'),
    ('carol.d@test.com',  'Carol Davis'),
    ('david.k@test.com',  'David Kim'),
]

DEMO_DATE = '2024-04-09'  # one day before mirror anchor


def make_polls(cur):
    rows_p = []
    rows_o = []
    rows_v = []
    poll_id = 1
    opt_id = 1
    vote_id = 1
    for slug, sport, question, options in POLL_DEFS:
        rows_p.append((poll_id, slug, sport, question, 0, '2024-05-15'))
        for i, lbl in enumerate(options):
            # Deterministic vote counts
            base = 80 + h(f'r6poll-{slug}-{i}', 250)
            rows_o.append((opt_id, poll_id, i, lbl, base))
            opt_id += 1
        # 4 demo user votes per poll (different options)
        for ui, (email, _name) in enumerate(DEMO_USERS):
            opt_pos = h(f'r6vote-{slug}-{email}', len(options))
            picked_opt_id = opt_id - len(options) + opt_pos
            rows_v.append((vote_id, poll_id, picked_opt_id, email, DEMO_DATE))
            vote_id += 1
        poll_id += 1
    cur.executemany(
        "INSERT INTO r6_polls (id, slug, sport_slug, question, is_closed, "
        "closes_at) VALUES (?,?,?,?,?,?)", rows_p)
    cur.executemany(
        "INSERT INTO r6_poll_options (id, poll_id, position, label, votes) "
        "VALUES (?,?,?,?,?)", rows_o)
    cur.executemany(
        "INSERT INTO r6_poll_votes (id, poll_id, option_id, user_email, "
        "voted_at) VALUES (?,?,?,?,?)", rows_v)
    return len(rows_p), len(rows_o), len(rows_v)


def make_comments(cur):
    """Seed 6 comments + 3 replies on first 8 articles. Includes one comment
    by each benchmark user on article id=1."""
    articles = cur.execute(
        "SELECT slug FROM articles ORDER BY id LIMIT 8").fetchall()
    if not articles:
        return 0
    rows = []
    cid = 1
    sample_bodies = [
        'This is huge — the Celtics look unstoppable when the threes are falling.',
        'Bench depth is what is winning these games, not just the stars.',
        'I respectfully disagree, the defensive scheme is the bigger story.',
        'Looking forward to seeing this matchup in the playoffs.',
        'Hot take: this trend reverses by next month.',
        'Hard to argue with the numbers. Lock it in.',
        'Anyone else notice the second-quarter run?',
        'The advanced stats tell a different story here.',
        'Coach deserves more credit for this turnaround.',
        'Calling it now: deep playoff run.',
    ]
    parent_targets = []
    for ai, (aslug,) in enumerate(articles):
        # Top-level comments
        for ci in range(6):
            if ai == 0 and ci < 4:
                author_email, author_name = DEMO_USERS[ci]
            else:
                idx = h(f'r6cmt-author-{aslug}-{ci}', len(DEMO_USERS))
                author_email, author_name = DEMO_USERS[idx]
            body = sample_bodies[h(f'r6cmt-body-{aslug}-{ci}',
                                    len(sample_bodies))]
            upvotes = h(f'r6cmt-up-{aslug}-{ci}', 25)
            rows.append((cid, aslug, None, author_name, author_email,
                         body, upvotes, DEMO_DATE, 0))
            if ci == 0:
                parent_targets.append((cid, aslug))
            cid += 1
    # Replies on the first comment of each of the first 3 articles
    for parent_cid, aslug in parent_targets[:3]:
        for ri in range(2):
            author_email, author_name = DEMO_USERS[ri + 1 if ri + 1 < 4 else 0]
            body = sample_bodies[h(f'r6rep-{aslug}-{ri}', len(sample_bodies))]
            rows.append((cid, aslug, parent_cid, author_name, author_email,
                         body, h(f'r6rep-up-{aslug}-{ri}', 12),
                         DEMO_DATE, 0))
            cid += 1
    cur.executemany(
        "INSERT INTO r6_comments (id, article_slug, parent_id, author_name, "
        "author_email, body, upvotes, created_at, is_flagged) "
        "VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def make_follows(cur):
    """Seed default follows: 3 teams + 2 players per benchmark user (mirrors
    user_favorites but exposes the r6_follows surface for the new
    /team/.../follow + /player/.../follow POSTs to be idempotent against)."""
    teams = cur.execute(
        "SELECT sport_slug, slug FROM teams ORDER BY id LIMIT 8").fetchall()
    players = cur.execute(
        "SELECT sport_slug, slug FROM players ORDER BY id LIMIT 8").fetchall()
    rows = []
    fid = 1
    for ui, (email, _) in enumerate(DEMO_USERS):
        # 3 teams
        for ti in range(3):
            sport, slug = teams[(ui * 3 + ti) % len(teams)]
            rows.append((fid, email, 'team', sport, slug, DEMO_DATE))
            fid += 1
        # 2 players
        for pi in range(2):
            sport, slug = players[(ui * 2 + pi) % len(players)]
            rows.append((fid, email, 'player', sport, slug, DEMO_DATE))
            fid += 1
    cur.executemany(
        "INSERT INTO r6_follows (id, user_email, entity_kind, entity_sport, "
        "entity_slug, followed_at) VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


def make_bracket_pools(cur):
    """One default public pool per bracket, each with 4 benchmark users."""
    brackets = cur.execute(
        "SELECT id, slug, name FROM r5_brackets ORDER BY id").fetchall()
    pool_rows = []
    member_rows = []
    pick_rows = []
    pid = 1
    mid = 1
    pick_id = 1
    for bid, bslug, bname in brackets:
        pool_slug = f'{bslug}-bracket-pool-2024'
        invite_code = hashlib.md5(pool_slug.encode()).hexdigest()[:8].upper()
        pool_rows.append((pid, pool_slug, bslug,
                          f'{bname} — Official Friends Pool',
                          DEMO_USERS[0][0], 'standard', 0,
                          len(DEMO_USERS), DEMO_DATE, invite_code))
        # Members
        for ui, (email, name) in enumerate(DEMO_USERS):
            score = 40 + h(f'r6pool-{pool_slug}-score-{ui}', 60)
            member_rows.append((mid, pid, email, name, DEMO_DATE, score))
            mid += 1
        # Seed picks: each user picks the favorite (slot=0) in the first 8
        # round-1 matchups of this bracket.
        m_rows = cur.execute(
            "SELECT id, round_num FROM r5_bracket_matchups "
            "WHERE bracket_id=? AND round_num=1 ORDER BY id LIMIT 8",
            (bid,)).fetchall()
        for ui, (email, _name) in enumerate(DEMO_USERS):
            for m_id, rnd in m_rows:
                # Deterministic team pick label
                team_pick = f'top-seed-bracket-{bid}-m{m_id}'
                pick_rows.append((pick_id, email, bslug, pool_slug,
                                  m_id, team_pick, rnd, 0, None, 0,
                                  DEMO_DATE))
                pick_id += 1
        pid += 1
    cur.executemany(
        "INSERT INTO r6_bracket_pools (id, slug, bracket_slug, name, "
        "owner_email, scoring, is_locked, member_count, created_at, "
        "invite_code) VALUES (?,?,?,?,?,?,?,?,?,?)", pool_rows)
    cur.executemany(
        "INSERT INTO r6_bracket_pool_members (id, pool_id, user_email, "
        "display_name, joined_at, score) VALUES (?,?,?,?,?,?)", member_rows)
    cur.executemany(
        "INSERT INTO r6_bracket_picks (id, user_email, bracket_slug, "
        "pool_slug, matchup_id, picked_team, round_num, is_champion_pick, "
        "tiebreaker_score, is_locked, picked_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)", pick_rows)
    return len(pool_rows), len(member_rows), len(pick_rows)


def make_draft_state(cur):
    """Pre-seed 8 picks of an in-progress live draft for league id=1 to make
    the draft room view meaningful out of the box."""
    lg = cur.execute(
        "SELECT slug FROM r4_fantasy_leagues WHERE id=1").fetchone()
    if not lg:
        return 0
    league_slug = lg[0]
    teams = cur.execute(
        "SELECT slug, team_name FROM r4_fantasy_teams WHERE league_id=1 "
        "ORDER BY id LIMIT 8").fetchall()
    sample_picks = [
        ('Christian McCaffrey', 'RB', 'SF'),
        ('Tyreek Hill', 'WR', 'MIA'),
        ('CeeDee Lamb', 'WR', 'DAL'),
        ('Justin Jefferson', 'WR', 'MIN'),
        ('Ja\'Marr Chase', 'WR', 'CIN'),
        ('Bijan Robinson', 'RB', 'ATL'),
        ('Breece Hall', 'RB', 'NYJ'),
        ('Travis Kelce', 'TE', 'KC'),
    ]
    rows = []
    for i, (player, pos, abbr) in enumerate(sample_picks):
        team_slug, team_name = teams[i % len(teams)]
        rows.append((i + 1, league_slug, i + 1, 1, team_slug, team_name,
                     player, pos, abbr, DEMO_DATE))
    cur.executemany(
        "INSERT INTO r6_draft_picks (id, league_slug, pick_num, round_num, "
        "team_slug, team_name, player_name, player_pos, nfl_team_abbr, "
        "picked_at) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R6 GUI extension already applied — no-op.')
        conn.close()
        return
    create_tables(cur)
    n_p, n_o, n_v = make_polls(cur)
    n_c = make_comments(cur)
    n_f = make_follows(cur)
    n_bp, n_bm, n_bk = make_bracket_pools(cur)
    n_dp = make_draft_state(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R6 GUI inserted: polls={n_p} options={n_o} votes={n_v} '
          f'comments={n_c} follows={n_f} pools={n_bp} pool_members={n_bm} '
          f'pool_picks={n_bk} draft_picks={n_dp}')


if __name__ == '__main__':
    main()
