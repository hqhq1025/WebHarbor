#!/usr/bin/env python3
"""Generate 30+ GUI tasks per new page family added by the GUI-deepen pass.
Appends to ``tasks.jsonl`` with deterministic IDs in the
``Allrecipes--gui_<page>_<NNN>`` format. Idempotent: re-running won't
duplicate entries because we check existing IDs first."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from app import app, db, Recipe  # noqa: E402
from gui_deepen_routes import (  # noqa: E402
    CUISINE_LANDING, SKILL_LEVELS, EQUIPMENT_LANDING, MEAL_TYPES, SEASONS,
    BUDGETS, TIME_BUCKETS, DINNER_FIX, DIET_COMPARE_TABLE,
    _chef_directory, _recipes_in_cuisine, _recipes_for_skill,
    _recipes_for_equipment, _recipes_for_meal, _recipes_for_season,
    _recipes_for_budget, _recipes_for_time, _recipes_for_dinner_fix,
)

TASKS_FILE = os.path.join(ROOT, "tasks.jsonl")
WEB = "http://localhost:40000/"
UPSTREAM = "https://www.allrecipes.com/"


def _existing_ids():
    if not os.path.exists(TASKS_FILE):
        return set()
    out = set()
    with open(TASKS_FILE) as f:
        for line in f:
            try:
                out.add(json.loads(line)["id"])
            except (ValueError, KeyError):
                pass
    return out


def _task(_id, task_type, ques):
    return {
        "web_name": "Allrecipes",
        "id": _id,
        "task_type": task_type,
        "ques": ques,
        "web": WEB,
        "upstream_url": UPSTREAM,
    }


def _seed_recipes(query_fn, n=3, min_reviews=10):
    """Pick first N recipes (deterministic order) from a query-builder
    callable. Returns a list of Recipe rows."""
    res = query_fn()
    if hasattr(res, "order_by"):
        rows = res.order_by(Recipe.review_count.desc(), Recipe.id.asc()).limit(n).all()
    else:
        rows = sorted(res, key=lambda r: (-r.review_count, r.id))[:n]
    return rows


def gen_recipe_subpage_tasks():
    """30+ tasks across photos / reviews / troubleshooting / nutrition-label."""
    out = []
    # Pick 24 deterministic recipes spread across the catalog.
    picks = (Recipe.query
             .filter(Recipe.review_count > 20)
             .order_by(Recipe.id.asc())
             .limit(40).all())[:24]
    if not picks:
        picks = Recipe.query.order_by(Recipe.id.asc()).limit(24).all()

    family_seq = ["photos", "reviews", "troubleshooting", "nutrition-label"]
    i = 0
    for fam in family_seq:
        for r in picks[:8]:
            i += 1
            tid = f"Allrecipes--gui_recipe_{fam.replace('-', '_')}_{i:03d}"
            if fam == "photos":
                q = (f"Open the photo gallery for the recipe '{r.title}' "
                     f"and report how many photos appear on the gallery page.")
            elif fam == "reviews":
                q = (f"Go to the reviews tab for '{r.title}', filter by 5-star "
                     f"reviews only, and copy the title of the first review shown.")
            elif fam == "troubleshooting":
                q = (f"Open the troubleshooting Q&A page for '{r.title}' and "
                     f"summarize the answer to the first question listed.")
            else:  # nutrition-label
                q = (f"Open the FDA-style nutrition label for '{r.title}' and "
                     f"report the calories per serving.")
            out.append(_task(tid, f"gui-recipe-{fam}", q))
    # Add disambiguation/star-filter tasks for variety to hit 30+.
    extra_recipes = picks[8:16]
    for j, r in enumerate(extra_recipes, 1):
        out.append(_task(
            f"Allrecipes--gui_recipe_reviews_filter_{j:03d}",
            "gui-recipe-reviews",
            f"On the reviews page for '{r.title}', filter the reviews to "
            f"1-star only and count how many reviews are shown."
        ))
        out.append(_task(
            f"Allrecipes--gui_recipe_reviews_sort_{j:03d}",
            "gui-recipe-reviews",
            f"On the reviews page for '{r.title}', switch the sort order to "
            f"'Top-rated' and copy the title of the first review."
        ))
    return out


def gen_cuisine_tasks():
    out = []
    counter = 0
    for slug, name, _desc in CUISINE_LANDING:
        counter += 1
        out.append(_task(
            f"Allrecipes--gui_cuisine_hub_{counter:03d}",
            "gui-cuisine-hub",
            f"From the Cuisines hub, click '{name}' and report the total "
            f"number of recipes listed in that cuisine."
        ))
        out.append(_task(
            f"Allrecipes--gui_cuisine_top_{counter:03d}",
            "gui-cuisine-detail",
            f"Open the {name} cuisine page and copy the title of the "
            f"first (top-rated) recipe shown."
        ))
        # Drill into one recipe per cuisine for variety
        rows = _seed_recipes(lambda s=slug: _recipes_in_cuisine(s), n=1)
        if rows:
            r = rows[0]
            out.append(_task(
                f"Allrecipes--gui_cuisine_recipe_{counter:03d}",
                "gui-cuisine-detail",
                f"From the {name} cuisine page, navigate to the recipe "
                f"'{r.title}' and report its total time."
            ))
    # Round out to 36 = 12*3
    return out


def gen_skill_level_tasks():
    out = []
    counter = 0
    for slug, name, _desc in SKILL_LEVELS:
        for k in range(10):
            counter += 1
            if k == 0:
                q = f"Open /skill-level/{slug} and report how many {name} recipes are listed in total."
            elif k == 1:
                q = f"From the Skill Level hub, click '{name}' and copy the title of the first recipe shown."
            elif k == 2:
                q = f"From /skill-level/{slug}, navigate to the second recipe in the listing and report its average rating."
            elif k == 3:
                q = f"On the {name} skill-level page, count the recipes whose card shows a total time under 30 minutes (page 1 only)."
            elif k == 4:
                q = f"From the {name} skill-level page, click any recipe with a 5-star rating and copy its title."
            elif k == 5:
                q = f"Open the {name} skill-level page, go to page 2, and copy the title of the first recipe on that page."
            elif k == 6:
                q = f"From /skill-level/{slug}, find a recipe whose calories per serving are under 400 and copy its title."
            elif k == 7:
                q = f"From the Skill Level hub, identify which level has the most recipes and report the level name."
            elif k == 8:
                q = f"On /skill-level/{slug}, click the first recipe and report its number of reviews."
            else:
                q = f"From /skill-level/{slug}, copy the description text shown in the page hero."
            out.append(_task(f"Allrecipes--gui_skill_level_{counter:03d}", "gui-skill-level", q))
    return out


def gen_equipment_tasks():
    out = []
    counter = 0
    for slug, name, _desc in EQUIPMENT_LANDING:
        for k in range(6):
            counter += 1
            if k == 0:
                q = f"From the Equipment hub, click '{name}' and report the total number of recipes listed."
            elif k == 1:
                q = f"Open /equipment/{slug} and copy the title of the first recipe shown."
            elif k == 2:
                q = f"From /equipment/{slug}, navigate to the second recipe and report its prep time."
            elif k == 3:
                q = f"On /equipment/{slug}, go to page 2 and copy the title of the third recipe on that page."
            elif k == 4:
                q = f"From the {name} page, find a recipe with at least 50 reviews and copy its title."
            else:
                q = f"On the {name} page, identify a recipe under 30 minutes total time and copy its title."
            out.append(_task(f"Allrecipes--gui_equipment_{counter:03d}", "gui-equipment", q))
    return out


def gen_meal_type_tasks():
    out = []
    counter = 0
    for slug, name, _desc in MEAL_TYPES:
        for k in range(6):
            counter += 1
            if k == 0:
                q = f"From the Meal Type hub, click '{name}' and report the total number of recipes in that meal type."
            elif k == 1:
                q = f"Open /meal-type/{slug} and copy the title of the first recipe shown."
            elif k == 2:
                q = f"On /meal-type/{slug}, find a recipe with an average rating of at least 4.5 stars and copy its title."
            elif k == 3:
                q = f"From the {name} page, click any recipe and report its calorie count per serving."
            elif k == 4:
                q = f"On /meal-type/{slug}, go to page 2 and copy the title of the first recipe on that page."
            else:
                q = f"From the Meal Type hub, identify which meal type has the fewest recipes."
            out.append(_task(f"Allrecipes--gui_meal_type_{counter:03d}", "gui-meal-type", q))
    return out


def gen_seasonal_tasks():
    out = []
    counter = 0
    for slug, name, _desc in SEASONS:
        for k in range(8):
            counter += 1
            if k == 0:
                q = f"From the Seasonal Featured hub, click '{name}' and report the total recipes shown."
            elif k == 1:
                q = f"Open /featured/seasonal/{slug} and copy the title of the first {name.lower()} recipe shown."
            elif k == 2:
                q = f"From /featured/seasonal/{slug}, navigate to the second recipe and report its total time."
            elif k == 3:
                q = f"On the {name} seasonal page, go to page 2 and copy the title of the first recipe on that page."
            elif k == 4:
                q = f"From /featured/seasonal/{slug}, find a recipe with at least 30 reviews and copy its title."
            elif k == 5:
                q = f"On /featured/seasonal/{slug}, click any recipe and report its main ingredient as shown on the recipe page."
            elif k == 6:
                q = f"From the {name} page, find a recipe whose calories are under 500 and copy its title."
            else:
                q = f"From the seasonal hub, report which season has the most recipes featured."
            out.append(_task(f"Allrecipes--gui_seasonal_{counter:03d}", "gui-seasonal", q))
    return out


def gen_budget_tasks():
    out = []
    counter = 0
    for slug, name, _desc in BUDGETS:
        for k in range(11):
            counter += 1
            if k == 0:
                q = f"From the Budget hub, click '{name}' and report how many recipes are listed."
            elif k == 1:
                q = f"Open /budget/{slug} and copy the title of the first recipe shown."
            elif k == 2:
                q = f"From /budget/{slug}, navigate to the second recipe and report its average rating."
            elif k == 3:
                q = f"On /budget/{slug}, find a recipe whose total time is under 30 minutes and copy its title."
            elif k == 4:
                q = f"From the {name} page, go to page 2 and copy the title of the first recipe on that page."
            elif k == 5:
                q = f"On /budget/{slug}, find a recipe with 4-star rating or higher and copy its title."
            elif k == 6:
                q = f"From the Budget hub, identify which bucket has the most recipes."
            elif k == 7:
                q = f"On the {name} page, click any recipe and report its serving size."
            elif k == 8:
                q = f"From /budget/{slug}, find a vegetarian-tagged recipe (look for the diet chip) and copy its title."
            elif k == 9:
                q = f"On /budget/{slug}, count how many recipes on page 1 have a rating of exactly 5 stars (rounded)."
            else:
                q = f"From the Budget hub, copy the description text shown for '{name}'."
            out.append(_task(f"Allrecipes--gui_budget_{counter:03d}", "gui-budget", q))
    return out


def gen_time_tasks():
    out = []
    counter = 0
    for slug, name, _lo, _hi, _desc in TIME_BUCKETS:
        for k in range(8):
            counter += 1
            if k == 0:
                q = f"From the Time hub, click '{name}' and report how many recipes are listed."
            elif k == 1:
                q = f"Open /time/{slug} and copy the title of the first recipe shown."
            elif k == 2:
                q = f"From /time/{slug}, navigate to the second recipe and report its total time."
            elif k == 3:
                q = f"On /time/{slug}, go to page 2 and copy the title of the first recipe on that page."
            elif k == 4:
                q = f"From the {name} page, find a recipe with at least 100 reviews and copy its title."
            elif k == 5:
                q = f"On /time/{slug}, click any recipe and report its calorie count per serving."
            elif k == 6:
                q = f"From /time/{slug}, find a dessert-tagged recipe and copy its title."
            else:
                q = f"From the Time hub, identify which time bucket has the most recipes."
            out.append(_task(f"Allrecipes--gui_time_{counter:03d}", "gui-time", q))
    return out


def gen_dinner_fix_tasks():
    out = []
    counter = 0
    for slug, name, _desc in DINNER_FIX:
        for k in range(11):
            counter += 1
            if k == 0:
                q = f"From the Dinner Fix hub, click '{name}' and report how many recipes are listed."
            elif k == 1:
                q = f"Open /dinner-fix/{slug} and copy the title of the first recipe."
            elif k == 2:
                q = f"From /dinner-fix/{slug}, navigate to the second recipe and report its prep time."
            elif k == 3:
                q = f"On /dinner-fix/{slug}, find a recipe with chicken as the main ingredient and copy its title."
            elif k == 4:
                q = f"From the {name} page, go to page 2 and copy the title of the first recipe."
            elif k == 5:
                q = f"On /dinner-fix/{slug}, click any recipe and report its servings."
            elif k == 6:
                q = f"From /dinner-fix/{slug}, find a recipe with a 5-star average rating and copy its title."
            elif k == 7:
                q = f"From the Dinner Fix hub, identify which style has the most recipes."
            elif k == 8:
                q = f"On /dinner-fix/{slug}, find a recipe with calories under 600 and copy its title."
            elif k == 9:
                q = f"From the {name} page, click the first recipe and report its review count."
            else:
                q = f"From the Dinner Fix hub, copy the description shown for '{name}'."
            out.append(_task(f"Allrecipes--gui_dinner_fix_{counter:03d}", "gui-dinner-fix", q))
    return out


def gen_chef_bio_tasks():
    out = []
    chefs = _chef_directory()[:12]
    counter = 0
    for slug, name, _count in chefs:
        for k in range(3):
            counter += 1
            if k == 0:
                q = f"Open the Chef profile for '{name}' at /chef-bio/{slug} and report their total recipe count."
            elif k == 1:
                q = f"From the Chef hub, navigate to '{name}' and report the location listed in the chef header."
            else:
                q = f"From the chef profile for '{name}', click the first recipe and copy its title."
            out.append(_task(f"Allrecipes--gui_chef_bio_{counter:03d}", "gui-chef-bio", q))
    # Hub-level tasks
    counter += 1
    out.append(_task(f"Allrecipes--gui_chef_bio_{counter:03d}",
                     "gui-chef-bio",
                     "From the Chefs & Contributors hub, report the total number of contributors shown."))
    counter += 1
    out.append(_task(f"Allrecipes--gui_chef_bio_{counter:03d}",
                     "gui-chef-bio",
                     "From the Chefs & Contributors hub, identify which chef has the most recipes."))
    return out


def gen_editorial_tasks():
    """Cover the 25 editorial articles."""
    from sqlalchemy import text
    rows = db.session.execute(text(
        "SELECT slug, title, author_name, category, read_time_mins FROM article ORDER BY view_count DESC"
    )).fetchall()
    out = []
    counter = 0
    for row in rows[:25]:
        for k in range(2):
            counter += 1
            if k == 0:
                q = f"Open the editorial article '{row.title}' on /editorial/{row.slug} and report the author name shown."
            else:
                q = f"From the Editorial hub, click '{row.title}' and report the read-time (in minutes) shown."
            out.append(_task(f"Allrecipes--gui_editorial_{counter:03d}", "gui-editorial", q))
    # Hub-level tasks
    counter += 1
    out.append(_task(f"Allrecipes--gui_editorial_{counter:03d}",
                     "gui-editorial",
                     "From the Editorial hub, report the title of the most-viewed article (shown first)."))
    return out


def gen_diet_compare_tasks():
    out = []
    counter = 0
    diet_rows = DIET_COMPARE_TABLE
    for slug, name, *_rest in diet_rows:
        for k in range(4):
            counter += 1
            if k == 0:
                q = f"On the Compare Diets page (/diet/compare), find the row for '{name}' and report its typical fat percentage."
            elif k == 1:
                q = f"From /diet/compare, find the row for '{name}' and report the foods it primarily avoids."
            elif k == 2:
                q = f"On /diet/compare, find '{name}' and click through to its detail page (/diet/{slug}); report the description shown."
            else:
                q = f"On /diet/compare, locate the recipe count column for '{name}' and report the value."
            out.append(_task(f"Allrecipes--gui_diet_compare_{counter:03d}", "gui-diet-compare", q))
    return out


def main():
    with app.app_context():
        existing = _existing_ids()
        print(f"existing task count: {len(existing)}")
        new_tasks = []
        for fn in [
            gen_recipe_subpage_tasks,
            gen_cuisine_tasks,
            gen_skill_level_tasks,
            gen_equipment_tasks,
            gen_meal_type_tasks,
            gen_seasonal_tasks,
            gen_budget_tasks,
            gen_time_tasks,
            gen_dinner_fix_tasks,
            gen_chef_bio_tasks,
            gen_editorial_tasks,
            gen_diet_compare_tasks,
        ]:
            t = fn()
            print(f"  {fn.__name__}: {len(t)} tasks")
            new_tasks.extend(t)
        # Filter dups
        before = len(new_tasks)
        new_tasks = [t for t in new_tasks if t["id"] not in existing]
        print(f"appending {len(new_tasks)} new tasks ({before - len(new_tasks)} already present)")
        with open(TASKS_FILE, "a") as f:
            for t in new_tasks:
                f.write(json.dumps(t) + "\n")
        print("done.")


if __name__ == "__main__":
    main()
