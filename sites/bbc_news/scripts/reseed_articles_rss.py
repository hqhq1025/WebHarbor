"""Re-seed the bbc_news.articles table from real BBC RSS feeds.

The table existed in instance/bbc_news.db at row count 0 — the rest of the
schema (users, categories, digests, comments, etc.) was intact but the
content rows were gone. The Article schema is the BBC mirror's own
(`headline`, `summary`, `body`, `hero_image`, `section_slug`, ...), not the
generic CMS schema the user's draft assumed.

This pulls ~30 entries per BBC RSS feed (11 feeds), maps each feed slug to
the matching category row, downloads the `<media:thumbnail>` hero image
into static/images/articles/, and INSERTs an `Article` row per RSS entry.

Writes are made to instance_seed/bbc_news.db first; on success the seed is
copied byte-id over instance/bbc_news.db.

Notes
-----
* feedparser handles BBC pubDate timezones (GMT/EDT/PDT) correctly via
  `entry.published_parsed`. Don't roll your own strptime.
* `hero_image` stores a `/static/images/articles/<file>` path that Flask
  serves; the file is downloaded locally so we don't fetch from BBC at
  runtime.
* `category_id` joins on the existing `categories` table by slug. The few
  RSS slugs that don't map (e.g. `top`) fall back to category `news`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

import feedparser

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED_DB = ROOT / "instance_seed" / "bbc_news.db"
INSTANCE_DB = ROOT / "instance" / "bbc_news.db"
IMG_DIR = ROOT / "static" / "images" / "articles"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# (feed slug -> URL, category slug). Feeds chosen so the mirror has
# coverage of the same sections the templates render (home, world,
# business, technology, science, health, sport, entertainment,
# politics, uk, education).
BBC_FEEDS: list[tuple[str, str, str]] = [
    ("news", "http://feeds.bbci.co.uk/news/rss.xml", "news"),
    ("world", "http://feeds.bbci.co.uk/news/world/rss.xml", "world"),
    ("uk", "http://feeds.bbci.co.uk/news/uk/rss.xml", "uk"),
    ("politics", "http://feeds.bbci.co.uk/news/politics/rss.xml", "politics"),
    ("business", "http://feeds.bbci.co.uk/news/business/rss.xml", "business"),
    ("technology", "http://feeds.bbci.co.uk/news/technology/rss.xml", "technology"),
    ("science", "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "science"),
    ("health", "http://feeds.bbci.co.uk/news/health/rss.xml", "health"),
    ("entertainment", "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "entertainment"),
    ("education", "http://feeds.bbci.co.uk/news/education/rss.xml", "news"),
    ("sport", "http://feeds.bbci.co.uk/sport/rss.xml", "sport"),
]

MAX_PER_FEED = 30
HTTP_TIMEOUT = 12


def http_get(url: str) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return r.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  http_get fail {url}: {e}")
        return None


def extract_thumb(entry) -> Optional[str]:
    # media:thumbnail, media:content, then enclosure
    for key in ("media_thumbnail", "media_content"):
        items = entry.get(key) or []
        for it in items:
            url = it.get("url")
            if url:
                return url
    for link in entry.get("links", []):
        if link.get("rel") == "enclosure" and "image" in (link.get("type") or ""):
            return link.get("href")
    return None


def slugify(entry) -> str:
    # BBC URLs look like .../news/articles/<24-char-id>
    link = entry.get("link") or ""
    last = link.rstrip("/").rsplit("/", 1)[-1]
    if last and re.match(r"^[a-z0-9]{6,}$", last):
        return last
    # fallback: hash the GUID
    gid = entry.get("id") or link or entry.get("title", "")
    return hashlib.md5(gid.encode("utf-8")).hexdigest()[:16]


def download_thumb(url: str, slug: str) -> Optional[str]:
    if not url:
        return None
    ext = pathlib.Path(url.split("?")[0]).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    dest = IMG_DIR / f"{slug}{ext}"
    if dest.exists() and dest.stat().st_size >= 5 * 1024:
        return f"/static/images/articles/{dest.name}"
    body = http_get(url)
    if not body or len(body) < 5 * 1024:
        return None
    dest.write_bytes(body)
    return f"/static/images/articles/{dest.name}"


def clean_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def fetch_all() -> list[dict]:
    out: list[dict] = []
    for feed_slug, url, cat_slug in BBC_FEEDS:
        print(f"[{feed_slug}] fetching {url}")
        feed = feedparser.parse(url, agent=USER_AGENT)
        if feed.bozo:
            print(f"  bozo: {feed.bozo_exception}")
        n_entries = len(feed.entries)
        print(f"  {n_entries} entries")
        for entry in feed.entries[:MAX_PER_FEED]:
            slug = slugify(entry)
            headline = entry.get("title") or "(untitled)"
            summary_raw = entry.get("summary") or entry.get("description") or ""
            summary = clean_html(summary_raw)
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            pub_dt = (
                dt.datetime(*published[:6]) if published else dt.datetime.utcnow()
            )
            thumb_url = extract_thumb(entry)
            local = download_thumb(thumb_url, slug) if thumb_url else None
            body = summary
            paragraphs = [body, "Reporting via the BBC News RSS feed."] if body else []
            word_count = sum(len(p.split()) for p in paragraphs)
            reading_time = max(1, word_count // 200)
            out.append(
                {
                    "slug": slug,
                    "headline": headline,
                    "subtitle": "",
                    "summary": summary[:500],
                    "body": "\n\n".join(paragraphs),
                    "category_slug": cat_slug,
                    "section_slug": cat_slug,
                    "hero_image": local or "",
                    "topics_json": json.dumps([feed_slug]),
                    "published_at": pub_dt,
                    "word_count": word_count,
                    "reading_time": reading_time,
                    "author": "BBC News",
                    "source_url": entry.get("link") or "",
                    "content_type": "article",
                }
            )
        time.sleep(0.5)
    return out


def seed(rows: list[dict]) -> None:
    con = sqlite3.connect(SEED_DB)
    try:
        cat_map = {
            slug: cid
            for cid, slug in con.execute("SELECT id, slug FROM categories").fetchall()
        }
        existing = con.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        print(f"existing articles: {existing}")
        inserted = 0
        for r in rows:
            cat_id = cat_map.get(r["category_slug"]) or cat_map.get("news")
            try:
                con.execute(
                    """
                    INSERT INTO articles
                        (slug, headline, subtitle, summary, body,
                         author, category_id, hero_image,
                         gallery_json, gallery_full_json, topics_json,
                         published_at, reading_time, word_count, view_count,
                         is_featured, is_breaking, is_live,
                         location, source_url,
                         section_slug, subsection, region,
                         video_url, feature_tags, content_type)
                    VALUES (?, ?, ?, ?, ?,
                            ?, ?, ?,
                            '[]', '{}', ?,
                            ?, ?, ?, 0,
                            0, 0, 0,
                            '', ?,
                            ?, '', '',
                            '', '[]', ?)
                    """,
                    (
                        r["slug"], r["headline"], r["subtitle"], r["summary"], r["body"],
                        r["author"], cat_id, r["hero_image"],
                        r["topics_json"],
                        r["published_at"], r["reading_time"], r["word_count"],
                        r["source_url"],
                        r["section_slug"],
                        r["content_type"],
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError as e:
                # likely slug collision
                print(f"  dup slug={r['slug']}: {e}")
        con.commit()
        print(f"inserted {inserted} new rows")
        new_total = con.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        with_hero = con.execute(
            "SELECT COUNT(*) FROM articles WHERE hero_image != ''"
        ).fetchone()[0]
        distinct_heroes = con.execute(
            "SELECT COUNT(DISTINCT hero_image) FROM articles WHERE hero_image != ''"
        ).fetchone()[0]
        print(
            f"total articles now: {new_total} (with hero: {with_hero}, distinct hero: {distinct_heroes})"
        )
        if new_total < 200:
            raise SystemExit(f"FAIL: only {new_total} articles after re-seed (<200)")
    finally:
        con.close()


def main() -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    if not SEED_DB.exists():
        raise SystemExit(f"seed db missing: {SEED_DB}")
    rows = fetch_all()
    print(f"fetched {len(rows)} rows from RSS")
    seed(rows)
    if INSTANCE_DB.exists():
        shutil.copy2(SEED_DB, INSTANCE_DB)
        print(f"copied {SEED_DB} -> {INSTANCE_DB}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
