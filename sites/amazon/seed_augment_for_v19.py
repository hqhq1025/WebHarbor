"""v19 seed augmentation for amazon — adds 8 NEW persona users AND pads
existing users deeper, so scenarios can broaden user enums for diversity.

Designed per Rule 3F of the harvest-macros-scenarios skill.

Re-runnable (idempotent): keyed on deterministic order_number, user email,
addr label, etc.

Run:
  cd /home/v-haoqiwang/repos/WebHarbor/sites/amazon
  python3 seed_augment_for_v19.py
"""
import sqlite3
import shutil
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / 'instance_seed' / 'amazon_store.db'
BACKUP_PATH = Path(__file__).parent / 'instance_seed' / 'amazon_store.db.preaugment_v19_bak'

# Pre-computed bcrypt of 'TestPass123!' — same as existing seed users
TESTPASS_HASH = 'scrypt:32768:8:1$dummy$fake'  # placeholder — copy from existing demo user


# ─────────────────────────────────────────────────────────────────────────
# 8 NEW persona users (Rule 3F)
# ─────────────────────────────────────────────────────────────────────────
NEW_USERS = [
    # (email, name, is_prime, archetype)
    ('bargain_hunter@test.com', 'Bargain Hunter', True,  'bargain_hunter'),
    ('gift_buyer@test.com',     'Gift Buyer',     True,  'gift_buyer'),
    ('heavy_reviewer@test.com', 'Heavy Reviewer', True,  'heavy_reviewer'),
    ('return_heavy@test.com',   'Return Heavy',   True,  'return_heavy'),
    ('abandoned_cart@test.com', 'Abandoned Cart', False, 'abandoned_cart'),
    ('wishlist_hoarder@test.com', 'Wishlist Hoarder', True, 'wishlist_hoarder'),
    ('sns_power_user@test.com', 'SnS Power User', True,  'sns_power_user'),
    ('big_spender@test.com',    'Big Spender',    True,  'big_spender'),
]

# ─────────────────────────────────────────────────────────────────────────
# Pad existing users (Rule 3F.1)
# ─────────────────────────────────────────────────────────────────────────
# We won't shrink anything; only add to bring totals to target.
PAD_EXISTING = {
    'alice.j@test.com': {
        'orders_by_status': {'delivered': 4, 'shipped': 2, 'processing': 1, 'pending': 1, 'cancelled': 1, 'returning': 1},
        'wishlist_min': 8,
        'sns_min': 6,
        'returns_min': 3,
    },
    'bob.c@test.com': {
        # Don't touch is_prime — persona-defining
        'orders_by_status': {'delivered': 2, 'shipped': 1, 'pending': 1},
        'cart_min': 3,
        'wishlist_min': 5,
        'sns_min': 2,
    },
    'carol.d@test.com': {
        'orders_by_status': {'delivered': 2, 'shipped': 1, 'pending': 1, 'cancelled': 1},
        'wishlist_min': 6,
        'sns_min': 4,
    },
    'david.k@test.com': {
        'orders_by_status': {'delivered': 2, 'shipped': 1, 'pending': 1, 'cancelled': 1, 'returning': 1},
        'wishlist_min': 5,
        'sns_min': 4,
    },
}


def reuse_or_create_user(c, email, name, is_prime):
    """Idempotent user create — returns user_id."""
    row = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if row:
        return row['id'], False
    cur = c.cursor()
    cur.execute("""
        INSERT INTO users (email, password_hash, name, phone, address_line1,
                           city, state, zip_code, country, is_prime, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (email, TESTPASS_HASH, name, '555-0100', '100 Test St',
          'Seattle', 'WA', '98101', 'USA', int(is_prime), '2026-01-01 00:00:00.000000'))
    return cur.lastrowid, True


def get_products(c, n=20, **filters):
    """Pick deterministic in-stock products (by primary key order, not RANDOM)."""
    sql = "SELECT id, name, price, image FROM products WHERE stock > 0"
    params = []
    if 'price_lt' in filters:
        sql += " AND price < ?"; params.append(filters['price_lt'])
    if 'price_gte' in filters:
        sql += " AND price >= ?"; params.append(filters['price_gte'])
    if 'category' in filters:
        sql += " AND category_slug = ?"; params.append(filters['category'])
    sql += f" ORDER BY id LIMIT {n}"
    return c.execute(sql, params).fetchall()


def ensure_addr(c, user_id, idx=0, is_default=True):
    """Idempotent address — one default per user."""
    label = f'augment-v19-{user_id}-addr-{idx}'
    row = c.execute("SELECT id FROM saved_addresses WHERE user_id=? AND label=?",
                    (user_id, label)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO saved_addresses (user_id, label, full_name, phone,
                                     address_line1, city, state, zip_code,
                                     country, is_default, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, label, f'Test User {user_id}', '555-0100',
          f'{100 + idx} Main St', 'Seattle', 'WA', '98101', 'USA',
          int(is_default), '2026-01-01 00:00:00.000000'))
    return cur.lastrowid


def ensure_payment(c, user_id, idx=0, is_default=True):
    label = f'augment-v19-{user_id}-card-{idx}'
    last4 = f'{(idx * 1111) % 10000:04d}'
    row = c.execute("""SELECT id FROM payment_methods
                       WHERE user_id=? AND last4=? AND cardholder_name=?""",
                    (user_id, last4, label)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO payment_methods (user_id, card_type, last4, exp_month, exp_year,
                                     cardholder_name, is_default, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, 'Visa', last4, 12, 2027, label, int(is_default),
          '2026-01-01 00:00:00.000000'))
    return cur.lastrowid


def ensure_order(c, user_id, status, total, products, idx=0):
    """Idempotent order keyed on order_number."""
    order_number = f'augment-v19-{user_id}-{status}-{idx:03d}'
    row = c.execute("SELECT id FROM orders WHERE order_number=?", (order_number,)).fetchone()
    if row:
        return row['id']
    user_row = c.execute("SELECT name FROM users WHERE id=?", (user_id,)).fetchone()
    user_name = user_row['name'] if user_row else 'Test User'
    cur = c.cursor()
    subtotal = round(total - 5.99 - total * 0.08, 2)
    created = {'pending': '2026-05-25', 'processing': '2026-05-20',
               'shipped': '2026-05-10', 'delivered': '2026-04-15',
               'cancelled': '2026-04-01', 'returning': '2026-04-10'}.get(status, '2026-04-01')
    cur.execute("""
        INSERT INTO orders (user_id, order_number, status, subtotal, shipping, tax, total,
                            ship_name, ship_address, ship_city, ship_state, ship_zip,
                            payment_method, payment_last4, created_at, delivery_estimate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, order_number, status, subtotal, 5.99, round(total*0.08, 2), total,
          user_name, '100 Main St', 'Seattle', 'WA', '98101', 'Visa', '1111',
          f'{created} 12:00:00.000000', '2-3 days'))
    order_id = cur.lastrowid
    for p in products[:3]:
        cur.execute("""
            INSERT INTO order_items (order_id, product_id, product_name, product_image,
                                     quantity, price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, p['id'], p['name'], p['image'], 1, p['price']))
    return order_id


def ensure_cart_item(c, user_id, product_id, qty=1):
    row = c.execute("SELECT id FROM cart_items WHERE user_id=? AND product_id=?",
                    (user_id, product_id)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO cart_items (user_id, product_id, quantity, added_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, product_id, qty, '2026-05-25 12:00:00.000000'))
    return cur.lastrowid


def ensure_wishlist_item(c, user_id, product_id):
    row = c.execute("SELECT id FROM wishlist_items WHERE user_id=? AND product_id=?",
                    (user_id, product_id)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO wishlist_items (user_id, product_id, added_at)
        VALUES (?, ?, ?)
    """, (user_id, product_id, '2026-05-15 12:00:00.000000'))
    return cur.lastrowid


def ensure_sns_plan(c, user_id, product_id, frequency, qty=1):
    row = c.execute("""SELECT id FROM subscribe_save_plans
                       WHERE user_id=? AND product_id=? AND frequency=?""",
                    (user_id, product_id, frequency)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO subscribe_save_plans (user_id, product_id, frequency, quantity,
                                          active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, product_id, frequency, qty, 1, '2026-03-01 12:00:00.000000'))
    return cur.lastrowid


def ensure_review(c, user_id, product_id, rating, title, body):
    row = c.execute("SELECT id FROM reviews WHERE user_id=? AND product_id=?",
                    (user_id, product_id)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO reviews (user_id, product_id, rating, title, body, verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, product_id, rating, title, body, 1, '2026-04-01 12:00:00.000000'))
    return cur.lastrowid


def ensure_qa_question(c, user_id, product_id, body):
    row = c.execute("""SELECT id FROM qa_questions
                       WHERE user_id=? AND product_id=? AND body=?""",
                    (user_id, product_id, body)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO qa_questions (product_id, user_id, body, vote_score, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (product_id, user_id, body, 0, '2026-04-15 12:00:00.000000'))
    return cur.lastrowid


def ensure_return(c, user_id, order_id, amount=99.99):
    row = c.execute("SELECT id FROM returns WHERE user_id=? AND order_id=?",
                    (user_id, order_id)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO returns (order_id, user_id, status, refund_method, refund_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, user_id, 'pending', 'original_payment', amount, '2026-04-20 12:00:00.000000'))
    return cur.lastrowid


def ensure_registry(c, owner_id, event_type, title, code):
    row = c.execute("SELECT id FROM registries WHERE public_code=?", (code,)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO registries (owner_id, event_type, title, public_code, event_date,
                                description, shipping_address, is_public, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (owner_id, event_type, title, code, '2026-06-01 00:00:00.000000',
          f'Test {event_type} registry', '100 Main St, Seattle WA', 1,
          '2026-04-01 12:00:00.000000'))
    return cur.lastrowid


def ensure_registry_item(c, registry_id, product_id, qty_wanted=2, qty_purchased=0, priority='medium'):
    row = c.execute("""SELECT id FROM registry_items
                       WHERE registry_id=? AND product_id=?""",
                    (registry_id, product_id)).fetchone()
    if row:
        return row['id']
    cur = c.cursor()
    cur.execute("""
        INSERT INTO registry_items (registry_id, product_id, qty_wanted, qty_purchased, priority)
        VALUES (?, ?, ?, ?, ?)
    """, (registry_id, product_id, qty_wanted, qty_purchased, priority))
    return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────
# Per-archetype population
# ─────────────────────────────────────────────────────────────────────────
def populate_archetype(c, user_id, archetype):
    """Build the user's data shape per Rule 3F.2."""
    addr_id = ensure_addr(c, user_id, 0, True)
    pay_id  = ensure_payment(c, user_id, 0, True)

    if archetype == 'bargain_hunter':
        # 6 small-$ orders, 12 wishlist, 1 card, 1 addr
        small_products = get_products(c, n=20, price_lt=30)
        for i in range(6):
            ensure_order(c, user_id, 'delivered', small_products[i]['price'] + 10,
                         [small_products[i]], idx=i)
        for p in small_products[:12]:
            ensure_wishlist_item(c, user_id, p['id'])

    elif archetype == 'gift_buyer':
        ensure_registry(c, user_id, 'wedding', 'Spring Wedding Registry', f'GIFT{user_id:03d}WED')
        reg2_id = ensure_registry(c, user_id, 'baby', 'Baby Shower Registry', f'GIFT{user_id:03d}BAB')
        prods = get_products(c, n=10)
        for p in prods[:6]:
            ensure_registry_item(c, reg2_id, p['id'], 2, 0, 'high')
        # 1-2 normal orders too
        for i in range(2):
            ensure_order(c, user_id, 'delivered', prods[i]['price'] + 10, [prods[i]], idx=i)

    elif archetype == 'heavy_reviewer':
        prods = get_products(c, n=12)
        for i, p in enumerate(prods[:10]):
            ensure_review(c, user_id, p['id'], 4 + (i % 2),
                          f'Quick take on {p["name"][:30]}',
                          'Good build, fast shipping, recommend.')
        # 8 Q&A
        for i, p in enumerate(prods[:8]):
            ensure_qa_question(c, user_id, p['id'],
                               f'Does this work with model X? (q{i:02d})')
        # 2 orders to give context
        for i in range(2):
            ensure_order(c, user_id, 'delivered', prods[i]['price'] + 10, [prods[i]], idx=i)

    elif archetype == 'return_heavy':
        prods = get_products(c, n=10)
        # 6 orders, 4 returns started
        for i in range(6):
            oid = ensure_order(c, user_id, 'delivered' if i < 4 else 'returning',
                               prods[i]['price'] + 10, [prods[i]], idx=i)
            if i < 4:
                ensure_return(c, user_id, oid, prods[i]['price'] + 10)

    elif archetype == 'abandoned_cart':
        # 8-10 cart items, 0 orders
        prods = get_products(c, n=10)
        for p in prods[:10]:
            ensure_cart_item(c, user_id, p['id'], qty=1)

    elif archetype == 'wishlist_hoarder':
        # 15-20 wishlist, 1 order
        prods = get_products(c, n=20)
        for p in prods[:18]:
            ensure_wishlist_item(c, user_id, p['id'])
        ensure_order(c, user_id, 'delivered', prods[0]['price'] + 10, [prods[0]], idx=0)

    elif archetype == 'sns_power_user':
        prods = get_products(c, n=8)
        freqs = ['1-month', '2-month', '3-month', '1-month', '6-month',
                 '2-month', '1-month', '3-month']
        for i, p in enumerate(prods[:7]):
            ensure_sns_plan(c, user_id, p['id'], freqs[i])

    elif archetype == 'big_spender':
        # 10 cart items high $, 4 payment, 4 addr
        for i in range(1, 4):
            ensure_addr(c, user_id, i, False)
            ensure_payment(c, user_id, i, False)
        big_prods = get_products(c, n=20, price_gte=100)
        for p in big_prods[:10]:
            ensure_cart_item(c, user_id, p['id'], qty=1)


# ─────────────────────────────────────────────────────────────────────────
# Pad existing users
# ─────────────────────────────────────────────────────────────────────────
def pad_existing(c, email, targets):
    """Bring existing user up to target shape; idempotent."""
    row = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return
    user_id = row['id']
    prods = get_products(c, n=30)

    # orders_by_status
    obs = targets.get('orders_by_status') or {}
    for status, target in obs.items():
        current = c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status=?",
                            (user_id, status)).fetchone()[0]
        for i in range(current, target):
            p = prods[i % len(prods)]
            ensure_order(c, user_id, status, p['price'] + 10, [p], idx=i)

    if (target := targets.get('cart_min')):
        cur = c.execute("SELECT COUNT(*) FROM cart_items WHERE user_id=?", (user_id,)).fetchone()[0]
        for i in range(cur, target):
            ensure_cart_item(c, user_id, prods[i + 5]['id'])

    if (target := targets.get('wishlist_min')):
        cur = c.execute("SELECT COUNT(*) FROM wishlist_items WHERE user_id=?", (user_id,)).fetchone()[0]
        for i in range(cur, target):
            ensure_wishlist_item(c, user_id, prods[i + 10]['id'])

    if (target := targets.get('sns_min')):
        cur = c.execute("SELECT COUNT(*) FROM subscribe_save_plans WHERE user_id=?", (user_id,)).fetchone()[0]
        freqs = ['1-month', '2-month', '3-month', '6-month']
        for i in range(cur, target):
            ensure_sns_plan(c, user_id, prods[i + 15]['id'], freqs[i % 4])

    if (target := targets.get('returns_min')):
        cur = c.execute("SELECT COUNT(*) FROM returns WHERE user_id=?", (user_id,)).fetchone()[0]
        # need a delivered order to return
        deliv = c.execute("SELECT id FROM orders WHERE user_id=? AND status='delivered'", (user_id,)).fetchall()
        for i in range(cur, target):
            if i < len(deliv):
                ensure_return(c, user_id, deliv[i]['id'])


# ─────────────────────────────────────────────────────────────────────────
# Rule 4F — Thin-table augmentation (data-for-macro-enablement)
# Target thresholds per the harvest-macros-scenarios skill §4F:
#   reviews    ≥ 100   (was 33)
#   returns    ≥ 50    (was 19)
#   registries ≥ 30    (was 8)
#   vine_members ≥ 20  (was 6)
#   promo_codes ≥ 30   (was 10)
#   redemption_codes ≥ 30  (was 10)
# ─────────────────────────────────────────────────────────────────────────

THIN_TABLE_TARGETS = {
    'reviews': 120,
    'returns': 50,
    'registries': 30,
    'vine_members': 20,
    'promo_codes': 30,
    'redemption_codes': 30,
}


def augment_thin_tables(c):
    """Rule 4F — add rows to thin tables to enable broader scenario types."""
    print("\n=== Rule 4F: Thin-table augmentation ===")
    prods = get_products(c, n=120)

    all_uids = [r['id'] for r in c.execute("SELECT id FROM users LIMIT 25").fetchall()]

    # 1. reviews
    cur_n = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    target = THIN_TABLE_TARGETS['reviews']
    print(f"  reviews: {cur_n} → target {target}")
    seed_user_ids = [1, 2, 3, 4, 5]
    titles = ["Good value", "As described", "Works great", "Five stars",
              "Solid choice", "Recommended", "Quality build", "Fast shipping"]
    bodies = ["Arrived on time, works as expected.", "Good quality for the price.",
              "Pleased with this purchase.", "Would buy again.",
              "Exactly what I needed.", "Great features for the cost."]
    added = 0
    i = 0
    while c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] < target and i < target * 3:
        uid = seed_user_ids[i % len(seed_user_ids)]
        prod = prods[i % len(prods)]
        exists = c.execute("SELECT 1 FROM reviews WHERE user_id=? AND product_id=?",
                           (uid, prod['id'])).fetchone()
        i += 1
        if exists: continue
        c.execute("""
            INSERT INTO reviews (user_id, product_id, rating, title, body, verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (uid, prod['id'], 3 + (i % 3), titles[i % len(titles)],
              bodies[i % len(bodies)], 1, '2026-03-01 12:00:00.000000'))
        added += 1
    print(f"    + {added} reviews inserted")

    # 2. returns
    cur_n = c.execute("SELECT COUNT(*) FROM returns").fetchone()[0]
    target = THIN_TABLE_TARGETS['returns']
    print(f"  returns: {cur_n} → target {target}")
    delivered = c.execute("""
        SELECT id, user_id, total FROM orders WHERE status='delivered' LIMIT 60
    """).fetchall()
    added = 0
    for i, o in enumerate(delivered):
        if c.execute("SELECT COUNT(*) FROM returns").fetchone()[0] >= target:
            break
        exists = c.execute("SELECT 1 FROM returns WHERE order_id=?", (o['id'],)).fetchone()
        if exists: continue
        c.execute("""
            INSERT INTO returns (order_id, user_id, status, refund_method, refund_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (o['id'], o['user_id'],
              ['pending','approved','complete'][i % 3],
              'original_payment', o['total'], '2026-04-20 12:00:00.000000'))
        added += 1
    print(f"    + {added} returns inserted")

    # 3. registries
    cur_n = c.execute("SELECT COUNT(*) FROM registries").fetchone()[0]
    target = THIN_TABLE_TARGETS['registries']
    print(f"  registries: {cur_n} → target {target}")
    events = ['wedding','baby','birthday','housewarming','graduation','anniversary']
    added = 0
    for i in range(target * 2):
        if c.execute("SELECT COUNT(*) FROM registries").fetchone()[0] >= target:
            break
        uid = all_uids[i % len(all_uids)]
        event = events[i % len(events)]
        code = f'REG{i:04d}{event[:3].upper()}'
        exists = c.execute("SELECT 1 FROM registries WHERE public_code=?", (code,)).fetchone()
        if exists: continue
        c.execute("""
            INSERT INTO registries (owner_id, event_type, title, public_code, event_date,
                                    description, shipping_address, is_public, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, event, f'{event.title()} Registry #{i}', code,
              '2026-08-01 00:00:00.000000', f'Augmented {event} registry',
              '123 Main St', 1, '2026-03-01 12:00:00.000000'))
        added += 1
    print(f"    + {added} registries inserted")

    # 4. vine_members
    cur_n = c.execute("SELECT COUNT(*) FROM vine_members").fetchone()[0]
    target = THIN_TABLE_TARGETS['vine_members']
    print(f"  vine_members: {cur_n} → target {target}")
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(vine_members)").fetchall()]
        print(f"    schema cols: {cols}")
        added = 0
        for i in range(target * 2):
            if c.execute("SELECT COUNT(*) FROM vine_members").fetchone()[0] >= target:
                break
            uid = all_uids[(i + 5) % len(all_uids)]
            exists = c.execute("SELECT 1 FROM vine_members WHERE user_id=?", (uid,)).fetchone()
            if exists: continue
            try:
                c.execute("""INSERT INTO vine_members (user_id, tier, joined_at)
                             VALUES (?, ?, ?)""",
                          (uid, ['gold','silver','bronze'][i % 3], '2026-01-01 00:00:00.000000'))
                added += 1
            except sqlite3.Error as e:
                print(f"    skip vine schema mismatch: {e}")
                break
        print(f"    + {added} vine_members inserted")
    except Exception as e:
        print(f"    skip vine_members: {e}")

    # 5. promo_codes
    cur_n = c.execute("SELECT COUNT(*) FROM promo_codes").fetchone()[0]
    target = THIN_TABLE_TARGETS['promo_codes']
    print(f"  promo_codes: {cur_n} → target {target}")
    cols = [r[1] for r in c.execute("PRAGMA table_info(promo_codes)").fetchall()]
    print(f"    schema cols: {cols}")
    added = 0
    code_prefixes = ['SAVE','DEAL','BLACK','SPRING','SUMMER','HOLIDAY','EXTRA','BONUS']
    for i in range(target * 2):
        if c.execute("SELECT COUNT(*) FROM promo_codes").fetchone()[0] >= target:
            break
        code = f'{code_prefixes[i % len(code_prefixes)]}{(10 + i * 5) % 100:02d}V{i:02d}'
        exists = c.execute("SELECT 1 FROM promo_codes WHERE code=?", (code,)).fetchone()
        if exists: continue
        try:
            c.execute("""INSERT INTO promo_codes (code, discount_pct, uses, max_uses, active, expires_at)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (code, 10 + (i % 5) * 5, 0, 1000, 1, '2026-12-31 23:59:59'))
            added += 1
        except sqlite3.Error:
            try:
                c.execute("INSERT INTO promo_codes (code) VALUES (?)", (code,))
                added += 1
            except sqlite3.Error as e2:
                print(f"    schema mismatch: {e2}")
                break
    print(f"    + {added} promo_codes inserted")

    # 6. redemption_codes
    cur_n = c.execute("SELECT COUNT(*) FROM redemption_codes").fetchone()[0]
    target = THIN_TABLE_TARGETS['redemption_codes']
    print(f"  redemption_codes: {cur_n} → target {target}")
    cols = [r[1] for r in c.execute("PRAGMA table_info(redemption_codes)").fetchall()]
    print(f"    schema cols: {cols}")
    added = 0
    for i in range(target * 2):
        if c.execute("SELECT COUNT(*) FROM redemption_codes").fetchone()[0] >= target:
            break
        code = f'REDEEM{i:04d}V'
        exists = c.execute("SELECT 1 FROM redemption_codes WHERE code=?", (code,)).fetchone()
        if exists: continue
        try:
            c.execute("""INSERT INTO redemption_codes (code, value, status, expires_at)
                         VALUES (?, ?, ?, ?)""",
                      (code, 10 + (i % 10) * 5, 'available', '2026-12-31 23:59:59'))
            added += 1
        except sqlite3.Error as e:
            try:
                c.execute("INSERT INTO redemption_codes (code) VALUES (?)", (code,))
                added += 1
            except sqlite3.Error as e2:
                print(f"    schema mismatch: {e2}")
                break
    print(f"    + {added} redemption_codes inserted")

    c.commit()


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────
def main():
    if not BACKUP_PATH.exists():
        shutil.copy(DB_PATH, BACKUP_PATH)
        print(f"backed up to {BACKUP_PATH}")
    else:
        print(f"backup already exists at {BACKUP_PATH}")

    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row

    # Read TESTPASS_HASH from demo user (the seeded one)
    demo_hash = c.execute("SELECT password_hash FROM users WHERE email='demo@amazon.com'").fetchone()
    if demo_hash:
        global TESTPASS_HASH
        TESTPASS_HASH = demo_hash['password_hash']

    # Create new users
    print("\n=== Creating NEW personas ===")
    for email, name, is_prime, archetype in NEW_USERS:
        uid, is_new = reuse_or_create_user(c, email, name, is_prime)
        print(f"  {email:40s} id={uid}  archetype={archetype}  {'(NEW)' if is_new else '(reuse)'}")
        populate_archetype(c, uid, archetype)

    # Pad existing
    print("\n=== Padding existing users ===")
    for email, targets in PAD_EXISTING.items():
        print(f"  padding {email}")
        pad_existing(c, email, targets)

    # Rule 4F — Thin-table augmentation
    augment_thin_tables(c)

    c.commit()
    c.close()

    # Verify
    print("\n=== Post-augmentation per-user inventory ===")
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    all_emails = [u[0] for u in NEW_USERS] + list(PAD_EXISTING) + ['demo@amazon.com']
    for email in all_emails:
        u = c.execute("SELECT id, name FROM users WHERE email=?", (email,)).fetchone()
        if not u: continue
        uid = u['id']
        stats = []
        for tbl in ['orders', 'cart_items', 'wishlist_items', 'saved_addresses',
                    'payment_methods', 'subscribe_save_plans', 'reviews', 'qa_questions',
                    'returns']:
            n = c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE user_id=?" if tbl != 'registries' else f"SELECT COUNT(*) FROM {tbl} WHERE owner_id=?", (uid,)).fetchone()[0]
            stats.append(f'{tbl[:6]}={n}')
        # registries owner_id
        reg_n = c.execute("SELECT COUNT(*) FROM registries WHERE owner_id=?", (uid,)).fetchone()[0]
        stats.append(f'reg={reg_n}')
        print(f"  {email:30s} {' '.join(stats)}")


if __name__ == '__main__':
    main()
