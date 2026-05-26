"""
One-off baker: enrich sites/bbc_news/instance_seed/bbc_news.db with

  * ~140 fresh articles parsed from public BBC RSS feeds (cached locally
    at /tmp/bbc_rss/*.xml so we never re-fetch during this script).
  * 100+ comments distributed across 5 users and 60+ articles, including
    reply chains.
  * 200+ reading_history rows for the 5 demo/benchmark users.

All inserts are gated by sentinel checks against a copy of the existing
DB; running the script twice produces byte-identical output (idempotent).
Timestamps are pinned to MIRROR_REFERENCE_DATE (2026-04-15) for new
synthetic rows; new articles get the real RSS pubDate when present.

Run from /home/v-haoqiwang/repos/WebHarbor with:

    python3 sites/bbc_news/bake_extras.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
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

# Map RSS feed file -> primary category slug used in our DB
FEED_TO_CAT = {
    "news_rss.xml": "world",
    "news_world_rss.xml": "world",
    "news_uk_rss.xml": "uk",
    "news_politics_rss.xml": "politics",
    "news_business_rss.xml": "business",
    "news_technology_rss.xml": "technology",
    "news_health_rss.xml": "health",
    "news_science_and_environment_rss.xml": "science",
    "news_entertainment_and_arts_rss.xml": "entertainment",
    "sport_rss.xml": "sport",
}

# Deterministic randomness — same outputs across runs
RNG = random.Random(20260415)


# -----------------------------------------------------------------------
# RSS parsing
# -----------------------------------------------------------------------

NS = {
    "media": "http://search.yahoo.com/mrss/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _slug_from_link(link: str) -> str | None:
    """Extract the BBC article id from a /news/articles/<id> URL."""
    m = re.search(r"/articles/([a-z0-9]{8,16})", link)
    if m:
        return m.group(1)
    return None


def parse_rss(path: Path, cat_slug: str) -> list[dict]:
    """Return parsed items from one RSS file. Skips Tech Life / Tech Now
    audio + iPlayer entries (they don't have /articles/<id> permalinks)."""
    out: list[dict] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return out
    for item in tree.getroot().iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        slug = _slug_from_link(link)
        if not slug or not title:
            continue
        # Try media:thumbnail first; fallback to media:content
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
        # Strip tracking params from canonical URL
        clean_link = re.sub(r"\?at_.*$", "", link)
        out.append({
            "slug": slug,
            "headline": title,
            "subtitle": desc[:300],
            "summary": desc[:300],
            "category": cat_slug,
            "thumb": thumb,
            "source_url": clean_link,
            "published_at": pub_dt,
        })
    return out


def collect_rss_articles() -> list[dict]:
    """Read every cached feed; de-dupe by slug; assign each article to its
    *first-seen* category so the feed order matches BBC's own taxonomy
    (Tech beats World for an AI item that appears in both)."""
    seen: set[str] = set()
    bucket: list[dict] = []
    # Priority: specialized feeds first, generic last
    priority = [
        "news_technology_rss.xml",
        "news_science_and_environment_rss.xml",
        "news_health_rss.xml",
        "news_business_rss.xml",
        "news_politics_rss.xml",
        "news_entertainment_and_arts_rss.xml",
        "sport_rss.xml",
        "news_uk_rss.xml",
        "news_world_rss.xml",
        "news_rss.xml",
    ]
    for fname in priority:
        path = RSS_DIR / fname
        if not path.exists():
            continue
        cat = FEED_TO_CAT[fname]
        for art in parse_rss(path, cat):
            if art["slug"] in seen:
                continue
            seen.add(art["slug"])
            bucket.append(art)
    return bucket


# -----------------------------------------------------------------------
# Body synthesis from RSS title + description
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


# -----------------------------------------------------------------------
# Insert: articles
# -----------------------------------------------------------------------

def insert_new_articles(con: sqlite3.Connection, rss: list[dict]) -> int:
    """Insert RSS-derived articles whose slug is not already in the DB.
    Returns # rows inserted."""
    existing = existing_article_slugs(con)
    cat_map = cat_id_by_slug(con)
    # Some RSS feeds map to slugs we don't have; default to 'world'
    default_cid = cat_map["world"]

    rows = []
    for art in rss:
        if art["slug"] in existing:
            continue
        cid = cat_map.get(art["category"], default_cid)
        body = synth_body(art["headline"], art["subtitle"])
        word_count = len(body.split())
        reading_time = max(2, word_count // 200)
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
            "topics_json": json.dumps([art["category"].title()]),
            "published_at": art["published_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "reading_time": reading_time,
            "word_count": word_count,
            # Deterministic but spread-out view counts (RNG seeded once)
            "view_count": 500 + RNG.randrange(40000),
            "is_featured": 0,
            "is_breaking": 0,
            "is_live": 0,
            "location": "",
            "source_url": art["source_url"],
            "section_slug": art["category"],
            "subsection": "",
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
# Insert: comments + reading_history
# -----------------------------------------------------------------------

def insert_comments(con: sqlite3.Connection) -> int:
    """Distribute ~120 top-level comments + replies across a diverse pool
    of articles. Idempotent: skips if any comment already exists.

    Approach:
      * Pick 60 articles (10 from each of: top viewed, random tech,
        random world, random uk, random sport, random business).
      * Assign 1-3 top-level comments per article (round-robin users).
      * For ~30% of top-level comments, add 1-2 replies from a
        different user.
    """
    cur = con.cursor()
    if cur.execute("SELECT COUNT(*) FROM comments").fetchone()[0] > 0:
        return 0

    user_ids = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
    # Pull a diverse article pool. We want spread across sections so the
    # task surface is rich, not just popular tech articles.
    article_pool: list[int] = []
    for section in ("technology", "world", "uk", "sport", "business",
                    "health", "science", "politics", "entertainment", "arts"):
        ids = [r[0] for r in cur.execute(
            "SELECT id FROM articles WHERE section_slug=? "
            "ORDER BY view_count DESC LIMIT 8", (section,)
        )]
        article_pool.extend(ids)
    # De-dupe while keeping order
    seen: set[int] = set()
    article_pool = [x for x in article_pool if not (x in seen or seen.add(x))]

    # If somehow we got too few, top up with random articles
    if len(article_pool) < 60:
        extra = [r[0] for r in cur.execute(
            "SELECT id FROM articles WHERE id NOT IN ({}) "
            "ORDER BY id LIMIT 60".format(
                ",".join(str(i) for i in article_pool) or "0"
            )
        )]
        article_pool.extend(extra[: 60 - len(article_pool)])

    base_ts = MIRROR_REFERENCE_DATE
    inserted = 0
    top_level_ids: list[tuple[int, int, int]] = []  # (article_id, user_id, comment_id placeholder)

    # Phase 1: top-level comments
    rows_top = []
    for idx, art_id in enumerate(article_pool):
        n_top = RNG.choice([1, 2, 2, 3])
        for j in range(n_top):
            uid = user_ids[(idx + j) % len(user_ids)]
            body = COMMENT_TOP_LEVEL[(idx * 3 + j) % len(COMMENT_TOP_LEVEL)]
            # Spread timestamps within the last 30 days before reference
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
    inserted += len(rows_top)

    # Phase 2: replies — for every 3rd top-level comment, add 1-2 replies
    new_top = list(cur.execute(
        "SELECT id, article_id, user_id, created_at FROM comments "
        "WHERE parent_id IS NULL ORDER BY id"
    ))
    rows_replies = []
    for i, (cid, art_id, uid, created_at) in enumerate(new_top):
        if i % 3 != 0:
            continue
        n_replies = RNG.choice([1, 1, 2])
        for k in range(n_replies):
            # reply user must differ from parent's user
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


# Topic affinity per user — drives realistic reading_history selection
USER_INTERESTS = {
    "alice.j@test.com": ["technology", "science", "ai", "business"],
    "bob.c@test.com":   ["business", "world", "politics", "uk"],
    "carol.d@test.com": ["health", "science", "earth", "uk"],
    "david.k@test.com": ["sport", "entertainment", "arts", "culture"],
    "demo@bbcnews.local": ["world", "uk", "technology", "business", "health"],
}


def insert_reading_history(con: sqlite3.Connection) -> int:
    """Generate ~50 reading_history rows per user (250 total) — articles
    drawn primarily from each user's interest sections, with a small mix
    of cross-topic exploration. Idempotent: skips if any row exists."""
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
        # A small slice of cross-topic exploration (10 random articles)
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

        # Assign timestamps — spread over the 21 days before reference
        for j, art_id in enumerate(chosen):
            ts = base_ts - timedelta(
                hours=(j * 9 + uid * 3) % (24 * 21),
                minutes=(j * 13) % 60,
            )
            rows.append((uid, art_id, ts.strftime("%Y-%m-%d %H:%M:%S")))

    cur.executemany(
        "INSERT INTO reading_history (user_id, article_id, viewed_at) "
        "VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


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
        con.commit()
    finally:
        con.close()

    print(f"[bake] inserted: +{n_art} articles, +{n_cm} comments, +{n_rh} reading_history")
    print(f"[bake] md5 after:  {_db_signature(DB_PATH)}")

    # Quick post-condition summary
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
