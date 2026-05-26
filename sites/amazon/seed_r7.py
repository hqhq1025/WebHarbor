#!/usr/bin/env python3
"""R7 polish pass — push catalog from ~21.1k to 30000+.

What this adds on top of R6 (seed_r6.py):

  • Three new storefront category_slugs registered in seed_data.CATEGORIES:
        grocery (Amazon Fresh + Whole Foods)
        audible (audiobooks by genre + narrator)
        kindle  (Kindle ebooks across fiction / non-fiction / textbook)
  • Distinct R7_SUFFIXES (32 fresh codenames) — no collision with R2/R4/R5/R6.
  • R7_TEMPLATES — brand × product-family tuples for the four new long-tail
    storefronts. Same shape as R6_NEW_TEMPLATES (brand, name_tpl, subcat,
    base_price, list_uplift, tag_csv, specs_template).
  • Replays SKU_TEMPLATES / R4 / R5 / R6 template pools with R7_SUFFIXES so
    each fresh suffix unlocks new slugs in existing categories too.
  • Adds R7 quality fields on top of R5/R6:
        - dietary tags (organic, gluten-free, kosher, vegan, low-fodmap)
          on grocery SKUs
        - narrator + listen-time on audible SKUs
        - kindle-unlimited flag + file-size on kindle SKUs

Deterministic: every numeric / boolean derived from idx + sfx_idx, so
rebuilds stay byte-identical. No datetime.now() / random without seed.

Idempotent — exits early when Product.count() already >= 29500 (R7 floor).
"""
import os

from seed_bulk import (
    SKU_TEMPLATES, _insert_product, _category_pool,
    COLOR_NAMES, SIZE_VALUES, SHOE_SIZES,
)
from seed_polish import R4_NEW_TEMPLATES
from seed_r5 import (
    R5_NEW_TEMPLATES, MADE_IN_BUCKETS, AGE_BUCKETS, SNS_CATEGORIES,
)
from seed_r6 import R6_NEW_TEMPLATES


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Distinct codename pool — no overlap with R2 / R4 / R5 / R6 suffix lists.
R7_SUFFIXES = [
    'Aurora', 'Borealis', 'Cascade', 'Dunes', 'Equinox', 'Fjord',
    'Glacier', 'Harbor', 'Isthmus', 'Jetstream', 'Kingfisher', 'Lagoon',
    'Meridian', 'Nautilus', 'Outrigger', 'Prairie', 'Quicksilver', 'Ravine',
    'Solstice', 'Tundra', 'Updraft', 'Vortex', 'Wavecrest', 'Xeranth',
    'Yardarm', 'Zenith', 'Anchorage', 'Bayou', 'Crestline', 'Driftwood',
    'Ember', 'Frostvale',
]


# Dietary buckets for grocery
DIETARY_TAGS = [
    'usda-organic', 'gluten-free', 'kosher', 'vegan', 'non-gmo',
    'low-fodmap', 'paleo-friendly', 'keto-friendly',
]


# ---------------------------------------------------------------------------
# R7-only templates — Amazon Fresh + Whole Foods + Audible + Kindle.
# Shape matches _build_generic_sku in seed_bulk:
#   (brand, name_tpl_with_{sku}, subcategory, base_price, list_uplift_pct,
#    tag_csv, specs_template)
# ---------------------------------------------------------------------------

R7_TEMPLATES = {
    # ---------------------- GROCERY (Amazon Fresh + Whole Foods) ----------
    'grocery': [
        # Pantry — Amazon Fresh
        ('Amazon Fresh', 'Organic Extra Virgin Olive Oil {sku} 16.9 fl oz', 'Pantry', 11.99, 18,
         'pantry,oil,organic',
         {'Volume': '16.9 fl oz', 'Origin': 'Spain', 'Cold Pressed': 'Yes'}),
        ('Amazon Fresh', 'Cold-Pressed Avocado Oil {sku} 25 fl oz', 'Pantry', 13.49, 22,
         'pantry,oil,avocado',
         {'Volume': '25 fl oz', 'Smoke Point': '500F'}),
        ('Amazon Fresh', 'Aged Balsamic Vinegar {sku} of Modena 16.9 fl oz', 'Pantry', 9.99, 25,
         'pantry,vinegar,italian',
         {'Volume': '16.9 fl oz', 'Origin': 'Modena, Italy', 'PGI': 'Yes'}),
        ('Amazon Fresh', 'Pink Himalayan Salt {sku} Fine Grain 32 oz', 'Pantry', 7.99, 28,
         'pantry,salt,himalayan',
         {'Weight': '32 oz', 'Grain': 'Fine', 'Origin': 'Pakistan'}),
        ('Amazon Fresh', 'Organic {sku} Quinoa Tri-Color 32 oz', 'Pantry', 8.49, 22,
         'pantry,grain,quinoa,organic',
         {'Weight': '32 oz', 'Variety': 'Red/White/Black blend'}),
        # Whole Foods 365 — pantry staples
        ('365 by Whole Foods', 'Organic Marinara {sku} Pasta Sauce 24 oz', 'Pantry', 4.49, 18,
         'pantry,sauce,organic,wholefoods',
         {'Volume': '24 oz', 'Tomato': 'San Marzano', 'No Sugar Added': 'Yes'}),
        ('365 by Whole Foods', 'Steel-Cut Oats {sku} 30 oz Canister', 'Pantry', 4.99, 22,
         'pantry,oats,breakfast,wholefoods',
         {'Weight': '30 oz', 'Variety': 'Steel-cut Irish'}),
        ('365 by Whole Foods', 'Almond Butter {sku} Creamy Unsweetened 16 oz', 'Pantry', 9.99, 22,
         'pantry,nut-butter,wholefoods',
         {'Volume': '16 oz', 'Ingredients': 'Almonds (no salt, no sugar)'}),
        # Beverages
        ('Amazon Fresh', 'Cold-Brew Coffee Concentrate {sku} 32 oz', 'Beverages', 12.99, 22,
         'beverages,coffee,cold-brew',
         {'Volume': '32 oz', 'Roast': 'Medium', 'Servings': '8'}),
        ('365 by Whole Foods', 'Organic {sku} Sparkling Water 12-pack', 'Beverages', 4.99, 25,
         'beverages,sparkling,wholefoods',
         {'Pack': '12 cans', 'Size': '12 fl oz', 'Sugar': '0g'}),
        ('La Croix', 'Sparkling Water {sku} Variety 24-Pack', 'Beverages', 14.99, 18,
         'beverages,sparkling,zero-cal',
         {'Pack': '24 cans', 'Calories': '0', 'Flavors': 'Lime/Lemon/Grapefruit'}),
        ('Pellegrino', 'Sparkling Natural Mineral Water {sku} 750ml 12-Pack', 'Beverages', 22.99, 18,
         'beverages,mineral-water,italian',
         {'Volume': '750ml x 12', 'TDS': '950 mg/L', 'Origin': 'Italy'}),
        # Snacks
        ('Amazon Fresh', 'Mixed Nuts Deluxe {sku} Roasted Salted 32 oz', 'Snacks', 16.99, 22,
         'snacks,nuts,deluxe',
         {'Weight': '32 oz', 'Variety': 'Almonds/Cashews/Pecans/Brazil'}),
        ('365 by Whole Foods', 'Organic Tortilla Chips {sku} Sea Salt 12 oz', 'Snacks', 3.49, 25,
         'snacks,chips,organic,wholefoods',
         {'Weight': '12 oz', 'Salt': 'Sea salt only', 'Oil': 'Sunflower'}),
        ('Siete', 'Grain-Free Tortilla Chips {sku} Sea Salt 5 oz', 'Snacks', 4.99, 18,
         'snacks,grain-free,paleo',
         {'Weight': '5 oz', 'Free Of': 'Gluten, grain, dairy'}),
        ('Kind', 'Dark Chocolate Nuts Sea Salt {sku} 12-Bar Box', 'Snacks', 14.99, 22,
         'snacks,bar,gluten-free',
         {'Pack': '12 bars', 'Sugar': '5g/bar'}),
        # Dairy / refrigerated (Whole Foods)
        ('365 by Whole Foods', 'Organic Whole Milk {sku} Half-Gallon', 'Dairy', 4.49, 18,
         'dairy,milk,organic,wholefoods',
         {'Volume': '64 fl oz', 'Fat': 'Whole 3.25%'}),
        ('Oatly', 'Oat Milk {sku} Original 64 oz', 'Dairy', 5.99, 22,
         'dairy,plant-milk,oat',
         {'Volume': '64 fl oz', 'Source': 'Oats (gluten-free)'}),
        ('Chobani', 'Greek Yogurt {sku} Plain Whole-Milk 32 oz', 'Dairy', 5.49, 22,
         'dairy,yogurt,greek',
         {'Volume': '32 oz', 'Protein': '17g/cup'}),
        ('Vital Farms', 'Pasture-Raised Large {sku} Eggs Dozen', 'Dairy', 7.49, 18,
         'dairy,eggs,pasture-raised',
         {'Count': '12 large', 'Welfare': 'Certified Humane'}),
        # Frozen
        ('Amazon Fresh', 'Wild-Caught Salmon Fillets {sku} 12 oz Frozen', 'Frozen', 14.99, 22,
         'frozen,seafood,salmon',
         {'Weight': '12 oz', 'Species': 'Sockeye', 'Source': 'Alaska wild-caught'}),
        ('365 by Whole Foods', 'Organic Mixed Berries {sku} 10 oz Frozen', 'Frozen', 4.99, 22,
         'frozen,berries,organic,wholefoods',
         {'Weight': '10 oz', 'Variety': 'Blueberry/Strawberry/Raspberry'}),
        ('Amy\'s', 'Organic Burrito {sku} Bean & Rice 6 oz', 'Frozen', 3.99, 22,
         'frozen,meal,organic,vegan',
         {'Weight': '6 oz', 'Calories': '290'}),
        # Produce + meat (long-tail)
        ('Amazon Fresh', 'Organic Hass Avocados {sku} 4-Count Bag', 'Produce', 5.99, 20,
         'produce,avocado,organic',
         {'Count': '4', 'Origin': 'Mexico', 'Ripeness': 'Ready to eat in 2-3 days'}),
        ('Amazon Fresh', 'Organic Bananas {sku} 2 lb Bunch', 'Produce', 2.49, 22,
         'produce,banana,organic',
         {'Weight': '2 lb', 'Variety': 'Cavendish'}),
        ('Whole Foods Market', 'Animal Welfare Step {sku} Boneless Chicken Breast 1 lb', 'Meat', 8.99, 18,
         'meat,chicken,welfare',
         {'Weight': '1 lb', 'Rating': 'Animal Welfare Step 3'}),
        # Bakery / breakfast
        ('365 by Whole Foods', 'Sourdough Loaf {sku} 24 oz Bakery', 'Bakery', 4.99, 20,
         'bakery,sourdough,wholefoods',
         {'Weight': '24 oz', 'Style': 'Country sourdough'}),
        ('Dave\'s Killer Bread', 'Powerseed {sku} Organic Loaf 25 oz', 'Bakery', 5.49, 18,
         'bakery,organic,whole-grain',
         {'Weight': '25 oz', 'Whole Grains': '21g/slice'}),
        # Pet (Amazon Fresh / Whole Foods adjacent)
        ('Amazon Fresh', 'Wild Salmon Dog Treats {sku} Single-Ingredient 6 oz', 'Pet Food', 11.99, 22,
         'pet,dog,treats,single-ingredient',
         {'Weight': '6 oz', 'Ingredient': '100% wild salmon'}),
    ],

    # ---------------------- AUDIBLE (audiobooks) --------------------------
    'audible': [
        # Fiction
        ('Audible Studios', '{sku} Ascendant — A Novel (Unabridged)', 'Fiction', 24.95, 30,
         'audiobook,fiction,unabridged',
         {'Length': '13 hr 42 min', 'Narrator': 'January LaVoy', 'Format': 'Unabridged'}),
        ('Random House Audio', 'The Last Lighthouse {sku} (Unabridged)', 'Fiction', 27.95, 32,
         'audiobook,fiction,whisper-sync',
         {'Length': '11 hr 28 min', 'Narrator': 'Rosamund Pike', 'Whispersync': 'Yes'}),
        ('Macmillan Audio', 'Songbird Hollow {sku} A Novel', 'Fiction', 24.95, 30,
         'audiobook,literary-fiction',
         {'Length': '12 hr 02 min', 'Narrator': 'Edoardo Ballerini'}),
        ('Penguin Audio', 'Salt and Story {sku} Audiobook', 'Fiction', 22.95, 30,
         'audiobook,family-saga,literary',
         {'Length': '10 hr 49 min', 'Narrator': 'Saskia Maarleveld'}),
        # Mystery / Thriller
        ('Audible Studios', 'Mercy River {sku} Detective Mira Holt #4', 'Mystery', 24.95, 30,
         'audiobook,mystery,detective,series',
         {'Length': '9 hr 31 min', 'Narrator': 'Tavia Gilbert', 'Series': 'Mira Holt'}),
        ('Hachette Audio', 'The Quiet Witness {sku} Thriller', 'Mystery', 26.95, 28,
         'audiobook,thriller,bestseller',
         {'Length': '12 hr 11 min', 'Narrator': 'Will Damron'}),
        ('Simon & Schuster Audio', 'Cold Iron {sku} A Sam Bennett Novel', 'Mystery', 25.95, 28,
         'audiobook,crime,procedural',
         {'Length': '10 hr 18 min', 'Narrator': 'Robert Petkoff'}),
        # Sci-Fi / Fantasy
        ('Audible Studios', 'Tide of Stars {sku} The Helix Cycle Book 1', 'SciFi & Fantasy', 27.95, 32,
         'audiobook,scifi,space-opera',
         {'Length': '17 hr 22 min', 'Narrator': 'Ray Porter', 'Series': 'Helix Cycle'}),
        ('Audible Studios', 'Emberhold {sku} Dragonbound Saga Book 1', 'SciFi & Fantasy', 27.95, 32,
         'audiobook,fantasy,epic,series',
         {'Length': '21 hr 04 min', 'Narrator': 'Michael Kramer'}),
        ('Recorded Books', 'The Glasswright {sku} An Imaginary History', 'SciFi & Fantasy', 24.95, 30,
         'audiobook,fantasy,worldbuilding',
         {'Length': '15 hr 47 min', 'Narrator': 'Suzy Jackson'}),
        # Self-Help / Business
        ('Penguin Audio', 'Deep Focus {sku} Reclaiming Attention', 'Self-Development', 22.95, 28,
         'audiobook,productivity,focus,non-fiction',
         {'Length': '7 hr 12 min', 'Narrator': 'Author', 'Bonus PDF': 'Yes'}),
        ('HarperAudio', '{sku} Effect — Compound Habits, Real Change', 'Self-Development', 21.95, 28,
         'audiobook,habits,self-help',
         {'Length': '6 hr 48 min', 'Narrator': 'Author'}),
        ('Audible Originals', 'The Negotiator Within {sku}', 'Business', 0.00, 0,
         'audiobook,business,audible-original,plus-catalog',
         {'Length': '5 hr 31 min', 'Narrator': 'Author', 'Plus Catalog': 'Included with membership'}),
        # History / Biography
        ('Audible Studios', 'Lincoln\'s Compass {sku} The 1864 Election', 'History', 26.95, 30,
         'audiobook,history,civil-war,biography',
         {'Length': '14 hr 02 min', 'Narrator': 'Grover Gardner'}),
        ('Penguin Audio', 'Mary Shelley {sku} A Life on Fire', 'Biography', 28.95, 30,
         'audiobook,biography,literary',
         {'Length': '16 hr 18 min', 'Narrator': 'Juliet Stevenson'}),
        # Science
        ('Audible Studios', '{sku} Patterns — The Hidden Math of Everything', 'Science', 25.95, 30,
         'audiobook,science,popular-math',
         {'Length': '8 hr 56 min', 'Narrator': 'Sean Pratt'}),
        ('Hachette Audio', 'Deep Time {sku} 4 Billion Years in 12 Hours', 'Science', 27.95, 30,
         'audiobook,geology,science',
         {'Length': '12 hr 04 min', 'Narrator': 'Author'}),
        # Memoir
        ('HarperAudio', 'Salt of the Sky {sku} A Pilot\'s Memoir', 'Memoir', 24.95, 28,
         'audiobook,memoir,aviation',
         {'Length': '9 hr 38 min', 'Narrator': 'Author'}),
        ('Audible Originals', 'Letters from the {sku} Edge', 'Memoir', 0.00, 0,
         'audiobook,memoir,audible-original,plus-catalog',
         {'Length': '4 hr 22 min', 'Plus Catalog': 'Included with membership'}),
        # Romance / Romantasy
        ('Bramble Audio', '{sku} Crowned Court (Romantasy)', 'Romance', 26.95, 30,
         'audiobook,romance,romantasy',
         {'Length': '13 hr 18 min', 'Narrator': 'Soneela Nankani'}),
        ('Audible Studios', 'Summer of Wildflowers {sku} (Contemporary Romance)', 'Romance', 22.95, 28,
         'audiobook,romance,contemporary',
         {'Length': '8 hr 14 min', 'Narrator': 'Julia Whelan'}),
        # YA
        ('Listening Library', '{sku} of Bone and Tide — YA Fantasy', 'Young Adult', 24.95, 30,
         'audiobook,ya,fantasy',
         {'Length': '11 hr 22 min', 'Narrator': 'Imani Jade Powers'}),
        # Kids / Family
        ('Audible Studios', 'Adventures of {sku} the Knight (Full Cast)', 'Kids', 19.95, 30,
         'audiobook,kids,full-cast',
         {'Length': '3 hr 42 min', 'Narrator': 'Full cast', 'Age': '6-10'}),
        # Language Learning
        ('Pimsleur', 'Spanish Conversational Course {sku} Level 1', 'Language', 19.95, 30,
         'audiobook,language,spanish',
         {'Length': '8 hr 00 min', 'Method': 'Pimsleur audio'}),
        ('Living Language', 'Beginning French {sku} Audio Course', 'Language', 19.95, 30,
         'audiobook,language,french',
         {'Length': '6 hr 20 min'}),
        # Audible Plus
        ('Audible Originals', 'Behind the Hit {sku} (Podcast-Style)', 'Audible Originals', 0.00, 0,
         'audiobook,audible-original,podcast,plus-catalog',
         {'Length': '3 hr 12 min', 'Plus Catalog': 'Included with membership'}),
    ],

    # ---------------------- KINDLE (ebooks) --------------------------------
    'kindle': [
        # Bestseller fiction
        ('Penguin Random House', '{sku} of Tides — A Novel (Kindle)', 'Fiction', 14.99, 35,
         'kindle,ebook,fiction,bestseller',
         {'Format': 'Kindle', 'File Size': '2.4 MB', 'Print Length': '384 pages'}),
        ('Random House', 'The {sku} Atlas (Kindle)', 'Fiction', 13.99, 32,
         'kindle,ebook,literary-fiction',
         {'Format': 'Kindle', 'File Size': '3.1 MB', 'Print Length': '432 pages'}),
        ('HarperCollins', '{sku} Hollow — A Novel (Kindle)', 'Fiction', 12.99, 30,
         'kindle,ebook,fiction',
         {'Format': 'Kindle', 'File Size': '2.7 MB', 'Print Length': '352 pages'}),
        # Mystery / Thriller
        ('Putnam', 'The {sku} Witness (Kindle)', 'Mystery', 14.99, 32,
         'kindle,ebook,thriller,bestseller',
         {'Format': 'Kindle', 'File Size': '2.2 MB', 'Print Length': '400 pages'}),
        ('Minotaur', '{sku} River — A Detective Holt Novel', 'Mystery', 13.99, 30,
         'kindle,ebook,mystery,series',
         {'Format': 'Kindle', 'File Size': '2.5 MB', 'Print Length': '368 pages'}),
        # SF / Fantasy
        ('Tor', 'Tide of {sku} — Helix Cycle Book 1 (Kindle)', 'SciFi & Fantasy', 11.99, 35,
         'kindle,ebook,scifi',
         {'Format': 'Kindle', 'File Size': '4.1 MB', 'Print Length': '624 pages'}),
        ('Tor', 'Emberhold {sku} — Dragonbound Book 1 (Kindle)', 'SciFi & Fantasy', 11.99, 35,
         'kindle,ebook,fantasy',
         {'Format': 'Kindle', 'File Size': '4.8 MB', 'Print Length': '760 pages'}),
        # Self-Help / Business
        ('Portfolio', 'Deep Focus {sku} — Reclaiming Attention (Kindle)', 'Self-Help', 13.99, 30,
         'kindle,ebook,productivity,non-fiction',
         {'Format': 'Kindle', 'File Size': '1.6 MB', 'Print Length': '256 pages'}),
        ('HarperBusiness', 'The {sku} Effect (Kindle)', 'Self-Help', 12.99, 30,
         'kindle,ebook,habits',
         {'Format': 'Kindle', 'File Size': '1.4 MB', 'Print Length': '224 pages'}),
        ('Crown Business', 'Negotiator {sku} — Practical Negotiation', 'Business', 14.99, 30,
         'kindle,ebook,business',
         {'Format': 'Kindle', 'File Size': '1.5 MB', 'Print Length': '288 pages'}),
        # History / Biography
        ('Knopf', 'Lincoln\'s {sku} — The 1864 Election (Kindle)', 'History', 15.99, 32,
         'kindle,ebook,history,civil-war',
         {'Format': 'Kindle', 'File Size': '4.6 MB', 'Print Length': '512 pages'}),
        ('Bloomsbury', 'Mary {sku} — A Life on Fire (Kindle)', 'Biography', 14.99, 30,
         'kindle,ebook,biography',
         {'Format': 'Kindle', 'File Size': '3.8 MB', 'Print Length': '480 pages'}),
        # Science
        ('Norton', '{sku} Patterns — The Hidden Math of Everything', 'Science', 12.99, 30,
         'kindle,ebook,science,popular-math',
         {'Format': 'Kindle', 'File Size': '2.1 MB', 'Print Length': '320 pages'}),
        ('Hachette', 'Deep Time {sku} — 4 Billion Years (Kindle)', 'Science', 13.99, 30,
         'kindle,ebook,geology',
         {'Format': 'Kindle', 'File Size': '5.2 MB', 'Print Length': '416 pages'}),
        # Programming / Technical
        ('O\'Reilly', 'Learning {sku} 2nd Edition (Kindle)', 'Programming', 49.99, 25,
         'kindle,ebook,programming,oreilly',
         {'Format': 'Kindle', 'File Size': '12.4 MB', 'Print Length': '512 pages'}),
        ('Manning', '{sku} in Action — Practical Guide (Kindle)', 'Programming', 39.99, 25,
         'kindle,ebook,programming,manning',
         {'Format': 'Kindle', 'File Size': '14.1 MB', 'Print Length': '480 pages'}),
        ('No Starch Press', 'Practical {sku} for Engineers (Kindle)', 'Programming', 34.99, 25,
         'kindle,ebook,programming,no-starch',
         {'Format': 'Kindle', 'File Size': '8.6 MB', 'Print Length': '352 pages'}),
        # Kindle Unlimited / Indie
        ('Kindle Direct', 'Tidewater {sku} — Indie Romance (KU)', 'Romance', 4.99, 0,
         'kindle,ebook,kindle-unlimited,romance,indie',
         {'Format': 'Kindle', 'File Size': '1.2 MB', 'Print Length': '352 pages',
          'Kindle Unlimited': 'Included'}),
        ('Kindle Direct', '{sku} Path — Cozy Mystery (KU)', 'Mystery', 4.99, 0,
         'kindle,ebook,kindle-unlimited,cozy-mystery',
         {'Format': 'Kindle', 'File Size': '1.1 MB', 'Print Length': '280 pages',
          'Kindle Unlimited': 'Included'}),
        ('Kindle Direct', 'Crowned {sku} — Romantasy (KU)', 'Romance', 4.99, 0,
         'kindle,ebook,kindle-unlimited,romantasy',
         {'Format': 'Kindle', 'File Size': '1.4 MB', 'Print Length': '416 pages',
          'Kindle Unlimited': 'Included'}),
        # Cookbook
        ('Clarkson Potter', 'The {sku} Pantry Cookbook (Kindle)', 'Cookbook', 19.99, 30,
         'kindle,ebook,cookbook',
         {'Format': 'Kindle', 'File Size': '36.4 MB', 'Print Length': '320 pages'}),
        # Travel / Reference
        ('Lonely Planet', '{sku} Italy 13th Edition (Kindle)', 'Travel', 18.99, 30,
         'kindle,ebook,travel,guidebook',
         {'Format': 'Kindle', 'File Size': '52.1 MB', 'Print Length': '912 pages'}),
        # YA
        ('Penguin Teen', '{sku} of Bone and Tide — YA Fantasy', 'Young Adult', 9.99, 30,
         'kindle,ebook,ya,fantasy',
         {'Format': 'Kindle', 'File Size': '2.8 MB', 'Print Length': '432 pages'}),
        # Children / Picture
        ('Scholastic', 'Adventures of {sku} the Knight (Kindle Kids)', 'Children', 6.99, 30,
         'kindle,ebook,kids,early-reader',
         {'Format': 'Kindle', 'File Size': '14.2 MB', 'Print Length': '48 pages'}),
        # Manga / Comics
        ('VIZ Media', '{sku} Hunter Volume 1 (Manga, Kindle)', 'Comics', 9.99, 28,
         'kindle,ebook,manga',
         {'Format': 'Kindle', 'File Size': '120 MB', 'Print Length': '200 pages',
          'Color': 'Black & white'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry — call from seed_extras.run_extras AFTER seed_r6.
# ---------------------------------------------------------------------------

def seed_r7(db, Product):
    """R7 polish: push catalog from ~21.1k to 30000+. Idempotent."""
    if Product.query.count() >= 29500:
        return 0
    added = 0

    # 1) Replay every prior template pool (SKU + R4 + R5 + R6) with
    #    R7_SUFFIXES — each fresh suffix unlocks a new slug.
    combined = []
    for cat, tpls in SKU_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R4_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R5_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R6_NEW_TEMPLATES.items():
        combined.append((cat, tpls))

    for category, templates in combined:
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(20):
                # 9 is co-prime with 32 → max suffix coverage per template.
                sfx_idx = (t_idx * 9 + variant_idx) % len(R7_SUFFIXES)
                idx = sfx_idx + 50000 + variant_idx * 67 + t_idx * 29
                data = _build_r7_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) R7-only templates × 30 variants — grocery / audible / kindle.
    for category, templates in R7_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(30):
                sfx_idx = (t_idx * 7 + variant_idx) % len(R7_SUFFIXES)
                idx = sfx_idx + 60000 + variant_idx * 53 + t_idx * 31
                data = _build_r7_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    return added


# ---------------------------------------------------------------------------
# Builder — extends R6 quality fields with R7 storefront-specific specs.
# ---------------------------------------------------------------------------

def _build_r7_sku(idx, template, category, pool, sfx_idx):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R7_SUFFIXES[sfx_idx % len(R7_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    # Audible-Plus / Kindle-Unlimited templates ship with base_price=0; keep
    # them free in the catalog instead of jittering into a negative.
    if base_price <= 0:
        price = 0.0
        list_price = 0.0
    else:
        jitter = -0.10 + ((idx * 53) % 21) / 100.0
        price = round(base_price * (1 + jitter), 2)
        list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.8 + ((idx * 37) % 110) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 50 + (idx * 197) % 27000
    color = COLOR_NAMES[idx % len(COLOR_NAMES)]
    specs = dict(specs_tpl)
    specs['Brand'] = brand
    if category in ('grocery', 'audible', 'kindle'):
        # New storefronts don't need a "Color" face — but the search filter UI
        # still relies on variant_options.color; supply a benign "Default".
        specs.setdefault('Variant', 'Standard')
    else:
        specs['Color'] = color

    variants = {}
    if category in ('grocery', 'audible', 'kindle'):
        # Provide a single "Standard" face so add-to-cart works without
        # forcing a variant pick (the templates render the dropdown unhidden
        # only when len(colors) > 1).
        variants['format'] = ['Standard']
    else:
        variants['color'] = [color,
                             COLOR_NAMES[(idx + 3) % len(COLOR_NAMES)],
                             COLOR_NAMES[(idx + 11) % len(COLOR_NAMES)]]
        if category == 'fashion' and subcat in ('Mens Clothing', 'Womens Clothing'):
            variants['size'] = SIZE_VALUES
        elif category == 'fashion' and subcat == 'Shoes':
            variants['size'] = SHOE_SIZES

    img = pool[idx % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 23) % len(pool)] for j in range(8)] if pool else []

    # --- R5/R6 quality fields (deterministic) ---
    is_climate_pledge = ((idx + sfx_idx) % 4 == 0)
    is_recyclable_pkg = ((idx * 3 + sfx_idx) % 10 < 3)
    made_in = MADE_IN_BUCKETS[(idx + sfx_idx * 3) % len(MADE_IN_BUCKETS)]
    is_one_day_eligible = ((idx * 7 + sfx_idx * 5) % 100 < 22)
    is_small_business = ((idx * 11 + sfx_idx * 7) % 100 < 12)
    is_sns = (
        (category in SNS_CATEGORIES or category == 'grocery')
        and ((idx + sfx_idx) % 3 == 0)
    )
    age_tag = None
    if category == 'toys':
        age_tag = AGE_BUCKETS[(idx + sfx_idx) % len(AGE_BUCKETS)]
    elif subcat in ('Educational', 'Plush', 'Building Sets', 'Children'):
        age_tag = AGE_BUCKETS[(idx + sfx_idx + 1) % len(AGE_BUCKETS)]

    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
    if category not in ('grocery', 'audible', 'kindle'):
        tags.append(color.lower().replace(' ', '-'))
    if is_climate_pledge:
        tags.append('climate-pledge-friendly')
    if is_recyclable_pkg:
        tags.append('recyclable-packaging')
    tags.append(made_in)
    if is_one_day_eligible:
        tags.append('one-day-shipping-eligible')
    if is_small_business:
        tags.append('small-business')
    if is_sns:
        tags.append('subscribe-and-save')
    if age_tag:
        tags.append(age_tag)

    # R7 storefront-specific tags
    if category == 'grocery':
        # Each grocery SKU gets 1-2 dietary tags deterministically.
        primary = DIETARY_TAGS[(idx + sfx_idx) % len(DIETARY_TAGS)]
        tags.append(primary)
        if (idx * 13 + sfx_idx) % 3 == 0:
            tags.append(DIETARY_TAGS[(idx + sfx_idx + 3) % len(DIETARY_TAGS)])
        # Whole Foods sub-flag for filterability.
        if '365' in brand or 'Whole Foods' in brand:
            tags.append('whole-foods-market')
        else:
            tags.append('amazon-fresh')
    elif category == 'audible':
        # Audible Plus catalog tag stays when free-base-price templates fire.
        if base_price <= 0:
            tags.append('audible-plus-included')
        else:
            tags.append('audible-credit-eligible')
    elif category == 'kindle':
        if 'kindle-unlimited' not in tags:
            tags.append('kindle-purchase')
        # X-ray + whispersync are pseudo-fixed on Kindle store rows.
        tags.append('x-ray-enabled')
        if (idx + sfx_idx) % 2 == 0:
            tags.append('whispersync-for-voice')

    # R7: stock-state distribution (same shape as R6 but slightly different
    # seed coefficients so we don't collide with R6 SKU stocks).
    stock_seed = (idx * 31 + sfx_idx * 17) % 100
    if category in ('audible', 'kindle'):
        # Digital goods — never out of stock, never low.
        stock = 999
    elif stock_seed < 6:
        stock = 0
        tags.append('notify-when-back')
    elif stock_seed < 18:
        stock = 1 + ((idx * 19 + sfx_idx * 7) % 4)
        tags.append('low-stock')
    else:
        stock = 15 + (idx * 23 + int(rating * 10)) % 380

    # --- specs additions for product detail readability ---
    specs['Climate Pledge Friendly'] = 'Yes' if is_climate_pledge else 'No'
    specs['Recyclable Packaging'] = 'Yes' if is_recyclable_pkg else 'No'
    made_in_display = {
        'made-in-usa': 'United States', 'made-in-germany': 'Germany',
        'made-in-japan': 'Japan', 'made-in-italy': 'Italy',
        'made-in-vietnam': 'Vietnam', 'made-in-china': 'China',
        'made-in-mexico': 'Mexico',
    }.get(made_in, 'Imported')
    specs['Country of Origin'] = made_in_display
    if is_one_day_eligible:
        specs['One-Day Shipping'] = 'Eligible'
    if is_sns:
        specs['Subscribe & Save'] = 'Available (up to 15% off)'
    if age_tag:
        specs['Age Range'] = age_tag.replace('age-', '').replace('-', '–') + ' years'

    description = (
        f"{name} by {brand}. {subcat} engineered for everyday performance. "
        + " ".join(f"{k}: {v}." for k, v in specs.items()
                   if k not in ('Brand', 'Color', 'Variant'))
    )
    features = [f"{k}: {v}" for k, v in list(specs.items())[:7]]
    if is_climate_pledge:
        features.append('Climate Pledge Friendly — certified sustainability')
    if is_one_day_eligible:
        features.append('Eligible for FREE One-Day Shipping')
    if is_sns:
        features.append('Subscribe & Save — up to 15% off recurring orders')
    if category == 'grocery':
        # Surface dietary tags inside features (visible on product page).
        d_features = [t for t in tags if t in DIETARY_TAGS]
        if d_features:
            features.append('Dietary: ' + ', '.join(d_features))
    if category == 'audible':
        features.append(f"Narrator: {specs.get('Narrator', 'Various')}")
        features.append(f"Listening Length: {specs.get('Length', 'Various')}")
    if category == 'kindle':
        features.append(f"Print Length: {specs.get('Print Length', 'N/A')}")
        if 'kindle-unlimited' in tags:
            features.append('Available with Kindle Unlimited subscription')

    is_deal = (idx % 5 == 0)
    is_bestseller = (reviews > 15000)
    is_featured = (idx % 17 == 0)
    return dict(
        name=name, brand=brand, category_slug=category, subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants=variants, stock=stock,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='',
    )
