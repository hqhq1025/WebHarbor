---
name: design-tasks
description: "Phase 2: Design 15-20 benchmark tasks for a WebHarbor mirror site and write them into sites/<site>/tasks.jsonl (one JSON object per line, WebVoyager-compatible schema). Tasks must cover the site's full functional breadth (search, browse, cart, checkout, account management, etc.) and include tasks that frontier models cannot easily solve. Use after clone-website to define what the environment must support."
---

# Design Tasks — Benchmark Task Construction

## When to use

- After Phase 1 (clone-website) to define the task set
- When enriching an existing site with new tasks
- When adapting tasks from WebVoyager / Online-Mind2Web to a mirror

## Output format: `sites/<site>/tasks.jsonl`

WebHarbor uses the WebVoyager schema, one JSON object per line:

```jsonl
{"web_name": "Amazon", "id": "Amazon--0", "ques": "Search an Xbox Wireless controller with green color and rated above 4 stars.", "web": "http://localhost:40001/", "upstream_url": "https://www.amazon.com/"}
{"web_name": "Amazon", "id": "Amazon--1", "ques": "Search for women's golf polos in M size, priced between 50 to 75 dollars, and save the lowest-priced result.", "web": "http://localhost:40001/", "upstream_url": "https://www.amazon.com/"}
```

Required fields:
- `web_name` — display name of the site (PascalCase, e.g. `"Amazon"`, `"BBC News"`)
- `id` — unique task ID, format `<web_name>--<index>`
- `ques` — the natural-language task instruction the agent will see
- `web` — local mirror URL, `http://localhost:<port>/`
- `upstream_url` — the real-site URL the mirror clones (for reference)

## Design principles

### 1. Functional breadth

Tasks must cover the site's FULL feature surface, not just one flow. Example for an Amazon-like site:

| Category | Example task |
|---|---|
| Search & filter | "Find a wireless mouse under $30 with 4+ stars" |
| Product detail | "What is the battery life of the Sony WH-1000XM5?" |
| Cart & checkout | "Add the cheapest USB-C hub to your cart and proceed to checkout" |
| Account | "Change the shipping address to 123 Main St, Denver, CO" |
| Order history | "Find the tracking number for your most recent order" |
| Payment | "Add a new Visa card ending in 4242" |
| Reviews | "How many 1-star reviews does the Kindle Paperwhite have?" |
| Comparison | "Which laptop has more RAM: MacBook Air or ThinkPad X1?" |

Aim for ≥3 distinct functional areas with 4-6 tasks each.

### 2. Difficulty spectrum

- **Easy** (2-3 steps): "Find the customer service phone number"
- **Medium** (4-6 steps): "Search for hiking boots, filter by size 10, find one under $100"
- **Hard** (7+ steps): "Compare 3 laptops by price, RAM, and battery life, then add the best value to cart"
- **Frontier-challenging**: multi-step reasoning, visual comparison, disambiguation

At least 3-5 tasks should require ≥5 steps.

### 3. Disambiguation tasks

Tasks where the user has multiple items and the agent must ask for clarification:

**Good** (forces clarification):
- "Cancel my recent order" (user has 2+ orders)
- "Remove a saved recipe" (user has 5 recipes — which one?)
- "Complete checkout" (user has 2+ payment cards)
- "Export my papers" (multiple formats: BibTeX, EndNote, RIS)

**Bad** (agent can guess):
- "Add a recipe to Recipe Box" (any item works)
- "Buy headphones" (any model works)

### 4. Ground truth

The expected answer must be verifiable against the DB. WebHarbor's grounded
truth checks live in the evaluation harness, not in `tasks.jsonl`. The
mirror DB must contain a single unambiguous answer for each task (modulo
disambiguation tasks).

## Task sources

### Adapt from existing benchmarks
If the site appears in WebVoyager or Online-Mind2Web, copy those tasks
verbatim into `tasks.jsonl` and verify they work against your mirror.

### LLM-generated
Prompt an LLM:

```
Design 20 benchmark tasks for a local mirror of {website}. The mirror supports
{list routes and capabilities}. Use this format (one JSON object per line):

{"web_name": "<Name>", "id": "<Name>--<i>", "ques": "<task>", "web": "http://localhost:<port>/", "upstream_url": "<real_url>"}

Tasks must:
1. Cover ≥5 distinct functional areas
2. Range from 2-step (easy) to 7+ step (hard)
3. Include 3+ multi-step reasoning tasks
4. Have specific, verifiable answers
5. Include 2+ disambiguation tasks
```

### Manual design
Browse the real site and design tasks based on real user workflows.

## Verification

For each task in `tasks.jsonl`, hand-walk it through the mirror to confirm:
- The natural search query for the task returns at least 6 results
- The correct answer exists in the DB
- The answer is NOT visible at the search-result level (must require detail page)
- For disambiguation tasks, the user has ≥2 ambiguous items

---

## Lessons learned — task authoring (added after IMDb contribution 2026-05-26)

The first draft of any tasks.jsonl will almost certainly violate the design
principles above. Don't ship it. The IMDb run produced a 12-task draft that
failed three of the four design principles (0 disambiguation, 0 hard tasks,
no hand-walk verification) — only realized in code review. The patterns below
are the ones that actually trip people up.

### Pattern 1: First draft is always too easy and too uniform

If you sit down to write 18 tasks based on the route list, you will end up
with ~16 medium tasks and zero disambiguation. The fix is to **design by
functional area + difficulty quota first, write task text second**:

```
6 functional areas × 3 tasks each = 18 tasks
of those 18: at least 3-5 require ≥5 steps (hard)
of those 18: at least 2 are disambiguation
```

Lay out a 6×3 grid before writing any prose. For each cell, ask
"what would actually require 5+ steps here?" — if you can't think of one,
the area might not need 3 tasks.

### Pattern 2: Designing disambiguation requires pre-seeded ambiguity

You cannot tack "ask the user for clarification" onto an arbitrary task.
Disambiguation requires the DB to have ≥2 candidates that *equally* satisfy
the request. That means **the seed-data step decides what disambiguation
tasks are possible**.

Plan ahead at seed time:
- benchmark user A has 4+ items in their watchlist, of which ≥2 are TV shows
  → task: "remove a TV show from A's watchlist" (must ask which one)
- benchmark user B has 3+ ratings on crime films
  → task: "update B's rating on one of their crime films"
- there are ≥2 movies by the same director
  → task: "open the X director's movie that's about Y" where multiple match

If your seed data has exactly 1 candidate everywhere, you have zero
disambiguation budget no matter how cleverly you phrase the question.

### Pattern 3: Hard tasks come from forcing cross-page navigation

The skill says "≥3-5 tasks ≥5 steps" but doesn't say how to get there. The
trick is to require information that lives on **separate detail pages**:

| Pattern | Steps |
|---|---|
| Person filmography → click each film → compare ratings | 6-8 (one click per film) |
| Cross-title compare ("which has higher gross, A or B?") | 4-6 (2× navigate + read + compare) |
| Login → search → filter → click → mutate (cart/review) | 5-7 |
| Browse top-of-list → open detail → read field hidden on list | 3-4 (easy edge) |
| Use advanced filter → click top result → cross-reference person page | 6-8 |

Pure "navigate to X and report field" is at most 3 steps. To get to ≥5
without inventing pointless steps, make the agent **integrate information
across at least two pages**.

### Pattern 4: Credentials in task text — explicit policy

WebVoyager-style benchmark tasks generally do NOT include credentials in the
`ques` field. WebHarbor's auth-gated tasks are the exception because the
mirror's benchmark users are fixed and public.

**Allowed (WebHarbor convention)**:
```
"Sign in as alice.j@test.com (password TestPass123!), open the watchlist..."
```

**Not allowed (looks like real credentials, smells synthetic)**:
- generated tokens, API keys, OAuth flows
- "use the credentials in your environment"

The reason WebHarbor inlines the test password is that the four benchmark
users (alice.j / bob.c / carol.d / david.k @ test.com) are part of the
mirror's contract — any agent reading the README knows them. Skipping them
would force every auth task to first navigate to README.

### Pattern 5: "Answer not at list level" is the most-broken rule

Easy to violate without noticing. The chart pages render rating column —
so "what's the rating of the #1 movie?" technically leaks the answer at
list level. Whether this counts depends on **list semantics**:

- **Curated chart pages (Top 250, Box Office, Most Popular)**: intentional
  surfacing. Rating IS the chart's purpose. Allowed to leak.
- **Search results pages (`/search?q=`, `/find?q=`)**: the agent typed a
  query; the answer in the result snippet IS a leak. Must require detail
  page click.
- **Genre browse pages**: in between. If the task is "find the highest-rated
  X-genre title", list-level rating is fine; if the task is "find the
  director of the highest-rated X-genre title", director must be on detail.

Write each task with the list-vs-detail boundary in mind: name the specific
field the answer comes from, then check that that field is only on detail.

### Pattern 6: "Search returns ≥6 results" needs the right query

The skill says natural-language search query must return ≥6 results. Stop
words (the, a, an, of, in, with, ...) get filtered by scored-search and
will return 0 — your query needs non-stop-word tokens that actually appear
in the catalog.

When validating with curl/Playwright: use multi-word queries that include
at least one rare token. `q=the` returns 0 in IMDb; `q=lord rings` returns 5;
`q=man` returns 50.

### Pattern 7: The verification script template

Don't hand-walk 18 tasks individually — write a verification script once,
re-run it after every seed change. The IMDb run learned this the hard way
when a Person redirect bug invalidated half the test cases.

Minimum verifier (curl-based, ~80 lines) checks per task:
- the target detail page returns 200 and contains the expected answer text
- for disambiguation tasks: the relevant user's watchlist has ≥2 candidates
- for write-mutation tasks: POST returns 302 and the new content appears

Then a smaller Playwright handwalk (~50 lines for 3 tasks) covers the
JS/form interactions that curl can't validate:
- login flow with form-scoped selectors (see evolve-env Pattern 1)
- form submission via real button click (not direct POST)
- POST → redirect → confirm rendered DOM updated

Together that's ~130 lines of test code per site — write it once and re-run
it after every seed change.

### Pattern 8: Re-verify after every seed change

Any data-quality fix in `seed_data.py` (canonical-URL guard, garbage
filter, new normalizer) can move titles in and out of the DB. Watchlists
referencing dropped titles silently shrink, breaking disambiguation
guarantees. After any seed regeneration:

1. re-run the verifier above
2. specifically check the disambiguation tasks still have ≥2 candidates
3. re-byte-identical check the seed DB md5

### Pattern 9: Task-text禁词 (carried over from feedback memory)

In `ques` text, the following phrasings smell synthetic and should be
rewritten as natural language:

- `visible fields`, `if shown`, `record`, `control`, `probe`, `label`,
  `details` — engineering vocabulary
- "X 或 Y" alternation that exposes generator enumeration
- `after seeded 2026-04-30 mirror snapshot` — internal phrasing
- Asking for fields that aren't visible on the page (inspect-element only)

Real user queries: "How long is The Shawshank Redemption?" not
"Report the runtime field visible on the title detail page."

### Pattern 10: State-mutation tasks need DB-diff verification before training

Any task that POSTs (add to watchlist, write review, submit rating)
produces state changes. For benchmark *evaluation*, the verifier can
re-fetch the page and grep. For benchmark *training* (where success is
judged by DB diff), state-mutation tasks must be marked `holdout` until a
DB-diff verifier confirms the expected row appeared in the right table.
See feedback-task-authoring-style memory for the full taxonomy.

## Next step

Proceed to **evolve-env** (Phase 3) to evolve the environment to support all tasks.

---

## WebVoyager GUI 任务的硬性边界 (added 2026-05-27)

Frontier agents drive a real browser. **No URL bar typing, no JSON parsing, no curl.** Tasks routing around the visual GUI are unsolvable.

### Hard-banned phrasings (regex-checked)

| Pattern | Banned because |
|---|---|
| `GET /` `POST /` mid-sentence | implies URL-bar / curl |
| `/api/`, `/graphql`, `/openapi`, `/jsonld`, `/webhook` | machine endpoints |
| `/healthz`, `/sitemap`, `/robots.txt`, `/.well-known` | SEO/ops chrome |
| `?format=json`, `.json`, `.xml` in URL | non-HTML response |
| "parse the JSON", "parse the XML", "in JSON format" | agent doesn't read JSON |
| "fetch the endpoint" / "curl" | requires shell |

Single-pass regex strip on tasks.jsonl (see `harden-env/gotchas.md` §24 for canonical regex).

### Hard cap: ≤5 tasks per 5-token prefix

```python
from collections import Counter
seen = Counter()
kept = []
for t in rows:
    key = " ".join(re.findall(r"\w+", t["ques"].lower())[:5])
    if seen[key] >= 5: continue
    seen[key] += 1
    kept.append(t)
```

For diversity, vary 2+ dimensions per row (entity + operation + question, not just slug substitution).

### GUI vs API examples

| ❌ banned | ✅ rewrite |
|---|---|
| `"On /api/v1/properties/search?city=berlin, parse the JSON 'count'."` | `"In Berlin, find hotels with at least 7.0 rating; how many results show up?"` |
| `"GET /scholar/results?q=Attention and report the first author."` | `"Search Google Scholar for 'Attention Is All You Need' and report the first listed author."` |
| `"Fetch the BBC RSS feed for tech and parse pubDate."` | `"On BBC Tech, what's the publication date of the top story?"` |

### Multi-step distribution

- ≥50 tasks at 2-3 steps
- ≥30 tasks at 4-6 steps
- ≥10 tasks at 7+ steps
- multi-step % per site: 25-50%

### Disambiguation density

≥2 disambig per surface, ≥15 per site total. Detect:

```bash
grep -E "which one|multiple|several|two of|both [A-Z]|each of the" sites/<site>/tasks.jsonl | wc -l
```

### Pre-merge audit thresholds

| Metric | Threshold |
|---|---|
| uniq-ques% | ≥ 90 |
| 5tok-prefix-dup% | ≤ 50 |
| multistep% | ≥ 25 |
| disambig-count | ≥ 15 |
| api-task-count | = 0 |
