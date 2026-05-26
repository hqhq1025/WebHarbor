"""Extended catalog seed for the Allrecipes mirror.

Loads ~600 real recipes from `scraped_data/themealdb.json` (TheMealDB
public API, https://www.themealdb.com/api.php) on top of the
hand-curated recipes already seeded by ``seed_database`` in ``app.py``.

The function is idempotent — gated by the presence of a sentinel
category slug ('british') — so re-running it after a populated DB is a
true no-op. This is what keeps `/reset/allrecipes` byte-identical.

What it adds:
  * 14 new categories (cuisine + meal-type, e.g. british, french,
    indian, vegetarian, vegan, beef, pork, lamb, side-dishes,
    slow-cooker, mediterranean, american, salad, kid-friendly).
    Combined with the 14 seeded by ``seed_database`` → 28 total.
  * ~500+ recipes parsed from TheMealDB (slug-collision deduped).
  * ~20 reviewer users with a pinned bcrypt hash (cannot log in;
    placeholder for FK integrity) and ~6-20 reviews per popular recipe,
    generated through a seeded ``random.Random(42)`` so byte-for-byte
    output is stable.

All time fields use a fixed ``MIRROR_REFERENCE_DATE`` to avoid
``datetime.utcnow()`` drift that would break byte-identical reset.
"""
from __future__ import annotations

import json
import os
import re
import random
import unicodedata
from datetime import datetime, timedelta

from sqlalchemy import text

from app import (
    app, db,
    Category, Recipe, User, Review,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPED = os.path.join(BASE_DIR, 'scraped_data')
IMAGES_DIR_REL = '/static/images/recipes_real'
IMAGE_POOL_SIZE = 219  # recipe_1.jpg … recipe_219.jpg

# Fixed reference date so created_at is stable across seed runs.
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)

# Pinned bcrypt hash for the dummy reviewer password. We use the
# canonical hash from the berkeley mirror (test1234) so the value is
# byte-identical across mirrors. These reviewers are not intended to
# log in — they exist purely to attach reviews to a user_id FK.
REVIEWER_PINNED_HASH = (
    '$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i'
)


# ---------------------------------------------------------------------------
# Categories to add (combined with the 14 from seed_database → 28+ total)
# ---------------------------------------------------------------------------

NEW_CATEGORIES = [
    # name,                 slug,             desc,                                                                                  parent_type, order
    ('British',             'british',        'Classic British comfort food, from full breakfasts to fish and chips.',               'cuisine',  15),
    ('French',              'french',         'French classics: from buttery croissants to coq au vin and crème brûlée.',            'cuisine',  16),
    ('Indian',              'indian',         'Fragrant curries, biryanis, dals, and tandoori favorites from across India.',         'cuisine',  17),
    ('Chinese',             'chinese',        'Stir-fries, dumplings, and savory classics from Sichuan, Cantonese, and beyond.',     'cuisine',  18),
    ('Japanese',            'japanese',       'Sushi, ramen, donburi and other Japanese favorites at home.',                          'cuisine',  19),
    ('Thai',                'thai',           'Bright, fragrant Thai curries, stir-fries, and noodle bowls.',                          'cuisine',  20),
    ('Mediterranean',       'mediterranean',  'Olive oil, herbs, seafood, grains — the freshness of the Mediterranean.',              'cuisine',  21),
    ('American',            'american',       'BBQ, casseroles, burgers, and the most-loved American comfort dishes.',                'cuisine',  22),
    ('Beef',                'beef',           'Steaks, stews, roasts, and ground-beef weeknight winners.',                              'ingredient', 23),
    ('Pork',                'pork',           'Pork chops, ribs, tenderloin and all things bacon.',                                     'ingredient', 24),
    ('Lamb',                'lamb',           'Slow-roasted lamb shanks, kebabs, stews and curries.',                                   'ingredient', 25),
    ('Vegetarian',          'vegetarian',     'Meat-free mains and sides packed with flavor.',                                          'meal',     26),
    ('Vegan',               'vegan',          'Fully plant-based recipes that don\'t skimp on taste.',                                  'meal',     27),
    ('Side Dishes',         'side-dishes',    'Roasted vegetables, grain bowls, and the perfect dinner sides.',                         'meal',     28),
    ('Slow Cooker',         'slow-cooker',    'Set-it-and-forget-it slow cooker recipes for busy days.',                                'meal',     29),
    # ---- R3: dietary lifestyle categories ----
    ('Keto',                'keto',           'Low-carb, high-fat keto recipes that keep you in ketosis without sacrificing flavor.',  'diet',     30),
    ('Paleo',               'paleo',          'Grain-free, dairy-free paleo recipes built on whole foods our ancestors would recognize.','diet',     31),
    ('Low-Carb',            'low-carb',       'Sub-30g-carb meals that still satisfy: zoodles, cauliflower rice, lettuce wraps.',       'diet',     32),
    ('Gluten-Free',         'gluten-free',    'Naturally gluten-free recipes and clever swaps for breads, pastas, and desserts.',       'diet',     33),
    ('Dairy-Free',          'dairy-free',     'Creamy, comforting recipes without a drop of dairy — coconut, oat, and cashew based.',   'diet',     34),
    ('Whole30',             'whole30',        'Strict-compliant Whole30 recipes: no sugar, grain, legume, dairy or alcohol.',           'diet',     35),
    ('Low-GI',              'low-gi',         'Low glycemic index meals that keep blood sugar steady — great for diabetics and energy.','diet',     36),
    ('Pescatarian',         'pescatarian',    'Fish-and-veggie focused recipes for pescatarian meal planning.',                          'diet',     37),
    # ---- R3: occasion / seasonal collections ----
    ('Thanksgiving',        'thanksgiving',   'Turkey, stuffing, sweet potato, pumpkin pie — the full Thanksgiving spread.',             'occasion', 38),
    ('Christmas',           'christmas',      'Holiday cookies, prime rib, roast goose, eggnog and yule logs.',                          'occasion', 39),
    ('Easter',              'easter',         'Spring ham, lamb, deviled eggs, hot cross buns and carrot cake.',                          'occasion', 40),
    ('Valentine\'s Day',    'valentines',     'Heart-shaped, chocolate-dipped, candlelit-dinner-worthy recipes.',                         'occasion', 41),
    ('4th of July',         'fourth-of-july', 'Backyard BBQ classics: burgers, ribs, slaw, watermelon, and apple pie.',                   'occasion', 42),
    ('Halloween',           'halloween',      'Spooky treats, pumpkin everything, and party-friendly finger foods.',                      'occasion', 43),
    ('Super Bowl',          'super-bowl',     'Dips, wings, sliders and chili built for game-day crowds.',                                'occasion', 44),
    ('Mother\'s Day',       'mothers-day',    'Brunch favorites, baked goods and impressive-looking but easy mains.',                     'occasion', 45),
]


# TheMealDB.strCategory -> our category slug (priority for category_id).
MEALDB_CATEGORY_TO_SLUG = {
    'Beef': 'beef',
    'Chicken': 'chicken',
    'Dessert': 'desserts',
    'Lamb': 'lamb',
    'Miscellaneous': 'dinner',
    'Pasta': 'pasta',
    'Pork': 'pork',
    'Seafood': 'seafood',
    'Side': 'side-dishes',
    'Starter': 'appetizers',
    'Vegan': 'vegan',
    'Vegetarian': 'vegetarian',
    'Breakfast': 'breakfast',
    'Goat': 'lamb',
}


# TheMealDB.strArea (cuisine) -> our cuisine display string (verbatim
# in Recipe.cuisine). Some areas also map to a cuisine category slug
# below for richer browsing.
AREA_TO_CUISINE_DISPLAY = {
    'American': 'American',  'British': 'British',     'Canadian': 'American',
    'Chinese': 'Chinese',     'Croatian': 'Mediterranean',
    'Dutch': 'European',      'Egyptian': 'Mediterranean',
    'Filipino': 'Asian',      'France': 'French',       'French': 'French',
    'Greek': 'Mediterranean', 'India': 'Indian',        'Indian': 'Indian',
    'Irish': 'British',       'Italian': 'Italian',
    'Jamaican': 'Caribbean',  'Japanese': 'Japanese',
    'Kenyan': 'African',      'Malaysian': 'Asian',
    'Mexican': 'Mexican',     'Moroccan': 'Mediterranean',
    'Netherlands': 'European','Norway': 'European',
    'Polish': 'European',     'Portuguese': 'Mediterranean',
    'Russian': 'European',    'Spanish': 'Mediterranean',
    'Thai': 'Thai',           'Tunisian': 'Mediterranean',
    'Turkish': 'Mediterranean','Ukrainian': 'European',
    'United States': 'American',
    'Vietnamese': 'Asian',    'Norwegian': 'European',
    'Algerian': 'Mediterranean','Argentina': 'Latin American',
    'Argentinian': 'Latin American',
    'Australian': 'Australian','Belgian': 'European',
    'Saudi Arabian': 'Middle Eastern',
    'Slovakia': 'European',   'Slovakian': 'European',
    'Uruguayan': 'Latin American','Venezuela': 'Latin American',
    'Venezuelan': 'Latin American',
    'Syrian': 'Middle Eastern',
}


# Recipe titles (lowercased word) -> reviewer-facing tag bucket. Used
# only to scatter dietary_tags so /category/healthy and /category/vegan
# pull in real candidates.
VEGAN_HINTS = {'vegan', 'lentil', 'tofu', 'tempeh'}
VEG_HINTS = {'vegetarian', 'spinach', 'mushroom', 'eggplant', 'paneer',
             'chickpea', 'quinoa', 'bean', 'cabbage'}
GF_HINTS = {'gluten-free', 'quinoa', 'rice', 'polenta'}

# Carbohydrate-light protein-forward titles → keto/low-carb signal.
KETO_HINTS = {'keto', 'fathead', 'bunless', 'cauliflower rice', 'zoodle',
              'lettuce wrap'}
LOW_CARB_HINTS = {'low-carb', 'cauliflower', 'zucchini', 'wrap', 'frittata',
                  'omelette', 'omelet'}
# Paleo: protein + veg, no grain/legume/dairy.
PALEO_HINTS = {'paleo', 'whole30'}
# Dairy-free indicators (these dishes are typically dairy-free).
DAIRY_FREE_HINTS = {'dairy-free', 'coconut milk', 'almond milk',
                    'vegan', 'vinaigrette'}
# Whole30 needs to be strict — only flag if explicit.
WHOLE30_HINTS = {'whole30', 'whole 30'}
# Low-GI: complex carbs, legumes, oats, quinoa, sweet potato.
LOW_GI_HINTS = {'oat', 'lentil', 'quinoa', 'sweet potato', 'chickpea',
                'barley', 'bean', 'low-gi', 'low gi'}
# Pescatarian fish-forward.
PESCATARIAN_HINTS = {'salmon', 'tuna', 'cod', 'shrimp', 'fish', 'prawn',
                     'mussel', 'oyster', 'crab', 'lobster', 'sardine',
                     'mackerel', 'tilapia'}
# Holiday seasonality from title/ingredient text.
HOLIDAY_KEYWORDS = {
    'thanksgiving': ['turkey', 'cranberry', 'stuffing', 'pumpkin', 'sweet potato'],
    'christmas': ['gingerbread', 'eggnog', 'fruitcake', 'roast', 'prime rib', 'yule'],
    'easter': ['easter', 'ham', 'hot cross', 'lamb'],
    'valentines': ['chocolate', 'strawberry', 'red velvet', 'heart'],
    'fourth-of-july': ['barbecue', 'bbq', 'burger', 'hot dog', 'watermelon', 'corn on the cob'],
    'halloween': ['pumpkin', 'caramel apple', 'cupcake'],
    'super-bowl': ['wings', 'dip', 'nachos', 'chili', 'slider'],
    'mothers-day': ['brunch', 'quiche', 'scone', 'pancake', 'frittata'],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    s = re.sub(r"[^a-zA-Z0-9]+", '-', s.lower()).strip('-')
    return s or 'recipe'


def _load_mealdb():
    p = os.path.join(SCRAPED, 'themealdb.json')
    if not os.path.exists(p):
        return []
    try:
        with open(p) as f:
            return json.load(f)
    except Exception as exc:
        print(f"[seed_extended] failed to read themealdb.json: {exc}")
        return []


def _parse_ingredients(meal: dict) -> list[str]:
    out = []
    for i in range(1, 21):
        name = (meal.get(f'strIngredient{i}') or '').strip()
        if not name:
            continue
        measure = (meal.get(f'strMeasure{i}') or '').strip()
        if measure:
            out.append(f"{measure} {name}".strip())
        else:
            out.append(name)
    return out


def _parse_instructions(meal: dict) -> list[str]:
    raw = (meal.get('strInstructions') or '').strip()
    if not raw:
        return ['Combine all ingredients and cook until done.']
    # TheMealDB often uses "STEP N\n" headings or raw \r\n separators.
    raw = re.sub(r"^STEP\s*\d+\s*", '', raw, flags=re.IGNORECASE | re.MULTILINE)
    # Split on blank lines or newlines
    parts = [p.strip() for p in re.split(r"\r?\n+", raw) if p.strip()]
    # Drop leading "step N" markers within lines
    cleaned = []
    for p in parts:
        p = re.sub(r"^step\s*\d+\W*", '', p, flags=re.IGNORECASE).strip()
        if p:
            cleaned.append(p)
    if not cleaned:
        cleaned = [raw]
    # If only 1 huge blob, split on sentence boundaries (keep punctuation)
    if len(cleaned) == 1 and len(cleaned[0]) > 400:
        cleaned = re.split(r"(?<=[.!?])\s+(?=[A-Z])", cleaned[0])
        cleaned = [c.strip() for c in cleaned if c.strip()]
    return cleaned[:25]


def _estimate_times(meal: dict) -> tuple[int, int, int]:
    """Heuristic prep/cook/total minutes based on category & instructions."""
    cat = (meal.get('strCategory') or '').lower()
    instr_len = len((meal.get('strInstructions') or ''))
    base_cook = {
        'beef': 75, 'lamb': 90, 'pork': 60, 'chicken': 40,
        'seafood': 25, 'pasta': 25, 'side': 30, 'starter': 20,
        'breakfast': 15, 'dessert': 45, 'vegan': 35, 'vegetarian': 35,
        'miscellaneous': 35, 'goat': 90,
    }.get(cat, 35)
    prep = 15 + (instr_len // 600) * 5
    prep = min(prep, 45)
    cook = base_cook + (instr_len // 800) * 5
    cook = min(cook, 240)
    total = prep + cook
    return prep, cook, total


def _fmt_mins(m: int) -> str:
    if m < 60:
        return f"{m} mins"
    h, rem = divmod(m, 60)
    return f"{h} hr" if rem == 0 else f"{h} hr {rem} mins"


def _calories_estimate(category: str, ingredients_n: int) -> int:
    base = {'desserts': 340, 'beef': 520, 'pork': 470, 'lamb': 510,
            'chicken': 360, 'seafood': 320, 'pasta': 480, 'side-dishes': 220,
            'appetizers': 210, 'breakfast': 290, 'vegan': 280,
            'vegetarian': 330, 'dinner': 410}.get(category, 360)
    return base + ingredients_n * 8


def _dietary_tags(title: str, category_slug: str, area: str) -> list[str]:
    t = title.lower()
    tags = []
    if category_slug == 'vegan' or any(w in t for w in VEGAN_HINTS):
        tags.append('vegan')
    if category_slug == 'vegetarian' or any(w in t for w in VEG_HINTS):
        tags.append('vegetarian')
    if any(w in t for w in GF_HINTS):
        tags.append('gluten-free')
    if any(w in t for w in KETO_HINTS):
        tags.append('keto')
        tags.append('low-carb')
    if any(w in t for w in LOW_CARB_HINTS) and 'pasta' not in t:
        if 'low-carb' not in tags:
            tags.append('low-carb')
    if any(w in t for w in PALEO_HINTS):
        tags.append('paleo')
    if any(w in t for w in WHOLE30_HINTS):
        tags.append('whole30')
    if any(w in t for w in DAIRY_FREE_HINTS):
        if 'dairy-free' not in tags:
            tags.append('dairy-free')
    if 'vegan' in tags and 'dairy-free' not in tags:
        tags.append('dairy-free')
    if any(w in t for w in LOW_GI_HINTS):
        tags.append('low-gi')
    if any(w in t for w in PESCATARIAN_HINTS) or category_slug == 'seafood':
        tags.append('pescatarian')
    # De-dupe but preserve order.
    seen = set()
    deduped = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    return deduped


def _holiday_for(title: str, category_slug: str) -> str:
    """Return holiday slug if title matches a seasonal keyword, else ''."""
    t = title.lower()
    for hol, kws in HOLIDAY_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                return hol
    return ''


def _meal_type_for(category_slug: str, title: str) -> str:
    t = title.lower()
    if category_slug == 'breakfast' or 'breakfast' in t or 'pancake' in t:
        return 'breakfast'
    if category_slug == 'desserts':
        return 'dessert'
    if category_slug == 'appetizers' or 'snack' in t or 'dip' in t:
        return 'snack'
    if category_slug == 'side-dishes':
        return 'side'
    if 'salad' in t or 'sandwich' in t:
        return 'lunch'
    return 'dinner'


def _dish_type_for(category_slug: str, title: str) -> str:
    if category_slug == 'desserts':
        return 'dessert'
    if category_slug == 'appetizers':
        return 'appetizer'
    if category_slug == 'side-dishes':
        return 'side'
    if 'salad' in title.lower():
        return 'salad'
    if 'soup' in title.lower() or 'stew' in title.lower():
        return 'soup'
    return 'main'


def _main_ingredient_for(category_slug: str) -> str:
    return {
        'beef': 'beef', 'pork': 'pork', 'lamb': 'lamb',
        'chicken': 'chicken', 'seafood': 'seafood',
        'pasta': 'pasta', 'vegetarian': 'vegetables',
        'vegan': 'vegetables',
    }.get(category_slug, '')


def _cooking_method(instructions_text: str) -> str:
    t = instructions_text.lower()
    if 'slow cooker' in t or 'crock pot' in t:
        return 'slow cooker'
    if 'grill' in t:
        return 'grilled'
    if 'fry' in t or 'fried' in t:
        return 'fried'
    if 'roast' in t:
        return 'roasted'
    if 'bake' in t or 'oven' in t:
        return 'baked'
    if 'simmer' in t or 'boil' in t:
        return 'stovetop'
    return ''


# ---------------------------------------------------------------------------
# Variant recipes (Slow Cooker / Air Fryer / Grilled / 30-Minute / Easy)
# ---------------------------------------------------------------------------
# Allrecipes.com is full of appliance/method-specific variants of the same
# core dish ("Slow Cooker Beef Stew", "Air Fryer Chicken Wings", "Grilled
# Honey Garlic Salmon", etc.). To double the catalog without inventing
# fictional dishes, we deterministically derive one variant per base
# recipe, modulated by category. Ingredients reuse the base; instructions
# are a templated cookware-specific wrapper.

VARIANT_RULES = {
    # category_slug -> (variant_prefix, variant_slug_prefix, cooking_method,
    #                   prep_delta, cook_factor, instr_template_key)
    'beef':         ('Slow Cooker',     'slow-cooker',  'slow cooker', 5,  3.0,  'slow_cooker'),
    'pork':         ('Slow Cooker',     'slow-cooker',  'slow cooker', 5,  3.0,  'slow_cooker'),
    'lamb':         ('Slow Cooker',     'slow-cooker',  'slow cooker', 5,  3.0,  'slow_cooker'),
    'chicken':      ('Air Fryer',       'air-fryer',    'air fryer',  -3,  0.6,  'air_fryer'),
    'seafood':      ('Grilled',         'grilled',      'grilled',    -2,  0.5,  'grilled'),
    'pasta':        ('30-Minute',       '30-minute',    'stovetop',   -5,  0.5,  'thirty_min'),
    'vegetarian':   ('Easy Weeknight',  'easy-weeknight','stovetop',  -3,  0.7,  'easy_weeknight'),
    'vegan':        ('30-Minute',       '30-minute',    'stovetop',   -5,  0.6,  'thirty_min'),
    'side-dishes':  ('Air Fryer',       'air-fryer',    'air fryer',  -2,  0.6,  'air_fryer'),
    'appetizers':   ('Easy Party',      'easy-party',   'baked',       0,  0.8,  'easy_weeknight'),
    'breakfast':    ('Easy Make-Ahead', 'easy-make-ahead','stovetop', -2,  0.9,  'easy_weeknight'),
    'desserts':     ('No-Bake',         'no-bake',      'no-bake',     5,  0.0,  'no_bake'),
    'dinner':       ('Slow Cooker',     'slow-cooker',  'slow cooker', 5,  2.5,  'slow_cooker'),
}


# Second variant rule set — diet-flavored adaptations. Every eligible base
# yields a SECOND variant (after the appliance/method variant above) so the
# catalog grows by another ~Nbase entries. Each diet variant is force-tagged
# with the appropriate dietary_tags so /diet/<slug> pages pull real candidates.
DIET_VARIANT_RULES = {
    # category_slug -> (variant_prefix, slug_prefix, method, prep_delta, cook_factor,
    #                   instr_template_key, primary_diet_tag, extra_tags, target_category_slug)
    'beef':         ('Keto',                  'keto',                 'pan-seared', 0,  1.0,  'easy_weeknight', 'keto',         ['low-carb','gluten-free','dairy-free'], 'keto'),
    'pork':         ('Whole30',               'whole30',              'roasted',     0,  1.0,  'easy_weeknight', 'whole30',      ['paleo','gluten-free','dairy-free'],    'whole30'),
    'lamb':         ('Paleo',                 'paleo',                'roasted',     2,  1.0,  'easy_weeknight', 'paleo',        ['gluten-free','dairy-free','whole30'],  'paleo'),
    'chicken':      ('Paleo',                 'paleo',                'baked',       0,  1.0,  'easy_weeknight', 'paleo',        ['gluten-free','dairy-free'],            'paleo'),
    'seafood':      ('Mediterranean Pescatarian','mediterranean-pescatarian','baked',0,1.0,  'easy_weeknight', 'pescatarian',  ['mediterranean','low-gi'],               'pescatarian'),
    'pasta':        ('Gluten-Free',           'gluten-free',          'stovetop',    0,  1.0,  'thirty_min',     'gluten-free',  [],                                       'gluten-free'),
    'vegetarian':   ('Vegan',                 'vegan',                'stovetop',    0,  1.0,  'easy_weeknight', 'vegan',        ['vegetarian','dairy-free'],              'vegan'),
    'vegan':        ('Whole30',               'whole30',              'roasted',     0,  1.0,  'easy_weeknight', 'whole30',      ['paleo','gluten-free','dairy-free'],    'whole30'),
    'side-dishes':  ('Dairy-Free',            'dairy-free',           'roasted',     0,  1.0,  'easy_weeknight', 'dairy-free',   [],                                       'dairy-free'),
    'appetizers':   ('Low-Carb',              'low-carb',             'baked',       0,  1.0,  'easy_weeknight', 'low-carb',     ['keto','gluten-free'],                   'low-carb'),
    'breakfast':    ('Low-GI',                'low-gi',               'stovetop',    0,  1.0,  'easy_weeknight', 'low-gi',       ['high-fiber'],                           'low-gi'),
    'desserts':     ('Gluten-Free',           'gluten-free',          'baked',       0,  1.0,  'no_bake',        'gluten-free',  ['low-sugar'],                            'gluten-free'),
    'dinner':       ('Whole30',               'whole30',              'baked',       0,  1.0,  'easy_weeknight', 'whole30',      ['paleo','gluten-free','dairy-free'],    'whole30'),
}


# Third variant rule set — cuisine-restaurant-style remixes for a handful
# of popular categories. Generates ANOTHER pass of variants from
# the eligible bases (mod 2 == 0) → roughly +Nbase/2 more recipes.
CUISINE_VARIANT_RULES = {
    'beef':         ('Restaurant-Style Steakhouse','restaurant-style','seared',     5,  1.1, 'easy_weeknight', 'American'),
    'pork':         ('Cajun-Style',                'cajun-style',     'pan-seared', 5,  1.1, 'easy_weeknight', 'American'),
    'chicken':      ('Tuscan-Style Creamy',        'tuscan-style',    'stovetop',   5,  1.0, 'thirty_min',     'Italian'),
    'seafood':      ('Thai-Inspired',              'thai-inspired',   'stovetop',   5,  0.9, 'thirty_min',     'Thai'),
    'pasta':        ('Restaurant-Style Italian',   'restaurant-italian','stovetop', 5,  1.0, 'thirty_min',     'Italian'),
    'vegetarian':   ('Indian-Spiced',              'indian-spiced',   'stovetop',   5,  1.1, 'easy_weeknight', 'Indian'),
    'vegan':        ('Mediterranean-Style',        'mediterranean-style','stovetop',5, 1.0, 'easy_weeknight', 'Mediterranean'),
    'desserts':     ('French-Style',               'french-style',    'baked',      5,  1.1, 'no_bake',        'French'),
    'breakfast':    ('Brunch-Style Cafe',          'brunch-style',    'stovetop',   5,  1.0, 'easy_weeknight', 'American'),
    'appetizers':   ('Spanish Tapas-Style',        'spanish-tapas',   'baked',      5,  1.0, 'easy_weeknight', 'Mediterranean'),
    'side-dishes':  ('Korean-Inspired',            'korean-inspired', 'stovetop',   5,  0.9, 'easy_weeknight', 'Asian'),
    'lamb':         ('Moroccan-Spiced',            'moroccan-spiced', 'roasted',    10, 1.2, 'easy_weeknight', 'Mediterranean'),
    'dinner':       ('Japanese-Style',             'japanese-style',  'stovetop',   5,  1.0, 'thirty_min',     'Japanese'),
}


# Fourth pass — time-budget speed variants (15-min / 20-min) for breakfast,
# appetizers, side-dishes, vegan and vegetarian categories. Gives task
# authors lots of "find a recipe under 20 minutes" candidates.
SPEED_VARIANT_RULES = {
    'breakfast':    ('5-Ingredient Quick',  '5-ingredient',    5,   5,  'easy_weeknight'),
    'appetizers':   ('20-Minute',           '20-minute',       10, 10,  'easy_weeknight'),
    'side-dishes':  ('15-Minute',           '15-minute',       5,  10,  'easy_weeknight'),
    'vegan':        ('15-Minute',           '15-minute',       5,  10,  'thirty_min'),
    'vegetarian':   ('20-Minute',           '20-minute',       10, 10,  'easy_weeknight'),
    'pasta':        ('20-Minute One-Pot',   '20-minute-one-pot',5, 15,  'thirty_min'),
    'seafood':      ('15-Minute Skillet',   '15-minute-skillet',5,10,   'thirty_min'),
    'chicken':      ('20-Minute Skillet',   '20-minute-skillet',5,15,   'thirty_min'),
    'desserts':     ('5-Ingredient',        '5-ingredient',    5,  10,  'no_bake'),
}


INSTRUCTION_TEMPLATES = {
    'slow_cooker': [
        "Brown the meat in a skillet with a tablespoon of oil over medium-high heat, 4 to 5 minutes per side, then transfer to the slow cooker.",
        "Add the remaining ingredients to the slow cooker, stirring to combine.",
        "Cover and cook on LOW for 7 to 8 hours, or on HIGH for 3 to 4 hours, until the meat is fork-tender.",
        "Skim any visible fat from the surface before serving. Adjust seasoning with salt and pepper to taste.",
        "Serve warm over rice, mashed potatoes, or crusty bread.",
    ],
    'air_fryer': [
        "Preheat the air fryer to 380°F (193°C) for 3 minutes.",
        "Toss the main ingredients with oil and seasoning in a large bowl until evenly coated.",
        "Arrange in a single layer in the air fryer basket, working in batches if needed to avoid crowding.",
        "Air fry for 12 to 15 minutes, shaking the basket halfway through, until golden brown and cooked through.",
        "Rest 2 minutes before serving with your favorite dipping sauce.",
    ],
    'grilled': [
        "Preheat an outdoor grill or grill pan to medium-high heat (about 400°F / 204°C). Lightly oil the grates.",
        "Pat the protein dry with paper towels, then rub all over with oil and the seasoning mix.",
        "Grill 3 to 5 minutes per side, depending on thickness, until just cooked through and grill marks form.",
        "Transfer to a plate and tent loosely with foil for 5 minutes to let the juices redistribute.",
        "Serve with a wedge of lemon and fresh herbs.",
    ],
    'thirty_min': [
        "Bring a large pot of well-salted water to a boil for the pasta or grains.",
        "While the water heats, prep all the remaining ingredients so everything is ready to go.",
        "Cook the pasta or grains according to package directions; meanwhile, sauté aromatics in a large skillet over medium-high heat.",
        "Add the remaining ingredients to the skillet and cook 5 to 7 minutes, stirring often, until heated through.",
        "Drain the pasta, reserving 1/4 cup cooking water, then toss everything together. Add reserved water as needed to loosen the sauce. Serve immediately.",
    ],
    'easy_weeknight': [
        "Gather all your ingredients on the counter so you can move quickly once you start cooking.",
        "Heat a large skillet or Dutch oven over medium heat with a glug of olive oil.",
        "Add the aromatics and cook 2 to 3 minutes until fragrant, then add the rest of the ingredients.",
        "Cook, stirring occasionally, until everything is heated through and the flavors have melded, 15 to 20 minutes.",
        "Taste and adjust seasoning. Serve hot, garnished with fresh herbs if you like.",
    ],
    'no_bake': [
        "Line an 8x8-inch baking dish with parchment paper, leaving overhang on two sides for easy lifting.",
        "Combine all the dry ingredients in a large bowl and whisk to remove any lumps.",
        "Gently fold the wet ingredients into the dry mixture until just combined.",
        "Press the mixture firmly into the prepared dish in an even layer.",
        "Refrigerate for at least 4 hours (or overnight) until set. Lift out using the parchment, then slice into squares and serve chilled.",
    ],
}


def _variant_pick_for(category_slug: str, slug_hash: int) -> str | None:
    """Return the variant key for this recipe, or None to skip."""
    if category_slug not in VARIANT_RULES:
        return None
    # Every eligible recipe gets exactly ONE variant (deterministic).
    return category_slug


def _seed_variant_recipes(cat_by_slug, base_recipes):
    """Create deterministic appliance/method variants of every eligible base."""
    added = 0
    existing_slugs = {r.slug for r in Recipe.query.all()}
    for ri, base in enumerate(base_recipes):
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if not base_cat_slug:
            continue
        rule_key = _variant_pick_for(base_cat_slug, ri)
        if not rule_key:
            continue
        prefix, slug_prefix, method, prep_delta, cook_factor, tmpl_key = VARIANT_RULES[rule_key]

        new_title = f"{prefix} {base.title}"
        new_slug = f"{slug_prefix}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)

        # Time math — deterministic.
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep + prep_delta)
        if cook_factor == 0.0:
            new_cook = 0  # no-bake
        else:
            new_cook = max(5, int(round(base_cook * cook_factor)))
        new_total = new_prep + new_cook

        # Reuse ingredients, but tweak the title-of-ingredient list to nod
        # at the appliance/method (deterministic, no random calls).
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings)
        if rule_key in ('beef','pork','lamb','dinner') and 'beef broth' not in ' '.join(new_ings).lower():
            new_ings.append('1 cup beef or chicken broth')
        if rule_key == 'chicken' and 'cooking spray' not in ' '.join(new_ings).lower():
            new_ings.append('Cooking spray, for the basket')
        if rule_key == 'seafood' and 'lemon' not in ' '.join(new_ings).lower():
            new_ings.append('1 lemon, cut into wedges, for serving')
        if rule_key == 'desserts':
            new_ings = new_ings + ['1 1/2 cups graham cracker crumbs',
                                    '1/2 cup unsalted butter, melted']

        # Instructions — adapt to method.
        new_instr = list(INSTRUCTION_TEMPLATES[tmpl_key])
        # Append one base-flavored line so the variant references its parent dish.
        try:
            base_instr = json.loads(base.instructions_json or '[]')
        except Exception:
            base_instr = []
        if base_instr:
            tail = base_instr[0]
            tail_clean = re.sub(r"\s+", ' ', tail).strip()[:200]
            if tail_clean and len(tail_clean) > 40:
                new_instr.append(f"Note from the original recipe: {tail_clean}")

        # Derived numeric fields.
        avg_rating = round(min(5.0, (base.avg_rating or 4.2) + ((ri % 7 - 3) * 0.05)), 1)
        # Don't seed a review count; the review pass below will set it.
        review_count = 0

        # Dietary tags: inherit, plus add a method-flavored tag.
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        method_tag = {
            'slow_cooker': 'slow-cooker',
            'air_fryer': 'air-fryer',
            'grilled': 'grilled',
            'thirty_min': 'quick',
            'easy_weeknight': 'easy',
            'no_bake': 'no-bake',
        }[tmpl_key]

        # feature_tags reuse + variant marker
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        new_features = list(dict.fromkeys(base_features + [method_tag, slug_prefix]))

        description = (
            f"A {prefix.lower()} take on the classic {base.title.lower()}. "
            f"Same flavors, adapted for the {method} so you can have dinner on the table "
            f"with less hands-on time."
        )

        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 5 + 11) % 720)

        # Image — recycle the existing pool with a deterministic offset
        # so a variant has a different image from the base.
        img_n = ((ri * 13 + 47) % IMAGE_POOL_SIZE) + 1
        image = f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg"

        servings_str = base.servings or '4'

        rec = Recipe(
            title=new_title,
            slug=new_slug,
            description=description,
            category_id=base.category_id,
            cuisine=base.cuisine,
            image=image,
            prep_time=_fmt_mins(new_prep),
            cook_time=_fmt_mins(new_cook) if new_cook else '0 mins',
            total_time=_fmt_mins(new_total),
            servings=servings_str,
            calories=base.calories,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(new_instr),
            nutrition_json=base.nutrition_json,
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps([]),
            is_featured=(ri % 31 == 0),
            is_editors_pick=(ri % 53 == 0),
            avg_rating=avg_rating,
            review_count=review_count,
            author_name=f"{prefix} Test Kitchen",
            prep_time_mins=new_prep,
            cook_time_mins=new_cook,
            total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(list(dict.fromkeys(base_dietary + ([method_tag] if method_tag in ('quick','easy') else [])))),
            dish_type=base.dish_type,
            meal_type=base.meal_type,
            cooking_method=method,
            main_ingredient=base.main_ingredient,
            occasion='',
            season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions=(
                'Refrigerate leftovers in an airtight container for up to 4 days. '
                'Reheat gently to preserve texture.'
            ),
            primary_seasoning='',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ---------------------------------------------------------------------------
# R3: second / third / fourth variant passes
# ---------------------------------------------------------------------------

def _seed_diet_variant_recipes(cat_by_slug, base_recipes):
    """Diet-flavored variant per eligible base (keto/paleo/vegan/etc.)."""
    added = 0
    existing_slugs = {r.slug for r in Recipe.query.all()}
    for ri, base in enumerate(base_recipes):
        # Skip variants of variants — only operate on original MealDB/fixture bases.
        if base.author_name and 'Test Kitchen' in base.author_name and (
                'Slow Cooker' in base.author_name or
                'Air Fryer' in base.author_name or
                'Grilled' in base.author_name or
                '30-Minute' in base.author_name or
                'Easy' in base.author_name or
                'No-Bake' in base.author_name):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if not base_cat_slug or base_cat_slug not in DIET_VARIANT_RULES:
            continue
        (prefix, slug_prefix, method, prep_delta, cook_factor,
         tmpl_key, primary_tag, extra_tags, target_cat) = DIET_VARIANT_RULES[base_cat_slug]
        new_title = f"{prefix} {base.title}"
        new_slug = f"{slug_prefix}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep + prep_delta)
        new_cook = max(5, int(round(base_cook * cook_factor))) if cook_factor > 0 else 0
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        diet_swaps = {
            'keto':         ['Substitute cauliflower rice for any rice', 'Use almond flour instead of all-purpose'],
            'paleo':        ['Use coconut aminos instead of soy sauce', 'Substitute ghee or coconut oil for butter'],
            'whole30':      ['Omit any sugar; sweeten with date paste if needed', 'Use compliant coconut aminos for soy sauce'],
            'low-carb':     ['Swap pasta for zucchini noodles', 'Use lettuce wraps instead of buns'],
            'gluten-free':  ['Substitute certified gluten-free flour blend', 'Use tamari instead of regular soy sauce'],
            'dairy-free':   ['Use coconut milk instead of cream', 'Substitute nutritional yeast for parmesan'],
            'vegan':        ['Substitute flax egg (1 tbsp flax + 3 tbsp water) for eggs', 'Use plant-based butter or coconut oil'],
            'low-gi':       ['Use steel-cut oats instead of instant', 'Swap white rice for quinoa or barley'],
            'pescatarian':  ['Keep all the seafood; add extra herbs and a squeeze of lemon', 'Pair with a green salad for a complete meal'],
        }
        new_ings = list(base_ings) + diet_swaps.get(primary_tag, [])
        new_instr = list(INSTRUCTION_TEMPLATES[tmpl_key])
        new_instr.insert(0, f"For a {prefix.lower()}-friendly version of this dish, see the diet-swap notes in the ingredient list.")
        avg_rating = round(min(5.0, (base.avg_rating or 4.2) + ((ri % 5 - 2) * 0.05)), 1)
        target_cat_obj = cat_by_slug.get(target_cat) or cat_by_slug.get(base_cat_slug)
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = list(dict.fromkeys(base_dietary + [primary_tag] + extra_tags))
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        new_features = list(dict.fromkeys(base_features + [primary_tag, slug_prefix] + extra_tags))
        cal_adjust = {
            'keto': 60, 'low-carb': -40, 'paleo': 20, 'whole30': 10,
            'vegan': -60, 'dairy-free': -30, 'gluten-free': 10,
            'low-gi': -40, 'pescatarian': 0,
        }.get(primary_tag, 0)
        new_cal = max(120, (base.calories or 360) + cal_adjust)
        carbs_g = {
            'keto': 6, 'low-carb': 12, 'paleo': 18, 'whole30': 20,
            'vegan': 38, 'dairy-free': 28, 'gluten-free': 32,
            'low-gi': 35, 'pescatarian': 26,
        }.get(primary_tag, 28)
        protein_g = {
            'keto': 32, 'paleo': 30, 'whole30': 30, 'pescatarian': 28,
            'low-carb': 28, 'dairy-free': 22, 'gluten-free': 22,
            'vegan': 18, 'low-gi': 20,
        }.get(primary_tag, 22)
        fat_g = {
            'keto': 28, 'paleo': 20, 'whole30': 18, 'dairy-free': 14,
            'low-carb': 18, 'gluten-free': 14, 'vegan': 12,
            'low-gi': 10, 'pescatarian': 14,
        }.get(primary_tag, 16)
        description = (
            f"A {primary_tag} adaptation of {base.title}. "
            f"All the flavor of the original, retooled with simple swaps so it fits a {primary_tag} eating plan."
        )
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 7 + 5) % 720)
        img_n = ((ri * 17 + 89) % IMAGE_POOL_SIZE) + 1
        image = f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg"
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=description,
            category_id=target_cat_obj.id if target_cat_obj else base.category_id,
            cuisine=base.cuisine, image=image,
            prep_time=_fmt_mins(new_prep),
            cook_time=_fmt_mins(new_cook) if new_cook else '0 mins',
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=new_cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(new_instr),
            nutrition_json=json.dumps({
                'Calories': str(new_cal),
                'Fat': f"{fat_g}g", 'Carbs': f"{carbs_g}g",
                'Protein': f"{protein_g}g",
                'Fiber': f"{4 + ri % 7}g",
                'Sodium': f"{300 + ri * 11 % 400}mg",
            }),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps([]),
            is_featured=(ri % 37 == 0),
            is_editors_pick=(ri % 59 == 0),
            avg_rating=avg_rating,
            review_count=0,
            author_name=f"{prefix} Diet Test Kitchen",
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type=base.dish_type,
            meal_type=base.meal_type,
            cooking_method=method,
            main_ingredient=base.main_ingredient,
            occasion=base.occasion or '',
            season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Store in an airtight container in the fridge for up to 4 days, or freeze for up to 2 months.',
            primary_seasoning='',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


def _seed_cuisine_variant_recipes(cat_by_slug, base_recipes):
    """Restaurant-style cuisine-spin variant for every OTHER eligible base."""
    added = 0
    existing_slugs = {r.slug for r in Recipe.query.all()}
    for ri, base in enumerate(base_recipes):
        if ri % 2 != 0:
            continue
        if base.author_name and any(token in base.author_name for token in (
                'Slow Cooker', 'Air Fryer', 'Grilled', '30-Minute',
                'Easy Weeknight', 'Easy Party', 'Easy Make-Ahead',
                'No-Bake', 'Diet Test', 'Cuisine Test', 'Speed Test')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if not base_cat_slug or base_cat_slug not in CUISINE_VARIANT_RULES:
            continue
        (prefix, slug_prefix, method, prep_delta, cook_factor,
         tmpl_key, cuisine_label) = CUISINE_VARIANT_RULES[base_cat_slug]
        new_title = f"{prefix} {base.title}"
        new_slug = f"{slug_prefix}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep + prep_delta)
        new_cook = max(5, int(round(base_cook * cook_factor)))
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        cuisine_addons = {
            'Italian':       ['1/4 cup grated Parmigiano-Reggiano', '2 tbsp fresh basil, torn'],
            'Mediterranean': ['1/4 cup Kalamata olives, halved', '2 tbsp extra-virgin olive oil', 'Pinch of sumac'],
            'Thai':          ['1 stalk lemongrass, bruised', '2 kaffir lime leaves', '1 tbsp fish sauce'],
            'Indian':        ['1 tsp garam masala', '1/2 tsp turmeric', '1 inch ginger, grated'],
            'French':        ['2 tbsp unsalted butter', '1/4 cup dry white wine', 'Fresh thyme sprigs'],
            'American':      ['2 strips smoky bacon, diced', '1/4 cup BBQ sauce', '1 tsp smoked paprika'],
            'Asian':         ['1 tbsp toasted sesame oil', '1 tbsp gochujang', '1 tsp rice vinegar'],
            'Japanese':      ['2 tbsp mirin', '1 tbsp white miso paste', '1 sheet nori, julienned'],
        }
        new_ings = list(base_ings) + cuisine_addons.get(cuisine_label, [])
        new_instr = list(INSTRUCTION_TEMPLATES[tmpl_key])
        new_instr.append(
            f"Finish with the {cuisine_label.lower()}-inspired garnishes listed below for an authentic restaurant feel.")
        avg_rating = round(min(5.0, (base.avg_rating or 4.3) + ((ri % 9 - 4) * 0.04)), 1)
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        new_features = list(dict.fromkeys(base_features + [slug_prefix, cuisine_label.lower(), 'restaurant-style']))
        description = (
            f"{prefix} take on {base.title} — the cozy classic dressed up with "
            f"{cuisine_label.lower()} flavors for a date-night or weekend dinner."
        )
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 3 + 17) % 720)
        img_n = ((ri * 23 + 113) % IMAGE_POOL_SIZE) + 1
        image = f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg"
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=description,
            category_id=base.category_id,
            cuisine=cuisine_label, image=image,
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=(base.calories or 380) + 20,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(new_instr),
            nutrition_json=base.nutrition_json,
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps([]),
            is_featured=(ri % 41 == 0),
            is_editors_pick=(ri % 67 == 0),
            avg_rating=avg_rating,
            review_count=0,
            author_name=f"{prefix} Cuisine Test Kitchen",
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=method,
            main_ingredient=base.main_ingredient,
            occasion=base.occasion or '', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Best enjoyed fresh. Leftovers keep 2 days refrigerated.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


def _seed_speed_variant_recipes(cat_by_slug, base_recipes):
    """Time-budget speed variants (15-min / 20-min / 5-ingredient) for ~half of eligible bases."""
    added = 0
    existing_slugs = {r.slug for r in Recipe.query.all()}
    for ri, base in enumerate(base_recipes):
        if ri % 2 != 0:
            continue
        if base.author_name and any(token in base.author_name for token in (
                'Slow Cooker', 'Air Fryer', 'Grilled', '30-Minute',
                'Easy Weeknight', 'Easy Party', 'Easy Make-Ahead',
                'No-Bake', 'Diet Test', 'Cuisine Test', 'Speed Test')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if not base_cat_slug or base_cat_slug not in SPEED_VARIANT_RULES:
            continue
        prefix, slug_prefix, prep_cap, cook_cap, tmpl_key = SPEED_VARIANT_RULES[base_cat_slug]
        new_title = f"{prefix} {base.title}"
        new_slug = f"{slug_prefix}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_prep = prep_cap
        new_cook = cook_cap
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        if '5-ingredient' in slug_prefix:
            new_ings = base_ings[:5] if len(base_ings) >= 5 else base_ings + ['Salt and pepper to taste']
        else:
            new_ings = list(base_ings)
        new_instr = list(INSTRUCTION_TEMPLATES[tmpl_key])[:3]
        new_instr.append(f"Serve immediately. Whole dish from prep to plate is about {new_total} minutes.")
        avg_rating = round(min(5.0, (base.avg_rating or 4.4) + ((ri % 5 - 2) * 0.05)), 1)
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        speed_tag = 'quick' if new_total <= 20 else 'easy'
        new_features = list(dict.fromkeys(base_features + [slug_prefix, speed_tag, 'weeknight']))
        description = (
            f"A weeknight-ready {prefix.lower()} version of {base.title}. "
            f"Built for nights when dinner needs to be on the table in {new_total} minutes or less."
        )
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 11 + 31) % 720)
        img_n = ((ri * 29 + 151) % IMAGE_POOL_SIZE) + 1
        image = f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg"
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=description,
            category_id=base.category_id,
            cuisine=base.cuisine, image=image,
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=base.calories or 380,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(new_instr),
            nutrition_json=base.nutrition_json,
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps([]),
            is_featured=False,
            is_editors_pick=(ri % 71 == 0),
            avg_rating=avg_rating,
            review_count=0,
            author_name=f"{prefix} Speed Test Kitchen",
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method='stovetop',
            main_ingredient=base.main_ingredient,
            occasion=base.occasion or '', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Best eaten fresh; leftovers keep 2-3 days refrigerated.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


def _generate_review_pool(rng: random.Random) -> list[tuple[int, str, str]]:
    """Return a fixed pool of (rating, title, body) tuples sampled per recipe."""
    return [
        (5, 'Family loved it!',           'Made this for Sunday dinner and the whole family asked for seconds. Will be in regular rotation.'),
        (5, 'Restaurant quality',         'Hard to believe I made this at home. Followed the recipe exactly and it turned out perfect.'),
        (4, 'Great recipe with tweaks',    'Solid base recipe — I added an extra clove of garlic and a pinch of red pepper flakes.'),
        (5, 'Better than the original',    'I have tried similar dishes before but this version has the best balance of flavors.'),
        (4, 'Comforting and easy',         'Comfort food at its best. Easy enough for a weeknight and impressive enough for guests.'),
        (5, 'New favorite',                'Going into my permanent recipe box. Thanks for sharing!'),
        (3, 'Good, not great',             'Pleasant flavors but I had to bump up the seasoning a lot. Worth a try.'),
        (5, 'Crowd pleaser',               'Brought this to a potluck and there were no leftovers. Several people asked for the recipe.'),
        (4, 'Will make again',             'A keeper. The leftovers reheated nicely the next day.'),
        (5, 'Five star meal',              'Restaurant-worthy and not difficult at all. The instructions were clear and easy to follow.'),
        (4, 'Perfect for meal prep',       'Made a double batch for the week. Portions out beautifully and freezes well.'),
        (5, 'Delicious flavor',            'The seasoning combination is spot on. Highly recommend trying this exactly as written first.'),
        (4, 'Solid weeknight option',      'Ready in under 45 minutes start to finish. Used pantry staples mostly.'),
        (5, 'Best version I have tried',   'I have tried 3 other recipes for this dish and this one is hands-down the best.'),
        (3, 'Needs more flavor',           'A bit bland for my taste. Added extra garlic and lemon zest and it was much better.'),
        (5, 'Beautiful presentation',      'Looks just like the photo. Plated it nicely and served to dinner guests who were impressed.'),
        (4, 'Kid-approved',                'My picky eaters cleaned their plates. That is the highest praise in our house.'),
        (5, 'Authentic taste',             'Tastes just like what my grandmother used to make. Brought back wonderful memories.'),
        (4, 'Great as written',            'Did not change a thing and it turned out beautifully. Will trust this recipe again.'),
        (5, 'Perfect every time',          'I have made this at least five times now and it always turns out great.'),
    ]


# ---------------------------------------------------------------------------
# Benchmark-fixture recipes
# ---------------------------------------------------------------------------
# `seed_benchmark_users` in app.py populates RecipeBoxItem / MealPlanItem
# rows by looking recipes up via title fragment. Several fragments in
# that list are not satisfied by the 26 hand-curated recipes in
# `seed_database`, so we insert minimal placeholders here BEFORE that
# function runs (we are called from app.py in that order).

BENCHMARK_FIXTURE_RECIPES = [
    # (title,                                          slug,                                       category_slug,  cuisine,           dietary,   main_ing)
    ('Easy Vegetarian Spinach Lasagna',                'easy-vegetarian-spinach-lasagna',          'pasta',        'Italian',         ['vegetarian'], 'pasta'),
    ('Mushroom and Spinach Vegetarian Lasagna',        'mushroom-spinach-vegetarian-lasagna',      'pasta',        'Italian',         ['vegetarian'], 'pasta'),
    ('Classic Vegetarian Lasagna',                     'classic-vegetarian-lasagna',               'pasta',        'Italian',         ['vegetarian'], 'pasta'),
    ('Eggplant Parmesan',                              'eggplant-parmesan',                        'vegetarian',   'Italian',         ['vegetarian'], 'vegetables'),
    ('Classic Italian Pasta Sauce',                    'classic-italian-pasta-sauce',              'pasta',        'Italian',         ['vegetarian'], 'pasta'),
    ('Baked Honey Garlic Salmon',                      'baked-honey-garlic-salmon',                'seafood',      'American',        [],             'salmon'),
    ('Flourless Gluten-Free Brownies',                 'flourless-gluten-free-brownies',           'desserts',     'American',        ['gluten-free'], ''),
    ('Avocado Tomato Salad',                           'avocado-tomato-salad',                     'salads',       'Mediterranean',   ['vegetarian','gluten-free'], 'vegetables'),
    ('Keto Low-Carb Breakfast Bowl',                   'keto-low-carb-breakfast-bowl',             'breakfast',    'American',        ['keto','gluten-free'], 'eggs'),
    ('Chicken Breast and Quinoa Bowl',                 'chicken-breast-quinoa-bowl',               'chicken',      'American',        ['gluten-free','high-protein'], 'chicken'),
    ('Three Bean Vegetarian Chili',                    'three-bean-vegetarian-chili',              'vegetarian',   'Mexican',         ['vegetarian','vegan','gluten-free'], 'beans'),
    ('Baked Herb-Crusted Salmon',                      'baked-herb-crusted-salmon',                'seafood',      'Mediterranean',   ['gluten-free','high-protein'], 'salmon'),
]


def _seed_benchmark_fixture_recipes(cat_by_slug, idx_start):
    """Insert benchmark-fixture recipes so seed_benchmark_users finds them."""
    added = 0
    for i, (title, slug, cat_slug, cuisine, dietary, main_ing) in enumerate(BENCHMARK_FIXTURE_RECIPES):
        if Recipe.query.filter_by(slug=slug).first():
            continue
        cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('dinner')
        prep_m, cook_m = 20, 35
        if 'lasagna' in slug:
            prep_m, cook_m = 30, 60
        elif 'salmon' in slug:
            prep_m, cook_m = 10, 20
        elif 'brownie' in slug:
            prep_m, cook_m = 15, 30
        elif 'salad' in slug or 'bowl' in slug:
            prep_m, cook_m = 15, 10
        elif 'chili' in slug:
            prep_m, cook_m = 15, 40
        total_m = prep_m + cook_m

        ingredients = [
            'Salt and pepper to taste', 'Olive oil', 'Garlic, minced',
            'Onion, chopped', 'Fresh herbs', 'Lemon juice',
        ]
        if 'lasagna' in slug:
            ingredients = [
                '12 lasagna noodles', '2 cups ricotta cheese',
                '10 oz spinach, thawed and drained', '3 cups marinara sauce',
                '2 cups shredded mozzarella', '1/2 cup grated Parmesan',
                '1 egg', 'Salt and pepper to taste',
            ]
        elif 'salmon' in slug:
            ingredients = [
                '4 (6 oz) salmon fillets', '3 tablespoons honey',
                '4 cloves garlic, minced', '2 tablespoons soy sauce',
                '1 tablespoon olive oil', '1 lemon, sliced',
                'Salt and pepper to taste',
            ]
        elif 'brownie' in slug:
            ingredients = [
                '1 cup almond flour', '3/4 cup cocoa powder',
                '3/4 cup coconut sugar', '3 eggs', '1/2 cup melted coconut oil',
                '1 tsp vanilla extract', '1/2 tsp baking powder',
                '1/2 cup dark chocolate chips',
            ]
        elif 'bowl' in slug and 'keto' in slug:
            ingredients = [
                '4 large eggs', '2 cups baby spinach', '1 avocado, sliced',
                '4 strips bacon', '2 tablespoons olive oil',
                'Salt and pepper to taste',
            ]
        elif 'quinoa' in slug:
            ingredients = [
                '2 chicken breasts', '1 cup quinoa', '2 cups broccoli florets',
                '2 tablespoons olive oil', '1 lemon', 'Salt and pepper',
            ]
        elif 'chili' in slug:
            ingredients = [
                '1 can black beans', '1 can kidney beans', '1 can pinto beans',
                '1 can diced tomatoes', '1 onion, diced', '2 cloves garlic',
                '2 tbsp chili powder', '1 tsp cumin', 'Salt and pepper',
            ]
        elif 'pasta-sauce' in slug:
            ingredients = [
                '2 (28 oz) cans San Marzano tomatoes', '4 cloves garlic',
                '1/4 cup olive oil', '1 tsp dried oregano', '1/2 tsp red pepper flakes',
                'Fresh basil', 'Salt and pepper',
            ]
        elif 'avocado' in slug:
            ingredients = [
                '2 ripe avocados, cubed', '2 cups cherry tomatoes, halved',
                '1/4 red onion, thinly sliced', 'Juice of 1 lime',
                '2 tablespoons olive oil', 'Fresh cilantro', 'Salt and pepper',
            ]
        elif 'eggplant' in slug:
            ingredients = [
                '2 large eggplants', '2 cups marinara sauce',
                '2 cups shredded mozzarella', '1/2 cup grated Parmesan',
                '1 cup breadcrumbs', '2 eggs, beaten', 'Olive oil for frying',
            ]

        instructions = [
            f'Prepare {title.lower()} ingredients as listed.',
            'Combine and cook according to method, adjusting seasoning to taste.',
            'Serve warm and enjoy.',
        ]

        cal = _calories_estimate(cat_slug, len(ingredients))
        ri = idx_start + i
        rec = Recipe(
            title=title, slug=slug,
            description=f"A reliable {cuisine.lower()} {cat_slug} recipe popular with weekly meal planners.",
            category_id=cat.id if cat else None,
            cuisine=cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{(ri % IMAGE_POOL_SIZE) + 1}.jpg",
            prep_time=_fmt_mins(prep_m),
            cook_time=_fmt_mins(cook_m),
            total_time=_fmt_mins(total_m),
            servings='6', calories=cal,
            ingredients_json=json.dumps(ingredients),
            instructions_json=json.dumps(instructions),
            nutrition_json=json.dumps({'Calories': str(cal), 'Fat': '14g', 'Carbs': '30g', 'Protein': '22g'}),
            tags_json=json.dumps([cat_slug, cuisine.lower()] + dietary),
            gallery_json=json.dumps([]),
            is_featured=False, is_editors_pick=False,
            avg_rating=4.6, review_count=180,
            author_name='Benchmark Test Kitchen',
            prep_time_mins=prep_m, cook_time_mins=cook_m, total_time_mins=total_m,
            ingredient_count=len(ingredients),
            dietary_tags_json=json.dumps(dietary),
            dish_type=_dish_type_for(cat_slug, title),
            meal_type=_meal_type_for(cat_slug, title),
            cooking_method='baked' if 'baked' in title.lower() else '',
            main_ingredient=main_ing,
            occasion='', season='',
            feature_tags=json.dumps([cat_slug, cuisine.lower()] + dietary),
            latest_review_text='',
            storage_instructions='Refrigerate leftovers in an airtight container for up to 3 days.',
            primary_seasoning='', max_oven_temp=0,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=ri % 365),
        )
        db.session.add(rec)
        added += 1
    return added


# ---------------------------------------------------------------------------
# R3: holiday / occasion fixture recipes — hand-curated so the seasonal
# pages have rich first-class content.
# ---------------------------------------------------------------------------

HOLIDAY_FIXTURE_RECIPES = [
    # (title, slug, category_slug, cuisine, occasion_slug, prep_m, cook_m, dietary, main_ing, hero_ings)
    # Thanksgiving (10)
    ('Classic Roast Turkey with Herb Butter', 'classic-roast-turkey-herb-butter', 'thanksgiving', 'American', 'thanksgiving', 30, 240, [], 'turkey',
     ['1 (14 lb) whole turkey', '1 cup unsalted butter, softened', '1/4 cup fresh sage', '1/4 cup fresh thyme', '1 head garlic, halved', '2 lemons, halved', 'Salt and pepper to taste']),
    ('Classic Bread Stuffing with Sage', 'classic-bread-stuffing-sage', 'thanksgiving', 'American', 'thanksgiving', 25, 60, [], '',
     ['1 lb day-old bread cubes', '1 cup celery, diced', '1 cup onion, diced', '4 tbsp butter', '2 cups turkey stock', '2 tbsp fresh sage', '1 egg, beaten']),
    ('Cranberry Orange Sauce', 'cranberry-orange-sauce', 'thanksgiving', 'American', 'thanksgiving', 5, 15, ['vegetarian', 'vegan', 'gluten-free'], 'fruit',
     ['12 oz fresh cranberries', '1 cup orange juice', '1 cup sugar', '1 orange, zested']),
    ('Brown Butter Mashed Potatoes', 'brown-butter-mashed-potatoes', 'thanksgiving', 'American', 'thanksgiving', 15, 25, ['vegetarian', 'gluten-free'], 'potato',
     ['3 lb Yukon Gold potatoes', '1 cup heavy cream', '1/2 cup butter', 'Salt and pepper']),
    ('Maple Bourbon Sweet Potato Casserole', 'maple-bourbon-sweet-potato-casserole', 'thanksgiving', 'American', 'thanksgiving', 20, 40, ['vegetarian', 'gluten-free'], 'sweet potato',
     ['3 lb sweet potatoes', '1/3 cup maple syrup', '2 tbsp bourbon', '1/2 cup pecans', '4 tbsp butter']),
    ('Green Bean Casserole from Scratch', 'green-bean-casserole-scratch', 'thanksgiving', 'American', 'thanksgiving', 20, 30, ['vegetarian'], 'green beans',
     ['2 lb green beans', '8 oz mushrooms, sliced', '2 cups cream of mushroom sauce', '1 cup fried onions']),
    ('Classic Pumpkin Pie', 'classic-pumpkin-pie-thanksgiving', 'desserts', 'American', 'thanksgiving', 20, 60, ['vegetarian'], '',
     ['1 (15 oz) can pumpkin puree', '1 cup evaporated milk', '3/4 cup sugar', '2 eggs', '1 tsp cinnamon', '1/2 tsp ginger', '1/4 tsp cloves', '1 pie crust']),
    ('Pecan Pie with Bourbon', 'pecan-pie-bourbon', 'desserts', 'American', 'thanksgiving', 15, 50, ['vegetarian'], '',
     ['1 1/2 cups pecans', '1 cup dark corn syrup', '3/4 cup brown sugar', '3 eggs', '2 tbsp bourbon', '1 pie crust']),
    ('Cornbread Stuffing with Sausage', 'cornbread-stuffing-sausage', 'thanksgiving', 'American', 'thanksgiving', 25, 55, [], 'pork',
     ['1 lb cornbread, cubed', '1 lb Italian sausage', '1 cup celery', '1 cup onion', '2 cups stock', '2 eggs']),
    ('Roast Turkey Gravy from Pan Drippings', 'roast-turkey-gravy-pan-drippings', 'thanksgiving', 'American', 'thanksgiving', 5, 15, [], '',
     ['1/4 cup turkey pan drippings', '3 tbsp flour', '2 cups turkey stock', 'Salt and pepper']),

    # Christmas (8)
    ('Holiday Prime Rib Roast', 'holiday-prime-rib-roast', 'christmas', 'American', 'christmas', 20, 180, ['gluten-free'], 'beef',
     ['1 (6 lb) prime rib roast', '1/4 cup olive oil', '6 cloves garlic', '2 tbsp fresh rosemary', 'Salt and pepper']),
    ('Glazed Spiral-Cut Ham', 'glazed-spiral-cut-ham', 'christmas', 'American', 'christmas', 15, 120, ['gluten-free'], 'pork',
     ['1 (8 lb) spiral-cut ham', '1 cup brown sugar', '1/2 cup maple syrup', '1/4 cup Dijon mustard']),
    ('Eggnog French Toast Casserole', 'eggnog-french-toast-casserole', 'christmas', 'American', 'christmas', 15, 45, ['vegetarian'], '',
     ['1 loaf challah, cubed', '2 cups eggnog', '4 eggs', '1 tsp cinnamon', '1/2 tsp nutmeg']),
    ('Classic Gingerbread Cookies', 'classic-gingerbread-cookies', 'christmas', 'American', 'christmas', 30, 12, ['vegetarian'], '',
     ['3 cups flour', '3/4 cup molasses', '3/4 cup brown sugar', '3/4 cup butter', '1 egg', '1 tbsp ginger', '1 tbsp cinnamon']),
    ('Yule Log Buche de Noel', 'yule-log-buche-de-noel', 'christmas', 'French', 'christmas', 45, 25, ['vegetarian'], '',
     ['6 eggs, separated', '1 cup sugar', '1/3 cup cocoa powder', '1/2 cup flour', '2 cups whipped cream', '4 oz dark chocolate']),
    ('Cranberry Brie Bites', 'cranberry-brie-bites', 'christmas', 'American', 'christmas', 15, 15, ['vegetarian'], '',
     ['1 sheet crescent dough', '8 oz Brie cheese', '1/2 cup cranberry sauce', '1/4 cup chopped pecans']),
    ('Slow-Cooker Mulled Wine', 'slow-cooker-mulled-wine', 'christmas', 'European', 'christmas', 5, 60, ['vegetarian', 'vegan', 'gluten-free'], '',
     ['1 bottle red wine', '1 orange, sliced', '4 cinnamon sticks', '6 cloves', '1/3 cup brown sugar']),
    ('Christmas Morning Sticky Buns', 'christmas-morning-sticky-buns', 'christmas', 'American', 'christmas', 30, 30, ['vegetarian'], '',
     ['1 lb refrigerated cinnamon roll dough', '1 cup brown sugar', '1/2 cup butter', '1 cup pecans', '1/4 cup maple syrup']),

    # Easter (6)
    ('Easter Honey-Glazed Ham', 'easter-honey-glazed-ham', 'easter', 'American', 'easter', 15, 90, ['gluten-free'], 'pork',
     ['1 (8 lb) bone-in ham', '1 cup honey', '1/2 cup brown sugar', '2 tbsp Dijon', '1 tsp cloves']),
    ('Easter Lamb Roast with Rosemary', 'easter-lamb-roast-rosemary', 'easter', 'Mediterranean', 'easter', 15, 90, ['gluten-free', 'paleo'], 'lamb',
     ['1 (5 lb) leg of lamb', '6 cloves garlic, slivered', '2 tbsp fresh rosemary', '1/4 cup olive oil', 'Salt and pepper']),
    ('Classic Deviled Eggs', 'classic-deviled-eggs', 'easter', 'American', 'easter', 15, 10, ['vegetarian', 'gluten-free', 'keto', 'low-carb'], 'eggs',
     ['12 hard-boiled eggs', '1/3 cup mayonnaise', '1 tbsp Dijon mustard', '1 tbsp white vinegar', 'Smoked paprika']),
    ('Hot Cross Buns Traditional', 'hot-cross-buns-traditional', 'easter', 'British', 'easter', 30, 25, ['vegetarian'], '',
     ['3 1/2 cups bread flour', '1/3 cup sugar', '1 cup warm milk', '1 packet yeast', '2 eggs', '1 cup mixed dried fruit', '2 tsp cinnamon']),
    ('Carrot Cake with Cream Cheese Frosting', 'carrot-cake-cream-cheese-frosting', 'easter', 'American', 'easter', 25, 40, ['vegetarian'], '',
     ['2 cups flour', '2 cups grated carrots', '1 cup walnuts', '4 eggs', '1 1/2 cups oil', '2 cups sugar', '8 oz cream cheese', '1/2 cup butter', '4 cups powdered sugar']),
    ('Spring Asparagus and Pea Risotto', 'spring-asparagus-pea-risotto', 'easter', 'Italian', 'easter', 15, 30, ['vegetarian', 'gluten-free'], 'rice',
     ['1 1/2 cups arborio rice', '1 bunch asparagus', '1 cup peas', '4 cups vegetable stock', '1/2 cup Parmesan', '1/4 cup white wine']),

    # Valentine's (6)
    ('Chocolate Lava Cakes for Two', 'chocolate-lava-cakes-two', 'valentines', 'French', 'valentines', 15, 12, ['vegetarian'], '',
     ['4 oz dark chocolate', '1/2 cup butter', '2 eggs', '2 yolks', '1/4 cup sugar', '2 tbsp flour']),
    ('Heart-Shaped Strawberry Tartlets', 'heart-shaped-strawberry-tartlets', 'valentines', 'French', 'valentines', 30, 20, ['vegetarian'], '',
     ['1 sheet puff pastry', '1 lb strawberries', '1/2 cup mascarpone', '1/4 cup powdered sugar', '1/4 cup strawberry jam']),
    ('Red Velvet Cupcakes', 'red-velvet-cupcakes-valentines', 'valentines', 'American', 'valentines', 25, 22, ['vegetarian'], '',
     ['2 1/2 cups flour', '2 tbsp cocoa', '1 1/2 cups sugar', '1 cup buttermilk', '2 eggs', '1 tbsp red food coloring', '8 oz cream cheese frosting']),
    ('Filet Mignon with Red Wine Reduction', 'filet-mignon-red-wine-reduction', 'valentines', 'French', 'valentines', 10, 18, ['gluten-free', 'keto', 'low-carb'], 'beef',
     ['2 filet mignon steaks', '1 cup dry red wine', '2 shallots', '2 tbsp butter', 'Fresh thyme']),
    ('Champagne Risotto with Shrimp', 'champagne-risotto-shrimp', 'valentines', 'Italian', 'valentines', 15, 30, ['gluten-free'], 'shrimp',
     ['1 lb large shrimp', '1 1/2 cups arborio rice', '1 cup champagne', '4 cups seafood stock', '1/2 cup Parmesan', '2 shallots']),
    ('Chocolate-Covered Strawberries', 'chocolate-covered-strawberries-valentines', 'valentines', 'American', 'valentines', 15, 0, ['vegetarian', 'gluten-free'], '',
     ['1 lb strawberries', '8 oz dark chocolate', '2 oz white chocolate']),

    # 4th of July (6)
    ('All-American BBQ Pulled Pork', 'all-american-bbq-pulled-pork', 'fourth-of-july', 'American', 'fourth-of-july', 20, 360, ['gluten-free'], 'pork',
     ['1 (6 lb) pork shoulder', '1/4 cup brown sugar', '2 tbsp paprika', '2 tbsp salt', '1 cup BBQ sauce']),
    ('Classic Grilled Cheeseburgers', 'classic-grilled-cheeseburgers', 'fourth-of-july', 'American', 'fourth-of-july', 10, 12, [], 'beef',
     ['2 lb ground beef', '6 burger buns', '6 slices American cheese', 'Lettuce, tomato, onion', 'Salt and pepper']),
    ('Watermelon Feta Salad with Mint', 'watermelon-feta-salad-mint', 'fourth-of-july', 'Mediterranean', 'fourth-of-july', 15, 0, ['vegetarian', 'gluten-free'], '',
     ['6 cups cubed watermelon', '1 cup crumbled feta', '1/4 cup fresh mint', '2 tbsp lime juice', '2 tbsp olive oil']),
    ('Grilled Corn on the Cob with Cotija', 'grilled-corn-cob-cotija', 'fourth-of-july', 'Mexican', 'fourth-of-july', 5, 12, ['vegetarian', 'gluten-free'], 'corn',
     ['6 ears of corn', '1/3 cup mayonnaise', '1/2 cup cotija cheese', '1 tsp chili powder', 'Lime wedges']),
    ('Creamy Coleslaw Classic', 'creamy-coleslaw-classic', 'fourth-of-july', 'American', 'fourth-of-july', 15, 0, ['vegetarian', 'gluten-free'], 'cabbage',
     ['1 small head green cabbage, shredded', '2 carrots, grated', '1 cup mayonnaise', '2 tbsp apple cider vinegar', '2 tbsp sugar']),
    ('Classic Apple Pie with Lattice Crust', 'classic-apple-pie-lattice', 'fourth-of-july', 'American', 'fourth-of-july', 45, 60, ['vegetarian'], '',
     ['6 large apples', '3/4 cup sugar', '2 tbsp flour', '1 tsp cinnamon', '2 pie crusts', '2 tbsp butter']),

    # Halloween (5)
    ('Pumpkin Spice Cupcakes', 'pumpkin-spice-cupcakes', 'halloween', 'American', 'halloween', 20, 22, ['vegetarian'], '',
     ['1 1/2 cups flour', '1 cup pumpkin puree', '3/4 cup sugar', '2 eggs', '1/3 cup oil', '2 tsp pumpkin pie spice']),
    ('Caramel-Dipped Apples', 'caramel-dipped-apples-halloween', 'halloween', 'American', 'halloween', 20, 15, ['vegetarian', 'gluten-free'], '',
     ['8 apples', '1 (11 oz) bag caramels', '2 tbsp cream', '1 cup chopped peanuts']),
    ('Spider Web Brownies', 'spider-web-brownies', 'halloween', 'American', 'halloween', 15, 35, ['vegetarian'], '',
     ['1 box brownie mix', '2 oz white chocolate', '2 oz dark chocolate', '1 toothpick for swirling']),
    ('Pumpkin Soup with Sage Croutons', 'pumpkin-soup-sage-croutons', 'halloween', 'American', 'halloween', 15, 35, ['vegetarian'], '',
     ['2 (15 oz) cans pumpkin', '4 cups vegetable broth', '1 onion', '2 tbsp butter', '1/2 cup heavy cream', '4 fresh sage leaves']),
    ('Monster Eyeball Deviled Eggs', 'monster-eyeball-deviled-eggs', 'halloween', 'American', 'halloween', 20, 10, ['vegetarian', 'gluten-free', 'keto', 'low-carb'], 'eggs',
     ['12 hard-boiled eggs', '1/3 cup mayonnaise', '1 tbsp Dijon', 'Sliced olives for irises', 'Paprika for veins']),

    # Super Bowl (5)
    ('Buffalo Chicken Wings Classic', 'buffalo-chicken-wings-classic', 'super-bowl', 'American', 'super-bowl', 10, 40, ['gluten-free', 'keto', 'low-carb'], 'chicken',
     ['3 lb chicken wings', '1/2 cup hot sauce', '1/3 cup butter', '1 tbsp vinegar', 'Blue cheese dressing']),
    ('Seven-Layer Mexican Dip', 'seven-layer-mexican-dip', 'super-bowl', 'Mexican', 'super-bowl', 20, 0, ['vegetarian'], '',
     ['1 (16 oz) can refried beans', '1 cup sour cream', '1 cup guacamole', '1 cup salsa', '2 cups shredded cheese', '1/4 cup olives', '1/4 cup green onion']),
    ('Slow Cooker Game Day Chili', 'slow-cooker-game-day-chili', 'super-bowl', 'American', 'super-bowl', 15, 360, ['gluten-free'], 'beef',
     ['2 lb ground beef', '2 cans kidney beans', '2 cans diced tomatoes', '1 onion', '3 tbsp chili powder', '1 tbsp cumin']),
    ('BBQ Pulled Pork Sliders', 'bbq-pulled-pork-sliders', 'super-bowl', 'American', 'super-bowl', 20, 360, [], 'pork',
     ['3 lb pork shoulder', '2 cups BBQ sauce', '24 slider buns', '1 cup pickles', '1 cup coleslaw']),
    ('Loaded Nachos Supreme', 'loaded-nachos-supreme', 'super-bowl', 'Mexican', 'super-bowl', 15, 15, ['vegetarian'], '',
     ['1 large bag tortilla chips', '2 cups shredded cheese', '1 can refried beans', '1 cup salsa', '1 cup guacamole', '1/2 cup sour cream', '1/4 cup jalapenos']),

    # Mother's Day brunch (4)
    ('Classic Eggs Benedict with Hollandaise', 'classic-eggs-benedict-hollandaise', 'mothers-day', 'American', 'mothers-day', 15, 15, ['gluten-free'], 'eggs',
     ['8 eggs', '4 English muffins', '8 slices Canadian bacon', '3 egg yolks', '1/2 cup butter', '1 lemon']),
    ('Spinach and Goat Cheese Quiche', 'spinach-goat-cheese-quiche', 'mothers-day', 'French', 'mothers-day', 20, 45, ['vegetarian'], '',
     ['1 pie crust', '6 eggs', '1 cup cream', '2 cups spinach', '4 oz goat cheese', '1/2 cup gruyere']),
    ('Lemon Ricotta Pancakes', 'lemon-ricotta-pancakes', 'mothers-day', 'Italian', 'mothers-day', 10, 15, ['vegetarian'], '',
     ['1 cup flour', '1 cup ricotta', '3 eggs', '1/2 cup milk', '2 tbsp sugar', '1 lemon, zested']),
    ('Smoked Salmon Bagel Board', 'smoked-salmon-bagel-board', 'mothers-day', 'American', 'mothers-day', 15, 0, ['pescatarian'], 'salmon',
     ['6 bagels', '8 oz smoked salmon', '8 oz cream cheese', '1 red onion', '2 tbsp capers', '1 cucumber']),
]


def _seed_holiday_fixture_recipes(cat_by_slug):
    """Insert ~50 hand-curated holiday fixtures. Idempotent on slug."""
    added = 0
    existing_slugs = {r.slug for r in Recipe.query.all()}
    for i, row in enumerate(HOLIDAY_FIXTURE_RECIPES):
        (title, slug, cat_slug, cuisine, occ_slug, prep_m, cook_m,
         dietary, main_ing, hero_ings) = row
        if slug in existing_slugs:
            continue
        existing_slugs.add(slug)
        cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('dinner')
        total_m = prep_m + cook_m
        cal_cat = cat_slug if cat_slug in (
            'desserts', 'beef', 'pork', 'lamb', 'chicken', 'seafood', 'pasta',
            'side-dishes', 'appetizers', 'breakfast', 'vegan', 'vegetarian'
        ) else 'dinner'
        cal = _calories_estimate(cal_cat, len(hero_ings))
        instructions = [
            f"Gather all ingredients for {title}.",
            "Prepare any prep work in advance: chop, measure, and bring perishables to temp.",
            f"Cook according to method noted in recipe metadata for about {cook_m} minutes." if cook_m else
            "Combine the ingredients and chill or assemble as the recipe requires.",
            "Plate generously and serve warm to family and guests.",
            "Store leftovers refrigerated in an airtight container for up to 3 days.",
        ]
        nutri = {
            'Calories': str(cal),
            'Fat': f"{14 + i % 16}g",
            'Carbs': f"{24 + i % 35}g",
            'Protein': f"{16 + i % 22}g",
            'Fiber': f"{3 + i % 6}g",
            'Sodium': f"{350 + (i * 17) % 500}mg",
            'Sugar': f"{8 + i % 14}g",
        }
        feature_tags = [cat_slug, cuisine.lower(), occ_slug, 'holiday', 'occasion'] + dietary
        img_n = ((i * 31 + 73) % IMAGE_POOL_SIZE) + 1
        rec = Recipe(
            title=title, slug=slug,
            description=f"A classic {occ_slug.replace('-', ' ')} {cal_cat} recipe — a crowd-pleaser worth making every year.",
            category_id=cat.id if cat else None,
            cuisine=cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(prep_m),
            cook_time=_fmt_mins(cook_m) if cook_m else '0 mins',
            total_time=_fmt_mins(total_m),
            servings=str(6 + (i % 6)),
            calories=cal,
            ingredients_json=json.dumps(hero_ings),
            instructions_json=json.dumps(instructions),
            nutrition_json=json.dumps(nutri),
            tags_json=json.dumps(feature_tags),
            gallery_json=json.dumps([]),
            is_featured=(i % 5 == 0),
            is_editors_pick=(i % 11 == 0),
            avg_rating=round(4.4 + (i * 7 % 6) * 0.1, 1),
            review_count=80 + (i * 13 % 320),
            author_name='Holiday Test Kitchen',
            prep_time_mins=prep_m,
            cook_time_mins=cook_m,
            total_time_mins=total_m,
            ingredient_count=len(hero_ings),
            dietary_tags_json=json.dumps(dietary),
            dish_type=_dish_type_for(cal_cat, title),
            meal_type=_meal_type_for(cal_cat, title),
            cooking_method='roasted' if 'roast' in title.lower() else (
                'grilled' if 'grilled' in title.lower() else (
                    'baked' if ('cake' in title.lower() or 'pie' in title.lower()) else '')),
            main_ingredient=main_ing,
            occasion=occ_slug,
            season='',
            feature_tags=json.dumps(feature_tags),
            latest_review_text='',
            storage_instructions='Refrigerate leftovers in an airtight container for up to 3 days. Best served fresh.',
            primary_seasoning='', max_oven_temp=375 if cal_cat == 'desserts' else 0,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=(i * 19 + 7) % 365),
        )
        db.session.add(rec)
        added += 1
    return added


# ---------------------------------------------------------------------------

def seed_extended_catalog():
    """Idempotent: add 14 new categories, ~500+ MealDB recipes, ~20
    reviewer users, and ~10 reviews per popular recipe."""
    # Sentinel gate — 'british' is added in NEW_CATEGORIES; once present
    # the entire extension has already been seeded.
    if Category.query.filter_by(slug='british').first():
        return

    print("[seed_extended] starting extended catalog seed…")

    # ----- Categories -----
    cat_by_slug: dict[str, Category] = {c.slug: c for c in Category.query.all()}
    for name, slug, desc, ptype, order in NEW_CATEGORIES:
        if slug in cat_by_slug:
            continue
        c = Category(name=name, slug=slug, description=desc,
                     parent_type=ptype, display_order=order)
        db.session.add(c)
        cat_by_slug[slug] = c
    db.session.flush()

    # Refresh map with IDs
    cat_by_slug = {c.slug: c for c in Category.query.all()}

    # ----- Benchmark-fixture recipes (must exist before seed_benchmark_users) -----
    fixture_added = _seed_benchmark_fixture_recipes(cat_by_slug, idx_start=1000)
    db.session.flush()
    print(f"[seed_extended] added {fixture_added} benchmark-fixture recipes")

    # ----- MealDB recipes -----
    meals = _load_mealdb()
    if not meals:
        print("[seed_extended] no themealdb.json — skipping recipes")
        db.session.commit()
        return

    existing_slugs = {r.slug for r in Recipe.query.all()}
    rng = random.Random(42)

    added = 0
    # Stable iteration order: sort by idMeal so seed output is deterministic
    meals_sorted = sorted(meals, key=lambda m: int(m.get('idMeal') or 0))

    for idx, meal in enumerate(meals_sorted):
        title = (meal.get('strMeal') or '').strip()
        if not title:
            continue
        slug = _slugify(title)
        if not slug or slug in existing_slugs:
            continue
        existing_slugs.add(slug)

        mealdb_cat = meal.get('strCategory') or ''
        cat_slug = MEALDB_CATEGORY_TO_SLUG.get(mealdb_cat, 'dinner')
        cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('dinner')

        area = meal.get('strArea') or ''
        cuisine_display = AREA_TO_CUISINE_DISPLAY.get(area, area or 'International')

        ingredients = _parse_ingredients(meal)
        if not ingredients:
            continue  # skip if no ingredient data
        instructions = _parse_instructions(meal)

        prep_m, cook_m, total_m = _estimate_times(meal)
        cal = _calories_estimate(cat_slug, len(ingredients))
        meal_type = _meal_type_for(cat_slug, title)
        dish_type = _dish_type_for(cat_slug, title)
        main_ing = _main_ingredient_for(cat_slug)
        cooking_method = _cooking_method(meal.get('strInstructions') or '')

        # Tags
        instr_tags_src = (meal.get('strTags') or '')
        raw_tags = [t.strip() for t in instr_tags_src.split(',') if t.strip()]
        feature_tags = [_slugify(t) for t in (raw_tags + [mealdb_cat, area, cuisine_display]) if t]
        dietary = _dietary_tags(title, cat_slug, area)

        # Image — recycle the bundled recipes_real pool so the mirror
        # works offline. Deterministic by index.
        img_n = (idx % IMAGE_POOL_SIZE) + 1
        image = f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg"

        # Ratings — deterministic from index for byte stability
        avg = round(3.8 + (idx * 7 % 13) * 0.1, 1)  # 3.8 .. 5.0
        avg = min(avg, 5.0)
        rev_seed_count = 20 + (idx * 17 % 480)  # 20 .. 499 (seeded display only)

        description = (
            (meal.get('strInstructions') or '').strip().split('.')[0][:240]
            or f"A traditional {cuisine_display} {cat_slug} recipe."
        )
        if not description.endswith('.'):
            description += '.'

        created = MIRROR_REFERENCE_DATE - timedelta(days=(idx * 3) % 720)

        recipe = Recipe(
            title=title,
            slug=slug,
            description=description,
            category_id=cat.id if cat else None,
            cuisine=cuisine_display,
            image=image,
            prep_time=_fmt_mins(prep_m),
            cook_time=_fmt_mins(cook_m),
            total_time=_fmt_mins(total_m),
            servings=str(4 + (idx % 5)),
            calories=cal,
            ingredients_json=json.dumps(ingredients),
            instructions_json=json.dumps(instructions),
            nutrition_json=json.dumps({
                'Calories': str(cal),
                'Fat': f"{8 + len(ingredients) % 20}g",
                'Carbs': f"{20 + len(ingredients) * 2 % 50}g",
                'Protein': f"{12 + len(ingredients) % 30}g",
            }),
            tags_json=json.dumps(raw_tags or [mealdb_cat.lower(), (area or '').lower()]),
            gallery_json=json.dumps([]),
            is_featured=(idx % 23 == 0),
            is_editors_pick=(idx % 47 == 0),
            avg_rating=avg,
            review_count=rev_seed_count,
            author_name=f"{area or 'Allrecipes'} Test Kitchen",
            prep_time_mins=prep_m,
            cook_time_mins=cook_m,
            total_time_mins=total_m,
            ingredient_count=len(ingredients),
            dietary_tags_json=json.dumps(dietary),
            dish_type=dish_type,
            meal_type=meal_type,
            cooking_method=cooking_method,
            main_ingredient=main_ing,
            occasion=_holiday_for(title, cat_slug),
            season='',
            feature_tags=json.dumps(list(dict.fromkeys(feature_tags))),
            latest_review_text='',
            storage_instructions='Refrigerate leftovers in an airtight container for up to 3 days.',
            primary_seasoning='',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(recipe)
        added += 1

    db.session.flush()
    print(f"[seed_extended] added {added} recipes from TheMealDB")

    # ----- Variant recipes (Slow Cooker / Air Fryer / Grilled / …) -----
    # Doubles the catalog with deterministic appliance/method variants of
    # every eligible MealDB base recipe. Variants live in the same Test
    # Kitchen author bucket so they pick up reviews below.
    base_for_variants = (
        Recipe.query
        .filter(Recipe.author_name.like('%Test Kitchen%'))
        .order_by(Recipe.id)
        .all()
    )
    variants_added = _seed_variant_recipes(cat_by_slug, base_for_variants)
    db.session.flush()
    print(f"[seed_extended] added {variants_added} variant recipes")

    # ----- R3: diet-flavored variants (keto/paleo/vegan/etc.) -----
    base_for_diet = (
        Recipe.query
        .filter(Recipe.author_name.like('%Test Kitchen%'))
        .order_by(Recipe.id)
        .all()
    )
    diet_added = _seed_diet_variant_recipes(cat_by_slug, base_for_diet)
    db.session.flush()
    print(f"[seed_extended] added {diet_added} diet variant recipes")

    # ----- R3: restaurant-style cuisine variants -----
    base_for_cuisine = (
        Recipe.query
        .filter(Recipe.author_name.like('%Test Kitchen%'))
        .order_by(Recipe.id)
        .all()
    )
    cuisine_added = _seed_cuisine_variant_recipes(cat_by_slug, base_for_cuisine)
    db.session.flush()
    print(f"[seed_extended] added {cuisine_added} cuisine variant recipes")

    # ----- R3: speed (5-ingredient / 15-min / 20-min) variants -----
    base_for_speed = (
        Recipe.query
        .filter(Recipe.author_name.like('%Test Kitchen%'))
        .order_by(Recipe.id)
        .all()
    )
    speed_added = _seed_speed_variant_recipes(cat_by_slug, base_for_speed)
    db.session.flush()
    print(f"[seed_extended] added {speed_added} speed variant recipes")

    # ----- R3: holiday/occasion fixture recipes -----
    holiday_added = _seed_holiday_fixture_recipes(cat_by_slug)
    db.session.flush()
    print(f"[seed_extended] added {holiday_added} holiday fixture recipes")

    # ----- R4: chef recipes + 4 variant passes + enrichment + collections + articles -----
    try:
        from r4_seed import run_r4_polish
        r4_counts = run_r4_polish(cat_by_slug)
        if not r4_counts.get('skipped'):
            print(f"[seed_extended] R4 polish: {r4_counts}")
    except Exception as exc:
        print(f"[seed_extended] R4 polish FAILED: {exc!r}")
        raise

    # ----- Reviewer users (placeholder, non-loginable) -----
    REVIEWER_COUNT = 24
    reviewer_first = [
        'emma', 'olivia', 'ava', 'sophia', 'isabella', 'mia', 'amelia',
        'harper', 'evelyn', 'abigail', 'liam', 'noah', 'oliver',
        'elijah', 'james', 'william', 'benjamin', 'lucas', 'henry',
        'theodore', 'mateo', 'jack', 'levi', 'sebastian',
    ]
    reviewer_last = [
        'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia',
        'miller', 'davis', 'rodriguez', 'martinez', 'hernandez',
        'lopez', 'gonzalez', 'wilson', 'anderson', 'thomas', 'taylor',
        'moore', 'jackson', 'martin', 'lee', 'perez', 'thompson', 'white',
    ]
    reviewers: list[User] = []
    for i in range(REVIEWER_COUNT):
        first = reviewer_first[i % len(reviewer_first)]
        last = reviewer_last[i % len(reviewer_last)]
        uname = f"{first}_{last[:1]}{i+1:02d}"
        email = f"{first}.{last}{i+1:02d}@example.com"
        if User.query.filter_by(email=email).first():
            continue
        u = User(
            username=uname,
            email=email,
            display_name=f"{first.capitalize()} {last.capitalize()}",
            bio=f"Home cook from the {['Midwest','South','West Coast','Northeast'][i % 4]}.",
            location=['Chicago, IL', 'Atlanta, GA', 'Seattle, WA', 'Boston, MA'][i % 4],
        )
        u.password_hash = REVIEWER_PINNED_HASH
        db.session.add(u)
        reviewers.append(u)
    db.session.flush()
    if not reviewers:
        reviewers = User.query.filter(
            User.email.like('%@example.com')).order_by(User.id).all()
    print(f"[seed_extended] reviewer pool size: {len(reviewers)}")

    # ----- Reviews on the newly seeded recipes -----
    # Attach 4-12 reviews to ~60% of new recipes, deterministic.
    pool = _generate_review_pool(rng)
    new_recipes = Recipe.query.filter(
        Recipe.author_name.like('%Test Kitchen%')).order_by(Recipe.id).all()
    review_count_added = 0
    for ri, recipe in enumerate(new_recipes):
        if ri % 5 == 4:  # skip every 5th for variety
            continue
        n_reviews = 4 + (ri * 11 % 9)  # 4..12
        for j in range(n_reviews):
            tmpl = pool[(ri * 7 + j * 3) % len(pool)]
            reviewer = reviewers[(ri * 5 + j) % len(reviewers)]
            review = Review(
                user_id=reviewer.id,
                recipe_id=recipe.id,
                rating=tmpl[0],
                title=tmpl[1],
                body=tmpl[2],
                helpful_count=(ri + j) % 25,
                created_at=MIRROR_REFERENCE_DATE - timedelta(days=(ri * 2 + j) % 600),
            )
            db.session.add(review)
            review_count_added += 1
        # Refresh recipe.avg_rating / review_count
        ratings = [pool[(ri * 7 + j * 3) % len(pool)][0] for j in range(n_reviews)]
        recipe.avg_rating = round(sum(ratings) / len(ratings), 1)
        recipe.review_count = n_reviews

    db.session.commit()
    print(f"[seed_extended] added {review_count_added} reviews "
          f"across {Recipe.query.count()} total recipes "
          f"in {Category.query.count()} categories")

    # Re-emit indexes in alpha order + VACUUM so a rebuild from source
    # gives a byte-identical SQLite file (see harden-env gotcha #2).
    _normalize_seed_db_layout()


def _normalize_seed_db_layout():
    """Re-emit indexes alphabetically + VACUUM. Run once after first seed."""
    conn = db.engine.connect()
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.execute(text("VACUUM"))
    conn.commit()
