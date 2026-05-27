"""One-shot real-image downloader for the Eventbrite mirror.

Pulls 500+ category-themed real photos from loremflickr (Flickr-backed) and
saves them under ``static/images/``. Idempotent — skips any file that already
exists. Deterministic: each filename's content depends only on its loremflickr
``lock`` parameter, which is a stable index derived from the filename.

Not part of the seed_database()/seed_benchmark_users() path — this script runs
once, the resulting images ship via HF dataset alongside instance_seed/.

Run:
    python3 scripts_download_images.py
"""
import os, sys, time, concurrent.futures, urllib.request, urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(BASE, 'static', 'images')
os.makedirs(OUT, exist_ok=True)

# Category -> (tag string, count). Counts are sized to mimic real Eventbrite
# distribution (lots of music, fewer school/auto). Total ~520 + ~30 organizer
# avatars + ~30 city banners + ~20 hero banners.
CATEGORIES = [
    ('music',        'concert,music,stage',           50),
    ('business',     'conference,business,meeting',   35),
    ('food-drink',   'food,wine,restaurant',          35),
    ('arts',         'theater,art,performance',       30),
    ('holiday',      'holiday,fireworks,celebration', 22),
    ('health',       'yoga,wellness,fitness',         30),
    ('hobbies',      'craft,hobby,workshop',          25),
    ('family',       'family,kids,children',          22),
    ('sports',       'sports,running,basketball',     30),
    ('travel',       'hiking,travel,outdoor',         25),
    ('charity',      'charity,volunteer,donation',    22),
    ('spirituality', 'meditation,spiritual,candle',   18),
    ('community',    'community,festival,crowd',      25),
    ('fashion',      'fashion,runway,style',          18),
    ('film',         'cinema,movie,screen',           20),
    ('home',         'plants,gardening,home',         18),
    ('auto',         'cars,classic,vintage',          15),
    ('school',       'school,classroom,education',    15),
]

ORGANIZER_TAGS = ['brand,logo,abstract', 'office,creative,design']
CITY_TAGS = {
    'ny--new-york':       'newyork,manhattan,skyline',
    'ca--los-angeles':    'losangeles,hollywood,city',
    'il--chicago':        'chicago,skyline',
    'tx--houston':        'houston,texas',
    'tx--austin':         'austin,texas,downtown',
    'ca--san-francisco':  'sanfrancisco,goldengate',
    'wa--seattle':        'seattle,spaceneedle',
    'co--denver':         'denver,colorado,mountains',
    'ma--boston':         'boston,massachusetts',
    'dc--washington':     'washington,dc,capitol',
    'ga--atlanta':        'atlanta,georgia,skyline',
    'fl--miami':          'miami,florida,beach',
    'pa--philadelphia':   'philadelphia,liberty',
    'mn--minneapolis':    'minneapolis,minnesota',
    'or--portland':       'portland,oregon',
    'az--phoenix':        'phoenix,arizona,desert',
    'nv--las-vegas':      'lasvegas,nevada,strip',
    'ca--san-diego':      'sandiego,california,coast',
    'tn--nashville':      'nashville,music,city',
    'la--new-orleans':    'neworleans,louisiana,jazz',
    'mi--detroit':        'detroit,michigan',
    'nc--raleigh':        'raleigh,northcarolina',
    'md--baltimore':      'baltimore,harbor',
}

HERO_TAGS = [
    ('hero_summer_festival', 'festival,outdoor,summer'),
    ('hero_concert_crowd',   'concert,crowd,lights'),
    ('hero_brunch',          'brunch,food,table'),
    ('hero_yoga_park',       'yoga,park,sunset'),
    ('hero_conference',      'conference,stage,keynote'),
    ('hero_block_party',     'street,party,festival'),
    ('hero_rooftop',         'rooftop,city,nightlife'),
    ('hero_workshop',        'workshop,hands,craft'),
    ('hero_charity_run',     'running,marathon,charity'),
    ('hero_artgallery',      'art,gallery,exhibit'),
    ('hero_filmnight',       'cinema,outdoor,screening'),
    ('hero_pridenight',      'pride,parade,rainbow'),
]


def url(width, height, tags, lock):
    """loremflickr URL — `lock` makes it deterministic across calls."""
    return f'https://loremflickr.com/{width}/{height}/{tags}/all?lock={lock}'


def fetch(target_path, src_url, min_bytes=4000):
    if os.path.exists(target_path) and os.path.getsize(target_path) > min_bytes:
        return ('skip', target_path)
    try:
        req = urllib.request.Request(src_url, headers={
            'User-Agent': 'Mozilla/5.0 (WebHarbor seed)'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < min_bytes:
            return ('small', target_path)
        with open(target_path, 'wb') as f:
            f.write(data)
        return ('ok', target_path)
    except Exception as e:
        return ('err:' + type(e).__name__, target_path)


def build_jobs():
    jobs = []
    for cat, tags, n in CATEGORIES:
        for i in range(n):
            name = f'evt_{cat}_{i:03d}.jpg'
            jobs.append((os.path.join(OUT, name),
                         url(800, 450, tags, lock=hash(name) & 0x7FFFFFFF)))
    for ci, tags in enumerate(ORGANIZER_TAGS * 18):  # 36 organizer textures
        name = f'org_texture_{ci:03d}.jpg'
        jobs.append((os.path.join(OUT, name),
                     url(400, 400, tags, lock=hash(name) & 0x7FFFFFFF)))
    for slug, tags in CITY_TAGS.items():
        name = f'city_{slug}.jpg'
        jobs.append((os.path.join(OUT, name),
                     url(1200, 480, tags, lock=hash(name) & 0x7FFFFFFF)))
    for name_part, tags in HERO_TAGS:
        name = f'{name_part}.jpg'
        jobs.append((os.path.join(OUT, name),
                     url(1600, 600, tags, lock=hash(name) & 0x7FFFFFFF)))
    return jobs


def main():
    jobs = build_jobs()
    print(f'Total jobs: {len(jobs)}')
    ok = skip = err = 0
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futs = [pool.submit(fetch, p, u) for p, u in jobs]
        for i, fu in enumerate(concurrent.futures.as_completed(futs)):
            status, path = fu.result()
            if status == 'ok':         ok += 1
            elif status == 'skip':     skip += 1
            else:                      err += 1
            if (i + 1) % 25 == 0:
                print(f'  [{i+1}/{len(jobs)}] ok={ok} skip={skip} err={err} elapsed={time.time()-t0:.0f}s')
    print(f'Done. ok={ok} skip={skip} err={err} in {time.time()-t0:.0f}s')
    print(f'Images directory: {OUT}')
    print(f'Files now: {len(os.listdir(OUT))}')


if __name__ == '__main__':
    main()
