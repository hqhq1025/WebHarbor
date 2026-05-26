#!/usr/bin/env python3
"""R3 polish extension for sites/espn — direct sqlite3 INSERT only.

Why this script exists (gotcha #14): the shipped HF `instance_seed/espn.db`
has drifted from `seed_data.py`. Rebuilding via `from app import app` would
overwrite the R1+R2 rows the live site has served for months. R3 piggybacks
on the same direct-INSERT pattern as `_r2_extend.py`.

What R3 adds on top of R2:
  * ~970 articles      → 2000+ total (target 2000+)
  * ~700 player_stats  → 1200+ total (target 1200+)
  * ~675 games         → 1200+ total (target 1200+)
  * 3 NEW tables seeded:
      betting_odds   (~140 rows) — moneyline / spread / over-under for games
      awards         (~80 rows)  — MVP / Cy / Hart / Vezina / Ballon d'Or…
      draft_picks    (~190 rows) — 2024 NFL Draft + 2024 NBA Draft mock
  * podcasts table (10 rows) so /podcasts has real data
  * Marker row sport_slug '_r3_marker' (id=100) — idempotent.

Determinism: every numeric/text field is derived from an md5 of a stable key
(team slug + date + index), so this script can be re-run on any host and
produce a byte-identical DB.

Idempotent: gated on `_r3_marker` row in `sports`. Re-running is a no-op.
"""
import hashlib
import json
import os
import sqlite3
from datetime import date, timedelta

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  'instance_seed', 'espn.db')
ANCHOR = date(2024, 4, 10)


def h(key: str, mod: int, offset: int = 0) -> int:
    """Deterministic hash → int in [offset, offset+mod)."""
    return offset + int.from_bytes(
        hashlib.md5(key.encode()).digest()[:4], 'big') % mod


def hf(key: str, lo: float, hi: float) -> float:
    """Deterministic hash → float in [lo, hi)."""
    return lo + (h(key, 10_000) / 10_000.0) * (hi - lo)


def hpick(key: str, seq):
    """Deterministic pick from a sequence."""
    return seq[h(key, len(seq))]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fetch_one(cur, sql, args=()):
    cur.execute(sql, args)
    row = cur.fetchone()
    return row[0] if row else None


def already_extended(cur) -> bool:
    return bool(fetch_one(cur,
        "SELECT 1 FROM sports WHERE slug='_r3_marker'"))


def mark_extended(cur):
    cur.execute(
        "INSERT INTO sports (id, name, slug, display_name, url_prefix, "
        "nav_order, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (100, 'R3 marker', '_r3_marker', 'r3_extend applied',
         '/_internal/', 100, 0))


def slugify(text: str) -> str:
    out = (text.lower().replace("'", '').replace('"', '').replace('&', 'and')
           .replace('.', '').replace(',', '').replace('?', '')
           .replace(':', '').replace('/', '-').replace('—', '-')
           .replace(' ', '-'))
    out = ''.join(c for c in out if c.isalnum() or c == '-')
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')


# ─── 1. New tables (CREATE IF NOT EXISTS — schema migration) ──────────────────

NEW_TABLES = [
    """CREATE TABLE IF NOT EXISTS betting_odds (
        id INTEGER PRIMARY KEY,
        game_id INTEGER NOT NULL,
        sport_slug VARCHAR(20),
        home_moneyline INTEGER,
        away_moneyline INTEGER,
        spread_favorite VARCHAR(10),
        spread_line FLOAT,
        total FLOAT,
        over_odds INTEGER,
        under_odds INTEGER,
        opened_label VARCHAR(40),
        status VARCHAR(20),
        sportsbook VARCHAR(40)
    )""",
    """CREATE TABLE IF NOT EXISTS awards (
        id INTEGER PRIMARY KEY,
        sport_slug VARCHAR(20),
        season VARCHAR(20),
        award_name VARCHAR(80),
        award_slug VARCHAR(80),
        winner_player_id INTEGER,
        winner_team_id INTEGER,
        finalists TEXT,
        voting_share FLOAT,
        announced_date VARCHAR(20)
    )""",
    """CREATE TABLE IF NOT EXISTS draft_picks (
        id INTEGER PRIMARY KEY,
        sport_slug VARCHAR(20),
        season VARCHAR(20),
        round INTEGER,
        pick INTEGER,
        overall_pick INTEGER,
        team_id INTEGER,
        player_name VARCHAR(150),
        position VARCHAR(20),
        school VARCHAR(120),
        country VARCHAR(60),
        height VARCHAR(10),
        weight INTEGER,
        scout_grade FLOAT,
        notes VARCHAR(300),
        is_mock INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS podcasts (
        id INTEGER PRIMARY KEY,
        title VARCHAR(200),
        slug VARCHAR(200),
        host VARCHAR(200),
        sport_slug VARCHAR(20),
        description TEXT,
        episode_count INTEGER,
        latest_episode_title VARCHAR(200),
        latest_episode_date VARCHAR(20),
        duration_minutes INTEGER
    )""",
    "CREATE INDEX IF NOT EXISTS ix_betting_odds_game_id ON betting_odds (game_id)",
    "CREATE INDEX IF NOT EXISTS ix_betting_odds_sport_slug ON betting_odds (sport_slug)",
    "CREATE INDEX IF NOT EXISTS ix_awards_sport_slug ON awards (sport_slug)",
    "CREATE INDEX IF NOT EXISTS ix_draft_picks_sport_slug ON draft_picks (sport_slug)",
    "CREATE INDEX IF NOT EXISTS ix_podcasts_slug ON podcasts (slug)",
]


def create_new_tables(cur):
    for sql in NEW_TABLES:
        cur.execute(sql)


# ─── 2. Articles ──────────────────────────────────────────────────────────────

# Each entry: (title_tpl, body_tpl)
R3_NBA_TEMPLATES = [
    ("Playoff bracket primer: how the {team} match up with the {opp}",
     "With seeding locked in, the {team}-{opp} first-round series should hinge on which side controls the paint. {star} averaged {pts} points across the regular-season series."),
    ("MVP watch: {star} crashes the top three after big April",
     "{star} finished the month with averages that put the {team} guard squarely in the MVP race. National TV games and clutch numbers should help the case."),
    ("Inside the {team}' closing lineup math",
     "The {team} coaching staff is split on the final spot in the closing lineup. {star}'s plus-minus in fourth quarters is the strongest argument for a bigger role."),
    ("Trade-deadline reaction: how the {team} reshaped the bench",
     "Front-office sources walked through the calculus behind the {team}' deadline-day moves. {star} called the additions 'exactly what we needed for the playoff push.'"),
    ("Ten takeaways from the {team}' road trip",
     "A six-game trip revealed the truth about the {team}. {star} carried the offense, but defensive rotations broke down in the losses to the {opp}."),
    ("{team} mailbag: rotation, contracts, and the playoff plan",
     "Beat reporters open the mailbag on the {team}. Subjects include {star}'s minutes, the next-summer cap sheet, and what a deep playoff run would change."),
    ("Best lineup data: {team} five-out look thrives vs. {opp}",
     "Per Cleaning the Glass tracking, the {team}' five-out lineup with {star} outscored opponents by {pts} points per 100 possessions across the past month."),
    ("How the {team} are using {star} as a tagger on defense",
     "A small wrinkle in pick-and-roll coverage has the {team} sending {star} to tag the roller. Opponents have shot {pts}% on those possessions in April."),
    ("Free-agency preview: {team} face big decisions on {star}",
     "{star} is entering a contract year and the {team} front office has a fork in the road. Cap holds, the apron, and the second tax line all factor in."),
    ("Power Rankings: the {team} jump into the top five",
     "After the win over the {opp}, the {team} climb into the top five of this week's rankings. {star} is playing the best basketball of the season."),
    ("Court vision: scouting {star} as a playmaker",
     "{star} is averaging a career-high {pts} assists, and the eye test backs the numbers up. The {team} unlocking a new offensive level."),
    ("Five questions for the {team} before Game 1 vs. {opp}",
     "Will {star} guard the opposing star? Can the bench give them ten minutes? Five questions ahead of the {team}' first-round opener."),
]

R3_NFL_TEMPLATES = [
    ("Mock Draft 5.0: {team} grab a {pos} at pick 14",
     "Our final mock has the {team} pivoting to a {pos} in the first round. Front-office sources call the position 'their biggest hole heading into 2024.'"),
    ("Free-agent signings every {team} fan should know",
     "Beyond the marquee names, the {team} added depth on both lines. {star} called the locker-room shake-up 'a needed reset.'"),
    ("Why the {team} pass rush should jump in 2024",
     "Coaching changes and a new edge package should help the {team} defensive front. {star} is poised for a contract-year breakout."),
    ("Schedule release: {team} get three primetime games",
     "The NFL released the 2024 schedule, and the {team} land three primetime windows. {star} versus the {opp} on Sunday Night Football is the marquee draw."),
    ("Draft-day rumors: the {team} are calling about a trade up",
     "League sources say the {team} have called multiple teams ahead of them in the order. The target is a top-10 prospect at {pos}."),
    ("Cap space tracker: where the {team} stand",
     "After restructures and post-June 1 cuts, the {team} project roughly $18M in usable cap space heading into camp. {star}'s extension is the next domino."),
    ("Position battle: who starts at {pos} for the {team}?",
     "An open competition is brewing in {team} camp at {pos}. The veteran has the inside track, but the rookie has impressed in offseason workouts."),
    ("OTA notes: {team} offense looks faster, more spread out",
     "Beat reporters tracked tempo at {team} OTAs and saw a faster, more spread-out attack. {star} took most of the first-team reps."),
    ("How {star} is preparing for a leap in Year 3",
     "{star} added muscle and refined the route tree this offseason. The {team} expect a Pro Bowl jump as the offense centers more touches around the third-year player."),
    ("Five {team} stats that will define 2024",
     "Red-zone touchdown rate, third-down conversion, and pressure rate top the list. {star}'s usage in the play-action game is the variable to watch."),
]

R3_MLB_TEMPLATES = [
    ("{star} extends hit streak as {team} sweep {opp}",
     "{star} pushed the hit streak to {pts} games and the {team} completed a three-game sweep of the {opp}. The bullpen finished the job with two scoreless innings."),
    ("Rotation reset: how the {team} plan to navigate May",
     "With an off-day in the schedule, the {team} flip the order of the rotation. {star} will pitch the series opener against the {opp}."),
    ("Top prospect watch: who's next up for the {team}?",
     "The {team} farm system has a Triple-A bat ready to debut. Insiders expect a call-up by Memorial Day."),
    ("Hot-take Tuesday: the {team} bullpen problem is real",
     "Despite a hot offense, the {team} bullpen has been the difference in losses. {star} is the only consistent late-inning option."),
    ("Numbers behind the {team} early run",
     "Run differential, expected wins, and base-running value all point to a sustainable {team} hot streak. {star} leads MLB in WAR."),
    ("{star} returns from injured list ahead of weekend series",
     "After a stint on the IL, {star} is back in the lineup. The {team} need the bat as they head into a divisional series with the {opp}."),
    ("Trade-deadline preview: the {team}' biggest need",
     "Two months in, the {team} look like buyers. Front-office sources say the priority is a left-handed reliever."),
    ("Why the {team} are leaning into the shift-replacement era",
     "MLB rule changes have forced the {team} to rebuild infield positioning. {star} has played a key role in the new alignment."),
]

R3_NHL_TEMPLATES = [
    ("{team} clinch playoff spot with win over {opp}",
     "The {team} officially clinched a postseason berth after the {pts}-point night from {star}. The {opp} will need help to lock in their own seed."),
    ("First-round preview: how the {team} stack up vs. {opp}",
     "Special teams should decide the {team}-{opp} first-round series. {star} sets the table on the top power-play unit."),
    ("Goalie carousel: who starts Game 1 for the {team}?",
     "Coach is keeping the Game 1 starter under wraps. {star} took the majority of reps at the most recent practice."),
    ("Trade-deadline grades: did the {team}' moves pay off?",
     "Two months removed from the trade deadline, the {team} additions are starting to show in the standings. {star} has been the biggest beneficiary."),
    ("Penalty kill turnaround: how the {team} fixed it",
     "An assistant-coach tweak to the diamond formation flipped the {team} penalty kill from 28th to top-five over the last month."),
    ("{star} closes in on milestone with goal vs. {opp}",
     "{star} scored the game-winner over the {opp} and now sits one goal away from a career milestone."),
    ("Awards watch: the case for {star} as Hart Trophy finalist",
     "Production at five-on-five, ice time against top lines, and game-state value all line up for {star}. A finalist appearance feels increasingly likely."),
]

R3_SOCCER_TEMPLATES = [
    ("Transfer-window rumors: where will {star} land?",
     "{star}'s contract is winding down and the {team} are bracing for a high-stakes summer window. Premier League sides and Saudi Pro League clubs are circling."),
    ("Tactical breakdown: how the {team} broke down the {opp} press",
     "A 4-3-3 with an inverted full-back gave the {team} a numerical edge against the {opp} press. {star} was the release valve."),
    ("Champions League draw reaction: the {team} get a manageable path",
     "The {team} drew a Europa League survivor in the next round. {star} called the bracket 'a real opportunity.'"),
    ("Manager interview: {star}'s next steps in the {team} system",
     "In a long-form interview, the {team} manager outlined how {star} fits into the long-term project. Squad rotation and minutes management top the priorities."),
    ("Top scorer race: the gap between {star} and the pack",
     "{star} leads the top-scorer race with {pts} goals. The closest challenger is {pts} behind heading into the run-in."),
    ("Why the {team} are winning the recruitment war",
     "Data-led scouting and a strong academy pipeline have the {team} consistently ahead of rivals. {star} is the latest blue-chip development."),
]

R3_NCAAF_TEMPLATES = [
    ("Spring game recap: {team} flash new look",
     "The {team} closed spring practice with an open scrimmage. The new offense, built around {star}, looked sharp in red-zone packages."),
    ("Transfer portal updates: who's in and out at {team}",
     "Five players entered the portal and two transfers committed to {team} this week. Coaches expect a quiet final stretch."),
    ("NIL roundup: the deals shaping {team}'s 2024 class",
     "Multiple six-figure NIL deals are now in place for the {team} 2024 recruiting class. {star} headlines the cohort."),
]

R3_NCAAM_TEMPLATES = [
    ("Top-25 reaction: the {team} climb after {opp} win",
     "A road win over the {opp} pushes the {team} back into the top fifteen. {star} hit the dagger three with under a minute left."),
    ("Conference tournament preview: the {team} as a seed",
     "Coaches will land the {team} somewhere on the protected seed line. {star}'s availability remains the key swing factor."),
    ("Stock report: which {team} players are rising for the NBA Draft?",
     "Pre-draft camps and combine measurements will refine the {team} prospect group. {star} is the most likely first-round pick."),
]

R3_NCAAW_TEMPLATES = [
    ("Recruiting class breakdown: {team} land a five-star",
     "The {team} secured a commitment from a top-five recruit. Coaches plan to deploy the freshman immediately alongside {star}."),
    ("Final Four scouting: how {team} match up",
     "Spacing, depth, and three-point shooting will define {team}'s Final Four chances. {star} is the program's leading scorer."),
]

R3_FANTASY_TEMPLATES = [
    ("Fantasy waiver wire: top adds for week ahead",
     "Injuries and rotation shifts created several fantasy-relevant adds. Streaming options at small forward and goalie are the priority."),
    ("Trade value chart: who's up, who's down",
     "Our trade value chart is refreshed after the latest week. Bigs with multi-category profile gained value, scoring guards held."),
    ("Punt-points build: a guide for the playoffs",
     "The classic punt-points build still works in the fantasy playoffs. Field-goal percentage and rebounds are the categories to chase."),
    ("Mock draft: dynasty rookie order revealed",
     "Our dynasty rookie mock locks in the first round. The top three picks are interchangeable depending on team build."),
    ("Lineup decisions: who to start in the championship",
     "Matchups, pace, and Vegas totals all factor in. Our championship lineup column highlights the must-starts and bench candidates."),
]

R3_TENNIS_TEMPLATES = [
    ("Madrid Open draw analysis: top half wide open",
     "Withdrawals at the top of the Madrid Open bracket open a path for a first-time Masters semifinalist."),
    ("Clay-court swing: who's peaking heading into Roland Garros",
     "Form charts on clay show the usual suspects, but a young player is creeping into title contention."),
]

R3_GOLF_TEMPLATES = [
    ("Masters in the books: what we learned at Augusta",
     "Course-management calls and short-game finesse decided the green jacket. Putting on the back nine remains the defining stat."),
    ("PGA Championship preview: the contenders at Valhalla",
     "Course history, recent form, and weather all factor in. Several players have major motivation after near-misses earlier in the season."),
]

R3_MMA_TEMPLATES = [
    ("UFC card weigh-in: who made weight, who didn't",
     "Two fighters missed weight on Friday. The main event is still on, but at a catchweight."),
    ("Title contender update: the next challenger emerges",
     "After a dominant win on Saturday, a new title challenger is at the front of the line. Negotiations are reportedly already underway."),
]

R3_BET_TEMPLATES = [
    ("Best bets: three picks for tonight's slate",
     "Our betting team breaks down three favorite plays on tonight's slate. Spreads, totals, and a player-prop highlight the picks."),
    ("ESPN BET edge: where the model disagrees with the market",
     "The model flags two games where the closing line should move toward the underdog. Both involve back-to-back travel for the favorite."),
    ("Futures watch: which long-shots to keep on the ticket",
     "Long-shot futures still have value with a few weeks left in the regular season. A first-time MVP candidate leads our list."),
]

R3_PODCAST_TEMPLATES = [
    ("New podcast episode: deep dive on the {team} season",
     "Our podcast team unpacks the {team}'s season in a 45-minute conversation. {star}'s arc and the front-office plan headline the talk."),
]


PLAN = [
    ('nba',      R3_NBA_TEMPLATES,       240, 5),
    ('nfl',      R3_NFL_TEMPLATES,       180, 5),
    ('mlb',      R3_MLB_TEMPLATES,       130, 6),
    ('nhl',      R3_NHL_TEMPLATES,       130, 6),
    ('soccer',   R3_SOCCER_TEMPLATES,     90, 6),
    ('ncaaf',    R3_NCAAF_TEMPLATES,      40, 8),
    ('ncaam',    R3_NCAAM_TEMPLATES,      40, 8),
    ('ncaaw',    R3_NCAAW_TEMPLATES,      40, 8),
    ('fantasy',  R3_FANTASY_TEMPLATES,    55, 7),
    ('tennis',   R3_TENNIS_TEMPLATES,     20, 6),
    ('golf',     R3_GOLF_TEMPLATES,       20, 6),
    ('mma',      R3_MMA_TEMPLATES,        20, 6),
]


def article_authors(idx: int) -> str:
    pool = ['Adrian Wojnarowski', 'Ramona Shelburne', 'Tim MacMahon',
            'Brian Windhorst', 'Jeremy Fowler', 'Adam Schefter',
            'Jeff Passan', 'Greg Wyshynski', 'Marc Stein',
            'Kevin Pelton', 'Zach Lowe', 'Bill Connelly',
            'Tom Hamilton', 'David Schoenfield', 'Eric Karabell',
            'Field Yates', 'Mike Reiss', 'Bobby Marks',
            'Jay Bilas', 'Charlie Creme', 'Mina Kimes',
            'ESPN Staff', 'Associated Press', 'Reuters']
    return pool[idx % len(pool)]


def make_articles(cur):
    """Insert ~970 deterministic R3 articles dated 2023-10-01 .. 2024-04-09."""
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM articles") or 0) + 1
    existing_slugs = {r[0] for r in
                      cur.execute("SELECT slug FROM articles").fetchall()}

    teams_by_sport = {}
    for sport_slug in ('nba', 'nfl', 'nhl', 'mlb', 'soccer', 'ncaaf',
                       'ncaam', 'ncaaw'):
        rows = cur.execute(
            "SELECT id, full_name, slug FROM teams "
            "WHERE sport_slug=? ORDER BY id", (sport_slug,)).fetchall()
        teams_by_sport[sport_slug] = rows

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
    inserted = 0
    for sport_slug, templates, count, headline_every in PLAN:
        teams = (teams_by_sport.get(sport_slug)
                 or teams_by_sport.get('nba'))
        if not teams:
            continue
        for i in range(count):
            t_idx = h(f'r3-{sport_slug}-team-{i}', len(teams))
            opp_idx = h(f'r3-{sport_slug}-opp-{i}', len(teams))
            if opp_idx == t_idx:
                opp_idx = (opp_idx + 1) % len(teams)
            team_id, team_name, team_slug = teams[t_idx]
            _, opp_name, _ = teams[opp_idx]
            star_row = stars_by_team.get(team_id)
            star_name = star_row[0] if star_row else f'{team_name} captain'
            star_pos = star_row[1] if star_row else 'F'

            tpl_i = h(f'r3-{sport_slug}-tpl-{i}', len(templates))
            title_tpl, body_tpl = templates[tpl_i]
            score_a = h(f'r3-{sport_slug}-sa-{i}', 30, 95)
            score_b = h(f'r3-{sport_slug}-sb-{i}', 25, 88)
            pts = h(f'r3-{sport_slug}-pts-{i}', 28, 18)
            pos_pool = ['EDGE', 'OT', 'CB', 'WR', 'LB', 'S']
            pos_pick = pos_pool[h(f'r3-{sport_slug}-pos-{i}', len(pos_pool))]
            try:
                title = title_tpl.format(team=team_name, opp=opp_name,
                                         star=star_name, pts=pts,
                                         pos=pos_pick)
                body = body_tpl.format(team=team_name, opp=opp_name,
                                       star=star_name,
                                       score=f'{score_a}-{score_b}',
                                       pts=pts, pos=pos_pick)
            except KeyError:
                title = title_tpl
                body = body_tpl

            # date: spread Oct 2023 .. Apr 9 2024
            day_offset = h(f'r3-{sport_slug}-date-{i}', 191)
            article_date = date(2023, 10, 1) + timedelta(days=day_offset)
            # Last 12% skewed to April 2024 for "latest"
            if i >= int(count * 0.88):
                article_date = date(2024, 4, 1) + timedelta(
                    days=h(f'r3-{sport_slug}-recent-{i}', 9))

            slug = f'{slugify(title)}-r3-{sport_slug}-{i:03d}'
            if slug in existing_slugs:
                slug = f'{slug}-{next_id}'
            existing_slugs.add(slug)

            tags = json.dumps([sport_slug.upper(), team_name, star_name,
                               'R3'])
            is_headline = 1 if (i % headline_every == 0) else 0
            is_featured = 1 if (i % (headline_every * 3) == 0) else 0
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
            inserted += 1

    cur.executemany(
        "INSERT INTO articles (id, sport_slug, title, slug, subtitle, body, "
        "author, image, tags, is_headline, is_featured, created_at, "
        "published_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows_to_insert)
    return inserted


# ─── 3. Games ─────────────────────────────────────────────────────────────────

NBA_VENUES = ['TD Garden', 'Crypto.com Arena', 'Madison Square Garden',
              'Chase Center', 'Ball Arena', 'Paycom Center',
              'Kaseya Center', 'American Airlines Center',
              'Footprint Center', 'Fiserv Forum', 'Spectrum Center']
NHL_VENUES = ['TD Garden', 'Madison Square Garden', 'United Center',
              'Rogers Arena', 'Scotiabank Arena', 'Bell Centre',
              'Wells Fargo Center', 'Capital One Arena',
              'Amerant Bank Arena', 'Honda Center', 'PPG Paints Arena']
NFL_VENUES = ['Arrowhead Stadium', 'AT&T Stadium', 'SoFi Stadium',
              'Lambeau Field', 'Lincoln Financial Field', 'M&T Bank Stadium',
              'Highmark Stadium', 'GEHA Field', 'MetLife Stadium',
              'Levi\'s Stadium', 'Empower Field at Mile High']
MLB_VENUES = ['Yankee Stadium', 'Fenway Park', 'Dodger Stadium',
              'Wrigley Field', 'Oracle Park', 'Tropicana Field',
              'Citi Field', 'Petco Park', 'Coors Field',
              'Camden Yards', 'Globe Life Field']
SOCCER_VENUES = ['Emirates Stadium', 'Old Trafford', 'Anfield',
                 'Stamford Bridge', 'Etihad Stadium',
                 'Tottenham Hotspur Stadium', 'Camp Nou', 'Santiago Bernabéu']


def make_games(cur):
    """Add ~675 historical games across NBA/NHL/MLB/NFL/Soccer."""
    next_id = (fetch_one(cur, "SELECT COALESCE(MAX(id),0) FROM games") or 0) + 1
    inserted = 0
    rows_to_insert = []

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
    soccer_teams = cur.execute(
        "SELECT id, full_name, slug FROM teams WHERE sport_slug='soccer' "
        "ORDER BY id").fetchall()

    def star_for(team_id):
        row = cur.execute(
            "SELECT name, position FROM players WHERE team_id=? "
            "ORDER BY id LIMIT 1", (team_id,)).fetchone()
        return row or ('Star Player', 'F')

    # NBA: 220 more regular-season (2023-11 .. 2024-04-08)
    for i in range(220):
        a = h(f'r3-nba-a-{i}', len(nba_teams))
        b = h(f'r3-nba-b-{i}', len(nba_teams))
        if a == b:
            b = (b + 1) % len(nba_teams)
        home = nba_teams[a]
        away = nba_teams[b]
        day_offset = h(f'r3-nba-day-{i}', 155)
        gdate = date(2023, 11, 1) + timedelta(days=day_offset)
        hs = h(f'r3-nba-hs-{i}', 30, 95)
        as_ = h(f'r3-nba-as-{i}', 30, 88)
        ven = NBA_VENUES[i % len(NBA_VENUES)]
        star_h = star_for(home[0])
        leaders = json.dumps({
            'top_scorer_name': star_h[0],
            'top_scorer_pts': h(f'r3-nba-tp-{i}', 25, 18),
            'top_scorer_team': home[1],
            'top_scorer_position': star_h[1],
            'top_rebounder_name': star_h[0],
            'top_rebounder_reb': h(f'r3-nba-tr-{i}', 8, 6),
            'top_rebounder_team': home[1],
            'top_assists_name': star_h[0],
            'top_assists_ast': h(f'r3-nba-ta-{i}', 7, 4),
            'top_assists_team': home[1],
            'home_high_scorer': star_h[0],
            'home_high_points': h(f'r3-nba-hh-{i}', 25, 18),
            'away_high_scorer': star_for(away[0])[0],
            'away_high_points': h(f'r3-nba-ah-{i}', 22, 16),
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

    # NHL: 160 more regular season (2023-10 .. 2024-04-08)
    for i in range(160):
        a = h(f'r3-nhl-a-{i}', len(nhl_teams))
        b = h(f'r3-nhl-b-{i}', len(nhl_teams))
        if a == b:
            b = (b + 1) % len(nhl_teams)
        home = nhl_teams[a]
        away = nhl_teams[b]
        day_offset = h(f'r3-nhl-day-{i}', 180)
        gdate = date(2023, 10, 10) + timedelta(days=day_offset)
        hs = h(f'r3-nhl-hs-{i}', 6, 1)
        as_ = h(f'r3-nhl-as-{i}', 6, 1)
        ven = NHL_VENUES[i % len(NHL_VENUES)]
        star_h = star_for(home[0])
        leaders = json.dumps({
            'top_scorer_name': star_h[0],
            'top_scorer_pts': h(f'r3-nhl-tp-{i}', 3, 1),
            'top_scorer_team': home[1],
            'top_scorer_position': star_h[1],
            'home_high_scorer': star_h[0],
            'home_high_points': h(f'r3-nhl-hh-{i}', 3, 1),
            'away_high_scorer': star_for(away[0])[0],
            'away_high_points': h(f'r3-nhl-ah-{i}', 3, 1),
        })
        rows_to_insert.append((
            next_id, 'nhl', home[0], away[0], hs, as_,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            '7:00 PM ET', 'final', 'Final', 'ESPN+', ven,
            f"{home[1]} edged the {away[1]} {hs}-{as_}.",
            'https://www.ticketmaster.com', leaders))
        next_id += 1
        inserted += 1

    # MLB: 120 more (2024-04-01 .. 2024-04-09 + 2023 historical)
    for i in range(120):
        a = h(f'r3-mlb-a-{i}', len(mlb_teams))
        b = h(f'r3-mlb-b-{i}', len(mlb_teams))
        if a == b:
            b = (b + 1) % len(mlb_teams)
        home = mlb_teams[a]
        away = mlb_teams[b]
        # Spread across full 2023 season + early 2024 (3-28 .. 4-09)
        if i < 80:
            day_offset = h(f'r3-mlb-day-{i}', 180)
            gdate = date(2023, 4, 1) + timedelta(days=day_offset)
        else:
            day_offset = h(f'r3-mlb-2024-{i}', 13)
            gdate = date(2024, 3, 28) + timedelta(days=day_offset)
        hs = h(f'r3-mlb-hs-{i}', 12, 0)
        as_ = h(f'r3-mlb-as-{i}', 12, 0)
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

    # NFL: 90 more (2022 season + 2023 season finals)
    for i in range(90):
        a = h(f'r3-nfl-a-{i}', len(nfl_teams))
        b = h(f'r3-nfl-b-{i}', len(nfl_teams))
        if a == b:
            b = (b + 1) % len(nfl_teams)
        home = nfl_teams[a]
        away = nfl_teams[b]
        if i < 50:
            # 2022 season Sep 8 2022 .. Jan 8 2023
            gdate = date(2022, 9, 8) + timedelta(days=h(f'r3-nfl-2022-{i}', 120))
        else:
            gdate = date(2023, 9, 7) + timedelta(days=h(f'r3-nfl-2023-{i}', 125))
        hs = h(f'r3-nfl-hs-{i}', 31, 10)
        as_ = h(f'r3-nfl-as-{i}', 31, 7)
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
        season = '2022' if i < 50 else '2023'
        rows_to_insert.append((
            next_id, 'nfl', home[0], away[0], hs, as_,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            '1:00 PM ET', 'final', 'Final', 'FOX', ven,
            f"({season}) {home[1]} defeated the {away[1]} {hs}-{as_}.",
            'https://www.nfl.com/tickets', leaders))
        next_id += 1
        inserted += 1

    # Soccer: 55 more (2023-24 EPL/UCL matches)
    if soccer_teams:
        for i in range(55):
            a = h(f'r3-soc-a-{i}', len(soccer_teams))
            b = h(f'r3-soc-b-{i}', len(soccer_teams))
            if a == b:
                b = (b + 1) % len(soccer_teams)
            home = soccer_teams[a]
            away = soccer_teams[b]
            day_offset = h(f'r3-soc-day-{i}', 200)
            gdate = date(2023, 8, 12) + timedelta(days=day_offset)
            hs = h(f'r3-soc-hs-{i}', 5, 0)
            as_ = h(f'r3-soc-as-{i}', 5, 0)
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
            rows_to_insert.append((
                next_id, 'soccer', home[0], away[0], hs, as_,
                gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
                '12:30 PM ET', 'final', 'FT', 'ESPN+', ven,
                f"{home[1]} drew {away[1]} {hs}-{as_}." if hs == as_
                else f"{home[1]} beat {away[1]} {hs}-{as_}.",
                'https://www.ticketmaster.com', leaders))
            next_id += 1
            inserted += 1

    # Upcoming NBA playoff games (2024-04-15 .. 2024-04-25)
    for i in range(30):
        a = h(f'r3-nba-up-a-{i}', len(nba_teams))
        b = h(f'r3-nba-up-b-{i}', len(nba_teams))
        if a == b:
            b = (b + 1) % len(nba_teams)
        home = nba_teams[a]
        away = nba_teams[b]
        gdate = date(2024, 4, 15) + timedelta(days=h(f'r3-nba-up-day-{i}', 11))
        ven = NBA_VENUES[i % len(NBA_VENUES)]
        rows_to_insert.append((
            next_id, 'nba', home[0], away[0], 0, 0,
            gdate.isoformat(), gdate.strftime('%B %-d, %Y'),
            f"{7 + (i % 3)}:00 PM ET", 'scheduled', 'Scheduled',
            'TNT', ven,
            f"First-round playoff matchup: {away[1]} at {home[1]}.",
            'https://www.ticketmaster.com', '{}'))
        next_id += 1
        inserted += 1

    cur.executemany(
        "INSERT INTO games (id, sport_slug, home_team_id, away_team_id, "
        "home_score, away_score, date, date_display, time, status, period, "
        "network, venue, recap, ticket_url, game_leaders) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows_to_insert)
    return inserted


# ─── 4. Player stats ──────────────────────────────────────────────────────────

def make_player_stats(cur):
    """Add R3 player_stats: 2022-23 season stats for many players (career
    breadth) + fill the 2023-24 season backlog beyond R2.
    """
    next_id = (fetch_one(cur,
        "SELECT COALESCE(MAX(id),0) FROM player_stats") or 0) + 1
    rows_to_insert = []

    # Pass A: backfill 2023-24 for any remaining player not yet covered
    season_24 = '2023-24'
    backfill_quotas = {'nba': 220, 'nfl': 160, 'mlb': 140, 'nhl': 200,
                       'soccer': 60}
    for sport_slug, quota in backfill_quotas.items():
        players = cur.execute(
            "SELECT p.id, p.name, p.position FROM players p "
            "WHERE p.sport_slug=? AND p.id NOT IN ("
            "  SELECT player_id FROM player_stats "
            "  WHERE stat_type='season' AND season=?) "
            "ORDER BY p.id LIMIT ?",
            (sport_slug, season_24, quota)).fetchall()
        for pid, _pname, pos in players:
            row = _make_stat_row(sport_slug, pid, pos, season_24, next_id)
            rows_to_insert.append(row)
            next_id += 1

    # Pass B: add 2022-23 season stats for the top-N per sport (career breadth)
    season_22 = '2022-23'
    historical_quotas = {'nba': 60, 'nfl': 40, 'mlb': 30, 'nhl': 30}
    for sport_slug, quota in historical_quotas.items():
        players = cur.execute(
            "SELECT p.id, p.name, p.position FROM players p "
            "WHERE p.sport_slug=? "
            "ORDER BY p.id LIMIT ?",
            (sport_slug, quota)).fetchall()
        for pid, _pname, pos in players:
            row = _make_stat_row(sport_slug, pid, pos, season_22, next_id)
            rows_to_insert.append(row)
            next_id += 1

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


def _make_stat_row(sport_slug, pid, pos, season, next_id):
    key = f'r3-{season}-{sport_slug}-{pid}'
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


# ─── 5. Betting odds ──────────────────────────────────────────────────────────

def make_betting_odds(cur):
    """Insert betting lines for ~140 games (mix of recent finals + upcoming)."""
    rows = []
    games = cur.execute(
        "SELECT id, sport_slug, home_team_id, away_team_id, status, date, "
        "       home_score, away_score "
        "FROM games "
        "WHERE date >= '2024-04-01' "
        "ORDER BY date DESC LIMIT 140").fetchall()
    sportsbooks = ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM', 'Caesars']
    odds_id = 1
    for gid, sport_slug, _hid, _aid, status, _gdate, hs, as_ in games:
        key = f'r3-odds-{gid}'
        # Choose favorite home or away
        fav_home = (h(f'{key}-fav', 2) == 0)
        spread = round(hf(f'{key}-sp', 1.5, 11.5) * 2) / 2  # half-point
        spread_disp = f'-{spread}' if spread else 'PK'
        ml_fav = -(h(f'{key}-mlf', 280, 110))
        ml_dog = h(f'{key}-mld', 320, 100)
        # totals by sport
        total_ranges = {'nba': (200, 240), 'nfl': (38, 54),
                        'mlb': (7.0, 11.5), 'nhl': (5.5, 7.0),
                        'soccer': (2.0, 3.5)}
        lo, hi = total_ranges.get(sport_slug, (40, 50))
        total = round(hf(f'{key}-tot', lo, hi) * 2) / 2
        rows.append((
            odds_id, gid, sport_slug,
            ml_fav if fav_home else ml_dog,
            ml_dog if fav_home else ml_fav,
            spread_disp,
            spread,
            total,
            -110, -110,
            'Opened 24h before tip',
            'closed' if status == 'final' else 'open',
            sportsbooks[odds_id % len(sportsbooks)],
        ))
        odds_id += 1
    cur.executemany(
        "INSERT INTO betting_odds (id, game_id, sport_slug, "
        "home_moneyline, away_moneyline, spread_favorite, spread_line, "
        "total, over_odds, under_odds, opened_label, status, sportsbook) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 6. Awards ────────────────────────────────────────────────────────────────

AWARDS_BY_SPORT = {
    'nba': [
        ('Most Valuable Player', 'mvp', '2023-24'),
        ('Defensive Player of the Year', 'dpoy', '2023-24'),
        ('Rookie of the Year', 'roy', '2023-24'),
        ('Sixth Man of the Year', 'sixth-man', '2023-24'),
        ('Most Improved Player', 'mip', '2023-24'),
        ('Coach of the Year', 'coach', '2023-24'),
        ('Most Valuable Player', 'mvp', '2022-23'),
        ('Defensive Player of the Year', 'dpoy', '2022-23'),
        ('Rookie of the Year', 'roy', '2022-23'),
    ],
    'nfl': [
        ('Most Valuable Player', 'mvp', '2023'),
        ('Offensive Player of the Year', 'opoy', '2023'),
        ('Defensive Player of the Year', 'dpoy', '2023'),
        ('Offensive Rookie of the Year', 'opo-roy', '2023'),
        ('Defensive Rookie of the Year', 'dpo-roy', '2023'),
        ('Comeback Player of the Year', 'cpoy', '2023'),
        ('Coach of the Year', 'coach', '2023'),
        ('Most Valuable Player', 'mvp', '2022'),
    ],
    'mlb': [
        ('AL Most Valuable Player', 'al-mvp', '2023'),
        ('NL Most Valuable Player', 'nl-mvp', '2023'),
        ('AL Cy Young', 'al-cy', '2023'),
        ('NL Cy Young', 'nl-cy', '2023'),
        ('AL Rookie of the Year', 'al-roy', '2023'),
        ('NL Rookie of the Year', 'nl-roy', '2023'),
        ('AL Manager of the Year', 'al-moy', '2023'),
        ('NL Manager of the Year', 'nl-moy', '2023'),
    ],
    'nhl': [
        ('Hart Trophy', 'hart', '2023-24'),
        ('Vezina Trophy', 'vezina', '2023-24'),
        ('Norris Trophy', 'norris', '2023-24'),
        ('Calder Trophy', 'calder', '2023-24'),
        ('Selke Trophy', 'selke', '2023-24'),
        ('Jack Adams Award', 'jack-adams', '2023-24'),
        ('Hart Trophy', 'hart', '2022-23'),
    ],
    'soccer': [
        ("Ballon d'Or", 'ballon-dor', '2023'),
        ('FIFA Men\'s Best', 'fifa-best', '2023'),
        ('Premier League Player of the Season', 'pl-pos', '2023-24'),
        ('Premier League Golden Boot', 'pl-gb', '2023-24'),
        ('Champions League Top Scorer', 'ucl-top', '2023-24'),
    ],
}


def make_awards(cur):
    rows = []
    aid = 1
    for sport_slug, awards in AWARDS_BY_SPORT.items():
        players = cur.execute(
            "SELECT id, name, team_id FROM players WHERE sport_slug=? "
            "ORDER BY id", (sport_slug,)).fetchall()
        if not players:
            continue
        for award_name, award_slug, season in awards:
            key = f'r3-award-{sport_slug}-{award_slug}-{season}'
            pidx = h(f'{key}-winner', len(players))
            wpid, wname, wtid = players[pidx]
            # finalists: 3 distinct names
            f_idxs = []
            attempt = 0
            while len(f_idxs) < 3 and attempt < 20:
                cand = h(f'{key}-fin-{attempt}', len(players))
                if cand != pidx and cand not in f_idxs:
                    f_idxs.append(cand)
                attempt += 1
            finalists = [{'player_id': players[i][0],
                          'name': players[i][1],
                          'votes_share': round(hf(f'{key}-vs-{i}', 0.04, 0.22), 3)}
                         for i in f_idxs]
            voting_share = round(hf(f'{key}-ws', 0.42, 0.78), 3)
            announced = '2024-04-25' if '2023-24' in season or '2023' in season else '2023-06-20'
            rows.append((
                aid, sport_slug, season, award_name, award_slug,
                wpid, wtid, json.dumps(finalists), voting_share, announced))
            aid += 1
    cur.executemany(
        "INSERT INTO awards (id, sport_slug, season, award_name, award_slug, "
        "winner_player_id, winner_team_id, finalists, voting_share, "
        "announced_date) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 7. Draft picks ───────────────────────────────────────────────────────────

NFL_DRAFT_POOL = [
    ('Caleb Williams', 'QB', 'USC', 'USA', "6'1", 215),
    ('Jayden Daniels', 'QB', 'LSU', 'USA', "6'4", 210),
    ('Drake Maye', 'QB', 'North Carolina', 'USA', "6'4", 223),
    ('Marvin Harrison Jr.', 'WR', 'Ohio State', 'USA', "6'3", 205),
    ('Malik Nabers', 'WR', 'LSU', 'USA', "6'0", 200),
    ('Rome Odunze', 'WR', 'Washington', 'USA', "6'3", 212),
    ('Brock Bowers', 'TE', 'Georgia', 'USA', "6'3", 240),
    ('Joe Alt', 'OT', 'Notre Dame', 'USA', "6'8", 321),
    ('Olu Fashanu', 'OT', 'Penn State', 'USA', "6'6", 312),
    ('JC Latham', 'OT', 'Alabama', 'USA', "6'6", 342),
    ('Taliese Fuaga', 'OT', 'Oregon State', 'USA', "6'6", 324),
    ('Troy Fautanu', 'OT', 'Washington', 'USA', "6'4", 317),
    ('Graham Barton', 'C', 'Duke', 'USA', "6'5", 313),
    ('Quinyon Mitchell', 'CB', 'Toledo', 'USA', "6'0", 195),
    ('Terrion Arnold', 'CB', 'Alabama', 'USA', "6'0", 196),
    ('Nate Wiggins', 'CB', 'Clemson', 'USA', "6'1", 173),
    ('Cooper DeJean', 'CB', 'Iowa', 'USA', "6'1", 203),
    ('Kool-Aid McKinstry', 'CB', 'Alabama', 'USA', "6'1", 195),
    ('Dallas Turner', 'EDGE', 'Alabama', 'USA', "6'4", 247),
    ('Laiatu Latu', 'EDGE', 'UCLA', 'USA', "6'5", 259),
    ('Jared Verse', 'EDGE', 'Florida State', 'USA', "6'4", 254),
    ('Chop Robinson', 'EDGE', 'Penn State', 'USA', "6'3", 254),
    ('Byron Murphy II', 'DT', 'Texas', 'USA', "6'1", 297),
    ('Jer\'Zhan Newton', 'DT', 'Illinois', 'USA', "6'2", 304),
    ('Brian Thomas Jr.', 'WR', 'LSU', 'USA', "6'4", 209),
    ('Adonai Mitchell', 'WR', 'Texas', 'USA', "6'4", 205),
    ('Xavier Worthy', 'WR', 'Texas', 'USA', "5'11", 165),
    ('Keon Coleman', 'WR', 'Florida State', 'USA', "6'4", 213),
    ('Ladd McConkey', 'WR', 'Georgia', 'USA', "6'0", 186),
    ('Bo Nix', 'QB', 'Oregon', 'USA', "6'2", 214),
    ('Michael Penix Jr.', 'QB', 'Washington', 'USA', "6'2", 216),
    ('Jackson Powers-Johnson', 'C', 'Oregon', 'USA', "6'3", 328),
]

NBA_DRAFT_POOL = [
    ('Zaccharie Risacher', 'SF', 'JL Bourg', 'France', "6'10", 204),
    ('Alex Sarr', 'C', 'Perth Wildcats', 'France', "7'1", 224),
    ('Reed Sheppard', 'PG', 'Kentucky', 'USA', "6'3", 187),
    ('Stephon Castle', 'SG', 'UConn', 'USA', "6'6", 215),
    ('Matas Buzelis', 'SF', 'G League Ignite', 'Lithuania', "6'10", 197),
    ('Donovan Clingan', 'C', 'UConn', 'USA', "7'2", 282),
    ('Rob Dillingham', 'PG', 'Kentucky', 'USA', "6'3", 165),
    ('Cody Williams', 'SF', 'Colorado', 'USA', "6'8", 178),
    ('Nikola Topic', 'PG', 'KK Crvena Zvezda', 'Serbia', "6'6", 200),
    ('Devin Carter', 'SG', 'Providence', 'USA', "6'3", 195),
    ('Ron Holland', 'SF', 'G League Ignite', 'USA', "6'8", 197),
    ('Dalton Knecht', 'SF', 'Tennessee', 'USA', "6'6", 213),
    ('Carlton Carrington', 'SG', 'Pittsburgh', 'USA', "6'4", 195),
    ('Tristan da Silva', 'SF', 'Colorado', 'Germany', "6'9", 217),
    ('Jared McCain', 'SG', 'Duke', 'USA', "6'2", 197),
    ('Yves Missi', 'C', 'Baylor', 'Cameroon', "6'10", 230),
    ('Tidjane Salaun', 'PF', 'Cholet Basket', 'France', "6'9", 212),
    ('Zach Edey', 'C', 'Purdue', 'Canada', "7'4", 299),
    ('Isaiah Collier', 'PG', 'USC', 'USA', "6'3", 205),
    ('Ja\'Kobe Walter', 'SG', 'Baylor', 'USA', "6'5", 195),
    ('Jonathan Mogbo', 'PF', 'San Francisco', 'USA', "6'8", 220),
    ('Pacome Dadiet', 'SF', 'Ulm', 'France', "6'8", 200),
    ('Bub Carrington', 'PG', 'Pittsburgh', 'USA', "6'5", 195),
    ('Kel\'el Ware', 'C', 'Indiana', 'USA', "7'0", 230),
    ('Dillon Jones', 'SF', 'Weber State', 'USA', "6'6", 235),
    ('Ryan Dunn', 'PF', 'Virginia', 'USA', "6'8", 216),
    ('AJ Johnson', 'SG', 'Illawarra Hawks', 'USA', "6'5", 175),
    ('Bobi Klintman', 'PF', 'Cairns Taipans', 'Sweden', "6'10", 215),
    ('Tyler Smith', 'PF', 'G League Ignite', 'USA', "6'10", 224),
    ('Kyle Filipowski', 'C', 'Duke', 'USA', "7'0", 248),
]


def make_draft_picks(cur):
    rows = []
    pid = 1
    nfl_teams = cur.execute(
        "SELECT id, full_name FROM teams WHERE sport_slug='nfl' "
        "ORDER BY id").fetchall()
    nba_teams = cur.execute(
        "SELECT id, full_name FROM teams WHERE sport_slug='nba' "
        "ORDER BY id").fetchall()

    # 2024 NFL Draft mock — 32 picks round 1 + 32 picks round 2 (deterministic shuffle)
    for round_n, mock_label in [(1, True), (2, True)]:
        for i in range(32):
            overall = (round_n - 1) * 32 + i + 1
            t_idx = h(f'r3-nfl-pick-{overall}', len(nfl_teams))
            tid, _tname = nfl_teams[t_idx]
            p_idx = h(f'r3-nfl-pl-{overall}', len(NFL_DRAFT_POOL))
            pname, pos, school, country, height, weight = NFL_DRAFT_POOL[p_idx]
            grade = round(hf(f'r3-nfl-gr-{overall}', 7.0, 9.5), 2)
            notes = f'{pname}: {pos} prospect from {school}, projected to {round_n}{"st" if round_n == 1 else "nd"} round.'
            rows.append((
                pid, 'nfl', '2024', round_n, i + 1, overall, tid,
                pname, pos, school, country, height, weight,
                grade, notes, 1 if mock_label else 0))
            pid += 1

    # 2024 NBA Draft mock — 30 picks round 1 (deterministic)
    for i in range(30):
        overall = i + 1
        t_idx = h(f'r3-nba-pick-{overall}', len(nba_teams))
        tid, _tname = nba_teams[t_idx]
        p_idx = h(f'r3-nba-pl-{overall}', len(NBA_DRAFT_POOL))
        pname, pos, school, country, height, weight = NBA_DRAFT_POOL[p_idx]
        grade = round(hf(f'r3-nba-gr-{overall}', 7.0, 9.5), 2)
        notes = f'{pname}: {pos} from {school}, projected lottery pick.'
        rows.append((
            pid, 'nba', '2024', 1, i + 1, overall, tid,
            pname, pos, school, country, height, weight,
            grade, notes, 1))
        pid += 1

    # 2024 NBA Draft mock round 2 — 30 picks
    for i in range(30):
        overall = 30 + i + 1
        t_idx = h(f'r3-nba-pick-2nd-{overall}', len(nba_teams))
        tid, _tname = nba_teams[t_idx]
        p_idx = h(f'r3-nba-pl-2nd-{overall}', len(NBA_DRAFT_POOL))
        pname, pos, school, country, height, weight = NBA_DRAFT_POOL[p_idx]
        grade = round(hf(f'r3-nba-gr-2nd-{overall}', 5.8, 7.2), 2)
        notes = f'{pname}: {pos} second-round mock from {school}.'
        rows.append((
            pid, 'nba', '2024', 2, i + 1, overall, tid,
            pname, pos, school, country, height, weight,
            grade, notes, 1))
        pid += 1

    # 2023 NFL Draft actual (top 32) — non-mock
    nfl_2023_pool = [
        ('Bryce Young', 'QB', 'Alabama', 'USA', "5'10", 204),
        ('C.J. Stroud', 'QB', 'Ohio State', 'USA', "6'3", 214),
        ('Will Anderson Jr.', 'EDGE', 'Alabama', 'USA', "6'4", 253),
        ('Anthony Richardson', 'QB', 'Florida', 'USA', "6'4", 244),
        ('Devon Witherspoon', 'CB', 'Illinois', 'USA', "6'0", 181),
        ('Paris Johnson Jr.', 'OT', 'Ohio State', 'USA', "6'6", 313),
        ('Tyree Wilson', 'EDGE', 'Texas Tech', 'USA', "6'6", 271),
        ('Bijan Robinson', 'RB', 'Texas', 'USA', "5'11", 215),
        ('Jalen Carter', 'DT', 'Georgia', 'USA', "6'3", 314),
        ('Darnell Wright', 'OT', 'Tennessee', 'USA', "6'5", 333),
        ('Peter Skoronski', 'OT', 'Northwestern', 'USA', "6'4", 313),
        ('Jaxon Smith-Njigba', 'WR', 'Ohio State', 'USA', "6'1", 196),
        ('Lukas Van Ness', 'EDGE', 'Iowa', 'USA', "6'5", 272),
        ('Broderick Jones', 'OT', 'Georgia', 'USA', "6'5", 311),
        ('Will McDonald IV', 'EDGE', 'Iowa State', 'USA', "6'4", 239),
        ('Emmanuel Forbes', 'CB', 'Mississippi State', 'USA', "6'0", 166),
        ('Christian Gonzalez', 'CB', 'Oregon', 'USA', "6'2", 197),
        ('Anton Harrison', 'OT', 'Oklahoma', 'USA', "6'5", 315),
        ('Calijah Kancey', 'DT', 'Pittsburgh', 'USA', "6'0", 281),
        ('Jahmyr Gibbs', 'RB', 'Alabama', 'USA', "5'9", 199),
    ]
    for i, (pname, pos, school, country, height, weight) in enumerate(nfl_2023_pool):
        overall = i + 1
        t_idx = h(f'r3-nfl-2023-pick-{overall}', len(nfl_teams))
        tid, _tname = nfl_teams[t_idx]
        grade = round(hf(f'r3-nfl-2023-gr-{overall}', 7.0, 9.5), 2)
        notes = f'{pname}: 2023 NFL Draft pick from {school}.'
        rows.append((
            pid, 'nfl', '2023', 1, overall, overall, tid,
            pname, pos, school, country, height, weight,
            grade, notes, 0))
        pid += 1

    cur.executemany(
        "INSERT INTO draft_picks (id, sport_slug, season, round, pick, "
        "overall_pick, team_id, player_name, position, school, country, "
        "height, weight, scout_grade, notes, is_mock) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 8. Podcasts ──────────────────────────────────────────────────────────────

PODCAST_SEED = [
    ('The Bill Simmons Podcast', 'bill-simmons-podcast', 'Bill Simmons', 'nba',
     'Bill Simmons hosts NBA-centric debates with guests across sports and pop culture.',
     320, 'Inside the playoff bracket and Boston\'s ceiling',
     '2024-04-09', 95),
    ('The Lowe Post', 'the-lowe-post', 'Zach Lowe', 'nba',
     'Zach Lowe\'s tape-driven look at the NBA, with weekly guests.',
     280, 'Pacers, Knicks, and the East playoff field',
     '2024-04-08', 72),
    ('Fantasy Focus Football', 'fantasy-focus-football', 'Field Yates, Matthew Berry guests', 'fantasy',
     'Daily fantasy football show with rankings, sleepers, and injury news.',
     1200, 'Post-draft fantasy reactions and dynasty risers',
     '2024-04-04', 45),
    ('Fantasy Focus Basketball', 'fantasy-focus-basketball', 'Andre Snellings', 'fantasy',
     'Weekly fantasy basketball breakdowns through the regular season and playoffs.',
     220, 'Championship week strategy and punt-builds',
     '2024-04-07', 35),
    ('Baseball Tonight with Buster Olney', 'baseball-tonight', 'Buster Olney', 'mlb',
     'Daily MLB takes from Buster Olney with reporter check-ins.',
     950, 'Early-season hot starts and trade chatter',
     '2024-04-09', 55),
    ('First Take', 'first-take-podcast', 'Stephen A. Smith, Molly Qerim', 'nba',
     'Audio cut of ESPN\'s morning debate show.',
     1500, 'NBA MVP race and NFL Draft hot takes',
     '2024-04-09', 60),
    ('NFL Live', 'nfl-live-podcast', 'Mina Kimes, Dan Orlovsky', 'nfl',
     'ESPN\'s daily NFL show with film breakdowns and Draft talk.',
     760, 'Mock Draft 5.0 reactions',
     '2024-04-09', 50),
    ('In The Crease', 'in-the-crease', 'Greg Wyshynski, Linda Cohn', 'nhl',
     'NHL Stanley Cup chase and trade rumors.',
     180, 'Playoff seeding race and Vezina debate',
     '2024-04-09', 40),
    ('ESPN FC Daily', 'espn-fc-daily', 'Dan Thomas, Shaka Hislop, Steve Nicol', 'soccer',
     'Premier League, Champions League, and global soccer news.',
     430, 'Champions League quarterfinal recap',
     '2024-04-09', 30),
    ('College GameDay Podcast', 'college-gameday-podcast', 'Rece Davis, Pat McAfee', 'ncaaf',
     'College football, with the GameDay crew.',
     150, 'Spring practice notes and recruiting',
     '2024-04-06', 65),
]


def make_podcasts(cur):
    rows = []
    for i, (title, slug, host, sport_slug, description, eps,
            latest_title, latest_date, dur) in enumerate(PODCAST_SEED):
        rows.append((i + 1, title, slug, host, sport_slug, description,
                     eps, latest_title, latest_date, dur))
    cur.executemany(
        "INSERT INTO podcasts (id, title, slug, host, sport_slug, "
        "description, episode_count, latest_episode_title, latest_episode_date, "
        "duration_minutes) VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


# ─── 9. Normalize layout ──────────────────────────────────────────────────────

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
        print('R3 extension already applied — no-op.')
        conn.close()
        return
    create_new_tables(cur)
    n_art = make_articles(cur)
    n_gm = make_games(cur)
    n_st = make_player_stats(cur)
    n_odds = make_betting_odds(cur)
    n_aw = make_awards(cur)
    n_dp = make_draft_picks(cur)
    n_pc = make_podcasts(cur)
    mark_extended(cur)
    normalize(cur)
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f'R3 inserted: articles={n_art}, games={n_gm}, '
          f'player_stats={n_st}, betting_odds={n_odds}, awards={n_aw}, '
          f'draft_picks={n_dp}, podcasts={n_pc}')


if __name__ == '__main__':
    main()
