# Amazon site polish — plan

## Targets
- wishlist_items 0 → 30+
- returns 0 → 10+ (with return_items)
- cart_items 3 → 15+
- products 407 → 700+
- Keep byte-identical reset (idempotent gates, fixed reference date)

## Approach
Create `sites/amazon/seed_extras.py`:
- `seed_extra_products(db, Product)` — adds ~310 synthetic products across 8 categories. Idempotent gate: `if Product.query.count() >= 700: return`. Deterministic random.Random(99). Image pool from existing `static/images/` dirs.
- `seed_extra_orders(db, User, Order, OrderItem, Product, SavedAddress, PaymentMethod)` — gives review users (jessica.m, rahul.p, etc.) saved addresses + payment + 1-2 delivered orders each so we can return them. Idempotent gate on `SavedAddress.query.filter_by(user_id=jessica_id).first()`.
- `seed_extra_carts(db, User, Product, CartItem)` — adds cart items for bob, carol, david, + 4 review users. Idempotent: `if CartItem.query.count() >= 15: return`.
- `seed_wishlists(db, User, Product, WishlistItem)` — 35 entries across alice/bob/carol/david/demo + 12 review users. Idempotent: `if WishlistItem.query.count() > 0: return`.
- `seed_returns(db, Order, OrderItem, Return, ReturnItem)` — 12 returns from delivered orders. Idempotent: `if Return.query.count() > 0: return`.

Edit `app.py` `__main__` block: import & call `from seed_extras import run_extras; run_extras(...)` after seed_benchmark_users.

## 404 audit
Compared all url_for endpoints in templates against routes — all match (37 endpoints, all resolve). No hardcoded /paths in templates other than `/s` action and url_for-derived. **No 404 fixes needed.**

## Verification
1. Build seed via docker `python:3.12-slim-bookworm` + pip + `python -c "from app import app, db; ..."`
2. Copy resulting `instance/amazon_store.db` → `instance_seed/amazon_store.db`
3. md5sum twice (run-twice idempotency check)
4. py_compile sites/amazon/*.py
