"""Wave 1 enhanced downloader for the Eventbrite mirror.

Pulls real photos for every event category, organizer texture, city banner, and
hero banner, validates them with Pillow, and re-encodes to <=200 KB JPEG so the
on-disk footprint stays reasonable.

Sources (in priority order per slot):
  1. loremflickr — category-tagged real Flickr photos (e.g. concert/music/stage)
  2. picsum.photos — deterministic real photos via seed (fallback, no tags)

The naming scheme matches the existing helpers in routes_more.py:
  evt_<category>_NNN.jpg   (pool, deterministic-pick per event slug hash)
  org_texture_NNN.jpg      (pool, deterministic-pick per organizer slug hash)
  city_<slug>.jpg          (one per city)
  hero_<name>.jpg          (one per hero banner)

Idempotent — skips any file that already exists at >=5 KB.

Run:
    python3 scripts_download_images_v2.py
"""
import io
import os
import sys
import time
import concurrent.futures
import urllib.request
import urllib.error
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'static', 'images')
os.makedirs(OUT, exist_ok=True)

# Category -> (loremflickr tag string, count per category).
# Counts are sized so md5(slug) % len(pool) gives wide variety per event.
CATEGORIES = [
    ('music',        'concert,music,stage,band',        35),
    ('business',     'conference,business,meeting,corporate', 35),
    ('food-drink',   'food,wine,restaurant,gourmet',    35),
    ('arts',         'theater,art,performance,gallery', 32),
    ('holiday',      'holiday,fireworks,celebration,parade', 28),
    ('health',       'yoga,wellness,fitness,meditation', 32),
    ('hobbies',      'craft,hobby,workshop,handmade',   32),
    ('family',       'family,kids,children,playground', 30),
    ('sports',       'sports,running,basketball,soccer', 30),
    ('travel',       'hiking,travel,outdoor,landscape', 32),
    ('charity',      'charity,volunteer,donation,community', 28),
    ('spirituality', 'meditation,spiritual,candle,zen', 28),
    ('community',    'community,festival,crowd,gathering', 30),
    ('fashion',      'fashion,runway,style,model',      28),
    ('film',         'cinema,movie,screen,projection',  28),
    ('home',         'plants,gardening,home,interior',  28),
    ('auto',         'cars,classic,vintage,motorcycle', 26),
    ('school',       'school,classroom,education,books', 26),
]

ORGANIZER_TAGS = [
    ('brand,logo,abstract,design',  18),
    ('office,creative,workspace,modern', 18),
]

CITY_TAGS = {
    'ny--new-york':       'newyork,manhattan,skyline,city',
    'ca--los-angeles':    'losangeles,hollywood,city,palm',
    'il--chicago':        'chicago,skyline,michigan',
    'tx--houston':        'houston,texas,downtown',
    'tx--austin':         'austin,texas,downtown',
    'ca--san-francisco':  'sanfrancisco,goldengate,bridge',
    'wa--seattle':        'seattle,spaceneedle,pacific',
    'co--denver':         'denver,colorado,mountains',
    'ma--boston':         'boston,massachusetts,harbor',
    'dc--washington':     'washington,dc,capitol,monument',
    'ga--atlanta':        'atlanta,georgia,skyline',
    'fl--miami':          'miami,florida,beach,ocean',
    'pa--philadelphia':   'philadelphia,liberty,bell',
    'mn--minneapolis':    'minneapolis,minnesota,bridge',
    'or--portland':       'portland,oregon,rose',
    'az--phoenix':        'phoenix,arizona,desert,cactus',
    'nv--las-vegas':      'lasvegas,nevada,strip,neon',
    'ca--san-diego':      'sandiego,california,coast,harbor',
    'tn--nashville':      'nashville,music,city,tennessee',
    'la--new-orleans':    'neworleans,louisiana,jazz,bourbon',
    'mi--detroit':        'detroit,michigan,downtown',
    'nc--raleigh':        'raleigh,northcarolina,downtown',
    'md--baltimore':      'baltimore,harbor,maryland',
}

HERO_TAGS = [
    ('hero_summer_festival', 'festival,outdoor,summer,crowd'),
    ('hero_concert_crowd',   'concert,crowd,lights,stage'),
    ('hero_brunch',          'brunch,food,table,morning'),
    ('hero_yoga_park',       'yoga,park,sunset,outdoor'),
    ('hero_conference',      'conference,stage,keynote,audience'),
    ('hero_block_party',     'street,party,festival,neighborhood'),
    ('hero_rooftop',         'rooftop,city,nightlife,bar'),
    ('hero_workshop',        'workshop,hands,craft,makerspace'),
    ('hero_charity_run',     'running,marathon,charity,race'),
    ('hero_artgallery',      'art,gallery,exhibit,museum'),
    ('hero_filmnight',       'cinema,outdoor,screening,movie'),
    ('hero_pridenight',      'pride,parade,rainbow,celebration'),
]

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) WebHarbor/1.0'}
MIN_BYTES_RAW = 5000
TARGET_MAX_KB = 200


def stable_lock(name):
    """Deterministic 32-bit lock derived from filename — same across runs."""
    import hashlib
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def loremflickr_url(width, height, tags, lock):
    return f'https://loremflickr.com/{width}/{height}/{tags}/all?lock={lock}'


def picsum_url(width, height, seed):
    return f'https://picsum.photos/seed/{seed}/{width}/{height}'


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get('Content-Type', '')


def reencode_jpeg(data, target_max_kb=TARGET_MAX_KB):
    """Open with Pillow (validates it's a real image), re-encode JPEG with
    quality reduction until size <= target_max_kb. Returns raw JPEG bytes or
    raises ValueError if image is invalid."""
    img = Image.open(io.BytesIO(data))
    img.load()  # forces decode; raises on truncated/corrupt
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    # Try descending quality.
    for q in (88, 82, 75, 68, 60, 52, 45):
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=q, optimize=True, progressive=True)
        b = buf.getvalue()
        if len(b) <= target_max_kb * 1024:
            return b
    # Image is huge — return the smallest we got.
    return b


def fetch_one(target_path, primary_url, fallback_url):
    """Try primary URL; on failure, fallback. Validate + re-encode. Return
    (status, target_path, bytes_written, source)."""
    if os.path.exists(target_path) and os.path.getsize(target_path) >= MIN_BYTES_RAW:
        return ('skip', target_path, os.path.getsize(target_path), 'cache')

    last_err = None
    for src_name, url in (('primary', primary_url), ('fallback', fallback_url)):
        if not url:
            continue
        try:
            raw, ctype = http_get(url)
            if len(raw) < 1000:
                last_err = f'{src_name}-too-small({len(raw)})'
                continue
            try:
                jpeg = reencode_jpeg(raw)
            except Exception as e:
                last_err = f'{src_name}-bad-image({type(e).__name__})'
                continue
            if len(jpeg) < MIN_BYTES_RAW:
                last_err = f'{src_name}-encoded-too-small'
                continue
            with open(target_path, 'wb') as f:
                f.write(jpeg)
            return ('ok', target_path, len(jpeg), src_name)
        except urllib.error.HTTPError as e:
            last_err = f'{src_name}-http{e.code}'
        except Exception as e:
            last_err = f'{src_name}-{type(e).__name__}'
    return (f'err:{last_err}', target_path, 0, 'none')


def build_jobs():
    jobs = []
    # Per-category event pools.
    for cat, tags, n in CATEGORIES:
        for i in range(n):
            name = f'evt_{cat}_{i:03d}.jpg'
            lock = stable_lock(name)
            primary = loremflickr_url(800, 450, tags, lock)
            fallback = picsum_url(800, 450, f'eb_{cat}_{i:03d}')
            jobs.append((os.path.join(OUT, name), primary, fallback))
    # Organizer texture pools.
    for variant_idx, (tags, n) in enumerate(ORGANIZER_TAGS):
        for i in range(n):
            name = f'org_texture_{variant_idx * 18 + i:03d}.jpg'
            lock = stable_lock(name)
            primary = loremflickr_url(400, 400, tags, lock)
            fallback = picsum_url(400, 400, f'eb_org_{variant_idx}_{i:03d}')
            jobs.append((os.path.join(OUT, name), primary, fallback))
    # City banners.
    for slug, tags in CITY_TAGS.items():
        name = f'city_{slug}.jpg'
        lock = stable_lock(name)
        primary = loremflickr_url(1200, 480, tags, lock)
        fallback = picsum_url(1200, 480, f'eb_city_{slug}')
        jobs.append((os.path.join(OUT, name), primary, fallback))
    # Hero banners.
    for name_part, tags in HERO_TAGS:
        name = f'{name_part}.jpg'
        lock = stable_lock(name)
        primary = loremflickr_url(1600, 600, tags, lock)
        fallback = picsum_url(1600, 600, f'eb_{name_part}')
        jobs.append((os.path.join(OUT, name), primary, fallback))
    return jobs


def main():
    jobs = build_jobs()
    print(f'Total jobs: {len(jobs)}')
    stats = {'ok': 0, 'skip': 0, 'err': 0, 'primary': 0, 'fallback': 0,
             'total_bytes': 0}
    errors = []
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(fetch_one, p, u, f) for p, u, f in jobs]
        for i, fu in enumerate(concurrent.futures.as_completed(futs)):
            status, path, nbytes, source = fu.result()
            if status == 'ok':
                stats['ok'] += 1
                stats['total_bytes'] += nbytes
                stats[source] = stats.get(source, 0) + 1
            elif status == 'skip':
                stats['skip'] += 1
                stats['total_bytes'] += nbytes
            else:
                stats['err'] += 1
                errors.append((os.path.basename(path), status))
            if (i + 1) % 50 == 0:
                print(f'  [{i+1}/{len(jobs)}] ok={stats["ok"]} skip={stats["skip"]} '
                      f'err={stats["err"]} elapsed={time.time()-t0:.0f}s')
    elapsed = time.time() - t0
    print()
    print(f'Done in {elapsed:.0f}s')
    print(f'  ok:       {stats["ok"]}  (primary={stats.get("primary",0)} '
          f'fallback={stats.get("fallback",0)})')
    print(f'  skip:     {stats["skip"]} (already on disk)')
    print(f'  err:      {stats["err"]}')
    print(f'  total MB: {stats["total_bytes"]/1024/1024:.1f}')
    print(f'Images directory: {OUT}')
    print(f'Files now: {len(os.listdir(OUT))}')
    if errors:
        print()
        print(f'First 20 errors:')
        for name, st in errors[:20]:
            print(f'  {name}: {st}')


if __name__ == '__main__':
    main()
