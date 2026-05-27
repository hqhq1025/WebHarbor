---
name: scrape-real-images
description: "Source distinct real photographs / logos / artwork for WebHarbor mirror entities at scale. Uses Tavily / WebFetch / public-API mirrors to fetch real upstream imagery, validates that the resulting per-entity image diversity beats the 'top image ≤5% of entities' threshold, and falls back to deterministic SVG generation only when real sourcing fails. Use when an entity table or json gallery has top-image > 30% duplicate (one placeholder reused everywhere), or when filling a new image field for the first time. Triggers: '真扒图', '占位图', 'placeholder image', 'real images for entities', 'image diversity'."
---

# Scrape Real Images — Source distinct upstream imagery, banish placeholders

This skill exists because WebHarbor mirrors look fake fast when 812 cities share one Eiffel Tower image, or 1500 authors share one CS.svg logo. Every entity column that names an image deserves a distinct real photo whenever cheaply possible.

## When to use

- After deepen/seed pass when a new image column is populated — verify diversity before declaring done
- When `image diversity check` (see `seed-database` skill / `harden-env` gotcha #42) fails — top image > 30%
- When `document-site-gui` audit notices "every place_detail page shows the same map snippet"
- When user reports "this site looks fake"

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

## ⚠️ Source priority: Wikipedia/Wikimedia FIRST, **local SearXNG SECOND**, Tavily LAST

**Tavily / Exa 是 last resort 不是 default**。Tavily 有月配额（free 1000 query/月），过去一次 36 站 polish 直接消耗 ~50-75%（700+ query），其中大部分本来能用免费 unlimited 的 Wikipedia/Wikimedia REST API + **本地 SearXNG meta-search** 拿到。

### 本地 SearXNG（替代 Tavily/Exa，完全免费、无 quota）

跑在 `http://localhost:8888`（docker container `searxng`，端口 8888 → 8080）。聚合 Google / Bing / DuckDuckGo / Brave / Wikipedia / Wikimedia 等 70 个引擎，返回标准 JSON。如果 container 没在跑，启动：

```bash
mkdir -p /tmp/searxng && cat > /tmp/searxng/settings.yml <<'EOF'
use_default_settings: true
server:
  secret_key: "<random>"
  bind_address: "0.0.0.0"
  port: 8080
  limiter: false
search:
  formats: [html, json]
EOF
docker run -d --name searxng -p 8888:8080 -v /tmp/searxng:/etc/searxng:rw searxng/searxng:latest
```

调用（wrapper at `~/webvoyager-analysis/real_components/search_local.py`）：

```python
from search_local import search, search_images

# Tavily-equivalent text search
results = search("italian restaurant interior", n=10)
# [{title, url, content, engine, score}, ...]

# Tavily include_images=True equivalent — returns Google+Bing image search aggregated
imgs = search_images("italian restaurant interior", n=20)
# [{img_src, thumbnail_src, title, source}, ...]
```

实测 2026-05：289 image results / "iron man" query in 1 second，Google + Bing + Wikimedia 聚合，0 cost。

**第一反应应该是查这张表**（按 entity 类型直接知道去哪爬），找不到才用本地 SearXNG，最后才用 Tavily：

| 想要的图 | 直接爬哪（免费 unlimited） | 限速 |
|---|---|---|
| **名地标 / 景点 / 城市** | `en.wikipedia.org/api/rest_v1/page/summary/<Title>` → `.thumbnail.source` | ≤4 并发 |
| **大学 / 公司 logo** | Wikipedia summary + Wikimedia Commons `api.php?action=query&list=allimages&aiprefix=<X>` | 1 req/s |
| **商品图（Amazon/eBay/...）** | 已知 CDN 模式直 GET：`images-na.ssl-images-amazon.com/images/I/<ASIN>.jpg` | 自由 |
| **电影 poster / 演员头像** | Wikipedia (绝大多数) / Open Library `covers.openlibrary.org/b/isbn/<ISBN>-L.jpg` | 1 req/s |
| **YouTube video thumb** | `img.youtube.com/vi/<ID>/maxresdefault.jpg` | 无 |
| **GitHub avatar** | `avatars.githubusercontent.com/<user>?v=4` 或 `/u/<id>?v=4` | 60/h unauth, 5000/h with token |
| **arXiv paper figure** | 直接 GET `arxiv.org/abs/<id>` HTML 解 `<img>` src | 1/3s |
| **TED talk thumbnail** | 已知 pattern: `pi.tedcdn.com/r/talkstar-photos.s3.amazonaws.com/uploads/<slug>.jpg` | 无 |
| **新闻 hero image** | RSS feed 自带 `<media:thumbnail url="...">` 或 `<enclosure type="image/...">` | 自由 |
| **HuggingFace model 截图** | `huggingface.co/<repo>/raw/main/<image>.png` 或 README 内 image | 自由 |
| **股票图 / 通用 photo** | Unsplash API `api.unsplash.com/search/photos?query=X` (free 50/h) / Pexels `api.pexels.com/v1/search` (200/h) | API key 免费申 |
| **找不到指定的** | DuckDuckGo image search HTML scrape `duckduckgo.com/?q=X&iax=images&ia=images` → 解 JSON | polite UA, 自由 |

### Wikipedia REST 直爬模板（最高 ROI，覆盖 60-80% 真实 entity）

```python
import requests, time

# ⚠️ UA 必须是真浏览器或合规归因 UA — 否则 upload.wikimedia.org 直接 403
# ❌ 别用: "Python/3.10" / "curl/7.x" / "Bot/1.0" / generic UA
# ✅ 用方案 A: 真 Chrome UA — 简单粗暴
UA_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
# ✅ 用方案 B: 合规归因 UA — 符合 Wikimedia attribution policy
UA_POLITE = "WebHarbor-Mirror-Builder/1.0 (https://github.com/aiming-lab/WebHarbor; contact@example.com)"

def wiki_thumb(name, size=800):
    """Get the canonical Wikipedia thumbnail for a named entity. Returns None on miss."""
    title = name.replace(' ', '_')
    r = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
        headers={'User-Agent': UA_POLITE},  # 任选 A 或 B
        timeout=5,
    )
    if r.status_code != 200: return None
    thumb = r.json().get('thumbnail')
    if not thumb: return None
    return thumb.get('source')

# bulk fetch for 1000 entities，无配额
for ent in entities:
    url = wiki_thumb(ent.name)
    if url:
        download_and_save(url, dest, headers={'User-Agent': UA_POLITE})  # 下载时也要带！
    time.sleep(0.3)
```

**2026-05 教训（必看）**：
- 多次实战 generic bot UA 在 `upload.wikimedia.org/wikipedia/commons/...` 直接 403（API 通但下载图被拒）
- 用真 Chrome UA 或合规归因 UA → 100% 通过
- 推荐先 polite UA，请求被拒再 fallback Chrome UA

**实测**：本会话 google_map 136 place 用 Wikipedia REST 一次抓 **407 张 wiki_*.jpg / 166MB**, 135/136 places 拿到 3 张 distinct 真照片 — **0 Tavily call**。berkeley/recreation_gov 6 列 top-dup 21-27% → ≤6.7%，127 张 webp 全 Wikipedia REST。

### Wikimedia Commons 直查（找特定文件名 / category）

```python
# 查 CarMax 相关图
r = requests.get(
    "https://commons.wikimedia.org/w/api.php",
    params={
        'action': 'query', 'format': 'json',
        'list': 'allimages', 'aiprefix': 'CarMax',
        'ailimit': 50,
    },
    headers={'User-Agent': 'WebHarbor/1.0 ...'}
)
for img in r.json().get('query', {}).get('allimages', []):
    print(img['url'])
```

或用 `prop=images` + `prop=imageinfo` 拿一个 page 的所有 image。

### Domain-specific CDN（已知 URL pattern）

不需要 search 或 API，直接拼 URL：

```python
# GitHub avatar
url = f"https://avatars.githubusercontent.com/u/{user_id}?v=4&s=120"

# YouTube thumb
for video_id in video_ids:
    url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

# Amazon product (if ASIN known)
url = f"https://images-na.ssl-images-amazon.com/images/I/{image_id}.jpg"

# Open Library book cover
url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
```

## Tavily as fallback only

当上面所有方法都没拿到 entity 真图（≈ 10-20% case），再用 Tavily：

```python
# Discovery — find real source URLs
results = tavily_search(
    query=f"{entity.name} {kind} photograph hero image",
    num_results=8,
)
img_candidates = [r.get('image_url') for r in results['results'] if r.get('image_url')]
```

Or use `tavily_extract` if Tavily returns page URLs and you need to harvest their images:

```python
extracted = tavily_extract(urls=[r['url'] for r in results['results'][:5]])
for page in extracted:
    for img in page.get('images', [])[:3]:
        img_candidates.append(img)
```

### Tavily 节流 / 配额省钱技巧

- 一次 `tavily_extract(urls=[...20 URLs...])` 比 20 次 `tavily_search` 便宜
- **batch query**：把"36 个 PR site 都各扒 25 个 page"想成"一次性 36 × 25 = 900 个 url 的 batch extract"，能省 80% query 数
- 找到第一张满足的图就 break，不要 fetch 8 候选都下载

### Query crafting per domain (Tavily as fallback)

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

## Wikipedia REST API details

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

## Direct CDN scraping (when the upstream pattern is known)

For known sources, use direct CDN URLs:

| Upstream | Pattern |
|---|---|
| TED talks | `https://pi.tedcdn.com/r/talkstar-photos.s3.amazonaws.com/uploads/{slug}.jpg` (battle-tested) |
| TMDB (movies) | API: `https://api.themoviedb.org/3/movie/{id}` → `poster_path` (needs API token) |
| Rotten Tomatoes | scrape page, regex extract flixster CDN URLs |
| GitHub avatars | `https://avatars.githubusercontent.com/u/{user_id}?v=4` |
| HuggingFace | `https://huggingface.co/avatars/{username}.svg` |
| OpenStreetMap places | Wikipedia REST summary (above) — most landmarks have Wiki page |

See `data-sources.md` in `seed-database/` for the full battle-tested registry.

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

1. **Tavily search + extract** — best quality, broad coverage
2. **Wikipedia REST summary** — best for famous landmarks / people / brands
3. **Domain-specific API** — TED/TMDB/GitHub avatars/OpenFlights
4. **md5-over-pool** — when entity is generic enough that any of N real photos works (e.g. "studio apartment floor plan" — any real studio plan reads ok)
5. **SVG-generated per entity** — last resort (gotcha #40 pattern)

Don't ship a column where strategy 5 is the dominant source unless the field truly has no real-world analog (e.g. r6_dict slugs).

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
