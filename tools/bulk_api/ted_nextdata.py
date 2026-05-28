#!/usr/bin/env python3
"""Extend TED talks via sitemap discovery + per-talk __NEXT_DATA__ JSON island.

Target: ~350 -> ~1000+ talks
Pitfall (discovered 2026-05-28): /talks?page=N returns the SAME 24 talks
in __NEXT_DATA__ regardless of N — pagination is purely client-side. Same
with ?sort=oldest and ?topics=X. The only reliable enumeration source is
https://www.ted.com/sitemaps/talks-YYYY.xml.gz, which lists every
canonical talk URL. We hit recent-year sitemaps and fetch each new talk
page; videoData inside __NEXT_DATA__.props.pageProps gives the full record.

INSERT OR IGNORE on source_id (UNIQUE) and slug (UNIQUE).
Image col stores the real pi.tedcdn.com URL; Phase 5b mirrors it.
"""
from __future__ import annotations
import gzip
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from _common import (  # noqa: E402
    fetch, open_db, insert_or_ignore, periodic_commit,
    upsert_count, assert_image_diversity,
)

SITE = 'ted'
SITEMAP_TMPL = 'https://www.ted.com/sitemaps/talks-{year}.xml.gz'
YEARS = list(range(2018, 2027))           # ~recent decade
MAX_NEW = 800                              # politeness cap per run
PER_TALK_SLEEP = 0.4

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
LOC_RE = re.compile(r'<loc>(https://www\.ted\.com/talks/[^<]+)</loc>')


def list_sitemap_slugs(year: int) -> list[str]:
    raw = fetch(SITEMAP_TMPL.format(year=year))
    xml = gzip.decompress(raw).decode('utf-8', 'ignore')
    out = []
    for loc in LOC_RE.findall(xml):
        slug = loc.rsplit('/', 1)[-1].split('?', 1)[0]
        if slug:
            out.append(slug)
    return out


def pick_image(image_set, thumb_fallback):
    if isinstance(image_set, list):
        for shot in image_set:
            if isinstance(shot, dict) and shot.get('aspectRatioName') == '16x9' and shot.get('url'):
                return shot['url']
        for shot in image_set:
            if isinstance(shot, dict) and shot.get('url'):
                return shot['url']
    return thumb_fallback


def fetch_video_row(slug: str) -> dict | None:
    html = fetch(f'https://www.ted.com/talks/{slug}').decode('utf-8', 'ignore')
    m = NEXT_DATA_RE.search(html)
    if not m:
        return None
    data = json.loads(m.group(1))
    v = (data.get('props') or {}).get('pageProps', {}).get('videoData') or {}
    if not v:
        return None
    source_id = str(v.get('id') or '').strip()
    real_slug = (v.get('slug') or slug).strip()
    title = (v.get('title') or '').strip()
    speaker = (v.get('presenterDisplayName') or '').strip()
    if not (source_id and real_slug and title and speaker):
        return None
    pd_raw = v.get('playerData') or '{}'
    pd = json.loads(pd_raw) if isinstance(pd_raw, str) else pd_raw
    speakers = (v.get('speakers') or {}).get('nodes') or []
    speaker_slug = speakers[0].get('slug') if speakers else None
    topics = (v.get('topics') or {}).get('nodes') or []
    topics_json = json.dumps([n.get('name') for n in topics if n.get('name')])
    image = pick_image(v.get('primaryImageSet'), pd.get('thumb'))
    pub_raw = pd.get('published')
    pub_str = str(pub_raw) if pub_raw is not None else ''
    rec_raw = v.get('recordedOn')
    rec_str = str(rec_raw) if rec_raw is not None else ''
    return {
        'source_id': source_id,
        'slug': real_slug,
        'title': title[:260],
        'speaker': speaker[:180],
        'speaker_slug': speaker_slug,
        'event': v.get('videoContext'),
        'talk_type': (v.get('type') or {}).get('name'),
        'duration_seconds': pd.get('duration'),
        'published_at': pub_str[:20] or None,
        'recorded_on': rec_str[:20] or None,
        'views': None,
        'image': image,
        'canonical_url': f'https://www.ted.com/talks/{real_slug}',
        'description': (v.get('description') or '')[:5000] or None,
        'transcript': None,
        'topics_json': topics_json,
        'recommended_json': None,
    }


def main():
    con = open_db(SITE)
    cur = con.cursor()
    existing_slug = {r[0] for r in cur.execute('SELECT slug FROM talk')}
    existing_sid = {r[0] for r in cur.execute('SELECT source_id FROM talk')}
    before = upsert_count(con, 'talk')
    print(f'before: {before} talks')

    # 1) Enumerate candidate slugs across recent sitemaps.
    pool: list[str] = []
    seen = set(existing_slug)
    for y in YEARS:
        try:
            slugs = list_sitemap_slugs(y)
        except Exception as e:
            print(f'  sitemap {y}: fail {e}')
            continue
        new = [s for s in slugs if s not in seen]
        for s in new:
            seen.add(s)
        pool.extend(new)
        print(f'  sitemap {y}: {len(slugs)} URLs, {len(new)} new')
        time.sleep(0.3)
    print(f'candidate pool: {len(pool)} slugs (cap {MAX_NEW})')

    # 2) Fetch each talk page, insert.
    added = 0
    for slug in pool[: MAX_NEW * 2]:
        if added >= MAX_NEW:
            break
        try:
            row = fetch_video_row(slug)
        except Exception as e:
            print(f'  {slug}: fetch fail {e}')
            time.sleep(0.8)
            continue
        if row is None or row['source_id'] in existing_sid:
            continue
        if insert_or_ignore(con, 'talk', row) is not None:
            existing_sid.add(row['source_id'])
            added += 1
            periodic_commit(con, added, every=50)
            if added % 25 == 0:
                print(f'  progress: +{added}')
        time.sleep(PER_TALK_SLEEP)

    con.commit()
    after = upsert_count(con, 'talk')
    print(f'after: {after} (+{added})')
    assert_image_diversity(con, 'talk', 'image')
    con.close()


if __name__ == '__main__':
    main()
