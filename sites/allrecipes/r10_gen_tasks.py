#!/usr/bin/env python3
"""R10 task generator — extends ``tasks.jsonl`` with ~500+ closing-polish
tasks targeting the surfaces audited in the R10 final review:

  * cross-link-consistency-check    (a link's anchor text matches the target
                                     page title)
  * all-route-200-validation        (every advertised path returns 200)
  * missing-image-fallback          (placeholder image surfaces when no asset
                                     exists)
  * breadcrumb-fully-wired          (breadcrumb crumbs link back to the right
                                     hub)
  * footer-link-validity            (every footer link resolves)
  * sitemap-completeness            (sitemap.xml contains the URLs it claims)
  * dessert-sweet-filter            (R10 dessert variant browseable)
  * seafood-coastal-filter          (R10 seafood variant browseable)
  * grilling-bbq-filter             (R10 grilling variant browseable)
  * multi-step                      (cross-page flows spanning 8+ pages)

Idempotent — re-running this script appends only the missing R10 task IDs.
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
    print(f"[r10_tasks] loaded {len(existing_tasks)} existing tasks")

    conn = sqlite3.connect(SEED_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # R10 variant subsets
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Dessert-Sweet Test Kitchen' "
                "ORDER BY id LIMIT 80")
    dessert = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Seafood-Coastal Test Kitchen' "
                "ORDER BY id LIMIT 80")
    seafood = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Grilling-BBQ Test Kitchen' "
                "ORDER BY id LIMIT 80")
    grilling = cur.fetchall()
    # Categories (every parent_type bucket — used for breadcrumb + footer tests).
    cur.execute("SELECT slug, name FROM category ORDER BY display_order, id")
    categories = cur.fetchall()
    # Popular recipes for cross-link / multi-step flows.
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE review_count >= 5 ORDER BY id LIMIT 200")
    popular = cur.fetchall()
    # Articles (for cross-link checks)
    cur.execute("SELECT slug, title FROM article ORDER BY id LIMIT 25")
    articles = cur.fetchall()
    # Collections
    cur.execute("SELECT slug, title FROM collection ORDER BY id LIMIT 20")
    collections = cur.fetchall()
    # Authors (chef recipes via author_name LIKE 'Chef %')
    cur.execute("SELECT DISTINCT author_name FROM recipe "
                "WHERE author_name LIKE 'Chef %' ORDER BY author_name")
    chefs = [row[0] for row in cur.fetchall()]
    conn.close()

    new_tasks = []
    n = 0
    while f"Allrecipes--R10--{n}" in existing_ids:
        n += 1

    def add(task_type, ques):
        nonlocal n
        tid = f"Allrecipes--R10--{n}"
        while tid in existing_ids:
            n += 1
            tid = f"Allrecipes--R10--{n}"
        existing_ids.add(tid)
        new_tasks.append(make_task(tid, task_type, ques))
        n += 1

    # ============================================================
    # 1) cross-link-consistency-check (~60)
    # Anchor text on a hub page must match the target page's H1.
    # ============================================================
    for r in popular[:30]:
        add('cross-link-consistency-check',
            f"On Allrecipes, open the index page '/' and find a card or link "
            f"pointing to /recipe/{r['slug']}. Confirm the link's anchor text "
            f"contains the same recipe title that appears as the H1 on the "
            f"target recipe detail page.")
    for art in articles[:15]:
        add('cross-link-consistency-check',
            f"On Allrecipes, open /articles. Locate the link to /article/{art['slug']}. "
            f"Click through and confirm the article H1 matches the anchor text of "
            f"the source link.")
    for col in collections[:8]:
        add('cross-link-consistency-check',
            f"On Allrecipes, navigate to /collections and click into "
            f"/collection/{col['slug']}. Confirm the collection title shown in "
            f"the breadcrumb matches the collection's H1 heading.")
    for cat in categories[:8]:
        add('cross-link-consistency-check',
            f"On Allrecipes, open the homepage. Confirm any nav link pointing to "
            f"/category/{cat['slug']} uses the exact category name '{cat['name']}' "
            f"as its anchor text.")

    # ============================================================
    # 2) all-route-200-validation (~80)
    # Each advertised path should return HTTP 200.
    # ============================================================
    static_routes = [
        '/', '/recipes', '/about', '/about/allstars', '/sitemap',
        '/occasions', '/dinners', '/meals', '/ingredients', '/cuisines',
        '/articles', '/diets', '/collections', '/community', '/authors',
        '/newsletter', '/login', '/register', '/help/shortcuts', '/help/popovers',
        '/recipe/import-url', '/sitemap.xml', '/robots.txt', '/feed.rss',
    ]
    for path in static_routes:
        add('all-route-200-validation',
            f"On Allrecipes, GET {path}. Confirm the response status is 200 OK "
            f"(or, for /sitemap.xml and /robots.txt, the appropriate Content-Type).")
    for cat in categories[:20]:
        add('all-route-200-validation',
            f"On Allrecipes, GET /category/{cat['slug']}. Confirm the response "
            f"is 200 OK and the page contains the category name '{cat['name']}'.")
    for r in popular[:20]:
        add('all-route-200-validation',
            f"On Allrecipes, GET /recipe/{r['slug']}. Confirm the response is "
            f"200 OK and the title '{r['title']}' appears in the page.")
    # Sub-routes of recipe detail (R7-R9 added many).
    sub_routes = ['/print', '/nutrition', '/allergens', '/versions', '/video',
                  '/export.json']
    for sub in sub_routes:
        add('all-route-200-validation',
            f"On Allrecipes, GET /recipe/butter-chicken-murgh-makhani{sub}. "
            f"Confirm the response is 200 OK and the recipe slug appears in "
            f"the response body.")

    # ============================================================
    # 3) missing-image-fallback (~40)
    # Recipes / categories without an asset should render a placeholder.
    # ============================================================
    for r in dessert[:15]:
        add('missing-image-fallback',
            f"On Allrecipes, open /recipe/{r['slug']}. Inspect the hero image "
            f"<img> tag. If the actual asset file is missing on disk, confirm "
            f"the src falls back to /static/images/placeholder.svg (and not a "
            f"broken 404).")
    for cat in categories[:10]:
        add('missing-image-fallback',
            f"On Allrecipes, open /category/{cat['slug']}. For each recipe card "
            f"shown, confirm every <img> has a valid alt attribute and a src "
            f"that does not resolve to a 404.")
    for col in collections[:8]:
        add('missing-image-fallback',
            f"On Allrecipes, open /collection/{col['slug']}. Confirm every "
            f"recipe card in the collection renders an image (or the placeholder "
            f"SVG if the asset is missing), and none show a broken-image icon.")
    add('missing-image-fallback',
        "On Allrecipes, GET /static/images/placeholder.svg. Confirm the response "
        "is 200 OK and the Content-Type is image/svg+xml.")

    # ============================================================
    # 4) breadcrumb-fully-wired (~50)
    # Breadcrumb crumbs link back to a real hub or category page.
    # ============================================================
    for r in popular[:25]:
        add('breadcrumb-fully-wired',
            f"On Allrecipes, open /recipe/{r['slug']}. Find the breadcrumb at "
            f"the top of the page. Confirm at least one crumb links to a valid "
            f"category page (/category/...) and that crumb's link does NOT 404.")
    for art in articles[:10]:
        add('breadcrumb-fully-wired',
            f"On Allrecipes, open /article/{art['slug']}. Confirm the breadcrumb "
            f"contains 'Home > Articles > <article-title>' and the 'Articles' "
            f"crumb links to /articles.")
    for col in collections[:8]:
        add('breadcrumb-fully-wired',
            f"On Allrecipes, open /collection/{col['slug']}. Confirm the "
            f"breadcrumb has 'Home > Collections > <collection-title>' and the "
            f"'Collections' crumb links to /collections.")
    for cat in categories[:7]:
        add('breadcrumb-fully-wired',
            f"On Allrecipes, open /category/{cat['slug']}. Confirm the breadcrumb "
            f"reads 'Home > <category-name>' and the 'Home' crumb links to '/'.")

    # ============================================================
    # 5) footer-link-validity (~30)
    # Every footer link in base.html should resolve.
    # ============================================================
    footer_targets = [
        ('/about', 'About'),
        ('/community', 'Community'),
        ('/newsletter', 'Newsletter'),
        ('/articles', 'Articles'),
        ('/sitemap', 'Sitemap'),
        ('/help/shortcuts', 'Keyboard shortcuts'),
        ('/help/popovers', 'Popover help'),
        ('/authors', 'Authors directory'),
        ('/cuisines', 'Cuisines hub'),
        ('/diets', 'Diets hub'),
        ('/occasions', 'Occasions hub'),
        ('/meals', 'Meals hub'),
        ('/ingredients', 'Ingredients hub'),
        ('/collections', 'Collections hub'),
    ]
    for path, label in footer_targets:
        add('footer-link-validity',
            f"On Allrecipes, scroll to the footer on the homepage. Click the "
            f"'{label}' footer link (target {path}). Confirm the destination "
            f"page loads with HTTP 200 and the page heading contains the link "
            f"label or its plural form.")
    add('footer-link-validity',
        "On Allrecipes, open '/'. Confirm the footer contains a Newsletter "
        "signup form whose action attribute is exactly '/newsletter' (no "
        "extra query string, no relative-path quirks).")
    add('footer-link-validity',
        "On Allrecipes, open '/'. In the footer, find the Sitemap link. "
        "Confirm it points to /sitemap (HTML view), not /sitemap.xml.")

    # ============================================================
    # 6) sitemap-completeness (~30)
    # /sitemap.xml advertises real URLs.
    # ============================================================
    add('sitemap-completeness',
        "On Allrecipes, GET /sitemap.xml. Confirm the response is valid XML "
        "with a root <urlset> element and at least one <url><loc> child.")
    add('sitemap-completeness',
        "On Allrecipes, GET /sitemap.xml. Parse the <loc> elements and confirm "
        "/recipe/butter-chicken-murgh-makhani is among the advertised URLs.")
    for r in popular[:15]:
        add('sitemap-completeness',
            f"On Allrecipes, GET /sitemap.xml. Confirm the URL "
            f"/recipe/{r['slug']} appears in at least one <loc> element.")
    for cat in categories[:8]:
        add('sitemap-completeness',
            f"On Allrecipes, GET /sitemap.xml. Confirm the URL "
            f"/category/{cat['slug']} appears in the sitemap.")
    add('sitemap-completeness',
        "On Allrecipes, GET /sitemap.xml. Count the total number of <url> "
        "entries and report the integer.")
    add('sitemap-completeness',
        "On Allrecipes, GET /robots.txt. Confirm it contains a 'Sitemap:' "
        "directive pointing to a /sitemap.xml URL.")
    add('sitemap-completeness',
        "On Allrecipes, GET /sitemap.xml. Confirm the response Content-Type "
        "header begins with 'application/xml' or 'text/xml'.")

    # ============================================================
    # 7) dessert-sweet-filter (~70)
    # ============================================================
    for r in dessert[:25]:
        add('dessert-sweet-filter',
            f"On Allrecipes, navigate to /category/desserts. Confirm "
            f"'{r['title']}' (slug '{r['slug']}') appears in the listing.")
    for r in dessert[25:50]:
        add('dessert-sweet-filter',
            f"On Allrecipes, open '{r['title']}' under /category/desserts. "
            f"Report the cooking_method tag (should be 'baked').")
    for r in dessert[50:65]:
        add('dessert-sweet-filter',
            f"On Allrecipes, open /recipe/{r['slug']}/nutrition. Report the "
            f"Carbs %DV (dessert variants are carb-forward).")
    add('dessert-sweet-filter',
        "On Allrecipes, GET /api/recipes/desserts. Confirm the JSON returns "
        "at least 12 dessert recipes.")
    add('dessert-sweet-filter',
        "On Allrecipes, navigate to /category/desserts. Report the category "
        "description shown at the top of the page.")

    # ============================================================
    # 8) seafood-coastal-filter (~70)
    # ============================================================
    for r in seafood[:25]:
        add('seafood-coastal-filter',
            f"On Allrecipes, navigate to /category/seafood. Confirm "
            f"'{r['title']}' (slug '{r['slug']}') appears in the listing.")
    for r in seafood[25:50]:
        add('seafood-coastal-filter',
            f"On Allrecipes, open '{r['title']}' under /category/seafood. "
            f"Report the cuisine field shown on the recipe page.")
    for r in seafood[50:65]:
        add('seafood-coastal-filter',
            f"On Allrecipes, open /recipe/{r['slug']}/allergens. Report whether "
            f"the row for 'fish' shows 'Yes' (it should — seafood-coastal is "
            f"fish-based).")
    add('seafood-coastal-filter',
        "On Allrecipes, GET /api/recipes/seafood. Confirm the JSON returns at "
        "least 12 seafood recipes.")
    add('seafood-coastal-filter',
        "On Allrecipes, navigate to /diet/pescatarian. Confirm the "
        "seafood-coastal variants appear in the pescatarian diet listing.")

    # ============================================================
    # 9) grilling-bbq-filter (~70)
    # ============================================================
    for r in grilling[:25]:
        add('grilling-bbq-filter',
            f"On Allrecipes, navigate to /category/grilling. Confirm "
            f"'{r['title']}' (slug '{r['slug']}') appears in the listing.")
    for r in grilling[25:50]:
        add('grilling-bbq-filter',
            f"On Allrecipes, open '{r['title']}' under /category/grilling. "
            f"Report the cooking_method tag (should be 'grilled').")
    for r in grilling[50:65]:
        add('grilling-bbq-filter',
            f"On Allrecipes, open /recipe/{r['slug']}. Report the occasion "
            f"field (should be 'summer-cookout').")
    add('grilling-bbq-filter',
        "On Allrecipes, GET /api/recipes/grilling. Confirm the JSON returns at "
        "least 12 grilling recipes.")
    add('grilling-bbq-filter',
        "On Allrecipes, navigate to /category/grilling. Report the category "
        "description shown at the top of the page.")

    # ============================================================
    # 10) multi-step (~50) — compound flows spanning 8+ pages
    # ============================================================
    for r in dessert[:10]:
        add('multi-step',
            f"On Allrecipes: (1) open '/', (2) navigate to /category/desserts, "
            f"(3) locate '{r['title']}', (4) open /recipe/{r['slug']}, "
            f"(5) open /recipe/{r['slug']}/nutrition, "
            f"(6) open /recipe/{r['slug']}/allergens, "
            f"(7) open /recipe/{r['slug']}/versions, "
            f"(8) open /recipe/{r['slug']}/print, "
            f"(9) finally GET /recipe/{r['slug']}/export.json and report the "
            f"recipeYield field.")
    for r in seafood[:10]:
        add('multi-step',
            f"On Allrecipes: (1) open '/', (2) /cuisines, "
            f"(3) /category/seafood, (4) locate '{r['title']}', "
            f"(5) /recipe/{r['slug']}, (6) /recipe/{r['slug']}/share/pinterest, "
            f"(7) /recipe/{r['slug']}/share/twitter, "
            f"(8) /recipe/{r['slug']}/share/facebook. Report the platform name "
            f"shown on each share page, in order.")
    for r in grilling[:10]:
        add('multi-step',
            f"On Allrecipes: (1) /category/grilling, (2) sort by rating, "
            f"(3) open '{r['title']}', (4) /recipe/{r['slug']}/video, "
            f"(5) /recipe/{r['slug']}/print, "
            f"(6) /recipe/{r['slug']}/nutrition, "
            f"(7) GET /api/recipes/{r['slug']}/scale?yield=12, "
            f"(8) POST {{\"event\":\"grill-finalized\"}} to /telemetry, "
            f"(9) GET /telemetry/events?n=1. Confirm the latest event is "
            f"'grill-finalized'.")
    for chef in chefs[:10]:
        chef_slug = chef.replace('Chef ', '').lower().replace(' ', '-')
        add('multi-step',
            f"On Allrecipes: (1) /authors, (2) locate '{chef}', "
            f"(3) /authors/{chef_slug}, (4) click into the first recipe, "
            f"(5) save it to the recipe-box (logged-in flow with test1234), "
            f"(6) /recipe-box, (7) /meal-plan, (8) add the recipe to Monday, "
            f"(9) /shopping-list. Report the number of items in the resulting "
            f"shopping list.")
    add('multi-step',
        "On Allrecipes: (1) GET /sitemap.xml, (2) pick any /recipe/<slug> URL, "
        "(3) open that recipe, (4) follow its breadcrumb back to the category, "
        "(5) open /api/recipes/<that-category>, (6) confirm the slug from step 2 "
        "appears in the JSON, (7) open /robots.txt, (8) confirm the Sitemap "
        "directive matches the /sitemap.xml URL from step 1.")
    add('multi-step',
        "On Allrecipes: (1) /register a new user, (2) /account, (3) /recipe-box, "
        "(4) save 3 recipes, (5) /meal-plan add each to a different day, "
        "(6) /shopping-list/create with name 'R10 grocery run', "
        "(7) add ingredients from each recipe to that list, (8) /shopping-list "
        "open the list, (9) confirm the item count matches the sum of "
        "ingredient counts.")

    # ============================================================
    # Append to tasks.jsonl
    # ============================================================
    with open(TASKS_FILE, 'a', encoding='utf-8') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    from collections import Counter
    c = Counter(t['task_type'] for t in new_tasks)
    print(f"[r10_tasks] appended {len(new_tasks)} new tasks")
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    print(f"[r10_tasks] tasks.jsonl total now: {len(existing_tasks) + len(new_tasks)}")


if __name__ == '__main__':
    main()
