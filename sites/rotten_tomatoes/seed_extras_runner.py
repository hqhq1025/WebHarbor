"""Seeder for the rotten_tomatoes deepening tables.

Called from app.py `init_db()` right after the base seed has run. Reads the
data definitions in `seed_extras.py` and writes deterministic rows into the
new tables defined in `app_ext.py`.
"""
from datetime import datetime, timedelta

from seed_extras import (
    REF_DATE, TV_SHOWS, MOVIE_LISTS, build_news_articles,
    PODCASTS, SWEEPSTAKES, POLLS, build_awards, build_critics, build_photos,
)
from seed_data import CRITIC_REVIEWS as RAW_CRITIC_REVIEWS, USERS as BENCH_USERS


def seed_extras(db, base_models, ext_models):
    """Populate every extension table."""
    User = base_models["User"]
    Movie = base_models["Movie"]
    Person = base_models["Person"]
    AudienceReview = base_models["AudienceReview"]

    TVShow = ext_models["TVShow"]
    Season = ext_models["Season"]
    Episode = ext_models["Episode"]
    Critic = ext_models["Critic"]
    MovieList = ext_models["MovieList"]
    MovieListItem = ext_models["MovieListItem"]
    NewsArticle = ext_models["NewsArticle"]
    NewsComment = ext_models["NewsComment"]
    Podcast = ext_models["Podcast"]
    PodcastEpisode = ext_models["PodcastEpisode"]
    Sweepstakes = ext_models["Sweepstakes"]
    Poll = ext_models["Poll"]
    PollOption = ext_models["PollOption"]
    WantToSee = ext_models["WantToSee"]
    Watched = ext_models["Watched"]
    Photo = ext_models["Photo"]
    Award = ext_models["Award"]

    # Idempotency — bail if any major extension table is already populated.
    if Critic.query.count() > 0 or TVShow.query.count() > 0:
        return

    # ── TV Shows ───────────────────────────────────────────────────
    for entry in sorted(TV_SHOWS, key=lambda t: t["slug"]):
        tv = TVShow(
            slug=entry["slug"],
            title=entry["title"],
            year_start=entry["year_start"],
            year_end=entry["year_end"],
            network=entry["network"],
            tomatometer=entry["tomatometer"],
            audience_score=entry["audience_score"],
            certified_fresh=entry["certified_fresh"],
            synopsis=entry["synopsis"],
            poster=entry["poster"],
            genre_text=", ".join(entry["genres"]),
        )
        db.session.add(tv)
        db.session.flush()
        for s in entry["seasons"]:
            season = Season(
                tv_id=tv.id,
                number=s["number"],
                title=s["title"],
                year=s["year"],
                synopsis=s["synopsis"],
                episode_count=s["episodes"],
            )
            db.session.add(season)
            db.session.flush()
            for ep_n in range(1, s["episodes"] + 1):
                ep = Episode(
                    season_id=season.id,
                    number=ep_n,
                    title=f"Episode {ep_n}",
                    synopsis=f"Synopsis for {entry['title']} season {s['number']} episode {ep_n}.",
                    air_date=f"{s['year']:04d}-{((ep_n - 1) % 12) + 1:02d}-15",
                    tomatometer=max(60, (entry["tomatometer"] + (ep_n * 7) % 11) % 101) or entry["tomatometer"],
                )
                db.session.add(ep)
    db.session.flush()

    # ── Critics — derived from CRITIC_REVIEWS rows ────────────────
    critics_data = build_critics(RAW_CRITIC_REVIEWS)
    for c in critics_data:
        db.session.add(Critic(
            slug=c["slug"], name=c["name"], publication=c["publication"],
            bio=c["bio"], photo=c["photo"], top_critic=c["top_critic"],
        ))
    db.session.flush()

    # ── Movie lists ───────────────────────────────────────────────
    all_movies = Movie.query.order_by(Movie.id).all()
    movies_by_slug = {m.slug: m for m in all_movies}
    for lst_def in MOVIE_LISTS:
        # Deterministic filter then ranking by tomatometer desc, title asc.
        matching = [m for m in all_movies if lst_def["movie_filter"](m)]
        matching.sort(key=lambda m: (-m.tomatometer, -m.audience_score, m.title))
        matching = matching[: lst_def["limit"]]
        lst = MovieList(
            slug=lst_def["slug"],
            title=lst_def["title"],
            description=lst_def["description"],
            owner_id=None,
            is_public=True,
            tag=lst_def["tag"],
            created_at=REF_DATE,
        )
        db.session.add(lst)
        db.session.flush()
        for order, m in enumerate(matching, start=1):
            db.session.add(MovieListItem(list_id=lst.id, movie_id=m.id, order=order))
    db.session.flush()

    # ── News articles ─────────────────────────────────────────────
    articles = build_news_articles(movies_by_slug, TV_SHOWS)
    for i, art in enumerate(articles):
        pub_at = REF_DATE - timedelta(days=i, hours=(i * 3) % 24)
        tag_id = None
        if art.get("tag_movie_slug"):
            mv = movies_by_slug.get(art["tag_movie_slug"])
            if mv:
                tag_id = mv.id
        db.session.add(NewsArticle(
            slug=art["slug"], title=art["title"], summary=art["summary"],
            body=art["body"], author=art["author"], author_slug=art["author_slug"],
            image=art["image"], category=art["category"],
            published_at=pub_at, tag_movie_id=tag_id,
        ))
    db.session.flush()

    # ── Podcasts + episodes ───────────────────────────────────────
    for p in PODCASTS:
        pod = Podcast(slug=p["slug"], title=p["title"], host=p["host"],
                      description=p["description"], image=p["image"])
        db.session.add(pod)
        db.session.flush()
        for n in range(p["episodes"], 0, -1):
            pub_at = REF_DATE - timedelta(days=(p["episodes"] - n) * 7)
            db.session.add(PodcastEpisode(
                podcast_id=pod.id,
                number=n,
                title=f"{p['title']} — Episode {n}",
                description=f"In episode {n}, the hosts discuss the week in movies and TV.",
                duration_min=30 + (n * 3) % 30,
                published_at=pub_at,
            ))
    db.session.flush()

    # ── Sweepstakes ───────────────────────────────────────────────
    for sw in SWEEPSTAKES:
        ends = (REF_DATE + timedelta(days=sw["ends_offset_days"])).strftime("%Y-%m-%d")
        db.session.add(Sweepstakes(
            slug=sw["slug"], title=sw["title"], prize=sw["prize"],
            description=sw["description"], image=sw["image"], ends_on=ends,
        ))
    db.session.flush()

    # ── Polls + options ───────────────────────────────────────────
    for p in POLLS:
        ends = (REF_DATE + timedelta(days=p["ends_offset_days"])).strftime("%Y-%m-%d")
        poll = Poll(slug=p["slug"], question=p["question"], ends_on=ends)
        db.session.add(poll)
        db.session.flush()
        for idx, opt_text in enumerate(p["options"]):
            db.session.add(PollOption(poll_id=poll.id, text=opt_text,
                                       votes=p["votes"][idx]))
    db.session.flush()

    # ── Awards ────────────────────────────────────────────────────
    persons_by_slug = {p.slug: p for p in Person.query.all()}
    awards = build_awards(all_movies, persons_by_slug.values())
    for a in awards:
        mid = movies_by_slug[a["movie_slug"]].id if a.get("movie_slug") in movies_by_slug else None
        pid = persons_by_slug[a["person_slug"]].id if a.get("person_slug") in persons_by_slug else None
        db.session.add(Award(
            year=a["year"], category=a["category"],
            movie_id=mid, person_id=pid, winner=a.get("winner", False),
        ))
    db.session.flush()

    # ── Photos (poster + actor headshots per movie) ───────────────
    photo_rows = build_photos(all_movies, None)
    for ph in photo_rows:
        mv = movies_by_slug.get(ph["movie_slug"])
        if not mv:
            continue
        db.session.add(Photo(
            movie_id=mv.id, image=ph["image"], caption=ph["caption"],
            kind=ph["kind"], order=ph["order"],
        ))
    db.session.flush()

    # ── Benchmark user state on the new tables ────────────────────
    bench_user_map = {u.name: u for u in User.query.order_by(User.id).all()}
    # WantToSee — 5 movies per benchmark user, distinct from watchlist
    wts_picks = {
        "alice_jones": ["nosferatu_2024", "the_substance", "wicked_2024", "the_brutalist", "anora"],
        "bob_clark":   ["dune_part_two", "the_dark_knight", "interstellar_2014", "oppenheimer_2023", "blade_runner_2049"],
        "carol_davis": ["barbie", "everything_everywhere_all_at_once", "oddity", "the_substance", "anora"],
        "david_kim":   ["avengers_endgame", "deadpool_and_wolverine", "superman_2025", "the_fantastic_four_first_steps", "top_gun_maverick"],
    }
    for uname, slugs in wts_picks.items():
        user = bench_user_map.get(uname)
        if not user:
            continue
        for idx, s in enumerate(slugs):
            mv = movies_by_slug.get(s)
            if not mv:
                continue
            db.session.add(WantToSee(
                user_id=user.id, movie_id=mv.id,
                added_at=REF_DATE - timedelta(days=idx),
            ))

    # Watched — 4 movies per benchmark user
    watched_picks = {
        "alice_jones": ["parasite_2019", "everything_everywhere_all_at_once", "barbie"],
        "bob_clark":   ["the_dark_knight", "top_gun_maverick", "interstellar_2014", "godzilla_minus_one"],
        "carol_davis": ["the_substance", "nosferatu_2024", "oddity", "anora"],
        "david_kim":   ["avengers_endgame", "godzilla_minus_one", "deadpool_and_wolverine"],
    }
    for uname, slugs in watched_picks.items():
        user = bench_user_map.get(uname)
        if not user:
            continue
        for idx, s in enumerate(slugs):
            mv = movies_by_slug.get(s)
            if not mv:
                continue
            db.session.add(Watched(
                user_id=user.id, movie_id=mv.id,
                added_at=REF_DATE - timedelta(days=idx, hours=2),
            ))

    db.session.commit()
