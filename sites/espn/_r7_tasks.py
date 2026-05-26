#!/usr/bin/env python3
"""Append R7 tasks (2513 → 3300+) to sites/espn/tasks.jsonl.

R7 task focuses:
  * SEO SportsEvent JSON-LD schema on /game/<id>
  * NewsArticle JSON-LD on /article/<slug>
  * TVSeries JSON-LD on /watch/<slug>
  * PodcastSeries JSON-LD on /podcast/<slug>
  * /robots.txt + /sitemap.xml presence
  * /rss/<sport>.xml RSS feeds (one per sport)
  * /espn-deportes/ Spanish locale + per-sport
  * Header locale switcher (EN | ES) in nav
  * Accessibility live region (aria-live polite)
  * Sound-cue toggle (checkbox + chime)
  * Multi-step cross-page chains

Idempotent: skips if file already has ≥ 3250 rows.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, 'tasks.jsonl')


with open(TASKS, 'r', encoding='utf-8') as f:
    existing = [ln for ln in f if ln.strip()]

if len(existing) >= 3300:
    print(f'tasks.jsonl already R7-extended ({len(existing)} rows) — no-op.')
    raise SystemExit(0)
start_id = len(existing)


# ─── Source pools (R7) ────────────────────────────────────────────────────────

R7_NBA_TEAMS = ['Boston Celtics', 'Los Angeles Lakers', 'Golden State Warriors',
                'Milwaukee Bucks', 'Denver Nuggets', 'Miami Heat',
                'Dallas Mavericks', 'Philadelphia 76ers', 'New York Knicks',
                'Phoenix Suns', 'Oklahoma City Thunder', 'Cleveland Cavaliers',
                'Indiana Pacers', 'Minnesota Timberwolves',
                'New Orleans Pelicans', 'Sacramento Kings']
R7_NFL_TEAMS = ['Kansas City Chiefs', 'San Francisco 49ers', 'Buffalo Bills',
                'Baltimore Ravens', 'Dallas Cowboys', 'Philadelphia Eagles',
                'Detroit Lions', 'Miami Dolphins', 'Green Bay Packers',
                'Cincinnati Bengals', 'Pittsburgh Steelers']
R7_MLB_TEAMS = ['New York Yankees', 'Los Angeles Dodgers', 'Boston Red Sox',
                'Atlanta Braves', 'Houston Astros', 'Texas Rangers',
                'Philadelphia Phillies', 'Chicago Cubs', 'San Diego Padres']
R7_NHL_TEAMS = ['Boston Bruins', 'Edmonton Oilers', 'Vegas Golden Knights',
                'New York Rangers', 'Toronto Maple Leafs', 'Florida Panthers']
R7_SOCCER_CLUBS = ['Real Madrid', 'Barcelona', 'Bayern Munich',
                   'Paris Saint-Germain', 'Inter Milan', 'Manchester City',
                   'Arsenal', 'Liverpool', 'Manchester United']

SPORTS_FOR_RSS = ['nba', 'nfl', 'mlb', 'nhl', 'soccer', 'ncaaf', 'ncaam',
                  'tennis', 'golf', 'mma', 'fantasy', 'watch', 'ncaaw']

R7_TEMPLATES = ['analytics-edge', 'rookie-watch-monthly', 'midseason-grade',
                'milestone-watch', 'salary-cap-corner',
                'rivalry-week-feature', 'beat-writer-mailbag']
R7B_TEMPLATES = ['longform-feature', 'practice-report', 'storyline-watch',
                 'matchup-pillars', 'one-on-one-interview', 'numbers-game']
R7_ES_TEMPLATES = ['analytics-edge', 'midseason-grade', 'rookie-watch-monthly']

new_tasks = []


# ─── 1. SEO: SportsEvent JSON-LD on /game/<id> (60) ──────────────────────────

for gid in list(range(50, 250, 10)) + list(range(5100, 5300, 10)) + \
           list(range(6000, 6400, 30)):
    new_tasks.append(
        f"On ESPN /game/{gid}, view the page source and confirm there is a "
        f"<script type=\"application/ld+json\"> block declaring "
        f"@type \"SportsEvent\".")
    new_tasks.append(
        f"On ESPN /game/{gid}, inspect the embedded JSON-LD and report "
        f"the value of the \"sport\" field.")


# ─── 2. SEO: NewsArticle on /article/<slug> (60) ─────────────────────────────

for tpl in R7_TEMPLATES[:6]:
    for team in R7_NBA_TEAMS[:5]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r7-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, view source and confirm a "
            f"<script type=\"application/ld+json\"> block declares "
            f"@type \"NewsArticle\" with a non-empty \"headline\".")
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the page has an "
            f"<meta property=\"og:type\" content=\"article\"> tag.")


# ─── 3. SEO: TVSeries on /watch/<slug> + PodcastSeries on /podcast/<slug> (50)

WATCH_SLUGS = ['30-for-30-bad-boys', '30-for-30-bo-knows',
               '30-for-30-catholics-vs-convicts',
               '30-for-30-june-17th-1994', '30-for-30-oj-made-in-america']
PODCAST_SLUGS = ['beyond-the-boxscore', 'pelton-hoop-collective',
                 'inside-the-crease', 'on-the-pine', 'total-yards',
                 'soccer-fix', 'cfb-insider-show', 'cbb-today',
                 'track-and-trade', 'court-side-with-doris',
                 'schefty-pod', 'bracket-watch-daily',
                 'premier-league-daily-r6', 'pga-tour-daily',
                 'tennis-beat', 'fantasy-football-locker',
                 'champions-league-now', 'around-hockey',
                 'around-college-football', 'nfl-insider-live']

for slug in WATCH_SLUGS:
    new_tasks.append(
        f"On ESPN /watch/{slug}, view source and confirm "
        f"@type \"TVSeries\" appears in a JSON-LD block.")
    new_tasks.append(
        f"On ESPN /watch/{slug}, locate the og:title meta tag and report "
        f"its content attribute.")
for slug in PODCAST_SLUGS:
    new_tasks.append(
        f"On ESPN /podcast/{slug}, view source and confirm "
        f"@type \"PodcastSeries\" appears in a JSON-LD block.")


# ─── 4. robots.txt + sitemap.xml + sitemap entries (45) ──────────────────────

new_tasks.append("On ESPN, fetch /robots.txt and confirm 'Sitemap: /sitemap.xml' appears.")
new_tasks.append("On ESPN /robots.txt, confirm 'Disallow: /account' appears in the rules.")
new_tasks.append("On ESPN /robots.txt, confirm '/api/' is disallowed.")
new_tasks.append("On ESPN, fetch /sitemap.xml and confirm the root '<urlset' tag is present with the standard sitemap namespace.")
new_tasks.append("On ESPN /sitemap.xml, count <url> entries and confirm there are at least 500.")
new_tasks.append("On ESPN /sitemap.xml, confirm /espn-deportes/ is listed.")
new_tasks.append("On ESPN /sitemap.xml, confirm at least one /article/r7-nba- URL is present.")
new_tasks.append("On ESPN /sitemap.xml, confirm a /game/ URL appears with a <lastmod> child element.")
new_tasks.append("On ESPN /sitemap.xml, confirm /podcast/beyond-the-boxscore is listed.")
new_tasks.append("On ESPN /sitemap.xml, confirm /rss/nba.xml appears in a <loc> entry.")

for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer', 'ncaaf', 'ncaam']:
    new_tasks.append(
        f"On ESPN /sitemap.xml, confirm /{sp}/scoreboard is present in a <loc> entry.")
    new_tasks.append(
        f"On ESPN /sitemap.xml, confirm /{sp}/standings is present in a <loc> entry.")
    new_tasks.append(
        f"On ESPN /sitemap.xml, confirm /{sp}/news is listed.")
    new_tasks.append(
        f"On ESPN /sitemap.xml, confirm /rss/{sp}.xml is present.")


# ─── 5. RSS feed by sport (35) ───────────────────────────────────────────────

for sp in SPORTS_FOR_RSS:
    new_tasks.append(
        f"On ESPN /rss/{sp}.xml, confirm the response begins with "
        f"'<?xml' and contains a <channel> element.")
    new_tasks.append(
        f"On ESPN /rss/{sp}.xml, confirm at least one <item> entry "
        f"contains a <link> pointing to an /article/ path.")
new_tasks.append("On ESPN, browse to /rss/nba.xml and report the value of the <channel><title> element.")
new_tasks.append("On ESPN, browse to /rss/soccer.xml and report the number of <item> entries listed in the channel.")


# ─── 6. ESPN-Deportes locale + locale switcher (50) ──────────────────────────

new_tasks.append("On ESPN /, locate the EN | ES locale switcher in the global header and confirm both links are present.")
new_tasks.append("On ESPN /, click the 'ES' link in the locale switcher and confirm you land on /espn-deportes/.")
new_tasks.append("On ESPN /espn-deportes/, confirm the page <html> lang or the main container lang attribute is 'es'.")
new_tasks.append("On ESPN /espn-deportes/, locate the 'View this site in English' link and report its href.")
new_tasks.append("On ESPN /espn-deportes/, confirm the page title contains 'Deportes' or 'Noticias'.")
new_tasks.append("On ESPN /espn-deportes/nba, confirm at least one Spanish article link (slug prefix 'es-r7-') is listed.")
new_tasks.append("On ESPN /espn-deportes/nfl, confirm the section header for NFL appears in Spanish.")
new_tasks.append("On ESPN /espn-deportes/mlb, click the first Spanish article and confirm its content body contains accented characters (e.g., á, é, ñ).")
new_tasks.append("On ESPN /espn-deportes/soccer, confirm Real Madrid or Barcelona appears in at least one article title.")
new_tasks.append("On ESPN /deportes/ (alias), confirm the page loads and shows Spanish article links.")
new_tasks.append("On ESPN /deportes/nba (alias), confirm the page renders identical content to /espn-deportes/nba.")

for tpl in R7_ES_TEMPLATES:
    for team in ['boston-celtics', 'los-angeles-lakers',
                 'kansas-city-chiefs', 'new-york-yankees',
                 'real-madrid', 'barcelona']:
        slug = f'es-r7-nba-{team}-{tpl}-00' if 'team' not in team else None
        # Better: split by likely sport
        if team in ('boston-celtics', 'los-angeles-lakers'):
            sp = 'nba'
        elif team == 'kansas-city-chiefs':
            sp = 'nfl'
        elif team == 'new-york-yankees':
            sp = 'mlb'
        else:
            sp = 'soccer'
        slug = f'es-r7-{sp}-{team}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{slug}, confirm the article author is "
            f"'ESPN Deportes' and the language meta tag is Spanish.")

new_tasks.append("On ESPN /article/es-r7-nba-boston-celtics-analytics-edge-00, view source and confirm an <meta property=\"og:locale\" content=\"es_ES\"> tag is present.")
new_tasks.append("On ESPN /article/es-r7-nba-boston-celtics-analytics-edge-00, confirm the JSON-LD inLanguage field is 'es'.")
new_tasks.append("On ESPN /article/es-r7-nba-boston-celtics-analytics-edge-00, confirm a hreflang=\"es\" alternate link is present in <head>.")


# ─── 7. Accessibility live region (35) ───────────────────────────────────────

new_tasks.append("On ESPN /, confirm there is an element with id 'a11y-live-region' and aria-live='polite'.")
new_tasks.append("On ESPN /, confirm the a11y live region element has aria-atomic='true'.")
new_tasks.append("On ESPN /, confirm the a11y live region has role='status'.")
new_tasks.append("On ESPN /, locate the data-r7-live attribute on the a11y live region and report its value.")
new_tasks.append("On ESPN /nba/scoreboard, confirm the live-toast container has aria-live='polite'.")
new_tasks.append("On ESPN /nba/scoreboard, confirm the live-toast container is keyboard-focusable (or marked aria-atomic).")
new_tasks.append("On ESPN /nfl/scoreboard, confirm an aria-live region exists for score updates.")

# Broader a11y sweep for each sport
for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    new_tasks.append(
        f"On ESPN /{sp}/live, confirm the page has at least one aria-live region available for live announcements.")
    new_tasks.append(
        f"On ESPN /{sp}/live-scores, confirm the aria-live region exists in <body>.")
    new_tasks.append(
        f"On ESPN /{sp}/scoreboard, confirm the live-toast container has role='status'.")
    new_tasks.append(
        f"On ESPN /{sp}/scoreboard, confirm the page exposes aria-atomic='true' on the live region.")
    new_tasks.append(
        f"On ESPN /{sp}/scoreboard, confirm the sound-cue toggle is reachable via tab order.")


# ─── 8. Sound cue toggle (25) ────────────────────────────────────────────────

new_tasks.append("On ESPN /, confirm a checkbox with id 'sound-cue-toggle' exists in the footer area.")
new_tasks.append("On ESPN /, confirm the 'Sound cues' label appears next to the sound-cue checkbox.")
new_tasks.append("On ESPN /, confirm the sound-cue toggle is unchecked by default.")
new_tasks.append("On ESPN /, click the sound-cue toggle and confirm the label visually updates (color or weight changes).")
new_tasks.append("On ESPN /, confirm the sound-cue toggle has an aria-describedby attribute pointing to 'sound-cue-hint'.")
new_tasks.append("On ESPN /, confirm the sound-cue hint reads 'Play a chime when scores update.'")
new_tasks.append("On ESPN /nba, confirm the sound-cue toggle is present and shares state with the home page version.")
new_tasks.append("On ESPN /nfl/scoreboard, confirm the sound-cue toggle is positioned in the bottom-right area.")
new_tasks.append("On ESPN /, confirm the sound-cue toggle wrapper has role='region' for accessibility.")
new_tasks.append("On ESPN /, confirm the sound-cue checkbox has data-default='off' as the initial state hint.")
new_tasks.append("On ESPN /, locate the sound-cue toggle then confirm clicking it triggers a visual change (a music-note glyph appears next to the label).")
new_tasks.append("On ESPN /, confirm the sound-cue toggle stays visible while scrolling the homepage.")
new_tasks.append("On ESPN /game/100, confirm the sound-cue toggle is present so users can opt in to score chimes.")
new_tasks.append("On ESPN /podcast/beyond-the-boxscore, confirm the sound-cue toggle is reachable from the page footer area.")
new_tasks.append("On ESPN /search, confirm the sound-cue toggle remains present and accessible.")
new_tasks.append("On ESPN /espn-deportes/, confirm the sound-cue toggle remains present in the Spanish-locale page.")
new_tasks.append("On ESPN /, after enabling the sound-cue toggle once, navigate to /nba and confirm the toggle state can be checked or unchecked again.")
new_tasks.append("On ESPN /, confirm the sound-cue toggle and the a11y live region coexist without overlap.")
new_tasks.append("On ESPN /, confirm the sound-cue toggle label is wrapped in a <label> element (so screen readers read it).")
new_tasks.append("On ESPN /, confirm the sound-cue toggle has a visible focus indicator when tabbed to.")


# ─── 9. Multi-step chains using R7 data (60) ─────────────────────────────────

for team in R7_NBA_TEAMS[:8]:
    slug = team.lower().replace(' ', '-')
    for tpl in R7_TEMPLATES[:3]:
        new_tasks.append(
            f"On ESPN, start at /, navigate to /nba, open the {team} team "
            f"home, then open the related article /article/r7-nba-{slug}-{tpl}-00, "
            f"confirm the SportsEvent / NewsArticle JSON-LD is present, "
            f"and report the article's author.")

for team in R7_NFL_TEAMS[:5]:
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /, navigate to /nfl, open the {team} team page, then "
        f"the schedule, click the most recent finished game, confirm the "
        f"SportsEvent JSON-LD block contains the venue, and report it.")

for team in R7_MLB_TEAMS[:4]:
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /, navigate to /mlb, open the {team} team page, click "
        f"into the schedule, open the most recent finished game, then "
        f"open the play-by-play, and report the home/away score from the "
        f"recap header.")

for team in R7_SOCCER_CLUBS[:6]:
    slug = team.lower().replace(' ', '-')
    new_tasks.append(
        f"On ESPN /, switch language to Spanish via the locale switcher, "
        f"open /espn-deportes/soccer, click any {team} article, confirm "
        f"the article author is 'ESPN Deportes' and report the title.")

new_tasks.append("On ESPN /, open /robots.txt, confirm the Sitemap entry, then visit /sitemap.xml and confirm /podcast/total-yards is listed.")
new_tasks.append("On ESPN /, open /espn-deportes/, click into a /article/es-r7- article, confirm hreflang='es' alternate link exists, then return to / and confirm locale switcher shows EN as active.")
new_tasks.append("On ESPN /, open /rss/nba.xml, copy an article link from an <item> entry, then visit that article and confirm a NewsArticle JSON-LD block is present.")


# ─── 10. R7b longform articles & coverage (50) ───────────────────────────────

for tpl in R7B_TEMPLATES:
    for team in ['boston-celtics', 'los-angeles-lakers',
                 'kansas-city-chiefs', 'new-york-yankees',
                 'boston-bruins', 'real-madrid']:
        if team in ('boston-celtics', 'los-angeles-lakers'):
            sp = 'nba'
        elif team == 'kansas-city-chiefs':
            sp = 'nfl'
        elif team == 'new-york-yankees':
            sp = 'mlb'
        elif team == 'boston-bruins':
            sp = 'nhl'
        else:
            sp = 'soccer'
        slug = f'r7b-{sp}-{team}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{slug}, confirm the article body loads and "
            f"the tag chips appear at the bottom.")


# ─── 11. R7 new games + betting coverage (40) ────────────────────────────────

for gid in range(5100, 5300, 12):
    new_tasks.append(
        f"On ESPN /game/{gid}, locate the recap text and confirm the "
        f"final score is mentioned.")
for gid in range(5500, 5700, 12):
    new_tasks.append(
        f"On ESPN /game/{gid}, confirm a SportsEvent JSON-LD block lists "
        f"the venue and at least one team in the competitor array.")
for gid in range(6000, 6300, 25):
    new_tasks.append(
        f"On ESPN /game/{gid}, click into the play-by-play view if "
        f"available and confirm the page header shows both team names.")


# ─── 12. R7 new parlays (15) ─────────────────────────────────────────────────

R7_PARLAY_SLUGS = ['r7-nba-mvp-trio', 'r7-nba-roy-double',
                   'r7-nfl-conference-treble', 'r7-mlb-cy-young-multi',
                   'r7-nhl-art-ross-multi', 'r7-soccer-ucl-final-double',
                   'r7-ncaaf-playoff-quartet', 'r7-ncaam-final-four',
                   'r7-nba-finals-rematch', 'r7-deportes-laliga-double',
                   'r7-mlb-postseason-trio', 'r7-nfl-super-bowl-mvp',
                   'r7-nhl-stanley-cup-double', 'r7-nba-three-team-overs',
                   'r7-cross-sport-saturday']
for slug in R7_PARLAY_SLUGS:
    new_tasks.append(
        f"On ESPN /bet/parlay-builder, locate the parlay '{slug}' and "
        f"report its american odds.")


# ─── 13. Index / hot-path tasks (15) ─────────────────────────────────────────

new_tasks.append("On ESPN /nba/scoreboard, confirm games filter by status='final' and load quickly (within reasonable time).")
new_tasks.append("On ESPN /nfl/standings, confirm the standings table renders without empty placeholder rows.")
new_tasks.append("On ESPN /mlb/scoreboard, confirm the upcoming-games widget shows only future-dated games.")
new_tasks.append("On ESPN /nhl/scoreboard, confirm past-games sort is most-recent first.")
new_tasks.append("On ESPN /team/nba/boston-celtics/schedule, confirm the schedule lists games chronologically.")
new_tasks.append("On ESPN /team/nfl/kansas-city-chiefs/schedule, confirm both home and away games are listed.")
new_tasks.append("On ESPN /team/mlb/new-york-yankees/schedule, confirm at least 20 games are listed.")
new_tasks.append("On ESPN /team/nba/los-angeles-lakers, confirm the team home page loads and displays a recent results section.")
new_tasks.append("On ESPN /team/soccer/real-madrid, confirm the team page loads cleanly with no broken images.")
new_tasks.append("On ESPN /nba/teams, confirm all 30 NBA teams are listed in the grid.")
new_tasks.append("On ESPN /nfl/teams, confirm all 32 NFL teams are listed.")
new_tasks.append("On ESPN /scores, confirm scores from multiple sports are aggregated on one page.")
new_tasks.append("On ESPN /nba/odds, confirm at least one game listing shows odds from multiple sportsbooks.")
new_tasks.append("On ESPN /mlb/odds, confirm spread, total, and moneyline columns are visible.")
new_tasks.append("On ESPN /nfl/odds, confirm a 'sportsbook' column lists at least ESPN BET, DraftKings, FanDuel.")


# ─── 14. Filler for newly added games (20) ───────────────────────────────────

for gid in range(6500, 6900, 22):
    new_tasks.append(
        f"On ESPN /game/{gid}, confirm the page renders the date display "
        f"and venue information.")


# ─── 15. R7 articles broader coverage (200) ──────────────────────────────────

for tpl in R7_TEMPLATES:
    for team in R7_NBA_TEAMS:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r7-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the article title mentions "
            f"'{team}' and the byline shows 'ESPN Staff'.")

for tpl in R7_TEMPLATES[:5]:
    for team in R7_NFL_TEAMS:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r7-nfl-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm a NewsArticle JSON-LD block "
            f"declares datePublished and report the value.")

# Spanish broad coverage
for tpl in R7_ES_TEMPLATES:
    for team in R7_NBA_TEAMS[:10]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'es-r7-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the page lang or content "
            f"contains Spanish-language phrasing.")
        new_tasks.append(
            f"On ESPN /espn-deportes/nba, confirm the article '{a}' is "
            f"listed in the NBA section.")


# ─── 16. R7b articles coverage (35) ──────────────────────────────────────────

for tpl in R7B_TEMPLATES:
    for team in R7_NBA_TEAMS[:5]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r7b-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /article/{a}, confirm the body loads and the "
            f"article has at least one tag chip rendered.")


# ─── 17. R7 betting/odds coverage (40) ───────────────────────────────────────

for gid in range(5100, 5300, 10):
    new_tasks.append(
        f"On ESPN /nba/odds, locate the odds row for game {gid} and "
        f"confirm at least one sportsbook is listed.")
for gid in range(5500, 5700, 10):
    new_tasks.append(
        f"On ESPN /mlb/odds, confirm the odds for game {gid} show "
        f"over/under columns.")
for gid in range(6300, 6500, 15):
    new_tasks.append(
        f"On ESPN /nfl/odds, confirm spread and moneyline columns "
        f"are populated for game {gid}.")


# ─── 18. RSS deep checks (15) ────────────────────────────────────────────────

for sp in ['nba', 'nfl', 'mlb', 'nhl', 'soccer']:
    new_tasks.append(
        f"On ESPN /rss/{sp}.xml, confirm at least one <pubDate> entry "
        f"exists in the items.")
    new_tasks.append(
        f"On ESPN /rss/{sp}.xml, confirm the channel <description> "
        f"matches the channel <title>.")
new_tasks.append("On ESPN /rss/fantasy.xml, confirm the channel renders even if items may be empty.")
new_tasks.append("On ESPN /rss/golf.xml, confirm the channel header is present.")
new_tasks.append("On ESPN /rss/tennis.xml, confirm the response is application/rss+xml content type.")


# ─── 19. Multi-step SEO + locale workflows (40) ──────────────────────────────

for tpl in R7_TEMPLATES[:4]:
    for team in R7_NBA_TEAMS[:5]:
        slug = team.lower().replace(' ', '-').replace('.', '')
        a = f'r7-nba-{slug}-{tpl}-00'
        new_tasks.append(
            f"On ESPN /, navigate to /nba, open the {team} team page, "
            f"open the related news section, find /article/{a}, confirm "
            f"the NewsArticle JSON-LD is present.")

new_tasks.append("On ESPN /, open /sitemap.xml, pick one /game/ entry, navigate to that game page, then confirm the SportsEvent JSON-LD references the venue.")
new_tasks.append("On ESPN /, open the ES locale switcher, navigate to /espn-deportes/soccer, click a Real Madrid article, then confirm the JSON-LD inLanguage is 'es'.")
new_tasks.append("On ESPN /, fetch /robots.txt, follow the Sitemap entry, locate /podcast/total-yards in sitemap.xml, navigate to that podcast page and confirm PodcastSeries JSON-LD is present.")
new_tasks.append("On ESPN /, navigate to /nba/scoreboard, locate the a11y live region, enable the sound-cue toggle in the footer, return to /, confirm both controls still render.")
new_tasks.append("On ESPN /, open /rss/nfl.xml, parse one <link> from an <item>, navigate to that article, then confirm the article author is shown.")


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
print(f'R7 tasks appended: +{len(new_tasks)} (total now {final})')
