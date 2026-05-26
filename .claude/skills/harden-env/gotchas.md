# Gotchas — common pitfalls when authoring or accepting a mirror

Field notes from a batch merge + extension pass over 30+ mirrors. Every item
below came up in **more than one** site. Cross-reference from clone-website,
evolve-env, harden-env, seed-database, review-env.

Order is by frequency × cost: the ones at the top will bite almost every new
mirror, the ones at the bottom only some.

## 1. bcrypt / werkzeug random salt breaks byte-identical reset

**Symptom**: `python3 -c 'from app import app'` two times in a row produces
two different `instance/<site>.db` md5s. Reset fails the post-condition check.

**Root cause**: `bcrypt.generate_password_hash(pw)` and Werkzeug's
`generate_password_hash(pw)` both mix a **random salt** on every call. Any
seed function that calls `user.set_password(...)` will store a different hash
on every rebuild → `users.password_hash` bytes shift → SQLite page bytes
shift → md5 differs.

**Fix A — PINNED hash literal** (simplest, drop-in):

```python
# One-time: python3 -c "import bcrypt; print(bcrypt.hashpw(b'test1234', bcrypt.gensalt(rounds=12)).decode())"
PINNED_PASSWORD_HASH = '$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i'  # 'test1234'

for u in benchmark_users:
    user = User(...)
    user.password_hash = PINNED_PASSWORD_HASH   # NOT u.set_password()
    db.session.add(user)
```

`bcrypt.check_password_hash(hash, raw)` accepts any valid `$2b$...` hash, so
login keeps working unchanged. `set_password()` itself can stay defined on
the model — only the **seed path** must avoid calling it.

**Fix B — fixed-salt pbkdf2** (use when you can't ship a bcrypt literal):

```python
import hashlib
fixed_salt = hashlib.sha1(("salt-" + u["email"]).encode()).hexdigest()[:8]
derived = hashlib.pbkdf2_hmac("sha256", b"<password>", fixed_salt.encode(), 1000, dklen=32).hex()
user.password_hash = f"pbkdf2:sha256:1000${fixed_salt}${derived}"
```

Werkzeug's `check_password_hash` will accept this string. Each user gets a
distinct deterministic hash.

**Pinned hashes already in tree (reuse if your benchmark users have matching pw)**:
- `$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i` — `test1234`
- `$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou` — `TestPass123!`

---

## 2. SQLAlchemy CREATE INDEX order is non-deterministic across processes

**Symptom**: Two `db.create_all()` runs in different Python processes
produce two different `.db` md5s, even when row data is byte-identical.

**Root cause**: SQLAlchemy emits `CREATE INDEX` from `Table.indexes`, which
is a **Python `set`**. Set iteration order depends on the `id()` of the
Index objects — `id()` is allocator-dependent and changes per process.
Affected: `ix_<table>_<col>` schema text inside `sqlite_schema` → page bytes
shift even though row data is identical.

**Does NOT break runtime `/reset`** — that endpoint is `shutil.copytree(seed
→ instance)`, a pure byte copy, so once you ship one canonical
`instance_seed/<site>.db` the reset invariant holds. The problem is only
"can a second machine rebuild byte-identical from source?".

**Fix** (MEGA pattern — apply right after `seed_database()` finishes):

```python
def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte."""
    conn = db.engine.connect()
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.execute(text("VACUUM"))
    conn.commit()
```

Gate it on a "fresh seed" sentinel so it only runs the first time (never on
warm restart with an existing DB).

---

## 3. `datetime.now()` / `datetime.utcnow()` in seed path

**Symptom**: First build at 10:00 and second build at 10:01 produce
different DBs.

**Root cause**: Any `default=datetime.utcnow` on a Column, or any
`created_at=datetime.now()` literal inside a seed loop, captures wall-clock
time.

**Two forms — both must be fixed**:

```python
# Form A — Column default (sneakier, easy to miss):
class Repository(db.Model):
    created_at = db.Column(DateTime, default=datetime.utcnow)   # ❌

# Form B — explicit call in seed loop:
row = Article(title=..., published_at=datetime.now())           # ❌
```

**Fix**: pin one constant at the top of `seed_data.py` and derive every
timestamp from it.

```python
MIRROR_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)
# Per-row offsets via arithmetic, never via datetime.now():
created_at = MIRROR_REFERENCE_DATE - timedelta(days=row_index)
```

Also audit Column defaults: `Column(DateTime, default=datetime.utcnow)` →
`default=lambda: MIRROR_REFERENCE_DATE` or remove the default entirely and
set the value explicitly in seed.

**Important**: Column-default `datetime.utcnow` **does NOT break runtime
reset** (every reset is a `shutil.copytree(seed → instance)` so the bytes
never get re-computed). It only breaks "rebuild from source on machine B
matches the shipped HF db". If you only need reset-byte-identity, you can
ship a Column default of `datetime.utcnow` — but it will bite you the first
time a contributor regenerates the seed db on a different day.

---

## 4. Empty tables that the model defines but seed never fills

**Symptom**: `/feature/N` returns 404 or "no items"; task list mentions a
feature the data can't support.

**Root cause**: PR author defined a SQLAlchemy model + route + template,
but seed only fills the headline tables. Common offenders:

| Site (example) | Empty tables found in PR |
|---|---|
| google_search | vertical, doodle, trending_term, google_app, result_feedback |
| google_map | review, photo, timeline_entry |
| google_flights | saved_search, cart_item, review |
| huggingface | follows, cart_items |
| amazon | wishlist_items, returns, return_items |
| apple | review, wishlist_item |
| arxiv | comments |
| bbc_news | comments, reading_history |
| wolfram_alpha | topic_feedback |

**Fix at review time**: `for t in tables: SELECT COUNT(*) FROM t` over the
seed DB; any 0-count table on a model that has routes pointing at it is a
red flag.

---

## 5. Template URL ≠ app.py route name (silent 404 in walkthrough)

**Symptom**: Page renders OK but every "Browse" / "All movies" link 404s.

**Root cause**: PR author wrote templates with one URL shape (e.g.
`<a href="/browse">`) and routes with a different shape (e.g.
`@app.route("/browse/movies/")`). evolve-env's Playwright walkthroughs miss
this when the canonical URL the agent uses happens to match.

**Audit** (one-liner — grep template URLs vs route definitions):

```bash
# Endpoints used in templates
grep -rohE "url_for\(['\"]([a-z_]+)" sites/<site>/templates/ | sort -u
# Routes / endpoints defined in app
grep -E "^@app.route|^def " sites/<site>/app.py
```

For raw `href=`/`action=` strings (not via `url_for`), also grep
`href=['\"]` and `action=['\"]` and check each path against `app.url_map`.

**Fix pattern — alias routes** (no template churn):

```python
@app.route("/browse")
@app.route("/browse/")
@app.route("/movies")
def browse_alias():
    return redirect(url_for("browse_movies"), code=301)

# Int converter is stricter than string, place above the slug variant:
@app.route("/article/<int:article_id>")
def article_int_alias(article_id):
    art = Article.query.get_or_404(article_id)
    return redirect(url_for("article_detail", slug=art.slug), code=301)
```

---

## 6. Hardcoded site count in `websyn_start.sh`

**Symptom**: Container boot says "16/16 sites ready" even when 20 sites are
listed; the ready-check loop times out at `max_wait=30` instead of breaking
early.

**Root cause**: Original `websyn_start.sh` had `[ $ready -eq 16 ]` literal.

**Fix**: replace every literal site count with `${#SITES[@]}`. Already done
on main — keep it that way for any future bump.

```bash
echo "[WebSyn] Starting ${#SITES[@]} sites on ports ${BASE_PORT}-$((BASE_PORT + ${#SITES[@]} - 1))..."
...
if [ $ready -eq ${#SITES[@]} ]; then break; fi
```

---

## 7. `download_*.py` script ships without its `scraped_data/*.json` input

**Symptom**: `python3 download_posters.py` errors out with
`FileNotFoundError: scraped_data/movies.json`. The download script is dead.

**Root cause**: PR author committed the scrape script but the JSON it reads
was untracked. `.gitignore` covers `sites/*/scraped_data/`, so it gets
silently excluded.

**Fix one of**:
- Move the JSON into the script as a literal (small datasets).
- Hard-code the source URLs the script needs, so it self-bootstraps from a
  public source (RT moved to scraping `rottentomatoes.com/m/<slug>` +
  Wikipedia summary API).
- Commit the JSON under a path that **is** tracked (e.g. inline at
  `sites/<site>/data/`), or add a narrow `.gitignore` exception.

---

## 8. Build-time `RUN cd /opt/WebSyn/<site> && python3 -c "from app import app"`

**Symptom**: Most sites cannot survive a fresh `git clone` + `./scripts/build.sh`
because the build trips the asset-probe and falls into `fetch_assets.sh`
even though the build itself was supposed to *generate* the DB.

**Root cause**: Berkeley/IMDb chose to generate `instance_seed/<site>.db`
at Docker build time via a `RUN` step. That's incompatible with
`check_assets.sh` which expects every site's `instance_seed/` to be
pre-populated *before* `docker build` starts.

**Fix**: keep the contract uniform. Pre-generate the DB on the build host
once (throwaway python:3.12-slim-bookworm container with the site's deps),
copy it into `sites/<site>/instance_seed/<site>.db`, and let `COPY sites/`
ship it. Then the `RUN` step in `Dockerfile` is unnecessary.

```bash
docker run --rm -v "$PWD/sites/<site>:/work" -w /work python:3.12-slim-bookworm \
  bash -c "pip install -q $(...flask deps...) && rm -rf instance && \
           python3 -c 'from app import app, db; from seed_data import seed
with app.app_context(): db.create_all(); seed(db)'"
sudo cp sites/<site>/instance/<site>.db sites/<site>/instance_seed/<site>.db
```

---

## 9. `app.run(port=N)` literal in `if __name__ == '__main__':`

**Cosmetic only** — `site_runner.py` spawns sites via
`python3 -c "from app import app; app.run(port=$PORT)"`, so the `__main__`
block is unreachable in the container. But it confuses people who try to
run the site standalone with `python3 app.py`.

**Fix**:

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 40015)), debug=False)
```

---

## 10. PR base is stale → merge silently deletes newer sites

**Symptom**: You merge an old open PR and `websyn_start.sh` loses sites
that were added to main after the PR was opened.

**Root cause**: PR was forked from main back when there were 15 sites; PR
diffs against that 15-site `websyn_start.sh`. A normal `git merge` keeps
both sides' adds (good), but a PR that *replaces* the 16th slot will
override whatever main added there.

**Fix**: don't `git merge upstream PR`. Pull only the site directory:

```bash
git fetch origin pull/<N>/head:pr<N>-<site>
git checkout pr<N>-<site> -- sites/<site>/
# Then hand-edit Dockerfile / control_server.py / websyn_start.sh to add
# the new site at the next free slot. Commit with a neutral message that
# does NOT mention "#<N>" so it doesn't ping the upstream PR page.
```

Bonus: this also avoids the GitHub auto-cross-reference behavior on the
upstream PR (`Merge PR #N` in a commit message becomes a permanent event
on the PR page that the author sees).

---

## 11. Multiple concurrent subagents in the same worktree clobber each other

**Symptom** (RT polish pass reported it): a subagent's edits to
`sites/<site>/seed_data.py` get reset to git HEAD mid-task by a sibling
agent's git checkout / restore.

**Root cause**: When you fan out N polish subagents in parallel against the
same checkout, any one of them running `git checkout <other-branch> -- ...`
or `git stash` will move the working tree under another agent's feet.

**Fix options**:
- **One worktree per agent** (`git worktree add -b polish-<site>
  .claude/worktrees/<site> main`) so each has an isolated tree.
- **Restrict each subagent to `sites/<site>/` only** and never run git
  commands inside the subagent — main agent does all `git add` / `git
  commit` serially at the end. Document this hard in the prompt.
- **Idempotent re-apply script** (RT's fallback): the subagent writes its
  changes via a `/tmp/<site>_apply_edits.py` patcher it can re-run if it
  detects its files were reverted.

---

## 12. SQLite has hidden non-determinism beyond schema-index order

Even after fix #2, you may still see md5 drift if any of these are present:

- `INSERT OR REPLACE` with overlapping keys (page allocation order changes).
- `M2M` association tables populated via `relationship.append(...)` instead
  of explicit `db.session.execute(insert(assoc).values(...))` in sorted
  (left_id, right_id) order.
- `flush()` without an explicit `order_by` on later queries that drive
  further inserts — the next batch's primary keys depend on the previous
  flush order.
- Trailing `VACUUM` (good) followed by another write (bad — re-fragments).

**Rule of thumb**: do all your writes, then run `normalize_seed_db_layout()`
(fix #2), then **stop touching the DB**. Anything after that re-introduces
the bug.

---

## 13. `pip install -q` inside the throwaway-container seed script

When pre-generating a DB in a throwaway container, always pin every package
exactly to the versions in the image's top-level `Dockerfile`:

```
Flask==3.1.0 Flask-SQLAlchemy==3.1.1 Flask-Login==0.6.3 Flask-Bcrypt==1.0.1 \
Flask-WTF==1.2.2 Werkzeug==3.1.3 Jinja2==3.1.4 SQLAlchemy==2.0.36 \
WTForms==3.2.1 email-validator==2.2.0 Pillow==11.0.0
```

Skipping `Werkzeug==3.1.3` (e.g. letting pip resolve "latest") gives you a
different password-hash *encoding* between build host and runtime container
— the on-disk hash string format shifts, login still works but byte-id
differs.

Add `requests==2.32.3` if the site has `import requests` (drugs.com).

---

## Quick "is this seed deterministic?" smoke check

Run twice inside a clean container. md5 must match.

```bash
docker run --rm -v "$PWD/sites/<site>:/work" -w /work python:3.12-slim-bookworm bash -c "
pip install -q <pinned deps>
rm -rf instance && python3 -c 'from app import app, db; from seed_data import seed
with app.app_context(): db.create_all(); seed(db)' && md5sum instance/<site>.db
rm -rf instance && python3 -c 'from app import app, db; from seed_data import seed
with app.app_context(): db.create_all(); seed(db)' && md5sum instance/<site>.db
"
```

If they don't match, walk the list above 1 → 17 in order.

---

## 14. `seed_data.py` has drifted from the shipped HF seed DB

**Symptom**: `docker run python:3.12-slim-bookworm` + reseed produces a DB
whose article slugs / row text **don't match** what the live site has
been serving for months. Sometimes only ~40 rows survive a rebuild that
should produce ~300.

**Root cause**: HF dataset is patched over the lifetime of the site
(occasional hand-written rows, edits via direct SQLite); the
`seed_data.py` literals in git fall out of sync. Hit during the espn pass
— `seed_data.py` had `celtics-clinch-best-record-2024` while the live DB
had row 1 = `celtics-eye-best-regular-season-in-years`.

**Diagnostic**:

```bash
docker run --rm -v "$PWD/sites/<site>:/work" -w /work python:3.12-slim-bookworm \
  bash -c "pip install -q <deps> && rm -rf instance && python3 -c '<seed entry>'"
md5sum instance/<site>.db sites/<site>/instance_seed/<site>.db
# If md5s differ, you have drift.

# Confirm scope:
diff <(sqlite3 instance/<site>.db 'SELECT slug FROM articles ORDER BY id') \
     <(sqlite3 instance_seed/<site>.db 'SELECT slug FROM articles ORDER BY id')
```

**Choices on drift**:

- **Reconcile** (correct but expensive): export the live HF db as the new
  source of truth, rewrite `seed_data.py` constants to match. Best done as
  a standalone task per site.
- **Skip rebuild** (escape hatch we used in this pass): when extending a
  drifted site, use direct `sqlite3` `INSERT` against `instance_seed/<site>.db`
  rather than `python3 -c "from app import app"`. Preserves the live rows.
  Trade-off: now the *new* rows live only in the DB, not in
  `seed_data.py` — drift gets worse, not better.

**Prevention**: include a CI step that diffs `instance_seed/<site>.db`
md5 against a rebuild from `seed_data.py`. Anything that's not byte-id
should fail review.

---

## 15. Empty model tables — "the silent 404"

**Symptom**: User navigates a UI feature that the model + template + route
all support, and the page renders but is empty / "no items" / 404 on the
inner link.

**Root cause**: The PR author defined the `SQLAlchemy.Model` + the
`@app.route` + the `templates/feature.html`, but never added an entry to
`seed_data.py` that fills the corresponding table. Rows count = 0 in
`instance_seed/<site>.db`.

**This is by far the most common quality defect in submitted mirrors.**
Found in 9 of 15 mirrors during the polish pass:

| Site | Empty tables that needed filling |
|---|---|
| google_search | vertical, doodle, trending_term, google_app, result_feedback (5!) |
| google_map | review, photo, timeline_entry |
| google_flights | saved_search, cart_item, review |
| amazon | wishlist_items, returns, return_items |
| apple | review, wishlist_item |
| huggingface | follows, cart_items |
| arxiv | comments (model + route + template-block all present, just no seed) |
| bbc_news | comments, reading_history |
| wolfram_alpha | topic_feedback |

**Mandatory review step** (add to review-env Step 4):

```bash
# Print all tables with their row counts; flag any 0-row table.
sqlite3 sites/<site>/instance_seed/<site>.db \
  ".tables" | tr ' ' '\n' | grep -v '^$' | while read t; do
    n=$(sqlite3 sites/<site>/instance_seed/<site>.db "SELECT COUNT(*) FROM \"$t\"")
    [[ $n -eq 0 ]] && echo "EMPTY: $t"
  done
```

Then for each `EMPTY:` table, grep templates for references — if a template
links to a feature that hits the empty table, the seed must populate it.

---

## 16. The "google_search GOOGLE_APPS" pattern — hardcoded URLs that aren't routes

**Symptom**: `url_for(...)` audit (gotcha #5) returns zero misses, but real
users still hit 404 because of `href` strings constructed elsewhere.

**Root cause**: A seed file contains a list of dicts like
`GOOGLE_APPS = [{"name":"Meet","url":"/meet"}, ...]` that the template
renders directly via `{{ app.url }}`. None of those URLs goes through
`url_for`, so the audit misses them.

**Repro from this pass**: `google_search` seed had 24 launcher apps; only 9
had corresponding routes; the other 15 were silent 404s in the launcher
grid even though `url_for(...)` checked clean.

**Audit** (extra grep on top of #5):

```bash
# Pull every literal "/path" string from seed_data.py / app.py.
grep -oE '"(/[a-zA-Z0-9/_-]+)"' sites/<site>/seed_data.py sites/<site>/app.py \
  | sort -u | grep -v static
# Cross-check against routes:
python3 -c "
from app import app
routes = {r.rule for r in app.url_map.iter_rules()}
import sys
for line in sys.stdin:
    path = line.strip().strip('\"')
    # crude match: any route whose rule starts with this path
    if not any(r == path or r.rstrip('/') == path for r in routes):
        print('MISSING ROUTE:', path)
"
```

**Fix**: prefer "stub" routes over deleting the link. Most of these are
plausible site features; the agent will keep getting confused if they
silently 404. Pattern:

```python
@app.route("/contact-sales")
@app.route("/enterprise")
@app.route("/education")
def _simple_landing(*, _endpoint="generic"):
    return render_template("simple_landing.html", topic=_endpoint)
```

GitHub polish pass used this for 10 missing pages with a shared
`templates/simple_landing.html`.

---

## 17. Subagent output token cap (32000) and "model not supported" — long-running polish runs

**Symptom**: A polish subagent runs for 20+ minutes, does real work, and
then dies with either `Claude's response exceeded the 32000 output token
maximum` or `API Error: 400 The requested model is not supported`. The
filesystem state shows the work *did* land (db md5 changed, counts grew),
but you get no final report.

**Root cause**:

- **32k cap**: the agent's *final* report was too long. Doesn't matter how
  many tool calls it made — the final assistant message gets clipped.
- **400 model error**: transient model-routing / quota issue. Usually
  resolves by re-dispatching.

**Diagnostic** (before deciding to re-dispatch):

```bash
md5sum sites/<site>/instance_seed/<site>.db   # Did anything actually change?
sqlite3 sites/<site>/instance_seed/<site>.db \
  "SELECT name, (SELECT COUNT(*) FROM '\"||name||\"') FROM sqlite_master WHERE type='table'"
```

If md5 + counts differ from baseline, **the work landed**; just mark task
complete without a report. If they're unchanged, re-dispatch.

**Prevention in the prompt**:

```
# Report — ≤200 words. No code dumps. No JSON dumps. No per-row enumeration.
# Just: counts delta / new db md5 (×2 runs) / 404s fixed (one line) / blocker.
```

Subagents tend to comply when the limit is stated as a hard rule with
"≤" rather than "please keep it short". When the polish target is huge
(say 1000+ rows added across 5 tables), the cap is real — 250 words is a
reasonable ceiling.
