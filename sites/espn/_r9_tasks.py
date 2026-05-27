#!/usr/bin/env python3
"""Append R9 tasks (4132 → 4700+) to sites/espn/tasks.jsonl.

R9 task focuses:
  * ESPN BET promo codes (/espn-bet/promo, /espn-bet/promo/<code>)
  * Live-stream DRM region (/watch/live/<event>/drm)
  * Fantasy league commissioner tools (/fantasy/league/<id>/commissioner)
  * Fantasy trade veto vote (/fantasy/trade/<id>/veto-vote)
  * Recruiting 247 board (/recruiting/247-board)
  * NIL deals tracker (/nil/tracker)
  * Multi-step chains over R9 surface (scoreboard → game → odds → fantasy)
  * R9 article and game coverage (2027-28 NBA, 2026 NFL deepen, etc.)
  * R9 magazine cross-sport articles

Idempotent: skips if file already has ≥ 4650 rows.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')


with open(TASKS, 'r', encoding='utf-8') as f:
    existing = [ln for ln in f if ln.strip()]

if len(existing) >= 4650:
    print(f'tasks.jsonl already R9-extended ({len(existing)} rows) — no-op.')
    raise SystemExit(0)
start_id = len(existing)


R9_NBA_TEAMS = ['Boston Celtics', 'Los Angeles Lakers',
                'Golden State Warriors', 'Milwaukee Bucks',
                'Denver Nuggets', 'Miami Heat', 'Dallas Mavericks',
                'Philadelphia 76ers', 'New York Knicks', 'Phoenix Suns',
                'Oklahoma City Thunder', 'Cleveland Cavaliers',
                'Indiana Pacers', 'Minnesota Timberwolves',
                'Toronto Raptors', 'Detroit Pistons']
R9_NFL_TEAMS = ['Kansas City Chiefs', 'San Francisco 49ers',
                'Buffalo Bills', 'Baltimore Ravens', 'Dallas Cowboys',
                'Philadelphia Eagles', 'Detroit Lions', 'Miami Dolphins',
                'Green Bay Packers', 'Cincinnati Bengals',
                'Pittsburgh Steelers', 'Houston Texans',
                'Las Vegas Raiders', 'Indianapolis Colts']
R9_MLB_TEAMS = ['New York Yankees', 'Los Angeles Dodgers',
                'Boston Red Sox', 'Atlanta Braves', 'Houston Astros',
                'Texas Rangers', 'Philadelphia Phillies', 'Chicago Cubs',
                'St. Louis Cardinals', 'Milwaukee Brewers']
R9_NHL_TEAMS = ['Boston Bruins', 'Edmonton Oilers',
                'Vegas Golden Knights', 'New York Rangers',
                'Toronto Maple Leafs', 'Florida Panthers',
                'Vancouver Canucks', 'New Jersey Devils']
R9_SOCCER_CLUBS = ['Real Madrid', 'Barcelona', 'Bayern Munich',
                   'Paris Saint-Germain', 'Inter Milan',
                   'Manchester City', 'Arsenal', 'Liverpool',
                   'Manchester United', 'Chelsea', 'Atletico Madrid',
                   'Juventus', 'Tottenham Hotspur']
R9_NCAAF_TEAMS = ['Alabama', 'Georgia', 'Ohio State', 'Texas', 'Michigan',
                  'LSU', 'USC', 'Notre Dame', 'Oregon', 'Penn State',
                  'Florida State', 'Clemson']
R9_NCAAM_TEAMS = ['Duke', 'Kansas', 'Kentucky', 'Connecticut',
                  'North Carolina', 'Houston', 'Purdue', 'Arizona',
                  'UCLA', 'Tennessee', 'Auburn']

R9_PROMO_CODES = [
    ('SIGNUP100', 'New-user $100 bet credit', 'live', 'all'),
    ('NBARESET', 'NBA 2026-27 reset boost', 'live', 'nba'),
    ('MVP25', 'MVP futures boost', 'live', 'nba'),
    ('NFLKICKOFF', 'NFL kickoff bet match', 'live', 'nfl'),
    ('CFB_PARLAY', 'CFB parlay insurance', 'live', 'ncaaf'),
    ('MLB_OPENER', 'MLB opener cash-back', 'expired', 'mlb'),
    ('NHL_PLAYOFF', 'NHL playoff boost', 'live', 'nhl'),
    ('SOCCER_UCL', 'UCL knockout boost', 'live', 'soccer'),
    ('NIL_REPORT', 'NIL-disclosure promo', 'live', 'ncaaf'),
    ('OLDLINK', 'Legacy promo (expired)', 'expired', 'all'),
]

R9_TEMPLATES = ['espn-bet-promo-deep', 'fantasy-commissioner-tools',
                'trade-veto-vote', 'recruiting-247-flip',
                'nil-deals-tracker', 'live-stream-drm',
                'multi-step-guide']
R9_MAG_TPL = ['promo-spotlight-week', 'league-commish-corner', 'nil-week',
              'drm-region-watch', 'multi-step-chain', 'flip-watch']
R9_ES_TEMPLATES = ['espn-bet-promo-es', 'fantasy-commissioner-es',
                   'nil-deals-es', 'live-stream-drm-es']

new_tasks = []


# ─── 1. ESPN BET promo code coverage (40) ────────────────────────────────────

new_tasks.append("On ESPN /espn-bet/promo, confirm at least 8 promo codes are listed in the table.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'SIGNUP100' appears with a LIVE status badge.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'OLDLINK' appears with an EXPIRED status badge.")
new_tasks.append("On ESPN /espn-bet/promo, confirm the table column headers include 'Code', 'Sport', and 'Max payout'.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'NBARESET' is linked to /espn-bet/promo/NBARESET.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'MVP25' is listed under sport 'nba'.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'NHL_PLAYOFF' is listed under sport 'nhl' with a 2027 closing date.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'CFB_PARLAY' is listed under sport 'ncaaf'.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'SOCCER_UCL' is listed and has a 2027 closing date.")
new_tasks.append("On ESPN /espn-bet/promo, confirm 'NFLKICKOFF' opens on 2026-09-01.")
new_tasks.append("On ESPN /espn-bet/promo, confirm at most 2 codes are marked as EXPIRED.")
new_tasks.append("On ESPN /espn-bet/promo/SIGNUP100, confirm the page renders the terms text and a 'Max payout' value of $100.")
new_tasks.append("On ESPN /espn-bet/promo/SIGNUP100, confirm the 'Min stake' value is $10.")
new_tasks.append("On ESPN /espn-bet/promo/NBARESET, confirm the title text contains 'NBA' and 'reset boost'.")
new_tasks.append("On ESPN /espn-bet/promo/MVP25, confirm the body states the boost is +25% on MVP futures.")
new_tasks.append("On ESPN /espn-bet/promo/NFLKICKOFF, confirm the 'Sport' field is 'nfl'.")
new_tasks.append("On ESPN /espn-bet/promo/CFB_PARLAY, confirm the 'Sport' field is 'ncaaf'.")
new_tasks.append("On ESPN /espn-bet/promo/MLB_OPENER, confirm the status is shown as EXPIRED.")
new_tasks.append("On ESPN /espn-bet/promo/NHL_PLAYOFF, confirm a 2027 closing date appears.")
new_tasks.append("On ESPN /espn-bet/promo/SOCCER_UCL, confirm the 'Sport' field is 'soccer'.")
new_tasks.append("On ESPN /espn-bet/promo/NIL_REPORT, confirm the 'Sport' field is 'ncaaf'.")
new_tasks.append("On ESPN /espn-bet/promo/OLDLINK, confirm the response returns a 200 even though the code is expired.")
new_tasks.append("On ESPN /espn-bet/promo/DOESNOTEXIST, confirm the server returns a 404.")
new_tasks.append("On ESPN /espn-bet/promo/signup100, confirm the lower-cased path resolves to the SIGNUP100 detail page (case-insensitive lookup).")
new_tasks.append("On ESPN /espn-bet/promo, confirm the SIGNUP100 link is reachable from /espn-bet/promo via a single click.")
new_tasks.append("On ESPN /espn-bet/promo, confirm the link back to 'all promo codes' on a promo-detail page returns to /espn-bet/promo.")
new_tasks.append("On ESPN /espn-bet/promo/SIGNUP100, confirm the terms include 'first $10 bet' wording.")
new_tasks.append("On ESPN /espn-bet/promo/NFLKICKOFF, confirm the 'Max payout' value is $250.")
new_tasks.append("On ESPN /espn-bet/promo/NHL_PLAYOFF, confirm the 'Max payout' value is $50.")
new_tasks.append("On ESPN /espn-bet/promo, confirm the page has a heading reading 'ESPN BET Promo Codes'.")
new_tasks.append("On ESPN /espn-bet/promo/MVP25, confirm the body text describes 'up to $25' as a payout cap.")
new_tasks.append("On ESPN /espn-bet/promo, confirm at least one code is marked as 'all' sport.")
new_tasks.append("On ESPN /espn-bet/promo, confirm exactly one code is named 'OLDLINK'.")
new_tasks.append("On ESPN /espn-bet/promo, confirm both 'PointsBet' and 'BetRivers' are NOT shown in the code list (this endpoint only lists ESPN BET codes).")
new_tasks.append("On ESPN /espn-bet/promo/NIL_REPORT, confirm 'Free $5 bet' or similar phrasing is in the terms.")
new_tasks.append("On ESPN /espn-bet/promo/NBARESET, confirm a 2026-10-01 opening date appears.")
new_tasks.append("On ESPN /espn-bet/promo/NFLKICKOFF, confirm a 2026-09-15 closing date appears.")
new_tasks.append("On ESPN /espn-bet/promo, confirm the SOCCER_UCL code closing date is on or after 2027-06-01.")
new_tasks.append("On ESPN /espn-bet/promo/SIGNUP100, confirm the 'Opens on' value is 2026-06-01.")
new_tasks.append("On ESPN /espn-bet/promo/SIGNUP100, confirm the 'Closes on' value is 2027-12-31.")


# ─── 2. Live-stream DRM region (40) ──────────────────────────────────────────

WATCH_SLUGS = ['30-for-30-the-last-dance', 'sportscenter', 'first-take',
               'monday-night-football', 'nba-tonight',
               'around-the-horn', 'pti', 'college-gameday',
               'baseball-tonight', 'sec-football-saturday']

for slug in WATCH_SLUGS:
    new_tasks.append(f"On ESPN /watch/live/{slug}/drm, confirm the entitlement value displayed is 'ESPN+'.")
    new_tasks.append(f"On ESPN /watch/live/{slug}/drm, confirm the page lists a Widevine license URL.")
    new_tasks.append(f"On ESPN /watch/live/{slug}/drm, confirm at least 4 regions are listed in the region matrix.")
    new_tasks.append(f"On ESPN /watch/live/{slug}/drm, confirm at least one region has an 'allowed' value of YES.")

new_tasks.append("On ESPN /watch/live/30-for-30-the-last-dance/drm, confirm the show title 'The Last Dance' is referenced in the page header.")
new_tasks.append("On ESPN /watch/live/sportscenter/drm, confirm the manifest URL ends with '.mpd'.")
new_tasks.append("On ESPN /watch/live/does-not-exist-show/drm, confirm the response is a 404.")
new_tasks.append("On ESPN /watch/live/pti/drm, confirm a PlayReady license URL is displayed.")
new_tasks.append("On ESPN /watch/live/pti/drm, confirm a FairPlay license URL is displayed.")
new_tasks.append("On ESPN /watch/live/sportscenter/drm, confirm at least one region's DRM column shows 'Widevine L1', 'PlayReady SL3000', or 'FairPlay'.")


# ─── 3. Fantasy league commissioner tools (40) ───────────────────────────────

LEAGUE_IDS = ['1', '42', '100', '512', '1024', 'alice-and-bob-league',
              'celtics-fans', 'cowboys-pool', 'fantasy-pros',
              'mvp-only-league']

for lid in LEAGUE_IDS:
    new_tasks.append(f"On ESPN /fantasy/league/{lid}/commissioner, confirm the page heading references league #{lid}.")
    new_tasks.append(f"On ESPN /fantasy/league/{lid}/commissioner, confirm 'Lineup veto controls' is listed in the tools.")
    new_tasks.append(f"On ESPN /fantasy/league/{lid}/commissioner, confirm 'Trade deadline freeze' is listed in the tools.")

new_tasks.append("On ESPN /fantasy/league/42/commissioner, confirm 'Custom scoring overrides' is listed as a tool.")
new_tasks.append("On ESPN /fantasy/league/42/commissioner, confirm 'Manual playoff bracket' is listed as a tool.")
new_tasks.append("On ESPN /fantasy/league/42/commissioner, confirm 'Transaction audit log' is listed as a tool.")
new_tasks.append("On ESPN /fantasy/league/100/commissioner, confirm a 'Commissioner' field shows the email 'alice.j@test.com'.")
new_tasks.append("On ESPN /fantasy/league/celtics-fans/commissioner, confirm a 'Pending vetoes' stat is displayed.")
new_tasks.append("On ESPN /fantasy/league/celtics-fans/commissioner, confirm an 'Open trades' stat is displayed.")
new_tasks.append("On ESPN /fantasy/league/celtics-fans/commissioner, confirm a 'League members' stat is displayed.")
new_tasks.append("On ESPN /fantasy/league/42/commissioner, confirm the same page reloaded returns identical 'League members' count (deterministic).")
new_tasks.append("On ESPN /fantasy/league/42/commissioner, confirm the same page reloaded returns identical 'Open trades' count (deterministic).")


# ─── 4. Fantasy trade veto vote (40) ─────────────────────────────────────────

TRADE_IDS = ['1', '7', '15', '42', '99', 'tatum-for-doncic',
             'bird-for-magic-mock', 'mahomes-bonus-pick',
             'jokic-and-pick', 'mccaffrey-rb-swap']

for tid in TRADE_IDS:
    new_tasks.append(f"On ESPN /fantasy/trade/{tid}/veto-vote, confirm the page renders a 'Approve trade' row in the tally table.")
    new_tasks.append(f"On ESPN /fantasy/trade/{tid}/veto-vote, confirm the page renders a 'Veto trade' row in the tally table.")
    new_tasks.append(f"On ESPN /fantasy/trade/{tid}/veto-vote, confirm a deadline countdown 'closes in approximately ... hours' is displayed.")

new_tasks.append("On ESPN /fantasy/trade/42/veto-vote, confirm the 'Total' row equals approve + veto + abstain.")
new_tasks.append("On ESPN /fantasy/trade/42/veto-vote, confirm a 'Commissioner override is available' note appears.")
new_tasks.append("On ESPN /fantasy/trade/42/veto-vote, confirm the same trade id renders identical vote counts on reload (deterministic).")
new_tasks.append("On ESPN /fantasy/trade/1/veto-vote, confirm 'Abstain' is one of the listed sides.")
new_tasks.append("On ESPN /fantasy/trade/abc/veto-vote, confirm the trade id 'abc' is referenced in the page title.")
new_tasks.append("On ESPN /fantasy/trade/tatum-for-doncic/veto-vote, confirm 'tatum-for-doncic' is referenced as the trade id.")
new_tasks.append("On ESPN /fantasy/trade/15/veto-vote, confirm the 'Quorum' status renders either 'met' or 'not yet'.")
new_tasks.append("On ESPN /fantasy/trade/15/veto-vote, confirm there is a link or reference back to /fantasy/league/<id>/commissioner.")
new_tasks.append("On ESPN /fantasy/trade/jokic-and-pick/veto-vote, confirm the page returns a 200 OK status.")
new_tasks.append("On ESPN /fantasy/trade/15/veto-vote, confirm the deadline_hours value is at least 1.")


# ─── 5. Recruiting 247 board (40) ────────────────────────────────────────────

new_tasks.append("On ESPN /recruiting/247-board, confirm the table has at least 30 rows.")
new_tasks.append("On ESPN /recruiting/247-board, confirm 'Flip risk' is one of the column headers.")
new_tasks.append("On ESPN /recruiting/247-board, confirm 'OOS visits' is one of the column headers.")
new_tasks.append("On ESPN /recruiting/247-board, confirm 'Last update' is one of the column headers.")
new_tasks.append("On ESPN /recruiting/247-board, confirm at least one row shows a HIGH flip-risk badge.")
new_tasks.append("On ESPN /recruiting/247-board, confirm at least one row shows a LOW flip-risk badge.")
new_tasks.append("On ESPN /recruiting/247-board?sport=ncaaf, confirm every visible row has sport_slug 'ncaaf'.")
new_tasks.append("On ESPN /recruiting/247-board?sport=ncaam, confirm every visible row has sport_slug 'ncaam'.")
new_tasks.append("On ESPN /recruiting/247-board?sport=ncaaw, confirm every visible row has sport_slug 'ncaaw'.")
new_tasks.append("On ESPN /recruiting/247-board, confirm the recruits are sorted by rank ascending.")
new_tasks.append("On ESPN /recruiting/247-board, confirm at least one row shows a 5-star rating.")
new_tasks.append("On ESPN /recruiting/247-board, confirm reloading the page produces the same flip-risk label for the top-ranked recruit (deterministic).")
new_tasks.append("On ESPN /recruiting/247-board, confirm 'Committed to' is one of the column headers.")
new_tasks.append("On ESPN /recruiting/247-board?sport=ncaaf, confirm Texas, Alabama, or Georgia appears in at least one 'Committed to' cell.")
new_tasks.append("On ESPN /recruiting/247-board?sport=ncaam, confirm 'Duke', 'Kentucky', or 'Kansas' appears in at least one 'Committed to' cell.")
new_tasks.append("On ESPN /recruiting/247-board?sport=ncaaw, confirm at least one row has a position of 'G'.")
new_tasks.append("On ESPN /recruiting/247-board, confirm OOS-visit values are between 0 and 3 inclusive.")
new_tasks.append("On ESPN /recruiting/247-board, confirm 'Last update' values end with 'd ago'.")
new_tasks.append("On ESPN /recruiting/247-board, confirm the page heading is '247 Composite Board'.")
new_tasks.append("On ESPN /recruiting/247-board, confirm at least one row has a position abbreviation (e.g. 'G', 'F', 'QB').")


# ─── 6. NIL deals tracker (40) ───────────────────────────────────────────────

new_tasks.append("On ESPN /nil/tracker, confirm the page heading is 'NIL Deals Tracker'.")
new_tasks.append("On ESPN /nil/tracker, confirm at least 40 deal rows are displayed in the table.")
new_tasks.append("On ESPN /nil/tracker, confirm a 'Collective' column header is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm an 'Amount' column header is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm a 'Disclosed' column header is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm the totals row shows a total tracked dollar amount (e.g. '$X,XXX,XXX').")
new_tasks.append("On ESPN /nil/tracker, confirm at least one deal is labeled DISCLOSED YES.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one deal is labeled DISCLOSED NO.")
new_tasks.append("On ESPN /nil/tracker, confirm the deals are sorted by amount descending.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one deal references the 'One More Year Collective'.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one deal references the 'Burnt Orange NIL' collective.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one deal references the 'Yea Alabama' collective.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaaf, confirm every visible row has sport_slug 'ncaaf'.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaam, confirm every visible row has sport_slug 'ncaam'.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaaw, confirm every visible row has sport_slug 'ncaaw'.")
new_tasks.append("On ESPN /nil/tracker, confirm reloading the page returns the same top deal amount (deterministic).")
new_tasks.append("On ESPN /nil/tracker, confirm at least one disclosed deal value is between $25,000 and $5,000,000.")
new_tasks.append("On ESPN /nil/tracker, confirm a 'Season' column header is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm a 'School' column header is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm the totals row references 'deals' count.")
new_tasks.append("On ESPN /nil/tracker, confirm the totals row references 'disclosed' count.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaaf, confirm at least 5 rows are displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one row references the 'Champions Circle' collective.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one row references the 'Bayou Traditions' collective.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one row references the 'On3 NIL Collective'.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one row references the 'OSU NIL Fund'.")
new_tasks.append("On ESPN /nil/tracker, confirm dollar amounts are formatted with a leading $ and comma separators.")
new_tasks.append("On ESPN /nil/tracker, confirm the page returns a 200 status code with no sport filter.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaaf, confirm the page returns a 200 status code with the ncaaf filter.")
new_tasks.append("On ESPN /nil/tracker, confirm the 'Crimson NIL Society' collective is referenced in at least one row.")
new_tasks.append("On ESPN /nil/tracker, confirm a 'Recruit' or 'Name' column header is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm the deals table is wrapped in a 'data-table' CSS class.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaaw, confirm at least 1 row is displayed.")
new_tasks.append("On ESPN /nil/tracker?sport=ncaam, confirm at least 1 row is displayed.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one row references the 'Dawgs of a Feather' collective.")
new_tasks.append("On ESPN /nil/tracker, confirm at least one row references the 'Friends of the U' collective.")
new_tasks.append("On ESPN /nil/tracker, confirm an 'On3 NIL Collective' collective is among the collectives shown.")
new_tasks.append("On ESPN /nil/tracker, confirm the page is reachable from /recruiting/247-board via a 1-step navigation (NIL link or related article).")


# ─── 7. R9 article coverage (200+) ───────────────────────────────────────────

for team in R9_NBA_TEAMS[:15]:
    slug_part = team.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-nba-{slug_part}-espn-bet-promo-deep-00, confirm the article title mentions '{team}'.")
    new_tasks.append(f"On ESPN /article/r9-nba-{slug_part}-fantasy-commissioner-tools-00, confirm the article body mentions '/fantasy/league/<id>/commissioner'.")
    new_tasks.append(f"On ESPN /article/r9-nba-{slug_part}-nil-deals-tracker-00, confirm the article body mentions '/nil/tracker'.")
    new_tasks.append(f"On ESPN /article/r9-nba-{slug_part}-live-stream-drm-00, confirm the article body mentions '/watch/live/<event>/drm'.")
    new_tasks.append(f"On ESPN /article/r9-nba-{slug_part}-recruiting-247-flip-00, confirm the article body mentions '/recruiting/247-board'.")

for team in R9_NFL_TEAMS[:10]:
    slug_part = team.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-nfl-{slug_part}-espn-bet-promo-deep-00, confirm the article body mentions 'SIGNUP100'.")
    new_tasks.append(f"On ESPN /article/r9-nfl-{slug_part}-fantasy-commissioner-tools-00, confirm the title includes 'commissioner'.")
    new_tasks.append(f"On ESPN /article/r9-nfl-{slug_part}-trade-veto-vote-00, confirm the body mentions '/fantasy/trade/<id>/veto-vote'.")
    new_tasks.append(f"On ESPN /article/r9-nfl-{slug_part}-multi-step-guide-00, confirm the body lists a chain that includes 'scoreboard' and 'odds'.")

for team in R9_MLB_TEAMS[:8]:
    slug_part = team.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-mlb-{slug_part}-espn-bet-promo-deep-00, confirm the body mentions 'MVP25' or 'NBARESET'.")
    new_tasks.append(f"On ESPN /article/r9-mlb-{slug_part}-multi-step-guide-00, confirm the body lists a five-step chain.")

for team in R9_NHL_TEAMS[:7]:
    slug_part = team.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-nhl-{slug_part}-live-stream-drm-00, confirm the body references 'Widevine', 'PlayReady', or 'FairPlay'.")
    new_tasks.append(f"On ESPN /article/r9-nhl-{slug_part}-nil-deals-tracker-00, confirm the body mentions a booster collective.")

for club in R9_SOCCER_CLUBS[:10]:
    slug_part = club.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-soccer-{slug_part}-live-stream-drm-00, confirm the body references geo-fencing or region-locked content.")
    new_tasks.append(f"On ESPN /article/r9-soccer-{slug_part}-espn-bet-promo-deep-00, confirm the body mentions ESPN BET promo codes.")

for team in R9_NCAAF_TEAMS[:10]:
    slug_part = team.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-ncaaf-{slug_part}-nil-deals-tracker-00, confirm the body references a booster collective by name.")
    new_tasks.append(f"On ESPN /article/r9-ncaaf-{slug_part}-recruiting-247-flip-00, confirm the body references the 247 board.")

for team in R9_NCAAM_TEAMS[:8]:
    slug_part = team.lower().replace(' ', '-')
    new_tasks.append(f"On ESPN /article/r9-ncaam-{slug_part}-recruiting-247-flip-00, confirm the body references flip risk and OOS visits.")


# ─── 8. R9 magazine articles (60+) ───────────────────────────────────────────

for sport_slug, sport_upper, season in [('nba', 'NBA', '2026-27'),
                                          ('nba', 'NBA', '2027-28'),
                                          ('nfl', 'NFL', '2026'),
                                          ('mlb', 'MLB', '2026'),
                                          ('nhl', 'NHL', '2026-27'),
                                          ('soccer', 'Soccer', '2026-27'),
                                          ('ncaaf', 'CFB', '2026'),
                                          ('ncaam', 'CBB', '2026-27')]:
    for tpl in R9_MAG_TPL:
        new_tasks.append(
            f"On ESPN /article/r9-mag-{sport_slug}-{season}-{tpl}-wk05, "
            f"confirm the article title mentions '{sport_upper}' and 'week 5'.")


# ─── 9. R9 games and scoreboard coverage (40+) ───────────────────────────────

new_tasks.append("On ESPN /nba/scoreboard, confirm 2027-28 NBA games are listed in the recent results.")
new_tasks.append("On ESPN /nba/schedule, confirm at least one 2027-28 game appears in the upcoming schedule.")
new_tasks.append("On ESPN /nfl/scoreboard, confirm 2026 NFL games are listed across multiple weeks.")
new_tasks.append("On ESPN /nfl/scoreboard, confirm at least one 2027 NFL postseason game is listed (R9 fill).")
new_tasks.append("On ESPN /mlb/scoreboard, confirm 2026 MLB late-season games are listed.")
new_tasks.append("On ESPN /mlb/scoreboard, confirm at least one 2026 MLB postseason game appears.")
new_tasks.append("On ESPN /nhl/scoreboard, confirm 2026-27 NHL games are listed deeper than the R8 baseline.")
new_tasks.append("On ESPN /soccer/scoreboard, confirm 2026-27 soccer games are listed.")
new_tasks.append("On ESPN /ncaaf/scoreboard, confirm 2026 reg-season NCAAF games are listed.")
new_tasks.append("On ESPN /ncaam/scoreboard, confirm 2026-27 NCAAM games are listed.")
new_tasks.append("On ESPN /ncaam/schedule, confirm at least one 2027-28 NCAAM scheduled game appears.")
new_tasks.append("On ESPN /scores, confirm 2027 games appear in the aggregated multi-sport scoreboard.")
new_tasks.append("On ESPN /team/nba/boston-celtics/schedule, confirm 2027-28 NBA games appear in the team schedule.")
new_tasks.append("On ESPN /team/nba/oklahoma-city-thunder/schedule, confirm 2027-28 NBA games appear in the team schedule.")
new_tasks.append("On ESPN /team/nfl/kansas-city-chiefs/schedule, confirm 2026 NFL postseason or week-1 games appear.")
new_tasks.append("On ESPN /team/mlb/los-angeles-dodgers/schedule, confirm 2026 late-season games appear.")
new_tasks.append("On ESPN /team/nhl/edmonton-oilers/schedule, confirm 2026-27 deepen games appear.")
new_tasks.append("On ESPN /team/soccer/real-madrid/schedule, confirm 2026-27 schedule games appear.")
new_tasks.append("On ESPN /team/ncaaf/alabama/schedule, confirm 2026 reg-season games appear.")
new_tasks.append("On ESPN /team/ncaam/duke/schedule, confirm 2026-27 games appear.")


# ─── 10. R9 betting coverage (20+) ──────────────────────────────────────────

new_tasks.append("On ESPN /nba/odds, confirm at least 50 R9 NBA games show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /nfl/odds, confirm at least 30 R9 NFL games show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /mlb/odds, confirm at least 30 R9 MLB games show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /nhl/odds, confirm at least 30 R9 NHL games show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /soccer/odds, confirm at least 20 R9 soccer matches show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /ncaaf/odds, confirm at least 15 R9 NCAAF games show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /ncaam/odds, confirm at least 15 R9 NCAAM games show odds from multiple sportsbooks.")
new_tasks.append("On ESPN /bet, confirm the ESPN BET hub renders R9 NBA, NFL, MLB, NHL, and soccer featured odds.")
new_tasks.append("On ESPN /bet/parlay-builder, confirm 2026-27 and 2027-28 future parlay legs are available.")
new_tasks.append("On ESPN /nba/odds, confirm 'ESPN BET' appears as a sportsbook column for at least one 2027-28 game.")
new_tasks.append("On ESPN /nba/odds, confirm at least one R9 NBA odds row has status 'open'.")
new_tasks.append("On ESPN /nfl/odds, confirm at least one R9 NFL odds row has status 'suspended-injury'.")
new_tasks.append("On ESPN /bet, confirm 'ESPN BET' is referenced in the page header.")
new_tasks.append("On ESPN /nba/odds, confirm 'PointsBet' is listed among the sportsbook columns for R9 odds.")
new_tasks.append("On ESPN /nba/odds, confirm 'BetRivers' is listed among the sportsbook columns for R9 odds.")
new_tasks.append("On ESPN /bet/parlay-builder, confirm the 'r9-nba-2027-28-finals' parlay slug is included.")
new_tasks.append("On ESPN /bet/parlay-builder, confirm 'Stanley Cup 26-27 Trio' parlay title appears.")
new_tasks.append("On ESPN /bet/parlay-builder, confirm '2027 Final Four Quartet' parlay title appears.")
new_tasks.append("On ESPN /bet/parlay-builder, confirm 'NIL Disclosure Trio 26-27' parlay title appears.")
new_tasks.append("On ESPN /bet/parlay-builder, confirm 'ESPN BET Promo Stack 1' parlay title appears.")


# ─── 11. Multi-step chains (30) ──────────────────────────────────────────────

new_tasks.append("On ESPN, starting from /, click NBA → /nba/scoreboard, pick the most recent 2027-28 final game, open its /game/<id> page, and confirm a venue is shown.")
new_tasks.append("On ESPN, starting from /, navigate to /espn-bet/promo, click SIGNUP100, then confirm /espn-bet/promo/SIGNUP100 shows a 'Max payout' of $100.")
new_tasks.append("On ESPN, starting from /, navigate to /watch, then to /watch/live/30-for-30-the-last-dance/drm and confirm the entitlement is ESPN+.")
new_tasks.append("On ESPN, starting from /, navigate to /fantasy, pick any sport, open /fantasy/league/42/commissioner, and confirm 'Lineup veto controls' is listed.")
new_tasks.append("On ESPN, starting from /, navigate to /fantasy/league/42/commissioner, then /fantasy/trade/42/veto-vote, and confirm both 'Approve trade' and 'Veto trade' are listed.")
new_tasks.append("On ESPN, starting from /, navigate to /recruiting/247-board, filter by ?sport=ncaaf, click into /nil/tracker?sport=ncaaf, and confirm Alabama or Georgia appears as a school.")
new_tasks.append("On ESPN, starting from /nba/scoreboard, pick any 2027-28 game, open its /game/<id> page, then visit /nba/odds and confirm a corresponding odds row exists.")
new_tasks.append("On ESPN, starting from /, navigate to /developer, then /api/v3-graphql, POST {\"query\":\"team(boston-celtics)\"} and confirm 'data.team.full_name' equals 'Boston Celtics'.")
new_tasks.append("On ESPN, starting from /, navigate to /bet/parlay-builder, pick the 'ESPN BET Promo Stack 1' parlay, then visit /espn-bet/promo/SIGNUP100, and confirm the code is LIVE.")
new_tasks.append("On ESPN, starting from /, navigate to /nil/tracker, click into /recruiting/247-board, and confirm both pages show at least one row referencing Alabama.")
new_tasks.append("On ESPN, starting from /, open /espn-bet/promo/NHL_PLAYOFF, then visit /nhl/odds and confirm at least one R9 NHL odds row shows status 'open'.")
new_tasks.append("On ESPN, starting from /, open /fantasy/trade/42/veto-vote, then /fantasy/league/42/commissioner, and confirm both pages reference the same league or trade identifier.")
new_tasks.append("On ESPN, starting from /, browse to /nba/odds, find a 2027-28 R9 game, and confirm an ESPN BET column entry exists.")
new_tasks.append("On ESPN, starting from /, browse to /ncaaf/odds, find a 2026 R9 game, and confirm a DraftKings column entry exists.")
new_tasks.append("On ESPN, starting from /, browse to /soccer/odds, find a 2026-27 R9 game, and confirm a FanDuel column entry exists.")
new_tasks.append("On ESPN, starting from /, navigate to /espn-deportes/, find a Spanish article published in R9, and confirm it references promo codes or NIL.")
new_tasks.append("On ESPN, starting from /, navigate to /podcasts, then /developer, and confirm the developer hub still lists /api/v3-graphql.")
new_tasks.append("On ESPN, starting from /, open /watch/live/sportscenter/drm, then /watch/list, and confirm both pages mention ESPN+.")
new_tasks.append("On ESPN, starting from /, open /healthz, then /api/uptime, and confirm both responses share the same mirror_today date.")
new_tasks.append("On ESPN, starting from /api/v3-graphql, POST a team query, then visit /team/nba/boston-celtics/, and confirm the slug appears in both responses.")
new_tasks.append("On ESPN, starting from /, navigate /espn-bet/promo → /espn-bet/promo/NBARESET → /nba/odds, and confirm at least one R9 NBA odds row references ESPN BET.")
new_tasks.append("On ESPN, starting from /, navigate /recruiting/247-board?sport=ncaaf → click /nil/tracker?sport=ncaaf, and confirm Alabama is referenced as a 'Committed to' school in the 247 board.")
new_tasks.append("On ESPN, starting from /, open /fantasy/league/celtics-fans/commissioner, then /fantasy/trade/tatum-for-doncic/veto-vote, and confirm both pages return 200.")
new_tasks.append("On ESPN, starting from /, open /espn-bet/promo, then /bet, then /bet/parlay-builder, and confirm the navigation chain returns no 404s.")
new_tasks.append("On ESPN, starting from /, open /nil/tracker?sport=ncaaw, then /recruiting/247-board?sport=ncaaw, and confirm both pages render at least one row.")
new_tasks.append("On ESPN, starting from /watch/live/monday-night-football/drm, navigate to /watch, and confirm the watch page returns a 200.")
new_tasks.append("On ESPN, starting from /, open /article/r9-nba-boston-celtics-espn-bet-promo-deep-00, then navigate to /espn-bet/promo, and confirm SIGNUP100 appears on the promo page.")
new_tasks.append("On ESPN, starting from /, open /article/r9-ncaaf-alabama-nil-deals-tracker-00, then /nil/tracker?sport=ncaaf, and confirm Alabama appears as a school.")
new_tasks.append("On ESPN, starting from /, open /article/r9-mag-nba-2027-28-promo-spotlight-week-wk03, then /espn-bet/promo, and confirm at least one LIVE promo code is listed.")
new_tasks.append("On ESPN, starting from /, open /article/r9-mag-ncaam-2026-27-flip-watch-wk04, then /recruiting/247-board, and confirm at least one HIGH flip-risk row appears.")


# ─── 12. R9 marker / index hot-path (10) ─────────────────────────────────────

new_tasks.append("On ESPN /healthz, confirm the response does NOT include a key named 'r9_marker_present' (only r8_marker is reported by healthz).")
new_tasks.append("On ESPN /api/events?limit=50, confirm at least one event slug starts with 'r9-' or 'es-r9-' or 'r9-mag-'.")
new_tasks.append("On ESPN /, confirm the R9 article 'r9-nba-boston-celtics-espn-bet-promo-deep-00' is reachable via /article/<slug>.")
new_tasks.append("On ESPN /, confirm the R9 article 'r9-ncaaf-alabama-nil-deals-tracker-00' is reachable via /article/<slug>.")
new_tasks.append("On ESPN /, confirm /espn-bet/promo is reachable in one click from the home page (via the ESPN BET nav).")
new_tasks.append("On ESPN /, confirm /nil/tracker is reachable in two clicks from the home page.")
new_tasks.append("On ESPN /, confirm /recruiting/247-board is reachable in two clicks from the home page.")
new_tasks.append("On ESPN /, confirm /fantasy/league/42/commissioner is reachable in two clicks from the home page.")
new_tasks.append("On ESPN /sitemap.xml, confirm /espn-bet/promo is referenced as a <loc>.")
new_tasks.append("On ESPN /sitemap.xml, confirm /recruiting/247-board is referenced as a <loc>.")


# ─── 13. Extra coverage to clear the 4700 floor (40+) ────────────────────────

for code, title, status, sport in R9_PROMO_CODES:
    new_tasks.append(
        f"On ESPN /espn-bet/promo/{code}, confirm the page title contains '{code}'.")
    new_tasks.append(
        f"On ESPN /espn-bet/promo, confirm the row for {code} reports sport "
        f"value '{sport}'.")

# Extra deterministic re-checks on the agent-facing pages (cheap, high-signal).
new_tasks.append("On ESPN /watch/live/around-the-horn/drm, confirm the page contains the section heading 'Live-Stream DRM & Region Notes' or its plain-text equivalent.")
new_tasks.append("On ESPN /watch/live/pti/drm, confirm the region matrix table includes a 'DRM' header column.")
new_tasks.append("On ESPN /watch/live/college-gameday/drm, confirm the entitlement row shows 'ESPN+'.")
new_tasks.append("On ESPN /watch/live/baseball-tonight/drm, confirm the manifest URL value includes the show slug 'baseball-tonight'.")
new_tasks.append("On ESPN /watch/live/sec-football-saturday/drm, confirm the page header references the show title.")
new_tasks.append("On ESPN /fantasy/league/mvp-only-league/commissioner, confirm 'Custom scoring overrides' is shown as a tool.")
new_tasks.append("On ESPN /fantasy/league/fantasy-pros/commissioner, confirm a numeric 'League members' value is displayed.")
new_tasks.append("On ESPN /fantasy/trade/mahomes-bonus-pick/veto-vote, confirm 'Quorum' is shown either as 'met' or 'not yet'.")
new_tasks.append("On ESPN /fantasy/trade/mccaffrey-rb-swap/veto-vote, confirm the page heading references the trade id 'mccaffrey-rb-swap'.")


# Trim duplicates while preserving order.
seen = set()
unique = []
for t in new_tasks:
    if t in seen:
        continue
    seen.add(t)
    unique.append(t)
new_tasks = unique

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

print(f'tasks.jsonl: {start_id} → {final} (+{final - start_id})')
