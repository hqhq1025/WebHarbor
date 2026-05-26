#!/usr/bin/env python3
"""Download movie posters + celebrity headshots.

Replaces download_posters.py + download_people.py with a single pipeline that
reads the slug lists directly from seed_data.py — no scraped_data/*.json dep.

- Posters: scraped from rottentomatoes.com/m/<slug> (resizing.flixster.com CDN).
- People: Wikipedia summary REST API → thumbnail.source. RT itself frequently
  has empty <og:image> for actor pages so Wikipedia is the more reliable source.
"""
import os
import re
import sys
import json
import subprocess
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_data import MOVIES, PERSONS  # noqa: E402

POSTER_DIR = "static/images/posters"
PEOPLE_DIR = "static/images/people"
os.makedirs(POSTER_DIR, exist_ok=True)
os.makedirs(PEOPLE_DIR, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

# Wikimedia rejects generic Chrome UAs with 429. Their UA policy requires
# something identifying the tool + a contact URL.
WIKI_UA = ("WebHarborImageFetch/1.0 "
           "(+https://huggingface.co/datasets/ChilleD/WebHarbor; "
           "research mirror) curl/8")

# Base64 fragments embedded in the flixster image path (decodes to
# 'prd-ems-assets/movies/' and 'prd-ems-assets/celebrities/').
MOVIE_PAT  = re.compile(r'https://resizing\.flixster\.com/[^"\s]+(?:bW92aWVzL|bW92aWV)[^"\s]*')
CELEB_PAT  = re.compile(r'https://resizing\.flixster\.com/[^"\s]+(?:Y2VsZWJyaXRpZXMv|Y2VsZWJyaXRpZX)[^"\s]*')


def fetch(url, timeout=15, ua=UA):
    r = subprocess.run(
        ['curl', '-sL', '-A', ua, '--compressed',
         '--connect-timeout', '8', '--max-time', str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    return r.stdout if r.returncode == 0 else ''


def download(url, outpath, timeout=20, ua=UA, retries=2):
    for attempt in range(retries + 1):
        r = subprocess.run(
            ['curl', '-sL', '-A', ua, '--compressed', '-o', outpath,
             '--connect-timeout', '8', '--max-time', str(timeout), url],
            capture_output=True, timeout=timeout + 5,
        )
        if r.returncode != 0 or not os.path.exists(outpath):
            if os.path.exists(outpath):
                os.remove(outpath)
            continue
        if os.path.getsize(outpath) < 1500:
            os.remove(outpath)
            continue
        # Reject HTML error pages that come back as 200 (Wikimedia 429, etc.).
        with open(outpath, 'rb') as f:
            head = f.read(64)
        if head.lstrip().lower().startswith(b'<!doctype') or head.lstrip().startswith(b'<html'):
            os.remove(outpath)
            # back off before retry — 429 needs breathing room
            __import__('time').sleep(2 + attempt * 3)
            continue
        return True
    return False


def pick_largest(urls):
    """Choose the largest-resolution variant by scanning for /<W>x<H>/ marker."""
    def area(u):
        m = re.search(r'/(\d+)x(\d+)/', u)
        if m:
            return int(m.group(1)) * int(m.group(2))
        return 0
    return max(urls, key=area) if urls else None


def get_movie_poster(slug):
    outpath = f"{POSTER_DIR}/{slug}.jpg"
    if os.path.exists(outpath) and os.path.getsize(outpath) > 1500:
        return slug, True, 'cached'
    html = fetch(f"https://www.rottentomatoes.com/m/{slug}")
    if not html:
        return slug, False, 'no_html'
    urls = MOVIE_PAT.findall(html)
    if not urls:
        # Try the search page as fallback
        return slug, False, 'no_url'
    target = pick_largest(urls)
    ok = download(target, outpath)
    return slug, ok, ('ok' if ok else 'dl_fail')


def get_person_photo(slug, name):
    """Get celebrity photo via Wikipedia summary REST API.

    Tries the slug-derived title first (e.g. "Aaron_Eckhart"), then the raw
    name with spaces replaced. Strategy mirrors what worked manually for a
    handful of test cases.
    """
    outpath = f"{PEOPLE_DIR}/{slug}.jpg"
    if os.path.exists(outpath) and os.path.getsize(outpath) > 1500:
        return slug, True, 'cached'

    # Build candidate Wikipedia titles
    title_from_name = name.replace(' ', '_')
    title_from_slug = '_'.join(p.capitalize() for p in slug.split('_'))
    candidates = []
    for t in (title_from_name, title_from_slug, f"{title_from_name}_(actor)"):
        if t not in candidates:
            candidates.append(t)

    photo_url = None
    for title in candidates:
        raw = fetch(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                    timeout=10, ua=WIKI_UA)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        # Skip disambiguation pages — they often have a generic icon
        if data.get('type') == 'disambiguation':
            continue
        # Prefer thumbnail (served via /thumb/ which Wikimedia explicitly says
        # tools should use; originalimage hits the rate-limited path).
        url = (data.get('thumbnail') or {}).get('source') \
            or (data.get('originalimage') or {}).get('source')
        if url:
            photo_url = url
            break

    if not photo_url:
        return slug, False, 'no_wiki_image'
    ok = download(photo_url, outpath, ua=WIKI_UA)
    return slug, ok, ('ok' if ok else 'dl_fail')


def run(label, items, fn, workers=12, with_name=False):
    print(f"[{label}] {len(items)} items, {workers} workers", flush=True)
    ok = 0
    failed = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        if with_name:
            futures = [ex.submit(fn, slug, name) for slug, name in items]
        else:
            futures = [ex.submit(fn, slug) for slug in items]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            slug, success, reason = fut.result()
            if success:
                ok += 1
            else:
                failed.append((slug, reason))
            if i % 25 == 0:
                print(f"  [{label}] {i}/{len(items)}  ok={ok}  fail={len(failed)}", flush=True)
    print(f"[{label}] DONE  ok={ok}/{len(items)}  fail={len(failed)}", flush=True)
    if failed:
        print(f"  [{label}] first failures: {failed[:10]}", flush=True)
    return ok, failed


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if target in ('all', 'posters'):
        movie_slugs = [m['slug'] for m in MOVIES]
        run('posters', movie_slugs, get_movie_poster)

    if target in ('all', 'people'):
        person_items = [(p['slug'], p['name']) for p in PERSONS]
        # Low concurrency — Wikimedia 429s aggressively above ~5 parallel.
        run('people', person_items, get_person_photo, workers=4, with_name=True)
