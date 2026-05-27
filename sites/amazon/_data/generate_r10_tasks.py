#!/usr/bin/env python3
"""Generate R10 tasks — cross-business multi-step flows.

Adds ~750 deterministic tasks that exercise R10 quality fixes (alias routes,
opensearch.xml, og-cover, form-validation feedback) PLUS cross-business
multi-step chains that touch 2+ business lines in a single agent flow:

  * Pharmacy + Pantry + Subscribe-Save "one-stop care kit"
  * Amazon Auto VIN-fit + browse + add-to-cart
  * Amazon Renewed grade-verify + return policy + add-to-cart
  * Amazon Household share + Subscribe-Save + Auto-Reorder
  * Kids FreeTime band + Amazon Custom monogram + cart
  * Amazon Live carousel deal + Warehouse-Deal open-box + checkout

Appends to tasks.jsonl, starting from the next free Amazon--N id.
"""
import json
import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'instance_seed', 'amazon_store.db')
TASKS_PATH = os.path.join(BASE_DIR, '..', 'tasks.jsonl')
WEB_LOCAL = 'http://localhost:40001/'
WEB_UPSTREAM = 'https://www.amazon.com/'


def load_slugs(con, where, limit=40):
    sql = f"SELECT slug, name, brand FROM products WHERE {where} ORDER BY id LIMIT ?"
    return con.execute(sql, (limit,)).fetchall()


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
                    except Exception:
                        pass

    tasks = []

    # Load deterministic pools — order-by-id keeps this stable.
    pharm = load_slugs(con, "category_slug='pharmacy'", 40)
    auto = load_slugs(con, "category_slug='auto'", 40)
    renewed = load_slugs(con, "category_slug='renewed'", 40)
    outlet = load_slugs(con, "category_slug='outlet'", 30)
    live = load_slugs(con, "category_slug='live_shopping'", 30)
    freetime = load_slugs(con, "category_slug='kids_freetime'", 30)
    household = load_slugs(con, "category_slug='household'", 20)
    bundles = load_slugs(con, "category_slug='bundles'", 60)
    custom = load_slugs(con, "category_slug='amazon_custom'", 40)
    mbya = load_slugs(con, "category_slug='made_by_amazon'", 60)
    seasonal = load_slugs(con, "category_slug='seasonal'", 40)
    warehouse = load_slugs(con, "category_slug='warehouse_deals'", 30)
    grocery = load_slugs(con, "category_slug='grocery'", 30)

    # ---- 1) R10 quality-fix tasks — alias routes / OG / favicon / opensearch (60) ----
    alias_pairs = [
        ('/freetime', '/kids/freetime'),
        ('/amazon-live', '/live-shopping'),
        ('/amazon-household', '/household'),
        ('/amazon-outlet', '/outlet'),
        ('/business', '/amazon-business'),
        ('/today-deals', '/todays-deals'),
        ('/today-s-deals', '/todays-deals'),
        ('/deals/today', '/todays-deals'),
        ('/c/pharmacy', '/pharmacy'),
        ('/c/rx', '/pharmacy'),
        ('/c/auto', '/amazon-auto'),
        ('/c/automotive', '/amazon-auto'),
        ('/c/renewed', '/amazon-renewed'),
        ('/c/refurbished', '/amazon-renewed'),
        ('/c/outlet', '/outlet'),
        ('/c/freetime', '/kids/freetime'),
        ('/c/kids', '/kids/freetime'),
        ('/live', '/live-shopping'),
    ]
    for src, dst in alias_pairs:
        tasks.append(
            f"GET {src} without following redirects. Confirm the response "
            f"status is 301 and the Location header is {dst}."
        )
        tasks.append(
            f"GET {src} with redirects followed. Confirm the final URL is "
            f"{dst} and the response is 200."
        )
    tasks.append(
        "GET /favicon.ico. Confirm the response status is 200 and the "
        "Content-Type starts with 'image/'."
    )
    tasks.append(
        "GET /favicon.ico twice. Confirm the response body is byte-identical "
        "between the two calls (no random salt in the favicon)."
    )
    tasks.append(
        "GET /opensearch.xml. Confirm the response is 200 and the body "
        "starts with '<?xml' and contains '<OpenSearchDescription'."
    )
    tasks.append(
        "GET /opensearch.xml. Parse the XML and confirm it contains exactly "
        "one Url element with type='text/html' whose template includes "
        "'{searchTerms}'."
    )
    tasks.append(
        "GET /opensearch.xml. Confirm the Content-Type header is "
        "'application/opensearchdescription+xml; charset=utf-8'."
    )
    tasks.append(
        "GET /static/images/homepage/og-cover.jpg. Confirm the response is "
        "200 and Content-Length is > 10000 (not a placeholder)."
    )
    tasks.append(
        "GET /. Find the <meta property=\"og:image\"> tag and confirm its "
        "content URL ends with '/static/images/homepage/og-cover.jpg'."
    )
    tasks.append(
        "GET / then GET the og:image URL from the meta tag. Confirm the "
        "image returns 200 and is a real JPEG (no 404 placeholder)."
    )
    tasks.append(
        "GET /sitemap.xml. Confirm the response is 200 and the body contains "
        "at least one <loc> tag ending with '/product/'."
    )

    # ---- 2) Address-form / payment-form validation feedback (40) ----------
    tasks.append(
        "Open /account/addresses/add. Submit the form with all fields blank "
        "(but include csrf_token). Confirm the response contains the string "
        "'Please correct the highlighted fields.' near the top of the form."
    )
    tasks.append(
        "Open /account/addresses/add. Submit only csrf_token (leave name, "
        "street, city, state, zip blank). Confirm the rendered page contains "
        "an element with id='err-full_name' AND id='err-address_line1' AND "
        "id='err-city' AND id='err-state' AND id='err-zip_code'."
    )
    tasks.append(
        "Open /account/addresses/add. Submit with full_name='', street, "
        "city, state, zip all filled. Confirm the full_name input has "
        "aria-invalid='true' and an error message is rendered below it."
    )
    tasks.append(
        "Open /account/payment/add. Submit with cardholder_name='' and "
        "card_number=''. Confirm both fields show aria-invalid='true' AND "
        "form-error messages are rendered for each."
    )
    tasks.append(
        "Open /account/payment/add. Submit with cardholder_name filled but "
        "card_number=''. Confirm only #err-card_number is rendered and "
        "#err-cardholder_name is NOT in the HTML."
    )
    tasks.append(
        "Open /account/payment/add. Submit with all fields valid. Confirm "
        "the success path (redirect to /account/payment) and no form-error "
        "element renders."
    )
    # Additional validation tasks
    for field, label in [('full_name', 'Full Name'), ('address_line1', 'Street'),
                         ('city', 'City'), ('state', 'State'),
                         ('zip_code', 'ZIP Code')]:
        tasks.append(
            f"POST /account/addresses/add with all fields filled except "
            f"{field}. Confirm the response renders the form again with "
            f"#err-{field} containing a non-empty error message."
        )
    for field in ('cardholder_name', 'card_number'):
        tasks.append(
            f"POST /account/payment/add with {field} empty (other fields "
            f"valid). Confirm the response renders #err-{field} and the "
            f"input has aria-invalid='true'."
        )

    # ---- 3) Cross-business: Pharmacy + Pantry + Subscribe-Save (110) ------
    care_kits = [r for r in bundles if 'care-kit' in (r[1] or '').lower()
                 or 'hsa' in (r[1] or '').lower()]
    if not care_kits:
        care_kits = bundles[:10]
    for slug, name, brand in care_kits[:30]:
        tasks.append(
            f"Step 1: GET /product/{slug}. Step 2: confirm the specs JSON "
            f"includes 'HSA Eligible: Yes'. Step 3: confirm the feature_tags "
            f"include both 'hsa-care' and 'bundle'."
        )
        tasks.append(
            f"Step 1: GET /pharmacy and read the otc count. Step 2: open "
            f"/product/{slug} and confirm Subscribe & Save is offered. "
            f"Step 3: POST /api/subscribe-save/enroll for product_slug="
            f"'{slug}' with interval=4 (weeks). Confirm enrolled=true."
        )
    rx_pool = [r for r in pharm if 'rx' in (r[2] or '').lower()
               or 'prescription' in (r[1] or '').lower()][:20]
    if not rx_pool:
        rx_pool = pharm[:20]
    for slug, name, brand in rx_pool[:15]:
        tasks.append(
            f"Step 1: GET /pharmacy. Step 2: open /product/{slug} and "
            f"confirm the rendered page contains 'Prescription Required: "
            f"Yes' (the Rx flag must surface to the agent)."
        )
        tasks.append(
            f"Step 1: GET /product/{slug}. Step 2: try to POST /api/cart "
            f"with product_slug='{slug}', quantity=1. Step 3: confirm the "
            f"response requires Rx verification (look for 'prescription' "
            f"in the error or warning text)."
        )
    for slug, name, brand in care_kits[:10]:
        tasks.append(
            f"Step 1: open /pharmacy then /pantry (or /grocery). Step 2: add "
            f"product /product/{slug} to cart. Step 3: GET /bag and confirm "
            f"the line item shows the Subscribe & Save discount of 15%."
        )
    # Multi-step HSA-receipt flow
    for slug, name, brand in care_kits[:15]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm Bundle Type: "
            f"'Hsa Care' is in the specs. Step 3: confirm the description "
            f"mentions HSA / FSA eligibility for the agent's expense report."
        )

    # ---- 4) Cross-business: Auto VIN-fit + browse + cart (110) ------------
    vin_pool = [r for r in (bundles + auto) if 'vin' in (r[1] or '').lower()
                or 'oil' in (r[1] or '').lower() or 'brake' in (r[1] or '').lower()]
    if not vin_pool:
        vin_pool = auto[:20]
    test_vins = ['1HGBH41JXMN109186', '5YJ3E1EA7LF712345', '4T1BF1FK0HU123456',
                 'WAUEFAFL1BN012345', '1FTFW1ET5DKE12345']
    for i, (slug, name, brand) in enumerate(vin_pool[:25]):
        vin = test_vins[i % len(test_vins)]
        tasks.append(
            f"Step 1: GET /amazon-auto. Step 2: POST /amazon-auto/vin-decode "
            f"with vin='{vin}'. Step 3: open /product/{slug} and confirm "
            f"the Vehicle Fitment spec is present."
        )
        tasks.append(
            f"Step 1: GET /product/{slug}. Step 2: from the specs, read "
            f"'Vehicle Fitment'. Step 3: confirm at least one feature_tag "
            f"begins with 'fits-'."
        )
    for slug, name, brand in vin_pool[:15]:
        tasks.append(
            f"Step 1: open /amazon-auto and browse the maintenance kits. "
            f"Step 2: add /product/{slug} to cart with quantity=1. Step 3: "
            f"GET /bag and confirm the item is present."
        )
    for slug, name, brand in (vin_pool[:15] or auto[:15]):
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm one of the "
            f"feature_tags is 'bundle' OR 'vin-fit' OR 'fits-sedan'. Step 3: "
            f"check that the 'Mileage Interval' spec is set."
        )
    # Garage save flow
    for i, (slug, _n, _b) in enumerate(vin_pool[:20]):
        vin = test_vins[i % len(test_vins)]
        tasks.append(
            f"Step 1: POST /amazon-auto/garage/save with vin='{vin}', "
            f"nickname='Daily'. Step 2: GET /amazon-auto/garage and confirm "
            f"the VIN is listed. Step 3: open /product/{slug} and check "
            f"that the page (or API) flags fitment match."
        )
    # Add-to-cart with VIN context
    for slug, _n, _b in auto[:15]:
        tasks.append(
            f"Step 1: POST /api/cart with product_slug='{slug}', quantity=1, "
            f"vin='1HGBH41JXMN109186'. Step 2: confirm the response shows "
            f"ok=true. Step 3: GET /bag and confirm the cart total reflects "
            f"the new line item."
        )

    # ---- 5) Cross-business: Renewed grade-verify + return + cart (110) ----
    for slug, name, brand in renewed[:25]:
        tasks.append(
            f"Step 1: GET /amazon-renewed. Step 2: open /product/{slug}. "
            f"Step 3: confirm the specs include 'Renewed Grade' and one of "
            f"'Premium','Excellent','Good','Acceptable'."
        )
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: POST /amazon-renewed/"
            f"grade-verify with slug='{slug}'. Step 3: confirm the response "
            f"includes a 'grade' field that matches the product's spec."
        )
    for slug, name, brand in renewed[:20]:
        tasks.append(
            f"Step 1: GET /product/{slug}. Step 2: locate the return-policy "
            f"summary on the page. Step 3: confirm the 90-day Amazon "
            f"Renewed Guarantee is referenced either in specs or features."
        )
    # Refurb-pack bundle flow
    refurb_pool = [r for r in bundles if 'refurb' in (r[1] or '').lower()
                   or 'renewed' in (r[1] or '').lower()]
    for slug, name, brand in refurb_pool[:15]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm Bundle Type "
            f"is 'Refurb Pack'. Step 3: confirm both 'renewed' and 'bundle' "
            f"appear in feature_tags."
        )
    # Add-to-cart from renewed
    for slug, name, brand in renewed[:15]:
        tasks.append(
            f"Step 1: open /product/{slug} (Amazon Renewed). Step 2: add "
            f"to cart with quantity=1. Step 3: GET /bag, confirm the item is "
            f"present AND that the renewed-grade tag survived into the cart."
        )

    # ---- 6) Cross-business: Household share + S&S + Auto-Reorder (90) ----
    for slug, name, brand in household[:15]:
        tasks.append(
            f"Step 1: GET /household and read the fixture roster. Step 2: "
            f"open /product/{slug}. Step 3: confirm the specs include "
            f"'Household Share: Eligible (Amazon Household)'."
        )
    sns_pool = [r for r in (bundles + mbya + pharm) if 'subscribe' in (r[1] or '').lower()
                or 'subscribe-and-save' in (r[1] or '').lower()][:30]
    if not sns_pool:
        sns_pool = (bundles + mbya)[:30]
    for slug, name, brand in sns_pool[:25]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: enroll in Subscribe & "
            f"Save: POST /api/subscribe-save/enroll with product_slug="
            f"'{slug}', interval=8. Step 3: confirm the response field "
            f"enrolled=true."
        )
        tasks.append(
            f"Step 1: GET /household. Step 2: GET /product/{slug}. Step 3: "
            f"POST /api/subscribe-save/enroll with shared=true. Confirm the "
            f"enrollment is visible to all adults in the household roster."
        )
    # Auto-reorder threshold
    for slug, _n, _b in sns_pool[:15]:
        tasks.append(
            f"Step 1: POST /api/subscribe-save/enroll with product_slug="
            f"'{slug}', interval=4, threshold=2 (auto-reorder when stock<=2). "
            f"Step 2: confirm enrolled=true AND threshold echoed back."
        )

    # ---- 7) Cross-business: Kids FreeTime + Custom monogram (90) ----------
    for slug, name, brand in freetime[:15]:
        tasks.append(
            f"Step 1: GET /kids/freetime. Step 2: open /product/{slug}. "
            f"Step 3: confirm the specs include 'FreeTime Age Band' with one "
            f"of '3–5','6–8','9–12'."
        )
    for slug, name, brand in custom[:15]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm Bundle Type or "
            f"feature_tags include 'monogram-pack'. Step 3: confirm the "
            f"specs include 'Personalization' and 'Lead Time'."
        )
    for slug, name, brand in custom[:15]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: POST /api/cart with "
            f"product_slug='{slug}', quantity=1, customization='K.W.'. "
            f"Step 3: GET /bag and confirm the customization is preserved."
        )
    for i, (slug, _n, _b) in enumerate(freetime[:15]):
        cust_slug = custom[i % max(len(custom), 1)][0] if custom else slug
        tasks.append(
            f"Step 1: GET /kids/freetime. Step 2: add /product/{slug} (kid "
            f"tablet) AND /product/{cust_slug} (custom monogram gift) to "
            f"cart. Step 3: GET /bag, confirm both line items are present."
        )
    # Parental approval flow
    for slug, _n, _b in freetime[:15]:
        tasks.append(
            f"Step 1: POST /kids/freetime/request-add with product_slug="
            f"'{slug}', kid_email='kid1@test.com'. Step 2: confirm the "
            f"response status_code='pending_approval'. Step 3: report "
            f"the parent email to whom approval was routed."
        )

    # ---- 8) Cross-business: Live + Warehouse + Outlet checkout (80) -------
    for slug, name, brand in live[:12]:
        tasks.append(
            f"Step 1: GET /live-shopping. Step 2: open /product/{slug}. "
            f"Step 3: confirm the specs include 'Amazon Live: Featured in "
            f"livestream carousel' AND is_deal is true."
        )
    for slug, name, brand in warehouse[:15]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm specs include "
            f"'Warehouse Deal: Yes (inspected, 90-day warranty)' AND the "
            f"stock value is between 1 and 12."
        )
    for slug, name, brand in outlet[:12]:
        tasks.append(
            f"Step 1: GET /outlet. Step 2: open /product/{slug}. Step 3: "
            f"confirm one of the feature_tags is 'outlet-open-box'."
        )
    # Multi-line checkout
    for i, (slug, _n, _b) in enumerate(warehouse[:12]):
        live_slug = live[i % max(len(live), 1)][0] if live else slug
        outlet_slug = outlet[i % max(len(outlet), 1)][0] if outlet else slug
        tasks.append(
            f"Step 1: add /product/{slug} (warehouse-deal), /product/"
            f"{live_slug} (live-deal), /product/{outlet_slug} (outlet) to "
            f"cart. Step 2: GET /bag, confirm three line items. Step 3: POST "
            f"/checkout/confirm and report the final order id."
        )
    # Frustration-free packaging
    ffp_pool = [r for r in warehouse if 'ffp' in (r[1] or '').lower()
                or 'frustration' in (r[1] or '').lower()]
    for slug, _n, _b in (ffp_pool[:10] or warehouse[:5]):
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm specs include "
            f"'Packaging: Frustration-Free (recyclable)'. Step 3: confirm "
            f"the feature_tags include 'frustration-free' AND 'recyclable-"
            f"packaging'."
        )

    # ---- 9) Seasonal / Holiday Gift Guide (60) ----------------------------
    for slug, name, brand in seasonal[:20]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm the specs "
            f"include a 'Season' field whose value contains '26' (2026 cycle)."
        )
    gg_pool = [r for r in seasonal if 'holiday' in (r[1] or '').lower()
               or 'gift' in (r[1] or '').lower() or 'winter' in (r[1] or '').lower()]
    for slug, _n, _b in (gg_pool[:15] or seasonal[:15]):
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm the feature_tags "
            f"include 'holiday-gift-guide'. Step 3: confirm is_featured=true "
            f"(should be promoted on the home page)."
        )
    for slug, _n, _b in seasonal[:15]:
        tasks.append(
            f"Step 1: GET /. Step 2: search for /product/{slug} on the "
            f"home page or via /s?k=. Step 3: confirm the seasonal-bundle "
            f"product is discoverable from a sub-3-step browse path."
        )

    # ---- 10) Made by Amazon private-label (50) ----------------------------
    for slug, name, brand in mbya[:30]:
        tasks.append(
            f"Step 1: open /product/{slug}. Step 2: confirm the brand is one "
            f"of 'Amazon Basics','Amazon Essentials','Amazon Aware'. Step 3: "
            f"confirm 'made-by-amazon' appears in feature_tags."
        )
    for slug, _n, _b in mbya[:10]:
        tasks.append(
            f"Step 1: GET /product/{slug}. Step 2: confirm the specs include "
            f"'Private Label: Made by Amazon'. Step 3: report the country of "
            f"origin from the specs."
        )

    # ---- 11) Catalog-floor verification (R10 head-count) (20) -------------
    tasks.append(
        "GET /api/metrics/catalog. Confirm products_total >= 55500 (R10 "
        "floor)."
    )
    tasks.append(
        "GET /metrics. Report the value of 'amazon_products_total' and "
        "confirm it is >= 55500."
    )
    tasks.append(
        "GET /readyz. Confirm status='ready' and 'products' >= 55500."
    )
    for cat, floor in [('pharmacy', 200), ('auto', 200), ('renewed', 200),
                       ('outlet', 150), ('live_shopping', 150),
                       ('kids_freetime', 150), ('household', 80),
                       ('bundles', 600), ('amazon_custom', 250),
                       ('made_by_amazon', 400), ('seasonal', 400),
                       ('warehouse_deals', 250)]:
        tasks.append(
            f"GET /c/{cat.replace('_', '-')} (follow any 301 redirect). "
            f"Confirm the category lists at least {floor} products. "
            f"Alternative: GET /api/products/{cat} and count the items array."
        )

    # ---- 12) End-to-end multi-business benchmark scenarios (50) -----------
    # These are the marquee "5+ step cross-business" tasks that exercise the
    # whole stack. Helpers take *lists of slugs* (strings), not tuples.
    def _slugs(rows):
        return [r[0] for r in rows] if rows else []

    benchmark_flows = [
        lambda c, a, r, h: (
            f"Multi-business one-stop care kit flow: Step 1: open /pharmacy "
            f"and read otc count. Step 2: open /product/{c[0]} (HSA care "
            f"kit). Step 3: enroll in Subscribe & Save (interval=4). Step 4: "
            f"add to cart. Step 5: POST /api/checkout/preview and confirm "
            f"the HSA-eligible line-item sub-total. Step 6: report sub-total."
        ),
        lambda c, a, r, h: (
            f"VIN-anchored auto maintenance flow: Step 1: POST /amazon-auto/"
            f"vin-decode with '1HGBH41JXMN109186'. Step 2: open /product/"
            f"{a[0]} (oil change pack). Step 3: confirm fitment compatibility. "
            f"Step 4: add to cart with vin. Step 5: GET /bag and report "
            f"the VIN attached to the line item."
        ),
        lambda c, a, r, h: (
            f"Renewed-grade verify + warranty flow: Step 1: GET /amazon-"
            f"renewed. Step 2: open /product/{r[0]} (refurb). Step 3: POST "
            f"/amazon-renewed/grade-verify and confirm the returned grade. "
            f"Step 4: add to cart. Step 5: confirm Renewed Guarantee in cart."
        ),
        lambda c, a, r, h: (
            f"Household-share Subscribe-Save flow: Step 1: GET /household. "
            f"Step 2: open /product/{c[1] if len(c) > 1 else c[0]} (care kit). "
            f"Step 3: enroll in Subscribe & Save shared=true. Step 4: confirm "
            f"every adult email in the roster is granted access."
        ),
        lambda c, a, r, h: (
            f"Kids+ FreeTime + Custom-monogram gift flow: Step 1: GET "
            f"/kids/freetime. Step 2: add /product/{h[0] if h else c[0]} "
            f"(kid item). Step 3: add /product/{c[0]} (monogrammed gift). "
            f"Step 4: POST /checkout/preview. Step 5: confirm parental "
            f"approval is required for the kid-tagged line."
        ),
        lambda c, a, r, h: (
            f"Live carousel + Warehouse open-box deal flow: Step 1: GET "
            f"/live-shopping. Step 2: pick a featured deal /product/{c[0]}. "
            f"Step 3: GET /outlet, pick /product/{a[0]}. Step 4: add both "
            f"to cart. Step 5: POST /checkout/confirm. Step 6: report order "
            f"id and discount applied."
        ),
        lambda c, a, r, h: (
            f"Holiday Gift Guide cross-cat flow: Step 1: GET /todays-deals. "
            f"Step 2: filter by holiday-gift-guide tag. Step 3: add /product/"
            f"{c[0]} and /product/{r[0]}. Step 4: confirm both are tagged "
            f"holiday-gift-guide. Step 5: complete checkout and report the "
            f"total."
        ),
        lambda c, a, r, h: (
            f"Made-by-Amazon back-to-school flow: Step 1: GET /. Step 2: "
            f"search 'amazon basics' via /s?k=. Step 3: add /product/{c[0]} "
            f"and /product/{a[0]} (Amazon Essentials apparel). Step 4: "
            f"confirm 'made-by-amazon' tag is present on both items in /bag."
        ),
    ]
    flow_inputs = [
        (_slugs(bundles or mbya), _slugs(auto or seasonal), _slugs(renewed or outlet), _slugs(freetime or live)),
        (_slugs(bundles or mbya), _slugs(auto), _slugs(renewed), _slugs(freetime)),
        (_slugs(bundles), _slugs(auto), _slugs(renewed), _slugs(freetime)),
        (_slugs(bundles), _slugs(auto), _slugs(renewed), _slugs(freetime)),
        (_slugs(custom or bundles), _slugs(auto), _slugs(renewed), _slugs(freetime)),
        (_slugs(live or bundles), _slugs(warehouse or outlet), _slugs(renewed), _slugs(freetime)),
        (_slugs(seasonal or bundles), _slugs(mbya or auto), _slugs(renewed), _slugs(freetime)),
        (_slugs(mbya or bundles), _slugs(mbya[10:20] if len(mbya) > 10 else mbya), _slugs(renewed), _slugs(freetime)),
    ]
    for flow_fn, inputs in zip(benchmark_flows, flow_inputs):
        c, a, r, h = inputs
        # Each flow rendered with multiple SKU rotations (5 each = 40 total).
        for shift in range(5):
            c_shift = (c[shift % max(len(c), 1):] + c[:shift % max(len(c), 1)]) if c else ['placeholder-slug']
            a_shift = (a[shift % max(len(a), 1):] + a[:shift % max(len(a), 1)]) if a else ['placeholder-slug']
            r_shift = (r[shift % max(len(r), 1):] + r[:shift % max(len(r), 1)]) if r else ['placeholder-slug']
            h_shift = (h[shift % max(len(h), 1):] + h[:shift % max(len(h), 1)]) if h else ['placeholder-slug']
            tasks.append(flow_fn(c_shift, a_shift, r_shift, h_shift))

    # ---- Wire tasks into tasks.jsonl --------------------------------------
    out_rows = []
    for i, ques in enumerate(tasks):
        out_rows.append({
            'web_name': 'Amazon',
            'id': f'Amazon--{next_n + i}',
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
