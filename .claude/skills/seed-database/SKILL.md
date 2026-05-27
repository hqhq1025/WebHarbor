---
name: seed-database
description: "Phase 5: Finalize the seed DB and ship the asset side of the change. Covers idempotent seeding (the byte-identical reset invariant), benchmark test users, scored search, and the two-repo workflow: code goes to github.com/aiming-lab/WebHarbor, heavy assets (instance_seed DBs, static/images) go to huggingface.co/datasets/ChilleD/WebHarbor, then .assets-revision pins them together."
---

# Seed Database — Final Stabilization & Asset Workflow

## When to use

- Finalizing a mirror before opening PRs
- After harden-env when DB / image changes need to be persisted
- When debugging "byte-identical reset failed" issues

## Layout reminder

`instance_seed/*.db` and `static/images/` for every site are stored in the
HuggingFace dataset `ChilleD/WebHarbor`, NOT directly in git.
`.assetpaths` in this repo lists which paths are HF-managed; `.gitignore`
keeps them out of git; `.dockerignore` does NOT ignore them (they must ship
in the image).

`.assets-revision` pins the exact HF dataset commit the image was built
against. Bumping this file is the final step of any change that touches
seed DBs or images.

## Seeding requirements

### 1. Idempotent seed functions (the byte-identical reset invariant)

Every `seed_*()` function in `app.py` or `seed_data.py` MUST early-return
when the DB is already populated:

```python
def seed_database():
    if Product.query.count() > 0:
        return                    # ← gate the WHOLE function
    # ... seed rows ...

def seed_benchmark_users():
    if User.query.filter_by(email='alice.j@test.com').first():
        return
    # ... seed 4 users ...

with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()
```

**Per-row gates are NOT enough.** Even a no-op `db.session.commit()` bumps
SQLite metadata, breaking `/reset/<site>` byte-identity. Gate every seed
function as a whole.

Diagnose with:

```bash
docker exec wh-test md5sum \
  /opt/WebSyn/<site>/instance/<site>.db \
  /opt/WebSyn/<site>/instance_seed/<site>.db
# must match

docker restart wh-test && sleep 5
docker exec wh-test md5sum \
  /opt/WebSyn/<site>/instance/<site>.db \
  /opt/WebSyn/<site>/instance_seed/<site>.db
# must STILL match
```

### 2. Benchmark test users

Seed exactly 4 users:

```python
USERS = [
    {'username': 'alice_j', 'email': 'alice.j@test.com', 'display_name': 'Alice Johnson'},
    {'username': 'bob_c',   'email': 'bob.c@test.com',   'display_name': 'Bob Chen'},
    {'username': 'carol_d', 'email': 'carol.d@test.com', 'display_name': 'Carol Davis'},
    {'username': 'david_k', 'email': 'david.k@test.com', 'display_name': 'David Kim'},
]
PASSWORD = 'TestPass123!'
```

Each should have pre-existing:
- Cart/bag items (2-4)
- Bookmarks/favorites/saved items (3-6)
- Order history (1-3 past orders)
- Profile with address & payment method (for checkout tasks)

### 3. Realistic catalog volume

| Entity | Min seed count | Why |
|---|---|---|
| Primary (products, articles, courses) | 50-200 | Realistic browse/search |
| Categories/sections | 5-15 | Real-site taxonomy |
| Reviews per popular item | 3-10 | Detail pages feel populated |

### 4. Scored search (NEVER strict AND)

Multi-word queries like "Boston Celtic players" fail strict matching.
Use token-overlap scoring:

```python
import re

STOP_WORDS = {'the','a','an','in','on','at','to','for','of','and','or','is','it','by','with'}

def scored_search(query, items, fields=['name','description']):
    tokens = [t.lower() for t in re.split(r'\W+', query)
              if t.lower() not in STOP_WORDS and len(t) > 1]
    if not tokens:
        return items
    results = []
    for item in items:
        text = ' '.join(getattr(item, f, '') or '' for f in fields).lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            results.append((item, score))
    results.sort(key=lambda x: -x[1])
    return [r[0] for r in results]
```

### 5. Runtime data lives in the seed DB, not JSON

HTTP handlers must read from SQLAlchemy, not from `scraped_data/*.json`.
If you have intermediate scrape JSON, fold it into `instance_seed/<site>.db`
at build time via `seed_data.py`. `scraped_data/` is gitignored and
dockerignored — never shipped.

### 6. Date pinning

If tasks reference relative dates ("order placed 3 days ago"), pin a
reference date:

```python
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15)
# Replace all datetime.utcnow() with this constant in seed scripts
```

## Asset-side workflow: ship to HuggingFace

After all DB/image changes are stable, push the heavy assets to HF:

```bash
# 1. Split assets out of this repo into a staging directory
./scripts/extract_assets.sh ../wh-static-pr/

# 2. Review the diff in the HF web UI before uploading
cd ../wh-static-pr
hf upload-large-folder <your-fork>/WebHarbor . --repo-type dataset

# 3. Open a PR on https://huggingface.co/datasets/ChilleD/WebHarbor
# 4. After it's merged, grab the merge commit SHA.

# 5. Back in the code repo, bump the pin:
cd ../webharbor
sed -i "s/^revision:.*/revision: <hf-merge-sha>/" .assets-revision

# 6. Commit + open the GitHub PR (referencing the HF PR)
git commit -am "feat(<site>): add new site

Adds Flask app, templates, and seed DB for <real-site-name>.
Assets uploaded to HF; .assets-revision bumped to <sha>."
gh pr create
```

## Final verification

```bash
./scripts/check_assets.sh                       # every site has instance_seed/
./scripts/build.sh webharbor:dev                # docker build succeeds
docker run -d --rm --name wh-test \
  -p 8201:8101 -p 41000-41014:40000-40014 webharbor:dev

# all 15 sites return 200
for p in $(seq 41000 41014); do
  curl -so /dev/null -w "$p:%{http_code}\n" http://localhost:$p/
done

# parallel reset under 10s
time curl -X POST http://localhost:8201/reset-all

# byte-identity for every site
for s in allrecipes amazon apple arxiv bbc_news booking github \
         google_flights google_map google_search huggingface \
         wolfram_alpha cambridge_dictionary coursera espn; do
  docker exec wh-test md5sum \
    /opt/WebSyn/$s/instance/$s.db \
    /opt/WebSyn/$s/instance_seed/$s.db
done

docker stop wh-test
```

## Output

After Phase 5:
- `sites/<site>/instance_seed/<site>.db` is a stable, idempotent seed
- All 4 benchmark users exist with pre-populated data
- Scored search returns diverse results
- HF dataset PR opened and merged
- `.assets-revision` bumped to the HF merge SHA
- Both GitHub and HF PRs cross-reference each other

---

## Lessons learned — HF push + clean-PR workflow (IMDb 2026-05-26)

### Pattern 1: `hf upload --create-pr` is a one-line replacement for the fork+UI dance

The CONTRIBUTING workflow shows pushing to your fork, then opening a PR
through the HF web UI. There's a much shorter path:

```bash
hf upload ChilleD/WebHarbor /tmp/wh-static-pr/imdb.tar.gz imdb.tar.gz \
    --repo-type dataset --create-pr \
    --commit-message "Add IMDb mirror assets" \
    --commit-description "$(cat <<EOF
392 titles + 3796 persons + 4280 real posters/headshots scraped via
Playwright from imdb.com. Paired with code PR adding sites/imdb/ to
aiming-lab/WebHarbor at port 40015.
EOF
)"
```

This pushes directly to a `refs/pr/N` branch in the upstream repo and
opens a PR for you. No fork-side push, no web UI step.

Find the PR number afterwards:

```bash
curl -s -H "Authorization: Bearer $(cat ~/.cache/huggingface/token)" \
     "https://huggingface.co/api/datasets/ChilleD/WebHarbor/discussions?type=pull_request&status=open&sort=recently-created" | \
     python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"#{p['num']}: {p['title']}\") for p in d['discussions'][:3]]"
```

### Pattern 2: Always verify the HF upload round-trips

After upload, download the tarball back and md5-check it. Catches corrupted
uploads, partial uploads, and CDN cache misses:

```bash
mkdir -p /tmp/hf-verify
curl -sL -o /tmp/hf-verify/$site-from-hf.tar.gz \
    https://huggingface.co/datasets/<repo>/resolve/<commit-sha>/$site.tar.gz
md5sum /tmp/hf-verify/$site-from-hf.tar.gz /tmp/wh-static-pr/$site.tar.gz
# both must match
tar -tzf /tmp/hf-verify/$site-from-hf.tar.gz | wc -l
# expected: instance_seed/<site>.db + every image file + dir entries
```

### Pattern 3: Open the GitHub PR from a fresh worktree based on origin/main

If you work on the main repo directly, your local `main` accumulates merge
commits from every other in-flight PR. Branching off it and pushing creates
a PR diff that includes 30+ unrelated file changes.

**Use a worktree off `origin/main`** for the PR branch:

```bash
cd ~/repos/WebHarbor
git fetch origin
git worktree add ~/repos/WebHarbor-<feature>-pr origin/main -b feat/<feature>
cd ~/repos/WebHarbor-<feature>-pr

# Copy in your changes from the main checkout:
rsync -a --exclude='__pycache__' --exclude='scraped_data' \
      --exclude='instance/' --exclude='static/images/' \
      --exclude='static/external_cache/' \
      ~/repos/WebHarbor/sites/<site>/ sites/<site>/

# Apply the three-site registration patches manually on top of origin/main
# (the local main's SITES list looks nothing like origin/main's).

git add -A
git commit -m "..."
git push -u fork feat/<feature>
gh pr create --repo aiming-lab/WebHarbor --head <user>:feat/<feature> --base main
```

This guarantees the PR shows only your intended diff.

### Pattern 4: Port slot in PR is based on origin/main, not local main

`origin/main` has 15 sites → your new site goes at port `40000+15 = 40015`,
not at whatever your local main shows. If 10 other PRs land before yours,
the maintainer rebases your branch to the new port slot during merge —
your job is to write the patch against origin/main only.

This means **don't hardcode your local-main port number in the PR
description** ("Adds IMDb at port 40019" is wrong if 40019 belongs to
some other already-merged PR upstream).

### Pattern 5: README has more port references than you think

The README and CONTRIBUTING.md docs contain at least three hardcoded
references that drift when you add a new site:

```bash
# Find all of them before committing:
grep -nE '40000-?40[0-9]+|[0-9]+ (sites|mirrors|local|distinct)' README.md CONTRIBUTING.md AGENTS.md
```

For IMDb on top of origin/main (15 → 16 sites), three places needed bumping:

| File | Pattern | Old | New |
|---|---|---|---|
| README.md | "N sites today" | 15 | 16 |
| README.md | `docker run -p 40000-40014` | 40014 | 40015 |
| README.md | "explore N local mirrors ... and X, Y, Z" | 15-site list | append IMDb |

Don't trust local main's README — it's been bumped by other in-flight PRs.

### Pattern 6: `--rm` on PR-final container hides build-time failures

The first build of the IMDb PR ran `RUN cd /opt/WebSyn/imdb && python3 -c
"from app import app"` — which succeeded the docker build with exit 0 but
silently produced a 0-row DB because `scraped_data/` was excluded by
`.dockerignore`. If the build container had been kept around (no --rm),
`docker exec ... sqlite3 imdb.db "SELECT COUNT(*) FROM titles"` would
have caught it immediately.

**Verify seed DB row count inside the container** before declaring the
build done:

```bash
docker exec wh-test python3 -c "
import sqlite3
c = sqlite3.connect('/opt/WebSyn/<site>/instance_seed/<site>.db')
print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())
print('rows in <main table>:',
      c.execute('SELECT COUNT(*) FROM <main table>').fetchone()[0])
"
```

If the main table has 0 rows, you're in the trap from clone-website
Pattern 8 — your seed needs HF assets, not build-time RUN.

### Pattern 7: Two-PR coordination is asymmetric — code PR waits for HF PR

The two PRs cross-reference, but only the code PR depends on the HF PR's
merge SHA (`.assets-revision`). The HF PR doesn't depend on code merge.

Sequence:

1. Open both PRs (any order, but HF first is cleaner)
2. Maintainer reviews + merges HF PR → grab the merge commit SHA
3. On the code PR branch: `sed -i "s/^revision:.*/revision: <sha>/" .assets-revision`
4. `git commit --amend` (or new commit) + `git push`
5. Maintainer reviews + merges code PR

Until step 3, the code PR's `.assets-revision` still points to old `main`,
and `fetch_assets.sh` won't find the new site's assets. Reviewers running
the code PR locally will see "site missing instance_seed/<site>.db" until
the HF PR merges.

---

## Hard rule: page content must live in SQLAlchemy tables (added 2026-05-27)

A repeated failure mode: agents drop "data" into helper modules as module-level Python lists/dicts, then routes read from those at request time.

```python
# sites/<site>/_r10_extend.py — ❌ anti-pattern
R10_PRODUCTS = [
    {"id": 1, "name": "MagicBand", "price": 49.95, ...},
    # 60 more entries
]

# sites/<site>/app.py
@app.route('/r10/product/<int:pid>')
def r10_product(pid):
    return render_template('product.html', p=R10_PRODUCTS[pid - 1])
```

**Why it's wrong**:

1. Tasks asking aggregate queries ("how many products under $50?") can't be answered
2. byte-id reset becomes trivially "consistent" — there's no DB to drift
3. Data not versioned alongside HF dataset — the code is the data
4. New agents grep DB, find nothing, re-add it

### Correct pattern

```python
class R10Product(db.Model):
    __tablename__ = 'r10_products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)

def seed_r10_products():
    if R10Product.query.count() > 0:
        return
    for row in REAL_DATA_FROM_TAVILY:
        db.session.add(R10Product(**row))
    db.session.commit()
```

### Detection

```bash
# Suspicious in-memory data structures in non-task non-seed modules
for site in sites/*/; do
    site=$(basename "$site")
    n=$(grep -hcE "^[A-Z][A-Z0-9_]+\s*=\s*\[" sites/$site/*.py 2>/dev/null | \
        awk -F: '!/seed_data|_recompute|_tasks\.py|generate_/')
    [ "${n:-0}" -gt 5 ] && echo "$site: $n suspicious module-level lists"
done
```

False positives: task generators (build-time, fine). True positives: runtime route handlers reading from module-level lists.

### Migration recipe (in-memory → DB)

1. Inventory offending lists/dicts. Snapshot schemas.
2. Define SQLAlchemy models with matching fields (+ id PK).
3. Write `seed_<feature>()` gated by `Model.query.count() > 0`.
4. Replace `THE_LIST[i]` / `THE_LIST.get(slug)` in handlers with ORM query.
5. Delete in-memory list from source file.
6. Verify byte-id reset: `cp instance_seed/<site>.db instance/<site>.db`, md5 both, must match.
7. Bump `_normalize_seed_db_layout` sentinel.

Real-pass examples (2026-05-27): google_search 9 new tables (ImageCard / VideoCard / ScholarPaper / FeaturedSnippet / PaaBundle / KnowledgePanel / ...), wolfram 16 new R11 tables (r11_blog_posts / r11_jobs / r11_store_products / ...).
