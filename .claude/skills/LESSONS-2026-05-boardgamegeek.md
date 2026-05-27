# Lessons from the BoardGameGeek mirror (2026-05)

This is the war-story log behind the iteration of the WebHarbor skills.
Each lesson here is also referenced from the SKILL.md it most affects
(clone-website / design-tasks / evolve-env / harden-env / seed-database /
review-env). Read it once, then go back to the skill files for the
mechanical recipes.

Site: `sites/boardgamegeek/`
PR: https://github.com/aiming-lab/WebHarbor/pull/35
HF PR: https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/25
Outcome: 500 base games + 5,169 expansions, 5,246 ratings, 11,338 cover
images, 32/32 Playwright handwalk checks, byte-identical reset
`10a5b3d4ae85380d8019bd9ac7cf9e61`.

---

## 1. Scraping (clone-website)

### 1a. The CF-gated-paramcombo trap
The BGG `api.geekdo.com` endpoints look open (no `Authorization` header
required for the queries we ran), but a *subset* of query-param combos
silently return `{"items": []}` from a `curl` while returning real data
from a real Chromium tab. Examples we hit on `/api/collections`:

- `sort=lowest&require_review=true`  →  works in browser, empty from curl
- `sort=rating&direction=asc`        →  same
- `minrating=1&maxrating=5`          →  returns `{"errors": [...]}`

Diagnosis: BGG's WAF allows these *only* when the request carries a
fresh CF challenge cookie. Without it, the server returns 200 + an empty
shell rather than 401 — easy to miss.

**Recipe to detect:** before relying on a param combo, capture the same
request from a real Chromium via `page.on("response")` and compare body
length:

```python
captured = []
page.on("response", lambda r: r.url.startswith("https://api.geekdo.com/api/collections") and captured.append((r.url, r.text())))
page.goto("https://boardgamegeek.com/boardgame/174430/gloomhaven/ratings?sort=lowest")
page.wait_for_timeout(8000)
# Diff: curl returns 0 items, browser returns 50.
```

**If you can't beat the gate:** document the limitation in the PR body
(see PR #35 "Known limitation: BGG `sort=lowest` API is CF-gated"), keep
the scraper script in-repo (we kept `scrape_low_ratings.py` even though
it returns empty), and rewrite the affected tasks to use a different
sort/filter that DOES work (we swapped "lowest rating" → "most helpful
thumbs").

### 1b. Per-page Playwright context for browse loops
Hitting `boardgamegeek.com/browse/boardgame/page/N` for `N` in 1..15
**inside a single Playwright context** fails after page 2 with `Target
page, context or browser has been closed`. Cause: CF re-challenges
mid-session and the context dies before re-solving.

Fix: spin a *new* `browser.new_context()` per page, with a
`time.sleep(1.5)` between pages. ~15s/page but reliable through 15
pages. See `sites/boardgamegeek/scrape_bgg.py::scrape_top_pages`.

### 1c. Unbuffered output for long-running scrapers
`python script.py > /tmp/log 2>&1` buffers stdout in 4 KB chunks when
the destination is a pipe — for a 15-minute scraper that prints every
50 items, you'll see **nothing** for the first 10+ minutes, then a
dump. We waited 11 minutes thinking the scraper was wedged.

Fix: at the top of every long-running script:

```python
import functools
print = functools.partial(print, flush=True)
```

Or invoke with `python -u script.py`. Either way, also write progress
to a small `progress.json` so a sibling process can read it without
fighting the same buffer.

### 1d. Two-pass scraping for linked-entity catalogs
The first pass got the top 500 games. Twilight Struggle's detail page
listed 11 expansions, but Twilight Struggle: "Anni di Piombo" Promo Card
(rank: thousands) was NOT in our top-500 catalog, so the expansion link
**resolved to nothing** in the seed. Game detail page showed "0
expansions."

Fix: run a second pass that follows `boardgameexpansion` links from
every top-pass entity. Add the linked entities as Game rows with
`subtype='boardgameexpansion'` (we use the same model, just a flag).
This grew the catalog from 500 → 5,669 games — see
`sites/boardgamegeek/scrape_extras.py`.

After the second pass: Twilight Struggle expansions page shows the real
11.

### 1e. Defensive shape checks on API responses
The BGG API returns `/api/user` as either `[{user...}]` (list) or
`{user: {...}}` (dict) depending on the user. Our first scraper crashed
with `'list' object has no attribute 'get'`.

```python
base = fetch_json(f"{API}/user?username={username}")
if isinstance(base, list):
    entry = base[0] if base else None
elif isinstance(base, dict):
    entry = base.get("user") or base
else:
    entry = None
```

Same applies to `it.get("rating")` which can be `int | float | str |
{rating: int | dict}` — always type-check before drilling.

---

## 2. Tasks (design-tasks + harden-env)

### 2a. Don't ask for fields that browse tables already show
Original BGG--0: "Find the #1 ranked game and report its **designer and
year**." The browse table shows year in the "title (year)" column —
agent reads it without clicking. After fix: "...report its
**designer(s)**" only.

Rule of thumb: anything in the rank-table columns (year, avg rating,
voter count, weight, rank) is fair to read FROM the list; tasks should
ask for fields that exist ONLY on the detail page (designer, artist,
description, polls, language dependence, expansions, reviews).

### 2b. Pick mechanics whose top-by-rank game differs from the overall #1
Original BGG--12 was "highest-ranked game using Hand Management" — the
answer was Brass: Birmingham (overall #1), same as BGG--0. Two distinct
tasks with the same answer.

Fix: switch to a mechanic whose top game differs. Action Points → top is
Pandemic Legacy: Season 1 (rank 3). We checked Tile Placement, Action
Points, Variable Player Powers, Set Collection, Drafting, Modular Board,
Cooperative Game, Dice Rolling, Solo / Solitaire Game, Hexagon Grid,
Network and Route Building before picking.

### 2c. Search results may include base + expansions; use direct URLs
Search for "Ark Nova" returns both the base game AND
"Ark Nova: Marine Worlds" (expansion). Playwright
`page.locator('a:has-text("Ark Nova")').first.click()` may click the
expansion (which is alphabetically/score-first depending on token weight).

For **ground-truth handwalk tests**, always navigate by direct URL:

```python
page.goto(f"{ROOT}/boardgame/342942/ark-nova", wait_until="domcontentloaded")
```

For task **prompts** that target a specific game, name disambiguation
fields explicitly: "Compare **Brass: Birmingham (2018)** and **Ark Nova
(2021)**".

### 2d. Tab-bar parenthesized counts are answer leaks
"Expansions (11)" on the tab bar → agent reads "11" without clicking
the tab. Same for "Forums (N)".

Fix: drop counts from tab labels. Let the agent count rows on the
landing page. We learned this is **harden-env archetype #14** — added
to `.claude/skills/harden-env/SKILL.md`.

### 2e. Benchmark users shouldn't dominate edge answers
Wingspan's lowest rating in our seed is `7.0` by `carol_d` (benchmark
user). If a task asks "the lowest rating on Wingspan", the answer leaks
the benchmark account.

Fix paths:
1. **Re-frame the task** (cheapest): we changed BGG--14 from "lowest" to
   "most helpful (thumbs)" — answer is `ogzz, 23 thumbs`, a real user.
2. **Move the bench user's rating out of edge positions**: seed_data.py
   could clamp bench ratings to the median ±1 so they never appear at
   the top or bottom of any sort.
3. **Re-scrape the underlying real data**: only possible if the API
   isn't gated (see 1a).

### 2f. Item overview should NOT show individual reviews
Real BGG's game overview DOES show top reviews — but for benchmark
purposes that's a shortcut. We removed the "Top Reviews" section from
`item.html` overview. Agents must navigate to the Ratings tab to read
individual reviews. The summary stats (avg rating, voter count) stay
in the overview's stats box.

---

## 3. Hand-walk Playwright (evolve-env + review-env)

### 3a. Form-submit selector must be anchored to the form
Naive `page.click('button[type="submit"]')` matches:
1. Header search button (form action=/search method=GET)
2. Header logout form (action=/logout method=POST) — **PRESENT FOR LOGGED-IN PAGES**
3. The form on the page you actually want

We spent 4 iterations debugging why `login()` "succeeded" but downstream
tests failed — Playwright was clicking the header search button, not the
login submit. After `login()` "succeeded", the page was at
`/search?q=&type=boardgame`, not `/user/<name>`.

Diagnosis: `print(page.url)` and `print(page.title())` after every
critical click.

Fix: anchor the submit selector to a field unique to the form:

```python
# Login form has a unique input[name="password"]:
page.locator('input[name="password"]') \
    .locator('xpath=ancestor::form//button[@type="submit"]') \
    .first.click()

# GeekList-new form has input[name="title"]:
page.locator('input[name="title"]') \
    .locator('xpath=ancestor::form//button[@type="submit"]') \
    .first.click()
```

Or use a CSS attribute selector that targets the form by `action`:

```python
page.locator('form[action*="/rate/"] button[type="submit"]').click()
```

### 3b. Login success check should be URL-based, not content-based
`return "Welcome" in page.content() or username in page.content()`
fails when `username in page.content()` matches an unrelated string
(e.g. the username column on a search page that happened to be the
landing page after a failed login form post).

Better: check the *destination URL*:

```python
return f"/user/{username}" in page.url or "Sign out" in page.content()
```

### 3c. Hand-walk failure can be the test's fault, not the env's
Three "real env bug" alarms from our first Playwright run were actually
test bugs:
- BGG--2 "only 40 of top 100 visible on weight-sorted page" — math is
  correct; weight ≠ rank, so only 40 ranked-top-100 games appear in
  weight-sorted top 100.
- BGG--10 "Ark Nova weight=0.00" — selector matched an Ark Nova expansion
  page, not the base game.
- BGG--20 "1 expansion link on TS expansions page" — wrong tab clicked;
  navigation hit the breadcrumb instead.

Always reproduce manually with `curl` against the same URL before
filing the env bug.

---

## 4. Seed DB stabilization (seed-database)

### 4a. Multi-source merge before the seed loop iterates
We had `bgg.json` (first pass) and `bgg_extras.json` (expansion pass).
Wrong: seed once from bgg.json, then run a second pass that mutates
existing rows. The second pass bumps SQLite metadata even when no rows
change, breaking byte-identity.

Right: merge the two JSONs into a single in-memory `data` dict, THEN
run the single seed loop. We extended `seed_data.py` to detect
`scraped_data/bgg_extras.json` and merge it before the main loop. See
the comment block "Optional: expansion + low-rating augmentation pass
(scrape_extras.py)."

### 4b. Pinned random.Random — don't mix with the global RNG
Every call to `random.choice(...)` uses Python's global RNG, which is
seeded from time at import. Across runs, byte-identity breaks.

Use a module-level `_R = random.Random(N)` and pass it everywhere:

```python
_R = random.Random(20260526)
...
def _seed_geeklists(db, games_by_bgg, users_by_name, R):
    ...
    comment_body = R.choice([...])
```

Audit your seed file: `grep -n "random\." | grep -v "_R\.\|R\."`
should return zero results.

### 4c. Per-game side data is only for primary subtypes
We created per-game `Forum` rows for every game. With 5,669 games
(500 base + 5,169 expansions), the `forums` table hit 39,695 rows —
most empty. Real BGG only has forums on base games.

Fix: guard the forum creation loop on `g.subtype == 'boardgame'`.
Brought us back to 3,512 forums.

### 4d. flush vs commit, in one place
We had `db.session.commit()` between sub-phases. Each commit triggers a
WAL/journal write that breaks byte-identity even when no rows changed.

Rule: `db.session.flush()` between phases (makes inserted IDs queryable),
ONE `db.session.commit()` at the end of `seed_database()`.

### 4e. HF upload via Python API, not via the broken `hf` CLI
`hf upload <repo> <local> <remote> --repo-type dataset` currently fails
with `AttributeError: 'Sentinel' object has no attribute 'strip'` —
Typer 0.17 incompatibility with the way `--repo-type` is declared.

Use the Python API:

```python
from huggingface_hub import upload_file, create_commit, CommitOperationAdd
token = open('/home/<you>/.cache/huggingface/token').read().strip()

# Upload to your fork:
upload_file(
    path_or_fileobj='/tmp/wh-static-pr/<site>.tar.gz',
    path_in_repo='<site>.tar.gz',
    repo_id='<your-user>/WebHarbor',
    repo_type='dataset',
    commit_message='feat(<site>): add <site>.tar.gz',
    token=token,
)

# Open a PR (discussion) on upstream — this is what the IMDb PR did:
create_commit(
    repo_id='ChilleD/WebHarbor',
    repo_type='dataset',
    operations=[CommitOperationAdd(
        path_in_repo='<site>.tar.gz',
        path_or_fileobj='/tmp/wh-static-pr/<site>.tar.gz',
    )],
    commit_message='feat(<site>): add <site>.tar.gz',
    commit_description='Paired with github.com/aiming-lab/WebHarbor#XX',
    create_pr=True,
    token=token,
)
# Returns CommitInfo with .pr_url, .pr_num
```

---

## 5. PR workflow (cross-cutting)

### 5a. Parallel agents = unstable SITES list
While we worked, other agents added discogs, compass, osu, craigslist,
ted, nba, mega to `websyn_start.sh` SITES + `control_server.py` SITES.
Every few minutes our `boardgamegeek` entry was overwritten and the
container booted with the OLD SITES list. We re-added at the END five
separate times.

Defensive strategy: **branch off origin/main and add ONLY your site +
the 3 reg files** before opening the PR. Don't try to merge the local
SITES list. The PR-base diff will show your addition cleanly; the
maintainer resolves conflicts at merge time.

```bash
git stash push -m "wip" -- <unrelated changes>
git checkout -b feat/<site>-mirror origin/main
git checkout main -- sites/<site>/  # restore your files
# now edit the 3 reg files: append your site at the END
```

### 5b. Container name + alt port range must avoid contention
Default `wh-test` / 41000-41014 collides with other agents. Pick a
unique name (`wh-bgg5`) and port range that's known-free
(`-p 42034:40030`). Other agents kept removing our container — we burned
3 fresh builds before realizing.

### 5c. Use the IMDb PR (#33) as the template for the body
Same section order: Summary / Catalog / Routes / Benchmark users /
tasks.jsonl / Skill-conformance / Paired HF PR / Test plan.

Add a **"Known limitation"** section for anything that the skill rules
imply but you couldn't deliver (e.g. low-end rating distribution). Don't
hide it in a footnote; the maintainers want to know upfront.

---

## 6. Container fragility under parallel review

When you start the verification container, **always assume some other
agent will kill it within minutes**. Don't keep state in the container
expecting it to persist across handwalk steps. Re-build, re-start, and
re-verify in a single short cycle. If your handwalk takes >5 minutes,
break it into chunks that each finish in <5 min and re-start the
container between chunks.

---

## 7. Final by-the-numbers

| Lesson | Time cost without it | Time cost with it |
|---|---|---|
| 1a (CF-gated detection) | Wasted 25 min scraping low ratings that came back empty | 2-min Playwright capture, then move on |
| 1b (per-page context) | First scraper died after 200 games, had to restart twice (15 min wasted) | New context per page, ~15s/page reliable |
| 1c (unbuffered output) | 11 min thinking scraper was wedged | Add 2 lines, see progress live |
| 3a (form-submit selector) | 4 iterations × ~30 min each debugging Playwright | 5 lines per critical form, works first try |
| 4a (multi-source merge) | First seed pass produced non-deterministic md5 | Single merged dict, byte-identical from run 1 |
| 5a (parallel SITES churn) | Re-added boardgamegeek 5 times across 90 min | Branch from origin/main, ignore local main |

Total time saved if these were known up-front: ~3 hours on a single mirror.
