#!/usr/bin/env python3
"""R4 polish pass — add ~2000 more products to push catalog past 5500.

Approach (matches the seed_bulk / seed_matrix pattern):
- Re-uses _build_generic_sku + _insert_product from seed_bulk
- Uses a fresh suffix pool (R4_SUFFIXES) so generated slugs don't collide
  with R2/R3 SKUs that share the same template list
- Adds R4-only templates that broaden brand coverage for fashion, beauty,
  home, sports, toys, electronics smart-home, computers accessories
- Adds ~200 leftover Open Library books (the openlib_books.json snapshot
  that R2 used — we re-iterate from a different offset slice to pick up
  titles that R2's deduplication skipped)

Idempotent: skip when Product.count() already >= 5400 (R4 floor).
"""
import json
import os

from seed_bulk import (
    SKU_TEMPLATES, _build_generic_sku, _insert_product, _category_pool,
    COLOR_NAMES, SIZE_VALUES, SHOE_SIZES,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '_data')


# Distinct suffix pool from R3 so slugs don't collide on the existing SKU
# templates that R2/R3 already exercised. Each entry is unique English word.
R4_SUFFIXES = [
    'Aria', 'Apex', 'Atlas', 'Beacon', 'Boreal', 'Cascade', 'Cipher', 'Cobalt',
    'Crest', 'Dune', 'Echo', 'Ember', 'Fjord', 'Forge', 'Glacier', 'Halo',
    'Helio', 'Indigo', 'Lumen', 'Lyra', 'Maple', 'Meridian', 'Mirage', 'Nimbus',
    'Nova', 'Onyx', 'Orbit', 'Phantom', 'Prism', 'Quartz', 'Ranger', 'Reef',
    'Rio', 'Sage', 'Scout', 'Sierra', 'Solstice', 'Spectra', 'Summit', 'Tundra',
    'Vector', 'Vista', 'Vivid', 'Wave', 'Zen',
]


# ---------------------------------------------------------------------------
# R4-only templates — completely new (brand, name, …) tuples that R2/R3 didn't
# emit, so even at suffix 'Pro'/'Plus' they won't collide.
# ---------------------------------------------------------------------------

R4_NEW_TEMPLATES = {
    'electronics': [
        ('TP-Link', 'Tapo {sku} Indoor Pan/Tilt Camera 2K', 'Smart Home', 49.99, 30,
         'security,camera,wifi,2k',
         {'Resolution': '2K (2304x1296)', 'Field of View': '360° pan / 114° tilt',
          'Night Vision': 'Color', 'Storage': 'microSD up to 512GB'}),
        ('Eufy', 'SoloCam {sku} Wire-Free Outdoor Camera 2K', 'Smart Home', 129.99, 25,
         'security,camera,wire-free,outdoor,2k',
         {'Resolution': '2K', 'Battery': '180 days', 'Weatherproof': 'IP67',
          'Local Storage': '8GB built-in'}),
        ('Nest', 'Learning Thermostat {sku} 4th Gen', 'Smart Home', 279.00, 18,
         'thermostat,smart,energy-saving',
         {'Display': 'Soli radar', 'Compatible': '95% of HVAC',
          'Saves': '10-15% on heating/cooling'}),
        ('Ecobee', 'SmartThermostat {sku} Premium', 'Smart Home', 249.99, 20,
         'thermostat,smart,alexa',
         {'Display': '4in touchscreen', 'Voice': 'Built-in Alexa',
          'Air Quality': 'Included'}),
        ('Wyze', 'Cam v{sku} 1080p Indoor/Outdoor', 'Smart Home', 35.98, 28,
         'security,camera,1080p,affordable',
         {'Resolution': '1080p', 'Night Vision': 'Color', 'Storage': 'microSD'}),
        ('Arlo', 'Pro {sku} Wire-Free 2K Security Camera', 'Smart Home', 199.99, 25,
         'security,camera,2k,wire-free',
         {'Resolution': '2K HDR', 'Battery': '6 months', 'Spotlight': 'Integrated'}),
        ('Ring', 'Video Doorbell {sku} Plus', 'Smart Home', 169.99, 22,
         'doorbell,1536p,wifi',
         {'Resolution': '1536p HD+', 'Field of View': '150°',
          'Connectivity': 'Dual-band WiFi'}),
        ('Lutron', 'Caseta {sku} Smart Lighting Starter Kit', 'Smart Home', 159.95, 18,
         'smart-switch,dimmer,zigbee',
         {'Compatibility': 'Most bulb types', 'Hub': 'Required',
          'Voice': 'Alexa, Google, Siri'}),
        ('Sonos', 'Era {sku} Premium Smart Speaker', 'Speakers', 449.00, 15,
         'smart-speaker,wifi,airplay-2',
         {'Drivers': '2 tweeters + 1 woofer', 'Voice': 'Alexa built-in',
          'Connectivity': 'WiFi 6, Bluetooth 5.0'}),
        ('Marshall', 'Stanmore III {sku} Speaker', 'Speakers', 449.00, 18,
         'speaker,bluetooth,vintage',
         {'Power': '80W', 'Drivers': '2 tweeters + 1 woofer',
          'Connectivity': 'Bluetooth 5.2, RCA, 3.5mm'}),
        ('GoPro', 'HERO{sku} Black Action Camera', 'Cameras', 399.99, 25,
         'action-cam,5.3k,waterproof',
         {'Resolution': '5.3K60', 'Stabilization': 'HyperSmooth 6.0',
          'Waterproof': '33ft', 'Battery': 'Enduro'}),
        ('DJI', 'Osmo Pocket {sku} 3-Axis Gimbal Camera', 'Cameras', 549.00, 18,
         'gimbal,4k,vlog',
         {'Resolution': '4K60', 'Sensor': '1-inch CMOS',
          'Stabilization': '3-axis mechanical'}),
        ('Canon', 'EOS R{sku} Mirrorless Camera Body', 'Cameras', 1499.99, 12,
         'mirrorless,full-frame,4k',
         {'Sensor': 'Full-frame 24MP', 'Video': '4K 60p oversampled',
          'AF': 'Dual Pixel CMOS AF II'}),
        ('Bose', 'QuietComfort Ultra {sku} Earbuds', 'Headphones', 299.00, 20,
         'earbuds,anc,immersive',
         {'Battery': '6h+24h case', 'ANC': 'Adaptive',
          'Immersive Audio': 'Yes', 'Bluetooth': '5.3'}),
        ('Sennheiser', 'Momentum {sku} True Wireless 4', 'Headphones', 299.95, 20,
         'earbuds,anc,hi-res',
         {'Battery': '7.5h+22.5h case', 'ANC': 'Adaptive',
          'Codecs': 'aptX Lossless, LDAC', 'IP': 'IP54'}),
    ],
    'computers': [
        ('Logitech', 'MX Keys {sku} Wireless Keyboard', 'Computer Accessories', 119.99, 18,
         'keyboard,wireless,backlit',
         {'Layout': 'Full size', 'Battery': '10 days backlit / 5 months off',
          'Connect': 'Bluetooth, Logi Bolt'}),
        ('Logitech', 'MX Anywhere {sku} Compact Mouse', 'Computer Accessories', 79.99, 20,
         'mouse,wireless,compact',
         {'DPI': '8000', 'Battery': '70 days', 'Connect': 'Bluetooth, Logi Bolt'}),
        ('Keychron', 'Q{sku} 75% Mechanical Keyboard', 'Computer Accessories', 199.00, 12,
         'keyboard,mechanical,gasket-mount',
         {'Layout': '75%', 'Switches': 'Gateron Pro', 'Body': 'CNC aluminum'}),
        ('Anker', 'Prime {sku} USB-C Charger 100W', 'Computer Accessories', 79.99, 22,
         'charger,gan,fast-charge',
         {'Wattage': '100W', 'Ports': '3 (2 USB-C, 1 USB-A)', 'Tech': 'GaNPrime'}),
        ('CalDigit', 'TS{sku} Thunderbolt 4 Dock', 'Computer Accessories', 399.99, 12,
         'dock,thunderbolt-4,18-port',
         {'Ports': '18 total', 'Power Delivery': '98W',
          'Display Support': 'Dual 4K60 or 8K'}),
        ('Razer', 'BlackWidow V{sku} Pro Mechanical', 'Computer Accessories', 229.99, 18,
         'gaming-keyboard,mechanical,rgb',
         {'Switches': 'Razer Green', 'RGB': 'Razer Chroma',
          'Connectivity': 'Wireless + Wired'}),
        ('SteelSeries', 'Arctis Nova {sku} Wireless Gaming Headset', 'Computer Accessories', 379.99, 18,
         'gaming-headset,wireless,multi-platform',
         {'Driver': 'Neodymium 40mm', 'Battery': '36h',
          'Connect': '2.4GHz + Bluetooth'}),
        ('Crucial', 'MX{sku} 2TB Internal SSD', 'Storage', 169.99, 28,
         'ssd,sata,2tb',
         {'Capacity': '2TB', 'Interface': 'SATA 6 Gb/s', 'Speed': '560 MB/s'}),
        ('Samsung', '990 PRO {sku}TB NVMe SSD', 'Storage', 179.99, 25,
         'ssd,nvme,gen4',
         {'Capacity': '2TB', 'Interface': 'PCIe Gen 4', 'Speed': '7450 MB/s'}),
        ('Seagate', 'IronWolf {sku}TB NAS HDD', 'Storage', 169.99, 22,
         'hdd,nas,enterprise',
         {'Capacity': '8TB', 'Speed': '7200 RPM', 'Cache': '256MB'}),
        ('ASUS', 'ROG Strix {sku} 27in QHD Gaming Monitor', 'Monitors', 599.99, 22,
         'monitor,qhd,165hz,gaming',
         {'Size': '27in QHD', 'Refresh Rate': '165Hz', 'Response': '1ms GtG'}),
        ('BenQ', 'PD{sku} 32in 4K Designer Monitor', 'Monitors', 799.00, 18,
         'monitor,4k,color-accurate',
         {'Size': '32in 4K', 'Color': '99% sRGB / Rec.709', 'Connectivity': 'USB-C 90W'}),
        ('HP', 'OMEN {sku}L Gaming Desktop RTX 4070', 'Desktops', 1899.99, 18,
         'gaming-desktop,rtx-4070,32gb',
         {'CPU': 'Intel Core i7-14700F', 'RAM': '32GB DDR5',
          'GPU': 'NVIDIA RTX 4070 12GB', 'Storage': '1TB NVMe + 2TB HDD',
          'OS': 'Windows 11 Home'}),
        ('Apple', 'Mac mini M{sku} (16GB, 512GB)', 'Desktops', 799.00, 0,
         'mini-pc,m-chip,macos',
         {'CPU': 'Apple M3', 'RAM': '16GB', 'Storage': '512GB SSD',
          'Ports': '2x TB4, HDMI, 2x USB-A'}),
        ('Microsoft', 'Surface Studio {sku} All-in-One', 'Desktops', 4499.99, 0,
         'all-in-one,touch,creator',
         {'Display': '28in 4500x3000 PixelSense touch',
          'CPU': 'Intel Core i7-11370H', 'GPU': 'RTX 3060 6GB',
          'RAM': '32GB', 'Storage': '1TB SSD'}),
    ],
    'home': [
        ('Vitamix', 'A{sku} Ascent Series Blender', 'Kitchen Appliances', 549.95, 18,
         'blender,high-performance,smart',
         {'Power': '2.2 HP', 'Container': '64 oz', 'Programs': '5 presets'}),
        ('Breville', 'Barista Express {sku} Espresso Machine', 'Kitchen Appliances', 749.95, 18,
         'espresso,bean-to-cup,burr-grinder',
         {'Built-in grinder': 'Conical burr', 'Boiler': '15-bar Italian',
          'Capacity': '67 oz water tank'}),
        ('Nespresso', 'Vertuo {sku} Coffee & Espresso Maker', 'Kitchen Appliances', 199.00, 20,
         'coffee,pod-machine,vertuo',
         {'Pod System': 'Vertuo', 'Brew Sizes': '5 (1.35-18 oz)',
          'Tank': '40 oz'}),
        ('De\'Longhi', 'Magnifica {sku} Automatic Espresso', 'Kitchen Appliances', 799.95, 20,
         'espresso,automatic,milk-frother',
         {'Grinder': 'Conical burr', 'Tank': '60 oz', 'Programs': '6 one-touch'}),
        ('Zojirushi', 'Neuro Fuzzy {sku} Rice Cooker', 'Kitchen Appliances', 215.00, 18,
         'rice-cooker,neuro-fuzzy,steel',
         {'Capacity': '5.5 cups uncooked', 'Programs': '12 cooking',
          'Inner Pot': 'Nonstick'}),
        ('Hamilton Beach', 'FlexBrew {sku} 2-Way Coffee Maker', 'Kitchen Appliances', 99.99, 28,
         'coffee-maker,dual,k-cup',
         {'Type': '2-way (carafe + single-serve)', 'Capacity': '12-cup',
          'Pod': 'K-Cup compatible'}),
        ('Char-Broil', 'Performance {sku} 5-Burner Gas Grill', 'Outdoor Living', 449.99, 22,
         'grill,5-burner,propane',
         {'Burners': '5 stainless steel', 'BTU': '60,000',
          'Cooking Area': '650 sq in'}),
        ('Weber', 'Spirit II E{sku}-310 Gas Grill', 'Outdoor Living', 599.00, 12,
         'grill,3-burner,weber',
         {'Burners': '3', 'BTU': '30,000', 'Cooking Area': '529 sq in'}),
        ('Traeger', 'Pro Series {sku} Pellet Grill', 'Outdoor Living', 899.99, 15,
         'pellet-grill,wifire,smart',
         {'Capacity': '780 sq in', 'WiFire': 'Yes', 'Temp Range': '180-500°F'}),
        ('YETI', 'Tundra {sku} Hard Cooler 45qt', 'Outdoor Living', 325.00, 12,
         'cooler,roto-molded,bear-proof',
         {'Capacity': '45 qt', 'Insulation': 'PermaFrost',
          'Bear-resistant': 'Certified'}),
        ('Vornado', 'Pivot{sku} Personal Air Circulator', 'Home Comfort', 39.99, 22,
         'fan,desktop,energy-saving',
         {'Speeds': '3', 'Tilt': '90°', 'Mount': 'Desk or wall'}),
        ('Dyson', 'Pure Cool {sku} TP09 Purifier Fan', 'Home Comfort', 599.99, 18,
         'air-purifier,fan,hepa',
         {'Filter': 'HEPA + Activated Carbon', 'Coverage': 'Whole room',
          'App': 'Dyson Link'}),
        ('Honeywell', 'HPA{sku} HEPA Air Purifier', 'Home Comfort', 269.99, 22,
         'air-purifier,hepa,large-room',
         {'CADR': '300', 'Coverage': '465 sq ft', 'Filter': 'True HEPA'}),
        ('iRobot', 'Braava jet m{sku} Mopping Robot', 'Cleaning', 449.99, 18,
         'robot-mop,wet-mop,wifi',
         {'Modes': '3 (dry/damp/wet)', 'Mapping': 'Imprint Smart Mapping',
          'App': 'iRobot Home'}),
        ('Shark', 'AI Robot Vacuum RV{sku}', 'Cleaning', 599.99, 20,
         'robot-vacuum,self-empty,ai',
         {'Self-Empty': '30-day base', 'Navigation': 'LIDAR',
          'Suction': 'Powerful HEPA'}),
    ],
    'fashion': [
        ('Calvin Klein', "Modern Cotton Boxer Brief {sku}-Pack", 'Mens Clothing', 42.00, 28,
         'underwear,cotton,boxer-brief',
         {'Material': '95% Cotton / 5% Elastane', 'Pack': '3',
          'Sizes': 'S, M, L, XL, XXL'}),
        ('Tommy Hilfiger', "Cotton Classics Polo Shirt {sku}", 'Mens Clothing', 49.50, 22,
         'polo,cotton,classic-fit',
         {'Material': '100% Cotton pique', 'Fit': 'Classic',
          'Sizes': 'S, M, L, XL, XXL'}),
        ('Polo Ralph Lauren', "Iconic Polo Shirt Slim Fit {sku}", 'Mens Clothing', 98.50, 18,
         'polo,cotton,slim-fit',
         {'Material': '100% Cotton mesh', 'Fit': 'Slim',
          'Sizes': 'XS, S, M, L, XL, XXL'}),
        ('J.Crew', "Slim-fit Stretch Chino Pant {sku}", 'Mens Clothing', 79.50, 22,
         'chino,stretch,slim-fit',
         {'Material': 'Cotton/elastane', 'Fit': 'Slim',
          'Sizes': '28-40 waist'}),
        ('Banana Republic', "Tailored Travel Suit Jacket {sku}", 'Mens Clothing', 298.00, 25,
         'suit-jacket,wool,travel',
         {'Material': 'Performance wool blend', 'Fit': 'Tailored',
          'Sizes': '36-46'}),
        ('Brooks Brothers', "Madison Fit Non-Iron Dress Shirt {sku}", 'Mens Clothing', 92.50, 22,
         'dress-shirt,non-iron,cotton',
         {'Material': '100% Cotton (non-iron)', 'Fit': 'Madison',
          'Sizes': '14.5-18.5 neck'}),
        ('Allbirds', "Wool Runner Shoes Size {sku}", 'Shoes', 110.00, 12,
         'shoes,wool,sustainable',
         {'Material': 'ZQ-certified Merino wool',
          'Insole': 'Castor bean-based foam', 'Sizes': '7-14'}),
        ('Hoka', "Bondi {sku} Running Shoe", 'Shoes', 175.00, 12,
         'running-shoes,max-cushion,hoka',
         {'Drop': '4mm', 'Weight': '10.8 oz', 'Sizes': '7-14'}),
        ('Brooks', "Ghost {sku} Cushioned Running Shoe", 'Shoes', 140.00, 18,
         'running-shoes,cushion,brooks',
         {'Drop': '12mm', 'Weight': '9.7 oz', 'Sizes': '6.5-15'}),
        ('Cole Haan', "Original Grand Wingtip Oxford Size {sku}", 'Shoes', 200.00, 22,
         'dress-shoe,wingtip,grand-os',
         {'Material': 'Leather + Grand.OS sole', 'Sizes': '7-13'}),
        ('Madewell', "The Perfect Vintage Jean Wash {sku}", 'Womens Clothing', 128.00, 18,
         'jeans,vintage,high-rise',
         {'Material': '99% Cotton / 1% Elastane', 'Rise': 'High',
          'Sizes': '23-35'}),
        ('Free People', "We the Free Aria Sweater Color {sku}", 'Womens Clothing', 128.00, 22,
         'sweater,boho,oversized',
         {'Material': 'Cotton blend', 'Fit': 'Oversized',
          'Sizes': 'XS, S, M, L'}),
        ('Anthropologie', "Pilcro Bootcut Pant Wash {sku}", 'Womens Clothing', 118.00, 22,
         'pants,bootcut,pilcro',
         {'Material': 'Stretch cotton', 'Rise': 'Mid', 'Sizes': '24-32'}),
        ('Athleta', "Salutation Stash II Pocket Tight {sku}", 'Womens Clothing', 89.00, 18,
         'leggings,pockets,yoga',
         {'Material': 'Powervita', 'Pockets': '2 side',
          'Sizes': 'XXS-3X'}),
        ('Eileen Fisher', "Organic Linen Tunic Color {sku}", 'Womens Clothing', 198.00, 18,
         'tunic,organic,linen',
         {'Material': 'Organic linen', 'Fit': 'Relaxed',
          'Sizes': 'XS, S, M, L, XL, XXL'}),
    ],
    'beauty': [
        ('Glossier', 'Boy Brow Eyebrow Pomade Shade {sku}', 'Makeup', 19.00, 0,
         'eyebrows,pomade,glossier',
         {'Volume': '0.11 oz', 'Finish': 'Soft hold', 'Coverage': 'Buildable'}),
        ('Glossier', 'Cloud Paint Blush Shade {sku}', 'Makeup', 20.00, 0,
         'blush,cream,glossier',
         {'Volume': '0.33 oz', 'Finish': 'Dewy', 'Skin Type': 'All'}),
        ('Rare Beauty', 'Soft Pinch Liquid Blush Shade {sku}', 'Makeup', 23.00, 0,
         'blush,liquid,rare-beauty',
         {'Volume': '0.25 oz', 'Finish': 'Matte/Dewy',
          'Skin Type': 'All'}),
        ('Tatcha', 'The Dewy Skin Cream {sku}oz', 'Skincare', 72.00, 12,
         'moisturizer,dewy,japanese',
         {'Volume': '1.7 oz', 'Skin Type': 'Dry/Normal',
          'Key Ingredients': 'Hadasei-3, Okinawa algae'}),
        ('Pat McGrath', 'Mothership {sku} Eyeshadow Palette', 'Makeup', 128.00, 15,
         'eyeshadow,palette,luxury',
         {'Shades': '10', 'Finish': 'Mixed', 'Pigmentation': 'High'}),
        ('NARS', 'Radiant Creamy Concealer Shade {sku}', 'Makeup', 32.00, 20,
         'concealer,creamy,radiant',
         {'Volume': '0.22 oz', 'Coverage': 'Medium-Full',
          'Finish': 'Natural radiant'}),
        ('IT Cosmetics', 'CC+ Cream SPF 50+ Shade {sku}', 'Makeup', 44.00, 22,
         'cc-cream,spf-50,full-coverage',
         {'Volume': '1.08 oz', 'SPF': '50+',
          'Coverage': 'Full', 'Finish': 'Natural radiant'}),
        ('Maybelline', 'Sky High Mascara {sku}', 'Makeup', 12.99, 22,
         'mascara,lengthening,affordable',
         {'Volume': '0.24 oz', 'Brush': 'Flex tower',
          'Effect': 'Length + volume'}),
        ('Urban Decay', 'All Nighter Long-Lasting Setting Spray {sku}', 'Makeup', 36.00, 18,
         'setting-spray,16-hour,oil-free',
         {'Volume': '4 oz', 'Wear': '16h', 'Finish': 'Natural'}),
        ('Fenty Beauty', 'Pro Filt\'r Foundation Shade {sku}', 'Makeup', 39.00, 12,
         'foundation,medium-full,fenty',
         {'Volume': '1.08 oz', 'Coverage': 'Medium-Full',
          'Finish': 'Soft matte', 'Shades': '50'}),
        ('Hourglass', 'Ambient Lighting Powder Shade {sku}', 'Makeup', 60.00, 12,
         'powder,setting,ambient-light',
         {'Volume': '0.35 oz', 'Finish': 'Photo-luminescent'}),
        ('Living Proof', 'Perfect hair Day Dry Shampoo {sku}oz', 'Hair Care', 30.00, 22,
         'dry-shampoo,clean,living-proof',
         {'Volume': '4 oz', 'Hair Type': 'All',
          'Key Ingredient': 'OFPMA'}),
        ('Briogeo', 'Don\'t Despair Repair Mask {sku}oz', 'Hair Care', 39.00, 22,
         'hair-mask,repair,clean-beauty',
         {'Volume': '8 oz', 'Hair Type': 'Damaged/dry',
          'Key Ingredients': 'Algae, biotin, rosehip'}),
        ('Function of Beauty', 'Custom Shampoo {sku}oz', 'Hair Care', 36.00, 20,
         'shampoo,custom,personalized',
         {'Volume': '8 oz', 'Customizable': 'Yes', 'Hair Quiz': 'Required'}),
        ('Aesop', 'Resurrection Aromatique Hand Wash {sku}ml', 'Bath & Body', 41.00, 12,
         'hand-wash,aromatic,aesop',
         {'Volume': '500ml', 'Notes': 'Mandarin, rosemary, cedar'}),
    ],
    'sports': [
        ('Peloton', 'Bike+ {sku} Studio Edition', 'Fitness', 2495.00, 12,
         'spin-bike,smart,subscription',
         {'Display': '23.8in HD rotating touchscreen',
          'Resistance': '100 levels', 'App': 'All-Access included'}),
        ('NordicTrack', 'Commercial X{sku} Treadmill', 'Fitness', 2299.99, 18,
         'treadmill,incline,ifit',
         {'Motor': '4.0 CHP', 'Incline': '-6% to +40%',
          'Speed': '0-12 mph', 'App': 'iFit'}),
        ('Bowflex', 'Max Trainer M{sku}', 'Fitness', 1799.00, 18,
         'cardio,low-impact,hiit',
         {'Display': '10in HD', 'Resistance': '20 levels',
          'App': 'JRNY'}),
        ('Tonal', 'Smart Home Gym System {sku}', 'Fitness', 3995.00, 0,
         'smart-gym,digital-weight,coaching',
         {'Weight': 'Up to 200 lb digital', 'Display': '24in HD',
          'Workouts': 'Live + on-demand'}),
        ('Mirror', 'The Mirror Home Studio {sku}', 'Fitness', 1495.00, 12,
         'smart-mirror,workouts,interactive',
         {'Display': '40in 1080p', 'Workouts': 'Live + on-demand',
          'Subscription': '$39/mo'}),
        ('Theragun', 'Pro {sku} Percussion Massager', 'Fitness', 599.00, 18,
         'massage-gun,deep-tissue,bluetooth',
         {'Speed': '5 (1750-2400 PPM)', 'Battery': '300 min (2 swappable)',
          'Stall Force': '60 lb'}),
        ('Hyperice', 'Hypervolt {sku} GO 2', 'Fitness', 199.00, 18,
         'massage-gun,portable,hyperice',
         {'Speed': '3', 'Battery': '180 min', 'Weight': '1.5 lb'}),
        ('Wilson', 'EVO NXT Game Basketball Size {sku}', 'Basketball', 99.99, 18,
         'basketball,indoor,nba-spec',
         {'Size': '7 (29.5in)', 'Cover': 'Composite leather'}),
        ('Spalding', 'Precision Indoor Basketball Size {sku}', 'Basketball', 109.99, 18,
         'basketball,indoor,leather',
         {'Size': '7', 'Cover': 'ZK microfiber composite'}),
        ('Titleist', 'Pro V{sku} Golf Balls 12-Pack', 'Golf', 54.99, 12,
         'golf-balls,tour-grade,titleist',
         {'Pack': '12', 'Compression': '90', 'Construction': '3-piece'}),
        ('Callaway', 'Chrome Soft {sku} Golf Balls 12-Pack', 'Golf', 49.99, 15,
         'golf-balls,soft-feel,chrome',
         {'Pack': '12', 'Compression': '75', 'Construction': '3-piece'}),
        ('Wilson', 'Pro Staff {sku} Tennis Racket 100', 'Tennis', 219.00, 18,
         'tennis,racket,100sqin',
         {'Head Size': '100 sq in', 'Weight': '11.6 oz', 'Grip': '4 3/8'}),
        ('Babolat', 'Pure Drive {sku} Tennis Racket', 'Tennis', 249.00, 18,
         'tennis,racket,power',
         {'Head Size': '100 sq in', 'Weight': '11.2 oz', 'Strung': 'No'}),
        ('Trek', 'FX {sku} Hybrid Bike', 'Cycling', 879.99, 18,
         'bike,hybrid,fitness',
         {'Frame': 'Alpha Gold Aluminum', 'Gears': '2x9',
          'Wheels': '700c'}),
        ('Specialized', 'Sirrus X {sku} Fitness Bike', 'Cycling', 1099.99, 15,
         'bike,fitness,disc-brakes',
         {'Frame': 'A1 Premium Aluminum', 'Gears': '1x10',
          'Brakes': 'Hydraulic disc'}),
    ],
    'toys': [
        ('LEGO', 'Architecture Skyline Series {sku}', 'Building Sets', 49.99, 18,
         'lego,architecture,collector',
         {'Pieces': '598', 'Age': '12+', 'Theme': 'Architecture'}),
        ('LEGO', 'Creator Expert {sku} Modular Building', 'Building Sets', 199.99, 12,
         'lego,creator,expert',
         {'Pieces': '2354', 'Age': '16+', 'Theme': 'Creator Expert'}),
        ('LEGO', 'Ideas {sku} Tribute Build', 'Building Sets', 199.99, 12,
         'lego,ideas,fan-design',
         {'Pieces': '2300', 'Age': '18+', 'Theme': 'Ideas'}),
        ('LEGO', 'Harry Potter Hogwarts {sku}', 'Building Sets', 169.99, 15,
         'lego,harry-potter,hogwarts',
         {'Pieces': '1176', 'Age': '8+', 'Theme': 'Harry Potter'}),
        ('Playmobil', 'Knights {sku} Adventure Set', 'Building Sets', 79.99, 22,
         'playmobil,knights,medieval',
         {'Pieces': '120', 'Age': '5-12'}),
        ('Fisher-Price', 'Laugh & Learn {sku} Activity Center', 'Educational', 79.99, 25,
         'baby,interactive,learning',
         {'Age': '6-36 months', 'Modes': '3', 'Sounds': '75+'}),
        ('VTech', 'KidiZoom Camera Pix Plus {sku}', 'Educational', 59.99, 25,
         'kids,camera,vtech',
         {'Age': '4-9', 'Storage': '512MB built-in',
          'Features': 'Photo + video + games'}),
        ('Osmo', 'Genius Starter Kit {sku} for iPad', 'Educational', 99.99, 22,
         'osmo,stem,ipad',
         {'Age': '6-10', 'Compatible': 'iPad', 'Games': '5 included'}),
        ('Mattel', 'UNO Classic Card Game {sku} Edition', 'Board Games', 9.99, 28,
         'cards,uno,classic',
         {'Players': '2-10', 'Age': '7+', 'Cards': '108'}),
        ('Hasbro', 'Clue Classic Board Game {sku}', 'Board Games', 19.99, 28,
         'board-game,clue,mystery',
         {'Players': '2-6', 'Age': '8+'}),
        ('Catan Studio', 'Catan {sku} Edition Board Game', 'Board Games', 54.99, 18,
         'board-game,catan,strategy',
         {'Players': '3-4', 'Age': '10+', 'Time': '60-120 min'}),
        ('Asmodee', 'Ticket to Ride {sku} Edition', 'Board Games', 54.95, 18,
         'board-game,ticket-to-ride,family',
         {'Players': '2-5', 'Age': '8+', 'Time': '30-60 min'}),
        ('Nintendo', 'amiibo {sku} Figure', 'Collectibles', 15.99, 22,
         'amiibo,nintendo,collectible',
         {'Compatible': 'Switch / Wii U / 3DS',
          'Material': 'PVC', 'Height': '4in'}),
        ('Squishmallows', 'Original {sku} 12in Plush', 'Plush', 24.99, 25,
         'plush,squishmallows,collectible',
         {'Size': '12in', 'Material': 'Polyester'}),
        ('Build-A-Bear', 'Classic Teddy Bear {sku} Edition', 'Plush', 35.00, 20,
         'plush,teddy,build-a-bear',
         {'Size': '16in', 'Material': 'Polyester'}),
    ],
}


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def seed_polish(db, Product):
    """R4 polish: bring catalog from ~3631 to ~5500+. Idempotent."""
    if Product.query.count() >= 5400:
        return 0
    added = 0

    # 1) Re-run existing SKU_TEMPLATES with R4 suffixes (so each template
    #    emits N more SKU variants — slug uniqueness check skips collisions).
    #    range(13) keeps the catalog increase moderate (~1200 new SKUs).
    for category, templates in SKU_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(13):
                sfx_idx = (t_idx * 11 + variant_idx) % len(R4_SUFFIXES)
                idx = sfx_idx + 1000 + variant_idx * 31
                data = _build_generic_sku_r4(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 2) Add R4-only templates × 6 variants — adds ~700 brand-new SKUs.
    for category, templates in R4_NEW_TEMPLATES.items():
        pool = _category_pool(category)
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(6):
                sfx_idx = (t_idx * 7 + variant_idx * 5) % len(R4_SUFFIXES)
                idx = sfx_idx + 5000 + variant_idx * 41 + t_idx * 13
                data = _build_generic_sku_r4(idx, tpl, category, pool, sfx_idx)
                if _insert_product(db, Product, data):
                    added += 1
        db.session.commit()

    # 3) Extra book pass — Open Library data, but starting from offset 200 so
    #    we pick up titles R2's pass skipped due to duplicate slugs at the head.
    book_path = os.path.join(DATA_DIR, 'openlib_books_r3.json')
    if os.path.exists(book_path):
        from seed_bulk import _build_book, _category_pool as _cp
        import random as _rng_mod
        rng = _rng_mod.Random(2027)
        with open(book_path, 'r', encoding='utf-8') as f:
            books = json.load(f)
        book_pool = _cp('books')
        seen = set(p.name.lower() for p in
                   Product.query.filter_by(category_slug='books').all())
        # Slice from offset 800 so we pull from the tail that R3 truncated
        for idx, b in enumerate(books[800:1400]):
            title = (b.get('title') or '').strip()
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            data = _build_book(idx + 10000, b, book_pool, rng)
            if _insert_product(db, Product, data):
                added += 1
        db.session.commit()

    return added


def _build_generic_sku_r4(idx, template, category, pool, sfx_idx):
    """R4 wrapper that lets us pin the suffix to R4_SUFFIXES."""
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = R4_SUFFIXES[sfx_idx % len(R4_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    # mild deterministic price jitter ±10%
    jitter = -0.10 + ((idx * 37) % 21) / 100.0
    price = round(base_price * (1 + jitter), 2)
    list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.9 + ((idx * 23) % 100) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 50 + (idx * 191) % 24000
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
    gallery = [pool[(idx + j * 17) % len(pool)] for j in range(8)] if pool else []
    description = (
        f"{name} by {brand}. {subcat} engineered for everyday performance. "
        + " ".join(f"{k}: {v}." for k, v in specs.items() if k != 'Brand')
    )
    features = [f"{k}: {v}" for k, v in list(specs.items())[:6]]
    # R4 climate-pledge tag — deterministic ~25% of SKUs (slug-hash based but
    # we don't have slug here, so use idx parity in the suffix slot).
    is_climate_pledge = ((idx + sfx_idx) % 4 == 0)
    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
    tags.append(color.lower().replace(' ', '-'))
    if is_climate_pledge:
        tags.append('climate-pledge-friendly')
    is_deal = (idx % 5 == 0)
    is_bestseller = (reviews > 13000)
    is_featured = (idx % 13 == 0)
    return dict(
        name=name, brand=brand, category_slug=category, subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants=variants, stock=15 + (idx * 19 + int(rating * 10)) % 380,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='',
    )
