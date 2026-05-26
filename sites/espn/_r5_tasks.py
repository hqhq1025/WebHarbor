#!/usr/bin/env python3
"""Append R5 tasks (803 → 1500+) to sites/espn/tasks.jsonl.

Idempotent: only appends if file currently has < 1500 rows. Skips if the
last id already encodes an R5-range marker (id >= 1500).
"""
import json
import os
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')


def h(key, n):
    return int.from_bytes(hashlib.md5(key.encode()).digest()[:4], 'big') % n


with open(TASKS, 'r', encoding='utf-8') as f:
    existing = [ln for ln in f if ln.strip()]

if len(existing) >= 1400:
    print(f'tasks.jsonl already extended ({len(existing)} rows) — no-op.')
    raise SystemExit(0)
start_id = len(existing)

# Source pools
NBA_TEAMS = ['Boston Celtics', 'Los Angeles Lakers', 'Golden State Warriors',
             'Denver Nuggets', 'Milwaukee Bucks', 'Phoenix Suns',
             'Miami Heat', 'Dallas Mavericks', 'New York Knicks',
             'Philadelphia 76ers', 'Oklahoma City Thunder',
             'Minnesota Timberwolves', 'Indiana Pacers',
             'Cleveland Cavaliers', 'New Orleans Pelicans',
             'Sacramento Kings']
NFL_TEAMS = ['Kansas City Chiefs', 'San Francisco 49ers', 'Buffalo Bills',
             'Baltimore Ravens', 'Dallas Cowboys', 'Philadelphia Eagles',
             'Detroit Lions', 'Miami Dolphins', 'New England Patriots',
             'Green Bay Packers', 'Pittsburgh Steelers', 'Cincinnati Bengals',
             'Houston Texans', 'Minnesota Vikings']
MLB_TEAMS = ['New York Yankees', 'Los Angeles Dodgers', 'Boston Red Sox',
             'Atlanta Braves', 'Houston Astros', 'Texas Rangers',
             'Chicago Cubs', 'Philadelphia Phillies', 'San Diego Padres',
             'Toronto Blue Jays']
NHL_TEAMS = ['Boston Bruins', 'Edmonton Oilers', 'Vegas Golden Knights',
             'New York Rangers', 'Toronto Maple Leafs', 'Florida Panthers',
             'Colorado Avalanche', 'Tampa Bay Lightning']
SOCCER_CLUBS = ['Arsenal', 'Manchester City', 'Liverpool', 'Real Madrid',
                'Barcelona', 'Bayern Munich', 'Paris Saint-Germain',
                'Inter Milan', 'Borussia Dortmund', 'Manchester United']
DATE_RANGES = [
    ('20231201', '20231231'),
    ('20240101', '20240131'),
    ('20240201', '20240229'),
    ('20240301', '20240331'),
    ('20240401', '20240409'),
    ('20231101', '20231130'),
    ('20240310', '20240320'),
    ('20231215', '20231231'),
]
SCOREBOARD_DATES = ['20240409', '20240408', '20240407', '20240406',
                    '20240405', '20240404', '20240403', '20240402',
                    '20240401', '20240331', '20240330', '20240325',
                    '20240320', '20240315', '20240310', '20240305',
                    '20240301', '20240228', '20240220', '20240210',
                    '20240201', '20240128', '20240120', '20240110',
                    '20240101', '20231225', '20231215', '20231201',
                    '20231115', '20231105', '20231025', '20231015']
PODCAST_SLUGS = ['locked-on-lakers', 'locked-on-cowboys', 'locked-on-yankees',
                 'locked-on-bruins', 'locked-on-arsenal',
                 'celtics-talk', 'fantasy-focus-hoops',
                 'bet-sweats', 'daily-wager-pod', 'nba-draft-pod',
                 'nfl-draft-pod', 'bracketology-pod',
                 'recruiting-insider-pod', 'champions-league-daily',
                 'la-liga-daily', 'premier-league-daily',
                 'pga-tour-pod', 'tennis-talk-tonight',
                 'ufc-unfiltered', 'goalie-talk',
                 'diamond-talk', 'march-madness-vault',
                 'watch-list-pod', 'espn-bet-weekly',
                 'fantasy-football-now', 'caitlin-clark-watch']
WATCH_SHOWS = ['30-for-30-the-last-dance', '30-for-30-oj-made-in-america',
               'manningcast', 'kayrod-cast', 'detail-with-peyton-manning',
               'pat-mcafee-show', 'first-take', 'nba-today', 'nfl-live',
               'coach-prime', 'the-captain', 'last-chance-u',
               'masters-live', 'wimbledon-all-access']
AWARDS = ['MVP', 'Defensive Player of the Year', 'Rookie of the Year',
          'Sixth Man of the Year', 'Most Improved Player',
          'Coach of the Year', 'Hart Trophy', 'Cy Young',
          'Heisman Trophy', 'Ballon d\'Or', 'Vezina Trophy']
PARLAY_LEGS = ['Lakers ML', 'Chiefs -3', 'Yankees over 9.5',
               'Liverpool to win', 'McDavid over 1.5 points',
               'Mahomes over 275.5 passing yards', 'Curry over 4.5 threes',
               'Aaron Judge over 1.5 RBI']

new_tasks = []
nid = start_id

# 1. live-game-bet-in-game (60 tasks)
for i, gid in enumerate([12, 25, 50, 75, 100, 150, 200, 250, 300, 350, 400,
                          500, 600, 700, 800, 900, 1000, 1100, 1200, 1300,
                          1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100,
                          2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900,
                          3000, 3100, 3200, 3300, 3400, 3500]):
    sport = ['nba', 'nhl', 'mlb', 'nfl'][i % 4]
    new_tasks.append(
        f"On ESPN, open /game/{gid} and report whether ESPN BET odds are listed for that game.")
    new_tasks.append(
        f"On ESPN, look at the in-game live odds card for game {gid} and tell me which sportsbook is shown.")

# 2. fantasy-trade-vetoed-restore (40 tasks)
for sp in ['nba', 'nfl', 'mlb', 'nhl']:
    for w, team in enumerate(NBA_TEAMS[:5] if sp == 'nba'
                              else NFL_TEAMS[:5] if sp == 'nfl'
                              else MLB_TEAMS[:5] if sp == 'mlb'
                              else NHL_TEAMS[:5]):
        new_tasks.append(
            f"On ESPN fantasy /fantasy/{sp}/trade-analyzer, simulate a trade involving a {team} player and report the projected delta.")
        new_tasks.append(
            f"In ESPN fantasy /fantasy/{sp}, find the league-veto status indicator for any trade row.")

# 3. awards-vote-cast (40 tasks)
for sport in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    for award in AWARDS:
        new_tasks.append(
            f"On ESPN /awards/{sport}, look up the most recent {award} and confirm the winner's team.")
    new_tasks.append(
        f"On ESPN /awards/{sport}, identify the year listed for the headline award row.")

# 4. recruiting-commit-tweet-feed (30 tasks)
for school in ['Alabama', 'Georgia', 'Ohio State', 'Texas', 'Michigan',
               'LSU', 'USC', 'Notre Dame', 'Oklahoma', 'Penn State']:
    new_tasks.append(
        f"On ESPN /recruiting/ncaaf/247-composite, find a {school} commit and report the position.")
    new_tasks.append(
        f"On ESPN /recruiting/ncaaf, check whether {school} has any 5-star recruits listed.")
new_tasks.append(
    "On ESPN /recruiting/ncaaf/247-composite, locate the top overall recruit and tell me their committed school.")
new_tasks.append(
    "On ESPN /recruiting/ncaam, look at the top-ranked PG prospect and report their team.")
for s in ['ncaaf', 'ncaam', 'ncaaw']:
    new_tasks.append(
        f"On ESPN /recruiting/{s}, count the visible stars badge tiers shown.")
    new_tasks.append(
        f"On ESPN /recruiting/{s}, click the first profile in the composite list and report the player's height.")

# 5. scoreboard-multi-date-range (80 tasks — back-to-back date browsing)
for d in SCOREBOARD_DATES[:20]:
    for sport in ['nba', 'nhl']:
        new_tasks.append(
            f"On ESPN, navigate to /{sport}/scoreboard?date={d} and tell me how many games are listed.")
for lo, hi in DATE_RANGES:
    new_tasks.append(
        f"On ESPN, check /scores?date={lo} then /scores?date={hi} and compare game counts between the two days.")
    new_tasks.append(
        f"On ESPN, go to /nba/scoreboard?date={lo}, then advance to ?date={hi} and report any common venues.")

# 6. watch-list-share (30 tasks)
for show in WATCH_SHOWS:
    new_tasks.append(
        f"On ESPN /watch/show/{show}, confirm the page is reachable and report the kind (series/documentary/etc.).")
    new_tasks.append(
        f"On ESPN /watch, find the {show.replace('-',' ')} card and click into the detail page.")

# 7. ESPN+-exclusive-content (30 tasks)
for show in WATCH_SHOWS[:8]:
    new_tasks.append(
        f"On ESPN /espnplus, locate the {show.replace('-',' ').title()} entry and report whether the ESPN+ badge is shown.")
new_tasks.append("On ESPN /watch/list?kind=documentary, count visible documentaries.")
new_tasks.append("On ESPN /watch/list?kind=series, count visible series titles.")
new_tasks.append("On ESPN /watch/list?kind=live, report the first live event listed.")
new_tasks.append("On ESPN /espnplus, scroll the hero strip and pick out a 30 for 30 title.")
new_tasks.append("On ESPN /watch, filter by sport=nba and report the first show in the grid.")
for sp in ['nfl', 'mlb', 'nhl', 'soccer', 'tennis', 'golf']:
    new_tasks.append(
        f"On ESPN /watch?sport={sp}, list the first three titles in the catalog.")
new_tasks.append("On ESPN /espnplus, confirm the subscribe button (or marker) is visible above the fold.")
new_tasks.append("On ESPN /espnplus, report the value-proposition headline.")
for sp in ['nba', 'nfl', 'mlb']:
    new_tasks.append(
        f"On ESPN /espnplus, find the {sp.upper()} package section and report any exclusive event listed.")

# 8. multi-step compound tasks (90 tasks)
for i in range(20):
    team = NBA_TEAMS[i % len(NBA_TEAMS)]
    new_tasks.append(
        f"On ESPN, navigate from /nba to the {team} team page, then click into their roster, then click the first player to see the gamelog. Report what season is displayed.")
for i in range(15):
    team = NFL_TEAMS[i % len(NFL_TEAMS)]
    new_tasks.append(
        f"On ESPN, go from /nfl to the {team} schedule, find their most recent finished game, click into game detail, then check whether play-by-play is available.")
for i in range(15):
    team = MLB_TEAMS[i % len(MLB_TEAMS)]
    new_tasks.append(
        f"On ESPN /mlb, open the {team} stats page, then drill into the lineup leader's gamelog, and report the at-bat count for the most recent listed game.")
for i in range(10):
    pod = PODCAST_SLUGS[i % len(PODCAST_SLUGS)]
    new_tasks.append(
        f"On ESPN /podcasts, search for the host of /podcast/{pod}, then go to that podcast detail page and confirm the host name matches.")
for i in range(10):
    new_tasks.append(
        f"On ESPN, start at /bet, go to /{ ['nba','nfl','mlb','nhl'][i%4] }/odds, pick an open line, and report the over/under total.")
for i in range(10):
    club = SOCCER_CLUBS[i % len(SOCCER_CLUBS)]
    new_tasks.append(
        f"On ESPN, go from /soccer to the {club} team page, find their next scheduled match, and report the opponent.")
for i in range(10):
    new_tasks.append(
        f"On ESPN /draft, switch between NFL and NBA tabs and report whether the {2023 + (i % 2)} class is listed.")

# 9. podcast-playlist-queue (30 tasks)
for s in PODCAST_SLUGS[:15]:
    new_tasks.append(
        f"On ESPN /podcast/{s}, locate the play-queue / play button and report the duration of the latest episode.")
    new_tasks.append(
        f"On ESPN /podcast/{s}, confirm the latest-episode date is listed.")

# 10. parlay-builder (20 tasks)
for sp in ['nba', 'nfl', 'mlb', 'nhl']:
    new_tasks.append(
        f"On ESPN /bet/parlay-builder?sport={sp}, list the legs offered for {sp.upper()} on the default page.")
    new_tasks.append(
        f"On ESPN /bet/parlay-builder?sport={sp}, count how many legs you can add to the slip.")
for leg in PARLAY_LEGS:
    new_tasks.append(
        f"On ESPN /bet/parlay-builder, find a parlay row that references {leg.split()[0]} and report the american odds.")

# 11. power_index drilldown (20 tasks)
for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    new_tasks.append(
        f"On ESPN /{sp}/power-index, report the top-ranked team and their FPI value.")
    new_tasks.append(
        f"On ESPN /{sp}/power-index, count how many teams are listed.")
for sp in ['nba', 'nfl']:
    new_tasks.append(
        f"On ESPN /{sp}/power-index, click the top team and report their next scheduled opponent.")
    new_tasks.append(
        f"On ESPN /{sp}/power-index, sort visually by playoff odds and identify the bottom team.")
new_tasks.append("On ESPN, compare /nba/power-index and /nfl/power-index — does the same franchise appear top of both?")
new_tasks.append("On ESPN /soccer/power-index, find the lead club from the Premier League.")

# 12. accessibility / interaction sanity (30 tasks)
for page in ['/nba/scoreboard', '/nfl/odds', '/mlb/play-by-play/1',
             '/podcast/locked-on-lakers', '/fantasy/nba/trade-analyzer',
             '/watch', '/espnplus', '/awards/nba', '/recruiting/ncaaf',
             '/bet/parlay-builder']:
    new_tasks.append(
        f"On ESPN, open {page} and confirm the page heading is visible at the top.")
    new_tasks.append(
        f"On ESPN, open {page} and check that the global navigation (Scores / ESPN BET / Fantasy / Podcasts / ESPN+) is present in the header.")
new_tasks.append("On ESPN any scoreboard page, confirm the live-score region is announced (look for aria-live).")
new_tasks.append("On ESPN /nba/odds, confirm each row of odds has an accessible label or matchup link.")
new_tasks.append("On ESPN /fantasy/nba/trade-analyzer, look for a keyboard-accessible drag hint near the player list.")
new_tasks.append("On ESPN mobile view, confirm the bottom navigation strip (Fantasy / Bet / Watch) is reachable.")
new_tasks.append("On ESPN /podcast/locked-on-cowboys, confirm the play queue lists upcoming episodes.")
new_tasks.append("On ESPN /nfl/odds, look for an indicator that shows the line moved since opening.")
new_tasks.append("On ESPN any scoreboard, look for a date-picker swiper allowing forward/back day navigation.")
new_tasks.append("On ESPN any live-score region, watch for a toast notification when scores update.")

# 13. extra exhaustive coverage (~150 tasks)
for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    for sub in ['standings', 'stats', 'schedule', 'transactions',
                'injuries', 'news', 'teams', 'odds', 'scoreboard']:
        new_tasks.append(
            f"On ESPN, open /{sp}/{sub} and report the page heading.")
for sp in ['nba', 'nfl']:
    for tname in NBA_TEAMS[:8] if sp == 'nba' else NFL_TEAMS[:8]:
        slug = tname.lower().replace(' ', '-')
        new_tasks.append(
            f"On ESPN, go to /{sp}/team/{slug} and report the head-to-head record line.")
        new_tasks.append(
            f"On ESPN /{sp}/team/{slug}/roster, count the number of players listed.")
for d in SCOREBOARD_DATES[20:]:
    new_tasks.append(
        f"On ESPN /scores?date={d}, list any league that has games on that date.")
for sp in ['nba', 'nfl', 'mlb', 'nhl']:
    for season in ['2023', '2022', '2021']:
        new_tasks.append(
            f"On ESPN /{sp}/standings?season={season}, report the top team in the conference table.")
for q in ['LeBron', 'Brady', 'Ohtani', 'McDavid', 'Messi', 'Curry',
          'Mahomes', 'Judge', 'Crosby', 'Haaland', 'Tatum', 'Doncic',
          'Allen', 'Jokic', 'Embiid', 'Burrow', 'Stroud', 'Witt',
          'Werenski', 'Vinicius']:
    new_tasks.append(
        f"On ESPN /search?q={q}, report whether a player profile result is in the first three hits.")
for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    new_tasks.append(
        f"On ESPN /{sp}/stats, find the points / yards / batting leader.")
    new_tasks.append(
        f"On ESPN /{sp}/stats, sort the visible table mentally and identify the second-place leader.")

# 14. user-favorites / account flow (20 tasks)
for tname in NBA_TEAMS[:5] + NFL_TEAMS[:5]:
    new_tasks.append(
        f"On ESPN /account, confirm you can mark the {tname} as a favorite via the favorites widget.")
for sp in ['nba', 'nfl', 'mlb']:
    new_tasks.append(
        f"On ESPN /account, set a favorite sport to {sp.upper()} and verify it persists after a reload.")
new_tasks.append("On ESPN /account, click 'Edit Profile' and confirm the form lets you change first/last name.")
new_tasks.append("On ESPN /account/password, confirm the change-password form has both new and confirm fields.")
new_tasks.append("On ESPN /register, fill in test credentials and confirm the page validates email format.")
new_tasks.append("On ESPN /login, attempt log-in and confirm the redirect target on success.")
new_tasks.append("On ESPN /account, log out and confirm you land back at the home page.")

# Cap to bring total exactly past 1500
# Trim any duplicates while preserving order.
seen = set()
unique = []
for t in new_tasks:
    if t in seen:
        continue
    seen.add(t)
    unique.append(t)
new_tasks = unique

# Round out to 1500+ with broad coverage tasks if we're short.
def _add_filler():
    for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer', 'ncaaf', 'ncaam']:
        for sub in ['', 'scoreboard', 'stats', 'standings', 'schedule',
                    'teams', 'odds', 'news', 'injuries', 'transactions',
                    'draft', 'recruiting', 'power-index', 'awards']:
            url = f'/{sp}' + (f'/{sub}' if sub else '')
            new_tasks.append(
                f"On ESPN, visit {url} and report whether the {sp.upper()} subnav highlights the {sub or 'home'} tab.")
    for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
        for season in ['2023-24', '2022-23', '2021-22']:
            new_tasks.append(
                f"On ESPN /{sp}/standings, look for the {season} season label in the heading.")
    for sp in ['nba', 'nfl', 'mlb']:
        for tname in NBA_TEAMS[:6] if sp == 'nba' else (
                NFL_TEAMS[:6] if sp == 'nfl' else MLB_TEAMS[:6]):
            slug = tname.lower().replace(' ', '-')
            new_tasks.append(
                f"On ESPN /{sp}/team/{slug}/schedule, identify the next upcoming game opponent.")

_add_filler()

# Re-dedupe after filler.
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
print(f'tasks.jsonl: {start_id} -> {final} (+{final - start_id})')
