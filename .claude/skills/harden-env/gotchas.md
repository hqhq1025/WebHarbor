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

---

## 18. `pag.items` (or any dict key named like a dict method) silently breaks Jinja

**Symptom**: a Jinja template using `{% for r in pag.items %}` crashes
with `TypeError: 'builtin_function_or_method' object is not iterable`.
The pagination helper returns a plain `dict` whose `items` key holds
the list of rows.

**Root cause**: Jinja's attribute resolution prefers Python's
`dict.items` method over the `"items"` dict key. The for-loop iterates
the bound method, not the list.

**Fix**: return a `SimpleNamespace` (or any object that exposes the data
as a real attribute, not a key):

```python
from types import SimpleNamespace
def paginate(q, page, per_page=25):
    ...
    return SimpleNamespace(items=items, page=page, pages=pages, total=total)
```

**Other landmines in the same family**: `keys`, `values`, `get`, `pop`,
`update`, `copy`, `clear`. Never use these as dict keys for anything you
pass into a Jinja template. Or just use SimpleNamespace / dataclass from
the start.

Found in: discogs mirror, `templates/genre.html`, `marketplace.html`,
`collection.html`, …

---

## 19. Jinja macros do not accept `**kwargs` — pass a dict explicitly

**Symptom**: `{% macro pagination(pag, endpoint, **kwargs) %}` produces

```
jinja2.exceptions.TemplateSyntaxError: expected token 'name', got '**'
```

at template load time. Every page that imports the macro file 500s.

**Root cause**: Jinja macros have strict positional/named param syntax.
No `*args`, no `**kwargs`. The `**` is unparseable.

**Fix**: change the variadic part to an explicit dict:

```jinja
{% macro pagination(pag, endpoint, params=None) %}
  {% set params = params or {} %}
  <a href="{{ url_for(endpoint, page=p, **params) }}">{{ p }}</a>
{% endmacro %}
```

`**params` *inside* `url_for(...)` is fine — it's only the macro
*signature* that rejects `**`. Caller becomes:

```jinja
{{ m.pagination(pag, 'search', params={'q': q, 'sort': sort}) }}
```

Found in: discogs mirror, `templates/_macros.html`.

---

## 20. `Release.query.get(rid)` looks up by PK — not by your public ID column

**Symptom**: a form like `/sell` takes a user-typed `release_id` that
matches the public URL ID (e.g. `/release/793593`). The POST handler
silently 404s with `Pick a valid release.` even though the release page
loads fine. Database inspection shows no row was created.

**Root cause**: SQLAlchemy's `.query.get(rid)` looks up by **primary
key** only. Public IDs (`discogs_id`, `imdb_tt`, `bgg_id`, …) live in
indexed *non-PK* columns. If your PKs are `1..N` and the user types
`793593`, the lookup misses.

**Fix**: any route that accepts a user-typed public ID must check both:

```python
release = (Release.query.filter_by(discogs_id=rid).first()
           or Release.query.get(rid))
```

**Where this trap hides**: routes that read `release_id` / `movie_id` /
`book_id` from `request.form` and assume the form-renderer used the PK.
If the form is rendered by *your* template (`<input type="hidden"
name="release_id" value="{{ r.id }}">`), the PK assumption is safe. If
the form is rendered manually by the user (the Discogs `/sell` page),
or if the value transits through a JSON API, you need the dual lookup.

**Audit** before opening a PR:

```bash
grep -n "request\.form\.get.*release_id.*type=int\|request\.form\.get.*movie_id.*type=int" sites/<site>/app.py
# For each callsite: does the next lookup use .get(...) only? If so, fix it.
```

Found in: discogs mirror, `/sell` route. Caused Task #13 to silently
fail Playwright validation.

---

## 21. `ORDER BY year ASC` puts NULL *first* in SQLite — "oldest" tasks see a year-less row

**Symptom**: a task asks for "the oldest release by Artist X" and the
agent sees a card with empty year metadata at the top. Subsequent
real-dated rows are buried.

**Root cause**: SQLite's default NULL ordering is `NULLS FIRST` for
`ASC` and `NULLS FIRST` for `DESC`. Any "oldest" task returns the rows
where `year IS NULL` first.

**Fix**: chain `.nullslast()` on every year-based sort:

```python
q = q.order_by(Release.year.asc().nullslast())
q = q.order_by(Release.year.desc().nullslast())
```

Same applies to `release_date`, `published_at`, `first_release_date`,
or any nullable timestamp/year column you sort on.

**Audit**:

```bash
grep -nE "\.(year|release_date|published_at|first_release_date|added_at)\.(asc|desc)\(\)" sites/<site>/app.py
# Every match should be followed by .nullslast() unless you genuinely want NULL-first.
```

Found in: discogs mirror, `artist_detail`, `genre_detail`, `label_detail`,
`master_detail`.

---

## 22. CoverArt Archive TLS is blocked from corp / Azure egress — use Wikipedia REST API as the cover fallback

**Symptom**: every request to `coverartarchive.org` fails the TLS
handshake mid-protocol:

```
OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to coverartarchive.org:443
urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING]
```

Reproduces in `curl`, `python urllib`, `httpx`, and Playwright. Almost
certainly a transparent middlebox / deep-packet inspector on the egress
path. Switching User-Agent / IP version doesn't help.

**Workaround that works in this env**: Wikipedia REST API for metadata
+ `upload.wikimedia.org` for image bytes. Both pass TLS clean.

Recipe (see `sites/discogs/scraped_data/scrape_wikipedia.py`):

```python
def try_lookup(title, artist):
    candidates = [
        f"{title} ({artist} album)" if artist else None,
        f"{title} (album)",
        f"{title} ({artist} EP)" if artist else None,
        title,
    ]
    for c in candidates:
        if not c: continue
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(c.replace(' ', '_'))}?redirect=true"
        data = fetch_json(url, retries=1)
        if data and data.get("originalimage", {}).get("source"):
            return data
    return None
```

Hit rate on a 7,000-release catalog: ~5% (323/7042). Don't try to
stretch the same N covers across M releases to hide the gap — fall back
to a generic `no-cover.svg` placeholder and the agent never knows.

Use `originalimage.source` over `thumbnail.source` — the latter is
downsized to 330px.

Found in: discogs mirror, Wikipedia cover-fetch pipeline.

---

## 23. Discogs public API hard-throttles at ~25 req/min — IP-level shadow block, not per-token

**Symptom**: after ~50 successful `/database/search` calls at any
spacing, every subsequent request from the same IP returns `HTTP 429
Too Many Requests` for **5–15 minutes**. The retry loop with
exponential backoff *adds* to the load, deepening the block.

We started a scraper, got 500 results from genre=rock (the first
SEARCHES entry), then stalled at 429 for 30+ minutes.

**Root cause**: Discogs's documented limit is 25/min for unauthenticated
calls, but the *enforcement* is IP-based and shadow-blocks for much
longer than the rate window suggests. On a shared corp / Azure egress
IP, other tenants' traffic counts against you.

**Fixes (combine all three)**:

1. **Genre rotation, not sequential pages**: shuffle the search-combo
   list so the first minute hits *every* genre once, instead of 5 pages
   of one genre. `random.shuffle(combos); for (g,s) in combos: ...`

2. **Polite spacing — 12s+ between requests, not 2.5s**. The
   theoretical 25/min == 2.4s/req only works on a quiet IP. On shared
   egress, budget 5x.

3. **Add a second data source**. Discogs is good for community
   signals (have/want, prices, marketplace) but you can't rely on it
   for catalog breadth. Fall back to MusicBrainz (1 req/sec, no IP
   block, structured tags) for the bulk of the data:

   - `https://musicbrainz.org/ws/2/release-group/?query=tag:"jazz"+AND+primarytype:Album+AND+status:Official&fmt=json&limit=100`
   - Rotate 30+ tags for diversity. ~2400 releases in 6 minutes.
   - Mint synthetic IDs (`90_000_001+`) for the `discogs_id` column so
     MB-sourced rows blend cleanly with API-sourced ones.

**Anti-pattern**: don't put the scraper in a tight retry loop that
treats 429 as transient. The 429 has a long memory; back-to-back
retries make it worse.

Found in: discogs mirror, `scraped_data/scrape_discogs.py`. Final
catalog: 500 from Discogs (Rock only) + 3,520 from MusicBrainz across
30 tags = 4,020 unique. Plus another scrape pass after IP cooldown to
get to 3,522 Discogs + 3,520 MB = 7,042 total.


## 24. The "API endpoint trap" — agents inflate route count with /api/ /graphql /healthz etc that GUI agents can't use

**Symptom**: Final task push includes thousands of ques like
`"On /api/v1/properties/search?city=berlin&limit=3&min_rating=7, parse the JSON 'count' and report it."` —
WebVoyager-style agents drive a real browser, they don't type `/api/` paths nor parse JSON.

**Root cause**: When an agent is told "add R10 surface", its default instinct is to expose REST mirrors / GraphQL stubs / sitemap.xml / .well-known / OAI-PMH / healthz — all the "machine-facing" plumbing a real production site has. Easy to generate, fills the route count, but **useless for benchmarks**.

**Numbers from a real cleanup pass** (15 vanilla sites, 2026-05-27):
- google_flights: 1447 API-style tasks (21% of the file)
- apple: 1037 (18%)
- bbc_news: 1007 (14%)
- huggingface: 860 (14%)
- 15-site total: **14,468 deleted** (14.3% of 101k)

**Fix template** (in cleanup script):

```python
API_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+/"
    r"|/api[/\b]"
    r"|/graphql"
    r"|/healthz"
    r"|/sitemap"
    r"|/robots\.txt"
    r"|/\.well-known"
    r"|/webhook"
    r"|/jsonld"
    r"|/openapi"
    r"|parse the JSON|parse the XML"
    r"|\?format=json|\?format=xml"
    r"|fetch the endpoint"
    r"|OAI-PMH"
    r"|as JSON|as XML"
    r"|in JSON format|in XML format"
    r"|curl\s",
    re.IGNORECASE,
)
```

Run as a post-build pass on every site. Backup `tasks.jsonl.preapi`.

**Prevention rule for new agents**: in their prompt, lead with **"绝对不准新增 /api/, /graphql, /healthz, /sitemap, /webhook, /.well-known, /jsonld, /openapi 路由"** AND **"task 必须是 GUI 自然语言不准 'parse the JSON' / 'GET /api'"**. Agents will still add a few — that's why you also run the regex cleanup.

## 25. The "in-memory data dict" trap — bypasses byte-id reset, can't be queried via GUI tasks

**Symptom**: A helper module `_r4_r10_routes.py` declares:

```python
R4_CARDS = [
    {"id": 1, "slug": "aurora_over_the_norwegian_fjords", ...},
    {"id": 2, "slug": "lavender_field_at_sunset_in_provence", ...},
    # 24 hardcoded entries total
]
```

Routes do `R4_CARDS[card_id - 1]` instead of `db.session.query(Card).get(card_id)`. Site appears to work — until you:

- Run byte-id reset check — passes (data isn't in DB so no drift)
- ...but means the data isn't covered by reset either; it's static code
- A task asks "how many image cards have CC-BY license" — the answer is hardcoded in Python, not queryable
- An agent that grep'd the DB for the answer finds nothing
- Worst: 24 cards is way too few to feel real

**Detection**:

```bash
# Find suspicious in-memory data tables (>=10 items) in helper modules
grep -rE "^[A-Z][A-Z0-9_]+\s*=\s*\[" sites/<site>/*.py | \
  grep -v "app.py" | grep -v "_recompute_taxonomy" | \
  grep -v "_tasks.py" | grep -v "generate_.*_tasks.py"
# False positives: task generators (build-time), seed builders.
# Real hits: route-handler-adjacent files like _r10_extend.py
```

Per `seed-database` SKILL: page content **must** live in SQLAlchemy tables, seeded once, queried at runtime.

**Fix template**:

1. Define ORM models for the content (`ImageCard`, `VideoCard`, etc.)
2. Move the hardcoded list into a `seed_<feature>()` function gated by `Model.query.count() > 0`
3. Replace `R4_CARDS[i]` → `ImageCard.query.get(i)` in handlers
4. Drop the hardcoded list from the helper module

**Found in this pass**: google_search R4/R5/R6/R10 (24 image / 24 video / 16 paper / 12 snippet / 10 PAA / 8 KP all in-memory), wolfram R11 (16 page families × ~12 items each in helper module). Both rewritten to use 9-16 new SQLAlchemy tables.

## 26. The "shared marketing template" trap — N routes, 1 template, fake visual surface count

**Symptom**: 20+ routes all call `render_template('info_page.html', page=page)` with different `page` data passed in. Route count looks high (200+), template count is moderate (60+), but **the same hero/grid/CTA layout shows for every "page"**.

**Real example — github**:
- 12 routes share `info_page.html`: /pricing, /features/copilot, /features/actions, /features/codespaces, /resources/security, ...
- 8 routes share `simple_landing.html`: /contact-sales, /enterprise, /education, /features/code-scanning, /features/secret-scanning, ...

On the real upstream site each of those is a distinct landing page with its own hero, screenshot carousel, customer logo wall, pricing table, FAQ accordion. Sharing one template visually flattens 20 pages into 1.

**Same pattern — wolfram_alpha**:
- Initial pass added 36 routes for 16 page families (examples / widgets / blog / community / jobs / store / mathworld / etc.) all rendering `r10/vertical.html` — a single generic 2-column layout. blog post and job posting were visually identical.

**Detection**:

```bash
# Routes per template per site
python3 -c "
import re, collections
src = open('sites/<site>/app.py').read()
hits = collections.Counter(re.findall(r\"render_template\(['\\\"]([^'\\\"]+)\", src))
for tpl, n in hits.most_common(8):
    print(f'{n}\t{tpl}')
"
# Anything ≥6 routes per template warrants a closer look.
```

**Fix**: per page family, write a **distinct template** with the real upstream's visual hooks. Examples:

| Family | Real-site visual cue | Template |
|---|---|---|
| pricing | three-column comparison table + ✓ matrix + FAQ accordion | `pricing.html` |
| feature/copilot | AI animation hero + IDE-integration logos | `feature_copilot.html` |
| feature/actions | pipeline diagram + YAML code block + matrix | `feature_actions.html` |
| enterprise | customer logo wall + testimonial pull-quotes + sales CTA | `enterprise.html` |
| pub/notebook | In[]/Out[] cell strip + execute button | `notebook_pub.html` |
| forum/topic | OP card + threaded replies + upvote arrows | `community_topic.html` |
| store/product | product image grid + add-to-cart + price | `store_product.html` |
| job/detail | sidebar filter + apply-now CTA | `job_detail.html` |

**Smoke after split**: pick 5 visually-different page families, grep each rendered HTML for a CSS class that's only in that template (`.r11-bp-hero`, `.r11-ct-op`, `.r11-sp-buttons`, `.r11-jd-tag`, `.r11-nb-cells`). Must be present on its own page and **absent on the other four**. If two share a class, the templates weren't actually split.

## 27. The "entry-link 断链" trap — routes exist but nothing links to them

**Symptom**: A subagent adds `/search/images/tools`, `/search/images/preview/<id>`, `/scholar/results` — all return 200 if you GET them directly. But:

- `/images` is 404 (no hub)
- The index page doesn't have an `<a href="/search/images/tools">` anywhere
- The natural search results page doesn't show an "Images" tab linking to it
- A GUI agent that lands on `/` cannot navigate to the new pages

The tasks that reference these routes are unsolvable.

**Detection**:

```python
from bs4 import BeautifulSoup
page = client.get('/').data.decode()
links = {a['href'] for a in BeautifulSoup(page, 'html.parser').find_all('a', href=True)}
for new_hub in ['/images', '/videos', '/scholar', '/myaccount', '/orders', '/help']:
    if new_hub not in str(links) and not any(l.startswith(new_hub) for l in links):
        print(f"BROKEN ENTRY: {new_hub} unreachable from /")
```

Or check the rendered nav/tab bar:

```bash
grep -oE 'href="[^"]+"' sites/<site>/templates/base.html sites/<site>/templates/index.html | sort -u
# Then diff against `grep '@app.route' sites/<site>/app.py | grep -oP "'/[^']+'"`
```

**Fix**: when you add a hub URL, also patch `base.html` (global nav) or the appropriate parent page (e.g. `search.html` for `/images`, `account.html` for `/myaccount`). Add an `<a href="/new-hub">Label</a>` somewhere visible. Ideally inside the nav/tab bar component so it appears on every page.

**Smoke**: from `/`, you should be able to reach every new top-level GUI page via ≤2 clicks (page links). Walk the link graph in BFS — if a route isn't in the closure, it's orphaned.

**Found in this pass**: google_search R4/R5/R6/R10 — all 30+ routes were orphaned until a root-cause fix wired `<a href>` into `base.html` tab bar + `index.html` + `search.html`.

## 28. The "task literal duplicate" trap — generator multiplies same句式 1000x

**Symptom**: 994 tasks all have ques `"On the Cambridge Dictionary entry for X..."` differing only in the word X. 100 tasks have **byte-identical ques** because the generator wrote the same line 100 times without varying anything.

**Detection**:

```python
from collections import Counter
import json
counts = Counter()
for ln in open(f"sites/<site>/tasks.jsonl"):
    counts[json.loads(ln)["ques"]] += 1
for q, n in counts.most_common(10):
    if n > 5:
        print(f"{n}x {q[:80]}")
```

**Fix in two passes**:

1. **Literal dedup**: keep first occurrence of each ques (case-insensitive). Removed 10,151 rows across 15 sites.
2. **5-token prefix cap @ 5**: tokenize the first 5 words of each ques, keep at most 5 rows per prefix. Removed another 30,770 rows.

Combined: 101k → 44k (−57%) without touching real GUI tasks.

**Prevention in generator**: when programmatically expanding a task template, change at least 2 dimensions per row (entity + operation, not just entity). And cap output per template at the start: `min(generate(N), 5)`.

## 29. Test client run skips the seed-copy step — fake-503 in audits

**Symptom**: `python3 -c "from app import app; c=app.test_client(); print(c.get('/').status_code)"` returns 500 with
"`sqlite3.OperationalError: no such table: sports`".
But the actual deployed app works fine.

**Root cause**: At first request, the Flask app reaches for `instance/<site>.db`. In docker, the entrypoint **copies** `instance_seed/<site>.db → instance/<site>.db` before serving. The test_client doesn't trigger that copy — it gets the 0-byte empty `instance/<site>.db` that the app creates on `db.create_all()`. Models exist; tables don't.

**Fix template** in any local smoke harness:

```python
import shutil, pathlib
sd = pathlib.Path("sites/<site>")
inst = sd / "instance"; inst.mkdir(exist_ok=True)
for sb in (sd / "instance_seed").glob("*.db"):
    target = inst / sb.name
    if not target.exists() or target.stat().st_size == 0:
        shutil.copy2(sb, target)
# now import app and test
```

**Prevention**: documentation in CONTRIBUTING.md and `evolve-env/SKILL.md` should mention this explicitly.

## 30. Image asset utilization — 800 files on disk, 9 `<img>` tags in templates

**Symptom**: `find sites/<site>/static/images -type f | wc -l` returns 800+. `grep -rh "<img" sites/<site>/templates | wc -l` returns 9. The mirror has a treasure trove of real photos but the templates barely reference them.

**Real numbers** (post-deepen, 2026-05-27):
- google_map: 818 files / 9 refs (1.1% utilization) — for a maps site this is fatal
- arxiv: 108 files / 3 refs (2.8%) — paper figures + author headshots invisible
- google_flights: 420 / 19 (4.5%)
- espn: 426 / 20 (4.7%)
- huggingface: 714 / 23 (3.2%)

**Why this happens**: agents focus on data fields (title, price, count) and forget templates need visual content. Hero photo, thumbnail strip, gallery, lightbox — all skipped.

**Fix template**:

1. Add an `image_path` column to the dominant model (`Place`, `Paper`, `Recipe`, `Property`) if not already there.
2. Seed real upstream image URLs from your existing `static/images/<entity>/*.jpg` by md5-deriving a deterministic mapping `entity.slug → image_path`.
3. In detail templates, add `<img src="{{ item.image_path }}" alt="{{ item.name }}">` hero + `{% for p in item.photos %}<img>...{% endfor %}` gallery.
4. In list/grid pages, show thumbnail per card.
5. Target ≥40% utilization (template `<img>` refs / disk files).

## 31. Concurrent subagent file race (extended) — APPEND-ONLY discipline

**Symptom**: subagent A and subagent B both edit `app.py`. Their Edit tool calls race; one fails with "file modified since read". Or both commit, one rebase-conflicts on push.

This was hit repeatedly in this pass (R2/R3 backfill + mid-rounds touching same app.py).

**Fixes that worked**:

1. **APPEND-ONLY**: tell each subagent to write its block at end of file or between sentinel comments (`# === R11 GUI deepen BEGIN/END ===`). Never edit existing code blocks. Diff is then a pure addition, conflicts are syntactic at most.
2. **Atomic file replace**: in seed/build scripts, write to `<file>.tmp` then `os.replace(<file>.tmp, <file>)`. Avoids partial writes.
3. **`git pull --rebase` immediately before commit**, plus catch the rebase conflict and abort cleanly with a clear error to the orchestrator.
4. **Per-site agents only**: never two agents on the same site simultaneously. Cross-site parallelism is safe; same-site parallelism is not.
5. **Blueprint-style registration**: agent A writes `gui_deepen.py` exporting `register(app)`, agent B writes `r11_extend.py` exporting `register_r11(app)`. `app.py` does `gui_deepen.register(app); r11_extend.register_r11(app)`. Each agent's code is in its own file.

## 32. `seed_data.py` top-level `from app import` + late-import in app_context = circular import

**Symptom**: `python3 -c "from app import app"` (fresh process, REPL, smoke test) fails with:

```
ImportError: cannot import name 'seed_extended_catalog' from partially initialized module 'seed_data' (most likely due to a circular import)
```

Docker startup works fine because the entrypoint path doesn't trip the cycle, but any local test harness / `pytest` / `python3 -c ...` will break.

**Root cause**:

```python
# seed_data.py top of file
from app import app, db, Category, Recipe, User, Review   # ← top-level

# app.py somewhere
with app.app_context():
    from seed_data import seed_extended_catalog   # ← late-import inside context
    seed_extended_catalog()
```

When anything imports `seed_data` first (test harness, sibling module), Python starts loading it, sees `from app import ...`, starts loading `app`, which hasn't yet defined `db/Category/...` (those are below the `db = SQLAlchemy(app)` line). seed_data's import hits a partially-initialized module and raises.

**Fix** (real one used in allrecipes, commit `e34bf1e`):

Move the `from app import ...` **inside** the seed function as a late import:

```python
# seed_data.py — fixed
def _bind_app_symbols():
    """Late-import app symbols and write them into this module's globals."""
    global app, db, Category, Recipe, User, Review
    from app import app as _app, db as _db, Category as _Cat, Recipe as _R, User as _U, Review as _Rv
    app, db, Category, Recipe, User, Review = _app, _db, _Cat, _R, _U, _Rv

def seed_extended_catalog():
    _bind_app_symbols()   # ← bind at call time, not import time
    # ... use Category/Recipe/User/Review here
```

All helpers within `seed_data.py` reference the names via globals (already in scope after `_bind_app_symbols()` writes them). No `try/except ImportError` — that would mask the cycle; just relocate the import.

**Verification**:
- `python3 -c "import seed_data"` clean
- `python3 -c "from app import app; c=app.test_client(); print(c.get('/').status_code)"` → 200
- byte-id reset still ✅

**Prevention rule**: never `from app import ...` at module level in `seed_data.py`, `evolve_*.py`, `r*_extend.py`, `gui_deepen.py`, or any file that `app.py` itself imports. Always late-import.

## 33. Hub URL inventory — core user-facing pages silently missing

**Symptom**: site appears polished (76+ templates / 5000+ tasks) but smoke-testing a small list of "what every real user expects" returns 404 for several:

- amazon: `/orders` 404, `/help` 404
- booking: `/myaccount` 404
- coursera: `/browse` 404
- google_map: `/your-places/saved` 404

These are core hubs on the real upstream. Users rely on them. Their absence blocks substantial workflow chains ("check my order history", "edit account preferences", "browse all data-science courses").

**Per-site-type expected hub URLs**:

| Site type | Hub URLs |
|---|---|
| E-commerce | `/`, `/cart`, `/orders`, `/orders/<id>`, `/wishlist`, `/account`, `/account/addresses`, `/account/payments`, `/help`, `/help/category/<slug>`, `/help/contact` |
| Booking / travel | `/`, `/searchresults`, `/myaccount`, `/myaccount/payments`, `/myaccount/genius`, `/myaccount/inbox`, `/help` |
| Course / learning | `/`, `/browse`, `/browse/<subject>`, `/specializations`, `/professional-certificates`, `/degrees`, `/help-center`, `/account`, `/my-courses` |
| Search engine | `/`, `/images`, `/videos`, `/scholar`, `/news`, `/maps`, `/settings`, `/settings/search`, `/settings/safesearch` |
| Map / places | `/`, `/maps`, `/your-places`, `/your-places/saved`, `/your-places/visited`, `/your-places/lists`, `/your-places/maps`, `/trips`, `/contribute` |
| Marketplace / dev | `/`, `/explore`, `/pricing`, `/features/<slug>`, `/enterprise`, `/education`, `/marketplace`, `/account`, `/settings`, `/notifications` |
| News / sport | `/`, `/section/<slug>`, `/topics/<slug>`, `/account`, `/preferences`, `/saved`, `/podcasts`, `/newsletters` |
| Dictionary | `/`, `/dictionary/english/<word>`, `/grammar`, `/thesaurus`, `/translate`, `/about`, `/plus`, `/account`, `/vocab/list/<id>` |

Smoke test (after seed-copy from §29):

```python
import shutil, pathlib, importlib.util, sys
sd = pathlib.Path("sites/<site>")
inst = sd / "instance"; inst.mkdir(exist_ok=True)
for sb in (sd / "instance_seed").glob("*.db"):
    target = inst / sb.name
    if not target.exists() or target.stat().st_size == 0:
        shutil.copy2(sb, target)
for k in list(sys.modules):
    if k.startswith(("app", "seed_", "_r", "gui_", "airport_extras")):
        sys.modules.pop(k, None)
sys.path.insert(0, str(sd))
spec = importlib.util.spec_from_file_location("app", sd / "app.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
c = m.app.test_client()
for url in EXPECTED_HUBS:
    r = c.get(url, follow_redirects=False)
    if r.status_code in (404, 500):
        print(f"BAD: {url} = {r.status_code}")
```

**Fix per missing hub**:

1. Identify the matching real upstream URL (e.g. `amazon.com/gp/your-account/order-history` → mirror `/orders`)
2. Build the template family (`orders_list.html`, `order_detail.html`, `order_track.html`)
3. Wire the route handler with ORM query on Order/User
4. Add a link in the global nav / account dropdown
5. Add ≥5 GUI tasks targeting the new hub

This pass added 5 hubs (amazon /orders + /help, booking /myaccount, coursera /browse, google_map /your-places/saved) — each got 6-14 new routes and 30-60 new tasks.

## 34. Image utilization recipe — going from 1% to 50%+

**Symptom**: `static/images/` has 800+ real photos, templates have <20 `<img>` references. Visual mirror feels barren.

**Real numbers from this pass** (after fix):
- google_map: 1.1% → **54.2%** utilization (443/818 files referenced)
- arxiv: 2.8% → **58-60%** (140/243 reachable)

**Schema patterns**:

```python
# Single-image entity (Recipe, Product, Article)
class Recipe(db.Model):
    image_path = db.Column(db.String(200))  # static/images/recipes/<slug>.jpg

# Multi-image entity (Paper figures, Place photos, Property rooms)
class PaperFigure(db.Model):
    __tablename__ = 'paper_figures'
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'))
    position = db.Column(db.Integer)        # 1, 2, 3, ...
    kind = db.Column(db.String(30))         # 'figure' / 'table' / 'equation'
    filename = db.Column(db.String(120))
    caption = db.Column(db.String(500))
    w = db.Column(db.Integer)
    h = db.Column(db.Integer)
    paper = db.relationship('Paper', backref='figures')

# Avatar/headshot entity
class AuthorImage(db.Model):
    author_name = db.Column(db.String(120), primary_key=True)
    kind = db.Column(db.String(30))         # 'headshot' / 'banner' / 'institution_logo'
    filename = db.Column(db.String(120))

# Brand/logo entity (for marketplace sellers, conferences)
class ConferenceImage(db.Model):
    conf = db.Column(db.String(30))
    year = db.Column(db.Integer)
    filename = db.Column(db.String(120))
    accent_color = db.Column(db.String(7))  # for hero gradient
```

**Mapping recipe**:

```python
import hashlib
def deterministic_filename(slug, kind, n_files=24):
    h = hashlib.md5(f"{slug}_{kind}".encode()).hexdigest()
    idx = int(h[:8], 16) % n_files + 1
    return f"{kind}_{idx:03d}.jpg"
# stable across seeds, distributes files evenly
```

**Template patterns**:

```html
<!-- Hero photo on detail page -->
<img src="/static/images/places/{{ place.image_path }}"
     alt="{{ place.name }}" class="hero-photo">

<!-- 5-mosaic gallery -->
<div class="photo-mosaic">
  {% for photo in place.photos[:5] %}
    <img src="/static/images/places/{{ photo.filename }}" alt="{{ photo.caption }}">
  {% endfor %}
</div>

<!-- Thumbnail strip in list pages -->
{% for paper in papers %}
  <a href="/abs/{{ paper.arxiv_id }}">
    <img src="/static/images/covers/{{ paper.cover_filename }}"
         class="result-thumb">
    {{ paper.title }}
  </a>
{% endfor %}
```

**Tasks targeting image fields** (mandatory part of the deepen):

```
"On the paper /abs/1706.03762, open the third figure and report its caption."
"What is the institution banner shown on author Bo Pang's profile?"
"On NeurIPS 2024 conference page, what accent color is used in the hero gradient?"
"On the place /place/eiffel-tower, how many photos are in the visitor gallery?"
"On /recipe/lasagna-bolognese, what does the hero photo show?"
```

These tasks force agents to actually look at images, not just data fields. They also unlock the visual modality of the benchmark.

## 35. POST interaction patterns — going from 11 to 40+ form endpoints

**Symptom**: site has 80+ GET routes but only 10-15 POST. Real users do far more than browse — they save, vote, comment, follow, edit, submit.

**Real numbers from this pass**:
- espn: 11 POST → 41 (+30)
- cambridge: 14 POST → 36 (+22)
- booking: added 11 POST in /myaccount
- google_map: added 15 POST (Q&A / edit / report / check-in / save / rating)

**Feature families that reliably add many POSTs**:

| Family | Example POST routes |
|---|---|
| Save / bookmark | `/place/<id>/save`, `/article/<id>/save`, `/job/<id>/bookmark` |
| Vote / rating | `/poll/<id>/vote`, `/example/<id>/upvote`, `/comment/<id>/upvote` |
| Comment / reply | `/article/<id>/comment`, `/comment/<id>/reply`, `/question/<id>/answer` |
| Follow / subscribe | `/team/<slug>/follow`, `/author/<id>/follow`, `/alert/subscribe` |
| Edit-suggest / report | `/word/<id>/suggest-edit`, `/place/<id>/report`, `/photo/<id>/report` |
| User content create | `/list/create`, `/deck/create`, `/quiz/start`, `/post/new` |
| User content edit | `/list/<id>/rename`, `/list/<id>/add-item`, `/profile/update` |
| Forms with stages | `/quiz/<id>/submit-answer`, `/quiz/<id>/skip`, `/quiz/<id>/restart` |
| Workflow actions | `/order/<id>/cancel`, `/order/<id>/return`, `/booking/<id>/modify` |
| Account / preferences | `/account/preferences/update`, `/account/password/change`, `/account/2fa/enable` |
| Cart / wishlist | `/cart/add/<id>`, `/cart/remove/<id>`, `/wishlist/<id>/move-to-cart` |
| Game-like (sports) | `/lineup/save`, `/trade/propose`, `/bracket/<id>/pick/<game>`, `/draft/pick` |

**Pattern per POST**:

1. GET page (`/feature/form`) renders the form
2. POST handler validates + writes DB + redirects with flash
3. New DB table or column for the write target
4. ≥3 tasks per POST referencing the form (`"On the X form, set Y to Z and submit; verify the confirmation message"`)

**Anti-pattern**: a POST that returns a status JSON without redirect. Real users don't see JSON — they see a confirmation page. Always redirect (302) to a result page on success.

## 36. MarketingPage + MarketingPageSection schema (for sites with many distinct landing pages)

For sites with 15+ visually-distinct marketing/landing pages (github features/pricing/enterprise/education, Apple buy-config/services, Coursera business/government), use the section-based schema:

```python
class MarketingPage(db.Model):
    __tablename__ = 'marketing_pages'
    slug = db.Column(db.String(60), primary_key=True)
    title = db.Column(db.String(200))
    eyebrow = db.Column(db.String(80))
    subtitle = db.Column(db.String(500))
    hero_image_path = db.Column(db.String(200))
    meta_description = db.Column(db.String(300))

class MarketingPageSection(db.Model):
    __tablename__ = 'marketing_page_sections'
    id = db.Column(db.Integer, primary_key=True)
    page_slug = db.Column(db.String(60), db.ForeignKey('marketing_pages.slug'))
    position = db.Column(db.Integer)
    kind = db.Column(db.String(40))      # hero / grid / table / faq / cta / logo_wall / diagram / code / testimonial / timeline
    json_data = db.Column(db.Text)        # JSON blob; structure depends on kind
    page = db.relationship('MarketingPage', backref='sections')
```

**Template strategy**: each distinct page (not each section kind) gets its own template. Each template can pick which section kinds it uses:

- `pricing.html` uses `hero + table + faq + cta`
- `feature_copilot.html` uses `hero + diagram + logo_wall + testimonial + cta`
- `enterprise.html` uses `hero + stats + logo_wall + testimonial + cta`

Each template has inline CSS expressing its visual identity — pricing has 3-column comparison, Copilot has AI animation hero, Enterprise has client logo wall. **No shared "vertical.html"**.

Real-pass: github's 21 pages all migrated to this schema (commit `7da5723`). Each template has a distinct content md5 verified by smoke test.

## 37. Subagent stalls mid-deepen — the "Now I'll write the seed data..." cliff

**Symptom**: Background subagent reaches "stalled: no progress for 600s" with last visible output being mid-sentence:
- `"Now I'll write the seed data sections..."`
- `"Now I'll write the deepen extension. First, the SQL extension script:"`
- `"Now let me add the seed data sections and the new seed functions. First let me find where to put them."`

Each was a partial-progress state where app.py had 500-900 new lines added (routes + POST endpoints), but 0 new templates and 0 new tasks. Not committed.

**Why this happens**: large deepen prompts (≥3 distinct work blocks: routes + templates + seed + tasks) seem to exhaust the agent's working memory mid-task. The stream watchdog kills the process while the agent is "thinking" about the next block. Real example from this pass: phet/osu/nba all stalled at the same checkpoint despite being given different sites.

**Detection (post-stall)**:

```bash
# What did the agent actually do before dying?
cd /home/v-haoqiwang/repos/WebHarbor
git status sites/<site>/                  # uncommitted changes left behind?
git diff --stat sites/<site>/             # how big?
grep -c '^@app.route' sites/<site>/app.py # routes count vs baseline
find sites/<site>/templates -name '*.html' | wc -l  # template count vs baseline
wc -l sites/<site>/tasks.jsonl            # tasks count vs baseline
```

If app.py grew substantially but templates/tasks didn't move and nothing is committed → the agent died at the cliff.

**Finisher prompt template**:

```
Site: sites/<site>/
**情况**: Previous agent stalled at "Now I'll write seed/templates/tasks...".
**当前**: app.py modified (+routes/+POST), 0 new templates, 0 new tasks, uncommitted.

**任务**:
1. git status to confirm modifications still present
2. grep app.py for render_template('xxx') calls referencing missing templates
3. Build each missing template with distinct inline-CSS visual style
4. Generate 1500+ GUI tasks (id: Site--gui_<page>_<NNN>)
5. Test client smoke 20 URLs → 200
6. byte-id reset: cp instance_seed/<site>.db instance/<site>.db → md5 equal
7. git pull --rebase origin main; commit; push fork

**强制**: 5-token cap @5 / 0 API / PINNED bcrypt + md5 seed + normalize_seed_db_layout
**报告**: ≤200 words.
```

**Prevention for new deepen prompts**:

1. **Cap each agent's scope at 2 work blocks** (routes+templates OR seed+tasks), not 4 at once.
2. **Encourage append-only blueprint pattern**: agent writes `_deepen_extend.py` exporting `register(app)`, then `app.py` does `_deepen_extend.register(app)` — this localizes the work to one file and reduces the agent's surface area.
3. **Tell the agent to commit early** ("commit + push after Step 3 even if not done; we'll resume").

Found in: phet_simulations (a52058...), osu (a802ca...), nba (a2aad3...). All recovered via finisher prompt.

## 38. `image_path` column referencing non-existent files

**Symptom**: site has `static/images/<entity>/<file>.jpg` directory with N real files, but the DB `Model.image_path` column is populated with synthetic filenames like `C0000<id>-photo.jpg` that don't match any real on-disk file. Templates render `<img src="/static/images/cars/{{ vehicle.image_path }}">` → 404 for every image. Visual surface is broken.

**Real example — carmax**: 741 Vehicle rows with `image_path` like `C0001234-photo.jpg`, but only 123 real stock-image prefixes on disk. Image utilization measured 0% despite 748 photo files present.

**Detection**:

```python
import pathlib, sqlite3
con = sqlite3.connect("sites/<site>/instance_seed/<site>.db")
img_paths = [r[0] for r in con.execute("SELECT image_path FROM Vehicle WHERE image_path IS NOT NULL")]
existing = {p.name for p in pathlib.Path("sites/<site>/static/images/vehicles").rglob("*.jpg")}
broken = [p for p in img_paths if p not in existing]
print(f"broken: {len(broken)} / total: {len(img_paths)}")
```

If >50% broken → run a deterministic remap.

**Fix recipe — deterministic md5 remap**:

```python
import hashlib
real_prefixes = sorted({p.stem.split("-")[0] for p in
                        pathlib.Path("static/images/vehicles").rglob("*.jpg")})
# 123 unique stock prefixes
for vehicle in Vehicle.query.all():
    h = int(hashlib.md5(str(vehicle.id).encode()).hexdigest()[:8], 16)
    chosen_prefix = real_prefixes[h % len(real_prefixes)]
    # Pick a hero photo of that prefix
    candidates = sorted(pathlib.Path("static/images/vehicles").rglob(f"{chosen_prefix}-*.jpg"))
    vehicle.image_path = candidates[h % len(candidates)].name
db.session.commit()
```

Run as a one-shot in `seed_deepen()` gated by a row-count check (so it doesn't bump byte-id on re-seed).

**Verification**:

```python
broken_after = [...]  # repeat detection
assert len(broken_after) == 0
# Image utilization = 100% on the deepened surface
```

Pattern is general: any time templates use `{{ item.image_path }}` for a path that should point at a real file, validate the path exists. If not, remap deterministically onto the real asset set.

## 39. `_pinned_pbkdf2(email, pw)` — alternative to PINNED bcrypt

**Context**: §1 documented PINNED bcrypt hashes. Some sites prefer pbkdf2 (Flask-Login default, no native dep). The same byte-id problem applies — **pbkdf2 with random salt** breaks reset.

**Fix B (pbkdf2 with deterministic salt)**:

```python
import hashlib, hmac, base64
def _pinned_pbkdf2(email: str, password: str) -> str:
    """Deterministic pbkdf2 hash: salt = md5(email)[:16], iterations pinned."""
    salt = hashlib.md5(email.encode()).hexdigest()[:16].encode()
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2:sha256:600000${salt.decode()}${base64.b64encode(hash_bytes).decode()}"
```

Use during seed:

```python
for u in USERS:
    user = User(email=u["email"], password_hash=_pinned_pbkdf2(u["email"], "TestPass123!"))
    db.session.add(user)
```

Verification: `User.query.get(1).password_hash` returns the same string across reseeds. Login still works because `check_password_hash` is salt-agnostic at verify time.

Found used in: imdb (commit `a1e31f2`), ted (commit `f346c8a`), recreation_gov (commit `c5bc12d`).

## 40. SVG generation as image fallback for high utilization

**Context**: §34 said target 40-50% image utilization. What if `static/images/<site>/` doesn't have enough real photos for every entity?

**Solution**: generate deterministic SVGs for missing assets. Two patterns:

### Pattern A: pre-generate at seed time

```python
# sites/<site>/generate_svgs.py
import hashlib, pathlib
OUT = pathlib.Path("static/images/avatars")
OUT.mkdir(parents=True, exist_ok=True)
for slug in slugs:
    h = hashlib.md5(slug.encode()).hexdigest()
    color = "#" + h[:6]
    initial = slug[0].upper()
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <rect width="200" height="200" fill="{color}"/>
  <text x="100" y="120" font-size="80" text-anchor="middle" fill="white">{initial}</text>
</svg>'''
    (OUT / f"{slug}.svg").write_text(svg)
```

Run once. Template: `<img src="/static/images/avatars/{{ user.slug }}.svg">`.

### Pattern B: route-generated at request time

```python
@app.route("/static-gen/<kind>/<slug>.svg")
def static_gen(kind, slug):
    h = hashlib.md5(slug.encode()).hexdigest()
    color = "#" + h[:6]
    label = slug[:2].upper()
    svg = f'<svg ...>...</svg>'  # parameterized by kind
    return svg, 200, {"Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=86400"}
```

Template: `<img src="/static-gen/avatar/{{ author.slug }}.svg">`. No disk footprint, deterministic.

**Real examples**:
- berkeley: 76 SVGs generated via `generate_svgs.py` (campus/headshot/banner/fund/library/sport) → 73.7% utilization
- phys_org: `/static-gen/{avatar,podcast,banner,video}/<slug>.svg` route → 40.5% utilization

**Visual identity tip**: vary `kind` to control svg style — avatar gets initials, podcast gets a circle+microphone, banner gets a gradient strip. Each SVG type has a distinct visual aesthetic so they don't look identical.

### When to choose A vs B

- **Pattern A (pre-generate)**: when you want the asset to ship with the HF dataset (visible in `ls static/images/`). Easier to inspect. Bigger disk footprint.
- **Pattern B (route-generated)**: when you have 10k+ entities and don't want 10k SVG files. Lower disk footprint. Slightly higher CPU per request.

Both achieve >40% image utilization in templates without needing real photos.

## 41. R8 / "advanced UX" 键盘 hotkey + Cmd+K palette 灾难 — 死盖在内容上挡点击

**症状**：用户打开任何 page，pressing Cmd+K 或者 `?` （或者意外 keypress）会把一个 fullscreen modal 罩在整个 viewport 上。多重 modal 还会叠 z-index 一起盖。modal 外面的内容**全部不可点**。点 modal 外的暗背景理论上能关 但不一定 wire 对。

视觉上：
- 上方：`<input placeholder="Jump to model, dataset, space, or page…">` 形如 Cmd+K command palette
- 下方：`<dialog>Keyboard shortcuts: / ? j k g then m ...</dialog>`
- 两者背景 `rgba(15,23,42,.55)`、`z-index:9998-9999`、`position:fixed;inset:0`

来源：早期某轮（如 R8 "advanced UX"）的 deepen prompt 让 subagent 加了 "Cmd+K command palette + j/k card nav + g-chord navigation" 之类，violation of `feedback_gui_only_no_keyboard.md`：

> 动作空间限 click/type/submit/select/hover/scroll/back，禁止 Cmd+K / j+k / g+s / ? / / 等键盘 hotkey

R8 round 在 2026-05-26 之前加的，那时 GUI-only feedback 还没立——所以混进了 14 个 vanilla 站。

### 怎么发现

```bash
# 1. 扫所有 R8 markup 变体
for s in sites/*/; do
  sn=$(basename "$s")
  hits=$(grep -rE 'r8-(cmdk|help|command-palette|modal|overlay)|R8:.*command palette|Keyboard shortcuts|keyboard-shortcuts|⌘K|Cmd\+K|/api/command-palette' "$s/templates" "$s/static" 2>/dev/null | wc -l)
  [ "$hits" -gt 0 ] && echo "$sn: $hits hits"
done

# 2. 扫 JS keydown listener 处理 Cmd+K / ? / j / k / g
grep -rnE "metaKey.*'k'|key === '\\?'|gPending|navCursor|openCmdK|toggleHelp|loadPalette" sites/*/static/js/*.js 2>/dev/null
```

Markup id 变体观察到的：`r8-cmdk` / `r8-help` / `r8-command-palette` / `r8-help-modal` / `r8-help-overlay` / `r8-help-list` / `r8HelpModal`、CSS class `.r8-modal` / `.r8-overlay` / `.r8-command-palette__panel`。每站都不同。

### 怎么根治（4 类清理）

**Category 1: 模板 markup**

`templates/base.html` (或对应 layout) 中：
- 删 `<div id="r8-*">...</div>` 整块
- 删 `<style>` 中 `.r8-*` 块
- 删 `{# R8: ... #}` 注释

**Category 2: JS keydown listener**

`static/js/*.js` 中删 IIFE 块（特征：`document.addEventListener('keydown', ...)` 处理 `metaKey + k` / `e.key === '?'` / `gPending` / `navCursor`）。整段 R8 listener IIFE 删干净 — Cmd+K 不开 modal、`?` 不开 help、`j/k/g+m` 不导航。

**Category 3: Route + handler**

`app.py` 中删：
- `/api/command-palette` route + handler（返回 search 结果给 palette 用的，无 modal 就不需要）
- `/api/keyboard-shortcuts` / `/api/shortcuts` 类似的 — 删
- 任何 `MARKETING_PAGES` / `PALETTE_ITEMS` in-memory dict 给 palette 喂数据的 — 删

**Category 4: site_specs/<slug>.yaml**

- `modals.r8_help_modal` / `modals.command_palette_modal` / `modals.cmdk_modal` 条目删
- 任何 `elements[].transition = open_modal` 指向上述 modal 的 — 改成 `page_navigate` 或删 element
- `atomic_skills` 中以"按 Cmd+K"/"按 ?"开头的 — 删
- `notes` 备注键盘 hotkey 的 — 删

### Docker hot-reload (不用重 build image)

```bash
for slug in <changed-sites>; do
  docker cp sites/$slug/templates wh-r10:/opt/WebSyn/$slug/
  docker cp sites/$slug/static wh-r10:/opt/WebSyn/$slug/ 2>/dev/null || true
  docker cp sites/$slug/app.py wh-r10:/opt/WebSyn/$slug/
done
docker restart wh-r10   # 重启所有 site_runner.py supervisor
```

### Verify

```python
import requests
r = requests.get('http://localhost:43010/')
assert 'r8-cmdk' not in r.text, "R8 cmdk modal still present!"
assert 'Cmd+K' not in r.text or 'Keyboard shortcuts' not in r.text
```

### 防止再发生（防止后续 deepen subagent 重新引入）

新派 deepen subagent 时 prompt 里加一条 **明确禁令**：

```
❌ 禁止加：keyboard shortcuts modal / command palette / Cmd+K hotkey / 
   j-k card navigation / g-chord navigation / "/" search focus hotkey /
   "?" help dialog / 任何 keydown listener
✅ 允许的交互：click / hover / form submit / scroll / browser back
```

每 deepen subagent 完成后跑上面 detection grep 复查。

**真案例（2026-05-27）**：14/15 vanilla 站受影响。allrecipes / apple / cambridge_dictionary / espn / github / huggingface / wolfram_alpha 几乎所有 vanilla 都中招。bbc_news / amazon / arxiv / booking / coursera / google_flights / google_map / google_search 在 templates/base.html 里没显式 markup 但可能在 JS listener / inline css 里有残留 — 需要 4 类全部 grep 确认。一次清掉，docker hot-reload，commit per-site。

## 42. 占位图被多个 entity 共用 — 视觉品质崩

**症状**：browse 列表页 / hub 页 / detail page 上 5-50 个不同 entity 的图全是同一张占位图。看起来像"Mock UI Studio"。最严重时：812 个城市的 hero_image 95% 都是 eiffel-tower.jpg，46 个 neighborhood 100% 都是同一张 hero-compass.svg。

视觉上：
- "Chemical Elements" 和 "Chemical Equations" 两个不同 section 用一模一样的截图
- City hub `/city/<slug>` 不管 slug 是 paris / tokyo / nyc 渲染的 hero 都是同一张
- Profile / Avatar 50%+ 用户用同一张 `avatar_00.jpg`
- Store / Branch / Location 全是同一张 `storefront_default.jpg`

### 怎么发现

```python
"""Find sites where many entities share the same image file."""
import sqlite3, glob, collections, pathlib
ROOT = pathlib.Path("sites")
for sd in sorted(ROOT.iterdir()):
    for db in glob.glob(str(sd / "instance" / "*.db")):
        con = sqlite3.connect(db)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tables:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
            img_cols = [c for c in cols if any(k in c.lower() for k in
                ('image','photo','poster','thumb','avatar','cover','banner','headshot','icon'))]
            for col in img_cols:
                rows = con.execute(f'SELECT "{col}" FROM "{t}" WHERE "{col}" IS NOT NULL').fetchall()
                if len(rows) < 20: continue
                top = collections.Counter([r[0] for r in rows]).most_common(1)[0]
                pct = top[1] * 100.0 / len(rows)
                if pct > 30:
                    print(f"{sd.name}/{t}.{col}: {top[1]}/{len(rows)} = {pct:.0f}% on {top[0][:60]}")
```

Threshold 30%：top 图占 ≥30% entity 就是 placeholder 问题。

JSON files 同理：

```python
import json, collections
data = json.load(open("sites/<slug>/<some>.json"))
imgs = [...]  # recurse pull all 'image' / 'poster' values
c = collections.Counter(imgs)
top = c.most_common(1)[0]
if top[1] / len(imgs) > 0.3:
    print(f"{top[1]}/{len(imgs)} share {top[0]}")
```

### 3 种 fix 策略

#### 策略 A：真扒（最高质量）

用 `mcp__tavily__tavily_search` + `WebFetch` 真去抓上游对应 entity 的代表图：

```python
for place in places:
    # tavily 搜真实图
    results = tavily_search(f"{place.name} cityscape hero image")
    img_url = results['results'][0].get('image_url') or results['images'][0]
    # 下载
    r = requests.get(img_url, timeout=10)
    fname = f"static/images/heroes/{place.slug}.jpg"
    open(fname, 'wb').write(r.content)
    place.hero_image = fname
db.session.commit()
```

适用：≤100 个 entity（fetch 慢 + 上游 rate-limit）。

#### 策略 B：deterministic md5 mapping over real pool

如果 `static/images/<kind>/*.jpg` 已经有 30+ 张真实图但没被使用：

```python
import hashlib, pathlib
pool = sorted([p.name for p in pathlib.Path("static/images/cities").glob("*.jpg")])
for city in cities:
    h = int(hashlib.md5(city.slug.encode()).hexdigest()[:8], 16)
    city.hero_image = f"static/images/cities/{pool[h % len(pool)]}"
db.session.commit()
```

适用：≥1000 个 entity but pool 只有几十张。每个 entity 有 stable assignment，不重 build 不会变。

#### 策略 C：SVG 生成（fallback）

如果完全没有真图：

```python
def gen_svg(slug, palette):
    h = hashlib.md5(slug.encode()).hexdigest()
    color = "#" + h[:6]
    initial = slug.replace("-", " ").title()[:2]
    return f'<svg xmlns="..." width="400" height="240">' \
           f'<rect width="400" height="240" fill="{color}"/>' \
           f'<text x="200" y="140" font-size="80" text-anchor="middle" fill="white">{initial}</text>' \
           f'</svg>'
```

每个 entity 一张独特 SVG，确定性，至少不全是同色块。

详见 gotcha #40 (SVG generation as image fallback) — 这里强调"不要共用一张占位"。

### 完成标准

修后再跑 detection grep，**任一 image_column 的 top 重复 ≤ 5%**。

### 防止再发生

deepen / clone-website / seed-database 三个 skill 都要在 seed 完成后跑一次 "image diversity check"：

```bash
python3 ~/webvoyager-analysis/scripts/check_image_diversity.py <slug>
# 输出每个 image-like 列的 top-N 重复百分比；任意 >30% 报错
```

把这个 check 集成到 `seed-database` SKILL 的"verify"步骤里，CI 也跑。

**真案例 (2026-05-27)**：
- compass：3 表 100% 共用 hero-compass.svg
- google_map：city 812 行 95% 是 eiffel-tower.jpg
- carmax：62 store 100% 是 storefront_default.jpg  
- wolfram_alpha：topic_galleries.json 56 image refs / 21 distinct (37% dup), mathematics.png 用了 10x
- github：39 user 54% 用 avatar_00.jpg
- berkeley：23 library 39% library_003.svg
- apartments_com：6048 floor_plan 31% floorplan-2br.svg
- google_search：1323 topic 92% images_json 是空数组 `[]`

## 43. 横向溢出 / 布局崩 — flex 子元素无 wrap 撑爆 viewport

**症状**：page 横向出现长长一行内容（产品 variant / band picker / tab strip / chip list）超过 viewport 宽，body 出现水平滚动条。看截图：apple watch 一个"Milanese Loop (R6) - Sand - 45/49mm" 等 variant 选择条目占满 viewport 后还在继续向右延伸，导致整页歪掉、其它内容也被推到右下角看不见 — 视觉品质崩。

伴生：
- 这些 variant 大多是 text-only（没匹配 product image，因 image_path 缺失或 fallback 失败）
- 截图显示同名条目重复（Sand 45/49mm + Sand 41/42mm + Lake Green 45/49mm + Lake Green 41/42mm + ... × N 色 × 2 size）— variant 笛卡尔积没收敛到 ≤8 cards 一行 + 多行

### 根因（CSS 常见 3 类）

1. **`display:flex` 没 `flex-wrap:wrap`**：子元素一律一行排，N 个 width=140px 子元素就是 N*140 px wide。修：加 `flex-wrap:wrap`，或包裹层加 `overflow-x: auto` 改成横向滚动 carousel。

2. **没设 `min-width:0` 在 flex 子元素**：长文本不收缩，撑爆父容器。修：variant card 加 `min-width:0; flex-basis: 140px; flex-shrink: 1`，或文本加 `overflow:hidden; text-overflow:ellipsis; white-space:nowrap`。

3. **fixed `width` 配 N children**：如 `.variant-row { width: max-content }` 配 16 个 variant — math 算出 2240px 直接破 1280viewport。修：去掉 max-content，改 grid `grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))`。

### 怎么发现（Playwright 全站扫）

```python
from playwright.sync_api import sync_playwright
def detect_overflow(slug, base_url, urls):
    issues = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        for url in urls:
            page.goto(base_url + url, timeout=10000)
            sw = page.evaluate("document.documentElement.scrollWidth")
            cw = page.evaluate("document.documentElement.clientWidth")
            if sw > cw + 5:  # 5px tolerance
                # locate offending element
                culprits = page.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('*').forEach(el => {
                        const r = el.getBoundingClientRect();
                        if (r.right > document.documentElement.clientWidth + 5) {
                            out.push({
                                tag: el.tagName,
                                cls: el.className.toString().slice(0,60),
                                w: Math.round(r.width),
                                right: Math.round(r.right)
                            });
                        }
                    });
                    return out.slice(0, 5);
                }""")
                issues.append({"url": url, "scrollWidth": sw, "clientWidth": cw, "culprits": culprits})
        b.close()
    return issues
```

跑 yaml 里 N 个 page，记录 scrollWidth > clientWidth 的 URLs + 撑爆的元素 className。

### 怎么修

```css
/* universal safety net in base.html */
html, body { overflow-x: hidden; }

/* variant pickers etc */
.variant-row, .band-picker, .tab-strip, .chip-row, .feature-grid {
  display: flex;
  flex-wrap: wrap;          /* 1️⃣ 关键：允许换行 */
  gap: 12px;
}
.variant-row > *, .band-picker > * {
  flex-basis: 140px;
  min-width: 0;             /* 2️⃣ 关键：允许收缩 */
  max-width: 200px;
}

/* OR carousel pattern if真心要单行（移动端常见）*/
.product-carousel {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}
.product-carousel > * {
  flex: 0 0 auto;
  scroll-snap-align: start;
}
```

### Variant explosion 衍生问题

screenshot 里同一个 band (Milanese Loop) × 4 color × 2 size = 8 个 cards，加上 Alpine Loop × 4 color × 2 size = 8 — 一行 16 cards，每个 140px = 2240px ≫ viewport。这是 **variant 笛卡尔积没收敛**：

修法：
- 把 variant **按 attribute 分级展示**：先展示 color (4 个), 用户选完再展示 size (2 个)。一次最多 4-8 card 一行。
- 或者 grid + wrap，让 16 个 card 自然分 4 行 × 4 列。

### 防止再发生

每 deepen subagent prompt 加一条：

```
❌ 禁止：variant card 平铺 N×M 笛卡尔积一行 (>8 张)
✅ 必须：grid wrap 自动多行 OR 分级 selector (color → size → ...)

所有新 template 必须通过 viewport overflow check：
  scrollWidth ≤ clientWidth + 5
```

每站完成时跑 `_verify_playwright.py` 加 overflow detection 模块。

**真案例 (2026-05-27)**：apple `/shop/buy-watch/<model>` Ultra 系列 watch band picker — 16 个 R6 band variant 一行平铺撑爆 viewport，整页视觉崩，下面 product detail 被挤到看不见。


## 44. 慢加载性能根治 — lazy-load + 图片宽高 + LIMIT + cache headers

**症状**：用户反馈"网站加载很慢，图片太多"。打开一个 list/hub page 等几秒才出图，且每个 image 加载都触发 layout reflow（页面跳动），点 link 跳到下一页又重 fetch 整套 static asset。

具体场景：
- huggingface `/models` 一次 query 456k repos
- google_map `/maps` 一次 fetch 903k places
- amazon homepage 200+ thumb 全用 default `<img src>` 没 lazy / 没 width/height
- 所有 page reload 都重 fetch `/static/images/...`（默认 Flask 不设 Cache-Control）

### 4 类优化（一起做）

#### A. 全 site `<img>` 加 `loading="lazy"`

```bash
for s in sites/*/; do
  find $s/templates -name '*.html' -exec sed -i \
    's/<img \(src=\)/<img loading="lazy" decoding="async" \1/g' {} \;
done
```

⚠️ above-the-fold (首屏) hero image 不加 lazy。简单办法：全加 lazy，浏览器会自动 prioritize viewport 内的 image —— 实测影响很小，可以接受。

#### B. 图片明确 width/height — 防 layout shift

```html
<!-- 改前：CLS 满天飞 -->
<img loading="lazy" src="...">
<!-- 改后 -->
<img loading="lazy" width="240" height="160" src="...">
```

option 1：jinja 模板用 DB 字段 `width="{{ obj.image_w or 240 }}"`
option 2：默认值约定 — thumb 240×160 / hero 800×480 / avatar 80×80

#### C. List page LIMIT + pagination

大 DB 站必做。每个 list view function 加：
```python
PAGE_SIZE = 24
page = int(request.args.get('page', 1))
q = Model.query.order_by(...)
total = q.count()
items = q.limit(PAGE_SIZE).offset((page-1) * PAGE_SIZE).all()
n_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
return render_template('list.html', items=items, page=page, n_pages=n_pages)
```

模板加 prev/next 按钮 + 页码 strip。或 "Load more" 跳下一页。

#### D. Static asset cache headers — 防重复 fetch

`app.py` 顶层加 hook：
```python
@app.after_request
def add_static_cache(resp):
    if request.path.startswith('/static/'):
        resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    return resp
```

86400 = 1 天。如果 image / css / js 文件名带 hash (e.g. `main.abc123.css`) 可改成 `max-age=31536000` (1 年)，因为内容变了文件名也变。

### 验证

```python
import requests
r = requests.get('http://localhost:43010/')
html = r.text
n_img = html.count('<img')
n_lazy = html.count('loading="lazy"')
assert n_lazy / n_img > 0.9, f"only {n_lazy}/{n_img} img lazy"

r2 = requests.get('http://localhost:43010/static/css/main.css')
assert 'max-age=86400' in r2.headers.get('Cache-Control', '')
```

Playwright 测 page load time：
```python
page.goto(url, wait_until='load')
load_ms = page.evaluate("performance.timing.loadEventEnd - performance.timing.navigationStart")
assert load_ms < 3000  # under 3s
```

### 防止再发生

每 deepen / clone-website subagent prompt 加一条：

```
新加 list/hub template 必须有 LIMIT (≤ 24 per page) + pagination
新加 <img> tag 必须有 loading="lazy" + width=N + height=N
app.py 必须有 @app.after_request 给 /static/* 加 Cache-Control max-age=86400
```

每 `verify-site-gui` pass 增加 perf check（page load time / lazy ratio / cache headers）。

**真案例 (2026-05-27)**：用户截 hf 站慢加载报告，36 站统一优化通过。

## 45. Docker port mapping 在 restart 后丢失 — 必须 recreate 不是 restart

**症状**：`docker restart wh-r10` 后所有 host:port → container:port 映射消失。`docker port wh-r10` 返回空。`docker inspect` 显示 `HostConfig.PortBindings` 有配置但 `NetworkSettings.Ports` 是 `{}`。host 端 curl 全 000。

容器内 process 本身正常（`docker exec ... urllib.urlopen(http://127.0.0.1:40000)` 200）。问题在 host iptables forwarding 没建立。

**根因（未确认）**：可能是 docker daemon 版本 bug，或宿主 iptables 规则被外部清理（NSG 改动 / cni race / systemd-networkd 干预）。`docker restart` 仅 stop+start 但不重建 network namespace。

### 修复

不要 `docker restart`，每次都 **recreate**：

```bash
docker rm -f wh-r10
docker run -d --restart unless-stopped --name wh-r10 \
  -p 8311:8101 \
  -p 43000-43035:40000-40035 \
  webharbor:r10-final
```

`docker rm -f` + `docker run -p ...` 强制重建网络 namespace 和 iptables 规则。

### 自动化 wrapper

写一个 bash function 替代 `docker restart`：

```bash
wh_restart() {
  local name=$1
  local image=$(docker inspect $name --format '{{.Config.Image}}')
  local ports=$(docker inspect $name --format '{{range $p, $conf := .HostConfig.PortBindings}}-p {{(index $conf 0).HostPort}}:{{$p}} {{end}}' | sed 's|/tcp||g')
  docker rm -f $name
  docker run -d --restart unless-stopped --name $name $ports $image
}
wh_restart wh-r10
```

### docker cp hot-fix 也别 restart

如果只是 `docker cp` 进新文件，**不要** docker restart 那个容器（会丢端口）。改用：
1. `docker cp` 修改文件
2. `docker exec wh-r10 sh -c "pkill -HUP -f site_runner.py.*<slug>"` 触发那个 site 重启（如果 supervisor 支持）
3. 或 control_server `/reset/<site>` HTTP endpoint

如果必须重启整个容器（image 改了），用上面的 wh_restart wrapper。

**真案例 (2026-05-27)**：本会话至少 2 次 docker restart 后端口丢，每次需要 docker rm -f + docker run 重建才恢复。

## 46. Container 容器内 instance_seed 跟随 image，hot-fix 失效

**症状**：本地 `sites/<slug>/instance_seed/<db>` 已经更新到新 schema（promotion from instance/），但容器 `/opt/WebSyn/<slug>/instance_seed/<db>` 仍然是 image build 时 baked-in 的旧 schema。Container restart 时 websyn_start.sh 跑 `cp -a instance_seed instance` 把旧 schema 复制回 instance/，site 又 schema-drift crash。

### 修复路径



**⚠️ Werkzeug 重要陷阱**：Flask 静态 blueprint 在 `SEND_FILE_MAX_AGE_DEFAULT=None` (modern default) 下**预先 set `Cache-Control: no-cache`** 到每个 static response。所以 `headers.setdefault('Cache-Control', '...')` 是 **no-op**（已经有值），覆盖不生效。**必须用直接赋值**：

```python
@app.after_request
def add_static_cache(resp):
    if request.path.startswith('/static/'):
        resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'  # 直接赋值，不要 setdefault
    return resp
```

verify：`curl -I http://localhost:43000/static/css/main.css | grep Cache-Control` 必须看到 `max-age=86400` 而不是 `no-cache`。本会话第一轮 36 commit 用 setdefault 全 silently 失败，第二轮直接赋值才生效。

#### Path A：rebuild image + recreate container

```bash
cd ~/repos/WebHarbor
./scripts/build.sh webharbor:r10-final     # ~10-15 min, COPYs latest sites/
docker rm -f wh-r10
docker run -d --restart unless-stopped --name wh-r10 \
  -p 8311:8101 -p 43000-43035:40000-40035 webharbor:r10-final
```

Clean，但慢。

#### Path B：docker cp + 不重启容器（hot patch）

```bash
for s in <broken-sites>; do
  for db in ~/repos/WebHarbor/sites/$s/instance_seed/*.db; do
    [ -s "$db" ] || continue
    docker cp "$db" wh-r10:/opt/WebSyn/$s/instance_seed/$(basename $db)
    docker cp "$db" wh-r10:/opt/WebSyn/$s/instance/$(basename $db)
  done
done
# 用 control_server reset，不全 restart 容器
for s in <broken-sites>; do
  curl -s -X POST http://localhost:8311/reset/$s --max-time 10
done
```

⚠️ `/reset/<site>` 是否真重启 site process 依赖 control_server.py 实现。**如果它只是 cp seed→instance** 而 site_runner.py 已经 import 了旧 schema，重启 site process 才能拿到新 DB。看 control_server.py 源码确认。

#### Path C：bind-mount sites/ 进容器（最灵活）

dev 时不 COPY，bind mount：
```bash
docker run -d --restart unless-stopped --name wh-r10 \
  -p 8311:8101 -p 43000-43035:40000-40035 \
  -v ~/repos/WebHarbor/sites:/opt/WebSyn \
  webharbor:r10-final
```

local 改文件立刻生效（不用 docker cp）。但开发友好不代表 prod 友好 — release 时 build image。

### 检测

```bash
# 比较 image 里 DB 跟本地 DB
docker exec wh-r10 md5sum /opt/WebSyn/huggingface/instance_seed/hf.db
md5sum ~/repos/WebHarbor/sites/huggingface/instance_seed/hf.db
# 不匹配 → container 不是最新
```

### 防止再发生

如果 deepen subagent 改了 `instance/<db>` 而没 promote 到 `instance_seed/<db>`：

```bash
# promote helper
for s in sites/*/; do
  sn=$(basename "$s")
  for db in $s/instance/*.db; do
    [ -s "$db" ] || continue
    bname=$(basename "$db")
    seed=$s/instance_seed/$bname
    if [ ! -f "$seed" ] || [ "$(wc -c <"$db")" -gt "$(wc -c <"$seed")" ]; then
      cp "$db" "$seed"
      echo "promoted $sn/$bname"
    fi
  done
done
```

把这个加到每 deepen subagent 完成的 checklist 里。

## 47. 站根本没 CSS — base.html 引了 file 但 static/css/*.css 不存在 (404)

**症状**：打开 site，看到的是完全裸 HTML 浏览器默认样式：
- 蓝色下划线链接
- 无 layout（所有元素纵向堆叠或满屏铺开）
- 图片不对齐，文本块挤在一起
- 输入框是原生 chunky 灰色，按钮是 OS-default

不是 "CSS 加载慢" 或 "broken CSS rule" — 是 **CSS file 根本不存在**。

### 怎么发现

```bash
# 1. base.html 引用了什么 CSS
grep -hoE "static/css/[^'\"\\) ]+\.css" sites/<slug>/templates/*.html | sort -u

# 2. 验证文件存在
for ref in $(grep -hoE "static/css/[^'\"\\) ]+\.css" sites/<slug>/templates/*.html | sort -u); do
  fname=${ref#static/}
  if [ ! -f "sites/<slug>/static/$fname" ]; then
    echo "MISSING: $ref"
  fi
done

# 3. 浏览器端
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:<port>/static/css/<file>.css
# 404 = missing
```

全 36 站扫：

```bash
for s in sites/*/; do
  sn=$(basename "$s")
  for ref in $(grep -hoE "static/css/[^'\"\\) ]+\.css" "$s/templates/"*.html 2>/dev/null | sort -u); do
    fname=${ref#static/}
    [ ! -f "$s/static/$fname" ] && echo "$sn: MISSING $ref"
  done
done
```

### 怎么修

clone-website 系列 skill 应该已经在 Step 4 (Backend build) 生成 CSS。但 boardgamegeek 这种是 community PR site，作者没写 CSS（或写了但忘 commit）。

**Fix path A**：手写一份基础 CSS，按真上游品牌 + 视觉风格：

参考 `~/repos/WebHarbor/sites/boardgamegeek/static/css/bgg.css`（真案例 230 lines）—— 包含：
- header gradient + 品牌色 (BGG 棕橙)
- nav links
- search form
- card grid + hover effect
- ranking table 风格
- buttons + forms
- footer
- responsive media query
- **horizontal overflow safety net**: `html, body { overflow-x: hidden; max-width: 100vw; }`

**Fix path B**：复用其它 site 的 CSS 做 starter，改色 / 改字体。

**Fix path C**：用 Tavily 抓上游一份 CSS snippet 参考，再 polish。

### Hot-deploy

```bash
docker cp sites/<slug>/static/css wh-r10:/opt/WebSyn/<slug>/static/
# 不需要 restart，CSS 静态文件下次 page reload 就生效
```

### 防止再发生

每 clone-website / PR-merge 时跑 detection grep。把它加到 `verify-site-gui` harness 的检查项：

```python
# 在 verify_one() 里加
import re
for tpl in (sd / "templates").glob("*.html"):
    src = tpl.read_text()
    for ref in re.findall(r"static/[^'\"\\) ]+\.(?:css|js)", src):
        fname = ref.replace("static/", "")
        if not (sd / "static" / fname).exists():
            findings["missing_static"].append({"template": tpl.name, "ref": ref})
```

**真案例 (2026-05-27)**：boardgamegeek (port 43030) 整站裸 HTML —— `base.html` 引 `/static/css/bgg.css` 但该文件根本不存在。修法：写 230-line bgg.css (BGG 风：棕橙 / 卡片网格 / ranking table)；docker cp 后立即可见。其它 35 站扫了一遍无类似问题。

## 48. CSS 负 margin 把内容挡掉 / 截掉 — Amazon hero 灾难

**症状**：page 顶部出现奇怪的 dark / colored strip 浮在内容上方，下面卡片网格看上去像浮在彩色背景里——但实际**那个背景是某个 section 被 negative margin 拉到几乎消失**，只剩一条 thin strip。用户看到：

- amazon `/`: 深色 navy 条压在 cards 网格上方，应该是完整的 "Welcome to Amazon" hero CTA 整个被遮住
- 经检查 `.hero-banner { margin-bottom: -200px; }` —— 设计初衷是 hero 含一张大图（image height ~250px），负 margin 把下一个 section 拉上来 200px 营造"floating cards over hero image" 效果（真 amazon 风格）
- 但 lite-CTA 版本的 hero 只有 ~120px 高（padding 40 + 标题 + button），-200px 把整个 hero 都拉到 cards 下面去了

### 怎么发现

```bash
# 扫所有大负 margin（>=200px 嫌疑大）
for s in sites/*/; do
  sn=$(basename "$s")
  hits=$(grep -hnE 'margin(-top|-bottom)?\s*:\s*-[2-9][0-9][0-9](px|em|rem)' "$s/static/css/"*.css 2>/dev/null)
  [ -n "$hits" ] && echo "=== $sn ===" && echo "$hits"
done

# 加 inline style 里的
grep -rhnE 'margin(-top|-bottom)?\s*:\s*-[2-9][0-9][0-9](px|em|rem)' sites/*/templates/*.html 2>/dev/null
```

任何 `margin-X: -200px+` 都嫌疑大。如果配合一个本来矮的 sibling section，**几乎一定是 bug**。

### 怎么修

#### Fix A：去掉负 margin

最简单：去掉这条 CSS。如果原设计需要"cards 浮在 hero 上"效果但 hero 本来就矮，去掉负 margin 后 cards 自然 stack 在 hero 下，符合 80% 用户期望。

```css
.hero-banner {
    ...
    /* margin-bottom: -200px;   ← removed: lite-CTA hero too short */
}
```

#### Fix B：保证 hero 足够高

```css
.hero-banner {
    min-height: 280px;        /* hero ≥ |margin| + 80px buffer */
    margin-bottom: -200px;
}
```

#### Fix C：sticky-sidebar 风格（recreation_gov 案例）

```css
@media (min-width: 901px) {
    .detail-content-grid {
        margin-top: -600px;    /* 主内容拉上覆盖 sidebar */
    }
    .detail-side-column {
        padding-top: 600px;    /* sidebar 顶部空 600px 让主内容浮上 */
    }
}
```

这是 **paired** pattern — `-X` 配 `+X`，是 intentional sticky-sidebar 设计，不是 bug。**判定标准**：搜 sibling element 有没有对应 +X padding/margin。有 → intentional；没有 → bug。

### 防止再发生

- 在 deepen / clone-website prompt 加："禁止任何 `margin: -X` 其中 X > section 自身高度。如果要做 overlap effect，sibling 必须有对应 `padding`/`margin` 补偿"
- verify-site-gui harness 加 visual sanity check: 截图首页，目测顶部 content 不被遮挡

**真案例 (2026-05-27)**：amazon `.hero-banner { margin-bottom: -200px }` 把 ~120px hero 几乎完全遮住，只剩顶部 thin dark strip 漏在 cards 上方。修法 = 删 `margin-bottom: -200px`，commit 5e52a17。recreation_gov `.detail-content-grid { margin-top: -600px }` 配 `.detail-side-column { padding-top: 600px }` 是 sticky-sidebar，intentional，不动。

## 49. Feature regression — 并行 fix subagent 误删 interactive 部件

**症状**：用户报告 "之前能用的功能现在用不了"。例 amazon /cart/update qty=3 → DB 没生效；google_map /place/save → 500；allrecipes save_recipe → 模板渲不出。

### 怎么发生的

多个 fix subagent 并行修不同问题（R8 cleanup / overflow / asset audit / perf optimize），每个都 docker cp 改文件。可能：

- R8 cleanup 删 modal markup 时，误删 modal 内的 `<form action="/cart/update">`
- overflow fix 加 `overflow: hidden` 在 form 容器上 → dropdown 折叠不见，无法选 qty
- asset audit 修 form action `/search/_/q/` → `/search` 时，sed 误改了其他 `/_/` 路径
- perf optimize 加 `.limit(20)` 在 `cart.items.query` 上 → 第 21 个 cart item 看不见
- image dup fix `UPDATE places SET hero_image = ...` 误改了 `cart_items.image`（共用 col 名）

### 怎么发现

dispatch 一个专门"feature regression hunter" subagent：

对每站、每个 interactive feature（cart / save / review / follow / wishlist / login）：
1. test_client login as benchmark user
2. POST 对应 endpoint
3. GET 验证 effect（cart item 出现 / saved 列表有它 / etc）
4. 任何 fail 记录 + `git log --oneline sites/<site>/ -10` 看最近 commit 找 culprit

### 怎么修

找 culprit commit，**精准 revert** 那条改动（不要 revert 整 commit，否则其他 fix 也丢）。`git show <hash>` 看每个 file 改了什么，恢复 broken file 的那行。

### 防止再发生

- **并行 fix subagent 数量 ≤3** 同时改同 site —— 多了 race
- 每 fix subagent 完成前必须跑一个 "smoke test" 验证主要交互还 work
- verify-site-gui harness 加 POST/form smoke test 模式（不只 GET）

**真案例 (2026-05-27)**：5 个并行 fix subagent (R8/overflow/image-dup/asset-audit/perf) 同时改 amazon，结果 /cart/update + /cart/remove 退化。专门派 hunter agent 找 culprit + revert specific lines + verify。
