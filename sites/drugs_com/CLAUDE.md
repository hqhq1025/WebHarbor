# drugs_com — WebHarbor mirror site

Flask mirror of drugs.com at port **40015**. Covers pharmaceutical drug information: lookup, interaction checking, pill identification, conditions, news, and user accounts.

## Quick start

```bash
# Build and run (from repo root)
./scripts/build.sh webharbor:dev
docker run -d --rm --name wh-test -p 8209:8101 -p 49015:40015 webharbor:dev

# Verify
curl -s http://localhost:8209/health | python3 -m json.tool   # control plane
curl -so /dev/null -w "%{http_code}" http://localhost:49015/   # should print 200

# Logs
docker logs wh-test --tail 50
docker exec wh-test cat /tmp/websyn_drugs_com.log

# Reset to seed state (byte-identical)
curl -X POST http://localhost:8209/reset/drugs_com
docker exec wh-test md5sum \
  /opt/WebSyn/drugs_com/instance/drugs_com.db \
  /opt/WebSyn/drugs_com/instance_seed/drugs_com.db
# Both hashes must match: f4c0012b93fba43b91f551d65d254dfd
```

## Architecture

### Models (`app.py`)

| Model | Key fields |
|-------|-----------|
| `Drug` | `slug`, `generic_name`, `brand_names`, `drug_class_id`, `availability` (Rx/OTC), `csa_schedule`, `pregnancy_risk`, `rating`, `review_count` |
| `DrugClass` | `name`, `slug`, `description` |
| `DrugImage` | `drug_id`, `imprint`, `shape`, `color`, `dosage_form` |
| `DrugInteraction` | `drug_a_id`, `drug_b_id`, `severity` (major/moderate/minor), `description` |
| `DrugReview` | `drug_id`, `user_id`, `rating` (1–10), `title`, `body` |
| `Condition` | `name`, `slug`, `description` |
| `NewsArticle` | `title`, `category`, `body`, `published_at` |
| `SavedDrug` | `user_id`, `drug_id` (My Med List) |
| `User` | `email`, `username`, `password_hash` |

### Key routes

| URL pattern | Template | Notes |
|-------------|----------|-------|
| `/` | `index.html` | Homepage with featured drugs and news |
| `/<slug>.html` | `drug_detail.html` | Drug detail (canonical) |
| `/drug_information.html` | `drug_az.html` | A-Z index |
| `/drug-interactions` | `interaction_checker.html` | Interaction checker (canonical) |
| `/pill-identifier` | `pill_identifier.html` | Pill identifier (canonical) |
| `/drug-classes/` | `drug_classes.html` | Drug class browser |
| `/drug-classes/<slug>/` | `drug_class.html` | Single drug class |
| `/conditions/` | `conditions.html` | Conditions A-Z |
| `/condition/<slug>/` | `condition.html` | Single condition |
| `/news/` | `news.html` | News index with category filter |
| `/search` | `search.html` | Drug/class/condition search |
| `/my-med-list` | `my_med_list.html` | Saved drugs (auth required) |

Flask uses the **last** `@app.route` decorator as the canonical URL for `url_for()`. Alias routes are placed first.

`app.url_map.strict_slashes = False` — all routes accept trailing-slash variants.

### Pill images

Rendered as inline SVGs via the `_pill_svg.html` macro — no external image files needed for the benchmark. Real pill photos live at `static/images/pills/<slug>.jpg` (HuggingFace asset); a `pill_image_exists` Jinja filter falls back to the SVG macro when the file is absent.

## Seed database

- **Location**: `instance_seed/drugs_com.db` (gitignored — sourced from HuggingFace)
- **MD5**: `f4c0012b93fba43b91f551d65d254dfd`
- **Contents**: 1050 drugs · 892 reviews · 685 interactions · 103 pill images · 205 conditions · 80 news articles · 12 users · 102 glossary terms · 10 forum categories · 51 forum topics · 153 forum posts · 30 health-news articles · 25 drug recalls · 20 pharmacies · 5 refill reminders · 15 side-effect reports

All `seed_*()` functions gate on an already-populated DB (early-return if rows exist) so `seed_database()` is idempotent and the reset invariant holds.

## Benchmark users

| Username | Email | Password | Notes |
|----------|-------|----------|-------|
| alice_j | alice.j@test.com | TestPass123! | Primary test user |
| bob_c | bob.c@test.com | TestPass123! | Secondary |
| carol_d | carol.d@test.com | TestPass123! | Secondary |
| david_k | david.k@test.com | TestPass123! | Secondary |

**Alice's seeded state** (task-critical — do not change):
- Med list: ibuprofen, metformin, atorvastatin (NOT lisinopril — task 14 asks to add it)
- Reviews: ibuprofen 9/10, lisinopril 7/10, hydrochlorothiazide 10/10

## Benchmark tasks

2298 tasks in `tasks.jsonl`: 21 original `Drugs.com--<N>` tasks plus 2277
deepening tasks with ids of the form `Drugs--gui_<page>_<NNN>`. Surfaces
covered: drug detail / pregnancy / breastfeeding / dosage / side-effects /
warnings / interactions / FAQ / reviews / monograph / images / price guide,
condition detail + condition-drugs, drug-class browse, glossary, forum
(browse + topic + reply + delete), refill reminders (CRUD), drug recalls,
pharmacy finder, health news, dosage calculator, drug comparison, multi-step
pill identifier wizard, search + autocomplete, and authenticated flows
(myaccount hub / medications / refill reminder / review / forum post /
contact pharmacist / report side effect / save comparison).

## Deepening module

`_deepen_routes.py` registers 12 new model classes and ~40 new routes
(22 of them POST) on top of the base app. `_deepen.py` holds all literal
seed data (glossary terms, forum topics, health news, recalls, pharmacies,
side-effect reports, refill reminder presets).

`seed_deepening()` is idempotent: each table is gated on `count() == 0`.
The post-seed `normalize_seed_db_layout()` pass runs **only** when at least
one row was added this boot — calling it on a stable DB would repaginate
via VACUUM and break the byte-id reset invariant.

## HuggingFace assets

Assets are packaged as `drugs_com.tar.gz` in the `ChilleD/WebHarbor` dataset (PR #13).

To repack and upload:
```bash
# From repo root
./scripts/extract_assets.sh /tmp/wh-assets drugs_com
hf upload ChilleD/WebHarbor /tmp/wh-assets/drugs_com.tar.gz drugs_com.tar.gz \
  --repo-type dataset --create-pr
```

To pull assets locally before building:
```bash
./scripts/fetch_assets.sh drugs_com
```
