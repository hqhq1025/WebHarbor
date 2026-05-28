#!/usr/bin/env python3
"""Extend GitHub mirror repos via GitHub REST search API.

Target: 56001 repos / 6701 users / 12391 topics (already saturated; this
script is reproducibility reference).
Source: https://api.github.com/search/repositories?q=stars:>10000&sort=stars

Notes:
  - DB file is `github_mirror.db`, NOT `github.db`. We bypass _common.open_db
    and open it directly with sqlite3.
  - Tables: repository, user, topic, repo_topics (singular).
  - Unauthenticated search limit = 10 req/min => sleep 6s between calls.
    Honors GITHUB_TOKEN env var if present (raises ceiling to 30/min).
  - Only use the search endpoint; we don't probe per-repo /repos/X/Y as it
    blows past the rate budget for negligible new entities.
  - Max 1000 search results per query (10 pages * 100 per_page).
"""
from __future__ import annotations
import os
import sqlite3
import sys
import time
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import fetch_json, slugify, insert_or_ignore, periodic_commit  # noqa: E402

DB = '/home/v-haoqiwang/repos/WebHarbor/sites/github/instance/github_mirror.db'
API = 'https://api.github.com'
PER_PAGE = 100
MAX_PAGES = 10  # GitHub caps search at 1000 results
SLEEP_BETWEEN = 6.5  # 10 req/min unauthenticated

TOKEN = os.environ.get('GITHUB_TOKEN')
AUTH = {'Authorization': f'Bearer {TOKEN}'} if TOKEN else {}


def gh_search(query: str, page: int):
    url = f'{API}/search/repositories?q={query}&sort=stars&order=desc&per_page={PER_PAGE}&page={page}'
    return fetch_json(url, headers=AUTH)


def parse_dt(s):
    if not s:
        return None
    try:
        return dt.datetime.strptime(s.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
    except Exception:
        return None


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    before_r = cur.execute('SELECT COUNT(*) FROM repository').fetchone()[0]
    before_u = cur.execute('SELECT COUNT(*) FROM user').fetchone()[0]
    before_t = cur.execute('SELECT COUNT(*) FROM topic').fetchone()[0]
    print(f'before: repository={before_r} user={before_u} topic={before_t}')

    existing_full = {r[0] for r in cur.execute('SELECT full_name FROM repository')}
    existing_users = {r[0]: r[1] for r in cur.execute('SELECT username, id FROM user')}
    existing_topics = {r[0]: r[1] for r in cur.execute('SELECT slug, id FROM topic')}

    added_r = added_u = added_t = 0
    seen = 0
    for page in range(1, MAX_PAGES + 1):
        try:
            payload = gh_search('stars:>10000', page)
        except Exception as e:
            print(f'  page {page} failed: {e}')
            time.sleep(SLEEP_BETWEEN * 2)
            continue
        items = payload.get('items') or []
        if not items:
            break
        for item in items:
            seen += 1
            full = item.get('full_name') or ''
            if not full or full in existing_full:
                continue
            owner = item.get('owner') or {}
            uname = owner.get('login') or ''
            if not uname:
                continue
            # Insert owner first
            owner_id = existing_users.get(uname)
            if owner_id is None:
                row_u = {
                    'username': uname,
                    'email': f'{uname}@users.noreply.github.com',
                    'password_hash': '!disabled',
                    'name': uname,
                    'bio': None,
                    'location': None,
                    'website': owner.get('html_url') or None,
                    'company': None,
                    'twitter': None,
                    'avatar': owner.get('avatar_url') or None,
                    'is_admin': 0,
                    'created_at': dt.datetime.utcnow(),
                    'plan': 'free',
                }
                new_uid = insert_or_ignore(con, 'user', row_u)
                if new_uid is not None:
                    added_u += 1
                    owner_id = new_uid
                else:
                    row = cur.execute('SELECT id FROM user WHERE username=?', (uname,)).fetchone()
                    owner_id = row[0] if row else None
                existing_users[uname] = owner_id
            if owner_id is None:
                continue
            topics_list = item.get('topics') or []
            row_r = {
                'owner_id': owner_id,
                'name': item.get('name') or full.split('/')[-1],
                'full_name': full,
                'description': item.get('description'),
                'language': item.get('language'),
                'license': ((item.get('license') or {}) or {}).get('spdx_id'),
                'stars_count': item.get('stargazers_count') or 0,
                'forks_count': item.get('forks_count') or 0,
                'watchers_count': item.get('watchers_count') or 0,
                'open_issues_count': item.get('open_issues_count') or 0,
                'is_public': 0 if item.get('private') else 1,
                'is_fork': 1 if item.get('fork') else 0,
                'is_template': 1 if item.get('is_template') else 0,
                'is_archived': 1 if item.get('archived') else 0,
                'has_readme': 0,
                'has_wiki': 1 if item.get('has_wiki') else 0,
                'has_issues': 1 if item.get('has_issues') else 0,
                'owner_type': (owner.get('type') or '')[:20],
                'homepage': item.get('homepage'),
                'default_branch': item.get('default_branch') or 'main',
                'size_kb': item.get('size') or 0,
                'readme': None,
                'topics_text': ' '.join(topics_list),
                'gallery_json': '[]',
                'created_at': parse_dt(item.get('created_at')),
                'updated_at': parse_dt(item.get('updated_at')),
                'pushed_at': parse_dt(item.get('pushed_at')),
            }
            new_rid = insert_or_ignore(con, 'repository', row_r)
            if new_rid is None:
                continue
            added_r += 1
            existing_full.add(full)
            # Topics
            for tslug in topics_list:
                if not tslug:
                    continue
                tid = existing_topics.get(tslug)
                if tid is None:
                    nt = insert_or_ignore(con, 'topic', {
                        'slug': tslug, 'display_name': tslug.replace('-', ' ').title(),
                        'description': None, 'short_desc': None, 'image': None,
                        'repos_count': 0, 'is_featured': 0, 'created_at': dt.datetime.utcnow(),
                    })
                    if nt is not None:
                        added_t += 1
                        tid = nt
                    else:
                        row = cur.execute('SELECT id FROM topic WHERE slug=?', (tslug,)).fetchone()
                        tid = row[0] if row else None
                    existing_topics[tslug] = tid
                if tid is not None:
                    insert_or_ignore(con, 'repo_topics', {'repo_id': new_rid, 'topic_id': tid})
            periodic_commit(con, added_r, every=50)
        con.commit()
        print(f'  page {page}: seen total={seen}, +repo={added_r}')
        time.sleep(SLEEP_BETWEEN)

    con.commit()
    after_r = cur.execute('SELECT COUNT(*) FROM repository').fetchone()[0]
    after_u = cur.execute('SELECT COUNT(*) FROM user').fetchone()[0]
    after_t = cur.execute('SELECT COUNT(*) FROM topic').fetchone()[0]
    print(f'after: repository={after_r} (+{added_r}) user={after_u} (+{added_u}) topic={after_t} (+{added_t})')
    con.close()


if __name__ == '__main__':
    main()
