"""Generate GUI deepen tasks for bbc_news/tasks.jsonl.

Produces ≥30 GUI-style natural-language tasks per new visual page (27+
templates), all answerable by reading the rendered HTML. No API/JSON
phrasing; the agent should describe behaviour like a human reading bbc.com.

Run:
    .venv/bin/python3 sites/bbc_news/_data/generate_gui_deepen_tasks.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))
from gui_deepen import (  # noqa: E402
    SPORTS, UK_CITIES, WORLD_CITIES, IPLAYER_CATEGORIES, TV_CHANNELS,
    PODCASTS, LIVE_STATIONS, NEWS_TOPICS, NEWS_PICTURES_EVENTS,
    NEWS_EXPLAINERS, NEWS_LONGFORM, PROGRAMMES, BITESIZE_SUBJECTS,
    MARKET_INDICES, COMPANIES,
    build_sport_hub, build_sport_scoreboard, build_sport_standings,
    build_sport_team, build_sport_fixtures, build_sport_results,
    build_sport_live_blog, build_weather_forecast, build_weather_world,
    build_weather_uk, build_iplayer_episode, build_iplayer_category,
    build_iplayer_schedule, build_sounds_podcast, build_sounds_live,
    build_news_pictures, build_news_explainer, build_news_longform,
    build_programme, build_bitesize, build_region, build_market,
    build_company, build_news_topic, GUI_REFERENCE_DATE,
)

WEB_NAME = "BBC News"
WEB_URL = "http://localhost:40004/"
UPSTREAM = "https://www.bbc.com/news/"
TAG = "[gui-deepen-v1]"
START_ID = 7055


def mk(idx, ques, page_key):
    return {
        "web_name": WEB_NAME,
        "id": f"{WEB_NAME}--gui_{page_key}_{idx:03d}",
        "ques": ques,
        "web": WEB_URL,
        "upstream_url": UPSTREAM,
        "tags": [page_key, TAG],
    }


def gen_sport_hub_tasks():
    out = []
    sport_keys_label = {s[0]: s[1] for s in SPORTS}
    idx_per = {s[0]: 0 for s in SPORTS}
    for sport_key, sport_label, _ in SPORTS:
        d = build_sport_hub(sport_key)
        page_key = f"sport_{sport_key.replace('-', '_')}_hub"
        templates = [
            f"On BBC Sport, open the {sport_label} hub at /sport/{sport_key}/hub and report the league label shown.",
            f"Visit the {sport_label} hub on BBC Sport, then report the first headline in the top stories list.",
            f"On the {sport_label} hub, report which item appears in slot 2 of the top stories.",
            f"Open BBC Sport {sport_label} and find the headline shown in slot 3.",
            f"On the {sport_label} BBC Sport hub, what is the next big fixture shown?",
            f"Open the {sport_label} hub and report the kickoff time of the next big fixture.",
            f"On BBC Sport {sport_label}, who is listed as the top scorer/leader?",
            f"On the {sport_label} hub, how many goals/points does the top scorer have?",
            f"Open the {sport_label} BBC Sport hub and count how many teams or players appear in the listing.",
            f"On BBC Sport {sport_label}, which team appears first in the alphabetical listing?",
            f"On the {sport_label} hub, click the Tables/Standings link and confirm where it leads.",
            f"On BBC Sport {sport_label}, click the Scores & Fixtures tab and report the page title.",
            f"On the {sport_label} hub, click the Fixtures link and confirm a fixtures table appears.",
            f"On the {sport_label} hub, click the Results link and confirm a results table appears.",
            f"Open the {sport_label} hub and report the snapshot date shown in the subtitle.",
            f"On BBC Sport {sport_label}, report the second top-story headline.",
            f"On BBC Sport {sport_label}, report the fourth top-story headline.",
            f"On BBC Sport {sport_label}, report the fifth top-story headline.",
            f"On the {sport_label} hub, report how many minutes ago the first headline was filed.",
            f"On the {sport_label} hub, report how many minutes ago the third headline was filed.",
            f"On BBC Sport {sport_label}, report which team appears in position 5 of the team grid.",
            f"On the {sport_label} BBC Sport hub, what is the last team/competitor in the grid?",
            f"Open the {sport_label} hub and check whether the hero banner shows the BBC Sport - {sport_label} title.",
            f"On the {sport_label} hub, click on the first team/player and confirm the team profile loads.",
            f"On BBC Sport {sport_label}, identify the league label and report it back verbatim.",
            f"On the {sport_label} hub, count the navigation tabs shown.",
            f"On BBC Sport {sport_label}, find any item that mentions a final/championship.",
            f"On the {sport_label} hub, find an item that mentions a player/team retiring or transferring.",
            f"On the {sport_label} hub, identify the next big fixture and which sport it belongs to.",
            f"On BBC Sport {sport_label}, scroll to the bottom and confirm the team/competitor grid is visible.",
            f"Open the {sport_label} BBC Sport hub at /sport/{sport_key}/hub and report the top scorer plus their stat.",
        ]
        for t in templates:
            idx_per[sport_key] += 1
            out.append(mk(idx_per[sport_key], t, page_key))
    return out


def gen_sport_scoreboard_tasks():
    out = []
    date_str = GUI_REFERENCE_DATE.strftime("%Y-%m-%d")
    page_key = "sport_scoreboard"
    sports_to_use = ["football", "cricket", "rugby-union"]
    i = 0
    for sport in sports_to_use:
        d = build_sport_scoreboard(sport, date_str)
        templates = [
            f"On BBC Sport, open the {sport} scoreboard for {date_str} and report how many matches are listed.",
            f"On the {sport} scoreboard for {date_str}, what is the score of the first match?",
            f"On the {sport} scoreboard for {date_str}, who is the home team in the second match?",
            f"On the {sport} scoreboard for {date_str}, what is the status of the third match?",
            f"On BBC Sport scoreboard ({sport}, {date_str}), report the kickoff time of the first match.",
            f"On the {sport} scoreboard, which venue hosts the first match?",
            f"On the {sport} scoreboard for {date_str}, find any match listed as Postponed.",
            f"On the {sport} scoreboard, report the away team in the fourth match.",
            f"On BBC Sport {sport} scoreboard ({date_str}), find a match currently labelled Live and report its score.",
            f"On the {sport} scoreboard, report the competition label shown.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sport_standings_tasks():
    out = []
    page_key = "sport_standings"
    leagues = [
        ("football", "premier-league", "Premier League"),
        ("football", "la-liga", "La Liga"),
        ("cricket", "the-hundred", "The Hundred"),
        ("rugby-union", "six-nations", "Six Nations"),
    ]
    i = 0
    for sport, league_slug, label in leagues:
        d = build_sport_standings(sport, league_slug)
        rows = d["rows"]
        templates = [
            f"On BBC Sport, open the {label} standings and report the team in 1st place.",
            f"On the {label} table, which team is in 4th place?",
            f"On the {label} standings, how many points does the top team have?",
            f"On BBC Sport {label} table, what is the goal difference of the team in 2nd place?",
            f"On the {label} standings, which team is in last place?",
            f"On the {label} table, report the wins/drawn/lost record of the 1st place team.",
            f"On BBC Sport {label} table, find the team in 3rd place.",
            f"On the {label} standings, report the season label shown.",
            f"On the {label} table, count how many teams are listed in the standings.",
            f"On the {label} standings, report the points of the team in 5th place.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sport_team_tasks():
    out = []
    page_key = "sport_team"
    teams = ["arsenal", "manchester-city", "liverpool", "chelsea", "tottenham",
             "newcastle", "leicester-tigers", "saracens", "england", "australia"]
    i = 0
    for team_id in teams:
        templates = [
            f"On BBC Sport, open the profile page for {team_id.replace('-', ' ').title()} and report the manager name.",
            f"On the {team_id.replace('-', ' ').title()} profile, what is the home venue?",
            f"On {team_id.replace('-', ' ').title()}'s profile, what is the stadium capacity?",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sport_fixtures_tasks():
    out = []
    page_key = "sport_fixtures"
    i = 0
    for sport in ["football", "cricket", "rugby-union", "tennis", "formula1",
                  "american-football", "boxing", "olympics"]:
        templates = [
            f"On BBC Sport {sport} fixtures, how many fixtures are listed?",
            f"On the {sport} fixtures page, report the home team in the first fixture.",
            f"On the {sport} fixtures page, report the kickoff time of the second fixture.",
            f"On BBC Sport {sport} fixtures, report the competition label of the first fixture.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sport_results_tasks():
    out = []
    page_key = "sport_results"
    i = 0
    for sport in ["football", "cricket", "rugby-union", "tennis", "formula1",
                  "american-football", "boxing", "olympics"]:
        templates = [
            f"On BBC Sport {sport} results, how many results are shown?",
            f"On the {sport} results page, report the score of the first result.",
            f"On the {sport} results page, report the date of the most recent result.",
            f"On BBC Sport {sport} results, find a result where the home team won.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sport_live_blog_tasks():
    out = []
    page_key = "sport_live_blog"
    pairs = [("football", "match-001"), ("football", "match-cup-final"),
             ("cricket", "test-1st-day"), ("rugby-union", "premiership-r10"),
             ("tennis", "wimbledon-sf"), ("formula1", "monaco-gp"),
             ("boxing", "title-fight"), ("american-football", "super-bowl")]
    i = 0
    for sport, ev in pairs:
        templates = [
            f"On BBC Sport, open the live blog for {sport} event {ev} and report the current minute.",
            f"On the live blog for {sport} {ev}, report the current score.",
            f"On the {sport} live blog ({ev}), report the most recent update's event type.",
            f"On the {sport} live blog ({ev}), how many updates are listed?",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_weather_forecast_tasks():
    out = []
    page_key = "weather_forecast"
    i = 0
    for slug, name, _, _, _ in UK_CITIES[:8]:
        templates = [
            f"On BBC Weather, open the {name} forecast and report the current temperature in Celsius.",
            f"On the {name} weather page, what is the current condition shown?",
            f"On {name} BBC Weather, report the sunrise and sunset times.",
            f"On BBC Weather {name}, report the UV index.",
            f"On {name} weather, what is the high temperature for tomorrow (Day 2 of the 7-day forecast)?",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    for slug, name, country, _, _ in WORLD_CITIES[:6]:
        templates = [
            f"On BBC Weather, open the {name} ({country}) forecast and report the current temperature.",
            f"On {name} BBC Weather, report the wind speed and direction.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_weather_world_tasks():
    out = []
    page_key = "weather_world"
    i = 0
    base = [
        "On BBC Weather, open /weather/world and report how many cities are listed in the table.",
        "On the world weather page, report the temperature shown for New York.",
        "On the world weather page, report the temperature shown for Tokyo.",
        "On the world weather page, find the city with the highest temperature.",
        "On BBC Weather world, report the country of Dubai as shown.",
        "On the world weather page, report the condition shown for Singapore.",
        "On BBC Weather world, report the humidity for Sydney.",
        "On the world weather page, what is the wind speed for Berlin?",
        "On the world weather page, report the temperature in Rome.",
        "On BBC Weather world, click Tokyo and confirm the Tokyo forecast page loads.",
        "On the world weather page, count how many cities have temperature above 20 degrees.",
        "On the world weather page, find the city in India and report its temperature.",
    ]
    extras = []
    for slug, name, country, _, _ in WORLD_CITIES:
        extras.append(f"On the world weather page, click {name} and confirm the {name} forecast page loads.")
        extras.append(f"On BBC Weather world, find {name} in the table and report its temperature.")
    for t in base + extras:
        i += 1
        out.append(mk(i, t, page_key))
    return out


def gen_weather_uk_tasks():
    out = []
    page_key = "weather_uk"
    i = 0
    base = [
        "On BBC Weather, open /weather/uk and report how many UK cities are listed.",
        "On the UK weather summary, report the temperature for London.",
        "On the UK weather page, report the temperature for Manchester.",
        "On UK weather summary, find the city with the highest temperature.",
        "On UK weather, report the rain chance for Edinburgh.",
        "On the UK weather summary, report the condition for Cardiff.",
        "On UK weather, find a city with rain chance above 50%.",
        "On UK weather, report the wind speed for Belfast.",
        "On the UK weather summary, report the temperature in Bristol.",
        "On UK weather, click Glasgow and confirm the Glasgow forecast loads.",
        "On UK weather, count how many cities have temperature above 15 degrees.",
        "On the UK weather summary, report the temperature for Newcastle.",
    ]
    extras = []
    for slug, name, _, _, _ in UK_CITIES:
        extras.append(f"On the UK weather summary, click {name} and confirm the {name} forecast page loads.")
        extras.append(f"On BBC UK weather, find {name} in the table and report its wind speed.")
    for t in base + extras:
        i += 1
        out.append(mk(i, t, page_key))
    return out


def gen_iplayer_episode_tasks():
    out = []
    page_key = "iplayer_episode"
    i = 0
    shows = [(s[0], s[1]) for _, _, lst in IPLAYER_CATEGORIES for s in lst][:12]
    for sid, name in shows:
        templates = [
            f"On BBC iPlayer, open the show page for '{name}' and report the lead actor.",
            f"On iPlayer for '{name}', how many series are listed?",
            f"On '{name}' iPlayer page, report the audience rating shown.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_iplayer_category_tasks():
    out = []
    page_key = "iplayer_category"
    i = 0
    for cat_slug, cat_label, shows in IPLAYER_CATEGORIES:
        templates = [
            f"On BBC iPlayer category {cat_label}, report how many shows are listed.",
            f"On iPlayer {cat_label}, report the first show in the grid.",
            f"On iPlayer {cat_label}, click on a show and confirm the show page loads.",
            f"On iPlayer {cat_label}, find a show starring a known BBC presenter.",
            f"On iPlayer {cat_label}, report the lead actor of the second show.",
            f"On iPlayer {cat_label}, count how many series the first show has.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_iplayer_schedule_tasks():
    out = []
    page_key = "iplayer_schedule"
    date_str = GUI_REFERENCE_DATE.strftime("%Y-%m-%d")
    i = 0
    for ch_slug, ch_label in TV_CHANNELS:
        templates = [
            f"On BBC iPlayer schedule for {ch_label} on {date_str}, report the first programme shown.",
            f"On {ch_label} schedule ({date_str}), what is on at 19:30?",
            f"On {ch_label} schedule ({date_str}), how many time slots are listed?",
            f"On {ch_label} schedule, report the synopsis of the 21:00 programme.",
            f"On {ch_label} schedule for {date_str}, what is the last programme of the day?",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sounds_podcast_tasks():
    out = []
    page_key = "sounds_podcast"
    i = 0
    for slug, name, host, _, _, _ in PODCASTS:
        templates = [
            f"On BBC Sounds podcast '{name}', report the host name.",
            f"On the '{name}' podcast page, report the average rating.",
            f"On '{name}', report the publication date of the most recent episode.",
            f"On the '{name}' page, click Subscribe and confirm the subscribe action.",
            f"On '{name}' podcast, count how many episodes are listed.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_sounds_live_tasks():
    out = []
    page_key = "sounds_live"
    i = 0
    for slug, name, _ in LIVE_STATIONS:
        templates = [
            f"On BBC Sounds live station {name}, report the current DJ on air.",
            f"On {name} live, report the track currently playing and its artist.",
            f"On {name} live, report the listener count.",
            f"On {name} live, report the next show in the 'Coming up' list.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_news_pictures_tasks():
    out = []
    page_key = "news_pictures"
    i = 0
    for slug, title, location in NEWS_PICTURES_EVENTS:
        templates = [
            f"On BBC News in pictures '{title}', how many photos are in the gallery?",
            f"On in_pictures '{title}', report the event location shown.",
            f"On the '{title}' gallery, report the publication date.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_news_explainer_tasks():
    out = []
    page_key = "news_explainer"
    i = 0
    for slug, title in NEWS_EXPLAINERS:
        templates = [
            f"On BBC News explainer '{title}', how many sections does the article have?",
            f"On the '{title}' explainer, report the reading time in minutes.",
            f"On '{title}' explainer, report the author/team listed.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_news_longform_tasks():
    out = []
    page_key = "news_longform"
    i = 0
    for slug, title in NEWS_LONGFORM:
        templates = [
            f"On BBC News longform '{title}', how many chapters does it have?",
            f"On the '{title}' longform, report the total word count.",
            f"On '{title}' longform, report the author shown.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_programmes_tasks():
    out = []
    page_key = "programmes"
    i = 0
    for pid, name, channel, genre, year, series, dur in PROGRAMMES:
        templates = [
            f"On BBC Programmes /programmes/{pid}, report the programme name.",
            f"On the {name} programmes page, what year did it first air?",
            f"On {name} ({pid}), how many series are listed?",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_bitesize_tasks():
    out = []
    page_key = "bitesize_subject"
    i = 0
    for slug, label, levels in BITESIZE_SUBJECTS:
        templates = [
            f"On BBC Bitesize, open the {label} subject page and report how many topics are listed.",
            f"On Bitesize {label}, report the first topic shown.",
            f"On Bitesize {label}, list the exam boards shown.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_region_tasks():
    out = []
    i = 0
    region_label = {"cymru": "Cymru", "scotland": "Scotland",
                    "northernireland": "Northern Ireland", "wales": "Wales"}
    region_cap = {"cymru": "Cardiff", "scotland": "Edinburgh",
                  "northernireland": "Belfast", "wales": "Cardiff"}
    for slug in ["cymru", "scotland", "northernireland", "wales"]:
        page_key = f"region_{slug}"
        label = region_label[slug]
        cap = region_cap[slug]
        templates = [
            f"On BBC, open the {label} regional homepage at /{slug} and report the capital city shown.",
            f"On BBC {label}, report the first top-story headline shown on the page.",
            f"On BBC {label} ({slug}), count how many navigation sections are shown in the tabs.",
            f"On BBC {label}, find the second headline in the top-stories list and report it.",
            f"On BBC {label} homepage, report which section the first headline belongs to.",
            f"On BBC {label}, scroll to find a Sport or sport-related headline.",
            f"On BBC {label}, count how many headlines are shown in total.",
            f"On BBC {label}, report the third headline as shown.",
            f"On BBC {label}, report the fourth headline in the feed.",
            f"On BBC {label}, report the fifth headline in the feed.",
            f"On BBC {label}, report the section label attached to the second headline.",
            f"On BBC {label}, report the section label attached to the third headline.",
            f"On BBC {label}, report how many minutes ago the first headline was filed.",
            f"On BBC {label}, report how many minutes ago the second headline was filed.",
            f"On BBC {label}, report how many minutes ago the third headline was filed.",
            f"On BBC {label}, look at the page header and confirm the capital is {cap}.",
            f"On BBC {label}, click the first navigation tab and confirm the in-page anchor jumps.",
            f"On BBC {label} homepage, find the sixth headline if present.",
            f"On BBC {label}, find a headline mentioning 'hospital' or 'health'.",
            f"On BBC {label}, find a headline mentioning 'cup' or 'team' (sport).",
            f"On BBC {label}, find a headline mentioning 'reforms' or 'announced'.",
            f"On BBC {label}, find a headline mentioning 'climate' or 'change'.",
            f"On BBC {label}, find a headline mentioning 'festival' or 'cultural'.",
            f"On BBC {label}, find a headline mentioning 'transport' or 'infrastructure'.",
            f"On BBC {label}, find a headline mentioning 'business' or 'award'.",
            f"On BBC {label}, find a headline mentioning 'first minister' or 'parliament'.",
            f"On BBC {label}, report the snapshot date shown in the subtitle.",
            f"On BBC {label}, report the order of sections shown in the navigation tabs.",
            f"On BBC {label}, click the third navigation tab and confirm where it jumps.",
            f"On BBC {label}, click the last navigation tab and confirm where it jumps.",
            f"On BBC {label}, confirm the page hero displays 'BBC {label}' or its localised form.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_market_tasks():
    out = []
    page_key = "business_market"
    i = 0
    for slug, name, exch, currency, _, _ in MARKET_INDICES:
        templates = [
            f"On BBC Business, open the {name} market page and report the current value.",
            f"On {name} ({slug}), report the change in points and percent today.",
            f"On {name} business page, report the 52-week high and 52-week low.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_company_tasks():
    out = []
    page_key = "business_company"
    i = 0
    for ticker, name, exch, currency, industry in COMPANIES:
        templates = [
            f"On BBC Business, open the company page for {name} ({ticker}) and report the current share price.",
            f"On {ticker} BBC Business page, report the CEO name and industry.",
            f"On {name} ({ticker}), report the market cap and P/E ratio.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def gen_topic_tasks():
    out = []
    page_key = "news_topic"
    i = 0
    for slug, label in NEWS_TOPICS:
        templates = [
            f"On BBC News topic '{label}', how many articles are listed?",
            f"On topic '{label}', report the follower count.",
            f"On '{label}' topic page, click Follow and confirm the action.",
        ]
        for t in templates:
            i += 1
            out.append(mk(i, t, page_key))
    return out


def main():
    all_tasks = []
    generators = [
        gen_sport_hub_tasks,           # 8 sports x 31 = 248
        gen_sport_scoreboard_tasks,    # 3 x 10 = 30
        gen_sport_standings_tasks,     # 4 x 10 = 40
        gen_sport_team_tasks,          # 10 x 3 = 30
        gen_sport_fixtures_tasks,      # 8 x 4 = 32
        gen_sport_results_tasks,       # 8 x 4 = 32
        gen_sport_live_blog_tasks,     # 8 x 4 = 32
        gen_weather_forecast_tasks,    # 8x5 + 6x2 = 52
        gen_weather_world_tasks,       # 12
        gen_weather_uk_tasks,          # 12
        gen_iplayer_episode_tasks,     # 12 x 3 = 36
        gen_iplayer_category_tasks,    # 5 x 6 = 30
        gen_iplayer_schedule_tasks,    # 6 x 5 = 30
        gen_sounds_podcast_tasks,      # 10 x 5 = 50
        gen_sounds_live_tasks,         # 8 x 4 = 32
        gen_news_pictures_tasks,       # 10 x 3 = 30
        gen_news_explainer_tasks,      # 10 x 3 = 30
        gen_news_longform_tasks,       # 10 x 3 = 30
        gen_programmes_tasks,          # 12 x 3 = 36
        gen_bitesize_tasks,            # 12 x 3 = 36
        gen_region_tasks,              # 4 x 8 = 32
        gen_market_tasks,              # 10 x 3 = 30
        gen_company_tasks,             # 14 x 3 = 42
        gen_topic_tasks,               # 12 x 3 = 36
    ]
    for g in generators:
        all_tasks.extend(g())

    # Re-number globally with START_ID, but keep per-page tagging in id.
    tasks_file = SITE / "tasks.jsonl"
    existing = tasks_file.read_text().splitlines() if tasks_file.exists() else []
    # Strip prior gui-deepen entries (in case rerun).
    existing = [ln for ln in existing if "[gui-deepen-v1]" not in ln]

    # Append new with global index starting at len(existing).
    global_next = START_ID
    new_lines = []
    for t in all_tasks:
        # Keep id stable: BBC News--gui_<page>_<NNN>.
        new_lines.append(json.dumps(t, ensure_ascii=False))
        global_next += 1

    out_text = "\n".join(existing + new_lines) + "\n"
    tasks_file.write_text(out_text)
    print(f"Wrote {len(new_lines)} new GUI deepen tasks "
          f"(prior count={len(existing)}, total now={len(existing) + len(new_lines)}).")
    # Sanity: groups
    by_page = {}
    for t in all_tasks:
        # page_key is the first tag.
        pk = t["tags"][0]
        by_page[pk] = by_page.get(pk, 0) + 1
    print(f"Per-page totals across {len(by_page)} pages:")
    for k, v in sorted(by_page.items()):
        print(f"  {k:35s} {v}")


if __name__ == "__main__":
    main()
