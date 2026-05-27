"""
Extra seed data for the Rotten Tomatoes deepening pass.

Adds new content types (TV shows, critics, lists, news, podcasts, sweepstakes,
polls, awards, photos, comments, etc.) plus the seeding logic that fills the
new tables defined in app.py. All values are deterministic — derived from the
existing MOVIES / PERSONS / USERS lists in seed_data.py so the
byte-identical reset invariant still holds.
"""
from datetime import datetime, timedelta
import hashlib


REF_DATE = datetime(2026, 5, 26, 12, 0, 0)


# ──────────────────────────────────────────────
# TV Shows — small curated set with seasons/episodes
# ──────────────────────────────────────────────

TV_SHOWS = [
    {"slug": "the_last_of_us", "title": "The Last of Us", "year_start": 2023, "year_end": 0,
     "network": "HBO", "tomatometer": 96, "audience_score": 87, "certified_fresh": True,
     "genres": ["Drama", "Sci-Fi", "Horror"],
     "synopsis": "Twenty years after a fungal pandemic has destroyed civilization, hardened survivor Joel takes on the job of smuggling 14-year-old Ellie out of an oppressive quarantine zone.",
     "poster": "/static/images/posters/the_last_of_us.jpg",
     "seasons": [
         {"number": 1, "year": 2023, "episodes": 9, "title": "Season 1",
          "synopsis": "Joel and Ellie's cross-country journey across post-apocalyptic America."},
         {"number": 2, "year": 2025, "episodes": 7, "title": "Season 2",
          "synopsis": "Five years after the events of season 1, Ellie and Joel are drawn into conflict with each other and a world even more dangerous than the one they left behind."},
     ]},
    {"slug": "the_bear", "title": "The Bear", "year_start": 2022, "year_end": 0,
     "network": "FX", "tomatometer": 99, "audience_score": 84, "certified_fresh": True,
     "genres": ["Comedy", "Drama"],
     "synopsis": "A young chef from the fine dining world returns to Chicago to run his family's Italian beef sandwich shop.",
     "poster": "/static/images/posters/the_bear.jpg",
     "seasons": [
         {"number": 1, "year": 2022, "episodes": 8, "title": "Season 1",
          "synopsis": "Carmy returns to Chicago to run his late brother's sandwich shop."},
         {"number": 2, "year": 2023, "episodes": 10, "title": "Season 2",
          "synopsis": "The crew prepares to open a new restaurant."},
         {"number": 3, "year": 2024, "episodes": 10, "title": "Season 3",
          "synopsis": "After opening night, Carmy chases an impossible standard."},
     ]},
    {"slug": "shogun", "title": "Shōgun", "year_start": 2024, "year_end": 0,
     "network": "FX", "tomatometer": 99, "audience_score": 90, "certified_fresh": True,
     "genres": ["Drama", "History", "War"],
     "synopsis": "In Japan in the year 1600, at the dawn of a century-defining civil war, Lord Yoshii Toranaga is fighting for his life as his enemies on the Council of Regents unite against him.",
     "poster": "/static/images/posters/shogun.jpg",
     "seasons": [
         {"number": 1, "year": 2024, "episodes": 10, "title": "Season 1",
          "synopsis": "Lord Toranaga maneuvers against the Council of Regents while an English navigator washes ashore."},
     ]},
    {"slug": "succession", "title": "Succession", "year_start": 2018, "year_end": 2023,
     "network": "HBO", "tomatometer": 95, "audience_score": 87, "certified_fresh": True,
     "genres": ["Drama"],
     "synopsis": "The Roy family is known for controlling the biggest media and entertainment company in the world. However, their world changes when their father steps down from the company.",
     "poster": "/static/images/posters/succession.jpg",
     "seasons": [
         {"number": s, "year": 2017 + s, "episodes": 10, "title": f"Season {s}",
          "synopsis": f"Roy family power dynamics escalate in season {s}."}
         for s in range(1, 5)
     ]},
    {"slug": "severance", "title": "Severance", "year_start": 2022, "year_end": 0,
     "network": "Apple TV+", "tomatometer": 96, "audience_score": 87, "certified_fresh": True,
     "genres": ["Drama", "Mystery & Thriller", "Sci-Fi"],
     "synopsis": "Mark leads a team of office workers whose memories have been surgically divided between their work and personal lives.",
     "poster": "/static/images/posters/severance.jpg",
     "seasons": [
         {"number": 1, "year": 2022, "episodes": 9, "title": "Season 1",
          "synopsis": "Mark begins to question his role at Lumon Industries."},
         {"number": 2, "year": 2025, "episodes": 10, "title": "Season 2",
          "synopsis": "Innie consequences spill outside Lumon."},
     ]},
    {"slug": "house_of_the_dragon", "title": "House of the Dragon", "year_start": 2022, "year_end": 0,
     "network": "HBO", "tomatometer": 84, "audience_score": 80, "certified_fresh": True,
     "genres": ["Fantasy", "Drama", "Action"],
     "synopsis": "The reign of House Targaryen begins with King Viserys ascending the Iron Throne, and ends 172 years before the birth of Daenerys Targaryen.",
     "poster": "/static/images/posters/house_of_the_dragon.jpg",
     "seasons": [
         {"number": 1, "year": 2022, "episodes": 10, "title": "Season 1",
          "synopsis": "The Dance of the Dragons looms as the succession turns bitter."},
         {"number": 2, "year": 2024, "episodes": 8, "title": "Season 2",
          "synopsis": "Civil war fractures the realm."},
     ]},
    {"slug": "fallout", "title": "Fallout", "year_start": 2024, "year_end": 0,
     "network": "Prime Video", "tomatometer": 94, "audience_score": 89, "certified_fresh": True,
     "genres": ["Sci-Fi", "Adventure", "Drama"],
     "synopsis": "In a post-apocalyptic future Los Angeles, a vault dweller goes searching for her kidnapped father.",
     "poster": "/static/images/posters/fallout.jpg",
     "seasons": [
         {"number": 1, "year": 2024, "episodes": 8, "title": "Season 1",
          "synopsis": "Lucy ventures from Vault 33 into the irradiated wasteland."},
     ]},
    {"slug": "the_penguin", "title": "The Penguin", "year_start": 2024, "year_end": 0,
     "network": "Max", "tomatometer": 95, "audience_score": 95, "certified_fresh": True,
     "genres": ["Crime", "Drama"],
     "synopsis": "Picking up one week after the events of The Batman, Oz Cobb makes a play for power in Gotham's criminal underworld.",
     "poster": "/static/images/posters/the_penguin.jpg",
     "seasons": [
         {"number": 1, "year": 2024, "episodes": 8, "title": "Season 1",
          "synopsis": "Oz Cobb rises through Gotham's underworld."},
     ]},
    {"slug": "andor", "title": "Andor", "year_start": 2022, "year_end": 2025,
     "network": "Disney+", "tomatometer": 96, "audience_score": 85, "certified_fresh": True,
     "genres": ["Sci-Fi", "Adventure", "Drama"],
     "synopsis": "In an era filled with danger, deception and intrigue, Cassian Andor embarks on the path that is destined to turn him into a rebel hero.",
     "poster": "/static/images/posters/andor.jpg",
     "seasons": [
         {"number": s, "year": 2021 + s, "episodes": 12, "title": f"Season {s}",
          "synopsis": f"Cassian's journey toward Rogue One continues in season {s}."}
         for s in range(1, 3)
     ]},
    {"slug": "the_crown", "title": "The Crown", "year_start": 2016, "year_end": 2023,
     "network": "Netflix", "tomatometer": 89, "audience_score": 78, "certified_fresh": True,
     "genres": ["Drama", "History", "Biography"],
     "synopsis": "Follows the political rivalries and romance of Queen Elizabeth II's reign and the events that shaped the second half of the 20th century.",
     "poster": "/static/images/posters/the_crown.jpg",
     "seasons": [
         {"number": s, "year": 2015 + s, "episodes": 10, "title": f"Season {s}",
          "synopsis": f"The reign of Queen Elizabeth II in season {s}."}
         for s in range(1, 7)
     ]},
    {"slug": "stranger_things", "title": "Stranger Things", "year_start": 2016, "year_end": 0,
     "network": "Netflix", "tomatometer": 92, "audience_score": 87, "certified_fresh": True,
     "genres": ["Drama", "Fantasy", "Horror", "Mystery & Thriller"],
     "synopsis": "When a young boy vanishes, a small town uncovers a mystery involving secret experiments, terrifying supernatural forces and one strange little girl.",
     "poster": "/static/images/posters/stranger_things.jpg",
     "seasons": [
         {"number": s, "year": 2015 + s, "episodes": 9, "title": f"Season {s}",
          "synopsis": f"Hawkins' troubles deepen in season {s}."}
         for s in range(1, 5)
     ]},
    {"slug": "ted_lasso", "title": "Ted Lasso", "year_start": 2020, "year_end": 2023,
     "network": "Apple TV+", "tomatometer": 92, "audience_score": 90, "certified_fresh": True,
     "genres": ["Comedy", "Drama"],
     "synopsis": "An American football coach is hired to manage a British soccer team — despite having no experience.",
     "poster": "/static/images/posters/ted_lasso.jpg",
     "seasons": [
         {"number": s, "year": 2019 + s, "episodes": 12, "title": f"Season {s}",
          "synopsis": f"AFC Richmond's journey in season {s}."}
         for s in range(1, 4)
     ]},
    {"slug": "the_white_lotus", "title": "The White Lotus", "year_start": 2021, "year_end": 0,
     "network": "HBO", "tomatometer": 93, "audience_score": 80, "certified_fresh": True,
     "genres": ["Comedy", "Drama", "Mystery & Thriller"],
     "synopsis": "Various guests visit a tropical resort over the span of a week.",
     "poster": "/static/images/posters/the_white_lotus.jpg",
     "seasons": [
         {"number": s, "year": 2020 + s, "episodes": 7, "title": f"Season {s}",
          "synopsis": f"A new White Lotus resort, a new set of wealthy guests, and another death in season {s}."}
         for s in range(1, 4)
     ]},
    {"slug": "wednesday", "title": "Wednesday", "year_start": 2022, "year_end": 0,
     "network": "Netflix", "tomatometer": 73, "audience_score": 86, "certified_fresh": False,
     "genres": ["Comedy", "Mystery & Thriller", "Horror"],
     "synopsis": "Smart, sarcastic, and a little dead inside, Wednesday Addams investigates a murder spree while making new friends — and foes — at Nevermore Academy.",
     "poster": "/static/images/posters/wednesday.jpg",
     "seasons": [
         {"number": 1, "year": 2022, "episodes": 8, "title": "Season 1",
          "synopsis": "Wednesday arrives at Nevermore and begins solving a string of monstrous murders."},
     ]},
    {"slug": "the_mandalorian", "title": "The Mandalorian", "year_start": 2019, "year_end": 0,
     "network": "Disney+", "tomatometer": 91, "audience_score": 89, "certified_fresh": True,
     "genres": ["Sci-Fi", "Adventure", "Action", "Fantasy"],
     "synopsis": "After the fall of the Empire, a lone gunfighter makes his way through the lawless galaxy with his foundling, Grogu.",
     "poster": "/static/images/posters/the_mandalorian.jpg",
     "seasons": [
         {"number": s, "year": 2018 + s, "episodes": 8, "title": f"Season {s}",
          "synopsis": f"The Mandalorian's bounty hunt in season {s}."}
         for s in range(1, 4)
     ]},
    {"slug": "yellowstone", "title": "Yellowstone", "year_start": 2018, "year_end": 2024,
     "network": "Paramount+", "tomatometer": 79, "audience_score": 84, "certified_fresh": False,
     "genres": ["Drama", "Western"],
     "synopsis": "A ranching family in Montana faces off against others encroaching on their land.",
     "poster": "/static/images/posters/yellowstone.jpg",
     "seasons": [
         {"number": s, "year": 2017 + s, "episodes": 10, "title": f"Season {s}",
          "synopsis": f"The Duttons defend their ranch in season {s}."}
         for s in range(1, 6)
     ]},
    {"slug": "breaking_bad", "title": "Breaking Bad", "year_start": 2008, "year_end": 2013,
     "network": "AMC", "tomatometer": 96, "audience_score": 98, "certified_fresh": True,
     "genres": ["Crime", "Drama", "Mystery & Thriller"],
     "synopsis": "A high school chemistry teacher diagnosed with cancer turns to making and selling methamphetamine.",
     "poster": "/static/images/posters/breaking_bad.jpg",
     "seasons": [
         {"number": s, "year": 2007 + s, "episodes": 13, "title": f"Season {s}",
          "synopsis": f"Walter White descends further in season {s}."}
         for s in range(1, 6)
     ]},
    {"slug": "game_of_thrones", "title": "Game of Thrones", "year_start": 2011, "year_end": 2019,
     "network": "HBO", "tomatometer": 88, "audience_score": 84, "certified_fresh": True,
     "genres": ["Drama", "Fantasy", "Action", "Adventure"],
     "synopsis": "Nine noble families fight for control over the lands of Westeros, while an ancient enemy returns after being dormant for millennia.",
     "poster": "/static/images/posters/game_of_thrones.jpg",
     "seasons": [
         {"number": s, "year": 2010 + s, "episodes": 10, "title": f"Season {s}",
          "synopsis": f"Westeros descends further into war in season {s}."}
         for s in range(1, 9)
     ]},
    {"slug": "the_boys", "title": "The Boys", "year_start": 2019, "year_end": 0,
     "network": "Prime Video", "tomatometer": 93, "audience_score": 87, "certified_fresh": True,
     "genres": ["Action", "Comedy", "Crime", "Drama"],
     "synopsis": "A group of vigilantes set out to take down corrupt superheroes who abuse their abilities.",
     "poster": "/static/images/posters/the_boys.jpg",
     "seasons": [
         {"number": s, "year": 2018 + s, "episodes": 8, "title": f"Season {s}",
          "synopsis": f"The Boys vs. Vought in season {s}."}
         for s in range(1, 5)
     ]},
    {"slug": "abbott_elementary", "title": "Abbott Elementary", "year_start": 2021, "year_end": 0,
     "network": "ABC", "tomatometer": 96, "audience_score": 86, "certified_fresh": True,
     "genres": ["Comedy"],
     "synopsis": "A workplace mockumentary about the unsung heroes of an underfunded Philadelphia public school.",
     "poster": "/static/images/posters/abbott_elementary.jpg",
     "seasons": [
         {"number": s, "year": 2020 + s, "episodes": 22, "title": f"Season {s}",
          "synopsis": f"Abbott Elementary teachers tackle a new year in season {s}."}
         for s in range(1, 5)
     ]},
]


# ──────────────────────────────────────────────
# Curated movie lists — public editorial lists
# ──────────────────────────────────────────────

MOVIE_LISTS = [
    {"slug": "best_picture_winners", "title": "Best Picture Winners of the 21st Century",
     "description": "The Academy Award winners for Best Picture from the year 2000 onwards.",
     "tag": "awards",
     "movie_filter": lambda m: m.tomatometer >= 90 and m.year >= 2000,
     "limit": 20},
    {"slug": "best_certified_fresh_2024", "title": "The Best Certified Fresh Movies of 2024",
     "description": "Every Certified Fresh release from 2024, ranked.",
     "tag": "year",
     "movie_filter": lambda m: m.year == 2024 and m.certified_fresh,
     "limit": 30},
    {"slug": "best_certified_fresh_2025", "title": "The Best Certified Fresh Movies of 2025",
     "description": "Every Certified Fresh release from 2025, ranked.",
     "tag": "year",
     "movie_filter": lambda m: m.year == 2025 and m.certified_fresh,
     "limit": 30},
    {"slug": "best_certified_fresh_2023", "title": "The Best Certified Fresh Movies of 2023",
     "description": "Every Certified Fresh release from 2023, ranked.",
     "tag": "year",
     "movie_filter": lambda m: m.year == 2023 and m.certified_fresh,
     "limit": 30},
    {"slug": "best_horror_movies", "title": "100 Best Horror Movies",
     "description": "From classic dread to modern terror.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "horror" for g in m.genres),
     "limit": 40},
    {"slug": "best_comedies", "title": "Funniest Movies of All Time",
     "description": "Critic-approved comedies that still land.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "comedy" for g in m.genres),
     "limit": 40},
    {"slug": "best_animation", "title": "Greatest Animated Films",
     "description": "A century of animated achievement.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "animation" for g in m.genres),
     "limit": 30},
    {"slug": "best_sci_fi", "title": "Top Sci-Fi Movies",
     "description": "Worlds beyond our own, ranked by the Tomatometer.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "sci_fi" for g in m.genres),
     "limit": 40},
    {"slug": "best_action_movies", "title": "Highest-Rated Action Movies",
     "description": "Explosive, exhilarating, Certified Fresh.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "action" for g in m.genres),
     "limit": 40},
    {"slug": "best_drama", "title": "Greatest Dramas Ever",
     "description": "Powerhouse performances and unforgettable stories.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "drama" for g in m.genres),
     "limit": 40},
    {"slug": "marvel_ranked", "title": "Every Marvel Cinematic Universe Movie, Ranked",
     "description": "All MCU entries from worst to best by Tomatometer.",
     "tag": "franchise",
     "movie_filter": lambda m: "Walt Disney" in (m.studio or "") or "Marvel" in (m.title or ""),
     "limit": 35},
    {"slug": "summer_blockbusters", "title": "Best Summer Blockbusters",
     "description": "The big-budget movies that defined summer.",
     "tag": "season",
     "movie_filter": lambda m: m.tomatometer >= 80 and any(g.slug in ("action","adventure","sci_fi") for g in m.genres),
     "limit": 30},
    {"slug": "indie_picks", "title": "Best Indie Films",
     "description": "Independent gems worth your time.",
     "tag": "indie",
     "movie_filter": lambda m: m.tomatometer >= 85 and m.box_office and ("$1" in (m.box_office or "") or "$2" in (m.box_office or "")) and "M" in (m.box_office or ""),
     "limit": 30},
    {"slug": "streaming_now_netflix", "title": "Best Movies on Netflix",
     "description": "Top-rated titles streaming on Netflix right now.",
     "tag": "platform",
     "movie_filter": lambda m: "Netflix" in (m.streaming_platform or ""),
     "limit": 40},
    {"slug": "streaming_now_max", "title": "Best Movies on Max",
     "description": "Top-rated titles streaming on Max right now.",
     "tag": "platform",
     "movie_filter": lambda m: "Max" in (m.streaming_platform or ""),
     "limit": 40},
    {"slug": "streaming_now_disney", "title": "Best Movies on Disney+",
     "description": "Top-rated titles streaming on Disney+ right now.",
     "tag": "platform",
     "movie_filter": lambda m: "Disney+" in (m.streaming_platform or ""),
     "limit": 40},
    {"slug": "streaming_now_apple", "title": "Best Movies on Apple TV+",
     "description": "Top-rated titles streaming on Apple TV+ right now.",
     "tag": "platform",
     "movie_filter": lambda m: "Apple TV+" in (m.streaming_platform or ""),
     "limit": 40},
    {"slug": "streaming_now_prime", "title": "Best Movies on Prime Video",
     "description": "Top-rated titles streaming on Prime Video right now.",
     "tag": "platform",
     "movie_filter": lambda m: "Prime Video" in (m.streaming_platform or ""),
     "limit": 40},
    {"slug": "feel_good_picks", "title": "Feel-Good Movies for Tough Days",
     "description": "Hand-picked uplifters when you need them most.",
     "tag": "mood",
     "movie_filter": lambda m: m.audience_score >= 85 and any(g.slug in ("comedy","kids_family","romance","musical") for g in m.genres),
     "limit": 30},
    {"slug": "must_see_2026", "title": "Most Anticipated Movies of 2026",
     "description": "What's hitting theaters and streaming next.",
     "tag": "year",
     "movie_filter": lambda m: m.year == 2026,
     "limit": 30},
    {"slug": "best_thrillers", "title": "Best Mystery & Thriller Movies",
     "description": "Edge-of-your-seat selections from the genre.",
     "tag": "genre",
     "movie_filter": lambda m: any(g.slug == "mystery_thriller" for g in m.genres),
     "limit": 40},
    {"slug": "directors_finest", "title": "Directors' Finest Hours",
     "description": "The highest-rated film by each celebrated filmmaker on Rotten Tomatoes.",
     "tag": "director",
     "movie_filter": lambda m: m.certified_fresh and m.tomatometer >= 95,
     "limit": 40},
]


# ──────────────────────────────────────────────
# News articles — auto-generated headlines per high-profile movie
# ──────────────────────────────────────────────

NEWS_CATEGORIES = ["Movies", "TV", "Awards", "Box Office", "Streaming", "Trailers", "Interviews"]

NEWS_AUTHORS = [
    ("Joel Meares", "joel_meares"),
    ("Alex Vo", "alex_vo"),
    ("Sandra Gonzalez", "sandra_gonzalez"),
    ("Jacqueline Coley", "jacqueline_coley"),
    ("Tim Ryan", "tim_ryan"),
    ("Cristina Escobar", "cristina_escobar"),
]


def build_news_articles(movies_by_slug, tv_shows):
    """Generate ~40 news articles derived from the movie + TV catalogs."""
    out = []
    # 1 article per featured movie (top 30 by tomatometer)
    top = sorted(movies_by_slug.values(), key=lambda m: (-m.tomatometer, m.title))[:30]
    for i, m in enumerate(top):
        author, author_slug = NEWS_AUTHORS[i % len(NEWS_AUTHORS)]
        out.append({
            "slug": f"why_{m.slug}_is_a_must_see",
            "title": f"Why \"{m.title}\" is a Must-See — Critics Sound Off",
            "summary": f"With a Tomatometer score of {m.tomatometer}% and audience score of {m.audience_score}%, {m.title} is one of the year's most talked-about releases. Here's what the critics are saying.",
            "body": (
                f"{m.title} ({m.year}) has captured both critics and audiences. "
                f"The {m.pg_rating} {(', '.join(g.name for g in m.genres) if m.genres else 'film')} earned a {m.tomatometer}% Tomatometer score and a {m.audience_score}% audience score. "
                f"{m.consensus} "
                f"Directed by {m.director_name or 'an acclaimed filmmaker'}, the film follows: {m.synopsis[:240]}... "
                f"Below, we've gathered reactions, behind-the-scenes notes, and where you can watch it next."
            ),
            "image": m.poster_image,
            "category": "Movies",
            "author": author,
            "author_slug": author_slug,
            "tag_movie_slug": m.slug,
        })
    # 1 article per TV show
    for i, tv in enumerate(tv_shows):
        author, author_slug = NEWS_AUTHORS[(i + 3) % len(NEWS_AUTHORS)]
        out.append({
            "slug": f"recap_{tv['slug']}_season",
            "title": f"\"{tv['title']}\" Returns: Everything You Need to Know",
            "summary": f"{tv['title']} is back on {tv['network']} with a Tomatometer score of {tv['tomatometer']}%.",
            "body": (
                f"{tv['title']} continues its critically acclaimed run on {tv['network']}. "
                f"With a Tomatometer of {tv['tomatometer']}% and audience score of {tv['audience_score']}%, "
                f"the series remains one of the platform's flagship dramas. "
                f"{tv['synopsis']} "
                f"Here's a complete look at where each character stands and what to expect."
            ),
            "image": tv["poster"],
            "category": "TV",
            "author": author,
            "author_slug": author_slug,
            "tag_movie_slug": "",
        })
    # Awards-season + box-office takes
    award_picks = sorted(movies_by_slug.values(), key=lambda m: (-m.tomatometer, m.title))[:5]
    for i, m in enumerate(award_picks):
        author, author_slug = NEWS_AUTHORS[(i + 1) % len(NEWS_AUTHORS)]
        out.append({
            "slug": f"oscars_outlook_{m.slug}",
            "title": f"Oscar Outlook: Is \"{m.title}\" a Best Picture Contender?",
            "summary": f"With {m.tomatometer}% on the Tomatometer, {m.title} is shaping up to be a major awards-season player.",
            "body": (
                f"As awards season heats up, {m.title} is increasingly mentioned as a Best Picture contender. "
                f"The film, directed by {m.director_name or 'an acclaimed filmmaker'}, holds a {m.tomatometer}% Tomatometer score "
                f"and a {m.audience_score}% audience score. "
                f"{m.consensus} "
                f"Voters tend to reward films that combine critical acclaim with cultural impact — and {m.title} has both."
            ),
            "image": m.poster_image,
            "category": "Awards",
            "author": author,
            "author_slug": author_slug,
            "tag_movie_slug": m.slug,
        })
    return out


# ──────────────────────────────────────────────
# Podcasts
# ──────────────────────────────────────────────

PODCASTS = [
    {"slug": "the_rotten_tomatoes_podcast", "title": "The Rotten Tomatoes Podcast",
     "host": "Mark Ellis, Jacqueline Coley",
     "description": "A weekly look at the freshest (and most rotten) movies and TV.",
     "image": "/static/images/podcasts/rt_podcast.jpg",
     "episodes": 24},
    {"slug": "weekend_binge", "title": "Weekend Binge",
     "host": "Joel Meares",
     "description": "Streaming recommendations for your weekend, delivered every Friday.",
     "image": "/static/images/podcasts/weekend_binge.jpg",
     "episodes": 20},
    {"slug": "the_horror_show", "title": "The Horror Show",
     "host": "Cristina Escobar",
     "description": "Deep dives into the year's scariest films.",
     "image": "/static/images/podcasts/the_horror_show.jpg",
     "episodes": 16},
    {"slug": "awards_circuit", "title": "Awards Circuit",
     "host": "Jacqueline Coley, Tim Ryan",
     "description": "Predictions, contenders, and analysis from across the awards landscape.",
     "image": "/static/images/podcasts/awards_circuit.jpg",
     "episodes": 18},
    {"slug": "tv_talk", "title": "TV Talk",
     "host": "Alex Vo",
     "description": "Weekly recaps of the prestige shows everyone's watching.",
     "image": "/static/images/podcasts/tv_talk.jpg",
     "episodes": 22},
    {"slug": "indie_spotlight", "title": "Indie Spotlight",
     "host": "Sandra Gonzalez",
     "description": "The best of independent cinema, deep cuts and festival gems included.",
     "image": "/static/images/podcasts/indie_spotlight.jpg",
     "episodes": 14},
]


# ──────────────────────────────────────────────
# Sweepstakes
# ──────────────────────────────────────────────

SWEEPSTAKES = [
    {"slug": "win_avatar_screening", "title": "Win Tickets to an Advance Screening of Avatar: Fire and Ash",
     "prize": "Two tickets to the premiere in LA, plus hotel and airfare.",
     "description": "Enter for your chance to attend the world premiere of Avatar: Fire and Ash.",
     "image": "/static/images/posters/avatar_fire_and_ash.jpg",
     "ends_offset_days": 14},
    {"slug": "best_picture_swag", "title": "Win Awards Season Swag",
     "prize": "Limited-edition Best Picture swag bag worth $500.",
     "description": "Enter our awards season giveaway for a chance to win a swag bag full of nominee gear.",
     "image": "/static/images/posters/oppenheimer_2023.jpg",
     "ends_offset_days": 28},
    {"slug": "summer_blockbuster_kit", "title": "Win a Summer Blockbuster Movie Kit",
     "prize": "Year of free streaming + $500 AMC gift card + popcorn maker.",
     "description": "Be ready for every summer release with a streaming subscription, theater gift card, and home popcorn maker.",
     "image": "/static/images/posters/top_gun_maverick.jpg",
     "ends_offset_days": 21},
    {"slug": "horror_marathon_kit", "title": "Win a Halloween Horror Marathon Kit",
     "prize": "Horror Blu-ray collection + smart TV.",
     "description": "Enter to win the ultimate horror marathon kit, just in time for spooky season.",
     "image": "/static/images/posters/nosferatu_2024.jpg",
     "ends_offset_days": 10},
    {"slug": "win_dune_collectors", "title": "Win the Dune Collector's Edition",
     "prize": "Dune: Part One + Part Two 4K SteelBook + signed poster.",
     "description": "Enter for a chance to win the limited Dune collector's edition.",
     "image": "/static/images/posters/dune_part_two.jpg",
     "ends_offset_days": 7},
]


# ──────────────────────────────────────────────
# Polls — community polls on the homepage
# ──────────────────────────────────────────────

POLLS = [
    {"slug": "best_picture_2024_audience", "question": "Which 2024 film should win Best Picture?",
     "options": ["Dune: Part Two", "Inside Out 2", "The Wild Robot", "Wicked", "Nosferatu"],
     "votes": [3421, 2890, 2104, 1812, 1503], "ends_offset_days": 30},
    {"slug": "best_horror_2024", "question": "Best Horror Movie of 2024?",
     "options": ["Nosferatu", "Oddity", "Longlegs", "The Substance", "MaXXXine"],
     "votes": [1820, 1654, 1432, 1389, 1102], "ends_offset_days": 14},
    {"slug": "favorite_marvel_phase4", "question": "Favorite Marvel Phase 4/5 Movie?",
     "options": ["Spider-Man: No Way Home", "Deadpool & Wolverine", "Guardians of the Galaxy Vol. 3", "The Fantastic Four: First Steps", "Thunderbolts"],
     "votes": [4128, 3995, 2104, 1872, 1294], "ends_offset_days": 21},
    {"slug": "most_anticipated_2026", "question": "Which 2026 release are you most excited for?",
     "options": ["Avatar: Fire and Ash", "Avengers: Doomsday", "The Bone Temple", "The Mandalorian & Grogu", "Mortal Kombat 2"],
     "votes": [4521, 3892, 2104, 1875, 1102], "ends_offset_days": 60},
    {"slug": "best_streaming_2024", "question": "Best Streaming-Only Movie of 2024?",
     "options": ["The Wild Robot", "Hit Man", "Rebel Ridge", "Will & Harper", "It's What's Inside"],
     "votes": [2104, 1892, 1432, 1102, 894], "ends_offset_days": 14},
    {"slug": "best_franchise_2025", "question": "Best Franchise Continuation in 2025?",
     "options": ["Mission: Impossible — The Final Reckoning", "Jurassic World Rebirth", "Tron: Ares", "Captain America: Brave New World", "Superman"],
     "votes": [3892, 2104, 1875, 1432, 2750], "ends_offset_days": 21},
]


# ──────────────────────────────────────────────
# Awards — yearly winners (Best Picture, Director, Lead Actor, Lead Actress)
# ──────────────────────────────────────────────

AWARD_CATEGORIES = ["Best Picture", "Best Director", "Best Actor", "Best Actress", "Best Animated Feature"]


def build_awards(movies, persons):
    """For each year, pick top-rated movie as Best Picture and director."""
    awards = []
    by_year = {}
    for m in movies:
        by_year.setdefault(m.year, []).append(m)
    for year, mlist in sorted(by_year.items()):
        if year < 2000 or year > 2026:
            continue
        ranked = sorted(mlist, key=lambda x: (-x.tomatometer, -x.audience_score, x.title))
        top = ranked[0] if ranked else None
        if not top:
            continue
        awards.append({"year": year, "category": "Best Picture", "movie_slug": top.slug, "winner": True})
        # Pick directors from MovieCast for that movie
        for cast in top.cast_members:
            if cast.role_type == "director":
                awards.append({"year": year, "category": "Best Director", "person_slug": cast.person.slug, "movie_slug": top.slug, "winner": True})
                break
        # Lead actor = billing_order 1
        actors_sorted = [c for c in top.cast_members if c.role_type == "actor"]
        if actors_sorted:
            actors_sorted.sort(key=lambda c: c.billing_order)
            awards.append({"year": year, "category": "Best Actor", "person_slug": actors_sorted[0].person.slug, "movie_slug": top.slug, "winner": True})
            if len(actors_sorted) > 1:
                awards.append({"year": year, "category": "Best Actress", "person_slug": actors_sorted[1].person.slug, "movie_slug": top.slug, "winner": True})
        # Best Animated Feature
        animated = [m for m in mlist if any(g.slug == "animation" for g in m.genres)]
        if animated:
            animated.sort(key=lambda x: (-x.tomatometer, x.title))
            awards.append({"year": year, "category": "Best Animated Feature", "movie_slug": animated[0].slug, "winner": True})
    return awards


# ──────────────────────────────────────────────
# Critics — promote critic names from CRITIC_REVIEWS to a Critic table
# ──────────────────────────────────────────────

def build_critics(critic_reviews_seed):
    """Derive a stable list of critic dicts from CRITIC_REVIEWS rows."""
    seen = {}
    for r in critic_reviews_seed:
        name = r["critic"].strip()
        pub = r["publication"].strip()
        key = (name, pub)
        if key in seen:
            continue
        slug = name.lower().replace(" ", "_").replace(".", "").replace("'", "").replace("-", "_")
        slug = "".join(ch for ch in slug if ch.isalnum() or ch == "_")
        if not slug or slug in {v["slug"] for v in seen.values()}:
            # Disambiguate by appending hash of publication.
            slug = f"{slug}_{hashlib.md5(pub.encode()).hexdigest()[:6]}"
        seen[key] = {
            "name": name,
            "slug": slug,
            "publication": pub,
            "bio": f"{name} writes for {pub}.",
            "photo": "",
            "top_critic": True if any(t in pub for t in ("New York Times", "Variety", "Hollywood Reporter", "Empire", "Time", "Guardian", "BBC", "Washington Post")) else False,
        }
    # Stable ordering: by slug
    return sorted(seen.values(), key=lambda c: c["slug"])


# ──────────────────────────────────────────────
# Photos — derive a Photo row per movie from poster + headshots of its cast
# ──────────────────────────────────────────────

def build_photos(movies, cast_index):
    """For each movie, generate up to 4 photo rows (poster + 3 cast headshots)."""
    photos = []
    for m in movies:
        if m.poster_image:
            photos.append({
                "movie_slug": m.slug,
                "image": m.poster_image,
                "caption": f"Theatrical poster for {m.title}",
                "kind": "poster",
                "order": 0,
            })
        related_cast = [c for c in m.cast_members if c.role_type == "actor"][:3]
        for i, c in enumerate(related_cast):
            if c.person and c.person.photo:
                photos.append({
                    "movie_slug": m.slug,
                    "image": c.person.photo,
                    "caption": f"{c.person.name} as {c.character_name or 'a cast member'} in {m.title}",
                    "kind": "still",
                    "order": i + 1,
                })
    return photos
