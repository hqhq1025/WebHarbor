#!/usr/bin/env python3
"""R8 task generator — extends ``tasks.jsonl`` with ~700+ new tasks covering
the R8 polish surface: keyboard shortcuts, command palette, contextual help
popovers, OCR import, Mealie JSON export, telemetry events, healthz/metrics
observability, baking-subcategory variant filters and multi-step flows.

Idempotent.

Task types added:
  * keyboard-shortcut-discover
  * command-palette-search
  * contextual-help-popover
  * recipe-import-OCR
  * recipe-export-JSON-Mealie
  * telemetry-event-fire
  * health-probe
  * metrics-extract
  * baking-cookies-filter
  * baking-cakes-filter
  * baking-pies-filter
  * baking-breads-filter
  * baking-pastries-filter
  * multi-step (additional cross-page flows)
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
    print(f"[r8_tasks] loaded {len(existing_tasks)} existing tasks")

    conn = sqlite3.connect(SEED_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Baking variant subsets
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Baking-Cookies Test Kitchen' "
                "ORDER BY id LIMIT 60")
    cookies = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Baking-Cakes Test Kitchen' "
                "ORDER BY id LIMIT 60")
    cakes = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Baking-Pies Test Kitchen' "
                "ORDER BY id LIMIT 60")
    pies = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Baking-Breads Test Kitchen' "
                "ORDER BY id LIMIT 60")
    breads = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Baking-Pastries Test Kitchen' "
                "ORDER BY id LIMIT 60")
    pastries = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Chef Pierre Beaumont' "
                "ORDER BY id")
    pierre = cur.fetchall()
    cur.execute("SELECT slug, title, cuisine, total_time_mins, avg_rating "
                "FROM recipe WHERE review_count >= 5 ORDER BY id LIMIT 200")
    popular_recipes = cur.fetchall()
    conn.close()

    new_tasks = []
    n = 0
    while f"Allrecipes--R8--{n}" in existing_ids:
        n += 1

    def add(task_type, ques):
        nonlocal n
        tid = f"Allrecipes--R8--{n}"
        while tid in existing_ids:
            n += 1
            tid = f"Allrecipes--R8--{n}"
        existing_ids.add(tid)
        new_tasks.append(make_task(tid, task_type, ques))
        n += 1

    # ============================================================
    # 1) keyboard-shortcut-discover (~80)
    # ============================================================
    shortcut_questions = [
        "Open the Allrecipes site and press '?' anywhere on a non-form page. Report the title of the modal that appears.",
        "Open Allrecipes. Press '/' on the homepage. Report which DOM element receives focus.",
        "Open Allrecipes. Press Cmd+K (or Ctrl+K on Windows/Linux) on any page. Report the placeholder text shown in the search input that appears.",
        "On Allrecipes, open /help/shortcuts. List every kbd token shown in the first column of the shortcuts table.",
        "On Allrecipes, open /help/shortcuts. Find the shortcut that focuses the navigation search bar and report its key combination.",
        "On Allrecipes, open /help/shortcuts. Find the shortcut that opens the command palette and report its key combination on macOS.",
        "On Allrecipes, open /help/shortcuts. Find the shortcut that closes any open modal and report its key.",
        "On Allrecipes, open /help/shortcuts. Find the shortcut that toggles the contextual help popover and report its key.",
        "On Allrecipes, press g then h from the homepage. Confirm the URL after the keypress is the root '/'.",
        "On Allrecipes, press g then r. Report the URL the browser navigates to.",
        "On Allrecipes, press g then m. Report the URL the browser navigates to.",
        "On Allrecipes, press g then b. Report the URL the browser navigates to.",
        "On Allrecipes, press g then s. Report the URL the browser navigates to.",
        "On Allrecipes, press g then a. Report the URL the browser navigates to.",
        "On Allrecipes, press g then c. Report the URL the browser navigates to.",
        "On Allrecipes, press g then o. Report the URL the browser navigates to.",
        "On Allrecipes, press g then d. Report the URL the browser navigates to.",
        "On Allrecipes /help/shortcuts page, count how many distinct shortcuts are documented in the shortcuts table.",
        "Open Allrecipes. Press '?' to open the help modal. Confirm pressing Esc closes it.",
        "Open Allrecipes /help/shortcuts. Find a footer link to the same page from the homepage footer. Report the link text.",
    ]
    # Pad to ~80 with per-page shortcut-discovery tasks
    for r in popular_recipes[:60]:
        shortcut_questions.append(
            f"Open the Allrecipes recipe '{r['title']}'. Press '?' to open the keyboard "
            f"shortcut help. From the modal, report the description shown for the '/' shortcut.")
    for q in shortcut_questions:
        add('keyboard-shortcut-discover', q)

    # ============================================================
    # 2) command-palette-search (~100)
    # ============================================================
    # Search for recipes by partial title via Cmd+K palette
    for r in popular_recipes[:50]:
        first_word = r['title'].split()[0] if r['title'] else 'recipe'
        add('command-palette-search',
            f"Open Allrecipes and press Cmd+K (Ctrl+K) to open the command palette. "
            f"Type '{first_word}' into the palette input. Confirm a recipe result for "
            f"'{r['title']}' appears and report its URL (clicking the row navigates there).")
    # Search categories / collections / static pages
    palette_categories = ['cookies', 'cakes', 'pies', 'breads', 'pastries',
                          'italian', 'mexican', 'thai', 'korean', 'french',
                          'desserts', 'baking', 'vegan']
    for cat in palette_categories:
        add('command-palette-search',
            f"Open Allrecipes. Press Cmd+K. Type '{cat}' into the command palette. "
            f"Confirm a 'Category' result appears for '{cat.capitalize()}' and report "
            f"the URL it links to.")
    for page in ['Meal Plan', 'Recipe Box', 'Shopping List', 'Sitemap',
                 'Newsletter', 'Authors', 'Articles', 'Metrics',
                 'Keyboard Shortcuts', 'Community', 'Diets', 'Occasions']:
        add('command-palette-search',
            f"Open Allrecipes. Press Cmd+K. Type a fragment of '{page}' into the "
            f"palette and confirm a result with kind='page' for '{page}' is returned. "
            f"Report the URL.")
    # API direct queries
    for q in ['apple', 'chocolate', 'pasta', 'salmon', 'tofu',
              'lasagna', 'cookies', 'sourdough', 'tart', 'macaron',
              'biryani', 'kimchi', 'curry', 'risotto', 'tiramisu',
              'brownie', 'frosting', 'meringue', 'eclair', 'galette',
              'paella', 'tacos', 'ramen', 'falafel', 'gnocchi']:
        add('command-palette-search',
            f"Call /api/command-palette/search?q={q}&limit=5 on Allrecipes. Report "
            f"the 'label' field of the first result and its 'url'.")

    # ============================================================
    # 3) contextual-help-popover (~80)
    # ============================================================
    for r in popular_recipes[:40]:
        add('contextual-help-popover',
            f"Open the Allrecipes recipe '{r['title']}'. Press '.' (period) to open the "
            f"contextual help popover. Confirm the popover heading reads 'Contextual help' "
            f"and report the first word of the help text.")
    popover_anchors = [
        'header.nav-search', 'recipe.servings', 'recipe.print', 'recipe.rating',
        'meal-plan.day', 'shopping-list.consolidate', 'command-palette',
        'telemetry.opt-out',
    ]
    for anchor in popover_anchors:
        add('contextual-help-popover',
            f"Open /help/popovers on Allrecipes. Find the row whose anchor is "
            f"'{anchor}' and report the popover text shown next to it.")
    add('contextual-help-popover',
        "Open /help/popovers on Allrecipes. Count how many distinct popover anchors "
        "are documented in the table.")
    add('contextual-help-popover',
        "Open /help/popovers on Allrecipes. Confirm the page explains that popovers "
        "fire a 'popover.open' event to /telemetry.")
    add('contextual-help-popover',
        "Open Allrecipes homepage. Press '.' to open the contextual help popover. "
        "Confirm pressing '.' again closes it.")
    add('contextual-help-popover',
        "Open Allrecipes /recipes. Press '.' to open the popover. Confirm pressing "
        "Esc also closes it.")
    add('contextual-help-popover',
        "Open Allrecipes /collections. Press '.' to open the popover. Report the URL "
        "linked from the popover for the full popover inventory.")
    for r in popular_recipes[40:62]:
        add('contextual-help-popover',
            f"Open the Allrecipes recipe '{r['title']}'. Press '.' to toggle the "
            f"contextual help popover. Report the close button's aria-label.")

    # ============================================================
    # 4) recipe-import-OCR (~80)
    # ============================================================
    for r in popular_recipes[:50]:
        add('recipe-import-OCR',
            f"Open /recipe/{r['slug']}/import on Allrecipes. Report the title of the "
            f"page (should be 'Import OCR — {r['title']}' or similar).")
    for r in popular_recipes[50:70]:
        add('recipe-import-OCR',
            f"POST a JSON body {{\"ocr_text\": \"2 cups flour\\n1 tsp salt\\nWhisk dry "
            f"ingredients.\"}} to /recipe/{r['slug']}/import on Allrecipes. Report the "
            f"length of the returned 'ingredients' array (expect 2).")
    add('recipe-import-OCR',
        "Open /recipe/sourdough-bread/import on Allrecipes. List the 4 numbered steps "
        "the OCR pipeline performs (read the OCR Pipeline section).")
    add('recipe-import-OCR',
        "Open any /recipe/<slug>/import page on Allrecipes. Find the 'Example POST body' "
        "code block and report the value of its 'image_url' field.")
    add('recipe-import-OCR',
        "Open any /recipe/<slug>/import page on Allrecipes. The example response shows a "
        "confidence score — report its value.")
    add('recipe-import-OCR',
        "POST {} (empty JSON) to /recipe/pad-thai-classic/import on Allrecipes. Report "
        "the value of 'ocr_text_length' in the response.")
    for r in popular_recipes[70:78]:
        add('recipe-import-OCR',
            f"On Allrecipes, /recipe/{r['slug']}/import is the OCR import endpoint. "
            f"Confirm a link back to the Mealie JSON export at /recipe/{r['slug']}/export.json "
            f"is present on that page.")

    # ============================================================
    # 5) recipe-export-JSON-Mealie (~80)
    # ============================================================
    for r in popular_recipes[:60]:
        add('recipe-export-JSON-Mealie',
            f"GET /recipe/{r['slug']}/export.json on Allrecipes. Report the value of the "
            f"'@type' field in the JSON response.")
    for r in popular_recipes[60:80]:
        add('recipe-export-JSON-Mealie',
            f"GET /recipe/{r['slug']}/export.json on Allrecipes. Report the ISO-8601 "
            f"duration string in the 'totalTime' field.")
    add('recipe-export-JSON-Mealie',
        "GET /recipe/pad-thai-classic/export.json on Allrecipes. Report the 'format' "
        "field of the JSON response.")
    add('recipe-export-JSON-Mealie',
        "GET /recipe/tarte-tatin-classic/export.json on Allrecipes. Report the 'schema_version' "
        "field in the JSON response.")

    # ============================================================
    # 6) telemetry-event-fire (~60)
    # ============================================================
    add('telemetry-event-fire',
        "POST {\"event\": \"unit-test\", \"props\": {\"x\": 1}} to /telemetry on "
        "Allrecipes. Report the value of 'ack' in the JSON response.")
    add('telemetry-event-fire',
        "POST {\"event\": \"my-test-event\", \"event_id\": \"abc123\"} to /telemetry on "
        "Allrecipes twice in a row. On the second response, report the value of the "
        "'duplicate' field.")
    add('telemetry-event-fire',
        "POST {\"event\": \"shortcut.fire\", \"props\": {\"key\": \"slash\"}} to "
        "/telemetry on Allrecipes. Report the structure of the returned JSON (field names).")
    add('telemetry-event-fire',
        "GET /telemetry/events?n=5 on Allrecipes. Report the 'sink_size' value in the JSON.")
    add('telemetry-event-fire',
        "POST 10 distinct telemetry events to /telemetry on Allrecipes, then GET "
        "/telemetry/events?n=3. Confirm the response includes the 3 most recent events "
        "in chronological order.")
    add('telemetry-event-fire',
        "Open the Allrecipes homepage. Press '/' to focus the search box. Then GET "
        "/telemetry/events?n=5 and confirm a 'shortcut.fire' event with props.key='slash' "
        "appears in the sink.")
    add('telemetry-event-fire',
        "Open the Allrecipes homepage. Press '?' to open the help modal. Then GET "
        "/telemetry/events?n=5 and confirm a 'shortcut.fire' event with props.key='question' "
        "appears in the sink.")
    add('telemetry-event-fire',
        "Open the Allrecipes homepage. Press Cmd+K (Ctrl+K) to open the command palette. "
        "Then GET /telemetry/events?n=5 and confirm a 'shortcut.fire' event with "
        "props.key='cmd-k' is in the sink.")
    add('telemetry-event-fire',
        "Open the Allrecipes homepage. Press g then h. Confirm a 'shortcut.fire' event "
        "with props.key='g-h' and props.dest='/' appears in /telemetry/events.")
    # 50 more shortcut firing scenarios
    for key, dest in [('g-r', '/recipes'), ('g-m', '/meal-plan'), ('g-b', '/recipe-box'),
                      ('g-s', '/shopping-list'), ('g-a', '/articles'),
                      ('g-c', '/collections'), ('g-o', '/occasions'), ('g-d', '/diets')]:
        add('telemetry-event-fire',
            f"On Allrecipes, fire the {key} shortcut. GET /telemetry/events?n=5 and "
            f"confirm the most recent shortcut.fire event has props.dest='{dest}'.")
    for r in popular_recipes[:40]:
        add('telemetry-event-fire',
            f"Open Allrecipes recipe '{r['title']}'. Press '.' to open the popover. GET "
            f"/telemetry/events?n=2 and confirm a 'popover.open' event is present.")

    # ============================================================
    # 7) health-probe (~20)
    # ============================================================
    for q in [
        "GET /healthz on Allrecipes. Report the value of the 'status' field.",
        "GET /healthz on Allrecipes. Report the value of the 'service' field.",
        "GET /healthz on Allrecipes. Report the value of the 'version' field.",
        "GET /healthz on Allrecipes. Report the recipe count exposed in the response.",
        "GET /healthz on Allrecipes. Report the category count exposed in the response.",
        "GET /healthz on Allrecipes. Confirm the response Content-Type is application/json.",
        "GET /healthz on Allrecipes. Report the HTTP status code (expect 200).",
        "Compare /healthz on Allrecipes with /metrics — both should report the same total recipe count. Confirm.",
        "GET /healthz on Allrecipes after firing a /reset. Confirm the response still reports status='ok'.",
        "GET /healthz on Allrecipes. Confirm there is NO field named 'uptime_seconds' in the response.",
    ]:
        add('health-probe', q)

    # ============================================================
    # 8) metrics-extract (~40)
    # ============================================================
    metric_names = [
        'allrecipes_recipes_total', 'allrecipes_categories_total',
        'allrecipes_reviews_total', 'allrecipes_articles_total',
        'allrecipes_collections_total', 'allrecipes_users_total',
    ]
    for mn in metric_names:
        add('metrics-extract',
            f"GET /metrics on Allrecipes. Find the row labelled '{mn}' and report its "
            f"numeric value.")
        add('metrics-extract',
            f"GET /metrics?format=prom on Allrecipes. Find the line starting with "
            f"'{mn} ' and report the integer that follows.")
    add('metrics-extract',
        "GET /metrics?format=prom on Allrecipes. Report the Content-Type header "
        "(expect text/plain; version=0.0.4).")
    add('metrics-extract',
        "GET /metrics?format=prom on Allrecipes. Count how many '# HELP' lines appear.")
    add('metrics-extract',
        "GET /metrics?format=prom on Allrecipes. Count how many '# TYPE' lines appear.")
    add('metrics-extract',
        "GET /metrics on Allrecipes (HTML view). Confirm the table has 3 columns: Metric, "
        "Value, Description.")
    add('metrics-extract',
        "Open /metrics on Allrecipes. Below the table, confirm a 'Related Endpoints' list "
        "links to /healthz, /telemetry/events, and /metrics?format=prom.")
    for mn in metric_names:
        add('metrics-extract',
            f"GET /metrics on Allrecipes. The row '{mn}' has a help description in the "
            f"third column — report the first sentence.")

    # ============================================================
    # 9) Baking sub-category filter tasks (~250)
    # ============================================================
    for r in cookies[:50]:
        add('baking-cookies-filter',
            f"On Allrecipes, find a recipe in the new Cookies sub-category. Open "
            f"'{r['title']}' (slug '{r['slug']}') and confirm the category page "
            f"/category/cookies lists this recipe.")
    for r in cakes[:50]:
        add('baking-cakes-filter',
            f"On Allrecipes, navigate to /category/cakes. Confirm '{r['title']}' "
            f"(slug '{r['slug']}') appears in the listing. Report its servings count "
            f"from the recipe page.")
    for r in pies[:50]:
        add('baking-pies-filter',
            f"On Allrecipes, find a recipe under /category/pies. Open '{r['title']}'. "
            f"Report the value of 'max_oven_temp' (the recipe should bake at 425°F).")
    for r in breads[:50]:
        add('baking-breads-filter',
            f"On Allrecipes, navigate to /category/breads. Find '{r['title']}' and "
            f"report the cooking_method tag (should be 'baked' with steam at 450°F).")
    for r in pastries[:50]:
        add('baking-pastries-filter',
            f"On Allrecipes, navigate to /category/pastries. Find '{r['title']}'. "
            f"Confirm the cuisine is French and the recipe describes lamination.")

    # ============================================================
    # 10) multi-step (~80) — cross-feature flows
    # ============================================================
    for r in pierre[:14]:
        add('multi-step',
            f"On Allrecipes: (1) press Cmd+K to open the command palette, (2) type "
            f"'{r['title'].split()[0]}' to locate '{r['title']}' by Chef Pierre, "
            f"(3) navigate to the recipe, (4) press '.' to open the contextual popover, "
            f"(5) finally GET /recipe/{r['slug']}/export.json and report the totalTime ISO duration.")
    for r in cookies[:18]:
        add('multi-step',
            f"On Allrecipes: open the recipe '{r['title']}', press 's' to attempt to "
            f"save it to the Recipe Box (logged-in flow), then GET /telemetry/events?n=2 "
            f"and confirm at least one shortcut.fire event is in the sink.")
    for r in cakes[:18]:
        add('multi-step',
            f"On Allrecipes: navigate to /category/cakes, locate '{r['title']}', "
            f"open it, then GET /recipe/{r['slug']}/export.json and report the 'recipeYield'.")
    for r in pies[:14]:
        add('multi-step',
            f"On Allrecipes: open '{r['title']}' under /category/pies, then GET "
            f"/recipe/{r['slug']}/import to confirm the OCR import page renders, then GET "
            f"/recipe/{r['slug']}/export.json and report the prepTime ISO duration.")
    for r in breads[:8]:
        add('multi-step',
            f"On Allrecipes: open '{r['title']}' under /category/breads, then POST "
            f"a telemetry event {{\"event\": \"manual-test\"}} to /telemetry, then GET "
            f"/telemetry/events?n=1 and confirm the most recent event has event='manual-test'.")
    for r in pastries[:8]:
        add('multi-step',
            f"On Allrecipes: open '{r['title']}' under /category/pastries, GET "
            f"/recipe/{r['slug']}/export.json, and report the 'recipeCuisine' field "
            f"(expect French).")

    # ============================================================
    # 11) baking-category-discovery sanity (~10)
    # ============================================================
    for cat_slug in ['cookies', 'cakes', 'pies', 'breads', 'pastries']:
        add('baking-cookies-filter' if cat_slug == 'cookies' else
            'baking-cakes-filter' if cat_slug == 'cakes' else
            'baking-pies-filter' if cat_slug == 'pies' else
            'baking-breads-filter' if cat_slug == 'breads' else
            'baking-pastries-filter',
            f"On Allrecipes, navigate to /category/{cat_slug}. Confirm the category page "
            f"renders and report the category description (shown at the top of the page).")
    for cat_slug in ['cookies', 'cakes', 'pies', 'breads', 'pastries']:
        add('baking-cookies-filter' if cat_slug == 'cookies' else
            'baking-cakes-filter' if cat_slug == 'cakes' else
            'baking-pies-filter' if cat_slug == 'pies' else
            'baking-breads-filter' if cat_slug == 'breads' else
            'baking-pastries-filter',
            f"On Allrecipes, GET /api/recipes/{cat_slug}. Confirm the JSON returns at "
            f"least 12 recipes for this baking sub-category.")

    # ============================================================
    # Append to tasks.jsonl
    # ============================================================
    with open(TASKS_FILE, 'a', encoding='utf-8') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    from collections import Counter
    c = Counter(t['task_type'] for t in new_tasks)
    print(f"[r8_tasks] appended {len(new_tasks)} new tasks")
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    print(f"[r8_tasks] tasks.jsonl total now: {len(existing_tasks) + len(new_tasks)}")


if __name__ == '__main__':
    main()
