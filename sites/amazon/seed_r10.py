#!/usr/bin/env python3
"""R10 final-polish pass — push catalog from ~51.9k to 56000+.

What this adds on top of R9 (seed_r9.py):

  * R10_NEW_TEMPLATES — cross-business "bundle" SKUs that pair existing
    business lines together (Pharmacy + Pantry HSA-eligible kits,
    Amazon Auto VIN-fit packs, Amazon Renewed grade bundles, Amazon Custom
    monogram apparel, Made-by-Amazon basics, Seasonal / Holiday long-tail).
  * R10_SUFFIXES — 40 fresh codenames (no overlap with R2-R9).
  * Replays prior template pools (SKU + R4 + R5 + R6 + R7 + R8 + R9) with
    R10_SUFFIXES so the long-tail keeps growing.
  * R10 quality fields on top of R9:
        - bundle_kind  (hsa-care / vin-fit / refurb-pack / monogram-pack)
        - made_by_amazon flag
        - seasonal_band (spring-26 / summer-26 / fall-26 / winter-26)
        - holiday_gift_guide flag

Deterministic: every numeric / boolean derived from idx + sfx_idx, so
rebuilds stay byte-identical. No datetime.now() / random without seed.

Idempotent — exits early when Product.count() already >= 55500 (R10 floor).
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
from seed_r8 import R8_NEW_TEMPLATES, FIT_TYPES, SKIN_TYPES
from seed_r9 import (
    R9_NEW_TEMPLATES, RENEWED_GRADES, FREETIME_BANDS, VEHICLE_FITMENT,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Distinct codename pool — no overlap with R2 / R4 / R5 / R6 / R7 / R8 / R9.
R10_SUFFIXES = [
    'Aerie', 'Brook', 'Cedar', 'Dawn', 'Echo10', 'Fable',
    'Grove', 'Halcyon', 'Iris', 'Juniper', 'Kestrel', 'Loom',
    'Meadow', 'Nimbus10', 'Orchard', 'Petal', 'Quill', 'Rowan',
    'Sage', 'Thistle', 'Umbra', 'Vesper', 'Willow', 'Xander',
    'Yew', 'Zephyr10', 'Almanac', 'Bridge', 'Caravan', 'Drift10',
    'Estuary', 'Fern', 'Gable', 'Harvest', 'Inlet', 'Jubilee',
    'Karst', 'Lantern', 'Mistral', 'Nectar',
]


# R10-only quality buckets.
BUNDLE_KINDS = ['hsa-care', 'vin-fit', 'refurb-pack', 'monogram-pack',
                'made-by-amazon', 'seasonal-bundle']
SEASONAL_BANDS = ['spring-26', 'summer-26', 'fall-26', 'winter-26']


# ---------------------------------------------------------------------------
# R10-only templates. Shape matches _build_generic_sku:
#   (brand, name_tpl_with_{sku}, subcategory, base_price, list_uplift_pct,
#    tag_csv, specs_template)
# ---------------------------------------------------------------------------

R10_NEW_TEMPLATES = {
    # ---------------------- BUNDLES (cross-business) ----------------------
    'bundles': [
        # HSA-eligible care kits (Pharmacy + Pantry)
        ('Amazon Pharmacy', 'HSA-Eligible Cold & Flu Care Kit {sku}', 'Care Kits', 38.99, 25,
         'bundle,hsa-care,pharmacy,pantry,otc,subscribe-and-save',
         {'Items': '6', 'HSA Eligible': 'Yes', 'Includes': 'Acetaminophen, Decongestant, Electrolyte mix, Tissues, Throat lozenges, Thermometer'}),
        ('Amazon Pharmacy', 'HSA-Eligible Allergy Relief Bundle {sku}', 'Care Kits', 32.50, 30,
         'bundle,hsa-care,allergy,pharmacy,subscribe-and-save',
         {'Items': '4', 'HSA Eligible': 'Yes', 'Includes': 'Cetirizine 10mg, Saline nasal spray, Eye drops, HEPA dust mask'}),
        ('Amazon Pharmacy', 'HSA-Eligible First Aid Refresh Pack {sku}', 'Care Kits', 24.75, 28,
         'bundle,hsa-care,first-aid,pharmacy',
         {'Items': '7', 'HSA Eligible': 'Yes', 'Includes': 'Bandages, Antiseptic wipes, Antibiotic ointment, Gauze, Tape, Scissors, Gloves'}),
        ('Amazon Pharmacy', 'HSA-Eligible Diabetes Daily Kit {sku}', 'Care Kits', 56.00, 22,
         'bundle,hsa-care,diabetes,pharmacy,subscribe-and-save',
         {'Items': '5', 'HSA Eligible': 'Yes', 'Includes': 'Glucose meter strips, Lancets, Alcohol swabs, Glucose tablets, Carrying case'}),
        ('Amazon Pharmacy', 'HSA-Eligible Heart-Health Starter {sku}', 'Care Kits', 44.25, 27,
         'bundle,hsa-care,heart,pharmacy,subscribe-and-save',
         {'Items': '4', 'HSA Eligible': 'Yes', 'Includes': 'Wrist BP monitor, Aspirin 81mg, CoQ10 supplement, Daily-log notebook'}),
        # Auto VIN-fit packs (Auto + Pantry-style consumables)
        ('Amazon Auto', 'Synthetic Oil Change Pack {sku} — Fits 4-cyl Sedan', 'Maintenance Kits', 49.99, 18,
         'bundle,vin-fit,auto,oil-change,prime,fits-sedan',
         {'Includes': '5qt 5W-30 synthetic, OEM-spec filter, Drain plug gasket', 'Vehicle Fitment': 'Sedan', 'Mileage Interval': '7,500 mi'}),
        ('Amazon Auto', 'Synthetic Oil Change Pack {sku} — Fits SUV/Truck', 'Maintenance Kits', 64.99, 18,
         'bundle,vin-fit,auto,oil-change,prime,fits-suv',
         {'Includes': '6qt 5W-30 synthetic, OEM-spec filter, Drain plug gasket', 'Vehicle Fitment': 'SUV', 'Mileage Interval': '7,500 mi'}),
        ('Amazon Auto', 'Brake Service Pack {sku} — Front Pads + Rotors', 'Maintenance Kits', 159.00, 24,
         'bundle,vin-fit,auto,brakes,fits-sedan',
         {'Includes': 'Ceramic pads (2), Vented rotors (2), Caliper grease, Brake-fluid bottle', 'Vehicle Fitment': 'Sedan / Coupe'}),
        ('Amazon Auto', 'Wiper + Washer-Fluid Bundle {sku} — Sedan Fit', 'Maintenance Kits', 28.50, 22,
         'bundle,vin-fit,auto,wipers,fits-sedan',
         {'Includes': 'Driver/passenger beam blades, 1gal washer fluid, Cabin air freshener', 'Vehicle Fitment': 'Sedan'}),
        ('Amazon Auto', 'Detailing Kit {sku} — Interior + Exterior', 'Maintenance Kits', 42.00, 20,
         'bundle,auto,detailing,prime',
         {'Includes': 'Wax, Microfiber towels (6), Interior cleaner, Tire shine, Glass cleaner', 'Vehicle Fitment': 'Universal'}),
        # Renewed grade bundles (Renewed + Accessories + Warranty)
        ('Amazon Renewed', 'Refurbished Laptop Starter {sku} — Premium Grade', 'Refurb Bundles', 549.00, 30,
         'bundle,refurb-pack,renewed,renewed-premium,prime',
         {'Includes': '13-inch refurb laptop, Neoprene sleeve, USB-C hub, 90-day Renewed guarantee, 1-yr extended protection', 'Renewed Grade': 'Premium'}),
        ('Amazon Renewed', 'Refurbished Laptop Starter {sku} — Excellent Grade', 'Refurb Bundles', 449.00, 32,
         'bundle,refurb-pack,renewed,renewed-excellent,prime',
         {'Includes': '13-inch refurb laptop, Neoprene sleeve, USB-C hub, 90-day Renewed guarantee', 'Renewed Grade': 'Excellent'}),
        ('Amazon Renewed', 'Refurbished Phone Trade-In Pack {sku}', 'Refurb Bundles', 329.00, 28,
         'bundle,refurb-pack,renewed,trade-in,prime',
         {'Includes': 'Renewed unlocked phone, Tempered-glass screen protector, USB-C cable, 90-day guarantee', 'Renewed Grade': 'Good'}),
        ('Amazon Renewed', 'Refurbished Tablet Family Pack {sku}', 'Refurb Bundles', 219.00, 26,
         'bundle,refurb-pack,renewed,family,kids,freetime-6to8',
         {'Includes': '10-inch refurb tablet, Kid-proof case, 1-yr Kids+ subscription, 90-day Renewed guarantee', 'Renewed Grade': 'Excellent'}),
        ('Amazon Renewed', 'Refurbished Smart-Home Starter {sku}', 'Refurb Bundles', 119.00, 33,
         'bundle,refurb-pack,renewed,smart-home,prime',
         {'Includes': 'Renewed Echo speaker, Renewed smart plug (2-pack), Setup guide, 90-day guarantee', 'Renewed Grade': 'Excellent'}),
    ],

    # ---------------------- AMAZON CUSTOM (monogram) ----------------------
    'amazon_custom': [
        ('Amazon Custom', 'Monogrammed Leather Wallet {sku}', 'Custom Accessories', 49.00, 35,
         'amazon-custom,monogram-pack,personalized,leather,gift',
         {'Personalization': 'Up to 3 initials', 'Material': 'Full-grain leather', 'Lead Time': '3-5 days'}),
        ('Amazon Custom', 'Engraved Cutting Board {sku}', 'Custom Home', 38.50, 30,
         'amazon-custom,monogram-pack,personalized,kitchen,gift,wedding',
         {'Personalization': 'Family name + est. year', 'Material': 'Acacia hardwood', 'Lead Time': '4-6 days'}),
        ('Amazon Custom', 'Custom Photo Mug {sku}', 'Custom Home', 16.99, 30,
         'amazon-custom,monogram-pack,personalized,kitchen,gift',
         {'Personalization': 'Photo upload + caption', 'Capacity': '11oz', 'Lead Time': '2-3 days'}),
        ('Amazon Custom', 'Personalized Dog Collar {sku}', 'Custom Pet', 22.00, 32,
         'amazon-custom,monogram-pack,personalized,pet,prime',
         {'Personalization': "Pet name + owner phone", 'Material': 'Nylon webbing', 'Lead Time': '3-4 days'}),
        ('Amazon Custom', 'Embroidered Bath Towel Set {sku}', 'Custom Home', 44.00, 28,
         'amazon-custom,monogram-pack,personalized,home,wedding,gift',
         {'Personalization': 'Single-letter monogram', 'Material': '100% cotton, 600 GSM', 'Lead Time': '5-7 days'}),
        ('Amazon Custom', 'Monogrammed Tote Bag {sku}', 'Custom Accessories', 24.99, 32,
         'amazon-custom,monogram-pack,personalized,gift,prime',
         {'Personalization': 'Up to 8 characters', 'Material': 'Canvas', 'Lead Time': '2-3 days'}),
    ],

    # ---------------------- MADE BY AMAZON (private label expansion) ----------------------
    'made_by_amazon': [
        ('Amazon Basics', 'Heavy-Duty Storage Bins {sku} — 4-Pack', 'Storage', 32.99, 25,
         'made-by-amazon,storage,home,prime,climate-pledge-friendly',
         {'Capacity': '60L each', 'Material': 'Polypropylene', 'Stackable': 'Yes'}),
        ('Amazon Basics', 'Microfiber Cleaning Cloths {sku} — 24-Pack', 'Cleaning', 12.99, 30,
         'made-by-amazon,cleaning,home,prime,subscribe-and-save',
         {'Count': '24', 'Size': '12x16 inch', 'Lint-Free': 'Yes'}),
        ('Amazon Basics', 'Stainless Steel Mixing Bowls {sku} — 5-Piece', 'Kitchen', 27.50, 28,
         'made-by-amazon,kitchen,home,prime',
         {'Pieces': '5', 'Material': '18/8 stainless', 'Dishwasher Safe': 'Yes'}),
        ('Amazon Basics', 'Cable Management Sleeve {sku} — 10ft', 'Home Office', 14.99, 35,
         'made-by-amazon,home-office,prime',
         {'Length': '10ft', 'Diameter': '0.7-1.4 inch', 'Material': 'Neoprene mesh'}),
        ('Amazon Basics', 'LED Desk Lamp {sku} — Dimmable', 'Home Office', 28.99, 32,
         'made-by-amazon,home-office,prime,climate-pledge-friendly',
         {'Brightness': '600 lumens', 'Color Temp': '3000K-6500K adjustable', 'USB Port': 'Yes'}),
        ('Amazon Basics', '3-Ring Binder {sku} — 1.5 inch', 'Office Supplies', 6.99, 30,
         'made-by-amazon,office,prime,small-business',
         {'Capacity': '375 sheets', 'View Cover': 'Yes', 'Color Options': 'Black / Navy / White'}),
        ('Amazon Basics', 'Whiteboard Markers {sku} — 12-Pack', 'Office Supplies', 9.99, 30,
         'made-by-amazon,office,prime,small-business',
         {'Count': '12', 'Tip': 'Chisel', 'Low Odor': 'Yes'}),
        ('Amazon Essentials', 'Mens Cotton Crewneck Tee {sku}', 'Apparel', 12.99, 38,
         'made-by-amazon,fashion,apparel,prime,fits-regular',
         {'Material': '100% cotton', 'Fit': 'Regular', 'Care': 'Machine wash'}),
        ('Amazon Essentials', 'Womens Slim Pull-On Pant {sku}', 'Apparel', 22.50, 35,
         'made-by-amazon,fashion,apparel,prime,fits-slim',
         {'Material': '95% rayon / 5% spandex', 'Fit': 'Slim', 'Inseam Options': '29 / 31 / 33'}),
        ('Amazon Aware', 'Carbon-Aware Hoodie {sku}', 'Apparel', 36.00, 30,
         'made-by-amazon,fashion,apparel,prime,climate-pledge-friendly,recyclable-packaging',
         {'Carbon Footprint': 'Verified', 'Material': '100% recycled cotton blend', 'Fit': 'Relaxed'}),
    ],

    # ---------------------- SEASONAL / HOLIDAY LONG-TAIL ----------------------
    'seasonal': [
        ('Amazon Holiday', 'Spring Garden Starter Kit {sku}', 'Seasonal', 34.99, 28,
         'seasonal-bundle,seasonal,spring-26,garden,prime',
         {'Includes': '12 seed packets, Trowel, Watering can, Gardening gloves', 'Season': 'Spring 2026'}),
        ('Amazon Holiday', 'Summer Patio Refresh {sku}', 'Seasonal', 89.99, 24,
         'seasonal-bundle,seasonal,summer-26,patio,prime',
         {'Includes': 'Solar string lights (50ft), Throw pillows (2), Citronella candles (3)', 'Season': 'Summer 2026'}),
        ('Amazon Holiday', 'Fall Cozy Bundle {sku}', 'Seasonal', 56.50, 25,
         'seasonal-bundle,seasonal,fall-26,home,prime',
         {'Includes': 'Plaid throw blanket, Pumpkin-spice candle (2), Knit pillow cover', 'Season': 'Fall 2026'}),
        ('Amazon Holiday', 'Winter Holiday Decor Pack {sku}', 'Seasonal', 78.00, 28,
         'seasonal-bundle,seasonal,winter-26,holiday-gift-guide,prime',
         {'Includes': 'String lights (200), Wreath, Tree topper, Stockings (4), Garland', 'Season': 'Winter 2026'}),
        ('Amazon Holiday', 'Holiday Gift Wrap Bundle {sku}', 'Seasonal', 22.99, 30,
         'seasonal-bundle,seasonal,winter-26,holiday-gift-guide,gift',
         {'Includes': 'Wrapping paper (4 rolls), Ribbons (8), Gift tags (24), Bows (12)', 'Season': 'Winter 2026'}),
        ('Amazon Holiday', 'Valentines Romance Kit {sku}', 'Seasonal', 48.00, 26,
         'seasonal-bundle,seasonal,winter-26,holiday-gift-guide,gift',
         {'Includes': 'Chocolates (24-piece), Rose-bouquet faux flowers, Candle, Card', 'Season': 'February 2026'}),
        ('Amazon Holiday', 'Back-to-School Essentials {sku}', 'Seasonal', 64.99, 27,
         'seasonal-bundle,seasonal,fall-26,school,prime,small-business',
         {'Includes': 'Notebook (4), Pencils (24), Sticky notes, Backpack-clip flashlight, Highlighters', 'Season': 'Late Summer 2026'}),
        ('Amazon Holiday', 'Mothers Day Pamper Set {sku}', 'Seasonal', 52.00, 28,
         'seasonal-bundle,seasonal,spring-26,holiday-gift-guide,gift',
         {'Includes': 'Bath bombs (6), Robe, Slippers, Candle, Card', 'Season': 'Spring 2026'}),
        ('Amazon Holiday', 'Fathers Day Grill Pack {sku}', 'Seasonal', 68.00, 25,
         'seasonal-bundle,seasonal,summer-26,holiday-gift-guide,gift',
         {'Includes': 'BBQ tools (4-piece), Grill brush, Steak seasoning rub, Apron', 'Season': 'Summer 2026'}),
    ],

    # ---------------------- AMAZON WAREHOUSE DEALS / FRUSTRATION-FREE ----------------------
    'warehouse_deals': [
        ('Amazon Warehouse', 'Open-Box Bluetooth Speaker {sku}', 'Warehouse Deals', 39.00, 35,
         'warehouse-deal,open-box,electronics,prime,renewed-acceptable',
         {'Condition': 'Open Box - Like New', 'Warehouse Inspection': 'Full', 'Warranty': '90-day Warehouse'}),
        ('Amazon Warehouse', 'Open-Box Coffee Maker {sku}', 'Warehouse Deals', 54.00, 32,
         'warehouse-deal,open-box,kitchen,renewed-good',
         {'Condition': 'Open Box - Used Like New', 'Warehouse Inspection': 'Full', 'Warranty': '90-day Warehouse'}),
        ('Amazon Warehouse', 'Open-Box Vacuum {sku}', 'Warehouse Deals', 119.00, 30,
         'warehouse-deal,open-box,home,renewed-excellent',
         {'Condition': 'Open Box - Excellent', 'Warehouse Inspection': 'Full', 'Warranty': '90-day Warehouse'}),
        ('Amazon Warehouse', 'Open-Box Monitor {sku}', 'Warehouse Deals', 159.00, 28,
         'warehouse-deal,open-box,electronics,renewed-good',
         {'Condition': 'Open Box - Used Acceptable', 'Warehouse Inspection': 'Full', 'Warranty': '90-day Warehouse'}),
        ('Amazon Warehouse', 'Open-Box Kitchen Mixer {sku}', 'Warehouse Deals', 199.00, 30,
         'warehouse-deal,open-box,kitchen,renewed-excellent',
         {'Condition': 'Open Box - Like New', 'Warehouse Inspection': 'Full', 'Warranty': '90-day Warehouse'}),
        ('Amazon Frustration-Free', 'FFP Drone Starter {sku}', 'Frustration-Free', 169.00, 25,
         'frustration-free,open-box,electronics,prime,recyclable-packaging',
         {'Packaging': 'Frustration-Free', 'Recyclable': 'Yes', 'Setup': 'Out-of-box ready'}),
        ('Amazon Frustration-Free', 'FFP Kid Tablet {sku}', 'Frustration-Free', 99.00, 28,
         'frustration-free,kids,freetime-3to5,prime,recyclable-packaging',
         {'Packaging': 'Frustration-Free', 'Recyclable': 'Yes', 'Includes': 'Tablet + Kid-Proof case (no plastic clamshell)'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry — call from seed_extras.run_extras AFTER seed_r9.
# ---------------------------------------------------------------------------

def seed_r10(db, Product):
    """R10 final polish: push catalog from ~51.9k to 56000+. Idempotent."""
    if Product.query.count() >= 55500:
        return 0
    added = 0

    # 1) Replay every prior template pool (SKU + R4 + R5 + R6 + R7 + R8 + R9)
    #    with R10_SUFFIXES — each fresh suffix unlocks a new slug.
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
    for cat, tpls in R8_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R9_NEW_TEMPLATES.items():
        combined.append((cat, tpls))

    for category, templates in combined:
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(8):
                # 13 is co-prime with 40 → broad suffix coverage.
                sfx_idx = (t_idx * 13 + variant_idx) % len(R10_SUFFIXES)
                idx = sfx_idx + 200000 + variant_idx * 79 + t_idx * 47
                data = _build_r10_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) R10-only templates × 48 variants — Bundles / Custom / Made-by-Amazon /
    #    Seasonal / Warehouse Deals.
    for category, templates in R10_NEW_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(48):
                sfx_idx = (t_idx * 17 + variant_idx) % len(R10_SUFFIXES)
                idx = sfx_idx + 300000 + variant_idx * 67 + t_idx * 53
                data = _build_r10_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    return added


# ---------------------------------------------------------------------------
# Builder — extends R9 quality fields with R10 bundle / made-by-amazon /
# seasonal-band / holiday-gift-guide flags.
# ---------------------------------------------------------------------------

def _build_r10_sku(idx, template, category, pool, sfx_idx):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R10_SUFFIXES[sfx_idx % len(R10_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    if base_price <= 0:
        price = 0.0
        list_price = 0.0
    else:
        jitter = -0.10 + ((idx * 59) % 21) / 100.0
        price = round(base_price * (1 + jitter), 2)
        list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.9 + ((idx * 41) % 100) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 60 + (idx * 199) % 22000
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
    gallery = [pool[(idx + j * 37) % len(pool)] for j in range(8)] if pool else []

    # --- prior quality fields (deterministic from idx/sfx_idx) ---
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

    is_prescription = (category == 'pharmacy' and subcat == 'Prescription')
    vehicle_fit = None
    if category == 'auto':
        vehicle_fit = VEHICLE_FITMENT[(idx + sfx_idx * 5) % len(VEHICLE_FITMENT)]
    renewed_grade = None
    if category == 'renewed':
        renewed_grade = RENEWED_GRADES[(idx + sfx_idx) % len(RENEWED_GRADES)]
    freetime_band = None
    if category == 'kids_freetime':
        freetime_band = FREETIME_BANDS[(idx + sfx_idx) % len(FREETIME_BANDS)]
    is_household_share = (category == 'household') or ((idx * 29 + sfx_idx * 13) % 100 < 8)
    is_live_featured = (category == 'live_shopping') or ((idx * 31 + sfx_idx * 17) % 100 < 4)
    is_outlet_open_box = (category == 'outlet')

    # --- R10-only quality fields ---
    bundle_kind = None
    if category in ('bundles', 'warehouse_deals'):
        bundle_kind = BUNDLE_KINDS[(idx + sfx_idx) % len(BUNDLE_KINDS)]
    is_made_by_amazon = category in ('made_by_amazon',)
    seasonal_band = None
    if category == 'seasonal':
        seasonal_band = SEASONAL_BANDS[(idx + sfx_idx) % len(SEASONAL_BANDS)]
    is_holiday_gift_guide = (category == 'seasonal' and seasonal_band == 'winter-26'
                             ) or ('holiday-gift-guide' in tag_csv)
    is_warehouse_deal = (category == 'warehouse_deals')
    is_frustration_free = (category == 'warehouse_deals' and 'Frustration-Free' in subcat)

    # --- additional vehicle fitment for AUTO BUNDLES (cross-category) ---
    if category == 'bundles' and bundle_kind == 'vin-fit':
        vehicle_fit = VEHICLE_FITMENT[(idx + sfx_idx * 7) % len(VEHICLE_FITMENT)]
    if category == 'bundles' and bundle_kind == 'refurb-pack':
        renewed_grade = RENEWED_GRADES[(idx + sfx_idx * 3) % len(RENEWED_GRADES)]

    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
    tags.append(color.lower().replace(' ', '-'))
    if is_climate_pledge:
        tags.append('climate-pledge-friendly')
    if is_recyclable_pkg and 'recyclable-packaging' not in tags:
        tags.append('recyclable-packaging')
    tags.append(made_in)
    if is_one_day_eligible:
        tags.append('one-day-shipping-eligible')
    if is_small_business and 'small-business' not in tags:
        tags.append('small-business')
    if is_sns and 'subscribe-and-save' not in tags:
        tags.append('subscribe-and-save')
    if age_tag:
        tags.append(age_tag)
    if is_business_prime:
        tags.append('business-prime-eligible')
    if fit_type and fit_type not in ','.join(tags):
        tags.append(fit_type)
    if skin_type:
        tags.append(skin_type)
    if is_cruelty_free:
        tags.append('cruelty-free')
    if is_vegan_formula:
        tags.append('vegan-formula')
    if is_prescription:
        tags.append('prescription-required')
    if vehicle_fit and vehicle_fit not in ','.join(tags):
        tags.append(vehicle_fit)
    if renewed_grade and renewed_grade not in ','.join(tags):
        tags.append(renewed_grade)
    if freetime_band and freetime_band not in ','.join(tags):
        tags.append(freetime_band)
    if is_household_share:
        tags.append('household-share-eligible')
    if is_live_featured:
        tags.append('live-shopping-featured')
    if is_outlet_open_box:
        tags.append('outlet-open-box')

    if bundle_kind:
        tags.append('bundle')
        tags.append(bundle_kind)
    if is_made_by_amazon:
        tags.append('made-by-amazon')
    if seasonal_band:
        tags.append(seasonal_band)
    if is_holiday_gift_guide and 'holiday-gift-guide' not in tags:
        tags.append('holiday-gift-guide')
    if is_warehouse_deal:
        tags.append('warehouse-deal')
    if is_frustration_free:
        tags.append('frustration-free')

    # R10: stock-state distribution.
    stock_seed = (idx * 43 + sfx_idx * 29) % 100
    if category in ('audible', 'kindle'):
        stock = 999
    elif category in ('household', 'live_shopping'):
        stock = 999
    elif category == 'pharmacy' and subcat == 'Prescription':
        stock = 500
    elif category == 'seasonal':
        # Seasonal items go limited-stock late in cycle (deterministic anchor).
        stock = 24 + (idx * 13) % 240
        if (idx % 11) == 0:
            tags.append('limited-time')
    elif category == 'warehouse_deals':
        # Warehouse items are one-of-a-kind-ish: 1-12 per slug.
        stock = 1 + (idx * 17) % 12
        if 'open-box' not in tags:
            tags.append('open-box')
    elif stock_seed < 6:
        stock = 0
        tags.append('notify-when-back')
    elif stock_seed < 19:
        stock = 1 + ((idx * 23 + sfx_idx * 13) % 4)
        tags.append('low-stock')
    else:
        stock = 12 + (idx * 27 + int(rating * 10)) % 360

    # --- specs additions ---
    specs['Climate Pledge Friendly'] = 'Yes' if is_climate_pledge else 'No'
    specs['Recyclable Packaging'] = 'Yes' if (is_recyclable_pkg or is_frustration_free) else 'No'
    made_in_display = {
        'made-in-usa': 'United States', 'made-in-germany': 'Germany',
        'made-in-japan': 'Japan', 'made-in-italy': 'Italy',
        'made-in-vietnam': 'Vietnam', 'made-in-china': 'China',
        'made-in-mexico': 'Mexico',
    }.get(made_in, 'Imported')
    specs['Country of Origin'] = made_in_display
    if is_one_day_eligible:
        specs['One-Day Shipping'] = 'Eligible'
    if is_sns or 'subscribe-and-save' in tags:
        specs['Subscribe & Save'] = 'Available (up to 15% off)'
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
    if is_prescription:
        specs['Prescription Required'] = 'Yes'
    if vehicle_fit:
        specs['Vehicle Fitment'] = vehicle_fit.replace('fits-', '').title()
    if renewed_grade:
        specs['Renewed Grade'] = renewed_grade.replace('renewed-', '').title()
        specs['Renewed Guarantee'] = '90-day Amazon Renewed Guarantee'
    if freetime_band:
        band = freetime_band.replace('freetime-', '').replace('to', '–')
        specs['FreeTime Age Band'] = band
        specs['Kid-Safe Content'] = 'Yes (curated by Amazon Kids)'
    if is_household_share:
        specs['Household Share'] = 'Eligible (Amazon Household)'
    if is_live_featured:
        specs['Amazon Live'] = 'Featured in livestream carousel'
    if bundle_kind:
        specs['Bundle Type'] = bundle_kind.replace('-', ' ').title()
    if is_made_by_amazon:
        specs['Private Label'] = 'Made by Amazon'
    if seasonal_band:
        specs['Season'] = seasonal_band.replace('-', ' ').title()
    if is_holiday_gift_guide:
        specs['Featured In'] = 'Holiday Gift Guide 2026'
    if is_warehouse_deal:
        specs['Warehouse Deal'] = 'Yes (inspected, 90-day warranty)'
    if is_frustration_free:
        specs['Packaging'] = 'Frustration-Free (recyclable)'

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
    if 'subscribe-and-save' in tags:
        features.append('Subscribe & Save — up to 15% off recurring orders')
    if is_business_prime:
        features.append('Business Prime — bulk-pricing tier for verified buyers')
    if bundle_kind == 'hsa-care':
        features.append('HSA / FSA eligible — pay with your health-savings account')
    if bundle_kind == 'vin-fit':
        features.append('VIN-fitment verified — Amazon Garage compatible')
    if bundle_kind == 'refurb-pack':
        features.append('Amazon Renewed — 90-day guarantee + extended protection options')
    if bundle_kind == 'monogram-pack':
        features.append('Amazon Custom — personalization included')
    if is_made_by_amazon:
        features.append('Made by Amazon — private-label quality at value pricing')
    if seasonal_band:
        features.append(f"Season: {seasonal_band.replace('-', ' ').title()}")
    if is_holiday_gift_guide:
        features.append('Featured in the 2026 Amazon Holiday Gift Guide')
    if is_warehouse_deal:
        features.append('Amazon Warehouse — inspected open-box with 90-day warranty')
    if is_frustration_free:
        features.append('Frustration-Free Packaging — 100% recyclable, no clamshell')

    is_deal = (idx % 5 == 0) or is_outlet_open_box or is_live_featured or is_warehouse_deal
    is_bestseller = (reviews > 14000)
    is_featured = (idx % 19 == 0) or is_live_featured or is_holiday_gift_guide
    return dict(
        name=name, brand=brand, category_slug=category, subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants=variants, stock=stock,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='',
    )
