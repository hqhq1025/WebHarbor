---
name: clone-website
description: "Phase 1: Clone a real website into a local Flask mirror that fits the WebHarbor repo layout. Scaffolds with ./scripts/new_site.py, harvests real assets (images, CSS), builds SQLAlchemy models, generates Jinja2 templates matching the original design, and produces an idempotent seed DB. The result is a runnable site under sites/<name>/ with auth, basic CRUD, and real product/article imagery. Use when starting a new WebHarbor website contribution."
---

# Clone Website — Initial Mirror Construction

## When to use

- Starting a new website mirror for WebHarbor
- Phase 1 of the WebHarbor contribution pipeline

## Prerequisites

- The website has been claimed via the tracking sheet and contribution form
- You have a fork of `https://github.com/aiming-lab/WebHarbor` cloned locally
- You have run `./scripts/fetch_assets.sh` to pull current assets from HuggingFace
- You can run Docker locally
- **⚠️ MANDATORY Phase 0**: Run [[harvest-real-components]] first to capture real upstream HTML + screenshots + img URLs from the target site. Outputs under `~/webvoyager-analysis/real_components/snapshots/<site>/`. The harvested `full.html` files contain real `<img src>` references that will be needed in Phase 1 image scraping (see below).

## Per-entity real images — MANDATORY pre-ship check (added 2026-05)

Before declaring a clone "done", every entity column with an image field MUST satisfy `top duplicate ≤ 5%`. See [[scrape-real-images]] skill for the canonical workflow:

1. After Phase 0 harvest: `python3 ~/webvoyager-analysis/real_components/extract_image_urls.py <site>` → `_image_urls.jsonl` with `{page, url, alt, kind}` per image (real CDN URLs the upstream site actually uses for each entity)
2. Grep by alt text or URL pattern to match entity → download with `Referer: https://<site>/` header (see [[scrape-real-images]] §"harvest-real-components bridge")
3. Fall back to Tavily / Wikipedia / domain-specific APIs / md5-over-pool / procedural SVG (last resort) per the ladder in [[scrape-real-images]]
4. Validate diversity: `python3 -c "..."` (skill provides the snippet)
5. **5 个 P0 站 (2026-05) 实战教训**：fandom 109 角色页用 gradient placeholder / mayo 220 张程序 SVG / smartasset 0 张真 author 头像 —— 都是因为跳过这步而后来需要补 deepen pass。**不要重复这个错误**。

## Repo layout (this is the source of truth)

```
sites/<your_site>/
├── app.py              ← Flask app: routes + SQLAlchemy models
├── seed_data.py        ← build-time seed
├── _health.py          ← end-to-end health check
├── requirements.txt    ← Flask + any extras
├── templates/          ← Jinja2 templates
├── static/{css,js,icons}/        ← small UI files, committed to git
├── static/images/                ← heavy, lives in HF dataset
├── static/external_cache/        ← optional, lives in HF dataset
├── instance_seed/<site>.db       ← seed DB, lives in HF dataset
├── instance/                     ← gitignored, recreated on boot
├── scraped_data/                 ← gitignored, build-time only
└── tasks.jsonl                   ← benchmark tasks (jsonl, one per line)
```

Inside the running container sites live at `/opt/WebSyn/<site>/`. The path
predates the rename and is kept stable.

## Workflow

### Step 1: Scaffold

```bash
./scripts/new_site.py <your_site>
```

This creates `sites/<your_site>/` with the skeleton above. Register the site
in three places (must stay in sync):

1. `websyn_start.sh` — `SITES=( ... )` array (port = 40000 + index)
2. `control_server.py` — `SITES = [ ... ]` list (exact match)
3. `Dockerfile` — `EXPOSE 8101 40000-N` (raise N if needed)

### Reconnaissance & scraping: drive a real browser with Playwright

Modern target sites (Amazon, Booking, Apple, Coursera, ...) are JS-heavy SPAs / hydrated React apps. `requests.get(url)` returns an empty shell — no products, no images, no cards. Recon and scraping both **must** be done by driving a real Chromium via Playwright (or an equivalent real-browser tool); only that path produces the rendered DOM and the real image URLs the live site actually serves. The `agent_demo/` env already has Playwright + Chromium installed via `uv sync` — reuse it.

Minimum scraping recipe — render the page, then pull the post-hydration DOM and the resolved image `src` attributes:

```python
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import httpx, pathlib

OUT = pathlib.Path("sites/<your_site>/scraped_data")
OUT.mkdir(parents=True, exist_ok=True)
(IMG := OUT / "images").mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.example.com/category/phones", wait_until="networkidle")
    page.screenshot(path=OUT / "category_phones.png", full_page=True)
    (OUT / "category_phones.html").write_text(page.content())          # post-JS DOM

    cards = page.eval_on_selector_all(                                  # extract structured data
        "[data-product-card]",
        "els => els.map(e => ({"
        "  name: e.querySelector('.title')?.innerText,"
        "  price: e.querySelector('.price')?.innerText,"
        "  href:  e.querySelector('a')?.href,"
        "  img:   e.querySelector('img')?.src"
        "}))",
    )
    browser.close()

# Fetch the real images at their resolved URLs.
with httpx.Client(follow_redirects=True, timeout=30) as cx:
    for c in cards:
        if not c["img"]: continue
        r = cx.get(c["img"]); r.raise_for_status()
        slug = c["href"].rstrip("/").split("/")[-1]
        (IMG / f"{slug}.jpg").write_bytes(r.content)
```

Things that REQUIRE Playwright (not curl/`requests`):

- Listing pages whose cards are injected client-side (most e-commerce, most modern news)
- Detail pages with lazy-loaded image galleries
- Image URLs that come from a `data-src` / `srcset` resolved by JS
- Sites that require scroll or click to load more (`page.mouse.wheel`, `page.click("button.load-more")`)
- Anything behind a banner / cookie modal that blocks initial render

`requests` / `httpx` are OK **only** for fetching final, resolved asset URLs (the image bytes themselves, the static CSS files) once Playwright has surfaced them. Never use them to fetch the listing HTML.

Map the target's structure from these renders:

- Homepage layout (hero, nav, sidebar, footer, cards)
- Navigation hierarchy (top-level categories, sub-pages)
- URL patterns (`/product/<slug>`, `/category/<slug>`, `/search?q=`)
- Key page types (listing, detail, search results, account, checkout)
- Auth flows (login, register, logout, password reset)
- Forms (search, contact, checkout, review submission)

### Step 3: Asset harvesting

Drive the live site with Playwright (recipe above) and download assets into `scraped_data/` (gitignored, build-time only). Then organize what you keep into `static/`:

- **Product/article images** → `sites/<site>/static/images/` (lives in HF dataset, not committed to git)
- **Brand assets, CSS, JS, icons** → `sites/<site>/static/{css,js,icons}/` (small, committed)

**Critical**: use REAL images from the live site, captured via Playwright + a follow-up `httpx.get` of the resolved URL. Never use placeholders, colored rectangles, AI-generated stock photos, or `requests.get(target_url)` HTML (it returns a JS shell without the image URLs). Multimodal fidelity is a core WebHarbor differentiator and is the #1 reason agents reject reviews.

### Step 4: Backend build

Edit `sites/<your_site>/app.py`:

```python
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # NEVER hard-code absolute paths
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BASE_DIR}/instance/<site>.db'
app.config['SECRET_KEY'] = 'webharbor-<site>-dev-key'   # deterministic dev key OK
db = SQLAlchemy(app)
```

Required models (adapt to site type):
- `User` (password hashing, login)
- Primary entity (Product / Article / Course / Recipe / ...)
- Categories, reviews, orders, bookmarks, junction tables

Required routes:
- `/` — homepage
- `/login`, `/register`, `/logout` — auth
- `/account`, `/account/edit` — profile management
- `/search?q=` — search with scored relevance (token-overlap, NOT strict AND)
- `/<entity>/<slug>` — detail pages
- CRUD routes for cart/bookmarks/favorites

### Step 5: Frontend build

Create Jinja2 templates under `sites/<your_site>/templates/`:

- `base.html` — shared layout (header, nav, footer)
- `index.html` — homepage with real content
- `login.html`, `register.html`
- Entity listing & detail templates
- Search results template

Match the original site's color scheme, typography, and navigation. Don't
ship a generic Bootstrap theme.

### Step 6: Seed data

Edit `sites/<your_site>/seed_data.py` so that `seed_database()` is **idempotent**:

```python
def seed_database():
    if Product.query.count() > 0:
        return                    # ← critical: early-return on populated DB
    # ... seed rows ...

def seed_benchmark_users():
    if User.query.filter_by(email='alice.j@test.com').first():
        return                    # ← gate this function too
    # ... seed 4 benchmark users ...
```

In `app.py`, wire both into the bootstrap:

```python
with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()
```

**Gate every seed function as a whole.** Per-row gates aren't enough: a
no-op `db.session.commit()` still bumps SQLite metadata and breaks the
byte-identical reset invariant.

Then run the site once locally to produce `instance/<site>.db`, copy it to
`instance_seed/<site>.db`. That seed is what ships with the image.

### Step 7: Verify locally

```bash
./scripts/build.sh webharbor:dev
docker run -d --rm --name wh-test \
  -p 8201:8101 -p 41000-41014:40000-40014 webharbor:dev

# your new site is on port 41000 + its index
curl -so /dev/null -w "%{http_code}\n" http://localhost:41000NN/

# byte-identical reset invariant
curl -X POST http://localhost:8201/reset/<your_site>
docker exec wh-test md5sum \
  /opt/WebSyn/<your_site>/instance/<your_site>.db \
  /opt/WebSyn/<your_site>/instance_seed/<your_site>.db
# both md5s MUST match
```

Then drive the mirror through Playwright (same recipe as recon, but pointing at `http://localhost:41000+i/`): screenshot the homepage, one listing page, one detail page, the login flow, and one search. Diff visually against the screenshots you captured in Step 2. If something looks like a coloured rectangle or "Image" alt text, you're missing real assets — go back to Step 3.

## Output

After Phase 1, you should have:
- `sites/<your_site>/app.py` with all models, routes, and bootstrap
- `sites/<your_site>/seed_data.py` with idempotent seed functions
- `sites/<your_site>/templates/` with 15+ Jinja2 templates
- `sites/<your_site>/static/` with real CSS/JS/icons (and images under HF assets)
- `sites/<your_site>/instance_seed/<site>.db` with seeded data
- Site registered in `websyn_start.sh`, `control_server.py`, `Dockerfile`
- All 15 sites still return 200 on the alt-port container
- Byte-identical reset passes

---

## Lessons learned — anti-bot, Playwright quirks, seed pattern choice (IMDb 2026-05-26)

### Pattern 1: `wait_until="networkidle"` does not work on sites with persistent traffic

The Playwright recipe in this skill uses `networkidle` — IMDb (and most
ad-supported sites) ship continuous ad/analytics/tracking beacons, so the
network *never* idles within the 15-30s timeout. You get a TimeoutError
even though the page rendered fine.

**Replace `networkidle` with `load` + explicit selector wait**:

```python
await page.goto(url, wait_until="load", timeout=30_000)
await page.wait_for_selector('h1', timeout=15_000)  # known anchor on the page
```

The `load` event fires once the initial document is parsed; the subsequent
`wait_for_selector` ensures the post-hydration DOM is ready before you parse.

### Pattern 2: `page.screenshot()` blocks on web fonts

Default `page.screenshot()` waits for fonts to load. On a slow CDN this
exceeds the 30s default timeout and aborts the whole scrape mid-page. The
fix is short timeout + animations off + a try/except wrapper that lets
data extraction continue when the screenshot fails:

```python
def shot(page, path):
    try:
        page.screenshot(path=str(path), full_page=False,
                        timeout=8_000, animations="disabled")
    except Exception:
        pass  # screenshot is documentation, not data; OK to skip
```

### Pattern 3: Concurrency above ~8 triggers anti-bot 403 chaff

The IMDb scrape ran two recon processes in parallel at concurrency 10
each (20 simultaneous page loads). The site silently served `<h1>403
Forbidden</h1>` pages instead of throwing — the scraper happily saved
1854 person JSONs whose `h1` was literally "403 Forbidden". Half the
catalog was garbage.

**Defenses**:
- **Cap concurrency at 6-8** when fetching a real site (lower if the target
  rate-limits aggressively).
- **Validate `h1` immediately after parse**: drop any JSON whose `h1`
  starts with `403 / 404 / 5xx / Error / Service Unavailable / empty`.
- **Apply this as a `garbage_filter` in seed_data.py too**, so even if a
  bad JSON sneaks past the scraper, it never reaches the DB.

### Pattern 4: Canonical-URL guard (IMDb-style redirects)

Some sites redirect unknown / deleted IDs to a different valid page rather
than returning 404. The scraper requests `/title/tt0245429/` (Spirited Away)
but the server silently sends back `/title/tt0054215/` (Psycho). Without a
guard, the scrape saves Psycho's data into `title_tt0245429.json` and your
DB now claims `tt0245429 = Psycho`.

**Always validate the canonical URL of the rendered page against the
requested ID**:

```python
# In the JS extractor:
ld = ...JSON-LD structured data...
return { ..., url: location.href, ld }

# In seed_data.py:
canonical_id = re.search(r'/title/(tt\d+)', d['ld'].get('url', '')).group(1)
if canonical_id != filename_id:
    redirect_skipped += 1
    continue
```

On the IMDb run this guard dropped 65 redirected JSON files, taking the
catalog from 455 → 390 *clean* titles.

### Pattern 5: Hero `<h1>` beats JSON-LD `name` for human display

`ld.name` in IMDb's schema.org structured data returns the original-language
title — `Gisaengchung` for Parasite, `Ladri di biciclette` for Bicycle
Thieves. The hero `<h1>` element shows the English title. For user-facing
display, prefer `h1`; keep `ld.name` only as a fallback when `h1` is empty.

Same applies for `Person.name`: IMDb appends a disambiguator suffix like
`(I)` / `(II)` to same-name people. Strip both the year-paren and the
disambiguator-paren before storing:

```python
DISAMBIG_RE = re.compile(r'\([IVX]+\)')
YEAR_PAREN_RE = re.compile(r'\(\d{4}(?:[-–]\d{4}?)?\)')
```

### Pattern 6: HTML entities + lowercase data-testid keys

Two related parser surprises:

- `ld.name` can contain entity-encoded chars: `Schindler&apos;s List`,
  `It&apos;s a Wonderful Life`. Always run scraped strings through
  `html.unescape()` at seed time.
- IMDb's `data-testid` attribute uses **lowercase only**:
  `bo_grossdomestic`, `bo_cumulativeworldwidegross`,
  `bo_openingweekenddomestic`. Exact-key lookup using camelCase
  (`bo_grossDomestic`) silently returns nothing, producing an all-zero
  box-office column.

Use case-insensitive substring matching for testid-derived keys:

```python
def find_money(details, *needles):
    lc = {k.lower(): v for k, v in details.items()}
    for n in needles:
        for k, v in lc.items():
            if n.lower() in k:
                return parse_money(v)
    return None
```

### Pattern 7: Selectors break silently — inspect the real DOM before writing them

The first version of the IMDb name-page extractor returned `profession=[]`
for all 3796 persons. The selector
`[data-testid="hero__primary-text-secondary"]` didn't exist in IMDb's
current DOM. The fix: load **one** real page, dump every `data-testid` that
matches `^(nm|hero|profession|...)`, then write the right selectors.

Quick recipe for a target site:

```python
diag = page.evaluate("""() => ({
    all_testids: [...new Set([...document.querySelectorAll('[data-testid]')]
        .map(e => e.getAttribute('data-testid')))],
    hero_subtext: [...document.querySelectorAll('h1 ~ *')]
        .slice(0, 5).map(e => ({tag: e.tagName, text: e.innerText.slice(0,200)})),
})""")
```

This 5-line diagnostic saves hours of guessing.

### Pattern 8: Two distinct seed patterns — pick consciously

The skill shows the **berkeley pattern** (build-time RUN that materializes
the DB at `docker build` time):

```dockerfile
RUN cd /opt/WebSyn/berkeley && \
    python3 -c "from app import app" && \
    cp instance/berkeley.db instance_seed/berkeley.db
```

This works **only when seed data is Python literals hardcoded inside
seed_data.py**. Berkeley's catalog is hand-authored; the seed runs
without external files.

The **HF asset pattern** is the second valid choice: scraped data lives
in `sites/<site>/scraped_data/*.json` (gitignored + dockerignored),
gets materialized into `instance_seed/<site>.db` at recon time, and the
DB ships via the HF dataset tarball — *not* via a Dockerfile RUN.

**The trap**: copying berkeley's RUN line for a scraper-fed site. The
docker build context excludes `scraped_data/`, so the RUN sees an empty
JSON directory and produces a 0-row DB silently. You'll find out at
runtime when `/_health` returns `{"titles": 0}`.

Decision rule:

| Seed data shape | Pattern | Dockerfile RUN? | HF asset needed? |
|---|---|---|---|
| Python literals in `seed_data.py` | berkeley | yes | no |
| Reads from `scraped_data/*.json` | HF asset | **no** | yes (instance_seed + static/images) |

If you're in the HF-asset pattern, `scripts/fetch_assets.sh` brings the
seed DB and images into place before `scripts/build.sh` runs. The
Dockerfile just `COPY sites/`s the already-populated tree.

## Next step

Proceed to **design-tasks** (Phase 2) to define `tasks.jsonl` for this mirror.

---

## 真扒上游优先：禁止"占位字符串" (added 2026-05-27)

Agents repeatedly fall into the trap of generating fake-looking real-data with hardcoded strings like:

```python
R4_CARDS = [
    {"title": "Aurora over the Norwegian fjords", "source": "nasa.gov", ...},
    {"title": "Lavender field at sunset in Provence", "source": "unsplash.com", ...},
    # 22 more identical-structure entries
]
```

The titles are plausible-sounding but **synthesized**. The source domains are real-domain placeholders. The thumbnail filename `thumb_1.jpg` doesn't exist on disk. This is "fake real" — it passes a casual review but is detectable and unrealistic.

### Mandatory: scrape real upstream before seeding

Every new page family needs at least **50% of its content from real upstream scraping** via:

- `mcp__tavily__tavily_extract(urls=[...], format="markdown")` — full-page extraction
- `mcp__tavily__tavily_search(query="...")` — find relevant real URLs first
- `WebFetch(url=..., prompt="...")` — single-page extraction with summarization

The `data-sources.md` registry (under `seed-database/`) lists battle-tested **free, no-key** APIs that already produced real data for 20+ mirrors. Check it first.

### Recipe pattern

```python
# Step 1: discover real URLs
results = tavily_search("site:apple.com iPhone 17 Pro buy page configuration")
target_urls = [r["url"] for r in results["results"][:5]]

# Step 2: extract real content
pages = tavily_extract(urls=target_urls, format="markdown")

# Step 3: parse and seed
for page in pages:
    parsed = parse_apple_buy_config(page["raw_content"])
    db.session.add(Product(name=parsed["name"], price=parsed["price"], ...))
db.session.commit()
```

### Acceptable synthesis (only when real data is sparse)

Synthesizing is allowed ONLY when:
1. The real upstream has too many entries to scrape exhaustively (e.g. all 7000 airports)
2. The field is deterministically derivable from a small real anchor

For example carmax: NHTSA vPIC API (30 makes × 10 models) + hash-derived prices/MPG:
`int.from_bytes(hashlib.md5(slug.encode()).digest()[:4], "big") % 50000`

The anchor names are real. Numeric fields are synthesized but **deterministically and reproducibly**.

**Never use**: `random.random()` without seeding from stable string. `Faker().name()` for entity names. Made-up domains.

---

## "更多 GUI 页面" — what counts as a real GUI surface (added 2026-05-27)

When deepening, agents inflate the **route** count by adding API endpoints, redirects, alternate URLs of existing pages. **None are GUI surfaces.**

A real GUI surface meets all of:

1. Has a unique HTML template (not a shared 'vertical.html')
2. Renders distinct visual content (different hero / grid / form)
3. Reachable from `/` via clickable `<a href>` chain in ≤3 hops
4. Has tasks targeting it that **work via clicks**, not URL typing
5. Backed by DB rows (not in-memory dict)

### Per-site GUI page target

| Site type | Surface target | Reference |
|---|---|---|
| Search engine | 80-100 templates | google_search 91 |
| Marketplace | 70-90 templates | amazon 76 |
| Social / community | 70-90 templates | huggingface 72, github 72 |
| Booking / travel | 60-80 templates | booking 75 |
| News / sport | 70-90 templates | bbc_news 75, espn 91 |
| Catalog / dictionary | 50-70 templates | cambridge 66 |

Under 50 distinct templates → run a GUI-only deepen pass.

### Image utilization in templates

`static/images/` may have 800+ photos. Check refs:

```bash
grep -rhoE "<img[\s>]|background-image\s*:|\.image_url|\.thumb|\.photo|\.poster" sites/<site>/templates | wc -l
```

Under 30% utilization → templates visually starved. Add hero + gallery + thumbnail patterns.

### Form interaction debt

Per site:
- ≥ 60% GET (read pages)
- ≥ 20% POST (write forms: save / edit / submit / vote / follow / upload)

Under 20% POST → site is view-only. Add user-write surfaces by family (vocab list / quiz / save / review / message / report).

---

## Canonical "deepen pass" recipe (added 2026-05-27)

When taking a skeleton site (≤30 templates / ≤50 tasks) up to vanilla-level (≥65 templates / ≥1500 tasks / ≥20 POST / ≥40% image utilization), use this proven architecture:

### Architecture: append-only blueprint module

```python
# sites/<site>/<feature>_deepen.py — new file, doesn't touch existing app.py
"""All deepen routes + models + seed live here. app.py imports register()."""
from flask import render_template, request, redirect, flash

# Models — define here, register on the existing db
def define_models(db):
    class NewModel1(db.Model):
        __tablename__ = "deepen_new_1"
        id = db.Column(db.Integer, primary_key=True)
        # ...
    return {"NewModel1": NewModel1, ...}

# Seed — gated by row-count check
def seed_deepen(app, db, models):
    with app.app_context():
        if models["NewModel1"].query.count() > 0:
            return
        for row in REAL_DATA:
            db.session.add(models["NewModel1"](**row))
        db.session.commit()

# Routes — register on the app
def register_routes(app, db, models):
    @app.route("/new-hub")
    def new_hub():
        items = models["NewModel1"].query.all()
        return render_template("new_hub.html", items=items)
    # ... 30+ more routes

# Main entry
def register(app, db):
    """Called once from app.py."""
    from app import db  # late-import to avoid circular
    models = define_models(db)
    register_routes(app, db, models)
    seed_deepen(app, db, models)
```

`app.py` adds ONE line:

```python
from <feature>_deepen import register as register_deepen
register_deepen(app, db)
```

**Benefits**:
- Diff is +1 line in app.py, all new code is in the blueprint file
- No conflicts with parallel agents touching app.py
- Easy to remove/disable: just comment out the one line
- Easy to verify: `grep '_deepen' app.py` shows the wiring

### Task generator script

```python
# sites/<site>/_gen_tasks_deepen.py
"""Generates GUI tasks from current DB state. Idempotent."""
import json, re
from collections import Counter
from app import app, db
from <feature>_deepen import define_models

OUT = "tasks.jsonl"
SITE_PREFIX = "<Site>"

def main():
    with app.app_context():
        models = define_models(db)
        existing_ids = {json.loads(l)["id"] for l in open(OUT)}
        seen_prefix = Counter()
        new_tasks = []
        for family_id, gen in TASK_FAMILIES.items():
            for ques, item_id in gen(models):
                # 5-token prefix cap @5
                key = " ".join(re.findall(r"\w+", ques.lower())[:5])
                if seen_prefix[key] >= 5: continue
                seen_prefix[key] += 1
                # Generate unique id
                task_id = f"{SITE_PREFIX}--gui_{family_id}_{len(new_tasks):03d}"
                if task_id in existing_ids: continue
                new_tasks.append({
                    "web_name": SITE_PREFIX, "id": task_id, "ques": ques,
                    "web": "http://localhost:40000/", "upstream_url": "...",
                })
        with open(OUT, "a") as f:
            for t in new_tasks:
                f.write(json.dumps(t) + "\n")
        print(f"+{len(new_tasks)} tasks")

TASK_FAMILIES = {
    "hub_view": lambda m: [(f"On /{x.slug}, ...", x.id) for x in m["X"].query.all()[:50]],
    "detail_read": lambda m: [...],
    # 20-30 families, each ≤30 tasks (5-token cap will trim further)
}
```

Generates 1500-3000 tasks across 20-30 families deterministically.

### Verification before commit

```bash
# 1. byte-id reset
cp instance_seed/<site>.db instance/<site>.db
md5sum instance/<site>.db instance_seed/<site>.db
# both must match

# 2. smoke 20 routes
python3 -c "
from app import app
c = app.test_client()
for url in SAMPLE_URLS:
    r = c.get(url)
    assert r.status_code < 400, f'{url}={r.status_code}'
print('OK')
"

# 3. task-quality audit
python3 -c "
import json
rows = [json.loads(l) for l in open('tasks.jsonl')]
total = len(rows)
uniq_ques = len({r['ques'] for r in rows})
print(f'total={total} uniq={uniq_ques} ratio={uniq_ques/total:.2%}')
# Expect ratio > 90%
"

# 4. API-style task = 0
grep -cE '/api/|/graphql|parse the JSON|GET /api' tasks.jsonl
# Expect 0
```

### Numbers from 14 PR sites deepen pass

| Site | tpl_after | tasks_after | POST_after | img_util |
|---|---:|---:|---:|---:|
| ted | 47 | 3193 | 25 | 47% |
| drugs_com | 79 | 2298 | 47 | – |
| phys_org | 37 | 2306 | 22 | 41% |
| carmax | 81 | 1722 | 31 | **100%** |
| berkeley | 67 | 1984 | 24 | **74%** |
| compass | 70 | 2009 | 32 | – |
| mega | 68 | 2188 | 31 | 58% |
| osu | 64 | 1848 | 21 | – |
| rotten_tomatoes | 45 | 1716 | 26 | 53% |
| nba | 78 | 1613 | 25 | **94%** |
| imdb | 51 | 2120 | 27 | **94%** |
| recreation_gov | 49 | 2879 | 23 | 41% |
| craigslist | 39 | 1600 | 24 | 44% |
| phet_simulations | 47 | 1725 | 20 | – |

Median: 60 templates, 1992 tasks, 25 POST, 49% image utilization. Each agent took 15-45 min wall time.
