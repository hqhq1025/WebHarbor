"""R7 polish seed — international cuisines + vegetarian-by-protein passes
+ new chefs broadening cuisine-origin coverage.

Runs AFTER R6 inside ``seed_data.seed_extended_catalog``. Everything in
here is deterministic so a rebuild from source is byte-identical to the
shipped ``instance_seed/allrecipes.db``.

R7 deliverables (recipes 14054 -> 18000+):
  * 4 new variant passes — Korean, Thai-Regional, Mexican-Regional,
    Vegetarian-by-Protein — each operating on the same Test Kitchen
    base subsample (~1000 recipes per pass, ~4000 new total).
  * 4 new chefs (~48 recipes) broadening cuisine-origin coverage
    (Korean, Thai, Mexican-regional, Plant-based by protein).

Idempotent — gated on the presence of a sentinel R7 recipe slug.
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


# Authors we never re-iterate over (R7 own + R6 variants).
R7_AUTHOR_TOKENS = (
    'Korean-Regional', 'Thai-Regional', 'Mexican-Regional',
    'Vegetarian-By-Protein',
)
R6_AUTHOR_TOKENS = (
    'Copycat-Restaurant', 'Budget-Friendly', 'Holiday-Entertaining',
    'Air-Fryer-Shortcut',
)


def _is_r7_variant(author_name: str) -> bool:
    return any(tok in (author_name or '') for tok in R7_AUTHOR_TOKENS)


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
# Pass 1 — Korean-Regional variants
# ===========================================================================

KOREAN_INSTRUCTIONS = [
    "Build your korean flavor base first: gochujang + soy + sesame oil + a pinch of sugar — taste before adding anything else.",
    "Marinate the protein for at least 20 minutes in the korean base so the flavor goes all the way through.",
    "Cook over high heat for the maillard char that Korean BBQ is famous for; do not crowd the pan.",
    "Finish with toasted sesame seeds and thin-sliced scallion greens — they hit the dish at the table, not in the pan.",
    "Serve with banchan (kimchi, pickled radish, blanched spinach) and short-grain rice for the full bansang spread.",
]


def _seed_korean_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_title = f"Korean-Regional {base.title}"
        new_slug = f"korean-regional-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 25
        new_prep = max(15, base_prep + 5)
        new_cook = max(10, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '2 tbsp gochujang (Korean fermented chile paste)',
            '1 tbsp toasted sesame oil',
            '1 tbsp soy sauce',
            '1 tsp toasted sesame seeds (finish)',
            '2 scallions, thin-sliced (finish)',
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
            'korean', 'korean-regional', 'gochujang', 'sesame', 'banchan',
            cat_slug or 'dinner']))
        img_n = ((ri * 167 + 13) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Korean walkthrough',
            'desc': f"Plating walkthrough for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 173 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 179 + 19) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 181 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 19 + 11) % 720)
        cal = max(300, (base.calories or 420))
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A Korean-regional take on {base.title}. Built on a gochujang + "
                "sesame-oil base, marinated for depth, finished with banchan "
                "and short-grain rice for a full bansang spread."),
            category_id=base.category_id, cuisine='Korean',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(KOREAN_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 73 == 0),
            is_editors_pick=(ri % 97 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 11 - 5) * 0.02)), 1),
            review_count=0,
            author_name='Korean-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or 'stir-fry',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 2 days; reheat in a hot pan to refresh the sesame oil aromatics.',
            primary_seasoning='gochujang',
            max_oven_temp=base.max_oven_temp or 0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 2 — Thai-Regional variants
# ===========================================================================

THAI_INSTRUCTIONS = [
    "Balance the four Thai pillars in the bowl: salty (fish sauce), sour (lime), sweet (palm sugar), spicy (bird chiles) — taste, taste, taste.",
    "Pound your aromatics (lemongrass, galangal, cilantro root) in a mortar and pestle to release their oils — knife-cut won't do it.",
    "Use a wide wok or skillet on the highest heat and don't crowd the pan; Thai stir-fry depends on the wok hei char.",
    "Add fresh herbs (Thai basil, mint, cilantro) at the very end — they wilt in seconds and lose their perfume if cooked.",
    "Serve over jasmine rice with a small bowl of nam pla prik (fish sauce + chiles + lime) for adjustment at the table.",
]


def _seed_thai_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        new_title = f"Thai-Regional {base.title}"
        new_slug = f"thai-regional-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 25
        new_prep = max(15, base_prep + 5)
        new_cook = max(10, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '2 tbsp fish sauce',
            '1 tbsp palm sugar',
            '2 limes (juice + zest)',
            '2 bird chiles, sliced',
            '1 stalk lemongrass, bruised',
            '1 handful Thai basil (finish)',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        # Thai versions are dairy-free by construction.
        if 'dairy-free' not in base_dietary:
            base_dietary = list(base_dietary) + ['dairy-free']
        new_features = list(dict.fromkeys(base_features + [
            'thai', 'thai-regional', 'fish-sauce', 'lemongrass', 'thai-basil',
            cat_slug or 'dinner']))
        img_n = ((ri * 191 + 17) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': 'Thai walkthrough',
            'desc': f"Aromatic plating for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 193 + 5) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 197 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 199 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 29 + 13) % 720)
        cal = max(280, (base.calories or 380))
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A Thai-regional take on {base.title}. Built on the four Thai "
                "pillars (salty / sour / sweet / spicy), aromatics pounded in a "
                "mortar, finished with Thai basil at the table."),
            category_id=base.category_id, cuisine='Thai',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(THAI_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 79 == 0),
            is_editors_pick=(ri % 103 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.4) + ((ri % 9 - 4) * 0.02)), 1),
            review_count=0,
            author_name='Thai-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or 'stir-fry',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 2 days; refresh with a squeeze of lime when reheating.',
            primary_seasoning='fish-sauce',
            max_oven_temp=base.max_oven_temp or 0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 3 — Mexican-Regional variants
# ===========================================================================

MEXICAN_REGIONS = ('Oaxacan', 'Yucatecan', 'Pueblan', 'Sonoran', 'Veracruzano', 'Jalisciense')
MEXICAN_INSTRUCTIONS = [
    "Toast every whole spice and dried chile before grinding — the regional Mexican cooks call this the moment the kitchen wakes up.",
    "Build a wet base (sofrito / recaudo / mole) before adding the main protein; the dish's regional identity lives in this base.",
    "Cook low and slow when the regional dish calls for stewing (mole, birria, cochinita); the depth comes from time, not heat.",
    "Use fresh masa or rehydrated masa harina for the corn component; never substitute wheat tortillas for a corn-tortilla regional dish.",
    "Finish with a regional salsa at the table (xnipec for Yucatecan, salsa macha for Veracruzano, salsa de molcajete for Oaxacan).",
]


def _seed_mexican_regional_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        region = MEXICAN_REGIONS[ri % len(MEXICAN_REGIONS)]
        new_title = f"{region}-Style {base.title}"
        new_slug = f"mexican-{region.lower()}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 25
        base_cook = base.cook_time_mins or 40
        new_prep = max(15, base_prep + 5)
        new_cook = max(20, base_cook + 5)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        new_ings = list(base_ings) + [
            '3 dried guajillo chiles',
            '2 dried ancho chiles',
            '1 tsp Mexican oregano',
            '1 tsp cumin seed (toasted)',
            '2 tbsp lard or neutral oil (sofrito)',
            '1 cup masa-based component (tortillas, sope, gordita)',
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
            'mexican', 'mexican-regional', region.lower(), 'sofrito',
            'masa', 'guajillo', cat_slug or 'dinner']))
        img_n = ((ri * 211 + 19) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f'{region}-style walkthrough',
            'desc': f"Regional plating for {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 223 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 227 + 29) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 229 + 43) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 37 + 17) % 720)
        cal = max(320, (base.calories or 450))
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A {region}-style regional take on {base.title}. Built around a "
                f"toasted-chile recaudo + masa component, finished with a "
                f"regional salsa at the table — true to the {region} kitchen."),
            category_id=base.category_id, cuisine='Mexican',
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(MEXICAN_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 83 == 0),
            is_editors_pick=(ri % 107 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.3) + ((ri % 9 - 4) * 0.02)), 1),
            review_count=0,
            author_name='Mexican-Regional Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(base_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or 'braised',
            main_ingredient=base.main_ingredient,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 3 days; the sauce deepens overnight — reheat gently with a splash of stock.',
            primary_seasoning='guajillo',
            max_oven_temp=base.max_oven_temp or 0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# Pass 4 — Vegetarian-By-Protein variants
# ===========================================================================

VEG_PROTEINS = (
    ('tofu',     'firm tofu (pressed)',           'soy'),
    ('tempeh',   'tempeh (cubed)',                'soy'),
    ('seitan',   'sliced seitan',                 'wheat'),
    ('chickpea', 'rinsed chickpeas',              'legume'),
    ('lentil',   'cooked green lentils',          'legume'),
    ('jackfruit','young jackfruit (shredded)',    'fruit-protein'),
    ('mushroom', 'sliced cremini mushrooms',      'mushroom'),
    ('paneer',   'pan-fried paneer cubes',        'dairy'),
)
VEG_INSTRUCTIONS = [
    "Treat the plant protein like the original meat: salt-cure or marinate so it absorbs the dish's flavor base.",
    "Sear or roast the protein dry on high heat first — the maillard browning is what makes the plant version taste cooked, not steamed.",
    "Use a savory hit (miso, soy, nutritional yeast, mushroom powder) to replace the meat's umami; don't try to disguise — replace.",
    "Build texture deliberately: cube tofu, shred jackfruit, slice mushrooms thick so each bite has the chew the meat version had.",
    "Finish with a fat (extra-virgin olive oil, brown butter, tahini, or cashew cream) — plant proteins read leaner unless you balance with fat.",
]


def _seed_vegetarian_by_protein_variants(cat_by_slug, base_recipes, existing_slugs):
    added = 0
    for ri, base in enumerate(base_recipes):
        if _is_r6_variant(base.author_name) or _is_r7_variant(base.author_name):
            continue
        cat_slug = _cat_slug_for(base, cat_by_slug)
        prot_key, prot_label, prot_family = VEG_PROTEINS[ri % len(VEG_PROTEINS)]
        new_title = f"Vegetarian-{prot_key.capitalize()} {base.title}"
        new_slug = f"vegetarian-{prot_key}-{base.slug}"
        if new_slug in existing_slugs:
            continue
        existing_slugs.add(new_slug)
        base_prep = base.prep_time_mins or 20
        base_cook = base.cook_time_mins or 25
        new_prep = max(15, base_prep + 5)
        new_cook = max(15, base_cook)
        new_total = new_prep + new_cook
        try:
            base_ings = json.loads(base.ingredients_json or '[]')
        except Exception:
            base_ings = []
        # Strip obvious meat-only ingredients from the inherited list.
        meat_tokens = ('chicken', 'beef', 'pork', 'sausage', 'bacon', 'ham',
                       'turkey', 'lamb', 'fish', 'shrimp', 'salmon', 'tuna',
                       'anchovy', 'pancetta', 'prosciutto', 'crab')
        cleaned_ings = []
        for ing in base_ings:
            low = (ing or '').lower()
            if any(tok in low for tok in meat_tokens):
                continue
            cleaned_ings.append(ing)
        new_ings = cleaned_ings + [
            f'1 lb {prot_label}',
            '2 tbsp soy sauce or tamari (savory hit)',
            '1 tbsp miso paste',
            '1 tsp nutritional yeast',
            '2 tbsp tahini or cashew cream (finish)',
        ]
        try:
            base_features = json.loads(base.feature_tags or '[]')
        except Exception:
            base_features = []
        try:
            base_dietary = json.loads(base.dietary_tags_json or '[]')
        except Exception:
            base_dietary = []
        # Always vegetarian. Most are also dairy-free / vegan unless paneer.
        dietary = set(base_dietary) | {'vegetarian'}
        if prot_key != 'paneer':
            dietary.add('dairy-free')
            dietary.add('vegan')
        if prot_key in ('tofu', 'tempeh', 'chickpea', 'lentil', 'jackfruit',
                         'mushroom'):
            dietary.add('plant-based')
        new_dietary = sorted(dietary)
        new_features = list(dict.fromkeys(base_features + [
            'vegetarian', 'vegetarian-by-protein', prot_key,
            f'protein-{prot_family}', 'meat-free', cat_slug or 'dinner']))
        img_n = ((ri * 233 + 23) % IMAGE_POOL_SIZE) + 1
        gallery = [{
            'title': f'{prot_key.capitalize()} walkthrough',
            'desc': f"Step-by-step photos of {new_title}.",
            'images': [
                f"{IMAGES_DIR_REL}/recipe_{((ri * 239 + 11) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 241 + 31) % IMAGE_POOL_SIZE) + 1}.jpg",
                f"{IMAGES_DIR_REL}/recipe_{((ri * 251 + 47) % IMAGE_POOL_SIZE) + 1}.jpg",
            ],
        }]
        created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 41 + 19) % 720)
        cal = max(260, (base.calories or 380) - 40)
        rec = Recipe(
            title=new_title, slug=new_slug,
            description=(
                f"A vegetarian-{prot_key} take on {base.title}. The plant protein "
                "is salt-cured + seared dry first; umami is rebuilt with miso + "
                "nutritional yeast; finished with tahini or cashew cream for richness."),
            category_id=base.category_id, cuisine=base.cuisine,
            image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
            prep_time=_fmt_mins(new_prep), cook_time=_fmt_mins(new_cook),
            total_time=_fmt_mins(new_total),
            servings=base.servings or '4',
            calories=cal,
            ingredients_json=json.dumps(new_ings),
            instructions_json=json.dumps(list(VEG_INSTRUCTIONS)),
            nutrition_json=base.nutrition_json or json.dumps({'Calories': str(cal)}),
            tags_json=json.dumps(new_features),
            gallery_json=json.dumps(gallery),
            is_featured=(ri % 89 == 0),
            is_editors_pick=(ri % 113 == 0),
            avg_rating=round(min(5.0, (base.avg_rating or 4.3) + ((ri % 7 - 3) * 0.02)), 1),
            review_count=0,
            author_name='Vegetarian-By-Protein Test Kitchen',
            prep_time_mins=new_prep, cook_time_mins=new_cook, total_time_mins=new_total,
            ingredient_count=len(new_ings),
            dietary_tags_json=json.dumps(new_dietary),
            dish_type=base.dish_type, meal_type=base.meal_type,
            cooking_method=base.cooking_method or '',
            main_ingredient=prot_key,
            occasion='', season='',
            feature_tags=json.dumps(new_features),
            latest_review_text='',
            storage_instructions='Stores 3 days; the protein takes flavor beautifully overnight.',
            primary_seasoning='miso',
            max_oven_temp=base.max_oven_temp or 0,
            created_at=created,
        )
        db.session.add(rec)
        added += 1
    return added


# ===========================================================================
# R7 chef recipes — 4 new chefs broadening cuisine-origin coverage.
# ===========================================================================

R7_CHEF_RECIPES = [
    ('Chef Soo-jin Park', 'Korean', [
        ('Bibimbap Mixed Rice Bowl',           'bibimbap-mixed-rice-bowl',           'main-dishes', 'Korean', ['gluten-free'],            ['2 cups short-grain rice', '1 cup spinach', '1 cup bean sprouts', '1 cup julienned carrot', '1 cup sliced shiitake', '1 lb beef bulgogi', '4 eggs', '4 tbsp gochujang'], 30, 25),
        ('Galbi Korean Short Ribs',            'galbi-korean-short-ribs',            'beef',        'Korean', ['dairy-free'],             ['3 lb flanken short ribs', '1/2 cup soy sauce', '1/2 cup brown sugar', '1 pear (grated)', '6 cloves garlic', '2 tbsp sesame oil', '1 tbsp toasted sesame seeds'], 20, 12),
        ('Kimchi Jjigae Stew',                 'kimchi-jjigae-stew',                 'soups',       'Korean', ['dairy-free'],             ['2 cups aged kimchi', '8 oz pork belly', '1 block tofu', '4 cups stock', '2 tbsp gochujang', '1 tbsp gochugaru', '2 scallions'], 15, 30),
        ('Japchae Glass Noodles',              'japchae-glass-noodles',              'main-dishes', 'Korean', ['dairy-free'],             ['8 oz sweet potato glass noodles', '1 lb beef sirloin', '1 cup spinach', '1 cup julienned carrot', '1 onion', '6 shiitake', '3 tbsp soy sauce', '2 tbsp sesame oil'], 25, 20),
        ('Bulgogi Marinated Beef',             'bulgogi-marinated-beef',             'beef',        'Korean', ['dairy-free'],             ['2 lb ribeye (thin-sliced)', '1/2 cup soy sauce', '1/4 cup brown sugar', '1 Asian pear', '4 cloves garlic', '2 tbsp sesame oil', '4 scallions'], 25, 10),
        ('Tteokbokki Spicy Rice Cakes',        'tteokbokki-spicy-rice-cakes',        'main-dishes', 'Korean', ['vegetarian'],              ['1 lb Korean rice cakes', '4 cups dashi', '3 tbsp gochujang', '1 tbsp gochugaru', '2 sheets fish cake', '2 scallions', '1 tbsp sugar'], 10, 20),
        ('Banchan Pickled Radish',             'banchan-pickled-radish',             'side-dishes', 'Korean', ['vegan', 'gluten-free'],   ['1 lb daikon', '1 cup rice vinegar', '1/2 cup sugar', '1 tbsp salt', '1 tbsp gochugaru'], 10, 0),
        ('Sundubu Jjigae Soft Tofu Stew',      'sundubu-jjigae-soft-tofu-stew',      'soups',       'Korean', ['vegetarian'],              ['2 packages silken tofu', '1 cup kimchi', '4 cups dashi', '2 tbsp gochugaru', '1 tbsp gochujang', '2 eggs', '2 scallions'], 10, 25),
        ('Korean Fried Chicken Yangnyeom',     'korean-fried-chicken-yangnyeom',     'chicken',     'Korean', [],                          ['2 lb chicken wings', '1 cup cornstarch', '1/2 cup gochujang', '1/4 cup honey', '3 tbsp soy sauce', '4 cloves garlic', '1 tbsp toasted sesame seeds'], 20, 25),
        ('Kalbi Tang Short Rib Soup',          'kalbi-tang-short-rib-soup',          'soups',       'Korean', ['dairy-free'],             ['3 lb beef short ribs', '1 daikon', '1 onion', '2 scallions', '2 tbsp soy sauce', '1 tsp sesame oil'], 20, 180),
        ('Pajeon Scallion Pancake',            'pajeon-scallion-pancake',            'appetizers',  'Korean', ['vegetarian'],              ['1.5 cups flour', '1 egg', '1 cup ice water', '8 scallions', '1/2 cup julienned squid (optional)', '3 tbsp neutral oil'], 10, 12),
        ('Bossam Boiled Pork Wraps',           'bossam-boiled-pork-wraps',           'pork',        'Korean', ['dairy-free'],             ['3 lb pork belly', '1 head garlic', '1 piece ginger', '1 cup doenjang', '1 head napa cabbage', '1 cup kimchi'], 15, 90),
    ]),
    ('Chef Niran Sutthi', 'Thai', [
        ('Pad Thai',                           'pad-thai-classic',                   'main-dishes', 'Thai', ['dairy-free'],              ['8 oz rice noodles', '1/2 lb shrimp', '4 oz firm tofu', '2 eggs', '1 cup bean sprouts', '3 tbsp fish sauce', '3 tbsp tamarind', '2 tbsp palm sugar', '1/4 cup peanuts'], 20, 15),
        ('Tom Yum Goong',                      'tom-yum-goong-hot-sour-soup',        'soups',       'Thai', ['dairy-free', 'pescatarian'], ['1 lb shrimp', '4 cups stock', '3 stalks lemongrass', '5 kaffir lime leaves', '1 piece galangal', '4 Thai chiles', '3 tbsp fish sauce', '3 tbsp lime juice'], 15, 20),
        ('Green Curry Chicken',                'green-curry-chicken',                'main-dishes', 'Thai', ['dairy-free', 'gluten-free'], ['1.5 lb chicken thighs', '1 can coconut milk', '3 tbsp green curry paste', '1 Thai eggplant', '1/2 cup bamboo shoots', '1 handful Thai basil', '2 tbsp fish sauce'], 15, 25),
        ('Som Tam Papaya Salad',               'som-tam-papaya-salad',               'salads',      'Thai', ['vegan', 'gluten-free'],   ['1 green papaya', '4 cherry tomatoes', '4 garlic cloves', '4 Thai chiles', '3 tbsp fish sauce (or soy)', '3 tbsp lime juice', '2 tbsp palm sugar', '1/4 cup peanuts'], 15, 0),
        ('Massaman Curry Beef',                'massaman-curry-beef',                'beef',        'Thai', ['dairy-free', 'gluten-free'], ['2 lb beef chuck', '1 can coconut milk', '3 tbsp massaman paste', '2 potatoes', '1/2 cup peanuts', '1 onion', '2 tbsp fish sauce', '2 tbsp palm sugar'], 20, 120),
        ('Larb Gai Spicy Chicken Salad',       'larb-gai-spicy-chicken-salad',       'salads',      'Thai', ['dairy-free', 'gluten-free'], ['1 lb ground chicken', '3 tbsp fish sauce', '3 tbsp lime juice', '1 tbsp toasted rice powder', '4 shallots', '1 bunch mint', '1 bunch cilantro'], 15, 10),
        ('Pad Krapow Holy Basil Stir-Fry',     'pad-krapow-holy-basil',              'main-dishes', 'Thai', ['dairy-free'],              ['1 lb ground pork', '6 cloves garlic', '4 Thai chiles', '2 tbsp oyster sauce', '1 tbsp soy sauce', '1 tsp sugar', '1 cup holy basil', '4 fried eggs'], 10, 10),
        ('Khao Soi Northern Curry Noodle',     'khao-soi-northern-curry-noodle',     'main-dishes', 'Thai', ['dairy-free'],              ['1 lb egg noodles', '1.5 lb chicken legs', '1 can coconut milk', '3 tbsp khao soi paste', '2 tbsp fish sauce', '1/4 cup pickled mustard greens', '4 shallots'], 20, 35),
        ('Mango Sticky Rice',                  'mango-sticky-rice',                  'desserts',    'Thai', ['vegan', 'gluten-free'],   ['1.5 cups sticky rice', '1 can coconut milk', '1/3 cup sugar', '1 tsp salt', '2 ripe mangoes', '1 tbsp toasted sesame seeds'], 15, 30),
        ('Tom Kha Gai Chicken Coconut Soup',   'tom-kha-gai-chicken-coconut-soup',   'soups',       'Thai', ['dairy-free', 'gluten-free'], ['1 lb chicken thighs', '1 can coconut milk', '3 cups stock', '4 slices galangal', '3 stalks lemongrass', '6 mushrooms', '3 tbsp fish sauce', '3 tbsp lime juice'], 10, 25),
        ('Yum Woon Sen Glass Noodle Salad',    'yum-woon-sen-glass-noodle-salad',    'salads',      'Thai', ['dairy-free'],              ['8 oz glass noodles', '1/2 lb ground pork', '1/2 lb shrimp', '4 shallots', '2 Thai chiles', '3 tbsp fish sauce', '3 tbsp lime juice', '1/4 cup peanuts'], 15, 15),
        ('Khanom Krok Coconut Pancakes',       'khanom-krok-coconut-pancakes',       'desserts',    'Thai', ['vegan', 'gluten-free'],   ['1.5 cups rice flour', '1 can coconut milk', '1/3 cup sugar', '1/2 tsp salt', '2 tbsp scallion'], 15, 20),
    ]),
    ('Chef Adriana Castillo', 'Mexican', [
        ('Mole Poblano',                       'mole-poblano',                       'main-dishes', 'Mexican', ['dairy-free'],            ['1 whole chicken (cut)', '4 ancho chiles', '4 mulato chiles', '4 pasilla chiles', '2 chipotle in adobo', '1/2 cup almonds', '1/2 cup raisins', '2 tomatoes', '3 tbsp sesame seeds', '2 oz Mexican chocolate'], 60, 120),
        ('Cochinita Pibil',                    'cochinita-pibil',                    'pork',        'Mexican', ['dairy-free', 'gluten-free'], ['4 lb pork shoulder', '4 oz achiote paste', '1 cup sour orange juice', '1 tbsp Mexican oregano', '4 cloves garlic', '1 banana leaf', '1 red onion (pickled)'], 30, 240),
        ('Birria de Res',                      'birria-de-res',                      'beef',        'Mexican', ['dairy-free', 'gluten-free'], ['4 lb beef chuck', '6 guajillo chiles', '4 ancho chiles', '2 chipotle in adobo', '1 tbsp cumin', '1 tbsp Mexican oregano', '1 onion', '6 cloves garlic'], 30, 240),
        ('Chiles en Nogada',                   'chiles-en-nogada',                   'main-dishes', 'Mexican', [],                          ['6 poblano chiles', '1 lb ground pork', '1/4 cup raisins', '1/4 cup almonds', '1 ripe pear', '1 cup walnuts', '1 cup crema', '1 pomegranate'], 45, 60),
        ('Pozole Rojo',                        'pozole-rojo',                        'soups',       'Mexican', ['dairy-free'],            ['2 lb pork shoulder', '2 cans hominy', '6 guajillo chiles', '4 ancho chiles', '1 onion', '4 cloves garlic', '1 cabbage (garnish)', '4 radishes (garnish)'], 25, 180),
        ('Tlayudas Oaxaqueñas',                'tlayudas-oaxaquenas',                'main-dishes', 'Mexican', [],                          ['8 large corn tortillas', '1 cup refried black beans', '1 lb tasajo (cured beef)', '1 cup Oaxacan string cheese', '1/2 cup salsa', '2 avocados'], 25, 20),
        ('Sopa de Tortilla',                   'sopa-de-tortilla',                   'soups',       'Mexican', [],                          ['8 cups chicken stock', '2 tomatoes', '2 pasilla chiles', '1 onion', '4 cloves garlic', '12 fried tortilla strips', '4 oz queso fresco', '1 avocado'], 20, 30),
        ('Tacos al Pastor',                    'tacos-al-pastor',                    'pork',        'Mexican', ['dairy-free'],            ['3 lb pork shoulder', '4 guajillo chiles', '2 ancho chiles', '2 tbsp achiote paste', '1/4 cup white vinegar', '1 pineapple', '20 corn tortillas', '1 bunch cilantro'], 30, 30),
        ('Enchiladas Verdes',                  'enchiladas-verdes',                  'main-dishes', 'Mexican', [],                          ['12 corn tortillas', '1 lb shredded chicken', '1 lb tomatillos', '2 jalapenos', '1 cup chicken stock', '1 cup queso fresco', '1 cup crema', '1/2 cup cilantro'], 20, 30),
        ('Chiles Rellenos',                    'chiles-rellenos',                    'main-dishes', 'Mexican', [],                          ['8 poblano chiles', '1 lb queso Oaxaca', '4 eggs', '1 cup flour', '2 tomatoes', '1 onion', '2 cloves garlic', '1 cup tomato sauce'], 30, 25),
        ('Tamales Verdes',                     'tamales-verdes',                     'main-dishes', 'Mexican', ['gluten-free'],            ['4 cups masa harina', '1 lb shredded chicken', '1 lb tomatillos', '2 jalapenos', '1 cup chicken stock', '1 cup lard', '20 corn husks'], 60, 90),
        ('Champurrado',                        'champurrado',                        'desserts',    'Mexican', ['vegetarian'],              ['4 cups whole milk', '1 cup masa harina', '6 oz Mexican chocolate', '1/2 cup piloncillo', '1 cinnamon stick', '1 tsp vanilla'], 5, 25),
    ]),
    ('Chef Iris Bloom', 'Plant-Based', [
        ('Cashew Cream Alfredo with Roasted Cauliflower', 'cashew-cream-alfredo-cauliflower',  'pasta',       'Italian', ['vegan', 'dairy-free'], ['1 lb fettuccine', '1.5 cups raw cashews (soaked)', '1 head cauliflower', '4 cloves garlic', '1/4 cup nutritional yeast', '2 tbsp lemon juice', '1 tbsp white miso'], 15, 25),
        ('Smoky Tempeh BLT',                  'smoky-tempeh-blt',                   'sandwiches',  'American', ['vegan'],                   ['1 block tempeh', '4 tbsp soy sauce', '2 tbsp maple syrup', '1 tsp smoked paprika', '8 slices sourdough', '4 tomatoes', '1 head lettuce', '1/2 cup vegan mayo'], 15, 12),
        ('Lentil Walnut Bolognese',           'lentil-walnut-bolognese',            'pasta',       'Italian', ['vegan', 'dairy-free'], ['1 lb spaghetti', '1.5 cups green lentils', '1 cup walnuts', '1 can crushed tomatoes', '1 onion', '4 cloves garlic', '1/4 cup nutritional yeast', '2 tbsp tomato paste'], 15, 35),
        ('Jackfruit Carnitas Tacos',          'jackfruit-carnitas-tacos',           'main-dishes', 'Mexican', ['vegan', 'dairy-free'], ['2 cans young jackfruit', '1 onion', '4 cloves garlic', '1 tbsp cumin', '1 tbsp Mexican oregano', '2 tbsp orange juice', '12 corn tortillas', '1 cup salsa verde'], 15, 30),
        ('Chickpea Tikka Masala',             'chickpea-tikka-masala',              'main-dishes', 'Indian', ['vegan', 'dairy-free', 'gluten-free'], ['2 cans chickpeas', '1 can coconut milk', '1 can crushed tomatoes', '1 onion', '4 cloves garlic', '1 piece ginger', '2 tbsp garam masala', '1 tbsp turmeric'], 15, 30),
        ('Crispy Tofu Pad See Ew',            'crispy-tofu-pad-see-ew',             'main-dishes', 'Thai', ['vegan'],                   ['1 block extra-firm tofu', '1 lb wide rice noodles', '1 bunch Chinese broccoli', '3 cloves garlic', '3 tbsp soy sauce', '2 tbsp dark soy', '2 tbsp sugar', '2 eggs (optional)'], 20, 15),
        ('Mushroom Bourguignon',              'mushroom-bourguignon',               'main-dishes', 'French', ['vegan'],                  ['2 lb mixed mushrooms', '1 cup pearl onions', '4 carrots', '2 cups dry red wine', '2 cups stock', '3 tbsp tomato paste', '4 cloves garlic', '2 tbsp soy sauce'], 20, 60),
        ('Black Bean Burger',                 'black-bean-burger',                  'sandwiches',  'American', ['vegan'],                  ['2 cans black beans', '1 cup cooked brown rice', '1/2 cup oats', '1 onion', '4 cloves garlic', '1 tbsp smoked paprika', '1 tbsp cumin', '4 burger buns'], 15, 20),
        ('Seitan Korean BBQ Bowl',            'seitan-korean-bbq-bowl',             'main-dishes', 'Korean', ['vegan'],                  ['1 lb seitan', '3 tbsp soy sauce', '2 tbsp gochujang', '1 tbsp sesame oil', '2 cups short-grain rice', '1 cup kimchi', '2 carrots', '1 cucumber'], 15, 20),
        ('Vegan Pho',                         'vegan-pho',                          'soups',       'Vietnamese', ['vegan'],              ['1 block tofu', '8 oz mushrooms', '1 lb rice noodles', '8 cups veggie stock', '1 piece charred ginger', '1 charred onion', '5 star anise', '1 cinnamon stick', '1 cup Thai basil'], 20, 60),
        ('Paneer Tikka Skewers',              'paneer-tikka-skewers',               'appetizers',  'Indian', ['vegetarian', 'gluten-free'], ['1 lb paneer', '1 cup Greek yogurt', '2 tbsp tikka masala paste', '1 lemon', '1 bell pepper', '1 red onion', '2 tbsp ghee'], 30, 15),
        ('Tofu Banh Mi',                      'tofu-banh-mi',                       'sandwiches',  'Vietnamese', ['vegan'],              ['1 block extra-firm tofu', '4 baguettes', '2 carrots (pickled)', '1 daikon (pickled)', '1 cucumber', '1 bunch cilantro', '2 jalapenos', '3 tbsp soy sauce'], 20, 15),
    ]),
]


def _seed_r7_chef_recipes(cat_by_slug, existing_slugs):
    added = 0
    for ci, (chef, cuisine_label, dishes) in enumerate(R7_CHEF_RECIPES):
        for di, dish in enumerate(dishes):
            (title, slug, cat_slug, cuisine, dietary, ings, prep, cook) = dish
            if slug in existing_slugs:
                continue
            cat = cat_by_slug.get(cat_slug) or cat_by_slug.get('main-dishes')
            existing_slugs.add(slug)
            total = max(1, prep + cook)
            ri = ci * 100 + di
            img_n = ((ri * 263 + 47) % IMAGE_POOL_SIZE) + 1
            feature_tags = [
                cat_slug, cuisine.lower().replace(' ', '-'), 'chef-special',
                f'chef-{_slugify(chef.replace("Chef ", ""))}',
            ] + list(dietary)
            gallery = [{
                'title': 'Chef walkthrough',
                'desc': f"Step-by-step photos of {title} by {chef}.",
                'images': [
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 269 + 7) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 271 + 23) % IMAGE_POOL_SIZE) + 1}.jpg",
                    f"{IMAGES_DIR_REL}/recipe_{((ri * 277 + 41) % IMAGE_POOL_SIZE) + 1}.jpg",
                ],
            }]
            created = MIRROR_REFERENCE_DATE - timedelta(days=(ri * 17 + 11) % 720)
            calories = 320 + (ri * 17) % 260
            avg_rating = round(4.4 + (ri % 7) * 0.05, 1)
            rec = Recipe(
                title=title, slug=slug,
                description=(
                    f"{chef}'s signature {title} — a {cuisine_label.lower()} classic "
                    "cooked with traditional regional technique and uncompromised seasoning."),
                category_id=cat.id if cat else None, cuisine=cuisine,
                image=f"{IMAGES_DIR_REL}/recipe_{img_n}.jpg",
                prep_time=_fmt_mins(prep), cook_time=_fmt_mins(cook),
                total_time=_fmt_mins(total),
                servings='4',
                calories=calories,
                ingredients_json=json.dumps(ings),
                instructions_json=json.dumps([
                    f"Read through the full {title} recipe once; chef-level dishes reward planning.",
                    f"Stage every ingredient at room temperature — important for {cuisine_label} flavor balance.",
                    f"Follow {chef}'s primary cooking step exactly; rushing it loses the regional character.",
                    f"Finish at the table with the traditional {cuisine_label} garnish in the ingredient list.",
                    "Serve immediately — leftovers are good the next day after the flavors meld.",
                ]),
                nutrition_json=json.dumps({'Calories': str(calories), 'Protein': '22g', 'Fat': '14g', 'Carbs': '34g'}),
                tags_json=json.dumps(feature_tags),
                gallery_json=json.dumps(gallery),
                is_featured=(ri % 13 == 0),
                is_editors_pick=(ri % 19 == 0),
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
# Public entry point — called from seed_data.seed_extended_catalog after R6.
# ===========================================================================

R7_SENTINEL_SLUG = 'bibimbap-mixed-rice-bowl'


def run_r7_polish(cat_by_slug):
    """R7 top-level. Returns a counts dict."""
    if (Recipe.query.filter_by(slug=R7_SENTINEL_SLUG).first()
            or Recipe.query.filter_by(slug='korean-regional-classic-waffles').first()):
        return {'skipped': True}

    counts = {}

    # 1) R7 chef recipes first so they're available for same-chef wiring.
    existing_recipe_slugs = {r.slug for r in Recipe.query.all()}
    counts['r7_chef'] = _seed_r7_chef_recipes(cat_by_slug, existing_recipe_slugs)
    db.session.flush()

    # 2) Variant passes — base = all Test Kitchen recipes that are not R6/R7
    # own variants. Subsample by step 8 -> ~1060 per pass × 4 passes
    # = ~4250 new -> 14054 + 4250 + 48 chef = ~18350 target.
    base_for_r7 = (Recipe.query
                   .filter(Recipe.author_name.like('%Test Kitchen%'))
                   .order_by(Recipe.id)
                   .all())
    base_for_r7 = [r for r in base_for_r7
                   if not _is_r6_variant(r.author_name)
                   and not _is_r7_variant(r.author_name)]
    base_for_r7 = base_for_r7[::8]
    print(f"[r7_seed] base_for_r7 size: {len(base_for_r7)}")

    counts['korean'] = _seed_korean_variants(cat_by_slug, base_for_r7, existing_recipe_slugs)
    db.session.flush()
    counts['thai'] = _seed_thai_variants(cat_by_slug, base_for_r7, existing_recipe_slugs)
    db.session.flush()
    counts['mexican_regional'] = _seed_mexican_regional_variants(cat_by_slug, base_for_r7, existing_recipe_slugs)
    db.session.flush()
    counts['vegetarian_by_protein'] = _seed_vegetarian_by_protein_variants(cat_by_slug, base_for_r7, existing_recipe_slugs)
    db.session.flush()

    return counts
