#!/usr/bin/env python3
"""R9 polish pass — push catalog from ~40.7k to 50000+.

What this adds on top of R8 (seed_r8.py):

  • R9_NEW_TEMPLATES — Amazon Pharmacy (Rx + OTC), Amazon Auto (tires,
    batteries, motor oil, parts), Amazon Renewed (refurbished electronics
    grades), Amazon Outlet (overstock / open-box), Amazon Kids FreeTime
    (kid-safe content / kid-tablet bundles) and a tiny "live shopping" /
    "household" long-tail.
  • R9_SUFFIXES — 38 fresh codenames (no overlap with R2/R4/R5/R6/R7/R8).
  • Replays prior template pools (SKU + R4 + R5 + R6 + R7 + R8) with
    R9_SUFFIXES so the long-tail keeps growing.
  • R9 quality fields on top of R8:
        - prescription_required + ndc (pharmacy)
        - vehicle_fitment (auto: VIN-anchored part-fit tag)
        - renewed_grade (premium / excellent / good / acceptable)
        - household_share_eligible flag
        - freetime_age_band (kids: 3-5 / 6-8 / 9-12)
        - live_shopping_featured flag (livestream-deal carousel)

Deterministic: every numeric / boolean derived from idx + sfx_idx, so
rebuilds stay byte-identical. No datetime.now() / random without seed.

Idempotent — exits early when Product.count() already >= 48500 (R9 floor).
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
from seed_r8 import R8_NEW_TEMPLATES, R8_SUFFIXES, FIT_TYPES, SKIN_TYPES


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Distinct codename pool — no overlap with R2 / R4 / R5 / R6 / R7 / R8.
R9_SUFFIXES = [
    'Arden', 'Brio', 'Calix', 'Dune', 'Ember', 'Fjord',
    'Glade', 'Hearth', 'Isolde', 'Jovian', 'Krait', 'Lyra',
    'Maple', 'Nereid', 'Onyx9', 'Pulsar', 'Quasar', 'Reverie',
    'Saffron', 'Tundra', 'Ursa', 'Vellum', 'Wildflower', 'Xenon',
    'Yarrow', 'Zenith', 'Aurora9', 'Bastion', 'Crescent', 'Drift',
    'Equinox', 'Frost', 'Galaxy', 'Halberd', 'Inkwell', 'Jasper',
    'Kindred', 'Larkspur',
]


# R9-only quality buckets.
RENEWED_GRADES = ['renewed-premium', 'renewed-excellent', 'renewed-good',
                  'renewed-acceptable']
FREETIME_BANDS = ['freetime-3to5', 'freetime-6to8', 'freetime-9to12']
VEHICLE_FITMENT = ['fits-sedan', 'fits-suv', 'fits-truck', 'fits-coupe',
                   'fits-minivan', 'fits-ev', 'fits-motorcycle']


# ---------------------------------------------------------------------------
# R9-only templates. Shape matches _build_generic_sku:
#   (brand, name_tpl_with_{sku}, subcategory, base_price, list_uplift_pct,
#    tag_csv, specs_template)
# ---------------------------------------------------------------------------

R9_NEW_TEMPLATES = {
    # ---------------------- PHARMACY (Rx + OTC) ----------------------
    'pharmacy': [
        # Rx — prescription medications (priced at cash-pay rate)
        ('Amazon Pharmacy', 'Atorvastatin 20mg {sku} — 30-day Supply', 'Prescription', 14.50, 35,
         'pharmacy,rx,statin,cholesterol,prescription',
         {'NDC': '00093-7616-30', 'Strength': '20mg', 'Days Supply': '30', 'Form': 'Tablet'}),
        ('Amazon Pharmacy', 'Metformin HCl 500mg {sku} — 60-count', 'Prescription', 8.50, 40,
         'pharmacy,rx,diabetes,prescription',
         {'NDC': '00093-1048-60', 'Strength': '500mg', 'Days Supply': '30', 'Form': 'Tablet'}),
        ('Amazon Pharmacy', 'Lisinopril 10mg {sku} — Hypertension', 'Prescription', 6.99, 38,
         'pharmacy,rx,bp,prescription',
         {'NDC': '00378-1812-90', 'Strength': '10mg', 'Days Supply': '30', 'Form': 'Tablet'}),
        ('Amazon Pharmacy', 'Levothyroxine 50mcg {sku} — Thyroid', 'Prescription', 11.00, 33,
         'pharmacy,rx,thyroid,prescription',
         {'NDC': '00378-1801-30', 'Strength': '50mcg', 'Days Supply': '30', 'Form': 'Tablet'}),
        ('Amazon Pharmacy', 'Amlodipine 5mg {sku} — Calcium Blocker', 'Prescription', 7.50, 36,
         'pharmacy,rx,bp,prescription',
         {'NDC': '00093-7370-30', 'Strength': '5mg', 'Days Supply': '30', 'Form': 'Tablet'}),
        ('Amazon Pharmacy', 'Sertraline HCl 50mg {sku} — Antidepressant', 'Prescription', 12.00, 34,
         'pharmacy,rx,ssri,prescription',
         {'NDC': '00093-7197-30', 'Strength': '50mg', 'Days Supply': '30', 'Form': 'Tablet'}),
        ('Amazon Pharmacy', 'Albuterol HFA Inhaler {sku} — Rescue', 'Prescription', 23.00, 28,
         'pharmacy,rx,asthma,inhaler,prescription',
         {'NDC': '00173-0682-20', 'Strength': '90mcg/actuation', 'Form': 'Inhaler'}),
        ('Amazon Pharmacy', 'Omeprazole DR 20mg {sku} — Acid Reflux', 'Prescription', 9.99, 34,
         'pharmacy,rx,ppi,prescription',
         {'NDC': '00378-7104-30', 'Strength': '20mg', 'Days Supply': '30', 'Form': 'Capsule'}),
        ('Amazon Pharmacy', 'Gabapentin 300mg {sku} — Neuropathy', 'Prescription', 13.50, 32,
         'pharmacy,rx,neuropathy,prescription',
         {'NDC': '00781-2024-60', 'Strength': '300mg', 'Days Supply': '30', 'Form': 'Capsule'}),
        ('Amazon Pharmacy', 'Hydrochlorothiazide 25mg {sku} — Diuretic', 'Prescription', 5.50, 38,
         'pharmacy,rx,diuretic,prescription',
         {'NDC': '00781-1085-30', 'Strength': '25mg', 'Days Supply': '30', 'Form': 'Tablet'}),
        # OTC — over-the-counter (no prescription)
        ('Amazon Basic Care', 'Ibuprofen 200mg {sku} — 500 Tablets', 'OTC', 11.99, 30,
         'pharmacy,otc,pain-relief,nsaid',
         {'Strength': '200mg', 'Count': '500', 'Form': 'Tablet'}),
        ('Amazon Basic Care', 'Acetaminophen 500mg {sku} — 250 Caplets', 'OTC', 8.49, 32,
         'pharmacy,otc,pain-relief,fever',
         {'Strength': '500mg', 'Count': '250', 'Form': 'Caplet'}),
        ('Amazon Basic Care', 'Loratadine 10mg {sku} — 365 Tablets', 'OTC', 18.99, 28,
         'pharmacy,otc,allergy,antihistamine',
         {'Strength': '10mg', 'Count': '365', 'Form': 'Tablet'}),
        ('Amazon Basic Care', 'Omeprazole OTC 20mg {sku} — 42 Tablets', 'OTC', 19.99, 26,
         'pharmacy,otc,acid-reducer',
         {'Strength': '20mg', 'Count': '42', 'Form': 'Tablet'}),
        ('Amazon Basic Care', 'Melatonin 5mg {sku} — 120 Gummies', 'OTC', 9.99, 35,
         'pharmacy,otc,sleep,supplement',
         {'Strength': '5mg', 'Count': '120', 'Form': 'Gummy'}),
        ('Nature Made', 'Vitamin D3 2000 IU {sku} — 400 Softgels', 'OTC', 13.99, 30,
         'pharmacy,otc,vitamin,supplement',
         {'Strength': '2000 IU', 'Count': '400', 'Form': 'Softgel'}),
        ('Centrum', 'Silver Adults 50+ Multivitamin {sku} — 250ct', 'OTC', 18.49, 32,
         'pharmacy,otc,multivitamin,senior',
         {'Count': '250', 'Form': 'Tablet'}),
        ('Zyrtec', '10mg Allergy Tablets {sku} — 90 Count', 'OTC', 28.99, 28,
         'pharmacy,otc,allergy,antihistamine',
         {'Strength': '10mg', 'Count': '90', 'Form': 'Tablet'}),
        ('Claritin', '24-Hour Allergy 10mg {sku} — 100 Tablets', 'OTC', 32.49, 25,
         'pharmacy,otc,allergy,non-drowsy',
         {'Strength': '10mg', 'Count': '100', 'Form': 'Tablet'}),
        ('Tylenol', 'Extra Strength 500mg {sku} — 325 Caplets', 'OTC', 18.99, 28,
         'pharmacy,otc,pain-relief',
         {'Strength': '500mg', 'Count': '325', 'Form': 'Caplet'}),
    ],
    # ---------------------- AUTO (tires / batteries / parts) ----------------------
    'auto': [
        ('Michelin', 'Defender T+H 215/60R16 {sku} — All-Season Tire', 'Auto Tires', 169.99, 22,
         'auto,tire,all-season',
         {'Size': '215/60R16', 'Tread Warranty': '80,000 mi', 'Speed Rating': 'H'}),
        ('Bridgestone', 'Turanza QuietTrack 225/65R17 {sku}', 'Auto Tires', 215.00, 20,
         'auto,tire,touring,all-season',
         {'Size': '225/65R17', 'Tread Warranty': '80,000 mi', 'Noise': 'Quiet'}),
        ('Goodyear', 'Assurance WeatherReady 235/60R18 {sku}', 'Auto Tires', 225.00, 20,
         'auto,tire,all-weather',
         {'Size': '235/60R18', 'Tread Warranty': '60,000 mi', '3PMS': 'Yes'}),
        ('Continental', 'PureContact LS 215/55R17 {sku}', 'Auto Tires', 189.00, 22,
         'auto,tire,grand-touring,all-season',
         {'Size': '215/55R17', 'Tread Warranty': '70,000 mi'}),
        ('Pirelli', 'P Zero PZ4 245/40R19 {sku} — Summer', 'Auto Tires', 348.00, 16,
         'auto,tire,summer,performance',
         {'Size': '245/40R19', 'Type': 'Summer', 'Speed Rating': 'Y'}),
        ('Cooper', 'Discoverer AT3 4S 265/70R17 {sku}', 'Auto Tires', 198.00, 22,
         'auto,tire,all-terrain,truck',
         {'Size': '265/70R17', 'Tread': 'A/T', '3PMS': 'Yes'}),
        # Batteries / oil / fluids
        ('Optima', 'RedTop 35 AGM Starting Battery {sku}', 'Auto Parts', 249.99, 18,
         'auto,battery,agm,starting',
         {'CCA': '720', 'Reserve': '90 min', 'Type': 'AGM'}),
        ('Interstate', 'MTP-94R Mega-Tron Plus {sku}', 'Auto Parts', 189.99, 20,
         'auto,battery,starting',
         {'CCA': '850', 'Reserve': '160 min'}),
        ('DieHard', 'Gold AGM Group 94R Battery {sku}', 'Auto Parts', 219.99, 18,
         'auto,battery,agm',
         {'CCA': '850', 'Reserve': '160 min', 'Type': 'AGM'}),
        ('Mobil 1', 'Extended Performance 5W-30 5qt {sku}', 'Auto Parts', 38.99, 25,
         'auto,oil,full-synthetic,5w30',
         {'Viscosity': '5W-30', 'Volume': '5 qt', 'Type': 'Full Synthetic'}),
        ('Castrol', 'EDGE 0W-20 Advanced Full Synthetic 5qt {sku}', 'Auto Parts', 32.99, 28,
         'auto,oil,full-synthetic,0w20',
         {'Viscosity': '0W-20', 'Volume': '5 qt', 'Type': 'Full Synthetic'}),
        ('Valvoline', 'MaxLife 10W-30 5qt {sku} — High Mileage', 'Auto Parts', 27.99, 30,
         'auto,oil,high-mileage,10w30',
         {'Viscosity': '10W-30', 'Volume': '5 qt'}),
        ('Bosch', 'Icon Wiper Blade 22" {sku} — Beam', 'Auto Parts', 28.99, 25,
         'auto,wiper,blade,beam',
         {'Length': '22"', 'Type': 'Beam'}),
        ('K&N', '57-Series FIPK Cold Air Intake {sku}', 'Auto Parts', 349.00, 18,
         'auto,intake,performance',
         {'Type': 'Cold Air Intake', 'Filter': 'Lifetime Washable'}),
        ('Brembo', 'OE Premium Brake Rotor 320mm {sku} — Front', 'Auto Parts', 119.00, 22,
         'auto,brake,rotor,front',
         {'Diameter': '320mm', 'Type': 'Vented'}),
        ('Akebono', 'EUR1078 ProACT Ultra-Premium Pads {sku}', 'Auto Parts', 64.99, 28,
         'auto,brake,pads,ceramic',
         {'Type': 'Ceramic', 'Position': 'Front'}),
        # Accessories
        ('WeatherTech', 'FloorLiner Front Pair {sku} — Black', 'Auto Accessories', 169.99, 22,
         'auto,floor-liner,interior',
         {'Material': 'TPE', 'Color': 'Black', 'Coverage': 'Front Pair'}),
        ('Husky', 'X-Act Contour 2nd Row Floor Liner {sku}', 'Auto Accessories', 139.99, 22,
         'auto,floor-liner,interior',
         {'Material': 'Rubber', 'Coverage': '2nd Row'}),
        ('Thule', 'Force XT Sport Cargo Box {sku} — 11 cu ft', 'Auto Accessories', 599.00, 14,
         'auto,roof-box,cargo',
         {'Capacity': '11 cu ft', 'Mount': 'Quick-Mount'}),
        ('Yakima', 'JetStream Crossbars 60" Pair {sku}', 'Auto Accessories', 269.00, 18,
         'auto,roof-rack,crossbar',
         {'Length': '60"', 'Material': 'Aluminum'}),
    ],
    # ---------------------- AMAZON RENEWED (refurb electronics) ----------------------
    'renewed': [
        ('Amazon Renewed', 'iPhone 13 128GB {sku} — Renewed Premium', 'Renewed Phones', 449.00, 30,
         'renewed,phone,iphone,refurbished',
         {'Storage': '128GB', 'Carrier': 'Unlocked', 'Battery': '≥90% capacity'}),
        ('Amazon Renewed', 'Galaxy S22 256GB {sku} — Renewed Excellent', 'Renewed Phones', 379.00, 35,
         'renewed,phone,samsung,refurbished',
         {'Storage': '256GB', 'Carrier': 'Unlocked', 'Battery': '≥85% capacity'}),
        ('Amazon Renewed', 'Google Pixel 7 128GB {sku} — Renewed', 'Renewed Phones', 299.00, 38,
         'renewed,phone,pixel,refurbished',
         {'Storage': '128GB', 'Carrier': 'Unlocked'}),
        ('Amazon Renewed', 'MacBook Air M1 256GB {sku} — Renewed', 'Renewed Laptops', 729.00, 28,
         'renewed,laptop,macbook,refurbished',
         {'CPU': 'Apple M1', 'RAM': '8GB', 'Storage': '256GB'}),
        ('Amazon Renewed', 'MacBook Pro 14" M1 Pro {sku} — Renewed Premium', 'Renewed Laptops', 1399.00, 22,
         'renewed,laptop,macbook,refurbished',
         {'CPU': 'M1 Pro 8-core', 'RAM': '16GB', 'Storage': '512GB'}),
        ('Amazon Renewed', 'Dell XPS 13 9310 i7 {sku} — Renewed Excellent', 'Renewed Laptops', 649.00, 30,
         'renewed,laptop,dell,refurbished',
         {'CPU': 'i7-1185G7', 'RAM': '16GB', 'Storage': '512GB'}),
        ('Amazon Renewed', 'iPad Pro 11" M1 128GB {sku} — Renewed', 'Renewed Tablets', 599.00, 28,
         'renewed,tablet,ipad,refurbished',
         {'CPU': 'Apple M1', 'Storage': '128GB', 'Display': '11" Liquid Retina'}),
        ('Amazon Renewed', 'Surface Pro 8 i5 {sku} — Renewed Good', 'Renewed Tablets', 549.00, 32,
         'renewed,tablet,surface,refurbished',
         {'CPU': 'i5-1135G7', 'RAM': '8GB', 'Storage': '256GB'}),
        ('Amazon Renewed', 'Bose QC45 Wireless Headphones {sku} — Renewed', 'Renewed Audio', 199.00, 28,
         'renewed,headphones,anc,refurbished',
         {'Type': 'Over-Ear', 'ANC': 'Yes', 'Battery': '24h'}),
        ('Amazon Renewed', 'Sony WH-1000XM4 {sku} — Renewed Premium', 'Renewed Audio', 219.00, 30,
         'renewed,headphones,anc,refurbished',
         {'Type': 'Over-Ear', 'ANC': 'Yes', 'Battery': '30h'}),
        ('Amazon Renewed', 'Apple Watch Series 7 45mm GPS {sku} — Renewed', 'Renewed Watches', 269.00, 28,
         'renewed,watch,apple-watch,refurbished',
         {'Case': '45mm Aluminum', 'GPS': 'Yes'}),
        ('Amazon Renewed', 'Garmin Fenix 6 Sapphire {sku} — Renewed', 'Renewed Watches', 379.00, 26,
         'renewed,watch,garmin,refurbished',
         {'Case': '47mm Sapphire', 'GPS': 'Multi-Band'}),
        ('Amazon Renewed', 'Canon EOS R6 Body {sku} — Renewed Excellent', 'Renewed Cameras', 1599.00, 18,
         'renewed,camera,mirrorless,refurbished',
         {'Sensor': '20MP Full-Frame', 'Video': '4K 60p'}),
        ('Amazon Renewed', 'Sony A7 III Body {sku} — Renewed', 'Renewed Cameras', 1299.00, 22,
         'renewed,camera,mirrorless,refurbished',
         {'Sensor': '24MP Full-Frame', 'Video': '4K 30p'}),
        ('Amazon Renewed', 'Nintendo Switch OLED {sku} — Renewed Good', 'Renewed Gaming', 269.00, 28,
         'renewed,gaming,console,refurbished',
         {'Display': '7" OLED', 'Storage': '64GB'}),
        ('Amazon Renewed', 'PlayStation 5 Disc Edition {sku} — Renewed', 'Renewed Gaming', 419.00, 22,
         'renewed,gaming,console,refurbished',
         {'Storage': '825GB SSD', 'Disc Drive': 'Yes'}),
    ],
    # ---------------------- AMAZON OUTLET (overstock / open-box) ----------------------
    'outlet': [
        ('Amazon Outlet', 'KitchenAid 5-Quart Stand Mixer {sku} — Open Box', 'Outlet Kitchen', 269.00, 38,
         'outlet,open-box,kitchen,overstock',
         {'Condition': 'Open Box', 'Capacity': '5 qt', 'Original Box': 'Damaged'}),
        ('Amazon Outlet', 'Dyson V11 Cordless Vacuum {sku} — Overstock', 'Outlet Home', 449.00, 32,
         'outlet,overstock,vacuum',
         {'Condition': 'Overstock', 'Run Time': '60 min', 'Warranty': '1 year'}),
        ('Amazon Outlet', 'iRobot Roomba j7+ {sku} — Open Box', 'Outlet Home', 539.00, 30,
         'outlet,open-box,robot-vacuum,overstock',
         {'Condition': 'Open Box', 'Mapping': 'Yes', 'Auto-Empty': 'Yes'}),
        ('Amazon Outlet', 'Samsung 55" QLED 4K TV {sku} — Outlet', 'Outlet Electronics', 549.00, 28,
         'outlet,overstock,tv,4k',
         {'Display': '55" QLED 4K', 'HDR': 'HDR10+'}),
        ('Amazon Outlet', 'LG OLED 65" C2 {sku} — Open Box', 'Outlet Electronics', 1499.00, 22,
         'outlet,open-box,tv,oled',
         {'Display': '65" OLED Evo', 'HDR': 'Dolby Vision IQ'}),
        ('Amazon Outlet', 'Sonos Beam Gen 2 Soundbar {sku} — Outlet', 'Outlet Electronics', 349.00, 28,
         'outlet,overstock,soundbar',
         {'Condition': 'Overstock', 'Channels': '5.0'}),
        ('Amazon Outlet', 'Vitamix 5200 Blender {sku} — Open Box', 'Outlet Kitchen', 349.00, 32,
         'outlet,open-box,blender',
         {'Condition': 'Open Box', 'Motor': '2.0 HP'}),
        ('Amazon Outlet', 'Breville Barista Express Espresso {sku} — Outlet', 'Outlet Kitchen', 549.00, 28,
         'outlet,overstock,espresso',
         {'Type': 'Semi-Automatic', 'Built-in Grinder': 'Yes'}),
        ('Amazon Outlet', 'Herman Miller Aeron Size B {sku} — Open Box', 'Outlet Office', 1099.00, 30,
         'outlet,open-box,chair,office',
         {'Condition': 'Open Box', 'Size': 'B (Medium)'}),
        ('Amazon Outlet', 'Steelcase Leap V2 Chair {sku} — Overstock', 'Outlet Office', 749.00, 32,
         'outlet,overstock,chair,office',
         {'Condition': 'Overstock', 'Adjustments': '4D Arms + LiveBack'}),
    ],
    # ---------------------- KIDS FREETIME (kid-safe content / bundles) ----------------------
    'kids_freetime': [
        ('Amazon Kids', 'Fire HD 8 Kids Pro Tablet {sku} — 32GB', 'Kids Tablets', 139.99, 28,
         'kids,freetime,tablet,kid-safe',
         {'Display': '8" HD', 'Storage': '32GB', 'Age': '6-12', 'Bundled Content': '1 year FreeTime+'}),
        ('Amazon Kids', 'Fire 7 Kids Tablet {sku} — 16GB', 'Kids Tablets', 109.99, 30,
         'kids,freetime,tablet,kid-safe',
         {'Display': '7"', 'Storage': '16GB', 'Age': '3-7'}),
        ('Amazon Kids', 'Fire HD 10 Kids Pro {sku} — 32GB Disney Mickey', 'Kids Tablets', 189.99, 28,
         'kids,freetime,tablet,disney',
         {'Display': '10.1" 1080p', 'Storage': '32GB', 'Age': '6-12'}),
        ('Amazon Kids', 'Echo Dot Kids Owl {sku} — Alexa for Kids', 'Kids Audio', 59.99, 32,
         'kids,freetime,echo,alexa-kids',
         {'Voice': 'Kid-friendly', 'Parental Dashboard': 'Yes'}),
        ('Amazon Kids', 'Kindle Kids Edition {sku} — 16GB Black Cover', 'Kids E-Readers', 119.99, 30,
         'kids,freetime,kindle,e-reader',
         {'Storage': '16GB', 'Display': '6" 300ppi', 'Bundled Content': 'Kids+ 1 yr'}),
        ('Amazon Kids', 'FreeTime+ Annual Subscription {sku} — 12 Months', 'Kids Subscriptions', 79.00, 25,
         'kids,freetime,subscription,kid-safe',
         {'Term': '12 months', 'Devices': 'Up to 4 child profiles'}),
        ('LeapFrog', 'LeapPad Academy Tablet {sku} — Pink', 'Kids Tablets', 129.99, 28,
         'kids,tablet,learning',
         {'Display': '7" Touchscreen', 'Age': '3-8', 'Apps': '20+ included'}),
        ('VTech', 'KidiZoom Creator Cam HD {sku}', 'Kids Cameras', 89.99, 30,
         'kids,camera,creator',
         {'Resolution': '1080p', 'Tripod': 'Included', 'Age': '5+'}),
        ('Osmo', 'Genius Starter Kit for iPad {sku}', 'Kids Educational', 99.99, 32,
         'kids,educational,osmo,stem',
         {'Age': '6-10', 'Includes': '5 hands-on games'}),
        ('Tonies', 'Toniebox Starter Set {sku} — Audio Player', 'Kids Audio', 99.99, 30,
         'kids,audio,toniebox,screen-free',
         {'Age': '3+', 'Battery': '7 hrs', 'WiFi': 'Yes'}),
    ],
    # ---------------------- LIVE SHOPPING (livestream-deal carousel) ----------------------
    'live_shopping': [
        ('Amazon Live', 'Livestream Featured Deal Bundle {sku}', 'Live Shopping', 49.99, 45,
         'live-shopping,livestream,deal,featured',
         {'Format': 'Livestream', 'Window': '1-hour flash'}),
        ('Amazon Live', 'Beauty Influencer Pick {sku} — Glow Bundle', 'Live Shopping', 59.99, 40,
         'live-shopping,beauty,influencer-pick',
         {'Curator': 'Verified Influencer', 'Format': 'Replay-available'}),
        ('Amazon Live', 'Home Chef Live Pick {sku} — Cookware Set', 'Live Shopping', 119.99, 35,
         'live-shopping,kitchen,cookware,deal',
         {'Bundle': 'Cookware', 'Window': '24h'}),
        ('Amazon Live', 'Tech Reviewer Pick {sku} — Gadget Bundle', 'Live Shopping', 89.99, 38,
         'live-shopping,electronics,tech,deal',
         {'Curator': 'Verified Tech Creator', 'Window': '6h'}),
        ('Amazon Live', 'Fashion Stylist Pick {sku} — Capsule Wardrobe', 'Live Shopping', 149.99, 32,
         'live-shopping,fashion,stylist,deal',
         {'Curator': 'Verified Stylist', 'Window': '12h'}),
    ],
    # ---------------------- HOUSEHOLD (Amazon Household shared profiles) ----------------------
    'household': [
        ('Amazon Household', 'Family Plan Annual Membership {sku}', 'Household Plans', 0.00, 0,
         'household,family,membership,share',
         {'Adults': 'Up to 2', 'Teens': 'Up to 4', 'Kids': 'Up to 4'}),
        ('Amazon Household', 'Shared Wallet Top-Up Card {sku} — $50', 'Household Plans', 50.00, 0,
         'household,gift,shared-wallet',
         {'Denomination': '$50', 'Sharing': 'Family'}),
        ('Amazon Household', 'Shared Wallet Top-Up Card {sku} — $100', 'Household Plans', 100.00, 0,
         'household,gift,shared-wallet',
         {'Denomination': '$100', 'Sharing': 'Family'}),
        ('Amazon Household', 'Teen Profile Sub-Account {sku} — Yearly Add-On', 'Household Plans', 0.00, 0,
         'household,teen,sub-account',
         {'Approval': 'Parent', 'Spend Cap': 'Configurable'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry — call from seed_extras.run_extras AFTER seed_r8.
# ---------------------------------------------------------------------------

def seed_r9(db, Product):
    """R9 polish: push catalog from ~40.7k to 50000+. Idempotent."""
    if Product.query.count() >= 48500:
        return 0
    added = 0

    # 1) Replay every prior template pool (SKU + R4 + R5 + R6 + R7 + R8)
    #    with R9_SUFFIXES — each fresh suffix unlocks a new slug.
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

    for category, templates in combined:
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(18):
                # 17 is co-prime with 38 → broad suffix coverage.
                sfx_idx = (t_idx * 17 + variant_idx) % len(R9_SUFFIXES)
                idx = sfx_idx + 90000 + variant_idx * 73 + t_idx * 41
                data = _build_r9_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) R9-only templates × 36 variants — Pharmacy / Auto / Renewed /
    #    Outlet / Kids FreeTime / Live Shopping / Household.
    for category, templates in R9_NEW_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(36):
                sfx_idx = (t_idx * 19 + variant_idx) % len(R9_SUFFIXES)
                idx = sfx_idx + 100000 + variant_idx * 61 + t_idx * 43
                data = _build_r9_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    return added


# ---------------------------------------------------------------------------
# Builder — extends R8 quality fields with R9 prescription / fitment /
# renewed-grade / freetime-band / household / live-shopping flags.
# ---------------------------------------------------------------------------

def _build_r9_sku(idx, template, category, pool, sfx_idx):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R9_SUFFIXES[sfx_idx % len(R9_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
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
    reviews = 40 + (idx * 197) % 24000
    color = COLOR_NAMES[idx % len(COLOR_NAMES)]
    specs = dict(specs_tpl)
    specs['Color'] = color
    specs['Brand'] = brand

    variants = {'color': [color,
                          COLOR_NAMES[(idx + 3) % len(COLOR_NAMES)],
                          COLOR_NAMES[(idx + 11) % len(COLOR_NAMES)]]}
    if category == 'fashion' and subcat in ('Mens Clothing', 'Womens Clothing'):
        variants['size'] = SIZE_VALUES
    elif category == 'fashion' and subcat == 'Shoes':
        variants['size'] = SHOE_SIZES

    img = pool[idx % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 31) % len(pool)] for j in range(8)] if pool else []

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

    # --- R8 quality fields ---
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

    # --- R9-only quality fields ---
    is_prescription = (category == 'pharmacy' and subcat == 'Prescription')
    ndc = specs.get('NDC') or ''
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

    # R9 tags
    if is_prescription:
        tags.append('prescription-required')
        if ndc:
            tags.append('ndc:' + ndc.replace(' ', ''))
    if vehicle_fit:
        tags.append(vehicle_fit)
    if renewed_grade:
        tags.append(renewed_grade)
    if freetime_band:
        tags.append(freetime_band)
        tags.append('kid-safe-content')
    if is_household_share:
        tags.append('household-share-eligible')
    if is_live_featured:
        tags.append('live-shopping-featured')
    if is_outlet_open_box:
        tags.append('open-box')

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

    # R9: stock-state distribution (slightly different coefficients vs R8).
    stock_seed = (idx * 41 + sfx_idx * 23) % 100
    if category in ('audible', 'kindle'):
        stock = 999
    elif category in ('household', 'live_shopping'):
        # Digital / membership lines effectively never go out of stock.
        stock = 999
    elif category == 'pharmacy' and subcat == 'Prescription':
        # Rx is always "available pending verification" rather than counted.
        stock = 500
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
    if is_prescription:
        specs['Prescription Required'] = 'Yes'
        specs['Refills'] = '0 (new) / up to 11 (on renewal)'
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
    if is_outlet_open_box:
        specs['Condition'] = specs.get('Condition', 'Open Box')

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
    if is_prescription:
        features.append('Prescription required — Amazon Pharmacy will verify before fulfilment')
    if vehicle_fit:
        features.append(f"Vehicle fitment: {vehicle_fit.replace('fits-', '').title()}")
    if renewed_grade:
        features.append(f"Amazon Renewed grade: {renewed_grade.replace('renewed-', '').title()} + 90-day guarantee")
    if freetime_band:
        features.append(f"Amazon Kids+ ages {freetime_band.replace('freetime-', '').replace('to', '–')}")
    if is_household_share:
        features.append('Shareable via Amazon Household')
    if is_live_featured:
        features.append('Amazon Live featured deal')
    if is_outlet_open_box:
        features.append('Amazon Outlet — open-box / overstock at reduced price')

    is_deal = (idx % 5 == 0) or is_outlet_open_box or is_live_featured
    is_bestseller = (reviews > 14000)
    is_featured = (idx % 19 == 0) or is_live_featured
    return dict(
        name=name, brand=brand, category_slug=category, subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants=variants, stock=stock,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='',
    )
