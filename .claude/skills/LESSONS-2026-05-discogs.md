# Lessons from the Discogs mirror (2026-05)

War-story log behind the iteration of the WebHarbor skills. Each lesson
here is also referenced from the SKILL.md / `gotchas.md` it most affects.
Read it once, then go back to the skill files for the mechanical recipes.

Many lessons here **overlap** with `LESSONS-2026-05-boardgamegeek.md`
(form-submit selectors, parallel-agent SITES churn, HF Python API upload,
pinned-RNG seeding). Where the BGG file already covers a topic, this file
cross-references it and only records what was *additionally* learned for
Discogs.

Site: `sites/discogs/`
GitHub PR: <https://github.com/aiming-lab/WebHarbor/pull/34>
HF PR: <https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/24>
Outcome: 7,042 releases (3,522 Discogs + 3,520 MusicBrainz), 5,031 artists,
3,938 labels, 86,714 ratings, 2,640 marketplace listings, 323 real Wikipedia
covers. 20/20 Playwright handwalk PASS. Byte-identical reset
`3e7373b547034a45800a62c413a9feeb`.

---

## 1. Scraping (clone-website) — when one source isn't enough

### 1a. Discogs public API hard-blocks at ~25 req/min, *and* the limit is per-IP shared with other agents

The Discogs `/database/search` endpoint takes 25 unauthenticated req/min
on paper. In practice from a shared Azure / corp egress IP, a single bad
minute (we hit it with `time.sleep(2.6)`) gets the IP blacklisted for
**5–15 minutes** — every subsequent request returns `HTTP 429` regardless
of pacing. Worse: our retry loop with `backoff = 1, 2, 4, 8` *adds* to
the load against the same IP, deepening the block.

We started at 500 results (all Rock — first genre in our SEARCHES list)
and stalled there for half an hour, watching the same `429` come back.

**Recipe that worked:**

1. Cap `sleep_s` at 12s **and** spread genres via `random.shuffle(combos)`
   so the first minute hits *all* genres, not 5 pages of Rock.
2. Limit to `pages_per_combo = 2` for breadth; come back later if you
   need more depth.
3. **Don't put the scraper in tight retry loops.** A failed request
   should mean "abort this page, sleep an extra 15s, move on" — never
   "back off and try again".
4. **Add a second data source.** Discogs is good for marketplace +
   community signals (have/want counts, prices) but you can't rely on
   it for catalog breadth. We fell back to MusicBrainz for the bulk of
   the catalog.

### 1b. MusicBrainz as the second source — open, 1 req/sec, diverse tags

For music sites, MusicBrainz (`musicbrainz.org/ws/2/release-group/?...`)
is the right primary catalog source:

- No auth required (with a real `User-Agent` containing contact email)
- 1 req/sec polite policy, no IP-level block; you actually get 60/min
- Multi-tag query lets you sweep diverse genres in one script: rotate
  `jazz` / `techno` / `disco` / `funk` / `dub` / `ska` / `soul` etc.
- 80–100 release-groups per query → 30 tags × 80 = 2,400 releases in
  ~5 minutes

Field-mapping notes:

- MusicBrainz `release-group.id` is a UUID, not an integer. We minted
  synthetic Discogs-style IDs starting at `90_000_001` so the
  `discogs_id` column stays integer-typed and unique.
- `first-release-date` is `YYYY-MM-DD` (sometimes just `YYYY`); parse
  defensively.
- `artist-credit` is a list of dicts; the *first* element is what you
  want for "primary artist".

See `sites/discogs/scraped_data/scrape_musicbrainz.py` for the working
recipe. It ran clean to 3,520 release-groups across 30 genre tags in ~6
minutes.

### 1c. Album covers — CoverArt Archive is blocked from this env; use Wikipedia

The canonical free source for album covers is CoverArt Archive
(`coverartarchive.org`, hosted by Internet Archive). In this VM the TLS
handshake to `coverartarchive.org:443` is interrupted mid-protocol
(`SSL_ERROR_SYSCALL`, `UNEXPECTED_EOF_WHILE_READING`). Tested in `curl`,
`python -m urllib.request`, and Playwright — all fail. Almost certainly
a transparent middlebox / corp egress filter (the SNI looks suspicious
to a deep packet inspector).

Workaround that *does* work: **Wikipedia REST API + `upload.wikimedia.org`
for image bytes**. Both hosts resolve and TLS clean from this env.

Recipe (`sites/discogs/scraped_data/scrape_wikipedia.py`):

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
        if data and data.get("thumbnail", {}).get("source"):
            return data
    return None
```

Hit rate on our 7,042-release catalogue: **323 covers** (≈ 28% of the
1,150 lookups we attempted, ≈ 5% of total releases). The rest don't
have a Wikipedia page — *and that's fine*. Use a fallback SVG
("no-cover.svg") with a vinyl-record glyph and the agent never knows
the difference. **Don't try to hide the gap by stretching the same
N covers across M releases.**

### 1d. Image URL needs the `originalimage` field, not just `thumbnail`

Wikipedia's summary endpoint returns both:

```json
"thumbnail":     { "source": "https://upload.wikimedia.org/.../330px-X.jpg", "width": 330 },
"originalimage": { "source": "https://upload.wikimedia.org/.../X.jpg",       "width": 3000 }
```

`thumbnail.source` works for browser preview but is downsized. For real
fidelity, prefer `originalimage.source`. Our covers are 200KB–3MB and
look genuinely like real Discogs detail pages.

---

## 2. Templating (clone-website + evolve-env)

### 2a. `pag.items` collides with dict's `.items()` method

Subtle Jinja bug. We returned pagination state as a `dict`:

```python
return {"items": items, "page": page, "pages": pages, ...}
```

Then in the template:

```jinja
{% for r in pag.items %}
```

Python evaluates `pag.items` as **`dict.items` (the method)**, not the
`"items"` *key*, because dict's method lookup beats `__getitem__` in
Jinja's attribute resolution. The for-loop then tries to iterate a bound
method and crashes with:

```
TypeError: 'builtin_function_or_method' object is not iterable
```

The fix is one-character: return a `SimpleNamespace` (or any object with
an `items` attribute, not a method):

```python
from types import SimpleNamespace
return SimpleNamespace(items=items, page=page, pages=pages, ...)
```

**General rule**: never use dict keys that collide with Python's built-in
dict methods (`items`, `keys`, `values`, `get`, `pop`, `update`, `copy`,
`clear`) when the dict is going to a Jinja template. Either rename the
key or wrap in SimpleNamespace/dataclass.

### 2b. Jinja macros do NOT accept `**kwargs`

Wrote a paginate-link macro:

```jinja
{% macro pagination(pag, endpoint, **kwargs) %}
  <a href="{{ url_for(endpoint, page=p, **kwargs) }}">{{ p }}</a>
{% endmacro %}
```

→ `TemplateSyntaxError: expected token 'name', got '**'`. Jinja's macro
grammar is strict positional/named params, no `*args` or `**kwargs`. You
must pass the variadic part as an explicit dict:

```jinja
{% macro pagination(pag, endpoint, params=None) %}
  {% set params = params or {} %}
  <a href="{{ url_for(endpoint, page=p, **params) }}">{{ p }}</a>
{% endmacro %}
```

Callers:

```jinja
{{ m.pagination(pag, 'search', params={'q': q, 'sort': sort, 'genre': genre.slug}) }}
```

`**params` in `url_for()` works fine — it's only the macro signature
that rejects `**`.

### 2c. Macro alias must not shadow a context variable

In `templates/master.html` I had:

```jinja
{% import "_macros.html" as m %}
{{ m.title }}     {# the Master object passed to render_template #}
```

The macro alias `m` shadowed the `m` view-context variable (the Master
row). Jinja silently looks at the macro module, finds no `.title`, and
errors with `'jinja2.environment.TemplateModule object' has no attribute
'artist'`.

Fix: rename the alias when it would collide:

```jinja
{% import "_macros.html" as mac %}
{{ m.title }}     {# now resolves to the view-context Master #}
```

**Convention to avoid this**: in `templates/_macros.html`, import as
`mac` everywhere; reserve single-letter `m` for view-context objects.

---

## 3. Backend — public ID vs internal PK (clone-website)

### 3a. `Model.query.get(rid)` is by PRIMARY KEY, not by public ID

We expose releases at URLs like `/release/793593` where `793593` is the
public **Discogs ID** (column `discogs_id`), not the SQLAlchemy primary
key. The release-detail route handles both:

```python
r = Release.query.filter_by(discogs_id=rid).first() or Release.query.get_or_404(rid)
```

But the **`/sell` route** I wrote *only* did `Release.query.get(rid)`:

```python
release = Release.query.get(rid)   # ← uses PK only, ignores discogs_id
```

Task #13 was "list release ID 793593 for sale" — `rid=793593` mapped to
PK=793593, which didn't exist (our PKs are 1..7042). The form silently
hit the `if not release: flash("Pick a valid release")` branch and the
listing never persisted. Playwright reported PASS-ish because the page
navigated cleanly; only DB inspection revealed the bug.

**Rule**: any route that takes a user-typed `release_id` (forms where
the user transcribes the ID from a URL) must accept BOTH:

```python
release = (Release.query.filter_by(discogs_id=rid).first()
           or Release.query.get(rid))
```

For routes whose `release_id` comes from a hidden form field rendered
by *our* template (where we control whether it's `r.id` or
`r.discogs_id`), pick one and stick with it. We picked `r.id` (the PK)
because it's smaller and never collides.

**Audit step** before opening a PR: `grep -n 'request.form.get."release_id".*type=int' app.py`
and verify each callsite's lookup strategy matches the form's hidden
field type.

### 3b. SQLite `ORDER BY year ASC` puts NULL *first*

Task #5 was "Miles Davis oldest release, sorted year ↑". For a clean
catalog this would return a 1950s record. For a catalog that has some
`year IS NULL` rows (≈ 8% of MB releases have no first-release-date),
SQLite returns NULL rows first, so the agent sees "Star People | · CD ·
Europe" with an empty year — confusing and ambiguous.

Fix is one chained method call: `.nullslast()`:

```python
if sort == "year_asc":
    q = q.order_by(Release.year.asc().nullslast())
elif sort == "year_desc":
    q = q.order_by(Release.year.desc().nullslast())
```

After the fix, task #5 stably returns "Plays For Lovers (1965)" — a
real-looking oldest record.

**Audit**: `grep -n "Release\.year\.\(asc\|desc\)()" app.py` and chain
`.nullslast()` everywhere unless you genuinely want NULL-first ordering.

---

## 4. Playwright walk-through (evolve-env)

### 4a. Form-submit selector — see `LESSONS-2026-05-boardgamegeek.md §3a`

Same identical bug. `page.click('button[type="submit"]')` clicks the
header search bar's button before reaching the login / register / sell /
list-new form's button. We burned 4 iterations debugging "why does
alice_crate log in but then have no Add-to-Collection form?" before
realizing Playwright was just submitting the header search.

Use `form[method="post"] button[type="submit"]` *or* anchor to a unique
input on the form (`input[name="password"]`'s ancestor form).

### 4b. The shared symptom: "form looks empty / button missing" → check login first

When the test reports "no Add-to-Collection form on release page" or "no
wantlist form" after a login step, the most likely cause is that **the
login step didn't actually log in** (see 4a) — the release page then
renders the un-authenticated branch (the `{% if current_user.is_authenticated %}`
block is hidden).

Diagnostic two-liner:

```python
page.goto(f"{BASE}/release/793593")
print(page.url, ':',
      'logged in' if 'Sign out' in page.content() else 'NOT logged in')
```

If "NOT logged in", revisit the login function before debugging the form.

### 4c. Walking your own collection is destructive — reset between runs

The walk script in `agent_demo/walk_discogs_tasks.py` performs CRUD as
it goes (adds collections, removes items, creates lists, posts replies).
Running it twice without `POST /reset/discogs` between runs will:

- Discogs--16 "remove HOUSE NATION" → reports FAIL on the 2nd run because
  the item is already gone
- Discogs--3, 4, 8, 11, 13, 19 → all PASS on the 2nd run because state
  is already there, but the *first-run* assertion may be different

Always start a fresh walk with:

```bash
curl -X POST http://localhost:8801/reset/discogs
.venv/bin/python walk_discogs_tasks.py
```

---

## 5. Seed reproducibility (seed-database)

### 5a. `MIRROR_REFERENCE_DATE` is the cheap fix; full RNG isolation is the right one

The skill `seed-database/SKILL.md §6` calls out `datetime.utcnow()` as a
byte-identity hazard. I pinned `NOW = datetime(2026, 5, 26, 0, 0, 0)` and
did `sed -i 's/datetime\.utcnow()/NOW/g'` over `seed_data.py`. That
fixes *date* non-determinism.

What it does NOT fix: bare `random.randint()` and `random.choice()`
calls in the catalogue-seed loop that use Python's global RNG (seeded
from `os.urandom`). Two clean re-seeds gave different counts for
"listings = 2640 vs 2709" precisely because the listing-creation loop
used `random.random() < 0.22` to decide whether each release got a
listing, against the global RNG.

`LESSONS-2026-05-boardgamegeek.md §4b` has the full recipe — make every
non-deterministic call go through one pinned `_R = random.Random(N)`
instance. We *partially* did this (the `seed_community` body has
`rng = random.Random(42)`), but the catalogue loop and benchmark-user
loop both still use the global RNG.

**For Discogs specifically**, this isn't a release-blocker because:

1. The **shipped** `instance_seed/discogs.db` is the source of truth at
   build time. Reset (file copy) is byte-identical against the SHIPPED
   binary, which is what the byte-identity invariant cares about.
2. Re-running `seed_data.py` from `scraped_data/` is a contributor /
   forensic workflow, not a runtime path.

But on next iteration I'd switch to a pinned `_R` (see BGG §4b) for full
bit-for-bit re-seed reproducibility.

### 5b. bcrypt salt — pinned hash if you want re-seedable passwords

Same trap the Phys.org PR #6 documented:
`bcrypt.generate_password_hash(...)` mixes a random salt every call, so
two re-seeds give different `users.password_hash` even with all other
RNG pinned.

Workaround used by Phys.org: pre-compute one hash per password and
inline it as a `PINNED_PASSWORD_HASH = "..."` constant. `check_password_hash`
accepts the pinned hash transparently because bcrypt encodes the salt
into the hash itself.

We didn't do this on Discogs (each fresh re-seed generates new hashes),
but the *shipped* seed DB has stable hashes. The lesson is: if you want
hash stability across re-seeds, pin one hash per user.

---

## 6. PR workflow (cross-cutting)

### 6a. Branch off `origin/main`, not local main — see BGG §5a

Local `main` accumulated 200+ commits from other parallel agents'
in-progress merges (compass, osu, craigslist, ted, nba, mega, imdb,
phys_org, carmax, recreation_gov, ...). A branch from local main would
have produced a PR containing every one of those *as someone else's
work*.

What worked:

```bash
git fetch origin
git worktree add -b feat/discogs-mirror /tmp/wh-discogs-pr origin/main
# /tmp/wh-discogs-pr now has 15 sites + 3 reg files, untouched by parallel work
rsync -a --exclude='__pycache__' --exclude='.venv' --exclude='instance/' \
      --exclude='scraped_data/' --exclude='static/images/' \
      sites/discogs/ /tmp/wh-discogs-pr/sites/discogs/
# Edit the 3 reg files in /tmp/wh-discogs-pr to ADD discogs at the end
git -C /tmp/wh-discogs-pr add sites/discogs/ websyn_start.sh control_server.py Dockerfile
git -C /tmp/wh-discogs-pr commit -m "..."
git -C /tmp/wh-discogs-pr push fork feat/discogs-mirror
```

PR diff: 43 NEW files in `sites/discogs/`, 3 sync files modified
(EXPOSE 40015 + add `discogs` to SITES). **Zero other changes.**

### 6b. Worktree builds can't `docker build` — assets aren't checked out

`git worktree add` only checks out git-tracked files. Heavy assets
(`instance_seed/*.db`, `static/images/`, `static/external_cache/`) are
gitignored — they live in HF and arrive via `scripts/fetch_assets.sh`.

So a worktree at `/tmp/wh-discogs-pr/` is missing the assets for
*every other site* (not just yours). `docker build` from that worktree
fails at boot:

```
[WebSyn] Resetting all databases to seed state...
cp: cannot stat '/opt/WebSyn/allrecipes/instance_seed': No such file or directory
```

Don't try to docker-build from the worktree. Verify the build from the
**main repo** (where `fetch_assets.sh` has populated everything), then
push the worktree branch. The CI on the maintainer's side will do its
own asset fetch.

### 6c. HF upload via `huggingface_hub` Python API — see BGG §4e

Same recipe. `from huggingface_hub import HfApi, CommitOperationAdd`
→ `api.create_commit(repo_id='ChilleD/WebHarbor', repo_type='dataset',
operations=[...], create_pr=True)` returns a `CommitInfo` with `.pr_url`
and `.pr_num`. The `hf` CLI is broken (Typer / Sentinel incompatibility)
in this env.

For Discogs the call returned `pr_url =
https://huggingface.co/datasets/ChilleD/WebHarbor/discussions/24`,
which I cross-referenced in the GitHub PR body.

### 6d. All open WebHarbor PRs claim port 40015 — that's the convention

The site-tracking sheet is the source of truth for "the next port".
**Every open PR claims port 40015** because each branches off
`origin/main` (15 sites, next port = 40015). Maintainers reconcile the
ports at merge time. Don't try to coordinate via local main's port
allocation — it's racy and doesn't match what the maintainer will see.

### 6e. `gh pr create` warns "uncommitted changes" — that's fine if they're in *your other working dirs*

When opening the PR via `gh pr create --repo aiming-lab/WebHarbor --head
hqhq1025:feat/discogs-mirror ...`, `gh` warns "60 uncommitted changes".
Those are the parallel-agent edits in the *main* working dir, not in the
worktree we pushed from. The PR is created against the pushed branch
regardless and contains exactly what the worktree had.

---

## 7. Container fragility — same as BGG §6

Other agents kept removing our test containers. Use a unique name
(`wh-discogs-test`) on a far-away port range (`8801` + `45000-45015`) to
minimize collisions. Each verification run is ~90s container-lifetime;
don't expect state to persist across handwalk batches.

---

## 8. Final by-the-numbers

| Lesson | Time cost without it | Time cost with it |
|---|---|---|
| 1a (Discogs 429 lockout) | 30 min watching 429 retries fill the log | Spread + cap to 12s/req + accept partial coverage |
| 1b (MusicBrainz fallback) | Stuck at 500 Rock releases | 3,520 release-groups across 30 tags in ~6 min |
| 1c (CoverArt blocked → Wikipedia) | 0 covers shipping | 323 real covers from upload.wikimedia.org |
| 2a (`pag.items` collision) | ~30 min debugging "object not iterable" | One `SimpleNamespace` line |
| 2b (Jinja macro **kwargs) | First template render crashed every page | Pass `params=` dict explicitly |
| 3a (`.get` vs `discogs_id`) | Task #13 silently failed; only DB inspection caught it | One-line `filter_by(discogs_id=…).first() or .get(…)` |
| 3b (NULL year first) | Task #5 returned a year-less record | `.nullslast()` everywhere |
| 4a (form-submit selector) | 4 iterations debugging "form looks empty" | Anchor selectors to form, ~5 lines per login |
| 6a (branch off origin/main) | Local main has 200+ unrelated commits | Worktree + cherry-pick own files; PR diff is clean |

Total time saved if these were known up-front: **~3 hours on a single mirror**, on top of the ~3 hours BGG already documents. Most of the saved time is on (1a) and (4a).
