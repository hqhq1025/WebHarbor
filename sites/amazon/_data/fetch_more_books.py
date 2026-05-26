#!/usr/bin/env python3
"""One-shot fetch script: pull additional Open Library books for R3 expansion.

Outputs sites/amazon/_data/openlib_books_r3.json — a list of dicts with the
same shape as openlib_books.json (title, author, genre, year, edition_count,
cover_id, key). De-dups against openlib_books.json so the matrix expansion
adds *new* titles.
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))

# Subject -> internal genre label (must match GENRE_PRICING in seed_bulk.py).
# Picked to add genres NOT in the first pass + double up on popular ones.
SUBJECTS = [
    ('horror', 'Thriller'),
    ('detective_and_mystery_stories', 'Mystery'),
    ('classics', 'Fiction'),
    ('adventure', 'Fiction'),
    ('historical_fiction', 'Fiction'),
    ('short_stories', 'Fiction'),
    ('graphic_novel', 'Fiction'),
    ('drama', 'Fiction'),
    ('fantasy_fiction', 'Fantasy'),
    ('dragons', 'Fantasy'),
    ('wizards', 'Fantasy'),
    ('time_travel', 'Science Fiction'),
    ('space_opera', 'Science Fiction'),
    ('dystopian', 'Science Fiction'),
    ('cyberpunk', 'Science Fiction'),
    ('mathematics', 'Science'),
    ('physics', 'Science'),
    ('biology', 'Science'),
    ('chemistry', 'Science'),
    ('astronomy', 'Science'),
    ('economics', 'Business'),
    ('finance', 'Business'),
    ('management', 'Business'),
    ('entrepreneurship', 'Business'),
    ('cooking', 'Cookbook'),
    ('baking', 'Cookbook'),
    ('italian_cooking', 'Cookbook'),
    ('vegan_cooking', 'Cookbook'),
    ('memoir', 'Biography'),
    ('autobiography', 'Biography'),
    ('us_history', 'History'),
    ('world_history', 'History'),
    ('ancient_history', 'History'),
    ('children_s_picture_books', 'Children'),
    ('young_adult_fiction', 'Young Adult'),
    ('photography', 'Art'),
    ('architecture', 'Art'),
    ('music', 'Art'),
    ('film', 'Art'),
    ('travel_guide', 'Travel'),
    ('hiking', 'Travel'),
    ('religion', 'Philosophy'),
    ('ethics', 'Philosophy'),
    ('meditation', 'Self-Help'),
    ('productivity', 'Self-Help'),
    ('happiness', 'Self-Help'),
    ('relationships', 'Psychology'),
    ('parenting', 'Psychology'),
    ('python_(computer_program_language)', 'Programming'),
    ('javascript', 'Programming'),
    ('machine_learning', 'Programming'),
    ('algorithms', 'Programming'),
    ('software_engineering', 'Programming'),
    ('poetry', 'Poetry'),
    ('love_poetry', 'Poetry'),
]

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')


def fetch_subject(subj, limit=40):
    url = f'https://openlibrary.org/subjects/{subj}.json?limit={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f'  ! {subj}: {e}', file=sys.stderr)
        return None


def main():
    existing_path = os.path.join(BASE, 'openlib_books.json')
    out_path = os.path.join(BASE, 'openlib_books_r3.json')
    seen = set()
    if os.path.exists(existing_path):
        for b in json.load(open(existing_path)):
            seen.add((b.get('title') or '').strip().lower())
    if os.path.exists(out_path):
        for b in json.load(open(out_path)):
            seen.add((b.get('title') or '').strip().lower())

    collected = []
    if os.path.exists(out_path):
        collected = json.load(open(out_path))

    for subj, genre in SUBJECTS:
        data = fetch_subject(subj, limit=40)
        if not data:
            continue
        added = 0
        for w in data.get('works', []):
            title = (w.get('title') or '').strip()
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            authors = w.get('authors') or []
            author = (authors[0].get('name') if authors else 'Anonymous')
            year = w.get('first_publish_year') or 0
            cover_id = w.get('cover_id') or 0
            collected.append({
                'title': title,
                'author': author,
                'genre': genre,
                'year': year,
                'edition_count': w.get('edition_count') or 1,
                'cover_id': cover_id,
                'key': w.get('key', ''),
            })
            added += 1
        print(f'  {subj:40s} +{added} (running total {len(collected)})')
        # Persist progress each subject
        json.dump(collected, open(out_path, 'w'), indent=1, ensure_ascii=False)
        time.sleep(1.0)  # be polite

    print(f'Done. Total new books: {len(collected)} → {out_path}')


if __name__ == '__main__':
    main()
