---
name: review-env
description: "Review pipeline for WebHarbor mirror PRs. Systematically verify visual fidelity, functional depth, byte-identical reset, and task quality of a submitted mirror site. Catches agent shortcuts (answer leaks, single-item catalogs, broken forms, placeholder images) that automated checks miss. Use when reviewing a GitHub PR + paired HF assets PR."
---

# Review Environment — Quality Verification Pipeline

## When to use

- Reviewing a GitHub PR that adds or modifies a website mirror
- Auditing an existing mirror for quality issues
- Verifying that hardening fixes actually resolved the problems

## Prerequisites

- The PR contributor has completed Phases 1-5 (clone → design → evolve → harden → seed)
- There is a paired PR on the HF dataset (`ChilleD/WebHarbor`)
- `.assets-revision` in the GitHub PR points to a real HF merge SHA

## Pipeline overview

### Step 1: Check out and build

```bash
gh pr checkout <pr-number>
./scripts/fetch_assets.sh             # pull the pinned HF revision
./scripts/build.sh webharbor:dev
docker run -d --rm --name wh-review \
  -p 8201:8101 -p 41000-41014:40000-40014 webharbor:dev
```

Confirm the new/changed site is on the expected port (40000 + index).

### Step 2: The mechanical checks (5 minutes)

Run the same Pre-PR checks the contributor was supposed to run.

```bash
# 1. all 15 sites return 200
for p in $(seq 41000 41014); do
  curl -so /dev/null -w "$p:%{http_code}\n" http://localhost:$p/
done

# 2. control plane healthy
curl -s http://localhost:8201/health | python3 -m json.tool | head

# 3. byte-identical reset on the touched site
curl -X POST http://localhost:8201/reset/<site>
docker exec wh-review md5sum \
  /opt/WebSyn/<site>/instance/<site>.db \
  /opt/WebSyn/<site>/instance_seed/<site>.db
# md5s MUST match

# 4. parallel reset still works for everyone
time curl -X POST http://localhost:8201/reset-all
```

If any of these fail, request changes; don't bother with the deeper review yet.

### Drive review with Playwright — NOT curl

Steps 3, 4, and 5 below MUST be performed by driving a real Chromium via Playwright. `curl | grep` and Flask `test_client` are not acceptable for visual / functional / task-quality review — they miss JS-rendered cards, client-side validation, async loads, and the actual DOM the benchmark agent will see. Use the `agent_demo/` env (it already has Playwright + Chromium installed via `uv sync`):

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:41001/")          # the site under review, alt port
    page.wait_for_load_state("networkidle")
    page.screenshot(path="/tmp/home.png", full_page=True)
    page.fill('input[name="q"]', "iphone")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.screenshot(path="/tmp/search.png", full_page=True)
    print(page.content()[:3000])                   # grep this for answer leaks
    browser.close()
```

Save every screenshot you capture; they go into the review comment as evidence. `curl` is only for control-plane endpoints (`/health`, `/reset`, `/reset-all`) and HTTP-200 sweeps.

### Step 3: Visual fidelity (10 min)

Open the mirror at `http://localhost:41000+i/` (via Playwright `page.goto` — see recipe above) and the real website side by side.

| Check | What to verify |
|---|---|
| Homepage layout | Header, nav, hero, cards, footer match the real site |
| Navigation | All top-level links work, no 404s |
| Real images | Product/article/profile images are real (not placeholders, not colored rectangles) |
| Detail pages | Open 5+ random detail pages; layout matches, content populated |
| Typography | Fonts and colors close to original (not pixel-perfect, but same brand feel) |
| Responsive | Resize to 768px — layout adapts, no overflow |

Capture side-by-side screenshots for your review comment.

### Step 4: Functional depth (15 min)

Actually drive the site through Playwright — `page.fill` / `page.click` / `page.reload` / `page.content()`. Capture a screenshot for each check below.

| Check | How to test |
|---|---|
| Login | `alice.j@test.com` / `TestPass123!` → redirects to account, shows user name |
| Register | Create a new account, can log back in |
| Search | Try 3+ queries including multi-word ("Boston Celtic players") |
| Browse | Click 3+ categories; pages load with populated content |
| CRUD: add | Cart/bookmark/favorite an item; reload page; it persists |
| CRUD: remove | Remove the item; count updates, item gone |
| Forms | Submit review/contact/checkout; validates input, persists to DB |
| Account edit | Change display name; persists after reload |

### Step 5: Task quality audit (the most important part, 20-30 min)

For EACH task in `sites/<site>/tasks.jsonl`:

#### Solvability
- Can you actually complete the task using only the mirror's UI?
- Does the expected answer exist in the environment?

#### Answer-leak detection
Perform the task's natural search query. Check:
- Answer NOT visible in search result titles/cards
- Answer NOT pre-computed in headings or callout boxes
- Answer requires clicking into a detail page
- Count-based answers don't have count labels visible

If you solve the task from the search-results page alone, it's a **leak**.

#### Distractor check
On the search results for each task's query:
- ≥6 total results
- ≤50% are full matches (satisfy ALL task constraints)
- Near-miss items exist (match category, fail one constraint)
- Results come from multiple sub-categories

If every result satisfies the task, the catalog is **too narrow**.

#### Difficulty assessment
- ≥3 tasks require ≥5 agent actions
- ≥2 tasks involve multi-step reasoning or comparison
- ≥1 task would challenge a frontier model (GPT-4o / Claude)
- No task solvable by clicking the first result

### Step 6: Common agent pitfalls

Based on 15+ mirror reviews:

| # | Issue | Quick check |
|---|---|---|
| 1 | Task constraint values in product/item names | Search each constraint term, see if it appears in card titles |
| 2 | Single-item catalog for task targets | Count unique items matching each task category |
| 3 | Strict-AND search | Search a multi-word query ("Boston Celtic") — must return results |
| 4 | Placeholder images | Scroll listing pages, spot-check 10 items |
| 5 | Forms that don't validate | Submit empty form, submit malformed email |
| 6 | Pre-sorted results revealing answer | Check if answer is always at position #1 |
| 7 | Inconsistent specs across fields | Compare specs table vs description vs features on a detail page |
| 8 | Missing auth-gated features | Log in, try cart/checkout/bookmarks/order-history |
| 9 | Count labels next to lists agent should count | Look for "N items", "N results", "N courses" |
| 10 | Cross-imports between sites | Grep for `from sites.<other>` (sites must be isolated) |

### Step 7: Asset PR check

Verify the paired HuggingFace PR is real:

```bash
cat .assets-revision
# revision: <some-sha>

# go to https://huggingface.co/datasets/ChilleD/WebHarbor/commit/<sha>
# confirm: that commit exists, is merged, and contains the expected assets
```

If `.assets-revision` doesn't match a real HF merge SHA, request changes.

### Step 8: Submit review

Leave a structured comment on the PR:

```markdown
## Review: <site_name>

### Mechanical checks: PASS / FAIL
- [x] All 15 sites return 200
- [x] Control plane healthy
- [x] Byte-identical reset (md5 match)
- [x] Parallel reset <10s
- [x] HF revision SHA verified

### Visual fidelity: PASS / FAIL
- [x] Layout matches real site
- [x] Real images, no placeholders
- [ ] Footer links broken → /about returns 404

### Functional depth: PASS / FAIL
- [x] Auth flows work
- [x] Search returns scored results
- [ ] Checkout form doesn't validate payment

### Task quality: PASS / FAIL
- Task 3: LEAK — "iPhone 17 Pro" appears in search card title
- Task 7: TOO EASY — only 2 results match the query
- Task 12: GOOD — requires 6-step comparison

### Required fixes before approval:
1. De-leak task 3: strip "Pro" from product card title
2. Add 10+ distractor phones for task 7
3. Fix /about 404
4. Add payment validation in checkout

### Screenshots:
[attach side-by-side and issue screenshots]
```

## Reviewer authorship

Reviewing **5 environments** with thorough checklist reports earns a spot
on the final paper's author list. Quality matters: a review that says
"looks good" without evidence doesn't count.

## Teardown

```bash
docker stop wh-review
```

---

## Lessons learned — pre-PR audit checklist (IMDb 2026-05-26)

The contributor side of this skill applies just as much when *you* are
about to open a PR. Use this 10-step audit before `gh pr create` — most of
these are mechanical and take under 30 seconds each.

### The 10-item pre-PR audit

```bash
SITE=imdb  # or whatever
PR_ROOT=~/repos/WebHarbor-${SITE}-pr

cd $PR_ROOT

# 1. branch is based on origin/main, not local main
git log --oneline origin/main..HEAD | head -5
git log --oneline HEAD..origin/main | wc -l   # should be 0 (no missed commits)

# 2. only your site's files (and the 3 registration files + README) appear
git diff --cached --stat origin/main

# 3. no secrets / tokens leaked
grep -rEn 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}' sites/$SITE/

# 4. python syntax compiles
python3 -m py_compile sites/$SITE/app.py sites/$SITE/seed_data.py sites/$SITE/_health.py

# 5. all tasks.jsonl lines are valid JSON + have required 5 fields
python3 -c "
import json
req = {'web_name', 'id', 'ques', 'web', 'upstream_url'}
with open('sites/$SITE/tasks.jsonl') as f:
    for i, l in enumerate(f, 1):
        if not l.strip(): continue
        d = json.loads(l)
        miss = req - set(d.keys())
        if miss: print(f'line {i}: missing {miss}')
"

# 6. all task IDs unique + single port
python3 -c "
import json; ids=set(); ports=set()
for l in open('sites/$SITE/tasks.jsonl'):
    d=json.loads(l); ids.add(d['id']); ports.add(d['web'])
print(f'unique ids: {len(ids)}; single port: {len(ports)==1} ({ports})')
"

# 7. flask test_client shows all routes <500
python3 -c "
import sys; sys.path.insert(0,'sites/$SITE')
from app import app
with app.test_client() as c:
    for p in ['/', '/_health', '/login']:   # add your routes
        r = c.get(p); assert r.status_code < 500, f'{p}: {r.status_code}'
print('all routes <500')
"

# 8. README/CONTRIBUTING port range + site list bumped
grep -nE '40000-?40[0-9]+|[0-9]+ (sites|mirrors|local|distinct)' README.md

# 9. no recon/scraper artifacts accidentally tracked
git ls-files sites/$SITE/ | grep -E 'recon|scrape|inspect' && echo 'BAD: scraper files tracked'

# 10. .assets-revision unchanged (will be bumped after HF merge)
git diff --cached -- .assets-revision   # should be empty
```

If any check fails, fix and re-run. Don't `gh pr create` with unfixed audit
items — review noise wastes everyone's time.

### Common bugs the audit catches

From IMDb run + general experience:

| Bug | Caught by |
|-----|-----------|
| HTML entities in titles (`Schindler&apos;s`) | step 7 + visual check |
| Box office all zero (lowercase testid keys) | step 7 visiting a known title |
| 0-row seed DB (Dockerfile RUN trap) | seed-database Pattern 6 |
| Hardcoded `/home/...` paths | `grep -rn '/home/' sites/$SITE/` |
| `__pycache__` accidentally committed | step 2 |
| Tasks reference dropped entities | step 7 + curl walk |
| README still says "15 sites" | step 8 |
| `.assets-revision` prematurely bumped | step 10 |

### Worktree-from-origin/main is mandatory for clean PRs

Repeating because it's the single biggest source of PR noise:

```bash
git fetch origin
git worktree add ~/repos/WebHarbor-${SITE}-pr origin/main -b feat/${SITE}-mirror
```

If you skip this and branch from local main, every other in-flight PR's
files show up in your diff. Reviewers can't tell what's yours; CI may
fail because your PR claims to touch files you didn't touch.

### Two-PR coordination workflow (from the contributor side)

The seed-database skill describes this from the maintainer's view. From
your view:

1. Push HF asset PR first (`hf upload <upstream> --create-pr`) so you have
   a URL to reference in the GitHub PR description
2. `gh pr create` with the HF PR URL in the body
3. Watch HF PR for merge → grab merge commit SHA
4. On code PR branch: bump `.assets-revision` to that SHA → push
5. Ping the maintainer on the code PR

Don't rush step 4 — if the HF PR isn't merged yet, the code PR can't be
fetched-and-built end-to-end by reviewers.

