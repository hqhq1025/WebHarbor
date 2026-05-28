#!/usr/bin/env python3
"""Extend Hugging Face repositories via HF official listing API.

Target: top-up 456k repositories / 89k authors mirror DB with most recent
        trending models, datasets and spaces (last few days). Site is
        super-saturated so per-run delta will be small — that's expected.
Source: https://huggingface.co/api/{models,datasets,spaces} (no auth).

Quirks discovered:
- The actual DB file is hf.db, NOT huggingface.db (huggingface.db is 0 bytes).
- repositories has UNIQUE (slug, repo_type), so the same id can exist under
  different repo_types and that's fine; we dedup per repo_type.
- HF listing API returns `id` (full slug "user/repo"), `author`, `downloads`,
  `likes`, `tags`, `lastModified`, `createdAt`, optionally `pipeline_tag`,
  `library_name`, `sdk` (spaces). License lives in tags as `license:foo` or
  in cardData; falls back to NULL.
- Sort by createdAt DESC pulls newest-first; we stop once we hit a row that's
  already in the DB to keep the run short.
"""
from __future__ import annotations
import sqlite3
import sys
import time
import json
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import fetch_json, UA  # noqa: E402

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/huggingface/instance/hf.db'
API_BASE = 'https://huggingface.co/api'

# (repo_type, listing endpoint, sort key)
KINDS = [
    ('model',   'models',   'createdAt'),
    ('dataset', 'datasets', 'createdAt'),
    ('space',   'spaces',   'createdAt'),
]

PAGES_PER_KIND = 12   # 12 * 100 = up to 1200 candidates per kind
PER_PAGE = 100
SLEEP = 0.25


def _license_from_tags(tags):
    for t in tags or []:
        if isinstance(t, str) and t.startswith('license:'):
            return t.split(':', 1)[1][:80]
    return None


def _iso(s):
    if not s:
        return None
    try:
        return dt.datetime.strptime(s.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
    except Exception:
        try:
            return dt.datetime.strptime(s.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
        except Exception:
            return None


def _ensure_author(cur, username, author_cache):
    if not username:
        return None
    if username in author_cache:
        return author_cache[username]
    row = cur.execute('SELECT id FROM authors WHERE username=?', (username,)).fetchone()
    if row:
        author_cache[username] = row[0]
        return row[0]
    # Insert minimal author row.
    cur.execute(
        'INSERT OR IGNORE INTO authors (username, display_name, kind, bio, '
        'followers_count, website, avatar_url, is_verified, created_at) '
        'VALUES (?,?,?,?,?,?,?,?,?)',
        (username[:120], username[:200], 'user', None, 0, None, None, 0, dt.datetime.utcnow()))
    row = cur.execute('SELECT id FROM authors WHERE username=?', (username,)).fetchone()
    author_cache[username] = row[0]
    return row[0]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    before_repos = cur.execute('SELECT COUNT(*) FROM repositories').fetchone()[0]
    before_authors = cur.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
    print(f'before: repositories={before_repos} authors={before_authors}')

    existing = {(r[0], r[1]) for r in cur.execute(
        'SELECT slug, repo_type FROM repositories')}
    author_cache = {}
    added_repos = 0
    added_authors_before = before_authors

    for repo_type, endpoint, sort_key in KINDS:
        kind_added = 0
        stop_kind = False
        for page in range(PAGES_PER_KIND):
            url = (f'{API_BASE}/{endpoint}?sort={sort_key}&direction=-1'
                   f'&limit={PER_PAGE}&full=false&skip={page * PER_PAGE}')
            try:
                payload = fetch_json(url)
            except Exception as e:
                print(f'  {repo_type} page {page} fetch fail: {e}')
                break
            if not isinstance(payload, list) or not payload:
                break
            page_added = 0
            for item in payload:
                slug = (item.get('id') or '')[:300]
                if not slug:
                    continue
                if (slug, repo_type) in existing:
                    continue
                existing.add((slug, repo_type))
                name = slug.split('/', 1)[-1][:200]
                author_user = item.get('author') or (slug.split('/', 1)[0] if '/' in slug else None)
                author_id = _ensure_author(cur, author_user, author_cache)
                tags = item.get('tags') or []
                cur.execute(
                    'INSERT OR IGNORE INTO repositories '
                    '(slug, name, repo_type, author_id, library, license, '
                    'description, downloads, likes_count, tags_json, '
                    'last_modified, created_at) '
                    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (slug, name, repo_type, author_id,
                     (item.get('library_name') or item.get('sdk') or None),
                     _license_from_tags(tags),
                     None,
                     int(item.get('downloads') or 0),
                     int(item.get('likes') or 0),
                     json.dumps(tags) if tags else None,
                     _iso(item.get('lastModified')),
                     _iso(item.get('createdAt'))))
                if cur.rowcount:
                    added_repos += 1
                    kind_added += 1
                    page_added += 1
                    if added_repos % 50 == 0:
                        con.commit()
            print(f'  {repo_type} page {page}: +{page_added}')
            if page_added == 0:
                # Newest page yielded no new ids → caught up.
                stop_kind = True
            con.commit()
            time.sleep(SLEEP)
            if stop_kind:
                break
        print(f'  {repo_type} total added: {kind_added}')

    con.commit()
    after_repos = cur.execute('SELECT COUNT(*) FROM repositories').fetchone()[0]
    after_authors = cur.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
    print(f'after: repositories={after_repos} (+{added_repos}) '
          f'authors={after_authors} (+{after_authors - added_authors_before})')
    con.close()


if __name__ == '__main__':
    main()
