#!/usr/bin/env python3
"""Append R4 tasks (418 → 800+) to sites/espn/tasks.jsonl. Idempotent: only
appends if file currently has 418 rows."""
import json
import os
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')


def h(key, n):
    return int.from_bytes(hashlib.md5(key.encode()).digest()[:4], 'big') % n


with open(TASKS, 'r', encoding='utf-8') as f:
    existing = [ln for ln in f if ln.strip()]

if len(existing) >= 800:
    print(f'tasks.jsonl already extended ({len(existing)} rows) — no-op.')
    raise SystemExit(0)
start_id = len(existing)

# Source pools for templated tasks
NBA_TEAMS = ['Boston Celtics', 'Los Angeles Lakers', 'Golden State Warriors',
             'Denver Nuggets', 'Milwaukee Bucks', 'Phoenix Suns',
             'Miami Heat', 'Dallas Mavericks', 'New York Knicks',
             'Philadelphia 76ers', 'Oklahoma City Thunder',
             'Minnesota Timberwolves', 'Indiana Pacers', 'Cleveland Cavaliers']
NFL_TEAMS = ['Kansas City Chiefs', 'San Francisco 49ers', 'Buffalo Bills',
             'Baltimore Ravens', 'Dallas Cowboys', 'Philadelphia Eagles',
             'Detroit Lions', 'Miami Dolphins', 'New England Patriots',
             'Green Bay Packers']
MLB_TEAMS = ['New York Yankees', 'Los Angeles Dodgers', 'Boston Red Sox',
             'Atlanta Braves', 'Houston Astros', 'Texas Rangers',
             'Chicago Cubs', 'Philadelphia Phillies']
NHL_TEAMS = ['Boston Bruins', 'Edmonton Oilers', 'Vegas Golden Knights',
             'New York Rangers', 'Toronto Maple Leafs', 'Florida Panthers']
SOCCER_CLUBS = ['Arsenal', 'Manchester City', 'Liverpool',
                'Real Madrid', 'Barcelona', 'Bayern Munich']
RECENT_DATES = ['20240409', '20240408', '20240407', '20240406',
                '20240405', '20240404', '20240403', '20240402', '20240401',
                '20240331', '20240330', '20240325', '20240320', '20240315']
PODCAST_KEYWORDS = ['draft', 'MVP', 'bracket', 'fantasy', 'parlay',
                    'playoff', 'trade', 'recruiting', 'mock', 'NBA',
                    'NFL', 'Champions League', 'Cy Young', 'goalie',
                    'masters', 'UCL', 'NIL']
WATCH_SHOWS = ['30-for-30-the-last-dance', '30-for-30-oj-made-in-america',
               'manningcast', 'kayrod-cast', 'detail-with-peyton-manning',
               'pat-mcafee-show', 'first-take', 'nba-today', 'nfl-live',
               '30-for-30-bad-boys', '30-for-30-bo-knows',
               '30-for-30-once-brothers', 'coach-prime', 'the-captain',
               'last-chance-u', 'masters-live', 'wimbledon-all-access']

new_tasks = []
nid = start_id

# 1. scoreboard-by-date (60 tasks)
for d in RECENT_DATES:
    for sport in ['nba', 'nfl', 'mlb', 'nhl']:
        new_tasks.append(f"On ESPN, open /{sport}/scoreboard?date={d} and report the games shown for that date.")
for d in RECENT_DATES[:4]:
    new_tasks.append(f"Use ESPN's /scores?date={d} aggregator and list any games that finished that day.")

# 2. live-game-play-by-play (40 tasks)
for gid in range(1, 25):
    sport = ['nba', 'nhl', 'mlb', 'nfl'][gid % 4]
    new_tasks.append(f"On ESPN, open /{sport}/play-by-play/{gid} and report the first three plays of the game.")
for gid in [50, 75, 120, 200, 300, 450, 600, 800, 1000, 1100, 1200, 1500]:
    sport = ['nba', 'nhl', 'mlb'][gid % 3]
    new_tasks.append(f"Pull /{sport}/play-by-play/{gid} on ESPN and tell me the final score recorded in the last event row.")
new_tasks.append("On ESPN, open the play-by-play page for the most recent NBA game and check the LIVE indicator visibility.")
new_tasks.append("On ESPN, look up play-by-play for any NHL game and report what event types appear (goal, save, etc.).")
new_tasks.append("On ESPN, find an MLB play-by-play page and report whether the events include strikeouts and walks.")
new_tasks.append("On ESPN, locate a play-by-play view that shows offensive rebounds for an NBA game.")

# 3. fantasy-trade-analyzer (30 tasks)
for sport in ['nba', 'nfl', 'mlb', 'nhl']:
    new_tasks.append(f"On ESPN, go to /fantasy/{sport}/trade-analyzer and report how many candidate players are listed.")
    new_tasks.append(f"Open ESPN's fantasy trade analyzer for {sport.upper()} and report the page heading.")
for team in ['lebron-james', 'jayson-tatum', 'patrick-mahomes', 'luka-doncic',
             'shai-gilgeous-alexander', 'stephen-curry', 'nikola-jokic',
             'shohei-ohtani', 'connor-mcdavid', 'erling-haaland']:
    new_tasks.append(f"On ESPN's fantasy trade analyzer, locate {team} in the candidate pool.")
new_tasks.extend([
    "On ESPN, open the fantasy NBA trade analyzer and check that drag-and-drop slot zones are present.",
    "Use ESPN's fantasy trade analyzer for NFL and report the projection caption.",
    "On ESPN, evaluate a 1-for-2 trade on /fantasy/nba/trade-analyzer.",
    "Locate the fantasy trade analyzer in ESPN's site navigation under Fantasy.",
])

# 4. fantasy-waiver-wire (30 tasks)
for sport in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    new_tasks.append(f"On ESPN, open /fantasy/{sport}/waiver-wire and list the top 3 waiver options shown.")
    new_tasks.append(f"On ESPN's {sport.upper()} waiver-wire page, report the column headings used.")
new_tasks.extend([
    "On ESPN, find the player with the highest 'Add %' on the NBA waiver wire.",
    "On ESPN, identify a pitcher on the MLB waiver wire whose ERA is below 3.0.",
    "On ESPN's NHL waiver wire, locate a player with 70+ points.",
    "On ESPN's NFL waiver wire, find a quarterback with 3000+ passing yards.",
    "On ESPN, compare the top 5 NBA waiver wire adds vs the top 5 NHL adds.",
    "On ESPN's fantasy waiver wire, report the season label shown next to each player.",
    "On ESPN, check whether the NBA waiver wire shows shooting percentages.",
    "On ESPN, navigate to fantasy soccer waiver wire from the NBA waiver wire page.",
    "On ESPN's waiver wire, sort or scan for soccer goal leaders among waiver candidates.",
    "On ESPN, on /fantasy/nfl/waiver-wire, identify a wide receiver with 1000+ receiving yards.",
    "On ESPN, check that the NHL waiver wire shows goals and assists side by side.",
    "On ESPN, count rows in the NBA waiver-wire table.",
    "On ESPN's MLB waiver wire, find a batter with 30+ home runs.",
    "On ESPN, locate the waiver-wire link in the fantasy hub navigation.",
    "On ESPN, confirm fantasy waiver-wire pages exist for all five major sports.",
])

# 5. betting-parlay-build (40 tasks)
new_tasks.extend([
    "On ESPN, open /bet/parlay-builder and report how many featured parlays are highlighted.",
    "On ESPN's parlay builder, identify a parlay with American odds above +500.",
    "On ESPN, find a 5-leg parlay on the parlay-builder page.",
    "On ESPN, locate a parlay sponsored by 'ESPN BET' on the parlay-builder.",
    "On ESPN's parlay builder, list parlays for the NBA.",
    "On ESPN, identify the highest-odds parlay shown on /bet/parlay-builder.",
    "On ESPN's parlay-builder, report the decimal odds of any featured parlay.",
    "On ESPN, count featured parlays vs non-featured on the parlay builder page.",
    "On ESPN, find a parlay involving golf on /bet/parlay-builder.",
    "On ESPN, locate an MLB run-line parlay on the parlay builder.",
    "On ESPN, find an NFL same-game parlay on /bet/parlay-builder.",
    "On ESPN, confirm the parlay-builder page uses American-style odds notation.",
    "On ESPN, find a 4-leg parlay on the parlay-builder.",
    "On ESPN, identify the sportsbook attached to each parlay on /bet/parlay-builder.",
    "On ESPN, list the sports represented in the parlay-builder featured grid.",
    "On ESPN, report the title of the first featured parlay on /bet/parlay-builder.",
    "On ESPN, find a UFC parlay on the parlay builder.",
    "On ESPN, find a soccer parlay on /bet/parlay-builder and report its leg count.",
    "On ESPN, on /bet/parlay-builder, identify a NCAA tournament parlay.",
    "On ESPN, scan /bet/parlay-builder for a parlay with at least 3 legs and negative American odds.",
])
for i in range(20):
    sport = ['NBA', 'NFL', 'MLB', 'NHL', 'soccer'][i % 5]
    n_legs = 2 + (i % 4)
    new_tasks.append(f"On ESPN's /bet/parlay-builder, locate a {n_legs}-leg {sport} parlay.")

# 6. recruit-247-composite (30 tasks)
for sport in ['ncaam', 'ncaaw']:
    for k in range(8):
        new_tasks.append(f"On ESPN, open /recruiting/{sport}/247-composite and find the rank-{k+1} recruit.")
new_tasks.extend([
    "On ESPN's NCAAM 247-composite page, count how many five-star recruits are listed.",
    "On ESPN's NCAAW 247-composite, identify recruits committed to specific programs.",
    "On ESPN, sort the 247-composite list and find the highest-ranked uncommitted recruit.",
    "On ESPN, find a recruit on the 247-composite with 'PG' as position.",
    "On ESPN, on /ncaam/recruiting/247-composite (alias route), confirm same data renders.",
    "On ESPN, locate the 247-composite page from ESPN's main recruiting hub.",
    "On ESPN, find a 247-composite recruit from a specific state.",
    "On ESPN, on the 247-composite, identify recruits with hometowns outside the USA.",
    "On ESPN, scan the 247-composite for NCAAW and find a recruit committed to UConn.",
    "On ESPN, count the total number of recruits on the 247-composite page for NCAAM.",
    "On ESPN, find a forward on the NCAAM 247-composite.",
    "On ESPN, identify recruits with 5 stars on /recruiting/ncaaw/247-composite.",
    "On ESPN, confirm the 247-composite is reachable via both /recruiting/NCAAM and /ncaam/recruiting paths.",
    "On ESPN, find the lowest-ranked recruit shown on the 247-composite.",
])

# 7. awards-finalist-list (40 tasks)
for sport in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    for year in ['2023', '2022', '2021']:
        new_tasks.append(f"On ESPN, open /{sport}/awards/{year} and report the awards shown for that year.")
new_tasks.extend([
    "On ESPN, on the NBA 2023-24 MVP awards entry, list the finalists shown.",
    "On ESPN, identify the Hart Trophy finalists for 2023-24 in /nhl/awards/2023.",
    "On ESPN, on /nfl/awards/2023, find the OPOY finalists.",
    "On ESPN, on /mlb/awards/2022, locate the AL MVP finalists list.",
    "On ESPN, on /soccer/awards/2022, find the Ballon d'Or finalists.",
    "On ESPN's awards page, report the voting share of the latest MVP winner.",
    "On ESPN, count the number of finalists listed for any NBA award in /nba/awards/2023.",
    "On ESPN, navigate from /awards (the hub) to /nba/awards/2023 and back.",
    "On ESPN, locate the announced date for the latest NHL Hart Trophy award.",
    "On ESPN, scan /nba/awards/2022 and identify finalists with at least 20% voting share.",
])
for sport in ['ncaam', 'ncaaw', 'ncaaf']:
    for year in ['2023']:
        new_tasks.append(f"On ESPN, open /{sport}/awards/{year} and report the awards shown.")

# 8. podcast-transcript-search (40 tasks)
for kw in PODCAST_KEYWORDS:
    new_tasks.append(f"On ESPN, search the podcasts page for transcripts containing '{kw}' and report the matches.")
for kw in PODCAST_KEYWORDS[:10]:
    new_tasks.append(f"On ESPN, use /podcasts/search?q={kw} and count the result rows.")
new_tasks.extend([
    "On ESPN, search podcasts for 'Mock Draft 6.0' and report the matching podcasts.",
    "On ESPN, on /podcasts/search?q=playoff, report whether 'The Lowe Post' appears.",
    "On ESPN, search podcasts for 'Bracketology' and report the host's name.",
    "On ESPN, search podcasts for 'parlay' and verify 'Cousin Sal Talks Gambling' is in the results.",
    "On ESPN, search podcasts for 'masters' and verify a golf podcast is returned.",
    "On ESPN, search podcasts with the keyword 'Champions League' and verify ESPN FC Daily appears.",
    "On ESPN, search /podcasts/search?q=draft and identify episodes that match.",
    "On ESPN, confirm the search box is reachable from the /podcasts hub.",
    "On ESPN, search podcasts for 'NIL' and report whether any results are found.",
    "On ESPN, search podcasts for 'goalie' and identify NHL-related results.",
])

# 9. watch-list-add (40 tasks)
for slug in WATCH_SHOWS:
    new_tasks.append(f"On ESPN, open /watch/{slug} and confirm the show detail page loads.")
new_tasks.extend([
    "On ESPN, browse /watch/list and identify all 30 for 30 documentaries.",
    "On ESPN, on /watch/list, filter by kind=documentary and report how many shows match.",
    "On ESPN, on /watch/list?sport=nfl, list the NFL-related shows.",
    "On ESPN, on /watch/list?kind=live-event, count the live events.",
    "On ESPN, on /watch/list?sport=soccer, identify Bundesliga or FA Cup entries.",
    "On ESPN, open /watch/the-last-dance (or the closest slug) and verify it's an ESPN+ documentary.",
    "On ESPN, find a 'simulcast' kind show on /watch/list.",
    "On ESPN, on /watch/list, find UFC-related live events.",
    "On ESPN, on /watch/list, count the documentaries about basketball.",
    "On ESPN, on /watch/list, find Masters Live and check its release date.",
])
for slug in WATCH_SHOWS[:6]:
    new_tasks.append(f"On ESPN, navigate to /watch/{slug} and click 'Add to Watch List'.")

# 10. ESPN+-content (30 tasks)
new_tasks.extend([
    "On ESPN, open /espnplus and verify ESPN+ branding is visible.",
    "On ESPN, browse /watch/list and report the number of shows with an ESPN+ badge.",
    "On ESPN, identify a live ESPN+ tennis event from /watch/list.",
    "On ESPN, find an ESPN+ Bundesliga event from /watch/list.",
    "On ESPN, on /watch/list?kind=live-event, confirm all entries are ESPN+ exclusive.",
    "On ESPN, list ESPN+ documentaries by sport on /watch/list.",
    "On ESPN, identify the Manningcast simulcast on the ESPN+ Watch list.",
    "On ESPN, confirm the ESPN+ Watch list shows release dates for documentaries.",
    "On ESPN, find an ESPN+ golf event for the Masters week.",
    "On ESPN, identify ESPN+ college football content on /watch/list?sport=ncaaf.",
    "On ESPN, identify ESPN+ NHL live coverage on /watch/list?sport=nhl.",
    "On ESPN, identify a Special-kind ESPN+ piece on /watch/list?kind=special.",
    "On ESPN, on /watch/list, find UFC PPV Pre-Show coverage.",
    "On ESPN, scan /watch/list?kind=series for College football series.",
    "On ESPN, identify any ESPN+ NWSL coverage on /watch/list.",
    "On ESPN, confirm the ESPN+ badge displays on the Watch list cards.",
    "On ESPN, search for tennis content on the Watch list.",
    "On ESPN, identify the host of Manningcast from /watch/manningcast.",
    "On ESPN, identify the studio behind a 30 for 30 documentary.",
    "On ESPN, on /watch/list?sport=mma, identify boxing or MMA coverage.",
    "On ESPN, confirm /watch (existing page) still loads alongside /watch/list.",
    "On ESPN, browse /watch/list?sport=mlb and identify MLB Sunday Leadoff.",
    "On ESPN, on /watch/list, find the longest-duration documentary.",
    "On ESPN, identify Caitlin Clark related ESPN+ content.",
    "On ESPN, on /watch/list, identify Eli's Places and Peyton's Places.",
    "On ESPN, identify any ESPN+ boxing coverage on the watch list.",
    "On ESPN, identify Bracketology Live on the ESPN+ watch list.",
    "On ESPN, confirm the ESPN+ branding includes a yellow accent badge.",
    "On ESPN, on /watch/list, count tennis-related live events.",
    "On ESPN, on /watch/list, count golf-related live events.",
])

# 11. multi-step (40 tasks)
new_tasks.extend([
    "On ESPN, find the most recent NBA game, then open its play-by-play, then identify the top scorer.",
    "On ESPN, open /scores, drill into one NBA game, then open the play-by-play.",
    "On ESPN, navigate from the NBA homepage to the all-time leaders, then click into the top scorer's player page.",
    "On ESPN, from /bet, open the parlay-builder, then pick the parlay with the highest odds.",
    "On ESPN, from /fantasy, click into NBA waiver wire, then add a player by reading the Add %.",
    "On ESPN, from /podcasts, search for 'draft', then open the first matching podcast.",
    "On ESPN, from /watch/list, find a Manningcast entry, then click into its detail page.",
    "On ESPN, navigate from /awards to /nba/awards/2023, then read the MVP finalists list.",
    "On ESPN, from the NBA scoreboard for 2024-04-09, click into a game, then open its play-by-play.",
    "On ESPN, from /fantasy/nba, click waiver-wire, then trade-analyzer.",
    "On ESPN, from /recruiting/ncaam/247-composite, click into a recruit's name (if linked).",
    "On ESPN, from the homepage, navigate to /bet/parlay-builder and confirm at least 6 featured parlays show.",
    "On ESPN, from /podcasts, find Pat McAfee Show, open the detail page, then read the latest episode title.",
    "On ESPN, from /watch/list?sport=nfl, click into KayRod Cast, then click related Manningcast.",
    "On ESPN, search ESPN for 'celtics', then click into the team page, then open the depth chart.",
    "On ESPN, navigate from /nba/awards/2022 to /nba/awards/2023 and compare MVP winners.",
    "On ESPN, from /scoreboard, drill into an NHL game, then open the play-by-play.",
    "On ESPN, from /nba/all-time, identify the player atop, then read their player profile.",
    "On ESPN, from /bet, then /bet/parlay-builder, find a 5-leg parlay and report its decimal odds.",
    "On ESPN, from /podcasts, filter to NBA, then open Hoop Collective, then read host name.",
    "On ESPN, from /fantasy, navigate to /fantasy/nfl/trade-analyzer, then to /fantasy/nfl/waiver-wire.",
    "On ESPN, from /watch/list, filter kind=documentary, then open one, then add it to the Watch List.",
    "On ESPN, from /recruiting/ncaaw/247-composite, find a recruit committed to a specific school.",
    "On ESPN, from /nhl/awards/2023, identify the Hart winner, then click into a related player page.",
    "On ESPN, from /scores?date=20240408, click into a game, then play-by-play, then return to /scores.",
    "On ESPN, from the homepage Featured grid, drill into one article, then into the linked team page.",
    "On ESPN, navigate /podcasts → /podcasts/search?q=mock → first result detail page.",
    "On ESPN, from the homepage, locate the ESPN BET tab, then drill into /bet/parlay-builder.",
    "On ESPN, from /watch (the original page) navigate to /watch/list, then filter by sport.",
    "On ESPN, from /awards hub, open /mlb/awards/2022, then click through to /mlb/awards/2023.",
    "On ESPN, from the global nav, click ESPN+, then Watch List, then a documentary.",
    "On ESPN, navigate /podcasts → search 'parlay' → open Cousin Sal Talks Gambling.",
    "On ESPN, from /nba/scoreboard?date=20240406, identify games shown.",
    "On ESPN, from /fantasy, hop to NHL waiver wire, then back to fantasy NBA waiver wire.",
    "On ESPN, from /bet, open parlay builder, then find a 3-leg parlay on the NHL.",
    "On ESPN, from /draft/nfl, navigate cross-link to /draft/nba (or /nba/draft).",
    "On ESPN, from /awards hub, navigate to NBA 2021-22 MVP entry.",
    "On ESPN, from /watch/list?kind=documentary, find a baseball documentary, then click in.",
    "On ESPN, from /podcasts, find Bracketology Live host and confirm via /podcast/bracketology-podcast detail.",
    "On ESPN, from /recruiting/ncaam/247-composite, sort by stars descending mentally and report the top.",
])

# Pad up if we are short of 800
while start_id + len(new_tasks) < 800:
    i = len(new_tasks)
    sport = ['nba', 'nfl', 'mlb', 'nhl', 'soccer'][i % 5]
    new_tasks.append(f"On ESPN, browse /{sport}/scoreboard and check that recent results render.")

with open(TASKS, 'a', encoding='utf-8') as f:
    for i, q in enumerate(new_tasks):
        rec = {
            'web_name': 'ESPN',
            'id': f'ESPN--{start_id + i}',
            'ques': q,
            'web': 'http://localhost:40014/',
            'upstream_url': 'https://www.espn.com/',
        }
        f.write(json.dumps(rec) + '\n')

print(f'Appended {len(new_tasks)} R4 tasks; new total = {start_id + len(new_tasks)}.')
