"""R9 polish seed — four ethnic-cuisine regional variant passes
(Indian-Regional / MiddleEastern-Regional / Caribbean-Regional /
African-Regional) plus four chef collections broadening the global
cuisine surface.

Runs AFTER R8 inside ``seed_data.seed_extended_catalog``. Everything in
here is deterministic so a rebuild from source is byte-identical to the
shipped ``instance_seed/allrecipes.db``.

R9 deliverables (recipes 23521 -> 28000+):
  * 4 new top-level cuisine categories: indian / middle-eastern /
    caribbean / african
  * 4 new variant passes — Indian, MiddleEastern, Caribbean, African
    each operating on the same Test Kitchen base subsample (step 7,
    ~1180 recipes per pass, ~4720 new total). They re-cast the base
    with regional spice blends, fats and techniques.
  * Four chef collections — Vikram Singh (regional Indian),
    Ayesha Khoury (Lebanese / Persian / Turkish),
    Marcus Boateng (West-African / Ethiopian / Moroccan / South-African),
    Lourdes Castillo (Jamaican / Cuban / Trinidadian).
    ~60 new chef-led recipes total.

Idempotent — gated on the presence of a sentinel R9 recipe slug.
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


# Variant authors we never re-iterate over (R6/R7/R8/R9).
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
                                    + R8_AUTHOR_TOKENS + R9_AUTHOR_TOKENS))


def _cat_slug_for(base, cat_by_slug):
    if not base.category_id:
        return None
    for slug, c in cat_by_slug.items():
        if c.id == base.category_id:
            return slug
    return None


# ===========================================================================
# Ethnic-cuisine top-level categories
# ===========================================================================

R9_CATEGORIES = [
    ('Indian',          'indian',          'Regional Indian cooking — Punjabi tandoor, South-Indian rice and lentil staples, Bengali fish, Gujarati vegetarian.',    'cuisine', 110),
    ('Middle Eastern',  'middle-eastern',  'Lebanese mezze, Persian rice and stews, Turkish kebabs and breads — all under one regional banner.',                       'cuisine', 111),
    ('Caribbean',       'caribbean',       'Jamaican jerk, Cuban beans-and-rice, Trinidadian curries and roti — island cuisines with bright, spiced flavors.',          'cuisine', 112),
    ('African',         'african',         'Moroccan tagines, Ethiopian injera and stews, West-African jollof and South-African braai — a wide-ranging continent.',     'cuisine', 113),
]


def _seed_r9_categories(cat_by_slug):
    added = 0
    for name, slug, desc, ptype, order in R9_CATEGORIES:
        if slug in cat_by_slug:
            continue
        c = Category(name=name, slug=slug, description=desc,
                     parent_type=ptype, display_order=order)
        db.session.add(c)
        cat_by_slug[slug] = c
        added += 1
    return added


# ===========================================================================
# Pass 1 — Indian-Regional variant
# ===========================================================================

INDIAN_INSTRUCTIONS = [
    "Bloom whole spices (cumin, mustard seeds, curry leaves) in hot ghee for 30 seconds — the oil should be the flavor carrier, not the spices themselves.",
    "Soften the onion-ginger-garlic base for a full 8 minutes until visibly golden — this is the bhuna stage where bitterness cooks out.",
    "Add ground spices (turmeric, coriander, garam masala, chili) off heat for 10 seconds, then return to medium to avoid scorching the powders.",
    "Simmer the main protein or vegetable on low heat with a tight lid for 25 minutes; finish with a swirl of cream or yogurt off heat.",
    "Garnish with a fresh tadka of ghee, asafoetida and dried red chili poured over the dish at the table.",
]


def _seed_indian_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('indian')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"indian-regional-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"Indian-Regional {base.title}"
        new_prep = 20 + (ri % 12)
        new_cook = 30 + (ri % 14)
        new_total = new_prep + new_cook
        region = ('Punjabi', 'South-Indian', 'Bengali', 'Gujarati', 'Hyderabadi')[ri % 5]
        new_ings = [
            '2 tbsp ghee',
            '1 tsp cumin seeds',
            '1 tsp mustard seeds (South-Indian/Gujarati passes)',
            '10 fresh curry leaves',
            '1 large yellow onion, finely diced',
            '1 tbsp ginger-garlic paste',
            '2 small green chilies, slit',
            '1 tsp ground turmeric',
            '2 tsp ground coriander',
            '1 tsp garam masala',
            '1 tsp Kashmiri chili powder',
            f"500 g {base.main_ingredient or 'chicken thigh'}, cut into 1-inch pieces",
            '1 cup full-fat yogurt (whisked)',
            '1/2 cup heavy cream',
            '2 tbsp tomato paste',
            '1 tsp fine sea salt',
            'Fresh cilantro and lime wedges to finish',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'indian', 'indian-regional', region.lower(), 'spice-bloomed',
            'curry', 'subcontinental',
            cat_slug or 'cuisines',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary))  # Indian-Regional preserves base dietary tags
        img_n = ((ri * 251 + 7) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{region} walkthrough",
            'desc': f"Spice bloom + bhuna + simmer photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 257 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 263 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 269 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 43 + 5) % 720)
        cal = 380 + (ri * 17) % 220
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {region} Indian reinterpretation of {base.title}. Whole spices "
                "bloomed in ghee, onion-ginger-garlic bhuna base, finished with yogurt "
                "and a fresh tadka. Serve over basmati rice or with warm roti."),
            category_id=(cat.id if cat else base.category_id),
            cuisine='Indian',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(INDIAN_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '24g', 'Fat': '20g', 'Carbs': '28g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 73 == 0),
            is_editors_pick=(ri % 97 == 0),
            avg_rating=round(min(5.0, 4.55 + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Indian-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='main', meal_type='dinner',
            cooking_method='simmered',
            main_ingredient=base.main_ingredient or 'chicken',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 4 days refrigerated; flavors deepen overnight. Freeze portions up to 3 months.',
            primary_seasoning='garam-masala',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 2 — MiddleEastern-Regional variant
# ===========================================================================

MIDEAST_INSTRUCTIONS = [
    "Toast whole coriander, cumin and allspice in a dry pan for 90 seconds until aromatic; grind with a mortar and pestle.",
    "Render olive oil over very low heat with crushed garlic and a strip of lemon peel for 5 minutes — this is the flavor base, never brown the garlic.",
    "Marinate the protein or vegetable in lemon juice + olive oil + the toasted spice blend + Greek yogurt for at least 1 hour.",
    "Sear the marinated mixture in a screaming hot pan or under a high broiler for 6 minutes per side to develop the Maillard crust.",
    "Finish with a drizzle of tahini-lemon sauce, pomegranate molasses, and fresh herbs (parsley, mint, dill) — all three for layered freshness.",
]


def _seed_mideast_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('middle-eastern')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"middleeastern-regional-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"MiddleEastern-Regional {base.title}"
        new_prep = 25 + (ri % 12)
        new_cook = 25 + (ri % 14)
        new_total = new_prep + new_cook + 60  # 1 hr marinate
        region = ('Lebanese', 'Persian', 'Turkish', 'Syrian', 'Israeli')[ri % 5]
        new_ings = [
            '3 tbsp extra-virgin olive oil',
            '4 cloves garlic, crushed',
            '1 strip lemon peel',
            '1 tsp toasted coriander seeds, ground',
            '1 tsp toasted cumin seeds, ground',
            '1/2 tsp ground allspice',
            '1/2 tsp Aleppo pepper',
            '1 tsp sumac',
            f"600 g {base.main_ingredient or 'chicken thigh'}, cut into chunks",
            '1/2 cup Greek yogurt',
            '2 tbsp lemon juice',
            '1 tsp fine sea salt',
            '3 tbsp tahini',
            '1 tbsp pomegranate molasses',
            'Fresh parsley, mint and dill to finish',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'middle-eastern', 'middle-eastern-regional', region.lower(),
            'tahini-finished', 'sumac-dusted', 'mezze',
            cat_slug or 'cuisines',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary))
        img_n = ((ri * 271 + 11) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{region} mezze walkthrough",
            'desc': f"Toast + marinate + sear photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 277 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 281 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 283 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 47 + 11) % 720)
        cal = 340 + (ri * 13) % 200
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {region} reinterpretation of {base.title}. Toasted whole-spice "
                "blend, garlic-and-olive-oil base, yogurt-marinated and broiled. "
                "Finished with tahini-lemon, pomegranate molasses and three fresh herbs."),
            category_id=(cat.id if cat else base.category_id),
            cuisine='Middle Eastern',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(MIDEAST_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '26g', 'Fat': '22g', 'Carbs': '14g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 79 == 0),
            is_editors_pick=(ri % 101 == 0),
            avg_rating=round(min(5.0, 4.55 + ((ri % 13 - 6) * 0.02)), 1),
            review_count=0,
            author_name='MiddleEastern-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='main', meal_type='dinner',
            cooking_method='broiled',
            main_ingredient=base.main_ingredient or 'chicken',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 3 days refrigerated; the spice blend keeps in a jar for 3 months.',
            primary_seasoning='sumac',
            max_oven_temp=500,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 3 — Caribbean-Regional variant
# ===========================================================================

CARIBBEAN_INSTRUCTIONS = [
    "Pound the wet seasoning paste — green onion, thyme, garlic, scotch bonnet, allspice — in a mortar until aromatic and slightly soupy.",
    "Marinate the protein or vegetable in the wet paste + lime juice + soy sauce for at least 2 hours; overnight gives proper jerk depth.",
    "Sear over very high heat (or grill over pimento wood if available) for 4 minutes per side to char the marinade — the smoke is half the dish.",
    "Lower the heat, add coconut milk + scotch bonnet halves, and braise covered for 25 minutes; remove the chili before serving.",
    "Serve over rice-and-peas (kidney beans simmered with coconut milk and thyme) with a side of fried plantain.",
]


def _seed_caribbean_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('caribbean')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"caribbean-regional-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"Caribbean-Regional {base.title}"
        new_prep = 25 + (ri % 12)
        new_cook = 35 + (ri % 12)
        new_total = new_prep + new_cook + 120  # 2 hr marinate
        region = ('Jamaican', 'Cuban', 'Trinidadian', 'Bajan', 'Haitian')[ri % 5]
        new_ings = [
            '6 green onions, white and green parts',
            '2 tbsp fresh thyme leaves',
            '6 cloves garlic',
            '1 scotch bonnet pepper (seeded if heat-sensitive)',
            '1 tbsp ground allspice (pimento)',
            '1 tbsp dark soy sauce',
            '2 tbsp lime juice',
            '2 tbsp light brown sugar',
            '1 tbsp dark rum',
            f"600 g {base.main_ingredient or 'chicken thigh'}",
            '1 can (400 ml) coconut milk',
            '1 cup kidney beans (drained, for rice-and-peas)',
            '2 ripe plantains, sliced',
            '2 cups jasmine rice',
            '1 tsp fine sea salt',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'caribbean', 'caribbean-regional', region.lower(),
            'jerk', 'coconut-braised', 'rice-and-peas',
            cat_slug or 'cuisines',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary))
        img_n = ((ri * 293 + 13) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{region} walkthrough",
            'desc': f"Wet paste + char + coconut braise photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 307 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 311 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 313 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 53 + 17) % 720)
        cal = 460 + (ri * 19) % 220
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {region} reinterpretation of {base.title}. Pounded green-onion / thyme / "
                "scotch-bonnet wet paste, charred over high heat, then coconut-braised. "
                "Served over rice-and-peas with fried plantain."),
            category_id=(cat.id if cat else base.category_id),
            cuisine='Caribbean',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(CARIBBEAN_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '28g', 'Fat': '24g', 'Carbs': '40g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 71 == 0),
            is_editors_pick=(ri % 103 == 0),
            avg_rating=round(min(5.0, 4.5 + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Caribbean-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='main', meal_type='dinner',
            cooking_method='braised',
            main_ingredient=base.main_ingredient or 'chicken',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 4 days refrigerated; the wet paste keeps in a jar for 1 week.',
            primary_seasoning='allspice',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 4 — African-Regional variant
# ===========================================================================

AFRICAN_INSTRUCTIONS = [
    "Bloom whole spices (cumin, coriander, fennel, cardamom) in hot peanut or palm oil for 90 seconds — this is the berbere / ras-el-hanout / suya base.",
    "Sweat finely diced onion, garlic, ginger and Scotch bonnet for 10 minutes until the rawness is gone and the base has visibly thickened.",
    "Stir in tomato paste and the ground-spice blend; cook for 3 more minutes to take the raw edge off the tomato and rehydrate the spices.",
    "Add the protein or root vegetable and stock; simmer covered on low heat for 40 minutes until the meat falls apart or the vegetable is tender.",
    "Finish with a knob of butter or palm oil, lemon juice, and fresh cilantro. Serve over jollof rice, injera or fufu depending on the region.",
]


def _seed_african_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    cat = cat_by_slug.get('african')
    for ri, base in enumerate(base_recipes):
        if _is_prev_variant(base.author_name):
            continue
        new_slug = f"african-regional-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        new_title = f"African-Regional {base.title}"
        new_prep = 25 + (ri % 12)
        new_cook = 45 + (ri % 16)
        new_total = new_prep + new_cook
        region = ('Moroccan', 'Ethiopian', 'WestAfrican', 'SouthAfrican', 'Nigerian')[ri % 5]
        new_ings = [
            '3 tbsp peanut oil (or palm oil for West-African passes)',
            '1 tsp cumin seeds',
            '1 tsp coriander seeds',
            '1/2 tsp fennel seeds',
            '4 green cardamom pods',
            '1 large red onion, finely diced',
            '6 cloves garlic, minced',
            '1 tbsp fresh ginger, grated',
            '1 Scotch bonnet, finely minced',
            '2 tbsp tomato paste',
            '2 tbsp berbere (Ethiopian) / ras-el-hanout (Moroccan) / suya (West-African)',
            f"600 g {base.main_ingredient or 'lamb shoulder'}, cubed",
            '3 cups stock',
            '1 cup chopped tomatoes',
            '2 tbsp lemon juice',
            'Fresh cilantro to finish',
        ]
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_features = list(dict.fromkeys([
            'african', 'african-regional', region.lower(),
            'spice-bloomed', 'tagine', 'stew',
            cat_slug or 'cuisines',
        ]))
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        new_dietary = sorted(set(base_dietary))
        img_n = ((ri * 317 + 17) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f"{region} walkthrough",
            'desc': f"Spice bloom + sweat + simmer photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 331 + 13) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 337 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 347 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 59 + 23) % 720)
        cal = 480 + (ri * 23) % 200
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {region} reinterpretation of {base.title}. Whole-spice bloom in "
                "peanut or palm oil, slow-sweated onion-garlic-ginger base, berbere / "
                "ras-el-hanout / suya spice blend. Long-simmered until tender."),
            category_id=(cat.id if cat else base.category_id),
            cuisine='African',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings='4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(AFRICAN_INSTRUCTIONS)),
            nutrition_json=json.dumps({'Calories': str(cal), 'Protein': '30g', 'Fat': '26g', 'Carbs': '32g'}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 67 == 0),
            is_editors_pick=(ri % 107 == 0),
            avg_rating=round(min(5.0, 4.55 + ((ri % 13 - 6) * 0.02)), 1),
            review_count=0,
            author_name='African-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type='main', meal_type='dinner',
            cooking_method='simmered',
            main_ingredient=base.main_ingredient or 'lamb',
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 4 days refrigerated; tagines deepen overnight. Freeze portions up to 3 months.',
            primary_seasoning='berbere',
            max_oven_temp=0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# R9 chef recipes — Vikram Singh / Ayesha Khoury / Marcus Boateng / Lourdes Castillo
# ===========================================================================

R9_CHEF_RECIPES = [
    ('Chef Vikram Singh', 'Indian-Regional', [
        ('Butter Chicken (Murgh Makhani)', 'butter-chicken-murgh-makhani', 'indian', 'Indian', [],
         ['600 g chicken thigh', '1 cup yogurt', '2 tbsp ginger-garlic paste', '1 cup tomato puree', '1/2 cup heavy cream', '4 tbsp butter', '1 tsp garam masala', '1 tsp Kashmiri chili', '1 tsp dried fenugreek leaves (kasuri methi)', 'salt'], 25, 35),
        ('Hyderabadi Chicken Biryani', 'hyderabadi-chicken-biryani', 'indian', 'Indian', [],
         ['1 kg chicken on the bone', '3 cups basmati rice', '1 cup yogurt', '2 large onions, fried (birista)', '1 tbsp ginger-garlic paste', '1 tsp saffron in 1/4 cup warm milk', '1 tsp garam masala', '6 green cardamom', '4 cloves', '2 bay leaves', '1 cup mint and cilantro'], 45, 60),
        ('Punjabi Chole (Spiced Chickpeas)', 'punjabi-chole', 'indian', 'Indian', ['vegetarian', 'vegan'],
         ['3 cups dried chickpeas (soaked overnight)', '2 onions', '4 tomatoes', '1 tbsp ginger-garlic paste', '2 tsp chole masala', '1 black tea bag (for color)', '2 tbsp ghee', 'salt and cilantro'], 30, 50),
        ('Dosa with Coconut Chutney', 'dosa-coconut-chutney', 'indian', 'Indian', ['vegetarian', 'gluten-free'],
         ['2 cups rice', '1/2 cup urad dal', '1/4 tsp fenugreek seeds', 'salt', 'oil for griddling', '1 cup grated coconut', '2 green chilies', '1 tbsp roasted chana dal', 'curry leaves'], 30, 30),
        ('Goan Fish Curry', 'goan-fish-curry', 'indian', 'Indian', ['gluten-free'],
         ['600 g firm white fish', '6 dried red chilies', '1 tsp coriander seeds', '1 tsp cumin seeds', '1 tbsp tamarind paste', '1 can coconut milk', '1 onion', '4 garlic cloves', '1-inch ginger', 'salt'], 25, 25),
        ('Rajma (Kidney Bean Curry)', 'rajma-kidney-bean-curry', 'indian', 'Indian', ['vegetarian', 'vegan', 'gluten-free'],
         ['2 cups dried red kidney beans (soaked)', '2 onions', '4 tomatoes', '1 tbsp ginger-garlic paste', '1 tsp garam masala', '1 tsp ground coriander', '2 tbsp ghee', 'salt and cilantro'], 25, 60),
        ('Bengali Macher Jhol (Fish Stew)', 'bengali-macher-jhol', 'indian', 'Indian', ['gluten-free'],
         ['600 g rohu or carp', '1 tsp turmeric', '4 tbsp mustard oil', '1 tsp panch phoron', '2 potatoes (cubed)', '2 tomatoes', '2 green chilies', '1 tbsp ginger paste', 'salt and cilantro'], 20, 30),
        ('South Indian Sambar', 'south-indian-sambar', 'indian', 'Indian', ['vegetarian', 'vegan'],
         ['1 cup toor dal', '1 cup mixed vegetables (drumstick, eggplant, carrot)', '2 tbsp tamarind paste', '2 tbsp sambar powder', '1 tsp mustard seeds', '10 curry leaves', '2 dried red chilies', '1 tbsp ghee', 'salt'], 20, 40),
    ]),
    ('Chef Ayesha Khoury', 'MiddleEastern-Regional', [
        ('Lebanese Tabbouleh', 'lebanese-tabbouleh', 'middle-eastern', 'Middle Eastern', ['vegetarian', 'vegan'],
         ['3 cups finely chopped parsley', '1/2 cup chopped mint', '1/4 cup fine bulgur (soaked)', '4 tomatoes (finely diced)', '4 green onions', '1/2 cup olive oil', '1/4 cup lemon juice', 'salt'], 30, 0),
        ('Persian Fesenjan', 'persian-fesenjan', 'middle-eastern', 'Middle Eastern', ['gluten-free'],
         ['600 g chicken thigh', '2 cups walnuts (finely ground)', '1 cup pomegranate molasses', '1 large onion', '1 tsp ground cinnamon', '1 tsp ground cardamom', '2 tbsp butter', 'salt and pepper'], 25, 90),
        ('Turkish Adana Kebab', 'turkish-adana-kebab', 'middle-eastern', 'Middle Eastern', ['gluten-free'],
         ['600 g lamb shoulder (hand-minced)', '100 g lamb fat', '1 tbsp Aleppo pepper', '1 tsp sumac', '1 tsp cumin', '1 small onion (grated, drained)', '4 cloves garlic', 'salt'], 30, 15),
        ('Israeli Shakshuka', 'israeli-shakshuka', 'middle-eastern', 'Middle Eastern', ['vegetarian', 'gluten-free'],
         ['4 tbsp olive oil', '1 onion', '1 red pepper', '4 cloves garlic', '2 tbsp tomato paste', '1 tsp smoked paprika', '1 tsp cumin', '1 can crushed tomatoes', '6 large eggs', '100 g feta', 'parsley'], 10, 25),
        ('Syrian Mujadara', 'syrian-mujadara', 'middle-eastern', 'Middle Eastern', ['vegetarian', 'vegan'],
         ['1 cup green lentils', '1 cup long-grain rice', '3 large onions (sliced thin, slow-fried)', '1/2 cup olive oil', '1 tsp cumin', '1 tsp allspice', 'salt and pepper'], 20, 50),
        ('Lebanese Kibbeh Nayyeh', 'lebanese-kibbeh-nayyeh', 'middle-eastern', 'Middle Eastern', ['gluten-free'],
         ['400 g very lean lamb leg', '1 cup fine bulgur (soaked)', '1 small onion (grated, drained)', '1 tsp baharat', '1 tsp Aleppo pepper', '1 tsp sumac', 'olive oil and mint to serve'], 25, 0),
        ('Turkish Manti', 'turkish-manti', 'middle-eastern', 'Middle Eastern', [],
         ['3 cups flour', '2 eggs', '1 tsp salt (dough)', '300 g ground lamb', '1 onion (grated)', '1 tsp Aleppo pepper', '2 cups yogurt', '4 cloves garlic', '4 tbsp butter', '1 tsp red pepper flakes'], 60, 20),
    ]),
    ('Chef Marcus Boateng', 'African-Regional', [
        ('Moroccan Lamb Tagine with Apricots', 'moroccan-lamb-tagine-apricots', 'african', 'African', ['gluten-free'],
         ['1 kg lamb shoulder', '2 onions', '4 garlic cloves', '1 tbsp ras-el-hanout', '1 tsp ground ginger', '1 cinnamon stick', '1 cup dried apricots', '1/2 cup almonds', '2 tbsp honey', '2 tbsp olive oil', 'salt and saffron'], 25, 120),
        ('Ethiopian Doro Wat', 'ethiopian-doro-wat', 'african', 'African', ['gluten-free'],
         ['1 kg chicken on the bone', '4 large onions (very finely diced)', '4 tbsp berbere', '4 tbsp niter kibbeh (spiced butter)', '1 tbsp ginger-garlic paste', '6 hard-boiled eggs', 'salt and lemon'], 30, 90),
        ('West African Jollof Rice', 'west-african-jollof-rice', 'african', 'African', ['vegetarian', 'vegan'],
         ['3 cups parboiled long-grain rice', '4 red bell peppers', '4 plum tomatoes', '2 Scotch bonnets', '2 onions', '1/4 cup tomato paste', '1/4 cup vegetable oil', '2 tsp curry powder', '2 tsp thyme', '1 tsp ginger', 'salt and stock'], 30, 50),
        ('Nigerian Egusi Soup', 'nigerian-egusi-soup', 'african', 'African', ['gluten-free'],
         ['1 cup ground egusi (melon seeds)', '500 g goat meat (cubed)', '300 g spinach (chopped)', '1/2 cup palm oil', '1 onion', '2 Scotch bonnets', '2 tbsp ground crayfish', 'stock and salt'], 20, 60),
        ('South African Bobotie', 'south-african-bobotie', 'african', 'African', [],
         ['750 g ground beef or lamb', '1 onion', '4 garlic cloves', '2 tbsp curry powder', '1 tbsp turmeric', '1/4 cup chutney', '1/4 cup raisins', '2 slices white bread (soaked in milk)', '3 eggs', '1 cup milk', 'bay leaves'], 25, 50),
        ('Senegalese Thieboudienne', 'senegalese-thieboudienne', 'african', 'African', ['gluten-free'],
         ['600 g firm white fish', '2 cups broken rice', '2 onions', '4 tbsp tomato paste', '2 tomatoes', '1 small cabbage', '1 large carrot', '1 eggplant', '2 Scotch bonnets', '1/4 cup palm oil', '2 tbsp parsley-garlic paste (rof)', 'salt'], 30, 75),
        ('Moroccan Chicken Bastilla', 'moroccan-chicken-bastilla', 'african', 'African', [],
         ['1 kg chicken (poached, shredded)', '12 sheets phyllo pastry', '4 eggs (scrambled into broth)', '1 cup almonds', '1 cinnamon stick', '4 tbsp powdered sugar (dusting)', '2 tbsp ras-el-hanout', '4 tbsp butter', 'cilantro and parsley'], 60, 35),
    ]),
    ('Chef Lourdes Castillo', 'Caribbean-Regional', [
        ('Jamaican Jerk Chicken', 'jamaican-jerk-chicken', 'caribbean', 'Caribbean', ['gluten-free'],
         ['1 kg chicken thighs', '6 green onions', '6 garlic cloves', '2 Scotch bonnets', '1 tbsp fresh thyme', '1 tbsp ground allspice', '1 tbsp brown sugar', '2 tbsp soy sauce', '2 tbsp lime juice', '1 tbsp dark rum', '1 tsp cinnamon', 'salt'], 30, 35),
        ('Cuban Ropa Vieja', 'cuban-ropa-vieja', 'caribbean', 'Caribbean', ['gluten-free'],
         ['1 kg flank steak', '2 bell peppers (sliced)', '1 onion (sliced)', '6 garlic cloves', '1 can crushed tomatoes', '1 cup beef stock', '1 tbsp ground cumin', '1 tsp oregano', '2 bay leaves', '1/2 cup pimento-stuffed olives', '1/4 cup capers', 'salt and pepper'], 20, 180),
        ('Trinidadian Doubles', 'trinidadian-doubles', 'caribbean', 'Caribbean', ['vegetarian', 'vegan'],
         ['3 cups flour', '1 tbsp turmeric', '1 tsp cumin', '1 tbsp yeast', '2 cups dried chickpeas (soaked)', '1 tsp curry powder', '2 cloves garlic', '1 Scotch bonnet', '2 tbsp mango chutney', 'cilantro and tamarind sauce'], 90, 30),
        ('Bajan Flying Fish Cou-Cou', 'bajan-flying-fish-cou-cou', 'caribbean', 'Caribbean', ['gluten-free'],
         ['600 g flying fish (or any white fish)', '2 cups cornmeal', '1 cup okra (sliced)', '1 onion', '2 tomatoes', '1 tbsp Bajan seasoning', '2 tbsp lime juice', '2 tbsp butter', 'salt and pepper'], 25, 30),
        ('Haitian Griot (Fried Pork)', 'haitian-griot', 'caribbean', 'Caribbean', ['gluten-free'],
         ['1 kg pork shoulder (cubed)', '6 garlic cloves', '1 sour orange (juice)', '2 limes (juice)', '1 Scotch bonnet', '1 onion', '1 tbsp thyme', '1 cup epis (Haitian seasoning paste)', 'oil for frying', 'salt'], 30, 90),
        ('Puerto Rican Mofongo', 'puerto-rican-mofongo', 'caribbean', 'Caribbean', ['gluten-free'],
         ['4 green plantains', '200 g chicharrón (pork rind)', '6 garlic cloves', '2 tbsp olive oil', '1 tsp salt', '1 cup chicken stock', 'fresh cilantro'], 20, 25),
        ('Dominican Sancocho', 'dominican-sancocho', 'caribbean', 'Caribbean', ['gluten-free'],
         ['500 g beef shank', '500 g chicken thigh', '300 g pork ribs', '2 green plantains', '2 yuca', '2 ñame (yam)', '1 chayote', '1 corn (sliced)', '1 onion', '6 garlic cloves', '1 bunch cilantro', '1 tbsp oregano', 'salt'], 30, 120),
    ]),
]


def _seed_r9_chef_recipes(cat_by_slug, existing_slugs):
    added = 0
    for ci, (chef, cuisine_label, dishes) in enumerate(R9_CHEF_RECIPES):
        for di, dish in enumerate(dishes):
            (title, slug, cat_slug, cuisine, dietary, ings, prep, cook) = dish
            if slug in existing_slugs:
                continue
            cat = cat_by_slug.get(cat_slug)
            existing_slugs.add(slug)
            total = max(1, prep + cook)
            ri = ci * 100 + di
            img_n = ((ri * 353 + 53) % IMAGE_POOL_SIZE) + 1
            feature_tags = [
                cat_slug, cuisine.lower(), 'chef-special',
                f'chef-{_slugify(chef.replace("Chef ", ""))}',
                cuisine_label.lower(),
            ] + list(dietary)
            gallery = [{
                'title': 'Chef walkthrough',
                'desc': f"Step-by-step photos of {title} by {chef}.",
                'images': [
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 359 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 367 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 373 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                ],
            }]
            created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 29 + 13) % 720)
            calories = 420 + (ri * 23) % 260
            avg_rating = round(4.6 + (ri % 5) * 0.05, 1)
            rec = Recipe(
                title=title, slug=slug,
                description=(
                    f"{chef}'s signature {title} — a {cuisine_label.lower()} classic "
                    "cooked with regional technique and authentic spice ratios."),
                category_id=cat.id if cat else None, cuisine=cuisine,
                image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
                prep_time=_fmt_mins(prep), cook_time=_fmt_mins(cook),
                total_time=_fmt_mins(total),
                servings='6',
                calories=calories,
                ingredients_json=json.dumps(ings),
                instructions_json=json.dumps([
                    f"Read the {title} recipe top to bottom — regional cooking rewards mise en place.",
                    "Stage every spice and aromatic at the correct stage — whole spices first, ground spices near the end.",
                    f"Follow {chef}'s heat curve exactly; the dish moves through bloom, sweat, sear, and simmer phases.",
                    f"Finish with the traditional regional garnish — fresh herbs, citrus, or a knob of fat as listed.",
                    "Serve with the canonical accompaniment for the region (rice / injera / fufu / pita / plantain).",
                ]),
                nutrition_json=json.dumps({'Calories': str(calories), 'Protein': '28g', 'Fat': '24g', 'Carbs': '34g'}),
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
                dish_type='main', meal_type='dinner',
                cooking_method='simmered',
                main_ingredient='varies',
                occasion='', season='',
                feature_tags=json.dumps(feature_tags),
                latest_review_text='',
                storage_instructions="Stores 4 days refrigerated; regional stews and curries deepen overnight.",
                primary_seasoning='regional-spice-blend',
                max_oven_temp=0,
                created_at=created,
            )
            db.session.add(rec)
            added += 1
    return added


# ===========================================================================
# Public entry point — called from seed_data.seed_extended_catalog after R8.
# ===========================================================================

R9_SENTINEL_SLUG = 'butter-chicken-murgh-makhani'


def run_r9_polish(cat_by_slug):
    """R9 top-level. Returns a counts dict."""
    if (Recipe.query.filter_by(slug=R9_SENTINEL_SLUG).first()
            or Recipe.query.filter_by(slug='indian-regional-classic-waffles').first()):
        return {'skipped': True}

    counts = {}

    # 1) Ethnic-cuisine top-level categories
    counts['categories'] = _seed_r9_categories(cat_by_slug)
    db.session.flush()
    cat_by_slug.update({c.slug: c for c in Category.query.all()})

    # 2) Chef recipes (small set, before variant passes)
    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['r9_chef'] = _seed_r9_chef_recipes(cat_by_slug, existing_recipe_slugs)
    db.session.flush()

    # 3) Variant passes — base = Test Kitchen recipes not already R6/R7/R8/R9.
    # Subsample by step 7 -> ~1180 per pass × 4 = ~4720 new.
    base_for_r9 = (Recipe.query
                   .filter(Recipe.author_name.like('%Test Kitchen%'))
                   .order_by(Recipe.id)
                   .all())
    base_for_r9 = [r for r in base_for_r9
                   if not _is_prev_variant(r.author_name)]
    base_for_r9 = base_for_r9[::7]
    print(f"[r9_seed] base_for_r9 size: {len(base_for_r9)}")

    counts['indian'] = _seed_indian_variants(cat_by_slug, base_for_r9, existing_recipe_slugs)
    db.session.flush()
    counts['middle_eastern'] = _seed_mideast_variants(cat_by_slug, base_for_r9, existing_recipe_slugs)
    db.session.flush()
    counts['caribbean'] = _seed_caribbean_variants(cat_by_slug, base_for_r9, existing_recipe_slugs)
    db.session.flush()
    counts['african'] = _seed_african_variants(cat_by_slug, base_for_r9, existing_recipe_slugs)
    db.session.flush()

    return counts
