"""Seed data orchestrator for fandom mirror.

Critical: every seed function is gated as a whole. A no-op db.session.commit()
still bumps SQLite metadata and breaks the byte-identical reset invariant.

This module is imported from app.py at module-bottom AFTER all models are
defined, so importing from app at function call time is safe and avoids
circular-import crashes (which occur when seed_data tries to import models
at module-load time and app.py is still being initialized as __main__).
"""
from datetime import datetime, timedelta
import json

from seed_articles_mcu import MCU_ARTICLES, MCU_CATEGORIES, MCU_TALK
from seed_articles_starwars import SW_ARTICLES, SW_CATEGORIES, SW_TALK
from seed_articles_genshin import GS_ARTICLES, GS_CATEGORIES, GS_TALK


WIKI_DEFS = [
    dict(
        slug="mcu",
        name="Marvel Cinematic Universe Wiki",
        tagline="The Marvel Cinematic Universe Wiki — the encyclopedia about the MCU.",
        accent="#ed1d24",
        hero_image="/static/images/mcu_hero.jpg",
        description=(
            "The Marvel Cinematic Universe Wiki is a comprehensive encyclopedia "
            "covering Marvel Studios films, Disney+ series, characters, locations, "
            "items, and behind-the-scenes content across the Infinity Saga and "
            "the Multiverse Saga."
        ),
        featured_article_slug="Tony_Stark",
        article_count=63,
        page_count=215,
        discussion_count=47,
        members_count=12840,
    ),
    dict(
        slug="starwars",
        name="Wookieepedia",
        tagline="Wookieepedia — the Star Wars Wiki anyone can edit.",
        accent="#ffe81f",
        hero_image="/static/images/sw_hero.jpg",
        description=(
            "Wookieepedia is the Star Wars wiki — covering films, TV series, "
            "novels, comics, and games across the Skywalker Saga, the High "
            "Republic era, and beyond."
        ),
        featured_article_slug="Luke_Skywalker",
        article_count=66,
        page_count=240,
        discussion_count=58,
        members_count=18230,
    ),
    dict(
        slug="genshin",
        name="Genshin Impact Wiki",
        tagline="Genshin Impact Wiki — characters, weapons, regions, and lore of Teyvat.",
        accent="#4a90e2",
        hero_image="/static/images/gs_hero.jpg",
        description=(
            "The Genshin Impact Wiki is the community-driven reference for HoYoverse's "
            "open-world action RPG, with full coverage of playable characters, "
            "weapons, regions, quests, and events."
        ),
        featured_article_slug="Diluc",
        article_count=62,
        page_count=210,
        discussion_count=51,
        members_count=9420,
    ),
]


# Deterministic timestamp anchor so seeded data is reproducible.
# All revision timestamps are derived from this anchor minus integer days.
BASE_TS = datetime(2026, 5, 1, 12, 0, 0)


def _wiki_seed():
    from app import db, Wiki
    if Wiki.query.count() > 0:
        return
    for d in WIKI_DEFS:
        w = Wiki(**d)
        db.session.add(w)
    db.session.commit()


def _categories_seed():
    from app import db, Wiki, Category, slugify
    if Category.query.count() > 0:
        return
    for wiki_slug, cats in [
        ("mcu", MCU_CATEGORIES),
        ("starwars", SW_CATEGORIES),
        ("genshin", GS_CATEGORIES),
    ]:
        w = Wiki.query.filter_by(slug=wiki_slug).first()
        for c in cats:
            db.session.add(Category(
                wiki_id=w.id, name=c["name"], slug=slugify(c["name"]),
                parent_slug=slugify(c.get("parent", "") or ""),
                description=c.get("description", ""),
            ))
    db.session.commit()


def _articles_seed():
    from app import db, Wiki, Article, Category, ArticleCategory, slugify
    if Article.query.count() > 0:
        return
    for wiki_slug, articles in [
        ("mcu", MCU_ARTICLES),
        ("starwars", SW_ARTICLES),
        ("genshin", GS_ARTICLES),
    ]:
        w = Wiki.query.filter_by(slug=wiki_slug).first()
        seen_slugs = set()
        for i, art in enumerate(articles):
            title = art["title"]
            slug = slugify(title)
            if slug in seen_slugs:
                # Skip silently — duplicate within wiki would violate UNIQUE
                continue
            seen_slugs.add(slug)
            created = BASE_TS - timedelta(days=art.get("age_days", 300) + i)
            updated = BASE_TS - timedelta(days=art.get("updated_days", 7) + (i % 5))
            a = Article(
                wiki_id=w.id,
                title=title,
                slug=slug,
                summary=(art.get("summary") or art.get("content", "")[:280]),
                content=art["content"],
                infobox_kind=art.get("infobox_kind", ""),
                infobox_json=json.dumps(art.get("infobox", {}), ensure_ascii=False),
                image=art.get("image", ""),
                created_at=created,
                updated_at=updated,
                view_count=art.get("views", 1200 + i * 37),
                is_featured=art.get("featured", False),
                namespace=art.get("namespace", "Main"),
            )
            db.session.add(a)
            db.session.flush()
            # Categories
            for cat_name in art.get("categories", []):
                cat = Category.query.filter_by(wiki_id=w.id, slug=slugify(cat_name)).first()
                if cat:
                    db.session.add(ArticleCategory(article_id=a.id, category_id=cat.id))
    db.session.commit()


def _revisions_seed():
    from app import db, Article, Revision
    if Revision.query.count() > 0:
        return
    # Each article gets 3-5 historical revisions ending at its current content.
    # Author labels rotate among a fixed pool of bot/anon/editor names so the
    # data is deterministic.
    EDITORS = [
        ("StarkFan42", "user", False),
        ("WikiBot", "bot", True),
        ("LucasCanon", "user", False),
        ("HoYoLore", "user", False),
        ("76.121.44.92", "anon", False),
        ("EnabranTain", "user", False),
        ("ShinyCelestia", "user", False),
        ("InfinityScribe", "user", False),
    ]
    articles = Article.query.all()
    for idx, a in enumerate(articles):
        n_rev = 3 + (idx % 4)  # 3..6 revisions
        # Older revisions = content with last N sections trimmed away
        full = a.content
        parts = full.split("\n\n")
        chunks = max(2, len(parts) // n_rev)
        for k in range(n_rev):
            stop = min(len(parts), chunks * (k + 1) + 1)
            content_at_k = "\n\n".join(parts[:stop]) if k < n_rev - 1 else full
            editor = EDITORS[(idx + k) % len(EDITORS)]
            label, kind, is_bot = editor
            # Anchor: oldest is older, newest is the article's updated_at
            ts = a.updated_at - timedelta(days=(n_rev - 1 - k) * 11 + (idx % 7))
            summary = [
                "Initial draft",
                "Expanded biography section",
                "Added infobox details",
                "Copy-edit and rephrasing",
                "Added references and cleaned formatting",
                "Reverted vandalism",
                "Updated after latest release",
            ][k % 7]
            rev = Revision(
                article_id=a.id,
                user_id=None,  # set after user seed if matchable
                author_label=label,
                summary=summary,
                content=content_at_k,
                minor=(k > 0 and k % 3 == 0),
                bot=is_bot,
                bytes_size=len(content_at_k.encode("utf-8")),
                bytes_delta=(len(content_at_k.encode("utf-8")) -
                             (len(parts[:stop-1]) and len("\n\n".join(parts[:stop-1]).encode("utf-8")) or 0)),
                timestamp=ts,
            )
            db.session.add(rev)
    db.session.commit()


def _polls_seed():
    from app import db, Wiki, Poll, PollVote
    if Poll.query.count() > 0:
        return
    poll_defs = [
        ("mcu", "Who is your favorite Avenger?",
         ["Iron Man", "Captain America", "Thor", "Black Widow", "Hulk", "Hawkeye"]),
        ("starwars", "Greatest Jedi of all time?",
         ["Luke Skywalker", "Yoda", "Obi-Wan Kenobi", "Mace Windu", "Ahsoka Tano"]),
        ("genshin", "Which region has the best music?",
         ["Mondstadt", "Liyue", "Inazuma", "Sumeru", "Fontaine", "Natlan"]),
    ]
    for slug, question, options in poll_defs:
        w = Wiki.query.filter_by(slug=slug).first()
        p = Poll(wiki_id=w.id, question=question,
                 options_json=json.dumps(options, ensure_ascii=False),
                 is_active=True)
        db.session.add(p)
    db.session.commit()
    # Pre-seed deterministic vote counts so the poll has tallies on first load.
    # We use anon votes (user_id=None) keyed off poll choice index.
    seeded_counts = {
        "mcu": [142, 89, 67, 51, 73, 22],
        "starwars": [98, 122, 81, 44, 76],
        "genshin": [54, 71, 88, 62, 47, 36],
    }
    polls = Poll.query.all()
    for p in polls:
        w = Wiki.query.get(p.wiki_id)
        counts = seeded_counts.get(w.slug, [])
        for i, c in enumerate(counts):
            for _ in range(c):
                db.session.add(PollVote(poll_id=p.id, choice_idx=i,
                                        user_id=None, timestamp=BASE_TS))
    db.session.commit()


def _talk_seed():
    from app import db, Wiki, Article, TalkPost, slugify
    if TalkPost.query.count() > 0:
        return
    for wiki_slug, posts in [
        ("mcu", MCU_TALK),
        ("starwars", SW_TALK),
        ("genshin", GS_TALK),
    ]:
        w = Wiki.query.filter_by(slug=wiki_slug).first()
        for tp in posts:
            a = Article.query.filter_by(wiki_id=w.id, slug=slugify(tp["article"])).first()
            if not a:
                continue
            ts = BASE_TS - timedelta(days=tp.get("age_days", 30))
            db.session.add(TalkPost(
                article_id=a.id,
                user_id=None,
                author_label=tp.get("author", "WikiContributor"),
                subject=tp.get("subject", ""),
                body=tp["body"],
                timestamp=ts,
            ))
    db.session.commit()


def seed_database():
    """Idempotent at the function level — re-running is a no-op."""
    from app import Wiki, Article, Revision
    if Wiki.query.count() > 0 and Article.query.count() > 0 \
            and Revision.query.count() > 0:
        return
    _wiki_seed()
    _categories_seed()
    _articles_seed()
    _revisions_seed()
    _polls_seed()
    _talk_seed()


def seed_benchmark_users():
    """Benchmark users for tasks. Gated by alice's email."""
    from app import db, User, Wiki, Article, Revision
    if User.query.filter_by(email="alice.j@test.com").first():
        return

    base = [
        ("alice.j@test.com", "AliceJ", "MCU_Fan_Alice2024", "Big fan of the MCU since Iron Man (2008). Editor of Phase 4 articles.", "mcu", "autoconfirmed,rollback"),
        ("bob.k@test.com", "BobK", "StarWars_Bob_42", "Wookieepedia editor focused on the High Republic era.", "starwars", "autoconfirmed,sysop"),
        ("carol.s@test.com", "CarolS", "Genshin_Carol_AR60", "Liyue lore enthusiast. AR60. Main Hu Tao.", "genshin", "autoconfirmed"),
        ("dan.r@test.com", "DanR", "Dan_The_Reviewer", "Cross-wiki contributor. Categories cleanup work.", "", "autoconfirmed,rollback"),
    ]
    bot_pwd = "WikiBot_Pass_2024!"
    for email, username, pwd, bio, home, groups in base:
        u = User(email=email, username=username, bio=bio,
                 home_wiki=home, groups=groups,
                 avatar_color="#ed1d24" if home == "mcu" else
                             ("#ffe81f" if home == "starwars" else
                             ("#4a90e2" if home == "genshin" else "#fa0046")),
                 joined=BASE_TS - timedelta(days=900))
        u.set_password(pwd)
        db.session.add(u)
    # Also add the WikiBot account so revisions can be linked.
    bot = User(email="wikibot@fandom.test", username="WikiBot",
               bio="Maintenance bot — typo fixes, link cleanup, archive runs.",
               groups="bot,autoconfirmed", joined=BASE_TS - timedelta(days=1200),
               avatar_color="#888888")
    bot.set_password(bot_pwd)
    db.session.add(bot)
    db.session.commit()

    # Link some seeded revisions to the benchmark users (raises edit count).
    alice = User.query.filter_by(username="AliceJ").first()
    bob = User.query.filter_by(username="BobK").first()
    carol = User.query.filter_by(username="CarolS").first()
    dan = User.query.filter_by(username="DanR").first()
    wikibot = User.query.filter_by(username="WikiBot").first()

    mcu = Wiki.query.filter_by(slug="mcu").first()
    sw = Wiki.query.filter_by(slug="starwars").first()
    gs = Wiki.query.filter_by(slug="genshin").first()

    def assign_to(user, wiki, label, every):
        revs = (Revision.query.join(Article)
                .filter(Article.wiki_id == wiki.id,
                        Revision.author_label == label).all())
        for r in revs[::every]:
            r.user_id = user.id

    assign_to(alice, mcu, "StarkFan42", 1)
    assign_to(alice, mcu, "InfinityScribe", 2)
    assign_to(bob, sw, "LucasCanon", 1)
    assign_to(bob, sw, "EnabranTain", 2)
    assign_to(carol, gs, "HoYoLore", 1)
    assign_to(carol, gs, "ShinyCelestia", 2)
    # Dan touches all three wikis lightly
    for wiki in (mcu, sw, gs):
        revs = (Revision.query.join(Article)
                .filter(Article.wiki_id == wiki.id,
                        Revision.author_label == "76.121.44.92").all())
        for r in revs[:5]:
            r.user_id = dan.id
    # WikiBot owns all bot revisions
    bot_revs = Revision.query.filter_by(author_label="WikiBot").all()
    for r in bot_revs:
        r.user_id = wikibot.id
    db.session.commit()
