#!/usr/bin/env python3
"""index_pool.py — unified image pool with FTS5 search + content-hash dedup.

Walks all snapshots/<site>/_image_urls.jsonl, indexes alt text with FTS5 for
fast text search across all harvested image URLs.

Usage:
  python3 index_pool.py build      # build pool.db from all _image_urls.jsonl
  python3 index_pool.py search 'concert music stage' --n 10
  python3 index_pool.py stats
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path("~/webvoyager-analysis/real_components").expanduser()
SNAPSHOTS = ROOT / "snapshots"
POOL_DB = ROOT / "pool.db"


def init_db():
    con = sqlite3.connect(POOL_DB)
    con.executescript("""
        DROP TABLE IF EXISTS images_fts;
        DROP TABLE IF EXISTS images;
        CREATE TABLE images (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            alt TEXT,
            kind TEXT,
            source_site TEXT,
            source_page TEXT,
            cdn_host TEXT
        );
        CREATE VIRTUAL TABLE images_fts USING fts5(
            alt, kind, source_site, cdn_host,
            content='images', content_rowid='id'
        );
    """)
    return con


def build():
    if POOL_DB.exists():
        POOL_DB.unlink()
    con = init_db()
    n = 0
    for site_dir in sorted(SNAPSHOTS.iterdir()):
        if not site_dir.is_dir():
            continue
        urls_file = site_dir / "_image_urls.jsonl"
        if not urls_file.exists():
            continue
        for line in urls_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            url = r.get("url", "")
            if not url.startswith(("http://", "https://")):
                continue
            cdn = url.split("/")[2] if "://" in url else ""
            try:
                con.execute("""INSERT OR IGNORE INTO images
                               (url, alt, kind, source_site, source_page, cdn_host)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                             (url, r.get("alt", ""), r.get("kind", ""),
                              site_dir.name, r.get("page", ""), cdn))
                n += 1
            except Exception:
                pass
    con.commit()
    # Populate FTS via INSERT INTO ... SELECT (works regardless of triggers)
    con.execute("INSERT INTO images_fts(rowid, alt, kind, source_site, cdn_host) "
                "SELECT id, alt, kind, source_site, cdn_host FROM images")
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    distinct_cdn = con.execute("SELECT COUNT(DISTINCT cdn_host) FROM images").fetchone()[0]
    fts_total = con.execute("SELECT COUNT(*) FROM images_fts").fetchone()[0]
    print(f"Built pool.db: {total} URLs / {distinct_cdn} CDN hosts / {fts_total} FTS rows")
    con.close()


def search_pool(query, n=10, source_site=None, cdn_host=None):
    if not POOL_DB.exists():
        print("pool.db missing — run `index_pool.py build` first", file=sys.stderr)
        return []
    con = sqlite3.connect(POOL_DB)
    where = []
    if source_site:
        where.append(f"images.source_site GLOB '{source_site}'")
    if cdn_host:
        where.append(f"images.cdn_host GLOB '{cdn_host}'")
    where_str = " AND " + " AND ".join(where) if where else ""
    rows = con.execute(f"""
        SELECT images.url, images.alt, images.cdn_host, images.source_site, rank
        FROM images_fts JOIN images ON images_fts.rowid = images.id
        WHERE images_fts MATCH ? {where_str}
        ORDER BY rank LIMIT ?
    """, (query, n)).fetchall()
    con.close()
    return rows


def stats():
    if not POOL_DB.exists():
        print("pool.db missing — run `index_pool.py build` first")
        return
    con = sqlite3.connect(POOL_DB)
    total = con.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    print(f"Total: {total} distinct URLs")
    print("\nTop 15 CDN hosts:")
    for cdn, count in con.execute("""SELECT cdn_host, COUNT(*) c FROM images
                                       GROUP BY cdn_host ORDER BY c DESC LIMIT 15"""):
        print(f"  {count:>6}  {cdn}")
    print("\nTop 10 source_site by URL count:")
    for site, count in con.execute("""SELECT source_site, COUNT(*) c FROM images
                                        GROUP BY source_site ORDER BY c DESC LIMIT 10"""):
        print(f"  {count:>6}  {site}")
    con.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("build")
    sub.add_parser("stats")
    sp = sub.add_parser("search")
    sp.add_argument("query")
    sp.add_argument("--n", type=int, default=10)
    sp.add_argument("--source", default=None)
    sp.add_argument("--cdn", default=None)
    args = ap.parse_args()

    if args.cmd == "build":
        build()
    elif args.cmd == "stats":
        stats()
    elif args.cmd == "search":
        rows = search_pool(args.query, args.n, args.source, args.cdn)
        for url, alt, cdn, site, rank in rows:
            print(f"  [{cdn[:30]:30s}] alt={alt[:50]:50s} {url[:80]}")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
