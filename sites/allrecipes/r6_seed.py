"""R6 polish seed — additional variant passes + new chefs + edge-case data.

Runs AFTER R5 inside ``seed_data.seed_extended_catalog``. Everything in
here is deterministic so a rebuild from source is byte-identical to the
shipped ``instance_seed/allrecipes.db``.

R6 deliverables (recipes 8434 -> 12000+):
  * 4 new variant passes — copycat-restaurant, budget-friendly,
    holiday-entertaining, air-fryer-shortcut — each operating on the
    full Test Kitchen base (~1000 recipes each, ~4000 new total).
  * 4 new chefs (~50 recipes) broadening cuisine-origin coverage
    (Brazilian, Greek, Vietnamese, Cajun).

Idempotent — gated on the presence of a sentinel R6 recipe slug.
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


# Filter helper: identify any "R6 variant" author so the variant passes
# don't recurse on their own output.
R6_AUTHOR_TOKENS = (
    'Copycat-Restaurant', 'Budget-Friendly', 'Holiday-Entertaining',
    'Air-Fryer-Shortcut',
)


def _is_r6_variant(author_name: str) -> bool:
    return any(tok in (author_name or '') for tok in R6_AUTHOR_TOKENS)


def _cat_slug_for(base, cat_by_slug):
    if not base.category_id:
        return None
    for slug, c in cat_by_slug.items():
        if c.id == base.category_id:
            return slug
    return None


# ===========================================================================
# Pass 1 — Copycat Restaurant variants
# ===========================================================================

COPYCAT_INSTRUCTIONS = [
    "Read the original menu item once, then plan the kitchen flow: cold prep first, then the main protein, sauce, and plating components last.",
    "Mise en place every ingredient before turning the heat on — the restaurant version is fast because the prep is done.",
    "Cook the protein to the doneness the restaurant menu calls out: medium for steaks, just-set for fish, golden for breaded items.",
    "Build the sauce with one clear flavor axis the restaurant is known for (smoky / garlicky / citrus / umami) — don't muddy it.",
    "Plate exactly the way the restaurant does — height in the center, sauce around or under the protein, never on top of the crisp parts.",
]


def _seed_copycat_variants(cat_by_slug, base_recipes, existing_slugs):
    """Restaurant-style copycat variant for every eligible base recipe."""
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_title = f"Copycat-Restaurant {base.title}"
        new_slug = f"copycat-restaurant-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(15, base_prep + 5)
        new_cook = max(15, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '1 tbsp finishing butter (for the restaurant gloss)',
            '1 squeeze fresh lemon (brightens at the pass)',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'copycat-restaurant', 'restaurant-style', 'menu-recreation',
            'restaurant-copycat', cat_slug or 'dinner']))
        img_n = ((ri * 113 + 7) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Restaurant-style photos',
            'desc': f"Plating walkthrough for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 131 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 137 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 149 + 37) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 31 + 19) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A copycat-restaurant version of {base.title}. Built from the "
                "techniques that make a chain restaurant's menu item taste consistent: "
                "tight mise en place, a single sauce axis, and proper finishing butter."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=base.calories or 420,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(COPYCAT_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '420'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 67 == 0),
            is_editors_pick=(ri % 89 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Copycat-Restaurant Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method,
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Best eaten same day; reheat low and gentle to keep crust intact.',
            primary_seasoning=base.primary_seasoning or '',
            max_oven_temp=base.max_oven_temp or 0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 2 — Budget-friendly variants
# ===========================================================================

BUDGET_INSTRUCTIONS = [
    "Shop the recipe with a price list — pantry staples first, fresh produce second, protein last. Use what you already have.",
    "Substitute the most expensive ingredient with a thrifty equivalent (e.g. ground chuck for sirloin, cabbage for kale, pearl barley for orzo).",
    "Stretch the protein with beans, lentils, or rice — aim for half the meat called for in the original.",
    "Cook in large enough batches that lunches the next day are free; the per-portion cost halves once leftovers are counted.",
    "Garnish smart: a quick pickle of any leftover crisp veg adds restaurant-grade brightness for pennies.",
]


def _seed_budget_variants(cat_by_slug, base_recipes, existing_slugs):
    """Budget-friendly variant for every eligible base recipe."""
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_title = f"Budget-Friendly {base.title}"
        new_slug = f"budget-friendly-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(10, base_prep)
        new_cook = max(15, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '1 cup cooked rice or 1 can rinsed beans (to stretch the protein)',
            '1 tbsp vinegar (for the quick-pickle garnish)',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'budget-friendly', 'budget', 'thrifty', 'pantry-staples',
            'cheap-eats', cat_slug or 'dinner']))
        img_n = ((ri * 127 + 11) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Budget-friendly photos',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 139 + 5) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 151 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 163 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 23 + 7) % 720)
        cal = max(280, (base.calories or 400) - 30)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A budget-friendly version of {base.title}. Same flavor, half the "
                "grocery receipt: pantry staples first, expensive proteins stretched "
                "with beans or rice. Lunches the next day are free."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '6',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(BUDGET_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 71 == 0),
            is_editors_pick=(ri % 101 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.3) + ((ri % 9 - 4) * 0.02)), 1),
            review_count=0,
            author_name='Budget-Friendly Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method,
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 4 days in the fridge; doubles down as next-day lunch.',
            primary_seasoning=base.primary_seasoning or '',
            max_oven_temp=base.max_oven_temp or 0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 3 — Holiday-entertaining variants
# ===========================================================================

HOLIDAY_INSTRUCTIONS = [
    "Build the menu around one show-piece dish — this one — and keep everything else on the table simple so the host can actually sit down.",
    "Scale to a crowd: double the protein, but leave aromatics and dairy at 1.5x so the seasoning stays balanced.",
    "Do the prep the night before. Sauces, marinades, and braises all improve in the fridge overnight; same-day work is just the bake.",
    "Garnish with seasonal greenery (rosemary, thyme, citrus zest) at the table — entertaining is half visual.",
    "Plate family-style on one large platter — it photographs better and lets guests serve themselves while the host pours wine.",
]


def _seed_holiday_entertaining_variants(cat_by_slug, base_recipes, existing_slugs):
    """Holiday-entertaining variant for every eligible base recipe."""
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_title = f"Holiday-Entertaining {base.title}"
        new_slug = f"holiday-entertaining-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(20, base_prep + 10)
        new_cook = max(25, base_cook + 10)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '2 sprigs fresh rosemary (table garnish)',
            '1 tbsp flaky sea salt (for finishing at the table)',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'holiday-entertaining', 'holiday', 'entertaining', 'crowd-feeding',
            'show-piece', 'party-menu', cat_slug or 'dinner']))
        img_n = ((ri * 167 + 19) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Holiday-entertaining photos',
            'desc': f"Plating walkthrough for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 173 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 179 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 191 + 43) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 37 + 11) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A holiday-entertaining version of {base.title}. Built to feed 8-12 "
                "with most of the prep done the night before — so the host can pour "
                "wine, take the photo, and actually sit down with the guests."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='10',
            calories=base.calories or 450,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(HOLIDAY_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '450'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 47 == 0),
            is_editors_pick=(ri % 73 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.5) + ((ri % 13 - 6) * 0.02)), 1),
            review_count=0,
            author_name='Holiday-Entertaining Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method,
            main_ingredient=base.main_ingredient,
            occasion='Holiday Entertaining', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Prep components up to 24 hours ahead; assemble and reheat the day of.',
            primary_seasoning=base.primary_seasoning or '',
            max_oven_temp=base.max_oven_temp or 350,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 4 — Air-fryer-shortcut variants
# ===========================================================================

AIR_FRYER_INSTRUCTIONS = [
    "Preheat the air fryer to 375°F for 3 minutes — the basket needs to be hot when the food goes in or the surface won't crisp.",
    "Toss the protein or vegetable in 2 tsp neutral oil and salt; lay in a single layer with at least 1/4 inch of space between pieces.",
    "Cook at 375°F for 8 to 12 minutes, shaking the basket halfway through. Smaller pieces (cubed) need 8; larger (whole fillets) need 12.",
    "Check doneness by texture: the surface should sound hollow when tapped and bounce back gently when pressed.",
    "Rest for 2 minutes on a wire rack — that final rest is what locks the crust in. Skipping it leaves the bottom soggy.",
]


def _seed_air_fryer_shortcut_variants(cat_by_slug, base_recipes, existing_slugs):
    """Air-fryer-shortcut variant for every eligible base recipe."""
    skip_cats = {'soups', 'salads'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        if cat_slug in skip_cats:
            continue
        new_title = f"Air-Fryer-Shortcut {base.title}"
        new_slug = f"air-fryer-shortcut-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep - 5)
        new_cook = max(8, min(15, int(base_cook * 0.5)))
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '2 tsp neutral oil (avocado or grapeseed — high smoke point)',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'air-fryer-shortcut', 'air-fryer', 'shortcut', 'quick',
            'weeknight', 'under-30-min', cat_slug or 'dinner']))
        img_n = ((ri * 181 + 11) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Air-fryer photos',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 193 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 197 + 17) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 211 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 41 + 13) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"An air-fryer-shortcut version of {base.title}. Half the cook time, "
                "all the crust — preheat the basket, single layer, shake halfway, rest on "
                "a wire rack so the crust locks in. Weeknight-fast."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=max(220, (base.calories or 380) - 50),
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(AIR_FRYER_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '330'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 53 == 0),
            is_editors_pick=(ri % 97 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 7 - 3) * 0.02)), 1),
            review_count=0,
            author_name='Air-Fryer-Shortcut Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method='air-fryer',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Re-crisp in the air fryer at 350°F for 2 minutes the next day.',
            primary_seasoning=base.primary_seasoning or '',
            max_oven_temp=375,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# R6 chef recipes — 4 new chefs broadening cuisine-origin coverage.
# ===========================================================================

R6_CHEF_RECIPES = [
    ('Chef Beatriz Almeida', 'Brazilian', [
        ('Feijoada Completa',                   'feijoada-completa',                  'main-dishes', 'Brazilian', [],                          ['1 lb black beans', '8 oz smoked pork ribs', '6 oz linguica sausage', '4 oz salt-cured pork', '2 onions', '4 cloves garlic', '2 bay leaves', '4 cups stock'], 25, 180),
        ('Pao de Queijo',                       'pao-de-queijo-brazilian-cheese',     'breads',      'Brazilian', ['gluten-free', 'vegetarian'], ['2 cups tapioca flour', '1 cup whole milk', '1/2 cup neutral oil', '1 tsp salt', '2 large eggs', '1.5 cups grated minas or parmesan'], 15, 25),
        ('Brigadeiros',                         'brigadeiros-brazilian-truffles',     'desserts',    'Brazilian', ['gluten-free', 'vegetarian'], ['1 can (14 oz) sweetened condensed milk', '2 tbsp unsweetened cocoa powder', '1 tbsp butter', '1/2 cup chocolate sprinkles'], 10, 15),
        ('Moqueca de Peixe',                    'moqueca-de-peixe-fish-stew',         'seafood',     'Brazilian', ['gluten-free', 'pescatarian', 'dairy-free'], ['2 lb white fish fillets', '1 can coconut milk', '2 tbsp dende palm oil', '2 bell peppers', '2 tomatoes', '1 bunch cilantro'], 20, 35),
        ('Coxinha de Frango',                   'coxinha-de-frango-teardrop',         'appetizers',  'Brazilian', [],                          ['1 lb shredded chicken', '2 cups chicken stock', '2 cups flour', '4 oz cream cheese', '2 cups breadcrumbs', '2 eggs', 'Oil for frying'], 40, 30),
        ('Picanha Grelhada',                    'picanha-grelhada-grilled-rump',      'beef',        'Brazilian', ['gluten-free', 'dairy-free'], ['2.5 lb picanha (top sirloin cap)', '2 tbsp rock salt', 'Wood charcoal'], 10, 30),
        ('Acaraje',                             'acaraje-black-eyed-pea-fritter',     'appetizers',  'Brazilian', ['vegetarian'], ['2 cups dried black-eyed peas', '1 onion', '1 cup palm oil', '1 tsp salt', 'Shrimp filling (optional)'], 30, 20),
        ('Pudim de Leite',                      'pudim-de-leite-flan',                'desserts',    'Brazilian', ['vegetarian', 'gluten-free'], ['1 can sweetened condensed milk', '1 cup whole milk', '3 large eggs', '1 cup sugar (for caramel)'], 15, 60),
        ('Vatapa',                              'vatapa-shrimp-bread-stew',           'seafood',     'Brazilian', ['pescatarian'], ['1 lb shrimp', '4 slices stale bread', '1 can coconut milk', '1/2 cup roasted peanuts', '1/2 cup palm oil', '1 onion'], 20, 30),
        ('Quindim',                             'quindim-coconut-custard',            'desserts',    'Brazilian', ['vegetarian', 'gluten-free'], ['8 egg yolks', '1 cup sugar', '1 cup grated coconut', '2 tbsp butter'], 15, 45),
        ('Pao de Mel',                          'pao-de-mel-honey-cake',              'desserts',    'Brazilian', ['vegetarian'], ['1.5 cups flour', '1/2 cup honey', '1/2 cup brown sugar', '1 tbsp cocoa', '1/2 cup milk', '1 tsp baking powder', '1 cup dark chocolate (coating)'], 20, 25),
        ('Empadinha de Palmito',                'empadinha-de-palmito',               'appetizers',  'Brazilian', ['vegetarian'], ['2 cups flour', '1 cup butter', '1 can hearts of palm', '1 onion', '2 tbsp tomato paste', '1 egg (wash)'], 25, 30),
    ]),
    ('Chef Eleni Stavros', 'Greek', [
        ('Moussaka',                            'moussaka-greek-eggplant-bake',       'main-dishes', 'Greek', [],                              ['3 large eggplants', '1.5 lb ground lamb', '2 onions', '4 cloves garlic', '2 cups bechamel', '1 cup grated kefalotyri', '1 can crushed tomatoes', '1 tsp cinnamon'], 30, 75),
        ('Spanakopita',                         'spanakopita-spinach-feta-pie',       'appetizers',  'Greek', ['vegetarian'],                  ['1 lb spinach', '8 oz feta', '4 oz ricotta', '1 onion', '1 lb phyllo dough', '1 cup butter (melted)', '2 large eggs', '1 tbsp dill'], 30, 45),
        ('Avgolemono Soup',                     'avgolemono-soup-greek-egg-lemon',    'soups',       'Greek', ['gluten-free'],                 ['8 cups chicken stock', '1 cup orzo or rice', '3 large eggs', '1/3 cup fresh lemon juice', '2 cups shredded chicken'], 10, 30),
        ('Souvlaki Pork Skewers',               'souvlaki-pork-skewers',              'pork',        'Greek', ['gluten-free', 'dairy-free'],   ['2 lb pork shoulder', '1/3 cup olive oil', '3 cloves garlic', '1 lemon (juiced)', '1 tbsp dried oregano', '1 tsp salt'], 20, 15),
        ('Greek Salad Choriatiki',              'greek-salad-choriatiki',             'salads',      'Greek', ['vegetarian', 'gluten-free'],   ['4 tomatoes', '1 cucumber', '1/2 red onion', '1 cup kalamata olives', '8 oz feta', '1/4 cup olive oil', '1 tbsp dried oregano'], 15, 0),
        ('Baklava',                             'baklava-honey-walnut-pastry',        'desserts',    'Greek', ['vegetarian'],                  ['1 lb phyllo dough', '4 cups walnuts', '1 cup butter (melted)', '1 cup sugar', '1 cup honey', '1 cinnamon stick', '1 lemon'], 45, 60),
        ('Dolmades Stuffed Grape Leaves',       'dolmades-stuffed-grape-leaves',      'appetizers',  'Greek', ['vegetarian', 'dairy-free'],    ['1 jar grape leaves', '1 cup rice', '1 onion', '1/2 cup pine nuts', '1 lemon', '1/4 cup olive oil', '2 tbsp fresh dill'], 30, 45),
        ('Tzatziki Sauce',                      'tzatziki-cucumber-yogurt-dip',       'appetizers',  'Greek', ['vegetarian', 'gluten-free'],   ['2 cups Greek yogurt', '1 cucumber', '3 cloves garlic', '1 tbsp olive oil', '1 tbsp lemon juice', '1 tbsp fresh dill'], 10, 0),
        ('Gyro Lamb',                           'gyro-lamb-with-tzatziki',            'lamb',        'Greek', [],                              ['1.5 lb ground lamb', '1 onion', '3 cloves garlic', '1 tbsp oregano', '1 tsp cumin', '4 pita breads', '1 cup tzatziki'], 15, 35),
        ('Pastitsio Greek Lasagna',             'pastitsio-greek-lasagna',            'pasta',       'Greek', [],                              ['1 lb bucatini', '1.5 lb ground beef', '1 can crushed tomatoes', '2 cups bechamel', '1 cup grated kefalotyri', '1 tsp cinnamon'], 30, 60),
        ('Galaktoboureko',                      'galaktoboureko-semolina-custard',    'desserts',    'Greek', ['vegetarian'],                  ['1 lb phyllo dough', '4 cups milk', '1 cup semolina', '4 eggs', '1.5 cups sugar', '1 cup butter (melted)', '1 lemon (syrup)'], 25, 50),
        ('Octopus Grilled with Lemon Oregano',  'octopus-grilled-lemon-oregano',      'seafood',     'Greek', ['gluten-free', 'pescatarian', 'dairy-free'], ['2.5 lb octopus', '1/4 cup olive oil', '1 lemon', '1 tbsp dried oregano', '2 tbsp red wine vinegar'], 15, 90),
    ]),
    ('Chef Linh Tran', 'Vietnamese', [
        ('Pho Bo',                              'pho-bo-vietnamese-beef-noodle',      'soups',       'Vietnamese', ['dairy-free'],            ['2 lb beef bones', '1 lb beef brisket', '1 onion (charred)', '1 piece ginger (charred)', '5 star anise', '1 cinnamon stick', '6 cloves', '1 lb rice noodles', 'Thai basil, bean sprouts (garnish)'], 25, 240),
        ('Banh Mi Sandwich',                    'banh-mi-pork-sandwich',              'sandwiches',  'Vietnamese', ['dairy-free'],            ['1 baguette', '8 oz cha lua (Vietnamese ham)', '4 oz pork liver pate', '1 carrot', '1 daikon', '1 cucumber', '1 bunch cilantro', '2 jalapenos', 'Maggi seasoning'], 20, 0),
        ('Goi Cuon Fresh Spring Rolls',         'goi-cuon-fresh-spring-rolls',        'appetizers',  'Vietnamese', ['gluten-free', 'pescatarian', 'dairy-free'], ['12 rice paper wrappers', '1/2 lb shrimp', '4 oz pork belly', '4 oz vermicelli noodles', '1 head butter lettuce', '1 bunch mint', '1 bunch cilantro'], 25, 0),
        ('Bun Cha Hanoi',                       'bun-cha-hanoi-grilled-pork',         'main-dishes', 'Vietnamese', ['dairy-free'],            ['1.5 lb pork shoulder', '1/2 lb ground pork (patties)', '1/4 cup fish sauce', '2 tbsp sugar', '4 cloves garlic', '1 lb rice vermicelli', 'Carrot-daikon pickle', 'Herb plate'], 30, 25),
        ('Ca Kho To Caramel Catfish',           'ca-kho-to-caramel-catfish',          'seafood',     'Vietnamese', ['gluten-free', 'pescatarian', 'dairy-free'], ['2 lb catfish steaks', '1/3 cup palm sugar', '3 tbsp fish sauce', '1 tbsp ground pepper', '1 shallot', '1 chili'], 15, 35),
        ('Cha Gio Fried Spring Rolls',          'cha-gio-fried-spring-rolls',         'appetizers',  'Vietnamese', ['dairy-free'],            ['1 lb ground pork', '4 oz wood ear mushrooms', '4 oz bean thread noodles', '1 carrot', '1 onion', '20 spring roll wrappers', 'Oil for frying'], 30, 20),
        ('Banh Xeo Sizzling Crepe',             'banh-xeo-sizzling-crepe',            'main-dishes', 'Vietnamese', ['dairy-free', 'gluten-free'], ['2 cups rice flour', '1 can coconut milk', '1 tsp turmeric', '8 oz pork belly', '1/2 lb shrimp', '1 cup bean sprouts', 'Lettuce wraps + herbs'], 25, 30),
        ('Com Tam Broken Rice',                 'com-tam-broken-rice-grilled-pork',   'main-dishes', 'Vietnamese', ['gluten-free', 'dairy-free'], ['2 cups broken rice', '1.5 lb pork chops', '3 tbsp fish sauce', '3 tbsp sugar', '4 cloves garlic', '1 cucumber'], 20, 25),
        ('Che Ba Mau Three-Color Dessert',      'che-ba-mau-three-color-dessert',     'desserts',    'Vietnamese', ['gluten-free', 'vegan'],  ['1 cup mung beans', '1 cup red beans', '1 cup pandan jelly', '1 can coconut milk', '1/2 cup sugar'], 30, 60),
        ('Bo Kho Beef Stew',                    'bo-kho-vietnamese-beef-stew',        'beef',        'Vietnamese', ['dairy-free'],            ['2.5 lb beef chuck', '4 lemongrass stalks', '2 tbsp fish sauce', '1 can coconut water', '4 carrots', '1 tbsp curry powder', '1 cinnamon stick'], 25, 150),
        ('Banh Cuon Steamed Rice Rolls',        'banh-cuon-steamed-rice-rolls',       'appetizers',  'Vietnamese', ['dairy-free'],            ['2 cups rice flour', '1/4 cup tapioca starch', '8 oz ground pork', '4 oz wood ear mushrooms', '1 shallot', '1/4 cup fried shallots'], 30, 25),
        ('Goi Ga Vietnamese Chicken Salad',     'goi-ga-vietnamese-chicken-salad',    'salads',      'Vietnamese', ['gluten-free', 'dairy-free'], ['1.5 lb poached chicken', '1/2 head cabbage', '1 carrot', '1 onion', '1 bunch mint', '1 bunch cilantro', '1/4 cup fish sauce dressing', '1/4 cup roasted peanuts'], 20, 0),
    ]),
    ('Chef Marcel Boudreaux', 'Cajun', [
        ('Gumbo Ya-Ya',                         'gumbo-ya-ya-chicken-andouille',      'soups',       'Cajun', ['dairy-free'],                ['1.5 lb chicken thighs', '1 lb andouille sausage', '1 cup flour (roux)', '1 cup oil (roux)', '2 onions', '2 bell peppers', '4 celery stalks', '8 cups chicken stock', '1 tsp file powder'], 30, 120),
        ('Jambalaya',                           'jambalaya-cajun-rice',               'main-dishes', 'Cajun', ['dairy-free'],                ['1 lb shrimp', '1 lb andouille sausage', '1 lb chicken', '2 cups rice', '1 can crushed tomatoes', '1 onion', '2 bell peppers', '4 cups stock', '2 tbsp Cajun seasoning'], 20, 45),
        ('Crawfish Etouffee',                   'crawfish-etouffee-cajun-stew',       'seafood',     'Cajun', ['pescatarian'],               ['2 lb crawfish tails', '1/2 cup butter', '1/3 cup flour', '1 onion', '2 bell peppers', '3 celery stalks', '2 cups seafood stock', '2 tbsp Cajun seasoning', '1 cup rice'], 25, 35),
        ('Red Beans and Rice',                  'red-beans-and-rice-monday',          'main-dishes', 'Cajun', ['dairy-free'],                ['1 lb red kidney beans', '1 lb smoked ham hock', '8 oz andouille', '1 onion', '2 bell peppers', '3 celery stalks', '8 cups stock', '2 cups rice'], 15, 180),
        ('Po Boy Sandwich Shrimp',              'po-boy-sandwich-fried-shrimp',       'sandwiches',  'Cajun', [],                            ['1 lb shrimp', '1 cup buttermilk', '1.5 cups cornmeal', '4 baguette rolls', '1 head lettuce', '2 tomatoes', '1/2 cup remoulade'], 20, 12),
        ('Boudin Sausage',                      'boudin-rice-sausage',                'pork',        'Cajun', ['dairy-free'],                ['1 lb pork shoulder', '8 oz pork liver', '1 cup cooked rice', '1 onion', '1 bell pepper', '1 tbsp Cajun seasoning', '4 ft hog casing'], 60, 60),
        ('Maque Choux',                         'maque-choux-corn-saute',             'side-dishes', 'Cajun', ['vegetarian', 'gluten-free'], ['6 ears corn', '1 onion', '1 bell pepper', '4 tbsp butter', '1/2 cup heavy cream', '2 tomatoes', '1 tsp Cajun seasoning'], 15, 25),
        ('Pralines',                            'pralines-louisiana-pecan',           'desserts',    'Cajun', ['vegetarian', 'gluten-free'], ['2 cups pecans', '1 cup brown sugar', '1 cup white sugar', '1/2 cup heavy cream', '4 tbsp butter', '1 tsp vanilla'], 10, 25),
        ('Dirty Rice',                          'dirty-rice-cajun',                   'side-dishes', 'Cajun', ['dairy-free'],                ['1 lb ground beef', '4 oz chicken livers', '2 cups rice', '1 onion', '1 bell pepper', '3 celery stalks', '2 cups stock', '2 tbsp Cajun seasoning'], 15, 45),
        ('Cajun Catfish Blackened',             'cajun-catfish-blackened',            'seafood',     'Cajun', ['gluten-free', 'pescatarian'], ['4 catfish fillets', '4 tbsp butter', '2 tbsp paprika', '1 tbsp cayenne', '1 tsp thyme', '1 tsp oregano', '1 tsp garlic powder'], 5, 8),
        ('Hush Puppies',                        'hush-puppies-cornmeal-fritters',     'appetizers',  'Cajun', ['vegetarian'],                ['1.5 cups cornmeal', '1/2 cup flour', '1 onion', '1 cup buttermilk', '1 egg', '1 tsp baking powder', 'Oil for frying'], 10, 10),
        ('King Cake',                           'king-cake-mardi-gras',               'desserts',    'Cajun', ['vegetarian'],                ['4 cups flour', '1/2 cup sugar', '1 packet yeast', '1 cup warm milk', '4 eggs', '1 cup butter', '2 tsp cinnamon', '1 cup pecans', 'Purple/green/gold sugars'], 40, 35),
    ]),
]


def _seed_r6_chef_recipes(cat_by_slug, existing_slugs):
    added = 0
    for ci, (chef, cuisine_label, dishes) in enumerate(R6_CHEF_RECIPES):
        for di, dish in enumerate(dishes):
            (title, slug, cat_slug, cuisine, dietary, ings, prep, cook) = dish
            if slug in existing_slugs:
                continue
            cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('main-dishes')
            existing_slugs.add(slug)
            total = max(1, prep + cook)
            ri = ci * 100 + di
            img_n = ((ri * 239 + 41) % IMAGE_POOL_SIZE) + 1
            feature_tags = [
                cat_slug, cuisine.lower().replace(' ', '-'), 'chef-special',
                f'chef-{_slugify(chef.replace("Chef ", ""))}',
            ] + list(dietary)
            gallery = [{
                'title': 'Chef walkthrough',
                'desc': f"Step-by-step photos of {title} by {chef}.",
                'images': [
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 241 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 251 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 257 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
                ],
            }]
            created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 13 + 7) % 720)
            calories = 320 + (ri * 13) % 280
            avg_rating = round(4.4 + (ri % 7) * 0.05, 1)
            rec = Recipe(
                title=title, slug=slug,
                description=(
                    f"{chef}'s signature {title} — a {cuisine_label.lower()} classic "
                    "served the way it's meant to be: traditional technique, "
                    "uncompromised seasoning, plated for the dinner table."),
                category_id=cat.id if cat else None, cuisine=cuisine,
                image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
                prep_time=_fmt_mins(prep), cook_time=_fmt_mins(cook),
                total_time=_fmt_mins(total),
                servings='4',
                calories=calories,
                ingredients_json=json.dumps(ings),
                instructions_json=json.dumps([
                    f"Read through the full recipe for {title} once before starting; this is a chef's recipe, prep first.",
                    f"Bring all ingredients to room temperature — important especially for the {cuisine_label} flavor base.",
                    f"Follow {chef}'s technique for the primary cooking step; do not rush it.",
                    f"Finish at the table with the traditional {cuisine_label} garnish (see ingredient list).",
                    f"Serve immediately while the textures are at their peak; leftovers are best the next day after the flavors meld.",
                ]),
                nutrition_json=json.dumps({'Calories': str(calories), 'Protein': '24g', 'Fat': '15g', 'Carbs': '32g'}),
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
                dish_type=cat_slug, meal_type='dinner',
                cooking_method='',
                main_ingredient=cat_slug,
                occasion='', season='',
                feature_tags=json.dumps(feature_tags),
                latest_review_text='',
                storage_instructions=f"Stores 3 days in the fridge; reheat gently to preserve the {cuisine_label} texture.",
                primary_seasoning='', max_oven_temp=0,
                created_at=created,
            )
            db.session.add(rec)
            added += 1
    return added


# ===========================================================================
# Enrichment — top up "more-like-this" features for the new R6 rows so
# the recipe detail page can compute related-by-tag matches.
# ===========================================================================

def _enrich_r6_more_like_features(*, sentinel_check=True):
    """Pure mutation: append a small 'more-like' tag bucket on every recipe
    so detail-page recommendations have something rich to query against."""
    if sentinel_check:
        sentinel = Recipe.query.filter_by(slug='moqueca-de-peixe-fish-stew').first()
        if not sentinel:
            return 0
    touched = 0
    for r in Recipe.query.order_by(Recipe.id).all():
        try:
            feats = json.loads(r.feature_tags or '[]')
        except Exception:
            feats = []
        if not isinstance(feats, list):
            feats = []
        # Derive a stable bucket key for "more like this" matching:
        # combo of meal_type + main_ingredient + cuisine.
        bucket = []
        if r.meal_type:
            bucket.append(f'mealtype-{_slugify(r.meal_type)}')
        if r.main_ingredient:
            bucket.append(f'mainingr-{_slugify(r.main_ingredient)}')
        if r.cuisine:
            bucket.append(f'cuisine-{_slugify(r.cuisine)}')
        # Don't double-write if already present.
        before = list(feats)
        for tag in bucket:
            if tag not in feats:
                feats.append(tag)
        if feats != before:
            r.feature_tags = json.dumps(feats)
            r.tags_json = json.dumps(feats)
            touched += 1
    return touched


# ===========================================================================
# Public entry point — called from seed_data.seed_extended_catalog after R5
# ===========================================================================

R6_SENTINEL_SLUG = 'feijoada-completa'


def run_r6_polish(cat_by_slug):
    """R6 top-level. Returns a counts dict."""
    if (Recipe.query.filter_by(slug=R6_SENTINEL_SLUG).first()
            or Recipe.query.filter_by(slug='copycat-restaurant-pancakes').first()):
        return {'skipped': True}

    counts = {}

    # 1) R6 chef recipes first so they're available for "same chef" wiring.
    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['r6_chef'] = _seed_r6_chef_recipes(cat_by_slug, existing_recipe_slugs)
    db.session.flush()

    # 2) Variant passes — base = all Test Kitchen recipes that are NOT R6 own.
    base_for_r6 = (Recipe.query
                   .filter(Recipe.author_name.like('%Test Kitchen%'))
                   .order_by(Recipe.id)
                   .all())
    base_for_r6 = [r for r in base_for_r6 if not _is_r6_variant(r.author_name)]
    # Deterministic sub-sample so total adds reach the R6 target (+~4000)
    # without ballooning the DB. ::6 yields ~1100-1300 entries × 4 passes
    # = ~4500 new recipes -> 8434 + ~4500 = ~13000.
    base_for_r6 = base_for_r6[::6]
    print(f"[r6_seed] base_for_r6 size: {len(base_for_r6)}")

    counts['copycat'] = _seed_copycat_variants(cat_by_slug, base_for_r6, existing_recipe_slugs)
    db.session.flush()
    counts['budget'] = _seed_budget_variants(cat_by_slug, base_for_r6, existing_recipe_slugs)
    db.session.flush()
    counts['holiday_entertaining'] = _seed_holiday_entertaining_variants(cat_by_slug, base_for_r6, existing_recipe_slugs)
    db.session.flush()
    counts['air_fryer_shortcut'] = _seed_air_fryer_shortcut_variants(cat_by_slug, base_for_r6, existing_recipe_slugs)
    db.session.flush()

    # 3) Enrich every recipe with more-like bucket tags.
    counts['enrich_more_like'] = _enrich_r6_more_like_features()
    db.session.flush()

    return counts
