#!/usr/bin/env python3
"""Enrich short BBC article bodies by scraping each `source_url`.

Background
----------
Earlier `bbc_rss_feeds.py` populated 600+ rows with the RSS `<description>`,
which BBC trims to ~140 chars. Real BBC articles run 500-2000+ words, so the
mirror feels truncated. This script walks every row whose `LENGTH(body) < 500`
AND has a `source_url`, fetches the real article HTML, extracts the main text
with trafilatura, and writes it back.

Safety
------
* GUI-only / mirror semantics: body cap at 8 KB (truncation is fine).
* Sleep 0.4s between requests; bail if 10 consecutive HTTP failures.
* Commits every 50 rows so a crash midway still keeps progress.
* Failures (404, timeout, empty extract) leave the original RSS summary intact.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from urllib.parse import urlsplit, urlunsplit

import requests
import trafilatura

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/bbc_news/instance/bbc_news.db'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
MIN_LEN = 500           # rows shorter than this are candidates
MAX_BODY = 8 * 1024     # 8 KB hard cap on stored body
SLEEP_S = 0.4
COMMIT_EVERY = 50
ABORT_AFTER = 10        # consecutive HTTP failures before bailing


def clean_url(url: str) -> str:
    """Drop RSS tracking params (?at_medium=RSS&at_campaign=rss)."""
    parts = urlsplit(url)
    if parts.query and 'at_medium=RSS' in parts.query:
        parts = parts._replace(query='')
    return urlunsplit(parts)


def fetch_body(url: str, session: requests.Session) -> tuple[str | None, str]:
    """Return (extracted_text, reason). reason is '' on success."""
    try:
        r = session.get(url, timeout=12, allow_redirects=True)
    except requests.RequestException as exc:
        return None, f'net:{type(exc).__name__}'
    if r.status_code != 200:
        return None, f'http:{r.status_code}'
    body = trafilatura.extract(
        r.text,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if not body or len(body) < 200:
        return None, 'extract:short'
    return body, ''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='Only process first N rows (0 = all)')
    ap.add_argument('--dry-run', action='store_true', help='Fetch but do not write')
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, source_url FROM articles "
        "WHERE LENGTH(body) < ? AND source_url IS NOT NULL AND source_url != '' "
        "ORDER BY id",
        (MIN_LEN,),
    ).fetchall()
    if args.limit:
        rows = rows[: args.limit]

    avg_before = cur.execute('SELECT AVG(LENGTH(body)) FROM articles').fetchone()[0]
    print(f'[bbc_body_enrich] candidates={len(rows)}  avg_body_before={avg_before:.0f}')

    session = requests.Session()
    session.headers.update({'User-Agent': UA, 'Accept-Language': 'en-GB,en;q=0.9'})

    updated = 0
    skipped: dict[str, int] = {}
    consec_fail = 0
    t0 = time.time()

    for i, (aid, url) in enumerate(rows, 1):
        clean = clean_url(url)
        body, reason = fetch_body(clean, session)
        if body is None:
            skipped[reason] = skipped.get(reason, 0) + 1
            if reason.startswith('http:') or reason.startswith('net:'):
                consec_fail += 1
                if consec_fail >= ABORT_AFTER:
                    print(
                        f'[abort] {consec_fail} consecutive HTTP/net failures; '
                        f'BBC may be rate-limiting. Stopping at row {i}/{len(rows)}.',
                        file=sys.stderr,
                    )
                    break
        else:
            consec_fail = 0
            if len(body) > MAX_BODY:
                body = body[:MAX_BODY]
            wc = len(body.split())
            rt = max(1, wc // 200)
            if not args.dry_run:
                cur.execute(
                    'UPDATE articles SET body = ?, word_count = ?, reading_time = ? WHERE id = ?',
                    (body, wc, rt, aid),
                )
            updated += 1

        if i % COMMIT_EVERY == 0:
            if not args.dry_run:
                con.commit()
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed else 0
            eta = (len(rows) - i) / rate if rate else 0
            print(
                f'  [{i}/{len(rows)}] updated={updated} skipped={sum(skipped.values())} '
                f'rate={rate:.1f}/s eta={eta:.0f}s',
                flush=True,
            )

        time.sleep(SLEEP_S)

    if not args.dry_run:
        con.commit()

    avg_after = cur.execute('SELECT AVG(LENGTH(body)) FROM articles').fetchone()[0]
    over1k = cur.execute('SELECT COUNT(*) FROM articles WHERE LENGTH(body) > 1000').fetchone()[0]
    mn, mx = cur.execute('SELECT MIN(LENGTH(body)), MAX(LENGTH(body)) FROM articles').fetchone()
    con.close()

    print()
    print('[bbc_body_enrich] DONE')
    print(f'  updated      : {updated}')
    print(f'  skipped      : {sum(skipped.values())}  detail={skipped}')
    print(f'  avg_body     : {avg_before:.0f} -> {avg_after:.0f}')
    print(f'  body min/max : {mn} / {mx}')
    print(f'  body > 1000  : {over1k}')
    print(f'  elapsed      : {time.time() - t0:.0f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
