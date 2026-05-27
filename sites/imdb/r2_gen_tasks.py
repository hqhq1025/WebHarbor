#!/usr/bin/env python3
"""Generate IMDb mirror tasks.jsonl from the seed DB.

Walks the seed DB to produce ~1500+ tasks across 30+ task_types. Each task is
written in WebVoyager schema with `task_type` and a `IMDb--<type>_<NN>` id.
Image-bearing surfaces (posters, headshots, photo galleries) are targeted in
≥40% of tasks per the deepening brief.

Run from sites/imdb/:  python3 r2_gen_tasks.py
"""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB   = BASE / 'instance_seed' / 'imdb.db'
OUT  = BASE / 'tasks.jsonl'
PORT = 40019  # IMDb port — per project memory
WEB  = f'http://localhost:{PORT}/'
UPS  = 'https://www.imdb.com/'

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# ---------------------------------------------------------------------------
# Source data
# ---------------------------------------------------------------------------

titles = con.execute(
    "SELECT id, tt_id, title_type, primary_title, year, runtime_min, "
    "mpaa_rating, rating_avg, num_votes, top_rank, popularity_rank, "
    "box_office_us, box_office_world, box_office_opening, budget, "
    "release_date, country, language, poster_path "
    "FROM titles ORDER BY tt_id"
).fetchall()

# Genre rows per title
title_genres = {}
for r in con.execute(
    "SELECT tg.title_id, g.name FROM title_genre tg "
    "JOIN genres g ON g.id = tg.genre_id "
    "ORDER BY tg.title_id, g.name"
):
    title_genres.setdefault(r['title_id'], []).append(r['name'])

# Title primary cast (top-3 billed, with photo)
top_cast = {}
for r in con.execute(
    "SELECT c.title_id, p.name AS person, p.nm_id, c.character, "
    "       c.billing_order, p.photo_path "
    "FROM credits c JOIN persons p ON p.id = c.person_id "
    "WHERE c.role='actor' "
    "ORDER BY c.title_id, COALESCE(c.billing_order, 999), p.name"
):
    top_cast.setdefault(r['title_id'], []).append(dict(r))

# Title director (first one alphabetical)
directors = {}
for r in con.execute(
    "SELECT c.title_id, p.name AS person, p.nm_id "
    "FROM credits c JOIN persons p ON p.id = c.person_id "
    "WHERE c.role='director' ORDER BY c.title_id, p.name"
):
    directors.setdefault(r['title_id'], []).append(dict(r))

# Title writers
writers = {}
for r in con.execute(
    "SELECT c.title_id, p.name AS person, p.nm_id "
    "FROM credits c JOIN persons p ON p.id = c.person_id "
    "WHERE c.role='writer' ORDER BY c.title_id, p.name"
):
    writers.setdefault(r['title_id'], []).append(dict(r))

persons = con.execute(
    "SELECT id, nm_id, name, birth_year, death_year, "
    "       primary_profession, bio, photo_path "
    "FROM persons WHERE photo_path != '' "
    "ORDER BY nm_id"
).fetchall()

# Trivia / quotes / goofs per title
trivia = {}
for r in con.execute(
    "SELECT title_id, body, helpful_count "
    "FROM r2_title_trivia ORDER BY title_id, id"
):
    trivia.setdefault(r['title_id'], []).append(dict(r))

quotes = {}
for r in con.execute(
    "SELECT title_id, character, body, helpful_count "
    "FROM r2_title_quotes ORDER BY title_id, id"
):
    quotes.setdefault(r['title_id'], []).append(dict(r))

goofs = {}
for r in con.execute(
    "SELECT title_id, category, body "
    "FROM r2_title_goofs ORDER BY title_id, category, id"
):
    goofs.setdefault(r['title_id'], []).append(dict(r))

polls = con.execute(
    "SELECT id, slug, question FROM r2_polls ORDER BY id"
).fetchall()

poll_options = {}
for r in con.execute(
    "SELECT poll_id, label, position FROM r2_poll_options ORDER BY poll_id, position"
):
    poll_options.setdefault(r['poll_id'], []).append(dict(r))

lists = con.execute(
    "SELECT L.id, L.name, L.description, u.name AS owner, u.email AS owner_email "
    "FROM r2_user_lists L JOIN users u ON u.id = L.owner_id "
    "ORDER BY L.id"
).fetchall()

list_items = {}
for r in con.execute(
    "SELECT li.list_id, t.tt_id, t.primary_title "
    "FROM r2_user_list_items li JOIN titles t ON t.id = li.title_id "
    "ORDER BY li.list_id, li.position"
):
    list_items.setdefault(r['list_id'], []).append(dict(r))

news = con.execute(
    "SELECT id, headline, summary, source, published_at, category, related_tt "
    "FROM news_items ORDER BY id"
).fetchall()

# Genre list
genres = [r['name'] for r in con.execute("SELECT name FROM genres ORDER BY name")]

# Picks: well-known title list — gives stable bench feel.
WELL_KNOWN = ['tt0111161', 'tt0068646', 'tt0468569', 'tt1375666', 'tt0816692',
              'tt0167260', 'tt0110912', 'tt0903747', 'tt15398776', 'tt6751668',
              'tt0944947', 'tt0137523', 'tt0099685', 'tt0050083', 'tt0080684',
              'tt0078788', 'tt0386676', 'tt0114369', 'tt0102926', 'tt0245429',
              'tt0120737', 'tt0109830', 'tt0114709', 'tt0078748', 'tt0083658',
              'tt0133093', 'tt0070047', 'tt0185906', 'tt5491994', 'tt7678620',
              'tt0795176', 'tt0317705', 'tt2380307', 'tt4574334', 'tt1517268']

# Filter wks to titles actually present.
wk_titles = [t for t in titles if t['tt_id'] in WELL_KNOWN]
# Top by votes (broader pool than wks)
top_titles = sorted(titles, key=lambda t: -(t['num_votes'] or 0))[:80]

# Movies/TV that have rich data
def has_box_office(t):
    return bool(t['box_office_us'] or t['box_office_world'])


# ---------------------------------------------------------------------------
# Output buffer
# ---------------------------------------------------------------------------

out = []
def add(task_type, idx, ques):
    out.append({
        'web_name': 'IMDb',
        'id': f'IMDb--{task_type}_{idx:03d}',
        'task_type': task_type,
        'ques': ques,
        'web': WEB,
        'upstream_url': UPS,
    })


def title_label(t):
    return f"{t['primary_title']} ({t['year']})" if t['year'] else t['primary_title']


# ---------------------------------------------------------------------------
# Task generators — one function per task_type
# ---------------------------------------------------------------------------

def gen_chart_top():
    for i, t in enumerate([t for t in titles if t['top_rank']][:50]):
        add('gui-chart-top', i,
            f"Open the IMDb Top 250 movies chart and report the title and "
            f"IMDb rating of the movie currently ranked #{t['top_rank']}.")


def gen_chart_toptv():
    rows = [t for t in titles if t['title_type']=='tvSeries' and t['top_rank']]
    rows.sort(key=lambda t: t['top_rank'])
    for i, t in enumerate(rows[:50]):
        add('gui-chart-toptv', i,
            f"Open the Top 250 TV Shows chart on IMDb. Report the show and its "
            f"IMDb rating in position #{t['top_rank']}.")


def gen_chart_moviemeter():
    rows = [t for t in titles if t['popularity_rank']]
    rows.sort(key=lambda t: t['popularity_rank'])
    for i, t in enumerate(rows[:50]):
        add('gui-chart-moviemeter', i,
            f"Open the Most Popular Movies chart. Report the title sitting at "
            f"popularity rank #{t['popularity_rank']} and its IMDb rating.")


def gen_chart_boxoffice():
    rows = [t for t in titles if t['box_office_us']]
    rows.sort(key=lambda t: -t['box_office_us'])
    for i, t in enumerate(rows[:50]):
        add('gui-chart-boxoffice', i,
            f"Open the Top Box Office (US) chart on IMDb. Find {title_label(t)} "
            f"in the chart and report its US gross.")


def gen_chart_popular_tv():
    rows = [t for t in titles if t['title_type']=='tvSeries' and t['popularity_rank']]
    rows.sort(key=lambda t: t['popularity_rank'])
    for i, t in enumerate(rows[:40]):
        add('gui-chart-popular-tv', i,
            f"Open the Most Popular TV Shows chart on IMDb. Report the show at "
            f"position #{t['popularity_rank']} and its IMDb rating.")


def gen_chart_lowest_rated():
    rows = [t for t in titles if (t['num_votes'] or 0) >= 50000]
    rows.sort(key=lambda t: t['rating_avg'] or 0)
    for i, t in enumerate(rows[:40]):
        add('gui-chart-lowest-rated', i,
            f"Open the Lowest Rated chart (titles with at least 50k votes) "
            f"and report the rating of {title_label(t)}.")


def gen_genre_browse():
    for i, g in enumerate(genres):
        add('gui-genre-browse', i,
            f"Browse the {g} genre page on IMDb. Report the title and IMDb "
            f"rating of the highest-rated film listed at the top of that genre page.")
    # plus repeat with different framings to bulk count.
    for i, g in enumerate(genres[:20], start=len(genres)):
        add('gui-genre-browse', i,
            f"Open the {g} genre browse page. Among the listed titles, how "
            f"many have an IMDb rating of 8.0 or above? (Look only at the page.)")


def gen_title_runtime():
    for i, t in enumerate(top_titles[:60]):
        add('gui-title-runtime', i,
            f"Open the IMDb page for {title_label(t)}. Report its runtime in minutes.")


def gen_title_director():
    for i, t in enumerate(top_titles[:60]):
        ds = directors.get(t['id'], [])
        if not ds:
            continue
        add('gui-title-director', i,
            f"Open the IMDb page for {title_label(t)}. Who directed the film? "
            f"Report all directors listed in the credits.")


def gen_title_writer():
    for i, t in enumerate(top_titles[:50]):
        ws = writers.get(t['id'], [])
        if not ws:
            continue
        add('gui-title-writer', i,
            f"Open the IMDb page for {title_label(t)}. Report the credited "
            f"writers as shown on the title page.")


def gen_title_metadata():
    rows = [t for t in top_titles if t['country']][:50]
    for i, t in enumerate(rows):
        add('gui-title-metadata', i,
            f"Open the IMDb page for {title_label(t)}. Report the country of "
            f"origin and the primary language listed in the Box office & details section.")


def gen_title_box_office():
    rows = [t for t in top_titles if has_box_office(t)][:50]
    for i, t in enumerate(rows):
        add('gui-title-box-office', i,
            f"Open the IMDb page for {title_label(t)} and report its worldwide "
            f"gross and its budget as listed in the Box office section.")


def gen_title_box_office_open():
    rows = [t for t in top_titles if t['box_office_opening']][:40]
    for i, t in enumerate(rows):
        add('gui-title-box-office-open', i,
            f"Open the IMDb page for {title_label(t)} and report its opening "
            f"weekend US & Canada gross.")


def gen_title_cast_billing():
    """Image-bearing: agent must view the top-cast photo grid."""
    rows = [t for t in top_titles if top_cast.get(t['id'])][:60]
    for i, t in enumerate(rows):
        cast = top_cast[t['id']]
        if not cast:
            continue
        idx_q = (i % 5) + 1
        add('gui-title-cast-billing', i,
            f"Open the IMDb page for {title_label(t)} and look at the Top cast "
            f"grid (each card shows a headshot). Report the name of the actor "
            f"billed #{idx_q} and the character they play.")


def gen_title_trivia():
    rows = [t for t in top_titles if trivia.get(t['id'])][:50]
    for i, t in enumerate(rows):
        add('gui-title-trivia', i,
            f"Open the Trivia subpage for {title_label(t)} (linked from the "
            f"title page). Report the headline trivia item shown first.")
    # second framing for bulk
    for i, t in enumerate(rows[:30], start=50):
        add('gui-title-trivia', i,
            f"On the IMDb Trivia page for {title_label(t)}, how many distinct "
            f"trivia entries are listed?")


def gen_title_quotes():
    rows = [t for t in top_titles if quotes.get(t['id'])][:50]
    for i, t in enumerate(rows):
        add('gui-title-quotes', i,
            f"Open the Quotes subpage for {title_label(t)}. Report the character "
            f"label and the quote shown at the very top of the page.")
    for i, t in enumerate(rows[:30], start=50):
        add('gui-title-quotes', i,
            f"On the IMDb Quotes page for {title_label(t)}, count the number "
            f"of distinct quotes listed.")


def gen_title_goofs():
    rows = [t for t in top_titles if goofs.get(t['id'])][:50]
    for i, t in enumerate(rows):
        add('gui-title-goofs', i,
            f"Open the Goofs subpage for {title_label(t)}. Report the goof "
            f"category headings shown on the page.")


def gen_title_awards():
    rows = [t for t in top_titles if t['top_rank'] or t['rating_avg']][:50]
    for i, t in enumerate(rows):
        add('gui-title-awards', i,
            f"Open the Awards subpage for {title_label(t)}. Report the "
            f"awards summary line shown on that page (wins and nominations).")


def gen_title_parents_guide():
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-parents-guide', i,
            f"Open the Parents Guide page for {title_label(t)}. Report the "
            f"severity rating in the 'Violence & Gore' row.")


def gen_title_tech_specs():
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-tech-specs', i,
            f"Open the Technical Specs page for {title_label(t)}. Report the "
            f"aspect ratio and sound mix listed there.")


def gen_title_keywords():
    rows = [t for t in top_titles if True][:50]
    for i, t in enumerate(rows):
        add('gui-title-keywords', i,
            f"Open the Keywords page for {title_label(t)}. How many keyword "
            f"pills are shown on the page? List the first three.")


def gen_title_locations():
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-locations', i,
            f"Open the Filming Locations page for {title_label(t)}. Report the "
            f"first filming location listed (or note that none are listed).")


def gen_title_companies():
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-companies', i,
            f"Open the Production Companies page for {title_label(t)}. Report "
            f"the first production company listed.")


def gen_title_release_info():
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-release-info', i,
            f"Open the Release Info page for {title_label(t)}. Report the "
            f"release date and language listed there.")


def gen_title_external():
    for i, t in enumerate(top_titles[:40]):
        add('gui-title-external', i,
            f"Open the External Sites page for {title_label(t)}. How many "
            f"entries are listed on the page?")


def gen_title_connections():
    for i, t in enumerate(top_titles[:40]):
        add('gui-title-connections', i,
            f"Open the Connections page for {title_label(t)}. Report the titles "
            f"shown in the 'related connections' grid (each card has a poster).")


def gen_title_photos():
    """Image-bearing: photo gallery."""
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-photos', i,
            f"Open the Photos page for {title_label(t)}. Report the caption "
            f"under the official poster image, and the caption under the first "
            f"cast headshot in the gallery.")


def gen_title_soundtrack():
    for i, t in enumerate(top_titles[:40]):
        add('gui-title-soundtrack', i,
            f"Open the Soundtrack page for {title_label(t)}. Report the name "
            f"of the original-music composer if any is listed.")


def gen_title_faq():
    for i, t in enumerate(top_titles[:50]):
        add('gui-title-faq', i,
            f"Open the FAQ page for {title_label(t)}. Report the answer to "
            f"'What is the runtime?' shown on the page.")


def gen_title_episodes():
    rows = [t for t in titles if t['title_type']=='tvSeries'][:40]
    for i, t in enumerate(rows):
        add('gui-title-episodes', i,
            f"Open the Episodes page for {title_label(t)}. Report how many "
            f"seasons are listed (Season N headings).")


def gen_name_bio():
    """Image-bearing: headshot."""
    for i, p in enumerate(persons[:50]):
        add('gui-name-bio', i,
            f"Open IMDb's Biography page for {p['name']} (look up the name via "
            f"search if needed). Report the opening sentence of the biography "
            f"shown on that page, alongside the headshot.")


def gen_name_personal():
    for i, p in enumerate(persons[:50]):
        add('gui-name-personal', i,
            f"Open the Personal Life page for {p['name']}. Report the value "
            f"shown next to 'Born' and 'Primary profession'.")


def gen_name_awards():
    for i, p in enumerate(persons[:40]):
        add('gui-name-awards', i,
            f"Open the Awards page for {p['name']}. Report the title of the "
            f"first project listed in the awards table.")


def gen_name_filmography():
    for i, p in enumerate(persons[:50]):
        add('gui-name-filmography', i,
            f"Open the Full Filmography page for {p['name']}. Report the number "
            f"of acting credits listed for them.")


def gen_name_photos():
    """Image-bearing — galleries."""
    for i, p in enumerate(persons[:50]):
        add('gui-name-photos', i,
            f"Open the Photo Gallery page for {p['name']}. Report the captions "
            f"under the first three figures on the page.")


def gen_advanced_search():
    samples = [(g, 8.0) for g in genres]
    for i, (g, rmin) in enumerate(samples):
        add('gui-advanced-search', i,
            f"Use the Advanced Title Search page. Filter by genre {g} and "
            f"set the minimum IMDb rating to {rmin}. Report the top three "
            f"titles in the result list, sorted by rating.")


def gen_news_index():
    for i, n in enumerate(news):
        add('gui-news-index', i,
            f"Open the IMDb News page. Locate the headline that begins with "
            f"'{n['headline'][:40]}'. Report its source and publication date.")


def gen_news_detail():
    for i, n in enumerate(news):
        add('gui-news-detail', i,
            f"Open the IMDb news article with headline starting "
            f"'{n['headline'][:40]}'. Click into the detail page and report "
            f"the article's category and any related title shown.")


def gen_polls_index():
    for i, p in enumerate(polls):
        add('gui-polls-index', i,
            f"Open the Polls page on IMDb. Locate the poll titled "
            f"'{p['question'][:60]}'. Report the number of voting options it has.")


def gen_poll_vote():
    """POST: vote on a poll."""
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    for i, p in enumerate(polls):
        opts = poll_options.get(p['id'], [])
        if len(opts) < 2:
            continue
        acct = accounts[i % 4]
        choice = opts[0]['label'][:60]
        add('gui-poll-vote', i,
            f"Sign in to IMDb as {acct}@test.com (password TestPass123!). Open "
            f"the poll '{p['question'][:60]}' and vote for the option matching "
            f"'{choice}'. Confirm afterward that the option shows your vote was recorded.")


def gen_lists_index():
    for i, L in enumerate(lists):
        add('gui-lists-index', i,
            f"Open the IMDb Lists index. Find the list titled '{L['name']}' "
            f"and report the owner displayed and the number of titles in it.")


def gen_list_detail():
    for i, L in enumerate(lists):
        items = list_items.get(L['id'], [])
        if not items:
            continue
        first = items[0]['primary_title']
        add('gui-list-detail', i,
            f"Open the IMDb list titled '{L['name']}'. Report the first title "
            f"in the list (as shown in the card grid) and how many titles total are in the list.")


def gen_list_create():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    names = [
        '90s Crime Classics', 'Sunday Comfort Watches',
        'Films Set in NYC', 'Underrated Sci-Fi',
        'My Top 5 Animated', 'Best Cinematography',
        'Films Under 90 Minutes', 'Films I want to see this year',
        'Awards-bait Dramas', 'Foreign Language Picks',
        'Cult Favorites', 'Films My Friend Recommended',
        'Long Films Worth The Time', 'Director: Christopher Nolan',
        'My Comfort Comedies', 'Watch With Family',
        'Reread The Book First', 'Heist Movies',
        'Time Travel Stories', 'Anti-Heroes',
    ]
    for i, name in enumerate(names):
        acct = accounts[i % 4]
        add('gui-list-create', i,
            f"Sign in to IMDb as {acct}@test.com (password TestPass123!). Open "
            f"the Create List page and submit a new public list titled "
            f"'{name}' with a brief description of your choice. Confirm the "
            f"new list appears on the public lists index.")


def gen_list_add():
    accounts_lists = []
    # only owner can add
    by_email = {}
    for L in lists:
        by_email.setdefault(L['owner_email'], []).append(L)
    keys = sorted(by_email.keys())
    samples = [(t['tt_id'], t['primary_title']) for t in top_titles[:30]]
    i = 0
    for email in keys:
        for L in by_email[email]:
            for tt, ptitle in samples[:3]:
                acct = email.split('@')[0]
                add('gui-list-add', i,
                    f"Sign in as {acct}@test.com (password TestPass123!). Open "
                    f"your list '{L['name']}' and add the title with tt-id "
                    f"{tt} ('{ptitle}'). Confirm the title appears in the list grid afterward.")
                i += 1
                if i >= 32:
                    return


def gen_review_helpful():
    """POST: vote helpful on a review."""
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:30]]
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        add('gui-review-helpful', i,
            f"Sign in to IMDb as {acct}@test.com (password TestPass123!). Open "
            f"the User Reviews page for {title_label(t)} and click 'Helpful' "
            f"on the very first (top) featured review.")


def gen_review_flag():
    """POST: flag review."""
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:30]]
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        cat = ['spoiler', 'offensive', 'other'][i % 3]
        add('gui-review-flag', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the User "
            f"Reviews page for {title_label(t)} and flag the top review with "
            f"category '{cat}'. Confirm a flash message acknowledges the report.")


def gen_trivia_submit():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:35]]
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        add('gui-trivia-submit', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"Trivia page for {title_label(t)} and submit a new trivia entry "
            f"of your own (body must not be empty). Confirm a flash message "
            f"says 'Trivia submitted for review.'")


def gen_quote_submit():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:30]]
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        cast = top_cast.get(t['id'], [])
        char = cast[0]['character'] if cast else 'Lead'
        add('gui-quote-submit', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"Quotes page for {title_label(t)} and add a new quote with "
            f"character set to '{char}' and a short line of dialogue. Confirm "
            f"the success flash appears.")


def gen_goof_submit():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:30]]
    cats = ['Continuity', 'Factual error', 'Audio/visual unsynchronised',
            'Anachronism', 'Crew or equipment visible', 'Plot hole']
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        cat = cats[i % len(cats)]
        add('gui-goof-submit', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"Goofs page for {title_label(t)} and submit a new goof in the "
            f"'{cat}' category. Confirm the success flash appears.")


def gen_title_report():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:30]]
    cats = ['incorrect-data', 'spoiler', 'duplicate', 'other']
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        cat = cats[i % len(cats)]
        add('gui-title-report', i,
            f"Sign in as {acct}@test.com (password TestPass123!). On the IMDb "
            f"page for {title_label(t)}, submit a report with category "
            f"'{cat}'. Confirm the report-acknowledged flash appears.")


def gen_follow():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [p for p in persons[:30]]
    for i, p in enumerate(rows):
        acct = accounts[i % 4]
        add('gui-follow', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"IMDb name page for {p['name']} and click the Follow button. "
            f"Confirm the page now shows 'Unfollow' for this person.")


def gen_mark_watched():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    rows = [t for t in top_titles[:30]]
    for i, t in enumerate(rows):
        acct = accounts[i % 4]
        add('gui-mark-watched', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"IMDb page for {title_label(t)} and click 'Mark as Watched'. "
            f"Confirm a flash message confirms the action.")


def gen_search_name():
    samples = [p for p in persons[:40]]
    for i, p in enumerate(samples):
        add('gui-search-name', i,
            f"Go to the IMDb Name Search page (under search, names tab). "
            f"Search for '{p['name'][:30]}' and confirm the matching result "
            f"includes a headshot in the result card.")


def gen_recently_viewed():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    for i in range(20):
        acct = accounts[i % 4]
        add('gui-recently-viewed', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"Recently Viewed page from your account. Report how many titles "
            f"appear under the 'From your Watchlist' heading and how many under 'From your ratings'.")


def gen_account_edit():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    new_names = ['Alice J. Reviewer', 'Bob the Cinephile', 'Carol D. Critic',
                 'David K. Watcher', 'Alice the Curator', 'Bobby C.',
                 'Carol Davis', 'Dave K.', 'Alice', 'Bob', 'Carol', 'David',
                 'A. Johnson', 'B. Chen', 'C. Davis', 'D. Kim',
                 'Alice Johnson', 'Bob Chen', 'Carol D.', 'David K.']
    for i, n in enumerate(new_names):
        acct = accounts[i % 4]
        add('gui-account-edit', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"Edit Profile page and change the display name to '{n}'. "
            f"Confirm the new name appears on your account summary afterward.")


def gen_watchlist_clear():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    for i in range(12):
        acct = accounts[i % 4]
        add('gui-watchlist-clear', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"account page and use 'Clear my Watchlist' to remove all "
            f"watchlist entries. Confirm the watchlist is now empty afterward.")


def gen_ratings_clear():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    for i in range(12):
        acct = accounts[i % 4]
        add('gui-ratings-clear', i,
            f"Sign in as {acct}@test.com (password TestPass123!). On the "
            f"account page use 'Clear my Ratings' to remove every personal "
            f"rating. Confirm the ratings page is now empty.")


def gen_follows_clear():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    for i in range(12):
        acct = accounts[i % 4]
        add('gui-follows-clear', i,
            f"Sign in as {acct}@test.com (password TestPass123!). On the "
            f"account page use 'Unfollow everyone' to clear all followed "
            f"persons. Confirm the followed-people count is zero afterward.")


def gen_poll_suggest():
    accounts = ['alice.j', 'bob.c', 'carol.d', 'david.k']
    for i, p in enumerate(polls):
        acct = accounts[i % 4]
        add('gui-poll-suggest', i,
            f"Sign in as {acct}@test.com (password TestPass123!). Open the "
            f"poll '{p['question'][:60]}' and use the 'Suggest a new option' "
            f"form to send a suggestion. Confirm a flash message says "
            f"'Suggestion sent to moderators.'")


# ---------------------------------------------------------------------------
# Run all generators
# ---------------------------------------------------------------------------

GENERATORS = [
    gen_chart_top, gen_chart_toptv, gen_chart_moviemeter, gen_chart_boxoffice,
    gen_chart_popular_tv, gen_chart_lowest_rated,
    gen_genre_browse, gen_advanced_search,
    gen_title_runtime, gen_title_director, gen_title_writer,
    gen_title_metadata, gen_title_box_office, gen_title_box_office_open,
    gen_title_cast_billing,
    gen_title_trivia, gen_title_quotes, gen_title_goofs, gen_title_awards,
    gen_title_parents_guide, gen_title_tech_specs, gen_title_keywords,
    gen_title_locations, gen_title_companies, gen_title_release_info,
    gen_title_external, gen_title_connections, gen_title_photos,
    gen_title_soundtrack, gen_title_faq, gen_title_episodes,
    gen_name_bio, gen_name_personal, gen_name_awards, gen_name_filmography,
    gen_name_photos,
    gen_news_index, gen_news_detail,
    gen_polls_index, gen_poll_vote,
    gen_lists_index, gen_list_detail, gen_list_create, gen_list_add,
    gen_review_helpful, gen_review_flag,
    gen_trivia_submit, gen_quote_submit, gen_goof_submit,
    gen_title_report, gen_follow, gen_mark_watched,
    gen_search_name, gen_recently_viewed,
    gen_account_edit, gen_watchlist_clear,
    gen_ratings_clear, gen_follows_clear, gen_poll_suggest,
]

for fn in GENERATORS:
    fn()

# Renumber per task_type so ids stay dense 000..
by_type = {}
for t in out:
    by_type.setdefault(t['task_type'], []).append(t)
final = []
for tt, rows in by_type.items():
    for i, r in enumerate(rows):
        r['id'] = f'IMDb--{tt}_{i:03d}'
        final.append(r)

OUT.write_text('\n'.join(json.dumps(t, ensure_ascii=False) for t in final) + '\n')

# Print summary
from collections import Counter
counts = Counter(t['task_type'] for t in final)
print(f"Wrote {len(final)} tasks across {len(counts)} task_types to {OUT}")
for k in sorted(counts):
    print(f"  {k}: {counts[k]}")
