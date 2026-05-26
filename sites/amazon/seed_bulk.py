#!/usr/bin/env python3
"""Bulk product seeder for Amazon mirror (R2 polish).

Adds ~800 additional products on top of seed_data.py + seed_extras.py to bring
Product total from ~743 to ~1500+. Sources:
  • Books: 600 real titles fetched from Open Library /subjects API
    (snapshot at sites/amazon/_data/openlib_books.json).
  • Other categories: deterministic synthesis of brand + product type +
    variants (storage / color / size) using fixed Random(seed).

All seeding is deterministic — every value derived from a seeded
random.Random or from data files checked into the repo — so the
instance_seed/amazon_store.db md5 remains byte-identical across rebuilds.
"""
import os
import re
import json
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "static", "images")
DATA_DIR = os.path.join(BASE_DIR, "_data")


def _slugify(text):
    s = re.sub(r'[^\w\s-]', '', text.lower())
    s = re.sub(r'[\s_-]+', '-', s).strip('-')
    return s[:100]


def _list_imgs(subdir, min_size=3000):
    path = os.path.join(IMG_DIR, subdir)
    if not os.path.isdir(path):
        return []
    out = []
    for f in sorted(os.listdir(path)):
        if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            continue
        if 'sprite' in f.lower() or 'shadow' in f.lower():
            continue
        full = os.path.join(path, f)
        try:
            if os.path.getsize(full) >= min_size:
                out.append(f"/static/images/{subdir}/{f}")
        except OSError:
            pass
    return out


CATEGORY_POOLS = {
    'electronics': ['search_electronics', 'search_camera', 'search_headphones', 'products_amazon', 'products'],
    'computers':   ['search_laptop', 'products_amazon', 'products'],
    'home':        ['search_home', 'products', 'products_amazon'],
    'fashion':     ['search_fashion', 'products', 'products_amazon'],
    'books':       ['search_books', 'products', 'homepage'],
    'beauty':      ['products_amazon', 'products', 'homepage'],
    'sports':      ['products_amazon', 'products', 'homepage'],
    'toys':        ['products_amazon', 'products', 'homepage'],
}


def _category_pool(cat):
    seen, out = set(), []
    for d in CATEGORY_POOLS.get(cat, ['products_amazon', 'products']):
        for p in _list_imgs(d):
            if p not in seen:
                seen.add(p); out.append(p)
    return out


# ---------------------------------------------------------------------------
# Book bulk loader
# ---------------------------------------------------------------------------

# Deterministic genre → (price_low, price_high, list_uplift_pct)
GENRE_PRICING = {
    'Fiction':          (12.99, 19.99, 35),
    'Science Fiction':  (13.99, 21.99, 38),
    'Fantasy':          (13.99, 22.99, 36),
    'Mystery':          (12.99, 18.99, 32),
    'Thriller':         (13.99, 19.99, 32),
    'Romance':          (10.99, 16.99, 30),
    'History':          (16.99, 28.99, 40),
    'Biography':        (15.99, 26.99, 38),
    'Cookbook':         (19.99, 34.99, 42),
    'Self-Help':        (14.99, 24.99, 38),
    'Business':         (19.99, 32.99, 42),
    'Science':          (17.99, 29.99, 40),
    'Children':         (8.99,  15.99, 30),
    'Young Adult':      (11.99, 18.99, 32),
    'Poetry':           (12.99, 19.99, 30),
    'Philosophy':       (15.99, 26.99, 38),
    'Psychology':       (16.99, 26.99, 38),
    'Programming':      (29.99, 54.99, 45),
    'Art':              (24.99, 49.99, 42),
    'Travel':           (14.99, 24.99, 36),
}

PUBLISHERS = [
    'Aurora & Quill Press', 'Lighthouse Books', 'Granite Hill', 'Penguin Vanguard',
    'Cypress & Reed', 'North Wind Editions', 'Lantern Books', 'Half-Moon Press',
    'Iron Owl Publishing', 'Bramble & Vine', 'Cascade Books', 'Hummingbird Editions',
]


def _build_book(idx, b, pool, rng):
    title = b['title']
    author = b['author']
    genre = b['genre']
    year = b.get('year') or 2020
    # Sanity-clip year (Open Library has some "1000" entries; bump those forward)
    if not isinstance(year, int) or year < 1800 or year > 2025:
        year = 1900 + (idx * 7) % 125
    edition_count = b.get('edition_count') or 50
    # price within genre band, deterministic via idx
    low, high, uplift = GENRE_PRICING.get(genre, (12.99, 22.99, 35))
    price = round(low + ((idx * 31) % 1000) / 1000.0 * (high - low), 2)
    list_price = round(price * (1 + uplift / 100.0), 2)
    # rating in 3.6 – 4.9 band
    rating = round(3.6 + ((idx * 17 + edition_count) % 130) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    # review count loosely correlated with edition_count
    reviews = max(20, min(48210, edition_count * 4 + (idx * 13) % 5000))
    pages = 160 + (idx * 23) % 540
    publisher = PUBLISHERS[idx % len(PUBLISHERS)]
    isbn = f"978-{(idx % 9) + 1}-{(idx * 7) % 9000 + 1000:04d}-{(idx * 11) % 900 + 100:03d}-{idx % 10}"
    img = pool[idx % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 11) % len(pool)] for j in range(6)] if pool else []
    description = (
        f"{title} by {author}. A {genre.lower()} title originally published in {year}, "
        f"with {edition_count}+ editions in print. {pages} pages. Whether you are a "
        f"long-time fan of {author} or new to {genre.lower()}, this edition is a "
        f"satisfying addition to your library."
    )
    features = [
        f'Genre: {genre}',
        f'Format: Paperback, {pages} pages',
        'Language: English',
        f'Author: {author}',
        f'Original publication: {year}',
        f'Publisher: {publisher}',
    ]
    specs = {
        'Author': author,
        'Genre': genre,
        'Pages': str(pages),
        'Publisher': publisher,
        'Language': 'English',
        'Publication Date': f'{year}-{(idx % 12) + 1:02d}-{(idx % 27) + 1:02d}',
        'Format': 'Paperback',
        'ISBN-13': isbn,
        'Editions': str(edition_count),
    }
    tags = ['book', 'paperback', genre.lower().replace(' ', '-')]
    if edition_count > 200:
        tags.append('bestseller')
    is_deal = (idx % 5 == 0)
    is_bestseller = edition_count > 500
    is_featured = (idx % 13 == 0)
    return dict(
        name=title, brand=author, category_slug='books', subcategory=genre,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants={'format': ['Paperback', 'Hardcover', 'Kindle', 'Audiobook']},
        stock=20 + (idx * 13 + int(rating * 10)) % 380,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date=f'{year}-{(idx % 12) + 1:02d}-01',
    )


# ---------------------------------------------------------------------------
# Generic SKU bulk synthesizer for non-book categories
# ---------------------------------------------------------------------------

SKU_TEMPLATES = {
    'electronics': [
        # (brand, family, subcategory, base_price, list_uplift, tag_csv, specs_template)
        ('Anker', 'Soundcore Liberty {sku} Wireless Earbuds', 'Headphones', 79.99, 30,
         'anc,wireless,earbuds,bluetooth',
         {'Battery':'10h+30h case','ANC':'Adaptive','Driver':'11mm','Bluetooth':'5.3'}),
        ('JBL', 'Flip {sku} Portable Bluetooth Speaker', 'Speakers', 99.99, 35,
         'portable,waterproof,bluetooth',
         {'Battery':'12h','Waterproof':'IP67','Bluetooth':'5.1','Power':'20W'}),
        ('Sony', 'WH-{sku} Over-Ear Wireless Headphones', 'Headphones', 249.99, 30,
         'anc,wireless,over-ear',
         {'Battery':'30h','ANC':'Industry-leading','Driver':'40mm','Bluetooth':'5.2'}),
        ('Bose', 'SoundLink {sku} Portable Speaker', 'Speakers', 149.99, 25,
         'portable,waterproof,bluetooth',
         {'Battery':'12h','Waterproof':'IP67','Bluetooth':'4.2'}),
        ('Samsung', 'Galaxy Buds{sku} Wireless Earbuds', 'Headphones', 149.99, 30,
         'anc,wireless,earbuds,samsung',
         {'Battery':'8h+18h case','ANC':'Yes','Bluetooth':'5.3'}),
        ('Apple', 'AirPods Pro Gen{sku} USB-C', 'Headphones', 249.00, 0,
         'anc,wireless,earbuds,apple',
         {'Battery':'6h+30h case','ANC':'Adaptive','Chip':'H2','Case':'MagSafe USB-C'}),
        ('Amazon', 'Echo Dot {sku} Smart Speaker', 'Smart Home', 49.99, 40,
         'smart-speaker,alexa,wifi',
         {'Voice':'Alexa','Connectivity':'WiFi, Bluetooth','Color':'Charcoal'}),
        ('Amazon', 'Fire HD {sku} Tablet', 'Tablets', 149.99, 33,
         'tablet,kids,amazon',
         {'Display':'10.1in HD','Storage':'32GB','Battery':'12h','Camera':'5MP'}),
        ('Kindle', 'Paperwhite {sku} (16GB)', 'E-readers', 159.99, 25,
         'e-reader,waterproof,backlight',
         {'Display':'6.8in 300ppi','Storage':'16GB','Waterproof':'IPX8','Battery':'10 weeks'}),
        ('Logitech', 'MX Master {sku} Wireless Mouse', 'Computer Accessories', 99.99, 20,
         'wireless,ergonomic,office',
         {'DPI':'8000','Battery':'70 days','Connectivity':'Bluetooth, Logi Bolt'}),
        ('Roku', 'Express {sku} 4K Streaming Stick', 'Streaming', 39.99, 33,
         'streaming,4k,hdr',
         {'Resolution':'4K HDR Dolby Vision','WiFi':'Dual-band','Voice Remote':'Yes'}),
        ('Garmin', 'Vivoactive {sku} GPS Smartwatch', 'Wearables', 299.99, 25,
         'gps,smartwatch,fitness',
         {'Display':'AMOLED','Battery':'11 days','GPS':'Built-in','Water Rating':'5 ATM'}),
        ('Fitbit', 'Versa {sku} Fitness Smartwatch', 'Wearables', 199.99, 30,
         'fitness,smartwatch,heart-rate',
         {'Display':'AMOLED','Battery':'6+ days','GPS':'Built-in','Water Rating':'50m'}),
        ('Ring', 'Stick Up Cam {sku} Security Camera', 'Smart Home', 99.99, 30,
         'security,camera,wifi',
         {'Resolution':'1080p HD','Connectivity':'WiFi','Power':'Battery + Plug-in'}),
        ('Philips Hue', 'White & Color {sku} Bulb 4-pack', 'Smart Home', 159.99, 25,
         'smart-bulb,zigbee,color',
         {'Bulbs':'4x A19','Hub':'Required','Color':'Multicolor + White'}),
    ],
    'computers': [
        ('Dell', 'Inspiron {sku} (i5, 16GB, 512GB)', 'Laptops', 749.99, 35,
         'laptop,16gb,windows-11-home',
         {'CPU':'Intel Core i5','RAM':'16GB','Storage':'512GB SSD','Display':'15.6in FHD','OS':'Windows 11 Home'}),
        ('HP', 'Pavilion {sku} (Ryzen 7, 16GB, 1TB)', 'Laptops', 899.99, 30,
         'laptop,ryzen,16gb,1tb,windows-11-home',
         {'CPU':'AMD Ryzen 7','RAM':'16GB','Storage':'1TB SSD','Display':'15.6in FHD','OS':'Windows 11 Home'}),
        ('Lenovo', 'IdeaPad {sku} (i7, 16GB, 512GB)', 'Laptops', 829.99, 33,
         'laptop,i7,windows-11-home',
         {'CPU':'Intel Core i7','RAM':'16GB','Storage':'512GB SSD','Display':'14in FHD','OS':'Windows 11 Home'}),
        ('ASUS', 'Vivobook {sku} (Ryzen 5, 8GB, 256GB)', 'Laptops', 549.99, 28,
         'laptop,budget,windows-11-home',
         {'CPU':'AMD Ryzen 5','RAM':'8GB','Storage':'256GB SSD','Display':'15.6in FHD','OS':'Windows 11 Home'}),
        ('Acer', 'Aspire {sku} (i3, 8GB, 512GB)', 'Laptops', 449.99, 30,
         'laptop,budget,starter',
         {'CPU':'Intel Core i3','RAM':'8GB','Storage':'512GB SSD','Display':'15.6in FHD','OS':'Windows 11 Home'}),
        ('Apple', 'MacBook Air {sku}-inch M3', 'Laptops', 1299.00, 0,
         'macbook,m3,macos',
         {'CPU':'Apple M3 8-core','RAM':'16GB','Storage':'512GB','Display':'Liquid Retina','OS':'macOS'}),
        ('Samsung', 'Galaxy Book{sku} Pro 360', 'Laptops', 1099.99, 30,
         '2-in-1,oled,touchscreen',
         {'CPU':'Intel Core Ultra 7','RAM':'16GB','Storage':'1TB','Display':'15.6in AMOLED','OS':'Windows 11 Home'}),
        ('Microsoft', 'Surface Pro {sku} (i7, 16GB)', 'Tablets', 1499.99, 28,
         'surface,tablet,windows-11-pro',
         {'CPU':'Intel Core Ultra 7','RAM':'16GB','Storage':'512GB','Display':'13in PixelSense','OS':'Windows 11 Pro'}),
        ('Razer', 'Blade {sku} Gaming Laptop RTX 4070', 'Laptops', 2499.99, 25,
         'gaming,rtx,32gb',
         {'CPU':'Intel Core i9-14900HX','RAM':'32GB DDR5','Storage':'1TB SSD','GPU':'NVIDIA RTX 4070','Display':'16in QHD+ 240Hz'}),
        ('Logitech', 'G{sku} Pro X Mechanical Keyboard', 'Computer Accessories', 199.99, 22,
         'gaming,mechanical,hot-swap',
         {'Layout':'TKL','Switches':'GX Brown','Connectivity':'USB-C'}),
        ('SanDisk', 'Extreme {sku}TB Portable SSD', 'Storage', 159.99, 35,
         'portable-ssd,usb-c,rugged',
         {'Capacity':'1TB','Interface':'USB-C 3.2 Gen 2','Speed':'1050 MB/s','Rugged':'IP65'}),
        ('Samsung', 'T{sku} Portable SSD 2TB', 'Storage', 219.99, 30,
         'portable-ssd,2tb,fast',
         {'Capacity':'2TB','Interface':'USB-C 3.2 Gen 2','Speed':'2000 MB/s'}),
        ('Western Digital', 'My Passport {sku}TB Portable HDD', 'Storage', 89.99, 33,
         'portable-hdd,backup',
         {'Capacity':'4TB','Interface':'USB 3.2','Encryption':'AES-256 hardware'}),
        ('Dell', 'UltraSharp U{sku} 27in 4K Monitor', 'Monitors', 599.99, 28,
         '4k,ips,usb-c-docking',
         {'Size':'27in 4K','Panel':'IPS','Refresh Rate':'60Hz','Connectivity':'USB-C 90W'}),
        ('LG', 'UltraGear {sku} 32in OLED Monitor', 'Monitors', 899.99, 25,
         '4k,oled,gaming,240hz',
         {'Size':'32in 4K','Panel':'OLED','Refresh Rate':'240Hz','Response':'0.03ms'}),
    ],
    'home': [
        ('Cuisinart', 'CookPro {sku} 12-Cup Food Processor', 'Kitchen Appliances', 199.95, 32,
         'food-processor,12-cup,stainless',
         {'Capacity':'12 cups','Power':'600W','Blades':'Stainless steel S, slicing, shredding'}),
        ('Ninja', 'Speedi {sku} Rapid Cooker & Air Fryer', 'Kitchen Appliances', 169.99, 30,
         'air-fryer,multi-cooker,6qt',
         {'Capacity':'6 qt','Functions':'Air fry, rapid cook, slow cook, sear'}),
        ('Instant Pot', 'Duo Plus {sku} 9-in-1 Pressure Cooker', 'Kitchen Appliances', 139.99, 30,
         'pressure-cooker,8qt,multi-cooker',
         {'Capacity':'8 qt','Functions':'Pressure cook, sterilize, slow cook, sous-vide'}),
        ('KitchenAid', 'Classic {sku} 4.5-Qt Stand Mixer', 'Kitchen Appliances', 379.99, 28,
         'stand-mixer,4.5-quart,classic',
         {'Capacity':'4.5 qt','Power':'275W','Attachments':'10+','Color':'White'}),
        ('Cosori', 'Pro {sku}-Qt Air Fryer', 'Kitchen Appliances', 109.99, 32,
         'air-fryer,window,bestseller',
         {'Capacity':'5.8 qt','Functions':'12 presets','Window':'Yes'}),
        ('Lodge', 'Cast Iron {sku}-Inch Skillet Pre-Seasoned', 'Cookware', 29.90, 30,
         'cast-iron,made-in-usa',
         {'Diameter':'10 inch','Material':'Pre-seasoned cast iron','Made In':'USA'}),
        ('Le Creuset', 'Signature {sku} Qt Round Dutch Oven', 'Cookware', 399.95, 12,
         'dutch-oven,enameled,premium',
         {'Capacity':'3.5 qt','Material':'Enameled cast iron','Lifetime Warranty':'Yes'}),
        ('All-Clad', 'D3 Stainless {sku}-Piece Cookware Set', 'Cookware', 599.95, 35,
         'cookware-set,stainless,tri-ply',
         {'Pieces':'7','Material':'Tri-ply stainless steel','Dishwasher Safe':'Yes'}),
        ('OXO', 'Good Grips {sku}-Piece Kitchen Tool Set', 'Kitchen Utensils', 49.95, 25,
         'kitchen-tools,non-slip,starter',
         {'Pieces':'10','Material':'Stainless steel + soft-grip handles'}),
        ('iRobot', 'Roomba {sku} Robot Vacuum', 'Cleaning', 399.99, 30,
         'robot-vacuum,wifi,multi-surface',
         {'Suction':'Tangle-free','Battery':'90 min','App':'iRobot Home','Voice':'Alexa, Google'}),
        ('Dyson', 'V{sku} Cordless Stick Vacuum', 'Cleaning', 549.99, 25,
         'cordless,vacuum,hepa',
         {'Battery':'60 min','Filter':'HEPA','Bin':'0.76 L','Weight':'6.0 lb'}),
        ('Shark', 'Navigator {sku} Lift-Away Vacuum', 'Cleaning', 219.99, 28,
         'vacuum,corded,upright',
         {'Type':'Upright','Filter':'HEPA','Power':'1200W','Bin':'1.0 qt'}),
        ('Tempur-Pedic', 'TEMPUR-Adapt {sku} Pillow', 'Bedding', 129.00, 22,
         'pillow,memory-foam,medium',
         {'Material':'TEMPUR memory foam','Size':'Queen','Cover':'Removable, washable'}),
        ('Brooklinen', 'Luxe {sku}-Piece Sheet Set', 'Bedding', 169.00, 18,
         'sheets,sateen,400-thread',
         {'Material':'100% long-staple cotton sateen','Thread Count':'480','Size':'Queen'}),
        ('Casper', 'Original {sku} Pillow Queen', 'Bedding', 89.00, 25,
         'pillow,foam,casper',
         {'Material':'Memory foam + polyester fill','Size':'Queen','Cooling':'AirScape technology'}),
    ],
    'fashion': [
        ('Levi\'s', "Men's 501 Original Fit Jeans Wash {sku}", 'Mens Clothing', 69.50, 25,
         'jeans,denim,classic',
         {'Material':'100% Cotton denim','Fit':'Original 501','Sizes':'28-44 waist'}),
        ('Levi\'s', "Women's 721 High Rise Skinny Jeans Wash {sku}", 'Womens Clothing', 79.50, 22,
         'jeans,skinny,high-rise',
         {'Material':'Stretch denim','Rise':'High','Sizes':'24-34 waist'}),
        ('Nike', 'Sportswear Tech Fleece Hoodie Color {sku}', 'Mens Clothing', 130.00, 18,
         'hoodie,fleece,sport',
         {'Material':'Cotton/poly fleece','Fit':'Standard','Sizes':'S, M, L, XL, XXL'}),
        ('Nike', 'Air Force 1 \'07 White Sneakers Size {sku}', 'Shoes', 110.00, 15,
         'sneakers,classic,white,leather',
         {'Material':'Leather upper','Cushioning':'Air-Sole','Sizes':'6-14'}),
        ('Adidas', 'Ultraboost {sku} Running Shoes', 'Shoes', 189.99, 18,
         'running-shoes,boost,performance',
         {'Material':'Primeknit upper','Midsole':'Boost','Sizes':'6-14'}),
        ('Adidas', 'Stan Smith Sneakers Color {sku}', 'Shoes', 100.00, 18,
         'sneakers,classic,white',
         {'Material':'Leather upper','Sole':'Rubber cupsole','Sizes':'5-13'}),
        ('Hanes', "Men's ComfortSoft Crew T-Shirt {sku}-Pack", 'Mens Clothing', 23.99, 30,
         'tshirt,cotton,basics',
         {'Material':'100% Cotton','Pack':'6','Color':'White','Sizes':'S, M, L, XL, XXL, 3XL'}),
        ('Champion', "Powerblend Pullover Hoodie {sku}", 'Mens Clothing', 50.00, 25,
         'hoodie,fleece,classic',
         {'Material':'Cotton/poly fleece','Fit':'Standard','Sizes':'S, M, L, XL, XXL'}),
        ('Under Armour', 'HeatGear Compression Shirt Size {sku}', 'Mens Clothing', 35.00, 22,
         'compression,heatgear,workout',
         {'Material':'Polyester/elastane','Fit':'Compression','Sizes':'S, M, L, XL, XXL'}),
        ('Lululemon', "Align High-Rise Pant 25in {sku}", 'Womens Clothing', 98.00, 12,
         'leggings,yoga,nulu',
         {'Material':'Nulu fabric','Rise':'High','Inseam':'25in','Sizes':'0-20'}),
        ('Patagonia', 'Better Sweater Fleece Jacket Color {sku}', 'Mens Clothing', 159.00, 18,
         'fleece,jacket,outdoor',
         {'Material':'Recycled polyester fleece','Fit':'Regular','Sizes':'XS-3XL'}),
        ('Columbia', 'Bugaboo II Insulated Jacket {sku}', 'Mens Clothing', 199.00, 30,
         'jacket,3-in-1,waterproof',
         {'Material':'Nylon shell + Omni-Heat liner','Sizes':'S-XXL'}),
        ('Fossil', "Men's Carraway Leather Watch Model {sku}", 'Accessories', 159.00, 25,
         'watch,leather,classic',
         {'Material':'Leather strap','Movement':'Quartz','Water-resistant':'50m'}),
        ('Ray-Ban', 'Aviator Classic Sunglasses Size {sku}', 'Accessories', 169.00, 20,
         'sunglasses,aviator,polarized',
         {'Material':'Metal frame','Lens':'G-15 glass','Sizes':'55mm, 58mm, 62mm'}),
        ('Coach', 'Tabby Shoulder Bag {sku}', 'Accessories', 350.00, 20,
         'handbag,leather,designer',
         {'Material':'Refined calf leather','Size':'Medium','Color':'Black'}),
    ],
    'beauty': [
        ('CeraVe', 'Moisturizing Cream {sku}oz Jar', 'Skincare', 19.99, 25,
         'moisturizer,sensitive-skin,fragrance-free',
         {'Volume':'19oz','Skin Type':'Dry/Normal','Key Ingredients':'Ceramides, Hyaluronic Acid'}),
        ('Neutrogena', 'Hydro Boost Water Gel {sku}oz', 'Skincare', 16.99, 30,
         'moisturizer,hyaluronic-acid,oil-free',
         {'Volume':'1.7oz','Skin Type':'Dry','Key Ingredients':'Hyaluronic Acid'}),
        ('La Roche-Posay', 'Anthelios Melt-in Sunscreen SPF{sku}', 'Skincare', 34.99, 22,
         'sunscreen,spf60,broad-spectrum',
         {'Volume':'3oz','SPF':'60','Type':'Chemical','Water-resistant':'80 min'}),
        ('The Ordinary', 'Niacinamide 10% + Zinc 1% Serum {sku}ml', 'Skincare', 6.50, 38,
         'serum,niacinamide,acne',
         {'Volume':'30ml','Key Ingredients':'Niacinamide 10%, Zinc PCA 1%'}),
        ('Olaplex', 'No.{sku} Bond Maintenance Shampoo', 'Hair Care', 30.00, 18,
         'shampoo,sulfate-free,bond-repair',
         {'Volume':'8.5oz','Hair Type':'Damaged','Sulfate-Free':'Yes'}),
        ('Olaplex', 'No.{sku} Bond Maintenance Conditioner', 'Hair Care', 30.00, 18,
         'conditioner,sulfate-free,bond-repair',
         {'Volume':'8.5oz','Hair Type':'Damaged','Sulfate-Free':'Yes'}),
        ('L\'Oreal Paris', 'Elvive Total Repair {sku} Shampoo', 'Hair Care', 7.99, 28,
         'shampoo,damaged-hair,affordable',
         {'Volume':'12.6oz','Hair Type':'Damaged','Key Ingredients':'Protein, Ceramides'}),
        ('Dove', 'Beauty Bar {sku}-Pack 3.75oz', 'Bath & Body', 9.99, 30,
         'soap,sensitive-skin,bar',
         {'Pack':'8','Skin Type':'All','Scent':'Original'}),
        ('Native', 'Aluminum-Free Deodorant {sku}oz', 'Bath & Body', 13.00, 25,
         'deodorant,aluminum-free,natural',
         {'Volume':'2.65oz','Scent':'Coconut & Vanilla'}),
        ('Maybelline', 'SuperStay Matte Ink Liquid Lipstick Shade {sku}', 'Makeup', 9.99, 28,
         'lipstick,matte,long-wear',
         {'Volume':'0.17 fl oz','Finish':'Matte','Wear':'16h'}),
        ('NARS', 'Radiant Creamy Concealer Shade {sku}', 'Makeup', 32.00, 18,
         'concealer,radiant,medium-coverage',
         {'Volume':'0.22 oz','Finish':'Radiant','Wear':'16h'}),
        ('Charlotte Tilbury', 'Pillow Talk Lipstick Shade {sku}', 'Makeup', 38.00, 15,
         'lipstick,matte,nude',
         {'Volume':'0.12 oz','Finish':'Matte revolution','Wear':'10h'}),
        ('Drunk Elephant', 'C-Firma Fresh Vitamin C Day Serum {sku}ml', 'Skincare', 80.00, 12,
         'serum,vitamin-c,brightening',
         {'Volume':'30ml','Key Ingredients':'L-Ascorbic Acid 15%'}),
        ('Sunday Riley', 'Good Genes Lactic Acid Treatment {sku}oz', 'Skincare', 85.00, 15,
         'serum,lactic-acid,exfoliating',
         {'Volume':'1.7oz','Key Ingredients':'Lactic Acid','Use':'PM'}),
        ('Bumble & Bumble', 'Hairdresser\'s Invisible Oil {sku}oz', 'Hair Care', 42.00, 18,
         'hair-oil,smoothing,heat-protection',
         {'Volume':'3.4oz','Hair Type':'All','Heat Protection':'Yes'}),
    ],
    'sports': [
        ('Wilson', 'NCAA Solution Game Basketball Size {sku}', 'Basketball', 79.99, 25,
         'basketball,indoor,leather',
         {'Size':'7 (29.5in)','Surface':'Indoor','Material':'Leather'}),
        ('Spalding', 'Cross Court Streetball Size {sku}', 'Basketball', 24.99, 30,
         'basketball,outdoor,rubber',
         {'Size':'7','Surface':'Outdoor','Material':'Composite rubber'}),
        ('Yeti', 'Rambler {sku}oz Tumbler', 'Outdoor', 38.00, 12,
         'tumbler,insulated,stainless',
         {'Volume':'20oz','Material':'Stainless steel','Dishwasher Safe':'Yes'}),
        ('Hydro Flask', 'Standard Mouth {sku}oz Water Bottle', 'Outdoor', 39.95, 15,
         'water-bottle,insulated,stainless',
         {'Volume':'21oz','Material':'TempShield insulated stainless'}),
        ('Stanley', 'Adventure Quencher Tumbler {sku}oz', 'Outdoor', 44.95, 12,
         'tumbler,insulated,40oz',
         {'Volume':'40oz','Material':'Recycled stainless steel'}),
        ('REI Co-op', 'Trail {sku} Backpack 40L', 'Outdoor', 99.95, 22,
         'backpack,hiking,40l',
         {'Capacity':'40L','Material':'Recycled nylon','Frame':'Internal'}),
        ('Osprey', 'Talon {sku} Backpack 22L', 'Outdoor', 130.00, 18,
         'backpack,daypack,airscape',
         {'Capacity':'22L','Material':'Bluesign-certified nylon','Frame':'AirScape'}),
        ('Coleman', 'Sundome {sku}-Person Tent', 'Camping', 89.99, 28,
         'tent,4-person,weatherproof',
         {'Capacity':'4-person','Setup':'10 min','Material':'WeatherTec polyester'}),
        ('Therm-a-Rest', 'NeoAir XLite {sku} Sleeping Pad', 'Camping', 199.95, 18,
         'sleeping-pad,ultralight,inflatable',
         {'Type':'Inflatable','R-Value':'4.2','Weight':'13 oz'}),
        ('Bowflex', 'SelectTech {sku} Adjustable Dumbbells', 'Fitness', 549.00, 22,
         'dumbbells,adjustable,5-52.5lb',
         {'Weight Range':'5-52.5 lb','Adjustments':'15','Pair':'Yes'}),
        ('Manduka', 'PRO {sku} Yoga Mat 71in', 'Fitness', 138.00, 12,
         'yoga-mat,6mm,non-slip',
         {'Thickness':'6mm','Length':'71in','Material':'PVC, latex-free'}),
        ('TRX', 'GO Suspension Trainer {sku}', 'Fitness', 169.95, 15,
         'suspension-trainer,portable,full-body',
         {'Length':'Adjustable','Anchor':'Door / Tree','Weight':'1 lb'}),
        ('Garmin', 'Edge {sku} GPS Bike Computer', 'Cycling', 249.99, 22,
         'bike-computer,gps,navigation',
         {'Display':'2.6in color','Battery':'20h','GPS':'Multi-band'}),
        ('Shimano', 'PD-{sku} SPD Clipless Pedals', 'Cycling', 89.99, 20,
         'pedals,spd,clipless',
         {'Type':'SPD clipless','Material':'Composite body, chromoly axle','Weight':'342g pair'}),
        ('Wilson', 'Pro Staff RF{sku} Tennis Racket', 'Tennis', 249.00, 18,
         'tennis,racket,pro-staff',
         {'Head Size':'97in²','Weight':'12.6 oz','Grip':'4 3/8'}),
    ],
    'toys': [
        ('LEGO', 'Star Wars {sku} Building Set', 'Building Sets', 79.99, 18,
         'lego,star-wars,collector',
         {'Pieces':'500+','Age':'8+','Theme':'Star Wars'}),
        ('LEGO', 'City Police Station {sku}', 'Building Sets', 119.99, 18,
         'lego,city,police',
         {'Pieces':'668','Age':'6+','Theme':'City'}),
        ('LEGO', 'Friends Heartlake {sku} School', 'Building Sets', 59.99, 22,
         'lego,friends,school',
         {'Pieces':'605','Age':'8+','Theme':'Friends'}),
        ('LEGO', 'Technic Bugatti Chiron {sku}', 'Building Sets', 349.99, 12,
         'lego,technic,bugatti',
         {'Pieces':'3599','Age':'16+','Theme':'Technic'}),
        ('Melissa & Doug', 'Wooden {sku} Activity Set Ages 3-5', 'Educational', 29.99, 25,
         'wood,educational,preschool',
         {'Material':'Wood','Age':'3-5','Pieces':'20'}),
        ('Magna-Tiles', 'Clear Colors {sku}-Piece Set', 'Building Sets', 119.99, 20,
         'magnetic,stem,creative',
         {'Pieces':'100','Age':'3+','Magnets':'Yes'}),
        ('Crayola', 'Inspiration Art Case {sku}-Piece', 'Arts & Crafts', 24.99, 28,
         'art-supplies,crayola,starter',
         {'Pieces':'140','Age':'5+','Includes':'Crayons, markers, pencils, paper'}),
        ('Hot Wheels', 'Track Builder Unlimited {sku}-Piece Set', 'Vehicles', 49.99, 25,
         'hot-wheels,track-builder,vehicles',
         {'Pieces':'40+','Vehicles':'2','Age':'5+'}),
        ('Barbie', 'Dreamhouse Doll Playset {sku}', 'Dolls', 199.99, 20,
         'barbie,dreamhouse,playset',
         {'Pieces':'75+','Levels':'3','Age':'3+'}),
        ('Disney', 'Frozen Elsa Singing Doll {sku}', 'Dolls', 39.99, 25,
         'frozen,disney,singing',
         {'Height':'12in','Battery':'AAA x 2','Age':'3+'}),
        ('Pokemon', 'TCG Booster Box {sku} Edition', 'Trading Cards', 119.99, 22,
         'pokemon,tcg,booster-box',
         {'Pack':'36 boosters','Cards per pack':'10','Age':'6+'}),
        ('Hasbro', 'Monopoly Classic Board Game {sku} Edition', 'Board Games', 24.99, 28,
         'board-game,monopoly,classic',
         {'Players':'2-6','Age':'8+','Pieces':'8 movers'}),
        ('Ravensburger', '{sku}-Piece Jigsaw Puzzle World Map', 'Puzzles', 29.99, 22,
         'puzzle,1000-piece,adult',
         {'Pieces':'1000','Age':'12+','Finished Size':'27x20in'}),
        ('Bicycle', 'Standard Index Playing Cards {sku}-Pack', 'Card Games', 8.99, 25,
         'playing-cards,classic,standard',
         {'Pack':'4','Material':'Air-cushion finish'}),
        ('Fisher-Price', 'Laugh & Learn Smart Stages Puppy {sku}', 'Infant', 24.99, 28,
         'baby,interactive,electronic',
         {'Age':'6 mo+','Battery':'AA x 3','Phrases':'75+'}),
    ],
}


# SKU suffix pools, deterministic per index
SKU_SUFFIXES = ['Pro', 'Plus', 'Max', 'Ultra', 'Lite', 'Edition X', 'V2', 'V3', 'V4', '2024',
                '2025', '2026', 'XL', 'Mini', 'SE', 'Air', 'One', 'Two', 'Three', 'Series A',
                'Series B', 'Limited', 'Sport', 'Classic', 'Signature', 'Elite', 'Studio',
                'Slim', 'Premium', 'Compact']
COLOR_NAMES = ['Black', 'White', 'Charcoal', 'Silver', 'Navy', 'Olive', 'Burgundy',
               'Forest Green', 'Stone Blue', 'Rose Gold', 'Graphite', 'Sand', 'Ivory',
               'Slate Gray', 'Crimson', 'Teal', 'Mocha', 'Espresso', 'Sunset', 'Lilac']
SIZE_VALUES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
SHOE_SIZES = ['6', '7', '8', '9', '10', '11', '12', '13']


def _build_generic_sku(idx, template, category, pool):
    brand, name_tpl, subcat, base_price, uplift, tag_csv, specs_tpl = template
    suffix = SKU_SUFFIXES[idx % len(SKU_SUFFIXES)]
    name = name_tpl.replace('{sku}', suffix)
    # mild deterministic price jitter ±10%
    jitter = -0.10 + ((idx * 37) % 21) / 100.0
    price = round(base_price * (1 + jitter), 2)
    list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.8 + ((idx * 19) % 110) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 80 + (idx * 173) % 28000
    color = COLOR_NAMES[idx % len(COLOR_NAMES)]
    specs = dict(specs_tpl)
    specs['Color'] = color
    specs['Brand'] = brand
    variants = {'color': [color, COLOR_NAMES[(idx + 1) % len(COLOR_NAMES)],
                          COLOR_NAMES[(idx + 7) % len(COLOR_NAMES)]]}
    if category == 'fashion' and subcat in ('Mens Clothing', 'Womens Clothing'):
        variants['size'] = SIZE_VALUES
    elif category == 'fashion' and subcat == 'Shoes':
        variants['size'] = SHOE_SIZES
    img = pool[idx % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 13) % len(pool)] for j in range(6)] if pool else []
    description = (
        f"{name} by {brand}. {subcat} delivering on quality, fit, and value. "
        + " ".join(f"{k}: {v}." for k, v in specs.items() if k != 'Brand')
    )
    features = [f"{k}: {v}" for k, v in list(specs.items())[:6]]
    tags = [t.strip() for t in tag_csv.split(',') if t.strip()] + [color.lower().replace(' ', '-')]
    is_deal = (idx % 4 == 0)
    is_bestseller = (reviews > 12000)
    is_featured = (idx % 11 == 0)
    return dict(
        name=name, brand=brand, category_slug=category, subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants=variants, stock=20 + (idx * 17 + int(rating * 10)) % 380,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='',
    )


def _insert_product(db, Product, data):
    slug = _slugify(data['name'])
    if Product.query.filter_by(slug=slug).first():
        return False
    list_price = data['list_price'] or data['price']
    deal_discount = 0
    if list_price > data['price']:
        deal_discount = int(round((list_price - data['price']) / list_price * 100))
    p = Product(
        name=data['name'],
        slug=slug,
        brand=data['brand'],
        category_slug=data['category_slug'],
        subcategory=data['subcategory'],
        description=data['description'],
        features=json.dumps(data['features']),
        specs=json.dumps(data['specs']),
        price=data['price'],
        list_price=list_price,
        image=data['image'],
        gallery_images=json.dumps(data['gallery']),
        variant_options=json.dumps(data['variants']),
        stock=data['stock'],
        rating=data['rating'],
        review_count=data['reviews'],
        is_featured=data['is_featured'],
        is_deal=data['is_deal'] or deal_discount >= 10,
        is_bestseller=data['is_bestseller'],
        deal_discount=deal_discount,
        feature_tags=json.dumps(data['tags']),
        release_date=data['release_date'],
    )
    db.session.add(p)
    return True


def seed_bulk_products(db, Product):
    """Add ~800 additional products to reach 1500+ total.

    Idempotent: skip when Product.count() >= 1450.
    """
    if Product.query.count() >= 1450:
        return 0

    rng = random.Random(2026)

    # 1) Books from Open Library snapshot
    book_path = os.path.join(DATA_DIR, 'openlib_books.json')
    books = []
    if os.path.exists(book_path):
        with open(book_path, 'r', encoding='utf-8') as f:
            books = json.load(f)
    book_pool = _category_pool('books')
    added = 0
    seen_titles = set()
    for idx, b in enumerate(books):
        title = b.get('title') or ''
        if not title or title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())
        data = _build_book(idx, b, book_pool, rng)
        if _insert_product(db, Product, data):
            added += 1
    db.session.commit()

    # 2) Generic SKUs across other categories
    for category, templates in SKU_TEMPLATES.items():
        pool = _category_pool(category)
        # 5 suffix variants per template => ~75 SKUs per category, x8 cats => ~600
        for t_idx, tpl in enumerate(templates):
            for variant_idx in range(5):
                idx = t_idx * 7 + variant_idx * 53
                data = _build_generic_sku(idx, tpl, category, pool)
                if _insert_product(db, Product, data):
                    added += 1
    db.session.commit()
    return added
