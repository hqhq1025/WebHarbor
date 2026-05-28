#!/usr/bin/env python3
"""harvest_spider.py — BFS spider with checkpoint + link-pattern filter +
per-host fail-fast.

Builds on harvest.py: given a start URL, follows internal links matching a
regex pattern, BFS-bounded by --max-depth and --max-pages. SQLite-backed queue
means you can --resume after crash.

Usage:
  python3 harvest_spider.py <site> <start_url> \\
      --link-pattern '/dp/|/product/' --max-depth 2 --max-pages 200

Per-host fail-fast: after 2 consecutive bot_blocks on same hostname, spider
skips remaining queued URLs from that host.
"""
import argparse
import asyncio
import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harvest import harvest as harvest_one_url

ROOT = Path("~/webvoyager-analysis/real_components/snapshots").expanduser()


def url_slug(url):
    parsed = urllib.parse.urlparse(url)
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    last = parsed.path.rstrip("/").split("/")[-1] or "root"
    last = re.sub(r"[^a-zA-Z0-9._-]", "-", last)[:32].strip("-") or "page"
    return f"{last}_{h}"


def hostname(url):
    return urllib.parse.urlparse(url).netloc.lower()


def init_db(db_path: Path):
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS queue (
            url TEXT PRIMARY KEY,
            depth INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            added_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_status ON queue(status);
    """)
    return con


def extract_links(html, base_url, pattern):
    """Find <a href> matching regex, return absolute URLs within same domain."""
    base_host = hostname(base_url)
    rx = re.compile(pattern) if pattern else None
    links = set()
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = m.group(1).strip()
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        absolute = absolute.split("#")[0]  # strip fragment
        if hostname(absolute) != base_host:
            continue
        if rx and not rx.search(absolute):
            continue
        links.add(absolute)
    return links


class FakeArgs:
    """Adapter so we can call harvest.harvest() which expects argparse.Namespace."""
    def __init__(self, site, page_name, url, **kw):
        self.site = site
        self.page_name = page_name
        self.url = url
        self.headless = kw.get("headless", True)
        self.timeout = kw.get("timeout", 30)
        self.settle = kw.get("settle", 2000)
        self.scrolls = kw.get("scrolls", 3)
        self.ua = kw.get("ua", None)
        self.no_fallback = kw.get("no_fallback", False)


async def spider(args):
    site_dir = ROOT / args.site
    site_dir.mkdir(parents=True, exist_ok=True)
    db_path = site_dir / "_spider_queue.db"
    con = init_db(db_path)

    # Seed queue with start URL if not resume or queue empty
    pending = con.execute("SELECT COUNT(*) FROM queue WHERE status='pending'").fetchone()[0]
    if pending == 0 or not args.resume:
        con.execute("INSERT OR IGNORE INTO queue(url, depth, added_at) VALUES (?, 0, ?)",
                     (args.start_url, time.time()))
        con.commit()

    host_blocks = defaultdict(int)
    skipped_hosts = set()
    done_count = 0

    while done_count < args.max_pages:
        row = con.execute("""SELECT url, depth FROM queue
                              WHERE status='pending'
                              ORDER BY depth, added_at LIMIT 1""").fetchone()
        if not row:
            break
        url, depth = row
        host = hostname(url)
        if host in skipped_hosts:
            con.execute("UPDATE queue SET status='skipped_host' WHERE url=?", (url,))
            con.commit()
            continue

        con.execute("UPDATE queue SET status='in_progress' WHERE url=?", (url,))
        con.commit()

        page_name = url_slug(url)
        try:
            fake = FakeArgs(args.site, page_name, url,
                             timeout=args.timeout, settle=args.settle,
                             scrolls=args.scrolls)
            captured = await harvest_one_url(fake)
            done_count += 1

            if captured.get("bot_block"):
                host_blocks[host] += 1
                if host_blocks[host] >= 2:
                    skipped_hosts.add(host)
                    print(f"[fail-fast] {host} hit 2 bot_blocks — skipping remaining queued URLs")
            else:
                host_blocks[host] = 0

            # Extract links from full.html, enqueue
            if depth < args.max_depth and not captured.get("bot_block"):
                full_path = site_dir / page_name / "full.html"
                if full_path.exists():
                    html = full_path.read_text(encoding="utf-8", errors="ignore")
                    links = extract_links(html, url, args.link_pattern)
                    for link in links:
                        con.execute("INSERT OR IGNORE INTO queue(url, depth, added_at) VALUES (?, ?, ?)",
                                     (link, depth + 1, time.time()))

            con.execute("UPDATE queue SET status='done' WHERE url=?", (url,))
            con.commit()
        except Exception as e:
            con.execute("UPDATE queue SET status='failed' WHERE url=?", (url,))
            con.commit()
            print(f"[err] {url}: {e}")

    # Summary
    counts = dict(con.execute("SELECT status, COUNT(*) FROM queue GROUP BY status").fetchall())
    print(f"{args.site}: spider done — done={counts.get('done', 0)} "
          f"pending={counts.get('pending', 0)} skipped_host={counts.get('skipped_host', 0)} "
          f"failed={counts.get('failed', 0)} hosts_walled={len(skipped_hosts)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("start_url")
    ap.add_argument("--link-pattern", default="", help="regex; empty = follow all same-domain links")
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--max-pages", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--settle", type=int, default=1500)
    ap.add_argument("--scrolls", type=int, default=3)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    asyncio.run(spider(args))


if __name__ == "__main__":
    main()
