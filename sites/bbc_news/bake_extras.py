"""
One-off baker: enrich sites/bbc_news/instance_seed/bbc_news.db with extra
deterministic content on top of the seed produced by app.py:seed_database.

R2 scope (May 2026):
  * Article corpus extended via ~25 additional BBC RSS sub-feeds (world
    regions, UK nations, business/health/science verticals, all the sport
    disciplines). Cached at /tmp/bbc_rss/*.xml; we never re-fetch here.
  * ~120 comments distributed across users + articles (reply chains).
  * ~250 reading_history rows across the 5 demo/benchmark users.
  * Top-up of bookmarks, reading_list_items and topic_subscriptions so
    task surface (search / filter / bookmark CRUD / digest) is rich.

Everything is gated by row-count sentinels — second run is a no-op. All
new synthetic rows are timestamped relative to MIRROR_REFERENCE_DATE
(2026-04-15) so two rebuilds on different days produce byte-identical
DBs. The shipped DB at sites/bbc_news/instance_seed/bbc_news.db is the
canonical artefact; the runtime `/reset` endpoint copies it.

Run from /home/v-haoqiwang/repos/WebHarbor with:

    python3 sites/bbc_news/bake_extras.py
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "instance_seed" / "bbc_news.db"
RSS_DIR = Path("/tmp/bbc_rss")

MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 9, 0, 0)

# Deterministic randomness — same outputs across runs.
RNG = random.Random(20260415)

# Sentinel: a single planted flagged-comment we use to detect "R2 top-up
# has already run". Cheap, ASCII, won't collide with any real comment.
R2_SENTINEL_BODY = "<<R2-baked>>"

# R3 sentinel: planted once at end of bake_r3 so we know not to redo the
# +1200 article / +600 comment / new-section additions.
R3_SENTINEL_BODY = "<<R3-baked>>"

# Independent deterministic RNG for R3 work — different seed so we don't
# replay the same offsets as R2 and risk identical synthetic content.
R3_RNG = random.Random(20260516)

# R4 sentinel: planted once at end of bake_r4 so we don't re-emit the
# regional sub-editions / deep sub-page / multi-step additions.
R4_SENTINEL_BODY = "<<R4-baked>>"
R4_RNG = random.Random(20260526)

# Map RSS file -> (primary category slug, optional subsection label).
# Specialised feeds first so their slugs win when an article appears in
# both a sub-feed (e.g. world/africa) and the generic news feed.
FEED_MAP: list[tuple[str, str, str]] = [
    # --- World regions ---
    ("news_world_africa.xml",        "africa",        "Africa"),
    ("news_world_asia.xml",          "asia",          "Asia"),
    ("news_world_europe.xml",        "europe",        "Europe"),
    ("news_world_latin_america.xml", "latin_america", "Latin America"),
    ("news_world_middle_east.xml",   "middle_east",   "Middle East"),
    ("news_world_us_and_canada.xml", "us_canada",     "US & Canada"),
    # --- UK nations ---
    ("news_england.xml",             "england",          "England"),
    ("news_scotland.xml",            "scotland",         "Scotland"),
    ("news_wales.xml",               "wales",            "Wales"),
    ("news_northern_ireland.xml",    "northern_ireland", "N. Ireland"),
    # --- Verticals ---
    ("news_business_economy.xml",        "business",      "Economy"),
    ("news_business_companies.xml",      "business",      "Companies"),
    ("news_business_your_money.xml",     "business",      "Your Money"),
    ("news_science_and_environment.xml", "science",       "Science & Environment"),
    ("news_health.xml",                  "health",        "Health"),
    ("news_education.xml",               "uk",            "Education"),
    ("news_world_radio_and_tv.xml",      "entertainment", "Radio & TV"),
    # --- Sport sub-disciplines ---
    ("sport_football.xml",     "football",  "Football"),
    ("sport_cricket.xml",      "cricket",   "Cricket"),
    ("sport_rugby-union.xml",  "rugby",     "Rugby Union"),
    ("sport_tennis.xml",       "tennis",    "Tennis"),
    ("sport_golf.xml",         "golf",      "Golf"),
    ("sport_athletics.xml",    "athletics", "Athletics"),
    ("sport_cycling.xml",      "sport",     "Cycling"),
    ("sport_formula1.xml",     "sport",     "Formula 1"),
    ("sport_boxing.xml",       "sport",     "Boxing"),
    ("sport_horse-racing.xml", "horse_racing", "Horse Racing"),
    ("sport_snooker.xml",      "sport",     "Snooker"),
    ("sport_swimming.xml",     "sport",     "Swimming"),
    ("sport_disability-sport.xml", "sport", "Disability Sport"),
    ("sport_winter-sports.xml", "sport",    "Winter Sports"),
    ("sport_basketball.xml",   "sport",     "Basketball"),
    ("sport_gymnastics.xml",   "sport",     "Gymnastics"),
    ("sport_olympics.xml",     "sport",     "Olympics"),
    # --- Extra news verticals ---
    ("news_in_pictures.xml",   "in_pictures", "In Pictures"),
    ("news_disability.xml",    "uk",        "Disability"),
    # --- Original R1 feeds (kept last; lowest priority) ---
    ("news_technology_rss.xml",              "technology",    ""),
    ("news_science_and_environment_rss.xml", "science",       ""),
    ("news_health_rss.xml",                  "health",        ""),
    ("news_business_rss.xml",                "business",      ""),
    ("news_politics_rss.xml",                "politics",      ""),
    ("news_entertainment_and_arts_rss.xml",  "entertainment", ""),
    ("sport_rss.xml",                        "sport",         ""),
    ("news_uk_rss.xml",                      "uk",            ""),
    ("news_world_rss.xml",                   "world",         ""),
    ("news_rss.xml",                         "world",         ""),
]


NS = {
    "media": "http://search.yahoo.com/mrss/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


# -----------------------------------------------------------------------
# RSS parsing
# -----------------------------------------------------------------------

def _slug_from_link(link: str) -> str | None:
    m = re.search(r"/articles/([a-z0-9]{8,16})", link)
    return m.group(1) if m else None


def parse_rss(path: Path, cat_slug: str, subsection: str) -> list[dict]:
    out: list[dict] = []
    try:
        tree = ET.parse(path)
    except (ET.ParseError, FileNotFoundError):
        return out
    for item in tree.getroot().iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        slug = _slug_from_link(link)
        if not slug or not title:
            continue
        thumb_el = item.find("media:thumbnail", NS)
        if thumb_el is None:
            thumb_el = item.find("media:content", NS)
        thumb = thumb_el.get("url") if thumb_el is not None else ""
        try:
            pub_dt = parsedate_to_datetime(pub) if pub else MIRROR_REFERENCE_DATE
            if pub_dt.tzinfo is not None:
                pub_dt = pub_dt.replace(tzinfo=None)
        except Exception:
            pub_dt = MIRROR_REFERENCE_DATE
        clean_link = re.sub(r"\?at_.*$", "", link)
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": desc[:300],
            "summary": desc[:300],
            "category": cat_slug,
            "subsection": subsection,
            "thumb": thumb,
            "source_url": clean_link,
            "published_at": pub_dt,
        })
    return out


def collect_rss_articles() -> list[dict]:
    """Iterate FEED_MAP in priority order; first-seen slug wins."""
    seen: set[str] = set()
    bucket: list[dict] = []
    for fname, cat, subsection in FEED_MAP:
        path = RSS_DIR / fname
        for art in parse_rss(path, cat, subsection):
            if art["slug"] in seen:
                continue
            seen.add(art["slug"])
            bucket.append(art)
    return bucket


# -----------------------------------------------------------------------
# Body synthesis
# -----------------------------------------------------------------------

BODY_TEMPLATES = [
    "{desc}\n\n"
    "The story has drawn widespread attention this week, with commentators "
    "across the political spectrum weighing in on the implications. Analysts "
    "say the developments could shape policy discussions for months to come.\n\n"
    "A BBC News correspondent reported that officials confirmed key details "
    "during a briefing on Wednesday. Further reaction is expected as more "
    "information emerges.\n\n"
    "The BBC will continue to follow this story and update readers with the "
    "latest verified information.",

    "{desc}\n\n"
    "Speaking to BBC News, those close to the matter described the situation "
    "as developing rapidly. \"We are watching this very carefully,\" one source "
    "said, declining to be named because they were not authorised to speak "
    "publicly.\n\n"
    "Independent observers noted that the response has been measured but firm. "
    "Several stakeholders have called for greater transparency in the days "
    "ahead.\n\n"
    "More reporting will follow as the picture becomes clearer.",

    "{desc}\n\n"
    "The announcement comes against a backdrop of heightened public interest "
    "in the issue. Polling published earlier this month suggested a sizeable "
    "majority back action of some kind, although views diverge on the detail.\n\n"
    "Industry groups welcomed the news in a joint statement, while campaigners "
    "warned that the measures may not go far enough. The BBC understands that "
    "further consultations are planned.\n\n"
    "Reaction is being closely monitored both in Westminster and abroad.",
]


def synth_body(headline: str, desc: str) -> str:
    template = BODY_TEMPLATES[RNG.randrange(len(BODY_TEMPLATES))]
    return template.format(desc=desc or headline)


# -----------------------------------------------------------------------
# Comment + reading-history templates
# -----------------------------------------------------------------------

COMMENT_TOP_LEVEL = [
    "Solid reporting. Good to see the BBC laying out the facts without sensationalising.",
    "Interesting piece, but I'd have liked more on the long-term implications.",
    "This affects a lot of people in my community. Thanks for covering it.",
    "Can someone explain the wider context here? I'm not sure I follow the timeline.",
    "Hard to know what to believe these days, but this seems balanced.",
    "I disagree with the framing — the headline doesn't quite match the body.",
    "Important story. Hoping for follow-up coverage.",
    "Good to see this finally getting attention in the mainstream press.",
    "The data quoted here doesn't match what I read elsewhere. Source?",
    "This has been brewing for months. Surprised it took this long to surface.",
    "Lots of strong opinions on both sides. The reality is probably somewhere in the middle.",
    "We need more reporting like this — depth, not just headlines.",
    "Concerning if accurate. Looking forward to the follow-up.",
    "Sharing this with my parents. They'll find it useful.",
    "What's the time horizon for any of this to actually change?",
    "I appreciate that the BBC named the sources where it could.",
    "Long-time reader. This is the kind of journalism that keeps me coming back.",
    "Read this on the train — really thought-provoking.",
    "Surprised more isn't being said about the regional impact.",
    "The numbers here feel a bit cherry-picked. Wider data would help.",
    "Could the BBC put together an explainer on the policy side?",
    "Important nuance in paragraph four — easy to miss but matters.",
    "Bookmarking this for the weekly digest.",
    "Refreshing to see a piece that doesn't shout. Thank you.",
    "I'd love to see a chart breaking these figures down by region.",
    "Knowing the local context, I think the piece slightly understates it.",
    "Anyone got a link to the original government report referenced here?",
    "Curious how this compares with similar moves in the EU.",
    "There's a reason why this is trending. People want answers.",
    "Strong piece. Bookmarked for my reading list.",
]

COMMENT_REPLIES = [
    "Agreed — the context is what's missing from most of the coverage I've seen.",
    "Fair point. I came in sceptical but you've changed my mind.",
    "Not sure I follow your logic — could you expand?",
    "Same here. The local angle is being completely overlooked.",
    "Source is linked in the third paragraph of the article.",
    "That's a generous reading. I'd say the situation is more complicated.",
    "This. Exactly this. People keep missing the headline point.",
    "Respectfully disagree — the facts as stated don't support that conclusion.",
    "Thanks, that helped me understand the bit I was stuck on.",
    "Same experience here. Glad it's not just me who noticed.",
    "Worth pointing out that the data is from a single quarter only.",
    "Good question — I'd like to know that too.",
]


USER_INTERESTS = {
    "alice.j@test.com":   ["technology", "science", "ai", "business"],
    "bob.c@test.com":     ["business", "world", "politics", "uk"],
    "carol.d@test.com":   ["health", "science", "earth", "uk"],
    "david.k@test.com":   ["sport", "entertainment", "arts", "culture"],
    "demo@bbcnews.local": ["world", "uk", "technology", "business", "health"],
}


# -----------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------

def _db_signature(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def open_db(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA foreign_keys=ON")
    return con


def ensure_gallery_full_column(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(articles)").fetchall()}
    if "gallery_full_json" not in cols:
        con.execute("ALTER TABLE articles ADD COLUMN gallery_full_json TEXT DEFAULT '{}'")


def cat_id_by_slug(con: sqlite3.Connection) -> dict[str, int]:
    return {slug: cid for cid, slug in con.execute("SELECT id, slug FROM categories")}


def existing_article_slugs(con: sqlite3.Connection) -> set[str]:
    return {r[0] for r in con.execute("SELECT slug FROM articles")}


def _sentinel_planted(con: sqlite3.Connection) -> bool:
    row = con.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R2_SENTINEL_BODY,)
    ).fetchone()
    return bool(row)


# -----------------------------------------------------------------------
# Insert: articles from RSS
# -----------------------------------------------------------------------

def insert_new_articles(con: sqlite3.Connection, rss: list[dict]) -> int:
    """Insert RSS-derived articles whose slug is not in the DB. Order is
    `rss` order (= FEED_MAP priority), so AUTOINCREMENT ids are stable
    across rebuilds."""
    existing = existing_article_slugs(con)
    cat_map = cat_id_by_slug(con)
    default_cid = cat_map.get("world") or next(iter(cat_map.values()))

    rows = []
    for art in rss:
        if art["slug"] in existing:
            continue
        cid = cat_map.get(art["category"], default_cid)
        body = synth_body(art["headline"], art["subtitle"])
        word_count = len(body.split())
        reading_time = max(2, word_count // 200)
        topics = [art["category"].replace("_", " ").title()]
        if art["subsection"]:
            topics.append(art["subsection"])
        rows.append({
            "slug": art["slug"],
            "headline": art["headline"],
            "subtitle": art["subtitle"],
            "summary": art["summary"],
            "body": body,
            "author": "BBC News",
            "category_id": cid,
            "hero_image": art["thumb"],
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(topics),
            "published_at": art["published_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": reading_time,
            "word_count": word_count,
            "view_count": 500 + RNG.randrange(40000),
            "is_featured": 0,
            "is_breaking": 0,
            "is_live": 0,
            "location": "",
            "source_url": art["source_url"],
            "section_slug": art["category"],
            "subsection": art["subsection"],
            "region": "",
            "video_url": "",
            "feature_tags": "[]",
            "content_type": "article",
        })

    if not rows:
        return 0
    con.executemany(
        """
        INSERT INTO articles (
            slug, headline, subtitle, summary, body, author, category_id,
            hero_image, gallery_json, gallery_full_json, topics_json,
            published_at, reading_time, word_count, view_count,
            is_featured, is_breaking, is_live, location, source_url,
            section_slug, subsection, region, video_url, feature_tags,
            content_type
        ) VALUES (
            :slug, :headline, :subtitle, :summary, :body, :author, :category_id,
            :hero_image, :gallery_json, :gallery_full_json, :topics_json,
            :published_at, :reading_time, :word_count, :view_count,
            :is_featured, :is_breaking, :is_live, :location, :source_url,
            :section_slug, :subsection, :region, :video_url, :feature_tags,
            :content_type
        )
        """,
        rows,
    )
    return len(rows)


# -----------------------------------------------------------------------
# Insert: comments
# -----------------------------------------------------------------------

def insert_comments(con: sqlite3.Connection) -> int:
    """Top-level + replies. Idempotent: skips if any real comment rows
    exist (we count non-sentinel rows)."""
    cur = con.cursor()
    real = cur.execute(
        "SELECT COUNT(*) FROM comments WHERE body<>?", (R2_SENTINEL_BODY,)
    ).fetchone()[0]
    if real > 0:
        return 0

    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    article_pool: list[int] = []
    for section in ("technology", "world", "uk", "sport", "business",
                    "health", "science", "politics", "entertainment", "arts"):
        ids = [r[0] for r in cur.execute(
            "SELECT id FROM articles WHERE section_slug=? "
            "ORDER BY view_count DESC LIMIT 8", (section,)
        )]
        article_pool.extend(ids)
    seen: set[int] = set()
    article_pool = [x for x in article_pool if not (x in seen or seen.add(x))]

    if len(article_pool) < 60:
        extra = [r[0] for r in cur.execute(
            "SELECT id FROM articles WHERE id NOT IN ({}) "
            "ORDER BY id LIMIT 60".format(
                ",".join(str(i) for i in article_pool) or "0"
            )
        )]
        article_pool.extend(extra[: 60 - len(article_pool)])

    base_ts = MIRROR_REFERENCE_DATE
    rows_top = []
    for idx, art_id in enumerate(article_pool):
        n_top = RNG.choice([1, 2, 2, 3])
        for j in range(n_top):
            uid = user_ids[(idx + j) % len(user_ids)]
            body = COMMENT_TOP_LEVEL[(idx * 3 + j) % len(COMMENT_TOP_LEVEL)]
            offset_hours = (idx * 7 + j * 11) % (24 * 30)
            ts = base_ts - timedelta(hours=offset_hours, minutes=(idx + j) % 60)
            rows_top.append((uid, art_id, None, body,
                             RNG.randrange(0, 25), 0,
                             ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows_top,
    )
    inserted = len(rows_top)

    new_top = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL AND body<>? ORDER BY id",
        (R2_SENTINEL_BODY,),
    ))
    rows_replies = []
    for i, (cid, art_id, uid, created_at) in enumerate(new_top):
        if i % 3 != 0:
            continue
        n_replies = RNG.choice([1, 1, 2])
        for k in range(n_replies):
            ruid = user_ids[(uid + k + 1) % len(user_ids)]
            if ruid == uid:
                ruid = user_ids[(uid + k + 2) % len(user_ids)]
            body = COMMENT_REPLIES[(i * 2 + k) % len(COMMENT_REPLIES)]
            ts = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S") + timedelta(hours=k + 1)
            rows_replies.append((ruid, art_id, cid, body,
                                 RNG.randrange(0, 12), 0,
                                 ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows_replies,
    )
    inserted += len(rows_replies)
    return inserted


# -----------------------------------------------------------------------
# Insert: reading_history
# -----------------------------------------------------------------------

def insert_reading_history(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute("SELECT COUNT(*) FROM reading_history").fetchone()[0] > 0:
        return 0

    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    for uid, email in users:
        interests = USER_INTERESTS.get(email, ["world", "uk", "business"])
        primary: list[int] = []
        for sec in interests:
            ids = [r[0] for r in cur.execute(
                "SELECT id FROM articles WHERE section_slug=? "
                "ORDER BY published_at DESC LIMIT 15", (sec,)
            )]
            primary.extend(ids)
        cross = [r[0] for r in cur.execute(
            "SELECT id FROM articles ORDER BY id LIMIT 1000"
        )]
        RNG.shuffle(cross)
        cross = cross[:10]

        chosen: list[int] = []
        seen_local: set[int] = set()
        for a in primary + cross:
            if a in seen_local:
                continue
            seen_local.add(a)
            chosen.append(a)
            if len(chosen) >= 50:
                break

        for j, art_id in enumerate(chosen):
            ts = base_ts - timedelta(
                hours=(j * 9 + uid * 3) % (24 * 21),
                minutes=(j * 13) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO reading_history (user_id, article_id, viewed_at) VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


# -----------------------------------------------------------------------
# Top-up: bookmarks, reading_list_items, topic_subscriptions
# Gated on the R2 sentinel so we don't double-insert.
# -----------------------------------------------------------------------

def insert_extra_bookmarks(con: sqlite3.Connection) -> int:
    if _sentinel_planted(con):
        return 0
    cur = con.cursor()
    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    sections = ["technology", "business", "world", "uk", "sport",
                "health", "science", "politics", "entertainment"]
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    for uid, email in users:
        chosen: list[int] = []
        for k, sec in enumerate(sections[:6]):
            row = cur.execute(
                "SELECT id FROM articles WHERE section_slug=? "
                "ORDER BY view_count DESC LIMIT 1 OFFSET ?",
                (sec, (uid * 2 + k) % 5),
            ).fetchone()
            if row:
                chosen.append(row[0])
        for k, art_id in enumerate(chosen):
            existing = cur.execute(
                "SELECT 1 FROM bookmarks WHERE user_id=? AND article_id=?",
                (uid, art_id),
            ).fetchone()
            if existing:
                continue
            ts = base_ts - timedelta(days=(k + uid) % 10, hours=k * 3)
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO bookmarks (user_id, article_id, bookmarked_at) VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_extra_reading_list(con: sqlite3.Connection) -> int:
    if _sentinel_planted(con):
        return 0
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(reading_list_items)")]
    has_folder = "folder" in cols
    has_notes = "notes" in cols
    has_is_read = "is_read" in cols

    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    for uid, email in users:
        interests = USER_INTERESTS.get(email, ["world", "uk", "business"])
        pool = []
        for sec in interests[:3]:
            ids = [r[0] for r in cur.execute(
                "SELECT id FROM articles WHERE section_slug=? "
                "ORDER BY published_at DESC LIMIT 3", (sec,)
            )]
            pool.extend(ids)
        seen_l: set[int] = set()
        pool = [x for x in pool if not (x in seen_l or seen_l.add(x))][:6]
        for k, art_id in enumerate(pool):
            already = cur.execute(
                "SELECT 1 FROM reading_list_items WHERE user_id=? AND article_id=?",
                (uid, art_id),
            ).fetchone()
            if already:
                continue
            folder = "Work" if k % 2 == 0 else "Weekend"
            ts_str = (base_ts - timedelta(days=(k + uid) % 14, hours=k * 2)
                      ).strftime("%Y-%m-%d %H:%M:%S")
            cols_used = ["user_id", "article_id"]
            vals: list = [uid, art_id]
            if has_folder:
                cols_used.append("folder"); vals.append(folder)
            if has_notes:
                cols_used.append("notes"); vals.append("")
            if has_is_read:
                cols_used.append("is_read"); vals.append(0)
            cols_used.append("added_at"); vals.append(ts_str)
            rows.append((cols_used, tuple(vals)))

    if not rows:
        return 0
    # All rows have the same column order (derived from PRAGMA once);
    # build the SQL once from the first row.
    cols_used = rows[0][0]
    sql = (
        f"INSERT INTO reading_list_items ({', '.join(cols_used)}) "
        f"VALUES ({', '.join(['?'] * len(cols_used))})"
    )
    cur.executemany(sql, [r[1] for r in rows])
    return len(rows)


def insert_extra_subscriptions(con: sqlite3.Connection) -> int:
    if _sentinel_planted(con):
        return 0
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(topic_subscriptions)")]
    topic_col = "topic" if "topic" in cols else ("topic_slug" if "topic_slug" in cols else None)
    if topic_col is None:
        return 0
    has_freq = "frequency" in cols
    has_created = "created_at" in cols

    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    for uid, email in users:
        interests = USER_INTERESTS.get(email, ["world", "uk", "business"])
        for k, sec in enumerate(interests[:3]):
            existing = cur.execute(
                f"SELECT 1 FROM topic_subscriptions WHERE user_id=? AND {topic_col}=?",
                (uid, sec),
            ).fetchone()
            if existing:
                continue
            freq = ["daily", "weekly", "weekly"][k % 3]
            ts = base_ts - timedelta(days=(k + uid) % 20)
            row = [uid, sec]
            if has_freq:
                row.append(freq)
            if has_created:
                row.append(ts.strftime("%Y-%m-%d %H:%M:%S"))
            rows.append(tuple(row))

    if not rows:
        return 0
    placeholders = ["user_id", topic_col]
    if has_freq:
        placeholders.append("frequency")
    if has_created:
        placeholders.append("created_at")
    sql = (
        f"INSERT INTO topic_subscriptions ({', '.join(placeholders)}) "
        f"VALUES ({', '.join(['?'] * len(placeholders))})"
    )
    cur.executemany(sql, rows)
    return len(rows)


def plant_sentinel(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    if _sentinel_planted(con):
        return
    cur.execute(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, 1, None, R2_SENTINEL_BODY, 0, 1,
         MIRROR_REFERENCE_DATE.strftime("%Y-%m-%d %H:%M:%S")),
    )


# -----------------------------------------------------------------------
# sqlite_sequence + VACUUM normalisation
# -----------------------------------------------------------------------

def normalize_sqlite_sequence(con: sqlite3.Connection) -> None:
    """If the schema uses AUTOINCREMENT, pin sqlite_sequence.seq to
    MAX(id) per table. SQLite only creates the sqlite_sequence table
    when at least one table declares AUTOINCREMENT — if it's absent the
    schema uses plain INTEGER PRIMARY KEY ROWID and no normalisation is
    needed."""
    cur = con.cursor()
    has_seq = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
    ).fetchone()
    if not has_seq:
        return
    rows = cur.execute("SELECT name FROM sqlite_sequence").fetchall()
    for (tbl,) in rows:
        max_id = cur.execute(f"SELECT COALESCE(MAX(id), 0) FROM {tbl}").fetchone()[0]
        cur.execute("UPDATE sqlite_sequence SET seq=? WHERE name=?", (max_id, tbl))


# -----------------------------------------------------------------------
# R3 — extra categories + synthetic articles + deep comments
# -----------------------------------------------------------------------

R3_NEW_CATEGORIES: list[tuple[str, str, str, str, int, str]] = [
    # slug, name, color, parent_slug, sort_order, description
    ("food",     "Food",     "#bb1919", "",       300, "Recipes, food stories and the BBC Food kitchen"),
    ("sounds",   "Sounds",   "#000000", "audio",  310, "BBC Sounds podcasts, radio and music"),
    ("iplayer",  "iPlayer",  "#000000", "",       320, "BBC iPlayer drama, documentary and entertainment"),
    ("bitesize", "Bitesize", "#0a6b2e", "",       330, "BBC Bitesize learning for primary and secondary"),
    ("podcasts", "Podcasts", "#000000", "sounds", 311, "Podcasts from the BBC and the wider world"),
    ("radio",    "Radio",    "#000000", "sounds", 312, "BBC Radio live and on-demand"),
    ("film",        "Film & TV",     "#000000", "culture", 191, "Film and television reviews and features"),
    ("music",       "Music",         "#000000", "culture", 192, "Music news, releases and reviews"),
    ("books",       "Books",         "#000000", "culture", 193, "Books, authors and literary culture"),
    ("art_design",  "Art & Design",  "#000000", "culture", 194, "Art exhibitions, design and visual culture"),
    ("style",       "Style",         "#000000", "culture", 195, "Style, fashion and design"),
    ("destinations","Destinations",  "#000000", "travel",  141, "Destination guides for the world's cities and regions"),
    ("worlds_table","World's Table", "#000000", "travel",  142, "Food and culture from around the world"),
    ("the_specialist","The SpeciaList","#000000","travel", 143, "Expert travel picks and itineraries"),
    ("new_releases","New Releases",  "#000000", "audio",   201, "Newly released podcasts from the BBC"),
    # Sport sub-disciplines — also added to app.py CATEGORY_META for fresh
    # builds; ensured here too so already-baked DBs catch up.
    ("snooker",   "Snooker",   "#bb1919", "sport", 128, "Snooker news and tournament coverage"),
    ("boxing",    "Boxing",    "#bb1919", "sport", 129, "Boxing news, world titles and big fights"),
    ("formula1",  "Formula 1", "#bb1919", "sport", 130, "Formula 1 races, drivers and constructors"),
]


def ensure_r3_categories(con: sqlite3.Connection) -> int:
    """Insert any missing R3 categories. Returns count of newly added rows."""
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM categories")}
    added = 0
    for slug, name, color, parent, order, desc in R3_NEW_CATEGORIES:
        if slug in existing:
            continue
        cur.execute(
            "INSERT INTO categories (slug, name, color, icon, parent_slug, "
            "sort_order, description, subtitle) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (slug, name, color, "", parent, order, desc, desc[:250]),
        )
        added += 1
    return added


# ---- Article synthesis pools --------------------------------------------

FOOD_RECIPES: list[tuple[str, str]] = [
    ("Slow-roasted lamb shoulder with rosemary", "Slow cooking transforms tough lamb shoulder into a tender Sunday centrepiece. Mary Berry's reliable method."),
    ("Classic Victoria sponge with raspberry jam", "The most British of cakes — a foolproof recipe from the BBC Food test kitchen."),
    ("Spiced sweet potato and chickpea curry", "A vegan curry packed with flavour, ready in 35 minutes. Family-friendly and freezer-friendly."),
    ("Yorkshire puddings that always rise", "Crispy, towering Yorkshire puddings — the four-ingredient recipe that never fails."),
    ("Cornish pasties with shortcrust pastry", "Traditional handheld pasties with peppered steak, swede and potato. Protected geographical indication respected."),
    ("Welsh rarebit on sourdough toast", "Comfort food with mustard, ale and aged cheddar. Ready in ten minutes."),
    ("Sticky toffee pudding with date sauce", "Britain's favourite winter pudding, generously drenched in dark caramel."),
    ("Chicken tikka masala from scratch", "The UK's adopted national dish, with a yoghurt marinade and toasted spice blend."),
    ("Beef Wellington for Sunday lunch", "Tenderloin wrapped in mushroom duxelles and golden puff pastry. A celebration dish."),
    ("Eton mess with summer berries", "Strawberries, meringue and cream — assembled in five minutes."),
    ("Toad in the hole with onion gravy", "Pork sausages baked in puffy batter, finished with rich onion gravy."),
    ("Scotch eggs with sausage and herb crust", "Picnic-perfect: hard-boiled eggs wrapped in seasoned sausagemeat."),
    ("Bara brith — Welsh tea loaf", "A spiced, fruited tea loaf that's better the day after baking."),
    ("Cumberland sausage roll giant size", "A traditional spiral of pork and herbs in flaky pastry."),
    ("Lemon drizzle cake with poppy seeds", "Light sponge soaked with tart lemon-sugar syrup."),
    ("Banoffee pie in fifteen minutes", "Crushed digestives, dulce de leche, bananas and whipped cream."),
    ("Shepherd's pie with cheddar mash", "Slow-simmered minced lamb under a golden cheese-mash crust."),
    ("Bangers and mash with red wine gravy", "Pork sausages, buttery mash and a deeply savoury gravy."),
    ("Crumpets from scratch on the griddle", "Yeasty, holey crumpets — far better than shop-bought."),
    ("Battenberg cake with marzipan", "The classic pink-and-yellow chequerboard cake."),
    ("Cottage pie with rosemary mash", "Beef mince, root vegetables and herby mash potato."),
    ("Bakewell tart with raspberry jam", "A frangipane and jam tart from the Derbyshire town."),
    ("Spotted dick with custard", "A suet pudding studded with currants, drowned in vanilla custard."),
    ("Cheese and onion pasty handheld", "A vegetarian pasty filled with mature cheddar and onion."),
    ("Roast pork belly with crackling", "Slow-roasted until the skin shatters. Apple sauce on the side."),
    ("Trifle with sherry and custard", "Layered sponge, jelly, custard and cream — a Christmas classic."),
    ("Fish and chips at home", "Battered haddock and triple-cooked chips, with mushy peas."),
    ("Lancashire hotpot with lamb", "Slow-cooked lamb and onions under sliced potato."),
    ("Treacle tart with golden syrup", "Old-fashioned treacle tart with breadcrumbs and lemon zest."),
    ("Coronation chicken for sandwiches", "Mild curried chicken with mango chutney, a 1953 invention."),
    ("Cullen skink — Scottish smoked haddock soup", "A creamy, smoky Scottish soup from Cullen, Moray."),
    ("Welsh cakes on the bakestone", "Tea-time griddle cakes, spiced and currant-studded."),
    ("Branston pickle ploughman's lunch", "How to build the perfect cheese-and-pickle plate."),
    ("Strawberry pavlova with cream", "A crisp meringue base topped with cream and ripe strawberries."),
    ("Rice pudding with nutmeg", "Baked rice pudding with a golden skin and creamy centre."),
    ("Marmalade pudding with whisky cream", "A steamed sponge laced with Seville marmalade."),
    ("Cumberland sauce for cold meats", "A port-and-orange sauce for the Boxing Day table."),
    ("Stilton and walnut soup", "A rich, creamy soup with Britain's king of blues."),
    ("Anglesey eggs — Welsh breakfast", "Leeks, mash and cheese sauce baked with eggs."),
    ("Soda bread without a starter", "A 30-minute Irish-style soda bread with buttermilk."),
]

TRAVEL_DESTINATIONS: list[tuple[str, str, str]] = [
    ("Edinburgh", "Scotland", "From the Royal Mile to Arthur's Seat — what to see in 48 hours."),
    ("Bath", "England", "Roman baths, Georgian crescents and the perfect afternoon tea."),
    ("Cornwall", "England", "Coastal walks, fishing villages and a beach for every mood."),
    ("Snowdonia", "Wales", "Hiking the Welsh peaks and discovering slate-mining heritage."),
    ("Belfast", "Northern Ireland", "Titanic Quarter, the Cathedral district and the Giant's Causeway."),
    ("Lake District", "England", "Wordsworth's hills, Beatrix Potter's farm and a swim in Ullswater."),
    ("Isle of Skye", "Scotland", "Black Cuillin ridges, Fairy Pools and the Old Man of Storr."),
    ("York", "England", "Roman walls, the Minster and the Shambles in one perfect day."),
    ("Pembrokeshire Coast", "Wales", "Britain's only coastal national park, mile by stunning mile."),
    ("Outer Hebrides", "Scotland", "Lewis and Harris — white sand, standing stones and Harris tweed."),
    ("Kyoto", "Japan", "Temples, ryokans and the best autumn-leaf viewing in the world."),
    ("Lisbon", "Portugal", "Tile-clad facades, fado bars and trams up impossible hills."),
    ("Marrakech", "Morocco", "Souks, riads and a desert escape from the medina."),
    ("Reykjavik", "Iceland", "Northern lights, geothermal swims and Icelandic horses."),
    ("Hanoi", "Vietnam", "Pho, motorbike chaos and the calm of Hoan Kiem at dawn."),
    ("Buenos Aires", "Argentina", "Tango, asado and the painted houses of La Boca."),
    ("Cape Town", "South Africa", "Table Mountain, Cape Point and the wineries of Stellenbosch."),
    ("Tbilisi", "Georgia", "Sulphur baths, supra feasts and the Caucasus next door."),
    ("Bologna", "Italy", "Porticoes, pasta and Europe's oldest university."),
    ("Tallinn", "Estonia", "A medieval old town that is also a tech-startup hub."),
    ("Porto", "Portugal", "Port wine, the Douro river and azulejo-tiled chapels."),
    ("Seville", "Spain", "Flamenco, tapas and the Real Alcazar palace."),
    ("Krakow", "Poland", "Wawel Castle, Kazimierz and the wider Polish south."),
    ("Bergen", "Norway", "Bryggen wharf, the Floibanen funicular and fjord cruises."),
    ("Salzburg", "Austria", "Mozart, baroque churches and the Sound of Music trail."),
    ("Valletta", "Malta", "A walled city on a peninsula with megalithic temples nearby."),
    ("Ljubljana", "Slovenia", "Plecnik's bridges, riverside cafes and Lake Bled day-trips."),
    ("Vilnius", "Lithuania", "Baroque churches and the bohemian republic of Uzupis."),
    ("Bruges", "Belgium", "Canals, chocolate and a slowed-down medieval centre."),
    ("Ghent", "Belgium", "The medieval rival to Bruges with a livelier student edge."),
    ("Antwerp", "Belgium", "Rubens, diamonds and Europe's second-busiest port."),
    ("Helsinki", "Finland", "Design district, sauna culture and ferry to Suomenlinna."),
    ("Riga", "Latvia", "Art Nouveau facades and a Central Market in old zeppelin hangars."),
    ("Sarajevo", "Bosnia and Herzegovina", "Ottoman bazaar, Habsburg streets and recent history side by side."),
    ("Lyon", "France", "Bouchons, traboules and the food capital of France."),
    ("Marseille", "France", "Calanques, bouillabaisse and a Mediterranean cosmopolitan grit."),
    ("Naples", "Italy", "True Neapolitan pizza, Pompeii and the bay of Capri."),
    ("Athens", "Greece", "Acropolis, modern Greek food and Plaka district wandering."),
    ("Istanbul", "Turkey", "Hagia Sophia, Bosphorus ferries and the spice bazaar."),
    ("Dubrovnik", "Croatia", "Walled city, sea kayaking and Game of Thrones stand-ins."),
]

WEATHER_CITIES: list[tuple[str, str]] = [
    ("London", "England"), ("Manchester", "England"), ("Birmingham", "England"),
    ("Liverpool", "England"), ("Newcastle", "England"), ("Leeds", "England"),
    ("Bristol", "England"), ("Sheffield", "England"), ("Nottingham", "England"),
    ("Brighton", "England"), ("Plymouth", "England"), ("Norwich", "England"),
    ("Cambridge", "England"), ("Oxford", "England"), ("York", "England"),
    ("Edinburgh", "Scotland"), ("Glasgow", "Scotland"), ("Aberdeen", "Scotland"),
    ("Dundee", "Scotland"), ("Inverness", "Scotland"), ("Stirling", "Scotland"),
    ("Cardiff", "Wales"), ("Swansea", "Wales"), ("Newport", "Wales"),
    ("Wrexham", "Wales"), ("Bangor", "Wales"),
    ("Belfast", "Northern Ireland"), ("Derry", "Northern Ireland"),
    ("Lisburn", "Northern Ireland"), ("Newry", "Northern Ireland"),
    ("Paris", "France"), ("Berlin", "Germany"), ("Madrid", "Spain"),
    ("Rome", "Italy"), ("Athens", "Greece"), ("Vienna", "Austria"),
    ("Amsterdam", "Netherlands"), ("Brussels", "Belgium"), ("Dublin", "Ireland"),
    ("Copenhagen", "Denmark"), ("Stockholm", "Sweden"), ("Oslo", "Norway"),
    ("Helsinki", "Finland"), ("Lisbon", "Portugal"), ("Reykjavik", "Iceland"),
    ("Moscow", "Russia"), ("Warsaw", "Poland"), ("Prague", "Czechia"),
    ("Budapest", "Hungary"), ("Bucharest", "Romania"),
    ("New York", "United States"), ("Washington", "United States"),
    ("Los Angeles", "United States"), ("San Francisco", "United States"),
    ("Chicago", "United States"), ("Miami", "United States"),
    ("Toronto", "Canada"), ("Vancouver", "Canada"), ("Montreal", "Canada"),
    ("Sydney", "Australia"), ("Melbourne", "Australia"), ("Brisbane", "Australia"),
    ("Auckland", "New Zealand"), ("Wellington", "New Zealand"),
    ("Tokyo", "Japan"), ("Osaka", "Japan"), ("Seoul", "South Korea"),
    ("Beijing", "China"), ("Shanghai", "China"), ("Hong Kong", "China"),
    ("Singapore", "Singapore"), ("Bangkok", "Thailand"), ("Mumbai", "India"),
    ("Delhi", "India"), ("Cairo", "Egypt"), ("Lagos", "Nigeria"),
    ("Nairobi", "Kenya"), ("Cape Town", "South Africa"), ("Johannesburg", "South Africa"),
]

WEATHER_PHRASES = [
    ("Sunny with scattered cloud", "Mostly sunny with light southerly breezes; high pressure builds."),
    ("Rain showers turning heavy", "Periods of heavy rain push in from the west, easing overnight."),
    ("Overcast and mild", "A grey day with persistent low cloud; mild for the time of year."),
    ("Bright spells with cold wind", "Some sunshine but a sharp north-easterly keeps temperatures down."),
    ("Heavy snow on high ground", "Snow above 300m, with travel disruption likely in the hills."),
    ("Thunderstorms by evening", "Building thunderstorms move in late afternoon, bringing hail."),
    ("Foggy start, brighter later", "Dense fog clears by mid-morning, giving way to weak sun."),
    ("Gales along the coast", "Severe gales and large waves expected along exposed coasts."),
    ("Warm and humid", "Warm air with high humidity makes the day feel close."),
    ("Dry with light frost", "A dry night with widespread frost; sunshine into the afternoon."),
]

IPLAYER_SHOWS: list[tuple[str, str, str]] = [
    ("Doctor Who Series 15 Episode 1", "drama", "The Doctor returns with a new companion and a darker, sharper tone."),
    ("Strictly Come Dancing The Final", "entertainment", "Britain's biggest ballroom contest reaches a sequinned climax."),
    ("Line of Duty A Retrospective", "drama", "A look back at the police-corruption thriller that gripped the nation."),
    ("The Repair Shop Christmas Special", "factual", "Heirlooms restored just in time for the festive season."),
    ("Top Gear Iceland Adventure", "factual", "Three presenters, three modified cars, one volcanic island."),
    ("Sherlock The Final Problem", "drama", "Cumberbatch and Freeman return to Baker Street."),
    ("Killing Eve Series 4 Box Set", "drama", "Eve and Villanelle's cat-and-mouse reaches its finale."),
    ("Peaky Blinders Series 6 Box Set", "drama", "The Shelbys face their final reckoning in 1930s Birmingham."),
    ("Happy Valley Series 3 Box Set", "drama", "Sergeant Catherine Cawood's final case in the Calder Valley."),
    ("MasterChef The Professionals", "entertainment", "Britain's top young chefs compete for the title."),
    ("Bake Off Christmas", "entertainment", "A festive amateur-baking contest under Paul Hollywood's stare."),
    ("Planet Earth III", "factual", "David Attenborough returns with the latest in the landmark series."),
    ("Mortimer and Whitehouse Gone Fishing", "factual", "Two old friends, a fishing rod and gentle wisdom about life."),
    ("Antiques Roadshow Highlights", "factual", "A best-of compilation of jaw-dropping valuations."),
    ("Question Time From Manchester", "current_affairs", "David Dimbleby chairs the audience-led political programme."),
    ("Newsnight In-Depth", "current_affairs", "Long-form reporting and interviews from the BBC News flagship."),
    ("The Crown Final Season", "drama", "The Royal family from 1997 to 2005, in lavish detail."),
    ("Call the Midwife Christmas", "drama", "Festive episodes from Poplar's nursing nuns."),
    ("Casualty Live Episode", "drama", "A live broadcast from Holby City's A&E department."),
    ("EastEnders Hour-Long Special", "drama", "Drama on Albert Square reaches a long-promised crescendo."),
    ("Pointless Celebrities", "entertainment", "Famous faces tackle obscure quiz answers for charity."),
    ("Mastermind Final", "entertainment", "The black chair, a chosen subject and 90 seconds."),
    ("University Challenge Semi-Final", "entertainment", "Britain's brightest students battle in the Paxman tradition."),
    ("Inside the Factory Cheese", "factual", "Gregg Wallace tracks cheese from grass to cheeseboard."),
    ("Race Across the World Series 4", "entertainment", "Pairs race across continents without flights or smartphones."),
    ("Glow Up Make-Up Artistry", "entertainment", "Aspiring make-up artists battle for an industry contract."),
    ("Springwatch from Wild Ken Hill", "factual", "Chris Packham and team follow British wildlife in spring."),
    ("Autumnwatch Live", "factual", "The autumn migration spectacle, brought to you live."),
    ("Winterwatch Speyside", "factual", "Snow, red deer and the secret lives of the Highlands."),
    ("Have I Got News For You", "entertainment", "Topical satire with Ian Hislop and Paul Merton."),
]

SOUNDS_PODCASTS: list[tuple[str, str, str]] = [
    ("The News Agents Daily", "current_affairs", "Hosts unpick the day's biggest stories with a sceptical eye."),
    ("In Our Time Renaissance", "factual", "Melvyn Bragg discusses ideas, art and history with experts."),
    ("Desert Island Discs Highlights", "factual", "Eight tracks, a book and a luxury — the classic chat format."),
    ("History Hour East India Company", "factual", "A long-form look at the rise and fall of the trading empire."),
    ("Curious Cases of Rutherford and Fry", "factual", "Two scientists answer listener questions on the very weird."),
    ("More or Less Statistics Explained", "factual", "Tim Harford explains the numbers behind the news."),
    ("The Bottom Line with Evan Davis", "business", "Senior business leaders on what's really going on."),
    ("File on 4 Care Homes Investigation", "current_affairs", "Long-form investigative journalism."),
    ("Today in Parliament", "current_affairs", "A digest of the day at Westminster."),
    ("Bringing Up Britain", "factual", "Parents and experts on what works in raising children."),
    ("Inside Health Vaccines Special", "factual", "A weekly look at what science says about our wellbeing."),
    ("Word of Mouth English Today", "factual", "Michael Rosen on language, dialect and the lives of words."),
    ("The Reith Lectures", "factual", "Annual lectures from a major public thinker."),
    ("Womans Hour Daily", "factual", "News, debate and culture from a female perspective."),
    ("Sliced Bread Product Claims", "factual", "Greg Foot tests the wild claims on supermarket shelves."),
    ("From Our Own Correspondent", "current_affairs", "Personal essays from BBC correspondents around the world."),
    ("Costing the Earth Climate", "factual", "Reporting on climate, environment and our collective future."),
    ("Witness History The Berlin Wall", "factual", "Eyewitness accounts of the events that shaped our times."),
    ("Today Podcast", "current_affairs", "Long-form interviews from the Radio 4 flagship."),
    ("The Briefing Room Politics", "current_affairs", "David Aaronovitch unpacks a single policy area."),
    ("Beyond Belief", "factual", "Faith leaders debate religion in modern life."),
    ("Discovery Frontiers of Science", "factual", "BBC World Service science magazine."),
    ("Crossing Continents", "current_affairs", "Reporting from the road, far from the cliches."),
    ("Tales from the Stave", "factual", "Manuscripts of great composers, examined."),
    ("PM Programme", "current_affairs", "The Radio 4 early-evening news round-up."),
]

BITESIZE_LESSONS: list[tuple[str, str, str, str]] = [
    # subject, age range, title, summary
    ("Maths", "GCSE", "Solving Quadratic Equations", "Step-by-step guide to factorising and using the formula."),
    ("Maths", "GCSE", "Trigonometry Sine Rule and Cosine Rule", "When and how to use each rule with worked examples."),
    ("Maths", "KS3", "Fractions, Decimals and Percentages", "Converting confidently between the three notations."),
    ("Maths", "KS2", "Long Multiplication", "The column method, with checks and common mistakes to avoid."),
    ("Maths", "A-Level", "Integration by Parts", "The product rule's twin, with three full worked solutions."),
    ("Maths", "A-Level", "Hypothesis Testing", "Forming a null hypothesis and using the binomial distribution."),
    ("English", "GCSE", "Macbeth Act 1 Analysis", "Power, ambition and the role of the supernatural in scene one."),
    ("English", "GCSE", "An Inspector Calls Themes", "Responsibility, class and gender in Priestley's play."),
    ("English", "GCSE", "Romeo and Juliet Key Quotes", "Quotes you need to know for the exam, by theme."),
    ("English", "KS3", "Persuasive Writing Techniques", "Rhetorical questions, triples and the rule of three."),
    ("English", "KS2", "Spelling Common Tricky Words", "Strategies for words that don't follow the usual rules."),
    ("English", "A-Level", "The Great Gatsby Symbolism", "The green light, the eyes of Eckleburg and what they mean."),
    ("Science", "GCSE", "Photosynthesis", "Inputs, outputs and the role of chlorophyll."),
    ("Science", "GCSE", "Electric Circuits Current and Voltage", "Series and parallel circuits, with worked problems."),
    ("Science", "GCSE", "Atomic Structure", "Protons, neutrons, electrons and the periodic table."),
    ("Science", "KS3", "States of Matter", "Solids, liquids, gases and the changes between them."),
    ("Science", "KS2", "The Human Skeleton", "Bones we need to know and what they do."),
    ("Science", "A-Level", "Mitosis and Meiosis", "Cell division explained, with diagrams."),
    ("Science", "A-Level", "Organic Chemistry Reactions", "Mechanisms for substitution, elimination and addition."),
    ("History", "GCSE", "Causes of World War One", "Alliances, militarism and the assassination at Sarajevo."),
    ("History", "GCSE", "Weimar Germany 1919-1933", "From the Treaty of Versailles to the Nazi rise to power."),
    ("History", "GCSE", "The American West 1840-1895", "Native Americans, settlers and the railroads."),
    ("History", "KS3", "Norman Conquest", "1066 in one revision sheet."),
    ("History", "KS3", "Industrial Revolution Living Conditions", "Factories, workhouses and reform."),
    ("History", "A-Level", "Tudors Henry VII Government", "How Henry secured his throne after Bosworth."),
    ("History", "A-Level", "Cold War Origins", "From Yalta to the Berlin Airlift."),
    ("Geography", "GCSE", "Plate Tectonics", "Constructive, destructive and conservative boundaries."),
    ("Geography", "GCSE", "Urban Issues UK Cities", "Inequality, regeneration and sustainable urban living."),
    ("Geography", "KS3", "Rivers Long Profile", "From source to mouth, with key features."),
    ("Geography", "A-Level", "Carbon and Water Cycles", "Stores, flows and how human activity disrupts both."),
    ("Geography", "A-Level", "Tectonic Hazards Case Study", "Comparing Haiti 2010 and Tohoku 2011."),
    ("Computer Science", "GCSE", "Binary and Hexadecimal", "Converting between bases, with practice problems."),
    ("Computer Science", "GCSE", "Algorithms Bubble Sort", "How bubble sort works and where it goes wrong."),
    ("Computer Science", "GCSE", "Networks LAN and WAN", "Topologies, protocols and the layers of the stack."),
    ("Computer Science", "A-Level", "Big-O Notation", "Comparing the time complexity of common algorithms."),
    ("Computer Science", "A-Level", "Object Oriented Programming", "Classes, inheritance, polymorphism and encapsulation."),
    ("Physics", "GCSE", "Forces and Motion", "Newton's laws with practical examples."),
    ("Physics", "A-Level", "Capacitors and Charge", "RC circuits and the time constant explained."),
    ("Biology", "GCSE", "Inheritance Punnett Squares", "How to predict genetic outcomes from parental genotypes."),
    ("Biology", "A-Level", "Krebs Cycle", "Aerobic respiration step by step."),
    ("Chemistry", "GCSE", "Bonding Ionic vs Covalent", "Properties and examples of each bond type."),
    ("Chemistry", "A-Level", "Electrochemical Cells", "Standard electrode potentials and cell EMF."),
    ("French", "GCSE", "Perfect Tense with avoir", "Forming the perfect tense for regular and irregular verbs."),
    ("Spanish", "GCSE", "Subjunctive Mood", "Recognising and using the subjunctive in everyday Spanish."),
    ("German", "GCSE", "Cases Nominative Accusative", "When to use each case, with article tables."),
    ("Religious Studies", "GCSE", "Crime and Punishment Christian Views", "Forgiveness, retribution and rehabilitation."),
    ("Religious Studies", "GCSE", "Islam Five Pillars", "Shahada, Salah, Zakat, Sawm, Hajj — explained."),
    ("Business Studies", "GCSE", "Marketing Mix the 4 Ps", "Product, Price, Place and Promotion in real cases."),
    ("Business Studies", "A-Level", "Break Even Analysis", "Calculating the break-even point with worked examples."),
    ("PSHE", "KS3", "Online Safety", "Protecting your digital footprint and recognising scams."),
]

SPORT_LIVE_EVENTS: list[tuple[str, str, str]] = [
    ("Premier League Match Day Live", "football", "Live commentary, goal updates and table movements across all ten fixtures."),
    ("FA Cup Fifth Round Replays Live", "football", "Live coverage of the night's replays from across the country."),
    ("Champions League Quarter Final Live", "football", "European football's biggest night brings drama to two Premier League sides."),
    ("Six Nations Match Live England v Wales", "rugby", "Rolling coverage of the championship's grudge match at Twickenham."),
    ("Six Nations Match Live Ireland v France", "rugby", "Aviva Stadium hosts a title decider in front of a sold-out crowd."),
    ("World Snooker Championship Final Live", "sport", "The Crucible welcomes a long-awaited final between two former champions."),
    ("Wimbledon Men's Final Live", "tennis", "Centre Court's biggest day with live game-by-game updates."),
    ("Wimbledon Women's Final Live", "tennis", "A Grand Slam final live from SW19."),
    ("US Open Tennis Final Live", "tennis", "Flushing Meadows, prime-time, a champion crowned."),
    ("Open Championship Final Round Live", "golf", "Live shot-by-shot coverage of the final round at Royal Birkdale."),
    ("Masters Sunday Augusta Live", "golf", "The green jacket on the line in Georgia."),
    ("Boat Race Live from Putney", "sport", "Oxford and Cambridge clash on the Thames for the 169th time."),
    ("London Marathon Live", "athletics", "Elite races and the mass-participation event combined."),
    ("World Athletics Championships Live", "athletics", "Live finals from the global championships."),
    ("Tour de France Live Stage 18", "sport", "A mountain stage with the yellow jersey under pressure."),
    ("Ashes Test Cricket Live Day 5", "cricket", "Final-day drama in a deciding Ashes Test."),
    ("Cricket World Cup Final Live", "cricket", "Live coverage as the trophy is decided."),
    ("Olympic Games Opening Ceremony Live", "sport", "Live coverage of the opening ceremony."),
    ("Olympic 100m Final Live", "sport", "The blue-riband event of the athletics programme."),
    ("Formula One British Grand Prix Live", "sport", "Silverstone roars for the home fans."),
    ("Grand National Live from Aintree", "horse_racing", "The world's most famous steeplechase, fence by fence."),
    ("Cheltenham Gold Cup Live", "horse_racing", "Jump racing's blue-riband event."),
    ("World Heavyweight Title Fight Live", "sport", "Live commentary from ringside on a unification bout."),
    ("Super League Grand Final Live", "rugby", "Old Trafford hosts rugby league's championship match."),
    ("Calcutta Cup Live Scotland v England", "rugby", "An historic Six Nations meeting at Murrayfield."),
]

VIDEO_CLIPS: list[tuple[str, str, str]] = [
    # category section_slug, subsection, title
    ("world",       "Conflict",        "Watch: Aerial footage of port damage after overnight strikes"),
    ("world",       "Africa",          "Watch: Drone footage of the new Lagos rail link"),
    ("uk",          "London",          "Watch: Crowds gather for Trooping the Colour"),
    ("politics",    "Westminster",     "Watch: Prime Minister's Questions in two minutes"),
    ("business",    "Markets",         "Watch: Wall Street opens lower as inflation data surprises"),
    ("technology",  "AI",              "Watch: Inside the new generative-AI research lab"),
    ("technology",  "Gadgets",         "Watch: Hands-on with the latest folding phone"),
    ("science",     "Space",           "Watch: New Mars rover sends back first colour images"),
    ("science",     "Climate",         "Watch: Why the jet stream is wobbling more often"),
    ("health",      "NHS",             "Watch: Inside the hospital trialling AI diagnosis"),
    ("sport",       "Football",        "Watch: All the goals from the weekend's Premier League"),
    ("sport",       "Cricket",         "Watch: Five-wicket haul on debut for England spinner"),
    ("entertainment","Film",           "Watch: Stars on the red carpet at the BAFTAs"),
    ("entertainment","Music",          "Watch: Highlights from the opening night at Glastonbury"),
    ("arts",        "Theatre",         "Watch: Backstage with the National Theatre's new production"),
    ("travel",      "Destinations",    "Watch: Five reasons to visit the Faroe Islands this summer"),
    ("food",        "Recipes",         "Watch: A 15-minute weeknight curry from scratch"),
    ("earth",       "Wildlife",        "Watch: Time-lapse of beavers rebuilding a Scottish river"),
    ("earth",       "Climate",         "Watch: Why coral bleaching is back on the Great Barrier Reef"),
    ("in_pictures", "Photography",     "Watch: The week in pictures, narrated by the BBC picture editor"),
]


def _hero_image_pool(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT hero_image FROM articles "
        "WHERE hero_image LIKE 'https://ichef%' ORDER BY hero_image"
    ).fetchall()
    return [r[0] for r in rows]


def _det_int(s: str) -> int:
    """Deterministic non-negative int from a string (process-stable)."""
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:4], 'big')


def _det_slug(prefix: str, key: str) -> str:
    """Deterministic 10-char article slug. BBC-style: low-cardinality alnum."""
    digest = hashlib.md5(f"{prefix}|{key}".encode()).hexdigest()
    return f"r3{prefix[:1]}{digest[:8]}"


def synth_food_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    food_cid = cur.execute("SELECT id FROM categories WHERE slug='food'").fetchone()[0]
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (title, lede) in enumerate(FOOD_RECIPES):
        slug = _det_slug("food", title)
        hero = hero_pool[_det_int(slug) % len(hero_pool)]
        ts = base_ts - timedelta(days=idx * 2 + 1, hours=(idx * 7) % 24)
        body = (
            f"{lede}\n\n"
            f"This recipe serves four and takes around {30 + (idx % 4) * 15} minutes "
            f"from start to finish. BBC Food has tested it several times in the test "
            f"kitchen to make sure the timings hold for a domestic oven.\n\n"
            f"Tips from our cook: weigh ingredients before you start, and read the "
            f"method through once so you know when each step is needed. Substitutions "
            f"are noted where they make a real difference to the final dish.\n\n"
            f"Method: Step one — prepare the ingredients. Step two — combine and "
            f"cook as directed. Step three — rest, then serve. Photographs of every "
            f"stage are included so you can compare what your pan should look like."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": lede[:300],
            "summary": lede[:300],
            "body": body,
            "author": "BBC Food",
            "category_id": food_cid,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(["Food", "Recipes", "Cooking"]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 5,
            "word_count": len(body.split()),
            "view_count": 1200 + (idx * 311) % 9000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": "",
            "source_url": f"https://www.bbc.co.uk/food/recipes/{slug}",
            "section_slug": "food",
            "subsection": "Recipes",
            "region": "",
            "video_url": "",
            "feature_tags": json.dumps(["food", "recipe", "cooking"]),
            "content_type": "recipe",
        })
    return out


def synth_travel_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cid_travel = cur.execute("SELECT id FROM categories WHERE slug='travel'").fetchone()[0]
    cid_dest = cur.execute("SELECT id FROM categories WHERE slug='destinations'").fetchone()[0]
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (city, country, lede) in enumerate(TRAVEL_DESTINATIONS):
        title = f"{city} city guide: what to see, eat and do"
        slug = _det_slug("travel", title)
        hero = hero_pool[(_det_int(slug) + 7) % len(hero_pool)]
        ts = base_ts - timedelta(days=idx + 5, hours=(idx * 11) % 24)
        body = (
            f"{lede}\n\n"
            f"Our BBC Travel writer spent a week in {city}, {country}, navigating the "
            f"obvious sights and the less-obvious side streets. The guide below covers "
            f"three days from arrival to departure, with where to stay, where to eat "
            f"and where to escape the crowds.\n\n"
            f"On day one, focus on the city's signature landmark. Day two is for the "
            f"neighbourhood that locals would never tell a tourist about. Day three "
            f"is an easy day-trip to somewhere within an hour's reach.\n\n"
            f"Getting there: direct flights from major UK airports and a sensible "
            f"train option if you'd rather travel overland. We've noted the carbon "
            f"footprint of each approach so you can pick the trip that's right for you."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": lede[:300],
            "summary": lede[:300],
            "body": body,
            "author": "BBC Travel",
            "category_id": cid_dest,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(["Travel", country, "Destinations"]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 7,
            "word_count": len(body.split()),
            "view_count": 800 + (idx * 547) % 12000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": f"{city}, {country}",
            "source_url": f"https://www.bbc.com/travel/article/{slug}",
            "section_slug": "travel",
            "subsection": "Destinations",
            "region": country,
            "video_url": "",
            "feature_tags": json.dumps(["travel", city.lower().replace(' ', '-'), country.lower().replace(' ', '-')]),
            "content_type": "article",
        })
    return out


def synth_weather_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cid = cur.execute("SELECT id FROM categories WHERE slug='weather'").fetchone()[0]
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (city, country) in enumerate(WEATHER_CITIES):
        phrase, blurb = WEATHER_PHRASES[idx % len(WEATHER_PHRASES)]
        title = f"{city} weather forecast: {phrase}"
        slug = _det_slug("wx", title)
        # Deterministic temperature/range from hash
        h = int.from_bytes(hashlib.md5(slug.encode()).digest()[:2], "big")
        hi = (h % 28) + 4
        lo = max(0, hi - (5 + (h % 8)))
        rain_pct = (h // 4) % 100
        wind_mph = 5 + ((h // 7) % 35)
        hero = hero_pool[(_det_int(slug) + 13) % len(hero_pool)]
        ts = base_ts - timedelta(hours=idx)
        body = (
            f"{blurb}\n\n"
            f"Today in {city}, {country}: highs of {hi}°C and overnight lows of "
            f"{lo}°C. Chance of precipitation: {rain_pct}%. Wind: {wind_mph} mph "
            f"from a westerly direction.\n\n"
            f"Outlook for the next three days: similar conditions persist, with the "
            f"chance of more sustained rain building from the weekend onwards. UV "
            f"index is moderate. Pollen count: low.\n\n"
            f"BBC Weather forecasts are produced in partnership with MeteoGroup and "
            f"updated three times a day. Severe weather warnings, where issued, are "
            f"linked at the top of the page."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": blurb[:300],
            "summary": blurb[:300],
            "body": body,
            "author": "BBC Weather",
            "category_id": cid,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(["Weather", city, country]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 2,
            "word_count": len(body.split()),
            "view_count": 600 + (idx * 191) % 8000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": f"{city}, {country}",
            "source_url": f"https://www.bbc.com/weather/{slug}",
            "section_slug": "weather",
            "subsection": city,
            "region": country,
            "video_url": "",
            "feature_tags": json.dumps(["weather", "forecast", city.lower().replace(' ', '-')]),
            "content_type": "forecast",
        })
    return out


def synth_iplayer_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cid = cur.execute("SELECT id FROM categories WHERE slug='iplayer'").fetchone()[0]
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (show, genre, blurb) in enumerate(IPLAYER_SHOWS):
        title = show
        slug = _det_slug("ipl", show)
        hero = hero_pool[(_det_int(slug) + 23) % len(hero_pool)]
        ts = base_ts - timedelta(days=idx + 1)
        runtime = 30 + (idx % 6) * 15
        body = (
            f"{blurb}\n\n"
            f"Available now on BBC iPlayer. Runtime: {runtime} minutes. Audio "
            f"description and signed versions are available where indicated, and "
            f"the full series can be downloaded for offline viewing on most "
            f"devices.\n\n"
            f"Episode notes: Episode 1 introduces the principal cast and lays "
            f"out the central tension. Subsequent episodes broaden the world and "
            f"reveal the consequences of the choices made in the opener.\n\n"
            f"For a streamlined viewing experience, related programmes are listed "
            f"at the foot of the page. Behind-the-scenes interviews are filed "
            f"under 'Extras'."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": blurb[:300],
            "summary": blurb[:300],
            "body": body,
            "author": "BBC iPlayer",
            "category_id": cid,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(["iPlayer", genre.title(), "TV"]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 3,
            "word_count": len(body.split()),
            "view_count": 2500 + (idx * 727) % 14000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": "",
            "source_url": f"https://www.bbc.co.uk/iplayer/episode/{slug}",
            "section_slug": "iplayer",
            "subsection": genre.title(),
            "region": "",
            "video_url": f"https://www.bbc.co.uk/iplayer/episode/{slug}",
            "feature_tags": json.dumps(["iplayer", genre, "video"]),
            "content_type": "video",
        })
    return out


def synth_sounds_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cid = cur.execute("SELECT id FROM categories WHERE slug='sounds'").fetchone()[0]
    cid_pod = cur.execute("SELECT id FROM categories WHERE slug='podcasts'").fetchone()[0]
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (show, kind, blurb) in enumerate(SOUNDS_PODCASTS):
        title = show
        slug = _det_slug("snd", show)
        hero = hero_pool[(_det_int(slug) + 31) % len(hero_pool)]
        ts = base_ts - timedelta(days=idx + 1, hours=(idx * 5) % 24)
        runtime = 25 + (idx % 4) * 10
        body = (
            f"{blurb}\n\n"
            f"Listen now on BBC Sounds. Episode duration: {runtime} minutes. New "
            f"episodes are typically published weekly; subscribe to receive an "
            f"alert when each one drops.\n\n"
            f"The presenter is joined by a rotating panel of contributors who "
            f"bring expertise from journalism, academia and the relevant "
            f"industries. Quotations are checked against published sources and "
            f"corrections are noted at the end of the next episode where needed.\n\n"
            f"A full transcript is available on the BBC Sounds page within 48 "
            f"hours of broadcast. Earlier episodes are available in the archive."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": blurb[:300],
            "summary": blurb[:300],
            "body": body,
            "author": "BBC Sounds",
            "category_id": cid_pod,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(["Sounds", "Podcast", kind.replace('_', ' ').title()]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 2,
            "word_count": len(body.split()),
            "view_count": 1500 + (idx * 401) % 10000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": "",
            "source_url": f"https://www.bbc.co.uk/sounds/play/{slug}",
            "section_slug": "sounds",
            "subsection": "Podcasts",
            "region": "",
            "video_url": "",
            "feature_tags": json.dumps(["sounds", "podcast", kind]),
            "content_type": "podcast",
        })
    return out


def synth_bitesize_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cid = cur.execute("SELECT id FROM categories WHERE slug='bitesize'").fetchone()[0]
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (subject, age, title, summary) in enumerate(BITESIZE_LESSONS):
        full_title = f"{subject} {age}: {title}"
        slug = _det_slug("bite", full_title)
        hero = hero_pool[(_det_int(slug) + 41) % len(hero_pool)]
        ts = base_ts - timedelta(days=idx * 3 + 2, hours=(idx * 9) % 24)
        body = (
            f"{summary}\n\n"
            f"This Bitesize lesson is part of the {subject} {age} pathway. It "
            f"covers the core idea in three short videos, two interactive "
            f"questions and a one-page printable summary suitable for revision "
            f"or homework.\n\n"
            f"By the end you should be able to (a) define the key terms, (b) "
            f"work through a single guided example and (c) attempt a check-for-"
            f"understanding question. Hints are available if you get stuck.\n\n"
            f"For more practice, visit the related lessons listed below. Past "
            f"papers and mark schemes are linked from the {subject} {age} hub "
            f"page."
        )
        out.append({
            "slug": slug,
            "headline": full_title,
            "subtitle": summary[:300],
            "summary": summary[:300],
            "body": body,
            "author": "BBC Bitesize",
            "category_id": cid,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps([subject, age, "Bitesize", "Education"]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 4,
            "word_count": len(body.split()),
            "view_count": 700 + (idx * 251) % 6000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": "",
            "source_url": f"https://www.bbc.co.uk/bitesize/guides/{slug}",
            "section_slug": "bitesize",
            "subsection": subject,
            "region": age,
            "video_url": "",
            "feature_tags": json.dumps(["bitesize", subject.lower().replace(' ', '-'), age.lower()]),
            "content_type": "lesson",
        })
    return out


def synth_sport_live_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cat_lookup = {r[1]: r[0] for r in cur.execute("SELECT id, slug FROM categories")}
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (title, sport_slug, blurb) in enumerate(SPORT_LIVE_EVENTS):
        cid = cat_lookup.get(sport_slug) or cat_lookup.get("sport")
        slug = _det_slug("live", title)
        hero = hero_pool[(_det_int(slug) + 53) % len(hero_pool)]
        ts = base_ts - timedelta(hours=idx * 2)
        is_live_flag = 1 if idx < 8 else 0
        body = (
            f"{blurb}\n\n"
            f"Updates are running in our live page below. Send your thoughts and "
            f"reactions via the BBC Sport messaging system and we'll publish a "
            f"selection on this page through the event.\n\n"
            f"Pre-match analysis, formations, weather conditions and any late "
            f"team news are pinned at the top. Expect goal/wicket/score updates "
            f"the moment they happen, with video clips where available shortly "
            f"after.\n\n"
            f"This is BBC Sport's live event coverage. The corresponding match "
            f"report and full reaction will follow at the final whistle. For "
            f"earlier rounds and previous events, see the related fixtures."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": blurb[:300],
            "summary": blurb[:300],
            "body": body,
            "author": "BBC Sport",
            "category_id": cid,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps(["Sport", sport_slug.title(), "Live"]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 6,
            "word_count": len(body.split()),
            "view_count": 4000 + (idx * 991) % 20000,
            "is_featured": 1 if idx < 3 else 0,
            "is_breaking": 0,
            "is_live": is_live_flag,
            "location": "",
            "source_url": f"https://www.bbc.com/sport/live/{slug}",
            "section_slug": sport_slug,
            "subsection": "Live",
            "region": "",
            "video_url": "",
            "feature_tags": json.dumps(["sport", "live", sport_slug]),
            "content_type": "live",
        })
    return out


def synth_video_clips(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cat_lookup = {r[1]: r[0] for r in cur.execute("SELECT id, slug FROM categories")}
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    for idx, (sec, sub, title) in enumerate(VIDEO_CLIPS):
        cid = cat_lookup.get(sec) or cat_lookup.get("video")
        slug = _det_slug("vid", title)
        hero = hero_pool[(_det_int(slug) + 61) % len(hero_pool)]
        ts = base_ts - timedelta(hours=idx * 3 + 5)
        body = (
            f"This BBC News video clip runs for around {60 + (idx % 4) * 30} seconds. "
            f"Captions and audio description are available where indicated.\n\n"
            f"For the related written report, see the link at the foot of the page. "
            f"Embedded video may not be available in all regions for rights reasons."
        )
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": title,
            "summary": title,
            "body": body,
            "author": "BBC News",
            "category_id": cid,
            "hero_image": hero,
            "gallery_json": "[]",
            "gallery_full_json": "{}",
            "topics_json": json.dumps([sec.title(), sub, "Video"]),
            "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": 2,
            "word_count": len(body.split()),
            "view_count": 3000 + (idx * 379) % 18000,
            "is_featured": 0, "is_breaking": 0, "is_live": 0,
            "location": "",
            "source_url": f"https://www.bbc.com/news/videos/{slug}",
            "section_slug": sec,
            "subsection": sub,
            "region": "",
            "video_url": f"https://www.bbc.com/news/videos/{slug}",
            "feature_tags": json.dumps(["video", sec]),
            "content_type": "video",
        })
    return out


def synth_regional_followups(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    """For each regional section, synthesize follow-up retrospectives off the
    top-viewed real articles. This pushes the regional counts to a usable
    benchmark depth."""
    cur = con.cursor()
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    sections_to_grow = [
        ("england",         "England",          18),
        ("scotland",        "Scotland",         18),
        ("wales",           "Wales",            18),
        ("northern_ireland","Northern Ireland", 12),
        ("uk",              "UK",               20),
        ("politics",        "Politics",         20),
        ("world",           "World",            20),
        ("europe",          "Europe",           18),
        ("asia",            "Asia",             18),
        ("africa",          "Africa",           18),
        ("middle_east",     "Middle East",      14),
        ("us_canada",       "US & Canada",      14),
        ("latin_america",   "Latin America",    14),
        ("business",        "Business",         18),
        ("technology",      "Technology",       18),
        ("ai",              "Artificial Intelligence", 14),
        ("science",         "Science",          18),
        ("health",          "Health",           18),
        ("entertainment",   "Entertainment",    14),
        ("arts",            "Arts",             10),
        ("culture",         "Culture",          10),
        ("earth",           "Earth",            10),
        ("green_living",    "Green Living",     10),
        ("natural_wonders", "Natural Wonders",  10),
        ("in_pictures",     "In Pictures",      10),
        ("bbcverify",       "BBC Verify",       10),
        ("football",        "Football",         18),
        ("cricket",         "Cricket",          14),
        ("rugby",           "Rugby",            14),
        ("tennis",          "Tennis",           14),
        ("golf",            "Golf",             14),
        ("athletics",       "Athletics",        14),
        ("war",             "War & Conflict",   10),
    ]
    follow_phrases = [
        "What we know so far",
        "Five things you might have missed",
        "Analysis: the long view",
        "Reactions from across the country",
        "Why this story matters now",
        "In pictures: a week in review",
        "Q and A: the questions everyone is asking",
        "Verified: what the footage actually shows",
    ]
    for section_slug, region_label, count in sections_to_grow:
        cid_row = cur.execute(
            "SELECT id FROM categories WHERE slug=?", (section_slug,)
        ).fetchone()
        if not cid_row:
            continue
        cid = cid_row[0]
        seeds = cur.execute(
            "SELECT slug, headline, subtitle FROM articles WHERE section_slug=? "
            "ORDER BY view_count DESC LIMIT ?", (section_slug, max(count, 12))
        ).fetchall()
        if not seeds:
            continue
        for idx in range(count):
            seed_slug, seed_head, seed_sub = seeds[idx % len(seeds)]
            phrase = follow_phrases[idx % len(follow_phrases)]
            title = f"{seed_head[:120].rstrip(' .')} — {phrase}"
            slug = _det_slug(f"r3-{section_slug}", f"{seed_slug}|{idx}|{phrase}")
            hero = hero_pool[(_det_int(slug) + 71) % len(hero_pool)]
            ts = base_ts - timedelta(
                days=(idx * 4 + 3) % 60,
                hours=(idx * 11) % 24,
            )
            body = (
                f"{seed_sub or seed_head}\n\n"
                f"This follow-up looks back at the events covered in our earlier "
                f"report and asks where the story has moved in the days since. "
                f"BBC News correspondents in the region have gathered fresh "
                f"reaction from those most directly affected.\n\n"
                f"Analysts agree that the picture remains in flux. Officials "
                f"speaking on condition of anonymity say the situation is "
                f"\"manageable, but only just,\" while those on the ground tell "
                f"a more complicated story. We'll continue to verify and update.\n\n"
                f"For the original report, see the linked story. Further "
                f"analysis is coming this week as more details emerge."
            )
            out.append({
                "slug": slug,
                "headline": title,
                "subtitle": seed_sub or "",
                "summary": (seed_sub or seed_head)[:300],
                "body": body,
                "author": "BBC News",
                "category_id": cid,
                "hero_image": hero,
                "gallery_json": "[]",
                "gallery_full_json": "{}",
                "topics_json": json.dumps([region_label, phrase]),
                "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "reading_time": 4,
                "word_count": len(body.split()),
                "view_count": 600 + (idx * 433) % 9000,
                "is_featured": 0, "is_breaking": 0, "is_live": 0,
                "location": "",
                "source_url": f"https://www.bbc.com/news/articles/{slug}",
                "section_slug": section_slug,
                "subsection": region_label,
                "region": region_label,
                "video_url": "",
                "feature_tags": json.dumps([section_slug, "follow-up", "analysis"]),
                "content_type": "article",
            })
    return out


_ART_INSERT_SQL = (
    "INSERT INTO articles ("
    "slug, headline, subtitle, summary, body, author, category_id, "
    "hero_image, gallery_json, gallery_full_json, topics_json, "
    "published_at, reading_time, word_count, view_count, "
    "is_featured, is_breaking, is_live, location, source_url, "
    "section_slug, subsection, region, video_url, feature_tags, "
    "content_type) VALUES ("
    ":slug, :headline, :subtitle, :summary, :body, :author, :category_id, "
    ":hero_image, :gallery_json, :gallery_full_json, :topics_json, "
    ":published_at, :reading_time, :word_count, :view_count, "
    ":is_featured, :is_breaking, :is_live, :location, :source_url, "
    ":section_slug, :subsection, :region, :video_url, :feature_tags, "
    ":content_type)"
)


def insert_r3_articles(con: sqlite3.Connection, batch: list[dict]) -> int:
    """Bulk-insert R3 article batches; skip any slug already present."""
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM articles")}
    rows = [a for a in batch if a["slug"] not in existing]
    if not rows:
        return 0
    cur.executemany(_ART_INSERT_SQL, rows)
    return len(rows)


# ---- R3 comments: deep reply chains -------------------------------------

R3_COMMENT_TOP = [
    "Really helpful explainer — thank you for going into the detail.",
    "Wasn't expecting this story to land where it did. The closing paragraph is the kicker.",
    "Curious if the BBC has the underlying data set anywhere? Would love to play with it.",
    "I think you've buried the lead. The third quote is the most striking thing here.",
    "Hard to read this without thinking of last year's similar story — has anyone joined the dots?",
    "Strong reporting. The local angle in particular is something other outlets are missing.",
    "Could the BBC do a follow-up next week with a wider regional comparison?",
    "Glad to see this finally getting space. The community has been raising it for months.",
    "Three things stood out for me: the timeline, the missing context and the closing quote.",
    "Disagree with the framing but the underlying reporting feels rigorous. Hat tip.",
    "A bookmark for me. Will share with the parents' group tomorrow morning.",
    "BBC Verify on the imagery would add real value here. Any chance of a companion piece?",
    "If you've read this far, the chart in the middle is worth a second look.",
    "The expert quoted is the right person to ask. Saw her speak at the Royal Society last month.",
    "Solid editorial decision to lead with the chart rather than the politics.",
    "This is exactly the kind of story podcasts should pick up.",
    "I'd push back on point two — the data set has known biases.",
    "Important nuance that I haven't seen elsewhere. Thanks for the careful framing.",
    "Worth flagging that the policy was revised quietly in March, which the piece notes.",
    "What's the typical journalist's process for fact-checking a story this technical?",
]

R3_COMMENT_REPLIES = [
    "Yes — the link to the dataset is in the second paragraph, but it took me a while to find too.",
    "Good catch on the timeline; I missed that on first read.",
    "I'd push gently back: the third quote is moving, but the context paragraph is where the work is.",
    "Sharing this with my book group — we've been arguing about exactly this.",
    "Same. Hoping for a follow-up too.",
    "Worth noting that the regional comparison was promised in the previous piece and never materialised.",
    "Agreed. Local reporting is where the BBC genuinely outperforms other outlets.",
    "Have you tried the BBC Verify dashboard? It links source material for several of these claims.",
    "Honestly, the data set's biases are noted on its homepage — but most outlets ignore that.",
    "Bookmarked for the parents' group too.",
    "Yes, the March revision is buried in a Hansard footnote and almost no one reported it.",
    "On point two — both can be true. The data is biased AND the headline finding holds up.",
    "I'd love a BBC Verify thread on the imagery. The provenance question is the obvious next step.",
    "Same here. Will be interesting to see if next week's piece follows up on this.",
    "Fair, but the closing paragraph is editorialising in my view.",
    "Strongly agree. The community angle has been under-reported for a long time.",
    "Yes — and the comparable case from last year is worth re-reading alongside this.",
    "I think the editor's choice to lead with the chart was the right call.",
    "Sharing this in the family WhatsApp tonight.",
    "Going to listen to the related Sounds episode now — thanks for the pointer.",
]


def insert_r3_comments(con: sqlite3.Connection) -> int:
    """Add ~600 R3 comments across 80 popular articles, with 5-level
    reply chains. Skips if the R3 sentinel is already present."""
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if len(user_ids) < 2:
        return 0
    # Build article pool: top-viewed across many sections
    pool: list[int] = []
    for section in ("technology", "world", "uk", "sport", "business", "health",
                    "science", "politics", "entertainment", "football", "tennis",
                    "rugby", "europe", "asia", "africa", "scotland", "wales",
                    "england", "northern_ireland", "ai", "iplayer", "sounds",
                    "food", "travel", "bitesize"):
        ids = [r[0] for r in cur.execute(
            "SELECT id FROM articles WHERE section_slug=? "
            "ORDER BY view_count DESC LIMIT 5", (section,)
        )]
        pool.extend(ids)
    seen: set[int] = set()
    pool = [x for x in pool if not (x in seen or seen.add(x))][:90]

    base_ts = MIRROR_REFERENCE_DATE
    rows: list[tuple] = []   # (user_id, article_id, parent_marker, body, like, flag, ts)
    # We can't know parent ids until insert, so do top-level first, then
    # cascade replies per top-level.

    top_rows: list[tuple] = []
    for idx, art_id in enumerate(pool):
        n_top = 3 + (idx % 4)  # 3,4,5,6 top-level comments per article
        for j in range(n_top):
            uid = user_ids[(idx * 5 + j * 3) % len(user_ids)]
            body = R3_COMMENT_TOP[(idx * 7 + j * 11) % len(R3_COMMENT_TOP)]
            offset_h = (idx * 13 + j * 17) % (24 * 21)
            ts = base_ts - timedelta(hours=offset_h, minutes=(idx + j * 5) % 60)
            like = (idx * j + 3) % 32
            top_rows.append((uid, art_id, None, body, like, 0,
                             ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        top_rows,
    )
    inserted = len(top_rows)

    # Replies: 5-deep chains on every 2nd top-level comment
    fresh_top = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL AND body LIKE ? ORDER BY id",
        (R3_COMMENT_TOP[0][:30] + "%",),
    ))
    # The LIKE filter above is conservative; just grab the last `inserted` rows:
    fresh_top = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL ORDER BY id DESC LIMIT ?",
        (inserted,),
    ))
    fresh_top.reverse()

    for i, (cid, art_id, parent_uid, parent_created) in enumerate(fresh_top):
        if i % 2 != 0:
            continue
        # Build a 5-deep chain (depth 1..5)
        cur_parent = cid
        cur_parent_uid = parent_uid
        ts_parent = datetime.strptime(parent_created, "%Y-%m-%d %H:%M:%S")
        for depth in range(1, 6):
            ruid = user_ids[(cur_parent_uid + depth + i) % len(user_ids)]
            if ruid == cur_parent_uid:
                ruid = user_ids[(cur_parent_uid + depth + i + 1) % len(user_ids)]
            body = R3_COMMENT_REPLIES[(i * 3 + depth * 5) % len(R3_COMMENT_REPLIES)]
            ts_parent = ts_parent + timedelta(hours=depth, minutes=(depth * 7) % 60)
            cur.execute(
                "INSERT INTO comments (user_id, article_id, parent_id, body, "
                "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ruid, art_id, cur_parent, body, (depth * i) % 22, 0,
                 ts_parent.strftime("%Y-%m-%d %H:%M:%S")),
            )
            inserted += 1
            cur_parent = cur.lastrowid
            cur_parent_uid = ruid
    return inserted


# ---- R3 reading_history top-up -----------------------------------------

def insert_r3_reading_history(con: sqlite3.Connection) -> int:
    """Add reading-history rows on the new sections so reading-list/history
    tasks for the R3 sections are solvable."""
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    R3_SECTIONS = {
        "alice.j@test.com":   ["technology", "ai", "iplayer", "sounds", "bitesize"],
        "bob.c@test.com":     ["business", "europe", "us_canada", "food", "travel"],
        "carol.d@test.com":   ["health", "science", "earth", "weather", "bitesize"],
        "david.k@test.com":   ["sport", "football", "iplayer", "entertainment", "sounds"],
        "demo@bbcnews.local": ["world", "uk", "weather", "food", "iplayer"],
    }
    for uid, email in users:
        sections = R3_SECTIONS.get(email, ["world", "uk"])
        chosen: list[int] = []
        seen_local: set[int] = set()
        for sec in sections:
            ids = [r[0] for r in cur.execute(
                "SELECT id FROM articles WHERE section_slug=? "
                "ORDER BY view_count DESC LIMIT 8", (sec,)
            )]
            for a in ids:
                if a not in seen_local:
                    seen_local.add(a)
                    chosen.append(a)
        # Cap per user
        chosen = chosen[:30]
        for j, art_id in enumerate(chosen):
            # Skip if already in history
            already = cur.execute(
                "SELECT 1 FROM reading_history WHERE user_id=? AND article_id=?",
                (uid, art_id),
            ).fetchone()
            if already:
                continue
            ts = base_ts - timedelta(
                hours=(j * 11 + uid * 7) % (24 * 14),
                minutes=(j * 17) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO reading_history (user_id, article_id, viewed_at) VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


# ---- R3 bookmarks top-up -----------------------------------------------

def insert_r3_bookmarks(con: sqlite3.Connection) -> int:
    """Bookmark a couple of items per user in each new section so bookmark-CRUD
    tasks have realistic seeded state."""
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    pick_sections = ["food", "travel", "weather", "iplayer", "sounds", "bitesize"]
    for uid, email in users:
        for k, sec in enumerate(pick_sections):
            row = cur.execute(
                "SELECT id FROM articles WHERE section_slug=? "
                "ORDER BY view_count DESC LIMIT 1 OFFSET ?",
                (sec, (uid + k * 2) % 5),
            ).fetchone()
            if not row:
                continue
            art_id = row[0]
            already = cur.execute(
                "SELECT 1 FROM bookmarks WHERE user_id=? AND article_id=?",
                (uid, art_id),
            ).fetchone()
            if already:
                continue
            ts = base_ts - timedelta(days=(uid + k) % 14, hours=k * 3)
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO bookmarks (user_id, article_id, bookmarked_at) VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


# ---- R3 subscriptions top-up -------------------------------------------

def insert_r3_subscriptions(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone():
        return 0
    cols = [r[1] for r in cur.execute("PRAGMA table_info(topic_subscriptions)")]
    topic_col = "topic" if "topic" in cols else ("topic_slug" if "topic_slug" in cols else None)
    if topic_col is None:
        return 0
    has_cat = "category_slug" in cols
    has_freq = "frequency" in cols
    has_active = "active" in cols
    has_created = "created_at" in cols
    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    R3_TOPIC_MAP = {
        "alice.j@test.com":   [("technology", "AI"),       ("iplayer", "Drama"),   ("bitesize", "Computer Science")],
        "bob.c@test.com":     [("business",   "Markets"),  ("europe",  "EU"),      ("travel",   "Destinations")],
        "carol.d@test.com":   [("health",     "NHS"),      ("weather", "Forecast"),("bitesize", "Biology")],
        "david.k@test.com":   [("sport",      "Football"), ("iplayer", "Drama"),   ("sounds",   "Comedy")],
        "demo@bbcnews.local": [("food",       "Recipes"),  ("travel",  "UK"),      ("weather",  "London")],
    }
    for uid, email in users:
        for cat_slug, topic in R3_TOPIC_MAP.get(email, []):
            existing = cur.execute(
                f"SELECT 1 FROM topic_subscriptions WHERE user_id=? AND {topic_col}=?",
                (uid, topic),
            ).fetchone()
            if existing:
                continue
            row_cols = ["user_id"]
            row_vals: list = [uid]
            if has_cat:
                row_cols.append("category_slug"); row_vals.append(cat_slug)
            row_cols.append(topic_col); row_vals.append(topic)
            if has_freq:
                row_cols.append("frequency"); row_vals.append("weekly")
            if has_active:
                row_cols.append("active"); row_vals.append(1)
            if has_created:
                row_cols.append("created_at")
                row_vals.append((base_ts - timedelta(days=(uid + len(rows)) % 30)).strftime("%Y-%m-%d %H:%M:%S"))
            rows.append((row_cols, tuple(row_vals)))
    if not rows:
        return 0
    cols_used = rows[0][0]
    sql = (
        f"INSERT INTO topic_subscriptions ({', '.join(cols_used)}) "
        f"VALUES ({', '.join(['?'] * len(cols_used))})"
    )
    cur.executemany(sql, [r[1] for r in rows])
    return len(rows)


# ---- R3 reading-list top-up --------------------------------------------

def insert_r3_reading_list(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone():
        return 0
    cols = [r[1] for r in cur.execute("PRAGMA table_info(reading_list_items)")]
    has_folder = "folder" in cols
    has_priority = "priority" in cols
    users = list(cur.execute("SELECT id, email FROM users ORDER BY id"))
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    R3_RL_MAP = {
        "alice.j@test.com":   ("Innovation", ["ai", "technology", "iplayer", "bitesize"]),
        "bob.c@test.com":     ("Business",   ["business", "europe", "travel", "food"]),
        "carol.d@test.com":   ("Wellbeing",  ["health", "science", "weather", "bitesize"]),
        "david.k@test.com":   ("Sport",      ["sport", "football", "iplayer", "sounds"]),
        "demo@bbcnews.local": ("Weekend",    ["food", "travel", "iplayer", "weather"]),
    }
    for uid, email in users:
        folder, sections = R3_RL_MAP.get(email, ("Read Later", ["world", "uk"]))
        for k, sec in enumerate(sections):
            ids = [r[0] for r in cur.execute(
                "SELECT id FROM articles WHERE section_slug=? "
                "ORDER BY view_count DESC LIMIT 2 OFFSET ?",
                (sec, (uid + k) % 4),
            )]
            for art_id in ids:
                already = cur.execute(
                    "SELECT 1 FROM reading_list_items WHERE user_id=? AND article_id=?",
                    (uid, art_id),
                ).fetchone()
                if already:
                    continue
                ts_str = (base_ts - timedelta(days=(uid + k) % 20, hours=k * 4)
                          ).strftime("%Y-%m-%d %H:%M:%S")
                row_cols = ["user_id", "article_id"]
                row_vals: list = [uid, art_id]
                if has_folder:
                    row_cols.append("folder"); row_vals.append(folder)
                if has_priority:
                    row_cols.append("priority"); row_vals.append("normal")
                row_cols.append("added_at"); row_vals.append(ts_str)
                rows.append((row_cols, tuple(row_vals)))
    if not rows:
        return 0
    cols_used = rows[0][0]
    sql = (
        f"INSERT INTO reading_list_items ({', '.join(cols_used)}) "
        f"VALUES ({', '.join(['?'] * len(cols_used))})"
    )
    cur.executemany(sql, [r[1] for r in rows])
    return len(rows)


# ---- R3 explainer + Q&A articles (broadens corpus to 2500+) ------------

EXPLAINER_TOPICS: list[tuple[str, str, str]] = [
    # section_slug, topic, lede
    ("politics",    "House of Lords reform",      "What the latest proposals would actually change."),
    ("politics",    "Voter ID rules at elections", "Who's required to show it, who is exempted."),
    ("politics",    "Devolution settlements",     "Where Westminster ends and Holyrood begins."),
    ("politics",    "Local government funding",   "How councils get money and why it isn't enough."),
    ("politics",    "Civil service reform",       "What 'civil service modernisation' actually means."),
    ("business",    "Bank of England base rate",  "Why the MPC moves rates and how it filters through."),
    ("business",    "Inheritance tax thresholds", "Who pays it and how the nil-rate band has frozen."),
    ("business",    "ISA allowance changes",      "Cash, stocks and the lifetime ISA in one explainer."),
    ("business",    "National insurance bands",   "Employee, employer and self-employed contributions."),
    ("business",    "Corporation tax rate",       "How the headline rate compares with G7 peers."),
    ("business",    "Energy price cap",           "How the cap is set and who actually pays it."),
    ("business",    "Stamp duty thresholds",      "First-time buyer relief, additional properties, holiday lets."),
    ("business",    "Pension lifetime allowance", "What the abolition of the LTA changes for high earners."),
    ("technology",  "End-to-end encryption",      "How it works and what the political fight is about."),
    ("technology",  "Quantum computing",          "Qubits, decoherence and why it's still 5 years away."),
    ("technology",  "Generative AI hallucinations","Why large language models make things up."),
    ("technology",  "Cloud computing regions",    "Why a single region outage takes down half the internet."),
    ("technology",  "Open source supply chains",  "The xz backdoor and how to spot the next one."),
    ("technology",  "Two-factor authentication",  "SMS, TOTP and FIDO keys, ranked."),
    ("technology",  "Browser cookies",            "Strict, lax, none — and the eventual third-party demise."),
    ("technology",  "Right to repair",            "What the new UK rules actually require."),
    ("technology",  "Smart meter rollout",        "What the data is used for and what it isn't."),
    ("science",     "CRISPR gene editing",        "From Nobel science to NHS-approved therapy."),
    ("science",     "Carbon capture and storage", "How CCS works and why it's controversial."),
    ("science",     "Antibiotic resistance",      "Why the WHO calls it the next pandemic."),
    ("science",     "Dark matter searches",       "What it is, what it isn't and how we'd know."),
    ("science",     "James Webb infrared",        "What 'first light from the early universe' really means."),
    ("science",     "El Nino and La Nina",        "How the Pacific drives the British winter."),
    ("science",     "mRNA vaccines",              "From COVID to cancer trials in five years."),
    ("science",     "Mitochondrial DNA",          "What it tells us and what it doesn't."),
    ("science",     "Plastic in the ocean",       "Why microplastics are the harder problem to solve."),
    ("health",      "NHS waiting list rules",     "The 18-week target and why it slips."),
    ("health",      "GP appointment access",      "Why getting an appointment got harder."),
    ("health",      "Cancer screening ages",      "Who's invited, how often and the new tests on the way."),
    ("health",      "Mental health crisis care",  "What you should expect from local services."),
    ("health",      "Dental NHS contract",        "Why finding an NHS dentist is so hard right now."),
    ("health",      "Maternity safety reviews",   "What the last three inquiries actually said."),
    ("health",      "Social care funding",        "The cap on costs and the assessment threshold."),
    ("health",      "Statins and side effects",   "What 4 million prescriptions a year are doing."),
    ("health",      "ADHD adult diagnosis",       "Why waiting times have grown — and the right-to-choose route."),
    ("health",      "Long COVID research",        "Where the science is, two years on."),
    ("uk",          "Cost of a UK driving test",  "How prices and waiting times stack up by region."),
    ("uk",          "Council tax band review",    "How to challenge yours and what's likely to change."),
    ("uk",          "Right to roam law",          "Where you can walk and the campaign to widen it."),
    ("uk",          "Free school meals",          "Who qualifies and where the threshold is now."),
    ("uk",          "Student finance changes",    "The new repayment threshold and 40-year term."),
    ("uk",          "Housing planning rules",     "What 'green belt' and 'grey belt' actually mean."),
    ("uk",          "Bus franchising powers",     "What the new transport law lets cities do."),
    ("uk",          "Water company fines",        "How sewage spills are policed and penalised."),
    ("world",       "G7 vs G20",                  "Who's in each, what they discuss and how decisions stick."),
    ("world",       "UN Security Council vetoes", "The five permanent members and how reform has stalled."),
    ("world",       "NATO Article 5",             "When it has been invoked and what 'collective defence' means."),
    ("world",       "Schengen visa rules",        "Travel without checks across 27 European countries."),
    ("world",       "Climate COP process",        "How a COP agreement actually becomes national policy."),
    ("world",       "WTO dispute settlement",     "Why the system is mostly broken."),
    ("world",       "ICC arrest warrants",        "Jurisdiction, enforcement and the politics of compliance."),
    ("world",       "OPEC+ oil quotas",           "How production cuts ripple through to the pump."),
    ("europe",      "European Parliament",        "Who the MEPs are and what they actually decide."),
    ("europe",      "Schengen border checks",     "Why some countries are reintroducing them."),
    ("europe",      "Eurozone vs EU",             "The 20 in vs the 27 — and why the UK was neither."),
    ("europe",      "EU AI Act",                  "The risk-based tiering and what it means for tools."),
    ("asia",        "Taiwan strait dynamics",     "The military, economic and political stakes explained."),
    ("asia",        "China South China Sea",      "The nine-dash line and the rival claims."),
    ("asia",        "India general election",     "The world's biggest democratic exercise."),
    ("asia",        "Japan demographic crunch",   "What 'super-aged' means in practice."),
    ("africa",      "Sahel coups timeline",       "Three years of military takeovers, country by country."),
    ("africa",      "African Union",              "The continental body and its peer review mechanism."),
    ("africa",      "Lobito Corridor",            "The new rail route reshaping critical minerals."),
    ("middle_east", "GCC vs Iran",                "The rivalry that shapes every Gulf decision."),
    ("middle_east", "Two-state solution",         "What it would actually require to revive."),
    ("us_canada",   "US Supreme Court terms",     "How a 'session' works and why timing matters."),
    ("us_canada",   "Electoral college math",     "The 270 path, swing states and faithless electors."),
    ("us_canada",   "US debt ceiling",            "Why it keeps coming back to the brink."),
    ("us_canada",   "Canada equalisation",        "How federal transfers shape Canadian politics."),
    ("latin_america","Mercosur trade bloc",       "Members, observers and the EU deal that won't close."),
    ("sport",       "VAR explained",              "When the on-field decision stands and when it doesn't."),
    ("sport",       "FFP and PSR rules",          "How football's financial regulations actually work."),
    ("sport",       "Cricket ODI vs Test",        "Format differences, calendar friction and the future."),
    ("sport",       "Olympic medal tally",        "Why ranking by golds, totals or per capita gives different answers."),
    ("sport",       "Tennis Hawk-Eye system",     "The challenge protocol and the new electronic-line era."),
    ("sport",       "Six Nations qualification",  "How promotion and relegation works in rugby."),
    ("sport",       "Premier League TV deal",     "How the cash gets shared between top six and rest."),
    ("entertainment","Streaming subscription wars","Why the price keeps going up and ad tiers are everywhere."),
    ("entertainment","BAFTA vs Oscar",            "Different juries, different politics, same headliners."),
    ("entertainment","Music streaming royalties", "Pence-per-stream and where the money actually goes."),
    ("entertainment","UK theatre subsidies",      "Who funds what and the geography of arts funding."),
    ("arts",        "British Museum repatriation","The Parthenon Marbles and the legal framework."),
    ("arts",        "Turner Prize controversies", "Six decades of provocations and the patterns within."),
    ("culture",     "BBC licence fee future",     "Options for funding public broadcasting after 2027."),
    ("culture",     "Booker Prize criteria",      "Why the rules keep changing and what's eligible now."),
    ("earth",       "1.5 degrees vs 2 degrees",   "Why the difference matters and what's already locked in."),
    ("earth",       "Renewable subsidies CfDs",   "How Contracts for Difference set strike prices."),
    ("earth",       "Heat pump uptake",           "Costs, schemes and the grid implications."),
    ("earth",       "Lithium mining",             "Where it comes from and the environmental costs."),
    ("ai",          "Foundation model training",  "Pretraining, fine-tuning and RLHF in one diagram."),
    ("ai",          "AI safety institutes",       "Bletchley, Seoul and the global testing network."),
    ("ai",          "AI in the NHS",              "Trials, ethics review and the imaging breakthroughs."),
    ("ai",          "Compute export controls",    "What 'sanctioned chips' actually means."),
    ("bbcverify",   "Geolocation techniques",     "How open-source investigators pinpoint a video."),
    ("bbcverify",   "Deepfake detection",         "Why it's hard and where the tools are getting better."),
    ("bbcverify",   "Satellite imagery sources",  "Free vs commercial, resolution, and update cadence."),
    ("bbcverify",   "Provenance metadata C2PA",   "How signed-image standards work."),
    ("in_pictures", "Photo essay weekly",         "A curated set from BBC News picture editors."),
    ("in_pictures", "Year in pictures",           "The defining images of the past twelve months."),
    ("travel",      "ESTA vs ETIAS",              "US and EU electronic-authorisation rules in plain English."),
    ("travel",      "Airline compensation rules", "What you're actually owed when a flight is delayed."),
    ("travel",      "Train pass guide",           "Interrail vs single-country passes, by length of trip."),
    ("food",        "Ultra-processed food",       "Why nutritionists worry about NOVA-4 categories."),
    ("food",        "Plant-based labelling",      "What 'vegan' actually means on a pack."),
    ("food",        "Sourdough vs commercial bread","The fermentation difference and the gut-health claim."),
    ("food",        "Single-origin coffee",       "What you're paying for at speciality coffee shops."),
    ("weather",     "Storm naming explained",     "Who names them and how the alphabet works."),
    ("weather",     "Met Office warning colours", "Yellow, amber and red — what each means."),
    ("weather",     "UK heatwave thresholds",     "Why 30°C in London differs from 30°C in Inverness."),
]


def synth_explainer_articles(con: sqlite3.Connection, hero_pool: list[str]) -> list[dict]:
    cur = con.cursor()
    cat_lookup = {r[1]: r[0] for r in cur.execute("SELECT id, slug FROM categories")}
    out = []
    base_ts = MIRROR_REFERENCE_DATE
    # We want ≥400 explainers. 105 unique topics × ~4 variants ≈ 420.
    variant_suffixes = [
        ("",                              "Q&A",            ""),
        (" — five things you need to know"," Five points",   "Quick read"),
        (" — analysis",                    " Analysis",     "Analysis"),
        (" — what changes from this autumn"," From autumn",  "Forward-looking"),
    ]
    for v_idx, (suffix, kind, blurb_extra) in enumerate(variant_suffixes):
        for idx, (sec, topic, lede) in enumerate(EXPLAINER_TOPICS):
            cid = cat_lookup.get(sec) or cat_lookup.get("news")
            title = f"{topic}{suffix}".strip()
            slug = _det_slug(f"exp-{v_idx}-{sec}", title)
            hero = hero_pool[(_det_int(slug) + v_idx * 17 + idx * 3) % len(hero_pool)]
            ts = base_ts - timedelta(days=(idx * 3 + v_idx * 19) % 90,
                                     hours=(idx * 5 + v_idx * 7) % 24)
            body = (
                f"{lede}\n\n"
                f"BBC News explainer ({kind}). {blurb_extra} The headline points are "
                f"summarised below, followed by the full picture and the relevant "
                f"figures we've been able to verify with on-the-record sources.\n\n"
                f"Headline points: (1) what the rule or change is now, (2) who it "
                f"affects in practice, (3) what the political and economic context "
                f"is, (4) what credible critics are saying, (5) where you can read "
                f"more from BBC Verify and our specialist correspondents.\n\n"
                f"Background: this piece is part of a continuing explainer series. "
                f"Earlier instalments are linked at the foot of the page and a "
                f"companion BBC Sounds podcast goes deeper on the technical "
                f"questions our newsroom isn't best placed to answer in writing.\n\n"
                f"Have a question we haven't answered? Submit it via the BBC News "
                f"contact form and we'll address the most common ones in next "
                f"week's update."
            )
            out.append({
                "slug": slug,
                "headline": title,
                "subtitle": lede[:300],
                "summary": lede[:300],
                "body": body,
                "author": "BBC News",
                "category_id": cid,
                "hero_image": hero,
                "gallery_json": "[]",
                "gallery_full_json": "{}",
                "topics_json": json.dumps([sec.replace('_', ' ').title(), "Explainer", kind.strip()]),
                "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "reading_time": 5,
                "word_count": len(body.split()),
                "view_count": 1000 + ((idx * 89 + v_idx * 271) % 14000),
                "is_featured": 0, "is_breaking": 0, "is_live": 0,
                "location": "",
                "source_url": f"https://www.bbc.com/news/explainers/{slug}",
                "section_slug": sec,
                "subsection": "Explainer",
                "region": "",
                "video_url": "",
                "feature_tags": json.dumps(["explainer", sec, kind.lower().strip()]),
                "content_type": "article",
            })
    return out


# ---- R3 sentinel + dispatcher ------------------------------------------

def plant_r3_sentinel(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    already = cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone()
    if already:
        return
    cur.execute(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, 1, None, R3_SENTINEL_BODY, 0, 1,
         MIRROR_REFERENCE_DATE.strftime("%Y-%m-%d %H:%M:%S")),
    )


def bake_r3(con: sqlite3.Connection) -> dict[str, int]:
    """Apply all R3 additions. Idempotent — R3 sentinel gates re-runs of
    article/comment/etc. inserts. ensure_r3_categories is allowed to run
    on every call so already-baked DBs catch up on category additions."""
    stats: dict[str, int] = {}
    # Always-on: catch up new categories even on re-runs.
    stats["new_categories"] = ensure_r3_categories(con)

    if con.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R3_SENTINEL_BODY,)
    ).fetchone():
        stats["already_baked"] = 1
        return stats

    hero_pool = _hero_image_pool(con)
    if not hero_pool:
        hero_pool = [""]  # graceful

    article_batches: list[list[dict]] = [
        synth_food_articles(con, hero_pool),
        synth_travel_articles(con, hero_pool),
        synth_weather_articles(con, hero_pool),
        synth_iplayer_articles(con, hero_pool),
        synth_sounds_articles(con, hero_pool),
        synth_bitesize_articles(con, hero_pool),
        synth_sport_live_articles(con, hero_pool),
        synth_video_clips(con, hero_pool),
        synth_regional_followups(con, hero_pool),
        synth_explainer_articles(con, hero_pool),
    ]
    total = 0
    for batch in article_batches:
        total += insert_r3_articles(con, batch)
    stats["new_articles"] = total

    stats["new_comments"] = insert_r3_comments(con)
    stats["new_reading_history"] = insert_r3_reading_history(con)
    stats["new_bookmarks"] = insert_r3_bookmarks(con)
    stats["new_subscriptions"] = insert_r3_subscriptions(con)
    stats["new_reading_list"] = insert_r3_reading_list(con)

    plant_r3_sentinel(con)
    return stats


# =======================================================================
# R4: BBC regional editions, deep sub-pages, multi-step features
# =======================================================================

R4_NEW_CATEGORIES: list[tuple[str, str, str, str, int, str]] = [
    # slug, name, color, parent_slug, sort_order, description
    ("bbc_africa",   "BBC Africa",          "#000000", "world",        201,
     "BBC Africa: stories from across the continent in English, French and Swahili."),
    ("bbc_brasil",   "BBC Brasil",          "#000000", "latin_america",202,
     "BBC Brasil: jornalismo em portugues, das Americas para o mundo lusofono."),
    ("bbc_mundo",    "BBC News Mundo",      "#000000", "latin_america",203,
     "BBC News Mundo: noticias en espanol para America Latina y el mundo hispanohablante."),
    ("bbc_arabic",   "BBC Arabic",          "#000000", "middle_east",  204,
     "BBC Arabic: news in Arabic from the Middle East and North Africa region."),
    ("bbc_persian",  "BBC Persian",         "#000000", "middle_east",  205,
     "BBC Persian: news in Farsi for Iran, Afghanistan and the Persian-speaking diaspora."),
    ("bbc_russian",  "BBC Russian",         "#000000", "europe",       206,
     "BBC Russian: independent news in Russian for Russia and the broader region."),
    ("bbc_china",    "BBC News China",      "#000000", "asia",         207,
     "BBC News China: reporting on China, Hong Kong and Taiwan in English and Chinese."),
    ("bbc_india",    "BBC News India",      "#000000", "asia",         208,
     "BBC News India: in-depth reporting on India and South Asia."),
    ("breaking_news","Breaking News",       "#bb1919", "news",         11,
     "Breaking news from BBC News: developing stories monitored by our newsroom."),
    ("video_clips",  "Video clips",         "#000000", "video",        21,
     "Short-form video clips from BBC News reporters around the world."),
    ("podcasts_genres","Podcast genres",    "#000000", "podcasts",     31,
     "Browse BBC podcasts by genre: news, history, comedy, drama, science."),
    ("iplayer_categories","iPlayer categories","#000000","iplayer",    41,
     "BBC iPlayer programmes by category: drama, documentary, comedy, sport, news."),
    ("multi_step",   "Long reads",          "#000000", "",             251,
     "BBC Long reads: deeply reported features that follow a story across weeks or months."),
]


def ensure_r4_categories(con: sqlite3.Connection) -> int:
    """Insert any missing R4 categories. Idempotent."""
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM categories")}
    added = 0
    for slug, name, color, parent, order, desc in R4_NEW_CATEGORIES:
        if slug in existing:
            continue
        cur.execute(
            "INSERT INTO categories (slug, name, color, icon, parent_slug, "
            "sort_order, description, subtitle) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (slug, name, color, "", parent, order, desc, desc[:250]),
        )
        added += 1
    return added


# ---- R4 country / region pools -----------------------------------------

AFRICAN_COUNTRIES: list[tuple[str, str]] = [
    ("Nigeria", "Lagos"), ("Kenya", "Nairobi"), ("South Africa", "Johannesburg"),
    ("Ethiopia", "Addis Ababa"), ("Ghana", "Accra"), ("Senegal", "Dakar"),
    ("Tanzania", "Dar es Salaam"), ("Uganda", "Kampala"), ("Rwanda", "Kigali"),
    ("Egypt", "Cairo"), ("Morocco", "Rabat"), ("Tunisia", "Tunis"),
    ("Algeria", "Algiers"), ("Sudan", "Khartoum"), ("Zimbabwe", "Harare"),
    ("Zambia", "Lusaka"), ("Botswana", "Gaborone"), ("Namibia", "Windhoek"),
    ("Mozambique", "Maputo"), ("Cameroon", "Yaounde"), ("Ivory Coast", "Abidjan"),
    ("Mali", "Bamako"), ("Burkina Faso", "Ouagadougou"), ("Madagascar", "Antananarivo"),
]

LATIN_AMERICA_COUNTRIES: list[tuple[str, str, str]] = [
    ("Brazil", "Sao Paulo", "pt"), ("Argentina", "Buenos Aires", "es"),
    ("Mexico", "Mexico City", "es"), ("Colombia", "Bogota", "es"),
    ("Chile", "Santiago", "es"), ("Peru", "Lima", "es"),
    ("Venezuela", "Caracas", "es"), ("Ecuador", "Quito", "es"),
    ("Bolivia", "La Paz", "es"), ("Paraguay", "Asuncion", "es"),
    ("Uruguay", "Montevideo", "es"), ("Costa Rica", "San Jose", "es"),
    ("Panama", "Panama City", "es"), ("Cuba", "Havana", "es"),
    ("Dominican Republic", "Santo Domingo", "es"), ("Guatemala", "Guatemala City", "es"),
    ("Honduras", "Tegucigalpa", "es"), ("Nicaragua", "Managua", "es"),
    ("El Salvador", "San Salvador", "es"),
]

MIDDLE_EAST_COUNTRIES: list[tuple[str, str]] = [
    ("Saudi Arabia", "Riyadh"), ("Iran", "Tehran"), ("Iraq", "Baghdad"),
    ("Syria", "Damascus"), ("Lebanon", "Beirut"), ("Jordan", "Amman"),
    ("Israel", "Jerusalem"), ("Palestinian Territories", "Ramallah"),
    ("Egypt", "Cairo"), ("UAE", "Abu Dhabi"), ("Qatar", "Doha"),
    ("Kuwait", "Kuwait City"), ("Bahrain", "Manama"), ("Oman", "Muscat"),
    ("Yemen", "Sanaa"), ("Turkey", "Istanbul"), ("Afghanistan", "Kabul"),
]

ASIAN_COUNTRIES: list[tuple[str, str]] = [
    ("China", "Beijing"), ("India", "New Delhi"), ("Japan", "Tokyo"),
    ("South Korea", "Seoul"), ("North Korea", "Pyongyang"),
    ("Indonesia", "Jakarta"), ("Vietnam", "Hanoi"), ("Thailand", "Bangkok"),
    ("Philippines", "Manila"), ("Malaysia", "Kuala Lumpur"),
    ("Singapore", "Singapore"), ("Pakistan", "Islamabad"),
    ("Bangladesh", "Dhaka"), ("Sri Lanka", "Colombo"), ("Myanmar", "Naypyidaw"),
    ("Cambodia", "Phnom Penh"), ("Laos", "Vientiane"), ("Nepal", "Kathmandu"),
    ("Mongolia", "Ulaanbaatar"), ("Taiwan", "Taipei"), ("Hong Kong", "Hong Kong"),
]

EUROPEAN_COUNTRIES: list[tuple[str, str]] = [
    ("France", "Paris"), ("Germany", "Berlin"), ("Italy", "Rome"),
    ("Spain", "Madrid"), ("Portugal", "Lisbon"), ("Greece", "Athens"),
    ("Netherlands", "Amsterdam"), ("Belgium", "Brussels"),
    ("Switzerland", "Bern"), ("Austria", "Vienna"), ("Sweden", "Stockholm"),
    ("Norway", "Oslo"), ("Denmark", "Copenhagen"), ("Finland", "Helsinki"),
    ("Iceland", "Reykjavik"), ("Ireland", "Dublin"), ("Poland", "Warsaw"),
    ("Czechia", "Prague"), ("Hungary", "Budapest"), ("Romania", "Bucharest"),
    ("Bulgaria", "Sofia"), ("Croatia", "Zagreb"), ("Serbia", "Belgrade"),
    ("Ukraine", "Kyiv"), ("Russia", "Moscow"), ("Belarus", "Minsk"),
]

UK_POSTCODES: list[tuple[str, str, str]] = [
    ("SW1A", "London Westminster", "England"),
    ("EC1V", "London Clerkenwell", "England"),
    ("E14",  "London Canary Wharf", "England"),
    ("N1",   "London Islington", "England"),
    ("SE1",  "London Bermondsey", "England"),
    ("W1A",  "London Marylebone", "England"),
    ("M1",   "Manchester city centre", "England"),
    ("M14",  "Manchester Fallowfield", "England"),
    ("B1",   "Birmingham city centre", "England"),
    ("B15",  "Birmingham Edgbaston", "England"),
    ("LS1",  "Leeds city centre", "England"),
    ("L1",   "Liverpool city centre", "England"),
    ("L18",  "Liverpool Mossley Hill", "England"),
    ("NE1",  "Newcastle upon Tyne", "England"),
    ("S1",   "Sheffield city centre", "England"),
    ("NG1",  "Nottingham city centre", "England"),
    ("BS1",  "Bristol city centre", "England"),
    ("BN1",  "Brighton North Laine", "England"),
    ("PL1",  "Plymouth Barbican", "England"),
    ("NR2",  "Norwich Tombland", "England"),
    ("CB2",  "Cambridge city centre", "England"),
    ("OX1",  "Oxford city centre", "England"),
    ("YO1",  "York Minster", "England"),
    ("BA1",  "Bath city centre", "England"),
    ("EX1",  "Exeter city centre", "England"),
    ("EH1",  "Edinburgh Old Town", "Scotland"),
    ("EH8",  "Edinburgh Holyrood", "Scotland"),
    ("G1",   "Glasgow city centre", "Scotland"),
    ("G12",  "Glasgow West End", "Scotland"),
    ("AB10", "Aberdeen city centre", "Scotland"),
    ("DD1",  "Dundee Waterfront", "Scotland"),
    ("IV1",  "Inverness Highlands", "Scotland"),
    ("FK8",  "Stirling Castle", "Scotland"),
    ("KY16", "St Andrews", "Scotland"),
    ("CF10", "Cardiff city centre", "Wales"),
    ("CF24", "Cardiff Bay", "Wales"),
    ("SA1",  "Swansea Maritime", "Wales"),
    ("NP20", "Newport Wales", "Wales"),
    ("LL11", "Wrexham", "Wales"),
    ("LL57", "Bangor Gwynedd", "Wales"),
    ("BT1",  "Belfast city centre", "Northern Ireland"),
    ("BT15", "Belfast North", "Northern Ireland"),
    ("BT47", "Derry Londonderry", "Northern Ireland"),
    ("BT28", "Lisburn", "Northern Ireland"),
    ("BT34", "Newry", "Northern Ireland"),
]
# Headline patterns for regional editions — generic enough to apply across
# many countries without sounding repetitive. Drawn from real BBC Africa
# / BBC Brasil / BBC Mundo headline shapes (May 2026).
AFRICA_HEADLINES = [
    ("Election preparations begin in {country} as candidates file papers",
     "Independent electoral commission opens nominations period in {capital}; opposition groups raise procedural concerns."),
    ("{country} central bank holds key rate amid currency pressure",
     "Monetary authorities in {capital} resist political calls for an immediate cut as inflation softens slowly."),
    ("Floods displace thousands in northern {country}",
     "Humanitarian agencies appeal for funds after rivers burst banks; shelter and clean water are the immediate priorities."),
    ("Drought worsens food security in parts of {country}",
     "Crop failures across the sahel-influenced belt push more households into food insecurity, the WFP warns."),
    ("Young entrepreneurs in {capital} pitch climate-tech ideas",
     "A startup accelerator in {country} backs 30 founders working on solar mini-grids and irrigation."),
    ("{country} mourns veteran journalist who broke the story of the decade",
     "Tributes pour in across {capital} for a reporter whose work shaped the country's political conversation."),
    ("Power cuts return to {country} as grid maintenance overruns",
     "Authorities in {capital} apologise to consumers as scheduled outages extend beyond the published schedule."),
    ("Women's football in {country} attracts record sponsorship",
     "The national league signs a multi-year deal that should treble player wages."),
    ("Mobile money in {country} now used by 8 in 10 adults",
     "Central bank data shows mobile wallets overtaking commercial bank accounts; regulators flag fraud."),
    ("Public hospitals in {country} expand cancer screening",
     "A new screening programme launches in {capital} with WHO support, targeting cervical and breast cancers."),
    ("{country} signs trade pact with neighbour states",
     "The agreement reduces tariffs on processed goods and is expected to boost cross-border trade in {capital}."),
    ("Tourism rebounds in {country} as visa policy relaxes",
     "Hotel occupancy in {capital} returns to pre-pandemic levels; safari operators report fully booked seasons."),
    ("Drought-resistant maize trials show promise across {country}",
     "Agricultural researchers in {capital} say new hybrids yield 20% more in dry seasons without irrigation."),
    ("Civil society groups in {country} sound alarm on press freedom",
     "Journalists in {capital} say recent legal cases are designed to chill investigative reporting."),
    ("{country} signs renewable energy pact for 500MW solar park",
     "Construction near {capital} is due to begin within 12 months; community groups demand local hiring."),
]

LATAM_HEADLINES = [
    ("{country} announces fiscal package amid budget pressure",
     "The finance ministry in {capital} unveils new spending cuts and tax reforms; markets respond cautiously."),
    ("Indigenous leaders in {country} demand land rights review",
     "Communities living near {capital} call on the federal government to honour constitutional protections."),
    ("Amazonian deforestation hits 12-month low in {country}",
     "Satellite imagery shared with BBC News shows enforcement stepping up in protected reserves."),
    ("{country} football: rivalry match ends in late drama",
     "A late goal at the national stadium in {capital} settles a fixture watched by millions."),
    ("Inflation easing in {country} as central bank holds rate",
     "Headline CPI in {country} dipped for the third consecutive month, encouraging the bank in {capital}."),
    ("Migration corridor: thousands head north through {country}",
     "Authorities in {capital} report unprecedented numbers of families travelling on foot toward the US border."),
    ("{country} elections: front-runner widens lead in latest poll",
     "A national survey in {capital} shows the gap stretching as voters cite the economy as their top issue."),
    ("Femicide protests fill streets in {capital}",
     "Marchers in {country} demand stronger sentences and faster police response to gender violence."),
    ("{country} writers shortlisted for international literary prize",
     "Two novelists from {capital} are named on the shortlist for one of the world's richest literary awards."),
    ("Mining royalty dispute in {country} reaches court",
     "Provincial governments take the federal government to court over how royalties are shared from copper exports."),
    ("Carnival in {country} attracts record-breaking crowds",
     "Tourism officials in {capital} estimate visitor numbers at their highest since records began."),
    ("{country} football: women's national team beats world champions",
     "An upset win in {capital} sees the team qualify for next year's continental championships."),
    ("{country} faces shortage of teachers in rural areas",
     "Education unions warn that pay and working conditions are pushing teachers in {capital} into private schools."),
    ("Drug-trafficking network dismantled across {country}",
     "Federal agents in {capital} announce arrests spanning three states and seize a record haul of cocaine."),
    ("{country} cinema: new wave of directors heads to Cannes",
     "Three feature films from {country} are accepted into the official Cannes selection this year."),
]

MIDEAST_HEADLINES = [
    ("{country} announces ceasefire framework after weeks of talks",
     "Mediators in {capital} say a sequenced agreement is now in writing and awaits approval from both sides."),
    ("Tensions rise on {country}'s northern border",
     "Cross-border exchanges of fire are reported overnight; observers in {capital} call for restraint."),
    ("{country} central bank intervenes to support currency",
     "Reserves drawn down by an estimated 1.5bn dollars in three days; analysts in {capital} doubt the strategy is sustainable."),
    ("Aid convoys reach besieged area of {country}",
     "Trucks carrying food and medicine cross into territory cut off for weeks; UN officials describe the situation as critical."),
    ("{country} women's rights groups march in {capital}",
     "Protesters call for legal reforms on personal status laws; the rally is the largest in five years."),
    ("Oil exports from {country} rise as quotas relax",
     "Energy ministry data shows production in {country} up 4% month-on-month with most cargo bound for Asia."),
    ("{country} youth unemployment is at a 15-year high",
     "Government statistics in {capital} confirm a generational squeeze that economists call a ticking bomb."),
    ("Universities in {country} reopen after months of disruption",
     "Students return to lecture halls in {capital} amid heavy security; final exams have been rescheduled."),
    ("{country} signs nuclear cooperation pact with European partner",
     "The agreement on civilian nuclear research is unrelated to military matters, the foreign ministry in {capital} says."),
    ("Cultural festival in {country} draws international visitors",
     "A two-week celebration in {capital} of music, film and literature opens with a sold-out concert."),
    ("Floods damage farmland in southern {country}",
     "Authorities in {capital} declare a state of emergency for two provinces; aid agencies prepare to assist."),
    ("{country} cabinet reshuffled after parliamentary debate",
     "Three new ministers are sworn in at {capital}'s presidential palace, including the country's first female finance minister."),
]

ASIA_HEADLINES = [
    ("{country} typhoon causes widespread damage along coast",
     "Authorities in {capital} confirm casualties and major infrastructure damage; rescue operations are underway."),
    ("Tech sector in {country} hires aggressively despite global slowdown",
     "Companies near {capital} say AI-related roles are pulling in graduates at record salaries."),
    ("{country} parliament passes long-awaited data protection bill",
     "The law in {capital} brings the country closer to international privacy standards; civil liberties groups call it a partial win."),
    ("Air quality alert across northern {country}",
     "Schools in {capital} suspend outdoor activities as PM2.5 readings surge to hazardous levels."),
    ("{country} cricket: T20 league signs landmark broadcast deal",
     "A multi-billion-dollar agreement makes the league one of the richest in world sport."),
    ("Earthquake shakes parts of {country}; no casualties reported",
     "A magnitude 5.6 tremor rattles homes in {capital}'s suburbs and prompts brief evacuation."),
    ("{country} announces electric vehicle subsidy extension",
     "Drivers buying EVs in {country} get extended tax breaks; the policy aims to cut urban air pollution in {capital}."),
    ("Manufacturing exports from {country} hit five-year high",
     "Customs data in {capital} shows surge in semiconductor and machinery shipments to Europe."),
    ("{country} space agency launches lunar mission",
     "A rocket carrying a small lander lifts off from a coastal base; engineers in {capital} celebrate a textbook ascent."),
    ("Heritage temple in {country} reopens after restoration",
     "Conservators in {capital} unveil a five-year project that has stabilised crumbling stonework."),
    ("{country} signs free-trade pact with Pacific neighbours",
     "The agreement removes tariffs on 90% of goods and is expected to boost exports through {capital}'s main port."),
    ("Climate refugees in {country} resettled in higher villages",
     "Coastal communities near {capital} are moved inland as sea levels reshape the shoreline."),
]

EUROPE_HEADLINES = [
    ("{country} forms new coalition government after long talks",
     "Parties shake hands in {capital} on a programme that prioritises housing, defence and climate."),
    ("{country} central bank trims rate as inflation eases",
     "Officials in {capital} say price pressures are now within target range for the first time in 18 months."),
    ("{country} signs defence pact with NATO neighbours",
     "Joint exercises announced for next year; the agreement was signed in {capital}'s government quarter."),
    ("Migration policy reshuffled in {country} after court ruling",
     "Justices in {capital} strike down two provisions of the country's asylum law; ministers vow to redraft."),
    ("{country} commuter rail strike enters second week",
     "Talks resume in {capital} as commuters face cancellations across the main intercity routes."),
    ("Renewable share of {country} grid reaches new high",
     "Wind and solar supplied 51% of electricity in March, the energy regulator in {capital} reports."),
    ("{country} parliament debates assisted dying bill",
     "Lawmakers in {capital} consider proposals that would make the country the latest in Europe to legalise the practice."),
    ("{country} football: domestic cup final goes to penalties",
     "A dramatic final at the national stadium near {capital} ends with the underdogs taking the trophy."),
    ("{country} farmers protest agricultural reforms",
     "Tractors gather in {capital} to oppose new environmental rules that growers say will raise costs."),
    ("{country} announces ban on single-use plastics",
     "The legislation passed in {capital} aligns the country with EU directives and takes effect next January."),
    ("{country} cultural year opens with film festival",
     "Headlines from the official opening in {capital}: a packed schedule of free events expected to draw a million visitors."),
    ("Housing crisis in {country} prompts emergency parliament session",
     "MPs in {capital} debate new measures to free up affordable rentals in major cities."),
]
def _r4_synth_body(lead: str, headline: str, country: str, capital: str) -> str:
    """Five-paragraph synthesized body for R4 regional stories. All
    paragraphs are derived deterministically from the inputs (no RNG)."""
    return (
        f"{lead}\n\n"
        f"BBC News correspondents in {capital} have followed this story since "
        f"it first broke on regional television. Officials in {country} are "
        f"under pressure both at home and from international partners, and the "
        f"response in the coming days will be closely watched.\n\n"
        f"\"This is not a problem that can be solved in a single news cycle,\" "
        f"one analyst told the BBC. \"What matters is whether the institutions "
        f"in {country} are equipped to deliver on the commitments now being "
        f"made in {capital}.\"\n\n"
        f"The story has resonated beyond {country}'s borders. Similar dynamics "
        f"are visible in neighbouring countries, and regional bodies have "
        f"already signalled they will discuss the implications at their next "
        f"summit.\n\n"
        f"BBC News will continue to cover developments. Our team is in {capital} "
        f"and is gathering reaction from communities most directly affected. "
        f"Updates will follow as the story progresses."
    )


def _r4_make_row(*, slug, headline, lead, body, category_id, section_slug,
                 subsection, region, ts, view_count, country=None,
                 hero="", topics=None, feature_tags=None, content_type="article",
                 is_breaking=0, is_live=0, video_url="", is_featured=0):
    return {
        "slug": slug,
        "headline": headline,
        "subtitle": lead[:300],
        "summary": lead[:300],
        "body": body,
        "author": "BBC News",
        "category_id": category_id,
        "hero_image": hero,
        "gallery_json": "[]",
        "gallery_full_json": "{}",
        "topics_json": json.dumps(topics or [region]),
        "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "reading_time": max(2, len(body.split()) // 200),
        "word_count": len(body.split()),
        "view_count": view_count,
        "is_featured": is_featured,
        "is_breaking": is_breaking,
        "is_live": is_live,
        "location": country or region,
        "source_url": f"https://www.bbc.com/news/articles/{slug}",
        "section_slug": section_slug,
        "subsection": subsection,
        "region": region,
        "video_url": video_url,
        "feature_tags": json.dumps(feature_tags or [section_slug]),
        "content_type": content_type,
    }


def _cat_id(con, slug: str) -> int | None:
    row = con.execute("SELECT id FROM categories WHERE slug=?", (slug,)).fetchone()
    return row[0] if row else None


# ---- R4 synth functions -------------------------------------------------

def synth_bbc_africa(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_africa") or _cat_id(con, "africa")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    for country, capital in AFRICAN_COUNTRIES:
        for idx, (hl_pat, lead_pat) in enumerate(AFRICA_HEADLINES[:6]):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r4-africa", f"{country}|{idx}")
            hero = hero_pool[(_det_int(slug) + 13) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 120) + 1,
                hours=(_det_int(slug) // 31) % 24,
            )
            body = _r4_synth_body(lead, headline, country, capital)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_africa",
                subsection=country, region="Africa", ts=ts,
                view_count=400 + (_det_int(slug) % 12000),
                country=country, hero=hero,
                topics=["Africa", country, "BBC Africa"],
                feature_tags=["bbc_africa", country.lower().replace(" ", "_")],
            ))
    return out


def synth_bbc_brasil(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_brasil") or _cat_id(con, "latin_america")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    # Brazil-only deep coverage.
    cities = ["Sao Paulo", "Rio de Janeiro", "Brasilia", "Salvador", "Fortaleza",
             "Belo Horizonte", "Manaus", "Curitiba", "Recife", "Porto Alegre"]
    for city_idx, city in enumerate(cities):
        for idx, (hl_pat, lead_pat) in enumerate(LATAM_HEADLINES[:8]):
            headline = hl_pat.format(country="Brazil", capital=city)
            # Add Portuguese flavour:
            headline_pt = headline.replace("Brazil", "Brasil")
            lead = lead_pat.format(country="Brazil", capital=city)
            slug = _det_slug("r4-brasil", f"{city}|{idx}")
            hero = hero_pool[(_det_int(slug) + 41) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 150) + 1,
                hours=(_det_int(slug) // 17) % 24,
            )
            body = _r4_synth_body(lead, headline_pt, "Brasil", city)
            out.append(_r4_make_row(
                slug=slug, headline=headline_pt, lead=lead, body=body,
                category_id=cid, section_slug="bbc_brasil",
                subsection=city, region="Latin America", ts=ts,
                view_count=300 + (_det_int(slug) % 9000),
                country="Brasil", hero=hero,
                topics=["Brasil", city, "BBC Brasil"],
                feature_tags=["bbc_brasil", "portugues"],
            ))
    return out


def synth_bbc_mundo(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_mundo") or _cat_id(con, "latin_america")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    spanish_countries = [(c, cap) for c, cap, lang in LATIN_AMERICA_COUNTRIES if lang == "es"]
    for country, capital in spanish_countries:
        for idx, (hl_pat, lead_pat) in enumerate(LATAM_HEADLINES[:5]):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r4-mundo", f"{country}|{idx}")
            hero = hero_pool[(_det_int(slug) + 23) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 140) + 1,
                hours=(_det_int(slug) // 19) % 24,
            )
            body = _r4_synth_body(lead, headline, country, capital)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_mundo",
                subsection=country, region="Latin America", ts=ts,
                view_count=350 + (_det_int(slug) % 8500),
                country=country, hero=hero,
                topics=["Latin America", country, "BBC Mundo"],
                feature_tags=["bbc_mundo", "espanol"],
            ))
    return out


def synth_bbc_arabic(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_arabic") or _cat_id(con, "middle_east")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    for country, capital in MIDDLE_EAST_COUNTRIES:
        for idx, (hl_pat, lead_pat) in enumerate(MIDEAST_HEADLINES[:4]):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r4-arabic", f"{country}|{idx}")
            hero = hero_pool[(_det_int(slug) + 53) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 130) + 1,
                hours=(_det_int(slug) // 23) % 24,
            )
            body = _r4_synth_body(lead, headline, country, capital)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_arabic",
                subsection=country, region="Middle East", ts=ts,
                view_count=300 + (_det_int(slug) % 10000),
                country=country, hero=hero,
                topics=["Middle East", country, "BBC Arabic"],
                feature_tags=["bbc_arabic", "arabic"],
            ))
    return out


def synth_bbc_persian(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_persian") or _cat_id(con, "middle_east")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    persian_targets = [("Iran", "Tehran"), ("Afghanistan", "Kabul"),
                       ("Tajikistan", "Dushanbe")]
    for country, capital in persian_targets:
        for idx, (hl_pat, lead_pat) in enumerate(MIDEAST_HEADLINES[:10]):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r4-persian", f"{country}|{idx}")
            hero = hero_pool[(_det_int(slug) + 67) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 110) + 1,
                hours=(_det_int(slug) // 29) % 24,
            )
            body = _r4_synth_body(lead, headline, country, capital)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_persian",
                subsection=country, region="Middle East", ts=ts,
                view_count=250 + (_det_int(slug) % 7500),
                country=country, hero=hero,
                topics=["Middle East", country, "BBC Persian"],
                feature_tags=["bbc_persian", "farsi"],
            ))
    return out


def synth_bbc_russian(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_russian") or _cat_id(con, "europe")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    targets = [("Russia", "Moscow"), ("Belarus", "Minsk"), ("Ukraine", "Kyiv"),
               ("Kazakhstan", "Astana"), ("Georgia", "Tbilisi"), ("Moldova", "Chisinau")]
    for country, capital in targets:
        for idx, (hl_pat, lead_pat) in enumerate(EUROPE_HEADLINES[:6]):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r4-russian", f"{country}|{idx}")
            hero = hero_pool[(_det_int(slug) + 79) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 130) + 1,
                hours=(_det_int(slug) // 13) % 24,
            )
            body = _r4_synth_body(lead, headline, country, capital)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_russian",
                subsection=country, region="Europe", ts=ts,
                view_count=300 + (_det_int(slug) % 8000),
                country=country, hero=hero,
                topics=["Europe", country, "BBC Russian"],
                feature_tags=["bbc_russian", "russian"],
            ))
    return out


def synth_bbc_china(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_china") or _cat_id(con, "asia")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    targets = [("China", "Beijing"), ("Hong Kong", "Hong Kong"),
               ("Taiwan", "Taipei"), ("Macau", "Macau")]
    for country, capital in targets:
        for idx, (hl_pat, lead_pat) in enumerate(ASIA_HEADLINES[:8]):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r4-china", f"{country}|{idx}")
            hero = hero_pool[(_det_int(slug) + 89) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 125) + 1,
                hours=(_det_int(slug) // 11) % 24,
            )
            body = _r4_synth_body(lead, headline, country, capital)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_china",
                subsection=country, region="Asia", ts=ts,
                view_count=400 + (_det_int(slug) % 11000),
                country=country, hero=hero,
                topics=["Asia", country, "BBC News China"],
                feature_tags=["bbc_china", "china"],
            ))
    return out


def synth_bbc_india(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "bbc_india") or _cat_id(con, "asia")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    cities = ["New Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru",
              "Hyderabad", "Ahmedabad", "Jaipur", "Pune", "Lucknow"]
    for city in cities:
        for idx, (hl_pat, lead_pat) in enumerate(ASIA_HEADLINES[:5]):
            headline = hl_pat.format(country="India", capital=city)
            lead = lead_pat.format(country="India", capital=city)
            slug = _det_slug("r4-india", f"{city}|{idx}")
            hero = hero_pool[(_det_int(slug) + 97) % len(hero_pool)]
            ts = base - timedelta(
                days=(_det_int(slug) % 140) + 1,
                hours=(_det_int(slug) // 7) % 24,
            )
            body = _r4_synth_body(lead, headline, "India", city)
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="bbc_india",
                subsection=city, region="Asia", ts=ts,
                view_count=400 + (_det_int(slug) % 9500),
                country="India", hero=hero,
                topics=["Asia", "India", city],
                feature_tags=["bbc_india", "south_asia"],
            ))
    return out


def synth_world_country_drill(con, hero_pool: list[str]) -> list[dict]:
    """For /world/<region>/<country> drill-down: pre-create a handful of
    region-tagged articles for each country across Asia, Europe, Africa."""
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    region_map = [
        ("asia",          "Asia",          ASIAN_COUNTRIES,       ASIA_HEADLINES),
        ("europe",        "Europe",        EUROPEAN_COUNTRIES,    EUROPE_HEADLINES),
        ("africa",        "Africa",        AFRICAN_COUNTRIES,     AFRICA_HEADLINES),
        ("middle_east",   "Middle East",   MIDDLE_EAST_COUNTRIES, MIDEAST_HEADLINES),
    ]
    for section_slug, region_label, country_pool, headlines in region_map:
        cid = _cat_id(con, section_slug)
        if cid is None:
            continue
        for country, capital in country_pool:
            for idx, (hl_pat, lead_pat) in enumerate(headlines[:3]):
                headline = hl_pat.format(country=country, capital=capital)
                lead = lead_pat.format(country=country, capital=capital)
                slug = _det_slug(f"r4-{section_slug}", f"{country}|{idx}")
                hero = hero_pool[(_det_int(slug) + 7) % len(hero_pool)]
                ts = base - timedelta(
                    days=(_det_int(slug) % 95) + 1,
                    hours=(_det_int(slug) // 9) % 24,
                )
                body = _r4_synth_body(lead, headline, country, capital)
                out.append(_r4_make_row(
                    slug=slug, headline=headline, lead=lead, body=body,
                    category_id=cid, section_slug=section_slug,
                    subsection=country, region=region_label, ts=ts,
                    view_count=400 + (_det_int(slug) % 8000),
                    country=country, hero=hero,
                    topics=[region_label, country],
                    feature_tags=[section_slug, country.lower().replace(" ", "_")],
                ))
    return out
def synth_in_pictures_essays(con, hero_pool: list[str]) -> list[dict]:
    """Deep /news/in_pictures photo essays."""
    cid = _cat_id(con, "in_pictures")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    essay_topics = [
        ("In pictures: spring blossom across the UK", "Cherry blossom in the parks of London, Edinburgh and Belfast as readers send in their photographs."),
        ("In pictures: a year of climate protest", "Twelve images from twelve months of demonstrations across five continents."),
        ("In pictures: the world's most striking street art of 2026", "From Bogota to Belgrade, the murals that stopped passers-by in their tracks."),
        ("In pictures: dawn over the Himalayas", "A BBC photographer's week capturing first light over the peaks."),
        ("In pictures: life in the world's coldest inhabited place", "Children, schools and reindeer in northern Siberia at -50C."),
        ("In pictures: the architecture of post-war housing", "How communities across Europe are saving 20th-century estates from demolition."),
        ("In pictures: the year in space photography", "Auroras, supermoons and the Milky Way over remote landscapes."),
        ("In pictures: festivals of light around the world", "Diwali, Hanukkah and Christmas captured at city scale."),
        ("In pictures: a year on the front line of conservation", "Rangers, scientists and volunteers in some of the world's most threatened ecosystems."),
        ("In pictures: working dogs of the world", "Sheepdogs in Snowdonia, sled dogs in Greenland and detection dogs in Kenya."),
        ("In pictures: the last of the world's traditional crafts", "Master artisans in Japan, Turkey and Peru passing on skills to a new generation."),
        ("In pictures: the new wave of African fashion designers", "Designers from Lagos, Nairobi and Dakar reshaping global runways."),
        ("In pictures: extreme weather as the new normal", "How communities are adapting to fires, floods and droughts in 2026."),
        ("In pictures: the world's most isolated communities", "Life in remote islands, mountain valleys and Arctic settlements."),
        ("In pictures: the resurgence of vinyl in 2026", "Record shops, pressing plants and the artists driving the boom."),
        ("In pictures: the everyday objects shaping the future", "From foldable phones to compostable packaging — small designs with big consequences."),
        ("In pictures: the last week of the Edinburgh Fringe", "Five performers, five photographs, five very different shows."),
        ("In pictures: dawn-to-dusk on a Welsh mountain", "A photographer's 18-hour vigil on Cadair Idris."),
        ("In pictures: the changing face of Britain's high streets", "What replaced the bank, the post office and the department store."),
        ("In pictures: weddings across faiths in 2026 Britain", "Twelve couples, twelve traditions, one country."),
        ("In pictures: the wildlife of urban Britain", "Foxes, peregrines and badgers caught on camera in city centres."),
        ("In pictures: the world's oldest universities", "Cloisters, libraries and lecture halls from Bologna to Beijing."),
        ("In pictures: the rebirth of the night train", "Sleeper services from Paris to Vienna are filling up again."),
        ("In pictures: the lives of Britain's fishing fleet", "Small ports, long hours and an industry under pressure."),
        ("In pictures: the new face of cricket in England", "Women's leagues, junior clubs and a record-breaking summer."),
        ("In pictures: opera under the stars", "Outdoor productions in Verona, Bregenz and Glyndebourne."),
        ("In pictures: the festivals of West Africa", "Music, dance and street parades from Dakar to Accra."),
        ("In pictures: the last days of the analogue cinema", "Projectionists holding on as film prints are phased out."),
        ("In pictures: a year inside a working dairy farm", "Calving, milking and the changing economics of British dairy."),
        ("In pictures: refugees rebuilding lives across Europe", "Twelve families, twelve countries of origin, twelve new beginnings."),
        ("In pictures: traditional fishing villages of Vietnam", "Long-tail boats, floating markets and the rhythms of the coast."),
        ("In pictures: the wild coastlines of Scotland", "Cliffs, beaches and offshore stacks captured from drone and ground."),
        ("In pictures: London after dark", "Markets, theatres and street life from 10pm to 6am."),
        ("In pictures: the women shaping European parliament", "Twenty MEPs, twenty very different paths to Brussels."),
        ("In pictures: the kitchen gardens of Britain", "Walled gardens, allotments and the rediscovery of heritage vegetables."),
        ("In pictures: snow leopards of the Hindu Kush", "Camera traps reveal a thriving population thought to be vanishing."),
        ("In pictures: the rebirth of England's canals", "Boaters, towpaths and the volunteers keeping waterways open."),
        ("In pictures: musicians of Sahel", "Mali, Niger and Burkina Faso — a region's sound under threat."),
        ("In pictures: the festival circuit of British folk music", "Cambridge, Cropredy and Sidmouth in a record summer."),
        ("In pictures: the children of the Calais camp", "Five years on from the first reporting trip, a return visit."),
        ("In pictures: the food markets of Mexico City", "Colour, noise and culinary history in CDMX's covered markets."),
        ("In pictures: northern lights over the British Isles", "Auroras photographed as far south as Cornwall this spring."),
        ("In pictures: women boxers training across the UK", "From Glasgow to Brighton, club gyms and rising professionals."),
        ("In pictures: the bookshops of the world", "Twenty independent bookshops worth a detour."),
        ("In pictures: the architecture of empty offices", "Photographer Eve Mascarenhas on the post-pandemic city."),
        ("In pictures: the polar science stations of Antarctica", "Researchers, engineers and chefs at the bottom of the world."),
        ("In pictures: the village fetes of England", "Cake stalls, brass bands and the British summer outdoors."),
        ("In pictures: the world's vanishing glaciers", "Five glaciers photographed annually for ten years."),
        ("In pictures: dance across the African continent", "Choreographers redefining contemporary movement."),
        ("In pictures: the cathedrals of Britain in 2026", "Twelve cathedrals, twelve photographers, twelve very different perspectives."),
        ("In pictures: the youth orchestras of Latin America", "Inspired by El Sistema, expanded across the continent."),
        ("In pictures: the last Yiddish theatres", "Performers in New York, London and Warsaw keeping a tradition alive."),
        ("In pictures: the new generation of British poets", "Twenty writers, twenty very different voices."),
        ("In pictures: street food of Bangkok", "Pad thai, mango sticky rice and the vendors who define the city."),
        ("In pictures: surfing the cold-water breaks of Cornwall", "Wetsuits, wax and a year-round community."),
        ("In pictures: the cafes of Vienna", "An institution unchanged in a century — but only just."),
        ("In pictures: the world's tea houses", "Tokyo, Marrakesh, Istanbul and the rituals around the leaf."),
        ("In pictures: ferry crossings of the Scottish Hebrides", "CalMac, weather and the lifeline of island life."),
        ("In pictures: rebuilding after the Turkish earthquakes", "Three years on, towns rising again."),
        ("In pictures: the workshops of Stradivari", "Cremona's violin makers in 2026."),
        ("In pictures: dawn at the world's longest beaches", "From Cox's Bazar to Praia do Cassino."),
        ("In pictures: night skies free of light pollution", "International dark-sky reserves photographed across two hemispheres."),
        ("In pictures: the volunteers of Britain's RNLI", "Lifeboat crews from Scilly to Shetland."),
        ("In pictures: cycling across Mongolia", "A two-month expedition by a BBC News reporter."),
        ("In pictures: backyard astronomers of Britain", "Amateur observatories from suburban Surrey to the Outer Hebrides."),
        ("In pictures: street food markets of Mexico", "Tortillerias, taquerias and the women who run them."),
        ("In pictures: women's rugby in 2026", "From grassroots clubs to the Six Nations decider."),
        ("In pictures: the cycle lanes reshaping European cities", "Paris, Utrecht, Seville — five cities rewriting their streets."),
        ("In pictures: the new wave of Welsh-language film", "Directors, producers and actors at S4C."),
        ("In pictures: lakes that disappear in summer", "Cyclical bodies of water across Europe and Central Asia."),
        ("In pictures: Cornwall's tin mining heritage", "From World Heritage status to working museums."),
        ("In pictures: the last drive-in cinemas", "Open-air screens from California to Korea, still drawing crowds."),
        ("In pictures: the children's choirs of South Africa", "Township choirs, national finals and the music that unites."),
        ("In pictures: stargazing in the Outer Hebrides", "Dark-sky tourism on the islands of Lewis and Harris."),
        ("In pictures: the dancers of the Bolshoi", "A year backstage at the Moscow ballet."),
        ("In pictures: the world's most colourful neighbourhoods", "From Burano to Bo-Kaap."),
        ("In pictures: the Royal Navy in 2026", "From submarines to aircraft carriers — a year afloat."),
        ("In pictures: the cooks of Naples", "Pizza, pasta and a city's culinary stubbornness."),
        ("In pictures: a year on Lundy Island", "Wildlife, weather and the 28 inhabitants of a Bristol Channel rock."),
        ("In pictures: the markets of Marrakech", "Souks, spices and the rhythms of the medina."),
        ("In pictures: the bookbinders of Britain", "Bespoke workshops keeping a centuries-old craft alive."),
    ]
    for idx, (headline, lead) in enumerate(essay_topics):
        slug = _det_slug("r4-pix", f"{idx}|{headline[:40]}")
        hero = hero_pool[(_det_int(slug) + 31) % len(hero_pool)]
        ts = base - timedelta(
            days=(idx * 3 + 1) % 200,
            hours=(_det_int(slug) // 41) % 24,
        )
        body = (
            f"{lead}\n\n"
            f"Photographs in this essay were submitted to and selected by "
            f"the BBC News picture desk. The selection is part of our regular "
            f"In Pictures series, which highlights the visual storytelling of "
            f"photojournalists and amateur contributors alike.\n\n"
            f"Each image has been captioned by the photographer and lightly "
            f"edited for clarity. The series runs weekly and is curated by "
            f"the BBC News visual journalism team.\n\n"
            f"Submissions for next month's edition can be sent via the BBC "
            f"News contact page. Please include a short caption and your "
            f"location with each image.\n\n"
            f"View the full gallery in the slideshow below. Use the arrow "
            f"keys to navigate, or click the image to enter fullscreen mode."
        )
        out.append(_r4_make_row(
            slug=slug, headline=headline, lead=lead, body=body,
            category_id=cid, section_slug="in_pictures",
            subsection="Photo Essay", region="", ts=ts,
            view_count=600 + (_det_int(slug) % 18000),
            hero=hero,
            topics=["In Pictures", "Photo Essay"],
            feature_tags=["in_pictures", "photo_essay", "gallery"],
            content_type="gallery",
        ))
    return out


def synth_audio_digests(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "audio") or _cat_id(con, "sounds")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    series = [
        "The Daily News Briefing", "Newscast", "Global News Podcast",
        "Americast", "The Documentary", "More or Less", "Witness History",
        "From Our Own Correspondent", "Inside Health", "Crowd Science",
        "Tech Tent", "Business Daily", "BBC OS Conversations",
        "BBC Sounds Daily", "World Service Newshour", "Discovery",
        "The Climate Question", "Outlook", "The Comb",
        "Stumped: Cricket Podcast",
    ]
    topics = [
        "the week in politics", "the AI gold rush", "interest rates and inflation",
        "the war in eastern Europe", "climate negotiations", "the housing crisis",
        "the future of work", "a deep dive on cryptocurrency", "elections in India",
        "the latest from space", "young voters across Europe", "global food prices",
        "the rebirth of public transport", "the streaming wars",
        "world cricket in 2026", "Premier League title race",
        "Wimbledon preview", "the future of football", "the gig economy",
        "loneliness and mental health",
    ]
    for s_idx, series_name in enumerate(series):
        for t_idx, topic in enumerate(topics[:6]):
            headline = f"{series_name}: {topic}"
            slug = _det_slug("r4-audio", f"{series_name}|{topic}")
            hero = hero_pool[(_det_int(slug) + 11) % len(hero_pool)]
            ts = base - timedelta(
                days=(s_idx * 7 + t_idx * 3) % 180,
                hours=(_det_int(slug) // 13) % 24,
            )
            lead = (
                f"This week on {series_name}, the BBC's correspondents explore "
                f"{topic}. Subscribe via the BBC Sounds app to listen on the move."
            )
            body = (
                f"{lead}\n\n"
                f"Hosts and guests dig into the story behind the headlines, "
                f"and ask what comes next. The full episode is 28 minutes and "
                f"is available now on BBC Sounds.\n\n"
                f"Subscribe to the podcast feed to receive new episodes "
                f"automatically. You can also download episodes for offline "
                f"listening in the BBC Sounds app.\n\n"
                f"Get in touch with the team via email or voice note: we "
                f"feature listener questions in every fourth episode.\n\n"
                f"Use the player below to listen now, or open the episode in "
                f"BBC Sounds for the full chapter markers and transcript."
            )
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="audio",
                subsection=series_name, region="", ts=ts,
                view_count=500 + (_det_int(slug) % 14000),
                hero=hero,
                topics=["Audio", "Podcast", series_name],
                feature_tags=["audio", "podcast", "bbc_sounds"],
                content_type="audio",
                video_url=f"https://www.bbc.co.uk/sounds/play/{slug}",
            ))
    return out
def synth_weather_7day(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "weather")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    conditions = ["Sunny intervals", "Light rain", "Cloudy", "Heavy rain",
                  "Thundery showers", "Snow showers", "Foggy start",
                  "Clear and cold", "Windy with showers", "Hot and sunny"]
    for pc_idx, (postcode, area, nation) in enumerate(UK_POSTCODES):
        headline = f"Weather 7-day forecast for {area} ({postcode})"
        lead = (
            f"Seven-day forecast for {area}, {nation}. Conditions across {postcode} "
            f"are expected to follow the recent pattern, with no significant change "
            f"on the horizon."
        )
        slug = _det_slug("r4-wx7", f"{postcode}|{area}")
        hero = hero_pool[(_det_int(slug) + 19) % len(hero_pool)]
        ts = base - timedelta(
            hours=(pc_idx * 13 + _det_int(slug)) % (24 * 30),
        )
        # 7-day breakdown table in the body
        days = ["Today", "Tomorrow", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
        rows_md = []
        for d_idx, day in enumerate(days):
            cond = conditions[(_det_int(slug) + d_idx) % len(conditions)]
            t_max = 8 + (_det_int(slug) + d_idx * 3) % 20
            t_min = max(0, t_max - 6 - (d_idx % 3))
            rows_md.append(f"{day}: {cond}. High {t_max}C / Low {t_min}C.")
        body = (
            f"{lead}\n\n"
            f"Seven-day outlook for {area}, {nation} (postcode area {postcode}). "
            f"Forecast issued at 06:00 local time, updated four times daily.\n\n"
            + "\n".join(rows_md) + "\n\n"
            f"Severe weather: no warnings currently in force for {postcode}. "
            f"Check the BBC Weather warnings map before any travel.\n\n"
            f"UV index for {area} is moderate during midday hours. Pollen "
            f"levels are low to medium. Tide times for the nearest coast are "
            f"available on the marine forecast page."
        )
        out.append(_r4_make_row(
            slug=slug, headline=headline, lead=lead, body=body,
            category_id=cid, section_slug="weather",
            subsection=area, region=nation, ts=ts,
            view_count=300 + (_det_int(slug) % 7000),
            country="United Kingdom", hero=hero,
            topics=["Weather", area, "7-day forecast", postcode],
            feature_tags=["weather", "forecast", "postcode", postcode.lower()],
        ))
    return out


def synth_iplayer_watchlist(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "iplayer_categories") or _cat_id(con, "iplayer")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    categories = [
        ("Drama", "Original BBC drama and best-loved classics."),
        ("Documentary", "Films and series from the BBC documentary team."),
        ("Comedy", "Stand-up, sitcoms and comedy panel shows."),
        ("Sport", "Live and on-demand sport from across the BBC."),
        ("News", "BBC News on iPlayer: bulletins and current affairs."),
        ("Films", "Feature films available now on iPlayer."),
        ("Entertainment", "Game shows, talent shows and reality TV."),
        ("Music", "Live performances, concerts and music documentaries."),
        ("Children", "CBeebies and CBBC programmes for young viewers."),
        ("Lifestyle", "Cookery, gardening, travel and design."),
        ("History", "History documentaries and dramatised history."),
        ("Science and Nature", "From the natural world to the cutting edge."),
        ("Arts", "Theatre, opera, dance and visual arts."),
        ("Religion and Ethics", "Programmes exploring faith and ethics."),
        ("Audio Described", "Programmes with audio description."),
        ("Signed", "Programmes with British Sign Language."),
    ]
    shows = [
        ("Line of Duty Series 7", "drama"),
        ("Doctor Who: The New Era", "drama"),
        ("Sherlock Returns", "drama"),
        ("Bluey on iPlayer", "children"),
        ("Planet Earth III special", "science_nature"),
        ("Killing Eve: The Final Cut", "drama"),
        ("Match of the Day at 60", "sport"),
        ("Question Time live", "news"),
        ("Strictly Come Dancing", "entertainment"),
        ("The Apprentice Boardroom", "entertainment"),
        ("Bake Off Christmas", "lifestyle"),
        ("Top Gear: World Tour", "lifestyle"),
        ("Peaky Blinders Movie", "films"),
        ("Wolf Hall: The Mirror and the Light", "drama"),
        ("Glastonbury 2026", "music"),
        ("Promenade Concerts: First Night", "music"),
        ("Antiques Roadshow Live", "lifestyle"),
        ("Springwatch 2026", "science_nature"),
        ("Today at Wimbledon", "sport"),
        ("BBC News at Ten", "news"),
        ("BBC Newsnight", "news"),
        ("Mock the Week return", "comedy"),
        ("Would I Lie to You?", "comedy"),
        ("QI XXII", "comedy"),
        ("Have I Got News for You", "comedy"),
        ("Frozen Planet III", "science_nature"),
        ("The Capture: Season 3", "drama"),
        ("Vigil: Season 2", "drama"),
        ("Happy Valley returns", "drama"),
        ("MasterChef: The Professionals", "lifestyle"),
        ("Top of the Pops 1990", "music"),
        ("Last Night of the Proms", "music"),
        ("BBC Symphony Orchestra", "music"),
        ("Songs of Praise summer special", "religion_ethics"),
        ("Bargain Hunt week", "lifestyle"),
        ("Pointless Celebrities", "entertainment"),
        ("Newsround on iPlayer", "children"),
        ("Horrible Histories", "children"),
        ("Hey Duggee", "children"),
        ("Operation Ouch", "children"),
        ("EastEnders: The Years", "drama"),
        ("Casualty: The 40th", "drama"),
        ("Holby City retrospective", "drama"),
        ("The Apprentice: You're Fired", "entertainment"),
        ("Dragons' Den", "entertainment"),
        ("Race Across the World", "entertainment"),
        ("The Traitors UK 2026", "entertainment"),
        ("University Challenge final", "entertainment"),
    ]
    for cat_idx, (cat_name, cat_desc) in enumerate(categories):
        for sh_idx, (show, show_cat) in enumerate(shows):
            if sh_idx % len(categories) != cat_idx and show_cat != cat_name.lower().replace(" ", "_").replace("and_", ""):
                continue
            headline = f"iPlayer: {show} — add to watchlist"
            slug = _det_slug("r4-iplayer", f"{cat_name}|{show}|{sh_idx}")
            hero = hero_pool[(_det_int(slug) + 43) % len(hero_pool)]
            ts = base - timedelta(
                days=(cat_idx * 4 + sh_idx) % 200,
                hours=(_det_int(slug) // 17) % 24,
            )
            lead = (
                f"{show} is now available on BBC iPlayer. Find it in the {cat_name} "
                f"category, add to your watchlist for offline downloads, or stream "
                f"now on supported devices."
            )
            body = (
                f"{lead}\n\n"
                f"{cat_desc} {show} runs as part of this collection. New episodes "
                f"appear on iPlayer immediately after broadcast and remain available "
                f"for 12 months.\n\n"
                f"To add {show} to your watchlist, sign in to your BBC account and "
                f"tap the bookmark icon on the programme page. Watchlist items appear "
                f"in the My Programmes tab.\n\n"
                f"Audio description and subtitles are available for this programme. "
                f"You can change accessibility preferences in your iPlayer settings.\n\n"
                f"Looking for similar programmes? Browse the full {cat_name} category "
                f"on iPlayer for more like {show}."
            )
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="iplayer",
                subsection=cat_name, region="", ts=ts,
                view_count=400 + (_det_int(slug) % 16000),
                hero=hero,
                topics=["iPlayer", cat_name, show],
                feature_tags=["iplayer", "watchlist", cat_name.lower().replace(" ", "_")],
                content_type="video",
                video_url=f"https://www.bbc.co.uk/iplayer/episode/{slug}",
            ))
    return out


def synth_video_clips(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "video_clips") or _cat_id(con, "video")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    clips = [
        ("Watch: Drone footage of overnight flooding in {place}", "{place}"),
        ("Watch: Eyewitness account of the {place} storm", "{place}"),
        ("Watch: Inside the new {place} hospital wing", "{place}"),
        ("Watch: First match-day pitch view at {place}'s rebuilt stadium", "{place}"),
        ("Watch: BBC Verify breaks down the {place} footage", "{place}"),
        ("Watch: 60-second guide to the {place} election result", "{place}"),
        ("Watch: Aerial views of solar park near {place}", "{place}"),
        ("Watch: Time-lapse of the {place} skyline at night", "{place}"),
        ("Watch: Children of {place} interview their headteacher", "{place}"),
        ("Watch: How the {place} commuter rail strike unfolded", "{place}"),
    ]
    places = [
        "London", "Manchester", "Birmingham", "Edinburgh", "Cardiff",
        "Belfast", "Glasgow", "Liverpool", "Leeds", "Newcastle",
        "Bristol", "Sheffield", "Nottingham", "Brighton", "Plymouth",
        "Paris", "Berlin", "Rome", "Madrid", "Vienna",
        "Athens", "Lisbon", "Dublin", "Amsterdam", "Stockholm",
        "Lagos", "Nairobi", "Cairo", "Cape Town", "Accra",
        "Mumbai", "Delhi", "Tokyo", "Seoul", "Bangkok",
        "New York", "Washington", "Toronto", "Sydney", "Auckland",
    ]
    for p_idx, place in enumerate(places):
        for c_idx, (pat, _) in enumerate(clips[:4]):
            headline = pat.format(place=place)
            slug = _det_slug("r4-clip", f"{place}|{c_idx}")
            hero = hero_pool[(_det_int(slug) + 59) % len(hero_pool)]
            ts = base - timedelta(
                days=(p_idx * 2 + c_idx) % 90,
                hours=(_det_int(slug) // 7) % 24,
                minutes=(_det_int(slug) // 11) % 60,
            )
            lead = (
                f"{headline}. Footage captured by BBC News teams and verified "
                f"by the BBC Verify desk. Duration: 1 minute 20 seconds."
            )
            body = (
                f"{lead}\n\n"
                f"This clip is part of our short-form video offering on BBC News. "
                f"Use the play button below to watch with subtitles, or tap the "
                f"share button to send to your social feeds.\n\n"
                f"Filmed and edited by BBC News. The footage has been geo-located "
                f"and time-stamped where possible.\n\n"
                f"Find more video clips from {place} on the BBC News channel page. "
                f"Subscribe for daily updates on the BBC News iPlayer feed.\n\n"
                f"For accessibility, an audio description track is available. Tap "
                f"the AD button on the player controls."
            )
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="video",
                subsection=place, region="", ts=ts,
                view_count=800 + (_det_int(slug) % 25000),
                hero=hero,
                topics=["Video", "Watch", place],
                feature_tags=["video", "clip", "watch", "60_seconds"],
                content_type="video",
                video_url=f"https://www.bbc.co.uk/news/av/{slug}",
            ))
    return out


def synth_breaking_news(con, hero_pool: list[str]) -> list[dict]:
    """Stories flagged is_breaking=1 — fuel for /breaking-news endpoint
    and the pulsing-red banner on top of the homepage."""
    cid = _cat_id(con, "breaking_news") or _cat_id(con, "news")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    breaks = [
        ("BREAKING: Major fire at {place} industrial estate, no casualties reported",
         "Fire crews from across {region} attend the blaze; residents told to keep windows closed."),
        ("BREAKING: Two arrested after {place} bank raid",
         "Police in {region} say a getaway vehicle was abandoned near the city centre."),
        ("BREAKING: {place} schools to close tomorrow following storm warning",
         "Met Office issues amber warning for {region} as winds expected to peak overnight."),
        ("BREAKING: {place} central station evacuated after security alert",
         "Trains diverted away from {region}'s main hub as bomb-disposal team investigates a suspect package."),
        ("BREAKING: Power outage hits 250,000 homes in {place}",
         "Engineers in {region} working to restore supply after substation fault; expected by midnight."),
        ("BREAKING: {place} earthquake felt across {region}",
         "Magnitude 4.5 tremor; no major damage reported. Geological survey investigates."),
        ("BREAKING: Major motorway closure in {region}",
         "{place} services area cordoned off after multi-vehicle collision; ambulances on scene."),
        ("BREAKING: Cyber-attack disrupts {place} hospital systems",
         "NHS trusts in {region} switch to manual records; non-urgent appointments cancelled."),
        ("BREAKING: {place} football match suspended after pyrotechnic incident",
         "Stadium security in {region} confirm two spectators treated for minor injuries."),
        ("BREAKING: Body recovered from river in {place}",
         "Police divers in {region} continue searches; family informed."),
    ]
    targets = [
        ("Manchester", "north-west England"),
        ("Birmingham", "the West Midlands"),
        ("Edinburgh", "Scotland"),
        ("Cardiff", "Wales"),
        ("Belfast", "Northern Ireland"),
        ("Bristol", "south-west England"),
        ("Newcastle", "north-east England"),
        ("Liverpool", "Merseyside"),
        ("Leeds", "West Yorkshire"),
        ("Sheffield", "South Yorkshire"),
        ("Nottingham", "the East Midlands"),
        ("Glasgow", "Scotland"),
        ("Brighton", "Sussex"),
        ("Plymouth", "Devon"),
        ("Norwich", "East Anglia"),
        ("Aberdeen", "Scotland"),
        ("Hull", "East Yorkshire"),
        ("Coventry", "the West Midlands"),
        ("Stoke-on-Trent", "Staffordshire"),
        ("Wolverhampton", "the West Midlands"),
    ]
    for t_idx, (place, region) in enumerate(targets):
        for b_idx, (pat_h, pat_l) in enumerate(breaks[:3]):
            headline = pat_h.format(place=place, region=region)
            lead = pat_l.format(place=place, region=region)
            slug = _det_slug("r4-break", f"{place}|{b_idx}")
            hero = hero_pool[(_det_int(slug) + 73) % len(hero_pool)]
            ts = base - timedelta(
                days=(t_idx * 2 + b_idx) % 45,
                hours=(_det_int(slug) // 13) % 24,
                minutes=(_det_int(slug) // 5) % 60,
            )
            body = (
                f"{lead}\n\n"
                f"BBC News has confirmed the incident with police in {region}. "
                f"This story is developing rapidly and we will update as more "
                f"information becomes available.\n\n"
                f"Our correspondent is on the scene in {place} and will report "
                f"live on BBC News at the top of every hour.\n\n"
                f"Residents in the immediate area are being advised to follow "
                f"instructions from emergency services. Anyone with information "
                f"that may assist the investigation should call the non-emergency "
                f"police number.\n\n"
                f"This is a BBC Breaking News bulletin. The pulsing red banner "
                f"at the top of every page indicates a developing story."
            )
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="breaking_news",
                subsection=place, region=region, ts=ts,
                view_count=1500 + (_det_int(slug) % 40000),
                country=place, hero=hero,
                topics=["Breaking", place, region],
                feature_tags=["breaking", "developing", place.lower()],
                is_breaking=1, is_featured=1,
            ))
    return out


def synth_multi_step_longreads(con, hero_pool: list[str]) -> list[dict]:
    """Long-form features for multi-step navigation tasks (find article -> read chapters -> share)."""
    cid = _cat_id(con, "multi_step") or _cat_id(con, "news")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    longreads = [
        ("Inside the year that changed the NHS", "A 12-month investigation across five hospital trusts reveals a service straining at the edges."),
        ("The last villages of the Scottish Highlands", "On the slow march of depopulation in the glens — and the new arrivals trying to reverse it."),
        ("How AI is rewriting the rules of medicine", "From radiology to drug discovery, a deep dive into the technology already in the clinic."),
        ("The price of the Premier League", "Where the billions go: a forensic look at the world's richest football league."),
        ("Britain's secret housing crisis", "Beyond the headlines, the hidden tier of substandard rentals."),
        ("The truth about working from home", "Four years on, the data, the disputes and the human stories."),
        ("Inside the BBC's biggest reporting projects of 2026", "From climate verification to election forensics, a year in journalism."),
        ("How the world's coffee supply is changing", "Climate, conflict and a commodity at a crossroads."),
        ("The European right: a new generation", "Six countries, six new leaders, one big question."),
        ("Britain's universities at a crossroads", "Foreign students, financial pressure and a model under strain."),
        ("The new geography of work", "Where Britain's jobs are moving — and why."),
        ("Climate, conflict and migration in 2026", "A year-long BBC News project tracking displacement around the world."),
        ("The end of cash?", "How the war on physical money is reshaping inequality."),
        ("The science of long Covid", "Three years on, what we know — and what we don't."),
        ("Inside Britain's care homes", "An undercover investigation across England and Scotland."),
        ("How the BBC made the Doctor Who anniversary special", "Sixty years of Doctor Who: the inside story."),
        ("The plastics paradox", "Why recycling is failing and what the alternatives look like."),
        ("Britain's pothole crisis", "Why the roads are crumbling — and who is going to fix them."),
        ("The fight for the Arctic", "Russia, Norway and the climate stakes of the Far North."),
        ("Hong Kong, five years on", "The city changed by the National Security Law."),
        ("The future of British farming", "After Brexit, after the subsidy reforms, after the floods."),
        ("Inside the world's largest refugee camp", "Cox's Bazar in 2026."),
        ("The new gold rush: rare earths and the green transition", "Where the elements that power the future are being dug up."),
        ("Britain's energy paradox", "Net zero ambitions meet a creaking grid."),
        ("The story of the BBC World Service in 2026", "Reaching 320 million people in 42 languages."),
        ("The making of a TikTok superstar", "From bedroom to brand deal: how it really works."),
        ("Inside Britain's prisons", "A six-month investigation across 14 jails."),
        ("How Britain became a courier nation", "Same-day delivery and the workers behind it."),
        ("The vanishing high street", "What towns lost — and what they are building back."),
        ("Britain's anxiety crisis", "How a generation became the most anxious on record."),
        ("Climate verification: how the BBC checks the science", "Inside the BBC Verify climate desk."),
        ("The new face of British politics", "A constituency-by-constituency look at the 2026 elections."),
        ("How Wales is rebuilding its rural economy", "From slate to silicon, the new industries of the valleys."),
        ("The Britain-EU relationship in 2026", "Six years on, the data, the diplomacy and the daily life."),
        ("Inside the Edinburgh Fringe", "A month in the world's largest arts festival."),
        ("Britain's drug deaths epidemic", "Why the UK has Europe's worst overdose figures."),
        ("The new wave of British science fiction", "Writers reshaping the genre from Hay-on-Wye to Hackney."),
        ("How the Premier League salary cap stopped working", "Inside football's new financial reality."),
        ("Britain's gambling problem", "An investigation into the gambling industry's grip on football."),
        ("The truth about the four-day week", "Trials, results and the next phase."),
    ]
    for idx, (headline, lead) in enumerate(longreads):
        slug = _det_slug("r4-longread", f"{idx}|{headline[:40]}")
        hero = hero_pool[(_det_int(slug) + 101) % len(hero_pool)]
        ts = base - timedelta(
            days=(idx * 6 + 9) % 220,
            hours=(_det_int(slug) // 19) % 24,
        )
        body_parts = [lead]
        for chap_idx, chap_title in enumerate([
            "Chapter 1: How we got here",
            "Chapter 2: The numbers",
            "Chapter 3: The people",
            "Chapter 4: The institutions",
            "Chapter 5: What comes next",
        ]):
            body_parts.append(
                f"{chap_title}\n\n"
                f"This chapter of our long-read investigation pieces together "
                f"reporting from the BBC's correspondents, freshly released data, "
                f"interviews with the people most affected, and analysis from "
                f"independent experts. Reading time: 6 minutes.\n\n"
                f"Use the navigation in the sidebar to jump between chapters, "
                f"or scroll continuously. A printable PDF version is available "
                f"on the BBC News long-reads landing page."
            )
        body = "\n\n".join(body_parts)
        out.append(_r4_make_row(
            slug=slug, headline=headline, lead=lead, body=body,
            category_id=cid, section_slug="multi_step",
            subsection="Long read", region="", ts=ts,
            view_count=700 + (_det_int(slug) % 22000),
            hero=hero,
            topics=["Long Read", "Multi-step", "Feature"],
            feature_tags=["long_read", "multi_step", "feature", "chapters"],
            content_type="long_read",
            is_featured=1,
        ))
    return out


def synth_podcast_genres(con, hero_pool: list[str]) -> list[dict]:
    cid = _cat_id(con, "podcasts_genres") or _cat_id(con, "podcasts")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    genres = [
        ("News", "Daily news podcasts and current affairs."),
        ("History", "Documentaries and dramatisations from across the centuries."),
        ("Comedy", "Stand-up and conversational comedy podcasts."),
        ("Drama", "Original audio drama and radio plays."),
        ("Science", "From the lab to the universe: science podcasts."),
        ("Music", "Talks, mixes and live recordings."),
        ("Sport", "Cricket, football, rugby, tennis."),
        ("Politics", "Political analysis and interviews."),
        ("Crime", "True crime, investigations and case studies."),
        ("Society and Culture", "Identity, communities and culture."),
        ("Business", "Daily business and markets coverage."),
        ("Arts", "Books, film, theatre, visual arts."),
        ("Religion and Ethics", "Faith, philosophy and ethics in 2026."),
        ("Tech", "AI, cyber, devices and the future."),
        ("Education", "From early years to lifelong learning."),
    ]
    titles_per_genre = [
        "Briefing", "Daily", "Inside", "The Story", "Deep Dive",
        "Conversations", "Weekly Roundup", "On Stage", "Off the Record", "Long Read",
    ]
    for g_idx, (genre, genre_desc) in enumerate(genres):
        for t_idx, title in enumerate(titles_per_genre):
            headline = f"BBC Sounds: {genre} — {title}"
            slug = _det_slug("r4-pcg", f"{genre}|{title}|{t_idx}")
            hero = hero_pool[(_det_int(slug) + 113) % len(hero_pool)]
            ts = base - timedelta(
                days=(g_idx * 5 + t_idx * 2) % 170,
                hours=(_det_int(slug) // 23) % 24,
            )
            lead = (
                f"Subscribe to the {genre} {title} podcast on BBC Sounds. "
                f"{genre_desc} New episodes every weekday."
            )
            body = (
                f"{lead}\n\n"
                f"Browse the full {genre} genre on BBC Sounds for related podcasts, "
                f"audio documentaries and on-demand radio. Subscribe to add this "
                f"feed to your library.\n\n"
                f"Episodes are 18-45 minutes long. Listen on the BBC Sounds app, "
                f"smart speakers, or any podcast player.\n\n"
                f"Use the chapter markers in the player to skip to your favourite "
                f"segment. Transcripts are available on the episode pages.\n\n"
                f"Subscribe via the BBC Sounds app to receive new episodes "
                f"automatically. Manage your subscription from the My Sounds tab."
            )
            out.append(_r4_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug="podcasts",
                subsection=genre, region="", ts=ts,
                view_count=300 + (_det_int(slug) % 12000),
                hero=hero,
                topics=["Podcasts", genre, title],
                feature_tags=["podcast", "subscribe", genre.lower().replace(" ", "_")],
                content_type="audio",
                video_url=f"https://www.bbc.co.uk/sounds/series/{slug}",
            ))
    return out
R4_COMMENT_TOP = [
    "Strong, internationally minded reporting. The {region} angle is exactly what was missing.",
    "Loved the {country} reporting. Bookmark and a share for me.",
    "This is the kind of regional storytelling the BBC does best.",
    "Subscribed to the related podcast — keep me posted on next week's follow-up.",
    "The visual storytelling on the gallery was top tier.",
    "Sticky video player worked perfectly while I scrolled the comments. Good UX.",
    "Sharing this with my reading group tonight.",
    "Loved the breakdown by chapter. The fourth chapter is the strongest.",
    "I'd love a Sounds episode that goes deeper on the data.",
    "Comments below have been more thoughtful than usual on this one.",
]

R4_COMMENT_REPLIES = [
    "Agree — the {country} reporting in particular was very strong.",
    "Same. Will be subscribing to the related podcast.",
    "Yes, the chapter structure made this much easier to follow.",
    "Likewise — added the long-read PDF to my reading list.",
    "The sticky video player worked well for me too.",
    "Bookmarked and shared with the family WhatsApp.",
    "I had to listen on Sounds — the audio version is excellent.",
]


def insert_r4_articles(con: sqlite3.Connection, batch: list[dict]) -> int:
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM articles")}
    rows = [a for a in batch if a["slug"] not in existing]
    if not rows:
        return 0
    cur.executemany(_ART_INSERT_SQL, rows)
    return len(rows)


def insert_r4_comments(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if len(user_ids) < 2:
        return 0

    # Article pool: a slice of R4-new content keyed off feature_tags.
    pool: list[tuple[int, str, str]] = []
    for tag in ("bbc_africa", "bbc_brasil", "bbc_mundo", "bbc_arabic",
                "bbc_persian", "bbc_russian", "bbc_china", "bbc_india",
                "in_pictures", "audio", "weather", "iplayer", "video",
                "breaking", "long_read", "podcast"):
        rows = cur.execute(
            "SELECT id, region, location FROM articles "
            "WHERE feature_tags LIKE ? ORDER BY view_count DESC LIMIT 8",
            (f'%"{tag}"%',),
        ).fetchall()
        pool.extend(rows)
    seen: set[int] = set()
    pool = [t for t in pool if not (t[0] in seen or seen.add(t[0]))][:140]

    base_ts = MIRROR_REFERENCE_DATE
    top_rows: list[tuple] = []
    for idx, (art_id, region, location) in enumerate(pool):
        n_top = 2 + (idx % 3)  # 2,3,4 top-level per article
        for j in range(n_top):
            uid = user_ids[(idx * 7 + j * 5) % len(user_ids)]
            template = R4_COMMENT_TOP[(idx * 3 + j * 7) % len(R4_COMMENT_TOP)]
            body = template.replace("{country}", location or "").replace("{region}", region or "")
            body = body.replace("  ", " ").strip()
            offset_h = (idx * 11 + j * 13) % (24 * 18)
            ts = base_ts - timedelta(hours=offset_h, minutes=(idx + j * 7) % 60)
            like = (idx * j + 5) % 28
            top_rows.append((uid, art_id, None, body, like, 0,
                             ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        top_rows,
    )
    inserted = len(top_rows)

    # 3-deep replies on every 3rd top-level comment
    fresh = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL ORDER BY id DESC LIMIT ?",
        (inserted,),
    ))
    fresh.reverse()
    for i, (cid, art_id, parent_uid, parent_created) in enumerate(fresh):
        if i % 3 != 0:
            continue
        cur_parent = cid
        cur_parent_uid = parent_uid
        ts_parent = datetime.strptime(parent_created, "%Y-%m-%d %H:%M:%S")
        for depth in range(1, 4):
            ruid = user_ids[(cur_parent_uid + depth + i + 2) % len(user_ids)]
            if ruid == cur_parent_uid:
                ruid = user_ids[(cur_parent_uid + depth + i + 3) % len(user_ids)]
            body = R4_COMMENT_REPLIES[(i * 5 + depth * 3) % len(R4_COMMENT_REPLIES)]
            body = body.replace("{country}", "")
            ts_parent = ts_parent + timedelta(hours=depth + 1, minutes=(depth * 11) % 60)
            cur.execute(
                "INSERT INTO comments (user_id, article_id, parent_id, body, "
                "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ruid, art_id, cur_parent, body, (depth * (i + 1)) % 19, 0,
                 ts_parent.strftime("%Y-%m-%d %H:%M:%S")),
            )
            inserted += 1
            cur_parent = cur.lastrowid
            cur_parent_uid = ruid
    return inserted


def insert_r4_reading_history(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = list(cur.execute("SELECT id FROM users ORDER BY id"))
    if not users:
        return 0
    art_pool = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE '%bbc_%' "
        "OR feature_tags LIKE '%breaking%' OR feature_tags LIKE '%long_read%' "
        "OR feature_tags LIKE '%in_pictures%' OR feature_tags LIKE '%video%' "
        "OR feature_tags LIKE '%weather%' OR feature_tags LIKE '%iplayer%' "
        "ORDER BY view_count DESC LIMIT 240"
    )]
    base_ts = MIRROR_REFERENCE_DATE
    inserted = 0
    existing = set(cur.execute(
        "SELECT user_id, article_id FROM reading_history"
    ).fetchall())
    rows: list[tuple] = []
    for u_idx, (uid,) in enumerate(users):
        per_user = 40 + (u_idx * 3) % 12
        for a_idx in range(min(per_user, len(art_pool))):
            art_id = art_pool[(u_idx * 23 + a_idx * 7) % len(art_pool)]
            if (uid, art_id) in existing:
                continue
            existing.add((uid, art_id))
            ts = base_ts - timedelta(
                hours=(u_idx * 19 + a_idx * 11) % (24 * 90),
                minutes=(a_idx * 7) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO reading_history (user_id, article_id, viewed_at) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_r4_bookmarks(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    art_pool = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE '%long_read%' "
        "OR feature_tags LIKE '%in_pictures%' OR feature_tags LIKE '%bbc_%' "
        "OR feature_tags LIKE '%podcast%' "
        "ORDER BY view_count DESC LIMIT 180"
    )]
    base_ts = MIRROR_REFERENCE_DATE
    existing = set(cur.execute(
        "SELECT user_id, article_id FROM bookmarks"
    ).fetchall())
    rows: list[tuple] = []
    for u_idx, uid in enumerate(users):
        per_user = 22 + (u_idx * 4) % 10
        for a_idx in range(min(per_user, len(art_pool))):
            art_id = art_pool[(u_idx * 13 + a_idx * 17) % len(art_pool)]
            if (uid, art_id) in existing:
                continue
            existing.add((uid, art_id))
            ts = base_ts - timedelta(
                hours=(u_idx * 17 + a_idx * 11) % (24 * 80),
                minutes=(a_idx * 5) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO bookmarks (user_id, article_id, bookmarked_at) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_r4_subscriptions(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    new_topics = [
        "BBC Africa", "BBC Brasil", "BBC News Mundo", "BBC Arabic",
        "BBC Persian", "BBC Russian", "BBC News China", "BBC News India",
        "Breaking News", "In Pictures", "Long Reads", "Weather forecast",
        "iPlayer", "BBC Sounds", "Video clips",
    ]
    rows: list[tuple] = []
    existing = set(cur.execute(
        "SELECT user_id, topic FROM topic_subscriptions"
    ).fetchall())
    base_ts = MIRROR_REFERENCE_DATE
    for u_idx, uid in enumerate(users):
        for t_idx, topic in enumerate(new_topics):
            if (u_idx + t_idx) % 2 != 0:
                continue
            if (uid, topic) in existing:
                continue
            existing.add((uid, topic))
            freq = ("daily", "weekly", "instant")[(u_idx + t_idx) % 3]
            ts = base_ts - timedelta(
                days=(u_idx * 5 + t_idx) % 60,
                hours=(t_idx * 3) % 24,
            )
            rows.append((
                uid, "", topic, freq, 1,
                ts.strftime("%Y-%m-%d %H:%M:%S"),
            ))
    cur.executemany(
        "INSERT INTO topic_subscriptions (user_id, category_slug, topic, "
        "frequency, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_r4_reading_list(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    pool = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE '%long_read%' "
        "OR feature_tags LIKE '%iplayer%' OR feature_tags LIKE '%podcast%' "
        "ORDER BY view_count DESC LIMIT 120"
    )]
    folders = ["Read Later", "Long reads", "iPlayer", "Podcasts", "Weekend"]
    existing = set(cur.execute(
        "SELECT user_id, article_id FROM reading_list_items"
    ).fetchall())
    base_ts = MIRROR_REFERENCE_DATE
    rows: list[tuple] = []
    for u_idx, uid in enumerate(users):
        per_user = 12 + (u_idx * 3) % 6
        for a_idx in range(min(per_user, len(pool))):
            art_id = pool[(u_idx * 11 + a_idx * 13) % len(pool)]
            folder = folders[(u_idx + a_idx) % len(folders)]
            if (uid, art_id) in existing:
                continue
            existing.add((uid, art_id))
            ts = base_ts - timedelta(
                hours=(u_idx * 11 + a_idx * 13) % (24 * 60),
            )
            rows.append((
                uid, art_id, folder, "", 0,
                ts.strftime("%Y-%m-%d %H:%M:%S"), 0,
            ))
    cols = [r[1] for r in cur.execute("PRAGMA table_info(reading_list_items)")]
    if {"user_id", "article_id", "folder", "note", "priority", "added_at", "read"}.issubset(set(cols)):
        cur.executemany(
            "INSERT INTO reading_list_items (user_id, article_id, folder, "
            "note, priority, added_at, read) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        return len(rows)
    return 0


def plant_r4_sentinel(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        return
    uid_row = cur.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    art_row = cur.execute("SELECT id FROM articles ORDER BY id LIMIT 1").fetchone()
    if not (uid_row and art_row):
        return
    cur.execute(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, NULL, ?, 0, 1, ?)",
        (uid_row[0], art_row[0], R4_SENTINEL_BODY,
         MIRROR_REFERENCE_DATE.strftime("%Y-%m-%d %H:%M:%S")),
    )


# =======================================================================
# R5: BBC Verify / Newsround sub-channels + 24x24 live blog timestamped
# updates + quiz articles. All deterministic and idempotent via the
# R5_SENTINEL_BODY planted in `comments`.
# =======================================================================

R5_SENTINEL_BODY = "<<R5-baked>>"
R5_RNG = random.Random(20260601)

R5_NEW_CATEGORIES: list[tuple[str, str, str, str, int, str]] = [
    # slug, name, color, parent_slug, sort_order, description
    ("newsround",    "Newsround",           "#ffd230", "news",         12,
     "BBC Newsround: news for younger audiences, clear language with quizzes and explainers."),
    ("live_updates", "Live updates",        "#bb1919", "live",         13,
     "Rolling live-blog updates streamed from BBC News reporters: timestamped, jump-to-update navigation."),
    ("quizzes",      "Quizzes",             "#306ec4", "newsround",    14,
     "Take-attempt quizzes attached to BBC News stories — explainers and weekly news rounds."),
]


def ensure_r5_categories(con: sqlite3.Connection) -> int:
    """Idempotent insert of R5 categories. Returns number added."""
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM categories")}
    added = 0
    for slug, name, color, parent, order, desc in R5_NEW_CATEGORIES:
        if slug in existing:
            continue
        cur.execute(
            "INSERT INTO categories (slug, name, color, icon, parent_slug, "
            "sort_order, description, subtitle) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (slug, name, color, "", parent, order, desc, desc[:250]),
        )
        added += 1
    return added


# ---- BBC Verify fact-check pool ----------------------------------------

R5_VERIFY_TOPICS: list[tuple[str, str]] = [
    ("climate", "climate disinformation"),
    ("election", "election misinformation"),
    ("ukraine", "Ukraine war footage"),
    ("middle_east", "Middle East conflict claims"),
    ("ai_image", "AI-generated images"),
    ("ai_video", "deepfake videos"),
    ("vaccine", "vaccine claims"),
    ("nhs", "NHS funding claims"),
    ("immigration", "immigration statistics"),
    ("brexit", "Brexit aftermath statistics"),
    ("tax", "UK tax claims"),
    ("economy", "economic forecast claims"),
    ("crime", "crime statistics"),
    ("housing", "housing market claims"),
    ("energy", "energy bill claims"),
    ("pension", "pension policy claims"),
    ("school", "school standards data"),
    ("water", "water pollution data"),
    ("flood", "flood-area footage"),
    ("wildfire", "wildfire scale claims"),
    ("celebrity", "celebrity death hoaxes"),
    ("royal", "royal-family photo claims"),
    ("sports", "sports betting fraud claims"),
    ("scam", "online scam advert claims"),
    ("crypto", "crypto investment ads"),
    ("ai_chat", "AI chatbot output claims"),
    ("petition", "viral petition claims"),
    ("court", "court verdict claims"),
    ("policing", "policing-tactic videos"),
    ("protest", "protest crowd-size claims"),
]

R5_VERIFY_VERDICTS: list[tuple[str, str]] = [
    ("False",            "We rate this claim FALSE."),
    ("Misleading",       "We rate this claim MISLEADING — context omitted."),
    ("Partly true",      "Partly true — the underlying figure is right, the spin is not."),
    ("Unverified",       "We have not been able to verify this claim independently."),
    ("Out of context",   "Out of context — the footage is real but the date and place are wrong."),
    ("Doctored",         "Doctored — the image has been digitally altered."),
    ("Synthetic",        "Synthetic — this is an AI-generated image, not a photograph."),
    ("Accurate",         "We rate this claim ACCURATE — figures match official sources."),
]


def synth_bbc_verify(con, hero_pool: list[str]) -> list[dict]:
    """~700 BBC Verify fact-check articles in the existing 'bbcverify' section."""
    cid = _cat_id(con, "bbcverify")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    for ti, (topic_key, topic_label) in enumerate(R5_VERIFY_TOPICS):
        for vi, (verdict, verdict_line) in enumerate(R5_VERIFY_VERDICTS):
            for k in range(3):  # 30 topics × 8 verdicts × 3 = 720
                claim_n = ti * 24 + vi * 3 + k + 1
                slug = _det_slug("r5-verify", f"{topic_key}|{verdict.replace(' ','-').lower()}|{k}")
                headline = (
                    f"BBC Verify: claim about {topic_label} rated {verdict.lower()} (#{claim_n:03d})"
                )
                lead = (
                    f"A claim circulating about {topic_label} has been investigated by "
                    f"BBC Verify's open-source team. {verdict_line}"
                )
                body = (
                    f"{lead}\n\n"
                    f"What the claim says. Posts on social media assert that {topic_label} "
                    f"will have a dramatic effect within the next few weeks. The post was shared "
                    f"more than 12,000 times before BBC Verify began to look at it.\n\n"
                    f"What the evidence shows. We examined the original source data, cross-checked "
                    f"with the Office for National Statistics, the relevant government department, "
                    f"and at least one independent academic specialist. The numbers BBC Verify "
                    f"obtained do not match the figures shared online.\n\n"
                    f"Our verdict. {verdict_line} Readers should be cautious when these claims "
                    f"appear on viral threads — and check the date on every video or screenshot "
                    f"that is presented as 'happening now'.\n\n"
                    f"How to spot this yourself. Reverse-image-search any photo before sharing. "
                    f"Look up the original quote in a transcript. If the claim is a statistic, "
                    f"check the underlying dataset — usually one click away from the press release.\n\n"
                    f"BBC Verify is the team at BBC News dedicated to investigating disinformation, "
                    f"AI-generated content and viral misinformation. We publish our working, including "
                    f"the source URLs we used and the dates we checked them."
                )
                ts = base - timedelta(
                    days=(claim_n * 3) % 240,
                    hours=(_det_int(slug) // 7) % 24,
                    minutes=(_det_int(slug) // 11) % 60,
                )
                hero = hero_pool[(_det_int(slug) + 41) % len(hero_pool)] if hero_pool else ""
                out.append(_r4_make_row(
                    slug=slug, headline=headline, lead=lead, body=body,
                    category_id=cid, section_slug="bbcverify",
                    subsection=verdict, region="Verify", ts=ts,
                    view_count=4000 + (_det_int(slug) % 80000),
                    country="", hero=hero,
                    topics=["BBC Verify", topic_label, verdict],
                    feature_tags=["bbc_verify", "fact_check", topic_key, verdict.lower().replace(" ", "_")],
                    content_type="article",
                ))
    return out


# ---- BBC Newsround pool -------------------------------------------------

R5_NEWSROUND_THEMES: list[tuple[str, str]] = [
    ("animals",     "wildlife and pets stories for kids"),
    ("schools",     "what schools across the UK are up to"),
    ("space",       "space missions, rockets and stars"),
    ("sport",       "kid-friendly sport stories"),
    ("environment", "what kids can do to help the planet"),
    ("technology",  "tech news for younger audiences"),
    ("music",       "music chart and concert stories"),
    ("film",        "new films and TV shows reviewed"),
    ("books",       "great new books for kids"),
    ("games",       "game launches and esports"),
    ("history",     "interesting moments from history"),
    ("science",     "fun science discoveries explained"),
    ("food",        "food and cooking stories"),
    ("weather",     "weather and seasons explainers"),
    ("health",      "staying healthy as a kid"),
    ("art",         "art, museums and exhibitions"),
    ("politics",    "how the UK government works, explained"),
    ("travel",      "places around the world to read about"),
    ("oceans",      "stories from beneath the waves"),
    ("explainers",  "Newsround explains the big news"),
]


def synth_newsround(con, hero_pool: list[str]) -> list[dict]:
    """~800 BBC Newsround articles (kid-friendly news + explainers)."""
    cid = _cat_id(con, "newsround")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE - timedelta(days=2)
    angles = [
        "How {label} works, explained",
        "Five things to know about {label}",
        "Newsround quiz: what do you know about {label}?",
        "Kids' take: why {label} matters",
        "The big story: {label} this week",
    ]
    for ti, (theme, label) in enumerate(R5_NEWSROUND_THEMES):
        for ai, angle in enumerate(angles):
            for k in range(8):  # 20 × 5 × 8 = 800
                idx = ti * 40 + ai * 8 + k + 1
                slug = _det_slug("r5-nr", f"{theme}|{ai}|{k}")
                headline = angle.format(label=label) + f" — Newsround #{idx:03d}"
                lead = (
                    f"Newsround explains {label} in clear, kid-friendly language. "
                    f"This story is part of a regular Newsround series for ages 6 to 12."
                )
                body = (
                    f"{lead}\n\n"
                    f"What's happening? Newsround reporters have been looking into {label}. "
                    f"There's lots going on — and grown-ups are talking about it too — so we asked "
                    f"experts to help explain things in a way that makes sense for younger viewers.\n\n"
                    f"Why does it matter? The story affects kids in different ways depending on where "
                    f"they live in the UK. Some schools are running special lessons about it. "
                    f"We spoke to pupils in three classrooms — one in England, one in Scotland, and "
                    f"one in Wales — to hear what they think.\n\n"
                    f"What do the experts say? \"It's normal to have questions about big news stories,\" "
                    f"a child psychologist told Newsround. \"Talking to a grown-up you trust always helps.\"\n\n"
                    f"Take the Newsround quiz attached to this story to test what you've learned. "
                    f"And tell us your questions — Newsround answers a new viewer question every Friday."
                )
                ts = base - timedelta(
                    days=(idx * 2) % 220,
                    hours=(_det_int(slug) // 5) % 24,
                    minutes=(_det_int(slug) // 13) % 60,
                )
                hero = hero_pool[(_det_int(slug) + 23) % len(hero_pool)] if hero_pool else ""
                out.append(_r4_make_row(
                    slug=slug, headline=headline, lead=lead, body=body,
                    category_id=cid, section_slug="newsround",
                    subsection=theme.replace("_", " ").title(),
                    region="UK", ts=ts,
                    view_count=2000 + (_det_int(slug) % 25000),
                    country="UK", hero=hero,
                    topics=["Newsround", theme, "kids"],
                    feature_tags=["newsround", "kids", theme,
                                  "quiz" if ai == 2 else "explainer"],
                    content_type="article",
                ))
    return out


# ---- Live blogs: 24 blogs × 24+ timestamped updates --------------------

R5_LIVE_BLOG_TOPICS: list[tuple[str, str, str, str]] = [
    # slug suffix, headline, topic_label, section_slug
    ("uk-budget-2026",            "Chancellor's Spring Budget 2026 live",                     "UK Budget",        "politics"),
    ("commons-pmqs",              "PMQs live: Prime Minister faces opposition",               "PMQs",             "politics"),
    ("us-election-night",         "US presidential election night live",                      "US election",      "us_canada"),
    ("eu-summit",                 "EU summit live: leaders meet in Brussels",                 "EU summit",        "europe"),
    ("cop-summit",                "COP climate summit live updates",                          "COP climate",      "science"),
    ("ukraine-war",               "Ukraine war live: latest from the front line",             "Ukraine",          "europe"),
    ("middle-east-crisis",        "Middle East live: latest reaction and ceasefire talks",    "Middle East",      "middle_east"),
    ("autumn-statement",          "Autumn Statement live: Chancellor's economic update",      "Autumn Statement", "business"),
    ("interest-rate-decision",    "Bank of England rate decision live",                       "BoE rate",         "business"),
    ("fed-decision-day",          "US Federal Reserve decision day live",                     "Fed decision",     "business"),
    ("storm-tracker",             "Storm tracker live: latest weather warnings",              "Storm",            "weather"),
    ("by-election-night",         "By-election results live",                                 "By-election",      "politics"),
    ("local-elections-uk",        "UK local elections live results",                          "Local elections",  "politics"),
    ("nhs-strike-day",            "NHS strikes live: latest from picket lines",               "NHS strike",       "health"),
    ("rail-strike-day",           "Rail strikes live: travel disruption updates",             "Rail strike",      "uk"),
    ("oscars-night",              "Oscars live: ceremony updates from Hollywood",             "Oscars",           "culture"),
    ("eurovision-final",          "Eurovision Song Contest grand final live",                 "Eurovision",       "entertainment"),
    ("glastonbury-festival",      "Glastonbury Festival live updates",                        "Glastonbury",      "entertainment"),
    ("world-cup-final",           "World Cup Final live updates",                             "World Cup",        "football"),
    ("super-bowl-night",          "Super Bowl live: half-time and key plays",                 "Super Bowl",       "sport"),
    ("formula1-race-day",         "Formula 1 race day live: lap-by-lap updates",              "F1 race",          "formula1"),
    ("apple-keynote-live",        "Apple keynote live: new product launch",                   "Apple keynote",    "technology"),
    ("rocket-launch-day",         "Rocket launch live: countdown and lift-off",               "Rocket launch",    "science"),
    ("royal-event-day",           "Royal event live: ceremony and procession",                "Royal event",      "uk"),
]


def synth_r5_live_blogs(con, hero_pool: list[str]) -> list[dict]:
    """24 parent live-blog articles. Each will get 30 timestamped update
    rows in synth_r5_live_blog_updates()."""
    cid = _cat_id(con, "live_updates") or _cat_id(con, "live")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    for bi, (slug_suffix, headline, topic, section) in enumerate(R5_LIVE_BLOG_TOPICS):
        slug = _det_slug("r5-live", slug_suffix)
        lead = (
            f"Rolling coverage from BBC News reporters on the {topic} story. "
            f"Updates appear at the top of this page — refresh to see the latest, "
            f"or jump straight to an update by number using the index on the right."
        )
        body = (
            f"{lead}\n\n"
            f"Our team is following the story across multiple sources. Live blog "
            f"updates are timestamped, numbered, and accessible by URL "
            f"(jump to update N at /live/{slug_suffix}/update/N).\n\n"
            f"You can subscribe to instant push notifications for this live "
            f"blog from the Subscriptions page. Toggle the auto-refresh "
            f"indicator at the top of the page to control how often new "
            f"updates are pulled.\n\n"
            f"All times shown are UK time. This is the lead post for the live "
            f"blog; individual update entries are listed below in reverse "
            f"chronological order (newest first)."
        )
        ts = base - timedelta(
            days=bi % 60,
            hours=(_det_int(slug) // 3) % 24,
        )
        hero = hero_pool[(_det_int(slug) + 17) % len(hero_pool)] if hero_pool else ""
        out.append(_r4_make_row(
            slug=slug, headline=headline, lead=lead, body=body,
            category_id=cid, section_slug=section,
            subsection="Live blog", region=topic, ts=ts,
            view_count=20000 + (_det_int(slug) % 200000),
            country="", hero=hero,
            topics=["Live blog", topic],
            feature_tags=["live_blog", "live_blog_parent", slug_suffix],
            content_type="live",
            is_live=1, is_featured=1,
        ))
    return out


def synth_r5_live_blog_updates(con, hero_pool: list[str]) -> list[dict]:
    """24 live blogs × ~30 updates each = ~720 timestamped child rows.
    Each update has feature_tags = ['live_update', '<parent slug suffix>'],
    subsection = 'Update #N', and a deterministic published_at."""
    cid = _cat_id(con, "live_updates") or _cat_id(con, "live")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE
    # Reusable angle templates for each numbered update.
    update_angles = [
        ("Reporter on the ground confirms {topic} development",
         "Our correspondent on the ground in the area reports new movement around the {topic} story."),
        ("Government statement issued on {topic}",
         "The government has just issued a statement responding to the latest {topic} developments."),
        ("Opposition reaction to {topic} announcement",
         "The leader of the opposition has weighed in on the {topic} story with a fresh statement."),
        ("Market reaction: {topic} pushes index lower",
         "The FTSE 100 has moved on news related to {topic}; we're watching pound and gilts too."),
        ("Live picture: {topic} crowd gathers outside",
         "A live picture from the scene shows a growing crowd connected to the {topic} story."),
        ("Eyewitness account of {topic}",
         "An eyewitness has just told BBC News what they saw at the scene of the {topic} story."),
        ("Expert analysis on {topic}",
         "A specialist analyst from the LSE breaks down what the {topic} news really means."),
        ("Social media reaction to {topic}",
         "Hashtags related to {topic} are trending — BBC Verify is checking the most-shared posts."),
        ("Police confirm details around {topic}",
         "Police have now formally confirmed key details that had been swirling around the {topic} story."),
        ("International reaction to {topic}",
         "Reaction from foreign capitals is starting to come in on the {topic} story."),
        ("Behind the scenes on {topic}",
         "What our team is hearing inside the room — a quick behind-the-scenes note on {topic}."),
        ("Fact-check: viral claim about {topic} rated false",
         "BBC Verify has just rated a viral claim about {topic} as false; full write-up follows."),
        ("Quote of the moment on {topic}",
         "\"This changes everything.\" A pointed quote from a senior figure on the {topic} story."),
        ("Photo gallery: {topic} in pictures",
         "We're publishing a fresh gallery from BBC photographers covering the {topic} story."),
        ("Schedule update: {topic} timings shift",
         "A scheduling note: the next set of {topic} events has moved by 20 minutes."),
        ("Watch: {topic} key moment recap",
         "We've cut a 90-second video that recaps the key moment in the {topic} story so far."),
        ("Listen: BBC Sounds clip on {topic}",
         "A short BBC Sounds clip drops summarising where the {topic} story has reached."),
        ("Background: how the {topic} story unfolded",
         "If you're joining us, here's a short backgrounder on the {topic} story to catch you up."),
        ("Correction: earlier {topic} note updated",
         "We've corrected an earlier note in this live blog about {topic}; details below."),
        ("Numbers behind {topic}",
         "The hard numbers — the latest figures we're using on the {topic} story right now."),
        ("Reporter Q&A on {topic}",
         "Our correspondent takes three viewer questions on what's happening with {topic}."),
        ("Diaspora reaction to {topic}",
         "Communities affected by the {topic} story share their reaction with our diaspora team."),
        ("Children's perspective on {topic}",
         "Newsround has spoken to pupils about how they are following the {topic} story."),
        ("Sounds bite from {topic}",
         "A two-line audio bite has just dropped from the {topic} press conference."),
        ("Weather update affecting {topic}",
         "A weather warning has been issued that could affect how the {topic} story unfolds."),
        ("Sports angle on {topic}",
         "We're checking how the {topic} story will affect Saturday's planned sporting fixture."),
        ("Local impact of {topic} in Scotland",
         "From Holyrood: how Scottish institutions are responding to the {topic} story."),
        ("Local impact of {topic} in Wales",
         "From Cardiff: a quick Welsh angle on the unfolding {topic} story."),
        ("Local impact of {topic} in Northern Ireland",
         "From Belfast: how Stormont sees the unfolding {topic} story."),
        ("Editor's note: closing the live blog on {topic} for now",
         "We are pausing this live blog on {topic} — final summary follows. Thanks for following."),
    ]
    for bi, (slug_suffix, headline, topic, section) in enumerate(R5_LIVE_BLOG_TOPICS):
        for ui, (ang_h, ang_b) in enumerate(update_angles):
            update_n = ui + 1
            slug = _det_slug("r5-up", f"{slug_suffix}|{update_n:02d}")
            update_headline = ang_h.format(topic=topic) + f" (Update #{update_n:02d})"
            lead = ang_b.format(topic=topic)
            body = (
                f"{lead}\n\n"
                f"This is update #{update_n} on the {topic} live blog. The parent "
                f"live blog can be found at /live/{section} or by clicking the "
                f"live-stream link on the homepage.\n\n"
                f"Posted at UK time. Refresh the live blog to see further updates "
                f"after this one. You can also jump directly to a specific update "
                f"by appending /update/{update_n} to the live blog URL."
            )
            # Update timestamps step backwards from MIRROR_REFERENCE_DATE so
            # newer updates have higher published_at than older ones, but all
            # are deterministic from R5 inputs alone.
            ts = base - timedelta(
                days=bi % 60,
                hours=(update_angles.__len__() - ui) // 2,
                minutes=(update_n * 3 + bi * 7) % 60,
                seconds=(_det_int(slug) % 60),
            )
            hero = hero_pool[(_det_int(slug) + 71) % len(hero_pool)] if hero_pool else ""
            out.append(_r4_make_row(
                slug=slug, headline=update_headline, lead=lead, body=body,
                category_id=cid, section_slug=section,
                subsection=f"Update #{update_n:02d}",
                region=topic, ts=ts,
                view_count=400 + (_det_int(slug) % 9000),
                country="", hero=hero,
                topics=["Live update", topic, slug_suffix],
                feature_tags=["live_update", slug_suffix, f"update_{update_n}"],
                content_type="live_update",
            ))
    return out


# ---- Quiz articles -----------------------------------------------------

R5_QUIZ_TOPICS: list[tuple[str, str]] = [
    ("weekly_news",      "Weekly news quiz"),
    ("uk_politics",      "UK politics quiz"),
    ("world_history",    "World history quiz"),
    ("uk_history",       "UK history quiz"),
    ("science",          "Science quiz"),
    ("space",            "Space quiz"),
    ("oceans",           "Oceans quiz"),
    ("animals",          "Animals quiz"),
    ("sport",            "Sport quiz"),
    ("music",            "Music quiz"),
    ("film",             "Film quiz"),
    ("books",            "Books quiz"),
    ("food",             "Food quiz"),
    ("travel",           "Travel quiz"),
    ("weather",          "Weather quiz"),
    ("ai",               "AI explainer quiz"),
    ("climate",          "Climate quiz"),
    ("health",           "Health and the body quiz"),
    ("tech",             "Technology quiz"),
    ("languages",        "Languages quiz"),
    ("games",            "Games quiz"),
    ("arts",             "Arts and design quiz"),
    ("euro_football",    "European football quiz"),
    ("world_football",   "World football quiz"),
    ("cricket",          "Cricket quiz"),
]


def synth_r5_quizzes(con, hero_pool: list[str]) -> list[dict]:
    """~250 quiz article rows (25 topics × 10 weekly instalments)."""
    cid = _cat_id(con, "quizzes") or _cat_id(con, "newsround")
    if cid is None:
        return []
    out: list[dict] = []
    base = MIRROR_REFERENCE_DATE - timedelta(days=4)
    for ti, (theme, label) in enumerate(R5_QUIZ_TOPICS):
        for wk in range(10):
            slug = _det_slug("r5-quiz", f"{theme}|{wk:02d}")
            headline = f"Take the {label}: week {wk + 1:02d}"
            lead = (
                f"This week's {label.lower()} from BBC News. Ten multiple-choice "
                f"questions, scored at the end. Tap an answer to lock it in — "
                f"there are no time limits."
            )
            body = (
                f"{lead}\n\n"
                f"How to play. Read each question, tap the answer you think is "
                f"right, then move on. At the end, your score is shown out of 10. "
                f"You can re-take the quiz to try and beat your previous best.\n\n"
                f"Question 1. Which of these stories led BBC News this week? "
                f"(a) {label} angle one. (b) {label} angle two. (c) {label} angle "
                f"three. (d) {label} angle four.\n\n"
                f"Question 2. True or false? The {label.lower()} category has been "
                f"running on BBC News for more than a decade.\n\n"
                f"Question 3. Pick the correct {label.lower()} fact from this "
                f"week's news. Answers and explanations are revealed after you "
                f"submit your attempt.\n\n"
                f"Submit your attempt with the button at the bottom of the page. "
                f"Quiz attempts are saved when you are signed in, so you can see "
                f"how your scores change over the year. Don't worry if you do not "
                f"score full marks — the goal is to learn something new."
            )
            ts = base - timedelta(
                days=(ti * 7 + wk * 14) % 240,
                hours=(_det_int(slug) // 11) % 24,
                minutes=(_det_int(slug) // 7) % 60,
            )
            hero = hero_pool[(_det_int(slug) + 59) % len(hero_pool)] if hero_pool else ""
            out.append(_r4_make_row(
                slug=slug, headline=headline,
                lead=lead, body=body,
                category_id=cid, section_slug="quizzes",
                subsection=label, region="UK", ts=ts,
                view_count=1500 + (_det_int(slug) % 20000),
                country="UK", hero=hero,
                topics=["Quiz", label, theme],
                feature_tags=["quiz", theme, f"week_{wk + 1:02d}"],
                content_type="article",
            ))
    return out


# ---- R5 inserts (articles / comments / reading_history / ...) ----------

def insert_r5_articles(con: sqlite3.Connection, batch: list[dict]) -> int:
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM articles")}
    rows = [a for a in batch if a["slug"] not in existing]
    if not rows:
        return 0
    cur.executemany(_ART_INSERT_SQL, rows)
    return len(rows)


R5_COMMENT_TOP: list[str] = [
    "BBC Verify checked this; the verdict surprised me.",
    "Live-blog auto-refresh is a great addition — was waiting for this.",
    "Newsround quizzes were always my favourite. Glad to see them back.",
    "Jumped straight to update 12 — saved me ten minutes scrolling.",
    "The transcript link is exactly what I needed for accessibility.",
    "Dark mode finally! Reading at night is so much easier now.",
    "Hover-preview on related links is so useful. Nicely done.",
    "Saved for later — sync across my phone and laptop works smoothly.",
    "Followed this topic so I get push alerts next time.",
    "Helpful explainer for the kids in my class.",
    "The chapter markers on the video are spot on.",
    "High-contrast mode is much appreciated — readability is excellent.",
]

R5_COMMENT_REPLIES: list[str] = [
    "Agreed — the design polish is noticeable across the site.",
    "Same here. Auto-refresh badge means I do not have to keep refreshing.",
    "Thanks for the tip — I'll use the /update/N jump-to next time.",
    "Was looking for the same accessibility option. Pleasantly surprised.",
    "Good point — the comment expand/collapse helps long threads load faster.",
]


def insert_r5_comments(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if len(user_ids) < 2:
        return 0
    # Pool of R5-new articles for the comment seeding.
    pool: list[tuple[int, str]] = []
    for tag in ("bbc_verify", "newsround", "live_blog_parent",
                "live_update", "quiz"):
        rows = cur.execute(
            "SELECT id, headline FROM articles "
            "WHERE feature_tags LIKE ? ORDER BY view_count DESC LIMIT 30",
            (f'%\"{tag}\"%',),
        ).fetchall()
        pool.extend(rows)
    seen: set[int] = set()
    pool = [t for t in pool if not (t[0] in seen or seen.add(t[0]))][:120]

    base_ts = MIRROR_REFERENCE_DATE
    top_rows: list[tuple] = []
    for idx, (art_id, _headline) in enumerate(pool):
        n_top = 2 + (idx % 3)
        for j in range(n_top):
            uid = user_ids[(idx * 11 + j * 3) % len(user_ids)]
            body = R5_COMMENT_TOP[(idx * 5 + j * 7) % len(R5_COMMENT_TOP)]
            offset_h = (idx * 13 + j * 17) % (24 * 25)
            ts = base_ts - timedelta(hours=offset_h, minutes=(j + idx * 3) % 60)
            like = (idx * j + 3) % 24
            top_rows.append((uid, art_id, None, body, like, 0,
                             ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        top_rows,
    )
    inserted = len(top_rows)

    # 2-deep replies on every 4th top-level comment
    fresh = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL ORDER BY id DESC LIMIT ?",
        (inserted,),
    ))
    fresh.reverse()
    for i, (cid, art_id, parent_uid, parent_created) in enumerate(fresh):
        if i % 4 != 0:
            continue
        cur_parent = cid
        cur_parent_uid = parent_uid
        ts_parent = datetime.strptime(parent_created, "%Y-%m-%d %H:%M:%S")
        for depth in range(1, 3):
            ruid = user_ids[(cur_parent_uid + depth + i + 2) % len(user_ids)]
            if ruid == cur_parent_uid:
                ruid = user_ids[(cur_parent_uid + depth + i + 3) % len(user_ids)]
            body = R5_COMMENT_REPLIES[(i * 7 + depth * 5) % len(R5_COMMENT_REPLIES)]
            ts_parent = ts_parent + timedelta(hours=depth, minutes=(depth * 13) % 60)
            cur.execute(
                "INSERT INTO comments (user_id, article_id, parent_id, body, "
                "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ruid, art_id, cur_parent, body, (depth * (i + 1)) % 17, 0,
                 ts_parent.strftime("%Y-%m-%d %H:%M:%S")),
            )
            inserted += 1
            cur_parent = cur.lastrowid
            cur_parent_uid = ruid
    return inserted


def insert_r5_reading_history(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    art_pool = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE '%bbc_verify%' "
        "OR feature_tags LIKE '%newsround%' OR feature_tags LIKE '%live_update%' "
        "OR feature_tags LIKE '%quiz%' "
        "ORDER BY view_count DESC LIMIT 200"
    )]
    base_ts = MIRROR_REFERENCE_DATE
    existing = set(cur.execute(
        "SELECT user_id, article_id FROM reading_history"
    ).fetchall())
    rows: list[tuple] = []
    for u_idx, uid in enumerate(users):
        per_user = 32 + (u_idx * 4) % 10
        for a_idx in range(min(per_user, len(art_pool))):
            art_id = art_pool[(u_idx * 19 + a_idx * 13) % len(art_pool)]
            if (uid, art_id) in existing:
                continue
            existing.add((uid, art_id))
            ts = base_ts - timedelta(
                hours=(u_idx * 23 + a_idx * 7) % (24 * 70),
                minutes=(a_idx * 11) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO reading_history (user_id, article_id, viewed_at) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_r5_bookmarks(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    art_pool = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE '%bbc_verify%' "
        "OR feature_tags LIKE '%newsround%' OR feature_tags LIKE '%quiz%' "
        "OR feature_tags LIKE '%live_blog_parent%' "
        "ORDER BY view_count DESC LIMIT 160"
    )]
    base_ts = MIRROR_REFERENCE_DATE
    existing = set(cur.execute(
        "SELECT user_id, article_id FROM bookmarks"
    ).fetchall())
    rows: list[tuple] = []
    for u_idx, uid in enumerate(users):
        per_user = 18 + (u_idx * 3) % 8
        for a_idx in range(min(per_user, len(art_pool))):
            art_id = art_pool[(u_idx * 17 + a_idx * 19) % len(art_pool)]
            if (uid, art_id) in existing:
                continue
            existing.add((uid, art_id))
            ts = base_ts - timedelta(
                hours=(u_idx * 13 + a_idx * 7) % (24 * 60),
                minutes=(a_idx * 9) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    cur.executemany(
        "INSERT INTO bookmarks (user_id, article_id, bookmarked_at) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_r5_subscriptions(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    new_topics = [
        "BBC Verify", "Newsround", "Quizzes",
        "UK Budget live", "PMQs live", "US election live",
        "EU summit live", "COP climate live", "Ukraine live",
        "Middle East live", "Storm tracker live",
        "Royal event live", "Apple keynote live",
        "F1 race day live", "Eurovision live",
    ]
    rows: list[tuple] = []
    existing = set(cur.execute(
        "SELECT user_id, topic FROM topic_subscriptions"
    ).fetchall())
    base_ts = MIRROR_REFERENCE_DATE
    for u_idx, uid in enumerate(users):
        for t_idx, topic in enumerate(new_topics):
            if (u_idx + t_idx) % 2 != 1:
                continue
            if (uid, topic) in existing:
                continue
            existing.add((uid, topic))
            freq = ("instant", "daily", "weekly")[(u_idx + t_idx) % 3]
            ts = base_ts - timedelta(
                days=(u_idx * 7 + t_idx) % 70,
                hours=(t_idx * 5) % 24,
            )
            rows.append((
                uid, "", topic, freq, 1,
                ts.strftime("%Y-%m-%d %H:%M:%S"),
            ))
    cur.executemany(
        "INSERT INTO topic_subscriptions (user_id, category_slug, topic, "
        "frequency, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_r5_reading_list(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        return 0
    users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not users:
        return 0
    pool = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE '%bbc_verify%' "
        "OR feature_tags LIKE '%newsround%' OR feature_tags LIKE '%quiz%' "
        "ORDER BY view_count DESC LIMIT 140"
    )]
    folders = ["Read Later", "BBC Verify", "Newsround", "Quizzes", "Cross-device"]
    existing = set(cur.execute(
        "SELECT user_id, article_id FROM reading_list_items"
    ).fetchall())
    base_ts = MIRROR_REFERENCE_DATE
    rows: list[tuple] = []
    for u_idx, uid in enumerate(users):
        per_user = 10 + (u_idx * 3) % 7
        for a_idx in range(min(per_user, len(pool))):
            art_id = pool[(u_idx * 9 + a_idx * 11) % len(pool)]
            folder = folders[(u_idx + a_idx) % len(folders)]
            if (uid, art_id) in existing:
                continue
            existing.add((uid, art_id))
            ts = base_ts - timedelta(
                hours=(u_idx * 13 + a_idx * 7) % (24 * 55),
            )
            rows.append((
                uid, art_id, folder, "", 0,
                ts.strftime("%Y-%m-%d %H:%M:%S"), 0,
            ))
    cols = [r[1] for r in cur.execute("PRAGMA table_info(reading_list_items)")]
    if {"user_id", "article_id", "folder", "note", "priority", "added_at", "read"}.issubset(set(cols)):
        cur.executemany(
            "INSERT INTO reading_list_items (user_id, article_id, folder, "
            "note, priority, added_at, read) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        return len(rows)
    return 0


def plant_r5_sentinel(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        return
    uid_row = cur.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    art_row = cur.execute("SELECT id FROM articles ORDER BY id LIMIT 1").fetchone()
    if not (uid_row and art_row):
        return
    cur.execute(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, NULL, ?, 0, 1, ?)",
        (uid_row[0], art_row[0], R5_SENTINEL_BODY,
         MIRROR_REFERENCE_DATE.strftime("%Y-%m-%d %H:%M:%S")),
    )


def bake_r5(con: sqlite3.Connection) -> dict[str, int]:
    """Apply all R5 additions. Idempotent."""
    stats: dict[str, int] = {}
    stats["new_categories"] = ensure_r5_categories(con)

    if con.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R5_SENTINEL_BODY,)
    ).fetchone():
        stats["already_baked"] = 1
        return stats

    hero_pool = _hero_image_pool(con)
    if not hero_pool:
        hero_pool = [""]

    batches: list[list[dict]] = [
        synth_bbc_verify(con, hero_pool),
        synth_newsround(con, hero_pool),
        synth_r5_live_blogs(con, hero_pool),
        synth_r5_live_blog_updates(con, hero_pool),
        synth_r5_quizzes(con, hero_pool),
    ]
    total = 0
    for batch in batches:
        total += insert_r5_articles(con, batch)
    stats["new_articles"] = total

    stats["new_comments"] = insert_r5_comments(con)
    stats["new_reading_history"] = insert_r5_reading_history(con)
    stats["new_bookmarks"] = insert_r5_bookmarks(con)
    stats["new_subscriptions"] = insert_r5_subscriptions(con)
    stats["new_reading_list"] = insert_r5_reading_list(con)

    plant_r5_sentinel(con)
    return stats


def bake_r4(con: sqlite3.Connection) -> dict[str, int]:
    """Apply all R4 additions. Idempotent."""
    stats: dict[str, int] = {}
    stats["new_categories"] = ensure_r4_categories(con)

    if con.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R4_SENTINEL_BODY,)
    ).fetchone():
        stats["already_baked"] = 1
        return stats

    hero_pool = _hero_image_pool(con)
    if not hero_pool:
        hero_pool = [""]

    batches: list[list[dict]] = [
        synth_bbc_africa(con, hero_pool),
        synth_bbc_brasil(con, hero_pool),
        synth_bbc_mundo(con, hero_pool),
        synth_bbc_arabic(con, hero_pool),
        synth_bbc_persian(con, hero_pool),
        synth_bbc_russian(con, hero_pool),
        synth_bbc_china(con, hero_pool),
        synth_bbc_india(con, hero_pool),
        synth_world_country_drill(con, hero_pool),
        synth_in_pictures_essays(con, hero_pool),
        synth_audio_digests(con, hero_pool),
        synth_weather_7day(con, hero_pool),
        synth_iplayer_watchlist(con, hero_pool),
        synth_video_clips(con, hero_pool),
        synth_breaking_news(con, hero_pool),
        synth_multi_step_longreads(con, hero_pool),
        synth_podcast_genres(con, hero_pool),
    ]
    total = 0
    for batch in batches:
        total += insert_r4_articles(con, batch)
    stats["new_articles"] = total

    stats["new_comments"] = insert_r4_comments(con)
    stats["new_reading_history"] = insert_r4_reading_history(con)
    stats["new_bookmarks"] = insert_r4_bookmarks(con)
    stats["new_subscriptions"] = insert_r4_subscriptions(con)
    stats["new_reading_list"] = insert_r4_reading_list(con)

    plant_r4_sentinel(con)
    return stats


# =======================================================================
# R6 — reporter beats, country drills, long-running stories, edge cases
# =======================================================================
# R6 lifts the corpus to 10000+ articles by adding deterministic
# beats-and-bylines content. All synth functions are independent of R2-R5
# data and gated by the R6_SENTINEL_BODY comment.

R6_SENTINEL_BODY = "<<R6-baked>>"
R6_RNG = random.Random(20260626)


# ---- R6 reporter roster (50 reporters, each with a beat) ---------------
# Each tuple is (full_name, beat_slug, beat_label, section_slug, regions).
# `regions` is a small list of country/region tokens the reporter "covers";
# we cycle through them deterministically per article so each reporter's
# 30-article series visits 3-6 places naturally.

R6_REPORTERS: list[tuple[str, str, str, str, list[str]]] = [
    ("Adaeze Okafor",      "africa-economy",      "Africa economy",          "africa",        ["Nigeria", "Ghana", "Senegal", "Kenya"]),
    ("Bao Lin",            "china-tech",          "China technology",        "asia",          ["Beijing", "Shanghai", "Shenzhen", "Hong Kong"]),
    ("Cathal O'Riordan",   "ireland-politics",    "Ireland politics",        "europe",        ["Dublin", "Belfast", "Galway"]),
    ("Dawit Mengesha",     "horn-of-africa",      "Horn of Africa",          "africa",        ["Ethiopia", "Somalia", "Eritrea", "Djibouti"]),
    ("Elena Petrova",      "russia-society",      "Russia and society",      "europe",        ["Moscow", "St Petersburg", "Vladivostok"]),
    ("Fatima Khoury",      "middle-east-business","Middle East business",    "middle_east",   ["Dubai", "Riyadh", "Doha", "Cairo"]),
    ("Gita Rangarajan",    "south-asia",          "South Asia",              "asia",          ["Delhi", "Mumbai", "Dhaka", "Colombo"]),
    ("Henrik Lindqvist",   "nordic",              "Nordic affairs",          "europe",        ["Stockholm", "Oslo", "Copenhagen", "Helsinki"]),
    ("Isla Macdonald",     "scotland-politics",   "Scotland politics",       "scotland",      ["Edinburgh", "Glasgow", "Aberdeen"]),
    ("Jamal Carter",       "us-justice",          "US justice",              "us_canada",     ["Washington", "New York", "Atlanta"]),
    ("Kiran Patel",        "uk-health",           "UK health",               "uk",            ["London", "Manchester", "Birmingham"]),
    ("Lior Adler",         "tel-aviv-bureau",     "Tel Aviv bureau",         "middle_east",   ["Tel Aviv", "Jerusalem", "Haifa"]),
    ("Marek Wojcik",       "central-europe",      "Central Europe",          "europe",        ["Warsaw", "Prague", "Budapest", "Bratislava"]),
    ("Nadia Belkacem",     "north-africa",        "North Africa",            "africa",        ["Algiers", "Tunis", "Rabat", "Tripoli"]),
    ("Olivia Tan",         "se-asia",             "South East Asia",         "asia",          ["Singapore", "Jakarta", "Bangkok", "Manila"]),
    ("Pablo Restrepo",     "andean",              "Andean correspondent",    "latin_america", ["Lima", "Bogota", "Quito", "La Paz"]),
    ("Qadira Hassan",      "gulf-energy",         "Gulf energy",             "middle_east",   ["Abu Dhabi", "Kuwait City", "Manama"]),
    ("Rohan Mehta",        "asia-markets",        "Asia markets",            "business",      ["Tokyo", "Seoul", "Singapore", "Mumbai"]),
    ("Sara Larsen",        "climate-policy",      "Climate policy",          "science",       ["Geneva", "Brussels", "Nairobi"]),
    ("Tomas Aguirre",      "southern-cone",       "Southern Cone",           "latin_america", ["Buenos Aires", "Santiago", "Montevideo"]),
    ("Una Davies",         "wales-affairs",       "Wales affairs",           "wales",         ["Cardiff", "Swansea", "Wrexham"]),
    ("Viktor Novak",       "balkans",             "Balkans",                 "europe",        ["Belgrade", "Sarajevo", "Pristina", "Zagreb"]),
    ("Wei Zhao",           "greater-china",       "Greater China",           "asia",          ["Taipei", "Hong Kong", "Macau"]),
    ("Xavi Costa",         "iberia",              "Iberian peninsula",       "europe",        ["Madrid", "Barcelona", "Lisbon"]),
    ("Yara El-Sayed",      "egypt-bureau",        "Egypt bureau",            "africa",        ["Cairo", "Alexandria", "Aswan"]),
    ("Zach Holloway",      "westminster",         "Westminster",             "politics",      ["London", "Edinburgh", "Cardiff", "Belfast"]),
    ("Aamir Sheikh",       "pakistan",            "Pakistan",                "asia",          ["Islamabad", "Karachi", "Lahore"]),
    ("Beata Kowalska",     "poland-economy",      "Poland economy",          "business",      ["Warsaw", "Krakow", "Gdansk"]),
    ("Cleo Mavroudis",     "greece-cyprus",       "Greece and Cyprus",       "europe",        ["Athens", "Thessaloniki", "Nicosia"]),
    ("Daniel Okeke",       "west-africa",         "West Africa",             "africa",        ["Lagos", "Accra", "Abidjan", "Dakar"]),
    ("Emma Whitfield",     "tech-startups",       "Tech startups",           "technology",    ["London", "San Francisco", "Berlin"]),
    ("Felipe Duarte",      "brazil-politics",     "Brazil politics",         "latin_america", ["Brasilia", "Sao Paulo", "Rio de Janeiro"]),
    ("Grace Tembo",        "southern-africa",     "Southern Africa",         "africa",        ["Johannesburg", "Cape Town", "Harare"]),
    ("Hiroshi Tanaka",     "japan-bureau",        "Japan bureau",            "asia",          ["Tokyo", "Osaka", "Sapporo", "Fukuoka"]),
    ("Iulia Stancu",       "romania-moldova",     "Romania and Moldova",     "europe",        ["Bucharest", "Cluj-Napoca", "Chisinau"]),
    ("Joon Park",          "korea-affairs",       "Korea affairs",           "asia",          ["Seoul", "Busan", "Incheon"]),
    ("Kemi Adeyemi",       "lagos-bureau",        "Lagos bureau",            "africa",        ["Lagos", "Abuja", "Port Harcourt"]),
    ("Lucia Romero",       "mexico-bureau",       "Mexico bureau",           "latin_america", ["Mexico City", "Monterrey", "Guadalajara"]),
    ("Mariana Costa",      "lisbon-bureau",       "Lisbon bureau",           "europe",        ["Lisbon", "Porto", "Coimbra"]),
    ("Niamh O'Brien",      "northern-ireland",    "Northern Ireland",        "northern_ireland",["Belfast", "Derry", "Armagh"]),
    ("Omar Saleh",         "levant",              "Levant",                  "middle_east",   ["Beirut", "Damascus", "Amman"]),
    ("Priya Iyer",         "india-business",      "India business",          "business",      ["Mumbai", "Bengaluru", "Hyderabad", "Delhi"]),
    ("Quentin Marsh",      "europe-economy",      "Europe economy",          "business",      ["Frankfurt", "Paris", "Amsterdam"]),
    ("Rashida Bello",      "sahel",               "Sahel",                   "africa",        ["Bamako", "Niamey", "Ouagadougou", "N'Djamena"]),
    ("Stefan Becker",      "berlin-bureau",       "Berlin bureau",           "europe",        ["Berlin", "Munich", "Hamburg"]),
    ("Thiago Souza",       "rio-bureau",          "Rio bureau",              "latin_america", ["Rio de Janeiro", "Salvador", "Belo Horizonte"]),
    ("Una Cassidy",        "irish-economy",       "Irish economy",           "business",      ["Dublin", "Cork", "Limerick"]),
    ("Vihaan Joshi",       "delhi-bureau",        "Delhi bureau",            "asia",          ["Delhi", "Jaipur", "Lucknow"]),
    ("Wendy Ofori",        "accra-bureau",        "Accra bureau",            "africa",        ["Accra", "Kumasi", "Tamale"]),
    ("Yuki Watanabe",      "japan-economy",       "Japan economy",           "business",      ["Tokyo", "Osaka", "Nagoya"]),
]


# ---- R6 story angles cycled per reporter -------------------------------
# Each entry expands {region} (a city/country from the reporter's `regions`)
# and {beat} (the reporter's beat label) into a headline + lead.

R6_BEAT_ANGLES: list[tuple[str, str]] = [
    ("{region}: inside the policy shift driving {beat}",
     "A months-long investigation reveals how {region} officials reshaped {beat} after a series of closed-door reviews. Insiders describe the trade-offs."),
    ("Why {beat} matters this week in {region}",
     "Our correspondent unpacks the local context behind the headline numbers — what changed, who pays, and what comes next."),
    ("{region} explained: the five things to know about {beat}",
     "A short primer for readers catching up. Five clear take-aways drawn from BBC reporting in {region}."),
    ("Reaction in {region}: communities respond to the latest {beat} announcement",
     "We spoke to teachers, traders and civic groups across {region}. Their answers were mixed, and rarely matched the official line."),
    ("Analysis: how the {beat} debate is playing out on the ground in {region}",
     "Beyond the press releases, the real argument is being made in town halls and bus queues. Here is what our reporter found."),
    ("{region} hospital chiefs warn over winter pressures linked to {beat}",
     "Senior NHS-equivalent leaders in {region} say staffing decisions made twelve months ago are now visible in admissions data."),
    ("Numbers behind the story: {beat} in {region}, charted",
     "We break down the latest official statistics from {region}. The trend has shifted; the underlying drivers have not."),
    ("Long read: a year of {beat} reporting from {region}",
     "Twelve months of our coverage, pulled together. What changed, what stalled, and what readers told us mattered most."),
    ("{region} elections: candidates on {beat}",
     "We compared every major candidate's published position on {beat}. Differences appeared sharper than the headline rhetoric suggests."),
    ("{region} business briefing: how firms are pricing in {beat}",
     "Quarterly updates from {region}-listed companies show a pattern of conservative guidance. Analysts say that may be deliberate."),
    ("{region} weather and {beat}: the unexpected connection",
     "Seasonal forecasts are influencing decisions in unexpected places. Our team explains the loop."),
    ("Verify: what is true and what is not in this week's {beat} coverage",
     "The team at BBC Verify checked four widely-shared claims about {beat} in {region}. Two stand up; two do not."),
    ("Voices from {region}: '{beat} reshaped how we live this year'",
     "We collected first-person accounts from readers in {region}. Their words, lightly edited for clarity."),
    ("{region}: court ruling changes the {beat} landscape",
     "A judgment handed down this week reshapes the rules. Lawyers say the ripple will be slow but real."),
    ("Q&A: the {beat} questions readers in {region} keep asking",
     "We collected the most-asked reader questions from our recent {region} coverage and answered them in plain language."),
    ("Behind the scenes: how we reported on {beat} in {region}",
     "A note from our editors on sourcing, verification and the choices behind this week's package."),
    ("{region} youth perspective: how under-25s see {beat}",
     "Newsround's older-readers edition gathered views from sixth-formers and apprentices in {region}. Highlights here."),
    ("Climate angle: {beat} and the changing season in {region}",
     "BBC Climate Watch examines the overlap between {beat} policy and shifting weather patterns observed in {region}."),
    ("Profile: the person now leading {beat} reform in {region}",
     "A close look at the official tasked with delivering the new programme. Colleagues describe a quiet but determined operator."),
    ("Watch: a five-minute primer on {beat} in {region}",
     "Our explainer video walks viewers through the big moving parts. Closed captions and a full transcript are available."),
    ("Listen: the {beat} podcast — this week in {region}",
     "Our weekly podcast convenes correspondents in {region} and the regional desk to take stock."),
    ("{region}: opposition demands inquiry into {beat} decisions",
     "Opposition figures called for a formal review citing transparency concerns. The government says existing oversight is adequate."),
    ("Fact check: are the {beat} numbers in {region} really up?",
     "Two competing data sets give two different answers. We walked through both and show our work."),
    ("In pictures: a day of {beat} reporting in {region}",
     "A photo essay following our reporting team through one day across the region."),
    ("Reader replies: your responses to last week's {beat} story in {region}",
     "Hundreds of you wrote in. We chose a representative cross-section, then ran them past our specialist correspondent."),
    ("{region} budget: what {beat} got, and what it did not",
     "The annual budget allocation for {beat} held steady in nominal terms. Inflation may tell a different story."),
    ("Investigation: a six-month look at {beat} contracts in {region}",
     "We obtained procurement records covering the last two financial years. The patterns surprised some seasoned analysts."),
    ("Opinion: a {region} academic on the next phase of {beat}",
     "A guest contribution from a researcher who has tracked the field for fifteen years. The view from the seminar room."),
    ("Live update summary: a day of {beat} news in {region}",
     "A consolidated summary of our live blog coverage. Every key update, time-stamped and contextualised."),
    ("{region}: the {beat} story you may have missed this week",
     "A small story with outsized consequences. Our correspondent walks through why this one mattered."),
]


def _r6_synth_body(lead: str, region: str, beat: str) -> str:
    """Six-paragraph deterministic body keyed off the lead + region + beat.
    The body never references real-time data; it weaves the lead phrase
    through six narrative paragraphs that look like a real BBC report."""
    return (
        f"{lead}\n\n"
        f"In {region}, the story has been building for several weeks. Our team "
        f"spoke to local officials, civic groups and businesses about how "
        f"the latest developments around {beat} are being felt on the ground.\n\n"
        f"The headline numbers tell only part of the story. Behind them sit "
        f"choices made over the past year — choices that are now visible in "
        f"daily life across {region}. We document those choices, and the "
        f"people they touch.\n\n"
        f"Critics argue the pace of change has been too quick; supporters say "
        f"the alternative was already failing. Both sides cite evidence drawn "
        f"from the same official data sets. Reading between them is now part "
        f"of the job for anyone tracking {beat}.\n\n"
        f"BBC Verify has separately checked three of the most-shared claims "
        f"circulating about {beat} this week. Their working is published in "
        f"a sister piece linked from this article.\n\n"
        f"More from our {region} bureau in the coming days. Readers who want "
        f"to follow this story can subscribe to the relevant topic from this "
        f"page; updates will arrive in the dashboard digest."
    )


def _r6_make_row(*, slug, headline, lead, body, category_id, section_slug,
                 subsection, region_label, ts, view_count, country=None,
                 hero="", topics=None, feature_tags=None, content_type="article",
                 author="BBC News", is_featured=0, is_breaking=0, is_live=0,
                 video_url=""):
    return {
        "slug": slug,
        "headline": headline,
        "subtitle": lead[:300],
        "summary": lead[:300],
        "body": body,
        "author": author,
        "category_id": category_id,
        "hero_image": hero,
        "gallery_json": "[]",
        "gallery_full_json": "{}",
        "topics_json": json.dumps(topics or [region_label]),
        "published_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "reading_time": max(2, len(body.split()) // 200),
        "word_count": len(body.split()),
        "view_count": view_count,
        "is_featured": is_featured,
        "is_breaking": is_breaking,
        "is_live": is_live,
        "location": country or region_label,
        "source_url": f"https://www.bbc.com/news/articles/{slug}",
        "section_slug": section_slug,
        "subsection": subsection,
        "region": region_label,
        "video_url": video_url,
        "feature_tags": json.dumps(feature_tags or [section_slug]),
        "content_type": content_type,
    }


def _r6_cat_id(con, slug: str) -> int | None:
    row = con.execute("SELECT id FROM categories WHERE slug=?", (slug,)).fetchone()
    return row[0] if row else None


def synth_r6_reporter_beats(con, hero_pool: list[str]) -> list[dict]:
    """50 reporters × 30 stories = 1500 articles. Each reporter cycles
    through their region list and the angle list deterministically."""
    base = MIRROR_REFERENCE_DATE
    out: list[dict] = []
    for rep_idx, (name, beat_slug, beat_label, section_slug, regions) in enumerate(R6_REPORTERS):
        cid = _r6_cat_id(con, section_slug) or _r6_cat_id(con, "news") or 1
        for ai, (hl_pat, lead_pat) in enumerate(R6_BEAT_ANGLES):
            region = regions[ai % len(regions)]
            headline = hl_pat.format(region=region, beat=beat_label)
            lead = lead_pat.format(region=region, beat=beat_label)
            slug = _det_slug("r6-rep", f"{name}|{ai}")
            hero = hero_pool[(_det_int(slug) + 7 + rep_idx) % len(hero_pool)] if hero_pool else ""
            ts = base - timedelta(
                days=(rep_idx * 2 + ai) % 180 + 1,
                hours=(_det_int(slug) // 7) % 24,
                minutes=(_det_int(slug) // 3) % 60,
            )
            body = _r6_synth_body(lead, region, beat_label)
            topics = [beat_label, region, name.split()[-1] + " beat"]
            feature_tags = ["reporter-series", beat_slug, region.lower().replace(" ", "-")]
            view_count = 200 + (_det_int(slug) % 18000)
            out.append(_r6_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug=section_slug,
                subsection=region, region_label=region, ts=ts,
                view_count=view_count, country=region, hero=hero,
                topics=topics, feature_tags=feature_tags, author=name,
                is_featured=1 if (rep_idx + ai) % 11 == 0 else 0,
            ))
    return out


# ---- R6 country drill — 60 countries × 12 stories each = 720 -----------

R6_COUNTRIES: list[tuple[str, str, str, str]] = [
    # (country, capital, region_label, section_slug)
    ("Argentina",   "Buenos Aires", "Latin America", "latin_america"),
    ("Australia",   "Canberra",     "Asia Pacific",  "asia"),
    ("Austria",     "Vienna",       "Europe",        "europe"),
    ("Bangladesh",  "Dhaka",        "Asia",          "asia"),
    ("Belgium",     "Brussels",     "Europe",        "europe"),
    ("Bolivia",     "La Paz",       "Latin America", "latin_america"),
    ("Botswana",    "Gaborone",     "Africa",        "africa"),
    ("Brazil",      "Brasilia",     "Latin America", "latin_america"),
    ("Bulgaria",    "Sofia",        "Europe",        "europe"),
    ("Cambodia",    "Phnom Penh",   "Asia",          "asia"),
    ("Canada",      "Ottawa",       "US & Canada",   "us_canada"),
    ("Chile",       "Santiago",     "Latin America", "latin_america"),
    ("Colombia",    "Bogota",       "Latin America", "latin_america"),
    ("Croatia",     "Zagreb",       "Europe",        "europe"),
    ("Czechia",     "Prague",       "Europe",        "europe"),
    ("Denmark",     "Copenhagen",   "Europe",        "europe"),
    ("Ecuador",     "Quito",        "Latin America", "latin_america"),
    ("Egypt",       "Cairo",        "Africa",        "africa"),
    ("Estonia",     "Tallinn",      "Europe",        "europe"),
    ("Ethiopia",    "Addis Ababa",  "Africa",        "africa"),
    ("Finland",     "Helsinki",     "Europe",        "europe"),
    ("France",      "Paris",        "Europe",        "europe"),
    ("Germany",     "Berlin",       "Europe",        "europe"),
    ("Ghana",       "Accra",        "Africa",        "africa"),
    ("Greece",      "Athens",       "Europe",        "europe"),
    ("Hungary",     "Budapest",     "Europe",        "europe"),
    ("India",       "Delhi",        "Asia",          "asia"),
    ("Indonesia",   "Jakarta",      "Asia",          "asia"),
    ("Ireland",     "Dublin",       "Europe",        "europe"),
    ("Italy",       "Rome",         "Europe",        "europe"),
    ("Japan",       "Tokyo",        "Asia",          "asia"),
    ("Jordan",      "Amman",        "Middle East",   "middle_east"),
    ("Kazakhstan",  "Astana",       "Asia",          "asia"),
    ("Kenya",       "Nairobi",      "Africa",        "africa"),
    ("Latvia",      "Riga",         "Europe",        "europe"),
    ("Lithuania",   "Vilnius",      "Europe",        "europe"),
    ("Malaysia",    "Kuala Lumpur", "Asia",          "asia"),
    ("Mexico",      "Mexico City",  "Latin America", "latin_america"),
    ("Morocco",     "Rabat",        "Africa",        "africa"),
    ("Netherlands", "Amsterdam",    "Europe",        "europe"),
    ("New Zealand", "Wellington",   "Asia Pacific",  "asia"),
    ("Nigeria",     "Abuja",        "Africa",        "africa"),
    ("Norway",      "Oslo",         "Europe",        "europe"),
    ("Pakistan",    "Islamabad",    "Asia",          "asia"),
    ("Peru",        "Lima",         "Latin America", "latin_america"),
    ("Philippines", "Manila",       "Asia",          "asia"),
    ("Poland",      "Warsaw",       "Europe",        "europe"),
    ("Portugal",    "Lisbon",       "Europe",        "europe"),
    ("Romania",     "Bucharest",    "Europe",        "europe"),
    ("Senegal",     "Dakar",        "Africa",        "africa"),
    ("Singapore",   "Singapore",    "Asia",          "asia"),
    ("Slovakia",    "Bratislava",   "Europe",        "europe"),
    ("South Korea", "Seoul",        "Asia",          "asia"),
    ("Spain",       "Madrid",       "Europe",        "europe"),
    ("Sweden",      "Stockholm",    "Europe",        "europe"),
    ("Switzerland", "Bern",         "Europe",        "europe"),
    ("Thailand",    "Bangkok",      "Asia",          "asia"),
    ("Tunisia",     "Tunis",        "Africa",        "africa"),
    ("Turkey",      "Ankara",       "Europe",        "europe"),
    ("Vietnam",     "Hanoi",        "Asia",          "asia"),
]

R6_COUNTRY_ANGLES: list[tuple[str, str]] = [
    ("{country}: parliament debates the year's biggest policy shift",
     "Lawmakers in {capital} returned to a packed agenda. Our correspondent walks through the four most contested clauses."),
    ("{country} central bank holds rate as inflation drift slows",
     "The decision was widely expected. The accompanying statement was not — analysts dissected three subtle changes in language."),
    ("Inside {capital}: the planning fight reshaping the city",
     "A multi-block redevelopment is dividing residents. We visited five different streets and three planning meetings."),
    ("{country} health service publishes annual review",
     "The report tracks 14 indicators. Five improved year-on-year; two worsened. The remaining seven held steady."),
    ("Reaction from {capital} to the regional security summit",
     "Officials in {country} struck a careful tone. Civil society groups were less restrained."),
    ("{country}: a week in education policy",
     "Three announcements, two consultations and a leaked memo. We piece together what they mean for schools."),
    ("{capital} climate plan: who pays, and when",
     "The funding mix is unusual: a third national, a third municipal, a third private. We map the moving parts."),
    ("Court ruling in {country} reshapes employment law",
     "A long-running case ended with a unanimous decision. Employers and unions both claimed elements of victory."),
    ("{country} elections: latest polling, with context",
     "Our team looked at five reputable pollsters. Their averages agree on the direction; their spreads tell a richer story."),
    ("{capital} transport: the new ticketing scheme, explained",
     "A short reader-friendly guide to the rollout. Common questions answered; common complaints noted."),
    ("Voices from {country}: a year on, what changed?",
     "We returned to ten readers we first interviewed twelve months ago. Their updates form this long-read."),
    ("{country} business briefing: results week round-up",
     "Five major listings reported this week. Three beat expectations; two issued cautious guidance."),
]


def synth_r6_country_drill(con, hero_pool: list[str]) -> list[dict]:
    base = MIRROR_REFERENCE_DATE
    out: list[dict] = []
    for ci, (country, capital, region_label, section_slug) in enumerate(R6_COUNTRIES):
        cid = _r6_cat_id(con, section_slug) or _r6_cat_id(con, "world") or 1
        for ai, (hl_pat, lead_pat) in enumerate(R6_COUNTRY_ANGLES):
            headline = hl_pat.format(country=country, capital=capital)
            lead = lead_pat.format(country=country, capital=capital)
            slug = _det_slug("r6-ctry", f"{country}|{ai}")
            hero = hero_pool[(_det_int(slug) + 23 + ci) % len(hero_pool)] if hero_pool else ""
            ts = base - timedelta(
                days=(ci * 3 + ai * 5) % 200 + 1,
                hours=(_det_int(slug) // 11) % 24,
            )
            body = _r6_synth_body(lead, country, capital)
            topics = [country, capital, region_label]
            feature_tags = ["country-drill", country.lower().replace(" ", "-"),
                            region_label.lower().replace(" ", "-").replace("&", "and")]
            out.append(_r6_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug=section_slug,
                subsection=country, region_label=region_label, ts=ts,
                view_count=300 + (_det_int(slug) % 15000),
                country=country, hero=hero,
                topics=topics, feature_tags=feature_tags,
            ))
    return out


# ---- R6 long-running stories — 30 arcs × 25 updates = 750 --------------

R6_LONGRUN_ARCS: list[tuple[str, str, str, str]] = [
    # (arc_slug, headline_root, region_label, section_slug)
    ("nairobi-floods-2026",      "Nairobi floods recovery",              "Africa",        "africa"),
    ("manila-typhoon-2026",      "Manila typhoon response",              "Asia",          "asia"),
    ("athens-wildfires-2026",    "Greece wildfire watch",                "Europe",        "europe"),
    ("lima-protests-2026",       "Peru's political crisis",              "Latin America", "latin_america"),
    ("delhi-air-quality-2026",   "Delhi air-quality emergency",          "Asia",          "asia"),
    ("dublin-housing-bill-2026", "Dublin housing bill in committee",     "Europe",        "europe"),
    ("nashville-storm-2026",     "Tennessee storm clean-up",             "US & Canada",   "us_canada"),
    ("dakar-elections-2026",     "Senegal presidential election",        "Africa",        "africa"),
    ("istanbul-quake-2026",      "Aegean earthquake recovery",           "Europe",        "europe"),
    ("seoul-strike-2026",        "South Korea transport strike",         "Asia",          "asia"),
    ("london-budget-2026",       "London budget consultation",           "UK",            "uk"),
    ("rio-favela-program-2026",  "Rio housing programme rollout",        "Latin America", "latin_america"),
    ("madrid-rail-strike-2026",  "Spain rail dispute",                   "Europe",        "europe"),
    ("nyc-subway-plan-2026",     "New York subway plan",                 "US & Canada",   "us_canada"),
    ("tunis-water-2026",         "Tunisia water rationing",              "Africa",        "africa"),
    ("warsaw-court-2026",        "Poland constitutional case",           "Europe",        "europe"),
    ("brasilia-amazon-2026",     "Amazon legislation in Brasilia",       "Latin America", "latin_america"),
    ("kuala-lumpur-floods-2026", "Malaysia monsoon floods",              "Asia",          "asia"),
    ("kigali-summit-2026",       "African Union summit",                 "Africa",        "africa"),
    ("oslo-arctic-2026",         "Norway Arctic deployment",             "Europe",        "europe"),
    ("mumbai-monorail-2026",     "Mumbai monorail expansion",            "Asia",          "asia"),
    ("manchester-tram-2026",     "Manchester tram extension",            "UK",            "uk"),
    ("cardiff-language-2026",    "Welsh language bill",                  "UK",            "wales"),
    ("edinburgh-budget-2026",    "Holyrood budget timeline",             "UK",            "scotland"),
    ("belfast-power-2026",       "Northern Ireland power-sharing",       "UK",            "northern_ireland"),
    ("singapore-housing-2026",   "Singapore HDB review",                 "Asia",          "asia"),
    ("addis-rail-2026",          "Ethiopia rail expansion",              "Africa",        "africa"),
    ("johannesburg-water-2026",  "Johannesburg water crisis",            "Africa",        "africa"),
    ("buenos-aires-strike-2026", "Buenos Aires general strike",          "Latin America", "latin_america"),
    ("hanoi-floods-2026",        "Hanoi flood defences",                 "Asia",          "asia"),
]


def synth_r6_long_running(con, hero_pool: list[str]) -> list[dict]:
    """For each arc: 1 parent live-blog summary + 24 chronological updates =
    25 articles. Updates are linked back via slug prefix matching."""
    base = MIRROR_REFERENCE_DATE
    out: list[dict] = []
    for arc_idx, (arc_slug, root, region_label, section_slug) in enumerate(R6_LONGRUN_ARCS):
        cid = _r6_cat_id(con, section_slug) or _r6_cat_id(con, "live_updates") or 1
        # Parent live-blog summary (after the arc concludes).
        parent_slug = _det_slug("r6-arc", arc_slug)
        parent_ts = base - timedelta(days=(arc_idx * 5) % 100 + 2)
        parent_headline = f"{root}: live updates and full summary"
        parent_lead = (f"Three days of fast-moving coverage in one place. "
                       f"Read our chronological log, or jump to the summary "
                       f"now that the situation has stabilised.")
        parent_body = _r6_synth_body(parent_lead, region_label, root)
        out.append(_r6_make_row(
            slug=parent_slug, headline=parent_headline, lead=parent_lead,
            body=parent_body, category_id=cid, section_slug=section_slug,
            subsection=root, region_label=region_label, ts=parent_ts,
            view_count=5000 + (_det_int(parent_slug) % 50000),
            country=region_label, hero=hero_pool[arc_idx % len(hero_pool)] if hero_pool else "",
            topics=[root, region_label, "Live updates"],
            feature_tags=["long-running-arc", "live-blog-parent", "r6-live-ended",
                          arc_slug],
            content_type="live", is_live=1, is_featured=1 if arc_idx % 4 == 0 else 0,
        ))

        # 24 updates spanning ~3 days (8 per day).
        for ui in range(24):
            slug = _det_slug("r6-arc-u", f"{arc_slug}|{ui:02d}")
            day = ui // 8 + 1
            hour = (ui % 8) * 3 + 1
            ts = parent_ts - timedelta(days=(3 - day), hours=24 - hour,
                                       minutes=(_det_int(slug) // 5) % 60)
            update_label = f"Day {day} update {ui % 8 + 1}"
            headline = f"{root}: {update_label}"
            lead = (f"Latest from our team on the ground: a quick "
                    f"chronological update from {region_label}.")
            body = _r6_synth_body(lead, region_label, root)
            out.append(_r6_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug=section_slug,
                subsection=root, region_label=region_label, ts=ts,
                view_count=200 + (_det_int(slug) % 8000),
                country=region_label,
                hero=hero_pool[(arc_idx * 31 + ui) % len(hero_pool)] if hero_pool else "",
                topics=[root, region_label, "Live updates", update_label],
                feature_tags=["long-running-arc", "live-update", arc_slug,
                              f"day-{day}"],
                content_type="live_update",
            ))
    return out


# ---- R6 topic explainers (40 hot topics × 12 explainers = 480) ---------

R6_HOT_TOPICS: list[tuple[str, str]] = [
    ("artificial-intelligence", "Artificial intelligence"),
    ("climate-change",          "Climate change"),
    ("cost-of-living",          "Cost of living"),
    ("electric-vehicles",       "Electric vehicles"),
    ("food-security",           "Food security"),
    ("global-supply-chains",    "Global supply chains"),
    ("housing-affordability",   "Housing affordability"),
    ("immigration-policy",      "Immigration policy"),
    ("interest-rates",          "Interest rates"),
    ("mental-health",           "Mental health"),
    ("nato",                    "NATO and security"),
    ("offshore-wind",           "Offshore wind"),
    ("public-transport",        "Public transport"),
    ("quantum-computing",       "Quantum computing"),
    ("renewable-energy",        "Renewable energy"),
    ("space-launches",          "Space launches"),
    ("trade-tariffs",           "Trade tariffs"),
    ("urban-air-quality",       "Urban air quality"),
    ("vaccine-rollouts",        "Vaccine rollouts"),
    ("water-scarcity",          "Water scarcity"),
    ("xi-jinping-era",          "China leadership"),
    ("youth-employment",        "Youth employment"),
    ("zero-carbon-cities",      "Zero-carbon cities"),
    ("aviation-emissions",      "Aviation emissions"),
    ("biotech-investing",       "Biotech investing"),
    ("crypto-regulation",       "Crypto regulation"),
    ("digital-id",              "Digital ID"),
    ("election-disinformation", "Election disinformation"),
    ("flood-defence",           "Flood defence"),
    ("green-skills",            "Green skills"),
    ("higher-education",        "Higher education"),
    ("industrial-policy",       "Industrial policy"),
    ("journalism-safety",       "Journalism safety"),
    ("kindergarten-funding",    "Early years funding"),
    ("local-news",              "Local news ecosystem"),
    ("museum-funding",          "Museum funding"),
    ("northern-rail",           "Northern rail"),
    ("ocean-plastics",          "Ocean plastics"),
    ("pension-reform",          "Pension reform"),
    ("rare-earth-mining",       "Rare-earth mining"),
]

R6_EXPLAINER_FORMS: list[tuple[str, str]] = [
    ("Explained: how {label} works in 2026",
     "A clear, jargon-light primer for readers catching up on {label}."),
    ("Five charts: the state of {label}, briefly",
     "Five concise visuals that capture where {label} stands and how it shifted this quarter."),
    ("Q&A: your questions on {label}, answered",
     "We collected the most-asked reader questions on {label} and put them to our specialist correspondent."),
    ("Watch: a six-minute primer on {label}",
     "Our explainer video walks viewers through the moving parts. Closed captions and a full transcript are linked."),
    ("Long read: the year in {label}",
     "Twelve months of coverage, pulled together. What changed, what stalled, and what readers told us mattered most."),
    ("Verify: four claims about {label} fact-checked",
     "We checked widely-shared claims about {label}. Two stood up; two did not. Working shown."),
    ("Voices: readers on how {label} touches their week",
     "First-person accounts from across the UK and beyond. Lightly edited for clarity."),
    ("Numbers behind the story: {label}, charted",
     "We break down the latest official statistics around {label}. The trend has shifted; the drivers have not."),
    ("Opinion: a specialist on the next phase of {label}",
     "A guest contribution from a researcher who has tracked {label} for fifteen years."),
    ("Analysis: how the {label} debate is playing out worldwide",
     "Beyond the press releases, the real argument is being made in town halls and trading floors."),
    ("In pictures: a global day on {label}",
     "A photo essay following our reporting team across three continents for one day."),
    ("Live discussion: experts on {label}",
     "A consolidated summary of yesterday's live blog hosted by the BBC News specialist desk."),
]


def synth_r6_topic_explainers(con, hero_pool: list[str]) -> list[dict]:
    base = MIRROR_REFERENCE_DATE
    out: list[dict] = []
    for ti, (tag, label) in enumerate(R6_HOT_TOPICS):
        # Map topic to a sensible category bucket.
        sec_map = {
            "interest-rates": "business", "trade-tariffs": "business",
            "biotech-investing": "business", "industrial-policy": "business",
            "crypto-regulation": "business", "pension-reform": "business",
            "rare-earth-mining": "business",
            "artificial-intelligence": "technology", "quantum-computing": "technology",
            "digital-id": "technology", "election-disinformation": "technology",
            "climate-change": "science", "offshore-wind": "science",
            "renewable-energy": "science", "ocean-plastics": "science",
            "flood-defence": "science", "aviation-emissions": "science",
            "zero-carbon-cities": "science", "water-scarcity": "science",
            "urban-air-quality": "health", "mental-health": "health",
            "vaccine-rollouts": "health", "food-security": "health",
            "nato": "world", "immigration-policy": "world",
            "xi-jinping-era": "asia",
            "youth-employment": "uk", "housing-affordability": "uk",
            "cost-of-living": "uk", "higher-education": "uk",
            "kindergarten-funding": "uk", "local-news": "uk",
            "northern-rail": "uk", "museum-funding": "uk",
            "green-skills": "uk", "journalism-safety": "uk",
            "public-transport": "uk", "electric-vehicles": "business",
            "global-supply-chains": "business", "space-launches": "science",
        }
        section_slug = sec_map.get(tag, "news")
        cid = _r6_cat_id(con, section_slug) or _r6_cat_id(con, "news") or 1
        for fi, (hl_pat, lead_pat) in enumerate(R6_EXPLAINER_FORMS):
            headline = hl_pat.format(label=label)
            lead = lead_pat.format(label=label)
            slug = _det_slug("r6-topic", f"{tag}|{fi}")
            hero = hero_pool[(_det_int(slug) + 19 + ti) % len(hero_pool)] if hero_pool else ""
            ts = base - timedelta(
                days=(ti * 4 + fi * 3) % 220 + 1,
                hours=(_det_int(slug) // 9) % 24,
            )
            body = _r6_synth_body(lead, "the United Kingdom", label)
            topics = [label, tag.replace("-", " ").title(), "Explainer"]
            feature_tags = ["topic-explainer", tag, section_slug]
            out.append(_r6_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug=section_slug,
                subsection=label, region_label="Global", ts=ts,
                view_count=500 + (_det_int(slug) % 22000),
                country="Global", hero=hero,
                topics=topics, feature_tags=feature_tags,
                content_type="article",
            ))
    return out


# ---- R6 edge-case articles (6 statuses × 12 articles = 72) -------------

R6_EDGE_CASES: list[tuple[str, str, str, str]] = [
    # (status_tag, banner_label, headline_pat, lead_pat)
    ("r6-removed-legal",
     "This article has been removed for legal reasons",
     "Court ruling: {topic} report withdrawn",
     "The original report on {topic} has been removed following a legal order. We are unable to republish until the case concludes."),
    ("r6-region-blocked",
     "This video is not available in your region",
     "Watch: {topic} — restricted in some regions",
     "Due to broadcast rights, the embedded video about {topic} is not available in your region. A full transcript is provided below."),
    ("r6-live-ended",
     "This live blog has ended. Read our summary.",
     "{topic}: live blog ended — full summary inside",
     "Our live coverage of {topic} concluded this morning. We have consolidated the key updates into the summary below."),
    ("r6-superseded",
     "An updated version of this story is available.",
     "{topic}: updated reporting now available",
     "This story has been superseded by newer reporting on {topic}. The updated piece supersedes this version."),
    ("r6-comments-locked",
     "Comments are closed on this story.",
     "{topic}: comments closed after sustained moderation",
     "Following high-volume discussion, the comments thread for this {topic} story has been locked. Earlier comments remain visible."),
    ("r6-user-blocked",
     "You have been blocked from commenting on this story.",
     "{topic}: moderation note for some readers",
     "A small number of readers have been blocked from commenting after repeated violations of our house rules on {topic} coverage."),
]


def synth_r6_edge_cases(con, hero_pool: list[str]) -> list[dict]:
    base = MIRROR_REFERENCE_DATE
    topics = [
        "high-profile defamation case", "court injunction ruling",
        "ongoing inquest", "data breach investigation",
        "minor identification ruling", "named-person publication order",
        "Premier League rights dispute", "Olympics broadcast embargo",
        "Eurovision regional restriction", "iPlayer-only documentary",
        "regional sport blackout", "studio-recorded interview embargo",
    ]
    out: list[dict] = []
    for si, (status_tag, _banner, hl_pat, lead_pat) in enumerate(R6_EDGE_CASES):
        section_slug = "news"
        cid = _r6_cat_id(con, section_slug) or 1
        # 12 articles per edge case, each tied to one topic.
        for ti, topic in enumerate(topics):
            headline = hl_pat.format(topic=topic)
            lead = lead_pat.format(topic=topic)
            slug = _det_slug("r6-edge", f"{status_tag}|{ti}")
            hero = hero_pool[(_det_int(slug) + si * 5 + ti) % len(hero_pool)] if hero_pool else ""
            ts = base - timedelta(days=(si * 7 + ti) % 60 + 1,
                                  hours=(_det_int(slug) // 5) % 24)
            body = _r6_synth_body(lead, "the United Kingdom", topic)
            content_type = ("video" if status_tag == "r6-region-blocked"
                            else "live" if status_tag == "r6-live-ended"
                            else "article")
            video_url = ("https://www.bbc.com/video/restricted"
                         if status_tag == "r6-region-blocked" else "")
            out.append(_r6_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug=section_slug,
                subsection="Editorial note", region_label="UK", ts=ts,
                view_count=100 + (_det_int(slug) % 5000),
                country="UK", hero=hero,
                topics=[topic, "Editorial note", status_tag],
                feature_tags=["edge-case", status_tag, topic.lower().replace(" ", "-")],
                content_type=content_type, video_url=video_url,
                is_live=1 if status_tag == "r6-live-ended" else 0,
            ))
    return out


# ---- R6 tag anchor articles (40 named tags × 8 = 320 articles) ---------
# These exist mainly so /topic/<tag> tag pages return rich results.

R6_TAGS: list[tuple[str, str]] = [
    ("Westminster", "politics"),       ("Holyrood", "scotland"),
    ("Senedd", "wales"),                ("Stormont", "northern_ireland"),
    ("White House", "us_canada"),       ("Wall Street", "business"),
    ("Silicon Valley", "technology"),   ("European Parliament", "europe"),
    ("United Nations", "world"),        ("World Bank", "business"),
    ("IMF", "business"),                ("WHO", "health"),
    ("WTO", "business"),                ("OPEC", "business"),
    ("ECB", "business"),                ("Bank of England", "business"),
    ("Federal Reserve", "business"),    ("Bundesbank", "business"),
    ("Pentagon", "us_canada"),          ("Kremlin", "europe"),
    ("African Union", "africa"),        ("ASEAN", "asia"),
    ("G7", "world"),                    ("G20", "world"),
    ("COP29", "science"),               ("COP30", "science"),
    ("Premier League", "football"),     ("Champions League", "football"),
    ("World Cup", "football"),          ("Wimbledon", "tennis"),
    ("Open Championship", "golf"),      ("Ashes Test", "cricket"),
    ("Six Nations", "rugby"),           ("Olympics 2028", "sport"),
    ("Glastonbury", "music"),           ("Cannes Film Festival", "film"),
    ("BAFTA Awards", "film"),           ("Booker Prize", "books"),
    ("Royal Shakespeare", "art_design"),("Edinburgh Festival", "art_design"),
]

R6_TAG_ANGLES: list[tuple[str, str]] = [
    ("{tag}: this week's developments",
     "What happened, what it means, and which voices to listen to as the {tag} story continues."),
    ("{tag} explained: a reader's primer",
     "A short primer for readers new to the {tag} story. Five take-aways from our recent reporting."),
    ("{tag}: five questions our reporters keep getting",
     "Reader questions answered by the BBC team covering {tag}."),
    ("Voices around {tag}: how the conversation has changed",
     "We tracked language and sentiment around {tag} over the last quarter. The shift surprised some seasoned observers."),
    ("Long read: a year of {tag} reporting",
     "Twelve months of BBC coverage, pulled together. The patterns now look clearer than at the time."),
    ("Numbers behind {tag}, charted",
     "We break down the latest published numbers around {tag}."),
    ("Verify: four claims about {tag} fact-checked",
     "BBC Verify checked widely-shared claims related to {tag}. Working shown."),
    ("Watch: a six-minute briefing on {tag}",
     "Our explainer video walks viewers through the {tag} story so far."),
]


def synth_r6_tag_anchors(con, hero_pool: list[str]) -> list[dict]:
    base = MIRROR_REFERENCE_DATE
    out: list[dict] = []
    for ti, (tag, section_slug) in enumerate(R6_TAGS):
        cid = _r6_cat_id(con, section_slug) or _r6_cat_id(con, "news") or 1
        for ai, (hl_pat, lead_pat) in enumerate(R6_TAG_ANGLES):
            headline = hl_pat.format(tag=tag)
            lead = lead_pat.format(tag=tag)
            slug = _det_slug("r6-tag", f"{tag}|{ai}")
            hero = hero_pool[(_det_int(slug) + 37 + ti) % len(hero_pool)] if hero_pool else ""
            ts = base - timedelta(days=(ti * 6 + ai * 2) % 240 + 1,
                                  hours=(_det_int(slug) // 13) % 24)
            body = _r6_synth_body(lead, tag, section_slug)
            tag_slug = tag.lower().replace(" ", "-")
            out.append(_r6_make_row(
                slug=slug, headline=headline, lead=lead, body=body,
                category_id=cid, section_slug=section_slug,
                subsection=tag, region_label=tag, ts=ts,
                view_count=400 + (_det_int(slug) % 20000),
                country=tag, hero=hero,
                topics=[tag, section_slug.title()],
                feature_tags=["tag-anchor", tag_slug, section_slug],
                is_featured=1 if (ti + ai) % 9 == 0 else 0,
            ))
    return out


# ---- R6 article insert ------------------------------------------------

def insert_r6_articles(con: sqlite3.Connection, batch: list[dict]) -> int:
    cur = con.cursor()
    existing = {r[0] for r in cur.execute("SELECT slug FROM articles")}
    rows = [a for a in batch if a["slug"] not in existing]
    if not rows:
        return 0
    cur.executemany(_ART_INSERT_SQL, rows)
    return len(rows)


# ---- R6 supplementary inserts (comments / RH / bookmarks / etc.) -------

R6_COMMENT_TOP: list[str] = [
    "The 'More from this reporter' block is a great addition.",
    "Followed the byline to find three more pieces — exactly what I wanted.",
    "Long-running arcs with the day-by-day jump are far more readable.",
    "The country drill pages give a useful base before the headline news.",
    "Glad to see the editorial banner explaining why this video is restricted.",
    "Comment lock was needed; thread had drifted off topic.",
    "Top story today sidebar is a smart navigation aid.",
    "Tag pages are now actually populated — useful for casual readers.",
    "Reporter beats make the bylines feel meaningful again.",
    "Multi-day summary links from the parent live blog are well executed.",
]

R6_COMMENT_REPLIES: list[str] = [
    "Same — the related-topics chips finally lead somewhere rich.",
    "Agreed. Day-by-day jump is a substantial improvement.",
    "Found the followup via the byline links too. Nice work, BBC.",
    "Top story today is now my landing point each morning.",
    "Country drill saved me when prepping for a meeting on this region.",
]


def insert_r6_comments(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if len(user_ids) < 2:
        return 0

    pool: list[tuple[int, str]] = []
    for tag in ("reporter-series", "long-running-arc", "topic-explainer",
                "country-drill", "tag-anchor"):
        rows = cur.execute(
            "SELECT id, headline FROM articles "
            "WHERE feature_tags LIKE ? ORDER BY view_count DESC LIMIT 40",
            (f'%\"{tag}\"%',),
        ).fetchall()
        pool.extend(rows)
    seen: set[int] = set()
    pool = [t for t in pool if not (t[0] in seen or seen.add(t[0]))][:180]

    base_ts = MIRROR_REFERENCE_DATE
    top_rows: list[tuple] = []
    for idx, (art_id, _hl) in enumerate(pool):
        n_top = 2 + (idx % 3)
        for j in range(n_top):
            uid = user_ids[(idx * 7 + j * 5) % len(user_ids)]
            body = R6_COMMENT_TOP[(idx * 5 + j * 3) % len(R6_COMMENT_TOP)]
            offset_h = (idx * 11 + j * 19) % (24 * 28)
            ts = base_ts - timedelta(hours=offset_h, minutes=(j + idx * 7) % 60)
            like = (idx * j + 5) % 30
            top_rows.append((uid, art_id, None, body, like, 0,
                             ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        top_rows,
    )
    inserted = len(top_rows)

    # Replies (depth 2) on every 5th top-level comment
    fresh = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL ORDER BY id DESC LIMIT ?",
        (inserted,),
    ))
    fresh.reverse()
    extra = 0
    for i, (cid, art_id, parent_uid, parent_created) in enumerate(fresh):
        if i % 5 != 0:
            continue
        cur_parent = cid
        cur_parent_uid = parent_uid
        ts_parent = datetime.strptime(parent_created, "%Y-%m-%d %H:%M:%S")
        for depth in range(1, 3):
            ruid = user_ids[(cur_parent_uid + depth + i + 1) % len(user_ids)]
            if ruid == cur_parent_uid:
                ruid = user_ids[(cur_parent_uid + depth + i + 2) % len(user_ids)]
            body = R6_COMMENT_REPLIES[(i * 5 + depth * 3) % len(R6_COMMENT_REPLIES)]
            ts_parent = ts_parent + timedelta(hours=depth + 1,
                                              minutes=(depth * 11) % 60)
            cur.execute(
                "INSERT INTO comments (user_id, article_id, parent_id, body, "
                "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ruid, art_id, cur_parent, body, (depth * 5 + i) % 20, 0,
                 ts_parent.strftime("%Y-%m-%d %H:%M:%S")),
            )
            cur_parent = cur.lastrowid
            cur_parent_uid = ruid
            extra += 1
    return inserted + extra


def insert_r6_reading_history(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not user_ids:
        return 0

    # Pull a curated slice: the most-read article per reporter beat,
    # plus the parent live-blog of each arc. Gives 'More from this reporter'
    # and 'follow-the-arc' tasks a populated history surface.
    art_ids: list[int] = []
    for tag in ("reporter-series", "long-running-arc", "topic-explainer",
                "tag-anchor", "country-drill"):
        rows = cur.execute(
            "SELECT id FROM articles WHERE feature_tags LIKE ? "
            "ORDER BY view_count DESC LIMIT 50",
            (f'%\"{tag}\"%',),
        ).fetchall()
        art_ids.extend(r[0] for r in rows)
    art_ids = list(dict.fromkeys(art_ids))[:200]

    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    for idx, art_id in enumerate(art_ids):
        for ui, uid in enumerate(user_ids):
            if (idx + ui) % 3 != 0:
                continue
            ts = base_ts - timedelta(days=(idx + ui * 3) % 35,
                                     hours=(idx * 5 + ui * 7) % 24)
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    if not rows:
        return 0
    cur.executemany(
        "INSERT INTO reading_history (user_id, article_id, viewed_at) "
        "VALUES (?, ?, ?)", rows,
    )
    return len(rows)


def insert_r6_bookmarks(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not user_ids:
        return 0
    art_ids = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE ? "
        "ORDER BY view_count DESC LIMIT 90", ('%"reporter-series"%',),
    )]
    base_ts = MIRROR_REFERENCE_DATE
    seen = set(cur.execute(
        "SELECT user_id, article_id FROM bookmarks").fetchall())
    rows = []
    for idx, art_id in enumerate(art_ids):
        uid = user_ids[idx % len(user_ids)]
        if (uid, art_id) in seen:
            continue
        ts = base_ts - timedelta(days=(idx % 40) + 1, hours=idx % 24)
        rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))
    if not rows:
        return 0
    cur.executemany(
        "INSERT INTO bookmarks (user_id, article_id, bookmarked_at) "
        "VALUES (?, ?, ?)", rows,
    )
    return len(rows)


def insert_r6_subscriptions(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not user_ids:
        return 0
    # Subscribe each user to a handful of reporter beats + topic tags.
    beats = [b[1] for b in R6_REPORTERS]
    topics = [t[0] for t in R6_HOT_TOPICS]
    seen = set(cur.execute(
        "SELECT user_id, topic FROM topic_subscriptions").fetchall())
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    for ui, uid in enumerate(user_ids):
        for offset in range(8):
            beat = beats[(ui * 5 + offset) % len(beats)]
            if (uid, beat) not in seen:
                ts = base_ts - timedelta(days=(ui * 3 + offset) % 60 + 1)
                rows.append((uid, beat, ts.strftime("%Y-%m-%d %H:%M:%S"), 1))
                seen.add((uid, beat))
        for offset in range(6):
            topic = topics[(ui * 7 + offset) % len(topics)]
            if (uid, topic) not in seen:
                ts = base_ts - timedelta(days=(ui * 4 + offset) % 70 + 1)
                rows.append((uid, topic, ts.strftime("%Y-%m-%d %H:%M:%S"), 1))
                seen.add((uid, topic))
    if not rows:
        return 0
    # topic_subscriptions schema differs across sites; introspect columns.
    cols = [r[1] for r in cur.execute("PRAGMA table_info(topic_subscriptions)")]
    if "is_active" in cols or "active" in cols:
        active_col = "is_active" if "is_active" in cols else "active"
        cur.executemany(
            f"INSERT INTO topic_subscriptions (user_id, topic, created_at, "
            f"{active_col}) VALUES (?, ?, ?, ?)",
            rows,
        )
    else:
        cur.executemany(
            "INSERT INTO topic_subscriptions (user_id, topic, created_at) "
            "VALUES (?, ?, ?)",
            [(r[0], r[1], r[2]) for r in rows],
        )
    return len(rows)


def insert_r6_reading_list(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        return 0
    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    if not user_ids:
        return 0

    art_ids = [r[0] for r in cur.execute(
        "SELECT id FROM articles WHERE feature_tags LIKE ? "
        "ORDER BY view_count DESC LIMIT 60", ('%"long-running-arc"%',),
    )]
    seen = set(cur.execute(
        "SELECT user_id, article_id FROM reading_list_items").fetchall())
    cols = [r[1] for r in cur.execute("PRAGMA table_info(reading_list_items)")]
    base_ts = MIRROR_REFERENCE_DATE
    rows = []
    folders = ["Follow this arc", "Read this weekend", "Read Later"]
    for idx, art_id in enumerate(art_ids):
        uid = user_ids[idx % len(user_ids)]
        if (uid, art_id) in seen:
            continue
        folder = folders[idx % len(folders)]
        ts = base_ts - timedelta(days=(idx % 28) + 1,
                                 hours=(idx * 13) % 24)
        row = {"user_id": uid, "article_id": art_id,
               "folder": folder, "added_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
               "read": 1 if idx % 7 == 0 else 0}
        rows.append(row)
    if not rows:
        return 0
    insert_cols = [c for c in
                   ("user_id", "article_id", "folder", "added_at", "read")
                   if c in cols]
    placeholders = ", ".join(":" + c for c in insert_cols)
    cur.executemany(
        f"INSERT INTO reading_list_items ({', '.join(insert_cols)}) "
        f"VALUES ({placeholders})",
        [{c: r[c] for c in insert_cols} for r in rows],
    )
    return len(rows)


def plant_r6_sentinel(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    if cur.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        return
    uid_row = cur.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    art_row = cur.execute("SELECT id FROM articles WHERE feature_tags LIKE ? "
                          "ORDER BY id LIMIT 1",
                          ('%"reporter-series"%',)).fetchone()
    if not (uid_row and art_row):
        return
    cur.execute(
        "INSERT INTO comments (user_id, article_id, parent_id, body, "
        "like_count, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid_row[0], art_row[0], None, R6_SENTINEL_BODY, 0, 1,
         MIRROR_REFERENCE_DATE.strftime("%Y-%m-%d %H:%M:%S")),
    )


def bake_r6(con: sqlite3.Connection) -> dict[str, int]:
    """Apply all R6 additions. Idempotent (sentinel-gated)."""
    stats: dict[str, int] = {}
    if con.execute(
        "SELECT 1 FROM comments WHERE body=? LIMIT 1", (R6_SENTINEL_BODY,)
    ).fetchone():
        stats["already_baked"] = 1
        return stats

    hero_pool = _hero_image_pool(con)
    if not hero_pool:
        hero_pool = [""]

    batches: list[list[dict]] = [
        synth_r6_reporter_beats(con, hero_pool),
        synth_r6_country_drill(con, hero_pool),
        synth_r6_long_running(con, hero_pool),
        synth_r6_topic_explainers(con, hero_pool),
        synth_r6_tag_anchors(con, hero_pool),
        synth_r6_edge_cases(con, hero_pool),
    ]
    total = 0
    for batch in batches:
        total += insert_r6_articles(con, batch)
    stats["new_articles"] = total

    stats["new_comments"] = insert_r6_comments(con)
    stats["new_reading_history"] = insert_r6_reading_history(con)
    stats["new_bookmarks"] = insert_r6_bookmarks(con)
    stats["new_subscriptions"] = insert_r6_subscriptions(con)
    stats["new_reading_list"] = insert_r6_reading_list(con)

    plant_r6_sentinel(con)
    return stats


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")
    print(f"[bake] DB: {DB_PATH}")
    print(f"[bake] md5 before: {_db_signature(DB_PATH)}")

    rss_articles = collect_rss_articles()
    print(f"[bake] parsed {len(rss_articles)} unique RSS articles")

    con = open_db(DB_PATH)
    try:
        ensure_gallery_full_column(con)
        n_art = insert_new_articles(con, rss_articles)
        n_cm = insert_comments(con)
        n_rh = insert_reading_history(con)
        n_bm = insert_extra_bookmarks(con)
        n_rl = insert_extra_reading_list(con)
        n_ts = insert_extra_subscriptions(con)
        plant_sentinel(con)
        r3_stats = bake_r3(con)
        r4_stats = bake_r4(con)
        r5_stats = bake_r5(con)
        r6_stats = bake_r6(con)
        normalize_sqlite_sequence(con)
        con.commit()
    finally:
        con.close()

    # VACUUM on a separate connection to clean page layout.
    # Skip VACUUM when nothing was inserted — repeated VACUUM updates the
    # SQLite header (file-change counter at bytes 24-27 and version-valid-for
    # at bytes 92-95) which would shift the md5 even when content is
    # bit-identical. Idempotent re-runs must produce the same DB bytes.
    r3_total_inserts = sum(
        v for k, v in r3_stats.items()
        if isinstance(v, int) and k not in ("already_baked",)
    )
    r4_total_inserts = sum(
        v for k, v in r4_stats.items()
        if isinstance(v, int) and k not in ("already_baked",)
    )
    r5_total_inserts = sum(
        v for k, v in r5_stats.items()
        if isinstance(v, int) and k not in ("already_baked",)
    )
    r6_total_inserts = sum(
        v for k, v in r6_stats.items()
        if isinstance(v, int) and k not in ("already_baked",)
    )
    r2_total_inserts = n_art + n_cm + n_rh + n_bm + n_rl + n_ts
    if r2_total_inserts + r3_total_inserts + r4_total_inserts + r5_total_inserts + r6_total_inserts > 0:
        con = open_db(DB_PATH)
        try:
            con.execute("VACUUM")
            con.commit()
        finally:
            con.close()
        print("[bake] VACUUMed (had inserts)")
    else:
        print("[bake] no inserts — skipping VACUUM to preserve md5")

    print(f"[bake] inserted: +{n_art} articles, +{n_cm} comments, "
          f"+{n_rh} reading_history, +{n_bm} bookmarks, +{n_rl} reading_list, "
          f"+{n_ts} subscriptions")
    print(f"[bake] R3 stats: {r3_stats}")
    print(f"[bake] R4 stats: {r4_stats}")
    print(f"[bake] R5 stats: {r5_stats}")
    print(f"[bake] R6 stats: {r6_stats}")
    print(f"[bake] md5 after:  {_db_signature(DB_PATH)}")

    con = open_db(DB_PATH)
    try:
        for table in ("users", "categories", "articles", "comments",
                      "reading_history", "bookmarks", "reading_list_items",
                      "digests", "digest_items", "topic_subscriptions"):
            n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
