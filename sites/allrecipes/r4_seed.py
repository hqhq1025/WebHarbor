"""R4 polish seed: recipe enrichment + new variant passes + Collections + Articles.

This module is imported by ``seed_data.seed_extended_catalog`` and runs after
all existing recipes are inserted but BEFORE the review pass. Everything in
here is fully deterministic so a rebuild from source is byte-identical to the
shipped ``instance_seed/allrecipes.db``.

R4 deliverables:
  * +1500 new recipes via four new variant passes (seasonal / one-pot /
    sheet-pan / healthy-swap) plus ~40 named-chef recipes.
  * Enrichment of *every* existing recipe so it has >=5 tags, full nutrition
    (Fiber/Sugar/Sodium/Saturated Fat) and a 3-step image gallery.
  * 10 curated Collections (e.g. Best Summer Grilling, 30 Days Slow Cooker).
  * 25 cooking-tip Articles for ``/article/<slug>``.

Idempotent — gated on the presence of a sentinel collection slug.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta

from app import (
    db, Category, Recipe, Article, Collection,
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
# Phase 1 — Recipe enrichment (tags >=5, nutrition complete, 3-step gallery)
# ===========================================================================

# Cuisine label -> a 1-word slug tag we drop in feature_tags so the cuisine
# survives the >=5 tag rule even when its display label has spaces.
_CUISINE_SLUG_OVERRIDE = {
    'Latin American': 'latin-american',
    'Middle Eastern': 'middle-eastern',
}


def _enrich_existing_recipes(*, sentinel_check=True):
    """Top up every recipe so it has >=5 feature_tags + full nutrition + a
    3-step image gallery. Pure mutation, no new rows, deterministic."""
    recipes = Recipe.query.order_by(Recipe.id).all()
    touched_tags = 0
    touched_nutrition = 0
    touched_gallery = 0
    for r in recipes:
        try:
            feats = json.loads(r.feature_tags or '[]')
        except Exception:
            feats = []
        if not isinstance(feats, list):
            feats = []

        # ---- Top up tags from category + dish_type + meal_type + cuisine +
        # cooking_method + main_ingredient + occasion + dietary_tags ----
        addable = []
        if r.dish_type:
            addable.append(r.dish_type)
        if r.meal_type:
            addable.append(r.meal_type)
        if r.cuisine:
            addable.append(_CUISINE_SLUG_OVERRIDE.get(r.cuisine, r.cuisine.lower()))
        if r.cooking_method:
            addable.append(r.cooking_method.replace(' ', '-'))
        if r.main_ingredient:
            addable.append(r.main_ingredient.lower())
        if r.occasion:
            addable.append(r.occasion)
        try:
            dietary = json.loads(r.dietary_tags_json or '[]')
            for d in dietary:
                if d:
                    addable.append(d)
        except Exception:
            pass
        # Time bucket
        if r.total_time_mins:
            if r.total_time_mins <= 30:
                addable.append('quick')
            elif r.total_time_mins >= 180:
                addable.append('low-and-slow')
        # Generic dish noun fallback derived from title keywords.
        title_low = (r.title or '').lower()
        title_kws = ['salad', 'soup', 'stew', 'casserole', 'pasta', 'pie',
                     'cake', 'cookie', 'bread', 'sandwich', 'pizza',
                     'curry', 'risotto', 'tacos', 'wrap']
        for kw in title_kws:
            if kw in title_low:
                addable.append(kw)
                break

        for tok in addable:
            tok = (tok or '').strip().lower().replace(' ', '-')
            if tok and tok not in feats:
                feats.append(tok)
            if len(feats) >= 7:
                break

        # Fallback filler tags so EVERY recipe has >=5.
        filler_pool = ['family-friendly', 'crowd-pleaser', 'weeknight',
                       'classic', 'comfort-food', 'home-cooked']
        fi = 0
        while len(feats) < 5 and fi < len(filler_pool):
            cand = filler_pool[fi]
            if cand not in feats:
                feats.append(cand)
            fi += 1
        r.feature_tags = json.dumps(feats)
        touched_tags += 1

        # ---- Nutrition top-up ----
        try:
            nut = json.loads(r.nutrition_json or '{}')
        except Exception:
            nut = {}
        if not isinstance(nut, dict):
            nut = {}
        cal = int(re.findall(r"\d+", str(nut.get('Calories') or r.calories or '360'))[0] or 360)
        rid = r.id or 1
        if 'Calories' not in nut:
            nut['Calories'] = str(cal)
        if 'Fat' not in nut:
            nut['Fat'] = f"{10 + (rid * 7) % 22}g"
        if 'Saturated Fat' not in nut:
            # 25-40% of total fat — deterministic.
            fat_n = int(re.findall(r"\d+", nut['Fat'])[0])
            nut['Saturated Fat'] = f"{max(1, fat_n // 3)}g"
        if 'Carbs' not in nut:
            nut['Carbs'] = f"{20 + (rid * 11) % 40}g"
        if 'Protein' not in nut:
            nut['Protein'] = f"{14 + (rid * 5) % 26}g"
        if 'Fiber' not in nut:
            nut['Fiber'] = f"{2 + (rid * 3) % 8}g"
        if 'Sugar' not in nut:
            nut['Sugar'] = f"{4 + (rid * 13) % 20}g"
        if 'Sodium' not in nut:
            nut['Sodium'] = f"{280 + (rid * 17) % 520}mg"
        if 'Cholesterol' not in nut:
            nut['Cholesterol'] = f"{30 + (rid * 19) % 110}mg"
        r.nutrition_json = json.dumps(nut)
        touched_nutrition += 1

        # ---- 3-step image gallery ----
        try:
            gallery = json.loads(r.gallery_json or '[]')
        except Exception:
            gallery = []
        if not isinstance(gallery, list):
            gallery = []
        if not gallery:
            n = rid
            step_imgs = [
                f"{IMAGES_DIR_REL}/recipe_{((n * 7 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((n * 13 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((n * 19 + 89) % IMAGE_POOL_SIZE) + 1}.jpg",
            ]
            gallery = [{
                'title': 'Step-by-step photos',
                'desc': f"Visual walkthrough for {r.title}.",
                'images': step_imgs,
            }]
            r.gallery_json = json.dumps(gallery)
            touched_gallery += 1

    db.session.flush()
    print(f"[r4_seed] enriched tags={touched_tags} nutrition={touched_nutrition} galleries={touched_gallery}")


# ===========================================================================
# Phase 2 — New variant passes (seasonal / one-pot / sheet-pan / healthy-swap)
# ===========================================================================

SEASONAL_VARIANT_RULES = {
    # category -> (season label, season slug, prep_delta, cook_factor, hero_ingredients)
    'beef':         ('Winter',  'winter',  5,  1.2,  ['1 cup red wine', '2 sprigs rosemary']),
    'pork':         ('Autumn',  'autumn',  5,  1.1,  ['2 apples, sliced', '1/4 cup apple cider']),
    'lamb':         ('Spring',  'spring',  5,  1.0,  ['1 bunch fresh mint', '1 cup peas']),
    'chicken':      ('Summer',  'summer', -2,  0.9,  ['1 lemon, sliced', '1 bunch fresh basil']),
    'seafood':      ('Summer',  'summer', -2,  0.8,  ['1 lime, wedged', '1 cup cherry tomatoes']),
    'pasta':        ('Spring',  'spring',  0,  1.0,  ['1 cup peas', '1/4 cup fresh parsley']),
    'vegetarian':   ('Autumn',  'autumn',  0,  1.0,  ['1 butternut squash, cubed', '2 sprigs sage']),
    'vegan':        ('Summer',  'summer',  0,  0.8,  ['1 zucchini, sliced', '1 cup cherry tomatoes']),
    'side-dishes':  ('Autumn',  'autumn',  0,  1.0,  ['1 acorn squash, cubed', '2 tbsp maple syrup']),
    'appetizers':   ('Winter',  'winter',  0,  1.0,  ['1 wheel brie cheese', '1/4 cup cranberry sauce']),
    'breakfast':    ('Spring',  'spring',  0,  0.9,  ['1 cup strawberries', '2 tbsp lemon zest']),
    'desserts':     ('Summer',  'summer',  0,  0.9,  ['1 lb berries', '1 cup whipped cream']),
    'dinner':       ('Winter',  'winter',  5,  1.2,  ['1 cup beef stock', '1 tbsp dried thyme']),
    'soups':        ('Winter',  'winter',  0,  1.1,  ['1 leek, sliced', '1 parsnip, diced']),
    'salads':       ('Summer',  'summer',  0,  0.5,  ['1 cup heirloom tomatoes', '1/4 cup torn basil']),
}

ONE_POT_INSTRUCTIONS = [
    "Heat 2 tbsp oil in a large Dutch oven or heavy pot over medium-high heat.",
    "Brown the protein on all sides, about 6 minutes, then push to the side of the pot.",
    "Add aromatics and any vegetables; cook 4 to 5 minutes until softened.",
    "Pour in the liquid, scraping the bottom of the pot to release the browned bits.",
    "Bring to a simmer, cover, and cook 30 to 45 minutes until everything is tender. Serve straight from the pot.",
]

SHEET_PAN_INSTRUCTIONS = [
    "Preheat the oven to 425°F (218°C) and line a large sheet pan with parchment.",
    "Toss every ingredient on the pan with olive oil, salt and pepper.",
    "Arrange in a single layer with the densest vegetables at the edges (where heat is higher).",
    "Roast 22 to 28 minutes, flipping halfway, until everything is golden brown and tender.",
    "Squeeze fresh lemon over the top and finish with chopped herbs. Serve from the pan.",
]

HEALTHY_SWAP_INSTRUCTIONS = [
    "Prep all ingredients. Substitute Greek yogurt for sour cream, whole-grain pasta or rice for white, and olive oil for butter wherever possible.",
    "Heat 1 tablespoon of olive oil in a non-stick pan over medium heat.",
    "Build the dish in layers: aromatics first, then proteins, then vegetables and the lightened sauce.",
    "Reduce salt by half and rely on lemon, vinegar, and fresh herbs to brighten the dish at the end.",
    "Plate with a generous handful of leafy greens on the side for extra fiber and color.",
]


def _seed_seasonal_variants(cat_by_slug, base_recipes, existing_slugs):
    """One seasonal variant per eligible base — Winter/Spring/Summer/Autumn."""
    added = 0
    for ri, base in enumerate(base_recipes):
        if base.author_name and ' Test Kitchen' not in base.author_name:
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if not base_cat_slug or base_cat_slug not in SEASONAL_VARIANT_RULES:
            continue
        season_label, season_slug, prep_delta, cook_factor, hero_ings = SEASONAL_VARIANT_RULES[base_cat_slug]
        new_title = f"{season_label} {base.title}"
        new_slug = f"{season_slug}-{base.slug}"
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
        new_ings = list(base_ings) + hero_ings
        new_instr = []
        try:
            new_instr = json.loads(base.instructions_json or '[]')[:5]
        except Exception:
            new_instr = []
        new_instr.append(
            f"For a {season_label.lower()} touch, fold in the seasonal additions during the last 5 minutes of cooking and finish with extra herbs.")
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        new_features = list(dict.fromkeys(base_features + [
            season_slug, f'{season_slug}-recipe', 'seasonal', base_cat_slug]))
        img_n = ((ri * 31 + 7) % IMAGE_POOL_SIZE) + 1
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 4 + 13) % 720)
        cal = (base.calories or 360) + (10 if season_label in ('Winter', 'Autumn') else -20)
        # Gallery — 3 deterministic step images.
        gallery = [{
            'title': f'{season_label} prep',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 11 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 17 + 47) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 23 + 71) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=f"A {season_label.lower()}-seasonal twist on {base.title}. Built around the produce and pantry items at their peak in {season_label.lower()}.",
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4', calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(new_instr),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 43 == 0),
            is_editors_pick=(ri % 73 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.3) + ((ri % 5 - 2) * 0.04)), 1),
            review_count=0,
            author_name=f"{season_label} Seasonal Test Kitchen",
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method,
            main_ingredient=base.main_ingredient,
            occasion='', season=season_slug,
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions=f'Best eaten fresh in {season_label.lower()}. Refrigerate leftovers up to 3 days in an airtight container.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


def _seed_one_pot_variants(cat_by_slug, base_recipes, existing_slugs):
    """One-pot/Dutch-oven variant for every other eligible main-dish base."""
    eligible_cats = {'beef', 'pork', 'lamb', 'chicken', 'pasta', 'dinner',
                     'vegetarian', 'vegan', 'soups'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 2 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug not in eligible_cats:
            continue
        new_title = f"One-Pot {base.title}"
        new_slug = f"one-pot-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep - 3)
        new_cook = max(15, int(base_cook * 0.9))
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + ['1 cup broth (to deglaze the pot)']
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'one-pot', 'easy-cleanup', 'dutch-oven', base_cat_slug]))
        img_n = ((ri * 37 + 19) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'One-pot photos',
            'desc': f"Visual walkthrough for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 41 + 5) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 43 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 47 + 53) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 6 + 19) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=f"Everything cooks in a single Dutch oven so cleanup is one pot, max. Same comforting flavors of {base.title}, none of the dish stack.",
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=(base.calories or 380),
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(ONE_POT_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '380'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=False, is_editors_pick=(ri % 79 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 7 - 3) * 0.03)), 1),
            review_count=0,
            author_name='One-Pot Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method='stovetop', main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Refrigerate leftovers in the pot or transfer to an airtight container; keeps 4 days.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


def _seed_sheet_pan_variants(cat_by_slug, base_recipes, existing_slugs):
    """Sheet-pan variant for every third eligible base."""
    eligible_cats = {'chicken', 'pork', 'seafood', 'vegetarian', 'vegan',
                     'side-dishes', 'breakfast', 'dinner'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 3 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug not in eligible_cats:
            continue
        new_title = f"Sheet-Pan {base.title}"
        new_slug = f"sheet-pan-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        new_prep = max(10, base_prep - 5)
        new_cook = 25
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + ['2 tbsp olive oil',
                                       'Salt and pepper to taste',
                                       '1 sheet parchment paper']
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_features = list(dict.fromkeys(base_features + [
            'sheet-pan', 'roasted', 'easy-cleanup', 'oven', base_cat_slug]))
        img_n = ((ri * 53 + 11) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Sheet-pan photos',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 59 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 61 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 67 + 53) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 8 + 23) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=f"A sheet-pan version of {base.title} — everything roasts together for hands-off weeknight cooking.",
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=base.calories or 360,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(SHEET_PAN_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': '360'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 31 == 0), is_editors_pick=False,
            avg_rating=round(min(5.0, (base.avg_rating or 4.5) + ((ri % 5 - 2) * 0.04)), 1),
            review_count=0,
            author_name='Sheet-Pan Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method='roasted', main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Refrigerate in an airtight container up to 3 days. Reheat at 350°F for 8-10 minutes.',
            primary_seasoning='', max_oven_temp=425,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


def _seed_healthy_swap_variants(cat_by_slug, base_recipes, existing_slugs):
    """Healthy-swap (lower fat, lower sodium, more fiber) variant per
    every fourth eligible base."""
    eligible_cats = {'beef', 'pork', 'chicken', 'pasta', 'desserts',
                     'breakfast', 'vegetarian', 'dinner', 'seafood'}
    added = 0
    for ri, base in enumerate(base_recipes):
        if ri % 4 != 0:
            continue
        if base.author_name and any(tok in base.author_name for tok in (
                'Seasonal', 'One-Pot', 'Sheet-Pan', 'Healthy-Swap')):
            continue
        base_cat_slug = None
        if base.category_id:
            for slug, c in cat_by_slug.items():
                if c.id == base.category_id:
                    base_cat_slug = slug
                    break
        if base_cat_slug not in eligible_cats:
            continue
        new_title = f"Healthy-Swap {base.title}"
        new_slug = f"healthy-swap-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 30
        new_prep = max(5, base_prep)
        new_cook = max(5, int(base_cook * 0.9))
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            'Substitute Greek yogurt for sour cream',
            'Use whole-grain pasta or brown rice in place of white',
            'Reduce salt by half; finish with lemon zest instead',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = list(dict.fromkeys(base_dietary + ['high-fiber', 'low-sodium']))
        new_features = list(dict.fromkeys(base_features + [
            'healthy', 'better-for-you', 'lighter', 'low-sodium', 'high-fiber',
            base_cat_slug]))
        img_n = ((ri * 71 + 17) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Healthy-swap photos',
            'desc': f"Step-by-step photos for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 73 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 79 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 83 + 67) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        new_cal = max(140, (base.calories or 360) - 80)
        nut = {
            'Calories': str(new_cal),
            'Fat': f"{8 + ri % 8}g",
            'Saturated Fat': f"{2 + ri % 4}g",
            'Carbs': f"{24 + ri % 18}g",
            'Protein': f"{20 + ri % 10}g",
            'Fiber': f"{6 + ri % 5}g",
            'Sugar': f"{4 + ri % 6}g",
            'Sodium': f"{240 + (ri * 7) % 220}mg",
        }
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 9 + 29) % 720)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=f"A lighter take on {base.title}. We swap full-fat dairy for Greek yogurt, cut sodium by half, and bump up the fiber. Same family-loved flavors, dialed-in for everyday eating.",
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4', calories=new_cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(HEALTHY_SWAP_INSTRUCTIONS)),
            nutrition_json=json.dumps(nut),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=False, is_editors_pick=(ri % 41 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.3) + ((ri % 5 - 2) * 0.03)), 1),
            review_count=0,
            author_name='Healthy-Swap Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or 'stovetop',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Refrigerate up to 4 days; freeze portions for up to 2 months.',
            primary_seasoning='', max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Phase 3 — Allstar / named-chef recipes (40 deterministic chefs)
# ===========================================================================

CHEF_RECIPES = [
    # (chef_name, recipes:[(title, slug, cat_slug, cuisine, dietary, ing_list, prep, cook)])
    ('Chef Marie Laurent', 'French', [
        ('Coq au Vin Maison',           'coq-au-vin-maison',          'chicken',  'French',        [],                ['1 whole chicken, cut up', '1 bottle Burgundy wine', '8 oz pearl onions', '8 oz mushrooms', '4 oz bacon', '1 bouquet garni'], 25, 90),
        ('Beef Bourguignon Sunday',     'beef-bourguignon-sunday',    'beef',     'French',        [],                ['3 lb beef chuck', '1 bottle red wine', '8 oz lardons', '1 lb pearl onions', '1 lb mushrooms', '3 carrots', '1 bouquet garni'], 30, 180),
        ('Croque Madame Brunch',        'croque-madame-brunch',       'breakfast','French',        ['vegetarian'],    ['8 slices sourdough', '8 slices gruyere', '8 slices ham', '4 eggs', '1 cup bechamel', '2 tbsp butter'], 15, 18),
        ('Lemon Tart Classique',        'lemon-tart-classique',       'desserts', 'French',        ['vegetarian'],    ['1 pre-baked tart shell', '6 lemons', '4 eggs', '1 1/4 cups sugar', '1/2 cup butter'], 20, 12),
        ('Ratatouille Provençale',      'ratatouille-provencale',     'vegan',    'French',        ['vegan','gluten-free','vegetarian'], ['2 zucchini', '1 eggplant', '2 bell peppers', '4 tomatoes', '1 onion', '6 cloves garlic', '1/4 cup olive oil', 'Fresh thyme'], 30, 60),
    ]),
    ('Chef Marcus Bell', 'Southern', [
        ('Shrimp & Grits Lowcountry',   'shrimp-grits-lowcountry',    'seafood',  'American',      [],                ['1 lb large shrimp', '1 cup stone-ground grits', '4 oz bacon', '1 cup sharp cheddar', '4 cups stock', '2 green onions'], 15, 35),
        ('Buttermilk Fried Chicken',    'buttermilk-fried-chicken',   'chicken',  'American',      [],                ['1 whole chicken, cut up', '2 cups buttermilk', '2 cups flour', '2 tbsp paprika', '1 tbsp garlic powder', 'Oil for frying'], 30, 30),
        ('Sweet Potato Pie Holiday',    'sweet-potato-pie-holiday',   'desserts', 'American',      ['vegetarian'],    ['3 lb sweet potatoes', '1 cup brown sugar', '3 eggs', '1 cup evaporated milk', '1 pie crust', '1 tsp cinnamon'], 20, 55),
        ('Collard Greens Slow-Cooked',  'collard-greens-slow-cooked', 'side-dishes','American',    ['gluten-free'],   ['3 lb collard greens', '1 smoked ham hock', '1 onion', '4 cloves garlic', '6 cups stock', '1 tbsp apple cider vinegar'], 20, 120),
    ]),
    ('Chef Yuki Tanaka', 'Japanese', [
        ('Miso Glazed Salmon',          'miso-glazed-salmon',          'seafood',  'Japanese',      ['gluten-free','pescatarian'], ['4 salmon fillets', '1/3 cup white miso', '3 tbsp mirin', '2 tbsp sake', '2 tbsp sugar'], 15, 12),
        ('Chicken Katsu Curry',         'chicken-katsu-curry',         'chicken',  'Japanese',      [],                ['4 chicken breasts', '2 cups panko', '2 eggs', '1 box Japanese curry roux', '1 onion', '2 carrots', '2 potatoes'], 20, 35),
        ('Ramen Tonkotsu Bowl',         'ramen-tonkotsu-bowl',         'soups',    'Japanese',      [],                ['4 servings ramen noodles', '2 lb pork bones', '1 onion', '6 cloves garlic', '2 inch ginger', '4 soft-boiled eggs', 'Green onions'], 30, 360),
        ('Onigiri Salmon Rice Balls',   'onigiri-salmon-rice-balls',   'appetizers','Japanese',     ['pescatarian','gluten-free'], ['3 cups sushi rice', '4 oz cooked salmon', '4 sheets nori', '1 tbsp sesame seeds', 'Salt'], 15, 25),
    ]),
    ('Chef Priya Sharma', 'Indian', [
        ('Butter Chicken Punjabi',      'butter-chicken-punjabi',      'chicken',  'Indian',        ['gluten-free'],   ['2 lb chicken thighs', '1 cup yogurt', '2 tbsp garam masala', '1 (28 oz) can tomatoes', '1/2 cup heavy cream', '1/4 cup butter', '1 tbsp ginger', '4 cloves garlic'], 30, 35),
        ('Aloo Gobi Spiced',            'aloo-gobi-spiced',            'vegetarian','Indian',       ['vegetarian','vegan','gluten-free','dairy-free'], ['1 head cauliflower', '4 potatoes', '1 onion', '2 tomatoes', '1 tbsp turmeric', '1 tbsp cumin', '1 tbsp coriander'], 15, 30),
        ('Dal Tadka Classic',           'dal-tadka-classic',           'vegetarian','Indian',       ['vegetarian','vegan','gluten-free','dairy-free'], ['1 cup toor dal', '1 onion', '3 tomatoes', '2 green chiles', '1 tbsp cumin seeds', '1 tbsp ghee', 'Fresh cilantro'], 10, 40),
        ('Naan Garlic-Butter',          'naan-garlic-butter',          'breakfast','Indian',        ['vegetarian'],    ['3 cups flour', '1 cup yogurt', '1 tsp baking powder', '4 cloves garlic, minced', '1/2 cup butter', 'Fresh cilantro'], 15, 10),
    ]),
    ('Chef Sofia Romano', 'Italian', [
        ('Cacio e Pepe Classic',        'cacio-e-pepe-classic',        'pasta',    'Italian',       ['vegetarian'],    ['1 lb tonnarelli pasta', '1 1/2 cups Pecorino Romano', '2 tbsp black peppercorns'], 5, 15),
        ('Tiramisu Authentic',          'tiramisu-authentic',          'desserts', 'Italian',       ['vegetarian'],    ['24 ladyfingers', '1 1/4 cups espresso', '6 eggs, separated', '3/4 cup sugar', '1 lb mascarpone', '1/4 cup Marsala', 'Cocoa powder'], 30, 0),
        ('Osso Buco Milanese',          'osso-buco-milanese',          'beef',     'Italian',       ['gluten-free'],   ['4 veal shanks', '1 cup white wine', '2 cups stock', '1 onion', '2 carrots', '2 stalks celery', 'Gremolata to finish'], 20, 150),
        ('Risotto Funghi Porcini',      'risotto-funghi-porcini',      'pasta',    'Italian',       ['vegetarian','gluten-free'], ['1 1/2 cups arborio rice', '1 oz dried porcini', '4 cups stock', '1/2 cup white wine', '1/2 cup parmesan', '2 tbsp butter'], 10, 25),
    ]),
    ('Chef Diego Hernandez', 'Mexican', [
        ('Mole Poblano Festivo',        'mole-poblano-festivo',        'chicken',  'Mexican',       ['gluten-free'],   ['1 whole chicken', '4 ancho chiles', '4 pasilla chiles', '2 oz Mexican chocolate', '2 tbsp sesame seeds', '1 cup tomato puree', 'Spice mix'], 45, 90),
        ('Tacos Carnitas Slow',         'tacos-carnitas-slow',         'pork',     'Mexican',       ['gluten-free','dairy-free'], ['3 lb pork shoulder', '1 orange', '1 onion', '6 cloves garlic', '12 corn tortillas', 'Fresh cilantro', '2 limes'], 15, 240),
        ('Pozole Rojo Family',          'pozole-rojo-family',          'soups',    'Mexican',       ['gluten-free'],   ['2 lb pork shoulder', '2 (29 oz) cans hominy', '4 guajillo chiles', '1 onion', '6 cloves garlic', 'Garnishes: cabbage, lime, radish'], 20, 150),
        ('Churros con Chocolate',       'churros-con-chocolate',       'desserts', 'Mexican',       ['vegetarian'],    ['1 cup water', '1 cup flour', '2 eggs', '1/4 cup sugar', 'Oil for frying', '4 oz dark chocolate', '1/2 cup cream'], 20, 20),
    ]),
    ('Chef Olivia Park', 'Asian Fusion', [
        ('Korean Bulgogi Beef',         'korean-bulgogi-beef',         'beef',     'Asian',         ['dairy-free'],    ['2 lb ribeye, thinly sliced', '1/2 cup soy sauce', '1/4 cup brown sugar', '1 Asian pear', '2 tbsp sesame oil', '4 cloves garlic'], 30, 12),
        ('Bibimbap Bowl Veggie',        'bibimbap-bowl-veggie',        'vegetarian','Asian',        ['vegetarian','dairy-free'], ['2 cups short-grain rice', '1 cup spinach', '1 cup bean sprouts', '1 zucchini', '1 carrot', '4 eggs', 'Gochujang sauce'], 25, 25),
        ('Banh Mi Pulled Pork',         'banh-mi-pulled-pork',         'pork',     'Asian',         ['dairy-free'],    ['1 lb pulled pork', '4 baguettes', '1 cucumber', 'Pickled carrots', 'Cilantro', 'Sriracha mayo'], 20, 15),
    ]),
    ('Chef Aisha Patel', 'Mediterranean', [
        ('Falafel Plate Mediterranean', 'falafel-plate-mediterranean', 'vegan',    'Mediterranean', ['vegan','vegetarian','dairy-free'], ['2 cups dried chickpeas (soaked)', '1 onion', '6 cloves garlic', '1/2 cup fresh parsley', '1 tbsp cumin', 'Oil for frying'], 30, 12),
        ('Lamb Kofta Skewers',          'lamb-kofta-skewers',          'lamb',     'Mediterranean', ['gluten-free','dairy-free'], ['2 lb ground lamb', '1 onion', '4 cloves garlic', '2 tbsp cumin', '2 tbsp coriander', 'Fresh parsley'], 20, 12),
        ('Greek Spanakopita Pie',       'greek-spanakopita-pie',       'appetizers','Mediterranean', ['vegetarian'],    ['1 lb spinach', '8 oz feta', '1 cup ricotta', '4 eggs', '1 package phyllo dough', '1/2 cup butter'], 25, 45),
        ('Tahini Roasted Eggplant',     'tahini-roasted-eggplant',     'vegan',    'Mediterranean', ['vegan','vegetarian','dairy-free','gluten-free'], ['2 large eggplants', '1/2 cup tahini', '2 lemons', '4 cloves garlic', '1/4 cup olive oil', 'Pomegranate seeds'], 15, 45),
    ]),
    ('Chef Liam Walsh', 'British', [
        ('Sticky Toffee Pudding',       'sticky-toffee-pudding',       'desserts', 'British',       ['vegetarian'],    ['1 cup chopped dates', '1 1/2 cups boiling water', '1 stick butter', '1 cup brown sugar', '2 eggs', '1 1/2 cups flour', 'Toffee sauce'], 15, 35),
        ('Cottage Pie Sunday',          'cottage-pie-sunday',          'beef',     'British',       [],                ['2 lb ground beef', '2 onions', '3 carrots', '3 lb potatoes', '1 cup beef stock', '2 tbsp Worcestershire', '1 cup peas'], 25, 60),
    ]),
    ('Chef Anika Volkova', 'Eastern European', [
        ('Pierogi Potato Onion',        'pierogi-potato-onion',        'side-dishes','European',    ['vegetarian'],    ['3 cups flour', '2 eggs', '1 cup sour cream', '4 potatoes', '2 onions', '1 stick butter'], 45, 25),
        ('Borscht Ukrainian',           'borscht-ukrainian',           'soups',    'European',      ['vegetarian','gluten-free'], ['4 beets', '1 cabbage', '2 carrots', '2 potatoes', '1 onion', '6 cups stock', '2 tbsp dill', 'Sour cream'], 25, 60),
    ]),
]


def _seed_chef_recipes(cat_by_slug, existing_slugs):
    """Insert 40-ish named-chef recipes spread across 10 chefs."""
    added = 0
    ri = 0
    for chef_name, specialty, recipe_list in CHEF_RECIPES:
        for (title, slug, cat_slug, cuisine, dietary, hero_ings, prep_m, cook_m) in recipe_list:
            if slug in existing_slugs:
                ri += 1
                continue
            existing_slugs.add(slug)
            cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('dinner')
            total_m = prep_m + cook_m
            cal_base = {'desserts': 380, 'beef': 540, 'pork': 480, 'lamb': 520,
                        'chicken': 380, 'seafood': 340, 'pasta': 470, 'vegan': 320,
                        'vegetarian': 360, 'side-dishes': 240, 'appetizers': 220,
                        'breakfast': 320, 'soups': 280, 'salads': 220}.get(cat_slug, 380)
            cal = cal_base + len(hero_ings) * 7
            nut = {
                'Calories': str(cal),
                'Fat': f"{14 + ri % 14}g",
                'Saturated Fat': f"{4 + ri % 6}g",
                'Carbs': f"{28 + ri % 22}g",
                'Protein': f"{18 + ri % 16}g",
                'Fiber': f"{3 + ri % 6}g",
                'Sugar': f"{6 + ri % 12}g",
                'Sodium': f"{420 + (ri * 13) % 420}mg",
                'Cholesterol': f"{50 + ri % 80}mg",
            }
            instructions = [
                f"Gather all ingredients for {title}, a signature dish from {chef_name}.",
                "Pat any proteins dry, salt liberally, and bring to room temperature 20 minutes before cooking.",
                "Heat the pan or oven to working temperature. Build the dish in layers as the recipe directs.",
                f"Cook for about {cook_m} minutes (or until the protein hits its safe internal temp).",
                "Let the dish rest 5 minutes off heat so flavors come together. Serve generously.",
            ]
            gallery = [{
                'title': f'Behind the dish — {chef_name}',
                'desc': f"Step-by-step photos for {title}.",
                'images': [
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 89 + 17) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 97 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 101 + 73) % IMAGE_POOL_SIZE) + 1}.jpg",
                ],
            }]
            feature_tags = [cat_slug, cuisine.lower().replace(' ', '-'),
                            'signature', 'chef-pick', specialty.lower().replace(' ', '-')] + dietary
            feature_tags = list(dict.fromkeys(feature_tags))
            img_n = ((ri * 103 + 13) % IMAGE_POOL_SIZE) + 1
            created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 11 + 31) % 720)
            rec = Recipe(
                title=title, slug=slug,
                description=f"{title} — a signature {cat_slug.replace('-', ' ')} dish from {chef_name}, drawing on the depth of {specialty.lower()} cooking.",
                category_id=cat.id if cat else None,
                cuisine=cuisine,
                image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
                prep_time=_fmt_mins(prep_m),
                cook_time=_fmt_mins(cook_m) if cook_m else '0 mins',
                total_time=_fmt_mins(total_m),
                servings=str(4 + ri % 4), calories=cal,
                ingredients_json=json.dumps(hero_ings),
                instructions_json=json.dumps(instructions),
                nutrition_json=json.dumps(nut),
                tags_json=json.dumps(feature_tags),
                gallery_json=json.dumps(gallery),
                is_featured=(ri % 5 == 0),
                is_editors_pick=(ri % 7 == 0),
                avg_rating=round(4.6 + (ri * 3 % 4) * 0.1, 1),
                review_count=200 + (ri * 17 % 220),
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
# Phase 4 — Collections (curated themed recipe lists)
# ===========================================================================

COLLECTION_DEFS = [
    ('Best Summer Grilling',         'best-summer-grilling',        'Summer', 'Summer', 'BBQ, grilled mains, and refreshing sides for hot-weather entertaining.',
     ['classic-grilled-cheeseburgers', 'watermelon-feta-salad-mint', 'grilled-corn-cob-cotija', 'korean-bulgogi-beef', 'miso-glazed-salmon', 'creamy-coleslaw-classic', 'lamb-kofta-skewers', 'classic-apple-pie-lattice']),
    ('30 Days of Slow Cooker',       'thirty-days-slow-cooker',     'Year-round', '',     'A month of set-and-forget slow cooker dinners — beef stews, pulled pork, soup nights and more.',
     ['slow-cooker-game-day-chili', 'all-american-bbq-pulled-pork', 'slow-cooker-mulled-wine', 'pozole-rojo-family', 'borscht-ukrainian', 'cottage-pie-sunday', 'pierogi-potato-onion', 'banh-mi-pulled-pork']),
    ('Cozy Comfort Food',            'cozy-comfort-food',           'Autumn', 'Autumn', 'Stick-to-your-ribs classics for blanket-and-fireplace weather.',
     ['classic-bread-stuffing-sage', 'brown-butter-mashed-potatoes', 'green-bean-casserole-scratch', 'cottage-pie-sunday', 'osso-buco-milanese', 'risotto-funghi-porcini', 'pierogi-potato-onion', 'sticky-toffee-pudding']),
    ('Best for Picnics',             'best-for-picnics',            'Summer', 'Summer', 'Pack-and-go dishes that travel well to the park or beach.',
     ['avocado-tomato-salad', 'watermelon-feta-salad-mint', 'creamy-coleslaw-classic', 'classic-deviled-eggs', 'falafel-plate-mediterranean', 'onigiri-salmon-rice-balls', 'chocolate-covered-strawberries-valentines']),
    ('Holiday Cookie Box',           'holiday-cookie-box',          'Winter', 'Winter', '12 cookie recipes for filling a tin to gift.',
     ['classic-gingerbread-cookies', 'chocolate-lava-cakes-two', 'yule-log-buche-de-noel', 'churros-con-chocolate', 'red-velvet-cupcakes-valentines', 'pumpkin-spice-cupcakes', 'sticky-toffee-pudding', 'lemon-tart-classique']),
    ('30-Minute Weeknight Dinners',  'thirty-minute-weeknight',     'Year-round', '',     'Dinner on the table in 30 minutes or less, every recipe.',
     ['cacio-e-pepe-classic', 'miso-glazed-salmon', 'falafel-plate-mediterranean', 'naan-garlic-butter', 'aloo-gobi-spiced', 'dal-tadka-classic', 'tahini-roasted-eggplant', 'korean-bulgogi-beef']),
    ('Brunch at Home',               'brunch-at-home',              'Year-round', '',     'Weekend brunch staples: eggs benedict, quiche, pancakes, smoked salmon.',
     ['classic-eggs-benedict-hollandaise', 'spinach-goat-cheese-quiche', 'lemon-ricotta-pancakes', 'smoked-salmon-bagel-board', 'eggnog-french-toast-casserole', 'christmas-morning-sticky-buns', 'croque-madame-brunch']),
    ('Vegetarian All-Stars',         'vegetarian-all-stars',        'Year-round', '',     'Hearty, meat-free dishes that even confirmed carnivores ask for.',
     ['eggplant-parmesan', 'easy-vegetarian-spinach-lasagna', 'three-bean-vegetarian-chili', 'aloo-gobi-spiced', 'dal-tadka-classic', 'tahini-roasted-eggplant', 'risotto-funghi-porcini', 'falafel-plate-mediterranean']),
    ('Date Night In',                'date-night-in',               'Year-round', '',     'Restaurant-worthy meals to make for two.',
     ['filet-mignon-red-wine-reduction', 'champagne-risotto-shrimp', 'chocolate-lava-cakes-two', 'cacio-e-pepe-classic', 'osso-buco-milanese', 'miso-glazed-salmon']),
    ('Game Day Spread',              'game-day-spread',             'Winter', 'Winter', 'Wings, dips, sliders and chili — the full big-game lineup.',
     ['buffalo-chicken-wings-classic', 'seven-layer-mexican-dip', 'slow-cooker-game-day-chili', 'bbq-pulled-pork-sliders', 'loaded-nachos-supreme', 'cranberry-brie-bites']),
]


def _seed_collections(existing_collection_slugs):
    added = 0
    for i, (title, slug, season_label, season_field, desc, recipe_slugs) in enumerate(COLLECTION_DEFS):
        if slug in existing_collection_slugs:
            continue
        existing_collection_slugs.add(slug)
        img_n = ((i * 23 + 41) % IMAGE_POOL_SIZE) + 1
        # filter to slugs that we expect to exist (best-effort, but keep them all
        # since the page renders missing-recipe slots gracefully).
        col = Collection(
            title=title, slug=slug,
            subtitle=f"Curated {season_label.lower() if season_label != 'Year-round' else 'year-round'} pick — {len(recipe_slugs)} recipes",
            description=desc,
            hero_image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            curator_name='Allrecipes Editors',
            recipe_slugs_json=json.dumps(recipe_slugs),
            tags_json=json.dumps([_slugify(season_label), 'curated', 'editors-pick',
                                  *[t for t in title.lower().split() if len(t) > 3][:4]]),
            season=season_label if season_label != 'Year-round' else '',
            display_order=i,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=(i * 7) % 180),
        )
        db.session.add(col)
        added += 1
    return added


# ===========================================================================
# Phase 5 — Cooking-tips Articles (long-form)
# ===========================================================================

ARTICLE_DEFS = [
    ('How to Roast a Turkey Like a Pro',         'how-to-roast-a-turkey',          'cooking-tips',  'Thanksgiving is here. Here is every trick — brining, butter-basting, resting — for the juiciest turkey of your life.',
     [
         ('Pick the Right Turkey',
          ['Heritage turkeys have richer flavor, but a standard supermarket turkey of 12–14 pounds is enough to feed eight with leftovers.',
           'Plan on 1 to 1.25 pounds per person if you want next-day sandwiches.']),
         ('Brine, Wet or Dry?',
          ['A 24-hour dry brine of 1 tbsp kosher salt per 5 pounds, plus chopped herbs, gives the crispiest skin and well-seasoned meat.',
           'Wet brines work too but make the skin less crackly. Pat the bird thoroughly dry before roasting either way.']),
         ('Roast Low Then High',
          ['Start at 325°F until the breast hits 150°F, then crank to 425°F for the last 15 minutes to crisp the skin.',
           'Tent the breast with foil if it browns too fast — the dark meat needs to hit 175°F before serving.']),
         ('Rest the Bird',
          ['Tent loosely with foil for at least 30 minutes before carving. Juice loss drops by half.']),
     ],
     ['classic-roast-turkey-herb-butter', 'classic-bread-stuffing-sage', 'roast-turkey-gravy-pan-drippings'],
     ['thanksgiving', 'turkey', 'holiday', 'roasting', 'technique'], 8),

    ('5 Knife Skills Every Home Cook Should Know', 'five-knife-skills',           'technique',      'A sharp knife and a few foundational cuts cover 90% of weeknight prep.',
     [
         ('Hold the Knife Right',
          ['The "pinch grip" — thumb and forefinger choking up on the blade — gives you the most control.',
           'Your guide hand should curl into a claw, knuckles tucked under, knife sliding along your knuckles.']),
         ('Master the Dice',
          ['A 1/4-inch dice on an onion: peel, halve, lay flat, make horizontal cuts, then vertical cuts, then crosswise.',
           'Keep the root end intact so the layers stay glued together while you cut.']),
         ('Chiffonade Like a Pro',
          ['Stack basil or mint leaves, roll them into a tight cigar, slice thinly. Ribbons every time.']),
         ('Honing vs. Sharpening',
          ['Honing realigns the edge — do it every couple of uses. Sharpening removes metal — once a year is plenty for a home cook.']),
     ],
     ['eggplant-parmesan', 'cacio-e-pepe-classic', 'aloo-gobi-spiced'],
     ['knife-skills', 'prep', 'technique', 'beginner'], 6),

    ('The Science of Browning: Maillard 101',     'science-of-browning',           'technique',      'Why a dry surface and a hot pan make all the difference between gray and golden.',
     [
         ('Water is the Enemy',
          ['Browning only starts above 285°F, but water boils at 212°F. Until every drop on the surface evaporates, you are steaming, not browning.',
           'Pat proteins bone-dry with paper towels before they hit the pan.']),
         ('Hot Pan First, Oil Second',
          ['Heat the pan first, then add oil — that way the oil gets ripping-hot without burning, and the protein sears the instant it lands.',
           'A wisp of smoke off the oil is the cue to add the food.']),
         ('Don\'t Crowd the Pan',
          ['Each piece of food pushes moisture into the air. Too many pieces in one pan and the air saturates — steam, again.',
           'Sear in two batches if you have to.']),
     ],
     ['buttermilk-fried-chicken', 'osso-buco-milanese', 'beef-bourguignon-sunday'],
     ['maillard', 'browning', 'science', 'technique'], 5),

    ('Pantry Staples: 25 Essentials',             'pantry-staples-25-essentials',   'kitchen-101',    'A solid pantry turns "what do I cook?" into "what looks good tonight?".',
     [
         ('The Oils',
          ['Extra-virgin olive oil for finishing. Neutral oil (canola or grapeseed) for high-heat cooking. Toasted sesame oil for stir-fries.']),
         ('The Salts',
          ['Diamond Crystal kosher salt for almost everything. Flaky sea salt for finishing. Fine sea salt for baking.']),
         ('Acids',
          ['Sherry vinegar, rice vinegar, fresh lemons. Brightness is what separates a flat dish from a great one.']),
         ('Grains and Legumes',
          ['Stone-ground polenta, farro, lentils, chickpeas (dried and canned), good rice (basmati and arborio).']),
     ],
     ['cacio-e-pepe-classic', 'falafel-plate-mediterranean', 'dal-tadka-classic'],
     ['pantry', 'shopping', 'kitchen-101', 'beginner'], 7),

    ('How to Build a Better Salad',               'how-to-build-a-better-salad',    'technique',      'Five components, four mistakes to avoid, three crowd-favorite dressings.',
     [
         ('Five Components',
          ['Greens. Crunch. Protein. Fat. Acid. Build every salad around all five and it will feel like a meal instead of a side.']),
         ('Dressing the Right Way',
          ['Dress greens at the last second in a wide bowl. Use your hands to massage every leaf so it gets a thin, even coat.',
           'Salt the leaves before adding dressing so they don\'t taste flat.']),
         ('Three Dressings to Memorize',
          ['Lemon vinaigrette: 3 tbsp olive oil + 1 tbsp lemon juice + salt.',
           'Tahini-yogurt: 1/4 cup tahini + 1/4 cup yogurt + 1 lemon + water to thin.',
           'Caesar: anchovy + garlic + lemon + Parmesan + olive oil + Dijon.']),
     ],
     ['avocado-tomato-salad', 'watermelon-feta-salad-mint', 'bibimbap-bowl-veggie'],
     ['salads', 'dressings', 'technique'], 5),

    ('Eggs: 10 Ways to Cook Them Right',          'eggs-ten-ways',                  'technique',      'From silky scrambles to perfect poached, the eggs cheat sheet.',
     [
         ('Soft Scramble',
          ['Whisk eggs with a splash of cream. Cook in butter over LOW heat with constant stirring. Pull off the heat while still slightly wet.']),
         ('Hard-Boiled',
          ['Add to actively boiling water, cook 10 minutes, plunge into ice water. Peels every time.']),
         ('Poached',
          ['1 tbsp vinegar in simmering water. Swirl. Crack the egg into the eye of the whirlpool. 3 minutes.']),
     ],
     ['classic-deviled-eggs', 'classic-eggs-benedict-hollandaise', 'spinach-goat-cheese-quiche'],
     ['eggs', 'technique', 'breakfast'], 5),

    ('Bread Baking for Beginners',                'bread-baking-beginners',         'baking',         'A loaf of bread is just flour, water, salt, and time. Here is how to get started.',
     [
         ('Buy the Right Flour',
          ['Bread flour (12–14% protein) is the easiest to work with. King Arthur is a reliable supermarket pick.']),
         ('Develop Gluten',
          ['Mix, then rest 30 minutes (autolyse). Then knead — or do four stretch-and-folds every 30 minutes over 2 hours.']),
         ('Bulk Ferment Slowly',
          ['Refrigerate the dough overnight. Cold-fermented bread tastes vastly more complex than 4-hour bread.']),
     ],
     ['naan-garlic-butter', 'hot-cross-buns-traditional', 'christmas-morning-sticky-buns'],
     ['baking', 'bread', 'beginner'], 8),

    ('Pasta Water is Liquid Gold',                'pasta-water-liquid-gold',        'technique',      'The secret to silkier sauces is the starchy water you usually throw away.',
     [
         ('Salt the Water',
          ['One tablespoon of kosher salt per quart. Your pasta water should taste like the sea.']),
         ('Reserve Before Draining',
          ['Always set aside a cup of cooking water before you drain. You\'ll use 1/4 to 1/2 cup of it to finish the sauce.']),
         ('Why It Works',
          ['Starch in the water emulsifies oil and butter into a glossy sauce that clings to the noodles instead of pooling at the bottom of the bowl.']),
     ],
     ['cacio-e-pepe-classic', 'risotto-funghi-porcini', 'classic-italian-pasta-sauce'],
     ['pasta', 'technique', 'sauces'], 4),

    ('Sheet-Pan Dinners: A Method',               'sheet-pan-method',               'method',         'One pan, three components, 30 minutes. Here is how to design your own.',
     [
         ('Pick One Protein',
          ['Bone-in chicken thighs, salmon fillets, pork sausages, or cubed tofu — each handles roasting differently.']),
         ('Two Vegetables',
          ['One sturdy (potato, carrot, broccoli) and one tender (cherry tomatoes, asparagus, zucchini). Add the tender vegetable halfway.']),
         ('A Big Hit of Flavor',
          ['Garlic-herb butter, peanut-lime sauce, harissa-yogurt — pick a sauce that ties the proteins and vegetables together.']),
     ],
     ['classic-grilled-cheeseburgers'],
     ['sheet-pan', 'method', 'weeknight'], 4),

    ('How to Stock a Spice Cabinet',              'how-to-stock-a-spice-cabinet',   'kitchen-101',    'Twenty spices and blends that cover most of the world\'s cooking.',
     [
         ('Whole Over Ground',
          ['Buy whole cumin, coriander, peppercorns, fennel. Toast and grind as you need them — the difference is night and day.']),
         ('Replace Annually',
          ['Ground spices lose half their punch in 6 months. Date your jars and rotate.']),
         ('Must-Haves',
          ['Kosher salt, black pepper, cumin, coriander, smoked paprika, garlic powder, oregano, thyme, bay leaf, Aleppo or red pepper flakes, cinnamon, turmeric, cardamom.']),
     ],
     ['butter-chicken-punjabi', 'dal-tadka-classic', 'mole-poblano-festivo'],
     ['spices', 'pantry', 'kitchen-101'], 5),

    ('Cookies: The Complete Texture Guide',       'cookies-complete-texture-guide', 'baking',         'Want chewy? Crispy? Cakey? It comes down to a few key ratios.',
     [
         ('Chewy',
          ['More brown sugar than white. Bread flour over all-purpose. Underbake by 1 minute.']),
         ('Crispy',
          ['More white sugar than brown. Beat butter and sugar 4 minutes. Bake fully.']),
         ('Cakey',
          ['Add an extra egg yolk. Use cake flour. Don\'t overbeat.']),
     ],
     ['classic-gingerbread-cookies'],
     ['baking', 'cookies', 'technique'], 6),

    ('Rice Done Right: 5 Foolproof Methods',      'rice-done-right',                'technique',      'Long-grain, short-grain, basmati, jasmine — one chart, every kind of rice.',
     [
         ('Long-Grain White',
          ['1 cup rice : 1.5 cups water. Bring to boil, cover, reduce to lowest heat, 18 minutes. Rest 10 minutes off heat.']),
         ('Brown Rice',
          ['1 cup rice : 2 cups water. Same method but 40 minutes. Fluff and rest covered 10 minutes.']),
         ('Sushi Rice',
          ['Rinse until water runs clear. 1:1 ratio. Soak 20 minutes before cooking.']),
     ],
     ['onigiri-salmon-rice-balls', 'chicken-katsu-curry', 'bibimbap-bowl-veggie'],
     ['rice', 'technique', 'kitchen-101'], 4),

    ('A Better Vinaigrette in 90 Seconds',        'better-vinaigrette',             'technique',      'The 3:1 ratio, when to add mustard, and why a shallot makes everything sing.',
     [
         ('The Ratio',
          ['Three parts oil, one part acid. Adjust to taste — bright dressings for hearty greens, mellower ones for delicate leaves.']),
         ('The Emulsifier',
          ['A small spoon of Dijon, or 1 minced shallot rested in vinegar for 5 minutes, holds the dressing together.']),
         ('Build the Layers',
          ['Salt + acid + emulsifier + oil. Whisk until thick. Taste a leaf, adjust salt, then dress the salad.']),
     ],
     ['avocado-tomato-salad', 'watermelon-feta-salad-mint'],
     ['dressings', 'salads', 'technique'], 3),

    ('How to Build a Roast Vegetable Tray',       'how-to-build-a-roast-veg-tray',  'technique',      'Roasted vegetables are vastly better than steamed. Here is how to do them well.',
     [
         ('High Heat',
          ['Roast at 425°F. Below that and the vegetables steam in their own moisture; above that and they burn before they soften.']),
         ('Single Layer',
          ['Crowded pans = soggy vegetables. Use two pans before you cram one.']),
         ('Salt Twice',
          ['Salt before roasting, then a finishing flake when they come out of the oven.']),
     ],
     ['collard-greens-slow-cooked', 'aloo-gobi-spiced', 'tahini-roasted-eggplant'],
     ['vegetables', 'roasting', 'technique'], 4),

    ('How to Make Stock from Scratch',            'how-to-make-stock',              'technique',      'Bones, scraps, time. Stock is the multiplier that lifts every soup and braise.',
     [
         ('Chicken Stock',
          ['One whole carcass, two carrots, two stalks celery, one onion, a head of garlic. Cover with cold water. Simmer 4 hours. Strain.']),
         ('Beef Stock',
          ['Roast bones 45 minutes at 425°F first. Then simmer 8–10 hours with mirepoix, tomato paste, and a splash of red wine.']),
         ('Vegetable Stock',
          ['Save vegetable scraps in the freezer. When the bag is full, simmer with water for 90 minutes.']),
     ],
     ['borscht-ukrainian', 'pozole-rojo-family', 'ramen-tonkotsu-bowl'],
     ['stock', 'soups', 'technique'], 5),

    ('Better Burgers: 7 Rules',                   'better-burgers-seven-rules',     'technique',      'How to make a steakhouse-quality smash burger or thick patty at home.',
     [
         ('The Meat',
          ['80/20 ground chuck. Anything leaner and you get hockey pucks; anything fattier and the patty falls apart.']),
         ('Salt After Forming',
          ['Salt only the outside of the patty. Salt mixed into the meat draws moisture out and tightens the texture.']),
         ('Smash and Press',
          ['Hot cast iron, ball of meat, smash flat with a spatula in the first 30 seconds. Don\'t touch it again for 2 minutes.']),
     ],
     ['classic-grilled-cheeseburgers'],
     ['burgers', 'grilling', 'technique'], 4),

    ('What to Do with Leftover Chicken',          'leftover-chicken-ideas',         'cooking-tips',   'Twelve ways to turn a sad piece of leftover chicken into a real meal.',
     [
         ('Chicken Salad',
          ['Shredded chicken + mayo + Dijon + celery + grapes + tarragon. Lunch sorted.']),
         ('Quick Soup',
          ['Sweat aromatics, add stock, drop in leftover chicken + a handful of pasta. Done in 15 minutes.']),
         ('Tacos',
          ['Crisp shredded chicken in a hot skillet with cumin and lime. Pile onto tortillas with avocado and salsa.']),
     ],
     ['banh-mi-pulled-pork', 'chicken-breast-quinoa-bowl'],
     ['leftovers', 'chicken', 'quick'], 4),

    ('Beans: From Dried to Dinner',               'beans-dried-to-dinner',          'technique',      'Why dried beans are vastly better than canned — and how to cook them.',
     [
         ('Soak (or Don\'t)',
          ['Soaking overnight cuts cook time by half. But unsoaked beans cooked from cold water taste better and hold their shape.']),
         ('Salt Early',
          ['Old wisdom said never salt until cooked; new wisdom says salt the soaking water. Either way, salt before serving.']),
         ('The Pot Liquor',
          ['Don\'t drain. The cooking liquid is what makes pinto beans, white beans, or chickpeas taste deep instead of beige.']),
     ],
     ['three-bean-vegetarian-chili', 'dal-tadka-classic', 'falafel-plate-mediterranean'],
     ['beans', 'pantry', 'technique'], 6),

    ('Sauces You Can Make in 5 Minutes',          'five-minute-sauces',             'cooking-tips',   'Six pantry-based sauces that turn anything roasted into dinner.',
     [
         ('Chimichurri',
          ['Parsley + garlic + red wine vinegar + olive oil + red pepper flakes + salt. Spoon over grilled anything.']),
         ('Salsa Verde',
          ['Capers + anchovy + mint + parsley + lemon + olive oil. Italian, not Mexican — and built for fish or steak.']),
         ('Yogurt-Tahini',
          ['Plain Greek yogurt + tahini + lemon + garlic + water to thin. The dip that goes on everything.']),
     ],
     ['lamb-kofta-skewers', 'falafel-plate-mediterranean', 'sheet-pan-method'],
     ['sauces', 'pantry', 'quick'], 4),

    ('Holiday Hosting Survival Guide',            'holiday-hosting-survival',       'entertaining',   'A game-day plan for cooking dinner for ten without losing your mind.',
     [
         ('Two Days Out',
          ['Make the sides. Pies, cranberry sauce, mashed potatoes (reheat in butter), even the gravy base. The day-of stress comes from doing it all on the day.']),
         ('Morning Of',
          ['Set the table. Pour wine. Put soft music on. Your guests show up to a calm host, not a frantic one.']),
         ('30 Minutes Before',
          ['Pull the turkey or roast to rest. Reheat sides in covered dishes. Pour everyone a drink.']),
     ],
     ['classic-roast-turkey-herb-butter', 'holiday-prime-rib-roast', 'easter-honey-glazed-ham', 'glazed-spiral-cut-ham'],
     ['hosting', 'holidays', 'planning'], 6),

    ('Cast Iron 101',                              'cast-iron-101',                  'kitchen-101',    'Why a $20 pan can outlast your career — and how to care for one.',
     [
         ('Buy Pre-Seasoned',
          ['Lodge\'s 12-inch is the entry-level pan that hundreds of restaurants use too. Pre-seasoned, ready to go.']),
         ('Don\'t Be Afraid of Soap',
          ['A drop of dish soap will not strip your seasoning. Scrub, dry on the burner, rub with a tiny film of oil.']),
         ('Restore Stickers',
          ['If a friend tossed it in the dishwasher: scrub off the rust, season three times in the oven at 450°F with vegetable oil.']),
     ],
     ['classic-grilled-cheeseburgers', 'cottage-pie-sunday'],
     ['cast-iron', 'tools', 'kitchen-101'], 5),

    ('What Pan to Buy First',                     'what-pan-to-buy-first',          'kitchen-101',    'A 12-inch stainless skillet beats a 12-piece set every time.',
     [
         ('Stainless Skillet',
          ['12 inches. Heavy bottom. Tri-ply if you can stretch — All-Clad D3 or the Made In option are the go-tos.']),
         ('Cast Iron Skillet',
          ['10 to 12 inches. Lodge. $25. Lifetime tool.']),
         ('Dutch Oven',
          ['6-quart. Le Creuset or Staub if budget allows; Lodge enameled if not. Stews, braises, bread baking.']),
     ],
     ['osso-buco-milanese', 'beef-bourguignon-sunday'],
     ['tools', 'kitchen-101', 'beginner'], 5),

    ('Five Quick Marinades',                      'five-quick-marinades',           'cooking-tips',   'Memorize these and you have a year of weeknight dinners.',
     [
         ('Lemon-Herb',
          ['Lemon + olive oil + garlic + oregano + salt. 30 minutes for chicken, fish, or vegetables.']),
         ('Ginger-Soy',
          ['Soy + rice vinegar + ginger + garlic + sesame oil. Tofu, salmon, chicken thighs.']),
         ('Mole Adobo',
          ['Adobo + lime + cumin + brown sugar + olive oil. Tacos, fajitas, sheet-pan dinners.']),
     ],
     ['korean-bulgogi-beef', 'miso-glazed-salmon', 'tacos-carnitas-slow'],
     ['marinades', 'cooking-tips', 'weeknight'], 3),

    ('How to Throw a Brunch Party',               'how-to-throw-a-brunch-party',    'entertaining',   'Six dishes, three drinks, one stress-free morning.',
     [
         ('Make-Ahead Mains',
          ['Spinach quiche, French toast casserole, frittata, cinnamon rolls — all assemble the night before, bake fresh.']),
         ('Three Drinks',
          ['Mimosas, Bloody Marys, a non-alc sparkling lemonade. Nobody wants seventeen options.']),
         ('Plate Family-Style',
          ['Big platters in the middle of the table. No assigned portions. Less work, more fun.']),
     ],
     ['classic-eggs-benedict-hollandaise', 'spinach-goat-cheese-quiche', 'lemon-ricotta-pancakes', 'smoked-salmon-bagel-board'],
     ['brunch', 'hosting', 'entertaining'], 5),

    ('Cooking for One: A Strategy',               'cooking-for-one-strategy',       'cooking-tips',   'Cook twice, eat four times — the lazy single cook\'s playbook.',
     [
         ('Big Pot, Reheat Smart',
          ['Make a 4-serving batch on Sunday. Eat it Sunday, Tuesday, Thursday, Saturday. Stretch with new vegetables each time.']),
         ('Freeze Half',
          ['Portion stews and soups into freezer-safe single-serve containers. Future-you will be grateful.']),
         ('Half-Recipes Don\'t Always Work',
          ['Baking, especially, doesn\'t scale down well. Bake full batches and freeze portions in slices.']),
     ],
     ['three-bean-vegetarian-chili', 'pozole-rojo-family', 'slow-cooker-game-day-chili'],
     ['cooking-for-one', 'planning', 'budget'], 5),
]


def _seed_articles(existing_article_slugs):
    added = 0
    for i, (title, slug, category, excerpt, sections, related_slugs, tags, read_min) in enumerate(ARTICLE_DEFS):
        if slug in existing_article_slugs:
            continue
        existing_article_slugs.add(slug)
        body = []
        for j, (heading, paras) in enumerate(sections):
            body.append({
                'heading': heading,
                'paragraphs': paras,
                'callout': (paras[0][:120] if j == len(sections) - 1 else None),
            })
        img_n = ((i * 17 + 9) % IMAGE_POOL_SIZE) + 1
        author_pool = ['Allrecipes Editors', 'Chef Marie Laurent', 'Chef Marcus Bell',
                       'Chef Sofia Romano', 'Chef Priya Sharma', 'Chef Yuki Tanaka']
        art = Article(
            title=title, slug=slug, category=category,
            author_name=author_pool[i % len(author_pool)],
            excerpt=excerpt,
            body_json=json.dumps(body),
            hero_image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            read_time_mins=read_min,
            related_recipes_json=json.dumps(related_slugs),
            tags_json=json.dumps(tags),
            published_at=MIRROR_REFERENCE_DATE - timedelta(days=(i * 5 + 13) % 360),
            view_count=1200 + i * 137,
        )
        db.session.add(art)
        added += 1
    return added


# ===========================================================================
# Public entry point — called from seed_data.seed_extended_catalog
# ===========================================================================

def run_r4_polish(cat_by_slug):
    """Top-level R4 entry point. Returns a dict of counts."""
    # Sentinel: if at least one R4 collection exists, the whole pass already
    # ran — bail out so re-runs are no-ops.
    if Collection.query.filter_by(slug='best-summer-grilling').first():
        return {'skipped': True}

    counts = {}

    # 1) Chef recipes — first so reviewers/reviews pass picks them up too.
    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['chef_recipes'] = _seed_chef_recipes(cat_by_slug, existing_recipe_slugs)
    db.session.flush()

    # 2) Variant passes — operate on every existing recipe.
    base_for_r4 = (Recipe.query
                   .filter(Recipe.author_name.like('%Test Kitchen%'))
                   .order_by(Recipe.id)
                   .all())
    counts['seasonal'] = _seed_seasonal_variants(cat_by_slug, base_for_r4, existing_recipe_slugs)
    db.session.flush()
    counts['one_pot'] = _seed_one_pot_variants(cat_by_slug, base_for_r4, existing_recipe_slugs)
    db.session.flush()
    counts['sheet_pan'] = _seed_sheet_pan_variants(cat_by_slug, base_for_r4, existing_recipe_slugs)
    db.session.flush()
    counts['healthy_swap'] = _seed_healthy_swap_variants(cat_by_slug, base_for_r4, existing_recipe_slugs)
    db.session.flush()

    # 3) Enrich EVERY recipe — tags >=5, full nutrition, 3-step gallery.
    _enrich_existing_recipes()
    db.session.flush()

    # 4) Collections + Articles.
    existing_col_slugs = {c.slug for c in Collection.query.all()}
    counts['collections'] = _seed_collections(existing_col_slugs)
    db.session.flush()

    existing_art_slugs = {a.slug for a in Article.query.all()}
    counts['articles'] = _seed_articles(existing_art_slugs)
    db.session.flush()

    return counts
