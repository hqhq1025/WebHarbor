# tools/bulk_api/ — direct-API entity expansion

Companion to `tools/harvest/` (Phase 0). Where harvest is **route-sampled**
(~14 representative URLs per site, JSON-LD records 0–22 per site), `bulk_api`
hits each site's official/public API or feed and pulls **hundreds–thousands**
of structured entity rows directly into `instance/<site>.db`.

Per-site script: ~100 lines. Per-site run: 2–10 min. Hits real CDN/API.
**0 Tavily**. Picks up where harvest's JSON-LD enrichment plateaus.

## When to use

- Mirror DB looks underpopulated relative to upstream (IMDb shipping 392
  titles vs 11M on imdb.com is fine; shipping 392 vs the 1500+ a single
  benchmark task needs is not).
- harvest snapshot's `_extruct_index.json` only yields a dozen rows per page
  because the site is SPA / paywalled / non-JSON-LD.
- You need *real* entity metadata (rating, release date, roster, RSS feed),
  not just real images.

**Don't use** for:
- Real upstream HTML markup → use `tools/harvest/` instead.
- Real entity images → use `scrape-real-images` skill (Wikipedia FIRST).
- Synthetic data fill (when the upstream API has no real data at this URL,
  do NOT fabricate — leave NULL).

## Per-site recipe table

| Site | Source | Endpoint pattern | Ship script |
|---|---|---|---|
| imdb | OMDB (free key `trilogy`) | `omdbapi.com/?s={term}&y={year}&type=movie` then `?i={tt_id}&plot=full` | ✅ `imdb_omdb.py` |
| nba | ESPN site API | `site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{id}/roster` | ✅ `nba_espn_roster.py` |
| bbc_news | BBC RSS (21 subsection feeds) | `feeds.bbci.co.uk/news/<section>/rss.xml` | ✅ `bbc_rss_feeds.py` |
| boardgamegeek | BGG XML API v2 | `boardgamegeek.com/xmlapi2/hot?type=boardgame` then `/thing?id={id}&stats=1` | ⏳ template |
| github | GitHub REST v3 | `api.github.com/search/repositories?q={q}&sort=stars` | ⏳ template |
| allrecipes | category page scrape | `allrecipes.com/recipes/{cat_id}/?page={n}` | ⏳ template |
| ted | TED `__NEXT_DATA__` from talk listing | `ted.com/talks?page={n}` JSON island | ⏳ template |
| coursera | Coursera browse pages | `coursera.org/browse/{subject}?page={n}` | ⏳ template |
| arxiv | arxiv API | `export.arxiv.org/api/query?search_query=cat:{cat}&max_results=100` | ⏳ template |
| huggingface | HF API | `huggingface.co/api/models?limit=100&full=true&sort=downloads` | ⏳ template |
| fandom | Fandom REST | `<wiki>.fandom.com/api.php?action=query&list=allpages&aplimit=500` | ⏳ template |
| craigslist | RSS / `?format=rss` | `<region>.craigslist.org/search/{cat}?format=rss` | ⏳ template |

Sites that should NOT use `bulk_api` (no public API, just clone-website):
google_search, google_map, google_flights, wolfram_alpha, cambridge_dictionary,
booking, apple, amazon, espn (sports DB locked behind auth).

## Conventions enforced by `_common.py`

- **UA**: full Mozilla string (some CDNs 403 on bot-looking UAs).
- **Retries**: 3 attempts with exponential backoff (0.8→1.6→3.2s).
- **Periodic commit**: every 50 INSERT — subagent stall recovery.
- **INSERT OR IGNORE on canonical unique key**: never UPDATE, never UPSERT
  on top of seeded rows. Re-running the script must be safe.
- **Diversity gate**: top image URL must be <5% of rows (or call fails loudly).
- **Never touch**: PINNED bcrypt rows, 4 benchmark users, instance_seed/.
  Edit `instance/<site>.db`; reset rebuilds it from `instance_seed/<site>.db`
  later — `seed-database` Phase 5 handles that handover.

## Workflow (where this sits in the pipeline)

```
Phase 5  seed-database
   ├─ 5a  idempotent seed (existing)
   ├─ 5b  scrape-real-images (existing)
   ├─ 5c  image diversity gate (existing)
   └─ 5d  bulk-api-enrich  ← THIS
```

Order matters: `bulk_api` runs BEFORE `scrape-real-images` so that 5b can
fill in CDN/Wikipedia thumbs for the newly-added rows in the same pass.

After running, the change must propagate to `instance_seed/<site>.db`:
```
normalize_seed_db_layout sites/<site>/instance/<site>.db \
                         sites/<site>/instance_seed/<site>.db
```
(See `seed-database` skill for the exact recipe + HF asset repack.)

## Writing a new fetcher

1. Copy `_template_site.py` to `<site>_<source>.py` (e.g. `bgg_xmlapi.py`).
2. Fill in the 4 TODOs (site slug, API base, candidate pool, image column).
3. Run with: `.venv/bin/python3 tools/bulk_api/<script>.py > /tmp/<site>_bulk.log 2>&1`
4. Verify in container:
   ```
   docker exec wh-r10 sqlite3 /opt/WebSyn/<site>/instance/<site>.db \
       'SELECT COUNT(*) FROM <table>'
   ```
5. If schema needs new columns first, that's a `harden-env` change — do
   it in `app.py` model first, NEVER in raw SQL DDL here (gotcha #H).

## Verifying without spawning containers

Each script is self-contained and just reads + writes one SQLite DB. Run it
locally; no Flask, no container, no /reset/<site> needed until you want to
verify the live mirror shows the new rows.
