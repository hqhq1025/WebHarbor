#!/usr/bin/env python3
"""Append R6 tasks (1543 → 2500+) to sites/espn/tasks.jsonl.

R6 task focuses:
  * Long cross-page chains (home → sport → team → roster → player →
    game → boxscore → play-by-play → article → podcast).
  * Player-to-season-stats-to-all-time-rank traces.
  * Breadcrumb + "Related" section confirmations on detail pages.
  * Edge-case banners: postponed game, injured-star banner,
    fantasy-roster locked, ESPN+ paywall, regional bet block,
    future-protected draft pick.

Idempotent: skips if file already has ≥ 2400 rows.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')


with open(TASKS, 'r', encoding='utf-8') as f:
    existing = [ln for ln in f if ln.strip()]

if len(existing) >= 2400:
    print(f'tasks.jsonl already extended ({len(existing)} rows) — no-op.')
    raise SystemExit(0)
start_id = len(existing)

# ─── Source pools ─────────────────────────────────────────────────────────────

NBA_TEAMS = ['Boston Celtics', 'Los Angeles Lakers', 'Golden State Warriors',
             'Denver Nuggets', 'Milwaukee Bucks', 'Phoenix Suns',
             'Miami Heat', 'Dallas Mavericks', 'New York Knicks',
             'Philadelphia 76ers', 'Oklahoma City Thunder',
             'Minnesota Timberwolves', 'Indiana Pacers',
             'Cleveland Cavaliers', 'New Orleans Pelicans',
             'Sacramento Kings', 'Memphis Grizzlies', 'Atlanta Hawks',
             'Orlando Magic', 'Houston Rockets']
NFL_TEAMS = ['Kansas City Chiefs', 'San Francisco 49ers', 'Buffalo Bills',
             'Baltimore Ravens', 'Dallas Cowboys', 'Philadelphia Eagles',
             'Detroit Lions', 'Miami Dolphins', 'New England Patriots',
             'Green Bay Packers', 'Pittsburgh Steelers', 'Cincinnati Bengals',
             'Houston Texans', 'Minnesota Vikings', 'Los Angeles Rams',
             'New York Jets', 'Jacksonville Jaguars', 'Cleveland Browns']
MLB_TEAMS = ['New York Yankees', 'Los Angeles Dodgers', 'Boston Red Sox',
             'Atlanta Braves', 'Houston Astros', 'Texas Rangers',
             'Chicago Cubs', 'Philadelphia Phillies', 'San Diego Padres',
             'Toronto Blue Jays', 'Baltimore Orioles', 'Seattle Mariners',
             'New York Mets', 'Milwaukee Brewers']
NHL_TEAMS = ['Boston Bruins', 'Edmonton Oilers', 'Vegas Golden Knights',
             'New York Rangers', 'Toronto Maple Leafs', 'Florida Panthers',
             'Colorado Avalanche', 'Tampa Bay Lightning', 'Dallas Stars',
             'Carolina Hurricanes']
SOCCER_CLUBS = ['Arsenal', 'Manchester City', 'Liverpool', 'Real Madrid',
                'Barcelona', 'Bayern Munich', 'Paris Saint-Germain',
                'Inter Milan', 'Borussia Dortmund', 'Manchester United']
NBA_STARS = ['Jayson Tatum', 'LeBron James', 'Stephen Curry',
             'Nikola Jokic', 'Joel Embiid', 'Luka Doncic',
             'Giannis Antetokounmpo', 'Anthony Edwards',
             'Shai Gilgeous-Alexander', 'Damian Lillard',
             'Jimmy Butler', 'Kawhi Leonard', 'Devin Booker',
             'Donovan Mitchell']
NFL_STARS = ['Patrick Mahomes', 'Josh Allen', 'Joe Burrow',
             'Lamar Jackson', 'Christian McCaffrey', 'Tyreek Hill',
             'Justin Jefferson', 'Travis Kelce', 'Aaron Donald',
             'Micah Parsons']
MLB_STARS = ['Aaron Judge', 'Shohei Ohtani', 'Mookie Betts',
             'Ronald Acuna Jr.', 'Juan Soto', 'Mike Trout',
             'Freddie Freeman', 'Bobby Witt Jr.', 'Gunnar Henderson']
NHL_STARS = ['Connor McDavid', 'Auston Matthews', 'Nathan MacKinnon',
             'David Pastrnak', 'Leon Draisaitl', 'Sidney Crosby',
             'Cale Makar', 'Nikita Kucherov']
SOCCER_STARS = ['Erling Haaland', 'Mohamed Salah', 'Vinicius Junior',
                'Bukayo Saka', 'Jude Bellingham', 'Kylian Mbappe',
                'Harry Kane', 'Rodri']
ALL_TIME_RANK_QUERIES = [
    ('NBA', 'career points'), ('NBA', 'career assists'),
    ('NBA', 'career rebounds'), ('NBA', 'career 3-pointers made'),
    ('NFL', 'career passing yards'), ('NFL', 'career touchdowns'),
    ('NFL', 'career receiving yards'), ('MLB', 'career home runs'),
    ('MLB', 'career RBI'), ('MLB', 'career batting average'),
    ('NHL', 'career goals'), ('NHL', 'career assists'),
    ('NHL', 'career points'), ('Soccer', 'career goals'),
    ('Soccer', 'career assists'),
]
ARTICLE_TAG_TOPICS = ['lockerroom', 'trade', 'rankings', 'injury',
                      'coaching', 'fpi', 'fantasy', 'bet',
                      'draft', 'preview', 'recruiting',
                      'roster', 'film', 'history', 'gameday']

new_tasks = []

# ─── 1. Cross-page chain: home → sport → team → roster → player →
#     game → boxscore → play-by-play → article → podcast (160) ─────────────────

for i, team in enumerate(NBA_TEAMS[:15]):
    slug = team.lower().replace(' ', '-')
    star = NBA_STARS[i % len(NBA_STARS)]
    new_tasks.append(
        f"On ESPN, start at the home page, navigate to /nba, then to the "
        f"{team} team page, open the roster, click {star}, then open his "
        f"gamelog and report the points he scored in the most recent "
        f"listed game.")
    new_tasks.append(
        f"On ESPN, from /nba/team/{slug}, click into the schedule, find "
        f"the most recent finished game, open the box score, then open "
        f"the play-by-play and report the final score.")
    new_tasks.append(
        f"On ESPN /nba, follow a path home→/nba→/nba/team/{slug}→roster→"
        f"first player→profile. Report the player's position and jersey.")
    new_tasks.append(
        f"On ESPN, from the {team} team page, click into an article "
        f"mentioning the team, then navigate to a related podcast (NBA-"
        f"tagged) from /podcasts and report the latest episode title.")

for i, team in enumerate(NFL_TEAMS[:12]):
    slug = team.lower().replace(' ', '-')
    star = NFL_STARS[i % len(NFL_STARS)]
    new_tasks.append(
        f"On ESPN, start at /nfl, open /nfl/team/{slug}, open the roster, "
        f"click {star}, then open his gamelog and report the passing/"
        f"rushing/receiving yards from the most recent listed game.")
    new_tasks.append(
        f"On ESPN /nfl/team/{slug}/schedule, identify the most recent "
        f"completed game, open the boxscore, then click into the play-"
        f"by-play and report the period where scoring is densest.")

for i, team in enumerate(MLB_TEAMS[:10]):
    slug = team.lower().replace(' ', '-')
    star = MLB_STARS[i % len(MLB_STARS)]
    new_tasks.append(
        f"On ESPN /mlb/team/{slug}, navigate to the roster, click {star}, "
        f"open his gamelog and report the at-bat count in the latest "
        f"listed game; then go to /mlb/stats and find his RBI total.")
    new_tasks.append(
        f"On ESPN /mlb/team/{slug}/schedule, find the latest finished "
        f"game, open box score, click into play-by-play, and report the "
        f"home-run total mentioned in the recap.")

for i, team in enumerate(NHL_TEAMS):
    slug = team.lower().replace(' ', '-')
    star = NHL_STARS[i % len(NHL_STARS)]
    new_tasks.append(
        f"On ESPN /nhl/team/{slug}, open the roster, click {star}, then "
        f"open his gamelog and report his goal total for the season.")
    new_tasks.append(
        f"On ESPN, from /nhl, click into the {team} team page, open the "
        f"latest finished game in their schedule, open play-by-play and "
        f"identify the period with the most penalties.")

for club in SOCCER_CLUBS:
    slug = club.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /soccer, click into the {club} team page, open the "
        f"squad, click the captain, then open his profile and report "
        f"his preferred foot or position.")
    new_tasks.append(
        f"On ESPN /soccer/team/{slug}/schedule, find the next scheduled "
        f"fixture, click into the match preview, then click into a "
        f"related article and report its headline.")

# ─── 2. "track player from game-result back to season-stats to
#     all-time-rank" chains (120) ────────────────────────────────────────────

for league, metric in ALL_TIME_RANK_QUERIES:
    sport_path = {'NBA': 'nba', 'NFL': 'nfl', 'MLB': 'mlb',
                  'NHL': 'nhl', 'Soccer': 'soccer'}[league]
    star_pool = {'NBA': NBA_STARS, 'NFL': NFL_STARS, 'MLB': MLB_STARS,
                 'NHL': NHL_STARS, 'Soccer': SOCCER_STARS}[league]
    for star in star_pool[:6]:
        slug = star.lower().replace(' ', '-').replace('.', '')
        new_tasks.append(
            f"On ESPN /player/{sport_path}/{slug}, start from this season's"
            f" stat line, click into the season-stats card, then navigate "
            f"to /{sport_path}/all-time and report where this player "
            f"sits in {metric}.")
        new_tasks.append(
            f"On ESPN, track {star}: open a recent game from his gamelog,"
            f" return to season stats, then click into the {league} all-"
            f"time leaderboards for {metric} and report his rank.")

# ─── 3. Breadcrumb confirmations on detail pages (130) ───────────────────────

DETAIL_PAGES_TEMPLATE = [
    ('article', '/article/celtics-eye-best-regular-season-in-years'),
    ('player', '/player/nba/jayson-tatum'),
    ('player-gamelog', '/player/nba/jayson-tatum/gamelog'),
    ('team', '/team/nba/boston-celtics'),
    ('team-roster', '/team/nba/boston-celtics/roster'),
    ('team-schedule', '/team/nba/boston-celtics/schedule'),
    ('team-stats', '/team/nba/boston-celtics/stats'),
    ('team-injuries', '/team/nba/boston-celtics/injuries'),
    ('team-depth', '/team/nba/boston-celtics/depth-chart'),
    ('game', '/game/100'),
    ('pbp', '/nba/play-by-play/100'),
    ('podcast', '/podcast/locked-on-lakers'),
    ('award', '/awards/nba'),
    ('draft', '/draft/nba'),
    ('recruit', '/recruiting/ncaaf/247-composite'),
]
for kind, path in DETAIL_PAGES_TEMPLATE:
    new_tasks.append(
        f"On ESPN {path}, confirm the breadcrumb trail at the top of the "
        f"page reflects the navigation hierarchy (Home > Sport > ...).")
    new_tasks.append(
        f"On ESPN {path}, click the breadcrumb's parent link and confirm "
        f"you land on the parent listing page.")
# Same drill across teams
for tname in (NBA_TEAMS[:6] + NFL_TEAMS[:6] + MLB_TEAMS[:6]):
    sp = ('nba' if tname in NBA_TEAMS else
          'nfl' if tname in NFL_TEAMS else 'mlb')
    slug = tname.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /team/{sp}/{slug}, confirm the breadcrumb shows the "
        f"path Home > {sp.upper()} > {tname}.")
    new_tasks.append(
        f"On ESPN /team/{sp}/{slug}/roster, confirm the breadcrumb still"
        f" includes the {tname} team link.")
for p in SOCCER_STARS[:6]:
    slug = p.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /player/soccer/{slug}, confirm the breadcrumb includes "
        f"a link back to /soccer and his club page.")

# ─── 4. "Games this team played" / "Players in same position" /
#     "Articles mentioning this game" / "Related podcasts" (150) ────────────

for tname in (NBA_TEAMS[:8] + NFL_TEAMS[:6] + MLB_TEAMS[:6] +
              NHL_TEAMS[:5]):
    sp = ('nba' if tname in NBA_TEAMS else
          'nfl' if tname in NFL_TEAMS else
          'mlb' if tname in MLB_TEAMS else 'nhl')
    slug = tname.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /team/{sp}/{slug}, scroll to the 'Games this team "
        f"played' section and report the most recent listed opponent.")
    new_tasks.append(
        f"On ESPN /team/{sp}/{slug}, find the 'Games this team played' "
        f"strip and count how many games are listed in the most recent "
        f"month.")
for star in (NBA_STARS[:8] + NFL_STARS[:6] + MLB_STARS[:5]):
    sp = ('nba' if star in NBA_STARS else
          'nfl' if star in NFL_STARS else 'mlb')
    slug = star.lower().replace(' ', '-').replace('.', '')
    new_tasks.append(
        f"On ESPN /player/{sp}/{slug}, scroll to the 'Players in same "
        f"position' related card and report the first peer player listed.")
    new_tasks.append(
        f"On ESPN /player/{sp}/{slug}, locate the 'Players in same "
        f"position' module and count how many peers are linked.")
for gid in range(50, 230, 6):
    new_tasks.append(
        f"On ESPN /game/{gid}, scroll to the 'Articles mentioning this "
        f"game' section and report the first article headline listed.")
    new_tasks.append(
        f"On ESPN /game/{gid}, find the 'Related podcasts' module under "
        f"the box score and report the first podcast name.")

# ─── 5. Edge-case banners (90 — split across 6 banners) ─────────────────────

# 5a. game-postponed banner
for gid in [3550, 3590, 3650, 3700, 3760, 3820, 3880, 3940, 4000,
            4060, 4120, 4180, 4240, 4300, 4360]:
    new_tasks.append(
        f"On ESPN /game/{gid}, look for the 'GAME POSTPONED' banner above "
        f"the box score and report whether a make-up date is listed.")
    new_tasks.append(
        f"On ESPN /game/{gid}, if the postponed banner is shown, click "
        f"any 'reschedule' or 'rescheduled' link and report where it "
        f"lands.")
# 5b. player-injured-status banner on player profile
for star in (NBA_STARS[:5] + NFL_STARS[:5] + MLB_STARS[:3]):
    sp = ('nba' if star in NBA_STARS else
          'nfl' if star in NFL_STARS else 'mlb')
    slug = star.lower().replace(' ', '-').replace('.', '')
    new_tasks.append(
        f"On ESPN /player/{sp}/{slug}, look for the 'INJURED — STATUS' "
        f"banner near the player photo and report the listed status word "
        f"(Out / Day-to-Day / Questionable / GTD).")
    new_tasks.append(
        f"On ESPN /player/{sp}/{slug}, if an injury banner is shown, "
        f"click any 'injury report' link and report which team injury "
        f"page it navigates to.")
# 5c. fantasy-roster-locked-game-started
for sp in ['nba', 'nfl', 'mlb', 'nhl']:
    new_tasks.append(
        f"On ESPN /fantasy/{sp}, locate any 'Lineup locked — game in "
        f"progress' banner and report which roster slot is locked.")
    new_tasks.append(
        f"On ESPN /fantasy/{sp}/waiver-wire, look for the 'Locked — game "
        f"started' marker on any roster row and report the player team.")
# 5d. ESPN+ required content paywall
for show in ['30-for-30-the-last-dance', 'manningcast', 'last-chance-u',
             'detail-with-peyton-manning', 'masters-live',
             'wimbledon-all-access', 'pat-mcafee-show']:
    new_tasks.append(
        f"On ESPN /watch/{show}, look for the 'ESPN+ REQUIRED' paywall "
        f"banner and report whether a subscribe CTA is visible.")
new_tasks.append(
    "On ESPN /espnplus, confirm the 'ESPN+ Required' badge appears on "
    "at least three premium tiles in the hero grid.")
# 5e. betting-not-available-region
for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    new_tasks.append(
        f"On ESPN /{sp}/odds, look for the 'Not available in your "
        f"region' banner and report any 'where ESPN BET is live' help "
        f"link target.")
new_tasks.append(
    "On ESPN /bet, look for the geo-region banner near the page top and "
    "report which states/regions are listed as eligible.")
new_tasks.append(
    "On ESPN /bet/parlay-builder, if the region-block banner shows, "
    "confirm the parlay slip is disabled.")
# 5f. draft-pick-future-protected
for yr in [2025, 2026, 2027]:
    new_tasks.append(
        f"On ESPN /draft/nba, look for the {yr} round-1 picks and "
        f"identify which picks carry a 'protected' label.")
    new_tasks.append(
        f"On ESPN /draft/nfl, scan the {yr} mock draft and report the "
        f"first pick listed as 'future-protected' or 'top-N protected'.")

# ─── 6. Compound multi-step + breadcrumb chains (100) ───────────────────────

for i, team in enumerate(NBA_TEAMS[:10]):
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN, navigate Home → /nba → /nba/scoreboard → /game/{50+i} "
        f"→ /nba/play-by-play/{50+i}, then read the breadcrumb trail at "
        f"the top and report the final crumb.")
    new_tasks.append(
        f"On ESPN, walk /nba → /nba/team/{slug} → roster → first player. "
        f"After landing on the player page, click the breadcrumb's "
        f"'roster' crumb and confirm you return to /team/nba/{slug}/"
        f"roster.")
for i, team in enumerate(NFL_TEAMS[:8]):
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN, from /nfl find the {team}, open the schedule, click "
        f"the most recent game, then open the play-by-play. Report which "
        f"team the home/away last drive scored for.")
for i, team in enumerate(MLB_TEAMS[:8]):
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /mlb, click into {team}, open the team stats, then "
        f"navigate to the team's most recent recap article. Report the "
        f"article's published date.")
for star in (NBA_STARS[:6] + NHL_STARS[:6]):
    sp = 'nba' if star in NBA_STARS else 'nhl'
    slug = star.lower().replace(' ', '-').replace('.', '')
    new_tasks.append(
        f"On ESPN /player/{sp}/{slug}, open the gamelog, click into the "
        f"most recent game, then click into the play-by-play for that "
        f"game and confirm you can locate the player's scoring play.")
for club in SOCCER_CLUBS[:8]:
    slug = club.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /soccer/team/{slug}, find a related podcast (Soccer-"
        f"tagged) from the 'Related podcasts' module, click it, then "
        f"report the host name.")
for tname in NBA_TEAMS[:8]:
    slug = tname.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /team/nba/{slug}, open an article in 'Articles "
        f"mentioning this team' and then click any inline player link to "
        f"reach a player profile. Report the player's position.")

# ─── 7. Betting / parlay deep workflows (80) ────────────────────────────────

R6_PARLAYS = ['chiefs-bills-bears-survive',
              'lakers-warriors-celtics-overs',
              'yankees-dodgers-braves-runline',
              'mcdavid-matthews-anytime',
              'mahomes-allen-burrow-passing-tds',
              'curry-tatum-doncic-threes',
              'saturday-college-favorites',
              'manchester-derby-overs',
              'judge-ohtani-acuna-hr-day',
              'panthers-rangers-stars-ml',
              'sundays-best-overs-nfl',
              'three-team-chalk-cbb',
              'lakers-celtics-bucks-spreads',
              'ucl-knockout-double',
              'all-sport-saturday-cross',
              'thursday-night-nfl',
              'cup-final-future-double',
              'nba-mvp-doncic-anytime-3',
              'mlb-ace-strikeouts-trio',
              'soccer-anytime-scorer-treble',
              'cfb-conference-favorites',
              'nfl-rookie-passing-multi',
              'curry-mvp-and-warriors-overs',
              'hockey-rookie-multi',
              'three-team-cbb-overs',
              'nba-rookie-roy-prop',
              'nfl-prime-time-overs',
              'mlb-postseason-futures-double',
              'soccer-clean-sheet-trio',
              'nba-finals-mvp-double']
for s in R6_PARLAYS:
    new_tasks.append(
        f"On ESPN /bet/parlay-builder, locate the saved parlay {s.replace('-',' ')} "
        f"and report the american odds.")
    new_tasks.append(
        f"On ESPN /bet/parlay-builder, click the {s.replace('-',' ')} "
        f"slip; report the number of legs.")
for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    for book in ['ESPN BET', 'DraftKings', 'FanDuel', 'BetMGM']:
        new_tasks.append(
            f"On ESPN /{sp}/odds, filter visible rows for {book} as the "
            f"sportsbook and report the first matchup's total.")

# ─── 8. Article / podcast cross-link (80) ───────────────────────────────────

for topic in ARTICLE_TAG_TOPICS:
    for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
        new_tasks.append(
            f"On ESPN /{sp}/news, find an article tagged '{topic}' and "
            f"click any inline /podcast/ link found inside the body. "
            f"Report the podcast host name.")
for tname in (NBA_TEAMS[:4] + NFL_TEAMS[:3] + MLB_TEAMS[:3]):
    sp = ('nba' if tname in NBA_TEAMS else
          'nfl' if tname in NFL_TEAMS else 'mlb')
    slug = tname.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /team/{sp}/{slug}, find the 'Related podcasts' "
        f"section. Open the top podcast and confirm a {tname}-related "
        f"episode is featured.")
    new_tasks.append(
        f"On ESPN /team/{sp}/{slug}, browse the 'Articles mentioning "
        f"this team' module and report how many headlines mention a "
        f"trade or rumor.")

# ─── 9. Power index + all-time crossover (60) ───────────────────────────────

for sp, league in [('nba', 'NBA'), ('nfl', 'NFL'), ('mlb', 'MLB'),
                   ('nhl', 'NHL'), ('soccer', 'Soccer')]:
    for metric in [m for ll, m in ALL_TIME_RANK_QUERIES if ll == league][:3]:
        new_tasks.append(
            f"On ESPN /{sp}/power-index, identify the top team, then "
            f"navigate to /{sp}/all-time and compare against the {metric} "
            f"leader. Report whether the names match.")
        new_tasks.append(
            f"On ESPN /{sp}/all-time?metric={metric.replace(' ','-')}, "
            f"report the top three names listed.")
for sp in ['nba', 'nfl', 'mlb', 'nhl']:
    new_tasks.append(
        f"On ESPN /{sp}/all-time, scroll through the leaderboard and "
        f"report any active player appearing in the top 10.")
    new_tasks.append(
        f"On ESPN /{sp}/all-time, click into the top entry's player "
        f"profile and report the active/retired status.")

# ─── 10. Filler: cover every newly added R6 game / article / parlay /
#     podcast (80) ────────────────────────────────────────────────────────────

for gid in range(4000, 4200, 6):
    new_tasks.append(
        f"On ESPN /game/{gid}, locate the recap text and confirm the "
        f"final score is mentioned.")
for slug in ['r6-nba-boston-celtics-power-rankings-week-00',
             'r6-nfl-kansas-city-chiefs-fpi-deep-dive-00',
             'r6-mlb-new-york-yankees-trade-deadline-buzz-00',
             'r6-nhl-boston-bruins-coach-roundtable-00',
             'r6-soccer-arsenal-betting-line-watch-00',
             'r6-ncaaf-alabama-recruit-commit-recap-00',
             'r6-ncaam-duke-power-rankings-week-00']:
    new_tasks.append(
        f"On ESPN /article/{slug}, confirm the article body loads and "
        f"the tag chips appear at the bottom.")
    new_tasks.append(
        f"On ESPN /article/{slug}, click any tag chip and report the "
        f"landing page heading.")
for slug in ['beyond-the-boxscore', 'pelton-hoop-collective',
             'soccer-fix', 'total-yards', 'cbb-today',
             'inside-the-crease', 'schefty-pod',
             'cfb-insider-show', 'tennis-beat']:
    new_tasks.append(
        f"On ESPN /podcast/{slug}, confirm the host and latest-episode "
        f"date are listed near the play button.")
    new_tasks.append(
        f"On ESPN /podcasts/search?q={slug.split('-')[0]}, confirm at "
        f"least one matching show is returned.")

# Trim duplicates while preserving order.
seen = set()
unique = []
for t in new_tasks:
    if t in seen:
        continue
    seen.add(t)
    unique.append(t)
new_tasks = unique

# Append
with open(TASKS, 'a', encoding='utf-8') as f:
    for i, ques in enumerate(new_tasks):
        rec = {
            'web_name': 'ESPN',
            'id': f'ESPN--{start_id + i}',
            'ques': ques,
            'web': 'http://localhost:40014/',
            'upstream_url': 'https://www.espn.com/'
        }
        f.write(json.dumps(rec) + '\n')

with open(TASKS, 'r', encoding='utf-8') as f:
    final = sum(1 for ln in f if ln.strip())
print(f'R6 tasks appended: +{len(new_tasks)} (total now {final})')
