#!/usr/bin/env python3
"""Generic body-refetch template for thin-text bulk_api rows.

Pattern (BBC 2026-05-28): bulk_api script INSERTed rows with short
body / description / summary text from RSS / search snippet / API stub.
This second-pass script visits each row's `source_url` and replaces the
short text with the full article body extracted via trafilatura.

Copy this file to <site>_body_enrich.py and fill in 4 TODOs.

Real impact reference (bbc_news):
  870 rows updated / avg body 581 → 3088 chars / 7.5 min / 0 HTTP failures
"""
from __future__ import annotations
import sys
import time
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import fetch, open_db, periodic_commit, upsert_count  # noqa: E402

import trafilatura  # type: ignore

# TODO #1: site + table + column names
SITE = '<site_slug>'
TABLE = 'articles'
BODY_COL = 'body'              # column holding the text to extend
SOURCE_URL_COL = 'source_url'  # column holding the upstream URL to scrape
MIN_BODY_LEN = 500             # rows shorter than this are candidates
EXTRACT_MIN_LEN = 200          # trafilatura output below this is rejected
BODY_CAP_BYTES = 8192          # 8 KB cap — mirror not archive

# TODO #2 (optional): extra columns to update in lockstep with body
# e.g. word_count, reading_time — set to None to skip
WORD_COUNT_COL: str | None = 'word_count'
READING_TIME_COL: str | None = 'reading_time'

# TODO #3: pacing
SLEEP_BETWEEN_REQUESTS = 0.4   # seconds — be polite to upstream
CONSECUTIVE_FAIL_BAIL = 10     # stop early if N consecutive failures (likely IP blocked)


def select_candidates(con: sqlite3.Connection) -> list[tuple[int, str]]:
    sql = (f'SELECT id, "{SOURCE_URL_COL}" FROM "{TABLE}" '
           f'WHERE LENGTH("{BODY_COL}") < ? '
           f'AND "{SOURCE_URL_COL}" IS NOT NULL AND "{SOURCE_URL_COL}" != "" '
           f'ORDER BY id')
    return list(con.execute(sql, (MIN_BODY_LEN,)))


def extract_body(url: str) -> str | None:
    try:
        html = fetch(url, timeout=10, retries=2).decode('utf-8', errors='replace')
    except Exception:
        return None
    body = trafilatura.extract(html, include_comments=False, include_tables=False,
                                include_formatting=False, favor_recall=True)
    if not body or len(body) < EXTRACT_MIN_LEN:
        return None
    return body[:BODY_CAP_BYTES]


def main():
    # TODO #4: import argparse if you need --limit / --dry-run; otherwise leave bare
    con = open_db(SITE)
    candidates = select_candidates(con)
    print(f'before: {upsert_count(con, TABLE)} rows total, {len(candidates)} candidates with short body + source_url')

    updated = skipped = consec_fail = 0
    for rid, url in candidates:
        body = extract_body(url)
        if not body:
            skipped += 1
            consec_fail += 1
            if consec_fail >= CONSECUTIVE_FAIL_BAIL:
                print(f'BAIL: {consec_fail} consecutive failures, likely rate-limited')
                break
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            continue
        consec_fail = 0

        words = body.split()
        sets: list[str] = [f'"{BODY_COL}" = ?']
        vals: list = [body]
        if WORD_COUNT_COL:
            sets.append(f'"{WORD_COUNT_COL}" = ?')
            vals.append(len(words))
        if READING_TIME_COL:
            sets.append(f'"{READING_TIME_COL}" = ?')
            vals.append(max(1, len(words) // 200))
        vals.append(rid)
        con.execute(f'UPDATE "{TABLE}" SET {", ".join(sets)} WHERE id = ?', vals)

        updated += 1
        periodic_commit(con, updated, every=50)
        if updated % 100 == 0:
            print(f'  progress: updated={updated}, skipped={skipped}')
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    con.commit()
    avg_after = con.execute(f'SELECT AVG(LENGTH("{BODY_COL}")) FROM "{TABLE}"').fetchone()[0]
    long_after = con.execute(f'SELECT COUNT(*) FROM "{TABLE}" WHERE LENGTH("{BODY_COL}") > 1000').fetchone()[0]
    print(f'after: updated={updated} skipped={skipped} avg_body={avg_after:.0f} long_count={long_after}')

    # IMPORTANT: verify container DB matches host (gotcha #56)
    print('\nNext: docker cp + verify container row count matches host:')
    print(f'  docker cp sites/{SITE}/instance/{SITE}.db wh-r10:/opt/WebSyn/{SITE}/instance/{SITE}.db')
    print(f'  docker cp sites/{SITE}/instance/{SITE}.db wh-r10:/opt/WebSyn/{SITE}/instance_seed/{SITE}.db')
    print(f'  docker exec wh-r10 python3 -c "import sqlite3; '
          f'print(sqlite3.connect(\'/opt/WebSyn/{SITE}/instance/{SITE}.db\').'
          f'execute(\'SELECT COUNT(*) FROM {TABLE} WHERE LENGTH({BODY_COL}) > 1000\').fetchone()[0])"')

    con.close()


if __name__ == '__main__':
    main()
