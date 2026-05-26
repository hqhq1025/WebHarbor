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
        normalize_sqlite_sequence(con)
        con.commit()
    finally:
        con.close()

    # VACUUM on a separate connection to clean page layout
    con = open_db(DB_PATH)
    try:
        con.execute("VACUUM")
        con.commit()
    finally:
        con.close()

    print(f"[bake] inserted: +{n_art} articles, +{n_cm} comments, "
          f"+{n_rh} reading_history, +{n_bm} bookmarks, +{n_rl} reading_list, "
          f"+{n_ts} subscriptions")
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
