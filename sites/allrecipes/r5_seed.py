"""R5 polish seed: recipe enrichment (cuisine_origin / time / calorie / allergen
/ equipment tags) + three new variant passes + extra chef recipes.

Imported by ``seed_data.seed_extended_catalog`` AFTER the R4 polish so it sees
every R4-generated recipe. Everything in here is fully deterministic so a
rebuild from source is byte-identical to the shipped ``instance_seed/allrecipes.db``.

R5 deliverables (recipes 5790 -> 8000+):
  * 3 new variant passes: make-ahead, kid-friendly, global-fusion.
  * 3 new chefs (~12 recipes) to broaden cuisine-origin coverage.
  * Enrichment of EVERY recipe so feature_tags carry: cuisine-origin slug,
    time-to-make tier (``under-30-min`` / ``under-1-hour`` / ``over-1-hour``),
    calorie tier (``under-300-cal`` / ``under-500-cal`` / ``over-500-cal``),
    one equipment hint, and an allergen-free roster (``dairy-free``,
    ``gluten-free``, ``nut-free``, ``egg-free``, ``soy-free``) derived
    deterministically from ingredient strings.
  * dietary_tags_json is topped up with allergen-free entries so
    /diet/<slug> queries hit the new fields.

Idempotent — gated on the presence of a sentinel recipe slug.
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


# ===========================================================================
# Allergen / equipment heuristics
# ===========================================================================

_DAIRY_KEYWORDS = (
    'milk', 'butter', 'cream', 'cheese', 'yogurt', 'parmesan', 'cheddar',
    'mozzarella', 'mascarpone', 'ricotta', 'feta', 'sour cream', 'gruyere',
    'pecorino', 'brie',
)
_GLUTEN_KEYWORDS = (
    'flour', 'bread', 'pasta', 'tortilla', 'noodle', 'panko', 'crouton',
    'phyllo', 'ladyfinger', 'cracker', 'baguette', 'roux', 'biscuit',
    'naan', 'pita',
)
_NUT_KEYWORDS = (
    'almond', 'pecan', 'walnut', 'cashew', 'pistachio', 'hazelnut',
    'macadamia', 'pine nut', 'peanut',
)
_EGG_KEYWORDS = (
    ' egg', 'eggs', 'mayonnaise', 'hollandaise', 'meringue', 'aioli',
    'custard',
)
_SOY_KEYWORDS = (
    'soy sauce', 'tofu', 'edamame', 'miso', 'tamari', 'tempeh',
)


_EQUIPMENT_PATTERNS = (
    # (substring match on title/method/feature, equipment slug)
    ('dutch oven',      'dutch-oven'),
    ('one-pot',         'dutch-oven'),
    ('one pot',         'dutch-oven'),
    ('sheet-pan',       'sheet-pan'),
    ('sheet pan',       'sheet-pan'),
    ('slow cooker',     'slow-cooker'),
    ('slow-cook',       'slow-cooker'),
    ('crock',           'slow-cooker'),
    ('instant pot',     'instant-pot'),
    ('pressure cooker', 'instant-pot'),
    ('air fryer',       'air-fryer'),
    ('grill',           'grill'),
    ('bbq',             'grill'),
    ('skillet',         'skillet'),
    ('cast iron',       'skillet'),
    ('wok',             'wok'),
    ('stir-fry',        'wok'),
    ('stir fry',        'wok'),
    ('blender',         'blender'),
    ('food processor',  'food-processor'),
    ('stand mixer',     'stand-mixer'),
    ('dough hook',      'stand-mixer'),
    ('baking sheet',    'sheet-pan'),
    ('roast',           'oven'),
    ('bake',            'oven'),
    ('saute',           'skillet'),
    ('sear',            'skillet'),
    ('fry',             'skillet'),
    ('simmer',          'saucepan'),
    ('boil',            'saucepan'),
)


def _detect_allergens(ingredients_text: str) -> list[str]:
    """Return allergen-FREE tags ('dairy-free', 'gluten-free', …) when the
    ingredients text does NOT mention the allergen keywords. Conservative:
    a tag is added only if none of the trigger words appear."""
    txt = (ingredients_text or '').lower()
    tags = []
    if not any(k in txt for k in _DAIRY_KEYWORDS):
        tags.append('dairy-free')
    if not any(k in txt for k in _GLUTEN_KEYWORDS):
        tags.append('gluten-free')
    if not any(k in txt for k in _NUT_KEYWORDS):
        tags.append('nut-free')
    if not any(k in txt for k in _EGG_KEYWORDS):
        tags.append('egg-free')
    if not any(k in txt for k in _SOY_KEYWORDS):
        tags.append('soy-free')
    return tags


def _detect_equipment(recipe) -> str:
    """Return a single equipment slug based on title / cooking_method /
    instructions / feature_tags. Falls back to 'stovetop' for the catch-all."""
    haystack_parts = [
        (recipe.title or '').lower(),
        (recipe.cooking_method or '').lower(),
        (recipe.author_name or '').lower(),
    ]
    try:
        instr = json.loads(recipe.instructions_json or '[]')
        haystack_parts.append(' '.join(instr).lower())
    except Exception:
        pass
    try:
        feats = json.loads(recipe.feature_tags or '[]')
        haystack_parts.append(' '.join(feats).lower())
    except Exception:
        pass
    hay = ' '.join(haystack_parts)
    for needle, slug in _EQUIPMENT_PATTERNS:
        if needle in hay:
            return slug
    return 'stovetop'


_CUISINE_TO_ORIGIN = {
    'italian':      'europe',
    'french':       'europe',
    'european':     'europe',
    'british':      'europe',
    'spanish':      'europe',
    'greek':        'europe',
    'mexican':      'latin-america',
    'latin american': 'latin-america',
    'brazilian':    'latin-america',
    'cuban':        'latin-america',
    'caribbean':    'latin-america',
    'american':     'north-america',
    'canadian':     'north-america',
    'southern':     'north-america',
    'chinese':      'east-asia',
    'japanese':     'east-asia',
    'korean':       'east-asia',
    'thai':         'south-east-asia',
    'vietnamese':   'south-east-asia',
    'indian':       'south-asia',
    'pakistani':    'south-asia',
    'mediterranean': 'mediterranean',
    'middle eastern': 'middle-east',
    'moroccan':     'north-africa',
    'african':      'africa',
    'asian':        'east-asia',
    'asian fusion': 'east-asia',
}


def _detect_cuisine_origin(recipe) -> str:
    c = (recipe.cuisine or '').strip().lower()
    if c in _CUISINE_TO_ORIGIN:
        return _CUISINE_TO_ORIGIN[c]
    for k, v in _CUISINE_TO_ORIGIN.items():
        if k in c:
            return v
    return 'global'


def _time_tier(total_mins: int) -> str:
    t = total_mins or 0
    if t and t <= 30:
        return 'under-30-min'
    if t and t <= 60:
        return 'under-1-hour'
    return 'over-1-hour'


def _calorie_tier(cal: int) -> str:
    c = cal or 0
    if c and c < 300:
        return 'under-300-cal'
    if c and c < 500:
        return 'under-500-cal'
    return 'over-500-cal'


def _enrich_r5_fields(*, sentinel_check=True):
    """Add cuisine-origin slug + time tier + calorie tier + equipment + 5
    allergen-free flags to every recipe's feature_tags. Pure mutation.

    Allergen-free flags are also pushed into dietary_tags_json so
    /diet/<slug> filter queries hit the new data.
    """
    recipes = Recipe.query.order_by(Recipe.id).all()
    touched = 0
    for r in recipes:
        try:
            feats = json.loads(r.feature_tags or '[]')
        except Exception:
            feats = []
        if not isinstance(feats, list):
            feats = []

        origin = _detect_cuisine_origin(r)
        if origin and origin not in feats:
            feats.append(origin)
        if r.cuisine:
            cs = _slugify(r.cuisine)
            cuisine_origin_tag = f'cuisine-{cs}'
            if cuisine_origin_tag not in feats:
                feats.append(cuisine_origin_tag)

        t_tier = _time_tier(r.total_time_mins or 0)
        if t_tier not in feats:
            feats.append(t_tier)

        c_tier = _calorie_tier(r.calories or 0)
        if c_tier not in feats:
            feats.append(c_tier)

        equipment = _detect_equipment(r)
        equipment_tag = f'equipment-{equipment}'
        if equipment_tag not in feats:
            feats.append(equipment_tag)
        if equipment not in feats:
            feats.append(equipment)

        # Allergen-free flags from ingredients.
        try:
            ings = json.loads(r.ingredients_json or '[]')
        except Exception:
            ings = []
        if isinstance(ings, list):
            allergen_free = _detect_allergens(' '.join(str(i) for i in ings))
        else:
            allergen_free = []
        for tag in allergen_free:
            if tag not in feats:
                feats.append(tag)

        # Cap so a long-tail recipe doesn't carry 30 tags.
        r.feature_tags = json.dumps(feats[:20])

        # Mirror allergen flags + tiers into dietary_tags_json so
        # /diet/<slug> hits them.
        try:
            dietary = json.loads(r.dietary_tags_json or '[]')
        except Exception:
            dietary = []
        if not isinstance(dietary, list):
            dietary = []
        for tag in allergen_free:
            if tag not in dietary:
                dietary.append(tag)
        r.dietary_tags_json = json.dumps(dietary)
        touched += 1

    db.session.flush()
    print(f"[r5_seed] enriched {touched} recipes with cuisine-origin/time/cal/equipment/allergen tags")


# ===========================================================================
# Make-ahead variants (every 2nd eligible base)
# ===========================================================================

MAKE_AHEAD_INSTRUCTIONS = [
    "Make this dish 1 to 2 days ahead — refrigerate covered in an airtight container.",
    "On the day, preheat the oven to 350°F (175°C) and let the dish come to room temperature for 30 minutes while the oven heats.",
    "Re-warm covered for 18 to 22 minutes, removing the cover for the last 5 minutes to crisp the top.",
    "Adjust seasoning right before serving — refrigeration can dull flavors, so a final pinch of salt + squeeze of lemon brings it back to life.",
    "Garnish with fresh herbs at the table. Store leftovers up to 4 days; the flavors continue to deepen.",
]


def _seed_make_ahead_variants(cat_by_slug, base_recipes, existing_slugs):
    """Make-ahead variant for every 2nd eligible base — recipes that
    explicitly improve overnight (stews, lasagnas, casseroles, dips, dressings)."""
    skip_cats = {'desserts', 'salads', 'appetizers'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 2 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap',
                'Make-Ahead', 'Kid-Friendly', 'Global-Fusion')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug in skip_cats:
            continue
        new_title = f"Make-Ahead {base.title}"
        new_slug = f"make-ahead-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(10, base_prep + 5)
        new_cook = max(10, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + ['1 tbsp fresh lemon juice (to brighten on day-of)',
                                      'Fresh herbs for finishing']
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'make-ahead', 'overnight', 'meal-prep', 'reheats-well',
            base_cat_slug or 'dinner']))
        img_n = ((ri * 109 + 23) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Make-ahead photos',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 113 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 127 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 131 + 53) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 13 + 41) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A make-ahead version of {base.title}. Build it 1 to 2 days in advance, refrigerate covered, "
                "then reheat at 350°F. The flavors deepen overnight — perfect for stress-free entertaining."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '6',
            calories=base.calories or 400,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(MAKE_AHEAD_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '400'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 47 == 0),
            is_editors_pick=(ri % 67 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 7 - 3) * 0.03)), 1),
            review_count=0,
            author_name='Make-Ahead Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method,
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions=(
                'Refrigerate covered up to 2 days before reheating. Once cooked, '
                'leftovers keep 4 days; portions freeze well up to 2 months.'),
            primary_seasoning='', max_oven_temp=350,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Kid-friendly variants (every 4th eligible base, dialed-down spice)
# ===========================================================================

KID_FRIENDLY_INSTRUCTIONS = [
    "Prep the dish exactly as the parent recipe directs, but skip the hot spices and any strong aromatics (raw garlic, fish sauce, blue cheese).",
    "Cut every protein and vegetable into bite-sized pieces — easier on small hands and small mouths.",
    "Build the flavor with sweetness (honey or maple), umami (mild cheese, soy or low-sodium broth), and mild herbs (basil, parsley).",
    "Cook at moderate heat so nothing scorches; finish with a sprinkle of cheese or a swirl of butter for picky-eater appeal.",
    "Serve with a familiar side — buttered noodles, rice, or roasted potato wedges — so there is always something safe on the plate.",
]


def _seed_kid_friendly_variants(cat_by_slug, base_recipes, existing_slugs):
    """Kid-friendly variant for every 3rd eligible base."""
    eligible_cats = {'chicken', 'pasta', 'pork', 'beef', 'vegetarian',
                     'breakfast', 'dinner', 'side-dishes', 'soups',
                     'desserts', 'appetizers', 'salads', 'seafood'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 3 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap',
                'Make-Ahead', 'Kid-Friendly', 'Global-Fusion')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug not in eligible_cats:
            continue
        new_title = f"Kid-Friendly {base.title}"
        new_slug = f"kid-friendly-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep - 5)
        new_cook = max(10, int(base_cook * 0.85))
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        # Filter out aggressive heat from ingredients — deterministic.
        spicy_keywords = ('chile', 'chili', 'jalape', 'cayenne', 'hot sauce',
                          'sriracha', 'harissa', 'gochujang')
        filtered = [i for i in base_ings
                    if not any(k in str(i).lower() for k in spicy_keywords)]
        new_ings = filtered + [
            '1/4 cup grated mild cheddar (optional, for finishing)',
            '1 tbsp butter (for richness)',
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
            'kid-friendly', 'family-friendly', 'mild', 'crowd-pleaser',
            'school-night', base_cat_slug]))
        img_n = ((ri * 137 + 19) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Kid-friendly photos',
            'desc': f"Visual walkthrough for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 139 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 149 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 151 + 47) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 17 + 53) % 720)
        cal = max(220, (base.calories or 380) - 40)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A kid-friendly take on {base.title} — mild seasoning, "
                "bite-sized pieces, and a sprinkle of mild cheddar on top. Built so "
                "even the pickiest eater at the table finishes the plate."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(KID_FRIENDLY_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=False,
            is_editors_pick=(ri % 53 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.5) + ((ri % 5 - 2) * 0.02)), 1),
            review_count=0,
            author_name='Kid-Friendly Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or 'stovetop',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Refrigerate leftovers up to 3 days; great for next-day school lunches.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Global-fusion variants (every 6th eligible base, cross-cuisine flavor swap)
# ===========================================================================

FUSION_RULES = [
    # (slug-prefix, label, hero ingredients, instructions hint)
    ('thai-twist',         'Thai Twist',         ['2 tbsp red curry paste', '1 (13.5 oz) can coconut milk', '1 tbsp fish sauce', '1 lime, zested', 'Fresh Thai basil'],
     'Whisk the curry paste into the simmering coconut milk and finish the dish with a squeeze of lime + torn Thai basil.'),
    ('korean-bbq-twist',   'Korean BBQ Twist',   ['1/4 cup gochujang', '2 tbsp soy sauce', '2 tbsp rice vinegar', '1 tbsp sesame oil', '2 green onions, sliced'],
     'Stir together gochujang, soy, and rice vinegar; toss with the cooked base and finish with sesame oil + green onions.'),
    ('mexican-mole-twist', 'Mexican Mole Twist', ['2 dried ancho chiles, rehydrated', '1 oz Mexican chocolate', '1 tbsp cumin', '1 tbsp smoked paprika', 'Fresh cilantro'],
     'Blend the rehydrated chiles with the chocolate and aromatics; fold into the dish, simmer 8 minutes, finish with cilantro.'),
    ('moroccan-twist',     'Moroccan Twist',     ['1 tsp ras el hanout', '1/4 cup dried apricots', '2 tbsp preserved lemon', '1/4 cup toasted almonds', 'Fresh mint'],
     'Toast the spice blend until fragrant; stir in apricots and preserved lemon, then finish with almonds + mint.'),
    ('japanese-miso-twist', 'Japanese Miso Twist', ['1/4 cup white miso', '2 tbsp mirin', '1 tbsp rice vinegar', '1 sheet nori, crumbled', 'Furikake to finish'],
     'Whisk miso into the warm pan juices; glaze the dish and finish with crumbled nori + a generous shake of furikake.'),
    ('indian-curry-twist', 'Indian Curry Twist', ['2 tbsp garam masala', '1 (14 oz) can crushed tomatoes', '1 tbsp ginger', '1/4 cup heavy cream', 'Fresh cilantro'],
     'Bloom garam masala in oil; add tomatoes and ginger, simmer 10 minutes, then enrich with cream and finish with cilantro.'),
]


def _seed_global_fusion_variants(cat_by_slug, base_recipes, existing_slugs):
    """Global-fusion variant for every 6th eligible base — pick a fusion
    style from FUSION_RULES based on row index so it is deterministic."""
    eligible_cats = {'chicken', 'beef', 'pork', 'pasta', 'seafood',
                     'vegetarian', 'vegan', 'dinner', 'side-dishes', 'soups'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 6 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap',
                'Make-Ahead', 'Kid-Friendly', 'Global-Fusion')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug not in eligible_cats:
            continue
        rule = FUSION_RULES[(ri // 6) % len(FUSION_RULES)]
        prefix, label, hero_ings, hint = rule
        new_title = f"{label}: {base.title}"
        new_slug = f"{prefix}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(10, base_prep + 5)
        new_cook = max(15, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + list(hero_ings)
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        fusion_origin = {
            'thai-twist':         ('south-east-asia', 'Thai'),
            'korean-bbq-twist':   ('east-asia',       'Korean'),
            'mexican-mole-twist': ('latin-america',   'Mexican'),
            'moroccan-twist':     ('north-africa',    'Moroccan'),
            'japanese-miso-twist':('east-asia',       'Japanese'),
            'indian-curry-twist': ('south-asia',      'Indian'),
        }[prefix]
        new_features = list(dict.fromkeys(base_features + [
            'fusion', 'global', prefix, fusion_origin[0], base_cat_slug,
            f'cuisine-{fusion_origin[1].lower()}']))
        new_instructions = []
        try:
            new_instructions = json.loads(base.instructions_json or '[]')[:4]
        except Exception:
            new_instructions = []
        new_instructions.append(hint)
        img_n = ((ri * 157 + 7) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f'{label} prep',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 163 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 167 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 173 + 53) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 19 + 71) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {label} twist on {base.title}. Cross-cultural pantry swaps — "
                f"{fusion_origin[1]} spices, sauces, and finishing flair — built on the "
                "familiar comfort of the original."),
            category_id=base.category_id, cuisine=fusion_origin[1],
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=(base.calories or 400) + 20,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(new_instructions),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '420'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 71 == 0),
            is_editors_pick=False,
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 9 - 4) * 0.02)), 1),
            review_count=0,
            author_name='Global-Fusion Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or 'stovetop',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Refrigerate up to 4 days. Bold flavors hold up well to reheating.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Freezer-meal variants (every 3rd eligible base — meal-prep for the freezer)
# ===========================================================================

FREEZER_INSTRUCTIONS = [
    "Assemble the dish in a freezer-safe container (foil pan, 9x13 baking dish lined with parchment, or quart-size zipper bag for soups).",
    "Cool to room temperature first — packing a hot dish into the freezer warms everything else and risks the food safety zone.",
    "Label with the recipe name, date, and reheating instructions. Press parchment directly onto the surface before sealing to prevent freezer burn.",
    "Freeze flat for up to 3 months. To cook, thaw overnight in the refrigerator (best) or use the defrost setting on the microwave for 6 to 8 minutes.",
    "Reheat at 350°F covered for 25 to 35 minutes; remove the cover for the last 5 minutes to crisp the top. Stir soups halfway and check seasoning.",
]


def _seed_freezer_meal_variants(cat_by_slug, base_recipes, existing_slugs):
    """Freezer-meal variant for every 3rd eligible base — anything that
    freezes well: soups, stews, casseroles, sauces, baked goods."""
    skip_cats = {'salads', 'appetizers'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 3 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap',
                'Make-Ahead', 'Kid-Friendly', 'Global-Fusion', 'Freezer-Meal')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug in skip_cats:
            continue
        new_title = f"Freezer-Meal {base.title}"
        new_slug = f"freezer-meal-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(15, base_prep + 5)
        new_cook = max(20, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '1 freezer-safe container or zipper bag',
            '1 sheet parchment paper (to press onto the surface)',
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
            'freezer-meal', 'freezer-friendly', 'meal-prep', 'batch-cook',
            'big-batch', base_cat_slug or 'dinner']))
        img_n = ((ri * 197 + 19) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Freezer-meal photos',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 199 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 211 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 223 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 29 + 17) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A freezer-meal version of {base.title}. Batch-cook on Sunday, "
                "stash in the freezer, and pull a homemade dinner whenever weeknight chaos hits. Freezes 3 months."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '8',
            calories=base.calories or 400,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(FREEZER_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '400'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 59 == 0),
            is_editors_pick=(ri % 83 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 7 - 3) * 0.02)), 1),
            review_count=0,
            author_name='Freezer-Meal Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method,
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions=(
                'Freeze up to 3 months. Thaw in fridge overnight; reheat covered at 350°F '
                'for 25-35 minutes. Stir soups halfway.'),
            primary_seasoning='', max_oven_temp=350,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# R5 chef extension — 3 more chefs (Nordic, West African, Filipino)
# ===========================================================================

R5_CHEF_RECIPES = [
    ('Chef Ingrid Lindqvist', 'Nordic', [
        ('Gravlax with Mustard Sauce',     'gravlax-mustard-sauce',     'seafood',   'Nordic',         ['gluten-free', 'pescatarian', 'dairy-free'], ['2 lb fresh salmon fillet', '1/3 cup kosher salt', '1/3 cup sugar', '1 large bunch fresh dill', '2 tbsp aquavit', 'Coarse black pepper'], 20, 0),
        ('Smoked Salmon Smorrebrod',       'smoked-salmon-smorrebrod',  'breakfast', 'Nordic',         ['pescatarian'], ['4 slices dense rye bread', '8 oz cold-smoked salmon', '4 tbsp creme fraiche', '2 tbsp capers', '1 red onion, thinly sliced', 'Fresh dill'], 10, 0),
        ('Swedish Pea Soup with Bacon',    'swedish-pea-soup-bacon',    'soups',     'Nordic',         [], ['2 cups yellow split peas', '6 oz thick-cut bacon', '1 onion', '2 carrots', '1 tsp dried marjoram', '6 cups stock'], 15, 90),
        ('Norwegian Cardamom Buns',        'norwegian-cardamom-buns',   'breakfast', 'Nordic',         ['vegetarian'], ['4 cups bread flour', '1 cup whole milk', '1/2 cup butter', '1/2 cup sugar', '2 tsp ground cardamom', '1 packet active dry yeast', '2 eggs'], 30, 25),
    ]),
    ('Chef Adaeze Okoye', 'West African', [
        ('Jollof Rice Festive',           'jollof-rice-festive',        'side-dishes', 'West African',  ['vegan', 'vegetarian', 'gluten-free', 'dairy-free'], ['3 cups long-grain rice', '4 Roma tomatoes', '2 red bell peppers', '1 large onion', '2 Scotch bonnet peppers', '3 tbsp tomato paste', '1 tsp curry powder', '1 tsp dried thyme', '3 cups stock'], 20, 50),
        ('Suya Beef Skewers',              'suya-beef-skewers',          'beef',        'West African',  ['gluten-free', 'dairy-free'], ['2 lb beef sirloin, thinly sliced', '1/4 cup peanut powder', '2 tbsp suya spice (yaji)', '1 tbsp smoked paprika', '1 tbsp ginger powder', 'Bamboo skewers'], 25, 12),
        ('Egusi Stew Lagos-Style',         'egusi-stew-lagos',           'soups',       'West African',  ['gluten-free', 'dairy-free'], ['1 lb beef or goat meat', '1 cup ground egusi (melon seeds)', '1 lb spinach', '1/2 cup palm oil', '2 dried crayfish (ground)', '2 Scotch bonnet peppers', '1 onion'], 25, 75),
        ('Plantain Chips Crispy',          'plantain-chips-crispy',      'appetizers',  'West African',  ['vegan', 'vegetarian', 'gluten-free', 'dairy-free'], ['3 green plantains', 'Oil for frying', '1 tsp sea salt', '1/4 tsp cayenne pepper'], 10, 8),
    ]),
    ('Chef Joaquin Reyes', 'Filipino', [
        ('Chicken Adobo Classic',          'chicken-adobo-classic',      'chicken',     'Filipino',      ['gluten-free', 'dairy-free'], ['3 lb bone-in chicken thighs', '1/2 cup soy sauce', '1/3 cup cane vinegar', '1 head garlic, smashed', '6 bay leaves', '1 tbsp black peppercorns'], 10, 50),
        ('Pancit Bihon Noodles',           'pancit-bihon-noodles',       'pasta',       'Filipino',      ['dairy-free'], ['1 lb rice vermicelli', '1 lb chicken or pork', '1 cup green beans', '1 carrot, julienned', '1/2 head cabbage', '1/4 cup soy sauce', '2 tbsp fish sauce', '2 limes'], 20, 25),
        ('Lumpia Shanghai',                'lumpia-shanghai',            'appetizers',  'Filipino',      [], ['1 lb ground pork', '1/2 lb shrimp, minced', '1 carrot, grated', '4 green onions, minced', '30 lumpia wrappers', '1 egg', 'Oil for frying'], 25, 15),
        ('Halo Halo Refreshing',           'halo-halo-refreshing',       'desserts',    'Filipino',      ['vegetarian'], ['Shaved ice', '1/4 cup sweetened red beans', '1/4 cup sweetened jackfruit', '1/4 cup nata de coco', '2 tbsp ube ice cream', '2 tbsp leche flan'], 15, 0),
    ]),
]


def _seed_r5_chef_recipes(cat_by_slug, existing_slugs):
    """Insert ~12 new chef recipes spread across 3 R5 chefs."""
    added = 0
    ri = 0
    for chef_name, specialty, recipe_list in R5_CHEF_RECIPES:
        for (title, slug, cat_slug, cuisine, dietary, hero_ings, prep_m, cook_m) in recipe_list:
            if slug in existing_slugs:
                ri += 1
                continue
            existing_slugs.add(slug)
            cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('dinner')
            total_m = prep_m + cook_m
            cal_base = {'desserts': 320, 'beef': 540, 'pork': 480, 'lamb': 520,
                        'chicken': 380, 'seafood': 320, 'pasta': 470, 'vegan': 320,
                        'vegetarian': 360, 'side-dishes': 320, 'appetizers': 220,
                        'breakfast': 320, 'soups': 280, 'salads': 220}.get(cat_slug, 380)
            cal = cal_base + len(hero_ings) * 6
            nut = {
                'Calories': str(cal),
                'Fat': f"{12 + ri % 14}g",
                'Saturated Fat': f"{3 + ri % 5}g",
                'Carbs': f"{30 + ri % 20}g",
                'Protein': f"{20 + ri % 14}g",
                'Fiber': f"{4 + ri % 6}g",
                'Sugar': f"{6 + ri % 10}g",
                'Sodium': f"{440 + (ri * 17) % 380}mg",
                'Cholesterol': f"{50 + ri % 80}mg",
            }
            instructions = [
                f"Gather all ingredients for {title}, a signature dish from {chef_name} ({specialty} cooking).",
                "Prep proteins and vegetables; season generously and bring proteins to room temperature.",
                "Build the dish in layers — aromatics, then protein, then the signature sauce or spice mix that defines the cuisine.",
                f"Cook for about {cook_m} minutes, tasting and adjusting seasoning halfway through.",
                "Rest 5 minutes off heat so flavors come together; garnish with the traditional finishing herbs or condiments.",
            ]
            gallery = [{
                'title': f'Behind the dish — {chef_name}',
                'desc': f"Step-by-step photos for {title}.",
                'images': [
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 179 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 181 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 191 + 67) % IMAGE_POOL_SIZE) + 1}.jpg",
                ],
            }]
            feature_tags = [cat_slug, _slugify(cuisine), 'signature',
                            'chef-pick', _slugify(specialty)] + dietary
            feature_tags = list(dict.fromkeys(feature_tags))
            img_n = ((ri * 193 + 17) % IMAGE_POOL_SIZE) + 1
            created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 23 + 37) % 720)
            rec = Recipe(
                title=title, slug=slug,
                description=(
                    f"{title} — a signature {cat_slug.replace('-', ' ')} dish from "
                    f"{chef_name}, drawing on {specialty.lower()} cooking traditions."),
                category_id=cat.id if cat else None,
                cuisine=cuisine,
                image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
                prep_time=_fmt_mins(prep_m),
                cook_time=_fmt_mins(cook_m) if cook_m else '0 mins',
                total_time=_fmt_mins(total_m),
                servings=str(4 + ri % 4),
                calories=cal,
                ingredients_json=json.dumps(hero_ings),
                instructions_json=json.dumps(instructions),
                nutrition_json=json.dumps(nut),
                tags_json=json.dumps(feature_tags),
                gallery_json=json.dumps(gallery),
                is_featured=(ri % 4 == 0),
                is_editors_pick=(ri % 5 == 0),
                avg_rating=round(4.6 + (ri * 3 % 4) * 0.1, 1),
                review_count=180 + (ri * 19 % 220),
                author_name=chef_name,
                prep_time_mins=prep_m, cook_time_mins=cook_m, total_time_mins=total_m,
                ingredient_count=len(hero_ings),
                dietary_tags_json=json.dumps(dietary),
                dish_type='', meal_type='', cooking_method='',
                main_ingredient='',
                occasion='', season='',
                feature_tags=json.dumps(feature_tags),
                latest_review_text='',
                storage_instructions='Best fresh; leftovers refrigerated up to 3 days.',
                primary_seasoning='', max_oven_temp=0,
                created_at=created,
            )
            db.session.add(rec)
            added += 1
            ri += 1
    return added


# ===========================================================================
# Public entry point — called from seed_data.seed_extended_catalog
# ===========================================================================

R5_SENTINEL_SLUG = 'make-ahead-coq-au-vin-maison'


def run_r5_polish(cat_by_slug):
    """R5 top-level. Returns a counts dict."""
    # Sentinel: any R5 variant or chef recipe means we already ran.
    if (Recipe.query.filter_by(slug=R5_SENTINEL_SLUG).first()
            or Recipe.query.filter_by(slug='chicken-adobo-classic').first()):
        return {'skipped': True}

    counts = {}

    # 1) R5 chef recipes — fresh slugs, run first.
    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['r5_chef'] = _seed_r5_chef_recipes(cat_by_slug, existing_recipe_slugs)
    db.session.flush()

    # 2) New variant passes — base = Test Kitchen recipes that are NOT R4
    # variants (so we don't recurse on variants of variants).
    base_for_r5 = (Recipe.query
                   .filter(Recipe.author_name.like('%Test Kitchen%'))
                   .order_by(Recipe.id)
                   .all())
    base_for_r5 = [
        r for r in base_for_r5
        if not any(tok in (r.author_name or '') for tok in (
            'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap',
            'Make-Ahead', 'Kid-Friendly', 'Global-Fusion'))
    ]
    print(f"[r5_seed] base_for_r5 size: {len(base_for_r5)}")

    counts['make_ahead'] = _seed_make_ahead_variants(cat_by_slug, base_for_r5, existing_recipe_slugs)
    db.session.flush()
    counts['kid_friendly'] = _seed_kid_friendly_variants(cat_by_slug, base_for_r5, existing_recipe_slugs)
    db.session.flush()
    counts['global_fusion'] = _seed_global_fusion_variants(cat_by_slug, base_for_r5, existing_recipe_slugs)
    db.session.flush()
    counts['freezer_meal'] = _seed_freezer_meal_variants(cat_by_slug, base_for_r5, existing_recipe_slugs)
    db.session.flush()

    # 3) Enrich EVERY recipe with R5 fields.
    _enrich_r5_fields()
    db.session.flush()

    return counts
