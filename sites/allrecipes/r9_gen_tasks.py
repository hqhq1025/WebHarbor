#!/usr/bin/env python3
"""R9 task generator — extends ``tasks.jsonl`` with ~600+ new tasks covering
the R9 polish surface: video tutorial pages, print views, deep nutrition
detail, allergen cross-reference, URL-based recipe import, social-share
links (Pinterest/Twitter/Facebook), AI pantry-suggest, recipe version
history, regional-cuisine filters (Indian/MiddleEastern/Caribbean/African)
plus cross-feature multi-step flows.

Idempotent.

Task types added:
  * video-tutorial-watch
  * recipe-print-page
  * nutrition-detail-deep
  * allergen-cross-reference
  * recipe-import-from-URL
  * share-to-pinterest
  * share-to-twitter
  * share-to-facebook
  * AI-recipe-suggest-from-pantry
  * recipe-versioning
  * indian-regional-filter
  * middle-eastern-regional-filter
  * caribbean-regional-filter
  * african-regional-filter
  * multi-step (R9 cross-page flows)
"""
from __future__ import annotations

import json
import os
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
    print(f"[r9_tasks] loaded {len(existing_tasks)} existing tasks")

    conn = sqlite3.connect(SEED_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # R9 regional variant subsets
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Indian-Regional Test Kitchen' "
                "ORDER BY id LIMIT 70")
    indian = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='MiddleEastern-Regional Test Kitchen' "
                "ORDER BY id LIMIT 70")
    mideast = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Caribbean-Regional Test Kitchen' "
                "ORDER BY id LIMIT 70")
    caribbean = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='African-Regional Test Kitchen' "
                "ORDER BY id LIMIT 70")
    african = cur.fetchall()
    # R9 chefs
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name IN ('Chef Vikram Singh','Chef Ayesha Khoury',"
                "'Chef Marcus Boateng','Chef Lourdes Castillo') "
                "ORDER BY id")
    chefs = cur.fetchall()
    # General popular recipes (reused across many task types).
    cur.execute("SELECT slug, title, cuisine, total_time_mins, avg_rating "
                "FROM recipe WHERE review_count >= 5 ORDER BY id LIMIT 200")
    popular = cur.fetchall()
    conn.close()

    new_tasks = []
    n = 0
    while f"Allrecipes--R9--{n}" in existing_ids:
        n += 1

    def add(task_type, ques):
        nonlocal n
        tid = f"Allrecipes--R9--{n}"
        while tid in existing_ids:
            n += 1
            tid = f"Allrecipes--R9--{n}"
        existing_ids.add(tid)
        new_tasks.append(make_task(tid, task_type, ques))
        n += 1

    # ============================================================
    # 1) video-tutorial-watch (~60)
    # ============================================================
    for r in popular[:40]:
        add('video-tutorial-watch',
            f"Open /recipe/{r['slug']}/video on Allrecipes. Find the total "
            f"video length (in seconds) shown next to the video stub and report it.")
    for r in popular[40:60]:
        add('video-tutorial-watch',
            f"Open /recipe/{r['slug']}/video on Allrecipes. Find the chapters "
            f"list and report the 'duration_seconds' value of the FIRST chapter.")
    add('video-tutorial-watch',
        "Open /recipe/butter-chicken-murgh-makhani/video on Allrecipes. Count "
        "how many chapter items appear in the chapter list and report the number.")
    add('video-tutorial-watch',
        "Open /recipe/jamaican-jerk-chicken/video on Allrecipes. Report the "
        "title text of the LAST chapter shown.")

    # ============================================================
    # 2) recipe-print-page (~60)
    # ============================================================
    for r in popular[:40]:
        add('recipe-print-page',
            f"Open /recipe/{r['slug']}/print on Allrecipes. Confirm the page "
            f"has a 'Print this page' button and report the recipe's listed "
            f"servings count from the meta row.")
    for r in popular[40:55]:
        add('recipe-print-page',
            f"Open /recipe/{r['slug']}/print on Allrecipes. Count the number "
            f"of <li> ingredient items shown in the print view ingredient list.")
    add('recipe-print-page',
        "Open /recipe/moroccan-lamb-tagine-apricots/print on Allrecipes. "
        "Report the recipe author shown at the bottom of the print page.")
    add('recipe-print-page',
        "Open /recipe/croissant-classic/print on Allrecipes. Confirm there is "
        "a 'Back to recipe' link and report its href.")
    add('recipe-print-page',
        "Open /recipe/butter-chicken-murgh-makhani/print on Allrecipes. "
        "Confirm the page has CSS @media print rules that hide the site header.")

    # ============================================================
    # 3) nutrition-detail-deep (~60)
    # ============================================================
    for r in popular[:30]:
        add('nutrition-detail-deep',
            f"Open /recipe/{r['slug']}/nutrition on Allrecipes. Report the "
            f"value of the 'Sodium' row (mg per serving) from the nutrition table.")
    for r in popular[30:55]:
        add('nutrition-detail-deep',
            f"Open /recipe/{r['slug']}/nutrition on Allrecipes. Report the "
            f"% Daily Value shown for 'Total Carbs'.")
    add('nutrition-detail-deep',
        "Open /recipe/jamaican-jerk-chicken/nutrition on Allrecipes. Find the "
        "'Iron' row and report the mg value AND the %DV side-by-side.")
    add('nutrition-detail-deep',
        "Open /recipe/butter-chicken-murgh-makhani/nutrition on Allrecipes. "
        "Confirm the table includes Vitamin A and Vitamin C rows.")
    add('nutrition-detail-deep',
        "Open /recipe/persian-fesenjan/nutrition on Allrecipes. Report the "
        "serving size note shown at the bottom of the table.")

    # ============================================================
    # 4) allergen-cross-reference (~60)
    # ============================================================
    for r in popular[:30]:
        add('allergen-cross-reference',
            f"Open /recipe/{r['slug']}/allergens on Allrecipes. Find the row "
            f"for 'wheat' and report whether it shows 'Yes' or 'No'.")
    for r in popular[30:55]:
        add('allergen-cross-reference',
            f"Open /recipe/{r['slug']}/allergens on Allrecipes. Find the row "
            f"for 'milk' and report the suggested substitution if present.")
    add('allergen-cross-reference',
        "Open /recipe/jamaican-jerk-chicken/allergens on Allrecipes. Count how "
        "many of the 9 FDA major allergens are present in this recipe.")
    add('allergen-cross-reference',
        "Open /recipe/persian-fesenjan/allergens on Allrecipes. Report the "
        "ingredient evidence shown for 'tree-nuts'.")
    add('allergen-cross-reference',
        "Open /recipe/croissant-classic/allergens on Allrecipes. Confirm the "
        "milk and wheat rows both show 'Yes'.")
    add('allergen-cross-reference',
        "Open /recipe/lebanese-tabbouleh/allergens on Allrecipes. Report the "
        "header text shown for the cross-reference table.")

    # ============================================================
    # 5) recipe-import-from-URL (~40)
    # ============================================================
    add('recipe-import-from-URL',
        "Open /recipe/import-url on Allrecipes. Confirm the page renders with "
        "a form input named 'url' and a submit button labelled 'Import'.")
    add('recipe-import-from-URL',
        "Open /recipe/import-url on Allrecipes. Read the 'Import pipeline' "
        "section and list the 4 numbered steps in order.")
    for example_url in [
        'https://www.seriouseats.com/perfect-pan-pizza-recipe',
        'https://cooking.nytimes.com/recipes/spicy-coconut-pumpkin-pie',
        'https://smittenkitchen.com/easiest-fudgy-brownies',
        'https://www.bbcgoodfood.com/recipes/chicken-tikka-masala',
        'https://www.bonappetit.com/recipe/bas-best-chocolate-chip-cookies',
        'https://www.foodnetwork.com/recipes/garlic-shrimp-pasta',
        'https://www.epicurious.com/recipes/food/views/cacio-e-pepe',
        'https://www.simplyrecipes.com/the-best-burgers',
        'https://www.themediterraneandish.com/easy-shakshuka',
        'https://www.recipetineats.com/butter-chicken/',
    ]:
        add('recipe-import-from-URL',
            f"POST a JSON body {{\"url\": \"{example_url}\"}} to /recipe/import-url "
            f"on Allrecipes. Report the value of the 'slug' field in the response.")
        add('recipe-import-from-URL',
            f"POST a JSON body {{\"url\": \"{example_url}\"}} to /recipe/import-url "
            f"on Allrecipes. Report the 'confidence' score in the response.")
    add('recipe-import-from-URL',
        "POST {} (empty JSON body) to /recipe/import-url on Allrecipes. Confirm "
        "the response has HTTP status 400 and an 'error' field naming the missing key.")
    add('recipe-import-from-URL',
        "POST a JSON body to /recipe/import-url with url='https://example.com/'. "
        "Report the recipeYield in the response.")
    add('recipe-import-from-URL',
        "POST {\"url\": \"https://www.allrecipes.com/recipe/some-test\"} to "
        "/recipe/import-url. Report the prepTime ISO duration in the response.")
    add('recipe-import-from-URL',
        "Open /recipe/import-url on Allrecipes. Find the 'Example POST body' "
        "code block and report the example URL it shows.")
    add('recipe-import-from-URL',
        "Open /recipe/import-url. Find the link to the OCR import example and "
        "report the recipe slug it links to.")

    # ============================================================
    # 6) share-to-pinterest / twitter / facebook (~80)
    # ============================================================
    for r in popular[:20]:
        add('share-to-pinterest',
            f"Open /recipe/{r['slug']}/share/pinterest on Allrecipes. Report "
            f"the value of the pre-built Pinterest share URL shown on the page.")
    for r in popular[:20]:
        add('share-to-twitter',
            f"Open /recipe/{r['slug']}/share/twitter on Allrecipes. Report the "
            f"value of the 'via' parameter in the Twitter share URL.")
    for r in popular[:20]:
        add('share-to-facebook',
            f"Open /recipe/{r['slug']}/share/facebook on Allrecipes. Find the "
            f"Facebook share URL and report the path of its target endpoint.")
    add('share-to-pinterest',
        "GET /recipe/jamaican-jerk-chicken/share/pinterest?go=1 on Allrecipes. "
        "Confirm the response is a 302 redirect and report the Location header.")
    add('share-to-twitter',
        "GET /recipe/butter-chicken-murgh-makhani/share/twitter?go=1 on "
        "Allrecipes. Confirm the response 302-redirects to twitter.com/intent/tweet.")
    add('share-to-facebook',
        "GET /recipe/croissant-classic/share/facebook?go=1 on Allrecipes. "
        "Confirm the redirect target host is facebook.com.")
    for r in chefs[:10]:
        add('share-to-pinterest',
            f"Open /recipe/{r['slug']}/share/pinterest. Confirm the page lists "
            f"the canonical URL containing '/recipe/{r['slug']}'.")
    for r in chefs[:10]:
        add('share-to-twitter',
            f"Open /recipe/{r['slug']}/share/twitter. Confirm the page lists "
            f"the platform name 'twitter' in the share-platform field.")
    for r in chefs[:10]:
        add('share-to-facebook',
            f"Open /recipe/{r['slug']}/share/facebook. Confirm the page lists "
            f"the platform name 'facebook' in the share-platform field.")

    # ============================================================
    # 7) AI-recipe-suggest-from-pantry (~40)
    # ============================================================
    pantry_lists = [
        ['chicken', 'rice', 'onion'],
        ['flour', 'butter', 'sugar', 'egg'],
        ['tomato', 'pasta', 'garlic'],
        ['salmon', 'lemon', 'dill'],
        ['tofu', 'soy', 'ginger'],
        ['lamb', 'cumin', 'yogurt'],
        ['beef', 'mushroom', 'cream'],
        ['shrimp', 'lime', 'cilantro'],
        ['chickpea', 'tahini', 'lemon'],
        ['plantain', 'coconut', 'thyme'],
        ['lentil', 'curry', 'spinach'],
        ['paneer', 'tomato', 'cream'],
        ['phyllo', 'butter', 'honey'],
        ['couscous', 'apricot', 'almond'],
        ['cornmeal', 'okra', 'fish'],
    ]
    for items in pantry_lists:
        items_str = ','.join(items)
        add('AI-recipe-suggest-from-pantry',
            f"GET /api/ai-suggest?pantry={items_str} on Allrecipes. Report the "
            f"'total' field of the response.")
        add('AI-recipe-suggest-from-pantry',
            f"POST {{\"pantry\": {json.dumps(items)}}} to /api/ai-suggest on "
            f"Allrecipes. Report the slug of the FIRST recipe in 'results'.")
    add('AI-recipe-suggest-from-pantry',
        "POST {} (empty body) to /api/ai-suggest on Allrecipes. Confirm the "
        "response includes a 'note' field telling the caller to provide a "
        "non-empty pantry list.")
    add('AI-recipe-suggest-from-pantry',
        "GET /api/ai-suggest?pantry=chicken,rice,onion&limit=3 on Allrecipes. "
        "Confirm at most 3 results are returned.")
    add('AI-recipe-suggest-from-pantry',
        "GET /api/ai-suggest?pantry=butter on Allrecipes. Report the value of "
        "'pantry_match_ratio' on the first result (should be 1.0).")
    add('AI-recipe-suggest-from-pantry',
        "POST {\"pantry\": [\"chicken\", \"yogurt\", \"garam masala\"]} to "
        "/api/ai-suggest. Confirm an Indian regional recipe appears in the "
        "top results.")
    add('AI-recipe-suggest-from-pantry',
        "GET /api/ai-suggest?pantry=phyllo,butter,honey on Allrecipes. Confirm "
        "the response has a 'format' field equal to 'allrecipes.ai-suggest'.")
    add('AI-recipe-suggest-from-pantry',
        "GET /api/ai-suggest?pantry=salmon,dill on Allrecipes. Report the "
        "schema_version field of the response.")

    # ============================================================
    # 8) recipe-versioning (~50)
    # ============================================================
    for r in popular[:30]:
        add('recipe-versioning',
            f"Open /recipe/{r['slug']}/versions on Allrecipes. Count how many "
            f"version entries are shown in the version-list and report the number.")
    for r in popular[30:45]:
        add('recipe-versioning',
            f"Open /recipe/{r['slug']}/versions. Find the most recent version "
            f"entry (top of the list) and report its version_id.")
    add('recipe-versioning',
        "Open /recipe/butter-chicken-murgh-makhani/versions on Allrecipes. "
        "Report the editor name shown on the topmost version.")
    add('recipe-versioning',
        "Open /recipe/croissant-classic/versions on Allrecipes. Find any "
        "version entry whose kind is 'temperature-adjust' and report its note text.")
    add('recipe-versioning',
        "Open /recipe/west-african-jollof-rice/versions on Allrecipes. Report "
        "the date (YYYY-MM-DD) shown on the second-most-recent version.")
    add('recipe-versioning',
        "Open /recipe/jamaican-jerk-chicken/versions on Allrecipes. Confirm "
        "each version entry shows a 'kind' label with a green background pill.")
    add('recipe-versioning',
        "Open /recipe/persian-fesenjan/versions on Allrecipes. Read the "
        "footer note and report how many revisions are shown vs total.")

    # ============================================================
    # 9) Regional-cuisine variant filter tasks (~200)
    # ============================================================
    for r in indian[:50]:
        add('indian-regional-filter',
            f"On Allrecipes, navigate to /category/indian. Confirm "
            f"'{r['title']}' (slug '{r['slug']}') appears in the listing.")
    for r in mideast[:50]:
        add('middle-eastern-regional-filter',
            f"On Allrecipes, navigate to /category/middle-eastern. Open "
            f"'{r['title']}' and report the cuisine field from the recipe page.")
    for r in caribbean[:50]:
        add('caribbean-regional-filter',
            f"On Allrecipes, open '{r['title']}' under /category/caribbean. "
            f"Confirm the cooking_method tag is 'braised' and primary_seasoning "
            f"is 'allspice'.")
    for r in african[:50]:
        add('african-regional-filter',
            f"On Allrecipes, navigate to /category/african. Find '{r['title']}' "
            f"and report the primary_seasoning value (should be 'berbere').")

    # Category landing-page sanity probes
    for cat_slug in ['indian', 'middle-eastern', 'caribbean', 'african']:
        task_type = (
            'indian-regional-filter' if cat_slug == 'indian' else
            'middle-eastern-regional-filter' if cat_slug == 'middle-eastern' else
            'caribbean-regional-filter' if cat_slug == 'caribbean' else
            'african-regional-filter')
        add(task_type,
            f"On Allrecipes, navigate to /category/{cat_slug}. Confirm the "
            f"category page renders and report the category description "
            f"(shown at the top of the page).")
        add(task_type,
            f"On Allrecipes, GET /api/recipes/{cat_slug}. Confirm the JSON "
            f"returns at least 12 recipes for this regional cuisine.")

    # ============================================================
    # 10) multi-step (~100) — cross-feature flows
    # ============================================================
    for r in chefs[:20]:
        add('multi-step',
            f"On Allrecipes: (1) press Cmd+K to open the command palette, "
            f"(2) type a fragment of '{r['title']}' to locate the recipe, "
            f"(3) navigate to /recipe/{r['slug']}/video, (4) finally GET "
            f"/recipe/{r['slug']}/export.json and report the recipeCuisine field.")
    for r in indian[:15]:
        add('multi-step',
            f"On Allrecipes: open /recipe/{r['slug']}, then /recipe/{r['slug']}/nutrition, "
            f"then /recipe/{r['slug']}/allergens. Report whether the allergen check "
            f"shows 'milk' as present (yogurt is in the recipe).")
    for r in mideast[:15]:
        add('multi-step',
            f"On Allrecipes: open /recipe/{r['slug']}/print, then click 'Back to recipe', "
            f"then open /recipe/{r['slug']}/share/twitter. Report the canonical URL.")
    for r in caribbean[:15]:
        add('multi-step',
            f"On Allrecipes: navigate to /category/caribbean, locate '{r['title']}', "
            f"open it, then GET /recipe/{r['slug']}/versions and report the "
            f"kind of the topmost version.")
    for r in african[:15]:
        add('multi-step',
            f"On Allrecipes: open '{r['title']}' under /category/african, GET "
            f"/recipe/{r['slug']}/nutrition, and report the Sodium row value.")
    for r in chefs[:10]:
        add('multi-step',
            f"On Allrecipes: GET /api/ai-suggest?pantry=chicken,onion,garlic, "
            f"then open the first result, then GET that recipe's /allergens. "
            f"Report which allergen is found first as 'present'.")
    for r in popular[:15]:
        add('multi-step',
            f"On Allrecipes: open /recipe/{r['slug']}/video, then /recipe/{r['slug']}/print, "
            f"then POST a telemetry event {{\"event\": \"recipe-flow\"}} to /telemetry. "
            f"GET /telemetry/events?n=1 and confirm the most recent event is 'recipe-flow'.")

    # ============================================================
    # Append to tasks.jsonl
    # ============================================================
    with open(TASKS_FILE, 'a', encoding='utf-8') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    from collections import Counter
    c = Counter(t['task_type'] for t in new_tasks)
    print(f"[r9_tasks] appended {len(new_tasks)} new tasks")
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    print(f"[r9_tasks] tasks.jsonl total now: {len(existing_tasks) + len(new_tasks)}")


if __name__ == '__main__':
    main()
