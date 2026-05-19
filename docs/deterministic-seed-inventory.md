# Deterministic Seed Inventory

## Policy proposal

WebHarbor seed generation should be reproducible by default. Any value that can affect benchmark answers should come from one of these deterministic sources:

- literal fixture data,
- a stable hash helper based on `hashlib`, or
- a local `random.Random(seed)` instance derived from an explicit site/profile seed.

Avoid these in seed-time code:

- bare global `random.*` without a site/profile seed,
- Python `hash(...)`, because it is randomized per process,
- `datetime.utcnow()` / `date.today()` for fixture timestamps unless anchored to a mirror reference date,
- SQL `func.random()` for pages used by benchmark tasks.

Runtime security/session operations may still use `secrets.*`; runtime user actions may use wall-clock time when the action is genuinely user initiated. The migration priority is seed-time answer-affecting data first.

## Recommended migration order

1. **High priority**: Booking, Google Flights, Google Search, Google Map. These generate prices, ratings, amenities, locations, result counts, or answer-bearing fields.
2. **Medium priority**: Amazon, arXiv, Coursera, BBC News. They contain seeded user histories, randomized counts, or randomized display ordering that can affect trajectories.
3. **Lower priority**: Apple, GitHub, WolframAlpha, Cambridge Dictionary, Hugging Face. Mostly user action IDs, display helpers, or already-stable small random uses.

## How to use this file

Run `python3 scripts/audit_seed_randomness.py > docs/deterministic-seed-inventory.md` after changing seed code. Review the summary first, then inspect detailed findings for `stage=seed-time` and `kind=python_hash`.

# Seed Randomness Audit

## Summary by Site

| Site | random | hash | SQL random | utcnow | today | secrets | seed-time | runtime-display | time-dependent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| allrecipes | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| amazon | 10 | 1 | 10 | 4 | 0 | 0 | 9 | 0 | 3 |
| apple | 0 | 0 | 0 | 4 | 0 | 3 | 3 | 0 | 2 |
| arxiv | 12 | 0 | 1 | 15 | 0 | 0 | 28 | 0 | 0 |
| bbc_news | 3 | 0 | 3 | 6 | 0 | 0 | 11 | 0 | 1 |
| booking | 24 | 0 | 0 | 11 | 35 | 1 | 61 | 0 | 9 |
| cambridge_dictionary | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| coursera | 8 | 0 | 0 | 4 | 0 | 0 | 12 | 0 | 0 |
| espn | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
| github | 0 | 3 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| google_flights | 61 | 1 | 0 | 6 | 1 | 0 | 61 | 0 | 4 |
| google_map | 34 | 0 | 0 | 4 | 0 | 0 | 34 | 0 | 3 |
| google_search | 20 | 3 | 3 | 5 | 0 | 1 | 23 | 3 | 4 |
| huggingface | 6 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| wolfram_alpha | 0 | 0 | 0 | 5 | 0 | 1 | 5 | 0 | 0 |

## Detailed Findings

| File | Line | Kind | Stage | Code |
| --- | ---: | --- | --- | --- |
| `sites/allrecipes/app.py` | 950 | random_call | runtime-or-unknown | `rng_pad = random.Random(seed + 1)` |
| `sites/allrecipes/app.py` | 959 | random_call | runtime-or-unknown | `random.Random(seed + 11).shuffle(tier_strong)` |
| `sites/allrecipes/app.py` | 960 | random_call | runtime-or-unknown | `random.Random(seed + 12).shuffle(tier_partial)` |
| `sites/allrecipes/app.py` | 961 | random_call | runtime-or-unknown | `random.Random(seed + 13).shuffle(tier_decoy)` |
| `sites/amazon/app.py` | 383 | sql_random | runtime-or-unknown | `featured = Product.query.filter_by(is_featured=True).order_by(_func.random()).limit(12).all()` |
| `sites/amazon/app.py` | 384 | sql_random | runtime-or-unknown | `deals = Product.query.filter_by(is_deal=True).order_by(_func.random()).limit(8).all()` |
| `sites/amazon/app.py` | 385 | sql_random | runtime-or-unknown | `bestsellers = Product.query.filter_by(is_bestseller=True).order_by(_func.random()).limit(12).all()` |
| `sites/amazon/app.py` | 386 | sql_random | runtime-or-unknown | `electronics = Product.query.filter_by(category_slug='electronics').order_by(_func.random()).limit(6).all()` |
| `sites/amazon/app.py` | 387 | sql_random | runtime-or-unknown | `fashion = Product.query.filter_by(category_slug='fashion').order_by(_func.random()).limit(6).all()` |
| `sites/amazon/app.py` | 388 | sql_random | runtime-or-unknown | `home_goods = Product.query.filter_by(category_slug='home').order_by(_func.random()).limit(6).all()` |
| `sites/amazon/app.py` | 389 | sql_random | runtime-or-unknown | `books = Product.query.filter_by(category_slug='books').order_by(_func.random()).limit(6).all()` |
| `sites/amazon/app.py` | 390 | sql_random | runtime-or-unknown | `computers = Product.query.filter_by(category_slug='computers').order_by(_func.random()).limit(6).all()` |
| `sites/amazon/app.py` | 395 | sql_random | runtime-or-unknown | `.order_by(_func.random()).limit(4).all())` |
| `sites/amazon/app.py` | 401 | sql_random | runtime-or-unknown | `extra = q.order_by(_func.random()).limit(4 - len(beauty)).all()` |
| `sites/amazon/app.py` | 683 | python_hash | runtime-or-unknown | `query_seed = abs(hash(q.lower())) % (2**31)` |
| `sites/amazon/app.py` | 684 | random_call | runtime-or-unknown | `rng = random.Random(query_seed)` |
| `sites/amazon/app.py` | 1226 | random_call | runtime-or-unknown | `order_num = f"112-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"` |
| `sites/amazon/app.py` | 1242 | random_call | time-dependent | `delivery_estimate=(datetime.utcnow() + timedelta(days=random.randint(2, 5))).strftime('%A, %B %d')` |
| `sites/amazon/app.py` | 1242 | utcnow | time-dependent | `delivery_estimate=(datetime.utcnow() + timedelta(days=random.randint(2, 5))).strftime('%A, %B %d')` |
| `sites/amazon/app.py` | 1338 | utcnow | time-dependent | `if order.created_at and (datetime.utcnow() - order.created_at).days > 30:` |
| `sites/amazon/app.py` | 1579 | random_call | seed-time | `order_num = f"112-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"` |
| `sites/amazon/app.py` | 1596 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=days_ago),` |
| `sites/amazon/app.py` | 1597 | random_call | seed-time | `delivery_estimate=(datetime.utcnow() + timedelta(days=random.randint(2, 5))).strftime('%A, %B %d'),` |
| `sites/amazon/app.py` | 1597 | utcnow | seed-time | `delivery_estimate=(datetime.utcnow() + timedelta(days=random.randint(2, 5))).strftime('%A, %B %d'),` |
| `sites/amazon/seed_data.py` | 1189 | random_call | seed-time | `random.shuffle(unique)` |
| `sites/amazon/seed_data.py` | 1207 | random_call | seed-time | `random.seed(42)` |
| `sites/amazon/seed_data.py` | 1235 | random_call | seed-time | `gallery = pick_gallery_from_sources(sources, random.randint(8, 15),` |
| `sites/amazon/seed_data.py` | 1259 | random_call | seed-time | `stock=random.randint(20, 500),` |
| `sites/amazon/seed_data.py` | 1287 | random_call | seed-time | `rating, title, body = random.choice(sample_reviews)` |
| `sites/apple/app.py` | 27 | secrets | security/runtime | `app.config['SECRET_KEY'] = secrets.token_hex(32)` |
| `sites/apple/app.py` | 786 | utcnow | time-dependent | `order.updated_at = datetime.utcnow()` |
| `sites/apple/app.py` | 1108 | secrets | security/runtime | `order_number=f"W{secrets.token_hex(5).upper()}",` |
| `sites/apple/app.py` | 1461 | utcnow | time-dependent | `today = datetime.utcnow().date()` |
| `sites/apple/app.py` | 2260 | secrets | seed-time | `order_number=f"APL-{secrets.token_hex(4).upper()}",` |
| `sites/apple/app.py` | 2266 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=days_ago),` |
| `sites/apple/app.py` | 2267 | utcnow | seed-time | `updated_at=datetime.utcnow() - timedelta(days=days_ago),` |
| `sites/arxiv/app.py` | 626 | random_call | seed-time | `view_count=random.randint(50, 5000),` |
| `sites/arxiv/app.py` | 627 | random_call | seed-time | `download_count=random.randint(20, 2000),` |
| `sites/arxiv/app.py` | 628 | random_call | seed-time | `star_count=random.randint(0, 200),` |
| `sites/arxiv/app.py` | 684 | utcnow | seed-time | `current_year=datetime.utcnow().year,` |
| `sites/arxiv/app.py` | 713 | random_call | seed-time | `return "EX" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))` |
| `sites/arxiv/app.py` | 713 | utcnow | seed-time | `return "EX" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))` |
| `sites/arxiv/app.py` | 1113 | sql_random | seed-time | `.order_by(func.random()).limit(6).all())` |
| `sites/arxiv/app.py` | 2179 | random_call | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))))` |
| `sites/arxiv/app.py` | 2179 | utcnow | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))))` |
| `sites/arxiv/app.py` | 2186 | random_call | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))))` |
| `sites/arxiv/app.py` | 2186 | utcnow | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))))` |
| `sites/arxiv/app.py` | 2203 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=5),` |
| `sites/arxiv/app.py` | 2239 | random_call | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 45))))` |
| `sites/arxiv/app.py` | 2239 | utcnow | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 45))))` |
| `sites/arxiv/app.py` | 2246 | random_call | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))))` |
| `sites/arxiv/app.py` | 2246 | utcnow | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))))` |
| `sites/arxiv/app.py` | 2263 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=10),` |
| `sites/arxiv/app.py` | 2300 | random_call | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))))` |
| `sites/arxiv/app.py` | 2300 | utcnow | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))))` |
| `sites/arxiv/app.py` | 2307 | random_call | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 25))))` |
| `sites/arxiv/app.py` | 2307 | utcnow | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 25))))` |
| `sites/arxiv/app.py` | 2328 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=15),` |
| `sites/arxiv/app.py` | 2343 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=3),` |
| `sites/arxiv/app.py` | 2378 | random_call | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))))` |
| `sites/arxiv/app.py` | 2378 | utcnow | seed-time | `added_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))))` |
| `sites/arxiv/app.py` | 2385 | random_call | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 10))))` |
| `sites/arxiv/app.py` | 2385 | utcnow | seed-time | `starred_at=datetime.utcnow() - timedelta(days=random.randint(1, 10))))` |
| `sites/arxiv/app.py` | 2401 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=7),` |
| `sites/bbc_news/app.py` | 185 | utcnow | time-dependent | `now = datetime.utcnow()` |
| `sites/bbc_news/app.py` | 396 | utcnow | seed-time | `now = datetime.utcnow()` |
| `sites/bbc_news/app.py` | 431 | random_call | seed-time | `published = now - timedelta(hours=random.randint(1, 72), minutes=random.randint(0, 59))` |
| `sites/bbc_news/app.py` | 448 | random_call | seed-time | `view_count=random.randint(500, 50000),` |
| `sites/bbc_news/app.py` | 846 | utcnow | seed-time | `now = datetime.utcnow()` |
| `sites/bbc_news/app.py` | 898 | random_call | seed-time | `return "D" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))` |
| `sites/bbc_news/app.py` | 898 | utcnow | seed-time | `return "D" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))` |
| `sites/bbc_news/app.py` | 914 | sql_random | seed-time | `must_read = Article.query.order_by(func.random()).limit(5).all()` |
| `sites/bbc_news/app.py` | 1042 | utcnow | seed-time | `existing.viewed_at = datetime.utcnow()` |
| `sites/bbc_news/app.py` | 1050 | sql_random | seed-time | `).order_by(func.random()).limit(6).all())` |
| `sites/bbc_news/app.py` | 1053 | sql_random | seed-time | `.order_by(func.random()).limit(4).all())` |
| `sites/bbc_news/app.py` | 1161 | utcnow | seed-time | `cutoff = datetime.utcnow() - timedelta(days=since_days)` |
| `sites/booking/app.py` | 669 | today | time-dependent | `tomorrow = date.today() + timedelta(days=1)` |
| `sites/booking/app.py` | 670 | today | time-dependent | `day_after = date.today() + timedelta(days=3)` |
| `sites/booking/app.py` | 1410 | today | time-dependent | `check_in = data.get('check_in') or (date.today() + timedelta(days=1)).isoformat()` |
| `sites/booking/app.py` | 1411 | today | time-dependent | `check_out = data.get('check_out') or (date.today() + timedelta(days=3)).isoformat()` |
| `sites/booking/app.py` | 1416 | today | time-dependent | `ci = date.today() + timedelta(days=1)` |
| `sites/booking/app.py` | 1417 | today | time-dependent | `co = date.today() + timedelta(days=3)` |
| `sites/booking/app.py` | 1504 | today | time-dependent | `ci = date.today() + timedelta(days=1)` |
| `sites/booking/app.py` | 1508 | today | time-dependent | `co = date.today() + timedelta(days=3)` |
| `sites/booking/app.py` | 1718 | secrets | security/runtime | `booking_number = 'BKN-' + secrets.token_hex(5).upper()` |
| `sites/booking/app.py` | 1800 | today | time-dependent | `new_ci = date.today() + timedelta(days=14)` |
| `sites/booking/app.py` | 2154 | random_call | seed-time | `random.seed(20260518)` |
| `sites/booking/app.py` | 2250 | random_call | seed-time | `stars = h.get('stars', random.randint(3, 5))` |
| `sites/booking/app.py` | 2270 | random_call | seed-time | `price = round(base_price * city_multiplier * random.uniform(0.85, 1.25), 0)` |
| `sites/booking/app.py` | 2273 | random_call | seed-time | `rating = round(random.uniform(7.8, 9.6), 1)` |
| `sites/booking/app.py` | 2276 | random_call | seed-time | `amenities = random.sample(AMENITIES, random.randint(8, 14))` |
| `sites/booking/app.py` | 2284 | random_call | seed-time | `random.shuffle(city_gallery)` |
| `sites/booking/app.py` | 2285 | random_call | seed-time | `prop_gallery = city_gallery[:random.randint(8, 14)]` |
| `sites/booking/app.py` | 2303 | random_call | seed-time | `dest_cat = random.choice(dest_cat_slugs)` |
| `sites/booking/app.py` | 2313 | random_call | seed-time | `if random.random() < 0.35:` |
| `sites/booking/app.py` | 2314 | random_call | seed-time | `discount_pct = random.choice([10, 15, 20, 25, 30])` |
| `sites/booking/app.py` | 2315 | random_call | seed-time | `if random.random() < 0.4:` |
| `sites/booking/app.py` | 2318 | random_call | seed-time | `is_featured = random.random() < 0.4` |
| `sites/booking/app.py` | 2366 | random_call | seed-time | `review_count=random.randint(120, 3400),` |
| `sites/booking/app.py` | 2374 | random_call | seed-time | `free_cancellation=random.random() > 0.2,` |
| `sites/booking/app.py` | 2375 | random_call | seed-time | `breakfast_included=random.random() > 0.5,` |
| `sites/booking/app.py` | 2376 | random_call | seed-time | `distance_from_center=round(random.uniform(0.3, 6.5), 1),` |
| `sites/booking/app.py` | 2385 | random_call | seed-time | `for _ in range(random.randint(3, 6)):` |
| `sites/booking/app.py` | 2386 | random_call | seed-time | `reviewer = random.choice(reviewers)` |
| `sites/booking/app.py` | 2387 | random_call | seed-time | `template = random.choice(review_templates)` |
| `sites/booking/app.py` | 2391 | random_call | seed-time | `rating=round(random.uniform(7.5, 10.0), 1),` |
| `sites/booking/app.py` | 2395 | random_call | seed-time | `traveller_type=random.choice(traveller_types),` |
| `sites/booking/app.py` | 2396 | random_call | seed-time | `stay_length=random.randint(1, 7),` |
| `sites/booking/app.py` | 2397 | random_call | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(5, 365)),` |
| `sites/booking/app.py` | 2397 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(5, 365)),` |
| `sites/booking/app.py` | 2756 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=60),` |
| `sites/booking/app.py` | 2762 | today | seed-time | `check_in=date.today() + timedelta(days=30),` |
| `sites/booking/app.py` | 2763 | today | seed-time | `check_out=date.today() + timedelta(days=33),` |
| `sites/booking/app.py` | 2783 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=120),` |
| `sites/booking/app.py` | 2789 | today | seed-time | `check_in=date.today() - timedelta(days=80),` |
| `sites/booking/app.py` | 2790 | today | seed-time | `check_out=date.today() - timedelta(days=78),` |
| `sites/booking/app.py` | 2809 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=10),` |
| `sites/booking/app.py` | 2815 | today | seed-time | `check_in=date.today() + timedelta(days=60),` |
| `sites/booking/app.py` | 2816 | today | seed-time | `check_out=date.today() + timedelta(days=64),` |
| `sites/booking/app.py` | 2827 | today | seed-time | `check_in=date.today() + timedelta(days=90),` |
| `sites/booking/app.py` | 2828 | today | seed-time | `check_out=date.today() + timedelta(days=95),` |
| `sites/booking/app.py` | 2880 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=30),` |
| `sites/booking/app.py` | 2886 | today | seed-time | `check_in=date.today() + timedelta(days=14),` |
| `sites/booking/app.py` | 2887 | today | seed-time | `check_out=date.today() + timedelta(days=19),` |
| `sites/booking/app.py` | 2906 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=90),` |
| `sites/booking/app.py` | 2912 | today | seed-time | `check_in=date.today() - timedelta(days=70),` |
| `sites/booking/app.py` | 2913 | today | seed-time | `check_out=date.today() - timedelta(days=67),` |
| `sites/booking/app.py` | 2924 | today | seed-time | `check_in=date.today() + timedelta(days=45),` |
| `sites/booking/app.py` | 2925 | today | seed-time | `check_out=date.today() + timedelta(days=48),` |
| `sites/booking/app.py` | 2982 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=45),` |
| `sites/booking/app.py` | 2988 | today | seed-time | `check_in=date.today() + timedelta(days=75),` |
| `sites/booking/app.py` | 2989 | today | seed-time | `check_out=date.today() + timedelta(days=82),` |
| `sites/booking/app.py` | 3008 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=200),` |
| `sites/booking/app.py` | 3014 | today | seed-time | `check_in=date.today() - timedelta(days=170),` |
| `sites/booking/app.py` | 3015 | today | seed-time | `check_out=date.today() - timedelta(days=166),` |
| `sites/booking/app.py` | 3026 | today | seed-time | `check_in=date.today() + timedelta(days=120),` |
| `sites/booking/app.py` | 3027 | today | seed-time | `check_out=date.today() + timedelta(days=127),` |
| `sites/booking/app.py` | 3082 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=5),` |
| `sites/booking/app.py` | 3088 | today | seed-time | `check_in=date.today() + timedelta(days=7),` |
| `sites/booking/app.py` | 3089 | today | seed-time | `check_out=date.today() + timedelta(days=9),` |
| `sites/booking/app.py` | 3108 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=150),` |
| `sites/booking/app.py` | 3114 | today | seed-time | `check_in=date.today() - timedelta(days=130),` |
| `sites/booking/app.py` | 3115 | today | seed-time | `check_out=date.today() - timedelta(days=127),` |
| `sites/booking/app.py` | 3133 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=2),` |
| `sites/booking/app.py` | 3139 | today | seed-time | `check_in=date.today() + timedelta(days=20),` |
| `sites/booking/app.py` | 3140 | today | seed-time | `check_out=date.today() + timedelta(days=21),` |
| `sites/booking/app.py` | 3207 | random_call | seed-time | `rng = random.Random((p.id or 0) * 9301 + 49297)` |
| `sites/cambridge_dictionary/app.py` | 647 | random_call | runtime-or-unknown | `word = random.choice(words)` |
| `sites/cambridge_dictionary/app.py` | 649 | random_call | runtime-or-unknown | `random.shuffle(letters)` |
| `sites/coursera/app.py` | 2465 | random_call | seed-time | `e = Enrollment(user_id=alice.id, course_id=c.id, progress=random.randint(10, 80))` |
| `sites/coursera/app.py` | 2493 | random_call | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(10, 90))))` |
| `sites/coursera/app.py` | 2493 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(10, 90))))` |
| `sites/coursera/app.py` | 2509 | random_call | seed-time | `e = Enrollment(user_id=bob.id, course_id=c.id, progress=random.randint(20, 95))` |
| `sites/coursera/app.py` | 2534 | random_call | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(5, 60))))` |
| `sites/coursera/app.py` | 2534 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(5, 60))))` |
| `sites/coursera/app.py` | 2550 | random_call | seed-time | `e = Enrollment(user_id=carol.id, course_id=c.id, progress=random.randint(30, 100))` |
| `sites/coursera/app.py` | 2576 | random_call | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(15, 120))))` |
| `sites/coursera/app.py` | 2576 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(15, 120))))` |
| `sites/coursera/app.py` | 2592 | random_call | seed-time | `e = Enrollment(user_id=david.id, course_id=c.id, progress=random.randint(40, 100))` |
| `sites/coursera/app.py` | 2619 | random_call | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(5, 180))))` |
| `sites/coursera/app.py` | 2619 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(days=random.randint(5, 180))))` |
| `sites/espn/seed_data.py` | 962 | utcnow | seed-time | `created_at=datetime.utcnow(),` |
| `sites/github/app.py` | 416 | python_hash | runtime-or-unknown | `idx = abs(hash(username)) % 15` |
| `sites/github/app.py` | 1861 | python_hash | seed-time | `u.avatar = f"/static/images/avatars/avatar_{(hash(uname) % 15):02d}.jpg"` |
| `sites/github/app.py` | 2087 | python_hash | seed-time | `'commit_sha': r.get('commit_sha') or (f"{abs(hash(version)):x}"[:7]),` |
| `sites/google_flights/app.py` | 321 | random_call | runtime-or-unknown | `return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))` |
| `sites/google_flights/app.py` | 332 | utcnow | time-dependent | `'now': datetime.utcnow(),` |
| `sites/google_flights/app.py` | 333 | utcnow | time-dependent | `'current_year': datetime.utcnow().year,` |
| `sites/google_flights/app.py` | 1114 | utcnow | time-dependent | `today = datetime.utcnow().date()` |
| `sites/google_flights/app.py` | 1144 | python_hash | runtime-or-unknown | `seed_base = hash((origin_ids[0], dest_ids[0])) & 0xFFFF` |
| `sites/google_flights/app.py` | 1671 | random_call | runtime-or-unknown | `seat=random.choice(['12A', '14C', '22F', '9D', '31B']),` |
| `sites/google_flights/app.py` | 1682 | random_call | runtime-or-unknown | `seat=random.choice(['12A', '14C', '22F', '9D', '31B']),` |
| `sites/google_flights/app.py` | 1726 | utcnow | time-dependent | `b.cancelled_at = datetime.utcnow()` |
| `sites/google_flights/app.py` | 2126 | random_call | seed-time | `b.cancelled_at = datetime.utcnow() - timedelta(days=random.randint(1, 10))` |
| `sites/google_flights/app.py` | 2126 | utcnow | seed-time | `b.cancelled_at = datetime.utcnow() - timedelta(days=random.randint(1, 10))` |
| `sites/google_flights/app.py` | 2136 | random_call | seed-time | `seat=random.choice(['12A', '14C', '22F', '9D', '31B']),` |
| `sites/google_flights/seed_data.py` | 182 | random_call | seed-time | `duration = base + random.randint(-30, 60)` |
| `sites/google_flights/seed_data.py` | 185 | random_call | seed-time | `price = random.uniform(89, 380)` |
| `sites/google_flights/seed_data.py` | 187 | random_call | seed-time | `price = random.uniform(240, 520)` |
| `sites/google_flights/seed_data.py` | 189 | random_call | seed-time | `price = random.uniform(420, 890)` |
| `sites/google_flights/seed_data.py` | 191 | random_call | seed-time | `price = random.uniform(620, 1280)` |
| `sites/google_flights/seed_data.py` | 193 | random_call | seed-time | `price = random.uniform(840, 1680)` |
| `sites/google_flights/seed_data.py` | 321 | random_call | seed-time | `random.seed(42)` |
| `sites/google_flights/seed_data.py` | 325 | today | seed-time | `today = date.today()` |
| `sites/google_flights/seed_data.py` | 373 | random_call | seed-time | `airline_idx = random.randint(0, len(AIRLINES) - 1)` |
| `sites/google_flights/seed_data.py` | 375 | random_call | seed-time | `fn = f"{airline_code}{random.randint(10, 9999)}"` |
| `sites/google_flights/seed_data.py` | 377 | random_call | seed-time | `fn = f"{airline_code}{random.randint(10, 9999)}"` |
| `sites/google_flights/seed_data.py` | 380 | random_call | seed-time | `depart_h = random.choice([5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 22])` |
| `sites/google_flights/seed_data.py` | 381 | random_call | seed-time | `depart_m = random.choice([0, 15, 30, 45])` |
| `sites/google_flights/seed_data.py` | 391 | random_call | seed-time | `stops = random.choice([0, 0, 0, 1, 1, 2]) if duration > 240 else random.choice([0, 0, 1])` |
| `sites/google_flights/seed_data.py` | 392 | random_call | seed-time | `co2 = int(duration * 0.9) + random.randint(-20, 30)` |
| `sites/google_flights/seed_data.py` | 393 | random_call | seed-time | `co2_vs = random.choice([-20, -15, -10, -5, 0, 0, 5, 10, 15, 20, 25])` |
| `sites/google_flights/seed_data.py` | 413 | random_call | seed-time | `aircraft=random.choice(AIRCRAFT),` |
| `sites/google_flights/seed_data.py` | 421 | random_call | seed-time | `baggage_free=random.choice([0, 1, 1, 2]),` |
| `sites/google_flights/seed_data.py` | 422 | random_call | seed-time | `legroom_inches=random.choice([30, 31, 32, 33]),` |
| `sites/google_flights/seed_data.py` | 423 | random_call | seed-time | `wifi=random.choice([True, True, True, False]),` |
| `sites/google_flights/seed_data.py` | 424 | random_call | seed-time | `power=random.choice([True, True, False]),` |
| `sites/google_flights/seed_data.py` | 425 | random_call | seed-time | `entertainment=random.choice([True, True, True, False]),` |
| `sites/google_flights/seed_data.py` | 426 | random_call | seed-time | `rating=round(random.uniform(3.8, 4.9), 1),` |
| `sites/google_flights/seed_data.py` | 427 | random_call | seed-time | `meal_service=random.choice([` |
| `sites/google_flights/seed_data.py` | 431 | random_call | seed-time | `]) if duration > 180 else random.choice(['Snack box', 'Buy on board', 'Complimentary snack']),` |
| `sites/google_flights/seed_data.py` | 432 | random_call | seed-time | `seat_type=random.choice([` |
| `sites/google_flights/seed_data.py` | 435 | random_call | seed-time | `seat_pitch=random.choice(['31 in', '31 in', '32 in', '32 in', '33 in', '34 in']),` |
| `sites/google_flights/seed_data.py` | 450 | random_call | seed-time | `airline_idx = random.randint(0, len(AIRLINES) - 1)` |
| `sites/google_flights/seed_data.py` | 452 | random_call | seed-time | `fn = f"{airline_code}{random.randint(10, 9999)}"` |
| `sites/google_flights/seed_data.py` | 454 | random_call | seed-time | `fn = f"{airline_code}{random.randint(10, 9999)}"` |
| `sites/google_flights/seed_data.py` | 456 | random_call | seed-time | `depart_h = random.choice([5, 6, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18, 19, 20, 22])` |
| `sites/google_flights/seed_data.py` | 457 | random_call | seed-time | `depart_m = random.choice([0, 15, 30, 45])` |
| `sites/google_flights/seed_data.py` | 461 | random_call | seed-time | `stops = random.choice([0, 0, 0, 1, 1, 2]) if duration > 240 else random.choice([0, 0, 1])` |
| `sites/google_flights/seed_data.py` | 462 | random_call | seed-time | `co2 = int(duration * 0.9) + random.randint(-20, 30)` |
| `sites/google_flights/seed_data.py` | 463 | random_call | seed-time | `co2_vs = random.choice([-20, -15, -10, -5, 0, 0, 5, 10, 15, 20, 25])` |
| `sites/google_flights/seed_data.py` | 479 | random_call | seed-time | `'aircraft': random.choice(AIRCRAFT),` |
| `sites/google_flights/seed_data.py` | 487 | random_call | seed-time | `'baggage_free': random.choice([0, 1, 1, 2]),` |
| `sites/google_flights/seed_data.py` | 490 | random_call | seed-time | `'legroom_inches': random.choice([30, 31, 32, 33]),` |
| `sites/google_flights/seed_data.py` | 491 | random_call | seed-time | `'wifi': random.choice([True, True, True, False]),` |
| `sites/google_flights/seed_data.py` | 492 | random_call | seed-time | `'power': random.choice([True, True, False]),` |
| `sites/google_flights/seed_data.py` | 493 | random_call | seed-time | `'entertainment': random.choice([True, True, True, False]),` |
| `sites/google_flights/seed_data.py` | 494 | random_call | seed-time | `'meal_service': (random.choice([` |
| `sites/google_flights/seed_data.py` | 499 | random_call | seed-time | `else random.choice(['Snack box', 'Buy on board', 'Complimentary snack'])),` |
| `sites/google_flights/seed_data.py` | 500 | random_call | seed-time | `'seat_type': random.choice([` |
| `sites/google_flights/seed_data.py` | 503 | random_call | seed-time | `'seat_pitch': random.choice(['31 in', '31 in', '32 in', '32 in', '33 in', '34 in']),` |
| `sites/google_flights/seed_data.py` | 504 | random_call | seed-time | `'rating': round(random.uniform(3.8, 4.9), 1),` |
| `sites/google_flights/seed_data.py` | 508 | utcnow | seed-time | `'created_at': datetime.utcnow(),` |
| `sites/google_flights/seed_data.py` | 581 | random_call | seed-time | `for offset in random.sample(range(0, 366), k=random.choice([6, 7, 8, 9])):` |
| `sites/google_flights/seed_data.py` | 726 | random_call | seed-time | `random.shuffle(stops_pool)` |
| `sites/google_flights/seed_data.py` | 735 | random_call | seed-time | `f.stops = stops_pool[i] if i < len(stops_pool) else random.choice([0, 1])` |
| `sites/google_flights/seed_data.py` | 748 | random_call | seed-time | `random.uniform(max_eco_price * 0.40, max_eco_price * 0.95), 0` |
| `sites/google_flights/seed_data.py` | 752 | random_call | seed-time | `random.uniform(max_eco_price * 5.5, max_eco_price * 9.0), 0` |
| `sites/google_flights/seed_data.py` | 755 | random_call | seed-time | `spread = random.uniform(0.55, 1.65)` |
| `sites/google_flights/seed_data.py` | 763 | random_call | seed-time | `f.duration_minutes = int(f.duration_minutes * random.uniform(1.15, 1.35))` |
| `sites/google_flights/seed_data.py` | 764 | random_call | seed-time | `f.stops = max(f.stops, random.choice([1, 1, 2]))` |
| `sites/google_flights/seed_data.py` | 773 | random_call | seed-time | `airline_factor = random.uniform(0.78, 1.22)` |
| `sites/google_flights/seed_data.py` | 774 | random_call | seed-time | `aircraft_factor = random.choice([0.85, 0.95, 1.0, 1.1, 1.18])` |
| `sites/google_flights/seed_data.py` | 776 | random_call | seed-time | `f.co2_vs_typical = random.choice([-25, -18, -12, -8, -3, 0, 4, 9, 14, 20])` |
| `sites/google_map/app.py` | 398 | random_call | runtime-or-unknown | `return "TRIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))` |
| `sites/google_map/app.py` | 439 | utcnow | time-dependent | `"current_year": datetime.utcnow().year,` |
| `sites/google_map/app.py` | 2409 | utcnow | time-dependent | `visited_at=datetime.utcnow(),` |
| `sites/google_map/app.py` | 2487 | utcnow | time-dependent | `visited_at=datetime.utcnow(),` |
| `sites/google_map/app.py` | 2657 | utcnow | seed-time | `today = datetime.utcnow().date()` |
| `sites/google_map/seed_data.py` | 210 | random_call | seed-time | `return base + random.uniform(-amount, amount)` |
| `sites/google_map/seed_data.py` | 218 | random_call | seed-time | `random.seed(42)` |
| `sites/google_map/seed_data.py` | 543 | random_call | seed-time | `addr = f"{random.randint(1, 999)} {random.choice(streets)}, {city.display_name}"` |
| `sites/google_map/seed_data.py` | 545 | random_call | seed-time | `rating = round(random.uniform(4.2, 4.9), 1)` |
| `sites/google_map/seed_data.py` | 546 | random_call | seed-time | `review_count = random.randint(1200, 85000)` |
| `sites/google_map/seed_data.py` | 547 | random_call | seed-time | `price = random.choice(price_by_cat.get(cat_slug, ["$"]))` |
| `sites/google_map/seed_data.py` | 559 | random_call | seed-time | `phone=f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",` |
| `sites/google_map/seed_data.py` | 560 | random_call | seed-time | `hours=random.choice(OPEN_HOURS_TEMPLATES),` |
| `sites/google_map/seed_data.py` | 602 | random_call | seed-time | `style_name, cat_slug, desc, price = random.choice(style_pack)` |
| `sites/google_map/seed_data.py` | 607 | random_call | seed-time | `name = f"{random.choice(streets).split(' ')[0]} {style_name}"` |
| `sites/google_map/seed_data.py` | 615 | random_call | seed-time | `donor_slug, donor_imgs = random.choice(city_places_imgs)` |
| `sites/google_map/seed_data.py` | 632 | random_call | seed-time | `address=f"{random.randint(1, 999)} {random.choice(streets)}, {display}",` |
| `sites/google_map/seed_data.py` | 633 | random_call | seed-time | `phone=f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",` |
| `sites/google_map/seed_data.py` | 634 | random_call | seed-time | `hours=random.choice(OPEN_HOURS_TEMPLATES),` |
| `sites/google_map/seed_data.py` | 635 | random_call | seed-time | `rating=round(random.uniform(4.0, 4.8), 1),` |
| `sites/google_map/seed_data.py` | 636 | random_call | seed-time | `review_count=random.randint(80, 3500),` |
| `sites/google_map/seed_data.py` | 644 | random_call | seed-time | `is_popular=random.random() > 0.6,` |
| `sites/google_map/seed_data.py` | 658 | random_call | seed-time | `p.parking_info = random.choice([` |
| `sites/google_map/seed_data.py` | 667 | random_call | seed-time | `p.parking_info = random.choice([` |
| `sites/google_map/seed_data.py` | 675 | random_call | seed-time | `p.parking_info = random.choice([` |
| `sites/google_map/seed_data.py` | 681 | random_call | seed-time | `p.has_parking_lot = random.random() > 0.4` |
| `sites/google_map/seed_data.py` | 683 | random_call | seed-time | `p.parking_info = random.choice([` |
| `sites/google_map/seed_data.py` | 689 | random_call | seed-time | `p.has_parking_lot = random.random() > 0.5` |
| `sites/google_map/seed_data.py` | 691 | random_call | seed-time | `p.delivery_available = random.random() > 0.3` |
| `sites/google_map/seed_data.py` | 693 | random_call | seed-time | `p.parking_info = random.choice([` |
| `sites/google_map/seed_data.py` | 842 | random_call | seed-time | `lat=kwargs.pop("lat", city.lat + random.uniform(-0.02, 0.02)),` |
| `sites/google_map/seed_data.py` | 843 | random_call | seed-time | `lng=kwargs.pop("lng", city.lng + random.uniform(-0.02, 0.02)),` |
| `sites/google_map/seed_data.py` | 850 | random_call | seed-time | `random.seed(99)` |
| `sites/google_map/seed_data.py` | 862 | random_call | seed-time | `subcategory="Beauty Salon", rating=round(random.uniform(4.86, 4.95), 2),` |
| `sites/google_map/seed_data.py` | 863 | random_call | seed-time | `address=f"{random.randint(100, 999)} Pike St, Seattle, WA",` |
| `sites/google_map/seed_data.py` | 940 | random_call | seed-time | `address=f"{random.randint(100, 999)} Detroit Rd, Avon, OH 44012",` |
| `sites/google_map/seed_data.py` | 942 | random_call | seed-time | `rating=round(random.uniform(4.0, 4.8), 1),` |
| `sites/google_map/seed_data.py` | 1100 | random_call | seed-time | `rating=round(random.uniform(4.6, 4.9), 1),` |
| `sites/google_search/app.py` | 335 | utcnow | time-dependent | `'current_year': datetime.utcnow().year,` |
| `sites/google_search/app.py` | 442 | utcnow | time-dependent | `delta = datetime.utcnow() - dt` |
| `sites/google_search/app.py` | 635 | utcnow | time-dependent | `if not recent or (datetime.utcnow() - recent.searched_at).seconds > 60:` |
| `sites/google_search/app.py` | 649 | random_call | runtime-or-unknown | `result_count = random.randint(100_000, 10_000_000)` |
| `sites/google_search/app.py` | 650 | random_call | runtime-or-unknown | `search_time = round(random.uniform(0.24, 0.88), 2)` |
| `sites/google_search/app.py` | 758 | sql_random | runtime-display | `t = Topic.query.order_by(func.random()).first()` |
| `sites/google_search/app.py` | 767 | sql_random | runtime-display | `related_topics = Topic.query.filter(Topic.id != topic.id).order_by(func.random()).limit(6).all()` |
| `sites/google_search/app.py` | 954 | sql_random | runtime-display | `related_topics = Topic.query.filter(Topic.id != topic.id).order_by(func.random()).limit(6).all()` |
| `sites/google_search/app.py` | 1511 | utcnow | time-dependent | `if not recent or (datetime.utcnow() - recent.searched_at).seconds > 60:` |
| `sites/google_search/app.py` | 1597 | utcnow | seed-time | `now = datetime.utcnow()` |
| `sites/google_search/app.py` | 1613 | random_call | seed-time | `result_count=random.randint(100000, 5000000),` |
| `sites/google_search/app.py` | 1685 | random_call | seed-time | `result_count=random.randint(50000, 3000000),` |
| `sites/google_search/app.py` | 1739 | random_call | seed-time | `result_count=random.randint(200000, 8000000),` |
| `sites/google_search/app.py` | 1796 | random_call | seed-time | `result_count=random.randint(100000, 6000000),` |
| `sites/google_search/seed_data.py` | 1013 | secrets | seed-time | `('Inception (2010) - IMDb', 'www.imdb.com', 'Inception rated 8.8/10 on IMDb. Directed by Christopher Nolan. A thief enters the dreams of others to steal secrets.'),` |
| `sites/google_search/seed_data.py` | 1473 | random_call | seed-time | `result_count=random.randint(1_000_000, 500_000_000),` |
| `sites/google_search/seed_data.py` | 1474 | random_call | seed-time | `search_time=round(random.uniform(0.22, 0.79), 2),` |
| `sites/google_search/seed_data.py` | 1607 | random_call | seed-time | `random.seed(hash(slug) % 10000)` |
| `sites/google_search/seed_data.py` | 1607 | python_hash | seed-time | `random.seed(hash(slug) % 10000)` |
| `sites/google_search/seed_data.py` | 1608 | random_call | seed-time | `picked = ['wikipedia'] + random.sample([p for p in providers if p != 'wikipedia'], 7)` |
| `sites/google_search/seed_data.py` | 1646 | random_call | seed-time | `random.seed(hash(topic) % 50000)` |
| `sites/google_search/seed_data.py` | 1646 | python_hash | seed-time | `random.seed(hash(topic) % 50000)` |
| `sites/google_search/seed_data.py` | 1647 | random_call | seed-time | `picked = random.sample(PAA_TEMPLATES, 5)` |
| `sites/google_search/seed_data.py` | 1653 | random_call | seed-time | `random.seed(hash(topic) % 20000)` |
| `sites/google_search/seed_data.py` | 1653 | python_hash | seed-time | `random.seed(hash(topic) % 20000)` |
| `sites/google_search/seed_data.py` | 1655 | random_call | seed-time | `picks = random.sample(pool, min(8, len(pool)))` |
| `sites/google_search/seed_data.py` | 1658 | random_call | seed-time | `random.shuffle(mods)` |
| `sites/google_search/seed_data.py` | 1689 | random_call | seed-time | `volume=random.randint(50000, 5000000),` |
| `sites/google_search/seed_data.py` | 1690 | random_call | seed-time | `trend_direction=random.choice(['up', 'up', 'up', 'flat', 'down']),` |
| `sites/google_search/seed_data.py` | 1700 | random_call | seed-time | `image_url=f'/static/images/topics/{random.choice(["paris", "mars", "moon", "galaxy", "sunflower", "ada_lovelace"])}/img_hero.jpg',` |
| `sites/google_search/seed_data.py` | 1717 | random_call | seed-time | `result_count=random.randint(1_000_000, 500_000_000),` |
| `sites/google_search/seed_data.py` | 1718 | random_call | seed-time | `search_time=round(random.uniform(0.22, 0.79), 2),` |
| `sites/huggingface/app.py` | 459 | random_call | runtime-or-unknown | `followers_count=random.randint(300, 9000),` |
| `sites/huggingface/app.py` | 633 | random_call | seed-time | `rng = random.Random(7)` |
| `sites/huggingface/app.py` | 1786 | random_call | seed-time | `avatar_url=f"/static/images/avatars/{random.choice(avatar_files)}" if avatar_files else "",` |
| `sites/huggingface/app.py` | 2139 | random_call | seed-time | `ep_id = "EP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))` |
| `sites/huggingface/app.py` | 2674 | random_call | seed-time | `rng = random.Random(42)` |
| `sites/huggingface/seed_data.py` | 668 | random_call | seed-time | `rng = random.Random(42)` |
| `sites/wolfram_alpha/app.py` | 21 | secrets | security/runtime | `app.config['SECRET_KEY'] = secrets.token_hex(32)` |
| `sites/wolfram_alpha/app.py` | 718 | utcnow | seed-time | `now = datetime.utcnow()` |
| `sites/wolfram_alpha/app.py` | 809 | utcnow | seed-time | `pro_plan='professional', pro_since=datetime.utcnow())` |
| `sites/wolfram_alpha/app.py` | 820 | utcnow | seed-time | `created_at=datetime.utcnow() - timedelta(hours=i*3)))` |
| `sites/wolfram_alpha/app.py` | 1444 | utcnow | seed-time | `nb.updated_at = datetime.utcnow()` |
| `sites/wolfram_alpha/app.py` | 1475 | utcnow | seed-time | `nb.updated_at = datetime.utcnow()` |
