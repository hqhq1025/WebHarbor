#!/usr/bin/env python3
"""Amazon deepen seed — populate R3..R10 tables deterministically.

Adds:
  * R3  Subscribe & Save plans + auto-delivery schedule
  * R4  Registries (wedding/baby/birthday) + collaborators + items
  * R5  Amazon Fresh / Whole Foods storefront markers on grocery SKUs
  * R6  Product Q&A questions + answers + votes
  * R7  Kindle ebook catalog + Prime Video titles + redemption codes
  * R8  Seller profiles + brand storefronts (md5-derived seller_id)
  * R9  Vine reviewer roster + Vine items + Early-reviewer items + promo codes
  * R10 Webhook event log (synthetic, for /api/v1 callbacks)

Every numeric/boolean/string is derived from a deterministic seed
(`md5(slug)` or row_index) so rebuilds stay byte-identical.

Idempotent — each seeder early-returns when the target row count is already
at or above its floor.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta

REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)


def _md5_int(s, mod):
    return int(hashlib.md5(s.encode('utf-8')).hexdigest(), 16) % mod


def _md5_pick(s, seq):
    return seq[_md5_int(s, len(seq))]


# Pinned bcrypt('TestPass123!') for byte-identical reset (see harden-env/gotchas.md).
PINNED_TESTPASS_HASH = '$2b$12$PpubQvLvUkIksb10lxqIduzS2wfRkZ.ZAobDEtGEF7N9qelOp5ktK'


# ===========================================================================
# R3 — Subscribe & Save plans + auto-delivery schedule
# ===========================================================================

SNS_FREQUENCIES = ['1-month', '2-month', '3-month', '6-month']
SNS_TIER_THRESHOLDS = [(5, 15), (3, 10), (1, 5)]  # (item_count_min, percent_off)


def _tier_for_count(count):
    """Subscribe & Save tier discount: 5+ items 15% off, 3-4 items 10%, 1-2 items 5%."""
    for floor, pct in SNS_TIER_THRESHOLDS:
        if count >= floor:
            return pct
    return 0


def seed_r3_subscribe_save(db, User, Product, SubscribeSavePlan, AutoDeliverySchedule):
    if SubscribeSavePlan.query.count() >= 12:
        return
    sns_products = (Product.query
                    .filter(Product.feature_tags.ilike('%subscribe-and-save%'))
                    .order_by(Product.review_count.desc())
                    .limit(60).all())
    users = User.query.order_by(User.id).all()
    if not sns_products or not users:
        return
    plan_seeds = [
        ('alice.j@test.com', 0,  '1-month'),
        ('alice.j@test.com', 1,  '2-month'),
        ('alice.j@test.com', 2,  '1-month'),
        ('alice.j@test.com', 3,  '3-month'),
        ('alice.j@test.com', 4,  '1-month'),  # 5 → 15% tier
        ('bob.c@test.com',   5,  '6-month'),
        ('bob.c@test.com',   6,  '3-month'),
        ('carol.d@test.com', 7,  '2-month'),
        ('carol.d@test.com', 8,  '1-month'),
        ('carol.d@test.com', 9,  '2-month'),
        ('david.k@test.com', 10, '1-month'),
        ('david.k@test.com', 11, '3-month'),
        ('david.k@test.com', 12, '1-month'),
    ]
    by_email = {u.email: u for u in users}
    for email, prod_idx, freq in plan_seeds:
        u = by_email.get(email)
        if not u or prod_idx >= len(sns_products):
            continue
        prod = sns_products[prod_idx]
        plan = SubscribeSavePlan(
            user_id=u.id,
            product_id=prod.id,
            frequency=freq,
            quantity=1 + _md5_int(prod.slug, 3),
            active=True,
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(prod.slug, 60)),
        )
        db.session.add(plan)
        db.session.flush()
        # 6 scheduled deliveries
        for k in range(6):
            months = {'1-month': 1, '2-month': 2, '3-month': 3, '6-month': 6}[freq]
            scheduled = REFERENCE_DATE + timedelta(days=months * 30 * k)
            db.session.add(AutoDeliverySchedule(
                plan_id=plan.id,
                scheduled_date=scheduled,
                status='upcoming' if k > 0 else 'next',
            ))
    db.session.commit()


# ===========================================================================
# R4 — Registries (wedding/baby/birthday) + collaborators + items
# ===========================================================================

REGISTRY_SEEDS = [
    ('alice.j@test.com', 'wedding',  'Alice & Jordan Wedding Registry', 'WED-AJ-2026', '2026-09-12'),
    ('bob.c@test.com',   'baby',     "Baby Chen on the Way",           'BABY-BC-2026', '2026-08-04'),
    ('carol.d@test.com', 'birthday', 'Mia turns 5 — Princess Party',   'BIRTH-MD-2026','2026-06-21'),
    ('carol.d@test.com', 'wedding',  'Carol & Daniel — Vow Renewal',   'WED-CD-2026', '2026-10-18'),
    ('david.k@test.com', 'baby',     "David & Priya's Baby Registry",  'BABY-DK-2026','2026-11-29'),
    ('david.k@test.com', 'birthday', 'Arjun turns 8 — Robotics Theme', 'BIRTH-AK-2026','2026-07-30'),
]


def seed_r4_registries(db, User, Product, Registry, RegistryItem, RegistryCollaborator):
    if Registry.query.count() >= len(REGISTRY_SEEDS):
        return
    users = {u.email: u for u in User.query.all()}
    if not users:
        return
    products = Product.query.order_by(Product.id).limit(2000).all()
    for owner_email, event_type, title, public_code, event_date in REGISTRY_SEEDS:
        owner = users.get(owner_email)
        if not owner:
            continue
        reg = Registry(
            owner_id=owner.id,
            event_type=event_type,
            title=title,
            public_code=public_code,
            event_date=datetime.strptime(event_date, '%Y-%m-%d'),
            description=f'A {event_type} registry for friends and family.',
            shipping_address=f'{owner.address_line1}, {owner.city}, {owner.state} {owner.zip_code}',
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(public_code, 90)),
        )
        db.session.add(reg)
        db.session.flush()
        # 10 items per registry, deterministic picks
        for i in range(10):
            pidx = _md5_int(f'{public_code}-{i}', len(products))
            prod = products[pidx]
            db.session.add(RegistryItem(
                registry_id=reg.id,
                product_id=prod.id,
                qty_wanted=1 + _md5_int(f'{public_code}-{i}-qty', 3),
                qty_purchased=_md5_int(f'{public_code}-{i}-purch', 2),
                priority=_md5_pick(f'{public_code}-{i}-pri', ['must-have', 'nice-to-have', 'low']),
            ))
        # 2-3 collaborators per registry
        co_emails = [e for e in users if e != owner_email][:3]
        for j, ce in enumerate(co_emails):
            db.session.add(RegistryCollaborator(
                registry_id=reg.id,
                user_id=users[ce].id,
                role='co-owner' if j == 0 else 'viewer',
                invited_at=REFERENCE_DATE - timedelta(days=_md5_int(f'{public_code}-co-{j}', 45)),
            ))
    db.session.commit()


# ===========================================================================
# R5 — Amazon Fresh / Whole Foods sort markers on grocery SKUs
#      (no new table — uses Product.feature_tags JSON-encoded markers)
# ===========================================================================


def seed_r5_fresh_markers(db, Product):
    """Tag a deterministic subset of grocery products with fresh/whole-foods
    routing tags. Idempotent: re-run is a no-op once tags applied."""
    grocery = Product.query.filter(Product.category_slug == 'grocery').limit(800).all()
    changed = 0
    for p in grocery:
        try:
            tags = json.loads(p.feature_tags or '[]')
        except Exception:
            tags = []
        if any(t in ('amazon-fresh', 'whole-foods') for t in tags):
            continue
        pick = _md5_pick(p.slug, ['amazon-fresh', 'whole-foods', 'both'])
        if pick in ('amazon-fresh', 'both'):
            tags.append('amazon-fresh')
        if pick in ('whole-foods', 'both'):
            tags.append('whole-foods')
        # Add shelf-life days deterministically
        shelf = 3 + _md5_int(p.slug, 28)
        tags.append(f'shelf-life-days:{shelf}')
        # Cold-chain temperature class
        temp = _md5_pick(p.slug, ['ambient', 'chilled', 'frozen'])
        tags.append(f'temp:{temp}')
        p.feature_tags = json.dumps(tags)
        changed += 1
    if changed:
        db.session.commit()


# ===========================================================================
# R6 — Q&A questions + answers + votes
# ===========================================================================

QA_PROMPTS = [
    ('Does this fit my device?',                       'Yes — compatible with the device version listed.'),
    ('How long is the battery life?',                  'Manufacturer states 8 hours in typical use.'),
    ('Is the warranty international?',                 'Domestic only by default; extended care plans available at checkout.'),
    ('Does it ship from a US warehouse?',              'Yes, ships from FBA fulfilment centers.'),
    ('Is the box damage-free?',                        'New condition arrives sealed; Renewed grades vary.'),
    ('Are accessories included?',                      'Yes, see the "What\'s in the box" section in the listing.'),
    ('Is it dishwasher-safe?',                         'Hand-wash recommended for longest life.'),
    ('Is the cable USB-C or Micro-USB?',               'USB-C as of the current revision.'),
    ('Does it work with Alexa?',                       'Yes, supports Alexa voice and Echo show.'),
    ('How loud is it on highest setting?',             'About 65 dB at 1 meter under load.'),
]


def seed_r6_qa(db, User, Product, Question, Answer, QAVote):
    if Question.query.count() >= 600:
        return
    users = User.query.order_by(User.id).all()
    products = Product.query.order_by(Product.review_count.desc()).limit(120).all()
    if not users or not products:
        return
    for p in products:
        # 5 questions per top product
        for qi in range(5):
            qtext, atext = QA_PROMPTS[(_md5_int(p.slug + str(qi), len(QA_PROMPTS)))]
            asker = users[_md5_int(f'{p.slug}-q-{qi}', len(users))]
            q = Question(
                product_id=p.id,
                user_id=asker.id,
                body=qtext,
                vote_score=_md5_int(f'{p.slug}-q-{qi}-v', 80) - 10,
                created_at=REFERENCE_DATE - timedelta(days=_md5_int(f'{p.slug}-q-{qi}-t', 180)),
            )
            db.session.add(q)
            db.session.flush()
            # 2 answers per question
            for ai in range(2):
                answerer = users[_md5_int(f'{p.slug}-q-{qi}-a-{ai}', len(users))]
                ans_badge = _md5_pick(f'{p.slug}-q-{qi}-a-{ai}-b',
                                      ['', '', '', 'seller', 'verified-purchase', 'amazon-staff'])
                ans = Answer(
                    question_id=q.id,
                    user_id=answerer.id,
                    body=atext if ai == 0 else atext + ' Also see customer-images for confirmation.',
                    vote_score=_md5_int(f'{p.slug}-q-{qi}-a-{ai}-v', 50),
                    helpful_count=_md5_int(f'{p.slug}-q-{qi}-a-{ai}-h', 30),
                    badge=ans_badge,
                    created_at=REFERENCE_DATE - timedelta(days=_md5_int(f'{p.slug}-q-{qi}-a-{ai}-t', 120)),
                )
                db.session.add(ans)
                db.session.flush()
                # 1 vote per (answer, distinct user)
                voter = users[_md5_int(f'{p.slug}-q-{qi}-a-{ai}-voter', len(users))]
                db.session.add(QAVote(
                    user_id=voter.id,
                    target_kind='answer',
                    target_id=ans.id,
                    value=1 if _md5_int(f'{p.slug}-q-{qi}-a-{ai}-vv', 4) > 0 else -1,
                ))
    db.session.commit()


# ===========================================================================
# R7 — Kindle ebook catalog + Prime Video titles + redemption codes
# ===========================================================================

KINDLE_BOOKS_SEED = [
    ('9780062316097', 'Sapiens: A Brief History of Humankind',          'Yuval Noah Harari',   12.99, True,  'non-fiction'),
    ('9780525559474', 'The Midnight Library',                          'Matt Haig',            9.99,  True,  'fiction'),
    ('9780735211292', 'Atomic Habits',                                 'James Clear',         13.99, True,  'non-fiction'),
    ('9780062457714', 'The Subtle Art of Not Giving a F*ck',           'Mark Manson',          9.99,  True,  'non-fiction'),
    ('9780062696823', 'Educated',                                      'Tara Westover',        10.99, False, 'biography'),
    ('9781501161933', 'It Ends with Us',                               'Colleen Hoover',       7.99,  True,  'fiction'),
    ('9780525536291', 'Where the Crawdads Sing',                       'Delia Owens',          11.99, False, 'fiction'),
    ('9780571365456', 'Klara and the Sun',                             'Kazuo Ishiguro',       12.49, True,  'fiction'),
    ('9780525574323', 'Becoming',                                      'Michelle Obama',       13.49, False, 'biography'),
    ('9780062060624', 'The Way of Kings (Stormlight Archive)',         'Brandon Sanderson',    9.99,  True,  'fantasy'),
    ('9781984822178', 'Project Hail Mary',                             'Andy Weir',            12.99, True,  'sci-fi'),
    ('9781250819857', 'The Atlas Six',                                 'Olivie Blake',         10.99, True,  'fantasy'),
    ('9780525559498', 'Tomorrow, and Tomorrow, and Tomorrow',          'Gabrielle Zevin',      13.99, True,  'fiction'),
    ('9780593189436', 'Lessons in Chemistry',                          'Bonnie Garmus',        12.99, True,  'fiction'),
    ('9780593422951', 'Demon Copperhead',                              'Barbara Kingsolver',   14.99, False, 'fiction'),
    ('9780063031807', 'Babel',                                         'R.F. Kuang',           13.99, True,  'fantasy'),
    ('9780063256491', 'Iron Flame',                                    'Rebecca Yarros',       14.99, True,  'fantasy'),
    ('9780593467824', 'Fourth Wing',                                   'Rebecca Yarros',       13.49, True,  'fantasy'),
    ('9780063340992', 'The Heaven & Earth Grocery Store',              'James McBride',        14.49, True,  'fiction'),
    ('9781668002193', 'Tom Lake',                                      'Ann Patchett',         13.99, True,  'fiction'),
    ('9780593467817', 'The Wager',                                     'David Grann',          12.99, True,  'non-fiction'),
    ('9780593422944', 'Trust',                                         'Hernan Diaz',          11.99, False, 'fiction'),
    ('9780593354414', 'A Little Life',                                 'Hanya Yanagihara',     14.99, False, 'fiction'),
    ('9780765326355', 'The Way of Kings',                              'Brandon Sanderson',    9.99,  True,  'fantasy'),
    ('9780062457141', 'Steve Jobs',                                    'Walter Isaacson',      14.99, False, 'biography'),
    ('9780062459367', 'When Breath Becomes Air',                       'Paul Kalanithi',       10.99, True,  'biography'),
    ('9780812979688', 'The Power of Now',                              'Eckhart Tolle',        9.99,  True,  'non-fiction'),
    ('9781524763138', 'Born a Crime',                                  'Trevor Noah',          11.99, True,  'biography'),
    ('9780525536499', 'Talking to Strangers',                          'Malcolm Gladwell',     12.99, False, 'non-fiction'),
    ('9780812995435', 'Sapiens',                                       'Yuval Noah Harari',    12.99, True,  'non-fiction'),
]


def seed_r7_kindle(db, KindleBook):
    if KindleBook.query.count() >= len(KINDLE_BOOKS_SEED):
        return
    for isbn, title, author, price, ku, genre in KINDLE_BOOKS_SEED:
        slug = title.lower().replace(' ', '-').replace('—', '-')[:80]
        slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
        db.session.add(KindleBook(
            isbn=isbn,
            title=title,
            author=author,
            price=price,
            kindle_unlimited=ku,
            genre=genre,
            slug=slug,
            file_size_mb=1 + _md5_int(isbn, 12),
            page_count=180 + _md5_int(isbn, 420),
            language='English',
            release_date=REFERENCE_DATE - timedelta(days=_md5_int(isbn, 2400)),
        ))
    db.session.commit()


PRIME_VIDEO_TITLES = [
    ('Reacher',                      'series', 2022, True,  'action'),
    ('The Boys',                     'series', 2019, True,  'superhero'),
    ('The Marvelous Mrs. Maisel',    'series', 2017, True,  'comedy'),
    ('Fallout',                      'series', 2024, True,  'sci-fi'),
    ('Mr. & Mrs. Smith',             'series', 2024, True,  'action'),
    ('The Wheel of Time',            'series', 2021, True,  'fantasy'),
    ('Citadel',                      'series', 2023, True,  'spy-thriller'),
    ('The Rings of Power',           'series', 2022, True,  'fantasy'),
    ('Jack Ryan',                    'series', 2018, True,  'thriller'),
    ('Gen V',                        'series', 2023, True,  'superhero'),
    ('Air',                          'movie',  2023, True,  'drama'),
    ('Saltburn',                     'movie',  2023, True,  'thriller'),
    ('Argylle',                      'movie',  2024, False, 'action'),
    ('The Tomorrow War',             'movie',  2021, True,  'sci-fi'),
    ('Manchester by the Sea',        'movie',  2016, True,  'drama'),
    ('Sound of Metal',               'movie',  2019, True,  'drama'),
    ('Coming 2 America',             'movie',  2021, True,  'comedy'),
    ('My Spy: The Eternal City',     'movie',  2024, True,  'action'),
    ('Road House',                   'movie',  2024, True,  'action'),
    ('The Idea of You',              'movie',  2024, True,  'romance'),
    ('Cassandra',                    'movie',  2024, True,  'drama'),
    ('The Big Sick',                 'movie',  2017, True,  'romance'),
    ('A Quiet Place',                'movie',  2018, False, 'horror'),
    ('Knives Out',                   'movie',  2019, False, 'mystery'),
    ('The Voice',                    'series', 2023, True,  'reality'),
    ('Top Gear America',             'series', 2021, True,  'reality'),
    ('Carnival Row',                 'series', 2019, True,  'fantasy'),
    ('Goliath',                      'series', 2016, True,  'legal'),
    ('Bosch: Legacy',                'series', 2022, True,  'crime'),
    ('Hunters',                      'series', 2020, True,  'thriller'),
]


def seed_r7_prime_video(db, PrimeVideoTitle):
    if PrimeVideoTitle.query.count() >= len(PRIME_VIDEO_TITLES):
        return
    for i, (title, kind, year, prime_inc, genre) in enumerate(PRIME_VIDEO_TITLES):
        slug = title.lower().replace(' ', '-').replace('.', '').replace(':', '').replace("'", '')
        slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
        db.session.add(PrimeVideoTitle(
            slug=slug,
            title=title,
            kind=kind,
            year=year,
            included_with_prime=prime_inc,
            genre=genre,
            imdb_rating=round(5.5 + _md5_int(slug, 35) / 10.0, 1),
            episode_count=(8 + _md5_int(slug, 16)) if kind == 'series' else 1,
            runtime_minutes=(40 + _md5_int(slug, 30)) if kind == 'series' else (90 + _md5_int(slug, 50)),
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(slug, 1200)),
        ))
    db.session.commit()


REDEMPTION_CODES = [
    ('GIFT-ALICE-50',       'gift-card',   50.00,  'unredeemed'),
    ('GIFT-BOB-25',         'gift-card',   25.00,  'unredeemed'),
    ('PRIMEVIDEO-3MO-CAROL','prime-video', 0.00,   'unredeemed'),
    ('KINDLEUNL-1MO-DAVID', 'kindle-unl',  0.00,   'unredeemed'),
    ('MUSICUNL-3MO-PROMO',  'music-unl',   0.00,   'unredeemed'),
    ('AUDIBLE-30DAY-FREE',  'audible',     0.00,   'unredeemed'),
    ('GIFT-USED-100',       'gift-card',   100.00, 'redeemed'),
    ('GIFT-DEMO-15',        'gift-card',   15.00,  'unredeemed'),
    ('PROMO-FRESH-FREESHIP','promo',       0.00,   'unredeemed'),
    ('PROMO-DEALDAY-10OFF', 'promo',       10.00,  'unredeemed'),
]


def seed_r7_redemption_codes(db, RedemptionCode):
    if RedemptionCode.query.count() >= len(REDEMPTION_CODES):
        return
    for code, kind, val, status in REDEMPTION_CODES:
        db.session.add(RedemptionCode(
            code=code,
            kind=kind,
            value_usd=val,
            status=status,
            issued_at=REFERENCE_DATE - timedelta(days=_md5_int(code, 200)),
        ))
    db.session.commit()


# ===========================================================================
# R8 — Seller profiles + brand storefronts (md5-derived seller_id)
# ===========================================================================

# Real consumer brand list (subset of Wikipedia "List of consumer brands"
# popular on Amazon US). Each maps to a deterministic seller_id via md5.
REAL_BRANDS = [
    ('Anker',          'Anker Innovations',         'CN', 2011),
    ('Bose',           'Bose Corporation',          'US', 1964),
    ('Sony',           'Sony Group',                'JP', 1946),
    ('Samsung',        'Samsung Electronics',       'KR', 1969),
    ('Apple',          'Apple Inc.',                'US', 1976),
    ('Logitech',       'Logitech International',    'CH', 1981),
    ('Microsoft',      'Microsoft Corporation',     'US', 1975),
    ('LG',             'LG Electronics',            'KR', 1958),
    ('Dell',           'Dell Technologies',         'US', 1984),
    ('HP',             'HP Inc.',                   'US', 1939),
    ('Lenovo',         'Lenovo Group',              'CN', 1984),
    ('ASUS',           'ASUSTeK Computer',          'TW', 1989),
    ('Acer',           'Acer Inc.',                 'TW', 1976),
    ('Razer',          'Razer Inc.',                'SG', 2005),
    ('Canon',          'Canon Inc.',                'JP', 1937),
    ('Nikon',          'Nikon Corporation',         'JP', 1917),
    ('GoPro',          'GoPro Inc.',                'US', 2002),
    ('JBL',            'Harman International',      'US', 1946),
    ('Beats',          'Beats Electronics',         'US', 2006),
    ('Sennheiser',     'Sennheiser Electronic',     'DE', 1945),
    ('Nest',           'Google Nest',               'US', 2010),
    ('Ring',           'Ring (Amazon)',             'US', 2013),
    ('Roomba',         'iRobot Corporation',        'US', 1990),
    ('Dyson',          'Dyson Ltd.',                'GB', 1991),
    ('KitchenAid',     'Whirlpool Corp.',           'US', 1919),
    ('Instant Pot',    'Instant Brands',            'CA', 2009),
    ('Ninja',          'SharkNinja Operating',      'US', 1995),
    ('Cuisinart',      'Conair Corporation',        'US', 1971),
    ('OXO',            'OXO International',         'US', 1990),
    ('Hamilton Beach', 'Hamilton Beach Brands',     'US', 1910),
    ('Bissell',        'Bissell Inc.',              'US', 1876),
    ('Shark',          'SharkNinja Operating',      'US', 1998),
    ('Vitamix',        'Vita-Mix Corporation',      'US', 1921),
    ('Pyrex',          'Corelle Brands',            'US', 1915),
    ('Le Creuset',     'Le Creuset Group',          'FR', 1925),
    ('Lodge',          'Lodge Cast Iron',           'US', 1896),
    ('Yeti',           'Yeti Coolers',              'US', 2006),
    ('Hydro Flask',    'Helen of Troy',             'US', 2009),
    ('Stanley',        'PMI Worldwide',             'US', 1913),
    ('Patagonia',      'Patagonia Inc.',            'US', 1973),
    ('North Face',     'VF Corporation',            'US', 1966),
    ('Columbia',       'Columbia Sportswear',       'US', 1938),
    ('Nike',           'Nike Inc.',                 'US', 1964),
    ('Adidas',         'Adidas AG',                 'DE', 1949),
    ('Puma',           'Puma SE',                   'DE', 1948),
    ('Levi\'s',        'Levi Strauss & Co.',        'US', 1853),
    ('Calvin Klein',   'PVH Corp.',                 'US', 1968),
    ('Tommy Hilfiger', 'PVH Corp.',                 'US', 1985),
    ('Ralph Lauren',   'Ralph Lauren Corp.',        'US', 1967),
    ('Under Armour',   'Under Armour Inc.',         'US', 1996),
    ('L\'Oreal',       'L\'Oréal S.A.',             'FR', 1909),
    ('Olay',           'Procter & Gamble',          'US', 1949),
    ('Maybelline',     'L\'Oréal S.A.',             'FR', 1915),
    ('Neutrogena',     'Johnson & Johnson',         'US', 1930),
    ('Aveeno',         'Johnson & Johnson',         'US', 1945),
    ('Cetaphil',       'Galderma Laboratories',     'CH', 1947),
    ('CeraVe',         'L\'Oréal S.A.',             'FR', 2005),
    ('Bath & Body Works','L Brands',               'US', 1990),
    ('Crest',          'Procter & Gamble',          'US', 1955),
    ('Colgate',        'Colgate-Palmolive',         'US', 1873),
    ('Oral-B',         'Procter & Gamble',          'US', 1950),
    ('Philips',        'Koninklijke Philips',       'NL', 1891),
    ('Braun',          'De\'Longhi Group',          'DE', 1921),
    ('Gillette',       'Procter & Gamble',          'US', 1901),
    ('Schick',         'Edgewell Personal Care',    'US', 1926),
    ('Tide',           'Procter & Gamble',          'US', 1946),
    ('Pampers',        'Procter & Gamble',          'US', 1961),
    ('Huggies',        'Kimberly-Clark',            'US', 1968),
    ('Fisher-Price',   'Mattel Inc.',               'US', 1930),
    ('Mattel',         'Mattel Inc.',               'US', 1945),
    ('Hasbro',         'Hasbro Inc.',               'US', 1923),
    ('LEGO',           'The LEGO Group',            'DK', 1932),
    ('Crayola',        'Hallmark Cards',            'US', 1885),
    ('Melissa & Doug', 'Spin Master Corp.',         'US', 1988),
    ('Bandai',         'Bandai Namco',              'JP', 1950),
    ('Funko',          'Funko Inc.',                'US', 1998),
    ('Nintendo',       'Nintendo Co., Ltd.',        'JP', 1889),
    ('Activision',     'Microsoft Gaming',          'US', 1979),
    ('Ubisoft',        'Ubisoft Entertainment',     'FR', 1986),
    ('Epson',          'Seiko Epson',               'JP', 1942),
    ('Brother',        'Brother Industries',        'JP', 1908),
    ('Bissell',        'Bissell Inc.',              'US', 1876),
]


def seed_r8_sellers(db, SellerProfile, BrandStore):
    if SellerProfile.query.count() >= 30:
        return
    seen = set()
    for brand, legal_name, country, founded in REAL_BRANDS:
        if brand in seen:
            continue
        seen.add(brand)
        seller_id = int(hashlib.md5(brand.encode('utf-8')).hexdigest()[:8], 16)
        sp = SellerProfile(
            id=seller_id % 99999999,
            brand=brand,
            legal_name=legal_name,
            country=country,
            founded_year=founded,
            rating=round(3.5 + _md5_int(brand, 16) / 10.0, 1),
            review_count=100 + _md5_int(brand, 9000),
            fulfillment=_md5_pick(brand, ['FBA', 'FBA', 'FBM', 'FBA-mixed']),
            response_time_hours=2 + _md5_int(brand, 22),
            on_time_delivery_pct=85 + _md5_int(brand, 14),
            cancellation_rate_pct=_md5_int(brand, 5),
            late_shipment_rate_pct=_md5_int(brand, 4),
            customer_service_rating=round(4.0 + _md5_int(brand, 9) / 10.0, 1),
            joined_at=REFERENCE_DATE - timedelta(days=365 * (1 + _md5_int(brand, 8))),
        )
        db.session.add(sp)
        db.session.flush()
        # Each brand seller also opens a "brand store"
        bstore = BrandStore(
            seller_id=sp.id,
            brand_slug=brand.lower().replace(' ', '-').replace("'", '').replace('.', ''),
            title=f"{brand} Brand Store",
            banner_image=f"/static/images/brand/{brand.lower().replace(' ', '-')}.jpg",
            tagline=f"Shop the official {brand} storefront on Amazon.",
            featured_categories='electronics,home,fashion'[:60],
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(brand, 600)),
        )
        db.session.add(bstore)
    db.session.commit()


# ===========================================================================
# R9 — Vine reviewer roster + Vine items + Early Reviewer + promo codes
# ===========================================================================

VINE_TIER_THRESHOLDS = [(500, 'gold'), (250, 'silver'), (50, 'bronze')]


def seed_r9_vine(db, User, Product, VineMember, VineItem, EarlyReviewerItem, PromoCode):
    if VineMember.query.count() >= 4:
        return
    users = User.query.order_by(User.id).all()
    products = Product.query.order_by(Product.review_count.desc()).limit(200).all()
    for u in users[:6]:
        items_reviewed = 50 + _md5_int(u.email, 700)
        tier = 'bronze'
        for floor, name in VINE_TIER_THRESHOLDS:
            if items_reviewed >= floor:
                tier = name
                break
        db.session.add(VineMember(
            user_id=u.id,
            tier=tier,
            items_reviewed=items_reviewed,
            helpful_votes=10 + _md5_int(u.email + 'h', 1500),
            joined_at=REFERENCE_DATE - timedelta(days=_md5_int(u.email, 1200)),
        ))
    # Vine items — products eligible for Vine review
    for i, p in enumerate(products[:60]):
        db.session.add(VineItem(
            product_id=p.id,
            eligible_until=REFERENCE_DATE + timedelta(days=30 + _md5_int(p.slug, 60)),
            estimated_value_usd=p.price,
            claimed_by_user_id=None if (_md5_int(p.slug, 3) == 0) else users[_md5_int(p.slug + 'v', len(users))].id,
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(p.slug + 'vi', 30)),
        ))
    # Early-reviewer program (legacy) — products that have only 1-5 reviews
    early_targets = [p for p in products if p.review_count <= 5][:40]
    for p in early_targets:
        db.session.add(EarlyReviewerItem(
            product_id=p.id,
            reward_amount_usd=_md5_pick(p.slug + 'er', [1.00, 2.00, 3.00, 5.00, 10.00]),
            completed_reviews=_md5_int(p.slug + 'erc', 5),
            target_reviews=5,
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(p.slug + 'ert', 90)),
        ))
    # Promo codes
    promo_codes = [
        ('PRIMEDAY26',  15, 1000, 0, '2026-07-15'),
        ('BACK2SCHOOL', 10, 500,  0, '2026-09-05'),
        ('CYBER26',     20, 2000, 0, '2026-12-02'),
        ('FRESH5',       5, 5000, 0, '2026-12-31'),
        ('VINE-WELCOME',25, 100,  0, '2026-12-31'),
        ('GIFT-NEW10',  10, 999,  0, '2026-12-31'),
        ('AUDIBLE-FREE',100, 50,  0, '2026-12-31'),
        ('KU-30DAY',    100, 200, 0, '2026-12-31'),
        ('MUSIC-FREE',  100, 200, 0, '2026-12-31'),
        ('REFURB-15',   15, 300,  0, '2026-12-31'),
    ]
    for code, pct, mu, used, expires in promo_codes:
        db.session.add(PromoCode(
            code=code,
            percent_off=pct,
            max_uses=mu,
            uses=used,
            expires_at=datetime.strptime(expires, '%Y-%m-%d'),
            created_at=REFERENCE_DATE - timedelta(days=_md5_int(code, 90)),
        ))
    db.session.commit()


# ===========================================================================
# R10 — Webhook event log (synthetic, for /api/v1 callbacks)
# ===========================================================================


def seed_r10_webhooks(db, Order, WebhookEvent):
    if WebhookEvent.query.count() >= 20:
        return
    orders = Order.query.order_by(Order.id).limit(20).all()
    for i, o in enumerate(orders):
        for kind in ('order.created', 'order.shipped', 'order.delivered'):
            event_id = f'evt_{i:04d}_{kind.replace(".", "_")}'
            db.session.add(WebhookEvent(
                event_id=event_id,
                kind=kind,
                payload_json=json.dumps({
                    'order_id': o.id,
                    'order_number': o.order_number,
                    'status': kind.split('.')[-1],
                    'total': float(o.total or 0),
                }, sort_keys=True),
                delivered_at=REFERENCE_DATE - timedelta(days=_md5_int(event_id, 60)),
                attempts=1,
                http_status=200,
            ))
    db.session.commit()


# ===========================================================================
# Top-level runner
# ===========================================================================


def run_deepen(db, models):
    """Single-entry deepen runner.

    `models` is a dict bridging this module to the model classes defined in
    app.py (so we don't double-register them via SQLAlchemy declarative).

    Idempotency / byte-identical: the normalize+VACUUM step at the end can
    re-shuffle SQLite page bytes if invoked on a DB that already contains
    the deepening rows (b-tree fanout depends on history of inserts).  So
    we skip normalize entirely when every seeder reports "already at
    floor".  The first build (cold seed DB → deepening rows) is the only
    one where normalize runs; subsequent boots re-use the canonical
    bytes shipped in instance_seed/.
    """
    # Detect "warm" boot — every deepening table at floor → no work to do.
    cold = (
        models['SubscribeSavePlan'].query.count() < 12
        or models['Registry'].query.count() < 6
        or models['Question'].query.count() < 600
        or models['KindleBook'].query.count() < 30
        or models['PrimeVideoTitle'].query.count() < 30
        or models['SellerProfile'].query.count() < 30
        or models['VineMember'].query.count() < 4
        or models['WebhookEvent'].query.count() < 20
    )
    if not cold:
        # Warm restart — DB already deepened, nothing to do.
        return

    seed_r3_subscribe_save(db, models['User'], models['Product'],
                           models['SubscribeSavePlan'], models['AutoDeliverySchedule'])
    seed_r4_registries(db, models['User'], models['Product'],
                       models['Registry'], models['RegistryItem'], models['RegistryCollaborator'])
    seed_r5_fresh_markers(db, models['Product'])
    seed_r6_qa(db, models['User'], models['Product'],
               models['Question'], models['Answer'], models['QAVote'])
    seed_r7_kindle(db, models['KindleBook'])
    seed_r7_prime_video(db, models['PrimeVideoTitle'])
    seed_r7_redemption_codes(db, models['RedemptionCode'])
    seed_r8_sellers(db, models['SellerProfile'], models['BrandStore'])
    seed_r9_vine(db, models['User'], models['Product'],
                 models['VineMember'], models['VineItem'],
                 models['EarlyReviewerItem'], models['PromoCode'])
    seed_r10_webhooks(db, models['Order'], models['WebhookEvent'])
    # Re-emit ix_* indexes alpha + VACUUM so rebuilds stay byte-identical.
    from sqlalchemy import text
    conn = db.engine.connect()
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.commit()
    conn.close()
    raw = db.engine.raw_connection()
    raw.isolation_level = None
    try:
        raw.execute("VACUUM")
    finally:
        raw.close()
