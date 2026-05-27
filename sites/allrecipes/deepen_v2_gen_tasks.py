#!/usr/bin/env python3
"""Deepen-v2 task generator — appends ~1500 R3..R10 tasks to tasks.jsonl.

R3  nutrition-calculator   (macro / kcal / GI / per-serving scaling)
R4  step-photo-wizard      (cook-along step pages + glossary + cues)
R5  meal-planner / grocery (7-day plan generator + auto-merge bag)
R6  technique / cooking-school   (article long-reads + course catalog + quiz)
R7  holiday-hub             (thanksgiving / christmas / lunar-new-year / ramadan / passover ...)
R8  community / UGC         (submit / gallery / leaderboard / upvote / featured)
R9  kitchenware-affiliate   (catalog / detail / compare / buy / deals)
R10 public-api / graphql / webhook / json-ld / sitemap-index

Idempotent — skips ids already present in tasks.jsonl. Run from the site
directory: ``python3 deepen_v2_gen_tasks.py``.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
TASKS = BASE / 'tasks.jsonl'
DB = BASE / 'instance_seed' / 'allrecipes.db'
WEB = 'http://localhost:40000/'
UPSTREAM = 'https://www.allrecipes.com/'


def load_existing_ids() -> set[str]:
    if not TASKS.exists():
        return set()
    out = set()
    with TASKS.open() as f:
        for line in f:
            try:
                out.add(json.loads(line)['id'])
            except Exception:
                pass
    return out


def pull_pool():
    c = sqlite3.connect(DB)
    top = list(c.execute(
        "SELECT slug, title, servings, calories, avg_rating, review_count, "
        "cuisine, occasion, dish_type, meal_type, cooking_method "
        "FROM recipe WHERE avg_rating >= 4.5 AND review_count >= 80 "
        "ORDER BY review_count DESC LIMIT 200"))
    mid = list(c.execute(
        "SELECT slug, title, servings, calories "
        "FROM recipe WHERE avg_rating >= 4.0 AND review_count >= 20 "
        "ORDER BY id LIMIT 1500"))
    holiday = {}
    for occ in ('thanksgiving', 'christmas', 'easter', 'valentines',
                'halloween', 'fourth-of-july', 'super-bowl', 'mothers-day',
                'birthday', 'summer-cookout', 'hanukkah'):
        rows = list(c.execute(
            "SELECT slug, title FROM recipe WHERE occasion LIKE ? "
            "AND avg_rating >= 4.0 ORDER BY review_count DESC LIMIT 50",
            (f'%{occ}%',)))
        holiday[occ] = rows
    c.close()
    return top, mid, holiday


def emit(out, tid, ttype, ques):
    out.append({
        'web_name': 'Allrecipes',
        'id': tid,
        'task_type': ttype,
        'ques': ques,
        'web': WEB,
        'upstream_url': UPSTREAM,
    })


# --------------------------------------------------------------------------
# R3 — nutrition calculator + allergen-multi-filter (~200 tasks)
# --------------------------------------------------------------------------

def gen_r3(out, top, mid):
    # 3a — macro % split for top recipes
    for i, r in enumerate(top[:50]):
        slug, title = r[0], r[1]
        emit(out, f'Allrecipes--r3_macro_split_{i:03d}',
             'nutrition-macro-split',
             f"Open the nutrition calculator at /nutrition/calculator?recipe={slug} "
             f"and report the protein / carbs / fat percentage split for {title}.")
    # 3b — per-serving scaling
    targets = [2, 4, 6, 8, 12, 16, 24]
    for i, r in enumerate(top[:50]):
        slug, title, servings = r[0], r[1], r[2] or '4'
        t = targets[i % len(targets)]
        emit(out, f'Allrecipes--r3_scale_serving_{i:03d}',
             'nutrition-per-serving',
             f"Use /nutrition/calculator?recipe={slug}&servings={t} to rescale "
             f"{title} (base servings {servings}) to {t} servings — report the "
             f"new kcal and sodium per serving.")
    # 3c — glycemic index lookup
    for i, r in enumerate(top[:40]):
        slug, title = r[0], r[1]
        emit(out, f'Allrecipes--r3_gi_lookup_{i:03d}',
             'nutrition-glycemic-index',
             f"Hit /nutrition/glycemic?recipe={slug} and report the glycemic "
             f"index band (low / medium / high) for {title}.")
    # 3d — allergen multi-filter
    combos = [
        ['dairy'], ['gluten'], ['nut'], ['egg'], ['soy'],
        ['dairy', 'gluten'], ['dairy', 'nut'], ['gluten', 'egg'],
        ['gluten', 'nut'], ['dairy', 'soy'], ['dairy', 'gluten', 'nut'],
        ['dairy', 'gluten', 'egg'], ['gluten', 'nut', 'soy'],
        ['dairy', 'gluten', 'nut', 'egg'],
        ['dairy', 'gluten', 'nut', 'egg', 'soy'],
    ]
    for i, combo in enumerate(combos * 4):
        joined = ','.join(combo)
        emit(out, f'Allrecipes--r3_allergen_multi_{i:03d}',
             'allergen-multi-filter',
             f"Use /allergen/multi-filter?free={joined} to find recipes that "
             f"are simultaneously free of {', '.join(combo)} — name two "
             f"matching recipes and their dietary tags.")
    # 3e — diabetic-friendly check
    for i, r in enumerate(top[:30]):
        slug, title = r[0], r[1]
        emit(out, f'Allrecipes--r3_diabetic_check_{i:03d}',
             'nutrition-diabetic-friendly',
             f"Is {title} flagged as diabetic-friendly by the calculator? "
             f"Check /nutrition/glycemic?recipe={slug}.")


# --------------------------------------------------------------------------
# R4 — step-by-step photo wizard (~200 tasks)
# --------------------------------------------------------------------------

def gen_r4(out, top, mid):
    # 4a — open wizard landing
    for i, r in enumerate(top[:60]):
        slug, title = r[0], r[1]
        emit(out, f'Allrecipes--r4_wizard_landing_{i:03d}',
             'step-photo-wizard-landing',
             f"Open the step-by-step photo wizard for {title} at "
             f"/recipe/{slug}/wizard and report the total number of steps.")
    # 4b — navigate to a specific step
    for i, r in enumerate(top[:60]):
        slug, title = r[0], r[1]
        step = (i % 5) + 2
        emit(out, f'Allrecipes--r4_wizard_step_{i:03d}',
             'step-photo-wizard-step',
             f"From /recipe/{slug}/wizard/{step}, copy the instruction text "
             f"that appears for step {step} of {title}.")
    # 4c — sound-cue chip
    for i, r in enumerate(top[:30]):
        slug, title = r[0], r[1]
        emit(out, f'Allrecipes--r4_wizard_cue_{i:03d}',
             'step-photo-wizard-sound-cue',
             f"In the {title} wizard, walk through every step until you find "
             f"one whose sound cue is not 'idle' — report the step number "
             f"and the cue.")
    # 4d — glossary
    terms = ['fold', 'saute', 'deglaze', 'blanch', 'temper', 'reduce',
             'cream', 'knead', 'proof', 'rest', 'sear', 'braise', 'roux',
             'emulsify', 'baste']
    for i, term in enumerate(terms * 3):
        emit(out, f'Allrecipes--r4_glossary_{i:03d}',
             'cooking-glossary-lookup',
             f"Use /wizard/glossary?q={term} to look up the technique '{term}' "
             f"and copy back the one-sentence definition.")
    # 4e — wizard progress strip (top up to 200+)
    for i, r in enumerate(top[:20]):
        slug, title = r[0], r[1]
        emit(out, f'Allrecipes--r4_wizard_progress_{i:03d}',
             'step-photo-wizard-progress',
             f"Open /recipe/{slug}/wizard/2 and confirm the progress strip "
             f"highlights step 2 of N as the current step.")


# --------------------------------------------------------------------------
# R5 — meal-planner + grocery list (~200 tasks)
# --------------------------------------------------------------------------

def gen_r5(out, top, mid):
    presets = ['balanced', 'high-protein', 'low-carb', 'vegan',
               'family-kids', 'mediterranean', 'pescatarian', 'budget']
    # 5a — preset 1-week plan
    for i in range(60):
        preset = presets[i % len(presets)]
        week = (i // len(presets)) + 1
        emit(out, f'Allrecipes--r5_meal_plan_generate_{i:03d}',
             'meal-plan-generate',
             f"Generate a 1-week meal plan with /meal-planner/generate"
             f"?preset={preset}&week={week} and report Wednesday's dinner "
             f"and the average kcal/day.")
    # 5b — grocery merge
    pool_slugs = [r[0] for r in top[:80]]
    for i in range(50):
        combo = [pool_slugs[(i * 3) % 80], pool_slugs[(i * 5 + 1) % 80],
                 pool_slugs[(i * 7 + 2) % 80]]
        slugs = ','.join(combo)
        emit(out, f'Allrecipes--r5_grocery_merge_{i:03d}',
             'grocery-list-merge',
             f"Use /grocery-list/merge?recipes={slugs} to combine the "
             f"shopping list for those three recipes — name the ingredient "
             f"that appears in all three.")
    # 5c — grocery by aisle
    for i in range(40):
        combo = [pool_slugs[(i * 11) % 80], pool_slugs[(i * 13 + 1) % 80]]
        slugs = ','.join(combo)
        emit(out, f'Allrecipes--r5_grocery_by_aisle_{i:03d}',
             'grocery-list-by-aisle',
             f"Use /grocery-list/by-aisle?recipes={slugs} to organise the "
             f"merged shopping list by store aisle — list the produce aisle items.")
    # 5d — kcal target sanity check
    for i, preset in enumerate(presets * 6):
        emit(out, f'Allrecipes--r5_kcal_target_{i:03d}',
             'meal-plan-kcal-target',
             f"For preset='{preset}' week=1 plan, does the average kcal/day "
             f"fall within ±150 kcal of the preset's declared target?")
    # 5e — Wednesday breakfast extraction (top up to 200+)
    for i in range(12):
        preset = presets[i % len(presets)]
        emit(out, f'Allrecipes--r5_wed_breakfast_{i:03d}',
             'meal-plan-day-meal',
             f"From /meal-planner/generate?preset={preset}&week=1 report "
             f"Wednesday's breakfast recipe slug.")


# --------------------------------------------------------------------------
# R6 — technique articles + cooking-school (~200 tasks)
# --------------------------------------------------------------------------

def gen_r6(out, top, mid):
    courses = [
        ('knife-skills', 'Knife Skills 101'),
        ('sauces-mother', 'The Five Mother Sauces'),
        ('breadmaking-fundamentals', 'Breadmaking Fundamentals'),
        ('butchery-home', 'Home Butchery Basics'),
        ('pastry-laminated', 'Laminated Pastry'),
        ('grilling-mastery', 'Grilling & BBQ Mastery'),
        ('fermentation-101', 'Fermentation 101'),
        ('sous-vide', 'Sous-vide Fundamentals'),
        ('vegan-cookery', 'Vegan Cookery Foundations'),
        ('asian-stir-fry', 'Asian Stir-fry Wok Skills'),
        ('charcuterie', 'Charcuterie & Curing'),
        ('cake-decorating', 'Cake Decorating Essentials'),
    ]
    # 6a — course detail open
    for i, (slug, title) in enumerate(courses * 4):
        emit(out, f'Allrecipes--r6_course_detail_{i:03d}',
             'cooking-school-course-detail',
             f"Open /cooking-school/course/{slug} and report how many "
             f"lessons the {title} course has.")
    # 6b — quiz attempt
    for i, (slug, title) in enumerate(courses * 4):
        emit(out, f'Allrecipes--r6_quiz_attempt_{i:03d}',
             'cooking-school-quiz',
             f"From /cooking-school/quiz/{slug}, report the passing score "
             f"and the correct answer for question 3.")
    # 6c — technique master list
    terms = ['baste', 'blanch', 'braise', 'cream', 'deglaze', 'emulsify',
             'fold', 'knead', 'proof', 'reduce', 'rest', 'roux',
             'saute', 'sear', 'temper']
    for i, t in enumerate(terms * 4):
        emit(out, f'Allrecipes--r6_technique_index_{i:03d}',
             'technique-master-list',
             f"Use /technique/master-list to locate '{t}' and report which "
             f"cooking-school courses reference it.")
    # 6d — cooking-school catalog
    for i in range(40):
        emit(out, f'Allrecipes--r6_school_catalog_{i:03d}',
             'cooking-school-catalog',
             f"Visit /cooking-school and report the {(i % 12) + 1}th course "
             f"title and its difficulty level.")
    # 6e — technique-course cross (top up to 200+)
    for i, (slug, title) in enumerate(courses):
        emit(out, f'Allrecipes--r6_school_lessons_{i:03d}',
             'cooking-school-lesson-count',
             f"Open /cooking-school/course/{slug} and confirm the lesson "
             f"list renders {(i % 5) + 5}+ lessons for {title}.")


# --------------------------------------------------------------------------
# R7 — holiday hubs (~200 tasks)
# --------------------------------------------------------------------------

def gen_r7(out, holiday):
    holidays = [
        ('thanksgiving', 'Thanksgiving'),
        ('christmas', 'Christmas Dinner'),
        ('lunar-new-year', 'Lunar New Year'),
        ('ramadan-iftar', 'Ramadan Iftar'),
        ('passover', 'Passover Seder'),
        ('easter', 'Easter Brunch'),
        ('hanukkah', 'Hanukkah'),
        ('diwali', 'Diwali'),
    ]
    # 7a — open holiday hub
    for i, (slug, name) in enumerate(holidays * 4):
        emit(out, f'Allrecipes--r7_holiday_open_{i:03d}',
             'holiday-hub-open',
             f"Open /holiday/{slug} and name the top-rated main course "
             f"recommended for {name}.")
    # 7b — count totals
    for i, (slug, name) in enumerate(holidays * 4):
        emit(out, f'Allrecipes--r7_holiday_total_{i:03d}',
             'holiday-hub-total',
             f"How many total recipes does the {name} hub at /holiday/{slug} "
             f"list across all four menu sections?")
    # 7c — desserts surface
    for i, (slug, name) in enumerate(holidays * 4):
        emit(out, f'Allrecipes--r7_holiday_dessert_{i:03d}',
             'holiday-hub-dessert',
             f"From the {name} hub at /holiday/{slug}, copy the name of "
             f"the first dessert listed.")
    # 7d — appetisers / sides cross
    for i, (slug, name) in enumerate(holidays * 4):
        emit(out, f'Allrecipes--r7_holiday_appetiser_{i:03d}',
             'holiday-hub-appetiser',
             f"In /holiday/{slug}, find the first appetiser listed for "
             f"{name} and click through — what cuisine does it belong to?")
    # 7e — master holiday hub
    for i in range(40):
        emit(out, f'Allrecipes--r7_holidays_master_{i:03d}',
             'holidays-master-hub',
             f"Visit /holidays and report the season label printed next to "
             f"{holidays[i % 8][1]}.")
    # 7f — sides surface (top up to 200+)
    for i, (slug, name) in enumerate(holidays * 5):
        emit(out, f'Allrecipes--r7_holiday_sides_{i:03d}',
             'holiday-hub-side',
             f"From /holiday/{slug}, copy the title of the first side dish "
             f"recommended for {name}.")


# --------------------------------------------------------------------------
# R8 — UGC community (~200 tasks)
# --------------------------------------------------------------------------

def gen_r8(out, top, mid):
    pool = list(top[:80])
    # 8a — submit a recipe
    for i in range(40):
        emit(out, f'Allrecipes--r8_ugc_submit_{i:03d}',
             'ugc-recipe-submit',
             f"Open /community/submit, fill in 'Submission #{i:03d}' as "
             f"title plus dummy ingredients and steps, and confirm the "
             f"returned submission_id is non-zero.")
    # 8b — leaderboard navigation
    for i in range(50):
        emit(out, f'Allrecipes--r8_leaderboard_{i:03d}',
             'community-leaderboard',
             f"Hit /community/leaderboard and report rank #{(i % 50) + 1}: "
             f"recipe title, community score and author name.")
    # 8c — gallery pagination
    for i in range(40):
        page = (i % 5) + 1
        emit(out, f'Allrecipes--r8_gallery_paging_{i:03d}',
             'community-gallery-paging',
             f"Open /community/gallery?page={page} and count how many "
             f"recipe tiles are shown on that page.")
    # 8d — upvote
    for i in range(40):
        r = pool[i % len(pool)]
        emit(out, f'Allrecipes--r8_upvote_{i:03d}',
             'community-upvote',
             f"POST to /community/upvote/<id> for {r[1]} (its recipe id is "
             f"discoverable via /api/v1/search?q={r[0]}) and confirm the "
             f"projected upvote count goes up by 1.")
    # 8e — featured editors picks
    for i in range(40):
        emit(out, f'Allrecipes--r8_featured_{i:03d}',
             'community-featured',
             f"Visit /community/featured and report the {(i % 30) + 1}th "
             f"editor's-pick recipe title and average rating.")


# --------------------------------------------------------------------------
# R9 — kitchenware affiliate (~200 tasks)
# --------------------------------------------------------------------------

def gen_r9(out):
    kitchen = [
        'dutch-oven-7qt', 'cast-iron-12in', 'chef-knife-8in', 'paring-knife',
        'santoku-knife', 'stand-mixer-6qt', 'food-processor', 'pressure-cooker',
        'sous-vide-circ', 'wok-14in', 'grill-charcoal', 'pizza-stone',
        'mandoline', 'digital-scale', 'instant-thermometer', 'rolling-pin',
        'mortar-pestle', 'blender-high-speed', 'hand-blender',
        'baking-sheet-set', 'pasta-machine', 'mixing-bowl-set',
        'bench-scraper', 'cake-pan-9in',
    ]
    cats = ['pot', 'skillet', 'knife', 'mixer', 'processor', 'cooker',
            'sous-vide', 'wok', 'grill', 'baking', 'gadget', 'tool',
            'blender']
    # 9a — open product detail
    for i, slug in enumerate(kitchen * 3):
        emit(out, f'Allrecipes--r9_kitchen_detail_{i:03d}',
             'kitchenware-detail',
             f"Open /kitchen/{slug} and report the list price plus the "
             f"first technique listed under 'Used in these techniques'.")
    # 9b — buy redirect
    for i, slug in enumerate(kitchen * 2):
        emit(out, f'Allrecipes--r9_kitchen_buy_{i:03d}',
             'kitchenware-amazon-redirect',
             f"Follow /kitchen/{slug}/buy and confirm the 302 redirects to "
             f"an amazon.com link with affiliate tag allrecipes-20.")
    # 9c — category browse
    for i, cat in enumerate(cats * 4):
        emit(out, f'Allrecipes--r9_kitchen_category_{i:03d}',
             'kitchenware-category',
             f"Visit /kitchen/category/{cat} and count how many products "
             f"are listed in the {cat} category.")
    # 9d — compare two items
    for i in range(30):
        a = kitchen[(i * 3) % len(kitchen)]
        b = kitchen[(i * 5 + 1) % len(kitchen)]
        emit(out, f'Allrecipes--r9_kitchen_compare_{i:03d}',
             'kitchenware-compare',
             f"Use /kitchen/compare?items={a},{b} to compare those two "
             f"products — which is cheaper and by how much?")
    # 9e — deals carousel
    for i in range(30):
        emit(out, f'Allrecipes--r9_kitchen_deals_{i:03d}',
             'kitchenware-deals',
             f"Open /kitchen/deals and report deal-position {(i % 8) + 1}: "
             f"product name, list price and deal price.")


# --------------------------------------------------------------------------
# R10 — public API / GraphQL / webhook / JSON-LD (~200 tasks)
# --------------------------------------------------------------------------

def gen_r10(out, top, mid):
    pool = list(top[:80])
    # 10a — REST recipe by id
    for i in range(60):
        emit(out, f'Allrecipes--r10_rest_recipe_{i:03d}',
             'api-v1-recipe-detail',
             f"GET /api/v1/recipes/{(i % 80) + 1} and report the title and "
             f"calories from the JSON payload.")
    # 10b — REST list pagination
    for i in range(40):
        page = (i % 20) + 1
        per = [10, 25, 50][i % 3]
        emit(out, f'Allrecipes--r10_rest_list_{i:03d}',
             'api-v1-recipes-list',
             f"GET /api/v1/recipes?page={page}&per_page={per} and report "
             f"how many results came back and the total field.")
    # 10c — REST search
    queries = ['chicken', 'lasagna', 'salad', 'soup', 'pasta', 'cookies',
               'cake', 'pie', 'shrimp', 'tofu', 'curry', 'pancake']
    for i, q in enumerate(queries * 4):
        emit(out, f'Allrecipes--r10_rest_search_{i:03d}',
             'api-v1-search',
             f"GET /api/v1/search?q={q}&limit=10 and report the slug of the "
             f"top result.")
    # 10d — GraphQL query (recipe by slug)
    for i, r in enumerate(pool[:30]):
        slug = r[0]
        emit(out, f'Allrecipes--r10_graphql_recipe_{i:03d}',
             'graphql-recipe',
             f"POST to /graphql with query "
             f'\'query {{ recipe(slug: "{slug}") {{ id title calories }} }}\' '
             f"and report the calories field.")
    # 10e — GraphQL recipes(limit)
    for i in range(20):
        lim = [5, 10, 25][i % 3]
        emit(out, f'Allrecipes--r10_graphql_recipes_{i:03d}',
             'graphql-recipes',
             f"POST to /graphql with query "
             f'\'query {{ recipes(limit: {lim}) {{ id slug title }} }}\' '
             f"and report how many recipes came back.")
    # 10f — JSON-LD schema.org Recipe
    for i, r in enumerate(pool[:30]):
        slug = r[0]
        emit(out, f'Allrecipes--r10_jsonld_{i:03d}',
             'jsonld-recipe',
             f"GET /jsonld/recipe/{slug} and confirm the @type field "
             f"is 'Recipe' and ingredients are present.")
    # 10g — sitemap-index
    for i in range(20):
        emit(out, f'Allrecipes--r10_sitemap_index_{i:03d}',
             'sitemap-index',
             f"GET /sitemap-index.xml and count how many <sitemap> entries "
             f"are listed.")
    # 10h — webhook subscribe
    for i in range(20):
        cb = f'https://hooks.example.com/r{i:02d}'
        emit(out, f'Allrecipes--r10_webhook_{i:03d}',
             'webhook-subscribe',
             f"POST to /webhook/recipe-updated/subscribe with "
             f'{{"callback_url": "{cb}"}} and confirm the response contains '
             f"a subscription_id and a verification_token.")
    # 10i — healthz
    for i in range(10):
        emit(out, f'Allrecipes--r10_healthz_{i:03d}',
             'healthz-check',
             "GET /healthz and confirm the response is 200 with status='ok'.")


def main():
    if not DB.exists():
        # Fall back to instance/site.db if seed DB missing.
        alt = BASE / 'instance' / 'site.db'
        if alt.exists():
            globals()['DB'] = alt
        else:
            raise SystemExit("DB not found; run app first to seed.")
    top, mid, holiday = pull_pool()
    out: list[dict] = []
    gen_r3(out, top, mid)
    gen_r4(out, top, mid)
    gen_r5(out, top, mid)
    gen_r6(out, top, mid)
    gen_r7(out, holiday)
    gen_r8(out, top, mid)
    gen_r9(out)
    gen_r10(out, top, mid)

    existing = load_existing_ids()
    fresh = [t for t in out if t['id'] not in existing]

    with TASKS.open('a') as f:
        for t in fresh:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    by_round = {}
    for t in fresh:
        r = t['id'].split('--')[1].split('_')[0]
        by_round[r] = by_round.get(r, 0) + 1
    print(f"[deepen_v2_gen_tasks] generated={len(out)} new_appended={len(fresh)} "
          f"skipped_dup={len(out) - len(fresh)}")
    for k in sorted(by_round):
        print(f"  {k}: {by_round[k]}")


if __name__ == '__main__':
    main()
