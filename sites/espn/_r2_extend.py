#!/usr/bin/env python3
"""R2 polish extension for sites/espn — direct sqlite3 INSERT only.

Why this script exists (gotcha #14): the shipped HF `instance_seed/espn.db`
has drifted from `seed_data.py`. Rebuilding via `from app import app` would
overwrite rows that the live site has been serving for months. Instead, we
INSERT new rows on top of the live seed, preserving all baseline data.

What gets added:
  * ~520 articles      → 1020+ total (target 1000+)
  * ~250 player_stats  → 478+ total (target 450+)
  * ~210 games         → 526 total (target 500+)
  * sports nav re-ordered to mirror espn.com (NFL/NBA/MLB/NHL/Soccer/NCAA*/Fantasy/Watch)
  * Watch sport row added (sport_slug='watch')

Determinism: every numeric/text field is derived from an md5 of a stable key
(team slug + date + index), so this script can be re-run on any host and
produce a byte-identical DB.

Idempotent: gated on `r2_extend_marker` row in `sports` (slug='_r2_marker').
Re-running is a no-op.
"""
import hashlib
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  'instance_seed', 'espn.db')
ANCHOR = date(2024, 4, 10)          # MIRROR_REFERENCE_DATE
ANCHOR_TS = '2024-04-10 12:00:00.000000'


def h(key: str, mod: int, offset: int = 0) -> int:
    """Deterministic hash → int in [offset, offset+mod)."""
    return offset + int.from_bytes(
        hashlib.md5(key.encode()).digest()[:4], 'big') % mod


def hf(key: str, lo: float, hi: float) -> float:
    """Deterministic hash → float in [lo, hi)."""
    return lo + (h(key, 10_000) / 10_000.0) * (hi - lo)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fetch_one(cur, sql, args=()):
    cur.execute(sql, args)
    row = cur.fetchone()
    return row[0] if row else None


def already_extended(cur) -> bool:
    return bool(fetch_one(cur,
        "SELECT 1 FROM sports WHERE slug='_r2_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (99, 'R2 marker', '_r2_marker', 'r2_extend applied',
         '/_internal/', 99, 0))


# ─── 1. Sports nav re-order + Watch ───────────────────────────────────────────

def update_nav(cur):
    """Mirror real espn.com top nav order: NFL, NBA, MLB, NHL, Soccer, NCAAF,
    NCAAM, NCAAW, Fantasy, Watch, Tennis, Golf, MMA."""
    # Fantasy promoted to slot 9; Watch new at slot 10
    cur.execute("UPDATE sports SET nav_order=9 WHERE slug='fantasy'")
    cur.execute("UPDATE sports SET nav_order=11 WHERE slug='tennis'")
    cur.execute("UPDATE sports SET nav_order=12 WHERE slug='golf'")
    cur.execute("UPDATE sports SET nav_order=13 WHERE slug='mma'")
    # Insert Watch
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (13, 'Watch', 'watch', 'Watch on ESPN', '/watch/', 10, 1))


# ─── 2. Articles ──────────────────────────────────────────────────────────────

NBA_TEMPLATES = [
    ("{team} keep playoff push alive with {opp} win",
     "{team} earned a critical {score} victory over the {opp}. {star} led all scorers with {pts} points, while the defense held strong in the fourth quarter to seal the win."),
    ("{star} drops {pts} as {team} cruise past {opp}",
     "{star} poured in {pts} points to lead the {team} past the {opp}. The performance moves {team} closer to clinching home-court advantage in the first round."),
    ("Inside the {team} bench rotation as playoffs loom",
     "Coaches around the league are taking notice of how the {team} have managed minutes for {star} and the supporting cast. The plan: rest now, win in May."),
    ("{team} owner addresses long-term roster plans",
     "Speaking after the {team}' latest game, ownership outlined a multi-year vision built around {star}. Cap flexibility and the draft remain the priorities."),
    ("{team} adjust rotation ahead of postseason",
     "The {team} are tinkering with closing lineups in the season's final stretch. {star} and the starters logged heavier minutes in the win over the {opp}."),
    ("Scouting report: how the {opp} could trouble {team} in May",
     "An advance scout breaks down the matchup-by-matchup edges the {opp} hold against the {team}. Defending {star} remains the central question."),
]
NHL_TEMPLATES = [
    ("{team} edge {opp} in late-season clash",
     "The {team} pulled out a {score} win over the {opp}. {star} contributed a goal and an assist as the {team} chase a playoff spot."),
    ("{star} hat trick lifts {team} past {opp}",
     "{star} netted three goals as the {team} downed the {opp}. Goaltending and special teams stayed sharp through three periods."),
    ("Coach evaluates {team} top line ahead of playoffs",
     "With the regular season winding down, the {team} are fine-tuning their top six. {star} continues to anchor the first line."),
]
MLB_TEMPLATES = [
    ("{star} homers as {team} top {opp}",
     "{star} launched a home run to power the {team} past the {opp} {score}. The starter went six innings and earned the win."),
    ("{team} bullpen settles as season takes shape",
     "Early-season bullpen volatility has cleared up for the {team}. Manager pointed to {star}'s leadership and the late-inning trio."),
    ("Inside the {team} clubhouse: early-season storylines",
     "Beat reporters file a clubhouse dispatch on the {team}. {star} is hot, the rotation is shuffling, and the lineup is settling."),
]
NFL_TEMPLATES = [
    ("{team} eye {pos} help in upcoming draft",
     "The {team} are reportedly targeting a {pos} in the early rounds. The roster around {star} is built to win now, but depth is thin."),
    ("Free agency recap: how the {team} reshape the roster",
     "After a busy free agency window, the {team} project a different look. The signings give {star} new weapons heading into next season."),
    ("{team} coaching staff finalizes spring schedule",
     "The {team} laid out the OTA and minicamp calendar. {star} is expected to attend voluntary workouts and lead the locker room."),
]
SOCCER_TEMPLATES = [
    ("{team} grind out result in tight derby",
     "A late equalizer saw the {team} come away with a hard-earned draw against the {opp}. {star} was named man of the match."),
    ("Manager defends rotation after {team} road win",
     "Rotation choices paid off as the {team} took the points on the road. {star} provided the assist for the winner."),
]
NCAAF_TEMPLATES = [
    ("{team} spring practice opens with eye on {star}",
     "The {team} kicked off spring practice this week. Coaches are focused on developing {star} and the offensive line."),
]
NCAAM_TEMPLATES = [
    ("{team} land top recruit ahead of next season",
     "The {team} added a top-100 recruit to the 2024 class. The signing complements returning starter {star}."),
]
NCAAW_TEMPLATES = [
    ("{team} extend coach contract through 2028",
     "The {team} program will keep its head coach in place through 2028. Recruiting and player development continue under {star}."),
]
TENNIS_TEMPLATES = [
    ("Hard-court tune-up reveals new contender",
     "An emerging player took a set off the top seed in the third round. Slams remain the ultimate measure, but the rankings are shifting."),
]
GOLF_TEMPLATES = [
    ("Masters prep: who looks ready for Augusta",
     "Early-season form gives shape to the Masters field. Driving accuracy and putting numbers will decide the green jacket."),
]
MMA_TEMPLATES = [
    ("Title fight booked for summer pay-per-view",
     "A long-rumored championship matchup is finally official. Both camps confirmed terms for the summer card."),
]
FANTASY_TEMPLATES = [
    ("Fantasy waiver wire: who to add this week",
     "Injuries and rotation shifts created several fantasy-relevant adds. Streamers at center and forward are the priorities."),
    ("Power rankings: top fantasy assets entering playoffs",
     "Our weekly power rankings spotlight category leaders and matchup specialists. Punt builds remain viable into the playoffs."),
]


def article_authors(idx: int) -> str:
    pool = ['Adrian Wojnarowski', 'Ramona Shelburne', 'Tim MacMahon',
            'Brian Windhorst', 'Jeremy Fowler', 'Adam Schefter',
            'Jeff Passan', 'Greg Wyshynski', 'Marc Stein',
            'Kevin Pelton', 'Zach Lowe', 'Bill Connelly',
            'ESPN Staff', 'Associated Press', 'Reuters']
    return pool[idx % len(pool)]


def make_articles(cur):
    """Insert ~520 deterministic articles dated 2023-10-01 .. 2024-04-09."""
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing_slugs = {r[0] for r in
                      cur.execute("SELECT slug FROM articles").fetchall()}

    teams_by_sport = {}
    for sport_slug in ('nba', 'nfl', 'nhl', 'mlb', 'soccer', 'ncaaf',
                       'ncaam', 'ncaaw'):
        rows = cur.execute(
            "SELECT id, full_name, slug, sport_slug FROM teams "
            "WHERE sport_slug=? ORDER BY id", (sport_slug,)).fetchall()
        teams_by_sport[sport_slug] = rows

    # star player per team (first by id)
    stars_by_team = {}
    for tid, *_ in cur.execute(
            "SELECT DISTINCT team_id FROM players "
            "WHERE team_id IS NOT NULL ORDER BY team_id").fetchall():
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (tid,)).fetchone()
        if row:
            stars_by_team[tid] = row

    plan = [
        # (sport_slug, templates, count, headline_every)
        ('nba',    NBA_TEMPLATES,     150, 6),
        ('nhl',    NHL_TEMPLATES,      80, 6),
        ('mlb',    MLB_TEMPLATES,      80, 6),
        ('nfl',    NFL_TEMPLATES,      80, 6),
        ('soccer', SOCCER_TEMPLATES,   50, 8),
        ('ncaaf',  NCAAF_TEMPLATES,    20, 10),
        ('ncaam',  NCAAM_TEMPLATES,    20, 10),
        ('ncaaw',  NCAAW_TEMPLATES,    20, 10),
        ('tennis', TENNIS_TEMPLATES,    8, 8),
        ('golf',   GOLF_TEMPLATES,      8, 8),
        ('mma',    MMA_TEMPLATES,       8, 8),
        ('fantasy', FANTASY_TEMPLATES,  8, 8),
    ]

    inserted = 0
    rows_to_insert = []
    for sport_slug, templates, count, headline_every in plan:
        teams = teams_by_sport.get(sport_slug, []) or teams_by_sport.get('nba')
        if not teams:
            continue
        for i in range(count):
            t_idx = h(f'{sport_slug}-team-{i}', len(teams))
            opp_idx = h(f'{sport_slug}-opp-{i}', len(teams))
            if opp_idx == t_idx:
                opp_idx = (opp_idx + 1) % len(teams)
            team_id, team_name, team_slug, _ = teams[t_idx]
            _, opp_name, _, _ = teams[opp_idx]
            star_row = stars_by_team.get(team_id)
            star_name = star_row[0] if star_row else f'{team_name} captain'
            star_pos = star_row[1] if star_row else 'F'

            tpl_i = h(f'{sport_slug}-tpl-{i}', len(templates))
            title_tpl, body_tpl = templates[tpl_i]
            score_a = h(f'{sport_slug}-sa-{i}', 30, 95)
            score_b = h(f'{sport_slug}-sb-{i}', 25, 88)
            pts = h(f'{sport_slug}-pts-{i}', 28, 18)
            title = title_tpl.format(team=team_name, opp=opp_name,
                                     star=star_name, pts=pts, pos=star_pos)
            body = body_tpl.format(team=team_name, opp=opp_name,
                                   star=star_name,
                                   score=f'{score_a}-{score_b}',
                                   pts=pts, pos=star_pos)

            # date: spread across Oct 2023 .. Apr 9 2024
            day_offset = h(f'{sport_slug}-date-{i}', 191)  # 0..190
            article_date = date(2023, 10, 1) + timedelta(days=day_offset)
            # late-season skew: ensure last 10% of articles are in Apr 2024
            if i >= count * 0.9:
                article_date = date(2024, 4, 1) + timedelta(
                    days=h(f'{sport_slug}-recent-{i}', 9))  # 04-01..04-09

            slug_base = (
                title.lower()
                .replace("'", '').replace('"', '')
                .replace('&', 'and')
                .replace('.', '')
                .replace(',', '')
                .replace('?', '')
                .replace(':', '')
                .replace('/', '-')
                .replace(' ', '-')
            )
            # strip non [a-z0-9-]
            slug_base = ''.join(
                c for c in slug_base if c.isalnum() or c == '-')
            while '--' in slug_base:
                slug_base = slug_base.replace('--', '-')
            slug = f'{slug_base}-r2-{sport_slug}-{i:03d}'
            if slug in existing_slugs:
                slug = f'{slug}-{next_id}'
            existing_slugs.add(slug)

            # tags
            tags = json.dumps([sport_slug.upper(), team_name, star_name])
            is_headline = 1 if (i % headline_every == 0) else 0
            is_featured = 1 if (i % (headline_every * 3) == 0) else 0
            created_at = (
                f'{article_date.isoformat()} '
                f'{12 + (i % 8):02d}:{(i*7) % 60:02d}:'
                f'{(i*13) % 60:02d}.000000')
            published_label = article_date.strftime('%B %-d, %Y')

            rows_to_insert.append((
                next_id, sport_slug, title, slug, '', body,
                article_authors(i),
                f'/static/images/espn/articles/{sport_slug}/{next_id}.jpg',
                tags, is_headline, is_featured, created_at, published_label,
            ))
            next_id += 1
            inserted += 1

    # Sort by id (already monotonic) then bulk insert
    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, body, "
        "author, image, tags, is_headline, is_featured, created_at, "
        "published_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows_to_insert)
    return inserted


# ─── 3. Games ─────────────────────────────────────────────────────────────────

NHL_VENUES = ['TD Garden', 'Madison Square Garden', 'United Center',
              'Rogers Arena', 'Scotiabank Arena', 'Bell Centre',
              'Wells Fargo Center', 'Capital One Arena']
NBA_VENUES = ['TD Garden', 'Crypto.com Arena', 'Madison Square Garden',
              'Chase Center', 'Ball Arena', 'Paycom Center',
              'Kaseya Center', 'American Airlines Center']
NFL_VENUES = ['Arrowhead Stadium', 'AT&T Stadium', 'SoFi Stadium',
              'Lambeau Field', 'Lincoln Financial Field', 'M&T Bank Stadium',
              'Highmark Stadium']
MLB_VENUES = ['Yankee Stadium', 'Fenway Park', 'Dodger Stadium',
              'Wrigley Field', 'Oracle Park', 'Tropicana Field',
              'Citi Field', 'Petco Park']


def make_games(cur):
    """Add ~210 games: more 2023-24 NHL/NBA regular season + early 2024 MLB."""
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM games") or 0) + 1
    inserted = 0
    rows_to_insert = []

    # NBA historical: spread across Nov 2023 .. April 8 2024
    nba_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='nba' "
        "ORDER BY id").fetchall()
    nhl_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='nhl' "
        "ORDER BY id").fetchall()
    mlb_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='mlb' "
        "ORDER BY id").fetchall()
    nfl_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='nfl' "
        "ORDER BY id").fetchall()

    def star_for(team_id):
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (team_id,)).fetchone()
        return row or ('Star Player', 'F')

    # NBA: 80 historical regular-season finals
    for i in range(80):
        a = h(f'nba-game-a-{i}', len(nba_teams))
        b = h(f'nba-game-b-{i}', len(nba_teams))
        if a == b:
            b = (b + 1) % len(nba_teams)
        home = nba_teams[a]
        away = nba_teams[b]
        day_offset = h(f'nba-game-day-{i}', 130)
        gdate = date(2023, 11, 5) + timedelta(days=day_offset)  # 11-05 .. 03-14
        hs = h(f'nba-hs-{i}', 30, 95)
        as_ = h(f'nba-as-{i}', 30, 88)
        ven = NBA_VENUES[i % len(NBA_VENUES)]
        star_h = star_for(home[0])
        leaders = json.dumps({
            'top_scorer_name': star_h[0],
            'top_scorer_pts': h(f'nba-tp-{i}', 25, 18),
            'top_scorer_team': home[1],
            'top_scorer_position': star_h[1],
            'top_rebounder_name': star_h[0],
            'top_rebounder_reb': h(f'nba-tr-{i}', 8, 6),
            'top_rebounder_team': home[1],
            'top_assists_name': star_h[0],
            'top_assists_ast': h(f'nba-ta-{i}', 6, 4),
            'top_assists_team': home[1],
            'home_high_scorer': star_h[0],
            'home_high_points': h(f'nba-hh-{i}', 25, 18),
            'away_high_scorer': star_for(away[0])[0],
            'away_high_points': h(f'nba-ah-{i}', 22, 16),
        })
        rows_to_insert.append((
            next_id, 'nba', home[0], away[0], hs, as_,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            f"{7 + (i % 4)}:{30 if i % 2 else '00'} PM ET",
            'final', 'Final', 'ESPN', ven,
            f"{home[1]} beat the {away[1]} {hs}-{as_}.",
            'https://www.ticketmaster.com', leaders))
        next_id += 1
        inserted += 1

    # NHL: 60 historical
    for i in range(60):
        a = h(f'nhl-game-a-{i}', len(nhl_teams))
        b = h(f'nhl-game-b-{i}', len(nhl_teams))
        if a == b:
            b = (b + 1) % len(nhl_teams)
        home = nhl_teams[a]
        away = nhl_teams[b]
        day_offset = h(f'nhl-game-day-{i}', 140)
        gdate = date(2023, 11, 1) + timedelta(days=day_offset)
        hs = h(f'nhl-hs-{i}', 5, 1)
        as_ = h(f'nhl-as-{i}', 5, 1)
        ven = NHL_VENUES[i % len(NHL_VENUES)]
        star_h = star_for(home[0])
        leaders = json.dumps({
            'top_scorer_name': star_h[0],
            'top_scorer_pts': h(f'nhl-tp-{i}', 3, 1),
            'top_scorer_team': home[1],
            'top_scorer_position': star_h[1],
            'home_high_scorer': star_h[0],
            'home_high_points': h(f'nhl-hh-{i}', 3, 1),
            'away_high_scorer': star_for(away[0])[0],
            'away_high_points': h(f'nhl-ah-{i}', 3, 1),
        })
        rows_to_insert.append((
            next_id, 'nhl', home[0], away[0], hs, as_,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            '7:00 PM ET', 'final', 'Final', 'ESPN+', ven,
            f"{home[1]} edged the {away[1]} {hs}-{as_}.",
            'https://www.ticketmaster.com', leaders))
        next_id += 1
        inserted += 1

    # MLB: 40 early-season historical (Mar 28 .. Apr 8 fills)
    for i in range(40):
        a = h(f'mlb-game-a-{i}', len(mlb_teams))
        b = h(f'mlb-game-b-{i}', len(mlb_teams))
        if a == b:
            b = (b + 1) % len(mlb_teams)
        home = mlb_teams[a]
        away = mlb_teams[b]
        day_offset = h(f'mlb-game-day-{i}', 12)  # 03-28..04-08
        gdate = date(2024, 3, 28) + timedelta(days=day_offset)
        hs = h(f'mlb-hs-{i}', 11, 0)
        as_ = h(f'mlb-as-{i}', 11, 0)
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
        rows_to_insert.append((
            next_id, 'mlb', home[0], away[0], hs, as_,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            '7:05 PM ET', 'final', 'Final', 'MLB Network', ven,
            f"{home[1]} topped the {away[1]} {hs}-{as_}.",
            'https://www.mlb.com/tickets', leaders))
        next_id += 1
        inserted += 1

    # NFL: 30 historical regular-season recap entries (2023 season finals)
    for i in range(30):
        a = h(f'nfl-game-a-{i}', len(nfl_teams))
        b = h(f'nfl-game-b-{i}', len(nfl_teams))
        if a == b:
            b = (b + 1) % len(nfl_teams)
        home = nfl_teams[a]
        away = nfl_teams[b]
        gdate = date(2023, 9, 10) + timedelta(days=h(f'nfl-game-day-{i}', 130) * 1)
        hs = h(f'nfl-hs-{i}', 31, 10)
        as_ = h(f'nfl-as-{i}', 31, 7)
        ven = NFL_VENUES[i % len(NFL_VENUES)]
        star_h = star_for(home[0])
        leaders = json.dumps({
            'top_scorer_name': star_h[0],
            'top_scorer_pts': hs // 7,
            'top_scorer_team': home[1],
            'top_scorer_position': star_h[1] or 'QB',
            'home_high_scorer': star_h[0],
            'home_high_points': hs,
            'away_high_scorer': star_for(away[0])[0],
            'away_high_points': as_,
        })
        rows_to_insert.append((
            next_id, 'nfl', home[0], away[0], hs, as_,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            '1:00 PM ET', 'final', 'Final', 'CBS', ven,
            f"{home[1]} defeated the {away[1]} {hs}-{as_}.",
            'https://www.nfl.com/tickets', leaders))
        next_id += 1
        inserted += 1

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows_to_insert)
    return inserted


# ─── 4. Player stats backfill ─────────────────────────────────────────────────

def make_player_stats(cur):
    """Add 2023-24 season stat row for ~250 players currently missing one."""
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM player_stats") or 0) + 1
    rows_to_insert = []
    # Per-sport quota
    quotas = {'nba': 80, 'nfl': 60, 'mlb': 60, 'nhl': 50, 'soccer': 30}
    season = '2023-24'

    for sport_slug, quota in quotas.items():
        players = cur.execute(
            "SELECT p.id, p.name, p.position FROM players p "
            "WHERE p.sport_slug=? AND p.id NOT IN ("
            "  SELECT player_id FROM player_stats "
            "  WHERE stat_type='season' AND season=?) "
            "ORDER BY p.id LIMIT ?",
            (sport_slug, season, quota)).fetchall()
        for p in players:
            pid, pname, pos = p
            key = f'{sport_slug}-{pid}'
            base = {
                'id': next_id, 'player_id': pid,
                'season': season, 'stat_type': 'season',
                'games_played': h(f'{key}-gp', 40, 30),
                'games_started': h(f'{key}-gs', 40, 20),
            }
            if sport_slug == 'nba':
                base.update({
                    'points_per_game': round(hf(f'{key}-ppg', 5, 28), 1),
                    'rebounds_per_game': round(hf(f'{key}-rpg', 2, 12), 1),
                    'assists_per_game': round(hf(f'{key}-apg', 1, 9), 1),
                    'steals_per_game': round(hf(f'{key}-spg', 0.3, 2), 1),
                    'blocks_per_game': round(hf(f'{key}-bpg', 0.2, 2.5), 1),
                    'fg_pct': round(hf(f'{key}-fg', 0.4, 0.55), 3),
                    'three_pt_pct': round(hf(f'{key}-3p', 0.32, 0.42), 3),
                    'ft_pct': round(hf(f'{key}-ft', 0.7, 0.9), 3),
                    'minutes_per_game': round(hf(f'{key}-mpg', 18, 36), 1),
                })
            elif sport_slug == 'nfl':
                if (pos or '').upper() == 'QB':
                    base.update({
                        'passing_yards': h(f'{key}-pyd', 3500, 2200),
                        'passing_tds': h(f'{key}-ptd', 30, 12),
                        'rushing_yards': h(f'{key}-ryd', 400, 50),
                        'rushing_tds': h(f'{key}-rtd', 6, 0),
                    })
                elif (pos or '').upper() == 'RB':
                    base.update({
                        'rushing_yards': h(f'{key}-ryd', 1100, 600),
                        'rushing_tds': h(f'{key}-rtd', 12, 3),
                        'receptions': h(f'{key}-rec', 60, 20),
                        'receiving_yards': h(f'{key}-recy', 500, 150),
                    })
                elif (pos or '').upper() in ('WR', 'TE'):
                    base.update({
                        'receptions': h(f'{key}-rec', 80, 40),
                        'receiving_yards': h(f'{key}-recy', 1100, 500),
                        'receiving_tds': h(f'{key}-rectd', 11, 3),
                    })
                else:
                    base.update({
                        'tackles': h(f'{key}-tck', 80, 40),
                        'sacks': round(hf(f'{key}-sk', 0.5, 12), 1),
                    })
            elif sport_slug == 'mlb':
                if 'P' in (pos or ''):
                    base.update({
                        'era': round(hf(f'{key}-era', 2.5, 5.5), 2),
                        'strikeouts': h(f'{key}-so', 220, 60),
                        'wins_pitcher': h(f'{key}-wp', 16, 4),
                    })
                else:
                    base.update({
                        'batting_avg': round(hf(f'{key}-ba', 0.22, 0.33), 3),
                        'home_runs': h(f'{key}-hr', 40, 5),
                        'rbi': h(f'{key}-rbi', 100, 30),
                        'stolen_bases': h(f'{key}-sb', 25, 1),
                    })
            elif sport_slug == 'nhl':
                base.update({
                    'goals': h(f'{key}-g', 40, 5),
                    'hockey_assists': h(f'{key}-a', 50, 8),
                    'hockey_points': h(f'{key}-pt', 80, 15),
                    'plus_minus': h(f'{key}-pm', 50, -20),
                    'penalty_minutes': h(f'{key}-pim', 80, 5),
                })
            elif sport_slug == 'soccer':
                base.update({
                    'soccer_goals': h(f'{key}-sg', 18, 1),
                    'soccer_assists': h(f'{key}-sa', 12, 1),
                    'soccer_appearances': h(f'{key}-sap', 35, 10),
                    'yellow_cards': h(f'{key}-yc', 9, 0),
                    'red_cards': h(f'{key}-rc', 2, 0),
                })

            cols = list(base.keys())
            vals = [base[c] for c in cols]
            rows_to_insert.append((cols, vals))
            next_id += 1

    # Group by column-set so we can executemany within each group
    by_cols = {}
    for cols, vals in rows_to_insert:
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


# ─── 5. Normalize layout (gotcha #2 — sort indexes, VACUUM) ───────────────────

def normalize(cur):
    idx_rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'ix_%'").fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if already_extended(cur):
        print('R2 extension already applied — no-op.')
        conn.close()
        return
    update_nav(cur)
    n_art = make_articles(cur)
    n_gm = make_games(cur)
    n_st = make_player_stats(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'Inserted: articles={n_art}, games={n_gm}, player_stats={n_st}')


if __name__ == '__main__':
    main()
