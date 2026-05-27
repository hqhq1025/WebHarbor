#!/usr/bin/env python3
"""Generate R8 tasks — Cmd+K palette + keyboard shortcuts + observability
(/healthz /metrics) + telemetry (/api/events /api/error-report) +
two-step + WebAuthn passkey + developer OAuth + business-prime tier +
abandoned-cart-email + multi-step chains.

Appends ~750 deterministically generated tasks to tasks.jsonl, starting
from the next free Amazon--N id. Output structure matches existing
tasks (same keys: web_name, id, ques, web, upstream_url).
"""
import json
import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'instance_seed', 'amazon_store.db')
TASKS_PATH = os.path.join(BASE_DIR, '..', 'tasks.jsonl')
WEB_LOCAL = 'http://localhost:40001/'
WEB_UPSTREAM = 'https://www.amazon.com/'


def load_slugs(con, category=None, limit=60, where=None):
    sql = "SELECT slug, name, brand FROM products"
    args = []
    if category:
        sql += " WHERE category_slug=?"
        args.append(category)
    if where:
        sql += (' AND ' if 'WHERE' in sql else ' WHERE ') + where
    sql += " ORDER BY id LIMIT ?"
    args.append(limit)
    return con.execute(sql, args).fetchall()


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
    fashion = load_slugs(con, 'fashion', limit=40)
    beauty = load_slugs(con, 'beauty', limit=40)
    grocery = load_slugs(con, 'grocery', limit=20)
    electronics = load_slugs(con, 'electronics', limit=20)
    books = load_slugs(con, 'books', limit=20)
    all_pool = fashion + beauty + electronics + books + grocery

    # ---- 1) keyboard-shortcut (80 tasks) --------------------------------
    chord_targets = [
        ('h', '/',               'home'),
        ('o', '/account/orders', 'your orders'),
        ('w', '/wishlist',       'wishlist'),
        ('c', '/bag',            'cart'),
        ('d', '/todays-deals',   "today's deals"),
        ('a', '/account',        'account'),
        ('p', '/prime',          'Prime'),
    ]
    for k, path, label in chord_targets:
        tasks.append(
            f"From any page, press the vim-style chord 'g {k}' (g then {k}). "
            f"Confirm the browser navigates to {label} ({path})."
        )
        tasks.append(
            f"Open /help/keyboard-shortcuts (JSON) and confirm the chord "
            f"'g {k}' is listed as the shortcut to {label}."
        )
    for slug, name, _b in fashion[:10]:
        tasks.append(
            f"Open /product/{slug}, then press '/' (forward slash). Confirm "
            f"the top-nav search input gains focus (its id is nav-search-input)."
        )
    for slug, name, _b in beauty[:10]:
        tasks.append(
            f"Open /product/{slug}. Press Cmd+K (Mac) or Ctrl+K (other). "
            f"The command palette overlay should appear and the input "
            f"#cmdk-input should be focused."
        )
    for slug, _n, _b in electronics[:8]:
        tasks.append(
            f"Open /product/{slug}. Press '?' to open the command palette "
            f"in help mode and confirm the suggestion list is non-empty."
        )
    tasks.append(
        "Open /help/keyboard-shortcuts and report the chord_window_ms "
        "value (the chord-timeout in milliseconds)."
    )
    tasks.append(
        "From /, press 'g' followed by 'd' within 1 second. Confirm the "
        "page navigates to /todays-deals."
    )
    tasks.append(
        "Open /help/keyboard-shortcuts and count how many bindings are "
        "exposed under 'bindings'."
    )
    tasks.append(
        "Press Esc while the command palette is open. Confirm #cmdk-overlay "
        "becomes hidden again."
    )

    # ---- 2) command-palette / search (80) -------------------------------
    cmdk_queries = ['ole', 'wat', 'fenty', 'lulu', 'cera', 'echo', 'fire',
                    'kindle', 'audible', 'olaplex', 'k18', 'nike', 'adidas',
                    'tom ford', 'la mer', 'glossier', 'rare', 'dunk',
                    'macbook', 'iphone']
    for q in cmdk_queries:
        tasks.append(
            f"GET /api/command-palette?q={q.replace(' ', '%20')}. Report the "
            f"first item's url and label."
        )
        tasks.append(
            f"Open the Cmd+K command palette (Cmd/Ctrl+K), type '{q}', and "
            f"report the first non-static suggestion URL."
        )
    palette_jumps = [
        ('deals', '/todays-deals'), ('orders', '/account/orders'),
        ('wishlist', '/wishlist'), ('cart', '/bag'),
        ('grocery', '/c/grocery'), ('audible', '/c/audible'),
        ('kindle', '/c/kindle'), ('beauty', '/c/beauty'),
        ('prime', '/prime'),    ('account', '/account'),
        ('addresses', '/account/addresses'), ('payment', '/account/payment'),
        ('metrics', '/metrics'), ('healthz', '/healthz'),
        ('twostep', '/signin/twostep'), ('developer', '/developer/oauth'),
        ('business', '/business-prime/tier'),
        ('accessibility', '/.well-known/accessibility'),
    ]
    for label, url in palette_jumps:
        tasks.append(
            f"Open the Cmd+K command palette and search for '{label}'. "
            f"Pick the result whose URL is {url} and press Enter. Confirm "
            f"the page navigates there."
        )
    for q in cmdk_queries[:10]:
        tasks.append(
            f"GET /api/command-palette?q={q}. For the first item, confirm "
            f"the 'url' field starts with '/product/'."
        )
    tasks.append(
        "GET /api/command-palette?q=a (single char). Confirm 'items' is an "
        "empty list (palette only fires on >= 2-char queries)."
    )
    tasks.append(
        "GET /api/command-palette with no q parameter. Confirm it 200s and "
        "items is an empty list."
    )

    # ---- 3) two-step + WebAuthn (80) ------------------------------------
    methods = ['sms', 'authenticator', 'email', 'backup-code']
    for m in methods * 3:
        tasks.append(
            f"POST /signin/twostep with method={m} and code=424242. "
            f"Confirm the response ok=true and next='/account'."
        )
        tasks.append(
            f"POST /signin/twostep with method={m} and code=000000. "
            f"Confirm the response ok=false and reason='invalid_code'."
        )
    tasks.append(
        "POST /signin/twostep with method='telegram' and code=424242. "
        "Confirm the response 4xx with reason='unsupported_method'."
    )
    tasks.append(
        "GET /signin/twostep. Confirm the response lists 'webauthn' under "
        "'methods' and points 'webauthn_url' at /signin/twostep/webauthn."
    )
    tasks.append(
        "GET /signin/twostep/webauthn. Report the rp_name field."
    )
    tasks.append(
        "GET /signin/twostep/webauthn?action=challenge. Confirm the response "
        "contains a 'challenge' field whose value is base64url-encoded."
    )
    tasks.append(
        "GET /signin/twostep/webauthn?action=challenge twice and confirm the "
        "challenge value is byte-identical on both calls (deterministic)."
    )
    tasks.append(
        "POST /signin/twostep/webauthn?action=verify with credential_id="
        "'fixture-passkey' and signature=base64('test-passkey-fixture'). "
        "Confirm ok=true and next='/account'."
    )
    tasks.append(
        "POST /signin/twostep/webauthn?action=verify with signature='wrong'. "
        "Confirm ok=false with reason='invalid_signature'."
    )
    tasks.append(
        "POST /signin/twostep/webauthn?action=register with nickname='Work "
        "MacBook'. Confirm the credential_id starts with 'cred_'."
    )
    tasks.append(
        "POST /signin/twostep/webauthn?action=register with nickname='iPhone "
        "15 Pro'. Confirm the credential_id is exactly 17 characters "
        "(cred_ + 12 hex)."
    )
    tasks.append(
        "POST /signin/twostep/webauthn?action=delete. Confirm the response "
        "is a 4xx with reason='unknown_action'."
    )
    tasks.append(
        "GET /signin/twostep and confirm rp_id matches the host of the "
        "request (e.g. localhost when the mirror is on port 40001)."
    )
    for method in methods:
        tasks.append(
            f"POST /signin/twostep with method={method} but no code. "
            f"Confirm the response is 4xx with reason='invalid_code'."
        )

    # ---- 4) developer OAuth flow (110) ----------------------------------
    apps = [
        ('My Inventory Sync',   'https://example.com/cb',  ['orders:read']),
        ('Cart Analytics',      'https://acme.com/oauth',  ['cart:read', 'profile']),
        ('Wishlist Mirror',     'https://wishly.io/cb',    ['wishlist:read', 'wishlist:write']),
        ('Review Importer',     'https://reviews.dev/cb',  ['reviews:write']),
        ('Order Exporter',      'https://export.io/cb',    ['orders:read', 'orders:write']),
        ('Loyalty Bridge',      'https://loyalty.app/cb',  ['profile', 'orders:read']),
    ]
    for app_name, cb, scopes in apps:
        scope_str = ' '.join(scopes)
        tasks.append(
            f"POST /developer/oauth/register with app_name='{app_name}', "
            f"redirect_uri='{cb}', and scopes={scopes}. Report the "
            f"client_id from the response."
        )
        tasks.append(
            f"Register an OAuth app named '{app_name}' at "
            f"/developer/oauth/register. Take its client_id and call "
            f"POST /developer/oauth/authorize?client_id=<cid>&scope="
            f"{scope_str.replace(' ', '%20')}. Report the issued code."
        )
        tasks.append(
            f"Walk the full OAuth authorization_code flow for '{app_name}': "
            f"register, authorize (get code), then POST "
            f"/developer/oauth/token with grant_type=authorization_code, "
            f"client_id=<cid>, code=<code>. Report the access_token prefix."
        )
        tasks.append(
            f"After running the OAuth flow for '{app_name}', call "
            f"/developer/oauth/userinfo with Authorization: Bearer "
            f"<access_token>. Report the 'sub' field."
        )
        tasks.append(
            f"Register '{app_name}' twice with the same arguments. Confirm "
            f"both runs return the same client_id (deterministic)."
        )
    tasks.append(
        "GET /developer/oauth. List the values under 'scopes' alphabetically "
        "and report the third one."
    )
    tasks.append(
        "GET /developer/oauth. List the values under 'flows' and report the "
        "count."
    )
    tasks.append(
        "POST /developer/oauth/token with grant_type=client_credentials and "
        "client_id=amzn-app-test. Report the token_type and expires_in."
    )
    tasks.append(
        "POST /developer/oauth/token with grant_type=password and "
        "client_id=amzn-app-test. Confirm error='unsupported_grant_type' "
        "and 'password' is NOT in the supported list."
    )
    tasks.append(
        "POST /developer/oauth/token with grant_type=refresh_token, "
        "client_id=amzn-app-test, refresh_token=refresh_abc123. Report "
        "the new access_token prefix."
    )
    tasks.append(
        "POST /developer/oauth/token with grant_type=authorization_code but "
        "no code. Confirm the response is 4xx with reason mentioning 'code'."
    )
    tasks.append(
        "GET /developer/oauth/userinfo with no Authorization header. Confirm "
        "the response is 401 with error='invalid_token'."
    )
    tasks.append(
        "POST /developer/oauth/register with app_name only (no redirect_uri). "
        "Confirm ok=false and the errors list mentions 'redirect_uri'."
    )
    tasks.append(
        "POST /developer/oauth/authorize with state='xyz789', client_id="
        "'amzn-app-test', redirect_uri='https://example.com/cb'. Confirm the "
        "returned redirect URL contains 'state=xyz789'."
    )

    # ---- 5) telemetry — /api/events + /api/error-report (80) -----------
    event_types = [
        ('page_view', 'home.viewed', {'url': '/'}),
        ('click', 'nav.todays_deals', {'url': '/todays-deals'}),
        ('add_to_cart', 'product.add', {'slug': fashion[0][0] if fashion else 'x', 'qty': 1}),
        ('search_submit', 'search.run', {'q': 'olaplex'}),
        ('purchase', 'order.created', {'order_id': 1, 'total': 99.99}),
        ('login', 'user.signin', {'method': 'password'}),
        ('wishlist_add', 'wishlist.added', {'slug': beauty[0][0] if beauty else 'x'}),
        ('video_play', 'aplus.video', {'product_slug': electronics[0][0] if electronics else 'x'}),
    ]
    for et, name, payload in event_types * 4:
        body = json.dumps({'type': et, 'name': name, 'payload': payload})
        tasks.append(
            f"POST /api/events application/json with body {body}. "
            f"Confirm accepted=1 and event_id starts with 'evt_'."
        )
    for et, name, payload in event_types[:4]:
        body = json.dumps({'type': et, 'name': name, 'payload': payload})
        tasks.append(
            f"POST /api/events twice with the same body {body}. Confirm "
            f"both calls return the same event_id (deterministic)."
        )
    tasks.append(
        "GET /api/events with no params. Confirm 'supported_types' includes "
        "'purchase' and 'page_view'."
    )
    tasks.append(
        "POST /api/events with body {} (empty object). Confirm the response "
        "is 4xx with accepted=0 and an error mentioning 'type'."
    )
    tasks.append(
        "POST /api/events with type='page_view' but no name. Confirm "
        "accepted=0 and the response is 4xx."
    )
    err_msgs = [
        ("TypeError: Cannot read property 'x' of undefined", '/product/echo-dot-5th-gen-smart-speaker-with-alexa'),
        ("ReferenceError: addToCart is not defined", '/cart'),
        ("NetworkError: failed to fetch /api/cart/add", '/bag'),
        ("SyntaxError: Unexpected token <", '/checkout'),
        ("Image failed to load: 404", '/c/electronics'),
    ]
    for msg, url in err_msgs * 3:
        body = json.dumps({'message': msg, 'url': url, 'severity': 'error'})
        tasks.append(
            f"POST /api/error-report with body {body}. Confirm accepted=1 "
            f"and report_id starts with 'err_'."
        )
    tasks.append(
        "POST /api/error-report with body {\"url\":\"/cart\"} (no message). "
        "Confirm accepted=0 with an error mentioning 'message'."
    )
    tasks.append(
        "GET /api/error-report and report the list of expected 'fields' "
        "from the response."
    )

    # ---- 6) abandoned-cart-email (60) -----------------------------------
    for step in [1, 2, 3]:
        for total in [49.99, 129.50, 299.00, 18.49, 425.75]:
            body = json.dumps({'step': step, 'email': 'demo@amazon.com',
                              'cart_total': total})
            tasks.append(
                f"POST /api/abandoned-cart-email with body {body}. Report "
                f"the cart_total_after_discount."
            )
    tasks.append(
        "GET /api/abandoned-cart-email and report the discount_code for "
        "step 2 (should be 'BACK5')."
    )
    tasks.append(
        "GET /api/abandoned-cart-email and report the discount_code for "
        "step 3 (should be 'SAVE10')."
    )
    tasks.append(
        "GET /api/abandoned-cart-email. Confirm the schedule has exactly "
        "3 steps and the offsets are 1h / 24h / 72h."
    )
    tasks.append(
        "POST /api/abandoned-cart-email with step=2, email='alice.j@test.com', "
        "cart_total=200. Confirm cart_total_after_discount=190.0."
    )
    tasks.append(
        "POST /api/abandoned-cart-email with step=3, email='bob.c@test.com', "
        "cart_total=100. Confirm the response subject contains '10% off' "
        "and discount_code='SAVE10'."
    )
    tasks.append(
        "POST /api/abandoned-cart-email with step=99 (out of range). Confirm "
        "the response normalizes to step=3 and uses code SAVE10."
    )
    for total in [55.00, 250.00, 999.99]:
        body = json.dumps({'step': 1, 'email': 'carol.d@test.com',
                          'cart_total': total})
        tasks.append(
            f"POST /api/abandoned-cart-email with body {body}. Confirm "
            f"discount_pct=0 (step 1 is a soft reminder, no discount)."
        )

    # ---- 7) business-prime-tier (70) ------------------------------------
    tier_qs = [
        ('Essentials', 179.00, 3),
        ('Small',      499.00, 10),
        ('Medium',     1299.00, 100),
        ('Enterprise', 10099.00, -1),
    ]
    for name, price, seats in tier_qs:
        tasks.append(
            f"GET /business-prime/tier. Report the annual_price for the "
            f"'{name}' tier (expected: ${price})."
        )
        tasks.append(
            f"GET /business-prime/tier. Confirm the '{name}' tier has "
            f"seats={seats}."
        )
        tasks.append(
            f"GET /business-prime. Report the 'best_for' string of the "
            f"'{name}' tier."
        )
    tasks.append(
        "GET /business-prime/tier. Confirm 'Tax-Exempt Purchasing Program' "
        "first appears at the 'Medium' tier (not in Essentials or Small)."
    )
    tasks.append(
        "GET /business-prime/tier and report the count of SKUs tagged "
        "'business-prime-eligible' under the 'eligible_skus' field."
    )
    tasks.append(
        "GET /business-prime/tier. Confirm 'Punch-out / ERP integration' "
        "appears only under the 'Enterprise' tier."
    )
    tasks.append(
        "Visit /search?k=business-prime-eligible. Confirm there are "
        "results and the listing renders with the catalog grid layout."
    )
    tasks.append(
        "GET /business-prime/tier. Confirm the 'eligible_tag' value is "
        "exactly 'business-prime-eligible'."
    )
    for name, _p, _s in tier_qs:
        tasks.append(
            f"GET /business-prime/tier. List all 'features' for the "
            f"'{name}' tier and report the count."
        )

    # ---- 8) /healthz + /metrics + /readyz (60) --------------------------
    tasks.append(
        "GET /healthz. Confirm status='ok' and release='R8'."
    )
    tasks.append(
        "GET /healthz twice in a row and confirm the response body is "
        "byte-identical between the two calls."
    )
    tasks.append(
        "GET /readyz. Confirm status='ready' and 'products' is a positive "
        "integer >= 39500."
    )
    tasks.append(
        "GET /healthz. Report the 'version' field (should match R8 release: "
        "8.0.0)."
    )
    tasks.append(
        "GET /metrics. Confirm the response Content-Type starts with "
        "'text/plain; version=0.0.4'."
    )
    tasks.append(
        "GET /metrics. Report the value of the 'amazon_products_total' "
        "gauge."
    )
    tasks.append(
        "GET /metrics. Report the value of 'amazon_orders_total' gauge."
    )
    tasks.append(
        "GET /metrics. Report the value of 'amazon_products_out_of_stock'."
    )
    tasks.append(
        "GET /metrics. Confirm there is a HELP line for "
        "'amazon_products_low_stock'."
    )
    tasks.append(
        "GET /metrics. Confirm the response ends with a newline and contains "
        "'build_release=\"R8\"' in the trailer comment."
    )
    tasks.append(
        "GET /metrics. Confirm the gauge value for amazon_categories_total "
        "is at least 11 (Electronics, Computers, Home, Fashion, Books, "
        "Beauty, Sports, Toys, Grocery, Audible, Kindle)."
    )
    # Hit metrics across various flow contexts
    for slug, _n, _b in all_pool[:30]:
        tasks.append(
            f"Open /product/{slug}, then GET /metrics. Confirm the "
            f"products_total gauge is unchanged (no side effects)."
        )
    tasks.append(
        "GET /healthz, /readyz, /metrics. Confirm all three return 200."
    )
    tasks.append(
        "GET /metrics. Find the gauge with the largest numeric value and "
        "report its name."
    )

    # ---- 9) multi-step chains (150) ------------------------------------
    multi_pool = fashion[:20] + beauty[:20] + electronics[:10]
    multi_variants = [
        lambda slug, name, brand: (
            f"Step 1: GET /healthz. Step 2: open the Cmd+K palette and "
            f"search for '{(brand or name).split()[0]}'. Step 3: open the "
            f"first product result. Step 4: GET /metrics and report the new "
            f"value of amazon_products_total (should be unchanged)."
        ),
        lambda slug, name, brand: (
            f"Step 1: POST /signin/twostep with method=sms and code=424242. "
            f"Step 2: GET /signin/twostep and confirm mfa_enrolled=true. "
            f"Step 3: GET /developer/oauth and report the list of scopes."
        ),
        lambda slug, name, brand: (
            f"Step 1: POST /developer/oauth/register with app_name='Test "
            f"Bot {slug[:8]}' and redirect_uri='https://t.io/cb'. Step 2: "
            f"Use the returned client_id to call /developer/oauth/authorize. "
            f"Step 3: POST /developer/oauth/token with grant_type="
            f"authorization_code and the code from step 2."
        ),
        lambda slug, name, brand: (
            f"Step 1: POST /api/abandoned-cart-email step=1 cart_total=120. "
            f"Step 2: POST step=2 with same cart. Step 3: POST step=3 with "
            f"same cart. Report the three discount_pct values in order."
        ),
        lambda slug, name, brand: (
            f"Step 1: open /product/{slug}. Step 2: POST /api/events with "
            f"type=page_view, name=product.viewed, payload="
            f"{{slug: '{slug}'}}. Step 3: POST /api/events with type="
            f"add_to_cart, name=product.add, payload={{slug:'{slug}'}}. "
            f"Step 4: confirm both event_ids are non-empty and differ."
        ),
        lambda slug, name, brand: (
            f"Step 1: open the command palette, search for 'business prime', "
            f"and open /business-prime/tier. Step 2: GET /metrics and report "
            f"the products_total gauge. Step 3: visit /search?k="
            f"business-prime-eligible and confirm results render."
        ),
        lambda slug, name, brand: (
            f"Step 1: GET /signin/twostep/webauthn?action=challenge. Step 2: "
            f"POST action=verify with the fixture signature. Step 3: GET "
            f"/developer/oauth/userinfo with Authorization: Bearer fake. "
            f"Step 4: report the 'sub' field."
        ),
        lambda slug, name, brand: (
            f"Step 1: POST /api/error-report with message='Image failed to "
            f"load' and url='/product/{slug}'. Step 2: open /product/{slug} "
            f"and confirm the page still renders. Step 3: POST another "
            f"error-report with the same body and confirm report_id is "
            f"identical (deterministic)."
        ),
        lambda slug, name, brand: (
            f"Step 1: open /-/fr-FR/product/{slug}. Step 2: open the Cmd+K "
            f"palette and search for 'grocery'. Step 3: navigate to "
            f"/c/grocery. Step 4: GET /metrics and read the gauge value "
            f"for amazon_products_total."
        ),
        lambda slug, name, brand: (
            f"Step 1: GET /business-prime/tier. Step 2: filter the catalog "
            f"by feature_tag=business-prime-eligible at /search?k=business-"
            f"prime-eligible. Step 3: open the first result and confirm its "
            f"feature_tags include 'business-prime-eligible'."
        ),
        lambda slug, name, brand: (
            f"Step 1: open /developer/oauth/register and submit a new app "
            f"named '{(brand or 'Mirror')} Bot'. Step 2: visit "
            f"/help/keyboard-shortcuts and look up the chord for going home. "
            f"Step 3: trigger the chord 'g h' to return to /."
        ),
        lambda slug, name, brand: (
            f"Step 1: POST /api/events type=search_submit name=search.run "
            f"payload={{q:'{(brand or name).split()[0]}'}}. Step 2: actually "
            f"run that search at /s?k={(brand or name).split()[0]}. Step 3: "
            f"compare the event_id of step 1 to a repeated POST."
        ),
        lambda slug, name, brand: (
            f"Step 1: GET /healthz, then GET /metrics. Step 2: open the "
            f"command palette and type 'health'. Step 3: confirm "
            f"'Health (/healthz)' shows up in the suggestion list."
        ),
        lambda slug, name, brand: (
            f"Step 1: GET /signin/twostep. Step 2: open "
            f"/signin/twostep/webauthn and request a challenge. Step 3: POST "
            f"action=register with nickname='Backup Key'. Step 4: confirm "
            f"the credential_id begins with 'cred_'."
        ),
        lambda slug, name, brand: (
            f"Step 1: open /product/{slug}. Step 2: POST /api/abandoned-cart-"
            f"email step=2 cart_total=80 for demo@amazon.com. Step 3: report "
            f"the discount_code (BACK5) and the cart_total_after_discount "
            f"(should be 76.0)."
        ),
    ]
    for i, (slug, name, brand) in enumerate(multi_pool):
        variant = multi_variants[i % len(multi_variants)]
        tasks.append(variant(slug, name, brand))
    # Pad multi-step bucket with brand-specific variations.
    for i, (slug, name, brand) in enumerate(multi_pool):
        variant = multi_variants[(i + 3) % len(multi_variants)]
        tasks.append(variant(slug, name, brand))
    for i, (slug, name, brand) in enumerate(multi_pool[:30]):
        variant = multi_variants[(i + 7) % len(multi_variants)]
        tasks.append(variant(slug, name, brand))

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
