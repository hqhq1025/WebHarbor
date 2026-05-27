"""R8 polish seed — five baking sub-category variant passes
(Cookies / Cakes / Pies / Breads / Pastries) + a new baking-focused chef
(Chef Pierre Beaumont) broadening the Pastry / French baking surface.

Runs AFTER R7 inside ``seed_data.seed_extended_catalog``. Everything in
here is deterministic so a rebuild from source is byte-identical to the
shipped ``instance_seed/allrecipes.db``.

R8 deliverables (recipes 18282 -> 23000+):
  * 5 new categories: cookies / cakes / pies / breads / pastries
  * 5 new variant passes — Cookies, Cakes, Pies, Breads, Pastries
    each operating on the same Test Kitchen base subsample (~1040
    recipes per pass, ~5200 new total). They sweet-pivot the base by
    folding in butter / sugar / flour / egg ratios + classic baking
    techniques (creaming, kneading, blind-baking, lamination).
  * Chef Pierre Beaumont — 14 patisserie classics filling the
    French-pastry leaderboard.

Idempotent — gated on the presence of a sentinel R8 recipe slug.
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


# Variant authors we never re-iterate over (R6/R7/R8).
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


def _is_r6_variant(name: str) -> bool:
    return any(tok in (name or '') for tok in R6_AUTHOR_TOKENS)


def _is_r7_variant(name: str) -> bool:
    return any(tok in (name or '') for tok in R7_AUTHOR_TOKENS)


def _is_r8_variant(name: str) -> bool:
    return any(tok in (name or '') for tok in R8_AUTHOR_TOKENS)


def _cat_slug_for(base, cat_by_slug):
    if not base.category_id:
        return None
    for slug, c in cat_by_slug.items():
        if c.id == base.category_id:
            return slug
    return None


# ===========================================================================
# Baking sub-categories
# ===========================================================================

BAKING_SUBCATEGORIES = [
    ('Cookies',   'cookies',   'Drop, rolled, bar and no-bake cookies — every variety from chewy to crisp.',                 'meal', 95),
    ('Cakes',     'cakes',     'Layer cakes, sheet cakes, bundts, cupcakes — birthday- and bakery-grade frostings included.', 'meal', 96),
    ('Pies',      'pies',      'Sweet and savory pies — single-crust, double-crust, hand pies and tarts.',                    'meal', 97),
    ('Breads',    'breads',    'Yeasted loaves, quick breads, flatbreads, focaccia and rolls.',                               'meal', 98),
    ('Pastries',  'pastries',  'Laminated dough, choux, danish, croissants and puff-pastry creations.',                       'meal', 99),
]


def _seed_baking_subcategories(cat_by_slug):
    added = 0
    for name, slug, desc, ptype, order in BAKING_SUBCATEGORIES:
        if slug in cat_by_slug:
            continue
        c = Category(name=name, slug=slug, description=desc,
                     parent_type=ptype, display_order=order)
        db.session.add(c)
        cat_by_slug[slug] = c
        added += 1
    return added


# ===========================================================================
# Pass 1 — Cookies variant
# ===========================================================================

COOKIE_INSTRUCTIONS = [
    "Cream room-temperature butter with the sugars on medium speed for a full 3 minutes — this is where the chew comes from.",
    "Whisk dry ingredients (flour + leavening + salt) separately so the leavening is evenly distributed before it touches the wet.",
    "Fold in mix-ins at the end on the lowest speed for under 10 seconds — overmixing develops gluten and turns cookies cakey.",
    "Chill the scooped dough at least 30 minutes (overnight is better) so the butter re-solidifies and the cookies spread less.",
    "Bake on a parchment-lined sheet at 350°F and pull at the moment the edges set — the center finishes baking on the hot pan.",
]


def _seed_cookies_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cookies_cat = cat_by_slug.get('cookies') or cat_by_slug.get('baking')
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name) or _is_r8_variant(base.author_name):
            continue
        new_title = f"Baking-Cookies {base.title}"
        new_slug = f"baking-cookies-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 15
        new_prep = max(15, base_prep + 10)  # chilling time bumps prep
        new_cook = 12 + (ri % 4)  # cookies bake fast, 12-15 mins
        new_total = new_prep + new_cook
        new_ings = [
            '1 cup unsalted butter, room temperature',
            '3/4 cup granulated sugar',
            '3/4 cup packed brown sugar',
            '2 large eggs',
            '2 tsp vanilla extract',
            '2 1/4 cups all-purpose flour',
            '1 tsp baking soda',
            '1 tsp fine sea salt',
            f'1 1/2 cups {base.main_ingredient or "chocolate chips"} (folded in last)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'cookies', 'baking', 'baking-cookies', 'dessert', 'sweet',
            'butter-creamed', 'chill-and-bake',
            cat_slug or 'desserts',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary) | {'vegetarian'})
        img_n = ((ri * 137 + 7) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Cookie walkthrough',
            'desc': f"Step-by-step photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 139 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 149 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 151 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 23 + 5) % 720)
        cal = 180 + (ri * 7) % 80  # per cookie
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A cookie reinterpretation of {base.title}. Creamed-butter base, "
                "chilled dough for clean edges, baked at 350°F to a barely-set "
                "center for the classic chewy cookie texture."),
            category_id=(cookies_cat.id if cookies_cat else base.category_id),
            cuisine='American',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='24 cookies',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(COOKIE_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Sugar': '14g', 'Fat': '9g', 'Carbs': '24g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 71 == 0),
            is_editors_pick=(ri % 89 == 0),
            avg_rating=round(min(5.0, 4.5 + ((ri % 9 - 4) * 0.02)), 1),
            review_count=0,
            author_name='Baking-Cookies Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='dessert', meal_type='snack',
            cooking_method='baked',
            main_ingredient='flour',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 5 days at room temperature in an airtight tin; freeze the scooped dough up to 3 months.',
            primary_seasoning='vanilla',
            max_oven_temp=350,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 2 — Cakes variant
# ===========================================================================

CAKE_INSTRUCTIONS = [
    "Bring eggs, butter and dairy to room temperature; cold ingredients curdle the emulsion and cause a dense crumb.",
    "Cream butter and sugar until visibly lighter and fluffier — at least 4 minutes on medium-high.",
    "Alternate dry and wet additions (dry / wet / dry / wet / dry) to keep the batter emulsified.",
    "Bake at 350°F until a tester inserted in the center comes out with a few moist crumbs — never bone-dry.",
    "Cool 10 minutes in the pan, then invert onto a rack so the cake doesn't steam itself soggy on the bottom.",
]


def _seed_cakes_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cakes_cat = cat_by_slug.get('cakes') or cat_by_slug.get('baking')
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name) or _is_r8_variant(base.author_name):
            continue
        new_title = f"Baking-Cakes {base.title}"
        new_slug = f"baking-cakes-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_prep = 25 + (ri % 10)
        new_cook = 35 + (ri % 6)
        new_total = new_prep + new_cook
        new_ings = [
            '1 cup unsalted butter, room temperature',
            '1 3/4 cups granulated sugar',
            '4 large eggs, room temperature',
            '2 tsp vanilla extract',
            '3 cups cake flour (sifted)',
            '1 tbsp baking powder',
            '1/2 tsp fine sea salt',
            '1 1/4 cups whole milk, room temperature',
            f'1 1/2 cups {base.main_ingredient or "fresh berries"} (folded in last)',
            '1/2 cup cream cheese frosting (per slice)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'cakes', 'baking', 'baking-cakes', 'dessert', 'celebration-cake',
            'layer-cake', 'creaming-method',
            cat_slug or 'desserts',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary) | {'vegetarian'})
        img_n = ((ri * 157 + 11) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Cake walkthrough',
            'desc': f"Layer-by-layer photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 163 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 167 + 17) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 173 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 29 + 7) % 720)
        cal = 380 + (ri * 11) % 150
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A celebration-cake interpretation of {base.title}. Creaming-method "
                "batter, alternating dry/wet additions, baked at 350°F to a moist-crumb "
                "tester. Frosted with cream-cheese buttercream while still slightly warm."),
            category_id=(cakes_cat.id if cakes_cat else base.category_id),
            cuisine='American',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='12 slices',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(CAKE_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Sugar': '32g', 'Fat': '16g', 'Carbs': '58g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 79 == 0),
            is_editors_pick=(ri % 101 == 0),
            avg_rating=round(min(5.0, 4.55 + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Baking-Cakes Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='dessert', meal_type='dessert',
            cooking_method='baked',
            main_ingredient='flour',
            occasion='birthday', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 3 days at room temp under a cake dome; refrigerate if frosted with cream-cheese.',
            primary_seasoning='vanilla',
            max_oven_temp=350,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 3 — Pies variant
# ===========================================================================

PIE_INSTRUCTIONS = [
    "Cut very cold butter into the flour until the pieces are pea-sized — visible butter is what makes the crust flaky.",
    "Add ice water one tablespoon at a time until the dough just holds together when pressed; over-hydration = tough crust.",
    "Chill the disc of dough at least 1 hour before rolling — gluten relaxes and the butter re-firms.",
    "Blind-bake the bottom shell with pie weights at 425°F for 15 minutes before adding wet fillings — keeps the bottom crisp.",
    "Drop the oven to 375°F once filling is in and bake until the filling bubbles in the center, not just the edges.",
]


def _seed_pies_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    pies_cat = cat_by_slug.get('pies') or cat_by_slug.get('baking')
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name) or _is_r8_variant(base.author_name):
            continue
        new_title = f"Baking-Pies {base.title}"
        new_slug = f"baking-pies-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_prep = 35 + (ri % 10)
        new_cook = 45 + (ri % 8)
        new_total = new_prep + new_cook + 60  # 1 hr chill
        new_ings = [
            '2 1/2 cups all-purpose flour',
            '1 tsp fine sea salt',
            '1 tsp granulated sugar',
            '1 cup unsalted butter, very cold and cubed',
            '6 tbsp ice water',
            f'4 cups {base.main_ingredient or "sliced apples"} (filling)',
            '3/4 cup granulated sugar',
            '3 tbsp cornstarch',
            '1 tsp ground cinnamon',
            '1 tbsp lemon juice',
            '1 large egg (egg wash)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'pies', 'baking', 'baking-pies', 'dessert',
            'flaky-crust', 'blind-bake',
            cat_slug or 'desserts',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary) | {'vegetarian'})
        img_n = ((ri * 179 + 13) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Pie-crust walkthrough',
            'desc': f"Lattice + blind-bake photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 181 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 191 + 17) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 193 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 31 + 11) % 720)
        cal = 420 + (ri * 13) % 140
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A pie reinterpretation of {base.title}. Cold-butter pie dough "
                "with pea-sized butter pieces, blind-baked at 425°F for a crisp "
                "bottom, finished at 375°F until the filling bubbles in the center."),
            category_id=(pies_cat.id if pies_cat else base.category_id),
            cuisine='American',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='8 slices',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(PIE_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Sugar': '28g', 'Fat': '22g', 'Carbs': '52g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 67 == 0),
            is_editors_pick=(ri % 103 == 0),
            avg_rating=round(min(5.0, 4.6 + ((ri % 13 - 6) * 0.02)), 1),
            review_count=0,
            author_name='Baking-Pies Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='dessert', meal_type='dessert',
            cooking_method='baked',
            main_ingredient='flour',
            occasion='thanksgiving', season='fall',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 2 days at room temp loosely covered; fruit pies refrigerate up to 4 days.',
            primary_seasoning='cinnamon',
            max_oven_temp=425,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 4 — Breads variant
# ===========================================================================

BREAD_INSTRUCTIONS = [
    "Bloom yeast in 110°F water with a pinch of sugar for 5 minutes — if it doesn't foam, the yeast is dead, start over.",
    "Knead until the dough passes the windowpane test: stretch a small piece between your fingers and look for translucent thinness without tearing.",
    "First rise (bulk fermentation) at room temperature until doubled — typically 1-2 hours; cold proof overnight for deeper flavor.",
    "Shape gently to preserve the gas bubbles, then second-proof until a finger-poke leaves a slow-springback dent.",
    "Bake into a preheated 450°F oven with steam (a tray of boiling water) for the first 10 minutes — that's what gives a glossy crust.",
]


def _seed_breads_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    breads_cat = cat_by_slug.get('breads') or cat_by_slug.get('baking')
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name) or _is_r8_variant(base.author_name):
            continue
        new_title = f"Baking-Breads {base.title}"
        new_slug = f"baking-breads-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_prep = 30 + (ri % 10)
        new_cook = 35 + (ri % 6)
        new_total = new_prep + new_cook + 180  # 3 hr proof
        new_ings = [
            '4 cups bread flour',
            '1 1/2 tsp instant yeast',
            '2 tsp fine sea salt',
            '1 1/3 cups water (110°F)',
            '2 tbsp olive oil',
            '1 tbsp honey',
            f'1 cup {base.main_ingredient or "rosemary and sea-salt"} (mixed in)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'breads', 'baking', 'baking-breads',
            'yeasted', 'long-proof', 'crusty-loaf',
            cat_slug or 'baking',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary) | {'vegetarian'})
        img_n = ((ri * 197 + 17) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Bread walkthrough',
            'desc': f"Proof + shape + bake photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 199 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 211 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 223 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 37 + 13) % 720)
        cal = 220 + (ri * 5) % 80
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A yeasted-bread reinterpretation of {base.title}. Bloomed-yeast "
                "start, kneaded to a windowpane, bulk-fermented 2 hours, shaped "
                "gently, baked at 450°F with steam for the glossy crust."),
            category_id=(breads_cat.id if breads_cat else base.category_id),
            cuisine='European',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='1 loaf (12 slices)',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(BREAD_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Sugar': '2g', 'Fat': '3g', 'Carbs': '42g', 'Protein': '7g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 83 == 0),
            is_editors_pick=(ri % 107 == 0),
            avg_rating=round(min(5.0, 4.5 + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Baking-Breads Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='bread', meal_type='side',
            cooking_method='baked',
            main_ingredient='bread-flour',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 2 days cut-side-down on the counter; freeze sliced for up to 3 months.',
            primary_seasoning='salt',
            max_oven_temp=450,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 5 — Pastries variant
# ===========================================================================

PASTRY_INSTRUCTIONS = [
    "Keep your butter cold the entire time — sheet it into a beurrage block and chill until firm but pliable before lamination.",
    "Roll the détrempe (dough) into a long rectangle, place the butter block in the center, and fold over like a letter — single turn.",
    "Chill 30 minutes between every two turns; flour the work surface lightly, brush off excess flour between each fold.",
    "Six single turns total gives ~729 layers; let the laminated dough rest overnight in the fridge before final shaping.",
    "Bake at 400°F until the layers visibly puff and the surface is deep amber — under-baked pastry stays gummy in the center.",
]


def _seed_pastries_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    pastries_cat = cat_by_slug.get('pastries') or cat_by_slug.get('baking')
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name) or _is_r8_variant(base.author_name):
            continue
        new_title = f"Baking-Pastries {base.title}"
        new_slug = f"baking-pastries-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_prep = 60 + (ri % 15)  # lamination takes time
        new_cook = 22 + (ri % 5)
        new_total = new_prep + new_cook + 720  # overnight rest
        new_ings = [
            '4 cups all-purpose flour',
            '1 1/2 tsp fine sea salt',
            '1/4 cup granulated sugar',
            '2 1/4 tsp instant yeast',
            '1 cup whole milk (110°F)',
            '1 large egg + 1 yolk',
            '1 1/2 cups European-style unsalted butter (for lamination)',
            f'3/4 cup {base.main_ingredient or "almond cream"} (filling)',
            '1 large egg (egg wash)',
            '2 tbsp pearl sugar (finish)',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'pastries', 'baking', 'baking-pastries',
            'laminated-dough', 'viennoiserie', 'butter-rich',
            cat_slug or 'baking',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary) | {'vegetarian'})
        img_n = ((ri * 227 + 19) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Lamination walkthrough',
            'desc': f"Beurrage + six-turn lamination photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 229 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 233 + 17) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 239 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 41 + 17) % 720)
        cal = 360 + (ri * 17) % 160
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A laminated-pastry reinterpretation of {base.title}. Beurrage "
                "block + six single turns gives ~729 butter layers; overnight rest "
                "before shaping; baked at 400°F until deep amber and visibly puffed."),
            category_id=(pastries_cat.id if pastries_cat else base.category_id),
            cuisine='French',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='12 pastries',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(PASTRY_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Sugar': '12g', 'Fat': '24g', 'Carbs': '38g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 73 == 0),
            is_editors_pick=(ri % 109 == 0),
            avg_rating=round(min(5.0, 4.6 + ((ri % 13 - 6) * 0.02)), 1),
            review_count=0,
            author_name='Baking-Pastries Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='dessert', meal_type='breakfast',
            cooking_method='baked',
            main_ingredient='butter',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Best the day of; refresh day-old pastries at 300°F for 5 minutes to revive crispness.',
            primary_seasoning='butter',
            max_oven_temp=400,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# R8 chef recipes — Chef Pierre Beaumont (French patisserie classics)
# ===========================================================================

R8_CHEF_RECIPES = [
    ('Chef Pierre Beaumont', 'French-Patisserie', [
        ('Pain au Chocolat',                'pain-au-chocolat-classic',          'pastries', 'French', ['vegetarian'], ['4 cups bread flour', '1 1/2 tsp salt', '1/4 cup sugar', '2 1/4 tsp yeast', '1 cup milk (110°F)', '1 1/2 cups European butter', '24 chocolate batons', '1 egg (wash)'], 90, 22),
        ('Croissant',                       'croissant-classic',                  'pastries', 'French', ['vegetarian'], ['4 cups bread flour', '1 1/2 tsp salt', '1/4 cup sugar', '2 1/4 tsp yeast', '1 cup milk (110°F)', '1 1/2 cups European butter', '1 egg (wash)'], 90, 20),
        ('Éclair au Chocolat',              'eclair-au-chocolat',                 'pastries', 'French', ['vegetarian'], ['1 cup water', '1/2 cup butter', '1 cup flour', '4 eggs', '2 cups crème pâtissière', '6 oz dark chocolate (glaze)', '2 tbsp cream'], 45, 35),
        ('Tarte Tatin',                     'tarte-tatin-classic',                'pies',     'French', ['vegetarian'], ['8 apples', '1 cup sugar', '1/2 cup butter', '1 sheet puff pastry', '1 tsp vanilla', '1 lemon (zest)'], 25, 45),
        ('Mille-Feuille',                   'mille-feuille-vanilla',              'pastries', 'French', ['vegetarian'], ['3 sheets puff pastry', '3 cups crème pâtissière', '1 cup powdered sugar (glaze)', '2 tbsp cocoa (marbling)', '1 tsp vanilla bean paste'], 60, 25),
        ('Madeleines',                      'madeleines-classic',                 'cookies',  'French', ['vegetarian'], ['3 large eggs', '2/3 cup sugar', '1 tsp vanilla', '1 cup flour', '1 tsp baking powder', '1/2 cup butter (browned)', '1 lemon (zest)'], 15, 12),
        ('Macarons Parisiens',              'macarons-parisiens',                 'cookies',  'French', ['vegetarian', 'gluten-free'], ['1 3/4 cups powdered sugar', '1 cup almond flour', '3 egg whites', '1/4 cup granulated sugar', '1 cup buttercream (filling)'], 60, 14),
        ('Crème Brûlée',                    'creme-brulee-classic',               'desserts', 'French', ['vegetarian', 'gluten-free'], ['2 cups heavy cream', '1 vanilla bean', '5 egg yolks', '1/2 cup sugar', '4 tbsp sugar (brûlée top)'], 15, 40),
        ('Profiteroles au Chocolat',        'profiteroles-au-chocolat',           'desserts', 'French', ['vegetarian'], ['1 cup water', '1/2 cup butter', '1 cup flour', '4 eggs', '2 cups vanilla ice cream', '8 oz dark chocolate', '1/2 cup cream'], 35, 30),
        ('Tarte au Citron',                 'tarte-au-citron-meringuee',          'pies',     'French', ['vegetarian'], ['1 pre-baked tart shell', '6 lemons (juice + zest)', '1 1/4 cups sugar', '4 eggs', '1/2 cup butter', '4 egg whites (meringue)', '1/2 cup sugar (meringue)'], 45, 25),
        ('Galette des Rois',                'galette-des-rois-frangipane',        'pastries', 'French', ['vegetarian'], ['2 sheets puff pastry', '1 cup almond cream (frangipane)', '1 fève (charm)', '1 egg (wash)', '2 tbsp simple syrup (glaze)'], 30, 35),
        ('Saint-Honoré',                    'saint-honore',                       'desserts', 'French', ['vegetarian'], ['1 puff pastry disc', '24 choux puffs', '2 cups caramel', '3 cups Chantilly cream', '2 cups crème pâtissière'], 90, 25),
        ('Paris-Brest',                     'paris-brest',                        'pastries', 'French', ['vegetarian'], ['1 cup water', '1/2 cup butter', '1 cup flour', '4 eggs', '3 cups praline mousseline', '1/4 cup sliced almonds', '2 tbsp powdered sugar'], 60, 30),
        ('Kouign-Amann',                    'kouign-amann-breton',                'pastries', 'French', ['vegetarian'], ['4 cups flour', '1 1/2 tsp salt', '1 1/2 tsp yeast', '1 cup water', '1 cup European butter (lamination)', '1 cup sugar (folded in)'], 75, 28),
    ]),
]


def _seed_r8_chef_recipes(cat_by_slug, existing_slugs):
    added = 0
    for ci, (chef, cuisine_label, dishes) in enumerate(R8_CHEF_RECIPES):
        for di, dish in enumerate(dishes):
            (title, slug, cat_slug, cuisine, dietary, ings, prep, cook) = dish
            if slug in existing_slugs:
                continue
            cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('baking')
            existing_slugs.add(slug)
            total = max(1, prep + cook)
            ri = ci * 100 + di
            img_n = ((ri * 281 + 53) % IMAGE_POOL_SIZE) + 1
            feature_tags = [
                cat_slug, cuisine.lower(), 'chef-special', 'patisserie',
                f'chef-{_slugify(chef.replace("Chef ", ""))}',
            ] + list(dietary)
            gallery = [{
                'title': 'Chef walkthrough',
                'desc': f"Step-by-step photos of {title} by {chef}.",
                'images': [
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 283 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 293 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 307 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                ],
            }]
            created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 19 + 13) % 720)
            calories = 380 + (ri * 19) % 220
            avg_rating = round(4.6 + (ri % 5) * 0.05, 1)
            rec = Recipe(
                title=title, slug=slug,
                description=(
                    f"{chef}'s signature {title} — a {cuisine_label.lower()} classic "
                    "cooked with patisserie technique and uncompromised butter."),
                category_id=cat.id if cat else None, cuisine=cuisine,
                image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
                prep_time=_fmt_mins(prep), cook_time=_fmt_mins(cook),
                total_time=_fmt_mins(total),
                servings='8',
                calories=calories,
                ingredients_json=json.dumps(ings),
                instructions_json=json.dumps([
                    f"Read the {title} recipe top to bottom; patisserie rewards mise en place.",
                    f"Stage every ingredient at the correct temperature — cold butter for lamination, warm milk for yeast.",
                    f"Follow {chef}'s laminating / piping / blind-bake step exactly; rushing kills the texture.",
                    f"Finish with the traditional French garnish — powdered sugar, glaze, or pearl sugar as listed.",
                    "Serve fresh that day; day-old can be refreshed at 300°F for 5 minutes.",
                ]),
                nutrition_json=json.dumps({'Calories': str(calories), 'Protein': '7g', 'Fat': '22g', 'Carbs': '46g'}),
                tags_json=json.dumps(feature_tags),
                gallery_json=json.dumps(gallery),
                is_featured=(ri % 11 == 0),
                is_editors_pick=(ri % 17 == 0),
                avg_rating=avg_rating,
                review_count=0,
                author_name=chef,
                prep_time_mins=prep, cook_time_mins=cook, total_time_mins=total,
                ingredient_count=len(ings),
                dietary_tags_json=json.dumps(dietary),
                dish_type=cat_slug, meal_type='dessert',
                cooking_method='baked',
                main_ingredient='butter',
                occasion='', season='',
                feature_tags=json.dumps(feature_tags),
                latest_review_text='',
                storage_instructions=f"Best fresh; refresh at 300°F for 5 minutes to revive crisp layers.",
                primary_seasoning='vanilla', max_oven_temp=400,
                created_at=created,
            )
            db.session.add(rec)
            added += 1
    return added


# ===========================================================================
# Public entry point — called from seed_data.seed_extended_catalog after R7.
# ===========================================================================

R8_SENTINEL_SLUG = 'pain-au-chocolat-classic'


def run_r8_polish(cat_by_slug):
    """R8 top-level. Returns a counts dict."""
    if (Recipe.query.filter_by(slug=R8_SENTINEL_SLUG).first()
            or Recipe.query.filter_by(slug='baking-cookies-classic-waffles').first()):
        return {'skipped': True}

    counts = {}

    # 1) Baking sub-categories first so chef recipes + variants can attach to them.
    counts['categories'] = _seed_baking_subcategories(cat_by_slug)
    db.session.flush()
    cat_by_slug.update({c.slug: c for c in Category.query.all()})

    # 2) Chef Pierre patisserie classics — small set, before variants
    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['r8_chef'] = _seed_r8_chef_recipes(cat_by_slug, existing_recipe_slugs)
    db.session.flush()

    # 3) Variant passes — base = Test Kitchen recipes not already R6/R7/R8.
    # Subsample by step 8 -> ~1040 per pass × 5 = ~5200 new.
    base_for_r8 = (Recipe.query
                   .filter(Recipe.author_name.like('%Test Kitchen%'))
                   .order_by(Recipe.id)
                   .all())
    base_for_r8 = [r for r in base_for_r8
                   if not _is_r6_variant(r.author_name)
                   and not _is_r7_variant(r.author_name)
                   and not _is_r8_variant(r.author_name)]
    base_for_r8 = base_for_r8[::8]
    print(f"[r8_seed] base_for_r8 size: {len(base_for_r8)}")

    counts['cookies'] = _seed_cookies_variants(cat_by_slug, base_for_r8, existing_recipe_slugs)
    db.session.flush()
    counts['cakes'] = _seed_cakes_variants(cat_by_slug, base_for_r8, existing_recipe_slugs)
    db.session.flush()
    counts['pies'] = _seed_pies_variants(cat_by_slug, base_for_r8, existing_recipe_slugs)
    db.session.flush()
    counts['breads'] = _seed_breads_variants(cat_by_slug, base_for_r8, existing_recipe_slugs)
    db.session.flush()
    counts['pastries'] = _seed_pastries_variants(cat_by_slug, base_for_r8, existing_recipe_slugs)
    db.session.flush()

    return counts
