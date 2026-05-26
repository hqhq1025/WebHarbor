#!/usr/bin/env python3
"""R6 task generator — extends ``tasks.jsonl`` with ~1000 new tasks that
emphasise cross-page multi-step flows: search -> filter -> detail -> box ->
meal-plan -> shopping-list. Idempotent (skips any task_id already in file).

R6 task themes:
  * copycat-restaurant-filter      (R6 variant theme)
  * budget-friendly-filter         (R6 variant theme)
  * holiday-entertaining-filter    (R6 variant theme)
  * air-fryer-shortcut-filter      (R6 variant theme)
  * cross-page-recipe-box-mealplan-shopping (4+ pages)
  * see-also-jump                  (related / more-like / same-chef)
  * breadcrumb-back-and-forth      (uses breadcrumb to back out, then re-enters via a different path)
  * alternate-entry-same-task      (same goal reached via two different entry pages)
  * edge-case-recovery             (404 / 429 / loading / session-expired pages)
  * same-chef-discovery            (R6 chef-page jumps)
  * more-like-discovery            (R6 more-like-this carousel)
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


def next_id(existing_ids, prefix='Allrecipes--R6--'):
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
    print(f"[r6_tasks] loaded {len(existing_tasks)} existing tasks")

    conn = sqlite3.connect(SEED_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT slug, title, cuisine FROM recipe WHERE author_name='Copycat-Restaurant Test Kitchen' ORDER BY id LIMIT 80")
    copycat = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Budget-Friendly Test Kitchen' ORDER BY id LIMIT 80")
    budget = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Holiday-Entertaining Test Kitchen' ORDER BY id LIMIT 80")
    holiday = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE author_name='Air-Fryer-Shortcut Test Kitchen' ORDER BY id LIMIT 80")
    airfryer = cur.fetchall()
    cur.execute("SELECT DISTINCT author_name FROM recipe WHERE author_name LIKE 'Chef %' ORDER BY author_name")
    chefs = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT slug, title, author_name FROM recipe WHERE author_name LIKE 'Chef %' ORDER BY id LIMIT 120")
    chef_recipes = cur.fetchall()
    cur.execute("SELECT slug, title, cuisine FROM recipe WHERE cuisine IN ('Brazilian','Greek','Vietnamese','Cajun') ORDER BY id LIMIT 60")
    new_cuisine = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe WHERE total_time_mins>0 AND total_time_mins<=20 ORDER BY id LIMIT 80")
    super_quick = cur.fetchall()
    cur.execute("SELECT slug, title FROM collection ORDER BY id")
    collections = cur.fetchall()
    cur.execute("SELECT slug, title FROM article ORDER BY id LIMIT 12")
    articles = cur.fetchall()
    conn.close()

    rng = random.Random(20260527)
    new_tasks = []

    def add(task_type, ques):
        tid, n = next_id(existing_ids)
        existing_ids.add(tid)
        new_tasks.append(make_task(tid, task_type, ques))

    # ============================================================
    # 1) copycat-restaurant-filter (~60)
    # ============================================================
    for r in copycat[:50]:
        add('copycat-restaurant-filter',
            f"On Allrecipes, find a copycat-restaurant recipe titled like '{r['title']}' and report its prep + cook time.")
    for q in [
        "Find a copycat-restaurant recipe with under 30 minutes total time.",
        "Find a copycat-restaurant recipe with at least 4.5 stars and report the chef-finishing-butter step.",
        "Find a copycat-restaurant recipe whose cuisine is Italian and list its ingredients.",
        "Find a copycat-restaurant pasta and explain the single-sauce-axis instruction.",
        "Find a copycat-restaurant chicken dish and report its plating note.",
        "Find a copycat-restaurant breakfast item and report its serving size.",
        "Find a copycat-restaurant dessert and report its calorie count.",
        "Find a copycat-restaurant seafood dish and report its main protein.",
        "Find a copycat-restaurant burger or sandwich and report its prep time.",
        "Find a copycat-restaurant Asian dish and report its sauce ingredients.",
    ]:
        add('copycat-restaurant-filter', q)

    # ============================================================
    # 2) budget-friendly-filter (~60)
    # ============================================================
    for r in budget[:50]:
        add('budget-friendly-filter',
            f"Find a budget-friendly Allrecipes recipe similar to '{r['title']}' and report which thrifty substitution it uses.")
    for q in [
        "Find a budget-friendly recipe whose total time is under 45 minutes.",
        "Find a budget-friendly recipe that stretches the protein with beans or rice.",
        "Find a budget-friendly recipe with at least 6 servings.",
        "Find a budget-friendly vegetarian recipe.",
        "Find a budget-friendly chicken dinner that costs less per portion.",
        "Find a budget-friendly soup recipe.",
        "Find a budget-friendly recipe that doubles as next-day lunch.",
        "Find a budget-friendly pasta recipe.",
        "Find a budget-friendly recipe and report its quick-pickle garnish.",
        "Find a budget-friendly recipe with at least a 4-star rating.",
    ]:
        add('budget-friendly-filter', q)

    # ============================================================
    # 3) holiday-entertaining-filter (~60)
    # ============================================================
    for r in holiday[:50]:
        add('holiday-entertaining-filter',
            f"Find a holiday-entertaining recipe based on '{r['title']}' and report its make-ahead step.")
    for q in [
        "Find a holiday-entertaining recipe that serves at least 10.",
        "Find a holiday-entertaining dessert with a make-ahead component.",
        "Find a holiday-entertaining main course that uses rosemary as garnish.",
        "Find a holiday-entertaining recipe and report its family-style plating note.",
        "Find a holiday-entertaining recipe with under 1 hour cook time.",
        "Find a holiday-entertaining recipe whose protein is doubled but aromatics are 1.5x.",
        "Find a holiday-entertaining side dish.",
        "Find a holiday-entertaining recipe and explain why entertaining is half visual.",
        "Find a holiday-entertaining recipe with at least 4.5 stars.",
        "Find a holiday-entertaining recipe with the 'show-piece' tag.",
    ]:
        add('holiday-entertaining-filter', q)

    # ============================================================
    # 4) air-fryer-shortcut-filter (~60)
    # ============================================================
    for r in airfryer[:50]:
        add('air-fryer-shortcut-filter',
            f"Find an air-fryer-shortcut recipe similar to '{r['title']}' and report its 375F preheat step.")
    for q in [
        "Find an air-fryer-shortcut recipe that finishes in under 15 minutes of cook time.",
        "Find an air-fryer-shortcut chicken recipe and report the shake-halfway step.",
        "Find an air-fryer-shortcut vegetable side dish.",
        "Find an air-fryer-shortcut fish recipe.",
        "Find an air-fryer-shortcut breakfast item.",
        "Find an air-fryer-shortcut recipe whose total time is under 25 minutes.",
        "Find an air-fryer-shortcut recipe that uses a wire rack for the final rest.",
        "Find an air-fryer-shortcut recipe with the 'weeknight' tag.",
        "Find an air-fryer-shortcut recipe and report the basket-preheat duration.",
        "Find an air-fryer-shortcut recipe with at least a 4-star rating.",
    ]:
        add('air-fryer-shortcut-filter', q)

    # ============================================================
    # 5) cross-page-recipe-box-mealplan-shopping — 4+ pages, multi-step (~180)
    # ============================================================
    test_users = [
        ('alice.j@test.com', 'TestPass123!', 'Alice'),
        ('bob.c@test.com',   'TestPass123!', 'Bob'),
        ('carol.d@test.com', 'TestPass123!', 'Carol'),
        ('david.k@test.com', 'TestPass123!', 'David'),
    ]
    cuisines_for_xpage = ['Italian', 'Mexican', 'Japanese', 'Thai',
                          'Brazilian', 'Greek', 'Vietnamese', 'Cajun',
                          'Indian', 'French', 'Korean', 'Mediterranean']
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday']

    # 60 — search -> filter -> detail -> recipe-box
    for i in range(60):
        email, pw, _ = test_users[i % len(test_users)]
        cuisine = cuisines_for_xpage[i % len(cuisines_for_xpage)]
        add('cross-page-multi-step',
            f"Log in to Allrecipes as {email} ({pw}). From the search bar, query '{cuisine}'. "
            f"On the search results page, click into a recipe with at least 4 stars. "
            f"Save it to the Recipe Box, then visit the Recipe Box page and confirm it appears there.")

    # 50 — search -> detail -> meal-plan -> shopping-list (4 pages)
    for i in range(50):
        email, pw, name = test_users[i % len(test_users)]
        cuisine = cuisines_for_xpage[(i + 3) % len(cuisines_for_xpage)]
        day = days[i % len(days)]
        add('cross-page-multi-step',
            f"Log in to Allrecipes as {email} ({pw}). Search for a '{cuisine}' recipe, click into a 4-star+ result, "
            f"add it to {name}'s {day} dinner meal plan, then open the Shopping List page and create a new list named "
            f"'{day} groceries' with that recipe's ingredients.")

    # 40 — category -> detail -> related-carousel -> meal-plan
    for i in range(40):
        email, pw, name = test_users[i % len(test_users)]
        cuisine = cuisines_for_xpage[(i + 5) % len(cuisines_for_xpage)]
        day = days[(i + 2) % len(days)]
        add('cross-page-multi-step',
            f"Log in as {email} ({pw}). Browse the Allrecipes {cuisine} category. Click into a 4-star+ recipe. "
            f"From the 'You Might Also Like' related carousel on the detail page, click into a SECOND recipe. "
            f"Add that second recipe to {name}'s {day} dinner meal plan.")

    # 30 — collection -> recipe -> shopping-list
    for col in collections[:10]:
        for j in range(3):
            email, pw, _ = test_users[j % len(test_users)]
            add('cross-page-multi-step',
                f"Log in as {email} ({pw}). Open the Allrecipes collection '{col['title']}'. "
                f"Click into any recipe in the collection. Add its ingredients to a new shopping list named "
                f"'{col['title']} groceries' and verify the list shows the items.")

    # ============================================================
    # 6) see-also-jump (related / more-like / same-chef) (~120)
    # ============================================================
    # 40 — same-chef discovery
    for r in chef_recipes[:40]:
        add('same-chef-discovery',
            f"Open the Allrecipes recipe '{r['title']}'. From the 'Recipes from {r['author_name']}' carousel "
            f"on the detail page, click into ANOTHER recipe by the same chef and report its title and rating.")

    # 40 — more-like discovery (R6 cross-category carousel)
    for r in (copycat[:20] + budget[:10] + holiday[:10]):
        add('more-like-discovery',
            f"Open the Allrecipes recipe '{r['title']}'. From the 'More Like {r['title']}' carousel, click into "
            f"a recipe in a DIFFERENT category and report which category it belongs to.")

    # 40 — related-carousel jumps (R5 carryover)
    for r in (chef_recipes[40:80] if len(chef_recipes) >= 80 else chef_recipes):
        add('see-also-jump',
            f"Open the Allrecipes recipe '{r['title']}'. From the 'You Might Also Like' carousel, click into a "
            f"recipe whose rating is higher than the current one and report the difference.")

    # ============================================================
    # 7) breadcrumb-back-and-forth (~60)
    # ============================================================
    for r in (chef_recipes[:30] + copycat[:30]):
        add('breadcrumb-back-and-forth',
            f"Open the Allrecipes recipe '{r['title']}'. Use the breadcrumb (Home > Category > Recipe) to go back to "
            f"the parent CATEGORY page. From there, click into a DIFFERENT recipe in the same category and report "
            f"that second recipe's title and rating.")

    # ============================================================
    # 8) alternate-entry-same-task (~80)
    # Same goal reached via two different entry pages.
    # ============================================================
    for cuisine in cuisines_for_xpage:
        add('alternate-entry-same-task',
            f"On Allrecipes, reach a {cuisine} recipe TWO different ways: (1) via the search bar querying '{cuisine}', "
            f"(2) via the Cuisines hub then clicking '{cuisine}'. Report whether both paths surface the same top result.")
        add('alternate-entry-same-task',
            f"On Allrecipes, reach a {cuisine} recipe via (1) the homepage cuisine tile, and (2) the Sitemap page's "
            f"link to '{cuisine}'. Report whether both paths land on the same hub page.")

    for r in chef_recipes[:30]:
        add('alternate-entry-same-task',
            f"On Allrecipes, reach the recipe '{r['title']}' TWO ways: (1) via search, (2) via the chef's author page. "
            f"Report which path is faster (fewer clicks).")

    # 20 more — collection vs occasion entry
    occasion_terms = ['Mother\'s Day', 'Father\'s Day', 'Thanksgiving', '4th of July',
                      'Christmas', 'Valentine\'s Day', 'New Year\'s Eve', 'Easter',
                      'Halloween', 'Cinco de Mayo']
    for occ in occasion_terms:
        add('alternate-entry-same-task',
            f"On Allrecipes, reach a {occ} recipe TWO ways: (1) via the Occasions hub, (2) via the Collections hub. "
            f"Report whether both paths surface the same recipe.")

    # ============================================================
    # 9) edge-case-recovery (~70)
    # ============================================================
    for q in [
        # 404 recovery
        "Open the Allrecipes URL /recipe/this-recipe-does-not-exist-xyz. Report what the 404 page suggests you do, then click 'Back to homepage' to recover.",
        "Open /category/not-a-category-foo on Allrecipes. Use the 404 page's suggestion carousel to navigate to a real recipe and report its title.",
        "Open /author/some-fake-chef on Allrecipes. From the 404 page, navigate to 'Browse all recipes' and report the title of the first recipe shown.",
        "Open /collection/imaginary-collection on Allrecipes. Use the 404 page's 'Search recipes' link to find a chicken recipe.",
        "Open /occasion/fictional-holiday on Allrecipes. Use the 404 page to recover and reach a holiday recipe via the Occasions hub.",
        # 429 demo
        "Open /__rate-limit-demo on Allrecipes. Report the HTTP status code, the 'what you can do' steps, and how long the user is asked to wait.",
        "Open /__rate-limit-demo on Allrecipes. Report whether the page recommends signing in to get a higher request budget.",
        "Open /__rate-limit-demo on Allrecipes. Click 'Back to homepage' from the 429 page and confirm the homepage loads.",
        # session-expired demo
        "Open /__session-expired-demo on Allrecipes. Report which three saved-content areas the page reassures the user are still safe.",
        "Open /__session-expired-demo on Allrecipes. Click 'Sign in again' and confirm you arrive on the login page.",
        # loading-skeleton demo
        "Open /__loading-demo on Allrecipes. Report how many skeleton cards are shown and whether the page is marked aria-busy.",
        "Open /__loading-demo on Allrecipes. Click the 'browse the recipe index' link from the loading page and confirm it lands on /recipes.",
        # 500 demo
        "Open /__server-error-demo on Allrecipes. Report the HTTP status code and the 'banana peel' wording on the page.",
        # empty-cart / empty-shopping-list
        "Log in to Allrecipes as a NEW account (register first with username 'emptyTester', email 'empty@example.com', password 'NewUser12!'). Open /shopping-list. Report what the empty-state message says.",
        "Log in as a new account, open /meal-plan. Report what the empty meal-plan state encourages the user to do.",
        "Log in as a new account, open /recipe-box. Report what the empty recipe-box state says and which button it offers.",
    ]:
        add('edge-case-recovery', q)

    # 25 — recovery flows after error
    for cuisine in cuisines_for_xpage[:10]:
        add('edge-case-recovery',
            f"Open a deliberately broken Allrecipes URL /recipe/broken-{cuisine.lower()}-foo. From the 404 page's "
            f"suggestion list, click any suggestion and report whether you reach a valid recipe detail page.")
    for r in copycat[:15]:
        add('edge-case-recovery',
            f"Open /__loading-demo, then click the link to /recipes, then search for '{r['title']}' from the search bar. "
            f"Report whether the search returns the copycat-restaurant variant.")

    # ============================================================
    # 10) new-cuisine-discovery — exercise the R6 chefs' cuisines (~80)
    # ============================================================
    for r in new_cuisine[:40]:
        add('new-cuisine-discovery',
            f"On Allrecipes, find the recipe '{r['title']}' (cuisine: {r['cuisine']}) and report its primary "
            f"cooking technique from the description.")
    for chef in chefs:
        add('chef-recipe',
            f"On Allrecipes, open the author page for {chef}. Report how many recipes are listed and the name "
            f"of the highest-rated one.")
    for q in [
        "Find a Brazilian recipe by Chef Beatriz Almeida and list its ingredients.",
        "Find a Greek recipe by Chef Eleni Stavros and report its dietary tags.",
        "Find a Vietnamese recipe by Chef Linh Tran and report its prep + cook time.",
        "Find a Cajun recipe by Chef Marcel Boudreaux and report its main protein.",
        "Browse the Brazilian cuisine page on Allrecipes and pick the highest-rated recipe.",
        "Browse the Greek cuisine page on Allrecipes and find a recipe with phyllo dough in its ingredients.",
        "Browse the Vietnamese cuisine page on Allrecipes and find a recipe that takes over 2 hours total time.",
        "Browse the Cajun cuisine page on Allrecipes and find a recipe with andouille sausage.",
        "Find a Greek recipe with the 'gluten-free' dietary tag and report its category.",
        "Find a Brazilian dessert and report its description.",
    ]:
        add('new-cuisine-discovery', q)

    # ============================================================
    # 11) extra cross-page concrete multi-step (~80)
    # ============================================================
    for i in range(40):
        email, pw, name = test_users[i % len(test_users)]
        day = days[(i + 4) % len(days)]
        add('cross-page-multi-step',
            f"Log in as {email} ({pw}). Open the Articles hub. Pick any cooking-tip article, then from its 'Related recipes' "
            f"section click into a recipe. Save that recipe to the Recipe Box and add it to {name}'s {day} dinner meal plan.")
    for i in range(40):
        email, pw, name = test_users[(i + 1) % len(test_users)]
        cuisine = cuisines_for_xpage[(i + 7) % len(cuisines_for_xpage)]
        add('cross-page-multi-step',
            f"Log in as {email} ({pw}). Search Allrecipes for '{cuisine}', open a recipe, scroll to the 'More Like X' "
            f"carousel, click into a recipe in a DIFFERENT category, then add THAT second recipe's ingredients to a new "
            f"shopping list named '{name} variety night'.")

    # ============================================================
    # 12) recipe-box-curation (~40) — manage a saved-recipe collection
    # ============================================================
    for i in range(40):
        email, pw, name = test_users[i % len(test_users)]
        c1 = cuisines_for_xpage[i % len(cuisines_for_xpage)]
        c2 = cuisines_for_xpage[(i + 4) % len(cuisines_for_xpage)]
        add('cross-page-multi-step',
            f"Log in as {email} ({pw}). Save a {c1} recipe and a {c2} recipe to {name}'s Recipe Box. Then open the Recipe Box "
            f"page and add a personal note 'Try next weekend' to the {c1} recipe.")

    # ============================================================
    # 14) extra coverage — super-quick, article+collection, dietary cross (~100)
    # ============================================================
    for r in super_quick[:30]:
        add('time-budget-tier',
            f"On Allrecipes, find the recipe '{r['title']}' (under 20 minutes total time) and report its calorie count.")
    for art in articles[:8]:
        for c in cuisines_for_xpage[:5]:
            add('article-detail',
                f"Open the Allrecipes article '{art['title']}'. From the article body, look for a tip that applies to {c} "
                f"cuisine and report it.")
    for col in collections[:5]:
        for r_pair in [(super_quick[i], super_quick[i+1]) for i in range(0, 10, 2)]:
            add('collection-detail',
                f"Open the Allrecipes collection '{col['title']}'. Pick a recipe similar to '{r_pair[0]['title']}' and "
                f"report whether the collection contains a recipe similar to '{r_pair[1]['title']}'.")

    # 50 more — extra cross-page targets to clear the 2500+ floor with margin.
    for i in range(50):
        email, pw, name = test_users[i % len(test_users)]
        cuisine = cuisines_for_xpage[(i + 9) % len(cuisines_for_xpage)]
        chef_name = chefs[i % len(chefs)] if chefs else 'Chef Smith'
        day = days[(i + 1) % len(days)]
        add('cross-page-multi-step',
            f"Log in as {email} ({pw}). Open the {chef_name} author page on Allrecipes. Pick the top-rated recipe, "
            f"save it to {name}'s Recipe Box, then add it to {day} dinner on the meal plan, and finally add its "
            f"ingredients to a new shopping list named '{chef_name} weeknight'. This task spans 4 distinct pages: "
            f"author -> detail -> recipe-box -> meal-plan -> shopping-list.")

    # ============================================================
    # 13) Write back.
    # ============================================================
    print(f"[r6_tasks] generated {len(new_tasks)} new tasks")
    if not new_tasks:
        return
    with open(TASKS_FILE, 'a', encoding='utf-8') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f"[r6_tasks] wrote to {TASKS_FILE}; total tasks now: {len(existing_tasks) + len(new_tasks)}")


if __name__ == '__main__':
    main()
