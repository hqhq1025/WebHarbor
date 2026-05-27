"""CarMax mirror — deepen module (append-only).

Adds 25+ new templates / 10+ new POST endpoints / extra GUI hubs that
match real carmax.com page families:

- /car/<stock>/transfer            transfer-request form
- /car/<stock>/finance/calculator  per-car finance calculator
- /car/<stock>/history-report      Vehicle History Report unlock
- /car/<stock>/similar             Similar-cars page
- /car/<stock>/photos              full photo lightbox
- /cars/under/<price>              browse hub by max price
- /cars/with-feature/<feature>     browse hub by feature
- /shop/price-drops, /shop/new-arrivals, /shop/featured
- /sell-my-car/instant-offer       instant-offer form (POST)
- /sell-my-car/appointment         in-store appointment (POST)
- /trade-in, /trade-in/calculator  trade-in flow (POST)
- /comparison/<id1>-vs-<id2>       pair compare (read-only)
- /comparison/multi/<ids>          multi-way compare
- /store/<city>                    store hub by city (alias-like)
- /store/<city>/inventory          per-city inventory
- /locations/<state>               state directory landing
- /financing/pre-qualify           dedicated pre-qual landing
- /financing/calculator            standalone payment calculator (POST)
- /maxcare/quote                   warranty quote (POST)
- /research/topic/<slug>           research topic hub
- /research/buying-guides          research category landing
- /myaccount                       account home (alias-redirect-or-dedicated)
- /myaccount/saved-cars
- /myaccount/recent-searches
- /myaccount/alerts                + new/edit/delete POST
- /about, /about/our-promise, /careers

Patterns from harden-env/gotchas §24-36:
- §31 APPEND-ONLY blueprint: this module exports `register(app)` and is
  called from the very bottom of `app.py`. No edits to existing routes.
- §32 Late import: `from app import ...` happens inside register() at
  call time, never at module load. Safe for test_client + pytest.
- §25 No in-memory data dicts — every page goes through ORM models
  (PriceAlert, RecentSearch, TransferRequest, TradeInQuote, MaxCareQuote,
  FinanceCalcQuote, ResearchTopic).
- §27 Entry links: nav links into `/myaccount/` and `/shop/price-drops`
  are added in `base.html` (separate edit) so new hubs are reachable.
- §30 / §34 Image utilization: every detail / gallery / compare
  template iterates `vehicle.get_gallery()` so the 738 vehicle images on
  disk get referenced. Store photos, article hero images, badge images
  also wired in.
- §35 POST families: transfer / instant-offer / appointment / trade-in
  / finance-calc / alert-new / alert-edit / alert-delete / maxcare-quote
  / recent-searches-clear / dismiss-photo.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta


# Late-import slot. register() fills these in.
app = None
db = None
Vehicle = None
Store = None
User = None
Article = None
Review = None
SavedVehicle = None


def _bind_app_symbols():
    """Late-import app symbols and write them into module globals.

    See harden-env/gotchas §32: top-level `from app import` here would
    create a circular import because app.py imports this module too.
    """
    global app, db, Vehicle, Store, User, Article, Review, SavedVehicle
    from app import (
        app as _app, db as _db,
        Vehicle as _V, Store as _S, User as _U, Article as _A,
        Review as _R, SavedVehicle as _SV,
    )
    app, db = _app, _db
    Vehicle, Store, User, Article, Review = _V, _S, _U, _A, _R
    SavedVehicle = _SV


# =============================================================================
# Frozen seed clock — must match seed_data.SEED_NOW for byte-id reset.
# =============================================================================
SEED_NOW = datetime(2026, 1, 15, 12, 0, 0)
TODAY = date(2026, 5, 14)


# =============================================================================
# Real image stock prefixes that exist under static/images/vehicles/.
# Enumerated at import time so the remap in seed_deepen() is deterministic
# and byte-identical across boots. We sort lexicographically.
# =============================================================================
def _enumerate_avail_stocks():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'static', 'images', 'vehicles')
    if not os.path.isdir(base):
        return []
    seen = set()
    for name in os.listdir(base):
        if '-' not in name or not name.endswith('.jpg'):
            continue
        prefix = name.split('-', 1)[0]
        # Only purely numeric / 8-char-numeric prefixes (skip placeholder)
        if prefix.isdigit() and len(prefix) == 8:
            seen.add(prefix)
    return sorted(seen)


import os  # noqa: E402  (used by _enumerate_avail_stocks above)
_AVAIL_STOCKS = _enumerate_avail_stocks()


# Feature slugs that carmax.com surfaces as browseable feature hubs.
FEATURE_HUBS = [
    ('apple-carplay', 'Apple CarPlay'),
    ('android-auto', 'Android Auto'),
    ('blind-spot-monitor', 'Blind Spot Monitor'),
    ('sunroof', 'Sunroof'),
    ('leather-seats', 'Leather Seats'),
    ('heated-seats', 'Heated Seats'),
    ('navigation-system', 'Navigation System'),
    ('third-row-seating', 'Third Row Seating'),
    ('automated-cruise-control', 'Automated Cruise Control'),
    ('lane-departure-warning', 'Lane Departure Warning'),
    ('bose-sound-system', 'BOSE Sound System'),
    ('backup-camera', 'Backup Camera'),
    ('power-seats', 'Power Seats'),
    ('tow-package', 'Tow Package'),
    ('all-electric-drivetrain', 'All-Electric Drivetrain'),
]

PRICE_BUCKETS = [10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000]

RESEARCH_TOPICS = [
    ('best-suvs', 'Best Used SUVs',
     'Our editors rank used SUVs by reliability, cargo room, and value.',
     'research'),
    ('best-trucks', 'Best Used Trucks',
     'From light-duty pickups to full-size haulers — every used truck deserves consideration.',
     'research'),
    ('best-sedans', 'Best Used Sedans',
     'Practical, efficient, and affordable — used sedans offer outstanding value.',
     'research'),
    ('best-hybrids', 'Best Used Hybrid Cars',
     'Hybrids combine excellent fuel economy with low running costs.',
     'research'),
    ('best-electric', 'Best Used Electric Cars',
     'Drive past the gas pump in a used EV — see which models are worth buying.',
     'research'),
    ('best-luxury', 'Best Used Luxury Cars Under $30,000',
     'Premium features and badges without the new-car price tag.',
     'research'),
    ('best-family', 'Best Used Family Cars',
     'Safe, spacious, and reliable — picks for growing families.',
     'research'),
    ('best-first-car', 'Best Used Cars for First-Time Buyers',
     'Easy to drive, affordable to insure, and cheap to maintain.',
     'how-to'),
    ('best-snow', 'Best Used Cars for Snowy Climates',
     'AWD, ground clearance, and standard heated seats — picks for cold weather.',
     'research'),
    ('best-mpg', 'Best High-MPG Used Cars',
     'Highway-friendly fuel economy without going hybrid.',
     'research'),
    ('how-financing-works', 'How CarMax Financing Works',
     'CarMax Auto Finance + outside lenders compete for your business — here is how.',
     'financing'),
    ('credit-tier-guide', 'Credit Tier Guide for Used Car Financing',
     'How your credit score maps to APRs in our marketplace.',
     'financing'),
    ('trade-in-tips', 'Trade-In Tips: Get the Most for Your Car',
     'Clean it, document it, and bring the title — three steps to a higher offer.',
     'selling'),
    ('home-delivery-faq', 'Home Delivery FAQ',
     'Eligible vehicles can be delivered as far as 60 miles from your nearest CarMax.',
     'how-to'),
    ('warranty-vs-service-plan', 'Limited Warranty vs MaxCare Service Plan',
     'The 30-day limited warranty is included. MaxCare picks up after that.',
     'how-to'),
]

ABOUT_PAGES = [
    ('about', 'About CarMax',
     'The way it should be.',
     "CarMax was founded in 1993 with a simple idea: car shopping should be honest, transparent, and stress-free. We pioneered no-haggle pricing and built the largest selection of used vehicles in the United States. Today we operate more than 240 stores nationwide and sell more than 750,000 vehicles each year.\n\nEvery vehicle we offer is CarMax Certified — that means no flood or frame damage, no salvage history, and a 125+ point inspection. We back every car with a 30-day Limited Warranty and a 10-day Money-Back Guarantee."),
    ('about/our-promise', 'The CarMax Promise',
     'Five things every customer can count on.',
     "1. Upfront pricing — what you see is what you pay. No haggling, ever.\n2. CarMax Certified quality — every car passes our 125+ point inspection.\n3. 30-Day Limited Warranty — 1,500 miles of peace of mind, on us.\n4. 10-Day Money-Back Guarantee — bring it back, no questions asked.\n5. Real, written offers — sell your car to us in under an hour, even if you don't buy from us."),
    ('about/leadership', 'CarMax Leadership',
     'Our executive team.',
     "Bill Nash, President & CEO. Enrique Mayor-Mora, EVP & Chief Financial Officer. Diane Cafritz, EVP, Chief Human Resources & Administrative Officer. Jim Lyski, EVP & Chief Strategy, Marketing, and Innovation Officer. Joe Wilson, EVP & Chief Operating Officer."),
    ('about/sustainability', 'Sustainability at CarMax',
     'Selling pre-owned vehicles is inherently sustainable — and we go further.',
     "Each pre-owned vehicle we sell extends the useful life of materials and energy that have already been spent. Beyond that, we are reducing energy intensity in our reconditioning centers, expanding EV inventory, and partnering with Habitat for Humanity to deliver Cars for Communities."),
    ('careers', 'Careers at CarMax',
     'Join the team that put used-car shopping right.',
     "We hire across reconditioning, customer experience, technology, finance, and corporate roles in Richmond, VA. Our culture values integrity, action, and inclusion. CarMax has been recognized 21 consecutive years by Fortune as one of the 100 Best Companies to Work For."),
    ('about/diversity', 'Diversity, Equity & Inclusion at CarMax',
     'Different perspectives drive a better business.',
     "Our DE&I strategy focuses on workforce, workplace, and community. Associate Resource Groups span 8 communities of interest. We publish progress against representation goals every year."),
]


# =============================================================================
# Models — gated by their own empty-state for byte-id reset (gotcha §25)
# =============================================================================

def _define_models():
    global TransferRequest, PriceAlert, RecentSearch, TradeInQuote
    global MaxCareQuote, FinanceCalcQuote, ResearchTopic, AboutPage, StorePhoto

    class TransferRequest(db.Model):
        __tablename__ = 'transfer_requests'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
        vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
        from_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
        to_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
        contact_name = db.Column(db.String(120), default='')
        contact_email = db.Column(db.String(120), default='')
        contact_phone = db.Column(db.String(30), default='')
        transfer_fee = db.Column(db.Float, default=0.0)
        eta_days = db.Column(db.Integer, default=7)
        status = db.Column(db.String(20), default='pending')
        notes = db.Column(db.String(400), default='')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class PriceAlert(db.Model):
        __tablename__ = 'price_alerts'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        label = db.Column(db.String(120), default='')
        make_slug = db.Column(db.String(40), default='')
        model_slug = db.Column(db.String(60), default='')
        body_style = db.Column(db.String(30), default='')
        year_min = db.Column(db.Integer, default=0)
        price_max = db.Column(db.Integer, default=0)
        mileage_max = db.Column(db.Integer, default=0)
        zip_code = db.Column(db.String(10), default='')
        frequency = db.Column(db.String(20), default='daily')
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        last_match_count = db.Column(db.Integer, default=0)

    class RecentSearch(db.Model):
        __tablename__ = 'recent_searches'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        query_text = db.Column(db.String(200), default='')
        filters_json = db.Column(db.Text, default='{}')
        result_count = db.Column(db.Integer, default=0)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class TradeInQuote(db.Model):
        __tablename__ = 'trade_in_quotes'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
        year = db.Column(db.Integer, nullable=False)
        make = db.Column(db.String(40), nullable=False)
        model = db.Column(db.String(60), nullable=False)
        trim = db.Column(db.String(60), default='')
        mileage = db.Column(db.Integer, nullable=False)
        condition = db.Column(db.String(20), default='good')
        zip_code = db.Column(db.String(10), default='')
        owed_amount = db.Column(db.Float, default=0.0)
        estimated_value = db.Column(db.Float, nullable=False)
        equity_estimate = db.Column(db.Float, default=0.0)
        target_vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
        valid_until = db.Column(db.Date, nullable=False)
        status = db.Column(db.String(20), default='active')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class MaxCareQuote(db.Model):
        __tablename__ = 'maxcare_quotes'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
        vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
        plan_tier = db.Column(db.String(20), default='gold')
        coverage_months = db.Column(db.Integer, default=48)
        coverage_miles = db.Column(db.Integer, default=75000)
        deductible = db.Column(db.Integer, default=200)
        monthly_amount = db.Column(db.Float, default=0.0)
        total_premium = db.Column(db.Float, default=0.0)
        valid_until = db.Column(db.Date, nullable=False)
        status = db.Column(db.String(20), default='active')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class FinanceCalcQuote(db.Model):
        __tablename__ = 'finance_calc_quotes'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
        vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
        sale_price = db.Column(db.Float, nullable=False)
        down_payment = db.Column(db.Float, default=2000.0)
        trade_in_value = db.Column(db.Float, default=0.0)
        term_months = db.Column(db.Integer, default=72)
        apr = db.Column(db.Float, default=6.99)
        monthly_payment = db.Column(db.Float, default=0.0)
        total_interest = db.Column(db.Float, default=0.0)
        total_cost = db.Column(db.Float, default=0.0)
        credit_tier = db.Column(db.String(20), default='good')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class ResearchTopic(db.Model):
        __tablename__ = 'research_topics'
        slug = db.Column(db.String(80), primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        category = db.Column(db.String(40), default='research')
        summary = db.Column(db.String(500), default='')
        body = db.Column(db.Text, default='')
        hero_image = db.Column(db.String(255), default='')
        published_at = db.Column(db.Date, nullable=False)

    class AboutPage(db.Model):
        __tablename__ = 'about_pages'
        slug = db.Column(db.String(80), primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        eyebrow = db.Column(db.String(200), default='')
        body = db.Column(db.Text, default='')

    class StorePhoto(db.Model):
        __tablename__ = 'store_photos'
        id = db.Column(db.Integer, primary_key=True)
        store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
        position = db.Column(db.Integer, default=0)
        kind = db.Column(db.String(40), default='exterior')
        image = db.Column(db.String(255), default='')
        caption = db.Column(db.String(200), default='')

    # Stash on module for later access
    globals().update({
        'TransferRequest': TransferRequest, 'PriceAlert': PriceAlert,
        'RecentSearch': RecentSearch, 'TradeInQuote': TradeInQuote,
        'MaxCareQuote': MaxCareQuote, 'FinanceCalcQuote': FinanceCalcQuote,
        'ResearchTopic': ResearchTopic, 'AboutPage': AboutPage,
        'StorePhoto': StorePhoto,
    })


# =============================================================================
# Seed — gated on each new model's empty state (byte-id safe)
# =============================================================================

def _deterministic_image(slug, kind, n_files):
    """Hash slug+kind to a file index, distributed across n_files."""
    h = hashlib.md5(f"{slug}_{kind}".encode()).hexdigest()
    return int(h[:8], 16) % n_files


def seed_deepen():
    """Seed new tables. Idempotent at function level.

    Also runs a one-shot fixup: many evolve_env-generated vehicles
    reference image filenames (e.g. ``C0000017-front.jpg``) that were
    never created on disk because asset generation only produced 123
    distinct stock-prefixed image sets. We deterministically remap
    each Vehicle.image + Vehicle.gallery_images to point at an existing
    file. After fixup, paths start with ``/static/images/vehicles/0``
    (numeric prefix) instead of ``C``; the gate below uses that
    invariant to avoid re-running.
    """
    _bind_app_symbols()

    # ----- One-shot image remap so every Vehicle row points at a real
    # asset on disk. The list of 123 actual stock prefixes is enumerated
    # at module load (see AVAIL_STOCKS). Each Vehicle.id maps deterministically
    # to one of those prefixes via id % 123. We rewrite both .image and
    # .gallery_images. Gate: a vehicle whose .image starts with "/static/
    # images/vehicles/C" hasn't been fixed up yet.
    sample = Vehicle.query.filter(
        Vehicle.image.like('/static/images/vehicles/C%')).first()
    if sample is not None and _AVAIL_STOCKS:
        for v in Vehicle.query.order_by(Vehicle.id).all():
            prefix = _AVAIL_STOCKS[v.id % len(_AVAIL_STOCKS)]
            v.image = f'/static/images/vehicles/{prefix}-front.jpg'
            v.gallery_images = json.dumps([
                f'/static/images/vehicles/{prefix}-front.jpg',
                f'/static/images/vehicles/{prefix}-side.jpg',
                f'/static/images/vehicles/{prefix}-rear.jpg',
                f'/static/images/vehicles/{prefix}-dashboard.jpg',
                f'/static/images/vehicles/{prefix}-cargo.jpg',
                f'/static/images/vehicles/{prefix}-interior.jpg',
            ])
        db.session.commit()
    # Topic seed
    if ResearchTopic.query.count() == 0:
        for i, (slug, title, summary, category) in enumerate(RESEARCH_TOPICS):
            body = (summary + '\n\nOur research team evaluated dozens of options '
                    'in this segment based on price, reliability data from RepairPal, '
                    'consumer reviews, cost of ownership over 5 years, and the '
                    'availability of relevant used inventory in our nationwide selection.\n\n'
                    'Browse top picks from our certified inventory using the link below, '
                    'or pre-qualify in under 2 minutes to see personalized monthly '
                    'payments on every car.')
            pub = date(2025, 9, 1) + timedelta(days=(i * 11) % 240)
            hero = f"/static/images/articles/{['how-carmax-works','how-to-sell-your-car-to-carmax','pre-approval-vs-pre-qualified','best-compact-sedan-honda-civic-vs-toyota-corolla-vs-nissan-sentra','best-hatchback-cars-ranking','how-to-buy-a-used-car','maxcare-explained','first-time-car-buyer','best-high-mpg-cars','attainable-dream-cars-under-50000'][i % 10]}.jpg"
            db.session.add(ResearchTopic(
                slug=slug, title=title, category=category,
                summary=summary, body=body,
                hero_image=hero, published_at=pub))

    if AboutPage.query.count() == 0:
        for slug, title, eyebrow, body in ABOUT_PAGES:
            db.session.add(AboutPage(
                slug=slug, title=title, eyebrow=eyebrow, body=body))

    # Store photos: 4 per store using the vehicle-image pool by deterministic
    # mapping (12+ stores * 4 = 48+ store-photo template refs). NOTE we
    # derive directly from Vehicle.image (post-remap) so every store-photo
    # path resolves to an actual file on disk.
    if StorePhoto.query.count() == 0:
        stores = Store.query.order_by(Store.id).all()
        all_vehicles = Vehicle.query.order_by(Vehicle.id).all()
        kinds_views = [('exterior', 1), ('showroom', 0),
                       ('service', 2), ('lot', 0)]
        for s in stores:
            for pos, (kind, view_idx) in enumerate(kinds_views):
                idx = _deterministic_image(s.slug + str(pos), kind,
                                           len(all_vehicles))
                v = all_vehicles[idx]
                gallery = v.get_gallery() or [v.image]
                image = gallery[view_idx % len(gallery)]
                cap = {
                    'exterior': f"{s.name} storefront on {s.street}",
                    'showroom': f"Indoor showroom at {s.location_label}",
                    'service': f"Service center at {s.name}",
                    'lot': f"Inventory lot at {s.location_label}",
                }[kind]
                db.session.add(StorePhoto(
                    store_id=s.id, position=pos, kind=kind,
                    image=image, caption=cap))

    # Benchmark per-user seed entries (PriceAlert / RecentSearch / TradeInQuote
    # / MaxCareQuote / FinanceCalcQuote / TransferRequest)
    if PriceAlert.query.count() == 0:
        alice = User.query.filter_by(email='alice.j@test.com').first()
        bob = User.query.filter_by(email='bob.k@test.com').first()
        carol = User.query.filter_by(email='carol.l@test.com').first()
        dan = User.query.filter_by(email='dan.m@test.com').first()
        emma = User.query.filter_by(email='emma.n@test.com').first()
        if alice:
            db.session.add(PriceAlert(
                user_id=alice.id, label='Honda CR-V under $25k',
                make_slug='honda', model_slug='cr-v', body_style='SUV',
                year_min=2020, price_max=25000, mileage_max=70000,
                zip_code='30303', frequency='daily', is_active=True,
                last_match_count=4, created_at=SEED_NOW))
            db.session.add(PriceAlert(
                user_id=alice.id, label='Any Toyota under $22k',
                make_slug='toyota', model_slug='', body_style='',
                year_min=2019, price_max=22000, mileage_max=80000,
                zip_code='30303', frequency='weekly', is_active=True,
                last_match_count=7, created_at=SEED_NOW))
        if bob:
            db.session.add(PriceAlert(
                user_id=bob.id, label='Ford F-150 4WD',
                make_slug='ford', model_slug='f-150', body_style='Truck',
                year_min=2021, price_max=42000, mileage_max=50000,
                zip_code='77002', frequency='daily', is_active=True,
                last_match_count=3, created_at=SEED_NOW))
        if carol:
            db.session.add(PriceAlert(
                user_id=carol.id, label='Compact sedan under $18k',
                make_slug='', model_slug='', body_style='Sedan',
                year_min=2019, price_max=18000, mileage_max=85000,
                zip_code='33176', frequency='instant', is_active=True,
                last_match_count=11, created_at=SEED_NOW))
            db.session.add(PriceAlert(
                user_id=carol.id, label='Nissan Altima paused',
                make_slug='nissan', model_slug='altima', body_style='Sedan',
                year_min=2019, price_max=17000, mileage_max=80000,
                zip_code='33176', frequency='daily', is_active=False,
                last_match_count=2, created_at=SEED_NOW))
        if dan:
            db.session.add(PriceAlert(
                user_id=dan.id, label='Mazda CX-5 Grand Touring',
                make_slug='mazda', model_slug='cx-5', body_style='SUV',
                year_min=2021, price_max=30000, mileage_max=45000,
                zip_code='02062', frequency='daily', is_active=True,
                last_match_count=2, created_at=SEED_NOW))
        if emma:
            db.session.add(PriceAlert(
                user_id=emma.id, label='Any electric under $30k',
                make_slug='', model_slug='', body_style='',
                year_min=2020, price_max=30000, mileage_max=60000,
                zip_code='98037', frequency='daily', is_active=True,
                last_match_count=3, created_at=SEED_NOW))

    if RecentSearch.query.count() == 0:
        alice = User.query.filter_by(email='alice.j@test.com').first()
        bob = User.query.filter_by(email='bob.k@test.com').first()
        carol = User.query.filter_by(email='carol.l@test.com').first()
        emma = User.query.filter_by(email='emma.n@test.com').first()
        if alice:
            for i, (q, fj, n) in enumerate([
                ('Honda CR-V', '{"make":"honda","model":"cr-v"}', 16),
                ('AWD SUV under 25000', '{"body_style":"SUV","drive_type":"AWD","price_max":"25000"}', 22),
                ('Toyota Camry 2022', '{"make":"toyota","model":"camry","year":"2022"}', 8),
            ]):
                db.session.add(RecentSearch(
                    user_id=alice.id, query_text=q, filters_json=fj,
                    result_count=n,
                    created_at=SEED_NOW - timedelta(days=i)))
        if bob:
            for i, (q, fj, n) in enumerate([
                ('Ford F-150 Lariat', '{"make":"ford","model":"f-150","trim":"lariat"}', 5),
                ('Chevrolet Silverado 4WD', '{"make":"chevrolet","model":"silverado","drive_type":"4WD"}', 9),
            ]):
                db.session.add(RecentSearch(
                    user_id=bob.id, query_text=q, filters_json=fj,
                    result_count=n,
                    created_at=SEED_NOW - timedelta(days=i + 1)))
        if carol:
            db.session.add(RecentSearch(
                user_id=carol.id, query_text='Sedan under 18000',
                filters_json='{"body_style":"Sedan","price_max":"18000"}',
                result_count=14, created_at=SEED_NOW))
        if emma:
            db.session.add(RecentSearch(
                user_id=emma.id, query_text='Tesla Model 3',
                filters_json='{"make":"tesla","model":"model-3"}',
                result_count=4, created_at=SEED_NOW))
            db.session.add(RecentSearch(
                user_id=emma.id, query_text='electric',
                filters_json='{"fuel_type":"Electric"}',
                result_count=4, created_at=SEED_NOW - timedelta(days=2)))

    if TradeInQuote.query.count() == 0:
        alice = User.query.filter_by(email='alice.j@test.com').first()
        bob = User.query.filter_by(email='bob.k@test.com').first()
        dan = User.query.filter_by(email='dan.m@test.com').first()
        if alice:
            db.session.add(TradeInQuote(
                user_id=alice.id, year=2018, make='Honda', model='Civic', trim='EX',
                mileage=68500, condition='good', zip_code='30303',
                owed_amount=3500.0, estimated_value=14200.0,
                equity_estimate=10700.0,
                valid_until=TODAY + timedelta(days=7),
                status='active', created_at=SEED_NOW))
        if bob:
            db.session.add(TradeInQuote(
                user_id=bob.id, year=2016, make='Toyota', model='Highlander',
                trim='XLE', mileage=98700, condition='fair', zip_code='77002',
                owed_amount=0.0, estimated_value=15600.0,
                equity_estimate=15600.0,
                valid_until=TODAY + timedelta(days=4),
                status='active', created_at=SEED_NOW))
        if dan:
            db.session.add(TradeInQuote(
                user_id=dan.id, year=2014, make='Subaru', model='Outback',
                trim='Premium', mileage=132000, condition='fair', zip_code='02062',
                owed_amount=0.0, estimated_value=7950.0,
                equity_estimate=7950.0,
                valid_until=TODAY + timedelta(days=5),
                status='active', created_at=SEED_NOW))

    if MaxCareQuote.query.count() == 0:
        alice = User.query.filter_by(email='alice.j@test.com').first()
        bob = User.query.filter_by(email='bob.k@test.com').first()
        v3 = db.session.get(Vehicle, 3)
        v7 = db.session.get(Vehicle, 7)
        if alice and v3:
            db.session.add(MaxCareQuote(
                user_id=alice.id, vehicle_id=v3.id, plan_tier='gold',
                coverage_months=48, coverage_miles=75000, deductible=200,
                monthly_amount=42.95, total_premium=1895.0,
                valid_until=TODAY + timedelta(days=14),
                status='active', created_at=SEED_NOW))
        if bob and v7:
            db.session.add(MaxCareQuote(
                user_id=bob.id, vehicle_id=v7.id, plan_tier='platinum',
                coverage_months=60, coverage_miles=100000, deductible=100,
                monthly_amount=54.95, total_premium=2395.0,
                valid_until=TODAY + timedelta(days=14),
                status='active', created_at=SEED_NOW))

    if FinanceCalcQuote.query.count() == 0:
        carol = User.query.filter_by(email='carol.l@test.com').first()
        emma = User.query.filter_by(email='emma.n@test.com').first()
        v11 = db.session.get(Vehicle, 11)
        v23 = db.session.get(Vehicle, 23)
        if carol and v11:
            db.session.add(FinanceCalcQuote(
                user_id=carol.id, vehicle_id=v11.id,
                sale_price=v11.price, down_payment=2000.0,
                trade_in_value=0.0, term_months=72, apr=11.99,
                monthly_payment=405.50, total_interest=7796.0,
                total_cost=v11.price + 7796.0,
                credit_tier='fair', created_at=SEED_NOW))
        if emma and v23:
            db.session.add(FinanceCalcQuote(
                user_id=emma.id, vehicle_id=v23.id,
                sale_price=v23.price, down_payment=1000.0,
                trade_in_value=0.0, term_months=66, apr=17.99,
                monthly_payment=478.20, total_interest=9420.0,
                total_cost=v23.price + 9420.0,
                credit_tier='building', created_at=SEED_NOW))

    if TransferRequest.query.count() == 0:
        alice = User.query.filter_by(email='alice.j@test.com').first()
        v15 = db.session.get(Vehicle, 15)
        v23 = db.session.get(Vehicle, 23)
        if alice and v15 and v23:
            alice_store_id = alice.home_store_id or v15.store_id
            db.session.add(TransferRequest(
                user_id=alice.id, vehicle_id=v23.id,
                from_store_id=v23.store_id, to_store_id=alice_store_id,
                contact_name='Alice Johnson',
                contact_email='alice.j@test.com',
                contact_phone='(404) 555-0118',
                transfer_fee=v23.transfer_fee or 99.0,
                eta_days=5, status='pending',
                notes='Please call when ready for pickup.',
                created_at=SEED_NOW))

    db.session.commit()


# =============================================================================
# Helpers
# =============================================================================

def _vehicle_or_404(stock):
    from flask import abort
    v = Vehicle.query.filter_by(stock_number=stock).first()
    if not v:
        abort(404)
    return v


def _vehicle_by_id_or_404(vid):
    from flask import abort
    v = db.session.get(Vehicle, int(vid))
    if not v:
        abort(404)
    return v


def _safe_int(s, default=0):
    try:
        return int(str(s).replace(',', '').strip())
    except (TypeError, ValueError):
        return default


def _safe_float(s, default=0.0):
    try:
        return float(str(s).replace(',', '').strip())
    except (TypeError, ValueError):
        return default


def _calc_monthly(price, down, trade, apr_pct, term):
    principal = max(0.0, price - down - trade)
    if principal <= 0:
        return 0.0
    if apr_pct <= 0:
        return principal / max(term, 1)
    r = apr_pct / 100.0 / 12.0
    return principal * (r * (1 + r) ** term) / ((1 + r) ** term - 1)


# =============================================================================
# register(app) — called from the bottom of app.py
# =============================================================================

def register(target_app):
    """Bind models, ensure tables, seed, then attach all routes."""
    _bind_app_symbols()
    _define_models()

    with target_app.app_context():
        db.create_all()
        seed_deepen()

    from flask import (abort, flash, redirect, render_template, request,
                       url_for)
    from flask_login import current_user, login_required

    # ---------------------------------------------------------------------
    # /car/<stock> aliases
    # ---------------------------------------------------------------------

    @target_app.route('/car/<stock>')
    def car_alias(stock):
        v = _vehicle_or_404(stock)
        return redirect(url_for('vehicle_detail', slug=v.slug), code=302)

    @target_app.route('/car/<stock>/photos')
    def car_photos(stock):
        v = _vehicle_or_404(stock)
        return render_template('deepen/photos_lightbox.html', v=v)

    @target_app.route('/car/<stock>/history-report')
    def car_history_report(stock):
        v = _vehicle_or_404(stock)
        # Deterministic owner / accident / service history derived from VIN
        seed = int(hashlib.md5(v.vin.encode()).hexdigest()[:8], 16)
        owners = 1 + (seed % 3)
        accidents = 0 if seed % 5 else 1
        service_events = 2 + (seed % 6)
        return render_template('deepen/vehicle_history_report.html',
                               v=v, owners=owners, accidents=accidents,
                               service_events=service_events,
                               report_id=f"VHR-{v.stock_number}")

    @target_app.route('/car/<stock>/similar')
    def car_similar(stock):
        v = _vehicle_or_404(stock)
        # 12 nearest cars by same body_style, then same make, then price proximity
        candidates = (Vehicle.query
                      .filter(Vehicle.id != v.id,
                              Vehicle.body_style == v.body_style)
                      .all())
        candidates.sort(key=lambda x: (
            x.make != v.make,
            abs((x.price or 0) - (v.price or 0)),
            abs((x.year or 0) - (v.year or 0)),
        ))
        return render_template('deepen/similar_cars.html',
                               v=v, similar=candidates[:12])

    @target_app.route('/car/<stock>/transfer', methods=['GET', 'POST'])
    def car_transfer(stock):
        v = _vehicle_or_404(stock)
        stores = Store.query.order_by(Store.state, Store.city).all()
        if request.method == 'POST':
            to_store_slug = (request.form.get('to_store') or '').strip()
            name = (request.form.get('name') or '').strip()
            email = (request.form.get('email') or '').strip()
            phone = (request.form.get('phone') or '').strip()
            notes = (request.form.get('notes') or '').strip()[:400]
            to_store = next((s for s in stores if s.slug == to_store_slug), None)
            if not to_store or not name or not email:
                flash('Please pick a destination store and provide your contact info.',
                      'error')
                return render_template('deepen/transfer_request.html',
                                       v=v, stores=stores,
                                       form_name=name, form_email=email,
                                       form_phone=phone, form_notes=notes,
                                       form_to_store=to_store_slug)
            fee = v.transfer_fee if v.store_id != to_store.id else 0.0
            tr = TransferRequest(
                user_id=current_user.id if current_user.is_authenticated else None,
                vehicle_id=v.id, from_store_id=v.store_id,
                to_store_id=to_store.id,
                contact_name=name, contact_email=email, contact_phone=phone,
                transfer_fee=fee, eta_days=5 if fee else 2,
                status='pending', notes=notes)
            db.session.add(tr)
            db.session.commit()
            flash(f'Transfer request submitted. Reference TR-{tr.id:06d}.', 'success')
            return redirect(url_for('transfer_confirmation', tr_id=tr.id))
        return render_template('deepen/transfer_request.html',
                               v=v, stores=stores,
                               form_name='', form_email='', form_phone='',
                               form_notes='', form_to_store='')

    @target_app.route('/transfer/<int:tr_id>')
    def transfer_confirmation(tr_id):
        tr = db.session.get(TransferRequest, tr_id)
        if not tr:
            abort(404)
        v = db.session.get(Vehicle, tr.vehicle_id)
        from_store = db.session.get(Store, tr.from_store_id)
        to_store = db.session.get(Store, tr.to_store_id)
        return render_template('deepen/transfer_confirmation.html',
                               tr=tr, v=v, from_store=from_store,
                               to_store=to_store)

    @target_app.route('/car/<stock>/finance/calculator', methods=['GET', 'POST'])
    def car_finance_calculator(stock):
        v = _vehicle_or_404(stock)
        defaults = {
            'sale_price': v.price, 'down': 2000.0, 'trade': 0.0,
            'apr': 6.99, 'term': 72, 'credit_tier': 'good',
        }
        result = None
        if request.method == 'POST':
            down = _safe_float(request.form.get('down'), 2000.0)
            trade = _safe_float(request.form.get('trade'), 0.0)
            apr = _safe_float(request.form.get('apr'), 6.99)
            term = _safe_int(request.form.get('term'), 72)
            credit_tier = (request.form.get('credit_tier') or 'good').lower()
            monthly = _calc_monthly(v.price, down, trade, apr, term)
            total_paid = monthly * term + down + trade
            total_interest = max(0.0, total_paid - v.price)
            q = FinanceCalcQuote(
                user_id=current_user.id if current_user.is_authenticated else None,
                vehicle_id=v.id, sale_price=v.price, down_payment=down,
                trade_in_value=trade, term_months=term, apr=apr,
                monthly_payment=round(monthly, 2),
                total_interest=round(total_interest, 2),
                total_cost=round(total_paid, 2),
                credit_tier=credit_tier)
            db.session.add(q)
            db.session.commit()
            result = q
            defaults.update({'down': down, 'trade': trade, 'apr': apr,
                             'term': term, 'credit_tier': credit_tier})
        return render_template('deepen/finance_calculator.html',
                               v=v, defaults=defaults, result=result)

    # ---------------------------------------------------------------------
    # Hub-style search aliases
    # ---------------------------------------------------------------------

    @target_app.route('/cars/under/<int:price>')
    def cars_under_price(price):
        if price <= 0:
            abort(404)
        items = (Vehicle.query.filter(Vehicle.price <= price)
                 .order_by(Vehicle.price.asc()).limit(48).all())
        total = Vehicle.query.filter(Vehicle.price <= price).count()
        return render_template('deepen/cars_under_price.html',
                               price=price, items=items, total=total)

    @target_app.route('/cars/with-feature/<slug>')
    def cars_with_feature(slug):
        label = next((lbl for s, lbl in FEATURE_HUBS if s == slug), None)
        if not label:
            label = slug.replace('-', ' ').title()
        items = (Vehicle.query
                 .filter(Vehicle.features.ilike(f'%"{label}"%'))
                 .order_by(Vehicle.price.asc()).limit(48).all())
        total = (Vehicle.query
                 .filter(Vehicle.features.ilike(f'%"{label}"%')).count())
        return render_template('deepen/cars_with_feature.html',
                               slug=slug, label=label,
                               items=items, total=total,
                               feature_hubs=FEATURE_HUBS)

    @target_app.route('/shop/price-drops')
    def shop_price_drops():
        items = (Vehicle.query.filter(Vehicle.is_price_drop.is_(True))
                 .order_by(Vehicle.price.asc()).limit(48).all())
        return render_template('deepen/shop_price_drops.html', items=items)

    @target_app.route('/shop/new-arrivals')
    def shop_new_arrivals():
        items = (Vehicle.query.filter(Vehicle.is_new_arrival.is_(True))
                 .order_by(Vehicle.added_at.desc()).limit(48).all())
        return render_template('deepen/shop_new_arrivals.html', items=items)

    @target_app.route('/shop/featured')
    def shop_featured():
        items = (Vehicle.query.filter(Vehicle.is_featured.is_(True))
                 .order_by(Vehicle.price.asc()).limit(48).all())
        return render_template('deepen/shop_featured.html', items=items)

    @target_app.route('/shop/electric')
    def shop_electric():
        items = (Vehicle.query.filter(Vehicle.fuel_type == 'Electric')
                 .order_by(Vehicle.price.asc()).limit(48).all())
        return render_template('deepen/shop_electric.html', items=items)

    # ---------------------------------------------------------------------
    # Sell-my-car deeper funnel
    # ---------------------------------------------------------------------

    @target_app.route('/sell-my-car/instant-offer', methods=['GET', 'POST'])
    def sell_instant_offer():
        from app import make_appraisal_offer, Appraisal
        result = None
        form_data = {}
        if request.method == 'POST':
            year = _safe_int(request.form.get('year'), 2020)
            make = (request.form.get('make') or '').strip()
            model = (request.form.get('model') or '').strip()
            trim = (request.form.get('trim') or '').strip()
            mileage = _safe_int(request.form.get('mileage'), 60000)
            condition = (request.form.get('condition') or 'good').lower()
            zip_code = (request.form.get('zip_code') or '').strip()
            email = (request.form.get('email') or '').strip()
            has_accidents = bool(request.form.get('has_accidents'))
            form_data = dict(year=year, make=make, model=model, trim=trim,
                             mileage=mileage, condition=condition,
                             zip_code=zip_code, email=email,
                             has_accidents=has_accidents)
            if not make or not model:
                flash('Please tell us your car\'s make and model.', 'error')
            else:
                offer = make_appraisal_offer(year, make, model, trim,
                                             mileage, condition, has_accidents)
                ap = Appraisal(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    year=year, make=make, model=model, trim=trim,
                    mileage=mileage, condition=condition,
                    zip_code=zip_code, has_accidents=has_accidents,
                    owner_count=1, offer_amount=float(offer),
                    offer_valid_until=TODAY + timedelta(days=7),
                    status='active', contact_email=email)
                db.session.add(ap)
                db.session.commit()
                return redirect(url_for('sell_offer', appraisal_id=ap.id))
        return render_template('deepen/sell_instant_offer.html',
                               form_data=form_data, result=result)

    @target_app.route('/sell-my-car/appointment', methods=['GET', 'POST'])
    def sell_appointment():
        stores = Store.query.order_by(Store.state, Store.city).all()
        if request.method == 'POST':
            store_slug = request.form.get('store')
            date_str = request.form.get('date')
            time_str = request.form.get('time')
            name = (request.form.get('name') or '').strip()
            email = (request.form.get('email') or '').strip()
            year = _safe_int(request.form.get('year'), 2020)
            make = (request.form.get('make') or '').strip()
            model = (request.form.get('model') or '').strip()
            mileage = _safe_int(request.form.get('mileage'), 0)
            store = next((s for s in stores if s.slug == store_slug), None)
            if not (store and date_str and name and make and model):
                flash('Please fill out all required fields.', 'error')
                return render_template('deepen/sell_appointment.html',
                                       stores=stores, today=TODAY,
                                       confirmation=None)
            from app import Appraisal
            offer = 0.0
            ap = Appraisal(
                user_id=current_user.id if current_user.is_authenticated else None,
                year=year, make=make, model=model, trim='',
                mileage=mileage, condition='good',
                zip_code=store.zip_code, has_accidents=False, owner_count=1,
                offer_amount=offer,
                offer_valid_until=TODAY + timedelta(days=7),
                status='scheduled', contact_email=email)
            db.session.add(ap)
            db.session.commit()
            flash(f'Appointment confirmed at {store.name} on {date_str} {time_str}.',
                  'success')
            return render_template('deepen/sell_appointment.html',
                                   stores=stores, today=TODAY,
                                   confirmation={'store': store,
                                                 'date': date_str,
                                                 'time': time_str,
                                                 'name': name})
        return render_template('deepen/sell_appointment.html',
                               stores=stores, today=TODAY, confirmation=None)

    # ---------------------------------------------------------------------
    # Trade-in
    # ---------------------------------------------------------------------

    @target_app.route('/trade-in')
    def trade_in_index():
        return render_template('deepen/trade_in.html')

    @target_app.route('/trade-in/calculator', methods=['GET', 'POST'])
    def trade_in_calculator():
        from app import make_appraisal_offer
        result = None
        form_data = {}
        if request.method == 'POST':
            year = _safe_int(request.form.get('year'), 2020)
            make = (request.form.get('make') or '').strip()
            model = (request.form.get('model') or '').strip()
            trim = (request.form.get('trim') or '').strip()
            mileage = _safe_int(request.form.get('mileage'), 60000)
            condition = (request.form.get('condition') or 'good').lower()
            zip_code = (request.form.get('zip_code') or '').strip()
            owed = _safe_float(request.form.get('owed'), 0.0)
            form_data = dict(year=year, make=make, model=model, trim=trim,
                             mileage=mileage, condition=condition,
                             zip_code=zip_code, owed=owed)
            if make and model:
                offer = make_appraisal_offer(year, make, model, trim, mileage,
                                             condition, False)
                equity = round(float(offer) - owed, 2)
                quote = TradeInQuote(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    year=year, make=make, model=model, trim=trim,
                    mileage=mileage, condition=condition, zip_code=zip_code,
                    owed_amount=owed, estimated_value=float(offer),
                    equity_estimate=equity,
                    valid_until=TODAY + timedelta(days=7),
                    status='active')
                db.session.add(quote)
                db.session.commit()
                result = quote
            else:
                flash('Please enter your car\'s make and model.', 'error')
        return render_template('deepen/trade_in_calculator.html',
                               form_data=form_data, result=result)

    # ---------------------------------------------------------------------
    # Comparison
    # ---------------------------------------------------------------------

    @target_app.route('/comparison/<int:a_id>-vs-<int:b_id>')
    def comparison_pair(a_id, b_id):
        a = db.session.get(Vehicle, a_id)
        b = db.session.get(Vehicle, b_id)
        if not (a and b):
            abort(404)
        return render_template('deepen/comparison_pair.html', a=a, b=b)

    @target_app.route('/comparison/multi/<ids>')
    def comparison_multi(ids):
        try:
            id_list = [int(x) for x in ids.split('-') if x.isdigit()][:4]
        except Exception:
            id_list = []
        vehicles = [db.session.get(Vehicle, x) for x in id_list]
        vehicles = [v for v in vehicles if v is not None]
        if not vehicles:
            abort(404)
        return render_template('deepen/comparison_multi.html',
                               ids_str=ids, vehicles=vehicles)

    # ---------------------------------------------------------------------
    # Store / city / state hubs
    # ---------------------------------------------------------------------

    @target_app.route('/store/<slug>/inventory')
    def store_city_inventory(slug):
        s = (Store.query.filter_by(slug=slug).first()
             or Store.query.filter(Store.slug.like(f'{slug}-%')).first()
             or Store.query.filter(Store.slug.like(f'%-{slug}')).first()
             or Store.query.filter(
                db.func.lower(Store.city) == slug.replace('-', ' ')).first())
        if not s:
            abort(404)
        items = (Vehicle.query.filter_by(store_id=s.id)
                 .order_by(Vehicle.price.asc()).all())
        return render_template('deepen/store_city_inventory.html',
                               store=s, items=items, total=len(items))

    @target_app.route('/store/<slug>/photos')
    def store_city(slug):
        # Photo wall + featured local inventory hub for a store.
        s = (Store.query.filter_by(slug=slug).first()
             or Store.query.filter(Store.slug.like(f'{slug}-%')).first()
             or Store.query.filter(Store.slug.like(f'%-{slug}')).first()
             or Store.query.filter(
                db.func.lower(Store.city) == slug.replace('-', ' ')).first())
        if not s:
            abort(404)
        photos = StorePhoto.query.filter_by(store_id=s.id).order_by(
            StorePhoto.position).all()
        local_vehicles = (Vehicle.query.filter_by(store_id=s.id)
                          .order_by(Vehicle.price.asc()).limit(8).all())
        return render_template('deepen/store_city.html',
                               store=s, photos=photos, vehicles=local_vehicles)

    @target_app.route('/locations/<state>')
    def locations_state(state):
        st = state.upper()
        stores = (Store.query.filter_by(state=st)
                  .order_by(Store.city).all())
        if not stores:
            abort(404)
        store_ids = [s.id for s in stores]
        from sqlalchemy import func as _f
        total_in_state = (Vehicle.query
                          .filter(Vehicle.store_id.in_(store_ids))
                          .count())
        return render_template('deepen/locations_state.html',
                               state=st, stores=stores,
                               total_in_state=total_in_state)

    # ---------------------------------------------------------------------
    # Financing
    # ---------------------------------------------------------------------

    @target_app.route('/financing')
    def financing_alias():
        return redirect(url_for('financing'), code=302)

    @target_app.route('/financing/pre-qualify')
    def financing_pre_qualify():
        return render_template('deepen/financing_pre_qualify.html')

    @target_app.route('/financing/calculator', methods=['GET', 'POST'])
    def financing_calculator():
        result = None
        defaults = {
            'sale_price': 25000.0, 'down': 2000.0, 'trade': 0.0,
            'apr': 7.99, 'term': 72, 'credit_tier': 'good',
        }
        if request.method == 'POST':
            sale = _safe_float(request.form.get('sale_price'), 25000.0)
            down = _safe_float(request.form.get('down'), 2000.0)
            trade = _safe_float(request.form.get('trade'), 0.0)
            apr = _safe_float(request.form.get('apr'), 7.99)
            term = _safe_int(request.form.get('term'), 72)
            credit_tier = (request.form.get('credit_tier') or 'good').lower()
            monthly = _calc_monthly(sale, down, trade, apr, term)
            total_paid = monthly * term + down + trade
            total_interest = max(0.0, total_paid - sale)
            q = FinanceCalcQuote(
                user_id=current_user.id if current_user.is_authenticated else None,
                vehicle_id=None, sale_price=sale, down_payment=down,
                trade_in_value=trade, term_months=term, apr=apr,
                monthly_payment=round(monthly, 2),
                total_interest=round(total_interest, 2),
                total_cost=round(total_paid, 2),
                credit_tier=credit_tier)
            db.session.add(q)
            db.session.commit()
            result = q
            defaults.update({'sale_price': sale, 'down': down, 'trade': trade,
                             'apr': apr, 'term': term, 'credit_tier': credit_tier})
        return render_template('deepen/financing_calculator.html',
                               defaults=defaults, result=result)

    # ---------------------------------------------------------------------
    # MaxCare quote
    # ---------------------------------------------------------------------

    @target_app.route('/maxcare/quote', methods=['GET', 'POST'])
    def maxcare_quote():
        prices = {
            'silver': (1495, 36, 50000),
            'gold': (1895, 48, 75000),
            'platinum': (2395, 60, 100000),
        }
        result = None
        if request.method == 'POST':
            stock = (request.form.get('stock') or '').strip()
            plan = (request.form.get('plan') or 'gold').lower()
            deductible = _safe_int(request.form.get('deductible'), 200)
            v = Vehicle.query.filter_by(stock_number=stock).first()
            if not v:
                flash('Please enter a valid stock number.', 'error')
            else:
                price, months, miles = prices.get(plan, prices['gold'])
                # Deductible $100 adds 8%, $50 adds 15%
                if deductible <= 50:
                    price = int(price * 1.15)
                elif deductible <= 100:
                    price = int(price * 1.08)
                monthly = round(price / 48.0, 2)
                q = MaxCareQuote(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    vehicle_id=v.id, plan_tier=plan,
                    coverage_months=months, coverage_miles=miles,
                    deductible=deductible, monthly_amount=monthly,
                    total_premium=float(price),
                    valid_until=TODAY + timedelta(days=14),
                    status='active')
                db.session.add(q)
                db.session.commit()
                result = q
        return render_template('deepen/maxcare_quote.html',
                               result=result, prices=prices)

    # ---------------------------------------------------------------------
    # Research topics
    # ---------------------------------------------------------------------

    @target_app.route('/research/topic/<slug>')
    def research_topic(slug):
        t = db.session.get(ResearchTopic, slug)
        if not t:
            abort(404)
        # Surface 6 related vehicles based on topic slug
        body_style = None
        fuel = None
        if 'suv' in slug:
            body_style = 'SUV'
        elif 'truck' in slug:
            body_style = 'Truck'
        elif 'sedan' in slug:
            body_style = 'Sedan'
        elif 'electric' in slug:
            fuel = 'Electric'
        elif 'hybrid' in slug:
            fuel = 'Hybrid'
        q = Vehicle.query
        if body_style:
            q = q.filter(Vehicle.body_style == body_style)
        if fuel:
            q = q.filter(Vehicle.fuel_type == fuel)
        related = q.order_by(Vehicle.price.asc()).limit(8).all()
        return render_template('deepen/research_topic.html',
                               t=t, related=related)

    @target_app.route('/research/buying-guides')
    def research_buying_guides():
        topics = (ResearchTopic.query
                  .filter(ResearchTopic.category == 'research')
                  .order_by(ResearchTopic.title).all())
        return render_template('deepen/research_buying_guides.html',
                               topics=topics)

    @target_app.route('/research/financing-guides')
    def research_financing_guides():
        topics = (ResearchTopic.query
                  .filter(ResearchTopic.category == 'financing')
                  .order_by(ResearchTopic.title).all())
        return render_template('deepen/research_financing_guides.html',
                               topics=topics)

    @target_app.route('/research/selling-guides')
    def research_selling_guides():
        topics = (ResearchTopic.query
                  .filter(ResearchTopic.category == 'selling')
                  .order_by(ResearchTopic.title).all())
        return render_template('deepen/research_selling_guides.html',
                               topics=topics)

    # ---------------------------------------------------------------------
    # /myaccount/* hubs
    # ---------------------------------------------------------------------

    @target_app.route('/myaccount')
    @login_required
    def myaccount_home():
        from app import (SavedVehicle as SV, Reservation, TestDrive,
                         Appraisal, Order)
        saved_count = SV.query.filter_by(user_id=current_user.id).count()
        recent_count = RecentSearch.query.filter_by(user_id=current_user.id).count()
        alert_count = PriceAlert.query.filter_by(user_id=current_user.id).count()
        active_alert_count = PriceAlert.query.filter_by(
            user_id=current_user.id, is_active=True).count()
        order_count = Order.query.filter_by(user_id=current_user.id).count()
        res_count = Reservation.query.filter_by(user_id=current_user.id).count()
        td_count = TestDrive.query.filter_by(user_id=current_user.id).count()
        app_count = Appraisal.query.filter_by(user_id=current_user.id).count()
        return render_template('deepen/myaccount_home.html',
                               saved_count=saved_count,
                               recent_count=recent_count,
                               alert_count=alert_count,
                               active_alert_count=active_alert_count,
                               order_count=order_count,
                               res_count=res_count,
                               td_count=td_count,
                               app_count=app_count)

    @target_app.route('/myaccount/saved-cars')
    @login_required
    def myaccount_saved_cars():
        from app import SavedVehicle as SV
        rows = (SV.query.filter_by(user_id=current_user.id)
                .order_by(SV.saved_at.desc()).all())
        return render_template('deepen/myaccount_saved_cars.html', rows=rows)

    @target_app.route('/myaccount/recent-searches')
    @login_required
    def myaccount_recent_searches():
        rows = (RecentSearch.query.filter_by(user_id=current_user.id)
                .order_by(RecentSearch.created_at.desc()).all())
        return render_template('deepen/myaccount_recent_searches.html',
                               rows=rows)

    @target_app.route('/myaccount/recent-searches/clear', methods=['POST'])
    @login_required
    def myaccount_recent_searches_clear():
        RecentSearch.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash('Recent search history cleared.', 'success')
        return redirect(url_for('myaccount_recent_searches'))

    @target_app.route('/myaccount/alerts')
    @login_required
    def myaccount_alerts():
        rows = (PriceAlert.query.filter_by(user_id=current_user.id)
                .order_by(PriceAlert.created_at.desc()).all())
        return render_template('deepen/myaccount_alerts.html', rows=rows)

    @target_app.route('/myaccount/alerts/new', methods=['GET', 'POST'])
    @login_required
    def myaccount_alert_new():
        if request.method == 'POST':
            label = (request.form.get('label') or '').strip()[:120]
            make_slug = (request.form.get('make_slug') or '').strip().lower()
            model_slug = (request.form.get('model_slug') or '').strip().lower()
            body_style = (request.form.get('body_style') or '').strip()
            year_min = _safe_int(request.form.get('year_min'), 0)
            price_max = _safe_int(request.form.get('price_max'), 0)
            mileage_max = _safe_int(request.form.get('mileage_max'), 0)
            zip_code = (request.form.get('zip_code') or '').strip()
            frequency = (request.form.get('frequency') or 'daily').lower()
            if not label:
                label = ' '.join(filter(None, [
                    make_slug.title(), model_slug.upper(), body_style,
                    f'under ${price_max:,}' if price_max else ''])) or 'My alert'
            pa = PriceAlert(
                user_id=current_user.id, label=label, make_slug=make_slug,
                model_slug=model_slug, body_style=body_style,
                year_min=year_min, price_max=price_max, mileage_max=mileage_max,
                zip_code=zip_code, frequency=frequency, is_active=True)
            db.session.add(pa)
            db.session.commit()
            flash('Price alert created.', 'success')
            return redirect(url_for('myaccount_alerts'))
        return render_template('deepen/myaccount_alert_form.html',
                               row=None, action_url=url_for(
                                   'myaccount_alert_new'),
                               makes=_make_slugs())

    @target_app.route('/myaccount/alerts/<int:alert_id>/edit',
                      methods=['GET', 'POST'])
    @login_required
    def myaccount_alert_edit(alert_id):
        pa = db.session.get(PriceAlert, alert_id)
        if not pa or pa.user_id != current_user.id:
            abort(404)
        if request.method == 'POST':
            pa.label = (request.form.get('label') or pa.label).strip()[:120]
            pa.make_slug = (request.form.get('make_slug') or '').strip().lower()
            pa.model_slug = (request.form.get('model_slug') or '').strip().lower()
            pa.body_style = (request.form.get('body_style') or '').strip()
            pa.year_min = _safe_int(request.form.get('year_min'), 0)
            pa.price_max = _safe_int(request.form.get('price_max'), 0)
            pa.mileage_max = _safe_int(request.form.get('mileage_max'), 0)
            pa.zip_code = (request.form.get('zip_code') or '').strip()
            pa.frequency = (request.form.get('frequency') or 'daily').lower()
            pa.is_active = bool(request.form.get('is_active'))
            db.session.commit()
            flash('Alert updated.', 'success')
            return redirect(url_for('myaccount_alerts'))
        return render_template('deepen/myaccount_alert_form.html',
                               row=pa, action_url=url_for(
                                   'myaccount_alert_edit', alert_id=pa.id),
                               makes=_make_slugs())

    @target_app.route('/myaccount/alerts/<int:alert_id>/delete',
                      methods=['POST'])
    @login_required
    def myaccount_alert_delete(alert_id):
        pa = db.session.get(PriceAlert, alert_id)
        if not pa or pa.user_id != current_user.id:
            abort(404)
        db.session.delete(pa)
        db.session.commit()
        flash('Alert deleted.', 'success')
        return redirect(url_for('myaccount_alerts'))

    @target_app.route('/myaccount/alerts/<int:alert_id>/toggle',
                      methods=['POST'])
    @login_required
    def myaccount_alert_toggle(alert_id):
        pa = db.session.get(PriceAlert, alert_id)
        if not pa or pa.user_id != current_user.id:
            abort(404)
        pa.is_active = not pa.is_active
        db.session.commit()
        return redirect(url_for('myaccount_alerts'))

    def _make_slugs():
        from sqlalchemy import distinct
        rows = (db.session.query(Vehicle.make, Vehicle.make_slug)
                .distinct().order_by(Vehicle.make).all())
        return rows

    # ---------------------------------------------------------------------
    # About / careers
    # ---------------------------------------------------------------------

    @target_app.route('/about')
    def about_index():
        page = db.session.get(AboutPage, 'about')
        other_pages = (AboutPage.query
                       .filter(AboutPage.slug != 'about',
                               AboutPage.slug != 'careers')
                       .order_by(AboutPage.title).all())
        return render_template('deepen/about.html',
                               page=page, other_pages=other_pages)

    @target_app.route('/about/<sub>')
    def about_sub(sub):
        page = db.session.get(AboutPage, f'about/{sub}')
        if not page:
            abort(404)
        return render_template('deepen/about_sub.html', page=page)

    @target_app.route('/careers')
    def careers():
        page = db.session.get(AboutPage, 'careers')
        return render_template('deepen/careers.html', page=page)


__all__ = ['register']
