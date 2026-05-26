#!/usr/bin/env python3
"""R7 task generator — extends ``tasks.jsonl`` with ~750 new tasks covering
the R7 polish surface: SEO endpoints (canonical / OG / JSON-LD / sitemap.xml
/ robots.txt / RSS), multi-language stub (/lang/<x>/), performance / a11y
edge cases, and the new international-cuisine + vegetarian-by-protein
variant catalog. Idempotent.

Task types added:
  * seo-canonical-extract
  * social-share-OG-tag
  * recipe-schema-JSON-LD
  * sitemap-xml-extract
  * robots-txt-extract
  * rss-feed-validity
  * language-switch-i18n
  * performance-loading-time
  * accessibility-audit
  * korean-regional-filter
  * thai-regional-filter
  * mexican-regional-filter
  * vegetarian-by-protein-filter
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
    print(f"[r7_tasks] loaded {len(existing_tasks)} existing tasks")

    conn = sqlite3.connect(SEED_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT slug, title, cuisine FROM recipe "
                "WHERE author_name='Korean-Regional Test Kitchen' "
                "ORDER BY id LIMIT 80")
    korean = cur.fetchall()
    cur.execute("SELECT slug, title FROM recipe "
                "WHERE author_name='Thai-Regional Test Kitchen' "
                "ORDER BY id LIMIT 80")
    thai = cur.fetchall()
    cur.execute("SELECT slug, title, main_ingredient FROM recipe "
                "WHERE author_name='Mexican-Regional Test Kitchen' "
                "ORDER BY id LIMIT 80")
    mexican_r = cur.fetchall()
    cur.execute("SELECT slug, title, main_ingredient FROM recipe "
                "WHERE author_name='Vegetarian-By-Protein Test Kitchen' "
                "ORDER BY id LIMIT 80")
    veg = cur.fetchall()

    cur.execute("SELECT slug, title, cuisine, calories, total_time_mins, "
                "avg_rating, review_count, author_name "
                "FROM recipe WHERE review_count >= 5 ORDER BY id LIMIT 200")
    popular_recipes = cur.fetchall()

    cur.execute("SELECT slug, title FROM article ORDER BY id LIMIT 25")
    articles = cur.fetchall()

    cur.execute("SELECT slug, title FROM collection ORDER BY id")
    collections = cur.fetchall()

    cur.execute("SELECT DISTINCT author_name FROM recipe "
                "WHERE author_name LIKE 'Chef %' ORDER BY author_name")
    chefs = [row[0] for row in cur.fetchall()]
    conn.close()

    test_users = [
        ('alex.morgan@example.com', 'test1234', 'Alex'),
        ('priya.kumar@example.com', 'test1234', 'Priya'),
        ('jordan.lee@example.com', 'test1234', 'Jordan'),
        ('sam.taylor@example.com', 'test1234', 'Sam'),
    ]
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    new_tasks = []
    n = 0
    while f"Allrecipes--R7--{n}" in existing_ids:
        n += 1

    def add(task_type, ques):
        nonlocal n
        tid = f"Allrecipes--R7--{n}"
        while tid in existing_ids:
            n += 1
            tid = f"Allrecipes--R7--{n}"
        existing_ids.add(tid)
        new_tasks.append(make_task(tid, task_type, ques))
        n += 1

    # ============================================================
    # 1) seo-canonical-extract (~80) — read rel=canonical from <head>
    # ============================================================
    for r in popular_recipes[:80]:
        add('seo-canonical-extract',
            f"Open the Allrecipes recipe page for '{r['title']}'. From the HTML <head>, "
            f"extract the value of the rel=\"canonical\" link tag and report the full URL.")

    # ============================================================
    # 2) social-share-OG-tag (~60) — read og:title / og:description / og:image
    # ============================================================
    og_fields = [('og:title', 'og:title'), ('og:description', 'og:description'),
                 ('og:image', 'og:image'), ('og:url', 'og:url'),
                 ('twitter:card', 'twitter:card'), ('twitter:image', 'twitter:image')]
    for i, r in enumerate(popular_recipes[:60]):
        prop_label, prop_key = og_fields[i % len(og_fields)]
        add('social-share-OG-tag',
            f"Open the Allrecipes recipe '{r['title']}'. Inspect the Open Graph "
            f"meta tags in <head> and report the value of the '{prop_label}' "
            f"meta tag — needed for the recipe's social-share preview card.")

    # ============================================================
    # 3) recipe-schema-JSON-LD (~80) — extract field from <script type="application/ld+json">
    # ============================================================
    schema_fields = ['recipeYield', 'totalTime', 'prepTime', 'cookTime',
                     'recipeCuisine', 'aggregateRating.ratingValue',
                     'aggregateRating.reviewCount', 'nutrition.calories', 'author.name']
    for i, r in enumerate(popular_recipes[:80]):
        field = schema_fields[i % len(schema_fields)]
        add('recipe-schema-JSON-LD',
            f"Open the Allrecipes recipe '{r['title']}'. Inside the "
            f"application/ld+json structured-data script in <head>, find the "
            f"Recipe object and report the '{field}' field.")

    # ============================================================
    # 4) sitemap-xml-extract (~40)
    # ============================================================
    for i, r in enumerate(popular_recipes[:40]):
        add('sitemap-xml-extract',
            f"Open /sitemap.xml on Allrecipes. Verify that the page lists "
            f"a <loc> entry for '{r['title']}' (path /recipe/{r['slug']}) and "
            f"report its <priority> value.")
    add('sitemap-xml-extract',
        "Open /sitemap.xml on Allrecipes. Report how many distinct <url> "
        "entries it contains (under the urlset).")
    add('sitemap-xml-extract',
        "Open /sitemap.xml on Allrecipes. Confirm that the root URL "
        "(<loc>http://localhost:40000/</loc>) appears with priority 1.0.")

    # ============================================================
    # 5) robots-txt-extract (~10)
    # ============================================================
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Report which User-agent the rules apply to.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. List every path that is Disallow-ed.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Report the URL of the XML sitemap "
        "advertised at the bottom of the file.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Is /recipe-box disallowed? Yes or No.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Is the /api/ prefix crawlable? Yes or No.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Confirm both the XML sitemap and the "
        "RSS feed are listed under Sitemap: directives.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Report whether /account is allowed or disallowed.")
    add('robots-txt-extract',
        "Open /robots.txt on Allrecipes. Report whether /meal-plan is allowed or disallowed.")

    # ============================================================
    # 6) rss-feed-validity (~40)
    # ============================================================
    for art in articles[:25]:
        add('rss-feed-validity',
            f"Open /feed.rss on Allrecipes. Verify that an <item> entry "
            f"with <title>{art['title']}</title> appears in the channel. "
            f"Report its <pubDate>.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report the <title> of the RSS channel.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report how many <item> entries appear "
        "in the channel.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report the <language> declared in "
        "the channel.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report the <link> URL declared at "
        "the channel level (NOT the per-item link).")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report the version attribute of the "
        "<rss> root element.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Confirm that the channel <description> "
        "mentions cooking tips or technique.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Verify the feed declares "
        "Content-Type application/rss+xml in the HTTP response headers.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report the title of the FIRST "
        "<item> in the channel.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report the title of the LAST "
        "<item> in the channel.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Confirm that every <item> entry "
        "carries a <guid> matching its <link>.")
    add('rss-feed-validity',
        "Open /feed.rss on Allrecipes. Report whether the RSS XML declares "
        "version=\"2.0\".")

    # ============================================================
    # 7) language-switch-i18n (~80)
    # ============================================================
    lang_labels = [('es', 'Spanish', 'Español'),
                    ('fr', 'French', 'Français'),
                    ('de', 'German', 'Deutsch'),
                    ('zh', 'Chinese', '中文')]
    for i in range(80):
        lang_code, lang_en, lang_native = lang_labels[i % 4]
        if i % 4 < 2:
            add('language-switch-i18n',
                f"On Allrecipes, click the language switcher in the header and "
                f"navigate to the {lang_en} version (/lang/{lang_code}/). "
                f"Report the banner text shown at the top of the page.")
        else:
            r = popular_recipes[i % len(popular_recipes)]
            add('language-switch-i18n',
                f"On Allrecipes, navigate to /lang/{lang_code}/. Confirm the "
                f"<html lang=\"{lang_code}\"> attribute is set and that the "
                f"language banner uses the label '{lang_native}'. Then open "
                f"the recipe '{r['title']}' to verify the canonical URL still "
                f"points at the English /recipe/<slug> path (no /lang prefix).")

    # ============================================================
    # 8) performance-loading-time (~50)
    # ============================================================
    add('performance-loading-time',
        "Open the Allrecipes homepage and confirm that the <head> includes "
        "a <link rel=\"preload\" as=\"style\"> directive for the critical CSS.")
    add('performance-loading-time',
        "Open the Allrecipes loading-skeleton demo at /__loading-demo. "
        "Confirm the skeleton placeholders render with shimmer animation.")
    for r in popular_recipes[:24]:
        add('performance-loading-time',
            f"Open the Allrecipes recipe '{r['title']}'. Confirm that critical CSS "
            f"is preloaded and that the recipe hero image carries a defined "
            f"image width/height (helps prevent layout shift).")
    add('performance-loading-time',
        "Open /sitemap.xml on Allrecipes. Report the Content-Type header "
        "the server returns (application/xml expected).")
    add('performance-loading-time',
        "Open /robots.txt on Allrecipes. Report the Content-Type header "
        "the server returns (text/plain expected).")
    add('performance-loading-time',
        "Open /feed.rss on Allrecipes. Report the Content-Type header "
        "the server returns (application/rss+xml expected).")
    add('performance-loading-time',
        "Open the Allrecipes 429 rate-limit demo at /__rate-limit-demo. "
        "Confirm the response status code is 429 and that a 'try again later' "
        "message is shown.")
    add('performance-loading-time',
        "Open the Allrecipes session-expired demo at /__session-expired-demo. "
        "Confirm the response status code is 401 and that a sign-in CTA is shown.")
    add('performance-loading-time',
        "Open the Allrecipes server-error demo at /__server-error-demo. "
        "Confirm the response status code is 500.")
    for r in popular_recipes[24:40]:
        add('performance-loading-time',
            f"Open the Allrecipes recipe '{r['title']}'. Confirm the canonical "
            f"URL in <head> matches the current page URL (without query string).")
    add('performance-loading-time',
        "Open the Allrecipes homepage and confirm that the page weight stays under "
        "a single CSS preload + the main CSS link (no duplicate large files).")
    add('performance-loading-time',
        "Open the Allrecipes index page. Verify that the JSON-LD WebSite schema "
        "includes a SearchAction pointing at /search?q={search_term_string}.")

    # ============================================================
    # 9) accessibility-audit (~40)
    # ============================================================
    add('accessibility-audit',
        "Open the Allrecipes homepage. Confirm the skip-to-content link "
        "(.skip-link) is present and that pressing Tab focuses it first.")
    add('accessibility-audit',
        "Open any Allrecipes page. Confirm the <html lang=\"en\"> attribute "
        "is correctly set for the default English UX.")
    add('accessibility-audit',
        "Open the Allrecipes header. Confirm the search input has an "
        "associated <label> (use visually-hidden) and the submit button has "
        "an aria-label.")
    add('accessibility-audit',
        "Open the Allrecipes navigation. Confirm the <nav> element has "
        "aria-label=\"Primary\" set.")
    add('accessibility-audit',
        "Open the Allrecipes recipe-box badge. Confirm it has aria-label "
        "describing the number of items.")
    for r in popular_recipes[:24]:
        add('accessibility-audit',
            f"Open the Allrecipes recipe '{r['title']}'. Confirm that the rating "
            f"stars carry an aria-label (or accessible name) describing the rating.")
    add('accessibility-audit',
        "Open the Allrecipes login page. Confirm every form input has an "
        "associated <label> (or aria-labelledby).")
    add('accessibility-audit',
        "Open the Allrecipes language switcher. Confirm every language link "
        "carries an aria-label (e.g. 'Spanish', 'French').")
    add('accessibility-audit',
        "Open the Allrecipes 404 page. Confirm the page heading is a <h1> "
        "(not visually-styled-as-h1).")
    add('accessibility-audit',
        "Open the Allrecipes flash-messages region. Confirm role=\"status\" "
        "and aria-live=\"polite\" are set so screen readers announce them.")
    add('accessibility-audit',
        "Open any Allrecipes hub page. Confirm <main id=\"main-content\"> "
        "is present and tabindex=\"-1\" so the skip-link can land focus.")

    # ============================================================
    # 10) korean-regional-filter (~50)
    # ============================================================
    for r in korean[:40]:
        add('korean-regional-filter',
            f"On Allrecipes, find a Korean-Regional recipe such as '{r['title']}'. "
            f"From the recipe detail page, report the gochujang quantity called for "
            f"in the ingredients list.")
    for i in range(10):
        add('korean-regional-filter',
            f"On Allrecipes, browse the Korean cuisine page and find a recipe whose "
            f"author is 'Korean-Regional Test Kitchen'. Open it and report the calorie count.")

    # ============================================================
    # 11) thai-regional-filter (~50)
    # ============================================================
    for r in thai[:40]:
        add('thai-regional-filter',
            f"On Allrecipes, find a Thai-Regional recipe such as '{r['title']}'. "
            f"From the recipe detail page, report which of the four Thai pillars "
            f"(salty, sour, sweet, spicy) the instructions emphasize first.")
    for i in range(10):
        add('thai-regional-filter',
            f"On Allrecipes, browse the Thai cuisine page and find a Thai-Regional "
            f"Test Kitchen recipe. Open it and confirm whether 'dairy-free' appears "
            f"in its dietary tags.")

    # ============================================================
    # 12) mexican-regional-filter (~50)
    # ============================================================
    for r in mexican_r[:40]:
        add('mexican-regional-filter',
            f"On Allrecipes, find a Mexican-Regional recipe such as '{r['title']}'. "
            f"From the recipe detail page, identify which Mexican region (Oaxacan / "
            f"Yucatecan / Pueblan / Sonoran / Veracruzano / Jalisciense) the title "
            f"refers to and report it.")
    for i in range(10):
        add('mexican-regional-filter',
            f"On Allrecipes, search for 'guajillo' and open a Mexican-Regional Test "
            f"Kitchen recipe from the results. Report its total time.")

    # ============================================================
    # 13) vegetarian-by-protein-filter (~60)
    # ============================================================
    proteins = ['tofu', 'tempeh', 'seitan', 'chickpea', 'lentil', 'jackfruit', 'mushroom', 'paneer']
    for r in veg[:50]:
        add('vegetarian-by-protein-filter',
            f"On Allrecipes, find a vegetarian recipe by main protein, e.g. "
            f"'{r['title']}'. Confirm 'vegetarian' is in its dietary tags and "
            f"report the main protein listed (one of: tofu, tempeh, seitan, "
            f"chickpea, lentil, jackfruit, mushroom, paneer).")
    for prot in proteins:
        add('vegetarian-by-protein-filter',
            f"On Allrecipes, find a Vegetarian-By-Protein Test Kitchen recipe "
            f"whose main protein is {prot}. Open it and confirm whether the "
            f"dietary tags include 'vegan' (true for non-dairy proteins, false "
            f"only for paneer).")
    for i in range(2):
        add('vegetarian-by-protein-filter',
            "On Allrecipes, search for 'vegetarian' and filter down to recipes "
            "by Vegetarian-By-Protein Test Kitchen. Report whether tofu, tempeh "
            "and seitan all appear in the result set.")

    # ============================================================
    # 14) multi-step (~100) — additional cross-page flows that exercise R7 surface
    # ============================================================
    for i in range(40):
        email, pw, name = test_users[i % len(test_users)]
        lang_code, lang_en, _ = lang_labels[i % 4]
        r = (korean + thai + mexican_r + veg)[i % (len(korean) + len(thai) + len(mexican_r) + len(veg))]
        add('multi-step',
            f"Log in as {email} ({pw}). Open /lang/{lang_code}/ on Allrecipes. "
            f"From the language banner, confirm {lang_en} is the active language. "
            f"Then navigate to /recipe/{r['slug']}, save it to {name}'s Recipe Box, "
            f"and verify the canonical URL in <head> does NOT include /lang/{lang_code}/.")
    for i in range(30):
        email, pw, name = test_users[i % len(test_users)]
        r = popular_recipes[i % len(popular_recipes)]
        day = days[i % len(days)]
        add('multi-step',
            f"Log in as {email} ({pw}). Open the Allrecipes recipe '{r['title']}'. "
            f"From the embedded JSON-LD Recipe schema, copy the totalTime field. "
            f"Then add the recipe to {day} dinner on {name}'s meal plan, and finally "
            f"add its ingredients to a new shopping list named '{name} {day} prep'.")
    for i in range(30):
        email, pw, name = test_users[i % len(test_users)]
        veg_recipe = veg[i % len(veg)]
        kor_recipe = korean[i % len(korean)]
        add('multi-step',
            f"Log in as {email} ({pw}). On Allrecipes, save the vegetarian recipe "
            f"'{veg_recipe['title']}' to {name}'s Recipe Box AND the Korean-Regional "
            f"recipe '{kor_recipe['title']}'. Then open /sitemap.xml and confirm "
            f"both recipe URLs are listed (priority 0.6) under the urlset.")

    # ============================================================
    # 15) Cross-cuisine variety (~80) — alternate-entry-same-task style for R7
    # ============================================================
    for i in range(40):
        r = (korean + thai + mexican_r)[i % (len(korean) + len(thai) + len(mexican_r))]
        add('alternate-entry-same-task',
            f"On Allrecipes, reach the recipe '{r['title']}' via TWO different entry "
            f"points: (1) the search box, and (2) the relevant Cuisine page in /cuisines. "
            f"Confirm both paths land on the same /recipe/<slug> URL and report it.")
    for i in range(40):
        r = veg[i % len(veg)]
        add('alternate-entry-same-task',
            f"On Allrecipes, reach the vegetarian recipe '{r['title']}' via TWO different "
            f"entry points: (1) the /diet/vegetarian filter page, and (2) the global "
            f"search box. Confirm both paths land on the same /recipe/<slug> URL.")

    # ============================================================
    # Write back
    # ============================================================
    print(f"[r7_tasks] generated {len(new_tasks)} new tasks")
    if not new_tasks:
        return
    with open(TASKS_FILE, 'a', encoding='utf-8') as f:
        for t in new_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f"[r7_tasks] wrote to {TASKS_FILE}; total tasks now: "
          f"{len(existing_tasks) + len(new_tasks)}")


if __name__ == '__main__':
    main()
