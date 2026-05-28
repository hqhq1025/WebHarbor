#!/usr/bin/env python3
"""Bulk-API fetcher template — copy this to <site>_<source>.py for a new site.

Replace the four TODO blocks. Keep the file under ~150 lines; if you need
more, you probably want a second script (e.g. one for entity, one for
relations) rather than one giant orchestrator.

Pattern:
  1. Build candidate pool from the public/official API (search, listing,
     category page, etc).
  2. Dedup against the rows already in instance/<site>.db (slug / canonical id).
  3. For each new candidate, fetch detail (if needed) and INSERT OR IGNORE.
  4. Periodic commit every N rows + final commit.
  5. Diversity gate on the image column (if the table has one).

Run with:
  .venv/bin/python3 tools/bulk_api/<script>.py > /tmp/<site>_bulk.log 2>&1
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import (  # noqa: E402
    fetch_json, slugify, open_db, insert_or_ignore, periodic_commit,
    upsert_count, assert_image_diversity,
)

# TODO #1: site identifier (matches sites/<SITE>/instance/<SITE>.db)
SITE = '<site_slug>'

# TODO #2: API constants
API_BASE = 'https://api.example.com/v1'
ENTITY_TABLE = 'items'
ENTITY_UNIQUE_COL = 'slug'
ENTITY_IMAGE_COL = 'image_url'   # set to None if the table has no image column


def build_candidate_pool(con) -> list[dict]:
    """TODO #3: query the public API, return a list of dict rows.

    Each dict should contain at minimum:
      - ENTITY_UNIQUE_COL (e.g. 'slug') — used for dedup
      - the columns the destination table requires (NOT NULL columns first).
    Skip image URLs if you don't have a real CDN/public one yet — leave NULL
    and let scrape-real-images Phase 5b fill it.
    """
    existing = {r[0] for r in con.execute(
        f'SELECT "{ENTITY_UNIQUE_COL}" FROM "{ENTITY_TABLE}"'
    )}
    candidates: list[dict] = []
    # Example: page through a search endpoint.
    # for page in range(1, 21):
    #     payload = fetch_json(f'{API_BASE}/search?page={page}')
    #     for item in payload.get('results', []):
    #         slug = slugify(item['title'])
    #         if slug in existing:
    #             continue
    #         existing.add(slug)
    #         candidates.append({
    #             'slug': slug,
    #             'title': item['title'],
    #             ENTITY_IMAGE_COL: item.get('thumbnail') or None,
    #         })
    #     time.sleep(0.3)
    return candidates


def main():
    con = open_db(SITE)
    before = upsert_count(con, ENTITY_TABLE)
    print(f'before: {before} rows in {ENTITY_TABLE}')

    candidates = build_candidate_pool(con)
    print(f'candidate pool: {len(candidates)} new rows')

    added = 0
    for row in candidates:
        if insert_or_ignore(con, ENTITY_TABLE, row) is not None:
            added += 1
            periodic_commit(con, added, every=50)

    con.commit()
    after = upsert_count(con, ENTITY_TABLE)
    print(f'after: {after} rows (+{added})')

    # TODO #4: drop or keep depending on whether the table has an image column.
    if ENTITY_IMAGE_COL:
        assert_image_diversity(con, ENTITY_TABLE, ENTITY_IMAGE_COL)
    con.close()


if __name__ == '__main__':
    main()
