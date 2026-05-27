---
name: harden-env
description: "Phase 4: Harden environment difficulty by eliminating answer leaks, adding near-miss distractors, broadening the catalog, and ensuring cross-field consistency. This is the critical human-review step where most agent shortcuts are caught and fixed. Use after evolve-env when each task can be walked through but the environment may still be trivially easy."
---

# Harden Environment — Difficulty & Fidelity Hardening

## When to use

- After Phase 3 (evolve-env) when each task in `tasks.jsonl` is walkable
- When a reviewer reports tasks are too easy or have answer leaks
- When an agent solves tasks by clicking the first/only result

## Why this phase exists

Coding agents consistently produce environments where tasks are technically
solvable but trivially easy. The agent's implicit goal is "make the task
work," not "make it challenging." This leads to:

- Answers visible in search results without clicking detail pages
- Databases with only the target item (no distractors)
- Search results pre-sorted to put the answer at position #1

**Human review is essential.** Automated checks (`_health.py`, byte-identical
reset) verify correctness, not difficulty.

## The 4 hardening dimensions

### Dimension A: De-leak answers

For each task in `sites/<site>/tasks.jsonl`, check whether the answer is
visible without navigating to a detail page.

| Where to check | What to look for | Fix |
|---|---|---|
| Search result titles | Task constraint values in `product.name` | Strip from name, push to specs/description |
| Card subtitles | Pre-computed answers ("48 GB more storage") | Show raw values, force agent to compute |
| Section headings | Count labels next to a list | Remove count; let agent count items |
| Page titles | Task question echoed | Use descriptive titles, not questions |
| Search snippets | Answer text in preview | Truncate snippets |

**The 13 known leak archetypes** (from building 15 mirrors):

1. Numeric difference/comparison pre-computed
2. Count of items the agent should count
3. Verbatim task framing word echoed
4. Pre-bundled answer sentence
5. Pinned/highlighted answer callout
6. Spoon-fed list endings with count
7. Wiki one-paragraph matching task question
8. Operand-only fuzzy-match in search backends
9. Bare-anchor → answer-bucket flood (maps/places)
10. Algorithm-revealing UI text ("sorted by distance")
11. Sort order putting answer at position #1
12. Pre-curated lookup table with fuzzy matching
13. Constraint values in product/item names

### Dimension B: Near-miss distractors

For each task's natural search query, results should contain:

- 1-3 full-match items (the correct answers)
- ≥5 near-miss items (match category, fail ONE constraint)
- ≤50% full-match density overall

How to create near-misses: take a full-match and flip one constraint:
- Price above/below the target range
- Different spec (screen size, weight, color)
- Different brand/category close to target
- Remove one required feature

### Dimension C: Catalog breadth

Search queries must return ≥6 results from multiple sub-categories.

Signs of insufficient breadth:
- A zip code search returns only restaurants (add gyms, banks, pharmacies)
- A "laptop" search returns 3 results (add 15+ laptops across brands)
- A category page has only the target items

### Dimension D: Cross-field consistency

After modifying ANY field on an item, regenerate ALL related fields:

```
specs → source of truth
  ↓ regenerate ↓
description (prose matching specs)
features (bullet points from specs)
feature_tags (short labels from specs)
variant_options (if applicable)
name (should NOT contain constraint values)
```

**The bug that keeps hitting us**: change `specs["OS"]` from "Windows 11
Home" to "Windows 11 Pro" but leave `features` saying "Windows 11 Home
pre-installed." The detail page shows both, confusing agents.

## Verification process

Drive every check through Playwright, not curl. The point of hardening is to catch what a real browser-driving agent will see — only Playwright reproduces that surface. Reading templates by eye, or `curl | grep`, will silently miss client-side JS injections, hidden form fields, and async-rendered cards. Use the `agent_demo/` env (`uv sync` there already pulls Playwright + Chromium):

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"http://localhost:41000/?q={query}")     # alt-port test container
    page.wait_for_load_state("networkidle")
    page.screenshot(path=f"/tmp/{task_id}_search.png", full_page=True)
    rendered = page.content()                            # grep THIS for leaks
    # ...repeat for each task; only open detail pages via page.click(...), not by hand
```

For EACH task:

1. Open the mirror at `http://localhost:41000+i/` in Playwright
2. Read the task instruction from `tasks.jsonl`
3. Run the natural search query via `page.fill` + `page.click`; screenshot the results page; grep `page.content()` for the answer string
4. Count full-match vs near-miss results from the rendered DOM
5. Check ≥6 diverse results in the screenshot
6. Click into the correct answer's detail page via Playwright; verify all fields agree across specs / description / features
7. Record pass/fail per dimension, attach screenshot path

## After hardening: re-verify the invariants

Hardening changes seed data. After any DB change:

```bash
./scripts/build.sh webharbor:dev
docker run -d --rm --name wh-test \
  -p 8201:8101 -p 41000-41014:40000-40014 webharbor:dev
curl -X POST http://localhost:8201/reset/<your_site>
docker exec wh-test md5sum \
  /opt/WebSyn/<your_site>/instance/<your_site>.db \
  /opt/WebSyn/<your_site>/instance_seed/<your_site>.db
# md5s must match
```

If your hardening changes touched `static/images/` or seed DB, you'll also
need to bump `.assets-revision` after uploading to HuggingFace (see
`CONTRIBUTING.md`).

## Output

After Phase 4:
- Zero answer leaks across all tasks
- Each task has ≥5 near-miss distractors
- Search returns diverse results from multiple sub-categories
- Cross-field consistency verified
- Byte-identical reset still passes

---

## Lessons learned — leak semantics + audit script (IMDb 2026-05-26)

### Pattern 1: List-page leaks have nuance — chart ≠ search

The skill says "answer NOT visible at search-result level". On IMDb's
`/chart/top` page, the rating column IS visible by design — that's what
makes it a chart. Tasks like "what's the rating of the Top 250 #1" are
intentionally easy and the rating IS the answer surface. Not a leak.

Distinguish three list-page categories:

| Page type | Leak rule |
|---|---|
| **Curated chart / leaderboard** (Top 250, Box Office, Most Popular) | Whatever column the chart displays IS legitimate. Answers must come from a *different* field than what's columnated. |
| **Search results** (`/search?q=`, `/find?q=`) | Strict no-leak rule applies — answer must be on detail page. |
| **Genre / category browse** (`/genre/<slug>`) | Same as search — strict. |

Write the rule into the task itself: "what's the rating of #1 on Top 250"
is fine; "what's the runtime of #1 on Top 250" forces a detail click
because runtime isn't a chart column.

### Pattern 2: Stop words make distractor breadth queries return 0

The skill says "search returns ≥6 results from multiple sub-categories".
If you sanity-check with `q=the`, scored-search filters `the` as a stop
word and returns 0 — looks like a catastrophic catalog gap when it's just
the wrong probe.

**Use non-stop-word probes**: `q=man`, `q=love`, `q=war`, `q=star`,
`q=king`. These return 25-50 results each on a 392-title catalog.

### Pattern 3: Run a standardized data-quality audit script per site

After every seed regeneration, run a 10-question audit. The IMDb run
caught 1854 garbage persons + an all-zero box office column + 47 still-
empty profession fields by automating these checks rather than spot-checking.

Audit template (see also `clone-website` Pattern 3, 4, 6):

```python
# Q1: titles with HTML entities still in DB
n = Title.query.filter(Title.primary_title.like('%&%')).count()

# Q2: persons with HTML entities in name/bio
Person.query.filter(Person.name.like('%&%')).count()
Person.query.filter(Person.bio.like('%&apos%')).count()

# Q3: titles still showing original-language name (h1 vs ld.name mismatch)
# walk scraped JSONs, flag mismatches

# Q4: titles missing box office that should have it
# spot-check 5 well-known movies have non-zero box_office_us

# Q5: titles with year=None / rating=0 / no genres
Title.query.filter(Title.year.is_(None)).count()
Title.query.filter(Title.rating_avg == 0.0).count()

# Q6: persons with no profession / no bio / no birth_year
Person.query.filter(Person.primary_profession == '').count()

# Q7: same-name persons (potential duplicates from redirects)
db.session.query(Person.name, func.count(Person.id).label('n')) \
    .group_by(Person.name).having(func.count(Person.id) > 1).all()

# Q8: orphan persons (no credit) — scraped but never linked
Person.query.filter(~Person.id.in_(db.session.query(Credit.person_id))).count()

# Q9: missing posters / headshots
Title.query.filter(Title.poster_path == '').count()
Person.query.filter(Person.photo_path == '').count()

# Q10: chart coverage
Title.query.filter(Title.top_rank.isnot(None)).count()
Title.query.filter(Title.popularity_rank.isnot(None)).count()
```

Save as `/tmp/audit_<site>.py` and re-run after every seed change. The
IMDb run caught two production-blocking bugs (1854 garbage persons +
all-zero box office) only because this audit was written, not because
they showed up in route-level testing.

### Pattern 4: Cross-field consistency check is one curl

For each task's target entity, fetch the detail page and grep three
fields that should all agree:

```bash
B=http://localhost:44019
curl -s $B/title/tt0468569 | \
    grep -oE '<title>[^<]+</title>|<h1>[^<]+</h1>|class="big">[0-9.]+'
# Should print Dark Knight title, h1, and rating — all three consistent.
```

Skill Dimension D's "specs vs description vs features" is the typed
version; this is the lightweight version that catches simple mismatches
like h1=`Schindler's List` vs primary_title=`Schindler&apos;s List`.

### Pattern 5: Distractor near-miss arithmetic

For "X with constraint K" the skill wants `≥5 near-miss results` (match
category, fail one constraint). Calculate as:

```
near_miss_count = (results where K relaxed) - (results where K satisfied)
```

For IMDb--10 (Crime 1990s ≥8.5):

- full match (`crime + year:1990-1999 + rating>=8.5`): 14
- relaxed rating (`crime + 1990-1999 + rating>=8.0`): 18 → 4 near-miss
- cross-genre (`drama + 1990-1999 + rating>=8.5`): 23 — a different category of near-miss

4 < 5 is borderline. To bump near-miss count, either widen the catalog
(more 1990s crime titles) or relax the task's hardest constraint
(rating>=8.0 instead of 8.5).

## Next step

Proceed to **seed-database** (Phase 5) for final seed-DB stabilization and
the asset-split workflow.
