#!/usr/bin/env python3
"""Generate synthetic audience reviews for the rotten_tomatoes seed.

Goal: produce 500+ rows distributed across all 147 movies (target 4-8 per
movie) using deterministic templates parametrised by the movie's audience_score
and primary genre. Output is appended to seed_data.AUDIENCE_REVIEWS via stdout
as a Python list literal — the caller pastes the result into seed_data.py.

The templates are intentionally generic-but-genre-aware so they pass a quick
plausibility check on the movie detail page; they are NOT scraped from real
RT users. A few seed reviews from the original 28-row list are preserved by
the caller (this script does not delete them).
"""
import json
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_data import MOVIES, AUDIENCE_REVIEWS

# Pool of plausible audience handles. Stable order — picked deterministically
# via per-movie hash so seeds replay byte-identically.
USER_HANDLES = [
    "Jordan M", "Alex T", "Sam P", "Taylor R", "Morgan K", "Riley S", "Casey L",
    "Quinn B", "Avery J", "Reese D", "Drew N", "Hayden W", "Parker O", "Sage V",
    "Blake H", "Rowan F", "Skyler C", "Devon E", "Cameron Y", "Eli G", "Harper Z",
    "Indigo A", "Jamie U", "Kai L", "Lennox I", "Marlowe X", "Nico P", "Ocean Q",
    "Phoenix R", "Rio S", "Sasha T", "Toby U", "Vesper V", "Wren W", "Yuki Y",
    "Zion Z", "Ashton M", "Brielle K", "Cody P", "Daria L", "Emery T", "Finn S",
    "Gemma R", "Holly N", "Isla J", "Juno D", "Kira C", "Liam B", "Mira A",
    "Nina O", "Owen H", "Pia F", "Quincy E", "Rina G", "Silas X", "Tara V",
    "Una Y", "Vance Q", "Will P", "Xena Z", "Yasmin W", "Zane U", "Aria I",
    "Beau H", "Cleo G", "Dax F", "Esme E", "Flynn D", "Gianna C", "Hugo B",
    "Iris A", "Jude T", "Kelsey S", "Luca R", "Maya Q", "Nash P", "Olive O",
    "Pax N",
]

# Score buckets — review tone scales with audience_score.
POSITIVE = 5      # 90+
GOOD = 4          # 70-89
MIXED = 3         # 50-69
NEGATIVE = 2      # 30-49
PAN = 1           # <30

GENRE_HOOKS = {
    'Action':           ["the action sequences", "the fight choreography", "the set-pieces", "the pacing"],
    'Adventure':        ["the world-building", "the journey", "the scope", "the spectacle"],
    'Animation':        ["the animation", "the art direction", "the character designs", "the visual style"],
    'Biography':        ["the lead performance", "the historical detail", "the screenplay", "the emotional arc"],
    'Comedy':           ["the jokes", "the comedic timing", "the chemistry between the leads", "the gags"],
    'Crime':            ["the tension", "the twists", "the cat-and-mouse dynamic", "the atmosphere"],
    'Documentary':      ["the access", "the editing", "the subject's story", "the interviews"],
    'Drama':            ["the performances", "the writing", "the emotional weight", "the quiet moments"],
    'Fantasy':          ["the magic system", "the lore", "the costume design", "the production design"],
    'History':          ["the period detail", "the lead performance", "the script", "the cinematography"],
    'Horror':           ["the dread", "the scares", "the sound design", "the atmosphere"],
    'Kids & Family':    ["the heart", "the humor", "the message", "the characters"],
    'Musical':          ["the songs", "the choreography", "the lead vocal performance", "the staging"],
    'Mystery & Thriller': ["the suspense", "the mystery", "the twists", "the pacing"],
    'Romance':          ["the chemistry between the leads", "the writing", "the emotional honesty", "the soundtrack"],
    'Sci-Fi':           ["the world-building", "the visual effects", "the ideas", "the production design"],
    'Western':          ["the cinematography", "the lead performance", "the landscapes", "the tone"],
}
DEFAULT_HOOKS = ["the performances", "the script", "the direction", "the pacing"]

POSITIVE_TPLS = [
    "Loved {hook}. {title} is exactly the kind of movie I want to see in theaters again.",
    "{title} blew me away. {hook_cap} alone is worth the watch.",
    "Probably my favorite {genre} of the year. {hook_cap} stuck with me for days.",
    "Easily a 5/5. {hook_cap} is on a different level here.",
    "This is the one. {hook_cap} delivers and the ending sticks the landing.",
    "Watched it twice in a week. {hook_cap} keeps getting better on rewatches.",
    "Hands-down one of the best things I've watched in years. {hook_cap} is masterful.",
    "Cinematic. {hook_cap} carries this from start to finish.",
]
GOOD_TPLS = [
    "Really enjoyed it. {hook_cap} is the highlight.",
    "Solid {genre}. {hook_cap} works, even if the third act gets a bit long.",
    "Better than I expected. {hook_cap} kept me engaged the whole way.",
    "Fun watch. {hook_cap} more than makes up for the slower middle stretch.",
    "Glad I saw it on the big screen. {hook_cap} pops on a real screen.",
    "Strong recommend. {hook_cap} is doing a lot of heavy lifting and it earns it.",
    "Good time at the movies. {hook_cap} is the reason to go.",
]
MIXED_TPLS = [
    "Middle of the road for me. {hook_cap} is good but the script lets it down.",
    "Wanted to love it. {hook_cap} works but the pacing drags in the second half.",
    "Mixed bag. {hook_cap} carries it but there are some weird tonal choices.",
    "It was fine. {hook_cap} is the strongest element by a mile.",
    "Some great moments and some flat ones. {hook_cap} keeps it watchable.",
]
NEGATIVE_TPLS = [
    "Didn't land for me. {hook_cap} was the only thing keeping me in my seat.",
    "Disappointing. {hook_cap} can't save a clunky script.",
    "Wanted more from {title}. {hook_cap} deserved a better movie around it.",
    "Skip it. {hook_cap} is fine but the rest just doesn't work.",
]
PAN_TPLS = [
    "Walked out feeling cheated. Even {hook} couldn't hold this together.",
    "Hard pass. Not even {hook} could rescue this.",
    "One of the year's biggest letdowns. {hook_cap} is bafflingly mishandled.",
]


def bucket(score):
    if score is None:
        return GOOD
    if score >= 90:
        return POSITIVE
    if score >= 70:
        return GOOD
    if score >= 50:
        return MIXED
    if score >= 30:
        return NEGATIVE
    return PAN


def tpl_pool(score_bucket):
    return {
        POSITIVE: POSITIVE_TPLS,
        GOOD:     GOOD_TPLS,
        MIXED:    MIXED_TPLS,
        NEGATIVE: NEGATIVE_TPLS,
        PAN:      PAN_TPLS,
    }[score_bucket]


def seeded_rand(seed_str, n):
    """Deterministic int in [0,n) from a string seed (sha256-based)."""
    h = hashlib.sha256(seed_str.encode()).digest()
    return int.from_bytes(h[:4], 'big') % n


def primary_genre(movie):
    g = movie.get('genres') or []
    for name in g:
        if name in GENRE_HOOKS:
            return name
    return g[0] if g else ''


def gen_review(movie, idx):
    score = movie.get('audience_score') or 70
    bkt = bucket(score)
    # Some variance — give 1-in-6 reviews a different mood than the consensus
    drift = seeded_rand(f"{movie['slug']}|{idx}|drift", 6)
    if drift == 0 and bkt > PAN:
        actual = bkt - 1
    elif drift == 1 and bkt < POSITIVE:
        actual = bkt + 1
    else:
        actual = bkt

    pool = tpl_pool(actual)
    tpl = pool[seeded_rand(f"{movie['slug']}|{idx}|tpl", len(pool))]
    genre = primary_genre(movie) or 'movie'
    hooks = GENRE_HOOKS.get(genre, DEFAULT_HOOKS)
    hook = hooks[seeded_rand(f"{movie['slug']}|{idx}|hook", len(hooks))]
    text = tpl.format(
        title=movie['title'],
        genre=genre.lower() if genre != 'movie' else 'movie',
        hook=hook,
        hook_cap=hook[0].upper() + hook[1:],
    )
    user = USER_HANDLES[seeded_rand(f"{movie['slug']}|{idx}|user", len(USER_HANDLES))]
    return {
        "movie_slug": movie['slug'],
        "user": user,
        "text": text,
        "rating": actual,
    }


def gen_all(target_per_movie_min=4, target_per_movie_max=7):
    # Count what's already there
    existing = {}
    for r in AUDIENCE_REVIEWS:
        existing[r['movie_slug']] = existing.get(r['movie_slug'], 0) + 1

    out = []
    for m in MOVIES:
        have = existing.get(m['slug'], 0)
        # Per-movie target derived deterministically from slug hash, in [min,max]
        span = target_per_movie_max - target_per_movie_min + 1
        target = target_per_movie_min + seeded_rand(f"{m['slug']}|target", span)
        need = max(0, target - have)
        for i in range(need):
            # idx offset by `have` so seeds added now don't collide with later
            # manual additions to the existing 28-row list.
            out.append(gen_review(m, have + i))
    return out


if __name__ == '__main__':
    new_rows = gen_all()
    print(f"# Generated {len(new_rows)} new audience reviews ({len(AUDIENCE_REVIEWS)} pre-existing).",
          file=sys.stderr)
    # Emit as Python list literal fragment for direct paste into seed_data.py
    for r in new_rows:
        # repr handles quoting cleanly
        print("    " + json.dumps(r, ensure_ascii=False) + ",")
