# Data source registry — public APIs / datasets used across the batch

A field-tested list of free, no-key (or trivial-key) data sources that produced
real seed data for WebHarbor mirrors. Use this as the first stop when extending
or building a new mirror; only fall back to synthesis if nothing here fits.

Every entry below was used in a real mirror polish pass. The "battle-tested"
column says which site already proved the source works against our seed
pipeline.

---

## Generic catalogs (works for many mirrors)

| Source | URL | Auth | Battle-tested in | Good for |
|---|---|---|---|---|
| **Wikipedia (REST summary)** | `https://en.wikipedia.org/api/rest_v1/page/summary/<title>` | none | rotten_tomatoes (people headshots) | bio + thumbnail (300px) for any named entity. Rate-limited; respect `User-Agent` + ≤4 parallel workers |
| **OpenStreetMap Overpass** | `https://overpass-api.de/api/interpreter` | none | google_map | places by category + city, lat/lng |
| **US Census MSA list** | `census.gov` static lists | none | compass, craigslist, booking | top-100 US metros with state |
| **OpenFlights airports.dat** | `github.com/jpatokal/openflights/blob/master/data/airports.dat` | none | google_flights | 7k+ airports IATA/ICAO/lat/lng |
| **NHTSA vPIC** | `https://vpic.nhtsa.dot.gov/api/` | none | carmax | make/model/year permutations |

## Domain-specific APIs

### Movies / TV / talks

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **TMDB** | `api.themoviedb.org/3` | API token (free) | — | best for movie posters / actor headshots but **token required** |
| **OMDb** | `omdbapi.com` | free key | — | fallback when TMDB token missing |
| **Rotten Tomatoes movie pages** | `rottentomatoes.com/m/<slug>` | none | rotten_tomatoes | flixster CDN poster URLs via regex |
| **TED `__NEXT_DATA__`** | `ted.com/talks` HTML | none | ted | 350 real talks + thumbnails via `pi.tedcdn.com` |

### Recipes / food

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **TheMealDB** | `themealdb.com/api/json/v1/1/search.php?f=<letter>` | none | allrecipes | 633 unique meals A-Z + full ingredient list + image URL |

### Education / dictionary

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **WordNet (NLTK local)** | `pip install nltk; nltk.download('wordnet')` | offline | cambridge_dictionary | beats `dictionaryapi.dev` which 429s aggressively (~88% of bursts rejected); 1500 entries in seconds offline |
| **arXiv API** | `export.arxiv.org/api/query?search_query=cat:<cat>` | none | arxiv | use 3.2s sleep between calls; sweep 47 categories |
| **PhET metadata** | `phet.colorado.edu/services/metadata/1.3/simulations` | none | phet_simulations | 184 sims; HTML5 subset = 119 |
| **OSU programs catalog** | `gpadmissions.osu.edu/programs/` | none | osu | HTML parse |
| **Berkeley programs A-Z** | `berkeley.edu/academics` | none | berkeley | HTML parse |

### News / scientific articles

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **BBC RSS** | `feeds.bbci.co.uk/news/<section>/rss.xml` | none | bbc_news | real `pubDate` + `media:thumbnail` URL; 11 sub-feeds (tech/business/health/sci/sport/…) |
| **Phys.org RSS** | `phys.org/rss-feed/` | none | phys_org | 210 articles; **watch `pubDate` parsing for `EDT`/`PDT`** — strptime `%Z` rejects them, strip the TZ token first |
| **news.osu.edu RSS** | `news.osu.edu/feed/` | none | osu | per-category RSS |
| **news.berkeley.edu RSS** | `news.berkeley.edu/feed/` | none | berkeley | recent only (~10 live items, augment with templated headlines) |

### Code repos / model hub

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **GitHub Search API** | `api.github.com/search/repositories?q=stars:N..M&sort=stars` | optional token | github | unauth: 60 req/hr; with token: 5000/hr. **Segment by `stars:N..M` ranges** (e.g. 1000..2000, 2000..5000, …) to avoid hitting 1000-result cap per query |
| **HuggingFace Hub** | `huggingface.co/api/{models,datasets,spaces}?sort=downloads` | none | huggingface | 2276 real repos; pipeline_tag + library_name + sdk all in payload |

### Health / drugs / facilities

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **DailyMed (NIH)** | `dailymed.nlm.nih.gov/dailymed/services/` | none | drugs_com | drug labels + classification |
| **RxNorm (NLM)** | `rxnav.nlm.nih.gov/REST/` | none | drugs_com | drug interaction graph |
| **RIDB** | `ridb.recreation.gov/api/v1/facilities` | **key required** (401 without) | recreation_gov | failed without key; fell back to NPS campground synthesis from public-knowledge inventory |

### Sports

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **NBA Stats** | `stats.nba.com/stats/` | none | nba | needs realistic `User-Agent`; rate-limited |
| **ESPN site API** | `site.api.espn.com/apis/site/v2/sports/...` | none | espn | rich; multiple `apis/...` paths per sport |

### Mapping / aviation

| Source | URL | Auth | Battle-tested in | Notes |
|---|---|---|---|---|
| **OpenFlights airports.dat** | (see above) | none | google_flights | |
| **OSM Nominatim** | `nominatim.openstreetmap.org/search` | none | — | geocoding; 1 req/s policy |

---

## Anti-patterns to avoid

- **`dictionaryapi.dev`** — 429s ~88% of bursts at sustained 1 req/s. Use WordNet offline instead.
- **Live RT API** for posters — 401 without TMDB token. Use page scrape + Wikipedia for cast.
- **Bare `User-Agent: python-requests/...`** — banned by NBA Stats and many others. Always set a browser-style UA.
- **TMDB without API token** — 401. Either ship a token via env var or skip.
- **`api.nps.gov`** from corp networks — DNS often blocked; have a fallback synthesis path.

---

## Throttle / pagination patterns

- **arXiv**: 3.2s sleep between requests; OAI explicitly asks for this
- **Wikipedia REST**: ≤4 parallel; honor `Retry-After` on 429; set proper `User-Agent`
- **GitHub Search**: segment by stars range; pages cap at 1000 results per query; sort=stars with explicit ranges fans out cleanly
- **HF Hub**: no documented throttle, fine at 10 parallel
- **TheMealDB**: 26 A-Z queries cover the catalog; no throttle issues
- **NBA Stats**: needs `User-Agent: Mozilla/...` + `Referer: https://www.nba.com/`; 2s between requests

---

## When all of the above fails — synthesis rules

If the real source is blocked / rate-limited / requires payment, synthesize
**deterministically** from a smaller real anchor:

1. Take a small public anchor (Wikipedia "List of …", US Census, BLS SOC).
2. Cross-product it (e.g. 30 makes × 10 models × 7 years for cars).
3. Derive every numeric field from a hash of the anchor key
   (`int.from_bytes(hashlib.md5(slug.encode()).digest()[:4], "big") % range`)
   so rebuilds are bit-for-bit identical.
4. Never use `random.random()` without seeding from a string derived from the row's stable identifier.

Example seen in this pass: **carmax** (NHTSA make/model anchor + hash-derived prices/MPG), **craigslist** (US Census place names + BLS SOC titles), **wolfram_alpha** (curated constants + algorithmic factor/derivative batches).
