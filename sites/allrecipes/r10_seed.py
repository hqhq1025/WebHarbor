"""R10 final polish seed — three closing variant passes (Dessert-Sweet /
Seafood-Coastal / Grilling-BBQ) targeting the lingering surface gaps
identified by the R10 audit.

Runs AFTER R9 inside ``seed_data.seed_extended_catalog``. Everything in
here is deterministic so a rebuild from source is byte-identical to the
shipped ``instance_seed/allrecipes.db``.

R10 deliverables (recipes 28326 -> 31000+):
  * 1 new top-level cuisine/cooking-method category: grilling.
    (desserts / seafood already exist as top-level categories.)
  * 3 variant passes — Dessert-Sweet, Seafood-Coastal, Grilling-BBQ —
    each operating on the same Test Kitchen base subsample (step 9,
    ~930 recipes per pass, ~2790 new total). They re-cast the base
    into a dessert, a seafood/coastal, and a grilling/BBQ register.

Idempotent — gated on the presence of a sentinel R10 recipe slug.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta

from app import (
    db, Category, Recipe,
)

IMAGES_DIR_REL = '/static/images/recipes_real'
IMAGE_POOL_SIZE = 219
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)


def _slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    s = re.sub(r"[^a-zA-Z0-9]+", '-', s.lower()).strip('-')
    return s or 'item'


def _fmt_mins(m: int) -> str:
    if m < 60:
        return f"{m} mins"
    h, rem = divmod(m, 60)
    return f"{h} hr" if rem == 0 else f"{h} hr {rem} mins"


# All variant author tokens introduced before R10. We skip recipes whose
# author_name already contains any of these to avoid stacking variants on
# variants.
R10_AUTHOR_TOKENS = (
    'Dessert-Sweet', 'Seafood-Coastal', 'Grilling-BBQ',
)
R9_AUTHOR_TOKENS = (
    'Indian-Regional', 'MiddleEastern-Regional',
    'Caribbean-Regional', 'African-Regional',
)
R8_AUTHOR_TOKENS = (
    'Baking-Cookies', 'Baking-Cakes', 'Baking-Pies',
    'Baking-Breads', 'Baking-Pastries',
)
R7_AUTHOR_TOKENS = (
    'Korean-Regional', 'Thai-Regional', 'Mexican-Regional',
    'Vegetarian-By-Protein',
)
R6_AUTHOR_TOKENS = (
    'Copycat-Restaurant', 'Budget-Friendly', 'Holiday-Entertaining',
    'Air-Fryer-Shortcut',
)


def _is_prev_variant(name: str) -> bool:
    n = name or ''
    return any(tok in n for tok in (R6_AUTHOR_TOKENS + R7_AUTHOR_TOKENS
                                    + R8_AUTHOR_TOKENS + R9_AUTHOR_TOKENS
                                    + R10_AUTHOR_TOKENS))


def _cat_slug_for(base, cat_by_slug):
    if not base.category_id:
        return None
    for slug, c in cat_by_slug.items():
        if c.id == base.category_id:
            return slug
    return None


# ===========================================================================
# R10 top-level categories (only the new ones — desserts + seafood already
# exist from earlier rounds).
# ===========================================================================

R10_CATEGORIES = [
    ('Grilling',
     'grilling',
     'Live-fire and grill cooking — direct-heat sears, indirect-heat smoke, dry rubs, mop sauces and barbecue traditions from Texas, Carolina, Kansas City and Memphis.',
     'cooking-method',
     120),
]


def _seed_r10_categories(cat_by_slug):
    added = 0
    for name, slug, desc, ptype, order in R10_CATEGORIES:
        if slug in cat_by_slug:
            continue
        c = Category(name=name, slug=slug, description=desc,
                     parent_type=ptype, display_order=order)
        db.session.add(c)
        cat_by_slug[slug] = c
        added += 1
    return added


# ===========================================================================
# Pass 1 — Dessert-Sweet variant
# ===========================================================================

DESSERT_INSTRUCTIONS = [
    "Cream butter and sugar at medium speed for a full 4 minutes — the mixture should triple in volume and pale to ivory.",
    "Add eggs one at a time, scraping the bowl after each; emulsion before flour is what gives the dessert a fine, even crumb.",
    "Fold in dry ingredients in three additions on low speed; stop as soon as no streaks remain to avoid gluten development.",
    "Bake at the temperature your recipe specifies; rotate the pan once at the halfway mark for even browning.",
    "Cool the dessert completely before glazing or dusting with powdered sugar — warm desserts will dissolve the topping.",
]


def _seed_dessert_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('desserts')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"dessert-sweet-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"Dessert-Sweet {base.title}"
        new_prep = 25 + (ri % 12)
        new_cook = 30 + (ri % 18)
        new_total = new_prep + new_cook
        style = ('Bakery-Classic', 'French-Patisserie', 'American-Comfort',
                 'Nordic-Light', 'Italian-Dolci')[ri % 5]
        new_ings = [
            '1 cup unsalted butter (room temp)',
            '1 cup granulated sugar',
            '1/2 cup light brown sugar (packed)',
            '3 large eggs (room temp)',
            '2 tsp pure vanilla extract',
            '2 1/2 cups all-purpose flour',
            '1 tsp baking powder',
            '1/2 tsp baking soda',
            '1/2 tsp fine sea salt',
            '1 cup buttermilk',
            f"1 1/2 cups {base.main_ingredient or 'mixed fruit'}, prepped",
            '1/4 cup powdered sugar (for dusting)',
            '1 tbsp lemon zest (brightener)',
            '1/2 cup heavy cream (for whipped finish)',
            '1 tsp ground cinnamon (optional warmth)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'desserts', 'dessert-sweet', style.lower(),
            'baked', 'sweet-finish',
            cat_slug or 'desserts',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        # Dessert pass: vegan/dairy-free not preserved because we add butter +
        # eggs + cream. Vegetarian survives.
        new_dietary = sorted(
            set(tag for tag in base_dietary if tag in {'vegetarian', 'gluten-free'})
        )
        img_n = ((ri * 281 + 17) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{style} dessert walkthrough",
            'desc': f"Cream + fold + bake photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 283 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 293 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 307 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 31 + 7) % 720)
        cal = 360 + (ri * 19) % 220
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {style} sweet reinterpretation of {base.title}. Creamed-butter "
                "base, three-stage flour fold, and a gentle bake — finished with a "
                "powdered-sugar dust or whipped-cream cap depending on the cut."),
            category_id=(cat.id if cat else base.category_id),
            cuisine=base.cuisine or 'American',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='8',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(DESSERT_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '6g', 'Fat': '18g', 'Carbs': '52g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 83 == 0),
            is_editors_pick=(ri % 109 == 0),
            avg_rating=round(min(5.0, 4.6 + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Dessert-Sweet Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='dessert', meal_type='dessert',
            cooking_method='baked',
            main_ingredient=base.main_ingredient or 'butter-and-sugar',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Store in an airtight container at room temperature up to 3 days; refrigerate up to 1 week if cream-finished.',
            primary_seasoning='vanilla',
            max_oven_temp=350,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 2 — Seafood-Coastal variant
# ===========================================================================

SEAFOOD_INSTRUCTIONS = [
    "Pat the fish or shellfish dry with paper towels — moisture is the enemy of a clean sear.",
    "Season at most 20 minutes before cooking; salt extracts moisture from the surface if it sits too long.",
    "Cook the seafood gently — most fish is done at 130-140°F internal; an opaque-but-still-translucent center is the target.",
    "Build a coastal sauce on a separate burner: shallots, white wine, lemon, butter, capers and fresh herbs.",
    "Plate the seafood over the sauce, never under, so the crust stays crisp; finish with sea salt and a squeeze of lemon at the table.",
]


def _seed_seafood_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('seafood')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"seafood-coastal-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"Seafood-Coastal {base.title}"
        new_prep = 15 + (ri % 10)
        new_cook = 12 + (ri % 14)
        new_total = new_prep + new_cook
        region = ('New-England', 'Pacific-Northwest', 'Gulf-Coast',
                  'Mediterranean', 'Iberian-Atlantic')[ri % 5]
        new_ings = [
            f"600 g fresh seafood (cod, halibut, shrimp or scallops — substitute for {base.main_ingredient or 'protein'})",
            '2 tbsp olive oil',
            '2 tbsp unsalted butter',
            '4 shallots (thinly sliced)',
            '3 cloves garlic (minced)',
            '1/2 cup dry white wine',
            '1 cup fish or seafood stock',
            '1 lemon (juice + zest)',
            '2 tbsp capers (drained)',
            '1 tbsp fresh dill (chopped)',
            '2 tbsp flat-leaf parsley',
            '1/2 tsp red pepper flakes',
            '1/2 tsp flaky sea salt',
            '1/4 tsp white pepper',
            '1 tbsp extra-virgin olive oil (finishing)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'seafood', 'seafood-coastal', region.lower(),
            'pescatarian-friendly', 'light-protein', 'shallot-and-wine',
            cat_slug or 'seafood',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        # Seafood pass: vegan/vegetarian drop out (added fish + butter).
        # gluten-free, dairy-free preserved if base had them — though we add
        # butter, so dairy-free also drops. Treat conservatively: keep only
        # gluten-free.
        new_dietary = sorted(
            set(tag for tag in base_dietary if tag in {'gluten-free'})
        ) + ['pescatarian']
        new_dietary = sorted(set(new_dietary))
        img_n = ((ri * 311 + 29) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{region} coastal walkthrough",
            'desc': f"Sear + sauce + plate photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 313 + 17) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 317 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 331 + 47) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 37 + 11) % 720)
        cal = 280 + (ri * 11) % 160
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {region} coastal reinterpretation of {base.title}. Gently seared "
                "fish or shellfish over a shallot-wine-lemon-butter sauce, finished "
                "with capers, dill, parsley and flaky salt for clean, bright flavor."),
            category_id=(cat.id if cat else base.category_id),
            cuisine=base.cuisine or 'Coastal',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(SEAFOOD_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '32g', 'Fat': '14g', 'Carbs': '8g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 89 == 0),
            is_editors_pick=(ri % 113 == 0),
            avg_rating=round(min(5.0, 4.55 + ((ri % 13 - 6) * 0.02)), 1),
            review_count=0,
            author_name='Seafood-Coastal Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='main', meal_type='dinner',
            cooking_method='pan-seared',
            main_ingredient='fish-or-shellfish',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Best eaten the day cooked; refrigerate leftovers up to 24 hours and reheat gently to avoid rubbery seafood.',
            primary_seasoning='lemon-and-dill',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 3 — Grilling-BBQ variant
# ===========================================================================

GRILLING_INSTRUCTIONS = [
    "Set up a two-zone grill — direct heat on one side for searing, indirect on the other for finishing. This is the single most important step.",
    "Pat the protein dry, then apply a dry rub at least 30 minutes (and up to overnight) before cooking; the salt cures the surface for a deeper bark.",
    "Sear over direct heat for 2-3 minutes per side to build crust; move to the indirect side and close the lid for the remaining cook time.",
    "Mop with a vinegar-based sauce in the last 10 minutes only — sugar in the sauce will burn if applied too early.",
    "Rest the grilled protein for at least 5 minutes (large cuts: 15+) before slicing across the grain. Resting is non-negotiable for juicy results.",
]


def _seed_grilling_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('grilling')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"grilling-bbq-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"Grilling-BBQ {base.title}"
        new_prep = 30 + (ri % 14)  # includes rub-cure time
        new_cook = 25 + (ri % 22)
        new_total = new_prep + new_cook
        style = ('Texas-Brisket', 'Carolina-Vinegar', 'Kansas-City-Sweet',
                 'Memphis-Dry', 'Santa-Maria-Tri-Tip')[ri % 5]
        new_ings = [
            f"800 g {base.main_ingredient or 'beef brisket or pork shoulder'}, trimmed",
            '2 tbsp coarse kosher salt',
            '2 tbsp coarse-ground black pepper',
            '2 tbsp dark brown sugar',
            '1 tbsp smoked paprika',
            '1 tbsp garlic powder',
            '1 tbsp onion powder',
            '1 tsp cayenne pepper',
            '1 tsp ground mustard',
            '1 tsp ground cumin',
            '1/2 cup apple cider vinegar (mop)',
            '1/2 cup ketchup-based BBQ sauce',
            '2 tbsp Worcestershire sauce',
            '1 tbsp molasses',
            '1 bottle dark beer (for spritz)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'grilling', 'grilling-bbq', style.lower(),
            'live-fire', 'two-zone-grill', 'dry-rub', 'mop-sauce',
            cat_slug or 'grilling',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        # Grilling pass: vegetarian/vegan drop (heavy meat focus). gluten-free
        # preserved (no flour in rub). dairy-free preserved (no dairy).
        new_dietary = sorted(
            set(tag for tag in base_dietary if tag in {'gluten-free', 'dairy-free', 'paleo', 'low-carb', 'keto'})
        )
        img_n = ((ri * 337 + 41) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{style} grill walkthrough",
            'desc': f"Rub + sear + smoke + rest photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 347 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 349 + 37) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 353 + 53) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 41 + 17) % 720)
        cal = 460 + (ri * 23) % 240
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {style} barbecue reinterpretation of {base.title}. Salt-and-"
                "pepper-forward dry rub, two-zone grilling (sear then indirect smoke), "
                "and a vinegar-based mop applied only in the final 10 minutes."),
            category_id=(cat.id if cat else base.category_id),
            cuisine=base.cuisine or 'American',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='6',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(GRILLING_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '38g', 'Fat': '26g', 'Carbs': '16g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 79 == 0),
            is_editors_pick=(ri % 103 == 0),
            avg_rating=round(min(5.0, 4.6 + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Grilling-BBQ Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='main', meal_type='dinner',
            cooking_method='grilled',
            main_ingredient=base.main_ingredient or 'pork-or-beef',
            occasion='summer-cookout', season='summer',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Refrigerate leftovers up to 4 days wrapped in butcher paper; reheat in a 250°F oven with a splash of mop sauce.',
            primary_seasoning='kosher-salt-and-pepper',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Public entry point — called from seed_data.seed_extended_catalog after R9.
# ===========================================================================

R10_SENTINEL_SLUG = 'dessert-sweet-classic-waffles'


def run_r10_polish(cat_by_slug):
    """R10 top-level. Returns a counts dict."""
    if Recipe.query.filter_by(slug=R10_SENTINEL_SLUG).first():
        return {'skipped': True}

    counts = {}

    # 1) New top-level category (grilling).
    counts['categories'] = _seed_r10_categories(cat_by_slug)
    db.session.flush()
    cat_by_slug.update({c.slug: c for c in Category.query.all()})

    # 2) Variant passes — base = Test Kitchen recipes not already R6/R7/R8/R9.
    # Subsample by step 9 -> ~930 per pass × 3 = ~2790 new.
    base_for_r10 = (Recipe.query
                    .filter(Recipe.author_name.like('%Test Kitchen%'))
                    .order_by(Recipe.id)
                    .all())
    base_for_r10 = [r for r in base_for_r10
                    if not _is_prev_variant(r.author_name)]
    base_for_r10 = base_for_r10[::9]
    print(f"[r10_seed] base_for_r10 size: {len(base_for_r10)}")

    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['dessert'] = _seed_dessert_variants(cat_by_slug, base_for_r10, existing_recipe_slugs)
    db.session.flush()
    counts['seafood'] = _seed_seafood_variants(cat_by_slug, base_for_r10, existing_recipe_slugs)
    db.session.flush()
    counts['grilling'] = _seed_grilling_variants(cat_by_slug, base_for_r10, existing_recipe_slugs)
    db.session.flush()

    return counts
