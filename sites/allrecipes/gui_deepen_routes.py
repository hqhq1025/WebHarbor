#!/usr/bin/env python3
"""GUI Deepen pass (2026-05-27): adds 25 new real-page templates to mirror
the genuine page surface of allrecipes.com — per-recipe sub-pages (photos,
reviews-by-star, troubleshooting, FDA nutrition label) plus catalog landing
pages (cuisine / diet / skill-level / equipment / meal-type / seasonal /
budget / time / dinner-fix / chef-bio / editorial).

All routes are pure GUI — no JSON endpoints. They read from the existing
Recipe / Review / Article / User tables and compute deterministic filtered
result sets so the byte-identical reset invariant is preserved.

Wired into ``app.py`` via ``from gui_deepen_routes import *`` at import
time; nothing in this file is called at seed-time.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict

from flask import abort, render_template, request
from sqlalchemy import or_, func

from app import app, db, Recipe, Review, User, Category


# ---------------------------------------------------------------------------
# Static taxonomies (kebab-case slug → display)
# ---------------------------------------------------------------------------
CUISINE_LANDING = [
    ("mediterranean", "Mediterranean",
     "Olive oil, sun-ripened tomato, fresh herbs and seafood are the heart "
     "of Mediterranean cooking — light, bright and rooted in the kitchens "
     "of Greece, southern Italy and the Levantine coast."),
    ("italian", "Italian",
     "From silky carbonara to slow-simmered Sunday gravy, Italian cooking "
     "is built on a short list of stunning ingredients treated with care."),
    ("mexican", "Mexican",
     "Charred chiles, masa, lime and avocado define a cuisine that ranges "
     "from breakfast chilaquiles to weekend birria."),
    ("chinese", "Chinese",
     "Stir-fries, dumplings, braises and steamed buns — eight regional "
     "styles, one of the world's most varied kitchens."),
    ("japanese", "Japanese",
     "Precise knife work, dashi-based broths and seasonal vegetables form "
     "the backbone of Japanese home cooking."),
    ("indian", "Indian",
     "Layered spice tadkas, dals, biryanis and tandoori-style roasts "
     "from across the subcontinent."),
    ("french", "French",
     "Classic mother sauces, butter-mounted pan reductions and patient "
     "braises — the technical foundation of much of Western cooking."),
    ("thai", "Thai",
     "Sour, sweet, salty and spicy in every bite — coconut curries, "
     "papaya salads and fragrant noodle soups."),
    ("korean", "Korean",
     "Banchan, fermented kimchis, gochujang-glazed grills and bibimbap "
     "bowls topped with a runny egg."),
    ("vietnamese", "Vietnamese",
     "Bright herb-laden bowls of pho, banh mi, fresh spring rolls and "
     "caramelised clay-pot braises."),
    ("brazilian", "Brazilian",
     "Feijoada bean stews, pao de queijo, churrasco-style grills and the "
     "tropical flavours of the Atlantic coast."),
    ("moroccan", "Moroccan",
     "Slow tagines, preserved lemons, ras-el-hanout spice blends and "
     "fluffy couscous served family-style."),
]
CUISINE_BY_SLUG = {s: (n, d) for s, n, d in CUISINE_LANDING}

DIET_LANDING = [
    ("vegan", "Vegan", "Plant-only — no meat, dairy or eggs."),
    ("vegetarian", "Vegetarian", "No meat or fish; dairy and eggs OK."),
    ("keto", "Keto", "Very-low-carb, high-fat to drive ketosis."),
    ("paleo", "Paleo", "Whole foods only — no grains, legumes or refined sugar."),
    ("gluten-free", "Gluten-Free", "No wheat, rye or barley — safe for celiac diets."),
    ("low-carb", "Low-Carb", "Carbs limited but not as strict as keto."),
    ("whole30", "Whole30", "A 30-day reset eliminating sugar, grains and legumes."),
    ("mediterranean-diet", "Mediterranean Diet",
     "Olive oil, fish, whole grains and vegetables — the longevity-tested template."),
]
DIET_BY_SLUG = {s: (n, d) for s, n, d in DIET_LANDING}

SKILL_LEVELS = [
    ("beginner", "Beginner",
     "Five-ingredient or fewer recipes with one cooking technique and "
     "clear stop points — perfect for a first cook."),
    ("intermediate", "Intermediate",
     "Recipes that combine two techniques (sear + braise, roast + sauce) "
     "and assume you can manage a heat schedule."),
    ("advanced", "Advanced",
     "Multi-component dishes with timing-critical steps — emulsions, "
     "laminated doughs, multi-day ferments."),
]
SKILL_BY_SLUG = {s: (n, d) for s, n, d in SKILL_LEVELS}

EQUIPMENT_LANDING = [
    ("air-fryer", "Air Fryer",
     "Convection at maximum velocity — crispy results without a deep-fry."),
    ("instant-pot", "Instant Pot",
     "Multicooker that pressure-cooks beans, braises and rice in a fraction "
     "of the stovetop time."),
    ("slow-cooker", "Slow Cooker",
     "Set-and-forget braises, stews and overnight oats."),
    ("cast-iron", "Cast Iron",
     "Deep, even heat retention — the right pan for searing, cornbread "
     "and crispy chicken thighs."),
    ("dutch-oven", "Dutch Oven",
     "Heavy enamelled pot for braises, bread and big-batch soups."),
    ("sheet-pan", "Sheet Pan",
     "One-pan oven dinners — roast a protein and vegetables on a single "
     "tray for minimal cleanup."),
]
EQUIPMENT_BY_SLUG = {s: (n, d) for s, n, d in EQUIPMENT_LANDING}

MEAL_TYPES = [
    ("breakfast", "Breakfast",
     "Pancakes, eggs, oats and breakfast bakes — fuel for the day."),
    ("lunch", "Lunch",
     "Bowls, sandwiches, salads and quick soups that travel well."),
    ("dinner", "Dinner",
     "The night's centerpiece — proteins, pastas, casseroles and bowls."),
    ("appetizer", "Appetizer",
     "Bite-sized openers and party platters for any gathering."),
    ("side", "Side",
     "Vegetables, grains and starches to round out a plate."),
    ("dessert", "Dessert",
     "Cakes, cookies, pies and the sweet ending every meal deserves."),
]
MEAL_TYPE_BY_SLUG = {s: (n, d) for s, n, d in MEAL_TYPES}

SEASONS = [
    ("spring", "Spring",
     "Asparagus, peas, ramps and rhubarb — the first burst of fresh "
     "produce after a long winter."),
    ("summer", "Summer",
     "Heirloom tomatoes, sweet corn, stone fruit and grilled everything."),
    ("fall", "Fall",
     "Squash, apples, root vegetables and slow-braised comfort food."),
    ("winter", "Winter",
     "Citrus, hardy greens, cured meats and steaming bowls of stew."),
]
SEASON_BY_SLUG = {s: (n, d) for s, n, d in SEASONS}

BUDGETS = [
    ("under-5", "Under $5 per Serving",
     "Lean, pantry-leaning recipes built around beans, eggs, rice and "
     "seasonal vegetables — feed a family for less than a coffee."),
    ("5-to-15", "$5 to $15 per Serving",
     "The everyday range — chicken, fish, pasta and family-style mains "
     "that don't strain a weekly grocery budget."),
    ("over-15", "Premium ($15+ per Serving)",
     "Special-occasion mains — steaks, prime cuts, lobster and dinner-"
     "party showstoppers."),
]
BUDGET_BY_SLUG = {s: (n, d) for s, n, d in BUDGETS}

TIME_BUCKETS = [
    ("under-15-min", "Under 15 Minutes", 0, 15,
     "Truly weeknight-fast recipes that hit the table before the rice "
     "finishes — sandwiches, quick stir-fries and salads."),
    ("under-30-min", "Under 30 Minutes", 0, 30,
     "The bulk of weeknight dinners — protein-and-vegetable plates that "
     "you can knock out in half an hour."),
    ("under-1-hr", "Under 1 Hour", 0, 60,
     "Recipes that go from prep to plate in under sixty minutes — "
     "perfect for the weekend dinner you actually plan."),
    ("over-1-hr", "Over 1 Hour", 60, 100000,
     "Slow-cooked braises, roast dinners and stews — recipes that "
     "reward a patient afternoon."),
]
TIME_BY_SLUG = {s: (n, lo, hi, d) for s, n, lo, hi, d in TIME_BUCKETS}

DINNER_FIX = [
    ("quick", "Quick Dinner Fix",
     "Fifteen-to-thirty-minute weeknight wins — the recipes that bail you "
     "out at 6:45pm on a Tuesday."),
    ("sheet-pan", "Sheet-Pan Dinner Fix",
     "One tray, one oven, one cleanup. Protein plus vegetables, roasted "
     "together at the same temperature."),
    ("one-pot", "One-Pot Dinner Fix",
     "Pastas, stews and skillet meals that finish in a single vessel — "
     "less to wash, more to enjoy."),
]
DINNER_FIX_BY_SLUG = {s: (n, d) for s, n, d in DINNER_FIX}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def _h(slug: str, mod: int) -> int:
    """Deterministic hash for slug → integer modulo mod. Used for budget /
    skill-level / troubleshooting Q&A so the same recipe always lands on
    the same bucket / answer."""
    return int(hashlib.md5(slug.encode()).hexdigest(), 16) % mod


def _recipe_or_404(slug: str) -> Recipe:
    r = Recipe.query.filter_by(slug=slug).first()
    if not r:
        abort(404)
    return r


def _paginate(query, page: int, per_page: int = 12):
    return query.paginate(page=page, per_page=per_page, error_out=False)


def _ft_clause(slug: str):
    """SQL LIKE clause that finds a kebab-case tag inside the JSON-encoded
    ``feature_tags`` text. The seed always stores tags as JSON-encoded
    string lists, so the literal `"<tag>"` substring is reliable."""
    needle = f'"{slug}"'
    return Recipe.feature_tags.like(f"%{needle}%")


def _recipes_in_cuisine(slug: str):
    name, _ = CUISINE_BY_SLUG[slug]
    return Recipe.query.filter(
        or_(
            func.lower(Recipe.cuisine) == name.lower(),
            _ft_clause(f"cuisine-{slug}"),
            _ft_clause(slug),
        )
    )


def _recipes_in_diet(slug: str):
    target = slug
    if slug == "mediterranean-diet":
        # Mediterranean-diet shares its tag set with the Mediterranean cuisine.
        return Recipe.query.filter(
            or_(
                func.lower(Recipe.cuisine) == "mediterranean",
                _ft_clause("mediterranean"),
                _ft_clause("mediterranean-diet"),
            )
        )
    return Recipe.query.filter(
        or_(
            Recipe.dietary_tags_json.like(f'%"{target}"%'),
            _ft_clause(target),
        )
    )


def _recipes_for_equipment(slug: str):
    """Equipment match: feature_tags has 'equipment-<slug>' OR cooking_method
    matches a known synonym."""
    synonyms = {
        "air-fryer": ["air fryer", "air-fryer"],
        "instant-pot": ["instant pot", "pressure cooker"],
        "slow-cooker": ["slow cooker", "slow-cooker"],
        "cast-iron": ["cast iron", "skillet"],
        "dutch-oven": ["dutch oven", "braised"],
        "sheet-pan": ["sheet pan", "sheet-pan", "roasted"],
    }
    methods = synonyms.get(slug, [])
    clauses = [_ft_clause(f"equipment-{slug}"), _ft_clause(slug)]
    for m in methods:
        clauses.append(func.lower(Recipe.cooking_method) == m.lower())
    return Recipe.query.filter(or_(*clauses))


def _recipes_for_meal(slug: str):
    return Recipe.query.filter(
        or_(
            func.lower(Recipe.meal_type) == slug,
            func.lower(Recipe.dish_type) == slug,
            _ft_clause(slug),
        )
    )


def _recipes_for_season(slug: str):
    # Treat fall and autumn as synonyms.
    if slug == "fall":
        return Recipe.query.filter(
            or_(
                func.lower(Recipe.season) == "fall",
                func.lower(Recipe.season) == "autumn",
                _ft_clause("fall"),
                _ft_clause("autumn"),
            )
        )
    return Recipe.query.filter(
        or_(
            func.lower(Recipe.season) == slug,
            _ft_clause(slug),
        )
    )


def _recipes_for_budget(slug: str):
    """Budget bucket determined deterministically from slug-hash on each
    recipe. We split the catalog into roughly equal buckets so any budget
    landing page has hundreds of items."""
    bucket = {"under-5": 0, "5-to-15": 1, "over-15": 2}[slug]
    all_recipes = Recipe.query.all()
    return [r for r in all_recipes if _h(r.slug, 3) == bucket]


def _recipes_for_time(slug: str):
    lo = TIME_BY_SLUG[slug][1]
    hi = TIME_BY_SLUG[slug][2]
    return Recipe.query.filter(
        Recipe.total_time_mins >= lo,
        Recipe.total_time_mins < hi,
    )


def _recipes_for_dinner_fix(slug: str):
    if slug == "quick":
        return Recipe.query.filter(
            or_(
                Recipe.total_time_mins.between(1, 30),
                _ft_clause("quick"),
                _ft_clause("under-30-min"),
            ),
            or_(
                func.lower(Recipe.meal_type) == "dinner",
                _ft_clause("dinner"),
                func.lower(Recipe.dish_type) == "main",
            ),
        )
    if slug == "sheet-pan":
        return Recipe.query.filter(_ft_clause("sheet-pan"))
    if slug == "one-pot":
        return Recipe.query.filter(_ft_clause("one-pot"))
    return Recipe.query.filter(Recipe.id < 0)  # empty


def _recipes_for_skill(slug: str):
    """Skill bucket: deterministic from recipe.id so the same recipe is
    always the same level. We blend in real signals — short ingredient
    count and total_time push toward beginner; long total_time or large
    ingredient_count push toward advanced."""
    bucket = {"beginner": 0, "intermediate": 1, "advanced": 2}[slug]
    out = []
    for r in Recipe.query.all():
        ic = r.ingredient_count or 5
        tt = r.total_time_mins or 30
        if ic <= 6 and tt <= 30:
            level = 0
        elif ic >= 12 or tt >= 90:
            level = 2
        else:
            level = 1
        # Mix in slug-hash to spread evenly when a recipe sits at a
        # boundary (otherwise the buckets are unbalanced).
        if level == bucket or (level == 1 and _h(r.slug, 4) == bucket):
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# Recipe sub-page: photos
# ---------------------------------------------------------------------------
@app.route("/recipe/<slug>/photos")
def gui_recipe_photos(slug):
    r = _recipe_or_404(slug)
    try:
        gallery = json.loads(r.gallery_json or "[]") or []
    except (TypeError, ValueError):
        gallery = []
    # Expand: if gallery is empty fall back to the hero image so the page
    # still has something to render — the user-typed query "show photos for X"
    # should never 404.
    photos = []
    for section in gallery:
        for img in section.get("images", []):
            photos.append({
                "url": img,
                "caption": section.get("title") or "Step photo",
            })
    if not photos and r.image:
        photos.append({"url": r.image, "caption": "Hero photo"})
    return render_template(
        "recipe_photos.html",
        recipe=r,
        photos=photos,
        photo_count=len(photos),
        page_title=f"Photos — {r.title}",
    )


# ---------------------------------------------------------------------------
# Recipe sub-page: reviews-by-star
# ---------------------------------------------------------------------------
@app.route("/recipe/<slug>/reviews")
def gui_recipe_reviews(slug):
    r = _recipe_or_404(slug)
    try:
        star_filter = int(request.args.get("stars", "0"))
    except ValueError:
        star_filter = 0
    sort = request.args.get("sort", "recent")  # recent | top
    all_reviews = Review.query.filter_by(recipe_id=r.id).all()
    distribution = Counter(rv.rating for rv in all_reviews)
    filtered = (
        [rv for rv in all_reviews if rv.rating == star_filter]
        if 1 <= star_filter <= 5 else list(all_reviews)
    )
    if sort == "top":
        filtered.sort(key=lambda rv: (-rv.rating, rv.id))
    else:
        filtered.sort(key=lambda rv: -rv.id)
    # Hydrate author display names
    user_ids = {rv.user_id for rv in filtered}
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    return render_template(
        "recipe_reviews.html",
        recipe=r,
        reviews=filtered[:60],
        total=len(all_reviews),
        showing=len(filtered[:60]),
        distribution={i: distribution.get(i, 0) for i in range(1, 6)},
        star_filter=star_filter,
        sort=sort,
        users=users,
        page_title=f"Reviews — {r.title}",
    )


# ---------------------------------------------------------------------------
# Recipe sub-page: troubleshooting Q&A
# ---------------------------------------------------------------------------
TROUBLESHOOTING_LIBRARY = [
    ("Why did my dish turn out dry?",
     "Dryness almost always traces back to over-cooking the protein or "
     "starch. Pull the dish off the heat 5°F (3°C) below your target and "
     "let carry-over cooking finish the job. For braises, make sure the "
     "liquid covers at least two-thirds of the meat for the first hour."),
    ("Why is my sauce too thin?",
     "A thin sauce is almost always a reduction problem. Move the pan to "
     "the largest burner and crank the heat to medium-high — surface "
     "area is what drives evaporation. A small slurry of cornstarch (1 "
     "tsp in 2 tsp cold water) is the emergency fix."),
    ("My batter looks lumpy — did I ruin it?",
     "Lumpy batter is fine for pancakes and quick breads — over-mixing "
     "develops gluten and makes them tough. For crepes and tempura, "
     "strain the batter through a sieve."),
    ("Why didn't my dough rise?",
     "Either the yeast was dead (test by proofing a teaspoon in warm "
     "water with sugar — should foam within 10 minutes) or the dough was "
     "too cold. Move it to a warm 75-80°F (24-27°C) spot and give it "
     "another hour."),
    ("Can I make this ahead?",
     "Most braises, soups and stews actually improve overnight in the "
     "fridge — flavors marry. Sear-and-roast preparations are best the "
     "day of. Reheat braises in a 325°F (160°C) oven covered, not on the "
     "stovetop where the bottom scorches."),
    ("How do I store leftovers?",
     "Cool to room temperature within 2 hours, store in shallow airtight "
     "containers for fastest cooling, and refrigerate up to 3-4 days. "
     "Freeze portions you won't eat within that window."),
    ("Can I freeze this?",
     "Yes for braises, soups, casseroles and most baked goods. No for "
     "dishes with crisp toppings (gratins) or fresh herb garnishes — add "
     "those after thawing. Wrap tightly to avoid freezer burn and label "
     "with the date."),
    ("Why is the texture grainy?",
     "Grainy custards and cheese sauces almost always mean too-high "
     "heat. Pull the pan off the burner, whisk in a splash of cold "
     "cream, and rebuild gently over low heat. For grainy ganache, warm "
     "and re-emulsify with a hand blender."),
    ("My oil is foaming — what's wrong?",
     "Water content in the food has hit the hot oil. Pat ingredients dry "
     "before frying and never crowd the pan. If foam appears mid-fry, "
     "remove the food, let the oil settle, and resume in smaller batches."),
    ("Why is my rice mushy?",
     "Too much water or too much agitation. Use a 1:1.5 rice-to-water "
     "ratio for long-grain white, cover tightly and don't peek for the "
     "first 15 minutes. Fluff with a fork only after a 10-minute rest."),
    ("Can I substitute the main ingredient?",
     "Most proteins swap one-for-one as long as the cooking time is "
     "adjusted (chicken thighs cook 5 minutes longer than breasts). For "
     "vegetarian swaps, replace each pound of meat with 8 oz of firm "
     "tofu or 1.5 cups of cooked beans plus 2 tbsp of soy sauce for umami."),
    ("How spicy is this recipe?",
     "Mild by default — about a 2/10 if you're calibrating against a "
     "vindaloo. Halve or omit any fresh chile and skip cayenne for a "
     "kid-friendly version; double both for the heat-seekers in your house."),
]


@app.route("/recipe/<slug>/troubleshooting")
def gui_recipe_troubleshooting(slug):
    r = _recipe_or_404(slug)
    # Pick a deterministic slice of 6 Q&As so each recipe page is unique
    # but reproducible.
    base = _h(r.slug, len(TROUBLESHOOTING_LIBRARY))
    indices = [(base + 2 * i) % len(TROUBLESHOOTING_LIBRARY) for i in range(6)]
    qas = [TROUBLESHOOTING_LIBRARY[i] for i in indices]
    return render_template(
        "recipe_troubleshooting.html",
        recipe=r,
        qas=qas,
        page_title=f"Troubleshooting — {r.title}",
    )


# ---------------------------------------------------------------------------
# Recipe sub-page: FDA-style nutrition label
# ---------------------------------------------------------------------------
@app.route("/recipe/<slug>/nutrition-label")
def gui_recipe_nutrition_label(slug):
    r = _recipe_or_404(slug)
    h = _h(r.slug, 1_000_000)
    cal = r.calories or 0
    derived = {
        "serving_size": "1 serving",
        "servings": r.servings or "6",
        "calories": cal,
        "total_fat_g": 8 + (h * 3) % 24,
        "sat_fat_g": 3 + (h * 5) % 9,
        "trans_fat_g": 0,
        "cholesterol_mg": 30 + (h * 19) % 100,
        "sodium_mg": 200 + (h * 17) % 500,
        "total_carbs_g": 20 + (h * 7) % 40,
        "fiber_g": 2 + (h * 13) % 8,
        "sugar_g": 4 + (h * 11) % 16,
        "added_sugar_g": 1 + (h * 23) % 8,
        "protein_g": 10 + h % 30,
        "vit_d_mcg": 1 + (h * 29) % 5,
        "calcium_mg": 40 + (h * 29) % 200,
        "iron_mg": 1 + (h * 31) % 6,
        "potassium_mg": 200 + (h * 23) % 400,
    }
    return render_template(
        "nutrition_label_fda.html",
        recipe=r,
        n=derived,
        page_title=f"Nutrition label — {r.title}",
    )


# ---------------------------------------------------------------------------
# Cuisine
# ---------------------------------------------------------------------------
@app.route("/cuisine")
def gui_cuisine_hub():
    counts = {}
    for slug, _name, _desc in CUISINE_LANDING:
        counts[slug] = _recipes_in_cuisine(slug).count()
    return render_template(
        "cuisine_hub.html",
        landing=CUISINE_LANDING,
        counts=counts,
        page_title="Recipes by Cuisine",
    )


@app.route("/cuisine/<slug>")
def gui_cuisine_detail(slug):
    if slug not in CUISINE_BY_SLUG:
        abort(404)
    name, desc = CUISINE_BY_SLUG[slug]
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = _recipes_in_cuisine(slug).order_by(Recipe.avg_rating.desc(), Recipe.id.asc())
    paged = _paginate(q, page)
    return render_template(
        "cuisine_detail.html",
        slug=slug,
        name=name,
        description=desc,
        recipes=paged,
        siblings=CUISINE_LANDING,
        page_title=f"{name} Recipes",
    )


# ---------------------------------------------------------------------------
# Skill level
# ---------------------------------------------------------------------------
@app.route("/skill-level")
def gui_skill_level_hub():
    counts = {}
    for slug, _n, _d in SKILL_LEVELS:
        counts[slug] = len(_recipes_for_skill(slug))
    return render_template(
        "skill_level_hub.html",
        landing=SKILL_LEVELS,
        counts=counts,
        page_title="Recipes by Skill Level",
    )


@app.route("/skill-level/<slug>")
def gui_skill_level_detail(slug):
    if slug not in SKILL_BY_SLUG:
        abort(404)
    name, desc = SKILL_BY_SLUG[slug]
    items = _recipes_for_skill(slug)
    items.sort(key=lambda r: (-r.avg_rating, r.id))
    page = max(int(request.args.get("page", 1) or 1), 1)
    per_page = 12
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "skill_level_detail.html",
        slug=slug,
        name=name,
        description=desc,
        items=page_items,
        total=total,
        page=page,
        pages=pages,
        siblings=SKILL_LEVELS,
        page_title=f"{name} Recipes",
    )


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------
@app.route("/equipment")
def gui_equipment_hub():
    counts = {}
    for slug, _n, _d in EQUIPMENT_LANDING:
        counts[slug] = _recipes_for_equipment(slug).count()
    return render_template(
        "equipment_hub.html",
        landing=EQUIPMENT_LANDING,
        counts=counts,
        page_title="Recipes by Equipment",
    )


@app.route("/equipment/<slug>")
def gui_equipment_detail(slug):
    if slug not in EQUIPMENT_BY_SLUG:
        abort(404)
    name, desc = EQUIPMENT_BY_SLUG[slug]
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = _recipes_for_equipment(slug).order_by(Recipe.avg_rating.desc(), Recipe.id.asc())
    paged = _paginate(q, page)
    return render_template(
        "equipment_detail.html",
        slug=slug,
        name=name,
        description=desc,
        recipes=paged,
        siblings=EQUIPMENT_LANDING,
        page_title=f"{name} Recipes",
    )


# ---------------------------------------------------------------------------
# Meal type
# ---------------------------------------------------------------------------
@app.route("/meal-type")
def gui_meal_type_hub():
    counts = {}
    for slug, _n, _d in MEAL_TYPES:
        counts[slug] = _recipes_for_meal(slug).count()
    return render_template(
        "meal_type_hub.html",
        landing=MEAL_TYPES,
        counts=counts,
        page_title="Recipes by Meal Type",
    )


@app.route("/meal-type/<slug>")
def gui_meal_type_detail(slug):
    if slug not in MEAL_TYPE_BY_SLUG:
        abort(404)
    name, desc = MEAL_TYPE_BY_SLUG[slug]
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = _recipes_for_meal(slug).order_by(Recipe.avg_rating.desc(), Recipe.id.asc())
    paged = _paginate(q, page)
    return render_template(
        "meal_type_detail.html",
        slug=slug,
        name=name,
        description=desc,
        recipes=paged,
        siblings=MEAL_TYPES,
        page_title=f"{name} Recipes",
    )


# ---------------------------------------------------------------------------
# Featured seasonal
# ---------------------------------------------------------------------------
@app.route("/featured/seasonal")
def gui_seasonal_hub():
    counts = {}
    for slug, _n, _d in SEASONS:
        counts[slug] = _recipes_for_season(slug).count()
    return render_template(
        "seasonal_hub.html",
        landing=SEASONS,
        counts=counts,
        page_title="Seasonal Featured Recipes",
    )


@app.route("/featured/seasonal/<slug>")
def gui_seasonal_detail(slug):
    if slug not in SEASON_BY_SLUG:
        abort(404)
    name, desc = SEASON_BY_SLUG[slug]
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = _recipes_for_season(slug).order_by(Recipe.avg_rating.desc(), Recipe.id.asc())
    paged = _paginate(q, page)
    return render_template(
        "seasonal_detail.html",
        slug=slug,
        name=name,
        description=desc,
        recipes=paged,
        siblings=SEASONS,
        page_title=f"{name} Recipes",
    )


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------
@app.route("/budget")
def gui_budget_hub():
    counts = {}
    for slug, _n, _d in BUDGETS:
        counts[slug] = len(_recipes_for_budget(slug))
    return render_template(
        "budget_hub.html",
        landing=BUDGETS,
        counts=counts,
        page_title="Recipes by Budget",
    )


@app.route("/budget/<slug>")
def gui_budget_detail(slug):
    if slug not in BUDGET_BY_SLUG:
        abort(404)
    name, desc = BUDGET_BY_SLUG[slug]
    items = _recipes_for_budget(slug)
    items.sort(key=lambda r: (-r.avg_rating, r.id))
    page = max(int(request.args.get("page", 1) or 1), 1)
    per_page = 12
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "budget_detail.html",
        slug=slug,
        name=name,
        description=desc,
        items=page_items,
        total=total,
        page=page,
        pages=pages,
        siblings=BUDGETS,
        page_title=f"{name}",
    )


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------
@app.route("/time")
def gui_time_hub():
    counts = {}
    for slug, _n, _lo, _hi, _d in TIME_BUCKETS:
        counts[slug] = _recipes_for_time(slug).count()
    return render_template(
        "time_hub.html",
        landing=TIME_BUCKETS,
        counts=counts,
        page_title="Recipes by Time",
    )


@app.route("/time/<slug>")
def gui_time_detail(slug):
    if slug not in TIME_BY_SLUG:
        abort(404)
    name, lo, hi, desc = TIME_BY_SLUG[slug]
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = _recipes_for_time(slug).order_by(Recipe.total_time_mins.asc(), Recipe.id.asc())
    paged = _paginate(q, page)
    return render_template(
        "time_detail.html",
        slug=slug,
        name=name,
        description=desc,
        recipes=paged,
        siblings=TIME_BUCKETS,
        page_title=f"{name} Recipes",
    )


# ---------------------------------------------------------------------------
# Dinner-fix
# ---------------------------------------------------------------------------
@app.route("/dinner-fix")
def gui_dinner_fix_hub():
    counts = {}
    for slug, _n, _d in DINNER_FIX:
        counts[slug] = _recipes_for_dinner_fix(slug).count()
    return render_template(
        "dinner_fix_hub.html",
        landing=DINNER_FIX,
        counts=counts,
        page_title="Dinner Fix",
    )


@app.route("/dinner-fix/<slug>")
def gui_dinner_fix_detail(slug):
    if slug not in DINNER_FIX_BY_SLUG:
        abort(404)
    name, desc = DINNER_FIX_BY_SLUG[slug]
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = _recipes_for_dinner_fix(slug).order_by(Recipe.avg_rating.desc(), Recipe.id.asc())
    paged = _paginate(q, page)
    return render_template(
        "dinner_fix_detail.html",
        slug=slug,
        name=name,
        description=desc,
        recipes=paged,
        siblings=DINNER_FIX,
        page_title=f"{name}",
    )


# ---------------------------------------------------------------------------
# Chef bio
# ---------------------------------------------------------------------------
def _chef_directory():
    """Return list of (slug, display_name, recipe_count) for chefs that
    have at least 6 recipes. Cached at module level for cheap re-use."""
    if _chef_directory._cache is not None:
        return _chef_directory._cache
    rows = (db.session.query(Recipe.author_name, func.count(Recipe.id))
            .filter(Recipe.author_name.isnot(None), Recipe.author_name != "")
            .group_by(Recipe.author_name)
            .all())
    chefs = []
    seen = set()
    for name, cnt in rows:
        if cnt < 6:
            continue
        slug = _slugify(name)
        if slug in seen:
            continue
        seen.add(slug)
        chefs.append((slug, name, cnt))
    chefs.sort(key=lambda r: -r[2])
    _chef_directory._cache = chefs[:48]
    return _chef_directory._cache
_chef_directory._cache = None  # type: ignore[attr-defined]


CHEF_BIO_TEMPLATES = [
    ("Test-kitchen specialist focused on {topic}. Joined Allrecipes in 2019 and "
     "has contributed over {count} recipes."),
    ("Cookbook author and food stylist who pivoted from restaurant kitchens to "
     "developing approachable home recipes. Specializes in {topic}."),
    ("Former line cook turned recipe developer. Known for crystal-clear "
     "instructions and {topic} that work the first time."),
    ("Food writer and James-Beard-nominated home-cook educator. Spent five "
     "years documenting {topic} for the Allrecipes test kitchen."),
]


@app.route("/chef-bio")
def gui_chef_bio_hub():
    chefs = _chef_directory()
    return render_template(
        "chef_bio_hub.html",
        chefs=chefs,
        total=len(chefs),
        page_title="Allrecipes Chefs & Contributors",
    )


@app.route("/chef-bio/<slug>")
def gui_chef_bio_detail(slug):
    chefs = {s: (n, c) for s, n, c in _chef_directory()}
    if slug not in chefs:
        abort(404)
    name, count = chefs[slug]
    recipes = (Recipe.query.filter_by(author_name=name)
               .order_by(Recipe.avg_rating.desc(), Recipe.id.asc())
               .limit(36).all())
    # Topic = main_ingredient or cuisine most common in this chef's recipes
    topic_counter = Counter()
    for r in recipes:
        for k in (r.cuisine, r.main_ingredient, r.meal_type, r.dish_type):
            if k:
                topic_counter[k.lower()] += 1
    top_topics = [t for t, _c in topic_counter.most_common(3)]
    topic_phrase = ", ".join(top_topics) if top_topics else "everyday cooking"
    bio_idx = _h(slug, len(CHEF_BIO_TEMPLATES))
    bio = CHEF_BIO_TEMPLATES[bio_idx].format(topic=topic_phrase, count=count)
    location_pool = ["Seattle, WA", "Brooklyn, NY", "Austin, TX", "Portland, OR",
                     "Asheville, NC", "Oakland, CA", "Chicago, IL",
                     "Boulder, CO", "Minneapolis, MN", "Atlanta, GA"]
    join_year = 2016 + _h(slug, 9)
    location = location_pool[_h(slug, len(location_pool))]
    # Avg rating across this chef's recipes
    avg = round(sum(r.avg_rating for r in recipes) / max(len(recipes), 1), 2)
    return render_template(
        "chef_bio_detail.html",
        slug=slug,
        name=name,
        bio=bio,
        recipes=recipes,
        recipe_count=count,
        avg_rating=avg,
        location=location,
        join_year=join_year,
        top_topics=top_topics,
        page_title=f"Chef Profile — {name}",
    )


# ---------------------------------------------------------------------------
# Editorial / article surface
# ---------------------------------------------------------------------------
@app.route("/editorial")
def gui_editorial_hub():
    from sqlalchemy import text as _text
    rows = db.session.execute(_text(
        "SELECT slug, title, category, author_name, excerpt, hero_image, "
        "read_time_mins, view_count FROM article "
        "ORDER BY view_count DESC"
    )).fetchall()
    return render_template(
        "editorial_hub.html",
        articles=rows,
        total=len(rows),
        page_title="Allrecipes Editorial",
    )


@app.route("/editorial/<slug>")
def gui_editorial_detail(slug):
    from sqlalchemy import text as _text
    row = db.session.execute(_text(
        "SELECT slug, title, category, author_name, excerpt, body_json, "
        "hero_image, read_time_mins, view_count, related_recipes_json, tags_json "
        "FROM article WHERE slug = :s"
    ), {"s": slug}).fetchone()
    if not row:
        abort(404)
    try:
        body = json.loads(row.body_json or "[]")
    except (TypeError, ValueError):
        body = []
    try:
        related_titles = json.loads(row.related_recipes_json or "[]")
    except (TypeError, ValueError):
        related_titles = []
    try:
        tags = json.loads(row.tags_json or "[]")
    except (TypeError, ValueError):
        tags = []
    related = []
    for t in related_titles[:6]:
        r = Recipe.query.filter(Recipe.title.ilike(f"%{t}%")).first()
        if r:
            related.append(r)
    return render_template(
        "editorial_detail.html",
        slug=row.slug,
        title=row.title,
        category=row.category,
        author=row.author_name,
        excerpt=row.excerpt,
        body=body,
        hero_image=row.hero_image,
        read_time=row.read_time_mins,
        view_count=row.view_count,
        tags=tags,
        related=related,
        page_title=row.title,
    )


# ---------------------------------------------------------------------------
# Diet compare
# ---------------------------------------------------------------------------
DIET_COMPARE_TABLE = [
    # (slug, name, carbs, fat, protein, hallmark, primary_avoids)
    ("vegan", "Vegan", "varies", "varies", "moderate",
     "Plant-only", "all animal products"),
    ("vegetarian", "Vegetarian", "varies", "varies", "moderate",
     "No meat or fish", "meat, poultry, fish"),
    ("keto", "Keto", "5-10%", "70-80%", "20-25%",
     "Very-low-carb ketosis", "grains, sugar, most fruit"),
    ("paleo", "Paleo", "30%", "40%", "30%",
     "Pre-agricultural whole foods", "grains, legumes, dairy"),
    ("gluten-free", "Gluten-Free", "varies", "varies", "varies",
     "Celiac-safe", "wheat, rye, barley"),
    ("low-carb", "Low-Carb", "<25%", "40%", "30%",
     "Reduced carbohydrate", "refined carbs, sugar"),
    ("whole30", "Whole30", "varies", "varies", "varies",
     "30-day elimination", "added sugar, grains, legumes, dairy"),
    ("mediterranean-diet", "Mediterranean Diet", "45%", "35%", "20%",
     "Olive oil & fish", "red meat (limited)"),
]


@app.route("/diet/compare")
def gui_diet_compare():
    rows = []
    for slug, name, carbs, fat, protein, hallmark, avoids in DIET_COMPARE_TABLE:
        cnt = _recipes_in_diet(slug).count()
        rows.append({
            "slug": slug,
            "name": name,
            "carbs": carbs,
            "fat": fat,
            "protein": protein,
            "hallmark": hallmark,
            "avoids": avoids,
            "recipe_count": cnt,
        })
    return render_template(
        "diet_compare.html",
        rows=rows,
        page_title="Compare Diets",
    )


__all__ = [
    "CUISINE_LANDING", "DIET_LANDING", "SKILL_LEVELS", "EQUIPMENT_LANDING",
    "MEAL_TYPES", "SEASONS", "BUDGETS", "TIME_BUCKETS", "DINNER_FIX",
]
