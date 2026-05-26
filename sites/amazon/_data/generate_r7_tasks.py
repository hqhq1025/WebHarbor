#!/usr/bin/env python3
"""Generate R7 tasks — SEO / multilang / performance / accessibility /
A/B / voice-shopping / multi-step.

Appends ~870 deterministically generated tasks to tasks.jsonl, starting from
the next free Amazon--N id. Output structure matches the existing tasks
(same keys: web_name, id, ques, web, upstream_url).

Run once during R7 polish; downstream rebuilds re-use the resulting
tasks.jsonl (tasks file is not regenerated at docker-build time).
"""
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'instance_seed', 'amazon_store.db')
TASKS_PATH = os.path.join(BASE_DIR, '..', 'tasks.jsonl')
WEB_LOCAL = 'http://localhost:40001/'
WEB_UPSTREAM = 'https://www.amazon.com/'


def load_slugs(con, category, limit=60):
    rows = con.execute(
        "SELECT slug, name FROM products WHERE category_slug=? ORDER BY id LIMIT ?",
        (category, limit),
    ).fetchall()
    return rows


def next_id(start, n):
    return [f'Amazon--{i}' for i in range(start, start + n)]


def gen():
    con = sqlite3.connect(DB_PATH)

    # Discover the next free ID from the existing tasks.jsonl.
    next_n = 0
    if os.path.exists(TASKS_PATH):
        with open(TASKS_PATH) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get('id', '').startswith('Amazon--'):
                    try:
                        n = int(obj['id'].split('--', 1)[1])
                        next_n = max(next_n, n + 1)
                    except ValueError:
                        pass

    # Curated product samples — feeds the question templates below.
    grocery = load_slugs(con, 'grocery', 60)
    audible = load_slugs(con, 'audible', 60)
    kindle = load_slugs(con, 'kindle', 60)
    electronics = load_slugs(con, 'electronics', 30)
    books = load_slugs(con, 'books', 30)
    home = load_slugs(con, 'home', 30)
    fashion = load_slugs(con, 'fashion', 30)
    beauty = load_slugs(con, 'beauty', 30)
    pool = electronics + books + home + fashion + beauty + grocery[:20]

    tasks = []

    # ---- 1) SEO product-schema-validate (120 tasks) ----------------------
    for slug, name in pool[:60]:
        tasks.append(
            f"Open /product/{slug}/schema.json and report (a) the price under "
            f"the offers field and (b) the availability URL. The page must "
            f"return Content-Type application/ld+json."
        )
        tasks.append(
            f"On the product page /product/{slug}, find the <script "
            f"type=\"application/ld+json\"> block. Confirm it declares "
            f"@type Product and report the price + priceCurrency."
        )

    # ---- 2) multilang DE / FR / JP listing (110 tasks) -------------------
    locales = [('de-DE', 'Deutsch'), ('fr-FR', 'Français'),
               ('ja-JP', '日本語'), ('en-DE', 'English (Germany)')]
    for slug, name in pool[:25]:
        for code, label in locales:
            tasks.append(
                f"Navigate to /-/{code}/product/{slug}. Report the active "
                f"locale shown in the top-right language switcher (it should "
                f"highlight {label}) and the og:locale meta-tag value rendered "
                f"in the page <head>."
            )
        # Also one per-product hreflang validate.
        tasks.append(
            f"Open /product/{slug} and list every <link rel=\"alternate\" "
            f"hreflang=...> URL you find in the page head. Report the count."
        )

    # ---- 3) performance page-weight (90 tasks) ---------------------------
    routes = ['/', '/c/electronics', '/c/computers', '/c/home',
              '/c/fashion', '/c/books', '/c/beauty', '/c/sports',
              '/c/toys', '/c/grocery', '/c/audible', '/c/kindle',
              '/deals', '/bestsellers', '/search']
    for r in routes:
        tasks.append(
            f"Fetch /health/page-weight and report the page_weight_kb value "
            f"for the route '{r}', plus the within_budget flag."
        )
    for _ in range(2):
        tasks.append(
            "Fetch /health/page-weight and report (a) the budget_kb ceiling, "
            "(b) the count of routes that are within budget, and (c) the "
            "value of critical_css_inlined."
        )
    # Page-weight per-product sanity (45 tasks)
    for slug, name in pool[:45]:
        tasks.append(
            f"Open /product/{slug} and look at the page <head>. Confirm that "
            "a <style> block with the comment 'critical-css-inline-v1' is "
            "present and that <link rel=\"stylesheet\"> for main.css appears "
            "AFTER it."
        )

    # ---- 4) accessibility WCAG-AA (110 tasks) ----------------------------
    tasks.append(
        "Open /.well-known/accessibility and report (a) the conformance_target "
        "string and (b) the count of items in 'features'."
    )
    tasks.append(
        "Fetch /.well-known/accessibility and list any entries in the "
        "known_issues array."
    )
    for slug, name in pool[:50]:
        tasks.append(
            f"Open /product/{slug}. Use keyboard tab navigation only; confirm "
            "the first focusable element on the page is the 'Skip to main "
            "content' link, and that pressing Enter on it jumps to the main "
            "content."
        )
    for r in routes[:10]:
        tasks.append(
            f"Open {r}. Confirm that every <img> tag in the rendered HTML has "
            "a non-empty alt attribute. Report the count of img tags inspected."
        )
    for r in routes[10:]:
        tasks.append(
            f"Open {r}. Confirm that the search input in the top nav has a "
            "visible :focus outline when tabbed to (not display:none)."
        )
    # Extra accessibility tasks across products
    for slug, name in pool[50:90]:
        tasks.append(
            f"Open /product/{slug}. Verify the price element has a contrast "
            "ratio sufficient for WCAG AA (the orange #cc0c39-on-white pair). "
            "Report any aria-label on the Add-to-cart button."
        )

    # ---- 5) A/B test toggle (90 tasks) -----------------------------------
    cohorts = [('prime-banner', 'control'), ('prime-banner', 'variant'),
               ('search-rank', 'control'), ('search-rank', 'variant')]
    for cohort, bucket in cohorts:
        for slug, name in pool[:15]:
            tasks.append(
                f"POST /ab-test/toggle with cohort={cohort} and bucket={bucket}; "
                f"then GET /ab-test/toggle and report the active.{cohort} value. "
                f"Finally open /product/{slug} and confirm the page still renders."
            )
    # A/B discovery tasks
    for _ in range(5):
        tasks.append(
            "GET /ab-test/toggle (no params). Report (a) the list of cohorts "
            "and (b) the buckets available."
        )
    tasks.append(
        "POST /ab-test/toggle cohort=prime-banner bucket=does-not-exist; "
        "confirm the API rejects it (ok=false or buckets list returned)."
    )
    tasks.append(
        "Toggle yourself into the 'search-rank=variant' bucket via POST "
        "/ab-test/toggle. Then GET /ab-test/toggle and verify active.search-rank "
        "now reports 'variant'."
    )

    # ---- 6) voice shopping via Alexa (90 tasks) --------------------------
    utterances_template = [
        ("reorder my {name}", 'reorder'),
        ("add a {name} to my cart", 'add-to-cart'),
        ("find {name} under 100 dollars", 'search'),
        ("search for {name}", 'search'),
    ]
    for slug, name in pool[:20]:
        # Use first 4 words of name to keep utterance natural.
        short = ' '.join(name.split()[:4])
        for utt_tmpl, intent in utterances_template:
            utt = utt_tmpl.format(name=short)
            tasks.append(
                f"POST /voice/alexa-shopping with utterance='{utt}'. Report "
                f"the detected intent (should be {intent}) and the first "
                f"product slug under 'matches'."
            )
    tasks.append(
        "GET /voice/alexa-shopping with no parameters; report the list of "
        "example utterances from the response."
    )
    tasks.append(
        "POST /voice/alexa-shopping with utterance='find AAA batteries under "
        "20 dollars'. Report the detected intent and the count of matches."
    )

    # ---- 7) multi-step (350 tasks) ---------------------------------------
    # Each multi-step task chains an SEO check + a locale change + a search.
    multi_pool = pool[:50]
    multi_variants = [
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: switch to locale {loc} via /lang/switch?locale={loc}. "
            f"Step 2: open /product/{slug} and copy the canonical URL from "
            f"the <link rel='canonical'> tag. Step 3: open the schema endpoint "
            f"at /product/{slug}/schema.json and report the price. Step 4: "
            f"toggle yourself into the {cohort}={bucket} A/B bucket."
        ),
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: open /sitemap.xml; confirm it lists /c/{slug.split('-')[0]}. "
            f"Step 2: open /robots.txt and report whether '/cart' is disallowed. "
            f"Step 3: open /product/{slug} and report the og:type value."
        ),
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: GET /health/page-weight. Step 2: pick the route with "
            f"the highest page_weight_kb. Step 3: open that route and confirm "
            f"the response 200s. Step 4: visit /product/{slug} and confirm "
            f"the JSON-LD Product script tag is present."
        ),
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: POST /voice/alexa-shopping utterance='reorder my "
            f"{' '.join(name.split()[:3])}'. Step 2: take the first match slug "
            f"and open /product/<that-slug>. Step 3: verify a Product JSON-LD "
            f"block is present in the HTML."
        ),
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: switch to {loc} via the language switcher in the top "
            f"nav. Step 2: navigate to /c/grocery and apply the 'usda-organic' "
            f"feature tag filter. Step 3: open the first result and confirm "
            f"the og:locale meta tag reflects {loc}."
        ),
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: open /-/{loc}/product/{slug}. Step 2: open /robots.txt "
            f"and confirm the Sitemap: line points at /sitemap.xml. Step 3: "
            f"fetch /sitemap.xml and confirm the product slug '{slug}' is "
            f"listed."
        ),
        lambda slug, name, loc, cohort, bucket: (
            f"Step 1: GET /.well-known/accessibility. Step 2: open /product/"
            f"{slug} and confirm a skip-to-main-content link is the first "
            f"focusable element. Step 3: tab to it and press Enter."
        ),
    ]
    for i, (slug, name) in enumerate(multi_pool):
        loc = locales[i % len(locales)][0]
        cohort, bucket = cohorts[i % len(cohorts)]
        for variant in multi_variants:
            tasks.append(variant(slug, name, loc, cohort, bucket))

    # ---- Wire tasks into tasks.jsonl --------------------------------------
    ids = next_id(next_n, len(tasks))
    out_rows = []
    for tid, ques in zip(ids, tasks):
        out_rows.append({
            'web_name': 'Amazon',
            'id': tid,
            'ques': ques,
            'web': WEB_LOCAL,
            'upstream_url': WEB_UPSTREAM,
        })

    with open(TASKS_PATH, 'a') as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    con.close()
    print(f"appended {len(out_rows)} tasks starting at Amazon--{next_n}")


if __name__ == '__main__':
    gen()
