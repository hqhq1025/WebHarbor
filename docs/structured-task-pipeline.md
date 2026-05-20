# Structured task pipeline prototype

This is the local minimum viable path for moving WebHarbor tasks away from
ambiguous natural-language-only prompts and fixed-token answer checks.

## Why this exists

Older `sites/*/tasks.jsonl` rows contain only:

```json
{"web_name": "...", "id": "...", "ques": "...", "web": "...", "upstream_url": "..."}
```

That format is fine for LLM-as-judge smoke tests, but it cannot distinguish
these two cases reliably:

1. The task truly allows any matching entity: "open one matching hotel".
2. The evaluator expects one canonical entity: `Praktik Èssens`.

A hidden fixed-token check can therefore reject a reasonable trajectory that
opens another visibly matching result. The structured format makes the intended
target, DB-verifiable constraints, answer fields, and state changes explicit.

## Structured row shape

Generated rows keep the legacy keys for compatibility and add:

- `site` and `task_family`
- `start_url` and `instruction`
- `target_entity`: the DB-backed entity the task is asking about or mutating
- `constraints`: search/filter/sort/identity constraints that must hold
- `expected_answer`: exact fields or identity expected in the final answer
- `validation`: DB predicate, visible-page evidence fields, answer kind, optional uniqueness
- `actor` / `login`: only for authenticated state-mutation tasks
- `state_transition`: only for state-mutation tasks
- `stability`: fixture/date/session/randomness risk metadata
- `difficulty`

## Why 13 supported sites, not all 15?

WebHarbor has 15 mirrors in `websyn_start.sh`:

```text
allrecipes, amazon, apple, arxiv, bbc_news, booking, github,
google_flights, google_map, google_search, huggingface, wolfram_alpha,
cambridge_dictionary, coursera, espn
```

The structured generator currently supports **13/15** because it only emits tasks
when there is a real seeded DB oracle for the target entity. In this checkout,
fresh local seeding exposes:

- `bbc_news.Article.query.count() == 0`
- `google_search.SearchResult.query.count() == 0`

So adding BBC News or Google Search generators right now would create fake
coverage: the task could not be validated from a DB-backed entity. They should be
added once their article/search-result fixture data is present and stable. The
runtime helper already knows about all 15 sites; the supported list is kept
smaller on purpose to avoid non-oracle tasks.

## Supported families

For each supported site, the generator emits three DB-backed families:

1. **Detail lookup**: the task names a target entity and asks for visible fields.
2. **Identify by constraints**: the task hides the target name, gives stable target features as constraints, and expects the entity identity.
3. **State mutation**: the task logs in as a benchmark user, performs an operation such as save/cart/star/like/favorite/track, and validates DB before/after state.

Most state-mutation sites also expose a multi-entity variant. Multi-entity rows
keep the legacy `target_entity` for compatibility and add `target_entities` plus
an operation such as `cart_add_multiple_products` or `saved_places_add_multiple`.
Use `--item-count 2..4` and `--quantity-profile ones|mixed|increasing` to control
the combination size and quantities.

| Site | Detail family | Identify family | Mutation family | Oracle entity |
| --- | --- | --- | --- | --- |
| Allrecipes | `recipe_detail_lookup` | `recipe_identify_by_constraints` | `recipe_box_save` | `Recipe` |
| Amazon | `product_search_with_filters` | `product_identify_by_constraints` | `cart_add_product` | `Product` |
| Apple | `product_detail_lookup` | `product_identify_by_constraints` | `cart_add_product` | `Product` |
| arXiv | `paper_metadata_lookup` | `paper_identify_by_constraints` | `library_add_paper` | `Paper` |
| Booking | `hotel_search_with_amenity_filters` | `property_identify_by_constraints` | `saved_property_add` | `Property` |
| Cambridge Dictionary | `dictionary_entry_lookup` | `word_identify_by_constraints` | `saved_word_add` | `Word` |
| Coursera | `course_search_detail_lookup` | `course_identify_by_constraints` | `saved_course_add` | `Course` |
| ESPN | `team_standings_lookup` | `team_identify_by_constraints` | `favorite_team_add` | `Team` |
| GitHub | `repository_search_detail_lookup` | `repository_identify_by_constraints` | `repo_star_add` | `Repository` |
| Google Flights | `one_way_cheapest_flight` | `flight_identify_by_constraints` | `tracked_flight_add` | `Flight` |
| Google Maps | `place_search_detail_lookup` | `place_identify_by_constraints` | `saved_place_add` | `Place` |
| Hugging Face | `repository_search_detail_lookup` | `repository_identify_by_constraints` | `repo_like_add` | `Repository` |
| Wolfram Alpha | `topic_example_lookup` | `topic_identify_by_constraints` | `favorite_topic_add` | `Topic` |

Multi-entity state families currently include:

```text
allrecipes: recipe_box_save_multiple
amazon: cart_add_multiple_products
apple: bag_add_multiple_products
arxiv: library_add_multiple_papers
booking: bag_add_multiple_stays
cambridge_dictionary: saved_words_add_multiple
coursera: saved_courses_add_multiple
espn: favorite_teams_add_multiple
github: repo_star_add_multiple
google_flights: tracked_flights_add_multiple
google_map: saved_places_add_multiple
huggingface: repo_like_add_multiple
wolfram_alpha: favorite_topics_add_multiple
```

## How to generate

List supported sites:

```bash
.venv/bin/python scripts/generate_structured_tasks.py --list-sites
```

List families for a site:

```bash
.venv/bin/python scripts/generate_structured_tasks.py --site amazon --list-families
```

Example output:

```text
product_search_with_filters
product_identify_by_constraints
cart_add_product
```

Generate one task. `--limit` defaults to `1`, preserving the original
single-spec behavior:

```bash
.venv/bin/python scripts/generate_structured_tasks.py \
  --site amazon \
  --family product_identify_by_constraints \
  --output /tmp/amazon_identify.jsonl
```

Generate a deterministic batch from multiple DB entities:

```bash
.venv/bin/python scripts/generate_structured_tasks.py \
  --site amazon \
  --family product_identify_by_constraints \
  --limit 25 \
  --offset 0 \
  --output /tmp/amazon_identify_25.jsonl
```

`--limit` means "emit at most N tasks"; if fewer DB entities satisfy the
family's constraints, fewer rows are written. `--offset` is a stable candidate
offset for paging through the same deterministic ordering:

```bash
.venv/bin/python scripts/generate_structured_tasks.py \
  --site amazon \
  --family product_search_with_filters \
  --offset 25 \
  --limit 25 \
  --output /tmp/amazon_detail_page2.jsonl
```

Generate a multi-item state task batch:

```bash
.venv/bin/python scripts/generate_structured_tasks.py \
  --site amazon \
  --family cart_add_multiple_products \
  --item-count 2 \
  --quantity-profile mixed \
  --limit 20 \
  --output /tmp/amazon_multi_cart.jsonl
```

Validate a JSONL batch:

```bash
.venv/bin/python scripts/validate_structured_task.py \
  --spec /tmp/amazon_identify_25.jsonl
```

The validator reads every non-empty JSONL row. Any row failure returns non-zero
and reports the failing task id; success prints `validated N task(s)`.

Generate and validate every supported family in batches:

```bash
for site in $(.venv/bin/python scripts/generate_structured_tasks.py --list-sites); do
  for family in $(.venv/bin/python scripts/generate_structured_tasks.py --site "$site" --list-families); do
    out="/tmp/${site}.${family}.jsonl"
    .venv/bin/python scripts/generate_structured_tasks.py \
      --site "$site" \
      --family "$family" \
      --limit 3 \
      --output "$out"
    phase=spec
    case "$family" in
      recipe_box_save|cart_add_product|library_add_paper|saved_property_add|saved_word_add|saved_course_add|favorite_team_add|repo_star_add|tracked_flight_add|saved_place_add|repo_like_add|favorite_topic_add)
        phase=before
        ;;
    esac
    .venv/bin/python scripts/validate_structured_task.py --spec "$out" --phase "$phase"
  done
done
```

For read-only detail/identify tasks, `--phase before` is equivalent to normal
spec validation. For mutation tasks, it checks the pre-action state.

## Detail vs identify

Detail tasks are the old, forward direction:

```text
Given X, open X, answer X.field values.
```

Identify tasks are the true reverse direction:

```text
Pick hidden target X from DB.
Extract stable distinguishing features from X.
Ask the agent to find the entity with those features.
Expected answer = identity(X).
```

Identify prompts must not reveal the human-visible target name. The validator
checks that the hidden target entity still matches the DB fields, that the
constraint set uniquely identifies the target in the seeded DB, and that an
incorrect `expected_answer.identity` is rejected.

## Mutation families and login injection

Mutation specs add authenticated actor and state-transition metadata:

```json
{
  "actor": {"email": "alice.j@test.com", "password": "TestPass123!"},
  "login": {
    "required": true,
    "strategy": "ui_credentials",
    "login_url": "https://www.amazon.com/ap/signin",
    "post_login_assertion": "authenticated user session is active"
  },
  "state_transition": {
    "before": {"db_predicate": "amazon.cart_item_absent"},
    "after": {"db_predicate": "amazon.cart_item_quantity"}
  }
}
```

The generator chooses a benchmark user and a target that is absent from that
user's current state, so each task has a clean before state. Browser runners
should use `actor.email`, `actor.password`, and `login.login_url` through the
normal UI login flow. `login.login_url` is the real upstream website's login or
account sign-in URL, such as `https://www.amazon.com/ap/signin` or
`https://github.com/login`, not a localhost mirror URL. This is the
login-injection contract: credentials are not hard-coded into the runner; they
are carried by the structured task.

Validate before an agent run:

```bash
.venv/bin/python scripts/validate_structured_task.py \
  --spec /tmp/amazon_cart_add.jsonl \
  --phase before
```

Validate after an agent run by pointing the validator at the mutated runtime DB
state and using:

```bash
.venv/bin/python scripts/validate_structured_task.py \
  --spec /tmp/amazon_cart_add.jsonl \
  --phase after
```

In this local prototype, validator tests load a fresh DB for determinism, so
`--phase after` intentionally fails before any browser action has mutated the
runtime DB. The spec contract is already present: actor, login route, operation,
before predicate, and after predicate.

## Validation semantics

`must_appear` is useful as a page/final-answer evidence check, but it is not the
primary oracle. The DB predicate decides whether the target entity or state
transition satisfies the task.

- Detail tasks validate target fields.
- Identify tasks validate target fields plus `expected_answer.identity`.
- Mutation tasks validate `before` and `after` state predicates.

Keep LLM-as-judge as a secondary trajectory-quality check, not the source of
truth for entity identity or state mutation.

## Current implementation

- `scripts/generate_structured_tasks.py`
  - `--list-sites`
  - `--site <site> --list-families`
  - `--site <site> --family <family> --limit <n> --offset <n> --output <jsonl>`
- `scripts/validate_structured_task.py`
  - validates one JSON spec or every row in a JSONL batch against seeded SQLite
    DB predicates
  - supports `--phase spec|before|after`
- `scripts/structured_task_runtime.py`
  - loads each site app from a temporary copy, calls real seed functions, and
    avoids mutating `sites/<site>/instance/`
- Tests:
  - `tests/test_task_spec_pipeline.py`
  - `tests/test_reverse_generators_all_sites.py`
  - `tests/test_reverse_identify_families.py`
  - `tests/test_mutation_generators.py`
  - `tests/test_structured_task_batch_generation.py`

## Next extensions

1. Add BBC News and Google Search once their fresh seeded `Article` /
   `SearchResult` rows are present.
2. Add more families per entity: top-k, compare, count, form validation,
   negative constraints, multi-hop tasks.
3. Add optional HTML/screenshot visible-text checks after a run, using
   `validation.visible_evidence_fields`.
4. Teach dashboard/review tooling to display structured fields alongside legacy
   `ques`.
5. Add runtime DB selection for post-agent mutation validation, e.g. `--db-path`
   or control-plane instance lookup.
