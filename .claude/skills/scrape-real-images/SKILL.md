---
name: scrape-real-images
description: "Source distinct real photographs / logos / artwork for WebHarbor mirror entities at scale. Uses Tavily / WebFetch / public-API mirrors to fetch real upstream imagery, validates that the resulting per-entity image diversity beats the 'top image ≤5% of entities' threshold, and falls back to deterministic SVG generation only when real sourcing fails. Use when an entity table or json gallery has top-image > 30% duplicate (one placeholder reused everywhere), or when filling a new image field for the first time. Triggers: '真扒图', '占位图', 'placeholder image', 'real images for entities', 'image diversity'."
---

# Scrape Real Images — Source distinct upstream imagery, banish placeholders

This skill exists because WebHarbor mirrors look fake fast when 812 cities share one Eiffel Tower image, or 1500 authors share one CS.svg logo. Every entity column that names an image deserves a distinct real photo whenever cheaply possible.

## When to use

- **Phase 1 (clone-website) — MANDATORY for every entity column with an image field**. Before declaring a site clone done, every `<X>.image_url` column must pass `top duplicate ≤ 5%` check. New per-clone checklist item.
- **After deepen/seed pass** when a new image column is populated — verify diversity before declaring done
- **When `image diversity check`** (see `seed-database` skill / `harden-env` gotcha #42) fails — top image > 30%
- **When `document-site-gui` audit notices** "every place_detail page shows the same map snippet"
- **When user reports** "this site looks fake"
- **5 个 P0 站 (2026-05) 实战教训**：fandom 109 角色页用 procedural gradient placeholder / mayo_clinic 220 张程序 SVG / smartasset 0 张真 author 头像 —— 所有这些都因为没在 clone-website 阶段就跑本 skill 而被发现得太晚

Don't use for: pure SVG icon design (use a design tool / gotcha #40 SVG generation), one-off hero images (just commit the file), broken CSS / layout bugs.

## Hard rules

### 1. Top duplicate ≤ 5%

After fix, run:

```python
import sqlite3, collections
con = sqlite3.connect("instance/<site>.db")
rows = [r[0] for r in con.execute('SELECT image_col FROM table WHERE image_col IS NOT NULL')]
top_n = collections.Counter(rows).most_common(1)[0][1]
assert top_n / len(rows) < 0.05, f"top {top_n}/{len(rows)} = {top_n/len(rows):.0%} still too duplicated"
```

5% is the gate. Some duplication is unavoidable (24 cities sharing 1 of 30 stock photos = 3.3% top), but **anything ≥ 30% is broken**.

### 2. Per-entity multi-section diversity

If an entity has multiple "sections" each carrying its own image (like google_map `place_galleries.json` Overview / Visitor Experience / History sections), **each section must have a distinct image**. Don't reuse the same `img_00.png` for all 3.

```python
# good: every entity has ≥len(sections) distinct images
for entity, sections in data.items():
    imgs = sum((s.get('images', []) for s in sections), [])
    assert len(set(imgs)) >= len(sections), f"{entity}: needs ≥{len(sections)} distinct images"
```

### 3. Real upstream pixels — not random color SVG when avoidable

SVG generation is a fallback (gotcha #40). Default to real Tavily/WebFetch scraping first.

### 4. Validate downloaded content

```python
r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 ...'})
if r.status_code != 200: skip
if len(r.content) < 5000: skip   # 1x1 tracking pixel / 404 stub
ct = r.headers.get('content-type', '').lower()
if not any(x in ct for x in ('image/jpeg', 'image/png', 'image/webp', 'image/svg+xml')): skip
```

Reject anything under 5 KB — almost always a tracking pixel, HTML error page, or empty placeholder.

## Tavily as primary source

```python
# Discovery — find real source URLs
results = tavily_search(
    query=f"{entity.name} {kind} photograph hero image",
    num_results=8,
)
# Each result has .image_url (top result image) or .url (page to extract from)
img_candidates = [r.get('image_url') for r in results['results'] if r.get('image_url')]
```

Or use `tavily_extract` if Tavily returns page URLs and you need to harvest their images:

```python
extracted = tavily_extract(urls=[r['url'] for r in results['results'][:5]])
for page in extracted:
    for img in page.get('images', [])[:3]:
        img_candidates.append(img)
```

### Query crafting per domain

| Site type | Good query pattern |
|---|---|
| Place / landmark | `f"{name} attraction landmark photograph"` |
| University / library | `f"{name} interior building photograph"` |
| Brand / store / dealership | `f"{brand} {city} storefront exterior photograph"` |
| Author / person | `f"{name} portrait headshot researcher"` (often returns OK; ORCID-style headshots) |
| Institution / lab | `f"{name} official logo svg"` then visit Wikipedia / official site |
| Product / SKU | `f"{product_name} press image white background"` |
| News / article hero | `f"{headline} news photograph"` |

Tavily throttling: insert `time.sleep(1)` between calls. ~100 queries / minute sustained is fine.

## Wikipedia as fallback (high quality, free)

For famous entities Wikipedia has a high-quality canonical image at:

```
https://en.wikipedia.org/api/rest_v1/page/summary/{Title}
```

Returns JSON with `thumbnail.source` URL. Used in 2026-05 batch for arxiv author headshots, rotten_tomatoes celebrity portraits, ted speaker photos. Throttle ≤4 parallel + set `User-Agent`.

```python
import requests
def wiki_thumb(name):
    title = name.replace(' ', '_')
    r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                     headers={'User-Agent': 'WebHarbor seed/1.0'}, timeout=5)
    if r.status_code == 200:
        return r.json().get('thumbnail', {}).get('source')
```

## Direct CDN scraping (battle-tested per-domain registry)

For known sources, use direct CDN URLs:

| Upstream | Pattern | Note |
|---|---|---|
| **TED talks** | `https://pi.tedcdn.com/r/talkstar-photos.s3.amazonaws.com/uploads/{slug}.jpg` | battle-tested across 480 talks |
| **TMDB (movies/TV)** | API: `https://api.themoviedb.org/3/movie/{id}` → `poster_path` | needs API token |
| **Rotten Tomatoes** | scrape page, regex extract flixster CDN URLs → store in `scraped_data/movies.json` `poster_url` → curl per slug (see `rotten_tomatoes/download_posters.py` for canonical impl, 748 posters) | RT page → flixster CDN |
| **IMDb posters / headshots** | `https://m.media-amazon.com/images/M/{hash}._V1_.jpg` extracted from imdb.com page parse | 4283 images via this path |
| **GitHub avatars** | `https://avatars.githubusercontent.com/u/{user_id}?v=4` | unauth 60/h |
| **HuggingFace avatars** | `https://huggingface.co/avatars/{username}.svg` | works for users + orgs |
| **BoardGameGeek covers** | `https://cf.geekdo-images.com/{hash}__imagepage/img/{path}` extracted from BGG game page meta | 11339 game covers harvested |
| **Fandom (Wikia) images** | `https://static.wikia.nocookie.net/{wiki}/images/{a}/{ab}/{filename}.jpg/revision/latest` OR `https://vignette.wikia.nocookie.net/{wiki-id}/scale-to-width-down/...` — extract from harvest snapshots (1752 URLs for MCU/SW/Genshin) | per-character infobox |
| **Best Buy product** | `https://pisces.bbystatic.com/image2/BestBuy_US/dam/{filename}.jpg` per SKU — extract from PDP page or harvest snapshot | 1113 URLs via Phase 0 |
| **Apple product** | `https://www.apple.com/v/iphone/.../images/...` and `www.apple.com/v/mac/...` | extract from harvest snapshot, 2551 URLs |
| **OpenStreetMap places** | Wikipedia REST summary (above) — most landmarks have Wiki page | google_map used this for 1227 places |
| **MusicBrainz / Discogs covers** | `https://i.discogs.com/{hash}-{size}.jpeg` extracted from release page | works for indie / non-mainstream |

See `data-sources.md` in `seed-database/` for the full battle-tested registry. Also see `~/webvoyager-analysis/real_components/snapshots/<site>/_image_urls.jsonl` for harvested-URL alternative.

## Wikipedia Commons category-page HTML scrape (the rate-limit-friendly trick)

For medical / anatomy / nature / building-type imagery, the Wikipedia REST API hits rate limits fast. **Workaround**: scrape Wikipedia Commons category pages directly (mayo_clinic battle-tested in `_fetch_images.py`):

```python
# Fetch e.g. https://commons.wikimedia.org/wiki/Category:Anatomy_of_the_human_heart
# Parse <a class="image"><img src=".../thumb/.../{file}.jpg/200px-..."> from gallery
# Rewrite thumb URL to original (strip the /thumb/.../200px- part)
# Download with browser UA + Referer
```

Categories with broad public-domain imagery:
- Anatomy / medical: `Anatomy_of_the_human_heart` / `Lungs` / `Human_brain` / `Digestive_system` / etc.
- Buildings: `<City>_skylines` / `Universities_in_<state>` / `Hospitals_in_<state>`
- Nature: `National_parks_of_the_United_States` / `<Animal>_breeds`

## Generic per-entity sources (lighter weight than Tavily)

When Tavily quota is exhausted or the entity is not famous enough for Wikipedia:

| Source | URL pattern | Use case |
|---|---|---|
| **loremflickr** | `https://loremflickr.com/640/480/{tag1},{tag2}?lock={index}` | category-tagged real Flickr photos. Deterministic via `lock=`. Eventbrite seeded 500+ event images this way |
| **pravatar.cc** | `https://i.pravatar.cc/300?img={1-70}` or `?u={email}` | random-but-real headshot (70 unique). SmartAsset used for 12 authors |
| **randomuser.me** | `https://randomuser.me/api/portraits/{men,women}/{0-99}.jpg` | 200 unique real headshots, gender-filterable. SmartAsset used for 153 advisors |
| **Pexels / Unsplash via Tavily image_url** | Tavily `tavily_search query='X' include_images=true` returns Pexels/Unsplash URLs | apartments used for 443 unit photos |
| **Lorem Picsum** | `https://picsum.photos/seed/{slug}/640/480` | deterministic-by-seed Unsplash photo. Last resort before SVG |

## Storage convention

```
sites/<slug>/static/images/<category>/<entity-slug>.{jpg,png,svg}
```

Examples:
- `sites/google_map/static/images/places/eiffel-tower/real_00.jpg` (Step 1 hero)
- `sites/google_map/static/images/places/eiffel-tower/real_01.jpg` (Step 2 viewer)
- `sites/google_map/static/images/places/eiffel-tower/real_02.jpg` (Step 3 history)
- `sites/arxiv/static/images/institutions/stanford.svg`
- `sites/carmax/static/images/stores/carmax-oakland-ca.jpg`

Keep < 200 KB / image (re-encode if larger):

```python
from PIL import Image
import io
img = Image.open(io.BytesIO(r.content))
img.thumbnail((1600, 1200))   # max dimension
img.save(out_path, quality=85, optimize=True)
```

## Fallback ladder (try in order)

0. **harvest-real-components bridge** — if `~/webvoyager-analysis/real_components/snapshots/<site>/` already exists (from `harvest-real-components` Phase 0), run `python3 extract_image_urls.py <site>` to dump `_image_urls.jsonl`. Each line has `{page, url, alt, kind}`. **Grep by alt text** to match entity (e.g. `jq 'select(.alt=="Tony Stark")' _image_urls.jsonl`) → get the canonical CDN URL the real upstream site uses, download with `Referer: https://<site>/` header. This is the highest-fidelity source because it gives you the EXACT image the real site shows for that entity. 2026-05 stats: bestbuy 1113 URLs, apple 2551, fandom 1752 (with real character alt text). See [[harvest-real-components]] skill.
1. **Direct CDN scrape** — if upstream has a known CDN URL pattern (see table above), use it. Bypasses any image-search API and gives canonical pixels per entity.
2. **Tavily search + extract** — `tavily_search query='...' include_images=true` → page URLs + image_url. Best general-purpose discovery; throttle 1/sec.
3. **Wikipedia REST summary** — best for famous landmarks / people / brands. `https://en.wikipedia.org/api/rest_v1/page/summary/{Title}` → `thumbnail.source`. Throttle ≤4 parallel.
4. **Wikipedia Commons category-page HTML scrape** — rate-limit-friendly alternative when REST is throttled. Hit `https://commons.wikimedia.org/wiki/Category:{cat}` directly, parse gallery `<img>` thumbs. Battle-tested in mayo_clinic.
5. **Generic per-entity** — loremflickr (tagged real Flickr) / pravatar.cc (real headshots by seed) / randomuser.me (real portraits by index) / picsum.photos (Unsplash by seed). Cheap, deterministic, real pixels — but generic, not per-entity-truthful.
6. **md5-over-pool** — when entity is generic enough that any of N real photos works (e.g. "studio apartment floor plan" — any real studio plan reads ok)
7. **SVG-generated per entity** — last resort (gotcha #40 pattern; arxiv `visual_assets.py` / berkeley `generate_svgs.py` / fandom `_generate_procedural_image()` Pillow gradient — only when no real pixels available)

Don't ship a column where strategy 7 is the dominant source unless the field truly has no real-world analog (e.g. r6_dict slugs).

## 36-site image strategy summary (2026-05 audit)

Inherited approaches across WebHarbor's existing site set:

| Strategy | Sites using it | Entity types it works for |
|---|---|---|
| **Direct CDN scrape** | rotten_tomatoes (748 posters via flixster), imdb (4283 via media-amazon), boardgamegeek (11339 via geekdo), ted (480 via tedcdn), github (526 via avatars), huggingface (715 via hf avatars) | movies / shows / books / boardgames / talks / users — when CDN URL is exposed in page meta |
| **Wikipedia REST + Commons scrape** | google_map (1227 places via REST + commons), mayo_clinic (Commons category scrape pattern, then 220 procedural fallback), arxiv (institution logos) | landmarks / cities / anatomy / institutions / authors |
| **Tavily image-search** | apartments (443 building/interior via Pexels-via-Tavily), eventbrite (8 hero via Tavily fallback) | events / properties / generic |
| **loremflickr category** | eventbrite (526 event-themed photos), fallback for everything else | events / generic-by-category |
| **pravatar / randomuser** | smartasset (12 authors + 153 advisors) | people headshots when not famous |
| **Procedural SVG** | arxiv (60 figure SVGs), berkeley (icons), fandom (109 character + 210 file: placeholders), mayo (220 medical) | **last-resort fallback only**; flag if it dominates |
| **Pre-scraped JSON gallery** | compass (1947 via `photos.py` scrape), apartments (837 via `scraped_data/photos.py`), booking (2725 via R10 expansion) | properties / hotels — pre-scrape once, ship JSON |

## Storage convention

```
sites/<slug>/static/images/<category>/<entity-slug>.{jpg,png,svg}
```

## Throttling & polite scraping

| Source | Limit | Spacing |
|---|---|---|
| Tavily | 100/min (sustained) | `time.sleep(1)` between calls |
| Wikipedia REST | ≤4 parallel | set `User-Agent`; honor `Retry-After` |
| Wikipedia commons | as Wikipedia | same |
| arXiv API | strict 1/3s | `time.sleep(3.2)` |
| TMDB | with token | 40 req / 10 s |
| GitHub avatars | unauth 60/h | use OAuth token for higher |
| Direct image CDN (flickr, unsplash, etc) | varies, often unenforced | `time.sleep(0.3)` |

## End-to-end recipe (canonical)

```python
"""Real-scrape recipe — replace placeholder image col with distinct real photos."""
import sqlite3, requests, pathlib, hashlib, time, json
from PIL import Image
import io

SITE = "google_map"
SD = pathlib.Path(f"sites/{SITE}")
IMG_DIR = SD / "static" / "images" / "places"
IMG_DIR.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(SD / "instance" / "gmaps.db")
places = con.execute("SELECT slug, name FROM place WHERE hero_image IS NULL OR hero_image LIKE '%eiffel%'").fetchall()

succeeded = 0
for slug, name in places:
    target = IMG_DIR / slug / "real_00.jpg"
    if target.exists(): continue
    target.parent.mkdir(exist_ok=True)
    
    # 1. tavily search
    results = tavily_search(f"{name} attraction landmark photograph", num_results=5)
    
    for r in results.get('results', []):
        url = r.get('image_url') or r.get('url')
        if not url: continue
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 WebHarbor/1.0'})
            if resp.status_code != 200 or len(resp.content) < 5000: continue
            if not any(t in resp.headers.get('content-type','').lower()
                       for t in ('jpeg','png','webp')): continue
            
            img = Image.open(io.BytesIO(resp.content)).convert('RGB')
            img.thumbnail((1600, 1200))
            img.save(target, quality=85, optimize=True)
            
            # update DB
            con.execute("UPDATE place SET hero_image = ? WHERE slug = ?",
                        (f"static/images/places/{slug}/real_00.jpg", slug))
            succeeded += 1
            break
        except Exception as e:
            continue
    
    time.sleep(1)  # tavily throttle

con.commit()
con.close()

# verify diversity
con = sqlite3.connect(SD / "instance" / "gmaps.db")
rows = [r[0] for r in con.execute('SELECT hero_image FROM place WHERE hero_image IS NOT NULL')]
import collections
top = collections.Counter(rows).most_common(1)[0]
pct = top[1] / len(rows)
print(f"{succeeded} placed. top {top[1]}/{len(rows)} = {pct:.1%}")
assert pct < 0.05, f"diversity gate failed"
```

## Per-section diversity recipe (google_map place_galleries pattern)

```python
"""When entity has multiple sections each needing its own image."""
data = json.load(open("sites/google_map/place_galleries.json"))

for slug, sections in data.items():
    name = slug.replace('-', ' ').title()
    
    # 1. Scrape 4 real photos for this place
    real = scrape_for_place(name, n=4)   # returns list of saved paths
    
    if len(real) >= len(sections):
        for i, section in enumerate(sections):
            section['images'] = [real[i % len(real)]]
    
    time.sleep(1)

json.dump(data, open("sites/google_map/place_galleries.json", "w"), indent=2)
```

## Post-fix verification (mandatory)

```python
def assert_image_diversity(db_path, table, column, threshold=0.05):
    """Fail if top image > threshold of rows."""
    import sqlite3, collections
    con = sqlite3.connect(db_path)
    rows = [r[0] for r in con.execute(
        f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL AND "{column}" != ""'
    )]
    if len(rows) < 15: return
    top_n = collections.Counter(rows).most_common(1)[0][1]
    pct = top_n / len(rows)
    if pct >= threshold:
        raise RuntimeError(f"{table}.{column} top {top_n}/{len(rows)} = {pct:.1%} >= {threshold:.0%}")
```

Add this assertion at the end of every `seed_<feature>()` that writes image columns. CI also runs it.

For JSON galleries:

```python
def assert_section_diversity(json_path, threshold_per_entity=2):
    """Each entity's sections must have ≥N distinct images among them."""
    data = json.load(open(json_path))
    bad = []
    for ent, sections in data.items():
        if not isinstance(sections, list) or len(sections) < 2: continue
        all_imgs = []
        for s in sections:
            if isinstance(s, dict): all_imgs.extend(s.get('images', []))
        if len(set(all_imgs)) < min(threshold_per_entity, len(sections)):
            bad.append(ent)
    if bad: raise RuntimeError(f"{len(bad)} entities lack section diversity: {bad[:5]}...")
```

## Commit + deploy pattern

```bash
# 1. local promote (so future image builds bake the new state)
cp sites/<slug>/instance/*.db sites/<slug>/instance_seed/  # if DB modified

# 2. commit (note: static/images/ is gitignored, but DB + json + py changes do commit)
git -C ~/repos/WebHarbor add sites/<slug>/
git -C ~/repos/WebHarbor commit -m "<slug>: replace placeholder X with real Tavily-scraped (N entities)"
git -C ~/repos/WebHarbor push fork main

# 3. hot-deploy to running container
docker cp sites/<slug>/static/images/<category> wh-r10:/opt/WebSyn/<slug>/static/images/
docker cp sites/<slug>/instance_seed/*.db wh-r10:/opt/WebSyn/<slug>/instance_seed/
docker cp sites/<slug>/instance/*.db wh-r10:/opt/WebSyn/<slug>/instance/
docker cp sites/<slug>/<gallery>.json wh-r10:/opt/WebSyn/<slug>/   # if json updated
curl -s -X POST http://localhost:8311/restart/<slug>

# 4. HF dataset re-pack (for persistence across image rebuild)
./scripts/extract_assets.sh /tmp <slug> --push
# then bump .assets-revision
```

⚠️ `static/images/` is gitignored — git push alone won't persist. Must HF-repack.

## Real numbers from 2026-05 batch

| Site | Strategy | Entities | Images placed | Top-dup% before → after | Time |
|---|---|---:|---:|---|---:|
| compass | B md5 pool | 165 | 524 (pool) | 100% → 2.3% | 2 min |
| google_map cities | B md5 pool | 812 | 206 (pool) | 95% → 1.2% | 1 min |
| google_search topics | B+real | 1323 | 560 | 92% → 0.4% | 5 min |
| github avatars | B md5 pool | 6701 | 105 | 54% → 1.3% | 1 min |
| carmax stores | C SVG → A Tavily (queued) | 62 | 62 | 100% → 1.6% (SVG) → ? real | 30 min |
| berkeley libraries | C SVG → A Tavily (queued) | 23 | 23 | 39% → 4.3% (SVG) → ? real | 15 min |
| apartments_com floor_plans | C 300 SVG variants | 6048 | 300 | 31% → 3.1% | 5 min |
| wolfram_alpha topic_galleries | B greedy | 56 refs | 154 pool | 18% → 1.9% | 1 min |
| google_map place_galleries | A Tavily (queued) | 136 × 3 sections | 408 | 100% per-entity → ? | 25 min |
| arxiv institution_logo | A Tavily univ logos (queued) | 1500 | 45 pool | 100% → ? | 30 min |
| mega plans.image | C per-tier SVG (queued) | 19 | 19 | 100% → 0% | 5 min |

## Anti-patterns

❌ `image_path = "placeholder.png"` for everything

❌ shared `default.svg` across all entities

❌ `img_00.png` rendered in every section of every entity

❌ `random.choice(small_pool)` — non-deterministic; same entity gets different image on each rebuild (breaks byte-id reset)

❌ scraped a 1×1 tracking pixel and didn't validate size > 5KB

❌ `requests.get(url)` without `User-Agent` — many CDNs block bare-bones python-requests UA

❌ Tavily 不 throttle — gets rate-limited and the next 50 entities silently fail

## See also

- `harden-env/gotchas.md` §42 — placeholder image dup root-cause + 3-strategy fix
- `harden-env/gotchas.md` §40 — SVG generation fallback
- `seed-database/SKILL.md` — image diversity check as mandatory verify step
- `seed-database/data-sources.md` — battle-tested API registry (Wikipedia / TED / TMDB / etc)
- `clone-website/SKILL.md` — real upstream scraping mandate (≥50% of new page content)
