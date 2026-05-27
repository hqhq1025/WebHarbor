#!/usr/bin/env python3
"""Task generator for the Rotten Tomatoes mirror deepening pass.

Reads the seeded DB and writes ~1500 WebVoyager-compatible benchmark tasks to
`tasks.jsonl`. The generator is deterministic: it iterates over sorted DB rows
so re-runs produce byte-identical task lists.
"""
import json
import os
import sqlite3
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "rotten_tomatoes.db")
OUT = os.path.join(BASE_DIR, "tasks.jsonl")
WEB = "http://localhost:40015/"
UPSTREAM = "https://www.rottentomatoes.com/"

# Existing curated baseline tasks (the original 20). We keep them so prior IDs
# stay stable; new tasks are appended starting at id=20.
BASELINE = [
    "Browse movies at home filtered by the Sci-Fi genre. Find the movie with the highest audience score among the results, navigate to its detail page, and report the name of its director.",
    "Search for 'Parasite' and go to its movie page. What is the difference between the Tomatometer score and the audience score?",
    "Search for 'knives out' and find the Knives Out sequel/mystery movie on the site. What streaming platform is it available on?",
    "Go to the Oppenheimer movie page and find who produced it. One of the producers also produced The Dark Knight and another well-known movie on this site. Search for and visit that third movie's page — what is its Tomatometer score?",
    "Browse movies at home and filter by the Animation genre and Certified Fresh. How many movies match these filters?",
    "Search for 'Cold Storage' and 'Jurassic World Rebirth' and visit both movie pages. Look at the Movie Info section — who is the screenwriter they have in common? What is the Tomatometer score difference between these two movies?",
    "Browse movies at home filtered to Disney+ platform, then filtered to Max platform. Compare the number of Certified Fresh movies available on each. Which platform has more Certified Fresh titles, and how many does each have?",
    "Go to Timothée Chalamet's celebrity page and find all movies in his filmography. Then check which of those movies are Certified Fresh by visiting each movie's detail page. How many are Certified Fresh?",
    "Register a new account with email testreviewer@test.com, name 'Test Reviewer', and password ReviewPass456!. After registering, verify you can access the account page.",
    "Log in as bob.c@test.com (password: TestPass123!), go to the account settings, and change the display name to 'Robert Clark'. Verify the name was updated on the account page.",
    "Log in as bob.c@test.com (password: TestPass123!), search for 'Parasite', navigate to its movie page, and add it to your watchlist. Then go to the watchlist page and verify 'Parasite' appears there. How many total movies are now in Bob's watchlist?",
    "Log in as david.k@test.com (password: TestPass123!), go to the watchlist page, and remove 'Deadpool & Wolverine' from the watchlist. How many movies remain in David's watchlist after removal?",
    "Log in as carol.d@test.com (password: TestPass123!). Search for 'Dune: Part Two', add it to your watchlist. Then search for 'Oppenheimer' and add that to your watchlist too. Go to the watchlist page — how many total movies are in Carol's watchlist now?",
    "Log in as alice.j@test.com (password: TestPass123!), search for 'The Dark Knight', go to its movie page, and give it a rating of 5 out of 5 stars. Then navigate to the 'My Ratings' page and verify the rating appears there.",
    "Log in as carol.d@test.com (password: TestPass123!) and navigate to the 'My Ratings' page. How many movies has Carol rated, and what score did she give to 'Oddity'?",
    "Log in as carol.d@test.com (password: TestPass123!), navigate to the 'Dune: Part Two' movie page, and submit an audience review with the text 'A visually stunning sequel that surpasses the original in every way' and a score of 5 out of 5. Then check the 'My Reviews' page to confirm it was saved.",
    "Log in as david.k@test.com (password: TestPass123!), go to the 'Superman' movie page, and write an audience review saying 'James Gunn delivers a fresh take on the Man of Steel' with a rating of 4 out of 5. After submitting, reload the page and verify your review appears in the audience reviews section.",
    "Compare 'Superman' and 'The Fantastic Four: First Steps' by visiting both movie pages. Which one has a higher Tomatometer score, and by how many percentage points?",
    "Search for 'Avengers: Endgame' and look at its Movie Info section to find the producer. Then search for other movies by that same producer on this site. Among all movies produced by this person, which one has the highest audience score, and what is it?",
    "Register a new account with email filmfan@test.com and password FilmFan123!. Then search for 'Inside Out 2', navigate to its page, add it to your watchlist, and give it a rating of 5 stars. Finally, go to your watchlist page to confirm it was added. How many items are in your watchlist?",
]


def load_db():
    """Load DB rows into a structured dict so templates can iterate."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    out = {}

    out["movies"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, title, year, tomatometer, audience_score, certified_fresh, "
        "pg_rating, director_name, streaming_platform, studio, box_office "
        "FROM movies ORDER BY id"
    )]
    out["persons"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, name, birthplace FROM persons ORDER BY id"
    )]
    out["tv_shows"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, title, year_start, year_end, network, tomatometer, audience_score, certified_fresh, genre_text "
        "FROM tv_shows ORDER BY id"
    )]
    out["critics"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, name, publication, top_critic FROM critics ORDER BY id"
    )]
    out["lists"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, title FROM movie_lists ORDER BY id"
    )]
    out["news"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, title, category, author FROM news_articles ORDER BY id"
    )]
    out["podcasts"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, title, host FROM podcasts ORDER BY id"
    )]
    out["polls"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, question FROM polls ORDER BY id"
    )]
    out["sweepstakes"] = [dict(r) for r in conn.execute(
        "SELECT id, slug, title, prize FROM sweepstakes ORDER BY id"
    )]
    out["genres"] = [dict(r) for r in conn.execute(
        "SELECT id, name, slug FROM genres ORDER BY name"
    )]
    out["awards_years"] = sorted({r[0] for r in conn.execute(
        "SELECT year FROM awards"
    )}, reverse=True)
    # Indexes
    out["movies_by_slug"] = {m["slug"]: m for m in out["movies"]}
    return out


def emit(tasks, q):
    """Append a task with auto-assigned RottenTomatoes ID."""
    idx = len(tasks)
    tasks.append({
        "web_name": "RottenTomatoes",
        "id": f"RottenTomatoes--{idx}",
        "ques": q,
        "web": WEB,
        "upstream_url": UPSTREAM,
    })


# ── Task template factories ───────────────────────────────────────

def gen_search_basic(tasks, data):
    """T1: Search for a movie and report a fact from its page."""
    movies = [m for m in data["movies"] if m["tomatometer"] >= 50][:120]
    facts = [
        ("director", "Who directed it?", "director_name"),
        ("year", "What year was it released?", "year"),
        ("tomatometer", "What is its Tomatometer score?", "tomatometer"),
        ("audience score", "What is the audience score?", "audience_score"),
        ("MPAA rating", "What is its MPAA rating?", "pg_rating"),
        ("studio", "Which studio distributed it?", "studio"),
        ("box office", "What is its US box office gross?", "box_office"),
        ("streaming platform", "Where is it currently streaming, if anywhere?", "streaming_platform"),
    ]
    for i, m in enumerate(movies):
        ftxt, fq, _ = facts[i % len(facts)]
        emit(tasks, f"Search for '{m['title']}' on Rotten Tomatoes and navigate to its movie page. {fq}")


def gen_tomatometer_vs_audience(tasks, data):
    """T2: Compute difference between tomatometer and audience score."""
    movies = sorted(data["movies"], key=lambda m: abs(m["tomatometer"] - m["audience_score"]), reverse=True)[:80]
    for m in movies:
        emit(tasks, f"Go to the '{m['title']}' ({m['year']}) movie page on Rotten Tomatoes. What is the difference between its Tomatometer score and its audience score (positive if Tomatometer is higher)?")


def gen_filter_browse(tasks, data):
    """T3: Browse movies with genre/platform/year filters."""
    genres = data["genres"]
    platforms = ["Netflix", "Max", "Disney+", "Apple TV+", "Prime Video", "Paramount+", "Hulu", "Peacock"]
    years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
    ratings = ["G", "PG", "PG-13", "R"]
    for g in genres:
        emit(tasks, f"Browse all movies on Rotten Tomatoes and filter by the {g['name']} genre. How many movies match this filter?")
    for p in platforms:
        emit(tasks, f"Browse the streaming hub on Rotten Tomatoes and filter to the {p} platform. How many movies are listed?")
    for y in years:
        emit(tasks, f"Browse all movies on Rotten Tomatoes and filter by the year {y}. Report how many movies are listed.")
    for r in ratings:
        emit(tasks, f"Browse all movies on Rotten Tomatoes and filter by the {r} MPAA rating. How many movies match?")


def gen_top_by_genre(tasks, data):
    """T4: Find the highest-rated movie in a genre."""
    genres = data["genres"]
    for g in genres:
        emit(tasks, f"On Rotten Tomatoes, browse all movies filtered to the {g['name']} genre and sorted by Tomatometer. Which movie is ranked first, and what is its Tomatometer score?")
        emit(tasks, f"On Rotten Tomatoes, browse all movies filtered to the {g['name']} genre and sorted by audience score. Which movie is ranked first, and what is its audience score?")


def gen_certified_fresh_count(tasks, data):
    """T5: Count certified fresh by various filters."""
    for g in data["genres"]:
        emit(tasks, f"On Rotten Tomatoes, browse movies in the {g['name']} genre that are Certified Fresh. How many are there?")


def gen_celebrity_filmography(tasks, data):
    """T6: Find an actor's filmography stats."""
    persons = data["persons"][:150]
    for p in persons:
        emit(tasks, f"Go to {p['name']}'s celebrity page on Rotten Tomatoes. How many movies are listed in their filmography?")
        emit(tasks, f"Visit {p['name']}'s page on Rotten Tomatoes and look at their highest-rated film on the site. What is its title?")


def gen_tv_show(tasks, data):
    """T7: TV show navigation."""
    for tv in data["tv_shows"]:
        emit(tasks, f"Visit the '{tv['title']}' page on Rotten Tomatoes. What is its Tomatometer score and on which network does it air?")
        emit(tasks, f"Go to the '{tv['title']}' page on Rotten Tomatoes and open Season 1. How many episodes are in Season 1?")
        emit(tasks, f"Browse TV shows on Rotten Tomatoes and find '{tv['title']}'. What years was the show on the air?")


def gen_critic_navigation(tasks, data):
    """T8: Critic pages."""
    critics = data["critics"][:100]
    for c in critics:
        emit(tasks, f"On Rotten Tomatoes, navigate to the Critics directory and open {c['name']}'s page. Which publication do they write for?")
    top_critics = [c for c in data["critics"] if c["top_critic"]][:30]
    for c in top_critics:
        emit(tasks, f"Filter the Critics directory to show Top Critics only. Locate {c['name']}'s entry. How many of their reviews are indexed on the site?")


def gen_list_navigation(tasks, data):
    """T9: Editorial list navigation."""
    for lst in data["lists"]:
        emit(tasks, f"On Rotten Tomatoes, open the editorial list titled '{lst['title']}'. How many movies are on the list?")
        emit(tasks, f"Visit the '{lst['title']}' list on Rotten Tomatoes. Which movie is ranked #1 in the list?")


def gen_news_navigation(tasks, data):
    """T10: News and feature articles."""
    for a in data["news"]:
        emit(tasks, f"Open the Rotten Tomatoes news article titled '{a['title']}'. Who is the author of the article?")
    for cat in ["Movies", "TV", "Awards", "Box Office", "Streaming", "Trailers", "Interviews"]:
        emit(tasks, f"Visit the Rotten Tomatoes News hub and filter to the '{cat}' category. How many articles are listed?")


def gen_podcast(tasks, data):
    """T11: Podcasts."""
    for p in data["podcasts"]:
        emit(tasks, f"Open the Rotten Tomatoes podcast '{p['title']}'. Who hosts the podcast?")
        emit(tasks, f"Navigate to the '{p['title']}' podcast page on Rotten Tomatoes. What is the title of the most recent episode?")


def gen_polls(tasks, data):
    """T12: Polls and sweepstakes."""
    for poll in data["polls"]:
        emit(tasks, f"Visit the Rotten Tomatoes community poll '{poll['question']}'. Which option is currently leading the vote?")
    for sw in data["sweepstakes"]:
        emit(tasks, f"Open the Rotten Tomatoes sweepstakes titled '{sw['title']}'. What is the prize?")


def gen_awards(tasks, data):
    """T13: Awards hub."""
    for y in data["awards_years"][:25]:
        emit(tasks, f"Open the Rotten Tomatoes awards hub for the year {y}. Which film won Best Picture?")
        emit(tasks, f"Look up the {y} awards on Rotten Tomatoes. Who won Best Director, and for which film?")


def gen_streaming_hubs(tasks, data):
    """T14: Theatrical / streaming hubs."""
    hubs = [
        ("In Theaters", "/theatrical/in-theaters", "in theaters now"),
        ("Coming Soon to Theaters", "/theatrical/coming-soon", "coming soon to theaters"),
        ("Streaming Now", "/streaming/now", "available to stream now"),
        ("Streaming Coming Soon", "/streaming/coming-soon", "coming to streaming soon"),
    ]
    for title, _, descr in hubs:
        emit(tasks, f"Visit the '{title}' hub on Rotten Tomatoes. How many movies are listed as {descr}?")


def gen_account_actions(tasks, data):
    """T15: Authenticated POST actions (rate / review / want-to-see / watched / watchlist)."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    movies = data["movies"][:120]
    # Want-to-See add
    for i, m in enumerate(movies[:40]):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), navigate to the '{m['title']}' page on Rotten Tomatoes, and add it to your Want to See list. Then go to /myaccount/want-to-see and verify the title appears. How many movies are in your Want to See list now?")
    # Mark Watched
    for i, m in enumerate(movies[40:80]):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open the '{m['title']}' movie page on Rotten Tomatoes, and mark it as Watched. Then go to /myaccount/watched and confirm the title appears there.")
    # Rating
    for i, m in enumerate(movies[80:120]):
        u = users[i % 4]
        rate = 0.5 + (i % 10) * 0.5
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open the '{m['title']}' movie page, and give it a rating of {rate} out of 5 stars. Then visit the 'My Ratings' page to confirm the rating was saved.")
    # Watchlist add
    for i, m in enumerate(movies[:40]):
        u = users[(i + 1) % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), search for '{m['title']}', open its movie page, and add it to your watchlist.")
    # Write an audience review
    review_phrases = [
        "An instant classic — the kind of film you'll want to revisit again and again.",
        "Visually stunning but the second act drags. Still worth a watch.",
        "Better than expected. The cast is excellent and the pacing is tight.",
        "A bold swing that mostly connects. Recommended for genre fans.",
        "Pure popcorn entertainment from start to finish.",
    ]
    for i, m in enumerate(movies[:30]):
        u = users[i % 4]
        rate = 3.0 + (i % 5) * 0.5
        phrase = review_phrases[i % len(review_phrases)]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), navigate to the '{m['title']}' movie page, and submit an audience review with the text '{phrase}' and a rating of {rate} out of 5. Then check the My Reviews page to confirm it was saved.")


def gen_critic_follow(tasks, data):
    """T16: Follow / unfollow critics."""
    critics = data["critics"][:30]
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    for i, c in enumerate(critics):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), navigate to the critic page for '{c['name']}' on Rotten Tomatoes, and click Follow. Then visit /myaccount/follows and confirm '{c['name']}' appears in your followed critics.")


def gen_poll_vote(tasks, data):
    """T17: Cast poll votes."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    for i, p in enumerate(data["polls"]):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open the community poll '{p['question']}', and submit a vote for the first option. After voting, the page should display the results bar.")


def gen_sweepstakes_enter(tasks, data):
    """T18: Enter sweepstakes."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    for i, sw in enumerate(data["sweepstakes"]):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), navigate to the sweepstakes titled '{sw['title']}', and click Enter Sweepstakes. Then visit /myaccount/sweepstakes and confirm your entry is listed.")


def gen_podcast_subscribe(tasks, data):
    """T19: Subscribe to podcasts."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    for i, p in enumerate(data["podcasts"]):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open the podcast '{p['title']}' on Rotten Tomatoes, and subscribe. Then visit /myaccount/podcasts to confirm the subscription.")


def gen_news_comment(tasks, data):
    """T20: Comment on news articles."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    for i, a in enumerate(data["news"][:45]):
        u = users[i % 4]
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open the Rotten Tomatoes news article '{a['title']}', and post a comment that reads 'Great read, thanks for the writeup.' Then verify the comment appears on the article page.")


def gen_review_helpful(tasks, data):
    """T21: Mark a review as helpful or report it."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    movies = data["movies"][:60]
    for i, m in enumerate(movies):
        u = users[i % 4]
        action = "mark the most recent audience review as Helpful" if i % 2 == 0 else "report the most recent audience review for 'inappropriate'"
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open the reviews tab for '{m['title']}' on Rotten Tomatoes, and {action}.")


def gen_list_management(tasks, data):
    """T22: Create / add to / delete a user list."""
    users = ["alice.j", "bob.c", "carol.d", "david.k"]
    movies = data["movies"]
    for i in range(12):
        u = users[i % 4]
        title = f"My Top {i+5} Picks of {2020 + (i % 6)}"
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), go to /myaccount/lists, and create a public list titled '{title}'. After creating, you should land on the new list's page.")
    # Add movies to a created list
    for i, m in enumerate(movies[:12]):
        u = users[i % 4]
        list_title = f"My Top {(i % 6) + 5} Picks of {2020 + (i % 6)}"
        emit(tasks, f"Log in as {u}@test.com (password: TestPass123!), open your previously-created list '{list_title}', and add '{m['title']}' to that list.")


def gen_disambiguation(tasks, data):
    """T23: Disambiguation tasks (users with multiple items)."""
    emit(tasks, "Log in as alice.j@test.com (password: TestPass123!). She has multiple movies in her watchlist. Pick the oldest one (lowest release year) and remove it from the watchlist. Report the title you removed.")
    emit(tasks, "Log in as bob.c@test.com (password: TestPass123!). He has multiple ratings on file. Find the movie he rated lowest and report its title.")
    emit(tasks, "Log in as carol.d@test.com (password: TestPass123!). She has multiple audience reviews. From the My Reviews page, delete the review for the movie with the lowest Tomatometer score and report which review you deleted.")
    emit(tasks, "Log in as david.k@test.com (password: TestPass123!). His watchlist contains movies from multiple studios. Which studio appears most often in his watchlist?")


def gen_compare(tasks, data):
    """T24: Comparative tasks."""
    pairs = []
    seen = set()
    for i, m1 in enumerate(data["movies"]):
        if i % 3 != 0:
            continue
        for j, m2 in enumerate(data["movies"][i+1:]):
            if j % 5 != 0:
                continue
            if (m1["slug"], m2["slug"]) in seen:
                continue
            seen.add((m1["slug"], m2["slug"]))
            pairs.append((m1, m2))
            if len(pairs) >= 100:
                break
        if len(pairs) >= 100:
            break
    for m1, m2 in pairs:
        emit(tasks, f"Compare '{m1['title']}' and '{m2['title']}' on Rotten Tomatoes by visiting both movie pages. Which one has the higher Tomatometer score, and by how many percentage points?")


def gen_year_search(tasks, data):
    """T25: Find a movie by year + descriptor."""
    movies = sorted(data["movies"], key=lambda m: (m["year"], m["title"]))
    by_year = defaultdict(list)
    for m in movies:
        by_year[m["year"]].append(m)
    for year, mlist in sorted(by_year.items()):
        if year < 2018 or year > 2026:
            continue
        if len(mlist) >= 2:
            emit(tasks, f"On Rotten Tomatoes, find the highest-rated movie released in {year}. Report its title and Tomatometer score.")
            emit(tasks, f"On Rotten Tomatoes, find how many movies in the catalog were released in {year}.")


def gen_register(tasks, data):
    """T26: Account creation flows."""
    for i in range(20):
        email = f"reviewer{i:02d}@test.com"
        emit(tasks, f"Register a new account on Rotten Tomatoes with email {email}, name 'Reviewer {i:02d}', and password 'Pass{i:02d}!'. After registering, verify you can access the account page.")


def gen_tv_episode(tasks, data):
    """T27: Specific episode navigation."""
    for tv in data["tv_shows"]:
        emit(tasks, f"Navigate to '{tv['title']}' on Rotten Tomatoes, then to Season 1, Episode 1. Report the air date listed for that episode.")
        emit(tasks, f"Open the latest available season of '{tv['title']}' on Rotten Tomatoes. How many episodes does that season have?")


def gen_search_person(tasks, data):
    """T28: Search for people."""
    persons = data["persons"][150:300]
    for p in persons:
        emit(tasks, f"Use the search bar on Rotten Tomatoes to find '{p['name']}'. Click their profile and report where they were born.")


def gen_photos(tasks, data):
    """T29: Photos tab navigation."""
    movies = data["movies"][:60]
    for m in movies:
        emit(tasks, f"Open the '{m['title']}' page on Rotten Tomatoes and navigate to the Photos tab. How many photos are displayed?")


def gen_streaming_filter(tasks, data):
    """T30: Streaming platform deep-dive."""
    platforms = ["Netflix", "Max", "Disney+", "Apple TV+", "Prime Video"]
    for p in platforms:
        emit(tasks, f"Browse movies streaming on {p} via Rotten Tomatoes. How many of those are Certified Fresh?")
        emit(tasks, f"On Rotten Tomatoes, find the highest-rated movie currently streaming on {p}. Report its title and Tomatometer score.")


# ── Driver ───────────────────────────────────────────────────────

def main():
    data = load_db()
    tasks = []
    # Start with the original 20 baseline tasks (preserved for stable IDs).
    for q in BASELINE:
        emit(tasks, q)

    # Generators (deterministic order).
    generators = [
        gen_search_basic,
        gen_tomatometer_vs_audience,
        gen_filter_browse,
        gen_top_by_genre,
        gen_certified_fresh_count,
        gen_celebrity_filmography,
        gen_tv_show,
        gen_critic_navigation,
        gen_list_navigation,
        gen_news_navigation,
        gen_podcast,
        gen_polls,
        gen_awards,
        gen_streaming_hubs,
        gen_account_actions,
        gen_critic_follow,
        gen_poll_vote,
        gen_sweepstakes_enter,
        gen_podcast_subscribe,
        gen_news_comment,
        gen_review_helpful,
        gen_list_management,
        gen_disambiguation,
        gen_compare,
        gen_year_search,
        gen_register,
        gen_tv_episode,
        gen_search_person,
        gen_photos,
        gen_streaming_filter,
    ]
    for gen in generators:
        gen(tasks, data)

    with open(OUT, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Wrote {len(tasks)} tasks to {OUT}")
    # Brief breakdown
    print(f"Templates: {len(generators) + 1} (1 baseline + {len(generators)} programmatic)")


if __name__ == "__main__":
    main()
