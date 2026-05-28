#!/usr/bin/env python3
"""Extend Coursera courses via /browse/<subject> Apollo state.

Target: 23055 already large (mostly synthetic seed); script still ships
        for reproducibility + a few hundred *real* upstream Specializations
        with real ratings/partners that Phase 5b can scrape covers for.
Source: coursera.org/browse/<subject> is server-rendered with
        `window.__APOLLO_STATE__ = {...};` containing Specialization_Specialization
        entities + ProductCard_ProductCard records (rating/review_count) +
        Partner_Partner records.

INSERT OR IGNORE on slug.
Partner_id resolved via existing partners.name table; NULL on miss.
"""
from __future__ import annotations
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

SITE = 'coursera'
BROWSE_URL = 'https://www.coursera.org/browse/{subject}'
SUBJECTS = [
    'data-science', 'business', 'computer-science', 'information-technology',
    'language-learning', 'health', 'math-and-logic', 'personal-development',
    'physical-science-and-engineering', 'social-sciences', 'arts-and-humanities',
]

APOLLO_RE = re.compile(r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});', re.S)

PRODUCT_TYPE_MAP = {
    'PROFESSIONAL_CERTIFICATE': 'Professional Certificate',
    'SPECIALIZATION': 'Specialization',
    'COURSE': 'Course',
    'DEGREE': 'Degree',
    'GUIDED_PROJECT': 'Guided Project',
}
LEVEL_MAP = {
    'BEGINNER': 'Beginner', 'INTERMEDIATE': 'Intermediate',
    'ADVANCED': 'Advanced', 'MIXED': 'Mixed',
}


def parse_apollo(html: str) -> dict:
    m = APOLLO_RE.search(html)
    return json.loads(m.group(1)) if m else {}


def harvest_subject(subject: str) -> list[dict]:
    html = fetch(BROWSE_URL.format(subject=subject)).decode('utf-8', 'ignore')
    state = parse_apollo(html)
    if not state:
        return []
    # Index ProductCard by id for rating lookups (canonical -> the entity id)
    pcards = {}
    for k, v in state.items():
        if isinstance(v, dict) and v.get('__typename') == 'ProductCard_ProductCard':
            pa = v.get('productTypeAttributes') or {}
            ref = (pa.get('canonical') or {}).get('__ref') or ''
            target_id = ref.split(':', 1)[1] if ':' in ref else v.get('id')
            pcards[target_id] = {
                'rating': pa.get('rating'),
                'reviewCount': pa.get('reviewCount'),
                'isFree': pa.get('isFree'),
                'marketingProductType': v.get('marketingProductType'),
            }

    candidates = []
    for k, v in state.items():
        if not (isinstance(v, dict) and v.get('__typename') == 'Specialization_Specialization'):
            continue
        slug = (v.get('slug') or '').strip()
        title = (v.get('name') or '').strip()
        if not (slug and title):
            continue
        partner_refs = v.get('partners') or []
        partner_names = []
        for pref in partner_refs:
            ref = (pref or {}).get('__ref') or ''
            tgt = state.get(ref)
            if isinstance(tgt, dict) and tgt.get('name'):
                partner_names.append(tgt['name'])
        pc = pcards.get(v.get('id'), {})
        candidates.append({
            'slug': slug,
            'title': title,
            'partner_names': partner_names,
            'course_type': PRODUCT_TYPE_MAP.get(pc.get('marketingProductType'), 'Specialization'),
            'level': LEVEL_MAP.get(v.get('difficultyLevel')),
            'category': subject.replace('-', ' ').title(),
            'rating': pc.get('rating'),
            'review_count': pc.get('reviewCount'),
            'is_free': 1 if pc.get('isFree') else 0,
            'image_url': v.get('cardImageUrl'),
        })
    return candidates


def main():
    con = open_db(SITE)
    cur = con.cursor()
    existing = {r[0] for r in cur.execute('SELECT slug FROM courses')}
    partner_map = {(r[1] or '').strip().lower(): r[0]
                   for r in cur.execute('SELECT id, name FROM partners')}
    before = upsert_count(con, 'courses')
    print(f'before: {before} courses, {len(partner_map)} partners indexed')

    added = 0
    for subject in SUBJECTS:
        try:
            harvested = harvest_subject(subject)
        except Exception as e:
            print(f'  {subject}: fetch fail {e}')
            continue
        sub_added = 0
        for c in harvested:
            if c['slug'] in existing:
                continue
            partner_id = None
            for pn in c['partner_names']:
                partner_id = partner_map.get(pn.strip().lower())
                if partner_id is not None:
                    break
            row = {
                'title': c['title'][:300],
                'slug': c['slug'][:300],
                'partner_id': partner_id,
                'course_type': c['course_type'],
                'level': c['level'],
                'category': c['category'][:100],
                'rating': c['rating'],
                'review_count': c['review_count'],
                'is_free': c['is_free'],
                'has_certificate': 1 if c['course_type'] != 'Course' else None,
                'instructor': (c['partner_names'][0] if c['partner_names'] else None),
            }
            # Coursera card image stored separately (no image col on courses) —
            # Phase 5b handles thumbs via instructor/cover scrape; we leave cover
            # in description-less, but record cardImageUrl into testimonials_json
            # is wrong; just drop and let 5b scrape from /browse/<subject>/<slug>.
            if insert_or_ignore(con, 'courses', row) is not None:
                existing.add(c['slug'])
                added += 1
                sub_added += 1
                periodic_commit(con, added, every=50)
        print(f'  {subject}: +{sub_added}')
        time.sleep(0.6)

    con.commit()
    after = upsert_count(con, 'courses')
    print(f'after: {after} (+{added})')
    # No image column on courses; skip diversity gate.
    con.close()


if __name__ == '__main__':
    main()
