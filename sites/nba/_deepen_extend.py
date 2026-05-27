#!/usr/bin/env python3
"""NBA deepen — extend instance_seed/nba.db with vanilla-level surfaces.

Adds new tables backing 30+ nba.com pages: awards, all-star, draft (year-scoped),
playoff brackets, player career/gamelog/splits, team news/video/tickets/store,
game box-score/play-by-play/shot-chart, video catalogue, fantasy leagues/teams,
account follows/alerts/saved games, article comments, highlight shares.

Strict gotcha #14 compliance: writes directly to instance_seed/nba.db via raw
sqlite3, never `from app import`. Gated on `users` row 'nba_deepen_marker'.

Determinism — every value derived from md5(key); two clean runs reproduce
byte-identical bytes after drop+recreate ix_* + VACUUM.
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "instance_seed", "nba.db")
RUNTIME_DB = os.path.join(HERE, "instance", "nba.db")

REF_DATE = datetime(2026, 5, 15, 12, 0, 0)


def h(key, mod, offset=0):
    return offset + int.from_bytes(hashlib.md5(key.encode()).digest()[:4], "big") % mod


def hf(key, lo, hi):
    return round(lo + (h(key, 10000) / 10000.0) * (hi - lo), 2)


def pick(key, options):
    return options[h(key, len(options))]


def already_extended(cur):
    try:
        row = cur.execute(
            "SELECT 1 FROM users WHERE email='_nba_deepen_marker@webharbor.local'"
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False


def mark_extended(cur):
    cur.execute(
        "INSERT INTO users (id, username, email, password_hash, display_name, "
        "phone, address_line1, city, state, zip_code, favorite_team_slug, "
        "payment_last4, created_at) VALUES (?, ?, ?, ?, ?, '', '', '', '', '', '', '0000', ?)",
        (99, "_nba_deepen_marker", "_nba_deepen_marker@webharbor.local",
         "$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou",
         "Deepen Marker", REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
    )


# ── schema ─────────────────────────────────────────────────────────────────

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS follows (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind VARCHAR(20),
        target_slug VARCHAR(140), target_id INTEGER, alert_on INTEGER DEFAULT 0,
        created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind VARCHAR(40),
        target_slug VARCHAR(140), label VARCHAR(160), active INTEGER DEFAULT 1,
        created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS allstar_votes (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, year INTEGER,
        conference VARCHAR(8), position VARCHAR(8), player_slug VARCHAR(140),
        created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS awards (
        id INTEGER PRIMARY KEY, year INTEGER, slug VARCHAR(40), name VARCHAR(80),
        winner_slug VARCHAR(140), winner_team_slug VARCHAR(60),
        runner_up_slug VARCHAR(140), third_slug VARCHAR(140),
        ceremony_date VARCHAR(40), share FLOAT, votes_first INTEGER)""",
    """CREATE TABLE IF NOT EXISTS award_votes (
        id INTEGER PRIMARY KEY, user_id INTEGER, year INTEGER, award_slug VARCHAR(40),
        first_slug VARCHAR(140), second_slug VARCHAR(140), third_slug VARCHAR(140),
        created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS draft_prospects (
        id INTEGER PRIMARY KEY, year INTEGER, slug VARCHAR(140), name VARCHAR(120),
        position VARCHAR(12), height VARCHAR(16), weight INTEGER,
        wingspan VARCHAR(16), college VARCHAR(120), country VARCHAR(60), age INTEGER,
        mock_rank INTEGER, tier VARCHAR(20), strengths VARCHAR(300),
        concerns VARCHAR(300), comp VARCHAR(120), image VARCHAR(180))""",
    """CREATE TABLE IF NOT EXISTS draft_picks (
        id INTEGER PRIMARY KEY, year INTEGER, round INTEGER, pick_no INTEGER,
        team_slug VARCHAR(60), prospect_slug VARCHAR(140), via VARCHAR(80))""",
    """CREATE TABLE IF NOT EXISTS lottery_results (
        id INTEGER PRIMARY KEY, year INTEGER, team_slug VARCHAR(60),
        seed INTEGER, odds_pct FLOAT, final_pick INTEGER)""",
    """CREATE TABLE IF NOT EXISTS player_gamelogs (
        id INTEGER PRIMARY KEY, player_slug VARCHAR(140), game_date VARCHAR(20),
        opponent_slug VARCHAR(60), at_home INTEGER, result VARCHAR(8), mins INTEGER,
        pts INTEGER, reb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER, tov INTEGER,
        fg VARCHAR(12), three VARCHAR(12), ft VARCHAR(12), plus_minus INTEGER)""",
    """CREATE TABLE IF NOT EXISTS player_splits (
        id INTEGER PRIMARY KEY, player_slug VARCHAR(140), split_kind VARCHAR(40),
        gp INTEGER, ppg FLOAT, rpg FLOAT, apg FLOAT, fg_pct FLOAT, three_pct FLOAT)""",
    """CREATE TABLE IF NOT EXISTS player_endorsements (
        id INTEGER PRIMARY KEY, player_slug VARCHAR(140), brand VARCHAR(80),
        shoe VARCHAR(140), shoe_slug VARCHAR(140), price FLOAT, colorway VARCHAR(80),
        release_date VARCHAR(20), image VARCHAR(180))""",
    """CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY, slug VARCHAR(180), title VARCHAR(220), kind VARCHAR(40),
        team_slug VARCHAR(60), player_slug VARCHAR(140), duration VARCHAR(12),
        image VARCHAR(180), description TEXT, published_at DATETIME, views INTEGER)""",
    """CREATE TABLE IF NOT EXISTS video_likes (
        id INTEGER PRIMARY KEY, user_id INTEGER, video_slug VARCHAR(180),
        created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS article_comments (
        id INTEGER PRIMARY KEY, user_id INTEGER, article_slug VARCHAR(240),
        body TEXT, upvotes INTEGER DEFAULT 0, created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS highlight_shares (
        id INTEGER PRIMARY KEY, user_id INTEGER, video_slug VARCHAR(180),
        channel VARCHAR(30), recipient VARCHAR(160), note VARCHAR(240),
        created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS saved_games (
        id INTEGER PRIMARY KEY, user_id INTEGER, game_id INTEGER,
        note VARCHAR(180), created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS game_boxscores (
        id INTEGER PRIMARY KEY, game_id INTEGER, team_slug VARCHAR(60),
        q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, ot INTEGER,
        fg_made INTEGER, fg_att INTEGER, three_made INTEGER, three_att INTEGER,
        ft_made INTEGER, ft_att INTEGER, reb INTEGER, ast INTEGER, tov INTEGER, fouls INTEGER)""",
    """CREATE TABLE IF NOT EXISTS game_playbyplay (
        id INTEGER PRIMARY KEY, game_id INTEGER, period INTEGER, clock VARCHAR(8),
        team_slug VARCHAR(60), description VARCHAR(240), home_score INTEGER, away_score INTEGER)""",
    """CREATE TABLE IF NOT EXISTS game_shots (
        id INTEGER PRIMARY KEY, game_id INTEGER, player_slug VARCHAR(140), team_slug VARCHAR(60),
        period INTEGER, clock VARCHAR(8), x INTEGER, y INTEGER, made INTEGER, value INTEGER, distance INTEGER)""",
    """CREATE TABLE IF NOT EXISTS game_four_factors (
        id INTEGER PRIMARY KEY, game_id INTEGER, team_slug VARCHAR(60),
        efg FLOAT, tov_pct FLOAT, oreb_pct FLOAT, ft_rate FLOAT, pace FLOAT)""",
    """CREATE TABLE IF NOT EXISTS fantasy_leagues (
        id INTEGER PRIMARY KEY, slug VARCHAR(120), name VARCHAR(160), owner_user_id INTEGER,
        scoring VARCHAR(20), team_count INTEGER, public INTEGER DEFAULT 1, description TEXT)""",
    """CREATE TABLE IF NOT EXISTS fantasy_teams (
        id INTEGER PRIMARY KEY, slug VARCHAR(120), league_slug VARCHAR(120),
        user_id INTEGER, name VARCHAR(160), wins INTEGER, losses INTEGER, ties INTEGER,
        pts_for FLOAT, pts_against FLOAT, rank INTEGER, owner_label VARCHAR(120))""",
    """CREATE TABLE IF NOT EXISTS fantasy_rosters (
        id INTEGER PRIMARY KEY, team_slug VARCHAR(120), player_slug VARCHAR(140),
        slot VARCHAR(8), status VARCHAR(20))""",
    """CREATE TABLE IF NOT EXISTS fantasy_lineups (
        id INTEGER PRIMARY KEY, team_slug VARCHAR(120), week INTEGER,
        player_slug VARCHAR(140), slot VARCHAR(8), locked INTEGER DEFAULT 0,
        proj_pts FLOAT, submitted_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS ticket_orders (
        id INTEGER PRIMARY KEY, user_id INTEGER, game_id INTEGER, section VARCHAR(40),
        row_label VARCHAR(8), seats INTEGER, price_each FLOAT, total FLOAT,
        confirmation VARCHAR(20), created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS store_wishlist (
        id INTEGER PRIMARY KEY, user_id INTEGER, product_slug VARCHAR(200),
        note VARCHAR(160), created_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, hide_scores INTEGER DEFAULT 0,
        timezone VARCHAR(40), email_news INTEGER DEFAULT 1, push_alerts INTEGER DEFAULT 1,
        league_pass_quality VARCHAR(20), updated_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS celebrity_allstar (
        id INTEGER PRIMARY KEY, year INTEGER, team VARCHAR(40), name VARCHAR(120),
        role VARCHAR(40), tagline VARCHAR(200), image VARCHAR(180))""",
    """CREATE TABLE IF NOT EXISTS mock_drafts (
        id INTEGER PRIMARY KEY, user_id INTEGER, year INTEGER, pick_no INTEGER,
        prospect_slug VARCHAR(140), submitted_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS player_news_items (
        id INTEGER PRIMARY KEY, player_slug VARCHAR(140), title VARCHAR(220),
        body VARCHAR(600), tag VARCHAR(40), published_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS team_news_items (
        id INTEGER PRIMARY KEY, team_slug VARCHAR(60), title VARCHAR(220),
        body VARCHAR(600), tag VARCHAR(40), image VARCHAR(180), published_at DATETIME)""",
    """CREATE TABLE IF NOT EXISTS stat_leaderboards (
        id INTEGER PRIMARY KEY, category VARCHAR(40), rank INTEGER,
        player_slug VARCHAR(140), team_slug VARCHAR(60), value FLOAT)""",
]


# ── data builders ──────────────────────────────────────────────────────────

PLAYER_HEADSHOTS_AVAILABLE = [
    "lebron_james", "anthony_davis", "luka_doncic", "kyrie_irving",
    "jayson_tatum", "jaylen_brown", "nikola_jokic", "jamal_murray",
    "giannis_antetokounmpo", "damian_lillard", "stephen_curry",
    "draymond_green", "shai_gilgeous_alexander", "chet_holmgren",
    "kevin_durant", "devin_booker", "jalen_brunson", "joel_embiid",
    "tyrese_haliburton", "anthony_edwards", "jimmy_butler",
    "victor_wembanyama", "paolo_banchero", "donovan_mitchell",
    "tyrese_maxey", "ja_morant", "kawhi_leonard", "paul_george",
]


def headshot_for(player_slug):
    base = player_slug.replace("-", "_")
    if base in PLAYER_HEADSHOTS_AVAILABLE:
        return f"/static/images/players/{base}.png"
    idx = h(player_slug, len(PLAYER_HEADSHOTS_AVAILABLE))
    return f"/static/images/players/{PLAYER_HEADSHOTS_AVAILABLE[idx]}.png"


ARTICLE_IMAGES = [
    "harris-levert-051426-scaled.jpg", "edwards-spurs-gm5-051426-scaled.jpg",
    "wembanyama-gm5.jpg", "edwards-game5-051426-scaled.jpg",
    "johnson-iso-051426-scaled.jpg", "okc-lal-recap.jpg",
    "brunson-iso-051426-scaled.jpg", "harden-game5.jpg", "cavs-playoffs.jpg",
    "pistons-cavs-game6.jpg", "draft-combine-2026.jpg",
    "og-anunoby.jpg", "cle-det-recap.jpg", "det-cle-recap.jpg",
    "min-sas-recap.jpg", "brandon-clarke.png", "peterson-dybantsa.jpg",
    "combine-knueppel.jpg", "ian-eagle-noah-eagle.jpg",
    "nba-official-draft-combine-hero.jpg", "nba-official-draft-logo.png",
    "nba-official-draft-lottery.jpg", "nba-official-draft-banner.png",
    "nba-official-draft-video-1.jpg", "nba-official-draft-video-2.jpg",
    "nba-official-finals-logo.png", "nba-official-spurs-thunder.jpg",
    "nba-official-young-spurs.jpg", "wizards-no1.jpg",
    "morey.jpg", "lebron-stern-draft-night.jpg", "collins-obituary.png",
]


def article_image_for(slug):
    return f"/static/images/articles/{ARTICLE_IMAGES[h(slug, len(ARTICLE_IMAGES))]}"


# Real 2026 draft prospects (battle-tested from public ESPN / The Athletic / NBA mock boards)
PROSPECTS_2026 = [
    ("aj-dybantsa", "AJ Dybantsa", "F", "6-9", 210, "7-0", "BYU", "USA", 18,
     "Combo wing with elite shot creation; #1 overall buzz since prep year.",
     "Half-court polish, defensive consistency under playoff pressure.",
     "Paul George comp"),
    ("darryn-peterson", "Darryn Peterson", "G", "6-5", 195, "6-9", "Kansas", "USA", 19,
     "Two-way guard with rare blend of frame, speed and decision-making.",
     "Pull-up jumper variance from deep range.",
     "Jaylen Brown comp"),
    ("cameron-boozer", "Cameron Boozer", "F", "6-9", 240, "7-1", "Duke", "USA", 18,
     "High-floor scoring big with elbow passing and physical post game.",
     "Pop-out shooting indicator still developing.",
     "Julius Randle comp"),
    ("dylan-harper", "Dylan Harper", "G", "6-6", 215, "6-10", "Rutgers", "USA", 19,
     "Big lead guard with downhill scoring and three-level shot diet.",
     "Foot speed when defending traditional point guards.",
     "Jalen Brunson comp"),
    ("nate-ament", "Nate Ament", "F", "6-9", 195, "7-2", "Tennessee", "USA", 18,
     "Long shot-blocking forward with growing perimeter shooting.",
     "Frame and ball-handling under physical pressure.",
     "Brandon Ingram comp"),
    ("vj-edgecombe", "VJ Edgecombe", "G", "6-5", 190, "6-10", "Baylor", "Bahamas", 19,
     "Hyper-athletic two-way guard with transition explosiveness.",
     "Half-court shot creation indicators against set defenses.",
     "Anthony Edwards comp"),
    ("kasparas-jakucionis", "Kasparas Jakucionis", "G", "6-6", 200, "6-7", "Illinois", "Lithuania", 19,
     "Polished pick-and-roll passer with high feel and pace control.",
     "Lateral quickness when chased over screens.",
     "Lonzo Ball comp"),
    ("ace-bailey", "Ace Bailey", "F", "6-10", 200, "7-0", "Rutgers", "USA", 18,
     "Tough shot maker with size, ball-handling and pull-up package.",
     "Shot selection discipline and team-defense rotations.",
     "Jaden McDaniels comp"),
    ("derik-queen", "Derik Queen", "C", "6-10", 245, "7-1", "Maryland", "USA", 20,
     "Skilled offensive center with passing and short-roll touch.",
     "Foot speed and rim protection against modern pace.",
     "Domantas Sabonis comp"),
    ("tre-johnson", "Tre Johnson", "G", "6-6", 195, "6-9", "Texas", "USA", 19,
     "Pure shot maker with elite three-level scoring profile.",
     "Defensive engagement consistency.",
     "CJ McCollum comp"),
    ("khaman-maluach", "Khaman Maluach", "C", "7-2", 250, "7-7", "Duke", "South Sudan", 18,
     "Generational rim protector with growing offensive footwork.",
     "Pick-and-pop shooting indicators.",
     "Walker Kessler comp"),
    ("jase-richardson", "Jase Richardson", "G", "6-3", 185, "6-6", "Michigan State", "USA", 19,
     "Elite shooter and shifty pull-up guard with NBA bloodlines.",
     "Defensive size and finishing through length.",
     "Devin Booker comp"),
    ("liam-mcneeley", "Liam McNeeley", "F", "6-8", 215, "6-9", "Connecticut", "USA", 19,
     "Smooth shot-making wing with growing playmaking flashes.",
     "Athletic burst when matched against quick wings.",
     "Klay Thompson comp"),
    ("nolan-traore", "Nolan Traore", "G", "6-4", 175, "6-7", "Saint-Quentin", "France", 19,
     "Lightning-quick point guard with French league reps.",
     "Pull-up jumper and finishing through length.",
     "TJ McConnell comp"),
    ("noa-essengue", "Noa Essengue", "F", "6-10", 200, "7-1", "Ratiopharm Ulm", "France", 19,
     "Versatile forward with multipositional defense and transition scoring.",
     "Half-court shooting consistency.",
     "Jonathan Kuminga comp"),
    ("jeremiah-fears", "Jeremiah Fears", "G", "6-4", 180, "6-7", "Oklahoma", "USA", 18,
     "Speedy guard with downhill driving force and developing pull-up.",
     "Defensive frame and ball-control under pressure.",
     "Tyrese Maxey comp"),
    ("egor-demin", "Egor Demin", "G", "6-9", 200, "6-10", "BYU", "Russia", 19,
     "Jumbo playmaker with elite vision and length.",
     "Three-point consistency and lateral defense.",
     "Lonzo Ball comp"),
    ("collin-murray-boyles", "Collin Murray-Boyles", "F", "6-8", 245, "7-0", "South Carolina", "USA", 20,
     "Skilled passing big with two-way versatility.",
     "Height for a center in the modern game.",
     "Draymond Green comp"),
    ("rasheer-fleming", "Rasheer Fleming", "F", "6-9", 230, "7-5", "Saint Joseph's", "USA", 21,
     "Long stretch four with shooting and rim protection upside.",
     "Self-creation off the dribble.",
     "Pascal Siakam comp"),
    ("kon-knueppel", "Kon Knueppel", "G-F", "6-7", 215, "6-8", "Duke", "USA", 19,
     "Connective offensive wing with elite shooting touch.",
     "Vertical athleticism and finishing through length.",
     "Sam Hauser comp"),
    ("ryan-kalkbrenner", "Ryan Kalkbrenner", "C", "7-1", 260, "7-6", "Creighton", "USA", 24,
     "Senior center with elite rim protection and finishing.",
     "Mobility on switches at NBA pace.",
     "Brook Lopez comp"),
    ("yaxel-lendeborg", "Yaxel Lendeborg", "F", "6-9", 230, "7-3", "UAB", "Puerto Rico", 22,
     "Versatile forward with rebounding and connective passing.",
     "Perimeter shooting reliability against NBA closeouts.",
     "Naz Reid comp"),
    ("danny-wolf", "Danny Wolf", "C", "7-0", 250, "7-3", "Michigan", "USA", 21,
     "Skilled big with elbow handle and pick-and-roll passing.",
     "Defensive switching against quick guards.",
     "Alperen Sengun comp"),
    ("hugo-gonzalez", "Hugo Gonzalez", "G-F", "6-6", 200, "6-8", "Real Madrid", "Spain", 19,
     "Two-way wing groomed in Real Madrid system.",
     "Half-court self-creation rate.",
     "OG Anunoby comp"),
    ("isaiah-evans", "Isaiah Evans", "G-F", "6-6", 175, "6-9", "Duke", "USA", 19,
     "Elite movement shooter with deep range.",
     "Frame and on-ball defense at NBA pace.",
     "Buddy Hield comp"),
    ("milos-uzan", "Milos Uzan", "G", "6-4", 195, "6-7", "Houston", "USA", 21,
     "Steady combo guard with three-point shooting and decision-making.",
     "Burst when attacking set defenses.",
     "Andrew Nembhard comp"),
    ("alex-condon", "Alex Condon", "F-C", "6-11", 230, "7-1", "Florida", "Australia", 20,
     "Mobile big with switching defense and developing offense.",
     "Half-court scoring volume.",
     "Aaron Gordon comp"),
    ("flory-bidunga", "Flory Bidunga", "C", "6-10", 230, "7-4", "Kansas", "DR Congo", 18,
     "Athletic rim-running center with shot-blocking explosion.",
     "Skill polish on offensive end.",
     "Mitchell Robinson comp"),
    ("johni-broome", "Johni Broome", "C", "6-10", 240, "7-1", "Auburn", "USA", 22,
     "Hard-nosed post scorer with shot-blocking and rebounding.",
     "Pick-and-pop range against modern coverages.",
     "Steven Adams comp"),
    ("tahaad-pettiford", "Tahaad Pettiford", "G", "6-1", 180, "6-3", "Auburn", "USA", 19,
     "Bouncy lead guard with elite finishing for size.",
     "Defensive size and turnover rate.",
     "Cole Anthony comp"),
]


def seed_awards_and_votes(cur, teams, players_by_slug, users):
    award_specs = [
        ("mvp", "Kia Most Valuable Player", "shai-gilgeous-alexander", "nikola-jokic", "luka-doncic", "thunder", 0.892, 78),
        ("dpoy", "Kia Defensive Player of the Year", "victor-wembanyama", "rudy-gobert", "evan-mobley", "spurs", 0.812, 65),
        ("roy", "Kia Rookie of the Year", "stephon-castle", "zaccharie-risacher", "alex-sarr", "spurs", 0.741, 58),
        ("smoy", "Kia Sixth Man of the Year", "malik-monk", "naz-reid", "payton-pritchard", "kings", 0.610, 41),
        ("mip", "Kia Most Improved Player", "tyrese-maxey", "alperen-sengun", "scottie-barnes", "seventysixers", 0.580, 38),
        ("coy", "Kia Coach of the Year", None, None, None, None, 0.700, 52),
        ("clutch", "Jerry West Trophy Clutch Player", "shai-gilgeous-alexander", "jalen-brunson", "stephen-curry", "thunder", 0.554, 33),
        ("teammate", "Twyman-Stokes Teammate of the Year", "mike-conley", "chris-paul", "draymond-green", "timberwolves", 0.420, 20),
        ("citizenship", "Bob Lanier Community Assist", "stephen-curry", "kevin-durant", "jayson-tatum", "warriors", 0.380, 18),
    ]
    awards_rows = []
    for year in (2024, 2025, 2026):
        ceremony = f"{year}-06-{17 + (year - 2024):02d}"
        for slug, name, winner, runner_up, third, team, share, votes_first in award_specs:
            if slug == "coy" and winner is None:
                # coach award gets text winner via name
                continue
            # shift winners across years deterministically
            offset = (year - 2026)
            awards_rows.append((
                year, slug, name, winner, team, runner_up, third, ceremony,
                round(share - 0.04 * abs(offset), 3), max(1, votes_first + offset * 5)
            ))
    cur.executemany(
        "INSERT INTO awards (year, slug, name, winner_slug, winner_team_slug, "
        "runner_up_slug, third_slug, ceremony_date, share, votes_first) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        awards_rows,
    )

    vote_rows = []
    user_award_pairs = [
        (1, "mvp", "shai-gilgeous-alexander", "nikola-jokic", "luka-doncic"),
        (1, "dpoy", "victor-wembanyama", "rudy-gobert", "evan-mobley"),
        (2, "mvp", "nikola-jokic", "shai-gilgeous-alexander", "jayson-tatum"),
        (2, "smoy", "naz-reid", "malik-monk", "payton-pritchard"),
        (3, "mvp", "luka-doncic", "shai-gilgeous-alexander", "nikola-jokic"),
        (3, "roy", "stephon-castle", "zaccharie-risacher", "alex-sarr"),
        (4, "mvp", "jalen-brunson", "shai-gilgeous-alexander", "nikola-jokic"),
        (4, "mip", "tyrese-maxey", "scottie-barnes", "alperen-sengun"),
    ]
    for u, slug, a, b, c in user_award_pairs:
        vote_rows.append((u, 2026, slug, a, b, c, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")))
    cur.executemany(
        "INSERT INTO award_votes (user_id, year, award_slug, first_slug, "
        "second_slug, third_slug, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        vote_rows,
    )


def seed_draft(cur):
    rows = []
    for rank, p in enumerate(PROSPECTS_2026, 1):
        slug, name, pos, height, weight, wingspan, college, country, age, strengths, concerns, comp = p
        rows.append((
            2026, slug, name, pos, height, weight, wingspan, college, country, age,
            rank,
            "Top tier" if rank <= 5 else ("Lottery" if rank <= 14 else ("First round" if rank <= 30 else "Second round")),
            strengths, concerns, comp,
            headshot_for(slug.replace("-", "_")),
        ))
    cur.executemany(
        "INSERT INTO draft_prospects (year, slug, name, position, height, weight, "
        "wingspan, college, country, age, mock_rank, tier, strengths, concerns, comp, image) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    teams = [r[0] for r in cur.execute("SELECT slug FROM teams").fetchall()]
    # Real-style lottery odds for 2026 (Washington won, top-4 protected)
    lottery_specs = [
        ("wizards", 1, 14.0, 1), ("hornets", 2, 14.0, 2), ("trail_blazers", 3, 14.0, 3),
        ("pistons", 4, 12.5, 4), ("raptors", 5, 10.5, 5), ("spurs", 6, 9.0, 6),
        ("nets", 7, 7.5, 7), ("rockets", 8, 6.0, 8), ("jazz", 9, 4.5, 9),
        ("hawks", 10, 3.0, 10), ("bulls", 11, 1.8, 11), ("grizzlies", 12, 1.7, 12),
        ("warriors", 13, 1.0, 13), ("kings", 14, 0.5, 14),
    ]
    cur.executemany(
        "INSERT INTO lottery_results (year, team_slug, seed, odds_pct, final_pick) "
        "VALUES (2026, ?, ?, ?, ?)",
        lottery_specs,
    )

    # Build picks 1-30 first round
    first_round_team_order = [
        "wizards", "hornets", "trail_blazers", "pistons", "raptors", "spurs",
        "nets", "rockets", "jazz", "hawks", "bulls", "grizzlies", "warriors", "kings",
        "magic", "hornets", "heat", "celtics", "lakers", "mavericks", "pacers",
        "bucks", "knicks", "clippers", "suns", "seventysixers", "nuggets",
        "thunder", "timberwolves", "cavaliers",
    ]
    pick_rows = []
    for i, team in enumerate(first_round_team_order[:30], 1):
        prospect = PROSPECTS_2026[(i - 1) % len(PROSPECTS_2026)][0]
        via = ""
        pick_rows.append((2026, 1, i, team, prospect, via))
    cur.executemany(
        "INSERT INTO draft_picks (year, round, pick_no, team_slug, prospect_slug, via) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        pick_rows,
    )


def seed_player_extras(cur, players_rows):
    log_rows = []
    split_rows = []
    endorse_rows = []
    news_rows = []
    opp_teams = ["lakers", "celtics", "knicks", "heat", "warriors", "bucks",
                 "thunder", "nuggets", "suns", "mavericks", "pacers", "magic",
                 "cavaliers", "76ers", "spurs", "timberwolves"]
    for pid, slug, name, team_id, position, ppg, rpg, apg, spg, bpg, fg_pct, three_pct in players_rows:
        # 18-game game log
        for g in range(18):
            key = f"{slug}-game-{g}"
            opp = pick(key + "-opp", opp_teams)
            if opp == slug.split("-")[0]:
                opp = "lakers"
            mins = 22 + h(key + "min", 16)
            pts = max(0, int(ppg + (h(key + "p", 14) - 7)))
            reb = max(0, int(rpg + (h(key + "r", 8) - 4)))
            ast = max(0, int(apg + (h(key + "a", 8) - 4)))
            fga = max(8, int(pts / 1.8) + h(key + "fga", 6))
            fgm = max(2, int(fga * fg_pct / 100.0))
            three_a = max(0, h(key + "3a", 9))
            three_m = max(0, min(three_a, int(three_a * three_pct / 100.0)))
            fta = max(0, h(key + "fta", 7))
            ftm = max(0, fta - h(key + "ftm", 3))
            pm = h(key + "pm", 41) - 20
            date_iso = (REF_DATE - timedelta(days=g * 3 + 1)).strftime("%Y-%m-%d")
            log_rows.append((
                slug, date_iso, opp, h(key + "ah", 2), pick(key + "res", ["W", "L"]),
                mins, pts, reb, ast,
                max(0, h(key + "stl", 5)), max(0, h(key + "blk", 4)), max(0, h(key + "tov", 5)),
                f"{fgm}-{fga}", f"{three_m}-{three_a}", f"{ftm}-{fta}", pm,
            ))
        # Splits
        for kind in ("Home", "Away", "vs East", "vs West", "Before All-Star", "After All-Star",
                     "Wins", "Losses", "Day games", "Night games"):
            key = f"{slug}-split-{kind}"
            gp = 30 + h(key + "gp", 25)
            split_rows.append((
                slug, kind, gp,
                round(ppg + (h(key + "p", 60) - 30) / 10.0, 1),
                round(rpg + (h(key + "r", 30) - 15) / 10.0, 1),
                round(apg + (h(key + "a", 30) - 15) / 10.0, 1),
                round(fg_pct + (h(key + "f", 80) - 40) / 10.0, 1),
                round(three_pct + (h(key + "3", 100) - 50) / 10.0, 1),
            ))
        # Endorsements / shoes
        brands = ["Nike", "Adidas", "Jordan Brand", "Puma", "New Balance", "Anta", "Li-Ning", "Converse"]
        brand = pick(slug + "brand", brands)
        shoe_name_suffix = h(slug + "shoe", 12) + 1
        shoe_name = f"{brand} {name.split()[-1]} {shoe_name_suffix}"
        endorse_rows.append((
            slug, brand, shoe_name, f"{slug}-shoe-{shoe_name_suffix}",
            float(89 + h(slug + "price", 90)),
            pick(slug + "color", ["Hardwood", "City Edition", "Throwback", "Court Purple", "Black/White",
                                  "Volt", "Triple Black", "Olympic Gold", "Carbon Red"]),
            (REF_DATE - timedelta(days=h(slug + "release", 120))).strftime("%Y-%m-%d"),
            headshot_for(slug.replace("-", "_")),
        ))
        # 6 player news items
        topics = [
            ("Practice update", "limited contact in shoot-around ahead of next matchup."),
            ("Postgame quotes", "spoke about the offensive rhythm and defensive adjustments."),
            ("Trainer report", "listed as probable with the team's standard recovery protocol."),
            ("Workout footage", "shared a clip of late-night perimeter shooting work."),
            ("Endorsement story", "announced a community outreach event in his hometown."),
            ("Film breakdown", "broke down the read-and-react decisions in last clutch possession."),
        ]
        for i, (title_tag, fragment) in enumerate(topics):
            title = f"{name}: {title_tag}"
            body = f"{name} {fragment} Updated context shared by the NBA.com news desk."
            news_rows.append((
                slug, title, body, title_tag.split()[0].lower(),
                (REF_DATE - timedelta(hours=i * 8 + 2)).strftime("%Y-%m-%d %H:%M:%S.000000"),
            ))
    cur.executemany(
        "INSERT INTO player_gamelogs (player_slug, game_date, opponent_slug, at_home, result, "
        "mins, pts, reb, ast, stl, blk, tov, fg, three, ft, plus_minus) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        log_rows,
    )
    cur.executemany(
        "INSERT INTO player_splits (player_slug, split_kind, gp, ppg, rpg, apg, fg_pct, three_pct) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        split_rows,
    )
    cur.executemany(
        "INSERT INTO player_endorsements (player_slug, brand, shoe, shoe_slug, price, "
        "colorway, release_date, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        endorse_rows,
    )
    cur.executemany(
        "INSERT INTO player_news_items (player_slug, title, body, tag, published_at) "
        "VALUES (?, ?, ?, ?, ?)",
        news_rows,
    )


def seed_team_news(cur, teams):
    rows = []
    topics = [
        ("Injury update", "released its official injury report ahead of the next game."),
        ("Practice notes", "ran extended late-game scenario reps in Wednesday's practice."),
        ("Front office", "front office confirmed it had no further roster moves to announce."),
        ("Community", "hosted a community basketball clinic with local middle schools."),
        ("Coach quotes", "head coach addressed media after a competitive shoot-around."),
        ("Schedule note", "issued a tip-off and broadcast adjustment for an upcoming home game."),
        ("Roster spotlight", "highlighted the development arc of its second-unit forwards."),
        ("Arena", "shared a behind-the-scenes look at arena setup for playoff broadcasts."),
    ]
    for slug, name in teams:
        for i, (tag, fragment) in enumerate(topics):
            title = f"{name}: {tag}"
            body = f"The {name} {fragment}"
            rows.append((
                slug, title, body, tag.split()[0].lower(),
                article_image_for(f"{slug}-news-{i}"),
                (REF_DATE - timedelta(days=i * 2 + 1)).strftime("%Y-%m-%d %H:%M:%S.000000"),
            ))
    cur.executemany(
        "INSERT INTO team_news_items (team_slug, title, body, tag, image, published_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_videos(cur, players_rows, teams):
    rows = []
    template_titles = [
        ("Highlights", "Highlights"), ("Game recap", "Recap"), ("Film breakdown", "Film"),
        ("Mic'd up", "Wired"), ("Press conference", "Presser"),
        ("Practice clip", "Practice"), ("Top 10 plays", "Top10"),
        ("Top dunks", "Dunks"), ("Top blocks", "Blocks"), ("Top assists", "Assists"),
    ]
    for slug, name, team_id, ppg in [(p[1], p[2], p[3], p[5]) for p in players_rows]:
        for tt_title, tt_kind in template_titles:
            video_slug = f"{slug}-{tt_kind.lower()}-{h(slug + tt_kind, 9000)}"
            duration_s = 60 + h(slug + tt_kind + "d", 540)
            mins = duration_s // 60
            secs = duration_s % 60
            rows.append((
                video_slug,
                f"{name} — {tt_title}",
                tt_kind,
                "",
                slug,
                f"{mins:02d}:{secs:02d}",
                article_image_for(slug + tt_kind),
                f"{name} {tt_title.lower()} clip from the NBA.com video desk.",
                (REF_DATE - timedelta(hours=h(slug + tt_kind + "ts", 720))).strftime("%Y-%m-%d %H:%M:%S.000000"),
                h(slug + tt_kind + "v", 200000) + 5000,
            ))
    # Team-level highlight reels
    for team_slug, name in teams:
        for tt_title, tt_kind in [("Team highlights", "Highlights"), ("Best plays", "Top10"),
                                   ("Pregame intro", "Intro"), ("All-access", "Access"),
                                   ("Coach interview", "Presser"), ("Locker room", "Locker")]:
            video_slug = f"{team_slug}-{tt_kind.lower()}-{h(team_slug + tt_kind, 7000)}"
            duration_s = 90 + h(team_slug + tt_kind + "d", 510)
            mins = duration_s // 60
            secs = duration_s % 60
            rows.append((
                video_slug, f"{name} — {tt_title}", tt_kind, team_slug, "",
                f"{mins:02d}:{secs:02d}",
                article_image_for(team_slug + tt_kind),
                f"{name} {tt_title.lower()} from NBA.com video desk.",
                (REF_DATE - timedelta(hours=h(team_slug + tt_kind + "ts", 720))).strftime("%Y-%m-%d %H:%M:%S.000000"),
                h(team_slug + tt_kind + "v", 100000) + 5000,
            ))
    cur.executemany(
        "INSERT INTO videos (slug, title, kind, team_slug, player_slug, duration, image, "
        "description, published_at, views) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_game_extras(cur, games):
    bs_rows, pbp_rows, shot_rows, ff_rows = [], [], [], []
    for gid, home_id, away_id, home_score, away_score, status, home_slug, away_slug in games:
        if status != "Final" or home_score is None:
            # build pretend stats anyway from md5 for shot chart / four factors
            key = f"game-{gid}"
            home_q = [22 + h(key + "h" + str(q), 12) for q in range(4)]
            away_q = [22 + h(key + "a" + str(q), 12) for q in range(4)]
            home_score_calc = sum(home_q)
            away_score_calc = sum(away_q)
        else:
            key = f"game-{gid}"
            home_q = [home_score // 4 + (h(key + "hq" + str(q), 7) - 3) for q in range(4)]
            home_q[-1] += home_score - sum(home_q)
            away_q = [away_score // 4 + (h(key + "aq" + str(q), 7) - 3) for q in range(4)]
            away_q[-1] += away_score - sum(away_q)
            home_score_calc = home_score
            away_score_calc = away_score
        for slug, qs, total in [(home_slug, home_q, home_score_calc), (away_slug, away_q, away_score_calc)]:
            fga = 78 + h(f"game-{gid}-{slug}fga", 14)
            fgm = int(fga * (0.43 + h(f"game-{gid}-{slug}fp", 12) / 100.0))
            tha = 28 + h(f"game-{gid}-{slug}3a", 14)
            thm = int(tha * (0.33 + h(f"game-{gid}-{slug}3p", 14) / 100.0))
            fta = 14 + h(f"game-{gid}-{slug}fta", 14)
            ftm = int(fta * (0.74 + h(f"game-{gid}-{slug}ftp", 20) / 100.0))
            reb = 38 + h(f"game-{gid}-{slug}reb", 10)
            ast = 18 + h(f"game-{gid}-{slug}ast", 10)
            tov = 9 + h(f"game-{gid}-{slug}tov", 7)
            fouls = 14 + h(f"game-{gid}-{slug}f", 8)
            bs_rows.append((gid, slug, qs[0], qs[1], qs[2], qs[3], 0,
                            fgm, fga, thm, tha, ftm, fta, reb, ast, tov, fouls))
            ff_rows.append((
                gid, slug,
                round((fgm + 0.5 * thm) / max(1, fga) * 100, 1),
                round(tov * 100 / max(1, fga + 0.44 * fta + tov), 1),
                round((reb / 2) * 100 / max(1, (reb / 2) + 22), 1),
                round(fta / max(1, fga) * 100, 1),
                round(98 + h(f"game-{gid}-{slug}pace", 8) / 2.0, 1),
            ))
        # Play-by-play (8 events)
        for ev in range(8):
            key = f"game-{gid}-pbp-{ev}"
            quarter = (ev // 2) + 1
            tslug = home_slug if ev % 2 == 0 else away_slug
            score_h = sum(home_q[:quarter])
            score_a = sum(away_q[:quarter])
            descs = [
                "drives baseline for the layup", "drains a transition three", "makes the cut for a lob slam",
                "splashes a pull-up jumper", "blocks the shot at the rim", "comes up with the steal",
                "drops the no-look pass", "knocks down the floater",
            ]
            pbp_rows.append((
                gid, quarter, f"{8 - ev:02d}:{ev * 5:02d}", tslug,
                pick(key + "desc", descs), score_h, score_a,
            ))
        # Shots (12 per game)
        for s in range(12):
            key = f"game-{gid}-shot-{s}"
            tslug = home_slug if s % 2 == 0 else away_slug
            value = 3 if h(key + "val", 100) < 38 else 2
            shot_rows.append((
                gid, "", tslug, (s // 3) + 1, f"{8 - s % 8:02d}:{s * 4 % 60:02d}",
                h(key + "x", 250) - 125, h(key + "y", 250) - 25,
                1 if h(key + "made", 100) < 47 else 0, value, 6 + h(key + "dist", 22),
            ))
    cur.executemany(
        "INSERT INTO game_boxscores (game_id, team_slug, q1, q2, q3, q4, ot, fg_made, fg_att, "
        "three_made, three_att, ft_made, ft_att, reb, ast, tov, fouls) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        bs_rows,
    )
    cur.executemany(
        "INSERT INTO game_playbyplay (game_id, period, clock, team_slug, description, home_score, away_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        pbp_rows,
    )
    cur.executemany(
        "INSERT INTO game_shots (game_id, player_slug, team_slug, period, clock, x, y, made, value, distance) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        shot_rows,
    )
    cur.executemany(
        "INSERT INTO game_four_factors (game_id, team_slug, efg, tov_pct, oreb_pct, ft_rate, pace) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ff_rows,
    )


def seed_fantasy(cur, players_rows, users):
    league_specs = [
        ("playoff-press", "Playoff Press League", 1, "Head-to-Head Points", 10, 1, "Public league with playoff-style head-to-head."),
        ("hardwood-stretch-run", "Hardwood Stretch Run", 1, "Roto 9-Cat", 12, 1, "9-category rotisserie for the stretch run."),
        ("draft-day-dynasty", "Draft Day Dynasty", 2, "Dynasty Keep 15", 12, 1, "Dynasty league keeping 15 players."),
        ("nba-mock-room", "NBA Mock Room", 3, "Salary Cap Auction", 14, 1, "Salary cap auction draft format."),
        ("nation-of-stats", "Nation of Stats", 4, "Roto 8-Cat", 10, 1, "8-category rotisserie without turnovers."),
    ]
    cur.executemany(
        "INSERT INTO fantasy_leagues (slug, name, owner_user_id, scoring, team_count, public, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        league_specs,
    )
    team_rows = []
    user_team_owners = [
        ("alice-rising-stars", "playoff-press", 1, "Rising Stars"),
        ("alice-thunderstruck", "hardwood-stretch-run", 1, "Thunderstruck"),
        ("bob-board-room", "playoff-press", 2, "Board Room"),
        ("bob-celtic-pride", "draft-day-dynasty", 2, "Celtic Pride"),
        ("carol-mavs-faithful", "playoff-press", 3, "Mavs Faithful"),
        ("carol-court-vision", "hardwood-stretch-run", 3, "Court Vision"),
        ("david-empire-state", "playoff-press", 4, "Empire State"),
        ("david-knicks-army", "draft-day-dynasty", 4, "Knicks Army"),
    ]
    for slug, league_slug, uid, name in user_team_owners:
        wins = 8 + h(slug + "w", 12)
        losses = 6 + h(slug + "l", 10)
        pts = 850.0 + h(slug + "p", 600)
        team_rows.append((slug, league_slug, uid, name, wins, losses, 0, pts, pts - 30, 0, name))
    # Add filler teams to fill league counts
    fillers = ["the-pulse", "rim-rattlers", "transition-game", "perimeter-watch",
               "the-glassmen", "boxing-out", "shot-clock-heroes", "second-unit",
               "deep-bench", "spacing-kings", "screen-game", "switch-defense",
               "small-ball", "ringers", "the-undrafted", "splash-zone"]
    for i, leaguename in enumerate(["playoff-press", "hardwood-stretch-run", "draft-day-dynasty",
                                     "nba-mock-room", "nation-of-stats"]):
        for j in range(8):
            slug = f"{leaguename}-team-{j+1}"
            owner_label = fillers[(i * 4 + j) % len(fillers)].replace("-", " ").title()
            wins = 5 + h(slug + "w", 18)
            losses = 5 + h(slug + "l", 18)
            pts = 800.0 + h(slug + "p", 700)
            team_rows.append((slug, leaguename, 0, owner_label, wins, losses, 0, pts, pts - 30, 0, owner_label))
    cur.executemany(
        "INSERT INTO fantasy_teams (slug, league_slug, user_id, name, wins, losses, ties, "
        "pts_for, pts_against, rank, owner_label) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        team_rows,
    )
    roster_rows = []
    lineup_rows = []
    slots = ["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL", "UTIL", "BN", "BN", "BN", "BN"]
    # All fantasy_teams pick rotating top players
    all_players = [(p[1], p[5]) for p in players_rows]  # slug, ppg
    all_players_sorted = sorted(all_players, key=lambda x: -x[1])
    for team_slug, _, _, _ in [(s, l, u, n) for s, l, u, n, _, _, _, _, _, _, _ in team_rows]:
        start_idx = h(team_slug + "roster", len(all_players_sorted) - 14)
        roster = all_players_sorted[start_idx:start_idx + 13]
        for slot, (pslug, _) in zip(slots, roster):
            roster_rows.append((team_slug, pslug, slot, "Active"))
            lineup_rows.append((
                team_slug, 30, pslug, slot, 1 if slot in {"PG", "SG", "SF", "PF", "C"} else 0,
                round(25 + h(team_slug + pslug + "proj", 200) / 10.0, 1),
                REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000"),
            ))
    cur.executemany(
        "INSERT INTO fantasy_rosters (team_slug, player_slug, slot, status) "
        "VALUES (?, ?, ?, ?)",
        roster_rows,
    )
    cur.executemany(
        "INSERT INTO fantasy_lineups (team_slug, week, player_slug, slot, locked, "
        "proj_pts, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        lineup_rows,
    )


def seed_celebrity(cur):
    rows = []
    teams = [("Team Stephen A.", ["DJ D-Nice", "Anuel AA", "Jason Bateman", "Jenny McCarthy",
                                   "Common", "Robin Roberts", "Caleb McLaughlin", "Quinta Brunson"]),
             ("Team Shannon", ["Lil Wayne", "Pete Davidson", "Andy Cohen", "Travis Kelce",
                               "Kane Brown", "Alix Earle", "Walker Hayes", "Adam Sandler"])]
    for team, names in teams:
        for n in names:
            slug = n.lower().replace(" ", "-").replace(".", "")
            rows.append((
                2026, team, n, pick(slug + "role", ["Captain", "Starter", "Reserve", "Honorary captain"]),
                pick(slug + "line", [
                    "Bringing the energy from courtside to center court.",
                    "Long-time celebrity hooper with a soft midrange.",
                    "Fan favorite back for another All-Star weekend.",
                    "First-time All-Star celebrity game participant.",
                ]),
                article_image_for("celeb-" + slug),
            ))
    cur.executemany(
        "INSERT INTO celebrity_allstar (year, team, name, role, tagline, image) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_allstar_votes(cur):
    # Deterministic seed: each user casts a frontcourt + backcourt ballot per conference
    rows = []
    user_specs = [
        (1, "East", "F", "jayson-tatum"), (1, "East", "G", "jalen-brunson"),
        (1, "West", "F", "luka-doncic"), (1, "West", "G", "shai-gilgeous-alexander"),
        (2, "East", "F", "giannis-antetokounmpo"), (2, "East", "G", "donovan-mitchell"),
        (2, "West", "F", "kevin-durant"), (2, "West", "G", "stephen-curry"),
        (3, "West", "F", "victor-wembanyama"), (3, "West", "G", "kyrie-irving"),
        (4, "East", "F", "paolo-banchero"), (4, "East", "G", "tyrese-haliburton"),
    ]
    for u, conf, pos, p in user_specs:
        rows.append((u, 2026, conf, pos, p, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")))
    cur.executemany(
        "INSERT INTO allstar_votes (user_id, year, conference, position, player_slug, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def seed_follows_alerts(cur):
    follows = [
        (1, "team", "lakers", 16, 1), (1, "player", "lebron-james", None, 1),
        (1, "player", "luka-doncic", None, 0), (1, "team", "thunder", 14, 0),
        (2, "team", "celtics", 1, 1), (2, "player", "jayson-tatum", None, 1),
        (2, "player", "jrue-holiday", None, 0),
        (3, "team", "mavericks", 11, 1), (3, "player", "luka-doncic", None, 1),
        (3, "player", "kyrie-irving", None, 1),
        (4, "team", "knicks", 2, 1), (4, "player", "jalen-brunson", None, 1),
        (4, "player", "karl-anthony-towns", None, 0),
    ]
    for u, kind, slug, tid, alert in follows:
        cur.execute(
            "INSERT INTO follows (user_id, kind, target_slug, target_id, alert_on, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (u, kind, slug, tid, alert, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )
    alerts = [
        (1, "tipoff", "lakers", "Tipoff alert: Lakers"),
        (1, "score_swing", "lakers", "Lakers score swing alert (>=10)"),
        (1, "player_news", "lebron-james", "Breaking news alerts for LeBron James"),
        (2, "tipoff", "celtics", "Tipoff alert: Celtics"),
        (2, "all_star_vote_open", "", "All-Star fan vote open window"),
        (3, "tipoff", "mavericks", "Tipoff alert: Mavericks"),
        (3, "score_swing", "mavericks", "Mavericks score swing alert (>=10)"),
        (3, "player_news", "luka-doncic", "Breaking news alerts for Luka Doncic"),
        (4, "tipoff", "knicks", "Tipoff alert: Knicks"),
        (4, "player_news", "jalen-brunson", "Breaking news alerts for Jalen Brunson"),
    ]
    for u, kind, slug, label in alerts:
        cur.execute(
            "INSERT INTO alerts (user_id, kind, target_slug, label, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (u, kind, slug, label, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )


def seed_user_extras(cur, games):
    # saved games + ticket orders + wishlist + preferences
    saved = [
        (1, 1, "Worth saving for the highlight"), (1, 3, "Game 7 candidate"),
        (2, 1, "Cavs road closeout"), (2, 5, "Conference Finals placeholder"),
        (3, 2, "Spurs march"), (3, 4, "Wolves rebound shot"),
        (4, 1, "East matchup save"), (4, 3, "Detroit revenge tour"),
    ]
    for uid, gid, note in saved:
        cur.execute(
            "INSERT INTO saved_games (user_id, game_id, note, created_at) VALUES (?, ?, ?, ?)",
            (uid, gid, note, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )
    # Ticket orders (5 confirmed purchases)
    ticket_specs = [
        (1, 5, "Lower Bowl", "12", 4, 280.0),
        (2, 6, "Suite Level", "C", 2, 540.0),
        (3, 5, "Floor Seats", "1", 2, 1100.0),
        (3, 9, "Mezzanine", "8", 3, 165.0),
        (4, 7, "Lower Bowl", "9", 2, 320.0),
    ]
    for uid, gid, section, row_label, seats, price in ticket_specs:
        total = round(price * seats + 8.5, 2)
        conf = f"NBA-TIX-{uid:02d}{gid:03d}"
        cur.execute(
            "INSERT INTO ticket_orders (user_id, game_id, section, row_label, seats, "
            "price_each, total, confirmation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, gid, section, row_label, seats, price, total, conf,
             REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )
    # Store wishlist
    wishlist = [
        (1, "los-angeles-lakers-icon-swingman-jersey", "For LeBron's birthday"),
        (1, "denver-nuggets-2024-champions-tee", ""),
        (2, "boston-celtics-association-edition-jersey", "Game-day fit"),
        (3, "dallas-mavericks-statement-hoodie", "Mavs gear"),
        (4, "new-york-knicks-courtside-long-sleeve", "Office Fridays"),
    ]
    for uid, slug, note in wishlist:
        cur.execute(
            "INSERT INTO store_wishlist (user_id, product_slug, note, created_at) VALUES (?, ?, ?, ?)",
            (uid, slug, note, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )
    # Preferences
    prefs = [
        (1, 0, "America/Los_Angeles", 1, 1, "Auto"),
        (2, 1, "America/New_York", 1, 0, "1080p"),
        (3, 0, "America/Chicago", 0, 1, "4K"),
        (4, 1, "America/New_York", 1, 1, "720p"),
    ]
    for uid, hide_scores, tz, email_news, push, quality in prefs:
        cur.execute(
            "INSERT INTO user_preferences (user_id, hide_scores, timezone, email_news, "
            "push_alerts, league_pass_quality, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (uid, hide_scores, tz, email_news, push, quality,
             REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )


def seed_article_comments(cur):
    rows = [
        (1, "celtics-defense-sets-tone-in-latest-home-win", "Boston's switching D has been the story of the playoffs.", 12),
        (2, "celtics-defense-sets-tone-in-latest-home-win", "Tatum closing strong made the difference.", 7),
        (3, "doncic-and-thunder-guards-prepare-for-pace-test", "Mavs need to slow OKC's transition.", 5),
        (4, "doncic-and-thunder-guards-prepare-for-pace-test", "Brunson-Booker hypothetical would be wild.", 9),
        (1, "wembanyama-s-rim-protection-changes-spurs-math", "Wembanyama makes opponents shoot floaters.", 18),
        (2, "wembanyama-s-rim-protection-changes-spurs-math", "Game changing presence on D.", 4),
        (3, "haliburton-fuels-indiana-s-early-offense", "Hit-ahead game is unstoppable.", 6),
        (4, "lakers-warriors-condensed-game", "LeBron's late paint touches sealed it.", 11),
        (1, "brunson-s-footwork-keeps-knicks-offense-steady", "Footwork is the most underrated skill.", 8),
        (2, "bucks-focus-on-half-court-spacing", "Giannis-Dame fit only works when shooters hit.", 10),
    ]
    for uid, slug, body, upvotes in rows:
        cur.execute(
            "INSERT INTO article_comments (user_id, article_slug, body, upvotes, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, slug, body, upvotes, REF_DATE.strftime("%Y-%m-%d %H:%M:%S.000000")),
        )


def seed_stat_leaderboards(cur, players_rows):
    cats = [
        ("ppg", 5), ("rpg", 6), ("apg", 7), ("spg", 8), ("bpg", 9),
        ("fg_pct", 10), ("three_pct", 11),
    ]
    for cat, idx in cats:
        sorted_players = sorted(players_rows, key=lambda r: -r[idx])
        for rank, row in enumerate(sorted_players[:25], 1):
            cur.execute(
                "INSERT INTO stat_leaderboards (category, rank, player_slug, team_slug, value) "
                "VALUES (?, ?, ?, ?, ?)",
                (cat, rank, row[1], "", row[idx]),
            )


def normalize_indexes(cur):
    rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    ).fetchall()
    for name, _ in rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)


def main(db_path=None):
    target = db_path or DB
    conn = sqlite3.connect(target)
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()
    if already_extended(cur):
        print("[deepen] already applied — skipping")
        conn.close()
        return

    for ddl in SCHEMA:
        cur.execute(ddl)

    teams = cur.execute("SELECT slug, name FROM teams ORDER BY id").fetchall()
    players_rows = cur.execute(
        "SELECT id, slug, name, team_id, position, ppg, rpg, apg, spg, bpg, fg_pct, three_pct "
        "FROM players ORDER BY id"
    ).fetchall()
    players_by_slug = {p[1]: p for p in players_rows}
    users = cur.execute("SELECT id, username, email FROM users ORDER BY id").fetchall()
    games = cur.execute(
        "SELECT g.id, g.home_team_id, g.away_team_id, g.home_score, g.away_score, g.status, "
        "ht.slug, at.slug FROM games g JOIN teams ht ON ht.id=g.home_team_id "
        "JOIN teams at ON at.id=g.away_team_id ORDER BY g.id"
    ).fetchall()

    seed_awards_and_votes(cur, teams, players_by_slug, users)
    seed_draft(cur)
    seed_player_extras(cur, players_rows)
    seed_team_news(cur, teams)
    seed_videos(cur, players_rows, teams)
    seed_game_extras(cur, games)
    seed_fantasy(cur, players_rows, users)
    seed_celebrity(cur)
    seed_allstar_votes(cur)
    seed_follows_alerts(cur)
    seed_user_extras(cur, games)
    seed_article_comments(cur)
    seed_stat_leaderboards(cur, players_rows)

    mark_extended(cur)
    normalize_indexes(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print("[deepen] applied")


if __name__ == "__main__":
    main()
