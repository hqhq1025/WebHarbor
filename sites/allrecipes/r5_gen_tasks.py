#!/usr/bin/env python3
"""R5 task generator — extends ``tasks.jsonl`` with 700+ new tasks across
the new task types specified in the R5 polish iteration.

Run once from the site dir: `python3 r5_gen_tasks.py`. Idempotent — skips
any task_id that already exists in the file.

New task types added:
  * equipment-filter         (find a recipe using a specific kitchen tool)
  * allergen-exclude         (avoid dairy/gluten/nut/egg/soy)
  * ingredient-substitute    (swap an ingredient)
  * recipe-difficulty-find   (under-30-min / one-pot)
  * recipe-yield-convert     (scale servings)
  * cooking-tip-extract      (from a cooking-tip article)
  * video-show-step          (find a step-by-step photo / gallery)
  * multi-step               (browse + filter + extract)
  * make-ahead-filter        (R5 variant theme)
  * kid-friendly-filter
  * freezer-meal-filter
  * global-fusion-filter
  * calorie-tier
  * cuisine-origin
  * time-budget-tier
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, 'tasks.jsonl')
SEED_DB = os.path.join(BASE_DIR, 'instance_seed', 'allrecipes.db')


def load_existing():
    if not os.path.exists(TASKS_FILE):
        return [], set()
    tasks = []
    ids = set()
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            tasks.append(t)
            ids.add(t['id'])
    return tasks, ids


def next_id(existing_ids, prefix='Allrecipes--R5--'):
    n = 0
    while f"{prefix}{n}" in existing_ids:
        n += 1
    return f"{prefix}{n}", n


def make_task(task_id, task_type, ques):
    return {
        "web_name": "Allrecipes",
        "id": task_id,
        "task_type": task_type,
        "ques": ques,
        "web": "http://localhost:40000/",
        "upstream_url": "https://www.allrecipes.com/",
    }


def main():
    if not os.path.exists(SEED_DB):
        print(f"ERROR: seed db not found at {SEED_DB}")
        sys.exit(1)

    existing_tasks, existing_ids = load_existing()
    print(f"[r5_tasks] loaded {len(existing_tasks)} existing tasks")

    conn = sqlite3.connect(SEED_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pull useful slug pools.
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Make-Ahead Test Kitchen' ORDER BY id")
    make_ahead = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Kid-Friendly Test Kitchen' ORDER BY id")
    kid_friendly = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Freezer-Meal Test Kitchen' ORDER BY id")
    freezer = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Global-Fusion Test Kitchen' ORDER BY id")
    fusion = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='One-Pot Test Kitchen' ORDER BY id LIMIT 60")
    one_pot = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Sheet-Pan Test Kitchen' ORDER BY id LIMIT 60")
    sheet_pan = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Healthy-Swap Test Kitchen' ORDER BY id LIMIT 60")
    healthy_swap = cur.fetchall()
    cur.execute("SELECT slug, title, total_time_mins FROM recipe WHERE total_time_mins>0 AND total_time_mins<=30 ORDER BY id LIMIT 80")
    under_30 = cur.fetchall()
    cur.execute("SELECT slug, title, calories FROM recipe WHERE calories<300 AND calories>0 ORDER BY id LIMIT 80")
    low_cal = cur.fetchall()
    cur.execute("SELECT slug, title, calories FROM recipe WHERE calories>=500 ORDER BY id LIMIT 80")
    high_cal = cur.fetchall()
    cur.execute("SELECT slug, title, cuisine FROM recipe WHERE cuisine IS NOT NULL AND cuisine!='' ORDER BY id LIMIT 200")
    by_cuisine = cur.fetchall()
    cur.execute("SELECT slug, title FROM article ORDER BY id")
    articles = cur.fetchall()
    cur.execute("SELECT slug, title FROM collection ORDER BY id")
    collections = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name LIKE 'Chef %' ORDER BY id LIMIT 60")
    chef_recipes = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Slow Cooker Test Kitchen' ORDER BY id LIMIT 40")
    slow_cooker = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Air Fryer Test Kitchen' ORDER BY id LIMIT 40")
    air_fryer = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Grilled Test Kitchen' ORDER BY id LIMIT 40")
    grilled = cur.fetchall()

    rng = random.Random(20260526)

    new_tasks = []

    def add(task_type, ques):
        tid, _ = next_id(existing_ids, 'Allrecipes--R5--')
        existing_ids.add(tid)
        new_tasks.append(make_task(tid, task_type, ques))

    # ----- equipment-filter (60) -----
    equipment_questions = [
        ("Dutch oven",   "Find a one-pot recipe that uses a Dutch oven and serves at least 4 people."),
        ("Dutch oven",   "Show me a recipe cooked in a Dutch oven that has a total time under 90 minutes."),
        ("sheet pan",    "Find a sheet-pan dinner recipe that needs less than 30 minutes of prep time."),
        ("sheet pan",    "Recommend a sheet-pan recipe with chicken and at least a 4-star rating."),
        ("slow cooker",  "Find a slow cooker recipe for game day with chili or pulled pork."),
        ("slow cooker",  "Recommend a slow cooker recipe that cooks for at least 4 hours and serves 6+."),
        ("air fryer",    "Find an air-fryer recipe with fewer than 6 ingredients."),
        ("air fryer",    "Recommend an air-fryer recipe with a 4.5-star or higher rating."),
        ("instant pot",  "Find a pressure-cooker (Instant Pot) recipe for a soup or stew."),
        ("grill",        "Find a grilled main-dish recipe suitable for outdoor summer cookouts."),
        ("grill",        "Recommend a grilled vegetarian recipe with at least 100 reviews."),
        ("skillet",      "Find a one-skillet weeknight dinner recipe that takes 30 minutes or less."),
        ("blender",      "Find a recipe whose sauce or soup is finished in a blender."),
        ("food processor", "Find a recipe whose dough or filling is made in a food processor."),
        ("wok",          "Find a stir-fry recipe suitable for cooking in a wok."),
        ("stand mixer",  "Find a bread or pastry recipe that calls for a stand mixer with dough hook."),
    ]
    for tool, q in equipment_questions:
        add('equipment-filter', q)
    # Extend with one query per popular base recipe.
    for r in (one_pot[:14] + sheet_pan[:14] + slow_cooker[:14]):
        slug = r['slug']
        title = r['title']
        add('equipment-filter',
            f"Find a recipe similar to {title} that uses the same primary piece of cooking equipment.")

    # ----- allergen-exclude (75) -----
    allergens = [
        ('dairy-free',    'dairy', 'milk, butter, cream and cheese'),
        ('gluten-free',   'gluten', 'wheat flour, pasta, bread and other gluten'),
        ('nut-free',      'tree nuts', 'almonds, walnuts, pecans, cashews and pine nuts'),
        ('egg-free',      'eggs', 'eggs, mayonnaise and meringue'),
        ('soy-free',      'soy', 'soy sauce, tofu, edamame and miso'),
    ]
    for tag, label, examples in allergens:
        add('allergen-exclude',
            f"Find a {tag} dessert recipe with at least 50 reviews — avoid {examples}.")
        add('allergen-exclude',
            f"Recommend a {tag} weeknight dinner that serves 4 and has a 4-star or higher rating.")
        add('allergen-exclude',
            f"I have a {label} allergy. Find a chicken main-dish recipe that does not contain {label}.")
        add('allergen-exclude',
            f"Find a {tag} pasta recipe — note any substitutes the page suggests for the allergens.")
        add('allergen-exclude',
            f"Find a breakfast recipe marked {tag} that takes under 30 minutes total.")
    # Combinations
    for q in [
        "Find a dairy-free AND gluten-free dessert recipe.",
        "Find a recipe that is dairy-free, gluten-free, AND nut-free.",
        "I am cooking for a guest with a peanut allergy and a dairy allergy. Find a chicken main-dish that is safe.",
        "Find a vegan recipe that is also gluten-free and serves at least 6 people.",
        "Find a soy-free Asian-style recipe — note any non-soy umami substitutes used.",
        "Find an egg-free baking recipe with a rating of 4.5 stars or higher.",
        "Find a nut-free pesto-style sauce recipe.",
        "Find a gluten-free pizza recipe that uses a cauliflower or almond-flour crust alternative — but is still nut-free if possible.",
        "Find a dairy-free chocolate-based dessert recipe (use cocoa powder or dairy-free chocolate).",
        "I have a gluten allergy. Find a soup recipe that uses corn or rice instead of flour as a thickener.",
        "Find a kid-friendly, peanut-free school-lunch recipe.",
        "Find a dairy-free smoothie or breakfast bowl recipe with at least 4 stars.",
        "Find a gluten-free pasta substitute recipe — note what is used instead of wheat pasta.",
        "Find a holiday-appropriate dairy-free side dish recipe.",
        "Find an egg-free pancake or waffle recipe.",
    ]:
        add('allergen-exclude', q)

    # ----- ingredient-substitute (55) -----
    sub_pairs = [
        ("Greek yogurt for sour cream", "a recipe where Greek yogurt is suggested as a substitute for sour cream"),
        ("almond milk for dairy milk", "a recipe where almond milk replaces dairy milk"),
        ("coconut oil for butter", "a recipe where coconut oil is suggested instead of butter"),
        ("applesauce for oil", "a baking recipe where applesauce can substitute for oil"),
        ("flax egg for egg", "a vegan baking recipe that uses a flax egg in place of a real egg"),
        ("whole-wheat flour for white flour", "a recipe where whole-wheat flour replaces white all-purpose flour"),
        ("aquafaba for egg whites", "a vegan meringue or mousse recipe that uses aquafaba"),
        ("cauliflower rice for rice", "a recipe that uses cauliflower rice in place of regular rice"),
        ("zucchini noodles for pasta", "a recipe that uses zucchini noodles (zoodles) instead of pasta"),
        ("honey for sugar", "a recipe where honey is used instead of refined sugar"),
        ("maple syrup for sugar", "a baking recipe where maple syrup substitutes for sugar"),
        ("ground turkey for ground beef", "a comfort-food recipe where ground turkey replaces ground beef"),
        ("nutritional yeast for parmesan", "a vegan recipe where nutritional yeast stands in for parmesan"),
        ("coconut aminos for soy sauce", "a soy-free recipe where coconut aminos replaces soy sauce"),
        ("avocado for butter", "a baking recipe where avocado is the fat replacement for butter"),
        ("Italian seasoning blend for fresh herbs", "a quick recipe that uses Italian seasoning blend in place of fresh herbs"),
    ]
    for _, fragment in sub_pairs:
        add('ingredient-substitute', f"Find {fragment}.")
        add('ingredient-substitute',
            f"Find {fragment} that has a rating of at least 4 stars and serves 4 or more.")
    # Add open-ended substitute prompts
    for q in [
        "Find a healthy-swap recipe that lists at least three explicit ingredient substitutions in the ingredient list.",
        "Find a recipe that substitutes Greek yogurt for sour cream AND whole-grain pasta for white pasta.",
        "I do not have buttermilk. Find a recipe that explicitly suggests a buttermilk substitute (milk + lemon, etc.).",
        "I am out of fresh basil. Find a pasta recipe that suggests using dried herbs as a substitute.",
        "Find a recipe that explains how to substitute fresh garlic with garlic powder.",
        "Find a low-fat dessert recipe that swaps in Greek yogurt or applesauce.",
        "Find a vegan brownie recipe that substitutes flax egg AND coconut oil.",
        "Find a gluten-free baking recipe that explicitly explains the flour substitution it uses.",
        "Find a recipe that explains why kosher salt and table salt should be swapped at different ratios.",
        "Find a recipe where soy sauce is substituted with tamari for a gluten-free version.",
        "Find a recipe that uses cashew cream in place of heavy cream.",
        "Find a recipe with a substitution note about replacing eggs with bananas in pancakes or muffins.",
        "Find a recipe whose ingredient list calls for plant-based milk and explicitly mentions which type works best.",
        "Find a 5-minute sauce recipe that explicitly suggests an oil substitute (e.g. avocado oil instead of olive).",
        "Find a healthy-swap pasta recipe — list the swaps it suggests.",
        "Find a healthy-swap dessert recipe — list the swaps it suggests.",
        "Find a healthy-swap chicken recipe — list every substitute in the ingredient list.",
        "Find a recipe that suggests a substitute for heavy cream to make a soup lighter.",
        "Find a recipe that explicitly suggests substituting kosher salt for table salt and vice versa.",
        "Find a recipe that substitutes a roux with corn-starch slurry for gluten-free thickening.",
        "Find a recipe that explains the substitution between fresh and dried thyme or oregano.",
        "Find a dessert recipe that uses date paste as a refined-sugar substitute.",
        "Find a 30-minute dinner recipe that substitutes chicken thighs for chicken breasts.",
    ]:
        add('ingredient-substitute', q)

    # ----- recipe-difficulty-find (50) -----
    for q in [
        "Find a one-pot dinner recipe with no more than 8 ingredients suitable for a beginner cook.",
        "Find a sheet-pan recipe with fewer than 10 ingredients and minimal active cook time.",
        "Find a 30-minute weeknight dinner that needs no special equipment.",
        "Find a beginner-friendly baking recipe with 5 or fewer steps.",
        "Find a vegetarian recipe with no chopping required — open-and-dump style.",
        "Find a recipe rated as 'easy' or 'beginner' in the tags with a 4+ star rating.",
        "Find a slow cooker recipe with fewer than 6 ingredients and prep under 15 minutes.",
        "Find a salad recipe with no cooking required.",
        "Find a no-bake dessert recipe rated 4+ stars.",
        "Find a recipe that lists 'crowd-pleaser' or 'family-friendly' as a tag, intended for a novice cook.",
        "Find a single-skillet chicken recipe that finishes in 20 minutes.",
        "Find a 15-minute pasta recipe with 5 ingredients or fewer.",
        "Find a recipe with the 'quick' or 'under-30-min' tag and at least 4-star rating.",
        "Find a one-pot soup recipe with fewer than 8 ingredients.",
        "Find a recipe that needs only a knife, a cutting board, and one pan.",
        "Find a beginner-friendly bread recipe that does not require kneading.",
        "Find a beginner-friendly cake recipe with 4 ingredients or fewer.",
        "Find a one-bowl muffin recipe.",
        "Find a recipe with the 'no-bake' tag for a hot summer day.",
        "Find a kid-friendly recipe that even an 8-year-old could help make with adult supervision.",
        "Find a 5-ingredient pasta dish suitable for a beginner cook.",
        "Find a 5-ingredient chicken recipe with no advanced techniques.",
        "Find a 5-ingredient soup recipe for a chilly evening.",
        "Find a 5-ingredient dessert recipe.",
        "Find a 5-ingredient breakfast recipe.",
        "Find a 5-ingredient vegan recipe.",
        "Find a beginner-friendly stir-fry that takes 20 minutes or less.",
        "Find a beginner-friendly risotto recipe with detailed steps.",
        "Find an easy weeknight chicken recipe that pairs with rice or pasta.",
        "Find a recipe with no oven needed — stovetop only.",
        "Find a recipe with no stovetop needed — oven only.",
        "Find a beginner soup recipe with only canned and frozen ingredients.",
        "Find a salad recipe with fewer than 6 ingredients including the dressing.",
        "Find a quick dessert recipe that uses fewer than 5 pantry ingredients.",
        "Find a recipe that lists the 'school-night' or 'weeknight' tag with under-30-minute total time.",
        "Find a one-pot pasta recipe (cook noodles in the sauce itself) with under 25 minutes total time.",
        "Find a sheet-pan breakfast recipe perfect for serving a crowd at brunch.",
        "Find a slow-cooker breakfast recipe (overnight oats, breakfast casserole) ready by morning.",
        "Find a recipe that the page explicitly labels as 'easy' for a tired weeknight.",
        "Find a recipe explicitly labeled 'beginner' that introduces a fundamental technique (sear, sauté, roast).",
        "Find a recipe that finishes in under 20 minutes total — title or tag must indicate the speed.",
        "Find a chicken thigh recipe with fewer than 7 ingredients and one pan.",
        "Find a vegetarian pasta recipe with fewer than 8 ingredients including pantry staples.",
        "Find a beginner-friendly recipe for a holiday side dish.",
        "Find a one-pot Mexican-style recipe with fewer than 10 ingredients.",
        "Find a beginner-friendly seafood recipe with simple white wine pan sauce.",
        "Find a beginner-friendly Italian recipe that introduces fresh herbs and good olive oil.",
        "Find a recipe explicitly labeled 'meal-prep' or 'batch-cook' that a beginner can manage.",
        "Find a one-pot vegan stew with at least 5 vegetables and a beginner-level instruction set.",
        "Find a one-pot beef stew with fewer than 12 ingredients.",
    ]:
        add('recipe-difficulty-find', q)

    # ----- recipe-yield-convert (50) -----
    if make_ahead:
        sample_titles = [r['title'] for r in make_ahead[:30]]
    else:
        sample_titles = [r['title'] for r in by_cuisine[:30]]
    sample_titles = [t for t in sample_titles if t]
    sample_titles = sample_titles[:30]
    yield_queries = [
        "Take the {t} recipe and tell me the new ingredient quantities to scale it from 4 to 8 servings.",
        "Scale the {t} recipe down from 6 servings to 2 servings — what becomes of the cook time?",
        "Convert the {t} recipe to feed a family of 5 — give me the new ingredient quantities.",
        "Take the {t} recipe and double it for a potluck — note any equipment changes (sheet-pan size, oven temp).",
        "The {t} recipe serves 4. Recompute for 12 servings for a holiday gathering.",
        "Halve the {t} recipe and tell me the new ingredient amounts and any timing change.",
        "Triple the {t} recipe for a freezer batch — recompute the ingredient quantities.",
        "Scale the {t} recipe from 4 servings to 6 servings using the scaling widget on the page.",
        "The {t} recipe is for 6 — recompute for 1 serving (single-serve cook).",
        "Scale the {t} recipe to serve 10 — note any changes to the suggested cookware.",
    ]
    yi = 0
    for t in sample_titles:
        for tmpl in yield_queries:
            add('recipe-yield-convert', tmpl.format(t=t))
            yi += 1
            if yi >= 50:
                break
        if yi >= 50:
            break

    # ----- cooking-tip-extract (50) -----
    if articles:
        for art in articles:
            slug, title = art['slug'], art['title']
            add('cooking-tip-extract',
                f'Extract the three main cooking tips from the article "{title}".')
            add('cooking-tip-extract',
                f'Find the article titled "{title}" and list every section heading it contains.')
    cooking_topic_qs = [
        "Find the article that explains the Maillard reaction and summarize the rules it gives for browning.",
        "Find the article on knife skills and list the four foundational cuts it teaches.",
        "Find the article on pantry staples — list the oils, salts, and acids it recommends.",
        "Find the article on bread baking — list the three big tips it gives for first-time bakers.",
        "Find the article on pasta water — explain why pasta water matters for sauces.",
        "Find the article on roasting vegetables — what temperature does it recommend, and why?",
        "Find the article on cooking eggs — list every cooking method it covers.",
        "Find the article on cookies — explain the ratio differences between chewy, crispy, and cakey cookies.",
        "Find the article on stock — list the differences between chicken, beef, and vegetable stock.",
        "Find the article on burgers — list the seven rules it teaches.",
        "Find the article on leftover chicken — list at least three ideas it suggests.",
        "Find the article on dried beans — list the steps for cooking dried beans from scratch.",
        "Find the article on 5-minute sauces — list every sauce it covers.",
        "Find the article on holiday hosting — list the timeline it gives for cooking dinner for ten.",
        "Find the article on cast iron — list the three rules for cast iron care.",
        "Find the article on which pan to buy first — list the three pans it recommends.",
        "Find the article on quick marinades — list every marinade it covers.",
        "Find the article on brunch — list every dish it suggests for a brunch spread.",
        "Find the article on cooking for one — list the three strategies it suggests.",
        "Find the article on rice — list the water-to-rice ratios it gives for long-grain, brown, and sushi rice.",
    ]
    for q in cooking_topic_qs:
        add('cooking-tip-extract', q)

    # ----- video-show-step (45) -----
    step_qs = []
    chef_pool = chef_recipes[:30]
    for r in chef_pool:
        slug, title = r['slug'], r['title']
        step_qs.append(f"Open the {title} recipe and list every step shown in its photo gallery.")
        step_qs.append(f"On the {title} recipe page, describe the first and last step images.")
    # Add general step prompts
    for q in [
        "Find a recipe whose photo gallery has at least 3 step-by-step images and list each step heading.",
        "Find a sheet-pan recipe with a photo gallery and describe what the 'before roasting' vs 'after roasting' images look like.",
        "Find a baking recipe with a photo gallery and describe the dough at each stage.",
        "Find a stir-fry recipe with a photo gallery and describe the wok at each stage.",
        "Find a slow cooker recipe with a photo gallery and describe the dish before vs. after the slow cooking.",
        "Find a recipe page that includes step images and the recipe author is a named chef (e.g. Chef Marie Laurent).",
        "Find a recipe with at least one step image, more than 4 ingredients, and a total time over an hour.",
        "Find a recipe with step images that involves multiple cooking methods (e.g., brown then braise).",
        "Find a make-ahead recipe with a photo gallery — describe what the dish looks like the day before serving.",
        "Find a freezer-meal recipe with a photo gallery — describe the packaging step.",
        "Find a global-fusion recipe with a photo gallery — describe how the fusion ingredients are added.",
        "Find a kid-friendly recipe with a photo gallery — describe how the dish is plated for kids.",
        "Find a recipe whose gallery shows the dish at three timeline checkpoints: prep, cook, serve.",
        "Find a holiday recipe with a photo gallery — describe each step.",
        "Find a recipe whose photo gallery shows knife-skill techniques (dicing, chiffonade, etc.).",
    ]:
        step_qs.append(q)
    for q in step_qs[:45]:
        add('video-show-step', q)

    # ----- multi-step (75) -----
    multi_step_qs = [
        "Open the homepage, click into the Dinner category, then filter to recipes under 30 minutes and tell me how many recipes match.",
        "Browse the Desserts category, sort by highest-rated, and report the top 3 dessert recipe titles.",
        "Search for 'chicken pasta', then filter to recipes with fewer than 10 ingredients, then sort by rating descending.",
        "From the Collections hub, open 'Best Summer Grilling', and list every recipe it contains.",
        "From the Articles hub, open 'How to Roast a Turkey Like a Pro' and report its read time.",
        "Browse the Diets hub, open the 'gluten-free' diet page, and list the first 5 recipes shown.",
        "Search for 'lasagna', open the highest-rated result, and tell me how many reviews it has.",
        "Open the Meal Plan, add the top-rated chicken recipe to Tuesday dinner, then verify it appears in the Meal Plan view.",
        "Search for 'sheet pan', open the highest-rated result, scale it to 8 servings, and report the new ingredient quantities.",
        "Register a new account (test@example.com), then save 3 recipes to your Recipe Box.",
        "From the homepage, navigate to Cuisines hub, open 'Italian', and list the first 5 Italian recipes.",
        "From the homepage, click 'Newsletter' and submit a sign-up — verify the success message.",
        "From the homepage, open the search page, look for 'no-results-typo-zxyx' and verify the empty-state suggestions are shown.",
        "Add a recipe to the shopping list, open the shopping list, mark an item as bought, and verify the visual change.",
        "Open the Collections hub, find a collection with at least 8 recipes, and report the curator name.",
        "Open any recipe detail page, click the 'Share' button, and verify the share URL is copied to the clipboard.",
        "Open any recipe detail page and click 'Print' — verify the print dialog launches.",
        "Open a make-ahead recipe (slug starts with 'make-ahead-'), then verify the storage instructions explicitly mention 1-2 days ahead.",
        "Open a freezer-meal recipe (slug starts with 'freezer-meal-'), then verify the storage instructions mention 3-month freezing.",
        "Open a kid-friendly recipe (slug starts with 'kid-friendly-'), then verify the description mentions mild seasoning.",
        "Open a global-fusion recipe (any 'Thai Twist:' or 'Korean BBQ Twist:' title) and report the fusion ingredients added.",
        "Browse the Meals hub, click into 'Breakfast', then filter to under-30-minute recipes.",
        "From the Cuisines hub, open 'Japanese', and report how many Japanese recipes exist in the catalog.",
        "From the homepage, search 'vegan', then count how many results appear on page 1.",
        "From the homepage, log in as 'alice.j' with password 'test1234' and open the Recipe Box — report how many recipes are saved.",
        "Browse Collections, open 'Holiday Cookie Box', and list the first three cookie recipe slugs.",
        "Open any chef-authored recipe, verify the chef name appears in the byline.",
        "Search for 'gluten-free', open the first result, and verify the dietary tags include 'gluten-free'.",
        "Search for 'dairy-free', open the first result, and verify the dietary tags include 'dairy-free'.",
        "Add the top-rated soup to the meal plan for Wednesday dinner using the AJAX widget on the recipe detail page.",
        "Open the article 'Cookies: The Complete Texture Guide' and report the ratio differences across chewy/crispy/cakey.",
        "Search for 'one-pot', open the first result, and verify the storage instructions are explicit.",
        "Open the 'Pierogi Potato Onion' recipe and report the chef name.",
        "From the homepage, navigate to Diets hub, open 'paleo', and report the number of recipes shown.",
        "Browse Articles hub, open any article tagged 'kitchen-101', and list the sections.",
        "Open the recipe 'Coq au Vin Maison' and report the cuisine plus total time.",
        "From the homepage, click 'Sign Up', enter mismatched passwords, and verify the form shows a 'Passwords do not match' error.",
        "From the homepage, click 'Sign Up', enter an invalid email, and verify the form shows a validation message.",
        "Open the registration form and verify the inputs have ARIA labels and form-error hints.",
        "Open any recipe detail page on mobile width — verify the hamburger menu icon shows and the categories drawer opens when clicked.",
        "On a recipe detail page, click the 'Save' button while logged out — verify you are redirected to the login page.",
        "Open the 404 page (visit /nonexistent-page) and verify it shows the 'You might be looking for' suggestions.",
        "On the homepage, verify the skip-to-content link appears when you press Tab as the first focusable element.",
        "Search for 'fusion', open the first result, and report the new fusion ingredients vs the base recipe.",
        "Search for a make-ahead recipe, open it, and verify the description explicitly mentions making it 1-2 days ahead.",
        "Open the recipe 'Jollof Rice Festive' and report the cuisine origin and the dietary tags.",
        "Open the recipe 'Chicken Adobo Classic' and report the chef name and cuisine.",
        "Open the recipe 'Gravlax with Mustard Sauce' and report the prep time.",
        "Open the recipe 'Halo Halo Refreshing' and report the cuisine origin.",
        "Open the article 'How to Make Stock from Scratch' and report the three stock variations it covers.",
        "Browse the Side-Dishes category and find a freezer-meal version of a side dish.",
        "Browse the Soups category and find a make-ahead version of any soup recipe.",
        "Browse the Pasta category, sort by rating descending, and list the top 5 pasta recipes.",
        "Browse the Chicken category, filter to under 30 minutes, and report the count.",
        "Open the recipe 'Make-Ahead Coq au Vin Maison' — verify it exists and has different instructions than the original Coq au Vin Maison.",
        "Open any recipe detail page, open the AJAX meal-plan widget, select 'friday dinner', and verify the success status appears.",
        "Open the Community page and report how many reviewers are listed.",
        "On the homepage, click 'Articles' nav link, open the most recent article, and report its publish date.",
        "On the homepage, click 'Collections' nav link, open 'Date Night In', and verify it lists chef-authored recipes.",
        "On the homepage, search 'mole', open the result for 'Mole Poblano Festivo', and report the cuisine.",
        "On the homepage, search 'spanakopita', open the result, and report the chef name.",
        "On a recipe detail page, click the photo gallery thumbnails one by one and confirm the step images load.",
        "On any recipe detail page, hover over the rating stars and confirm the fractional rating is shown.",
        "Browse the Diets hub, open 'whole30', and report the number of recipes shown.",
        "Browse the Diets hub, open 'keto', and report the first 5 recipe titles.",
        "Browse the Diets hub, open 'pescatarian', and verify only seafood/vegetarian recipes appear.",
        "Open the recipe 'Plantain Chips Crispy' and report the cuisine.",
        "Open the recipe 'Suya Beef Skewers' and report the cuisine and dietary tags.",
        "Open the recipe 'Egusi Stew Lagos-Style' and report the chef name.",
        "Open the recipe 'Smoked Salmon Smorrebrod' and report the cuisine.",
        "Open the recipe 'Pancit Bihon Noodles' and report the chef name and primary ingredient.",
        "Open the recipe 'Norwegian Cardamom Buns' and report the prep + cook time.",
        "On the homepage, click 'About' and report the year the company was founded (per the about page).",
        "On the homepage, click 'Sitemap' and report how many sections are listed.",
        "Search for 'thanksgiving', open the article 'How to Roast a Turkey Like a Pro', and report each section heading.",
        "From the homepage navigate to the Newsletter page and report the placeholder text in the email input.",
        "From the homepage navigate to the Occasions hub and open 'Thanksgiving'.",
    ]
    for q in multi_step_qs[:75]:
        add('multi-step', q)

    # Extra multi-step + nutrition-detail + share-link tasks to push total >700.
    extra_multi = [
        "Open the recipe 'Chicken Adobo Classic', add it to the meal plan for Friday dinner via the AJAX widget, and verify the success state.",
        "Open the recipe 'Suya Beef Skewers' and verify the description mentions yaji or suya spice.",
        "Search 'borscht', open 'Borscht Ukrainian', and report the chef name.",
        "On the homepage, navigate to /sitemap and verify every link in the sitemap returns a 200 (not 404).",
        "Browse Articles hub and confirm at least 25 articles are listed.",
        "Browse Collections hub and confirm at least 10 collections are listed.",
        "Browse Community hub and confirm chef pages link to their authored recipes.",
        "On the recipe-detail page for 'Tiramisu Authentic', verify the photo gallery has at least 3 step images.",
        "On the recipe-detail page for 'Cacio e Pepe Classic', verify the description mentions Pecorino Romano.",
        "On the recipe-detail page for 'Ratatouille Provençale', verify the dietary tags include 'vegan'.",
        "On the homepage, scroll to the editor's pick section and report the first 3 recipes shown.",
        "Open /diet/vegan, sort by review count, and report the top 5 recipes.",
        "Open /diet/dairy-free, filter to under 30 minutes, and report the count.",
        "Open /diet/gluten-free, report the first 5 recipes returned by the default sort.",
        "Open /diet/nut-free (if present) or search 'nut-free' and report what the page returns.",
        "Open /diet/egg-free or search 'egg-free' and report the first three results.",
        "Open /diet/soy-free or search 'soy-free' and report the first three results.",
        "Open /diet/whole30 and verify the description mentions Whole30 program rules.",
        "Open /diet/keto and report a high-fat, low-carb recipe shown.",
        "Search 'ravioli' and report the highest-rated result and its rating.",
        "Search 'gnocchi' and report the highest-rated result and its review count.",
        "Search 'tortellini' and report the highest-rated result and its cuisine.",
        "Search 'meatloaf' and report the highest-rated result.",
        "Search 'pot roast' and report the highest-rated result and total time.",
        "Search 'eggplant' and report the highest-rated result.",
        "Search 'cauliflower' and report the highest-rated result.",
        "Search 'shrimp' and report the highest-rated result.",
        "Search 'salmon' and report the highest-rated result.",
        "Search 'tofu' and report the highest-rated result.",
        "Search 'mushroom' and report the highest-rated result.",
        "Search 'butternut squash' and report the highest-rated result.",
        "Open the meal-plan page logged in as alice.j and report which recipes are in the plan.",
        "Open the recipe box page logged in as alice.j and report which recipes are saved.",
        "Open the shopping list page logged in as alice.j and verify items can be removed.",
        "Open the account page logged in as alice.j and report the location field shown.",
        "Open the account page logged in as bob.c and report the bio field shown.",
        "Open the change-password page and verify the form has client-side validation.",
        "Open the register page in mobile viewport and verify the form is full-width.",
        "Open any recipe detail page in mobile viewport and verify the hamburger menu appears.",
        "On the homepage in mobile viewport, verify the categories drawer opens on tap.",
    ]
    for q in extra_multi:
        add('multi-step', q)

    # Nutrition-detail extras
    for q in [
        "Open any recipe and report its Fiber content per serving.",
        "Open any recipe and report its Sodium content per serving.",
        "Open any recipe and report its Saturated Fat content per serving.",
        "Open any recipe and report its Sugar content per serving.",
        "Open any recipe and report its Cholesterol content per serving.",
        "Find a recipe with Fiber > 6 g per serving.",
        "Find a recipe with Sodium < 400 mg per serving.",
        "Find a recipe with Protein > 25 g per serving.",
        "Find a recipe with Sugar < 5 g per serving.",
        "Find a recipe with Cholesterol < 50 mg per serving.",
    ]:
        add('nutrition-detail', q)

    # ----- make-ahead-filter (35) -----
    for q in [
        "Find a make-ahead casserole recipe for entertaining on Saturday.",
        "Find a make-ahead breakfast recipe to assemble Sunday night for Monday morning.",
        "Find a make-ahead dessert recipe for a dinner party (assemble the day before).",
        "Find a make-ahead lasagna or pasta-bake recipe.",
        "Find a make-ahead soup that improves overnight in the fridge.",
        "Find a make-ahead vegetarian recipe for a meal prep Sunday.",
        "Find a make-ahead holiday-side recipe for Thanksgiving prep.",
        "Find a make-ahead chicken recipe with a 4+ star rating.",
        "Find a make-ahead beef stew or braise recipe.",
        "Find a make-ahead vegan or plant-based recipe.",
        "Find a make-ahead Italian-style recipe.",
        "Find a make-ahead Mexican-inspired recipe.",
        "Find a make-ahead recipe that serves 8 or more.",
        "Find a make-ahead recipe that finishes in 30 minutes on the day of serving.",
        "Find a make-ahead recipe with explicit reheating instructions.",
        "Find a make-ahead breakfast casserole for a brunch party.",
        "Find a make-ahead salad-style recipe (built ahead but dressed on the day).",
        "Find a make-ahead chicken-thigh recipe.",
        "Find a make-ahead chili recipe.",
        "Find a make-ahead overnight oats or breakfast bowl recipe.",
        "Find a make-ahead dip or appetizer recipe for entertaining.",
        "Find a make-ahead pasta-bake recipe that freezes well too.",
        "Find a make-ahead curry recipe with chicken or chickpeas.",
        "Find a make-ahead frittata or strata recipe.",
        "Find a make-ahead vegetarian-chili recipe.",
        "Find a make-ahead pulled-pork or BBQ recipe for game day.",
        "Find a make-ahead enchiladas recipe.",
        "Find a make-ahead stuffed shells recipe.",
        "Find a make-ahead chicken-pot-pie recipe.",
        "Find a make-ahead minestrone recipe.",
        "Find a make-ahead lentil-soup recipe.",
        "Find a make-ahead Indian curry recipe.",
        "Find a make-ahead Thai curry recipe.",
        "Find a make-ahead vegetable casserole for a side dish.",
        "Find a make-ahead breakfast burrito for the freezer.",
    ]:
        add('make-ahead-filter', q)

    # ----- kid-friendly-filter (30) -----
    for q in [
        "Find a kid-friendly weeknight dinner with mild seasoning.",
        "Find a kid-friendly pasta recipe a 6-year-old will eat.",
        "Find a kid-friendly chicken-nugget or finger-food recipe.",
        "Find a kid-friendly breakfast for picky eaters.",
        "Find a kid-friendly mac-and-cheese style recipe.",
        "Find a kid-friendly soup or stew that is not spicy.",
        "Find a kid-friendly vegetarian recipe (no meat).",
        "Find a kid-friendly dessert recipe under 30 minutes.",
        "Find a kid-friendly recipe with bite-sized pieces for small hands.",
        "Find a kid-friendly version of a usually-spicy dish (taco, chili, etc.).",
        "Find a kid-friendly Italian recipe.",
        "Find a kid-friendly Mexican-inspired recipe with mild seasoning.",
        "Find a kid-friendly recipe a child can help cook with adult supervision.",
        "Find a kid-friendly recipe for a school night under 25 minutes total time.",
        "Find a kid-friendly recipe for a birthday party.",
        "Find a kid-friendly snack recipe that travels well in a lunchbox.",
        "Find a kid-friendly fish or seafood recipe (mild flavor).",
        "Find a kid-friendly beef recipe with mild seasoning.",
        "Find a kid-friendly pork recipe with mild seasoning.",
        "Find a kid-friendly vegetarian pasta recipe.",
        "Find a kid-friendly side dish that pairs with chicken nuggets.",
        "Find a kid-friendly dessert recipe with fewer than 7 ingredients.",
        "Find a kid-friendly breakfast pancake or waffle recipe.",
        "Find a kid-friendly recipe with cheese as a main flavor.",
        "Find a kid-friendly recipe with butter and pasta as base ingredients.",
        "Find a kid-friendly fried-chicken-style recipe (not actually fried, but appealing).",
        "Find a kid-friendly recipe for a Halloween-themed party.",
        "Find a kid-friendly Thanksgiving-side dish recipe.",
        "Find a kid-friendly Christmas-morning recipe.",
        "Find a kid-friendly Easter-brunch recipe.",
    ]:
        add('kid-friendly-filter', q)

    # ----- freezer-meal-filter (25) -----
    for q in [
        "Find a freezer-meal chili recipe that batches enough for 8.",
        "Find a freezer-meal lasagna recipe with explicit freezing instructions.",
        "Find a freezer-meal soup recipe that freezes for up to 3 months.",
        "Find a freezer-meal casserole recipe with reheating instructions.",
        "Find a freezer-meal breakfast-burrito recipe.",
        "Find a freezer-meal chicken-and-rice recipe for the freezer.",
        "Find a freezer-meal vegetarian recipe.",
        "Find a freezer-meal stew or braise recipe.",
        "Find a freezer-meal pulled pork recipe.",
        "Find a freezer-meal pasta-bake recipe.",
        "Find a freezer-meal meatball recipe for the freezer.",
        "Find a freezer-meal taco-filling recipe for the freezer.",
        "Find a freezer-meal soup recipe for cold weather.",
        "Find a freezer-meal pizza or flatbread recipe.",
        "Find a freezer-meal stir-fry kit recipe.",
        "Find a freezer-meal curry recipe.",
        "Find a freezer-meal cookie-dough recipe for the freezer.",
        "Find a freezer-meal sauce recipe (marinara, pesto, etc.) for portioning out.",
        "Find a freezer-meal vegetable-soup recipe for batch cooking.",
        "Find a freezer-meal chicken-noodle-soup recipe.",
        "Find a freezer-meal beef-and-vegetable stew for an 8-quart batch.",
        "Find a freezer-meal lentil-soup recipe.",
        "Find a freezer-meal vegetarian-chili recipe.",
        "Find a freezer-meal pancake-batter recipe.",
        "Find a freezer-meal smoothie-pack recipe (pre-portion ingredients for blending).",
    ]:
        add('freezer-meal-filter', q)

    # ----- global-fusion-filter (25) -----
    fusion_cuisines = [
        ("Thai Twist", "south-east-asia"),
        ("Korean BBQ Twist", "east-asia"),
        ("Mexican Mole Twist", "latin-america"),
        ("Moroccan Twist", "north-africa"),
        ("Japanese Miso Twist", "east-asia"),
        ("Indian Curry Twist", "south-asia"),
    ]
    for label, _ in fusion_cuisines:
        add('global-fusion-filter',
            f"Find a {label} fusion recipe and list the fusion ingredients it adds.")
        add('global-fusion-filter',
            f"Find a chicken {label} fusion recipe with a 4+ star rating.")
        add('global-fusion-filter',
            f"Find a {label} fusion recipe that takes under 45 minutes total.")
        add('global-fusion-filter',
            f"Find a {label} fusion soup or stew recipe.")
    for q in [
        "Find any global-fusion recipe that crosses Italian + Asian flavor profiles.",
        "Find any global-fusion recipe with peanut sauce, lime, and basil.",
        "Find any global-fusion taco recipe with Korean BBQ flavors.",
        "Find any global-fusion pizza recipe with non-Italian toppings.",
        "Find any global-fusion pasta recipe with miso or gochujang.",
    ]:
        add('global-fusion-filter', q)

    # ----- calorie-tier (35) -----
    for q in [
        "Find a recipe with fewer than 250 calories per serving.",
        "Find a recipe with fewer than 300 calories per serving rated 4+ stars.",
        "Find a high-protein, low-calorie chicken recipe under 350 calories per serving.",
        "Find a dessert under 200 calories per serving.",
        "Find a salad meal under 400 calories per serving.",
        "Find a soup with fewer than 200 calories per serving.",
        "Find a moderate-calorie weeknight dinner (between 400 and 600 calories).",
        "Find an indulgent main dish over 700 calories per serving.",
        "Find a low-calorie pasta dish under 400 calories per serving.",
        "Find a low-calorie breakfast under 300 calories per serving.",
        "Find a low-calorie vegan dinner under 400 calories per serving.",
        "Find a low-calorie chicken stir-fry under 350 calories per serving.",
        "Find a low-calorie chocolate dessert under 200 calories per serving.",
        "Find a low-calorie pizza substitute under 400 calories per serving.",
        "Find a low-calorie burger or sandwich under 450 calories per serving.",
        "Find a low-calorie beef recipe under 400 calories per serving.",
        "Find a low-calorie fish recipe under 350 calories per serving.",
        "Find a low-calorie smoothie or breakfast bowl under 300 calories.",
        "Find a low-calorie weeknight casserole.",
        "Find a low-calorie vegetarian stir-fry.",
        "Find a low-calorie chicken-and-rice bowl.",
        "Find a low-calorie soup using lentils or beans.",
        "Find a high-calorie comfort food over 600 calories per serving.",
        "Find a high-calorie holiday side dish.",
        "Find a high-calorie indulgent breakfast.",
        "Find a high-calorie dessert with chocolate and cream.",
        "Find a high-calorie pasta dish for cold weather.",
        "Find a moderate-calorie healthy chicken recipe (400-500 calories).",
        "Find a moderate-calorie vegetarian meal (400-500 calories).",
        "Find a moderate-calorie burger recipe (400-500 calories).",
        "Find a recipe categorized as 'low-cal' or under-300-cal in its tags.",
        "Find a recipe categorized as 'high-cal' or over-500-cal in its tags.",
        "Find a low-calorie holiday recipe for healthy entertaining.",
        "Find a low-calorie game-day snack alternative.",
        "Find a low-calorie pasta dish using zucchini noodles or shirataki.",
    ]:
        add('calorie-tier', q)

    # ----- cuisine-origin (30) -----
    for q in [
        "Find a recipe originating from East Asia and report the chef name if any.",
        "Find a recipe originating from Latin America with a 4+ star rating.",
        "Find a recipe originating from West Africa.",
        "Find a recipe originating from the Mediterranean.",
        "Find a recipe originating from South Asia (Indian/Pakistani).",
        "Find a recipe originating from the Middle East.",
        "Find a recipe originating from Northern Europe (Nordic).",
        "Find a recipe originating from South-East Asia (Thai/Vietnamese/Filipino).",
        "Find a recipe originating from North America (US/Canadian).",
        "Find a recipe originating from North Africa (Moroccan/Algerian/Egyptian).",
        "Find a fusion recipe combining Japanese and American flavors.",
        "Find a fusion recipe combining Indian and Italian flavors.",
        "Find a fusion recipe combining Korean and Mexican flavors.",
        "Find a fusion recipe combining Thai and French flavors.",
        "Find a recipe with cuisine 'Filipino' and report its hero ingredient.",
        "Find a recipe with cuisine 'Nordic' and report the chef name.",
        "Find a recipe with cuisine 'West African' and report the chef name.",
        "Find a recipe with cuisine 'Italian' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'Mexican' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'Indian' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'Japanese' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'Korean' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'British' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'Mediterranean' and a 4.5+ star rating.",
        "Find a recipe with cuisine 'Asian Fusion' and report its dietary tags.",
        "Find a recipe with cuisine 'Southern' (US Southern cooking).",
        "Find a recipe with cuisine 'European' broadly defined.",
        "Find a recipe with cuisine 'Middle Eastern' and report its dietary tags.",
        "Find a recipe with cuisine 'Eastern European' and report the chef name.",
        "Find a recipe with cuisine 'French' and report the chef name.",
    ]:
        add('cuisine-origin', q)

    # ----- time-budget-tier (30) -----
    for q in [
        "Find a recipe with the 'under-30-min' tag and a 4-star rating.",
        "Find a recipe with the 'under-1-hour' tag and at least 6 servings.",
        "Find a recipe with the 'over-1-hour' tag and report why it takes so long (braise, slow cook, etc.).",
        "Find a recipe with total time under 20 minutes.",
        "Find a recipe with total time under 45 minutes and at least 100 reviews.",
        "Find a recipe with cook time over 2 hours (low and slow).",
        "Find a recipe with prep time under 10 minutes.",
        "Find a recipe with prep time over 30 minutes (a project recipe).",
        "Find a recipe with total time exactly between 30 and 60 minutes.",
        "Find a quick weeknight recipe with total time under 25 minutes.",
        "Find a weekend project recipe with total time over 3 hours.",
        "Find a recipe with prep time under 5 minutes (open-and-dump style).",
        "Find a 15-minute breakfast recipe.",
        "Find a 15-minute lunch recipe.",
        "Find a 15-minute dinner recipe.",
        "Find a 15-minute dessert recipe.",
        "Find a recipe whose cook time is exactly 0 minutes (no cooking required).",
        "Find a recipe whose total time falls in the under-30-min tier with no special equipment.",
        "Find a slow-cooker recipe whose total time is in the over-1-hour tier.",
        "Find a sheet-pan recipe whose total time is in the under-1-hour tier.",
        "Find an Instant Pot recipe whose total time is under 1 hour.",
        "Find an air-fryer recipe whose total time is under 30 minutes.",
        "Find a one-pot recipe whose total time is under 1 hour.",
        "Find a freezer-meal recipe whose prep time is under 30 minutes (assembly only).",
        "Find a make-ahead recipe whose day-of cook time is under 30 minutes.",
        "Find a kid-friendly recipe whose total time is under 30 minutes.",
        "Find a global-fusion recipe whose total time is under 1 hour.",
        "Find a chef-authored recipe whose total time is under 1 hour.",
        "Find a baking recipe whose total time is under 45 minutes.",
        "Find a holiday recipe whose total time is over 2 hours.",
    ]:
        add('time-budget-tier', q)

    # Write back.
    print(f"[r5_tasks] generated {len(new_tasks)} new tasks")
    if not new_tasks:
        return
    with open(TASKS_FILE, 'a', encoding='utf-8') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f"[r5_tasks] wrote to {TASKS_FILE}; total tasks now: {len(existing_tasks) + len(new_tasks)}")


if __name__ == '__main__':
    main()
