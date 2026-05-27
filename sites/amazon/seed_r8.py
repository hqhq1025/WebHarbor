#!/usr/bin/env python3
"""R8 polish pass — push catalog from ~31.2k to 40000+.

What this adds on top of R7 (seed_r7.py):

  • R8_NEW_TEMPLATES — Amazon Fashion (luxury / streetwear / athleisure
    cross-brand) + Beauty (clean / luxury / mass-market cross-brand)
    templates that did not exist in any prior round.
  • R8_SUFFIXES — 36 fresh codenames (no overlap with R2/R4/R5/R6/R7).
  • Replays SKU_TEMPLATES / R4 / R5 / R6 / R7 template pools with R8_SUFFIXES.
  • Adds R8 quality fields on top of R7:
        - fit-type (slim / regular / relaxed / oversized) on fashion
        - skin-type (oily / dry / combo / sensitive) on beauty
        - cruelty-free / vegan-formula on beauty
        - business-prime-eligible flag (carries B2B pricing tier)

Deterministic: every numeric / boolean derived from idx + sfx_idx, so
rebuilds stay byte-identical. No datetime.now() / random without seed.

Idempotent — exits early when Product.count() already >= 39500 (R8 floor).
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
from seed_r7 import R7_TEMPLATES, DIETARY_TAGS


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Distinct codename pool — no overlap with R2 / R4 / R5 / R6 / R7 suffix lists.
R8_SUFFIXES = [
    'Atlas', 'Beacon', 'Cipher', 'Delta', 'Echo', 'Falcon',
    'Granite', 'Helix', 'Iridium', 'Juniper', 'Kestrel', 'Lumen',
    'Mosaic', 'Nimbus', 'Obsidian', 'Pinnacle', 'Quill', 'Rampart',
    'Spectra', 'Talisman', 'Umbra', 'Verdant', 'Wreath', 'Xanthium',
    'Yonder', 'Zephyrine', 'Alabaster', 'Bramble', 'Coralia', 'Domino',
    'Everglow', 'Fathom', 'Grove', 'Halcyon', 'Indigo', 'Juno',
]


# Fashion fit / Beauty skin-type buckets — R8-only quality fields.
FIT_TYPES = ['slim-fit', 'regular-fit', 'relaxed-fit', 'oversized-fit', 'tailored-fit']
SKIN_TYPES = ['skin-oily', 'skin-dry', 'skin-combination', 'skin-sensitive', 'skin-normal']


# ---------------------------------------------------------------------------
# R8-only templates — Fashion (luxury + streetwear + athleisure) + Beauty
# (clean + luxury + mass-market). Shape matches _build_generic_sku:
#   (brand, name_tpl_with_{sku}, subcategory, base_price, list_uplift_pct,
#    tag_csv, specs_template)
# ---------------------------------------------------------------------------

R8_NEW_TEMPLATES = {
    # ---------------------- FASHION (cross-brand) ----------------------
    'fashion': [
        # Luxury / Designer
        ('Ralph Lauren', 'Polo Bear Cable-Knit Cardigan {sku}', 'Mens Clothing', 245.00, 35,
         'fashion,sweater,knit,luxury,designer',
         {'Material': '100% Cotton', 'Care': 'Hand Wash', 'Origin': 'Peru'}),
        ('Burberry', 'Vintage Check Cashmere Scarf {sku}', 'Mens Clothing', 480.00, 28,
         'fashion,scarf,cashmere,luxury,designer',
         {'Material': '100% Cashmere', 'Dimensions': '168 x 30 cm', 'Origin': 'Scotland'}),
        ('Versace', 'Medusa Silk Tie {sku} — Pure Silk', 'Mens Clothing', 195.00, 30,
         'fashion,tie,silk,luxury,designer',
         {'Material': '100% Silk', 'Width': '8 cm', 'Origin': 'Italy'}),
        ('Coach', 'Tabby Shoulder Bag 26 {sku} — Pebble Leather', 'Womens Clothing', 395.00, 32,
         'fashion,handbag,leather,luxury,designer',
         {'Material': 'Pebble Leather', 'Hardware': 'Brass', 'Origin': 'Vietnam'}),
        ('Michael Kors', 'Jet Set Travel Wallet {sku} — Saffiano', 'Womens Clothing', 158.00, 40,
         'fashion,wallet,leather,designer',
         {'Material': 'Saffiano Leather', 'Card Slots': '8', 'Origin': 'China'}),
        # Streetwear
        ('Stussy', 'Basic Logo Hoodie {sku} — Heavyweight Fleece', 'Mens Clothing', 110.00, 25,
         'fashion,hoodie,streetwear,heavyweight',
         {'Material': '80% Cotton / 20% Polyester', 'Weight': '420 gsm'}),
        ('Supreme', 'Box Logo Tee {sku} — SS Drop', 'Mens Clothing', 64.00, 30,
         'fashion,tshirt,streetwear,limited',
         {'Material': '100% Cotton', 'Fit': 'Regular', 'Country': 'USA'}),
        ('BAPE', 'Shark Full Zip Hoodie {sku} — Camo', 'Mens Clothing', 385.00, 18,
         'fashion,hoodie,streetwear,limited',
         {'Material': '100% Cotton French Terry', 'Origin': 'Japan'}),
        ('Carhartt WIP', 'Detroit Jacket {sku} — Dearborn Canvas', 'Mens Clothing', 178.00, 24,
         'fashion,jacket,workwear,streetwear',
         {'Material': '12oz Canvas', 'Lining': 'Quilted', 'Origin': 'Mexico'}),
        ('Palace', 'Tri-Ferg Crewneck {sku} — Heavy Cotton', 'Mens Clothing', 145.00, 22,
         'fashion,sweatshirt,streetwear,limited',
         {'Material': '100% Cotton', 'Fit': 'Boxy', 'Origin': 'Portugal'}),
        # Athleisure
        ('Lululemon', 'Align High-Rise Pant 25" {sku} — Nulu', 'Womens Clothing', 98.00, 20,
         'fashion,leggings,athleisure,yoga',
         {'Material': 'Nulu Fabric', 'Rise': 'High', 'Inseam': '25"'}),
        ('Alo Yoga', '7/8 High-Waist Airbrush Legging {sku}', 'Womens Clothing', 88.00, 22,
         'fashion,leggings,athleisure',
         {'Material': '88% Nylon / 12% Spandex', 'Rise': 'High-Waist'}),
        ('Vuori', 'Sunday Performance Jogger {sku} — DreamKnit', 'Mens Clothing', 89.00, 18,
         'fashion,joggers,athleisure',
         {'Material': 'DreamKnit', 'Fit': 'Relaxed', 'Pockets': '4'}),
        ('Outdoor Voices', 'Exercise Dress {sku} — 7" RecTrek', 'Womens Clothing', 100.00, 25,
         'fashion,dress,athleisure',
         {'Material': 'RecTrek Fabric', 'Built-in Shorts': 'Yes'}),
        # Shoes / Sneakers — cross-brand
        ('Nike', 'Dunk Low Retro {sku} — Premium', 'Shoes', 115.00, 25,
         'fashion,sneakers,athletic',
         {'Upper': 'Leather', 'Sole': 'Rubber', 'Style': 'Low-top'}),
        ('Adidas', 'Samba OG {sku} — Cloud White', 'Shoes', 100.00, 22,
         'fashion,sneakers,classic',
         {'Upper': 'Leather', 'Sole': 'Gum Rubber', 'Style': 'Low-top'}),
        ('New Balance', '2002R {sku} — Protection Pack', 'Shoes', 150.00, 18,
         'fashion,sneakers,lifestyle',
         {'Upper': 'Mesh / Suede', 'Cushioning': 'N-ergy', 'Made in': 'Vietnam'}),
        ('Hoka', 'Clifton 9 {sku} — Neutral Trainer', 'Shoes', 145.00, 14,
         'fashion,sneakers,running',
         {'Drop': '5mm', 'Cushioning': 'EVA Foam', 'Weight': '8.7 oz'}),
        ('On', 'Cloud 5 {sku} — Swiss Engineered', 'Shoes', 140.00, 15,
         'fashion,sneakers,running',
         {'Sole': 'CloudTec', 'Upper': 'Engineered Mesh'}),
        # Bags / Accessories
        ('Herschel', 'Little America Backpack {sku} — Classic', 'Mens Clothing', 110.00, 25,
         'fashion,backpack,accessory',
         {'Capacity': '25L', 'Laptop Sleeve': '15"', 'Material': '600D Polyester'}),
        ('Patagonia', 'Black Hole Duffel 55L {sku}', 'Mens Clothing', 159.00, 20,
         'fashion,duffel,outdoor,accessory',
         {'Capacity': '55L', 'Material': '100% Recycled Polyester'}),
        ('Fjallraven', 'Kanken Classic {sku} — 16L', 'Womens Clothing', 90.00, 22,
         'fashion,backpack,accessory',
         {'Capacity': '16L', 'Material': 'Vinylon F'}),
    ],
    # ---------------------- BEAUTY (cross-brand) ----------------------
    'beauty': [
        # Clean / Natural
        ('Drunk Elephant', 'C-Firma Fresh Day Serum {sku} 1 fl oz', 'Skincare', 80.00, 25,
         'beauty,skincare,serum,clean-beauty',
         {'Volume': '1 fl oz', 'Vitamin C': '15%', 'Free of': 'Essential oils, silicones'}),
        ('Glow Recipe', 'Watermelon Glow Niacinamide Dew Drops {sku}', 'Skincare', 35.00, 30,
         'beauty,skincare,serum,clean-beauty',
         {'Volume': '1.35 fl oz', 'Key Ingredient': 'Niacinamide 4%'}),
        ('Youth To The People', 'Superfood Cleanser {sku} 8 fl oz', 'Skincare', 36.00, 28,
         'beauty,skincare,cleanser,clean-beauty,vegan',
         {'Volume': '8 fl oz', 'pH': '5.5', 'Vegan': 'Yes'}),
        ('Tata Harper', 'Resurfacing Mask {sku} 30ml — Natural', 'Skincare', 65.00, 22,
         'beauty,skincare,mask,clean-beauty,luxury',
         {'Volume': '30ml', 'Natural Ingredients': '100%'}),
        ('Tower 28', 'SOS Daily Rescue Facial Spray {sku}', 'Skincare', 28.00, 28,
         'beauty,skincare,toner,clean-beauty,sensitive',
         {'Volume': '4 fl oz', 'Active': 'Hypochlorous Acid'}),
        # Luxury
        ('La Mer', 'Crème de la Mer Moisturizing Cream {sku} 1 oz', 'Skincare', 200.00, 18,
         'beauty,skincare,moisturizer,luxury',
         {'Volume': '1 oz', 'Signature': 'Miracle Broth'}),
        ('Sisley Paris', 'Black Rose Cream Mask {sku} 60ml', 'Skincare', 165.00, 20,
         'beauty,skincare,mask,luxury,french',
         {'Volume': '60ml', 'Origin': 'France'}),
        ('SK-II', 'Facial Treatment Essence {sku} 230ml', 'Skincare', 199.00, 22,
         'beauty,skincare,essence,luxury,japanese',
         {'Volume': '230ml', 'Pitera': '90%'}),
        ('Chanel', 'Sublimage La Crème {sku} 50g — Texture Suprême', 'Skincare', 460.00, 14,
         'beauty,skincare,moisturizer,luxury,french',
         {'Volume': '50g', 'Origin': 'France'}),
        ('Tom Ford', 'Black Orchid Eau de Parfum {sku} 50ml', 'Skincare', 145.00, 25,
         'beauty,fragrance,perfume,luxury',
         {'Volume': '50ml', 'Family': 'Oriental / Floral'}),
        # Mass-market / Drugstore
        ('CeraVe', 'Moisturizing Cream {sku} 19 oz Tub', 'Skincare', 17.99, 35,
         'beauty,skincare,moisturizer,drugstore,dermatologist',
         {'Volume': '19 oz', 'Ceramides': '3 essential'}),
        ('The Ordinary', 'Niacinamide 10% + Zinc 1% {sku}', 'Skincare', 6.50, 40,
         'beauty,skincare,serum,affordable',
         {'Volume': '30ml', 'pH': '5.0-6.0'}),
        ('Neutrogena', 'Hydro Boost Water Gel {sku} 1.7 oz', 'Skincare', 19.99, 30,
         'beauty,skincare,moisturizer,drugstore',
         {'Volume': '1.7 oz', 'Hyaluronic Acid': 'Yes'}),
        ('Cetaphil', 'Daily Facial Cleanser {sku} 16 oz', 'Skincare', 13.99, 30,
         'beauty,skincare,cleanser,drugstore,sensitive',
         {'Volume': '16 oz', 'Soap-Free': 'Yes'}),
        ('Olay', 'Regenerist Micro-Sculpting Cream {sku} 1.7 oz', 'Skincare', 28.99, 32,
         'beauty,skincare,moisturizer,drugstore',
         {'Volume': '1.7 oz', 'Niacinamide': 'Yes'}),
        # Makeup — cross-brand
        ('Charlotte Tilbury', 'Pillow Talk Lipstick {sku} — Original', 'Makeup', 38.00, 25,
         'beauty,makeup,lipstick,luxury',
         {'Finish': 'Matte Revolution', 'Shade Family': 'Nude Pink'}),
        ('Rare Beauty', 'Soft Pinch Liquid Blush {sku} — Joy', 'Makeup', 23.00, 32,
         'beauty,makeup,blush,clean-beauty',
         {'Volume': '0.25 fl oz', 'Finish': 'Dewy'}),
        ('Fenty Beauty', 'Pro Filt’r Soft Matte Foundation {sku}', 'Makeup', 40.00, 25,
         'beauty,makeup,foundation,inclusive',
         {'Volume': '1.08 fl oz', 'Shades': '50'}),
        ('Glossier', 'Boy Brow {sku} — Brown', 'Makeup', 18.00, 30,
         'beauty,makeup,brow,minimalist',
         {'Volume': '3.1g', 'Finish': 'Matte Tint'}),
        ('Pat McGrath Labs', 'MatteTrance Lipstick {sku} — Elson 4', 'Makeup', 39.00, 25,
         'beauty,makeup,lipstick,luxury',
         {'Finish': 'Matte', 'Edition': 'MatteTrance'}),
        # Hair — cross-brand
        ('Olaplex', 'No.3 Hair Perfector {sku} 3.3 fl oz', 'Hair Care', 30.00, 35,
         'beauty,haircare,treatment',
         {'Volume': '3.3 fl oz', 'Bonds': 'Rebuilds'}),
        ('Briogeo', 'Don’t Despair Repair Mask {sku} 8 oz', 'Hair Care', 38.00, 28,
         'beauty,haircare,mask,clean-beauty',
         {'Volume': '8 oz', 'Free of': 'Sulfates, parabens'}),
        ('K18', 'Leave-In Molecular Repair Hair Mask {sku} 50ml', 'Hair Care', 75.00, 22,
         'beauty,haircare,mask',
         {'Volume': '50ml', 'Patent': 'K18Peptide'}),
        # Tools
        ('Dyson', 'Airwrap Multi-Styler Complete {sku}', 'Hair Care', 599.99, 12,
         'beauty,haircare,tools,luxury',
         {'Voltage': '120V', 'Attachments': '5'}),
        ('T3', 'AireLuxe Hair Dryer {sku} — IonAir', 'Hair Care', 199.99, 18,
         'beauty,haircare,tools',
         {'Wattage': '1800W', 'Ion': 'Yes'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry — call from seed_extras.run_extras AFTER seed_r7.
# ---------------------------------------------------------------------------

def seed_r8(db, Product):
    """R8 polish: push catalog from ~31.2k to 40000+. Idempotent."""
    if Product.query.count() >= 39500:
        return 0
    added = 0

    # 1) Replay every prior template pool (SKU + R4 + R5 + R6 + R7) with
    #    R8_SUFFIXES — each fresh suffix unlocks a new slug.
    combined = []
    for cat, tpls in SKU_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R4_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R5_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R6_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R7_TEMPLATES.items():
        combined.append((cat, tpls))

    for category, templates in combined:
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(18):
                # 11 is co-prime with 36 → max suffix coverage per template.
                sfx_idx = (t_idx * 11 + variant_idx) % len(R8_SUFFIXES)
                idx = sfx_idx + 70000 + variant_idx * 71 + t_idx * 37
                data = _build_r8_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) R8-only templates × 32 variants — Fashion + Beauty cross-brand
    #    long-tail SKUs.  Two passes because R8_NEW_TEMPLATES is the main
    #    delta vs prior rounds.
    for category, templates in R8_NEW_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(32):
                sfx_idx = (t_idx * 13 + variant_idx) % len(R8_SUFFIXES)
                idx = sfx_idx + 80000 + variant_idx * 59 + t_idx * 41
                data = _build_r8_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    return added


# ---------------------------------------------------------------------------
# Builder — extends R7 quality fields with R8 fit-type / skin-type /
# business-prime / cruelty-free / vegan-formula tags.
# ---------------------------------------------------------------------------

def _build_r8_sku(idx, template, category, pool, sfx_idx):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R8_SUFFIXES[sfx_idx % len(R8_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    if base_price <= 0:
        price = 0.0
        list_price = 0.0
    else:
        jitter = -0.10 + ((idx * 59) % 21) / 100.0
        price = round(base_price * (1 + jitter), 2)
        list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.8 + ((idx * 41) % 110) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 50 + (idx * 223) % 26000
    color = COLOR_NAMES[idx % len(COLOR_NAMES)]
    specs = dict(specs_tpl)
    specs['Color'] = color
    specs['Brand'] = brand

    variants = {'color': [color,
                          COLOR_NAMES[(idx + 5) % len(COLOR_NAMES)],
                          COLOR_NAMES[(idx + 13) % len(COLOR_NAMES)]]}
    if category == 'fashion' and subcat in ('Mens Clothing', 'Womens Clothing'):
        variants['size'] = SIZE_VALUES
    elif category == 'fashion' and subcat == 'Shoes':
        variants['size'] = SHOE_SIZES

    img = pool[idx % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 29) % len(pool)] for j in range(8)] if pool else []

    # --- R5/R6/R7 quality fields (deterministic from idx/sfx_idx) ---
    is_climate_pledge = ((idx + sfx_idx) % 4 == 0)
    is_recyclable_pkg = ((idx * 3 + sfx_idx) % 10 < 3)
    made_in = MADE_IN_BUCKETS[(idx + sfx_idx * 3) % len(MADE_IN_BUCKETS)]
    is_one_day_eligible = ((idx * 7 + sfx_idx * 5) % 100 < 22)
    is_small_business = ((idx * 11 + sfx_idx * 7) % 100 < 12)
    is_sns = category in SNS_CATEGORIES and ((idx + sfx_idx) % 3 == 0)
    age_tag = None
    if category == 'toys':
        age_tag = AGE_BUCKETS[(idx + sfx_idx) % len(AGE_BUCKETS)]
    elif subcat in ('Educational', 'Plush', 'Building Sets'):
        age_tag = AGE_BUCKETS[(idx + sfx_idx + 1) % len(AGE_BUCKETS)]

    # --- R8-only quality fields ---
    is_business_prime = ((idx * 19 + sfx_idx * 11) % 100 < 18)
    fit_type = None
    skin_type = None
    is_cruelty_free = False
    is_vegan_formula = False
    if category == 'fashion':
        fit_type = FIT_TYPES[(idx + sfx_idx) % len(FIT_TYPES)]
    if category == 'beauty':
        skin_type = SKIN_TYPES[(idx + sfx_idx) % len(SKIN_TYPES)]
        is_cruelty_free = ((idx * 17 + sfx_idx * 5) % 100 < 70)
        is_vegan_formula = ((idx * 23 + sfx_idx * 7) % 100 < 38)

    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
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
    # R8 tags
    if is_business_prime:
        tags.append('business-prime-eligible')
    if fit_type:
        tags.append(fit_type)
    if skin_type:
        tags.append(skin_type)
    if is_cruelty_free:
        tags.append('cruelty-free')
    if is_vegan_formula:
        tags.append('vegan-formula')

    # R7 storefront-specific tags (carry forward when replaying R7 pool)
    if category == 'grocery':
        primary = DIETARY_TAGS[(idx + sfx_idx) % len(DIETARY_TAGS)]
        tags.append(primary)
        if (idx * 13 + sfx_idx) % 3 == 0:
            tags.append(DIETARY_TAGS[(idx + sfx_idx + 3) % len(DIETARY_TAGS)])
        if '365' in brand or 'Whole Foods' in brand:
            tags.append('whole-foods-market')
        else:
            tags.append('amazon-fresh')
    elif category == 'audible':
        if base_price <= 0:
            tags.append('audible-plus-included')
        else:
            tags.append('audible-credit-eligible')
    elif category == 'kindle':
        if 'kindle-unlimited' not in tags:
            tags.append('kindle-purchase')
        tags.append('x-ray-enabled')
        if (idx + sfx_idx) % 2 == 0:
            tags.append('whispersync-for-voice')

    # R8: stock-state distribution (different seed coefficients vs R7)
    stock_seed = (idx * 37 + sfx_idx * 19) % 100
    if category in ('audible', 'kindle'):
        stock = 999
    elif stock_seed < 6:
        stock = 0
        tags.append('notify-when-back')
    elif stock_seed < 18:
        stock = 1 + ((idx * 21 + sfx_idx * 11) % 4)
        tags.append('low-stock')
    else:
        stock = 15 + (idx * 23 + int(rating * 10)) % 380

    # --- specs additions ---
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
    if is_business_prime:
        specs['Business Prime'] = 'Eligible (B2B pricing tier)'
    if fit_type:
        specs['Fit'] = fit_type.replace('-', ' ').title()
    if skin_type:
        specs['Skin Type'] = skin_type.replace('skin-', '').title()
    if is_cruelty_free:
        specs['Cruelty-Free'] = 'Yes (Leaping Bunny certified)'
    if is_vegan_formula:
        specs['Vegan Formula'] = 'Yes'

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
    if is_business_prime:
        features.append('Business Prime — bulk-pricing tier for verified buyers')
    if fit_type:
        features.append(f"Fit: {fit_type.replace('-', ' ').title()}")
    if skin_type:
        features.append(f"Skin Type: {skin_type.replace('skin-', '').title()}")
    if is_cruelty_free:
        features.append('Cruelty-Free — Leaping Bunny certified')
    if is_vegan_formula:
        features.append('100% Vegan formula')

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
