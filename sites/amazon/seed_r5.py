#!/usr/bin/env python3
"""R5 polish pass — push catalog from ~5626 to 8000+ with quality fields.

What this adds on top of R4 (seed_polish.py):

  • Distinct R5_SUFFIXES (28 fresh codenames) — no collision with R4_SUFFIXES.
  • R5_NEW_TEMPLATES — brand-new (brand, family) tuples that R2/R3/R4 didn't
    emit, broadening the long tail (audio, smart-home, cookware, pet, baby,
    automotive, garden, office, music instruments, luggage, eyewear, …).
  • Each generated SKU carries enhanced quality tags:
        - climate-pledge-friendly   (deterministic ~25%)
        - recyclable-packaging      (deterministic ~30%)
        - made-in:<usa|germany|japan|italy|china|vietnam>  (deterministic)
        - one-day-shipping-eligible (deterministic ~22%)
        - subscribe-and-save        (consumables: beauty, pets, baby, groceries)
        - age-range:<…>             (toys + baby; encoded in feature_tags)
        - small-business            (deterministic ~12%)
  • Some SKUs (~7%) ship with stock=0 to seed "Currently unavailable" /
    "out-of-stock alternatives" coverage for the R5 task pack.
  • Deterministic: every numeric / boolean derived from idx + sfx_idx, so
    rebuilds stay byte-identical. No datetime.now() / random without seed.

Idempotent — exits early when Product.count() already >= 7800 (R5 floor).
"""
import os

from seed_bulk import (
    SKU_TEMPLATES, _build_generic_sku, _insert_product, _category_pool,
    COLOR_NAMES, SIZE_VALUES, SHOE_SIZES,
)
from seed_polish import R4_NEW_TEMPLATES


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Distinct codename pool — no overlap with R2 SKU_SUFFIXES or R4_SUFFIXES.
R5_SUFFIXES = [
    'Arcadia', 'Bristol', 'Cinder', 'Driftwood', 'Equinox', 'Fable', 'Galaxy',
    'Harbor', 'Ivy', 'Jasper', 'Kingfisher', 'Larkspur', 'Magnolia', 'Neptune',
    'Oxford', 'Petal', 'Quill', 'Rosewood', 'Saffron', 'Trillium', 'Umber',
    'Verdant', 'Willow', 'Xanadu', 'Yarrow', 'Zinnia', 'Aether', 'Borealis',
]

MADE_IN_BUCKETS = [
    'made-in-usa', 'made-in-germany', 'made-in-japan', 'made-in-italy',
    'made-in-vietnam', 'made-in-china', 'made-in-mexico',
]

# Age-range buckets for toys + baby; encoded as feature_tag so /s?feature=age-3-5 hits
AGE_BUCKETS = ['age-0-2', 'age-3-5', 'age-6-8', 'age-9-12', 'age-13-plus']

# Categories that legitimately offer Subscribe & Save (consumables)
SNS_CATEGORIES = {'beauty', 'home'}  # 'home' covers groceries-ish items here


# ---------------------------------------------------------------------------
# R5-only templates — brand-new tuples broadening the long tail.
# Shape matches seed_bulk._build_generic_sku:
#   (brand, name_tpl_with_{sku}, subcategory, base_price, list_uplift_pct,
#    tag_csv, specs_template)
# ---------------------------------------------------------------------------

R5_NEW_TEMPLATES = {
    'electronics': [
        ('Yamaha', 'YAS-{sku} Soundbar with Subwoofer', 'Speakers', 449.95, 25,
         'soundbar,wireless,dolby',
         {'Channels': '2.1', 'Power': '200W',
          'Connectivity': 'HDMI ARC, Bluetooth, Optical'}),
        ('Klipsch', 'Reference R-{sku}M Bookshelf Speakers', 'Speakers', 299.00, 18,
         'bookshelf,passive,audiophile',
         {'Driver': '4.5in woofer + 1in tweeter',
          'Sensitivity': '92 dB', 'Impedance': '8 ohms'}),
        ('Audio-Technica', 'AT-LP{sku}XBT Bluetooth Turntable', 'Speakers', 349.00, 20,
         'turntable,bluetooth,vinyl',
         {'Drive': 'Belt drive', 'Speeds': '33-1/3, 45',
          'Bluetooth': '5.0 with aptX'}),
        ('Shure', 'SM{sku} Dynamic Microphone', 'Audio', 99.00, 15,
         'microphone,dynamic,broadcast',
         {'Type': 'Dynamic cardioid', 'Frequency': '50Hz-15kHz',
          'Connector': 'XLR'}),
        ('Blue Microphones', 'Yeti {sku} USB Condenser Mic', 'Audio', 129.99, 25,
         'microphone,usb,podcast',
         {'Type': 'Condenser', 'Patterns': '4', 'Sample Rate': '48kHz/24-bit'}),
        ('Focal', 'Listen Pro {sku} Studio Headphones', 'Headphones', 299.00, 18,
         'headphones,studio,wired',
         {'Driver': '40mm', 'Impedance': '32 ohms',
          'Frequency Response': '5Hz-22kHz'}),
        ('Beyerdynamic', 'DT {sku} Pro Studio Headphones', 'Headphones', 179.00, 22,
         'studio,headphones,open-back',
         {'Driver': '45mm', 'Impedance': '80 ohms',
          'Frequency Response': '5Hz-35kHz'}),
        ('Insta360', 'X{sku} 360 Action Camera', 'Cameras', 549.99, 18,
         '360-camera,8k,action',
         {'Resolution': '5.7K 360', 'Stabilization': 'FlowState',
          'Waterproof': '33ft'}),
        ('Sony', 'ZV-{sku} Vlog Camera', 'Cameras', 749.00, 15,
         'vlog,camera,4k',
         {'Resolution': '4K30p', 'Mic': 'Directional 3-capsule',
          'Display': 'Vari-angle 3in touch'}),
        ('Nikon', 'Z {sku} Mirrorless Body', 'Cameras', 1799.99, 18,
         'mirrorless,full-frame,nikon',
         {'Sensor': 'Full-frame 45MP', 'Video': '8K30p',
          'AF Points': '493'}),
        ('Anker', 'Eufy SmartTrack {sku} Tracker 4-Pack', 'Smart Home', 79.99, 22,
         'tracker,bluetooth,4-pack',
         {'Range': '350ft', 'Battery': 'Replaceable CR2032',
          'Compatibility': 'Find My (Apple)'}),
        ('Tile', 'Mate {sku} Bluetooth Tracker 2-pack', 'Smart Home', 49.99, 20,
         'tracker,bluetooth,find-my',
         {'Range': '350ft', 'Battery': '3 years replaceable',
          'Compatibility': 'iOS + Android'}),
        ('Belkin', 'BoostCharge Pro {sku}W MagSafe Charger', 'Phone Accessories', 99.99, 18,
         'wireless-charger,magsafe,foldable',
         {'Power': '15W', 'Standard': 'MagSafe',
          'Design': 'Foldable travel'}),
        ('mophie', 'Powerstation Plus {sku} 10000mAh', 'Phone Accessories', 79.99, 22,
         'power-bank,lightning,usb-c',
         {'Capacity': '10000mAh', 'Output': 'USB-C 20W',
          'Cables': 'Lightning + USB-C built-in'}),
        ('Otterbox', 'Defender Series {sku} iPhone Case', 'Phone Accessories', 59.95, 25,
         'phone-case,rugged,iphone',
         {'Protection': 'Multi-layer + screen shield',
          'Drop Tested': 'MIL-STD-810G', 'Compatible': 'iPhone 15/15 Pro'}),
    ],
    'computers': [
        ('Framework', 'Laptop {sku} 13 (Ryzen, 32GB)', 'Laptops', 1399.00, 12,
         'modular,repairable,linux',
         {'CPU': 'AMD Ryzen 7 7840U', 'RAM': '32GB DDR5',
          'Storage': '1TB NVMe', 'Display': '13.5in 2256x1504'}),
        ('System76', 'Lemur Pro {sku}', 'Laptops', 1499.00, 10,
         'linux,pop-os,open-firmware',
         {'CPU': 'Intel Core i7-1355U', 'RAM': '40GB',
          'Storage': '500GB NVMe', 'OS': 'Pop!_OS'}),
        ('Eluktronics', 'Mech-{sku} G3Max Gaming Laptop', 'Laptops', 1799.99, 15,
         'gaming-laptop,rtx-4070,165hz',
         {'CPU': 'AMD Ryzen 9 7945HX', 'RAM': '32GB DDR5',
          'GPU': 'NVIDIA RTX 4070', 'Display': '16in QHD+ 240Hz'}),
        ('Beelink', 'SER {sku} Mini PC Ryzen 7', 'Desktops', 549.00, 22,
         'mini-pc,ryzen,windows-11-pro',
         {'CPU': 'AMD Ryzen 7 7735HS', 'RAM': '32GB DDR5',
          'Storage': '1TB NVMe', 'OS': 'Windows 11 Pro'}),
        ('Intel', 'NUC {sku} Pro Kit (i7)', 'Desktops', 699.00, 18,
         'nuc,bare-bones,modular',
         {'CPU': 'Intel Core i7-1360P', 'Form Factor': 'NUC',
          'Display': '4x 4K via TB4'}),
        ('Glorious', 'GMMK Pro {sku} Mechanical Keyboard', 'Computer Accessories', 169.99, 18,
         'keyboard,75-percent,gasket',
         {'Layout': '75%', 'Switches': 'Hot-swappable',
          'Body': 'Aluminum CNC'}),
        ('NZXT', 'Function {sku} Elite Keyboard', 'Computer Accessories', 199.99, 18,
         'keyboard,hotswap,linear',
         {'Layout': 'Full', 'Switches': 'Gateron Red',
          'RGB': 'Per-key'}),
        ('Endgame Gear', 'XM2w {sku} Wireless Mouse', 'Computer Accessories', 129.99, 12,
         'mouse,wireless,esports',
         {'Sensor': 'PixArt PAW3395', 'Weight': '63g',
          'Battery': '110h'}),
        ('Pulsar', 'X2 {sku} Symmetrical Wireless Mouse', 'Computer Accessories', 99.99, 12,
         'mouse,wireless,lightweight',
         {'Sensor': 'PAW3395', 'Weight': '52g',
          'DPI': '26000'}),
        ('Drop', 'Carina {sku} CTRL High-Profile', 'Computer Accessories', 199.99, 12,
         'keyboard,tkl,enthusiast',
         {'Layout': 'TKL', 'Switches': 'Hot-swappable',
          'Plate': 'Aluminum'}),
        ('Synology', 'DiskStation DS{sku}+ 4-Bay NAS', 'Storage', 559.99, 18,
         'nas,4-bay,btrfs',
         {'Bays': '4', 'RAM': '4GB ECC', 'Network': '2x 1GbE'}),
        ('QNAP', 'TS-{sku} 6-Bay NAS', 'Storage', 899.00, 18,
         'nas,6-bay,10gbe',
         {'Bays': '6', 'RAM': '16GB', 'Network': '10GbE + 2x 2.5GbE'}),
        ('WD', 'Black SN850X {sku}TB NVMe SSD', 'Storage', 169.99, 22,
         'ssd,gen4,nvme,gaming',
         {'Capacity': '2TB', 'Interface': 'PCIe Gen 4 x4',
          'Speed': '7300 MB/s'}),
        ('Gigabyte', 'AORUS FO{sku} 32U QD-OLED Monitor', 'Monitors', 1299.99, 18,
         'monitor,4k,oled,240hz',
         {'Size': '32in 4K', 'Panel': 'QD-OLED',
          'Refresh Rate': '240Hz'}),
        ('Alienware', 'AW{sku}DWF 34in OLED Monitor', 'Monitors', 1099.99, 18,
         'monitor,ultrawide,oled',
         {'Size': '34in 3440x1440', 'Panel': 'QD-OLED',
          'Refresh Rate': '165Hz'}),
    ],
    'home': [
        ('Le Creuset', 'Signature Round Dutch Oven {sku}qt', 'Cookware', 419.95, 12,
         'dutch-oven,enameled,french',
         {'Capacity': '5.5 qt', 'Material': 'Enameled cast iron',
          'Lifetime Warranty': 'Yes'}),
        ('Staub', 'La Cocotte Round {sku}qt French Oven', 'Cookware', 349.95, 12,
         'cocotte,enameled,french',
         {'Capacity': '4 qt', 'Lid': 'Self-basting spikes'}),
        ('GreenPan', 'Valencia Pro {sku}-Piece Ceramic Set', 'Cookware', 499.00, 22,
         'ceramic-nonstick,pfas-free,induction',
         {'Pieces': '11', 'Nonstick': 'Thermolon Diamond Advanced',
          'Induction': 'Yes'}),
        ('Calphalon', 'Premier Space Saving {sku}-Pc Set', 'Cookware', 299.99, 28,
         'cookware-set,stackable,nonstick',
         {'Pieces': '8', 'Saves Space': '30%',
          'Nonstick': 'Triple-layer'}),
        ('Wusthof', 'Classic Ikon {sku}-Inch Chef Knife', 'Kitchen Utensils', 199.95, 22,
         'chef-knife,german-steel,forged',
         {'Blade': '8 inch', 'Steel': 'X50CrMoV15',
          'Handle': 'Triple-rivet POM'}),
        ('Shun', 'Premier {sku}-Inch Chef Knife', 'Kitchen Utensils', 199.95, 18,
         'chef-knife,vg-max,damascus',
         {'Blade': '8 inch', 'Steel': 'VG-MAX clad',
          'Handle': 'Pakkawood'}),
        ('Global', 'G-{sku} 8-Inch Chef Knife', 'Kitchen Utensils', 169.95, 18,
         'chef-knife,japanese,stainless',
         {'Blade': '8 inch', 'Steel': 'CROMOVA 18',
          'Handle': 'Seamless stainless'}),
        ('Sodastream', 'Terra {sku} Sparkling Water Maker', 'Kitchen Appliances', 99.99, 25,
         'sparkling-water,co2,sustainable',
         {'Bottles': '1L carbonating bottle',
          'Compatible': 'Quick Connect CO2 cylinder'}),
        ('Aerogarden', 'Bounty Basic {sku} Hydroponic Garden', 'Kitchen Appliances', 199.95, 28,
         'hydroponic,grow-light,indoor',
         {'Pods': '9', 'Light': '50W LED',
          'Display': 'Touch screen'}),
        ('Joseph Joseph', 'Nest {sku}-Piece Mixing Bowl Set', 'Kitchen Utensils', 79.99, 22,
         'nesting,mixing-bowls,colander',
         {'Pieces': '9 nesting',
          'Storage': '50% less than traditional set'}),
        ('Tovolo', 'Sphere Ice Molds Set of {sku}', 'Kitchen Utensils', 14.95, 25,
         'ice-mold,sphere,whiskey',
         {'Pieces': '4', 'Sphere Size': '2.5 inch',
          'Material': 'Silicone'}),
        ('Hydro Flask', '{sku} oz Wide Mouth Water Bottle', 'Outdoor Living', 49.95, 12,
         'water-bottle,insulated,bpa-free',
         {'Capacity': '32 oz', 'Insulation': '24h cold, 12h hot',
          'Material': '18/8 pro-grade stainless'}),
        ('YETI', 'Rambler {sku} oz Tumbler MagSlider Lid', 'Outdoor Living', 38.00, 12,
         'tumbler,double-wall,magslider',
         {'Capacity': '20 oz', 'Material': '18/8 stainless',
          'Lid': 'Leak-resistant MagSlider'}),
        ('Stanley', 'Quencher H{sku}.0 FlowState Tumbler', 'Outdoor Living', 44.99, 12,
         'tumbler,straw,40oz',
         {'Capacity': '40 oz', 'Insulation': '11h hot / 2 days iced',
          'Lid': '3-position rotating'}),
        ('Owala', 'FreeSip {sku} oz Insulated Bottle', 'Outdoor Living', 32.99, 18,
         'water-bottle,freesip,insulated',
         {'Capacity': '24 oz', 'Insulation': '24h cold',
          'Material': '18/8 stainless'}),
    ],
    'fashion': [
        ('Patagonia', 'Better Sweater {sku} Fleece Jacket', 'Mens Clothing', 159.00, 12,
         'fleece,fair-trade,recycled',
         {'Material': '100% recycled polyester fleece',
          'Fair Trade': 'Sewn', 'Sizes': 'XS, S, M, L, XL, XXL'}),
        ('Patagonia', 'Nano Puff {sku} Insulated Jacket', 'Mens Clothing', 249.00, 12,
         'insulated,recycled,packable',
         {'Insulation': '60g PrimaLoft Gold Eco 55%',
          'Shell': '100% recycled polyester ripstop'}),
        ('Arc\'teryx', 'Beta {sku} GORE-TEX Shell', 'Mens Clothing', 549.00, 8,
         'rain-shell,gore-tex,3-layer',
         {'Material': 'GORE-TEX 3L', 'Helmet Compatible': 'Yes'}),
        ('The North Face', 'Thermoball Eco {sku} Vest', 'Mens Clothing', 149.00, 18,
         'vest,recycled-insulation,packable',
         {'Insulation': 'ThermoBall Eco', 'Shell': 'Recycled polyester'}),
        ('Cotopaxi', 'Fuego Hooded Down Jacket {sku}', 'Mens Clothing', 295.00, 12,
         'down,fair-trade,colorful',
         {'Insulation': '800-fill responsible down',
          'Fair Trade': 'Yes'}),
        ('Outdoor Voices', 'CloudKnit Sweatshirt Color {sku}', 'Womens Clothing', 88.00, 18,
         'sweatshirt,athleisure,soft',
         {'Material': 'CloudKnit poly/cotton blend',
          'Fit': 'Relaxed'}),
        ('Vuori', 'Performance Jogger Color {sku}', 'Mens Clothing', 89.00, 18,
         'joggers,performance,daily',
         {'Material': 'DreamKnit', 'Fit': 'Slim tapered'}),
        ('Alo', 'Airbrush High-Waist Legging Color {sku}', 'Womens Clothing', 88.00, 12,
         'leggings,seamless,yoga',
         {'Material': 'Airbrush fabric',
          'Compression': 'Medium'}),
        ('Reformation', 'Cynthia High Rise Straight Jean {sku}', 'Womens Clothing', 148.00, 12,
         'jeans,vintage,sustainable',
         {'Material': '100% organic cotton',
          'Rise': 'High', 'Sizes': '23-31'}),
        ('Everlane', "The Way-High Curve Jean Wash {sku}", 'Womens Clothing', 98.00, 18,
         'jeans,curve-fit,sustainable',
         {'Material': 'Organic cotton blend',
          'Rise': 'High curve', 'Sizes': '23-33'}),
        ('Allbirds', "Tree Runner Shoes Color {sku}", 'Shoes', 98.00, 12,
         'shoes,tencel,plant-based',
         {'Material': 'TENCEL Lyocell upper',
          'Insole': 'SweetFoam', 'Sizes': '6-14'}),
        ('On', 'Cloud{sku} Running Shoes', 'Shoes', 149.99, 12,
         'running-shoes,cloudtec,helion',
         {'Cushioning': 'CloudTec', 'Drop': '6mm',
          'Sizes': '6-14'}),
        ('New Balance', 'Fresh Foam {sku}v13 Running', 'Shoes', 144.99, 18,
         'running-shoes,fresh-foam,neutral',
         {'Cushioning': 'Fresh Foam X', 'Drop': '8mm',
          'Sizes': '6-15'}),
        ('Birkenstock', 'Arizona {sku} Soft Footbed Sandal', 'Shoes', 129.95, 12,
         'sandal,cork-footbed,classic',
         {'Footbed': 'Suede-lined cork',
          'Sizes': '36-46 EU'}),
        ('UGG', 'Classic Mini {sku} II Boot', 'Shoes', 169.95, 12,
         'boot,sheepskin,winter',
         {'Material': 'Twinface sheepskin',
          'Sole': 'Treadlite by UGG',
          'Sizes': '5-12'}),
    ],
    'beauty': [
        ('CeraVe', 'Moisturizing Cream {sku} oz Tub', 'Skincare', 19.99, 22,
         'moisturizer,ceramides,dermatologist',
         {'Volume': '19 oz', 'Skin Type': 'All / Dry',
          'Key Ingredients': 'Ceramides, hyaluronic acid'}),
        ('CeraVe', 'Hydrating Cleanser {sku} oz Bottle', 'Skincare', 16.99, 22,
         'cleanser,non-foaming,hyaluronic',
         {'Volume': '12 oz', 'Skin Type': 'Normal to Dry',
          'Key Ingredients': 'Hyaluronic acid, ceramides'}),
        ('La Roche-Posay', 'Toleriane Hydrating Cleanser {sku}oz', 'Skincare', 16.99, 18,
         'cleanser,sensitive,prebiotic',
         {'Volume': '13.5 oz', 'Skin Type': 'Sensitive',
          'Key Ingredients': 'Ceramide-3, niacinamide'}),
        ('Paula\'s Choice', 'Skin Perfecting {sku}% BHA Liquid', 'Skincare', 36.00, 12,
         'exfoliant,bha,salicylic',
         {'Volume': '4 oz', 'Active': '2% salicylic acid'}),
        ('The Ordinary', 'Niacinamide {sku}% + Zinc 1%', 'Skincare', 6.50, 30,
         'serum,niacinamide,affordable',
         {'Volume': '30 ml', 'Skin Type': 'Oily / Acne-prone'}),
        ('Skinceuticals', 'C E Ferulic {sku}ml Serum', 'Skincare', 182.00, 12,
         'vitamin-c,serum,antioxidant',
         {'Volume': '30 ml',
          'Actives': '15% L-ascorbic acid, 1% alpha tocopherol, 0.5% ferulic acid'}),
        ('Drunk Elephant', 'C-Firma Fresh Day Serum {sku}ml', 'Skincare', 80.00, 12,
         'vitamin-c,fresh-formula,clean',
         {'Volume': '30 ml',
          'Activated Vitamin C': 'L-ascorbic acid 15%'}),
        ('Kiehl\'s', 'Midnight Recovery Concentrate {sku}ml', 'Skincare', 64.00, 15,
         'oil,recovery,nighttime',
         {'Volume': '30 ml',
          'Notes': 'Evening primrose, squalane, lavender'}),
        ('Olaplex', 'No.{sku} Bond Maintenance Shampoo', 'Hair Care', 30.00, 22,
         'shampoo,bond-repair,salon',
         {'Volume': '8.5 oz', 'Hair Type': 'Damaged',
          'Bond Builder': 'Patented bis-amino'}),
        ('Drybar', 'Detox Dry Shampoo {sku}oz', 'Hair Care', 26.00, 22,
         'dry-shampoo,detox,salon',
         {'Volume': '3.5 oz', 'Hair Type': 'All',
          'Format': 'Aerosol'}),
        ('Mielle', 'Rosemary Mint Scalp Oil {sku}oz', 'Hair Care', 9.99, 22,
         'hair-oil,rosemary,scalp',
         {'Volume': '2 oz', 'Hair Type': 'All textures'}),
        ('Beautyblender', 'Original {sku} Sponge Pack', 'Makeup', 26.00, 18,
         'sponge,beauty-tool,reusable',
         {'Pack': '2', 'Material': 'Latex-free foam'}),
        ('Charlotte Tilbury', 'Pillow Talk Lipstick Shade {sku}', 'Makeup', 35.00, 12,
         'lipstick,matte,charlotte-tilbury',
         {'Finish': 'Matte', 'Volume': '0.12 oz'}),
        ('Dior', 'Backstage Glow Face Palette Shade {sku}', 'Makeup', 60.00, 12,
         'highlighter,palette,dior',
         {'Pans': '4', 'Finish': 'Glow / Bronze'}),
        ('Estée Lauder', 'Advanced Night Repair Serum {sku}ml', 'Skincare', 105.00, 12,
         'serum,anti-aging,multi-action',
         {'Volume': '50 ml',
          'Actives': 'ChronoluxCB technology'}),
    ],
    'sports': [
        ('Garmin', 'Edge {sku} GPS Cycling Computer', 'Cycling', 599.99, 18,
         'cycling-computer,gps,navigation',
         {'Display': '3.5in color touch',
          'Battery': '20h GPS', 'Navigation': 'Turn-by-turn'}),
        ('Wahoo', 'KICKR {sku} Smart Trainer', 'Cycling', 1299.99, 12,
         'smart-trainer,direct-drive,zwift',
         {'Resistance': '2200W', 'Accuracy': '±1%',
          'Compatible': 'Zwift, Trainerroad, Rouvy'}),
        ('Polar', 'Vantage {sku} Multisport Watch', 'Fitness', 599.95, 18,
         'multisport,gps,recovery',
         {'GPS': 'Dual-frequency',
          'Battery': '7 days smart / 60h GPS',
          'Sport Profiles': '150+'}),
        ('Coros', 'Pace {sku} GPS Sport Watch', 'Fitness', 349.00, 12,
         'gps,running,triathlon',
         {'Display': '1.2in AMOLED',
          'Battery': '24 days smart / 38h GPS',
          'Sport Profiles': '20+'}),
        ('Yeti', 'Loadout GoBox {sku} Gear Case', 'Outdoor Living', 249.99, 12,
         'gear-case,modular,outdoor',
         {'Capacity': '30L', 'Material': 'High-impact polymer'}),
        ('REI Co-op', 'Trail {sku} Daypack 25L', 'Outdoor Living', 89.95, 18,
         'daypack,hiking,trail',
         {'Capacity': '25L', 'Material': '100% recycled poly ripstop',
          'Hydration Compatible': 'Yes'}),
        ('Osprey', 'Atmos AG {sku} Backpacking Pack 65', 'Outdoor Living', 339.95, 12,
         'backpack,65l,anti-gravity',
         {'Capacity': '65L', 'Suspension': 'Anti-Gravity 3D mesh',
          'Trampoline Back': 'Yes'}),
        ('Hydro Flask', 'Trail Series {sku}L Lightweight Bottle', 'Outdoor Living', 49.95, 12,
         'water-bottle,trail,insulated',
         {'Capacity': '24 oz',
          'Insulation': 'TempShield single-wall lightweight'}),
        ('Black Diamond', 'Spot {sku} Headlamp 400 lumens', 'Outdoor Living', 49.95, 18,
         'headlamp,led,outdoor',
         {'Max Output': '400 lumens',
          'Beam Distance': '100m',
          'IPX': '8 (waterproof)'}),
        ('MSR', 'PocketRocket {sku} Stove', 'Outdoor Living', 49.95, 18,
         'stove,canister,ultralight',
         {'Weight': '2.6 oz',
          'Boil Time': '3.5 min per liter'}),
        ('Therm-a-Rest', 'NeoAir {sku}Lite Sleeping Pad', 'Outdoor Living', 199.95, 12,
         'sleeping-pad,ultralight,r-value-4.5',
         {'R-Value': '4.5',
          'Weight': '15 oz Regular',
          'Pack Size': '4x9 in'}),
        ('Helinox', 'Chair {sku} Camp Chair', 'Outdoor Living', 149.95, 12,
         'camp-chair,lightweight,packable',
         {'Weight': '1.7 lb',
          'Capacity': '320 lb',
          'Material': 'Aluminum + ripstop'}),
        ('Bauer', 'X-{sku} Ice Hockey Stick', 'Hockey', 299.99, 12,
         'hockey-stick,senior,carbon',
         {'Material': 'Carbon composite',
          'Flex': '77',
          'Hand': 'Right / Left'}),
        ('Easton', 'ADV {sku} BBCOR Bat', 'Baseball', 449.95, 12,
         'bbcor,baseball-bat,composite',
         {'Material': '2-piece composite',
          'Length-to-Weight': '-3'}),
        ('Wilson', 'A2000 {sku} 11.5 Glove', 'Baseball', 299.95, 12,
         'glove,leather,a2000',
         {'Size': '11.5 inch',
          'Material': 'Pro Stock Leather',
          'Web': 'H-Web'}),
    ],
    'toys': [
        ('Magna-Tiles', 'Clear Colors {sku}-Piece Set', 'Building Sets', 119.99, 18,
         'magnetic,stem,clear',
         {'Pieces': '100', 'Age': '3+',
          'Magnets': 'BPA-free safety'}),
        ('Melissa & Doug', 'Wooden Activity Cube {sku}', 'Educational', 49.99, 22,
         'wooden,sensory,toddler',
         {'Material': 'Sustainably-harvested wood',
          'Age': '12-36 months'}),
        ('Schleich', 'World of History {sku} Castle Set', 'Action Figures', 89.99, 18,
         'figurine,castle,collectible',
         {'Pieces': '23',
          'Age': '5+',
          'Hand-painted': 'Yes'}),
        ('Plan Toys', 'Sustainable Wood Tea Set {sku}', 'Educational', 29.99, 12,
         'wooden,tea-set,sustainable',
         {'Material': 'Rubberwood + soy-based dye',
          'Age': '3+'}),
        ('Tonies', 'Toniebox {sku} Audio Player Starter', 'Educational', 99.99, 12,
         'audio,interactive,screen-free',
         {'Age': '3+',
          'Storage': '500+ hours',
          'Includes': '1 Tonie character'}),
        ('Yoto', 'Player Mini {sku} Audio Box', 'Educational', 79.99, 12,
         'audio,bluetooth,screen-free',
         {'Age': '3-12',
          'Battery': '20h playback',
          'Cards': 'Sold separately'}),
        ('LEGO', 'Botanical Collection Bouquet {sku}', 'Building Sets', 59.99, 18,
         'lego,botanical,adult',
         {'Pieces': '756',
          'Age': '18+',
          'Theme': 'Botanical Collection'}),
        ('LEGO', 'Star Wars UCS {sku} Display Set', 'Building Sets', 849.99, 8,
         'lego,star-wars,ucs',
         {'Pieces': '7541',
          'Age': '18+',
          'Theme': 'Star Wars UCS'}),
        ('LEGO', 'Speed Champions {sku} Race Car', 'Building Sets', 24.99, 18,
         'lego,speed-champions,car',
         {'Pieces': '275',
          'Age': '8+',
          'Theme': 'Speed Champions'}),
        ('Bandai', 'Tamagotchi Pix {sku} Virtual Pet', 'Collectibles', 59.99, 18,
         'virtual-pet,collectible,90s',
         {'Display': 'Color screen',
          'Age': '8+'}),
        ('Crayola', 'Inspiration Art Case {sku} Pieces', 'Educational', 24.99, 22,
         'art-supplies,140-piece,kids',
         {'Pieces': '140',
          'Age': '5+',
          'Storage': 'Foldable case'}),
        ('Spin Master', 'Hatchimals Pixies Crystal Flyers {sku}', 'Collectibles', 24.99, 22,
         'hatchimals,collectible,flying',
         {'Age': '6+',
          'Battery': 'USB rechargeable'}),
        ('Hasbro', 'Nerf Elite 2.0 {sku} Commander', 'Outdoor Toys', 24.99, 22,
         'nerf,blaster,age-8',
         {'Darts': '12',
          'Age': '8+',
          'Range': '90 ft'}),
        ('Beyblade', 'Burst QuadDrive {sku} Battle Set', 'Action Figures', 49.99, 18,
         'beyblade,battle,collectible',
         {'Tops': '2',
          'Age': '8+',
          'Stadium': 'Included'}),
        ('Pokemon TCG', 'Scarlet Violet Booster Bundle {sku}', 'Collectibles', 26.95, 12,
         'pokemon,tcg,booster',
         {'Booster Packs': '6',
          'Age': '6+',
          'Set': 'Scarlet & Violet'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry — call from seed_extras.run_extras AFTER seed_polish.
# ---------------------------------------------------------------------------

def seed_r5(db, Product):
    """R5 polish: bring catalog from ~5500 to 8000+. Idempotent."""
    if Product.query.count() >= 7800:
        return 0
    added = 0

    # 1) Re-run all known templates (R2 SKU_TEMPLATES + R4 R4_NEW_TEMPLATES)
    #    with R5_SUFFIXES — each fresh suffix unlocks a new slug.
    combined = []
    for cat, tpls in SKU_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R4_NEW_TEMPLATES.items():
        combined.append((cat, tpls))

    for category, templates in combined:
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(22):
                # multiplier 1 is co-prime with len(R5_SUFFIXES)=28 → max distinct
                # suffixes per template within the loop bound.
                sfx_idx = (t_idx * 9 + variant_idx) % len(R5_SUFFIXES)
                idx = sfx_idx + 9000 + variant_idx * 53 + t_idx * 17
                data = _build_r5_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) Add R5-only templates × 20 variants — completely new long-tail SKUs.
    for category, templates in R5_NEW_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(20):
                sfx_idx = (t_idx * 5 + variant_idx) % len(R5_SUFFIXES)
                idx = sfx_idx + 20000 + variant_idx * 37 + t_idx * 19
                data = _build_r5_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    return added


# ---------------------------------------------------------------------------
# Builder — adds R5 quality fields on top of the R4 generator.
# ---------------------------------------------------------------------------

def _build_r5_sku(idx, template, category, pool, sfx_idx):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R5_SUFFIXES[sfx_idx % len(R5_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    jitter = -0.10 + ((idx * 41) % 21) / 100.0
    price = round(base_price * (1 + jitter), 2)
    list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.9 + ((idx * 29) % 100) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 60 + (idx * 199) % 26000
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
    gallery = [pool[(idx + j * 19) % len(pool)] for j in range(8)] if pool else []

    # --- R5 quality fields (deterministic from idx/sfx_idx) ---
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
        age_tag = AGE_BUCKETS[(idx + sfx_idx) % len(AGE_BUCKETS)]

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

    # Sold-out coverage: deterministic ~7% with stock=0 to seed
    # "Currently unavailable" UX + out-of-stock alternative recs.
    stock_seed = (idx * 19 + sfx_idx * 11) % 100
    if stock_seed < 7:
        stock = 0
    else:
        stock = 15 + (idx * 23 + int(rating * 10)) % 380

    # --- specs additions for product detail readability ---
    specs['Climate Pledge Friendly'] = 'Yes' if is_climate_pledge else 'No'
    specs['Recyclable Packaging'] = 'Yes' if is_recyclable_pkg else 'No'
    # Convert "made-in-usa" -> "United States" for human reading
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
        specs['Age Range'] = age_tag.replace('age-', '').replace('-', '–') + (' years' if 'plus' not in age_tag else ' years')

    description = (
        f"{name} by {brand}. {subcat} engineered for everyday performance. "
        + " ".join(f"{k}: {v}." for k, v in specs.items()
                   if k not in ('Brand', 'Color'))
    )
    features = [f"{k}: {v}" for k, v in list(specs.items())[:7]]
    if is_climate_pledge:
        features.append('Climate Pledge Friendly — certified sustainability')
    if is_one_day_eligible:
        features.append('Eligible for FREE One-Day Shipping')
    if is_sns:
        features.append('Subscribe & Save — up to 15% off recurring orders')

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
