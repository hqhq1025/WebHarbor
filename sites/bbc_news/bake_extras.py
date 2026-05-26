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
    r2_total_inserts = n_art + n_cm + n_rh + n_bm + n_rl + n_ts
    if r2_total_inserts + r3_total_inserts > 0:
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
