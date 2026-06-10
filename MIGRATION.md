# MIGRATION.md — WebHarbor data-generation pipeline migration runbook

This is a copy-pasteable runbook for moving the WebHarbor data-generation pipeline to a
fresh machine. Read section 0 first, then do the OLD-machine work (section 1) **before**
you touch the new box, or you will silently lose data.

> Conventions in this doc:
> - The repo root on the new machine is the cloned WebHarbor repo (referred to as `$REPO`).
> - Always invoke the venv binary directly: `.venv/bin/python3`, `.venv/bin/pip`, `.venv/bin/hf`.
>   **Never** `source .venv/bin/activate` (shell state does not persist between steps in our tooling).
> - `<site>` is a site slug from the SITES array (see §3).

---

## 0. What WebHarbor is, and what actually migrates

WebHarbor mirrors **36 real websites** as self-contained offline Flask apps, packaged into
one Docker image, fronted by a control plane on port `8101` that does sub-second per-site
SQLite database resets (byte-identical, for RL-rollout determinism). It produces two data
products:

1. **The served mirrors** — `sites/<site>/app.py` (Flask + SQLAlchemy + Jinja), each seeded
   from `sites/<site>/instance_seed/<site>.db`, each running as its own process on
   `40000 + index`.
2. **Structured benchmark tasks** — deterministic, DB-oracle-derived JSONL specs produced by
   `scripts/generate_structured_tasks.py` (no LLM). Legacy NL tasks live in
   `sites/<site>/tasks.jsonl`.

### What travels how

| Layer | Where it lives | Migrates via | Notes |
|---|---|---|---|
| Site code, seed scripts, CSS, templates, `tasks.jsonl`, `tools/`, `scripts/` | git-tracked (`sites/*` etc.) | **git** | ~7200 tracked files. |
| Seed DBs `instance_seed/*.db`, `static/images/`, `static/external_cache/` | git-ignored, HF dataset `ChilleD/WebHarbor` | **Hugging Face** | The `.assetpaths` globs. ~16 GB on disk; ~2.8–2.9 GB transfer as per-site `<site>.tar.gz`. |
| Runtime DBs `sites/*/instance/`, HF download cache `sites/.cache/` | git-ignored + docker-ignored | **local-only / ephemeral — DO NOT migrate** | `instance/` is rebuilt from `instance_seed/` at every container boot. |
| `scraped_data/`, large dashboard logs, `*.devloginbak`/`*.preauthbak`/`*.restart` | git-ignored / junk | **do not migrate** | Re-run harvest if you need recon JSON. |

**Hard rule:** a fresh clone has **empty** `instance_seed/` dirs. The image will not build and
`check_assets.sh` will hard-fail until you run `fetch_assets.sh`. Never assume `sites/` assets
are in git.

---

## 1. Pre-migration on the OLD machine

The Hugging Face dataset is **the authoritative source for assets on the new box**, but it is
currently **stale** versus local: cached tarballs reflect HF state from ~May 17/26, while real
local content was modified through **May 28** in 23 of 25 tarballed sites, and **11 sites have
no tarball on HF at all** (`apartments_com, berkeley, boardgamegeek, discogs, eventbrite,
fandom, imdb, mayo_clinic, osu, rotten_tomatoes, smartasset`). If you migrate now without
fixing this, a naive `fetch_assets.sh` on the new box **silently discards all May 18–28 edits
and drops those 11 sites entirely.** This is the single biggest migration hazard.

### 1a. Commit + push the code

```bash
cd /home/v-haoqiwang/repos/WebHarbor
git status --short
git rev-list --left-right --count origin/main...main   # expect: 0  <N>  -> fast-forward OK
```

The current working tree has ~58 **junk** untracked files (`*.devloginbak`, `*.preauthbak`,
`*.restart`, `app.py.bak-WV-*`, `.claude/worktrees/`) that the existing `*.bak` ignore rule does
**not** match. **Never `git add -A`.** Extend `.gitignore`, then stage explicitly:

```bash
# 1) Swallow the junk first
printf '\n# editor/agent backups + restart markers\n*.devloginbak\n*.preauthbak\n*.restart\nsites/*/app.py.bak-*\n.claude/worktrees/\n.claude/workspace/\n' >> .gitignore

# 2) Stage real edits (app.py / templates / seed / css)
git add -u sites/

# 3) Stage KEEP assets explicitly (favicons, audio, bulk-api scripts)
git add sites/*/static/icons/ sites/cambridge_dictionary/static/audio/ \
        sites/booking/static/js/destination_autocomplete.js \
        sites/amazon/seed_augment_for_v19.py \
        sites/eventbrite/scripts_download_images_v2.py \
        sites/huggingface/scripts/wave2_real_images.py \
        sites/mayo_clinic/_download_images.py sites/mayo_clinic/_fetch_doctors.py \
        sites/mayo_clinic/_reencode_images.py sites/mayo_clinic/_retry_images.py \
        sites/mayo_clinic/_image_catalog.json \
        tools/bulk_api/bbc_rss_feeds.py tools/bulk_api/imdb_omdb.py \
        tools/bulk_api/nba_espn_roster.py .gitignore

# 4) Verify no junk slipped in
git status --short | grep -E 'devloginbak|preauthbak|\.restart|\.bak-|\.claude/worktrees' \
  && echo 'JUNK STAGED - STOP' || echo 'clean'
git diff --cached --name-only | sort   # final review

# 5) Commit + push (fast-forward to upstream main)
git commit -m 'sites: dev-login + real-image upgrade across mirrors; add favicons/audio + bulk-api image scripts'
git push origin main      # or 'git push fork main' if you lack push rights to aiming-lab/WebHarbor
```

> Remotes: `origin = github.com/aiming-lab/WebHarbor` (upstream), `fork = github.com/hqhq1025/WebHarbor`.
> **Stranded work, decide before migrating:** three locked `.claude/worktrees/agent-*` worktrees
> hold unmerged commits (mayo_clinic / eventbrite / fandom, 3–7 ahead, NOT in main). Pushing main
> does not capture them — cherry-pick/merge first if you want them. `WebHarbor-booking-image-pr`
> has 2 uncommitted templates on `codex/fix-booking-homepage-images`. `feat/imdb-mirror` and
> `imdb-pr` are duplicate (same SHA) — delete one.

### 1b. Generate `requirements.txt` (there is none in the repo)

The host tooling env is 60 packages with **no `requirements.txt`**. The Dockerfile's inline pip
list (~12 pkgs) is image-only and does not cover the host scripts/tools. Capture ground truth on
the OLD box and commit it:

```bash
.venv/bin/pip freeze > requirements.txt
git add requirements.txt && git commit -m 'add host tooling requirements.txt (pip freeze ground truth)' && git push origin main
```

### 1c. Make HF authoritative (resync ALL assets, including the 11 missing sites)

Stop the running container first and checkpoint any WAL so tarballs capture a clean DB (the
packer includes whatever is under `instance_seed/`, including live `-shm`/`-wal` sidecars):

```bash
# stop containers that are mid-run; for each live DB:
sqlite3 sites/<site>/instance_seed/<site>.db 'PRAGMA wal_checkpoint(TRUNCATE);'   # if a WAL exists
```

Pack every site (incl. the 11 untarballed) into a staging dir and push:

```bash
export PATH="$PWD/.venv/bin:$PATH"      # so `hf` resolves
./scripts/extract_assets.sh ../wh-static-pr/ --push
# == repacks sites/*/{instance_seed,static/images,static/external_cache} -> <site>.tar.gz
#    then: hf upload-large-folder ChilleD/WebHarbor ../wh-static-pr --repo-type dataset
```

(Equivalent two-step without auto-push: `./scripts/extract_assets.sh ../wh-static-pr/` then
`hf upload-large-folder ChilleD/WebHarbor ../wh-static-pr --repo-type dataset`.)

### 1d. Pin a reproducible asset revision

`.assets-revision` pins `revision: main`, a **moving branch** — a fresh box could fetch different
assets later. After the HF upload lands, pin a commit SHA for reproducibility:

```bash
# get the HF commit sha from the upload output / HF UI, then:
sed -i 's/^revision:.*/revision: <hf-merge-sha>/' .assets-revision
git add .assets-revision && git commit -m 'pin assets to <hf-merge-sha>' && git push origin main
```

> CI fails closed if `.assets-revision` points at an unreachable HF revision — push/merge the
> HF side **first**, then bump the pin.

---

## 2. Fresh-machine bootstrap

Prerequisites on the new box: Docker engine, Python 3.12 (`python3.12`), `tar`/`gzip`, `bash`,
`awk`, `curl`, `git`. **Do not rsync the old `.venv`** — venvs hardcode the interpreter path.

```bash
# 2a. clone
git clone <webharbor-repo-url> WebHarbor && cd WebHarbor

# 2b. host tooling venv (recreate, never copy)
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt      # the committed freeze from §1b
# if requirements.txt is somehow absent, regenerate it from the OLD box (§1b) — do NOT
# improvise from the Dockerfile, which is image-only.

# 2c. fetch HF assets (~2.8 GB, several minutes; run in background)
export PATH="$PWD/.venv/bin:$PATH"             # so `hf` resolves; or call .venv/bin/hf
export HF_TOKEN=<token>                          # ONLY if the dataset became gated; else skip / `hf auth login`
./scripts/fetch_assets.sh                        # pulls all <site>.tar.gz @ pinned rev, extracts into sites/<site>/
# single site:  ./scripts/fetch_assets.sh amazon
# override pin: ASSETS_REVISION=<sha> ./scripts/fetch_assets.sh

# 2d. gate: every site must have a non-empty instance_seed/
./scripts/check_assets.sh
```

### Env vars (read from environment, none hardcoded)

| Var | Used by | When |
|---|---|---|
| `CONTROL_PORT` / `PORT` | `control_server.py` | override control-plane port (default 8101) |
| `ASSETS_REVISION` | `fetch_assets.sh` | override the `.assets-revision` pin |
| `HF_TOKEN` | `hf` CLI | only if HF dataset is gated |
| `OMDB` key (`trilogy` free) | `tools/bulk_api/imdb_omdb.py` | imdb harvest |
| `GITHUB_TOKEN` | `tools/bulk_api/github_rest_search.py` | github harvest |
| `BGG_BEARER` | `tools/bulk_api/boardgamegeek_bgg_xml.py` | boardgamegeek harvest |
| `HARVEST_UA` | harvest scrapers | optional UA override |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | `agent_demo/` | only for agent smoke tests |

> `agent_demo/` is a **separate uv-managed env** (browser-use, openai, playwright). It is NOT
> required to bring the mirrors up. If you need it: `cd agent_demo && uv sync && uv run playwright
> install chromium`. Delete any checked-in `.venv` there first.

---

## 3. Bring the sites up + verify

The **source of truth for the site list and ports is the `SITES` array** in
`control_server.py` and `websyn_start.sh` (kept index-aligned with the Dockerfile `EXPOSE`
line). README/AGENTS/CLAUDE/CONTRIBUTING say 15–20 sites on `40000-40014` — **that prose is
stale.** The live array is **36 sites on `40000-40035`**:

```
0  allrecipes   1  amazon     2  apple        3  arxiv       4  bbc_news     5  booking
6  github       7  google_flights  8 google_map  9 google_search  10 huggingface  11 wolfram_alpha
12 cambridge_dictionary  13 coursera  14 espn  15 phet_simulations  16 berkeley  17 drugs_com
18 rotten_tomatoes  19 imdb  20 recreation_gov  21 carmax  22 phys_org  23 discogs  24 compass
25 osu  26 craigslist  27 ted  28 nba  29 mega  30 boardgamegeek  31 apartments_com  32 smartasset
33 eventbrite  34 mayo_clinic  35 fandom
```

```bash
# build (auto-fetches assets if any instance_seed/ is missing; ~3 min cold, ~30s warm)
./scripts/build.sh webharbor:dev

# run with the FULL port range — using 40000-40014 silently loses sites 15-35
docker run -d -p 8101:8101 -p 40000-40035:40000-40035 webharbor:dev

# verify control plane + all sites
curl -s http://localhost:8101/health | python3 -m json.tool | head
for p in $(seq 40000 40035); do curl -so /dev/null -w "$p:%{http_code}\n" http://localhost:$p/; done
```

**Known expected anomalies (not regressions):**
- `imdb` boots **dead** (seed intentionally not yet written).
- `berkeley` and `smartasset` seed DBs are generated at **docker-build time** (the Dockerfile
  runs `python3 -c 'from app import app'` and copies `instance/<site>.db` to `instance_seed/`),
  not fetched from HF. A broken seed import fails the **build**, not just runtime.

### Control-plane endpoints

```bash
curl -s   http://localhost:8101/health          # status of every site
curl -X POST http://localhost:8101/reset/amazon  # kill, wipe instance/, copytree from seed, respawn
curl -X POST http://localhost:8101/reset-all      # reset every site in parallel
# /restart/<site> exists too: respawn WITHOUT wiping the DB
```

**Reset invariant check** — after a reset, runtime DB md5 must equal the seed DB md5:

```bash
docker exec <container> md5sum /opt/WebSyn/amazon/instance/amazon.db \
                               /opt/WebSyn/amazon/instance_seed/amazon.db
```

(The in-image path is `/opt/WebSyn/<site>` — the legacy WebSyn name predates the rename and is
kept stable.)

---

## 4. Run the data-generation pipeline end-to-end (structured tasks)

Structured task generation is **deterministic, DB-oracle-based, no LLM**. It runs on the **host
venv** (not in Docker) and imports each site app from a throwaway temp copy. Coverage is **13 of
the 15 original oracle sites** — `bbc_news` and `google_search` are excluded (empty article /
search tables), and the 21 newer mirrors (carmax, ted, nba, …) have **no structured support,
only legacy `tasks.jsonl`**. Do not assume all 36 sites are covered.

```bash
# discover
.venv/bin/python3 scripts/generate_structured_tasks.py --list-sites
.venv/bin/python3 scripts/generate_structured_tasks.py --site amazon --list-families

# generate (3 families/site: detail lookup, identify-by-constraints, state mutation + multi-entity)
.venv/bin/python3 scripts/generate_structured_tasks.py \
    --site amazon --family product_identify_by_constraints \
    --limit 25 --offset 0 --output /tmp/amazon_identify.jsonl

.venv/bin/python3 scripts/generate_structured_tasks.py \
    --site amazon --family cart_add_multiple_products \
    --item-count 2 --quantity-profile mixed --limit 20 --output /tmp/amazon_multi.jsonl
```

Mutation tasks inject a login persona from `configs/auth_personas.json` (benchmark password is
uniformly `TestPass123`; the login URL is the **real upstream** login URL, not localhost). Output
is JSONL with DB-derived `target_entity`, `constraints`, `expected_answer`, `validation`. Committed
examples live in `webvoyager_dashboard/mutation_runs`.

### Validate (re-loads the same oracle in three phases)

```bash
.venv/bin/python3 scripts/validate_structured_task.py --spec /tmp/amazon_identify.jsonl --phase spec
.venv/bin/python3 scripts/validate_structured_task.py --spec /tmp/amazon_cart.jsonl     --phase before
# after a mutation run completes, re-validate with --phase after
```

> Full per-tool details: `docs/structured-task-pipeline.md`. The single-site build playbook
> (Chinese, Steps 0–10; reference site `recreation_gov`) is `GUIDANCE.md`. Scaffold a new site
> with `./scripts/new_site.py <slug>` (registers in 3 places: `websyn_start.sh`,
> `control_server.py`, Dockerfile — keep all three index-aligned).

---

## 5. The `bulk_api` harvest tools — regenerate site data from real APIs

`tools/bulk_api/` (Phase 5d) hits each site's official/public API or feed and pulls
**hundreds–thousands** of structured rows directly into `instance/<site>.db`. Each script is
self-contained (reads + writes one SQLite DB, no Flask/container needed), uses `INSERT OR IGNORE`
on a canonical unique key (re-runnable), and **must never** touch the 4 pinned bcrypt benchmark
users or `instance_seed/`.

Shipped fetchers: `imdb_omdb.py` (OMDB, free key `trilogy`), `nba_espn_roster.py` (ESPN site
API), `bbc_rss_feeds.py` (BBC RSS). Others are templates — see the recipe table in
`tools/bulk_api/README.md`. Sites with no public API (google_*, wolfram_alpha, cambridge,
booking, apple, amazon, espn) should NOT use bulk_api.

```bash
# set any required tokens first (see §2 env table), then run a fetcher:
.venv/bin/python3 tools/bulk_api/imdb_omdb.py        > /tmp/imdb_bulk.log 2>&1
.venv/bin/python3 tools/bulk_api/nba_espn_roster.py  > /tmp/nba_bulk.log 2>&1
.venv/bin/python3 tools/bulk_api/bbc_rss_feeds.py    > /tmp/bbc_bulk.log 2>&1

# verify row count against the live mirror (after a reset)
docker exec <container> sqlite3 /opt/WebSyn/<site>/instance/<site>.db 'SELECT COUNT(*) FROM <table>'
```

**Pipeline order matters:** `bulk_api` (5d) runs **before** `scrape-real-images` (5b) so image
backfill picks up the newly-added rows. After running, propagate the change into the seed DB:

```bash
normalize_seed_db_layout sites/<site>/instance/<site>.db sites/<site>/instance_seed/<site>.db
# (exact recipe + HF asset repack live in the seed-database skill; then repack via §1c/§6)
```

Once the seed DB changes, **repack and push to HF** (§1c) and bump `.assets-revision` (§1d), or
the next `fetch_assets.sh` on any box will overwrite your work with the old tarball.

> The full pipeline is `harvest (Phase 0) -> bulk_api (5d) -> seed-database (5a/5b/5c) -> audit
> -> structured-task generation`. It is documented per-tool only (`tools/harvest/README.md`,
> `tools/bulk_api/README.md`, `tools/audit/README.md`); the phase numbers reference companion
> skills under `.claude/skills` — **verify `.claude/skills` survived migration** (it may be
> machine-local / gitignored).

---

## 6. Troubleshooting + known risks / stale-data hazards

**Stale assets (highest-priority hazard).** `.assets-revision` defaults to the moving branch
`main`. If you skipped §1c/§1d, HF is stale and `fetch_assets.sh` restores May-17/26 state and
drops 11 sites. Fix: do §1c on a machine that still has the good local assets, then re-pin.

**`fetch_assets: 'hf' CLI not found`** → `.venv/bin/pip install -U "huggingface_hub[cli]"`,
then `export PATH="$PWD/.venv/bin:$PATH"` or call `.venv/bin/hf`. A missing `hf` also breaks
`build.sh` (it auto-calls fetch). If the dataset is gated: `hf auth login` or set `HF_TOKEN`.

**`check_assets.sh` reports MISSING (required)** → a site has an empty `instance_seed/`.
Re-run `./scripts/fetch_assets.sh <site>`. This gate also runs in CI and in `build.sh`.

**Port range too small / sites 15–35 missing** → you used `40000-40014` from the stale README.
Use `-p 40000-40035:40000-40035`. Treat the `SITES` arrays as source of truth.

**Published image `battalion7244/webharbor:latest` exposes only ~20 sites** → it may predate the
36-site repo. Prefer `./scripts/build.sh` to get the current environment; verify with the
`seq 40000 40035` curl loop in §3.

**Reset md5 mismatch / non-byte-identical reset** → a non-idempotent seed function, a handler
that writes the DB on first access, or an import-time timestamp write. Every seed function must
early-return on a populated DB; even a no-op commit bumps SQLite metadata and breaks byte
identity (and RL-rollout determinism). Audit with `scripts/audit_seed_randomness.py`.

**Reset hangs / zombie supervisors** → supervisors started by `websyn_start.sh` (not respawned by
`control_server`) become un-reaped zombies until container exit; `control_server` only owns Popen
handles for sites it respawned itself. Harmless, but relevant when debugging. `site_runner.py`
exists because Werkzeug's threaded `serve_forever()` ignores `SIGTERM`; the supervisor uses
`setsid` so `control_server` can `killpg(SIGKILL)` the whole group.

**Lost Booking gallery images / ESPN league+team PNGs after a fetch** → those are un-upstreamed
local hotfixes under HF-managed `static/images`; re-running `fetch_assets.sh` or pulling the
upstream image wipes them. Permanent fix = updated HF tarballs for `booking` and `espn`
(`OPERATIONS.md`). The canonical hotfix/audit workspace is the sibling `WebHarbor` checkout, not
the `WebHarbor-booking-image-pr` worktree.

**Structured generator `ImportError` / silent breakage** → it imports each site via `importlib`
reusing short module names (`app`, `seed_data`, `content_data`), popping them between sites. Any
site refactor that renames a model/attribute silently breaks generation and validation. It needs
a venv whose Flask/SQLAlchemy roughly match the image (host venv Flask 3.1.1 vs image 3.1.0 is
fine — do **not** "reconcile" the two envs; the image stays reproducible from the Dockerfile, the
host env from the freeze).

**`webvoyager_dashboard` yields empty/partial data** → `generate_data.py` is pinned to the old
Azure VM: hardcoded container name `webharbor-audit`, host ports `8311->8101` and
`43000-43014->40000-40014`, an Azure IP, and a sibling WebVoyager checkout (`WEBVOYAGER_ROOT`).
None of this travels. To use it on the new box, recreate the `webharbor-audit` container with
those port maps, the WebVoyager checkout, NSG rules, and the
`webharbor-dashboard-preview.service` systemd unit (http.server on `5188`). The `tools/audit/`
scripts also hardcode `localhost:8311/health` — they find no sites against a standard image.

**`git worktree` lists broken entries** → one old worktree path lives under
`/datadrive/root-migrations/...` which won't exist on the new box. Run `git worktree prune`.

**Do not migrate:** `sites/*/instance/`, `sites/.cache/`, `scraped_data/`, the old `.venv`, large
dashboard logs (~103 MB), pid files under `/tmp/websyn_pids`, logs under `/tmp/websyn`.
