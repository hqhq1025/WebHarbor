#!/usr/bin/env python3
"""R6 polish pass — push catalog from ~12.3k to 18000+.

What this adds on top of R5 (seed_r5.py):

  • Distinct R6_SUFFIXES (32 fresh codenames) — no collision with R2/R4/R5.
  • R6_NEW_TEMPLATES — brand-new (brand, family) tuples for long-tail
    categories that R5 didn't cover (automotive, garden, pet, baby,
    office, music instruments, luggage, eyewear, kitchen-prep, lighting).
  • Replays every prior template pool (SKU + R4 + R5) with R6_SUFFIXES so
    each fresh suffix unlocks a new slug — no DB col change required.
  • Carries every R5 quality field (climate-pledge, made-in, recyclable,
    age-range, sns, one-day-shipping, small-business) plus R6 additions:
        - low-stock urgency (deterministic ~12% of SKUs get stock 1-4 so
          the "Only N left" banner fires; separate from R5 sold-out 7%)
        - notify-eligible (every stock==0 SKU is notify-when-back eligible).

Deterministic: every numeric / boolean derived from idx + sfx_idx, so
rebuilds stay byte-identical. No datetime.now() / random without seed.

Idempotent — exits early when Product.count() already >= 17500 (R6 floor).
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


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Distinct codename pool — no overlap with R2 / R4 / R5 suffix lists.
R6_SUFFIXES = [
    'Ascent', 'Boulder', 'Cobblestone', 'Daybreak', 'Evergreen', 'Flint',
    'Garnet', 'Heron', 'Iris', 'Juniper', 'Kestrel', 'Linden', 'Marigold',
    'Nightshade', 'Obsidian', 'Pinecone', 'Quartzite', 'Redwood', 'Sandstone',
    'Tidewater', 'Umbra', 'Vellum', 'Walnut', 'Xenon', 'Yucca', 'Zephyr',
    'Alpine', 'Bramble', 'Citrine', 'Driftstone', 'Ember-X', 'Foxglove',
]


# ---------------------------------------------------------------------------
# R6-only templates — long-tail categories R4/R5 didn't lean into.
# Shape matches _build_generic_sku in seed_bulk:
#   (brand, name_tpl_with_{sku}, subcategory, base_price, list_uplift_pct,
#    tag_csv, specs_template)
# ---------------------------------------------------------------------------

R6_NEW_TEMPLATES = {
    'electronics': [
        ('JBL', 'Charge {sku} Portable Bluetooth Speaker IP67', 'Speakers', 179.95, 22,
         'speaker,bluetooth,waterproof',
         {'Output': '40W', 'Battery': '20h', 'Bluetooth': '5.3'}),
        ('Bose', 'SoundLink Flex {sku} Bluetooth Speaker', 'Speakers', 149.00, 18,
         'speaker,bluetooth,portable',
         {'Battery': '12h', 'Waterproof': 'IP67', 'Weight': '1.3 lb'}),
        ('Marshall', 'Emberton {sku} II Portable Speaker', 'Speakers', 169.99, 15,
         'speaker,bluetooth,vintage',
         {'Battery': '30h', 'Bluetooth': '5.1', 'Charging': 'USB-C'}),
        ('Sennheiser', 'Momentum {sku} 4 Wireless Headphones', 'Headphones', 379.95, 16,
         'headphones,anc,wireless',
         {'Battery': '60h', 'ANC': 'Adaptive', 'Driver': '42mm'}),
        ('Bowers & Wilkins', 'Px{sku} S2 Wireless Headphones', 'Headphones', 399.00, 14,
         'headphones,anc,hifi',
         {'Driver': '40mm Carbon Cone', 'ANC': 'Adaptive', 'Battery': '30h'}),
        ('GoPro', 'HERO{sku} Black Action Camera 5.3K', 'Cameras', 399.99, 18,
         'action-camera,5k,hypersmooth',
         {'Resolution': '5.3K60', 'Waterproof': '33ft', 'Stabilization': 'HyperSmooth 6.0'}),
        ('DJI', 'Pocket {sku} 3 Gimbal Camera', 'Cameras', 519.00, 16,
         'gimbal,camera,vlog',
         {'Sensor': '1in CMOS', 'Video': '4K120p', 'Display': '2in OLED'}),
        ('Canon', 'PowerShot G{sku} X Mark III Compact', 'Cameras', 1099.00, 14,
         'compact-camera,1in,zoom',
         {'Sensor': '1in 20.1MP', 'Zoom': '24-120mm equiv', 'Video': '4K30p'}),
        ('Roborock', 'S{sku} MaxV Ultra Robot Vacuum + Mop', 'Smart Home', 1599.99, 22,
         'robot-vacuum,lidar,self-empty',
         {'Suction': '7000Pa', 'Navigation': 'LiDAR + AI camera', 'Dock': 'Auto empty + wash'}),
        ('Aqara', 'Smart Hub {sku} M3 Matter Thread', 'Smart Home', 129.99, 18,
         'smart-hub,matter,thread',
         {'Standards': 'Matter, Thread, Zigbee, BLE', 'Ethernet': 'Gigabit'}),
        ('Govee', 'Glide {sku} Hexagon Light Panels 6-pack', 'Smart Home', 119.99, 25,
         'smart-lighting,rgb,wifi',
         {'Panels': '6 hex', 'Voice': 'Alexa, Google', 'App': 'Govee Home'}),
        ('Tessan', 'Surge Protector {sku} 12-Outlet Power Strip', 'Phone Accessories', 39.99, 22,
         'surge-protector,usb-c,desktop',
         {'Outlets': '12 AC', 'USB-C': '2 ports 20W', 'Cord': '6ft'}),
        ('Ugreen', 'Nexode {sku} 200W USB-C Charger', 'Phone Accessories', 149.99, 18,
         'charger,gan,200w',
         {'Ports': '6 (4 USB-C, 2 USB-A)', 'Total Output': '200W', 'GaN': 'Yes'}),
        ('Satechi', 'Trio Wireless Charger {sku} for Apple', 'Phone Accessories', 119.99, 18,
         'wireless-charger,magsafe,apple',
         {'Devices': 'iPhone + AirPods + Apple Watch', 'Standard': 'MagSafe-compatible'}),
        ('SwitchBot', 'Lock {sku} Pro Smart Lock + Keypad', 'Smart Home', 159.99, 22,
         'smart-lock,fingerprint,keyless',
         {'Unlock': 'Fingerprint / PIN / NFC / App', 'Power': '4x AAA (10mo)'}),
    ],
    'computers': [
        ('Asus', 'ProArt StudioBook {sku} OLED H7604', 'Laptops', 2799.00, 12,
         'workstation,oled,creator',
         {'CPU': 'Intel Core i9-13980HX', 'GPU': 'RTX 4070 Laptop',
          'Display': '16in 3.2K OLED 120Hz', 'RAM': '32GB DDR5'}),
        ('MSI', 'Titan GT{sku} Pro HX 17 Gaming', 'Laptops', 3999.99, 10,
         'gaming,desktop-replacement,rtx-4090',
         {'CPU': 'Intel Core i9-14900HX', 'GPU': 'RTX 4090 Laptop',
          'Display': '17in 4K Mini-LED 144Hz', 'RAM': '64GB DDR5'}),
        ('Razer', 'Blade {sku} 16 OLED Gaming Laptop', 'Laptops', 2899.99, 12,
         'gaming,oled,rtx',
         {'CPU': 'Intel Core i9-14900HX', 'GPU': 'RTX 4080 Laptop',
          'Display': '16in QHD+ OLED 240Hz', 'RAM': '32GB DDR5'}),
        ('Minisforum', 'UM{sku} Mini PC Ryzen 9', 'Desktops', 749.00, 18,
         'mini-pc,ryzen-9,oculink',
         {'CPU': 'AMD Ryzen 9 7940HS', 'RAM': '32GB DDR5',
          'Storage': '1TB NVMe', 'Ports': 'OCuLink + 2.5GbE'}),
        ('GMKtec', 'NucBox {sku} K9 i9 Mini PC', 'Desktops', 899.00, 18,
         'mini-pc,core-i9,2.5gbe',
         {'CPU': 'Intel Core i9-12900HK', 'RAM': '32GB DDR4',
          'Storage': '1TB NVMe', 'Display': 'Quad 4K'}),
        ('Keychron', 'Q{sku} Max Wireless Mechanical Keyboard', 'Computer Accessories', 219.00, 14,
         'keyboard,wireless,qmk',
         {'Layout': '75%', 'Switches': 'Hot-swap K Pro', 'Wireless': '2.4GHz + BT5.1'}),
        ('Wooting', 'Two HE {sku} Analog Keyboard', 'Computer Accessories', 199.00, 12,
         'keyboard,analog,hall-effect',
         {'Switches': 'Lekker Hall-effect', 'Polling': '8000Hz', 'Layout': 'Full'}),
        ('Mountain', 'Everest 60 {sku} Modular Keyboard', 'Computer Accessories', 179.99, 18,
         'keyboard,modular,60-percent',
         {'Layout': '60% modular', 'Switches': 'Cherry MX hot-swap'}),
        ('Vaxee', 'Outset {sku} Symmetric Wireless Mouse', 'Computer Accessories', 89.99, 18,
         'mouse,wireless,esports',
         {'Sensor': 'PixArt 3395', 'Weight': '65g', 'Battery': '90h'}),
        ('Lamzu', 'Atlantis OG {sku} V2 Pro Wireless', 'Computer Accessories', 159.99, 12,
         'mouse,wireless,4khz',
         {'Sensor': 'PAW3395', 'Weight': '52g', 'Polling': '4000Hz'}),
        ('TerraMaster', 'F{sku}-424 Max 4-Bay NAS', 'Storage', 999.00, 18,
         'nas,4-bay,10gbe',
         {'Bays': '4', 'CPU': 'Intel i5-1235U', 'RAM': '16GB DDR5'}),
        ('Asustor', 'Lockerstor {sku} Gen3 8-Bay NAS', 'Storage', 1599.00, 16,
         'nas,8-bay,m.2-nvme',
         {'Bays': '8 SATA + 4 NVMe', 'Network': '2x 10GbE', 'CPU': 'Intel'}),
        ('Crucial', 'T{sku}05 Pro 4TB Gen5 NVMe SSD', 'Storage', 599.99, 22,
         'ssd,gen5,nvme,workstation',
         {'Capacity': '4TB', 'Speed': '14500 MB/s', 'Interface': 'PCIe Gen 5'}),
        ('LG', 'UltraGear {sku} 45 OLED Curved Monitor', 'Monitors', 1699.99, 18,
         'monitor,oled,ultrawide,240hz',
         {'Size': '45in 3440x1440', 'Panel': 'WOLED', 'Refresh': '240Hz'}),
        ('Samsung', 'Odyssey OLED G{sku}5 49in Dual QHD', 'Monitors', 1499.99, 22,
         'monitor,49-inch,super-ultrawide,oled',
         {'Size': '49in 5120x1440', 'Panel': 'QD-OLED', 'Refresh': '240Hz'}),
    ],
    'home': [
        ('All-Clad', 'D3 Stainless {sku}-Piece Cookware Set', 'Cookware', 699.99, 18,
         'stainless,tri-ply,cookware-set',
         {'Pieces': '10', 'Material': 'Tri-ply stainless', 'Induction': 'Yes'}),
        ('Made In', 'Stainless {sku} 10pc Cookware Set', 'Cookware', 999.00, 12,
         'stainless,5-ply,chef',
         {'Pieces': '10', 'Material': '5-ply stainless', 'Made In': 'Italy/France'}),
        ('OXO', 'Good Grips {sku}-Piece POP Container Set', 'Storage', 159.99, 22,
         'food-storage,airtight,modular',
         {'Pieces': '10', 'Seal': 'Airtight push-button', 'Dishwasher Safe': 'Lids'}),
        ('Ninja', 'Foodi {sku} XL Pro Air Fryer 8-qt', 'Appliances', 199.99, 22,
         'air-fryer,xl,dual-zone',
         {'Capacity': '8 qt', 'Functions': '6', 'Wattage': '1700W'}),
        ('Cuisinart', 'Bread Maker {sku} CBK-310 12-Hour', 'Appliances', 169.99, 18,
         'bread-maker,gluten-free,2lb',
         {'Loaf Size': '1, 1.5, 2 lb', 'Programs': '16', 'Delay': '13h'}),
        ('Vitamix', 'Ascent {sku} A3500 Smart Blender', 'Appliances', 649.95, 12,
         'blender,smart,programs',
         {'Motor': '2.2 HP', 'Container': '64 oz', 'Programs': '5'}),
        ('Casper', 'Original {sku} Mattress Queen', 'Furniture', 1295.00, 14,
         'mattress,foam,queen',
         {'Size': 'Queen', 'Layers': '4 foam', 'Trial': '100 nights'}),
        ('Tuft & Needle', 'Mint {sku} Hybrid Mattress King', 'Furniture', 1495.00, 14,
         'mattress,hybrid,king',
         {'Size': 'King', 'Coils': 'Pocket', 'Trial': '100 nights'}),
        ('Pottery Barn', 'PB Comfort Roll Arm {sku} Sofa', 'Furniture', 2199.00, 12,
         'sofa,upholstered,living-room',
         {'Length': '85in', 'Frame': 'Kiln-dried hardwood', 'Cushions': 'Down-blend'}),
        ('West Elm', 'Andes {sku} L-Shape Sectional', 'Furniture', 2999.00, 12,
         'sectional,modular,modern',
         {'Configuration': 'L-shape 110in', 'Frame': 'Engineered hardwood'}),
        ('Brooklinen', 'Luxe Sateen Sheet Set {sku} King', 'Bedding', 199.00, 16,
         'sheets,sateen,400-thread',
         {'Material': '100% long-staple cotton', 'Thread Count': '480'}),
        ('Parachute', 'Linen Duvet Cover {sku} Queen', 'Bedding', 229.00, 15,
         'duvet,linen,european',
         {'Material': 'European flax linen', 'Closure': 'Coconut buttons'}),
        ('Dyson', 'V{sku}5 Detect Submarine Cordless Vacuum', 'Appliances', 949.99, 12,
         'cordless-vacuum,wet-dry,laser',
         {'Battery': '70 min', 'Detect': 'Laser dust + acoustic count'}),
        ('Shark', 'AI Ultra {sku} Robot Vacuum + Mop', 'Appliances', 599.99, 22,
         'robot-vacuum,self-empty,mop',
         {'Suction': '4000Pa', 'Mapping': 'AI laser', 'Bin': '60-day base'}),
        ('Breville', 'Smart Oven Air Fryer Pro {sku} Plus', 'Appliances', 449.95, 18,
         'toaster-oven,air-fryer,countertop',
         {'Functions': '13', 'Capacity': '1 cu ft', 'Element IQ': 'Yes'}),
    ],
    'fashion': [
        ('Patagonia', 'Better Sweater {sku} Quarter-Zip', 'Mens Clothing', 119.00, 14,
         'fleece,quarter-zip,recycled',
         {'Material': '100% recycled polyester', 'Fit': 'Regular', 'Origin': 'Fair Trade'}),
        ('The North Face', 'ThermoBall {sku} Eco Jacket', 'Mens Clothing', 230.00, 18,
         'jacket,insulated,recycled',
         {'Insulation': 'ThermoBall Eco', 'Fill': '100% recycled', 'Hood': 'Stowable'}),
        ('Arc\'teryx', 'Beta AR {sku} Jacket Gore-Tex', 'Mens Clothing', 599.00, 12,
         'shell,gore-tex,alpine',
         {'Membrane': 'GORE-TEX Pro', 'Hood': 'Helmet-compatible'}),
        ('Lululemon', 'Align {sku} High-Rise Pant 25in', 'Womens Clothing', 98.00, 12,
         'leggings,yoga,high-rise',
         {'Fabric': 'Nulu', 'Rise': 'High', 'Inseam': '25in'}),
        ('Athleta', 'Salutation Stash {sku} Pocket Tight', 'Womens Clothing', 89.00, 18,
         'leggings,pockets,quick-dry',
         {'Fabric': 'Powervita', 'Pockets': '2 side + waist', 'Rise': 'High'}),
        ('Vuori', 'Sunday Performance {sku} Jogger', 'Mens Clothing', 89.00, 16,
         'joggers,performance,casual',
         {'Fabric': 'DreamKnit', 'Pockets': '3', 'Fit': 'Relaxed-tapered'}),
        ('Allbirds', 'Wool Runner Mizzle {sku} Sneaker', 'Shoes', 135.00, 14,
         'sneakers,wool,water-repellent',
         {'Upper': 'ZQ Merino + Puddle Guard', 'Sole': 'SweetFoam', 'Vegan': 'Yes'}),
        ('Hoka', 'Bondi {sku} 8 Running Shoe', 'Shoes', 165.00, 12,
         'running,cushion,max-stack',
         {'Stack Height': '33mm heel / 29mm forefoot', 'Drop': '4mm'}),
        ('Brooks', 'Ghost {sku} 16 Neutral Running Shoe', 'Shoes', 140.00, 14,
         'running,neutral,daily-trainer',
         {'Stack': '36/24', 'Drop': '12mm', 'Cushion': 'DNA Loft v3'}),
        ('Cole Haan', 'GrandPrø {sku} Topspin Sneaker', 'Shoes', 130.00, 18,
         'sneaker,casual,leather',
         {'Upper': 'Leather', 'Lining': 'Microfiber', 'Sole': 'Grand.OS'}),
        ('Mejuri', 'Bold {sku} Hoop Earrings 14k Gold-Vermeil', 'Jewelry', 75.00, 18,
         'earrings,gold-vermeil,hoops',
         {'Material': '14k gold vermeil', 'Diameter': '20mm'}),
        ('Catbird', 'Threadbare {sku} Stacking Ring 14k', 'Jewelry', 178.00, 14,
         'ring,stacking,solid-gold',
         {'Material': '14k yellow gold', 'Width': '1.2mm'}),
        ('Ray-Ban', 'Aviator Classic {sku} RB3025 Polarized', 'Accessories', 211.00, 15,
         'sunglasses,polarized,classic',
         {'Lens': 'G-15 polarized', 'Frame': 'Metal', 'Size': '58mm'}),
        ('Warby Parker', 'Percey {sku} Optical Frames', 'Accessories', 95.00, 18,
         'eyeglasses,optical,acetate',
         {'Material': 'Cellulose acetate', 'Includes': 'Anti-glare lenses'}),
        ('Coach', 'Tabby {sku} Shoulder Bag 26', 'Accessories', 495.00, 12,
         'handbag,leather,signature',
         {'Material': 'Refined calf leather', 'Closure': 'Magnetic kissing-lock'}),
    ],
    'books': [
        ('Brandon Sanderson', 'The Way of Kings {sku} Anniversary Edition', 'Fiction', 32.99, 30,
         'epic-fantasy,sanderson,stormlight',
         {'Pages': '1280', 'Series': 'Stormlight Archive'}),
        ('R.F. Kuang', 'Babel {sku} or the Necessity of Violence', 'Fiction', 27.99, 28,
         'fantasy,alt-history,oxford',
         {'Pages': '560', 'Awards': 'Nebula winner'}),
        ('Bonnie Garmus', 'Lessons in Chemistry {sku}', 'Fiction', 16.99, 35,
         'fiction,women,1960s',
         {'Pages': '400', 'Award': 'GMA Book Club'}),
        ('Hernan Diaz', 'Trust {sku} A Novel', 'Fiction', 17.99, 30,
         'historical-fiction,pulitzer',
         {'Pages': '402', 'Award': 'Pulitzer 2023'}),
        ('Stephanie Land', 'Class {sku} A Memoir', 'Biography', 18.99, 28,
         'memoir,poverty,education',
         {'Pages': '336', 'Format': 'Hardcover'}),
        ('Walter Isaacson', 'Elon Musk {sku} Authorized Biography', 'Biography', 35.00, 22,
         'biography,tech,2023',
         {'Pages': '688', 'Format': 'Hardcover'}),
        ('Yuval Noah Harari', 'Nexus {sku} A Brief History of Information', 'History', 35.00, 25,
         'history,information,ai',
         {'Pages': '512', 'Year': '2024'}),
        ('Andrew Huberman', 'Protocols {sku} Operating Manual for the Body', 'Self-Help', 32.00, 25,
         'health,science,neuroscience',
         {'Pages': '352', 'Format': 'Hardcover'}),
        ('Cal Newport', 'Slow Productivity {sku} Lost Art of Accomplishment', 'Self-Help', 28.00, 28,
         'productivity,work,career',
         {'Pages': '256', 'Year': '2024'}),
        ('Morgan Housel', 'Same as Ever {sku} Guide to What Never Changes', 'Business', 28.00, 28,
         'finance,psychology,behavior',
         {'Pages': '240', 'Year': '2023'}),
        ('Marc Levinson', 'Outside the Box {sku} How Globalization Changed', 'Business', 29.95, 30,
         'globalization,economics,history',
         {'Pages': '352', 'Publisher': 'Princeton'}),
        ('Robert Bjork', 'Deep Learning {sku} Comprehensive Reference', 'Programming', 64.99, 25,
         'machine-learning,ai,textbook',
         {'Pages': '800', 'Edition': '3rd'}),
        ('Aurelien Geron', 'Hands-On ML {sku} Scikit-Learn, Keras, TensorFlow', 'Programming', 79.99, 22,
         'machine-learning,python,oreilly',
         {'Pages': '850', 'Edition': '3rd'}),
        ('Suzanne Collins', 'Ballad of Songbirds {sku} Hunger Games Prequel', 'Young Adult', 14.99, 35,
         'dystopian,ya,hunger-games',
         {'Pages': '528', 'Series': 'Hunger Games 0'}),
        ('Sarah J. Maas', 'A Court of {sku} and Ruin Hardcover', 'Fiction', 28.99, 25,
         'fantasy-romance,maas,acotar',
         {'Pages': '720', 'Series': 'ACOTAR'}),
    ],
    'beauty': [
        ('Drunk Elephant', 'C-Firma {sku} Day Serum 30ml', 'Skincare', 80.00, 18,
         'vitamin-c,serum,brightening',
         {'Volume': '30ml', 'Key Actives': '15% L-Ascorbic + Ferulic + Vit E'}),
        ('The Ordinary', 'Niacinamide {sku} 10% + Zinc 1%', 'Skincare', 8.50, 25,
         'niacinamide,zinc,oily-skin',
         {'Volume': '30ml', 'pH': '5.5-6.5'}),
        ('Paula\'s Choice', 'Skin Perfecting BHA {sku} 2% Liquid', 'Skincare', 35.00, 18,
         'bha,exfoliant,salicylic',
         {'Volume': '118ml', 'Key Active': '2% salicylic'}),
        ('Tatcha', 'Dewy Skin Cream {sku} 50ml Refillable', 'Skincare', 72.00, 14,
         'moisturizer,hydration,plumping',
         {'Volume': '50ml', 'Refill': 'Yes (separate pod)'}),
        ('Augustinus Bader', 'The Rich Cream {sku} 50ml TFC8', 'Skincare', 295.00, 12,
         'luxury,moisturizer,renewal',
         {'Volume': '50ml', 'Technology': 'TFC8'}),
        ('Olaplex', 'No.{sku} Bond Maintenance Shampoo', 'Hair Care', 30.00, 22,
         'shampoo,bond-repair,salon',
         {'Volume': '250ml', 'Use': 'Damaged hair'}),
        ('Briogeo', 'Don\'t Despair, Repair {sku} Mask 235ml', 'Hair Care', 38.00, 22,
         'hair-mask,deep-conditioning,clean',
         {'Volume': '235ml', 'Free Of': 'Sulfates, parabens'}),
        ('Charlotte Tilbury', 'Pillow Talk {sku} Lipstick Matte', 'Makeup', 38.00, 18,
         'lipstick,matte,nude-pink',
         {'Shade': 'Pillow Talk Original', 'Finish': 'Matte'}),
        ('Rare Beauty', 'Soft Pinch Liquid Blush {sku} 7.5ml', 'Makeup', 23.00, 22,
         'liquid-blush,buildable,vegan',
         {'Volume': '7.5ml', 'Finish': 'Dewy'}),
        ('Glossier', 'You Eau de Parfum {sku} 50ml', 'Fragrance', 78.00, 22,
         'fragrance,clean,musk',
         {'Volume': '50ml', 'Notes': 'Iris, ambrette, pink pepper'}),
        ('Le Labo', 'Santal {sku} 33 Eau de Parfum 50ml', 'Fragrance', 215.00, 12,
         'fragrance,niche,sandalwood',
         {'Volume': '50ml', 'Family': 'Woody amber'}),
        ('Dyson', 'Airwrap Multi-Styler {sku} Complete', 'Hair Care', 599.99, 14,
         'styler,hair-tool,multi',
         {'Attachments': '6', 'Coanda': 'Yes'}),
        ('Maison Margiela', 'REPLICA Jazz Club {sku} EDT', 'Fragrance', 145.00, 14,
         'fragrance,unisex,replica',
         {'Volume': '100ml', 'Notes': 'Tobacco, rum, vanilla'}),
        ('NARS', 'Radiant Creamy Concealer {sku} Custard', 'Makeup', 32.00, 18,
         'concealer,creamy,longwear',
         {'Volume': '6ml', 'Coverage': 'Medium-buildable'}),
        ('Jo Malone', 'Wood Sage & Sea Salt {sku} Cologne', 'Fragrance', 158.00, 14,
         'cologne,citrus,marine',
         {'Volume': '100ml', 'Notes': 'Ambrette seeds, sea salt, sage'}),
    ],
    'sports': [
        ('Yeti', 'Tundra {sku} 45 Hard Cooler', 'Outdoor', 350.00, 16,
         'cooler,bear-proof,ice-retention',
         {'Capacity': '37 qt', 'Ice Retention': '7+ days'}),
        ('RTIC', 'Ultra-Light {sku} 52 Quart Cooler', 'Outdoor', 199.99, 18,
         'cooler,lightweight,affordable',
         {'Capacity': '52 qt', 'Weight': '23 lb'}),
        ('Black Diamond', 'Storm {sku} 500-R Headlamp', 'Outdoor', 59.95, 22,
         'headlamp,rechargeable,500-lumen',
         {'Lumens': '500', 'Battery': 'USB rechargeable', 'Waterproof': 'IPX7'}),
        ('Petzl', 'Actik Core {sku} Headlamp 600 Lumen', 'Outdoor', 69.95, 18,
         'headlamp,rechargeable,backpacking',
         {'Lumens': '600', 'Battery': 'Hybrid (Core + AAA)'}),
        ('Osprey', 'Talon {sku} 22 Hiking Daypack', 'Outdoor', 130.00, 16,
         'daypack,22l,hiking',
         {'Capacity': '22L', 'Suspension': 'BioStretch harness'}),
        ('Deuter', 'Speed Lite {sku} 25 Daypack', 'Outdoor', 110.00, 18,
         'daypack,ultralight,25l',
         {'Capacity': '25L', 'Weight': '1.4 lb'}),
        ('Hydro Flask', 'Wide Mouth {sku} 40oz with Flex Cap', 'Hydration', 49.95, 18,
         'water-bottle,insulated,40oz',
         {'Capacity': '40 oz', 'Insulation': 'TempShield'}),
        ('Stanley', 'Quencher H2.0 {sku} 40 oz Tumbler', 'Hydration', 44.95, 22,
         'tumbler,handle,40oz',
         {'Capacity': '40 oz', 'Insulation': 'Vacuum'}),
        ('Theragun', 'Pro Plus {sku} Massage Device', 'Fitness', 599.00, 12,
         'massage,recovery,percussive',
         {'Speeds': '5', 'Stall Force': '60 lb', 'Battery': '4 hr'}),
        ('Hyperice', 'Hypervolt {sku} 2 Pro Percussion', 'Fitness', 399.00, 14,
         'percussion-massager,recovery,5-speed',
         {'Speeds': '5', 'Battery': '3 hr', 'Attachments': '5'}),
        ('NordicTrack', 'Commercial X{sku}i Studio Treadmill', 'Fitness', 1999.00, 14,
         'treadmill,incline,interactive',
         {'Incline': '0-40%', 'Decline': '-6%', 'Screen': '14in HD touchscreen'}),
        ('Concept2', 'Model {sku} D Indoor Rower PM5', 'Fitness', 1175.00, 8,
         'rower,air-flywheel,pm5',
         {'Monitor': 'PM5', 'Footprint': '8 ft', 'Weight Capacity': '500 lb'}),
        ('TaylorMade', 'Stealth {sku} 2 Plus Driver', 'Golf', 599.99, 12,
         'driver,carbon-face,low-spin',
         {'Loft Options': '8°, 9°, 10.5°', 'Face': '60X Carbon Twist'}),
        ('Callaway', 'Paradym {sku} Triple Diamond Driver', 'Golf', 599.99, 12,
         'driver,triple-diamond,low-spin',
         {'Loft': '8°, 9°, 10.5°', 'Adjustability': '4° loft + lie'}),
        ('Salomon', 'Speedcross {sku} 6 Trail Shoe', 'Footwear', 140.00, 14,
         'trail-running,grippy,gore-tex-option',
         {'Drop': '10mm', 'Outsole': 'Contagrip TA', 'Weight': '10.6 oz'}),
    ],
    'toys': [
        ('LEGO', 'Icons {sku} Tranquil Garden Set', 'Building Sets', 109.99, 22,
         'lego,icons,adult',
         {'Pieces': '1363', 'Age': '18+', 'Theme': 'Icons'}),
        ('LEGO', 'Architecture {sku} Skyline Tokyo', 'Building Sets', 59.99, 22,
         'lego,architecture,skyline',
         {'Pieces': '547', 'Age': '12+', 'Theme': 'Architecture'}),
        ('LEGO', 'Botanical {sku} Wildflower Bouquet', 'Building Sets', 59.99, 22,
         'lego,botanical,decor',
         {'Pieces': '939', 'Age': '18+', 'Theme': 'Botanical'}),
        ('Playmobil', 'NHL Stanley Cup {sku} Set 70360', 'Building Sets', 49.99, 22,
         'playmobil,sports,nhl',
         {'Figures': '4', 'Age': '5+'}),
        ('PlayShifu', 'Tacto {sku} Coding Educational Kit', 'Educational', 79.99, 22,
         'stem,coding,ipad',
         {'Age': '4-10', 'Requires': 'Tablet (iOS/Android)'}),
        ('Osmo', 'Genius Starter Kit {sku} for iPad', 'Educational', 99.99, 22,
         'stem,interactive,ipad',
         {'Age': '6-10', 'Games': '5 included'}),
        ('Kinetic Sand', 'Sandbox {sku} Set 2lb 3-Color', 'Arts & Crafts', 19.99, 28,
         'sensory,kids,non-toxic',
         {'Weight': '2 lb', 'Age': '3+'}),
        ('Crayola', 'Light-Up {sku} Tracing Pad LED', 'Arts & Crafts', 29.99, 28,
         'light-pad,tracing,led',
         {'Battery': '3x AA', 'Includes': '10 traceable sheets'}),
        ('Mattel', 'Hot Wheels Mega Hauler {sku} Garage', 'Vehicles', 39.99, 28,
         'hot-wheels,hauler,storage',
         {'Capacity': '50 vehicles', 'Age': '4+'}),
        ('Mattel', 'Polly Pocket Mega {sku} Mall', 'Dolls', 49.99, 25,
         'mini-figure,dollhouse,polly',
         {'Pieces': '30+', 'Age': '4+'}),
        ('Pokemon', 'TCG Charizard {sku} Premium Collection', 'Trading Cards', 59.99, 18,
         'pokemon,tcg,premium',
         {'Pack': '7 boosters + figure', 'Age': '6+'}),
        ('Magic the Gathering', 'Modern Horizons {sku} Bundle', 'Trading Cards', 49.99, 18,
         'mtg,modern-horizons,bundle',
         {'Pack': '9 set boosters + lands', 'Age': '13+'}),
        ('Ravensburger', '{sku}-Piece Disney Castle Puzzle', 'Puzzles', 59.99, 22,
         'puzzle,disney,2000-piece',
         {'Pieces': '2000', 'Finished Size': '37x27in'}),
        ('Spin Master', 'PAW Patrol Tower {sku} Lookout', 'Educational', 79.99, 22,
         'paw-patrol,playset,preschool',
         {'Figures': '6', 'Age': '3+', 'Height': '24in'}),
        ('Squishmallows', 'Original {sku} 16in Plush', 'Plush', 29.99, 28,
         'squishmallow,plush,collectible',
         {'Size': '16in', 'Material': 'Marshmallow soft polyester'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry — call from seed_extras.run_extras AFTER seed_r5.
# ---------------------------------------------------------------------------

def seed_r6(db, Product):
    """R6 polish: push catalog from ~12.3k to 18000+. Idempotent."""
    if Product.query.count() >= 17500:
        return 0
    added = 0

    # 1) Replay every prior template pool with R6_SUFFIXES — each fresh
    #    suffix unlocks a new slug.
    combined = []
    for cat, tpls in SKU_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R4_NEW_TEMPLATES.items():
        combined.append((cat, tpls))
    for cat, tpls in R5_NEW_TEMPLATES.items():
        combined.append((cat, tpls))

    for category, templates in combined:
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(20):
                # 7 is co-prime with 32 → max suffix coverage per template.
                sfx_idx = (t_idx * 7 + variant_idx) % len(R6_SUFFIXES)
                idx = sfx_idx + 30000 + variant_idx * 61 + t_idx * 23
                data = _build_r6_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) R6-only templates × 22 variants — long-tail SKUs.
    for category, templates in R6_NEW_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(22):
                sfx_idx = (t_idx * 5 + variant_idx) % len(R6_SUFFIXES)
                idx = sfx_idx + 40000 + variant_idx * 43 + t_idx * 19
                data = _build_r6_sku(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    return added


# ---------------------------------------------------------------------------
# Builder — extends R5 quality fields with R6 low-stock urgency seeding.
# ---------------------------------------------------------------------------

def _build_r6_sku(idx, template, category, pool, sfx_idx):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R6_SUFFIXES[sfx_idx % len(R6_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    jitter = -0.10 + ((idx * 47) % 21) / 100.0
    price = round(base_price * (1 + jitter), 2)
    list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.8 + ((idx * 31) % 110) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 50 + (idx * 211) % 27000
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
    gallery = [pool[(idx + j * 23) % len(pool)] for j in range(8)] if pool else []

    # --- R5/R6 quality fields (deterministic from idx/sfx_idx) ---
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

    # R6: stock-state distribution
    #   • ~6% out of stock (stock=0) — notify-when-back eligible
    #   • ~12% low stock (1-4 units) — fires urgency banner "Only N left"
    #   • rest: in stock (15-394 units)
    stock_seed = (idx * 29 + sfx_idx * 13) % 100
    if stock_seed < 6:
        stock = 0
        tags.append('notify-when-back')
    elif stock_seed < 18:
        stock = 1 + ((idx * 17 + sfx_idx * 5) % 4)
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
