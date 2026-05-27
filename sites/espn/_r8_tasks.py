#!/usr/bin/env python3
"""Append R8 tasks (3383 → 4000+) to sites/espn/tasks.jsonl.

R8 task focuses:
  * Keyboard shortcuts (j / k / g + h|s / '/' / '?' / Cmd+K / Esc)
  * Command palette (Cmd+K) with /api/command-palette JSON backing
  * Contextual help — stat glossary (/stat-glossary, /api/stat/<KEY>)
  * GraphQL-min v3 (/api/v3-graphql)
  * Score-update webhook (/webhook/score-update)
  * Developer / fantasy-app integration page (/developer, /developer/fantasy-app)
  * Telemetry beacon (/api/telemetry)
  * Observability: /healthz, /api/events, /api/uptime
  * R8 article and game coverage
  * Multi-step chains touching new R8 surface
  * Magazine cross-sport articles

Idempotent: skips if file already has ≥ 3900 rows.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')


with open(TASKS, 'r', encoding='utf-8') as f:
    existing = [ln for ln in f if ln.strip()]

if len(existing) >= 3900:
    print(f'tasks.jsonl already R8-extended ({len(existing)} rows) — no-op.')
    raise SystemExit(0)
start_id = len(existing)


R8_NBA_TEAMS = ['Boston Celtics', 'Los Angeles Lakers',
                'Golden State Warriors', 'Milwaukee Bucks',
                'Denver Nuggets', 'Miami Heat', 'Dallas Mavericks',
                'Philadelphia 76ers', 'New York Knicks', 'Phoenix Suns',
                'Oklahoma City Thunder', 'Cleveland Cavaliers',
                'Indiana Pacers', 'Minnesota Timberwolves',
                'New Orleans Pelicans', 'Sacramento Kings',
                'Memphis Grizzlies', 'Atlanta Hawks', 'Brooklyn Nets',
                'Chicago Bulls', 'Houston Rockets', 'LA Clippers',
                'Orlando Magic']
R8_NFL_TEAMS = ['Kansas City Chiefs', 'San Francisco 49ers',
                'Buffalo Bills', 'Baltimore Ravens', 'Dallas Cowboys',
                'Philadelphia Eagles', 'Detroit Lions', 'Miami Dolphins',
                'Green Bay Packers', 'Cincinnati Bengals',
                'Pittsburgh Steelers', 'Houston Texans',
                'New York Giants', 'Los Angeles Rams',
                'Tampa Bay Buccaneers', 'Atlanta Falcons']
R8_MLB_TEAMS = ['New York Yankees', 'Los Angeles Dodgers',
                'Boston Red Sox', 'Atlanta Braves', 'Houston Astros',
                'Texas Rangers', 'Philadelphia Phillies', 'Chicago Cubs',
                'San Diego Padres', 'Toronto Blue Jays', 'New York Mets',
                'Seattle Mariners']
R8_NHL_TEAMS = ['Boston Bruins', 'Edmonton Oilers',
                'Vegas Golden Knights', 'New York Rangers',
                'Toronto Maple Leafs', 'Florida Panthers',
                'Colorado Avalanche', 'Tampa Bay Lightning']
R8_SOCCER_CLUBS = ['Real Madrid', 'Barcelona', 'Bayern Munich',
                   'Paris Saint-Germain', 'Inter Milan',
                   'Manchester City', 'Arsenal', 'Liverpool',
                   'Manchester United', 'Chelsea', 'Atletico Madrid']
R8_TEMPLATES = ['gm-perspective', 'coach-clipboard',
                'health-report-monthly', 'travel-and-schedule',
                'fan-voices', 'season-snapshot', 'lineup-lab',
                'tape-study', 'developer-corner-r8', 'broadcast-booth',
                'fantasy-app-spotlight-r8', 'history-corner']
R8_MAG_TPL = ['weekly-power-rankings', 'week-in-quotes',
              'numbers-of-the-week', 'what-we-learned', 'looking-ahead']
R8_ES_TEMPLATES = ['perspectiva-gm', 'pizarra-tecnico',
                   'snapshot-temporada', 'voces-aficion',
                   'salud-mensual', 'rincon-desarrollador']

new_tasks = []


# ─── 1. Observability: /healthz, /api/uptime, /api/events (25) ───────────────

new_tasks.append("On ESPN /healthz, confirm the JSON response has status='ok' and a 'service' field equal to 'espn-mirror'.")
new_tasks.append("On ESPN /healthz, confirm the JSON response includes 'r8_marker_present' and that the value is true.")
new_tasks.append("On ESPN /healthz, confirm a 'mirror_today' field appears in the JSON.")
new_tasks.append("On ESPN /health, confirm the response 301-redirects to /healthz.")
new_tasks.append("On ESPN /api/uptime, confirm the JSON has 'seconds_since_cutover' and the value is a positive integer.")
new_tasks.append("On ESPN /api/uptime, confirm the response includes 'r1_cutover' equal to '2024-04-01T00:00:00'.")
new_tasks.append("On ESPN /api/uptime, confirm the JSON includes a 'human' field formatted as 'N days'.")
new_tasks.append("On ESPN /api/uptime, confirm the 'mirror_today' field matches the mirror date banner on the homepage.")
new_tasks.append("On ESPN /api/events, confirm the JSON has an 'events' array of article-published entries.")
new_tasks.append("On ESPN /api/events?limit=5, confirm 'count' equals 5 (or fewer if fewer articles exist).")
new_tasks.append("On ESPN /api/events, confirm each event entry has 'type' equal to 'article.published'.")
new_tasks.append("On ESPN /api/events?limit=10, confirm at least one event 'slug' starts with 'r8-' or 'es-r8-' or 'r8-mag-'.")
new_tasks.append("On ESPN /api/events?limit=3, confirm each entry contains a 'sport_slug' field.")
new_tasks.append("On ESPN /api/events, confirm the events are sorted with the most recently published first.")
new_tasks.append("On ESPN /, confirm /healthz is listed in /sitemap.xml as a <loc> entry.")
new_tasks.append("On ESPN /sitemap.xml, confirm /stat-glossary appears as a <loc> entry.")
new_tasks.append("On ESPN /sitemap.xml, confirm /developer is listed in a <loc> entry.")
new_tasks.append("On ESPN /sitemap.xml, confirm /help/keyboard appears as a <loc> entry.")
new_tasks.append("On ESPN /robots.txt, confirm 'Disallow: /webhook/' is present.")
new_tasks.append("On ESPN /robots.txt, confirm 'Disallow: /api/telemetry' appears in the rules.")
new_tasks.append("On ESPN /robots.txt, confirm 'Sitemap: /sitemap.xml' is still present after R8.")
new_tasks.append("On ESPN /healthz, confirm the response Content-Type is application/json.")
new_tasks.append("On ESPN /api/events?limit=50, confirm the response contains at most 50 entries.")
new_tasks.append("On ESPN /api/events?limit=1000, confirm the server caps the limit at 100 (and 'count' is no greater than 100).")
new_tasks.append("On ESPN /api/uptime, confirm the seconds_since_cutover value is greater than 86400 (one day).")


# ─── 2. GraphQL v3 (/api/v3-graphql) (35) ────────────────────────────────────

new_tasks.append("On ESPN /api/v3-graphql, confirm a GET returns JSON metadata with 'version' equal to 'v3'.")
new_tasks.append("On ESPN /api/v3-graphql, confirm the GET response lists '__schema', 'game(id)', 'article(slug)', and 'team(slug)' in the 'queries' array.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"__schema\"} and confirm the response 'data.__schema.types' lists 'Team' and 'Article'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"team(boston-celtics)\"} and confirm 'data.team.full_name' equals 'Boston Celtics'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"team(los-angeles-lakers)\"} and confirm the response has a non-null 'data.team'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"team(kansas-city-chiefs)\"} and confirm 'data.team.sport_slug' equals 'nfl'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"team(new-york-yankees)\"} and confirm 'data.team.sport_slug' equals 'mlb'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"team(boston-bruins)\"} and confirm 'data.team.sport_slug' equals 'nhl'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"team(does-not-exist)\"} and confirm 'data.team' is null.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"article(r8-nba-boston-celtics-season-snapshot-00)\"} and confirm 'data.article.title' contains 'Boston Celtics'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"article(r8-nfl-kansas-city-chiefs-coach-clipboard-00)\"} and confirm 'data.article.sport_slug' equals 'nfl'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"article(r8-nba-boston-celtics-developer-corner-r8-00)\"} and confirm the author is 'ESPN Staff'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"game(1)\"} and confirm 'data.game.id' equals 1.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"game(100)\"} and confirm 'data.game' has 'status' and 'venue' keys.")
new_tasks.append("On ESPN /api/v3-graphql, POST with an empty body and confirm 'errors' contains a 'Missing query.' message.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"unknown(foo)\"} and confirm the 'errors' array contains a message starting with 'Unknown query'.")
new_tasks.append("On ESPN /api/v3-graphql?q=team(real-madrid), confirm 'data.team.sport_slug' equals 'soccer'.")
new_tasks.append("On ESPN /api/v3-graphql, POST {\"query\":\"game(notanint)\"} and confirm 'errors' contains 'Bad game id.'.")

for slug in ['boston-celtics', 'los-angeles-lakers', 'golden-state-warriors',
             'milwaukee-bucks', 'denver-nuggets', 'miami-heat',
             'kansas-city-chiefs', 'san-francisco-49ers', 'buffalo-bills',
             'baltimore-ravens', 'new-york-yankees', 'los-angeles-dodgers',
             'boston-red-sox', 'atlanta-braves', 'boston-bruins',
             'edmonton-oilers', 'real-madrid']:
    new_tasks.append(
        f"On ESPN /api/v3-graphql, POST {{\"query\":\"team({slug})\"}} and "
        f"confirm 'data.team.slug' equals '{slug}'.")


# ─── 3. Webhook /webhook/score-update (20) ───────────────────────────────────

new_tasks.append("On ESPN /webhook/score-update, a GET request returns JSON metadata listing 'POST' in the 'methods' array.")
new_tasks.append("On ESPN /webhook/score-update, a GET request lists 'game_id', 'home_score', and 'away_score' in the 'expects' object.")
new_tasks.append("On ESPN /webhook/score-update, a GET response 'returns' field includes 'ack_id'.")
new_tasks.append("On ESPN, POST {\"game_id\":42,\"home_score\":110,\"away_score\":108} to /webhook/score-update and confirm 'received' is true.")
new_tasks.append("On ESPN, POST {\"game_id\":42,\"home_score\":110,\"away_score\":108} to /webhook/score-update twice and confirm the 'ack_id' is identical across both calls (deterministic).")
new_tasks.append("On ESPN, POST {\"game_id\":99,\"home_score\":5,\"away_score\":4} to /webhook/score-update and confirm the 'echo' object equals the request payload.")
new_tasks.append("On ESPN, POST {} (empty JSON) to /webhook/score-update and confirm the response still returns 'received':true with an ack_id.")
new_tasks.append("On ESPN, POST to /webhook/score-update with a period field 'Q3 04:21' and confirm the period appears in the 'echo'.")
new_tasks.append("On ESPN, POST to /webhook/score-update WITHOUT a CSRF token and confirm the request succeeds (endpoint is csrf-exempt for webhook use).")
new_tasks.append("On ESPN, POST to /webhook/score-update with game_id=1 and confirm the 'note' field mentions 'not persisted'.")
new_tasks.append("On ESPN /webhook/score-update, confirm a POST returns Content-Type application/json.")
new_tasks.append("On ESPN /webhook/score-update, POST {\"game_id\":1234} and confirm the ack_id length is 16 hex characters.")
new_tasks.append("On ESPN /robots.txt, confirm /webhook/ paths are disallowed from indexing.")
new_tasks.append("On ESPN, POST {\"game_id\":7000,\"home_score\":42,\"away_score\":42} to /webhook/score-update and confirm 'received' is true.")
new_tasks.append("On ESPN /webhook/score-update, GET shows the 'endpoint' value '/webhook/score-update'.")
new_tasks.append("On ESPN /webhook/score-update, the GET expects schema documents an 'away_score' field of type 'int'.")
new_tasks.append("On ESPN, POST {\"game_id\":50,\"home_score\":3,\"away_score\":2} to /webhook/score-update and confirm the response has a 16-char ack_id derived deterministically from the payload.")
new_tasks.append("On ESPN /webhook/score-update, the GET methods array does NOT include 'PUT' or 'DELETE'.")
new_tasks.append("On ESPN, POST a payload to /webhook/score-update and then visit /healthz, confirming the healthz response is unaffected by the webhook traffic.")
new_tasks.append("On ESPN, POST a payload to /webhook/score-update and confirm the response is JSON (not HTML).")


# ─── 4. Developer hub + fantasy-app guide (25) ───────────────────────────────

new_tasks.append("On ESPN /developer, confirm the page title contains 'Developer Hub'.")
new_tasks.append("On ESPN /developer, confirm an HTML table with id 'r8-endpoints-table' lists at least 5 endpoints.")
new_tasks.append("On ESPN /developer, confirm '/api/v3-graphql' appears in the endpoints table.")
new_tasks.append("On ESPN /developer, confirm '/webhook/score-update' appears in the endpoints table.")
new_tasks.append("On ESPN /developer, confirm '/healthz' appears in the endpoints table.")
new_tasks.append("On ESPN /developer/, confirm the trailing-slash variant also serves the developer hub page.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm the page title contains 'Fantasy App'.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm a 'Quickstart' section is present with at least 4 numbered steps.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm a 'Sample roster lookup' section lists at least 4 team slugs.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm a 'Webhook contract' section shows a POST example to /webhook/score-update.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm at least one team link in the sample list points to a /team/<sport>/<slug> URL.")
new_tasks.append("On ESPN /developer, click the /api/v3-graphql link and confirm the JSON metadata page loads.")
new_tasks.append("On ESPN /developer, click the /api/uptime link and confirm a JSON uptime payload is shown.")
new_tasks.append("On ESPN /developer, click the /healthz link and confirm the JSON response status is 'ok'.")
new_tasks.append("On ESPN /developer, confirm the GraphQL example shows a query string 'team(boston-celtics)'.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm 'polling cadences' is mentioned in the Quickstart steps.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm '/api/events' is referenced as a way to subscribe to score events.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm 'ack_id' is mentioned in the webhook contract example.")
new_tasks.append("On ESPN /, the Developer Hub link is reachable from /sitemap.xml even if not visible in the global nav.")
new_tasks.append("On ESPN /developer, confirm '/developer/fantasy-app' is listed in the endpoints table.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm an HTML element with id 'r8-sample-teams' is present.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm the page has a section heading 'Quickstart'.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm 'team(slug)' appears somewhere in the Quickstart instructions.")
new_tasks.append("On ESPN /developer/fantasy-app, confirm '/api/telemetry' is mentioned in the Quickstart instructions.")
new_tasks.append("On ESPN /developer, confirm a 'GraphQL-min v3 example' section is rendered.")


# ─── 5. Telemetry (15) ───────────────────────────────────────────────────────

new_tasks.append("On ESPN /api/telemetry, a GET request returns JSON metadata with 'persisted' equal to false.")
new_tasks.append("On ESPN /api/telemetry, confirm the GET 'methods' array lists 'POST'.")
new_tasks.append("On ESPN /api/telemetry, confirm the GET 'fields' array includes 'event', 'page', and 'props'.")
new_tasks.append("On ESPN, POST {\"event\":\"pageview\",\"page\":\"/\"} to /api/telemetry and confirm 'ack' is true.")
new_tasks.append("On ESPN, POST {\"event\":\"click\",\"page\":\"/nba\"} to /api/telemetry twice and confirm the 'beacon_id' is identical across both calls.")
new_tasks.append("On ESPN, POST {\"event\":\"pageview\",\"page\":\"/scores\"} to /api/telemetry and confirm 'received.page' equals '/scores'.")
new_tasks.append("On ESPN, POST {} (empty body) to /api/telemetry and confirm the response still has 'ack':true.")
new_tasks.append("On ESPN /api/telemetry, the POST response 'beacon_id' is 12 hex characters long.")
new_tasks.append("On ESPN, POST a telemetry beacon then visit /healthz and confirm both endpoints still report healthy state.")
new_tasks.append("On ESPN, POST a telemetry beacon WITHOUT a CSRF token and confirm the call succeeds (endpoint is csrf-exempt).")
new_tasks.append("On ESPN /robots.txt, confirm /api/telemetry is disallowed for crawlers.")
new_tasks.append("On ESPN /api/telemetry, confirm a GET response contains a 'persisted' field documenting that beacons are not stored.")
new_tasks.append("On ESPN, POST {\"event\":\"scroll\",\"page\":\"/article/r8-nba-boston-celtics-season-snapshot-00\"} to /api/telemetry and confirm 'received.event' equals 'scroll'.")
new_tasks.append("On ESPN /api/telemetry, confirm the GET response 'endpoint' field equals '/api/telemetry'.")
new_tasks.append("On ESPN, POST {\"props\":{\"a\":1}} to /api/telemetry and confirm the response 'received' echoes the props.")


# ─── 6. Keyboard shortcuts (35) ──────────────────────────────────────────────

new_tasks.append("On ESPN /, confirm the page includes a script with id 'r8-keyboard-shortcuts-script'.")
new_tasks.append("On ESPN /, press '?' and confirm the keyboard help dialog with id 'r8-keyboard-help' becomes visible.")
new_tasks.append("On ESPN /, confirm the keyboard help dialog mentions the 'j' shortcut for the next game card.")
new_tasks.append("On ESPN /, confirm the keyboard help dialog mentions the 'k' shortcut for the previous game card.")
new_tasks.append("On ESPN /, confirm the keyboard help dialog mentions 'g' then 'h' to jump home.")
new_tasks.append("On ESPN /, confirm the keyboard help dialog mentions 'Cmd+K' to open the command palette.")
new_tasks.append("On ESPN /, press 'Escape' after opening the keyboard help and confirm the dialog hides.")
new_tasks.append("On ESPN /help/keyboard, confirm the page title contains 'Keyboard Shortcuts'.")
new_tasks.append("On ESPN /help/keyboard, confirm the shortcuts table id is 'r8-keyboard-shortcuts'.")
new_tasks.append("On ESPN /help/keyboard, confirm a table row lists 'j' as the key for moving to the next game card.")
new_tasks.append("On ESPN /help/keyboard, confirm a table row lists 'k' as the key for moving to the previous game card.")
new_tasks.append("On ESPN /help/keyboard, confirm a table row mentions 'Cmd+K' or 'Ctrl+K' for the command palette.")
new_tasks.append("On ESPN /help/keyboard, confirm a 'Tip: command palette' section is present.")
new_tasks.append("On ESPN /nba/scoreboard, press 'j' and confirm the first game card receives the 'r8-focused' CSS class.")
new_tasks.append("On ESPN /nba/scoreboard, press 'j' twice then 'k' once and confirm the focused card moved by one position net.")
new_tasks.append("On ESPN /nba/scoreboard, press 'j' and confirm the a11y live region content updates to mention 'Next game card'.")
new_tasks.append("On ESPN /, press '/' and confirm the focus moves to the page search input.")
new_tasks.append("On ESPN /, press 'g' then 's' and confirm the browser navigates to /scores.")
new_tasks.append("On ESPN /, press 'g' then 'h' from /scores and confirm the browser returns to the home page.")
new_tasks.append("On ESPN /, press 'g' then 'n' and confirm the browser navigates to /nba/.")
new_tasks.append("On ESPN /, press 'g' then 'f' and confirm the browser navigates to /nfl/.")
new_tasks.append("On ESPN /, with focus inside a text input, press 'j' and confirm scroll-focus is NOT moved (typing context is respected).")
new_tasks.append("On ESPN /, confirm the keyboard help dialog can ALSO be opened by visiting /help/keyboard directly.")
new_tasks.append("On ESPN /help/keyboard, confirm a list item describes the 'Esc' key as closing dialogs.")
new_tasks.append("On ESPN /help/keyboard, confirm a list item describes '/' as focusing the search box.")
new_tasks.append("On ESPN /, confirm the keyboard help dialog has 'aria-modal' set to 'true'.")
new_tasks.append("On ESPN /, confirm the command palette dialog has 'aria-modal' set to 'true'.")
new_tasks.append("On ESPN /, confirm both R8 dialogs use role='dialog'.")
new_tasks.append("On ESPN /, confirm clicking the keyboard help dialog backdrop hides the dialog.")
new_tasks.append("On ESPN /, confirm clicking the command palette backdrop hides the palette.")
new_tasks.append("On ESPN /, confirm pressing '?' inside a text input does NOT open the keyboard help dialog.")
new_tasks.append("On ESPN /, confirm pressing Cmd+K (or Ctrl+K) inside a text input STILL opens the command palette.")
new_tasks.append("On ESPN /, confirm the keyboard shortcut handler also handles 'Esc' to close any open dialog.")
new_tasks.append("On ESPN /, confirm the keyboard help dialog footer links to /help/keyboard for the full reference.")
new_tasks.append("On ESPN /help/keyboard, confirm at least 10 keyboard shortcut rows are listed in the table.")


# ─── 7. Command palette (Cmd+K) (30) ─────────────────────────────────────────

new_tasks.append("On ESPN /, press Cmd+K (or Ctrl+K) and confirm the command palette dialog 'r8-command-palette' becomes visible.")
new_tasks.append("On ESPN /, after opening the command palette, confirm an input element with id 'r8-command-palette-input' is focused.")
new_tasks.append("On ESPN /, after opening the command palette, confirm the list 'r8-command-palette-list' renders at least 5 items.")
new_tasks.append("On ESPN /, open the command palette and type 'NBA Score' — confirm a 'NBA Scoreboard' item appears in the filtered list.")
new_tasks.append("On ESPN /, open the command palette and type 'Stat' — confirm a 'Stat Glossary' item appears.")
new_tasks.append("On ESPN /, open the command palette and type 'Developer' — confirm a 'Developer Hub' item appears.")
new_tasks.append("On ESPN /, open the command palette and type 'Fantasy' — confirm a 'Fantasy' item appears.")
new_tasks.append("On ESPN /, open the command palette and confirm pressing ArrowDown moves the 'is-active' selection to the next item.")
new_tasks.append("On ESPN /, open the command palette and confirm pressing ArrowUp moves the 'is-active' selection to the previous item.")
new_tasks.append("On ESPN /, open the command palette, type 'NBA Stand', press Enter, and confirm the browser navigates to /nba/standings.")
new_tasks.append("On ESPN /, open the command palette and click the 'Home' item — confirm navigation to /.")
new_tasks.append("On ESPN /, open the command palette and confirm pressing Escape hides the palette.")
new_tasks.append("On ESPN /api/command-palette, confirm the response JSON has a 'commands' array.")
new_tasks.append("On ESPN /api/command-palette, confirm 'count' equals the length of the 'commands' array.")
new_tasks.append("On ESPN /api/command-palette, confirm at least one command has href '/scores'.")
new_tasks.append("On ESPN /api/command-palette, confirm one command labels 'Stat Glossary' with href '/stat-glossary'.")
new_tasks.append("On ESPN /api/command-palette, confirm one command labels 'Developer Hub' with href '/developer'.")
new_tasks.append("On ESPN /api/command-palette, confirm at least one command points to '/nba/scoreboard'.")
new_tasks.append("On ESPN /api/command-palette, confirm at least one command points to '/nfl/standings'.")
new_tasks.append("On ESPN /api/command-palette, confirm at least one command points to '/help/keyboard'.")
new_tasks.append("On ESPN /api/command-palette, confirm at least one command points to '/espn-deportes/'.")
new_tasks.append("On ESPN /api/command-palette, confirm at least one command points to '/podcasts'.")
new_tasks.append("On ESPN /, open the palette, type 'xyz-no-match' and confirm the list renders empty (or shows zero items).")
new_tasks.append("On ESPN /, open the palette and confirm the hint mentions ArrowUp, ArrowDown, Enter, and Esc.")
new_tasks.append("On ESPN /, confirm the palette panel limits to 12 results even on empty query.")
new_tasks.append("On ESPN /, after opening the palette and pressing Escape, confirm the input no longer has document focus.")
new_tasks.append("On ESPN /, confirm the command palette items each render a label span AND a path span.")
new_tasks.append("On ESPN /, confirm the active palette item carries the 'is-active' CSS class.")
new_tasks.append("On ESPN /, confirm the palette can be reopened multiple times without page reload.")
new_tasks.append("On ESPN /, open the command palette and verify the data-r8-href attribute on the first item matches its visible path.")


# ─── 8. Stat glossary + contextual help (30) ─────────────────────────────────

GLOSSARY_KEYS = ['PER', 'eFG%', 'TS%', 'USG%', 'BPM', 'VORP', 'EPA',
                 'DVOA', 'QBR', 'OPS', 'wRC+', 'FIP', 'Corsi', 'xG',
                 'PPG', 'RPG', 'APG', 'SPG', 'BPG']

new_tasks.append("On ESPN /stat-glossary, confirm the page title contains 'Stat Glossary'.")
new_tasks.append("On ESPN /stat-glossary, confirm a dl element with id 'r8-stat-glossary-list' is present.")
new_tasks.append("On ESPN /stat-glossary, confirm at least 15 glossary rows are rendered.")
new_tasks.append("On ESPN /stat-glossary, confirm an 'API access' section mentions /api/stat/<KEY>.")
new_tasks.append("On ESPN /stat-glossary, confirm each glossary row has a data-stat-key attribute.")
for key in GLOSSARY_KEYS[:12]:
    new_tasks.append(
        f"On ESPN /stat-glossary, confirm a row exists for stat key '{key}'.")
for key in GLOSSARY_KEYS[:8]:
    new_tasks.append(
        f"On ESPN /api/stat/{key}, confirm the JSON response contains "
        f"'key' equal to '{key}' and a non-empty 'definition'.")
new_tasks.append("On ESPN /api/stat/PER, confirm 'name' equals 'Player Efficiency Rating'.")
new_tasks.append("On ESPN /api/stat/eFG%, confirm 'name' equals 'Effective Field Goal Percentage'.")
new_tasks.append("On ESPN /api/stat/QBR, confirm the definition mentions 'quarterback'.")
new_tasks.append("On ESPN /api/stat/OPS, confirm the definition mentions 'OBP' or 'SLG'.")
new_tasks.append("On ESPN /api/stat/xG, confirm the definition mentions 'shot' and 'probability'.")
new_tasks.append("On ESPN /api/stat/Corsi, confirm the definition mentions 'shot attempts'.")
new_tasks.append("On ESPN /api/stat/zzzzzz, confirm the server responds with a 404 status code.")
new_tasks.append("On ESPN /, confirm the stat-glossary tooltip element with id 'r8-stat-tooltip' is present in the DOM.")
new_tasks.append("On ESPN /, hover any element carrying data-stat-key='PER' (if present) and confirm a tooltip with the PER definition appears.")


# ─── 9. R8 articles coverage (200) ───────────────────────────────────────────

for tpl in R8_TEMPLATES:
    for team in R8_NBA_TEAMS[:10]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r8-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the article title mentions "
            f"'{team}' and the byline shows 'ESPN Staff'.")

for tpl in R8_TEMPLATES[:8]:
    for team in R8_NFL_TEAMS[:8]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r8-nfl-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm a NewsArticle JSON-LD "
            f"block declares datePublished and report the value.")

for tpl in R8_TEMPLATES[:6]:
    for team in R8_MLB_TEAMS[:6]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r8-mlb-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the article body loads and "
            f"the published date appears in the header.")

for tpl in R8_ES_TEMPLATES:
    for team in R8_NBA_TEAMS[:8]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'es-r8-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the article author is "
            f"'ESPN Deportes' and the JSON-LD inLanguage is 'es'.")


# ─── 10. R8 magazine articles (50) ───────────────────────────────────────────

for sport_pair in [('nba', '2026-27'), ('nfl', '2026'),
                   ('mlb', '2026'), ('nhl', '2026-27'),
                   ('soccer', '2025-26')]:
    sport, season = sport_pair
    for tpl in R8_MAG_TPL:
        for wk in [1, 5, 10]:
            slug = f'r8-mag-{sport}-{season}-{tpl}-wk{wk:02d}'
            new_tasks.append(
                f"On ESPN /article/{slug}, confirm the article author is "
                f"'ESPN Magazine' and the title mentions week {wk}.")


# ─── 11. R8 games (60) ───────────────────────────────────────────────────────

for gid in range(7200, 7600, 25):
    new_tasks.append(
        f"On ESPN /game/{gid}, confirm the recap text mentions the "
        f"final score and the SportsEvent JSON-LD includes a venue.")
for gid in range(7800, 8200, 28):
    new_tasks.append(
        f"On ESPN /game/{gid}, click into the play-by-play view if "
        f"available and confirm the header shows both team names.")
for gid in range(8500, 8900, 30):
    new_tasks.append(
        f"On ESPN /game/{gid}, confirm a date_display field is rendered "
        f"and matches the SportsEvent JSON-LD startDate.")
for gid in range(9000, 9500, 30):
    new_tasks.append(
        f"On ESPN /game/{gid}, confirm both teams' game leaders are "
        f"shown on the recap page.")


# ─── 12. R8 betting odds (30) ────────────────────────────────────────────────

for gid in range(7200, 7700, 35):
    new_tasks.append(
        f"On ESPN /nba/odds, locate the odds row for game {gid} and "
        f"confirm at least two sportsbooks are listed.")
for gid in range(8000, 8400, 32):
    new_tasks.append(
        f"On ESPN /nfl/odds, confirm the odds for game {gid} show "
        f"spread, total, and moneyline columns.")
for gid in range(8800, 9200, 30):
    new_tasks.append(
        f"On ESPN /mlb/odds, confirm the odds for game {gid} list "
        f"over/under odds in addition to moneyline.")


# ─── 13. R8 parlays (20) ─────────────────────────────────────────────────────

R8_PARLAY_SLUGS = ['r8-nba-mvp-tier1', 'r8-nba-rookie-tier1',
                   'r8-nfl-mvp-treble', 'r8-mlb-cy-young-double-2026',
                   'r8-nhl-art-ross-future', 'r8-soccer-ucl-semis-quartet',
                   'r8-ncaaf-cfp-2026-quartet', 'r8-ncaam-2026-final-four',
                   'r8-nba-finals-2026-2027', 'r8-deportes-laliga-trio',
                   'r8-mlb-postseason-quartet', 'r8-nfl-super-bowl-coach',
                   'r8-nhl-stanley-cup-trio', 'r8-nba-overs-three-team',
                   'r8-cross-sport-sunday', 'r8-nba-coy-trio',
                   'r8-mma-title-double', 'r8-tennis-major-treble',
                   'r8-golf-major-double', 'r8-fantasy-three-app']
for slug in R8_PARLAY_SLUGS:
    new_tasks.append(
        f"On ESPN /bet/parlay-builder, locate the parlay '{slug}' and "
        f"report its american odds.")


# ─── 14. Multi-step chains using R8 surface (40) ─────────────────────────────

new_tasks.append("On ESPN /, press Cmd+K to open the command palette, type 'Developer', press Enter to land on /developer, then click /api/v3-graphql in the endpoints table and confirm the GET metadata page renders.")
new_tasks.append("On ESPN /, visit /developer/fantasy-app, copy the first team slug listed, then POST {\"query\":\"team(<slug>)\"} to /api/v3-graphql and confirm 'data.team.slug' matches.")
new_tasks.append("On ESPN /, visit /stat-glossary, copy the PER definition, then fetch /api/stat/PER and confirm the definition matches.")
new_tasks.append("On ESPN /, open the keyboard help dialog (?), then close it (Esc), then open the command palette (Cmd+K), then close it (Esc) — confirm both dialogs return to hidden state.")
new_tasks.append("On ESPN /, visit /healthz to confirm health, then /api/uptime to confirm uptime, then /api/events?limit=5 to confirm the five most recent article events.")
new_tasks.append("On ESPN /, POST a payload to /webhook/score-update, then visit /api/events to confirm the events list still loads (webhook does not pollute events list).")
new_tasks.append("On ESPN /nba/scoreboard, press 'j' three times to focus the third game card, then visit that game's page and confirm the SportsEvent JSON-LD is present.")
new_tasks.append("On ESPN /, open the command palette, type 'Stat', press Enter to navigate to /stat-glossary, then click into the API access section and read the /api/stat/PER definition.")
new_tasks.append("On ESPN /, open /developer, click /webhook/score-update to read the GET metadata, then POST a sample payload and confirm the ack_id is deterministic on retry.")
new_tasks.append("On ESPN /, navigate to /espn-deportes/, then open the command palette (Cmd+K), type 'Help', press Enter, and confirm /help/keyboard loads with the Spanish-locale page returning to EN.")
new_tasks.append("On ESPN /, fetch /api/command-palette, pick the first command, follow its href, then confirm the destination page returns 200.")
new_tasks.append("On ESPN /, visit /api/v3-graphql via GET, then POST {\"query\":\"__schema\"}, then POST {\"query\":\"team(real-madrid)\"} — confirm all three return 200 with valid JSON.")
new_tasks.append("On ESPN /, visit /developer/fantasy-app, locate the webhook contract example, then POST the example payload to /webhook/score-update and verify the ack_id is non-empty.")
new_tasks.append("On ESPN /, visit /robots.txt, confirm /webhook/ is disallowed, then attempt a POST to /webhook/score-update anyway and confirm the endpoint still accepts the payload (robots.txt is a directive, not enforcement).")
new_tasks.append("On ESPN /, visit /stat-glossary, click the 'API access' note, then fetch /api/stat/eFG% and confirm the returned JSON 'name' equals 'Effective Field Goal Percentage'.")
new_tasks.append("On ESPN /, press Cmd+K, type 'Fantasy', press Enter, confirm /fantasy loads, then in the address bar visit /developer/fantasy-app and confirm it is a distinct page.")
new_tasks.append("On ESPN /, open the command palette, type 'ESPN Deportes', press Enter to navigate to /espn-deportes/, then confirm the locale switcher shows ES as active.")
new_tasks.append("On ESPN /, visit /healthz, confirm 'r8_marker_present':true, then visit /sitemap.xml and confirm /developer is listed.")
new_tasks.append("On ESPN /, visit /api/events?limit=5, pick the first event slug, navigate to /article/<slug>, confirm the NewsArticle JSON-LD is present, then return to /api/events.")
new_tasks.append("On ESPN /, visit /developer, click /api/uptime, copy the seconds_since_cutover value, then visit /healthz and confirm both endpoints respond with mirror_today='2024-04-10'.")

for team in R8_NBA_TEAMS[:5]:
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /, open the command palette, type 'NBA', press Enter "
        f"to land on /nba/, then open the {team} team page and confirm "
        f"the R8 'season-snapshot' article /article/r8-nba-{slug}-season-snapshot-00 "
        f"is linked from the team news.")

for team in R8_NFL_TEAMS[:5]:
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /, open /nfl/, open the {team} team page, then open "
        f"/article/r8-nfl-{slug}-coach-clipboard-00 and confirm the "
        f"NewsArticle JSON-LD declares the author.")

for team in R8_SOCCER_CLUBS[:5]:
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /, switch language to Spanish via the locale switcher, "
        f"open /espn-deportes/soccer, click any {team} article, then "
        f"return to / and press '?' to open the keyboard shortcut help.")


# ─── 15. Magazine cross-sport articles (30) ──────────────────────────────────

for sport_pair in [('nba', '2025-26'), ('nba', '2026-27'),
                   ('nfl', '2026'), ('mlb', '2026'),
                   ('nhl', '2026-27'), ('soccer', '2025-26')]:
    sport, season = sport_pair
    for wk in [2, 6, 9]:
        slug = f'r8-mag-{sport}-{season}-weekly-power-rankings-wk{wk:02d}'
        new_tasks.append(
            f"On ESPN /article/{slug}, confirm the article tag list "
            f"includes 'magazine' and 'power-rankings'.")


# ─── 16. Index / hot-path tasks (10) ─────────────────────────────────────────

new_tasks.append("On ESPN /nba/scoreboard, confirm at least 30 final-status NBA games are listed in the recent results.")
new_tasks.append("On ESPN /nfl/scoreboard, confirm the page loads within reasonable time and renders R8 NFL 2026 games.")
new_tasks.append("On ESPN /mlb/scoreboard, confirm the 2026 MLB games are listed alongside earlier seasons.")
new_tasks.append("On ESPN /nhl/scoreboard, confirm the 2026-27 NHL games are listed.")
new_tasks.append("On ESPN /soccer/scoreboard, confirm 2025-26 deep soccer games are listed alongside 2025-26.")
new_tasks.append("On ESPN /scores, confirm 2026 games appear in the aggregated multi-sport scoreboard.")
new_tasks.append("On ESPN /nba/odds, confirm at least 5 R8 NBA games show odds from multiple sportsbooks (ESPN BET, DraftKings, FanDuel, BetMGM, etc.).")
new_tasks.append("On ESPN /nba/odds, confirm 'PointsBet' or 'BetRivers' appears as one of the listed sportsbook columns for at least one R8 game.")
new_tasks.append("On ESPN /team/nba/boston-celtics/schedule, confirm both 2025-26 and 2026-27 season games appear in the team schedule.")
new_tasks.append("On ESPN /team/nfl/kansas-city-chiefs/schedule, confirm the 2026 season games are listed.")


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

print(f'tasks.jsonl: was {start_id} rows, +{len(new_tasks)} = {final}')
